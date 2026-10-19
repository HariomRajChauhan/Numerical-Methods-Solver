"""Romberg integration for numerical integration (Chapter 4).

Romberg integration applies Richardson extrapolation to the composite
trapezoidal rule evaluated on successively halved steps. Each level adds one
trapezoid estimate (reusing the previous function values) and a new column of
extrapolations

``R(i, j) = R(i, j-1) + (R(i, j-1) - R(i-1, j-1)) / (4^(j-1) - 1)``,

until the gap between successive diagonal entries falls below the tolerance.
"""

from __future__ import annotations

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
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.parser import make_function, parse_expression
from app.core.registry import register
from app.solvers._common import (
    failed_response,
    format_num,
    function_field,
    number_field,
    precision_field,
    tolerance_field,
)
from app.solvers.ch4_diff_integration._quadrature import (
    Prepared,
    first_nonfinite,
    reference_integral,
    summary_table,
    symbolic_integral,
)


def _schema() -> list[InputField]:
    return [
        function_field(),
        number_field("a", "Lower limit a", 0.0),
        number_field("b", "Upper limit b", 1.0),
        tolerance_field(
            default=1e-8,
            help="Stop when the gap between successive diagonal entries is below this value.",
        ),
        InputField(
            key="max_levels",
            label="Maximum levels",
            type="integer",
            required=True,
            default=6,
            min=1,
            max=8,
            help="Rows of the Romberg table; level i uses n = 2^(i-1) subintervals.",
        ),
        precision_field(),
    ]


META = MethodMeta(
    id="romberg",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Romberg Integration",
    summary=(
        "Richardson extrapolation of the trapezoidal rule on successively halved steps; "
        "converges very rapidly for smooth integrands and stops when the diagonal stabilises."
    ),
    theory=(
        "Romberg integration starts from the composite trapezoidal rule. Writing T_k for "
        "the estimate with n = 2^k subintervals, the trapezoidal error has an expansion "
        "in even powers of h, T_k = I + c_1 h_k^2 + c_2 h_k^4 + ... Eliminating these "
        "terms one at a time by Richardson extrapolation\n"
        "  R(i, j) = R(i, j-1) + (R(i, j-1) - R(i-1, j-1)) / (4^(j-1) - 1)\n"
        "yields a triangular table whose diagonal R(i, i) converges to the integral much "
        "faster than the trapezoidal rule alone. The first extrapolation column "
        "reproduces Simpson's rule, the second Boole's rule, and so on.\n\n"
        "Each new trapezoidal row reuses the function values of the previous row and only "
        "evaluates the odd-indexed new nodes: level 1 needs 2 evaluations, and level "
        "k > 1 needs 2^(k-1) new evaluations. The iteration stops when the difference "
        "between successive diagonal entries |R(i, i) - R(i-1, i-1)| drops below the "
        "tolerance; otherwise it reports status 'max_iter' with the best available value."
    ),
    formulas=[
        LabeledLatex(
            label="Trapezoidal first column",
            latex=r"R(i, 1) = \frac{h_i}{2}\left[\,f(a) + 2\sum_{k=1}^{n_i-1} "
            r"f(a + k h_i) + f(b)\,\right], \qquad h_i = \frac{b - a}{2^{i-1}}",
        ),
        LabeledLatex(
            label="Richardson extrapolation",
            latex=r"R(i, j) = R(i, j-1) + \frac{R(i, j-1) - R(i-1, j-1)}{4^{\,j-1} - 1}",
        ),
        LabeledLatex(
            label="Stopping test",
            latex=r"\left|R(i, i) - R(i-1, i-1)\right| < \text{tolerance}",
        ),
    ],
    pseudocode=(
        "Romberg(f, a, b, tolerance, max_levels):\n"
        "    h <- b - a\n"
        "    R[1,1] <- h/2 * (f(a) + f(b))\n"
        "    for i = 2..max_levels:\n"
        "        h <- h / 2                              # new evaluations at odd nodes\n"
        "        S <- sum of f at the new interior nodes\n"
        "        R[i,1] <- R[i-1,1]/2 + h * S\n"
        "        for j = 2..i:\n"
        "            R[i,j] <- R[i,j-1] + (R[i,j-1] - R[i-1,j-1])/(4^(j-1) - 1)\n"
        "        if |R[i,i] - R[i-1,i-1]| < tolerance: return R[i,i]\n"
        "    return R[max_levels, max_levels]   # tolerance not reached"
    ),
    input_schema=_schema(),
    examples=[
        MethodExample(
            name="sin x on [0, pi]",
            description="Tolerance 1e-8 is reached in a few levels (exact 2).",
            inputs={
                "function": "sin(x)",
                "a": 0.0,
                "b": 3.141592653589793,
                "tolerance": 1e-8,
                "max_levels": 6,
                "decimal_precision": 8,
            },
        ),
        MethodExample(
            name="1/(1 + x^2) on [0, 1]",
            description="A smooth integrand converging to pi/4 = 0.78539816...",
            inputs={
                "function": "1/(1 + x^2)",
                "a": 0.0,
                "b": 1.0,
                "tolerance": 1e-10,
                "max_levels": 7,
                "decimal_precision": 10,
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


def _trapezoid_rows(
    f: Any, a: float, b: float, max_levels: int, tolerance: float
) -> tuple[list[dict[str, float]], list[list[float]], int | None]:
    """Build the Romberg table incrementally, stopping when the diagonal settles."""
    rows: list[dict[str, float]] = []
    table: list[list[float]] = []
    converged_level: int | None = None

    h = b - a
    estimate = 0.5 * h * (float(f(a)) + float(f(b)))
    rows.append({"n": 1, "h": h, "new": 2, "value": estimate})
    table.append([estimate])
    diagonal = [estimate]

    for level in range(1, max_levels):
        n = 2**level
        h = (b - a) / n
        interior = 0.0
        for index in range(1, n, 2):
            interior += float(f(a + index * h))
        estimate = 0.5 * estimate + h * interior
        rows.append({"n": n, "h": h, "new": n // 2, "value": estimate})

        row = [estimate]
        for j in range(1, level + 1):
            previous = table[level - 1][j - 1]
            row.append(row[j - 1] + (row[j - 1] - previous) / (4**j - 1))
        table.append(row)
        diagonal.append(row[-1])

        if abs(diagonal[-1] - diagonal[-2]) < tolerance:
            converged_level = level
            break

    return rows, table, converged_level


def _triangular_table(table: list[list[float]], decimals: int) -> DataTable:
    width = len(table)
    columns = ["i"] + [f"R(i,{j + 1})" for j in range(width)]
    rows: list[list[Any]] = []
    for i, entries in enumerate(table):
        padded = [format_num(value, decimals) for value in entries]
        padded += [""] * (width - len(entries))
        rows.append([i + 1, *padded])
    return DataTable(title="Romberg triangular table", columns=columns, rows=rows)


def _trapezoid_table(rows: list[dict[str, float]], decimals: int) -> DataTable:
    return DataTable(
        title="Trapezoidal estimates R(i,1) with new evaluations",
        columns=["i", "n = 2^(i-1)", "h", "New evaluations", "R(i,1)"],
        rows=[
            [
                i + 1,
                int(row["n"]),
                format_num(row["h"], decimals),
                int(row["new"]),
                format_num(row["value"], decimals),
            ]
            for i, row in enumerate(rows)
        ],
    )


def _diagnostics_table(
    table: list[list[float]], tolerance: float, converged_level: int | None, decimals: int
) -> DataTable:
    diagonal = [row[-1] for row in table]
    rows: list[list[Any]] = []
    for i, value in enumerate(diagonal):
        if i == 0:
            error_text = ""
            status = "start"
        else:
            error = abs(diagonal[i] - diagonal[i - 1])
            error_text = format_num(error, decimals)
            status = "below tolerance" if error < tolerance else "continue"
        rows.append([i + 1, format_num(value, decimals), error_text, status])
    if converged_level is not None:
        rows[converged_level][3] = "stopped"
    return DataTable(
        title="Diagonal convergence R(i,i)",
        columns=["i", "R(i,i)", "|R(i,i) - R(i-1,i-1)|", "Status"],
        rows=rows,
    )


def _build_steps(
    rows: list[dict[str, float]],
    table: list[list[float]],
    a: float,
    b: float,
    tolerance: float,
    converged_level: int | None,
    value: float,
    *,
    exact: float | None,
    abs_error: float | None,
    decimals: int,
) -> list[Step]:
    setup = Step(
        title="Set up",
        latex=(
            rf"a = {format_num(a, decimals)},\quad b = {format_num(b, decimals)},\quad "
            rf"\text{{tolerance}} = {format_num(tolerance, decimals)}"
            rf"\\[1mm] h_i = \frac{{b - a}}{{2^{{i-1}}}}"
        ),
        note="Level i uses n = 2^(i-1) subintervals; each new level halves h.",
    )
    trapezoid_lines = []
    for i, row in enumerate(rows):
        trapezoid_lines.append(
            rf"R({i + 1},1) = {format_num(row['value'], decimals)}"
            rf"\quad (n = {int(row['n'])},\ h = {format_num(row['h'], decimals)},"
            rf"\ \text{{new evals}} = {int(row['new'])})"
        )
    trapezoids = Step(
        title="Trapezoidal estimates (reusing previous values)",
        latex=r"\\[1mm]".join(trapezoid_lines),
        note=(
            "Each level evaluates only the new odd-indexed nodes, so the number of new "
            "function evaluations is 2, 1, 2, 4, 8, ... as i grows."
        ),
    )
    steps = [setup, trapezoids]

    for i in range(1, len(table)):
        lines = []
        for j in range(1, i + 1):
            lines.append(
                rf"R({i + 1},{j + 1}) = {format_num(table[i][j - 1], decimals)} + "
                rf"\frac{{{format_num(table[i][j - 1], decimals)} - "
                rf"{format_num(table[i - 1][j - 1], decimals)}}}{{4^{{{j}}} - 1}} = "
                rf"{format_num(table[i][j], decimals)}"
            )
        steps.append(
            Step(
                title=f"Extrapolation row i = {i + 1}",
                latex=r"\\[1mm]".join(lines),
                note="Richardson extrapolation removes the leading even-order error terms.",
            )
        )

    if converged_level is not None:
        gap = abs(table[converged_level][-1] - table[converged_level - 1][converged_level - 1])
        convergence_latex = (
            rf"\left|R({converged_level + 1},{converged_level + 1}) - "
            rf"R({converged_level},{converged_level})\right| = "
            rf"{format_num(gap, decimals)} < {format_num(tolerance, decimals)}"
        )
        note = "The diagonal has stabilised: the tolerance is met."
    else:
        convergence_latex = (
            rf"\left|R(i,i) - R(i-1,i-1)\right| \ge "
            rf"{format_num(tolerance, decimals)}\ \text{{for all levels}}"
        )
        note = "The tolerance was not reached within the maximum number of levels."
    steps.append(
        Step(
            title="Stopping test",
            latex=convergence_latex,
            note=note,
        )
    )

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
        steps.append(
            Step(
                title="Error",
                latex=rf"\text{{Absolute error}} = {format_num(abs_error, decimals)}",
                note="Compared with the exact value.",
            )
        )
    steps.append(
        Step(
            title="Result",
            latex=(
                rf"\int_{{{format_num(a, decimals)}}}^{{{format_num(b, decimals)}}}"
                rf" f(x)\,dx \approx {format_num(value, decimals)}"
            ),
            note="Best Romberg estimate.",
        )
    )
    return steps


def _plot(
    table: list[list[float]],
    exact: float | None,
    tolerance: float,
) -> PlotPayload:
    diagonal = [row[-1] for row in table]
    levels = list(range(1, len(diagonal) + 1))
    errors = [abs(diagonal[i] - diagonal[i - 1]) for i in range(1, len(diagonal))]
    error_levels = levels[1:]

    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Diagonal R(i,i)",
            "x": levels,
            "y": diagonal,
            "xaxis": "x",
            "yaxis": "y",
            "line": {"color": "#2563eb"},
        }
    ]
    if exact is not None:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Exact value",
                "x": [levels[0], levels[-1]],
                "y": [exact, exact],
                "xaxis": "x",
                "yaxis": "y",
                "line": {"color": "#16a34a", "dash": "dash"},
            }
        )
    traces.append(
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "|R(i,i) - R(i-1,i-1)|",
            "x": error_levels,
            "y": errors,
            "xaxis": "x2",
            "yaxis": "y2",
            "line": {"color": "#dc2626"},
        }
    )
    if tolerance > 0:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "tolerance",
                "x": [error_levels[0], error_levels[-1]] if error_levels else [1, 1],
                "y": [tolerance, tolerance],
                "xaxis": "x2",
                "yaxis": "y2",
                "line": {"color": "#94a3b8", "dash": "dot"},
            }
        )

    layout: dict[str, Any] = {
        "title": {"text": "Romberg: diagonal convergence and error vs level"},
        "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
        "xaxis": {"title": {"text": "level i"}, "domain": [0.0, 0.44]},
        "yaxis": {"title": {"text": "R(i,i)"}, "domain": [0.0, 1.0]},
        "xaxis2": {"title": {"text": "level i"}, "domain": [0.56, 1.0], "anchor": "y2"},
        "yaxis2": {"title": {"text": "|error|"}, "type": "log", "anchor": "x2"},
        "legend": {"orientation": "h", "y": -0.18},
    }
    return PlotPayload(traces=traces, layout=layout)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate with Romberg integration."""
    del limits
    method_id = "romberg"
    decimals = int(inputs.get("decimal_precision", 6))
    tolerance = float(inputs.get("tolerance", 1e-8))
    max_levels = int(inputs.get("max_levels", 6))

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
                "levels": 0,
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

    rows, table, converged_level = _trapezoid_rows(
        prepared.f, prepared.a, prepared.b, max_levels, tolerance
    )
    value = table[converged_level][-1] if converged_level is not None else table[-1][-1]

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

    if converged_level is None:
        status = SolveStatus.MAX_ITER
        notices.append(
            f"The tolerance {format_num(tolerance, decimals)} was not reached within "
            f"{max_levels} levels; the best value from level {max_levels} is reported."
        )
    else:
        status = SolveStatus.CONVERGED

    tables = [
        _trapezoid_table(rows, decimals),
        _triangular_table(table, decimals),
        _diagnostics_table(table, tolerance, converged_level, decimals),
        summary_table(value, exact, abs_error, rel_error, None, decimals, reference=reference),
    ]

    steps = _build_steps(
        rows,
        table,
        prepared.a,
        prepared.b,
        tolerance,
        converged_level,
        value,
        exact=exact,
        abs_error=abs_error,
        decimals=decimals,
    )

    result: dict[str, Any] = {
        "value": value,
        "a": prepared.a,
        "b": prepared.b,
        "levels": len(table),
        "max_levels": max_levels,
        "tolerance": tolerance,
        "converged": converged_level is not None,
        "exact_value": exact,
        "reference_value": reference,
        "absolute_error": abs_error,
        "relative_error_percent": rel_error,
    }

    return SolveResponse(
        method=method_id,
        status=status,
        result=result,
        steps=steps,
        tables=tables,
        plot=_plot(table, exact, tolerance),
        errors=ErrorInfo(absolute=abs_error, relative_percent=rel_error),
        warnings=notices,
    )
