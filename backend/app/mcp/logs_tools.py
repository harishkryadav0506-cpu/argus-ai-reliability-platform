"""
ARGUS MCP Logs & Knowledge Tools (READ Tools - Section 12)

Provides inspection tools for logs, incident history, deployment history, and runbooks:
- `get_recent_logs`: Queries recent structured log events.
- `get_incident_history`: Queries past incidents and resolutions.
- `get_deployment_history`: Queries recent deployment revisions.
- `search_runbooks`: Semantic search over the operational runbook knowledge base.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.services.incident_service import list_incidents
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)


def get_recent_logs(
    service_name: Optional[str] = None,
    limit: int = 50,
    level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    READ Tool: Returns recent structured log entries for diagnosis.
    """
    now = datetime.now(timezone.utc)
    base_logs = [
        {
            "timestamp": (now - timedelta(seconds=i * 12)).isoformat(),
            "service": "llm_gateway" if i % 2 == 0 else "vector_db",
            "level": "ERROR" if i % 5 == 0 else ("WARNING" if i % 3 == 0 else "INFO"),
            "message": (
                "Upstream gateway response latency elevated (>2500ms)"
                if i % 5 == 0
                else ("Query cache miss; querying HNSW index" if i % 3 == 0 else "Request processed successfully")
            ),
        }
        for i in range(min(limit * 2, 100))
    ]

    filtered = base_logs
    if service_name:
        filtered = [log for log in filtered if log["service"] == service_name]
    if level:
        filtered = [log for log in filtered if log["level"] == level.upper()]

    return filtered[:limit]


def get_incident_history(
    limit: int = 10,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    READ Tool: Queries incident history from database or in-memory tracking.
    """
    incidents = list_incidents(status=status, limit=limit)
    return [
        {
            "id": inc.id,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "failure_type": inc.failure_type,
            "confidence": inc.confidence,
            "created_at": inc.created_at.isoformat() if inc.created_at else "",
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
        }
        for inc in incidents
    ]


def get_deployment_history(
    service_name: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    READ Tool: Returns recent deployment revisions and build tags.
    """
    now = datetime.now(timezone.utc)
    deployments = [
        {
            "revision": "v2.0.0-rc1",
            "service": "core_service",
            "deployed_at": (now - timedelta(hours=2)).isoformat(),
            "status": "active",
            "commit_sha": "e960196",
            "author": "ci/cd",
        },
        {
            "revision": "v1.2.0",
            "service": "llm_gateway",
            "deployed_at": (now - timedelta(days=2)).isoformat(),
            "status": "active",
            "commit_sha": "a4b1c2d",
            "author": "platform-team",
        },
        {
            "revision": "v1_stable",
            "service": "llm_gateway",
            "deployed_at": (now - timedelta(days=7)).isoformat(),
            "status": "superseded",
            "commit_sha": "9f8e7d6",
            "author": "platform-team",
        },
        {
            "revision": "v1.1.9",
            "service": "vector_db",
            "deployed_at": (now - timedelta(days=10)).isoformat(),
            "status": "active",
            "commit_sha": "3b2a1c0",
            "author": "data-infra",
        },
    ]

    if service_name:
        deployments = [d for d in deployments if d["service"] == service_name]

    return deployments[:limit]


def search_runbooks(
    query: str,
    k: int = 3,
    failure_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    READ Tool: Semantic search over the operational runbook knowledge base.
    """
    return retrieve(query=query, k=k, failure_type_filter=failure_type)
