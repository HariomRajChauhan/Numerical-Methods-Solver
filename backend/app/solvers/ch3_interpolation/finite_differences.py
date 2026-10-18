"""Finite difference operators and their tables.

This method builds the forward, backward, central or divided difference table of
a dataset and shows the diagonal of differences that feeds the corresponding
interpolation formula.
"""

from __future__ import annotations

from typing import Any

import numpy as np

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
from app.solvers._common import format_num, precision_field
from app.solvers.ch3_interpolation._interp import (
    DEFAULT_POINTS,
    backward_leading,
    central_leading,
    common_step,
    data_points_field,
    difference_table,
    divided_leading,
    forward_leading,
    interpolating_curve,
    interpolation_plot,
    is_equal_spacing,
    node_table,
    prepare_dataset,
    spacing_note,
    step_sizes,
)

OPERATOR_OPTIONS: list[SelectOption] = [
    SelectOption(value="forward", label="Forward differences (Delta y)"),
    SelectOption(value="backward", label="Backward differences (nabla y)"),
    SelectOption(value="central", label="Central differences (delta y)"),
    SelectOption(value="divided", label="Divided differences"),
]

META = MethodMeta(
    id="finite_differences",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Finite Difference Operators",
    summary=(
        "Forward, backward, central and divided difference tables and the diagonal "
        "of differences each interpolation formula uses."
    ),
    theory=(
        "A finite difference is the change in y between neighbouring table entries "
        "and plays the role of a derivative on discrete data.\n\n"
        "Forward differences step to the right, Delta y_i = y_{i+1} - y_i; backward "
        "differences step to the left, nabla y_i = y_i - y_{i-1}; central "
        "differences straddle a point, delta y_{i+1/2} = y_{i+1} - y_i. Repeating "
        "any operator gives higher-order differences, and the results are laid out "
        "in a triangular difference table.\n\n"
        "When the nodes are equally spaced, simple relations hold between the "
        "operators, e.g. nabla y_i = Delta y_{i-1} and delta^2 y_i = Delta^2 y_{i-1}. "
        "The leading (diagonal) differences are exactly the coefficients used by "
        "the Gregory-Newton interpolation formulas, which is why the table is the "
        "starting point for forward and backward interpolation.\n\n"
        "Divided differences generalise the idea to unevenly spaced nodes: "
        "f[x_i, x_{i+1}] = (y_{i+1} - y_i) / (x_{i+1} - x_i), and the table is again "
        "triangular. They build Newton's divided-difference polynomial."
    ),
    formulas=[
        LabeledLatex(label="Forward difference", latex=r"\Delta y_i = y_{i+1} - y_i"),
        LabeledLatex(label="Backward difference", latex=r"\nabla y_i = y_i - y_{i-1}"),
        LabeledLatex(
            label="Central difference",
            latex=r"\delta y_{i+1/2} = y_{i+1} - y_i",
        ),
        LabeledLatex(
            label="Divided difference",
            latex=r"f[x_i, x_{i+1}] = \frac{y_{i+1} - y_i}{x_{i+1} - x_i}",
        ),
        LabeledLatex(
            label="Higher differences",
            latex=r"\Delta^k y_i = \Delta^{k-1} y_{i+1} - \Delta^{k-1} y_i",
        ),
    ],
    pseudocode=(
        "DifferenceTable(xs, ys, operator):\n"
        "    if operator == forward:\n"
        "        D[i][0] <- y[i]; D[i][k] <- D[i+1][k-1] - D[i][k-1]\n"
        "    elif operator == backward:\n"
        "        D[i][0] <- y[i]; D[i][k] <- D[i][k-1] - D[i-1][k-1]\n"
        "    elif operator == central:\n"
        "        build successive central differences level by level\n"
        "    else:  # divided\n"
        "        D[i][0] <- y[i]; D[i][k] <- (D[i+1][k-1] - D[i][k-1]) / (x[i+k] - x[i])\n"
        "    return D and its leading diagonal"
    ),
    input_schema=[
        data_points_field(),
        InputField(
            key="operator",
            label="Difference operator",
            type="select",
            required=True,
            default="forward",
            options=list(OPERATOR_OPTIONS),
            help="Which difference table to build and highlight.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Forward differences of y = x^2 + 1",
            description="Top diagonal 1, 1, 2, 0 feeds Newton's forward formula.",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "operator": "forward",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Divided differences of uneven data",
            description="f[x0..xk] for x = 0, 1, 3 with y = 1, 2, 10.",
            inputs={
                "points": [[0, 1], [1, 2], [3, 10]],
                "operator": "divided",
                "decimal_precision": 6,
            },
        ),
    ],
)


def _definitions_latex(kind: str) -> str:
    if kind == "forward":
        return r"\Delta y_i = y_{i+1} - y_i,\qquad \Delta^k y_i = \Delta^{k-1} y_{i+1} - \Delta^{k-1} y_i"
    if kind == "backward":
        return r"\nabla y_i = y_i - y_{i-1},\qquad \nabla^k y_i = \nabla^{k-1} y_i - \nabla^{k-1} y_{i-1}"
    if kind == "divided":
        return (
            r"f[x_i, x_{i+1}] = \frac{y_{i+1} - y_i}{x_{i+1} - x_i},\qquad "
            r"f[x_i,\dots,x_{i+k}] = \frac{f[x_{i+1},\dots,x_{i+k}] - f[x_i,\dots,x_{i+k-1}]}{x_{i+k} - x_i}"
        )
    return r"\delta y_{i+1/2} = y_{i+1} - y_i,\qquad \delta^k y = \delta^{k-1} y_{i+1} - \delta^{k-1} y_i"


def _leading_latex(kind: str, coefficients: list[float], decimals: int) -> str:
    parts: list[str] = []
    for k in range(len(coefficients)):
        value = format_num(coefficients[k], decimals)
        if kind == "forward":
            power = "" if k == 0 else f"^{k}"
            parts.append(rf"y_0 = {value}" if k == 0 else rf"\Delta{power} y_0 = {value}")
        elif kind == "backward":
            power = "" if k == 0 else f"^{k}"
            parts.append(rf"y_n = {value}" if k == 0 else rf"\nabla{power} y_n = {value}")
        elif kind == "divided":
            label = "f[x_0]" if k == 0 else f"f[x_0,\\dots,x_{{{k}}}]"
            parts.append(rf"{label} = {value}")
        else:
            label = "y" if k == 0 else rf"\delta^{k} y"
            parts.append(rf"{label} = {value}")
    return r",\quad ".join(parts)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Build the requested difference table and its leading diagonal."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    kind = str(inputs["operator"])
    count = len(xs)

    warnings = list(dataset.notices)
    if kind != "divided":
        warnings.extend(spacing_note(xs))

    coefficients = backward_leading(ys) if kind == "backward" else _leading(kind, xs, ys)

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"\text{Number of points } n = " + f"{count}"
                + r"\\[1mm] \text{Operator: } " + _operator_name(kind)
                + r"\\[1mm] " + _definitions_latex(kind)
            ),
            note="Difference operators replace derivatives on tabulated data.",
        ),
        Step(
            title="Leading differences",
            latex=_leading_latex(kind, coefficients, decimals),
            note="These diagonal entries are the coefficients used by the matching formula.",
        ),
    ]

    step = common_step(xs)
    equal = is_equal_spacing(xs)
    tables: list[DataTable] = [
        node_table(xs, ys, decimals),
        difference_table(xs, ys, kind, decimals),
    ]
    curve = interpolating_curve(xs, ys)
    plot = interpolation_plot(
        xs=xs,
        ys=ys,
        curve=curve,
        title=f"{_operator_name(kind)} difference table",
    )

    result: dict[str, Any] = {
        "operator": kind,
        "equal_spacing": equal,
        "step": step if equal else None,
        "steps": step_sizes(xs).tolist(),
        "degree": count - 1,
        "leading_differences": coefficients,
    }

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=tables,
        plot=plot,
        warnings=warnings,
    )


def _leading(kind: str, xs: np.ndarray, ys: np.ndarray) -> list[float]:
    if kind == "forward":
        return forward_leading(ys)
    if kind == "divided":
        return divided_leading(xs, ys)
    return central_leading(ys)


def _operator_name(kind: str) -> str:
    return {
        "forward": "Forward (Delta)",
        "backward": "Backward (nabla)",
        "central": "Central (delta)",
        "divided": "Divided",
    }.get(kind, kind)
