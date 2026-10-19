"""Euler's method for initial value problems (Chapter 5).

The simplest one-step ODE solver: advance along the tangent line,
``y_{n+1} = y_n + h f(x_n, y_n)``. First-order accurate; included as the
baseline against which the higher-order methods are compared.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.models import (
    Chapter,
    ErrorInfo,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.registry import register
from app.solvers._common import format_num
from app.solvers.ch5_ode._ivp import (
    IVP,
    IVPStep,
    Stepper,
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

MAX_WORKING_STEPS = 12


def _make_stepper(ivp: IVP) -> Stepper:
    def step(x: float, y: float, h: float) -> tuple[float, dict[str, Any]]:
        slope = float(ivp.f(x, y))
        return y + h * slope, {"slope": slope}

    return step


def _working_steps(ivp: IVP, steps: list[IVPStep]) -> list[Step]:
    output: list[Step] = []
    for step in steps[1 : MAX_WORKING_STEPS + 1]:
        previous = steps[step.k - 1]
        slope = float(step.data.get("slope", 0.0))
        output.append(
            Step(
                title=f"Step {step.k}",
                latex=(
                    rf"y_{{{step.k}}} = y_{{{step.k - 1}}} + h\,f(x_{{{step.k - 1}}}, y_{{{step.k - 1}}})"
                    rf"\\[1mm] = {format_num(previous.y, ivp.decimals)} + "
                    rf"{format_num(ivp.h, ivp.decimals)}\cdot{format_num(slope, ivp.decimals)}"
                    rf" = {format_num(step.y, ivp.decimals)}"
                    rf"\\[1mm] x_{{{step.k}}} = {format_num(step.x, ivp.decimals)}"
                ),
            )
        )
    if len(steps) - 1 > MAX_WORKING_STEPS:
        output.append(
            Step(
                title="Remaining steps",
                note=(
                    f"The working for the remaining {len(steps) - 1 - MAX_WORKING_STEPS} "
                    "steps follows the same pattern; every step is listed in the table."
                ),
            )
        )
    return output


def _instability_warning(ivp: IVP, steps: list[IVPStep]) -> list[str]:
    if ivp.dfdy is None:
        return []
    worst = 0.0
    worst_x = ivp.x0
    for step in steps:
        try:
            value = float(ivp.dfdy(step.x, step.y))
        except Exception:
            continue
        if math.isnan(value) or math.isinf(value):
            continue
        factor = abs(1.0 + ivp.h * value)
        if factor > worst:
            worst = factor
            worst_x = step.x
    if worst > 1.0:
        return [
            "Euler's method is unstable for this step: "
            f"|1 + h·(∂f/∂y)| = {format_num(worst, 4)} > 1 near x = "
            f"{format_num(worst_x, ivp.decimals)}. Expect growing oscillations — reduce h."
        ]
    return []


META = MethodMeta(
    id="euler",
    chapter=Chapter.CH5_ODE,
    name="Euler's Method",
    summary=(
        "The forward Euler method: advance along the tangent line y_{n+1} = y_n + h f(x_n, y_n). "
        "First-order accurate and the baseline for comparing higher-order schemes."
    ),
    variables=["x", "y"],
    theory=(
        "Euler's method truncates the Taylor series of y(x + h) after the linear term. "
        "Starting from y(x_0) = y_0 it marches forward with\n"
        "  y_{n+1} = y_n + h f(x_n, y_n),   x_{n+1} = x_n + h.\n"
        "The local error per step is O(h^2) and the global error is O(h), so halving the "
        "step roughly halves the error. The method is simple but only conditionally stable: "
        "for the model problem y' = λy the amplification factor is 1 + hλ, and the solution "
        "grows spuriously (oscillates and diverges) whenever |1 + hλ| > 1. Backward "
        "integration (x_end < x_0, h < 0) is allowed and follows the same recurrence."
    ),
    formulas=[
        LabeledLatex(label="Euler step", latex=r"y_{n+1} = y_n + h\,f(x_n, y_n)"),
        LabeledLatex(label="Local truncation error", latex=r"T = \tfrac{1}{2} h^2 y''(\xi) = O(h^2)"),
        LabeledLatex(label="Global error", latex=r"E_n = O(h)"),
        LabeledLatex(
            label="Stability",
            latex=r"|1 + h\,\partial f/\partial y| \le 1",
        ),
    ],
    pseudocode=(
        "Euler(f, x0, y0, h, n):\n"
        "    x <- x0;  y <- y0\n"
        "    for k = 0..n-1:\n"
        "        slope <- f(x, y)\n"
        "        y <- y + h * slope\n"
        "        x <- x + h\n"
        "    return y"
    ),
    input_schema=ivp_schema(),
    examples=[
        MethodExample(
            name="y' = x + y, y(0) = 1",
            description="Classic test problem; exact y = 2e^x - x - 1.",
            inputs={
                "function": "x + y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "step",
                "h": 0.1,
                "exact_solution": "2*exp(x) - x - 1",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Stiff instability: y' = -20y",
            description="h = 0.2 gives |1 + h·(-20)| = 3 > 1, so the solution oscillates and grows.",
            inputs={
                "function": "-20*y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "step",
                "h": 0.2,
                "exact_solution": "exp(-20*x)",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="y' = -2xy, y(0) = 1",
            description="Exact y = e^{-x^2}; a smooth, stable decay.",
            inputs={
                "function": "-2*x*y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "steps",
                "n": 10,
                "exact_solution": "exp(-x^2)",
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate y' = f(x, y) with the forward Euler method."""
    del limits
    method_id = "euler"
    prepared = prepare_ivp(inputs, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    ivp = prepared
    if ivp.n == 0:
        return degenerate_response(method_id, ivp)

    notices = list(ivp.notices)
    stepper = _make_stepper(ivp)
    steps, diverged = run_fixed_steps(ivp, stepper)
    if diverged is not None:
        return divergence_response(method_id, ivp, steps, diverged)

    notices.extend(_instability_warning(ivp, steps))

    y_end = steps[-1].y
    exact_end = sample_exact(ivp, ivp.x_end)
    abs_error = abs(y_end - exact_end) if exact_end is not None else None
    rel_error = (
        abs(abs_error / exact_end) * 100.0
        if abs_error is not None and exact_end not in (None, 0.0)
        else None
    )

    tables = [solution_table(steps, ivp.decimals)]

    target_values: list[float] = []
    target_exact: list[float | None] = []
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

    tables.append(summary_table(ivp, y_end, exact_end, abs_error, rel_error, ivp.decimals, reference=reference))

    steps_out = [setup_step(ivp, "Euler's method"), *_working_steps(ivp, steps)]
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
        title="Euler's method: numerical vs exact",
        slope_segments=True,
        study=study_plot,
    )

    result: dict[str, Any] = {
        "x0": ivp.x0,
        "y0": ivp.y0,
        "x_end": ivp.x_end,
        "y_end": y_end,
        "steps": ivp.n,
        "h": ivp.h,
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
