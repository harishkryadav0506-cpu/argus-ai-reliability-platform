"""
Regression test for 30-second incident deduplication gate (FIX-9).
"""
import pytest
from sqlalchemy import select
from app.database.models import Incident
from app.services import incident_service


def test_dedup_gate_regression_same_failure_type_within_30s(isolated_db):
    """
    Regression test: creating two incidents with same failure_type within
    30 seconds yields exactly 1 incident.
    SAFETY LOCKS (mandatory):
    - The test MUST use the session-scoped isolated DB fixture only.
    - It MUST NOT open any engine/session derived from the default
      DATABASE_URL directly.
    """
    failure_type = "MEMORY_LEAK_SPIKE"

    # Create first incident
    inc1 = incident_service.create_incident(
        title="First Incident Alert",
        description="First breach detected",
        severity="high",
        failure_type=failure_type,
        confidence=0.95,
        metrics={"latency": 3.5, "cpu_usage": 80.0},
        db=isolated_db,
    )

    # Create second incident with identical failure_type immediately (< 30 seconds)
    inc2 = incident_service.create_incident(
        title="Second Incident Alert - Duplicate",
        description="Second breach detected within 30s window",
        severity="critical",
        failure_type=failure_type,
        confidence=0.98,
        metrics={"latency": 3.8, "cpu_usage": 85.0},
        db=isolated_db,
    )

    # Both calls should return the exact same deduped incident
    assert inc1.id == inc2.id

    # Query the isolated database directly to verify exactly 1 incident exists
    stmt = select(Incident).where(Incident.failure_type == failure_type)
    incidents_in_db = isolated_db.scalars(stmt).all()
    assert len(incidents_in_db) == 1
    assert incidents_in_db[0].id == inc1.id
