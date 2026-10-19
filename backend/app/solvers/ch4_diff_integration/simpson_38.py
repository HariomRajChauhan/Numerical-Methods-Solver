"""Simpson's 3/8 rule for numerical integration (Chapter 4).

Simpson's 3/8 rule fits a cubic through every group of three subintervals and
integrates it, giving

``I = (3h/8) [y_0 + 3(y_1 + y_2 + y_4 + y_5 + ...) + 2(y_3 + y_6 + ...) + y_n]``.

It is fourth-order accurate and requires the number of subintervals n to be a
multiple of three.
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
    SIMPSON38_RULE,
    quadrature_schema,
    solve_quadrature,
)

META = MethodMeta(
    id="simpson_38",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Simpson's 3/8 Rule",
    summary=(
        "Integrate over triples of subintervals with a cubic fit; fourth-order "
        "accurate when the number of subintervals n is a multiple of three."
    ),
    theory=(
        "Group the equally spaced nodes in sets of four spanning three subintervals, "
        "(x_0, x_1, x_2, x_3), (x_3, x_4, x_5, x_6), ... With h = (b - a)/n and "
        "y_i = f(x_i), the cubic through each set is integrated exactly over its three "
        "subintervals to give (3h/8)(y_0 + 3y_1 + 3y_2 + y_3). Summing over the n/3 "
        "groups and collecting repeated nodes yields the composite rule\n"
        "  I ~ (3h/8)[y_0 + 3(y_1 + y_2 + y_4 + y_5 + ...) + 2(y_3 + y_6 + ...) + y_n].\n\n"
        "The rule integrates cubics exactly, so its leading error again depends on the "
        "fourth derivative: E = -((b - a)/80) h^4 f^(4)(xi) = O(h^4). It is especially "
        "useful when the data naturally come in multiples of three subintervals, for "
        "example n = 3, 6 or 9. The number of subintervals n must be a multiple of three; "
        "other values are rejected with a suggestion for the nearest valid n."
    ),
    formulas=[
        LabeledLatex(
            label="Composite Simpson 3/8 rule",
            latex=r"\int_a^b f(x)\,dx \approx \frac{3h}{8}\left[\,y_0 + "
            r"3\left(y_1 + y_2 + y_4 + y_5 + \cdots\right) + "
            r"2\left(y_3 + y_6 + \cdots\right) + y_n\,\right]",
        ),
        LabeledLatex(
            label="A single triple of subintervals",
            latex=r"\int_{x_0}^{x_3} f(x)\,dx \approx \frac{3h}{8}\left(y_0 + 3y_1 + 3y_2 + y_3\right)",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E = -\frac{(b - a)}{80}\,h^{4}\,f^{(4)}(\xi), \qquad a < \xi < b",
        ),
    ],
    pseudocode=(
        "Simpson38(f, a, b, n):        # n must be a multiple of 3\n"
        "    if n mod 3 != 0: report failure with a suggested multiple of 3\n"
        "    h <- (b - a) / n\n"
        "    total <- f(a) + f(b)\n"
        "    for i = 1..n-1:\n"
        "        total <- total + (2 if i mod 3 == 0 else 3) * f(a + i*h)\n"
        "    I <- 3h/8 * total\n"
        "    return I"
    ),
    input_schema=quadrature_schema(3),
    examples=[
        MethodExample(
            name="x^2 on [0, 1] with n = 3",
            description="A cubic-accurate rule integrates x^2 exactly: the value is 1/3.",
            inputs={
                "source": "function",
                "function": "x^2",
                "a": 0.0,
                "b": 1.0,
                "step_mode": "intervals",
                "n": 3,
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="sin x on [0, pi] with n = 6",
            description="Three groups of subintervals give about 2.00086, close to the exact value 2.",
            inputs={
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "step_mode": "intervals",
                "n": 6,
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Equally spaced table of y = x^2",
            description="n = 6 nodes of y = x^2 on [0, 1]; the integral is 1/3.",
            inputs={
                "source": "table",
                "points": [list(point) for point in QUAD_POINTS],
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate with the composite Simpson 3/8 rule."""
    return solve_quadrature(META, SIMPSON38_RULE, inputs, limits)
