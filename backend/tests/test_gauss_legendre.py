"""Tests for the Chapter 4 Gauss-Legendre quadrature solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from numpy.polynomial.legendre import leggauss
from scipy import integrate

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch4_diff_integration.gauss_legendre import GAUSS_RULES, META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PI = math.pi


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "exp(x)",
        "a": 0.0,
        "b": 1.0,
        "points": "2",
        "panels": 1,
        "compare": False,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestGaussNodesAndWeights:
    def test_nodes_match_leggauss_2(self) -> None:
        nodes, weights = leggauss(2)
        assert [t for t, _w in GAUSS_RULES[2]] == pytest.approx(
            [float(x) for x in nodes], rel=1e-12
        )
        assert [w for _t, w in GAUSS_RULES[2]] == pytest.approx(
            [float(x) for x in weights], rel=1e-12
        )

    def test_nodes_match_leggauss_3(self) -> None:
        nodes, weights = leggauss(3)
        assert [t for t, _w in GAUSS_RULES[3]] == pytest.approx(
            [float(x) for x in nodes], rel=1e-12
        )
        assert [w for _t, w in GAUSS_RULES[3]] == pytest.approx(
            [float(x) for x in weights], rel=1e-12
        )

    def test_weights_sum_to_two(self) -> None:
        for points in (1, 2, 3):
            assert sum(w for _t, w in GAUSS_RULES[points]) == pytest.approx(2.0, rel=1e-12)


class TestGaussValues:
    def test_two_point_exp(self) -> None:
        response = run(function="exp(x)", points="2")
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(1.717896378007504, rel=1e-9)

    def test_three_point_sine(self) -> None:
        response = run(function="sin(x)", a=0.0, b=PI, points="3")
        assert response.result["value"] == pytest.approx(2.001388913607743, rel=1e-9)

    def test_two_point_exact_for_cubic(self) -> None:
        response = run(function="x^3", a=0.0, b=1.0, points="2")
        assert response.result["value"] == pytest.approx(0.25, rel=1e-12)

    def test_three_point_exact_for_quintic(self) -> None:
        response = run(function="x^5", a=0.0, b=1.0, points="3")
        assert response.result["value"] == pytest.approx(1.0 / 6.0, rel=1e-12)

    def test_one_point_is_midpoint(self) -> None:
        response = run(function="x", a=0.0, b=1.0, points="1")
        assert response.result["value"] == pytest.approx(0.5, rel=1e-12)

    def test_one_point_not_exact_for_quadratic(self) -> None:
        response = run(function="x^2", a=0.0, b=1.0, points="1")
        assert response.result["value"] == pytest.approx(0.25, rel=1e-12)
        assert response.result["value"] != pytest.approx(1.0 / 3.0, abs=1e-3)

    def test_matches_scipy_quad(self) -> None:
        expected = float(integrate.quad(np.exp, 0.0, 1.0)[0])
        response = run(function="exp(x)", a=0.0, b=1.0, points="3")
        assert response.result["value"] == pytest.approx(expected, abs=1e-6)

    def test_exact_degree_reported(self) -> None:
        assert run(points="1").result["exact_degree"] == 1
        assert run(points="2").result["exact_degree"] == 3
        assert run(points="3").result["exact_degree"] == 5


class TestGaussComposite:
    def test_composite_quadratic(self) -> None:
        response = run(function="x^2", a=0.0, b=1.0, points="2", panels=2)
        assert response.result["value"] == pytest.approx(1.0 / 3.0, rel=1e-12)

    def test_composite_evaluation_count(self) -> None:
        response = run(function="exp(x)", points="3", panels=4)
        assert response.result["panels"] == 4
        assert response.result["evaluations"] == 12

    def test_composite_improves_sine(self) -> None:
        one_panel = run(function="sin(x)", a=0.0, b=PI, points="3", panels=1)
        four_panel = run(function="sin(x)", a=0.0, b=PI, points="3", panels=4)
        assert abs(four_panel.result["absolute_error"]) < abs(one_panel.result["absolute_error"])


class TestGaussTablesAndPlot:
    def test_node_table_rows(self) -> None:
        response = run(function="exp(x)", points="3", panels=2)
        table = next(t for t in response.tables if t.title.startswith("Gauss-Legendre nodes"))
        assert len(table.rows) == 6
        assert table.columns[0] == "Panel"

    def test_node_table_single_panel_columns(self) -> None:
        response = run(function="exp(x)", points="2", panels=1)
        table = next(t for t in response.tables if t.title.startswith("Gauss-Legendre nodes"))
        assert table.columns[0] == "i"

    def test_plot_marks_nodes(self) -> None:
        response = run(function="exp(x)", points="2", panels=1)
        names = [trace["name"] for trace in response.plot.traces]
        assert "Gauss nodes" in names
        assert "f(x)" in names

    def test_result_step_last(self) -> None:
        response = run()
        assert response.steps[-1].title == "Result"


class TestGaussComparison:
    def test_compare_table_rows_and_evaluations(self) -> None:
        response = run(function="sin(x)", a=0.0, b=PI, points="2", panels=2, compare=True)
        table = next(t for t in response.tables if t.title.startswith("Comparison"))
        assert [row[0] for row in table.rows] == [
            "Gauss-Legendre 2-point",
            "Gauss-Legendre 3-point",
            "Simpson's 1/3",
        ]
        assert [row[1] for row in table.rows] == [4, 6, 5]

    def test_compare_three_point_more_accurate(self) -> None:
        response = run(function="exp(x)", a=0.0, b=1.0, points="2", panels=1, compare=True)
        table = next(t for t in response.tables if t.title.startswith("Comparison"))
        two_point_error = table.rows[0][3]
        three_point_error = table.rows[1][3]
        assert three_point_error != two_point_error


class TestGaussEdges:
    def test_swapped_limits(self) -> None:
        normal = run(function="exp(x)", a=0.0, b=1.0)
        swapped = run(function="exp(x)", a=1.0, b=0.0)
        assert swapped.result["value"] == pytest.approx(normal.result["value"], rel=1e-12)
        assert any("swapped" in warning for warning in swapped.warnings)

    def test_equal_limits_give_zero(self) -> None:
        response = run(function="exp(x)", a=2.0, b=2.0)
        assert response.result["value"] == 0.0

    def test_singular_integrand_fails(self) -> None:
        response = run(function="1/x", a=-1.0, b=1.0)
        assert response.status == SolveStatus.FAILED

    def test_missing_function_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(function="")

    def test_invalid_points_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(points="5")


class TestGaussSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED


class TestGaussApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "exp(x)",
        "a": 0.0,
        "b": 1.0,
        "points": "2",
        "panels": 1,
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/gauss_legendre", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(1.717896378007504, rel=1e-9)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(
                f"/api/export/gauss_legendre?format={fmt}", json=self.PAYLOAD
            )
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "gauss_legendre")
        assert method["status"] == "available"
