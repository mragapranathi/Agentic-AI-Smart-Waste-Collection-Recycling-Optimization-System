from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseAgent
from backend.app.models.entities import Bin, SensorReading
from backend.app.services.sensor_validator import SensorValidator
from backend.app.alerts.alert_engine import AlertEngine
from backend.app.core.config import settings
from backend.app.core.logging import logger

# How long without a reading before a sensor is flagged STALE (hours)
STALE_SENSOR_THRESHOLD_HOURS = getattr(settings, "STALE_SENSOR_HOURS", 4.0)

# Max physically plausible fill delta between two consecutive valid readings (% per minute)
MAX_PLAUSIBLE_FILL_RATE_PER_MIN = 5.0  # >5%/min in a waste bin is physically impossible

# Required fields that must be present for a bin to be considered fully configured
REQUIRED_BIN_FIELDS = ["bin_id", "location_name", "capacity_liters", "current_fill_percent",
                       "latitude", "longitude", "waste_type", "collection_threshold_percent"]


class BinMonitoringAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Smart Bin Monitoring Agent",
            role="Validates IoT telemetry, detects anomalies, and tracks real-time fill states"
        )

    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        bins = db.query(Bin).filter(Bin.operational_status == "OPERATIONAL").all()
        now = datetime.utcnow()

        monitored_results = []
        valid_count = 0
        anomaly_count = 0

        # Categorised finding lists surfaced in agent output
        missing_info_bins: List[Dict] = []   # Bins with null / incomplete configuration
        stale_sensor_bins: List[Dict] = []   # Bins that have not reported recently
        unrealistic_bins: List[Dict] = []    # Bins whose current DB values are physically impossible

        for b in bins:
            issues: List[str] = []
            issue_codes: List[str] = []

            # ─────────────────────────────────────────────────────────────────
            # CHECK 1 — MISSING SENSOR INFORMATION
            # Identify bins that are missing critical configuration or readings
            # ─────────────────────────────────────────────────────────────────
            missing_fields = []
            if b.capacity_liters is None or b.capacity_liters <= 0:
                missing_fields.append("capacity_liters")
            if b.current_fill_percent is None:
                missing_fields.append("current_fill_percent")
            if b.latitude is None or b.longitude is None:
                missing_fields.append("coordinates (lat/lng)")
            if not b.waste_type:
                missing_fields.append("waste_type")
            if b.collection_threshold_percent is None:
                missing_fields.append("collection_threshold_percent")
            if b.last_sensor_reading is None:
                missing_fields.append("last_sensor_reading (never reported)")

            if missing_fields:
                detail = f"Missing sensor/config fields: {', '.join(missing_fields)}."
                issues.append(detail)
                issue_codes.append("MISSING_INFO")
                missing_info_bins.append({
                    "bin_id": b.bin_id,
                    "location_name": b.location_name,
                    "missing_fields": missing_fields,
                    "detail": detail
                })
                # Raise an alert so operators are notified
                AlertEngine.create_alert(
                    db, b.bin_id, "SENSOR_INVALID", "HIGH",
                    f"Bin {b.bin_id} has incomplete sensor/configuration data: {detail}"
                )
                logger.warning(f"[BinMonitoringAgent] {b.bin_id} — {detail}")

            # ─────────────────────────────────────────────────────────────────
            # CHECK 2 — STALE SENSOR DETECTION
            # A sensor is stale if it hasn't transmitted within the configured window
            # ─────────────────────────────────────────────────────────────────
            stale_hours = None
            if b.last_sensor_reading is not None:
                stale_hours = (now - b.last_sensor_reading).total_seconds() / 3600.0
                if stale_hours > STALE_SENSOR_THRESHOLD_HOURS:
                    detail = (
                        f"Sensor last reported {stale_hours:.1f}h ago "
                        f"(threshold: {STALE_SENSOR_THRESHOLD_HOURS}h). "
                        f"Connectivity or hardware failure suspected."
                    )
                    issues.append(detail)
                    issue_codes.append("STALE_SENSOR")
                    stale_sensor_bins.append({
                        "bin_id": b.bin_id,
                        "location_name": b.location_name,
                        "hours_since_last_reading": round(stale_hours, 1),
                        "last_sensor_reading": b.last_sensor_reading.isoformat() if b.last_sensor_reading else None,
                        "detail": detail
                    })
                    # Update bin sensor_status in DB to reflect stale state
                    if b.sensor_status not in ("STALE", "INVALID", "OFFLINE"):
                        b.sensor_status = "STALE"
                    AlertEngine.create_alert(
                        db, b.bin_id, "SENSOR_STALE", "WARNING",
                        f"Stale sensor on {b.bin_id}: no reading for {stale_hours:.1f}h."
                    )
                    logger.warning(f"[BinMonitoringAgent] {b.bin_id} — STALE ({stale_hours:.1f}h silent)")

            # ─────────────────────────────────────────────────────────────────
            # CHECK 3 — UNREALISTIC MEASUREMENT DETECTION
            # Audit the existing fill % and recent reading history for physical impossibilities
            # ─────────────────────────────────────────────────────────────────
            fill = b.current_fill_percent

            # 3a. Impossible fill range
            if fill is not None and (fill < 0.0 or fill > 100.0):
                detail = f"Impossible fill level in database: {fill:.1f}%. Valid range is [0, 100]%."
                issues.append(detail)
                issue_codes.append("UNREALISTIC_FILL")
                unrealistic_bins.append({
                    "bin_id": b.bin_id, "location_name": b.location_name,
                    "current_fill_percent": fill, "detail": detail
                })
                if b.sensor_status not in ("INVALID", "OFFLINE"):
                    b.sensor_status = "INVALID"
                AlertEngine.create_alert(
                    db, b.bin_id, "SENSOR_INVALID", "HIGH",
                    f"Bin {b.bin_id} has impossible stored fill level: {fill:.1f}%."
                )

            # 3b. Unrealistic fill growth rate between consecutive readings
            readings = (
                db.query(SensorReading)
                .filter(SensorReading.bin_id == b.bin_id)
                .order_by(SensorReading.timestamp.desc())
                .limit(3)
                .all()
            )

            if len(readings) >= 2:
                r_new, r_old = readings[0], readings[1]
                delta_fill = r_new.fill_percent - r_old.fill_percent
                delta_minutes = max(0.01, (r_new.timestamp - r_old.timestamp).total_seconds() / 60.0)
                rate_per_min = delta_fill / delta_minutes

                if rate_per_min > MAX_PLAUSIBLE_FILL_RATE_PER_MIN:
                    detail = (
                        f"Unrealistic fill growth rate: {r_old.fill_percent:.1f}% -> {r_new.fill_percent:.1f}% "
                        f"in {delta_minutes:.1f} min ({rate_per_min:.2f}%/min, max plausible: "
                        f"{MAX_PLAUSIBLE_FILL_RATE_PER_MIN}%/min). Sensor spike suspected."
                    )
                    issues.append(detail)
                    issue_codes.append("UNREALISTIC_RATE")
                    if not any(u["bin_id"] == b.bin_id for u in unrealistic_bins):
                        unrealistic_bins.append({
                            "bin_id": b.bin_id, "location_name": b.location_name,
                            "current_fill_percent": fill,
                            "growth_rate_per_min": round(rate_per_min, 3),
                            "detail": detail
                        })
                    if b.sensor_status not in ("SUSPICIOUS", "INVALID", "OFFLINE"):
                        b.sensor_status = "SUSPICIOUS"
                    AlertEngine.create_alert(
                        db, b.bin_id, "SENSOR_SUSPICIOUS", "WARNING",
                        f"Suspicious growth rate on {b.bin_id}: {detail}"
                    )

            # 3c. Fill higher than capacity allows (cross-check with weight if available)
            if fill is not None and fill > 100.0:
                # Already caught by 3a, but re-tag for unrealistic list
                pass
            elif readings and fill is not None:
                latest = readings[0]
                if latest.weight_kg is not None and b.capacity_liters is not None:
                    # Average waste density ~0.15 kg/L (general), organic ~0.25 kg/L
                    density = 0.25 if b.waste_type == "Organic" else 0.15
                    max_expected_weight = b.capacity_liters * density
                    if latest.weight_kg > max_expected_weight * 1.5:  # 50% margin
                        detail = (
                            f"Weight {latest.weight_kg:.1f}kg exceeds max plausible "
                            f"{max_expected_weight * 1.5:.1f}kg for a {b.capacity_liters}L {b.waste_type} bin."
                        )
                        issues.append(detail)
                        issue_codes.append("UNREALISTIC_WEIGHT")
                        if not any(u["bin_id"] == b.bin_id for u in unrealistic_bins):
                            unrealistic_bins.append({
                                "bin_id": b.bin_id, "location_name": b.location_name,
                                "current_fill_percent": fill,
                                "weight_kg": latest.weight_kg,
                                "detail": detail
                            })

            # ─────────────────────────────────────────────────────────────────
            # Aggregate result for this bin
            # ─────────────────────────────────────────────────────────────────
            latest_reading = readings[0] if readings else None
            val_status = latest_reading.validation_status if latest_reading else "NO_READING"
            s_status = b.sensor_status or "UNKNOWN"

            has_issue = bool(issues)
            if not has_issue and s_status == "HEALTHY" and val_status == "VALID":
                valid_count += 1
            else:
                anomaly_count += 1

            monitored_results.append({
                "bin_id": b.bin_id,
                "location_name": b.location_name,
                "waste_type": b.waste_type,
                "fill_percent": fill,
                "capacity_liters": b.capacity_liters,
                "sensor_status": s_status,
                "validation_status": val_status,
                "collection_threshold": b.collection_threshold_percent,
                "hours_since_last_reading": round(stale_hours, 1) if stale_hours is not None else None,
                "issue_codes": issue_codes,
                "issues": issues
            })

        # Commit any sensor_status updates made during this audit
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[BinMonitoringAgent] Failed to persist sensor status updates: {e}")

        reasoning = (
            f"Audited {len(bins)} operational smart bins. "
            f"{valid_count} sensors reporting nominal telemetry. "
            f"{len(missing_info_bins)} bins have missing/incomplete sensor information. "
            f"{len(stale_sensor_bins)} sensors are stale (silent >{STALE_SENSOR_THRESHOLD_HOURS}h). "
            f"{len(unrealistic_bins)} bins have physically unrealistic measurements. "
            f"Total anomalies: {anomaly_count}."
        )

        logger.info(f"[BinMonitoringAgent] {reasoning}")

        return {
            "monitored_bins": monitored_results,
            "total_monitored": len(bins),
            "healthy_count": valid_count,
            "anomaly_count": anomaly_count,
            "missing_info_bins": missing_info_bins,
            "stale_sensor_bins": stale_sensor_bins,
            "unrealistic_measurement_bins": unrealistic_bins,
        }, reasoning
