"""
Pydantic request/response contracts for the Execution API.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    project_id: int = Field(..., description="ID of an existing project this run belongs to")
    task: str = Field(
        "",
        description="Task/instruction for the agent. Required for agents that start "
        "from a raw idea (e.g. product-manager). Optional extra guidance for agents "
        "that derive their primary input from an upstream artifact (e.g. architect).",
    )


class ExecuteResponse(BaseModel):
    agent: str
    generated_artifact: str
    status: str


class ExecutionRecord(BaseModel):
    id: int
    agent_id: int
    project_id: Optional[str]
    input: str
    output: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
