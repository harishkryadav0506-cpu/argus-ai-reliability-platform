"""
ARGUS MCP Incident Tools (ACTION Tools - Sections 12 & 22)

Implements lifecycle action tools for incidents:
- `create_incident`: Declares an anomaly incident in the platform (Risk: LOW)
- `update_incident`: Modifies incident status and resolution notes (Risk: LOW)

Every action tool enforces:
1. Input validation & allowable categories/statuses
2. Risk classification (low)
3. AuditLog entry before (STARTED) and after (SUCCESS / FAILED)
"""
import logging
from typing import Any, Dict, Optional

from app.services.audit_service import record_audit_log
from app.services import incident_service
from app.ml.failure_prediction import FailureCategory

logger = logging.getLogger(__name__)

ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}
ALLOWED_STATUSES = {"open", "investigating", "mitigating", "resolved", "escalated"}
VALID_FAILURE_TYPES = set(FailureCategory.ALL)


def create_incident(
    title: str,
    severity: str = "medium",
    failure_type: str = "UNKNOWN",
    description: str = "",
    incident_id: Optional[str] = None,
    approved: bool = True,
    actor: str = "mcp:create_incident",
) -> Dict[str, Any]:
    """
    ACTION Tool (Risk: LOW):
    Creates and records a new incident in ARGUS.
    """
    risk_level = "low"
    action_desc = f"create_incident(title='{title}', severity='{severity}', failure_type='{failure_type}')"

    # 1. Audit Log (Before)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="STARTED: Creating new incident record",
        incident_id=incident_id,
    )

    # 2. Input Validation
    if severity.lower() not in ALLOWED_SEVERITIES:
        err = f"Severity '{severity}' not in allowed severities: {sorted(ALLOWED_SEVERITIES)}"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    if failure_type not in VALID_FAILURE_TYPES:
        err = f"Failure type '{failure_type}' not recognized in FailureCategory"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    # 3. Execution
    inc = incident_service.create_incident(
        title=title,
        description=description,
        severity=severity.lower(),
        failure_type=failure_type,
        confidence=0.90,
    )

    # 4. Audit Log (After)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result=f"SUCCESS: Incident {inc.id} created with status {inc.status}",
        incident_id=inc.id,
    )

    return {
        "tool": "create_incident",
        "type": "ACTION",
        "risk_level": risk_level,
        "status": "success",
        "incident": {
            "id": inc.id,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "failure_type": inc.failure_type,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
        },
    }


def update_incident(
    incident_id: str,
    status: Optional[str] = None,
    resolution_notes: Optional[str] = None,
    approved: bool = True,
    actor: str = "mcp:update_incident",
) -> Dict[str, Any]:
    """
    ACTION Tool (Risk: LOW):
    Updates an existing incident's status and notes.
    """
    risk_level = "low"
    action_desc = f"update_incident(id={incident_id}, status={status})"

    # 1. Audit Log (Before)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result="STARTED: Updating incident details",
        incident_id=incident_id,
    )

    # 2. Input Validation
    if status and status.lower() not in ALLOWED_STATUSES:
        err = f"Status '{status}' not in allowed statuses: {sorted(ALLOWED_STATUSES)}"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    # 3. Execution
    inc = incident_service.update_incident(
        incident_id=incident_id,
        status=status.lower() if status else None,
        resolution_notes=resolution_notes,
    )

    if not inc:
        err = f"Incident '{incident_id}' not found"
        record_audit_log(actor=actor, action=action_desc, result=f"FAILED: {err}", incident_id=incident_id)
        raise ValueError(err)

    # 4. Audit Log (After)
    record_audit_log(
        actor=actor,
        action=action_desc,
        result=f"SUCCESS: Incident {incident_id} updated to status '{inc.status}'",
        incident_id=incident_id,
    )

    return {
        "tool": "update_incident",
        "type": "ACTION",
        "risk_level": risk_level,
        "status": "success",
        "incident": {
            "id": inc.id,
            "status": inc.status,
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
        },
    }
