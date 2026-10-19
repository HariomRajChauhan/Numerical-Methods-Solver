"""Shared engine for the Chapter 4 Newton-Cotes quadrature solvers.

Private module (leading underscore) so the auto-loader skips it. It holds the
composite-weight builders, node evaluation, the SymPy exact value, the
numerical error-bound estimate, the drawing of trapezoids / quadratic / cubic
pieces and the optional convergence study shared by the trapezoidal, Simpson
1/3 and Simpson 3/8 solvers.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.errors import InvalidInputError
from app.core.models import (
    DataTable,
    ErrorInfo,
    InputField,
    MethodMeta,
    PlotPayload,
    SelectOption,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.parser import make_function, parse_expression
from app.solvers._common import (
    boolean_field,
    failed_response,
    format_num,
    function_field,
    number_field,
    points_trace,
    precision_field,
    sample_curve,
)
from app.solvers.ch3_interpolation._interp import (
    common_step,
    is_equal_spacing,
    prepare_dataset,
    spacing_failure,
)

TRAPEZOIDAL = "trapezoidal"
SIMPSON13 = "simpson_13"
SIMPSON38 = "simpson_38"

Evaluator = Callable[[float], float]

QUAD_POINTS: list[list[float]] = [
    [0.0, 0.0],
    [1.0 / 6.0, 1.0 / 36.0],
    [2.0 / 6.0, 4.0 / 36.0],
    [3.0 / 6.0, 0.25],
    [4.0 / 6.0, 16.0 / 36.0],
    [5.0 / 6.0, 25.0 / 36.0],
    [1.0, 1.0],
]


@dataclass(frozen=True)
class Rule:
    """The parameters that distinguish one Newton-Cotes rule from another."""

    key: str
    name: str
    constraint: str  # "any" | "even" | "multiple3"
    error_coefficient: float  # 1/12, 1/180, 1/80
    error_coefficient_latex: str  # \frac{1}{12}, ...
    derivative_order: int  # 2 or 4
    piece_degree: int  # 1, 2 or 3
    convergence_order: int  # 2 or 4 (h power in the error)
    factor_label: str  # latex multiplier, e.g. "h/2"
    grouped_latex: str


TRAPEZOIDAL_RULE = Rule(
    key=TRAPEZOIDAL,
    name="Trapezoidal rule",
    constraint="any",
    error_coefficient=1.0 / 12.0,
    error_coefficient_latex=r"\frac{1}{12}",
    derivative_order=2,
    piece_degree=1,
    convergence_order=2,
    factor_label=r"\frac{h}{2}",
    grouped_latex=(
        r"I \approx \frac{h}{2}\left[\,y_0 + 2\left(y_1 + y_2 + \cdots + y_{n-1}\right)"
        r" + y_n\,\right]"
    ),
)

SIMPSON13_RULE = Rule(
    key=SIMPSON13,
    name="Simpson's 1/3 rule",
    constraint="even",
    error_coefficient=1.0 / 180.0,
    error_coefficient_latex=r"\frac{1}{180}",
    derivative_order=4,
    piece_degree=2,
    convergence_order=4,
    factor_label=r"\frac{h}{3}",
    grouped_latex=(
        r"I \approx \frac{h}{3}\left[\,y_0 + 4\left(y_1 + y_3 + \cdots\right)"
        r" + 2\left(y_2 + y_4 + \cdots\right) + y_n\,\right]"
    ),
)

SIMPSON38_RULE = Rule(
    key=SIMPSON38,
    name="Simpson's 3/8 rule",
    constraint="multiple3",
    error_coefficient=1.0 / 80.0,
    error_coefficient_latex=r"\frac{1}{80}",
    derivative_order=4,
    piece_degree=3,
    convergence_order=4,
    factor_label=r"\frac{3h}{8}",
    grouped_latex=(
        r"I \approx \frac{3h}{8}\left[\,y_0 + 3\left(y_1 + y_2 + y_4 + y_5 + \cdots\right)"
        r" + 2\left(y_3 + y_6 + \cdots\right) + y_n\,\right]"
    ),
)


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------


def base_weights(rule: Rule, n: int) -> list[float]:
    """The integer weights of the composite rule (before the h-factor)."""
    if rule.key == TRAPEZOIDAL:
        return [1.0] + [2.0] * (n - 1) + [1.0]
    if rule.key == SIMPSON13:
        weights = [2.0] * (n + 1)
        weights[0] = weights[-1] = 1.0
        for index in range(1, n, 2):
            weights[index] = 4.0
        return weights
    weights = [3.0] * (n + 1)
    weights[0] = weights[-1] = 1.0
    for index in range(3, n, 3):
        weights[index] = 2.0
    return weights


def factor(rule: Rule, h: float) -> float:
    """The composite multiplier in front of the weighted sum."""
    if rule.key == TRAPEZOIDAL:
        return h / 2.0
    if rule.key == SIMPSON13:
        return h / 3.0
    return 3.0 * h / 8.0


# ---------------------------------------------------------------------------
# Errors, exact values and estimates
# ---------------------------------------------------------------------------


def symbolic_integral(expr: Any, a: float, b: float) -> float | None:
    """Exact definite integral via SymPy, or ``None`` when it is not available."""
    import sympy as sp

    x = sp.Symbol("x")
    try:
        result = sp.integrate(expr, (x, sp.Float(a), sp.Float(b)))
    except Exception:
        return None
    if result.has(sp.Integral) or result.has(sp.zoo) or result.has(sp.nan):
        return None
    try:
        value = float(sp.N(result))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def reference_integral(f: Evaluator, a: float, b: float) -> float | None:
    """A high-accuracy reference value from ``scipy.integrate.quad``."""
    from scipy import integrate

    try:
        value, _ = integrate.quad(f, a, b)
    except Exception:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def numeric_derivative_max(
    f: Evaluator,
    a: float,
    b: float,
    order: int,
    *,
    samples: int = 501,
) -> float | None:
    """Estimate ``max |f^(order)|`` on ``[a, b]`` by finite differences."""
    grid = np.linspace(a, b, samples)
    values = np.array([float(f(x)) for x in grid], dtype=float)
    if not np.all(np.isfinite(values)):
        return None
    derivative = values
    for _ in range(order):
        derivative = np.gradient(derivative, grid)
    maximum = float(np.max(np.abs(derivative)))
    return maximum if math.isfinite(maximum) else None


def polynomial_derivative_max(
    coefficients: np.ndarray, a: float, b: float, order: int
) -> float:
    """``max |f^(order)|`` for a fitted polynomial on ``[a, b]``."""
    derivative = np.polyder(coefficients, order)
    grid = np.linspace(a, b, 501)
    return float(np.max(np.abs(np.polyval(derivative, grid))))


# ---------------------------------------------------------------------------
# Nodes and tables
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Node:
    index: int
    x: float
    y: float
    weight: float


def evaluation_table(
    nodes: list[Node], factor_value: float, decimals: int
) -> DataTable:
    rows = [
        [
            node.index,
            format_num(node.x, decimals),
            format_num(node.y, decimals),
            f"{node.weight:g}",
            format_num(node.weight * node.y, decimals),
        ]
        for node in nodes
    ]
    return DataTable(
        title="Function values, weights and products",
        columns=["i", "x_i", "f(x_i)", "w_i", "w_i f(x_i)"],
        rows=rows,
    )


def summary_table(
    value: float,
    exact: float | None,
    abs_error: float | None,
    rel_error: float | None,
    bound: float | None,
    decimals: int,
    *,
    reference: float | None = None,
) -> DataTable:
    rows: list[list[Any]] = [["Approximate integral", format_num(value, decimals)]]
    if exact is not None:
        rows.append(["Exact value (SymPy)", format_num(exact, decimals)])
    if reference is not None:
        rows.append(["Reference value (quad)", format_num(reference, decimals)])
    if abs_error is not None:
        rows.append(["Absolute error", format_num(abs_error, decimals)])
    if rel_error is not None:
        rows.append(["Relative error (%)", format_num(rel_error, decimals)])
    if bound is not None:
        rows.append(["Error bound (estimate)", format_num(bound, decimals)])
    return DataTable(title="Result summary", columns=["Quantity", "Value"], rows=rows)


def convergence_table(
    steps: list[int], errors: list[float], h_values: list[float], decimals: int
) -> DataTable:
    rows = [
        [n, format_num(h, decimals), format_num(error, decimals)]
        for n, h, error in zip(steps, h_values, errors, strict=True)
    ]
    return DataTable(
        title="Convergence of the error",
        columns=["n", "h", "|error|"],
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------


def _approximation_curve(
    xs: np.ndarray, ys: np.ndarray, degree: int
) -> tuple[list[float], list[float]]:
    """Sample the piecewise interpolant used by the rule."""
    if degree <= 0 or len(xs) < 2:
        return list(xs), list(ys)
    out_x: list[float] = []
    out_y: list[float] = []
    for start in range(0, len(xs) - 1, degree):
        chunk_x = xs[start : start + degree + 1]
        chunk_y = ys[start : start + degree + 1]
        fit_degree = min(len(chunk_x) - 1, degree)
        if len(chunk_x) < 2:
            continue
        coefficients = np.polyfit(chunk_x, chunk_y, fit_degree)
        grid = np.linspace(chunk_x[0], chunk_x[-1], 40)
        out_x.extend(float(value) for value in grid)
        out_y.extend(float(value) for value in np.polyval(coefficients, grid))
    return out_x, out_y


def quadrature_plot(
    *,
    nodes: list[Node],
    rule: Rule,
    f_curve: tuple[list[float], list[float]] | None,
    convergence: tuple[list[int], list[float]] | None,
) -> PlotPayload:
    """The shaded area (with the rule's pieces) and an optional error study."""
    xs = np.asarray([node.x for node in nodes], dtype=float)
    ys = np.asarray([node.y for node in nodes], dtype=float)
    approx_x, approx_y = _approximation_curve(xs, ys, rule.piece_degree)

    area_trace: dict[str, Any] = {
        "type": "scatter",
        "mode": "lines",
        "name": f"{rule.name} pieces",
        "x": approx_x,
        "y": approx_y,
        "fill": "tozeroy",
        "fillcolor": "rgba(245, 158, 11, 0.20)",
        "line": {"color": "#f59e0b", "width": 1.5},
    }
    traces: list[dict[str, Any]] = [area_trace]
    if f_curve is not None and f_curve[0]:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "f(x)",
                "x": f_curve[0],
                "y": f_curve[1],
                "line": {"color": "#2563eb", "width": 2},
            }
        )
    traces.append(
        points_trace(
            [node.x for node in nodes],
            [node.y for node in nodes],
            "Nodes f(x_i)",
        )
    )

    layout: dict[str, Any] = {
        "title": {"text": f"{rule.name}: composite integration"},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "f(x)"}},
    }

    if convergence is not None and convergence[0]:
        steps, errors = convergence
        layout = {
            "title": {"text": f"{rule.name}: area and convergence"},
            "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
            "xaxis": {"title": {"text": "x"}, "domain": [0.0, 0.44]},
            "yaxis": {"title": {"text": "f(x)"}, "domain": [0.0, 1.0]},
            "xaxis2": {"title": {"text": "n"}, "domain": [0.56, 1.0], "anchor": "y2"},
            "yaxis2": {"title": {"text": "|error|"}, "type": "log", "anchor": "x2"},
            "legend": {"orientation": "h", "y": -0.18},
        }
        for trace in traces:
            trace["xaxis"] = "x"
            trace["yaxis"] = "y"
        log_errors = [math.log10(error) if error > 0 else None for error in errors]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Error vs n",
                "x": steps,
                "y": list(errors),
                "xaxis": "x2",
                "yaxis": "y2",
                "line": {"color": "#dc2626"},
            }
        )
        # Reference line with the theoretical slope: error ~ C n^{-p}.
        if all(value is not None for value in log_errors) and errors[0] > 0:
            slope = rule.convergence_order
            first_n, first_error = steps[0], errors[0]
            ref_x = [first_n, steps[-1]]
            ref_y = [
                first_error,
                first_error * (steps[-1] / first_n) ** (-slope),
            ]
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": f"slope {rule.convergence_order}",
                    "x": ref_x,
                    "y": ref_y,
                    "xaxis": "x2",
                    "yaxis": "y2",
                    "line": {"color": "#16a34a", "dash": "dash"},
                }
            )

    return PlotPayload(traces=traces, layout=layout)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def quadrature_schema(default_n: int) -> list[InputField]:
    """The shared input form (function or table input) for every rule."""
    return [
        InputField(
            key="source",
            label="Input type",
            type="select",
            required=True,
            default="function",
            options=[
                SelectOption(value="function", label="Function f(x) with a, b and n"),
                SelectOption(value="table", label="Tabulated equally spaced data (x, y)"),
            ],
            help="Integrate a function expression or a table of equally spaced values.",
        ),
        InputField(
            key="points",
            label="Data points (x, y)",
            type="data_points",
            required=False,
            default=[list(point) for point in QUAD_POINTS],
            placeholder="0,0; 0.5,0.25; 1,1",
            help="Used when the input type is a table; must be equally spaced.",
        ),
        function_field(required=False),
        number_field("a", "Lower limit a", 0.0, required=False),
        number_field("b", "Upper limit b", 1.0, required=False),
        InputField(
            key="step_mode",
            label="Interval specification",
            type="select",
            required=True,
            default="intervals",
            options=[
                SelectOption(value="intervals", label="Number of subintervals n"),
                SelectOption(value="step", label="Step size h"),
            ],
        ),
        InputField(
            key="n",
            label="Number of subintervals n",
            type="integer",
            required=True,
            default=default_n,
            min=1,
            max=100_000,
        ),
        number_field(
            "h",
            "Step size h",
            0.25,
            required=False,
            help="Used when the interval specification is a step size.",
        ),
        boolean_field(
            "show_convergence",
            "Show convergence of error vs n",
            False,
            help="Adds a semilog convergence study (function input with a known exact value).",
        ),
        precision_field(),
    ]


@dataclass(frozen=True)
class Prepared:
    """A validated quadrature problem ready for the rule."""

    xs: np.ndarray
    ys: np.ndarray
    a: float
    b: float
    n: int
    h: float
    f: Evaluator | None
    expr: Any | None
    notices: list[str] = field(default_factory=list)


def _prepare(
    inputs: dict[str, Any], rule: Rule, decimals: int, method_id: str
) -> Prepared | SolveResponse:
    source = str(inputs.get("source", "function"))
    notices: list[str] = []

    if source == "table":
        points = inputs.get("points")
        if not points:
            raise InvalidInputError("Data points are required for the tabulated input type.")
        dataset = prepare_dataset(points, min_points=2)
        xs, ys = dataset.xs, dataset.ys
        if not is_equal_spacing(xs):
            return spacing_failure(method_id, xs, decimals)
        notices.extend(dataset.notices)
        a = float(xs[0])
        b = float(xs[-1])
        h = common_step(xs)
        n = len(xs) - 1
        return Prepared(xs, ys, a, b, n, h, None, None, notices)

    text = inputs.get("function")
    if not text:
        raise InvalidInputError("A function expression is required for the function input type.")
    a = float(inputs.get("a", 0.0))
    b = float(inputs.get("b", 1.0))
    if a > b:
        a, b = b, a
        notices.append("a and b were swapped so that a < b.")
    expr = parse_expression(text, ("x",))
    f = make_function(expr, ("x",), strict=False)

    if a == b:
        xs = np.array([a], dtype=float)
        ys = np.array([float(f(a))], dtype=float)
        return Prepared(xs, ys, a, b, 0, 0.0, f, expr, notices)

    step_mode = str(inputs.get("step_mode", "intervals"))
    if step_mode == "step":
        h_input = float(inputs.get("h", 0.0))
        if h_input <= 0.0:
            raise InvalidInputError(
                "The step size h must be positive.",
                hint="Use a step such as 0.1 that divides [a, b].",
            )
        n = max(1, round((b - a) / h_input))
        if not math.isclose(n * h_input, b - a, rel_tol=1e-9, abs_tol=1e-12):
            notices.append(
                f"The step h = {h_input:g} does not divide [a, b] exactly; "
                f"n = {n} was used with h = {(b - a) / n:g}."
            )
    else:
        n = int(inputs.get("n", 1))
    if n < 1:
        raise InvalidInputError("The number of subintervals n must be at least 1.")

    h = (b - a) / n
    grid = np.linspace(a, b, n + 1)
    values = np.array([float(f(x)) for x in grid], dtype=float)
    return Prepared(grid, values, a, b, n, h, f, expr, notices)


def constraint_failure(rule: Rule, n: int, method_id: str) -> SolveResponse | None:
    """A ``failed`` response when ``n`` violates the rule's requirement."""
    if rule.constraint == "even" and n % 2 != 0:
        options = [f"n = {n + 1}"]
        if n - 1 >= 2:
            options.append(f"n = {n - 1}")
        return failed_response(
            method_id,
            "Simpson's 1/3 rule needs an even number of subintervals, but "
            f"n = {n} is odd. Choose {' or '.join(options)}.",
        )
    if rule.constraint == "multiple3" and n % 3 != 0:
        low = n - (n % 3)
        high = n + (3 - n % 3)
        options = [f"n = {high}"]
        if low >= 3:
            options.append(f"n = {low}")
        return failed_response(
            method_id,
            "Simpson's 3/8 rule needs a number of subintervals that is a multiple of 3, "
            f"but n = {n} is not. Choose {' or '.join(options)}.",
        )
    return None


def first_nonfinite(
    prepared: Prepared, *, samples: int = 257
) -> float | None:
    """The first x at which the integrand is not finite, else ``None``."""
    if prepared.f is None:
        return None
    grid = np.linspace(prepared.a, prepared.b, samples)
    for x in grid:
        if not math.isfinite(float(prepared.f(float(x)))):
            return float(x)
    for node in prepared.xs:
        if not math.isfinite(float(prepared.f(float(node)))):
            return float(node)
    return None


# ---------------------------------------------------------------------------
# Grouped sums, error bound, steps and the public entry point
# ---------------------------------------------------------------------------


def composite_value(f: Evaluator, a: float, b: float, n: int, rule: Rule) -> float:
    """Evaluate the composite rule directly (used by the convergence study)."""
    h = (b - a) / n
    grid = np.linspace(a, b, n + 1)
    weights = base_weights(rule, n)
    total = sum(
        weight * float(f(x)) for weight, x in zip(weights, grid, strict=True)
    )
    return factor(rule, h) * total


def _error_bound(prepared: Prepared, rule: Rule) -> float | None:
    """Estimate ``(b-a) h^p / coeff * max|f^(p)|`` (``M`` sampled numerically)."""
    derivative_max: float | None
    if prepared.f is not None:
        derivative_max = numeric_derivative_max(
            prepared.f, prepared.a, prepared.b, rule.derivative_order
        )
    else:
        coefficients = np.polyfit(prepared.xs, prepared.ys, len(prepared.xs) - 1)
        derivative_max = polynomial_derivative_max(
            coefficients, prepared.a, prepared.b, rule.derivative_order
        )
    if derivative_max is None:
        return None
    return (
        rule.error_coefficient
        * (prepared.b - prepared.a)
        * prepared.h ** rule.derivative_order
        * derivative_max
    )


def _grouped_inner(rule: Rule, ys: np.ndarray, decimals: int) -> str:
    """The numeric inner bracket of the grouped weighted sum."""
    n = len(ys) - 1
    first = format_num(float(ys[0]), decimals)
    last = format_num(float(ys[-1]), decimals)
    if rule.key == TRAPEZOIDAL:
        interior = float(np.sum(ys[1:-1]))
        parts = [first]
        if n > 1:
            parts.append(rf"2\left({format_num(interior, decimals)}\right)")
        parts.append(last)
        return " + ".join(parts)
    if rule.key == SIMPSON13:
        odd = float(np.sum(ys[1::2]))
        even = float(np.sum(ys[2:-1:2]))
        parts = [first, rf"4\left({format_num(odd, decimals)}\right)"]
        if even:
            parts.append(rf"2\left({format_num(even, decimals)}\right)")
        parts.append(last)
        return " + ".join(parts)
    group3 = float(np.sum([ys[i] for i in range(1, n) if i % 3 != 0]))
    group2 = float(np.sum([ys[i] for i in range(1, n) if i % 3 == 0]))
    parts = [first, rf"3\left({format_num(group3, decimals)}\right)"]
    if group2:
        parts.append(rf"2\left({format_num(group2, decimals)}\right)")
    parts.append(last)
    return " + ".join(parts)


def _build_steps(
    prepared: Prepared,
    rule: Rule,
    factor_value: float,
    value: float,
    *,
    exact: float | None,
    abs_error: float | None,
    rel_error: float | None,
    bound: float | None,
    decimals: int,
) -> list[Step]:
    source_note = (
        "Nodes x_i = a + i h sampled from the function f(x)."
        if prepared.f is not None
        else "Nodes read from the equally spaced table."
    )
    setup = Step(
        title="Set up the composite rule",
        latex=(
            rf"a = {format_num(prepared.a, decimals)},\quad "
            rf"b = {format_num(prepared.b, decimals)},\quad n = {prepared.n}"
            rf"\\[1mm] h = \frac{{b - a}}{{n}} = {format_num(prepared.h, decimals)}"
            rf"\\[1mm] I \approx {rule.factor_label}\left[\sum_{{i=0}}^{{n}} w_i\,f(x_i)\right]"
        ),
        note=source_note,
    )
    weighted = Step(
        title="Weighted sum (grouped form)",
        latex=(
            rule.grouped_latex
            + r" = "
            + format_num(factor_value, decimals)
            + r"\left[\, "
            + _grouped_inner(rule, prepared.ys, decimals)
            + r" \,\right] = "
            + format_num(value, decimals)
        ),
        note="The grouped form collects the repeated weights of the composite rule.",
    )
    steps = [setup, weighted]
    if exact is not None:
        steps.append(
            Step(
                title="Exact value",
                latex=(
                    rf"\int_{{{format_num(prepared.a, decimals)}}}^{{{format_num(prepared.b, decimals)}}}"
                    rf" f(x)\,dx = {format_num(exact, decimals)}"
                ),
                note="Evaluated symbolically with SymPy.",
            )
        )
    if abs_error is not None:
        error_latex = rf"\text{{Absolute error}} = {format_num(abs_error, decimals)}"
        if rel_error is not None:
            error_latex += rf",\qquad \text{{Relative error}} = {format_num(rel_error, decimals)}\%"
        steps.append(
            Step(title="Error", latex=error_latex, note="Compared with the exact value.")
        )
    if bound is not None:
        steps.append(
            Step(
                title="Theoretical error bound",
                latex=(
                    rf"|E| \le {rule.error_coefficient_latex}\,(b-a)\,h^{{{rule.derivative_order}}}"
                    rf"\,M_{{{rule.derivative_order}}} \approx {format_num(bound, decimals)}"
                ),
                note=(
                    rf"$M_{{{rule.derivative_order}}} = \max |f^{{({rule.derivative_order})}}|$ "
                    "is estimated numerically from samples of the integrand, so the bound "
                    "is itself an estimate."
                ),
            )
        )
    steps.append(
        Step(
            title="Result",
            latex=(
                rf"\int_{{{format_num(prepared.a, decimals)}}}^{{{format_num(prepared.b, decimals)}}}"
                rf" f(x)\,dx \approx {format_num(value, decimals)}"
            ),
            note="Composite Newton-Cotes estimate.",
        )
    )
    return steps


def _degenerate_response(
    method_id: str, prepared: Prepared, notices: list[str], decimals: int
) -> SolveResponse:
    step = Step(
        title="Degenerate interval",
        latex=(
            rf"a = b = {format_num(prepared.a, decimals)} \;\Rightarrow\; "
            rf"\int_a^b f(x)\,dx = 0"
        ),
        note="The lower and upper limits coincide, so the integral is exactly zero.",
    )
    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result={
            "value": 0.0,
            "a": prepared.a,
            "b": prepared.b,
            "n": 0,
            "h": 0.0,
            "exact_value": 0.0,
            "absolute_error": 0.0,
            "relative_error_percent": None,
            "error_bound": 0.0,
        },
        steps=[step],
        tables=[summary_table(0.0, 0.0, 0.0, None, 0.0, decimals)],
        plot=PlotPayload(),
        errors=ErrorInfo(absolute=0.0),
        warnings=notices or ["The interval is degenerate (a = b), so the integral is exactly 0."],
    )


def solve_quadrature(
    meta: MethodMeta,
    rule: Rule,
    inputs: dict[str, Any],
    limits: SolverLimits,
) -> SolveResponse:
    """Validate the input, apply the composite rule, and build the response."""
    del limits  # direct quadrature needs no iteration budget
    method_id = meta.id
    decimals = int(inputs.get("decimal_precision", 6))

    prepared = _prepare(inputs, rule, decimals, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    notices = list(prepared.notices)

    if prepared.n == 0:
        return _degenerate_response(method_id, prepared, notices, decimals)

    singular_x = first_nonfinite(prepared)
    if singular_x is not None:
        assert prepared.f is not None  # guaranteed by first_nonfinite
        node = None
        for value in prepared.xs:
            if not math.isfinite(float(prepared.f(float(value)))):
                node = float(value)
                break
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

    failure = constraint_failure(rule, prepared.n, method_id)
    if failure is not None:
        failure.warnings.extend(notices)
        return failure

    weights = base_weights(rule, prepared.n)
    nodes = [
        Node(i, float(prepared.xs[i]), float(prepared.ys[i]), weights[i])
        for i in range(prepared.n + 1)
    ]
    factor_value = factor(rule, prepared.h)
    value = factor_value * sum(node.weight * node.y for node in nodes)

    exact: float | None = None
    reference: float | None = None
    if prepared.expr is not None:
        exact = symbolic_integral(prepared.expr, prepared.a, prepared.b)
    if exact is None and prepared.f is not None:
        reference = reference_integral(prepared.f, prepared.a, prepared.b)
    target = exact if exact is not None else reference

    abs_error: float | None = None
    rel_error: float | None = None
    if target is not None:
        abs_error = abs(value - target)
        if target != 0.0:
            rel_error = abs(abs_error / target) * 100.0

    bound = _error_bound(prepared, rule)

    tables = [
        evaluation_table(nodes, factor_value, decimals),
        summary_table(value, exact, abs_error, rel_error, bound, decimals, reference=reference),
    ]

    convergence: tuple[list[int], list[float]] | None = None
    if bool(inputs.get("show_convergence")):
        if prepared.f is None:
            notices.append("The convergence study is available only for a function input.")
        elif exact is None:
            notices.append(
                "The convergence study needs an exact value, which SymPy could not find "
                "for this integrand."
            )
        else:
            steps_n = [prepared.n * (2**k) for k in range(5)]
            h_values = [(prepared.b - prepared.a) / m for m in steps_n]
            errors = [
                abs(composite_value(prepared.f, prepared.a, prepared.b, m, rule) - exact)
                for m in steps_n
            ]
            convergence = (steps_n, errors)
            tables.append(convergence_table(steps_n, errors, h_values, decimals))

    steps = _build_steps(
        prepared,
        rule,
        factor_value,
        value,
        exact=exact,
        abs_error=abs_error,
        rel_error=rel_error,
        bound=bound,
        decimals=decimals,
    )

    f_curve = (
        sample_curve(prepared.f, prepared.a, prepared.b)
        if prepared.f is not None
        else None
    )
    plot = quadrature_plot(
        nodes=nodes, rule=rule, f_curve=f_curve, convergence=convergence
    )

    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result={
            "value": value,
            "a": prepared.a,
            "b": prepared.b,
            "n": prepared.n,
            "h": prepared.h,
            "exact_value": exact,
            "reference_value": reference,
            "absolute_error": abs_error,
            "relative_error_percent": rel_error,
            "error_bound": bound,
        },
        steps=steps,
        tables=tables,
        plot=plot,
        errors=ErrorInfo(absolute=abs_error, relative_percent=rel_error),
        warnings=notices,
    )
