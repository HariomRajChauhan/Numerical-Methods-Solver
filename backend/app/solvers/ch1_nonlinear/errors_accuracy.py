"""Errors and accuracy.

A quantitative treatment of the standard error measures used throughout
numerical methods: absolute error, relative (and percentage) error, the
number of significant digits guaranteed by a given relative error, and a
side-by-side demonstration of rounding versus chopping to a fixed number of
decimal places.

Unlike the root-finding solvers this is a calculator: the student supplies a
true value and an approximation (and, optionally, the previous iterate of an
iterative process to obtain the *approximate* error).
"""

from __future__ import annotations

import math
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Any

from app.core.errors import InvalidInputError
from app.core.models import (
    Chapter,
    DataTable,
    ErrorInfo,
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
from app.solvers._common import (
    format_num,
    number_field,
    precision_field,
)


def _round_half_up(value: float, decimals: int) -> float:
    """Round to ``decimals`` places using exam-style round-half-up."""
    quant = Decimal(1).scaleb(-decimals)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def _chop(value: float, decimals: int) -> float:
    """Truncate (round toward zero) to ``decimals`` places."""
    quant = Decimal(1).scaleb(-decimals)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_DOWN))


def _significant_figures(value: float) -> int:
    """Count significant figures of ``value`` from its normalised decimal form."""
    if value == 0:
        return 1
    _sign, digits, _exp = Decimal(str(value)).normalize().as_tuple()
    return len(digits)


def _guaranteed_digits(relative_percent: float) -> int | None:
    """Greatest ``n`` with ``E_r% <= 0.5 x 10^(2-n)`` (Chapra & Canale)."""
    if relative_percent <= 0:
        return None
    return math.floor(2.0 - math.log10(2.0 * relative_percent))


META = MethodMeta(
    id="errors_accuracy",
    chapter=Chapter.CH1_NONLINEAR,
    name="Errors and Accuracy",
    summary=(
        "Compute absolute, relative and percentage error, the number of "
        "significant digits guaranteed, and compare rounding with chopping."
    ),
    theory=(
        "Numerical answers are always approximate. If x is the true (or accepted) "
        "value and x* the computed value, the absolute error is Ea = |x - x*| and "
        "the relative error is Er = Ea / |x|, usually quoted as a percentage "
        "Er x 100%.\n\n"
        "Relative error is scale independent, which is why it is preferred when "
        "comparing approximations of very different magnitudes. When the true "
        "value is unknown (as in an iterative process) we instead use the "
        "approximate error between successive iterates, "
        "|x(k) - x(k-1)| / |x(k)| x 100%.\n\n"
        "The number of correct significant digits follows from the relative "
        "error: a result whose relative error does not exceed "
        "0.5 x 10^(2-n) percent is correct to at least n significant digits. "
        "Finally, rounding a number to p decimal places is always at least as "
        "accurate as chopping it at the same place, because rounding can move the "
        "value either way while chopping always moves it toward zero."
    ),
    formulas=[
        LabeledLatex(label="Absolute error", latex=r"E_a = \left|x - x^{*}\right|"),
        LabeledLatex(
            label="Relative / percentage error",
            latex=r"E_r = \frac{\left|x - x^{*}\right|}{\left|x\right|},\qquad E_r\% = E_r \times 100\%",
        ),
        LabeledLatex(
            label="Approximate error",
            latex=r"\varepsilon_a = \left|\frac{x_k - x_{k-1}}{x_k}\right| \times 100\%",
        ),
        LabeledLatex(
            label="Significant digits",
            latex=r"E_r\% \le 0.5\times10^{\,2-n}\;\Rightarrow\; n \text{ significant digits}",
        ),
    ],
    pseudocode=(
        "Errors(true, approx, prev, p):\n"
        "    Ea <- |true - approx|\n"
        "    Er <- Ea / |true|\n"
        "    Erpct <- Er * 100\n"
        "    n <- floor(2 - log10(2 * Erpct))      # significant digits\n"
        "    if prev given:\n"
        "        approx_err <- |(approx - prev)/approx| * 100\n"
        "    rounded <- round_half_up(approx, p)\n"
        "    chopped <- truncate(approx, p)\n"
        "    return all measures and their errors"
    ),
    input_schema=[
        number_field(
            "true_value",
            "True (accepted) value x",
            3.141592653589793,
            help="The exact or accepted reference value.",
        ),
        number_field(
            "approximate_value",
            "Approximate value x*",
            3.142857142857143,
            help="The value being assessed (e.g. 22/7 for pi).",
        ),
        number_field(
            "previous_approximation",
            "Previous iterate (optional)",
            3.14,
            required=False,
            help=(
                "Optional earlier iterate of an iterative method, to obtain the "
                "approximate (successive) error."
            ),
        ),
        precision_field(default=4),
    ],
    examples=[
        MethodExample(
            name="pi as 22/7",
            description="Assess the classic rational approximation of pi.",
            inputs={
                "true_value": 3.141592653589793,
                "approximate_value": 3.142857142857143,
                "previous_approximation": 3.14,
                "decimal_precision": 4,
            },
        ),
        MethodExample(
            name="e to 3 decimals",
            description="Accepted value 2.71828 approximated by 2.718.",
            inputs={
                "true_value": 2.718281828459045,
                "approximate_value": 2.718,
                "decimal_precision": 3,
            },
        ),
        MethodExample(
            name="Rounding vs chopping 2/3",
            description="1/3 approximated by 0.3333 and rounded/chopped to 3 decimals.",
            inputs={
                "true_value": 0.3333333333333333,
                "approximate_value": 0.3333,
                "decimal_precision": 3,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Compute the error measures for the supplied true/approximate values."""
    del limits  # no iteration budget is needed for a direct calculation
    true_value = float(inputs["true_value"])
    approximate = float(inputs["approximate_value"])
    decimals = int(inputs["decimal_precision"])
    previous_raw = inputs.get("previous_approximation")
    previous = None if previous_raw is None else float(previous_raw)

    if true_value == 0:
        raise InvalidInputError(
            "The true value must be non-zero for a relative error.",
            hint="Relative and percentage error divide by |x|; use a non-zero true value.",
        )

    absolute = abs(true_value - approximate)
    relative = absolute / abs(true_value)
    relative_percent = relative * 100.0
    digits = _guaranteed_digits(relative_percent)

    rounded = _round_half_up(approximate, decimals)
    chopped = _chop(approximate, decimals)
    rounded_error = abs(true_value - rounded)
    chopped_error = abs(true_value - chopped)

    approximate_percent: float | None = None
    if previous is not None:
        if approximate == 0:
            raise InvalidInputError(
                "The approximate value must be non-zero to form a relative approximate error.",
                hint="The successive error divides by the current approximation.",
            )
        approximate_percent = abs((approximate - previous) / approximate) * 100.0

    warnings: list[str] = []
    if rounded_error > chopped_error + 1e-15:
        warnings.append(
            "Unusually, chopping was closer than rounding here; check the precision used."
        )

    rows: list[list[Any]] = [
        ["Absolute error", "|x - x*|", format_num(absolute, decimals)],
        [
            "Relative error",
            "|x - x*| / |x|",
            format_num(relative, decimals),
        ],
        [
            "Percentage error",
            "relative error x 100%",
            f"{format_num(relative_percent, decimals)}\\%",
        ],
        [
            "Guaranteed significant digits",
            "n = floor(2 - log10(2 x E_r%))",
            "exact" if digits is None else str(digits),
        ],
    ]
    if approximate_percent is not None:
        rows.append(
            [
                "Approximate error (iterative)",
                "|x_k - x_(k-1)| / |x_k| x 100%",
                f"{format_num(approximate_percent, decimals)}\\%",
            ]
        )

    comparison_rows: list[list[Any]] = [
        [
            "Given x*",
            format_num(approximate, decimals),
            format_num(absolute, decimals),
            format_num(relative_percent, decimals) + "\\%",
        ],
        [
            f"Rounded to {decimals} dp",
            format_num(rounded, decimals),
            format_num(rounded_error, decimals),
            format_num((rounded_error / abs(true_value)) * 100.0, decimals) + "\\%",
        ],
        [
            f"Chopped to {decimals} dp",
            format_num(chopped, decimals),
            format_num(chopped_error, decimals),
            format_num((chopped_error / abs(true_value)) * 100.0, decimals) + "\\%",
        ],
    ]

    digits_text = (
        "the value is exact"
        if digits is None
        else f"at least {digits} significant digit{'' if digits == 1 else 's'}"
    )
    bound_text = (
        format_num(2.0 - math.log10(2.0 * relative_percent), 4)
        if relative_percent > 0
        else r"\text{n/a}"
    )
    steps: list[Step] = [
        Step(
            title="Given data",
            latex=(
                f"x = {format_num(true_value, decimals)},\\qquad "
                f"x^{{*}} = {format_num(approximate, decimals)}"
            ),
            note="x is the true/accepted value; x* is the approximation being assessed.",
        ),
        Step(
            title="Absolute error",
            latex=(
                f"E_a = |x - x^{{*}}| = |{format_num(true_value, decimals)} - "
                f"{format_num(approximate, decimals)}| = {format_num(absolute, decimals)}"
            ),
            note="The absolute error carries the same units as the quantity itself.",
        ),
        Step(
            title="Relative and percentage error",
            latex=(
                f"E_r = \\frac{{E_a}}{{|x|}} = \\frac{{{format_num(absolute, decimals)}}}"
                f"{{{format_num(abs(true_value), decimals)}}} = {format_num(relative, decimals)}"
                f"\\\\ E_r\\% = {format_num(relative, decimals)} \\times 100\\% = "
                f"{format_num(relative_percent, decimals)}\\%"
            ),
            note="Relative error is dimensionless, so it is comparable across problems.",
        ),
        Step(
            title="Significant digits",
            latex=(
                f"n \\ge 2 - \\log_{{10}}\\left(2 \\times {format_num(relative_percent, decimals)}\\%\\right) "
                f"= {bound_text}"
                f"\\;\\Rightarrow\\; \\text{{{digits_text}}}"
            ),
            note="The relative error bounds how many leading digits are trustworthy.",
        ),
        Step(
            title="Rounding vs chopping",
            latex=(
                f"\\text{{Rounded to }} {decimals} \\text{{ dp}} = {format_num(rounded, decimals)}"
                f",\\quad |x - \\tilde{{x}}_r| = {format_num(rounded_error, decimals)}"
                f"\\\\ \\text{{Chopped to }} {decimals} \\text{{ dp}} = {format_num(chopped, decimals)}"
                f",\\quad |x - \\tilde{{x}}_c| = {format_num(chopped_error, decimals)}"
            ),
            note="Chopping always moves toward zero; rounding keeps the nearest representable value.",
        ),
    ]
    if previous is not None and approximate_percent is not None:
        steps.append(
            Step(
                title="Approximate (successive) error",
                latex=(
                    f"\\varepsilon_a = \\left|\\frac{{x_k - x_{{k-1}}}}{{x_k}}\\right| \\times 100\\% "
                    f"= \\left|\\frac{{{format_num(approximate, decimals)} - {format_num(previous, decimals)}}}"
                    f"{{{format_num(approximate, decimals)}}}\\right| \\times 100\\% = "
                    f"{format_num(approximate_percent, decimals)}\\%"
                ),
                note="Used when the true value is unknown, as in an iterative method.",
            )
        )

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result={
            "true_value": true_value,
            "approximate_value": approximate,
            "absolute_error": absolute,
            "relative_error": relative,
            "relative_error_percent": relative_percent,
            "significant_digits": digits,
            "significant_figures_true": _significant_figures(true_value),
            "significant_figures_approximate": _significant_figures(approximate),
            "approximate_error_percent": approximate_percent,
            "rounded_value": rounded,
            "rounded_absolute_error": rounded_error,
            "chopped_value": chopped,
            "chopped_absolute_error": chopped_error,
        },
        steps=steps,
        tables=[
            DataTable(
                title="Error measures",
                columns=["Measure", "Formula", "Value"],
                rows=rows,
            ),
            DataTable(
                title="Rounding vs chopping",
                columns=["Method", "Value", "Absolute error", "Relative error"],
                rows=comparison_rows,
            ),
        ],
        plot=_build_plot(decimals, absolute, rounded_error, chopped_error),
        errors=ErrorInfo(absolute=absolute, relative_percent=relative_percent),
        warnings=warnings,
    )


def _build_plot(
    decimals: int,
    given_error: float,
    rounded_error: float,
    chopped_error: float,
) -> PlotPayload:
    """A bar chart comparing the absolute error of the three representations."""
    labels = ["Given x*", "Rounded", "Chopped"]
    values = [given_error, rounded_error, chopped_error]
    trace = {
        "type": "bar",
        "name": "Absolute error",
        "x": labels,
        "y": values,
        "marker": {"color": ["#6366f1", "#16a34a", "#dc2626"]},
        "text": [f"{value:.{decimals}g}" for value in values],
        "textposition": "auto",
    }
    layout: dict[str, Any] = {
        "title": {"text": "Absolute error by representation"},
        "xaxis": {"title": {"text": "Representation"}},
        "yaxis": {"title": {"text": "|error|"}, "rangemode": "tozero"},
        "showlegend": False,
    }
    return PlotPayload(traces=[trace], layout=layout)
