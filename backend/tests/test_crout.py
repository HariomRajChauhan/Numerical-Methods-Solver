"""Tests for the Crout LU-decomposition solver (unit upper-triangular U)."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch2_linear.crout import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CASES: dict[str, tuple[list[list[float]], list[float]]] = {
    "classic": ([[2, 1, -1], [-3, -1, 2], [-2, 1, 2]], [8.0, -11.0, -3.0]),
    "diagonally_dominant": ([[4, 1, 1], [1, 5, 2], [1, 2, 6]], [9.0, 17.0, 23.0]),
    "tridiagonal_4x4": (
        [[4, 1, 0, 0], [1, 5, 1, 0], [0, 1, 6, 1], [0, 0, 1, 4]],
        [1.0, 2.0, 3.0, 4.0],
    ),
}

ZERO_PIVOT = ([[0.0, 2.0, 1.0], [1.0, 1.0, 0.0], [2.0, 1.0, 1.0]], [3.0, 2.0, 4.0])
SINGULAR = ([[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [1.0, 1.0, 1.0]], [1.0, 2.0, 1.0])


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "matrix": CASES["classic"][0],
        "vector": CASES["classic"][1],
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestCroutSolver:
    def test_solves_classic_system(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert np.allclose(response.result["solution_vector"], [2.0, 3.0, -1.0], atol=1e-9)
        assert response.result["residual_norm"] < 1e-9

    @pytest.mark.parametrize("case", list(CASES))
    def test_matches_numpy(self, case: str) -> None:
        matrix, rhs = CASES[case]
        response = run(matrix=matrix, vector=rhs)
        assert response.status == SolveStatus.CONVERGED
        expected = np.linalg.solve(np.asarray(matrix, dtype=float), np.asarray(rhs, dtype=float))
        assert np.allclose(response.result["solution_vector"], expected, atol=1e-8)

    @pytest.mark.parametrize("case", list(CASES))
    def test_factorisation_reconstructs_matrix(self, case: str) -> None:
        matrix, rhs = CASES[case]
        response = run(matrix=matrix, vector=rhs)
        lower = np.asarray(response.result["L"], dtype=float)
        upper = np.asarray(response.result["U"], dtype=float)
        assert np.allclose(lower @ upper, np.asarray(matrix, dtype=float), atol=1e-9)
        assert response.result["factorisation_error"] < 1e-9

    def test_upper_is_unit_triangular(self) -> None:
        response = run()
        upper = np.asarray(response.result["U"], dtype=float)
        assert np.allclose(np.diag(upper), np.ones(3))
        assert np.allclose(np.tril(upper, -1), 0.0)
        lower = np.asarray(response.result["L"], dtype=float)
        assert np.allclose(np.triu(lower, 1), 0.0)

    def test_returns_full_contract(self) -> None:
        response = run()
        assert response.method == "crout"
        assert response.result["factorisation"] == "crout"
        assert [table.title for table in response.tables] == [
            "L factor (lower triangular)",
            "U factor (unit upper triangular)",
            "Forward and back substitution",
            "Solution and verification",
        ]
        assert len(response.plot.traces) == 2

    def test_zero_pivot_fails_and_suggests_pivoting(self) -> None:
        response = run(matrix=ZERO_PIVOT[0], vector=ZERO_PIVOT[1])
        assert response.status == SolveStatus.FAILED
        message = response.warnings[0].lower()
        assert "zero pivot" in message
        assert "pivot" in message and "gauss elimination" in message
        assert response.result["pivot_step"] == 1

    def test_singular_zero_pivot_reports_infinite(self) -> None:
        response = run(matrix=SINGULAR[0], vector=SINGULAR[1])
        assert response.status == SolveStatus.FAILED
        assert response.result["classification"] == "infinite"

    def test_non_square_matrix_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="square"):
            run(matrix=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], vector=[1.0, 2.0])

    def test_mismatched_rhs_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="entries"):
            run(vector=[1.0, 2.0])

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["matrix"] and cleaned["vector"]


class TestCroutApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "matrix": CASES["classic"][0],
        "vector": CASES["classic"][1],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/crout", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["pseudocode"].startswith("Crout(")
        assert "def solve" in body["python_source"]

    def test_zero_pivot_is_200_failed(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/crout",
            json={**self.PAYLOAD, "matrix": ZERO_PIVOT[0], "vector": ZERO_PIVOT[1]},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "crout")
        assert method["status"] == "available"
        assert method["chapter"] == "ch2_linear"
