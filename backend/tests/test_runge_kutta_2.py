"""Tests for the Chapter 5 second-order Runge-Kutta solver."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from scipy.integrate import solve_ivp

from app.core.errors import ExpressionError, InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch5_ode.runge_kutta_2 import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.1,
        "step_mode": "step",
        "h": 0.1,
        "variant": "heun",
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestRK2Values:
    def test_heun_first_step(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["y_end"] == pytest.approx(1.11, abs=1e-12)
        assert response.result["variant"] == "Heun (improved Euler)"

    def test_stage_values_heun(self) -> None:
        response = run(variant="heun")
        table = next(t for t in response.tables if t.title == "Runge-Kutta stages")
        assert table.columns[:5] == ["step", "x", "y", "k1", "k2"]
        assert table.rows[1][3] == "1.000000"
        assert table.rows[1][4] == "1.200000"

    def test_variants_pick_different_k2(self) -> None:
        def k2(variant: str) -> str:
            table = next(
                t for t in run(variant=variant).tables if t.title == "Runge-Kutta stages"
            )
            return table.rows[1][4]

        assert k2("heun") == "1.200000"
        assert k2("midpoint") == "1.100000"
        assert k2("ralston") == "1.150000"

    def test_all_variants_match_first_step(self) -> None:
        for variant in ("heun", "midpoint", "ralston"):
            assert run(variant=variant).result["y_end"] == pytest.approx(1.11, abs=1e-12)

    def test_matches_scipy_solve_ivp(self) -> None:
        expected = float(
            solve_ivp(lambda t, s: [t + s[0]], [0.0, 1.0], [1.0], rtol=1e-12, atol=1e-14).y[0, -1]
        )
        response = run(x_end=1.0, h=0.01)
        assert response.result["y_end"] == pytest.approx(expected, abs=1e-3)

    def test_butcher_tableau_step_present(self) -> None:
        titles = [step.title for step in run().steps]
        assert "Butcher tableau" in titles

    def test_step_study_estimates_order_two(self) -> None:
        response = run(x_end=1.0, h=0.25, step_study=True)
        orders = next(t for t in response.tables if t.title == "Observed order of accuracy")
        assert float(orders.rows[0][1]) == pytest.approx(2.0, abs=0.2)


class TestRK2Compare:
    def test_compare_table(self) -> None:
        response = run(x_end=1.0, h=0.25, compare=True)
        table = next(t for t in response.tables if t.title == "Method comparison")
        assert [row[0] for row in table.rows] == ["Euler", "RK2 (Heun)", "RK4"]
        assert [row[3] for row in table.rows] == [4, 8, 16]

    def test_compare_plot_has_log_error_axis(self) -> None:
        response = run(x_end=1.0, h=0.25, compare=True)
        assert response.plot is not None
        assert response.plot.layout["yaxis2"]["type"] == "log"


class TestRK2Edges:
    def test_zero_step_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            run(h=0.0)

    def test_unparseable_function_raises(self) -> None:
        with pytest.raises(ExpressionError):
            run(function="x +")

    def test_backward_integration(self) -> None:
        response = run(x0=0.2, x_end=0.0)
        assert response.status == SolveStatus.CONVERGED
        assert any("reversed" in warning for warning in response.warnings)

    def test_equal_endpoints_return_initial_value(self) -> None:
        assert run(x_end=0.0).result["y_end"] == 1.0

    def test_quadratic_blow_up_diverges(self) -> None:
        response = run(function="y^2", x_end=2.0, h=0.1, exact_solution=None)
        assert response.status == SolveStatus.DIVERGED


class TestRK2Schema:
    def test_examples_validate(self) -> None:
        for example in META.examples:
            assert validate_inputs(META, example.inputs, LIMITS)

    def test_examples_converge(self) -> None:
        for example in META.examples:
            response = solve(validate_inputs(META, example.inputs, LIMITS), LIMITS)
            assert response.status in {SolveStatus.CONVERGED, SolveStatus.DIVERGED}

    def test_variant_validation(self) -> None:
        cleaned = validate_inputs(
            META,
            {"function": "x + y", "x0": 0, "y0": 1, "x_end": 1, "variant": "ralston"},
            LIMITS,
        )
        assert cleaned["variant"] == "ralston"


class TestRK2Api:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "function": "x + y",
        "x0": 0.0,
        "y0": 1.0,
        "x_end": 0.1,
        "step_mode": "step",
        "h": 0.1,
        "variant": "ralston",
        "exact_solution": "2*exp(x) - x - 1",
        "decimal_precision": 6,
    }

    def test_solve_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/runge_kutta_2", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "converged"
        assert body["result"]["y_end"] == pytest.approx(1.11, abs=1e-12)
        assert body["python_source"]
        assert body["pseudocode"]

    def test_export_pdf_and_csv(self, client: TestClient) -> None:
        for fmt in ("pdf", "csv"):
            response = client.post(f"/api/export/runge_kutta_2?format={fmt}", json=self.PAYLOAD)
            assert response.status_code == 200

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "runge_kutta_2")
        assert method["status"] == "available"
