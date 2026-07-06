"""
Agent Runner service.

Execution pipeline:
  1. Validate project exists (fail fast, no LLM cost)
  2. Validate agent is registered in DB
  3. Check all upstream artifact dependencies exist (fail fast)
  4. Load agent markdown file fresh from disk
  5. Load skills for this agent from AGENT_SKILL_MAP
  6. Build system prompt (agent instructions + injected skills)
  7. Build user prompt (task + upstream artifact context, budgeted and
     smart-truncated — see _build_upstream_context)
  8. Skip the LLM call entirely if an identical (system, user) prompt was
     already sent successfully earlier in this process (see _PROMPT_CACHE)
  9. Call LLM with an agent-specific max_tokens budget
 10. Record execution in DB (success or failure)
 11. Save artifact to workspace + DB (success only)
 12. If the artifact type is configured to explode (source-code, unit-tests),
     write each declared file to its own path under workspace/ (src/, tests/,
     config files) via artifact_service.explode_code_artifact

Every run is recorded in `executions` regardless of outcome so the audit
log is always complete. The caller (pipeline_service) decides what to do
with failures and loop control.
"""
import hashlib
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from app.core.config import (
    AGENT_DEPENDENCY_MAP,
    AGENT_MAX_TOKENS_MAP,
    AGENT_SKILL_MAP,
    AGENT_TEMPLATE_MAP,
    MAX_CONTEXT_CHARS,
    MAX_TOTAL_CONTEXT_CHARS,
    MIN_ARTIFACT_CONTEXT_CHARS,
)
from app.db.models import Agent, Execution
from app.services import agent_loader, artifact_service, llm_client, prompt_builder
from app.services.agent_loader import AgentNotFoundError
from app.services.agent_parser import AgentParseError
from app.services.artifact_service import ArtifactNotFoundError, UnmappedAgentError
from app.services.llm_client import LLMExecutionError
from app.services.project_service import ProjectNotFoundError, get_project
from app.services.skill_loader import load_skills_for_agent
from app.services.template_loader import load_templates_for_agent
from app.services.workflow_loader import WorkflowNotFoundError, WorkflowParseError, load_workflow
from app.utils.token_guard import truncate_smart

# Process-lifetime cache: sha256(system_prompt + "\x00" + user_prompt) ->
# generated artifact text. If the Reviewer<->Coder / Tester<->Coder retry
# loops ever end up calling the same agent with byte-for-byte identical
# upstream context and task (e.g. a retry triggered by something other
# than a substantive change), we skip the Groq call entirely instead of
# re-billing tokens for a prompt we already know the answer to. This is
# pure caching, not architecture: dependency order, DB writes, and API
# behaviour are all unchanged — only whether we redundantly re-call the
# LLM for prompt content we've already sent successfully.
_PROMPT_CACHE: Dict[str, str] = {}


def _prompt_cache_key(system_prompt: str, user_prompt: str) -> str:
    digest = hashlib.sha256()
    digest.update(system_prompt.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(user_prompt.encode("utf-8"))
    return digest.hexdigest()


class AgentNotRegisteredError(LookupError):
    """Agent exists on disk but has no DB registry row yet."""


class MissingDependencyError(RuntimeError):
    """Raised when an agent's required upstream artifact doesn't exist yet."""


def run_agent(
    db: Session,
    agent_name: str,
    project_id: int,
    task: str,
    workflow_name: Optional[str] = None,
) -> Dict:
    """Run a registered agent and return the result dict.

    `workflow_name`, when provided, is loaded via workflow_loader and its
    purpose/description is injected into the system prompt as orchestration
    framing ("Workflow Context"). It never changes agent responsibilities,
    skills, or output structure — those remain owned by the Agent, Skills,
    and Template layers respectively. A missing/malformed workflow file is
    non-fatal: the run proceeds without workflow context.

    Raises:
        ProjectNotFoundError       — project_id not found
        AgentNotRegisteredError    — no DB row for agent_name
        MissingDependencyError     — required upstream artifact absent
        AgentNotFoundError         — .md file missing from disk
        AgentParseError            — .md file is malformed
        LLMExecutionError          — LLM call failed (execution still recorded)
    """
    project = get_project(db, project_id)

    agent_row = db.query(Agent).filter(Agent.name == agent_name).first()
    if not agent_row:
        raise AgentNotRegisteredError(
            f"Agent '{agent_name}' is not registered. "
            f"Register it via POST /agents/register."
        )

    # Build upstream context from ONLY the artifacts this agent actually
    # depends on (AGENT_DEPENDENCY_MAP), never the full artifact history —
    # this is what keeps e.g. the Tester from re-receiving the Product
    # Manager's raw requirements verbatim through every intermediate stage.
    upstream_context: Optional[str] = None
    required_types: List[str] = AGENT_DEPENDENCY_MAP.get(agent_name, [])
    if required_types:
        # Per-artifact budget: MAX_CONTEXT_CHARS is the ceiling for a single
        # dependency, but agents with several dependencies (reviewer: 4,
        # tester: 4) would otherwise multiply that ceiling by the number of
        # artifacts. Instead, split a fixed total budget evenly across all
        # required artifacts, capped at MAX_CONTEXT_CHARS and floored at
        # MIN_ARTIFACT_CONTEXT_CHARS so no single slice becomes useless.
        fair_share = MAX_TOTAL_CONTEXT_CHARS // max(len(required_types), 1)
        per_artifact_budget = max(
            MIN_ARTIFACT_CONTEXT_CHARS, min(MAX_CONTEXT_CHARS, fair_share)
        )

        sections = []
        for artifact_type in required_types:
            try:
                upstream = artifact_service.get_artifact(db, project_id, artifact_type)
            except ArtifactNotFoundError as exc:
                raise MissingDependencyError(
                    f"Agent '{agent_name}' requires '{artifact_type}' to exist "
                    f"for project {project_id}. Run the producing agent first. ({exc})"
                ) from exc

            # Smart head+tail truncation: keeps the leading structure/summary
            # of the artifact AND its trailing conclusion (e.g. a review
            # report's final "**Verdict**:" line), instead of only the head.
            content = truncate_smart(upstream.markdown_content, per_artifact_budget)

            sections.append(f"### {artifact_type}\n\n{content}")

        upstream_context = "\n\n---\n\n".join(sections)

    # Load agent definition fresh from disk every run
    parsed_agent = agent_loader.load_agent(agent_name)

    # Load skills for this agent
    skill_names: List[str] = AGENT_SKILL_MAP.get(agent_name, [])
    skills = load_skills_for_agent(agent_name, skill_names)

    # Load template(s) for this agent — the ONLY source of Required Output
    # Format. AGENT_TEMPLATE_MAP is the single source of truth for agent ->
    # template resolution (mirrors AGENT_SKILL_MAP).
    template_names: List[str] = AGENT_TEMPLATE_MAP.get(agent_name, [])
    templates = load_templates_for_agent(template_names)

    # Load workflow orchestration context, if this run is part of a named
    # workflow. Non-fatal if absent/malformed — falls back to no framing.
    workflow = None
    if workflow_name:
        try:
            workflow = load_workflow(workflow_name)
        except (WorkflowNotFoundError, WorkflowParseError):
            workflow = None

    project_context = {"name": project.name, "description": project.description}

    # Build prompts
    system_prompt = prompt_builder.build_system_prompt(
        parsed_agent, skills=skills, workflow=workflow, templates=templates
    )
    user_prompt = prompt_builder.build_user_prompt(
        str(project_id), task, context=upstream_context, project_context=project_context
    )

    # Skip the LLM call if this exact (system, user) prompt already produced
    # a successful artifact earlier in this process — see _PROMPT_CACHE.
    cache_key = _prompt_cache_key(system_prompt, user_prompt)
    cached = _PROMPT_CACHE.get(cache_key)

    if cached is not None:
        artifact_text = cached
    else:
        # Per-agent completion budget instead of one flat ceiling for every
        # agent (AGENT_MAX_TOKENS_MAP falls back to DEFAULT_LLM_MAX_TOKENS
        # inside llm_client when an agent isn't listed).
        max_tokens = AGENT_MAX_TOKENS_MAP.get(agent_name)
        try:
            artifact_text = llm_client.generate(system_prompt, user_prompt, max_tokens=max_tokens)
        except LLMExecutionError as exc:
            _record_execution(db, agent_row.id, project_id, task, str(exc), "failed")
            raise
        _PROMPT_CACHE[cache_key] = artifact_text

    _record_execution(db, agent_row.id, project_id, task, artifact_text, "success")

    # Save artifact to workspace + DB (silently skip if agent has no mapping)
    try:
        artifact_service.save_artifact(db, project_id, agent_name, artifact_text)
        artifact_type, _ = artifact_service.resolve_artifact_target(agent_name)
        if artifact_service.should_explode(artifact_type):
            artifact_service.explode_code_artifact(project_id, artifact_text)
    except UnmappedAgentError:
        pass

    return {
        "agent": agent_name,
        "generated_artifact": artifact_text,
        "status": "success",
    }


def _record_execution(
    db: Session,
    agent_id: int,
    project_id: int,
    task: str,
    output: str,
    status: str,
) -> Execution:
    execution = Execution(
        agent_id=agent_id,
        project_id=project_id,
        input=task,
        output=output,
        status=status,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def list_executions(
    db: Session, agent_name: str | None = None
) -> list[Execution]:
    query = db.query(Execution).join(Agent)
    if agent_name:
        query = query.filter(Agent.name == agent_name)
    return query.order_by(Execution.created_at.desc()).all()
