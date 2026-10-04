import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import Collection, Bin, Vehicle, RecyclingRecord, RouteStop
from backend.app.schemas.pydantic_models import CollectionCreate, CollectionUpdate, CollectionResponse
from backend.app.alerts.alert_engine import AlertEngine
from backend.app.core.logging import logger

router = APIRouter(prefix="/collections", tags=["Collection Operations"])

@router.get("", response_model=List[CollectionResponse])
def get_collections(
    status: Optional[str] = None,
    bin_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    route_id: Optional[str] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Collection)
    if status:
        query = query.filter(Collection.status == status)
    if bin_id:
        query = query.filter(Collection.bin_id == bin_id)
    if vehicle_id:
        query = query.filter(Collection.vehicle_id == vehicle_id)
    if route_id:
        query = query.filter(Collection.route_id == route_id)
    query = query.order_by(Collection.scheduled_time.desc())
    if limit:
        query = query.limit(limit)
    return query.all()

@router.post("", response_model=CollectionResponse, status_code=201)
def create_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    cid = payload.collection_id or f"COL-{str(uuid.uuid4())[:8]}"
    coll = Collection(
        collection_id=cid,
        bin_id=payload.bin_id,
        vehicle_id=payload.vehicle_id,
        route_id=payload.route_id,
        scheduled_time=payload.scheduled_time or datetime.utcnow(),
        estimated_volume=payload.estimated_volume,
        status="PLANNED",
        operator_comment=payload.operator_comment
    )
    db.add(coll)
    db.commit()
    db.refresh(coll)
    return coll

@router.put("/{id_or_cid}", response_model=CollectionResponse)
def update_collection(id_or_cid: str, payload: CollectionUpdate, db: Session = Depends(get_db)):
    if id_or_cid.isdigit():
        coll = db.query(Collection).filter(Collection.id == int(id_or_cid)).first()
    else:
        coll = db.query(Collection).filter(Collection.collection_id == id_or_cid).first()

    if not coll:
        raise HTTPException(status_code=404, detail="Collection record not found.")

    prev_status = coll.status
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(coll, k, v)

    now = datetime.utcnow()
    # Lifecycle updates on vehicle status
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == coll.vehicle_id).first()
    if payload.status == "EN_ROUTE" and vehicle:
        vehicle.status = "IN_TRANSIT"
    elif payload.status == "COLLECTING" and vehicle:
        vehicle.status = "COLLECTING"

    # TC-08: If status transitioned to COLLECTED, VERIFIED, or COMPLETED, update Bin, Vehicle, and Route state
    if payload.status in ("COLLECTED", "VERIFIED", "COMPLETED") and prev_status not in ("COLLECTED", "VERIFIED", "COMPLETED"):
        coll.actual_collection_time = coll.actual_collection_time or now
        actual_vol = coll.actual_volume if coll.actual_volume is not None else coll.estimated_volume
        coll.actual_volume = actual_vol

        # Update Bin state (reset fill, update collection time)
        bin_obj = db.query(Bin).filter(Bin.bin_id == coll.bin_id).first()
        if bin_obj:
            collected_weight = bin_obj.current_weight_kg
            bin_obj.current_fill_percent = 0.0
            bin_obj.current_weight_kg = 0.0
            bin_obj.last_collection_time = now
            # Clear overflow and threshold alerts
            AlertEngine.resolve_alerts_for_bin(db, bin_obj.bin_id, ["OVERFLOW_RISK", "THRESHOLD_EXCEEDED"])

            # Create recycling record
            rec_weight = collected_weight if bin_obj.waste_type == "Recyclable" else (collected_weight * 0.85 if bin_obj.waste_type == "Organic" else 0.0)
            contam = collected_weight * 0.08  # 8% estimated contamination
            rr = RecyclingRecord(
                collection_id=coll.collection_id,
                waste_type=bin_obj.waste_type,
                weight_kg=max(10.0, collected_weight),
                recyclable_weight_kg=rec_weight,
                contamination_weight_kg=contam,
                created_at=now
            )
            db.add(rr)

        # Update Vehicle load
        if vehicle:
            vehicle.current_load_liters = min(vehicle.capacity_liters, vehicle.current_load_liters + actual_vol)

        # Mark route stop as collected if part of a route
        if coll.route_id:
            stop = db.query(RouteStop).filter(
                RouteStop.route_id == coll.route_id,
                RouteStop.bin_id == coll.bin_id
            ).first()
            if stop:
                stop.collected = True

            # Check if all stops in this route are collected
            remaining_stops = db.query(RouteStop).filter(
                RouteStop.route_id == coll.route_id,
                RouteStop.collected == False
            ).count()

            if remaining_stops == 0:
                from backend.app.models.entities import Route
                route = db.query(Route).filter(Route.route_id == coll.route_id).first()
                if route:
                    route.route_status = "COMPLETED"
                if vehicle:
                    vehicle.status = "AVAILABLE"
                logger.info(f"Route {coll.route_id} completed all stops. Route marked COMPLETED and vehicle {vehicle.vehicle_id if vehicle else ''} reset to AVAILABLE.")

        logger.info(f"[TC-08] Collection completed for {coll.bin_id} by {coll.vehicle_id}. Bin reset, vehicle load updated.")

    db.commit()
    db.refresh(coll)
    return coll
