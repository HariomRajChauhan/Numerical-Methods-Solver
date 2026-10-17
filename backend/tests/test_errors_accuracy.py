"""Tests for the errors-and-accuracy calculator."""

from __future__ import annotations

import math
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch1_nonlinear.errors_accuracy import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "true_value": 3.141592653589793,
        "approximate_value": 3.142857142857143,
        "previous_approximation": 3.14,
        "decimal_precision": 4,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestErrorsAccuracySolver:
    def test_known_pi_example(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        expected_abs = abs(3.141592653589793 - 3.142857142857143)
        assert math.isclose(response.result["absolute_error"], expected_abs, rel_tol=1e-12)
        assert math.isclose(response.result["relative_error_percent"], 0.04024994347, rel_tol=1e-6)
        assert response.result["significant_digits"] == 3
        assert math.isclose(
            response.result["relative_error"], response.result["absolute_error"] / math.pi, rel_tol=1e-12
        )

    def test_approximate_error_with_previous(self) -> None:
        response = run()
        expected = abs((3.142857142857143 - 3.14) / 3.142857142857143) * 100.0
        assert math.isclose(response.result["approximate_error_percent"], expected, rel_tol=1e-9)
        assert any("Approximate" in step.title for step in response.steps)

    def test_approximate_error_absent_without_previous(self) -> None:
        response = run(previous_approximation=None)
        assert response.result["approximate_error_percent"] is None

    def test_rounding_beats_chopping(self) -> None:
        response = run(approximate_value=3.1415, decimal_precision=3)
        assert response.result["rounded_value"] == pytest.approx(3.142)
        assert response.result["chopped_value"] == pytest.approx(3.141)
        assert response.result["rounded_absolute_error"] <= response.result["chopped_absolute_error"]

    def test_round_half_up_and_chop(self) -> None:
        response = run(true_value=3.0, approximate_value=2.5, previous_approximation=None, decimal_precision=0)
        assert response.result["rounded_value"] == 3.0
        assert response.result["chopped_value"] == 2.0

    def test_significant_figures_reported(self) -> None:
        response = run(true_value=123.45, approximate_value=123.4, previous_approximation=None)
        assert response.result["significant_figures_true"] == 5
        assert response.result["significant_figures_approximate"] == 4

    def test_exact_value_has_no_finite_digit_bound(self) -> None:
        response = run(true_value=2.0, approximate_value=2.0, previous_approximation=None)
        assert response.result["absolute_error"] == 0.0
        assert response.result["relative_error_percent"] == 0.0
        assert response.result["significant_digits"] is None

    def test_zero_true_value_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="non-zero"):
            run(true_value=0.0)

    def test_zero_approximation_with_previous_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="non-zero"):
            run(approximate_value=0.0, previous_approximation=1.0)

    def test_full_contract(self) -> None:
        response = run()
        assert response.method == "errors_accuracy"
        assert set(response.result) >= {
            "absolute_error",
            "relative_error",
            "relative_error_percent",
            "significant_digits",
        }
        assert len(response.tables) == 2
        assert response.tables[0].columns[0] == "Measure"
        assert response.tables[1].columns[0] == "Method"
        assert len(response.plot.traces) == 1
        assert response.plot.traces[0]["type"] == "bar"

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["true_value"] is not None


class TestErrorsAccuracyApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "true_value": 3.141592653589793,
        "approximate_value": 3.142857142857143,
        "decimal_precision": 4,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/errors_accuracy", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["method"] == "errors_accuracy"
        assert body["status"] == "converged"
        assert body["pseudocode"]
        assert "def solve" in body["python_source"]

    def test_export_csv_is_available(self, client: TestClient) -> None:
        response = client.post("/api/export/errors_accuracy?format=csv", json=self.PAYLOAD)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]
        assert "Absolute error" in response.text

    def test_zero_true_value_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/errors_accuracy",
            json={**self.PAYLOAD, "true_value": 0},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalog_marks_it_available(self, client: TestClient) -> None:
        method = next(
            m for m in client.get("/api/methods").json()["methods"] if m["id"] == "errors_accuracy"
        )
        assert method["status"] == "available"
        assert method["chapter"] == "ch1_nonlinear"
