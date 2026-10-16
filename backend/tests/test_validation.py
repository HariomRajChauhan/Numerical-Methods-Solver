"""Tests for schema-driven input validation."""

from __future__ import annotations

import pytest

from app.core.errors import ExpressionError, InvalidInputError
from app.core.models import (
    Chapter,
    InputField,
    MethodMeta,
    SelectOption,
    SolverLimits,
)
from app.core.validation import validate_inputs

LIMITS = SolverLimits(timeout_seconds=1.0, max_iterations=100, max_matrix_size=3)

META = MethodMeta(
    id="demo",
    chapter=Chapter.CH1_NONLINEAR,
    name="Demo",
    input_schema=[
        InputField(key="function", label="f(x)", type="function", variable="x"),
        InputField(key="a", label="a", type="number", min=0.0, max=10.0),
        InputField(key="n", label="n", type="integer", default=5, min=1, max=10),
        InputField(key="eps", label="tol", type="tolerance", default=1e-6),
        InputField(key="vector", label="data", type="vector", required=False),
        InputField(key="points", label="points", type="data_points"),
        InputField(key="matrix", label="matrix", type="matrix"),
        InputField(key="mode", label="mode", type="select",
                   options=[SelectOption(value="fast", label="Fast"),
                            SelectOption(value="safe", label="Safe")]),
        InputField(key="verbose", label="verbose", type="boolean", default=False),
        InputField(key="note", label="note", type="text", required=False),
    ],
)

BASE_PAYLOAD = {
    "function": "x^3 - x - 1",
    "a": "1.3",
    "points": "0,1; 1,2; 2,5",
    "matrix": "1,2; 3,4",
    "mode": "fast",
}


def _validate(payload: dict) -> dict:
    return validate_inputs(META, payload, LIMITS)


class TestHappyPath:
    def test_coercion_and_defaults(self) -> None:
        out = _validate(dict(BASE_PAYLOAD))
        assert out["function"] == "x^3 - x - 1"
        assert out["a"] == pytest.approx(1.3)  # string → float
        assert out["n"] == 5  # default applied
        assert out["eps"] == pytest.approx(1e-6)
        assert out["points"] == [[0.0, 1.0], [1.0, 2.0], [2.0, 5.0]]
        assert out["matrix"] == [[1.0, 2.0], [3.0, 4.0]]
        assert out["mode"] == "fast"
        assert out["verbose"] is False

    def test_matrix_accepts_semicolon_string_with_spaces(self) -> None:
        out = _validate({**BASE_PAYLOAD, "matrix": "1 2; 3 4"})
        assert out["matrix"] == [[1.0, 2.0], [3.0, 4.0]]

    def test_vector_accepts_comma_string(self) -> None:
        out = _validate({**BASE_PAYLOAD, "vector": "1, 2, 3"})
        assert out["vector"] == [1.0, 2.0, 3.0]

    def test_points_accepts_x_and_y_lists(self) -> None:
        out = _validate({**BASE_PAYLOAD, "points": {"x": [0, 2], "y": [1, 3]}})
        assert out["points"] == [[0.0, 1.0], [2.0, 3.0]]

    def test_points_accepts_list_of_pairs(self) -> None:
        out = _validate({**BASE_PAYLOAD, "points": [[0, 1], [2, 3]]})
        assert out["points"] == [[0.0, 1.0], [2.0, 3.0]]


class TestFailures:
    def test_non_object_body(self) -> None:
        with pytest.raises(InvalidInputError, match="JSON object"):
            validate_inputs(META, [1, 2, 3], LIMITS)

    def test_required_field_missing(self) -> None:
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "function"}
        with pytest.raises(InvalidInputError, match=r"'f\(x\)' is required"):
            _validate(payload)

    def test_number_out_of_range(self) -> None:
        with pytest.raises(InvalidInputError, match="at most 10"):
            _validate({**BASE_PAYLOAD, "a": 11})

    def test_not_a_number(self) -> None:
        with pytest.raises(InvalidInputError, match="must be a number"):
            _validate({**BASE_PAYLOAD, "a": "banana"})

    def test_whole_number_required(self) -> None:
        with pytest.raises(InvalidInputError, match="whole number"):
            _validate({**BASE_PAYLOAD, "n": "2.5"})

    def test_function_syntax_error_is_expression_error(self) -> None:
        with pytest.raises(ExpressionError):
            _validate({**BASE_PAYLOAD, "function": "x^2 ++"})

    def test_select_rejects_unknown_option(self) -> None:
        with pytest.raises(InvalidInputError, match="one of"):
            _validate({**BASE_PAYLOAD, "mode": "medium"})

    def test_matrix_dimension_guard(self) -> None:
        with pytest.raises(InvalidInputError, match="too large"):
            _validate({**BASE_PAYLOAD, "matrix": "1,2,3,4; 1,2,3,4; 1,2,3,4; 1,2,3,4"})

    def test_points_need_at_least_two(self) -> None:
        with pytest.raises(InvalidInputError, match="at least two points"):
            _validate({**BASE_PAYLOAD, "points": "0,1"})

    def test_points_format_error(self) -> None:
        with pytest.raises(InvalidInputError, match="x,y"):
            _validate({**BASE_PAYLOAD, "points": "0; 1; 2"})

    def test_nan_rejected(self) -> None:
        with pytest.raises(InvalidInputError, match="finite"):
            _validate({**BASE_PAYLOAD, "a": "nan"})
