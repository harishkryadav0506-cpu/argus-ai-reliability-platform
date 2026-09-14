"""
Pytest configuration and global safety guards for ARGUS test suite.
"""
import os
import pytest
from app.config import get_settings


def pytest_sessionstart(session):
    """
    Fail-fast guard at session start (FIX-9c):
    if the resolved DATABASE_URL does not contain "argus_test",
    raise RuntimeError("Refusing to run tests against non-test database")
    so tests can never accidentally touch the dev/production database.
    """
    get_settings.cache_clear()
    settings = get_settings()
    db_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    if "argus_test" not in db_url:
        raise RuntimeError("Refusing to run tests against non-test database")


@pytest.fixture(scope="session")
def isolated_db():
    """
    Session-scoped isolated DB fixture with safety locks (FIX-9b).
    MUST NOT open any engine/session derived from the default DATABASE_URL directly.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database.models import Base

    # Isolated in-memory SQLite engine
    isolated_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=isolated_engine)
    IsolatedSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=isolated_engine)

    session = IsolatedSessionLocal()
    try:
        yield session
    finally:
        session.close()
        isolated_engine.dispose()
