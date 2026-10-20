"""Tests for the Chapter 5 second-order ODE Runge-Kutta solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from scipy.integrate import solve_ivp

from app.core.errors import ExpressionError, InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch5_ode.ode_second_order_rk import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "-y",
        "x0": 0.0,
        "y0": 1.0,
        "yp0": 0.0,
        "x_end": 1.0,
        "step_mode": "step",
        "h": 0.1,
        "y_exact": "cos(x)",
        "scheme": "rk4",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestSecondOrderValues:
    def test_harmonic_matches_cos(self) -> None:
        response = run(x_end=1.0, h=0.1)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["y_end"][0] == pytest.approx(math.cos(1.0), abs=1e-6)

    def test_derivative_component_is_y_prime(self) -> None:
        response = run(x_end=1.0, h=0.1)
        assert response.result["y_end"][1] == pytest.approx(-math.sin(1.0), abs=1e-6)

    def test_exact_derivative_column(self) -> None:
        response = run(x_end=1.0, h=0.1)
        table = next(t for t in response.tables if t.title == "Numerical solution")
        assert table.columns == ["step", "x", "y", "z", "y exact", "z exact", "|e| y", "|e| z"]

    def test_matches_scipy_solve_ivp(self) -> None:
        expected = solve_ivp(
            lambda t, s: [s[1], -s[0]], [0.0, 6.0], [1.0, 0.0], rtol=1e-12, atol=1e-14
        ).y[:, -1]
        response = run(x_end=6.0, h=0.1)
        assert response.result["y_end"][0] == pytest.approx(float(expected[0]), abs=1e-4)
        assert response.result["y_end"][1] == pytest.approx(float(expected[1]), abs=1e-4)

    def test_fourth_order_convergence(self) -> None:
        coarse = run(x_end=6.0, h=0.2).result["max_absolute_error"]
        fine = run(x_end=6.0, h=0.1).result["max_absolute_error"]
        assert coarse / fine == pytest.approx(16.0, rel=0.5)

    def test_forced_second_order_equation(self) -> None:
        response = run(function="z - y + x", y_exact=None, x_end=2.0, h=0.05)
        reference = solve_ivp(
            lambda t, s: [s[1], s[1] - s[0] + t], [0.0, 2.0], [1.0, 0.0], rtol=1e-11, atol=1e-13
        ).y[:, -1]
        assert response.result["y_end"][0] == pytest.approx(float(reference[0]), abs=1e-5)


class TestSecondOrderPlots:
    def test_phase_portrait_between_y_and_z(self) -> None:
        response = run()
        assert response.plot is not None
        assert any(trace.get("name", "").startswith("phase") for trace in response.plot.traces)

    def test_substitution_preamble_step(self) -> None:
        response = run()
        assert response.steps[0].title == "Reduce to a first-order system"
        assert "z = y'" in response.steps[0].latex


class TestSecondOrderStepStudy:
    def test_step_study_estimates_order_four(self) -> None:
        response = run(x_end=6.0, h=0.25, step_study=True)
        orders = next(t for t in response.tables if t.title == "Observed order of accuracy")
        assert float(orders.rows[-1][1]) == pytest.approx(4.0, abs=0.4)


class TestSecondOrderCompare:
    def test_compare_table_lists_three_schemes(self) -> None:
        response = run(x_end=1.0, h=0.25, compare=True)
        table = next(t for t in response.tables if t.title == "Scheme comparison")
        assert [row[0] for row in table.rows] == ["Euler", "RK2 (Heun)", "RK4"]


class TestSecondOrderEdges:
    def test_zero_step_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(h=0.0)

    def test_undefined_variable_raises(self) -> None:
        with pytest.raises(ExpressionError):
            run(function="-y + q")

    def test_backward_integration(self) -> None:
        response = run(x0=1.0, x_end=0.0, h=0.1)
        assert response.status == SolveStatus.CONVERGED
        assert any("Backward" in warning for warning in response.warnings)

    def test_equal_endpoints_return_initial_vector(self) -> None:
        response = run(x0=1.0, x_end=1.0)
        assert response.result["y_end"] == [1.0, 0.0]
        assert response.result["steps"] == 0

    def test_blow_up_diverges(self) -> None:
        response = run(function="y^3", y_exact=None, y0=1.0, yp0=1.0, x_end=5.0, h=0.1)
        assert response.status == SolveStatus.DIVERGED


class TestSecondOrderSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            assert validate_inputs(META, example.inputs, LIMITS)

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status in {SolveStatus.CONVERGED, SolveStatus.DIVERGED}

    def test_schema_has_no_redundant_system_fields(self) -> None:
        keys = {field.key for field in META.input_schema}
        assert {"function", "y0", "yp0", "y_exact"} <= keys
        assert "equations" not in keys
        assert "state_variables" not in keys


class TestSecondOrderApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "-y",
        "x0": 0.0,
        "y0": 1.0,
        "yp0": 0.0,
        "x_end": 1.0,
        "step_mode": "step",
        "h": 0.1,
        "y_exact": "cos(x)",
        "scheme": "rk4",
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/ode_second_order_rk", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["variables"] == ["y", "z"]
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/ode_second_order_rk?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "ode_second_order_rk")
        assert method["status"] == "available"
