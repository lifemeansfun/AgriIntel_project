#!/usr/bin/env python3
"""Render the repository technical Markdown as a print-ready PDF.

Requires Pandoc and ReportLab. The two documented Mermaid diagrams are drawn
as vector flowcharts, so the PDF does not depend on a network renderer.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "TECHNICAL_DOCUMENTATION.md"
OUTPUT = ROOT / "output" / "pdf" / "AgriIntel_Technical_Documentation.pdf"
FONT_CANDIDATES = [
    Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype",
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/Library/Fonts"),
]


def register_fonts() -> None:
    font_dir = next((folder for folder in FONT_CANDIDATES
                     if (folder / "DejaVuSans.ttf").exists()), None)
    if font_dir is None:
        raise FileNotFoundError("DejaVu Sans fonts are required to render the technical PDF")
    names = {
        "DV": "DejaVuSans.ttf",
        "DV-Bold": "DejaVuSans-Bold.ttf",
        "DV-Oblique": "DejaVuSans-Oblique.ttf",
        "DV-Mono": "DejaVuSansMono.ttf",
    }
    for name, filename in names.items():
        path = font_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"PDF font missing: {path}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-Bold", italic="DV-Oblique")


def pandoc_blocks() -> list[dict]:
    result = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "json", str(SOURCE)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)["blocks"]


def plain(nodes: list[dict]) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", markup(nodes))).strip()


def markup(nodes: list[dict]) -> str:
    parts = []
    for node in nodes:
        kind, value = node["t"], node.get("c")
        if kind == "Str":
            parts.append(html.escape(value))
        elif kind in ("Space", "SoftBreak"):
            parts.append(" ")
        elif kind == "LineBreak":
            parts.append("<br/>")
        elif kind == "Strong":
            parts.append(f"<b>{markup(value)}</b>")
        elif kind == "Emph":
            parts.append(f"<i>{markup(value)}</i>")
        elif kind == "Code":
            parts.append(f'<font name="DV-Mono" color="#145c50">{html.escape(value[1])}</font>')
        elif kind == "Link":
            label, target = markup(value[1]), value[2][0]
            if target.startswith("../"):
                target = "https://github.com/lifemeansfun/AgriIntel_project/blob/main/" + target[3:]
            parts.append(f'<link href="{html.escape(target, quote=True)}" color="#126e63">{label}</link>')
        elif kind == "Span":
            parts.append(markup(value[1]))
        elif kind == "Math":
            parts.append(html.escape(value[1]))
        elif isinstance(value, list):
            parts.append(markup([x for x in value if isinstance(x, dict) and "t" in x]))
    return "".join(parts)


def block_text(blocks: list[dict]) -> str:
    return " ".join(plain(block.get("c", [])) for block in blocks if block["t"] in ("Plain", "Para"))


def table_rows(table: dict) -> list[list[str]]:
    _, _, _, head, bodies, foot = table["c"]

    def unpack(rows: list) -> list[list[str]]:
        return [[block_text(cell[4]) for cell in row[1]] for row in rows]

    result = unpack(head[1])
    for body in bodies:
        result.extend(unpack(body[2]))
        result.extend(unpack(body[3]))
    result.extend(unpack(foot[1]))
    return result


class FlowDiagram(Flowable):
    """Static vector counterparts of the two simple source flowcharts."""

    def __init__(self, feedback: bool):
        super().__init__()
        self.width = 498
        self.feedback = feedback
        self.height = 302 if feedback else 363

    def draw(self) -> None:
        c = self.canv
        c.setStrokeColor(colors.HexColor("#b8d0c8"))
        c.setFillColor(colors.HexColor("#f6faf7"))
        c.roundRect(0, 0, self.width, self.height, 11, fill=1, stroke=1)

        if self.feedback:
            labels = [
                "Browser A requests advice", "API reads shared supply and revision",
                "SQLite saves participant-bound quote", "Browser A commits a quoted crop",
                "SQLite saves commitment and revision atomically",
                "Browser B refreshes shared state", "API recalculates price and ranking",
            ]
            top, step, width = self.height - 25, 40, 335
        else:
            labels = [
                "Raw agronomy CSV", "Structural cleaning", "Past calendar-year features",
                "Year-wise yield training and calibration", "Immutable run and active pointer",
                "Validated historical catalog", "FastAPI v2", "React classroom dashboard",
            ]
            top, step, width = self.height - 25, 42, 285

        box_h = 30
        x = (self.width - width) / 2
        for i, label in enumerate(labels):
            y = top - i * step - box_h
            self._box(x, y, width, box_h, label, emphasized=i == len(labels) - 1)
            if i < len(labels) - 1:
                self._arrow(x + width / 2, y - 2, x + width / 2, y - step + box_h + 2)
        if not self.feedback:
            self._box(5, top - 2 * step - 5, 102, 42, "Generated price registry and CPI", side=True)
            self._arrow(107, top - 2 * step + 14, x - 4, top - 2 * step - 15)
            self._box(5, top - 5 * step - 5, 102, 42, "Regional scenario configuration", side=True)
            self._arrow(107, top - 5 * step + 14, x - 4, top - 5 * step - 15)
            self._box(self.width - 108, top - 6 * step - 5, 103, 42, "SQLite commitments, quotes, replays", side=True)
            self._arrow(self.width - 108, top - 6 * step + 14, x + width + 4, top - 6 * step - 15)

    def _box(self, x: float, y: float, width: float, height: float, label: str,
             *, emphasized: bool = False, side: bool = False) -> None:
        c = self.canv
        c.setFillColor(colors.HexColor("#dbefe7" if emphasized else "#ffffff"))
        c.setStrokeColor(colors.HexColor("#92bbae" if side else "#4d9a82"))
        c.roundRect(x, y, width, height, 6, fill=1, stroke=1)
        font_size = 7 if side else 8
        lines = simpleSplit(label, "DV", font_size, width - 12)
        c.setFillColor(colors.HexColor("#143e35"))
        c.setFont("DV", font_size)
        leading = font_size + 2
        text_y = y + height / 2 + (len(lines) - 1) * leading / 2 - font_size * .35
        for line in lines:
            c.drawCentredString(x + width / 2, text_y, line)
            text_y -= leading

    def _arrow(self, x1: float, y1: float, x2: float, y2: float) -> None:
        c = self.canv
        c.setStrokeColor(colors.HexColor("#4d9a82"))
        c.setFillColor(colors.HexColor("#4d9a82"))
        c.setLineWidth(1.4)
        c.line(x1, y1, x2, y2)
        if abs(x2 - x1) < 1:
            p = c.beginPath()
            p.moveTo(x2, y2)
            p.lineTo(x2 - 3, y2 + 5)
            p.lineTo(x2 + 3, y2 + 5)
        else:
            p = c.beginPath()
            p.moveTo(x2, y2)
            p.lineTo(x2 - 5, y2 + 3)
            p.lineTo(x2 - 5, y2 - 3)
        p.close()
        c.drawPath(p, fill=1, stroke=0)


class TechnicalDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(filename, pagesize=A4, leftMargin=47, rightMargin=47,
                         topMargin=51, bottomMargin=45, title="AgriIntel technical documentation",
                         author="Manish H, Anshul Singh, Aryan Sinha")
        width, height = A4
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="technical", frames=[frame], onPage=self.decorate))

    def decorate(self, canvas, doc) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(colors.HexColor("#143e35"))
        canvas.rect(0, height - 25, width, 25, fill=1, stroke=0)
        canvas.setFont("DV-Bold", 8)
        canvas.setFillColor(colors.white)
        canvas.drawString(47, height - 16, "AgriIntel  /  technical documentation")
        canvas.setStrokeColor(colors.HexColor("#a8cbbf"))
        canvas.line(47, 34, width - 47, 34)
        canvas.setFont("DV", 7.5)
        canvas.setFillColor(colors.HexColor("#647a72"))
        canvas.drawString(47, 22, "15 October 2026  •  historical classroom release")
        canvas.drawRightString(width - 47, 22, str(doc.page))
        canvas.restoreState()


def styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="DV", textColor=colors.HexColor("#1b2b27"), allowWidows=0, allowOrphans=0)
    return {
        "title": ParagraphStyle("Title", fontName="DV-Bold", fontSize=22, leading=27,
                                textColor=colors.HexColor("#143e35"), spaceAfter=11),
        "meta": ParagraphStyle("Meta", **{**base, "textColor": colors.HexColor("#526a60")},
                               fontSize=8.4, leading=13, spaceAfter=13),
        "body": ParagraphStyle("Body", **base, fontSize=8.7, leading=13.6, spaceAfter=8),
        "h2": ParagraphStyle("Section", fontName="DV-Bold", fontSize=13.5, leading=18,
                             textColor=colors.HexColor("#176c58"), spaceBefore=17,
                             spaceAfter=7, keepWithNext=True),
        "h3": ParagraphStyle("Subsection", fontName="DV-Bold", fontSize=10.4, leading=14,
                             textColor=colors.HexColor("#176c58"), spaceBefore=10,
                             spaceAfter=5, keepWithNext=True),
        "cell": ParagraphStyle("Cell", **base, fontSize=7.25, leading=10.3),
        "cellhead": ParagraphStyle("CellHead", fontName="DV-Bold", fontSize=7.3,
                                   leading=10.4, textColor=colors.white),
        "code": ParagraphStyle("Code", fontName="DV-Mono", fontSize=6.9,
                               leading=10.2, textColor=colors.HexColor("#274139")),
    }


def make_table(rows: list[list[str]], index: int, style: dict[str, ParagraphStyle]) -> Table:
    widths_by_index = {
        0: [108, 222, 171],
        1: [188, 198, 115],
        2: [205, 148, 148],
        3: [202, 149, 150],
    }
    widths = widths_by_index.get(index)
    if widths is None or len(widths) != len(rows[0]):
        widths = [501 / len(rows[0])] * len(rows[0])
    data = [[Paragraph(cell, style["cellhead"] if ridx == 0 else style["cell"])
             for cell in row] for ridx, row in enumerate(rows)]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c6351")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f7f3")]),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#cbded3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def main() -> None:
    register_fonts()
    blocks = pandoc_blocks()
    style = styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    story = []
    table_index = 0
    diagram_index = 0
    for index, block in enumerate(blocks):
        kind, value = block["t"], block.get("c")
        if kind == "Header":
            level, _, nodes = value
            style_name = "title" if level == 1 else "h2" if level == 2 else "h3"
            story.append(Paragraph(markup(nodes), style[style_name]))
        elif kind == "Para":
            paragraph_style = style["meta"] if index == 1 else style["body"]
            story.append(Paragraph(markup(value), paragraph_style))
        elif kind == "Table":
            story.append(make_table(table_rows(block), table_index, style))
            story.append(Spacer(1, 9))
            table_index += 1
        elif kind == "CodeBlock":
            classes, code = value[0][1], value[1]
            if "mermaid" in classes:
                story.append(FlowDiagram(feedback=diagram_index == 1))
                diagram_index += 1
            else:
                pre = Preformatted(code.replace("\t", "    "), style["code"], maxLineLength=107)
                box = Table([[pre]], colWidths=[501], hAlign="LEFT")
                box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f7f3")),
                    ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#b8d0c8")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(box)
            story.append(Spacer(1, 9))
    if table_index != 4 or diagram_index != 2:
        raise ValueError(f"Unexpected document structure: {table_index} tables, {diagram_index} diagrams")
    TechnicalDoc(str(OUTPUT)).build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
