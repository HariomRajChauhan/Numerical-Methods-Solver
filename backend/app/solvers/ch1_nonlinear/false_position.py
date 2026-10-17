"""False position (regula falsi) method.

A bracketing root finder like bisection, but the next estimate is the
x-intercept of the straight line joining ``(a, f(a))`` and ``(b, f(b))`` rather
than the midpoint. This uses the shape of the curve and usually converges much
faster than bisection, while retaining the guarantee of a bracket.
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

_MAX_SECANT_LINES = 6
_STALL_LIMIT = 25


META = MethodMeta(
    id="false_position",
    chapter=Chapter.CH1_NONLINEAR,
    name="False Position Method",
    summary=(
        "Bracketing root finder that interpolates linearly between the endpoints; "
        "faster than bisection but can stall at one end."
    ),
    theory=(
        "The false position method (regula falsi) keeps a sign-changing bracket "
        "[a, b] exactly like bisection, but instead of the midpoint it uses the "
        "x-intercept of the secant line through the two endpoints:\n\n"
        "c = b - f(b)(b - a) / (f(b) - f(a)).\n\n"
        "Because this point lies inside [a, b], the bracket is preserved. The sign "
        "of f(c) then decides which endpoint is replaced, so the method is always "
        "convergent for a valid bracket. It usually converges faster than bisection "
        "because it weights the estimate toward the endpoint with the smaller "
        "|f|; however, for convex functions one endpoint can stop moving, which "
        "makes convergence slow (stalling)."
    ),
    formulas=[
        LabeledLatex(
            label="Regula falsi estimate",
            latex=r"c_k = b_k - f(b_k)\,\frac{b_k - a_k}{f(b_k) - f(a_k)}",
        ),
        LabeledLatex(
            label="Bracket update",
            latex=r"f(a_k)\,f(c_k) < 0 \;\Rightarrow\; b_{k+1}=c_k,\quad \text{else } a_{k+1}=c_k",
        ),
        LabeledLatex(
            label="True relative error",
            latex=r"E_r\% = \left|\frac{c_k - c_{k-1}}{c_k}\right| \times 100\%",
        ),
    ],
    pseudocode=(
        "FalsePosition(f, a, b, tol, max_iter):\n"
        "    fa <- f(a); fb <- f(b)\n"
        "    if fa * fb > 0: stop \"no sign change on [a, b]\"\n"
        "    prev <- a\n"
        "    for k = 1 to max_iter:\n"
        "        c  <- b - fb*(b - a)/(fb - fa)\n"
        "        fc <- f(c)\n"
        "        update bracket using sign of fa*fc\n"
        "        if stopping criterion met: return c, k\n"
        "        prev <- c\n"
        "    return c, max_iter"
    ),
    input_schema=[
        function_field(),
        number_field("a", "Lower bound a", 1.0, help="Left end of the bracket."),
        number_field(
            "b",
            "Upper bound b",
            2.0,
            help="Right end of the bracket; f(a) and f(b) must have opposite signs.",
        ),
        tolerance_field(),
        max_iterations_field(),
        stop_criterion_field(default="function"),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Cubic: x^3 - x - 2 on [1, 2]",
            description="Standard example, root near 1.52138.",
            inputs={
                "function": "x^3 - x - 2",
                "a": 1.0,
                "b": 2.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "function",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Transcendental: cos(x) - x on [0, 1]",
            description="Root near 0.73909.",
            inputs={
                "function": "cos(x) - x",
                "a": 0.0,
                "b": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Exponential: e^x - 3x on [0.5, 1]",
            description="One root of e^x = 3x, near 0.61906.",
            inputs={
                "function": "e^x - 3x",
                "a": 0.5,
                "b": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "relative",
                "decimal_precision": 6,
            },
        ),
    ],
)


def _error_column(criterion: str) -> str:
    if criterion == "function":
        return "Error |f(c)|"
    if criterion == "relative":
        return "Error %"
    return "Error |c_k - c_(k-1)|"


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run the false position method for the validated ``inputs``."""
    text: str = inputs["function"]
    a = float(inputs["a"])
    b = float(inputs["b"])
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)
    criterion = str(inputs["stopping_criterion"])
    decimals = int(inputs["decimal_precision"])

    warnings: list[str] = []
    if a > b:
        a, b = b, a
        warnings.append("a and b were swapped so that a < b.")
    if a == b:
        raise InvalidInputError(
            "'a' and 'b' must be different to form an interval.",
            hint="Give two distinct bounds that bracket the root.",
        )
    a0, b0 = a, b

    expression = parse_expression(text, ("x",))
    f = make_function(expression, ("x",), strict=True)
    f_plot = make_function(expression, ("x",), strict=False)
    latex_f = expr_to_latex(expression)

    fa = f(a)
    fb = f(b)

    if fa == 0.0 or fb == 0.0:
        root = a if fa == 0.0 else b
        return SolveResponse(
            method=META.id,
            status=SolveStatus.CONVERGED,
            result={
                "root": root,
                "iterations": 0,
                "f(root)": fa if fa == 0.0 else fb,
                "final_interval": [a0, b0],
            },
            steps=[
                Step(
                    title="Setup",
                    latex=(
                        f"f(x) = {latex_f},\\quad a = {format_num(a, decimals)},"
                        f"\\quad b = {format_num(b, decimals)}"
                        f"\\\\ f(a) = {format_num(fa, decimals)},\\quad "
                        f"f(b) = {format_num(fb, decimals)}"
                    ),
                    note="An endpoint is already a root, so no iterations are needed.",
                )
            ],
            plot=_build_plot(f_plot, expression, a0, b0, root, [], decimals),
            errors=ErrorInfo(absolute=0.0, relative_percent=0.0),
            warnings=warnings,
        )

    if fa * fb > 0:
        raise InvalidInputError(
            "There is no sign change on [a, b]: f(a) and f(b) have the same sign.",
            hint=(
                "Choose an interval where the function crosses the axis "
                f"(here f(a) = {fa:.6g} and f(b) = {fb:.6g})."
            ),
        )

    columns = ["Iteration", "a", "b", "c", "f(a)", "f(b)", "f(c)", _error_column(criterion)]
    rows: list[list[Any]] = []
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                f"f(x) = {latex_f},\\quad a = {format_num(a, decimals)},"
                f"\\quad b = {format_num(b, decimals)}"
                f"\\\\ f(a) = {format_num(fa, decimals)},\\quad "
                f"f(b) = {format_num(fb, decimals)}"
            ),
            note="f(a) and f(b) have opposite signs, so a root lies in [a, b].",
        )
    ]

    prev: float = a0
    root = (a0 + b0) / 2
    iterations_used = 0
    last_error: float = abs(b0 - a0)
    last_dx: float = abs(b0 - a0) / 2
    converged = False
    left_bracket, right_bracket = a0, b0
    secant_data: list[tuple[float, float, float, float, float]] = []
    a_stall = b_stall = 0

    for k in range(1, max_iterations + 1):
        denominator = fb - fa
        if denominator == 0:
            return failed_response(
                META.id,
                "Division by zero: f(b) equals f(a), so the secant line is horizontal "
                "and gives no new estimate.",
                steps=[
                    *steps,
                    Step(
                        title=f"Iteration {k} - failed",
                        latex=(
                            f"f(b) - f(a) = {format_num(fb, decimals)} - "
                            f"{format_num(fa, decimals)} = 0 \\Rightarrow "
                            r"\text{division by zero}"
                        ),
                        note="Choose a bracket where the endpoint values are not equal.",
                    ),
                ],
                result={
                    "root": prev,
                    "iterations": k - 1,
                    "f(root)": f(prev),
                    "final_interval": [a, b],
                },
                plot=_build_plot(f_plot, expression, a0, b0, prev, secant_data, decimals),
            )
        c = b - fb * (b - a) / denominator
        fc = f(c)
        last_dx = abs(c - prev)
        reached, error = stop_reached(
            criterion, tolerance, f_value=fc, x=c, x_prev=prev
        )
        last_error = error if error is not None else last_dx
        rows.append([k, a, b, c, fa, fb, fc, last_error])
        secant_data.append((a, fa, b, fb, c))

        if fa * fc < 0:
            decision = r"f(a_k)\,f(c_k) < 0 \;\Rightarrow\; \text{root in } [a_k,\,c_k]"
            note = "Root is in the left part, so b <- c."
            new_b, new_fb = c, fc
            a_stall += 1
            b_stall = 0
        else:
            decision = r"f(a_k)\,f(c_k) > 0 \;\Rightarrow\; \text{root in } [c_k,\,b_k]"
            note = "Root is in the right part, so a <- c."
            new_b, new_fb = b, fb
            a_stall = 0
            b_stall += 1
        new_a, new_fa = (a, fa) if fa * fc < 0 else (c, fc)

        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"c_{{{k}}} = b - f(b)\\frac{{b - a}}{{f(b) - f(a)}} = "
                    f"{format_num(b, decimals)} - ({format_num(fb, decimals)})"
                    f"\\frac{{{format_num(b - a, decimals)}}}"
                    f"{{{format_num(denominator, decimals)}}} = {format_num(c, decimals)}"
                    f"\\\\ f(c_{{{k}}}) = {format_num(fc, decimals)}"
                    f"\\\\ {decision}"
                ),
                note=note,
            )
        )

        left_bracket, right_bracket = new_a, new_b

        if reached or fc == 0.0:
            root = c
            iterations_used = k
            converged = True
            break

        a, fa, b, fb = new_a, new_fa, new_b, new_fb
        prev = c

    if not converged and (a_stall >= _STALL_LIMIT or b_stall >= _STALL_LIMIT):
        warnings.append(
            "The bracket stagnated at one endpoint (regula falsi can stall on "
            "convex functions); consider bisection or the Illinois modification."
        )

    if converged:
        status = SolveStatus.CONVERGED
        steps.append(
            Step(
                title="Result",
                latex=(
                    f"\\text{{Stopping criterion met}}\\\\ x \\approx c_{{{iterations_used}}}"
                    f" = {format_num(root, decimals)},\\quad f(x) = {format_num(f(root), decimals)}"
                ),
                note=f"Converged in {iterations_used} iteration(s).",
            )
        )
    else:
        status = SolveStatus.MAX_ITER
        root = c
        iterations_used = max_iterations
        warnings.append(
            f"The stopping criterion was not met within {max_iterations} iterations; "
            "returning the latest estimate."
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

    f_root = f(root)
    relative = abs(last_dx / root) * 100.0 if root != 0 else None

    return SolveResponse(
        method=META.id,
        status=status,
        result={
            "root": root,
            "iterations": iterations_used,
            "f(root)": f_root,
            "final_interval": [left_bracket, right_bracket],
            "last_error": last_error,
            "step_error": last_dx,
        },
        steps=steps,
        tables=[
            DataTable(title="False position iterations", columns=columns, rows=rows),
        ],
        plot=_build_plot(f_plot, expression, a0, b0, root, secant_data, decimals),
        errors=ErrorInfo(absolute=last_dx, relative_percent=relative),
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
    a: float,
    b: float,
    root: float,
    secant_data: list[tuple[float, float, float, float, float]],
    decimals: int,
) -> PlotPayload:
    """Curve of f(x), the secant lines, the iterates and the root marker."""
    span = b - a
    margin = 0.05 * span if span > 0 else max(abs(b), 1.0) * 0.1
    xs, ys = sample_curve(f_plot, a - margin, b + margin, points=400)
    traces: list[dict[str, Any]] = [
        line_trace(xs, ys, name=f"f(x) = {expr_to_latex(expression)}")
    ]
    for index, (ax, ay, bx, by, _cx) in enumerate(secant_data[:_MAX_SECANT_LINES], start=1):
        traces.append(segment_trace(ax, ay, bx, by, name=f"secant {index}"))
    if secant_data:
        traces.append(
            points_trace(
                [entry[4] for entry in secant_data],
                [0.0] * len(secant_data),
                "iterates",
            )
        )
    traces.append(marker_trace(root, _marker_y(f_plot, root), "root"))
    layout: dict[str, Any] = {
        "title": {"text": f"False position on [{format_num(a, decimals)}, {format_num(b, decimals)}]"},
        "xaxis": {"title": {"text": "x"}, "zeroline": True},
        "yaxis": {"title": {"text": "f(x)"}, "zeroline": True},
    }
    return PlotPayload(traces=traces, layout=layout)
