"""Newton's divided-difference interpolation for arbitrarily spaced data.

The interpolating polynomial is written in the Newton form
``P(x) = f[x_0] + f[x_0,x_1](x - x_0) + f[x_0,x_1,x_2](x - x_0)(x - x_1) + ...``
where the coefficients are the top diagonal of the divided-difference table. The
data need not be equally spaced, which is what makes this the general-purpose
polynomial interpolant.
"""

from __future__ import annotations

from typing import Any

from app.core.models import (
    Chapter,
    DataTable,
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
    difference_table,
    divided_evaluation_latex,
    divided_leading,
    divided_polynomial_latex,
    expanded_polynomial_latex,
    extrapolation_warnings,
    high_degree_warning,
    interpolating_curve,
    interpolation_plot,
    node_table,
    overlay_plot,
    prepare_dataset,
    require_targets,
    targets_field,
    value_table,
)
from app.solvers.ch3_interpolation._lagrange import (
    comparison_table,
    lagrange_value,
)

META = MethodMeta(
    id="newton_divided_difference",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Newton's Divided Difference Interpolation",
    summary=(
        "Build the interpolating polynomial from divided differences; works for "
        "arbitrarily spaced x values."
    ),
    theory=(
        "Divided differences generalise finite differences to unevenly spaced nodes. "
        "The zeroth divided difference is the value itself, f[x_i] = y_i, and each "
        "higher one is a difference quotient:\n"
        "  f[x_i,...,x_{i+k}] = (f[x_{i+1},...,x_{i+k}] - f[x_i,...,x_{i+k-1}]) / "
        "(x_{i+k} - x_i).\n\n"
        "The interpolating polynomial is then written in the Newton form using the "
        "top diagonal of the table as its coefficients:\n"
        "  P(x) = f[x_0] + f[x_0,x_1](x - x_0) + f[x_0,x_1,x_2](x - x_0)(x - x_1) + "
        "... + f[x_0,...,x_n](x - x_0)...(x - x_{n-1}).\n\n"
        "Unlike the equally-spaced formulas, this works for any set of distinct x "
        "values, and adding one new data point only adds one new term."
    ),
    formulas=[
        LabeledLatex(
            label="Divided difference",
            latex=r"f[x_i,\dots,x_{i+k}] = "
            r"\frac{f[x_{i+1},\dots,x_{i+k}] - f[x_i,\dots,x_{i+k-1}]}{x_{i+k} - x_i}",
        ),
        LabeledLatex(
            label="Newton divided-difference form",
            latex=r"P(x) = f[x_0] + \sum_{k=1}^{n} f[x_0,\dots,x_k] "
            r"\prod_{j=0}^{k-1}(x - x_j)",
        ),
        LabeledLatex(
            label="Error term",
            latex=r"E(x) = f[x_0,\dots,x_n,x]\,(x-x_0)(x-x_1)\cdots(x-x_n)",
        ),
    ],
    pseudocode=(
        "NewtonDivided(xs, ys, x):\n"
        "    for i = 0 to n: table[i][0] <- ys[i]\n"
        "    for k = 1 to n:\n"
        "        for i = 0 to n-k:\n"
        "            table[i][k] <- (table[i+1][k-1] - table[i][k-1]) / (xs[i+k] - xs[i])\n"
        "    coefficients <- table[0][0..n]        # top diagonal\n"
        "    P <- coefficients[0]\n"
        "    product <- 1\n"
        "    for k = 1 to n:\n"
        "        product <- product * (x - xs[k-1])\n"
        "        P <- P + coefficients[k] * product\n"
        "    return P"
    ),
    input_schema=[
        data_points_field(
            help="One point per row as 'x, y'; the x values may be unevenly spaced.",
        ),
        targets_field(),
        boolean_field(
            "expand_polynomial",
            "Expand the polynomial (SymPy)",
            False,
            help="Also show the polynomial multiplied out into powers of x.",
        ),
        boolean_field(
            "compare",
            "Compare with Lagrange",
            False,
            help="Overlay the Lagrange curve and show that both methods agree.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Parabola y = x^2 + 1",
            description="Divided-difference interpolation at x = 2.5 gives 7.25.",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "targets": [2.5],
                "expand_polynomial": False,
                "compare": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Unevenly spaced cubic",
            description="Points x = 0, 1, 3, 4 of y = x^3; interpolate at x = 2.",
            inputs={
                "points": [[0, 0], [1, 1], [3, 27], [4, 64]],
                "targets": [2.0],
                "expand_polynomial": True,
                "compare": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


def _coefficients_latex(coefficients: list[float], decimals: int) -> str:
    parts = [rf"f[x_0] = {format_num(float(coefficients[0]), decimals)}"]
    for k in range(1, len(coefficients)):
        nodes = ", ".join(f"x_{j}" for j in range(k + 1))
        parts.append(rf"f[{nodes}] = {format_num(float(coefficients[k]), decimals)}")
    return r",\quad ".join(parts)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Interpolate at the requested targets with the divided-difference form."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    targets = require_targets(inputs.get("targets"))
    count = len(xs)

    coefficients = divided_leading(xs, ys)
    expand = bool(inputs.get("expand_polynomial"))
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
                + r"\\[1mm] x_0 = " + format_num(float(xs[0]), decimals)
            ),
            note="Divided differences do not require equally spaced nodes.",
        ),
        Step(
            title="Divided differences (top diagonal)",
            latex=_coefficients_latex(coefficients, decimals),
            note="These leading divided differences are the coefficients of the Newton form.",
        ),
        Step(
            title="Newton's divided-difference formula",
            latex=divided_polynomial_latex(coefficients, xs, decimals),
            note="Each bracket (x - x_j) uses one more data point.",
        ),
    ]

    if expand:
        steps.append(
            Step(
                title="Expanded polynomial (SymPy)",
                latex=expanded_polynomial_latex(xs, ys, decimals),
                note="Multiplying the Newton form out gives the same polynomial in powers of x.",
            )
        )

    values: list[float] = []
    for index, target in enumerate(targets):
        latex, value = divided_evaluation_latex(
            coefficients=coefficients,
            xs=xs,
            target=target,
            decimals=decimals,
        )
        values.append(value)
        note = "Substitute the target into every bracket and add the terms."
        if index > 0:
            note = "Same formula, next target."
        steps.append(Step(title=f"Evaluate at x = {format_num(target, decimals)}", latex=latex, note=note))

    tables: list[DataTable] = [
        node_table(xs, ys, decimals),
        difference_table(xs, ys, "divided", decimals),
        value_table(targets, values, decimals),
    ]

    if compare:
        lagrange_values = [lagrange_value(xs, ys, float(target)) for target in targets]
        largest = max(
            (abs(newton - lagrange) for newton, lagrange in zip(values, lagrange_values, strict=True)),
            default=0.0,
        )
        steps.append(
            Step(
                title="Compare with Lagrange",
                latex=rf"\max\left|P_{{Newton}} - P_{{Lagrange}}\right| = {format_num(largest, decimals)}",
                note="Both methods build the same unique interpolating polynomial, so the values agree.",
            )
        )
        tables.insert(2, comparison_table(targets, values, lagrange_values, decimals))

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
            title="Newton divided difference vs Lagrange",
        )
    else:
        plot = interpolation_plot(
            xs=xs,
            ys=ys,
            curve=curve,
            targets=targets,
            target_values=values,
            title="Newton divided difference interpolation",
        )

    result: dict[str, Any] = {
        "value": values[0],
        "values": values,
        "targets": targets,
        "degree": count - 1,
        "divided_differences": coefficients,
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
