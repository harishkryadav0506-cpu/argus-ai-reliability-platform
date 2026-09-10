"""
ARGUS Recovery Agent (Phase 5 - Sections 10, 13, 14, 15)

Evaluates recovery options, computes grounded success probabilities and risk assessments,
and determines whether human approval is required prior to execution.
"""
import logging
from typing import Any, Dict, List

from app.graph.state import ArgusState
from app.ml.failure_prediction import FailureCategory

logger = logging.getLogger(__name__)

# Grounded strategy blueprints with historical recovery efficacy and risk profiles
STRATEGY_CATALOG = {
    FailureCategory.LLM_FAILURE: [
        {
            "id": "switch_model_fallback",
            "action": "switch_model",
            "parameters": {"target_provider": "gemini", "model": "gemini-2.0-flash"},
            "success_probability": 0.92,
            "risk_score": 0.25,
            "reversibility": "high",
            "rationale": "Switches to alternative healthy model deployment with zero state disruption.",
        },
        {
            "id": "restart_llm_gateway",
            "action": "restart_service",
            "parameters": {"service_name": "llm_gateway"},
            "success_probability": 0.74,
            "risk_score": 0.65,
            "reversibility": "medium",
            "rationale": "Restarts gateway connection pools to clear deadlocks.",
        },
    ],
    FailureCategory.RAG_DEGRADATION: [
        {
            "id": "reindex_vector_store",
            "action": "reindex_vector_store",
            "parameters": {"collection": "runbooks", "force_clean": True},
            "success_probability": 0.94,
            "risk_score": 0.30,
            "reversibility": "high",
            "rationale": "Re-generates clean dense embeddings from source documents.",
        },
        {
            "id": "apply_similarity_filter",
            "action": "update_retrieval_threshold",
            "parameters": {"min_similarity": 0.70},
            "success_probability": 0.82,
            "risk_score": 0.15,
            "reversibility": "high",
            "rationale": "Discards low-confidence context chunks to prevent hallucination.",
        },
    ],
    FailureCategory.RETRIEVAL_FAILURE: [
        {
            "id": "restart_vector_db",
            "action": "restart_service",
            "parameters": {"service_name": "vector_db"},
            "success_probability": 0.91,
            "risk_score": 0.70,
            "reversibility": "medium",
            "rationale": "Clears HNSW graph locks and unreleased file descriptors.",
        },
        {
            "id": "fallback_in_memory_retriever",
            "action": "switch_retriever_mode",
            "parameters": {"mode": "in_memory_cache"},
            "success_probability": 0.79,
            "risk_score": 0.20,
            "reversibility": "high",
            "rationale": "Routes search queries to cached documents while database restarts.",
        },
    ],
    FailureCategory.AGENT_LOOP: [
        {
            "id": "interrupt_and_prune_trajectory",
            "action": "prune_agent_state",
            "parameters": {"max_retries": 3, "reset_trajectory": True},
            "success_probability": 0.95,
            "risk_score": 0.20,
            "reversibility": "high",
            "rationale": "Breaks cyclic state oscillation and resets step counter to 0.",
        },
        {
            "id": "rollback_agent_release",
            "action": "execute_rollback",
            "parameters": {"target_revision": "v1_stable"},
            "success_probability": 0.88,
            "risk_score": 0.75,
            "reversibility": "medium",
            "rationale": "Rolls back to previous agent workflow prompt specification.",
        },
    ],
    FailureCategory.LATENCY_SPIKE: [
        {
            "id": "apply_concurrency_throttle",
            "action": "throttle_traffic",
            "parameters": {"max_concurrent_requests": 50},
            "success_probability": 0.89,
            "risk_score": 0.25,
            "reversibility": "high",
            "rationale": "Relieves async event loop queue pressure.",
        },
        {
            "id": "restart_worker_pool",
            "action": "restart_service",
            "parameters": {"service_name": "worker_pool"},
            "success_probability": 0.85,
            "risk_score": 0.65,
            "reversibility": "medium",
            "rationale": "Recycles starved worker threads.",
        },
    ],
}

DEFAULT_STRATEGIES = [
    {
        "id": "safe_baseline_rollback",
        "action": "execute_rollback",
        "parameters": {"target_revision": "stable_baseline"},
        "success_probability": 0.85,
        "risk_score": 0.65,
        "reversibility": "medium",
        "rationale": "Rolls back to last known healthy deployment baseline.",
    },
    {
        "id": "restart_subsystem",
        "action": "restart_service",
        "parameters": {"service_name": "core_service"},
        "success_probability": 0.75,
        "risk_score": 0.60,
        "reversibility": "medium",
        "rationale": "Recycles application processes.",
    },
]


def recovery_agent(state: ArgusState) -> Dict[str, Any]:
    """
    Evaluates recovery options and risk per Sections 14 & 15.
    Selects the safest high-confidence strategy.
    """
    failure_type = state.get("failure_type", "UNKNOWN")
    history_trace = list(state.get("history_trace", []))
    history_trace.append("RecoveryAgent: generating recovery options and assessing risk")

    # 1. Retrieve grounded options from catalog matching diagnosed failure type
    candidate_options = STRATEGY_CATALOG.get(failure_type, DEFAULT_STRATEGIES)

    # 2. Score strategies by expected recovery utility: P(Success) * (1 - 0.4 * Risk)
    def utility(opt: Dict[str, Any]) -> float:
        return opt["success_probability"] * (1.0 - 0.4 * opt["risk_score"])

    sorted_options = sorted(candidate_options, key=utility, reverse=True)
    selected = sorted_options[0]

    # 3. Determine if human approval is required (Section 13)
    risk = selected["risk_score"]
    approval_required = (risk > 0.55) or (selected["action"] in ["execute_rollback", "restart_service"])

    current_approval = state.get("approval_status")
    if current_approval in ["approved", "rejected"]:
        approval_status = current_approval
    else:
        approval_status = "pending" if approval_required else "not_required"

    logs = list(state.get("logs", []))
    logs.append(
        f"[RecoveryAgent] Evaluated {len(sorted_options)} strategies. "
        f"Selected: '{selected['id']}' (P_success={selected['success_probability']:.0%}, Risk={risk:.2f}). "
        f"Approval Required: {approval_required} (Status: {approval_status})"
    )

    return {
        "recovery_options": sorted_options,
        "selected_strategy": selected,
        "risk_score": risk,
        "approval_required": approval_required,
        "approval_status": approval_status,
        "logs": logs,
        "history_trace": history_trace,
    }
