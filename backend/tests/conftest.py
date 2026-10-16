"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core import registry
from app.main import app
from app.solvers import load_all


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """A TestClient for the real app (lifespan loads every solver module)."""
    load_all()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def registry_guard() -> Iterator[None]:
    """Isolate registry mutations made by a test from the rest of the suite.

    The registry is emptied for the duration of the test (so real, auto-loaded
    solvers like ``bisection`` never leak into the assertions) and restored
    exactly afterwards.
    """
    snapshot = dict(registry._REGISTRY)
    registry._REGISTRY.clear()
    try:
        yield
    finally:
        registry._REGISTRY.clear()
        registry._REGISTRY.update(snapshot)
