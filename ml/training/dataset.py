import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_training_data(n_samples: int = 5000, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates synthetic historical waste accumulation data for ML model training.
    Reflects diurnal cycles, waste type accumulation velocities, and day-of-week patterns.
    """
    np.random.seed(random_seed)

    waste_types = ["General", "Recyclable", "Organic"]
    # Base daily growth rate by waste type (% per day)
    growth_rates = {
        "General": (6.0, 16.0),
        "Recyclable": (4.0, 12.0),
        "Organic": (8.0, 22.0)
    }

    records = []
    base_time = datetime(2026, 1, 1, 8, 0, 0)

    for i in range(n_samples):
        w_type = np.random.choice(waste_types)
        min_rate, max_rate = growth_rates[w_type]
        base_rate = np.random.uniform(min_rate, max_rate)

        # Current fill percent
        current_fill = np.random.uniform(10.0, 95.0)
        # Hours since last collection
        hours_since_collection = np.random.uniform(2.0, 120.0)
        # Hour of day (0-23)
        hour = np.random.randint(0, 24)
        # Day of week (0-6)
        day_of_week = np.random.randint(0, 7)
        # Capacity
        capacity_liters = float(np.random.choice([800, 1000, 1200, 1500]))

        # Previous fill (6 hours ago)
        prev_fill = max(0.0, current_fill - (base_rate / 24.0 * 6.0) + np.random.normal(0, 1.0))
        fill_change = current_fill - prev_fill

        # Horizon: predict 24 hours into the future
        horizon_hours = 24.0

        # Weekend modifier (organic and recyclable increase on weekends)
        weekend_mult = 1.3 if day_of_week in [5, 6] and w_type in ["Organic", "Recyclable"] else 1.0
        # Peak business hour modifier (10:00 to 18:00)
        peak_mult = 1.2 if (10 <= hour <= 18) and w_type == "General" else 1.0

        daily_growth = base_rate * weekend_mult * peak_mult
        hourly_growth = daily_growth / 24.0

        future_fill = current_fill + (hourly_growth * horizon_hours) + np.random.normal(0, 2.0)
        future_fill = min(100.0, max(0.0, future_fill))

        records.append({
            "current_fill_percent": round(current_fill, 2),
            "prev_fill_percent": round(prev_fill, 2),
            "fill_change": round(fill_change, 2),
            "hour_of_day": hour,
            "day_of_week": day_of_week,
            "waste_type": w_type,
            "capacity_liters": capacity_liters,
            "time_since_collection_hours": round(hours_since_collection, 1),
            "historical_growth_rate": round(daily_growth, 2),
            "future_fill_percent": round(future_fill, 2)
        })

    df = pd.DataFrame(records)
    return df
