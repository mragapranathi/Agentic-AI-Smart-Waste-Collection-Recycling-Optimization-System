#!/usr/bin/env python
import os
import sys
import time
import random
import argparse
from datetime import datetime, timezone
import requests

# Ensure project root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal
from backend.app.models.entities import Bin, SensorReading
from backend.app.services.sensor_validator import SensorValidator

API_URL = "http://localhost:8000/api/sensors/readings"

def run_iot_simulation(num_cycles: int = 5, delay_seconds: float = 2.0, api_endpoint: str = API_URL):
    """
    Simulates real-time IoT smart bin sensor telemetry stream.
    Generates realistic gradual accumulation, periodic collections, and occasional anomalies.
    """
    print(f"=== Starting Municipal IoT Sensor Simulator ===")
    print(f"Cycles: {num_cycles} | Delay: {delay_seconds}s | Target: {api_endpoint}")

    db = SessionLocal()
    bins = db.query(Bin).all()
    bin_ids = [b.bin_id for b in bins]
    db.close()

    if not bin_ids:
        print("Error: No bins found in database. Please run python scripts/seed_database.py first.")
        return

    # Check if API server is running
    server_online = False
    try:
        r = requests.get("http://localhost:8000/api/health", timeout=1.5)
        if r.status_code == 200:
            server_online = True
            print("Detected live FastAPI backend at http://localhost:8000. Ingesting via REST API.")
    except:
        print("Backend server not running at http://localhost:8000. Ingesting directly into database via SensorValidator.")

    for cycle in range(1, num_cycles + 1):
        print(f"\n--- [IoT Telemetry Cycle {cycle}/{num_cycles}] ---")
        # Sample 5 bins per cycle to update
        sampled_bins = random.sample(bin_ids, min(6, len(bin_ids)))

        for bid in sampled_bins:
            db_session = SessionLocal()
            bin_obj = db_session.query(Bin).filter(Bin.bin_id == bid).first()
            if not bin_obj:
                db_session.close()
                continue

            current_fill = bin_obj.current_fill_percent

            # Decide behavior:
            # 85% normal gradual accumulation (+0.5% to +4.0%)
            # 5% empty/collection reset (drops to 5-10%)
            # 5% sudden spike (e.g., event/surge, +35% to +50%)
            # 5% invalid negative or impossible reading (>100% or <0%)
            rand = random.random()
            if rand < 0.85:
                # Normal accumulation
                new_fill = min(98.0, current_fill + random.uniform(0.5, 3.5))
            elif rand < 0.90:
                # Emptied
                new_fill = random.uniform(4.0, 10.0)
            elif rand < 0.95:
                # Sudden surge
                new_fill = min(99.0, current_fill + 40.0)
            else:
                # Sensor glitch
                new_fill = random.choice([-5.0, 115.0])

            density = 0.22 if bin_obj.waste_type == "General" else (0.12 if bin_obj.waste_type == "Recyclable" else 0.40)
            new_weight = max(0.0, round(bin_obj.capacity_liters * (new_fill / 100.0) * density, 1))

            payload = {
                "bin_id": bid,
                "fill_percent": round(new_fill, 1),
                "weight_kg": new_weight,
                "temperature": round(random.uniform(21.0, 32.0), 1),
                "sensor_status": "HEALTHY"
            }

            if server_online:
                try:
                    res = requests.post(api_endpoint, json=payload, timeout=2.0)
                    resp_data = res.json()
                    print(f"  [API] {bid}: {payload['fill_percent']}% | Val: {resp_data.get('validation_status')} ({resp_data.get('validation_reason')})")
                except Exception as e:
                    print(f"  [API Error] {e}")
            else:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                val_status, s_status, reason = SensorValidator.validate_reading(
                    db=db_session,
                    bin_obj=bin_obj,
                    fill_percent=payload["fill_percent"],
                    weight_kg=payload["weight_kg"],
                    reading_time=now
                )
                reading = SensorReading(
                    bin_id=bid,
                    timestamp=now,
                    fill_percent=payload["fill_percent"],
                    weight_kg=payload["weight_kg"],
                    temperature=payload["temperature"],
                    sensor_status=s_status,
                    validation_status=val_status,
                    validation_reason=reason
                )
                db_session.add(reading)
                if val_status in ("VALID", "SUSPICIOUS"):
                    bin_obj.current_fill_percent = payload["fill_percent"]
                    bin_obj.current_weight_kg = payload["weight_kg"]
                    bin_obj.sensor_status = s_status
                    bin_obj.last_sensor_reading = now
                elif val_status == "INVALID":
                    bin_obj.sensor_status = "INVALID"
                db_session.commit()
                print(f"  [DB]  {bid}: {payload['fill_percent']}% | Status: {val_status} ({reason[:45]}...)")

            db_session.close()

        if cycle < num_cycles:
            time.sleep(delay_seconds)

    print("\n=== IoT Simulation Batch Complete ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate smart bin IoT sensor readings")
    parser.add_argument("--cycles", type=int, default=3, help="Number of telemetry cycles")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between cycles in seconds")
    args = parser.parse_args()
    run_iot_simulation(num_cycles=args.cycles, delay_seconds=args.delay)
