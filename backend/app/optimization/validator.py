from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.entities import Vehicle, Bin
from backend.app.optimization.constraints import RoutingConstraints

class RouteValidator:
    @staticmethod
    def validate_route_plan(
        db: Session,
        routes: List[Dict[str, Any]],
        bins_dict: Dict[str, Bin],
        vehicles_dict: Dict[str, Vehicle]
    ) -> Tuple[bool, List[str]]:
        """
        Independently audits a solved route plan against physical constraints.
        Returns: (is_valid, list_of_violations)
        """
        violations = []

        assigned_bins = set()

        for route in routes:
            vid = route["vehicle_id"]
            vehicle = vehicles_dict.get(vid)
            if not vehicle:
                violations.append(f"Route references unknown vehicle ID '{vid}'.")
                continue

            total_volume = 0.0
            stops = route.get("stops", [])

            for stop in stops:
                bin_id = stop["bin_id"]
                if bin_id in assigned_bins:
                    violations.append(f"Duplicate assignment detected: Bin '{bin_id}' assigned multiple times.")
                assigned_bins.add(bin_id)

                bin_obj = bins_dict.get(bin_id)
                if not bin_obj:
                    violations.append(f"Stop references nonexistent bin '{bin_id}'.")
                    continue

                # Waste type compatibility
                if not RoutingConstraints.is_waste_compatible(vehicle, bin_obj.waste_type):
                    violations.append(
                        f"Incompatible waste: Vehicle '{vid}' ({vehicle.supported_waste_types}) "
                        f"assigned to '{bin_id}' with waste '{bin_obj.waste_type}'."
                    )

                # Volume accumulation
                bin_vol = (bin_obj.capacity_liters * bin_obj.current_fill_percent) / 100.0
                total_volume += bin_vol

            # Capacity overflow check
            remaining_cap = vehicle.capacity_liters - vehicle.current_load_liters
            if total_volume > remaining_cap + 1e-4:
                violations.append(
                    f"Vehicle '{vid}' capacity exceeded! Route volume: {total_volume:.1f}L, "
                    f"vehicle available: {remaining_cap:.1f}L."
                )

        is_valid = len(violations) == 0
        return is_valid, violations
