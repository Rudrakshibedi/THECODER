"""
Artifact service: turns agent LLM output into stored, queryable artifacts.

Most agents produce one artifact. The tester produces two (test-strategy.md
and qa-report.md) separated by a '---' delimiter. The split_tester_output()
helper handles that case; pipeline_service calls it directly rather than
routing through save_artifact which expects single-artifact output.
"""
from typing import List, Optional, Tuple
import re

from sqlalchemy.orm import Session

from app.core.config import AGENT_ARTIFACT_MAP, EXPLODE_ARTIFACT_TYPES
from app.db.models import Artifact
from app.services import workspace_service

# Delimiter the tester agent uses to separate test-strategy from qa-report
TESTER_OUTPUT_DELIMITER = "\n---\n"
QA_REPORT_ARTIFACT = ("qa-report", "qa-report.md")

# Matches a '### <relative/path>' header followed by a fenced code block,
# exactly as declared by code-template.md's Source Files / Dependencies &
# Configuration sections and test-strategy-template.md's Unit Tests section.
# This is the ONLY place that convention is parsed — one pattern, reused for
# both the coder's source-code artifact and the tester's unit-tests artifact.
CODE_BLOCK_PATTERN = re.compile(
    r"^###\s+(?P<path>\S.*?)\s*\n```[^\n]*\n(?P<content>.*?)\n```",
    re.MULTILINE | re.DOTALL,
)


class UnmappedAgentError(LookupError):
    """Agent has no entry in AGENT_ARTIFACT_MAP."""


class ArtifactNotFoundError(LookupError):
    pass


def resolve_artifact_target(agent_name: str) -> Tuple[str, str]:
    """Return (artifact_type, filename) for an agent name."""
    if agent_name not in AGENT_ARTIFACT_MAP:
        raise UnmappedAgentError(
            f"Agent '{agent_name}' has no artifact mapping in AGENT_ARTIFACT_MAP."
        )
    return AGENT_ARTIFACT_MAP[agent_name]


def save_artifact(
    db: Session,
    project_id: int,
    agent_name: str,
    markdown_content: str,
) -> Artifact:
    """Write artifact file and upsert DB row. One artifact per call."""
    artifact_type, filename = resolve_artifact_target(agent_name)
    return _upsert(db, project_id, artifact_type, filename, agent_name, markdown_content)


def save_named_artifact(
    db: Session,
    project_id: int,
    agent_name: str,
    artifact_type: str,
    filename: str,
    markdown_content: str,
) -> Artifact:
    """Save an artifact with explicit type/filename (used for tester's second output)."""
    return _upsert(db, project_id, artifact_type, filename, agent_name, markdown_content)


def split_tester_output(raw_output: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Split tester output into (test_strategy, unit_tests, qa_report).

    The tester produces up to three sections separated by '---' delimiters:
      Section 1: test-strategy.md content  (always present)
      Section 2: unit test code             (optional)
      Section 3: qa-report.md content       (optional)

    Returns a 3-tuple; missing sections are None.
    """
    parts = raw_output.split(TESTER_OUTPUT_DELIMITER)
    test_strategy = parts[0].strip() if len(parts) > 0 else raw_output
    unit_tests    = parts[1].strip() if len(parts) > 1 else None
    qa_report     = parts[2].strip() if len(parts) > 2 else None
    return test_strategy, unit_tests, qa_report


def parse_code_blocks(markdown_content: str) -> List[Tuple[str, str]]:
    """Extract every (relative_path, file_content) pair declared via the
    '### <path>' + fenced code block convention.

    Pure function — no I/O. Used to explode the coder's source-code
    artifact and the tester's unit-tests artifact into real files.
    Skips nothing structurally; callers decide which artifact types to run
    this against (see EXPLODE_ARTIFACT_TYPES in app/core/config.py).
    """
    return [
        (m.group("path").strip(), m.group("content"))
        for m in CODE_BLOCK_PATTERN.finditer(markdown_content)
    ]


def should_explode(artifact_type: str) -> bool:
    """Whether this artifact type's markdown should be exploded into a real
    file tree on disk, in addition to its consolidated .md file."""
    return artifact_type in EXPLODE_ARTIFACT_TYPES


def explode_code_artifact(project_id: int, markdown_content: str) -> List[str]:
    """Write every file declared in `markdown_content` to its own path under
    the project's workspace root (e.g. 'src/services/auth.ts',
    'tests/services/auth.test.ts'), using the path each file block declares
    for itself. Additive only — never touches the consolidated .md artifact
    already written under documents/ by _upsert().

    Returns the list of relative paths written. Silently skips any block
    whose declared path would escape the project directory.
    """
    written: List[str] = []
    for relative_path, content in parse_code_blocks(markdown_content):
        try:
            workspace_service.write_generated_file(project_id, relative_path, content)
            written.append(relative_path)
        except workspace_service.UnsafeGeneratedPathError:
            continue
    return written



def extract_reviewer_verdict(review_content: str) -> str:
    """
    Extract the machine-readable verdict from a review report.

    The reviewer is instructed to end with exactly one of:
      **Verdict**: APPROVED
      **Verdict**: CHANGES REQUIRED

    Returns "APPROVED" or "CHANGES REQUIRED". Defaults to "CHANGES REQUIRED"
    if no verdict line is found (conservative — do not proceed on ambiguity).
    """
    for line in reversed(review_content.splitlines()):
        line = line.strip()
        if "**Verdict**:" in line or "**verdict**:" in line.lower():
            if "APPROVED" in line.upper() and "CHANGES" not in line.upper():
                return "APPROVED"
            return "CHANGES REQUIRED"
    return "CHANGES REQUIRED"


def extract_qa_verdict(qa_content: str) -> str:
    """
    Extract the machine-readable verdict from a QA report.

    Returns "PASSED" or "FAILED". Defaults to "FAILED" on ambiguity.
    """
    for line in reversed(qa_content.splitlines()):
        line = line.strip()
        if "**QA Verdict**:" in line or "**qa verdict**:" in line.lower():
            if "PASSED" in line.upper():
                return "PASSED"
            return "FAILED"
    return "FAILED"


def _upsert(
    db: Session,
    project_id: int,
    artifact_type: str,
    filename: str,
    agent_name: str,
    content: str,
) -> Artifact:
    file_path = workspace_service.write_artifact_file(project_id, filename, content)

    existing = (
        db.query(Artifact)
        .filter(
            Artifact.project_id == project_id,
            Artifact.artifact_type == artifact_type,
        )
        .first()
    )
    if existing:
        existing.markdown_content = content
        existing.created_by_agent = agent_name
        existing.file_path = str(file_path)
        db.commit()
        db.refresh(existing)
        return existing

    artifact = Artifact(
        project_id=project_id,
        artifact_type=artifact_type,
        file_path=str(file_path),
        markdown_content=content,
        created_by_agent=agent_name,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def list_artifacts(db: Session, project_id: int) -> List[Artifact]:
    return (
        db.query(Artifact)
        .filter(Artifact.project_id == project_id)
        .order_by(Artifact.artifact_type)
        .all()
    )


def get_artifact(db: Session, project_id: int, artifact_type: str) -> Artifact:
    artifact = (
        db.query(Artifact)
        .filter(
            Artifact.project_id == project_id,
            Artifact.artifact_type == artifact_type,
        )
        .first()
    )
    if not artifact:
        raise ArtifactNotFoundError(
            f"No '{artifact_type}' artifact found for project {project_id}"
        )
    return artifact
