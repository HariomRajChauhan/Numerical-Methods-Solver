"""Weddle's rule for numerical integration (Chapter 4).

Weddle's rule integrates a single panel of six equal subintervals with the
weights 1:5:1:6:1:5:1,

``I_panel = (3h/10) [y_0 + 5y_1 + y_2 + 6y_3 + y_4 + 5y_5 + y_6]``.

It is exact for polynomials up to degree five (error O(h^6)) and is applied
compositely across every group of six subintervals.
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
from app.solvers.ch4_diff_integration._newton_cotes import (
    WEDDLE_RULE,
    classical_schema,
    solve_classical,
)

META = MethodMeta(
    id="weddle",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Weddle's Rule",
    summary=(
        "Six-subinterval Newton-Cotes rule with weights 1:5:1:6:1:5:1; exact for "
        "polynomials up to degree five (error O(h^6)). n must be a multiple of 6."
    ),
    theory=(
        "Weddle's rule integrates the seventh-order interpolating polynomial through the "
        "seven nodes of a panel. With h = (b - a)/n the panel value is\n"
        "  I_panel = (3h/10)[y_0 + 5 y_1 + y_2 + 6 y_3 + y_4 + 5 y_5 + y_6],\n"
        "i.e. Cotes numbers 3/10, 3/2, 3/10, 9/5, 3/10, 3/2, 3/10. The panel is exact for "
        "every polynomial up to degree five, and its error begins with the sixth "
        "derivative: E = -((b - a)/840) h^6 f^(6)(xi) = O(h^6). Halving h reduces the "
        "error by about 64, which the convergence study shows as a slope-6 line.\n\n"
        "Important subtlety: Weddle's rule is exact only up to degree 5, NOT degree 6. "
        "For example, integrating x^6 on [0, 1] with n = 6 gives about 0.142876 instead of "
        "the exact 1/7 = 0.142857. Because it uses six subintervals, the total number of "
        "subintervals n must be a multiple of 6; other values are rejected with a "
        "suggestion for the nearest valid n.\n\n"
        "Weddle's rule is very accurate for smooth integrands but its high-order weights "
        "make it sensitive to noisy or tabulated data."
    ),
    formulas=[
        LabeledLatex(
            label="Weddle's rule (one panel of 6 subintervals)",
            latex=r"\int_{x_0}^{x_6} f(x)\,dx \approx \frac{3h}{10}"
            r"\left(y_0 + 5y_1 + y_2 + 6y_3 + y_4 + 5y_5 + y_6\right)",
        ),
        LabeledLatex(
            label="Composite rule",
            latex=r"I \approx \sum_{\text{panels}} \frac{3h}{10}"
            r"\left(y_0 + 5y_1 + y_2 + 6y_3 + y_4 + 5y_5 + y_6\right)",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E = -\frac{(b - a)}{840}\,h^{6}\,f^{(6)}(\xi), \qquad a < \xi < b",
        ),
    ],
    pseudocode=(
        "Weddle(f, a, b, n):      # n must be a multiple of 6\n"
        "    if n mod 6 != 0: report failure with a suggested multiple of 6\n"
        "    h <- (b - a) / n\n"
        "    I <- 0\n"
        "    for each panel (x0 .. x6) of six subintervals:\n"
        "        I <- I + (3h/10)*(y0 + 5y1 + y2 + 6y3 + y4 + 5y5 + y6)\n"
        "    return I"
    ),
    input_schema=classical_schema(6),
    examples=[
        MethodExample(
            name="x^5 on [0, 1] with n = 6",
            description="A quintic is integrated exactly: the value is 1/6 = 0.166667.",
            inputs={
                "source": "function",
                "function": "x^5",
                "a": 0.0,
                "b": 1.0,
                "step_mode": "intervals",
                "n": 6,
                "compare": False,
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="sin x on [0, pi] with n = 6",
            description="Weddle's rule is very accurate here: about 2.00086 (exact 2).",
            inputs={
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "step_mode": "intervals",
                "n": 6,
                "compare": False,
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Compare all rules (n = 12)",
            description="Runs trapezoidal, Simpson 1/3 and 3/8, Boole and Weddle on sin x.",
            inputs={
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "step_mode": "intervals",
                "n": 12,
                "compare": True,
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate with the composite Weddle's rule."""
    return solve_classical(META, WEDDLE_RULE, inputs, limits)
