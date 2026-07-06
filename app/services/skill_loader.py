"""
Skill Loader service.

Mirrors agent_loader.py exactly in pattern:
  - reads skill markdown files from skills/
  - parses frontmatter (name, version, description, used_by) and sections
    (Capabilities, Instructions, Expected Usage) via the existing agent_parser
  - provides load_skill(name) for retrieval by name
  - provides sync_skills_from_disk() for startup discovery

Skills are file-only — they are not stored in the DB. The skills/ directory
IS the registry. No DB table is needed because skills are read-only reference
material injected into prompts; they are never created or updated via the API.
"""
import hashlib
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.core.config import SKILLS_DIR

FRONTMATTER_PATTERN = __import__("re").compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$", __import__("re").DOTALL
)
SECTION_PATTERN = __import__("re").compile(r"^##\s+(.+?)\s*$", __import__("re").MULTILINE)


class SkillNotFoundError(LookupError):
    pass


class SkillParseError(ValueError):
    pass


def _file_for(name: str) -> Path:
    return SKILLS_DIR / f"{name}.md"


def _split_sections(body: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    headings = list(SECTION_PATTERN.finditer(body))
    for i, m in enumerate(headings):
        heading = m.group(1).strip().lower()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        sections[heading] = body[start:end].strip()
    return sections


def parse_skill_markdown(content: str) -> Dict[str, Any]:
    """Parse a skill markdown file into a structured dict.

    Returns keys: name, version, description, used_by (list),
    capabilities (str), instructions (str), expected_usage (str).
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise SkillParseError(
            "Skill markdown must start with a YAML frontmatter block delimited by '---'."
        )
    frontmatter_raw, body = match.groups()
    try:
        fm = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"Invalid YAML frontmatter: {exc}") from exc

    if "name" not in fm:
        raise SkillParseError("Skill frontmatter missing required field: 'name'")

    sections = _split_sections(body)
    return {
        "name": fm["name"],
        "version": str(fm.get("version", "1.0.0")),
        "description": fm.get("description", ""),
        "used_by": fm.get("used_by") or [],
        "capabilities": sections.get("capabilities", "").strip(),
        "instructions": sections.get("instructions", "").strip(),
        "expected_usage": sections.get("expected usage", "").strip(),
    }


def read_skill_file(name: str) -> str:
    path = _file_for(name)
    if not path.exists():
        raise SkillNotFoundError(f"No skill file found for '{name}'")
    return path.read_text(encoding="utf-8")


def load_skill(name: str) -> Dict[str, Any]:
    """Read and parse a skill by name. The primary entry point for callers."""
    content = read_skill_file(name)
    try:
        parsed = parse_skill_markdown(content)
    except SkillParseError as exc:
        raise SkillParseError(f"Skill '{name}' is malformed: {exc}") from exc
    parsed["file_path"] = str(_file_for(name))
    return parsed


def load_skills_for_agent(agent_name: str, skill_names: List[str]) -> List[Dict[str, Any]]:
    """Load all skills for an agent, silently skipping any that fail to parse."""
    skills = []
    for name in skill_names:
        try:
            skills.append(load_skill(name))
        except (SkillNotFoundError, SkillParseError):
            continue
    return skills


def discover_skill_files() -> List[Path]:
    return sorted(SKILLS_DIR.glob("*.md"))


def list_skills() -> List[Dict[str, Any]]:
    """Return a summary list of all available skills."""
    skills = []
    for path in discover_skill_files():
        try:
            content = path.read_text(encoding="utf-8")
            parsed = parse_skill_markdown(content)
            skills.append({
                "name": parsed["name"],
                "version": parsed["version"],
                "description": parsed["description"],
                "used_by": parsed["used_by"],
                "file_path": str(path),
            })
        except SkillParseError:
            continue
    return skills
