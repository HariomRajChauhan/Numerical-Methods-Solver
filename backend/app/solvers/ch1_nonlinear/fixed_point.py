"""Fixed-point iteration.

Rewrite ``f(x) = 0`` as ``x = g(x)`` and iterate ``x(k+1) = g(x(k))``. The
sequence converges to a fixed point ``x* = g(x*)`` when ``g`` is a contraction
near ``x*``, i.e. ``|g'(x*)| < 1``. Convergence is linear with rate ``|g'|``.

The user supplies ``g(x)`` directly. When the original ``f(x) = 0`` is also
given, the solver suggests simple rearrangements of the family
``g(x) = x + c·f(x)`` together with their ``|g'(x0)|`` so a good choice can be
made.
"""

from __future__ import annotations

import math
from typing import Any

import sympy as sp

from app.core.models import (
    Chapter,
    DataTable,
    ErrorInfo,
    InputField,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    PlotPayload,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.parser import expr_to_latex, make_function, parse_expression
from app.core.registry import register
from app.solvers._common import (
    format_num,
    function_field,
    line_trace,
    marker_trace,
    max_iterations_field,
    number_field,
    precision_field,
    sample_curve,
    segment_trace,
    stop_criterion_field,
    stop_reached,
    tolerance_field,
)

_DIVERGENCE_BOUND = 1e10
_MAX_COBWEB_STEPS = 25
_SUGGEST_SCALES = (1.0, -1.0, 0.5, -0.5)


META = MethodMeta(
    id="fixed_point",
    chapter=Chapter.CH1_NONLINEAR,
    name="Fixed-Point Iteration",
    summary=(
        "Rearrange f(x) = 0 as x = g(x) and iterate x(k+1) = g(x(k)); converges "
        "when g is a contraction (|g'(x)| < 1) near the fixed point."
    ),
    theory=(
        "Any equation f(x) = 0 can be rearranged into the fixed-point form "
        "x = g(x). A solution of the original equation is a fixed point of g, and "
        "it is found by the simple iteration x(k+1) = g(x(k)).\n\n"
        "The iteration converges to a fixed point x* = g(x*) if g is a contraction "
        "close to x*: by the Mean Value Theorem the error obeys "
        "e(k+1) = g'(xi)·e(k) for some xi between x(k) and x*. Hence convergence "
        "requires |g'(x)| < 1 near the fixed point, and the error shrinks by a "
        "factor |g'| each step (linear convergence). If |g'(x)| >= 1 the errors "
        "grow and the method diverges.\n\n"
        "Because f(x) = 0 gives x = x + c·f(x) for any constant c, there are "
        "infinitely many rearrangements. Good choices minimise |g'(x0)| = "
        "|1 + c·f'(x0)|; providing f(x) lets the solver rank these automatically."
    ),
    formulas=[
        LabeledLatex(label="Fixed-point iteration", latex=r"x_{k+1} = g(x_k)"),
        LabeledLatex(label="Fixed point", latex=r"x^{*} = g(x^{*})"),
        LabeledLatex(
            label="Convergence condition",
            latex=r"|g'(x)| < 1 \quad\text{near } x^{*}",
        ),
        LabeledLatex(
            label="Error law (linear)",
            latex=r"e_{k+1} = g'(\xi)\,e_k,\qquad p = 1",
        ),
        LabeledLatex(
            label="Rearrangement family",
            latex=r"g_c(x) = x + c\,f(x),\qquad g_c'(x) = 1 + c\,f'(x)",
        ),
    ],
    pseudocode=(
        "FixedPoint(g, x0, tol, max_iter):\n"
        "    x <- x0\n"
        "    for k = 1 to max_iter:\n"
        "        x_new <- g(x)\n"
        "        err   <- |x_new - x|\n"
        "        if stopping criterion met: return x_new, k\n"
        "        if x_new is not finite or |x_new| > 1e10: stop \"diverged\"\n"
        "        x <- x_new\n"
        "    return x, max_iter"
    ),
    input_schema=[
        function_field(
            label="Iteration function g(x)",
            placeholder="cos(x)",
            help=(
                "The right-hand side of x = g(x). Note for the |f(x)| criterion "
                "the residual g(x) - x is used. Allowed: sin, cos, exp, ln, sqrt ..."
            ),
        ),
        InputField(
            key="original_function",
            label="Original equation f(x) (optional)",
            type="function",
            variable="x",
            required=False,
            default=None,
            placeholder="cos(x) - x",
            help="Provide f(x) = 0 to see suggested rearrangements g(x) = x + c·f(x).",
        ),
        number_field("x0", "Initial guess x0", 1.0, help="A starting value near the fixed point."),
        tolerance_field(),
        max_iterations_field(),
        stop_criterion_field(default="interval"),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="g(x) = cos(x) from 1",
            description="Fixed point of cosine, x* near 0.73909.",
            inputs={
                "function": "cos(x)",
                "original_function": "cos(x) - x",
                "x0": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Babylonian square root: g(x) = (x + 2/x)/2",
            description="Converges fast to sqrt(2) = 1.41421 (small |g'|).",
            inputs={
                "function": "(x + 2/x)/2",
                "original_function": "x^2 - 2",
                "x0": 1.0,
                "tolerance": 1e-8,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Divergent: g(x) = 2x from 0.5",
            description="|g'| = 2 >= 1, so the iteration diverges (warning shown).",
            inputs={
                "function": "2*x",
                "original_function": "",
                "x0": 0.5,
                "tolerance": 1e-6,
                "max_iterations": 100,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
    ],
)


def _error_column(criterion: str) -> str:
    if criterion == "function":
        return "Error |g(x) - x|"
    if criterion == "relative":
        return "Error %"
    return "Error |x_k - x_(k-1)|"


def _suggest_rearrangements(
    f_expr: sp.Expr,
    x0: float,
    decimals: int,
) -> tuple[list[list[Any]], str | None]:
    """Rank rearrangements g_c(x) = x + c·f(x) by ``|g'(x0)|``."""
    symbol = sp.Symbol("x")
    df = make_function(sp.diff(f_expr, symbol), ("x",), strict=False)
    try:
        fp0 = float(df(x0))
    except Exception:
        return [], None
    if not math.isfinite(fp0):
        return [], None

    scales = list(_SUGGEST_SCALES)
    if fp0 != 0.0:
        optimal = -1.0 / fp0
        if all(abs(optimal - c) > 1e-9 for c in scales):
            scales.append(optimal)

    rows: list[list[Any]] = []
    best_label: str | None = None
    best_mag = math.inf
    for c in scales:
        gprime = 1.0 + c * fp0
        if fp0 != 0.0 and abs(c - (-1.0 / fp0)) <= 1e-9:
            label = "x - f(x)/f'(x0)"
        else:
            sign = "-" if c < 0 else "+"
            coefficient = format_num(abs(c), decimals)
            label = f"x {sign} {coefficient} f(x)"
        contractive = abs(gprime) < 1.0
        rows.append([label, gprime, abs(gprime), "yes" if contractive else "no"])
        if contractive and abs(gprime) < best_mag:
            best_mag = abs(gprime)
            best_label = label
    return rows, best_label


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run fixed-point iteration for the validated ``inputs``."""
    text: str = inputs["function"]
    original_text = inputs.get("original_function")
    x0 = float(inputs["x0"])
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)
    criterion = str(inputs["stopping_criterion"])
    decimals = int(inputs["decimal_precision"])

    g_expr = parse_expression(text, ("x",))
    symbol = sp.Symbol("x")
    dg_expr = sp.diff(g_expr, symbol)
    g = make_function(g_expr, ("x",), strict=True)
    g_plot = make_function(g_expr, ("x",), strict=False)
    dg = make_function(dg_expr, ("x",), strict=False)
    latex_g = expr_to_latex(g_expr)
    latex_dg = expr_to_latex(dg_expr)

    try:
        gprime0 = float(dg(x0))
    except Exception:
        gprime0 = float("nan")
    contraction = math.isfinite(gprime0) and abs(gprime0) < 1.0

    warnings: list[str] = []
    if math.isfinite(gprime0):
        if abs(gprime0) >= 1.0:
            warnings.append(
                f"|g'(x0)| = {abs(gprime0):.{decimals}g} >= 1 near the guess, so the "
                "fixed-point iteration is not guaranteed to converge (not a contraction)."
            )
    else:
        warnings.append(
            "g'(x0) could not be evaluated, so the contraction condition |g'(x0)| < 1 "
            "cannot be verified."
        )

    tables: list[DataTable] = []
    setup_note = (
        "g is a contraction near x0 (|g'(x0)| < 1), so convergence is expected."
        if contraction
        else "g is not a contraction near x0; the iteration may diverge."
    )
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                f"g(x) = {latex_g},\\quad g'(x) = {latex_dg}"
                f"\\\\ x_0 = {format_num(x0, decimals)},\\quad "
                f"g'(x_0) = {format_num(gprime0, decimals)}"
            ),
            note=setup_note,
        )
    ]

    if original_text is not None and str(original_text).strip() != "":
        f_expr = parse_expression(str(original_text), ("x",))
        suggestion_rows, best = _suggest_rearrangements(f_expr, x0, decimals)
        if suggestion_rows:
            tables.append(
                DataTable(
                    title="Suggested rearrangements g(x) = x + c·f(x)",
                    columns=["Choice of g(x)", "g'(x_0)", "|g'(x_0)|", "Contraction?"],
                    rows=suggestion_rows,
                )
            )
            best_note = (
                f"Best of the listed choices: g(x) = {best} (smallest |g'(x0)|)."
                if best is not None
                else "None of the listed rearrangements is a contraction at x0."
            )
            steps.append(
                Step(
                    title="Suggested rearrangements",
                    latex=(
                        r"f(x) = 0 \;\Rightarrow\; x = x + c\,f(x)"
                        r"\;\Rightarrow\; g_c'(x) = 1 + c\,f'(x)"
                    ),
                    note=best_note,
                )
            )

    iterates: list[float] = [x0]
    rows: list[list[Any]] = []
    root = x0
    iterations_used = 0
    last_dx = 0.0
    converged = False
    diverged = False

    for k in range(1, max_iterations + 1):
        gx = g(root)
        dx = abs(gx - root)
        reached, error = stop_reached(
            criterion, tolerance, f_value=gx - root, x=gx, x_prev=root
        )
        error_value = error if error is not None else dx
        rows.append([k, root, gx, error_value])

        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"x_{{{k}}} = g(x_{{{k - 1}}}) = g({format_num(root, decimals)})"
                    f" = {format_num(gx, decimals)}"
                    f"\\\\ \\text{{Error}} = |x_{{{k}}} - x_{{{k - 1}}}|"
                    f" = {format_num(dx, decimals)}"
                ),
                note=f"Iterate x_{k} = {gx:.{decimals}g}.",
            )
        )

        previous = root
        root = gx
        iterates.append(gx)
        last_dx = dx
        iterations_used = k

        if reached or gx == previous:
            converged = True
            break

        if not math.isfinite(gx) or abs(gx) > _DIVERGENCE_BOUND:
            diverged = True
            warnings.append(
                "The iterates are growing without bound; the fixed-point iteration "
                "has diverged. Try a rearrangement with |g'(x)| < 1."
            )
            break

    if converged:
        status = SolveStatus.CONVERGED
        steps.append(
            Step(
                title="Result",
                latex=(
                    f"\\text{{Stopping criterion met}}\\\\ x \\approx "
                    f"{format_num(root, decimals)},\\quad g(x) = {format_num(g(root), decimals)}"
                ),
                note=(
                    f"Converged in {iterations_used} iteration(s) with rate "
                    f"|g'(x0)| = {abs(gprime0):.{decimals}g}."
                    if math.isfinite(gprime0)
                    else f"Converged in {iterations_used} iteration(s)."
                ),
            )
        )
    elif diverged:
        status = SolveStatus.DIVERGED
        steps.append(
            Step(
                title="Diverged",
                latex=(
                    f"x \\approx {format_num(root, decimals)},\\quad "
                    f"g(x) = {format_num(g(root), decimals)}"
                ),
                note="The iteration is not converging; choose a better rearrangement.",
            )
        )
    else:
        status = SolveStatus.MAX_ITER
        warnings.append(
            f"The stopping criterion was not met within {max_iterations} iterations."
        )
        steps.append(
            Step(
                title="Iteration limit reached",
                latex=(
                    f"x \\approx {format_num(root, decimals)},\\quad "
                    f"g(x) = {format_num(g(root), decimals)}"
                ),
                note=f"Stopped after the maximum of {max_iterations} iterations.",
            )
        )

    relative = abs(last_dx / root) * 100.0 if root != 0 else None

    return SolveResponse(
        method=META.id,
        status=status,
        result={
            "fixed_point": root,
            "iterations": iterations_used,
            "g(root)": g(root),
            "derivative_at_guess": gprime0 if math.isfinite(gprime0) else None,
            "is_contraction": contraction,
            "last_dx": last_dx,
        },
        steps=steps,
        tables=[
            DataTable(
                title="Fixed-point iterations",
                columns=["Iteration", "x_k", "g(x_k)", _error_column(criterion)],
                rows=rows,
            ),
            *tables,
        ],
        plot=_build_plot(
            g_plot, g_expr, x0, root, iterates, gprime0, decimals
        ),
        errors=ErrorInfo(
            absolute=last_dx,
            relative_percent=relative,
            order_of_convergence=1.0 if converged else None,
        ),
        warnings=warnings,
    )


def _marker_y(g_plot: Any, x: float) -> float:
    try:
        value = float(g_plot(x))
    except Exception:
        return 0.0
    return value if math.isfinite(value) else 0.0


def _cobweb_points(seq: list[float], xlo: float, xhi: float) -> tuple[list[float], list[float]]:
    """Staircase (cobweb) polyline for the first few iterates."""
    xs: list[float] = [seq[0]]
    ys: list[float] = [0.0]
    span = xhi - xlo
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        if not (math.isfinite(a) and math.isfinite(b)):
            break
        xs.extend((a, b))
        ys.extend((b, b))
        if not (xlo - span <= b <= xhi + span):
            break
    return xs, ys


def _build_plot(
    g_plot: Any,
    g_expr: Any,
    x0: float,
    root: float,
    iterates: list[float],
    gprime0: float,
    decimals: int,
) -> PlotPayload:
    """Curve y = g(x), the line y = x, the cobweb staircase and the fixed point."""
    finite_iter = [v for v in iterates if math.isfinite(v) and abs(v) < 1e3]
    candidates = [*finite_iter, root, x0]
    lo, hi = min(candidates), max(candidates)
    if hi - lo <= 0:
        lo, hi = x0 - 1.0, x0 + 1.0
    elif hi - lo > 20.0:
        lo, hi = x0 - 3.0, x0 + 3.0
    span = hi - lo
    margin = 0.2 * span
    xlo, xhi = lo - margin, hi + margin

    xs, ys = sample_curve(g_plot, xlo, xhi, points=400)
    y_values = [y for y in ys if math.isfinite(y)]
    y_values.extend((xlo, xhi))
    ylo = min(y_values) - 0.1 * span
    yhi = max(y_values) + 0.1 * span

    cob_x, cob_y = _cobweb_points(iterates[:_MAX_COBWEB_STEPS], xlo, xhi)
    traces: list[dict[str, Any]] = [
        line_trace(xs, ys, name=f"g(x) = {expr_to_latex(g_expr)}"),
        segment_trace(xlo, xlo, xhi, xhi, name="y = x", color="#94a3b8", dash="dash"),
        line_trace(cob_x, cob_y, name="cobweb"),
        marker_trace(root, _marker_y(g_plot, root), "fixed point"),
    ]
    layout: dict[str, Any] = {
        "title": {
            "text": (
                f"Fixed-point iteration from x0 = {format_num(x0, decimals)}"
                + (f" (|g'(x0)| = {format_num(abs(gprime0), decimals)})" if math.isfinite(gprime0) else "")
            )
        },
        "xaxis": {"title": {"text": "x"}, "zeroline": True, "range": [xlo, xhi]},
        "yaxis": {"title": {"text": "y"}, "zeroline": True, "range": [ylo, yhi]},
    }
    return PlotPayload(traces=traces, layout=layout)
