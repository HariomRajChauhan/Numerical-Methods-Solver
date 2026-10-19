"""Panel-based Newton-Cotes engine for the Chapter 4 Group C solvers.

Private module (leading underscore) so the auto-loader skips it. It generalises
the composite rules to a *panel* of ``p`` subintervals carrying the Cotes
numbers ``c_0 ... c_p`` (the integrals of the Lagrange basis over one panel),

``I_panel = h (c_0 y_0 + c_1 y_1 + ... + c_p y_p)``,

so that the trapezoidal (p=1), Simpson 1/3 (p=2), Simpson 3/8 (p=3), Boole
(p=4) and Weddle (p=6) rules — and the general n-point Newton-Cotes family —
all share one evaluator. It also builds the optional rule-comparison table and
overlay plot.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
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
from app.solvers.ch4_diff_integration._quadrature import (
    QUAD_POINTS,
    Prepared,
    _approximation_curve,
    _degenerate_response,
    _prepare,
    convergence_table,
    first_nonfinite,
    numeric_derivative_max,
    polynomial_derivative_max,
    quadrature_schema,
    reference_integral,
    summary_table,
    symbolic_integral,
)

TRAPEZOIDAL = "trapezoidal"
SIMPSON13 = "simpson_13"
SIMPSON38 = "simpson_38"
BOOLE = "boole"
WEDDLE = "weddle"

COMPARE_COLORS = {
    TRAPEZOIDAL: "#94a3b8",
    SIMPSON13: "#2563eb",
    SIMPSON38: "#f59e0b",
    BOOLE: "#16a34a",
    WEDDLE: "#dc2626",
}

CLASSICAL_BY_PANEL = {
    1: "Trapezoidal rule",
    2: "Simpson's 1/3 rule",
    3: "Simpson's 3/8 rule",
    4: "Boole's rule",
}


# ---------------------------------------------------------------------------
# Exact Cotes numbers
# ---------------------------------------------------------------------------


@cache
def cotes_numbers(panel_intervals: int) -> tuple[Fraction, ...]:
    """Exact Cotes numbers of the closed Newton-Cotes panel (via SymPy)."""
    import sympy as sp

    t = sp.Symbol("t")
    nodes = list(range(panel_intervals + 1))
    values: list[Fraction] = []
    for i in range(panel_intervals + 1):
        basis = sp.Integer(1)
        for j in range(panel_intervals + 1):
            if j != i:
                basis *= (t - nodes[j]) / sp.Integer(nodes[i] - nodes[j])
        integral = sp.integrate(basis, (t, sp.Integer(0), sp.Integer(panel_intervals)))
        rational = sp.Rational(integral)
        values.append(Fraction(int(rational.p), int(rational.q)))
    return tuple(values)


def fraction_latex(value: Fraction) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    sign = "-" if value < 0 else ""
    return rf"{sign}\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _join_signed(parts: list[str]) -> str:
    if not parts:
        return "0"
    text = parts[0]
    for part in parts[1:]:
        text += (" " + part) if part.startswith("-") else (" + " + part)
    return text


def composite_node_weights(
    panel_intervals: int, cotes: tuple[Fraction, ...], panels: int
) -> list[Fraction]:
    """Full node weights of the composite rule (in units of ``h``)."""
    total = panel_intervals * panels
    weights = [Fraction(0)] * (total + 1)
    for panel in range(panels):
        base = panel * panel_intervals
        for i, coefficient in enumerate(cotes):
            weights[base + i] += coefficient
    return weights


# ---------------------------------------------------------------------------
# Rule descriptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PanelSpec:
    name: str
    panel_intervals: int
    cotes: tuple[Fraction, ...]
    exact_degree: int
    error_coefficient: float
    error_coefficient_latex: str
    panel_latex: str
    reproduces: str | None = None

    @property
    def convergence_order(self) -> int:
        return self.exact_degree + 1

    @property
    def derivative_order(self) -> int:
        return self.exact_degree + 1


@dataclass(frozen=True)
class ClassicalRule:
    key: str
    name: str
    constraint: str  # "any" | "even" | "multiple3" | "multiple4" | "multiple6"
    spec: PanelSpec


_F = Fraction

TRAPEZOIDAL_RULE = ClassicalRule(
    key=TRAPEZOIDAL,
    name="Trapezoidal rule",
    constraint="any",
    spec=PanelSpec(
        name="Trapezoidal rule",
        panel_intervals=1,
        cotes=(_F(1, 2), _F(1, 2)),
        exact_degree=1,
        error_coefficient=1.0 / 12.0,
        error_coefficient_latex=r"\frac{1}{12}",
        panel_latex=r"\frac{h}{2}\left(y_0 + y_1\right)",
    ),
)

SIMPSON13_RULE = ClassicalRule(
    key=SIMPSON13,
    name="Simpson's 1/3 rule",
    constraint="even",
    spec=PanelSpec(
        name="Simpson's 1/3 rule",
        panel_intervals=2,
        cotes=(_F(1, 3), _F(4, 3), _F(1, 3)),
        exact_degree=3,
        error_coefficient=1.0 / 180.0,
        error_coefficient_latex=r"\frac{1}{180}",
        panel_latex=r"\frac{h}{3}\left(y_0 + 4y_1 + y_2\right)",
    ),
)

SIMPSON38_RULE = ClassicalRule(
    key=SIMPSON38,
    name="Simpson's 3/8 rule",
    constraint="multiple3",
    spec=PanelSpec(
        name="Simpson's 3/8 rule",
        panel_intervals=3,
        cotes=(_F(3, 8), _F(9, 8), _F(9, 8), _F(3, 8)),
        exact_degree=3,
        error_coefficient=1.0 / 80.0,
        error_coefficient_latex=r"\frac{1}{80}",
        panel_latex=r"\frac{3h}{8}\left(y_0 + 3y_1 + 3y_2 + y_3\right)",
    ),
)

BOOLE_RULE = ClassicalRule(
    key=BOOLE,
    name="Boole's rule",
    constraint="multiple4",
    spec=PanelSpec(
        name="Boole's rule",
        panel_intervals=4,
        cotes=(_F(14, 45), _F(64, 45), _F(24, 45), _F(64, 45), _F(14, 45)),
        exact_degree=5,
        error_coefficient=2.0 / 945.0,
        error_coefficient_latex=r"\frac{2}{945}",
        panel_latex=r"\frac{2h}{45}\left(7y_0 + 32y_1 + 12y_2 + 32y_3 + 7y_4\right)",
    ),
)

WEDDLE_RULE = ClassicalRule(
    key=WEDDLE,
    name="Weddle's rule",
    constraint="multiple6",
    spec=PanelSpec(
        name="Weddle's rule",
        panel_intervals=6,
        cotes=(
            _F(3, 10),
            _F(3, 2),
            _F(3, 10),
            _F(9, 5),
            _F(3, 10),
            _F(3, 2),
            _F(3, 10),
        ),
        exact_degree=5,
        error_coefficient=1.0 / 840.0,
        error_coefficient_latex=r"\frac{1}{840}",
        panel_latex=(
            r"\frac{3h}{10}\left(y_0 + 5y_1 + y_2 + 6y_3 + y_4 + 5y_5 + y_6\right)"
        ),
    ),
)

CLASSICAL_RULES: tuple[ClassicalRule, ...] = (
    TRAPEZOIDAL_RULE,
    SIMPSON13_RULE,
    SIMPSON38_RULE,
    BOOLE_RULE,
    WEDDLE_RULE,
)


def classical_constraint_failure(
    rule: ClassicalRule, total: int, method_id: str
) -> SolveResponse | None:
    """A ``failed`` response when the total subintervals break the rule."""
    multiples = {"even": 2, "multiple3": 3, "multiple4": 4, "multiple6": 6}
    if rule.constraint == "any":
        return None
    panels = multiples[rule.constraint]
    if total % panels == 0:
        return None
    low = total - (total % panels)
    high = total + (panels - total % panels)
    options = [f"n = {high}"]
    if low >= panels:
        options.append(f"n = {low}")
    return failed_response(
        method_id,
        f"{rule.name} needs a number of subintervals that is a multiple of {panels}, "
        f"but n = {total} is not. Choose {' or '.join(options)}.",
    )


# ---------------------------------------------------------------------------
# Tables, sums and steps
# ---------------------------------------------------------------------------


def cotes_table(spec: PanelSpec, decimals: int) -> DataTable:
    rows = [
        [i, fraction_latex(spec.cotes[i]), format_num(float(spec.cotes[i]), decimals)]
        for i in range(spec.panel_intervals + 1)
    ]
    return DataTable(
        title=f"Cotes numbers (one panel of {spec.panel_intervals} subintervals)",
        columns=["i", "Cotes number c_i", "Decimal"],
        rows=rows,
    )


def node_table(
    prepared: Prepared, weights: list[Fraction], decimals: int
) -> DataTable:
    rows = [
        [
            i,
            format_num(float(prepared.xs[i]), decimals),
            format_num(float(prepared.ys[i]), decimals),
            fraction_latex(weights[i]),
            format_num(float(weights[i]) * float(prepared.ys[i]), decimals),
        ]
        for i in range(prepared.n + 1)
    ]
    return DataTable(
        title="Nodes, exact weights and products",
        columns=["i", "x_i", "f(x_i)", "w_i (exact)", "w_i f(x_i)"],
        rows=rows,
    )


def substituted_sum_latex(
    prepared: Prepared, weights: list[Fraction], value: float, decimals: int, limit: int = 10
) -> str:
    terms = [
        rf"{fraction_latex(weights[i])}\left({format_num(float(prepared.ys[i]), decimals)}\right)"
        for i in range(prepared.n + 1)
    ]
    if len(terms) > limit:
        body = _join_signed([*terms[:limit], r"\cdots", terms[-1]])
    else:
        body = _join_signed(terms)
    return (
        rf"I \approx {format_num(prepared.h, decimals)}\left[\,{body}\,\right]"
        rf" = {format_num(value, decimals)}"
    )


def _error_bound(prepared: Prepared, spec: PanelSpec) -> float | None:
    if not math.isfinite(spec.error_coefficient):
        return None
    order = spec.derivative_order
    derivative_max: float | None
    if prepared.f is not None:
        derivative_max = numeric_derivative_max(
            prepared.f, prepared.a, prepared.b, order
        )
    else:
        coefficients = np.polyfit(prepared.xs, prepared.ys, len(prepared.xs) - 1)
        derivative_max = polynomial_derivative_max(
            coefficients, prepared.a, prepared.b, order
        )
    if derivative_max is None:
        return None
    return (
        spec.error_coefficient
        * (prepared.b - prepared.a)
        * prepared.h ** order
        * derivative_max
    )


def _build_steps(
    prepared: Prepared,
    spec: PanelSpec,
    panels: int,
    weights: list[Fraction],
    value: float,
    *,
    exact: float | None,
    abs_error: float | None,
    rel_error: float | None,
    bound: float | None,
    decimals: int,
) -> list[Step]:
    formula = spec.panel_latex + (
        rf"\quad\text{{(applied over {panels} panel{'s' if panels != 1 else ''})}}"
    )
    setup = Step(
        title="Set up the panels",
        latex=(
            rf"a = {format_num(prepared.a, decimals)},\quad "
            rf"b = {format_num(prepared.b, decimals)},\quad n = {prepared.n}"
            rf"\\[1mm] h = \frac{{b - a}}{{n}} = {format_num(prepared.h, decimals)}"
            rf"\\[1mm] \text{{panels}} = {panels},\quad "
            rf"\text{{panel size}} = {spec.panel_intervals}"
        ),
        note="Each panel spans the same number of equal subintervals.",
    )
    cotes_step = Step(
        title="Cotes numbers and panel formula",
        latex=(
            _join_signed(
                [f"{fraction_latex(c)}y_{{{i}}}" for i, c in enumerate(spec.cotes)]
            )
            + rf"\quad\Rightarrow\quad I \approx {formula}"
        ),
        note=(
            "The Cotes numbers are the integrals of the Lagrange basis polynomials "
            "over one panel; they are exact rational numbers."
        ),
    )
    sum_step = Step(
        title="Substituted weighted sum",
        latex=substituted_sum_latex(prepared, weights, value, decimals),
        note="Every node is multiplied by its exact composite weight and added.",
    )
    steps = [setup, cotes_step, sum_step]
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
                    rf"|E| \le {spec.error_coefficient_latex}\,(b-a)\,h^{{{spec.derivative_order}}}"
                    rf"\,M_{{{spec.derivative_order}}} \approx {format_num(bound, decimals)}"
                ),
                note=(
                    rf"$M_{{{spec.derivative_order}}} = \max |f^{{({spec.derivative_order})}}|$ "
                    "is estimated numerically, so the bound is itself an estimate."
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


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def panel_area_plot(
    prepared: Prepared,
    spec: PanelSpec,
    *,
    convergence: tuple[list[int], list[float]] | None,
) -> PlotPayload:
    xs = prepared.xs
    ys = prepared.ys
    approx_x, approx_y = _approximation_curve(xs, ys, spec.panel_intervals)
    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines",
            "name": f"{spec.name} pieces",
            "x": approx_x,
            "y": approx_y,
            "fill": "tozeroy",
            "fillcolor": "rgba(245, 158, 11, 0.20)",
            "line": {"color": "#f59e0b", "width": 1.5},
        }
    ]
    if prepared.f is not None:
        curve_x, curve_y = sample_curve(prepared.f, prepared.a, prepared.b)
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "f(x)",
                "x": curve_x,
                "y": curve_y,
                "line": {"color": "#2563eb", "width": 2},
            }
        )
    traces.append(
        points_trace(
            [float(value) for value in xs],
            [float(value) for value in ys],
            "Nodes f(x_i)",
        )
    )

    layout: dict[str, Any] = {
        "title": {"text": f"{spec.name}: composite integration"},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "f(x)"}},
    }
    if convergence is not None and convergence[0]:
        steps, errors = convergence
        layout = {
            "title": {"text": f"{spec.name}: area and convergence"},
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
        if errors[0] > 0 and all(error > 0 for error in errors):
            slope = spec.convergence_order
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": f"slope {slope}",
                    "x": [steps[0], steps[-1]],
                    "y": [errors[0], errors[0] * (steps[-1] / steps[0]) ** (-slope)],
                    "xaxis": "x2",
                    "yaxis": "y2",
                    "line": {"color": "#16a34a", "dash": "dash"},
                }
            )
    return PlotPayload(traces=traces, layout=layout)


def comparison_plot(
    prepared: Prepared, valid: list[tuple[ClassicalRule, float]]
) -> PlotPayload:
    traces: list[dict[str, Any]] = []
    if prepared.f is not None:
        curve_x, curve_y = sample_curve(prepared.f, prepared.a, prepared.b)
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "f(x)",
                "x": curve_x,
                "y": curve_y,
                "line": {"color": "#111827", "width": 2.5},
            }
        )
    for rule, _value in valid:
        approx_x, approx_y = _approximation_curve(
            prepared.xs, prepared.ys, rule.spec.panel_intervals
        )
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": rule.name,
                "x": approx_x,
                "y": approx_y,
                "line": {"color": COMPARE_COLORS[rule.key], "width": 1.5},
            }
        )
    layout: dict[str, Any] = {
        "title": {"text": "Comparison of quadrature rules on the same integral"},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "f(x)"}},
        "legend": {"orientation": "h", "y": -0.2},
    }
    return PlotPayload(traces=traces, layout=layout)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def comparison(
    prepared: Prepared, total: int, exact: float | None, decimals: int
) -> tuple[DataTable, list[tuple[ClassicalRule, float]]]:
    valid: list[tuple[ClassicalRule, float]] = []
    rows: list[list[Any]] = []
    for rule in CLASSICAL_RULES:
        spec = rule.spec
        if total % spec.panel_intervals != 0:
            continue
        panels = total // spec.panel_intervals
        weights = composite_node_weights(spec.panel_intervals, spec.cotes, panels)
        value = prepared.h * sum(
            float(weights[i]) * float(prepared.ys[i]) for i in range(total + 1)
        )
        error = abs(value - exact) if exact is not None else None
        valid.append((rule, value))
        rows.append(
            [
                rule.name,
                format_num(value, decimals),
                format_num(error, decimals) if error is not None else r"\text{n/a}",
            ]
        )
    table = DataTable(
        title=f"Comparison of rules on the same {total} subintervals",
        columns=["Method", "Value", "Absolute error"],
        rows=rows,
    )
    return table, valid


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def classical_schema(default_n: int) -> list[InputField]:
    """The Group B form plus a rule-comparison toggle."""
    return [
        *quadrature_schema(default_n),
        boolean_field(
            "compare",
            "Compare rules on the same integral",
            False,
            help="Runs every rule valid for this n and overlays them with a value/error table.",
        ),
    ]


def newton_cotes_schema() -> list[InputField]:
    return [
        InputField(
            key="source",
            label="Input type",
            type="select",
            required=True,
            default="function",
            options=[
                SelectOption(value="function", label="Function f(x) with a, b, n and m"),
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
            key="n",
            label="Panel size n (subintervals per panel, 1-8)",
            type="integer",
            required=True,
            default=4,
            min=1,
            max=8,
            help="One panel interpolation degree. n = 1 trapezoidal, 2 Simpson 1/3, 3 Simpson 3/8, 4 Boole.",
        ),
        InputField(
            key="panels",
            label="Composite panels m",
            type="integer",
            required=True,
            default=1,
            min=1,
            max=10_000,
            help="Total subintervals = n x m. Use m = 1 for the single-panel formula.",
        ),
        boolean_field(
            "compare",
            "Compare rules on the same integral",
            False,
            help="Runs every rule valid for the total n and overlays them with a value/error table.",
        ),
        boolean_field(
            "show_convergence",
            "Show convergence of error vs n",
            False,
            help="Adds a semilog convergence study (function input with a known exact value).",
        ),
        precision_field(),
    ]


def prepare_newton_cotes(
    inputs: dict[str, Any], decimals: int, method_id: str
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
        total = len(xs) - 1
        panel = int(inputs["n"])
        if total % panel != 0:
            divisors = [d for d in range(1, 9) if total % d == 0]
            options = ", ".join(f"n = {d}" for d in divisors) or "a different table"
            return failed_response(
                method_id,
                f"The table has {total} subintervals, which is not divisible into panels "
                f"of n = {panel}. Choose {options}.",
            )
        a = float(xs[0])
        b = float(xs[-1])
        h = common_step(xs)
        return Prepared(xs, ys, a, b, total, h, None, None, notices)

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
        return Prepared(
            np.array([a], dtype=float),
            np.array([float(f(a))], dtype=float),
            a,
            b,
            0,
            0.0,
            f,
            expr,
            notices,
        )

    panel = int(inputs["n"])
    panels = int(inputs["panels"])
    if panels < 1:
        raise InvalidInputError("The number of composite panels m must be at least 1.")
    total = panel * panels
    h = (b - a) / total
    grid = np.linspace(a, b, total + 1)
    values = np.array([float(f(x)) for x in grid], dtype=float)
    return Prepared(grid, values, a, b, total, h, f, expr, notices)


def newton_cotes_spec(panel_intervals: int) -> PanelSpec:
    """The general closed Newton-Cotes panel of the requested size."""
    cotes = cotes_numbers(panel_intervals)
    exact_degree = panel_intervals if panel_intervals % 2 == 1 else panel_intervals + 1
    coefficients = {
        # composite error coefficient (b-a) h^(d+1) f^(d+1), for the common sizes
        1: (1.0 / 12.0, r"\frac{1}{12}"),
        2: (1.0 / 180.0, r"\frac{1}{180}"),
        3: (1.0 / 80.0, r"\frac{1}{80}"),
        4: (2.0 / 945.0, r"\frac{2}{945}"),
    }
    coefficient, coefficient_latex = coefficients.get(
        panel_intervals, (math.nan, r"\text{(see Newton-Cotes tables)}")
    )
    terms = _join_signed(
        [rf"{fraction_latex(cotes[i])}y_{{{i}}}" for i in range(panel_intervals + 1)]
    )
    return PanelSpec(
        name=f"Newton-Cotes ({panel_intervals} subintervals)",
        panel_intervals=panel_intervals,
        cotes=cotes,
        exact_degree=exact_degree,
        error_coefficient=coefficient,
        error_coefficient_latex=coefficient_latex,
        panel_latex=rf"h\left[\,{terms}\,\right]",
        reproduces=CLASSICAL_BY_PANEL.get(panel_intervals),
    )


# ---------------------------------------------------------------------------
# Shared finishing
# ---------------------------------------------------------------------------


def finalize_panel(
    method_id: str,
    prepared: Prepared,
    spec: PanelSpec,
    panels: int,
    inputs: dict[str, Any],
    decimals: int,
    *,
    notices: list[str],
) -> SolveResponse:
    weights = composite_node_weights(spec.panel_intervals, spec.cotes, panels)
    value = prepared.h * sum(
        float(weights[i]) * float(prepared.ys[i]) for i in range(prepared.n + 1)
    )

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

    bound = _error_bound(prepared, spec)

    tables = [
        cotes_table(spec, decimals),
        node_table(prepared, weights, decimals),
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
            base_panels = panels
            step_panels = [base_panels * (2**k) for k in range(5)]
            totals = [spec.panel_intervals * count for count in step_panels]
            h_values = [(prepared.b - prepared.a) / total for total in totals]
            errors = [
                abs(_panelled_value(prepared.f, prepared.a, prepared.b, spec, count) - exact)
                for count in step_panels
            ]
            convergence = (totals, errors)
            tables.append(convergence_table(totals, errors, h_values, decimals))

    compare_on = bool(inputs.get("compare"))
    if compare_on:
        compare_table, valid = comparison(prepared, prepared.n, exact, decimals)
        tables.append(compare_table)
        if convergence is not None:
            notices.append(
                "Convergence and rule comparison were both requested; the comparison "
                "overlay is plotted and the convergence values remain in the table."
            )
        plot = comparison_plot(prepared, valid)
    else:
        plot = panel_area_plot(prepared, spec, convergence=convergence)

    steps = _build_steps(
        prepared,
        spec,
        panels,
        weights,
        value,
        exact=exact,
        abs_error=abs_error,
        rel_error=rel_error,
        bound=bound,
        decimals=decimals,
    )

    result: dict[str, Any] = {
        "value": value,
        "a": prepared.a,
        "b": prepared.b,
        "n": prepared.n,
        "h": prepared.h,
        "panel_intervals": spec.panel_intervals,
        "panels": panels,
        "cotes_latex": [fraction_latex(c) for c in spec.cotes],
        "exact_value": exact,
        "reference_value": reference,
        "absolute_error": abs_error,
        "relative_error_percent": rel_error,
        "error_bound": bound,
    }
    if spec.reproduces is not None:
        result["reproduces"] = spec.reproduces

    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=tables,
        plot=plot,
        errors=ErrorInfo(absolute=abs_error, relative_percent=rel_error),
        warnings=notices,
    )


def _panelled_value(
    f: Any, a: float, b: float, spec: PanelSpec, panels: int
) -> float:
    total = spec.panel_intervals * panels
    h = (b - a) / total
    grid = np.linspace(a, b, total + 1)
    weights = composite_node_weights(spec.panel_intervals, spec.cotes, panels)
    return h * sum(float(weights[i]) * float(f(grid[i])) for i in range(total + 1))


def solve_classical(
    meta: MethodMeta,
    rule: ClassicalRule,
    inputs: dict[str, Any],
    limits: SolverLimits,
) -> SolveResponse:
    """Shared entry point for the composite classical rules (Boole, Weddle)."""
    del limits
    method_id = meta.id
    decimals = int(inputs.get("decimal_precision", 6))

    prepared = _prepare(inputs, decimals, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    notices = list(prepared.notices)

    if prepared.n == 0:
        return _degenerate_response(method_id, prepared, notices, decimals)

    singular_x = first_nonfinite(prepared)
    if singular_x is not None:
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

    failure = classical_constraint_failure(rule, prepared.n, method_id)
    if failure is not None:
        failure.warnings.extend(notices)
        return failure

    panels = prepared.n // rule.spec.panel_intervals
    return finalize_panel(
        method_id, prepared, rule.spec, panels, inputs, decimals, notices=notices
    )
