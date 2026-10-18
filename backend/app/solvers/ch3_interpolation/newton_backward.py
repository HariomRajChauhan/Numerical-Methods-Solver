"""Newton's backward difference interpolation for equally spaced data.

The interpolating polynomial is written in terms of the backward differences at
the last node: ``P(x) = y_n + p nabla y_n + p(p+1)/2! nabla^2 y_n + ...`` with
``p = (x - x_n) / h``. It is most accurate near the end of the table.
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
    backward_leading,
    backward_region_warning,
    common_step,
    data_points_field,
    difference_table,
    extrapolation_warnings,
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
    id="newton_backward",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Newton's Backward Difference Interpolation",
    summary=(
        "Interpolate with a constant step using the backward differences at the "
        "last node; best near the end of the table."
    ),
    theory=(
        "For equally spaced nodes the backward difference operator is "
        "nabla y_i = y_i - y_{i-1}, with higher differences built by repeating it: "
        "nabla^k y_i = nabla^{k-1} y_i - nabla^{k-1} y_{i-1}.\n\n"
        "Writing p = (x - x_n) / h, the Gregory-Newton backward formula uses the "
        "backward differences at the last node x_n:\n"
        "  P(x) = y_n + p nabla y_n + p(p+1)/2! nabla^2 y_n + "
        "p(p+1)(p+2)/3! nabla^3 y_n + ...\n\n"
        "The coefficients are the bottom diagonal of the difference table. The "
        "formula is exact for a polynomial of degree at most n and its truncation "
        "error is smallest when x is near x_n, so it is used for the later part of "
        "a table (equivalently, p is small near x_n)."
    ),
    formulas=[
        LabeledLatex(label="Backward difference", latex=r"\nabla y_i = y_i - y_{i-1}"),
        LabeledLatex(label="Parameter", latex=r"p = \frac{x - x_n}{h}"),
        LabeledLatex(
            label="Newton backward formula",
            latex=r"P(x) = y_n + p\,\nabla y_n + \frac{p(p+1)}{2!}\nabla^2 y_n + "
            r"\frac{p(p+1)(p+2)}{3!}\nabla^3 y_n + \cdots",
        ),
        LabeledLatex(
            label="Truncation error",
            latex=r"E = \frac{p(p+1)\cdots(p+n)}{(n+1)!}\,h^{n+1} f^{(n+1)}(\xi)",
        ),
    ],
    pseudocode=(
        "NewtonBackward(xs, ys, x):\n"
        "    require equal spacing; h <- x[1] - x[0]; p <- (x - x[n]) / h\n"
        "    build the backward differences nabla^k y_n (bottom diagonal)\n"
        "    P <- y_n\n"
        "    term <- 1\n"
        "    for k = 1 to n:\n"
        "        term <- term * (p + (k-1)) / k\n"
        "        P <- P + term * nabla^k y_n\n"
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
            description="Backward interpolation at x = 2.5 gives 7.25.",
            inputs={
                "points": [list(point) for point in DEFAULT_POINTS],
                "targets": [2.5],
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Squares y = x^2",
            description="Table x = 1..5, y = 1, 4, 9, 16, 25; interpolate at x = 4.5.",
            inputs={
                "points": [[1, 1], [2, 4], [3, 9], [4, 16], [5, 25]],
                "targets": [4.5],
                "decimal_precision": 6,
            },
        ),
    ],
)


def _leading_latex(coefficients: list[float], decimals: int) -> str:
    parts = [rf"y_n = {format_num(coefficients[0], decimals)}"]
    for k in range(1, len(coefficients)):
        power = "" if k == 1 else f"^{k}"
        parts.append(rf"\nabla{power} y_n = {format_num(coefficients[k], decimals)}")
    return r",\quad ".join(parts)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Interpolate at the requested targets with Newton's backward formula."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    if not is_equal_spacing(xs):
        return spacing_failure(META.id, xs, decimals)

    targets = require_targets(inputs.get("targets"))
    step = common_step(xs)
    base = float(xs[-1])
    coefficients = backward_leading(ys)
    count = len(xs)

    warnings = [*dataset.notices, *extrapolation_warnings(targets, xs)]
    first_p = (targets[0] - base) / step if step else 0.0
    warnings.extend(backward_region_warning(first_p, count))

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"\text{Number of points } n = " + f"{count}"
                + r"\\[1mm] h = " + format_num(step, decimals)
                + r"\\[1mm] x_n = " + format_num(base, decimals)
                + r"\\[1mm] p = \frac{x - x_n}{h}"
            ),
            note="The nodes are equally spaced, so p is a single variable for the whole table.",
        ),
        Step(
            title="Backward differences (bottom diagonal)",
            latex=_leading_latex(coefficients, decimals),
            note="These backward differences at x_n are the coefficients of the formula.",
        ),
        Step(
            title="Newton backward formula",
            latex=newton_polynomial_latex(coefficients, decimals, backward=True),
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
            backward=True,
        )
        values.append(value)
        title = f"Evaluate at x = {format_num(target, decimals)}"
        note = "Full substitution of p and the backward difference coefficients."
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
        difference_table(xs, ys, "backward", decimals),
        value_table(targets, values, decimals),
    ]

    curve = interpolating_curve(xs, ys, targets=targets)
    plot = interpolation_plot(
        xs=xs,
        ys=ys,
        curve=curve,
        targets=targets,
        target_values=values,
        title="Newton backward interpolation",
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
