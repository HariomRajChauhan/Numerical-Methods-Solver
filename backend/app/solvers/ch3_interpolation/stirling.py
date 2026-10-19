"""Stirling's central-difference interpolation for equally spaced data.

The interpolating polynomial is written around a central node ``x0`` using the
averaged differences ``mu*delta`` (odd orders) and the even central differences
``delta^2, delta^4, ...``:

    P(x) = y0 + p*(mu*delta y0) + p^2/2! * delta^2 y0
             + p(p^2-1)/3! * (mu*delta^3 y0) + ...

with ``p = (x - x0)/h``. It is most accurate when ``|p| <= 0.25``.
"""

from __future__ import annotations

from typing import Any

from app.core.models import (
    Chapter,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.registry import register
from app.solvers._common import failed_response, format_num, precision_field
from app.solvers.ch3_interpolation._central import (
    center_field,
    order_field,
    side_points,
    stirling_center,
    stirling_differences_latex,
    stirling_evaluate,
    stirling_formula_latex,
    stirling_region_warning,
    target_evaluation_latex,
)
from app.solvers.ch3_interpolation._interp import (
    central_differences,
    central_table,
    common_step,
    data_points_field,
    extrapolation_warnings,
    interpolating_curve,
    interpolation_plot,
    is_equal_spacing,
    node_table,
    prepare_dataset,
    require_targets,
    spacing_failure,
    targets_field,
    value_table,
)

META = MethodMeta(
    id="stirling",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Stirling's Interpolation",
    summary=(
        "Central-difference interpolation that averages forward and backward "
        "differences around a chosen middle point; best for |p| <= 0.25."
    ),
    theory=(
        "Stirling's formula is a central-difference interpolation built around a "
        "node x_0 chosen near the target. With the constant step h and "
        "p = (x - x_0)/h it mixes the forward and backward differences at the "
        "centre by averaging the odd differences:\n"
        "  mu*delta y_0 = (delta y_{1/2} + delta y_{-1/2}) / 2\n\n"
        "The even differences delta^2 y_0, delta^4 y_0 are taken directly at the "
        "centre, giving\n"
        "  P(x) = y_0 + p (mu*delta y_0) + p^2/2! delta^2 y_0 "
        "+ p(p^2-1)/3! (mu*delta^3 y_0) + ...\n\n"
        "Because the centre is fixed, the formula is the most symmetric of the "
        "equal-spacing forms and is most accurate when the target lies close to "
        "x_0, roughly |p| <= 0.25. Only points that sit on both sides of the "
        "centre contribute; when the table is short on one side the highest "
        "available symmetric order is used and stated in the working."
    ),
    formulas=[
        LabeledLatex(label="Parameter", latex=r"p = \frac{x - x_0}{h}"),
        LabeledLatex(
            label="Averaged odd difference",
            latex=r"\mu\delta y_0 = \frac{\delta y_{1/2} + \delta y_{-1/2}}{2}",
        ),
        LabeledLatex(
            label="Stirling's formula",
            latex=r"P(x) = y_0 + p\,\mu\delta y_0 + \frac{p^2}{2!}\delta^2 y_0"
            r" + \frac{p(p^2-1)}{3!}\mu\delta^3 y_0"
            r" + \frac{p^2(p^2-1)}{4!}\delta^4 y_0 + \cdots",
        ),
    ],
    pseudocode=(
        "Stirling(xs, ys, x):\n"
        "    require equal spacing; h <- x[1] - x[0]\n"
        "    pick the central node x0 (nearest the target)\n"
        "    build the central-difference table around x0\n"
        "    p <- (x - x0) / h\n"
        "    P <- y0\n"
        "    for k = 1, 2, 3, ... up to the available order:\n"
        "        if k is odd:  add coefficient * ( (delta^k y at +/- 1/2) / 2 )\n"
        "        else:         add coefficient * delta^k y0\n"
        "    return P"
    ),
    input_schema=[
        data_points_field(),
        targets_field(),
        center_field(),
        order_field(),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Parabola y = x^2 + 1",
            description=(
                "Table x = 0..4, y = 1, 2, 5, 10, 17; centre near x = 2 gives "
                "P(2.1) = 5.41."
            ),
            inputs={
                "points": [[0, 1], [1, 2], [2, 5], [3, 10], [4, 17]],
                "targets": [2.1],
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Cubic y = x^3",
            description="Table x = 0..4, y = 0, 1, 8, 27, 64; interpolate at x = 2.2.",
            inputs={
                "points": [[0, 0], [1, 1], [2, 8], [3, 27], [4, 64]],
                "targets": [2.2],
                "decimal_precision": 6,
            },
        ),
    ],
)


def _side_note(side: int, maximum: int, used: int) -> str:
    return (
        f"The centre has {side} point(s) on its shorter side, so orders up to "
        f"{maximum} are available; order {used} is used."
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Interpolate at the requested targets with Stirling's central formula."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    if not is_equal_spacing(xs):
        return spacing_failure(META.id, xs, decimals)

    targets = require_targets(inputs.get("targets"))
    step = common_step(xs)
    size = len(xs)
    center = stirling_center(xs, inputs.get("center"), targets[0])
    side = side_points(center, size, bessel=False)
    if side < 1:
        return failed_response(
            META.id,
            "Stirling's formula needs data points on both sides of the central point, "
            "but the chosen centre is an end point of the table. Choose an interior "
            "central point, or use Newton's or Bessel's formula.",
        )

    levels = central_differences(ys)
    order = inputs.get("order")
    base = float(xs[center])

    warnings = [*dataset.notices, *extrapolation_warnings(targets, xs)]
    first_p = (targets[0] - base) / step if step else 0.0
    warnings.extend(stirling_region_warning(first_p))

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"\text{Number of points } n = " + f"{size}"
                + r"\\[1mm] h = " + format_num(step, decimals)
                + r"\\[1mm] x_0 = " + format_num(base, decimals)
                + r"\\[1mm] p = \frac{x - x_0}{h}"
            ),
            note="The central node x0 is the working origin; p is the single variable.",
        ),
    ]

    values: list[float] = []
    marks: set[tuple[int, int]] = set()
    order_used = 0
    max_order = 2 * side
    for target in targets:
        p = (target - base) / step if step else 0.0
        evaluation = stirling_evaluate(levels, ys, center, p, order, decimals)
        values.append(evaluation.value)
        marks = evaluation.marks
        order_used = evaluation.order_used
        max_order = evaluation.max_order
        steps.append(
            Step(
                title=f"Evaluation at x = {format_num(target, decimals)}",
                latex=target_evaluation_latex(
                    target=target,
                    base=base,
                    step=step,
                    p=p,
                    terms_latex=evaluation.terms_latex,
                    term_values=evaluation.term_values,
                    decimals=decimals,
                ),
                note=(
                    "Substitute p into the Stirling series; each term already shows "
                    "its numeric coefficient and difference."
                ),
            )
        )

    steps.insert(
        1,
        Step(
            title="Central differences used",
            latex=stirling_differences_latex(levels, center, order_used, decimals),
            note="These are the averaged odd and the even central differences at x0.",
        ),
    )
    steps.insert(
        2,
        Step(
            title="Stirling's formula",
            latex=stirling_formula_latex(order_used),
            note="Only the terms the table can support around the chosen centre are kept.",
        ),
    )
    steps.insert(
        3,
        Step(
            title="Difference order used",
            latex=rf"\text{{order}} = {order_used}\quad(\text{{maximum available }} {max_order})",
            note=_side_note(side, max_order, order_used),
        ),
    )

    steps.append(
        Step(
            title="Result",
            latex=(
                r"P(" + format_num(targets[0], decimals) + r") = "
                + format_num(values[0], decimals)
            ),
            note=(
                f"Central node x_0 = {format_num(base, decimals)} using central "
                f"differences up to order {order_used}."
            ),
        )
    )

    tables = [
        node_table(xs, ys, decimals),
        central_table(xs, ys, decimals, marks),
        value_table(targets, values, decimals),
    ]

    curve = interpolating_curve(xs, ys, targets=targets)
    plot = interpolation_plot(
        xs=xs,
        ys=ys,
        curve=curve,
        targets=targets,
        target_values=values,
        title="Stirling interpolation",
    )

    result: dict[str, Any] = {
        "value": values[0],
        "values": values,
        "targets": targets,
        "p": [(target - base) / step if step else 0.0 for target in targets],
        "step": step,
        "center_x": base,
        "center_index": center,
        "side_points": side,
        "order_used": order_used,
        "max_order": max_order,
        "central_differences": levels,
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
