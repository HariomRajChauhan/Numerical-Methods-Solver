"""Shared central-difference working for Stirling's and Bessel's formulas.

This private module holds the pieces common to the two central-interpolation
methods: choosing the central point, the pattern of coefficients that multiply
the central differences, the exam-style working and the region warnings. It is
picked up by neither the registry loader (leading underscore) nor the API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.core.errors import InvalidInputError
from app.core.models import InputField
from app.solvers._common import format_num

# Regions in which each central formula is most accurate (in units of p = (x - x0)/h).
STIRLING_LIMIT = 0.25
BESSEL_LOW = 0.25
BESSEL_HIGH = 0.75

# Match tolerance when the user supplies an x-coordinate for the central point.
_CENTER_EPS = 1e-9


def center_field() -> InputField:
    """The optional x-coordinate of the central point of the table."""
    return InputField(
        key="center",
        label="Central point x0 (optional)",
        type="number",
        required=False,
        default=None,
        placeholder="auto",
        help=(
            "An x value that already appears in the table; leave blank to pick the "
            "central point nearest the target (Stirling) or the pair straddling it (Bessel)."
        ),
    )


def order_field() -> InputField:
    """The optional highest difference order to include."""
    return InputField(
        key="order",
        label="Highest difference order (optional)",
        type="integer",
        required=False,
        default=None,
        min=1,
        max=12,
        placeholder="auto",
        help=(
            "Number of central-difference terms to use; leave blank to use the highest "
            "order the chosen centre supports."
        ),
    )


# ---------------------------------------------------------------------------
# Choosing the central point
# ---------------------------------------------------------------------------


def match_node(xs: np.ndarray, value: float) -> int:
    """Return the index of the data point whose x equals ``value``.

    Raises:
        InvalidInputError: When ``value`` is not one of the tabulated x values.
    """
    index = min(range(len(xs)), key=lambda i: abs(float(xs[i]) - float(value)))
    scale = max(1.0, abs(float(value)))
    if abs(float(xs[index]) - float(value)) > _CENTER_EPS * scale:
        raise InvalidInputError(
            f"The central point x0 = {float(value):g} is not one of the tabulated x values.",
            hint="Pick an x value shown in the data table, or leave the field blank.",
        )
    return index


def stirling_center(xs: np.ndarray, center: float | None, target: float) -> int:
    """The central node for Stirling: the given node, else the one nearest ``target``.

    The automatic choice stays away from the end points so that points remain on
    both sides of the centre.
    """
    size = len(xs)
    if center is not None:
        return match_node(xs, center)
    candidates = list(range(1, size - 1)) if size >= 3 else list(range(size))
    return min(candidates, key=lambda i: abs(float(xs[i]) - float(target)))


def bessel_center(xs: np.ndarray, center: float | None, target: float) -> int:
    """The left node of the central pair for Bessel.

    The pair is ``(x0, x1) = (xs[c], xs[c + 1])``. By default ``c`` is the lower
    node of the interval containing the target, which keeps ``p`` inside ``[0, 1]``.
    """
    size = len(xs)
    if center is not None:
        return match_node(xs, center)
    below = [i for i in range(size) if float(xs[i]) <= target]
    index = below[-1] if below else 0
    return min(index, size - 2)


def side_points(center: int, size: int, *, bessel: bool) -> int:
    """The number of points available on the shorter side of the central point."""
    if bessel:
        return min(center, size - 2 - center)
    return min(center, size - 1 - center)


# ---------------------------------------------------------------------------
# Coefficients and products
# ---------------------------------------------------------------------------


def _stirling_even_coefficient(p: float, m: int) -> float:
    return math.prod(p * p - j * j for j in range(m)) / math.factorial(2 * m)


def _stirling_odd_coefficient(p: float, m: int) -> float:
    return p * math.prod(p * p - j * j for j in range(1, m + 1)) / math.factorial(2 * m + 1)


def _bessel_factor_value(index: int, p: float) -> float:
    if index == 1:
        return p
    if index % 2 == 0:
        return p - index // 2
    return p + (index - 1) // 2


def _bessel_even_coefficient(p: float, m: int) -> float:
    product = math.prod(_bessel_factor_value(i, p) for i in range(1, 2 * m + 1))
    return product / math.factorial(2 * m)


def _bessel_odd_coefficient(p: float, m: int) -> float:
    product = math.prod(_bessel_factor_value(i, p) for i in range(1, 2 * m + 1))
    return (p - 0.5) * product / math.factorial(2 * m + 1)


def _stirling_even_product(m: int) -> str:
    parts = [r"p^{2}"]
    for j in range(1, m):
        parts.append(rf"(p^{{2}}-{j * j})")
    return "".join(parts)


def _stirling_odd_product(m: int) -> str:
    parts = [r"p"]
    for j in range(1, m + 1):
        parts.append(rf"(p^{{2}}-{j * j})")
    return "".join(parts)


def _bessel_product(count: int) -> str:
    parts: list[str] = []
    for i in range(1, count + 1):
        if i == 1:
            parts.append(r"p")
        elif i % 2 == 0:
            parts.append(rf"(p-{i // 2})")
        else:
            parts.append(rf"(p+{(i - 1) // 2})")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------


@dataclass
class CentralEvaluation:
    """The value and the exam-style pieces produced for one target."""

    value: float
    order_used: int
    max_order: int
    terms_latex: list[str]
    term_values: list[float]
    marks: set[tuple[int, int]]


def stirling_evaluate(
    levels: list[list[float]],
    ys: np.ndarray,
    center: int,
    p: float,
    order: int | None,
    decimals: int,
) -> CentralEvaluation:
    """Evaluate Stirling's central formula at ``p`` for the chosen centre."""
    size = len(ys)
    max_order = 2 * side_points(center, size, bessel=False)
    effective = max_order if order is None else min(int(order), max_order)

    terms_latex = [format_num(float(ys[center]), decimals)]
    values = [float(ys[center])]
    marks: set[tuple[int, int]] = {(0, center)}

    for k in range(1, effective + 1):
        if k % 2 == 1:
            m = (k - 1) // 2
            left = float(levels[k][center - m - 1])
            right = float(levels[k][center - m])
            mean = 0.5 * (left + right)
            marks.update({(k, center - m - 1), (k, center - m)})
            coefficient = _stirling_odd_coefficient(p, m)
            term = coefficient * mean
            values.append(term)
            terms_latex.append(
                _stirling_odd_latex(k, m, left, right, coefficient, term, decimals)
            )
        else:
            m = k // 2
            delta = float(levels[k][center - m])
            marks.add((k, center - m))
            coefficient = _stirling_even_coefficient(p, m)
            term = coefficient * delta
            values.append(term)
            terms_latex.append(_stirling_even_latex(k, m, delta, coefficient, term, decimals))

    return CentralEvaluation(float(sum(values)), effective, max_order, terms_latex, values, marks)


def bessel_evaluate(
    levels: list[list[float]],
    ys: np.ndarray,
    center: int,
    p: float,
    order: int | None,
    decimals: int,
) -> CentralEvaluation:
    """Evaluate Bessel's central formula at ``p`` for the chosen pair."""
    size = len(ys)
    max_order = 2 * side_points(center, size, bessel=True) + 1
    effective = max_order if order is None else min(int(order), max_order)

    left_y = float(ys[center])
    right_y = float(ys[center + 1])
    base = 0.5 * (left_y + right_y)
    terms_latex = [
        r"\frac{y_0+y_1}{2} = "
        rf"\frac{{{format_num(left_y, decimals)}+{format_num(right_y, decimals)}}}{{2}}"
        rf" = {format_num(base, decimals)}"
    ]
    values = [base]
    marks: set[tuple[int, int]] = {(0, center), (0, center + 1)}

    for k in range(1, effective + 1):
        if k % 2 == 1:
            m = (k - 1) // 2
            delta = float(levels[k][center - m])
            marks.add((k, center - m))
            coefficient = _bessel_odd_coefficient(p, m)
            term = coefficient * delta
            values.append(term)
            terms_latex.append(_bessel_odd_latex(k, m, delta, coefficient, term, decimals))
        else:
            m = k // 2
            a = float(levels[k][center - m])
            b = float(levels[k][center + 1 - m])
            average = 0.5 * (a + b)
            marks.update({(k, center - m), (k, center + 1 - m)})
            coefficient = _bessel_even_coefficient(p, m)
            term = coefficient * average
            values.append(term)
            terms_latex.append(_bessel_even_latex(k, m, a, b, coefficient, term, decimals))

    return CentralEvaluation(float(sum(values)), effective, max_order, terms_latex, values, marks)


# ---------------------------------------------------------------------------
# LaTeX fragments
# ---------------------------------------------------------------------------


def _stirling_even_latex(
    k: int, m: int, delta: float, coefficient: float, term: float, decimals: int
) -> str:
    return (
        rf"\frac{{{_stirling_even_product(m)}}}{{{k}!}}\,\delta^{{{k}}}y_0"
        rf" = ({format_num(coefficient, decimals)})"
        rf"({format_num(delta, decimals)})"
        rf" = {format_num(term, decimals)}"
    )


def _stirling_odd_latex(
    k: int,
    m: int,
    left: float,
    right: float,
    coefficient: float,
    term: float,
    decimals: int,
) -> str:
    symbol = r"p\,\mu\delta y_0" if k == 1 else (
        rf"\frac{{{_stirling_odd_product(m)}}}{{{k}!}}\,\mu\delta^{{{k}}}y_0"
    )
    return (
        rf"{symbol}"
        rf" = ({format_num(coefficient, decimals)})"
        rf"\left(\frac{{{format_num(left, decimals)}+{format_num(right, decimals)}}}{{2}}\right)"
        rf" = {format_num(term, decimals)}"
    )


def _bessel_even_latex(
    k: int, m: int, a: float, b: float, coefficient: float, term: float, decimals: int
) -> str:
    return (
        rf"\frac{{{_bessel_product(2 * m)}}}{{{k}!}}\,"
        rf"\frac{{\delta^{{{k}}}y_0+\delta^{{{k}}}y_1}}{{2}}"
        rf" = ({format_num(coefficient, decimals)})"
        rf"\left(\frac{{{format_num(a, decimals)}+{format_num(b, decimals)}}}{{2}}\right)"
        rf" = {format_num(term, decimals)}"
    )


def _bessel_odd_latex(
    k: int, m: int, delta: float, coefficient: float, term: float, decimals: int
) -> str:
    symbol = r"\left(p-\tfrac12\right)\,\delta y_{1/2}" if k == 1 else (
        rf"\left(p-\tfrac12\right)\frac{{{_bessel_product(2 * m)}}}{{{k}!}}\,\delta^{{{k}}}y_{{1/2}}"
    )
    return (
        rf"{symbol}"
        rf" = ({format_num(coefficient, decimals)})"
        rf"({format_num(delta, decimals)})"
        rf" = {format_num(term, decimals)}"
    )


def stirling_formula_latex(order: int) -> str:
    """The symbolic Stirling series up to ``order``."""
    parts = [r"y_0"]
    for k in range(1, order + 1):
        if k % 2 == 1:
            if k == 1:
                parts.append(r"p\,\mu\delta y_0")
            else:
                m = (k - 1) // 2
                parts.append(rf"\frac{{{_stirling_odd_product(m)}}}{{{k}!}}\,\mu\delta^{{{k}}}y_0")
        else:
            m = k // 2
            parts.append(rf"\frac{{{_stirling_even_product(m)}}}{{{k}!}}\,\delta^{{{k}}}y_0")
    return "P(x) = " + " + ".join(parts)


def bessel_formula_latex(order: int) -> str:
    parts = [r"\frac{y_0+y_1}{2}"]
    for k in range(1, order + 1):
        if k % 2 == 1:
            if k == 1:
                parts.append(r"\left(p-\tfrac12\right)\,\delta y_{1/2}")
            else:
                m = (k - 1) // 2
                parts.append(
                    rf"\left(p-\tfrac12\right)\frac{{{_bessel_product(2 * m)}}}{{{k}!}}"
                    rf"\,\delta^{{{k}}}y_{{1/2}}"
                )
        else:
            m = k // 2
            parts.append(
                rf"\frac{{{_bessel_product(2 * m)}}}{{{k}!}}\,"
                rf"\frac{{\delta^{{{k}}}y_0+\delta^{{{k}}}y_1}}{{2}}"
            )
    return "P(x) = " + " + ".join(parts)


def stirling_differences_latex(
    levels: list[list[float]], center: int, order: int, decimals: int
) -> str:
    parts: list[str] = []
    for k in range(1, order + 1):
        if k % 2 == 1:
            m = (k - 1) // 2
            mean = 0.5 * (levels[k][center - m - 1] + levels[k][center - m])
            symbol = r"\mu\delta y_0" if k == 1 else rf"\mu\delta^{{{k}}} y_0"
            parts.append(rf"{symbol} = {format_num(mean, decimals)}")
        else:
            m = k // 2
            parts.append(
                rf"\delta^{{{k}}} y_0 = {format_num(levels[k][center - m], decimals)}"
            )
    return r",\quad ".join(parts)


def bessel_differences_latex(
    levels: list[list[float]], center: int, order: int, decimals: int
) -> str:
    parts: list[str] = []
    for k in range(1, order + 1):
        if k % 2 == 1:
            m = (k - 1) // 2
            value = levels[k][center - m]
            symbol = r"\delta y_{1/2}" if k == 1 else rf"\delta^{{{k}}} y_{{1/2}}"
            parts.append(rf"{symbol} = {format_num(value, decimals)}")
        else:
            m = k // 2
            average = 0.5 * (levels[k][center - m] + levels[k][center + 1 - m])
            parts.append(
                rf"\frac{{\delta^{{{k}}} y_0+\delta^{{{k}}} y_1}}{{2}}"
                rf" = {format_num(average, decimals)}"
            )
    return r",\quad ".join(parts)


def signed_sum(values: list[float], decimals: int) -> str:
    """Render ``v0 + v1 - v2 ...`` with explicit signs for the working."""
    pieces: list[str] = []
    for index, value in enumerate(values):
        rendered = format_num(abs(value), decimals)
        if index == 0:
            pieces.append(f"-{rendered}" if value < 0 else rendered)
        else:
            pieces.append((" - " if value < 0 else " + ") + rendered)
    return "".join(pieces)


def target_evaluation_latex(
    target: float,
    base: float,
    step: float,
    p: float,
    terms_latex: list[str],
    term_values: list[float],
    decimals: int,
) -> str:
    """The ``p = ...`` then substituted-sum working for a single target."""
    p_line = (
        rf"p = \frac{{x - x_0}}{{h}} = "
        rf"\frac{{{format_num(target, decimals)} - {format_num(base, decimals)}}}"
        rf"{{{format_num(step, decimals)}}} = {format_num(p, decimals)}"
    )
    build = (
        rf"P\left({format_num(target, decimals)}\right) = " + " + ".join(terms_latex)
    )
    value_line = "= " + signed_sum(term_values, decimals)
    result_line = "= " + format_num(float(sum(term_values)), decimals)
    return r"\\[1mm]".join([p_line, build, value_line, result_line])


def stirling_region_warning(p: float) -> list[str]:
    if abs(p) > STIRLING_LIMIT:
        return [
            f"Stirling's formula is most accurate for |p| <= 0.25, but here p = {p:.6g}. "
            "Bessel's formula (0.25 <= p <= 0.75) is usually more accurate near the "
            "middle of the table."
        ]
    return []


def bessel_region_warning(p: float) -> list[str]:
    if p < BESSEL_LOW or p > BESSEL_HIGH:
        return [
            f"Bessel's formula is most accurate for 0.25 <= p <= 0.75, but here p = "
            f"{p:.6g}. Stirling's formula (|p| <= 0.25) is usually more accurate near "
            "a node."
        ]
    return []


__all__ = [
    "BESSEL_HIGH",
    "BESSEL_LOW",
    "STIRLING_LIMIT",
    "bessel_center",
    "bessel_differences_latex",
    "bessel_evaluate",
    "bessel_formula_latex",
    "bessel_region_warning",
    "center_field",
    "match_node",
    "order_field",
    "side_points",
    "signed_sum",
    "stirling_center",
    "stirling_differences_latex",
    "stirling_evaluate",
    "stirling_formula_latex",
    "stirling_region_warning",
    "target_evaluation_latex",
]
