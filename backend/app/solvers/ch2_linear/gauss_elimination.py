"""Gauss elimination with none / partial / complete pivoting.

The augmented matrix ``[A | b]`` is reduced to upper-triangular form by a
forward-elimination sweep; the unknowns then follow by back-substitution. Every
row operation is shown with its multiplier, pivoting choices are explained, and
the solution is verified through the residual ``A x - b``.
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
    SelectOption,
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

PIVOTING_OPTIONS = [
    SelectOption(value="none", label="None (use the diagonal entries)"),
    SelectOption(value="partial", label="Partial (largest |a_ik| in the column)"),
    SelectOption(value="complete", label="Complete (largest entry in the submatrix)"),
]

META = MethodMeta(
    id="gauss_elimination",
    chapter=Chapter.CH2_LINEAR,
    name="Gauss Elimination",
    summary=(
        "Solve A x = b by forward elimination to an upper-triangular system, with "
        "none, partial or complete pivoting, then back-substitute."
    ),
    theory=(
        "Gaussian elimination solves A x = b by removing unknowns one column at a "
        "time. The equations are stored as the augmented matrix [A | b]; the "
        "elementary row operation R_i <- R_i - m R_k with multiplier "
        "m = a_ik / a_kk clears the entry below the pivot a_kk and leaves the "
        "solution set unchanged.\n\n"
        "After the forward sweep has zeroed everything below the diagonal the "
        "coefficient block is upper triangular, so the unknowns follow one at a "
        "time by back-substitution, from x_n up to x_1.\n\n"
        "If a pivot is zero (or very small) the elimination would divide by a tiny "
        "number and amplify round-off error. Pivoting avoids this by reordering "
        "the equations and unknowns:\n"
        "  - none: use the diagonal entries as they stand;\n"
        "  - partial: swap in the row whose entry in the current column has the "
        "largest magnitude;\n"
        "  - complete: swap in the largest-magnitude entry of the whole remaining "
        "submatrix, swapping columns (and therefore unknowns) as well.\n\n"
        "A singular matrix is revealed by the ranks: rank(A) < rank([A | b]) means "
        "the system is inconsistent (no solution), while "
        "rank(A) = rank([A | b]) < n means it has infinitely many solutions. The "
        "condition number measures how close the system is to singular."
    ),
    formulas=[
        LabeledLatex(
            label="Elimination step",
            latex=r"R_i \leftarrow R_i - m\,R_k,\qquad m = \frac{a_{ik}}{a_{kk}}",
        ),
        LabeledLatex(
            label="Back-substitution",
            latex=r"x_i = \frac{1}{a_{ii}}\left(b_i - \sum_{j>i} a_{ij}x_j\right)",
        ),
        LabeledLatex(label="Partial pivoting", latex=r"p = \arg\max_{i\ge k} \left|a_{ik}\right|"),
        LabeledLatex(
            label="Complete pivoting",
            latex=r"(p,q) = \arg\max_{i,j\ge k} \left|a_{ij}\right|",
        ),
        LabeledLatex(label="Verification", latex=r"r = A x - b \approx 0"),
    ],
    pseudocode=(
        "GaussElimination(A, b, pivoting):\n"
        "    form augmented matrix M = [A | b]\n"
        "    for k = 1 to n:\n"
        "        if pivoting = partial: swap in row with max |M[i][k]| (i >= k)\n"
        "        if pivoting = complete: swap in largest |M[i][j]| (i, j >= k)\n"
        "                                and track the column/variable order\n"
        "        if |M[k][k]| ~ 0: report singular / no solution and stop\n"
        "        for i = k+1 to n:\n"
        "            m = M[i][k] / M[k][k]\n"
        "            M[i] <- M[i] - m * M[k]\n"
        "    back-substitute x_n, ..., x_1\n"
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
        InputField(
            key="pivoting",
            label="Pivoting",
            type="select",
            required=True,
            default="partial",
            options=PIVOTING_OPTIONS,
            help="How the pivot is chosen. Partial is a good default.",
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
                "pivoting": "partial",
            },
        ),
        MethodExample(
            name="Zero leading pivot (needs pivoting)",
            description="A zero on the diagonal that partial pivoting repairs.",
            inputs={
                "matrix": [[0, 2, 1], [1, 1, 0], [2, 1, 1]],
                "vector": [3, 2, 4],
                "pivoting": "partial",
            },
        ),
        MethodExample(
            name="Diagonally dominant 3x3",
            description="Solves cleanly even without pivoting; solution (1, 2, 3).",
            inputs={
                "matrix": [[4, 1, 1], [1, 5, 2], [1, 2, 6]],
                "vector": [9, 17, 23],
                "pivoting": "none",
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run Gauss elimination for the validated ``inputs``."""
    pivoting: str = inputs["pivoting"]
    decimals = int(inputs["decimal_precision"])
    matrix, rhs = validate_system(inputs["matrix"], inputs["vector"], limits)
    size = int(matrix.shape[0])
    names = variable_names(size)

    warnings = condition_warnings(matrix)

    working = [
        [float(matrix[i, j]) for j in range(size)] + [float(rhs[i])] for i in range(size)
    ]
    order = list(range(size))

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
    column_swaps = 0

    for column in range(size):
        if pivoting == "partial":
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
        elif pivoting == "complete":
            pivot_row, pivot_column = max(
                ((i, j) for i in range(column, size) for j in range(column, size)),
                key=lambda pair: abs(working[pair[0]][pair[1]]),
            )
            swaps: list[str] = []
            if pivot_row != column and abs(working[pivot_row][pivot_column]) > PIVOT_EPS:
                working[column], working[pivot_row] = working[pivot_row], working[column]
                row_swaps += 1
                swaps.append(f"R_{{{column + 1}}} \\leftrightarrow R_{{{pivot_row + 1}}}")
                operations.append([f"R{column + 1} <-> R{pivot_row + 1}", "-", "-"])
            if pivot_column != column and abs(working[column][pivot_column]) > PIVOT_EPS:
                for entry in working:
                    entry[column], entry[pivot_column] = entry[pivot_column], entry[column]
                order[column], order[pivot_column] = order[pivot_column], order[column]
                column_swaps += 1
                swaps.append(f"C_{{{column + 1}}} \\leftrightarrow C_{{{pivot_column + 1}}}")
                operations.append([f"C{column + 1} <-> C{pivot_column + 1}", "-", "-"])
            if swaps:
                steps.append(
                    Step(
                        title=f"Complete pivot for column {column + 1}",
                        latex=(
                            " ,\\quad ".join(swaps)
                            + r"\\[3mm]"
                            + augmented_from_rows(working, decimals, size)
                        ),
                        note=(
                            f"Largest entry of the remaining submatrix is "
                            f"{format_num(working[column][column], decimals)}; the unknowns now "
                            "follow the order "
                            f"({', '.join(names[order[j]] for j in range(size))})."
                        ),
                    )
                )

        pivot = working[column][column]
        if abs(pivot) < PIVOT_EPS:
            return _singular_response(
                matrix, rhs, pivoting, warnings, steps, operations
            )

        for row in range(column + 1, size):
            current = working[row][column]
            if abs(current) <= PIVOT_EPS:
                working[row][column] = 0.0
                continue
            factor = current / working[column][column]
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
                        f"Multiplier m = {format_num(current, decimals)} / "
                        f"{format_num(working[column][column], decimals)} = "
                        f"{format_num(factor, decimals)}, so A[{row + 1},{column + 1}] becomes 0."
                    ),
                )
            )

    solution_permuted = [0.0] * size
    substitution_rows: list[list[Any]] = []
    for column in range(size - 1, -1, -1):
        pivot = working[column][column]
        total = working[column][size]
        numerator = format_num(total, decimals)
        accumulated = 0.0
        for j in range(column + 1, size):
            accumulated += working[column][j] * solution_permuted[j]
            term = (
                f"\\left({format_num(working[column][j], decimals)}\\right)"
                f"\\left({format_num(solution_permuted[j], decimals)}\\right)"
            )
            numerator += f" - {term}"
        value = (total - accumulated) / pivot
        solution_permuted[column] = value
        variable = names[order[column]]
        substitution_rows.append([variable, format_num(value, decimals)])
        steps.append(
            Step(
                title=f"Back-substitute {variable}",
                latex=(
                    f"{variable} = \\frac{{{numerator}}}{{{format_num(pivot, decimals)}}}"
                    f" = {format_num(value, decimals)}"
                ),
                note="Solve the current row for its remaining unknown.",
            )
        )

    solution = [0.0] * size
    for column in range(size):
        solution[order[column]] = solution_permuted[column]
    solution_array = np.asarray(solution, dtype=float)

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
        "pivoting": pivoting,
        "condition_number": finite_or_none(condition_number(matrix)),
        "residual_norm": residual_norm,
        "relative_residual_percent": relative,
        "row_swaps": row_swaps,
        "column_swaps": column_swaps,
        "variable_order": [names[order[j]] for j in range(size)],
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
            matrix, solution_array, rhs, names, "Gauss elimination: solution and residual"
        ),
        errors=ErrorInfo(absolute=residual_norm, relative_percent=relative),
        warnings=warnings,
    )


def _singular_response(
    matrix: np.ndarray,
    rhs: np.ndarray,
    pivoting: str,
    warnings: list[str],
    steps: list[Step],
    operations: list[list[Any]],
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
            f"A zero pivot was encountered with pivoting = '{pivoting}'. The system "
            "has a unique solution, but this pivoting choice cannot proceed; select "
            "partial or complete pivoting."
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
