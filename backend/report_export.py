"""
Report export utilities for the research pipeline.

Exports a research report and critic evaluation to Markdown and PDF.
PDF formatting supports common Markdown structures while safely escaping
text before passing it to ReportLab.
"""

from datetime import datetime
from pathlib import Path
import re
from xml.sax.saxutils import escape
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Preformatted,
    Table,
    TableStyle,
    KeepTogether,
)


# ============================================================
# CONFIGURATION
# ============================================================

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

PAGE_RIGHT_MARGIN = 0.65 * inch
PAGE_LEFT_MARGIN = 0.65 * inch
PAGE_TOP_MARGIN = 0.70 * inch
PAGE_BOTTOM_MARGIN = 0.70 * inch


# ============================================================
# FILENAME AND INPUT HELPERS
# ============================================================

def clean_filename(topic: str) -> str:
    """Create a filesystem-safe filename with a timestamp."""
    topic = str(topic or "").strip()
    name = re.sub(r"[^a-zA-Z0-9]+", "_", topic).strip("_").lower()
    name = name[:60] or "research_report"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{name}_{timestamp}"


def _as_string(value) -> str:
    """Convert None and other values safely to strings."""
    return "" if value is None else str(value)


def _build_markdown(topic: str, report: str, feedback: str) -> str:
    """Build the complete Markdown report."""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return (
        f"# {topic}\n\n"
        f"Generated: {generated_at}\n\n"
        "---\n\n"
        f"{report.rstrip()}\n\n"
        "---\n\n"
        "# Critic Evaluation\n\n"
        f"{feedback.rstrip()}\n"
    )


# ============================================================
# MARKDOWN EXPORT
# ============================================================

def save_markdown(topic: str, report: str, feedback: str) -> Path:
    """Save the report and critic feedback as a UTF-8 Markdown file."""
    topic = _as_string(topic).strip() or "Research Report"
    report = _as_string(report)
    feedback = _as_string(feedback)

    filepath = REPORT_DIR / f"{clean_filename(topic)}.md"
    content = _build_markdown(topic, report, feedback)

    filepath.write_text(content, encoding="utf-8")

    print(f"[EXPORT] Markdown: {filepath.resolve()}")
    return filepath


# ============================================================
# PDF STYLES
# ============================================================

def _make_styles():
    """Create report-specific ReportLab paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ResearchTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=16,
            textColor=colors.HexColor("#172554"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=7,
            splitLongWords=1,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceBefore=12,
            spaceAfter=9,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            spaceBefore=10,
            spaceAfter=7,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchH3",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchBullet",
            parent=styles["ResearchBody"],
            leftIndent=16,
            firstLineIndent=-9,
            bulletIndent=2,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchQuote",
            parent=styles["ResearchBody"],
            leftIndent=18,
            rightIndent=12,
            borderColor=colors.HexColor("#CBD5E1"),
            borderWidth=0.7,
            borderPadding=6,
            textColor=colors.HexColor("#334155"),
            spaceBefore=4,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchCode",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            leftIndent=6,
            rightIndent=6,
            borderColor=colors.HexColor("#E2E8F0"),
            borderWidth=0.5,
            borderPadding=5,
            backColor=colors.HexColor("#F8FAFC"),
            spaceBefore=4,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ResearchSmall",
            parent=styles["ResearchBody"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        )
    )

    return styles


# ============================================================
# INLINE MARKDOWN CONVERSION
# ============================================================

def _safe_link_markup(url: str, label: str) -> str:
    """Create a ReportLab hyperlink only for HTTP(S) URLs."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return escape(label)

    safe_url = escape(url, {'"': "&quot;"})
    return (
        f'<link href="{safe_url}" color="#1D4ED8">'
        f"{escape(label)}</link>"
    )


def _inline_markdown(text: str) -> str:
    """
    Convert a small safe subset of inline Markdown to ReportLab markup.

    Raw HTML/XML is escaped first, so user-supplied content cannot inject
    ReportLab paragraph tags.
    """
    text = _as_string(text)

    # Temporarily protect Markdown links before escaping the remaining text.
    links = []

    def save_link(match):
        label = match.group(1)
        url = match.group(2).strip()
        token = f"@@LINK{len(links)}@@"
        links.append(_safe_link_markup(url, label))
        return token

    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        save_link,
        text,
    )

    text = escape(text)

    # Inline code.
    text = re.sub(
        r"`([^`]+)`",
        lambda m: f'<font name="Courier" size="8">{m.group(1)}</font>',
        text,
    )

    # Bold and italic.
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<i>\1</i>", text)

    for index, markup in enumerate(links):
        text = text.replace(f"@@LINK{index}@@", markup)

    return text


# ============================================================
# MARKDOWN BLOCK PARSING
# ============================================================

def _is_table_separator(line: str) -> bool:
    """Identify a Markdown table separator row."""
    stripped = line.strip().strip("|").strip()
    if not stripped:
        return False

    cells = [cell.strip() for cell in stripped.split("|")]
    return all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def _parse_table_row(line: str) -> list[str]:
    """Split a simple pipe-delimited Markdown table row into cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _make_pdf_table(lines: list[str], styles):
    """Convert a basic Markdown table into a ReportLab Table."""
    rows = [_parse_table_row(line) for line in lines]

    if len(rows) >= 2 and _is_table_separator(lines[1]):
        rows.pop(1)

    if not rows:
        return None

    column_count = max(len(row) for row in rows)
    normalized_rows = []

    for row in rows:
        row = row + [""] * (column_count - len(row))
        normalized_rows.append([
            Paragraph(_inline_markdown(cell), styles["ResearchSmall"])
            for cell in row
        ])

    table = Table(
        normalized_rows,
        repeatRows=1,
        hAlign="LEFT",
        colWidths=None,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _add_markdown_content(story: list, content: str, styles) -> None:
    """Append common Markdown blocks to a ReportLab story."""
    lines = _as_string(content).splitlines()
    index = 0
    paragraph_lines = []
    in_code_block = False
    code_lines = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            paragraph_text = " ".join(part.strip() for part in paragraph_lines)
            if paragraph_text:
                story.append(
                    Paragraph(
                        _inline_markdown(paragraph_text),
                        styles["ResearchBody"],
                    )
                )
            paragraph_lines = []

    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()

        # Fenced code blocks.
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_paragraph()

            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                code_text = "\n".join(code_lines)
                story.append(
                    Preformatted(
                        escape(code_text),
                        styles["ResearchCode"],
                    )
                )
                in_code_block = False
                code_lines = []

            index += 1
            continue

        if in_code_block:
            code_lines.append(raw_line)
            index += 1
            continue

        if not stripped:
            flush_paragraph()
            story.append(Spacer(1, 3))
            index += 1
            continue

        # Horizontal rule.
        if re.fullmatch(r"([-*_]\s*){3,}", stripped):
            flush_paragraph()
            story.append(Spacer(1, 4))
            story.append(
                Table(
                    [[""]],
                    colWidths=[7.0 * inch],
                    rowHeights=[0.6],
                    style=TableStyle([
                        ("LINEBELOW", (0, 0), (-1, -1), 0.5,
                         colors.HexColor("#CBD5E1")),
                    ]),
                )
            )
            story.append(Spacer(1, 5))
            index += 1
            continue

        # Markdown tables.
        if stripped.startswith("|") and index + 1 < len(lines):
            if _is_table_separator(lines[index + 1]):
                flush_paragraph()
                table_lines = [stripped]
                index += 1

                if index < len(lines) and _is_table_separator(lines[index]):
                    table_lines.append(lines[index])
                    index += 1

                while index < len(lines) and lines[index].strip().startswith("|"):
                    table_lines.append(lines[index].strip())
                    index += 1

                table = _make_pdf_table(table_lines, styles)
                if table is not None:
                    story.append(KeepTogether([table, Spacer(1, 7)]))
                continue

        # Headings.
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            style_name = {
                1: "ResearchH1",
                2: "ResearchH2",
                3: "ResearchH3",
            }[level]
            story.append(
                Paragraph(
                    _inline_markdown(heading_match.group(2)),
                    styles[style_name],
                )
            )
            index += 1
            continue

        # Unordered list.
        bullet_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        if bullet_match:
            flush_paragraph()
            story.append(
                Paragraph(
                    "&#8226; " + _inline_markdown(bullet_match.group(1)),
                    styles["ResearchBullet"],
                )
            )
            index += 1
            continue

        # Ordered list.
        number_match = re.match(r"^(\d+)[.)]\s+(.+)$", stripped)
        if number_match:
            flush_paragraph()
            story.append(
                Paragraph(
                    f"{number_match.group(1)}. "
                    + _inline_markdown(number_match.group(2)),
                    styles["ResearchBullet"],
                )
            )
            index += 1
            continue

        # Blockquote.
        if stripped.startswith(">"):
            flush_paragraph()
            quote_text = stripped.lstrip(">").strip()
            story.append(
                Paragraph(
                    _inline_markdown(quote_text),
                    styles["ResearchQuote"],
                )
            )
            index += 1
            continue

        # Regular paragraph; consecutive lines are joined.
        paragraph_lines.append(stripped)
        index += 1

    # Close an unclosed fenced code block gracefully.
    if in_code_block and code_lines:
        story.append(
            Preformatted(
                escape("\n".join(code_lines)),
                styles["ResearchCode"],
            )
        )

    flush_paragraph()


# ============================================================
# PDF EXPORT
# ============================================================

def _draw_page_footer(canvas, document):
    """Draw a small page number footer on every PDF page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawRightString(
        A4[0] - PAGE_RIGHT_MARGIN,
        0.38 * inch,
        f"Page {document.page}",
    )
    canvas.restoreState()


def save_pdf(topic: str, report: str, feedback: str) -> Path:
    """Save the research report and critic evaluation as a formatted PDF."""
    topic = _as_string(topic).strip() or "Research Report"
    report = _as_string(report)
    feedback = _as_string(feedback)

    filepath = REPORT_DIR / f"{clean_filename(topic)}.pdf"
    styles = _make_styles()

    document = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=PAGE_RIGHT_MARGIN,
        leftMargin=PAGE_LEFT_MARGIN,
        topMargin=PAGE_TOP_MARGIN,
        bottomMargin=PAGE_BOTTOM_MARGIN,
        title=topic,
        author="Research Pipeline",
        subject="AI-assisted research report",
    )

    story = [
        Paragraph(escape(topic), styles["ResearchTitle"]),
        Paragraph(
            "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            styles["ResearchSmall"],
        ),
        Spacer(1, 12),
    ]

    _add_markdown_content(story, report, styles)

    story.append(PageBreak())
    story.append(
        Paragraph("Critic Evaluation", styles["ResearchH1"])
    )
    _add_markdown_content(story, feedback, styles)

    document.build(
        story,
        onFirstPage=_draw_page_footer,
        onLaterPages=_draw_page_footer,
    )

    print(f"[EXPORT] PDF: {filepath.resolve()}")
    return filepath


# ============================================================
# OPTIONAL CONVENIENCE FUNCTION
# ============================================================

def export_report(topic: str, report: str, feedback: str) -> dict:
    """Export both formats and return their paths."""
    markdown_path = save_markdown(topic, report, feedback)
    pdf_path = save_pdf(topic, report, feedback)

    return {
        "markdown_file": str(markdown_path),
        "pdf_file": str(pdf_path),
    }
