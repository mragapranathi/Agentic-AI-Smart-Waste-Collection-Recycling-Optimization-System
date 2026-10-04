from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import Bin, SensorReading, Alert
from backend.app.schemas.pydantic_models import SensorReadingCreate, SensorReadingResponse, AlertResponse
from backend.app.services.sensor_validator import SensorValidator
from backend.app.alerts.alert_engine import AlertEngine
from backend.app.core.logging import logger

router = APIRouter(prefix="/sensors", tags=["Sensors & IoT"])

@router.post("/readings", response_model=SensorReadingResponse, status_code=201)
def submit_sensor_reading(payload: SensorReadingCreate, db: Session = Depends(get_db)):
    bin_obj = db.query(Bin).filter(Bin.bin_id == payload.bin_id).first()
    if not bin_obj:
        raise HTTPException(status_code=404, detail=f"Target bin '{payload.bin_id}' does not exist.")

    now = payload.timestamp or datetime.utcnow()

    # Sensor validation check
    val_status, sensor_status, val_reason = SensorValidator.validate_reading(
        db=db,
        bin_obj=bin_obj,
        fill_percent=payload.fill_percent,
        weight_kg=payload.weight_kg,
        reading_time=now,
        battery_level=payload.battery_level
    )

    reading = SensorReading(
        bin_id=payload.bin_id,
        timestamp=now,
        fill_percent=payload.fill_percent,
        weight_kg=payload.weight_kg,
        temperature=payload.temperature,
        battery_level=payload.battery_level if payload.battery_level is not None else 100.0,
        sensor_status=sensor_status,
        validation_status=val_status,
        validation_reason=val_reason
    )
    db.add(reading)

    # Only update current bin fill and weight if reading is VALID or SUSPICIOUS (not impossible/INVALID)
    if val_status in ("VALID", "SUSPICIOUS"):
        bin_obj.current_fill_percent = payload.fill_percent
        bin_obj.current_weight_kg = payload.weight_kg
        if payload.battery_level is not None:
            bin_obj.battery_level = payload.battery_level
        bin_obj.sensor_status = sensor_status
        bin_obj.last_sensor_reading = now
    elif val_status == "INVALID":
        bin_obj.sensor_status = "INVALID"

    db.commit()
    db.refresh(reading)
    logger.info(f"[INFO] Sensor reading received for {payload.bin_id}: {payload.fill_percent}% ({val_status})")

    # ── DYNAMIC REPLANNING TRIGGER ───────────────────────────────────────────
    # If a valid reading pushes this bin to a critical surge (>=90%), and there
    # are active routes, automatically evaluate whether a route insertion is feasible.
    # Spec requirement: "If BIN-010 becomes critical while vehicles are operating,
    # the system should detect the change, determine whether collection can be
    # added to an existing route, check vehicle capacity, recalculate route impact."
    replan_result = None
    if val_status in ("VALID", "SUSPICIOUS") and payload.fill_percent >= 90.0:
        try:
            from backend.app.services.replanning_service import ReplanningService
            replan_result = ReplanningService.evaluate_and_replan(
                db=db,
                trigger_bin_id=payload.bin_id,
                reason=f"Sensor surge to {payload.fill_percent:.1f}% — dynamic route insertion evaluation."
            )
            if replan_result and replan_result.get("success"):
                logger.warning(
                    f"[DYNAMIC REPLAN] Bin {payload.bin_id} triggered route insertion on "
                    f"route {replan_result.get('route_id')}. Awaiting operator approval."
                )
        except Exception as e:
            logger.error(f"[DYNAMIC REPLAN] Failed for {payload.bin_id}: {e}")

    response = SensorReadingResponse.from_orm(reading)
    # Attach replan info as extra context (frontend can show alert banner)
    if replan_result:
        response.__dict__["replan_triggered"] = replan_result.get("success", False)
        response.__dict__["replan_status"] = replan_result.get("replan_status")
    return response


@router.get("/readings", response_model=List[SensorReadingResponse])
def get_sensor_readings(
    bin_id: Optional[str] = None,
    validation_status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(SensorReading)
    if bin_id:
        query = query.filter(SensorReading.bin_id == bin_id)
    if validation_status:
        query = query.filter(SensorReading.validation_status == validation_status)
    return query.order_by(SensorReading.timestamp.desc()).limit(limit).all()

@router.get("/alerts", response_model=List[AlertResponse])
def get_sensor_alerts(
    status: Optional[str] = "ACTIVE",
    severity: Optional[str] = None,
    bin_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if status and status != "ALL":
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if bin_id:
        query = query.filter(Alert.bin_id == bin_id)
    return query.order_by(Alert.created_at.desc()).all()

@router.put("/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = AlertEngine.resolve_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert
