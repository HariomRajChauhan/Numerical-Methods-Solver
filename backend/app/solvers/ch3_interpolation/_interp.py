"""Shared building blocks for the Chapter 3 interpolation solvers.

Private module (leading underscore) so the auto-loader skips it. It holds the
pieces common to the interpolation and curve-fitting methods: dataset
validation (sorting, duplicate detection, equal-spacing checks), the difference
tables, the Newton evaluation working, and the plotting helpers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.errors import InvalidInputError
from app.core.models import DataTable, InputField, PlotPayload, SolveResponse
from app.solvers._common import failed_response, format_num, points_trace

# Tolerance used when deciding whether x values are equally spaced.
SPACING_EPS = 1e-9

# A small demo dataset: y = x^2 + 1 through x = 0, 1, 2, 3.
DEFAULT_POINTS: list[list[float]] = [
    [0.0, 1.0],
    [1.0, 2.0],
    [2.0, 5.0],
    [3.0, 10.0],
]


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def data_points_field(
    *,
    default: list[list[float]] | None = None,
    help: str = "One point per row as 'x, y'; separate rows with ';' or new lines.",
) -> InputField:
    """The editable data table shared by every Chapter 3 method."""
    return InputField(
        key="points",
        label="Data points (x, y)",
        type="data_points",
        required=True,
        default=[list(point) for point in (default or DEFAULT_POINTS)],
        placeholder="0,1; 1,2; 2,5; 3,10",
        help=help,
    )


def targets_field(
    *,
    required: bool = True,
    default: Any = None,
    label: str = "Target x value(s)",
    help: str = "One or more x values to interpolate at, separated by commas.",
) -> InputField:
    """One or more x values at which to interpolate."""
    return InputField(
        key="targets",
        label=label,
        type="vector",
        required=required,
        default=default,
        placeholder="0.5",
        help=help,
    )


# ---------------------------------------------------------------------------
# Dataset preparation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Dataset:
    """A validated, ascending-x dataset."""

    xs: np.ndarray
    ys: np.ndarray
    notices: list[str]


def prepare_dataset(
    points: list[list[float]],
    *,
    min_points: int = 2,
    allow_repeats: bool = False,
) -> Dataset:
    """Validate the raw ``[[x, y], ...]`` points and sort them by x.

    Args:
        points: The raw ``[[x, y], ...]`` rows.
        min_points: The fewest points a method can work with.
        allow_repeats: When True, repeated x values are permitted (valid for
            curve fitting, where repeated measurements are meaningful).

    Raises:
        InvalidInputError: On too few points or, unless ``allow_repeats`` is set,
            repeated x values.
    """
    if len(points) < min_points:
        raise InvalidInputError(f"At least {min_points} data points are required.")
    xs = np.asarray([float(point[0]) for point in points], dtype=float)
    ys = np.asarray([float(point[1]) for point in points], dtype=float)
    order = np.argsort(xs, kind="stable")
    sorted_xs = xs[order]
    sorted_ys = ys[order]

    notices: list[str] = []
    if not allow_repeats:
        gaps = np.diff(sorted_xs)
        repeats = gaps == 0.0
        if bool(np.any(repeats)):
            repeated = float(sorted_xs[1:][repeats][0])
            raise InvalidInputError(
                f"The data points must have distinct x values, but x = {repeated:g} is repeated.",
                hint="Remove the duplicate point; two different y values at one x are not a function.",
            )
    else:
        gaps = np.diff(sorted_xs)
        if bool(np.any(gaps == 0.0)):
            notices.append(
                "The data set repeats one or more x values; every point is used in the fit, "
                "which is valid for least-squares but not for interpolation."
            )

    if not np.array_equal(order, np.arange(len(xs))):
        notices.append(
            "The data points were not listed in ascending order of x; they were sorted "
            "automatically before interpolating."
        )
    return Dataset(sorted_xs, sorted_ys, notices)


def require_targets(raw: Any) -> list[float]:
    """Return at least one target x, raising a friendly error when empty."""
    targets = [] if raw is None else [float(value) for value in raw]
    if not targets:
        raise InvalidInputError("At least one target x value is required.")
    return targets


# ---------------------------------------------------------------------------
# Spacing
# ---------------------------------------------------------------------------


def step_sizes(xs: np.ndarray) -> np.ndarray:
    """The successive gaps ``x_{i+1} - x_i``."""
    return np.diff(np.asarray(xs, dtype=float))


def common_step(xs: np.ndarray) -> float:
    """The first gap (the common step when the nodes are equally spaced)."""
    gaps = step_sizes(xs)
    return float(gaps[0]) if gaps.size else 0.0


def is_equal_spacing(xs: np.ndarray, *, tolerance: float = SPACING_EPS) -> bool:
    """True when every gap equals the first (within a relative tolerance)."""
    gaps = step_sizes(xs)
    if gaps.size <= 1:
        return True
    scale = max(1.0, float(np.max(np.abs(gaps))))
    return bool(np.all(np.abs(gaps - gaps[0]) <= tolerance * scale))


def spacing_failure(method_id: str, xs: np.ndarray, decimals: int) -> SolveResponse:
    """A HTTP-200 ``failed`` response for a method that needs equal spacing."""
    gaps = step_sizes(xs)
    shown = ", ".join(f"{float(gap):.6g}" for gap in gaps)
    message = (
        "This method needs equally spaced x values, but the steps between the "
        f"given points are {shown}. Use the divided-difference or Lagrange method, "
        "which accept uneven spacing."
    )
    return failed_response(method_id, message)


def spacing_note(xs: np.ndarray) -> list[str]:
    """A warning when a difference operator is applied to uneven spacing."""
    if is_equal_spacing(xs):
        return []
    return [
        "The x values are not equally spaced; the difference table is still valid, but "
        "the equal-spacing interpolation formulas (Newton forward/backward, Stirling, "
        "Bessel) require a constant step."
    ]


# ---------------------------------------------------------------------------
# Extrapolation and region warnings
# ---------------------------------------------------------------------------


def extrapolation_warnings(targets: list[float], xs: np.ndarray) -> list[str]:
    """Warn for every target that lies outside the tabulated range."""
    lo = float(xs[0])
    hi = float(xs[-1])
    outside = [target for target in targets if target < lo or target > hi]
    if not outside:
        return []
    shown = ", ".join(f"{target:g}" for target in outside)
    return [
        f"Target x = {shown} lies outside the data range [{lo:g}, {hi:g}], so the "
        "value is an extrapolation and may be inaccurate."
    ]


def forward_region_warning(p: float, count: int) -> list[str]:
    """Warn when a forward formula is used near the lower part of the table."""
    if count >= 3 and p > (count - 1) / 2.0:
        return [
            "The target lies towards the end of the table (p = "
            f"{p:.6g}); Newton's backward formula is usually more accurate there."
        ]
    return []


def backward_region_warning(p: float, count: int) -> list[str]:
    """Warn when a backward formula is used near the upper part of the table."""
    if count >= 3 and p < -(count - 1) / 2.0:
        return [
            "The target lies towards the start of the table (p = "
            f"{p:.6g}); Newton's forward formula is usually more accurate there."
        ]
    return []


def high_degree_warning(count: int, *, limit: int = 10) -> list[str]:
    """Warn when a single high-degree polynomial is fitted through many points."""
    if count <= limit:
        return []
    return [
        f"A single polynomial through {count} points has degree {count - 1}. High-degree "
        "interpolation can oscillate badly between the nodes (Runge's phenomenon); a "
        "spline or a least-squares fit is usually safer."
    ]


# ---------------------------------------------------------------------------
# Difference tables
# ---------------------------------------------------------------------------


def _cell(value: float | None, decimals: int) -> str:
    if value is None:
        return ""
    number = float(value)
    if not math.isfinite(number):
        return ""
    return format_num(number, decimals)


def _marked(text: str, mark: bool) -> str:
    return f"{text} *" if mark and text else text


def forward_differences(ys: np.ndarray) -> list[list[float]]:
    """``table[i][k] = Delta^k y_i`` (defined for ``i + k <= n - 1``)."""
    size = len(ys)
    table = [[math.nan] * size for _ in range(size)]
    for i in range(size):
        table[i][0] = float(ys[i])
    for k in range(1, size):
        for i in range(size - k):
            table[i][k] = table[i + 1][k - 1] - table[i][k - 1]
    return table


def backward_differences(ys: np.ndarray) -> list[list[float]]:
    """``table[i][k] = nabla^k y_i`` (defined for ``i >= k``)."""
    size = len(ys)
    table = [[math.nan] * size for _ in range(size)]
    for i in range(size):
        table[i][0] = float(ys[i])
    for k in range(1, size):
        for i in range(k, size):
            table[i][k] = table[i][k - 1] - table[i - 1][k - 1]
    return table


def central_differences(ys: np.ndarray) -> list[list[float]]:
    """Central differences as levels: ``levels[k][i]`` is ``delta^k`` at offset i."""
    size = len(ys)
    levels: list[list[float]] = [[float(value) for value in ys]]
    for k in range(1, size):
        previous = levels[k - 1]
        levels.append([previous[i + 1] - previous[i] for i in range(len(previous) - 1)])
    return levels


def divided_differences(xs: np.ndarray, ys: np.ndarray) -> list[list[float]]:
    """``table[i][k] = f[x_i, ..., x_{i+k}]`` (defined for ``i + k <= n - 1``)."""
    size = len(ys)
    table = [[math.nan] * size for _ in range(size)]
    for i in range(size):
        table[i][0] = float(ys[i])
    for k in range(1, size):
        for i in range(size - k):
            denominator = float(xs[i + k] - xs[i])
            table[i][k] = (table[i + 1][k - 1] - table[i][k - 1]) / denominator
    return table


def forward_leading(ys: np.ndarray) -> list[float]:
    """The leading forward differences ``Delta^k y_0`` for every order."""
    table = forward_differences(ys)
    return [table[0][k] for k in range(len(ys))]


def backward_leading(ys: np.ndarray) -> list[float]:
    """The backward differences ``nabla^k y_{n-1}``."""
    table = backward_differences(ys)
    last = len(ys) - 1
    return [table[last][k] for k in range(len(ys))]


def central_leading(ys: np.ndarray) -> list[float]:
    """The central-difference diagonal closest to the middle of the table."""
    levels = central_differences(ys)
    leading: list[float] = []
    for level in levels:
        index = (len(level) - 1) // 2
        leading.append(float(level[index]))
    return leading


def divided_leading(xs: np.ndarray, ys: np.ndarray) -> list[float]:
    """The divided differences ``f[x_0, ..., x_k]`` (top diagonal)."""
    table = divided_differences(xs, ys)
    return [table[0][k] for k in range(len(ys))]


def difference_table(
    xs: np.ndarray,
    ys: np.ndarray,
    kind: str,
    decimals: int,
) -> DataTable:
    """Render the requested difference table, marking the diagonal in use."""
    size = len(ys)
    x_cells = [format_num(float(xs[i]), decimals) for i in range(size)]
    y_cells = [format_num(float(ys[i]), decimals) for i in range(size)]

    if kind == "forward":
        table = forward_differences(ys)
        columns = ["i", "x_i", "y_i", *[f"Dy{k}" if k > 1 else "Dy" for k in range(1, size)]]
        rows: list[list[Any]] = []
        for i in range(size):
            cells: list[Any] = [i, x_cells[i], y_cells[i]]
            for k in range(1, size):
                defined = i + k <= size - 1
                cells.append(_marked(_cell(table[i][k], decimals) if defined else "", i == 0))
            rows.append(cells)
        return DataTable(
            title="Forward difference table (D = Delta)",
            columns=columns,
            rows=rows,
        )

    if kind == "backward":
        table = backward_differences(ys)
        columns = ["i", "x_i", "y_i", *[f"Ny{k}" if k > 1 else "Ny" for k in range(1, size)]]
        rows = []
        for i in range(size):
            cells = [i, x_cells[i], y_cells[i]]
            for k in range(1, size):
                defined = i >= k
                cells.append(
                    _marked(_cell(table[i][k], decimals) if defined else "", i == size - 1)
                )
            rows.append(cells)
        return DataTable(
            title="Backward difference table (N = nabla)",
            columns=columns,
            rows=rows,
        )

    if kind == "divided":
        table = divided_differences(xs, ys)
        columns = ["i", "x_i", "y_i", *[f"DD{k}" for k in range(1, size)]]
        rows = []
        for i in range(size):
            cells = [i, x_cells[i], y_cells[i]]
            for k in range(1, size):
                defined = i + k <= size - 1
                cells.append(_marked(_cell(table[i][k], decimals) if defined else "", i == 0))
            rows.append(cells)
        return DataTable(
            title="Divided difference table",
            columns=columns,
            rows=rows,
        )

    levels = central_differences(ys)
    columns = ["Order", *[f"x_{j}" if j < size else "mid" for j in range(size)]]
    rows = []
    for order, level in enumerate(levels):
        cells = [f"C{order}"]
        index = (len(level) - 1) // 2
        for position, value in enumerate(level):
            cells.append(_marked(_cell(value, decimals), position == index))
        rows.append(cells)
    return DataTable(
        title="Central difference table (C = delta)",
        columns=columns,
        rows=rows,
    )


def central_table(
    xs: np.ndarray,
    ys: np.ndarray,
    decimals: int,
    marked: set[tuple[int, int]] | None = None,
) -> DataTable:
    """Central difference table with the entries used by the chosen formula flagged."""
    levels = central_differences(ys)
    size = len(ys)
    columns = ["Order", *[f"x_{j}" if j < size else "mid" for j in range(size)]]
    rows = []
    for order, level in enumerate(levels):
        cells: list[object] = [f"C{order}"]
        for position, value in enumerate(level):
            mark = marked is not None and (order, position) in marked
            cells.append(_marked(_cell(value, decimals), mark))
        rows.append(cells)
    return DataTable(
        title="Central difference table (* = entries used, C = delta)",
        columns=columns,
        rows=rows,
    )


def node_table(xs: np.ndarray, ys: np.ndarray, decimals: int) -> DataTable:
    """The list of data points with their indices."""
    rows = [
        [i, format_num(float(xs[i]), decimals), format_num(float(ys[i]), decimals)]
        for i in range(len(xs))
    ]
    return DataTable(title="Data points", columns=["i", "x_i", "y_i"], rows=rows)


def value_table(
    targets: list[float],
    values: list[float],
    decimals: int,
    title: str = "Target evaluations",
) -> DataTable:
    """Target x values next to the interpolated value."""
    rows = [
        [format_num(float(target), decimals), format_num(float(value), decimals)]
        for target, value in zip(targets, values, strict=True)
    ]
    return DataTable(title=title, columns=["x", "P(x)"], rows=rows)


# ---------------------------------------------------------------------------
# Newton working (forward and backward)
# ---------------------------------------------------------------------------


def newton_polynomial_latex(
    coefficients: list[float],
    decimals: int,
    *,
    backward: bool,
) -> str:
    """The symbolic Newton form ``P(x) = ...`` with symbolic p."""
    parts = [format_num(float(coefficients[0]), decimals)]
    for k in range(1, len(coefficients)):
        coefficient = float(coefficients[k])
        if abs(coefficient) < 1e-14:
            continue
        product = "".join(
            "p" if j == 0 else (f"(p+{j})" if backward else f"(p-{j})") for j in range(k)
        )
        shown = format_num(coefficient, decimals)
        if k == 1:
            parts.append(rf"{shown}\,{product}")
        else:
            parts.append(rf"\frac{{{shown}}}{{{math.factorial(k)}}}{product}")
    return r"P(x) = " + " + ".join(parts)


def newton_evaluation_latex(
    *,
    coefficients: list[float],
    base_x: float,
    step: float,
    target: float,
    decimals: int,
    backward: bool,
) -> tuple[str, float]:
    """Exam-style substitution of one Newton formula at ``target``.

    Returns:
        ``(latex, value)``.
    """
    p = (target - base_x) / step if step != 0 else math.nan
    terms_latex = [format_num(float(coefficients[0]), decimals)]
    term_values = [float(coefficients[0])]
    for k in range(1, len(coefficients)):
        factors = [
            f"({format_num(p + j if backward else p - j, decimals)})" for j in range(k)
        ]
        product = math.prod((p + j) if backward else (p - j) for j in range(k))
        term_value = float(coefficients[k]) * product / math.factorial(k)
        term_values.append(term_value)
        term_latex = (
            f"\\frac{{{''.join(factors)}}}{{{math.factorial(k)}}}"
            f"\\left({format_num(float(coefficients[k]), decimals)}\\right)"
        )
        terms_latex.append(term_latex)

    value = float(sum(term_values))
    subscript = _sub_label(backward)
    p_line = (
        f"p = \\frac{{x - x_{{{subscript}}}}}{{h}} = "
        f"\\frac{{{format_num(target, decimals)} - {format_num(base_x, decimals)}}}"
        f"{{{format_num(step, decimals)}}} = {format_num(p, decimals)}"
    )

    build = (
        f"P\\left({format_num(target, decimals)}\\right) = "
        + " + ".join(terms_latex)
    )
    value_line = "= " + _signed_sum(term_values, decimals)
    result_line = "= " + format_num(value, decimals)
    return r"\\[1mm]".join([p_line, build, value_line, result_line]), value


def _sub_label(backward: bool) -> str:
    return "n" if backward else "0"


def _signed_sum(values: list[float], decimals: int) -> str:
    pieces: list[str] = []
    for index, value in enumerate(values):
        rendered = format_num(abs(value), decimals)
        if index == 0:
            pieces.append(f"-{rendered}" if value < 0 else rendered)
        else:
            pieces.append((" - " if value < 0 else " + ") + rendered)
    return "".join(pieces)


# ---------------------------------------------------------------------------
# Newton divided-difference working
# ---------------------------------------------------------------------------


def divided_coefficients_latex(coefficients: list[float], decimals: int) -> str:
    """The divided differences on the top diagonal, written ``f[x0, ..., x_k]``."""
    parts = [rf"f[x_0] = {format_num(float(coefficients[0]), decimals)}"]
    for k in range(1, len(coefficients)):
        nodes = ", ".join(f"x_{j}" for j in range(k + 1))
        parts.append(rf"f[{nodes}] = {format_num(float(coefficients[k]), decimals)}")
    return r",\quad ".join(parts)


def divided_polynomial_latex(
    coefficients: list[float], xs: np.ndarray, decimals: int
) -> str:
    """The symbolic Newton divided-difference form ``P(x) = ...``."""
    pieces = [format_num(float(coefficients[0]), decimals)]
    for k in range(1, len(coefficients)):
        coefficient = float(coefficients[k])
        if abs(coefficient) < 1e-14:
            continue
        factors = "".join(
            rf"\left(x - {format_num(float(xs[j]), decimals)}\right)" for j in range(k)
        )
        body = rf"{format_num(abs(coefficient), decimals)}{factors}"
        pieces.append((" - " if coefficient < 0 else " + ") + body)
    return r"P(x) = " + "".join(pieces)


def divided_evaluation_latex(
    *,
    coefficients: list[float],
    xs: np.ndarray,
    target: float,
    decimals: int,
) -> tuple[str, float]:
    """Exam-style substitution of the Newton divided-difference form.

    Shows each term ``(x - x_0)(x - x_1)...`` with substituted factor values, the
    running partial sums and the final value.

    Returns:
        ``(latex, value)``.
    """
    count = len(coefficients)
    symbol_terms = [format_num(float(coefficients[0]), decimals)]
    terms: list[float] = [float(coefficients[0])]
    factors_shown = [
        rf"\left({format_num(target, decimals)} - {format_num(float(xs[j]), decimals)}\right)"
        for j in range(count - 1)
    ]

    for k in range(1, count):
        coefficient = float(coefficients[k])
        product = math.prod(target - float(xs[j]) for j in range(k))
        terms.append(coefficient * product)
        product_latex = "".join(factors_shown[:k])
        body = rf"\left({format_num(abs(coefficient), decimals)}\right){product_latex}"
        if k == 1:
            body = rf"{format_num(abs(coefficient), decimals)}\,{product_latex}"
        symbol_terms.append((" - " if coefficient < 0 else " + ") + body)

    value = float(sum(terms))
    partial = ", ".join(
        format_num(float(part), decimals) for part in np.cumsum(terms)
    )

    build = (
        rf"P\left({format_num(target, decimals)}\right) = " + "".join(symbol_terms)
    )
    value_line = "= " + _signed_sum(terms, decimals)
    running_line = r"\text{running sums } = " + partial
    result_line = "= " + format_num(value, decimals)
    return r"\\[1mm]".join([build, value_line, running_line, result_line]), value


def expanded_polynomial_latex(
    xs: np.ndarray, ys: np.ndarray, decimals: int
) -> str:
    """The interpolating polynomial expanded into powers of x, using SymPy."""
    import sympy as sp

    x = sp.Symbol("x")
    nodes = [(float(xi), float(yi)) for xi, yi in zip(xs, ys, strict=True)]
    expanded = sp.expand(sp.interpolate(nodes, x))
    coefficients = sp.Poly(expanded, x).all_coeffs()
    degree = len(coefficients) - 1
    pieces: list[str] = []
    for index, coefficient in enumerate(coefficients):
        value = float(coefficient)
        if abs(value) < 1e-12:
            continue
        power = degree - index
        magnitude = format_num(abs(value), decimals)
        if power == 0:
            body = magnitude
        elif power == 1:
            body = rf"{magnitude}\,x"
        else:
            body = rf"{magnitude}\,x^{{{power}}}"
        if not pieces:
            pieces.append(body if value >= 0 else f"-{body}")
        else:
            pieces.append((" - " if value < 0 else " + ") + body)
    if not pieces:
        return r"P(x) = 0"
    return r"P(x) = " + "".join(pieces)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def interpolating_curve(
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    targets: list[float] | None = None,
    points: int = 300,
) -> tuple[list[float], list[float | None]]:
    """Sample the unique interpolating polynomial through the data."""
    degree = len(xs) - 1
    if degree < 1:
        return [], []
    coefficients = np.polyfit(xs, ys, degree)
    lo = float(np.min(xs))
    hi = float(np.max(xs))
    if targets:
        lo = min(lo, min(targets))
        hi = max(hi, max(targets))
    pad = 0.05 * (hi - lo) if hi > lo else 0.5
    grid = np.linspace(lo - pad, hi + pad, points)
    sampled = np.polyval(coefficients, grid)
    series = [float(value) if math.isfinite(float(value)) else None for value in sampled]
    return grid.tolist(), series


def interpolation_plot(
    *,
    xs: np.ndarray,
    ys: np.ndarray,
    curve: tuple[list[float], list[float | None]] | None = None,
    targets: list[float] | None = None,
    target_values: list[float] | None = None,
    title: str,
) -> PlotPayload:
    """Data points, the interpolating curve and the highlighted targets."""
    traces: list[dict[str, Any]] = [points_trace(list(xs), list(ys), "Data points")]
    if curve and curve[0]:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Interpolating polynomial",
                "x": curve[0],
                "y": curve[1],
            }
        )
    if targets and target_values:
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": "Target",
                "x": list(targets),
                "y": list(target_values),
                "marker": {"color": "#dc2626", "size": 11, "symbol": "diamond"},
            }
        )
    layout = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "y"}},
    }
    return PlotPayload(traces=traces, layout=layout)


def overlay_plot(
    *,
    xs: np.ndarray,
    ys: np.ndarray,
    curves: list[tuple[str, tuple[list[float], list[float | None]]]],
    targets: list[float] | None = None,
    target_values: list[float] | None = None,
    title: str,
    curve_colors: list[str] | None = None,
) -> PlotPayload:
    """Data points with several named curves overlaid (used by the compare view)."""
    traces: list[dict[str, Any]] = [points_trace(list(xs), list(ys), "Data points")]
    colors = curve_colors or ["#2563eb", "#16a34a", "#9333ea", "#ea580c"]
    dashes = ["solid", "dash", "dot", "dashdot"]
    for index, (name, (grid_x, grid_y)) in enumerate(curves):
        if not grid_x:
            continue
        trace: dict[str, Any] = {
            "type": "scatter",
            "mode": "lines",
            "name": name,
            "x": grid_x,
            "y": grid_y,
            "line": {
                "color": colors[index % len(colors)],
                "dash": dashes[index % len(dashes)],
            },
        }
        traces.append(trace)
    if targets and target_values:
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": "Target",
                "x": list(targets),
                "y": list(target_values),
                "marker": {"color": "#dc2626", "size": 11, "symbol": "diamond"},
            }
        )
    layout = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "y"}},
    }
    return PlotPayload(traces=traces, layout=layout)
