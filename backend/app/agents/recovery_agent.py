"""
ARGUS Recovery Agent (Phase 5 & 6 - Sections 10, 12, 13, 14, 15)

Evaluates recovery options, runs MCP counterfactual simulation, computes grounded success
probabilities and risk assessments, and dispatches actions through the MCP server tool layer.
"""
import logging
from typing import Any, Dict, List, Optional

from app.graph.state import ArgusState
from app.ml.failure_prediction import FailureCategory
from app.mcp.server import call_tool
from app.mcp.deployment_tools import simulate_rollback

logger = logging.getLogger(__name__)

# Grounded strategy blueprints mapping to MCP Action Tools (Section 12 & 14)
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
            "id": "restart_vector_db",
            "action": "restart_service",
            "parameters": {"service_name": "vector_db"},
            "success_probability": 0.88,
            "risk_score": 0.65,
            "reversibility": "medium",
            "rationale": "Recycles vector database connection handles.",
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
            "id": "reindex_vector_store",
            "action": "reindex_vector_store",
            "parameters": {"collection": "runbooks", "force_clean": True},
            "success_probability": 0.85,
            "risk_score": 0.30,
            "reversibility": "high",
            "rationale": "Rebuilds corrupted index partitions.",
        },
    ],
    FailureCategory.AGENT_LOOP: [
        {
            "id": "restart_agent_worker",
            "action": "restart_service",
            "parameters": {"service_name": "agent_worker"},
            "success_probability": 0.95,
            "risk_score": 0.60,
            "reversibility": "high",
            "rationale": "Breaks cyclic state oscillation and resets step counter to 0.",
        },
        {
            "id": "rollback_agent_release",
            "action": "execute_rollback",
            "parameters": {"service_name": "agent_worker", "target_revision": "v1_stable"},
            "success_probability": 0.88,
            "risk_score": 0.75,
            "reversibility": "medium",
            "rationale": "Rolls back to previous agent workflow prompt specification.",
        },
    ],
    FailureCategory.LATENCY_SPIKE: [
        {
            "id": "restart_api_gateway",
            "action": "restart_service",
            "parameters": {"service_name": "api_gateway"},
            "success_probability": 0.91,
            "risk_score": 0.65,
            "reversibility": "medium",
            "rationale": "Clears socket starvation and async loop backpressure.",
        },
        {
            "id": "rollback_core_service",
            "action": "execute_rollback",
            "parameters": {"service_name": "core_service", "target_revision": "v1_stable"},
            "success_probability": 0.85,
            "risk_score": 0.70,
            "reversibility": "medium",
            "rationale": "Reverts to stable non-blocking service revision.",
        },
    ],
    FailureCategory.COST_SPIKE: [
        {
            "id": "switch_to_cost_effective_model",
            "action": "switch_model",
            "parameters": {"target_provider": "gemini", "model": "gemini-1.5-flash"},
            "success_probability": 0.94,
            "risk_score": 0.25,
            "reversibility": "high",
            "rationale": "Switches to high-efficiency flash tier to arrest token cost explosion.",
        },
        {
            "id": "restart_llm_gateway",
            "action": "restart_service",
            "parameters": {"service_name": "llm_gateway"},
            "success_probability": 0.75,
            "risk_score": 0.65,
            "reversibility": "medium",
            "rationale": "Purges active queued prompt sessions.",
        },
    ],
    FailureCategory.TOOL_FAILURE: [
        {
            "id": "restart_core_service",
            "action": "restart_service",
            "parameters": {"service_name": "core_service"},
            "success_probability": 0.90,
            "risk_score": 0.65,
            "reversibility": "medium",
            "rationale": "Resets stale external tool connections.",
        },
        {
            "id": "rollback_tool_integration",
            "action": "execute_rollback",
            "parameters": {"service_name": "core_service", "target_revision": "v1_stable"},
            "success_probability": 0.84,
            "risk_score": 0.70,
            "reversibility": "medium",
            "rationale": "Reverts tool schema definitions to previous verified release.",
        },
    ],
    FailureCategory.API_FAILURE: [
        {
            "id": "restart_api_gateway",
            "action": "restart_service",
            "parameters": {"service_name": "api_gateway"},
            "success_probability": 0.88,
            "risk_score": 0.65,
            "reversibility": "medium",
            "rationale": "Recycles 502/503 downstream reverse proxy sockets.",
        },
        {
            "id": "switch_model_backup",
            "action": "switch_model",
            "parameters": {"target_provider": "gemini", "model": "gemini-1.5-pro"},
            "success_probability": 0.82,
            "risk_score": 0.25,
            "reversibility": "high",
            "rationale": "Routes to alternative provider region.",
        },
    ],
}

DEFAULT_STRATEGIES = [
    {
        "id": "safe_baseline_rollback",
        "action": "execute_rollback",
        "parameters": {"service_name": "core_service", "target_revision": "v1_stable"},
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


def execute_recovery_action(
    strategy: Dict[str, Any],
    approval_status: str,
    incident_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dispatches the selected recovery strategy through the MCP Tool Layer (Phase 6).
    Passes approval status and incident_id for validation, allowlist check, and audit logging.
    """
    action = strategy.get("action", "unknown_action")
    params = dict(strategy.get("parameters", {}))
    params["approved"] = (approval_status == "approved")
    if incident_id:
        params["incident_id"] = incident_id

    return call_tool(action, params)


def recovery_agent(state: ArgusState) -> Dict[str, Any]:
    """
    Evaluates recovery options and risk per Sections 14 & 15.
    Selects the safest high-confidence strategy using MCP simulation and groundings.
    """
    failure_type = state.get("failure_type", "UNKNOWN")
    history_trace = list(state.get("history_trace", []))
    history_trace.append("RecoveryAgent: generating recovery options and assessing risk")

    # 1. Retrieve grounded options from catalog matching diagnosed failure type
    candidate_options = STRATEGY_CATALOG.get(failure_type, DEFAULT_STRATEGIES)

    # 2. Run counterfactual MCP simulation for rollback actions (Section 15)
    enhanced_options: List[Dict[str, Any]] = []
    incident = state.get("incident", {})
    inc_id = incident.get("id") if isinstance(incident, dict) else getattr(incident, "id", None)

    for opt in candidate_options:
        opt_copy = dict(opt)
        if opt_copy.get("action") in ["execute_rollback", "simulate_rollback"]:
            params = opt_copy.get("parameters", {})
            try:
                sim_res = simulate_rollback(
                    service_name=params.get("service_name", "core_service"),
                    target_revision=params.get("target_revision", "v1_stable"),
                    incident_id=inc_id,
                    actor="agent:recovery_agent",
                )
                if sim_res.get("status") == "success":
                    opt_copy["success_probability"] = sim_res["simulation"]["recovery_probability"]
                    opt_copy["potential_impact"] = sim_res["simulation"]["potential_impact"]
            except Exception as e:
                logger.warning("Error running counterfactual simulation for %s: %s", opt_copy.get("id"), e)
        enhanced_options.append(opt_copy)

    # 3. Score strategies by expected recovery utility: P(Success) * (1 - 0.4 * Risk)
    def utility(opt: Dict[str, Any]) -> float:
        return opt["success_probability"] * (1.0 - 0.4 * opt["risk_score"])

    sorted_options = sorted(enhanced_options, key=utility, reverse=True)
    selected = sorted_options[0]

    # 4. Determine if human approval is required (Section 13)
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
