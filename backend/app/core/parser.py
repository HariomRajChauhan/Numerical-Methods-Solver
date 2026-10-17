"""Safe mathematical expression parsing.

User input is never executed. Expressions go through SymPy's ``parse_expr``
with an explicit whitelist of symbols, functions and constants, standard plus
implicit-multiplication and ``^``-as-power transformations, and a set of
pre-parse character/size guards. Anything else raises :class:`ExpressionError`.
"""

from __future__ import annotations

import ast as pyast
import math
import re
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    standard_transformations,
)
from sympy.parsing.sympy_parser import parse_expr as _sympy_parse_expr

from app.core.errors import EvaluationError, ExpressionError

MAX_EXPRESSION_LENGTH: int = 300
MAX_NUMERIC_LITERAL_DIGITS: int = 9
MAX_POW_EXPONENT_DIGITS: int = 3
# Numeric-magnitude guards (see _guard_numeric_explosion): exponent values up
# to 10^6 and constant results up to 10^1000 are plenty for numerical methods
# while making integer bombs impossible to express.
MAX_POW_EXPONENT_LOG10: float = 6.0
MAX_FACTORIAL_ARGUMENT: int = 1_000
MAX_EXPR_LOG10: float = 1_000.0

# standard_transformations: auto_number / auto_symbol / factorial / repeated_decimals
# implicit_multiplication_application: 2x -> 2*x, x(x+1) -> x*(x+1)
# convert_xor: x^2 -> x**2
_TRANSFORMATIONS = (*standard_transformations, implicit_multiplication_application, convert_xor)

# Characters with no place in an arithmetic expression; also the building
# blocks of every python sandbox-escape attempt. '^' stays allowed (convert_xor).
_FORBIDDEN_CHARS = frozenset("_\"'`;[]{}@#$%&|~!?\\<>=")

_INTEGER_LITERAL_RE = re.compile(r"\d+")
_POW_EXPONENT_RE = re.compile(r"(?:\*\*|\^)\s*(\d+)")
_FLOAT_MASK_RE = re.compile(r"\d+\.\d+")

# Multi-character replacements (str.maketrans is 1:1 only).
_UNICODE_SEQUENCES: tuple[tuple[str, str], ...] = (
    ("\u221a(", "sqrt("),  # square-root sign before an opening bracket
)

# Characters students often paste from word processors / other maths software.
# They are folded into their ASCII equivalents before the forbidden-char guard
# so friendly input like "4-x" typed as "4-x" (unicode minus) still works.
_UNICODE_OPERATORS = str.maketrans(
    {
        "\u2212": "-",  # minus sign
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u00d7": "*",  # multiplication sign
        "\u22c5": "*",  # dot operator
        "\u00b7": "*",  # middle dot
        "\u2219": "*",  # bullet operator
        "\u00f7": "/",  # division sign
        "\u2044": "/",  # fraction slash
        "\u03c0": "pi",  # greek small letter pi
        "\u00a0": " ",  # non-breaking space
    }
)

# Unicode superscript digits, e.g. x^2 written as x-superscript-two.
_SUPERSCRIPT_DIGITS = {
    "\u2070": "0",
    "\u00b9": "1",
    "\u00b2": "2",
    "\u00b3": "3",
    "\u2074": "4",
    "\u2075": "5",
    "\u2076": "6",
    "\u2077": "7",
    "\u2078": "8",
    "\u2079": "9",
}


def _normalize(text: str) -> str:
    """Fold common unicode maths notation into the ASCII the parser expects."""
    normalized = text
    for source, target in _UNICODE_SEQUENCES:
        normalized = normalized.replace(source, target)
    normalized = normalized.translate(_UNICODE_OPERATORS)
    if not any(char in _SUPERSCRIPT_DIGITS for char in normalized):
        return normalized
    out: list[str] = []
    index = 0
    length = len(normalized)
    while index < length:
        char = normalized[index]
        if char in _SUPERSCRIPT_DIGITS:
            digits: list[str] = []
            while index < length and normalized[index] in _SUPERSCRIPT_DIGITS:
                digits.append(_SUPERSCRIPT_DIGITS[normalized[index]])
                index += 1
            out.append("^" + "".join(digits))
        else:
            out.append(char)
            index += 1
    return "".join(out)

# Whitelisted elementary functions (SymPy attribute names).
_FUNCTION_NAMES: tuple[str, ...] = (
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "acot", "asec", "acsc",
    "sinh", "cosh", "tanh", "coth",
    "asinh", "acosh", "atanh",
    "sqrt", "cbrt", "exp", "log", "Abs", "sign",
    "floor", "ceiling", "factorial", "Min", "Max",
)

# Aliases students expect: e/pi constants, ln = natural log, log10.
_CONSTANT_NAMES: dict[str, str] = {"pi": "pi", "E": "E", "e": "E"}
_EXTRA_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "ln": sp.log,
    "log10": lambda arg: sp.log(arg, 10),
}


def _build_namespace() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the (local, global) dictionaries handed to SymPy's parser.

    ``local_dict`` holds every allowed function/constant name so the parser
    never auto-symbolises them. ``global_dict`` is a minimal whitelist of the
    SymPy constructors the parser's own transformations rely on.
    """
    local_dict: dict[str, Any] = {}
    for name in _FUNCTION_NAMES:
        obj = getattr(sp, name, None)
        if obj is not None:
            local_dict[name] = obj
    local_dict.update(_EXTRA_FUNCTIONS)
    for alias, target in _CONSTANT_NAMES.items():
        local_dict[alias] = getattr(sp, target)
    global_dict: dict[str, Any] = {
        "Symbol": sp.Symbol,
        "Integer": sp.Integer,
        "Float": sp.Float,
        "Rational": sp.Rational,
        "Add": sp.Add,
        "Mul": sp.Mul,
        "Pow": sp.Pow,
        "Tuple": sp.Tuple,
    }
    return local_dict, global_dict


_LOCAL_DICT, _GLOBAL_DICT = _build_namespace()


def _check_raw_text(text: str) -> None:
    """Cheap syntactic guards applied before SymPy sees the text."""
    if not text or not text.strip():
        raise ExpressionError("The expression is empty.", hint="Example: x^3 - x - 1")
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ExpressionError(
            f"The expression is too long (limit {MAX_EXPRESSION_LENGTH} characters).",
        )
    offending = sorted({ch for ch in text if ch in _FORBIDDEN_CHARS})
    if offending:
        shown = ", ".join(repr(ch) for ch in offending)
        raise ExpressionError(
            f"Unsupported character(s) in the expression: {shown}.",
            hint="Use only numbers, the variable, operators (+ - * / ^), parentheses and whitelisted functions.",
        )
    # Digits of a literal: ignore the fractional part of floats.
    for literal in _INTEGER_LITERAL_RE.findall(_FLOAT_MASK_RE.sub("", text)):
        if len(literal) > MAX_NUMERIC_LITERAL_DIGITS:
            raise ExpressionError(
                f"Number {literal} has too many digits (limit {MAX_NUMERIC_LITERAL_DIGITS}).",
            )
    for exponent in _POW_EXPONENT_RE.findall(text):
        if len(exponent) > MAX_POW_EXPONENT_DIGITS:
            raise ExpressionError(
                f"Exponent {exponent} is too large (limit {MAX_POW_EXPONENT_DIGITS} digits).",
            )


class _NumberTooLarge(Exception):
    """Internal: a constant subexpression exceeds the numeric budget."""


_NEG_INF = float("-inf")


def _log10_bound(node: pyast.AST) -> float:
    """Conservative upper bound on log10(|value|) of a numeric subexpression.

    Returns ``+inf`` for symbolic (unknown) parts, which are always allowed —
    only provably enormous constant arithmetic is rejected. Raises
    :class:`_NumberTooLarge` for constant powers/factorials past the budget.
    """
    if isinstance(node, pyast.Constant):
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return float("inf")
        if value == 0:
            return _NEG_INF
        return math.log10(abs(float(value)))
    if isinstance(node, pyast.UnaryOp) and isinstance(node.op, (pyast.USub, pyast.UAdd)):
        return _log10_bound(node.operand)
    if isinstance(node, pyast.BinOp):
        left = _log10_bound(node.left)
        right = _log10_bound(node.right)
        if isinstance(node.op, pyast.Pow):
            if math.isfinite(right) and right > MAX_POW_EXPONENT_LOG10:
                raise _NumberTooLarge(
                    "Exponents above 10^6 are not allowed in an expression.",
                )
            if left == _NEG_INF:
                return _NEG_INF
            if math.isfinite(left) and math.isfinite(right):
                exponent = math.pow(10.0, right)
                return exponent * left
            return float("inf")
        if isinstance(node.op, (pyast.Mult, pyast.FloorDiv)):
            if math.isfinite(left) and math.isfinite(right):
                return left + right
            return float("inf")
        if isinstance(node.op, (pyast.Add, pyast.Sub)):
            if math.isfinite(left) and math.isfinite(right):
                return max(left, right) + 1.0
            return float("inf")
        if isinstance(node.op, pyast.Div):
            if right == _NEG_INF:
                return float("inf")
            if math.isfinite(left) and math.isfinite(right):
                return left - right
            return float("inf")
        return float("inf")
    if isinstance(node, pyast.Call):
        callee = node.func
        if (
            isinstance(callee, pyast.Name)
            and callee.id == "factorial"
            and len(node.args) == 1
            and isinstance(node.args[0], pyast.Constant)
            and isinstance(node.args[0].value, int)
            and not isinstance(node.args[0].value, bool)
        ):
            argument = node.args[0].value
            if argument < 0:
                return float("inf")
            if argument > MAX_FACTORIAL_ARGUMENT:
                raise _NumberTooLarge(
                    f"factorial() of numbers above {MAX_FACTORIAL_ARGUMENT} is not allowed.",
                )
            return math.lgamma(argument + 1) / math.log(10)
        return float("inf")
    return float("inf")


def _guard_numeric_explosion(text: str) -> None:
    """Reject constant arithmetic that would blow up memory or CPU at parse time."""
    try:
        tree = pyast.parse(text.replace("^", "**").strip(), mode="eval")
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return  # SymPy will raise the friendly syntax error itself
    try:
        bound = _log10_bound(tree.body)
    except _NumberTooLarge as exc:
        raise ExpressionError(str(exc)) from None
    if math.isfinite(bound) and bound > MAX_EXPR_LOG10:
        raise ExpressionError(
            "The numeric value of this expression is far too large "
            f"(over 10^{int(MAX_EXPR_LOG10)}).",
        )


def parse_expression(text: str, variables: Sequence[str] = ("x",)) -> sp.Expr:
    """Safely parse ``text`` into a SymPy expression.

    Args:
        text: Raw user expression, e.g. ``"x^2 + 2x + 1"``.
        variables: Symbol names the expression is allowed to contain.

    Returns:
        The parsed SymPy expression.

    Raises:
        ExpressionError: If the text fails any guard or is not valid math.
    """
    text = _normalize(text)
    _check_raw_text(text)
    _guard_numeric_explosion(text)
    try:
        expr = _sympy_parse_expr(
            text,
            local_dict=dict(_LOCAL_DICT),
            global_dict=dict(_GLOBAL_DICT),
            transformations=_TRANSFORMATIONS,
        )
    except Exception as exc:  # SymPy raises a grab-bag of types for hostile input.
        raise ExpressionError(
            "Could not understand the expression.",
            hint="Check the syntax — e.g. use ^ for powers and * for products like 2*x.",
        ) from exc

    if not isinstance(expr, sp.Expr):
        raise ExpressionError("The input must be a single mathematical expression.")
    if expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise ExpressionError(
            "The expression contains an undefined constant value.",
            hint="Check for division by zero or an out-of-domain constant (e.g. log(0)).",
        )

    allowed_symbols = {sp.Symbol(name) for name in variables}
    unknown = sorted(str(symbol) for symbol in expr.free_symbols - allowed_symbols)
    if unknown:
        raise ExpressionError(
            f"Unknown symbol(s): {', '.join(unknown)}.",
            hint=f"This method expects a function of {', '.join(variables)}.",
        )
    undefined = expr.atoms(AppliedUndef)
    if undefined:
        names = sorted(str(fn) for fn in undefined)
        raise ExpressionError(
            f"Unknown function(s): {', '.join(names)}.",
            hint="Only the whitelisted functions listed in the field help are allowed.",
        )
    return expr


def expr_to_latex(expr: sp.Expr) -> str:
    """Render a parsed expression as a KaTeX-compatible LaTeX string."""
    return str(sp.latex(expr))


def parse_function(
    text: str,
    variables: Sequence[str] = ("x",),
    *,
    strict: bool = True,
) -> Callable[..., Any]:
    """Parse and lambdify in one step (the common case for solvers)."""
    return make_function(parse_expression(text, variables), variables, strict=strict)


def make_function(
    expr: sp.Expr,
    variables: Sequence[str] = ("x",),
    *,
    strict: bool = True,
) -> Callable[..., Any]:
    """Lambdify a SymPy expression into a NumPy-backed callable.

    Args:
        expr: Parsed expression.
        variables: Bound symbol order.
        strict: When ``True`` (default) non-finite results raise
            :class:`EvaluationError`; otherwise ``nan`` is returned (used for
            plot sampling across domain gaps).

    Returns:
        A callable mirroring ``variables``' arity; scalar in → float out,
        array in → ``numpy.ndarray`` out.
    """
    raw = sp.lambdify(variables, expr, modules="numpy")
    latex = expr_to_latex(expr)

    def wrapped(*args: Any) -> Any:
        if len(args) != len(variables):
            raise TypeError(f"Expected {len(variables)} argument(s), got {len(args)}")
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            try:
                value = raw(*args)
            except (ZeroDivisionError, FloatingPointError, ValueError, TypeError) as exc:
                if strict:
                    raise EvaluationError(
                        f"The expression is undefined at the given point (f = {latex}).",
                        hint="Check the domain — e.g. no division by zero, no log of a negative number.",
                    ) from exc
                value = np.nan
        array = np.asarray(value, dtype=float)
        if strict and not np.all(np.isfinite(array)):
            point = ", ".join(
                f"{name}={arg!r}" for name, arg in zip(variables, args, strict=True)
            )
            raise EvaluationError(
                f"The expression is undefined at {point} (result is not a finite number).",
                hint="Check the domain — e.g. division by zero or a root of a negative number.",
            )
        if array.ndim == 0:
            return float(array)
        return array

    return wrapped
