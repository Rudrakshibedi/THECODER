"""
Workspace service: owns all filesystem layout/operations for project
artifacts. No DB access here — this module only knows about paths and
file I/O, mirroring the separation used for agents/ in agent_loader.py.

Layout:
    workspace/
        project_{id}/
            documents/
                requirements.md
                solution-design.md
                implementation-plan.md
                source-code.md      (consolidated, DB-backed reference)
                review-report.md
                test-strategy.md
                unit-tests.md       (consolidated, DB-backed reference)
                qa-report.md
            <exploded files>         (e.g. src/..., tests/..., package.json —
                                       written relative to the project root
                                       using the exact path each generated
                                       file declares in its '### <path>'
                                       header; see artifact_service.explode_
                                       code_artifact)
"""
from pathlib import Path

from app.core.config import WORKSPACE_DIR


def project_dir(project_id: int) -> Path:
    return WORKSPACE_DIR / f"project_{project_id}"


def documents_dir(project_id: int) -> Path:
    return project_dir(project_id) / "documents"


def init_project_workspace(project_id: int) -> Path:
    """Create the project's folder structure. Idempotent."""
    docs_dir = documents_dir(project_id)
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir


def artifact_path(project_id: int, filename: str) -> Path:
    return documents_dir(project_id) / filename


def write_artifact_file(project_id: int, filename: str, content: str) -> Path:
    """Write (overwrite) an artifact markdown file for a project."""
    init_project_workspace(project_id)
    path = artifact_path(project_id, filename)
    path.write_text(content, encoding="utf-8")
    return path


def read_artifact_file(project_id: int, filename: str) -> str:
    path = artifact_path(project_id, filename)
    if not path.exists():
        raise FileNotFoundError(f"Artifact file not found: {path}")
    return path.read_text(encoding="utf-8")


class UnsafeGeneratedPathError(ValueError):
    """Raised when a generated file's declared relative path escapes the
    project directory (e.g. via '..' segments or an absolute path)."""


def write_generated_file(project_id: int, relative_path: str, content: str) -> Path:
    """Write one exploded file (source code or unit test) at its declared
    relative path under the project's root directory.

    Coder and Tester agents declare each file's path themselves (e.g.
    'src/services/auth.service.ts', 'tests/services/auth.service.test.ts')
    via the '### <path>' convention in code-template.md / test-strategy-
    template.md. This function trusts that path only after validating it
    cannot escape the project directory, then creates parent directories
    as needed and writes the file — producing the real src/ and tests/
    trees alongside documents/.
    """
    relative_path = relative_path.strip().lstrip("/")
    candidate = (project_dir(project_id) / relative_path).resolve()
    root = project_dir(project_id).resolve()
    if root not in candidate.parents and candidate != root:
        raise UnsafeGeneratedPathError(
            f"Generated file path '{relative_path}' escapes the project directory"
        )

    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(content, encoding="utf-8")
    return candidate


def list_generated_files(project_id: int) -> list[str]:
    """List every exploded file's path (relative to the project root),
    excluding the documents/ folder of consolidated .md artifacts.

    Used to surface what explode_code_artifact() has written (e.g. under
    src/, tests/, or config files at the project root) in API responses,
    without introducing a new endpoint — see pipeline_service._build_response.
    """
    root = project_dir(project_id)
    if not root.exists():
        return []
    docs_dir = documents_dir(project_id).resolve()
    paths = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        resolved = path.resolve()
        if docs_dir in resolved.parents:
            continue
        paths.append(str(path.relative_to(root)))
    return paths
