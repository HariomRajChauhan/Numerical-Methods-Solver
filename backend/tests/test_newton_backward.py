"""Tests for Newton's backward difference interpolation."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation.newton_backward import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

PARABOLA = [[0.0, 1.0], [1.0, 2.0], [2.0, 5.0], [3.0, 10.0]]
SQUARES = [[1.0, 1.0], [2.0, 4.0], [3.0, 9.0], [4.0, 16.0], [5.0, 25.0]]
UNEVEN = [[0.0, 1.0], [1.0, 2.0], [3.0, 10.0]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in PARABOLA],
        "targets": [2.5],
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _numpy_value(points: list[list[float]], target: float) -> float:
    xs = np.asarray([point[0] for point in points], dtype=float)
    ys = np.asarray([point[1] for point in points], dtype=float)
    coefficients = np.polyfit(xs, ys, len(xs) - 1)
    return float(np.polyval(coefficients, target))


class TestNewtonBackwardSolver:
    def test_known_answer_parabola(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(7.25, abs=1e-12)
        assert response.result["leading_differences"] == pytest.approx([10.0, 5.0, 2.0, 0.0])
        assert response.result["base_x"] == pytest.approx(3.0)

    def test_multiple_targets(self) -> None:
        response = run(targets=[2.5, 1.5, 0.5])
        expected = [2.5**2 + 1, 1.5**2 + 1, 0.5**2 + 1]
        assert response.result["values"] == pytest.approx(expected, abs=1e-12)

    def test_matches_numpy_interpolation(self) -> None:
        response = run(points=SQUARES, targets=[4.7])
        assert response.result["value"] == pytest.approx(
            _numpy_value(SQUARES, 4.7), abs=1e-9
        )

    def test_unsorted_input_is_sorted_with_notice(self) -> None:
        response = run(points=list(reversed(PARABOLA)))
        assert response.result["value"] == pytest.approx(7.25, abs=1e-12)
        assert any("sorted" in warning for warning in response.warnings)

    def test_region_warning_near_start(self) -> None:
        response = run(targets=[0.1])
        assert any("forward" in warning for warning in response.warnings)

    def test_unequal_spacing_fails(self) -> None:
        response = run(points=UNEVEN, targets=[2.0])
        assert response.status == SolveStatus.FAILED
        assert any("equally spaced" in warning for warning in response.warnings)

    def test_duplicate_x_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="distinct"):
            run(points=[[0.0, 1.0], [0.0, 2.0], [3.0, 10.0]])

    def test_missing_target_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="target"):
            run(targets=[])

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["targets"]


class TestNewtonBackwardApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in PARABOLA],
        "targets": [2.5],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/newton_backward", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(7.25, abs=1e-12)
        assert "def solve" in body["python_source"]

    def test_missing_target_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/newton_backward", json={**self.PAYLOAD, "targets": []}
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_unequal_spacing_is_200_failed(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/newton_backward", json={**self.PAYLOAD, "points": UNEVEN}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "newton_backward")
        assert method["status"] == "available"
        assert method["chapter"] == "ch3_interpolation"
