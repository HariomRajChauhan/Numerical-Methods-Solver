"""Tests for the Chapter 4 Romberg integration solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy import integrate

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.parser import make_function, parse_expression
from app.core.validation import validate_inputs
from app.solvers.ch4_diff_integration.romberg import META, _trapezoid_rows, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PI = math.pi


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "sin(x)",
        "a": 0.0,
        "b": PI,
        "tolerance": 1e-8,
        "max_levels": 6,
        "decimal_precision": 8,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestRombergValues:
    def test_known_sine_value(self) -> None:
        response = run(function="sin(x)", tolerance=1e-8)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(2.0, abs=1e-6)

    def test_matches_scipy_romb_on_samples(self) -> None:
        f = make_function(parse_expression("sin(x)", ("x",)), ("x",), strict=False)
        _rows, table, _conv = _trapezoid_rows(f, 0.0, PI, 8, 0.0)
        for level in range(8):
            n = 2**level
            xs = np.linspace(0.0, PI, n + 1)
            expected = float(integrate.romb(np.sin(xs), dx=PI / n))
            assert table[level][level] == pytest.approx(expected, rel=1e-12)

    def test_first_extrapolation_is_simpson(self) -> None:
        _rows, table, _conv = _trapezoid_rows(
            make_function(parse_expression("sin(x)", ("x",)), ("x",), strict=False),
            0.0,
            PI,
            4,
            0.0,
        )
        from app.solvers.ch4_diff_integration.simpson_13 import solve as simpson13

        expected = simpson13(
            {
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": PI,
                "step_mode": "intervals",
                "n": 2,
            },
            LIMITS,
        ).result["value"]
        assert table[1][1] == pytest.approx(expected, rel=1e-12)

    def test_smooth_rational(self) -> None:
        response = run(function="1/(1+x^2)", a=0.0, b=1.0, tolerance=1e-10, max_levels=7)
        assert response.result["value"] == pytest.approx(PI / 4.0, abs=1e-10)

    def test_polynomial(self) -> None:
        response = run(function="x^3", a=0.0, b=1.0, tolerance=1e-12, max_levels=5)
        assert response.result["value"] == pytest.approx(0.25, abs=1e-12)


class TestRombergTablesAndConvergence:
    def test_trapezoid_estimates_table(self) -> None:
        response = run(max_levels=5, tolerance=1e-16)
        table = next(t for t in response.tables if t.title.startswith("Trapezoidal estimates"))
        assert [row[3] for row in table.rows] == [2, 1, 2, 4, 8]

    def test_triangular_table_shape(self) -> None:
        response = run(max_levels=5, tolerance=1e-16)
        table = next(t for t in response.tables if "triangular" in t.title)
        assert len(table.rows) == 5
        assert len(table.columns) == 6
        assert table.rows[0][1] != ""
        assert table.rows[0][2] == ""

    def test_diagnostics_table(self) -> None:
        response = run(max_levels=5, tolerance=1e-16)
        table = next(t for t in response.tables if t.title.startswith("Diagonal convergence"))
        assert table.rows[-1][-1] in {"continue", "stopped"}

    def test_converged_stops_early(self) -> None:
        response = run(tolerance=1e-6, max_levels=8)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["levels"] < 8

    def test_max_iter_when_tolerance_unreachable(self) -> None:
        response = run(function="sin(x)", tolerance=1e-16, max_levels=2)
        assert response.status == SolveStatus.MAX_ITER
        assert any("not reached" in warning for warning in response.warnings)
        assert response.result["value"] is not None

    def test_plot_has_two_subplots(self) -> None:
        response = run()
        assert response.plot.layout["grid"]["columns"] == 2
        names = [trace["name"] for trace in response.plot.traces]
        assert "Diagonal R(i,i)" in names


class TestRombergEdges:
    def test_swapped_limits(self) -> None:
        normal = run(a=0.0, b=PI)
        swapped = run(a=PI, b=0.0)
        assert swapped.result["value"] == pytest.approx(normal.result["value"], rel=1e-12)
        assert any("swapped" in warning for warning in swapped.warnings)

    def test_equal_limits_give_zero(self) -> None:
        response = run(a=2.0, b=2.0)
        assert response.result["value"] == 0.0

    def test_singular_integrand_fails(self) -> None:
        response = run(function="1/x", a=-1.0, b=1.0)
        assert response.status == SolveStatus.FAILED

    def test_missing_function_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(function="")


class TestRombergSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED


class TestRombergApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "sin(x)",
        "a": 0.0,
        "b": 3.141592653589793,
        "tolerance": 1e-8,
        "max_levels": 6,
        "decimal_precision": 8,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/romberg", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(2.0, abs=1e-6)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/romberg?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "romberg")
        assert method["status"] == "available"
