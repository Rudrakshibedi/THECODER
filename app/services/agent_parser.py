"""
Pure markdown -> structured dict parser for agent definition files.

No filesystem I/O here on purpose: this module only knows how to turn a
markdown string into structured data, which makes it trivially unit
testable and reusable (e.g. for validating agent content before saving).

Expected format:

    ---
    name: product-manager
    role: Product Manager
    version: 1.0.0
    ---

    ## Responsibilities
    - bullet
    - bullet

    ## Instructions
    free text...

    ## Output Format
    free text / code block...
"""
import re
from typing import Any, Dict, List

import yaml

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


class AgentParseError(ValueError):
    """Raised when an agent markdown file is malformed."""


def parse_agent_markdown(content: str) -> Dict[str, Any]:
    """Parse raw markdown content into a structured agent dict.

    Returns a dict with keys: name, role, version, responsibilities
    (list[str]), instructions (str), templates (list[str]), output_format (str).

    `templates` is the list of template names (from the `template:` or
    `templates:` frontmatter field) whose '## Structure' the Prompt Builder
    should inject as this agent's Required Output Format. Agents no longer
    own their output structure directly — that responsibility belongs to
    the templates/ layer (see app/services/template_loader.py). The legacy
    `output_format` key is still parsed for backward compatibility with any
    agent file that has not yet migrated to a `template:` reference, but new
    and updated agent files should rely on `templates` instead.
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise AgentParseError(
            "Agent markdown must start with a YAML frontmatter block "
            "delimited by '---' lines."
        )

    frontmatter_raw, body = match.groups()

    try:
        frontmatter = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as exc:
        raise AgentParseError(f"Invalid YAML frontmatter: {exc}") from exc

    for required in ("name", "role"):
        if required not in frontmatter:
            raise AgentParseError(f"Frontmatter missing required field: '{required}'")

    sections = _split_sections(body)

    responsibilities = _parse_bullets(sections.get("responsibilities", ""))
    instructions = sections.get("instructions", "").strip()
    output_format = sections.get("output format", "").strip()

    if not instructions:
        raise AgentParseError("Agent markdown must contain an '## Instructions' section")

    templates = _parse_template_refs(frontmatter)

    return {
        "name": frontmatter["name"],
        "role": frontmatter["role"],
        "version": str(frontmatter.get("version", "1.0.0")),
        "responsibilities": responsibilities,
        "instructions": instructions,
        "templates": templates,
        "output_format": output_format,
    }


def _parse_template_refs(frontmatter: Dict[str, Any]) -> List[str]:
    """Normalise the `template:` / `templates:` frontmatter field into a list.

    Accepts either a single string (`template: requirements-template`) or a
    list (`templates: [test-strategy-template, qa-report-template]`), since
    agents like the tester reference more than one template.
    """
    raw = frontmatter.get("templates", frontmatter.get("template"))
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return [str(t) for t in raw]


def _split_sections(body: str) -> Dict[str, str]:
    """Split the markdown body into {lowercased heading: content}."""
    sections: Dict[str, str] = {}
    headings = list(SECTION_PATTERN.finditer(body))

    for i, heading_match in enumerate(headings):
        heading = heading_match.group(1).strip().lower()
        start = heading_match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        sections[heading] = body[start:end].strip()

    return sections


def _parse_bullets(section_text: str) -> List[str]:
    """Extract '- item' bullet lines from a section as a list of strings."""
    bullets = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets
