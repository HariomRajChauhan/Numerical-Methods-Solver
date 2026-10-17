"""Newton's method for systems of non-linear equations.

Solves ``F(x) = 0`` where ``F: R^n -> R^n`` by repeatedly linearising at the
current estimate with the Jacobian and solving the linear system
``J(x^(k)) dx = -F(x^(k))`` before the update ``x^(k+1) = x^(k) + dx``. The
Jacobian is built symbolically with SymPy and shown at every iteration, so the
working is fully exam-style. Near a simple solution the method converges
quadratically, but it can fail at a singular Jacobian or diverge from a poor
guess.
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
from app.core.parser import make_function
from app.core.registry import register
from app.solvers._common import (
    estimate_order,
    failed_response,
    max_iterations_field,
    precision_field,
    stop_criterion_field,
    tolerance_field,
)
from app.solvers.ch1_nonlinear._systems import (
    DIVERGENCE_BOUND,
    MAX_CONDITION_NUMBER,
    build_system_plot,
    condition_number,
    equations_latex,
    jacobian_matrix,
    matrix_function,
    matrix_latex,
    norm,
    parse_residual_equations,
    parse_variables,
    system_error,
    vector_function,
    vector_latex,
)

_FIELD_HELP = (
    "Use ^ for powers, * for products and separate several equations with ';', "
    "a comma or a newline. Write f_i(x, y) = 0 either as an expression or as "
    "'left = right'."
)


META = MethodMeta(
    id="nonlinear_system_newton",
    chapter=Chapter.CH1_NONLINEAR,
    variables=["x", "y", "z"],
    name="Non-linear Systems (Newton's Method)",
    summary=(
        "Multi-variable Newton-Raphson: linearise F(x) = 0 with the symbolic "
        "Jacobian and solve J dx = -F at each step; quadratic near the root."
    ),
    theory=(
        "A system of non-linear equations, f1(x1, ..., xn) = 0, ..., "
        "fn(x1, ..., xn) = 0, is written compactly as F(x) = 0. Newton's method "
        "extends the single-variable tangent idea to several unknowns. At the "
        "current estimate x(k) the functions are replaced by their first-order "
        "Taylor expansion, F(x) ~= F(x(k)) + J(x(k)) (x - x(k)), where J is the "
        "Jacobian matrix with entries J_ij = df_i/dx_j.\n\n"
        "Setting the linearisation to zero and solving for the correction gives "
        "the linear system\n\n"
        "J(x(k)) dx = -F(x(k)),\n\n"
        "and the next estimate x(k+1) = x(k) + dx. Because the Jacobian is built "
        "symbolically with SymPy, the working (F, J, the linear system and dx) can "
        "be shown exactly at every iteration.\n\n"
        "The method converges quadratically near a solution where J is invertible "
        "and the guess is good, but it can diverge or jump away otherwise. If the "
        "Jacobian is singular (its determinant is zero, i.e. the equations are "
        "linearly dependent at that point) the linear system has no unique "
        "solution and the method stops with a failed status. The step norm ||dx|| "
        "or the residual norm ||F(x)|| is used as the convergence measure."
    ),
    formulas=[
        LabeledLatex(
            label="Newton step for systems",
            latex=(
                r"x^{(k+1)} = x^{(k)} + \Delta x,\qquad "
                r"J(x^{(k)})\,\Delta x = -F(x^{(k)})"
            ),
        ),
        LabeledLatex(
            label="Jacobian matrix",
            latex=r"J_{ij} = \frac{\partial f_i}{\partial x_j}",
        ),
        LabeledLatex(
            label="Linear system in full",
            latex=(
                r"\begin{bmatrix} \dfrac{\partial f_1}{\partial x_1} & \cdots & "
                r"\dfrac{\partial f_1}{\partial x_n} \\ \vdots & \ddots & \vdots \\ "
                r"\dfrac{\partial f_n}{\partial x_1} & \cdots & "
                r"\dfrac{\partial f_n}{\partial x_n} \end{bmatrix}"
                r"\begin{bmatrix} \Delta x_1 \\ \vdots \\ \Delta x_n \end{bmatrix}"
                r" = -\begin{bmatrix} f_1 \\ \vdots \\ f_n \end{bmatrix}"
            ),
        ),
        LabeledLatex(
            label="Order of convergence",
            latex=r"\text{quadratic},\quad p = 2",
        ),
    ],
    pseudocode=(
        "NewtonSystem(F, J, x0, tol, max_iter):\n"
        "    x <- x0\n"
        "    for k = 1 to max_iter:\n"
        "        Fx  <- F(x)\n"
        "        Jk  <- J(x)              # symbolic Jacobian evaluated at x\n"
        "        if Jk is singular: stop \"singular Jacobian\"\n"
        "        solve the linear system Jk dx = -Fx\n"
        "        x_new <- x + dx\n"
        "        err <- ||dx||\n"
        "        if stopping criterion met: return x_new, k\n"
        "        if x_new is not finite or ||x_new|| > 1e10: stop \"diverged\"\n"
        "        x <- x_new\n"
        "    return x, max_iter"
    ),
    input_schema=[
        InputField(
            key="equations",
            label="Equations f_i = 0",
            type="text",
            required=True,
            placeholder="x^2 + y^2 - 4; x^2 - y",
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
            name="Circle and parabola: x^2 + y^2 - 4, x^2 - y",
            description="Two curves crossing at (1.249621, 1.561553).",
            inputs={
                "equations": "x^2 + y^2 - 4; x^2 - y",
                "variables": "x, y",
                "initial_guess": "1, 1",
                "tolerance": 1e-6,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Transcendental: cos(x) - y, sin(y) - x",
            description="A trigonometric pair with the solution (0.694820, 0.768169).",
            inputs={
                "equations": "cos(x) - y; sin(y) - x",
                "variables": "x, y",
                "initial_guess": "0.5, 0.5",
                "tolerance": 1e-8,
                "max_iterations": 50,
                "stopping_criterion": "interval",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Three unknowns: x + yz - 7, xy + z - 5, x + y + z - 6",
            description="Solution (1, 2, 3) from the guess (1.5, 2.5, 3.5).",
            inputs={
                "equations": "x + y*z - 7; x*y + z - 5; x + y + z - 6",
                "variables": "x, y, z",
                "initial_guess": "1.5, 2.5, 3.5",
                "tolerance": 1e-6,
                "max_iterations": 50,
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


def _residuals_latex(values: np.ndarray, decimals: int) -> str:
    return vector_latex([float(value) for value in values], decimals)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run Newton's method for a system for the validated ``inputs``."""
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
            hint="Example: for x, y enter '1, 1'.",
        )
    expressions = parse_residual_equations(equations_text, variables)
    jacobian = jacobian_matrix(expressions, variables)

    fvec = vector_function(expressions, variables, strict=False)
    jac = matrix_function(jacobian, variables)

    x = np.array(initial, dtype=float)
    latex_equations = equations_latex(expressions)
    latex_jacobian = sp.latex(jacobian)
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                f"{latex_equations} \\\\ J = {latex_jacobian}"
                f"\\\\ x^{{(0)}} = {_residuals_latex(x, decimals)}"
            ),
            note=(
                "The Jacobian J is obtained symbolically from the equations with "
                "SymPy; the initial guess is evaluated next."
            ),
        )
    ]

    function_values = fvec(x)
    if not np.all(np.isfinite(function_values)):
        return failed_response(
            META.id,
            "The equations are undefined at the initial guess "
            f"({_residuals_latex(x, decimals)}).",
            steps=steps,
            result={"variables": variables, "solution": x.tolist()},
        )

    if norm(function_values) == 0.0:
        return SolveResponse(
            method=META.id,
            status=SolveStatus.CONVERGED,
            result=_result(variables, x, 0, 0.0, None),
            steps=[
                *steps,
                Step(
                    title="Result",
                    latex=(
                        f"F(x^{{(0)}}) = 0 \\Rightarrow the initial guess is already "
                        f"a solution: {_residuals_latex(x, decimals)}"
                    ),
                    note="No iteration was needed.",
                ),
            ],
            tables=[],
            plot=build_system_plot(
                variables=variables,
                iterates=[x],
                errors=[],
                residuals=[],
                root=x,
                title="Newton's method for a system",
                contour=_contour(expressions, variables),
            ),
            errors=ErrorInfo(absolute=0.0, order_of_convergence=2.0),
            warnings=[],
        )

    rows: list[list[Any]] = []
    iterates: list[np.ndarray] = [x]
    error_series: list[float | None] = []
    residual_series: list[float] = []
    step_errors: list[float] = []
    warnings: list[str] = []

    solution = x
    iterations_used = 0
    last_dx = 0.0
    converged = False
    diverged = False
    failed = False
    final_residual = float(norm(function_values))

    for k in range(1, max_iterations + 1):
        fk = fvec(x)
        jk = jac(x)
        if not np.all(np.isfinite(fk)):
            failed = True
            warnings.append("The residuals are undefined at the current iterate.")
            iterations_used = k - 1
            solution = x
            steps.append(
                Step(
                    title=f"Iteration {k} - failed",
                    latex=(
                        f"x^{{({k - 1})}} = {_residuals_latex(x, decimals)}"
                        r"\Rightarrow F(x)\text{ is not finite; cannot continue.}"
                    ),
                )
            )
            break

        condition = condition_number(jk)
        determinant = float(np.linalg.det(jk)) if np.all(np.isfinite(jk)) else math.nan
        if not math.isfinite(condition) or condition > MAX_CONDITION_NUMBER:
            failed = True
            iterations_used = k - 1
            solution = x
            warnings.append(
                "The Jacobian is singular at the current iterate, so the linear "
                "system J dx = -F has no unique solution; Newton's method stops."
            )
            steps.append(
                Step(
                    title=f"Iteration {k} - singular Jacobian",
                    latex=(
                        f"J(x^{{({k - 1})}}) = {matrix_latex(jk, decimals)}"
                        f"\\\\ \\det J = {_fmt(determinant, decimals)}"
                        r"\Rightarrow \text{singular; cannot solve for } \Delta x."
                    ),
                    note=(
                        "Try a different initial guess, or a method that does not "
                        "invert the Jacobian."
                    ),
                )
            )
            break

        try:
            dx = np.linalg.solve(jk, -fk)
        except np.linalg.LinAlgError:
            failed = True
            iterations_used = k - 1
            solution = x
            warnings.append("The linear system J dx = -F could not be solved.")
            break

        x_new = x + dx
        last_dx = float(norm(dx))
        f_new = fvec(x_new)
        finite_new = bool(np.all(np.isfinite(x_new)) and np.all(np.isfinite(f_new)))
        residual_new = float(norm(f_new)) if finite_new else math.inf
        x_norm = float(norm(x_new)) if math.isfinite(norm(x_new)) else math.inf
        error = system_error(
            criterion,
            residual_norm=residual_new,
            dx_norm=last_dx,
            x_norm=x_norm,
        )
        error_value = error if error is not None else last_dx

        rows.append([k, *[float(v) for v in x_new], residual_new, error_value])
        iterates.append(x_new if finite_new else x)
        error_series.append(error)
        residual_series.append(residual_new if math.isfinite(residual_new) else 0.0)
        step_errors.append(last_dx)

        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"F(x^{{({k - 1})}}) = {_residuals_latex(fk, decimals)}"
                    f"\\\\ J(x^{{({k - 1})}}) = {matrix_latex(jk, decimals)}"
                    f"\\\\ \\text{{Solve }} J\\,\\Delta x = -F:\\quad "
                    f"\\Delta x = {vector_latex([float(v) for v in dx], decimals)}"
                    f"\\\\ x^{{({k})}} = x^{{({k - 1})}} + \\Delta x = "
                    f"{vector_latex([float(v) for v in x_new], decimals)}"
                    f"\\\\ \\|\\Delta x\\| = {_fmt(last_dx, decimals)},\\quad "
                    f"\\|F(x^{{({k})}})\\| = {_fmt(residual_new, decimals)}"
                ),
                note=f"Next estimate x^({k}).",
            )
        )

        if finite_new and error is not None and error < tolerance:
            solution = x_new
            final_residual = residual_new
            iterations_used = k
            converged = True
            break

        if not finite_new or float(norm(x_new)) > DIVERGENCE_BOUND:
            solution = x_new if finite_new else x
            final_residual = residual_new if math.isfinite(residual_new) else math.inf
            iterations_used = k
            diverged = True
            warnings.append(
                "The iterates are growing without bound; Newton's method has diverged."
            )
            break

        x = x_new
        final_residual = residual_new

    order = estimate_order(step_errors) if converged else None
    if order is None and converged:
        order = 2.0

    if failed:
        status = SolveStatus.FAILED
    elif converged:
        status = SolveStatus.CONVERGED
        steps.append(
            Step(
                title="Result",
                latex=(
                    r"\text{Stopping criterion met}\\\\ "
                    f"x \\approx {vector_latex([float(v) for v in solution], decimals)},"
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
                latex=(
                    f"x \\approx {vector_latex([float(v) for v in solution], decimals)}"
                ),
                note="The sequence is not converging; try a better initial guess.",
            )
        )
    else:
        iterations_used = max_iterations
        status = SolveStatus.MAX_ITER
        warnings.append(
            f"The stopping criterion was not met within {max_iterations} iterations."
        )
        steps.append(
            Step(
                title="Iteration limit reached",
                latex=(
                    f"x \\approx {vector_latex([float(v) for v in solution], decimals)}"
                ),
                note=f"Stopped after the maximum of {max_iterations} iterations.",
            )
        )

    relative = (
        last_dx / float(norm(solution)) * 100.0 if float(norm(solution)) > 0.0 else None
    )

    return SolveResponse(
        method=META.id,
        status=status,
        result=_result(
            variables,
            solution,
            iterations_used,
            final_residual if math.isfinite(final_residual) else None,
            order,
        ),
        steps=steps,
        tables=[
            DataTable(
                title="Newton iterations (systems)",
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
            title="Newton's method for a system",
            contour=_contour(expressions, variables),
        ),
        errors=ErrorInfo(
            absolute=last_dx,
            relative_percent=relative,
            order_of_convergence=order,
        ),
        warnings=warnings,
    )


def _contour(
    expressions: list[sp.Expr],
    variables: list[str],
) -> tuple[Any, Any] | None:
    if len(variables) != 2 or len(expressions) != 2:
        return None
    first = make_function(expressions[0], tuple(variables), strict=False)
    second = make_function(expressions[1], tuple(variables), strict=False)
    return first, second


def _result(
    variables: list[str],
    solution: np.ndarray,
    iterations: int,
    residual_norm: float | None,
    order: float | None,
) -> dict[str, Any]:
    return {
        "variables": list(variables),
        "solution": [float(value) for value in solution],
        "named_solution": {
            name: float(value) for name, value in zip(variables, solution, strict=True)
        },
        "iterations": iterations,
        "residual_norm": residual_norm,
        "estimated_order": order,
    }


def _fmt(value: float, decimals: int) -> str:
    if not math.isfinite(value):
        return r"\text{undefined}"
    return (
        f"{value:.{decimals}f}" if abs(value) < 1e6 else f"{value:.{max(decimals, 1)}e}"
    )
