"""Classic fourth-order Runge-Kutta for initial value problems (Chapter 5).

Four slope evaluations are combined with weights 1:2:2:1, giving a one-step
method of order four without needing derivatives of ``f``:
``y_{n+1} = y_n + (h/6)(k1 + 2 k2 + 2 k3 + k4)``.
"""

from __future__ import annotations

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
    compare_field,
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
    stage_table,
    step_size_study,
    summary_table,
    targets_table,
)
from app.solvers.ch5_ode._schemes import compare_runs, rk4_step

MAX_WORKING_STEPS = 10


def _working_steps(ivp: IVP, steps: list[IVPStep]) -> list[Step]:
    output: list[Step] = []
    for step in steps[1 : MAX_WORKING_STEPS + 1]:
        previous = steps[step.k - 1]
        k1 = float(step.data.get("k1", 0.0))
        k2 = float(step.data.get("k2", 0.0))
        k3 = float(step.data.get("k3", 0.0))
        k4 = float(step.data.get("k4", 0.0))
        k2_x = previous.x + ivp.h / 2.0
        k2_y = previous.y + ivp.h * k1 / 2.0
        k3_x = previous.x + ivp.h / 2.0
        k3_y = previous.y + ivp.h * k2 / 2.0
        k4_x = previous.x + ivp.h
        k4_y = previous.y + ivp.h * k3
        output.append(
            Step(
                title=f"Step {step.k}",
                latex=(
                    rf"k_1 = f(x_{{{step.k - 1}}}, y_{{{step.k - 1}}}) = "
                    rf"f({format_num(previous.x, ivp.decimals)}, "
                    rf"{format_num(previous.y, ivp.decimals)}) = "
                    rf"{format_num(k1, ivp.decimals)}"
                    rf"\\[1mm] k_2 = f\!\left(x_{{{step.k - 1}}} + \tfrac{{h}}{{2}},\; "
                    rf"y_{{{step.k - 1}}} + \tfrac{{h}}{{2}}k_1\right) = "
                    rf"f({format_num(k2_x, ivp.decimals)}, {format_num(k2_y, ivp.decimals)}) = "
                    rf"{format_num(k2, ivp.decimals)}"
                    rf"\\[1mm] k_3 = f\!\left(x_{{{step.k - 1}}} + \tfrac{{h}}{{2}},\; "
                    rf"y_{{{step.k - 1}}} + \tfrac{{h}}{{2}}k_2\right) = "
                    rf"f({format_num(k3_x, ivp.decimals)}, {format_num(k3_y, ivp.decimals)}) = "
                    rf"{format_num(k3, ivp.decimals)}"
                    rf"\\[1mm] k_4 = f\!\left(x_{{{step.k - 1}}} + h,\; "
                    rf"y_{{{step.k - 1}}} + h\,k_3\right) = "
                    rf"f({format_num(k4_x, ivp.decimals)}, {format_num(k4_y, ivp.decimals)}) = "
                    rf"{format_num(k4, ivp.decimals)}"
                    rf"\\[1mm] y_{{{step.k}}} = y_{{{step.k - 1}}} + \tfrac{{h}}{{6}}"
                    rf"\left(k_1 + 2k_2 + 2k_3 + k_4\right) = "
                    rf"{format_num(previous.y, ivp.decimals)} + "
                    rf"\tfrac{{{format_num(ivp.h, ivp.decimals)}}}{{6}}"
                    rf"\left({format_num(k1, ivp.decimals)} + 2({format_num(k2, ivp.decimals)}) "
                    rf"+ 2({format_num(k3, ivp.decimals)}) + {format_num(k4, ivp.decimals)}\right) = "
                    rf"{format_num(step.y, ivp.decimals)}"
                    rf"\\[1mm] x_{{{step.k}}} = {format_num(step.x, ivp.decimals)}"
                ),
            )
        )
    if len(steps) - 1 > MAX_WORKING_STEPS:
        output.append(
            Step(
                title="Remaining steps",
                note=(
                    f"The remaining {len(steps) - 1 - MAX_WORKING_STEPS} steps follow the "
                    "same four-stage pattern; every step is listed in the table."
                ),
            )
        )
    return output


META = MethodMeta(
    id="runge_kutta_4",
    chapter=Chapter.CH5_ODE,
    name="Runge-Kutta 4th Order",
    summary=(
        "The classic fourth-order Runge-Kutta method: four slope evaluations per step, "
        "weighted 1:2:2:1, with no derivatives of f required."
    ),
    variables=["x", "y"],
    theory=(
        "The fourth-order Runge-Kutta method evaluates the slope four times per step — "
        "at the start, twice at the midpoint and once at the end — and combines them "
        "with the weights 1:2:2:1:\n"
        "  k1 = f(x_n, y_n),\n"
        "  k2 = f(x_n + h/2, y_n + (h/2) k1),\n"
        "  k3 = f(x_n + h/2, y_n + (h/2) k2),\n"
        "  k4 = f(x_n + h, y_n + h k3),\n"
        "  y_{n+1} = y_n + (h/6)(k1 + 2 k2 + 2 k3 + k4).\n"
        "It matches the Taylor expansion through the h^4 term, so the local error is "
        "O(h^5) and the global error is O(h^4): halving h cuts the error by about 16. "
        "Only four function evaluations are needed per step and no analytical "
        "derivatives, which is why RK4 is the standard workhorse one-step ODE method."
    ),
    formulas=[
        LabeledLatex(label="Stage 1", latex=r"k_1 = f(x_n, y_n)"),
        LabeledLatex(
            label="Stage 2",
            latex=r"k_2 = f\!\left(x_n + \tfrac{h}{2},\, y_n + \tfrac{h}{2} k_1\right)",
        ),
        LabeledLatex(
            label="Stage 3",
            latex=r"k_3 = f\!\left(x_n + \tfrac{h}{2},\, y_n + \tfrac{h}{2} k_2\right)",
        ),
        LabeledLatex(label="Stage 4", latex=r"k_4 = f\!\left(x_n + h,\, y_n + h\,k_3\right)"),
        LabeledLatex(
            label="Update",
            latex=r"y_{n+1} = y_n + \tfrac{h}{6}\left(k_1 + 2 k_2 + 2 k_3 + k_4\right)",
        ),
        LabeledLatex(
            label="Butcher tableau",
            latex=r"\begin{array}{c|cccc} 0 & & & & \\ \tfrac{1}{2} & \tfrac{1}{2} & & & \\ "
            r"\tfrac{1}{2} & 0 & \tfrac{1}{2} & & \\ 1 & 0 & 0 & 1 & \\ \hline "
            r"& \tfrac{1}{6} & \tfrac{1}{3} & \tfrac{1}{3} & \tfrac{1}{6} \end{array}",
        ),
        LabeledLatex(label="Global error", latex=r"E_n = O(h^4)"),
    ],
    pseudocode=(
        "RK4(f, x0, y0, h, n):\n"
        "    for k = 0..n-1:\n"
        "        k1 <- f(x, y)\n"
        "        k2 <- f(x + h/2, y + h*k1/2)\n"
        "        k3 <- f(x + h/2, y + h*k2/2)\n"
        "        k4 <- f(x + h,   y + h*k3)\n"
        "        y  <- y + h/6*(k1 + 2*k2 + 2*k3 + k4)\n"
        "        x  <- x + h"
    ),
    input_schema=ivp_schema(compare_field()),
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
            name="y' = -2xy, y(0) = 1",
            description="Exact y = e^{-x^2}; very high accuracy with a modest step.",
            inputs={
                "function": "-2*x*y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 2.0,
                "step_mode": "step",
                "h": 0.2,
                "exact_solution": "exp(-x^2)",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Comparison: y' = x + y, y(0) = 1",
            description="Overlay Euler, RK2 (Heun) and RK4 with the error on a log axis.",
            inputs={
                "function": "x + y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "step",
                "h": 0.25,
                "exact_solution": "2*exp(x) - x - 1",
                "compare": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate y' = f(x, y) with the classic fourth-order Runge-Kutta method."""
    del limits
    method_id = "runge_kutta_4"

    prepared = prepare_ivp(inputs, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    ivp = prepared
    if ivp.n == 0:
        return degenerate_response(method_id, ivp)

    notices = list(ivp.notices)
    stepper = rk4_step(ivp)
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

    tables = [
        solution_table(steps, ivp.decimals),
        stage_table(steps, ["k1", "k2", "k3", "k4"], ivp.decimals, title="Runge-Kutta stages"),
    ]

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

    compare = None
    if bool(inputs.get("compare")):
        compare = compare_runs(ivp, "Heun", 0.5, ivp.decimals)
        notices.extend(compare.notices)
        if compare.table is not None:
            tables.append(compare.table)

    tables.append(
        summary_table(ivp, y_end, exact_end, abs_error, rel_error, ivp.decimals, reference=reference)
    )

    steps_out = [setup_step(ivp, "RK4"), *_working_steps(ivp, steps)]
    if ivp.targets and target_values:
        lines = [
            rf"y({format_num(x, ivp.decimals)}) \approx {format_num(v, ivp.decimals)}"
            for x, v in zip(ivp.targets, target_values, strict=True)
        ]
        steps_out.append(
            Step(
                title="Target values",
                latex=r"\\[1mm]".join(lines),
                note="Linearly interpolated from the grid.",
            )
        )
    steps_out.append(
        result_step(ivp, y_end, exact_end if exact_end is not None else reference, abs_error)
    )

    study_plot = (study.hs, study.errors) if study is not None else None
    plot = ivp_plot(
        ivp,
        steps,
        title="RK4: numerical vs exact",
        study=study_plot,
    )
    if compare is not None and compare.plot is not None:
        plot = compare.plot

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
