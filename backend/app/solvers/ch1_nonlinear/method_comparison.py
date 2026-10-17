"""Method comparison.

Run several Chapter 1 root finders on the same equation f(x) = 0 and compare
them side by side: iteration counts, final estimate, residual, error measured
against a reference root, estimated order of convergence and status. A single
semilog error-versus-iteration plot shows how quickly each method closes in.

This module owns no iteration logic of its own. It orchestrates the existing
solvers through their registered ``solve`` functions, so each method stays
defined in exactly one place. A method that fails or diverges is reported in the
table and never breaks the comparison.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.errors import InvalidInputError, NMSBaseError
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
    boolean_field,
    format_num,
    function_field,
    max_iterations_field,
    number_field,
    precision_field,
    stop_criterion_field,
    tolerance_field,
)
from app.solvers.ch1_nonlinear.bisection import solve as _bisection_solve
from app.solvers.ch1_nonlinear.false_position import solve as _false_position_solve
from app.solvers.ch1_nonlinear.fixed_point import solve as _fixed_point_solve
from app.solvers.ch1_nonlinear.newton_raphson import solve as _newton_solve
from app.solvers.ch1_nonlinear.secant import solve as _secant_solve

_PLOT_ERROR_FLOOR = 1e-16
_PLOT_ERROR_CAP = 1e2

_METHOD_ORDER = ("bisection", "false_position", "secant", "newton_raphson", "fixed_point")
_METHOD_NAMES: dict[str, str] = {
    "bisection": "Bisection",
    "false_position": "False Position",
    "secant": "Secant",
    "newton_raphson": "Newton-Raphson",
    "fixed_point": "Fixed-Point",
}
_RUNNERS: dict[str, Callable[[dict[str, Any], SolverLimits], SolveResponse]] = {
    "bisection": _bisection_solve,
    "false_position": _false_position_solve,
    "secant": _secant_solve,
    "newton_raphson": _newton_solve,
    "fixed_point": _fixed_point_solve,
}
# Column index of the "next iterate" in each method's first data table.
_ITERATE_INDEX: dict[str, int] = {
    "bisection": 3,
    "false_position": 3,
    "secant": 3,
    "newton_raphson": 4,
    "fixed_point": 2,
}


@dataclass
class _Outcome:
    """One method's result inside the comparison."""

    method_id: str
    name: str
    status: str
    root: float | None
    iterations: int | None
    order: float | None
    series: list[float]
    residual: float | None = None
    error: float | None = None
    messages: list[str] = field(default_factory=list)


META = MethodMeta(
    id="method_comparison",
    chapter=Chapter.CH1_NONLINEAR,
    name="Method Comparison",
    summary=(
        "Run bisection, false position, secant, Newton-Raphson and/or fixed-point "
        "iteration on the same equation and compare iterations, accuracy and "
        "convergence order on one semilog plot."
    ),
    theory=(
        "Solving f(x) = 0 can be done with several different methods. Comparing "
        "them on the same problem shows the trade-offs between reliability and "
        "speed.\n\n"
        "Bracketing methods (bisection, false position) start from an interval "
        "[a, b] with f(a)*f(b) < 0. By the Intermediate Value Theorem the root stays "
        "trapped in the bracket, so they cannot diverge - but they can be slow.\n\n"
        "Open methods (secant, Newton-Raphson, fixed-point iteration) start from one "
        "or two guesses and keep no bracket. Near a simple root they converge much "
        "faster, but they can diverge, stall or jump away if the guesses are poor.\n\n"
        "The speed is described by the order of convergence p. If the error at step "
        "k behaves like e(k+1) ~ C*e(k)^p, then on a plot of log|e| against the "
        "iteration number each method is a straight line whose slope is log10(p): "
        "bisection is linear (p = 1, one extra decimal digit every 3-4 steps), the "
        "secant method is super-linear (p ~ 1.618), Newton-Raphson is quadratic "
        "(p = 2) near a simple root, and fixed-point iteration is linear with rate "
        "|g'(x*)|. A lower, steeper line means a faster, more accurate method."
    ),
    formulas=[
        LabeledLatex(
            label="Error measured against a reference root x*",
            latex=r"e_k = \left|x_k - x^{*}\right|",
        ),
        LabeledLatex(
            label="Order of convergence",
            latex=r"e_{k+1} \approx C\,e_k^{\,p}",
        ),
        LabeledLatex(label="Bisection: linear", latex=r"p = 1"),
        LabeledLatex(label="Secant: golden ratio", latex=r"p = \frac{1+\sqrt{5}}{2} \approx 1.618"),
        LabeledLatex(label="Newton-Raphson: quadratic", latex=r"p = 2"),
        LabeledLatex(
            label="Fixed-point: linear rate",
            latex=r"e_{k+1} \approx |g'(x^{*})|\,e_k",
        ),
    ],
    pseudocode=(
        "Compare(f, a, b, x0, x1, g, methods, tol, max_iter):\n"
        "    for each selected method in methods:\n"
        "        try: result <- run method(f, a, b, x0, x1, g, tol, max_iter)\n"
        "        except: record status \"error\" and continue\n"
        "    pick reference root x* from the most accurate converged result\n"
        "    for each result:\n"
        "        residual <- |f(root)|;  error <- |root - x*|\n"
        "    build the comparison table and the semilog error-vs-iteration plot"
    ),
    input_schema=[
        function_field(placeholder="x^3 - x - 2"),
        number_field(
            "a",
            "Lower bound a (bracketing methods)",
            1.0,
            help="Left end of the bracket used by bisection and false position.",
        ),
        number_field(
            "b",
            "Upper bound b (bracketing methods)",
            2.0,
            help="Right end of the bracket; f(a) and f(b) must have opposite signs.",
        ),
        number_field(
            "x0",
            "Initial guess x0 (open methods)",
            1.5,
            help="First starting value for secant, Newton-Raphson and fixed-point.",
        ),
        number_field(
            "x1",
            "Second guess x1 (secant only)",
            2.0,
            help="Second starting value; only the secant method needs it.",
        ),
        function_field(
            key="g",
            label="Fixed-point g(x) (optional)",
            placeholder="cos(x)",
            help=(
                "Right-hand side of x = g(x). Leave blank to use g(x) = x + f(x). "
                "Only used when fixed-point iteration is selected."
            ),
            required=False,
        ),
        tolerance_field(),
        max_iterations_field(),
        stop_criterion_field(default="function"),
        precision_field(),
        boolean_field("run_bisection", "Compare Bisection", True),
        boolean_field("run_false_position", "Compare False Position", True),
        boolean_field("run_secant", "Compare Secant", True),
        boolean_field("run_newton_raphson", "Compare Newton-Raphson", True),
        boolean_field("run_fixed_point", "Compare Fixed-Point Iteration", False),
    ],
    examples=[
        MethodExample(
            name="Cubic: x^3 - x - 2",
            description="Bracketing and open methods side by side, root near 1.52138.",
            inputs={
                "function": "x^3 - x - 2",
                "a": 1.0,
                "b": 2.0,
                "x0": 1.5,
                "x1": 2.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "function",
                "decimal_precision": 6,
                "run_bisection": True,
                "run_false_position": True,
                "run_secant": True,
                "run_newton_raphson": True,
                "run_fixed_point": False,
            },
        ),
        MethodExample(
            name="Transcendental: cos(x) - x",
            description="All five methods including fixed-point g(x) = cos(x), root near 0.73909.",
            inputs={
                "function": "cos(x) - x",
                "a": 0.0,
                "b": 1.0,
                "x0": 1.0,
                "x1": 0.5,
                "g": "cos(x)",
                "tolerance": 1e-8,
                "max_iterations": 60,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
                "run_bisection": True,
                "run_false_position": True,
                "run_secant": True,
                "run_newton_raphson": True,
                "run_fixed_point": True,
            },
        ),
        MethodExample(
            name="Divergent open method: atan(x) from 2",
            description="Newton-Raphson diverges while the bracketing methods still work.",
            inputs={
                "function": "atan(x)",
                "a": -1.0,
                "b": 1.0,
                "x0": 2.0,
                "x1": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 30,
                "stopping_criterion": "function",
                "decimal_precision": 6,
                "run_bisection": True,
                "run_false_position": True,
                "run_secant": False,
                "run_newton_raphson": True,
                "run_fixed_point": False,
            },
        ),
    ],
)


def _method_inputs(
    method_id: str,
    *,
    f_text: str,
    a: float,
    b: float,
    x0: float,
    x1: float,
    g_text: str,
    tolerance: float,
    max_iterations: int,
    criterion: str,
    decimals: int,
) -> dict[str, Any]:
    """Build the input dict each underlying solver expects."""
    common: dict[str, Any] = {
        "tolerance": tolerance,
        "max_iterations": max_iterations,
        "stopping_criterion": criterion,
        "decimal_precision": decimals,
    }
    if method_id in ("bisection", "false_position"):
        return {"function": f_text, "a": a, "b": b, **common}
    if method_id == "secant":
        return {"function": f_text, "x0": x0, "x1": x1, **common}
    if method_id == "newton_raphson":
        return {"function": f_text, "derivative": None, "x0": x0, **common}
    # fixed-point iteration: use the supplied g, otherwise g(x) = x + f(x).
    g = g_text.strip() if g_text else ""
    if not g:
        g = f"x + ({f_text})"
    return {"function": g, "original_function": f_text, "x0": x0, **common}


def _safe_value(fn: Callable[[Any], Any], x: float) -> float | None:
    """Evaluate ``fn`` at ``x``, returning ``None`` when it is undefined."""
    try:
        value = float(fn(x))
    except Exception:
        return None
    return value if math.isfinite(value) else None


def _extract_root(method_id: str, response: SolveResponse) -> float | None:
    key = "fixed_point" if method_id == "fixed_point" else "root"
    value = response.result.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(float(value)) else None


def _extract_series(method_id: str, response: SolveResponse) -> list[float]:
    if not response.tables:
        return []
    index = _ITERATE_INDEX[method_id]
    series: list[float] = []
    for row in response.tables[0].rows:
        if index >= len(row):
            continue
        cell = row[index]
        if isinstance(cell, bool) or not isinstance(cell, (int, float)):
            continue
        value = float(cell)
        if math.isfinite(value):
            series.append(value)
    return series


def _run_selected(
    selected: list[str],
    limits: SolverLimits,
    *,
    f_text: str,
    a: float,
    b: float,
    x0: float,
    x1: float,
    g_text: str,
    tolerance: float,
    max_iterations: int,
    criterion: str,
    decimals: int,
) -> list[_Outcome]:
    """Run every selected method, capturing failures instead of raising."""
    outcomes: list[_Outcome] = []
    for method_id in selected:
        name = _METHOD_NAMES[method_id]
        method_inputs = _method_inputs(
            method_id,
            f_text=f_text,
            a=a,
            b=b,
            x0=x0,
            x1=x1,
            g_text=g_text,
            tolerance=tolerance,
            max_iterations=max_iterations,
            criterion=criterion,
            decimals=decimals,
        )
        try:
            response = _RUNNERS[method_id](method_inputs, limits)
        except NMSBaseError as exc:
            outcomes.append(
                _Outcome(method_id, name, "error", None, None, None, [], messages=[exc.message])
            )
            continue
        except Exception:
            outcomes.append(
                _Outcome(
                    method_id,
                    name,
                    "error",
                    None,
                    None,
                    None,
                    [],
                    messages=["The method could not be applied to these inputs."],
                )
            )
            continue

        raw_iterations = response.result.get("iterations")
        iterations = (
            int(raw_iterations)
            if isinstance(raw_iterations, int) and not isinstance(raw_iterations, bool)
            else None
        )
        outcomes.append(
            _Outcome(
                method_id=method_id,
                name=name,
                status=response.status.value,
                root=_extract_root(method_id, response),
                iterations=iterations,
                order=response.errors.order_of_convergence,
                series=_extract_series(method_id, response),
                messages=list(response.warnings),
            )
        )
    return outcomes


def _residual_key(outcome: _Outcome) -> float:
    return outcome.residual if outcome.residual is not None else math.inf


def _reference_root(outcomes: list[_Outcome], fallback: float) -> float:
    """Pick the root that most looks like the true solution.

    Prefer converged results, then the smallest residual |f(root)|; fall back to
    the first starting guess when nothing usable was produced.
    """
    usable = [o for o in outcomes if o.root is not None and o.residual is not None]
    if not usable:
        return fallback
    best = min(usable, key=_residual_key)
    return best.root if best.root is not None else fallback


def _build_plot(outcomes: list[_Outcome], reference: float) -> PlotPayload:
    """Semilog error-versus-iteration plot, one line per method."""
    traces: list[dict[str, Any]] = []
    for outcome in outcomes:
        if not outcome.series:
            continue
        xs = list(range(1, len(outcome.series) + 1))
        ys = [
            min(max(abs(value - reference), _PLOT_ERROR_FLOOR), _PLOT_ERROR_CAP)
            for value in outcome.series
        ]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": outcome.name,
                "x": xs,
                "y": ys,
            }
        )

    values = [y for trace in traces for y in trace["y"]]
    if values:
        lo = max(min(values), _PLOT_ERROR_FLOOR)
        hi = min(max(values), _PLOT_ERROR_CAP)
        if hi <= lo:
            hi = lo * 10.0
        y_range = [math.log10(lo) - 0.3, math.log10(hi) + 0.3]
    else:
        y_range = [math.log10(_PLOT_ERROR_FLOOR), math.log10(_PLOT_ERROR_CAP)]

    layout: dict[str, Any] = {
        "title": {"text": "Convergence comparison (log scale)"},
        "xaxis": {"title": {"text": "Iteration k"}},
        "yaxis": {
            "title": {"text": "Error |x_k - x*|"},
            "type": "log",
            "range": y_range,
        },
    }
    return PlotPayload(traces=traces, layout=layout)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run every selected method on the same equation and compare them."""
    f_text: str = inputs["function"]
    a = float(inputs["a"])
    b = float(inputs["b"])
    x0 = float(inputs["x0"])
    x1 = float(inputs["x1"])
    g_text = str(inputs.get("g") or "")
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)
    criterion = str(inputs["stopping_criterion"])
    decimals = int(inputs["decimal_precision"])

    selected = [mid for mid in _METHOD_ORDER if bool(inputs.get(f"run_{mid}"))]
    if not selected:
        raise InvalidInputError(
            "Select at least one method to compare.",
            hint="Tick one or more of the 'Compare ...' boxes.",
        )

    expression = parse_expression(f_text, ("x",))
    f_plot = make_function(expression, ("x",), strict=False)
    latex_f = expr_to_latex(expression)

    outcomes = _run_selected(
        selected,
        limits,
        f_text=f_text,
        a=a,
        b=b,
        x0=x0,
        x1=x1,
        g_text=g_text,
        tolerance=tolerance,
        max_iterations=max_iterations,
        criterion=criterion,
        decimals=decimals,
    )

    for outcome in outcomes:
        if outcome.root is not None:
            value = _safe_value(f_plot, outcome.root)
            outcome.residual = abs(value) if value is not None else None

    reference = _reference_root(outcomes, x0)
    for outcome in outcomes:
        if outcome.root is not None:
            outcome.error = abs(outcome.root - reference)

    rows: list[list[Any]] = [
        [
            outcome.name,
            outcome.iterations,
            outcome.root,
            outcome.residual,
            outcome.error,
            outcome.order,
            outcome.status,
        ]
        for outcome in outcomes
    ]

    converged = [o for o in outcomes if o.status == "converged" and o.iterations is not None]
    fastest = min(converged, key=lambda o: o.iterations or math.inf) if converged else None

    warnings: list[str] = []
    for outcome in outcomes:
        for message in outcome.messages:
            warnings.append(f"{outcome.name}: {message}")

    methods_text = ", ".join(_METHOD_NAMES[mid] for mid in selected)
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                f"f(x) = {latex_f}"
                f"\\\\ [a, b] = [{format_num(a, decimals)},\\, {format_num(b, decimals)}],"
                f"\\quad x_0 = {format_num(x0, decimals)},\\quad x_1 = {format_num(x1, decimals)}"
                f"\\\\ \\text{{Methods compared}}:\\; {methods_text}"
            ),
            note=f"Tolerance {tolerance:g}, stopping criterion '{criterion}'.",
        ),
        Step(
            title="Bracketing vs open methods",
            latex=(
                r"\text{Bracketing (bisection, false position): root trapped in } [a,b]"
                r"\\ \text{Open (secant, Newton, fixed-point): from guesses, faster but can diverge}"
            ),
            note=(
                "Bracketing methods are reliable but usually slow; open methods are "
                "fast near the root but sensitive to the starting values."
            ),
        ),
    ]

    for outcome in outcomes:
        if outcome.root is not None and outcome.iterations is not None:
            steps.append(
                Step(
                    title=outcome.name,
                    latex=(
                        f"\\text{{{outcome.name}}}:\\quad x \\approx "
                        f"{format_num(outcome.root, decimals)},\\quad k = {outcome.iterations},"
                        f"\\quad \\text{{{outcome.status}}}"
                    ),
                )
            )
        else:
            steps.append(
                Step(
                    title=outcome.name,
                    latex=rf"\text{{{outcome.name}}}: \text{{not available}}",
                    note=outcome.messages[0] if outcome.messages else "",
                )
            )

    if fastest is not None:
        summary = (
            f"{fastest.name} used the fewest iterations "
            f"({fastest.iterations}) among the converged methods."
        )
    else:
        summary = "None of the selected methods converged to the tolerance."
    steps.append(
        Step(
            title="Result",
            latex=(
                f"x^{{*}} \\approx {format_num(reference, decimals)}"
                f"\\\\ \\text{{{summary}}}"
            ),
            note="Errors in the table are measured against this reference root.",
        )
    )

    errors = (
        ErrorInfo(absolute=fastest.error, order_of_convergence=fastest.order)
        if fastest is not None
        else ErrorInfo()
    )

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED if fastest is not None else SolveStatus.MAX_ITER,
        result={
            "reference_root": reference,
            "fastest_method": fastest.name if fastest is not None else None,
            "converged_methods": [o.name for o in outcomes if o.status == "converged"],
            "methods": [
                {
                    "method": outcome.name,
                    "status": outcome.status,
                    "root": outcome.root,
                    "iterations": outcome.iterations,
                    "residual": outcome.residual,
                    "error": outcome.error,
                    "order": outcome.order,
                }
                for outcome in outcomes
            ],
        },
        steps=steps,
        tables=[
            DataTable(
                title="Method comparison",
                columns=[
                    "Method",
                    "Iterations",
                    "Final root",
                    "Final |f(x)|",
                    "Final error",
                    "Order",
                    "Status",
                ],
                rows=rows,
            )
        ],
        plot=_build_plot(outcomes, reference),
        errors=errors,
        warnings=warnings,
    )
