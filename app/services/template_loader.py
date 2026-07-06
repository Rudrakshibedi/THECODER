"""
Template Loader service.

Mirrors skill_loader.py and workflow_loader.py exactly in pattern:
  - reads template markdown files from templates/
  - parses frontmatter (name, version, description, used_by) and the
    '## Structure' section via the same frontmatter/section conventions
    used across the codebase
  - provides load_template(name) for retrieval by name
  - provides load_templates_for_agent() for bulk retrieval (an agent may
    reference more than one template, e.g. tester → test-strategy + qa-report)
  - provides sync-free startup discovery via list_templates()

Templates are file-only — they are not stored in the DB, exactly like
skills and workflows. The templates/ directory IS the registry. No DB
table is needed because templates are read-only reference material
injected into prompts; they are never created or updated via the API.

Templates define ONLY reusable output structure. A template's '## Structure'
section is the single thing ever injected into a prompt — no reasoning, no
implementation guidance, no business rules, and no workflow logic live here.
"""
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.core.config import TEMPLATES_DIR

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


class TemplateNotFoundError(LookupError):
    pass


class TemplateParseError(ValueError):
    pass


def _file_for(name: str) -> Path:
    return TEMPLATES_DIR / f"{name}.md"


def _heading_matches_outside_fences(body: str) -> List[re.Match]:
    """Find '## Heading' matches that are NOT inside a ``` fenced block.

    Template Structure sections are, by design, fenced markdown skeletons
    that legitimately contain their own '## 1. Foo' style headings (e.g. a
    solution-design skeleton has '## 1. System Architecture' inside its
    fence). A naive line-anchored regex would misread those as new
    top-level sections and truncate the real 'Structure' section at the
    first nested heading. This walks the body tracking fence state so only
    headings genuinely outside a ``` fence count as section boundaries.
    """
    matches = []
    in_fence = False
    for m in re.finditer(r"^```.*$|^##\s+(.+?)\s*$", body, re.MULTILINE):
        if m.group(0).startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            matches.append(m)
    return matches


def _split_sections(body: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    headings = _heading_matches_outside_fences(body)
    for i, m in enumerate(headings):
        heading = m.group(1).strip().lower()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        sections[heading] = body[start:end].strip()
    return sections


def parse_template_markdown(content: str) -> Dict[str, Any]:
    """Parse a template markdown file into a structured dict.

    Returns keys: name, version, description, used_by (list), structure (str).

    'structure' is the ONLY section ever injected into a prompt. It must
    contain reusable output formatting alone — no reasoning, no
    implementation guidance, no business rules, no workflow logic.
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise TemplateParseError(
            "Template markdown must start with a YAML frontmatter block delimited by '---'."
        )
    frontmatter_raw, body = match.groups()
    try:
        fm = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as exc:
        raise TemplateParseError(f"Invalid YAML frontmatter: {exc}") from exc

    if "name" not in fm:
        raise TemplateParseError("Template frontmatter missing required field: 'name'")

    sections = _split_sections(body)
    structure = sections.get("structure", "").strip()
    if not structure:
        raise TemplateParseError(
            f"Template '{fm['name']}' must contain a '## Structure' section"
        )

    return {
        "name": fm["name"],
        "version": str(fm.get("version", "1.0.0")),
        "description": fm.get("description", ""),
        "used_by": fm.get("used_by") or [],
        "structure": structure,
    }


def read_template_file(name: str) -> str:
    path = _file_for(name)
    if not path.exists():
        raise TemplateNotFoundError(f"No template file found for '{name}'")
    return path.read_text(encoding="utf-8")


def load_template(name: str) -> Dict[str, Any]:
    """Read and parse a template by name. Primary entry point for callers."""
    content = read_template_file(name)
    try:
        parsed = parse_template_markdown(content)
    except TemplateParseError as exc:
        raise TemplateParseError(f"Template '{name}' is malformed: {exc}") from exc
    parsed["file_path"] = str(_file_for(name))
    return parsed


def load_templates_for_agent(template_names: List[str]) -> List[Dict[str, Any]]:
    """Load all templates for an agent, silently skipping any that fail to parse.

    Mirrors load_skills_for_agent()'s fail-soft behaviour so a malformed or
    missing template degrades gracefully instead of blocking agent execution.
    """
    templates = []
    for name in template_names:
        try:
            templates.append(load_template(name))
        except (TemplateNotFoundError, TemplateParseError):
            continue
    return templates


def discover_template_files() -> List[Path]:
    return sorted(TEMPLATES_DIR.glob("*.md"))


def list_templates() -> List[Dict[str, Any]]:
    """Return a summary list of all available templates."""
    templates = []
    for path in discover_template_files():
        try:
            content = path.read_text(encoding="utf-8")
            parsed = parse_template_markdown(content)
            templates.append({
                "name": parsed["name"],
                "version": parsed["version"],
                "description": parsed["description"],
                "used_by": parsed["used_by"],
                "file_path": str(path),
            })
        except TemplateParseError:
            continue
    return templates
