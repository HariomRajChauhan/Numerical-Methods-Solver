"""Schema-driven input validation.

The frontend renders forms from a method's ``input_schema``; this module
enforces the same schema on the way back in so solvers can trust their inputs.
Every failure is an :class:`InvalidInputError` with a student-friendly message.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.errors import InvalidInputError
from app.core.models import (
    INTEGER_FIELD_TYPES,
    NUMERIC_FIELD_TYPES,
    InputField,
    MethodMeta,
    SolverLimits,
)
from app.core.parser import parse_expression

MAX_TEXT_LENGTH: int = 2000
MAX_DATA_POINTS: int = 5_000
MAX_VECTOR_LENGTH: int = 5_000

_TEXT_FIELD_TYPES = frozenset({"text", "select"})
_JSON_NUMBER = (int, float)


def validate_inputs(meta: MethodMeta, data: Any, limits: SolverLimits) -> dict[str, Any]:
    """Validate and normalise a raw request payload against ``meta.input_schema``.

    Args:
        meta: Registered method metadata.
        data: Raw JSON object submitted by the client.
        limits: Runtime safety limits (matrix size etc.).

    Returns:
        A dict of normalised values keyed by field key.

    Raises:
        InvalidInputError: If a field is missing, malformed or out of range.
    """
    if not isinstance(data, dict):
        raise InvalidInputError("The request body must be a JSON object of input values.")

    cleaned: dict[str, Any] = {}
    for field in meta.input_schema:
        raw = data.get(field.key)
        if _is_missing(field, raw):
            if field.default is not None:
                cleaned[field.key] = _coerce(field, field.default, limits)
                continue
            if field.required:
                raise InvalidInputError(
                    f"'{field.label}' is required.",
                    hint=field.help or None,
                )
            cleaned[field.key] = None
            continue
        cleaned[field.key] = _coerce(field, raw, limits)
    return cleaned


def _is_missing(field: InputField, raw: Any) -> bool:
    if raw is None:
        return True
    return bool(isinstance(raw, str) and not raw.strip() and field.type not in _TEXT_FIELD_TYPES)


def _coerce(field: InputField, raw: Any, limits: SolverLimits) -> Any:
    """Dispatch coercion by field type."""
    if field.type in NUMERIC_FIELD_TYPES:
        return _as_float(field, raw)
    if field.type in INTEGER_FIELD_TYPES:
        return _as_int(field, raw)
    if field.type == "boolean":
        return _as_bool(field, raw)
    if field.type == "select":
        return _as_select(field, raw)
    if field.type == "function":
        return _as_function(field, raw)
    if field.type == "vector":
        return _as_vector(field, raw)
    if field.type == "data_points":
        return _as_data_points(field, raw)
    if field.type == "matrix":
        return _as_matrix(field, raw, limits)
    return _as_text(field, raw)


def _as_float(field: InputField, raw: Any) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (str, *_JSON_NUMBER)):
        raise InvalidInputError(f"'{field.label}' must be a number.")
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(f"'{field.label}' must be a number, got {raw!r}.") from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise InvalidInputError(f"'{field.label}' must be a finite number.")
    if field.min is not None and value < field.min:
        raise InvalidInputError(f"'{field.label}' must be at least {field.min}.")
    if field.max is not None and value > field.max:
        raise InvalidInputError(f"'{field.label}' must be at most {field.max}.")
    return value


def _as_int(field: InputField, raw: Any) -> int:
    value = _as_float(field, raw)
    if float(value).is_integer():
        return int(value)
    raise InvalidInputError(f"'{field.label}' must be a whole number.")


def _as_bool(field: InputField, raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise InvalidInputError(f"'{field.label}' must be true or false.")


def _as_select(field: InputField, raw: Any) -> str:
    value = str(raw).strip()
    allowed = {option.value for option in field.options}
    if allowed and value not in allowed:
        shown = ", ".join(sorted(allowed))
        raise InvalidInputError(f"'{field.label}' must be one of: {shown}.")
    return value


def _as_text(field: InputField, raw: Any) -> str:
    text = raw.strip() if isinstance(raw, str) else str(raw).strip()
    if not text and field.required:
        raise InvalidInputError(f"'{field.label}' is required.")
    if len(text) > MAX_TEXT_LENGTH:
        raise InvalidInputError(f"'{field.label}' is too long (limit {MAX_TEXT_LENGTH}).")
    return text


def _as_function(field: InputField, raw: Any) -> str:
    if not isinstance(raw, str):
        raise InvalidInputError(f"'{field.label}' must be a function, e.g. x^2 - 2.")
    text = raw.strip()
    # ``variable`` may list several names separated by commas (e.g. "x, y" for
    # an ODE right-hand side f(x, y)); a single name is the common case.
    variables = tuple(
        part for part in re.split(r"[,\s]+", field.variable or "x") if part
    )
    # Parse early so the student gets an immediate, friendly syntax error.
    parse_expression(text, variables)
    return text


def _as_vector(field: InputField, raw: Any) -> list[float]:
    if isinstance(raw, str):
        tokens = [token for token in re.split(r"[,\s;]+", raw.strip()) if token]
        values: list[Any] = tokens
    elif isinstance(raw, (list, tuple)):
        values = list(raw)
    else:
        raise InvalidInputError(f"'{field.label}' must be a list of numbers.")
    if not values:
        raise InvalidInputError(f"'{field.label}' must contain at least one number.")
    if len(values) > MAX_VECTOR_LENGTH:
        raise InvalidInputError(
            f"'{field.label}' has too many values (limit {MAX_VECTOR_LENGTH})."
        )
    return [_to_number(field, value) for value in values]


def _as_data_points(field: InputField, raw: Any) -> list[list[float]]:
    points: list[list[float]] = []
    if isinstance(raw, str):
        for chunk in re.split(r"[;\n]+", raw.strip()):
            if not chunk.strip():
                continue
            parts = [part for part in re.split(r"[,\s]+", chunk.strip()) if part]
            if len(parts) != 2:
                raise InvalidInputError(
                    f"'{field.label}': each point must be 'x,y'.",
                    hint="Example: 0,1; 1,2; 2,5",
                )
            points.append([_to_number(field, part) for part in parts])
    elif isinstance(raw, dict):
        # Convenience form: {"x": [...], "y": [...]}
        x_axis = raw.get("x")
        y_axis = raw.get("y")
        if not isinstance(x_axis, (list, tuple)) or not isinstance(y_axis, (list, tuple)):
            raise InvalidInputError(f"'{field.label}': expected 'x' and 'y' lists.")
        if len(x_axis) != len(y_axis):
            raise InvalidInputError(
                f"'{field.label}': the x and y lists must have the same length."
            )
        points = [
            [_to_number(field, x), _to_number(field, y)]
            for x, y in zip(x_axis, y_axis, strict=True)
        ]
    elif isinstance(raw, (list, tuple)):
        for item in raw:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise InvalidInputError(
                    f"'{field.label}': each point must be an [x, y] pair.",
                    hint="Example: [[0, 1], [1, 2], [2, 5]]",
                )
            points.append([_to_number(field, item[0]), _to_number(field, item[1])])
    else:
        raise InvalidInputError(f"'{field.label}' must be a list of [x, y] points.")

    if len(points) < 2:
        raise InvalidInputError(f"'{field.label}' needs at least two points.")
    if len(points) > MAX_DATA_POINTS:
        raise InvalidInputError(
            f"'{field.label}' has too many points (limit {MAX_DATA_POINTS})."
        )
    return points


def _as_matrix(field: InputField, raw: Any, limits: SolverLimits) -> list[list[float]]:
    rows: list[list[float]] = []
    if isinstance(raw, str):
        for chunk in re.split(r"[;\n]+", raw.strip()):
            if not chunk.strip():
                continue
            parts = [part for part in re.split(r"[,\s]+", chunk.strip()) if part]
            rows.append([_to_number(field, part) for part in parts])
    elif isinstance(raw, (list, tuple)):
        for item in raw:
            if isinstance(item, (list, tuple)):
                rows.append([_to_number(field, value) for value in item])
            else:
                raise InvalidInputError(f"'{field.label}' must be a 2-D grid of numbers.")
    else:
        raise InvalidInputError(f"'{field.label}' must be a 2-D grid of numbers.")

    if not rows or not rows[0]:
        raise InvalidInputError(f"'{field.label}' must not be empty.")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise InvalidInputError(f"'{field.label}': all rows must have the same number of columns.")
    if len(rows) > limits.max_matrix_size or width > limits.max_matrix_size:
        raise InvalidInputError(
            f"'{field.label}' is too large "
            f"(max {limits.max_matrix_size}x{limits.max_matrix_size})."
        )
    return rows


def _to_number(field: InputField, raw: Any) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (str, *_JSON_NUMBER)):
        raise InvalidInputError(f"'{field.label}' must contain numbers only.")
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(
            f"'{field.label}' must contain numbers only, got {raw!r}."
        ) from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise InvalidInputError(f"'{field.label}' must contain finite numbers only.")
    return value
