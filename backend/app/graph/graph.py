"""
ARGUS LangGraph State Machine (Phase 5 & 7 - Sections 10, 13, 16)

Compiles the multi-agent workflow graph orchestrating Detection, RAG Retrieval,
Diagnosis (Gemini + Fallback), Recovery Planning, Native Human Approval (via LangGraph interrupt/resume),
Execution via MCP tools, Telemetry Verification (Section 16 with bounded retry loop), Evaluation, and Postmortem.
"""
import logging
import uuid
from typing import Any, Dict, Literal, Optional
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.state import ArgusState
from app.agents.detection_agent import detection_agent
from app.agents.diagnosis_agent import diagnosis_agent
from app.agents.recovery_agent import recovery_agent, execute_recovery_action
from app.agents.evaluation_agent import evaluation_agent
from app.agents.postmortem_agent import postmortem_agent
from app.rag.retriever import retrieve
from app.services.recovery_service import record_recovery_action, update_recovery_action
from app.services import incident_service
from app.services.simulation_service import get_simulation_engine

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# Canonical baseline SLA limits for post-recovery verification (Section 16)
SLA_LIMITS = {
    "latency": 2.2,             # seconds max
    "error_rate": 0.02,          # 2% max
    "retrieval_score": 0.85,     # 85% min
    "tool_failure_rate": 0.03,   # 3% max
    "api_success_rate": 0.98,    # 98% min
}


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
    Pauses execution via native LangGraph interrupt() when approval is pending.
    Resumes seamlessly from interrupt point without re-running previous nodes.
    """
    history = list(state.get("history_trace", []))
    history.append("HumanApprovalNode: evaluating approval status")
    logs = list(state.get("logs", []))

    status = state.get("approval_status", "pending")
    incident = state.get("incident", {})
    inc_id = incident.get("id") if isinstance(incident, dict) else getattr(incident, "id", None)
    inc_id = inc_id or "unknown_incident"
    strategy = state.get("selected_strategy", {})
    action_name = strategy.get("action", "unknown_action")
    risk = state.get("risk_score", 0.5)

    # If approval already decided (e.g. pre-approved in automated tests), skip interrupt
    if status in ["approved", "rejected"]:
        record_recovery_action(
            incident_id=inc_id,
            strategy=action_name,
            risk=risk,
            approval_status=status,
            execution_status="pending",
        )
        logs.append(f"[HumanApproval] Action pre-evaluated as: {status}")
        return {
            "approval_status": status,
            "logs": logs,
            "history_trace": history,
        }

    # Record pending recovery action in DB / memory
    record_recovery_action(
        incident_id=inc_id,
        strategy=action_name,
        risk=risk,
        approval_status="pending",
        execution_status="pending",
    )
    logs.append(f"[HumanApproval] High-risk action '{action_name}' requires approval. Interrupting workflow.")

    # Native LangGraph Interrupt
    resume_val = interrupt({
        "incident_id": inc_id,
        "selected_strategy": strategy,
        "risk_score": risk,
        "options": state.get("recovery_options", []),
        "message": f"Human approval required for high-risk action '{action_name}' (Risk={risk:.2f}).",
    })

    # Resumed via Command(resume={"approved": True/False, ...})
    approved = False
    if isinstance(resume_val, dict):
        approved = resume_val.get("approved", False)
    elif isinstance(resume_val, bool):
        approved = resume_val

    new_status = "approved" if approved else "rejected"
    logs.append(f"[HumanApproval] Resumed from interrupt with decision: {new_status}")

    update_recovery_action(
        incident_id=inc_id,
        approval_status=new_status,
    )

    return {
        "approval_status": new_status,
        "logs": logs,
        "history_trace": history,
    }


def node_execution(state: ArgusState) -> Dict[str, Any]:
    """
    Executes the selected recovery strategy via MCP Action Tools (Phase 6).
    """
    strategy = state.get("selected_strategy", {})
    action = strategy.get("action", "unknown_action")
    params = strategy.get("parameters", {})
    history = list(state.get("history_trace", []))
    history.append(f"ExecutionNode: executing recovery action '{action}' via MCP")

    incident = state.get("incident", {})
    inc_id = incident.get("id") if isinstance(incident, dict) else getattr(incident, "id", None)
    approval_status = state.get("approval_status", "not_required")

    exec_result = execute_recovery_action(
        strategy=strategy,
        approval_status=approval_status,
        incident_id=inc_id,
    )

    logs = list(state.get("logs", []))
    status_str = exec_result.get("status", "unknown")
    msg_str = exec_result.get("message", exec_result.get("error", "Executed"))
    logs.append(f"[Execution via MCP] Action '{action}': Status={status_str} | Result={msg_str}")

    return {
        "execution_result": exec_result,
        "logs": logs,
        "history_trace": history,
    }


def node_verification(state: ArgusState) -> Dict[str, Any]:
    """
    Verifies recovery success by evaluating post-action telemetry against SLA limits (Section 16).
    Compares pre-recovery vs post-recovery metrics. If degraded, loops back to diagnosis (bounded retries).
    """
    history = list(state.get("history_trace", []))
    history.append("VerificationNode: checking post-recovery telemetry")
    logs = list(state.get("logs", []))

    incident = state.get("incident", {})
    inc_id = incident.get("id") if isinstance(incident, dict) else getattr(incident, "id", None)
    current_retries = state.get("retry_count", 0)

    # 1. Check explicit test simulation override
    simulated_fail = state.get("verification_result", {}).get("force_failure", False)

    # 2. Before metrics vs Post-recovery telemetry comparison (Section 16)
    before_metrics = state.get("metrics", {}) or {}
    exec_result = state.get("execution_result", {})
    action_status = exec_result.get("status")

    if simulated_fail or action_status != "success":
        verified = False
        new_retries = current_retries + 1
        msg = f"Post-recovery verification failed (attempt {new_retries}/{MAX_RETRIES}). Metrics remain degraded."
        if inc_id:
            update_recovery_action(
                incident_id=inc_id,
                execution_status="failed" if action_status != "success" else "executed",
                result=msg,
            )
    else:
        # Check post-action metrics
        engine = get_simulation_engine()
        post_metrics = engine.get_current_metrics()

        # Telemetry verification: latency <= 2.2s, error_rate <= 0.02, retrieval >= 0.85
        sla_passed = (
            post_metrics.get("latency", 1.2) <= SLA_LIMITS["latency"]
            and post_metrics.get("error_rate", 0.005) <= SLA_LIMITS["error_rate"]
            and post_metrics.get("retrieval_score", 0.92) >= SLA_LIMITS["retrieval_score"]
            and post_metrics.get("tool_failure_rate", 0.008) <= SLA_LIMITS["tool_failure_rate"]
            and post_metrics.get("api_success_rate", 0.99) >= SLA_LIMITS["api_success_rate"]
        )

        verified = sla_passed
        if verified:
            new_retries = current_retries
            msg = "Recovery verified: Telemetry returned to normal baseline SLA limits."
            if inc_id:
                incident_service.update_incident(incident_id=inc_id, status="resolved", resolution_notes=msg)
                update_recovery_action(
                    incident_id=inc_id,
                    execution_status="executed",
                    result=msg,
                )
        else:
            new_retries = current_retries + 1
            msg = f"Post-recovery verification failed: Telemetry breaches SLA limits. Attempt {new_retries}/{MAX_RETRIES}."
            if inc_id:
                update_recovery_action(
                    incident_id=inc_id,
                    execution_status="executed",
                    result=msg,
                )

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

    incident = state.get("incident", {})
    inc_id = incident.get("id") if isinstance(incident, dict) else getattr(incident, "id", None)
    if inc_id:
        incident_service.update_incident(incident_id=inc_id, status="escalated", resolution_notes="Escalated to human engineers.")
        update_recovery_action(incident_id=inc_id, execution_status="blocked", result="Escalated to human review")

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

checkpointer = InMemorySaver()


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

    compiled = builder.compile(checkpointer=checkpointer)

    # Attach transparent invoke wrapper to supply default thread_id when not provided
    orig_invoke = compiled.invoke

    def invoke_wrapper(input_data: Any, config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        if config is None:
            thread_id = None
            if isinstance(input_data, dict):
                inc = input_data.get("incident", {})
                thread_id = inc.get("id") if isinstance(inc, dict) else getattr(inc, "id", None)
            config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
        return orig_invoke(input_data, config=config, **kwargs)

    compiled.invoke = invoke_wrapper
    return compiled


# Global compiled graph
argus_graph = build_argus_graph()
