"""Tests for the matrix-inversion solver (Gauss-Jordan on [A | I])."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy import linalg as scipy_linalg

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch2_linear.matrix_inverse import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

INVERTIBLE_CASES: dict[str, list[list[float]]] = {
    "classic_3x3": [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]],
    "simple_2x2": [[4, 7], [2, 6]],
    "zero_leading_pivot": [[0, 2, 1], [1, 1, 0], [2, 1, 1]],
    "diagonally_dominant": [[4, 1, 1], [1, 5, 2], [1, 2, 6]],
    "tridiagonal_4x4": [[4, 1, 0, 0], [1, 5, 1, 0], [0, 1, 6, 1], [0, 0, 1, 4]],
}

SINGULAR = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [1.0, 1.0, 1.0]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {"matrix": INVERTIBLE_CASES["classic_3x3"], "decimal_precision": 6}
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestMatrixInverseSolver:
    def test_inverts_classic_matrix(self) -> None:
        response = run()
        assert response.status == SolveStatus.CONVERGED
        expected = np.linalg.inv(np.asarray(INVERTIBLE_CASES["classic_3x3"], dtype=float))
        assert np.allclose(response.result["inverse"], expected, atol=1e-9)

    @pytest.mark.parametrize("case", list(INVERTIBLE_CASES))
    def test_matches_numpy_and_scipy(self, case: str) -> None:
        matrix = INVERTIBLE_CASES[case]
        response = run(matrix=matrix)
        assert response.status == SolveStatus.CONVERGED
        array = np.asarray(matrix, dtype=float)
        assert np.allclose(response.result["inverse"], np.linalg.inv(array), atol=1e-8)
        assert np.allclose(response.result["inverse"], scipy_linalg.inv(array), atol=1e-8)

    def test_verification_product_is_identity(self) -> None:
        response = run()
        matrix = np.asarray(INVERTIBLE_CASES["classic_3x3"], dtype=float)
        product = matrix @ np.asarray(response.result["inverse"], dtype=float)
        assert np.allclose(product, np.eye(3), atol=1e-9)
        assert response.result["max_identity_error"] < 1e-9
        assert response.result["singular"] is False

    def test_returns_full_contract(self) -> None:
        response = run()
        assert response.method == "matrix_inverse"
        assert set(response.result) == {
            "inverse",
            "singular",
            "condition_number",
            "max_identity_error",
            "row_swaps",
        }
        assert [table.title for table in response.tables] == [
            "Row operations",
            "Inverse A^-1",
            "Verification A x A^-1",
        ]
        assert response.plot.traces[0]["type"] == "heatmap"
        assert "title" in response.plot.layout

    def test_auto_partial_pivoting(self) -> None:
        response = run(matrix=INVERTIBLE_CASES["zero_leading_pivot"])
        assert response.status == SolveStatus.CONVERGED
        assert response.result["row_swaps"] >= 1
        assert any(step.title.startswith("Partial pivot") for step in response.steps)

    def test_singular_matrix_fails(self) -> None:
        response = run(matrix=SINGULAR)
        assert response.status == SolveStatus.FAILED
        assert response.result["singular"] is True
        assert response.result["rank"] < 3
        assert any("singular" in warning.lower() for warning in response.warnings)

    def test_non_square_matrix_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="square"):
            run(matrix=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

    def test_too_small_matrix_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="at least"):
            run(matrix=[[2.0]])

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["matrix"]


class TestMatrixInverseApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "matrix": INVERTIBLE_CASES["classic_3x3"],
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/matrix_inverse", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["pseudocode"].startswith("Inverse(")
        assert "def solve" in body["python_source"]

    def test_singular_matrix_is_200_failed(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/matrix_inverse", json={**self.PAYLOAD, "matrix": SINGULAR}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    def test_non_square_matrix_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/matrix_inverse",
            json={**self.PAYLOAD, "matrix": [[1, 2, 3], [4, 5, 6]]},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "matrix_inverse")
        assert method["status"] == "available"
        assert method["chapter"] == "ch2_linear"

    def test_metadata_exposes_schema(self, client: TestClient) -> None:
        meta = client.get("/api/methods/matrix_inverse").json()
        keys = [field["key"] for field in meta["input_schema"]]
        assert keys == ["matrix", "decimal_precision"]
        assert meta["formulas"] and meta["examples"] and meta["theory"]
