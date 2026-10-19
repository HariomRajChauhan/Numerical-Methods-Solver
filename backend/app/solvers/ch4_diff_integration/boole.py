"""Boole's rule for numerical integration (Chapter 4).

Boole's rule integrates a single panel of four equal subintervals with the
weights 7:32:12:32:7,

``I_panel = (2h/45) [7y_0 + 32y_1 + 12y_2 + 32y_3 + 7y_4]``.

It is exact for polynomials up to degree five (error O(h^6)) and is applied
compositely across every group of four subintervals.
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
    BOOLE_RULE,
    classical_schema,
    solve_classical,
)

META = MethodMeta(
    id="boole",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Boole's Rule",
    summary=(
        "Fifth-degree Newton-Cotes rule over four subintervals; exact for polynomials up "
        "to degree five (error O(h^6)). The number of subintervals must be a multiple of 4."
    ),
    theory=(
        "Boole's rule interpolates the five nodes of a panel with the unique quartic "
        "through them and integrates it exactly. With h = (b - a)/n the panel value is\n"
        "  I_panel = (2h/45)[7 y_0 + 32 y_1 + 12 y_2 + 32 y_3 + 7 y_4],\n"
        "i.e. Cotes numbers 14/45, 64/45, 24/45, 64/45, 14/45 (they sum to 4h). Because "
        "the rule is exact for every polynomial up to degree five, its error begins with "
        "the sixth derivative: E = -(2(b - a)/945) h^6 f^(6)(xi) = O(h^6). Halving h "
        "reduces the error by a factor of about 64, shown by a slope-6 line in the "
        "convergence study.\n\n"
        "Applied compositely, the interval is split into panels of four subintervals, so "
        "the total number of subintervals n must be a multiple of 4; other values are "
        "rejected with a suggestion for the nearest valid n. Boole's rule is much more "
        "accurate than Simpson's rules for smooth integrands but needs more nodes.\n\n"
        "Note: Boole's rule is exact up to degree 5 only, and Weddle's rule is also exact "
        "only up to degree 5 (not degree 6), despite using six subintervals."
    ),
    formulas=[
        LabeledLatex(
            label="Boole's rule (one panel of 4 subintervals)",
            latex=r"\int_{x_0}^{x_4} f(x)\,dx \approx \frac{2h}{45}"
            r"\left(7y_0 + 32y_1 + 12y_2 + 32y_3 + 7y_4\right)",
        ),
        LabeledLatex(
            label="Composite rule",
            latex=r"I \approx \sum_{\text{panels}} \frac{2h}{45}"
            r"\left(7y_0 + 32y_1 + 12y_2 + 32y_3 + 7y_4\right)",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E = -\frac{2(b - a)}{945}\,h^{6}\,f^{(6)}(\xi), \qquad a < \xi < b",
        ),
    ],
    pseudocode=(
        "Boole(f, a, b, n):        # n must be a multiple of 4\n"
        "    if n mod 4 != 0: report failure with a suggested multiple of 4\n"
        "    h <- (b - a) / n\n"
        "    I <- 0\n"
        "    for each panel (x0 .. x4) of four subintervals:\n"
        "        I <- I + (2h/45)*(7y0 + 32y1 + 12y2 + 32y3 + 7y4)\n"
        "    return I"
    ),
    input_schema=classical_schema(4),
    examples=[
        MethodExample(
            name="x^4 on [0, 1] with n = 4",
            description="A quartic is integrated exactly: the value is 0.2.",
            inputs={
                "source": "function",
                "function": "x^4",
                "a": 0.0,
                "b": 1.0,
                "step_mode": "intervals",
                "n": 4,
                "compare": False,
                "show_convergence": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="sin x on [0, pi] with n = 4",
            description="Boole's rule is very accurate here: about 1.99857 (exact 2).",
            inputs={
                "source": "function",
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "step_mode": "intervals",
                "n": 4,
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
    """Integrate with the composite Boole's rule."""
    return solve_classical(META, BOOLE_RULE, inputs, limits)
