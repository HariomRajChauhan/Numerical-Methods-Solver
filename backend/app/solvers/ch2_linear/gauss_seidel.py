"""Gauss-Seidel iteration for linear systems.

Like Jacobi, but each unknown is updated in turn and the freshest value is
reused immediately:
``x_i(k+1) = (b_i - sum_{j<i} a_ij x_j(k+1) - sum_{j>i} a_ij x_j(k)) / a_ii``.
This usually converges about twice as fast as Jacobi. Non-convergence and
divergence are reported as statuses, never as errors.
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
from app.solvers._common import (
    failed_response,
    format_num,
    max_iterations_field,
    precision_field,
    tolerance_field,
)
from app.solvers.ch2_linear._iterative import (
    comparison_field,
    dominance_table,
    dominance_warnings,
    error_semilog_plot,
    gauss_seidel_spectral_radius,
    gauss_seidel_sweep,
    guess_vector,
    initial_guess_field,
    is_diagonally_dominant,
    iterate,
    iteration_table,
    jacobi_sweep,
    stop_criterion_field,
    zero_diagonal_indices,
)
from app.solvers.ch2_linear._linear import (
    condition_warnings,
    equations_latex,
    finite_or_none,
    matrix_latex,
    validate_system,
    variable_names,
    vector_latex,
)

META = MethodMeta(
    id="gauss_seidel",
    chapter=Chapter.CH2_LINEAR,
    name="Gauss-Seidel Iteration",
    summary=(
        "Iteratively solve A x = b, reusing each updated unknown immediately; "
        "usually converges faster than Jacobi."
    ),
    theory=(
        "Gauss-Seidel is a refinement of the Jacobi method. Instead of updating all "
        "unknowns simultaneously, it updates them one at a time and immediately "
        "reuses each new value within the same sweep:\n"
        "  x_i(k+1) = (1/a_ii) (b_i - sum_{j<i} a_ij x_j(k+1) - sum_{j>i} a_ij x_j(k)).\n\n"
        "Writing A = D + L + U (D the diagonal, L strictly lower, U strictly "
        "upper), the iteration is (D+L) x(k+1) = b - U x(k), i.e. "
        "x(k+1) = T x(k) + c with the iteration matrix T = -(D+L)^-1 U. It "
        "converges for every starting vector exactly when rho(T) < 1.\n\n"
        "Strict diagonal dominance guarantees convergence (as for Jacobi), and "
        "Gauss-Seidel also converges for any symmetric positive-definite matrix. "
        "Because it uses the latest values, it typically needs roughly half the "
        "iterations of Jacobi. When the matrix is not dominant the method may still "
        "converge, but convergence is not guaranteed - the check below is only a "
        "warning."
    ),
    formulas=[
        LabeledLatex(
            label="Gauss-Seidel update",
            latex=r"x_i^{(k+1)} = \frac{1}{a_{ii}}"
            r"\left(b_i - \sum_{j<i} a_{ij}x_j^{(k+1)} - \sum_{j>i} a_{ij}x_j^{(k)}\right)",
        ),
        LabeledLatex(
            label="Matrix form",
            latex=r"(D+L)x^{(k+1)} = b - U x^{(k)}",
        ),
        LabeledLatex(label="Iteration matrix", latex=r"T = -(D+L)^{-1}U"),
        LabeledLatex(label="Convergence", latex=r"\rho(T) < 1"),
        LabeledLatex(
            label="Sufficient conditions",
            latex=r"\text{diagonally dominant, or } A \text{ symmetric positive-definite}",
        ),
    ],
    pseudocode=(
        "GaussSeidel(A, b, x0, tol, max_iter):\n"
        "    x <- x0\n"
        "    for k = 1 to max_iter:\n"
        "        for i = 1 to n:\n"
        "            x[i] <- (b[i] - sum_{j != i} A[i][j] x[j]) / A[i][i]  # fresh x[j]\n"
        "        err <- ||x - x_prev||_inf\n"
        "        if err < tol: return x, k\n"
        "        if x not finite or ||x||_inf > 1e12: stop \"diverged\"\n"
        "        x_prev <- x\n"
        "    return x, max_iter"
    ),
    input_schema=[
        InputField(
            key="matrix",
            label="Coefficient matrix A",
            type="matrix",
            required=True,
            rows=3,
            cols=3,
            default=[[4.0, 1.0, 1.0], [1.0, 5.0, 2.0], [1.0, 2.0, 6.0]],
            help="Square grid, from 2x2 up to 10x10. Diagonal dominance helps convergence.",
        ),
        InputField(
            key="vector",
            label="Right-hand side b",
            type="vector",
            required=True,
            default=[9.0, 17.0, 23.0],
            placeholder="9, 17, 23",
            help="One value per equation, separated by commas.",
        ),
        initial_guess_field(),
        tolerance_field(default=1e-6),
        max_iterations_field(default=100),
        stop_criterion_field(),
        comparison_field("Jacobi"),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Diagonally dominant 3x3",
            description="Converges to x = (1, 2, 3), faster than Jacobi.",
            inputs={
                "matrix": [[4, 1, 1], [1, 5, 2], [1, 2, 6]],
                "vector": [9, 17, 23],
                "initial_guess": [0, 0, 0],
                "tolerance": 1e-6,
                "max_iterations": 100,
                "stopping_criterion": "absolute",
                "compare": True,
            },
        ),
        MethodExample(
            name="Classic 3x3 system",
            description="Same textbook system as the direct methods; solution (2, 3, -1).",
            inputs={
                "matrix": [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]],
                "vector": [8, -11, -3],
                "initial_guess": [0, 0, 0],
                "tolerance": 1e-8,
                "max_iterations": 200,
                "stopping_criterion": "absolute",
                "compare": True,
            },
        ),
        MethodExample(
            name="Not dominant (may diverge)",
            description="A non-dominant system; convergence is not guaranteed.",
            inputs={
                "matrix": [[1, 2, 3], [2, 4, 6], [1, 1, 1]],
                "vector": [1, 2, 1],
                "initial_guess": [0, 0, 0],
                "tolerance": 1e-6,
                "max_iterations": 100,
                "stopping_criterion": "absolute",
                "compare": True,
            },
        ),
    ],
)


def _first_iteration_latex(
    matrix: np.ndarray, rhs: np.ndarray, guess: np.ndarray, decimals: int
) -> str:
    """First Gauss-Seidel sweep, showing the reused (fresh) values."""
    size = int(matrix.shape[0])
    work = guess.astype(float).copy()
    lines: list[str] = []
    for i in range(size):
        terms: list[str] = []
        for j in range(size):
            if j == i:
                continue
            label = 1 if j < i else 0
            terms.append(
                f"\\left({format_num(float(matrix[i, j]), decimals)}\\right)"
                f"x_{{{j + 1}}}^{{({label})}}"
            )
        total = float(sum(matrix[i, j] * work[j] for j in range(size) if j != i))
        numerator = float(rhs[i]) - total
        value = numerator / float(matrix[i, i])
        work[i] = value
        lines.append(
            f"x_{{{i + 1}}}^{{(1)}} = \\frac{{{format_num(float(rhs[i]), decimals)} - "
            f"\\left[{' + '.join(terms)}\\right]}}{{{format_num(float(matrix[i, i]), decimals)}}}"
            f" = {format_num(value, decimals)}"
        )
    return r" \\ ".join(lines)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run Gauss-Seidel iteration for the validated ``inputs``."""
    decimals = int(inputs["decimal_precision"])
    matrix, rhs = validate_system(inputs["matrix"], inputs["vector"], limits)
    size = int(matrix.shape[0])
    names = variable_names(size)
    tolerance = float(inputs["tolerance"])
    max_iterations = int(inputs["max_iterations"])
    criterion = str(inputs["stopping_criterion"])
    compare = bool(inputs["compare"])
    guess = guess_vector(inputs.get("initial_guess"), size)

    zeros = zero_diagonal_indices(matrix)
    if zeros:
        return _zero_diagonal_response(zeros)

    warnings = condition_warnings(matrix) + dominance_warnings(matrix)
    radius = gauss_seidel_spectral_radius(matrix)
    if radius >= 1.0:
        warnings.append(
            f"The spectral radius of the Gauss-Seidel iteration matrix is "
            f"{radius:.6g} >= 1, so the iteration will not converge to the solution."
        )

    outcome = iterate(gauss_seidel_sweep, matrix, rhs, guess, tolerance, criterion, max_iterations)

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                equations_latex(matrix, rhs, names, decimals)
                + r"\\[2mm] A = " + matrix_latex(matrix, decimals)
                + r"\\[2mm] x^{(0)} = " + vector_latex([float(v) for v in guess], decimals)
            ),
            note=(
                "Diagonally dominant: convergence is expected."
                if is_diagonally_dominant(matrix)
                else "Not diagonally dominant: convergence is not guaranteed (still run)."
            ),
        ),
        Step(
            title="First iteration (k = 1)",
            latex=_first_iteration_latex(matrix, rhs, guess, decimals),
            note="Each unknown reuses the newest values already computed in this sweep.",
        ),
    ]

    for k in range(2, outcome.iterations + 1):
        vector = outcome.history[k - 1]
        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"x^{{({k})}} = " + vector_latex([float(v) for v in vector], decimals)
                    + r"\\[1mm] \text{Error} = "
                    + format_num(outcome.errors[k - 1], decimals)
                ),
                note=f"Error at this sweep: {format_num(outcome.errors[k - 1], decimals)}.",
            )
        )

    series: list[tuple[str, list[float]]] = [("Gauss-Seidel", outcome.errors)]
    extra_tables: list[DataTable] = []
    if compare:
        other = iterate(jacobi_sweep, matrix, rhs, guess, tolerance, criterion, max_iterations)
        comparison_rows: list[list[Any]] = [
            [
                "Gauss-Seidel",
                outcome.iterations,
                outcome.status,
                format_num(outcome.final_error, decimals),
            ],
            ["Jacobi", other.iterations, other.status, format_num(other.final_error, decimals)],
        ]
        series.append(("Jacobi", other.errors))
        extra_tables.append(
            DataTable(
                title="Iteration-count comparison",
                columns=["Method", "Iterations", "Status", "Final error"],
                rows=comparison_rows,
            )
        )
        steps.append(
            Step(
                title="Comparison with Jacobi",
                latex=(
                    r"\text{Gauss-Seidel: } " + f"{outcome.iterations}\\ \\text{{iterations}}"
                    r"\\[1mm] \text{Jacobi: } " + f"{other.iterations}\\ \\text{{iterations}}"
                ),
                note=(
                    "Gauss-Seidel converges in fewer iterations here because it reuses "
                    "each updated value immediately."
                    if other.status == SolveStatus.CONVERGED
                    and outcome.iterations < other.iterations
                    else "See the comparison table for both iteration counts and statuses."
                ),
            )
        )
        result_comparison = comparison_rows
    else:
        result_comparison = None

    tables: list[DataTable] = [
        dominance_table(matrix, decimals),
        iteration_table(names, guess, outcome.history, outcome.errors, criterion, decimals),
        *extra_tables,
    ]

    residual = matrix @ outcome.solution - rhs
    residual_norm = float(np.linalg.norm(residual, ord=np.inf))
    rhs_norm = float(np.linalg.norm(rhs, ord=np.inf))
    relative = (residual_norm / rhs_norm * 100.0) if rhs_norm > 0 else None

    steps.append(
        Step(
            title=_result_title(outcome.status),
            latex=(
                r"x \approx " + vector_latex([float(v) for v in outcome.solution], decimals)
                + r"\\[1mm] \text{iterations} = " + f"{outcome.iterations}"
                + r"\\[1mm] \text{Error} = " + format_num(outcome.final_error, decimals)
            ),
            note=f"Stopped with status '{outcome.status}'.",
        )
    )

    if outcome.status == SolveStatus.DIVERGED:
        warnings.append(
            "The Gauss-Seidel iteration diverged; try a dominant or "
            "symmetric positive-definite system."
        )
    elif outcome.status == SolveStatus.MAX_ITER:
        warnings.append(
            f"The stopping criterion was not met within {max_iterations} iterations."
        )

    result: dict[str, Any] = {
        "solution": {names[i]: float(outcome.solution[i]) for i in range(size)},
        "solution_vector": [float(v) for v in outcome.solution],
        "iterations": outcome.iterations,
        "final_error": outcome.final_error,
        "stopping_criterion": criterion,
        "spectral_radius": finite_or_none(radius),
        "diagonally_dominant": is_diagonally_dominant(matrix),
        "residual_norm": residual_norm,
        "relative_residual_percent": relative,
    }
    if result_comparison is not None:
        result["comparison"] = result_comparison

    return SolveResponse(
        method=META.id,
        status=outcome.status,
        result=result,
        steps=steps,
        tables=tables,
        plot=error_semilog_plot(series, "Gauss-Seidel: error vs iteration"),
        errors=ErrorInfo(
            absolute=outcome.final_error,
            relative_percent=relative,
            order_of_convergence=1.0 if outcome.status == SolveStatus.CONVERGED else None,
        ),
        warnings=warnings,
    )


def _result_title(status: SolveStatus) -> str:
    if status == SolveStatus.CONVERGED:
        return "Converged"
    if status == SolveStatus.DIVERGED:
        return "Diverged"
    return "Iteration limit reached"


def _zero_diagonal_response(zeros: list[int]) -> SolveResponse:
    rows = ", ".join(str(index + 1) for index in zeros)
    message = (
        f"The diagonal has a zero entry in row(s) {rows}, so the Gauss-Seidel "
        "update would divide by zero. Reorder the equations (pivoting) or use a "
        "direct method such as Gauss elimination."
    )
    return failed_response(META.id, message)
