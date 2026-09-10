"""
ARGUS LangGraph State Schema (Phase 5 - Section 10)

Defines the shared graph state across all agents and nodes during the
incident lifecycle (Detect -> Classify -> Diagnose -> Recover -> Verify -> Evaluate -> Postmortem).
"""
from typing import Any, Dict, List, Optional, TypedDict


class ArgusState(TypedDict, total=False):
    # Core Incident Entity (Section 22 Incident model representation)
    incident: Dict[str, Any]

    # Monitored Telemetry
    metrics: Dict[str, float]
    logs: List[str]
    evidence: List[str]

    # Failure Classification (Section 9)
    failure_type: str
    failure_confidence: float

    # Root Cause & RAG Grounding (Section 11)
    root_cause: str
    retrieved_runbooks: List[Dict[str, Any]]

    # Recovery Planning (Section 14 & 15)
    recovery_options: List[Dict[str, Any]]
    risk_score: float
    selected_strategy: Dict[str, Any]

    # Human-in-the-loop Gates (Section 13)
    approval_required: bool
    approval_status: str  # "not_required" | "pending" | "approved" | "rejected"

    # Execution & Verification (Section 16)
    execution_result: Dict[str, Any]
    verification_result: Dict[str, Any]  # {"recovery_verified": bool, "details": ...}

    # Evaluation & Resolution (Sections 18, 19, 26)
    evaluation_result: Dict[str, Any]
    final_status: str  # "open" | "investigating" | "resolved" | "failed" | "needs_review"

    # Loop bounding and audit trail
    retry_count: int
    history_trace: List[str]
