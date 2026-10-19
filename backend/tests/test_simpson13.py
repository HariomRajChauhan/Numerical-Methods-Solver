"""Tests for the Chapter 4 Simpson's 1/3 rule solver."""

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
from app.solvers.ch4_diff_integration.simpson_13 import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PI = math.pi


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


class TestSimpson13Values:
    def test_known_sine_value(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(2.0045597549844207, rel=1e-12)

    def test_matches_scipy(self) -> None:
        for n in (2, 4, 8, 16):
            xs = np.linspace(0.0, PI, n + 1)
            ys = np.sin(xs)
            expected = float(integrate.simpson(ys, x=xs))
            response = run(n=n)
            assert response.result["value"] == pytest.approx(expected, rel=1e-10)

    def test_exact_for_quadratic(self) -> None:
        response = run(function="x^2", a=0.0, b=1.0, n=2)
        assert response.result["value"] == pytest.approx(1.0 / 3.0, rel=1e-12)
        assert response.result["absolute_error"] == pytest.approx(0.0, abs=1e-12)

    def test_exact_for_cubic(self) -> None:
        response = run(function="x^3", a=0.0, b=1.0, n=2)
        assert response.result["value"] == pytest.approx(0.25, rel=1e-12)

    def test_table_of_quadratic(self) -> None:
        response = run(source="table", points=[list(point) for point in QUAD_POINTS])
        assert response.result["value"] == pytest.approx(1.0 / 3.0, rel=1e-12)


class TestSimpson13Edges:
    def test_odd_n_fails_with_suggestion(self) -> None:
        response = run(n=3)
        assert response.status == SolveStatus.FAILED
        message = " ".join(response.warnings)
        assert "even" in message
        assert "n = 4" in message

    def test_odd_one_fails(self) -> None:
        response = run(n=1)
        assert response.status == SolveStatus.FAILED

    def test_swapped_limits(self) -> None:
        normal = run(n=4)
        swapped = run(a=PI, b=0.0, n=4)
        assert swapped.result["value"] == pytest.approx(normal.result["value"], rel=1e-12)
        assert any("swapped" in warning for warning in swapped.warnings)

    def test_equal_limits_give_zero(self) -> None:
        response = run(a=2.0, b=2.0, n=4)
        assert response.result["value"] == 0.0

    def test_step_mode_resolves_n(self) -> None:
        response = run(step_mode="step", h=PI / 8.0)
        interval_response = run(n=8)
        assert response.result["n"] == 8
        assert response.result["value"] == pytest.approx(
            interval_response.result["value"], rel=1e-12
        )


class TestSimpson13TablesAndPlot:
    def test_evaluation_table(self) -> None:
        response = run(n=4)
        table = next(t for t in response.tables if t.title.startswith("Function values"))
        assert len(table.rows) == 5

    def test_plot_uses_rule_name(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "Simpson's 1/3 rule pieces" in names

    def test_result_step_last(self) -> None:
        response = run()
        assert response.steps[-1].title == "Result"


class TestSimpson13Convergence:
    def test_convergence_table(self) -> None:
        response = run(show_convergence=True)
        table = next(t for t in response.tables if t.title == "Convergence of the error")
        assert [row[0] for row in table.rows] == [4, 8, 16, 32, 64]

    def test_fourth_order_slope(self) -> None:
        response = run(show_convergence=True)
        names = [trace["name"] for trace in response.plot.traces]
        assert "slope 4" in names


class TestSimpson13Failures:
    def test_singular_integrand_fails(self) -> None:
        response = run(function="1/x", a=-1.0, b=1.0, n=4)
        assert response.status == SolveStatus.FAILED

    def test_uneven_table_fails(self) -> None:
        response = run(source="table", points=[[0.0, 0.0], [1.0, 1.0], [3.0, 9.0]])
        assert response.status == SolveStatus.FAILED

    def test_missing_function_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(function="")


class TestSimpson13Schema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED


class TestSimpson13Api:
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
        response = client.post("/api/solve/simpson_13", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(2.0045597549844207, rel=1e-9)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/simpson_13?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "simpson_13")
        assert method["status"] == "available"
