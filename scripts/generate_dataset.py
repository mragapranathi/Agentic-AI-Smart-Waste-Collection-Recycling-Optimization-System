#!/usr/bin/env python
import os
import csv
import random
from datetime import datetime, timedelta
import numpy as np

# Configurable Demo City Base Coordinates (Bangalore Municipal Area)
BASE_LAT = 12.9716
BASE_LNG = 77.5946

def generate_all_datasets(output_dir: str = "data"):
    os.makedirs(output_dir, exist_ok=True)
    random.seed(42)
    np.random.seed(42)

    # 1. BINS DATASET (60 Bins)
    # Exact required demo scenario bins 001-006:
    demo_bins = [
        {"bin_id": "BIN-001", "location_name": "Zone A - Commercial Plaza Hub", "lat": BASE_LAT + 0.012, "lng": BASE_LNG + 0.008, "waste_type": "General", "capacity_liters": 1000.0, "fill": 92.0, "weight": 210.0, "threshold": 85.0, "sensor_status": "HEALTHY"},
        {"bin_id": "BIN-002", "location_name": "Zone A - North Market Recyclables", "lat": BASE_LAT + 0.015, "lng": BASE_LNG + 0.005, "waste_type": "Recyclable", "capacity_liters": 800.0, "fill": 45.0, "weight": 65.0, "threshold": 85.0, "sensor_status": "HEALTHY"},
        {"bin_id": "BIN-003", "location_name": "Zone B - High-Density Residential Apts", "lat": BASE_LAT - 0.010, "lng": BASE_LNG + 0.015, "waste_type": "General", "capacity_liters": 1000.0, "fill": 87.0, "weight": 195.0, "threshold": 85.0, "sensor_status": "HEALTHY"},
        {"bin_id": "BIN-004", "location_name": "Zone B - Community Food Court Organics", "lat": BASE_LAT - 0.013, "lng": BASE_LNG + 0.012, "waste_type": "Organic", "capacity_liters": 700.0, "fill": 96.0, "weight": 280.0, "threshold": 85.0, "sensor_status": "HEALTHY"},
        {"bin_id": "BIN-005", "location_name": "Zone C - University Campus Center", "lat": BASE_LAT + 0.020, "lng": BASE_LNG - 0.015, "waste_type": "Recyclable", "capacity_liters": 800.0, "fill": 38.0, "weight": 52.0, "threshold": 85.0, "sensor_status": "HEALTHY"},
        {"bin_id": "BIN-006", "location_name": "Zone C - Tech Park Transit Terminal", "lat": BASE_LAT + 0.018, "lng": BASE_LNG - 0.012, "waste_type": "General", "capacity_liters": 1000.0, "fill": 78.0, "weight": 160.0, "threshold": 85.0, "sensor_status": "HEALTHY"},
        # BIN-010 for dynamic replanning scenario (TC-07)
        {"bin_id": "BIN-010", "location_name": "Zone A - Central Promenade Metro", "lat": BASE_LAT + 0.009, "lng": BASE_LNG + 0.011, "waste_type": "General", "capacity_liters": 1000.0, "fill": 62.0, "weight": 130.0, "threshold": 85.0, "sensor_status": "HEALTHY"},
        # Suspicious sensor bin for TC-03
        {"bin_id": "BIN-015", "location_name": "Zone D - Industrial Sector 4", "lat": BASE_LAT - 0.025, "lng": BASE_LNG - 0.018, "waste_type": "General", "capacity_liters": 1200.0, "fill": 99.0, "weight": 110.0, "threshold": 85.0, "sensor_status": "SUSPICIOUS"},
        # Stale sensor bin
        {"bin_id": "BIN-020", "location_name": "Zone E - South Park Recreational", "lat": BASE_LAT - 0.030, "lng": BASE_LNG + 0.022, "waste_type": "Organic", "capacity_liters": 800.0, "fill": 55.0, "weight": 120.0, "threshold": 85.0, "sensor_status": "STALE"},
    ]

    all_bins = list(demo_bins)
    zones = ["Zone A", "Zone B", "Zone C", "Zone D", "Zone E"]
    waste_types = ["General", "Recyclable", "Organic"]

    existing_ids = {b["bin_id"] for b in all_bins}

    for i in range(1, 61):
        bid = f"BIN-{i:03d}"
        if bid in existing_ids:
            continue
        z = zones[i % len(zones)]
        wt = waste_types[i % len(waste_types)]
        cap = float(random.choice([700, 800, 1000, 1200]))
        fill = round(random.uniform(15.0, 93.0), 1)
        density = 0.22 if wt == "General" else (0.12 if wt == "Recyclable" else 0.40)
        weight = round(cap * (fill / 100.0) * density, 1)

        lat = BASE_LAT + random.uniform(-0.045, 0.045)
        lng = BASE_LNG + random.uniform(-0.045, 0.045)

        s_status = "HEALTHY"
        if i == 25:
            s_status = "INVALID"
        elif i == 30:
            s_status = "OFFLINE"

        all_bins.append({
            "bin_id": bid,
            "location_name": f"{z} - Sector {i} Municipal Bin",
            "lat": round(lat, 5),
            "lng": round(lng, 5),
            "waste_type": wt,
            "capacity_liters": cap,
            "fill": fill,
            "weight": weight,
            "threshold": 85.0,
            "sensor_status": s_status
        })

    bins_csv_path = os.path.join(output_dir, "bins.csv")
    with open(bins_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "bin_id", "location_name", "latitude", "longitude", "waste_type",
            "capacity_liters", "current_fill_percent", "current_weight_kg",
            "sensor_id", "collection_threshold_percent", "operational_status", "sensor_status"
        ])
        for b in all_bins:
            writer.writerow([
                b["bin_id"], b["location_name"], b["lat"], b["lng"], b["waste_type"],
                b["capacity_liters"], b["fill"], b["weight"],
                f"SENS-{b['bin_id']}", b["threshold"], "OPERATIONAL", b["sensor_status"]
            ])

    print(f"Generated {len(all_bins)} bins in {bins_csv_path}")

    # 2. VEHICLES DATASET (12 Vehicles)
    vehicles_data = [
        # Demo scenario vehicles
        {"vehicle_id": "TRUCK-01", "types": '["General"]', "cap": 8000.0, "load": 0.0, "lat": BASE_LAT, "lng": BASE_LNG, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-02", "types": '["Recyclable"]', "cap": 6000.0, "load": 0.0, "lat": BASE_LAT, "lng": BASE_LNG, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-03", "types": '["Organic"]', "cap": 5000.0, "load": 0.0, "lat": BASE_LAT, "lng": BASE_LNG, "status": "AVAILABLE"},
        # Additional fleet
        {"vehicle_id": "TRUCK-04", "types": '["General"]', "cap": 8000.0, "load": 0.0, "lat": BASE_LAT + 0.005, "lng": BASE_LNG - 0.005, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-05", "types": '["Recyclable"]', "cap": 7000.0, "load": 0.0, "lat": BASE_LAT - 0.005, "lng": BASE_LNG + 0.005, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-06", "types": '["Organic"]', "cap": 6000.0, "load": 0.0, "lat": BASE_LAT + 0.010, "lng": BASE_LNG + 0.010, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-07", "types": '["General", "Recyclable"]', "cap": 9000.0, "load": 1200.0, "lat": BASE_LAT - 0.012, "lng": BASE_LNG - 0.008, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-08", "types": '["General"]', "cap": 8000.0, "load": 0.0, "lat": BASE_LAT + 0.015, "lng": BASE_LNG - 0.015, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-09", "types": '["Recyclable"]', "cap": 6000.0, "load": 0.0, "lat": BASE_LAT - 0.018, "lng": BASE_LNG + 0.018, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-10", "types": '["Organic"]', "cap": 5000.0, "load": 0.0, "lat": BASE_LAT + 0.022, "lng": BASE_LNG + 0.005, "status": "AVAILABLE"},
        {"vehicle_id": "TRUCK-11", "types": '["General"]', "cap": 7500.0, "load": 4500.0, "lat": BASE_LAT - 0.010, "lng": BASE_LNG - 0.010, "status": "COLLECTING"},
        {"vehicle_id": "TRUCK-12", "types": '["General", "Recyclable", "Organic"]', "cap": 10000.0, "load": 0.0, "lat": BASE_LAT, "lng": BASE_LNG, "status": "MAINTENANCE"}
    ]

    vehicles_csv_path = os.path.join(output_dir, "vehicles.csv")
    with open(vehicles_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["vehicle_id", "supported_waste_types", "capacity_liters", "current_load_liters", "latitude", "longitude", "status", "current_route_id"])
        for v in vehicles_data:
            writer.writerow([v["vehicle_id"], v["types"], v["cap"], v["load"], v["lat"], v["lng"], v["status"], None])

    print(f"Generated {len(vehicles_data)} vehicles in {vehicles_csv_path}")

    # 3. HISTORICAL SENSOR READINGS (Several weeks of telemetry)
    readings_csv_path = os.path.join(output_dir, "sensor_readings.csv")
    readings = []
    base_time = datetime.utcnow() - timedelta(days=21)

    for b in all_bins[:20]:  # Seed detailed time-series for top 20 bins
        curr_f = 20.0
        for step in range(80):  # readings every 6 hours
            r_time = base_time + timedelta(hours=step * 6)
            growth = random.uniform(1.0, 4.5)
            curr_f = min(98.0, curr_f + growth)
            weight = round(b["capacity_liters"] * (curr_f / 100.0) * 0.2, 1)

            # simulate collection emptying
            if curr_f >= 88.0 and random.random() > 0.4:
                curr_f = 5.0

            readings.append([
                b["bin_id"],
                r_time.isoformat(),
                round(curr_f, 1),
                weight,
                round(random.uniform(20.0, 31.0), 1),
                "HEALTHY",
                "VALID",
                "Routine periodic telemetry reading."
            ])

    with open(readings_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bin_id", "timestamp", "fill_percent", "weight_kg", "temperature", "sensor_status", "validation_status", "validation_reason"])
        for r in readings:
            writer.writerow(r)

    print(f"Generated {len(readings)} historical sensor readings in {readings_csv_path}")

    # 4. RECYCLING & COLLECTIONS (Historical records for KPI baseline)
    recycling_csv_path = os.path.join(output_dir, "recycling.csv")
    recycling_records = []
    collections_csv_path = os.path.join(output_dir, "collections.csv")
    collections_records = []

    for i in range(1, 41):
        col_id = f"COL-HIST-{i:04d}"
        wt = random.choice(["General", "Recyclable", "Organic"])
        tot_wt = round(random.uniform(180.0, 650.0), 1)
        rec_wt = round(tot_wt * 0.92 if wt == "Recyclable" else (tot_wt * 0.82 if wt == "Organic" else 0.0), 1)
        contam_wt = round(tot_wt * random.uniform(0.04, 0.12), 1)
        c_time = datetime.utcnow() - timedelta(days=random.randint(1, 25), hours=random.randint(1, 20))

        recycling_records.append([col_id, wt, tot_wt, rec_wt, contam_wt, c_time.isoformat()])
        collections_records.append([
            col_id,
            f"BIN-{(i % 25) + 1:03d}",
            f"TRUCK-{(i % 6) + 1:02d}",
            f"RT-HIST-{i:03d}",
            c_time.isoformat(),
            c_time.isoformat(),
            round(tot_wt * 4.5, 1),
            round(tot_wt * 4.5, 1),
            "VERIFIED",
            "Routine completed collection."
        ])

    with open(recycling_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["collection_id", "waste_type", "weight_kg", "recyclable_weight_kg", "contamination_weight_kg", "created_at"])
        for r in recycling_records:
            writer.writerow(r)

    with open(collections_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["collection_id", "bin_id", "vehicle_id", "route_id", "scheduled_time", "actual_collection_time", "estimated_volume", "actual_volume", "status", "operator_comment"])
        for c in collections_records:
            writer.writerow(c)

    print(f"Generated {len(recycling_records)} recycling and {len(collections_records)} collection records in data/")

if __name__ == "__main__":
    generate_all_datasets()
