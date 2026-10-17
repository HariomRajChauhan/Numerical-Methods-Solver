"""Shared helpers for the Chapter 1 non-linear *system* solvers.

Private module (leading underscore) so the auto-loader in :mod:`app.solvers`
skips it. It holds the parsing, Jacobian, plotting and error-metric building
blocks shared by ``nonlinear_system_direct`` and ``nonlinear_system_newton`` so
those two solvers stay focused on their iteration logic.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import sympy as sp

from app.core.errors import InvalidInputError
from app.core.models import PlotPayload
from app.core.parser import expr_to_latex, make_function, parse_expression
from app.solvers._common import format_num

MAX_VARIABLES = 6
MAX_CONDITION_NUMBER = 1e12
DIVERGENCE_BOUND = 1e10

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Names the expression parser reserves for functions/constants; a variable may
# not reuse them.
_RESERVED_NAMES = frozenset(
    {
        "sin", "cos", "tan", "cot", "sec", "csc",
        "asin", "acos", "atan", "acot", "asec", "acsc",
        "sinh", "cosh", "tanh", "coth", "asinh", "acosh", "atanh",
        "sqrt", "cbrt", "exp", "log", "ln", "log10", "abs", "sign",
        "floor", "ceiling", "factorial", "min", "max", "pi", "e",
    }
)

# Vector-valued callable: one float per variable in, one array out.
VectorFunction = Callable[..., np.ndarray]


# ---------------------------------------------------------------------------
# Parsing of the variable list and the equation strings
# ---------------------------------------------------------------------------


def parse_variables(text: str) -> list[str]:
    """Split and validate a comma/space separated variable-name list."""
    names = [token for token in re.split(r"[,\s]+", text.strip()) if token]
    if not names:
        raise InvalidInputError(
            "Enter at least one variable name.",
            hint="Example: x, y",
        )
    if len(names) > MAX_VARIABLES:
        raise InvalidInputError(
            f"At most {MAX_VARIABLES} variables are supported.",
        )
    seen: set[str] = set()
    for name in names:
        if not _IDENTIFIER_RE.match(name):
            raise InvalidInputError(
                f"'{name}' is not a valid variable name.",
                hint="Use letters, digits and underscores, starting with a letter.",
            )
        if name.lower() in _RESERVED_NAMES:
            raise InvalidInputError(
                f"'{name}' is a reserved function/constant name.",
                hint="Choose a different variable name, e.g. x, y or u.",
            )
        if name.lower() in seen:
            raise InvalidInputError(f"The variable '{name}' is listed twice.")
        seen.add(name.lower())
    return names


def _split_top_level_commas(text: str) -> list[str]:
    """Split on commas that are not inside parentheses.

    This lets students separate equations with commas as well as semicolons,
    while leaving multi-argument calls such as ``Max(x, y)`` intact.
    """
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def _split_entries(text: str) -> list[str]:
    entries: list[str] = []
    for line in re.split(r"[;\n]+", text):
        entries.extend(_split_top_level_commas(line))
    cleaned = [part.strip() for part in entries if part.strip()]
    if not cleaned:
        raise InvalidInputError(
            "Enter at least one equation.",
            hint="Separate several equations with ';', a newline or a comma.",
        )
    return cleaned


def parse_residual_equations(text: str, variables: Sequence[str]) -> list[sp.Expr]:
    """Parse ``f_i = 0`` equations (``expr`` or ``lhs = rhs``) for Newton's method."""
    entries = _split_entries(text)
    if len(entries) != len(variables):
        raise InvalidInputError(
            f"Expected {len(variables)} equation(s) for variables "
            f"{', '.join(variables)} but found {len(entries)}.",
            hint="Separate the equations with ';', a newline or a comma.",
        )
    expressions: list[sp.Expr] = []
    for entry in entries:
        if entry.count("=") > 1:
            raise InvalidInputError(
                f"'{entry}' contains more than one '='.",
                hint="Write each equation once, e.g. x^2 + y^2 - 4 = 0.",
            )
        if "=" in entry:
            left, right = entry.split("=", 1)
            expression = parse_expression(left, variables) - parse_expression(right, variables)
        else:
            expression = parse_expression(entry, variables)
        expressions.append(expression)
    return expressions


def parse_iteration_equations(text: str, variables: Sequence[str]) -> list[sp.Expr]:
    """Parse ``variable = g(...)`` equations for the direct (iteration) method.

    Returns the right-hand sides ordered to match ``variables``.
    """
    entries = _split_entries(text)
    mapping: dict[str, sp.Expr] = {}
    for entry in entries:
        if "=" not in entry:
            raise InvalidInputError(
                f"'{entry}' must have the form 'variable = expression'.",
                hint="Example: x = (20 - y^2)/10",
            )
        left, right = entry.split("=", 1)
        name = left.strip()
        if name not in variables:
            raise InvalidInputError(
                f"'{name}' is not one of the variables {', '.join(variables)}.",
            )
        if name in mapping:
            raise InvalidInputError(f"More than one equation defines '{name}'.")
        mapping[name] = parse_expression(right, variables)
    missing = [name for name in variables if name not in mapping]
    if missing:
        raise InvalidInputError(
            f"No iteration equation was given for {', '.join(missing)}.",
            hint="Every variable needs exactly one equation.",
        )
    return [mapping[name] for name in variables]


# ---------------------------------------------------------------------------
# Symbolic Jacobian and numeric evaluation
# ---------------------------------------------------------------------------


def jacobian_matrix(expressions: Sequence[sp.Expr], variables: Sequence[str]) -> sp.Matrix:
    """Symbolic Jacobian ``J[i, j] = d f_i / d x_j``."""
    symbols = [sp.Symbol(name) for name in variables]
    return sp.Matrix(
        [[sp.diff(expression, symbol) for symbol in symbols] for expression in expressions]
    )


def vector_function(
    expressions: Sequence[sp.Expr],
    variables: Sequence[str],
    *,
    strict: bool = False,
) -> VectorFunction:
    """Return ``point -> np.ndarray`` evaluating every expression at a point."""
    funcs = [
        make_function(expression, tuple(variables), strict=strict) for expression in expressions
    ]

    def evaluate(point: Sequence[float]) -> np.ndarray:
        return np.array([func(*point) for func in funcs], dtype=float)

    return evaluate


def matrix_function(matrix: sp.Matrix, variables: Sequence[str]) -> VectorFunction:
    """Return ``point -> np.ndarray`` evaluating a symbolic matrix at a point."""
    rows, cols = matrix.shape
    funcs = [
        [make_function(matrix[i, j], tuple(variables), strict=False) for j in range(cols)]
        for i in range(rows)
    ]

    def evaluate(point: Sequence[float]) -> np.ndarray:
        return np.array(
            [[funcs[i][j](*point) for j in range(cols)] for i in range(rows)],
            dtype=float,
        )

    return evaluate


def norm(vector: np.ndarray) -> float:
    """Euclidean (2-)norm of a vector, ``inf`` if it is not finite."""
    value = float(np.linalg.norm(vector))
    return value if math.isfinite(value) else math.inf


def spectral_radius(matrix: np.ndarray) -> float:
    """Largest modulus of the eigenvalues of a square matrix (``inf`` on failure)."""
    try:
        eigenvalues = np.linalg.eigvals(matrix)
    except np.linalg.LinAlgError:
        return math.inf
    modulus = np.abs(eigenvalues)
    if modulus.size == 0 or not np.all(np.isfinite(modulus)):
        return math.inf
    return float(np.max(modulus))


def condition_number(matrix: np.ndarray) -> float:
    """2-norm condition number, ``inf`` for a singular (or non-finite) matrix."""
    if not np.all(np.isfinite(matrix)):
        return math.inf
    try:
        value = float(np.linalg.cond(matrix))
    except np.linalg.LinAlgError:
        return math.inf
    return value if math.isfinite(value) else math.inf


def system_error(
    criterion: str,
    *,
    residual_norm: float,
    dx_norm: float,
    x_norm: float,
) -> float | None:
    """Map the stopping criterion onto a scalar system error.

    ``function`` uses the residual norm ``||F(x)||``, ``interval`` the step norm
    ``||dx||`` and ``relative`` the percentage ``||dx|| / ||x|| * 100``.
    """
    if criterion == "function":
        return residual_norm
    if criterion == "relative":
        return dx_norm / x_norm * 100.0 if x_norm > 0.0 else None
    return dx_norm


# ---------------------------------------------------------------------------
# LaTeX helpers for exam-style working
# ---------------------------------------------------------------------------


def vector_latex(values: Any, decimals: int) -> str:
    body = r" \\ ".join(_fmt(float(value), decimals) for value in values)
    return rf"\begin{{bmatrix}} {body} \end{{bmatrix}}"


def matrix_latex(matrix: Any, decimals: int) -> str:
    body = r" \\ ".join(
        " & ".join(_fmt(float(value), decimals) for value in row) for row in matrix
    )
    return rf"\begin{{bmatrix}} {body} \end{{bmatrix}}"


def _fmt(value: float, decimals: int) -> str:
    return format_num(float(value), decimals)


def equations_latex(expressions: Sequence[sp.Expr]) -> str:
    """Render a list of residuals as ``f_i = ... = 0``, one LaTeX line each."""
    lines = [
        f"f_{{{index}}} = {expr_to_latex(expression)} = 0"
        for index, expression in enumerate(expressions, start=1)
    ]
    return r" \\ ".join(lines)


# ---------------------------------------------------------------------------
# Plot building (error vs iteration + optional 2-D contour intersection)
# ---------------------------------------------------------------------------


def _grid_bounds(
    points: Sequence[Any],
    variables: Sequence[str],
) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    span_x = xhi - xlo
    span_y = yhi - ylo
    if not math.isfinite(span_x) or span_x <= 0:
        span_x = 1.0
    if not math.isfinite(span_y) or span_y <= 0:
        span_y = 1.0
    if span_x > 1e3 or span_y > 1e3:
        xlo, xhi = points[0][0] - 3.0, points[0][0] + 3.0
        ylo, yhi = points[0][1] - 3.0, points[0][1] + 3.0
        span_x = span_y = 6.0
    del variables
    margin_x = 0.6 * span_x
    margin_y = 0.6 * span_y
    return xlo - margin_x, xhi + margin_x, ylo - margin_y, yhi + margin_y


def _contour_trace(
    func: Callable[..., Any],
    xlo: float,
    xhi: float,
    ylo: float,
    yhi: float,
    name: str,
    color: str,
    *,
    points: int = 121,
) -> dict[str, Any]:
    xs = np.linspace(xlo, xhi, points)
    ys = np.linspace(ylo, yhi, points)
    grid_x, grid_y = np.meshgrid(xs, ys)
    try:
        z = np.asarray(func(grid_x, grid_y), dtype=float)
    except Exception:
        z = np.full(grid_x.shape, np.nan)
    return {
        "type": "contour",
        "x": xs.tolist(),
        "y": ys.tolist(),
        "z": z.tolist(),
        "name": name,
        "showscale": False,
        "hoverinfo": "name",
        "contours": {
            "coloring": "lines",
            "showlabels": True,
            "start": 0.0,
            "end": 0.0,
            "size": 1.0,
        },
        "line": {"width": 2.4, "color": color},
        "xaxis": "x2",
        "yaxis": "y2",
    }


def build_system_plot(
    *,
    variables: Sequence[str],
    iterates: Sequence[Any],
    errors: Sequence[float | None],
    residuals: Sequence[float],
    root: Any,
    title: str,
    contour: tuple[Callable[..., Any], Callable[..., Any]] | None = None,
) -> PlotPayload:
    """Build the Plotly payload: error vs iteration, plus a 2-D contour plot.

    The contour subplot is only drawn for two-variable systems, when
    ``contour`` provides the two residual functions ``F1`` and ``F2`` whose zero
    level curves intersect at the solution.
    """
    iterations = list(range(1, len(errors) + 1))
    error_y = [_floor(value) for value in errors]
    residual_y = [_floor(value) for value in residuals]

    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Error (stopping metric)",
            "x": iterations,
            "y": error_y,
        },
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Residual ||F||",
            "x": iterations,
            "y": residual_y,
            "line": {"dash": "dot"},
        },
    ]
    layout: dict[str, Any] = {
        "title": {"text": title},
        "showlegend": True,
    }

    two_dimensional = contour is not None and len(variables) == 2 and bool(iterates)
    if two_dimensional:
        assert contour is not None
        point_list = [list(point) for point in iterates]
        point_list.append(list(root))
        xlo, xhi, ylo, yhi = _grid_bounds(point_list, variables)
        traces[0]["xaxis"] = "x"
        traces[0]["yaxis"] = "y"
        traces[1]["xaxis"] = "x"
        traces[1]["yaxis"] = "y"
        traces.append(
            _contour_trace(contour[0], xlo, xhi, ylo, yhi, "F_1 = 0", "#2563eb")
        )
        traces.append(
            _contour_trace(contour[1], xlo, xhi, ylo, yhi, "F_2 = 0", "#dc2626")
        )
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": "iterates",
                "x": [point[0] for point in iterates],
                "y": [point[1] for point in iterates],
                "marker": {"size": 7, "color": "#059669"},
                "line": {"color": "#059669", "dash": "dot"},
                "xaxis": "x2",
                "yaxis": "y2",
            }
        )
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": "solution",
                "x": [root[0]],
                "y": [root[1]],
                "marker": {"size": 12, "color": "#111827", "symbol": "star"},
                "xaxis": "x2",
                "yaxis": "y2",
            }
        )
        total = error_y + residual_y
        layout["xaxis"] = {"domain": [0.0, 0.42], "anchor": "y", "title": {"text": "Iteration k"}}
        layout["yaxis"] = {
            "domain": [0.0, 1.0],
            "anchor": "x",
            "type": "log",
            "title": {"text": "Error"},
            "range": _log_range(total),
        }
        layout["xaxis2"] = {
            "domain": [0.55, 1.0],
            "anchor": "y2",
            "title": {"text": variables[0]},
            "zeroline": True,
        }
        layout["yaxis2"] = {
            "domain": [0.0, 1.0],
            "anchor": "x2",
            "title": {"text": variables[1]},
            "zeroline": True,
        }
    else:
        layout["xaxis"] = {"title": {"text": "Iteration k"}}
        layout["yaxis"] = {
            "title": {"text": "Error"},
            "type": "log",
            "range": _log_range(error_y + residual_y),
        }
    return PlotPayload(traces=traces, layout=layout)


def _floor(value: float | None) -> float:
    if value is None or not math.isfinite(value):
        return 1e-16
    return min(max(value, 1e-16), 1e2)


def _log_range(values: Sequence[float]) -> list[float]:
    finite = [value for value in values if math.isfinite(value) and value > 0]
    if not finite:
        return [-16.0, 2.0]
    lo = max(min(finite), 1e-16)
    hi = min(max(finite), 1e2)
    if hi <= lo:
        hi = lo * 10.0
    return [math.log10(lo) - 0.3, math.log10(hi) + 0.3]
