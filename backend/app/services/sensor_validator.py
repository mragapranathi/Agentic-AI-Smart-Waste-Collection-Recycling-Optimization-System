from datetime import datetime, timezone
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Bin, SensorReading
from backend.app.alerts.alert_engine import AlertEngine
from backend.app.core.config import settings
from backend.app.core.logging import logger

class SensorValidator:
    @classmethod
    def validate_reading(
        cls,
        db: Session,
        bin_obj: Bin,
        fill_percent: float,
        weight_kg: float,
        reading_time: Optional[datetime] = None,
        battery_level: Optional[float] = 100.0
    ) -> Tuple[str, str, str]:
        """
        Validates incoming sensor readings against municipal IoT constraints.
        Returns: (validation_status, sensor_status, validation_reason)
        Validation statuses: VALID, SUSPICIOUS, INVALID, STALE, DUPLICATE
        Sensor statuses: HEALTHY, STALE, INVALID, SUSPICIOUS, OFFLINE
        """
        now = reading_time or datetime.utcnow()

        # 1. Impossible values check
        if fill_percent < 0.0 or fill_percent > 100.0:
            reason = f"Impossible fill level: {fill_percent:.1f}%. Expected range [0, 100]%."
            AlertEngine.create_alert(
                db, bin_obj.bin_id, "SENSOR_INVALID", "HIGH",
                f"Sensor error on {bin_obj.bin_id}: {reason}"
            )
            return "INVALID", "INVALID", reason

        if weight_kg < 0.0:
            reason = f"Impossible negative weight: {weight_kg:.1f} kg."
            AlertEngine.create_alert(
                db, bin_obj.bin_id, "SENSOR_INVALID", "HIGH",
                f"Sensor load error on {bin_obj.bin_id}: {reason}"
            )
            return "INVALID", "INVALID", reason

        if battery_level is not None and (battery_level < 0.0 or battery_level > 100.0):
            reason = f"Impossible battery level: {battery_level:.1f}%. Expected range [0, 100]%."
            AlertEngine.create_alert(
                db, bin_obj.bin_id, "SENSOR_INVALID", "HIGH",
                f"Battery reading error on {bin_obj.bin_id}: {reason}"
            )
            return "INVALID", "INVALID", reason

        # Check for low battery
        if battery_level is not None and battery_level < 20.0:
            AlertEngine.create_alert(
                db, bin_obj.bin_id, "LOW_BATTERY", "WARNING",
                f"Low battery warning on {bin_obj.bin_id}: {battery_level:.1f}% remaining."
            )

        # 2. Check previous reading for duplicates and sudden jumps
        last_reading = db.query(SensorReading).filter(
            SensorReading.bin_id == bin_obj.bin_id
        ).order_by(SensorReading.timestamp.desc()).first()

        if last_reading:
            # Check duplicate reading
            time_diff_sec = abs((now - last_reading.timestamp).total_seconds())
            if time_diff_sec < 5 and abs(last_reading.fill_percent - fill_percent) < 0.01:
                reason = f"Duplicate sensor payload within {time_diff_sec:.1f} seconds."
                return "DUPLICATE", bin_obj.sensor_status or "HEALTHY", reason

            # Sudden change detection:
            # E.g., 40% -> 99% in 1 minute (delta >= 35% within 10 minutes)
            delta_fill = fill_percent - last_reading.fill_percent
            delta_minutes = time_diff_sec / 60.0

            if delta_minutes <= 15.0 and delta_fill >= settings.SUDDEN_CHANGE_THRESHOLD:
                reason = (
                    f"Sudden unrealistic increase: {last_reading.fill_percent:.1f}% -> {fill_percent:.1f}% "
                    f"in {delta_minutes:.1f} min ({delta_fill:+.1f}% jump). Possible sensor anomaly."
                )
                AlertEngine.create_alert(
                    db, bin_obj.bin_id, "SENSOR_SUSPICIOUS", "WARNING",
                    f"Suspicious reading on {bin_obj.bin_id}: {reason}"
                )
                return "SUSPICIOUS", "SUSPICIOUS", reason

        # 3. Check for stale sensor condition
        if bin_obj.last_sensor_reading:
            stale_hours = (now - bin_obj.last_sensor_reading).total_seconds() / 3600.0
            if stale_hours > settings.STALE_SENSOR_HOURS:
                logger.warning(f"Sensor on bin {bin_obj.bin_id} was stale ({stale_hours:.1f}h since update)")

        # 4. Valid reading processing
        validation_status = "VALID"
        sensor_status = "HEALTHY"
        reason = "Reading passed all physical and rate-of-change validation rules."

        # Trigger threshold or overflow alerts on valid readings
        if fill_percent >= 95.0:
            AlertEngine.create_alert(
                db, bin_obj.bin_id, "OVERFLOW_RISK", "CRITICAL",
                f"Critical overflow risk: Bin {bin_obj.bin_id} is at {fill_percent:.1f}% fill capacity!"
            )
        elif fill_percent >= bin_obj.collection_threshold_percent:
            AlertEngine.create_alert(
                db, bin_obj.bin_id, "THRESHOLD_EXCEEDED", "HIGH",
                f"Collection threshold reached: Bin {bin_obj.bin_id} is at {fill_percent:.1f}% "
                f"(Threshold: {bin_obj.collection_threshold_percent:.1f}%)."
            )

        return validation_status, sensor_status, reason
