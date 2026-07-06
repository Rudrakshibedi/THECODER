"""
Execution API endpoints:
  POST /agents/{agent_name}/execute     - run an agent against a task
  GET  /agents/{agent_name}/executions  - history for one agent
  GET  /executions                      - full execution history
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.execution_schema import ExecuteRequest, ExecuteResponse, ExecutionRecord
from app.services import agent_runner
from app.services.agent_loader import AgentNotFoundError
from app.services.agent_parser import AgentParseError
from app.services.agent_runner import AgentNotRegisteredError, MissingDependencyError
from app.services.llm_client import LLMExecutionError
from app.services.project_service import ProjectNotFoundError

router = APIRouter(tags=["execution"])


@router.post("/agents/{agent_name}/execute", response_model=ExecuteResponse)
def execute_agent(agent_name: str, payload: ExecuteRequest, db: Session = Depends(get_db)):
    try:
        result = agent_runner.run_agent(
            db, agent_name=agent_name, project_id=payload.project_id, task=payload.task
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentNotRegisteredError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingDependencyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AgentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMExecutionError as exc:
        raise HTTPException(status_code=502, detail=f"Agent execution failed: {exc}") from exc

    return result


@router.get("/agents/{agent_name}/executions", response_model=List[ExecutionRecord])
def get_agent_executions(agent_name: str, db: Session = Depends(get_db)):
    return agent_runner.list_executions(db, agent_name=agent_name)


@router.get("/executions", response_model=List[ExecutionRecord])
def get_all_executions(db: Session = Depends(get_db)):
    return agent_runner.list_executions(db)
