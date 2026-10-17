"""Tests for Newton's method for non-linear systems (Chapter 1)."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.nonlinear_system_newton import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CIRCLE_ROOT = (1.2496210676876531, 1.5615528128088303)
TRIG_ROOT = (0.6948196907307876, 0.768169156736796)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "equations": "x^2 + y^2 - 4; x^2 - y",
        "variables": "x, y",
        "initial_guess": [1.0, 1.0],
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestNonlinearSystemNewtonSolver:
    def test_converges_to_known_root(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        solution = response.result["solution"]
        assert math.isclose(solution[0], CIRCLE_ROOT[0], rel_tol=1e-6)
        assert math.isclose(solution[1], CIRCLE_ROOT[1], rel_tol=1e-6)
        assert response.result["residual_norm"] < 1e-6

    def test_transcendental_system_converges(self) -> None:
        response = run(
            equations="cos(x) - y; sin(y) - x",
            initial_guess=[0.5, 0.5],
            tolerance=1e-8,
        )
        assert response.status == SolveStatus.CONVERGED
        solution = response.result["solution"]
        assert math.isclose(solution[0], TRIG_ROOT[0], rel_tol=1e-7)
        assert math.isclose(solution[1], TRIG_ROOT[1], rel_tol=1e-7)

    def test_three_unknown_system(self) -> None:
        response = run(
            equations="x + y*z - 7; x*y + z - 5; x + y + z - 6",
            variables="x, y, z",
            initial_guess=[1.5, 2.5, 3.5],
        )
        assert response.status == SolveStatus.CONVERGED
        solution = response.result["solution"]
        assert solution == pytest.approx([1.0, 2.0, 3.0], abs=1e-6)

    def test_equality_form_equations_accepted(self) -> None:
        response = run(
            equations="x^2 + y^2 = 4; x^2 = y",
            initial_guess=[1.0, 1.0],
        )
        assert response.status == SolveStatus.CONVERGED
        assert response.result["solution"] == pytest.approx(list(CIRCLE_ROOT), rel=1e-6)

    def test_initial_guess_is_a_root(self) -> None:
        response = run(
            equations="x - 1; y - 2",
            initial_guess=[1.0, 2.0],
        )
        assert response.status == SolveStatus.CONVERGED
        assert response.result["iterations"] == 0

    def test_singular_jacobian_fails(self) -> None:
        response = run(
            equations="x + y - 2; 2*x + 2*y - 4",
            initial_guess=[0.0, 0.0],
        )
        assert response.status == SolveStatus.FAILED
        assert any("singular" in warning.lower() for warning in response.warnings)

    def test_undefined_at_guess_is_reported_not_raised(self) -> None:
        response = run(
            equations="log(x); y - 1",
            initial_guess=[0.0, 1.0],
        )
        assert response.status == SolveStatus.FAILED
        assert response.warnings

    def test_solution_is_named(self) -> None:
        response = run()
        named = response.result["named_solution"]
        assert set(named) == {"x", "y"}
        assert math.isclose(named["x"], CIRCLE_ROOT[0], rel_tol=1e-6)

    def test_convergence_is_quadratic(self) -> None:
        response = run(stopping_criterion="interval")
        order = response.result["estimated_order"]
        assert order is not None
        assert order == pytest.approx(2.0, abs=0.2)

    def test_table_shape(self) -> None:
        response = run()
        table = response.tables[0]
        assert table.columns == ["Iteration", "x", "y", "||F(x)||", "Error ||dx||"]
        assert len(table.rows) == response.result["iterations"]
        assert table.rows[0][0] == 1

    def test_plot_has_error_and_contour_for_two_variables(self) -> None:
        response = run()
        types = [trace["type"] for trace in response.plot.traces]
        assert types.count("contour") == 2
        assert "xaxis2" in response.plot.layout
        assert response.plot.layout["yaxis"]["type"] == "log"

    def test_plot_is_error_only_for_three_variables(self) -> None:
        response = run(
            equations="x + y*z - 7; x*y + z - 5; x + y + z - 6",
            variables="x, y, z",
            initial_guess=[1.5, 2.5, 3.5],
        )
        types = [trace["type"] for trace in response.plot.traces]
        assert "contour" not in types
        assert "xaxis2" not in response.plot.layout

    def test_steps_show_jacobian_and_linear_system(self) -> None:
        response = run()
        titles = [step.title for step in response.steps]
        assert titles[0] == "Setup"
        assert titles[-1] == "Result"
        first_iteration = next(step for step in response.steps if step.title == "Iteration 1")
        assert "J(x" in first_iteration.latex
        assert "Delta x" in first_iteration.latex

    def test_full_contract(self) -> None:
        response = run()
        assert response.method == "nonlinear_system_newton"
        assert set(response.result) >= {
            "variables",
            "solution",
            "named_solution",
            "iterations",
            "residual_norm",
            "estimated_order",
        }

    def test_comma_separated_equations_accepted(self) -> None:
        response = run(equations="x^2 + y^2 - 4, x^2 - y")
        assert response.status == SolveStatus.CONVERGED
        assert response.result["solution"] == pytest.approx(list(CIRCLE_ROOT), rel=1e-6)

    def test_mismatched_guess_length_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="one value per variable"):
            run(initial_guess=[1.0])

    def test_equation_count_mismatch_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="Expected 2 equation"):
            run(equations="x + y - 2")

    def test_all_examples_solve(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            response = solve(cleaned, LIMITS)
            assert response.status == SolveStatus.CONVERGED, example.name


class TestNonlinearSystemNewtonApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "equations": "x^2 + y^2 - 4; x^2 - y",
        "variables": "x, y",
        "initial_guess": "1, 1",
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/nonlinear_system_newton", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "nonlinear_system_newton"
        assert body["status"] == "converged"
        assert "def solve" in body["python_source"]
        assert body["pseudocode"]

    def test_export_csv(self, client: TestClient) -> None:
        response = client.post(
            "/api/export/nonlinear_system_newton?format=csv", json=self.PAYLOAD
        )
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "Newton" in response.text

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/nonlinear_system_newton").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == [
            "equations",
            "variables",
            "initial_guess",
            "tolerance",
            "max_iterations",
            "stopping_criterion",
            "decimal_precision",
        ]
        assert meta["status"] == "available"

    def test_bad_expression_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/nonlinear_system_newton",
            json={**self.PAYLOAD, "equations": "x + q - 2; y"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "expression_error"

    def test_bad_guess_length_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/nonlinear_system_newton",
            json={**self.PAYLOAD, "initial_guess": "1"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"
