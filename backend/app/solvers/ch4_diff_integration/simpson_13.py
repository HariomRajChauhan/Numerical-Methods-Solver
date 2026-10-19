"""Simpson's 1/3 rule for numerical integration (Chapter 4).

Simpson's 1/3 rule fits a parabola through every pair of subintervals and
integrates it, giving

``I = (h/3) [y_0 + 4(y_1 + y_3 + ...) + 2(y_2 + y_4 + ...) + y_n]``.

It is fourth-order accurate and requires an even number of subintervals n.
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
    SIMPSON13_RULE,
    quadrature_schema,
    solve_quadrature,
)

META = MethodMeta(
    id="simpson_13",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Simpson's 1/3 Rule",
    summary=(
        "Integrate over pairs of subintervals with a quadratic fit; fourth-order "
        "accurate when the number of subintervals n is even."
    ),
    theory=(
        "Group the equally spaced nodes in pairs, (x_0, x_1, x_2), (x_2, x_3, x_4), "
        "... With h = (b - a)/n and y_i = f(x_i), a parabola through each triple is "
        "integrated exactly over its two subintervals to give (h/3)(y_{2k} + 4y_{2k+1} + "
        "y_{2k+2}). Summing over the n/2 pairs and collecting repeated nodes yields the "
        "composite rule\n"
        "  I ~ (h/3)[y_0 + 4(y_1 + y_3 + ...) + 2(y_2 + y_4 + ...) + y_n].\n\n"
        "Because a parabola is exact for quadratics, the leading error depends on the "
        "fourth derivative: E = -((b - a)/180) h^4 f^(4)(xi) = O(h^4). Halving h "
        "reduces the error by a factor of about sixteen, shown by a slope-4 line in the "
        "optional convergence study. The number of subintervals n must be even; an odd "
        "n is rejected with a suggestion for the nearest valid value."
    ),
    formulas=[
        LabeledLatex(
            label="Composite Simpson 1/3 rule",
            latex=r"\int_a^b f(x)\,dx \approx \frac{h}{3}\left[\,y_0 + "
            r"4\left(y_1 + y_3 + \cdots\right) + 2\left(y_2 + y_4 + \cdots\right) "
            r"+ y_n\,\right]",
        ),
        LabeledLatex(
            label="A single pair of subintervals",
            latex=r"\int_{x_0}^{x_2} f(x)\,dx \approx \frac{h}{3}\left(y_0 + 4y_1 + y_2\right)",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E = -\frac{(b - a)}{180}\,h^{4}\,f^{(4)}(\xi), \qquad a < \xi < b",
        ),
    ],
    pseudocode=(
        "Simpson13(f, a, b, n):        # n must be even\n"
        "    if n is odd: report failure with a suggested even n\n"
        "    h <- (b - a) / n\n"
        "    total <- f(a) + f(b)\n"
        "    for i = 1..n-1:\n"
        "        total <- total + (4 if i is odd else 2) * f(a + i*h)\n"
        "    I <- h/3 * total\n"
        "    return I"
    ),
    input_schema=quadrature_schema(4),
    examples=[
        MethodExample(
            name="sin x on [0, pi] with n = 4",
            description="Simpson's 1/3 rule gives about 2.0046, close to the exact value 2.",
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
            description="n = 6 nodes of y = x^2 on [0, 1]; the quadratic is integrated exactly (1/3).",
            inputs={
                "source": "table",
                "points": [list(point) for point in QUAD_POINTS],
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Convergence of the error vs n",
            description="sin x on [0, pi] with a semilog convergence study (slope 4).",
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
    """Integrate with the composite Simpson 1/3 rule."""
    return solve_quadrature(META, SIMPSON13_RULE, inputs, limits)
