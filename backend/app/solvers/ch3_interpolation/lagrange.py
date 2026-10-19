"""Lagrange interpolation for arbitrarily spaced data.

The unique polynomial of degree at most n through n+1 points is written as a
weighted sum of Lagrange basis polynomials,
``P(x) = sum_i y_i L_i(x)`` with ``L_i(x) = prod_{j != i} (x - x_j)/(x_i - x_j)``.
Each basis polynomial is 1 at its own node and 0 at every other node, so the
weights read straight off the data.
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
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.registry import register
from app.solvers._common import boolean_field, format_num, precision_field
from app.solvers.ch3_interpolation._interp import (
    DEFAULT_POINTS,
    data_points_field,
    divided_leading,
    extrapolation_warnings,
    high_degree_warning,
    interpolating_curve,
    node_table,
    overlay_plot,
    prepare_dataset,
    require_targets,
    targets_field,
    value_table,
)
from app.solvers.ch3_interpolation._lagrange import (
    comparison_table,
    lagrange_basis_latex,
    lagrange_basis_plot,
    lagrange_substitution_latex,
    runge_demo,
)

RUNGE_NODES_FIELD = InputField(
    key="runge_nodes",
    label="Runge demo nodes (4-16)",
    type="integer",
    required=False,
    default=11,
    min=4,
    max=16,
    help="Number of nodes used by the equispaced / Chebyshev comparison.",
)

META = MethodMeta(
    id="lagrange",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Lagrange Interpolation",
    summary=(
        "Fit the unique degree-n polynomial through n+1 points as a sum of "
        "basis polynomials; works for arbitrary spacing."
    ),
    theory=(
        "Lagrange interpolation writes the unique polynomial of degree at most n "
        "through n+1 points as a weighted sum of basis polynomials. The i-th basis "
        "polynomial is 1 at its own node and 0 at all the others:\n"
        "  L_i(x) = product over j != i of (x - x_j) / (x_i - x_j).\n\n"
        "Because L_i(x_j) equals 1 when i = j and 0 otherwise, evaluating the sum "
        "P(x) = sum_i y_i L_i(x) at any node reproduces its tabulated value exactly. "
        "No equal spacing is assumed. The price is that adding a new data point "
        "changes every basis polynomial, so the whole table must be rebuilt."
    ),
    formulas=[
        LabeledLatex(
            label="Lagrange basis polynomial",
            latex=r"L_i(x) = \prod_{\substack{j=0 \\ j \neq i}}^{n} "
            r"\frac{x - x_j}{x_i - x_j}",
        ),
        LabeledLatex(
            label="Lagrange interpolating polynomial",
            latex=r"P(x) = \sum_{i=0}^{n} y_i\,L_i(x)",
        ),
        LabeledLatex(
            label="Basis property",
            latex=r"L_i(x_j) = \delta_{ij} = \begin{cases} 1 & i = j \\ 0 & i \neq j \end{cases}",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E(x) = \frac{f^{(n+1)}(\xi)}{(n+1)!}(x-x_0)(x-x_1)\cdots(x-x_n)",
        ),
    ],
    pseudocode=(
        "Lagrange(xs, ys, x):\n"
        "    P <- 0\n"
        "    for i = 0 to n:\n"
        "        L <- 1\n"
        "        for j = 0 to n:\n"
        "            if j != i: L <- L * (x - xs[j]) / (xs[i] - xs[j])\n"
        "        P <- P + ys[i] * L\n"
        "    return P"
    ),
    input_schema=[
        data_points_field(
            help="One point per row as 'x, y'; the x values may be unevenly spaced.",
        ),
        targets_field(
            required=False,
            help="One or more x values to interpolate at (not needed for the Runge demo).",
        ),
        boolean_field(
            "compare",
            "Compare with Newton divided difference",
            False,
            help="Overlay both interpolating curves and show that the values agree.",
        ),
        boolean_field(
            "runge_demo",
            "Runge phenomenon demo",
            False,
            help="Ignore the data and compare equispaced and Chebyshev nodes on [-1, 1].",
        ),
        RUNGE_NODES_FIELD,
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Parabola y = x^2 + 1",
            description="Lagrange interpolation at x = 2.5 gives 7.25.",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "targets": [2.5],
                "compare": False,
                "runge_demo": False,
                "runge_nodes": 11,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Unevenly spaced cubic",
            description="Points x = 0, 1, 3, 4 of y = x^3; compare with Newton DD at x = 2.",
            inputs={
                "points": [[0, 0], [1, 1], [3, 27], [4, 64]],
                "targets": [2.0],
                "compare": True,
                "runge_demo": False,
                "runge_nodes": 11,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Runge phenomenon demo",
            description="Equispaced vs Chebyshev nodes for 1/(1+25x^2) on [-1, 1].",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "targets": [0.5],
                "compare": False,
                "runge_demo": True,
                "runge_nodes": 11,
                "decimal_precision": 6,
            },
        ),
    ],
)


def _newton_value(xs: np.ndarray, ys: np.ndarray, target: float) -> float:
    """Evaluate the Newton divided-difference form (for the compare view)."""
    coefficients = divided_leading(xs, ys)
    total = float(coefficients[0])
    product = 1.0
    for k in range(1, len(coefficients)):
        product *= target - float(xs[k - 1])
        total += float(coefficients[k]) * product
    return total


def _solve_runge(inputs: dict[str, Any], decimals: int) -> SolveResponse:
    count = int(inputs.get("runge_nodes") or 11)
    plot, table, result = runge_demo(count, decimals)
    steps = [
        Step(
            title="Setup",
            latex=(
                r"f(x) = \frac{1}{1 + 25x^2}"
                + r"\\[1mm] x \in [-1, 1]"
                + r"\\[1mm] n = " + f"{count}"
            ),
            note="The classic Runge function is smooth, yet its equispaced interpolant oscillates.",
        ),
        Step(
            title="Equispaced vs Chebyshev nodes",
            latex=(
                r"\text{equispaced: } x_k = -1 + \frac{2k}{n-1}"
                + r"\\[1mm] \text{Chebyshev: } x_k = -\cos\frac{k\pi}{n-1}"
            ),
            note="Clustering the nodes near the ends (Chebyshev) removes the oscillations.",
        ),
        Step(
            title="Result",
            latex=(
                r"\max|E_{equi}| = " + format_num(result["max_error_equispaced"], decimals)
                + r"\\[1mm] \max|E_{cheb}| = " + format_num(result["max_error_chebyshev"], decimals)
            ),
            note="Maximum error of each interpolant against the true function on [-1, 1].",
        ),
    ]
    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=[table],
        plot=plot,
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Interpolate at the requested targets, or show the Runge demo."""
    decimals = int(inputs["decimal_precision"])
    if bool(inputs.get("runge_demo")):
        return _solve_runge(inputs, decimals)

    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    targets = require_targets(inputs.get("targets"))
    count = len(xs)
    compare = bool(inputs.get("compare"))

    warnings = [
        *dataset.notices,
        *extrapolation_warnings(targets, xs),
        *high_degree_warning(count),
    ]

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"\text{Number of points } n = " + f"{count}"
                + r"\\[1mm] \text{degree of polynomial} = " + f"{count - 1}"
            ),
            note="Lagrange interpolation places no restriction on the spacing of the nodes.",
        ),
        Step(
            title="Lagrange basis polynomials",
            latex=lagrange_basis_latex(xs, decimals),
            note="Each L_i is 1 at x_i and 0 at every other node.",
        ),
    ]

    values: list[float] = []
    for index, target in enumerate(targets):
        latex, value = lagrange_substitution_latex(xs, ys, target, decimals)
        values.append(value)
        note = "Substituted numerators, denominators and the weighted sum."
        if index > 0:
            note = "Same basis polynomials, next target."
        steps.append(Step(title=f"Evaluate at x = {format_num(target, decimals)}", latex=latex, note=note))

    tables: list[DataTable] = [
        node_table(xs, ys, decimals),
        value_table(targets, values, decimals),
    ]

    if compare:
        newton_values = [_newton_value(xs, ys, float(target)) for target in targets]
        largest = max(
            (abs(newton - lagrange) for newton, lagrange in zip(newton_values, values, strict=True)),
            default=0.0,
        )
        steps.append(
            Step(
                title="Compare with Newton divided difference",
                latex=rf"\max\left|P_{{Lagrange}} - P_{{Newton}}\right| = {format_num(largest, decimals)}",
                note="The interpolating polynomial is unique, so both methods must agree.",
            )
        )
        tables.insert(1, comparison_table(targets, newton_values, values, decimals))

    steps.append(
        Step(
            title="Result",
            latex=(
                r"P(" + format_num(targets[0], decimals) + r") = "
                + format_num(values[0], decimals)
            ),
            note=f"Interpolated with {count} points (degree {count - 1} polynomial).",
        )
    )

    curve = interpolating_curve(xs, ys, targets=targets)
    if compare:
        plot = overlay_plot(
            xs=xs,
            ys=ys,
            curves=[
                ("Newton divided difference", curve),
                ("Lagrange", curve),
            ],
            targets=targets,
            target_values=values,
            title="Lagrange vs Newton divided difference",
        )
    else:
        plot = lagrange_basis_plot(xs, decimals=decimals, title="Lagrange basis polynomials")

    result: dict[str, Any] = {
        "value": values[0],
        "values": values,
        "targets": targets,
        "degree": count - 1,
        "nodes": count,
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
