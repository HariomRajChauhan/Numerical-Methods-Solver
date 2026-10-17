"""Tests for the secant solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.optimize import brentq

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.secant import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CUBIC_ROOT = 1.5213797068045676
COS_FIXED_POINT = 0.7390851332151559
EXP_ROOT = 0.6190612867359452

SCIPY_FUNCS = {
    "x^3 - x - 2": lambda x: x**3 - x - 2,
    "cos(x) - x": lambda x: np.cos(x) - x,
    "e^x - 3x": lambda x: np.exp(x) - 3 * x,
    "sqrt(x^2+1)": lambda x: np.sqrt(x**2 + 1),
}


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x^3 - x - 2",
        "x0": 1.0,
        "x1": 2.0,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestSecantSolver:
    def test_converges_to_known_root(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["root"], CUBIC_ROOT, abs_tol=1e-6)
        assert response.result["iterations"] > 0

    @pytest.mark.parametrize(
        "function,x0,x1,expected",
        [
            ("x^3 - x - 2", 1.0, 2.0, CUBIC_ROOT),
            ("cos(x) - x", 0.0, 1.0, COS_FIXED_POINT),
            ("e^x - 3x", 0.0, 1.0, EXP_ROOT),
        ],
    )
    def test_matches_reference_and_scipy(self, function: str, x0: float, x1: float, expected: float) -> None:
        response = run(function=function, x0=x0, x1=x1, tolerance=1e-10)
        assert math.isclose(response.result["root"], expected, abs_tol=1e-6)
        # The guesses also bracket the root for these cases, so scipy agrees.
        lo, hi = min(x0, x1), max(x0, x1)
        if SCIPY_FUNCS[function](lo) * SCIPY_FUNCS[function](hi) < 0:
            assert math.isclose(expected, brentq(SCIPY_FUNCS[function], lo, hi), abs_tol=1e-9)

    def test_full_contract(self) -> None:
        response = run()
        assert response.method == "secant"
        assert set(response.result) >= {"root", "iterations", "f(root)", "estimated_order"}
        assert len(response.tables) == 1
        assert response.tables[0].columns[0] == "Iteration"
        assert len(response.tables[0].rows) == response.result["iterations"]

    def test_convergence_order_is_superlinear(self) -> None:
        response = run(tolerance=1e-12, max_iterations=50)
        order = response.errors.order_of_convergence
        assert order is not None
        assert 1.3 < order < 2.2
        assert response.result["estimated_order"] == pytest.approx(order, rel=1e-9)

    def test_equal_guesses_raise(self) -> None:
        with pytest.raises(InvalidInputError, match="different"):
            run(x0=1.5, x1=1.5)

    def test_division_by_zero_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="Division by zero"):
            run(function="x^2 + 1", x0=0.0, x1=1.0)

    def test_divergence_detected(self) -> None:
        response = run(function="sqrt(x^2+1)", x0=0.0, x1=1.0, max_iterations=60, tolerance=1e-6)
        assert response.status == SolveStatus.DIVERGED
        assert any("diverged" in warning for warning in response.warnings)

    def test_max_iterations_status(self) -> None:
        response = run(tolerance=1e-15, max_iterations=2)
        assert response.status == SolveStatus.MAX_ITER
        assert response.result["iterations"] == 2
        assert len(response.tables[0].rows) == 2
        assert response.warnings

    def test_stopping_criterion_function(self) -> None:
        response = run(stopping_criterion="function")
        assert response.status == SolveStatus.CONVERGED
        assert abs(response.result["f(root)"]) < 1e-5

    def test_steps_have_setup_and_result(self) -> None:
        titles = [step.title for step in run().steps]
        assert titles[0] == "Setup"
        assert "Iteration 1" in titles
        assert titles[-1] == "Result"

    def test_plot_marks_root_and_shows_secants(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "root" in names
        assert "iterates" in names
        assert any(name.startswith("secant") for name in names)
        assert "title" in response.plot.layout

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["function"]


class TestSecantApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x^3 - x - 2",
        "x0": 1,
        "x1": 2,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/secant", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "secant"
        assert body["status"] == "converged"
        assert body["tables"][0]["rows"]
        assert "def solve" in body["python_source"]

    def test_export_csv(self, client: TestClient) -> None:
        response = client.post("/api/export/secant?format=csv", json=self.PAYLOAD)
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "Secant iterations" in response.text

    def test_equal_guesses_is_400(self, client: TestClient) -> None:
        response = client.post("/api/solve/secant", json={**self.PAYLOAD, "x0": 1, "x1": 1})
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/secant").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == [
            "function",
            "x0",
            "x1",
            "tolerance",
            "max_iterations",
            "stopping_criterion",
            "decimal_precision",
        ]
        assert meta["status"] == "available"
