"""Shared vector engine for the Chapter 5 system-of-ODEs solvers.

Private module (leading underscore) so the auto-loader skips it. It parses a
system ``dY/dx = F(x, Y)`` (2-4 equations), provides the Euler / two-stage /
four-stage *vector* steppers, the fixed-step driver, the solution and stage
tables, the exam-style working, the per-variable and phase / 3-D plots, the
max-norm step-size study and the RK2-vs-RK4 comparison. The second-order solver
builds a :class:`SystemIVP` and reuses :func:`solve_system`, so no integration
logic is duplicated.
"""

from __future__ import annotations

import math
import re
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
    format_num,
    number_field,
    precision_field,
)
from app.solvers.ch3_interpolation._interp import targets_field
from app.solvers.ch5_ode._ivp import (
    DIVERGENCE_BOUND,
    MAX_STEPS,
)

ExactFunction = Callable[[float], float]
Component = Callable[..., float]
VectorStepper = Callable[[float, list[float], float], "tuple[list[float], dict[str, Any]]"]

MIN_STATE_VARS = 2
MAX_STATE_VARS = 4
MAX_WORKING_STEPS = 6

_SYMBOL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
# Optional derivative label: "dy/dx =" or "y' =" (with unicode prime variants).
_DERIV_PREFIX_RE = re.compile(
    r"^\s*(?:d\s*[A-Za-z][A-Za-z0-9]*\s*/\s*d\s*[A-Za-z][A-Za-z0-9]*"
    r"|[A-Za-z][A-Za-z0-9]*\s*['\u2032\u2019])\s*=\s*"
)

_SCHEMES: dict[str, str] = {
    "rk4": "RK4",
    "rk2_heun": "RK2 (Heun)",
    "rk2_midpoint": "RK2 (Midpoint)",
    "rk2_ralston": "RK2 (Ralston)",
}
_RK2_A2: dict[str, float] = {"rk2_heun": 0.5, "rk2_midpoint": 1.0, "rk2_ralston": 2.0 / 3.0}

_VAR_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#9333ea"]


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SystemIVP:
    """A validated vector initial value problem ``dY/dx = F(x, Y)``."""

    funcs: list[Component]
    exprs: list[sp.Expr]
    var_names: list[str]
    x_name: str
    x0: float
    y0: list[float]
    x_end: float
    h: float
    n: int
    decimals: int
    exact_funcs: list[ExactFunction | None]
    targets: list[float]
    notices: list[str] = field(default_factory=list)


@dataclass
class SystemStep:
    """One stored step of a numerical vector solution."""

    k: int
    x: float
    y: list[float]
    exact: list[float | None] | None = None
    errors: list[float | None] | None = None
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsing / validation
# ---------------------------------------------------------------------------


def _split_equations(text: str) -> list[str]:
    entries = [part.strip() for part in re.split(r"[;\n]+", text) if part.strip()]
    if not entries:
        raise InvalidInputError(
            "Enter at least one differential equation.",
            hint="Write one equation per line, e.g. y' = z and z' = -y.",
        )
    return [_DERIV_PREFIX_RE.sub("", item, count=1) for item in entries]


def _state_names(text: str) -> list[str]:
    names: list[str] = []
    for part in re.split(r"[,\s]+", text.strip()):
        if not part:
            continue
        if not _SYMBOL_RE.match(part):
            raise InvalidInputError(
                f"'{part}' is not a valid variable name.",
                hint="Use letters and digits only, e.g. y, z, w.",
            )
        if part not in names:
            names.append(part)
    if not MIN_STATE_VARS <= len(names) <= MAX_STATE_VARS:
        raise InvalidInputError(
            f"Declare between {MIN_STATE_VARS} and {MAX_STATE_VARS} state variables "
            f"(got {len(names)}).",
        )
    return names


def parse_system_equations(text: str, x_name: str, var_names: list[str]) -> list[sp.Expr]:
    """Parse the right-hand sides, validating against the declared variables."""
    entries = _split_equations(text)
    if len(entries) != len(var_names):
        raise InvalidInputError(
            f"Expected {len(var_names)} equation(s) for {', '.join(var_names)} "
            f"but found {len(entries)}.",
            hint="Write one equation per line (or separate them with ';').",
        )
    variables = (x_name, *var_names)
    exprs: list[sp.Expr] = []
    for entry in entries:
        if "=" in entry and entry.count("=") > 1:
            raise InvalidInputError(
                f"'{entry}' contains more than one '='.",
                hint="Write each right-hand side once, e.g. z' = -y.",
            )
        exprs.append(parse_expression(entry, variables))
    return exprs


def resolve_grid(inputs: dict[str, Any]) -> tuple[float, float, float, int, list[str]]:
    x0 = float(inputs.get("x0", 0.0))
    x_end = float(inputs.get("x_end", 1.0))
    notices: list[str] = []
    if x0 == x_end:
        return x0, x_end, 0.0, 0, notices
    direction = 1.0 if x_end > x0 else -1.0
    if str(inputs.get("step_mode", "step")) == "steps":
        n = int(inputs.get("n", 10))
        if n < 1 or n > MAX_STEPS:
            raise InvalidInputError(
                f"The number of steps must be between 1 and {MAX_STEPS}.",
            )
        h = (x_end - x0) / n
    else:
        h_input = float(inputs.get("h", 0.1))
        if h_input == 0.0:
            raise InvalidInputError(
                "The step size h must be non-zero.",
                hint="Use a positive h for a forward march, or a negative h to go backward.",
            )
        if math.copysign(1.0, h_input) != direction:
            notices.append("The sign of h was reversed so the march runs from x0 towards x_end.")
        n = round(abs(x_end - x0) / abs(h_input))
        if n < 1:
            raise InvalidInputError(
                "The step size h is larger than the interval |x_end - x0|.",
                hint="Choose a smaller h or use the number-of-steps mode.",
            )
        h = direction * (abs(x_end - x0) / n)
        if n > MAX_STEPS:
            raise InvalidInputError(
                f"The step size needs more than {MAX_STEPS} steps.",
            )
    if direction < 0:
        notices.append(
            "Backward integration: x_end < x0, so the method marches in the negative x "
            "direction with h < 0."
        )
    return x0, x_end, h, n, notices


def _exact_functions(
    text: str | None, x_name: str, var_names: list[str], decimals: int
) -> list[ExactFunction | None]:
    if not text or not text.strip():
        return [None] * len(var_names)
    entries = [part.strip() for part in re.split(r"[;\n]+", text) if part.strip()]
    funcs: list[ExactFunction | None] = []
    for index in range(len(var_names)):
        if index < len(entries):
            expr = parse_expression(entries[index], (x_name,))
            funcs.append(make_function(expr, (x_name,), strict=False))
        else:
            funcs.append(None)
    return funcs


def prepare_system(
    inputs: dict[str, Any], method_id: str
) -> SystemIVP | SolveResponse:
    """Parse and validate the shared system-ODE inputs."""
    del method_id
    x_name = str(inputs.get("independent_variable") or "x").strip()
    if not _SYMBOL_RE.match(x_name):
        raise InvalidInputError(
            f"'{x_name}' is not a valid independent-variable name.",
        )
    var_names = _state_names(str(inputs.get("state_variables") or "y, z"))
    if x_name in var_names:
        raise InvalidInputError(
            f"The independent variable '{x_name}' cannot also be a state variable.",
        )

    equations = str(inputs.get("equations") or "")
    if not equations.strip():
        raise InvalidInputError("The system of equations is required.")
    exprs = parse_system_equations(equations, x_name, var_names)
    funcs = [make_function(expr, (x_name, *var_names), strict=False) for expr in exprs]

    raw_y0 = inputs.get("y0")
    if not isinstance(raw_y0, list):
        raise InvalidInputError("The initial vector Y(x0) must be a list of numbers.")
    y0 = [float(value) for value in raw_y0]
    if len(y0) != len(var_names):
        raise InvalidInputError(
            f"Y(x0) needs one value per state variable (+{len(var_names)}), got {len(y0)}.",
        )

    x0, x_end, h, n, notices = resolve_grid(inputs)
    decimals = int(inputs.get("decimal_precision", 6))
    exact_funcs = _exact_functions(inputs.get("exact_solutions"), x_name, var_names, decimals)
    targets = [] if inputs.get("targets") is None else [float(v) for v in inputs["targets"]]

    return SystemIVP(
        funcs=funcs,
        exprs=exprs,
        var_names=var_names,
        x_name=x_name,
        x0=x0,
        y0=y0,
        x_end=x_end,
        h=h,
        n=n,
        decimals=decimals,
        exact_funcs=exact_funcs,
        targets=targets,
        notices=notices,
    )


def system_schema(*extra: InputField, default_h: float = 0.1) -> list[InputField]:
    """The shared input form for a system of first-order ODEs."""
    return [
        InputField(
            key="equations",
            label="Equations dY/dx = F(x, Y) (one per line)",
            type="text",
            required=True,
            rows=4,
            placeholder="y' = z\nz' = -y",
            help=(
                "Write each right-hand side on its own line (or separate with ';'). "
                "Optional 'y'' or 'dy/dx =' prefixes are accepted."
            ),
        ),
        InputField(
            key="independent_variable",
            label="Independent variable",
            type="text",
            required=True,
            default="x",
            placeholder="x",
            help="The variable the derivatives are taken with respect to.",
        ),
        InputField(
            key="state_variables",
            label="State variables",
            type="text",
            required=True,
            default="y, z",
            placeholder="y, z, w, v",
            help="2 to 4 names, one per equation, in that order.",
        ),
        InputField(
            key="y0",
            label="Initial values Y(x0)",
            type="vector",
            required=True,
            default="0, 1",
            placeholder="0, 1",
            help="One starting value per state variable, in the same order.",
        ),
        number_field("x0", "Initial x0", 0.0),
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
        ),
        number_field("h", "Step size h", default_h, required=False),
        InputField(
            key="n",
            label="Number of steps n",
            type="integer",
            required=True,
            default=10,
            min=1,
            max=MAX_STEPS,
        ),
        InputField(
            key="exact_solutions",
            label="Exact solutions (optional, one per line)",
            type="text",
            required=False,
            rows=2,
            placeholder="cos(x)\n-sin(x)",
            help="One exact y_i(x) per state variable, in order, for error columns.",
        ),
        targets_field(required=False, label="Target x values (optional)"),
        boolean_field("step_study", "Step-size study (h, h/2, h/4)", False),
        *extra,
        precision_field(),
    ]


def scheme_field() -> InputField:
    """The RK4 / RK2-variant selector shared by the system solvers."""
    return InputField(
        key="scheme",
        label="Scheme",
        type="select",
        required=True,
        default="rk4",
        options=[
            SelectOption(value="rk4", label="RK4 (classic)"),
            SelectOption(value="rk2_heun", label="RK2 — Heun"),
            SelectOption(value="rk2_midpoint", label="RK2 — Midpoint"),
            SelectOption(value="rk2_ralston", label="RK2 — Ralston"),
        ],
        help="Fourth-order RK is the default; the second-order pairs are cheaper.",
    )


def compare_field() -> InputField:
    return boolean_field(
        "compare",
        "Compare RK2 vs RK4 (and Euler)",
        False,
        help="Overlay the schemes and report the max-norm error at x_end.",
    )


# ---------------------------------------------------------------------------
# Vector steppers
# ---------------------------------------------------------------------------


def _rhs(ivp: SystemIVP, x: float, state: list[float]) -> list[float]:
    return [float(func(x, *state)) for func in ivp.funcs]


def euler_vector(ivp: SystemIVP) -> VectorStepper:
    def step(x: float, state: list[float], h: float) -> tuple[list[float], dict[str, Any]]:
        k1 = _rhs(ivp, x, state)
        y_next = [yi + h * ki for yi, ki in zip(state, k1, strict=True)]
        return y_next, {"k1": k1, "k1_x": x, "k1_s": list(state)}

    return step


def rk2_vector(ivp: SystemIVP, a2: float) -> VectorStepper:
    c2 = 1.0 / (2.0 * a2)

    def step(x: float, state: list[float], h: float) -> tuple[list[float], dict[str, Any]]:
        k1 = _rhs(ivp, x, state)
        arg2 = [yi + c2 * h * k1i for yi, k1i in zip(state, k1, strict=True)]
        k2 = _rhs(ivp, x + c2 * h, arg2)
        y_next = [
            yi + h * ((1.0 - a2) * k1i + a2 * k2i)
            for yi, k1i, k2i in zip(state, k1, k2, strict=True)
        ]
        return y_next, {
            "k1": k1,
            "k1_x": x,
            "k1_s": list(state),
            "k2": k2,
            "k2_x": x + c2 * h,
            "k2_s": arg2,
        }

    return step


def rk4_vector(ivp: SystemIVP) -> VectorStepper:
    def step(x: float, state: list[float], h: float) -> tuple[list[float], dict[str, Any]]:
        k1 = _rhs(ivp, x, state)
        arg2 = [yi + h / 2.0 * k1i for yi, k1i in zip(state, k1, strict=True)]
        k2 = _rhs(ivp, x + h / 2.0, arg2)
        arg3 = [yi + h / 2.0 * k2i for yi, k2i in zip(state, k2, strict=True)]
        k3 = _rhs(ivp, x + h / 2.0, arg3)
        arg4 = [yi + h * k3i for yi, k3i in zip(state, k3, strict=True)]
        k4 = _rhs(ivp, x + h, arg4)
        y_next = [
            yi + h / 6.0 * (k1i + 2.0 * k2i + 2.0 * k3i + k4i)
            for yi, k1i, k2i, k3i, k4i in zip(state, k1, k2, k3, k4, strict=True)
        ]
        return y_next, {
            "k1": k1,
            "k1_x": x,
            "k1_s": list(state),
            "k2": k2,
            "k2_x": x + h / 2.0,
            "k2_s": arg2,
            "k3": k3,
            "k3_x": x + h / 2.0,
            "k3_s": arg3,
            "k4": k4,
            "k4_x": x + h,
            "k4_s": arg4,
        }

    return step


def stepper_for(scheme: str, ivp: SystemIVP) -> VectorStepper:
    if scheme == "rk4":
        return rk4_vector(ivp)
    if scheme in _RK2_A2:
        return rk2_vector(ivp, _RK2_A2[scheme])
    raise InvalidInputError(f"Unknown scheme '{scheme}'.")


# ---------------------------------------------------------------------------
# Fixed-step driver
# ---------------------------------------------------------------------------


def _safe_value(func: ExactFunction, x: float) -> float | None:
    try:
        value = float(func(x))
    except Exception:
        return None
    return value if math.isfinite(value) else None


def _exact_at(ivp: SystemIVP, x: float) -> list[float | None] | None:
    if all(func is None for func in ivp.exact_funcs):
        return None
    return [None if func is None else _safe_value(func, x) for func in ivp.exact_funcs]


def _errors(state: list[float], exact: list[float | None] | None) -> list[float | None] | None:
    if exact is None:
        return None
    return [
        None if e is None else abs(y - e) for y, e in zip(state, exact, strict=True)
    ]


def _max_error(errors: list[float | None] | None) -> float | None:
    if errors is None:
        return None
    values = [value for value in errors if value is not None]
    return max(values) if values else None


def run_system(
    ivp: SystemIVP,
    stepper: VectorStepper,
    *,
    n: int | None = None,
    h: float | None = None,
) -> tuple[list[SystemStep], int | None]:
    steps: list[SystemStep] = []
    x, state = ivp.x0, list(ivp.y0)
    exact0 = _exact_at(ivp, x)
    steps.append(SystemStep(0, x, list(state), exact0, _errors(state, exact0), {}))
    total = ivp.n if n is None else n
    step_h = ivp.h if h is None else h
    for k in range(total):
        y_next, data = stepper(x, state, step_h)
        x_next = x + step_h
        finite = math.isfinite(x_next) and all(math.isfinite(value) for value in y_next)
        if not finite or max((abs(value) for value in y_next), default=0.0) > DIVERGENCE_BOUND:
            return steps, k + 1
        exact = _exact_at(ivp, x_next)
        steps.append(SystemStep(k + 1, x_next, y_next, exact, _errors(y_next, exact), data))
        x, state = x_next, y_next
    return steps, None


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def solution_table_system(ivp: SystemIVP, steps: list[SystemStep]) -> DataTable:
    has_exact = any(
        value is not None for step in steps for value in (step.exact or [])
    )
    columns = ["step", ivp.x_name, *ivp.var_names]
    if has_exact:
        columns += [f"{name} exact" for name in ivp.var_names]
        columns += [f"|e| {name}" for name in ivp.var_names]
    rows: list[list[Any]] = []
    for step in steps:
        row: list[Any] = [step.k, format_num(step.x, ivp.decimals)]
        row += [format_num(value, ivp.decimals) for value in step.y]
        if has_exact:
            exact = step.exact or [None] * len(ivp.var_names)
            errors = step.errors or [None] * len(ivp.var_names)
            row += [
                format_num(value, ivp.decimals) if value is not None else "n/a" for value in exact
            ]
            row += [
                format_num(value, ivp.decimals) if value is not None else "n/a" for value in errors
            ]
        rows.append(row)
    return DataTable(title="Numerical solution", columns=columns, rows=rows)


def stage_table(ivp: SystemIVP, steps: list[SystemStep], scheme: str) -> DataTable:
    if scheme == "rk4":
        labels = ["k1", "k2", "k3", "k4"]
    elif scheme.startswith("rk2"):
        labels = ["k1", "k2"]
    else:
        labels = ["k1"]
    columns = ["step", ivp.x_name, *labels]
    rows: list[list[Any]] = []
    for step in steps:
        row: list[Any] = [step.k, format_num(step.x, ivp.decimals)]
        for label in labels:
            vector = step.data.get(label)
            if vector is None:
                row.append(r"\text{--}")
            else:
                body = ", ".join(format_num(value, ivp.decimals) for value in vector)
                row.append(f"({body})")
        rows.append(row)
    return DataTable(title="Runge-Kutta stage vectors", columns=columns, rows=rows)


def summary_table_system(
    ivp: SystemIVP, y_end: list[float], max_error: float | None
) -> DataTable:
    rows: list[list[Any]] = []
    for name, value in zip(ivp.var_names, y_end, strict=True):
        rows.append([name, format_num(value, ivp.decimals)])
    if max_error is not None:
        rows.append(["Max |error|", format_num(max_error, ivp.decimals)])
    return DataTable(title="Final values", columns=["Quantity", "Value"], rows=rows)


def targets_table_system(
    ivp: SystemIVP, values: list[list[float]]
) -> DataTable:
    columns = ["Target x", *ivp.var_names]
    rows: list[list[Any]] = []
    for target, vector in zip(ivp.targets, values, strict=True):
        row: list[Any] = [format_num(target, ivp.decimals)]
        row += [format_num(value, ivp.decimals) for value in vector]
        rows.append(row)
    return DataTable(title="Values at the target x", columns=columns, rows=rows)


# ---------------------------------------------------------------------------
# Working steps
# ---------------------------------------------------------------------------


def vec_latex(values: list[float], decimals: int) -> str:
    body = r" \\ ".join(format_num(value, decimals) for value in values)
    return rf"\begin{{bmatrix}} {body} \end{{bmatrix}}"


def working_steps(ivp: SystemIVP, steps: list[SystemStep], scheme: str) -> list[Step]:
    labels = ["k1", "k2", "k3", "k4"] if scheme == "rk4" else (
        ["k1", "k2"] if scheme.startswith("rk2") else ["k1"]
    )
    output: list[Step] = []
    for step in steps[1 : MAX_WORKING_STEPS + 1]:
        previous = steps[step.k - 1]
        lines: list[str] = []
        for index, label in enumerate(labels, start=1):
            vector = step.data.get(f"k{index}")
            if vector is None:
                continue
            arg_x = step.data.get(f"k{index}_x")
            arg_s = step.data.get(f"k{index}_s")
            arg_x_latex = format_num(float(arg_x), ivp.decimals) if arg_x is not None else "?"
            arg_s_latex = (
                vec_latex([float(v) for v in arg_s], ivp.decimals) if arg_s is not None else "?"
            )
            lines.append(
                rf"{label} = f\!\left({arg_x_latex},\; {arg_s_latex}\right) = "
                rf"{vec_latex([float(v) for v in vector], ivp.decimals)}"
            )
        y_n = vec_latex(previous.y, ivp.decimals)
        if scheme == "rk4":
            update = (
                rf"Y_{{{step.k}}} = Y_{{{step.k - 1}}} + \tfrac{{h}}{{6}}"
                rf"\left(k_1 + 2k_2 + 2k_3 + k_4\right) = {y_n} \rightarrow "
                rf"{vec_latex(step.y, ivp.decimals)}"
            )
        elif scheme.startswith("rk2"):
            a2 = _RK2_A2[scheme]
            update = (
                rf"Y_{{{step.k}}} = Y_{{{step.k - 1}}} + h\left[{format_num(1 - a2, 4)}k_1 + "
                rf"{format_num(a2, 4)}k_2\right] = {y_n} \rightarrow "
                rf"{vec_latex(step.y, ivp.decimals)}"
            )
        else:
            update = (
                rf"Y_{{{step.k}}} = Y_{{{step.k - 1}}} + h\,k_1 = {y_n} \rightarrow "
                rf"{vec_latex(step.y, ivp.decimals)}"
            )
        output.append(
            Step(
                title=f"Step {step.k}",
                latex=r"\\[1mm]".join([*lines, update, rf"x_{{{step.k}}} = {format_num(step.x, ivp.decimals)}"]),
            )
        )
    if len(steps) - 1 > MAX_WORKING_STEPS:
        output.append(
            Step(
                title="Remaining steps",
                note=(
                    f"The remaining {len(steps) - 1 - MAX_WORKING_STEPS} steps follow the "
                    "same pattern; every step is listed in the table."
                ),
            )
        )
    return output


# ---------------------------------------------------------------------------
# Reference / step-size study
# ---------------------------------------------------------------------------


def system_reference(ivp: SystemIVP) -> Callable[[float], list[float | None]] | None:
    exact_funcs = [func for func in ivp.exact_funcs if func is not None]
    if len(exact_funcs) == len(ivp.var_names):
        return lambda x: [_safe_value(func, x) for func in exact_funcs]
    try:
        from scipy.integrate import solve_ivp

        solution = solve_ivp(
            lambda t, state: _rhs(ivp, t, list(state)),
            [ivp.x0, ivp.x_end],
            ivp.y0,
            rtol=1e-11,
            atol=1e-13,
            dense_output=True,
        )
    except Exception:
        return None
    if not solution.success:
        return None

    def sample(x: float) -> list[float | None]:
        try:
            values = solution.sol(x)
        except Exception:
            return [None] * len(ivp.var_names)
        return [float(value) if math.isfinite(float(value)) else None for value in values]

    return sample


def step_size_study_system(
    ivp: SystemIVP, stepper: VectorStepper
) -> tuple[DataTable | None, DataTable | None, list[float], list[float], list[str]]:
    reference = system_reference(ivp)
    if reference is None:
        return None, None, [], [], [
            "The step-size study needs exact solutions or a reference solution at x_end."
        ]
    ref_end = reference(ivp.x_end)
    if any(value is None for value in ref_end):
        return None, None, [], [], ["The reference solution is unavailable at x_end."]
    rows: list[list[Any]] = []
    errors: list[float] = []
    hs: list[float] = []
    for factor in (1, 2, 4):
        steps, diverged = run_system(ivp, stepper, n=ivp.n * factor, h=ivp.h / factor)
        if diverged is not None or not steps:
            return None, None, [], [], ["The step-size study stopped because the solution diverged."]
        y_end = steps[-1].y
        error = max(
            abs(y - ref) for y, ref in zip(y_end, ref_end, strict=True) if ref is not None
        )
        label = "h" if factor == 1 else f"h/{factor}"
        rows.append(
            [label, format_num(ivp.h / factor, ivp.decimals), format_num(error, ivp.decimals)]
        )
        errors.append(error)
        hs.append(ivp.h / factor)
    order_rows: list[list[Any]] = []
    for i in range(1, len(errors)):
        if errors[i - 1] > 0.0 and errors[i] > 0.0:
            order = math.log(errors[i - 1] / errors[i]) / math.log(2.0)
            order_rows.append([f"h vs h/{2**i}", format_num(order, max(ivp.decimals, 3))])
    study = DataTable(
        title="Step-size study",
        columns=["Step", "h", "|error at x_end| (max-norm)"],
        rows=rows,
    )
    orders = (
        DataTable(title="Observed order of accuracy", columns=["Comparison", "p"], rows=order_rows)
        if order_rows
        else None
    )
    return study, orders, hs, errors, []


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def _phase_arrows(steps: list[SystemStep]) -> list[dict[str, Any]]:
    annotations: list[dict[str, Any]] = []
    n = len(steps)
    if n < 3:
        return annotations
    indices = sorted({max(1, round(n * frac)) for frac in (0.25, 0.5, 0.75)})
    for index in indices:
        if index >= n:
            continue
        prev = steps[index - 1]
        point = steps[index]
        annotations.append(
            {
                "x": point.y[1],
                "y": point.y[0],
                "ax": prev.y[1],
                "ay": prev.y[0],
                "xref": "x2",
                "yref": "y2",
                "axref": "x2",
                "ayref": "y2",
                "showarrow": True,
                "arrowhead": 3,
                "arrowsize": 1.4,
                "arrowwidth": 1.5,
                "arrowcolor": "#7c3aed",
                "text": "",
            }
        )
    return annotations


def system_plot(
    ivp: SystemIVP,
    steps: list[SystemStep],
    *,
    title: str,
    study: tuple[list[float], list[float]] | None = None,
) -> PlotPayload:
    xs = [step.x for step in steps]
    traces: list[dict[str, Any]] = []
    for index, name in enumerate(ivp.var_names):
        color = _VAR_COLORS[index % len(_VAR_COLORS)]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": name,
                "x": xs,
                "y": [step.y[index] for step in steps],
                "marker": {"size": 5, "color": color},
                "line": {"color": color},
                "xaxis": "x",
                "yaxis": "y",
            }
        )
        func = ivp.exact_funcs[index]
        if func is not None:
            grid = np.linspace(ivp.x0, ivp.x_end, 200)
            traces.append(
                {
                    "type": "scatter",
                    "mode": "lines",
                    "name": f"exact {name}",
                    "x": grid.tolist(),
                    "y": [_safe_value(func, float(x)) for x in grid],
                    "line": {"color": color, "dash": "dot"},
                    "xaxis": "x",
                    "yaxis": "y",
                }
            )

    n_vars = len(ivp.var_names)
    if study is not None and study[0]:
        hs, errors = study
        layout: dict[str, Any] = {
            "title": {"text": title + " — and error vs step"},
            "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
            "xaxis": {"title": {"text": ivp.x_name}, "domain": [0.0, 0.44]},
            "yaxis": {"title": {"text": "value"}, "domain": [0.0, 1.0]},
            "xaxis2": {
                "title": {"text": "step |h|"},
                "domain": [0.56, 1.0],
                "anchor": "y2",
                "type": "log",
            },
            "yaxis2": {"title": {"text": "|error at x_end|"}, "type": "log", "anchor": "x2"},
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

    if n_vars == 2:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": f"phase {ivp.var_names[0]}-{ivp.var_names[1]}",
                "x": [step.y[1] for step in steps],
                "y": [step.y[0] for step in steps],
                "marker": {"size": 5, "color": "#7c3aed"},
                "line": {"color": "#7c3aed"},
                "xaxis": "x2",
                "yaxis": "y2",
            }
        )
        layout = {
            "title": {"text": title},
            "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
            "xaxis": {"title": {"text": ivp.x_name}, "domain": [0.0, 0.44]},
            "yaxis": {"title": {"text": "value"}, "domain": [0.0, 1.0]},
            "xaxis2": {
                "title": {"text": ivp.var_names[1]},
                "domain": [0.56, 1.0],
                "anchor": "y2",
            },
            "yaxis2": {"title": {"text": ivp.var_names[0]}, "anchor": "x2"},
            "annotations": _phase_arrows(steps),
        }
    elif n_vars == 3:
        traces.append(
            {
                "type": "scatter3d",
                "mode": "lines+markers",
                "name": "trajectory",
                "x": [step.y[0] for step in steps],
                "y": [step.y[1] for step in steps],
                "z": [step.y[2] for step in steps],
                "marker": {"size": 4, "color": "#7c3aed"},
                "line": {"color": "#7c3aed", "width": 4},
            }
        )
        layout = {
            "title": {"text": title},
            "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
            "xaxis": {"title": {"text": ivp.x_name}, "domain": [0.0, 0.44]},
            "yaxis": {"title": {"text": "value"}, "domain": [0.0, 1.0]},
            "scene": {
                "xaxis": {"title": {"text": ivp.var_names[0]}},
                "yaxis": {"title": {"text": ivp.var_names[1]}},
                "zaxis": {"title": {"text": ivp.var_names[2]}},
                "domain": {"x": [0.56, 1.0], "y": [0.0, 1.0]},
            },
        }
    else:
        layout = {
            "title": {"text": title},
            "xaxis": {"title": {"text": ivp.x_name}},
            "yaxis": {"title": {"text": "value"}},
        }
    return PlotPayload(traces=traces, layout=layout)


# ---------------------------------------------------------------------------
# Comparison (Euler vs RK2 vs RK4)
# ---------------------------------------------------------------------------


@dataclass
class SystemComparison:
    table: DataTable | None = None
    plot: PlotPayload | None = None
    notices: list[str] = field(default_factory=list)


def compare_system(ivp: SystemIVP, scheme: str) -> SystemComparison:
    reference = system_reference(ivp)
    if reference is None:
        return SystemComparison(notices=["The comparison needs a reference solution at x_end."])
    ref_end = reference(ivp.x_end)
    if any(value is None for value in ref_end):
        return SystemComparison(notices=["The reference solution is unavailable at x_end."])

    a2 = _RK2_A2.get(scheme, 0.5)
    rk2_label = _SCHEMES[scheme] if scheme.startswith("rk2") else "RK2 (Heun)"
    entries: list[tuple[str, VectorStepper, int]] = [
        ("Euler", euler_vector(ivp), 1),
        (rk2_label, rk2_vector(ivp, a2), 2),
        ("RK4", rk4_vector(ivp), 4),
    ]
    rows: list[list[Any]] = []
    error_traces: list[dict[str, Any]] = []
    first_traces: list[dict[str, Any]] = []
    for name, stepper, evals in entries:
        steps, diverged = run_system(ivp, stepper)
        if diverged is not None or not steps:
            rows.append([name, "diverged", evals * ivp.n])
            continue
        y_end = steps[-1].y
        error = max(abs(y - ref) for y, ref in zip(y_end, ref_end, strict=True) if ref is not None)
        rows.append([name, format_num(error, ivp.decimals), evals * ivp.n])
        err_x: list[float] = []
        err_y: list[float] = []
        for step in steps:
            ref = reference(step.x)
            values = [
                abs(y - r) for y, r in zip(step.y, ref, strict=True) if r is not None
            ]
            if values:
                err_x.append(step.x)
                err_y.append(max(max(values), 1e-16))
        error_traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": f"|error| {name}",
                "x": err_x,
                "y": err_y,
                "xaxis": "x2",
                "yaxis": "y2",
            }
        )
        first_traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": f"{ivp.var_names[0]} — {name}",
                "x": [step.x for step in steps],
                "y": [step.y[0] for step in steps],
                "xaxis": "x",
                "yaxis": "y",
            }
        )

    layout: dict[str, Any] = {
        "title": {"text": f"{ivp.var_names[0]} and max-norm error: Euler vs RK2 vs RK4"},
        "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
        "xaxis": {"title": {"text": ivp.x_name}, "domain": [0.0, 0.44]},
        "yaxis": {"title": {"text": ivp.var_names[0]}, "domain": [0.0, 1.0]},
        "xaxis2": {"title": {"text": ivp.x_name}, "domain": [0.56, 1.0], "anchor": "y2"},
        "yaxis2": {"title": {"text": "max |error|"}, "type": "log", "anchor": "x2"},
    }
    table = DataTable(
        title="Scheme comparison",
        columns=["Scheme", "max |error at x_end|", "Vector evaluations"],
        rows=rows,
    )
    return SystemComparison(
        table=table, plot=PlotPayload(traces=[*first_traces, *error_traces], layout=layout)
    )


# ---------------------------------------------------------------------------
# Response assembly
# ---------------------------------------------------------------------------


def degenerate_system_response(method_id: str, ivp: SystemIVP) -> SolveResponse:
    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result={
            "x0": ivp.x0,
            "x_end": ivp.x_end,
            "y_end": list(ivp.y0),
            "variables": ivp.var_names,
            "steps": 0,
            "h": 0.0,
            "max_absolute_error": 0.0,
        },
        steps=[
            Step(
                title="Zero-length interval",
                latex=(
                    rf"x_0 = x_{{end}} = {format_num(ivp.x0, ivp.decimals)} \;\Rightarrow\; "
                    rf"Y(x_0) = {vec_latex(ivp.y0, ivp.decimals)}"
                ),
            )
        ],
        tables=[solution_table_system(ivp, [SystemStep(0, ivp.x0, list(ivp.y0))])],
        warnings=ivp.notices or ["x0 = x_end, so the solution is the initial vector."],
    )


def divergence_system_response(
    method_id: str, ivp: SystemIVP, steps: list[SystemStep], step_index: int
) -> SolveResponse:
    bad = ivp.x0 + step_index * ivp.h
    return SolveResponse(
        method=method_id,
        status=SolveStatus.DIVERGED,
        result={
            "x0": ivp.x0,
            "x_end": ivp.x_end,
            "variables": ivp.var_names,
            "diverged_at_step": step_index,
            "diverged_at_x": bad,
        },
        steps=[
            Step(
                title="Divergence",
                latex=(
                    rf"\left\|Y\right\| \to \infty \ \text{{near}}\ x = "
                    rf"{format_num(bad, ivp.decimals)}"
                ),
                note="A component left the finite range of the method.",
            )
        ],
        tables=[solution_table_system(ivp, steps)],
        plot=system_plot(ivp, steps, title="Diverged solution"),
        warnings=[
            f"The solution diverged at step {step_index} "
            f"(x = {format_num(bad, ivp.decimals)}). Reduce the step size h.",
            *ivp.notices,
        ],
    )


def solve_system(
    ivp: SystemIVP,
    scheme: str,
    *,
    method_id: str,
    preamble: list[Step] | None = None,
    title: str | None = None,
    run_compare: bool = False,
    run_study: bool = False,
) -> SolveResponse:
    """Integrate a validated system with the chosen scheme and build the response."""
    if ivp.n == 0:
        return degenerate_system_response(method_id, ivp)
    scheme_label = _SCHEMES.get(scheme, scheme)
    stepper = stepper_for(scheme, ivp)
    notices = list(ivp.notices)
    steps, diverged = run_system(ivp, stepper)
    if diverged is not None:
        return divergence_system_response(method_id, ivp, steps, diverged)

    y_end = steps[-1].y
    max_error = _max_error(steps[-1].errors)
    tables = [solution_table_system(ivp, steps), stage_table(ivp, steps, scheme)]

    target_values: list[list[float]] = []
    if ivp.targets and len(steps) > 1:
        xs = [step.x for step in steps]
        reversed_order = xs[0] > xs[-1]
        for target in ivp.targets:
            vector: list[float] = []
            for index in range(len(ivp.var_names)):
                axis_x = xs[::-1] if reversed_order else xs
                axis_y = (
                    [step.y[index] for step in steps][::-1] if reversed_order
                    else [step.y[index] for step in steps]
                )
                vector.append(float(np.interp(target, axis_x, axis_y)))
            target_values.append(vector)
        tables.append(targets_table_system(ivp, target_values))

    study = None
    hs: list[float] = []
    errors: list[float] = []
    if run_study:
        study_table, orders, hs, errors, study_notices = step_size_study_system(ivp, stepper)
        notices.extend(study_notices)
        if study_table is not None:
            tables.append(study_table)
        if orders is not None:
            tables.append(orders)
        study = (hs, errors)

    compare = SystemComparison()
    if run_compare:
        compare = compare_system(ivp, scheme)
        notices.extend(compare.notices)
        if compare.table is not None:
            tables.append(compare.table)

    tables.append(summary_table_system(ivp, y_end, max_error))

    dx = f"d{ivp.x_name}"
    steps_out: list[Step] = [
        *(preamble or []),
        Step(
            title="Set up",
            latex=(
                rf"\frac{{dY}}{{{dx}}} = F({ivp.x_name}, Y),\qquad "
                rf"Y({format_num(ivp.x0, ivp.decimals)}) = "
                rf"{vec_latex(ivp.y0, ivp.decimals)}"
                rf"\\[1mm] x_0 = {format_num(ivp.x0, ivp.decimals)},\quad "
                rf"x_{{end}} = {format_num(ivp.x_end, ivp.decimals)},\quad "
                rf"h = {format_num(ivp.h, ivp.decimals)},\quad n = {ivp.n},\quad "
                rf"\text{{{scheme_label}}}"
            ),
        ),
        *working_steps(ivp, steps, scheme),
    ]
    if ivp.targets and target_values:
        lines = [
            rf"{vec_latex(vector, ivp.decimals)}\ \text{{at}}\ {ivp.x_name} = "
            rf"{format_num(target, ivp.decimals)}"
            for target, vector in zip(ivp.targets, target_values, strict=True)
        ]
        steps_out.append(Step(title="Target values", latex=r"\\[1mm]".join(lines)))
    steps_out.append(
        Step(
            title="Result",
            latex=(
                rf"Y({format_num(ivp.x_end, ivp.decimals)}) \approx "
                rf"{vec_latex(y_end, ivp.decimals)}"
                + (
                    rf",\qquad \max|e| = {format_num(max_error, ivp.decimals)}"
                    if max_error is not None
                    else ""
                )
            ),
        )
    )

    plot = system_plot(ivp, steps, title=title or f"{scheme_label} solution", study=study)
    if compare.plot is not None:
        plot = compare.plot

    result: dict[str, Any] = {
        "x0": ivp.x0,
        "x_end": ivp.x_end,
        "y_end": y_end,
        "variables": ivp.var_names,
        "steps": ivp.n,
        "h": ivp.h,
        "scheme": scheme_label,
        "exact_end": steps[-1].exact,
        "max_absolute_error": max_error,
        "target_values": target_values,
    }
    return SolveResponse(
        method=method_id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps_out,
        tables=tables,
        plot=plot,
        errors=ErrorInfo(absolute=max_error),
        warnings=notices,
    )
