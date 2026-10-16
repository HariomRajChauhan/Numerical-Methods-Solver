"""Bisection method — the reference solver template.

Solve ``f(x) = 0`` on a bracketing interval ``[a, b]`` where ``f(a)`` and
``f(b)`` have opposite signs. The interval is repeatedly halved; the midpoint
of the final bracket approximates the root. Convergence is guaranteed but slow
(linear), one binary digit per iteration.

This module shows the shape every solver follows:
- a :class:`MethodMeta` describing inputs, theory, formulas and pseudocode;
- a pure ``solve(inputs, limits) -> SolveResponse`` function;
- self-registration via the :func:`register` decorator.

Nothing outside this file (and its test file) knows the method exists.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.errors import InvalidInputError
from app.core.models import (
    Chapter,
    DataTable,
    ErrorInfo,
    InputField,
    LabeledLatex,
    MethodExample,
    MethodMeta,
    PlotPayload,
    SolveResponse,
    SolverLimits,
    SolveStatus,
    Step,
)
from app.core.parser import expr_to_latex, make_function, parse_expression
from app.core.registry import register
from app.solvers._common import line_trace, marker_trace, sample_curve

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _num(value: float) -> str:
    """Format a float for LaTeX, turning ``1.2e-07`` into ``1.2\\times10^{-7}``."""
    if value == 0:
        return "0"
    text = f"{value:.10g}"
    if "e" in text or "E" in text:
        mantissa, _, exponent = text.replace("E", "e").partition("e")
        return f"{mantissa}\\times 10^{{{int(exponent)}}}"
    return text


# ---------------------------------------------------------------------------
# Metadata (schema, theory, formulas, pseudocode, examples)
# ---------------------------------------------------------------------------

META = MethodMeta(
    id="bisection",
    chapter=Chapter.CH1_NONLINEAR,
    name="Bisection Method",
    summary=(
        "Find a root of f(x) = 0 by repeatedly halving a sign-changing interval. "
        "Simple and always reliable, but slow (linear convergence)."
    ),
    theory=(
        "The bisection method starts from an interval [a, b] on which the continuous "
        "function f changes sign, i.e. f(a)·f(b) < 0. By the Intermediate Value "
        "Theorem a root lies somewhere in between.\n\n"
        "Each step evaluates the midpoint c = (a + b)/2. If f(a) and f(c) have "
        "opposite signs the root lies in [a, c], otherwise it lies in [c, b]. The "
        "chosen half becomes the new bracket, so the interval — and therefore the "
        "error — is halved every iteration.\n\n"
        "After k iterations the distance from the true root x to the midpoint c_k is "
        "at most (b - a)/2^(k+1). The method always converges for a valid bracket, "
        "but only linearly: roughly one extra correct decimal digit every 3-4 steps."
    ),
    formulas=[
        LabeledLatex(label="Midpoint", latex=r"c_k = \frac{a_k + b_k}{2}"),
        LabeledLatex(
            label="Bracket update",
            latex=r"f(a_k)\,f(c_k) < 0 \;\Rightarrow\; b_{k+1}=c_k,\quad a_{k+1}=a_k",
        ),
        LabeledLatex(
            label="Error bound",
            latex=r"\left|x - c_k\right| \le \frac{b_0 - a_0}{2^{\,k+1}}",
        ),
        LabeledLatex(label="Order of convergence", latex=r"\text{linear},\quad p = 1"),
    ],
    pseudocode=(
        "Bisection(f, a, b, tol, max_iter):\n"
        "    fa <- f(a); fb <- f(b)\n"
        "    if fa * fb > 0:\n"
        "        stop \"no sign change on [a, b]\"\n"
        "    prev <- a\n"
        "    for k = 1 to max_iter:\n"
        "        c  <- (a + b) / 2\n"
        "        fc <- f(c)\n"
        "        err <- |c - prev|\n"
        "        if fc = 0 or err < tol:\n"
        "            return c, k                # converged\n"
        "        if fa * fc < 0:\n"
        "            b <- c; fb <- fc           # root in left half\n"
        "        else:\n"
        "            a <- c; fa <- fc           # root in right half\n"
        "        prev <- c\n"
        "    return (a + b) / 2, max_iter       # not converged"
    ),
    input_schema=[
        InputField(
            key="function",
            label="Function f(x)",
            type="function",
            variable="x",
            required=True,
            placeholder="x^3 - x - 1",
            help=(
                "Use ^ for powers, * for products (2*x). Allowed: sin, cos, tan, "
                "exp, ln, log, log10, sqrt, abs and more."
            ),
        ),
        InputField(
            key="a",
            label="Lower bound a",
            type="number",
            required=True,
            default=1.0,
            help="Left end of the bracket, where f(a) is evaluated.",
        ),
        InputField(
            key="b",
            label="Upper bound b",
            type="number",
            required=True,
            default=2.0,
            help="Right end of the bracket; f(a) and f(b) must have opposite signs.",
        ),
        InputField(
            key="tolerance",
            label="Tolerance (stopping error)",
            type="tolerance",
            required=True,
            default=1e-6,
            min=1e-15,
            max=1.0,
            help="Stop when the change in the midpoint is smaller than this.",
        ),
        InputField(
            key="max_iterations",
            label="Maximum iterations",
            type="max_iterations",
            required=True,
            default=50,
            min=1,
            max=10_000,
            help="Safety cap if the tolerance is never reached.",
        ),
    ],
    examples=[
        MethodExample(
            name="Cubic: x³ - x - 1 on [1, 2]",
            description="Classic textbook root near 1.3247.",
            inputs={
                "function": "x^3 - x - 1",
                "a": 1.0,
                "b": 2.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
            },
        ),
        MethodExample(
            name="√2: x² - 2 on [1, 2]",
            description="Recovers the square root of two.",
            inputs={
                "function": "x^2 - 2",
                "a": 1.0,
                "b": 2.0,
                "tolerance": 1e-8,
                "max_iterations": 50,
            },
        ),
        MethodExample(
            name="Transcendental: cos(x) - x on [0, 1]",
            description="Fixed point of cosine, root near 0.7391.",
            inputs={
                "function": "cos(x) - x",
                "a": 0.0,
                "b": 1.0,
                "tolerance": 1e-6,
                "max_iterations": 50,
            },
        ),
    ],
)


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Run the bisection method for the validated ``inputs``."""
    text: str = inputs["function"]
    a = float(inputs["a"])
    b = float(inputs["b"])
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)

    warnings: list[str] = []
    if a > b:
        a, b = b, a
        warnings.append("a and b were swapped so that a < b.")
    if a == b:
        raise InvalidInputError(
            "'a' and 'b' must be different to form an interval.",
            hint="Give two distinct bounds that bracket the root.",
        )
    a0, b0 = a, b

    expression = parse_expression(text, ("x",))
    f = make_function(expression, ("x",), strict=True)
    f_plot = make_function(expression, ("x",), strict=False)
    latex_f = expr_to_latex(expression)

    fa = f(a)
    fb = f(b)

    # A root sitting exactly on an endpoint needs no iteration.
    if fa == 0.0 or fb == 0.0:
        root = a if fa == 0.0 else b
        groot = fa if fa == 0.0 else fb
        return SolveResponse(
            method=META.id,
            status=SolveStatus.CONVERGED,
            result={
                "root": root,
                "iterations": 0,
                "f(root)": groot,
                "final_interval": [a0, b0],
            },
            steps=[
                Step(
                    title="Setup",
                    latex=(
                        f"f(x) = {latex_f},\\quad a = {_num(a)},\\quad b = {_num(b)}"
                        f"\\\\ f(a) = {_num(fa)},\\quad f(b) = {_num(fb)}"
                    ),
                    note="An endpoint is already a root, so no iterations are needed.",
                ),
            ],
            tables=[],
            plot=_build_plot(f_plot, expression, a0, b0, root),
            errors=ErrorInfo(absolute=0.0, relative_percent=0.0, order_of_convergence=1.0),
            warnings=warnings,
        )

    if fa * fb > 0:
        raise InvalidInputError(
            "There is no sign change on [a, b]: f(a) and f(b) have the same sign.",
            hint=(
                "Choose an interval where the function crosses the axis "
                f"(here f(a) = {fa:.6g} and f(b) = {fb:.6g})."
            ),
        )

    columns = [
        "Iteration",
        "a",
        "b",
        "c = (a+b)/2",
        "f(a)",
        "f(b)",
        "f(c)",
        "Error |c_k - c_(k-1)|",
    ]
    rows: list[list[Any]] = []
    steps: list[Step] = [
        Step(
            title="Setup",
            latex=(
                f"f(x) = {latex_f},\\quad a = {_num(a)},\\quad b = {_num(b)}"
                f"\\\\ f(a) = {_num(fa)},\\quad f(b) = {_num(fb)}"
            ),
            note=(
                "f(a) and f(b) have opposite signs, so a root lies in [a, b] "
                "(Intermediate Value Theorem)."
            ),
        )
    ]

    prev = a
    converged = False
    root = (a0 + b0) / 2
    last_error = abs(b0 - a0) / 2
    iterations_used = 0
    left_bracket, right_bracket = a0, b0

    for k in range(1, max_iterations + 1):
        c = (a + b) / 2
        fc = f(c)
        last_error = abs(c - prev)
        rows.append([k, a, b, c, fa, fb, fc, last_error])

        if fa * fc < 0:
            decision = r"f(a_k)\,f(c_k) < 0 \;\Rightarrow\; \text{root in } [a_k,\, c_k]"
            note = "Root is in the left half, so b ← c."
            new_a, new_b, new_fa, new_fb = a, c, fa, fc
        else:
            decision = r"f(a_k)\,f(c_k) > 0 \;\Rightarrow\; \text{root in } [c_k,\, b_k]"
            note = "Root is in the right half, so a ← c."
            new_a, new_b, new_fa, new_fb = c, b, fc, fb

        steps.append(
            Step(
                title=f"Iteration {k}",
                latex=(
                    f"c_{{{k}}} = \\frac{{a + b}}{{2}} ="
                    f" \\frac{{{_num(a)} + {_num(b)}}}{{2}} = {_num(c)}"
                    f"\\\\ f(c_{{{k}}}) = {_num(fc)}"
                    f"\\\\ {decision}"
                    f"\\\\ \\text{{Error}} = |c_{{{k}}} - c_{{{k - 1}}}| = {_num(last_error)}"
                ),
                note=note,
            )
        )

        left_bracket, right_bracket = new_a, new_b

        if fc == 0.0 or last_error < tolerance:
            root = c
            iterations_used = k
            converged = True
            break

        a, b, fa, fb = new_a, new_b, new_fa, new_fb
        prev = c

    if converged:
        status = SolveStatus.CONVERGED
        steps.append(
            Step(
                title="Result",
                latex=(
                    f"\\text{{Stopping criterion met}}"
                    f"\\\\ x \\approx c_{{{iterations_used}}} = {_num(root)}"
                    f",\\quad f(x) = {_num(f(root))}"
                ),
                note=f"Converged in {iterations_used} iterations (tolerance {tolerance:g}).",
            )
        )
    else:
        status = SolveStatus.MAX_ITER
        root = (a + b) / 2
        iterations_used = max_iterations
        warnings.append(
            f"The tolerance was not reached within {max_iterations} iterations; "
            "returning the latest midpoint."
        )
        steps.append(
            Step(
                title="Iteration limit reached",
                latex=(
                    f"x \\approx \\frac{{a + b}}{{2}} = {_num(root)}"
                    f",\\quad f(x) = {_num(f(root))}"
                ),
                note=f"Stopped after the maximum of {max_iterations} iterations.",
            )
        )

    f_root = f(root)
    relative = abs(last_error / root) * 100.0 if root != 0 else None

    return SolveResponse(
        method=META.id,
        status=status,
        result={
            "root": root,
            "iterations": iterations_used,
            "f(root)": f_root,
            "final_interval": [left_bracket, right_bracket],
        },
        steps=steps,
        tables=[
            DataTable(title="Bisection iterations", columns=columns, rows=rows),
        ],
        plot=_build_plot(f_plot, expression, a0, b0, root),
        errors=ErrorInfo(
            absolute=last_error,
            relative_percent=relative,
            order_of_convergence=1.0,
        ),
        warnings=warnings,
    )


def _marker_y(f_plot: Any, x: float) -> float:
    """f(x) for the root marker, snapped to the axis if not finite."""
    try:
        value = float(f_plot(x))
    except Exception:
        return 0.0
    return value if math.isfinite(value) else 0.0


def _build_plot(
    f_plot: Any,
    expression: Any,
    a: float,
    b: float,
    root: float,
) -> PlotPayload:
    """Curve of f(x) over the bracket plus the computed root marker."""
    span = b - a
    margin = 0.05 * span if span > 0 else max(abs(b), 1.0) * 0.1
    xs, ys = sample_curve(f_plot, a - margin, b + margin, points=400)
    traces = [
        line_trace(xs, ys, name=f"f(x) = {expr_to_latex(expression)}"),
        marker_trace(root, _marker_y(f_plot, root), "root"),
    ]
    layout: dict[str, Any] = {
        "title": {"text": f"Bisection on [{_num(a)}, {_num(b)}]"},
        "xaxis": {"title": {"text": "x"}, "zeroline": True},
        "yaxis": {"title": {"text": "f(x)"}, "zeroline": True},
    }
    return PlotPayload(traces=traces, layout=layout)
