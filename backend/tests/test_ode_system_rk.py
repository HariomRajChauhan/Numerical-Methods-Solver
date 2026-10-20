"""Tests for the Chapter 5 system-of-ODEs Runge-Kutta solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from scipy.integrate import solve_ivp

from app.core.errors import ExpressionError, InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch5_ode.ode_system_rk import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "equations": "y' = z\nz' = -y",
        "independent_variable": "x",
        "state_variables": "y, z",
        "y0": [0.0, 1.0],
        "x0": 0.0,
        "x_end": 1.0,
        "step_mode": "step",
        "h": 0.1,
        "exact_solutions": "sin(x)\ncos(x)",
        "scheme": "rk4",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestSystemValues:
    def test_harmonic_oscillator_matches_exact(self) -> None:
        response = run(x_end=1.0, h=0.1)
        assert response.status == SolveStatus.CONVERGED
        y_end = response.result["y_end"]
        assert y_end[0] == pytest.approx(math.sin(1.0), abs=1e-6)
        assert y_end[1] == pytest.approx(math.cos(1.0), abs=1e-6)

    def test_k_vector_table_has_one_column_per_stage(self) -> None:
        response = run()
        table = next(t for t in response.tables if t.title == "Runge-Kutta stage vectors")
        assert table.columns == ["step", "x", "k1", "k2", "k3", "k4"]
        first = table.rows[1]
        assert first[2] == "(1.000000, 0)"
        assert first[3] == "(1.000000, -0.050000)"

    def test_rk2_uses_two_stage_vectors(self) -> None:
        response = run(scheme="rk2_heun")
        table = next(t for t in response.tables if t.title == "Runge-Kutta stage vectors")
        assert table.columns == ["step", "x", "k1", "k2"]

    def test_matches_scipy_solve_ivp(self) -> None:
        expected = solve_ivp(
            lambda t, s: [s[1], -s[0]], [0.0, 6.0], [0.0, 1.0], rtol=1e-12, atol=1e-14
        ).y[:, -1]
        response = run(x_end=6.0, h=0.1)
        assert response.result["y_end"][0] == pytest.approx(float(expected[0]), abs=1e-4)
        assert response.result["y_end"][1] == pytest.approx(float(expected[1]), abs=1e-4)

    def test_fourth_order_convergence(self) -> None:
        coarse = run(x_end=6.0, h=0.2).result["max_absolute_error"]
        fine = run(x_end=6.0, h=0.1).result["max_absolute_error"]
        assert coarse / fine == pytest.approx(16.0, rel=0.5)

    def test_three_variable_system(self) -> None:
        response = run(
            equations="y' = z\nz' = w\nw' = -y",
            state_variables="y, z, w",
            y0=[0.0, 1.0, 0.0],
            exact_solutions=None,
            x_end=1.0,
        )
        assert response.status == SolveStatus.CONVERGED
        assert len(response.result["y_end"]) == 3


class TestSystemStepStudy:
    def test_step_study_estimates_order_four(self) -> None:
        response = run(x_end=6.0, h=0.25, step_study=True)
        orders = next(t for t in response.tables if t.title == "Observed order of accuracy")
        assert float(orders.rows[-1][1]) == pytest.approx(4.0, abs=0.4)

    def test_step_study_replaces_plot_with_error_axis(self) -> None:
        response = run(x_end=6.0, h=0.25, step_study=True)
        assert response.plot is not None
        assert any("error" in trace["name"] for trace in response.plot.traces)


class TestSystemCompare:
    def test_compare_table_lists_three_schemes(self) -> None:
        response = run(x_end=6.0, h=0.25, compare=True)
        table = next(t for t in response.tables if t.title == "Scheme comparison")
        assert [row[0] for row in table.rows] == ["Euler", "RK2 (Heun)", "RK4"]
        assert [row[2] for row in table.rows] == [24, 48, 96]

    def test_compare_plot_has_log_error_axis(self) -> None:
        response = run(x_end=6.0, h=0.25, compare=True)
        assert response.plot is not None
        assert response.plot.layout["yaxis2"]["type"] == "log"


class TestSystemPlots:
    def test_two_variable_system_has_phase_portrait(self) -> None:
        response = run()
        assert response.plot is not None
        graph = next(t for t in response.plot.traces if t.get("name", "").startswith("phase"))
        assert graph["x"] and graph["y"]
        assert "annotations" in response.plot.layout

    def test_three_variable_system_has_3d_trajectory(self) -> None:
        response = run(
            equations="y' = z\nz' = w\nw' = -y",
            state_variables="y, z, w",
            y0=[0.0, 1.0, 0.0],
            exact_solutions=None,
            x_end=1.0,
        )
        assert response.plot is not None
        assert any(trace.get("type") == "scatter3d" for trace in response.plot.traces)
        assert "scene" in response.plot.layout

    def test_exact_overlay_traces_present(self) -> None:
        response = run(exact_solutions="sin(x)\ncos(x)")
        assert response.plot is not None
        names = {trace["name"] for trace in response.plot.traces}
        assert {"exact y", "exact z"} <= names


class TestSystemEdges:
    def test_zero_step_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(h=0.0)

    def test_undefined_variable_raises(self) -> None:
        with pytest.raises(ExpressionError):
            run(equations="y' = z + q\nz' = -y")

    def test_wrong_initial_vector_length_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(y0=[0.0, 1.0, 2.0])

    def test_wrong_number_of_equations_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(equations="y' = z")

    def test_backward_integration(self) -> None:
        response = run(x0=1.0, x_end=0.0, h=0.1)
        assert response.status == SolveStatus.CONVERGED
        assert any("Backward" in warning for warning in response.warnings)

    def test_equal_endpoints_return_initial_vector(self) -> None:
        response = run(x0=1.0, x_end=1.0)
        assert response.result["y_end"] == [0.0, 1.0]
        assert response.result["steps"] == 0

    def test_exponential_blow_up_diverges(self) -> None:
        response = run(
            equations="y' = y*z\nz' = y*z",
            state_variables="y, z",
            y0=[1.0, 1.0],
            exact_solutions=None,
            x_end=5.0,
            h=0.5,
        )
        assert response.status == SolveStatus.DIVERGED
        assert response.result["diverged_at_step"] >= 1


class TestSystemSchema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            assert validate_inputs(META, example.inputs, LIMITS)

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status in {SolveStatus.CONVERGED, SolveStatus.DIVERGED}


class TestSystemApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "equations": "y' = z\nz' = -y",
        "independent_variable": "x",
        "state_variables": "y, z",
        "y0": [0.0, 1.0],
        "x0": 0.0,
        "x_end": 1.0,
        "step_mode": "step",
        "h": 0.1,
        "exact_solutions": "sin(x)\ncos(x)",
        "scheme": "rk4",
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/ode_system_rk", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["variables"] == ["y", "z"]
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/ode_system_rk?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "ode_system_rk")
        assert method["status"] == "available"
