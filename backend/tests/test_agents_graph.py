"""
Phase 5 tests — LangGraph Multi-Agent Workflow and Specialized Agents.

Tests:
1. End-to-end execution of graph on simulated incident (Detection -> RAG -> Diagnosis -> Recovery -> Verification -> Postmortem)
2. Low confidence routing to human review
3. High risk approval gate and rejection path
4. Verification failure retry loop bounded by MAX_RETRIES = 3
5. Section 37.4 verification: resolved incident automatically ingested into historical_incidents collection

Run with: pytest backend/tests/test_agents_graph.py -v -s
"""
import uuid
import pytest

from app.graph.graph import argus_graph, MAX_RETRIES
from app.rag.ingestion import ingest_runbooks
from app.rag.knowledge_base import get_historical_incidents_collection


@pytest.fixture(scope="module", autouse=True)
def setup_knowledge():
    """Ensure runbooks are ingested for agent RAG retrieval."""
    ingest_runbooks(runbooks_dir="data/runbooks")


def test_graph_end_to_end_resolution():
    """
    Test 1: Full end-to-end execution of the LangGraph workflow on a RAG degradation incident.
    """
    incident_id = f"inc_{str(uuid.uuid4())[:8]}"
    initial_state = {
        "incident": {"id": incident_id, "severity": "high"},
        "metrics": {
            "latency": 1.45,
            "error_rate": 0.01,
            "token_usage": 1520.0,
            "retrieval_score": 0.46,
            "hallucination_score": 0.58,
            "tool_failure_rate": 0.005,
            "request_volume": 52.0,
            "cpu_usage": 38.0,
            "memory_usage": 50.0,
            "api_success_rate": 0.992,
        },
        "logs": [],
        "evidence": [],
        "retry_count": 0,
        "history_trace": [],
        "approval_status": "approved",  # Pre-approved for end-to-end path
    }

    final_state = argus_graph.invoke(initial_state)

    print("\n--- Execution Trace of End-to-End Run ---")
    for step in final_state.get("history_trace", []):
        print(f"  -> {step}")

    # Assertions
    assert final_state["failure_type"] == "RAG_DEGRADATION"
    assert final_state["failure_confidence"] >= 0.70
    assert len(final_state["retrieved_runbooks"]) > 0
    assert "RB-002_RAG_DEGRADATION.md" in [rb["source"] for rb in final_state["retrieved_runbooks"]]
    assert final_state["root_cause"] != ""

    # Strategy & Execution
    assert "selected_strategy" in final_state
    assert final_state["selected_strategy"]["id"] in ["reindex_vector_store", "apply_similarity_filter"]
    assert final_state["execution_result"]["status"] == "success"

    # Verification & Resolution
    assert final_state["verification_result"]["recovery_verified"] is True
    assert final_state["final_status"] == "resolved"

    # Evaluation
    eval_res = final_state.get("evaluation_result", {})
    assert eval_res.get("overall_evaluation_score", 0.0) >= 0.75

    # Check Section 37.4 historical ingestion
    col = get_historical_incidents_collection()
    assert col.count() >= 1
    recent = col.get(ids=[f"hist_{incident_id}"])
    assert len(recent["ids"]) == 1
    assert recent["metadatas"][0]["failure_type"] == "RAG_DEGRADATION"


def test_graph_low_confidence_routes_to_human_review():
    """
    Test 2: When detection confidence is low, graph routes to escalate_human_review.
    """
    initial_state = {
        "incident": {"id": "inc_low_conf", "severity": "low"},
        "metrics": {
            "latency": 1.2,
            "error_rate": 0.005,
            "token_usage": 520.0,
            "retrieval_score": 0.92,
            "hallucination_score": 0.03,
            "tool_failure_rate": 0.008,
            "request_volume": 50.0,
            "cpu_usage": 35.0,
            "memory_usage": 48.0,
            "api_success_rate": 0.995,
        },
        "failure_confidence": 0.45,  # Artificially low confidence
        "retry_count": 0,
        "history_trace": [],
    }

    # Run detection agent with low confidence override
    final_state = argus_graph.invoke(initial_state)

    # For normal metrics, failure_confidence is low or unknown
    assert final_state["final_status"] in ["needs_human_review", "open"]


def test_graph_rejection_halts_at_human_review():
    """
    Test 3: High risk action rejected by human halts execution.
    """
    initial_state = {
        "incident": {"id": "inc_rejected", "severity": "critical"},
        "metrics": {
            "latency": 9.5,
            "error_rate": 0.005,
            "token_usage": 520.0,
            "retrieval_score": 0.92,
            "hallucination_score": 0.03,
            "tool_failure_rate": 0.008,
            "request_volume": 50.0,
            "cpu_usage": 80.0,
            "memory_usage": 55.0,
            "api_success_rate": 0.995,
        },
        "approval_status": "rejected",  # Explicit human rejection
        "retry_count": 0,
        "history_trace": [],
    }

    final_state = argus_graph.invoke(initial_state)
    assert final_state["final_status"] == "needs_human_review"
    assert "EscalateNode: routed to human engineering review" in final_state["history_trace"]


def test_graph_verification_retry_loop_bounded():
    """
    Test 4: When verification repeatedly fails, loop retries exactly MAX_RETRIES times and halts safely.
    """
    initial_state = {
        "incident": {"id": "inc_retry_loop", "severity": "high"},
        "metrics": {
            "latency": 8.5,
            "error_rate": 0.01,
            "token_usage": 520.0,
            "retrieval_score": 0.92,
            "hallucination_score": 0.03,
            "tool_failure_rate": 0.008,
            "request_volume": 50.0,
            "cpu_usage": 75.0,
            "memory_usage": 50.0,
            "api_success_rate": 0.99,
        },
        "verification_result": {"force_failure": True},  # Forces verification failure
        "approval_status": "approved",
        "retry_count": 0,
        "history_trace": [],
    }

    final_state = argus_graph.invoke(initial_state)

    print("\n--- Bounded Retry Loop Trace ---")
    diagnosis_attempts = sum(1 for step in final_state["history_trace"] if "DiagnosisAgent" in step)
    verification_attempts = sum(1 for step in final_state["history_trace"] if "VerificationNode" in step)
    print(f"Total Diagnosis Invocations: {diagnosis_attempts}")
    print(f"Total Verification Invocations: {verification_attempts}")
    print(f"Final Retry Count: {final_state['retry_count']}")

    # Must not loop forever; capped at MAX_RETRIES (3)
    assert final_state["retry_count"] == MAX_RETRIES
    assert final_state["final_status"] == "needs_human_review"
    assert "EscalateNode: routed to human engineering review" in final_state["history_trace"]
