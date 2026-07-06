"""
Project service: project CRUD + workspace folder lifecycle.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import Project
from app.services import workspace_service


class ProjectNotFoundError(LookupError):
    pass


def create_project(db: Session, name: str, description: Optional[str] = None) -> Project:
    project = Project(name=name, description=description)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Workspace folder is created right after the DB row exists, since the
    # folder name is derived from the auto-generated project id.
    workspace_service.init_project_workspace(project.id)

    return project


def get_project(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundError(f"Project with id {project_id} not found")
    return project


def list_projects(db: Session) -> List[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()
