"""
ARGUS Incident Service (Phase 1 & 2)

Handles creation, retrieval, and persistence of incidents and metric snapshots.
Per Section 32, operations degrade gracefully if database connectivity is unavailable.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.database.models import Incident, MetricSnapshot, AuditLog
from app.database.session import db_session

logger = logging.getLogger(__name__)

# In-memory fallback cache when database is temporarily unavailable
_IN_MEMORY_INCIDENTS: List[Incident] = []


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_incident(
    title: str,
    description: str = "",
    severity: str = "medium",
    failure_type: str = "UNKNOWN",
    confidence: float = 0.0,
    metrics: Optional[Dict[str, float]] = None,
    db: Optional[Session] = None,
) -> Incident:
    """
    Creates an incident and persists associated metric snapshots.
    If db is provided, uses it; otherwise uses db_session().
    Gracefully falls back to in-memory tracking if DB connection fails.
    """
    incident_id = str(uuid.uuid4())
    now = _now()
    dedup_window_seconds = 30
    cutoff = now - timedelta(seconds=dedup_window_seconds)

    # 1. Dedup check against existing DB incidents
    def _find_recent_duplicate(session: Session) -> Optional[Incident]:
        stmt = (
            select(Incident)
            .where(
                Incident.failure_type == failure_type,
                Incident.status.in_(["open", "investigating"]),
                Incident.created_at >= cutoff,
            )
            .order_by(Incident.created_at.desc())
        )
        return session.scalars(stmt).first()

    try:
        existing = None
        if db is not None:
            existing = _find_recent_duplicate(db)
        else:
            with db_session() as session:
                existing = _find_recent_duplicate(session)
        if existing:
            logger.info("Deduplication: returning recent open incident %s for %s", existing.id, failure_type)
            return existing
    except Exception as exc:
        logger.debug("DB query during dedup check failed: %s", exc)

    # Also check in-memory list
    for inc in reversed(_IN_MEMORY_INCIDENTS):
        if isinstance(inc, dict):
            f_type = inc.get("failure_type")
            st = inc.get("status")
            c_at = inc.get("created_at")
        else:
            f_type = getattr(inc, "failure_type", None)
            st = getattr(inc, "status", None)
            c_at = getattr(inc, "created_at", None)

        if f_type == failure_type and st in ("open", "investigating") and c_at:
            age = (now - c_at).total_seconds() if hasattr(c_at, "total_seconds") or isinstance(c_at, datetime) else 999
            if age < dedup_window_seconds:
                logger.info("Deduplication (in-memory): returning recent incident %s", getattr(inc, "id", None))
                return inc

    incident = Incident(
        id=incident_id,
        title=title,
        description=description,
        severity=severity,
        status="open",
        failure_type=failure_type,
        confidence=confidence,
        created_at=now,
    )

    snapshots: List[MetricSnapshot] = []
    if metrics:
        for metric_name, value in metrics.items():
            # Skip alias duplicate fields (consolidating to token_usage and cpu_usage)
            if metric_name in ("token_count", "cpu_utilization"):
                continue
            snapshot = MetricSnapshot(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                metric_name=metric_name,
                value=float(value),
                timestamp=now,
            )
            snapshots.append(snapshot)
    incident.metrics = snapshots

    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        actor="system:simulation_monitor",
        action="incident_created",
        result=f"Incident {incident_id} created for {failure_type} with severity {severity}",
        timestamp=now,
    )
    incident.audit_logs = [audit_entry]

    def _persist(session: Session):
        session.add(incident)
        for s in snapshots:
            session.add(s)
        session.add(audit_entry)
        session.flush()

    try:
        if db is not None:
            _persist(db)
            db.commit()
        else:
            with db_session() as session:
                _persist(session)
        logger.info("Successfully persisted incident %s to database.", incident_id)
    except Exception as e:
        logger.warning(
            "Database unavailable during create_incident (%s); retaining incident %s in-memory.",
            e,
            incident_id,
        )
        _IN_MEMORY_INCIDENTS.append(incident)

    return incident


def list_incidents(db: Optional[Session] = None, limit: int = 50) -> List[Incident]:
    """
    Retrieves the most recent incidents.
    """
    try:
        if db is not None:
            stmt = select(Incident).options(selectinload(Incident.metrics)).order_by(Incident.created_at.desc()).limit(limit)
            return list(db.scalars(stmt).all())
        else:
            with db_session() as session:
                stmt = select(Incident).options(selectinload(Incident.metrics)).order_by(Incident.created_at.desc()).limit(limit)
                return list(session.scalars(stmt).all())
    except Exception as e:
        logger.warning("Database unavailable during list_incidents (%s); returning in-memory incidents.", e)
        return list(reversed(_IN_MEMORY_INCIDENTS))[:limit]


def get_incident(incident_id: str, db: Optional[Session] = None) -> Optional[Incident]:
    """
    Retrieves a single incident by ID with its metric snapshots.
    """
    try:
        if db is not None:
            stmt = select(Incident).options(selectinload(Incident.metrics)).where(Incident.id == incident_id)
            return db.scalars(stmt).first()
        else:
            with db_session() as session:
                stmt = select(Incident).options(selectinload(Incident.metrics)).where(Incident.id == incident_id)
                return session.scalars(stmt).first()
    except Exception as e:
        logger.warning("Database unavailable during get_incident (%s); checking in-memory.", e)
        for inc in _IN_MEMORY_INCIDENTS:
            if inc.id == incident_id:
                return inc
        return None


def update_incident(
    incident_id: str,
    status: Optional[str] = None,
    resolution_notes: Optional[str] = None,
    db: Optional[Session] = None,
) -> Optional[Incident]:
    """
    Updates status and details of an existing incident.
    """
    now = _now()

    def _update_fields(inc: Incident):
        if status:
            inc.status = status
            if status.lower() == "resolved" and not inc.resolved_at:
                inc.resolved_at = now
        if resolution_notes:
            inc.description = f"{inc.description}\nResolution: {resolution_notes}".strip()

    try:
        if db is not None:
            stmt = select(Incident).where(Incident.id == incident_id)
            inc = db.scalars(stmt).first()
            if inc:
                _update_fields(inc)
                db.commit()
                return inc
        else:
            with db_session() as session:
                stmt = select(Incident).where(Incident.id == incident_id)
                inc = session.scalars(stmt).first()
                if inc:
                    _update_fields(inc)
                    session.commit()
                    return inc
    except Exception as e:
        logger.warning("Database unavailable during update_incident (%s); updating in-memory.", e)

    # In-memory update
    for inc in _IN_MEMORY_INCIDENTS:
        if inc.id == incident_id:
            _update_fields(inc)
            return inc
    return None


def resolve_incident(
    incident_id: str,
    resolution_notes: Optional[str] = None,
    db: Optional[Session] = None,
) -> Optional[Incident]:
    """
    Convenience function to transition an incident to resolved status.
    """
    return update_incident(incident_id=incident_id, status="resolved", resolution_notes=resolution_notes, db=db)
