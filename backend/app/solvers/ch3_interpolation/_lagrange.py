"""Shared building blocks for Lagrange interpolation, the compare view and the
Runge-phenomenon demo.

Private module (leading underscore) so the auto-loader skips it. It depends only
on :mod:`app.solvers.ch3_interpolation._interp` and stays free of solver-level
concerns, so both ``lagrange`` and ``newton_divided_difference`` can reuse it.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.core.models import DataTable, PlotPayload
from app.solvers._common import format_num

# Colours reused by the basis / compare charts.
BASIS_COLORS = [
    "#2563eb",
    "#16a34a",
    "#9333ea",
    "#ea580c",
    "#0891b2",
    "#db2777",
    "#65a30d",
    "#7c3aed",
]

# The classic Runge example and its demo interval.
RUNGE_LO = -1.0
RUNGE_HI = 1.0
RUNGE_GRID_POINTS = 500


# ---------------------------------------------------------------------------
# Lagrange basis
# ---------------------------------------------------------------------------


def lagrange_basis_value(xs: np.ndarray, index: int, target: float) -> float:
    """Evaluate ``L_i(target)`` for the node ``xs[index]``."""
    node = float(xs[index])
    value = 1.0
    for j in range(len(xs)):
        if j == index:
            continue
        denominator = node - float(xs[j])
        value *= (target - float(xs[j])) / denominator
    return value


def lagrange_value(xs: np.ndarray, ys: np.ndarray, target: float) -> float:
    """The Lagrange interpolant ``P(target) = sum_i y_i L_i(target)``."""
    total = 0.0
    for i in range(len(xs)):
        total += float(ys[i]) * lagrange_basis_value(xs, i, target)
    return float(total)


def lagrange_basis_latex(xs: np.ndarray, decimals: int) -> str:
    """Every basis polynomial ``L_i(x)`` as a numerator/denominator quotient."""
    size = len(xs)
    lines: list[str] = []
    for i in range(size):
        numerator = "".join(
            rf"\left(x - {format_num(float(xs[j]), decimals)}\right)"
            for j in range(size)
            if j != i
        )
        denominator = "".join(
            rf"\left({format_num(float(xs[i]), decimals)} - {format_num(float(xs[j]), decimals)}\right)"
            for j in range(size)
            if j != i
        )
        lines.append(rf"L_{{{i}}}(x) = \frac{{{numerator}}}{{{denominator}}}")
    return r"\\[1mm]".join(lines)


def lagrange_substitution_latex(
    xs: np.ndarray,
    ys: np.ndarray,
    target: float,
    decimals: int,
) -> tuple[str, float]:
    """Exam-style working for one target: numerators, denominators and the sum."""
    size = len(xs)
    basis_lines: list[str] = []
    products: list[str] = []
    terms: list[float] = []

    for i in range(size):
        numerator_values = [target - float(xs[j]) for j in range(size) if j != i]
        denominator_values = [float(xs[i]) - float(xs[j]) for j in range(size) if j != i]
        numerator = math.prod(numerator_values) if numerator_values else 1.0
        denominator = math.prod(denominator_values) if denominator_values else 1.0
        weight = numerator / denominator if denominator else math.nan

        numerator_latex = "".join(
            rf"\left({format_num(target, decimals)} - {format_num(float(xs[j]), decimals)}\right)"
            for j in range(size)
            if j != i
        )
        denominator_latex = "".join(
            rf"\left({format_num(float(xs[i]), decimals)} - {format_num(float(xs[j]), decimals)}\right)"
            for j in range(size)
            if j != i
        )
        basis_lines.append(
            rf"L_{{{i}}}({format_num(target, decimals)}) = "
            rf"\frac{{{numerator_latex}}}{{{denominator_latex}}} = "
            rf"\frac{{{format_num(numerator, decimals)}}}{{{format_num(denominator, decimals)}}} = "
            rf"{format_num(weight, decimals)}"
        )
        products.append(
            rf"f_{{{i}}}L_{{{i}}} = "
            rf"({format_num(float(ys[i]), decimals)})"
            rf"({format_num(weight, decimals)}) = {format_num(float(ys[i]) * weight, decimals)}"
        )
        terms.append(float(ys[i]) * weight)

    value = float(sum(terms))
    total_latex = (
        rf"P({format_num(target, decimals)}) = "
        + " + ".join(products)
        + " = "
        + format_num(value, decimals)
    )
    latex = r"\\[1mm]".join([*basis_lines, total_latex])
    return latex, value


def lagrange_basis_plot(xs: np.ndarray, *, decimals: int, title: str) -> PlotPayload:
    """All basis polynomials on one chart, each 1 at its node and 0 at the others."""
    size = len(xs)
    lo = float(np.min(xs))
    hi = float(np.max(xs))
    pad = 0.05 * (hi - lo) if hi > lo else 0.5
    grid = np.linspace(lo - pad, hi + pad, 300)
    nodes = [float(value) for value in xs]

    traces: list[dict[str, Any]] = []
    for i in range(size):
        color = BASIS_COLORS[i % len(BASIS_COLORS)]
        curve = [lagrange_basis_value(xs, i, float(x)) for x in grid]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": f"L_{i}(x)",
                "x": grid.tolist(),
                "y": curve,
                "line": {"color": color},
            }
        )
        node_values = [lagrange_basis_value(xs, i, node) for node in nodes]
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": f"L_{i} at nodes",
                "x": nodes,
                "y": node_values,
                "marker": {"color": color, "size": 7},
                "showlegend": False,
            }
        )

    layout = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "L_i(x)"}},
        "shapes": [
            {
                "type": "line",
                "x0": float(np.min(grid)),
                "x1": float(np.max(grid)),
                "y0": 0.0,
                "y1": 0.0,
                "line": {"color": "#94a3b8", "width": 1, "dash": "dot"},
            }
        ],
    }
    return PlotPayload(traces=traces, layout=layout)


# ---------------------------------------------------------------------------
# Comparison view (Newton divided difference vs Lagrange)
# ---------------------------------------------------------------------------


def comparison_table(
    targets: list[float],
    newton_values: list[float],
    lagrange_values: list[float],
    decimals: int,
) -> DataTable:
    """A table showing both methods agree (difference ~= 0)."""
    rows: list[list[Any]] = []
    for target, newton, lagrange in zip(targets, newton_values, lagrange_values, strict=True):
        rows.append(
            [
                format_num(float(target), decimals),
                format_num(float(newton), decimals),
                format_num(float(lagrange), decimals),
                format_num(abs(float(newton) - float(lagrange)), decimals),
            ]
        )
    return DataTable(
        title="Comparison: Newton divided difference vs Lagrange",
        columns=["x", "Newton DD", "Lagrange", "|difference|"],
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Runge-phenomenon demo
# ---------------------------------------------------------------------------


def runge_true(grid: np.ndarray) -> np.ndarray:
    """The Runge function ``f(x) = 1 / (1 + 25 x^2)``."""
    values = np.asarray(grid, dtype=float)
    return 1.0 / (1.0 + 25.0 * values**2)


def chebyshev_nodes(count: int) -> np.ndarray:
    """Chebyshev-Lobatto nodes on [-1, 1] (endpoints included), ascending."""
    if count <= 1:
        return np.array([0.0])
    indices = np.arange(count)
    return -np.cos(np.pi * indices / (count - 1))


def _clean(series: np.ndarray) -> list[float | None]:
    return [float(value) if math.isfinite(float(value)) else None for value in series]


def _interpolant(nodes: np.ndarray, grid: np.ndarray) -> np.ndarray:
    values = runge_true(nodes)
    coefficients = np.polyfit(nodes, values, len(nodes) - 1)
    return np.polyval(coefficients, grid)


def runge_demo(
    count: int,
    decimals: int,
) -> tuple[PlotPayload, DataTable, dict[str, Any]]:
    """Equispaced vs Chebyshev interpolation of the Runge function.

    Returns:
        ``(plot, table, result)``.
    """
    grid = np.linspace(RUNGE_LO, RUNGE_HI, RUNGE_GRID_POINTS)
    truth = runge_true(grid)
    equispaced = np.linspace(RUNGE_LO, RUNGE_HI, count)
    chebyshev = chebyshev_nodes(count)

    equi_curve = _interpolant(equispaced, grid)
    cheb_curve = _interpolant(chebyshev, grid)

    equi_error = float(np.max(np.abs(equi_curve - truth)))
    cheb_error = float(np.max(np.abs(cheb_curve - truth)))

    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines",
            "name": "f(x) = 1/(1+25x^2)",
            "x": grid.tolist(),
            "y": _clean(truth),
            "line": {"color": "#111827", "width": 3},
        },
        {
            "type": "scatter",
            "mode": "lines",
            "name": f"Equispaced ({count} nodes)",
            "x": grid.tolist(),
            "y": _clean(equi_curve),
            "line": {"color": "#dc2626"},
        },
        {
            "type": "scatter",
            "mode": "lines",
            "name": f"Chebyshev ({count} nodes)",
            "x": grid.tolist(),
            "y": _clean(cheb_curve),
            "line": {"color": "#16a34a"},
        },
        {
            "type": "scatter",
            "mode": "markers",
            "name": "Equispaced nodes",
            "x": equispaced.tolist(),
            "y": runge_true(equispaced).tolist(),
            "marker": {"color": "#dc2626", "size": 7, "symbol": "circle"},
        },
        {
            "type": "scatter",
            "mode": "markers",
            "name": "Chebyshev nodes",
            "x": chebyshev.tolist(),
            "y": runge_true(chebyshev).tolist(),
            "marker": {"color": "#16a34a", "size": 7, "symbol": "diamond"},
        },
    ]
    layout = {
        "title": {"text": "Runge phenomenon: equispaced vs Chebyshev nodes"},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "y"}},
    }
    plot = PlotPayload(traces=traces, layout=layout)

    table = DataTable(
        title="Maximum error on [-1, 1]",
        columns=["Nodes", "Equispaced max error", "Chebyshev max error"],
        rows=[[count, format_num(equi_error, decimals), format_num(cheb_error, decimals)]],
    )
    result: dict[str, Any] = {
        "nodes": count,
        "degree": count - 1,
        "max_error_equispaced": equi_error,
        "max_error_chebyshev": cheb_error,
    }
    return plot, table, result
