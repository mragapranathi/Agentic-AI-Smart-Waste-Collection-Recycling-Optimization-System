from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseAgent
from backend.app.services.priority_engine import PriorityEngine

class PriorityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Collection Priority Agent",
            role="Evaluates fill levels, forecast trajectories, and operational risks into prioritized dispatch queues"
        )

    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        planning_period = state.get("planning_period_hours", 24)
        priorities = PriorityEngine.calculate_all_priorities(db, planning_period_hours=planning_period)

        critical_bins = [p for p in priorities if p["priority_level"] == "CRITICAL"]
        high_bins = [p for p in priorities if p["priority_level"] == "HIGH"]
        predictive_candidates = [p for p in priorities if p.get("is_predictive_candidate")]
        verification_required = [p for p in priorities if p["priority_level"] == "SENSOR_VERIFICATION_REQUIRED"]

        reasoning = (
            f"Evaluated {len(priorities)} bins. Categorized {len(critical_bins)} as CRITICAL, "
            f"{len(high_bins)} as HIGH, and {len(predictive_candidates)} as predictive inclusion candidates. "
            f"{len(verification_required)} sensor audits required."
        )

        return {
            "priorities": priorities,
            "critical_count": len(critical_bins),
            "high_count": len(high_bins),
            "predictive_candidate_count": len(predictive_candidates),
            "verification_required_count": len(verification_required)
        }, reasoning
