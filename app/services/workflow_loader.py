"""
Workflow Loader service.

Mirrors skill_loader.py in pattern:
  - reads workflow markdown files from workflows/
  - parses frontmatter (name, version, description, stages list)
  - provides load_workflow(name) for retrieval by name
  - stages list is the machine-readable part: each stage has sequence,
    agent, task_from, and optional loop_back_to / loop_on_verdict /
    max_iterations / requires_verdict fields used by pipeline_service

Workflows are file-only — no DB table needed.
"""
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.core.config import WORKFLOWS_DIR

FRONTMATTER_PATTERN = __import__("re").compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$", __import__("re").DOTALL
)
SECTION_PATTERN = __import__("re").compile(r"^##\s+(.+?)\s*$", __import__("re").MULTILINE)


class WorkflowNotFoundError(LookupError):
    pass


class WorkflowParseError(ValueError):
    pass


def _file_for(name: str) -> Path:
    return WORKFLOWS_DIR / f"{name}.md"


def _split_sections(body: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    headings = list(SECTION_PATTERN.finditer(body))
    for i, m in enumerate(headings):
        heading = m.group(1).strip().lower()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        sections[heading] = body[start:end].strip()
    return sections


def parse_workflow_markdown(content: str) -> Dict[str, Any]:
    """Parse a workflow markdown file into a structured dict.

    Returns keys: name, version, description, stages (list of stage dicts).
    Each stage dict: sequence (int), agent (str), task_from (str),
    and optionally: loop_back_to, loop_on_verdict, max_iterations,
    requires_verdict.
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise WorkflowParseError(
            "Workflow markdown must start with a YAML frontmatter block delimited by '---'."
        )
    frontmatter_raw, body = match.groups()
    try:
        fm = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as exc:
        raise WorkflowParseError(f"Invalid YAML frontmatter: {exc}") from exc

    if "name" not in fm:
        raise WorkflowParseError("Workflow frontmatter missing required field: 'name'")
    if "stages" not in fm or not isinstance(fm["stages"], list):
        raise WorkflowParseError("Workflow frontmatter missing required 'stages' list")

    # Validate and normalise stages
    stages = []
    for raw in fm["stages"]:
        if "sequence" not in raw or "agent" not in raw:
            raise WorkflowParseError(
                f"Each workflow stage must have 'sequence' and 'agent'. Got: {raw}"
            )
        stage: Dict[str, Any] = {
            "sequence": int(raw["sequence"]),
            "agent": str(raw["agent"]),
            "task_from": str(raw.get("task_from", "")),
        }
        # Optional feedback-loop fields
        if "loop_back_to" in raw:
            stage["loop_back_to"] = str(raw["loop_back_to"])
        if "loop_on_verdict" in raw:
            stage["loop_on_verdict"] = str(raw["loop_on_verdict"])
        if "max_iterations" in raw:
            stage["max_iterations"] = int(raw["max_iterations"])
        if "requires_verdict" in raw:
            stage["requires_verdict"] = str(raw["requires_verdict"])
        stages.append(stage)

    stages.sort(key=lambda s: s["sequence"])

    sections = _split_sections(body)
    return {
        "name": fm["name"],
        "version": str(fm.get("version", "1.0.0")),
        "description": fm.get("description", ""),
        "stages": stages,
        "purpose": sections.get("purpose", "").strip(),
        "steps": sections.get("steps", "").strip(),
        "agents_involved": sections.get("agents involved", "").strip(),
        "expected_outputs": sections.get("expected outputs", "").strip(),
        "required_skills": sections.get("required skills", "").strip(),
    }


def read_workflow_file(name: str) -> str:
    path = _file_for(name)
    if not path.exists():
        raise WorkflowNotFoundError(f"No workflow file found for '{name}'")
    return path.read_text(encoding="utf-8")


def load_workflow(name: str) -> Dict[str, Any]:
    """Read and parse a workflow by name. Primary entry point for callers."""
    content = read_workflow_file(name)
    try:
        parsed = parse_workflow_markdown(content)
    except WorkflowParseError as exc:
        raise WorkflowParseError(f"Workflow '{name}' is malformed: {exc}") from exc
    parsed["file_path"] = str(_file_for(name))
    return parsed


def discover_workflow_files() -> List[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.md"))


def list_workflows() -> List[Dict[str, Any]]:
    """Return a summary list of all available workflows."""
    workflows = []
    for path in discover_workflow_files():
        try:
            content = path.read_text(encoding="utf-8")
            parsed = parse_workflow_markdown(content)
            workflows.append({
                "name": parsed["name"],
                "version": parsed["version"],
                "description": parsed["description"],
                "stage_count": len(parsed["stages"]),
                "agents": [s["agent"] for s in parsed["stages"]],
                "file_path": str(path),
            })
        except WorkflowParseError:
            continue
    return workflows
