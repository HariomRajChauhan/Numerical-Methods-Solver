"""Tests for the Chapter 4 general Newton-Cotes quadrature solver."""

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
from app.solvers.ch4_diff_integration.boole import solve as boole_solve
from app.solvers.ch4_diff_integration.newton_cotes import META, solve
from app.solvers.ch4_diff_integration.simpson_13 import solve as simpson13_solve
from app.solvers.ch4_diff_integration.simpson_38 import solve as simpson38_solve
from app.solvers.ch4_diff_integration.trapezoidal import solve as trapezoidal_solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PI = math.pi


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "source": "function",
        "function": "sin(x)",
        "a": 0.0,
        "b": PI,
        "n": 4,
        "panels": 1,
        "compare": False,
        "show_convergence": False,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestNewtonCotesReproducesClassical:
    def test_n1_matches_trapezoidal(self) -> None:
        general = run(function="sin(x)", n=1, panels=6)
        classical = trapezoidal_solve(
            {
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": PI,
                "step_mode": "intervals",
                "n": 6,
            },
            LIMITS,
        )
        assert general.result["value"] == pytest.approx(classical.result["value"], rel=1e-12)
        assert any("Trapezoidal rule" in warning for warning in general.warnings)

    def test_n2_matches_simpson13(self) -> None:
        general = run(function="sin(x)", n=2, panels=3)
        classical = simpson13_solve(
            {
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": PI,
                "step_mode": "intervals",
                "n": 6,
            },
            LIMITS,
        )
        assert general.result["value"] == pytest.approx(classical.result["value"], rel=1e-12)
        assert any("Simpson's 1/3 rule" in warning for warning in general.warnings)

    def test_n3_matches_simpson38(self) -> None:
        general = run(function="sin(x)", n=3, panels=2)
        classical = simpson38_solve(
            {
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": PI,
                "step_mode": "intervals",
                "n": 6,
            },
            LIMITS,
        )
        assert general.result["value"] == pytest.approx(classical.result["value"], rel=1e-12)
        assert any("Simpson's 3/8 rule" in warning for warning in general.warnings)

    def test_n4_matches_boole(self) -> None:
        general = run(function="sin(x)", n=4, panels=1)
        classical = boole_solve(
            {
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": PI,
                "step_mode": "intervals",
                "n": 4,
            },
            LIMITS,
        )
        assert general.result["value"] == pytest.approx(classical.result["value"], rel=1e-12)
        assert any("Boole's rule" in warning for warning in general.warnings)


class TestNewtonCotesValues:
    def test_n2_single_panel_matches_scipy(self) -> None:
        expected = float(integrate.quad(np.sin, 0.0, PI)[0])
        response = run(function="sin(x)", n=2, panels=2)
        assert response.result["value"] == pytest.approx(expected, abs=6e-3)

    def test_composite_panels_of_quadratic(self) -> None:
        response = run(function="x^2", a=0.0, b=1.0, n=2, panels=5)
        assert response.result["value"] == pytest.approx(1.0 / 3.0, rel=1e-12)
        assert response.result["panels"] == 5
        assert response.result["n"] == 10

    def test_n5_exact_for_quintic(self) -> None:
        response = run(function="x^5", a=0.0, b=1.0, n=5, panels=1)
        assert response.result["value"] == pytest.approx(1.0 / 6.0, rel=1e-12)

    def test_n8_exact_for_degree_eight(self) -> None:
        response = run(function="x^8", a=0.0, b=1.0, n=8, panels=1)
        assert response.result["value"] == pytest.approx(1.0 / 9.0, rel=1e-12)

    def test_table_mode(self) -> None:
        response = run(source="table", points=[list(point) for point in QUAD_POINTS], n=6, panels=1)
        assert response.result["value"] == pytest.approx(1.0 / 3.0, rel=1e-12)


class TestNewtonCotesCotesNumbers:
    def test_cotes_table_n4(self) -> None:
        response = run(n=4, panels=1)
        table = next(t for t in response.tables if t.title.startswith("Cotes numbers"))
        assert [row[1] for row in table.rows] == [
            r"\frac{14}{45}",
            r"\frac{64}{45}",
            r"\frac{8}{15}",
            r"\frac{64}{45}",
            r"\frac{14}{45}",
        ]

    def test_cotes_numbers_sum_to_panel_size(self) -> None:
        response = run(n=5, panels=1)
        assert response.result["cotes_latex"]
        assert response.result["panel_intervals"] == 5

    def test_negative_weight_warning_for_n8(self) -> None:
        response = run(function="exp(x)", a=0.0, b=1.0, n=8, panels=1)
        assert any("negative Cotes numbers" in warning for warning in response.warnings)

    def test_no_negative_weight_warning_for_small_n(self) -> None:
        response = run(function="exp(x)", a=0.0, b=1.0, n=4, panels=1)
        assert not any("negative Cotes numbers" in warning for warning in response.warnings)


class TestNewtonCotesEdges:
    def test_swapped_limits(self) -> None:
        normal = run(function="sin(x)", a=0.0, b=PI)
        swapped = run(function="sin(x)", a=PI, b=0.0)
        assert swapped.result["value"] == pytest.approx(normal.result["value"], rel=1e-12)
        assert any("swapped" in warning for warning in swapped.warnings)

    def test_equal_limits_give_zero(self) -> None:
        response = run(function="sin(x)", a=2.0, b=2.0, n=4, panels=1)
        assert response.result["value"] == 0.0

    def test_table_not_divisible_fails(self) -> None:
        response = run(source="table", points=[list(point) for point in QUAD_POINTS], n=5, panels=1)
        assert response.status == SolveStatus.FAILED
        assert "n = 6" in " ".join(response.warnings)

    def test_missing_function_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(function="")


class TestNewtonCotesPlotAndSteps:
    def test_area_plot_name(self) -> None:
        response = run(n=4, panels=1)
        names = [trace["name"] for trace in response.plot.traces]
        assert any("Newton-Cotes" in name for name in names)

    def test_result_step_last(self) -> None:
        response = run(n=4, panels=1)
        assert response.steps[-1].title == "Result"

    def test_node_table_rows(self) -> None:
        response = run(n=2, panels=3)
        table = next(t for t in response.tables if t.title.startswith("Nodes"))
        assert len(table.rows) == 7


class TestNewtonCotesComparison:
    def test_compare_lists_valid_rules(self) -> None:
        response = run(function="sin(x)", n=4, panels=1, compare=True)
        table = next(t for t in response.tables if t.title.startswith("Comparison"))
        methods = [row[0] for row in table.rows]
        assert methods == ["Trapezoidal rule", "Simpson's 1/3 rule", "Boole's rule"]

    def test_compare_overlay_plot(self) -> None:
        response = run(function="sin(x)", n=12, panels=1, compare=True)
        assert "Comparison of quadrature rules" in response.plot.layout["title"]["text"]
        names = [trace["name"] for trace in response.plot.traces]
        assert "Weddle's rule" in names


class TestNewtonCotesConvergence:
    def test_convergence_table(self) -> None:
        response = run(function="sin(x)", n=4, panels=1, show_convergence=True)
        table = next(t for t in response.tables if t.title == "Convergence of the error")
        assert [row[0] for row in table.rows] == [4, 8, 16, 32, 64]

    def test_reference_slope_trace(self) -> None:
        response = run(function="sin(x)", n=4, panels=1, show_convergence=True)
        names = [trace["name"] for trace in response.plot.traces]
        assert "slope 6" in names

    def test_compare_and_convergence_warns(self) -> None:
        response = run(function="sin(x)", n=4, panels=1, compare=True, show_convergence=True)
        assert any("both requested" in warning for warning in response.warnings)


class TestNewtonCotesFailures:
    def test_singular_integrand_fails(self) -> None:
        response = run(function="1/x", a=-1.0, b=1.0, n=4, panels=1)
        assert response.status == SolveStatus.FAILED

    def test_uneven_table_fails(self) -> None:
        response = run(
            source="table",
            points=[[0.0, 0.0], [1.0, 1.0], [2.0, 4.0], [4.0, 16.0]],
            n=3,
            panels=1,
        )
        assert response.status == SolveStatus.FAILED


class TestNewtonCotesSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED


class TestNewtonCotesApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "source": "function",
        "function": "sin(x)",
        "a": 0.0,
        "b": 3.141592653589793,
        "n": 4,
        "panels": 1,
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/newton_cotes", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(1.998570731823836, rel=1e-9)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/newton_cotes?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "newton_cotes")
        assert method["status"] == "available"
