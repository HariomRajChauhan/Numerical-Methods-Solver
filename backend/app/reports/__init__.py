"""Report generation (PDF and CSV) for solved problems.

Both builders take the already-enriched :class:`SolveResponse` plus the method
metadata, so they add no maths and can never disagree with the on-screen result.
"""

from __future__ import annotations

from app.reports.csv_report import build_csv
from app.reports.pdf_report import build_pdf

__all__ = ["build_csv", "build_pdf"]
