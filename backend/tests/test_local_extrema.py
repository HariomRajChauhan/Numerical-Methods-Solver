"""Tests for the Chapter 4 local maxima and minima solver."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch4_diff_integration.local_extrema import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

MINIMUM_DATA = [[0.0, 5.0], [1.0, 2.0], [2.0, 1.0], [3.0, 2.0], [4.0, 5.0]]
SADDLE_DATA = [[0.0, 0.0], [1.0, 3.0], [2.0, 2.0], [3.0, 9.0], [4.0, 24.0]]
NO_EXTREMA = [[0.0, 1.0], [1.0, 2.0], [2.0, 4.0], [3.0, 9.0]]
UNEVEN = [[0.0, 1.0], [1.0, 2.0], [3.0, 10.0]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in MINIMUM_DATA],
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestLocalExtrema:
    def test_known_minimum(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["count"] == 1
        extremum = response.result["extrema"][0]
        assert extremum["x"] == pytest.approx(2.0, abs=1e-9)
        assert extremum["y"] == pytest.approx(1.0, abs=1e-9)
        assert extremum["type"] == "minimum"
        assert extremum["second_derivative"] > 0

    def test_convenience_x_and_y(self) -> None:
        response = run()
        assert response.result["x"] == pytest.approx(2.0, abs=1e-9)
        assert response.result["y"] == pytest.approx(1.0, abs=1e-9)

    def test_saddle_has_two_turning_points(self) -> None:
        response = run(points=SADDLE_DATA)
        kinds = {item["type"] for item in response.result["extrema"]}
        assert response.result["count"] == 2
        assert kinds == {"maximum", "minimum"}

    def test_no_extrema_reports_warning(self) -> None:
        response = run(points=NO_EXTREMA)
        assert response.result["count"] == 0
        assert any("No local maximum" in warning for warning in response.warnings)

    def test_unsorted_input_is_sorted(self) -> None:
        response = run(points=list(reversed(MINIMUM_DATA)))
        assert response.result["extrema"][0]["x"] == pytest.approx(2.0, abs=1e-9)
        assert any("sorted" in warning for warning in response.warnings)

    def test_step_and_base_reported(self) -> None:
        response = run()
        assert response.result["step"] == pytest.approx(1.0)
        assert response.result["base_x"] == pytest.approx(0.0)


class TestLocalExtremaTablesAndPlot:
    def test_stationary_points_table(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title == "Stationary points")
        assert len(table.rows) == 1
        assert table.rows[0][-1] == "Minimum"

    def test_plot_marks_minimum(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "Data points" in names
        assert "Interpolating polynomial" in names
        assert "Minimum" in names

    def test_result_step_present(self) -> None:
        response = run()
        assert response.steps[-1].title == "Result"


class TestLocalExtremaFailures:
    def test_unequal_spacing_fails(self) -> None:
        response = run(points=UNEVEN)
        assert response.status == SolveStatus.FAILED
        assert any("equally spaced" in warning for warning in response.warnings)

    def test_too_few_points_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(points=[[0.0, 1.0], [1.0, 2.0]])

    def test_duplicate_x_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="distinct"):
            run(points=[[0.0, 1.0], [0.0, 2.0], [2.0, 5.0]])


class TestLocalExtremaSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED


class TestLocalExtremaApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in MINIMUM_DATA],
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/local_extrema", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method",
            "status",
            "result",
            "steps",
            "tables",
            "plot",
            "errors",
            "warnings",
            "pseudocode",
            "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["count"] == 1
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(
                f"/api/export/local_extrema?format={fmt}", json=self.PAYLOAD
            )
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "local_extrema")
        assert method["status"] == "available"
