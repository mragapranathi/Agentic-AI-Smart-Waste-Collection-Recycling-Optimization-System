from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseAgent
from backend.app.models.entities import ApprovalRequest, WorkflowRun
from backend.app.services.llm_service import LLMService

class ActionPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Waste Operations & Action Planning Agent",
            role="Synthesizes multi-agent telemetry and routes into actionable, explainable operational plans"
        )

    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        routes = state.get("routes", [])
        priorities = state.get("priorities", [])
        unassigned = state.get("unassigned_bins", [])
        warnings = state.get("segregation_warnings", [])

        # Build detailed stops with reasons
        total_bins = 0
        total_vol = 0.0

        for r in routes:
            for s in r.get("stops", []):
                total_bins += 1
                total_vol += s.get("estimated_volume", 0.0)

        # Generate operational explanation
        plan_summary = (
            f"Proposed Municipal Dispatch: {len(routes)} active routes encompassing {total_bins} bins "
            f"({total_vol:,.0f} L estimated collection volume). "
        )

        explanation = LLMService.generate_explanation(
            prompt="Explain the operational rationale for this collection dispatch cycle.",
            context={
                "topic": "planning",
                "route_count": len(routes),
                "bin_count": total_bins,
                "volume_liters": total_vol,
                "unassigned_count": len(unassigned)
            }
        )

        proposed_plan = {
            "workflow_id": workflow_id,
            "created_at": datetime.utcnow().isoformat(),
            "routes": routes,
            "unassigned_bins": unassigned,
            "total_routes": len(routes),
            "total_bins_scheduled": total_bins,
            "total_estimated_volume_liters": round(total_vol, 1),
            "warnings": warnings,
            "feasibility_status": "FEASIBLE" if not warnings else "FEASIBLE_WITH_WARNINGS",
            "approval_status": "PENDING_HUMAN_APPROVAL",
            "ai_explanation": explanation
        }

        from backend.app.agents.base import make_json_serializable
        proposed_plan = make_json_serializable(proposed_plan)

        # Create or update persistent approval request
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == workflow_id).first()
        if not approval:
            approval = ApprovalRequest(
                workflow_id=workflow_id,
                proposed_plan=proposed_plan,
                status="PENDING",
                created_at=datetime.utcnow()
            )
            db.add(approval)
        else:
            approval.proposed_plan = proposed_plan
            approval.status = "PENDING"

        # Update workflow run state
        wf_run = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).first()
        if wf_run:
            wf_run.current_state = "WAITING_FOR_APPROVAL"
            wf_run.status = "WAITING_APPROVAL"

        db.commit()

        reasoning = (
            f"Compiled unified municipal action plan with {len(routes)} routes ({total_bins} bins). "
            f"Submitted into PENDING_HUMAN_APPROVAL queue. Automatic execution blocked per safety policy."
        )

        return {
            "proposed_plan": proposed_plan,
            "approval_id": approval.id if approval else None,
            "approval_state": "PENDING_HUMAN_APPROVAL"
        }, reasoning
