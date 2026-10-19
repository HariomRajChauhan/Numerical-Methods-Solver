"""Shared building blocks for the Chapter 4 numerical-differentiation solver.

Private module (leading underscore) so the auto-loader skips it. It holds the
polynomial bases behind the derivative formulas — the Newton forward/backward
binomials ``p(p±1)...`` and the Stirling central terms — the difference-driven
derivative engine for equally spaced tables, the finite-difference stencils for
a function input, and the plotting helper.

Everything is evaluated through the parameter ``p``:
``p = (x - x_0) / h`` for forward, ``p = (x - x_n) / h`` for backward and
``p = (x - x_c) / h`` for the central (Stirling) form, so a single derivative
``d/dx = (1/h) d/dp`` covers every case.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.core.models import PlotPayload
from app.solvers._common import (
    marker_trace,
    points_trace,
    sample_curve,
    segment_trace,
)
from app.solvers.ch3_interpolation._interp import backward_leading, forward_leading

FORWARD = "forward"
BACKWARD = "backward"
CENTRAL = "central"

# The callable produced by app.core.parser.make_function.
Evaluator = Callable[[float], float]


# ---------------------------------------------------------------------------
# Polynomial bases
# ---------------------------------------------------------------------------


def _basis(roots: list[float], factorial: int) -> np.ndarray:
    """Ascending-power coefficients of ``prod(p - root) / factorial!``."""
    coefficients = (
        np.polynomial.polynomial.polyfromroots(roots) if roots else [1.0]
    )
    return np.asarray(coefficients, dtype=float) / float(math.factorial(factorial))


def forward_basis(m: int) -> np.ndarray:
    """Ascending coefficients of the Newton binomial ``p(p-1)...(p-m+1)/m!``."""
    return _basis([float(j) for j in range(m)], m)


def backward_basis(m: int) -> np.ndarray:
    """Ascending coefficients of ``p(p+1)...(p+m-1)/m!``."""
    return _basis([float(-j) for j in range(m)], m)


def central_basis(m: int) -> np.ndarray:
    """Ascending coefficients of the Stirling central term of order ``m``."""
    if m % 2 == 1:
        half = (m - 1) // 2
        roots = [float(j) for j in range(-half, half + 1)]
    else:
        half = m // 2
        roots = [0.0, 0.0]
        for j in range(1, half):
            roots.extend((float(j), float(-j)))
    return _basis(roots, m)


def derivative_at(coefficients: np.ndarray, p: float, order: int) -> float:
    """Evaluate the ``order``-th derivative of a polynomial at ``p``."""
    poly = np.asarray(coefficients, dtype=float)
    for _ in range(order):
        poly = np.polynomial.polynomial.polyder(poly)
    if poly.size == 0:
        return 0.0
    return float(np.polynomial.polynomial.polyval(p, poly))


# ---------------------------------------------------------------------------
# Central differences around a node
# ---------------------------------------------------------------------------

_CENTRAL_LABELS = [
    "y_c",
    r"\mu\delta y_c",
    r"\delta^2 y_c",
    r"\mu\delta^3 y_c",
    r"\delta^4 y_c",
    r"\mu\delta^5 y_c",
]


def central_difference_values(ys: np.ndarray, center: int) -> list[float]:
    """The Stirling differences at ``center``: ``y_c, mu*d, d^2, mu*d^3, ...``.

    Only the orders that fit symmetrically around ``center`` are returned, so
    the list length encodes how many central differences are available.
    """
    count = len(ys)
    radius = min(center, count - 1 - center)
    y = [float(value) for value in ys]
    values: list[float] = [y[center]]
    if radius >= 1:
        values.append((y[center + 1] - y[center - 1]) / 2.0)
        values.append(y[center + 1] - 2.0 * y[center] + y[center - 1])
    if radius >= 2:
        d3_right = y[center + 2] - 3.0 * y[center + 1] + 3.0 * y[center] - y[center - 1]
        d3_left = y[center + 1] - 3.0 * y[center] + 3.0 * y[center - 1] - y[center - 2]
        values.append((d3_right + d3_left) / 2.0)
        values.append(
            y[center + 2]
            - 4.0 * y[center + 1]
            + 6.0 * y[center]
            - 4.0 * y[center - 1]
            + y[center - 2]
        )
    if radius >= 3:
        d5_right = (
            y[center + 3]
            - 5.0 * y[center + 2]
            + 10.0 * y[center + 1]
            - 10.0 * y[center]
            + 5.0 * y[center - 1]
            - y[center - 2]
        )
        d5_left = (
            y[center + 2]
            - 5.0 * y[center + 1]
            + 10.0 * y[center]
            - 10.0 * y[center - 1]
            + 5.0 * y[center - 2]
            - y[center - 3]
        )
        values.append((d5_right + d5_left) / 2.0)
    return values


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    """One term ``difference * weight`` of a difference-series derivative."""

    label: str
    difference: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class DerivativeResult:
    """The outcome of differentiating equally spaced tabulated data."""

    family: str
    order: int
    p: float
    base_index: int
    base_x: float
    value: float
    terms: list[Term]
    labels: list[str]
    differences: list[float]
    central: bool = False


def suggest_family(xs: np.ndarray, target: float, h: float) -> str:
    """Pick forward/backward/central from where the target sits in the table."""
    count = len(xs)
    p = (target - float(xs[0])) / h if h else 0.0
    if p <= 0.5:
        return FORWARD
    if p >= (count - 1) - 0.5:
        return BACKWARD
    return CENTRAL


def _diff_label(family: str, k: int, base_index: int) -> str:
    if k == 0:
        return f"y_{{{base_index}}}"
    symbol = r"\Delta" if family == FORWARD else r"\nabla"
    power = "" if k == 1 else f"^{k}"
    return f"{symbol}{power}\\,y_{{{base_index}}}"


def tabulated_derivative(
    xs: np.ndarray,
    ys: np.ndarray,
    *,
    target: float,
    order: int,
    family: str,
    h: float,
) -> DerivativeResult:
    """Differentiate equally spaced data with the requested difference family."""
    count = len(ys)

    if family == CENTRAL:
        center = round((target - float(xs[0])) / h)
        center = min(max(center, 0), count - 1)
        if count >= 3:
            center = min(max(center, 1), count - 2)
        values = central_difference_values(ys, center)
        base_x = float(xs[center])
        p = (target - base_x) / h
        labels = _CENTRAL_LABELS[: len(values)]
        central_terms = [
            Term(
                labels[m],
                values[m],
                derivative_at(central_basis(m), p, order),
                values[m] * derivative_at(central_basis(m), p, order) / h**order,
            )
            for m in range(order, len(values))
        ]
        value = float(sum(term.contribution for term in central_terms))
        return DerivativeResult(
            family=CENTRAL,
            order=order,
            p=p,
            base_index=center,
            base_x=base_x,
            value=value,
            terms=central_terms,
            labels=labels,
            differences=list(values),
            central=True,
        )

    if family == BACKWARD:
        base_index = count - 1
        differences = backward_leading(ys)
        basis = backward_basis
    else:
        base_index = 0
        differences = forward_leading(ys)
        basis = forward_basis

    base_x = float(xs[base_index])
    p = (target - base_x) / h
    labels = [_diff_label(family, k, base_index) for k in range(count)]
    terms: list[Term] = []
    for m in range(order, count):
        weight = derivative_at(basis(m), p, order)
        contribution = float(differences[m]) * weight / h**order
        terms.append(Term(labels[m], float(differences[m]), weight, contribution))
    value = float(sum(term.contribution for term in terms))
    return DerivativeResult(
        family=family,
        order=order,
        p=p,
        base_index=base_index,
        base_x=base_x,
        value=value,
        terms=terms,
        labels=list(labels),
        differences=[float(item) for item in differences],
        central=False,
    )


# ---------------------------------------------------------------------------
# Function-input stencils
# ---------------------------------------------------------------------------

# (offsets in units of h, weights) and an extra denominator for each rule.
_STENCILS: dict[tuple[str, int], tuple[list[tuple[int, float]], float]] = {
    (FORWARD, 1): ([(0, -1.0), (1, 1.0)], 1.0),
    (BACKWARD, 1): ([(0, 1.0), (-1, -1.0)], 1.0),
    (CENTRAL, 1): ([(-1, -1.0), (1, 1.0)], 2.0),
    (FORWARD, 2): ([(0, 1.0), (1, -2.0), (2, 1.0)], 1.0),
    (BACKWARD, 2): ([(0, 1.0), (-1, -2.0), (-2, 1.0)], 1.0),
    (CENTRAL, 2): ([(-1, 1.0), (0, -2.0), (1, 1.0)], 1.0),
}


def stencil(order: int, family: str) -> tuple[list[tuple[int, float]], float]:
    """The finite-difference offsets, weights and extra denominator."""
    return _STENCILS[(family, order)]


@dataclass(frozen=True)
class Node:
    """One evaluation node of a finite-difference stencil."""

    x: float
    value: float
    weight: float


@dataclass(frozen=True)
class FunctionResult:
    """The outcome of differentiating a function with a local stencil."""

    family: str
    order: int
    x0: float
    h: float
    denominator: float
    value: float
    nodes: list[Node]


def function_derivative(
    f: Evaluator,
    *,
    x0: float,
    h: float,
    order: int,
    family: str,
) -> FunctionResult:
    """Apply a simple finite-difference stencil to a function input.

    Raises:
        ValueError: When the function is not finite at one of the stencil nodes;
            the message names the offending ``x``.
    """
    offsets, extra = stencil(order, family)
    denominator = h**order * extra
    nodes: list[Node] = []
    total = 0.0
    for shift, weight in offsets:
        node_x = x0 + shift * h
        node_y = float(f(node_x))
        if not math.isfinite(node_y):
            raise ValueError(f"f({node_x:g}) is not finite")
        nodes.append(Node(node_x, node_y, weight))
        total += weight * node_y
    return FunctionResult(
        family=family,
        order=order,
        x0=x0,
        h=h,
        denominator=denominator,
        value=total / denominator,
        nodes=nodes,
    )


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def derivative_plot(
    *,
    points: tuple[list[float], list[float]] | None,
    curve: tuple[list[float], list[float | None]] | None,
    target: float,
    target_y: float,
    slope: float | None,
    curve_name: str = "Interpolating polynomial",
    title: str = "Numerical differentiation",
) -> PlotPayload:
    """Data/curve plus the evaluation point and (for first derivatives) a tangent."""
    traces: list[dict[str, object]] = []
    if points is not None and points[0]:
        traces.append(points_trace(points[0], points[1], "Data points"))
    if curve is not None and curve[0]:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": curve_name,
                "x": curve[0],
                "y": curve[1],
            }
        )
    traces.append(marker_trace(target, target_y, "Evaluation point", color="#dc2626"))
    if slope is not None and math.isfinite(slope):
        xs = [float(value) for value in (curve[0] if curve else []) if value is not None]
        lo = min(xs) if xs else target
        hi = max(xs) if xs else target
        span = 0.18 * (hi - lo) if hi > lo else 1.0
        traces.append(
            segment_trace(
                target - span,
                target_y - slope * span,
                target + span,
                target_y + slope * span,
                "Tangent",
                color="#16a34a",
            )
        )
    layout = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "y"}},
    }
    return PlotPayload(traces=traces, layout=layout)


def function_curve(
    f: Evaluator, x0: float, h: float
) -> tuple[list[float], list[float | None]]:
    """Sample a window around ``x0`` wide enough to contain the whole stencil."""
    span = max(abs(h) * 8.0, 1.0)
    xs, ys = sample_curve(f, x0 - span, x0 + span)
    values: list[float | None] = [float(value) for value in ys]
    return xs, values
