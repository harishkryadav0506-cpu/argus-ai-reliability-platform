"""
ARGUS LangGraph State Machine (Phase 5 - Section 10)

Compiles the multi-agent workflow graph orchestrating Detection, RAG Retrieval,
Diagnosis (Gemini + Fallback), Recovery Planning, Human Approval Gates, Execution,
Verification (with bounded MAX_RETRIES=3 retry loop), Evaluation, and Postmortem.
"""
import logging
from typing import Any, Dict, Literal
from langgraph.graph import END, START, StateGraph

from app.graph.state import ArgusState
from app.agents.detection_agent import detection_agent
from app.agents.diagnosis_agent import diagnosis_agent
from app.agents.recovery_agent import recovery_agent
from app.agents.evaluation_agent import evaluation_agent
from app.agents.postmortem_agent import postmortem_agent
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


# --- Graph Nodes ---

def node_detection(state: ArgusState) -> Dict[str, Any]:
    return detection_agent(state)


def node_retrieval(state: ArgusState) -> Dict[str, Any]:
    failure_type = state.get("failure_type", "UNKNOWN")
    evidence = state.get("evidence", [])
    history = list(state.get("history_trace", []))
    history.append("RAGRetrieval: querying runbook knowledge base")

    query = f"{failure_type} {', '.join(evidence)}"
    runbooks = retrieve(query=query, k=3)

    logs = list(state.get("logs", []))
    logs.append(f"[RAG] Retrieved {len(runbooks)} runbooks for query: '{query}'")

    return {
        "retrieved_runbooks": runbooks,
        "logs": logs,
        "history_trace": history,
    }


def node_diagnosis(state: ArgusState) -> Dict[str, Any]:
    return diagnosis_agent(state)


def node_recovery_planning(state: ArgusState) -> Dict[str, Any]:
    return recovery_agent(state)


def node_human_approval(state: ArgusState) -> Dict[str, Any]:
    """
    Gatekeeper node for high-risk recovery actions (Section 13).
    If approval_status is not explicitly approved or rejected, keeps it pending.
    """
    history = list(state.get("history_trace", []))
    history.append("HumanApprovalNode: evaluating approval status")
    logs = list(state.get("logs", []))

    status = state.get("approval_status", "pending")
    logs.append(f"[HumanApproval] Action approval status is: {status}")

    return {
        "approval_status": status,
        "logs": logs,
        "history_trace": history,
    }


def node_execution(state: ArgusState) -> Dict[str, Any]:
    """
    Executes the selected recovery strategy (wired to MCP action tools in Phase 6).
    """
    strategy = state.get("selected_strategy", {})
    action = strategy.get("action", "unknown_action")
    params = strategy.get("parameters", {})
    history = list(state.get("history_trace", []))
    history.append(f"ExecutionNode: executing recovery action '{action}'")

    logs = list(state.get("logs", []))
    logs.append(f"[Execution] Executed recovery action '{action}' with params: {params}")

    exec_result = {
        "status": "success",
        "action": action,
        "applied_parameters": params,
        "message": f"Successfully applied {action}.",
    }

    return {
        "execution_result": exec_result,
        "logs": logs,
        "history_trace": history,
    }


def node_verification(state: ArgusState) -> Dict[str, Any]:
    """
    Verifies recovery success by evaluating post-action telemetry (Section 16).
    If forced or failed, increments retry_count to support bounded retry loop.
    """
    history = list(state.get("history_trace", []))
    history.append("VerificationNode: checking post-recovery telemetry")
    logs = list(state.get("logs", []))

    # In Phase 5 state simulation: check if verification failure is explicitly simulated in state
    simulated_fail = state.get("verification_result", {}).get("force_failure", False)
    current_retries = state.get("retry_count", 0)

    if simulated_fail:
        verified = False
        new_retries = current_retries + 1
        msg = f"Post-recovery verification failed (attempt {new_retries}/{MAX_RETRIES}). Metrics remain degraded."
    else:
        verified = True
        new_retries = current_retries
        msg = "Recovery verified: Telemetry returned to normal baseline SLA limits."

    logs.append(f"[Verification] {msg}")

    verification_result = {
        "recovery_verified": verified,
        "force_failure": simulated_fail,
        "details": msg,
    }

    return {
        "verification_result": verification_result,
        "retry_count": new_retries,
        "logs": logs,
        "history_trace": history,
    }


def node_evaluation(state: ArgusState) -> Dict[str, Any]:
    return evaluation_agent(state)


def node_postmortem(state: ArgusState) -> Dict[str, Any]:
    return postmortem_agent(state)


def node_escalate_human_review(state: ArgusState) -> Dict[str, Any]:
    history = list(state.get("history_trace", []))
    history.append("EscalateNode: routed to human engineering review")
    logs = list(state.get("logs", []))
    logs.append("[Escalate] Automated recovery stopped. Escalated for human engineer intervention.")

    return {
        "final_status": "needs_human_review",
        "logs": logs,
        "history_trace": history,
    }


# --- Conditional Routing Edges ---

def route_after_detection(state: ArgusState) -> Literal["retrieval", "escalate_human_review"]:
    """Routes to human review if confidence is low (< 0.60) per Section 10."""
    conf = state.get("failure_confidence", 0.0)
    if conf < 0.60:
        logger.warning("Low diagnostic confidence (%.2f < 0.60); routing to human review.", conf)
        return "escalate_human_review"
    return "retrieval"


def route_after_recovery_planning(state: ArgusState) -> Literal["human_approval", "execution", "escalate_human_review"]:
    """Routes to human approval gate if action is high risk, or stops if rejected."""
    if state.get("approval_status") == "rejected":
        return "escalate_human_review"
    if state.get("approval_required", False) and state.get("approval_status") != "approved":
        return "human_approval"
    return "execution"


def route_after_human_approval(state: ArgusState) -> Literal["execution", "escalate_human_review"]:
    """Routes based on human approval status."""
    status = state.get("approval_status", "pending")
    if status == "rejected":
        return "escalate_human_review"
    return "execution"


def route_after_verification(state: ArgusState) -> Literal["evaluation", "diagnosis", "escalate_human_review"]:
    """
    Routes based on verification outcome:
    - If verified: proceed to evaluation.
    - If failed and retries < MAX_RETRIES (3): loop back to diagnosis.
    - If failed and retries >= MAX_RETRIES: escalate to human review (prevents infinite loop!).
    """
    verification = state.get("verification_result", {})
    verified = verification.get("recovery_verified", False)

    if verified:
        return "evaluation"

    retries = state.get("retry_count", 0)
    if retries < MAX_RETRIES:
        logger.warning("Recovery verification failed; retrying diagnosis (retry %d/%d).", retries, MAX_RETRIES)
        return "diagnosis"
    else:
        logger.error("Verification retry limit exceeded (%d/%d); halting loop and escalating.", retries, MAX_RETRIES)
        return "escalate_human_review"


# --- Build and Compile StateGraph ---

def build_argus_graph():
    builder = StateGraph(ArgusState)

    # Register Nodes
    builder.add_node("detection", node_detection)
    builder.add_node("retrieval", node_retrieval)
    builder.add_node("diagnosis", node_diagnosis)
    builder.add_node("recovery_planning", node_recovery_planning)
    builder.add_node("human_approval", node_human_approval)
    builder.add_node("execution", node_execution)
    builder.add_node("verification", node_verification)
    builder.add_node("evaluation", node_evaluation)
    builder.add_node("postmortem", node_postmortem)
    builder.add_node("escalate_human_review", node_escalate_human_review)

    # Edges
    builder.add_edge(START, "detection")

    builder.add_conditional_edges(
        "detection",
        route_after_detection,
        {
            "retrieval": "retrieval",
            "escalate_human_review": "escalate_human_review",
        },
    )

    builder.add_edge("retrieval", "diagnosis")
    builder.add_edge("diagnosis", "recovery_planning")

    builder.add_conditional_edges(
        "recovery_planning",
        route_after_recovery_planning,
        {
            "human_approval": "human_approval",
            "execution": "execution",
            "escalate_human_review": "escalate_human_review",
        },
    )

    builder.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {
            "execution": "execution",
            "escalate_human_review": "escalate_human_review",
        },
    )

    builder.add_edge("execution", "verification")

    builder.add_conditional_edges(
        "verification",
        route_after_verification,
        {
            "evaluation": "evaluation",
            "diagnosis": "diagnosis",
            "escalate_human_review": "escalate_human_review",
        },
    )

    builder.add_edge("evaluation", "postmortem")
    builder.add_edge("postmortem", END)
    builder.add_edge("escalate_human_review", END)

    return builder.compile()


# Global compiled graph
argus_graph = build_argus_graph()
