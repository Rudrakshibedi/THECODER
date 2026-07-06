"""
Pydantic request/response contracts for the Agent API.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentRegisterRequest(BaseModel):
    """Body for registering an agent that already has a markdown file
    on disk under the agents/ directory, OR for creating a new one by
    supplying raw markdown content."""
    name: str = Field(..., description="Unique agent identifier, e.g. 'product-manager'")
    markdown_content: Optional[str] = Field(
        None,
        description="Raw markdown content. If provided, a new .md file is "
        "created/overwritten in the agents directory. If omitted, the loader "
        "expects a file named '<name>.md' to already exist on disk.",
    )


class AgentSummary(BaseModel):
    """Lightweight representation for list views."""
    id: int
    name: str
    role: str
    version: str
    file_path: str
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentDetail(BaseModel):
    """Full agent detail including parsed markdown sections."""
    name: str
    role: str
    version: str
    responsibilities: List[str]
    instructions: str
    templates: List[str] = Field(
        default_factory=list,
        description="Template name(s) this agent's Required Output Format "
        "is resolved from (see AGENT_TEMPLATE_MAP / templates/ directory).",
    )
    output_format: str = Field(
        "",
        description="Deprecated: legacy inline output format, if the agent "
        "file has not migrated to a `template:` reference. Empty for all "
        "agents that now reference a template.",
    )
    file_path: str


class AgentListResponse(BaseModel):
    agents: List[AgentSummary]
    total: int
