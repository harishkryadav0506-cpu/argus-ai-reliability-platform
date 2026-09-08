"""
ARGUS Incidents API Routes (Phase 2)

Endpoints for querying and creating incidents.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.services import incident_service
from app.services.simulation_service import simulation_engine

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
