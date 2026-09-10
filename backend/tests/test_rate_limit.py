"""
ARGUS Rate-Limiting & Security Tests (Phase 10 - Section 21)
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rate_limit_headers_present_on_requests():
    """Verify that rate-limiting headers are attached to non-exempt API responses."""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
    assert "x-ratelimit-reset" in response.headers


def test_exempt_paths_not_rate_limited():
    """Verify that /health and / liveness probes are exempt from rate limits."""
    health_resp = client.get("/health")
    assert health_resp.status_code == 200

    root_resp = client.get("/")
    assert root_resp.status_code == 200
