"""Tests for the Jacobi iterative solver."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch2_linear.jacobi import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

DOMINANT = ([[4.0, 1.0, 1.0], [1.0, 5.0, 2.0], [1.0, 2.0, 6.0]], [9.0, 17.0, 23.0])
SPD_4X4 = ([[4.0, 1.0, 0.0, 0.0], [1.0, 4.0, 1.0, 0.0], [0.0, 1.0, 4.0, 1.0], [0.0, 0.0, 1.0, 3.0]], [6.0, 12.0, 18.0, 15.0])
NON_DOMINANT = ([[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [1.0, 1.0, 1.0]], [1.0, 2.0, 1.0])
ZERO_DIAGONAL = ([[0.0, 2.0, 1.0], [1.0, 1.0, 0.0], [2.0, 1.0, 1.0]], [3.0, 2.0, 4.0])

CASES: dict[str, tuple[list[list[float]], list[float]]] = {
    "dominant": DOMINANT,
    "spd_4x4": SPD_4X4,
}


def run(**overrides: Any):
    matrix, rhs = DOMINANT
    inputs: dict[str, Any] = {
        "matrix": [list(row) for row in matrix],
        "vector": list(rhs),
        "initial_guess": [0.0, 0.0, 0.0],
        "tolerance": 1e-6,
        "max_iterations": 100,
        "stopping_criterion": "absolute",
        "compare": True,
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestJacobiSolver:
    def test_converges_to_expected_solution(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        assert np.allclose(response.result["solution_vector"], [1.0, 2.0, 3.0], atol=1e-4)
        assert response.result["solution"]["x1"] == pytest.approx(1.0, abs=1e-4)

    @pytest.mark.parametrize("case", list(CASES))
    def test_matches_numpy(self, case: str) -> None:
        matrix, rhs = CASES[case]
        response = run(
            matrix=[list(row) for row in matrix],
            vector=list(rhs),
            initial_guess=None,
            tolerance=1e-10,
        )
        assert response.status == SolveStatus.CONVERGED
        expected = np.linalg.solve(np.asarray(matrix, dtype=float), np.asarray(rhs, dtype=float))
        assert np.allclose(response.result["solution_vector"], expected, atol=1e-6)

    def test_diagonal_dominance_detected(self) -> None:
        response = run()
        assert response.result["diagonally_dominant"] is True
        assert response.result["spectral_radius"] < 1.0

    def test_non_dominant_warns_but_runs(self) -> None:
        response = run(matrix=NON_DOMINANT[0], vector=NON_DOMINANT[1], max_iterations=50)
        assert response.result["diagonally_dominant"] is False
        assert response.status == SolveStatus.DIVERGED
        assert any("not strictly diagonally dominant" in warning for warning in response.warnings)

    def test_max_iterations_status(self) -> None:
        response = run(max_iterations=2, compare=False)
        assert response.status == SolveStatus.MAX_ITER
        assert response.result["iterations"] == 2

    def test_zero_diagonal_fails(self) -> None:
        response = run(matrix=ZERO_DIAGONAL[0], vector=ZERO_DIAGONAL[1])
        assert response.status == SolveStatus.FAILED
        assert "zero" in response.warnings[0].lower()
        assert "gauss elimination" in response.warnings[0].lower()

    def test_returns_full_contract(self) -> None:
        response = run()
        assert response.method == "jacobi"
        assert set(response.result) >= {
            "solution",
            "solution_vector",
            "iterations",
            "final_error",
            "stopping_criterion",
            "spectral_radius",
            "diagonally_dominant",
            "comparison",
        }
        assert [table.title for table in response.tables] == [
            "Diagonal dominance check",
            "Iterations",
            "Iteration-count comparison",
        ]

    def test_first_iteration_is_worked(self) -> None:
        response = run()
        first = next(step for step in response.steps if step.title.startswith("First iteration"))
        assert r"x_{1}^{(1)}" in first.latex
        assert "x_{3}" in first.latex

    def test_iteration_table_columns(self) -> None:
        response = run()
        table = next(table for table in response.tables if table.title == "Iterations")
        assert table.columns[:4] == ["Iteration", "x1", "x2", "x3"]
        assert table.rows[0][0] == 0

    def test_error_plot_uses_log_axis(self) -> None:
        response = run()
        assert response.plot.layout["yaxis"]["type"] == "log"
        names = [trace["name"] for trace in response.plot.traces]
        assert "Jacobi" in names

    def test_comparison_with_gauss_seidel_runs_fewer_iterations(self) -> None:
        response = run()
        comparison = {row[0]: row for row in response.result["comparison"]}
        assert set(comparison) == {"Jacobi", "Gauss-Seidel"}
        assert comparison["Gauss-Seidel"][1] < comparison["Jacobi"][1]

    def test_comparison_can_be_disabled(self) -> None:
        response = run(compare=False)
        assert "comparison" not in response.result
        assert [table.title for table in response.tables] == [
            "Diagonal dominance check",
            "Iterations",
        ]

    def test_bad_initial_guess_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="initial guess"):
            run(initial_guess=[0.0, 0.0])

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


class TestJacobiApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "matrix": DOMINANT[0],
        "vector": DOMINANT[1],
        "initial_guess": [0.0, 0.0, 0.0],
        "tolerance": 1e-6,
        "max_iterations": 100,
        "stopping_criterion": "absolute",
        "compare": True,
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/jacobi", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["python_source"]

    def test_non_convergence_is_200_diverged(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/jacobi",
            json={**self.PAYLOAD, "matrix": NON_DOMINANT[0], "vector": NON_DOMINANT[1]},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "diverged"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "jacobi")
        assert method["status"] == "available"
        assert method["chapter"] == "ch2_linear"
