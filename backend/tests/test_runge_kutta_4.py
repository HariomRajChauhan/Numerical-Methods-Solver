"""Tests for the Chapter 5 classic fourth-order Runge-Kutta solver."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from scipy.integrate import solve_ivp

from app.core.errors import ExpressionError, InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch5_ode.runge_kutta_4 import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.1,
        "step_mode": "step",
        "h": 0.1,
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestRK4Values:
    def test_first_step(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["y_end"] == pytest.approx(1.1103416666666668, abs=1e-12)

    def test_stage_values(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title == "Runge-Kutta stages")
        assert table.columns[:6] == ["step", "x", "y", "k1", "k2", "k3"]
        assert table.columns[6] == "k4"
        assert table.rows[1][3] == "1.000000"
        assert table.rows[1][4] == "1.100000"
        assert table.rows[1][5] == "1.105000"
        assert table.rows[1][6] == "1.210500"

    def test_matches_scipy_solve_ivp(self) -> None:
        expected = float(
            solve_ivp(lambda t, s: [t + s[0]], [0.0, 1.0], [1.0], rtol=1e-12, atol=1e-14).y[0, -1]
        )
        response = run(x_end=1.0, h=0.1)
        assert response.result["y_end"] == pytest.approx(expected, abs=1e-4)

    def test_fourth_order_convergence(self) -> None:
        error_coarse = run(x_end=1.0, h=0.2).result["absolute_error"]
        error_fine = run(x_end=1.0, h=0.1).result["absolute_error"]
        assert error_coarse / error_fine == pytest.approx(16.0, rel=0.35)

    def test_step_study_estimates_order_four(self) -> None:
        response = run(x_end=1.0, h=0.25, step_study=True)
        orders = next(t for t in response.tables if t.title == "Observed order of accuracy")
        assert float(orders.rows[-1][1]) == pytest.approx(4.0, abs=0.3)


class TestRK4Compare:
    def test_compare_table(self) -> None:
        response = run(x_end=1.0, h=0.25, compare=True)
        table = next(t for t in response.tables if t.title == "Method comparison")
        assert [row[0] for row in table.rows] == ["Euler", "RK2 (Heun)", "RK4"]
        assert [row[3] for row in table.rows] == [4, 8, 16]

    def test_compare_plot_overlays_three_methods(self) -> None:
        response = run(x_end=1.0, h=0.25, compare=True)
        assert response.plot is not None
        names = {trace["name"] for trace in response.plot.traces}
        assert {"Euler", "RK2 (Heun)", "RK4"} <= names
        assert response.plot.layout["yaxis2"]["type"] == "log"


class TestRK4Edges:
    def test_zero_step_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(h=0.0)

    def test_unparseable_function_raises(self) -> None:
        with pytest.raises(ExpressionError):
            run(function="x +")

    def test_backward_integration(self) -> None:
        response = run(x0=0.2, x_end=0.0)
        assert response.status == SolveStatus.CONVERGED
        assert any("reversed" in warning for warning in response.warnings)

    def test_equal_endpoints_return_initial_value(self) -> None:
        assert run(x_end=0.0).result["y_end"] == 1.0

    def test_quadratic_blow_up_diverges(self) -> None:
        response = run(function="y^2", x_end=2.0, h=0.1, exact_solution=None)
        assert response.status == SolveStatus.DIVERGED


class TestRK4Schema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            assert validate_inputs(META, example.inputs, LIMITS)

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status in {SolveStatus.CONVERGED, SolveStatus.DIVERGED}


class TestRK4Api:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.1,
        "step_mode": "step",
        "h": 0.1,
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/runge_kutta_4", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["y_end"] == pytest.approx(1.1103416666666668, abs=1e-12)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/runge_kutta_4?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "runge_kutta_4")
        assert method["status"] == "available"
