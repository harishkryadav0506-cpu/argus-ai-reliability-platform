"""
Phase 7 Tests — Human-in-the-Loop Approval, Native Interrupt/Resume, and Verification (Sections 13, 15, 16)

Tests:
1. GET /api/incidents/{id}/recovery-options returns Section 15 counterfactual simulator schema.
2. Full approve -> execute -> verify-success path (using LangGraph interrupt/resume).
3. Approve -> execute -> verify-failure -> re-diagnose path (bounded retry logic).
4. Reject path halts workflow and escalates to human engineers.

Run with: pytest backend/tests/test_phase7_approval_verification.py -v -s
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from langgraph.types import Command

from app.main import app
from app.graph.graph import argus_graph, MAX_RETRIES
from app.services import incident_service, recovery_service
from app.ml.failure_prediction import FailureCategory

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    recovery_service.clear_in_memory_recovery_actions()
    yield


def test_recovery_options_counterfactual_schema():
    """
    Section 15 & 23:
    GET /api/incidents/{id}/recovery-options returns candidate strategies with grounded
    success probabilities, risk scores, reversibility, and potential impact before approval.
    """
    # 1. Create incident
    inc = incident_service.create_incident(
        title="Elevated LLM Gateway Timeouts",
        severity="high",
        failure_type=FailureCategory.LLM_FAILURE,
        confidence=0.92,
        metrics={"latency": 4.8, "error_rate": 0.28, "api_success_rate": 0.70},
    )

    # 2. Query recovery options
    response = client.get(f"/api/incidents/{inc.id}/recovery-options")
    assert response.status_code == 200
    data = response.json()

    assert data["incident_id"] == inc.id
    assert data["failure_type"] == FailureCategory.LLM_FAILURE
    assert "approval_required" in data
    assert "risk_score" in data
    assert "recommended_strategy" in data
    assert "strategies" in data

    rec = data["recommended_strategy"]
    assert "id" in rec
    assert "action" in rec
    assert "success_probability" in rec
    assert "risk_score" in rec
    assert "reversibility" in rec
    assert "rationale" in rec

    for s in data["strategies"]:
        assert 0.0 <= s["success_probability"] <= 1.0
        assert 0.0 <= s["risk_score"] <= 1.0
        assert s["reversibility"] in ["high", "medium", "low"]


def test_full_approve_execute_verify_success_path():
    """
    Full approve -> execute -> verify-success path:
    1. Incident workflow starts and triggers high-risk action (restart_service).
    2. Workflow halts via LangGraph interrupt() with status='pending'.
    3. POST /api/incidents/{id}/approve resumes thread with approved=True.
    4. Action executes, before/after metrics verified against SLA, incident marked resolved.
    """
    inc_id = f"inc_approve_{uuid.uuid4().hex[:8]}"
    inc = incident_service.create_incident(
        title="High Latency Gateway Backpressure",
        severity="high",
        failure_type=FailureCategory.LATENCY_SPIKE,
        confidence=0.95,
        metrics={"latency": 8.5, "cpu_usage": 75.0, "api_success_rate": 0.91},
    )
    # Ensure thread_id matches incident id
    inc.id = inc_id

    initial_state = {
        "incident": {"id": inc_id, "severity": "high"},
        "metrics": {"latency": 8.5, "cpu_usage": 75.0, "api_success_rate": 0.91},
        "failure_confidence": 0.95,
        "history_trace": [],
        "retry_count": 0,
    }

    config = {"configurable": {"thread_id": inc_id}}

    # 1. Run graph up to interrupt
    out = argus_graph.invoke(initial_state, config=config)
    assert "__interrupt__" in out, "Graph should pause at approval gate"
    interrupt_info = out["__interrupt__"][0].value
    assert interrupt_info["incident_id"] == inc_id

    # 2. Check RecoveryAction was logged as pending
    actions = recovery_service.get_recovery_actions_for_incident(inc_id)
    assert len(actions) >= 1
    assert actions[0]["approval_status"] == "pending"

    # 3. Call POST /api/incidents/{id}/approve to resume
    approve_resp = client.post(
        f"/api/incidents/{inc_id}/approve",
        json={"notes": "Approved by Senior SRE on-call", "actor": "sre:alice"},
    )
    assert approve_resp.status_code == 200
    res_data = approve_resp.json()

    assert res_data["approval_status"] == "approved"
    assert res_data["execution_status"] == "executed"
    assert res_data["verification"]["recovery_verified"] is True

    # 4. Check database state
    updated_inc = incident_service.get_incident(inc_id)
    assert updated_inc.status == "resolved"


def test_approve_execute_verify_failure_retry_path():
    """
    Approve -> execute -> verify-failure -> re-diagnose path:
    1. Incident workflow starts and interrupts.
    2. Simulated verification failure is injected in state.
    3. When approved, execution proceeds, but verification explicitly fails.
    4. Graph loops back to diagnosis with incremented retry_count (bounded by MAX_RETRIES).
    """
    inc_id = f"inc_retry_{uuid.uuid4().hex[:8]}"
    incident_service.create_incident(
        title="Persistent Latency Spike",
        severity="high",
        failure_type=FailureCategory.LATENCY_SPIKE,
        confidence=0.95,
        metrics={"latency": 8.5, "cpu_usage": 75.0, "api_success_rate": 0.91},
    )

    initial_state = {
        "incident": {"id": inc_id, "severity": "high"},
        "metrics": {"latency": 8.5, "cpu_usage": 75.0, "api_success_rate": 0.91},
        "verification_result": {"force_failure": True},  # Forces verification failure
        "failure_confidence": 0.95,
        "history_trace": [],
        "retry_count": 0,
    }
    config = {"configurable": {"thread_id": inc_id}}

    # 1. Run graph up to interrupt
    out = argus_graph.invoke(initial_state, config=config)
    assert "__interrupt__" in out

    # 2. Resume graph with approval
    resume_cmd = Command(resume={"approved": True})
    final_state = argus_graph.invoke(resume_cmd, config=config)

    # 3. Verify that verification failed and loop repeated up to MAX_RETRIES (3)
    assert final_state["verification_result"]["recovery_verified"] is False
    assert final_state["retry_count"] >= MAX_RETRIES
    assert "EscalateNode: routed to human engineering review" in final_state["history_trace"]


def test_reject_path_halts_and_escalates():
    """
    Reject path:
    1. Graph halts at approval gate via interrupt().
    2. POST /api/incidents/{id}/reject called.
    3. LangGraph thread resumed with approved=False.
    4. Graph halts at escalate_human_review without executing MCP action.
    5. Incident status updated to 'escalated'.
    """
    inc_id = f"inc_reject_{uuid.uuid4().hex[:8]}"
    inc = incident_service.create_incident(
        title="Uncertain Agent Stagnation",
        severity="high",
        failure_type=FailureCategory.AGENT_LOOP,
        confidence=0.88,
    )
    inc.id = inc_id

    initial_state = {
        "incident": {"id": inc_id, "severity": "high"},
        "metrics": {"tool_failure_rate": 0.15, "token_usage": 3200.0},
        "failure_confidence": 0.88,
        "history_trace": [],
        "retry_count": 0,
    }
    config = {"configurable": {"thread_id": inc_id}}

    # 1. Run graph up to interrupt
    out = argus_graph.invoke(initial_state, config=config)
    assert "__interrupt__" in out

    # 2. Call POST /api/incidents/{id}/reject
    reject_resp = client.post(
        f"/api/incidents/{inc_id}/reject",
        json={"notes": "Risky action rejected. Will investigate manually.", "actor": "lead:bob"},
    )
    assert reject_resp.status_code == 200
    res_data = reject_resp.json()

    assert res_data["approval_status"] == "rejected"
    assert res_data["execution_status"] == "blocked"
    assert "escalated" in res_data["message"]

    # 3. Confirm incident status is escalated
    updated_inc = incident_service.get_incident(inc_id)
    assert updated_inc.status == "escalated"
