"""Tests for Bessel's central-difference interpolation."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation.bessel import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
PARABOLA5 = [[0, 1], [1, 2], [2, 5], [3, 10], [4, 17]]
CUBIC5 = [[0, 0], [1, 1], [2, 8], [3, 27], [4, 64]]
UNEVEN = [[0, 1], [1, 2], [3, 10]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in PARABOLA5],
        "targets": [2.5],
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


class TestBesselSolver:
    def test_known_answer_parabola(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(7.25, abs=1e-12)
        assert response.result["center_index"] == 2
        assert response.result["next_x"] == pytest.approx(3.0, abs=1e-12)
        assert response.result["p"][0] == pytest.approx(0.5, abs=1e-12)

    def test_explicit_center(self) -> None:
        response = run(center=2)
        assert response.result["value"] == pytest.approx(7.25, abs=1e-12)

    def test_cubic_is_exact(self) -> None:
        response = run(points=CUBIC5, targets=[2.5])
        assert response.result["value"] == pytest.approx(2.5**3, abs=1e-9)

    def test_matches_numpy_for_cubic(self) -> None:
        response = run(points=CUBIC5, targets=[2.5])
        assert response.result["value"] == pytest.approx(_numpy_value(CUBIC5, 2.5), abs=1e-9)

    def test_region_warning_low_p(self) -> None:
        response = run(targets=[2.05])
        assert any("Stirling" in warning for warning in response.warnings)

    def test_region_warning_high_p(self) -> None:
        response = run(targets=[3.9])
        assert any("Stirling" in warning for warning in response.warnings)

    def test_last_node_center_is_shifted(self) -> None:
        response = run(center=4, targets=[3.5])
        assert response.result["center_index"] == 3
        assert response.result["order_used"] == 1
        assert response.result["value"] == pytest.approx(13.5, abs=1e-9)
        assert any("shifted" in warning for warning in response.warnings)

    def test_order_is_capped_by_available_points(self) -> None:
        response = run(center=1, targets=[1.5], order=9)
        assert response.result["order_used"] == response.result["max_order"]
        assert response.result["order_used"] == 3
        assert response.result["value"] == pytest.approx(1.5**2 + 1, abs=1e-9)

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


class TestBesselApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in PARABOLA5],
        "targets": [2.5],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/bessel", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["value"] == pytest.approx(7.25, abs=1e-9)
        assert body["python_source"]

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "bessel")
        assert method["status"] == "available"
