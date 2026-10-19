"""Least-squares curve fitting.

Fits the model that minimises the sum of squared vertical residuals. The
coefficients of a polynomial-type model come straight from the normal equations
``(A^T A) c = A^T y``; the exponential, power, reciprocal and hyperbolic forms
are first linearised (e.g. ``ln y = ln a + b x``) and then transformed back. The
solver reports the sums, the normal equations, the residuals and the goodness of
fit (SSE, R², RMSE), and can rank every applicable model by SSE.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.models import (
    Chapter,
    DataTable,
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
from app.solvers._common import boolean_field, failed_response, format_num, precision_field
from app.solvers.ch3_interpolation._interp import (
    data_points_field,
    node_table,
    overlay_plot,
    prepare_dataset,
    targets_field,
)
from app.solvers.ch3_interpolation._leastsquares import (
    FIT_KEYS,
    FIT_LABELS,
    REDUCIBLE,
    FitError,
    FitOutcome,
    build_fit,
    fit_residual_plot,
    normal_equations_latex,
    outcome_curve,
    predictions_table,
    ranking_table,
    residual_series,
    residual_table,
    sample_grid,
    solution_latex,
    statistics_table,
    sums_table,
    transformed_table,
)

FIT_OPTIONS: list[SelectOption] = [
    SelectOption(value="linear", label="Linear: y = a + b x"),
    SelectOption(value="quadratic", label="Quadratic: y = a + b x + c x^2"),
    SelectOption(value="polynomial", label="Polynomial degree n (2-6)"),
    SelectOption(value="exponential", label="Exponential: y = a e^(b x)"),
    SelectOption(value="power", label="Power: y = a x^b"),
    SelectOption(value="reciprocal", label="Reciprocal: y = a + b/x"),
    SelectOption(value="hyperbolic", label="Hyperbolic: y = 1/(a + b x)"),
]

DEGREE_FIELD = InputField(
    key="degree",
    label="Polynomial degree (2-6)",
    type="integer",
    required=False,
    default=3,
    min=2,
    max=6,
    help="Used only when the fit type is 'Polynomial degree n'.",
)

META = MethodMeta(
    id="least_squares",
    chapter=Chapter.CH3_INTERPOLATION,
    name="Least-Squares Curve Fitting",
    summary=(
        "Fit the best straight line, polynomial or linearisable curve by minimising "
        "the sum of squared residuals."
    ),
    theory=(
        "Least-squares fitting chooses the coefficients that minimise the sum of the "
        "squared vertical distances from the data to the model: SSE = sum_i (y_i - f(x_i))^2.\n\n"
        "For a model that is linear in its coefficients the minimisation gives the "
        "normal equations. Writing the design matrix as A and the data vector as y:\n"
        "  (A^T A) c = A^T y.\n"
        "For a straight line y = a + b x these reduce to the familiar pair\n"
        "  n a + b sum x = sum y,\n"
        "  a sum x + b sum x^2 = sum x y,\n"
        "and for a degree-k polynomial the matrix simply grows to include the higher "
        "powers sum x^3, sum x^4, ... .\n\n"
        "Curves that are not polynomials can often be linearised by a transformation. "
        "Taking logarithms, y = a e^{b x} becomes ln y = ln a + b x, and y = a x^b "
        "becomes ln y = ln a + b ln x; both are then straight-line fits in the "
        "transformed variables. The reciprocal y = a + b/x is linear in u = 1/x, and "
        "y = 1/(a + b x) is linear in 1/y. After fitting, the coefficients are mapped "
        "back to the original parameters.\n\n"
        "Quality measures: SSE is the residual sum of squares, R^2 = 1 - SSE/SST "
        "measures the fraction of the variance explained, and RMSE = sqrt(SSE/n) is "
        "the typical size of a residual."
    ),
    formulas=[
        LabeledLatex(
            label="Least-squares objective",
            latex=r"\text{SSE} = \sum_{i=0}^{n} \left(y_i - f(x_i)\right)^2",
        ),
        LabeledLatex(label="Normal equations", latex=r"\left(A^{T} A\right) c = A^{T} y"),
        LabeledLatex(
            label="Line: normal equations",
            latex=r"\begin{aligned} n a + b \sum x &= \sum y \\ a \sum x + b \sum x^2 &= \sum x y \end{aligned}",
        ),
        LabeledLatex(
            label="Exponential linearisation",
            latex=r"y = a e^{b x} \;\Longrightarrow\; \ln y = \ln a + b\,x",
        ),
        LabeledLatex(
            label="Power linearisation",
            latex=r"y = a x^{b} \;\Longrightarrow\; \ln y = \ln a + b\,\ln x",
        ),
        LabeledLatex(
            label="Hyperbolic linearisation",
            latex=r"y = \frac{1}{a + b x} \;\Longrightarrow\; \frac{1}{y} = a + b\,x",
        ),
        LabeledLatex(
            label="Goodness of fit",
            latex=r"R^2 = 1 - \frac{\text{SSE}}{\text{SST}},\qquad \text{RMSE} = \sqrt{\frac{\text{SSE}}{n}}",
        ),
    ],
    pseudocode=(
        "LeastSquares(xs, ys, model):\n"
        "    if model is reducible:\n"
        "        transform (xs, ys) -> (u, v)      # e.g. u = x, v = ln y\n"
        "    else:\n"
        "        (u, v) <- (xs, ys)\n"
        "    build the normal equations: A[i][j] = sum u^(i+j), rhs[i] = sum u^i * v\n"
        "    solve A c = rhs for the coefficients c\n"
        "    if model is reducible: back-transform c to the original parameters\n"
        "    residuals <- ys - f(xs)\n"
        "    return c, SSE = sum(residuals^2), R^2, RMSE"
    ),
    input_schema=[
        data_points_field(
            help="One point per row as 'x, y'. The model is fitted to all points at once.",
        ),
        InputField(
            key="fit_type",
            label="Fit type",
            type="select",
            required=True,
            default="linear",
            options=list(FIT_OPTIONS),
            help="The model to fit. Reducible forms are linearised automatically.",
        ),
        DEGREE_FIELD,
        targets_field(
            required=False,
            label="Predict at x value(s)",
            help="Optional x values at which to evaluate the fitted model.",
        ),
        boolean_field(
            "compare",
            "Compare all fit types",
            False,
            help="Fit every applicable model, rank them by SSE and overlay the curves.",
        ),
        precision_field(),
    ],
    examples=[
        MethodExample(
            name="Straight line",
            description="Fit y = a + b x to five points; exact line y = 1 + 2x.",
            inputs={
                "points": [[0, 1], [1, 3], [2, 5], [3, 7], [4, 9]],
                "fit_type": "linear",
                "degree": 3,
                "targets": [5.0],
                "compare": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Quadratic",
            description="Recover y = 1 + 2x + 3x^2 from five exact points.",
            inputs={
                "points": [[0, 1], [1, 6], [2, 17], [3, 34], [4, 57]],
                "fit_type": "quadratic",
                "degree": 3,
                "targets": [5.0],
                "compare": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Exponential",
            description="Linearise y = 2 e^(0.5 x) with ln y = ln a + b x.",
            inputs={
                "points": [[0, 2], [1, 3.29744], [2, 5.43656], [3, 8.96338], [4, 14.77811]],
                "fit_type": "exponential",
                "degree": 3,
                "targets": [5.0],
                "compare": False,
                "decimal_precision": 6,
            },
        ),
        MethodExample(
            name="Compare models",
            description="Rank every applicable model by SSE for the same data.",
            inputs={
                "points": [[0, 1], [1, 3], [2, 5], [3, 7], [4, 9]],
                "fit_type": "linear",
                "degree": 3,
                "targets": [5.0],
                "compare": True,
                "decimal_precision": 6,
            },
        ),
    ],
)


def _setup_latex(outcome: FitOutcome, count: int) -> str:
    return r"\\[1mm]".join(
        [
            r"\text{Number of points } n = " + f"{count}",
            r"\text{model: } " + outcome.general_form,
            r"\text{degree} = " + f"{outcome.poly_degree}",
        ]
    )


def _compare_keys(degree: int) -> list[str]:
    keys = list(FIT_KEYS)
    if degree < 3:
        keys = [key for key in keys if key != "polynomial"]
    return keys


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    """Fit the chosen model and, optionally, rank every applicable model."""
    decimals = int(inputs["decimal_precision"])
    dataset = prepare_dataset(inputs["points"])
    xs, ys = dataset.xs, dataset.ys
    count = len(xs)

    fit_type = str(inputs["fit_type"])
    degree = int(inputs.get("degree") or 3)
    compare = bool(inputs.get("compare"))
    raw_targets = inputs.get("targets")
    targets = [float(value) for value in raw_targets] if raw_targets else []

    try:
        primary = build_fit(fit_type, degree, xs, ys, decimals)
    except FitError as exc:
        return failed_response(META.id, str(exc), warnings=list(dataset.notices))

    warnings = list(dataset.notices)
    if primary.exact_fit:
        warnings.append(
            f"A degree-{primary.poly_degree} model has as many parameters as the {count} points "
            "can determine, so the curve passes through (or nearly through) every point: an exact "
            "fit that may be overfitting."
        )

    steps: list[Step] = [
        Step(
            title="Setup",
            latex=_setup_latex(primary, count),
            note="Least squares minimises the sum of squared vertical residuals.",
        )
    ]

    if primary.key in REDUCIBLE:
        steps.append(
            Step(
                title="Linearisation",
                latex=(
                    primary.linearization
                    + r"\\[1mm] U = "
                    + primary.u_symbol
                    + r",\quad V = "
                    + primary.v_symbol
                ),
                note="The model is linear in the transformed variables U and V.",
            )
        )

    steps.append(
        Step(
            title="Normal equations",
            latex=normal_equations_latex(primary, decimals),
            note="The sums in the table below populate A and the right-hand side A^T y.",
        )
    )
    steps.append(
        Step(
            title="Solve the normal equations",
            latex=solution_latex(primary, decimals),
            note="Solving the system gives the coefficients of the fitted model.",
        )
    )
    if primary.back_latex:
        steps.append(
            Step(
                title="Back-transformed coefficients",
                latex=primary.back_latex,
                note="Undo the linearisation to recover the original parameters.",
            )
        )
    steps.append(
        Step(
            title="Fitted equation",
            latex=primary.equation_latex,
            note="This is the model written in the original variables.",
        )
    )

    prediction_values: list[float | None] = []
    if targets:
        prediction_values = outcome_curve(primary, np.asarray(targets, dtype=float))
        lines = [
            r"f\left("
            + format_num(float(target), decimals)
            + r"\right) = "
            + (r"\text{n/a}" if value is None else format_num(float(value), decimals))
            for target, value in zip(targets, prediction_values, strict=True)
        ]
        steps.append(
            Step(
                title="Predictions",
                latex=r"\\[1mm]".join(lines),
                note="Evaluate the fitted equation at the requested x values.",
            )
        )

    outcomes: list[FitOutcome] = []
    if compare:
        for key in _compare_keys(degree):
            try:
                outcomes.append(build_fit(key, degree, xs, ys, decimals))
            except FitError as exc:
                warnings.append(f"{FIT_LABELS[key]} fit skipped: {exc}")
        if not outcomes:
            return failed_response(
                META.id,
                "None of the applicable models could be fitted to the data.",
                warnings=warnings,
            )
        steps.append(
            Step(
                title="Model comparison",
                latex=r"\text{The models are ranked by } \text{SSE} \text{ (smallest is best).}",
                note="A lower SSE means a closer overall fit to the data.",
            )
        )

    tables: list[DataTable] = [node_table(xs, ys, decimals)]
    if primary.key in REDUCIBLE:
        tables.append(transformed_table(primary, xs, ys, decimals))
    tables.append(sums_table(primary, decimals))
    tables.append(residual_table(primary, xs, ys, decimals))
    tables.append(statistics_table(primary, count, decimals))
    if targets:
        tables.append(predictions_table(targets, prediction_values, decimals))
    if compare:
        tables.append(ranking_table(outcomes, decimals))

    if compare:
        positive = any(outcome.positive_x for outcome in outcomes)
        grid = sample_grid(xs, targets, positive_x=positive)
        curves = [
            (outcome.label, (grid.tolist(), outcome_curve(outcome, grid)))
            for outcome in outcomes
        ]
        finite_targets = [float(value) for value in prediction_values if value is not None]
        marker_values = finite_targets if (targets and len(finite_targets) == len(targets)) else None
        plot = overlay_plot(
            xs=xs,
            ys=ys,
            curves=curves,
            targets=targets,
            target_values=marker_values,
            title="Model comparison",
        )
    else:
        grid = sample_grid(xs, targets, positive_x=primary.positive_x)
        plot = fit_residual_plot(
            xs=xs,
            ys=ys,
            grid=grid,
            curve=outcome_curve(primary, grid),
            residuals=residual_series(primary, xs, ys),
            targets=targets,
            target_values=prediction_values,
            title=f"Least-squares fit: {primary.label}",
        )

    result: dict[str, Any] = {
        "fit_type": primary.key,
        "model": primary.label,
        "parameters": primary.params,
        "equation": primary.equation_plain,
        "sse": primary.sse,
        "r_squared": primary.r_squared,
        "rmse": primary.rmse,
        "n": count,
        "degree": primary.poly_degree,
        "targets": targets,
        "predictions": prediction_values,
    }
    if compare:
        best = min(outcomes, key=lambda outcome: outcome.sse)
        result["best_model"] = best.label
        result["ranking"] = [
            {
                "model": outcome.label,
                "sse": outcome.sse,
                "r_squared": outcome.r_squared,
                "rmse": outcome.rmse,
            }
            for outcome in sorted(outcomes, key=lambda outcome: outcome.sse)
        ]

    steps.append(
        Step(
            title="Result",
            latex=(
                primary.equation_latex
                + r"\\[1mm] \text{SSE} = "
                + format_num(primary.sse, decimals)
                + r",\quad R^2 = "
                + (
                    r"\text{n/a}"
                    if primary.r_squared is None
                    else format_num(primary.r_squared, decimals)
                )
                + r",\quad \text{RMSE} = "
                + format_num(primary.rmse, decimals)
            ),
            note=f"Fitted with the {primary.label.lower()} model to {count} points.",
        )
    )

    return SolveResponse(
        method=META.id,
        status=SolveStatus.CONVERGED,
        result=result,
        steps=steps,
        tables=tables,
        plot=plot,
        warnings=warnings,
    )
