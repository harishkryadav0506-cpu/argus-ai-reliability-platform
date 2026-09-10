"""
Phase 2 tests — Simulation Engine, Fault Injection, and Incident Creation.

Run with: pytest backend/tests/test_simulation.py -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.models import Base, Incident, MetricSnapshot
from app.database.session import get_db
from app.schemas.simulation import FaultType
from app.services.simulation_service import SimulationEngine, simulation_engine
from app.services import incident_service

client = TestClient(app)

# Test SQLite in-memory database for isolated DB testing
test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clean_simulation_state():
    """Ensure simulation is in normal state before each test."""
    simulation_engine.reset_to_normal()
    yield
    simulation_engine.reset_to_normal()


# --- 1. Metric Generation Tests ---

def test_normal_metrics_contain_all_ten_keys():
    engine = SimulationEngine()
    metrics = engine.generate_metrics()

    expected_keys = [
        "latency",
        "error_rate",
        "token_usage",
        "retrieval_score",
        "hallucination_score",
        "tool_failure_rate",
        "request_volume",
        "cpu_usage",
        "memory_usage",
        "api_success_rate",
    ]
    for key in expected_keys:
        assert key in metrics, f"Missing metric: {key}"
        assert isinstance(metrics[key], (int, float))

    # Baseline health assertions
    assert 0.5 <= metrics["latency"] <= 3.0
    assert metrics["error_rate"] < 0.05
    assert metrics["retrieval_score"] > 0.75
    assert metrics["api_success_rate"] > 0.95


# --- 2. Fault Injection Tests ---

@pytest.mark.parametrize("fault_type", FaultType.ALL)
def test_each_fault_type_injection(fault_type):
    engine = SimulationEngine()
    engine.inject_fault(fault_type, severity="high", duration_seconds=60)
    assert engine.is_fault_active
    assert engine._active_fault == fault_type

    point = engine.tick()
    metrics = point["metrics"]

    if fault_type == FaultType.LATENCY_SPIKE:
        assert metrics["latency"] >= 4.0
    elif fault_type == FaultType.LLM_FAILURE:
        assert metrics["error_rate"] >= 0.08 or metrics["api_success_rate"] < 0.85
    elif fault_type == FaultType.RAG_DEGRADATION:
        assert metrics["retrieval_score"] < 0.70 or metrics["hallucination_score"] > 0.20
    elif fault_type == FaultType.TOOL_FAILURE:
        assert metrics["tool_failure_rate"] > 0.15
    elif fault_type == FaultType.COST_SPIKE:
        assert metrics["token_usage"] > 1800.0
    elif fault_type == FaultType.AGENT_LOOP:
        assert metrics["token_usage"] > 2000.0 and metrics["latency"] > 6.0


def test_simulation_reset():
    engine = SimulationEngine()
    engine.inject_fault(FaultType.LATENCY_SPIKE, duration_seconds=60)
    assert engine.is_fault_active

    engine.reset_to_normal()
    assert not engine.is_fault_active
    assert engine._active_fault is None


# --- 3. Incident Creation Tests ---

def test_incident_creation_service():
    db = TestingSessionLocal()
    metrics_data = {
        "latency": 8.5,
        "error_rate": 0.14,
        "token_usage": 2400.0,
        "retrieval_score": 0.52,
    }

    incident = incident_service.create_incident(
        title="High Latency Detected",
        description="P99 latency spiked past 8s",
        severity="high",
        failure_type=FaultType.LATENCY_SPIKE,
        confidence=0.95,
        metrics=metrics_data,
        db=db,
    )

    assert incident.id is not None
    assert incident.title == "High Latency Detected"
    assert incident.severity == "high"
    assert incident.status == "open"
    assert incident.failure_type == FaultType.LATENCY_SPIKE
    assert incident.confidence == 0.95

    # Check metric snapshots were created
    retrieved = incident_service.get_incident(incident.id, db=db)
    assert retrieved is not None
    assert len(retrieved.metrics) == 4
    metric_names = [m.metric_name for m in retrieved.metrics]
    assert "latency" in metric_names
    assert "error_rate" in metric_names
    db.close()


def test_threshold_breach_triggers_incident():
    db = TestingSessionLocal()
    engine = SimulationEngine()
    engine.inject_fault(FaultType.LLM_FAILURE, severity="critical", duration_seconds=30)

    # Ticking during fault should evaluate threshold violation and trigger incident
    point = engine.tick()
    assert point["metrics"]["error_rate"] >= 0.08 or point["metrics"]["api_success_rate"] < 0.85
    assert engine._incident_triggered_for_current_fault is True
    db.close()


# --- 4. API Endpoints Tests ---

def test_api_metrics_endpoint():
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "current" in data
    assert "history" in data
    assert "latency" in data["current"]


def test_api_simulation_flow():
    # 1. Inject fault
    resp = client.post(
        "/api/simulation/inject",
        json={"fault_type": FaultType.LATENCY_SPIKE, "severity": "high", "duration_seconds": 45},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "fault_active"
    assert body["active_fault"] == FaultType.LATENCY_SPIKE

    # 2. Check status
    status_resp = client.get("/api/simulation/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["active_fault"] == FaultType.LATENCY_SPIKE

    # 3. Manual tick
    tick_resp = client.post("/api/simulation/tick")
    assert tick_resp.status_code == 200
    assert tick_resp.json()["active_fault"] == FaultType.LATENCY_SPIKE

    # 4. Reset
    reset_resp = client.post("/api/simulation/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["mode"] == "normal"
    assert reset_resp.json()["active_fault"] is None


def test_api_incidents_endpoints():
    # Simulate an incident via API
    payload = {
        "title": "Simulated RAG Incident",
        "description": "Retriever degradation test",
        "severity": "high",
        "failure_type": FaultType.RAG_DEGRADATION,
        "confidence": 0.88,
    }
    resp = client.post("/api/incidents/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    inc_id = data["id"]
    assert data["title"] == "Simulated RAG Incident"
    assert data["failure_type"] == FaultType.RAG_DEGRADATION

    # List incidents
    list_resp = client.get("/api/incidents")
    assert list_resp.status_code == 200
    incidents = list_resp.json()
    assert any(i["id"] == inc_id for i in incidents)

    # Get incident by ID
    get_resp = client.get(f"/api/incidents/{inc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == inc_id
    assert len(get_resp.json()["metrics"]) > 0


def test_api_section_29_demo_scenario():
    """Verifies that POST /api/simulation/demo executes all 14 steps end-to-end."""
    resp = client.post("/api/simulation/demo")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["steps_count"] == 14
    assert len(data["steps"]) == 14
    assert "incident_id" in data

    # Verify step names cover the 14 Section 29 milestones
    step_names = [s["name"] for s in data["steps"]]
    assert "Start Simulated Healthy System" in step_names[0]
    assert "Inject RAG Degradation" in step_names[1]
    assert "Detect Anomaly" in step_names[2]
    assert "Create Incident" in step_names[3]
    assert "Collect Metrics & Logs" in step_names[4]
    assert "Diagnose Root Cause" in step_names[5]
    assert "Retrieve Historical Runbooks" in step_names[6]
    assert "Generate Recovery Strategies" in step_names[7]
    assert "Calculate Risk" in step_names[8]
    assert "Request Human Approval" in step_names[9]
    assert "Execute Recovery via MCP" in step_names[10]
    assert "Verify Recovery Telemetry" in step_names[11]
    assert "Run Evaluation" in step_names[12]
    assert "Generate Postmortem & Learn" in step_names[13]

    # Verify final recovery state is healthy
    assert data["restored_metrics"]["retrieval_score"] >= 0.85

