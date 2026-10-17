"""Tests for the fixed-point iteration solver."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
from fastapi.testclient import TestClient
from scipy.optimize import brentq

from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.fixed_point import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

COS_FIXED_POINT = 0.7390851332151559
SQRT2 = math.sqrt(2.0)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "cos(x)",
        "original_function": "cos(x) - x",
        "x0": 1.0,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestFixedPointSolver:
    def test_converges_to_cosine_fixed_point(self) -> None:
        response = run(tolerance=1e-10, max_iterations=100)
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["fixed_point"], COS_FIXED_POINT, abs_tol=1e-8)
        assert math.isclose(
            COS_FIXED_POINT, brentq(lambda x: np.cos(x) - x, 0.0, 1.0), abs_tol=1e-9
        )

    def test_babylonian_reaches_sqrt2(self) -> None:
        response = run(
            function="(x + 2/x)/2",
            original_function="x^2 - 2",
            x0=1.0,
            tolerance=1e-10,
        )
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["fixed_point"], SQRT2, abs_tol=1e-9)
        assert math.isclose(SQRT2, np.sqrt(2.0), abs_tol=0.0)

    def test_contraction_flag_reported(self) -> None:
        response = run()
        assert response.result["is_contraction"] is True
        assert response.result["derivative_at_guess"] is not None

    def test_non_contraction_warns(self) -> None:
        response = run(function="2*x", original_function="", x0=0.5, max_iterations=10)
        assert response.result["is_contraction"] is False
        assert any("|g'(x0)|" in warning for warning in response.warnings)

    def test_divergence_detected(self) -> None:
        response = run(function="2*x", original_function="", x0=0.5, max_iterations=100)
        assert response.status == SolveStatus.DIVERGED
        assert any("diverged" in warning for warning in response.warnings)

    def test_oscillation_hits_max_iter(self) -> None:
        response = run(function="x^2 - 1", original_function="", x0=1.0, max_iterations=20)
        assert response.status == SolveStatus.MAX_ITER
        assert response.warnings

    def test_suggested_rearrangements_present_with_original(self) -> None:
        response = run()
        titles = [table.title for table in response.tables]
        assert any("Suggested rearrangements" in title for title in titles)
        suggestion = next(t for t in response.tables if "Suggested" in t.title)
        assert suggestion.columns == ["Choice of g(x)", "g'(x_0)", "|g'(x_0)|", "Contraction?"]
        assert any(row[3] == "yes" for row in suggestion.rows)

    def test_no_suggestions_without_original(self) -> None:
        response = run(original_function="")
        titles = [table.title for table in response.tables]
        assert not any("Suggested" in title for title in titles)

    def test_full_contract(self) -> None:
        response = run()
        assert response.method == "fixed_point"
        assert set(response.result) >= {
            "fixed_point",
            "iterations",
            "g(root)",
            "derivative_at_guess",
            "is_contraction",
        }
        assert response.tables[0].columns[0] == "Iteration"
        assert len(response.tables[0].rows) == response.result["iterations"]

    def test_steps_have_setup_iterations_and_result(self) -> None:
        response = run()
        titles = [step.title for step in response.steps]
        assert titles[0] == "Setup"
        assert "Iteration 1" in titles
        assert titles[-1] == "Result"

    def test_plot_shows_cobweb_and_identity_line(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "cobweb" in names
        assert "y = x" in names
        assert "fixed point" in names

    def test_function_stopping_criterion(self) -> None:
        response = run(stopping_criterion="function", tolerance=1e-8)
        assert response.status == SolveStatus.CONVERGED

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["function"]


class TestFixedPointApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "cos(x)",
        "original_function": "cos(x) - x",
        "x0": 1.0,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "interval",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/fixed_point", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "fixed_point"
        assert body["status"] == "converged"
        assert body["tables"][0]["rows"]
        assert "def solve" in body["python_source"]

    def test_export_csv(self, client: TestClient) -> None:
        response = client.post("/api/export/fixed_point?format=csv", json=self.PAYLOAD)
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "Fixed-point iterations" in response.text

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/fixed_point").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == [
            "function",
            "original_function",
            "x0",
            "tolerance",
            "max_iterations",
            "stopping_criterion",
            "decimal_precision",
        ]
        assert meta["status"] == "available"
