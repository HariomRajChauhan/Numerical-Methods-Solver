"""Trapezoidal rule for numerical integration (Chapter 4).

The composite trapezoidal rule joins successive nodes with straight lines and
integrates the resulting piecewise-linear interpolant, giving

``I = (h/2) [y_0 + 2(y_1 + ... + y_{n-1}) + y_n]``.

It is second-order accurate and evaluates the integrand from a function or an
equally spaced table.
"""

from __future__ import annotations

from typing import Any

from app.core.models import (
    Chapter,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SolveResponse,
    SolverLimits,
)
from app.core.registry import register
from app.solvers.ch4_diff_integration._quadrature import (
    QUAD_POINTS,
    TRAPEZOIDAL_RULE,
    quadrature_schema,
    solve_quadrature,
)

META = MethodMeta(
    id="trapezoidal",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Trapezoidal Rule",
    summary=(
        "Integrate a function or equally spaced table by approximating the area with "
        "trapezoids; second-order accurate and exact for linear integrands."
    ),
    theory=(
        "Divide [a, b] into n equal subintervals of width h = (b - a)/n at the nodes "
        "x_i = a + i h, and write y_i = f(x_i). On each subinterval the curve is "
        "replaced by the straight line joining its endpoints, so the area there is the "
        "trapezoid (h/2)(y_i + y_{i+1}). Adding the n trapezoids collapses the interior "
        "terms to twice and gives the composite rule\n"
        "  I ~ (h/2)[y_0 + 2(y_1 + ... + y_{n-1}) + y_n].\n\n"
        "The rule integrates any linear polynomial exactly, so its error depends on the "
        "second derivative. The local error is -(h^3/12) f''(xi) and the global error is "
        "E = -((b - a)/12) h^2 f''(xi) = O(h^2). Halving h therefore quarters the error, "
        "which the optional convergence study shows as a slope-2 line on a log plot. The "
        "sign of the error is opposite to f'': a convex curve is under-estimated and a "
        "concave curve is over-estimated."
    ),
    formulas=[
        LabeledLatex(
            label="Composite trapezoidal rule",
            latex=r"\int_a^b f(x)\,dx \approx \frac{h}{2}\left[\,y_0 + "
            r"2\left(y_1 + y_2 + \cdots + y_{n-1}\right) + y_n\,\right]",
        ),
        LabeledLatex(
            label="Single subinterval",
            latex=r"\int_{x_i}^{x_{i+1}} f(x)\,dx \approx \frac{h}{2}\left(y_i + y_{i+1}\right)",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E = -\frac{(b - a)}{12}\,h^{2}\,f''(\xi), \qquad a < \xi < b",
        ),
    ],
    pseudocode=(
        "Trapezoidal(f, a, b, n):\n"
        "    h <- (b - a) / n\n"
        "    total <- f(a) + f(b)\n"
        "    for i = 1..n-1:\n"
        "        total <- total + 2 * f(a + i*h)\n"
        "    I <- h/2 * total\n"
        "    return I"
    ),
    input_schema=quadrature_schema(4),
    examples=[
        MethodExample(
            name="sin x on [0, pi] with n = 4",
            description="Classic textbook value: the trapezoidal rule gives about 1.8961 (exact 2).",
            inputs={
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "step_mode": "intervals",
                "n": 4,
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Equally spaced table of y = x^2",
            description="n = 6 nodes of y = x^2 on [0, 1]; the rule gives about 0.33796 (exact 1/3).",
            inputs={
                "source": "table",
                "points": [list(point) for point in QUAD_POINTS],
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Convergence of the error vs n",
            description="sin x on [0, pi] with a semilog convergence study (slope 2).",
            inputs={
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "step_mode": "intervals",
                "n": 4,
                "show_convergence": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate with the composite trapezoidal rule."""
    return solve_quadrature(META, TRAPEZOIDAL_RULE, inputs, limits)
