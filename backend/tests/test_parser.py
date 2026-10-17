"""Tests for the safe expression parser: accepted forms, rejections, evaluation."""

from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from app.core.errors import EvaluationError, ExpressionError
from app.core.parser import (
    MAX_EXPRESSION_LENGTH,
    expr_to_latex,
    make_function,
    parse_expression,
)


class TestParseValid:
    """Normal cases: everyday student expressions must just work."""

    @pytest.mark.parametrize(
        ("text", "expected_latex"),
        [
            ("x^2 + 2x + 1", "x^{2} + 2 x + 1"),
            ("x^3 - x - 1", "x^{3} - x - 1"),
            ("2^10", "1024"),
            ("sin(x) + cos(x)", "\\sin{\\left(x \\right)} + \\cos{\\left(x \\right)}"),
            ("e^x", "e^{x}"),
            ("ln(x)", "\\log{\\left(x \\right)}"),
            ("sqrt(x)", "\\sqrt{x}"),
            ("pi*x", "\\pi x"),
        ],
    )
    def test_parses_and_renders_latex(self, text: str, expected_latex: str) -> None:
        expr = parse_expression(text)
        assert isinstance(expr, sp.Expr)
        assert expr_to_latex(expr) == expected_latex

    def test_implicit_multiplication(self) -> None:
        fn = make_function(parse_expression("2x"))
        assert fn(3) == pytest.approx(6.0)

    def test_caret_is_power(self) -> None:
        fn = make_function(parse_expression("x^3"))
        assert fn(2.0) == pytest.approx(8.0)

    def test_parses_in_two_variables(self) -> None:
        expr = parse_expression("x + 2y", ("x", "y"))
        fn = make_function(expr, ("x", "y"))
        assert fn(1.0, 2.0) == pytest.approx(5.0)


class TestParseRejects:
    """Edge and failure cases: hostile or malformed input must be rejected."""

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "__import__('os')",
            "x; import os",
            "exec('print(1)')",
            "os.system('ls')",
            "x.__class__",
            "q + 1",
            "f(x)",
            "(x",
            "x + [1]",
            "x @ 2",
            "x = 5",
            "1/0",
            "x**10**9",
            "(10^9)^(10^9)",
            "2**10**9",
            "factorial(999999)",
            "2**factorial(999)",
            "log(0) + x",
            "9" * (MAX_EXPRESSION_LENGTH + 1),
            "1" * 15,  # more than 9 digits in one literal
            "x^12345",  # exponent with too many digits
        ],
    )
    def test_raises_expression_error(self, text: str) -> None:
        with pytest.raises(ExpressionError):
            parse_expression(text)

    def test_unknown_symbol_message_is_friendly(self) -> None:
        with pytest.raises(ExpressionError, match="Unknown symbol"):
            parse_expression("q^2 + 1")

    def test_symbol_outside_allowed_variables(self) -> None:
        with pytest.raises(ExpressionError, match="Unknown symbol"):
            parse_expression("x + y", ("x",))


class TestUnicodeNormalization:
    """Word-processor input (unicode minus, superscripts, symbols) is folded to ASCII."""

    def test_unicode_minus_and_superscript(self) -> None:
        expr = parse_expression("4\u2212x\u00b2", ("x",))
        x = sp.Symbol("x")
        assert sp.simplify(expr - (4 - x**2)) == 0

    def test_superscript_with_two_digits(self) -> None:
        expr = parse_expression("x\u00b2\u00b3", ("x",))
        assert sp.simplify(expr - sp.Symbol("x") ** 23) == 0

    def test_unicode_times_and_pi(self) -> None:
        fn = make_function(parse_expression("2\u00d7\u03c0", ("x",)))
        assert fn(0.0) == pytest.approx(2 * np.pi)

    def test_square_root_sign_before_bracket(self) -> None:
        fn = make_function(parse_expression("\u221a(4-x)", ("x",)))
        assert fn(0.0) == pytest.approx(2.0)

    def test_equals_sign_is_still_rejected(self) -> None:
        with pytest.raises(ExpressionError):
            parse_expression("x = 5")


class TestMakeFunction:
    """Evaluation behaviour, including the non-strict (plot) mode."""

    def test_scalar_evaluation(self) -> None:
        fn = make_function(parse_expression("x^2 - 2"))
        assert fn(2.0) == pytest.approx(2.0)
        assert isinstance(fn(2.0), float)

    def test_array_evaluation(self) -> None:
        fn = make_function(parse_expression("x^2"))
        out = fn(np.array([1.0, 2.0, 3.0]))
        assert out == pytest.approx(np.array([1.0, 4.0, 9.0]))

    def test_strict_mode_raises_on_undefined_point(self) -> None:
        fn = make_function(parse_expression("1/x"))
        with pytest.raises(EvaluationError, match="undefined"):
            fn(0.0)

    def test_non_strict_mode_returns_nan(self) -> None:
        fn = make_function(parse_expression("1/x"), strict=False)
        assert np.isnan(fn(0.0))

    def test_wrong_arity_raises_type_error(self) -> None:
        fn = make_function(parse_expression("x + y", ("x", "y")))
        with pytest.raises(TypeError):
            fn(1.0)
