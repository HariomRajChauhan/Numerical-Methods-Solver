"""Numerical differentiation from tabulated data or a function expression.

For an equally spaced table the derivative is obtained by differentiating the
difference series: Newton's forward formula
``f'(x) = (1/h)[Delta y_0 - Delta^2 y_0/2 + Delta^3 y_0/3 - ...]``,
Newton's backward formula, and the central (Stirling) formulas for interior
nodes. A function input instead uses the familiar local finite-difference
stencils ``(f(x+h) - f(x))/h``, etc.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.core.errors import InvalidInputError
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
from app.core.parser import expr_to_latex, make_function, parse_expression
from app.core.registry import register
from app.solvers._common import (
    failed_response,
    format_num,
    function_field,
    number_field,
    precision_field,
)
from app.solvers.ch3_interpolation._interp import (
    central_table,
    common_step,
    difference_table,
    extrapolation_warnings,
    forward_region_warning,
    interpolating_curve,
    is_equal_spacing,
    node_table,
    prepare_dataset,
    spacing_failure,
)
from app.solvers.ch4_diff_integration._differentiation import (
    BACKWARD,
    CENTRAL,
    FORWARD,
    DerivativeResult,
    FunctionResult,
    derivative_plot,
    function_curve,
    function_derivative,
    suggest_family,
    tabulated_derivative,
)

DIFF_POINTS: list[list[float]] = [
    [0.0, 0.0],
    [1.0, 1.0],
    [2.0, 8.0],
    [3.0, 27.0],
    [4.0, 64.0],
]

SOURCE_OPTIONS = [
    SelectOption(value="table", label="Tabulated data (x, y)"),
    SelectOption(value="function", label="Function f(x) with step h"),
]
FAMILY_OPTIONS = [
    SelectOption(value="auto", label="Auto (forward / backward / central)"),
    SelectOption(value="forward", label="Newton forward differences"),
    SelectOption(value="backward", label="Newton backward differences"),
    SelectOption(value="central", label="Central (Stirling) differences"),
]
ORDER_OPTIONS = [
    SelectOption(value="1", label="First derivative f'(x)"),
    SelectOption(value="2", label="Second derivative f''(x)"),
]

META = MethodMeta(
    id="numerical_differentiation",
    chapter=Chapter.CH4_DIFF_INTEGRATION,
    name="Numerical Differentiation",
    summary=(
        "Approximate f'(x) or f''(x) from an equally spaced table (Newton forward, "
        "backward or central differences) or from a function with a chosen step."
    ),
    theory=(
        "Differentiating an interpolation formula differentiates its difference "
        "series. With p = (x - x_0)/h and d/dx = (1/h) d/dp, Newton's forward "
        "formula gives\n"
        "  f'(x) = (1/h)[Delta y_0 - Delta^2 y_0/2 + Delta^3 y_0/3 - ...],\n"
        "  f''(x) = (1/h^2)[Delta^2 y_0 - Delta^3 y_0 + (11/12) Delta^4 y_0 - ...].\n\n"
        "The backward formula uses the nabla differences at the last node and is "
        "the method of choice near the end of a table. For an interior node the "
        "symmetric central (Stirling) formulas are the most accurate:\n"
        "  f'(x) = (1/h)[mu delta y_0 - (1/6) mu delta^3 y_0 + ...],\n"
        "  f''(x) = (1/h^2)[delta^2 y_0 - (1/12) delta^4 y_0 + ...].\n\n"
        "For a function given directly the same ideas reduce to the familiar "
        "finite-difference stencils, e.g. forward (f(x+h) - f(x))/h and central "
        "(f(x+h) - f(x-h))/(2h). Smaller h reduces truncation error but eventually "
        "amplifies round-off."
    ),
    formulas=[
        LabeledLatex(
            label="Newton forward (first derivative)",
            latex=r"f'(x) = \frac{1}{h}\left[\Delta y_0 - \frac{\Delta^2 y_0}{2} + "
            r"\frac{\Delta^3 y_0}{3} - \cdots\right]",
        ),
        LabeledLatex(
            label="Newton backward (first derivative)",
            latex=r"f'(x) = \frac{1}{h}\left[\nabla y_n + \frac{\nabla^2 y_n}{2} + "
            r"\frac{\nabla^3 y_n}{3} + \cdots\right]",
        ),
        LabeledLatex(
            label="Central (Stirling) second derivative",
            latex=r"f''(x) = \frac{1}{h^2}\left[\delta^2 y_0 - "
            r"\frac{1}{12}\delta^4 y_0 + \cdots\right]",
        ),
        LabeledLatex(
            label="Function stencils",
            latex=r"f'(x) \approx \frac{f(x+h) - f(x-h)}{2h},\quad "
            r"f''(x) \approx \frac{f(x+h) - 2f(x) + f(x-h)}{h^2}",
        ),
    ],
    pseudocode=(
        "Differentiate(source, target, order, scheme, h):\n"
        "    if source is a table:\n"
        "        require equal spacing; h <- x[1] - x[0]; p <- (target - base) / h\n"
        "        build the forward / backward / central differences\n"
        "        combine each difference with d/dp of its basis polynomial, / h^order\n"
        "    else:\n"
        "        evaluate f at the stencil nodes x +/- k h\n"
        "        apply the forward / backward / central weights and divide by h^order"
    ),
    input_schema=[
        InputField(
            key="source",
            label="Input type",
            type="select",
            required=True,
            default="table",
            options=list(SOURCE_OPTIONS),
            help="Differentiate a table of values or a function expression.",
        ),
        InputField(
            key="points",
            label="Data points (x, y)",
            type="data_points",
            required=False,
            default=[list(point) for point in DIFF_POINTS],
            placeholder="0,0; 1,1; 2,8; 3,27; 4,64",
            help="Used when the input type is a table; must be equally spaced.",
        ),
        function_field(required=False),
        number_field(
            "step",
            "Step size h",
            0.01,
            required=False,
            help="Used when the input type is a function; h > 0.",
        ),
        number_field("target", "Evaluation point x", 0.0, help="Where to estimate the derivative."),
        InputField(
            key="order",
            label="Derivative order",
            type="select",
            required=True,
            default="1",
            options=list(ORDER_OPTIONS),
        ),
        InputField(
            key="formula",
            label="Difference scheme",
            type="select",
            required=True,
            default="auto",
            options=list(FAMILY_OPTIONS),
            help="Auto picks forward near the start, backward near the end, central in between.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Forward at the first node (y = x^3)",
            description="f'(0) = 0 from the forward formula on x = 0..4.",
            inputs={
                "source": "table",
                "points": [list(point) for point in DIFF_POINTS],
                "target": 0.0,
                "order": "1",
                "formula": "forward",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Backward second derivative (y = x^3)",
            description="f''(3) = 18 from the backward formula at the last node.",
            inputs={
                "source": "table",
                "points": [list(point) for point in DIFF_POINTS],
                "target": 3.0,
                "order": "2",
                "formula": "backward",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Central difference of sin x",
            description="f'(0.2) ~ cos(0.2) using a function with step h = 0.1.",
            inputs={
                "source": "function",
                "function": "sin(x)",
                "step": 0.1,
                "target": 0.2,
                "order": "1",
                "formula": "central",
                "decimal_precision": 6,
            },
        ),
    ],
)


def _diagonal_latex(labels: list[str], values: list[float], decimals: int) -> str:
    parts = [
        rf"{label} = {format_num(value, decimals)}"
        for label, value in zip(labels, values, strict=True)
    ]
    return r",\quad ".join(parts)


def _family_name(family: str) -> str:
    return {
        FORWARD: "Newton forward differences",
        BACKWARD: "Newton backward differences",
        CENTRAL: "central (Stirling) differences",
    }[family]


def _series_latex(result: DerivativeResult, decimals: int) -> str:
    parts = [
        rf"{format_num(term.weight, decimals)}\,\left({term.label}\right)"
        for term in result.terms
    ]
    body = " + ".join(parts) if parts else "0"
    return (
        rf"f^{{({result.order})}}(x) = \frac{{1}}{{h^{result.order}}}"
        rf"\left[ {body} \right]"
    )


def _terms_latex(result: DerivativeResult, decimals: int) -> str:
    lines = [
        rf"{term.label}\cdot{format_num(term.weight, decimals)} = "
        rf"{format_num(term.contribution, decimals)}"
        for term in result.terms
    ]
    return r"\\[1mm]".join(lines) if lines else r"\text{(no terms)}"


def _term_table(result: DerivativeResult, decimals: int) -> DataTable:
    rows = [
        [
            term.label,
            format_num(term.difference, decimals),
            format_num(term.weight, decimals),
            format_num(term.contribution, decimals),
        ]
        for term in result.terms
    ]
    return DataTable(
        title="Derivative terms",
        columns=["Term", "Difference", "d-basis weight", "Contribution"],
        rows=rows,
    )


def _target_value(xs: np.ndarray, ys: np.ndarray, target: float) -> float:
    if len(xs) < 2:
        return float(ys[0])
    coefficients = np.polyfit(xs, ys, len(xs) - 1)
    return float(np.polyval(coefficients, target))


def _table_branch(
    inputs: dict[str, Any],
    *,
    target: float,
    order: int,
    choice: str,
    decimals: int,
) -> SolveResponse:
    points = inputs.get("points")
    if not points:
        raise InvalidInputError("Data points are required for the tabulated input type.")
    min_points = 3 if order == 2 else 2
    dataset = prepare_dataset(points, min_points=min_points)
    xs, ys = dataset.xs, dataset.ys
    if not is_equal_spacing(xs):
        return spacing_failure(META.id, xs, decimals)
    h = common_step(xs)
    if h == 0.0:
        raise InvalidInputError("The data points must have distinct x values.")

    family = suggest_family(xs, target, h) if choice == "auto" else choice
    if family == CENTRAL and len(xs) < 3:
        raise InvalidInputError(
            "The central (Stirling) formula needs at least three points.",
            hint="Add more points or choose the forward/backward scheme.",
        )
    result = tabulated_derivative(
        xs, ys, target=target, order=order, family=family, h=h
    )
    if order == 2 and len(result.terms) == 0:
        raise InvalidInputError(
            "Too few points for a second derivative with the chosen scheme.",
            hint="A second derivative needs at least three or four points.",
        )

    warnings = [*dataset.notices, *extrapolation_warnings([target], xs)]
    if family == FORWARD:
        warnings.extend(forward_region_warning(result.p, len(xs)))
    if family == BACKWARD and result.p < -(len(xs) - 1) / 2.0:
        warnings.append(
            "The target lies towards the start of the table; Newton's forward "
            "formula is usually more accurate there."
        )

    base_label = {
        FORWARD: "x_0",
        BACKWARD: "x_n",
        CENTRAL: "x_c",
    }[family]
    base_note = {
        FORWARD: "The series is anchored at the first node x_0.",
        BACKWARD: "The series is anchored at the last node x_n.",
        CENTRAL: "The series is centred on the node nearest the target, x_c.",
    }[family]

    steps = [
        Step(
            title="Setup",
            latex=(
                rf"\text{{Points }} n = {len(xs)},\quad h = {format_num(h, decimals)}"
                rf"\\[1mm] \text{{Target }} x = {format_num(target, decimals)},\quad "
                rf"\text{{order }} = {order}"
                rf"\\[1mm] p = \frac{{x - {base_label}}}{{h}}"
                rf" = {format_num(result.p, decimals)}"
                rf"\\[1mm] \text{{Scheme: {_family_name(family)}}}"
            ),
            note=base_note,
        ),
        Step(
            title="Differences used",
            latex=_diagonal_latex(result.labels, result.differences, decimals),
            note="These are the difference values entering the derivative series.",
        ),
        Step(
            title="Derivative formula",
            latex=_series_latex(result, decimals),
            note=(
                "Each basis polynomial p(p-1).../m! is differentiated with respect to p; "
                f"the factor 1/h^{order} converts d/dp into d/dx."
            ),
        ),
        Step(
            title="Substitute and sum",
            latex=_terms_latex(result, decimals),
            note="Each difference is multiplied by its weight and added.",
        ),
        Step(
            title="Result",
            latex=(
                rf"f^{{({order})}}\left({format_num(target, decimals)}\right) = "
                rf"{format_num(result.value, decimals)}"
            ),
            note="Derivative estimated from the equally spaced table.",
        ),
    ]

    tables = [node_table(xs, ys, decimals)]
    if family == CENTRAL:
        tables.append(central_table(xs, ys, decimals))
    else:
        tables.append(difference_table(xs, ys, family, decimals))
    tables.append(_term_table(result, decimals))

    curve = interpolating_curve(xs, ys, targets=[target])
    target_y = _target_value(xs, ys, target)
    slope = result.value if order == 1 and math.isfinite(result.value) else None
    plot = derivative_plot(
        points=(list(xs), list(ys)),
        curve=curve,
        target=target,
        target_y=target_y,
        slope=slope,
    )

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result={
            "value": result.value,
            "order": order,
            "family": family,
            "p": result.p,
            "base_index": result.base_index,
            "base_x": result.base_x,
            "step": h,
            "points": len(xs),
        },
        steps=steps,
        tables=tables,
        plot=plot,
        warnings=warnings,
    )


def _function_branch(
    inputs: dict[str, Any],
    *,
    target: float,
    order: int,
    choice: str,
    decimals: int,
) -> SolveResponse:
    text = inputs.get("function")
    if not text:
        raise InvalidInputError("A function expression is required for the function input type.")
    h = float(inputs.get("step", 0.01))
    if h <= 0.0:
        raise InvalidInputError(
            "The step h must be positive.",
            hint="Use a small positive step such as 0.01.",
        )
    family = CENTRAL if choice == "auto" else choice

    expression = parse_expression(text, ("x",))
    f = make_function(expression, ("x",), strict=False)
    latex_f = expr_to_latex(expression)

    try:
        outcome = function_derivative(f, x0=target, h=h, order=order, family=family)
    except ValueError as exc:
        return failed_response(META.id, str(exc))

    steps = [
        Step(
            title="Setup",
            latex=(
                rf"f(x) = {latex_f},\quad x = {format_num(target, decimals)},\quad "
                rf"h = {format_num(h, decimals)},\quad \text{{order }} = {order}"
                rf"\\[1mm] \text{{Scheme: {_family_name(family)}}}"
            ),
            note="A local finite-difference stencil applied directly to f(x).",
        ),
        Step(
            title="Finite-difference formula",
            latex=_function_formula(order, family),
            note="Substitute the tabulated values of f at the stencil nodes.",
        ),
        Step(
            title="Substitute values",
            latex=_function_substitution(outcome, decimals),
            note="Function values at the nodes x + k h.",
        ),
        Step(
            title="Result",
            latex=(
                rf"f^{{({order})}}\left({format_num(target, decimals)}\right) \approx "
                rf"{format_num(outcome.value, decimals)}"
            ),
            note="Finite-difference estimate.",
        ),
    ]

    nodes_table = DataTable(
        title="Stencil nodes",
        columns=["x + k h", "f(x + k h)", "Weight"],
        rows=[
            [
                format_num(node.x, decimals),
                format_num(node.value, decimals),
                format_num(node.weight, decimals),
            ]
            for node in outcome.nodes
        ],
    )

    curve = function_curve(f, target, h)
    slope = outcome.value if order == 1 and math.isfinite(outcome.value) else None
    plot = derivative_plot(
        points=None,
        curve=curve,
        target=target,
        target_y=float(f(target)),
        slope=slope,
        curve_name="f(x)",
    )

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result={
            "value": outcome.value,
            "order": order,
            "family": family,
            "step": h,
            "x": target,
        },
        steps=steps,
        tables=[nodes_table],
        plot=plot,
    )


def _function_formula(order: int, family: str) -> str:
    templates = {
        (1, FORWARD): r"f'(x) \approx \frac{f(x+h) - f(x)}{h}",
        (1, BACKWARD): r"f'(x) \approx \frac{f(x) - f(x-h)}{h}",
        (1, CENTRAL): r"f'(x) \approx \frac{f(x+h) - f(x-h)}{2h}",
        (2, FORWARD): r"f''(x) \approx \frac{f(x+2h) - 2f(x+h) + f(x)}{h^2}",
        (2, BACKWARD): r"f''(x) \approx \frac{f(x) - 2f(x-h) + f(x-2h)}{h^2}",
        (2, CENTRAL): r"f''(x) \approx \frac{f(x+h) - 2f(x) + f(x-h)}{h^2}",
    }
    return templates[(order, family)]


def _function_substitution(outcome: FunctionResult, decimals: int) -> str:
    terms = " + ".join(
        rf"{format_num(node.weight, decimals)}\cdot "
        rf"\left({format_num(node.value, decimals)}\right)"
        for node in outcome.nodes
    )
    return (
        rf"\frac{{ {terms} }}{{{format_num(outcome.denominator, decimals)}}} = "
        rf"{format_num(outcome.value, decimals)}"
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Estimate a derivative from a table or a function."""
    decimals = int(inputs["decimal_precision"])
    source = str(inputs.get("source", "table"))
    target = float(inputs["target"])
    order = int(inputs["order"])
    choice = str(inputs.get("formula", "auto"))

    if source == "function":
        return _function_branch(
            inputs, target=target, order=order, choice=choice, decimals=decimals
        )
    return _table_branch(
        inputs, target=target, order=order, choice=choice, decimals=decimals
    )
