"""Tests for the method registry."""

from __future__ import annotations

from typing import Any

import pytest

from app.core import registry
from app.core.errors import MethodNotFoundError, RegistrationError
from app.core.models import (
    Chapter,
    InputField,
    MethodMeta,
    MethodStatus,
    SolveResponse,
    SolverLimits,
    SolveStatus,
)


def _meta(method_id: str = "test_method", *, status: MethodStatus = MethodStatus.AVAILABLE) -> MethodMeta:
    return MethodMeta(
        id=method_id,
        chapter=Chapter.CH1_NONLINEAR,
        name="Test Method",
        status=status,
        summary="A test method.",
        input_schema=[InputField(key="x0", label="Initial guess", type="number")],
    )


def _fake_solver(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    del limits
    return SolveResponse(method="test_method", status=SolveStatus.CONVERGED, result={"x": inputs["x0"]})


class TestRegistry:
    def test_register_and_get_entry(self, registry_guard: None) -> None:
        del registry_guard
        registry.register(_meta())(_fake_solver)
        entry = registry.get_entry("test_method")
        assert entry.meta.name == "Test Method"
        assert entry.solver is _fake_solver

    def test_unknown_id_raises_not_found(self, registry_guard: None) -> None:
        del registry_guard
        with pytest.raises(MethodNotFoundError, match="nope"):
            registry.get_entry("nope")

    def test_duplicate_id_rejected(self, registry_guard: None) -> None:
        del registry_guard
        registry.register(_meta())(_fake_solver)
        with pytest.raises(RegistrationError, match="already registered"):
            registry.register(_meta())(_fake_solver)

    def test_stub_has_no_solver(self, registry_guard: None) -> None:
        del registry_guard
        registry.register_stub(_meta("stub", status=MethodStatus.COMING_SOON))
        entry = registry.get_entry("stub")
        assert entry.solver is None
        assert entry.meta.status == MethodStatus.COMING_SOON

    def test_stub_requires_coming_soon_status(self, registry_guard: None) -> None:
        del registry_guard
        with pytest.raises(RegistrationError, match="coming_soon"):
            registry.register_stub(_meta())

    def test_list_entries_filters_by_chapter(self, registry_guard: None) -> None:
        del registry_guard
        registry.register(_meta("a"))(_fake_solver)
        other = _meta("b")
        other = other.model_copy(update={"chapter": Chapter.CH2_LINEAR})
        registry.register(other)(_fake_solver)
        assert [e.meta.id for e in registry.list_entries(Chapter.CH2_LINEAR)] == ["b"]
        assert len(registry.list_entries()) == 2

    def test_catalog_lists_all_six_chapters(self, registry_guard: None) -> None:
        del registry_guard
        registry.register(_meta("a"))(_fake_solver)
        catalog = registry.build_catalog()
        assert len(catalog.chapters) == 6
        assert [c.number for c in catalog.chapters] == [1, 2, 3, 4, 5, 6]
        chapter_one = catalog.chapters[0]
        assert chapter_one.method_count == 1
        assert chapter_one.available_count == 1
        assert catalog.methods[0].chapter_title == "Non-linear Equations"

    def test_unregister_removes_entry(self, registry_guard: None) -> None:
        del registry_guard
        registry.register(_meta())(_fake_solver)
        registry.unregister("test_method")
        with pytest.raises(MethodNotFoundError):
            registry.get_entry("test_method")
