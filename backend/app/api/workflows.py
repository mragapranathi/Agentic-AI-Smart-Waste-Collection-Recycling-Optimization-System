from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import WorkflowRun, AgentRun, ApprovalRequest
from backend.app.schemas.pydantic_models import WorkflowRunRequest, WorkflowRunResponse, AgentRunResponse, ApprovalRequestResponse
from backend.app.workflows.runner import WorkflowRunner

router = APIRouter(prefix="/workflows", tags=["Multi-Agent Workflows"])

@router.post("/run", response_model=WorkflowRunResponse)
def trigger_workflow_run(
    payload: Optional[WorkflowRunRequest] = None,
    db: Session = Depends(get_db)
):
    try:
        final_state = WorkflowRunner.run_optimization_workflow(db)
        wf_id = final_state["workflow_id"]
        wf_record = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == wf_id).first()
        agent_runs = db.query(AgentRun).filter(AgentRun.workflow_id == wf_id).all()
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == wf_id).first()

        return WorkflowRunResponse(
            id=wf_record.id,
            workflow_id=wf_record.workflow_id,
            current_state=wf_record.current_state,
            status=wf_record.status,
            started_at=wf_record.started_at,
            completed_at=wf_record.completed_at,
            requires_human_approval=wf_record.requires_human_approval,
            agent_runs=[AgentRunResponse.from_orm(a) for a in agent_runs],
            approval_request=ApprovalRequestResponse.from_orm(approval) if approval else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow run failed: {str(e)}")

@router.get("", response_model=List[WorkflowRunResponse])
def list_workflows(limit: int = 20, db: Session = Depends(get_db)):
    runs = db.query(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(limit).all()
    results = []
    for r in runs:
        agent_runs = db.query(AgentRun).filter(AgentRun.workflow_id == r.workflow_id).all()
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == r.workflow_id).first()
        results.append(WorkflowRunResponse(
            id=r.id,
            workflow_id=r.workflow_id,
            current_state=r.current_state,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            requires_human_approval=r.requires_human_approval,
            agent_runs=[AgentRunResponse.from_orm(a) for a in agent_runs],
            approval_request=ApprovalRequestResponse.from_orm(approval) if approval else None
        ))
    return results

@router.get("/{wf_id}", response_model=WorkflowRunResponse)
def get_workflow(wf_id: str, db: Session = Depends(get_db)):
    if wf_id.isdigit():
        wf_record = db.query(WorkflowRun).filter(WorkflowRun.id == int(wf_id)).first()
    else:
        wf_record = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == wf_id).first()

    if not wf_record:
        raise HTTPException(status_code=404, detail="Workflow run not found.")

    agent_runs = db.query(AgentRun).filter(AgentRun.workflow_id == wf_record.workflow_id).all()
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == wf_record.workflow_id).first()

    return WorkflowRunResponse(
        id=wf_record.id,
        workflow_id=wf_record.workflow_id,
        current_state=wf_record.current_state,
        status=wf_record.status,
        started_at=wf_record.started_at,
        completed_at=wf_record.completed_at,
        requires_human_approval=wf_record.requires_human_approval,
        agent_runs=[AgentRunResponse.from_orm(a) for a in agent_runs],
        approval_request=ApprovalRequestResponse.from_orm(approval) if approval else None
    )
