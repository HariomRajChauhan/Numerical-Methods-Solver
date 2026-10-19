"""Gauss-Legendre quadrature for numerical integration (Chapter 4).

Gauss-Legendre quadrature places optimally chosen nodes inside each panel and
maps them from the reference interval [-1, 1] to [a, b]. With n nodes it is
exact for polynomials up to degree 2n-1, needing far fewer evaluations than the
Newton-Cotes rules for the same accuracy.

Nodes and weights:
  1-point: t = 0                     w = 2
  2-point: t = +-1/sqrt(3)           w = 1
  3-point: t = 0, +-sqrt(3/5)        w = 8/9, 5/9
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

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
    SelectOption,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.parser import make_function, parse_expression
from app.core.registry import register
from app.solvers._common import (
    boolean_field,
    failed_response,
    format_num,
    function_field,
    number_field,
    precision_field,
    sample_curve,
)
from app.solvers.ch4_diff_integration._quadrature import (
    Prepared,
    first_nonfinite,
    numeric_derivative_max,
    reference_integral,
    summary_table,
    symbolic_integral,
)

SQRT = math.sqrt
GAUSS_RULES: dict[int, list[tuple[float, float]]] = {
    1: [(0.0, 2.0)],
    2: [(-1.0 / SQRT(3.0), 1.0), (1.0 / SQRT(3.0), 1.0)],
    3: [(-SQRT(3.0 / 5.0), 5.0 / 9.0), (0.0, 8.0 / 9.0), (SQRT(3.0 / 5.0), 5.0 / 9.0)],
}

NODE_LATEX: dict[int, list[tuple[str, str]]] = {
    1: [(r"0", r"2")],
    2: [(r"-\frac{1}{\sqrt{3}}", r"1"), (r"\frac{1}{\sqrt{3}}", r"1")],
    3: [
        (r"-\sqrt{\frac{3}{5}}", r"\frac{5}{9}"),
        (r"0", r"\frac{8}{9}"),
        (r"\sqrt{\frac{3}{5}}", r"\frac{5}{9}"),
    ],
}


def _node_latex(n: int) -> str:
    parts = [
        rf"t_{{{i + 1}}} = {t},\ w_{{{i + 1}}} = {w}"
        for i, (t, w) in enumerate(NODE_LATEX[n])
    ]
    return r"\quad ".join(parts)


def _schema() -> list[InputField]:
    return [
        function_field(),
        number_field("a", "Lower limit a", 0.0),
        number_field("b", "Upper limit b", 1.0),
        InputField(
            key="points",
            label="Number of points",
            type="select",
            required=True,
            default="2",
            options=[
                SelectOption(value="1", label="1-point (midpoint rule)"),
                SelectOption(value="2", label="2-point (default, exact to degree 3)"),
                SelectOption(value="3", label="3-point (exact to degree 5)"),
            ],
            help="Number of Gauss-Legendre nodes per panel.",
        ),
        InputField(
            key="panels",
            label="Composite panels m",
            type="integer",
            required=True,
            default=1,
            min=1,
            max=10_000,
            help="Split [a, b] into m equal panels and apply the rule to each.",
        ),
        boolean_field(
            "compare",
            "Compare rules (2-point vs 3-point vs Simpson 1/3)",
            False,
            help="Runs the Gauss rules and Simpson's 1/3 rule with function evaluation counts.",
        ),
        precision_field(),
    ]


META = MethodMeta(
    id="gauss_legendre",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Gauss-Legendre Quadrature",
    summary=(
        "Optimal nodes and weights on [-1, 1] mapped to [a, b]; with n points it is exact "
        "for polynomials up to degree 2n-1 and needs very few evaluations."
    ),
    theory=(
        "Gauss-Legendre quadrature integrates f exactly for polynomials of degree up to "
        "2n-1 using just n interior nodes. On the reference interval [-1, 1] the nodes are "
        "the roots of the Legendre polynomial P_n and the weights are chosen so that "
        "  integral_{-1}^{1} g(t) dt ~= sum_i w_i g(t_i).\n"
        "For a general interval the linear map x = ((b - a) t + (b + a)) / 2, "
        "dx = ((b - a)/2) dt gives\n"
        "  integral_a^b f(x) dx ~= ((b - a)/2) sum_i w_i f(x_i).\n\n"
        "Two points give t = +-1/sqrt(3) with weights 1 (exact to degree 3); three points "
        "give t = 0, +-sqrt(3/5) with weights 8/9 and 5/9 (exact to degree 5); one point is "
        "the midpoint rule (exact to degree 1). For composite integration the interval is "
        "split into m panels and the rule applied to each, so the total number of function "
        "evaluations is n*m. The error is\n"
        "  E = (b - a)^(2n+1) (n!)^4 / [(2n+1)((2n)!)^3] f^(2n)(xi),\n"
        "so doubling the number of points raises the order of accuracy sharply."
    ),
    formulas=[
        LabeledLatex(
            label="Change of interval",
            latex=r"x = \frac{(b - a)t + (b + a)}{2}, \qquad dx = \frac{b - a}{2}\,dt",
        ),
        LabeledLatex(
            label="Gauss-Legendre rule",
            latex=r"\int_a^b f(x)\,dx \approx \frac{b - a}{2}\sum_{i=1}^{n} w_i f(x_i)",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E = \frac{(b - a)^{2n+1}(n!)^4}{(2n+1)\left((2n)!\right)^3}"
            r"\,f^{(2n)}(\xi), \qquad a < \xi < b",
        ),
    ],
    pseudocode=(
        "GaussLegendre(f, a, b, n, m):\n"
        "    obtain nodes t_i and weights w_i on [-1, 1] for n points\n"
        "    H <- (b - a) / m\n"
        "    I <- 0\n"
        "    for panel k = 0..m-1:\n"
        "        l <- a + k*H;  c <- l + H/2\n"
        "        for i = 0..n-1:\n"
        "            x <- c + (H/2) * t_i\n"
        "            I <- I + (H/2) * w_i * f(x)\n"
        "    return I"
    ),
    input_schema=_schema(),
    examples=[
        MethodExample(
            name="2-point on exp(x) over [0, 1]",
            description="Four-degree exactness: about 1.71828 (exact e - 1).",
            inputs={
                "function": "exp(x)",
                "a": 0.0,
                "b": 1.0,
                "points": "2",
                "panels": 1,
                "compare": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="3-point on sin(x) over [0, pi]",
            description="Exact to degree 5: about 2.00139 (exact 2).",
            inputs={
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "points": "3",
                "panels": 1,
                "compare": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Compare rules on sin(x) over [0, pi]",
            description="2-point vs 3-point vs Simpson's 1/3 with evaluation counts.",
            inputs={
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "points": "2",
                "panels": 2,
                "compare": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


def _prepare_function(
    inputs: dict[str, Any], decimals: int, method_id: str
) -> Prepared | SolveResponse:
    text = inputs.get("function")
    if not text:
        raise InvalidInputError("A function expression is required.")
    a = float(inputs.get("a", 0.0))
    b = float(inputs.get("b", 1.0))
    notices: list[str] = []
    if a > b:
        a, b = b, a
        notices.append("a and b were swapped so that a < b.")
    expr = parse_expression(text, ("x",))
    f = make_function(expr, ("x",), strict=False)
    return Prepared(
        np.array([], dtype=float),
        np.array([], dtype=float),
        a,
        b,
        0,
        0.0,
        f,
        expr,
        notices,
    )


def _panels(a: float, b: float, m: int) -> list[tuple[float, float]]:
    width = (b - a) / m
    return [(a + k * width, a + (k + 1) * width) for k in range(m)]


def _gauss_value(
    f: Any, a: float, b: float, nodes: list[tuple[float, float]], m: int
) -> float:
    total = 0.0
    for left, right in _panels(a, b, m):
        half = (right - left) / 2.0
        centre = (right + left) / 2.0
        for t, w in nodes:
            total += half * w * float(f(centre + half * t))
    return total


def _node_table(
    f: Any,
    a: float,
    b: float,
    nodes: list[tuple[float, float]],
    m: int,
    decimals: int,
) -> DataTable:
    columns = ["i", "t_i", "x_i", "f(x_i)", "w_i", "w_i f(x_i)"]
    rows: list[list[Any]] = []
    multi = m > 1
    if multi:
        columns = ["Panel", *columns]
    for panel_index, (left, right) in enumerate(_panels(a, b, m)):
        half = (right - left) / 2.0
        centre = (right + left) / 2.0
        for i, (t, w) in enumerate(nodes):
            x = centre + half * t
            y = float(f(x))
            row: list[Any] = [
                i + 1,
                format_num(t, decimals),
                format_num(x, decimals),
                format_num(y, decimals),
                format_num(w, decimals),
                format_num(w * y, decimals),
            ]
            if multi:
                row = [panel_index + 1, *row]
            rows.append(row)
    return DataTable(
        title="Gauss-Legendre nodes, transformed points and weighted terms",
        columns=columns,
        rows=rows,
    )


def _error_bound(f: Any, a: float, b: float, n: int, m: int) -> float | None:
    width = (b - a) / m
    coefficient = math.factorial(n) ** 4 / ((2 * n + 1) * math.factorial(2 * n) ** 3)
    derivative_max = numeric_derivative_max(f, a, b, 2 * n)
    if derivative_max is None:
        return None
    return (b - a) * width ** (2 * n) * coefficient * derivative_max


def _simpson13(f: Any, a: float, b: float, intervals: int) -> float:
    n = intervals if intervals % 2 == 0 else intervals + 1
    h = (b - a) / n
    weights = np.array(
        [1.0 if i in (0, n) else (4.0 if i % 2 == 1 else 2.0) for i in range(n + 1)]
    )
    xs = np.linspace(a, b, n + 1)
    return float(h / 3.0 * sum(w * float(f(x)) for w, x in zip(weights, xs, strict=True)))


def _comparison_table(
    f: Any, a: float, b: float, m: int, exact: float | None, decimals: int
) -> DataTable:
    rows: list[list[Any]] = []
    for points in (2, 3):
        value = _gauss_value(f, a, b, GAUSS_RULES[points], m)
        error = abs(value - exact) if exact is not None else None
        rows.append(
            [
                f"Gauss-Legendre {points}-point",
                points * m,
                format_num(value, decimals),
                format_num(error, decimals) if error is not None else r"\text{n/a}",
            ]
        )
    intervals = 2 * m
    simpson = _simpson13(f, a, b, intervals)
    error = abs(simpson - exact) if exact is not None else None
    rows.append(
        [
            "Simpson's 1/3",
            intervals + 1,
            format_num(simpson, decimals),
            format_num(error, decimals) if error is not None else r"\text{n/a}",
        ]
    )
    return DataTable(
        title="Comparison: Gauss-Legendre 2-point vs 3-point vs Simpson's 1/3",
        columns=["Method", "Function evaluations", "Value", "Absolute error"],
        rows=rows,
    )


def _build_steps(
    a: float,
    b: float,
    n: int,
    m: int,
    nodes: list[tuple[float, float]],
    value: float,
    *,
    exact: float | None,
    abs_error: float | None,
    rel_error: float | None,
    bound: float | None,
    decimals: int,
) -> list[Step]:
    width = (b - a) / m
    transform = Step(
        title="Change of interval",
        latex=(
            rf"x = \frac{{(b - a)t + (b + a)}}{{2}}, \qquad dx = \frac{{b - a}}{{2}}\,dt"
            rf"\\[1mm] a = {format_num(a, decimals)},\quad b = {format_num(b, decimals)},"
            rf"\quad n = {n},\quad m = {m}"
        ),
        note=f"Composite panels of width H = (b - a)/m = {format_num(width, decimals)}.",
    )
    nodes_latex = _node_latex(n)
    node_step = Step(
        title="Nodes and weights",
        latex=(
            rf"\int_a^b f(x)\,dx \approx \frac{{b - a}}{{2}}\sum_{{i=1}}^{{{n}}} w_i f(x_i)"
            rf"\\[1mm] {nodes_latex}"
        ),
        note="Nodes t_i are the roots of the Legendre polynomial P_n; weights w_i sum to 2.",
    )
    if m == 1:
        terms = []
        for t, w in nodes:
            x = (a + b) / 2.0 + (b - a) / 2.0 * t
            terms.append(
                rf"{format_num(w, decimals)}\,f({format_num(x, decimals)})"
            )
        sum_latex = (
            r"I \approx \frac{b - a}{2}\left[\,"
            + " + ".join(terms)
            + rf"\,\right] = {format_num(value, decimals)}"
        )
    else:
        sum_latex = (
            rf"I \approx \sum_{{k=1}}^{{{m}}} \frac{{H}}{{2}}\sum_{{i=1}}^{{{n}}} "
            rf"w_i f(x_i) = {format_num(value, decimals)}"
        )
    sum_step = Step(
        title="Substituted weighted sum",
        latex=sum_latex,
        note="Each transformed node is weighted and added; composite panels are summed.",
    )
    steps = [transform, node_step, sum_step]
    if exact is not None:
        steps.append(
            Step(
                title="Exact value",
                latex=(
                    rf"\int_{{{format_num(a, decimals)}}}^{{{format_num(b, decimals)}}}"
                    rf" f(x)\,dx = {format_num(exact, decimals)}"
                ),
                note="Evaluated symbolically with SymPy.",
            )
        )
    if abs_error is not None:
        error_latex = rf"\text{{Absolute error}} = {format_num(abs_error, decimals)}"
        if rel_error is not None:
            error_latex += (
                rf",\qquad \text{{Relative error}} = {format_num(rel_error, decimals)}\%"
            )
        steps.append(
            Step(title="Error", latex=error_latex, note="Compared with the exact value.")
        )
    if bound is not None:
        steps.append(
            Step(
                title="Theoretical error bound",
                latex=(
                    rf"|E| \le \frac{{(b-a)^{{{2 * n + 1}}}(n!)^4}}"
                    rf"{{(2n+1)\left((2n)!\right)^3}}\,f^{{({2 * n})}}(\xi)"
                    rf" \approx {format_num(bound, decimals)}"
                ),
                note=(
                    rf"$f^{{({2 * n})}}$ is estimated numerically, so the bound is an estimate."
                ),
            )
        )
    steps.append(
        Step(
            title="Result",
            latex=(
                rf"\int_{{{format_num(a, decimals)}}}^{{{format_num(b, decimals)}}}"
                rf" f(x)\,dx \approx {format_num(value, decimals)}"
            ),
            note=f"Exact for polynomials up to degree {2 * n - 1}.",
        )
    )
    return steps


def _plot(f: Any, a: float, b: float, node_x: list[float], node_y: list[float]) -> PlotPayload:
    curve_x, curve_y = sample_curve(f, a, b)
    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines",
            "name": "f(x)",
            "x": curve_x,
            "y": curve_y,
            "fill": "tozeroy",
            "fillcolor": "rgba(37, 99, 235, 0.15)",
            "line": {"color": "#2563eb", "width": 2},
        },
        {
            "type": "scatter",
            "mode": "markers",
            "name": "Gauss nodes",
            "x": node_x,
            "y": node_y,
            "marker": {"size": 10, "color": "#dc2626", "symbol": "circle"},
        },
    ]
    layout: dict[str, Any] = {
        "title": {"text": "Gauss-Legendre nodes over the shaded area"},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "f(x)"}},
    }
    return PlotPayload(traces=traces, layout=layout)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate with Gauss-Legendre quadrature."""
    del limits
    method_id = "gauss_legendre"
    decimals = int(inputs.get("decimal_precision", 6))
    n = int(str(inputs.get("points", 2)))
    if n not in GAUSS_RULES:
        raise InvalidInputError("The number of Gauss points must be 1, 2 or 3.")
    m = int(inputs.get("panels", 1))
    if m < 1:
        raise InvalidInputError("The number of composite panels m must be at least 1.")

    prepared = _prepare_function(inputs, decimals, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    notices = list(prepared.notices)
    assert prepared.f is not None

    if prepared.a == prepared.b:
        return SolveResponse(
            method=method_id,
            status=SolveStatus.CONVERGED,
            result={
                "value": 0.0,
                "a": prepared.a,
                "b": prepared.b,
                "points": n,
                "panels": m,
                "exact_value": 0.0,
                "absolute_error": 0.0,
            },
            steps=[
                Step(
                    title="Degenerate interval",
                    latex=(
                        rf"a = b = {format_num(prepared.a, decimals)} \;\Rightarrow\; "
                        rf"\int_a^b f(x)\,dx = 0"
                    ),
                    note="The lower and upper limits coincide, so the integral is zero.",
                )
            ],
            tables=[summary_table(0.0, 0.0, 0.0, None, None, decimals)],
            plot=PlotPayload(),
            errors=ErrorInfo(absolute=0.0),
            warnings=notices
            or ["The interval is degenerate (a = b), so the integral is exactly 0."],
        )

    singular_x = first_nonfinite(prepared)
    if singular_x is not None:
        return failed_response(
            method_id,
            "The integrand is not finite near "
            f"x = {format_num(singular_x, decimals)}; it is singular on [a, b].",
            warnings=notices,
        )

    nodes = GAUSS_RULES[n]
    node_x: list[float] = []
    node_y: list[float] = []
    for left, right in _panels(prepared.a, prepared.b, m):
        half = (right - left) / 2.0
        centre = (right + left) / 2.0
        for t, _w in nodes:
            x = centre + half * t
            y = float(prepared.f(x))
            if not math.isfinite(y):
                return failed_response(
                    method_id,
                    "The integrand is not finite at the node "
                    f"x = {format_num(x, decimals)}; the integral is singular there.",
                    warnings=notices,
                )
            node_x.append(x)
            node_y.append(y)

    value = _gauss_value(prepared.f, prepared.a, prepared.b, nodes, m)

    exact: float | None = None
    reference: float | None = None
    if prepared.expr is not None:
        exact = symbolic_integral(prepared.expr, prepared.a, prepared.b)
    if exact is None:
        reference = reference_integral(prepared.f, prepared.a, prepared.b)
    target = exact if exact is not None else reference

    abs_error: float | None = None
    rel_error: float | None = None
    if target is not None:
        abs_error = abs(value - target)
        if target != 0.0:
            rel_error = abs(abs_error / target) * 100.0

    bound = _error_bound(prepared.f, prepared.a, prepared.b, n, m)

    tables = [
        _node_table(prepared.f, prepared.a, prepared.b, nodes, m, decimals),
        summary_table(value, exact, abs_error, rel_error, bound, decimals, reference=reference),
    ]
    if bool(inputs.get("compare")):
        tables.append(
            _comparison_table(prepared.f, prepared.a, prepared.b, m, exact, decimals)
        )

    steps = _build_steps(
        prepared.a,
        prepared.b,
        n,
        m,
        nodes,
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
        "points": n,
        "panels": m,
        "evaluations": n * m,
        "exact_degree": 2 * n - 1,
        "exact_value": exact,
        "reference_value": reference,
        "absolute_error": abs_error,
        "relative_error_percent": rel_error,
        "error_bound": bound,
    }

    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=tables,
        plot=_plot(prepared.f, prepared.a, prepared.b, node_x, node_y),
        errors=ErrorInfo(absolute=abs_error, relative_percent=rel_error),
        warnings=notices,
    )
