from typing import Dict, Any
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from backend.app.agents.bin_monitoring import BinMonitoringAgent
from backend.app.agents.forecasting import ForecastingAgent
from backend.app.agents.priority import PriorityAgent
from backend.app.agents.vehicle_capacity import VehicleCapacityAgent
from backend.app.agents.route_optimizer import RouteOptimizerAgent
from backend.app.agents.recycling import RecyclingAgent
from backend.app.agents.action_planning import ActionPlanningAgent
from backend.app.agents.reviewer_critic import ReviewerCriticAgent
from backend.app.core.logging import logger


def build_waste_workflow_graph(db: Session):
    """
    Builds a stateful LangGraph workflow representing the 8-agent municipal decision chain.
    Nodes bind to the current active database session in closure.

    IMPORTANT: LangGraph StateGraph(dict) *replaces* the full state with whatever a node returns.
    Every node wrapper must therefore spread the incoming state and overlay new keys on top,
    so that 'workflow_id', 'planning_period_hours', and all previously accumulated keys survive
    across node boundaries.
    """
    graph = StateGraph(dict)

    bin_agent = BinMonitoringAgent()
    forecast_agent = ForecastingAgent()
    priority_agent = PriorityAgent()
    vehicle_agent = VehicleCapacityAgent()
    route_agent = RouteOptimizerAgent()
    recycling_agent = RecyclingAgent()
    planning_agent = ActionPlanningAgent()
    reviewer_agent = ReviewerCriticAgent()

    # -----------------------------------------------------------------------
    # Node wrappers — each spreads the current state before adding new keys
    # so LangGraph's full-state replacement does not drop upstream data.
    # -----------------------------------------------------------------------

    def run_bin_monitoring(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = bin_agent.execute(db, wf_id, state)
        return {**state, **res, "current_state": "VALIDATED"}

    def run_forecasting(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = forecast_agent.execute(db, wf_id, state)
        return {**state, **res, "current_state": "FORECASTED"}

    def run_priority(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = priority_agent.execute(db, wf_id, state)
        return {**state, **res, "current_state": "PRIORITIZED"}

    def run_vehicle_capacity(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = vehicle_agent.execute(db, wf_id, state)
        return {**state, **res, "current_state": "VEHICLES_ASSIGNED"}

    def run_route_optimizer(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = route_agent.execute(db, wf_id, state)
        return {**state, **res, "current_state": "ROUTES_OPTIMIZED"}

    def run_recycling(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = recycling_agent.execute(db, wf_id, state)
        return {**state, **res, "current_state": "RECYCLING_AUDITED"}

    def run_action_planning(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = planning_agent.execute(db, wf_id, state)
        return {**state, **res, "current_state": "PLAN_PROPOSED"}

    def run_reviewer(state: dict) -> dict:
        wf_id = state["workflow_id"]
        res = reviewer_agent.execute(db, wf_id, state)
        replan_count = state.get("replan_count", 0)
        decision = res.get("reviewer_decision")
        if decision == "REQUIRES_REPLANNING":
            replan_count += 1
        return {**state, **res, "replan_count": replan_count, "current_state": "REVIEWED"}

    # Add Nodes
    graph.add_node("bin_monitoring", run_bin_monitoring)
    graph.add_node("forecasting", run_forecasting)
    graph.add_node("priority", run_priority)
    graph.add_node("vehicle_capacity", run_vehicle_capacity)
    graph.add_node("route_optimizer", run_route_optimizer)
    graph.add_node("recycling", run_recycling)
    graph.add_node("action_planning", run_action_planning)
    graph.add_node("reviewer_critic", run_reviewer)

    # Set Entry Point
    graph.set_entry_point("bin_monitoring")

    # Sequential Edges
    graph.add_edge("bin_monitoring", "forecasting")
    graph.add_edge("forecasting", "priority")
    graph.add_edge("priority", "vehicle_capacity")
    graph.add_edge("vehicle_capacity", "route_optimizer")
    graph.add_edge("route_optimizer", "recycling")
    graph.add_edge("recycling", "action_planning")
    graph.add_edge("action_planning", "reviewer_critic")

    # Conditional Routing from Reviewer
    def route_decision(state: dict) -> str:
        decision = state.get("reviewer_decision")
        replan_count = state.get("replan_count", 0)

        # Allow at most 1 replan iteration; then proceed to completion/operator review
        if decision == "REQUIRES_REPLANNING" and replan_count <= 1:
            logger.warning(f"Reviewer triggered replanning (iteration {replan_count})")
            return "route_optimizer"
        return END

    graph.add_conditional_edges("reviewer_critic", route_decision, {
        "route_optimizer": "route_optimizer",
        END: END
    })

    return graph.compile()
