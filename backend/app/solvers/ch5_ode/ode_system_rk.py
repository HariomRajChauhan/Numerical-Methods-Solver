"""Systems of first-order ODEs solved simultaneously with Runge-Kutta (Chapter 5).

A coupled system ``dY/dx = F(x, Y)`` with two to four components is advanced as
one vector, applying the scalar scheme to every component at the same time. This
is the standard route for coupled equations and for higher-order ODEs once they
have been rewritten as a first-order system.
"""

from __future__ import annotations

from typing import Any

from app.core.models import (
    Chapter,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    SolveResponse,
    SolverLimits,
)
from app.core.registry import register
from app.solvers.ch5_ode._system import (
    compare_field,
    prepare_system,
    scheme_field,
    solve_system,
    system_schema,
)

META = MethodMeta(
    id="ode_system_rk",
    chapter=Chapter.CH5_ODE,
    name="Systems of ODEs (Runge-Kutta)",
    summary=(
        "Advance a coupled system dY/dx = F(x, Y) with two to four components "
        "using fourth-order Runge-Kutta or a second-order pair."
    ),
    variables=["x", "y", "z"],
    theory=(
        "A system of first-order equations, dy_i/dx = f_i(x, y_1, ..., y_m), is "
        "written compactly as dY/dx = F(x, Y) with the vector Y = (y_1, ..., y_m). "
        "Every Runge-Kutta scheme applies unchanged to vectors: the slope k_1 is now "
        "a vector obtained by evaluating all the right-hand sides at the same (x, Y), "
        "and the update adds vector combinations.\n"
        "For the classic fourth-order scheme:\n"
        "  K1 = F(x_n, Y_n),\n"
        "  K2 = F(x_n + h/2, Y_n + (h/2) K1),\n"
        "  K3 = F(x_n + h/2, Y_n + (h/2) K2),\n"
        "  K4 = F(x_n + h, Y_n + h K3),\n"
        "  Y_{n+1} = Y_n + (h/6)(K1 + 2 K2 + 2 K3 + K4).\n"
        "The accuracy is component-wise: each y_i has the same order as the scalar "
        "method. This is how coupled systems and higher-order ODEs (converted to "
        "first-order form) are integrated numerically."
    ),
    formulas=[
        LabeledLatex(label="System", latex=r"\frac{dY}{dx} = F(x, Y),\qquad Y = (y_1,\dots,y_m)"),
        LabeledLatex(label="Stage 1", latex=r"K_1 = F(x_n, Y_n)"),
        LabeledLatex(
            label="Stage 2",
            latex=r"K_2 = F\!\left(x_n + \tfrac{h}{2},\, Y_n + \tfrac{h}{2} K_1\right)",
        ),
        LabeledLatex(
            label="Stage 3",
            latex=r"K_3 = F\!\left(x_n + \tfrac{h}{2},\, Y_n + \tfrac{h}{2} K_2\right)",
        ),
        LabeledLatex(label="Stage 4", latex=r"K_4 = F\!\left(x_n + h,\, Y_n + h\,K_3\right)"),
        LabeledLatex(
            label="Update",
            latex=r"Y_{n+1} = Y_n + \tfrac{h}{6}\left(K_1 + 2 K_2 + 2 K_3 + K_4\right)",
        ),
        LabeledLatex(label="Global error", latex=r"\left\|E_n\right\| = O(h^4)"),
    ],
    pseudocode=(
        "RK4System(F, x0, Y0, h, n):\n"
        "    for k = 0..n-1:\n"
        "        K1 <- F(x, Y)\n"
        "        K2 <- F(x + h/2, Y + h*K1/2)\n"
        "        K3 <- F(x + h/2, Y + h*K2/2)\n"
        "        K4 <- F(x + h,   Y + h*K3)\n"
        "        Y  <- Y + h/6*(K1 + 2*K2 + 2*K3 + K4)   # vector update\n"
        "        x  <- x + h"
    ),
    input_schema=system_schema(scheme_field(), compare_field()),
    examples=[
        MethodExample(
            name="Harmonic oscillator y' = z, z' = -y",
            description="Exact y = sin(x), y' = cos(x); a circular phase portrait.",
            inputs={
                "equations": "y' = z\nz' = -y",
                "independent_variable": "x",
                "state_variables": "y, z",
                "y0": "0, 1",
                "x0": 0.0,
                "x_end": 6.283185307179586,
                "step_mode": "step",
                "h": 0.1,
                "exact_solutions": "sin(x)\ncos(x)",
                "scheme": "rk4",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Damped oscillator y' = z, z' = -0.5z - y",
            description="A stable spiral in the phase plane; no closed form required.",
            inputs={
                "equations": "y' = z\nz' = -0.5*z - y",
                "independent_variable": "x",
                "state_variables": "y, z",
                "y0": "1, 0",
                "x0": 0.0,
                "x_end": 12.0,
                "step_mode": "step",
                "h": 0.1,
                "scheme": "rk4",
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Comparison: harmonic oscillator",
            description="Overlay Euler, RK2 (Heun) and RK4 with the max-norm error on a log axis.",
            inputs={
                "equations": "y' = z\nz' = -y",
                "independent_variable": "x",
                "state_variables": "y, z",
                "y0": "0, 1",
                "x0": 0.0,
                "x_end": 6.283185307179586,
                "step_mode": "step",
                "h": 0.25,
                "exact_solutions": "sin(x)\ncos(x)",
                "scheme": "rk4",
                "compare": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Integrate a system dY/dx = F(x, Y) with the chosen Runge-Kutta scheme."""
    del limits
    method_id = "ode_system_rk"

    prepared = prepare_system(inputs, method_id)
    if isinstance(prepared, SolveResponse):
        return prepared
    ivp = prepared
    scheme = str(inputs.get("scheme") or "rk4")
    return solve_system(
        ivp,
        scheme,
        method_id=method_id,
        run_compare=bool(inputs.get("compare")),
        run_study=bool(inputs.get("step_study")),
    )
