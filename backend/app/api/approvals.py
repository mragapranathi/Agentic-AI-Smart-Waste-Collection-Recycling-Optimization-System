from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import ApprovalRequest
from backend.app.schemas.pydantic_models import ApprovalRequestResponse, ApprovalDecisionRequest
from backend.app.workflows.runner import WorkflowRunner
from backend.app.services.replanning_service import ReplanningService

router = APIRouter(prefix="/approvals", tags=["Human-in-the-Loop Approvals"])

@router.get("", response_model=List[ApprovalRequestResponse])
def get_approvals(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ApprovalRequest)
    if status:
        query = query.filter(ApprovalRequest.status == status)
    return query.order_by(ApprovalRequest.created_at.desc()).all()

@router.get("/{id_or_wfid}", response_model=ApprovalRequestResponse)
def get_approval(id_or_wfid: str, db: Session = Depends(get_db)):
    if id_or_wfid.isdigit():
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == int(id_or_wfid)).first()
    else:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == id_or_wfid).first()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    return approval

@router.post("/{id_or_wfid}/approve", response_model=ApprovalRequestResponse)
def approve_request(
    id_or_wfid: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db)
):
    if id_or_wfid.isdigit():
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == int(id_or_wfid)).first()
    else:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == id_or_wfid).first()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    # Check if this is a dynamic replan approval
    plan = approval.proposed_plan
    if plan.get("replan_type") == "SURGE_STOP_INSERTION":
        ReplanningService.apply_replan(db, approval.id, payload.operator)
        db.refresh(approval)
        return approval

    # Standard full workflow plan approval
    WorkflowRunner.approve_workflow_plan(
        db=db,
        workflow_id=approval.workflow_id,
        operator=payload.operator,
        comment=payload.comment
    )
    db.refresh(approval)
    return approval

@router.post("/{id_or_wfid}/reject", response_model=ApprovalRequestResponse)
def reject_request(
    id_or_wfid: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db)
):
    if id_or_wfid.isdigit():
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == int(id_or_wfid)).first()
    else:
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == id_or_wfid).first()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    WorkflowRunner.reject_workflow_plan(
        db=db,
        workflow_id=approval.workflow_id,
        operator=payload.operator,
        comment=payload.comment
    )
    db.refresh(approval)
    return approval
