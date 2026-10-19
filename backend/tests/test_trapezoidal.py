"""Tests for the Chapter 4 trapezoidal rule solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy import integrate

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch4_diff_integration._quadrature import QUAD_POINTS
from app.solvers.ch4_diff_integration.trapezoidal import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PI = math.pi

FUNCTIONS: dict[str, Any] = {
    "sin(x)": np.sin,
    "x^2": lambda values: np.asarray(values) ** 2,
    "exp(x)": np.exp,
}


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "source": "function",
        "function": "sin(x)",
        "a": 0.0,
        "b": PI,
        "step_mode": "intervals",
        "n": 4,
        "show_convergence": False,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def sine_points(n: int, a: float = 0.0, b: float = PI) -> list[list[float]]:
    return [[a + (b - a) * i / n, math.sin(a + (b - a) * i / n)] for i in range(n + 1)]


class TestTrapezoidalValues:
    def test_known_sine_value(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(1.8961188979370398, rel=1e-12)

    def test_matches_scipy(self) -> None:
        for n in (2, 4, 8, 16):
            xs = np.linspace(0.0, PI, n + 1)
            ys = np.sin(xs)
            expected = float(integrate.trapezoid(ys, xs))
            response = run(n=n)
            assert response.result["value"] == pytest.approx(expected, rel=1e-12)

    def test_quadratic_is_linear_rule(self) -> None:
        response = run(function="x^2", a=0.0, b=1.0, n=2)
        assert response.result["value"] == pytest.approx(0.375, rel=1e-12)
        assert response.result["exact_value"] == pytest.approx(1.0 / 3.0, rel=1e-12)
        assert response.result["absolute_error"] == pytest.approx(
            abs(1.0 / 3.0 - 0.375), rel=1e-12
        )

    def test_error_bound_matches_for_quadratic(self) -> None:
        response = run(function="x^2", a=0.0, b=1.0, n=2)
        assert response.result["error_bound"] == pytest.approx(
            response.result["absolute_error"], rel=1e-6
        )

    def test_table_matches_function_mode(self) -> None:
        function_response = run(n=4)
        table_response = run(source="table", points=sine_points(4))
        assert table_response.result["value"] == pytest.approx(
            function_response.result["value"], rel=1e-9
        )

    def test_table_of_quadratic(self) -> None:
        response = run(source="table", points=[list(point) for point in QUAD_POINTS])
        assert response.result["value"] == pytest.approx(0.3379629629629629, rel=1e-12)
        assert response.result["exact_value"] is None


class TestTrapezoidalEdges:
    def test_swapped_limits(self) -> None:
        normal = run(n=4)
        swapped = run(a=PI, b=0.0, n=4)
        assert swapped.status == SolveStatus.CONVERGED
        assert swapped.result["a"] == pytest.approx(0.0)
        assert swapped.result["b"] == pytest.approx(PI)
        assert swapped.result["value"] == pytest.approx(normal.result["value"], rel=1e-12)
        assert any("swapped" in warning for warning in swapped.warnings)

    def test_equal_limits_give_zero(self) -> None:
        response = run(a=1.5, b=1.5, n=10)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == 0.0
        assert response.result["exact_value"] == 0.0

    def test_step_mode_resolves_n(self) -> None:
        response = run(step_mode="step", h=PI / 4.0)
        assert response.result["n"] == 4
        assert response.result["value"] == pytest.approx(1.8961188979370398, rel=1e-12)

    def test_missing_function_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(function="")

    def test_nonpositive_step_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(step_mode="step", h=0.0)


class TestTrapezoidalTablesAndPlot:
    def test_evaluation_table(self) -> None:
        response = run(n=4)
        table = next(t for t in response.tables if t.title.startswith("Function values"))
        assert len(table.rows) == 5
        assert table.columns == ["i", "x_i", "f(x_i)", "w_i", "w_i f(x_i)"]

    def test_summary_table(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title == "Result summary")
        labels = [row[0] for row in table.rows]
        assert "Exact value (SymPy)" in labels
        assert "Error bound (estimate)" in labels

    def test_plot_traces(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "Trapezoidal rule pieces" in names
        assert "f(x)" in names
        assert "Nodes f(x_i)" in names

    def test_result_step_last(self) -> None:
        response = run()
        assert response.steps[-1].title == "Result"


class TestTrapezoidalConvergence:
    def test_convergence_table(self) -> None:
        response = run(show_convergence=True)
        table = next(t for t in response.tables if t.title == "Convergence of the error")
        assert [row[0] for row in table.rows] == [4, 8, 16, 32, 64]

    def test_error_decreases_second_order(self) -> None:
        response = run(show_convergence=True)
        table = next(t for t in response.tables if t.title == "Convergence of the error")
        errors = [row[2] for row in table.rows]
        assert all(errors[i] > errors[i + 1] for i in range(len(errors) - 1))
        assert response.result["value"] is not None

    def test_reference_slope_trace(self) -> None:
        response = run(show_convergence=True)
        names = [trace["name"] for trace in response.plot.traces]
        assert "Error vs n" in names
        assert "slope 2" in names


class TestTrapezoidalFailures:
    def test_singular_integrand_fails(self) -> None:
        response = run(function="1/x", a=-1.0, b=1.0, n=4)
        assert response.status == SolveStatus.FAILED
        assert any("not finite" in warning for warning in response.warnings)

    def test_uneven_table_fails(self) -> None:
        response = run(source="table", points=[[0.0, 0.0], [1.0, 1.0], [3.0, 9.0]])
        assert response.status == SolveStatus.FAILED
        assert any("equally spaced" in warning for warning in response.warnings)

    def test_too_few_points_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(source="table", points=[[0.0, 0.0]])


class TestTrapezoidalSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED


class TestTrapezoidalApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "source": "function",
        "function": "sin(x)",
        "a": 0.0,
        "b": 3.141592653589793,
        "step_mode": "intervals",
        "n": 4,
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/trapezoidal", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method",
            "status",
            "result",
            "steps",
            "tables",
            "plot",
            "errors",
            "warnings",
            "pseudocode",
            "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(1.8961188979370398, rel=1e-9)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(
                f"/api/export/trapezoidal?format={fmt}", json=self.PAYLOAD
            )
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "trapezoidal")
        assert method["status"] == "available"
