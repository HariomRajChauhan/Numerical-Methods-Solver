"""Tests for the finite difference operator tables."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core.errors import InvalidInputError
from app.core.models import SolverLimits, SolveStatus
from app.core.validation import validate_inputs
from app.solvers.ch3_interpolation.finite_differences import META, solve

LIMITS = SolverLimits(timeout_seconds=10.0, max_iterations=10_000, max_matrix_size=50)

PARABOLA = [[0.0, 1.0], [1.0, 2.0], [2.0, 5.0], [3.0, 10.0]]
UNEVEN = [[0.0, 1.0], [1.0, 2.0], [3.0, 10.0]]


def run(**overrides: Any):
    inputs: dict[str, Any] = {
        "points": [list(point) for point in PARABOLA],
        "operator": "forward",
        "decimal_precision": 6,
    }
    inputs.update(overrides)
    return solve(inputs, LIMITS)


class TestFiniteDifferencesSolver:
    def test_forward_diagonal(self) -> None:
        response = run(operator="forward")
        assert response.status == SolveStatus.CONVERGED
        assert response.result["leading_differences"] == pytest.approx([1.0, 1.0, 2.0, 0.0])
        assert response.result["equal_spacing"] is True
        assert response.result["step"] == pytest.approx(1.0)

    def test_backward_diagonal(self) -> None:
        response = run(operator="backward")
        assert response.result["leading_differences"] == pytest.approx([10.0, 5.0, 2.0, 0.0])

    def test_central_diagonal(self) -> None:
        response = run(operator="central")
        assert response.result["leading_differences"] == pytest.approx([2.0, 3.0, 2.0, 0.0])

    def test_divided_diagonal_on_uneven_data(self) -> None:
        response = run(points=UNEVEN, operator="divided")
        assert response.status == SolveStatus.CONVERGED
        assert response.result["leading_differences"] == pytest.approx([1.0, 1.0, 1.0])
        assert response.result["equal_spacing"] is False

    def test_uneven_spacing_warns_but_runs(self) -> None:
        response = run(points=UNEVEN, operator="forward")
        assert response.status == SolveStatus.CONVERGED
        assert response.result["equal_spacing"] is False
        assert response.result["step"] is None
        assert any("equally spaced" in warning for warning in response.warnings)

    def test_divided_does_not_warn_on_spacing(self) -> None:
        response = run(points=UNEVEN, operator="divided")
        assert not any("equally spaced" in warning for warning in response.warnings)

    def test_duplicate_x_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="distinct"):
            run(points=[[0.0, 1.0], [0.0, 2.0], [3.0, 10.0]])

    def test_table_titles_present(self) -> None:
        response = run(operator="divided")
        titles = [table.title for table in response.tables]
        assert "Data points" in titles
        assert any("Divided difference" in title for title in titles)

    def test_all_examples_validate_against_schema(self) -> None:
        for example in META.examples:
            cleaned = validate_inputs(META, example.inputs, LIMITS)
            assert cleaned["points"]
            assert cleaned["operator"] in {"forward", "backward", "central", "divided"}


class TestFiniteDifferencesApi:
    PAYLOAD: ClassVar[dict[str, Any]] = {
        "points": [list(point) for point in PARABOLA],
        "operator": "forward",
        "decimal_precision": 6,
    }

    def test_solve_returns_contract(self, client: TestClient) -> None:
        response = client.post("/api/solve/finite_differences", json=self.PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "method", "status", "result", "steps", "tables", "plot",
            "errors", "warnings", "pseudocode", "python_source",
        }
        assert body["status"] == "converged"
        assert body["result"]["leading_differences"] == pytest.approx([1.0, 1.0, 2.0, 0.0])
        assert "def solve" in body["python_source"]

    def test_divided_on_uneven_is_ok(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/finite_differences",
            json={**self.PAYLOAD, "points": UNEVEN, "operator": "divided"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "converged"

    def test_bad_operator_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/finite_differences", json={**self.PAYLOAD, "operator": "banana"}
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_duplicate_x_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/solve/finite_differences",
            json={**self.PAYLOAD, "points": [[0.0, 1.0], [0.0, 2.0], [3.0, 10.0]]},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_catalog_lists_method_as_available(self, client: TestClient) -> None:
        body = client.get("/api/methods").json()
        method = next(m for m in body["methods"] if m["id"] == "finite_differences")
        assert method["status"] == "available"
        assert method["chapter"] == "ch3_interpolation"
