from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class WorkflowState(BaseModel):
    workflow_id: str
    current_state: str = "INITIATED"
    planning_period_hours: int = 24
    monitored_bins: List[Dict[str, Any]] = Field(default_factory=list)
    forecasts: List[Dict[str, Any]] = Field(default_factory=list)
    priorities: List[Dict[str, Any]] = Field(default_factory=list)
    available_vehicles: List[Dict[str, Any]] = Field(default_factory=list)
    routes: List[Dict[str, Any]] = Field(default_factory=list)
    unassigned_bins: List[Dict[str, Any]] = Field(default_factory=list)
    recycling_analytics: Dict[str, Any] = Field(default_factory=dict)
    proposed_plan: Dict[str, Any] = Field(default_factory=dict)
    reviewer_decision: str = "PENDING"
    is_feasible: bool = True
    violations: List[str] = Field(default_factory=list)
    approval_state: str = "PENDING"
    replan_count: int = 0
    requires_human_approval: bool = True
