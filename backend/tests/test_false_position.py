"""Tests for the false position (regula falsi) solver."""

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
from app.solvers.ch1_nonlinear.false_position import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CUBIC_ROOT = 1.5213797068045676
COS_FIXED_POINT = 0.7390851332151559
EXP_ROOT = 0.6190612867359452

SCIPY_FUNCS = {
    "x^3 - x - 2": lambda x: x**3 - x - 2,
    "cos(x) - x": lambda x: np.cos(x) - x,
    "e^x - 3x": lambda x: np.exp(x) - 3 * x,
}


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x^3 - x - 2",
        "a": 1.0,
        "b": 2.0,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "function",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestFalsePositionSolver:
    def test_converges_to_known_root(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["root"], CUBIC_ROOT, abs_tol=1e-5)
        assert abs(response.result["f(root)"]) < 1e-4

    @pytest.mark.parametrize(
        "function,a,b,expected",
        [
            ("x^3 - x - 2", 1.0, 2.0, CUBIC_ROOT),
            ("cos(x) - x", 0.0, 1.0, COS_FIXED_POINT),
            ("e^x - 3x", 0.5, 1.0, EXP_ROOT),
        ],
    )
    def test_matches_scipy_brentq(self, function: str, a: float, b: float, expected: float) -> None:
        response = run(function=function, a=a, b=b, tolerance=1e-10)
        assert math.isclose(response.result["root"], expected, abs_tol=1e-6)
        assert math.isclose(expected, brentq(SCIPY_FUNCS[function], a, b), abs_tol=1e-9)

    def test_full_contract(self) -> None:
        response = run()
        assert response.method == "false_position"
        assert set(response.result) >= {"root", "iterations", "f(root)", "final_interval"}
        assert len(response.tables) == 1
        assert response.tables[0].columns[0] == "Iteration"
        assert len(response.tables[0].rows) == response.result["iterations"]
        assert response.tables[0].columns[-1].startswith("Error")

    def test_steps_have_setup_and_result(self) -> None:
        titles = [step.title for step in run().steps]
        assert titles[0] == "Setup"
        assert "Iteration 1" in titles
        assert titles[-1] == "Result"

    def test_stopping_criterion_interval(self) -> None:
        response = run(stopping_criterion="interval")
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["root"], CUBIC_ROOT, abs_tol=1e-5)

    def test_stopping_criterion_relative(self) -> None:
        response = run(stopping_criterion="relative", tolerance=1e-4)
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["root"], CUBIC_ROOT, abs_tol=1e-3)

    def test_no_sign_change_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="sign change"):
            run(function="x^2 + 1")

    def test_equal_bounds_raise(self) -> None:
        with pytest.raises(InvalidInputError, match="different"):
            run(a=1.0, b=1.0)

    def test_root_on_endpoint_needs_no_iterations(self) -> None:
        response = run(function="x", a=0.0, b=1.0)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["root"] == 0.0
        assert response.result["iterations"] == 0
        assert response.tables == []

    def test_swapped_bounds_are_corrected(self) -> None:
        response = run(a=2.0, b=1.0)
        assert any("swapped" in warning for warning in response.warnings)
        assert math.isclose(response.result["root"], CUBIC_ROOT, abs_tol=1e-5)

    def test_max_iterations_status(self) -> None:
        response = run(tolerance=1e-15, max_iterations=2)
        assert response.status == SolveStatus.MAX_ITER
        assert response.result["iterations"] == 2
        assert len(response.tables[0].rows) == 2
        assert response.warnings

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


class TestFalsePositionApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x^3 - x - 2",
        "a": 1,
        "b": 2,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "function",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/false_position", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "false_position"
        assert body["status"] == "converged"
        assert body["tables"][0]["rows"]
        assert "def solve" in body["python_source"]

    def test_export_csv(self, client: TestClient) -> None:
        response = client.post("/api/export/false_position?format=csv", json=self.PAYLOAD)
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "False position iterations" in response.text

    def test_no_sign_change_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/false_position", json={**self.PAYLOAD, "function": "x^2 + 1"}
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/false_position").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == [
            "function",
            "a",
            "b",
            "tolerance",
            "max_iterations",
            "stopping_criterion",
            "decimal_precision",
        ]
        assert meta["status"] == "available"
