"""Method registry.

A solver module registers itself with a single decorator call and a
:class:`MethodMeta` payload. The API and frontend read everything they need
from the registry, so adding a method never touches routers or UI code.

Adding a method is therefore: one solver file (+ decorator) + one test file.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.errors import MethodNotFoundError, RegistrationError
from app.core.models import (
    CHAPTER_DESCRIPTIONS,
    CHAPTER_TITLES,
    Chapter,
    ChapterInfo,
    MethodCatalog,
    MethodMeta,
    MethodStatus,
    SolveResponse,
    SolverLimits,
)

# A solver is a pure function: validated inputs + limits in, contract out.
SolverFn = Callable[[dict[str, Any], SolverLimits], SolveResponse]


@dataclass(frozen=True)
class MethodEntry:
    """A registered method: its metadata plus the callable that solves it (if any)."""

    meta: MethodMeta
    solver: SolverFn | None


_REGISTRY: dict[str, MethodEntry] = {}


def register(meta: MethodMeta) -> Callable[[SolverFn], SolverFn]:
    """Return a decorator that registers ``meta`` together with the solver function.

    Usage::

        @register(MethodMeta(id="bisection", ...))
        def solve(inputs, limits) -> SolveResponse: ...

    Raises:
        RegistrationError: On duplicate ids.
    """
    _validate_meta(meta)
    if meta.id in _REGISTRY:
        raise RegistrationError(f"Method id '{meta.id}' is already registered.")

    def decorator(fn: SolverFn) -> SolverFn:
        _REGISTRY[meta.id] = MethodEntry(meta=meta, solver=fn)
        return fn

    return decorator


def register_stub(meta: MethodMeta) -> None:
    """Register a 'coming soon' placeholder that has no solver yet."""
    if meta.status != MethodStatus.COMING_SOON:
        raise RegistrationError(f"register_stub expects status=coming_soon for '{meta.id}'.")
    _validate_meta(meta)
    if meta.id in _REGISTRY:
        raise RegistrationError(f"Method id '{meta.id}' is already registered.")
    _REGISTRY[meta.id] = MethodEntry(meta=meta, solver=None)


def _validate_meta(meta: MethodMeta) -> None:
    if not meta.id or not meta.id.strip():
        raise RegistrationError("A method id is required.")
    keys = [field.key for field in meta.input_schema]
    if len(keys) != len(set(keys)):
        raise RegistrationError(f"Method '{meta.id}' has duplicate input keys.")


def get_entry(method_id: str) -> MethodEntry:
    """Look up a registered method.

    Raises:
        MethodNotFoundError: If the id is unknown.
    """
    try:
        return _REGISTRY[method_id]
    except KeyError as exc:
        raise MethodNotFoundError(
            f"No method is registered under the id '{method_id}'.",
            hint="Fetch GET /api/methods for the list of available method ids.",
        ) from exc


def list_entries(chapter: Chapter | None = None) -> list[MethodEntry]:
    """All registered entries, optionally filtered by chapter, in insertion order."""
    entries = list(_REGISTRY.values())
    if chapter is not None:
        entries = [entry for entry in entries if entry.meta.chapter == chapter]
    return entries


def build_catalog() -> MethodCatalog:
    """Assemble the GET /api/methods payload (chapter cards + method metadata)."""
    methods = [entry.meta for entry in list_entries()]
    chapters: list[ChapterInfo] = []
    for number, chapter in enumerate(Chapter, start=1):
        chapter_methods = [m for m in methods if m.chapter == chapter]
        chapters.append(
            ChapterInfo(
                id=chapter,
                number=number,
                title=CHAPTER_TITLES[chapter],
                description=CHAPTER_DESCRIPTIONS[chapter],
                method_count=len(chapter_methods),
                available_count=sum(
                    1 for m in chapter_methods if m.status == MethodStatus.AVAILABLE
                ),
            )
        )
    return MethodCatalog(chapters=chapters, methods=methods)


def unregister(method_id: str) -> None:
    """Remove a method (test utility; keeps test isolation simple)."""
    _REGISTRY.pop(method_id, None)


def clear() -> None:
    """Remove every registration (test utility)."""
    _REGISTRY.clear()
