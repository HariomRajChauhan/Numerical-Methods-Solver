"""Taylor series method for initial value problems (Chapter 5).

For ``y' = f(x, y)`` the higher derivatives follow from repeated *total*
differentiation, ``y^{(k+1)} = D y^{(k)}`` with ``D g = g_x + g_y f``. Truncating
the Taylor expansion after order ``p`` gives a one-step method of order ``p``
that needs no sub-stage evaluations but does need the symbolic derivatives.
"""

from __future__ import annotations

from typing import Any

import sympy as sp

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
from app.solvers._common import failed_response, format_num
from app.solvers.ch5_ode._ivp import (
    IVP,
    MAX_SYMBOLIC_OPS,
    IVPStep,
    degenerate_response,
    divergence_response,
    interpolate_targets,
    ivp_plot,
    ivp_schema,
    prepare_ivp,
    reference_endpoint,
    result_step,
    run_fixed_steps,
    sample_exact,
    setup_step,
    solution_table,
    step_size_study,
    summary_table,
    targets_table,
)

MAX_WORKING_STEPS = 10
_FACTORIALS = [1, 1, 2, 6, 24, 120, 720, 5040]


def _order_field() -> InputField:
    return InputField(
        key="order",
        label="Order p",
        type="integer",
        required=True,
        default=3,
        min=2,
        max=6,
        help="Number of Taylor terms; p derivatives are built symbolically.",
    )


def _derivatives(f: sp.Expr, order: int) -> list[sp.Expr]:
    """``[y', y'', ..., y^{(order)}]`` by repeated total differentiation."""
    x, y = sp.Symbol("x"), sp.Symbol("y")
    derivatives = [f]
    current = f
    for _ in range(2, order + 1):
        current = sp.diff(current, x) + sp.diff(current, y) * f
        derivatives.append(sp.expand(current))
    return derivatives


def _derivative_latex(derivatives: list[sp.Expr]) -> str:
    lines = [rf"y' = f(x, y) = {sp.latex(derivatives[0])}"]
    for index, derivative in enumerate(derivatives[1:], start=2):
        lines.append(
            rf"y^{{({index})}} = D^{{{index - 1}}} f = {sp.latex(derivative)}"
        )
    return r"\\[1mm]".join(lines)


def _derivative_step(derivatives: list[sp.Expr]) -> Step:
    return Step(
        title="Symbolic derivatives (total differentiation)",
        latex=_derivative_latex(derivatives),
        note=(
            r"Each higher derivative uses $D g = g_x + g_y\,f$, since $y' = f(x, y)$."
        ),
    )


def _working_steps(ivp: IVP, steps: list[IVPStep], order: int) -> list[Step]:
    output: list[Step] = []
    for step in steps[1 : MAX_WORKING_STEPS + 1]:
        previous = steps[step.k - 1]
        values = [float(v) for v in step.data.get("derivatives", [])]
        terms = [format_num(previous.y, ivp.decimals)]
        for j, value in enumerate(values):
            power = j + 1
            if power == 1:
                terms.append(rf"h\left({format_num(value, ivp.decimals)}\right)")
            else:
                terms.append(
                    rf"\frac{{h^{{{power}}}}}{{{_FACTORIALS[power]}}}"
                    rf"\left({format_num(value, ivp.decimals)}\right)"
                )
        output.append(
            Step(
                title=f"Step {step.k}",
                latex=(
                    rf"y_{{{step.k}}} = y_{{{step.k - 1}}} + \sum_{{j=1}}^{{{order}}} "
                    rf"\frac{{h^j}}{{j!}}\,y^{{(j)}}_{{{step.k - 1}}}"
                    rf"\\[1mm] = " + " + ".join(terms) +
                    rf" = {format_num(step.y, ivp.decimals)}"
                    rf"\\[1mm] x_{{{step.k}}} = {format_num(step.x, ivp.decimals)}"
                ),
                note=f"Evaluated with {order} derivatives and h = {format_num(ivp.h, ivp.decimals)}.",
            )
        )
    if len(steps) - 1 > MAX_WORKING_STEPS:
        output.append(
            Step(
                title="Remaining steps",
                note=(
                    f"The remaining {len(steps) - 1 - MAX_WORKING_STEPS} steps follow the "
                    "same Taylor sum; every step is listed in the table."
                ),
            )
        )
    return output


def _derivatives_table(steps: list[IVPStep], order: int, decimals: int) -> DataTable:
    columns = ["k", "x", "y"] + [rf"y^({j})" for j in range(1, order + 1)]
    rows: list[list[Any]] = []
    for step in steps:
        values = [float(v) for v in step.data.get("derivatives", [])]
        row: list[Any] = [step.k, format_num(step.x, decimals), format_num(step.y, decimals)]
        row.extend(format_num(value, decimals) for value in values)
        rows.append(row)
    return DataTable(title="Taylor derivative values per step", columns=columns, rows=rows)


META = MethodMeta(
    id="taylor_series",
    chapter=Chapter.CH5_ODE,
    name="Taylor Series Method",
    summary=(
        "Advance y' = f(x, y) with its Taylor expansion, using symbolically generated "
        "higher derivatives (order p) for high accuracy with one function per derivative."
    ),
    variables=["x", "y"],
    theory=(
        "The Taylor series method expands the solution about each grid point:\n"
        "  y(x + h) = y + h y' + (h^2/2!) y'' + ... + (h^p/p!) y^{(p)}.\n"
        "Because y' = f(x, y), every higher derivative is obtained by *total* "
        "differentiation, D g = g_x + g_y f, so y'' = D f, y''' = D^2 f, and so on. "
        "Truncating after order p gives a one-step method whose local error is "
        "O(h^{p+1}) and whose global error is O(h^p). The price is symbolic "
        "differentiation: the expressions can grow quickly, so very high orders or "
        "complicated right-hand sides may not be practical.\n\n"
        "For a forward (or backward) march the same update is applied at every grid "
        "point. When an exact solution is supplied it is shown alongside and the error "
        "is tabulated; a step-size study estimates the observed order of accuracy."
    ),
    formulas=[
        LabeledLatex(
            label="Taylor update",
            latex=r"y_{n+1} = y_n + \sum_{j=1}^{p} \frac{h^j}{j!}\,y_n^{(j)}",
        ),
        LabeledLatex(
            label="Total derivative",
            latex=r"y^{(k+1)} = D\,y^{(k)} = \frac{\partial y^{(k)}}{\partial x} + "
            r"\frac{\partial y^{(k)}}{\partial y}\,f(x, y)",
        ),
        LabeledLatex(label="Local error", latex=r"O(h^{p+1})"),
    ],
    pseudocode=(
        "Taylor(f, x0, y0, h, n, p):\n"
        "    y1 <- f;  for k = 2..p: yk <- d/dx(yk-1) + d/dy(yk-1) * f\n"
        "    for each step:\n"
        "        y <- y + sum_{j=1..p} h^j / j! * yj(x, y)\n"
        "        x <- x + h"
    ),
    input_schema=ivp_schema(_order_field()),
    examples=[
        MethodExample(
            name="y' = x + y, y(0) = 1 (order 3)",
            description="Derivatives at x=0 are y'=1, y''=2, y'''=2; exact y = 2e^x - x - 1.",
            inputs={
                "function": "x + y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "step",
                "h": 0.1,
                "order": 3,
                "exact_solution": "2*exp(x) - x - 1",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="y' = x + y, y(0) = 1 (order 4)",
            description="One more Taylor term sharply reduces the error.",
            inputs={
                "function": "x + y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "step",
                "h": 0.1,
                "order": 4,
                "exact_solution": "2*exp(x) - x - 1",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="y' = -2xy, y(0) = 1 (order 3)",
            description="Exact y = e^{-x^2}.",
            inputs={
                "function": "-2*x*y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "steps",
                "n": 8,
                "order": 3,
                "exact_solution": "exp(-x^2)",
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate y' = f(x, y) with the order-p Taylor series method."""
    del limits
    method_id = "taylor_series"
    order = int(inputs.get("order", 3))

    prepared = prepare_ivp(inputs, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    ivp = prepared
    if ivp.n == 0:
        return degenerate_response(method_id, ivp)
    if ivp.expr is None:  # pragma: no cover - prepare_ivp always returns an expr
        return failed_response(method_id, "The Taylor method needs a symbolic f(x, y).")

    try:
        derivatives = _derivatives(ivp.expr, order)
    except Exception as exc:  # SymPy can fail on pathological expressions.
        return failed_response(
            method_id,
            f"Could not build the Taylor derivatives symbolically: {exc}",
            warnings=list(ivp.notices),
        )
    if any(sp.count_ops(derivative) > MAX_SYMBOLIC_OPS for derivative in derivatives):
        return failed_response(
            method_id,
            "The symbolic derivatives grow too large for this f(x, y). Try a lower "
            "order p or a simpler equation.",
            warnings=list(ivp.notices),
        )

    funcs = [make_function(derivative, ("x", "y"), strict=False) for derivative in derivatives]

    def stepper(x: float, y: float, h: float) -> tuple[float, dict[str, Any]]:
        values = [float(func(x, y)) for func in funcs]
        increment = 0.0
        for j, value in enumerate(values):
            increment += value * h ** (j + 1) / _FACTORIALS[j + 1]
        return y + increment, {"derivatives": values}

    notices = list(ivp.notices)
    steps, diverged = run_fixed_steps(ivp, stepper)
    if diverged is not None:
        return divergence_response(method_id, ivp, steps, diverged)

    y_end = steps[-1].y
    exact_end = sample_exact(ivp, ivp.x_end)
    abs_error = abs(y_end - exact_end) if exact_end is not None else None
    rel_error = (
        abs(abs_error / exact_end) * 100.0
        if abs_error is not None and exact_end not in (None, 0.0)
        else None
    )

    tables = [solution_table(steps, ivp.decimals), _derivatives_table(steps, order, ivp.decimals)]

    target_values: list[float] = []
    if ivp.targets and len(steps) > 1:
        target_values = interpolate_targets(steps, ivp.targets)
        target_exact = [sample_exact(ivp, x) for x in ivp.targets]
        tables.append(targets_table(ivp.targets, target_values, target_exact, ivp.decimals))

    study = None
    if bool(inputs.get("step_study")):
        study = step_size_study(ivp, stepper, ivp.decimals)
        notices.extend(study.notices)
        if study.table is not None:
            tables.append(study.table)
        if study.orders is not None:
            tables.append(study.orders)

    reference = None
    if exact_end is None:
        reference = reference_endpoint(ivp)
        if reference is not None:
            abs_error = abs(y_end - reference)
            rel_error = abs(abs_error / reference) * 100.0 if reference != 0.0 else None

    tables.append(
        summary_table(ivp, y_end, exact_end, abs_error, rel_error, ivp.decimals, reference=reference)
    )

    steps_out = [
        setup_step(ivp, f"Taylor series method (order {order})"),
        _derivative_step(derivatives),
        *_working_steps(ivp, steps, order),
    ]
    if ivp.targets and target_values:
        lines = [
            rf"y({format_num(x, ivp.decimals)}) \approx {format_num(v, ivp.decimals)}"
            for x, v in zip(ivp.targets, target_values, strict=True)
        ]
        steps_out.append(
            Step(title="Target values", latex=r"\\[1mm]".join(lines), note="Linearly interpolated from the grid.")
        )
    steps_out.append(result_step(ivp, y_end, exact_end if exact_end is not None else reference, abs_error))

    study_plot = (study.hs, study.errors) if study is not None else None
    plot = ivp_plot(
        ivp,
        steps,
        title=f"Taylor series method (order {order}): numerical vs exact",
        study=study_plot,
    )

    result: dict[str, Any] = {
        "x0": ivp.x0,
        "y0": ivp.y0,
        "x_end": ivp.x_end,
        "y_end": y_end,
        "steps": ivp.n,
        "h": ivp.h,
        "order": order,
        "derivatives": [sp.latex(d) for d in derivatives],
        "exact_value": exact_end,
        "reference_value": reference,
        "absolute_error": abs_error,
        "relative_error_percent": rel_error,
        "target_values": target_values,
    }
    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps_out,
        tables=tables,
        plot=plot,
        errors=ErrorInfo(absolute=abs_error, relative_percent=rel_error),
        warnings=notices,
    )
