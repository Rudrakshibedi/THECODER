"""
Pydantic request/response contracts for the Pipeline API.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    idea: str = Field(
        ...,
        min_length=10,
        description="Raw product idea that seeds the entire SDLC pipeline.",
        examples=["Create a food delivery application"],
    )
    workflow_name: Optional[str] = Field(
        None,
        description="Name of a workflow file in workflows/ to use instead of "
                    "the default PIPELINE_STAGES sequence. E.g. 'create-project'.",
    )


class PipelineStepLog(BaseModel):
    sequence:      int
    iteration:     int            # which review/QA loop iteration (0 = first pass)
    agent:         str
    status:        str            # success | failed | skipped | running
    artifact_type: Optional[str]
    duration_ms:   Optional[int]
    error:         Optional[str]
    started_at:    Optional[str]
    completed_at:  Optional[str]


class PipelineRunResponse(BaseModel):
    run_id:            int
    project_id:        int
    status:            str
    review_iterations: int
    workflow_name:     Optional[str]
    started_at:        str
    completed_at:      Optional[str]
    steps:             List[PipelineStepLog]
    artifacts:         Dict[str, str]    # {artifact_type: markdown_content}
    generated_files:   List[str] = Field(
        default_factory=list,
        description="Relative paths of every exploded file written under "
        "workspace/project_{id}/ (e.g. src/..., tests/..., config files) — "
        "everything outside documents/.",
    )


class PipelineRunSummary(BaseModel):
    run_id:            int
    status:            str
    idea:              str
    workflow_name:     Optional[str]
    review_iterations: int
    steps_total:       int
    steps_succeeded:   int
    steps_failed:      int
    started_at:        str
    completed_at:      Optional[str]


class PipelineRunListResponse(BaseModel):
    project_id: int
    runs:       List[PipelineRunSummary]
    total:      int
