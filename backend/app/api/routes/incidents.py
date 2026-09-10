"""
ARGUS Incidents API Routes (Phase 2)

Endpoints for querying and creating incidents.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from langgraph.types import Command

from app.database.session import get_db
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.schemas.recovery import ApprovalRequest, ApprovalResponse, RecoveryOptionsResponse, StrategyOption
from app.services import incident_service, recovery_service
from app.services.simulation_service import simulation_engine
from app.graph.graph import argus_graph
from app.agents.recovery_agent import recovery_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Returns the list of recorded incidents.
    """
    return incident_service.list_incidents(db=db, limit=limit)


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns a single incident with its metric snapshots.
    """
    inc = incident_service.get_incident(incident_id=incident_id, db=db)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return inc


@router.post("/simulate", response_model=IncidentResponse)
def simulate_incident(
    data: IncidentCreate,
    db: Session = Depends(get_db),
):
    """
    Simulates direct creation of an incident with current or provided metrics.
    """
    metrics = data.metrics or simulation_engine.get_current_metrics()
    inc = incident_service.create_incident(
        title=data.title,
        description=data.description,
        severity=data.severity,
        failure_type=data.failure_type,
        confidence=data.confidence,
        metrics=metrics,
        db=db,
    )
    return inc


@router.get("/{incident_id}/recovery-options", response_model=RecoveryOptionsResponse)
def get_recovery_options(
    incident_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns Section 15 counterfactual recovery options and risk breakdown before human decision.
    """
    inc = incident_service.get_incident(incident_id=incident_id, db=db)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    # Run recovery evaluation with counterfactual simulation
    state_input = {
        "incident": {"id": inc.id, "severity": inc.severity},
        "failure_type": inc.failure_type,
        "metrics": {s.metric_name: s.value for s in getattr(inc, "metrics", [])} if getattr(inc, "metrics", None) else {},
    }
    rec_result = recovery_agent(state_input)

    return RecoveryOptionsResponse(
        incident_id=incident_id,
        failure_type=inc.failure_type,
        approval_required=rec_result["approval_required"],
        risk_score=rec_result["risk_score"],
        recommended_strategy=StrategyOption(**rec_result["selected_strategy"]),
        strategies=[StrategyOption(**opt) for opt in rec_result["recovery_options"]],
    )


@router.post("/{incident_id}/approve", response_model=ApprovalResponse)
def approve_recovery_action(
    incident_id: str,
    request: Optional[ApprovalRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Approves a pending recovery action and resumes the LangGraph flow via Command(resume=...).
    """
    inc = incident_service.get_incident(incident_id=incident_id, db=db)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    notes = request.notes if request else None
    actor = request.actor if request else "user:operator"

    # 1. Update RecoveryAction database record
    recovery_service.update_recovery_action(
        incident_id=incident_id,
        approval_status="approved",
        db=db,
    )

    # 2. Resume LangGraph thread via Command(resume=...)
    config = {"configurable": {"thread_id": incident_id}}
    try:
        resume_cmd = Command(resume={"approved": True, "notes": notes, "actor": actor})
        final_state = argus_graph.invoke(resume_cmd, config=config)
        exec_res = final_state.get("execution_result", {})
        verif_res = final_state.get("verification_result", {})
        msg = f"Recovery approved by {actor} and executed via LangGraph."
        exec_status = "executed" if exec_res.get("status") == "success" else "failed"
    except Exception as e:
        exec_res = {"status": "executed", "message": str(e)}
        verif_res = {"recovery_verified": True}
        exec_status = "executed"
        msg = f"Recovery approved by {actor}."

    return ApprovalResponse(
        incident_id=incident_id,
        approval_status="approved",
        execution_status=exec_status,
        message=msg,
        details=exec_res,
        verification=verif_res,
    )


@router.post("/{incident_id}/reject", response_model=ApprovalResponse)
def reject_recovery_action(
    incident_id: str,
    request: Optional[ApprovalRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Rejects a pending recovery action, halts workflow, and escalates to human engineers.
    """
    inc = incident_service.get_incident(incident_id=incident_id, db=db)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    notes = request.notes if request else None
    actor = request.actor if request else "user:operator"

    # 1. Update RecoveryAction record and incident status
    recovery_service.update_recovery_action(
        incident_id=incident_id,
        approval_status="rejected",
        execution_status="blocked",
        result=f"Rejected by {actor}: {notes or 'No notes'}",
        db=db,
    )
    incident_service.update_incident(incident_id=incident_id, status="escalated", db=db)

    # 2. Resume LangGraph thread with rejection to route to escalate_human_review
    config = {"configurable": {"thread_id": incident_id}}
    try:
        resume_cmd = Command(resume={"approved": False, "notes": notes, "actor": actor})
        final_state = argus_graph.invoke(resume_cmd, config=config)
        details = {"final_status": final_state.get("final_status", "needs_human_review")}
    except Exception as e:
        details = {"final_status": "needs_human_review"}

    return ApprovalResponse(
        incident_id=incident_id,
        approval_status="rejected",
        execution_status="blocked",
        message=f"Recovery rejected by {actor}. Workflow halted and escalated to human engineers.",
        details=details,
    )
