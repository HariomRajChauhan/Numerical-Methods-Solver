"""Gauss-Jordan elimination.

The augmented matrix ``[A | b]`` is reduced all the way to reduced row-echelon
form: each pivot row is scaled to a unit pivot and every other row is cleared in
that column, so the right-hand column is the solution directly. Partial pivoting
is applied automatically for stability and the result is verified with
``A x - b``.
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
    PlotPayload,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.registry import register
from app.solvers._common import failed_response, format_num, precision_field
from app.solvers.ch2_linear._linear import (
    PIVOT_EPS,
    augmented_from_rows,
    augmented_latex,
    classify_solution,
    condition_number,
    condition_warnings,
    equations_latex,
    finite_or_none,
    residual_vector,
    system_plot,
    validate_system,
    variable_names,
    vector_latex,
)

META = MethodMeta(
    id="gauss_jordan",
    chapter=Chapter.CH2_LINEAR,
    name="Gauss-Jordan Elimination",
    summary=(
        "Reduce the augmented matrix [A | b] to reduced row-echelon form so the "
        "solution is read off directly, with no back-substitution."
    ),
    theory=(
        "Gauss-Jordan elimination continues the row operations above the pivot as "
        "well as below it. Each pivot row is first scaled so that its pivot equals "
        "one, and then that column is cleared from every other row. Once the "
        "coefficient block has become the identity matrix the right-hand column is "
        "the solution x, read off directly.\n\n"
        "For numerical stability the pivot row is chosen by partial pivoting: at "
        "each column the row with the largest magnitude entry on or below the "
        "diagonal is swapped into place. This keeps every multiplier within "
        "[-1, 1] and avoids dividing by a small pivot.\n\n"
        "The same reduction applied to the augmented matrix [A | I] turns the "
        "right block into the inverse A^-1, which is how the matrix-inversion "
        "method in this chapter works. A zero pivot means the matrix is singular; "
        "the ranks of A and [A | b] then distinguish a unique solution, infinitely "
        "many solutions, or an inconsistent system."
    ),
    formulas=[
        LabeledLatex(
            label="Pivot normalisation",
            latex=r"R_k \leftarrow \frac{R_k}{a_{kk}}",
        ),
        LabeledLatex(
            label="Full elimination",
            latex=r"R_i \leftarrow R_i - a_{ik}\,R_k,\qquad i \ne k",
        ),
        LabeledLatex(
            label="Reduced row-echelon form",
            latex=r"\left[ A \mid b \right] \longrightarrow \left[ I \mid x \right]",
        ),
        LabeledLatex(label="Partial pivoting", latex=r"p = \arg\max_{i\ge k} \left|a_{ik}\right|"),
        LabeledLatex(label="Verification", latex=r"r = A x - b \approx 0"),
    ],
    pseudocode=(
        "GaussJordan(A, b):\n"
        "    form augmented matrix M = [A | b]\n"
        "    for k = 1 to n:\n"
        "        swap in the row with max |M[i][k]| (i >= k)   # partial pivoting\n"
        "        if |M[k][k]| ~ 0: report singular / no solution and stop\n"
        "        M[k] <- M[k] / M[k][k]                        # unit pivot\n"
        "        for i = 1 to n, i != k:\n"
        "            M[i] <- M[i] - M[i][k] * M[k]             # clear the column\n"
        "    x = last column of M\n"
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
            name="Zero leading pivot (auto-pivoted)",
            description="A zero diagonal entry that automatic partial pivoting repairs.",
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


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run Gauss-Jordan elimination for the validated ``inputs``."""
    decimals = int(inputs["decimal_precision"])
    matrix, rhs = validate_system(inputs["matrix"], inputs["vector"], limits)
    size = int(matrix.shape[0])
    names = variable_names(size)

    warnings = condition_warnings(matrix)

    working = [
        [float(matrix[i, j]) for j in range(size)] + [float(rhs[i])] for i in range(size)
    ]

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                equations_latex(matrix, rhs, names, decimals)
                + r" \\[3mm] \text{Augmented matrix } [A \mid b] = "
                + augmented_latex(matrix, rhs, decimals)
            ),
            note="Write the equations and build the augmented matrix [A | b].",
        )
    ]
    operations: list[list[Any]] = []
    row_swaps = 0

    for column in range(size):
        pivot_row = max(range(column, size), key=lambda i: abs(working[i][column]))
        if pivot_row != column and abs(working[pivot_row][column]) > PIVOT_EPS:
            working[column], working[pivot_row] = working[pivot_row], working[column]
            row_swaps += 1
            operations.append([f"R{column + 1} <-> R{pivot_row + 1}", "-", "-"])
            steps.append(
                Step(
                    title=f"Partial pivot for column {column + 1}",
                    latex=(
                        f"R_{{{column + 1}}} \\leftrightarrow R_{{{pivot_row + 1}}}"
                        r"\\[3mm]"
                        + augmented_from_rows(working, decimals, size)
                    ),
                    note=(
                        f"Largest magnitude in column {column + 1} is "
                        f"{format_num(working[column][column], decimals)} in row "
                        f"{pivot_row + 1}; swap it into the pivot position."
                    ),
                )
            )

        pivot = working[column][column]
        if abs(pivot) < PIVOT_EPS:
            return _singular_response(matrix, rhs, warnings, steps)

        for j in range(column, size + 1):
            working[column][j] /= pivot
        working[column][column] = 1.0
        operations.append(
            [
                f"R{column + 1} <- R{column + 1} / ({format_num(pivot, decimals)})",
                f"R{column + 1}",
                "-",
            ]
        )
        steps.append(
            Step(
                title=f"Normalise pivot row {column + 1}",
                latex=(
                    f"R_{{{column + 1}}} \\leftarrow "
                    f"\\frac{{R_{{{column + 1}}}}}{{{format_num(pivot, decimals)}}}"
                    r"\\[3mm]"
                    + augmented_from_rows(working, decimals, size)
                ),
                note=f"Scale row {column + 1} so the pivot becomes 1.",
            )
        )

        for row in range(size):
            if row == column:
                continue
            current = working[row][column]
            if abs(current) <= PIVOT_EPS:
                working[row][column] = 0.0
                continue
            factor = current
            for j in range(column, size + 1):
                working[row][j] -= factor * working[column][j]
            working[row][column] = 0.0
            operations.append(
                [
                    f"R{row + 1} <- R{row + 1} - ({format_num(factor, decimals)})R{column + 1}",
                    f"R{column + 1}",
                    format_num(factor, decimals),
                ]
            )
            steps.append(
                Step(
                    title=f"Eliminate column {column + 1} from row {row + 1}",
                    latex=(
                        f"R_{{{row + 1}}} \\leftarrow R_{{{row + 1}}} - "
                        f"\\left({format_num(factor, decimals)}\\right) R_{{{column + 1}}}"
                        r"\\[3mm]"
                        + augmented_from_rows(working, decimals, size)
                    ),
                    note=(
                        f"Clear column {column + 1}: subtract "
                        f"{format_num(factor, decimals)} times row {column + 1}."
                    ),
                )
            )

    solution = [working[i][size] for i in range(size)]
    solution_array = np.asarray(solution, dtype=float)

    steps.append(
        Step(
            title="Reduced row-echelon form",
            latex=(
                r"\left[ A \mid b \right] = "
                + augmented_from_rows(working, decimals, size)
                + r"\\[2mm] x = "
                + vector_latex(solution, decimals)
            ),
            note="The left block is the identity, so the right column is the solution.",
        )
    )

    residual = residual_vector(matrix, solution_array, rhs)
    residual_norm = float(np.linalg.norm(residual, ord=np.inf))
    rhs_norm = float(np.linalg.norm(rhs, ord=np.inf))
    relative = (residual_norm / rhs_norm * 100.0) if rhs_norm > 0 else None
    axial = matrix @ solution_array

    verify_rows: list[list[Any]] = []
    for i in range(size):
        verify_rows.append(
            [
                names[i],
                format_num(float(solution[i]), decimals),
                format_num(float(axial[i]), decimals),
                format_num(float(rhs[i]), decimals),
                format_num(residual[i], decimals),
            ]
        )

    steps.append(
        Step(
            title="Verification",
            latex=(
                r"\text{Substitute } x \text{ back: }"
                r"\\[2mm] A x = "
                + vector_latex([float(value) for value in axial], decimals)
                + r"\approx b = "
                + vector_latex([float(value) for value in rhs], decimals)
                + r"\\[2mm] A x - b = "
                + vector_latex(residual, decimals)
            ),
            note="The residual should be (numerically) zero.",
        )
    )

    result = {
        "solution": {names[i]: float(solution[i]) for i in range(size)},
        "solution_vector": [float(value) for value in solution],
        "classification": "unique",
        "pivoting": "partial",
        "condition_number": finite_or_none(condition_number(matrix)),
        "residual_norm": residual_norm,
        "relative_residual_percent": relative,
        "row_swaps": row_swaps,
        "variable_order": list(names),
    }

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=[
            DataTable(
                title="Row operations",
                columns=["Operation", "Pivot row", "Multiplier m"],
                rows=operations,
            ),
            DataTable(
                title="Solution and verification",
                columns=["Unknown", "x_i", "(A x)_i", "b_i", "Residual"],
                rows=verify_rows,
            ),
        ],
        plot=system_plot(
            matrix, solution_array, rhs, names, "Gauss-Jordan: solution and residual"
        ),
        errors=ErrorInfo(absolute=residual_norm, relative_percent=relative),
        warnings=warnings,
    )


def _singular_response(
    matrix: np.ndarray,
    rhs: np.ndarray,
    warnings: list[str],
    steps: list[Step],
) -> SolveResponse:
    """HTTP-200 ``failed`` response when no unique solution can be produced."""
    kind, rank_a, rank_augmented = classify_solution(matrix, rhs)
    if kind == "none":
        message = (
            "The system is inconsistent: no solution exists because "
            f"rank(A) = {rank_a} is less than rank([A | b]) = {rank_augmented}."
        )
    elif kind == "infinite":
        message = (
            "The coefficient matrix is singular, so there are infinitely many "
            f"solutions (rank(A) = rank([A | b]) = {rank_a} < {matrix.shape[0]})."
        )
    else:
        message = (
            "A zero pivot was encountered even after partial pivoting; the "
            "coefficient matrix is singular."
        )
    return failed_response(
        META.id,
        message,
        steps=steps,
        result={
            "classification": kind,
            "rank": rank_a,
            "rank_augmented": rank_augmented,
            "condition_number": finite_or_none(condition_number(matrix)),
        },
        plot=PlotPayload(),
        warnings=warnings,
    )
