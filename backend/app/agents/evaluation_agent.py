"""
ARGUS Evaluation Agent (Phase 5 - Sections 10, 18, 19)

Evaluates diagnostic correctness, RAG groundedness, and recovery safety scores.
"""
import logging
from typing import Any, Dict

from app.graph.state import ArgusState

logger = logging.getLogger(__name__)


def evaluation_agent(state: ArgusState) -> Dict[str, Any]:
    """
    Computes rigorous evaluation metrics for the incident resolution trajectory.
    """
    failure_confidence = state.get("failure_confidence", 0.85)
    evidence = state.get("evidence", [])
    selected_strategy = state.get("selected_strategy", {})
    risk_score = state.get("risk_score", 0.3)
    verification = state.get("verification_result", {})
    history_trace = list(state.get("history_trace", []))
    history_trace.append("EvaluationAgent: scoring diagnosis, groundedness, and recovery efficacy")

    # 1. Groundedness score: verifies cited evidence exists
    groundedness = 0.95 if len(evidence) >= 2 else (0.80 if len(evidence) == 1 else 0.50)

    # 2. Recovery Safety score: inverse of risk score
    safety_score = round(1.0 - (risk_score * 0.5), 2)

    # 3. Verification outcome score
    verified = verification.get("recovery_verified", False)
    verification_score = 1.0 if verified else 0.0

    # 4. Overall quality score
    overall = round(
        0.35 * failure_confidence +
        0.25 * groundedness +
        0.20 * safety_score +
        0.20 * verification_score,
        2,
    )

    evaluation_result = {
        "diagnostic_confidence": failure_confidence,
        "rag_groundedness": groundedness,
        "recovery_safety_score": safety_score,
        "verification_score": verification_score,
        "overall_evaluation_score": overall,
    }

    logs = list(state.get("logs", []))
    logs.append(
        f"[EvaluationAgent] Evaluation Complete: Overall Score={overall:.2f} "
        f"(Groundedness={groundedness:.2f}, Safety={safety_score:.2f}, Verified={verified})"
    )

    return {
        "evaluation_result": evaluation_result,
        "logs": logs,
        "history_trace": history_trace,
    }
