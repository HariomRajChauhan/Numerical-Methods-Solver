"""Shared building blocks for cubic-spline interpolation.

Private module (leading underscore) so the auto-loader skips it. It builds the
tridiagonal system for the second derivatives ``M_i`` (natural or clamped
boundary conditions), solves it with the Thomas algorithm, forms the
piecewise-cubic coefficients, and provides the tables, LaTeX working and plot
used by the solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.models import DataTable, PlotPayload
from app.solvers._common import format_num, points_trace

NATURAL = "natural"
CLAMPED = "clamped"

# One colour per interval so each cubic piece is visually distinct.
PIECE_COLORS = [
    "#2563eb",
    "#16a34a",
    "#9333ea",
    "#ea580c",
    "#0891b2",
    "#db2777",
    "#65a30d",
    "#7c3aed",
    "#f59e0b",
    "#0ea5e9",
]

# The largest system rendered as a full matrix in the working step.
MATRIX_CAP = 12

# Samples drawn on each interval for a smooth piecewise plot.
POINTS_PER_INTERVAL = 60


class SplineError(Exception):
    """A mathematical breakdown (e.g. a singular tridiagonal system)."""


@dataclass(frozen=True)
class SplineSystem:
    """A fully determined cubic spline: the nodes, the M_i and the cubics."""

    xs: np.ndarray
    ys: np.ndarray
    h: np.ndarray
    boundary: str
    lower: np.ndarray
    diag: np.ndarray
    upper: np.ndarray
    rhs: np.ndarray
    c_prime: np.ndarray
    d_prime: np.ndarray
    m: np.ndarray
    a: np.ndarray
    b: np.ndarray
    c: np.ndarray
    d: np.ndarray

    @property
    def intervals(self) -> int:
        return len(self.xs) - 1


def _as_float(value: Any) -> float:
    return float(value)


# ---------------------------------------------------------------------------
# System assembly
# ---------------------------------------------------------------------------


def thomas(
    lower: np.ndarray,
    diag: np.ndarray,
    upper: np.ndarray,
    rhs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Solve a tridiagonal system with the Thomas algorithm.

    Returns:
        ``(M, c_prime, d_prime)`` where ``c_prime``/``d_prime`` are the modified
        upper diagonal and right-hand side produced by the forward sweep.

    Raises:
        SplineError: When a pivot vanishes (a singular system).
    """
    size = len(diag)
    c_prime = np.zeros(size)
    d_prime = np.zeros(size)
    c_prime[0] = upper[0] / diag[0]
    d_prime[0] = rhs[0] / diag[0]
    for i in range(1, size):
        denominator = diag[i] - lower[i] * c_prime[i - 1]
        if denominator == 0.0:
            raise SplineError(
                "The tridiagonal system is singular; check the data for repeated x values."
            )
        c_prime[i] = upper[i] / denominator
        d_prime[i] = (rhs[i] - lower[i] * d_prime[i - 1]) / denominator
    solution = np.zeros(size)
    solution[-1] = d_prime[-1]
    for i in range(size - 2, -1, -1):
        solution[i] = d_prime[i] - c_prime[i] * solution[i + 1]
    return solution, c_prime, d_prime


def build_system(
    xs: np.ndarray,
    ys: np.ndarray,
    boundary: str,
    left_derivative: float = 0.0,
    right_derivative: float = 0.0,
) -> SplineSystem:
    """Assemble and solve the M_i system, then form the piecewise cubics.

    The system always has ``n + 1`` unknowns ``M_0, ..., M_n`` (one per node):
    the interior rows come from the derivative-continuity condition and the two
    boundary rows encode the natural (``M = 0``) or clamped (prescribed slope)
    condition.

    Raises:
        SplineError: If the system turns out to be singular.
    """
    size = len(xs)
    h = np.diff(xs)
    lower = np.zeros(size)
    diag = np.zeros(size)
    upper = np.zeros(size)
    rhs = np.zeros(size)

    if boundary == CLAMPED:
        diag[0] = 2.0 * h[0]
        upper[0] = h[0]
        rhs[0] = 6.0 * ((ys[1] - ys[0]) / h[0] - left_derivative)
        lower[-1] = h[-1]
        diag[-1] = 2.0 * h[-1]
        rhs[-1] = 6.0 * (right_derivative - (ys[-1] - ys[-2]) / h[-1])
    else:
        diag[0] = 1.0
        diag[-1] = 1.0

    for i in range(1, len(xs) - 1):
        lower[i] = h[i - 1]
        diag[i] = 2.0 * (h[i - 1] + h[i])
        upper[i] = h[i]
        rhs[i] = 6.0 * ((ys[i + 1] - ys[i]) / h[i] - (ys[i] - ys[i - 1]) / h[i - 1])

    m, c_prime, d_prime = thomas(lower, diag, upper, rhs)

    a = ys[:-1].copy()
    b = (ys[1:] - ys[:-1]) / h - h * (2.0 * m[:-1] + m[1:]) / 6.0
    c = m[:-1] / 2.0
    d = (m[1:] - m[:-1]) / (6.0 * h)

    return SplineSystem(
        xs=np.asarray(xs, dtype=float),
        ys=np.asarray(ys, dtype=float),
        h=np.asarray(h, dtype=float),
        boundary=boundary,
        lower=lower,
        diag=diag,
        upper=upper,
        rhs=rhs,
        c_prime=c_prime,
        d_prime=d_prime,
        m=m,
        a=a,
        b=b,
        c=c,
        d=d,
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def interval_index(xs: np.ndarray, target: float) -> int:
    """The interval ``i`` with ``xs[i] <= target <= xs[i+1]`` (clamped at the ends)."""
    last = len(xs) - 1
    if target <= float(xs[0]):
        return 0
    if target >= float(xs[last]):
        return last - 1
    return int(np.searchsorted(xs, target, side="right") - 1)


def evaluate(spline: SplineSystem, target: float) -> tuple[float, int, bool]:
    """Return ``(S(target), interval_index, extrapolated)``."""
    index = interval_index(spline.xs, target)
    dx = target - _as_float(spline.xs[index])
    value = (
        _as_float(spline.a[index])
        + _as_float(spline.b[index]) * dx
        + _as_float(spline.c[index]) * dx * dx
        + _as_float(spline.d[index]) * dx * dx * dx
    )
    extrapolated = target < _as_float(spline.xs[0]) or target > _as_float(spline.xs[-1])
    return float(value), index, bool(extrapolated)


def derivative_value(spline: SplineSystem, target: float, order: int) -> float:
    """The ``order``-th derivative of the spline at ``target`` (1 or 2)."""
    index = interval_index(spline.xs, target)
    dx = target - _as_float(spline.xs[index])
    b = _as_float(spline.b[index])
    c = _as_float(spline.c[index])
    d = _as_float(spline.d[index])
    if order == 1:
        return float(b + 2.0 * c * dx + 3.0 * d * dx * dx)
    return float(2.0 * c + 6.0 * d * dx)


def _piece_bounds(
    spline: SplineSystem,
    targets: list[float],
) -> tuple[float, float]:
    lo = _as_float(spline.xs[0])
    hi = _as_float(spline.xs[-1])
    if targets:
        lo = min(lo, min(targets))
        hi = max(hi, max(targets))
    return lo, hi


def piecewise_grid(
    spline: SplineSystem,
    *,
    lo: float | None = None,
    hi: float | None = None,
    points: int = POINTS_PER_INTERVAL,
    order: int = 0,
) -> list[tuple[int, list[float], list[float]]]:
    """Dense samples of piece ``i`` over its own interval (ends extended on request)."""
    pieces: list[tuple[int, list[float], list[float]]] = []
    count = spline.intervals
    for i in range(count):
        left = _as_float(spline.xs[i])
        right = _as_float(spline.xs[i + 1])
        if i == 0 and lo is not None and lo < left:
            left = lo
        if i == count - 1 and hi is not None and hi > right:
            right = hi
        grid = np.linspace(left, right, points)
        if order == 0:
            values = [
                float(
                    _as_float(spline.a[i])
                    + _as_float(spline.b[i]) * (x - _as_float(spline.xs[i]))
                    + _as_float(spline.c[i]) * (x - _as_float(spline.xs[i])) ** 2
                    + _as_float(spline.d[i]) * (x - _as_float(spline.xs[i])) ** 3
                )
                for x in grid
            ]
        else:
            values = [derivative_value_interval(spline, i, float(x), order) for x in grid]
        pieces.append((i, grid.tolist(), [float(value) for value in values]))
    return pieces


def derivative_value_interval(
    spline: SplineSystem,
    index: int,
    target: float,
    order: int,
) -> float:
    """The ``order``-th derivative using a *specific* interval (for knot limits)."""
    dx = target - _as_float(spline.xs[index])
    b = _as_float(spline.b[index])
    c = _as_float(spline.c[index])
    d = _as_float(spline.d[index])
    if order == 1:
        return float(b + 2.0 * c * dx + 3.0 * d * dx * dx)
    return float(2.0 * c + 6.0 * d * dx)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def _cell(value: float, decimals: int) -> str:
    return format_num(float(value), decimals)


def spacing_table(spline: SplineSystem, decimals: int) -> DataTable:
    """The interval widths ``h_i`` and the first divided differences."""
    rows: list[list[Any]] = []
    count = len(spline.xs)
    for i in range(count):
        if i < count - 1:
            slope = (float(spline.ys[i + 1]) - float(spline.ys[i])) / float(spline.h[i])
            rows.append(
                [
                    i,
                    _cell(float(spline.xs[i]), decimals),
                    _cell(float(spline.ys[i]), decimals),
                    _cell(float(spline.h[i]), decimals),
                    _cell(slope, decimals),
                ]
            )
        else:
            rows.append([i, _cell(float(spline.xs[i]), decimals), _cell(float(spline.ys[i]), decimals), "", ""])
    return DataTable(
        title="Interval steps and first divided differences",
        columns=["i", "x_i", "y_i", "h_i", "f[x_i, x_{i+1}]"],
        rows=rows,
    )


def system_table(spline: SplineSystem, decimals: int) -> DataTable:
    """The tridiagonal system for the ``M_i`` as a filled-in augmented matrix."""
    rows: list[list[Any]] = []
    for i in range(len(spline.diag)):
        rows.append(
            [
                i,
                _cell(float(spline.lower[i]), decimals),
                _cell(float(spline.diag[i]), decimals),
                _cell(float(spline.upper[i]), decimals),
                _cell(float(spline.rhs[i]), decimals),
            ]
        )
    return DataTable(
        title="Tridiagonal system for the second derivatives M_i",
        columns=["i", "M_{i-1}", "M_i", "M_{i+1}", "RHS"],
        rows=rows,
    )


def thomas_table(spline: SplineSystem, decimals: int) -> DataTable:
    """The Thomas forward-sweep arrays ``c'_i`` and ``d'_i``."""
    rows = [
        [i, _cell(float(spline.c_prime[i]), decimals), _cell(float(spline.d_prime[i]), decimals)]
        for i in range(len(spline.d_prime))
    ]
    return DataTable(
        title="Thomas algorithm (forward sweep)",
        columns=["i", "c'_i", "d'_i"],
        rows=rows,
    )


def second_derivatives_table(spline: SplineSystem, decimals: int) -> DataTable:
    """The solved second derivatives at every node."""
    rows = [
        [i, _cell(float(spline.xs[i]), decimals), _cell(float(spline.m[i]), decimals)]
        for i in range(len(spline.m))
    ]
    return DataTable(
        title="Second derivatives M_i",
        columns=["i", "x_i", "M_i"],
        rows=rows,
    )


def coefficients_table(spline: SplineSystem, decimals: int) -> DataTable:
    """The coefficients ``a_i, b_i, c_i, d_i`` of each cubic piece."""
    rows: list[list[Any]] = []
    for i in range(spline.intervals):
        interval = (
            "[" + _cell(float(spline.xs[i]), decimals) + ", "
            + _cell(float(spline.xs[i + 1]), decimals) + "]"
        )
        rows.append(
            [
                i,
                interval,
                _cell(float(spline.a[i]), decimals),
                _cell(float(spline.b[i]), decimals),
                _cell(float(spline.c[i]), decimals),
                _cell(float(spline.d[i]), decimals),
            ]
        )
    return DataTable(
        title="Piecewise cubic coefficients (S_i = a_i + b_i t + c_i t^2 + d_i t^3, t = x - x_i)",
        columns=["i", "interval", "a_i", "b_i", "c_i", "d_i"],
        rows=rows,
    )


def second_derivatives_series(spline: SplineSystem) -> list[float]:
    """The ``M_i`` as plain floats (for the result payload)."""
    return [float(value) for value in spline.m]


def coefficients_series(spline: SplineSystem) -> list[dict[str, float]]:
    """The per-interval coefficients as plain floats."""
    return [
        {
            "interval": i,
            "a": float(spline.a[i]),
            "b": float(spline.b[i]),
            "c": float(spline.c[i]),
            "d": float(spline.d[i]),
        }
        for i in range(spline.intervals)
    ]


def evaluation_table(
    targets: list[float],
    values: list[float],
    intervals: list[int],
    extrapolated: list[bool],
    decimals: int,
) -> DataTable:
    """The evaluation at every target, naming the interval that was used."""
    rows: list[list[Any]] = []
    for target, value, index, outside in zip(
        targets, values, intervals, extrapolated, strict=True
    ):
        rows.append(
            [
                _cell(float(target), decimals),
                index,
                _cell(float(value), decimals),
                "yes" if outside else "",
            ]
        )
    return DataTable(
        title="Evaluations (S(x) and the interval used)",
        columns=["x", "interval i", "S(x)", "extrapolated"],
        rows=rows,
    )


# ---------------------------------------------------------------------------
# LaTeX working
# ---------------------------------------------------------------------------


def spacing_latex(spline: SplineSystem, decimals: int) -> str:
    lines = [
        rf"h_{{{i}}} = x_{{{i + 1}}} - x_{{{i}}} = {_cell(float(spline.h[i]), decimals)}"
        for i in range(spline.intervals)
    ]
    return r"\\[1mm]".join(lines)


def boundary_latex(spline: SplineSystem, decimals: int) -> str:
    if spline.boundary == CLAMPED:
        return r"\text{clamped: } S'(x_0),\ S'(x_n) \text{ prescribed}"
    return r"\text{natural: } M_0 = M_n = 0"


def system_latex(spline: SplineSystem, decimals: int) -> str:
    """The tridiagonal system as an augmented matrix (capped for large systems)."""
    size = len(spline.diag)
    if size > MATRIX_CAP:
        return (
            r"\text{tridiagonal system of size } "
            + f"{size}"
            + r"\text{ (see the system table for every entry)}"
        )

    def entry(i: int, j: int) -> str:
        if j == i:
            return _cell(float(spline.diag[i]), decimals)
        if j == i - 1:
            return _cell(float(spline.lower[i]), decimals)
        if j == i + 1:
            return _cell(float(spline.upper[i]), decimals)
        return "0"

    left = [r" & ".join(entry(i, j) for j in range(size)) for i in range(size)]
    matrix = r"\begin{bmatrix}" + r" \\ ".join(left) + r"\end{bmatrix}"
    m_vector = (
        r"\begin{bmatrix}"
        + r" \\ ".join(f"M_{{{i}}}" for i in range(size))
        + r"\end{bmatrix}"
    )
    rhs_vector = (
        r"\begin{bmatrix}"
        + r" \\ ".join(_cell(float(spline.rhs[i]), decimals) for i in range(size))
        + r"\end{bmatrix}"
    )
    return matrix + m_vector + " = " + rhs_vector


def thomas_latex(spline: SplineSystem, decimals: int) -> str:
    forward = (
        r"c'_i = \frac{u_i}{d_i - l_i c'_{i-1}},\qquad "
        r"d'_i = \frac{r_i - l_i d'_{i-1}}{d_i - l_i c'_{i-1}}"
    )
    backward = r"M_i = d'_i - c'_i\,M_{i+1},\qquad M_n = d'_n"
    return forward + r"\\[1mm]" + backward


def second_derivatives_latex(spline: SplineSystem, decimals: int) -> str:
    terms = [
        rf"M_{{{i}}} = {_cell(float(spline.m[i]), decimals)}"
        for i in range(len(spline.m))
    ]
    return r",\quad ".join(terms)


def piecewise_latex(spline: SplineSystem, decimals: int) -> str:
    lines: list[str] = []
    for i in range(spline.intervals):
        x_i = _cell(float(spline.xs[i]), decimals)
        lines.append(
            rf"S_{{{i}}}(x) = {_cell(float(spline.a[i]), decimals)} "
            rf"+ {_cell(float(spline.b[i]), decimals)}(x - {x_i}) "
            rf"+ {_cell(float(spline.c[i]), decimals)}(x - {x_i})^2 "
            rf"+ {_cell(float(spline.d[i]), decimals)}(x - {x_i})^3"
        )
    return r"\\[1mm]".join(lines)


def evaluation_latex(
    spline: SplineSystem,
    target: float,
    value: float,
    index: int,
    extrapolated: bool,
    decimals: int,
) -> str:
    x_i = _cell(float(spline.xs[index]), decimals)
    x_next = _cell(float(spline.xs[index + 1]), decimals)
    body = (
        rf"S({_cell(target, decimals)}) = S_{{{index}}}({_cell(target, decimals)}) = "
        rf"{_cell(value, decimals)}"
    )
    detail = rf"\text{{using interval }} [{x_i},\, {x_next}]"
    if extrapolated:
        detail += r"\quad\text{(extrapolated: the end cubic is extended)}"
    return body + r"\\[1mm]" + detail


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------


def spline_plot(
    spline: SplineSystem,
    *,
    targets: list[float],
    target_values: list[float],
    show_derivatives: bool,
    title: str,
) -> PlotPayload:
    """Each cubic piece in its own colour, with optional S' and S'' overlays."""
    lo, hi = _piece_bounds(spline, targets)
    traces: list[dict[str, Any]] = [
        points_trace(list(spline.xs), list(spline.ys), "Data points")
    ]

    for index, xs_piece, ys_piece in piecewise_grid(spline, lo=lo, hi=hi):
        name = f"S_{index}" if show_derivatives else f"S_{index}(x)"
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": name,
                "x": xs_piece,
                "y": ys_piece,
                "line": {"color": PIECE_COLORS[index % len(PIECE_COLORS)]},
            }
        )

    if show_derivatives:
        for order, label, colour in (
            (1, "S'(x)", "#b45309"),
            (2, "S''(x)", "#0f766e"),
        ):
            for index, xs_piece, ys_piece in piecewise_grid(
                spline, lo=lo, hi=hi, order=order
            ):
                traces.append(
                    {
                        "type": "scatter",
                        "mode": "lines",
                        "name": label if index == 0 else f"{label} (cont.)",
                        "x": xs_piece,
                        "y": ys_piece,
                        "line": {"color": colour, "dash": "dot"},
                        "showlegend": index == 0,
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
