"""End-to-end API tests for the methods catalogue and the solve dispatch."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.core import registry
from app.core.models import (
    Chapter,
    InputField,
    MethodMeta,
    MethodStatus,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)


def _solver_meta(method_id: str = "unit_solver", status: MethodStatus = MethodStatus.AVAILABLE) -> MethodMeta:
    return MethodMeta(
        id=method_id,
        chapter=Chapter.CH1_NONLINEAR,
        name="Unit Solver",
        status=status,
        summary="Used by API tests.",
        pseudocode="1. Do the thing.",
        input_schema=[
            InputField(key="x0", label="Initial guess", type="number"),
            InputField(key="function", label="f(x)", type="function", variable="x", required=False),
        ],
    )


def _ok_solver(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    del limits
    return SolveResponse(
        method="unit_solver",
        status=SolveStatus.CONVERGED,
        result={"root": inputs["x0"]},
        steps=[Step(title="Guess", latex=r"x_0 = 1")],
    )


class TestCatalogue:
    def test_list_methods_returns_chapters_and_methods(self, client: TestClient) -> None:
        response = client.get("/api/methods")
        assert response.status_code == 200
        body = response.json()
        assert len(body["chapters"]) == 6
        assert body["chapters"][0]["title"] == "Non-linear Equations"
        assert isinstance(body["methods"], list)

    def test_unknown_method_detail_is_404(self, client: TestClient) -> None:
        response = client.get("/api/methods/does_not_exist")
        assert response.status_code == 404
        assert response.json()["code"] == "method_not_found"


class TestSolve:
    def test_unknown_method_is_404(self, client: TestClient) -> None:
        response = client.post("/api/solve/does_not_exist", json={})
        assert response.status_code == 404
        assert response.json()["code"] == "method_not_found"

    def test_stub_method_is_409(self, client: TestClient, registry_guard: None) -> None:
        del registry_guard
        registry.register_stub(_solver_meta("unit_stub", MethodStatus.COMING_SOON))
        response = client.post("/api/solve/unit_stub", json={})
        assert response.status_code == 409
        assert response.json()["code"] == "method_unavailable"

    def test_valid_solve_returns_full_contract(
        self, client: TestClient, registry_guard: None
    ) -> None:
        del registry_guard
        registry.register(_solver_meta())(_ok_solver)
        response = client.post("/api/solve/unit_solver", json={"x0": 1.25})
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["root"] == 1.25
        assert body["pseudocode"] == "1. Do the thing."
        assert "def _ok_solver" in body["python_source"]

    def test_invalid_input_is_400(
        self, client: TestClient, registry_guard: None
    ) -> None:
        del registry_guard
        registry.register(_solver_meta())(_ok_solver)
        response = client.post("/api/solve/unit_solver", json={"x0": "banana"})
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_malformed_json_is_friendly(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/unit_solver",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_timeout_maps_to_408(
        self, client: TestClient, registry_guard: None, monkeypatch: Any
    ) -> None:
        del registry_guard
        import time

        from app.api import solve as solve_module

        def _slow(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
            del inputs, limits
            time.sleep(1.0)
            return SolveResponse(method="unit_solver", status=SolveStatus.CONVERGED)

        monkeypatch.setattr(
            solve_module,
            "_limits",
            lambda: SolverLimits(timeout_seconds=0.05, max_iterations=10, max_matrix_size=3),
        )
        registry.register(_solver_meta("slow_solver"))(_slow)
        response = client.post("/api/solve/slow_solver", json={"x0": 1.0})
        assert response.status_code == 408
        assert response.json()["code"] == "timeout"
