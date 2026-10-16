"""PDF report builder (reportlab).

Renders a solved problem into a printable, exam-style report: the problem
statement, the final answer, error/convergence metrics, the step-by-step
working, iteration tables, pseudocode and the Python source.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.models import MethodMeta, SolveResponse

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_SLATE_900 = colors.HexColor("#0f172a")
_SLATE_500 = colors.HexColor("#64748b")
_INDIGO = colors.HexColor("#3730a3")
_LINE = colors.HexColor("#cbd5e1")
_HEADER_BG = colors.HexColor("#eef2ff")

_TITLE = ParagraphStyle("NmsTitle", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=_SLATE_900)
_SUBTITLE = ParagraphStyle("NmsSubtitle", fontName="Helvetica", fontSize=9, leading=12, textColor=_SLATE_500)
_HEADING = ParagraphStyle(
    "NmsHeading",
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=15,
    spaceBefore=10,
    spaceAfter=4,
    textColor=_INDIGO,
)
_BODY = ParagraphStyle("NmsBody", fontName="Helvetica", fontSize=9.5, leading=13, textColor=_SLATE_900)
_STEP_TITLE = ParagraphStyle(
    "NmsStepTitle",
    fontName="Helvetica-Bold",
    fontSize=9.5,
    leading=13,
    spaceBefore=5,
    textColor=_SLATE_900,
)
_MONO = ParagraphStyle("NmsMono", fontName="Courier", fontSize=8, leading=11, textColor=_SLATE_900)
_PRE = ParagraphStyle("NmsPre", fontName="Courier", fontSize=7.5, leading=9.5, textColor=_SLATE_900)

# ---------------------------------------------------------------------------
# LaTeX -> readable plain text (best effort; PDF cannot typeset KaTeX)
# ---------------------------------------------------------------------------

_SYMBOLS: tuple[tuple[str, str], ...] = (
    (r"\times", "x"),
    (r"\cdot", "."),
    (r"\approx", "~="),
    (r"\Rightarrow", "=>"),
    (r"\rightarrow", "->"),
    (r"\leq", "<="),
    (r"\geq", ">="),
    (r"\pm", "+/-"),
    (r"\infty", "inf"),
)


def _latex_to_text(latex: str) -> str:
    """Turn a small LaTeX subset into readable monospaced text for the PDF."""
    text = latex.replace("\\\\", "\n")
    text = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", text)
    text = re.sub(r"\\text\{([^{}]*)\}", r"\1", text)
    for command, replacement in _SYMBOLS:
        text = text.replace(command, replacement)
    text = re.sub(r"\\(left|right|,|;|!|quad|qquad)", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _format_value(value: Any) -> str:
    """Compact string for one value (numbers with 10 significant digits)."""
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


# ---------------------------------------------------------------------------
# Flowable helpers
# ---------------------------------------------------------------------------


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), _INDIGO),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _info_table(pairs: list[tuple[str, str]], width: float) -> Table:
    data = [[str(key), str(value)] for key, value in pairs]
    table = Table(data, colWidths=[width * 0.35, width * 0.65], hAlign="LEFT")
    table.setStyle(_table_style())
    return table


def _grid_table(columns: list[str], rows: list[list[Any]], width: float) -> Table:
    data: list[list[str]] = [list(columns)]
    data.extend([[_format_value(cell) for cell in row] for row in rows])
    ncols = max(1, len(columns))
    col_width = width / ncols
    table = Table(data, colWidths=[col_width] * ncols, repeatRows=1, hAlign="LEFT")
    table.setStyle(_table_style())
    return table


def _footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_SLATE_500)
    canvas.drawString(18 * mm, 11 * mm, "Numerical Methods Solver")
    canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_pdf(
    meta: MethodMeta,
    response: SolveResponse,
    inputs: dict[str, Any] | None = None,
) -> bytes:
    """Render a full PDF report for ``response`` and return it as bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"{meta.name} - Numerical Methods Solver",
        author="Numerical Methods Solver",
        subject=meta.chapter_title,
    )
    width = doc.width

    story: list[Any] = [
        Paragraph(escape(meta.name), _TITLE),
        Paragraph(escape(f"{meta.chapter_title} - generated {_stamp()} UTC"), _SUBTITLE),
        Spacer(1, 5),
        HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#e2e8f0")),
    ]
    if meta.summary:
        story.append(Spacer(1, 4))
        story.append(Paragraph(escape(meta.summary), _BODY))

    if inputs:
        story.append(Paragraph("Problem", _HEADING))
        story.append(_info_table([(key, _format_value(value)) for key, value in inputs.items()], width))

    story.append(Paragraph("Result", _HEADING))
    story.append(Paragraph(f"Status: <b>{escape(response.status.value)}</b>", _BODY))
    if response.result:
        story.append(Spacer(1, 3))
        story.append(
            _info_table([(key, _format_value(value)) for key, value in response.result.items()], width)
        )

    errors = response.errors
    error_rows = [
        ("Absolute error", errors.absolute),
        ("Relative error (%)", errors.relative_percent),
        ("Order of convergence", errors.order_of_convergence),
    ]
    present = [(label, _format_value(value)) for label, value in error_rows if value is not None]
    if present:
        story.append(Spacer(1, 3))
        story.append(_info_table(present, width))

    if response.warnings:
        story.append(Paragraph("Warnings", _HEADING))
        for warning in response.warnings:
            story.append(Paragraph(f"- {escape(warning)}", _BODY))

    if response.steps:
        story.append(Paragraph("Step-by-step working", _HEADING))
        for step in response.steps:
            story.append(Paragraph(escape(step.title), _STEP_TITLE))
            cleaned = _latex_to_text(step.latex)
            if cleaned:
                html = "<br/>".join(escape(line) for line in cleaned.splitlines())
                story.append(Paragraph(html, _MONO))
            if step.note:
                story.append(Spacer(1, 2))
                story.append(Paragraph(escape(step.note), _BODY))

    for table in response.tables:
        story.append(Paragraph(escape(table.title), _HEADING))
        if table.rows:
            story.append(_grid_table(table.columns, table.rows, width))
        else:
            story.append(Paragraph("(no rows)", _BODY))

    if response.pseudocode:
        story.append(Paragraph("Pseudocode", _HEADING))
        story.append(Preformatted(response.pseudocode, _PRE))

    if response.python_source:
        story.append(Paragraph("Python source", _HEADING))
        story.append(Preformatted(response.python_source, _PRE))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
