"""Tests for the Chapter 5 Taylor series solver."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from scipy.integrate import solve_ivp

from app.core.errors import ExpressionError, InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch5_ode import taylor_series
from app.solvers.ch5_ode.taylor_series import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.1,
        "step_mode": "step",
        "h": 0.1,
        "order": 3,
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestTaylorValues:
    def test_order_three_first_step(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["y_end"] == pytest.approx(1.1103333333333334, abs=1e-12)
        table = next(t for t in response.tables if t.title == "Numerical solution")
        assert table.rows[1][2] == "1.110333"

    def test_derivative_values(self) -> None:
        response = run()
        assert response.result["derivatives"] == ["x + y", "x + y + 1", "x + y + 1"]
        table = next(t for t in response.tables if t.title == "Taylor derivative values per step")
        assert table.rows[1][3:] == ["1.000000", "2.000000", "2.000000"]

    def test_higher_order_is_more_accurate(self) -> None:
        order3 = run(order=3).result["absolute_error"]
        order4 = run(order=4).result["absolute_error"]
        order5 = run(order=5).result["absolute_error"]
        assert order4 < order3
        assert order5 < order4

    def test_matches_scipy_solve_ivp(self) -> None:
        expected = float(
            solve_ivp(lambda t, s: [t + s[0]], [0.0, 1.0], [1.0], rtol=1e-12, atol=1e-14).y[0, -1]
        )
        response = run(x_end=1.0, h=0.05, order=6)
        assert response.result["y_end"] == pytest.approx(expected, abs=1e-6)

    def test_exact_solution_optional(self) -> None:
        response = run(exact_solution=None)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["exact_value"] is None
        assert response.result["reference_value"] is not None

    def test_backward_integration(self) -> None:
        response = run(x0=0.2, x_end=0.0, order=3)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["y_end"] == pytest.approx(0.8011913944444445, abs=1e-12)

    def test_equal_endpoints_return_initial_value(self) -> None:
        response = run(x_end=0.0)
        assert response.result["y_end"] == 1.0
        assert response.result["steps"] == 0

    def test_step_study_estimates_order(self) -> None:
        response = run(x_end=1.0, h=0.25, order=3, step_study=True)
        orders = next(t for t in response.tables if t.title == "Observed order of accuracy")
        assert float(orders.rows[0][1]) == pytest.approx(3.0, abs=0.3)


class TestTaylorEdges:
    def test_symbolic_budget_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(taylor_series, "MAX_SYMBOLIC_OPS", 0)
        response = run()
        assert response.status == SolveStatus.FAILED
        assert any("derivative" in warning.lower() for warning in response.warnings)

    def test_zero_step_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(h=0.0)

    def test_unparseable_function_raises(self) -> None:
        with pytest.raises(ExpressionError):
            run(function="x +")

    def test_order_out_of_range_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            validate_inputs(
                META, {"function": "x + y", "x0": 0, "y0": 1, "x_end": 1, "order": 9}, LIMITS
            )


class TestTaylorSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            assert validate_inputs(META, example.inputs, LIMITS)

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status in {SolveStatus.CONVERGED, SolveStatus.DIVERGED}

    def test_validation_accepts_two_variables(self) -> None:
        cleaned = validate_inputs(META, {"function": "x + y", "x0": 0, "y0": 1, "x_end": 1}, LIMITS)
        assert cleaned["function"] == "x + y"


class TestTaylorApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.1,
        "step_mode": "step",
        "h": 0.1,
        "order": 3,
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/taylor_series", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["y_end"] == pytest.approx(1.1103333333333334, abs=1e-12)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/taylor_series?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "taylor_series")
        assert method["status"] == "available"
