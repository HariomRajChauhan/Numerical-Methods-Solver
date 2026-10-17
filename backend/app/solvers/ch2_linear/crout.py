"""Crout LU factorisation.

Factorises ``A = L U`` with a lower-triangular ``L`` that carries the pivots and
a unit upper-triangular ``U`` (ones on the diagonal). The factors are built
element by element with their formulas, then forward substitution solves
``L y = b`` and back-substitution solves ``U x = y``. If a zero pivot appears the
method stops with a clear message suggesting pivoting.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.models import (
    Chapter,
    DataTable,
    ErrorInfo,
    InputField,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.registry import register
from app.solvers._common import format_num, precision_field
from app.solvers.ch2_linear._linear import (
    PIVOT_EPS,
    column_labels,
    condition_number,
    condition_warnings,
    equations_latex,
    factorisation_error,
    finite_or_none,
    lu_zero_pivot_response,
    matrix_latex,
    matrix_table_rows,
    system_plot,
    validate_system,
    variable_names,
    vector_latex,
    verification_rows,
)

META = MethodMeta(
    id="crout",
    chapter=Chapter.CH2_LINEAR,
    name="Crout LU Decomposition",
    summary=(
        "Factorise A = L U with a unit upper-triangular U, then solve by forward "
        "and back substitution."
    ),
    theory=(
        "Crout's method is the transpose arrangement of Doolittle's: it writes "
        "A = L U with L lower triangular (carrying the pivots) and U upper "
        "triangular with ones on its diagonal. The entries follow from L U = A:\n"
        "  - the k-th column of L:  l_ik = a_ik - sum_{s<k} l_is u_sk  (i >= k);\n"
        "  - the k-th row of U:  u_kj = (a_kj - sum_{s<k} l_ks u_sj) / l_kk  "
        "(j > k), with u_kk = 1.\n\n"
        "Once the factors are known the system A x = b is solved in two triangular "
        "passes: forward substitution L y = b, then back-substitution U x = y. The "
        "factorisation is reused for any further right-hand sides.\n\n"
        "The method needs every pivot l_kk to be non-zero. If a zero pivot appears "
        "the elimination cannot continue without exchanging rows, so the equations "
        "must be pivoted (or Gauss elimination with partial pivoting used instead). "
        "A zero pivot that cannot be avoided means A is singular."
    ),
    formulas=[
        LabeledLatex(label="Factorisation", latex=r"A = L U"),
        LabeledLatex(
            label="Column of L",
            latex=r"l_{ik} = a_{ik} - \sum_{s<k} l_{is} u_{sk},\qquad i \ge k",
        ),
        LabeledLatex(
            label="Row of U",
            latex=r"u_{kj} = \frac{1}{l_{kk}}\left(a_{kj} - \sum_{s<k} l_{ks} u_{sj}\right),"
            r"\qquad j > k",
        ),
        LabeledLatex(
            label="Forward substitution",
            latex=r"y_i = \frac{1}{l_{ii}}\left(b_i - \sum_{j<i} l_{ij} y_j\right)",
        ),
        LabeledLatex(label="Back-substitution", latex=r"x_i = y_i - \sum_{j>i} u_{ij} x_j"),
    ],
    pseudocode=(
        "Crout(A, b):\n"
        "    L = 0, U = I\n"
        "    for k = 1 to n:\n"
        "        for i = k to n: L[i][k] = A[i][k] - sum_{s<k} L[i][s] U[s][k]\n"
        "        if L[k][k] ~ 0: report zero pivot, suggest pivoting, stop\n"
        "        for j = k+1 to n:\n"
        "            U[k][j] = (A[k][j] - sum_{s<k} L[k][s] U[s][j]) / L[k][k]\n"
        "    forward substitution: L y = b\n"
        "    back-substitution: U x = y\n"
        "    return x and verify r = A x - b"
    ),
    input_schema=[
        InputField(
            key="matrix",
            label="Coefficient matrix A",
            type="matrix",
            required=True,
            rows=3,
            cols=3,
            default=[[2.0, 1.0, -1.0], [-3.0, -1.0, 2.0], [-2.0, 1.0, 2.0]],
            help="Square grid, from 2x2 up to 10x10. Resize with the +Row / +Col buttons.",
        ),
        InputField(
            key="vector",
            label="Right-hand side b",
            type="vector",
            required=True,
            default=[8.0, -11.0, -3.0],
            placeholder="8, -11, -3",
            help="One value per equation, separated by commas.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Classic 3x3 system",
            description="Textbook system with solution x = (2, 3, -1).",
            inputs={
                "matrix": [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]],
                "vector": [8, -11, -3],
            },
        ),
        MethodExample(
            name="Zero pivot (needs pivoting)",
            description="A zero leading pivot exposes the need to reorder the equations.",
            inputs={
                "matrix": [[0, 2, 1], [1, 1, 0], [2, 1, 1]],
                "vector": [3, 2, 4],
            },
        ),
        MethodExample(
            name="Diagonally dominant 3x3",
            description="Well-conditioned system; solution (1, 2, 3).",
            inputs={
                "matrix": [[4, 1, 1], [1, 5, 2], [1, 2, 6]],
                "vector": [9, 17, 23],
            },
        ),
    ],
)


def _term_text(left: float, right: float, decimals: int) -> str:
    """A formatted product of two factors, e.g. ``(2)(3)``."""
    return (
        f"\\left({format_num(left, decimals)}\\right)"
        f"\\left({format_num(right, decimals)}\\right)"
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run Crout LU factorisation and substitution for the ``inputs``."""
    decimals = int(inputs["decimal_precision"])
    matrix, rhs = validate_system(inputs["matrix"], inputs["vector"], limits)
    size = int(matrix.shape[0])
    names = variable_names(size)

    warnings = condition_warnings(matrix)

    lower = np.zeros((size, size))
    upper = np.eye(size)

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                equations_latex(matrix, rhs, names, decimals)
                + r"\\[3mm] A = "
                + matrix_latex(matrix, decimals)
            ),
            note="Write the equations and the coefficient matrix; write A = L U.",
        )
    ]

    for k in range(size):
        lines: list[str] = []
        for i in range(k, size):
            terms = [_term_text(lower[i, s], upper[s, k], decimals) for s in range(k)]
            total = float(sum(lower[i, s] * upper[s, k] for s in range(k)))
            lower[i, k] = float(matrix[i, k]) - total
            value = float(lower[i, k])
            symbol = f"l_{{{i + 1}{k + 1}}}"
            if k == 0:
                lines.append(
                    f"{symbol} = a_{{{i + 1}{k + 1}}} = {format_num(value, decimals)}"
                )
            else:
                joined = " + ".join(terms)
                lines.append(
                    f"{symbol} = {format_num(float(matrix[i, k]), decimals)} - "
                    f"\\left[{joined}\\right] = {format_num(value, decimals)}"
                )

        pivot = float(lower[k, k])
        if abs(pivot) < PIVOT_EPS:
            steps.append(
                Step(
                    title=f"Zero pivot at l_{{{k + 1}{k + 1}}}",
                    latex=r" \\ ".join(lines),
                    note="The pivot is zero, so Crout cannot continue unpivoted.",
                )
            )
            return lu_zero_pivot_response(
                META.id,
                "Crout's method",
                f"l_{{{k + 1}{k + 1}}}",
                k,
                matrix,
                rhs,
                steps,
                warnings,
            )

        for j in range(k + 1, size):
            terms = [_term_text(lower[k, s], upper[s, j], decimals) for s in range(k)]
            total = float(sum(lower[k, s] * upper[s, j] for s in range(k)))
            upper[k, j] = (float(matrix[k, j]) - total) / pivot
            value = float(upper[k, j])
            symbol = f"u_{{{k + 1}{j + 1}}}"
            if k == 0:
                lines.append(
                    f"{symbol} = {format_num(float(matrix[k, j]), decimals)} / "
                    f"{format_num(pivot, decimals)} = {format_num(value, decimals)}"
                )
            else:
                joined = " + ".join(terms)
                lines.append(
                    f"{symbol} = \\left({format_num(float(matrix[k, j]), decimals)} - "
                    f"\\left[{joined}\\right]\\right) / {format_num(pivot, decimals)} = "
                    f"{format_num(value, decimals)}"
                )

        steps.append(
            Step(
                title=f"Build column {k + 1} of L and row {k + 1} of U",
                latex=r" \\ ".join(lines) + f" \\\\[2mm] u_{{{k + 1}{k + 1}}} = 1",
                note=f"Uses the pivot l_{{{k + 1}{k + 1}}} = {format_num(pivot, decimals)}.",
            )
        )

    steps.append(
        Step(
            title="Factors L and U",
            latex=(
                r"L = " + matrix_latex(lower, decimals)
                + r"\\[2mm] U = " + matrix_latex(upper, decimals)
                + r"\\[2mm] L U = " + matrix_latex(lower @ upper, decimals)
            ),
            note="Check that L U reproduces A.",
        )
    )

    solution_y = np.zeros(size)
    substitution_rows: list[list[Any]] = []
    for i in range(size):
        total = float(sum(lower[i, j] * solution_y[j] for j in range(i)))
        solution_y[i] = (float(rhs[i]) - total) / float(lower[i, i])
        substitution_rows.append(
            ["Forward (L y = b)", f"y{i + 1}", format_num(float(solution_y[i]), decimals)]
        )
        if i == 0:
            latex = (
                f"y_1 = {format_num(float(rhs[0]), decimals)} / "
                f"{format_num(float(lower[0, 0]), decimals)} = "
                f"{format_num(float(solution_y[0]), decimals)}"
            )
        else:
            symbolic = " + ".join(f"l_{{{i + 1}{j + 1}}} y_{{{j + 1}}}" for j in range(i))
            latex = (
                f"y_{{{i + 1}}} = \\frac{{b_{{{i + 1}}} - \\left({symbolic}\\right)}}"
                f"{{l_{{{i + 1}{i + 1}}}}} = "
                f"\\frac{{{format_num(float(rhs[i]), decimals)} - "
                f"{format_num(total, decimals)}}}"
                f"{{{format_num(float(lower[i, i]), decimals)}}} = "
                f"{format_num(float(solution_y[i]), decimals)}"
            )
        steps.append(
            Step(
                title=f"Forward substitution: y{i + 1}",
                latex=latex,
                note="Solve the lower-triangular system top to bottom.",
            )
        )

    solution = np.zeros(size)
    for i in range(size - 1, -1, -1):
        total = float(sum(upper[i, j] * solution[j] for j in range(i + 1, size)))
        solution[i] = float(solution_y[i]) - total
        substitution_rows.append(
            ["Back (U x = y)", f"x{i + 1}", format_num(float(solution[i]), decimals)]
        )
        if i == size - 1:
            latex = (
                f"x_{{{i + 1}}} = y_{{{i + 1}}} = "
                f"{format_num(float(solution[i]), decimals)}"
            )
        else:
            symbolic = " + ".join(f"u_{{{i + 1}{j + 1}}} x_{{{j + 1}}}" for j in range(i + 1, size))
            latex = (
                f"x_{{{i + 1}}} = y_{{{i + 1}}} - \\left({symbolic}\\right) = "
                f"{format_num(float(solution_y[i]), decimals)} - "
                f"\\left({format_num(total, decimals)}\\right) = "
                f"{format_num(float(solution[i]), decimals)}"
            )
        steps.append(
            Step(
                title=f"Back-substitution: x{i + 1}",
                latex=latex,
                note="U has a unit diagonal, so no division is required.",
            )
        )

    residual = matrix @ solution - rhs
    residual_norm = float(np.linalg.norm(residual, ord=np.inf))
    rhs_norm = float(np.linalg.norm(rhs, ord=np.inf))
    relative = (residual_norm / rhs_norm * 100.0) if rhs_norm > 0 else None

    steps.append(
        Step(
            title="Verification",
            latex=(
                r"\text{Substitute } x \text{ back: } A x = "
                + vector_latex([float(value) for value in matrix @ solution], decimals)
                + r"\approx b = "
                + vector_latex([float(value) for value in rhs], decimals)
                + r"\\[2mm] A x - b = "
                + vector_latex([float(value) for value in residual], decimals)
            ),
            note="The residual should be (numerically) zero.",
        )
    )

    result = {
        "L": [[float(value) for value in lower[i]] for i in range(size)],
        "U": [[float(value) for value in upper[i]] for i in range(size)],
        "solution": {names[i]: float(solution[i]) for i in range(size)},
        "solution_vector": [float(value) for value in solution],
        "factorisation": "crout",
        "condition_number": finite_or_none(condition_number(matrix)),
        "residual_norm": residual_norm,
        "relative_residual_percent": relative,
        "factorisation_error": factorisation_error(matrix, lower, upper),
    }

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=[
            DataTable(
                title="L factor (lower triangular)",
                columns=["Row", *column_labels(size)],
                rows=matrix_table_rows(lower, decimals),
            ),
            DataTable(
                title="U factor (unit upper triangular)",
                columns=["Row", *column_labels(size)],
                rows=matrix_table_rows(upper, decimals),
            ),
            DataTable(
                title="Forward and back substitution",
                columns=["Stage", "Unknown", "Value"],
                rows=substitution_rows,
            ),
            DataTable(
                title="Solution and verification",
                columns=["Unknown", "x_i", "(A x)_i", "b_i", "Residual"],
                rows=verification_rows(matrix, solution, rhs, names, decimals),
            ),
        ],
        plot=system_plot(matrix, solution, rhs, names, "Crout: solution and residual"),
        errors=ErrorInfo(absolute=residual_norm, relative_percent=relative),
        warnings=warnings,
    )
