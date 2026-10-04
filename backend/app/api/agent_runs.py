from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import AgentRun
from backend.app.schemas.pydantic_models import AgentRunResponse

router = APIRouter(prefix="/agent-runs", tags=["Agent Runs"])

@router.get("", response_model=List[AgentRunResponse])
def get_agent_runs(
    workflow_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(AgentRun)
    if workflow_id:
        query = query.filter(AgentRun.workflow_id == workflow_id)
    if agent_name:
        query = query.filter(AgentRun.agent_name == agent_name)
    return query.order_by(AgentRun.started_at.desc()).limit(limit).all()
