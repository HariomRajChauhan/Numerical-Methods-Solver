"""Tests for the Gauss-Jordan solver (reduced row-echelon form).

Covers the direct solver contract, automatic partial pivoting, the singular /
inconsistent failure paths (HTTP-200 ``failed``), input validation (HTTP 400)
and a comparison against ``numpy.linalg.solve``.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch2_linear.gauss_jordan import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CLASSIC_MATRIX = [[2.0, 1.0, -1.0], [-3.0, -1.0, 2.0], [-2.0, 1.0, 2.0]]
CLASSIC_RHS = [8.0, -11.0, -3.0]
CLASSIC_SOLUTION = [2.0, 3.0, -1.0]

ZERO_PIVOT_MATRIX = [[0.0, 2.0, 1.0], [1.0, 1.0, 0.0], [2.0, 1.0, 1.0]]
ZERO_PIVOT_RHS = [3.0, 2.0, 4.0]
ZERO_PIVOT_SOLUTION = [1.0, 1.0, 1.0]

NUMPY_CASES: dict[str, tuple[list[list[float]], list[float]]] = {
    "classic": (CLASSIC_MATRIX, CLASSIC_RHS),
    "zero_leading_pivot": (ZERO_PIVOT_MATRIX, ZERO_PIVOT_RHS),
    "diagonally_dominant": ([[4, 1, 1], [1, 5, 2], [1, 2, 6]], [9.0, 17.0, 23.0]),
    "tridiagonal_4x4": (
        [[4, 1, 0, 0], [1, 5, 1, 0], [0, 1, 6, 1], [0, 0, 1, 4]],
        [1.0, 2.0, 3.0, 4.0],
    ),
}

SINGULAR_MATRIX = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [1.0, 1.0, 1.0]]


def run(**overrides: Any):
    """Solve the classic system with optional input overrides."""
    inputs: dict[str, Any] = {
        "matrix": [list(row) for row in CLASSIC_MATRIX],
        "vector": list(CLASSIC_RHS),
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestGaussJordanSolver:
    def test_converges_to_known_solution(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["classification"] == "unique"
        assert np.allclose(response.result["solution_vector"], CLASSIC_SOLUTION, atol=1e-9)
        assert np.allclose(response.result["solution_vector"], [2.0, 3.0, -1.0], atol=1e-6)
        assert response.result["residual_norm"] < 1e-9

    def test_returns_full_contract(self) -> None:
        response = run()
        assert response.method == "gauss_jordan"
        assert set(response.result) >= {
            "solution",
            "solution_vector",
            "classification",
            "pivoting",
            "condition_number",
            "residual_norm",
            "row_swaps",
            "variable_order",
        }
        assert len(response.tables) == 2
        assert response.tables[0].columns == ["Operation", "Pivot row", "Multiplier m"]
        assert len(response.plot.traces) == 2
        assert "title" in response.plot.layout

    def test_steps_show_normalisation_and_rref(self) -> None:
        titles = [step.title for step in run().steps]
        assert titles[0] == "Setup"
        assert any(title.startswith("Normalise pivot row") for title in titles)
        assert "Reduced row-echelon form" in titles
        assert titles[-1] == "Verification"

    def test_partial_pivoting_is_applied_automatically(self) -> None:
        response = run(
            matrix=[list(row) for row in ZERO_PIVOT_MATRIX],
            vector=list(ZERO_PIVOT_RHS),
        )
        titles = [step.title for step in response.steps]
        assert response.result["row_swaps"] >= 1
        assert any(title.startswith("Partial pivot") for title in titles)
        assert np.allclose(response.result["solution_vector"], [1.0, 1.0, 1.0], atol=1e-9)

    def test_singular_matrix_has_infinite_solutions(self) -> None:
        response = run(matrix=SINGULAR_MATRIX, vector=[1.0, 2.0, 1.0])
        assert response.status == SolveStatus.FAILED
        assert response.result["classification"] == "infinite"
        assert any("infinitely many" in warning for warning in response.warnings)

    def test_inconsistent_system_has_no_solution(self) -> None:
        response = run(matrix=SINGULAR_MATRIX, vector=[1.0, 3.0, 1.0])
        assert response.status == SolveStatus.FAILED
        assert response.result["classification"] == "none"
        assert any("inconsistent" in warning for warning in response.warnings)

    @pytest.mark.parametrize("case", list(NUMPY_CASES))
    def test_matches_numpy(self, case: str) -> None:
        matrix, rhs = NUMPY_CASES[case]
        response = run(matrix=[list(row) for row in matrix], vector=list(rhs))
        assert response.status == SolveStatus.CONVERGED
        expected = np.linalg.solve(np.asarray(matrix, dtype=float), np.asarray(rhs, dtype=float))
        assert np.allclose(response.result["solution_vector"], expected, atol=1e-8)

    def test_non_square_matrix_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="square"):
            run(matrix=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], vector=[1.0, 2.0])

    def test_mismatched_rhs_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="entries"):
            run(vector=[1.0, 2.0])

    def test_system_too_small_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="at least"):
            run(matrix=[[2.0]], vector=[1.0])

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["matrix"]
            assert cleaned["vector"]


class TestGaussJordanApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "matrix": CLASSIC_MATRIX,
        "vector": CLASSIC_RHS,
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/gauss_jordan", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["pseudocode"].startswith("GaussJordan(")
        assert "def solve" in body["python_source"]

    def test_singular_system_is_200_failed(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/gauss_jordan",
            json={**self.PAYLOAD, "matrix": SINGULAR_MATRIX, "vector": [1.0, 2.0, 1.0]},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_non_square_matrix_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/gauss_jordan",
            json={**self.PAYLOAD, "matrix": [[1, 2, 3], [4, 5, 6]]},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "gauss_jordan")
        assert method["status"] == "available"
        assert method["chapter"] == "ch2_linear"

    def test_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/gauss_jordan").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == ["matrix", "vector", "decimal_precision"]
        assert meta["formulas"]
        assert meta["examples"]
        assert meta["theory"]
