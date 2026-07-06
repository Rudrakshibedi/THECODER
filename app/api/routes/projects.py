"""
Project + Artifact API endpoints:
  POST /projects                                - create a project (sets up its workspace)
  GET  /projects                                - list projects
  GET  /projects/{project_id}/artifacts         - list a project's artifacts
  GET  /projects/{project_id}/artifacts/{type}  - get one artifact's full content
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.project_schema import (
    ArtifactDetail,
    ArtifactListResponse,
    ArtifactSummary,
    ProjectCreateRequest,
    ProjectResponse,
)
from app.services import artifact_service, project_service
from app.services.artifact_service import ArtifactNotFoundError
from app.services.project_service import ProjectNotFoundError

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(payload: ProjectCreateRequest, db: Session = Depends(get_db)):
    project = project_service.create_project(db, name=payload.name, description=payload.description)
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return project_service.list_projects(db)


@router.get("/{project_id}/artifacts", response_model=ArtifactListResponse)
def get_project_artifacts(project_id: int, db: Session = Depends(get_db)):
    try:
        project_service.get_project(db, project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    artifacts = artifact_service.list_artifacts(db, project_id)
    return ArtifactListResponse(project_id=project_id, artifacts=artifacts, total=len(artifacts))


@router.get("/{project_id}/artifacts/{artifact_type}", response_model=ArtifactDetail)
def get_project_artifact(project_id: int, artifact_type: str, db: Session = Depends(get_db)):
    try:
        project_service.get_project(db, project_id)
        artifact = artifact_service.get_artifact(db, project_id, artifact_type)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ArtifactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return artifact
