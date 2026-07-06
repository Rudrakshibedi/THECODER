"""
Agent registry API endpoints:
  POST /agents/register   - register an agent (from disk file or raw markdown)
  GET  /agents            - list all registered agents
  GET  /agents/{name}     - get full parsed detail for one agent
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.agent_schema import (
    AgentDetail,
    AgentListResponse,
    AgentRegisterRequest,
    AgentSummary,
)
from app.services import agent_loader
from app.services.agent_parser import AgentParseError

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/register", response_model=AgentSummary, status_code=201)
def register_agent(payload: AgentRegisterRequest, db: Session = Depends(get_db)):
    try:
        agent = agent_loader.register_agent(
            db, name=payload.name, markdown_content=payload.markdown_content
        )
    except agent_loader.AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return agent


@router.get("", response_model=AgentListResponse)
def list_agents(db: Session = Depends(get_db)):
    agents = agent_loader.list_agents(db)
    return AgentListResponse(agents=agents, total=len(agents))


@router.get("/{name}", response_model=AgentDetail)
def get_agent(name: str, db: Session = Depends(get_db)):
    try:
        detail = agent_loader.get_agent_detail(db, name)
    except agent_loader.AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return detail
