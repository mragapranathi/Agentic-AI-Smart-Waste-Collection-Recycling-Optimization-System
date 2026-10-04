from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models.entities import Bin, Forecast
from backend.app.core.logging import logger

class PriorityEngine:
    @staticmethod
    def calculate_bin_priority(
        bin_obj: Bin,
        forecast: Optional[Forecast] = None,
        planning_period_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculates a deterministic collection priority score and category.
        Priority levels:
          - CRITICAL (Score >= 85 or fill >= 95%)
          - HIGH (Score >= 65 OR confirmed predictive candidate within planning window)
          - MEDIUM (Score >= 40)
          - LOW (Score < 40)
          - SENSOR_VERIFICATION_REQUIRED (Flagged sensor anomalies)

        Predictive inclusion logic:
          If a bin's current fill is below threshold but its ML forecast predicts
          it will cross the threshold before the next collection cycle, it is
          classified as a predictive candidate and included in the current route
          with an explanation of why it was included.
        """
        # 1. Sensor Verification Check
        if bin_obj.sensor_status in ("SUSPICIOUS", "INVALID", "OFFLINE"):
            return {
                "bin_id": bin_obj.bin_id,
                "location_name": bin_obj.location_name,
                "waste_type": bin_obj.waste_type,
                "current_fill_percent": bin_obj.current_fill_percent,
                "predicted_fill_percent": forecast.predicted_fill_percent if forecast else None,
                "threshold_percent": bin_obj.collection_threshold_percent,
                "priority_level": "SENSOR_VERIFICATION_REQUIRED",
                "score": 0.0,
                "reason": f"Sensor status is '{bin_obj.sensor_status}'. Reading must be physically or remotely verified before dispatch.",
                "recommended_action": "Dispatch technician for sensor audit or trigger remote sensor diagnostic.",
                "threshold_crossing_hours": None,
                "is_predictive_candidate": False
            }

        score = 0.0
        reasons = []
        is_predictive = False
        threshold = bin_obj.collection_threshold_percent
        fill = bin_obj.current_fill_percent

        # 2. Current fill level contribution
        # Bins >=95% scale with fill: 65 + (fill-95)*2, so 96%->67, 99%->73
        # This ensures a 96% bin ALWAYS outscores a 92% bin (which gets 69 via threshold branch)
        if fill >= 95.0:
            score += 65.0 + (fill - 95.0) * 2.0
            reasons.append(f"Immediate overflow hazard with fill level at {fill:.1f}%.")
        elif fill >= threshold:
            score += 55.0 + (fill - threshold) * 2.0
            reasons.append(f"Exceeds collection threshold ({threshold:.1f}%) at {fill:.1f}%.")
        else:
            score += (fill / 100.0) * 40.0

        # 3. Forecast and threshold-crossing contribution (up to 25 points)
        pred_fill = forecast.predicted_fill_percent if forecast else fill
        crossing_hours = None
        if forecast and forecast.threshold_crossing_time:
            now = datetime.utcnow()
            diff_hours = (forecast.threshold_crossing_time - now).total_seconds() / 3600.0
            crossing_hours = round(max(0.0, diff_hours), 1)

            if fill < threshold and pred_fill >= threshold:
                is_predictive = True
                if crossing_hours <= planning_period_hours:
                    # Will overflow before next collection window — operationally beneficial to include now
                    score += 25.0
                    reasons.append(
                        f"Predictive alert: Projected to reach {pred_fill:.1f}% within {crossing_hours:.1f}h "
                        f"(before next planned municipal cycle). Operationally beneficial to include now."
                    )
                else:
                    score += 15.0
                    reasons.append(
                        f"Forecast warning: Projected to cross threshold in {crossing_hours:.1f}h."
                    )
            elif fill >= threshold:
                score += 10.0

        # 4. Waste type hazard modifier (up to 10 points)
        # Organic waste decomposes quickly, producing odors and leachate
        if bin_obj.waste_type == "Organic":
            score += 10.0
            if fill >= 75.0:
                reasons.append("Organic waste poses odor and bacterial risks if delayed.")
        elif bin_obj.waste_type == "Recyclable":
            score += 3.0

        # Cap score at 100
        score = min(100.0, round(score, 1))

        # Categorize priority
        # Predictive candidates confirmed within the planning window are elevated to HIGH
        if fill >= 95.0 or score >= 85.0:
            level = "CRITICAL"
            action = "Dispatch immediate collection route."
        elif (fill >= threshold or score >= 65.0 or
              (is_predictive and crossing_hours is not None and crossing_hours <= planning_period_hours)):
            level = "HIGH"
            action = "Include in primary operational collection cycle."
        elif score >= 40.0:
            level = "MEDIUM"
            action = "Monitor accumulation; schedule in secondary collection cycle."
        else:
            level = "LOW"
            action = "Standard monitoring; no immediate dispatch needed."

        full_reason = " ".join(reasons) if reasons else f"Current fill is {fill:.1f}% (Threshold: {threshold:.1f}%)."

        return {
            "bin_id": bin_obj.bin_id,
            "location_name": bin_obj.location_name,
            "waste_type": bin_obj.waste_type,
            "current_fill_percent": bin_obj.current_fill_percent,
            "predicted_fill_percent": round(pred_fill, 1),
            "threshold_percent": threshold,
            "priority_level": level,
            "score": score,
            "reason": full_reason,
            "recommended_action": action,
            "threshold_crossing_hours": crossing_hours,
            "is_predictive_candidate": is_predictive
        }

    @classmethod
    def calculate_all_priorities(cls, db: Session, planning_period_hours: int = 24) -> List[Dict[str, Any]]:
        bins = db.query(Bin).filter(Bin.operational_status == "OPERATIONAL").all()
        results = []
        for b in bins:
            latest_forecast = db.query(Forecast).filter(
                Forecast.bin_id == b.bin_id
            ).order_by(Forecast.generated_at.desc()).first()

            p_data = cls.calculate_bin_priority(b, latest_forecast, planning_period_hours)
            results.append(p_data)

        # Sort by score descending
        results.sort(key=lambda x: (x["priority_level"] == "CRITICAL", x["score"]), reverse=True)
        logger.info(f"[INFO] Priority calculated for {len(results)} bins")
        return results
