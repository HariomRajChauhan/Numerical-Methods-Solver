"""Second-order ODEs ``y'' = f(x, y, y')`` solved with Runge-Kutta (Chapter 5).

The equation is reduced to the first-order system ``y' = z``, ``z' = f(x, y, z)``
and handed to the shared vector engine, so the integration logic is exactly the
one used by the system solver. The substitution and the plots of ``y(x)``,
``y'(x)`` and the phase portrait are the only additions.
"""

from __future__ import annotations

from typing import Any

import sympy as sp

from app.core.errors import InvalidInputError
from app.core.models import (
    Chapter,
    InputField,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SolveResponse,
    SolverLimits,
    Step,
)
from app.core.parser import make_function, parse_expression
from app.core.registry import register
from app.solvers._common import (
    format_num,
    number_field,
)
from app.solvers.ch5_ode._system import (
    SystemIVP,
    compare_field,
    resolve_grid,
    scheme_field,
    solve_system,
    system_schema,
)


def _second_order_schema() -> list[InputField]:
    shared = {"equations", "independent_variable", "state_variables", "y0", "exact_solutions"}
    schema = [field for field in system_schema(scheme_field(), compare_field()) if field.key not in shared]
    schema += [
        InputField(
            key="function",
            label="Second-order equation y'' = f(x, y, y')",
            type="function",
            required=True,
            variable="x, y, z",
            placeholder="-y",
            help="Right-hand side of y'' = f(x, y, y'). The derivative y' is called z.",
        ),
        number_field("y0", "Initial y(x0)", 1.0),
        number_field("yp0", "Initial y'(x0)", 0.0),
        InputField(
            key="y_exact",
            label="Exact solution y(x) (optional)",
            type="function",
            required=False,
            variable="x",
            placeholder="cos(x)",
            help="When given, the table and plot show the exact y, its derivative and the error.",
        ),
    ]
    return schema


META = MethodMeta(
    id="ode_second_order_rk",
    chapter=Chapter.CH5_ODE,
    name="Second-Order ODEs (Runge-Kutta)",
    summary=(
        "Solve y'' = f(x, y, y') by substituting z = y' and applying the "
        "Runge-Kutta system solver to (y, z)."
    ),
    variables=["x", "y", "z"],
    theory=(
        "A second-order initial value problem y'' = f(x, y, y'), y(x0) = y0, "
        "y'(x0) = z0 is converted into a first-order system by writing z = y':\n"
        "  y' = z,\n"
        "  z' = f(x, y, z).\n"
        "The vector (y, z) is then advanced with the same Runge-Kutta scheme used "
        "for systems; the initial slope z0 supplies the missing second component. "
        "This is the standard approach for vibrating systems, beam deflection and "
        "any equation whose highest derivative is of order two. The plot of z(x) is "
        "the numerical derivative of the solution, and the (y, z) curve is the "
        "phase portrait of the motion."
    ),
    formulas=[
        LabeledLatex(label="Given", latex=r"y'' = f(x, y, y'),\quad y(x_0) = y_0,\quad y'(x_0) = z_0"),
        LabeledLatex(label="Substitution", latex=r"z = y'"),
        LabeledLatex(label="System", latex=r"y' = z,\qquad z' = f(x, y, z)"),
        LabeledLatex(label="Initial vector", latex=r"Y(x_0) = \begin{pmatrix} y_0 \\ z_0 \end{pmatrix}"),
        LabeledLatex(
            label="RK4 update",
            latex=r"Y_{n+1} = Y_n + \tfrac{h}{6}\left(K_1 + 2 K_2 + 2 K_3 + K_4\right)",
        ),
    ],
    pseudocode=(
        "RK4SecondOrder(f, x0, y0, z0, h, n):\n"
        "    set y' = z and z' = f(x, y, z)          # reduce to first order\n"
        "    Y <- (y0, z0)\n"
        "    for k = 0..n-1:\n"
        "        K1 <- F(x, Y); K2 <- F(x + h/2, Y + h*K1/2)\n"
        "        K3 <- F(x + h/2, Y + h*K2/2); K4 <- F(x + h, Y + h*K3)\n"
        "        Y <- Y + h/6*(K1 + 2*K2 + 2*K3 + K4)\n"
        "        x <- x + h"
    ),
    input_schema=_second_order_schema(),
    examples=[
        MethodExample(
            name="y'' = -y, y(0) = 1, y'(0) = 0",
            description="Simple harmonic motion; exact y = cos(x), y' = -sin(x).",
            inputs={
                "function": "-y",
                "x0": 0.0,
                "y0": 1.0,
                "yp0": 0.0,
                "x_end": 6.283185307179586,
                "step_mode": "step",
                "h": 0.1,
                "y_exact": "cos(x)",
                "scheme": "rk4",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Damped: y'' + 0.5y' + y = 0, y(0) = 1, y'(0) = 0",
            description="A decaying oscillation; no closed form required.",
            inputs={
                "function": "-0.5*z - y",
                "x0": 0.0,
                "y0": 1.0,
                "yp0": 0.0,
                "x_end": 15.0,
                "step_mode": "step",
                "h": 0.1,
                "scheme": "rk4",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Comparison: y'' = -y, y(0) = 1, y'(0) = 0",
            description="Overlay Euler, RK2 (Heun) and RK4 with the max-norm error on a log axis.",
            inputs={
                "function": "-y",
                "x0": 0.0,
                "y0": 1.0,
                "yp0": 0.0,
                "x_end": 6.283185307179586,
                "step_mode": "step",
                "h": 0.25,
                "y_exact": "cos(x)",
                "scheme": "rk4",
                "compare": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


def _build_system(inputs: dict[str, Any]) -> SystemIVP:
    """Reduce y'' = f(x, y, y') to the first-order system (y' = z, z' = f)."""
    text = inputs.get("function")
    if not text:
        raise InvalidInputError("The second-order equation y'' = f(x, y, y') is required.")

    parsed = parse_expression(str(text), ("x", "y", "z"))
    f = make_function(parsed, ("x", "y", "z"), strict=False)
    z_component = make_function(sp.Symbol("z"), ("x", "y", "z"), strict=False)

    x0 = float(inputs.get("x0", 0.0))
    x_end = float(inputs.get("x_end", 1.0))
    y0 = float(inputs.get("y0", 1.0))
    z0 = float(inputs.get("yp0", 0.0))
    decimals = int(inputs.get("decimal_precision", 6))

    exact_func = None
    y_exact = inputs.get("y_exact")
    if y_exact:
        exact_expr = parse_expression(str(y_exact), ("x",))
        exact_func = make_function(exact_expr, ("x",), strict=False)
        dz_expr = sp.diff(exact_expr, sp.Symbol("x"))
        dz_func = make_function(dz_expr, ("x",), strict=False)
    else:
        dz_func = None

    targets = [] if inputs.get("targets") is None else [float(v) for v in inputs["targets"]]

    x0, x_end, h, n, notices = resolve_grid(inputs)
    return SystemIVP(
        funcs=[z_component, f],
        exprs=[sp.Symbol("z"), parsed],
        var_names=["y", "z"],
        x_name="x",
        x0=x0,
        y0=[y0, z0],
        x_end=x_end,
        h=h,
        n=n,
        decimals=decimals,
        exact_funcs=[exact_func, dz_func],
        targets=targets,
        notices=notices,
    )


def _substitution_step(ivp: SystemIVP) -> Step:
    return Step(
        title="Reduce to a first-order system",
        latex=(
            rf"\text{{Let }} z = y' \;\Rightarrow\; y' = z,\qquad "
            rf"z' = f({ivp.x_name}, y, z)"
            rf"\\[1mm] Y({format_num(ivp.x0, ivp.decimals)}) = "
            rf"\begin{{pmatrix}} {format_num(ivp.y0[0], ivp.decimals)} \\ "
            rf"{format_num(ivp.y0[1], ivp.decimals)} \end{{pmatrix}}"
        ),
    )


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate y'' = f(x, y, y') by reducing it to a first-order system."""
    del limits
    method_id = "ode_second_order_rk"

    ivp = _build_system(inputs)
    scheme = str(inputs.get("scheme") or "rk4")
    return solve_system(
        ivp,
        scheme,
        method_id=method_id,
        preamble=[_substitution_step(ivp)],
        title="Second-order RK solution",
        run_compare=bool(inputs.get("compare")),
        run_study=bool(inputs.get("step_study")),
    )
