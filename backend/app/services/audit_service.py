"""
ARGUS Audit Service (Phase 1 & 6 - Sections 12 & 22)

Records and queries structured audit logs for all system, agent, and MCP action tool executions.
Per Section 32, operations degrade gracefully if database connectivity is unavailable.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import AuditLog
from app.database.session import db_session

logger = logging.getLogger(__name__)

# In-memory audit log store for testing and when database is unavailable
_IN_MEMORY_AUDIT_LOGS: List[Dict[str, Any]] = []


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_audit_log(
    actor: str,
    action: str,
    result: str,
    incident_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Records an audit log entry in the database and in-memory cache.
    """
    log_id = str(uuid.uuid4())
    now = _now()

    entry_data = {
        "id": log_id,
        "incident_id": incident_id,
        "actor": actor,
        "action": action,
        "result": result,
        "timestamp": now.isoformat(),
    }
    _IN_MEMORY_AUDIT_LOGS.append(entry_data)

    def _persist(s: Session):
        entry = AuditLog(
            id=log_id,
            incident_id=incident_id,
            actor=actor,
            action=action,
            result=result,
            timestamp=now,
        )
        s.add(entry)
        s.commit()

    if db is not None:
        try:
            _persist(db)
        except Exception as exc:
            logger.warning("Database unavailable during record_audit_log (%s); using in-memory entry.", exc)
    else:
        try:
            with db_session() as s:
                _persist(s)
        except Exception as exc:
            logger.warning("Database unavailable during record_audit_log (%s); using in-memory entry.", exc)

    logger.info("AUDIT: actor=%s action=%s result=%s incident=%s", actor, action, result, incident_id)
    return entry_data


def get_audit_logs(
    incident_id: Optional[str] = None,
    limit: int = 50,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves audit logs, filtered by incident_id if specified.
    """
    def _fetch(s: Session) -> List[AuditLog]:
        query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        if incident_id:
            query = query.where(AuditLog.incident_id == incident_id)
        return list(s.scalars(query).all())

    try:
        if db is not None:
            records = _fetch(db)
        else:
            with db_session() as s:
                records = _fetch(s)
        return [
            {
                "id": r.id,
                "incident_id": r.incident_id,
                "actor": r.actor,
                "action": r.action,
                "result": r.result,
                "timestamp": r.timestamp.isoformat() if r.timestamp else "",
            }
            for r in records
        ]
    except Exception as exc:
        logger.warning("Database unavailable during get_audit_logs (%s); falling back to memory.", exc)
        filtered = [
            l for l in reversed(_IN_MEMORY_AUDIT_LOGS)
            if not incident_id or l.get("incident_id") == incident_id
        ]
        return filtered[:limit]


def clear_in_memory_audit_logs() -> None:
    """Helper for testing."""
    _IN_MEMORY_AUDIT_LOGS.clear()
