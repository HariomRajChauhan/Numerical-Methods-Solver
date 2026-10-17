"""Tests for the Newton-Raphson solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.optimize import brentq

from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.newton_raphson import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CUBIC_ROOT = 1.5213797068045676
COS_FIXED_POINT = 0.7390851332151559
EXP_ROOT = 0.6190612867359452
SQRT2 = math.sqrt(2.0)

SCIPY_FUNCS = {
    "x^3 - x - 2": (lambda x: x**3 - x - 2, 1.0, 2.0),
    "cos(x) - x": (lambda x: np.cos(x) - x, 0.0, 1.0),
    "e^x - 3x": (lambda x: np.exp(x) - 3 * x, 0.0, 1.0),
}


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x^3 - x - 2",
        "derivative": "",
        "x0": 1.5,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestNewtonSolver:
    def test_converges_to_known_root(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["root"], CUBIC_ROOT, abs_tol=1e-6)
        assert response.result["iterations"] > 0

    @pytest.mark.parametrize(
        "function,x0,expected",
        [
            ("x^3 - x - 2", 1.5, CUBIC_ROOT),
            ("cos(x) - x", 1.0, COS_FIXED_POINT),
            ("e^x - 3x", 1.0, EXP_ROOT),
        ],
    )
    def test_matches_scipy_brentq(self, function: str, x0: float, expected: float) -> None:
        response = run(function=function, x0=x0, tolerance=1e-10)
        assert math.isclose(response.result["root"], expected, abs_tol=1e-6)
        scipy_func, lo, hi = SCIPY_FUNCS[function]
        assert math.isclose(expected, brentq(scipy_func, lo, hi), abs_tol=1e-9)

    def test_manual_derivative_matches_automatic(self) -> None:
        automatic = run(function="x^2 - 2", derivative="", x0=1.0, tolerance=1e-12)
        manual = run(function="x^2 - 2", derivative="2*x", x0=1.0, tolerance=1e-12)
        assert math.isclose(automatic.result["root"], SQRT2, abs_tol=1e-9)
        assert math.isclose(manual.result["root"], SQRT2, abs_tol=1e-9)
        assert "supplied derivative" in manual.steps[0].note

    def test_zero_derivative_fails_gracefully(self) -> None:
        response = run(function="x^2 + 1", x0=0.0)
        assert response.status == SolveStatus.FAILED
        assert any("f'(x) = 0" in warning for warning in response.warnings)

    def test_identically_zero_derivative_fails_gracefully(self) -> None:
        response = run(function="5", x0=1.0)
        assert response.status == SolveStatus.FAILED
        assert any("identically zero" in warning for warning in response.warnings)

    def test_divergence_detected(self) -> None:
        response = run(function="atan(x)", x0=2.0, max_iterations=60)
        assert response.status == SolveStatus.DIVERGED
        assert any("diverged" in warning for warning in response.warnings)

    def test_two_cycle_oscillation_warns(self) -> None:
        response = run(function="x^3 - 2*x + 2", x0=0.0, max_iterations=20)
        assert response.status == SolveStatus.MAX_ITER
        assert any("oscillation" in warning for warning in response.warnings)

    def test_max_iterations_status(self) -> None:
        response = run(tolerance=1e-15, max_iterations=2)
        assert response.status == SolveStatus.MAX_ITER
        assert response.result["iterations"] == 2
        assert len(response.tables[0].rows) == 2
        assert response.warnings

    def test_full_contract(self) -> None:
        response = run()
        assert response.method == "newton_raphson"
        assert set(response.result) >= {"root", "iterations", "f(root)", "estimated_order"}
        assert len(response.tables) == 1
        assert response.tables[0].columns[0] == "Iteration"
        assert len(response.tables[0].rows) == response.result["iterations"]

    def test_convergence_is_quadratic(self) -> None:
        response = run(tolerance=1e-12, max_iterations=50)
        order = response.errors.order_of_convergence
        assert order is not None
        assert 1.8 < order < 2.2

    def test_steps_have_setup_iterations_and_result(self) -> None:
        response = run()
        titles = [step.title for step in response.steps]
        assert titles[0] == "Setup"
        assert "Iteration 1" in titles
        assert titles[-1] == "Result"

    def test_plot_marks_root_and_shows_tangents(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "root" in names
        assert "iterates" in names
        assert any(name.startswith("tangent") for name in names)

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["function"]


class TestNewtonApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x^3 - x - 2",
        "derivative": "",
        "x0": 1.5,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/newton_raphson", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "newton_raphson"
        assert body["status"] == "converged"
        assert body["tables"][0]["rows"]
        assert "def solve" in body["python_source"]

    def test_export_csv(self, client: TestClient) -> None:
        response = client.post("/api/export/newton_raphson?format=csv", json=self.PAYLOAD)
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "Newton-Raphson iterations" in response.text

    def test_zero_derivative_is_failed_not_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/newton_raphson",
            json={**self.PAYLOAD, "function": "x^2 + 1", "x0": 0},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/newton_raphson").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == [
            "function",
            "derivative",
            "x0",
            "tolerance",
            "max_iterations",
            "stopping_criterion",
            "decimal_precision",
        ]
        assert meta["status"] == "available"
