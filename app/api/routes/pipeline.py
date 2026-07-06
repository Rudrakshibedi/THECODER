"""
Pipeline API endpoints:

  POST /projects/{project_id}/generate
      Run the full automated SDLC pipeline and return the complete package.

  GET  /projects/{project_id}/pipeline-runs
      History of all pipeline runs for a project.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.pipeline_schema import (
    GenerateRequest,
    PipelineRunListResponse,
    PipelineRunResponse,
)
from app.services import pipeline_service
from app.services.pipeline_service import PipelineExecutionError
from app.services.project_service import ProjectNotFoundError

router = APIRouter(tags=["pipeline"])


@router.post(
    "/projects/{project_id}/generate",
    response_model=PipelineRunResponse,
    summary="Run the full automated SDLC pipeline",
    responses={
        200: {"description": "Pipeline completed — full SDLC package returned"},
        206: {"description": "Pipeline failed mid-chain — partial results returned"},
        404: {"description": "Project not found"},
    },
)
def generate_sdlc_package(
    project_id: int,
    payload: GenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Executes the full SDLC pipeline:
      1. Product Manager   → requirements.md
      2. Architect         → solution-design.md
      3. Developer         → implementation-plan.md
      4. Coder             → source-code.md
      5. Reviewer          → review-report.md  [loops back to Coder if CHANGES REQUIRED]
      6. Tester            → test-strategy.md + qa-report.md  [loops back to Coder if FAILED]

    Provide an optional `workflow_name` to use a workflow file from workflows/
    instead of the built-in stage sequence.
    """
    try:
        result = pipeline_service.run_pipeline(
            db,
            project_id=project_id,
            idea=payload.idea,
            workflow_name=payload.workflow_name,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PipelineExecutionError as exc:
        raise HTTPException(
            status_code=206,
            detail={
                "message":            str(exc),
                "run_id":             exc.run_id,
                "failed_step":        exc.failed_step,
                "failed_agent":       exc.failed_agent,
                "produced_artifacts": exc.produced_artifacts,
            },
        ) from exc

    return result


@router.get(
    "/projects/{project_id}/pipeline-runs",
    response_model=PipelineRunListResponse,
    summary="List all pipeline runs for a project",
)
def list_pipeline_runs(project_id: int, db: Session = Depends(get_db)):
    try:
        runs = pipeline_service.get_pipeline_runs(db, project_id=project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PipelineRunListResponse(
        project_id=project_id, runs=runs, total=len(runs)
    )
