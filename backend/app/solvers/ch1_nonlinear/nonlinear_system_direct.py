"""Direct (fixed-point / successive-substitution) method for non-linear systems.

For a system rearranged as ``x = g(x)`` the method iterates
``x^(k+1) = g(x^(k))``, updating one component at a time with the newest values
available (Gauss-Seidel style). By the contraction-mapping principle it converges
to a fixed point when the spectral radius of the Jacobian of ``g`` is below one
near that point, so the convergence check is shown explicitly at the guess.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import sympy as sp

from app.core.errors import InvalidInputError
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
from app.core.parser import expr_to_latex, make_function
from app.core.registry import register
from app.solvers._common import (
    max_iterations_field,
    precision_field,
    stop_criterion_field,
    tolerance_field,
)
from app.solvers.ch1_nonlinear._systems import (
    DIVERGENCE_BOUND,
    build_system_plot,
    jacobian_matrix,
    matrix_function,
    matrix_latex,
    norm,
    parse_iteration_equations,
    parse_variables,
    spectral_radius,
    system_error,
    vector_function,
    vector_latex,
)

_FIELD_HELP = (
    "Rearrange each equation as 'variable = g(...)'. Separate them with ';', a "
    "comma or a newline so that every variable is defined exactly once."
)


META = MethodMeta(
    id="nonlinear_system_direct",
    chapter=Chapter.CH1_NONLINEAR,
    variables=["x", "y", "z"],
    name="Non-linear Systems (Direct/Iteration)",
    summary=(
        "Fixed-point (successive-substitution) iteration for a system rearranged "
        "as x = g(x); converges when the Jacobian of g has spectral radius < 1."
    ),
    theory=(
        "The direct, or fixed-point, method solves a system of non-linear "
        "equations by rearranging each one so that a different variable is "
        "isolated on the left:\n\n"
        "x = g1(x, y, ...), y = g2(x, y, ...), ... that is x = g(x).\n\n"
        "Starting from a guess x(0), each new estimate is produced by substituting "
        "the current values on the right. When the components are refreshed one at "
        "a time so that each equation uses the most recent values (Gauss-Seidel "
        "style) the iteration is faster than refreshing them all at once "
        "(Jacobi style).\n\n"
        "By the contraction-mapping theorem the iteration converges to a fixed "
        "point when the map g is a contraction near it, which is guaranteed if the "
        "spectral radius (largest eigenvalue modulus) of the Jacobian J_g, with "
        "entries (J_g)_ij = dg_i/dx_j, is less than one at that point. The "
        "convergence check is therefore performed by building J_g at the initial "
        "guess and inspecting its eigenvalues: if the spectral radius is below one "
        "convergence is expected, otherwise the iteration may diverge and a bigger "
        "rearrangement is needed.\n\n"
        "A useful way to manufacture a convergent arrangement is to add a multiple "
        "of the residual, x = x + c f(x), and tune c so the eigenvalues of the "
        "resulting Jacobian are small in modulus."
    ),
    formulas=[
        LabeledLatex(
            label="Fixed-point iteration",
            latex=r"x_i^{(k+1)} = g_i\!\left(x_1^{(k+1)}, \ldots, x_n^{(k)}\right)",
        ),
        LabeledLatex(
            label="Convergence condition",
            latex=r"\rho\!\left(J_g(x^*)\right) < 1",
        ),
        LabeledLatex(
            label="Jacobian of the iteration map",
            latex=r"\left(J_g\right)_{ij} = \frac{\partial g_i}{\partial x_j}",
        ),
        LabeledLatex(
            label="Residual of the arrangement",
            latex=r"F(x) = g(x) - x",
        ),
    ],
    pseudocode=(
        "DirectSystem(g, x0, tol, max_iter):\n"
        "    x <- x0\n"
        "    Jg <- Jacobian of g at x0; warn if spectralRadius(Jg) >= 1\n"
        "    for k = 1 to max_iter:\n"
        "        x_old <- x\n"
        "        for i = 1 to n:\n"
        "            x_i <- g_i(x_1, ..., x_n)   # newest values used\n"
        "        dx <- x - x_old\n"
        "        if stopping criterion met: return x, k\n"
        "        if x is not finite or ||x|| > 1e10: stop \"diverged\"\n"
        "    return x, max_iter"
    ),
    input_schema=[
        InputField(
            key="equations",
            label="Iteration equations (variable = g(...))",
            type="text",
            required=True,
            placeholder="x = (20 - y^2)/10; y = (20 - x^2)/10",
            help=_FIELD_HELP,
            rows=3,
        ),
        InputField(
            key="variables",
            label="Variables",
            type="text",
            required=True,
            placeholder="x, y",
            help="Comma-separated list, one name per equation (up to 6).",
        ),
        InputField(
            key="initial_guess",
            label="Initial guess (one value per variable)",
            type="vector",
            required=True,
            placeholder="1, 1",
            help="Starting values, in the same order as the variables.",
        ),
        tolerance_field(default=1e-6),
        max_iterations_field(default=50),
        stop_criterion_field(default="interval"),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Contraction: x=(20-y^2)/10, y=(20-x^2)/10",
            description="Converges to (1.708204, 1.708204); spectral radius 0.20 at the guess.",
            inputs={
                "equations": "x = (20 - y^2)/10; y = (20 - x^2)/10",
                "variables": "x, y",
                "initial_guess": "1, 1",
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Trigonometric: x=cos(y), y=sin(x)",
            description="Converges slowly to (0.768169, 0.694820); spectral radius 0.6786.",
            inputs={
                "equations": "x = cos(y); y = sin(x)",
                "variables": "x, y",
                "initial_guess": "0.5, 0.5",
                "tolerance": 1e-8,
                "max_iterations": 100,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Three unknowns: nonlinear coupling",
            description="Spectral radius 0.10; converges to (1, 2, 3) in a few steps.",
            inputs={
                "equations": (
                    "x = 1 + 0.1*(y - 2)*(z - 3); "
                    "y = 2 + 0.1*(x - 1)*(z - 3); "
                    "z = 3 + 0.1*(x - 1)*(y - 2)"
                ),
                "variables": "x, y, z",
                "initial_guess": "1.5, 2.5, 3.5",
                "tolerance": 1e-6,
                "max_iterations": 100,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
    ],
)


def _error_column(criterion: str) -> str:
    if criterion == "function":
        return "Error ||F(x)||"
    if criterion == "relative":
        return "Error %"
    return "Error ||dx||"


def _iteration_latex(expressions: list[sp.Expr], variables: list[str]) -> str:
    lines = [
        f"{name} = {expr_to_latex(expression)}"
        for name, expression in zip(variables, expressions, strict=True)
    ]
    return r" \\ ".join(lines)


def _complex_latex(value: complex, decimals: int) -> str:
    real = float(value.real)
    imag = float(value.imag)
    if abs(imag) < 1e-12:
        return _fmt(real, decimals)
    sign = "+" if imag >= 0 else "-"
    return f"{_fmt(real, decimals)} {sign} {_fmt(abs(imag), decimals)}i"


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run the fixed-point iteration for a system for the validated ``inputs``."""
    equations_text: str = str(inputs["equations"])
    variables_text: str = str(inputs["variables"])
    initial: list[float] = [float(value) for value in inputs["initial_guess"]]
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)
    criterion = str(inputs["stopping_criterion"])
    decimals = int(inputs["decimal_precision"])

    variables = parse_variables(variables_text)
    if len(initial) != len(variables):
        raise InvalidInputError(
            "The initial guess must give one value per variable "
            f"({len(variables)} needed for {', '.join(variables)}).",
            hint="Example: for x, y enter '0, 0'.",
        )
    expressions = parse_iteration_equations(equations_text, variables)
    jacobian = jacobian_matrix(expressions, variables)
    jac = matrix_function(jacobian, variables)
    gfuncs = [
        make_function(expression, tuple(variables), strict=False)
        for expression in expressions
    ]
    gvec = vector_function(expressions, variables, strict=False)

    x = np.array(initial, dtype=float)
    setup_step = Step(
        title="Setup",
        latex=(
            f"{_iteration_latex(expressions, variables)}"
            f"\\\\ x^{{(0)}} = {vector_latex(x, decimals)}"
        ),
        note=(
            "Each equation isolates one variable, so the system is solved by "
            "repeated substitution."
        ),
    )

    jacobian_at_guess = jac(x)
    warnings: list[str] = []
    rho = spectral_radius(jacobian_at_guess)
    eigenvalues = (
        np.linalg.eigvals(jacobian_at_guess)
        if np.all(np.isfinite(jacobian_at_guess))
        else np.array([], dtype=complex)
    )
    if not math.isfinite(rho):
        warnings.append(
            "The Jacobian of g could not be evaluated at the guess, so no "
            "convergence guarantee can be given."
        )
        rho_note = "The spectral radius could not be computed."
    elif rho >= 1.0:
        warnings.append(
            f"The spectral radius of J_g at the guess is {rho:.4g} >= 1, so the "
            "fixed-point iteration may diverge. Try a better rearrangement or "
            "starting point."
        )
        rho_note = "rho >= 1: the map is not a contraction; divergence is possible."
    else:
        rho_note = "rho < 1: the map is a contraction near the guess; convergence expected."

    eigenvalues_latex = (
        r"\{" + ",\\ ".join(_complex_latex(value, decimals) for value in eigenvalues) + r"\}"
        if eigenvalues.size
        else r"\text{n/a}"
    )
    steps: list[Step] = [
        setup_step,
        Step(
            title="Convergence check",
            latex=(
                f"J_g(x^{{(0)}}) = {matrix_latex(jacobian_at_guess, decimals)}"
                f"\\\\ \\text{{eigenvalues}} = {eigenvalues_latex}"
                f"\\\\ \\rho(J_g) = {_fmt(rho, decimals)}"
            ),
            note=rho_note,
        ),
    ]

    rows: list[list[Any]] = []
    iterates: list[np.ndarray] = [x]
    error_series: list[float | None] = []
    residual_series: list[float] = []
    solution = x
    iterations_used = 0
    last_dx = 0.0
    converged = False
    diverged = False
    failed = False
    final_residual = math.inf

    for k in range(1, max_iterations + 1):
        x_old = x.copy()
        for index in range(len(variables)):
            x[index] = gfuncs[index](*x)
        if not np.all(np.isfinite(x)):
            failed = True
            iterations_used = k - 1
            solution = x_old
            warnings.append("An iterate became undefined; the iteration stopped.")
            steps.append(
                Step(
                    title=f"Iteration {k} - failed",
                    latex=r"\text{The iteration produced a non-finite value.}",
                    note="Check the domain of the rearrangement functions.",
                )
            )
            break

        dx = x - x_old
        last_dx = float(norm(dx))
        residual = gvec(x) - x
        residual_norm = float(norm(residual))
        x_norm = float(norm(x))
        error = system_error(
            criterion,
            residual_norm=residual_norm,
            dx_norm=last_dx,
            x_norm=x_norm,
        )
        error_value = error if error is not None else last_dx

        rows.append([k, *[float(v) for v in x], residual_norm, error_value])
        iterates.append(x.copy())
        error_series.append(error)
        residual_series.append(residual_norm)
        final_residual = residual_norm

        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"x^{{({k})}} = {vector_latex(x, decimals)}"
                    f"\\\\ \\|\\Delta x\\| = {_fmt(last_dx, decimals)}"
                    f"\\quad \\|F(x^{{({k})}})\\| = {_fmt(residual_norm, decimals)}"
                ),
                note=f"Residual of the arrangement: {_fmt(residual_norm, decimals)}.",
            )
        )

        if error is not None and error < tolerance:
            solution = x.copy()
            iterations_used = k
            converged = True
            break

        if x_norm > DIVERGENCE_BOUND:
            solution = x.copy()
            iterations_used = k
            diverged = True
            warnings.append(
                "The iterates are growing without bound; the iteration has diverged."
            )
            break

    if failed:
        status = SolveStatus.FAILED
    elif converged:
        status = SolveStatus.CONVERGED
        steps.append(
            Step(
                title="Result",
                latex=(
                    r"\text{Stopping criterion met}\\\\ "
                    f"x \\approx {vector_latex(solution, decimals)},"
                    f"\\quad \\|F\\| = {_fmt(final_residual, decimals)}"
                ),
                note=f"Converged in {iterations_used} iteration(s).",
            )
        )
    elif diverged:
        status = SolveStatus.DIVERGED
        steps.append(
            Step(
                title="Diverged",
                latex=f"x \\approx {vector_latex(solution, decimals)}",
                note="The sequence is not converging; try another rearrangement or guess.",
            )
        )
    else:
        solution = x
        iterations_used = max_iterations
        status = SolveStatus.MAX_ITER
        warnings.append(
            f"The stopping criterion was not met within {max_iterations} iterations."
        )
        steps.append(
            Step(
                title="Iteration limit reached",
                latex=f"x \\approx {vector_latex(solution, decimals)}",
                note=f"Stopped after the maximum of {max_iterations} iterations.",
            )
        )

    relative = (
        last_dx / float(norm(solution)) * 100.0 if float(norm(solution)) > 0.0 else None
    )

    return SolveResponse(
        method=META.id,
        status=status,
        result={
            "variables": list(variables),
            "solution": [float(value) for value in solution],
            "named_solution": {
                name: float(value)
                for name, value in zip(variables, solution, strict=True)
            },
            "iterations": iterations_used,
            "residual_norm": final_residual if math.isfinite(final_residual) else None,
            "spectral_radius": rho if math.isfinite(rho) else None,
        },
        steps=steps,
        tables=[
            DataTable(
                title="Fixed-point iterations (systems)",
                columns=["Iteration", *variables, "||F(x)||", _error_column(criterion)],
                rows=rows,
            )
        ],
        plot=build_system_plot(
            variables=variables,
            iterates=iterates,
            errors=error_series,
            residuals=residual_series,
            root=solution,
            title="Direct (fixed-point) iteration for a system",
            contour=_contour(expressions, variables),
        ),
        errors=ErrorInfo(absolute=last_dx, relative_percent=relative),
        warnings=warnings,
    )


def _contour(
    expressions: list[sp.Expr],
    variables: list[str],
) -> tuple[Any, Any] | None:
    if len(variables) != 2 or len(expressions) != 2:
        return None
    symbols = [sp.Symbol(name) for name in variables]
    residuals = [expressions[0] - symbols[0], expressions[1] - symbols[1]]
    first = make_function(residuals[0], tuple(variables), strict=False)
    second = make_function(residuals[1], tuple(variables), strict=False)
    return first, second


def _fmt(value: float, decimals: int) -> str:
    if not math.isfinite(value):
        return r"\infty"
    return (
        f"{value:.{decimals}f}" if abs(value) < 1e6 else f"{value:.{max(decimals, 1)}e}"
    )
