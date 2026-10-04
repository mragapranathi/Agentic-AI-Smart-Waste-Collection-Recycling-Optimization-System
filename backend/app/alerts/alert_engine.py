from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Alert
from backend.app.core.logging import logger

class AlertEngine:
    @staticmethod
    def create_alert(
        db: Session,
        bin_id: Optional[str],
        alert_type: str,
        severity: str,
        message: str
    ) -> Alert:
        """
        Creates an operational alert if an active identical alert doesn't already exist.
        Alert types: OVERFLOW_RISK, THRESHOLD_EXCEEDED, SENSOR_STALE, SENSOR_INVALID,
                     SENSOR_SUSPICIOUS, VEHICLE_CAPACITY, VEHICLE_INCOMPATIBLE,
                     ROUTE_INFEASIBLE, REPLANNING_REQUIRED, COLLECTION_OVERDUE
        Severities: INFO, WARNING, HIGH, CRITICAL
        """
        existing = db.query(Alert).filter(
            Alert.bin_id == bin_id,
            Alert.alert_type == alert_type,
            Alert.status == "ACTIVE"
        ).first()

        if existing:
            # Update timestamp and message if active
            existing.message = message
            existing.severity = severity
            db.commit()
            db.refresh(existing)
            return existing

        alert = Alert(
            bin_id=bin_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            status="ACTIVE",
            created_at=datetime.utcnow()
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.warning(f"[ALERT] {severity} - {alert_type} for Bin '{bin_id}': {message}")
        return alert

    @staticmethod
    def resolve_alert(db: Session, alert_id: int) -> Optional[Alert]:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = "RESOLVED"
            alert.resolved_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)
            logger.info(f"[ALERT RESOLVED] Alert {alert_id} marked as resolved")
        return alert

    @staticmethod
    def resolve_alerts_for_bin(db: Session, bin_id: str, alert_types: Optional[list] = None):
        query = db.query(Alert).filter(Alert.bin_id == bin_id, Alert.status == "ACTIVE")
        if alert_types:
            query = query.filter(Alert.alert_type.in_(alert_types))
        alerts = query.all()
        for a in alerts:
            a.status = "RESOLVED"
            a.resolved_at = datetime.utcnow()
        if alerts:
            db.commit()
