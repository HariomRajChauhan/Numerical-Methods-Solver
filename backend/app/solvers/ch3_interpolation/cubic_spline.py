"""Cubic spline interpolation.

A cubic spline uses a different cubic on each interval, glued together so that
the curve and its first two derivatives are continuous at the interior knots. The
unknowns are the second derivatives ``M_i`` at the nodes; they satisfy a
tridiagonal system that is solved with the Thomas algorithm. The boundary rows
encode either the natural condition (``M_0 = M_n = 0``) or clamped end slopes.
"""

from __future__ import annotations

from typing import Any

from app.core.models import (
    Chapter,
    DataTable,
    InputField,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SelectOption,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.registry import register
from app.solvers._common import (
    boolean_field,
    failed_response,
    format_num,
    number_field,
    precision_field,
)
from app.solvers.ch3_interpolation._interp import (
    DEFAULT_POINTS,
    data_points_field,
    extrapolation_warnings,
    is_equal_spacing,
    node_table,
    prepare_dataset,
    targets_field,
)
from app.solvers.ch3_interpolation._spline import (
    CLAMPED,
    NATURAL,
    SplineError,
    build_system,
    coefficients_series,
    coefficients_table,
    evaluate,
    evaluation_latex,
    evaluation_table,
    piecewise_latex,
    second_derivatives_latex,
    second_derivatives_series,
    second_derivatives_table,
    spacing_latex,
    spacing_table,
    spline_plot,
    system_latex,
    system_table,
    thomas_latex,
    thomas_table,
)

BOUNDARY_OPTIONS: list[SelectOption] = [
    SelectOption(value=NATURAL, label="Natural: M_0 = M_n = 0"),
    SelectOption(value=CLAMPED, label="Clamped: given f'(x_0) and f'(x_n)"),
]

BOUNDARY_FIELD = InputField(
    key="boundary",
    label="Boundary condition",
    type="select",
    required=True,
    default=NATURAL,
    options=list(BOUNDARY_OPTIONS),
    help="Natural sets the end second derivatives to zero; clamped prescribes the end slopes.",
)

LEFT_DERIVATIVE_FIELD = number_field(
    "left_derivative",
    "Left slope f'(x_0)",
    0.0,
    required=False,
    help="Used only for the clamped spline.",
)

RIGHT_DERIVATIVE_FIELD = number_field(
    "right_derivative",
    "Right slope f'(x_n)",
    0.0,
    required=False,
    help="Used only for the clamped spline.",
)

SPLINE_POINTS: list[list[float]] = [
    [0.0, 0.0],
    [1.0, 0.841471],
    [2.0, 0.909297],
    [3.0, 0.141120],
    [4.0, -0.756802],
]

META = MethodMeta(
    id="cubic_spline",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Cubic Spline Interpolation",
    summary=(
        "Fit smooth piecewise cubics through every point, with continuous first and "
        "second derivatives, using natural or clamped end conditions."
    ),
    theory=(
        "A cubic spline uses a different cubic S_i(x) on each interval [x_i, x_{i+1}], "
        "joined so that the curve and its first two derivatives are continuous at every "
        "interior knot. Writing each piece in terms of the second derivatives\n"
        "  M_i = S''(x_i),\n"
        "the cubics are\n"
        "  S_i(x) = y_i + b_i (x - x_i) + (M_i/2)(x - x_i)^2 + "
        "((M_{i+1}-M_i)/(6 h_i))(x - x_i)^3,\n"
        "with b_i = (y_{i+1}-y_i)/h_i - h_i(2 M_i + M_{i+1})/6 and h_i = x_{i+1} - x_i.\n\n"
        "Requiring S' and S'' to be continuous at the interior knots gives a tridiagonal "
        "system for the unknown second derivatives:\n"
        "  h_{i-1} M_{i-1} + 2(h_{i-1}+h_i) M_i + h_i M_{i+1} = "
        "6( (y_{i+1}-y_i)/h_i - (y_i - y_{i-1})/h_{i-1} ).\n\n"
        "Two more equations fix the ends. The natural spline sets M_0 = M_n = 0; the "
        "clamped spline prescribes the slopes f'(x_0) and f'(x_n) through\n"
        "  2 h_0 M_0 + h_0 M_1 = 6( (y_1-y_0)/h_0 - f'(x_0) )\n"
        "  h_{n-1} M_{n-1} + 2 h_{n-1} M_n = 6( f'(x_n) - (y_n - y_{n-1})/h_{n-1} ).\n\n"
        "The system is tridiagonal, so the Thomas algorithm solves it in O(n) time. The "
        "spline avoids the oscillation of a single high-degree polynomial and works for "
        "both equally and unequally spaced data."
    ),
    formulas=[
        LabeledLatex(
            label="Piecewise cubic",
            latex=r"S_i(x) = a_i + b_i(x-x_i) + c_i(x-x_i)^2 + d_i(x-x_i)^3",
        ),
        LabeledLatex(
            label="Coefficients from M_i",
            latex=r"a_i = y_i,\quad c_i = \frac{M_i}{2},\quad "
            r"d_i = \frac{M_{i+1}-M_i}{6h_i},\quad "
            r"b_i = \frac{y_{i+1}-y_i}{h_i} - \frac{h_i(2M_i + M_{i+1})}{6}",
        ),
        LabeledLatex(
            label="Interior equations",
            latex=r"h_{i-1} M_{i-1} + 2(h_{i-1}+h_i) M_i + h_i M_{i+1} = "
            r"6\!\left(\frac{y_{i+1}-y_i}{h_i} - \frac{y_i-y_{i-1}}{h_{i-1}}\right)",
        ),
        LabeledLatex(
            label="Natural boundary",
            latex=r"M_0 = 0,\qquad M_n = 0",
        ),
        LabeledLatex(
            label="Clamped boundary",
            latex=r"2h_0 M_0 + h_0 M_1 = 6\!\left(\frac{y_1-y_0}{h_0} - f'(x_0)\right),"
            r"\qquad h_{n-1}M_{n-1} + 2h_{n-1}M_n = "
            r"6\!\left(f'(x_n) - \frac{y_n-y_{n-1}}{h_{n-1}}\right)",
        ),
    ],
    pseudocode=(
        "CubicSpline(xs, ys, boundary):\n"
        "    h_i <- xs[i+1] - xs[i]\n"
        "    build the tridiagonal system for M_0..M_n:\n"
        "        interior rows use the continuity equation\n"
        "        natural: M_0 = M_n = 0\n"
        "        clamped: use the given slopes f'(x_0), f'(x_n)\n"
        "    solve the system with the Thomas algorithm\n"
        "    for each interval i:\n"
        "        a <- y_i\n"
        "        c <- M_i / 2\n"
        "        d <- (M_{i+1} - M_i) / (6 h_i)\n"
        "        b <- (y_{i+1} - y_i)/h_i - h_i(2 M_i + M_{i+1})/6\n"
        "    evaluate the active cubic at each target x"
    ),
    input_schema=[
        data_points_field(
            help="At least three points, one per row as 'x, y'; equally or unequally spaced.",
        ),
        BOUNDARY_FIELD,
        LEFT_DERIVATIVE_FIELD,
        RIGHT_DERIVATIVE_FIELD,
        targets_field(
            required=False,
            label="Evaluate at x value(s)",
            help="Optional x values at which to evaluate the spline.",
        ),
        boolean_field(
            "derivatives",
            "Overlay S'(x) and S''(x)",
            False,
            help="Also plot the first and second derivatives of the spline.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Natural spline (parabola)",
            description="Natural cubic spline through y = x^2 + 1; evaluate at x = 1.5.",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "boundary": NATURAL,
                "left_derivative": 0.0,
                "right_derivative": 0.0,
                "targets": [1.5],
                "derivatives": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Unequally spaced data",
            description="Spline through irregularly spaced points; evaluate at x = 2.",
            inputs={
                "points": [[0, 0], [1, 1], [3, 27], [4, 64], [6, 216]],
                "boundary": NATURAL,
                "left_derivative": 0.0,
                "right_derivative": 0.0,
                "targets": [2.0],
                "derivatives": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Clamped spline",
            description="Clamped ends with slopes f'(x_0) and f'(x_n); derivative overlay on.",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "boundary": CLAMPED,
                "left_derivative": 2.0,
                "right_derivative": 0.5,
                "targets": [1.5, 2.5],
                "derivatives": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


def _setup_latex(count: int, boundary: str, equal: bool) -> str:
    spacing = "equally spaced" if equal else "unequally spaced"
    return (
        r"\text{Number of points } n + 1 = " + f"{count}"
        + r"\\[1mm] \text{intervals} = " + f"{count - 1}"
        + r"\\[1mm] \text{x values are " + spacing + "}"
        + r"\\[1mm] \text{boundary: " + boundary + "}"
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Fit the cubic spline and evaluate it at the requested targets."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"], min_points=3)
    xs, ys = dataset.xs, dataset.ys
    count = len(xs)

    boundary = str(inputs.get("boundary") or NATURAL)
    left_derivative = float(inputs.get("left_derivative") or 0.0)
    right_derivative = float(inputs.get("right_derivative") or 0.0)
    raw_targets = inputs.get("targets")
    targets = [float(value) for value in raw_targets] if raw_targets else []
    show_derivatives = bool(inputs.get("derivatives"))

    try:
        spline = build_system(xs, ys, boundary, left_derivative, right_derivative)
    except SplineError as exc:
        return failed_response(META.id, str(exc), warnings=list(dataset.notices))

    warnings = [*dataset.notices, *extrapolation_warnings(targets, xs)]
    outside_warning = extrapolation_warnings(targets, xs)
    if outside_warning:
        warnings.append(
            "Outside the data range the nearest end cubic is extended unchanged, so the "
            "value is an extrapolation."
        )
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=_setup_latex(count, boundary, is_equal_spacing(xs)),
            note="A cubic spline uses one cubic per interval with continuous S, S' and S''.",
        ),
        Step(
            title="Interval widths h_i",
            latex=spacing_latex(spline, decimals),
            note="The step from each node to the next (equal or unequal).",
        ),
        Step(
            title="Tridiagonal system for M_i",
            latex=system_latex(spline, decimals),
            note="The interior rows enforce continuity of S''; the end rows set the boundary condition.",
        ),
        Step(
            title="Thomas algorithm",
            latex=thomas_latex(spline, decimals),
            note="Forward sweep for c'_i, d'_i then back-substitution for the M_i.",
        ),
        Step(
            title="Second derivatives M_i",
            latex=second_derivatives_latex(spline, decimals),
            note="These are the second derivatives at the nodes.",
        ),
        Step(
            title="Piecewise cubics S_i(x)",
            latex=piecewise_latex(spline, decimals),
            note="Each cubic uses the M_i at the ends of its interval.",
        ),
    ]

    values: list[float] = []
    intervals: list[int] = []
    extrapolated: list[bool] = []
    for target in targets:
        value, interval, outside = evaluate(spline, target)
        values.append(value)
        intervals.append(interval)
        extrapolated.append(outside)
        steps.append(
            Step(
                title=f"Evaluate at x = {format_num(target, decimals)}",
                latex=evaluation_latex(spline, target, value, interval, outside, decimals),
                note="The interval that contains the target is used.",
            )
        )

    tables: list[DataTable] = [
        node_table(xs, ys, decimals),
        spacing_table(spline, decimals),
        system_table(spline, decimals),
        thomas_table(spline, decimals),
        second_derivatives_table(spline, decimals),
        coefficients_table(spline, decimals),
    ]
    if targets:
        tables.append(evaluation_table(targets, values, intervals, extrapolated, decimals))

    if values:
        result_note = (
            f"Cubic spline ({boundary}) through {count} points, evaluated at "
            f"{len(values)} target(s)."
        )
        result_latex = r"\\[1mm]".join(
            rf"S({format_num(target, decimals)}) = {format_num(value, decimals)}"
            for target, value in zip(targets, values, strict=True)
        )
    else:
        result_note = f"Cubic spline ({boundary}) through {count} points."
        result_latex = second_derivatives_latex(spline, decimals)

    steps.append(Step(title="Result", latex=result_latex, note=result_note))

    plot = spline_plot(
        spline,
        targets=targets,
        target_values=values,
        show_derivatives=show_derivatives,
        title=f"Cubic spline ({boundary}) interpolation",
    )

    result: dict[str, Any] = {
        "boundary": boundary,
        "intervals": spline.intervals,
        "second_derivatives": second_derivatives_series(spline),
        "coefficients": coefficients_series(spline),
        "targets": targets,
        "values": values,
        "intervals_used": intervals,
    }
    if values:
        result["value"] = values[0]

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=tables,
        plot=plot,
        warnings=warnings,
    )
