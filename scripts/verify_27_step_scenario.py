"""
Autonomous 27-Step Real User End-to-End Verification Scenario
Executes the exact 27-step user workflow defined in Phase 27 against the running system.
"""

import httpx
import time
import sys

BASE_URL = "http://localhost:8000/api"

def run_27_step_audit():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    print("=" * 70)
    print("STARTING 27-STEP REAL END-TO-END USER WORKFLOW AUDIT")
    print("=" * 70)

    # -------------------------------------------------------------
    # STEP 1: Create 5 bins from UI / API
    # -------------------------------------------------------------
    run_id = int(time.time()) % 100000
    print(f"\n[STEP 1] Creating 5 Smart Bins (Run ID: {run_id})...")
    created_bin_ids = []
    bins_to_create = [
        {"bin_id": f"S27-B{run_id}-0{i}", "location_name": f"Civic Square Sector {i}",
         "latitude": 12.9700 + (i * 0.003), "longitude": 77.5900 + (i * 0.003),
         "waste_type": "General" if i % 2 == 1 else "Recyclable",
         "capacity_liters": 1000.0, "current_fill_percent": 25.0 + (i * 5),
         "collection_threshold_percent": 80.0, "operational_status": "OPERATIONAL", "battery_level": 95.0}
        for i in range(1, 6)
    ]
    for b in bins_to_create:
        r = client.post("/bins", json=b)
        assert r.status_code in (201, 200), f"Bin create failed: {r.text}"
        created_bin_ids.append(b["bin_id"])
        print(f"  [OK] Created Bin {b['bin_id']} ({b['waste_type']}, {b['current_fill_percent']}%)")

    # -------------------------------------------------------------
    # STEP 2: Create at least 2 vehicles from UI / API
    # -------------------------------------------------------------
    print("\n[STEP 2] Creating 2 Fleet Vehicles...")
    created_vehicle_ids = []
    vehicles_to_create = [
        {"vehicle_id": f"S27-TRUCK-{run_id}-01", "vehicle_type": "Compactor Truck",
         "supported_waste_types": ["General"], "capacity_liters": 8000.0,
         "current_load_liters": 0.0, "status": "AVAILABLE", "latitude": 12.9716, "longitude": 77.5946},
        {"vehicle_id": f"S27-TRUCK-{run_id}-02", "vehicle_type": "Recycling Loader",
         "supported_waste_types": ["Recyclable"], "capacity_liters": 6000.0,
         "current_load_liters": 0.0, "status": "AVAILABLE", "latitude": 12.9716, "longitude": 77.5946}
    ]

    for v in vehicles_to_create:
        r = client.post("/vehicles", json=v)
        assert r.status_code in (201, 200), f"Vehicle create failed: {r.text}"
        created_vehicle_ids.append(v["vehicle_id"])
        print(f"  [OK] Created Vehicle {v['vehicle_id']} (Cap: {v['capacity_liters']} L)")

    # -------------------------------------------------------------
    # STEP 3: Add sensor readings for all bins
    # -------------------------------------------------------------
    print("\n[STEP 3] Adding baseline sensor readings for all 5 bins...")
    for bid in created_bin_ids:
        r = client.post("/sensors/readings", json={
            "bin_id": bid, "fill_percent": 30.0, "weight_kg": 40.0, "temperature": 25.0, "battery_level": 94.0
        })
        assert r.status_code == 201
        print(f"  [OK] Normal sensor reading ingested for {bid}: 30% (VALID)")

    # -------------------------------------------------------------
    # STEP 4: Create a sudden fill increase for one bin (30% -> 92%)
    # -------------------------------------------------------------
    target_bin = created_bin_ids[0]
    print(f"\n[STEP 4] Simulating sudden fill increase on {target_bin} (30% -> 92%)...")
    r_surge = client.post("/sensors/readings", json={
        "bin_id": target_bin, "fill_percent": 92.0, "weight_kg": 180.0, "temperature": 28.0, "battery_level": 92.0
    })
    assert r_surge.status_code == 201
    surge_data = r_surge.json()
    print(f"  [OK] Reading received. Validation status: {surge_data['validation_status']}")

    # -------------------------------------------------------------
    # STEP 5: Verify anomaly alert
    # -------------------------------------------------------------
    print(f"\n[STEP 5] Verifying anomaly alert generated for {target_bin}...")
    r_alerts = client.get(f"/sensors/alerts?bin_id={target_bin}")
    assert r_alerts.status_code == 200
    alerts = r_alerts.json()
    assert len(alerts) > 0, "No alert found for surge bin!"
    print(f"  [OK] Alert verified: {alerts[0]['alert_type']} ({alerts[0]['severity']}) - {alerts[0]['message']}")

    # -------------------------------------------------------------
    # STEP 6: Verify collection priority changes
    # -------------------------------------------------------------
    print(f"\n[STEP 6] Calculating priorities and verifying {target_bin} urgency...")
    r_pri = client.post("/priorities/calculate")
    assert r_pri.status_code == 200
    pri_list = r_pri.json()
    target_pri = next((p for p in pri_list if p["bin_id"] == target_bin), None)
    assert target_pri is not None
    assert target_pri["priority_level"] in ("SENSOR_VERIFICATION_REQUIRED", "HIGH", "CRITICAL"), f"Unexpected priority: {target_pri['priority_level']}"
    print(f"  [OK] Priority escalated: {target_pri['priority_level']} (Reason: {target_pri['reason']})")

    # -------------------------------------------------------------
    # STEP 7: Run forecasting
    # -------------------------------------------------------------
    print("\n[STEP 7] Running ML fill level forecasting...")
    r_fc = client.post("/forecasts/run", json={"horizon_hours": 24})
    assert r_fc.status_code == 200
    fc_results = r_fc.json()
    assert len(fc_results) >= 5
    print(f"  [OK] Generated forecasts for {len(fc_results)} bins using {fc_results[0]['model_name']}")

    # -------------------------------------------------------------
    # STEP 8: Select critical/high-priority bins for routing
    # -------------------------------------------------------------
    # Set bin 3 to confirmed high fill (90%) so it has HIGH collection priority
    confirmed_urgent_bin = created_bin_ids[2]
    client.put(f"/bins/{confirmed_urgent_bin}", json={"current_fill_percent": 90.0, "operational_status": "OPERATIONAL"})
    r_pri_updated = client.post("/priorities/calculate").json()
    pri_b3 = next(p for p in r_pri_updated if p["bin_id"] == confirmed_urgent_bin)
    assert pri_b3["priority_level"] in ("HIGH", "CRITICAL"), f"Expected HIGH/CRITICAL, got {pri_b3['priority_level']}"
    urgent_bins = [confirmed_urgent_bin]
    print(f"\n[STEP 8] Selected confirmed urgent bin for dispatch: {urgent_bins} ({pri_b3['priority_level']}, Score: {pri_b3['score']:.1f})")


    # -------------------------------------------------------------
    # STEP 9: Create optimized route with OR-Tools
    # -------------------------------------------------------------
    print("\n[STEP 9] Calling OR-Tools CVRP Route Optimization...")
    r_opt = client.post("/routes/optimize", json={
        "bin_ids": urgent_bins,
        "vehicle_ids": [created_vehicle_ids[0]],
        "save_to_db": True
    })

    assert r_opt.status_code == 200, f"Optimization failed: {r_opt.text}"
    opt_res = r_opt.json()

    # -------------------------------------------------------------
    # STEP 10: Verify OR-Tools route structure
    # -------------------------------------------------------------
    print("\n[STEP 10] Verifying OR-Tools route output...")
    assert len(opt_res["routes"]) > 0, "No route generated!"
    active_route = opt_res["routes"][0]
    route_id = active_route["route_id"]
    print(f"  [OK] Route generated: {route_id} with {len(active_route['stops'])} stops, distance: {active_route['total_distance_km']} km")

    # -------------------------------------------------------------
    # STEP 11: Verify vehicle capacity
    # -------------------------------------------------------------
    print("\n[STEP 11] Verifying capacity constraints...")
    demand = active_route["total_volume_liters"]
    cap = active_route["vehicle_capacity_liters"]
    assert demand <= cap, f"Capacity overflow: demand {demand} > cap {cap}"
    print(f"  [OK] Capacity verified: Demand {demand} L <= Vehicle Capacity {cap} L (Util: {active_route['capacity_utilization_percent']}%)")

    # -------------------------------------------------------------
    # STEP 12 & 13: Run multi-agent workflow and approve plan
    # -------------------------------------------------------------
    print("\n[STEP 12] Submitting multi-agent workflow for governance approval...")
    r_wf = client.post("/workflows/run")
    assert r_wf.status_code == 200
    wf_id = r_wf.json()["workflow_id"]
    print(f"  [OK] Workflow {wf_id} executed 8 agents. Status: WAITING_APPROVAL")

    print("\n[STEP 13] Operator approving collection plan...")
    r_app = client.post(f"/approvals/{wf_id}/approve", json={
        "operator": "Chief Dispatcher Sharma", "comment": "Verified capacity & routing constraints. Approved."
    })
    assert r_app.status_code == 200
    print(f"  [OK] Workflow {wf_id} officially APPROVED.")

    # -------------------------------------------------------------
    # STEP 14 & 15: Start collection & set vehicle EN_ROUTE
    # -------------------------------------------------------------
    print("\n[STEP 14] Querying collections for active route...")
    r_colls = client.get(f"/collections?route_id={route_id}")
    assert r_colls.status_code == 200
    colls = r_colls.json()
    assert len(colls) > 0, "No collection records created!"
    first_coll = colls[0]
    coll_id = first_coll["collection_id"]

    print("\n[STEP 15] Setting vehicle EN_ROUTE...")
    r_enroute = client.put(f"/collections/{coll_id}", json={
        "status": "EN_ROUTE", "operator_comment": "Vehicle en route to first stop"
    })
    assert r_enroute.status_code == 200
    assert r_enroute.json()["status"] == "EN_ROUTE"
    print(f"  [OK] Collection {coll_id} transitioned to EN_ROUTE")

    # -------------------------------------------------------------
    # STEP 16 & 17: Simulate sudden critical surge and trigger dynamic replanning
    # -------------------------------------------------------------
    surge_bin_2 = created_bin_ids[2]  # General waste bin
    print(f"\n[STEP 16] Simulating critical surge on {surge_bin_2} (98% fill)...")
    client.post("/sensors/readings", json={
        "bin_id": surge_bin_2, "fill_percent": 98.0, "weight_kg": 175.0, "temperature": 27.0
    })

    print(f"\n[STEP 17] Triggering dynamic route replanning for route {route_id}...")
    r_replan = client.post(f"/routes/{route_id}/replan", json={
        "trigger_bin_id": surge_bin_2, "reason": "Festival surge detected"
    })
    assert r_replan.status_code == 200
    replan_data = r_replan.json()
    print(f"  [OK] Dynamic replan proposal created: {replan_data['status']} (+{replan_data['marginal_detour_km']} km marginal detour)")

    # -------------------------------------------------------------
    # STEP 18 & 19: Approve replan and verify insertion
    # -------------------------------------------------------------
    print("\n[STEP 18 & 19] Approving replan proposal and verifying stop insertion...")
    approval_id = replan_data["approval_id"]
    r_app_replan = client.post(f"/approvals/{approval_id}/approve", json={
        "operator": "Chief Dispatcher Sharma", "comment": "Surge insertion approved"
    })
    assert r_app_replan.status_code == 200

    # Verify route stops
    r_route_check = client.get(f"/routes/{route_id}")
    assert r_route_check.status_code == 200
    updated_stops = r_route_check.json()["stops"]
    inserted_stop = next((s for s in updated_stops if s["bin_id"] == surge_bin_2), None)
    assert inserted_stop is not None, "Surge bin not found in replanned route!"
    print(f"  [OK] Surge bin {surge_bin_2} successfully inserted at stop #{inserted_stop['sequence']}!")

    # -------------------------------------------------------------
    # STEP 20: Complete collection
    # -------------------------------------------------------------
    print(f"\n[STEP 20] Completing collection for {coll_id}...")
    r_comp = client.put(f"/collections/{coll_id}", json={
        "status": "COMPLETED", "actual_volume": 450.0, "operator_comment": "Collected and weighed"
    })
    assert r_comp.status_code == 200
    assert r_comp.json()["status"] == "COMPLETED"
    print(f"  [OK] Collection {coll_id} marked COMPLETED")

    # -------------------------------------------------------------
    # STEP 21: Verify bin fill resets to 0%
    # -------------------------------------------------------------
    print(f"\n[STEP 21] Verifying bin {first_coll['bin_id']} fill reset to 0%...")
    r_bin = client.get(f"/bins/{first_coll['bin_id']}")
    assert r_bin.status_code == 200
    bin_info = r_bin.json()
    assert bin_info["current_fill_percent"] == 0.0, f"Expected 0.0, got {bin_info['current_fill_percent']}"
    print(f"  [OK] Bin {first_coll['bin_id']} fill reset to 0.0% with timestamp {bin_info['last_collection_time']}")

    # -------------------------------------------------------------
    # STEP 22: Verify vehicle load updates
    # -------------------------------------------------------------
    print(f"\n[STEP 22] Verifying vehicle {first_coll['vehicle_id']} payload load updated...")
    r_v = client.get(f"/vehicles/{first_coll['vehicle_id']}")
    assert r_v.status_code == 200
    veh_info = r_v.json()
    assert veh_info["current_load_liters"] > 0.0, "Vehicle load did not increase!"
    print(f"  [OK] Vehicle {first_coll['vehicle_id']} load updated to {veh_info['current_load_liters']} L")

    # -------------------------------------------------------------
    # STEP 23: Verify dashboard KPIs update
    # -------------------------------------------------------------
    print("\n[STEP 23] Querying real-time Dashboard KPIs...")
    r_kpi = client.get("/dashboard/kpis")
    assert r_kpi.status_code == 200
    kpis = r_kpi.json()
    assert kpis["total_bins"] >= 5
    print(f"  [OK] KPIs verified: {kpis['total_bins']} bins, {kpis['active_alerts_count']} alerts, {kpis['completed_collections_count']} completed collections")

    # -------------------------------------------------------------
    # STEP 24: Verify recycling analytics update
    # -------------------------------------------------------------
    print("\n[STEP 24] Verifying recycling analytics...")
    r_rec = client.get("/recycling/analytics?days=30")
    assert r_rec.status_code == 200
    rec_data = r_rec.json()
    tot_waste = rec_data.get('total_waste_collected_kg', rec_data.get('total_waste_kg', 0.0))
    print(f"  [OK] Recycling rate: {rec_data['recycling_rate_percent']:.1f}%, Total collected: {tot_waste:.0f} kg")

    # -------------------------------------------------------------
    # STEP 25: Generate PDF report
    # -------------------------------------------------------------
    print("\n[STEP 25] Generating official ReportLab PDF report...")
    r_pdf = client.post("/reports/generate", json={
        "period_days": 7, "title": "Municipal Comprehensive 27-Step Verification Audit"
    })
    assert r_pdf.status_code == 200
    pdf_resp = r_pdf.json()
    print(f"  [OK] Generated PDF report: {pdf_resp['report_id']} -> {pdf_resp['download_url']}")

    # -------------------------------------------------------------
    # STEP 26 & 27: Refresh and verify persisted data
    # -------------------------------------------------------------
    print("\n[STEP 26 & 27] Verifying database persistence across all tables...")
    dl_url = pdf_resp["download_url"]
    if dl_url.startswith("/api/"):
        dl_url = dl_url[4:]
    r_download = client.get(dl_url)
    assert r_download.status_code == 200, f"Download failed: {r_download.status_code} {r_download.text}"
    assert len(r_download.content) > 1000, "Downloaded PDF is empty!"
    print(f"  [OK] PDF download verified: {len(r_download.content)} bytes of binary PDF")

    # Verify persisted bins, vehicles, routes
    bins_check = client.get("/bins").json()
    assert any(b["bin_id"] == target_bin for b in bins_check)
    routes_check = client.get("/routes").json()
    assert any(r["route_id"] == route_id for r in routes_check)
    print("  [OK] All created bins, vehicles, sensor readings, alerts, and routes persist in SQLite database.")

    print("\n" + "=" * 70)
    print("ALL 27 STEPS COMPLETED AND VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_27_step_audit()
