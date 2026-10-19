"""Tests for the Chapter 4 numerical differentiation solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch4_diff_integration.numerical_differentiation import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CUBE = [[0.0, 0.0], [1.0, 1.0], [2.0, 8.0], [3.0, 27.0], [4.0, 64.0]]
UNEVEN = [[0.0, 0.0], [1.0, 1.0], [3.0, 9.0]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "source": "table",
        "points": [list(point) for point in CUBE],
        "target": 0.0,
        "order": "1",
        "formula": "auto",
        "step": 0.01,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestTabulatedFirstDerivative:
    def test_forward_at_first_node(self) -> None:
        response = run(target=0.0, formula="forward")
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(0.0, abs=1e-12)
        assert response.result["family"] == "forward"
        assert response.result["p"] == pytest.approx(0.0)

    def test_forward_diagonal_labelled(self) -> None:
        response = run(target=0.0, formula="forward")
        table = next(t for t in response.tables if t.title == "Derivative terms")
        assert table.rows[0][0] == r"\Delta\,y_{0}"

    def test_backward_at_last_node(self) -> None:
        response = run(target=4.0, formula="backward")
        assert response.result["value"] == pytest.approx(48.0, abs=1e-9)
        assert response.result["family"] == "backward"

    def test_backward_known_value_at_x3(self) -> None:
        response = run(target=3.0, formula="backward")
        assert response.result["value"] == pytest.approx(27.0, abs=1e-9)

    def test_central_middle_node(self) -> None:
        response = run(target=2.0, formula="central")
        assert response.result["value"] == pytest.approx(12.0, abs=1e-9)
        assert response.result["family"] == "central"

    def test_central_uses_centre_index(self) -> None:
        response = run(target=2.0, formula="central")
        assert response.result["base_index"] == 2


class TestTabulatedSecondDerivative:
    def test_forward_second_derivative_at_first_node(self) -> None:
        response = run(target=0.0, order="2", formula="forward")
        assert response.result["value"] == pytest.approx(0.0, abs=1e-9)

    def test_backward_second_derivative_at_last_node(self) -> None:
        response = run(target=4.0, order="2", formula="backward")
        assert response.result["value"] == pytest.approx(24.0, abs=1e-9)

    def test_backward_second_derivative_at_x3(self) -> None:
        response = run(target=3.0, order="2", formula="backward")
        assert response.result["value"] == pytest.approx(18.0, abs=1e-9)

    def test_central_second_derivative(self) -> None:
        response = run(target=2.0, order="2", formula="central")
        assert response.result["value"] == pytest.approx(12.0, abs=1e-9)


class TestAutoSuggestion:
    def test_start_picks_forward(self) -> None:
        assert run(target=0.0).result["family"] == "forward"

    def test_end_picks_backward(self) -> None:
        assert run(target=4.0).result["family"] == "backward"

    def test_middle_picks_central(self) -> None:
        assert run(target=2.0).result["family"] == "central"


class TestFunctionInput:
    def test_central_first_derivative_of_sin(self) -> None:
        response = run(source="function", function="sin(x)", step=0.01, target=0.2)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["value"] == pytest.approx(math.cos(0.2), abs=1e-4)

    def test_forward_first_derivative_of_cube(self) -> None:
        response = run(
            source="function",
            function="x^3",
            step=0.001,
            target=1.0,
            formula="forward",
        )
        assert response.result["value"] == pytest.approx(3.0, abs=1e-2)

    def test_second_derivative_stencil(self) -> None:
        response = run(
            source="function",
            function="x^3",
            step=0.01,
            target=1.0,
            order="2",
            formula="central",
        )
        assert response.result["value"] == pytest.approx(6.0, abs=1e-6)

    def test_auto_defaults_to_central(self) -> None:
        response = run(source="function", function="exp(x)", step=0.01, target=0.0)
        assert response.result["family"] == "central"
        assert response.result["value"] == pytest.approx(1.0, abs=1e-4)

    def test_nonfinite_node_fails(self) -> None:
        response = run(
            source="function",
            function="1/x",
            step=0.1,
            target=0.0,
            formula="forward",
        )
        assert response.status == SolveStatus.FAILED
        assert any("finite" in warning for warning in response.warnings)

    def test_missing_function_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="function"):
            run(source="function", function="")

    def test_nonpositive_step_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="positive"):
            run(source="function", function="x^2", step=0.0, target=1.0)


class TestFailures:
    def test_unequal_spacing_fails(self) -> None:
        response = run(points=UNEVEN, target=1.0)
        assert response.status == SolveStatus.FAILED
        assert any("equally spaced" in warning for warning in response.warnings)

    def test_too_few_points_for_second_derivative(self) -> None:
        with pytest.raises(InvalidInputError):
            run(points=[[0.0, 0.0], [1.0, 1.0]], order="2")

    def test_central_needs_three_points(self) -> None:
        with pytest.raises(InvalidInputError, match="three"):
            run(points=[[0.0, 0.0], [1.0, 1.0]], target=0.5, formula="central")

    def test_missing_points_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(points=None)


class TestWarningsAndPlot:
    def test_extrapolation_warns(self) -> None:
        response = run(target=6.0, formula="backward")
        assert any("extrapolation" in warning for warning in response.warnings)

    def test_forward_used_near_end_warns(self) -> None:
        response = run(target=4.0, formula="forward")
        assert any("backward" in warning for warning in response.warnings)

    def test_plot_marks_evaluation_point(self) -> None:
        response = run(target=2.0, formula="central")
        names = [trace["name"] for trace in response.plot.traces]
        assert "Data points" in names
        assert "Evaluation point" in names

    def test_tangent_for_first_derivative(self) -> None:
        response = run(target=2.0, formula="central")
        names = [trace["name"] for trace in response.plot.traces]
        assert "Tangent" in names

    def test_no_tangent_for_second_derivative(self) -> None:
        response = run(target=2.0, order="2", formula="central")
        names = [trace["name"] for trace in response.plot.traces]
        assert "Tangent" not in names


class TestSchema:
    def test_all_examples_validate(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["source"] in {"table", "function"}

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status == SolveStatus.CONVERGED

    def test_unknown_scheme_rejected(self) -> None:
        with pytest.raises(InvalidInputError):
            validate_inputs(META, {"formula": "upwind", "float": 1}, LIMITS)


class TestApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "source": "table",
        "points": [list(point) for point in CUBE],
        "target": 2.0,
        "order": "1",
        "formula": "central",
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/numerical_differentiation", json=self.PAYLOAD)
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
        assert body["result"]["value"] == pytest.approx(12.0, abs=1e-9)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(
                f"/api/export/numerical_differentiation?format={fmt}", json=self.PAYLOAD
            )
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "numerical_differentiation")
        assert method["status"] == "available"
