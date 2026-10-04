#!/usr/bin/env python
import os
import sys
import csv
import json
from datetime import datetime

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal, engine, Base
from backend.app.models.entities import Bin, Vehicle, SensorReading, Collection, RecyclingRecord, Alert
from backend.app.forecasting.predictor import ForecastService
from backend.app.services.priority_engine import PriorityEngine
from backend.app.alerts.alert_engine import AlertEngine

def seed_database():
    print("Creating tables if not exists...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Clean existing records for fresh demo reproducibility
        print("Clearing existing records...")
        db.query(Alert).delete()
        db.query(SensorReading).delete()
        db.query(RecyclingRecord).delete()
        db.query(Collection).delete()
        db.query(Vehicle).delete()
        db.query(Bin).delete()
        db.commit()

        # 2. Seed Bins
        bins_path = "data/bins.csv"
        if os.path.exists(bins_path):
            print(f"Seeding bins from {bins_path}...")
            with open(bins_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    b = Bin(
                        bin_id=row["bin_id"],
                        location_name=row["location_name"],
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        waste_type=row["waste_type"],
                        capacity_liters=float(row["capacity_liters"]),
                        current_fill_percent=float(row["current_fill_percent"]),
                        current_weight_kg=float(row["current_weight_kg"]),
                        sensor_id=row["sensor_id"],
                        collection_threshold_percent=float(row["collection_threshold_percent"]),
                        operational_status=row["operational_status"],
                        sensor_status=row["sensor_status"],
                        last_sensor_reading=datetime.utcnow(),
                        last_collection_time=datetime.utcnow()
                    )
                    db.add(b)
            db.commit()
            print("Bins seeded.")

        # 3. Seed Vehicles
        vehicles_path = "data/vehicles.csv"
        if os.path.exists(vehicles_path):
            print(f"Seeding vehicles from {vehicles_path}...")
            with open(vehicles_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    types = json.loads(row["supported_waste_types"])
                    v = Vehicle(
                        vehicle_id=row["vehicle_id"],
                        supported_waste_types=types,
                        capacity_liters=float(row["capacity_liters"]),
                        current_load_liters=float(row["current_load_liters"]),
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        status=row["status"],
                        current_route_id=row["current_route_id"] if row["current_route_id"] else None
                    )
                    db.add(v)
            db.commit()
            print("Vehicles seeded.")

        # 4. Seed Sensor Readings
        readings_path = "data/sensor_readings.csv"
        if os.path.exists(readings_path):
            print(f"Seeding sensor readings from {readings_path}...")
            with open(readings_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sr = SensorReading(
                        bin_id=row["bin_id"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        fill_percent=float(row["fill_percent"]),
                        weight_kg=float(row["weight_kg"]),
                        temperature=float(row["temperature"]),
                        sensor_status=row["sensor_status"],
                        validation_status=row["validation_status"],
                        validation_reason=row["validation_reason"]
                    )
                    db.add(sr)
            db.commit()
            print("Sensor readings seeded.")

        # 5. Seed Recycling & Collections
        rec_path = "data/recycling.csv"
        if os.path.exists(rec_path):
            print(f"Seeding recycling records from {rec_path}...")
            with open(rec_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rr = RecyclingRecord(
                        collection_id=row["collection_id"],
                        waste_type=row["waste_type"],
                        weight_kg=float(row["weight_kg"]),
                        recyclable_weight_kg=float(row["recyclable_weight_kg"]),
                        contamination_weight_kg=float(row["contamination_weight_kg"]),
                        created_at=datetime.fromisoformat(row["created_at"])
                    )
                    db.add(rr)
            db.commit()
            print("Recycling records seeded.")

        coll_path = "data/collections.csv"
        if os.path.exists(coll_path):
            print(f"Seeding collections from {coll_path}...")
            with open(coll_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    c = Collection(
                        collection_id=row["collection_id"],
                        bin_id=row["bin_id"],
                        vehicle_id=row["vehicle_id"],
                        route_id=row["route_id"],
                        scheduled_time=datetime.fromisoformat(row["scheduled_time"]),
                        actual_collection_time=datetime.fromisoformat(row["actual_collection_time"]),
                        estimated_volume=float(row["estimated_volume"]),
                        actual_volume=float(row["actual_volume"]),
                        status=row["status"],
                        operator_comment=row["operator_comment"]
                    )
                    db.add(c)
            db.commit()
            print("Collections seeded.")

        # 6. Initialize Alerts for Critical Bins & Suspicious Sensors
        print("Initializing operational alerts for seed states...")
        bins = db.query(Bin).all()
        for b in bins:
            if b.current_fill_percent >= 95.0:
                AlertEngine.create_alert(db, b.bin_id, "OVERFLOW_RISK", "CRITICAL", f"Critical overflow hazard: {b.bin_id} fill is at {b.current_fill_percent:.1f}%.")
            elif b.current_fill_percent >= b.collection_threshold_percent:
                AlertEngine.create_alert(db, b.bin_id, "THRESHOLD_EXCEEDED", "HIGH", f"Collection threshold reached: {b.bin_id} is at {b.current_fill_percent:.1f}%.")
            if b.sensor_status == "SUSPICIOUS":
                AlertEngine.create_alert(db, b.bin_id, "SENSOR_SUSPICIOUS", "WARNING", f"Sensor on {b.bin_id} flagged as suspicious.")
            elif b.sensor_status == "STALE":
                AlertEngine.create_alert(db, b.bin_id, "SENSOR_STALE", "WARNING", f"Sensor on {b.bin_id} is stale (no recent heartbeat).")

        # 7. Generate Initial ML Forecasts
        print("Generating initial baseline forecasts...")
        ForecastService.run_all_forecasts(db, horizon_hours=24)

        print("=== Database Seeding Complete & Verified ===")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
