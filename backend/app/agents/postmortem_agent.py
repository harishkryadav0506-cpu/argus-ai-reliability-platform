"""
ARGUS Postmortem Agent (Phase 5 - Sections 26 & 37.4)

Generates structured incident postmortems in Markdown per Section 26.
CRITICAL: Per Section 37.4, once an incident reaches resolved status, this agent
automatically ingests it into the ChromaDB `historical_incidents` vector collection
so ARGUS accumulates real historical learning over time.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from app.graph.state import ArgusState
from app.rag.knowledge_base import get_historical_incidents_collection

logger = logging.getLogger(__name__)


def generate_postmortem_markdown(state: ArgusState) -> str:
    """
    Generates a full Markdown postmortem following Section 26 structure.
    """
    incident = state.get("incident", {})
    inc_id = incident.get("id", str(uuid.uuid4())[:8])
    failure_type = state.get("failure_type", "UNKNOWN")
    severity = incident.get("severity", "high")
    root_cause = state.get("root_cause", "No root cause diagnosed.")
    evidence = state.get("evidence", [])
    strategy = state.get("selected_strategy", {})
    verification = state.get("verification_result", {})
    history = state.get("history_trace", [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    evidence_bullets = "\n".join([f"- {ev}" for ev in evidence]) if evidence else "- No explicit evidence cited."
    timeline_bullets = "\n".join([f"- `{step}`" for step in history])

    return f"""# Incident Postmortem: {failure_type} [{inc_id}]

**Date**: {now}
**Severity**: {severity.upper()}
**Status**: RESOLVED
**Failure Type**: {failure_type}

---

## 1. Incident Summary
An automated reliability anomaly was detected by the ARGUS detection layer. The incident was classified as `{failure_type}` and escalated through autonomous root-cause investigation, recovery simulation, execution, and verification.

## 2. Impact
- **Affected Subsystem**: AI / RAG / Agent Inference Pipeline
- **User Facing Degradation**: Elevated error rate and latency divergence

## 3. Detection & Telemetry Evidence
{evidence_bullets}

## 4. Root Cause
{root_cause}

## 5. Recovery Action
- **Selected Action**: `{strategy.get('action', 'N/A')}`
- **Strategy ID**: `{strategy.get('id', 'N/A')}`
- **Rationale**: {strategy.get('rationale', 'N/A')}
- **Expected Probability of Success**: {strategy.get('success_probability', 0.0):.0%}
- **Risk Assessment**: {strategy.get('risk_score', 0.0):.2f}

## 6. Verification
- **Recovery Verified**: {verification.get('recovery_verified', True)}
- **Verification Details**: {verification.get('details', 'Post-recovery telemetry confirmed return to normal SLA.')}

## 7. Execution Timeline
{timeline_bullets}

## 8. Lessons Learned & Preventive Actions
1. Maintain strict automated circuit breakers on upstream tool calls.
2. Ingest this resolved incident into the historical incident memory for future experience-based retrieval.
"""


def _ingest_into_historical_incidents(state: ArgusState, postmortem_text: str):
    """
    Ingests resolved incident into ChromaDB historical_incidents collection (Section 37.4).
    """
    try:
        collection = get_historical_incidents_collection()
        incident = state.get("incident", {})
        inc_id = incident.get("id", str(uuid.uuid4()))
        failure_type = state.get("failure_type", "UNKNOWN")
        strategy = state.get("selected_strategy", {})
        action_name = strategy.get("action", "unknown_action")

        doc_summary = (
            f"Historical Incident: {inc_id} [{failure_type}]\n"
            f"Root Cause: {state.get('root_cause', '')}\n"
            f"Successful Recovery: {action_name} ({strategy.get('rationale', '')})\n"
            f"Verification: Recovery verified successfully."
        )

        collection.upsert(
            ids=[f"hist_{inc_id}"],
            documents=[doc_summary],
            metadatas=[{
                "incident_id": inc_id,
                "failure_type": failure_type,
                "recovery_action": action_name,
                "status": "resolved",
                "source": "historical_incident_lifecycle",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }],
        )
        logger.info("Successfully ingested resolved incident %s into historical RAG knowledge base.", inc_id)
    except Exception as e:
        logger.error("Failed to ingest historical incident into ChromaDB: %s", e)


def postmortem_agent(state: ArgusState) -> Dict[str, Any]:
    """
    Generates postmortem and automatically bootstraps historical knowledge (Section 37.4).
    """
    history_trace = list(state.get("history_trace", []))
    history_trace.append("PostmortemAgent: generating postmortem and recording historical incident")

    postmortem_text = generate_postmortem_markdown(state)

    # Per Section 37.4: Only resolved incidents are ingested as experience
    verification = state.get("verification_result", {})
    is_verified = verification.get("recovery_verified", False)
    final_status = "resolved" if is_verified else "failed"

    if is_verified:
        _ingest_into_historical_incidents(state, postmortem_text)

    logs = list(state.get("logs", []))
    logs.append(f"[PostmortemAgent] Postmortem generated. Final Status: {final_status}.")

    return {
        "final_status": final_status,
        "logs": logs,
        "history_trace": history_trace,
    }
