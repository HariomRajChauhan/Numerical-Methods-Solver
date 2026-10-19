"""Coming-soon stubs for Chapter 3 — Interpolation and Curve Fitting (ENSH 252 syllabus).

Stubs use ``register_coming_soon`` from ``app.solvers._common``; every method
imports it the same way until a real solver replaces the stub.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH3_INTERPOLATION

register_coming_soon(
    CHAPTER,
    "cubic_spline",
    "Cubic Spline Interpolation",
    "Piecewise cubics through every point with continuous first and second derivatives.",
    theory=(
        "A cubic spline uses a different cubic on each interval, chosen so the curve and "
        "its first two derivatives are continuous at the internal knots. It avoids the "
        "oscillation of high-degree polynomials and is popular for smooth interpolation."
    ),
    pseudocode=(
        "CubicSpline(xs, ys):\n"
        "    solve the tridiagonal system for the second derivatives M_i\n"
        "    (natural spline: M_0 = M_n = 0)\n"
        "    on each interval evaluate the cubic from M_i and M_{i+1}"
    ),
)
