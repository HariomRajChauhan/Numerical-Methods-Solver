"""Solve endpoint: validate → execute the solver with a deadline → enrich response."""

from __future__ import annotations

import inspect
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Annotated, Any

from fastapi import APIRouter, Body, Request

from app.core import registry
from app.core.config import get_settings
from app.core.errors import MethodUnavailableError, SolverTimeoutError
from app.core.models import SolveResponse, SolverLimits
from app.core.rate_limit import limiter, solve_rate_limit
from app.core.utils import to_builtin
from app.core.validation import validate_inputs

router = APIRouter(tags=["solve"])

# Shared pool: a solver that overruns its deadline cannot be killed (Python),
# but the bounded pool stops runaway requests from spawning unbounded threads.
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="solver")


def _limits() -> SolverLimits:
    settings = get_settings()
    return SolverLimits(
        timeout_seconds=settings.solver_timeout_seconds,
        max_iterations=settings.max_iterations_limit,
        max_matrix_size=settings.max_matrix_size,
    )


def _run_solver(
    entry: registry.MethodEntry,
    inputs: dict[str, Any],
    limits: SolverLimits,
) -> SolveResponse:
    assert entry.solver is not None
    response = entry.solver(inputs, limits)
    if not isinstance(response, SolveResponse):
        response = SolveResponse.model_validate(response)
    if not response.pseudocode:
        response.pseudocode = entry.meta.pseudocode
    if not response.python_source:
        response.python_source = _source_of(entry.solver)
    response.method = entry.meta.id
    return SolveResponse.model_validate(to_builtin(response.model_dump()))


def _source_of(fn: Any) -> str:
    """Best-effort Python source of a solver (used for the downloadable report)."""
    try:
        return inspect.getsource(fn)
    except (OSError, TypeError):
        return ""


PayloadBody = Annotated[dict[str, Any] | None, Body()]


@router.post("/solve/{method_id}", response_model=SolveResponse, summary="Solve a problem")
@limiter.limit(solve_rate_limit)
def solve(
    request: Request,
    method_id: str,
    payload: PayloadBody = None,
) -> SolveResponse:
    """Validate the payload against the method schema, solve it, return the contract."""
    entry = registry.get_entry(method_id)
    if entry.solver is None:
        raise MethodUnavailableError(
            f"'{entry.meta.name}' is on the roadmap but not implemented yet.",
            hint="Only methods marked 'available' can be solved for now.",
        )

    limits = _limits()
    inputs = validate_inputs(entry.meta, payload or {}, limits)

    future = _EXECUTOR.submit(_run_solver, entry, inputs, limits)
    try:
        return future.result(timeout=limits.timeout_seconds)
    except FutureTimeoutError as exc:
        raise SolverTimeoutError(
            f"The computation exceeded the {limits.timeout_seconds:g}s time limit.",
            hint="Reduce the number of iterations or simplify the problem.",
        ) from exc
