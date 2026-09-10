"""
ARGUS Recovery Action Service (Phase 1 & 7 - Sections 13 & 22)

Manages persistence and retrieval of RecoveryAction database records with dual-write in-memory fallback.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import RecoveryAction
from app.database.session import db_session

logger = logging.getLogger(__name__)

# In-memory storage fallback for testing and when DB is unavailable
_IN_MEMORY_RECOVERY_ACTIONS: List[Dict[str, Any]] = []


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_recovery_action(
    incident_id: str,
    strategy: str,
    risk: float,
    approval_status: str = "pending",
    execution_status: str = "pending",
    result: str = "",
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Creates and persists a new RecoveryAction record.
    """
    action_id = str(uuid.uuid4())
    now = _now()
    risk_str = str(round(risk, 2))

    data = {
        "id": action_id,
        "incident_id": incident_id,
        "strategy": strategy,
        "risk": risk_str,
        "approval_status": approval_status,
        "execution_status": execution_status,
        "result": result,
        "created_at": now.isoformat(),
    }
    _IN_MEMORY_RECOVERY_ACTIONS.append(data)

    def _persist(s: Session):
        entry = RecoveryAction(
            id=action_id,
            incident_id=incident_id,
            strategy=strategy,
            risk=risk_str,
            approval_status=approval_status,
            execution_status=execution_status,
            result=result,
            created_at=now,
        )
        s.add(entry)
        s.commit()

    if db is not None:
        try:
            _persist(db)
        except Exception as exc:
            logger.warning("Database unavailable during record_recovery_action (%s); stored in memory.", exc)
    else:
        try:
            with db_session() as s:
                _persist(s)
        except Exception as exc:
            logger.warning("Database unavailable during record_recovery_action (%s); stored in memory.", exc)

    return data


def update_recovery_action(
    incident_id: str,
    approval_status: Optional[str] = None,
    execution_status: Optional[str] = None,
    result: Optional[str] = None,
    db: Optional[Session] = None,
) -> Optional[Dict[str, Any]]:
    """
    Updates the most recent recovery action associated with an incident.
    """
    def _update_record(entry: RecoveryAction):
        if approval_status:
            entry.approval_status = approval_status
        if execution_status:
            entry.execution_status = execution_status
        if result:
            entry.result = result

    # Update in database if available
    try:
        def _execute(s: Session) -> Optional[RecoveryAction]:
            stmt = select(RecoveryAction).where(RecoveryAction.incident_id == incident_id).order_by(RecoveryAction.created_at.desc())
            entry = s.scalars(stmt).first()
            if entry:
                _update_record(entry)
                s.commit()
            return entry

        if db is not None:
            db_entry = _execute(db)
        else:
            with db_session() as s:
                db_entry = _execute(s)
    except Exception as exc:
        logger.warning("Database unavailable during update_recovery_action (%s); using in-memory entry.", exc)
        db_entry = None

    # Update in-memory entry
    for entry in reversed(_IN_MEMORY_RECOVERY_ACTIONS):
        if entry.get("incident_id") == incident_id:
            if approval_status:
                entry["approval_status"] = approval_status
            if execution_status:
                entry["execution_status"] = execution_status
            if result:
                entry["result"] = result
            return entry

    return None


def get_recovery_actions_for_incident(
    incident_id: str,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves all recovery actions for an incident.
    """
    try:
        def _fetch(s: Session) -> List[RecoveryAction]:
            stmt = select(RecoveryAction).where(RecoveryAction.incident_id == incident_id).order_by(RecoveryAction.created_at.desc())
            return list(s.scalars(stmt).all())

        if db is not None:
            records = _fetch(db)
        else:
            with db_session() as s:
                records = _fetch(s)
        return [
            {
                "id": r.id,
                "incident_id": r.incident_id,
                "strategy": r.strategy,
                "risk": r.risk,
                "approval_status": r.approval_status,
                "execution_status": r.execution_status,
                "result": r.result,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in records
        ]
    except Exception as exc:
        logger.warning("Database unavailable during get_recovery_actions_for_incident (%s); returning in-memory.", exc)
        return [r for r in reversed(_IN_MEMORY_RECOVERY_ACTIONS) if r.get("incident_id") == incident_id]


def clear_in_memory_recovery_actions() -> None:
    _IN_MEMORY_RECOVERY_ACTIONS.clear()
