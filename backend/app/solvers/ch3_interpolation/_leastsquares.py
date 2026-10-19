"""Shared building blocks for least-squares curve fitting (Chapter 3).

Private module (leading underscore) so the auto-loader skips it. It implements
the supported models -- the straight line, quadratic and general polynomial, and
the linearisable exponential, power, reciprocal and hyperbolic forms -- together
with the normal-equation working, the residual statistics and the plots used by
the ``least_squares`` solver.

The polynomial-type models are fitted directly by solving the normal equations
of an ordinary (unweighted) least-squares problem. The reducible forms are first
linearised (e.g. ``ln y = ln a + b x``), fitted in the transformed variables and
then mapped back to the original parameters.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.models import DataTable, PlotPayload
from app.solvers._common import format_num, points_trace

MIN_POLY_DEGREE = 2
MAX_POLY_DEGREE = 6
CURVE_POINTS = 300

# Fit keys, in the order the UI offers them.
FIT_KEYS = [
    "linear",
    "quadratic",
    "polynomial",
    "exponential",
    "power",
    "reciprocal",
    "hyperbolic",
]

# Human-readable names for the ranking table and the result payload.
FIT_LABELS: dict[str, str] = {
    "linear": "Linear",
    "quadratic": "Quadratic",
    "polynomial": "Polynomial",
    "exponential": "Exponential",
    "power": "Power",
    "reciprocal": "Reciprocal",
    "hyperbolic": "Hyperbolic",
}

# The general symbolic form of each model (LaTeX, for the theory/setup steps).
GENERAL_FORMS: dict[str, str] = {
    "linear": r"y = a + b\,x",
    "quadratic": r"y = a + b\,x + c\,x^2",
    "polynomial": r"y = a_0 + a_1 x + a_2 x^2 + \dots + a_n x^n",
    "exponential": r"y = a\,e^{b x}",
    "power": r"y = a\,x^{b}",
    "reciprocal": r"y = a + \frac{b}{x}",
    "hyperbolic": r"y = \frac{1}{a + b\,x}",
}

# The reducible models that need a linearisation step.
REDUCIBLE = {"exponential", "power", "reciprocal", "hyperbolic"}


class FitError(Exception):
    """A mathematical failure while fitting (mapped to HTTP 200 ``failed``)."""


@dataclass
class FitOutcome:
    """The result of fitting one model to one dataset."""

    key: str
    label: str
    poly_degree: int
    general_form: str
    linearization: str
    params: dict[str, float]
    solution_labels: list[str]
    solution_values: list[float]
    u: np.ndarray
    v: np.ndarray
    u_symbol: str
    v_symbol: str
    u_plain: str
    v_plain: str
    predict: Callable[[np.ndarray], np.ndarray]
    equation_latex: str
    equation_plain: str
    back_latex: str
    sums: list[float]
    normal_matrix: np.ndarray
    normal_rhs: np.ndarray
    sse: float
    r_squared: float | None
    rmse: float
    exact_fit: bool
    positive_x: bool


# ---------------------------------------------------------------------------
# Small number/LaTeX helpers
# ---------------------------------------------------------------------------

_SUPERSCRIPTS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def superscript(power: int) -> str:
    """Render a non-negative integer power with unicode superscripts."""
    return "".join(_SUPERSCRIPTS[int(digit)] for digit in str(power))


def _plain_num(value: float) -> str:
    if value == 0:
        return "0"
    return f"{value:.6g}"


def _term_latex(magnitude: str, var: str, power: int) -> str:
    if power == 0:
        return magnitude
    if power == 1:
        return rf"{magnitude}\,{var}"
    return rf"{magnitude}\,{var}^{{{power}}}"


def _signed_poly_latex(coefficients: list[float], var: str, decimals: int) -> str:
    """``a + b x + c x^2 + ...`` with explicit signs (no leading ``y =``)."""
    pieces: list[str] = []
    for power, coefficient in enumerate(coefficients):
        if abs(coefficient) < 1e-14 and power > 0:
            continue
        body = _term_latex(format_num(abs(coefficient), decimals), var, power)
        if not pieces:
            pieces.append(body if coefficient >= 0 else f"-{body}")
        else:
            pieces.append((" - " if coefficient < 0 else " + ") + body)
    return "".join(pieces) if pieces else "0"


def _signed_poly_plain(coefficients: list[float], var: str) -> str:
    pieces: list[str] = []
    for power, coefficient in enumerate(coefficients):
        if abs(coefficient) < 1e-14 and power > 0:
            continue
        magnitude = _plain_num(abs(coefficient))
        if power == 0:
            body = magnitude
        elif power == 1:
            body = f"{magnitude}*{var}"
        else:
            body = f"{magnitude}*{var}^{power}"
        if not pieces:
            pieces.append(body if coefficient >= 0 else f"-{body}")
        else:
            pieces.append((" - " if coefficient < 0 else " + ") + body)
    return "".join(pieces) if pieces else "0"


def _linear_latex(a: float, b: float, var: str, decimals: int) -> str:
    """``a + b var`` with explicit sign."""
    if b == 0:
        return format_num(a, decimals)
    sign = "-" if b < 0 else "+"
    return f"{format_num(a, decimals)} {sign} {format_num(abs(b), decimals)}\\,{var}"


def _bmatrix(rows: list[list[str]]) -> str:
    body = r" \\ ".join(" & ".join(cell for cell in row) for row in rows)
    return r"\begin{bmatrix}" + body + r"\end{bmatrix}"


def _solution_latex(labels: list[str], values: list[float], decimals: int) -> str:
    return r",\quad ".join(
        rf"{label} = {format_num(value, decimals)}"
        for label, value in zip(labels, values, strict=True)
    )


# ---------------------------------------------------------------------------
# Linear algebra: normal equations
# ---------------------------------------------------------------------------


def _normal_system(
    u: np.ndarray, v: np.ndarray, degree: int
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """Build ``(A, rhs, sums)`` for ``sum_k a_k u^k`` in the least-squares sense.

    ``sums[k] = sum u^k`` for ``k = 0 .. 2*degree``. The normal matrix is
    ``A[i, j] = sums[i + j]`` and ``rhs[i] = sum u^i v``.
    """
    sums = [float(np.sum(u**k)) for k in range(2 * degree + 1)]
    matrix = np.array(
        [[sums[i + j] for j in range(degree + 1)] for i in range(degree + 1)],
        dtype=float,
    )
    rhs = np.array([float(np.sum(u**k * v)) for k in range(degree + 1)], dtype=float)
    return matrix, rhs, sums


def _poly_predict(coefficients: list[float]) -> Callable[[np.ndarray], np.ndarray]:
    ordered = np.asarray(coefficients, dtype=float)[::-1]

    def predict(grid: np.ndarray) -> np.ndarray:
        return np.asarray(np.polyval(ordered, np.asarray(grid, dtype=float)), dtype=float)

    return predict


# ---------------------------------------------------------------------------
# Guards for the reducible forms
# ---------------------------------------------------------------------------


def _require_positive(values: np.ndarray, name: str, message: str, xs: np.ndarray) -> None:
    bad = values <= 0
    if bool(np.any(bad)):
        index = int(np.argmax(bad))
        raise FitError(
            f"{message}, but {name} = {float(values[index]):g} at x = {float(xs[index]):g}."
        )


def _require_nonzero(values: np.ndarray, name: str, message: str, xs: np.ndarray) -> None:
    bad = values == 0
    if bool(np.any(bad)):
        index = int(np.argmax(bad))
        raise FitError(
            f"{message}, but {name} = 0 at x = {float(xs[index]):g}."
        )


# ---------------------------------------------------------------------------
# The fit itself
# ---------------------------------------------------------------------------


def build_fit(fit_type: str, degree: int, xs: np.ndarray, ys: np.ndarray, decimals: int) -> FitOutcome:
    """Fit one model to the data, or raise :class:`FitError`."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    count = int(xs.size)
    positive_x = False

    if fit_type in {"linear", "quadratic", "polynomial"}:
        poly_degree = {
            "linear": 1,
            "quadratic": 2,
            "polynomial": max(MIN_POLY_DEGREE, min(degree, MAX_POLY_DEGREE)),
        }[fit_type]
        u, v = xs, ys
        u_symbol, v_symbol, u_plain, v_plain = "x", "y", "x", "y"
        linearization = ""
    elif fit_type == "exponential":
        _require_positive(ys, "y", "the exponential model y = a e^(bx) needs y > 0", xs)
        poly_degree = 1
        u, v = xs, np.log(ys)
        u_symbol, v_symbol, u_plain, v_plain = "x", r"\ln y", "x", "ln y"
        linearization = r"\ln y = \ln a + b\,x"
    elif fit_type == "power":
        _require_positive(xs, "x", "the power model y = a x^b needs x > 0", xs)
        _require_positive(ys, "y", "the power model y = a x^b needs y > 0", xs)
        poly_degree = 1
        u, v = np.log(xs), np.log(ys)
        u_symbol, v_symbol, u_plain, v_plain = r"\ln x", r"\ln y", "ln x", "ln y"
        linearization = r"\ln y = \ln a + b\,\ln x"
        positive_x = True
    elif fit_type == "reciprocal":
        _require_nonzero(xs, "x", "the reciprocal model y = a + b/x needs x != 0", xs)
        poly_degree = 1
        u, v = 1.0 / xs, ys
        u_symbol, v_symbol, u_plain, v_plain = r"1/x", "y", "1/x", "y"
        linearization = r"y = a + b\left(\tfrac{1}{x}\right)"
        positive_x = True
    elif fit_type == "hyperbolic":
        _require_nonzero(ys, "y", "the hyperbolic model y = 1/(a + bx) needs y != 0", xs)
        poly_degree = 1
        u, v = xs, 1.0 / ys
        u_symbol, v_symbol, u_plain, v_plain = "x", r"1/y", "x", "1/y"
        linearization = r"\frac{1}{y} = a + b\,x"
    else:
        raise FitError(f"Unknown fit type '{fit_type}'.")

    if count < poly_degree + 1:
        raise FitError(
            f"A degree-{poly_degree} fit needs at least {poly_degree + 1} data points, "
            f"but only {count} were given."
        )

    matrix, rhs, sums = _normal_system(u, v, poly_degree)
    try:
        coefficients = np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError as exc:
        raise FitError(
            "The normal equations are singular, so the coefficients cannot be found "
            "uniquely. Check the data for repeated or degenerate x values."
        ) from exc
    coeff_list = [float(value) for value in coefficients]
    if not all(math.isfinite(value) for value in coeff_list):
        raise FitError("The normal equations produced non-finite coefficients; the fit is ill-posed.")

    equation_latex, equation_plain, solution_labels, back_latex = _describe(
        fit_type, poly_degree, coeff_list, decimals
    )

    predict = _predictor(fit_type, coeff_list)

    y_hat = np.asarray(predict(xs), dtype=float)
    residuals = ys - y_hat
    sse = float(np.sum(residuals**2))
    if not math.isfinite(sse):
        raise FitError("The fitted model does not produce finite values on the data.")
    mean = float(np.mean(ys))
    sst = float(np.sum((ys - mean) ** 2))
    r_squared = float(1.0 - sse / sst) if sst > 0 else None
    rmse = math.sqrt(sse / count)

    label = FIT_LABELS[fit_type]
    if fit_type == "polynomial":
        label = f"Polynomial (degree {poly_degree})"

    return FitOutcome(
        key=fit_type,
        label=label,
        poly_degree=poly_degree,
        general_form=GENERAL_FORMS[fit_type],
        linearization=linearization,
        params=_original_params(fit_type, coeff_list),
        solution_labels=solution_labels,
        solution_values=coeff_list,
        u=u,
        v=v,
        u_symbol=u_symbol,
        v_symbol=v_symbol,
        u_plain=u_plain,
        v_plain=v_plain,
        predict=predict,
        equation_latex=equation_latex,
        equation_plain=equation_plain,
        back_latex=back_latex,
        sums=sums,
        normal_matrix=matrix,
        normal_rhs=rhs,
        sse=sse,
        r_squared=r_squared,
        rmse=rmse,
        exact_fit=poly_degree >= count - 1,
        positive_x=positive_x,
    )


def _describe(
    fit_type: str,
    poly_degree: int,
    coeff_list: list[float],
    decimals: int,
) -> tuple[str, str, list[str], str]:
    """Return ``(equation_latex, equation_plain, solution_labels, back_latex)``."""
    if fit_type == "linear":
        return (
            "y = " + _signed_poly_latex(coeff_list, "x", decimals),
            "y = " + _signed_poly_plain(coeff_list, "x"),
            ["a", "b"],
            "",
        )
    if fit_type == "quadratic":
        return (
            "y = " + _signed_poly_latex(coeff_list, "x", decimals),
            "y = " + _signed_poly_plain(coeff_list, "x"),
            ["a", "b", "c"],
            "",
        )
    if fit_type == "polynomial":
        labels = [f"a_{k}" for k in range(poly_degree + 1)]
        return (
            "y = " + _signed_poly_latex(coeff_list, "x", decimals),
            "y = " + _signed_poly_plain(coeff_list, "x"),
            labels,
            "",
        )
    if fit_type == "exponential":
        intercept, slope = coeff_list
        a = math.exp(intercept)
        equation_latex = rf"y = {format_num(a, decimals)}\,e^{{{format_num(slope, decimals)}\,x}}"
        equation_plain = f"y = {_plain_num(a)}*exp({_plain_num(slope)}*x)"
        back = (
            rf"a = e^{{\ln a}} = e^{{{format_num(intercept, decimals)}}} = {format_num(a, decimals)}"
            + r",\quad b = "
            + format_num(slope, decimals)
        )
        return equation_latex, equation_plain, [r"\ln a", "b"], back
    if fit_type == "power":
        intercept, slope = coeff_list
        a = math.exp(intercept)
        equation_latex = rf"y = {format_num(a, decimals)}\,x^{{{format_num(slope, decimals)}}}"
        equation_plain = f"y = {_plain_num(a)}*x^{_plain_num(slope)}"
        back = (
            rf"a = e^{{\ln a}} = e^{{{format_num(intercept, decimals)}}} = {format_num(a, decimals)}"
            + r",\quad b = "
            + format_num(slope, decimals)
        )
        return equation_latex, equation_plain, [r"\ln a", "b"], back
    if fit_type == "reciprocal":
        a, b = coeff_list
        term = rf"\frac{{{format_num(abs(b), decimals)}}}{{x}}"
        body = f"{format_num(a, decimals)} + {term}" if b >= 0 else f"{format_num(a, decimals)} - {term}"
        equation_plain = f"y = {_plain_num(a)} {'-' if b < 0 else '+'} {_plain_num(abs(b))}/x"
        return "y = " + body, equation_plain, ["a", "b"], ""
    # hyperbolic
    a, b = coeff_list
    equation_latex = rf"y = \frac{{1}}{{{_linear_latex(a, b, 'x', decimals)}}}"
    equation_plain = f"y = 1/({_plain_num(a)} + {_plain_num(b)}*x)"
    return equation_latex, equation_plain, ["a", "b"], ""


def _original_params(fit_type: str, coeff_list: list[float]) -> dict[str, float]:
    if fit_type == "exponential":
        intercept, slope = coeff_list
        return {"a": math.exp(intercept), "b": slope}
    if fit_type == "power":
        intercept, slope = coeff_list
        return {"a": math.exp(intercept), "b": slope}
    if fit_type == "linear":
        return {"a": coeff_list[0], "b": coeff_list[1]}
    if fit_type == "quadratic":
        return {"a": coeff_list[0], "b": coeff_list[1], "c": coeff_list[2]}
    if fit_type == "polynomial":
        return {f"a{k}": value for k, value in enumerate(coeff_list)}
    return {"a": coeff_list[0], "b": coeff_list[1]}


def _predictor(fit_type: str, coeff_list: list[float]) -> Callable[[np.ndarray], np.ndarray]:
    if fit_type in {"linear", "quadratic", "polynomial"}:
        return _poly_predict(coeff_list)
    if fit_type == "exponential":
        a = math.exp(coeff_list[0])
        b = coeff_list[1]

        def predict_exp(grid: np.ndarray) -> np.ndarray:
            return np.asarray(a * np.exp(b * np.asarray(grid, dtype=float)), dtype=float)

        return predict_exp
    if fit_type == "power":
        a = math.exp(coeff_list[0])
        b = coeff_list[1]

        def predict_power(grid: np.ndarray) -> np.ndarray:
            return np.asarray(a * np.power(np.asarray(grid, dtype=float), b), dtype=float)

        return predict_power
    if fit_type == "reciprocal":
        a, b = coeff_list

        def predict_reciprocal(grid: np.ndarray) -> np.ndarray:
            return np.asarray(a + b / np.asarray(grid, dtype=float), dtype=float)

        return predict_reciprocal
    a, b = coeff_list

    def predict_hyperbolic(grid: np.ndarray) -> np.ndarray:
        return np.asarray(1.0 / (a + b * np.asarray(grid, dtype=float)), dtype=float)

    return predict_hyperbolic


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def _wrapped(symbol: str) -> str:
    return f"({symbol})" if any(ch in symbol for ch in " /") else symbol


def sums_table(outcome: FitOutcome, decimals: int) -> DataTable:
    """The sums that populate the normal equations, as ``Sum | Value`` rows."""
    u_label = _wrapped(outcome.u_plain)
    v_label = _wrapped(outcome.v_plain)
    rows: list[list[Any]] = [
        ["n", int(outcome.u.size)],
        [f"Σ{u_label}", format_num(outcome.sums[1], decimals)],
        [f"Σ{v_label}", format_num(float(np.sum(outcome.v)), decimals)],
        [f"Σ{u_label}{v_label}", format_num(float(np.sum(outcome.u * outcome.v)), decimals)],
    ]
    for power in range(2, 2 * outcome.poly_degree + 1):
        rows.append([f"Σ{u_label}{superscript(power)}", format_num(outcome.sums[power], decimals)])
    for power in range(2, outcome.poly_degree + 1):
        value = float(np.sum(outcome.u**power * outcome.v))
        rows.append([f"Σ{u_label}{superscript(power)}{v_label}", format_num(value, decimals)])
    return DataTable(title="Sums for the normal equations", columns=["Sum", "Value"], rows=rows)


def transformed_table(outcome: FitOutcome, xs: np.ndarray, ys: np.ndarray, decimals: int) -> DataTable:
    """The original data alongside the linearised variables (reducible forms)."""
    columns = ["x", "y"]
    series: list[list[str]] = [
        [format_num(float(value), decimals) for value in xs],
        [format_num(float(value), decimals) for value in ys],
    ]
    if not np.allclose(outcome.u, xs):
        columns.append(f"U = {outcome.u_plain}")
        series.append([format_num(float(value), decimals) for value in outcome.u])
    if not np.allclose(outcome.v, ys):
        columns.append(f"V = {outcome.v_plain}")
        series.append([format_num(float(value), decimals) for value in outcome.v])
    rows = [[series[column][i] for column in range(len(columns))] for i in range(len(xs))]
    return DataTable(title="Transformed data", columns=columns, rows=rows)


def residual_table(outcome: FitOutcome, xs: np.ndarray, ys: np.ndarray, decimals: int) -> DataTable:
    """``x``, ``y``, fitted ``y`` and the residual with its square."""
    y_hat = np.asarray(outcome.predict(xs), dtype=float)
    rows: list[list[Any]] = []
    for x, y, fitted in zip(xs, ys, y_hat, strict=True):
        residual = float(y - fitted)
        rows.append(
            [
                format_num(float(x), decimals),
                format_num(float(y), decimals),
                format_num(float(fitted), decimals),
                format_num(residual, decimals),
                format_num(residual * residual, decimals),
            ]
        )
    return DataTable(
        title="Residuals",
        columns=["x", "y", "fitted y", "residual", "residual²"],
        rows=rows,
    )


def statistics_table(outcome: FitOutcome, count: int, decimals: int) -> DataTable:
    """SSE, R² and RMSE (with the model and the sample size)."""
    r_squared = "n/a" if outcome.r_squared is None else format_num(outcome.r_squared, decimals)
    rows: list[list[Any]] = [
        ["Model", outcome.label],
        ["Number of points", count],
        ["Degree", outcome.poly_degree],
        ["SSE = Σ(y - ŷ)²", format_num(outcome.sse, decimals)],
        ["R²", r_squared],
        ["RMSE", format_num(outcome.rmse, decimals)],
    ]
    return DataTable(title="Fit statistics", columns=["Quantity", "Value"], rows=rows)


def predictions_table(targets: list[float], values: list[float | None], decimals: int) -> DataTable:
    """Predicted ``y`` at the requested target ``x`` values."""
    rows: list[list[Any]] = []
    for target, value in zip(targets, values, strict=True):
        rows.append(
            [
                format_num(float(target), decimals),
                "n/a" if value is None else format_num(float(value), decimals),
            ]
        )
    return DataTable(title="Predicted values", columns=["x", "predicted y"], rows=rows)


def ranking_table(outcomes: list[FitOutcome], decimals: int) -> DataTable:
    """Fit models ranked by SSE (best first)."""
    ordered = sorted(outcomes, key=lambda outcome: outcome.sse)
    rows: list[list[Any]] = []
    for rank, outcome in enumerate(ordered, start=1):
        r_squared = "n/a" if outcome.r_squared is None else format_num(outcome.r_squared, decimals)
        rows.append(
            [
                rank,
                outcome.label,
                format_num(outcome.sse, decimals),
                r_squared,
                format_num(outcome.rmse, decimals),
            ]
        )
    return DataTable(
        title="Model comparison (ranked by SSE)",
        columns=["Rank", "Model", "SSE", "R²", "RMSE"],
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def _clean(values: np.ndarray) -> list[float | None]:
    return [float(value) if math.isfinite(float(value)) else None for value in values]


def sample_grid(xs: np.ndarray, targets: list[float], *, positive_x: bool) -> np.ndarray:
    """A plotting grid spanning the data (and targets), positive when needed."""
    lo = float(np.min(xs))
    hi = float(np.max(xs))
    if targets:
        lo = min(lo, min(targets))
        hi = max(hi, max(targets))
    if positive_x:
        if lo <= 0:
            lo = min(float(value) for value in xs if value > 0)
        return np.linspace(lo, hi, CURVE_POINTS)
    pad = 0.05 * (hi - lo) if hi > lo else 0.5
    return np.linspace(lo - pad, hi + pad, CURVE_POINTS)


def outcome_curve(outcome: FitOutcome, grid: np.ndarray) -> list[float | None]:
    """The fitted curve sampled on ``grid`` (non-finite points become gaps)."""
    return _clean(np.asarray(outcome.predict(grid), dtype=float))


def fit_residual_plot(
    *,
    xs: np.ndarray,
    ys: np.ndarray,
    grid: np.ndarray,
    curve: list[float | None],
    residuals: list[float | None],
    targets: list[float],
    target_values: list[float | None],
    title: str,
) -> PlotPayload:
    """Data points, the fitted curve and a residual panel underneath."""
    traces: list[dict[str, Any]] = [points_trace(list(xs), list(ys), "Data points")]
    traces.append(
        {
            "type": "scatter",
            "mode": "lines",
            "name": "Fitted curve",
            "x": [float(value) for value in grid],
            "y": curve,
        }
    )
    if targets and target_values:
        traces.append(
            {
                "type": "scatter",
                "mode": "markers",
                "name": "Prediction",
                "x": list(targets),
                "y": target_values,
                "marker": {"color": "#dc2626", "size": 11, "symbol": "diamond"},
            }
        )
    traces.append(
        {
            "type": "bar",
            "name": "Residuals",
            "x": [float(value) for value in xs],
            "y": residuals,
            "marker": {"color": "#f59e0b"},
            "xaxis": "x2",
            "yaxis": "y2",
        }
    )
    layout = {
        "title": {"text": title},
        "grid": {"rows": 2, "columns": 1, "pattern": "independent", "roworder": "top to bottom"},
        "xaxis": {"title": {"text": "x"}},
        "yaxis": {"domain": [0.34, 1.0], "title": {"text": "y"}},
        "xaxis2": {"title": {"text": "x"}, "anchor": "y2"},
        "yaxis2": {"domain": [0.0, 0.24], "title": {"text": "residual"}, "zeroline": True},
    }
    return PlotPayload(traces=traces, layout=layout)


# ---------------------------------------------------------------------------
# Working (LaTeX) helpers used by the solver
# ---------------------------------------------------------------------------


def unknown_labels(outcome: FitOutcome) -> list[str]:
    """LaTeX labels for the unknowns of the normal equations."""
    if outcome.key == "exponential" or outcome.key == "power":
        return [r"\ln a", "b"]
    if outcome.key == "polynomial":
        return [f"a_{k}" for k in range(outcome.poly_degree + 1)]
    if outcome.key == "quadratic":
        return ["a", "b", "c"]
    return ["a", "b"]


def normal_equations_latex(outcome: FitOutcome, decimals: int) -> str:
    """The normal equations rendered as ``[A][c] = [rhs]``."""
    degree = outcome.poly_degree
    matrix_rows = [
        [format_num(float(outcome.sums[i + j]), decimals) for j in range(degree + 1)]
        for i in range(degree + 1)
    ]
    rhs_rows = [[format_num(float(outcome.normal_rhs[i]), decimals)] for i in range(degree + 1)]
    unknown_rows = [[label] for label in unknown_labels(outcome)]
    return _bmatrix(matrix_rows) + _bmatrix(unknown_rows) + " = " + _bmatrix(rhs_rows)


def solution_latex(outcome: FitOutcome, decimals: int) -> str:
    """The solution of the normal equations (the coefficients actually found)."""
    return _solution_latex(unknown_labels(outcome), outcome.solution_values, decimals)


def residual_series(outcome: FitOutcome, xs: np.ndarray, ys: np.ndarray) -> list[float | None]:
    """``y_i - f(x_i)`` for every point (non-finite entries become ``None``)."""
    predicted = outcome_curve(outcome, xs)
    return [
        float(y) - value if value is not None else None
        for y, value in zip(ys, predicted, strict=True)
    ]
