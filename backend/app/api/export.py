"""Export endpoint: solve (via the shared solve path) then render PDF or CSV.

The report is generated from the same enriched :class:`SolveResponse` the
``/solve`` endpoint returns, so a downloaded file always matches the result
shown on screen.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Query, Request, Response

from app.api.solve import execute_solve
from app.core import registry
from app.core.rate_limit import limiter, solve_rate_limit
from app.reports.csv_report import build_csv
from app.reports.pdf_report import build_pdf

router = APIRouter(tags=["export"])

ExportFormat = Literal["pdf", "csv"]

PayloadBody = Annotated[dict[str, Any] | None, Body()]


def _download(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


@router.post("/export/{method_id}", summary="Download a PDF or CSV report")
@limiter.limit(solve_rate_limit)
def export_report(
    request: Request,
    method_id: str,
    export_format: Annotated[ExportFormat, Query(alias="format")] = "pdf",
    payload: PayloadBody = None,
) -> Response:
    """Re-run the solver and stream back a downloadable report."""
    del request  # required by the rate-limit decorator
    response = execute_solve(method_id, payload)
    meta = registry.get_entry(method_id).meta
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if export_format == "csv":
        return Response(
            content=build_csv(meta, response),
            media_type="text/csv; charset=utf-8",
            headers=_download(f"nms_{method_id}_{stamp}.csv"),
        )

    return Response(
        content=build_pdf(meta, response, payload or {}),
        media_type="application/pdf",
        headers=_download(f"nms_{method_id}_{stamp}.pdf"),
    )
