"""Coming-soon stubs for Chapter 4 — Numerical Differentiation and Integration (ENSH 252).

Stubs use ``register_coming_soon`` from ``app.solvers._common``; every method
imports it the same way until a real solver replaces the stub.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH4_DIFF_INTEGRATION

register_coming_soon(
    CHAPTER,
    "romberg",
    "Romberg Integration",
    "Accelerate the trapezoidal rule with Richardson extrapolation for high accuracy.",
    theory=(
        "Romberg integration applies Richardson extrapolation to a sequence of "
        "trapezoidal estimates on successively halved steps, cancelling leading error "
        "terms. The first extrapolation reproduces Simpson's rule, and higher levels "
        "converge very rapidly for smooth integrands."
    ),
    pseudocode=(
        "Romberg(f, a, b, order):\n"
        "    R[0][0] <- trapezoidal with 1 interval\n"
        "    for k = 1..order:\n"
        "        R[k][0] <- trapezoidal with 2^k intervals\n"
        "        for j = 1..k:\n"
        "            R[k][j] <- R[k][j-1] + (R[k][j-1] - R[k-1][j-1])/(4^j - 1)\n"
        "    return R[order][order]"
    ),
)

register_coming_soon(
    CHAPTER,
    "gauss_legendre",
    "Gauss-Legendre Quadrature",
    "Integrate exactly for polynomials up to degree 2n-1 using optimal nodes and weights.",
    theory=(
        "Gauss-Legendre quadrature chooses n interior nodes (the roots of the Legendre "
        "polynomial) and matching weights so that the rule is exact for polynomials of "
        "degree up to 2n-1. It needs fewer function evaluations than Newton-Cotes rules "
        "for the same accuracy."
    ),
    pseudocode=(
        "GaussLegendre(f, a, b, n):\n"
        "    obtain nodes x_i and weights w_i on [-1, 1]\n"
        "    map to [a, b]\n"
        "    I <- (b - a)/2 * sum_i w_i * f(x_i)"
    ),
)
