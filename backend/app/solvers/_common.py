"""Shared helpers for solver modules.

This module is deliberately private (leading underscore) so the auto-loader in
:mod:`app.solvers` skips it — only real solvers register themselves. It holds
small, reusable building blocks so individual solvers stay short.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from app.core.models import Chapter, MethodMeta, MethodStatus
from app.core.registry import register_stub

# Function-like callable produced by app.core.parser.make_function.
Evaluator = Callable[[Any], Any]


def _safe_eval(f: Evaluator, x: float) -> float:
    """Evaluate ``f`` at a scalar, mapping any failure to ``nan`` (plot gaps)."""
    try:
        return float(f(x))
    except Exception:
        return float("nan")


def sample_curve(
    f: Evaluator,
    lo: float,
    hi: float,
    *,
    points: int = 400,
) -> tuple[list[float], list[float]]:
    """Sample ``f`` over ``[lo, hi]`` for plotting.

    The callable is expected to be the non-strict variant
    (``make_function(..., strict=False)``), but every point is guarded anyway so
    domain gaps become ``nan`` instead of raising. Points are evaluated
    one-by-one, which also tolerates expressions that are not vectorisable.

    Returns:
        ``(xs, ys)`` as plain Python lists.
    """
    xs = np.linspace(lo, hi, points)
    ys = np.array([_safe_eval(f, float(x)) for x in xs], dtype=float)
    return xs.tolist(), ys.tolist()


def line_trace(xs: list[float], ys: list[float], name: str = "f(x)") -> dict[str, Any]:
    """A Plotly scatter trace drawn as a continuous line."""
    return {"type": "scatter", "mode": "lines", "name": name, "x": xs, "y": ys}


def marker_trace(
    x: float,
    y: float,
    name: str,
    *,
    color: str = "#dc2626",
    symbol: str = "circle",
) -> dict[str, Any]:
    """A single Plotly point marker (e.g. the computed root)."""
    return {
        "type": "scatter",
        "mode": "markers",
        "name": name,
        "x": [x],
        "y": [y],
        "marker": {"size": 11, "color": color, "symbol": symbol},
    }


def register_coming_soon(
    chapter: Chapter,
    method_id: str,
    name: str,
    summary: str,
    theory: str = "",
    pseudocode: str = "",
) -> None:
    """Register a syllabus method that is planned but not yet implemented.

    Coming-soon methods appear in navigation, search and the chapter pages with
    a "Coming soon" badge, and their theory/pseudocode tabs are already readable.
    Implementing the method later means replacing this call with ``@register``.
    """
    register_stub(
        MethodMeta(
            id=method_id,
            chapter=chapter,
            name=name,
            status=MethodStatus.COMING_SOON,
            summary=summary,
            theory=theory,
            pseudocode=pseudocode,
            input_schema=[],
        )
    )
