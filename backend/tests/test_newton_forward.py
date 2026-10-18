"""Tests for Newton's forward difference interpolation."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation.newton_forward import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

PARABOLA = [[0.0, 1.0], [1.0, 2.0], [2.0, 5.0], [3.0, 10.0]]
SQUARES = [[1.0, 1.0], [2.0, 4.0], [3.0, 9.0], [4.0, 16.0], [5.0, 25.0]]
UNEVEN = [[0.0, 1.0], [1.0, 2.0], [3.0, 10.0]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in PARABOLA],
        "targets": [0.5],
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _numpy_value(points: list[list[float]], target: float) -> float:
    xs = np.asarray([point[0] for point in points], dtype=float)
    ys = np.asarray([point[1] for point in points], dtype=float)
    coefficients = np.polyfit(xs, ys, len(xs) - 1)
    return float(np.polyval(coefficients, target))


class TestNewtonForwardSolver:
    def test_known_answer_parabola(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(1.25, abs=1e-12)
        assert response.result["leading_differences"] == pytest.approx([1.0, 1.0, 2.0, 0.0])
        assert response.result["step"] == pytest.approx(1.0)

    def test_multiple_targets(self) -> None:
        response = run(targets=[0.5, 1.5, 2.5])
        expected = [0.5**2 + 1, 1.5**2 + 1, 2.5**2 + 1]
        assert response.result["values"] == pytest.approx(expected, abs=1e-12)

    def test_matches_numpy_interpolation(self) -> None:
        response = run(points=SQUARES, targets=[1.3])
        assert response.result["value"] == pytest.approx(
            _numpy_value(SQUARES, 1.3), abs=1e-9
        )

    def test_unsorted_input_is_sorted_with_notice(self) -> None:
        response = run(points=list(reversed(PARABOLA)))
        assert response.result["value"] == pytest.approx(1.25, abs=1e-12)
        assert any("sorted" in warning for warning in response.warnings)

    def test_extrapolation_warning(self) -> None:
        response = run(targets=[5.0])
        assert any("extrapolation" in warning for warning in response.warnings)

    def test_region_warning_near_end(self) -> None:
        response = run(targets=[2.9])
        assert any("backward" in warning for warning in response.warnings)

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

    def test_steps_tables_and_plot_present(self) -> None:
        response = run()
        titles = [table.title for table in response.tables]
        assert titles[0] == "Data points"
        assert "Forward difference table (D = Delta)" in titles
        assert response.plot.traces
        assert any("Evaluate at" in step.title for step in response.steps)

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["targets"]


class TestNewtonForwardApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in PARABOLA],
        "targets": [0.5],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/newton_forward", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(1.25, abs=1e-12)
        assert "def solve" in body["python_source"]

    def test_missing_target_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/newton_forward", json={**self.PAYLOAD, "targets": []}
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_unequal_spacing_is_200_failed(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/newton_forward", json={**self.PAYLOAD, "points": UNEVEN}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "newton_forward")
        assert method["status"] == "available"
        assert method["chapter"] == "ch3_interpolation"
