from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Bin(Base):
    __tablename__ = "bins"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(String(50), unique=True, index=True, nullable=False)
    location_name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    waste_type = Column(String(50), nullable=False, default="General")  # General, Recyclable, Organic
    capacity_liters = Column(Float, nullable=False, default=1000.0)
    current_fill_percent = Column(Float, nullable=False, default=0.0)
    current_weight_kg = Column(Float, nullable=False, default=0.0)
    sensor_id = Column(String(100), nullable=True)
    collection_threshold_percent = Column(Float, nullable=False, default=85.0)
    operational_status = Column(String(50), nullable=False, default="OPERATIONAL")  # OPERATIONAL, MAINTENANCE, DECOMMISSIONED
    sensor_status = Column(String(50), nullable=False, default="HEALTHY")  # HEALTHY, STALE, INVALID, SUSPICIOUS, OFFLINE
    battery_level = Column(Float, nullable=True, default=100.0)
    last_sensor_reading = Column(DateTime, nullable=True)
    last_collection_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    readings = relationship("SensorReading", back_populates="bin", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="bin", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="bin", cascade="all, delete-orphan")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(String(50), ForeignKey("bins.bin_id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    fill_percent = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True, default=24.0)
    battery_level = Column(Float, nullable=True, default=100.0)
    sensor_status = Column(String(50), default="HEALTHY")
    validation_status = Column(String(50), default="VALID")  # VALID, SUSPICIOUS, INVALID, STALE, DUPLICATE
    validation_reason = Column(Text, nullable=True)

    bin = relationship("Bin", back_populates="readings")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String(50), unique=True, index=True, nullable=False)
    supported_waste_types = Column(JSON, nullable=False, default=list)  # e.g. ["General", "Recyclable"]
    capacity_liters = Column(Float, nullable=False, default=8000.0)
    current_load_liters = Column(Float, nullable=False, default=0.0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default="AVAILABLE")  # AVAILABLE, ASSIGNED, IN_TRANSIT, COLLECTING, MAINTENANCE, OFFLINE
    current_route_id = Column(String(50), nullable=True)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(String(50), unique=True, index=True, nullable=False)
    bin_id = Column(String(50), nullable=False, index=True)
    vehicle_id = Column(String(50), nullable=False, index=True)
    route_id = Column(String(50), nullable=True, index=True)
    scheduled_time = Column(DateTime, default=datetime.utcnow)
    actual_collection_time = Column(DateTime, nullable=True)
    estimated_volume = Column(Float, nullable=False, default=0.0)
    actual_volume = Column(Float, nullable=True)
    status = Column(String(50), default="PLANNED")  # PLANNED, APPROVED, IN_PROGRESS, COLLECTED, VERIFIED, SKIPPED
    operator_comment = Column(Text, nullable=True)


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), unique=True, index=True, nullable=False)
    vehicle_id = Column(String(50), nullable=False, index=True)
    route_status = Column(String(50), default="PLANNED")  # PLANNED, APPROVED, IN_PROGRESS, COMPLETED, CANCELLED
    total_distance_km = Column(Float, default=0.0)
    estimated_duration_minutes = Column(Float, default=0.0)
    optimization_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence")


class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), ForeignKey("routes.route_id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    bin_id = Column(String(50), nullable=False, index=True)
    estimated_arrival = Column(DateTime, nullable=True)
    collected = Column(Boolean, default=False)

    route = relationship("Route", back_populates="stops")


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(String(50), ForeignKey("bins.bin_id"), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    horizon_hours = Column(Integer, default=24)
    predicted_fill_percent = Column(Float, nullable=False)
    threshold_crossing_time = Column(DateTime, nullable=True)
    model_name = Column(String(100), default="RandomForestRegressor")
    model_version = Column(String(50), default="v1.0")
    prediction_type = Column(String(50), default="ML_PREDICTION")  # CURRENT_SENSOR, BASELINE_ESTIMATE, ML_PREDICTION
    confidence_or_error_metric = Column(Float, default=0.0)

    bin = relationship("Bin", back_populates="forecasts")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(String(50), ForeignKey("bins.bin_id"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)  # OVERFLOW_RISK, THRESHOLD_EXCEEDED, SENSOR_STALE, SENSOR_INVALID, SENSOR_SUSPICIOUS, etc.
    severity = Column(String(20), nullable=False, default="INFO")  # INFO, WARNING, HIGH, CRITICAL
    message = Column(Text, nullable=False)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, ACKNOWLEDGED, RESOLVED
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    bin = relationship("Bin", back_populates="alerts")


class RecyclingRecord(Base):
    __tablename__ = "recycling_records"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(String(50), nullable=False, index=True)
    waste_type = Column(String(50), nullable=False)
    weight_kg = Column(Float, nullable=False)
    recyclable_weight_kg = Column(Float, nullable=False)
    contamination_weight_kg = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(100), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    status = Column(String(50), default="SUCCESS")  # RUNNING, SUCCESS, FAILED, SKIPPED
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    reasoning_summary = Column(Text, nullable=True)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(100), nullable=False, index=True)
    proposed_plan = Column(JSON, nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED, REQUIRES_REPLAN
    operator = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(100), unique=True, index=True, nullable=False)
    current_state = Column(String(50), default="INITIATED")
    status = Column(String(50), default="RUNNING")  # RUNNING, WAITING_APPROVAL, COMPLETED, FAILED, REJECTED
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    requires_human_approval = Column(Boolean, default=True)
