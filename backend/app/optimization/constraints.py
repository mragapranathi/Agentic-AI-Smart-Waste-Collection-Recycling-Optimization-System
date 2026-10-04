from typing import List, Tuple
from backend.app.models.entities import Vehicle, Bin

class RoutingConstraints:
    @staticmethod
    def is_vehicle_available(vehicle: Vehicle) -> bool:
        """Vehicle must be in AVAILABLE status to accept new routing assignments."""
        return vehicle.status == "AVAILABLE"

    @staticmethod
    def is_waste_compatible(vehicle: Vehicle, waste_type: str) -> bool:
        """
        Validates vehicle compartment waste type compatibility.
        vehicle.supported_waste_types is a list (e.g. ['General'] or ['Recyclable']).
        """
        supported = vehicle.supported_waste_types
        if isinstance(supported, str):
            import json
            try:
                supported = json.loads(supported)
            except:
                supported = [supported]
        return waste_type in supported or "All" in supported

    @staticmethod
    def can_accommodate_volume(vehicle: Vehicle, additional_volume_liters: float) -> bool:
        """
        Checks whether adding waste volume would breach maximum capacity.
        remaining = vehicle.capacity_liters - vehicle.current_load_liters
        """
        remaining_capacity = vehicle.capacity_liters - vehicle.current_load_liters
        return remaining_capacity >= additional_volume_liters

    @staticmethod
    def validate_assignment(vehicle: Vehicle, bin_obj: Bin, required_volume: float) -> Tuple[bool, str]:
        """Validates all assignment rules for a single vehicle and bin."""
        if not RoutingConstraints.is_vehicle_available(vehicle):
            return False, f"Vehicle {vehicle.vehicle_id} is currently in status '{vehicle.status}', not AVAILABLE."

        if not RoutingConstraints.is_waste_compatible(vehicle, bin_obj.waste_type):
            return False, (
                f"Waste type mismatch: Vehicle {vehicle.vehicle_id} supports {vehicle.supported_waste_types}, "
                f"but Bin {bin_obj.bin_id} holds '{bin_obj.waste_type}'."
            )

        if not RoutingConstraints.can_accommodate_volume(vehicle, required_volume):
            remaining = vehicle.capacity_liters - vehicle.current_load_liters
            return False, (
                f"Capacity overflow: Vehicle {vehicle.vehicle_id} has {remaining:.1f}L remaining, "
                f"but Bin {bin_obj.bin_id} requires {required_volume:.1f}L."
            )

        return True, "Assignment feasible."
