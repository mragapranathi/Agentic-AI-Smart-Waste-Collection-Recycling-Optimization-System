from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import Route, RouteStop, Bin, Vehicle, Collection
from backend.app.schemas.pydantic_models import RouteResponse, RouteStopResponse, RouteOptimizationRequest, RouteReplanRequest
from backend.app.optimization.vrp_solver import VRPOptimizer
from backend.app.optimization.constraints import RoutingConstraints
from backend.app.services.priority_engine import PriorityEngine
from backend.app.services.replanning_service import ReplanningService

router = APIRouter(prefix="/routes", tags=["Route Optimization"])

@router.get("", response_model=List[RouteResponse])
def get_routes(route_status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Route)
    if route_status:
        query = query.filter(Route.route_status == route_status)
    routes = query.order_by(Route.created_at.desc()).all()

    # Hydrate stops with coordinate info
    result = []
    for r in routes:
        stops_out = []
        for s in r.stops:
            b = db.query(Bin).filter(Bin.bin_id == s.bin_id).first()
            stops_out.append(RouteStopResponse(
                id=s.id,
                route_id=s.route_id,
                sequence=s.sequence,
                bin_id=s.bin_id,
                estimated_arrival=s.estimated_arrival,
                collected=s.collected,
                location_name=b.location_name if b else s.bin_id,
                latitude=b.latitude if b else 0.0,
                longitude=b.longitude if b else 0.0,
                waste_type=b.waste_type if b else "General",
                fill_percent=b.current_fill_percent if b else 0.0
            ))
        result.append(RouteResponse(
            id=r.id,
            route_id=r.route_id,
            vehicle_id=r.vehicle_id,
            route_status=r.route_status,
            total_distance_km=r.total_distance_km,
            estimated_duration_minutes=r.estimated_duration_minutes,
            optimization_score=r.optimization_score,
            created_at=r.created_at,
            approved_at=r.approved_at,
            stops=stops_out
        ))
    return result

@router.post("/optimize")
def run_route_optimization(
    payload: Optional[RouteOptimizationRequest] = None,
    db: Session = Depends(get_db)
):
    from backend.app.models.entities import Collection, RouteStop
    from datetime import datetime

    period = payload.planning_period_hours if payload else 24
    priorities = PriorityEngine.calculate_all_priorities(db, planning_period_hours=period)
    priorities_dict = {p["bin_id"]: p for p in priorities}

    # Selective Bins
    if payload and payload.bin_ids is not None:
        if len(payload.bin_ids) == 0:
            raise HTTPException(status_code=400, detail="At least one bin must be selected for route optimization.")
        bins = db.query(Bin).filter(Bin.bin_id.in_(payload.bin_ids)).all()
        if len(bins) < len(payload.bin_ids):
            found_ids = {b.bin_id for b in bins}
            missing = set(payload.bin_ids) - found_ids
            raise HTTPException(status_code=400, detail=f"Bin(s) not found: {', '.join(missing)}")
    else:
        # Automatic selection based on collection urgency
        bins_to_route_ids = [
            p["bin_id"] for p in priorities
            if p["priority_level"] in ("CRITICAL", "HIGH") or (payload and payload.allow_predictive_bins and p.get("is_predictive_candidate"))
        ]
        bins = db.query(Bin).filter(Bin.bin_id.in_(bins_to_route_ids)).all()

    # Selective Vehicles
    if payload and payload.vehicle_ids is not None:
        if len(payload.vehicle_ids) == 0:
            raise HTTPException(status_code=400, detail="At least one vehicle must be selected for route optimization.")
        vehicles = db.query(Vehicle).filter(Vehicle.vehicle_id.in_(payload.vehicle_ids)).all()
        if len(vehicles) < len(payload.vehicle_ids):
            found_vids = {v.vehicle_id for v in vehicles}
            missing = set(payload.vehicle_ids) - found_vids
            raise HTTPException(status_code=400, detail=f"Vehicle(s) not found: {', '.join(missing)}")
        for v in vehicles:
            if v.status != "AVAILABLE":
                raise HTTPException(status_code=400, detail=f"Vehicle '{v.vehicle_id}' is not available (current status: {v.status}).")
        
        # Capacity check
        total_demand = sum(b.capacity_liters * (b.current_fill_percent / 100.0) for b in bins)
        total_cap = sum(v.capacity_liters - v.current_load_liters for v in vehicles)
        if total_demand > total_cap:
            raise HTTPException(
                status_code=400,
                detail=f"Vehicle capacity is insufficient for the selected bins. (Demand: {total_demand:.0f} L, Capacity: {total_cap:.0f} L)"
            )

        # Waste compatibility check
        for b in bins:
            compat = any(RoutingConstraints.is_waste_compatible(v, b.waste_type) for v in vehicles)
            if not compat:
                raise HTTPException(
                    status_code=400,
                    detail=f"Incompatible waste stream: No selected vehicle supports '{b.waste_type}' waste for bin {b.bin_id}."
                )
    else:
        vehicles = db.query(Vehicle).filter(Vehicle.status == "AVAILABLE").all()

    depot_coord = (payload.depot_lat, payload.depot_lng) if (payload and payload.depot_lat is not None and payload.depot_lng is not None) else None

    res = VRPOptimizer.optimize_routes(
        bins_to_collect=bins,
        available_vehicles=vehicles,
        priorities=priorities_dict,
        depot_coord=depot_coord
    )

    # Persist to database if save_to_db is requested
    if payload and payload.save_to_db and res.get("routes"):
        now = datetime.utcnow()
        for r_data in res["routes"]:
            rid = r_data["route_id"]
            existing_r = db.query(Route).filter(Route.route_id == rid).first()
            if not existing_r:
                new_r = Route(
                    route_id=rid,
                    vehicle_id=r_data["vehicle_id"],
                    route_status="APPROVED",
                    total_distance_km=r_data["total_distance_km"],
                    estimated_duration_minutes=r_data["estimated_duration_minutes"],
                    optimization_score=r_data.get("optimization_score", 1.0),
                    created_at=now,
                    approved_at=now
                )
                db.add(new_r)

                veh = db.query(Vehicle).filter(Vehicle.vehicle_id == r_data["vehicle_id"]).first()
                if veh:
                    veh.status = "ASSIGNED"
                    veh.current_route_id = rid

                for stop in r_data.get("stops", []):
                    arrival_time = stop["estimated_arrival"]
                    if isinstance(arrival_time, str):
                        arrival_time = datetime.fromisoformat(arrival_time)
                    rs = RouteStop(
                        route_id=rid,
                        sequence=stop["sequence"],
                        bin_id=stop["bin_id"],
                        estimated_arrival=arrival_time,
                        collected=False
                    )
                    db.add(rs)

                    coll_id = f"COL-{rid}-{stop['bin_id']}"
                    existing_coll = db.query(Collection).filter(Collection.collection_id == coll_id).first()
                    if not existing_coll:
                        coll = Collection(
                            collection_id=coll_id,
                            bin_id=stop["bin_id"],
                            vehicle_id=r_data["vehicle_id"],
                            route_id=rid,
                            scheduled_time=arrival_time,
                            estimated_volume=stop.get("estimated_volume", 0.0),
                            status="APPROVED"
                        )
                        db.add(coll)
        db.commit()

    return res


@router.get("/{id_or_rid}", response_model=RouteResponse)
def get_route(id_or_rid: str, db: Session = Depends(get_db)):
    if id_or_rid.isdigit():
        route = db.query(Route).filter(Route.id == int(id_or_rid)).first()
    else:
        route = db.query(Route).filter(Route.route_id == id_or_rid).first()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found.")

    stops_out = []
    for s in route.stops:
        b = db.query(Bin).filter(Bin.bin_id == s.bin_id).first()
        stops_out.append(RouteStopResponse(
            id=s.id,
            route_id=s.route_id,
            sequence=s.sequence,
            bin_id=s.bin_id,
            estimated_arrival=s.estimated_arrival,
            collected=s.collected,
            location_name=b.location_name if b else s.bin_id,
            latitude=b.latitude if b else 0.0,
            longitude=b.longitude if b else 0.0,
            waste_type=b.waste_type if b else "General",
            fill_percent=b.current_fill_percent if b else 0.0
        ))

    return RouteResponse(
        id=route.id,
        route_id=route.route_id,
        vehicle_id=route.vehicle_id,
        route_status=route.route_status,
        total_distance_km=route.total_distance_km,
        estimated_duration_minutes=route.estimated_duration_minutes,
        optimization_score=route.optimization_score,
        created_at=route.created_at,
        approved_at=route.approved_at,
        stops=stops_out
    )

@router.post("/{id_or_rid}/replan")
def trigger_route_replan(
    id_or_rid: str,
    payload: RouteReplanRequest,
    db: Session = Depends(get_db)
):
    try:
        replan_res = ReplanningService.evaluate_and_replan(
            db=db,
            trigger_bin_id=payload.trigger_bin_id,
            reason=payload.reason
        )
        return replan_res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
