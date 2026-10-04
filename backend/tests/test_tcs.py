from datetime import datetime, timedelta
from backend.app.models.entities import Bin, Vehicle, SensorReading, Collection, Route, RouteStop, Forecast, RecyclingRecord
from backend.app.services.priority_engine import PriorityEngine
from backend.app.services.sensor_validator import SensorValidator
from backend.app.optimization.constraints import RoutingConstraints
from backend.app.optimization.vrp_solver import VRPOptimizer
from backend.app.optimization.validator import RouteValidator
from backend.app.services.replanning_service import ReplanningService

def test_tc01_bin_reaches_92_percent(db_session):
    """TC-01: Bin reaches 92% fill level -> Expected: HIGH or CRITICAL priority."""
    bin_obj = Bin(
        bin_id="BIN-TC01",
        location_name="Zone A - Commercial Hub",
        latitude=12.9716,
        longitude=77.5946,
        waste_type="General",
        capacity_liters=1000.0,
        current_fill_percent=92.0,
        current_weight_kg=200.0,
        collection_threshold_percent=85.0,
        operational_status="OPERATIONAL",
        sensor_status="HEALTHY"
    )
    db_session.add(bin_obj)
    db_session.commit()

    p_result = PriorityEngine.calculate_bin_priority(bin_obj)
    assert p_result["priority_level"] in ("HIGH", "CRITICAL")
    assert p_result["score"] >= 65.0
    assert "threshold" in p_result["reason"].lower() or "hazard" in p_result["reason"].lower()

def test_tc02_predictive_collection_threshold_crossing(db_session):
    """TC-02: Bin at 70%, forecast exceeds threshold before next collection -> Expected: Predictive collection recommendation."""
    bin_obj = Bin(
        bin_id="BIN-TC02",
        location_name="Zone C - Tech Park",
        latitude=12.9800,
        longitude=77.6000,
        waste_type="General",
        capacity_liters=1000.0,
        current_fill_percent=70.0,
        current_weight_kg=150.0,
        collection_threshold_percent=85.0,
        operational_status="OPERATIONAL",
        sensor_status="HEALTHY"
    )
    db_session.add(bin_obj)
    db_session.commit()

    # Create forecast projecting threshold crossing in 14 hours
    now = datetime.utcnow()
    forecast = Forecast(
        bin_id="BIN-TC02",
        generated_at=now,
        horizon_hours=24,
        predicted_fill_percent=92.0,
        threshold_crossing_time=now + timedelta(hours=14),
        model_name="RandomForestRegressor",
        model_version="v1.0",
        prediction_type="ML_PREDICTION",
        confidence_or_error_metric=1.64
    )
    db_session.add(forecast)
    db_session.commit()

    p_result = PriorityEngine.calculate_bin_priority(bin_obj, forecast=forecast, planning_period_hours=24)
    assert p_result["is_predictive_candidate"] is True
    assert p_result["priority_level"] in ("HIGH", "MEDIUM")
    assert "predictive alert" in p_result["reason"].lower()

def test_tc03_sudden_sensor_jump_anomalous_reading(db_session):
    """TC-03: Sensor changes from 40% to 99% in one minute -> Expected: Sensor verification triggered (SUSPICIOUS status)."""
    bin_obj = Bin(
        bin_id="BIN-TC03",
        location_name="Zone D - Industrial",
        latitude=12.9500,
        longitude=77.5800,
        waste_type="General",
        capacity_liters=1000.0,
        current_fill_percent=40.0,
        current_weight_kg=88.0,
        collection_threshold_percent=85.0,
        operational_status="OPERATIONAL",
        sensor_status="HEALTHY"
    )
    db_session.add(bin_obj)
    db_session.commit()

    # Initial reading 1 minute ago
    t0 = datetime.utcnow() - timedelta(minutes=1)
    r0 = SensorReading(
        bin_id="BIN-TC03",
        timestamp=t0,
        fill_percent=40.0,
        weight_kg=88.0,
        temperature=25.0,
        sensor_status="HEALTHY",
        validation_status="VALID",
        validation_reason="Initial reading"
    )
    db_session.add(r0)
    db_session.commit()

    # Sudden jump reading: 40% -> 99% in 1 minute
    t1 = datetime.utcnow()
    val_status, s_status, reason = SensorValidator.validate_reading(
        db=db_session,
        bin_obj=bin_obj,
        fill_percent=99.0,
        weight_kg=120.0,
        reading_time=t1
    )

    assert val_status == "SUSPICIOUS"
    assert s_status == "SUSPICIOUS"
    assert "sudden unrealistic increase" in reason.lower()

    # Check priority evaluation for flagged sensor
    bin_obj.sensor_status = "SUSPICIOUS"
    p_result = PriorityEngine.calculate_bin_priority(bin_obj)
    assert p_result["priority_level"] == "SENSOR_VERIFICATION_REQUIRED"

def test_tc04_multiple_high_priority_bins_optimized_route(db_session):
    """TC-04: Multiple high-priority bins -> Expected: Optimized CVRP route generated with Google OR-Tools."""
    bins = [
        Bin(bin_id="BIN-001", location_name="Loc 1", latitude=12.980, longitude=77.600, waste_type="General", capacity_liters=1000, current_fill_percent=92, current_weight_kg=200),
        Bin(bin_id="BIN-003", location_name="Loc 2", latitude=12.960, longitude=77.610, waste_type="General", capacity_liters=1000, current_fill_percent=87, current_weight_kg=190),
        Bin(bin_id="BIN-006", location_name="Loc 3", latitude=12.985, longitude=77.590, waste_type="General", capacity_liters=1000, current_fill_percent=88, current_weight_kg=195),
    ]
    vehicle = Vehicle(
        vehicle_id="TRUCK-01",
        supported_waste_types=["General"],
        capacity_liters=8000.0,
        current_load_liters=0.0,
        latitude=12.9716,
        longitude=77.5946,
        status="AVAILABLE"
    )
    for b in bins:
        db_session.add(b)
    db_session.add(vehicle)
    db_session.commit()

    priorities = {
        b.bin_id: {"priority_level": "CRITICAL", "score": 90.0}
        for b in bins
    }

    result = VRPOptimizer.optimize_routes(
        bins_to_collect=bins,
        available_vehicles=[vehicle],
        priorities=priorities
    )

    assert len(result["routes"]) == 1
    route = result["routes"][0]
    assert route["vehicle_id"] == "TRUCK-01"
    assert len(route["stops"]) == 3
    assert route["total_distance_km"] > 0
    assert route["capacity_utilization_percent"] > 0
    assert len(result["unassigned_bins"]) == 0

def test_tc05_vehicle_lacks_remaining_capacity(db_session):
    """TC-05: Vehicle lacks remaining capacity -> Expected: Assignment prevented."""
    vehicle = Vehicle(
        vehicle_id="TRUCK-FULL",
        supported_waste_types=["General"],
        capacity_liters=8000.0,
        current_load_liters=7500.0,  # Only 500L remaining
        latitude=12.9716,
        longitude=77.5946,
        status="AVAILABLE"
    )
    bin_obj = Bin(
        bin_id="BIN-LARGE",
        location_name="Large Depot",
        latitude=12.9750,
        longitude=77.5950,
        waste_type="General",
        capacity_liters=1000.0,
        current_fill_percent=90.0,
        current_weight_kg=200.0
    )

    # Required volume is 900L, available is 500L
    required_volume = 900.0
    can_fit = RoutingConstraints.can_accommodate_volume(vehicle, required_volume)
    is_valid, msg = RoutingConstraints.validate_assignment(vehicle, bin_obj, required_volume)

    assert can_fit is False
    assert is_valid is False
    assert "capacity overflow" in msg.lower()

def test_tc06_vehicle_incompatible_waste_type(db_session):
    """TC-06: Vehicle incompatible with waste type -> Expected: Assignment prevented."""
    vehicle = Vehicle(
        vehicle_id="TRUCK-REC",
        supported_waste_types=["Recyclable"],  # Only accepts recyclables
        capacity_liters=6000.0,
        current_load_liters=0.0,
        latitude=12.9716,
        longitude=77.5946,
        status="AVAILABLE"
    )
    bin_obj = Bin(
        bin_id="BIN-ORG",
        location_name="Compost Center",
        latitude=12.9750,
        longitude=77.5950,
        waste_type="Organic",  # Incompatible with Recyclable
        capacity_liters=800.0,
        current_fill_percent=95.0,
        current_weight_kg=300.0
    )

    is_compatible = RoutingConstraints.is_waste_compatible(vehicle, bin_obj.waste_type)
    is_valid, msg = RoutingConstraints.validate_assignment(vehicle, bin_obj, 760.0)

    assert is_compatible is False
    assert is_valid is False
    assert "waste type mismatch" in msg.lower()

def test_tc07_dynamic_route_replanning_surge_bin(db_session):
    """TC-07: New critical bin appears during active route -> Expected: Dynamic replanning triggered with detour & approval request."""
    # Active Route
    vehicle = Vehicle(
        vehicle_id="TRUCK-01",
        supported_waste_types=["General"],
        capacity_liters=8000.0,
        current_load_liters=0.0,
        latitude=12.9716,
        longitude=77.5946,
        status="ASSIGNED"
    )
    route = Route(
        route_id="RT-ACTIVE-01",
        vehicle_id="TRUCK-01",
        route_status="APPROVED",
        total_distance_km=8.5,
        estimated_duration_minutes=35.0,
        optimization_score=0.9
    )
    b1 = Bin(bin_id="BIN-001", location_name="Stop 1", latitude=12.980, longitude=77.600, waste_type="General", capacity_liters=1000, current_fill_percent=90)
    b2 = Bin(bin_id="BIN-003", location_name="Stop 2", latitude=12.960, longitude=77.610, waste_type="General", capacity_liters=1000, current_fill_percent=88)

    # Surge bin BIN-010 (was 62%, now surges to 95%)
    b_surge = Bin(bin_id="BIN-010", location_name="Surge Stop", latitude=12.970, longitude=77.605, waste_type="General", capacity_liters=1000, current_fill_percent=95)

    db_session.add_all([vehicle, route, b1, b2, b_surge])
    db_session.commit()

    s1 = RouteStop(route_id="RT-ACTIVE-01", sequence=1, bin_id="BIN-001")
    s2 = RouteStop(route_id="RT-ACTIVE-01", sequence=2, bin_id="BIN-003")
    db_session.add_all([s1, s2])
    db_session.commit()

    # Trigger dynamic replan
    replan_res = ReplanningService.evaluate_and_replan(db_session, trigger_bin_id="BIN-010")
    assert replan_res["success"] is True
    plan = replan_res["proposed_plan"]

    assert plan["replan_type"] == "SURGE_STOP_INSERTION"
    assert plan["status"] == "PENDING_HUMAN_APPROVAL"
    assert plan["detour_km"] > 0
    assert plan["new_distance_km"] > plan["old_distance_km"]
    assert len(plan["new_stops"]) == 3

    # Human Operator Approves Replan
    apply_res = ReplanningService.apply_replan(db_session, approval_id=replan_res["approval_id"], operator="Chief Dispatcher")
    assert apply_res["success"] is True

    # Assert active route updated in DB
    updated_stops = db_session.query(RouteStop).filter(RouteStop.route_id == "RT-ACTIVE-01").all()
    assert len(updated_stops) == 3
    assert any(s.bin_id == "BIN-010" for s in updated_stops)

def test_tc08_collection_completed_state_updates(client, db_session):
    """TC-08: Collection completed -> Expected: Bin and vehicle state updated."""
    bin_obj = Bin(
        bin_id="BIN-TC08",
        location_name="Zone B Center",
        latitude=12.9716,
        longitude=77.5946,
        waste_type="Recyclable",
        capacity_liters=1000.0,
        current_fill_percent=88.0,
        current_weight_kg=120.0,
        collection_threshold_percent=85.0
    )
    vehicle = Vehicle(
        vehicle_id="TRUCK-REC-01",
        supported_waste_types=["Recyclable"],
        capacity_liters=6000.0,
        current_load_liters=1000.0,
        latitude=12.9716,
        longitude=77.5946,
        status="COLLECTING"
    )
    coll = Collection(
        collection_id="COL-TC08-01",
        bin_id="BIN-TC08",
        vehicle_id="TRUCK-REC-01",
        estimated_volume=880.0,
        status="PLANNED"
    )
    db_session.add_all([bin_obj, vehicle, coll])
    db_session.commit()

    # Mark collection completed via API endpoint
    response = client.put(f"/api/collections/COL-TC08-01", json={"status": "COLLECTED", "actual_volume": 880.0})
    assert response.status_code == 200

    # Refresh objects from DB
    db_session.refresh(bin_obj)
    db_session.refresh(vehicle)
    db_session.refresh(coll)

    assert coll.status == "COLLECTED"
    assert bin_obj.current_fill_percent == 0.0
    assert bin_obj.current_weight_kg == 0.0
    assert bin_obj.last_collection_time is not None
    assert vehicle.current_load_liters == 1880.0  # 1000 + 880

    # Verify recycling record was generated
    rec_rec = db_session.query(RecyclingRecord).filter(RecyclingRecord.collection_id == "COL-TC08-01").first()
    assert rec_rec is not None
    assert rec_rec.recyclable_weight_kg > 0
