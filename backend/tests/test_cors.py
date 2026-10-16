"""Tests for the API middleware: CORS preflight handling."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
def test_cors_preflight_allows_local_dev_origins(origin: str) -> None:
    """Both localhost and 127.0.0.1 forms are accepted, so the app works
    whichever host the dev server is opened with."""
    response = client.options(
        "/api/methods",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_preflight_rejects_unknown_origin() -> None:
    response = client.options(
        "/api/methods",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
