from datetime import datetime
from backend.app.models.entities import Bin, Vehicle, SensorReading, Route, Collection, RecyclingRecord

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_bins_crud(client, db_session):
    # Create bin
    payload = {
        "bin_id": "BIN-API-01",
        "location_name": "API Test Plaza",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "waste_type": "Recyclable",
        "capacity_liters": 800.0,
        "current_fill_percent": 45.0,
        "current_weight_kg": 60.0,
        "collection_threshold_percent": 85.0
    }
    create_res = client.post("/api/bins", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["bin_id"] == "BIN-API-01"

    # Get bins list
    get_res = client.get("/api/bins")
    assert get_res.status_code == 200
    assert len(get_res.json()) >= 1

    # Get single bin
    single_res = client.get("/api/bins/BIN-API-01")
    assert single_res.status_code == 200
    assert single_res.json()["waste_type"] == "Recyclable"

    # Update bin
    up_res = client.put("/api/bins/BIN-API-01", json={"current_fill_percent": 55.0})
    assert up_res.status_code == 200
    assert up_res.json()["current_fill_percent"] == 55.0

    # Delete bin
    del_res = client.delete("/api/bins/BIN-API-01")
    assert del_res.status_code == 200
    assert client.get("/api/bins/BIN-API-01").status_code == 404

def test_sensors_and_alerts_api(client, db_session):
    # Create target bin
    bin_obj = Bin(
        bin_id="BIN-SENS-01",
        location_name="Sensor Test Zone",
        latitude=12.9716,
        longitude=77.5946,
        waste_type="General",
        capacity_liters=1000.0,
        current_fill_percent=50.0,
        current_weight_kg=100.0,
        collection_threshold_percent=85.0
    )
    db_session.add(bin_obj)
    db_session.commit()

    # Submit valid sensor reading
    payload = {
        "bin_id": "BIN-SENS-01",
        "fill_percent": 96.0,  # Should trigger overflow alert
        "weight_kg": 210.0,
        "temperature": 26.5
    }
    res = client.post("/api/sensors/readings", json=payload)
    assert res.status_code == 201
    reading = res.json()
    assert reading["validation_status"] == "VALID"

    # Verify alert was generated
    alert_res = client.get("/api/sensors/alerts?bin_id=BIN-SENS-01")
    assert alert_res.status_code == 200
    alerts = alert_res.json()
    assert len(alerts) >= 1
    alert_types = [a["alert_type"] for a in alerts]
    assert any(t in ("OVERFLOW_RISK", "THRESHOLD_EXCEEDED") for t in alert_types), \
        f"Expected OVERFLOW_RISK or THRESHOLD_EXCEEDED in alerts, got: {alert_types}"

def test_vehicles_api(client, db_session):
    payload = {
        "vehicle_id": "TRUCK-API-01",
        "supported_waste_types": ["General", "Organic"],
        "capacity_liters": 8000.0,
        "current_load_liters": 0.0,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "status": "AVAILABLE"
    }
    res = client.post("/api/vehicles", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["vehicle_id"] == "TRUCK-API-01"

    get_res = client.get("/api/vehicles")
    assert get_res.status_code == 200
    assert any(v["vehicle_id"] == "TRUCK-API-01" for v in get_res.json())

def test_dashboard_kpis_api(client, db_session):
    res = client.get("/api/dashboard/kpis")
    assert res.status_code == 200
    kpis = res.json()
    assert "total_bins" in kpis
    assert "recycling_rate_percent" in kpis
    assert "collection_efficiency_percent" in kpis

def test_pdf_report_api(client, db_session):
    # Add dummy bin
    b = Bin(bin_id="BIN-RPT", location_name="Report Bin", latitude=12.97, longitude=77.59, waste_type="General", capacity_liters=1000, current_fill_percent=92)
    db_session.add(b)
    db_session.commit()

    res = client.post("/api/reports/generate", json={"period_days": 7, "title": "Test Municipal Report"})
    assert res.status_code == 200
    data = res.json()
    assert "download_url" in data
    assert data["report_id"].startswith("RPT-")

    # Test downloading the PDF
    download_res = client.get(data["download_url"])
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert len(download_res.content) > 1000
