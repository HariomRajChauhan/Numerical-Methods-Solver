"""Tests for Stirling's central-difference interpolation."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation.stirling import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PARABOLA5 = [[0, 1], [1, 2], [2, 5], [3, 10], [4, 17]]
CUBIC5 = [[0, 0], [1, 1], [2, 8], [3, 27], [4, 64]]
UNEVEN = [[0, 1], [1, 2], [3, 10]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in PARABOLA5],
        "targets": [2.1],
        "decimal_precision": 6,
        "center": None,
        "order": None,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _numpy_value(points: list[list[float]], target: float) -> float:
    xs = np.asarray([point[0] for point in points], dtype=float)
    ys = np.asarray([point[1] for point in points], dtype=float)
    coefficients = np.polyfit(xs, ys, len(xs) - 1)
    return float(np.polyval(coefficients, target))


class TestStirlingSolver:
    def test_known_answer_parabola(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(5.41, abs=1e-12)
        assert response.result["center_index"] == 2
        assert response.result["p"][0] == pytest.approx(0.1, abs=1e-12)

    def test_explicit_center(self) -> None:
        response = run(center=2)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(5.41, abs=1e-12)

    def test_cubic_is_exact(self) -> None:
        response = run(points=CUBIC5, targets=[2.2])
        assert response.result["value"] == pytest.approx(2.2**3, abs=1e-9)
        assert response.result["order_used"] == response.result["max_order"]

    def test_matches_numpy_for_cubic(self) -> None:
        response = run(points=CUBIC5, targets=[2.2])
        assert response.result["value"] == pytest.approx(_numpy_value(CUBIC5, 2.2), abs=1e-9)

    def test_region_warning_away_from_centre(self) -> None:
        response = run(targets=[1.5])
        assert any("Bessel" in warning for warning in response.warnings)

    def test_order_is_capped_by_available_points(self) -> None:
        response = run(center=1, targets=[1.3], order=4)
        assert response.result["order_used"] == 2
        assert response.result["max_order"] == 2
        assert response.result["value"] == pytest.approx(1.3**2 + 1, abs=1e-9)

    def test_end_point_centre_fails(self) -> None:
        response = run(center=0, targets=[0.4])
        assert response.status == SolveStatus.FAILED
        assert any("both sides" in warning for warning in response.warnings)

    def test_centre_must_be_a_tabulated_x(self) -> None:
        with pytest.raises(InvalidInputError, match="central point"):
            run(center=9.5)

    def test_unequal_spacing_fails(self) -> None:
        response = run(points=UNEVEN, targets=[2.0])
        assert response.status == SolveStatus.FAILED
        assert any("equally spaced" in warning for warning in response.warnings)

    def test_duplicate_x_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="distinct"):
            run(points=[[0, 1], [0, 2], [3, 10]])

    def test_missing_target_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="target"):
            run(targets=[])

    def test_extrapolation_warning(self) -> None:
        response = run(targets=[6.0])
        assert any("extrapolation" in warning for warning in response.warnings)

    def test_central_table_present(self) -> None:
        response = run()
        titles = [table.title for table in response.tables]
        assert any("Central difference table" in title for title in titles)
        assert response.plot.traces
        assert response.steps[-1].title == "Result"

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["targets"]
            assert cleaned["center"] is None
            assert cleaned["order"] is None


class TestStirlingApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in PARABOLA5],
        "targets": [2.1],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/stirling", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(5.41, abs=1e-9)
        assert body["python_source"]

    def test_invalid_center_is_bad_request(self, client: TestClient) -> None:
        payload = {**self.PAYLOAD, "center": 9.5}
        response = client.post("/api/solve/stirling", json=payload)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "stirling")
        assert method["status"] == "available"
