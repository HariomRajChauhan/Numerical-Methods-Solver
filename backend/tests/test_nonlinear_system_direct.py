"""Tests for the direct (fixed-point) method for non-linear systems (Chapter 1)."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.nonlinear_system_direct import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CONTRACTION_ROOT = (1.7082039, 1.7082039)
TRIG_ROOT = (0.7681691567183694, 0.6948196907175355)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "equations": "x = (20 - y^2)/10; y = (20 - x^2)/10",
        "variables": "x, y",
        "initial_guess": [1.0, 1.0],
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestNonlinearSystemDirectSolver:
    def test_contraction_converges(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        solution = response.result["solution"]
        assert math.isclose(solution[0], CONTRACTION_ROOT[0], rel_tol=1e-5)
        assert math.isclose(solution[1], CONTRACTION_ROOT[1], rel_tol=1e-5)
        assert response.result["residual_norm"] < 1e-6

    def test_trigonometric_system_converges(self) -> None:
        response = run(
            equations="x = cos(y); y = sin(x)",
            initial_guess=[0.5, 0.5],
            tolerance=1e-8,
            max_iterations=100,
        )
        assert response.status == SolveStatus.CONVERGED
        solution = response.result["solution"]
        assert math.isclose(solution[0], TRIG_ROOT[0], rel_tol=1e-7)
        assert math.isclose(solution[1], TRIG_ROOT[1], rel_tol=1e-7)

    def test_three_unknown_nonlinear_system(self) -> None:
        response = run(
            equations=(
                "x = 1 + 0.1*(y - 2)*(z - 3); "
                "y = 2 + 0.1*(x - 1)*(z - 3); "
                "z = 3 + 0.1*(x - 1)*(y - 2)"
            ),
            variables="x, y, z",
            initial_guess=[1.5, 2.5, 3.5],
        )
        assert response.status == SolveStatus.CONVERGED
        assert response.result["solution"] == pytest.approx([1.0, 2.0, 3.0], abs=1e-8)

    def test_spectral_radius_reported(self) -> None:
        response = run()
        rho = response.result["spectral_radius"]
        assert rho is not None
        assert rho == pytest.approx(0.2, abs=1e-6)

    def test_non_contraction_warns(self) -> None:
        response = run(
            equations="x = 1.5*x; y = 1.5*y",
            initial_guess=[0.5, 0.5],
            max_iterations=20,
        )
        assert any("spectral radius" in warning for warning in response.warnings)

    def test_divergence_is_reported(self) -> None:
        response = run(
            equations="x = 10*x; y = 10*y",
            initial_guess=[0.5, 0.5],
            max_iterations=50,
        )
        assert response.status == SolveStatus.DIVERGED

    def test_table_shape(self) -> None:
        response = run()
        table = response.tables[0]
        assert table.columns == ["Iteration", "x", "y", "||F(x)||", "Error ||dx||"]
        assert len(table.rows) == response.result["iterations"]

    def test_steps_include_convergence_check(self) -> None:
        response = run()
        titles = [step.title for step in response.steps]
        assert titles[0] == "Setup"
        assert "Convergence check" in titles
        assert titles[-1] == "Result"
        check = next(step for step in response.steps if step.title == "Convergence check")
        assert "rho" in check.latex

    def test_plot_has_contour_for_two_variables(self) -> None:
        response = run()
        types = [trace["type"] for trace in response.plot.traces]
        assert types.count("contour") == 2
        assert "xaxis2" in response.plot.layout

    def test_solution_is_named(self) -> None:
        response = run()
        named = response.result["named_solution"]
        assert set(named) == {"x", "y"}

    def test_comma_separated_equations_accepted(self) -> None:
        response = run(equations="x = (20 - y^2)/10, y = (20 - x^2)/10")
        assert response.status == SolveStatus.CONVERGED
        assert response.result["solution"] == pytest.approx(
            list(CONTRACTION_ROOT), rel=1e-5
        )

    def test_unicode_and_comma_input(self) -> None:
        response = run(
            equations="x = sqrt(1+y), y = sqrt(4\u2212x\u00b2)",
            initial_guess=[1.5, 1.5],
            tolerance=1e-8,
            max_iterations=100,
        )
        assert response.status == SolveStatus.CONVERGED
        assert response.result["solution"] == pytest.approx(
            [1.5174899127194688, 1.3027756387017142], rel=1e-6
        )

    def test_mismatched_guess_length_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="one value per variable"):
            run(initial_guess=[1.0])

    def test_missing_equation_for_variable_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="No iteration equation"):
            run(equations="x = cos(y)")

    def test_unknown_lhs_variable_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="not one of the variables"):
            run(equations="w = 1; y = 0")

    def test_equation_without_equals_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="variable = expression"):
            run(equations="x + y; y = 0")

    def test_all_examples_solve(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            response = solve(cleaned, LIMITS)
            assert response.status == SolveStatus.CONVERGED, example.name


class TestNonlinearSystemDirectApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "equations": "x = (20 - y^2)/10; y = (20 - x^2)/10",
        "variables": "x, y",
        "initial_guess": "1, 1",
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/nonlinear_system_direct", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "nonlinear_system_direct"
        assert body["status"] == "converged"
        assert "def solve" in body["python_source"]
        assert body["pseudocode"]

    def test_export_csv(self, client: TestClient) -> None:
        response = client.post(
            "/api/export/nonlinear_system_direct?format=csv", json=self.PAYLOAD
        )
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "Direct" in response.text

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/nonlinear_system_direct").json()
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

    def test_missing_equation_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/nonlinear_system_direct",
            json={**self.PAYLOAD, "equations": "x = (20 - y^2)/10"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_export_pdf(self, client: TestClient) -> None:
        response = client.post(
            "/api/export/nonlinear_system_direct?format=pdf", json=self.PAYLOAD
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
