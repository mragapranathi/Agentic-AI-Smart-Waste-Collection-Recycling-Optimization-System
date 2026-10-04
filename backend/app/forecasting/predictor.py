import os
import joblib
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.models.entities import Bin, SensorReading, Forecast
from backend.app.forecasting.threshold import calculate_threshold_crossing
from backend.app.core.logging import logger

MODEL_PATH = "ml/models/forecasting_model.joblib"
BASELINE_PATH = "ml/models/baseline_model.joblib"

class ForecastService:
    _ml_model = None
    _baseline_model = None

    @classmethod
    def load_models(cls):
        if cls._ml_model is None and os.path.exists(MODEL_PATH):
            try:
                cls._ml_model = joblib.load(MODEL_PATH)
                logger.info("Loaded production ML forecasting model from artifact.")
            except Exception as e:
                logger.error(f"Failed to load ML model artifact: {e}")

        if cls._baseline_model is None and os.path.exists(BASELINE_PATH):
            try:
                cls._baseline_model = joblib.load(BASELINE_PATH)
                logger.info("Loaded baseline forecasting model from artifact.")
            except Exception as e:
                logger.error(f"Failed to load baseline model artifact: {e}")

    @classmethod
    def predict_bin(
        cls,
        db: Session,
        bin_obj: Bin,
        horizon_hours: int = 24,
        persist: bool = True
    ) -> Dict[str, Any]:
        cls.load_models()
        now = datetime.utcnow()

        # Calculate time since collection
        time_since_collection = 24.0
        if bin_obj.last_collection_time:
            time_since_collection = max(0.5, (now - bin_obj.last_collection_time).total_seconds() / 3600.0)

        # Retrieve recent readings to compute delta and growth rate
        recent_readings = db.query(SensorReading).filter(
            SensorReading.bin_id == bin_obj.bin_id
        ).order_by(SensorReading.timestamp.desc()).limit(5).all()

        prev_fill = bin_obj.current_fill_percent
        if len(recent_readings) > 1:
            prev_fill = recent_readings[1].fill_percent

        fill_change = bin_obj.current_fill_percent - prev_fill

        # Estimate historical growth rate (%/day)
        base_daily_growth = 10.0
        if bin_obj.waste_type == "Organic":
            base_daily_growth = 14.0
        elif bin_obj.waste_type == "Recyclable":
            base_daily_growth = 8.0

        if len(recent_readings) >= 2:
            time_delta_hours = max(0.1, (recent_readings[0].timestamp - recent_readings[-1].timestamp).total_seconds() / 3600.0)
            fill_delta = recent_readings[0].fill_percent - recent_readings[-1].fill_percent
            if fill_delta > 0:
                base_daily_growth = (fill_delta / time_delta_hours) * 24.0

        input_data = pd.DataFrame([{
            "current_fill_percent": float(bin_obj.current_fill_percent),
            "prev_fill_percent": float(prev_fill),
            "fill_change": float(fill_change),
            "hour_of_day": int(now.hour),
            "day_of_week": int(now.weekday()),
            "waste_type": bin_obj.waste_type,
            "capacity_liters": float(bin_obj.capacity_liters),
            "time_since_collection_hours": float(time_since_collection),
            "historical_growth_rate": float(base_daily_growth)
        }])

        # Perform ML prediction
        prediction_type = "ML_PREDICTION"
        model_name = "RandomForestRegressor"
        model_version = "v1.0"
        confidence_metric = 1.638  # MAE on test set

        if cls._ml_model:
            pred_val = float(cls._ml_model.predict(input_data)[0])
        elif cls._baseline_model:
            pred_val = float(cls._baseline_model.predict(input_data)[0])
            prediction_type = "BASELINE_ESTIMATE"
            model_name = "LinearRegression"
        else:
            # Deterministic linear fallback
            hourly_rate = base_daily_growth / 24.0
            pred_val = bin_obj.current_fill_percent + (hourly_rate * horizon_hours)
            prediction_type = "BASELINE_ESTIMATE"
            model_name = "DeterministicLinearBaseline"

        # Constrain to 0-100%
        pred_val = min(100.0, max(bin_obj.current_fill_percent, pred_val))

        # Hourly rate for threshold crossing
        hourly_growth_rate = max(0.1, (pred_val - bin_obj.current_fill_percent) / float(horizon_hours))
        crossing_time, hours_remaining = calculate_threshold_crossing(
            current_fill=bin_obj.current_fill_percent,
            threshold=bin_obj.collection_threshold_percent,
            hourly_growth_rate=hourly_growth_rate,
            current_time=now
        )

        result = {
            "bin_id": bin_obj.bin_id,
            "horizon_hours": horizon_hours,
            "current_fill_percent": round(bin_obj.current_fill_percent, 1),
            "predicted_fill_percent": round(pred_val, 1),
            "threshold_crossing_time": crossing_time,
            "hours_until_threshold": hours_remaining,
            "prediction_type": prediction_type,
            "model_name": model_name,
            "model_version": model_version,
            "confidence_or_error_metric": confidence_metric
        }

        if persist:
            forecast_record = Forecast(
                bin_id=bin_obj.bin_id,
                generated_at=now,
                horizon_hours=horizon_hours,
                predicted_fill_percent=result["predicted_fill_percent"],
                threshold_crossing_time=result["threshold_crossing_time"],
                model_name=result["model_name"],
                model_version=result["model_version"],
                prediction_type=result["prediction_type"],
                confidence_or_error_metric=result["confidence_or_error_metric"]
            )
            db.add(forecast_record)
            db.commit()
            db.refresh(forecast_record)
            result["id"] = forecast_record.id

        return result

    @classmethod
    def run_all_forecasts(cls, db: Session, horizon_hours: int = 24) -> List[Dict[str, Any]]:
        bins = db.query(Bin).filter(Bin.operational_status == "OPERATIONAL").all()
        results = []
        for b in bins:
            res = cls.predict_bin(db, b, horizon_hours=horizon_hours, persist=True)
            results.append(res)
        logger.info(f"[INFO] Forecast generated for {len(results)} operational bins")
        return results
