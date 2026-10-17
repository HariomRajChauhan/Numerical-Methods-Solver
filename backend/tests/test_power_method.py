"""Tests for the power method (dominant and smallest eigenvalues)."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch2_linear.power_method import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

SYMMETRIC = [[4.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 2.0]]
NON_SYMMETRIC = [[4.0, 1.0], [2.0, 3.0]]
EQUAL_MAGNITUDE = [[0.0, 1.0], [1.0, 0.0]]
COMPLEX_ROTATION = [[0.0, -1.0], [1.0, 0.0]]
SINGULAR = [[1.0, 2.0], [2.0, 4.0]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "matrix": [list(row) for row in SYMMETRIC],
        "initial_vector": None,
        "mode": "largest",
        "tolerance": 1e-8,
        "max_iterations": 200,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


def _normalise_sign(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=float)
    pivot = vector[int(np.argmax(np.abs(vector)))]
    return vector / pivot


def _numpy_eigen(matrix: list[list[float]], smallest: bool = False) -> tuple[float, np.ndarray]:
    values, vectors = np.linalg.eig(np.asarray(matrix, dtype=float))
    magnitudes = np.abs(values)
    index = int(np.argmin(magnitudes)) if smallest else int(np.argmax(magnitudes))
    return float(np.real(values[index])), np.real(vectors[:, index])


class TestPowerMethodSolver:
    def test_dominant_eigenvalue_matches_numpy(self) -> None:
        response = run()
        expected, expected_vector = _numpy_eigen(SYMMETRIC)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["eigenvalue"] == pytest.approx(expected, abs=1e-6)
        assert np.allclose(
            _normalise_sign(response.result["eigenvector"]), _normalise_sign(expected_vector), atol=1e-4
        )

    def test_non_symmetric_matches_numpy(self) -> None:
        response = run(matrix=NON_SYMMETRIC, initial_vector=[1.0, 0.0], tolerance=1e-10)
        expected, expected_vector = _numpy_eigen(NON_SYMMETRIC)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["eigenvalue"] == pytest.approx(expected, abs=1e-6)
        actual = _normalise_sign(response.result["eigenvector"])
        target = _normalise_sign(expected_vector)
        assert np.allclose(actual, target, atol=1e-6) or np.allclose(actual, -target, atol=1e-6)

    def test_smallest_eigenvalue_via_inverse_iteration(self) -> None:
        response = run(mode="smallest")
        expected, expected_vector = _numpy_eigen(SYMMETRIC, smallest=True)
        assert response.status == SolveStatus.CONVERGED
        assert response.result["eigenvalue"] == pytest.approx(expected, abs=1e-6)
        got = _normalise_sign(np.asarray(response.result["eigenvector"]))
        want = _normalise_sign(np.asarray(expected_vector))
        assert np.allclose(got, want, atol=1e-4) or np.allclose(got, -want, atol=1e-4)

    def test_inverse_mode_reports_lu_factors(self) -> None:
        response = run(mode="smallest")
        lower = np.asarray(response.result["L"], dtype=float)
        upper = np.asarray(response.result["U"], dtype=float)
        matrix = np.asarray(SYMMETRIC, dtype=float)
        permutation = response.result["permutation"]
        assert np.allclose(lower @ upper, matrix[permutation], atol=1e-9)
        assert np.allclose(np.diag(lower), 1.0)

    def test_rayleigh_quotient_and_residual(self) -> None:
        response = run()
        vector = np.asarray(response.result["eigenvector"], dtype=float)
        matrix = np.asarray(SYMMETRIC, dtype=float)
        quotient = float(vector @ (matrix @ vector) / (vector @ vector))
        assert response.result["rayleigh_quotient"] == pytest.approx(quotient, rel=1e-12)
        assert response.result["eigenvalue"] == pytest.approx(quotient, rel=1e-12)
        assert response.result["residual_norm"] < 1e-6

    def test_convergence_ratio_matches_eigenvalues(self) -> None:
        response = run()
        magnitudes = np.sort(np.abs(np.linalg.eigvals(np.asarray(SYMMETRIC, dtype=float))))[::-1]
        assert response.result["convergence_ratio"] == pytest.approx(
            float(magnitudes[1] / magnitudes[0]), rel=1e-9
        )

    def test_tables_and_steps(self) -> None:
        response = run()
        titles = [table.title for table in response.tables]
        assert titles == ["Power iteration", "Eigenpair verification"]
        table = response.tables[0]
        assert table.columns == [
            "Iteration",
            "A x",
            "x (normalised)",
            "lambda estimate",
            "Error",
        ]
        assert table.rows[0][0] == 0
        first = next(step for step in response.steps if step.title.startswith("First iteration"))
        assert r"y^{(1)} = A x^{(0)}" in first.latex
        assert any(step.title == "Convergence ratio" for step in response.steps)

    def test_plot_has_reference_and_semilog_error(self) -> None:
        response = run()
        names = [trace["name"] for trace in response.plot.traces]
        assert names == ["lambda estimate", "true lambda (numpy)", "error"]
        assert response.plot.layout["yaxis2"]["type"] == "log"
        assert response.result["true_eigenvalue"] == pytest.approx(
            float(np.max(np.abs(np.linalg.eigvals(np.asarray(SYMMETRIC, dtype=float))))),
            abs=1e-9,
        )

    def test_equal_magnitude_warns_and_does_not_converge(self) -> None:
        response = run(
            matrix=EQUAL_MAGNITUDE,
            initial_vector=[1.0, 0.0],
            tolerance=1e-10,
            max_iterations=20,
        )
        assert response.result["equal_magnitude"] is True
        assert response.status in {SolveStatus.MAX_ITER, SolveStatus.DIVERGED}
        assert any("equal magnitude" in warning for warning in response.warnings)

    def test_complex_dominant_warns(self) -> None:
        response = run(matrix=COMPLEX_ROTATION, initial_vector=[1.0, 0.0], max_iterations=20)
        assert response.result["complex_dominant"] is True
        assert response.status in {SolveStatus.MAX_ITER, SolveStatus.DIVERGED}
        assert any("complex" in warning.lower() for warning in response.warnings)

    def test_no_component_along_eigenvector_fails(self) -> None:
        response = run(matrix=[[2.0, 0.0], [0.0, 1.0]], initial_vector=[0.0, 1.0])
        assert response.status == SolveStatus.FAILED
        assert "no component" in response.warnings[0].lower()

    def test_singular_matrix_in_inverse_mode_fails(self) -> None:
        response = run(matrix=SINGULAR, initial_vector=[1.0, 1.0], mode="smallest")
        assert response.status == SolveStatus.FAILED
        assert response.result["singular"] is True
        assert "singular" in response.warnings[0].lower()

    def test_zero_initial_vector_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="zero vector"):
            run(initial_vector=[0.0, 0.0, 0.0])

    def test_non_square_matrix_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="square"):
            run(matrix=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

    def test_wrong_length_initial_vector_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="initial vector"):
            run(initial_vector=[1.0, 1.0])

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["matrix"]
            assert cleaned["mode"] in {"largest", "smallest"}


class TestPowerMethodApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "matrix": SYMMETRIC,
        "initial_vector": None,
        "mode": "largest",
        "tolerance": 1e-8,
        "max_iterations": 200,
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/power_method", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["eigenvalue"] == pytest.approx(
            float(np.max(np.abs(np.linalg.eigvals(np.asarray(SYMMETRIC, dtype=float))))),
            abs=1e-6,
        )
        assert "def solve" in body["python_source"]

    def test_zero_initial_vector_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/power_method",
            json={**self.PAYLOAD, "initial_vector": [0.0, 0.0, 0.0]},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_no_component_is_200_failed(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/power_method",
            json={
                **self.PAYLOAD,
                "matrix": [[2.0, 0.0], [0.0, 1.0]],
                "initial_vector": [0.0, 1.0],
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "power_method")
        assert method["status"] == "available"
        assert method["chapter"] == "ch2_linear"
