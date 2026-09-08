"""
Phase 1 tests — app boot + health endpoint.

Run with: pytest backend/tests/test_health.py -v
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_boots():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "ARGUS"
    assert body["status"] == "running"


def test_health_returns_ok_even_without_optional_services():
    """Per Section 32: /health must never 500, even if DB/Redis/LangSmith
    are unavailable — it just reports their individual status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "OK"
    assert "database" in body["services"]
    assert "llm" in body["services"]
    assert "langsmith" in body["services"]
    assert "redis" in body["services"]
    assert "vector_db" in body["services"]
    assert "mcp" in body["services"]
