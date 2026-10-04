from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseAgent
from backend.app.models.entities import Bin, Vehicle
from backend.app.optimization.vrp_solver import VRPOptimizer

class RouteOptimizerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Route Optimization Agent",
            role="Computes mathematically optimal CVRP collection tours with Google OR-Tools"
        )

    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        priorities_data = state.get("priorities", [])
        priorities_dict = {p["bin_id"]: p for p in priorities_data}

        # Select bins requiring collection:
        # 1. CRITICAL
        # 2. HIGH
        # 3. Predictive candidates (fill < threshold but projected to cross soon)
        target_bin_ids = [
            p["bin_id"] for p in priorities_data
            if p["priority_level"] in ("CRITICAL", "HIGH") or p.get("is_predictive_candidate")
        ]

        if not target_bin_ids:
            # Check if any bin simply exceeds threshold
            threshold_bins = db.query(Bin).filter(
                Bin.current_fill_percent >= Bin.collection_threshold_percent,
                Bin.sensor_status != "SUSPICIOUS"
            ).all()
            target_bin_ids = [b.bin_id for b in threshold_bins]

        bins_to_route = db.query(Bin).filter(Bin.bin_id.in_(target_bin_ids)).all()
        vehicles = db.query(Vehicle).filter(Vehicle.status == "AVAILABLE").all()

        optimization_result = VRPOptimizer.optimize_routes(
            bins_to_collect=bins_to_route,
            available_vehicles=vehicles,
            priorities=priorities_dict
        )

        routes = optimization_result["routes"]
        unassigned = optimization_result["unassigned_bins"]
        tot_dist = optimization_result["total_distance_km"]
        tot_dur = optimization_result["total_duration_minutes"]

        reasoning = (
            f"Google OR-Tools solver formulated {len(routes)} multi-stop CVRP collection routes covering "
            f"{tot_dist:.1f} km (est. {tot_dur:.0f} min). Routed {sum(len(r['stops']) for r in routes)} bins. "
            f"{len(unassigned)} bins left unassigned due to capacity or constraint limits."
        )

        return {
            "routes": routes,
            "unassigned_bins": unassigned,
            "total_distance_km": tot_dist,
            "total_duration_minutes": tot_dur,
            "routed_bin_count": sum(len(r["stops"]) for r in routes)
        }, reasoning
