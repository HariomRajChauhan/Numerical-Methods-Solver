"""Tests for Lagrange interpolation, the compare view and the Runge demo."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.interpolate import lagrange as scipy_lagrange

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation._lagrange import lagrange_basis_value
from app.solvers.ch3_interpolation.lagrange import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PARABOLA4 = [[0, 1], [1, 2], [2, 5], [3, 10]]
UNEVEN3 = [[0, 1], [1, 2], [3, 10]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in PARABOLA4],
        "targets": [2.5],
        "compare": False,
        "runge_demo": False,
        "runge_nodes": 11,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _numpy_value(points: list[list[float]], target: float) -> float:
    xs = np.asarray([point[0] for point in points], dtype=float)
    ys = np.asarray([point[1] for point in points], dtype=float)
    return float(np.polyval(np.polyfit(xs, ys, len(xs) - 1), target))


class TestLagrangeSolver:
    def test_known_answer_parabola(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(7.25, abs=1e-12)

    def test_unequal_spacing_is_allowed(self) -> None:
        response = run(points=UNEVEN3, targets=[2.0])
        assert response.result["value"] == pytest.approx(5.0, abs=1e-12)

    def test_matches_numpy_polyfit(self) -> None:
        response = run(targets=[0.5, 1.5, 2.9])
        for target, value in zip([0.5, 1.5, 2.9], response.result["values"], strict=True):
            assert value == pytest.approx(_numpy_value(PARABOLA4, target), abs=1e-9)

    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    def test_matches_scipy_lagrange(self) -> None:
        xs = np.asarray([p[0] for p in PARABOLA4], dtype=float)
        ys = np.asarray([p[1] for p in PARABOLA4], dtype=float)
        reference = scipy_lagrange(xs, ys)
        response = run(targets=[2.5])
        assert response.result["value"] == pytest.approx(float(reference(2.5)), abs=1e-9)

    def test_basis_is_one_at_own_node_zero_elsewhere(self) -> None:
        xs = np.asarray([p[0] for p in PARABOLA4], dtype=float)
        for i in range(len(xs)):
            for j in range(len(xs)):
                expected = 1.0 if i == j else 0.0
                assert lagrange_basis_value(xs, i, float(xs[j])) == pytest.approx(expected, abs=1e-12)

    def test_basis_plot_has_one_curve_per_node(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        for i in range(len(PARABOLA4)):
            assert f"L_{i}(x)" in names

    def test_basis_step_present(self) -> None:
        steps = [step.title for step in run().steps]
        assert "Lagrange basis polynomials" in steps

    def test_compare_view_agrees(self) -> None:
        response = run(compare=True)
        table = next(t for t in response.tables if t.title.startswith("Comparison"))
        difference = float(table.rows[0][3])
        assert difference == pytest.approx(0.0, abs=1e-9)
        names = [trace["name"] for trace in response.plot.traces]
        assert "Newton divided difference" in names
        assert "Lagrange" in names

    def test_high_degree_warning(self) -> None:
        points = [[x, float(x) ** 2] for x in range(12)]
        response = run(points=points, targets=[5.5])
        assert any("Runge" in warning for warning in response.warnings)

    def test_duplicate_x_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="distinct"):
            run(points=[[0, 1], [0, 2], [3, 10]])

    def test_missing_target_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="target"):
            run(targets=[])

    def test_result_is_final_step(self) -> None:
        assert run().steps[-1].title == "Result"


class TestRungeDemo:
    def test_demo_returns_plot_table_and_errors(self) -> None:
        response = run(runge_demo=True, runge_nodes=11, targets=[])
        assert response.status == SolveStatus.CONVERGED
        assert response.result["nodes"] == 11
        assert response.result["degree"] == 10
        # Chebyshev is far better at degree 10.
        assert response.result["max_error_chebyshev"] < response.result["max_error_equispaced"]
        names = [trace["name"] for trace in response.plot.traces]
        assert any("f(x)" in name for name in names)
        assert response.tables

    def test_demo_respects_node_count(self) -> None:
        response = run(runge_demo=True, runge_nodes=7, targets=[])
        assert response.result["nodes"] == 7
        assert response.result["degree"] == 6

    def test_node_count_is_bounded(self) -> None:
        payload = {
            "points": [list(point) for point in PARABOLA4],
            "targets": [0.5],
            "runge_demo": True,
            "runge_nodes": 3,
            "decimal_precision": 6,
        }
        with pytest.raises(InvalidInputError):
            validate_inputs(META, payload, LIMITS)


class TestLagrangeApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in PARABOLA4],
        "targets": [2.5],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/lagrange", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(7.25, abs=1e-9)
        assert body["python_source"]

    def test_missing_target_is_bad_request(self, client: TestClient) -> None:
        payload = {**self.PAYLOAD, "targets": []}
        response = client.post("/api/solve/lagrange", json=payload)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "lagrange")
        assert method["status"] == "available"


class TestLagrangeSchema:
    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["runge_nodes"] >= 4
