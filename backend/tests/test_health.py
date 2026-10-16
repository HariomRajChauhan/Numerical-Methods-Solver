"""Smoke tests for the health endpoint (Phase 1 scaffold)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    """GET /api/health reports service status and version."""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Numerical Methods Solver"
    assert body["version"]


def test_openapi_document_available() -> None:
    """The OpenAPI schema is served (useful for frontend/types tooling)."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()
