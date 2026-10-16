"""Tests for the bisection solver (the reference template).

Covers the solver contract directly plus the end-to-end API path, so a new
method can be copied from this file and adapted.
"""

from __future__ import annotations

import itertools
import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.bisection import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CUBIC_ROOT = 1.324717957244746


def run(**overrides: Any):
    """Solve the classic cubic with optional input overrides."""
    inputs: dict[str, Any] = {
        "function": "x^3 - x - 1",
        "a": 1.0,
        "b": 2.0,
        "tolerance": 1e-6,
        "max_iterations": 50,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestBisectionSolver:
    def test_converges_to_known_root(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        root = response.result["root"]
        assert math.isclose(root, CUBIC_ROOT, abs_tol=1e-6)
        assert abs(response.result["f(root)"]) < 1e-5
        assert response.result["iterations"] > 0

    def test_returns_full_contract(self) -> None:
        response = run()
        assert response.method == "bisection"
        assert set(response.result) == {"root", "iterations", "f(root)", "final_interval"}
        assert len(response.tables) == 1
        table = response.tables[0]
        assert table.columns[0] == "Iteration"
        assert len(table.rows) == response.result["iterations"]
        assert len(response.steps) >= response.result["iterations"] + 1
        assert len(response.plot.traces) == 2

    def test_error_metrics_are_reported(self) -> None:
        errors = run().errors
        assert errors.absolute is not None and errors.absolute >= 0
        assert errors.relative_percent is not None and errors.relative_percent >= 0
        assert errors.order_of_convergence == 1.0

    def test_interval_shrinks_and_error_decreases_roughly(self) -> None:
        rows = run(tolerance=1e-4).tables[0].rows
        widths = [row[2] - row[1] for row in rows]
        assert all(later <= earlier + 1e-12 for earlier, later in itertools.pairwise(widths))
        assert widths[-1] <= widths[0] / 2 ** (len(widths) - 1) + 1e-9

    def test_plot_marks_the_root(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert "root" in names
        root_trace = next(t for t in response.plot.traces if t["name"] == "root")
        assert root_trace["x"] == [response.result["root"]]
        assert "title" in response.plot.layout

    def test_iteration_steps_are_labelled(self) -> None:
        titles = [step.title for step in run().steps]
        assert titles[0] == "Setup"
        assert "Iteration 1" in titles
        assert titles[-1] == "Result"

    def test_iteration_limit_step_is_labelled(self) -> None:
        titles = [step.title for step in run(tolerance=1e-15, max_iterations=5).steps]
        assert titles[-1] == "Iteration limit reached"

    def test_no_sign_change_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="sign change"):
            run(function="x^2 + 1")

    def test_max_iterations_status(self) -> None:
        response = run(tolerance=1e-15, max_iterations=3)
        assert response.status == SolveStatus.MAX_ITER
        assert response.result["iterations"] == 3
        assert len(response.tables[0].rows) == 3
        assert response.warnings

    def test_root_on_endpoint_needs_no_iterations(self) -> None:
        response = run(function="x", a=0.0, b=1.0)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["root"] == 0.0
        assert response.result["iterations"] == 0
        assert response.tables == []

    def test_swapped_bounds_are_corrected(self) -> None:
        response = run(a=2.0, b=1.0)
        assert response.status == SolveStatus.CONVERGED
        assert any("swapped" in warning for warning in response.warnings)
        assert math.isclose(response.result["root"], CUBIC_ROOT, abs_tol=1e-6)

    def test_equal_bounds_raise(self) -> None:
        with pytest.raises(InvalidInputError, match="different"):
            run(a=1.0, b=1.0)

    def test_transcendental_example(self) -> None:
        response = run(function="cos(x) - x", a=0.0, b=1.0)
        assert response.status == SolveStatus.CONVERGED
        assert math.isclose(response.result["root"], 0.7390851332, abs_tol=1e-6)

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["function"]


class TestBisectionApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x^3 - x - 1",
        "a": 1,
        "b": 2,
        "tolerance": 1e-6,
        "max_iterations": 50,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/bisection", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["method"] == "bisection"
        assert body["status"] == "converged"
        assert math.isclose(body["result"]["root"], CUBIC_ROOT, abs_tol=1e-6)
        assert body["tables"][0]["rows"]
        assert body["pseudocode"].startswith("Bisection(")
        assert "def solve" in body["python_source"]

    def test_no_sign_change_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/bisection",
            json={**self.PAYLOAD, "function": "x^2 + 1"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_bad_expression_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/bisection",
            json={**self.PAYLOAD, "function": "x +"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "expression_error"

    def test_missing_function_is_400(self, client: TestClient) -> None:
        payload = dict(self.PAYLOAD)
        payload.pop("function")
        response = client.post("/api/solve/bisection", json=payload)
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalog_lists_bisection(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "bisection")
        assert method["status"] == "available"
        assert method["chapter"] == "ch1_nonlinear"
        chapter_one = next(c for c in body["chapters"] if c["number"] == 1)
        assert chapter_one["available_count"] >= 1

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/bisection").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == ["function", "a", "b", "tolerance", "max_iterations"]
        assert meta["formulas"]
        assert meta["examples"]
        assert meta["theory"]
