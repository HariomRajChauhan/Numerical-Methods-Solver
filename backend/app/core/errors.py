"""Domain errors and FastAPI exception handlers.

Every user-facing failure carries a short, friendly message plus an optional
hint; raw stack traces are never returned to the client.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("nms.errors")


class NMSBaseError(Exception):
    """Base class for all errors that are safe to show to the user."""

    code: str = "error"
    status_code: int = 400

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def to_payload(self) -> dict[str, Any]:
        """JSON body returned to the client."""
        payload: dict[str, Any] = {"detail": self.message, "code": self.code}
        if self.hint:
            payload["hint"] = self.hint
        return payload


class ExpressionError(NMSBaseError):
    """The user's mathematical expression could not be parsed safely."""

    code = "expression_error"
    status_code = 400


class InvalidInputError(NMSBaseError):
    """A payload field is missing, malformed or out of range."""

    code = "invalid_input"
    status_code = 400


class EvaluationError(NMSBaseError):
    """A parsed expression is undefined at a requested point."""

    code = "evaluation_error"
    status_code = 400


class MethodNotFoundError(NMSBaseError):
    """No solver is registered under the requested method id."""

    code = "method_not_found"
    status_code = 404


class MethodUnavailableError(NMSBaseError):
    """The method exists in the syllabus but is not implemented yet (stub)."""

    code = "method_unavailable"
    status_code = 409


class SolverTimeoutError(NMSBaseError):
    """The solver exceeded the configured wall-clock budget."""

    code = "timeout"
    status_code = 408


class RegistrationError(NMSBaseError):
    """A solver registration violated registry invariants."""

    code = "registration_error"
    status_code = 500


def _error_response(status_code: int, payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload)


def _nms_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, NMSBaseError)
    return _error_response(exc.status_code, exc.to_payload())


def _http_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    payload: dict[str, Any] = {"detail": str(exc.detail), "code": f"http_{exc.status_code}"}
    return _error_response(exc.status_code, payload)


def _validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    first = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    field = f"'{location}'" if location else "request"
    message = f"Invalid value for {field}: {first.get('msg', 'validation failed')}"
    return _error_response(
        422,
        {"detail": message, "code": "validation_error", "hint": "Check the highlighted input field."},
    )


def _rate_limit_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)
    return _error_response(
        429,
        {
            "detail": "Too many requests — please wait a moment and try again.",
            "code": "rate_limited",
            "hint": f"Limit: {exc.detail}.",
        },
    )


def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _error_response(
        500,
        {
            "detail": "Something went wrong while solving the problem. Please try again.",
            "code": "internal_error",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all friendly error handlers (and the rate-limit handler) to an app."""
    app.add_exception_handler(NMSBaseError, _nms_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
