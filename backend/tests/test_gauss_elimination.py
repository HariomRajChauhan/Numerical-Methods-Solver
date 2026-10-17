"""Tests for the Gauss elimination solver (none / partial / complete pivoting).

Covers the direct solver contract, the three pivoting strategies, the singular /
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
from app.solvers.ch2_linear.gauss_elimination import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

CLASSIC_MATRIX = [[2.0, 1.0, -1.0], [-3.0, -1.0, 2.0], [-2.0, 1.0, 2.0]]
CLASSIC_RHS = [8.0, -11.0, -3.0]
CLASSIC_SOLUTION = [2.0, 3.0, -1.0]

ZERO_PIVOT_MATRIX = [[0.0, 2.0, 1.0], [1.0, 1.0, 0.0], [2.0, 1.0, 1.0]]
ZERO_PIVOT_RHS = [3.0, 2.0, 4.0]
ZERO_PIVOT_SOLUTION = [1.0, 1.0, 1.0]

# (matrix, rhs) pairs of guaranteed non-singular systems for the numpy comparison.
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
        "pivoting": "partial",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestGaussEliminationSolver:
    def test_converges_to_known_solution(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert response.result["classification"] == "unique"
        solution = response.result["solution_vector"]
        assert np.allclose(solution, CLASSIC_SOLUTION, atol=1e-9)
        assert response.result["residual_norm"] < 1e-9

    def test_returns_full_contract(self) -> None:
        response = run()
        assert response.method == "gauss_elimination"
        assert set(response.result) >= {
            "solution",
            "solution_vector",
            "classification",
            "pivoting",
            "condition_number",
            "residual_norm",
            "row_swaps",
            "column_swaps",
            "variable_order",
        }
        assert np.allclose(
            list(response.result["solution"].values()), CLASSIC_SOLUTION, atol=1e-9
        )
        assert len(response.tables) == 2
        assert response.tables[0].columns == ["Operation", "Pivot row", "Multiplier m"]
        assert len(response.plot.traces) == 2
        assert "title" in response.plot.layout

    def test_steps_show_row_operations_and_back_substitution(self) -> None:
        titles = [step.title for step in run().steps]
        assert titles[0] == "Setup"
        assert any(title.startswith("Eliminate column") for title in titles)
        assert sum(title.startswith("Back-substitute") for title in titles) == 3
        assert titles[-1] == "Verification"

    def test_operations_table_lists_multipliers(self) -> None:
        operations = run().tables[0].rows
        assert operations
        assert any("<-" in str(row[0]) for row in operations)

    @pytest.mark.parametrize("pivoting", ["partial", "complete"])
    def test_zero_pivot_is_repaired_by_pivoting(self, pivoting: str) -> None:
        response = run(
            matrix=[list(row) for row in ZERO_PIVOT_MATRIX],
            vector=list(ZERO_PIVOT_RHS),
            pivoting=pivoting,
        )
        assert response.status == SolveStatus.CONVERGED
        assert np.allclose(response.result["solution_vector"], ZERO_PIVOT_SOLUTION, atol=1e-9)
        assert response.result["row_swaps"] >= 1

    def test_complete_pivoting_tracks_variable_order(self) -> None:
        response = run(
            matrix=[list(row) for row in ZERO_PIVOT_MATRIX],
            vector=list(ZERO_PIVOT_RHS),
            pivoting="complete",
        )
        assert response.result["column_swaps"] >= 1
        assert sorted(response.result["variable_order"]) == ["x1", "x2", "x3"]
        assert np.allclose(response.result["solution_vector"], ZERO_PIVOT_SOLUTION, atol=1e-9)

    def test_none_pivoting_fails_on_zero_pivot(self) -> None:
        response = run(
            matrix=[list(row) for row in ZERO_PIVOT_MATRIX],
            vector=list(ZERO_PIVOT_RHS),
            pivoting="none",
        )
        assert response.status == SolveStatus.FAILED
        assert response.result["classification"] == "unique"
        assert any("zero pivot" in warning.lower() for warning in response.warnings)

    def test_singular_matrix_has_infinite_solutions(self) -> None:
        response = run(matrix=SINGULAR_MATRIX, vector=[1.0, 2.0, 1.0])
        assert response.status == SolveStatus.FAILED
        assert response.result["classification"] == "infinite"
        assert response.result["rank"] < 3
        assert any("infinitely many" in warning for warning in response.warnings)

    def test_inconsistent_system_has_no_solution(self) -> None:
        response = run(matrix=SINGULAR_MATRIX, vector=[1.0, 3.0, 1.0])
        assert response.status == SolveStatus.FAILED
        assert response.result["classification"] == "none"
        assert response.result["rank_augmented"] > response.result["rank"]
        assert any("inconsistent" in warning for warning in response.warnings)

    @pytest.mark.parametrize("pivoting", ["none", "partial", "complete"])
    @pytest.mark.parametrize("case", list(NUMPY_CASES))
    def test_matches_numpy(self, case: str, pivoting: str) -> None:
        if case == "zero_leading_pivot" and pivoting == "none":
            pytest.skip("a zero leading pivot cannot be solved without pivoting")
        matrix, rhs = NUMPY_CASES[case]
        response = run(matrix=[list(row) for row in matrix], vector=list(rhs), pivoting=pivoting)
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

    def test_condition_number_is_reported(self) -> None:
        hilbert = [[1.0, 0.5, 1 / 3], [0.5, 1 / 3, 0.25], [1 / 3, 0.25, 0.2]]
        response = run(matrix=hilbert, vector=[1.0, 1.0, 1.0])
        assert response.status == SolveStatus.CONVERGED
        assert response.result["condition_number"] and response.result["condition_number"] > 100

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["matrix"]
            assert cleaned["vector"]


class TestGaussEliminationApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "matrix": CLASSIC_MATRIX,
        "vector": CLASSIC_RHS,
        "pivoting": "partial",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/gauss_elimination", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["pseudocode"].startswith("GaussElimination(")
        assert "def solve" in body["python_source"]

    def test_singular_system_is_200_failed(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/gauss_elimination",
            json={**self.PAYLOAD, "matrix": SINGULAR_MATRIX, "vector": [1.0, 3.0, 1.0]},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_non_square_matrix_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/gauss_elimination",
            json={**self.PAYLOAD, "matrix": [[1, 2, 3], [4, 5, 6]]},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "gauss_elimination")
        assert method["status"] == "available"
        assert method["chapter"] == "ch2_linear"

    def test_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/gauss_elimination").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == ["matrix", "vector", "pivoting", "decimal_precision"]
        assert meta["formulas"]
        assert meta["examples"]
        assert meta["theory"]
