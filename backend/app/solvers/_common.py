"""Shared helpers for solver modules.

This module is deliberately private (leading underscore) so the auto-loader in
:mod:`app.solvers` skips it — only real solvers register themselves. It holds
small, reusable building blocks so individual solvers stay short.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np

from app.core.models import (
    Chapter,
    ErrorInfo,
    InputField,
    MethodMeta,
    MethodStatus,
    PlotPayload,
    SelectOption,
    SolveResponse,
    SolveStatus,
    Step,
)
from app.core.registry import register_stub

# Function-like callable produced by app.core.parser.make_function.
Evaluator = Callable[[Any], Any]


def _safe_eval(f: Evaluator, x: float) -> float:
    """Evaluate ``f`` at a scalar, mapping any failure to ``nan`` (plot gaps)."""
    try:
        return float(f(x))
    except Exception:
        return float("nan")


def sample_curve(
    f: Evaluator,
    lo: float,
    hi: float,
    *,
    points: int = 400,
) -> tuple[list[float], list[float]]:
    """Sample ``f`` over ``[lo, hi]`` for plotting.

    The callable is expected to be the non-strict variant
    (``make_function(..., strict=False)``), but every point is guarded anyway so
    domain gaps become ``nan`` instead of raising. Points are evaluated
    one-by-one, which also tolerates expressions that are not vectorisable.

    Returns:
        ``(xs, ys)`` as plain Python lists.
    """
    xs = np.linspace(lo, hi, points)
    ys = np.array([_safe_eval(f, float(x)) for x in xs], dtype=float)
    return xs.tolist(), ys.tolist()


def line_trace(xs: list[float], ys: list[float], name: str = "f(x)") -> dict[str, Any]:
    """A Plotly scatter trace drawn as a continuous line."""
    return {"type": "scatter", "mode": "lines", "name": name, "x": xs, "y": ys}


def marker_trace(
    x: float,
    y: float,
    name: str,
    *,
    color: str = "#dc2626",
    symbol: str = "circle",
) -> dict[str, Any]:
    """A single Plotly point marker (e.g. the computed root)."""
    return {
        "type": "scatter",
        "mode": "markers",
        "name": name,
        "x": [x],
        "y": [y],
        "marker": {"size": 11, "color": color, "symbol": symbol},
    }


def register_coming_soon(
    chapter: Chapter,
    method_id: str,
    name: str,
    summary: str,
    theory: str = "",
    pseudocode: str = "",
) -> None:
    """Register a syllabus method that is planned but not yet implemented.

    Coming-soon methods appear in navigation, search and the chapter pages with
    a "Coming soon" badge, and their theory/pseudocode tabs are already readable.
    Implementing the method later means replacing this call with ``@register``.
    """
    register_stub(
        MethodMeta(
            id=method_id,
            chapter=chapter,
            name=name,
            status=MethodStatus.COMING_SOON,
            summary=summary,
            theory=theory,
            pseudocode=pseudocode,
            input_schema=[],
        )
    )


# ---------------------------------------------------------------------------
# Number formatting for exam-style LaTeX
# ---------------------------------------------------------------------------


def format_num(value: float, decimals: int = 6) -> str:
    """Format ``value`` for LaTeX using ``decimals`` decimal places.

    Very small or very large magnitudes switch to scientific notation rendered
    as ``m\\times 10^{e}`` so iteration tables and working steps stay readable.
    """
    if value is None:
        return r"\text{n/a}"
    if not math.isfinite(value):
        return r"+\infty" if value > 0 else r"-\infty"
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 10.0 ** (decimals + 4) or magnitude < 1e-4:
        mantissa, exponent = f"{value:.{max(decimals, 1)}e}".split("e")
        return rf"{mantissa}\times 10^{{{int(exponent)}}}"
    return f"{value:.{decimals}f}"


# ---------------------------------------------------------------------------
# Extra Plotly trace helpers
# ---------------------------------------------------------------------------


def segment_trace(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    name: str = "secant",
    *,
    color: str = "#f59e0b",
    dash: str = "dot",
) -> dict[str, Any]:
    """A short line segment between two points (secant/tangent visualisation)."""
    return {
        "type": "scatter",
        "mode": "lines",
        "name": name,
        "x": [x1, x2],
        "y": [y1, y2],
        "line": {"color": color, "dash": dash, "width": 1},
        "hoverinfo": "skip",
    }


def points_trace(
    xs: list[float],
    ys: list[float],
    name: str,
    *,
    color: str = "#2563eb",
    symbol: str = "x",
) -> dict[str, Any]:
    """A set of small marker points (successive iterates, evaluation points)."""
    return {
        "type": "scatter",
        "mode": "markers",
        "name": name,
        "x": list(xs),
        "y": list(ys),
        "marker": {"size": 7, "color": color, "symbol": symbol},
    }


# ---------------------------------------------------------------------------
# Schema field factories (shared by the Chapter 1 root-finding solvers)
# ---------------------------------------------------------------------------


def function_field(
    *,
    key: str = "function",
    label: str = "Function f(x)",
    variable: str = "x",
    placeholder: str = "x^3 - x - 1",
    help: str = (
        "Use ^ for powers, * for products (2*x). Allowed: sin, cos, tan, exp, "
        "ln, log, log10, sqrt, abs and more."
    ),
    required: bool = True,
) -> InputField:
    """A text field holding a function of one variable."""
    return InputField(
        key=key,
        label=label,
        type="function",
        variable=variable,
        required=required,
        placeholder=placeholder,
        help=help,
    )


def number_field(
    key: str,
    label: str,
    default: float,
    *,
    help: str = "",
    placeholder: str = "",
    required: bool = True,
) -> InputField:
    """A numeric input with a default value."""
    return InputField(
        key=key,
        label=label,
        type="number",
        required=required,
        default=default,
        help=help,
        placeholder=placeholder,
    )


def tolerance_field(
    *,
    key: str = "tolerance",
    default: float = 1e-6,
    help: str = "Stop when the chosen stopping criterion falls below this value.",
) -> InputField:
    """The convergence threshold."""
    return InputField(
        key=key,
        label="Tolerance",
        type="tolerance",
        required=True,
        default=default,
        min=1e-15,
        max=1.0,
        help=help,
    )


def max_iterations_field(
    *,
    key: str = "max_iterations",
    default: int = 50,
) -> InputField:
    """The iteration safety cap."""
    return InputField(
        key=key,
        label="Maximum iterations",
        type="max_iterations",
        required=True,
        default=default,
        min=1,
        max=10_000,
        help="Safety cap if the tolerance is never reached.",
    )


def precision_field(
    *,
    key: str = "decimal_precision",
    default: int = 6,
) -> InputField:
    """Number of decimal places used when displaying intermediate values."""
    return InputField(
        key=key,
        label="Decimal precision (working)",
        type="precision",
        required=True,
        default=default,
        min=0,
        max=15,
        help="Decimal places shown in the exam-style working and tables.",
    )


STOP_CRITERION_OPTIONS: list[SelectOption] = [
    SelectOption(value="function", label="|f(x)| < tolerance"),
    SelectOption(value="interval", label="|x_k - x_{k-1}| < tolerance"),
    SelectOption(value="relative", label="relative error % < tolerance"),
]


def boolean_field(
    key: str,
    label: str,
    default: bool = False,
    *,
    help: str = "",
) -> InputField:
    """A checkbox used to include/exclude an option or method."""
    return InputField(
        key=key,
        label=label,
        type="boolean",
        required=False,
        default=default,
        help=help,
    )


def stop_criterion_field(
    *,
    key: str = "stopping_criterion",
    default: str = "function",
) -> InputField:
    """Which convergence test ends the iteration."""
    return InputField(
        key=key,
        label="Stopping criterion",
        type="select",
        required=True,
        default=default,
        options=list(STOP_CRITERION_OPTIONS),
        help="The test that must fall below the tolerance for convergence.",
    )


def stop_reached(
    criterion: str,
    tolerance: float,
    *,
    f_value: float,
    x: float,
    x_prev: float | None,
) -> tuple[bool, float | None]:
    """Evaluate the requested stopping criterion.

    Returns:
        ``(reached, error_value)`` where ``error_value`` is the quantity the
        criterion measures (``|f(x)|``, ``|dx|`` or relative %), or ``None`` when
        it cannot be formed yet.
    """
    if criterion == "function":
        error = abs(f_value)
    elif criterion == "relative":
        if x_prev is None or x == 0:
            return False, None
        error = abs((x - x_prev) / x) * 100.0
    else:  # "interval" / |dx|
        if x_prev is None:
            return False, None
        error = abs(x - x_prev)
    return error < tolerance, error


def estimate_order(step_errors: list[float]) -> float | None:
    """Estimate the convergence order ``p`` from successive iterate errors.

    Uses ``p ~= ln(e_{k+1}/e_k) / ln(e_k/e_{k-1})`` over the last three
    available errors. Returns ``None`` when the estimate is not meaningful.
    """
    errors = [e for e in step_errors if e > 0.0]
    if len(errors) < 3:
        return None
    e_prev, e_cur, e_next = errors[-3], errors[-2], errors[-1]
    num = math.log(e_next / e_cur)
    den = math.log(e_cur / e_prev)
    if den == 0.0:
        return None
    order = num / den
    if not math.isfinite(order) or order <= 0.0 or order >= 5.0:
        return None
    return order


def failed_response(
    method_id: str,
    message: str,
    *,
    steps: list[Step] | None = None,
    result: dict[str, Any] | None = None,
    plot: PlotPayload | None = None,
    errors: ErrorInfo | None = None,
    warnings: list[str] | None = None,
) -> SolveResponse:
    """Build a HTTP-200 ``failed`` response for a mathematical breakdown.

    Used when the method cannot continue for a *mathematical* reason
    (``f'(x) = 0``, ``f(x0) = f(x1)``, a division by zero) as opposed to
    malformed or invalid input, which is rejected earlier with HTTP 400.
    """
    return SolveResponse(
        method=method_id,
        status=SolveStatus.FAILED,
        result=result or {},
        steps=steps or [],
        plot=plot or PlotPayload(),
        errors=errors or ErrorInfo(),
        warnings=[message, *(warnings or [])],
    )
