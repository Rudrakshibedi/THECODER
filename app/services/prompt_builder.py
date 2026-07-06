"""
Builds the system and user prompts sent to the LLM from a parsed agent
definition, optional skills, optional workflow context, optional templates,
project context, and the user's task/idea.

Pure functions — no I/O, no side effects, easily unit-testable.

Separation of concerns (do not blur these):
  - Agent      -> identity, responsibilities, behavioural instructions
  - Skills     -> reusable capabilities/techniques
  - Workflow   -> orchestration context (what stage this is, why it runs now)
  - Template   -> ONLY the required output structure/formatting
  - Project    -> the project this run belongs to (name/description)
  - User Input -> the task or upstream artifact content for this run

The Prompt Builder's job is composition only. It must never invent
formatting requirements itself — that's the Template's job — and it must
never inject reasoning/business rules on a template's behalf.
"""
from typing import Dict, List, Optional


def build_system_prompt(
    agent: Dict,
    skills: Optional[List[Dict]] = None,
    workflow: Optional[Dict] = None,
    templates: Optional[List[Dict]] = None,
) -> str:
    """Assemble the system prompt for an agent.

    Structure (fixed order):
      1. Agent Identity          (always present)
      2. Responsibilities        (always present)
      3. Skill Instructions      (one block per skill, if any)
      4. Workflow Context        (orchestration framing, if a workflow is active)
      5. Agent Instructions      (from the agent markdown file)
      6. Template Structure      (Required Output Format, from the template layer)

    Each section is owned by exactly one layer:
      - Identity/Responsibilities/Instructions come from the Agent.
      - Skill blocks come from Skills.
      - Workflow Context comes from the active Workflow.
      - Required Output Format comes ONLY from Templates — agents no longer
        carry their own output structure.
    """
    responsibilities = "\n".join(f"- {r}" for r in agent["responsibilities"])

    parts = [
        f"You are the '{agent['name']}' agent, acting as: {agent['role']}.",
        f"## Your Responsibilities\n{responsibilities}",
    ]

    # Inject skill instructions if provided
    if skills:
        for skill in skills:
            if skill.get("instructions"):
                parts.append(
                    f"## Skill: {skill['name']}\n"
                    f"{skill['description']}\n\n"
                    f"{skill['instructions']}"
                )

    # Inject workflow orchestration context, if this run is part of a workflow
    if workflow:
        parts.append(f"## Workflow Context\n{_render_workflow_context(workflow)}")

    parts.append(f"## Instructions\n{agent['instructions']}")

    # Required Output Format comes exclusively from the template layer now.
    # Fall back to the agent's legacy inline output_format only if no
    # template was resolved for this agent (keeps older/unmigrated agent
    # files working without a hard failure).
    format_block = _render_template_structure(templates) or agent.get("output_format", "")
    if format_block:
        parts.append(
            f"## Required Output Format\n"
            f"You MUST respond with a single markdown artifact following this format:\n"
            f"{format_block}"
        )

    return "\n\n".join(parts)


def _render_workflow_context(workflow: Dict) -> str:
    """Render a short orchestration framing line from a parsed workflow dict.

    Only surfaces *what stage this is and why*, never re-states agent
    responsibilities or template formatting — those belong to their own
    layers.
    """
    lines = [f"This run is part of the '{workflow['name']}' workflow."]
    if workflow.get("purpose"):
        lines.append(workflow["purpose"])
    return "\n".join(lines)


def _render_template_structure(templates: Optional[List[Dict]]) -> str:
    """Concatenate the '## Structure' block of each template, in order.

    This is the ONLY place template content enters a prompt. Multiple
    templates (e.g. tester -> test-strategy-template + qa-report-template)
    are joined with the same '---' separator the pipeline already expects
    between the tester's multi-document output, so downstream splitting
    logic (artifact_service.split_tester_output) keeps working unchanged.
    """
    if not templates:
        return ""
    structures = [t["structure"] for t in templates if t.get("structure")]
    return "\n\n---\n\n".join(structures)


def build_user_prompt(
    project_id: str,
    task: str,
    context: Optional[str] = None,
    project_context: Optional[Dict] = None,
) -> str:
    """Build the user-turn prompt.

    Structure (fixed order):
      1. Project Context   (project name/description, if available)
      2. Upstream Input     (content of upstream artifacts, if any — this is
                             how Workflow-driven artifact hand-off reaches the
                             agent)
      3. User Input          (the task/idea; optional additional guidance if
                             upstream context is present, sole input otherwise)
    """
    parts = [f"Project ID: {project_id}"]

    if project_context:
        parts.append(f"## Project Context\n{_render_project_context(project_context)}")

    if context:
        parts.append(f"## Upstream Input\n{context}")
        if task:
            parts.append(f"## User Input\n{task}")
    else:
        parts.append(f"## User Input\n{task}")

    return "\n\n".join(parts)


def _render_project_context(project_context: Dict) -> str:
    name = project_context.get("name", "")
    description = project_context.get("description") or "(no description provided)"
    return f"Name: {name}\nDescription: {description}"
