"""Shared building blocks for the Chapter 2 iterative linear solvers.

Private module (leading underscore) so the auto-loader skips it. It holds the
pieces common to Jacobi and Gauss-Seidel: the diagonal-dominance check, the
sweep functions, the generic iteration driver, the semilog error plot, and the
schema helpers for the initial guess and stopping criterion.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.errors import InvalidInputError
from app.core.models import (
    DataTable,
    InputField,
    PlotPayload,
    SelectOption,
    SolveStatus,
)
from app.solvers._common import format_num
from app.solvers.ch2_linear._linear import PIVOT_EPS

# Above this infinity-norm the iteration is treated as divergent.
MAX_ERROR_BOUND = 1e12

Sweep = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


LINEAR_STOP_CRITERION_OPTIONS: list[SelectOption] = [
    SelectOption(value="absolute", label="||x_k - x_(k-1)||_inf < tolerance"),
    SelectOption(value="relative", label="relative change (inf-norm) < tolerance"),
]


def initial_guess_field() -> InputField:
    """An optional starting vector; blank means the zero vector."""
    return InputField(
        key="initial_guess",
        label="Initial guess x0 (optional)",
        type="vector",
        required=False,
        default=None,
        placeholder="0, 0, 0",
        help="Leave blank to start from the zero vector; otherwise one value per unknown.",
    )


def comparison_field(other_label: str) -> InputField:
    """A checkbox to run the sibling method and compare iteration counts."""
    return InputField(
        key="compare",
        label=f"Compare with {other_label}",
        type="boolean",
        required=False,
        default=True,
        help="Also run the sibling method and compare the number of iterations.",
    )


def stop_criterion_field(default: str = "absolute") -> InputField:
    """Which convergence test ends the iteration."""
    return InputField(
        key="stopping_criterion",
        label="Stopping criterion",
        type="select",
        required=True,
        default=default,
        options=list(LINEAR_STOP_CRITERION_OPTIONS),
        help="The test that must fall below the tolerance for convergence.",
    )


def error_column_label(criterion: str) -> str:
    """Header for the error column of the iteration table."""
    if criterion == "relative":
        return "Relative error"
    return "Error ||x_k - x_(k-1)||_inf"


# ---------------------------------------------------------------------------
# Validation of the initial guess
# ---------------------------------------------------------------------------


def guess_vector(initial_guess: list[float] | None, size: int) -> np.ndarray:
    """Return the starting vector, defaulting to zeros of length ``size``."""
    if initial_guess is None or len(initial_guess) == 0:
        return np.zeros(size)
    guess = np.asarray(initial_guess, dtype=float)
    if guess.shape[0] != size:
        raise InvalidInputError(
            f"The initial guess must have {size} entries to match A.",
            hint="Provide one starting value per unknown, or leave it blank for zeros.",
        )
    return guess


def zero_diagonal_indices(matrix: np.ndarray) -> list[int]:
    """Indices of rows whose diagonal entry is (numerically) zero."""
    return [i for i in range(matrix.shape[0]) if abs(float(matrix[i, i])) < PIVOT_EPS]


# ---------------------------------------------------------------------------
# Diagonal dominance
# ---------------------------------------------------------------------------


@dataclass
class RowDominance:
    """Dominance information for a single equation."""

    index: int
    diagonal: float
    off_diagonal_sum: float

    @property
    def dominant(self) -> bool:
        return abs(self.diagonal) > self.off_diagonal_sum


def dominance_rows(matrix: np.ndarray) -> list[RowDominance]:
    """Per-row diagonal-dominance information."""
    rows: list[RowDominance] = []
    for i in range(matrix.shape[0]):
        diagonal = float(matrix[i, i])
        off = float(sum(abs(float(matrix[i, j])) for j in range(matrix.shape[1]) if j != i))
        rows.append(RowDominance(index=i, diagonal=diagonal, off_diagonal_sum=off))
    return rows


def is_diagonally_dominant(matrix: np.ndarray) -> bool:
    """True when every row is strictly diagonally dominant."""
    return all(row.dominant for row in dominance_rows(matrix))


def dominance_table(matrix: np.ndarray, decimals: int) -> DataTable:
    """Table showing ``|a_ii|`` against the off-diagonal row sum."""
    rows: list[list[Any]] = []
    for row in dominance_rows(matrix):
        rows.append(
            [
                f"R{row.index + 1}",
                format_num(abs(row.diagonal), decimals),
                format_num(row.off_diagonal_sum, decimals),
                "yes" if row.dominant else "no",
            ]
        )
    return DataTable(
        title="Diagonal dominance check",
        columns=["Row", "|a_ii|", "sum |a_ij| (j != i)", "Dominant?"],
        rows=rows,
    )


def dominance_warnings(matrix: np.ndarray) -> list[str]:
    """Warn (without stopping) when the matrix is not diagonally dominant."""
    weak = [row for row in dominance_rows(matrix) if not row.dominant]
    if not weak:
        return []
    parts = [
        f"row {row.index + 1} (|a_ii| = {abs(row.diagonal):.6g} vs off-sum "
        f"{row.off_diagonal_sum:.6g})"
        for row in weak
    ]
    return [
        "The coefficient matrix is not strictly diagonally dominant: "
        + "; ".join(parts)
        + ". Convergence is not guaranteed, but the iteration is still run."
    ]


# ---------------------------------------------------------------------------
# Sweeps and the generic iteration driver
# ---------------------------------------------------------------------------


def jacobi_sweep(current: np.ndarray, matrix: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    """One Jacobi sweep: every unknown uses the previous iterate."""
    size = matrix.shape[0]
    updated = np.empty(size, dtype=float)
    for i in range(size):
        total = float(sum(matrix[i, j] * current[j] for j in range(size) if j != i))
        updated[i] = (float(rhs[i]) - total) / float(matrix[i, i])
    return updated


def gauss_seidel_sweep(current: np.ndarray, matrix: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    """One Gauss-Seidel sweep: reuses each freshly computed unknown at once."""
    work = current.astype(float).copy()
    size = matrix.shape[0]
    for i in range(size):
        total = float(sum(matrix[i, j] * work[j] for j in range(size) if j != i))
        work[i] = (float(rhs[i]) - total) / float(matrix[i, i])
    return work


def convergence_error(criterion: str, new: np.ndarray, old: np.ndarray) -> float:
    """The quantity tested against the tolerance."""
    difference = float(np.max(np.abs(new - old))) if new.size else 0.0
    if criterion == "relative":
        scale = float(np.max(np.abs(new))) if new.size else 0.0
        return difference / scale if scale > 0.0 else difference
    return difference


@dataclass
class IterationOutcome:
    """Result of running an iterative solver to completion."""

    status: SolveStatus
    solution: np.ndarray
    iterations: int
    errors: list[float] = field(default_factory=list)
    history: list[np.ndarray] = field(default_factory=list)

    @property
    def final_error(self) -> float:
        return self.errors[-1] if self.errors else math.inf


def iterate(
    sweep: Sweep,
    matrix: np.ndarray,
    rhs: np.ndarray,
    guess: np.ndarray,
    tolerance: float,
    criterion: str,
    max_iterations: int,
) -> IterationOutcome:
    """Drive an iterative sweep until convergence, divergence or the cap."""
    current = guess.astype(float).copy()
    errors: list[float] = []
    history: list[np.ndarray] = []
    for k in range(1, max_iterations + 1):
        updated = sweep(current, matrix, rhs)
        error = convergence_error(criterion, updated, current)
        errors.append(error)
        history.append(updated)
        current = updated
        if not bool(np.all(np.isfinite(current))) or float(np.max(np.abs(current))) > MAX_ERROR_BOUND:
            return IterationOutcome(SolveStatus.DIVERGED, current, k, errors, history)
        if error < tolerance:
            return IterationOutcome(SolveStatus.CONVERGED, current, k, errors, history)
    return IterationOutcome(SolveStatus.MAX_ITER, current, max_iterations, errors, history)


# ---------------------------------------------------------------------------
# Spectral radius of the iteration matrix
# ---------------------------------------------------------------------------


def jacobi_spectral_radius(matrix: np.ndarray) -> float:
    """Spectral radius of the Jacobi iteration matrix ``I - D^-1 A``."""
    diagonal = np.diag(matrix)
    if any(abs(value) < PIVOT_EPS for value in diagonal):
        return math.inf
    try:
        iteration_matrix = np.eye(matrix.shape[0]) - np.diag(1.0 / diagonal) @ matrix
        return float(np.max(np.abs(np.linalg.eigvals(iteration_matrix))))
    except np.linalg.LinAlgError:
        return math.inf


def gauss_seidel_spectral_radius(matrix: np.ndarray) -> float:
    """Spectral radius of the Gauss-Seidel iteration matrix ``-(D+L)^-1 U``."""
    diagonal = np.diag(matrix)
    if any(abs(value) < PIVOT_EPS for value in diagonal):
        return math.inf
    try:
        lower = np.tril(matrix, -1)
        upper = np.triu(matrix, 1)
        iteration_matrix = -np.linalg.solve(np.diag(diagonal) + lower, upper)
        return float(np.max(np.abs(np.linalg.eigvals(iteration_matrix))))
    except np.linalg.LinAlgError:
        return math.inf


# ---------------------------------------------------------------------------
# Plots and tables
# ---------------------------------------------------------------------------


def iteration_table(
    names: list[str],
    guess: np.ndarray,
    history: list[np.ndarray],
    errors: list[float],
    criterion: str,
    decimals: int,
) -> DataTable:
    """Iteration table: ``iter, x1..xn, error`` (iteration 0 is the guess)."""
    rows: list[list[Any]] = [
        [0, *[format_num(float(value), decimals) for value in guess], "-"]
    ]
    for index, (vector, error) in enumerate(zip(history, errors, strict=False), start=1):
        rows.append(
            [
                index,
                *[format_num(float(value), decimals) for value in vector],
                format_num(error, decimals),
            ]
        )
    return DataTable(
        title="Iterations",
        columns=["Iteration", *names, error_column_label(criterion)],
        rows=rows,
    )


def _log_series(errors: list[float]) -> list[float | None]:
    """Prepare errors for a log axis: zeros floor, non-finite become gaps."""
    prepared: list[float | None] = []
    for value in errors:
        if not math.isfinite(value):
            prepared.append(None)
        elif value <= 0.0:
            prepared.append(1e-16)
        else:
            prepared.append(value)
    return prepared


def error_semilog_plot(series: list[tuple[str, list[float]]], title: str) -> PlotPayload:
    """Semilog error-vs-iteration plot for one or more methods."""
    traces: list[dict[str, Any]] = []
    for name, errors in series:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": name,
                "x": list(range(1, len(errors) + 1)),
                "y": _log_series(errors),
            }
        )
    layout: dict[str, Any] = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "Iteration"}, "dtick": 1},
        "yaxis": {"title": {"text": "Error"}, "type": "log"},
    }
    return PlotPayload(traces=traces, layout=layout)
