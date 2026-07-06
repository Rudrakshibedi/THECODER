"""
Agent Loader service.

Responsible for:
  - reading agent markdown files from disk
  - parsing them via agent_parser
  - syncing metadata into the DB registry (Agent table)
  - loading full agent instructions dynamically by name

This is the single place that knows about the agents/ directory layout,
so routes never touch the filesystem directly.
"""
import hashlib
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.config import AGENTS_DIR
from app.db.models import Agent
from app.services.agent_parser import AgentParseError, parse_agent_markdown


class AgentNotFoundError(LookupError):
    pass


def _file_for(name: str) -> Path:
    return AGENTS_DIR / f"{name}.md"


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_agent_file(name: str) -> str:
    """Read raw markdown content for an agent by name."""
    path = _file_for(name)
    if not path.exists():
        raise AgentNotFoundError(f"No markdown file found for agent '{name}'")
    return path.read_text(encoding="utf-8")


def write_agent_file(name: str, markdown_content: str) -> Path:
    """Write/overwrite an agent's markdown file on disk."""
    path = _file_for(name)
    path.write_text(markdown_content, encoding="utf-8")
    return path


def load_agent(name: str) -> Dict:
    """Read + parse a single agent's markdown file into structured data.
    This is the 'dynamic loading' entry point: callers needing the full
    instructions for execution should use this function.
    """
    content = read_agent_file(name)
    try:
        parsed = parse_agent_markdown(content)
    except AgentParseError as exc:
        raise AgentParseError(f"Agent '{name}' is malformed: {exc}") from exc
    parsed["file_path"] = str(_file_for(name))
    return parsed


def discover_agent_files() -> List[Path]:
    """List all .md files currently present in the agents directory."""
    return sorted(AGENTS_DIR.glob("*.md"))


def register_agent(db: Session, name: str, markdown_content: str | None = None) -> Agent:
    """Register (create or update) an agent in the DB registry.

    If markdown_content is provided, it is written to disk first. Either
    way, the file is parsed and the DB row is created/updated to match.
    """
    if markdown_content is not None:
        write_agent_file(name, markdown_content)

    parsed = load_agent(name)
    content = read_agent_file(name)
    content_hash = _hash_content(content)

    existing = db.query(Agent).filter(Agent.name == parsed["name"]).first()
    if existing:
        existing.role = parsed["role"]
        existing.version = parsed["version"]
        existing.file_path = parsed["file_path"]
        existing.content_hash = content_hash
        db.commit()
        db.refresh(existing)
        return existing

    agent = Agent(
        name=parsed["name"],
        role=parsed["role"],
        version=parsed["version"],
        file_path=parsed["file_path"],
        content_hash=content_hash,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def sync_agents_from_disk(db: Session) -> List[Agent]:
    """Scan the agents directory and register/update every .md file found.
    Useful at startup so files dropped into agents/ are auto-indexed.
    """
    synced = []
    for path in discover_agent_files():
        name = path.stem
        try:
            synced.append(register_agent(db, name))
        except AgentParseError:
            # Skip malformed files rather than crashing the whole sync
            continue
    return synced


def list_agents(db: Session) -> List[Agent]:
    return db.query(Agent).order_by(Agent.name).all()


def get_agent_detail(db: Session, name: str) -> Dict:
    """Get full parsed agent detail, ensuring it's registered in the DB."""
    agent_row = db.query(Agent).filter(Agent.name == name).first()
    if not agent_row:
        raise AgentNotFoundError(f"Agent '{name}' is not registered")
    return load_agent(name)
