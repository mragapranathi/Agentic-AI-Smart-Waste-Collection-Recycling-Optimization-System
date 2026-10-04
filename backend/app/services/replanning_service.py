from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session

from backend.app.models.entities import Bin, Route, RouteStop, Vehicle, ApprovalRequest, Alert
from backend.app.optimization.distance import haversine_distance_km, estimate_duration_minutes
from backend.app.optimization.constraints import RoutingConstraints
from backend.app.services.llm_service import LLMService
from backend.app.core.logging import logger

class ReplanningService:
    @classmethod
    def evaluate_and_replan(
        cls,
        db: Session,
        trigger_bin_id: str,
        reason: str = "Surge fill reading detected"
    ) -> Dict[str, Any]:
        """
        Executes dynamic route replanning when a bin fill level unexpectedly surges.
        Calculates insertion detour, verifies capacity headroom, creates revision proposal,
        and enforces PENDING_HUMAN_APPROVAL state before committing changes.
        """
        bin_obj = db.query(Bin).filter(Bin.bin_id == trigger_bin_id).first()
        if not bin_obj:
            raise ValueError(f"Bin '{trigger_bin_id}' does not exist.")

        # Find active or approved route for compatible waste type
        active_routes = db.query(Route).filter(
            Route.route_status.in_(["APPROVED", "IN_PROGRESS", "PLANNED"])
        ).all()

        candidate_route = None
        assigned_vehicle = None

        for r in active_routes:
            v = db.query(Vehicle).filter(Vehicle.vehicle_id == r.vehicle_id).first()
            if v and RoutingConstraints.is_waste_compatible(v, bin_obj.waste_type):
                # Calculate current route load
                stops = db.query(RouteStop).filter(RouteStop.route_id == r.route_id).all()
                route_load = sum(
                    (db.query(Bin).filter(Bin.bin_id == s.bin_id).first().capacity_liters *
                     db.query(Bin).filter(Bin.bin_id == s.bin_id).first().current_fill_percent / 100.0)
                    for s in stops if db.query(Bin).filter(Bin.bin_id == s.bin_id).first()
                )
                bin_load = bin_obj.capacity_liters * (bin_obj.current_fill_percent / 100.0)
                if (v.capacity_liters - v.current_load_liters - route_load) >= bin_load:
                    candidate_route = r
                    assigned_vehicle = v
                    break

        if not candidate_route:
            # No current active route has capacity; alert dispatcher
            alert = Alert(
                bin_id=trigger_bin_id,
                alert_type="REPLANNING_REQUIRED",
                severity="HIGH",
                message=f"Surge on {trigger_bin_id} ({bin_obj.current_fill_percent}%): No active vehicle with sufficient capacity to insert stop.",
                status="ACTIVE"
            )
            db.add(alert)
            db.commit()
            return {
                "success": False,
                "replan_status": "CAPACITY_EXHAUSTED",
                "message": f"No active compatible vehicle has sufficient capacity for {trigger_bin_id}."
            }

        # Retrieve existing stops
        existing_stops = db.query(RouteStop).filter(
            RouteStop.route_id == candidate_route.route_id
        ).order_by(RouteStop.sequence).all()

        # Find best insertion index that minimizes detour distance
        old_stops_info = []
        for s in existing_stops:
            b = db.query(Bin).filter(Bin.bin_id == s.bin_id).first()
            old_stops_info.append({
                "sequence": s.sequence,
                "bin_id": s.bin_id,
                "location_name": b.location_name if b else s.bin_id,
                "latitude": b.latitude if b else 0.0,
                "longitude": b.longitude if b else 0.0,
                "fill_percent": b.current_fill_percent if b else 0.0
            })

        # Calculate best insertion point
        best_index = len(old_stops_info)  # default append
        min_extra_dist = float("inf")

        for idx in range(len(old_stops_info) + 1):
            # calculate marginal detour
            prev_coord = (old_stops_info[idx-1]["latitude"], old_stops_info[idx-1]["longitude"]) if idx > 0 else (assigned_vehicle.latitude, assigned_vehicle.longitude)
            next_coord = (old_stops_info[idx]["latitude"], old_stops_info[idx]["longitude"]) if idx < len(old_stops_info) else (assigned_vehicle.latitude, assigned_vehicle.longitude)

            direct_dist = haversine_distance_km(prev_coord, next_coord)
            detour_dist = (haversine_distance_km(prev_coord, (bin_obj.latitude, bin_obj.longitude)) +
                           haversine_distance_km((bin_obj.latitude, bin_obj.longitude), next_coord))
            extra = detour_dist - direct_dist

            if extra < min_extra_dist:
                min_extra_dist = extra
                best_index = idx

        extra_km = round(max(0.8, min_extra_dist), 2)
        new_total_dist = round(candidate_route.total_distance_km + extra_km, 2)
        new_duration = estimate_duration_minutes(new_total_dist, len(old_stops_info) + 1)

        # Build revised stops sequence
        new_stops_info = list(old_stops_info)
        new_stops_info.insert(best_index, {
            "sequence": best_index + 1,
            "bin_id": bin_obj.bin_id,
            "location_name": bin_obj.location_name,
            "latitude": bin_obj.latitude,
            "longitude": bin_obj.longitude,
            "fill_percent": bin_obj.current_fill_percent,
            "is_new_insertion": True
        })

        # Re-number sequences
        for i, s in enumerate(new_stops_info):
            s["sequence"] = i + 1

        explanation = LLMService.generate_explanation(
            prompt="Explain dynamic route replanning surge insertion.",
            context={
                "topic": "replanning",
                "bin_id": bin_obj.bin_id,
                "vehicle_id": assigned_vehicle.vehicle_id,
                "detour_km": extra_km
            }
        )

        wf_id = f"REPLAN-{candidate_route.route_id}-{str(uuid.uuid4())[:6]}"

        proposed_plan = {
            "workflow_id": wf_id,
            "replan_type": "SURGE_STOP_INSERTION",
            "trigger_bin_id": trigger_bin_id,
            "target_route_id": candidate_route.route_id,
            "vehicle_id": assigned_vehicle.vehicle_id,
            "old_distance_km": candidate_route.total_distance_km,
            "new_distance_km": new_total_dist,
            "detour_km": extra_km,
            "old_duration_minutes": candidate_route.estimated_duration_minutes,
            "new_duration_minutes": new_duration,
            "old_stops": old_stops_info,
            "new_stops": new_stops_info,
            "ai_explanation": explanation,
            "status": "PENDING_HUMAN_APPROVAL"
        }

        # Store in approval requests
        approval = ApprovalRequest(
            workflow_id=wf_id,
            proposed_plan=proposed_plan,
            status="PENDING",
            created_at=datetime.utcnow()
        )
        db.add(approval)
        db.commit()

        logger.info(
            f"[INFO] Dynamic replanning computed for surge on {trigger_bin_id}. "
            f"Inserted into Route {candidate_route.route_id} (+{extra_km} km). Approval ID: {approval.id}"
        )

        return {
            "success": True,
            "status": "REPLAN_PROPOSED",
            "approval_id": approval.id,
            "workflow_id": wf_id,
            "marginal_detour_km": extra_km,
            "target_route_id": candidate_route.route_id,
            "proposed_plan": proposed_plan
        }

    @classmethod
    def apply_replan(cls, db: Session, approval_id: int, operator: str) -> Dict[str, Any]:
        """Applies approved replan modifications to active route and route_stops in the database."""
        approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
        if not approval:
            raise ValueError("Approval request not found.")

        plan = approval.proposed_plan
        route_id = plan["target_route_id"]
        route_obj = db.query(Route).filter(Route.route_id == route_id).first()
        if not route_obj:
            raise ValueError(f"Target route {route_id} not found.")

        # Update route distance and duration
        route_obj.total_distance_km = plan["new_distance_km"]
        route_obj.estimated_duration_minutes = plan["new_duration_minutes"]

        # Clear old stops and write new stops
        db.query(RouteStop).filter(RouteStop.route_id == route_id).delete()

        now = datetime.utcnow()
        for s in plan["new_stops"]:
            stop = RouteStop(
                route_id=route_id,
                sequence=s["sequence"],
                bin_id=s["bin_id"],
                estimated_arrival=now + timedelta(minutes=s["sequence"] * 6),
                collected=False
            )
            db.add(stop)

        approval.status = "APPROVED"
        approval.operator = operator
        approval.decided_at = now
        db.commit()

        logger.info(f"[INFO] Dynamic replan committed to Route {route_id} by operator '{operator}'")
        return {"success": True, "route_id": route_id, "status": "COMMITTED"}
