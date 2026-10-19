"""Bessel's central-difference interpolation for equally spaced data.

Bessel's formula works with the central pair ``(x0, x1) = (x_c, x_c + h)`` and is
built from the average at the midpoint together with the odd differences at
``y_{1/2}`` and the averaged even differences:

    P(x) = (y0 + y1)/2 + (p - 1/2) delta y_{1/2}
             + p(p-1)/2! * (delta^2 y0 + delta^2 y1)/2 + ...

with ``p = (x - x0)/h``. It is most accurate for ``0.25 <= p <= 0.75``.
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
    bessel_center,
    bessel_differences_latex,
    bessel_evaluate,
    bessel_formula_latex,
    bessel_region_warning,
    center_field,
    order_field,
    side_points,
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
    id="bessel",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Bessel's Interpolation",
    summary=(
        "Central-difference interpolation for targets between the two middle entries "
        "of an equally spaced table; best for 0.25 <= p <= 0.75."
    ),
    theory=(
        "Bessel's formula is the companion of Stirling's formula. It chooses the "
        "central pair of nodes x0 and x1 = x0 + h that straddle the target and uses "
        "the value at the midpoint together with the differences at y_{1/2}:\n"
        "  P(x) = (y0 + y1)/2 + (p - 1/2) delta y_{1/2} "
        "+ p(p-1)/2! (delta^2 y0 + delta^2 y1)/2 + ...\n"
        "with p = (x - x0)/h.\n\n"
        "Because the expansion is centred on the middle of an interval, it is the "
        "most accurate of the equal-spacing forms when the target lies between two "
        "nodes, roughly 0.25 <= p <= 0.75. The even-order terms average the central "
        "differences on either side of the midpoint; the odd-order terms use the "
        "differences halfway between the nodes. Only the symmetric points the table "
        "can support are kept and the working states the order used."
    ),
    formulas=[
        LabeledLatex(label="Parameter", latex=r"p = \frac{x - x_0}{h}"),
        LabeledLatex(
            label="Midpoint value",
            latex=r"\frac{y_0 + y_1}{2}",
        ),
        LabeledLatex(
            label="Bessel's formula",
            latex=r"P(x) = \frac{y_0+y_1}{2} + \left(p-\tfrac12\right)\delta y_{1/2}"
            r" + \frac{p(p-1)}{2!}\frac{\delta^2 y_0+\delta^2 y_1}{2}"
            r" + \frac{(p-\tfrac12)p(p-1)}{3!}\delta^3 y_{1/2} + \cdots",
        ),
    ],
    pseudocode=(
        "Bessel(xs, ys, x):\n"
        "    require equal spacing; h <- x[1] - x[0]\n"
        "    pick the central pair (x0, x1) straddling the target\n"
        "    build the central-difference table around the pair\n"
        "    p <- (x - x0) / h\n"
        "    P <- (y0 + y1) / 2\n"
        "    for k = 1, 2, 3, ... up to the available order:\n"
        "        if k is odd:  add coefficient * delta^k y_{1/2}\n"
        "        else:         add coefficient * (delta^k y0 + delta^k y1) / 2\n"
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
                "Table x = 0..4, y = 1, 2, 5, 10, 17; central pair (2, 3) gives "
                "P(2.5) = 7.25."
            ),
            inputs={
                "points": [[0, 1], [1, 2], [2, 5], [3, 10], [4, 17]],
                "targets": [2.5],
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Cubic y = x^3",
            description="Table x = 0..4, y = 0, 1, 8, 27, 64; interpolate at x = 2.5.",
            inputs={
                "points": [[0, 0], [1, 1], [2, 8], [3, 27], [4, 64]],
                "targets": [2.5],
                "decimal_precision": 6,
            },
        ),
    ],
)


def _side_note(side: int, maximum: int, used: int) -> str:
    return (
        f"The central pair has {side} point(s) on its shorter side, so orders up to "
        f"{maximum} are available; order {used} is used."
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Interpolate at the requested targets with Bessel's central formula."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    if not is_equal_spacing(xs):
        return spacing_failure(META.id, xs, decimals)

    targets = require_targets(inputs.get("targets"))
    step = common_step(xs)
    size = len(xs)
    if size < 2:
        return failed_response(META.id, "Bessel's formula needs at least two data points.")

    center = bessel_center(xs, inputs.get("center"), targets[0])
    warnings = [*dataset.notices]
    if center > size - 2:
        center = size - 2
        warnings.append(
            "The chosen central point is the last node, which has no next point; the "
            "central pair was shifted down by one interval."
        )
    side = side_points(center, size, bessel=True)

    levels = central_differences(ys)
    order = inputs.get("order")
    base = float(xs[center])
    upper = float(xs[center + 1])

    warnings.extend(extrapolation_warnings(targets, xs))
    first_p = (targets[0] - base) / step if step else 0.0
    warnings.extend(bessel_region_warning(first_p))

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"\text{Number of points } n = " + f"{size}"
                + r"\\[1mm] h = " + format_num(step, decimals)
                + r"\\[1mm] x_0 = " + format_num(base, decimals)
                + r"\\[1mm] x_1 = " + format_num(upper, decimals)
                + r"\\[1mm] p = \frac{x - x_0}{h}"
            ),
            note="Bessel works from the central pair (x0, x1) straddling the target.",
        ),
    ]

    values: list[float] = []
    marks: set[tuple[int, int]] = set()
    order_used = 0
    max_order = 2 * side + 1
    for target in targets:
        p = (target - base) / step if step else 0.0
        evaluation = bessel_evaluate(levels, ys, center, p, order, decimals)
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
                    "Substitute p into the Bessel series; each term already shows its "
                    "numeric coefficient and difference."
                ),
            )
        )

    steps.insert(
        1,
        Step(
            title="Central differences used",
            latex=bessel_differences_latex(levels, center, order_used, decimals),
            note="Odd differences sit at y_{1/2}; even differences are averaged over the pair.",
        ),
    )
    steps.insert(
        2,
        Step(
            title="Bessel's formula",
            latex=bessel_formula_latex(order_used),
            note="Only the terms the table can support around the chosen pair are kept.",
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
                f"Central pair ({format_num(base, decimals)}, {format_num(upper, decimals)}) "
                f"using central differences up to order {order_used}."
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
        title="Bessel interpolation",
    )

    result: dict[str, Any] = {
        "value": values[0],
        "values": values,
        "targets": targets,
        "p": [(target - base) / step if step else 0.0 for target in targets],
        "step": step,
        "center_x": base,
        "next_x": upper,
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
