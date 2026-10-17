"""Newton-Raphson method.

An open root finder for ``f(x) = 0`` that uses the tangent line at the current
iterate: ``x(k+1) = x(k) - f(x(k))/f'(x(k))``. Near a simple root it converges
quadratically (the number of correct digits doubles each step), but it needs the
derivative and can fail if ``f'(x)`` vanishes or if the guess is poor.

The derivative is obtained symbolically with SymPy from ``f(x)``, or supplied
manually by the user when it is simpler to type.
"""

from __future__ import annotations

import math
from typing import Any

import sympy as sp

from app.core.errors import InvalidInputError
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
    estimate_order,
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
_MAX_TANGENT_LINES = 6
_OSCILLATION_TOL = 1e-12


META = MethodMeta(
    id="newton_raphson",
    chapter=Chapter.CH1_NONLINEAR,
    name="Newton-Raphson Method",
    summary=(
        "Open root finder using the tangent line at the current estimate; "
        "converges quadratically near a simple root but needs the derivative."
    ),
    theory=(
        "Newton-Raphson starts from a single guess x(0) and follows the tangent "
        "line of f at the current point down to the x-axis. Solving for the "
        "intercept gives the iteration\n\n"
        "x(k+1) = x(k) - f(x(k)) / f'(x(k)).\n\n"
        "Because a smooth function is well approximated by its tangent line close "
        "to the root, the error contracts quadratically: if the function has a "
        "simple root (f'(x*) != 0) and the guess is close enough, the number of "
        "correct significant digits roughly doubles every iteration (p = 2).\n\n"
        "The method is 'open': it keeps no bracket, so it can diverge or jump away "
        "when the guess is poor, when f'(x) is close to zero, or when f'(x(k)) = 0 "
        "exactly (division by zero). Oscillation in a two-point cycle is also "
        "possible. Good starting values come from the Intermediate Value Theorem "
        "(a sign change), from a quick hand sketch, or from a few bisection steps."
    ),
    formulas=[
        LabeledLatex(
            label="Newton update",
            latex=r"x_{k+1} = x_k - \frac{f(x_k)}{f'(x_k)}",
        ),
        LabeledLatex(
            label="Tangent line at x_k",
            latex=r"y = f(x_k) + f'(x_k)\,(x - x_k)",
        ),
        LabeledLatex(
            label="Error relation",
            latex=r"e_{k+1} = \frac{f''(\xi)}{2\,f'(x_k)}\,e_k^{2}",
        ),
        LabeledLatex(
            label="Order of convergence",
            latex=r"\text{quadratic},\quad p = 2",
        ),
    ],
    pseudocode=(
        "NewtonRaphson(f, f', x0, tol, max_iter):\n"
        "    x <- x0\n"
        "    for k = 1 to max_iter:\n"
        "        fx  <- f(x)\n"
        "        dfx <- f'(x)\n"
        "        if dfx = 0: stop \"zero derivative (division by zero)\"\n"
        "        x_new <- x - fx / dfx\n"
        "        err <- |x_new - x|\n"
        "        if stopping criterion met: return x_new, k\n"
        "        if x_new is not finite or |x_new| > 1e10: stop \"diverged\"\n"
        "        if x_new = x_{k-2}: warn \"two-point oscillation\"\n"
        "        x <- x_new\n"
        "    return x, max_iter"
    ),
    input_schema=[
        function_field(placeholder="x^3 - x - 2"),
        InputField(
            key="derivative",
            label="Derivative f'(x) (optional)",
            type="function",
            variable="x",
            required=False,
            default=None,
            placeholder="3*x^2 - 1",
            help="Leave blank to differentiate f(x) automatically with SymPy.",
        ),
        number_field(
            "x0",
            "Initial guess x0",
            1.5,
            help="A single starting value close to the root.",
        ),
        tolerance_field(),
        max_iterations_field(),
        stop_criterion_field(default="interval"),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Cubic: x^3 - x - 2 from 1.5",
            description="Derivative taken automatically; root near 1.52138.",
            inputs={
                "function": "x^3 - x - 2",
                "derivative": "",
                "x0": 1.5,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Transcendental: cos(x) - x from 1",
            description="Root near 0.73909.",
            inputs={
                "function": "cos(x) - x",
                "derivative": "",
                "x0": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "function",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Square root of 2 with a manual derivative",
            description="x^2 - 2, f'(x) = 2x typed by hand; root 1.41421.",
            inputs={
                "function": "x^2 - 2",
                "derivative": "2*x",
                "x0": 1.0,
                "tolerance": 1e-8,
                "max_iterations": 50,
                "stopping_criterion": "interval",
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
    """Run Newton-Raphson for the validated ``inputs``."""
    text: str = inputs["function"]
    derivative_text = inputs.get("derivative")
    x0 = float(inputs["x0"])
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)
    criterion = str(inputs["stopping_criterion"])
    decimals = int(inputs["decimal_precision"])

    expression = parse_expression(text, ("x",))
    symbol = sp.Symbol("x")
    manual = derivative_text is not None and str(derivative_text).strip() != ""
    if manual:
        dexpr = parse_expression(str(derivative_text), ("x",))
    else:
        dexpr = sp.diff(expression, symbol)

    if dexpr == 0:
        raise InvalidInputError(
            "The derivative is identically zero, so Newton-Raphson cannot be applied.",
            hint="The method needs f'(x) != 0; try Bisection or the Secant method.",
        )

    f = make_function(expression, ("x",), strict=True)
    df = make_function(dexpr, ("x",), strict=True)
    f_plot = make_function(expression, ("x",), strict=False)
    latex_f = expr_to_latex(expression)
    latex_df = expr_to_latex(dexpr)
    source = "supplied derivative" if manual else "derivative from SymPy"

    warnings: list[str] = []
    rows: list[list[Any]] = []
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                f"f(x) = {latex_f},\\quad f'(x) = {latex_df}"
                f"\\\\ x_0 = {format_num(x0, decimals)},\\quad "
                f"f(x_0) = {format_num(f(x0), decimals)}"
            ),
            note=f"Working with the {source}.",
        )
    ]

    if f(x0) == 0.0:
        return SolveResponse(
            method=META.id,
            status=SolveStatus.CONVERGED,
            result={
                "root": x0,
                "iterations": 0,
                "f(root)": 0.0,
                "estimated_order": None,
            },
            steps=[*steps, Step(title="Result", latex=f"x_0 = {format_num(x0, decimals)}", note="The initial guess is already a root.")],
            tables=[],
            plot=_build_plot(f_plot, expression, x0, x0, [], decimals),
            errors=ErrorInfo(absolute=0.0, relative_percent=0.0, order_of_convergence=2.0),
            warnings=warnings,
        )

    x = x0
    history: list[float] = [x0]
    tangent_data: list[tuple[float, float, float]] = []
    step_errors: list[float] = []
    root = x0
    iterations_used = 0
    last_dx = 0.0
    converged = False
    diverged = False
    failed = False
    oscillation_warned = False

    for k in range(1, max_iterations + 1):
        fk = f(x)
        dk = df(x)
        if dk == 0.0:
            failed = True
            root = x
            iterations_used = k - 1
            warnings.append(
                f"f'(x) = 0 at x = {x:.{decimals}g}: Newton-Raphson cannot continue "
                "(division by zero)."
            )
            steps.append(
                Step(
                    title=f"Iteration {k} - failed",
                    latex=(
                        f"f'(x_{{{k - 1}}}) = 0 \\Rightarrow "
                        r"\text{division by zero, cannot form } x_{k}"
                    ),
                    note="The tangent line is horizontal, so it never meets the x-axis here.",
                )
            )
            break

        x_new = x - fk / dk
        last_dx = abs(x_new - x)
        f_new = f(x_new)
        reached, error = stop_reached(
            criterion, tolerance, f_value=f_new, x=x_new, x_prev=x
        )
        error_value = error if error is not None else last_dx
        rows.append([k, x, fk, dk, x_new, error_value])
        tangent_data.append((x, fk, x_new))
        step_errors.append(last_dx)

        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"x_{{{k}}} = x_{{{k - 1}}} - \\frac{{f(x_{{{k - 1}}})}}"
                    f"{{f'(x_{{{k - 1}}})}} = {format_num(x, decimals)} - "
                    f"\\frac{{{format_num(fk, decimals)}}}{{{format_num(dk, decimals)}}}"
                    f" = {format_num(x_new, decimals)}"
                    f"\\\\ f(x_{{{k}}}) = {format_num(f_new, decimals)}"
                ),
                note=f"Next estimate x_{k} = {x_new:.{decimals}g}.",
            )
        )

        if reached or f_new == 0.0:
            root = x_new
            iterations_used = k
            converged = True
            break

        if not math.isfinite(x_new) or abs(x_new) > _DIVERGENCE_BOUND:
            root = x_new
            iterations_used = k
            diverged = True
            warnings.append(
                "The iterates are growing without bound; Newton-Raphson has diverged."
            )
            break

        if (
            not oscillation_warned
            and len(history) >= 2
            and abs(x_new - history[-2]) <= _OSCILLATION_TOL * max(1.0, abs(x_new))
            and last_dx > tolerance
        ):
            warnings.append(
                "The iterate repeats every two steps (two-point oscillation); "
                "Newton-Raphson will not converge from this guess. Try a different x0."
            )
            oscillation_warned = True

        history.append(x_new)
        x = x_new

    if failed:
        status = SolveStatus.FAILED
    elif converged:
        status = SolveStatus.CONVERGED
        steps.append(
            Step(
                title="Result",
                latex=(
                    f"\\text{{Stopping criterion met}}\\\\ x \\approx "
                    f"{format_num(root, decimals)},\\quad f(x) = {format_num(f(root), decimals)}"
                ),
                note=f"Converged in {iterations_used} iteration(s).",
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
                note="The sequence is not converging; try a better initial guess.",
            )
        )
    else:
        root = x
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

    order = estimate_order(step_errors) if converged else None
    if order is None and converged:
        order = 2.0
    relative = abs(last_dx / root) * 100.0 if root != 0 else None

    return SolveResponse(
        method=META.id,
        status=status,
        result={
            "root": root,
            "iterations": iterations_used,
            "f(root)": f(root),
            "estimated_order": order,
        },
        steps=steps,
        tables=[
            DataTable(
                title="Newton-Raphson iterations",
                columns=[
                    "Iteration",
                    "x_k",
                    "f(x_k)",
                    "f'(x_k)",
                    "x_(k+1)",
                    _error_column(criterion),
                ],
                rows=rows,
            )
        ],
        plot=_build_plot(f_plot, expression, x0, root, tangent_data, decimals),
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
    root: float,
    tangent_data: list[tuple[float, float, float]],
    decimals: int,
) -> PlotPayload:
    """Curve of f(x), the tangent lines, the iterates and the root marker."""
    candidates = [x0, root]
    for x_k, _fk, x_next in tangent_data[:_MAX_TANGENT_LINES]:
        candidates.extend((x_k, x_next))
    finite = [value for value in candidates if math.isfinite(value)]
    lo, hi = (min(finite), max(finite)) if finite else (x0 - 1.0, x0 + 1.0)
    span = hi - lo
    if not math.isfinite(span) or span <= 0:
        span = max(abs(lo), 1.0)
    if span > 1e6:
        lo, hi = x0 - 5.0, x0 + 5.0
        span = hi - lo
    margin = 0.15 * span
    xs, ys = sample_curve(f_plot, lo - margin, hi + margin, points=400)
    traces: list[dict[str, Any]] = [
        line_trace(xs, ys, name=f"f(x) = {expr_to_latex(expression)}")
    ]
    for index, (x_k, fk, x_next) in enumerate(tangent_data[:_MAX_TANGENT_LINES], start=1):
        if math.isfinite(x_k) and math.isfinite(fk) and math.isfinite(x_next):
            traces.append(
                segment_trace(x_k, fk, x_next, 0.0, name=f"tangent {index}", dash="dash")
            )
    if tangent_data:
        traces.append(
            points_trace(
                [entry[2] for entry in tangent_data],
                [0.0] * len(tangent_data),
                "iterates",
            )
        )
    traces.append(marker_trace(root, _marker_y(f_plot, root), "root"))
    layout: dict[str, Any] = {
        "title": {"text": f"Newton-Raphson from x0 = {format_num(x0, decimals)}"},
        "xaxis": {"title": {"text": "x"}, "zeroline": True},
        "yaxis": {"title": {"text": "f(x)"}, "zeroline": True},
    }
    return PlotPayload(traces=traces, layout=layout)
