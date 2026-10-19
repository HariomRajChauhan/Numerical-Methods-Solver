"""Canonical one-step Runge-Kutta schemes shared by the Chapter 5 solvers.

Private module (leading underscore) so the auto-loader skips it. It holds the
Euler, two-stage (Heun / midpoint / Ralston) and classic four-stage steppers,
plus the ``Euler vs RK2 vs RK4`` comparison table and overlay used by the
Runge-Kutta methods. Keeping the schemes here means the comparison never
duplicates integration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

import numpy as np

from app.core.models import DataTable, PlotPayload
from app.solvers._common import format_num
from app.solvers.ch5_ode._ivp import (
    IVP,
    Stepper,
    reference_sampler,
    run_fixed_steps,
)

# Two-stage family: y_{n+1} = y_n + h[(1 - a2) k1 + a2 k2] with
# k1 = f(x, y) and k2 = f(x + c2 h, y + c2 h k1), where c2 = 1 / (2 a2).
RK2_VARIANTS: dict[str, tuple[float, str]] = {
    "heun": (0.5, "Heun (improved Euler)"),
    "midpoint": (1.0, "Midpoint"),
    "ralston": (2.0 / 3.0, "Ralston"),
}


def euler_step(ivp: IVP) -> Stepper:
    """The first-order Euler stepper ``y + h f(x, y)``."""

    def step(x: float, y: float, h: float) -> tuple[float, dict[str, Any]]:
        slope = float(ivp.f(x, y))
        return y + h * slope, {"k1": slope}

    return step


def rk2_step(ivp: IVP, a2: float) -> Stepper:
    """The two-stage RK stepper for the weight ``a2`` (see :data:`RK2_VARIANTS`)."""
    c2 = 1.0 / (2.0 * a2)

    def step(x: float, y: float, h: float) -> tuple[float, dict[str, Any]]:
        k1 = float(ivp.f(x, y))
        k2 = float(ivp.f(x + c2 * h, y + c2 * h * k1))
        y_next = y + h * ((1.0 - a2) * k1 + a2 * k2)
        return y_next, {"k1": k1, "k2": k2}

    return step


def rk4_step(ivp: IVP) -> Stepper:
    """The classic fourth-order RK stepper (weighted 1:2:2:1)."""

    def step(x: float, y: float, h: float) -> tuple[float, dict[str, Any]]:
        k1 = float(ivp.f(x, y))
        k2 = float(ivp.f(x + h / 2.0, y + h * k1 / 2.0))
        k3 = float(ivp.f(x + h / 2.0, y + h * k2 / 2.0))
        k4 = float(ivp.f(x + h, y + h * k3))
        y_next = y + h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        return y_next, {"k1": k1, "k2": k2, "k3": k3, "k4": k4}

    return step


def fraction_latex(value: float) -> str:
    """Render a rational value as a tidy LaTeX fraction (``\\tfrac{p}{q}``)."""
    frac = Fraction(value).limit_denominator(12)
    if frac.denominator == 1:
        return str(frac.numerator)
    return rf"\tfrac{{{frac.numerator}}}{{{frac.denominator}}}"


# ---------------------------------------------------------------------------
# Euler / RK2 / RK4 comparison
# ---------------------------------------------------------------------------

# Colour per method family, reused by the comparison overlay.
_FAMILY_COLOR = {"Euler": "#94a3b8", "RK2": "#f59e0b", "RK4": "#2563eb"}


@dataclass
class Comparison:
    """The outcome of the optional Euler / RK2 / RK4 comparison."""

    table: DataTable | None = None
    plot: PlotPayload | None = None
    notices: list[str] = field(default_factory=list)


def _family(name: str) -> str:
    if name == "Euler":
        return "Euler"
    return "RK2" if name.startswith("RK2") else "RK4"


def compare_runs(ivp: IVP, rk2_label: str, a2: float, decimals: int) -> Comparison:
    """Run Euler, the chosen RK2 pair and RK4 and build the comparison outputs."""
    reference = reference_sampler(ivp)
    reference_end = reference(ivp.x_end)
    if reference_end is None:
        return Comparison(
            notices=["The comparison needs an exact or reference solution at x_end."]
        )

    entries: list[tuple[str, Stepper, int]] = [
        ("Euler", euler_step(ivp), 1),
        (f"RK2 ({rk2_label})", rk2_step(ivp, a2), 2),
        ("RK4", rk4_step(ivp), 4),
    ]

    rows: list[list[Any]] = []
    y_traces: list[dict[str, Any]] = []
    error_traces: list[dict[str, Any]] = []

    for name, stepper, evals_per_step in entries:
        steps, diverged = run_fixed_steps(ivp, stepper)
        if diverged is not None or not steps:
            rows.append([name, "diverged", "n/a", evals_per_step * ivp.n])
            continue
        y_end = steps[-1].y
        error = abs(y_end - reference_end)
        rows.append(
            [
                name,
                format_num(y_end, decimals),
                format_num(error, decimals),
                evals_per_step * ivp.n,
            ]
        )
        color = _FAMILY_COLOR[_family(name)]
        xs = [step.x for step in steps]
        ys = [step.y for step in steps]
        y_traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": name,
                "x": xs,
                "y": ys,
                "marker": {"size": 5, "color": color},
                "line": {"color": color},
                "xaxis": "x",
                "yaxis": "y",
            }
        )
        err_x: list[float] = []
        err_y: list[float] = []
        for step in steps:
            ref = reference(step.x)
            if ref is None:
                continue
            err_x.append(step.x)
            err_y.append(max(abs(step.y - ref), 1e-16))
        error_traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": f"|error| {name}",
                "x": err_x,
                "y": err_y,
                "marker": {"size": 5, "color": color},
                "line": {"color": color},
                "xaxis": "x2",
                "yaxis": "y2",
            }
        )

    grid = np.linspace(ivp.x0, ivp.x_end, 200)
    reference_curve = [reference(float(x)) for x in grid]
    traces: list[dict[str, Any]] = [
        *y_traces,
        {
            "type": "scatter",
            "mode": "lines",
            "name": "Reference y(x)",
            "x": grid.tolist(),
            "y": reference_curve,
            "line": {"color": "#16a34a", "dash": "dash"},
            "xaxis": "x",
            "yaxis": "y",
        },
        *error_traces,
    ]

    layout: dict[str, Any] = {
        "title": {"text": "Euler vs RK2 vs RK4"},
        "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
        "xaxis": {"title": {"text": "x"}, "domain": [0.0, 0.44]},
        "yaxis": {"title": {"text": "y"}, "domain": [0.0, 1.0]},
        "xaxis2": {
            "title": {"text": "x"},
            "domain": [0.56, 1.0],
            "anchor": "y2",
        },
        "yaxis2": {"title": {"text": "|error|"}, "type": "log", "anchor": "x2"},
        "legend": {"orientation": "h", "y": -0.18},
    }

    table = DataTable(
        title="Method comparison",
        columns=["Method", "y(x_end)", "|error at x_end|", "Function evaluations"],
        rows=rows,
    )
    return Comparison(table=table, plot=PlotPayload(traces=traces, layout=layout))
