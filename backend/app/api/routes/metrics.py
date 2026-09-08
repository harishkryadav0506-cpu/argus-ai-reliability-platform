"""
ARGUS Metrics API Routes (Phase 2)

Endpoints for querying real-time and historical time-series metrics.
"""
from fastapi import APIRouter, Query

from app.schemas.simulation import MetricsResponse
from app.services.simulation_service import simulation_engine

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(limit: int = Query(default=50, ge=1, le=300)):
    """
    Returns current metrics snapshot and recent time-series history.
    """
    current = simulation_engine.get_current_metrics()
    history = simulation_engine.get_history(limit=limit)
    return {
        "current": current,
        "history": history,
        "count": len(history),
    }
