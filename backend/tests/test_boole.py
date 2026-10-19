"""Tests for the Chapter 4 Boole's rule solver."""

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
from app.solvers.ch4_diff_integration.boole import META, solve

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
        "compare": False,
        "show_convergence": False,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def composite_reference(function: Any, a: float, b: float, n: int) -> float:
    h = (b - a) / n
    xs = np.linspace(a, b, n + 1)
    ys = function(xs)
    weights = np.array([7.0, 32.0, 12.0, 32.0, 7.0])
    total = 0.0
    for start in range(0, n, 4):
        total += float(np.sum(weights * ys[start : start + 5]))
    return float(2.0 * h / 45.0 * total)


class TestBooleValues:
    def test_known_sine_value(self) -> None:
        response = run(function="sin(x)", n=4)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(1.998570731823836, rel=1e-9)

    def test_matches_composite_reference(self) -> None:
        for n in (4, 8, 12):
            expected = composite_reference(np.sin, 0.0, PI, n)
            response = run(function="sin(x)", n=n)
            assert response.result["value"] == pytest.approx(expected, rel=1e-12)

    def test_exact_for_quartic(self) -> None:
        response = run(function="x^4", a=0.0, b=1.0, n=4)
        assert response.result["value"] == pytest.approx(0.2, rel=1e-12)

    def test_exact_for_quintic(self) -> None:
        response = run(function="x^5", a=0.0, b=1.0, n=4)
        assert response.result["value"] == pytest.approx(1.0 / 6.0, rel=1e-12)

    def test_not_exact_for_sextic(self) -> None:
        response = run(function="x^6", a=0.0, b=1.0, n=4)
        expected = float(integrate.quad(lambda x: x**6, 0.0, 1.0)[0])
        assert response.result["value"] == pytest.approx(expected, abs=5e-3)
        assert response.result["value"] != pytest.approx(expected, abs=1e-6)

    def test_matches_scipy_for_exp(self) -> None:
        expected = float(integrate.quad(np.exp, 0.0, 1.0)[0])
        response = run(function="exp(x)", a=0.0, b=1.0, n=8)
        assert response.result["value"] == pytest.approx(expected, abs=1e-6)

    def test_table_of_quartic(self) -> None:
        points = [[i / 4.0, (i / 4.0) ** 4] for i in range(5)]
        response = run(source="table", points=points)
        assert response.result["value"] == pytest.approx(0.2, rel=1e-12)


class TestBooleEdges:
    def test_non_multiple_of_four_fails(self) -> None:
        response = run(n=6)
        assert response.status == SolveStatus.FAILED
        message = " ".join(response.warnings)
        assert "multiple of 4" in message
        assert "n = 8" in message

    def test_suggestion_includes_lower_value(self) -> None:
        response = run(n=5)
        message = " ".join(response.warnings)
        assert "n = 4" in message

    def test_swapped_limits(self) -> None:
        normal = run(a=0.0, b=PI)
        swapped = run(a=PI, b=0.0)
        assert swapped.result["value"] == pytest.approx(normal.result["value"], rel=1e-12)
        assert any("swapped" in warning for warning in swapped.warnings)

    def test_equal_limits_give_zero(self) -> None:
        response = run(a=2.0, b=2.0, n=4)
        assert response.result["value"] == 0.0

    def test_step_mode_resolves_n(self) -> None:
        response = run(function="x^4", a=0.0, b=1.0, step_mode="step", h=0.25)
        assert response.result["n"] == 4
        assert response.result["value"] == pytest.approx(0.2, rel=1e-12)


class TestBooleTablesAndPlot:
    def test_node_table(self) -> None:
        response = run(n=4)
        table = next(t for t in response.tables if t.title.startswith("Nodes"))
        assert len(table.rows) == 5

    def test_cotes_table(self) -> None:
        response = run(n=4)
        table = next(t for t in response.tables if t.title.startswith("Cotes numbers"))
        assert [row[1] for row in table.rows] == [
            r"\frac{14}{45}",
            r"\frac{64}{45}",
            r"\frac{8}{15}",
            r"\frac{64}{45}",
            r"\frac{14}{45}",
        ]

    def test_plot_uses_rule_name(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "Boole's rule pieces" in names

    def test_result_step_last(self) -> None:
        response = run()
        assert response.steps[-1].title == "Result"


class TestBooleComparison:
    def test_compare_table_lists_valid_rules(self) -> None:
        response = run(function="sin(x)", n=12, compare=True)
        table = next(t for t in response.tables if t.title.startswith("Comparison"))
        methods = [row[0] for row in table.rows]
        assert methods == [
            "Trapezoidal rule",
            "Simpson's 1/3 rule",
            "Simpson's 3/8 rule",
            "Boole's rule",
            "Weddle's rule",
        ]

    def test_compare_table_excludes_invalid_rules(self) -> None:
        response = run(function="sin(x)", n=4, compare=True)
        table = next(t for t in response.tables if t.title.startswith("Comparison"))
        methods = [row[0] for row in table.rows]
        assert "Boole's rule" in methods
        assert "Weddle's rule" not in methods

    def test_compare_overlay_plot(self) -> None:
        response = run(function="sin(x)", n=12, compare=True)
        names = [trace["name"] for trace in response.plot.traces]
        assert "Comparison of quadrature rules on the same integral" in response.plot.layout[
            "title"
        ]["text"]
        assert "Weddle's rule" in names


class TestBooleConvergence:
    def test_convergence_table(self) -> None:
        response = run(show_convergence=True, n=4)
        table = next(t for t in response.tables if t.title == "Convergence of the error")
        assert [row[0] for row in table.rows] == [4, 8, 16, 32, 64]

    def test_reference_slope_trace(self) -> None:
        response = run(show_convergence=True, n=4)
        names = [trace["name"] for trace in response.plot.traces]
        assert "slope 6" in names


class TestBooleFailures:
    def test_singular_integrand_fails(self) -> None:
        response = run(function="1/x", a=-1.0, b=1.0, n=4)
        assert response.status == SolveStatus.FAILED

    def test_uneven_table_fails(self) -> None:
        response = run(source="table", points=[[0.0, 0.0], [1.0, 1.0], [2.0, 4.0], [4.0, 16.0]])
        assert response.status == SolveStatus.FAILED

    def test_missing_function_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(function="")


class TestBooleSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED


class TestBooleApi:
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
        response = client.post("/api/solve/boole", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(1.998570731823836, rel=1e-9)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/boole?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "boole")
        assert method["status"] == "available"
