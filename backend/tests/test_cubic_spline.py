"""Tests for cubic-spline interpolation (natural and clamped boundary conditions)."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.interpolate import CubicSpline

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation._spline import (
    CLAMPED,
    NATURAL,
    build_system,
    derivative_value,
    derivative_value_interval,
    evaluate,
)
from app.solvers.ch3_interpolation.cubic_spline import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
EQUAL_XS = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
EQUAL_YS = np.array([0.0, 1.0, 4.0, 9.0, 16.0])
UNEVEN_XS = np.array([0.0, 1.0, 3.0, 4.0, 6.0])
UNEVEN_YS = np.array([0.0, 1.0, 27.0, 64.0, 216.0])


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [[float(x), float(y)] for x, y in zip(EQUAL_XS, EQUAL_YS, strict=True)],
        "boundary": NATURAL,
        "left_derivative": 0.0,
        "right_derivative": 0.0,
        "targets": [1.5],
        "derivatives": False,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _grid(xs: np.ndarray) -> np.ndarray:
    return np.linspace(float(xs[0]), float(xs[-1]), 73)


class TestCubicSplineValues:
    @pytest.mark.parametrize(("xs", "ys"), [(EQUAL_XS, EQUAL_YS), (UNEVEN_XS, UNEVEN_YS)])
    def test_natural_matches_scipy(self, xs: np.ndarray, ys: np.ndarray) -> None:
        spline = build_system(xs, ys, NATURAL)
        reference = CubicSpline(xs, ys, bc_type="natural")
        grid = _grid(xs)
        ours = np.array([evaluate(spline, float(x))[0] for x in grid])
        assert np.allclose(ours, reference(grid), atol=1e-10)
        assert np.allclose(spline.m, reference(xs, 2), atol=1e-10)

    @pytest.mark.parametrize(("xs", "ys"), [(EQUAL_XS, EQUAL_YS), (UNEVEN_XS, UNEVEN_YS)])
    def test_clamped_matches_scipy(self, xs: np.ndarray, ys: np.ndarray) -> None:
        left_slope, right_slope = 0.3, -0.7
        spline = build_system(xs, ys, CLAMPED, left_slope, right_slope)
        reference = CubicSpline(xs, ys, bc_type=((1, left_slope), (1, right_slope)))
        grid = _grid(xs)
        ours = np.array([evaluate(spline, float(x))[0] for x in grid])
        assert np.allclose(ours, reference(grid), atol=1e-10)
        assert np.allclose(spline.m, reference(xs, 2), atol=1e-10)

    def test_second_derivatives_match_scipy(self) -> None:
        spline = build_system(EQUAL_XS, EQUAL_YS, NATURAL)
        reference = CubicSpline(EQUAL_XS, EQUAL_YS, bc_type="natural")
        assert np.allclose(spline.m, reference(EQUAL_XS, 2), atol=1e-10)

    def test_continuity_at_interior_knots(self) -> None:
        spline = build_system(UNEVEN_XS, UNEVEN_YS, NATURAL)
        for k in range(1, len(UNEVEN_XS) - 1):
            knot = float(UNEVEN_XS[k])
            assert evaluate(spline, knot)[0] == pytest.approx(
                evaluate(spline, knot - 1e-12)[0], abs=1e-9
            )
            for order in (1, 2):
                left = derivative_value_interval(spline, k - 1, knot, order)
                right = derivative_value_interval(spline, k, knot, order)
                assert left == pytest.approx(right, abs=1e-8)

    def test_linear_data_is_reproduced(self) -> None:
        xs = np.array([0.0, 1.0, 2.0, 3.0])
        ys = 2.0 * xs + 1.0
        spline = build_system(xs, ys, NATURAL)
        assert np.allclose(spline.m, 0.0, atol=1e-12)
        assert evaluate(spline, 2.5)[0] == pytest.approx(6.0, abs=1e-10)

    def test_natural_boundary_second_derivatives_are_zero(self) -> None:
        spline = build_system(UNEVEN_XS, UNEVEN_YS, NATURAL)
        assert spline.m[0] == pytest.approx(0.0, abs=1e-12)
        assert spline.m[-1] == pytest.approx(0.0, abs=1e-12)

    def test_clamped_end_slopes_are_honoured(self) -> None:
        left_slope, right_slope = 1.5, -2.0
        spline = build_system(EQUAL_XS, EQUAL_YS, CLAMPED, left_slope, right_slope)
        assert derivative_value(spline, float(EQUAL_XS[0]), 1) == pytest.approx(left_slope, abs=1e-10)
        assert derivative_value(spline, float(EQUAL_XS[-1]), 1) == pytest.approx(right_slope, abs=1e-10)

    def test_clamped_parabola_is_exact(self) -> None:
        xs = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        ys = xs ** 2 + 1.0
        spline = build_system(xs, ys, CLAMPED, 2.0 * xs[0], 2.0 * xs[-1])
        assert evaluate(spline, 1.5)[0] == pytest.approx(1.5 ** 2 + 1.0, abs=1e-10)

    def test_thomas_solution_satisfies_the_system(self) -> None:
        spline = build_system(UNEVEN_XS, UNEVEN_YS, CLAMPED, 0.3, -0.7)
        size = len(spline.diag)
        matrix = np.zeros((size, size))
        for i in range(size):
            matrix[i, i] = spline.diag[i]
            if i > 0:
                matrix[i, i - 1] = spline.lower[i]
            if i < size - 1:
                matrix[i, i + 1] = spline.upper[i]
        assert np.allclose(matrix @ spline.m, spline.rhs, atol=1e-9)

    def test_coefficients_a_equal_y_values(self) -> None:
        spline = build_system(EQUAL_XS, EQUAL_YS, NATURAL)
        assert np.allclose(spline.a, EQUAL_YS[:-1])


class TestCubicSplineFailures:
    def test_too_few_points_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="At least 3"):
            run(points=[[0, 0], [1, 1]], targets=[])

    def test_duplicate_x_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="distinct"):
            run(points=[[0, 0], [0, 1], [2, 4]], targets=[])  # type: ignore[list-item]

    def test_too_few_points_is_bad_request(self, client: TestClient) -> None:
        payload = {"points": [[0, 0], [1, 1]], "boundary": NATURAL, "decimal_precision": 6}
        response = client.post("/api/solve/cubic_spline", json=payload)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_duplicate_x_is_bad_request(self, client: TestClient) -> None:
        payload = {
            "points": [[0, 0], [0, 1], [2, 4]],
            "boundary": NATURAL,
            "decimal_precision": 6,
        }
        response = client.post("/api/solve/cubic_spline", json=payload)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"


class TestCubicSplineExtrapolation:
    def test_outside_target_warns(self) -> None:
        response = run(targets=[5.0])
        assert any("extrapolation" in warning.lower() for warning in response.warnings)

    def test_inside_target_does_not_warn(self) -> None:
        response = run(targets=[2.5])
        assert not any("extrapolation" in warning.lower() for warning in response.warnings)

    def test_extrapolation_uses_the_end_cubic(self) -> None:
        response = run(targets=[5.0])
        spline = build_system(EQUAL_XS, EQUAL_YS, NATURAL)
        expected, index, outside = evaluate(spline, 5.0)
        assert index == spline.intervals - 1
        assert outside is True
        assert response.result["values"][0] == pytest.approx(expected, abs=1e-10)


class TestCubicSplineTables:
    def test_spacing_table_reports_h(self) -> None:
        response = run(points=[[float(x), float(y)] for x, y in zip(UNEVEN_XS, UNEVEN_YS, strict=True)])
        table = next(t for t in response.tables if t.title.startswith("Interval steps"))
        heights = [float(row[3]) for row in table.rows if row[3] != ""]
        assert heights == pytest.approx([1.0, 2.0, 1.0, 2.0])

    def test_system_table_has_one_row_per_node(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title.startswith("Tridiagonal system"))
        assert len(table.rows) == len(EQUAL_XS)

    def test_coefficients_table_has_one_row_per_interval(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title.startswith("Piecewise cubic coefficients"))
        assert len(table.rows) == len(EQUAL_XS) - 1

    def test_evaluation_table_names_the_interval(self) -> None:
        response = run(targets=[2.5])
        table = next(t for t in response.tables if t.title.startswith("Evaluations"))
        assert table.rows[0][1] == 2

    def test_second_derivatives_table_lists_m(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title == "Second derivatives M_i")
        assert len(table.rows) == len(EQUAL_XS)


class TestCubicSplineDerivativeToggle:
    def test_overlay_adds_derivative_traces(self) -> None:
        response = run(derivatives=True)
        names = [trace["name"] for trace in response.plot.traces]
        assert any(name.startswith("S'(x)") for name in names)
        assert any(name.startswith("S''(x)") for name in names)

    def test_without_toggle_only_pieces(self) -> None:
        response = run(derivatives=False)
        names = [trace["name"] for trace in response.plot.traces]
        assert not any("S'" in name for name in names)
        assert sum(1 for name in names if name.startswith("S_")) == len(EQUAL_XS) - 1

    def test_each_piece_is_a_separate_trace(self) -> None:
        response = run()
        pieces = [trace for trace in response.plot.traces if trace["name"].startswith("S_")]
        assert len(pieces) == len(EQUAL_XS) - 1


class TestCubicSplineApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [[float(x), float(y)] for x, y in zip(UNEVEN_XS, UNEVEN_YS, strict=True)],
        "boundary": NATURAL,
        "left_derivative": 0.0,
        "right_derivative": 0.0,
        "targets": [2.0],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/cubic_spline", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        reference = CubicSpline(UNEVEN_XS, UNEVEN_YS, bc_type="natural")
        assert body["result"]["values"][0] == pytest.approx(float(reference(2.0)), abs=1e-9)
        assert body["result"]["boundary"] == NATURAL
        assert body["python_source"]
        assert body["pseudocode"]

    def test_clamped_solve_returns_values(self, client: TestClient) -> None:
        payload = {**self.PAYLOAD, "boundary": CLAMPED, "left_derivative": 0.0, "right_derivative": 20.0}
        body = client.post("/api/solve/cubic_spline", json=payload).json()
        assert body["status"] == "converged"
        assert body["result"]["boundary"] == CLAMPED

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/cubic_spline?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "cubic_spline")
        assert method["status"] == "available"


class TestCubicSplineSchema:
    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["boundary"] in {NATURAL, CLAMPED}

    def test_unknown_boundary_is_rejected(self) -> None:
        payload = {
            "points": [[0, 0], [1, 1], [2, 4]],
            "boundary": "periodic",
            "decimal_precision": 6,
        }
        with pytest.raises(InvalidInputError):
            validate_inputs(META, payload, LIMITS)

    def test_result_is_converged_for_all_examples(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED
            assert response.steps[-1].title == "Result"
