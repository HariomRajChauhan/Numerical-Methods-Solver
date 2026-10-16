"""Tests for the Phase 5 'coming soon' stubs.

Every syllabus method that has no solver yet must be registered as a
``coming_soon`` placeholder: visible in the catalogue and chapter navigation,
with readable theory/pseudocode, but refusing to solve with HTTP 409.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import registry
from app.core.models import Chapter, MethodStatus

# The exact ENSH 252 syllabus: chapter -> stub method ids. ``bisection`` is the
# one already implemented, so it is intentionally absent here.
EXPECTED_STUBS: dict[Chapter, list[str]] = {
    Chapter.CH1_NONLINEAR: [
        "errors_accuracy",
        "false_position",
        "secant",
        "newton_raphson",
        "fixed_point",
        "method_comparison",
        "nonlinear_system_direct",
        "nonlinear_system_newton",
    ],
    Chapter.CH2_LINEAR: [
        "gauss_jordan",
        "gauss_elimination",
        "matrix_inverse",
        "doolittle",
        "crout",
        "jacobi",
        "gauss_seidel",
        "power_method",
    ],
    Chapter.CH3_INTERPOLATION: [
        "finite_differences",
        "newton_forward",
        "newton_backward",
        "stirling",
        "bessel",
        "newton_divided_difference",
        "lagrange",
        "least_squares",
        "cubic_spline",
    ],
    Chapter.CH4_DIFF_INTEGRATION: [
        "numerical_differentiation",
        "local_extrema",
        "newton_cotes",
        "trapezoidal",
        "simpson_13",
        "simpson_38",
        "boole",
        "weddle",
        "romberg",
        "gauss_legendre",
    ],
    Chapter.CH5_ODE: [
        "taylor_series",
        "euler",
        "runge_kutta_2",
        "runge_kutta_4",
        "ode_system_rk",
        "ode_second_order_rk",
        "bvp_shooting",
        "bvp_finite_difference",
    ],
    Chapter.CH6_PDE: [
        "pde_classification",
        "fd_approximations",
        "laplace",
        "poisson",
        "heat_bendre_schmidt",
        "heat_crank_nicolson",
        "wave",
    ],
}

ALL_STUB_IDS = [method_id for ids in EXPECTED_STUBS.values() for method_id in ids]


@pytest.fixture(scope="module")
def catalogue(client: TestClient) -> dict:
    response = client.get("/api/methods")
    assert response.status_code == 200
    return response.json()


def test_all_expected_stubs_are_registered(catalogue: dict) -> None:
    registered = {method["id"] for method in catalogue["methods"]}
    assert registered.issuperset(ALL_STUB_IDS)


def test_catalog_matches_syllabus_exactly(catalogue: dict) -> None:
    registered = {method["id"] for method in catalogue["methods"]}
    assert registered == set(ALL_STUB_IDS) | {"bisection"}


def test_ids_are_unique() -> None:
    assert len(ALL_STUB_IDS) == len(set(ALL_STUB_IDS))


@pytest.mark.parametrize("method_id", ALL_STUB_IDS)
def test_stub_is_coming_soon_with_content(catalogue: dict, method_id: str) -> None:
    method = next(m for m in catalogue["methods"] if m["id"] == method_id)
    assert method["status"] == "coming_soon"
    assert method["name"]
    assert method["summary"]
    assert method["theory"]
    assert method["pseudocode"]
    assert method["input_schema"] == []


@pytest.mark.parametrize("chapter,method_ids", list(EXPECTED_STUBS.items()))
def test_stub_chapters_are_correct(catalogue: dict, chapter: Chapter, method_ids: list[str]) -> None:
    for method_id in method_ids:
        method = next(m for m in catalogue["methods"] if m["id"] == method_id)
        assert method["chapter"] == chapter.value


def test_chapter_counts_include_stubs(catalogue: dict) -> None:
    chapters = {card["id"]: card for card in catalogue["chapters"]}
    for chapter, method_ids in EXPECTED_STUBS.items():
        card = chapters[chapter.value]
        assert card["method_count"] >= len(method_ids)
    # Only bisection is implemented in Phase 5, so exactly one available method.
    total_available = sum(card["available_count"] for card in catalogue["chapters"])
    assert total_available == 1


def test_available_and_coming_soon_are_the_only_statuses(catalogue: dict) -> None:
    statuses = {method["status"] for method in catalogue["methods"]}
    assert statuses <= {"available", "coming_soon"}


def test_stub_detail_endpoint_returns_meta(client: TestClient) -> None:
    response = client.get("/api/methods/newton_raphson")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "newton_raphson"
    assert body["status"] == MethodStatus.COMING_SOON
    assert body["chapter"] == Chapter.CH1_NONLINEAR
    assert body["chapter_title"] == "Non-linear Equations"
    assert body["pseudocode"]


@pytest.mark.parametrize("method_id", ALL_STUB_IDS)
def test_solving_a_stub_is_conflict(client: TestClient, method_id: str) -> None:
    response = client.post(f"/api/solve/{method_id}", json={})
    assert response.status_code == 409
    assert response.json()["code"] == "method_unavailable"


def test_stubs_have_no_solver_in_registry() -> None:
    for method_id in ALL_STUB_IDS:
        assert registry.get_entry(method_id).solver is None
