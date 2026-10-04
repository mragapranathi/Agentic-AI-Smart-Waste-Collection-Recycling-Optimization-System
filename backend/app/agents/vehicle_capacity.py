from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseAgent
from backend.app.models.entities import Vehicle
from backend.app.optimization.constraints import RoutingConstraints

class VehicleCapacityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Vehicle & Capacity Management Agent",
            role="Audits municipal fleet readiness, load limits, and compartment segregation capabilities"
        )

    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        vehicles = db.query(Vehicle).all()
        available_vehicles = [v for v in vehicles if RoutingConstraints.is_vehicle_available(v)]

        fleet_summary = []
        by_waste_type = {}

        for v in available_vehicles:
            rem_cap = v.capacity_liters - v.current_load_liters
            supported = v.supported_waste_types
            if isinstance(supported, str):
                import json
                try:
                    supported = json.loads(supported)
                except:
                    supported = [supported]

            for w in supported:
                by_waste_type.setdefault(w, []).append(v.vehicle_id)

            fleet_summary.append({
                "vehicle_id": v.vehicle_id,
                "supported_waste_types": supported,
                "capacity_liters": v.capacity_liters,
                "current_load_liters": v.current_load_liters,
                "remaining_capacity_liters": rem_cap,
                "status": v.status,
                "latitude": v.latitude,
                "longitude": v.longitude
            })

        total_avail_cap = sum(v["remaining_capacity_liters"] for v in fleet_summary)
        reasoning = (
            f"Assessed fleet of {len(vehicles)} trucks: {len(available_vehicles)} currently AVAILABLE "
            f"with {total_avail_cap:,.0f} L aggregate reserve capacity. Segregation matrix: "
            f"{', '.join(f'{k}: {len(v)} units' for k, v in by_waste_type.items())}."
        )

        return {
            "available_vehicles": fleet_summary,
            "total_available_units": len(available_vehicles),
            "aggregate_reserve_capacity_liters": total_avail_cap,
            "stream_allocations": by_waste_type
        }, reasoning
