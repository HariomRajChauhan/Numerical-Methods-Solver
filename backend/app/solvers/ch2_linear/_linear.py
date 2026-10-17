"""Shared building blocks for the Chapter 2 direct linear-system solvers.

This is a private module (its name starts with an underscore) so the
auto-loader in :mod:`app.solvers` skips it: only the real solver modules
register themselves. It holds the pieces shared by Gauss elimination and
Gauss-Jordan elimination: input validation, LaTeX rendering of systems and
augmented matrices, singular / near-singular classification through matrix
ranks, and the verification graph.
"""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np

from app.core.errors import InvalidInputError
from app.core.models import PlotPayload, SolverLimits
from app.solvers._common import format_num

# unique solution, infinitely many solutions, or an inconsistent system.
SolutionKind = Literal["unique", "infinite", "none"]

MIN_SYSTEM_SIZE = 2
MAX_SYSTEM_SIZE = 10
# Anything below this magnitude counts as a zero pivot.
PIVOT_EPS = 1e-12
# Condition numbers above this flag a badly conditioned (near-singular) matrix.
NEAR_SINGULAR_COND = 1e12


def validate_system(
    matrix: list[list[float]],
    vector: list[float],
    limits: SolverLimits,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate a square coefficient matrix and its matching right-hand side.

    Raises:
        InvalidInputError: If ``A`` is not square, larger than the allowed size,
            or if ``b`` does not have one entry per equation.
    """
    matrix_array = np.asarray(matrix, dtype=float)
    rhs = np.asarray(vector, dtype=float)
    if matrix_array.ndim != 2 or matrix_array.shape[0] != matrix_array.shape[1]:
        raise InvalidInputError(
            "The coefficient matrix A must be square (n x n).",
            hint="Give the grid the same number of rows and columns.",
        )
    size = int(matrix_array.shape[0])
    if size < MIN_SYSTEM_SIZE:
        raise InvalidInputError(
            f"The system must have at least {MIN_SYSTEM_SIZE} equations.",
        )
    if size > MAX_SYSTEM_SIZE or size > limits.max_matrix_size:
        raise InvalidInputError(
            f"The system is too large: at most {MAX_SYSTEM_SIZE} equations are supported.",
        )
    if rhs.ndim != 1 or rhs.shape[0] != size:
        raise InvalidInputError(
            f"The right-hand side b must have {size} entries to match A.",
            hint="Provide exactly one value per equation.",
        )
    if not bool(np.all(np.isfinite(matrix_array))) or not bool(np.all(np.isfinite(rhs))):
        raise InvalidInputError("A and b must contain finite numbers only.")
    return matrix_array, rhs


def variable_names(size: int) -> list[str]:
    """Default unknown labels ``x1, x2, ...``."""
    return [f"x{i}" for i in range(1, size + 1)]


def condition_number(matrix: np.ndarray) -> float:
    """2-norm condition number; ``inf`` for a singular or non-finite matrix."""
    if not bool(np.all(np.isfinite(matrix))):
        return math.inf
    try:
        value = float(np.linalg.cond(matrix))
    except np.linalg.LinAlgError:
        return math.inf
    return value if math.isfinite(value) else math.inf


def classify_solution(matrix: np.ndarray, rhs: np.ndarray) -> tuple[SolutionKind, int, int]:
    """Classify the system through the ranks of ``A`` and ``[A | b]``.

    Returns the kind together with both ranks: ``none`` (inconsistent, no
    solution), ``infinite`` (rank deficient but consistent) or ``unique``.
    """
    augmented = np.column_stack([matrix, rhs])
    rank_a = int(np.linalg.matrix_rank(matrix))
    rank_augmented = int(np.linalg.matrix_rank(augmented))
    size = int(matrix.shape[0])
    if rank_augmented > rank_a:
        return "none", rank_a, rank_augmented
    if rank_a < size:
        return "infinite", rank_a, rank_augmented
    return "unique", rank_a, rank_augmented


def condition_warnings(matrix: np.ndarray) -> list[str]:
    """Warnings for a singular or badly conditioned coefficient matrix."""
    condition = condition_number(matrix)
    if not math.isfinite(condition):
        return [
            "The coefficient matrix is singular (infinite condition number); the "
            "system does not have a unique solution."
        ]
    if condition > NEAR_SINGULAR_COND:
        return [
            "The coefficient matrix is badly conditioned "
            f"(condition number {condition:.3g}); the computed solution may be inaccurate."
        ]
    return []


def finite_or_none(value: float) -> float | None:
    """Return ``value`` when finite, otherwise ``None`` (JSON-safe)."""
    return value if math.isfinite(value) else None


# ---------------------------------------------------------------------------
# LaTeX rendering (exam-style working)
# ---------------------------------------------------------------------------


def matrix_latex(rows: list[list[float]], decimals: int) -> str:
    """A plain bracketed matrix."""
    body = r" \\ ".join(
        " & ".join(format_num(float(value), decimals) for value in row) for row in rows
    )
    return r"\begin{bmatrix} " + body + r" \end{bmatrix}"


def augmented_from_rows(rows: list[list[float]], decimals: int, coefficient_columns: int) -> str:
    """An augmented matrix from full rows, drawing a vertical divider."""
    total_columns = len(rows[0])
    right_columns = total_columns - coefficient_columns
    spec = "c" * coefficient_columns + "|" + "c" * right_columns
    body = r" \\ ".join(
        " & ".join(format_num(float(value), decimals) for value in row) for row in rows
    )
    return rf"\left[\begin{{array}}{{{spec}}} {body} \end{{array}}\right]"


def augmented_latex(matrix: np.ndarray, rhs: np.ndarray, decimals: int) -> str:
    """The augmented matrix ``[A | b]`` rendered with a vertical divider."""
    rows = [
        [float(value) for value in matrix[i]] + [float(rhs[i])] for i in range(matrix.shape[0])
    ]
    return augmented_from_rows(rows, decimals, int(matrix.shape[1]))


def vector_latex(values: list[float], decimals: int) -> str:
    """A column vector."""
    body = r" \\ ".join(format_num(float(value), decimals) for value in values)
    return r"\begin{bmatrix} " + body + r" \end{bmatrix}"


def equations_latex(
    matrix: np.ndarray,
    rhs: np.ndarray,
    names: list[str],
    decimals: int,
) -> str:
    """The system written as ``a x1 + b x2 = c`` lines."""
    lines: list[str] = []
    for i in range(matrix.shape[0]):
        terms: list[tuple[float, str]] = []
        for j in range(matrix.shape[1]):
            coefficient = float(matrix[i, j])
            if coefficient == 0.0:
                continue
            magnitude = format_num(abs(coefficient), decimals)
            symbol = names[j]
            text = symbol if math.isclose(abs(coefficient), 1.0) else f"{magnitude}{symbol}"
            terms.append((coefficient, text))
        left = _linear_expression(terms)
        lines.append(f"{left} = {format_num(float(rhs[i]), decimals)}")
    return r" \\ ".join(lines)


def _linear_expression(terms: list[tuple[float, str]]) -> str:
    """Join ``(coefficient, text)`` terms into ``a - b + c`` form."""
    if not terms:
        return "0"
    first_coefficient, first_text = terms[0]
    expression = ("-" if first_coefficient < 0 else "") + first_text
    for coefficient, text in terms[1:]:
        expression += (" - " if coefficient < 0 else " + ") + text
    return expression


def residual_vector(matrix: np.ndarray, solution: np.ndarray, rhs: np.ndarray) -> list[float]:
    """The verification residual ``A x - b`` as a plain list."""
    residual = matrix @ solution - rhs
    return [float(value) for value in residual]


def system_plot(
    matrix: np.ndarray,
    solution: np.ndarray,
    rhs: np.ndarray,
    names: list[str],
    title: str,
) -> PlotPayload:
    """Bar chart of the solution and the verification residual ``A x - b``."""
    residual = residual_vector(matrix, solution, rhs)
    traces: list[dict[str, Any]] = [
        {
            "type": "bar",
            "name": "Solution x",
            "x": names,
            "y": [float(value) for value in solution],
            "marker": {"color": "#2563eb"},
        },
        {
            "type": "bar",
            "name": "Residual A x - b",
            "x": names,
            "y": residual,
            "marker": {"color": "#dc2626"},
        },
    ]
    layout: dict[str, Any] = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "variable"}},
        "yaxis": {"title": {"text": "value"}},
        "barmode": "group",
    }
    return PlotPayload(traces=traces, layout=layout)
