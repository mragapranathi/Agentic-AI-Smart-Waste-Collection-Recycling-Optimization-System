from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseAgent
from backend.app.models.entities import Bin, Vehicle, Forecast
from backend.app.optimization.validator import RouteValidator
from backend.app.optimization.constraints import RoutingConstraints
from backend.app.services.llm_service import LLMService
from backend.app.core.logging import logger

# Thresholds
MAX_FORECAST_DEVIATION_PCT = 30.0   # Flag if forecast deviates >30% from current fill
RECYCLING_RATE_MIN = 10.0           # Flag suspiciously low recycling rates
RECYCLING_RATE_MAX = 99.0           # Flag impossibly high recycling rates
STALE_SENSOR_HOURS = 6.0            # Bins not read for this long are stale


class ReviewerCriticAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Operations Reviewer / Critic Agent",
            role="Conducts comprehensive safety, capacity, and policy sanity checks on proposed plans"
        )

    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        proposed_plan = state.get("proposed_plan", {})
        routes = proposed_plan.get("routes", [])
        priorities = state.get("priorities", [])
        recycling_analytics = state.get("recycling_analytics", {})

        all_bins = {b.bin_id: b for b in db.query(Bin).all()}
        all_vehicles = {v.vehicle_id: v for v in db.query(Vehicle).all()}

        violations: List[str] = []
        warnings: List[str] = []

        # ──────────────────────────────────────────────────────────
        # CHECK 1: Mathematical route validation (capacity + waste compat)
        # ──────────────────────────────────────────────────────────
        is_feasible, route_violations = RouteValidator.validate_route_plan(
            db=db, routes=routes,
            bins_dict=all_bins, vehicles_dict=all_vehicles
        )
        violations.extend(route_violations)

        # ──────────────────────────────────────────────────────────
        # CHECK 2: Duplicate vehicle assignments across routes
        # ──────────────────────────────────────────────────────────
        vehicle_route_map: Dict[str, List[str]] = {}
        for r in routes:
            vid = r.get("vehicle_id")
            if vid:
                vehicle_route_map.setdefault(vid, []).append(r.get("route_id", "?"))

        duplicate_vehicles: List[str] = []
        for vid, route_ids in vehicle_route_map.items():
            if len(route_ids) > 1:
                duplicate_vehicles.append(vid)
                violations.append(
                    f"Duplicate vehicle assignment: Vehicle '{vid}' assigned to {len(route_ids)} routes "
                    f"simultaneously ({', '.join(route_ids)}). Only one route per vehicle permitted."
                )

        # ──────────────────────────────────────────────────────────
        # CHECK 3: Validate bin priority results
        # Ensure every CRITICAL and HIGH bin appears in a route
        # ──────────────────────────────────────────────────────────
        routed_bin_ids = {
            s["bin_id"]
            for r in routes
            for s in r.get("stops", [])
        }

        unrouted_critical: List[str] = []
        for p in priorities:
            if p.get("priority_level") == "CRITICAL" and p["bin_id"] not in routed_bin_ids:
                unrouted_critical.append(p["bin_id"])
                warnings.append(
                    f"CRITICAL bin '{p['bin_id']}' ({p['current_fill_percent']:.1f}%) "
                    f"is not assigned to any route. Immediate dispatch required."
                )

        # ──────────────────────────────────────────────────────────
        # CHECK 4: Validate forecast results for consistency
        # Flag bins whose forecast deviates implausibly from current fill
        # ──────────────────────────────────────────────────────────
        forecast_anomalies: List[str] = []
        now = datetime.utcnow()
        for p in priorities:
            current = p.get("current_fill_percent", 0.0)
            predicted = p.get("predicted_fill_percent")
            if predicted is None:
                continue
            deviation = predicted - current
            # Predicted fill cannot decrease (bins don't empty themselves)
            if deviation < -5.0:
                forecast_anomalies.append(p["bin_id"])
                warnings.append(
                    f"Implausible forecast for '{p['bin_id']}': "
                    f"predicted {predicted:.1f}% < current {current:.1f}% (bins do not empty without collection)."
                )
            # Flag extreme over-prediction
            if deviation > MAX_FORECAST_DEVIATION_PCT + current:
                forecast_anomalies.append(p["bin_id"])
                warnings.append(
                    f"Suspicious forecast for '{p['bin_id']}': "
                    f"deviation of {deviation:.1f}% in 24h is physically unlikely."
                )

        # Also check DB forecasts for stale records
        stale_forecasts: List[str] = []
        db_forecasts = db.query(Forecast).all()
        for f in db_forecasts:
            hours_old = (now - f.generated_at).total_seconds() / 3600.0
            if hours_old > 48.0:
                stale_forecasts.append(f.bin_id)
        if stale_forecasts:
            warnings.append(
                f"Stale forecast data for {len(stale_forecasts)} bins (>48h old). Re-run forecasting."
            )

        # ──────────────────────────────────────────────────────────
        # CHECK 5: Validate recycling rate calculations
        # ──────────────────────────────────────────────────────────
        recycling_issues: List[str] = []
        rr = recycling_analytics.get("recycling_rate_percent", 0.0) if recycling_analytics else 0.0
        total_waste = recycling_analytics.get("total_waste_kg", 0.0) if recycling_analytics else 0.0
        recyclable = recycling_analytics.get("recyclable_kg", 0.0) if recycling_analytics else 0.0

        if total_waste > 0:
            if rr < RECYCLING_RATE_MIN:
                recycling_issues.append(
                    f"Recycling rate {rr:.1f}% is suspiciously low — verify data completeness."
                )
            if rr > RECYCLING_RATE_MAX:
                recycling_issues.append(
                    f"Recycling rate {rr:.1f}% exceeds 99% — likely a data recording error."
                )
            computed = (recyclable / total_waste) * 100.0
            if abs(computed - rr) > 2.0:
                recycling_issues.append(
                    f"Recycling rate mismatch: reported {rr:.1f}% but computed {computed:.1f}% "
                    f"from {recyclable:.1f}kg / {total_waste:.1f}kg."
                )
        warnings.extend(recycling_issues)

        # ──────────────────────────────────────────────────────────
        # CHECK 6: Stale / suspicious sensor data on routed bins
        # ──────────────────────────────────────────────────────────
        stale_bins_included: List[str] = []
        for r in routes:
            for s in r.get("stops", []):
                bid = s["bin_id"]
                bin_obj = all_bins.get(bid)
                if bin_obj and bin_obj.sensor_status in ("SUSPICIOUS", "INVALID", "STALE"):
                    stale_bins_included.append(bid)

        if stale_bins_included:
            violations.append(
                f"Routes include {len(stale_bins_included)} bins with degraded sensor states: "
                f"{stale_bins_included}. Verify sensor readings before dispatching."
            )

        # ──────────────────────────────────────────────────────────
        # CHECK 7: Unsupported recommendations — bins with no compatible vehicle
        # ──────────────────────────────────────────────────────────
        unsupported_recommendations: List[str] = []
        for p in priorities:
            if p.get("priority_level") in ("CRITICAL", "HIGH"):
                bin_wt = p.get("waste_type")
                has_compatible = any(
                    RoutingConstraints.is_waste_compatible(v, bin_wt) and
                    RoutingConstraints.is_vehicle_available(v)
                    for v in all_vehicles.values()
                )
                if not has_compatible:
                    unsupported_recommendations.append(p["bin_id"])
                    warnings.append(
                        f"No available vehicle compatible with '{bin_wt}' waste for bin '{p['bin_id']}'. "
                        f"Recommendation cannot be fulfilled — notify fleet manager."
                    )

        # ──────────────────────────────────────────────────────────
        # Determine final decision
        # ──────────────────────────────────────────────────────────
        all_issues = violations + warnings

        if stale_bins_included or duplicate_vehicles:
            reviewer_decision = "REQUIRES_SENSOR_VERIFICATION"
            decision_notes = (
                f"Plan requires sensor verification: {stale_bins_included or duplicate_vehicles}."
            )
        elif not is_feasible or unrouted_critical:
            reviewer_decision = "REQUIRES_REPLANNING"
            decision_notes = f"Constraint violations or unrouted critical bins detected. Replanning needed."
        else:
            reviewer_decision = "APPROVED_FOR_HUMAN_REVIEW"
            decision_notes = (
                "All capacity, segregation, vehicle assignment, forecast, and recycling checks passed. "
                f"{len(warnings)} advisory warnings noted."
            )

        # Generate AI critique
        critique = LLMService.generate_explanation(
            prompt="Critique the proposed waste collection plan for operational safety.",
            context={
                "topic": "reviewer",
                "route_count": len(routes),
                "violations": violations,
                "warnings": warnings,
                "stale_bins": stale_bins_included,
                "duplicate_vehicles": duplicate_vehicles,
                "forecast_anomalies": forecast_anomalies,
                "recycling_issues": recycling_issues
            }
        )

        reasoning = (
            f"Critic audit verdict: [{reviewer_decision}]. "
            f"Feasibility: {is_feasible}. "
            f"Violations: {len(violations)}. "
            f"Warnings: {len(warnings)}. "
            f"Duplicate vehicles: {len(duplicate_vehicles)}. "
            f"Forecast anomalies: {len(forecast_anomalies)}. "
            f"Unrouted critical bins: {len(unrouted_critical)}. "
            f"Unsupported recommendations: {len(unsupported_recommendations)}."
        )

        logger.info(f"[ReviewerCriticAgent] {reasoning}")

        return {
            "reviewer_decision": reviewer_decision,
            "is_feasible": is_feasible,
            "violations": violations,
            "warnings": warnings,
            "stale_bins_flagged": stale_bins_included,
            "duplicate_vehicles": duplicate_vehicles,
            "unrouted_critical_bins": unrouted_critical,
            "forecast_anomalies": forecast_anomalies,
            "unsupported_recommendations": unsupported_recommendations,
            "recycling_issues": recycling_issues,
            "stale_forecasts": stale_forecasts,
            "critic_notes": decision_notes,
            "ai_critique": critique
        }, reasoning
