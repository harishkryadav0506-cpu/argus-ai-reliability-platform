"""
ARGUS Database Session

Provides a SQLAlchemy engine/session. Connection is attempted lazily so the
app can still boot (and report DB as unhealthy via /health) even if
PostgreSQL isn't reachable yet — per Section 32's graceful-degradation rule.
"""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

connect_args = {}
if "postgresql" in settings.DATABASE_URL:
    connect_args["connect_timeout"] = 1

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """Context manager for use outside FastAPI request handlers (e.g. in
    agents, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_health() -> dict:
    """Used by /health — never raises, always returns a status dict."""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "OK"}
    except OperationalError as e:
        logger.warning("Database health check failed: %s", e)
        return {"status": "UNAVAILABLE", "error": str(e)}
    except Exception as e:
        logger.warning("Unexpected database health check error: %s", e)
        return {"status": "ERROR", "error": str(e)}
