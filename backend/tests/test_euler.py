"""Tests for the Chapter 5 Euler solver."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from scipy.integrate import solve_ivp

from app.core.errors import ExpressionError, InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch5_ode.euler import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.2,
        "step_mode": "step",
        "h": 0.1,
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestEulerValues:
    def test_first_two_steps(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["y_end"] == pytest.approx(1.22, abs=1e-12)
        table = next(t for t in response.tables if t.title == "Numerical solution")
        assert table.rows[1][2] == "1.100000"
        assert table.rows[2][2] == "1.220000"

    def test_exact_error(self) -> None:
        response = run()
        exact = 2.0 * pow(2.718281828459045, 0.2) - 0.2 - 1.0
        assert response.result["exact_value"] == pytest.approx(exact, rel=1e-9)
        assert response.result["absolute_error"] == pytest.approx(abs(1.22 - exact), rel=1e-9)

    def test_matches_scipy_solve_ivp(self) -> None:
        expected = float(
            solve_ivp(lambda t, s: [t + s[0]], [0.0, 1.0], [1.0], rtol=1e-12, atol=1e-14).y[0, -1]
        )
        response = run(x_end=1.0, h=0.001)
        assert response.result["y_end"] == pytest.approx(expected, abs=5e-3)

    def test_backward_integration(self) -> None:
        backward = run(x0=0.2, x_end=0.0)
        assert backward.status == SolveStatus.CONVERGED
        assert any("reversed" in warning for warning in backward.warnings)
        assert backward.result["y_end"] == pytest.approx(0.782, abs=1e-12)

    def test_equal_endpoints_return_initial_value(self) -> None:
        response = run(x_end=0.0)
        assert response.result["y_end"] == 1.0
        assert response.result["steps"] == 0

    def test_target_values(self) -> None:
        response = run(x_end=1.0, h=0.1, targets=[0.3, 0.7])
        assert response.result["target_values"] == pytest.approx([1.362, 2.1974342], abs=1e-6)


class TestEulerInstabilityAndDivergence:
    def test_unstable_step_warning(self) -> None:
        response = run(function="-20*y", x_end=1.0, h=0.2, exact_solution="exp(-20*x)")
        assert response.status == SolveStatus.CONVERGED
        assert any("unstable" in warning for warning in response.warnings)
        table = next(t for t in response.tables if t.title == "Numerical solution")
        ys = [float(row[2]) for row in table.rows[1:]]
        assert abs(ys[-1]) > abs(ys[0])
        assert any(y > 0 for y in ys) and any(y < 0 for y in ys)

    def test_quadratic_blow_up_diverges(self) -> None:
        response = run(function="y^2", x_end=2.0, h=0.1, exact_solution=None)
        assert response.status == SolveStatus.DIVERGED
        assert response.result["diverged_at_step"] < 20
        assert any("diverged" in warning.lower() for warning in response.warnings)

    def test_step_study_estimates_order_one(self) -> None:
        response = run(x_end=1.0, h=0.25, step_study=True)
        orders = next(t for t in response.tables if t.title == "Observed order of accuracy")
        order = float(orders.rows[0][1])
        assert order == pytest.approx(1.0, abs=0.2)


class TestEulerEdges:
    def test_zero_step_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(h=0.0)

    def test_unparseable_function_raises(self) -> None:
        with pytest.raises(ExpressionError):
            run(function="x +")

    def test_validation_accepts_two_variables(self) -> None:
        cleaned = validate_inputs(META, {"function": "x + y", "x0": 0, "y0": 1, "x_end": 1}, LIMITS)
        assert cleaned["function"] == "x + y"


class TestEulerSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            assert validate_inputs(META, example.inputs, LIMITS)

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status in {SolveStatus.CONVERGED, SolveStatus.DIVERGED}


class TestEulerApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.2,
        "step_mode": "step",
        "h": 0.1,
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/euler", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["y_end"] == pytest.approx(1.22, abs=1e-12)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/euler?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "euler")
        assert method["status"] == "available"
