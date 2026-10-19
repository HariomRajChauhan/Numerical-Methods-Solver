"""Local maxima and minima of equally spaced tabulated data.

The unique interpolating polynomial is built in ``p = (x - x_0) / h``, its slope
``dy/dp`` is set to zero and the real roots inside the data range are classified
as maxima or minima from the sign of the second derivative.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.core.models import (
    Chapter,
    DataTable,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    PlotPayload,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.registry import register
from app.solvers._common import format_num, marker_trace, points_trace, precision_field
from app.solvers.ch3_interpolation._interp import (
    common_step,
    data_points_field,
    difference_table,
    high_degree_warning,
    interpolating_curve,
    is_equal_spacing,
    node_table,
    prepare_dataset,
    spacing_failure,
)
from app.solvers.ch4_diff_integration._extrema import (
    MAXIMUM,
    MINIMUM,
    Extremum,
    find_extrema,
)

EXTREMA_POINTS: list[list[float]] = [
    [0.0, 5.0],
    [1.0, 2.0],
    [2.0, 1.0],
    [3.0, 2.0],
    [4.0, 5.0],
]

_KIND_LABEL = {
    MAXIMUM: "Maximum",
    MINIMUM: "Minimum",
    "inconclusive": "Inconclusive",
}

META = MethodMeta(
    id="local_extrema",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Local Maxima and Minima",
    summary=(
        "Fit the interpolating polynomial to equally spaced data, solve dy/dp = 0 "
        "and classify each turning point with the second derivative."
    ),
    theory=(
        "For equally spaced data the interpolating polynomial can be written in the "
        "variable p = (x - x_0)/h. Because x is an affine function of p, the "
        "stationary points of the data are exactly the roots of dy/dp = 0.\n\n"
        "Writing the Newton form\n"
        "  P(p) = y_0 + p Delta y_0 + p(p-1)/2! Delta^2 y_0 + ...\n"
        "and differentiating term by term gives a polynomial whose roots p* give the "
        "candidate turning points x* = x_0 + p* h.\n\n"
        "Each root is classified with the second derivative: d^2y/dp^2 < 0 is a local "
        "maximum, > 0 is a local minimum and ~ 0 is inconclusive (a possible "
        "inflection or a higher-order flat point). Only roots inside the data range "
        "0 <= p <= n - 1 are reported, since outside it the polynomial is an "
        "extrapolation."
    ),
    formulas=[
        LabeledLatex(label="Parameter", latex=r"p = \frac{x - x_0}{h}"),
        LabeledLatex(
            label="Newton forward form",
            latex=r"P(p) = y_0 + p\,\Delta y_0 + \frac{p(p-1)}{2!}\Delta^2 y_0 + \cdots",
        ),
        LabeledLatex(label="Stationary points", latex=r"\frac{dy}{dp} = 0 \;\Rightarrow\; p = p^*"),
        LabeledLatex(
            label="Classification",
            latex=r"P''(p^*) < 0 \Rightarrow \text{max},\quad "
            r"P''(p^*) > 0 \Rightarrow \text{min}",
        ),
    ],
    pseudocode=(
        "LocalExtrema(xs, ys):\n"
        "    require equal spacing; h <- x[1] - x[0]\n"
        "    build the Newton forward interpolant P(p), p <- (x - x[0]) / h\n"
        "    solve P'(p) = 0 for the real roots p*\n"
        "    keep roots with 0 <= p* <= n - 1\n"
        "    classify each by the sign of P''(p*): max, min or inconclusive\n"
        "    report x* <- x[0] + p* h and y* <- P(p*)"
    ),
    input_schema=[
        data_points_field(
            default=EXTREMA_POINTS,
            help="Equally spaced x values; one point per row as 'x, y'.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Single minimum",
            description="x = 0..4, y = 5, 2, 1, 2, 5; minimum at x = 2 with y = 1.",
            inputs={
                "points": [list(point) for point in EXTREMA_POINTS],
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Maximum and minimum",
            description="A cubic-like set with a peak and a trough inside the range.",
            inputs={
                "points": [[0, 0], [1, 3], [2, 2], [3, 9], [4, 24]],
                "decimal_precision": 6,
            },
        ),
    ],
)


def _poly_latex(coefficients: np.ndarray, variable: str, decimals: int) -> str:
    pieces: list[str] = []
    degree = len(coefficients) - 1
    for index, coefficient in enumerate(coefficients):
        value = float(coefficient)
        if abs(value) < 1e-12:
            continue
        power = degree - index
        magnitude = format_num(abs(value), decimals)
        if power == 0:
            body = magnitude
        elif power == 1:
            body = rf"{magnitude}\,{variable}"
        else:
            body = rf"{magnitude}\,{variable}^{{{power}}}"
        if not pieces:
            pieces.append(body if value >= 0 else f"-{body}")
        else:
            pieces.append((" - " if value < 0 else " + ") + body)
    if not pieces:
        return "0"
    return "".join(pieces)


def _extrema_table(extrema: list[Extremum], decimals: int) -> DataTable:
    rows = [
        [
            format_num(item.p, decimals),
            format_num(item.x, decimals),
            format_num(item.y, decimals),
            format_num(item.second_derivative, decimals),
            _KIND_LABEL[item.kind],
        ]
        for item in extrema
    ]
    return DataTable(
        title="Stationary points",
        columns=["p", "x", "P(x)", "P''(p)", "Type"],
        rows=rows,
    )


def _extrema_plot(xs: np.ndarray, ys: np.ndarray, extrema: list[Extremum]) -> PlotPayload:
    curve = interpolating_curve(xs, ys)
    traces: list[dict[str, Any]] = [points_trace(list(xs), list(ys), "Data points")]
    if curve[0]:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Interpolating polynomial",
                "x": curve[0],
                "y": curve[1],
            }
        )
    for item in extrema:
        color = "#dc2626" if item.kind == MAXIMUM else "#16a34a"
        symbol = "triangle-up" if item.kind == MAXIMUM else "triangle-down"
        traces.append(
            marker_trace(item.x, item.y, _KIND_LABEL[item.kind], color=color, symbol=symbol)
        )
    layout = {
        "title": {"text": "Local maxima and minima"},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "y"}},
    }
    return PlotPayload(traces=traces, layout=layout)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Locate and classify the local extrema of equally spaced data."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"], min_points=3)
    xs, ys = dataset.xs, dataset.ys
    if not is_equal_spacing(xs):
        return spacing_failure(META.id, xs, decimals)

    step = common_step(xs)
    base = float(xs[0])
    extrema, coefficients, slope = find_extrema(xs, ys)

    warnings = [*dataset.notices, *high_degree_warning(len(xs))]
    if not extrema:
        warnings.append(
            "No local maximum or minimum lies inside the data range "
            f"[{xs[0]:g}, {xs[-1]:g}]."
        )

    slope_latex = _poly_latex(slope, "p", decimals) if slope.size else "0"
    polynomial_latex = _poly_latex(coefficients, "p", decimals)

    steps = [
        Step(
            title="Setup",
            latex=(
                rf"\text{{Points }} n = {len(xs)},\quad h = {format_num(step, decimals)}"
                rf"\\[1mm] x_0 = {format_num(base, decimals)},\quad "
                r"p = \frac{x - x_0}{h}"
            ),
            note="Equal spacing turns the data into a polynomial in the single variable p.",
        ),
        Step(
            title="Interpolating polynomial",
            latex=rf"P(p) = {polynomial_latex}",
            note=f"Degree {len(xs) - 1} polynomial through the {len(xs)} points.",
        ),
        Step(
            title="Set the slope to zero",
            latex=rf"\frac{{dy}}{{dp}} = {slope_latex} = 0",
            note="Differentiate P(p) term by term and solve for the stationary points.",
        ),
    ]

    if extrema:
        roots_latex = r",\quad ".join(
            rf"p^* = {format_num(item.p, decimals)} \;\Rightarrow\; "
            rf"x^* = {format_num(item.x, decimals)},\; y^* = {format_num(item.y, decimals)}"
            for item in extrema
        )
        steps.append(
            Step(
                title="Stationary points",
                latex=roots_latex,
                note="Only roots inside 0 <= p <= n - 1 lie within the data range.",
            )
        )
        classify_latex = r"\\[1mm]".join(
            rf"P''({format_num(item.p, decimals)}) = "
            rf"{format_num(item.second_derivative, decimals)} \;\Rightarrow\; "
            rf"{_KIND_LABEL[item.kind]}"
            for item in extrema
        )
        steps.append(
            Step(
                title="Classify with the second derivative",
                latex=classify_latex,
                note="A negative second derivative is a maximum, positive a minimum.",
            )
        )
        result_latex = r"\\[1mm]".join(
            rf"{_KIND_LABEL[item.kind]} \text{{ at }} "
            rf"x = {format_num(item.x, decimals)}:\; y = {format_num(item.y, decimals)}"
            for item in extrema
        )
        steps.append(
            Step(
                title="Result",
                latex=result_latex,
                note=f"{len(extrema)} turning point(s) found inside the data range.",
            )
        )
    else:
        steps.append(
            Step(
                title="Result",
                latex=r"\text{No real root of } \frac{dy}{dp} = 0 "
                r"\text{ lies inside the data range.}",
                note="The data has no local maximum or minimum between the given x values.",
            )
        )

    tables = [
        node_table(xs, ys, decimals),
        difference_table(xs, ys, "forward", decimals),
        _extrema_table(extrema, decimals),
    ]

    result: dict[str, Any] = {
        "count": len(extrema),
        "extrema": [
            {
                "p": item.p,
                "x": item.x,
                "y": item.y,
                "type": item.kind,
                "second_derivative": item.second_derivative,
            }
            for item in extrema
        ],
        "step": step,
        "base_x": base,
        "polynomial": [float(value) for value in coefficients],
        "slope_polynomial": [float(value) for value in slope],
    }
    if extrema and math.isfinite(extrema[0].x):
        result["x"] = extrema[0].x
        result["y"] = extrema[0].y

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=tables,
        plot=_extrema_plot(xs, ys, extrema),
        warnings=warnings,
    )
