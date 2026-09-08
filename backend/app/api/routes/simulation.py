"""
ARGUS Simulation API Routes (Phase 2)

Endpoints for injecting faults, resetting to normal baseline, and querying status.
"""
from fastapi import APIRouter, HTTPException

from app.schemas.simulation import (
    InjectFaultRequest,
    SimulationStatusResponse,
    FaultType,
)
from app.services.simulation_service import simulation_engine

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/inject", response_model=SimulationStatusResponse)
def inject_fault(req: InjectFaultRequest):
    """
    Injects a synthetic fault signature into the running simulation.
    """
    if req.fault_type not in FaultType.ALL:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fault_type '{req.fault_type}'. Valid types: {FaultType.ALL}",
        )

    status = simulation_engine.inject_fault(
        fault_type=req.fault_type,
        severity=req.severity,
        duration_seconds=req.duration_seconds,
    )
    # Perform immediate tick to reflect fault
    simulation_engine.tick()
    return simulation_engine.get_status()


@router.post("/reset", response_model=SimulationStatusResponse)
def reset_simulation():
    """
    Resets the simulation engine to generate normal baseline traffic.
    """
    status = simulation_engine.reset_to_normal()
    simulation_engine.tick()
    return simulation_engine.get_status()


@router.get("/status", response_model=SimulationStatusResponse)
def get_simulation_status():
    """
    Returns the current status of the simulation engine.
    """
    return simulation_engine.get_status()


@router.post("/tick")
def advance_tick():
    """
    Manually advances the simulation by one tick (useful for deterministic tests and demos).
    """
    point = simulation_engine.tick()
    return {
        "status": "ticked",
        "point": point,
        "active_fault": simulation_engine._active_fault,
    }
