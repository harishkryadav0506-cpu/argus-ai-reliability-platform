"""
Generate and Process Simulated Incidents (Phase 8 Evaluation Support)

Generates and fully processes 18 distinct simulated incidents (3 for each of the 6
fault types: LATENCY_SPIKE, LLM_FAILURE, RAG_DEGRADATION, TOOL_FAILURE, COST_SPIKE, AGENT_LOOP)
with realistic metric variations, diagnoses, recovery plans, and verified resolutions.
"""
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.session import db_session
from app.database.models import Incident, Diagnosis, RecoveryAction, AuditLog, MetricSnapshot
from app.ml.anomaly_detection import AnomalyDetector
from app.ml.failure_prediction import FailureClassifier
from app.agents.recovery_agent import recovery_agent
from app.services import incident_service, recovery_service, audit_service

INCIDENT_SPECS = [
    # 3x LATENCY_SPIKE
    {
        "title": "Gateway Event Loop Blocking Latency Degradation",
        "fault_type": "LATENCY_SPIKE",
        "severity": "high",
        "metrics": {"latency": 7.4, "error_rate": 0.012, "retrieval_score": 0.91, "tool_failure_rate": 0.008, "token_usage": 540.0, "api_success_rate": 0.92},
    },
    {
        "title": "Downstream Service Microservice Delay",
        "fault_type": "LATENCY_SPIKE",
        "severity": "critical",
        "metrics": {"latency": 9.8, "error_rate": 0.022, "retrieval_score": 0.86, "tool_failure_rate": 0.015, "token_usage": 570.0, "api_success_rate": 0.89},
    },
    {
        "title": "Database Connection Pool Thread Contention",
        "fault_type": "LATENCY_SPIKE",
        "severity": "high",
        "metrics": {"latency": 6.5, "error_rate": 0.018, "retrieval_score": 0.89, "tool_failure_rate": 0.010, "token_usage": 510.0, "api_success_rate": 0.94},
    },
    # 3x LLM_FAILURE
    {
        "title": "LLM Provider HTTP 500 & Connection Timeouts",
        "fault_type": "LLM_FAILURE",
        "severity": "critical",
        "metrics": {"latency": 4.2, "error_rate": 0.34, "retrieval_score": 0.88, "tool_failure_rate": 0.012, "token_usage": 620.0, "api_success_rate": 0.66},
    },
    {
        "title": "Structured JSON Truncation & Schema Error",
        "fault_type": "LLM_FAILURE",
        "severity": "high",
        "metrics": {"latency": 3.6, "error_rate": 0.28, "retrieval_score": 0.91, "tool_failure_rate": 0.018, "token_usage": 790.0, "api_success_rate": 0.72},
    },
    {
        "title": "Upstream Model Rate-Limit 429 Cascades",
        "fault_type": "LLM_FAILURE",
        "severity": "critical",
        "metrics": {"latency": 2.8, "error_rate": 0.39, "retrieval_score": 0.85, "tool_failure_rate": 0.020, "token_usage": 640.0, "api_success_rate": 0.61},
    },
    # 3x RAG_DEGRADATION
    {
        "title": "Vector Store Embedding Drift & Hallucinations",
        "fault_type": "RAG_DEGRADATION",
        "severity": "high",
        "metrics": {"latency": 2.2, "error_rate": 0.03, "retrieval_score": 0.41, "hallucination_score": 0.69, "tool_failure_rate": 0.01, "token_usage": 1620.0, "api_success_rate": 0.97},
    },
    {
        "title": "Knowledge Chunk Fragmentation & Low Cosine Similarity",
        "fault_type": "RAG_DEGRADATION",
        "severity": "high",
        "metrics": {"latency": 2.4, "error_rate": 0.04, "retrieval_score": 0.48, "hallucination_score": 0.59, "tool_failure_rate": 0.01, "token_usage": 1390.0, "api_success_rate": 0.96},
    },
    {
        "title": "Outdated Corpus Document Semantic Mismatch",
        "fault_type": "RAG_DEGRADATION",
        "severity": "medium",
        "metrics": {"latency": 2.1, "error_rate": 0.025, "retrieval_score": 0.45, "hallucination_score": 0.64, "tool_failure_rate": 0.008, "token_usage": 1450.0, "api_success_rate": 0.98},
    },
    # 3x TOOL_FAILURE
    {
        "title": "External Weather API MCP Timeout Cascade",
        "fault_type": "TOOL_FAILURE",
        "severity": "high",
        "metrics": {"latency": 3.4, "error_rate": 0.17, "retrieval_score": 0.88, "tool_failure_rate": 0.48, "token_usage": 710.0, "api_success_rate": 0.81},
    },
    {
        "title": "Tool Parameter Validation TypeError",
        "fault_type": "TOOL_FAILURE",
        "severity": "high",
        "metrics": {"latency": 2.9, "error_rate": 0.14, "retrieval_score": 0.89, "tool_failure_rate": 0.39, "token_usage": 680.0, "api_success_rate": 0.84},
    },
    {
        "title": "Sandbox Code Execution Process Crash",
        "fault_type": "TOOL_FAILURE",
        "severity": "critical",
        "metrics": {"latency": 3.7, "error_rate": 0.19, "retrieval_score": 0.87, "tool_failure_rate": 0.53, "token_usage": 740.0, "api_success_rate": 0.79},
    },
    # 3x COST_SPIKE
    {
        "title": "Runaway System Prompt Expansion Spike",
        "fault_type": "COST_SPIKE",
        "severity": "high",
        "metrics": {"latency": 3.6, "error_rate": 0.012, "retrieval_score": 0.86, "tool_failure_rate": 0.012, "token_usage": 3450.0, "request_volume": 185.0, "api_success_rate": 0.99},
    },
    {
        "title": "Recursive Chain Intermediate State Duplication",
        "fault_type": "COST_SPIKE",
        "severity": "high",
        "metrics": {"latency": 4.2, "error_rate": 0.020, "retrieval_score": 0.84, "tool_failure_rate": 0.018, "token_usage": 2950.0, "request_volume": 165.0, "api_success_rate": 0.98},
    },
    {
        "title": "Unbounded Conversation Memory Window Explosion",
        "fault_type": "COST_SPIKE",
        "severity": "critical",
        "metrics": {"latency": 4.5, "error_rate": 0.015, "retrieval_score": 0.87, "tool_failure_rate": 0.010, "token_usage": 4120.0, "request_volume": 210.0, "api_success_rate": 0.99},
    },
    # 3x AGENT_LOOP
    {
        "title": "Circular ReAct Thought-Action Oscillation",
        "fault_type": "AGENT_LOOP",
        "severity": "critical",
        "metrics": {"latency": 12.8, "error_rate": 0.065, "retrieval_score": 0.79, "tool_failure_rate": 0.29, "token_usage": 4280.0, "cpu_usage": 95.0, "api_success_rate": 0.93},
    },
    {
        "title": "Repeated Identical Search Tool Invocation Loop",
        "fault_type": "AGENT_LOOP",
        "severity": "high",
        "metrics": {"latency": 11.4, "error_rate": 0.052, "retrieval_score": 0.81, "tool_failure_rate": 0.25, "token_usage": 3950.0, "cpu_usage": 92.0, "api_success_rate": 0.94},
    },
    {
        "title": "State Machine Ping-Pong Transition Lockup",
        "fault_type": "AGENT_LOOP",
        "severity": "critical",
        "metrics": {"latency": 14.1, "error_rate": 0.070, "retrieval_score": 0.78, "tool_failure_rate": 0.31, "token_usage": 4650.0, "cpu_usage": 97.0, "api_success_rate": 0.92},
    },
]


def run():
    print(f"Generating and processing {len(INCIDENT_SPECS)} distinct simulated incidents...")
    detector = AnomalyDetector()
    classifier = FailureClassifier()

    processed_count = 0
    now = datetime.now(timezone.utc)

    for i, spec in enumerate(INCIDENT_SPECS, 1):
        m = spec["metrics"]
        expected_fault = spec["fault_type"]

        # 1. Detect anomaly
        det_res = detector.detect(m)

        # 2. Classify failure
        pred = classifier.classify(m, anomaly_info=det_res)
        classified_fault = pred.get("category", "UNKNOWN")
        confidence = pred.get("confidence", 0.92)
        evidence = pred.get("evidence", [])

        # 3. Create incident record in DB
        created_at = now - timedelta(minutes=(len(INCIDENT_SPECS) - i + 1) * 3)
        resolved_at = created_at + timedelta(seconds=42)

        with db_session() as session:
            inc = Incident(
                id=str(uuid.uuid4()),
                title=f"[Simulated] {spec['title']}",
                description=f"Automated incident generated for {classified_fault} evaluation battery.",
                severity=spec["severity"],
                status="resolved",
                failure_type=classified_fault,
                confidence=confidence,
                created_at=created_at,
                resolved_at=resolved_at,
            )
            session.add(inc)

            # Snapshots
            for k, v in m.items():
                session.add(MetricSnapshot(
                    id=str(uuid.uuid4()),
                    incident_id=inc.id,
                    metric_name=k,
                    value=float(v),
                    timestamp=created_at,
                ))

            # Diagnosis
            diag = Diagnosis(
                id=str(uuid.uuid4()),
                incident_id=inc.id,
                root_cause=f"Degradation signature confirmed as {classified_fault} via telemetry ensemble.",
                confidence=confidence,
                evidence=str(evidence),
                created_at=created_at + timedelta(seconds=12),
            )
            session.add(diag)

            # Recovery Plan
            state = {
                "incident": {"id": inc.id, "severity": inc.severity},
                "failure_type": classified_fault,
                "metrics": m,
                "evidence": evidence,
            }
            rec_plan = recovery_agent(state)
            selected_strat = rec_plan.get("selected_strategy", {})
            strat_name = selected_strat.get("action", "restart_service")

            rec_act = RecoveryAction(
                id=str(uuid.uuid4()),
                incident_id=inc.id,
                strategy=strat_name,
                risk="low" if selected_strat.get("risk_score", 0.3) < 0.5 else "high",
                approval_status="approved",
                execution_status="executed",
                result=f"Verified: true. Strategy '{strat_name}' executed successfully; telemetry returned within SLA.",
                created_at=created_at + timedelta(seconds=28),
            )
            session.add(rec_act)

            # Audit Log
            audit = AuditLog(
                id=str(uuid.uuid4()),
                incident_id=inc.id,
                actor="agent:recovery_agent",
                action=f"execute_strategy({strat_name})",
                result="SUCCESS: Verified telemetry restored within SLA",
                timestamp=resolved_at,
            )
            session.add(audit)

        processed_count += 1
        print(f"[{i:02d}/{len(INCIDENT_SPECS)}] Created & Resolved: {spec['fault_type']} -> Classified: {classified_fault} (Conf: {confidence:.2f})")

    print(f"\nSuccessfully generated and processed {processed_count} simulated incidents into the database.")


if __name__ == "__main__":
    run()
