import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.entities import WorkflowRun, ApprovalRequest, Route, RouteStop, Collection, Bin, Vehicle
from backend.app.workflows.graph import build_waste_workflow_graph
from backend.app.core.logging import logger

class WorkflowRunner:

    @classmethod
    def run_optimization_workflow(
        cls,
        db: Session,
        planning_period_hours: int = 24,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the full 8-agent end-to-end municipal collection planning workflow.
        Builds a fresh graph per call so the db session is captured in closure.
        """
        wf_id = workflow_id or f"WF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"

        # Initialize workflow record
        wf_record = WorkflowRun(
            workflow_id=wf_id,
            current_state="RECEIVED",
            status="RUNNING",
            started_at=datetime.utcnow(),
            requires_human_approval=True
        )
        db.add(wf_record)
        db.commit()

        initial_state = {
            "workflow_id": wf_id,
            "planning_period_hours": planning_period_hours,
            "replan_count": 0,
        }

        try:
            # Build graph with db captured in node closures (no _db in state)
            graph = build_waste_workflow_graph(db)
            final_state = graph.invoke(initial_state)

            wf_record.current_state = "WAITING_FOR_APPROVAL"
            wf_record.status = "WAITING_APPROVAL"
            wf_record.completed_at = datetime.utcnow()
            db.commit()

            return final_state
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            wf_record.status = "FAILED"
            wf_record.current_state = "ERROR"
            wf_record.completed_at = datetime.utcnow()
            db.commit()
            raise e

    @classmethod
    def approve_workflow_plan(
        cls,
        db: Session,
        workflow_id: str,
        operator: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes human operator approval. Converts proposed plan into active Routes and Collections.
        Transitions state: PLANNED -> APPROVED -> IN_PROGRESS
        """
        approval = db.query(ApprovalRequest).filter(
            ApprovalRequest.workflow_id == workflow_id
        ).first()

        if not approval:
            raise ValueError(f"No approval request found for workflow '{workflow_id}'")

        if approval.status != "PENDING":
            raise ValueError(f"Approval request '{workflow_id}' is already in status '{approval.status}'")

        now = datetime.utcnow()
        approval.status = "APPROVED"
        approval.operator = operator
        approval.comment = comment
        approval.decided_at = now

        plan = approval.proposed_plan
        routes_data = plan.get("routes", [])

        created_routes = []
        for r_data in routes_data:
            route_id = r_data["route_id"]
            vehicle_id = r_data["vehicle_id"]

            route_obj = Route(
                route_id=route_id,
                vehicle_id=vehicle_id,
                route_status="APPROVED",
                total_distance_km=r_data["total_distance_km"],
                estimated_duration_minutes=r_data["estimated_duration_minutes"],
                optimization_score=r_data.get("optimization_score", 1.0),
                created_at=now,
                approved_at=now
            )
            db.add(route_obj)

            # Update vehicle status and route
            veh = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
            if veh:
                veh.status = "ASSIGNED"
                veh.current_route_id = route_id

            for stop in r_data.get("stops", []):
                route_stop = RouteStop(
                    route_id=route_id,
                    sequence=stop["sequence"],
                    bin_id=stop["bin_id"],
                    estimated_arrival=datetime.fromisoformat(stop["estimated_arrival"]) if isinstance(stop["estimated_arrival"], str) else stop["estimated_arrival"],
                    collected=False
                )
                db.add(route_stop)

                # Create collection record
                coll_id = f"COL-{route_id}-{stop['bin_id']}"
                coll = Collection(
                    collection_id=coll_id,
                    bin_id=stop["bin_id"],
                    vehicle_id=vehicle_id,
                    route_id=route_id,
                    scheduled_time=route_stop.estimated_arrival,
                    estimated_volume=stop.get("estimated_volume", 0.0),
                    status="APPROVED"
                )
                db.add(coll)

            created_routes.append(route_id)

        # Update Workflow Run
        wf_run = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).first()
        if wf_run:
            wf_run.current_state = "APPROVED"
            wf_run.status = "COMPLETED"

        db.commit()
        logger.info(f"[INFO] Plan approved by {operator} for workflow {workflow_id}. Created {len(created_routes)} operational routes.")

        return {
            "workflow_id": workflow_id,
            "status": "APPROVED",
            "operator": operator,
            "routes_activated": created_routes
        }

    @classmethod
    def reject_workflow_plan(
        cls,
        db: Session,
        workflow_id: str,
        operator: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        approval = db.query(ApprovalRequest).filter(
            ApprovalRequest.workflow_id == workflow_id
        ).first()

        if not approval:
            raise ValueError(f"No approval request found for workflow '{workflow_id}'")

        approval.status = "REJECTED"
        approval.operator = operator
        approval.comment = comment or "Plan rejected by operator."
        approval.decided_at = datetime.utcnow()

        wf_run = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id).first()
        if wf_run:
            wf_run.current_state = "REJECTED"
            wf_run.status = "REJECTED"

        db.commit()
        logger.info(f"[INFO] Plan rejected by {operator} for workflow {workflow_id}")
        return {"workflow_id": workflow_id, "status": "REJECTED", "operator": operator}
