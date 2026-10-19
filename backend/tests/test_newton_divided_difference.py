"""Tests for Newton's divided-difference interpolation."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.interpolate import lagrange as scipy_lagrange

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation.newton_divided_difference import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PARABOLA4 = [[0, 1], [1, 2], [2, 5], [3, 10]]
UNEVEN3 = [[0, 1], [1, 2], [3, 10]]
CUBIC_UNEVEN = [[0, 0], [1, 1], [3, 27], [4, 64]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in PARABOLA4],
        "targets": [2.5],
        "expand_polynomial": False,
        "compare": False,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _numpy_value(points: list[list[float]], target: float) -> float:
    xs = np.asarray([point[0] for point in points], dtype=float)
    ys = np.asarray([point[1] for point in points], dtype=float)
    return float(np.polyval(np.polyfit(xs, ys, len(xs) - 1), target))


class TestNewtonDividedSolver:
    def test_known_answer_parabola(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(7.25, abs=1e-12)

    def test_unequal_spacing_is_allowed(self) -> None:
        response = run(points=UNEVEN3, targets=[2.0])
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(5.0, abs=1e-12)

    def test_cubic_is_exact_on_uneven_nodes(self) -> None:
        response = run(points=CUBIC_UNEVEN, targets=[2.0])
        assert response.result["value"] == pytest.approx(8.0, abs=1e-12)

    def test_matches_numpy_polyfit(self) -> None:
        response = run(points=CUBIC_UNEVEN, targets=[1.5, 2.5])
        for target, value in zip([1.5, 2.5], response.result["values"], strict=True):
            assert value == pytest.approx(_numpy_value(CUBIC_UNEVEN, target), abs=1e-9)

    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    def test_matches_scipy_lagrange(self) -> None:
        xs = np.asarray([p[0] for p in UNEVEN3], dtype=float)
        ys = np.asarray([p[1] for p in UNEVEN3], dtype=float)
        reference = scipy_lagrange(xs, ys)
        response = run(points=UNEVEN3, targets=[2.5])
        assert response.result["value"] == pytest.approx(float(reference(2.5)), abs=1e-9)

    def test_divided_table_marks_top_diagonal(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title == "Divided difference table")
        assert any(str(cell).endswith("*") for cell in table.rows[0])

    def test_expand_step_only_when_requested(self) -> None:
        assert not any(step.title.startswith("Expanded") for step in run().steps)
        response = run(expand_polynomial=True)
        assert any(step.title.startswith("Expanded") for step in response.steps)

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

    def test_extrapolation_warning(self) -> None:
        response = run(targets=[9.0])
        assert any("extrapolation" in warning for warning in response.warnings)

    def test_duplicate_x_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="distinct"):
            run(points=[[0, 1], [0, 2], [3, 10]])

    def test_missing_target_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="target"):
            run(targets=[])

    def test_result_is_final_step(self) -> None:
        assert run().steps[-1].title == "Result"

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["targets"]


class TestNewtonDividedApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in PARABOLA4],
        "targets": [2.5],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/newton_divided_difference", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(7.25, abs=1e-9)
        assert body["python_source"]

    def test_duplicate_x_is_bad_request(self, client: TestClient) -> None:
        payload = {**self.PAYLOAD, "points": [[0, 1], [0, 2], [3, 10]]}
        response = client.post("/api/solve/newton_divided_difference", json=payload)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "newton_divided_difference")
        assert method["status"] == "available"
