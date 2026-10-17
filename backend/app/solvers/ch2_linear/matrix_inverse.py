"""Matrix inversion by Gauss-Jordan elimination.

The matrix is augmented with the identity, ``[A | I]``, and reduced with
Gauss-Jordan elimination (automatic partial pivoting) until the left block is
the identity; the right block is then the inverse ``A^-1``. Every row operation
is shown, and the result is verified by forming ``A A^-1`` and comparing it with
``I``.
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
from app.solvers._common import failed_response, format_num, precision_field
from app.solvers.ch2_linear._linear import (
    PIVOT_EPS,
    augmented_from_rows,
    column_labels,
    condition_number,
    condition_warnings,
    finite_or_none,
    matrix_heatmap,
    matrix_latex,
    matrix_table_rows,
    row_labels,
    validate_matrix,
)

_CLASSIC = [[2.0, 1.0, -1.0], [-3.0, -1.0, 2.0], [-2.0, 1.0, 2.0]]

META = MethodMeta(
    id="matrix_inverse",
    chapter=Chapter.CH2_LINEAR,
    name="Matrix Inversion",
    summary=(
        "Compute A^-1 by applying Gauss-Jordan elimination to the augmented matrix "
        "[A | I]; the identity block becomes the inverse."
    ),
    theory=(
        "The inverse of a square matrix A is the matrix A^-1 with "
        "A A^-1 = A^-1 A = I. It can be computed with the same row operations used "
        "to solve a linear system.\n\n"
        "Augment A with the identity matrix to form [A | I]. Any elementary row "
        "operation applied to a row of A is applied simultaneously to the matching "
        "row of I; applying Gauss-Jordan elimination to force the left block into "
        "the identity I therefore transforms the right block into A^-1, i.e.\n"
        "  [A | I]  ->  [I | A^-1].\n\n"
        "Each pivot row is first scaled so its pivot becomes one, then that column "
        "is cleared from every other row. Partial pivoting (swapping in the "
        "largest-magnitude entry of the current column) keeps the multipliers small "
        "and the computation stable.\n\n"
        "If a pivot is zero after pivoting, rank(A) < n: the matrix is singular and "
        "has no inverse. The condition number measures how close A is to singular; "
        "a very large value warns that the computed inverse may be inaccurate."
    ),
    formulas=[
        LabeledLatex(
            label="Augmented matrix",
            latex=r"\left[ A \mid I \right] \longrightarrow \left[ I \mid A^{-1} \right]",
        ),
        LabeledLatex(label="Pivot normalisation", latex=r"R_k \leftarrow \frac{R_k}{a_{kk}}"),
        LabeledLatex(
            label="Full elimination",
            latex=r"R_i \leftarrow R_i - a_{ik}\,R_k,\qquad i \ne k",
        ),
        LabeledLatex(label="Defining property", latex=r"A A^{-1} = A^{-1} A = I"),
        LabeledLatex(label="Verification", latex=r"\left\| A A^{-1} - I \right\| \approx 0"),
    ],
    pseudocode=(
        "Inverse(A):\n"
        "    form the augmented matrix M = [A | I]\n"
        "    for k = 1 to n:\n"
        "        swap in the row with max |M[i][k]| (i >= k)   # partial pivoting\n"
        "        if |M[k][k]| ~ 0: report singular matrix and stop\n"
        "        M[k] <- M[k] / M[k][k]                        # unit pivot\n"
        "        for i != k: M[i] <- M[i] - M[i][k] * M[k]     # clear column k\n"
        "    return the right block of M as A^-1\n"
        "    verify A A^-1 = I"
    ),
    input_schema=[
        InputField(
            key="matrix",
            label="Coefficient matrix A",
            type="matrix",
            required=True,
            rows=3,
            cols=3,
            default=_CLASSIC,
            help="Square grid, from 2x2 up to 10x10. Resize with the +Row / +Col buttons.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Classic 3x3 matrix",
            description="Textbook matrix; its inverse is computed and verified.",
            inputs={"matrix": _CLASSIC},
        ),
        MethodExample(
            name="Simple 2x2 matrix",
            description="A quick 2x2 inverse: [[4, 7], [2, 6]].",
            inputs={"matrix": [[4, 7], [2, 6]]},
        ),
        MethodExample(
            name="Diagonally dominant 3x3",
            description="Well-conditioned matrix [[4, 1, 1], [1, 5, 2], [1, 2, 6]].",
            inputs={"matrix": [[4, 1, 1], [1, 5, 2], [1, 2, 6]]},
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run Gauss-Jordan matrix inversion for the validated ``inputs``."""
    decimals = int(inputs["decimal_precision"])
    matrix = validate_matrix(inputs["matrix"], limits)
    size = int(matrix.shape[0])

    warnings = condition_warnings(matrix)

    working = [
        [float(matrix[i, j]) for j in range(size)]
        + [1.0 if i == j else 0.0 for j in range(size)]
        for i in range(size)
    ]

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"A = " + matrix_latex(matrix, decimals)
                + r"\\[3mm] \left[ A \mid I \right] = "
                + augmented_from_rows(working, decimals, size)
            ),
            note="Augment A with the identity matrix and reduce the left block to I.",
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
                        f"Largest magnitude in column {column + 1} is in row "
                        f"{pivot_row + 1}; swap it into the pivot position."
                    ),
                )
            )

        pivot = working[column][column]
        if abs(pivot) < PIVOT_EPS:
            return _singular_response(matrix, warnings, steps, operations)

        for j in range(2 * size):
            working[column][j] /= pivot
        operations.append(
            [
                f"R{column + 1} <- R{column + 1} / ({format_num(pivot, decimals)})",
                f"R{column + 1}",
                format_num(1.0 / pivot, decimals),
            ]
        )
        steps.append(
            Step(
                title=f"Normalise pivot row {column + 1}",
                latex=(
                    f"R_{{{column + 1}}} \\leftarrow \\frac{{R_{{{column + 1}}}}}"
                    f"{{{format_num(pivot, decimals)}}}"
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
            for j in range(2 * size):
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

    inverse = np.array([[working[i][size + j] for j in range(size)] for i in range(size)])

    steps.append(
        Step(
            title="Reduced form [I | A^-1]",
            latex=(
                r"\left[ I \mid A^{-1} \right] = "
                + augmented_from_rows(working, decimals, size)
                + r"\\[2mm] A^{-1} = "
                + matrix_latex(inverse, decimals)
            ),
            note="The left block is now I, so the right block is the inverse.",
        )
    )

    product = matrix @ inverse
    identity = np.eye(size)
    error = product - identity
    max_error = float(np.max(np.abs(error))) if size else 0.0
    diagonal = np.diag(product)

    verify_rows: list[list[Any]] = []
    for i in range(size):
        off_diagonal = [abs(float(product[i, j])) for j in range(size) if j != i]
        verify_rows.append(
            [
                row_labels(size)[i],
                format_num(float(diagonal[i]), decimals),
                format_num(max(off_diagonal) if off_diagonal else 0.0, decimals),
                format_num(float(diagonal[i] - 1.0), decimals),
            ]
        )

    steps.append(
        Step(
            title="Verification A x A^-1 = I",
            latex=(
                r"A A^{-1} = "
                + matrix_latex(product, decimals)
                + r"\approx I,\qquad \max\left| A A^{-1} - I \right| = "
                + format_num(max_error, decimals)
            ),
            note="The product should be the identity matrix to within round-off.",
        )
    )

    result = {
        "inverse": [[float(value) for value in inverse[i]] for i in range(size)],
        "singular": False,
        "condition_number": finite_or_none(condition_number(matrix)),
        "max_identity_error": max_error,
        "row_swaps": row_swaps,
    }

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=[
            DataTable(
                title="Row operations",
                columns=["Operation", "Pivot row", "Multiplier"],
                rows=operations,
            ),
            DataTable(
                title="Inverse A^-1",
                columns=["Row", *column_labels(size)],
                rows=matrix_table_rows(inverse, decimals),
            ),
            DataTable(
                title="Verification A x A^-1",
                columns=["Row", "(A A^-1)_ii", "Max |off-diagonal|", "Diagonal error"],
                rows=verify_rows,
            ),
        ],
        plot=matrix_heatmap(inverse, "Inverse matrix A^-1"),
        errors=ErrorInfo(absolute=max_error),
        warnings=warnings,
    )


def _singular_response(
    matrix: np.ndarray,
    warnings: list[str],
    steps: list[Step],
    operations: list[list[Any]],
) -> SolveResponse:
    """HTTP-200 ``failed`` response when the matrix has no inverse."""
    rank = int(np.linalg.matrix_rank(matrix))
    size = int(matrix.shape[0])
    message = (
        "The matrix is singular and has no inverse: "
        f"rank(A) = {rank} < {size}. A zero pivot appeared even after partial pivoting."
    )
    return failed_response(
        META.id,
        message,
        steps=steps,
        result={
            "singular": True,
            "rank": rank,
            "condition_number": finite_or_none(condition_number(matrix)),
        },
        errors=ErrorInfo(absolute=None),
        warnings=warnings,
    )
