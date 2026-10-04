import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from backend.app.models.entities import Bin, Vehicle
from backend.app.optimization.distance import compute_distance_matrix, haversine_distance_km, estimate_duration_minutes
from backend.app.optimization.constraints import RoutingConstraints
from backend.app.core.config import settings
from backend.app.core.logging import logger

class VRPOptimizer:
    @classmethod
    def optimize_routes(
        cls,
        bins_to_collect: List[Bin],
        available_vehicles: List[Vehicle],
        priorities: Optional[Dict[str, Dict[str, Any]]] = None,
        depot_coord: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Solves multi-vehicle Capacitated Vehicle Routing Problem (CVRP) using Google OR-Tools.
        Partitioned by compatible waste stream to guarantee segregation compliance.
        """
        depot_lat = depot_coord[0] if depot_coord else settings.DEPOT_LAT
        depot_lng = depot_coord[1] if depot_coord else settings.DEPOT_LNG
        depot_location = (depot_lat, depot_lng)

        if not bins_to_collect or not available_vehicles:
            return {
                "routes": [],
                "unassigned_bins": [
                    {
                        "bin_id": b.bin_id,
                        "reason": "No available operational vehicles or no bins requiring collection."
                    } for b in bins_to_collect
                ],
                "total_distance_km": 0.0,
                "total_duration_minutes": 0.0,
                "optimization_status": "NO_WORK_OR_VEHICLES"
            }

        # Group bins by waste type to ensure segregated collection
        bins_by_waste = {}
        for b in bins_to_collect:
            bins_by_waste.setdefault(b.waste_type, []).append(b)

        all_generated_routes = []
        all_unassigned = []

        # Solve for each waste category
        for waste_type, stream_bins in bins_by_waste.items():
            # Find vehicles that support this waste type and are available
            compatible_vehicles = [
                v for v in available_vehicles
                if RoutingConstraints.is_vehicle_available(v) and
                   RoutingConstraints.is_waste_compatible(v, waste_type) and
                   RoutingConstraints.can_accommodate_volume(v, 100.0) # at least some capacity
            ]

            if not compatible_vehicles:
                for b in stream_bins:
                    all_unassigned.append({
                        "bin_id": b.bin_id,
                        "waste_type": b.waste_type,
                        "reason": f"No available vehicle compatible with '{waste_type}' waste stream."
                    })
                continue

            # Solve CVRP for this stream
            stream_result = cls._solve_cvrp_stream(
                stream_bins=stream_bins,
                vehicles=compatible_vehicles,
                depot_coord=depot_location,
                priorities=priorities or {}
            )

            all_generated_routes.extend(stream_result["routes"])
            all_unassigned.extend(stream_result["unassigned_bins"])

        total_dist = sum(r["total_distance_km"] for r in all_generated_routes)
        total_dur = sum(r["estimated_duration_minutes"] for r in all_generated_routes)

        logger.info(
            f"[INFO] OR-Tools CVRP solved: {len(all_generated_routes)} routes generated, "
            f"{sum(len(r['stops']) for r in all_generated_routes)} bins routed, "
            f"{len(all_unassigned)} unassigned. Total distance: {total_dist:.2f} km"
        )

        return {
            "routes": all_generated_routes,
            "unassigned_bins": all_unassigned,
            "total_distance_km": round(total_dist, 2),
            "total_duration_minutes": round(total_dur, 1),
            "optimization_status": "OPTIMAL" if not all_unassigned else "FEASIBLE_WITH_DROPPED_NODES"
        }

    @classmethod
    def _solve_cvrp_stream(
        cls,
        stream_bins: List[Bin],
        vehicles: List[Vehicle],
        depot_coord: tuple,
        priorities: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Solves a single waste stream CVRP problem with OR-Tools."""
        # Index 0 is the depot
        locations = [depot_coord] + [(b.latitude, b.longitude) for b in stream_bins]
        demands = [0] + [
            int(b.capacity_liters * (b.current_fill_percent / 100.0))
            for b in stream_bins
        ]

        vehicle_capacities = [
            int(v.capacity_liters - v.current_load_liters)
            for v in vehicles
        ]

        num_vehicles = len(vehicles)
        num_locations = len(locations)

        distance_matrix = compute_distance_matrix(locations)

        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Capacity Dimension
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity"
        )

        # Allow dropping unassigned nodes with penalty proportional to priority
        for node in range(1, num_locations):
            bin_obj = stream_bins[node - 1]
            p_info = priorities.get(bin_obj.bin_id, {})
            p_level = p_info.get("priority_level", "MEDIUM")

            # Penalty in meters: Higher penalty = harder for optimizer to drop
            penalty = 1_000_000  # Default 1000km equivalent
            if p_level == "CRITICAL":
                penalty = 10_000_000
            elif p_level == "HIGH":
                penalty = 5_000_000
            elif p_level == "MEDIUM":
                penalty = 1_000_000
            else:
                penalty = 200_000

            routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

        # Search Parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 3

        solution = routing.SolveWithParameters(search_parameters)

        routes_output = []
        visited_nodes = set()
        now = datetime.utcnow()

        if solution:
            for vehicle_idx, vehicle in enumerate(vehicles):
                index = routing.Start(vehicle_idx)
                route_stops = []
                route_dist_meters = 0
                route_load = 0
                seq = 1

                while not routing.IsEnd(index):
                    node = manager.IndexToNode(index)
                    if node != 0:
                        bin_obj = stream_bins[node - 1]
                        visited_nodes.add(node)
                        arrival_time = now + timedelta(minutes=seq * 6)
                        route_stops.append({
                            "sequence": seq,
                            "bin_id": bin_obj.bin_id,
                            "location_name": bin_obj.location_name,
                            "latitude": bin_obj.latitude,
                            "longitude": bin_obj.longitude,
                            "waste_type": bin_obj.waste_type,
                            "fill_percent": bin_obj.current_fill_percent,
                            "estimated_volume": round(demands[node], 1),
                            "estimated_arrival": arrival_time
                        })
                        route_load += demands[node]
                        seq += 1

                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    route_dist_meters += routing.GetArcCostForVehicle(previous_index, index, vehicle_idx)

                if route_stops:
                    dist_km = round(route_dist_meters / 1000.0, 2)
                    duration_min = estimate_duration_minutes(dist_km, len(route_stops))
                    utilization = round((route_load / vehicle.capacity_liters) * 100.0, 1)

                    routes_output.append({
                        "route_id": f"RT-{vehicle.vehicle_id}-{now.strftime('%H%M%S')}",
                        "vehicle_id": vehicle.vehicle_id,
                        "waste_type": vehicle.supported_waste_types[0] if vehicle.supported_waste_types else "General",
                        "total_distance_km": dist_km,
                        "estimated_duration_minutes": duration_min,
                        "total_volume_liters": route_load,
                        "vehicle_capacity_liters": vehicle.capacity_liters,
                        "capacity_utilization_percent": min(100.0, utilization),
                        "stops": route_stops,
                        "optimization_score": round(1.0 - (route_dist_meters / (len(route_stops) * 5000 + 1)), 2)
                    })

        # Identify unassigned bins
        unassigned = []
        for node in range(1, num_locations):
            if node not in visited_nodes:
                bin_obj = stream_bins[node - 1]
                unassigned.append({
                    "bin_id": bin_obj.bin_id,
                    "waste_type": bin_obj.waste_type,
                    "reason": f"Excluded due to vehicle capacity limit ({demands[node]}L demand) or detour cost."
                })

        return {
            "routes": routes_output,
            "unassigned_bins": unassigned
        }
