"""Power method for the dominant eigenvalue and its eigenvector.

The power method repeatedly multiplies a starting vector by ``A`` and rescales
it by its largest-magnitude component. The vector direction converges to the
eigenvector of the eigenvalue of largest magnitude and the scaling factor to
that eigenvalue. Selecting the smallest eigenvalue runs *inverse iteration*:
``A y = x`` is solved at every step through an LU factorisation of ``A``, which
amplifies the eigenvector belonging to the eigenvalue nearest zero.

The method requires the dominant eigenvalue to be strictly larger in magnitude
than the others; equal-magnitude or complex dominant pairs are reported as
warnings rather than errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.errors import InvalidInputError
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
from app.solvers._common import (
    failed_response,
    format_num,
    max_iterations_field,
    precision_field,
    tolerance_field,
)
from app.solvers.ch2_linear._iterative import MAX_ERROR_BOUND
from app.solvers.ch2_linear._linear import (
    PIVOT_EPS,
    column_labels,
    condition_number,
    condition_warnings,
    finite_or_none,
    matrix_latex,
    matrix_table_rows,
    validate_matrix,
    vector_latex,
)

# Relative threshold below which a starting vector counts as having no
# component along the target eigenvector.
COMPONENT_EPS = 1e-10
# Relative gap below which two dominant magnitudes count as equal.
EQUAL_EPS = 1e-9
# Relative imaginary part above which an eigenvalue counts as complex.
COMPLEX_EPS = 1e-9

_ONS = "ones"
_DEFAULT_MATRIX = [[4.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 2.0]]

MODE_OPTIONS: list[SelectOption] = [
    SelectOption(value="largest", label="Largest eigenvalue (power method)"),
    SelectOption(value="smallest", label="Smallest eigenvalue (inverse iteration)"),
]


def initial_vector_field() -> InputField:
    """An optional starting vector; blank means the vector of ones."""
    return InputField(
        key="initial_vector",
        label="Initial vector x0 (optional)",
        type="vector",
        required=False,
        default=None,
        placeholder="1, 1, 1",
        help="Leave blank to start from the vector of ones; otherwise one value per row of A.",
    )


def mode_field() -> InputField:
    """Choose between the dominant and the smallest eigenvalue."""
    return InputField(
        key="mode",
        label="Target eigenvalue",
        type="select",
        required=True,
        default="largest",
        options=list(MODE_OPTIONS),
        help="Largest uses A x; smallest runs inverse iteration, solving A y = x each step.",
    )


META = MethodMeta(
    id="power_method",
    chapter=Chapter.CH2_LINEAR,
    name="Power Method (Eigenvalues)",
    summary=(
        "Find the dominant eigenvalue and its eigenvector by repeated multiplication "
        "by A; inverse iteration finds the smallest eigenvalue."
    ),
    theory=(
        "Let A have eigenvalues l1, l2, ..., ln with |l1| > |l2| >= ... >= |ln| and "
        "linearly independent eigenvectors v1, ..., vn. Writing the starting vector "
        "as x^(0) = sum c_i v_i, repeated multiplication gives\n"
        "  A^k x^(0) = sum c_i l_i^k v_i = l_1^k ( c_1 v_1 + sum_{i>1} c_i (l_i/l_1)^k v_i ).\n"
        "Because |l_i/l_1| < 1 for i > 1, the terms with i > 1 fade away, so A^k x^(0) "
        "points more and more along v1 and the scaling factor approaches l_1.\n\n"
        "Each sweep multiplies by A and divides by the largest-magnitude component "
        "of the product, so that component becomes 1. That scaling factor is the "
        "eigenvalue estimate (the Rayleigh quotient after convergence is more "
        "accurate). The error falls by roughly the ratio |l_2/l_1| per iteration, so "
        "a small ratio means fast convergence and a ratio near 1 means slow "
        "convergence.\n\n"
        "To find the eigenvalue of smallest magnitude, inverse iteration applies the "
        "power method to A^-1: A y = x is solved at every step (here by an LU "
        "factorisation of A, with partial pivoting). The largest eigenvalue of A^-1 "
        "is 1/l_min, so the iteration converges to the eigenvector of l_min and "
        "l_min = 1/mu, where mu is the scaling factor.\n\n"
        "The method fails to converge when the dominant eigenvalues have equal "
        "magnitude (for example l and -l, which oscillate) or are complex; these "
        "are reported as warnings. A starting vector with no component along the "
        "dominant eigenvector, and a singular A in inverse mode, are reported as "
        "failures."
    ),
    formulas=[
        LabeledLatex(label="Power sweep", latex=r"y^{(k)} = A x^{(k-1)},\qquad x^{(k)} = \frac{y^{(k)}}{\mu_k}"),
        LabeledLatex(
            label="Scaling factor",
            latex=r"\mu_k = y^{(k)}_{p},\qquad p = \operatorname*{arg\,max}_i \left| y^{(k)}_i \right|",
        ),
        LabeledLatex(label="Eigenvalue estimate", latex=r"\lambda_1 \approx \mu_k"),
        LabeledLatex(label="Inverse iteration", latex=r"A y^{(k)} = x^{(k-1)},\qquad \lambda_{\min} \approx 1/\mu_k"),
        LabeledLatex(
            label="Rayleigh quotient",
            latex=r"\lambda = \frac{x^{T} A x}{x^{T} x}",
        ),
        LabeledLatex(label="Convergence ratio", latex=r"\left| \frac{\lambda_2}{\lambda_1} \right| < 1"),
    ],
    pseudocode=(
        "PowerMethod(A, x0, tol, max_iter, mode):\n"
        "    x <- x0 / max|x0|                       # normalise the start\n"
        "    if mode == smallest:                    # inverse iteration\n"
        "        factor A = P^T L U (partial pivoting); stop if a pivot is zero\n"
        "    for k = 1 to max_iter:\n"
        "        if mode == largest:\n"
        "            y <- A x\n"
        "        else:\n"
        "            solve L z = P x then U y = z     # A y = x\n"
        "        p <- index of the largest |y_i|\n"
        "        mu <- y[p]; x_new <- y / mu\n"
        "        lambda <- mu            (largest)  or  1/mu  (smallest)\n"
        "        err <- max|x_new - x|\n"
        "        if err < tol: return lambda (Rayleigh quotient), x_new\n"
        "        x <- x_new\n"
        "    return lambda with status max_iter or diverged"
    ),
    input_schema=[
        InputField(
            key="matrix",
            label="Square matrix A",
            type="matrix",
            required=True,
            rows=3,
            cols=3,
            default=_DEFAULT_MATRIX,
            help="Square grid, from 2x2 up to 10x10.",
        ),
        initial_vector_field(),
        mode_field(),
        tolerance_field(default=1e-6),
        max_iterations_field(default=100),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Largest eigenvalue (symmetric 3x3)",
            description="Dominant eigenvalue and eigenvector of [[4, 1, 0], [1, 3, 1], [0, 1, 2]].",
            inputs={
                "matrix": _DEFAULT_MATRIX,
                "mode": "largest",
                "initial_vector": None,
                "tolerance": 1e-6,
                "max_iterations": 100,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Smallest eigenvalue (inverse iteration)",
            description="Smallest eigenvalue of the same matrix, found through LU solves of A y = x.",
            inputs={
                "matrix": _DEFAULT_MATRIX,
                "mode": "smallest",
                "initial_vector": None,
                "tolerance": 1e-6,
                "max_iterations": 100,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Non-symmetric 2x2",
            description="A = [[4, 1], [2, 3]] has dominant eigenvalue 5. No symmetry required.",
            inputs={
                "matrix": [[4, 1], [2, 3]],
                "initial_vector": [1, 1],
                "mode": "largest",
                "tolerance": 1e-8,
                "max_iterations": 200,
                "decimal_precision": 6,
            },
        ),
    ],
)


# ---------------------------------------------------------------------------
# Small linear-algebra helpers
# ---------------------------------------------------------------------------


def _max_component_index(values: np.ndarray) -> int:
    return int(np.argmax(np.abs(values)))


def _rayleigh_quotient(matrix: np.ndarray, vector: np.ndarray) -> float:
    product = matrix @ vector
    denominator = float(vector @ vector)
    return float(vector @ product / denominator) if denominator else 0.0


def _lu_factor(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[int]] | None:
    """LU factorisation with partial pivoting: ``P A = L U``.

    Returns ``(L, U, permutation)`` or ``None`` when the matrix is singular.
    """
    size = int(matrix.shape[0])
    upper = matrix.astype(float).copy()
    lower = np.eye(size)
    permutation = list(range(size))
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda i: abs(upper[i, column]))
        if abs(float(upper[pivot_row, column])) < PIVOT_EPS:
            return None
        if pivot_row != column:
            upper[[column, pivot_row]] = upper[[pivot_row, column]]
            lower[[column, pivot_row], :column] = lower[[pivot_row, column], :column]
            permutation[column], permutation[pivot_row] = (
                permutation[pivot_row],
                permutation[column],
            )
        for row in range(column + 1, size):
            lower[row, column] = upper[row, column] / upper[column, column]
            upper[row, column:] -= lower[row, column] * upper[column, column:]
    return lower, upper, permutation


def _lu_solve(lower: np.ndarray, upper: np.ndarray, permutation: list[int], rhs: np.ndarray) -> np.ndarray:
    """Solve ``A x = rhs`` given ``P A = L U`` by forward/back substitution."""
    size = int(rhs.shape[0])
    permuted = rhs[permutation]
    intermediate = np.zeros(size)
    for row in range(size):
        intermediate[row] = permuted[row] - float(lower[row, :row] @ intermediate[:row])
    solution = np.zeros(size)
    for row in range(size - 1, -1, -1):
        residual = intermediate[row] - float(upper[row, row + 1 :] @ solution[row + 1 :])
        solution[row] = residual / float(upper[row, row])
    return solution


def _is_complex(value: complex) -> bool:
    return abs(value.imag) > COMPLEX_EPS * max(1.0, abs(value.real))


def _vector_text(values: np.ndarray, decimals: int) -> str:
    return "[" + ", ".join(format_num(float(v), decimals) for v in values) + "]"


def _log_series(errors: list[float]) -> list[float | None]:
    prepared: list[float | None] = []
    for value in errors:
        if not np.isfinite(value):
            prepared.append(None)
        elif value <= 0.0:
            prepared.append(1e-16)
        else:
            prepared.append(float(value))
    return prepared


# ---------------------------------------------------------------------------
# Iteration driver
# ---------------------------------------------------------------------------


@dataclass
class PowerOutcome:
    """Result of running the power / inverse iteration."""

    status: SolveStatus
    eigenvalue: float
    eigenvector: np.ndarray
    iterations: int
    lambdas: list[float] = field(default_factory=list)
    errors: list[float] = field(default_factory=list)
    products: list[np.ndarray] = field(default_factory=list)
    vectors: list[np.ndarray] = field(default_factory=list)

    @property
    def final_error(self) -> float:
        return self.errors[-1] if self.errors else float("inf")


def _run_iteration(
    matrix: np.ndarray,
    guess: np.ndarray,
    *,
    inverse: bool,
    factors: tuple[np.ndarray, np.ndarray, list[int]] | None,
    tolerance: float,
    max_iterations: int,
) -> PowerOutcome:
    current = guess / float(np.max(np.abs(guess)))
    vectors = [current]
    lambdas: list[float] = []
    errors: list[float] = []
    products: list[np.ndarray] = []
    for k in range(1, max_iterations + 1):
        if inverse:
            assert factors is not None
            product = _lu_solve(factors[0], factors[1], factors[2], current)
            mu = float(product[_max_component_index(product)])
            estimate = 1.0 / mu if mu != 0.0 else float("inf")
        else:
            product = matrix @ current
            mu = float(product[_max_component_index(product)])
            estimate = mu
        products.append(product)
        if mu == 0.0 or not np.isfinite(mu):
            lambdas.append(estimate)
            errors.append(float("inf"))
            vectors.append(current)
            return PowerOutcome(
                SolveStatus.DIVERGED, estimate, current, k, lambdas, errors, products, vectors
            )
        updated = product / mu
        error = float(np.max(np.abs(updated - current)))
        lambdas.append(estimate)
        errors.append(error)
        vectors.append(updated)
        current = updated
        if not bool(np.all(np.isfinite(current))) or float(np.max(np.abs(current))) > MAX_ERROR_BOUND:
            return PowerOutcome(
                SolveStatus.DIVERGED, estimate, current, k, lambdas, errors, products, vectors
            )
        if error < tolerance:
            return PowerOutcome(
                SolveStatus.CONVERGED, estimate, current, k, lambdas, errors, products, vectors
            )
    return PowerOutcome(
        SolveStatus.MAX_ITER, lambdas[-1], current, max_iterations, lambdas, errors, products, vectors
    )


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------


def _iteration_table(
    outcome: PowerOutcome,
    guess: np.ndarray,
    decimals: int,
    *,
    inverse: bool,
) -> DataTable:
    product_label = "A^{-1} x" if inverse else "A x"
    rows: list[list[Any]] = [
        [0, "-", _vector_text(guess, decimals), "-", "-"]
    ]
    for index, (product, vector, estimate, error) in enumerate(
        zip(outcome.products, outcome.vectors[1:], outcome.lambdas, outcome.errors, strict=False),
        start=1,
    ):
        rows.append(
            [
                index,
                _vector_text(product, decimals),
                _vector_text(vector, decimals),
                format_num(estimate, decimals),
                format_num(error, decimals),
            ]
        )
    return DataTable(
        title="Power iteration",
        columns=["Iteration", product_label, "x (normalised)", "lambda estimate", "Error"],
        rows=rows,
    )


def _verification_table(
    matrix: np.ndarray,
    eigenvector: np.ndarray,
    eigenvalue: float,
    decimals: int,
) -> DataTable:
    product = matrix @ eigenvector
    residual = product - eigenvalue * eigenvector
    rows: list[list[Any]] = [
        [
            f"x{i + 1}",
            format_num(float(product[i]), decimals),
            format_num(float(eigenvalue * eigenvector[i]), decimals),
            format_num(float(residual[i]), decimals),
        ]
        for i in range(eigenvector.shape[0])
    ]
    return DataTable(
        title="Eigenpair verification",
        columns=["Component", "(A x)_i", "lambda x_i", "Residual"],
        rows=rows,
    )


def _convergence_plot(
    lambdas: list[float],
    errors: list[float],
    reference: float,
    title: str,
) -> PlotPayload:
    iterations = list(range(1, len(lambdas) + 1))
    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "lambda estimate",
            "x": iterations,
            "y": [finite_or_none(float(value)) for value in lambdas],
        },
        {
            "type": "scatter",
            "mode": "lines",
            "name": "true lambda (numpy)",
            "x": iterations,
            "y": [reference for _ in iterations],
            "line": {"color": "#16a34a", "dash": "dash"},
        },
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "error",
            "x": iterations,
            "y": _log_series(errors),
            "yaxis": "y2",
        },
    ]
    layout: dict[str, Any] = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "Iteration"}, "dtick": 1},
        "yaxis": {"title": {"text": "lambda estimate"}},
        "yaxis2": {
            "title": {"text": "Error"},
            "type": "log",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
    }
    return PlotPayload(traces=traces, layout=layout)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run the power / inverse power method for the validated ``inputs``."""
    decimals = int(inputs["decimal_precision"])
    matrix = validate_matrix(inputs["matrix"], limits)
    size = int(matrix.shape[0])
    tolerance = float(inputs["tolerance"])
    max_iterations = int(inputs["max_iterations"])
    mode = str(inputs["mode"])
    inverse = mode == "smallest"

    guess = _initial_vector(inputs.get("initial_vector"), size)
    if float(np.max(np.abs(guess))) < PIVOT_EPS:
        raise InvalidInputError(
            "The initial vector must not be the zero vector.",
            hint="Give at least one non-zero component, or leave it blank for the ones vector.",
        )

    warnings = condition_warnings(matrix)

    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    magnitudes = np.abs(eigenvalues)
    order_desc = np.argsort(-magnitudes)
    order_asc = np.argsort(magnitudes)
    target_index = int(order_desc[0]) if not inverse else int(order_asc[0])
    target_value = complex(eigenvalues[target_index])
    reference = float(target_value.real)

    if inverse:
        ascending = magnitudes[order_asc]
        equal_magnitude = bool(
            size >= 2 and (ascending[1] - ascending[0]) <= EQUAL_EPS * max(1.0, float(ascending[1]))
        )
    else:
        descending = magnitudes[order_desc]
        equal_magnitude = bool(
            size >= 2 and (descending[0] - descending[1]) <= EQUAL_EPS * max(1.0, float(descending[0]))
        )
    complex_dominant = _is_complex(target_value)

    if equal_magnitude:
        warnings.append(
            "Two eigenvalues of the iteration matrix have equal magnitude, so the "
            "power method does not converge to a single eigenvector; the iterates "
            "may oscillate or fail to settle."
        )
    if complex_dominant:
        warnings.append(
            "The target eigenvalue is complex, so the real-vector power method "
            "cannot converge to it; the estimate keeps rotating instead."
        )

    target_vector = eigenvectors[:, target_index]
    component = float(
        np.abs(np.vdot(target_vector, guess))
        / (np.linalg.norm(target_vector) * np.linalg.norm(guess))
    )

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                r"A = " + matrix_latex(matrix, decimals)
                + r"\\[2mm] x^{(0)} = "
                + vector_latex([float(v) for v in guess / float(np.max(np.abs(guess)))], decimals)
                + r"\\[2mm] \text{target} = "
                + (r"\lambda_{\min}" if inverse else r"\lambda_{\max}")
            ),
            note=(
                "Normalise the start so its largest-magnitude component is 1. "
                "Each sweep multiplies by "
                + ("A^{-1} (solve A y = x)" if inverse else "A")
                + " and rescales by the largest component of the product."
            ),
        )
    ]

    factors: tuple[np.ndarray, np.ndarray, list[int]] | None = None
    tables: list[DataTable] = []

    if inverse:
        factors = _lu_factor(matrix)
        if factors is None:
            return _singular_inverse_response(matrix, warnings)
        lower, upper, _permutation = factors
        steps.append(
            Step(
                title="LU factorisation of A (partial pivoting)",
                latex=(
                    r"P A = L U,\qquad L = " + matrix_latex(lower, decimals)
                    + r",\qquad U = " + matrix_latex(upper, decimals)
                ),
                note=(
                    "Each step solves A y = x by forward substitution L z = P x and "
                    "back substitution U y = z. A zero pivot means A is singular."
                ),
            )
        )
        tables.append(
            DataTable(
                title="L factor (unit lower triangular)",
                columns=["Row", *column_labels(size)],
                rows=matrix_table_rows(lower, decimals),
            )
        )
        tables.append(
            DataTable(
                title="U factor (upper triangular)",
                columns=["Row", *column_labels(size)],
                rows=matrix_table_rows(upper, decimals),
            )
        )

    if not equal_magnitude and component < COMPONENT_EPS:
        return _no_component_response(matrix, guess, target_vector, target_value)

    outcome = _run_iteration(
        matrix,
        guess,
        inverse=inverse,
        factors=factors,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )

    if outcome.products:
        first_product = outcome.products[0]
        first_vector = outcome.vectors[1]
        mu = float(first_product[_max_component_index(first_product)])
        first_estimate = 1.0 / mu if inverse else mu
        steps.append(
            Step(
                title="First iteration (k = 1)",
                latex=(
                    _first_product_latex(matrix, outcome.vectors[0], first_product, inverse, decimals)
                    + r"\\[1mm] x^{(1)} = \frac{y^{(1)}}{\mu_1} = "
                    + vector_latex([float(v) for v in first_vector], decimals)
                    + r"\\[1mm] \mu_1 = " + format_num(mu, decimals)
                    + r",\qquad \lambda \approx " + format_num(first_estimate, decimals)
                ),
                note="The scaling factor is the component of largest magnitude.",
            )
        )

    for k in range(2, outcome.iterations + 1):
        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"x^{{({k})}} = " + vector_latex([float(v) for v in outcome.vectors[k]], decimals)
                    + r"\\[1mm] \lambda \approx " + format_num(outcome.lambdas[k - 1], decimals)
                    + r"\\[1mm] \text{Error} = " + format_num(outcome.errors[k - 1], decimals)
                ),
                note=f"Error at this sweep: {format_num(outcome.errors[k - 1], decimals)}.",
            )
        )

    ratio = _ratio_value(magnitudes, order_desc, order_asc, inverse)
    steps.append(
        Step(
            title="Convergence ratio",
            latex=r"\left| \frac{\lambda_2}{\lambda_1} \right| \approx " + format_num(ratio, decimals),
            note=(
                "The error is reduced by about this factor each iteration, so the "
                "number of correct digits grows by about "
                f"-log10({format_num(ratio, decimals)}) per sweep. A small ratio "
                "converges quickly; a ratio close to 1 is slow and equal magnitudes "
                "mean no convergence."
            ),
        )
    )

    rayleigh = _rayleigh_quotient(matrix, outcome.eigenvector)
    residual = matrix @ outcome.eigenvector - rayleigh * outcome.eigenvector
    residual_norm = float(np.max(np.abs(residual))) if residual.size else 0.0

    steps.append(
        Step(
            title=_result_title(outcome.status),
            latex=(
                r"\lambda \approx " + format_num(rayleigh, decimals)
                + r"\qquad\text{(Rayleigh quotient)}\\[1mm]"
                r"x \approx " + vector_latex([float(v) for v in outcome.eigenvector], decimals)
                + r"\\[1mm] \text{iterations} = " + f"{outcome.iterations}"
            ),
            note=f"Stopped with status '{outcome.status}'.",
        )
    )

    if outcome.status == SolveStatus.DIVERGED:
        warnings.append("The iteration diverged; try a different starting vector.")
    elif outcome.status == SolveStatus.MAX_ITER:
        warnings.append(
            f"The tolerance was not reached within {max_iterations} iterations."
        )

    tables.insert(0, _iteration_table(outcome, outcome.vectors[0], decimals, inverse=inverse))
    tables.append(_verification_table(matrix, outcome.eigenvector, rayleigh, decimals))

    result: dict[str, Any] = {
        "eigenvalue": rayleigh,
        "eigenvector": [float(value) for value in outcome.eigenvector],
        "mode": mode,
        "iterations": outcome.iterations,
        "final_error": outcome.final_error,
        "lambda_estimate": outcome.lambdas[-1] if outcome.lambdas else None,
        "rayleigh_quotient": rayleigh,
        "convergence_ratio": finite_or_none(_ratio_value(magnitudes, order_desc, order_asc, inverse)),
        "true_eigenvalue": reference,
        "residual_norm": residual_norm,
        "equal_magnitude": equal_magnitude,
        "complex_dominant": complex_dominant,
        "condition_number": finite_or_none(condition_number(matrix)),
    }
    if inverse:
        assert factors is not None
        lower, upper, perm = factors
        result["L"] = [[float(value) for value in lower[i]] for i in range(size)]
        result["U"] = [[float(value) for value in upper[i]] for i in range(size)]
        result["permutation"] = list(perm)

    return SolveResponse(
        method=META.id,
        status=outcome.status,
        result=result,
        steps=steps,
        tables=tables,
        plot=_convergence_plot(
            outcome.lambdas,
            outcome.errors,
            reference,
            "Power method: eigenvalue estimate vs iteration",
        ),
        errors=ErrorInfo(
            absolute=outcome.final_error,
            order_of_convergence=1.0 if outcome.status == SolveStatus.CONVERGED else None,
        ),
        warnings=warnings,
    )


def _first_product_latex(
    matrix: np.ndarray,
    current: np.ndarray,
    product: np.ndarray,
    inverse: bool,
    decimals: int,
) -> str:
    if inverse:
        return (
            r"\text{Solve } A y^{(1)} = x^{(0)}\text{ by LU: } y^{(1)} = "
            + vector_latex([float(v) for v in product], decimals)
        )
    return (
        r"y^{(1)} = A x^{(0)} = " + matrix_latex(matrix, decimals)
        + vector_latex([float(v) for v in current], decimals)
        + r" = " + vector_latex([float(v) for v in product], decimals)
    )


def _initial_vector(raw: list[float] | None, size: int) -> np.ndarray:
    if raw is None or len(raw) == 0:
        return np.ones(size)
    guess = np.asarray(raw, dtype=float)
    if guess.shape[0] != size:
        raise InvalidInputError(
            f"The initial vector must have {size} entries to match A.",
            hint="Provide one starting value per row, or leave it blank for ones.",
        )
    return guess


def _ratio_value(
    magnitudes: np.ndarray,
    order_desc: np.ndarray,
    order_asc: np.ndarray,
    inverse: bool,
) -> float:
    if magnitudes.shape[0] < 2:
        return 0.0
    if inverse:
        return float(magnitudes[order_asc[0]] / magnitudes[order_asc[1]])
    return float(magnitudes[order_desc[1]] / magnitudes[order_desc[0]])


def _result_title(status: SolveStatus) -> str:
    if status == SolveStatus.CONVERGED:
        return "Converged"
    if status == SolveStatus.DIVERGED:
        return "Diverged"
    return "Iteration limit reached"


def _singular_inverse_response(matrix: np.ndarray, warnings: list[str]) -> SolveResponse:
    rank = int(np.linalg.matrix_rank(matrix))
    size = int(matrix.shape[0])
    message = (
        "Inverse iteration needs to solve A y = x, but A is singular "
        f"(rank(A) = {rank} < {size}): a zero pivot appeared during LU "
        "factorisation, so the inverse does not exist. Inverse iteration cannot "
        "find the smallest eigenvalue of a singular matrix this way."
    )
    return failed_response(
        META.id,
        message,
        result={
            "mode": "smallest",
            "singular": True,
            "rank": rank,
            "condition_number": finite_or_none(condition_number(matrix)),
        },
        warnings=warnings,
    )


def _no_component_response(
    matrix: np.ndarray,
    guess: np.ndarray,
    target_vector: np.ndarray,
    target_value: complex,
) -> SolveResponse:
    message = (
        "The initial vector has (numerically) no component along the eigenvector of "
        "the target eigenvalue, so the power method cannot build it up. Choose a "
        "different starting vector with a component along that eigenvector, for "
        "example the vector of ones."
    )
    return failed_response(
        META.id,
        message,
        result={
            "target_eigenvalue": finite_or_none(float(target_value.real)),
            "initial_vector": [float(value) for value in guess],
            "condition_number": finite_or_none(condition_number(matrix)),
        },
    )
