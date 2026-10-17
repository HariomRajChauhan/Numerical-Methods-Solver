"""Secant method.

An open root finder that replaces the derivative of Newton-Raphson with a
finite difference across the two most recent iterates. It needs two starting
values and no derivative, and converges super-linearly with order close to the
golden ratio (about 1.618). It is not guaranteed to stay near the root.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.errors import InvalidInputError
from app.core.models import (
    Chapter,
    DataTable,
    ErrorInfo,
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
    estimate_order,
    failed_response,
    format_num,
    function_field,
    line_trace,
    marker_trace,
    max_iterations_field,
    number_field,
    points_trace,
    precision_field,
    sample_curve,
    segment_trace,
    stop_criterion_field,
    stop_reached,
    tolerance_field,
)

_DIVERGENCE_BOUND = 1e10
_MAX_SECANT_LINES = 6
_GOLDEN = (1.0 + math.sqrt(5.0)) / 2.0


META = MethodMeta(
    id="secant",
    chapter=Chapter.CH1_NONLINEAR,
    name="Secant Method",
    summary=(
        "Open root finder using a secant line through the last two iterates; "
        "needs no derivative and converges super-linearly."
    ),
    theory=(
        "The secant method keeps two recent approximations x(k-1) and x(k) and "
        "draws the straight line (secant) through the points "
        "(x(k-1), f(x(k-1))) and (x(k), f(x(k))). Its x-intercept is the next "
        "estimate:\n\n"
        "x(k+1) = x(k) - f(x(k)) (x(k) - x(k-1)) / (f(x(k)) - f(x(k-1))).\n\n"
        "This is Newton-Raphson with the derivative approximated by the divided "
        "difference, so no derivative is required. Near a simple root the order of "
        "convergence is the golden ratio (about 1.618), between the linear order of "
        "bisection and the quadratic order of Newton-Raphson. Because it is an open "
        "method it does not maintain a bracket and can diverge or fail if the two "
        "starting values give equal function values."
    ),
    formulas=[
        LabeledLatex(
            label="Secant update",
            latex=r"x_{k+1} = x_k - f(x_k)\,\frac{x_k - x_{k-1}}{f(x_k) - f(x_{k-1})}",
        ),
        LabeledLatex(
            label="Order of convergence",
            latex=r"p = \frac{1+\sqrt{5}}{2} \approx 1.618",
        ),
        LabeledLatex(
            label="True relative error",
            latex=r"E_r\% = \left|\frac{x_{k+1} - x_k}{x_{k+1}}\right| \times 100\%",
        ),
    ],
    pseudocode=(
        "Secant(f, x0, x1, tol, max_iter):\n"
        "    f0 <- f(x0); f1 <- f(x1)\n"
        "    for k = 1 to max_iter:\n"
        "        d <- f1 - f0\n"
        "        if d = 0: stop \"division by zero (f equal at guesses)\"\n"
        "        x2 <- x1 - f1*(x1 - x0)/d\n"
        "        if stopping criterion met: return x2, k\n"
        "        x0 <- x1; f0 <- f1\n"
        "        x1 <- x2; f1 <- f(x2)\n"
        "    return x1, max_iter"
    ),
    input_schema=[
        function_field(),
        number_field("x0", "First guess x0", 1.0, help="An initial approximation to the root."),
        number_field(
            "x1",
            "Second guess x1",
            2.0,
            help="A second, different initial approximation.",
        ),
        tolerance_field(default=1e-6),
        max_iterations_field(),
        stop_criterion_field(default="interval"),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Cubic: x^3 - x - 2 from 1 and 2",
            description="Root near 1.52138.",
            inputs={
                "function": "x^3 - x - 2",
                "x0": 1.0,
                "x1": 2.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Transcendental: cos(x) - x from 0 and 1",
            description="Root near 0.73909.",
            inputs={
                "function": "cos(x) - x",
                "x0": 0.0,
                "x1": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Exponential: e^x - 3x from 0 and 1",
            description="Root near 0.61906.",
            inputs={
                "function": "e^x - 3x",
                "x0": 0.0,
                "x1": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "function",
                "decimal_precision": 6,
            },
        ),
    ],
)


def _error_column(criterion: str) -> str:
    if criterion == "function":
        return "Error |f(x)|"
    if criterion == "relative":
        return "Error %"
    return "Error |x_k - x_(k-1)|"


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run the secant method for the validated ``inputs``."""
    text: str = inputs["function"]
    x0 = float(inputs["x0"])
    x1 = float(inputs["x1"])
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)
    criterion = str(inputs["stopping_criterion"])
    decimals = int(inputs["decimal_precision"])

    if x0 == x1:
        raise InvalidInputError(
            "The two initial guesses must be different.",
            hint="Give two distinct starting points, e.g. 1 and 2.",
        )

    expression = parse_expression(text, ("x",))
    f = make_function(expression, ("x",), strict=True)
    f_plot = make_function(expression, ("x",), strict=False)
    latex_f = expr_to_latex(expression)

    f0 = f(x0)
    f1 = f(x1)
    x0_init, x1_init = x0, x1

    columns = ["Iteration", "x_(k-1)", "x_k", "x_(k+1)", "f(x_(k-1))", "f(x_k)", "f(x_(k+1))", _error_column(criterion)]
    rows: list[list[Any]] = []
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                f"f(x) = {latex_f},\\quad x_0 = {format_num(x0, decimals)},"
                f"\\quad x_1 = {format_num(x1, decimals)}"
                f"\\\\ f(x_0) = {format_num(f0, decimals)},\\quad "
                f"f(x_1) = {format_num(f1, decimals)}"
            ),
            note="The secant method needs two starting values but no derivative.",
        )
    ]

    warnings: list[str] = []
    secant_data: list[tuple[float, float, float, float, float]] = []
    step_errors: list[float] = []
    converged = False
    diverged = False
    root = x1
    iterations_used = 0
    last_dx = abs(x1 - x0)

    for k in range(1, max_iterations + 1):
        denominator = f1 - f0
        if denominator == 0:
            return failed_response(
                META.id,
                "Division by zero: f(x0) equals f(x1), so the secant line is horizontal "
                "and gives no new estimate.",
                steps=[
                    *steps,
                    Step(
                        title=f"Iteration {k} - failed",
                        latex=(
                            f"f(x_{{{k - 1}}}) - f(x_{{{k}}}) = "
                            f"{format_num(f0, decimals)} - {format_num(f1, decimals)} = 0"
                            " \\Rightarrow \\text{division by zero}"
                        ),
                        note="Change the starting guesses so the function values differ.",
                    ),
                ],
                result={
                    "root": x1,
                    "iterations": k - 1,
                    "f(root)": f1,
                    "step_error": abs(x1 - x0),
                    "estimated_order": None,
                },
                plot=_build_plot(
                    f_plot, expression, x0_init, x1_init, x1, secant_data, decimals
                ),
            )
        x2 = x1 - f1 * (x1 - x0) / denominator
        f2 = f(x2)
        last_dx = abs(x2 - x1)
        reached, error = stop_reached(
            criterion, tolerance, f_value=f2, x=x2, x_prev=x1
        )
        error_value = error if error is not None else last_dx
        rows.append([k, x0, x1, x2, f0, f1, f2, error_value])
        secant_data.append((x0, f0, x1, f1, x2))
        step_errors.append(last_dx)

        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"x_{{{k + 1}}} = x_{{{k}}} - f(x_{{{k}}})"
                    f"\\frac{{x_{{{k}}} - x_{{{k - 1}}}}}{{f(x_{{{k}}}) - f(x_{{{k - 1}}})}} = "
                    f"{format_num(x1, decimals)} - ({format_num(f1, decimals)})"
                    f"\\frac{{{format_num(x1 - x0, decimals)}}}"
                    f"{{{format_num(denominator, decimals)}}} = {format_num(x2, decimals)}"
                    f"\\\\ f(x_{{{k + 1}}}) = {format_num(f2, decimals)}"
                ),
                note=f"Next estimate x_{k + 1} = {x2:.{decimals}g}.",
            )
        )

        if reached or f2 == 0.0:
            root = x2
            iterations_used = k
            converged = True
            break

        if not math.isfinite(x2) or abs(x2) > _DIVERGENCE_BOUND:
            root = x2
            iterations_used = k
            diverged = True
            warnings.append(
                "The iterates are growing without bound; the secant method has diverged."
            )
            break

        x0, f0 = x1, f1
        x1, f1 = x2, f2

    if not converged and not diverged:
        root = x1
        iterations_used = max_iterations
        status = SolveStatus.MAX_ITER
        warnings.append(
            f"The stopping criterion was not met within {max_iterations} iterations."
        )
        steps.append(
            Step(
                title="Iteration limit reached",
                latex=(
                    f"x \\approx {format_num(root, decimals)},\\quad "
                    f"f(x) = {format_num(f(root), decimals)}"
                ),
                note=f"Stopped after the maximum of {max_iterations} iterations.",
            )
        )
    elif diverged:
        status = SolveStatus.DIVERGED
        steps.append(
            Step(
                title="Diverged",
                latex=(
                    f"x \\approx {format_num(root, decimals)},\\quad "
                    f"f(x) = {format_num(f(root), decimals)}"
                ),
                note="The sequence is not converging; try different starting guesses.",
            )
        )
    else:
        status = SolveStatus.CONVERGED
        steps.append(
            Step(
                title="Result",
                latex=(
                    f"\\text{{Stopping criterion met}}\\\\ x \\approx {format_num(root, decimals)}"
                    f",\\quad f(x) = {format_num(f(root), decimals)}"
                ),
                note=f"Converged in {iterations_used} iteration(s).",
            )
        )

    order = estimate_order(step_errors)
    if order is None and converged and len(step_errors) >= 2:
        order = _GOLDEN
    relative = abs(last_dx / root) * 100.0 if root != 0 else None

    return SolveResponse(
        method=META.id,
        status=status,
        result={
            "root": root,
            "iterations": iterations_used,
            "f(root)": f(root),
            "step_error": last_dx,
            "estimated_order": order,
        },
        steps=steps,
        tables=[DataTable(title="Secant iterations", columns=columns, rows=rows)],
        plot=_build_plot(f_plot, expression, x0_init, x1_init, root, secant_data, decimals),
        errors=ErrorInfo(
            absolute=last_dx,
            relative_percent=relative,
            order_of_convergence=order,
        ),
        warnings=warnings,
    )


def _marker_y(f_plot: Any, x: float) -> float:
    try:
        value = float(f_plot(x))
    except Exception:
        return 0.0
    return value if math.isfinite(value) else 0.0


def _build_plot(
    f_plot: Any,
    expression: Any,
    x0: float,
    x1: float,
    root: float,
    secant_data: list[tuple[float, float, float, float, float]],
    decimals: int,
) -> PlotPayload:
    """Curve of f(x), the secant lines, the iterates and the root marker."""
    candidates = [x0, x1, root]
    for entry in secant_data[:_MAX_SECANT_LINES]:
        candidates.extend((entry[0], entry[2], entry[4]))
    finite = [value for value in candidates if math.isfinite(value)]
    lo, hi = (min(finite), max(finite)) if finite else (x0, x1)
    span = hi - lo
    if not math.isfinite(span) or span <= 0:
        span = max(abs(lo), 1.0)
    if span > 1e6:
        center = (x0 + x1) / 2
        lo, hi = center - 5.0, center + 5.0
        span = hi - lo
    margin = 0.15 * span
    xs, ys = sample_curve(f_plot, lo - margin, hi + margin, points=400)
    traces: list[dict[str, Any]] = [
        line_trace(xs, ys, name=f"f(x) = {expr_to_latex(expression)}")
    ]
    for index, (ax, ay, bx, by, _cx) in enumerate(secant_data[:_MAX_SECANT_LINES], start=1):
        traces.append(segment_trace(ax, ay, bx, by, name=f"secant {index}"))
    if secant_data:
        traces.append(
            points_trace([entry[4] for entry in secant_data], [0.0] * len(secant_data), "iterates")
        )
    traces.append(marker_trace(root, _marker_y(f_plot, root), "root"))
    layout: dict[str, Any] = {
        "title": {"text": f"Secant method from x0={format_num(x0, decimals)}, x1={format_num(x1, decimals)}"},
        "xaxis": {"title": {"text": "x"}, "zeroline": True},
        "yaxis": {"title": {"text": "f(x)"}, "zeroline": True},
    }
    return PlotPayload(traces=traces, layout=layout)
