"""CSV report builder.

Flattens a :class:`SolveResponse` into a spreadsheet-friendly text file:
a summary header, the final values and error metrics, then every iteration /
difference table. Generated with the standard library ``csv`` module so values
are escaped correctly.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from app.core.models import MethodMeta, SolveResponse


def _format_value(value: Any) -> str:
    """Human-readable, spreadsheet-safe string for one value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.10g}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return ", ".join(f"{key}: {_format_value(item)}" for key, item in value.items())
    if value is None:
        return ""
    return str(value)


def build_csv(meta: MethodMeta, response: SolveResponse) -> str:
    """Render ``response`` as CSV text (header, result, errors, tables)."""
    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Numerical Methods Solver - report"])
    writer.writerow(["Method", meta.name])
    writer.writerow(["Method id", meta.id])
    writer.writerow(["Chapter", meta.chapter_title])
    writer.writerow(["Status", response.status.value])
    writer.writerow([])

    if response.result:
        writer.writerow(["Result"])
        writer.writerow(["Name", "Value"])
        for key, value in response.result.items():
            writer.writerow([key, _format_value(value)])
        writer.writerow([])

    errors = response.errors
    error_rows: list[tuple[str, Any]] = [
        ("absolute_error", errors.absolute),
        ("relative_error_percent", errors.relative_percent),
        ("order_of_convergence", errors.order_of_convergence),
    ]
    if any(value is not None for _, value in error_rows):
        writer.writerow(["Error & convergence"])
        writer.writerow(["Metric", "Value"])
        for label, value in error_rows:
            if value is not None:
                writer.writerow([label, _format_value(value)])
        writer.writerow([])

    if response.warnings:
        writer.writerow(["Warnings"])
        for warning in response.warnings:
            writer.writerow([warning])
        writer.writerow([])

    for index, table in enumerate(response.tables):
        writer.writerow([table.title])
        writer.writerow(table.columns)
        for row in table.rows:
            writer.writerow([_format_value(cell) for cell in row])
        if index != len(response.tables) - 1:
            writer.writerow([])

    return buffer.getvalue()
