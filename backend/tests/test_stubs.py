"""Tests for the 'coming soon' stubs and the implemented-method catalogue.

Every syllabus method that has no solver yet must be registered as a
``coming_soon`` placeholder: visible in the catalogue and chapter navigation,
with readable theory/pseudocode, but refusing to solve with HTTP 409. Methods
that have been implemented must instead be ``available`` and expose an input
schema.

The full ENSH 252 syllabus is listed once in ``SYLLABUS``; implemented ids are
moved out of the stub expectations by editing ``IMPLEMENTED``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import registry
from app.core.models import Chapter, MethodStatus

# The complete ENSH 252 syllabus: chapter -> every method id in that chapter.
SYLLABUS: dict[Chapter, list[str]] = {
    Chapter.CH1_NONLINEAR: [
        "errors_accuracy",
        "bisection",
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

# Methods with a real solver (updated as chapters are implemented).
IMPLEMENTED: dict[Chapter, list[str]] = {
    Chapter.CH1_NONLINEAR: [
        "errors_accuracy",
        "bisection",
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
    ],
}

IMPLEMENTED_IDS = {method_id for ids in IMPLEMENTED.values() for method_id in ids}
ALL_SYLLABUS_IDS = [method_id for ids in SYLLABUS.values() for method_id in ids]

# Stubs = syllabus methods without a solver yet.
EXPECTED_STUBS: dict[Chapter, list[str]] = {
    chapter: [method_id for method_id in ids if method_id not in IMPLEMENTED_IDS]
    for chapter, ids in SYLLABUS.items()
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
    assert registered == set(ALL_SYLLABUS_IDS)


def test_ids_are_unique() -> None:
    assert len(ALL_SYLLABUS_IDS) == len(set(ALL_SYLLABUS_IDS))


def test_implemented_methods_are_available(catalogue: dict) -> None:
    for method_id in sorted(IMPLEMENTED_IDS):
        method = next(m for m in catalogue["methods"] if m["id"] == method_id)
        assert method["status"] == "available"
        assert method["input_schema"], f"{method_id} must expose an input schema"


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
    for chapter, method_ids in SYLLABUS.items():
        card = chapters[chapter.value]
        assert card["method_count"] >= len(method_ids)
        assert card["method_count"] == len(method_ids)
    total_available = sum(card["available_count"] for card in catalogue["chapters"])
    assert total_available == len(IMPLEMENTED_IDS)


def test_available_and_coming_soon_are_the_only_statuses(catalogue: dict) -> None:
    statuses = {method["status"] for method in catalogue["methods"]}
    assert statuses <= {"available", "coming_soon"}


def test_stub_detail_endpoint_returns_meta(client: TestClient) -> None:
    response = client.get("/api/methods/trapezoidal")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "trapezoidal"
    assert body["status"] == MethodStatus.COMING_SOON
    assert body["chapter"] == Chapter.CH4_DIFF_INTEGRATION
    assert body["chapter_title"] == "Differentiation & Integration"
    assert body["pseudocode"]


@pytest.mark.parametrize("method_id", ALL_STUB_IDS)
def test_solving_a_stub_is_conflict(client: TestClient, method_id: str) -> None:
    response = client.post(f"/api/solve/{method_id}", json={})
    assert response.status_code == 409
    assert response.json()["code"] == "method_unavailable"


def test_stubs_have_no_solver_in_registry() -> None:
    for method_id in ALL_STUB_IDS:
        assert registry.get_entry(method_id).solver is None
