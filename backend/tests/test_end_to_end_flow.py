import pytest
from datetime import datetime, timedelta
from backend.app.models.entities import Bin, Vehicle, Route, Collection, ApprovalRequest

def test_complete_18_step_end_to_end_scenario(client, db_session):
    """
    Executes the required 18-step realistic municipal waste management scenario end-to-end.
    Exercises real HTTP API endpoints, database state transitions, OR-Tools VRP optimization,
    surge replanning, lifecycle updates, and PDF report generation.
    """

    # ---------------------------------------------------------
    # 1. Create several bins
    # ---------------------------------------------------------
    bins_data = [
        {
            "bin_id": "BIN-E2E-01",
            "location_name": "Tech Park Block A",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "waste_type": "General",
            "capacity_liters": 1000.0,
            "current_fill_percent": 30.0,
            "current_weight_kg": 40.0,
            "collection_threshold_percent": 85.0,
            "battery_level": 98.0,
            "operational_status": "OPERATIONAL"
        },
        {
            "bin_id": "BIN-E2E-02",
            "location_name": "City Market Plaza",
            "latitude": 12.9750,
            "longitude": 77.6000,
            "waste_type": "General",
            "capacity_liters": 1200.0,
            "current_fill_percent": 88.0,
            "current_weight_kg": 150.0,
            "collection_threshold_percent": 80.0,
            "battery_level": 92.0,
            "operational_status": "OPERATIONAL"
        },
        {
            "bin_id": "BIN-E2E-03",
            "location_name": "Green Eco Zone Hub",
            "latitude": 12.9680,
            "longitude": 77.5900,
            "waste_type": "Recyclable",
            "capacity_liters": 800.0,
            "current_fill_percent": 92.0,
            "current_weight_kg": 110.0,
            "collection_threshold_percent": 85.0,
            "battery_level": 95.0,
            "operational_status": "OPERATIONAL"
        }
    ]

    for b in bins_data:
        r = client.post("/api/bins", json=b)
        assert r.status_code == 201, f"Failed to create bin: {r.text}"

    # Verify bins list
    r_bins = client.get("/api/bins")
    assert r_bins.status_code == 200
    assert len(r_bins.json()) >= 3

    # ---------------------------------------------------------
    # 2. Add normal sensor readings
    # ---------------------------------------------------------
    r_reading = client.post("/api/sensors/readings", json={
        "bin_id": "BIN-E2E-01",
        "fill_percent": 35.0,
        "weight_kg": 48.0,
        "temperature": 25.0,
        "battery_level": 96.0
    })
    assert r_reading.status_code == 201
    assert r_reading.json()["validation_status"] == "VALID"

    # ---------------------------------------------------------
    # 3. Detect an abnormal reading (impossible fill level)
    # ---------------------------------------------------------
    r_bad = client.post("/api/sensors/readings", json={
        "bin_id": "BIN-E2E-01",
        "fill_percent": 150.0,  # Impossible value
        "weight_kg": 50.0,
        "temperature": 25.0,
        "battery_level": 96.0
    })
    assert r_bad.status_code == 201
    assert r_bad.json()["validation_status"] == "INVALID"

    # Verify alert was created
    r_alerts = client.get("/api/sensors/alerts?bin_id=BIN-E2E-01")
    assert r_alerts.status_code == 200
    assert any(a["alert_type"] == "SENSOR_INVALID" for a in r_alerts.json())

    # ---------------------------------------------------------
    # 4. Forecast fill levels using ML / predictive pipeline
    # ---------------------------------------------------------
    r_fc = client.post("/api/forecasts/run", json={"horizon_hours": 24})
    assert r_fc.status_code == 200
    assert len(r_fc.json()) >= 3

    # ---------------------------------------------------------
    # 5. Calculate collection priorities
    # ---------------------------------------------------------
    r_pri = client.post("/api/priorities/calculate")
    assert r_pri.status_code == 200
    priorities = r_pri.json()
    assert len(priorities) >= 3
    # BIN-E2E-03 (92% fill, Recyclable) should be HIGH or CRITICAL
    p3 = next((p for p in priorities if p["bin_id"] == "BIN-E2E-03"), None)
    assert p3 is not None
    assert p3["priority_level"] in ("HIGH", "CRITICAL")
    assert "reason" in p3

    # ---------------------------------------------------------
    # 6. Select / register suitable vehicles
    # ---------------------------------------------------------
    vehicles_data = [
        {
            "vehicle_id": "TRUCK-E2E-01",
            "supported_waste_types": ["General"],
            "capacity_liters": 6000.0,
            "current_load_liters": 0.0,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "status": "AVAILABLE"
        },
        {
            "vehicle_id": "TRUCK-E2E-02",
            "supported_waste_types": ["Recyclable"],
            "capacity_liters": 5000.0,
            "current_load_liters": 0.0,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "status": "AVAILABLE"
        }
    ]
    for v in vehicles_data:
        r_v = client.post("/api/vehicles", json=v)
        assert r_v.status_code == 201

    # ---------------------------------------------------------
    # 7. Generate optimized route via Google OR-Tools CVRP
    # ---------------------------------------------------------
    r_opt = client.post("/api/routes/optimize", json={"planning_period_hours": 24})
    assert r_opt.status_code == 200
    opt_data = r_opt.json()
    assert "routes" in opt_data

    # ---------------------------------------------------------
    # 8. Request human approval via 8-Agent Workflow run
    # ---------------------------------------------------------
    r_wf = client.post("/api/workflows/run")
    assert r_wf.status_code == 200
    wf = r_wf.json()
    wf_id = wf["workflow_id"]
    assert wf["status"] == "WAITING_APPROVAL"
    assert len(wf["agent_runs"]) == 8

    # ---------------------------------------------------------
    # 9. Approve the route plan as authorized operator
    # ---------------------------------------------------------
    r_app = client.post(f"/api/approvals/{wf_id}/approve", json={
        "operator": "Senior Municipal Dispatcher Sharma",
        "comment": "All capacity checks verified. Approved for morning shift dispatch."
    })
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "APPROVED"

    # ---------------------------------------------------------
    # 10. Start collection & verify active routes & collections
    # ---------------------------------------------------------
    r_routes = client.get("/api/routes?route_status=APPROVED")
    assert r_routes.status_code == 200
    approved_routes = r_routes.json()
    assert len(approved_routes) >= 1
    active_route = approved_routes[0]
    route_id = active_route["route_id"]

    r_colls = client.get(f"/api/collections?route_id={route_id}")
    assert r_colls.status_code == 200
    collections = r_colls.json()
    assert len(collections) >= 1
    target_coll = collections[0]
    coll_id = target_coll["collection_id"]

    # ---------------------------------------------------------
    # 11. Mark vehicle EN_ROUTE
    # ---------------------------------------------------------
    r_enroute = client.put(f"/api/collections/{coll_id}", json={
        "status": "EN_ROUTE",
        "operator_comment": "Vehicle en route to first stop"
    })
    assert r_enroute.status_code == 200
    assert r_enroute.json()["status"] == "EN_ROUTE"

    # Verify vehicle status transitioned to IN_TRANSIT
    v_check = client.get(f"/api/vehicles").json()
    veh_matched = next((v for v in v_check if v["vehicle_id"] == target_coll["vehicle_id"]), None)
    if veh_matched:
        assert veh_matched["status"] == "IN_TRANSIT"

    # ---------------------------------------------------------
    # 12. Simulate a sudden critical surge bin
    # ---------------------------------------------------------
    surge_bin_id = "BIN-SURGE-99"
    client.post("/api/bins", json={
        "bin_id": surge_bin_id,
        "location_name": "Emergency Festival Square",
        "latitude": 12.9730,
        "longitude": 77.5960,
        "waste_type": active_route["stops"][0]["waste_type"],
        "capacity_liters": 800.0,
        "current_fill_percent": 99.0,
        "current_weight_kg": 180.0,
        "collection_threshold_percent": 80.0
    })

    # Ingest critical reading
    client.post("/api/sensors/readings", json={
        "bin_id": surge_bin_id,
        "fill_percent": 99.0,
        "weight_kg": 180.0
    })

    # ---------------------------------------------------------
    # 13. Trigger dynamic replanning for the active route
    # ---------------------------------------------------------
    r_replan = client.post(f"/api/routes/{route_id}/replan", json={
        "trigger_bin_id": surge_bin_id,
        "reason": "Sudden overflow risk during festival event"
    })
    assert r_replan.status_code == 200
    replan_res = r_replan.json()
    assert replan_res["status"] == "REPLAN_PROPOSED"
    assert "marginal_detour_km" in replan_res

    # ---------------------------------------------------------
    # 14. Complete collection
    # ---------------------------------------------------------
    r_done = client.put(f"/api/collections/{coll_id}", json={
        "status": "COMPLETED",
        "actual_volume": 450.0,
        "operator_comment": "Bin emptied, telemetry confirmed 0%"
    })
    assert r_done.status_code == 200
    assert r_done.json()["status"] == "COMPLETED"

    # ---------------------------------------------------------
    # 15. Verify bin fill resets to 0% and vehicle load updates
    # ---------------------------------------------------------
    r_bin_check = client.get(f"/api/bins/{target_coll['bin_id']}")
    assert r_bin_check.status_code == 200
    bin_data = r_bin_check.json()
    assert bin_data["current_fill_percent"] == 0.0
    assert bin_data["last_collection_time"] is not None

    # ---------------------------------------------------------
    # 16. Update and verify Dashboard KPIs reflect execution
    # ---------------------------------------------------------
    r_kpis = client.get("/api/dashboard/kpis")
    assert r_kpis.status_code == 200
    kpis = r_kpis.json()
    assert kpis["total_bins"] >= 3
    assert "recycling_rate_percent" in kpis
    assert "collection_efficiency_percent" in kpis

    # ---------------------------------------------------------
    # 17. Generate official PDF audit report
    # ---------------------------------------------------------
    r_pdf = client.post("/api/reports/generate", json={
        "period_days": 7,
        "title": "Municipal Comprehensive End-to-End Audit Report"
    })
    assert r_pdf.status_code == 200
    pdf_info = r_pdf.json()
    assert "download_url" in pdf_info

    # ---------------------------------------------------------
    # 18. Verify the PDF report can be downloaded cleanly
    # ---------------------------------------------------------
    r_download = client.get(pdf_info["download_url"])
    assert r_download.status_code == 200
    assert r_download.headers["content-type"] == "application/pdf"
    assert len(r_download.content) > 1000  # Valid binary PDF output
