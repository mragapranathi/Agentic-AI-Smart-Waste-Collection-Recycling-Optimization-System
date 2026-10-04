from datetime import datetime
from backend.app.models.entities import Bin, Vehicle, WorkflowRun, ApprovalRequest, AgentRun, Route
from backend.app.workflows.runner import WorkflowRunner
from backend.app.agents.bin_monitoring import BinMonitoringAgent
from backend.app.agents.forecasting import ForecastingAgent
from backend.app.agents.priority import PriorityAgent
from backend.app.agents.vehicle_capacity import VehicleCapacityAgent
from backend.app.agents.route_optimizer import RouteOptimizerAgent
from backend.app.agents.recycling import RecyclingAgent
from backend.app.agents.action_planning import ActionPlanningAgent
from backend.app.agents.reviewer_critic import ReviewerCriticAgent

def test_all_8_individual_agents(db_session):
    # Seed minimal environment
    b1 = Bin(bin_id="BIN-AG-01", location_name="Agent Loc 1", latitude=12.98, longitude=77.60, waste_type="General", capacity_liters=1000, current_fill_percent=92.0, current_weight_kg=200.0)
    b2 = Bin(bin_id="BIN-AG-02", location_name="Agent Loc 2", latitude=12.96, longitude=77.61, waste_type="Recyclable", capacity_liters=800, current_fill_percent=45.0, current_weight_kg=60.0)
    v1 = Vehicle(vehicle_id="TRUCK-AG-01", supported_waste_types=["General"], capacity_liters=8000.0, current_load_liters=0.0, latitude=12.9716, longitude=77.5946, status="AVAILABLE")
    db_session.add_all([b1, b2, v1])
    db_session.commit()

    wf_id = "WF-TEST-001"
    state = {"workflow_id": wf_id, "planning_period_hours": 24}

    # 1. Monitoring Agent
    a1 = BinMonitoringAgent()
    out1 = a1.execute(db_session, wf_id, state)
    assert out1["total_monitored"] >= 2
    state.update(out1)

    # 2. Forecasting Agent
    a2 = ForecastingAgent()
    out2 = a2.execute(db_session, wf_id, state)
    assert "forecasts" in out2
    state.update(out2)

    # 3. Priority Agent
    a3 = PriorityAgent()
    out3 = a3.execute(db_session, wf_id, state)
    assert "priorities" in out3
    state.update(out3)

    # 4. Vehicle Capacity Agent
    a4 = VehicleCapacityAgent()
    out4 = a4.execute(db_session, wf_id, state)
    assert out4["total_available_units"] >= 1
    state.update(out4)

    # 5. Route Optimizer Agent
    a5 = RouteOptimizerAgent()
    out5 = a5.execute(db_session, wf_id, state)
    assert "routes" in out5
    state.update(out5)

    # 6. Recycling Agent
    a6 = RecyclingAgent()
    out6 = a6.execute(db_session, wf_id, state)
    assert "recycling_analytics" in out6
    state.update(out6)

    # 7. Action Planning Agent
    a7 = ActionPlanningAgent()
    out7 = a7.execute(db_session, wf_id, state)
    assert out7["approval_state"] == "PENDING_HUMAN_APPROVAL"
    state.update(out7)

    # 8. Reviewer Critic Agent
    a8 = ReviewerCriticAgent()
    out8 = a8.execute(db_session, wf_id, state)
    assert out8["reviewer_decision"] in ("APPROVED_FOR_HUMAN_REVIEW", "REQUIRES_REPLANNING", "REQUIRES_SENSOR_VERIFICATION")

    # Verify agent_runs records were persisted in DB
    runs = db_session.query(AgentRun).filter(AgentRun.workflow_id == wf_id).all()
    assert len(runs) == 8
    for r in runs:
        assert r.status == "SUCCESS"
        assert r.reasoning_summary is not None
        assert len(r.reasoning_summary) > 0

def test_full_workflow_and_approval(db_session):
    # Seed operational data
    b1 = Bin(bin_id="BIN-WF-01", location_name="WF Loc 1", latitude=12.98, longitude=77.60, waste_type="General", capacity_liters=1000, current_fill_percent=94.0, current_weight_kg=210.0)
    v1 = Vehicle(vehicle_id="TRUCK-WF-01", supported_waste_types=["General"], capacity_liters=8000.0, current_load_liters=0.0, latitude=12.9716, longitude=77.5946, status="AVAILABLE")
    db_session.add_all([b1, v1])
    db_session.commit()

    # Run complete workflow
    final_state = WorkflowRunner.run_optimization_workflow(db_session)
    wf_id = final_state["workflow_id"]

    # Check workflow state in DB
    wf_run = db_session.query(WorkflowRun).filter(WorkflowRun.workflow_id == wf_id).first()
    assert wf_run is not None
    assert wf_run.current_state == "WAITING_FOR_APPROVAL"
    assert wf_run.status == "WAITING_APPROVAL"

    # Verify approval request was created
    approval = db_session.query(ApprovalRequest).filter(ApprovalRequest.workflow_id == wf_id).first()
    assert approval is not None
    assert approval.status == "PENDING"

    # Approve the plan
    approved_res = WorkflowRunner.approve_workflow_plan(db_session, workflow_id=wf_id, operator="Director of Municipal Services", comment="Approved for morning shift")
    assert approved_res["status"] == "APPROVED"

    # Verify routes were activated in DB
    routes = db_session.query(Route).filter(Route.route_status == "APPROVED").all()
    assert len(routes) >= 1
