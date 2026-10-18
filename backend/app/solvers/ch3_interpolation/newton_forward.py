"""Newton's forward difference interpolation for equally spaced data.

The interpolating polynomial is written in terms of the forward differences on
the top diagonal of the difference table:
``P(x) = y_0 + p Delta y_0 + p(p-1)/2! Delta^2 y_0 + ...`` with
``p = (x - x_0) / h``. It is most accurate near the start of the table.
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
from app.solvers._common import format_num, precision_field
from app.solvers.ch3_interpolation._interp import (
    DEFAULT_POINTS,
    common_step,
    data_points_field,
    difference_table,
    extrapolation_warnings,
    forward_leading,
    forward_region_warning,
    interpolating_curve,
    interpolation_plot,
    is_equal_spacing,
    newton_evaluation_latex,
    newton_polynomial_latex,
    node_table,
    prepare_dataset,
    require_targets,
    spacing_failure,
    targets_field,
    value_table,
)

META = MethodMeta(
    id="newton_forward",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Newton's Forward Difference Interpolation",
    summary=(
        "Interpolate with a constant step using the forward differences on the "
        "top diagonal; best near the start of the table."
    ),
    theory=(
        "For equally spaced nodes x_0, x_1 = x_0 + h, ..., the forward difference "
        "operator is Delta y_i = y_{i+1} - y_i, and higher differences are built "
        "by repeating it: Delta^k y_i = Delta^{k-1} y_{i+1} - Delta^{k-1} y_i.\n\n"
        "Every value is rewritten in terms of a single variable "
        "p = (x - x_0) / h. Because the nodes are x_0 + i h, the binomial "
        "coefficients give the Newton forward (Gregory-Newton) formula:\n"
        "  P(x) = y_0 + p Delta y_0 + p(p-1)/2! Delta^2 y_0 + "
        "p(p-1)(p-2)/3! Delta^3 y_0 + ...\n\n"
        "The coefficients are the top diagonal of the difference table. The formula "
        "is exact for a polynomial of degree at most n, and the truncated error is "
        "smallest when x sits near x_0, so it is the method of choice for the early "
        "part of a table."
    ),
    formulas=[
        LabeledLatex(label="Forward difference", latex=r"\Delta y_i = y_{i+1} - y_i"),
        LabeledLatex(label="Parameter", latex=r"p = \frac{x - x_0}{h}"),
        LabeledLatex(
            label="Newton forward formula",
            latex=r"P(x) = y_0 + p\,\Delta y_0 + \frac{p(p-1)}{2!}\Delta^2 y_0 + "
            r"\frac{p(p-1)(p-2)}{3!}\Delta^3 y_0 + \cdots",
        ),
        LabeledLatex(
            label="Truncation error",
            latex=r"E = \frac{p(p-1)\cdots(p-n)}{(n+1)!}\,h^{n+1} f^{(n+1)}(\xi)",
        ),
    ],
    pseudocode=(
        "NewtonForward(xs, ys, x):\n"
        "    require equal spacing; h <- x[1] - x[0]; p <- (x - x[0]) / h\n"
        "    build the forward differences Delta^k y_0 (top diagonal)\n"
        "    P <- y_0\n"
        "    term <- 1\n"
        "    for k = 1 to n:\n"
        "        term <- term * (p - (k-1)) / k\n"
        "        P <- P + term * Delta^k y_0\n"
        "    return P"
    ),
    input_schema=[
        data_points_field(),
        targets_field(),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Parabola y = x^2 + 1",
            description="Forward interpolation at x = 0.5 gives 1.25.",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "targets": [0.5],
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Squares y = x^2",
            description="Table x = 1..5, y = 1, 4, 9, 16, 25; interpolate at x = 1.5.",
            inputs={
                "points": [[1, 1], [2, 4], [3, 9], [4, 16], [5, 25]],
                "targets": [1.5],
                "decimal_precision": 6,
            },
        ),
    ],
)


def _leading_latex(coefficients: list[float], decimals: int) -> str:
    parts = [rf"y_0 = {format_num(coefficients[0], decimals)}"]
    for k in range(1, len(coefficients)):
        power = "" if k == 1 else f"^{k}"
        parts.append(rf"\Delta{power} y_0 = {format_num(coefficients[k], decimals)}")
    return r",\quad ".join(parts)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Interpolate at the requested targets with Newton's forward formula."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    if not is_equal_spacing(xs):
        return spacing_failure(META.id, xs, decimals)

    targets = require_targets(inputs.get("targets"))
    step = common_step(xs)
    base = float(xs[0])
    coefficients = forward_leading(ys)
    count = len(xs)

    warnings = [*dataset.notices, *extrapolation_warnings(targets, xs)]
    first_p = (targets[0] - base) / step if step else 0.0
    warnings.extend(forward_region_warning(first_p, count))

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"\text{Number of points } n = " + f"{count}"
                + r"\\[1mm] h = " + format_num(step, decimals)
                + r"\\[1mm] x_0 = " + format_num(base, decimals)
                + r"\\[1mm] p = \frac{x - x_0}{h}"
            ),
            note="The nodes are equally spaced, so p is a single variable for the whole table.",
        ),
        Step(
            title="Forward differences (top diagonal)",
            latex=_leading_latex(coefficients, decimals),
            note="These leading differences are the coefficients of the Newton formula.",
        ),
        Step(
            title="Newton forward formula",
            latex=newton_polynomial_latex(coefficients, decimals, backward=False),
            note="Substituting p into this polynomial evaluates the interpolant anywhere.",
        ),
    ]

    values: list[float] = []
    for index, target in enumerate(targets):
        latex, value = newton_evaluation_latex(
            coefficients=coefficients,
            base_x=base,
            step=step,
            target=target,
            decimals=decimals,
            backward=False,
        )
        values.append(value)
        title = f"Evaluate at x = {format_num(target, decimals)}"
        note = "Full substitution of p and the difference coefficients."
        if index > 0:
            note = "Same formula, next target."
        steps.append(Step(title=title, latex=latex, note=note))

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

    tables: list[DataTable] = [
        node_table(xs, ys, decimals),
        difference_table(xs, ys, "forward", decimals),
        value_table(targets, values, decimals),
    ]

    curve = interpolating_curve(xs, ys, targets=targets)
    plot = interpolation_plot(
        xs=xs,
        ys=ys,
        curve=curve,
        targets=targets,
        target_values=values,
        title="Newton forward interpolation",
    )

    result: dict[str, Any] = {
        "value": values[0],
        "values": values,
        "targets": targets,
        "p": [(target - base) / step if step else 0.0 for target in targets],
        "step": step,
        "base_x": base,
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
