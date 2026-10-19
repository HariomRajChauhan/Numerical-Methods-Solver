"""Tests for least-squares curve fitting (all models, failures and comparison)."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.optimize import curve_fit

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation.least_squares import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)
LINE = [[0, 1], [1, 3], [2, 5], [3, 7], [4, 9]]
QUADRATIC = [[0, 1], [1, 6], [2, 17], [3, 34], [4, 57]]
EXPONENTIAL = [[0, 2], [1, 3.29744], [2, 5.43656], [3, 8.96338], [4, 14.77811]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in LINE],
        "fit_type": "linear",
        "degree": 3,
        "targets": [],
        "compare": False,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _columns(points: list[list[float]]) -> tuple[np.ndarray, np.ndarray]:
    xs = np.asarray([point[0] for point in points], dtype=float)
    ys = np.asarray([point[1] for point in points], dtype=float)
    return xs, ys


def _number(value: Any) -> float:
    """Parse a formatted table cell (plain decimal or ``m\\times 10^{e}``)."""
    text = str(value)
    if "\\times" in text:
        mantissa, _, exponent = text.partition("\\times 10^{")
        return float(mantissa) * 10.0 ** int(exponent.rstrip("}"))
    return float(text)


def _sums_lookup(response: Any) -> dict[str, float]:
    table = next(t for t in response.tables if t.title.startswith("Sums"))
    return {row[0]: float(row[1]) for row in table.rows if row[0] != "n"}


class TestLeastSquaresModels:
    def test_linear_matches_numpy_polyfit(self) -> None:
        response = run(fit_type="linear")
        xs, ys = _columns(LINE)
        slope, intercept = np.polyfit(xs, ys, 1)
        assert response.result["parameters"]["a"] == pytest.approx(intercept, abs=1e-9)
        assert response.result["parameters"]["b"] == pytest.approx(slope, abs=1e-9)
        assert response.result["sse"] == pytest.approx(0.0, abs=1e-9)

    def test_linear_matches_scipy_curve_fit(self) -> None:
        response = run(fit_type="linear")
        xs, ys = _columns(LINE)
        (a, b), _ = curve_fit(lambda x, a, b: a + b * x, xs, ys)
        assert response.result["parameters"]["a"] == pytest.approx(float(a), abs=1e-7)
        assert response.result["parameters"]["b"] == pytest.approx(float(b), abs=1e-7)

    def test_quadratic_matches_numpy_polyfit(self) -> None:
        response = run(points=QUADRATIC, fit_type="quadratic", targets=[5.0])
        xs, ys = _columns(QUADRATIC)
        c2, c1, c0 = np.polyfit(xs, ys, 2)
        params = response.result["parameters"]
        assert params["c"] == pytest.approx(float(c2), abs=1e-6)
        assert params["b"] == pytest.approx(float(c1), abs=1e-6)
        assert params["a"] == pytest.approx(float(c0), abs=1e-6)
        assert response.result["predictions"][0] == pytest.approx(86.0, abs=1e-4)

    def test_polynomial_degree_matches_numpy(self) -> None:
        points = [[x, float(x) ** 4 - 2 * x + 1] for x in range(6)]
        response = run(points=points, fit_type="polynomial", degree=4, targets=[5.5])
        xs, ys = _columns(points)
        reference = np.polyval(np.polyfit(xs, ys, 4), 5.5)
        assert response.result["degree"] == 4
        assert response.result["predictions"][0] == pytest.approx(float(reference), abs=1e-4)

    def test_exponential_linearisation_matches_polyfit(self) -> None:
        response = run(points=EXPONENTIAL, fit_type="exponential", targets=[5.0])
        xs, ys = _columns(EXPONENTIAL)
        slope, intercept = np.polyfit(xs, np.log(ys), 1)
        assert response.result["parameters"]["a"] == pytest.approx(float(np.exp(intercept)), rel=1e-6)
        assert response.result["parameters"]["b"] == pytest.approx(float(slope), rel=1e-6)
        assert response.result["predictions"][0] == pytest.approx(2 * np.exp(0.5 * 5.0), rel=1e-4)

    def test_power_linearisation_matches_polyfit(self) -> None:
        points = [[1, 3], [2, 12], [3, 27], [4, 48], [5, 75]]
        response = run(points=points, fit_type="power", targets=[6.0])
        xs, ys = _columns(points)
        slope, intercept = np.polyfit(np.log(xs), np.log(ys), 1)
        assert response.result["parameters"]["a"] == pytest.approx(float(np.exp(intercept)), rel=1e-6)
        assert response.result["parameters"]["b"] == pytest.approx(float(slope), rel=1e-6)
        assert response.result["predictions"][0] == pytest.approx(108.0, rel=1e-5)

    def test_reciprocal_linearisation_matches_polyfit(self) -> None:
        points = [[1, 4], [2, 5], [4, 5.5], [8, 5.75]]
        response = run(points=points, fit_type="reciprocal", targets=[10.0])
        xs, ys = _columns(points)
        slope, intercept = np.polyfit(1.0 / xs, ys, 1)
        assert response.result["parameters"]["a"] == pytest.approx(float(intercept), abs=1e-9)
        assert response.result["parameters"]["b"] == pytest.approx(float(slope), abs=1e-9)
        assert response.result["predictions"][0] == pytest.approx(5.8, abs=1e-9)

    def test_hyperbolic_linearisation_matches_polyfit(self) -> None:
        points = [[0, 0.5], [1, 0.3333], [2, 0.25], [3, 0.2]]
        response = run(points=points, fit_type="hyperbolic", targets=[4.0])
        xs, ys = _columns(points)
        slope, intercept = np.polyfit(xs, 1.0 / ys, 1)
        assert response.result["parameters"]["a"] == pytest.approx(float(intercept), rel=1e-3)
        assert response.result["parameters"]["b"] == pytest.approx(float(slope), rel=1e-3)

    def test_sums_table_contents(self) -> None:
        response = run(points=[[0, 1], [1, 3], [2, 5]], fit_type="linear")
        sums = _sums_lookup(response)
        assert sums["Σx"] == pytest.approx(3.0)
        assert sums["Σy"] == pytest.approx(9.0)
        assert sums["Σxy"] == pytest.approx(13.0)
        assert sums["Σx²"] == pytest.approx(5.0)

    def test_residuals_sum_to_sse(self) -> None:
        response = run(points=QUADRATIC, fit_type="quadratic")
        table = next(t for t in response.tables if t.title == "Residuals")
        total = sum(_number(row[4]) for row in table.rows)
        assert total == pytest.approx(response.result["sse"], rel=1e-6)

    def test_statistics_table_reports_fit_quality(self) -> None:
        response = run(points=QUADRATIC, fit_type="quadratic")
        table = next(t for t in response.tables if t.title == "Fit statistics")
        values = {row[0]: row[1] for row in table.rows}
        assert _number(values["R²"]) == pytest.approx(response.result["r_squared"], rel=1e-6)
        assert _number(values["RMSE"]) == pytest.approx(response.result["rmse"], rel=1e-6)

    def test_reducible_form_shows_linearisation_step(self) -> None:
        steps = [step.title for step in run(points=EXPONENTIAL, fit_type="exponential").steps]
        assert "Linearisation" in steps
        assert "Back-transformed coefficients" in steps

    def test_normal_equations_step_present(self) -> None:
        steps = [step.title for step in run().steps]
        assert "Normal equations" in steps
        assert "Solve the normal equations" in steps

    def test_polynomial_step_absent_for_linear(self) -> None:
        steps = [step.title for step in run().steps]
        assert "Linearisation" not in steps

    def test_result_is_final_step(self) -> None:
        assert run().steps[-1].title == "Result"

    def test_exact_fit_warning(self) -> None:
        response = run(points=[[0, 1], [1, 3]], fit_type="linear")
        assert any("exact" in warning.lower() for warning in response.warnings)

    def test_no_exact_fit_warning_with_enough_points(self) -> None:
        response = run(points=LINE, fit_type="linear")
        assert not any("exact" in warning.lower() for warning in response.warnings)


class TestLeastSquaresFailures:
    def test_exponential_needs_positive_y(self) -> None:
        response = run(points=[[0, -1], [1, 2], [2, 3]], fit_type="exponential")
        assert response.status == SolveStatus.FAILED
        assert any("y > 0" in warning for warning in response.warnings)

    def test_power_needs_positive_x_and_y(self) -> None:
        response = run(points=[[-1, 1], [1, 2], [2, 3]], fit_type="power")
        assert response.status == SolveStatus.FAILED
        assert any("x > 0" in warning for warning in response.warnings)

    def test_power_needs_positive_y(self) -> None:
        response = run(points=[[1, -1], [2, 2], [3, 3]], fit_type="power")
        assert response.status == SolveStatus.FAILED
        assert any("y > 0" in warning for warning in response.warnings)

    def test_reciprocal_needs_nonzero_x(self) -> None:
        response = run(points=[[0, 1], [1, 2], [2, 3]], fit_type="reciprocal")
        assert response.status == SolveStatus.FAILED
        assert any("x != 0" in warning for warning in response.warnings)

    def test_hyperbolic_needs_nonzero_y(self) -> None:
        response = run(points=[[0, 0], [1, 2], [2, 3]], fit_type="hyperbolic")
        assert response.status == SolveStatus.FAILED
        assert any("y != 0" in warning for warning in response.warnings)

    def test_too_few_points_for_degree(self) -> None:
        response = run(points=[[0, 1], [1, 2]], fit_type="quadratic")
        assert response.status == SolveStatus.FAILED
        assert any("at least 3" in warning for warning in response.warnings)

    def test_failed_response_has_no_plot_curves(self) -> None:
        response = run(points=[[0, -1], [1, 2]], fit_type="exponential")
        assert response.status == SolveStatus.FAILED
        assert response.plot.traces == []

    def test_repeated_x_values_are_accepted(self) -> None:
        points = [[1, 2], [1, 2.2], [2, 5], [2, 5.3], [3, 9], [3, 9.4]]
        response = run(points=points, fit_type="linear")
        assert response.status == SolveStatus.CONVERGED
        xs, ys = _columns(points)
        slope, intercept = np.polyfit(xs, ys, 1)
        assert response.result["parameters"]["a"] == pytest.approx(intercept, abs=1e-9)
        assert response.result["parameters"]["b"] == pytest.approx(slope, abs=1e-9)

    def test_repeated_x_notice(self) -> None:
        points = [[1, 2], [1, 2.2], [2, 5], [3, 9]]
        response = run(points=points, fit_type="linear")
        assert any("repeat" in warning.lower() for warning in response.warnings)


class TestLeastSquaresCompare:
    def test_ranking_table_is_sorted(self) -> None:
        response = run(points=LINE, fit_type="linear", compare=True)
        table = next(t for t in response.tables if t.title.startswith("Model comparison"))
        sses = [_number(row[2]) for row in table.rows]
        assert sses == sorted(sses)
        assert [entry["sse"] for entry in response.result["ranking"]] == pytest.approx(sses, rel=1e-5)

    def test_overlay_plot_has_several_models(self) -> None:
        response = run(points=QUADRATIC, fit_type="quadratic", compare=True)
        names = [trace["name"] for trace in response.plot.traces]
        assert "Linear" in names
        assert "Quadratic" in names
        assert "Data points" in names

    def test_ranking_reports_best_model(self) -> None:
        response = run(points=QUADRATIC, fit_type="quadratic", compare=True)
        assert response.result["best_model"]
        ranking = response.result["ranking"]
        assert ranking[0]["sse"] <= ranking[-1]["sse"]

    def test_invalid_models_are_skipped_with_warning(self) -> None:
        points = [[0, 1], [1, 3], [2, 5], [3, 7], [4, 9]]
        response = run(points=points, fit_type="linear", compare=True)
        # The power and reciprocal models need x > 0 / x != 0, so x = 0 rules them out.
        assert any("skipped" in warning for warning in response.warnings)


class TestLeastSquaresApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in QUADRATIC],
        "fit_type": "quadratic",
        "degree": 3,
        "targets": [5.0],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/least_squares", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["predictions"][0] == pytest.approx(86.0, abs=1e-4)
        assert body["python_source"]

    def test_mathematical_failure_is_200_failed(self, client: TestClient) -> None:
        payload = {"points": [[0, -1], [1, 2], [2, 3]], "fit_type": "exponential", "decimal_precision": 6}
        response = client.post("/api/solve/least_squares", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_repeated_x_is_accepted(self, client: TestClient) -> None:
        payload = {
            "points": [[1, 2], [1, 2.2], [2, 5], [2, 5.3], [3, 9], [3, 9.4]],
            "fit_type": "linear",
            "degree": 3,
            "decimal_precision": 6,
        }
        response = client.post("/api/solve/least_squares", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "converged"

    def test_catalogue_lists_method(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "least_squares")
        assert method["status"] == "available"


class TestLeastSquaresSchema:
    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["fit_type"]

    def test_degree_is_bounded(self) -> None:
        payload = {
            "points": [list(point) for point in LINE],
            "fit_type": "polynomial",
            "degree": 9,
            "decimal_precision": 6,
        }
        with pytest.raises(InvalidInputError):
            validate_inputs(META, payload, LIMITS)
