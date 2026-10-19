"""Shared building blocks for the Chapter 4 local-extrema solver.

Private module (leading underscore) so the auto-loader skips it. It builds the
interpolating polynomial through equally spaced data in the variable
``p = (x - x_0) / h``, differentiates it, and locates and classifies the turning
points of ``dy/dp``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.solvers.ch3_interpolation._interp import forward_leading
from app.solvers.ch4_diff_integration._differentiation import forward_basis

MAXIMUM = "maximum"
MINIMUM = "minimum"
INCONCLUSIVE = "inconclusive"

# Tolerance for deciding a second derivative is (numerically) zero.
SECOND_DERIVATIVE_EPS = 1e-9


@dataclass(frozen=True)
class Extremum:
    """A stationary point of the interpolating polynomial."""

    p: float
    x: float
    y: float
    kind: str
    second_derivative: float


def interpolation_polynomial(ys: np.ndarray) -> np.ndarray:
    """Ascending-power coefficients of the interpolant in ``p`` (Newton form)."""
    differences = forward_leading(np.asarray(ys, dtype=float))
    coefficients = np.zeros(len(ys))
    for m, difference in enumerate(differences):
        coefficients[: m + 1] += difference * forward_basis(m)
    return coefficients


def find_extrema(
    xs: np.ndarray, ys: np.ndarray
) -> tuple[list[Extremum], np.ndarray, np.ndarray]:
    """Return ``(extrema, polynomial, slope_polynomial)`` for the data.

    The interpolant is fitted in ``p``; its roots that lie inside the data range
    (``0 <= p <= n - 1``) are classified by the sign of the second derivative.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    count = len(ys)
    h = float(xs[1] - xs[0])
    base = float(xs[0])

    coefficients = interpolation_polynomial(ys)
    slope = np.polynomial.polynomial.polyder(coefficients)
    curvature = np.polynomial.polynomial.polyder(coefficients, 2)

    extrema: list[Extremum] = []
    if slope.size > 1:
        roots = np.roots(slope[::-1])
        for root in roots:
            if abs(root.imag) > 1e-9:
                continue
            p = float(root.real)
            if p < -1e-7 or p > (count - 1) + 1e-7:
                continue
            value = float(np.polynomial.polynomial.polyval(p, coefficients))
            second = float(np.polynomial.polynomial.polyval(p, curvature))
            if second > SECOND_DERIVATIVE_EPS:
                kind = MINIMUM
            elif second < -SECOND_DERIVATIVE_EPS:
                kind = MAXIMUM
            else:
                kind = INCONCLUSIVE
            extrema.append(Extremum(p, base + p * h, value, kind, second))
    extrema.sort(key=lambda item: item.p)
    return extrema, coefficients, slope
