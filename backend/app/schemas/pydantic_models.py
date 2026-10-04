from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field

# --- Bins ---
class BinBase(BaseModel):
    bin_id: str
    location_name: str
    latitude: float
    longitude: float
    waste_type: str = "General"  # General, Recyclable, Organic
    capacity_liters: float = 1000.0
    current_fill_percent: float = 0.0
    current_weight_kg: float = 0.0
    sensor_id: Optional[str] = None
    collection_threshold_percent: float = 85.0
    operational_status: str = "OPERATIONAL"
    sensor_status: str = "HEALTHY"
    battery_level: Optional[float] = 100.0

class BinCreate(BinBase):
    pass

class BinUpdate(BaseModel):
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    waste_type: Optional[str] = None
    capacity_liters: Optional[float] = None
    current_fill_percent: Optional[float] = None
    current_weight_kg: Optional[float] = None
    collection_threshold_percent: Optional[float] = None
    operational_status: Optional[str] = None
    sensor_status: Optional[str] = None
    battery_level: Optional[float] = None

class BinResponse(BinBase):
    id: int
    last_sensor_reading: Optional[datetime] = None
    last_collection_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Sensors ---
class SensorReadingCreate(BaseModel):
    bin_id: str
    timestamp: Optional[datetime] = None
    fill_percent: float
    weight_kg: float
    temperature: Optional[float] = 24.0
    battery_level: Optional[float] = 100.0
    sensor_status: Optional[str] = "HEALTHY"

class SensorReadingResponse(BaseModel):
    id: int
    bin_id: str
    timestamp: datetime
    fill_percent: float
    weight_kg: float
    temperature: Optional[float]
    battery_level: Optional[float] = 100.0
    sensor_status: str
    validation_status: str
    validation_reason: Optional[str]

    class Config:
        from_attributes = True

# --- Vehicles ---
class VehicleBase(BaseModel):
    vehicle_id: str
    supported_waste_types: List[str] = Field(default_factory=lambda: ["General"])
    capacity_liters: float = 8000.0
    current_load_liters: float = 0.0
    latitude: float
    longitude: float
    status: str = "AVAILABLE"  # AVAILABLE, ASSIGNED, IN_TRANSIT, COLLECTING, MAINTENANCE, OFFLINE
    current_route_id: Optional[str] = None

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    supported_waste_types: Optional[List[str]] = None
    capacity_liters: Optional[float] = None
    current_load_liters: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    current_route_id: Optional[str] = None

class VehicleResponse(VehicleBase):
    id: int

    class Config:
        from_attributes = True

# --- Collections ---
class CollectionCreate(BaseModel):
    collection_id: Optional[str] = None
    bin_id: str
    vehicle_id: str
    route_id: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    estimated_volume: float
    operator_comment: Optional[str] = None

class CollectionUpdate(BaseModel):
    actual_collection_time: Optional[datetime] = None
    actual_volume: Optional[float] = None
    status: Optional[str] = None  # PLANNED, APPROVED, IN_PROGRESS, COLLECTED, VERIFIED, SKIPPED
    operator_comment: Optional[str] = None

class CollectionResponse(BaseModel):
    id: int
    collection_id: str
    bin_id: str
    vehicle_id: str
    route_id: Optional[str]
    scheduled_time: Optional[datetime]
    actual_collection_time: Optional[datetime]
    estimated_volume: float
    actual_volume: Optional[float]
    status: str
    operator_comment: Optional[str]

    class Config:
        from_attributes = True

# --- Route Stops and Routes ---
class RouteStopResponse(BaseModel):
    id: int
    route_id: str
    sequence: int
    bin_id: str
    estimated_arrival: Optional[datetime]
    collected: bool
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    waste_type: Optional[str] = None
    fill_percent: Optional[float] = None

    class Config:
        from_attributes = True

class RouteResponse(BaseModel):
    id: int
    route_id: str
    vehicle_id: str
    route_status: str
    total_distance_km: float
    estimated_duration_minutes: float
    optimization_score: float
    created_at: datetime
    approved_at: Optional[datetime]
    stops: List[RouteStopResponse] = []

    class Config:
        from_attributes = True

class RouteOptimizationRequest(BaseModel):
    planning_period_hours: int = 24
    waste_types: Optional[List[str]] = None
    allow_predictive_bins: bool = True
    bin_ids: Optional[List[str]] = None
    vehicle_ids: Optional[List[str]] = None
    depot_lat: Optional[float] = None
    depot_lng: Optional[float] = None
    save_to_db: Optional[bool] = True

class RouteReplanRequest(BaseModel):
    trigger_bin_id: str
    reason: str = "High priority surge detected"

# --- Forecasts ---
class ForecastResponse(BaseModel):
    id: int
    bin_id: str
    generated_at: datetime
    horizon_hours: int
    predicted_fill_percent: float
    threshold_crossing_time: Optional[datetime]
    model_name: str
    model_version: str
    prediction_type: str
    confidence_or_error_metric: float

    class Config:
        from_attributes = True

class ForecastRunRequest(BaseModel):
    bin_ids: Optional[List[str]] = None
    horizon_hours: int = 24

# --- Priorities ---
class PriorityItem(BaseModel):
    bin_id: str
    location_name: str
    waste_type: str
    current_fill_percent: float
    predicted_fill_percent: Optional[float] = None
    threshold_percent: float
    priority_level: str  # CRITICAL, HIGH, MEDIUM, LOW, SENSOR_VERIFICATION_REQUIRED
    score: float
    reason: str
    recommended_action: str
    threshold_crossing_hours: Optional[float] = None
    is_predictive_candidate: bool = False

class PriorityCalculateRequest(BaseModel):
    bin_ids: Optional[List[str]] = None

# --- Alerts ---
class AlertResponse(BaseModel):
    id: int
    bin_id: Optional[str]
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Recycling ---
class RecyclingRecordCreate(BaseModel):
    collection_id: str
    waste_type: str
    weight_kg: float
    recyclable_weight_kg: float
    contamination_weight_kg: float = 0.0

class RecyclingRecordResponse(RecyclingRecordCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class RecyclingAnalyticsResponse(BaseModel):
    total_waste_kg: float
    recyclable_kg: float
    organic_kg: float
    general_kg: float
    recycling_rate_percent: float
    average_contamination_percent: float
    waste_by_type: Dict[str, float]
    contamination_by_zone: Dict[str, float]
    trends: List[Dict[str, Any]]

# --- Agent Runs ---
class AgentRunResponse(BaseModel):
    id: int
    workflow_id: str
    agent_name: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    reasoning_summary: Optional[str]

    class Config:
        from_attributes = True

# --- Approvals ---
class ApprovalDecisionRequest(BaseModel):
    operator: str
    comment: Optional[str] = None

class ApprovalRequestResponse(BaseModel):
    id: int
    workflow_id: str
    proposed_plan: Dict[str, Any]
    status: str  # PENDING, APPROVED, REJECTED, REQUIRES_REPLAN
    operator: Optional[str]
    comment: Optional[str]
    created_at: datetime
    decided_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Workflows ---
class WorkflowRunRequest(BaseModel):
    notes: Optional[str] = "Automated municipal dispatch cycle"

class WorkflowRunResponse(BaseModel):
    id: int
    workflow_id: str
    current_state: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    requires_human_approval: bool
    agent_runs: List[AgentRunResponse] = []
    approval_request: Optional[ApprovalRequestResponse] = None

    class Config:
        from_attributes = True

# --- Dashboard & Reports ---
class DashboardKPIsResponse(BaseModel):
    total_bins: int
    bins_requiring_collection: int
    bins_above_threshold: Optional[int] = 0
    critical_bins: int
    high_priority_bins: Optional[int] = 0
    overflow_risk_bins: Optional[int] = 0
    overflow_incidents: int
    vehicles_available: int
    available_vehicles: Optional[int] = 0
    active_vehicles: int
    total_vehicles: Optional[int] = 0
    total_waste_collected_kg: float
    recycling_rate_percent: float
    average_route_distance_km: float
    collection_efficiency_percent: float
    sensor_failures: int
    average_vehicle_utilization_percent: float
    overflow_rate_percent: float
    active_alerts: Optional[int] = 0
    active_alerts_count: Optional[int] = 0
    completed_collections_count: Optional[int] = 0
    waste_type_distribution: Optional[Dict[str, Any]] = None
    priority_distribution: Optional[Dict[str, Any]] = None

class ReportGenerateRequest(BaseModel):
    period_days: int = 7
    title: Optional[str] = "Municipal Waste Collection & Recycling Optimization Audit Report"

class ReportResponse(BaseModel):
    report_id: str
    generated_at: datetime
    download_url: str
    summary: Dict[str, Any]
