"""
Pipeline service: automated SDLC chain execution.

Pipeline order: PM → Architect → Developer → Coder → Reviewer → Tester

The Reviewer→Coder feedback loop:
  - After the Reviewer runs, its verdict is extracted from review-report.md.
  - "APPROVED"         → proceed to Tester.
  - "CHANGES REQUIRED" → run Coder again with the review report as extra
                         context, then run Reviewer again. Repeat up to
                         MAX_REVIEW_ITERATIONS times. If the limit is
                         reached without approval, fail the pipeline.

The Tester→Coder feedback loop (if QA fails):
  - After Tester runs, its QA verdict is extracted from qa-report.md.
  - "PASSED"  → complete the pipeline.
  - "FAILED"  → run Coder again (with qa-report as context), then Reviewer,
                then Tester again. Maximum MAX_REVIEW_ITERATIONS times total.

Every agent execution is logged as a PipelineStep. Steps created during
loop iterations carry an `iteration` counter so the log is fully legible.
"""
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import AGENT_ARTIFACT_MAP, MAX_REVIEW_ITERATIONS, PIPELINE_STAGES
from app.db.models import Artifact, PipelineRun, PipelineStep
from app.services import agent_runner, artifact_service, workspace_service
from app.services.artifact_service import (
    QA_REPORT_ARTIFACT,
    extract_qa_verdict,
    extract_reviewer_verdict,
    split_tester_output,
    save_named_artifact,
)
from app.services.project_service import get_project


class PipelineExecutionError(RuntimeError):
    """Raised when the pipeline cannot complete. Carries partial state."""

    def __init__(
        self,
        message: str,
        run_id: int,
        failed_step: int,
        failed_agent: str,
        produced_artifacts: List[str],
    ):
        super().__init__(message)
        self.run_id = run_id
        self.failed_step = failed_step
        self.failed_agent = failed_agent
        self.produced_artifacts = produced_artifacts


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── PipelineRun helpers ────────────────────────────────────────────────────────

def _create_run(
    db: Session, project_id: int, idea: str, workflow_name: Optional[str]
) -> PipelineRun:
    run = PipelineRun(
        project_id=project_id,
        idea=idea,
        workflow_name=workflow_name,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _complete_run(db: Session, run: PipelineRun) -> None:
    run.status = "completed"
    run.completed_at = _now()
    db.commit()


def _fail_run(db: Session, run: PipelineRun) -> None:
    run.status = "failed"
    run.completed_at = _now()
    db.commit()


# ── PipelineStep helpers ───────────────────────────────────────────────────────

def _start_step(
    db: Session, run_id: int, sequence: int, agent_name: str, iteration: int = 0
) -> PipelineStep:
    step = PipelineStep(
        run_id=run_id,
        sequence=sequence,
        iteration=iteration,
        agent_name=agent_name,
        status="running",
        started_at=_now(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def _finish_step(
    db: Session,
    step: PipelineStep,
    status: str,
    duration_ms: Optional[int] = None,
    artifact_type: Optional[str] = None,
    error: Optional[str] = None,
) -> PipelineStep:
    step.status = status
    step.completed_at = _now()
    step.duration_ms = duration_ms
    step.artifact_type = artifact_type
    step.error = error
    db.commit()
    db.refresh(step)
    return step


def _skip_remaining(db: Session, run_id: int, remaining: List[Tuple]) -> None:
    for sequence, agent_name in remaining:
        step = PipelineStep(
            run_id=run_id,
            sequence=sequence,
            agent_name=agent_name,
            status="skipped",
            started_at=_now(),
            completed_at=_now(),
        )
        db.add(step)
    db.commit()


# ── Single agent execution (with step logging) ─────────────────────────────────

def _run_step(
    db: Session,
    run: PipelineRun,
    sequence: int,
    agent_name: str,
    project_id: int,
    task: str,
    produced: List[str],
    remaining_on_failure: List[Tuple],
    iteration: int = 0,
) -> str:
    """Execute one agent, log the step, and return the generated artifact text.

    On failure: logs the step as failed, skips remaining, fails the run,
    and raises PipelineExecutionError.
    """
    step = _start_step(db, run.id, sequence, agent_name, iteration)
    t0 = time.monotonic()
    try:
        result = agent_runner.run_agent(
            db,
            agent_name=agent_name,
            project_id=project_id,
            task=task,
            workflow_name=run.workflow_name,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        artifact_type = AGENT_ARTIFACT_MAP.get(agent_name, (None,))[0]
        _finish_step(db, step, "success", duration_ms, artifact_type)
        produced.append(agent_name)
        return result["generated_artifact"]

    except Exception as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        _finish_step(db, step, "failed", duration_ms, error=str(exc))
        _skip_remaining(db, run.id, remaining_on_failure)
        _fail_run(db, run)
        raise PipelineExecutionError(
            f"Pipeline failed at step {sequence} ({agent_name}): {exc}",
            run_id=run.id,
            failed_step=sequence,
            failed_agent=agent_name,
            produced_artifacts=produced,
        ) from exc


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(
    db: Session,
    project_id: int,
    idea: str,
    workflow_name: Optional[str] = None,
) -> Dict:
    """Execute the full SDLC pipeline with Reviewer↔Coder and Tester↔Coder loops.

    Stages: PM(1) → Architect(2) → Developer(3) → Coder(4) →
            Reviewer(5) [loop] → Tester(6) [loop]

    Returns the full response dict on success.
    Raises PipelineExecutionError on unrecoverable failure.
    """
    get_project(db, project_id)
    run = _create_run(db, project_id, idea, workflow_name)
    produced: List[str] = []

    # ── Stage 1: Product Manager ───────────────────────────────────────────────
    _run_step(db, run, 1, "product-manager", project_id, idea, produced,
              [(2,"architect"),(3,"developer"),(4,"coder"),(5,"reviewer"),(6,"tester")])

    # ── Stage 2: Architect ─────────────────────────────────────────────────────
    _run_step(db, run, 2, "architect", project_id, "", produced,
              [(3,"developer"),(4,"coder"),(5,"reviewer"),(6,"tester")])

    # ── Stage 3: Developer ─────────────────────────────────────────────────────
    _run_step(db, run, 3, "developer", project_id, "", produced,
              [(4,"coder"),(5,"reviewer"),(6,"tester")])

    # ── Stage 4: Coder ────────────────────────────────────────────────────────
    _run_step(db, run, 4, "coder", project_id, "", produced,
              [(5,"reviewer"),(6,"tester")])

    # ── Stage 5: Reviewer ↔ Coder loop ────────────────────────────────────────
    review_iteration = 0
    while True:
        review_text = _run_step(
            db, run, 5, "reviewer", project_id, "", produced,
            [(6,"tester")], iteration=review_iteration
        )
        verdict = extract_reviewer_verdict(review_text)

        if verdict == "APPROVED":
            break

        # CHANGES REQUIRED
        review_iteration += 1
        run.review_iterations = review_iteration
        db.commit()

        if review_iteration >= MAX_REVIEW_ITERATIONS:
            _skip_remaining(db, run.id, [(6, "tester")])
            _fail_run(db, run)
            raise PipelineExecutionError(
                f"Pipeline failed: Reviewer returned 'CHANGES REQUIRED' "
                f"{review_iteration} time(s), reaching the maximum of "
                f"{MAX_REVIEW_ITERATIONS}. Fix the underlying issues and re-run.",
                run_id=run.id,
                failed_step=5,
                failed_agent="reviewer",
                produced_artifacts=produced,
            )

        # Re-run Coder with the review report as additional guidance
        _run_step(
            db, run, 4, "coder", project_id,
            "The Reviewer has returned CHANGES REQUIRED. "
            "The review-report.md is now available as upstream context. "
            "Address all CRITICAL and HIGH issues before proceeding.",
            produced, [(5,"reviewer"),(6,"tester")],
            iteration=review_iteration,
        )

    # ── Stage 6: Tester ↔ Coder loop ──────────────────────────────────────────
    qa_iteration = 0
    while True:
        tester_text = _run_step(
            db, run, 6, "tester", project_id, "", produced,
            [], iteration=qa_iteration
        )

        # Tester produces test-strategy + unit tests + qa-report in one output
        test_strategy, unit_tests, qa_report = split_tester_output(tester_text)

        # Save test-strategy.md (primary artifact, already saved by agent_runner
        # via AGENT_ARTIFACT_MAP — but re-save just the strategy section here
        # so it's clean)
        artifact_service._upsert(
            db, project_id, "test-strategy", "test-strategy.md", "tester", test_strategy
        )

        # Save unit tests if present, and explode into real files under tests/
        if unit_tests:
            save_named_artifact(
                db, project_id, "tester", "unit-tests", "unit-tests.md", unit_tests
            )
            if artifact_service.should_explode("unit-tests"):
                artifact_service.explode_code_artifact(project_id, unit_tests)

        # Save qa-report.md if present
        if qa_report:
            qa_type, qa_file = QA_REPORT_ARTIFACT
            save_named_artifact(
                db, project_id, "tester", qa_type, qa_file, qa_report
            )
            qa_verdict = extract_qa_verdict(qa_report)
        else:
            qa_verdict = "PASSED"   # no report = treat as passed

        if qa_verdict == "PASSED":
            break

        # QA FAILED — loop back: Coder → Reviewer → Tester
        qa_iteration += 1
        run.review_iterations = run.review_iterations + 1
        db.commit()

        if qa_iteration >= MAX_REVIEW_ITERATIONS:
            _fail_run(db, run)
            raise PipelineExecutionError(
                f"Pipeline failed: Tester returned 'FAILED' {qa_iteration} time(s), "
                f"reaching the maximum retry limit of {MAX_REVIEW_ITERATIONS}.",
                run_id=run.id,
                failed_step=6,
                failed_agent="tester",
                produced_artifacts=produced,
            )

        # Re-run Coder, then Reviewer, then Tester
        _run_step(
            db, run, 4, "coder", project_id,
            "The Tester returned QA FAILED. The qa-report.md is now available "
            "as upstream context via review-report.md. Address all failing requirements.",
            produced, [(5,"reviewer"),(6,"tester")],
            iteration=qa_iteration,
        )
        _run_step(
            db, run, 5, "reviewer", project_id, "", produced,
            [(6,"tester")], iteration=qa_iteration,
        )

    _complete_run(db, run)
    db.refresh(run)
    return _build_response(db, run, project_id)


# ── Response builder ───────────────────────────────────────────────────────────

def _build_response(db: Session, run: PipelineRun, project_id: int) -> Dict:
    steps_log = [
        {
            "sequence":     s.sequence,
            "iteration":    s.iteration,
            "agent":        s.agent_name,
            "status":       s.status,
            "artifact_type": s.artifact_type,
            "duration_ms":  s.duration_ms,
            "error":        s.error,
            "started_at":   s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in run.steps
    ]
    rows: List[Artifact] = artifact_service.list_artifacts(db, project_id)
    return {
        "run_id":            run.id,
        "project_id":        project_id,
        "status":            run.status,
        "review_iterations": run.review_iterations,
        "workflow_name":     run.workflow_name,
        "started_at":        run.started_at.isoformat(),
        "completed_at":      run.completed_at.isoformat() if run.completed_at else None,
        "steps":             steps_log,
        "artifacts":         {r.artifact_type: r.markdown_content for r in rows},
        "generated_files":   workspace_service.list_generated_files(project_id),
    }


def get_pipeline_runs(db: Session, project_id: int) -> List[Dict]:
    runs = (
        db.query(PipelineRun)
        .filter(PipelineRun.project_id == project_id)
        .order_by(PipelineRun.started_at.desc())
        .all()
    )
    summaries = []
    for run in runs:
        db.refresh(run)
        summaries.append({
            "run_id":            run.id,
            "status":            run.status,
            "idea":              run.idea,
            "workflow_name":     run.workflow_name,
            "review_iterations": run.review_iterations,
            "steps_total":       len(run.steps),
            "steps_succeeded":   sum(1 for s in run.steps if s.status == "success"),
            "steps_failed":      sum(1 for s in run.steps if s.status == "failed"),
            "started_at":        run.started_at.isoformat(),
            "completed_at":      run.completed_at.isoformat() if run.completed_at else None,
        })
    return summaries
