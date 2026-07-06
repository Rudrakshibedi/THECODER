"""
Pydantic request/response contracts for Project and Artifact APIs.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ArtifactSummary(BaseModel):
    id: int
    project_id: int
    artifact_type: str
    created_by_agent: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArtifactDetail(ArtifactSummary):
    markdown_content: str
    file_path: str


class ArtifactListResponse(BaseModel):
    project_id: int
    artifacts: List[ArtifactSummary]
    total: int
