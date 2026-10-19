"""Shared engine for the Chapter 5 ordinary-differential-equation solvers.

Private module (leading underscore) so the auto-loader skips it. It holds the
input parsing and validation, the shared schema, the fixed-step integration
driver, the solution / target / summary tables, the step-size study, the
``y(x)`` versus exact plot, and the exam-style set-up and result steps common
to every initial-value-problem method.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import sympy as sp

from app.core.errors import InvalidInputError
from app.core.models import (
    DataTable,
    ErrorInfo,
    InputField,
    PlotPayload,
    SelectOption,
    SolveResponse,
    SolveStatus,
    Step,
)
from app.core.parser import make_function, parse_expression
from app.solvers._common import (
    boolean_field,
    failed_response,
    format_num,
    function_field,
    number_field,
    precision_field,
)
from app.solvers.ch3_interpolation._interp import targets_field

# Safety budget shared by every Chapter 5 IVP method.
MAX_STEPS: int = 10_000
# Symbolic derivatives longer than this are refused (Taylor series method).
MAX_SYMBOLIC_OPS: int = 2_000
# Above this magnitude the numerical solution is treated as having diverged,
# matching the Chapter 1/2 divergence convention.
DIVERGENCE_BOUND: float = 1e10

OdeFunction = Callable[[float, float], float]
ExactFunction = Callable[[float], float]
Stepper = Callable[[float, float, float], "tuple[float, dict[str, Any]]"]


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IVP:
    """A validated initial value problem ``y' = f(x, y)`` on ``[x0, x_end]``."""

    f: OdeFunction
    expr: sp.Expr | None
    x0: float
    y0: float
    x_end: float
    h: float  # signed step
    n: int
    decimals: int
    exact: ExactFunction | None
    exact_expr: sp.Expr | None
    targets: list[float]
    dfdy: OdeFunction | None
    notices: list[str] = field(default_factory=list)


@dataclass
class IVPStep:
    """One stored step of a numerical solution."""

    k: int
    x: float
    y: float
    exact: float | None = None
    error: float | None = None
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def ivp_schema(*extra: InputField, default_h: float = 0.1) -> list[InputField]:
    """The shared input form for every initial value problem."""
    return [
        function_field(
            key="function",
            label="Differential equation y' = f(x, y)",
            variable="x, y",
            placeholder="x + y",
            help=(
                "Right-hand side f(x, y). Use ^ for powers, * for products and any "
                "whitelisted function, e.g. x^2 - y."
            ),
        ),
        number_field("x0", "Initial x0", 0.0),
        number_field("y0", "Initial y0", 1.0),
        number_field("x_end", "End point x_end", 1.0),
        InputField(
            key="step_mode",
            label="Step specification",
            type="select",
            required=True,
            default="step",
            options=[
                SelectOption(value="step", label="Step size h"),
                SelectOption(value="steps", label="Number of steps n"),
            ],
            help="Give the step size directly, or ask for a fixed number of steps.",
        ),
        number_field(
            "h",
            "Step size h",
            default_h,
            required=False,
            help="Positive for a forward march; negative/with x_end < x0 for backward.",
        ),
        InputField(
            key="n",
            label="Number of steps n",
            type="integer",
            required=True,
            default=10,
            min=1,
            max=MAX_STEPS,
            help="Used when the step specification is a number of steps.",
        ),
        function_field(
            key="exact_solution",
            label="Exact solution y(x) (optional)",
            variable="x",
            placeholder="2*exp(x) - x - 1",
            required=False,
            help="When given, the table and plot show the exact y and its error.",
        ),
        targets_field(
            required=False,
            label="Target x values (optional)",
            help="Extra x values at which to report y, separated by commas.",
        ),
        boolean_field(
            "step_study",
            "Step-size study (h, h/2, h/4)",
            False,
            help="Compare the error at x_end for h, h/2 and h/4 and estimate the order.",
        ),
        *extra,
        precision_field(),
    ]


def compare_field() -> InputField:
    """The shared 'compare Euler / RK2 / RK4' checkbox for Chapter 5 methods."""
    return boolean_field(
        "compare",
        "Compare with Euler and RK4",
        False,
        help="Run Euler, the chosen RK2 pair and RK4 on the same problem and overlay them.",
    )


# ---------------------------------------------------------------------------
# Preparation
# ---------------------------------------------------------------------------


def _degenerate_ivp(inputs: dict[str, Any]) -> bool:
    return float(inputs.get("x0", 0.0)) == float(inputs.get("x_end", 1.0))


def prepare_ivp(inputs: dict[str, Any], method_id: str) -> IVP | SolveResponse:
    """Parse and validate the shared IVP inputs.

    Returns an :class:`IVP`, or a ``failed`` :class:`SolveResponse` for the
    degenerate zero-length interval (handled by the caller).
    """
    text = inputs.get("function")
    if not text:
        raise InvalidInputError("The differential equation y' = f(x, y) is required.")

    decimals = int(inputs.get("decimal_precision", 6))
    x0 = float(inputs.get("x0", 0.0))
    y0 = float(inputs.get("y0", 1.0))
    x_end = float(inputs.get("x_end", 1.0))
    notices: list[str] = []

    expr = parse_expression(text, ("x", "y"))
    f = make_function(expr, ("x", "y"), strict=False)

    dfdy: OdeFunction | None = None
    try:
        dfdy_expr = sp.diff(expr, sp.Symbol("y"))
        dfdy = make_function(dfdy_expr, ("x", "y"), strict=False)
    except Exception:  # pragma: no cover - numeric-only fallback
        dfdy = None

    exact: ExactFunction | None = None
    exact_expr: sp.Expr | None = None
    exact_text = inputs.get("exact_solution")
    if exact_text:
        exact_expr = parse_expression(exact_text, ("x",))
        exact = make_function(exact_expr, ("x",), strict=False)

    targets = [] if inputs.get("targets") is None else [float(v) for v in inputs["targets"]]

    if x0 == x_end:
        return IVP(
            f, expr, x0, y0, x_end, 0.0, 0, decimals, exact, exact_expr, targets, dfdy, notices
        )

    direction = 1.0 if x_end > x0 else -1.0
    step_mode = str(inputs.get("step_mode", "step"))
    if step_mode == "steps":
        n = int(inputs.get("n", 10))
        if n < 1:
            raise InvalidInputError("The number of steps n must be at least 1.")
        if n > MAX_STEPS:
            raise InvalidInputError(
                f"The number of steps must be at most {MAX_STEPS}.",
                hint="Use a larger step size or a shorter interval.",
            )
        h = (x_end - x0) / n
    else:
        h_input = float(inputs.get("h", 0.1))
        if h_input == 0.0:
            raise InvalidInputError(
                "The step size h must be non-zero.",
                hint="Use a positive h for a forward march, or a negative h to go backward.",
            )
        magnitude = abs(h_input)
        if math.copysign(1.0, h_input) != direction:
            notices.append(
                "The sign of h was reversed so the march runs from x0 towards x_end."
            )
        n = round(abs(x_end - x0) / magnitude)
        if n < 1:
            raise InvalidInputError(
                "The step size h is larger than the interval |x_end - x0|.",
                hint="Choose a smaller h or use the number-of-steps mode.",
            )
        h = direction * (abs(x_end - x0) / n)
        if not math.isclose(abs(x0 + n * h - x_end), 0.0, abs_tol=1e-9 * max(1.0, abs(x_end))):
            notices.append(
                f"The step h = {magnitude:g} did not divide [x0, x_end] exactly; "
                f"n = {n} steps with h = {h:g} were used instead."
            )
        if n > MAX_STEPS:
            raise InvalidInputError(
                f"The step size needs more than {MAX_STEPS} steps.",
                hint="Use a larger h or the number-of-steps mode.",
            )

    if direction < 0:
        notices.append(
            "Backward integration: x_end < x0, so the method marches in the negative x "
            "direction with h < 0."
        )

    return IVP(
        f, expr, x0, y0, x_end, h, n, decimals, exact, exact_expr, targets, dfdy, notices
    )


# ---------------------------------------------------------------------------
# Integration driver
# ---------------------------------------------------------------------------


def run_fixed_steps(
    ivp: IVP,
    stepper: Stepper,
    *,
    n: int | None = None,
    h: float | None = None,
) -> tuple[list[IVPStep], int | None]:
    """March the fixed-step method forward, recording every step.

    Returns ``(steps, diverged_at)`` where ``diverged_at`` is the 1-based step
    number at which a non-finite value appeared, or ``None`` on success.
    """
    steps: list[IVPStep] = []
    x, y = ivp.x0, ivp.y0
    exact0 = _safe(ivp.exact, x) if ivp.exact is not None else None
    error0 = abs(y - exact0) if exact0 is not None else None
    steps.append(IVPStep(0, x, y, exact0, error0, {}))
    total = ivp.n if n is None else n
    step = ivp.h if h is None else h

    for k in range(total):
        y_next, data = stepper(x, y, step)
        x_next = x + step
        if not (math.isfinite(y_next) and math.isfinite(x_next)) or abs(y_next) > DIVERGENCE_BOUND:
            return steps, k + 1
        exact_val = _safe(ivp.exact, x_next) if ivp.exact is not None else None
        error = abs(y_next - exact_val) if exact_val is not None else None
        steps.append(IVPStep(k + 1, x_next, y_next, exact_val, error, data))
        x, y = x_next, y_next
    return steps, None


def reference_sampler(ivp: IVP) -> Callable[[float], float | None]:
    """A callable giving the exact (or high-accuracy reference) ``y`` at any ``x``.

    Uses the supplied exact solution when present, otherwise a dense
    ``scipy.integrate.solve_ivp`` reference. Returns ``None`` at points where the
    reference cannot be evaluated, so overlays stay robust.
    """
    exact = ivp.exact
    if exact is not None:
        return lambda x: _safe(exact, x)

    try:
        from scipy.integrate import solve_ivp

        solution = solve_ivp(
            lambda t, state: [ivp.f(t, state[0])],
            [ivp.x0, ivp.x_end],
            [ivp.y0],
            rtol=1e-11,
            atol=1e-13,
            dense_output=True,
        )
    except Exception:
        return lambda x: None
    if not solution.success:
        return lambda x: None

    def sample(x: float) -> float | None:
        try:
            value = float(solution.sol(x)[0])
        except Exception:
            return None
        return value if math.isfinite(value) else None

    return sample


def _safe(fn: ExactFunction, x: float) -> float | None:
    try:
        value = float(fn(x))
    except Exception:
        return None
    return value if math.isfinite(value) else None


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def solution_table(steps: list[IVPStep], decimals: int) -> DataTable:
    has_exact = any(step.exact is not None for step in steps)
    columns = ["k", "x", "y", "Exact y", "|error|"] if has_exact else ["k", "x", "y"]
    rows: list[list[Any]] = []
    for step in steps:
        row: list[Any] = [step.k, format_num(step.x, decimals), format_num(step.y, decimals)]
        if has_exact:
            row.append(format_num(step.exact, decimals) if step.exact is not None else "n/a")
            row.append(format_num(step.error, decimals) if step.error is not None else "n/a")
        rows.append(row)
    return DataTable(title="Numerical solution", columns=columns, rows=rows)


def stage_table(
    steps: list[IVPStep],
    stage_labels: list[str],
    decimals: int,
    *,
    title: str,
) -> DataTable:
    """A table of the Runge-Kutta stage slopes ``k1, k2, ...`` per step."""
    has_exact = any(step.exact is not None for step in steps)
    columns = ["step", "x", "y", *stage_labels]
    if has_exact:
        columns += ["Exact y", "|error|"]
    rows: list[list[Any]] = []
    for step in steps:
        row: list[Any] = [step.k, format_num(step.x, decimals), format_num(step.y, decimals)]
        for label in stage_labels:
            value = step.data.get(label)
            if isinstance(value, int | float) and math.isfinite(float(value)):
                row.append(format_num(float(value), decimals))
            else:
                row.append(r"\text{--}")
        if has_exact:
            row.append(format_num(step.exact, decimals) if step.exact is not None else "n/a")
            row.append(format_num(step.error, decimals) if step.error is not None else "n/a")
        rows.append(row)
    return DataTable(title=title, columns=columns, rows=rows)


def targets_table(
    targets: list[float], values: list[float], exact: list[float | None], decimals: int
) -> DataTable:
    rows: list[list[Any]] = []
    for target, value, exact_value in zip(targets, values, exact, strict=True):
        row: list[Any] = [format_num(target, decimals), format_num(value, decimals)]
        if exact_value is not None:
            row.append(format_num(exact_value, decimals))
            row.append(format_num(abs(value - exact_value), decimals))
        rows.append(row)
    columns = ["Target x", "y (interpolated)", "Exact y", "|error|"] if any(
        value is not None for value in exact
    ) else ["Target x", "y (interpolated)"]
    return DataTable(title="Values at the target x", columns=columns, rows=rows)


def summary_table(
    ivp: IVP,
    y_end: float,
    exact_end: float | None,
    abs_error: float | None,
    rel_error: float | None,
    decimals: int,
    *,
    reference: float | None = None,
) -> DataTable:
    rows: list[list[Any]] = [
        ["Final x", format_num(ivp.x_end, decimals)],
        ["y (numerical)", format_num(y_end, decimals)],
    ]
    if exact_end is not None:
        rows.append(["Exact y (given)", format_num(exact_end, decimals)])
    if reference is not None:
        rows.append(["Reference y (solve_ivp)", format_num(reference, decimals)])
    if abs_error is not None:
        rows.append(["Absolute error", format_num(abs_error, decimals)])
    if rel_error is not None:
        rows.append(["Relative error (%)", format_num(rel_error, decimals)])
    return DataTable(title="Result summary", columns=["Quantity", "Value"], rows=rows)


# ---------------------------------------------------------------------------
# Values at arbitrary target x (linear interpolation of the computed grid)
# ---------------------------------------------------------------------------


def interpolate_targets(steps: list[IVPStep], targets: list[float]) -> list[float]:
    xs = [step.x for step in steps]
    ys = [step.y for step in steps]
    if xs[0] > xs[-1]:
        xs = xs[::-1]
        ys = ys[::-1]
    values: list[float] = []
    for target in targets:
        values.append(float(np.interp(target, xs, ys)))
    return values


# ---------------------------------------------------------------------------
# Step-size study
# ---------------------------------------------------------------------------


def reference_endpoint(ivp: IVP) -> float | None:
    """The exact (or high-accuracy reference) value of y at ``x_end``."""
    if ivp.exact is not None:
        value = _safe(ivp.exact, ivp.x_end)
        if value is not None:
            return value
    try:
        from scipy.integrate import solve_ivp

        solution = solve_ivp(
            lambda t, state: [ivp.f(t, state[0])],
            [ivp.x0, ivp.x_end],
            [ivp.y0],
            rtol=1e-11,
            atol=1e-13,
        )
    except Exception:
        return None
    if not solution.success or solution.y.shape[1] == 0:
        return None
    value = float(solution.y[0, -1])
    return value if math.isfinite(value) else None


@dataclass
class Study:
    """The outcome of the optional step-size study."""

    table: DataTable | None = None
    orders: DataTable | None = None
    hs: list[float] = field(default_factory=list)
    errors: list[float] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


def step_size_study(ivp: IVP, stepper: Stepper, decimals: int) -> Study:
    """Compare h, h/2 and h/4 and estimate the observed order of accuracy."""
    reference = reference_endpoint(ivp)
    if reference is None:
        return Study(notices=["The step-size study needs an exact or reference value at x_end."])

    rows: list[list[Any]] = []
    errors: list[float] = []
    hs: list[float] = []
    for factor in (1, 2, 4):
        n = ivp.n * factor
        h = ivp.h / factor
        steps, diverged = run_fixed_steps(ivp, stepper, n=n, h=h)
        if diverged is not None or not steps:
            return Study(notices=["The step-size study stopped because the solution diverged."])
        y_end = steps[-1].y
        error = abs(y_end - reference)
        label = "h" if factor == 1 else rf"h/{factor}"
        rows.append(
            [label, format_num(h, decimals), format_num(y_end, decimals), format_num(error, decimals)]
        )
        errors.append(error)
        hs.append(h)

    order_rows: list[list[Any]] = []
    for i in range(1, len(errors)):
        if errors[i - 1] > 0.0 and errors[i] > 0.0:
            order = math.log(errors[i - 1] / errors[i]) / math.log(2.0)
            order_rows.append([f"h vs h/{2**i}", format_num(order, max(decimals, 3))])

    study = DataTable(
        title="Step-size study",
        columns=["Step", "h", "y(x_end)", "|error at x_end|"],
        rows=rows,
    )
    orders = (
        DataTable(title="Observed order of accuracy", columns=["Comparison", "p"], rows=order_rows)
        if order_rows
        else None
    )
    return Study(table=study, orders=orders, hs=hs, errors=errors)


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------


def _slope_segments_trace(steps: list[IVPStep], f: OdeFunction, h: float) -> dict[str, Any]:
    xs: list[float | None] = []
    ys: list[float | None] = []
    dx = 0.35 * abs(h)
    for step in steps:
        try:
            slope = float(f(step.x, step.y))
        except Exception:
            continue
        if not math.isfinite(slope):
            continue
        xs.extend([step.x - dx, step.x + dx, None])
        ys.extend([step.y - dx * slope, step.y + dx * slope, None])
    return {
        "type": "scatter",
        "mode": "lines",
        "name": "slope segments",
        "x": xs,
        "y": ys,
        "line": {"color": "#94a3b8", "width": 1},
        "hoverinfo": "skip",
    }


def ivp_plot(
    ivp: IVP,
    steps: list[IVPStep],
    *,
    title: str,
    slope_segments: bool = False,
    study: tuple[list[float], list[float]] | None = None,
) -> PlotPayload:
    """The numerical solution versus the exact curve (plus an optional study)."""
    xs = [step.x for step in steps]
    ys = [step.y for step in steps]

    traces: list[dict[str, Any]] = [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Numerical y",
            "x": xs,
            "y": ys,
            "marker": {"size": 6, "color": "#2563eb"},
            "line": {"color": "#2563eb"},
            "xaxis": "x",
            "yaxis": "y",
        }
    ]
    if ivp.exact is not None:
        grid = np.linspace(ivp.x0, ivp.x_end, 400)
        exact_y = [ivp.exact(float(x)) if ivp.exact is not None else float("nan") for x in grid]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": "Exact y(x)",
                "x": grid.tolist(),
                "y": exact_y,
                "line": {"color": "#16a34a", "dash": "dash"},
                "xaxis": "x",
                "yaxis": "y",
            }
        )
    if slope_segments:
        trace = _slope_segments_trace(steps, ivp.f, ivp.h)
        trace["xaxis"] = "x"
        trace["yaxis"] = "y"
        traces.append(trace)

    layout: dict[str, Any] = {
        "title": {"text": title},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"title": {"text": "y"}},
    }

    if study is not None and study[0]:
        hs, errors = study
        layout = {
            "title": {"text": title + " — and error vs step"},
            "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
            "xaxis": {"title": {"text": "x"}, "domain": [0.0, 0.44]},
            "yaxis": {"title": {"text": "y"}, "domain": [0.0, 1.0]},
            "xaxis2": {
                "title": {"text": "step |h|"},
                "domain": [0.56, 1.0],
                "anchor": "y2",
                "type": "log",
            },
            "yaxis2": {"title": {"text": "|error at x_end|"}, "type": "log", "anchor": "x2"},
            "legend": {"orientation": "h", "y": -0.18},
        }
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": "error vs h",
                "x": [abs(value) for value in hs],
                "y": [max(value, 1e-16) for value in errors],
                "xaxis": "x2",
                "yaxis": "y2",
                "line": {"color": "#dc2626"},
            }
        )

    return PlotPayload(traces=traces, layout=layout)


# ---------------------------------------------------------------------------
# Shared steps
# ---------------------------------------------------------------------------


def setup_step(ivp: IVP, method_title: str) -> Step:
    direction = "forward" if ivp.h > 0 else "backward"
    return Step(
        title="Set up",
        latex=(
            rf"{method_title}:\quad y' = f(x, y),\qquad y({format_num(ivp.x0, ivp.decimals)}) = "
            rf"{format_num(ivp.y0, ivp.decimals)}"
            rf"\\[1mm] x_0 = {format_num(ivp.x0, ivp.decimals)},\quad "
            rf"x_{{end}} = {format_num(ivp.x_end, ivp.decimals)},\quad "
            rf"h = {format_num(ivp.h, ivp.decimals)},\quad n = {ivp.n}"
        ),
        note=f"{direction.capitalize()} march with {ivp.n} equal steps of size {format_num(ivp.h, ivp.decimals)}.",
    )


def result_step(ivp: IVP, y_end: float, exact_end: float | None, abs_error: float | None) -> Step:
    latex = rf"y({format_num(ivp.x_end, ivp.decimals)}) \approx {format_num(y_end, ivp.decimals)}"
    if exact_end is not None:
        latex += rf",\qquad y_{{exact}} = {format_num(exact_end, ivp.decimals)}"
    if abs_error is not None:
        latex += rf",\qquad |\text{{error}}| = {format_num(abs_error, ivp.decimals)}"
    return Step(title="Result", latex=latex, note="After the final step.")


# ---------------------------------------------------------------------------
# Common early responses
# ---------------------------------------------------------------------------


def degenerate_response(method_id: str, ivp: IVP) -> SolveResponse:
    step = Step(
        title="Zero-length interval",
        latex=(
            rf"x_0 = x_{{end}} = {format_num(ivp.x0, ivp.decimals)} \;\Rightarrow\; "
            rf"y({format_num(ivp.x_end, ivp.decimals)}) = {format_num(ivp.y0, ivp.decimals)}"
        ),
        note="No integration steps are needed; the solution is the initial value.",
    )
    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result={
            "x0": ivp.x0,
            "y0": ivp.y0,
            "x_end": ivp.x_end,
            "y_end": ivp.y0,
            "steps": 0,
            "h": 0.0,
            "exact_value": ivp.y0,
            "absolute_error": 0.0,
            "relative_error_percent": None,
        },
        steps=[step],
        tables=[summary_table(ivp, ivp.y0, ivp.y0, 0.0, None, ivp.decimals)],
        plot=PlotPayload(),
        errors=ErrorInfo(absolute=0.0),
        warnings=ivp.notices or ["x0 = x_end, so the solution is the initial value."],
    )


def divergence_response(
    method_id: str,
    ivp: IVP,
    steps: list[IVPStep],
    step_index: int,
) -> SolveResponse:
    bad = ivp.x0 + step_index * ivp.h
    message = (
        f"The solution diverged at step {step_index} "
        f"(x = {format_num(bad, ivp.decimals)}): |y| left the finite range of the "
        "method. The step size is too large for this problem — reduce h."
    )
    return SolveResponse(
        method=method_id,
        status=SolveStatus.DIVERGED,
        result={
            "x0": ivp.x0,
            "y0": ivp.y0,
            "x_end": ivp.x_end,
            "diverged_at_step": step_index,
            "diverged_at_x": bad,
            "steps_completed": len(steps) - 1,
        },
        steps=[
            Step(
                title="Divergence",
                latex=rf"y \to \pm\infty \ \text{{near}}\ x = {format_num(bad, ivp.decimals)}",
                note="The numerical solution left the finite range of the method.",
            )
        ],
        tables=[solution_table(steps, ivp.decimals)],
        plot=ivp_plot(ivp, steps, title="Diverged solution"),
        warnings=[message, *ivp.notices],
    )


def sample_exact(ivp: IVP, x: float) -> float | None:
    """Exact value at ``x`` for the table, guarded against domain errors."""
    if ivp.exact is None:
        return None
    return _safe(ivp.exact, x)


# ``failed_response`` is re-exported so the solver modules import it from here.
__all__ = [
    "IVP",
    "MAX_STEPS",
    "MAX_SYMBOLIC_OPS",
    "IVPStep",
    "Study",
    "compare_field",
    "degenerate_response",
    "divergence_response",
    "failed_response",
    "interpolate_targets",
    "ivp_plot",
    "ivp_schema",
    "prepare_ivp",
    "reference_endpoint",
    "reference_sampler",
    "result_step",
    "run_fixed_steps",
    "sample_exact",
    "setup_step",
    "solution_table",
    "stage_table",
    "step_size_study",
    "summary_table",
    "targets_table",
]
