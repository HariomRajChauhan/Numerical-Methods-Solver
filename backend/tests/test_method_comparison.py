"""Tests for the method-comparison solver (Chapter 1 orchestrator)."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.method_comparison import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CUBIC_ROOT = 1.5213797068045676
COS_ROOT = 0.7390851332151559
SQRT2 = math.sqrt(2.0)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x^3 - x - 2",
        "a": 1.0,
        "b": 2.0,
        "x0": 1.5,
        "x1": 2.0,
        "g": "",
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "function",
        "decimal_precision": 6,
        "run_bisection": True,
        "run_false_position": True,
        "run_secant": True,
        "run_newton_raphson": True,
        "run_fixed_point": False,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def row_for(response: Any, name: str) -> list[Any]:
    return next(row for row in response.tables[0].rows if row[0] == name)


class TestMethodComparisonSolver:
    def test_runs_every_selected_method(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        rows = response.tables[0].rows
        assert [row[0] for row in rows] == [
            "Bisection",
            "False Position",
            "Secant",
            "Newton-Raphson",
        ]
        assert all(row[6] == "converged" for row in rows)

    def test_reference_root_matches_true_root(self) -> None:
        response = run()
        assert math.isclose(response.result["reference_root"], CUBIC_ROOT, rel_tol=1e-6)

    def test_newton_beats_bisection_in_iterations(self) -> None:
        response = run()
        assert row_for(response, "Newton-Raphson")[1] < row_for(response, "Bisection")[1]

    def test_convergence_orders_reported(self) -> None:
        response = run()
        secant_order = row_for(response, "Secant")[5]
        newton_order = row_for(response, "Newton-Raphson")[5]
        assert secant_order == pytest.approx(1.618, abs=0.05)
        assert newton_order == pytest.approx(2.0, abs=0.1)

    def test_fastest_method_reported(self) -> None:
        response = run()
        assert response.result["fastest_method"] == "Newton-Raphson"
        assert set(response.result["converged_methods"]) == {
            "Bisection",
            "False Position",
            "Secant",
            "Newton-Raphson",
        }

    def test_all_five_methods_with_explicit_g(self) -> None:
        response = run(
            function="cos(x) - x",
            a=0.0,
            b=1.0,
            x0=1.0,
            x1=0.5,
            g="cos(x)",
            tolerance=1e-8,
            max_iterations=60,
            stopping_criterion="interval",
            run_fixed_point=True,
        )
        assert response.status == SolveStatus.CONVERGED
        assert len(response.tables[0].rows) == 5
        assert row_for(response, "Fixed-Point")[6] == "converged"
        assert math.isclose(response.result["reference_root"], COS_ROOT, rel_tol=1e-6)

    def test_fixed_point_auto_rearrangement_when_g_blank(self) -> None:
        response = run(
            function="cos(x) - x",
            a=0.0,
            b=1.0,
            x0=1.0,
            x1=0.5,
            g="",
            run_bisection=False,
            run_false_position=False,
            run_secant=False,
            run_newton_raphson=False,
            run_fixed_point=True,
        )
        assert response.status == SolveStatus.CONVERGED
        assert len(response.tables[0].rows) == 1
        assert row_for(response, "Fixed-Point")[6] == "converged"

    def test_divergent_method_does_not_break_comparison(self) -> None:
        response = run(
            function="atan(x)",
            a=-1.0,
            b=1.0,
            x0=2.0,
            x1=1.0,
            max_iterations=30,
            run_secant=False,
        )
        assert response.status == SolveStatus.CONVERGED
        assert row_for(response, "Newton-Raphson")[6] == "diverged"
        assert any("Newton-Raphson" in warning for warning in response.warnings)

    def test_failing_bracketing_method_is_reported_not_raised(self) -> None:
        response = run(
            function="x^2 - 2",
            a=2.0,
            b=3.0,
            x0=1.0,
            x1=2.0,
        )
        assert response.status == SolveStatus.CONVERGED
        assert row_for(response, "Bisection")[6] == "error"
        assert row_for(response, "False Position")[6] == "error"
        assert math.isclose(response.result["reference_root"], SQRT2, rel_tol=1e-6)

    def test_selecting_no_method_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="at least one method"):
            run(
                run_bisection=False,
                run_false_position=False,
                run_secant=False,
                run_newton_raphson=False,
                run_fixed_point=False,
            )

    def test_plot_is_semilog_with_one_line_per_method(self) -> None:
        response = run()
        assert response.plot.layout["yaxis"]["type"] == "log"
        assert len(response.plot.traces) == 4
        assert {trace["name"] for trace in response.plot.traces} == {
            "Bisection",
            "False Position",
            "Secant",
            "Newton-Raphson",
        }

    def test_full_contract(self) -> None:
        response = run()
        assert response.method == "method_comparison"
        assert set(response.result) >= {
            "reference_root",
            "fastest_method",
            "converged_methods",
            "methods",
        }
        table = response.tables[0]
        assert table.columns == [
            "Method",
            "Iterations",
            "Final root",
            "Final |f(x)|",
            "Final error",
            "Order",
            "Status",
        ]
        assert len(response.result["methods"]) == len(table.rows)

    def test_steps_have_setup_and_result(self) -> None:
        response = run()
        titles = [step.title for step in response.steps]
        assert titles[0] == "Setup"
        assert "Bracketing vs open methods" in titles
        assert titles[-1] == "Result"

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["function"]
            assert (cleaned["run_bisection"] or cleaned["run_false_position"]
                    or cleaned["run_secant"] or cleaned["run_newton_raphson"]
                    or cleaned["run_fixed_point"])


class TestMethodComparisonApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x^3 - x - 2",
        "a": 1.0,
        "b": 2.0,
        "x0": 1.5,
        "x1": 2.0,
        "tolerance": 1e-6,
        "max_iterations": 50,
        "stopping_criterion": "function",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/method_comparison", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "method_comparison"
        assert body["status"] == "converged"
        assert body["tables"][0]["rows"]
        assert "def solve" in body["python_source"]
        assert body["pseudocode"]

    def test_export_csv(self, client: TestClient) -> None:
        response = client.post(
            "/api/export/method_comparison?format=csv", json=self.PAYLOAD
        )
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "Method comparison" in response.text

    def test_method_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/method_comparison").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == [
            "function",
            "a",
            "b",
            "x0",
            "x1",
            "g",
            "tolerance",
            "max_iterations",
            "stopping_criterion",
            "decimal_precision",
            "run_bisection",
            "run_false_position",
            "run_secant",
            "run_newton_raphson",
            "run_fixed_point",
        ]
        assert meta["status"] == "available"
        booleans = [f for f in meta["input_schema"] if f["type"] == "boolean"]
        assert len(booleans) == 5

    def test_no_method_selected_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/method_comparison",
            json={
                **self.PAYLOAD,
                "run_bisection": False,
                "run_false_position": False,
                "run_secant": False,
                "run_newton_raphson": False,
                "run_fixed_point": False,
            },
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"
