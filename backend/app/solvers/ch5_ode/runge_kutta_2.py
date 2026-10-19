"""Second-order Runge-Kutta family for initial value problems (Chapter 5).

All two-stage variants share ``y_{n+1} = y_n + h[(1 - a2) k1 + a2 k2]`` with
``k1 = f(x, y)`` and ``k2 = f(x + h/(2 a2), y + h/(2 a2) k1)``. The weight
``a2`` selects the classic pairs:

* ``a2 = 1/2`` — Heun (improved Euler / explicit trapezoidal),
* ``a2 = 1``   — midpoint,
* ``a2 = 2/3`` — Ralston (minimum truncation error).
"""

from __future__ import annotations

from typing import Any

from app.core.models import (
    Chapter,
    ErrorInfo,
    InputField,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SelectOption,
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
from app.solvers.ch5_ode._schemes import (
    RK2_VARIANTS,
    compare_runs,
    fraction_latex,
    rk2_step,
)

MAX_WORKING_STEPS = 10


def _variant_field() -> InputField:
    return InputField(
        key="variant",
        label="RK2 variant",
        type="select",
        required=True,
        default="heun",
        options=[
            SelectOption(value="heun", label="Heun (improved Euler)"),
            SelectOption(value="midpoint", label="Midpoint"),
            SelectOption(value="ralston", label="Ralston"),
        ],
        help="All two-stage pairs are second-order accurate; they differ in the k2 point.",
    )


def _tableau_step(a2: float, variant_label: str) -> Step:
    c2 = 1.0 / (2.0 * a2)
    b1 = 1.0 - a2
    b2 = a2
    return Step(
        title="Butcher tableau",
        latex=(
            rf"\text{{{variant_label}:}}\qquad "
            rf"\begin{{array}}{{c|cc}} 0 & & \\ {fraction_latex(c2)} & {fraction_latex(c2)} & "
            rf"\\ \hline & {fraction_latex(b1)} & {fraction_latex(b2)} \end{{array}}"
        ),
        note=(
            "The first column gives the stage points, the last row the weights "
            r"$b_1 = 1 - a_2$ and $b_2 = a_2$."
        ),
    )


def _working_steps(ivp: IVP, steps: list[IVPStep], a2: float) -> list[Step]:
    c2 = 1.0 / (2.0 * a2)
    b1 = fraction_latex(1.0 - a2)
    b2 = fraction_latex(a2)
    output: list[Step] = []
    for step in steps[1 : MAX_WORKING_STEPS + 1]:
        previous = steps[step.k - 1]
        k1 = float(step.data.get("k1", 0.0))
        k2 = float(step.data.get("k2", 0.0))
        arg_x = previous.x + c2 * ivp.h
        arg_y = previous.y + c2 * ivp.h * k1
        output.append(
            Step(
                title=f"Step {step.k}",
                latex=(
                    rf"k_1 = f(x_{{{step.k - 1}}}, y_{{{step.k - 1}}}) = "
                    rf"f({format_num(previous.x, ivp.decimals)}, "
                    rf"{format_num(previous.y, ivp.decimals)}) = "
                    rf"{format_num(k1, ivp.decimals)}"
                    rf"\\[1mm] k_2 = f(x_{{{step.k - 1}}} + {fraction_latex(c2)}h,\; "
                    rf"y_{{{step.k - 1}}} + {fraction_latex(c2)}h\,k_1) = "
                    rf"f({format_num(arg_x, ivp.decimals)}, {format_num(arg_y, ivp.decimals)}) = "
                    rf"{format_num(k2, ivp.decimals)}"
                    rf"\\[1mm] y_{{{step.k}}} = y_{{{step.k - 1}}} + h\left[(1 - a_2)k_1 + a_2 k_2\right] "
                    rf"= {format_num(previous.y, ivp.decimals)} + "
                    rf"{format_num(ivp.h, ivp.decimals)}\left[{b1}\cdot"
                    rf"{format_num(k1, ivp.decimals)} + {b2}\cdot"
                    rf"{format_num(k2, ivp.decimals)}\right] = {format_num(step.y, ivp.decimals)}"
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
                    "same two-stage pattern; every step is listed in the table."
                ),
            )
        )
    return output


META = MethodMeta(
    id="runge_kutta_2",
    chapter=Chapter.CH5_ODE,
    name="Runge-Kutta 2nd Order",
    summary=(
        "Two-stage second-order Runge-Kutta in the Heun, midpoint or Ralston variant; "
        "two slope evaluations per step give O(h^2) accuracy."
    ),
    variables=["x", "y"],
    theory=(
        "Runge-Kutta methods replace Taylor derivatives with extra slope evaluations. "
        "The two-stage family takes a slope k1 = f(x, y) at the current point and a "
        "second slope k2 at a predicted point, then advances with a weighted average:\n"
        "  k1 = f(x_n, y_n),\n"
        "  k2 = f(x_n + h/(2 a2), y_n + h/(2 a2) k1),\n"
        "  y_{n+1} = y_n + h[(1 - a2) k1 + a2 k2].\n"
        "The weight a2 = 1/2 gives Heun (the explicit trapezoidal rule, k2 at x + h), "
        "a2 = 1 gives the midpoint rule (k2 at x + h/2) and a2 = 2/3 gives Ralston's "
        "pair, which minimises the leading truncation error. Every variant is second "
        "order: the local error is O(h^3) and the global error is O(h^2), so halving h "
        "cuts the error by about four. Two function evaluations are used per step, the "
        "cheapest real improvement over first-order Euler."
    ),
    formulas=[
        LabeledLatex(
            label="Stage 1",
            latex=r"k_1 = f(x_n, y_n)",
        ),
        LabeledLatex(
            label="Stage 2",
            latex=r"k_2 = f\!\left(x_n + \frac{h}{2 a_2},\, y_n + \frac{h}{2 a_2} k_1\right)",
        ),
        LabeledLatex(
            label="Update",
            latex=r"y_{n+1} = y_n + h\bigl[(1 - a_2) k_1 + a_2 k_2\bigr]",
        ),
        LabeledLatex(
            label="Weights",
            latex=r"a_2 = \tfrac12\ (\text{Heun}),\quad 1\ (\text{midpoint}),\quad "
            r"\tfrac23\ (\text{Ralston})",
        ),
        LabeledLatex(label="Global error", latex=r"E_n = O(h^2)"),
    ],
    pseudocode=(
        "RK2(f, x0, y0, h, n, a2):\n"
        "    c2 <- 1 / (2*a2)\n"
        "    for k = 0..n-1:\n"
        "        k1 <- f(x, y)\n"
        "        k2 <- f(x + c2*h, y + c2*h*k1)\n"
        "        y  <- y + h*((1 - a2)*k1 + a2*k2)\n"
        "        x  <- x + h"
    ),
    input_schema=ivp_schema(_variant_field(), compare_field()),
    examples=[
        MethodExample(
            name="Heun: y' = x + y, y(0) = 1",
            description="a2 = 1/2; exact y = 2e^x - x - 1.",
            inputs={
                "function": "x + y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "step",
                "h": 0.1,
                "variant": "heun",
                "exact_solution": "2*exp(x) - x - 1",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Midpoint: y' = x + y, y(0) = 1",
            description="a2 = 1; the k2 slope is taken at the midpoint x + h/2.",
            inputs={
                "function": "x + y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "step",
                "h": 0.1,
                "variant": "midpoint",
                "exact_solution": "2*exp(x) - x - 1",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Ralston: y' = -2xy, y(0) = 1",
            description="a2 = 2/3; exact y = e^{-x^2}.",
            inputs={
                "function": "-2*x*y",
                "x0": 0.0,
                "y0": 1.0,
                "x_end": 1.0,
                "step_mode": "steps",
                "n": 10,
                "variant": "ralston",
                "exact_solution": "exp(-x^2)",
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate y' = f(x, y) with a two-stage second-order Runge-Kutta pair."""
    del limits
    method_id = "runge_kutta_2"
    variant_key = str(inputs.get("variant", "heun"))
    a2, variant_label = RK2_VARIANTS.get(variant_key, RK2_VARIANTS["heun"])

    prepared = prepare_ivp(inputs, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    ivp = prepared
    if ivp.n == 0:
        return degenerate_response(method_id, ivp)

    notices = list(ivp.notices)
    stepper = rk2_step(ivp, a2)
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
        stage_table(steps, ["k1", "k2"], ivp.decimals, title="Runge-Kutta stages"),
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
        compare = compare_runs(ivp, variant_key.capitalize(), a2, ivp.decimals)
        notices.extend(compare.notices)
        if compare.table is not None:
            tables.append(compare.table)

    tables.append(
        summary_table(ivp, y_end, exact_end, abs_error, rel_error, ivp.decimals, reference=reference)
    )

    steps_out = [
        setup_step(ivp, f"RK2 ({variant_label})"),
        _tableau_step(a2, variant_label),
        *_working_steps(ivp, steps, a2),
    ]
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
        title=f"RK2 ({variant_label}): numerical vs exact",
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
        "variant": variant_label,
        "a2": a2,
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
