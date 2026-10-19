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
    "least_squares",
    "Least-Squares Curve Fitting",
    "Fit the best straight line or curve by minimising the sum of squared residuals.",
    theory=(
        "Least-squares fitting chooses coefficients that minimise the sum of squared "
        "vertical distances from the data to the model. For a line y = a + b x the "
        "normal equations give closed-form values for a and b; the idea extends to "
        "polynomial and linearisable (e.g. exponential) models."
    ),
    pseudocode=(
        "LeastSquares(xs, ys, model):\n"
        "    form the normal equations (A^T A) c = A^T y\n"
        "    solve for the coefficients c\n"
        "    return c and the residuals"
    ),
)

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
