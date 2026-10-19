"""General Newton-Cotes quadrature for numerical integration (Chapter 4).

The user chooses the panel size n (1-8 subintervals), builds the Cotes numbers of
that panel and integrates either one panel or m composite panels,

``I = h (c_0 y_0 + c_1 y_1 + ... + c_n y_n)``.

The classical rules appear as special cases: n = 1 trapezoidal, n = 2 Simpson
1/3, n = 3 Simpson 3/8 and n = 4 Boole.
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
from app.solvers._common import failed_response, format_num
from app.solvers.ch4_diff_integration._newton_cotes import (
    finalize_panel,
    fraction_latex,
    newton_cotes_schema,
    newton_cotes_spec,
    prepare_newton_cotes,
)
from app.solvers.ch4_diff_integration._quadrature import (
    QUAD_POINTS,
    _degenerate_response,
    first_nonfinite,
)

NEGATIVE_WEIGHT_PANEL = 8


def _failed_singular(method_id: str, prepared: Any, decimals: int, notices: list[str]) -> SolveResponse | None:
    import math

    singular_x = first_nonfinite(prepared)
    if singular_x is None:
        return None
    assert prepared.f is not None
    node = next(
        (
            float(value)
            for value in prepared.xs
            if not math.isfinite(float(prepared.f(float(value))))
        ),
        None,
    )
    if node is not None:
        message = (
            "The integrand is not finite at the node "
            f"x = {format_num(node, decimals)}; the integral is singular there."
        )
    else:
        message = (
            "The integrand is not finite near "
            f"x = {format_num(singular_x, decimals)}; it is singular on [a, b]."
        )
    return failed_response(method_id, message, warnings=notices)


META = MethodMeta(
    id="newton_cotes",
        chapter=Chapter.CH4_DIFF_INTEGRATION,
        name="General Newton-Cotes Quadrature",
        summary=(
            "Closed Newton-Cotes rule for a chosen panel size n = 1..8, with the exact "
            "Cotes numbers and optional composite panels. Reproduces the trapezoidal, "
            "Simpson 1/3, Simpson 3/8 and Boole rules."
        ),
        theory=(
            "The closed Newton-Cotes rules integrate the polynomial that interpolates "
            "f at the equally spaced nodes x_0 ... x_n of one panel. Writing the "
            "interpolation in Lagrange form and integrating term by term gives the Cotes "
            "numbers\n"
            "  c_i = (1/p) * integral over [0, p] of the i-th Lagrange basis,\n"
            "so that a single panel of p subintervals is\n"
            "  I_panel = h (c_0 y_0 + c_1 y_1 + ... + c_p y_p).\n"
            "The Cotes numbers are exact rationals; for p = 1, 2, 3, 4 they reproduce the "
            "trapezoidal, Simpson 1/3, Simpson 3/8 and Boole rules exactly. The rule is "
            "exact for every polynomial whose degree does not exceed p (or p + 1 when p "
            "is even).\n\n"
            "For composite integration the interval is split into m panels, giving a "
            "total of n = p * m subintervals and the same h throughout. The error behaves "
            "like O(h^(d+1)), where d is the degree of exactness, so halving h reduces the "
            "error by a factor of 2^(d+1).\n\n"
            "Numerical caveat: for p >= 8 some Cotes numbers become negative. Such rules "
            "are still exact for smooth polynomials but can amplify rounding error, so "
            "high-order Newton-Cotes quadrature is generally avoided in practice (Romberg "
            "extrapolation or Gauss-Legendre rules are preferred instead). The platform "
            "warns when these negative weights appear."
        ),
        formulas=[
            LabeledLatex(
                label="Single panel (Cotes numbers)",
                latex=r"I_{panel} = h\sum_{i=0}^{n} c_i\,y_i, \qquad c_i = \frac{1}{n}"
                r"\int_{0}^{n}\prod_{j \ne i}\frac{t - t_j}{t_i - t_j}\,dt",
            ),
            LabeledLatex(
                label="Composite (m panels, N = n m)",
                latex=r"I \approx h\sum_{i=0}^{N} w_i\,y_i, \qquad h = \frac{b - a}{N}",
            ),
            LabeledLatex(
                label="Classical cases",
                latex=r"n = 1\ \text{trapezoidal},\quad n = 2\ \text{Simpson 1/3},"
                r"\quad n = 3\ \text{Simpson 3/8},\quad n = 4\ \text{Boole}",
            ),
        ],
        pseudocode=(
            "NewtonCotes(f, a, b, n, m):\n"
            "    c[0..n] <- Cotes numbers by integrating the Lagrange basis (exact fractions)\n"
            "    N <- n * m\n"
            "    h <- (b - a) / N\n"
            "    I <- 0\n"
            "    for panel k = 0..m-1:\n"
            "        base <- k * n\n"
            "        for i = 0..n:\n"
            "            I <- I + h * c[i] * f(a + (base + i)*h)\n"
            "    return I"
        ),
        input_schema=newton_cotes_schema(),
        examples=[
            MethodExample(
                name="n = 4, one panel: x^4 on [0, 1]",
                description="Panel size 4 reproduces Boole's rule; the quartic integrates to exactly 0.2.",
                inputs={
                    "source": "function",
                    "function": "x^4",
                    "a": 0.0,
                    "b": 1.0,
                    "n": 4,
                    "panels": 1,
                    "compare": False,
                    "show_convergence": False,
                    "decimal_precision": 6,
                },
            ),
            MethodExample(
                name="n = 2, m = 2: sin x on [0, pi]",
                description="Simpson 1/3 with 4 subintervals gives about 2.00456 (exact 2).",
                inputs={
                    "source": "function",
                    "function": "sin(x)",
                    "a": 0.0,
                    "b": 3.141592653589793,
                    "n": 2,
                    "panels": 2,
                    "compare": False,
                    "show_convergence": False,
                    "decimal_precision": 6,
                },
            ),
            MethodExample(
                name="n = 8 instability warning",
                description="The eight-subinterval panel has negative Cotes numbers; the solver warns.",
                inputs={
                    "source": "function",
                    "function": "exp(x)",
                    "a": 0.0,
                    "b": 1.0,
                    "n": 8,
                    "panels": 1,
                    "compare": False,
                    "show_convergence": False,
                    "decimal_precision": 6,
                },
            ),
            MethodExample(
                name="Table input with n = 6, m = 1",
                description="Seven equally spaced values of y = x^2 on [0, 1] (exact 1/3).",
                inputs={
                    "source": "table",
                    "points": [list(point) for point in QUAD_POINTS],
                    "n": 6,
                    "panels": 1,
                    "compare": False,
                    "show_convergence": False,
                    "decimal_precision": 6,
                },
            ),
        ],
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate with the general (composite) Newton-Cotes rule."""
    del limits
    method_id = "newton_cotes"
    decimals = int(inputs.get("decimal_precision", 6))
    panel = int(inputs.get("n", 4))

    prepared = prepare_newton_cotes(inputs, decimals, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    notices = list(prepared.notices)

    if prepared.n == 0:
        return _degenerate_response(method_id, prepared, notices, decimals)

    singular = _failed_singular(method_id, prepared, decimals, notices)
    if singular is not None:
        return singular

    spec = newton_cotes_spec(panel)
    panels = prepared.n // panel

    if spec.reproduces is not None:
        notices.append(f"The {panel}-subinterval panel reproduces {spec.reproduces}.")
    if panel >= NEGATIVE_WEIGHT_PANEL and any(c < 0 for c in spec.cotes):
        notices.append(
            f"The {panel}-subinterval panel has negative Cotes numbers "
            f"({', '.join(fraction_latex(c) for c in spec.cotes if c < 0)}); such "
            "high-order Newton-Cotes rules can amplify rounding error."
        )

    return finalize_panel(
        method_id, prepared, spec, panels, inputs, decimals, notices=notices
    )
