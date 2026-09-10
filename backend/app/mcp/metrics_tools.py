"""
ARGUS MCP Metrics Tools (READ Tools - Section 12)

Provides telemetry and health inspection tools for monitored subsystems:
- `get_system_metrics`: Retrieves real-time and windowed telemetry.
- `get_service_health`: Queries health state across subsystems.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.simulation_service import get_simulation_engine

logger = logging.getLogger(__name__)


def get_system_metrics(window_minutes: int = 15) -> Dict[str, Any]:
    """
    READ Tool: Returns current system metrics and recent snapshot history.
    """
    engine = get_simulation_engine()
    current_metrics = engine.generate_metrics()
    history = engine.get_history()

    # If history is available, extract up to window_minutes of snapshots
    recent_history = history[-max(window_minutes, 1):] if history else [current_metrics]

    return {
        "tool": "get_system_metrics",
        "type": "READ",
        "window_minutes": window_minutes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_metrics": current_metrics,
        "sample_count": len(recent_history),
        "metrics_summary": {
            k: {
                "current": current_metrics.get(k),
                "avg": round(sum(s.get(k, 0.0) for s in recent_history) / max(len(recent_history), 1), 4),
            }
            for k in current_metrics
        },
    }


def get_service_health(service_name: Optional[str] = None) -> Dict[str, Any]:
    """
    READ Tool: Queries health and availability status of system components.
    """
    subsystems = {
        "llm_gateway": {
            "status": "healthy",
            "uptime_pct": 99.95,
            "provider": "gemini",
            "active_model": "gemini-2.0-flash",
            "circuit_breaker": "closed",
        },
        "vector_db": {
            "status": "healthy",
            "backend": "ChromaDB (local ONNX)",
            "index_type": "HNSW",
            "collections": ["runbooks", "historical_incidents"],
            "lock_status": "unlocked",
        },
        "api_gateway": {
            "status": "healthy",
            "error_rate_pct": 0.05,
            "active_connections": 42,
            "rate_limit_state": "nominal",
        },
        "agent_worker": {
            "status": "healthy",
            "state_engine": "LangGraph",
            "active_runs": 0,
            "max_retries": 3,
        },
        "core_service": {
            "status": "healthy",
            "framework": "FastAPI",
            "memory_usage_mb": 142.5,
        },
    }

    if service_name:
        if service_name not in subsystems:
            return {
                "tool": "get_service_health",
                "type": "READ",
                "status": "not_found",
                "service_name": service_name,
                "error": f"Unknown subsystem: {service_name}",
            }
        return {
            "tool": "get_service_health",
            "type": "READ",
            "service_name": service_name,
            "data": subsystems[service_name],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "tool": "get_service_health",
        "type": "READ",
        "overall_status": "healthy",
        "services": subsystems,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
