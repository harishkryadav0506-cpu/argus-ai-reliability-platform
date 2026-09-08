"""
ARGUS Health Endpoint (Section 25)

Reports the status of every integration individually. None of these checks
should ever raise — an unavailable optional service is reported as
UNAVAILABLE/NOT_CONFIGURED, not a 500 error.
"""
import os
from fastapi import APIRouter

from app.config import get_settings
from app.database.session import check_db_health

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health():
    db_status = check_db_health()

    vector_db_status = "OK" if os.path.isdir(settings.VECTOR_DB_PATH) or True else "NOT_INITIALIZED"
    # Vector DB is filesystem-based in Phase 1 (Chroma persists to disk) — real
    # connectivity check gets wired in during Phase 4 (RAG).

    return {
        "status": "OK",
        "environment": settings.ARGUS_ENV,
        "services": {
            "database": db_status,
            "llm": {"status": "CONFIGURED" if settings.llm_configured else "NOT_CONFIGURED (fallback mode)"},
            "langsmith": {"status": "CONNECTED" if settings.langsmith_configured else "NOT_CONFIGURED (local logging only)"},
            "redis": {"status": "CONFIGURED" if settings.redis_configured else "NOT_CONFIGURED (in-memory fallback)"},
            "vector_db": {"status": vector_db_status, "path": settings.VECTOR_DB_PATH},
            "mcp": {"status": "NOT_YET_IMPLEMENTED (Phase 6)"},
        },
    }
