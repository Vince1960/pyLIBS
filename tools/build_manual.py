#!/usr/bin/env python3
"""Build the Italian or English pyLIBS user manual from Markdown."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "pyLIBS_Manual.md"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "pyLIBS_Manual.pdf"

LANGUAGE_TEXT = {
    "it": {
        "header": "pyLIBS - Manuale operativo completo",
        "page": "Pagina",
        "subtitle": "Guida completa dalla configurazione al risultato CF-LIBS",
        "contents": "Indice",
        "title": "pyLIBS - Manuale operativo completo",
        "author": "Vincenzo Palleschi e collaboratori",
        "subject": "Guida completa all'uso di pyLIBS",
    },
    "en": {
        "header": "pyLIBS - Complete User Manual",
        "page": "Page",
        "subtitle": "Complete guide from configuration to CF-LIBS results",
        "contents": "Contents",
        "title": "pyLIBS - Complete User Manual",
        "author": "Vincenzo Palleschi and collaborators",
        "subject": "Complete guide to using pyLIBS",
    },
}

NAVY = colors.HexColor("#12324A")
BLUE = colors.HexColor("#1976A3")
PALE_BLUE = colors.HexColor("#EAF4F8")
PALE_GOLD = colors.HexColor("#FFF7DF")
TEXT = colors.HexColor("#202A32")
MUTED = colors.HexColor("#5C6870")
GRID = colors.HexColor("#C8D3D9")


def register_fonts():
    candidates = {
        "ManualSans": Path(r"C:\Windows\Fonts\segoeui.ttf"),
        "ManualSans-Bold": Path(r"C:\Windows\Fonts\seguisb.ttf"),
        "ManualSans-Italic": Path(r"C:\Windows\Fonts\segoeuii.ttf"),
        "ManualMono": Path(r"C:\Windows\Fonts\consola.ttf"),
    }
    if all(path.is_file() for path in candidates.values()):
        for name, path in candidates.items():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily(
            "ManualSans",
            normal="ManualSans",
            bold="ManualSans-Bold",
            italic="ManualSans-Italic",
            boldItalic="ManualSans-Bold",
        )
        return "ManualSans", "ManualSans-Bold", "ManualMono"
    return "Helvetica", "Helvetica-Bold", "Courier"


FONT, FONT_BOLD, FONT_MONO = register_fonts()


class ManualDocTemplate(BaseDocTemplate):
    def __init__(self, filename, language="it", **kwargs):
        super().__init__(filename, **kwargs)
        self.language = language
        cover_frame = Frame(24 * mm, 24 * mm, 162 * mm, 249 * mm, id="cover")
        body_frame = Frame(19 * mm, 18 * mm, 172 * mm, 254 * mm, id="body")
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[cover_frame], onPage=self.cover_page),
                PageTemplate(id="body", frames=[body_frame], onPage=self.body_page),
            ]
        )
        self._bookmark_counter = 0

    def beforeDocument(self):
        self._bookmark_counter = 0
        super().beforeDocument()

    def cover_page(self, canvas, _doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 72 * mm, width, 72 * mm, stroke=0, fill=1)
        canvas.setFillColor(BLUE)
        canvas.rect(0, height - 75 * mm, width, 3 * mm, stroke=0, fill=1)
        canvas.restoreState()

    def body_page(self, canvas, doc):
        width, height = A4
        labels = LANGUAGE_TEXT[self.language]
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D8E1E6"))
        canvas.setLineWidth(0.5)
        canvas.line(19 * mm, height - 14 * mm, width - 19 * mm, height - 14 * mm)
        canvas.setFont(FONT, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(19 * mm, height - 10.5 * mm, labels["header"])
        canvas.drawRightString(width - 19 * mm, 10 * mm, f'{labels["page"]} {doc.page}')
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style_name = flowable.style.name
        if style_name not in {"ManualH2", "ManualH3"}:
            return
        level = 0 if style_name == "ManualH2" else 1
        text = flowable.getPlainText()
        key = f"section-{self._bookmark_counter}"
        self._bookmark_counter += 1
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


def styles():
    sample = getSampleStyleSheet()
    result = {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName=FONT_BOLD,
            fontSize=30,
            leading=35,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=sample["Normal"],
            fontName=FONT,
            fontSize=14,
            leading=19,
            textColor=colors.white,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=sample["Normal"],
            fontName=FONT,
            fontSize=10,
            leading=16,
            textColor=TEXT,
        ),
        "h2": ParagraphStyle(
            "ManualH2",
            parent=sample["Heading1"],
            fontName=FONT_BOLD,
            fontSize=17,
            leading=21,
            textColor=NAVY,
            spaceBefore=9,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "ManualH3",
            parent=sample["Heading2"],
            fontName=FONT_BOLD,
            fontSize=11.5,
            leading=15,
            textColor=BLUE,
            spaceBefore=7,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ManualBody",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.35,
            leading=13.2,
            textColor=TEXT,
            spaceAfter=5,
            allowWidows=0,
            allowOrphans=0,
        ),
        "table_header": ParagraphStyle(
            "ManualTableHeader",
            parent=sample["BodyText"],
            fontName=FONT_BOLD,
            fontSize=9.2,
            leading=12,
            textColor=colors.white,
        ),
        "bullet": ParagraphStyle(
            "ManualBullet",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=12.8,
            textColor=TEXT,
            leftIndent=2 * mm,
        ),
        "callout": ParagraphStyle(
            "ManualCallout",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.2,
            leading=13,
            textColor=NAVY,
        ),
        "code": ParagraphStyle(
            "ManualCode",
            parent=sample["Code"],
            fontName=FONT_MONO,
            fontSize=8.2,
            leading=11,
            textColor=TEXT,
            leftIndent=5 * mm,
            backColor=colors.HexColor("#F3F5F6"),
            borderPadding=5,
            spaceAfter=6,
        ),
        "toc_h": ParagraphStyle(
            "TOCHeading",
            parent=sample["Heading1"],
            fontName=FONT_BOLD,
            fontSize=20,
            leading=24,
            textColor=NAVY,
            spaceAfter=10,
        ),
    }
    return result


def inline_markup(text):
    parts = re.split(r"(`[^`]+`)", text)
    rendered = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            rendered.append(f'<font name="{FONT_MONO}" color="#174D66">{html.escape(part[1:-1])}</font>')
            continue
        escaped = html.escape(part)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
        rendered.append(escaped)
    return "".join(rendered)


def callout(text, style):
    table = Table([[Paragraph(inline_markup(text), style)]], colWidths=[166 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_GOLD),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#E4C96A")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def markdown_table(rows, body_style, header_style):
    cols = max(len(row) for row in rows)
    normalized = [row + [""] * (cols - len(row)) for row in rows]
    data = []
    for row_index, row in enumerate(normalized):
        style = header_style if row_index == 0 else body_style
        data.append([Paragraph(inline_markup(cell.strip()), style) for cell in row])
    if cols == 3:
        widths = [42 * mm, 43 * mm, 81 * mm]
    elif cols == 2:
        widths = [48 * mm, 118 * mm]
    else:
        widths = [166 * mm / cols] * cols
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                ("GRID", (0, 0), (-1, -1), 0.35, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def parse_manual(source, language="it"):
    st = styles()
    labels = LANGUAGE_TEXT[language]
    lines = source.read_text(encoding="utf-8").splitlines()
    story = []
    paragraph = []
    index = 0
    in_toc = False

    def flush_paragraph():
        if paragraph:
            text = " ".join(item.strip() for item in paragraph)
            story.append(Paragraph(inline_markup(text), st["body"]))
            paragraph.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if index == 0 and stripped.startswith("# "):
            title = stripped[2:]
            story.extend(
                [
                    Spacer(1, 23 * mm),
                    Paragraph(inline_markup(title), st["cover_title"]),
                    Paragraph(labels["subtitle"], st["cover_subtitle"]),
                    Spacer(1, 50 * mm),
                ]
            )
            index += 1
            continue
        if index in {1, 2, 3} and stripped:
            story.append(Paragraph(inline_markup(stripped.rstrip("  ")), st["cover_meta"]))
            index += 1
            continue
        if stripped in {"## Indice operativo", "## Operating contents"}:
            flush_paragraph()
            story.append(NextPageTemplate("body"))
            story.append(PageBreak())
            story.append(Paragraph(labels["contents"], st["toc_h"]))
            toc = TableOfContents()
            toc.levelStyles = [
                ParagraphStyle(
                    "TOC1", fontName=FONT, fontSize=10, leading=15,
                    leftIndent=0, firstLineIndent=0, textColor=TEXT,
                ),
                ParagraphStyle(
                    "TOC2", fontName=FONT, fontSize=8.5, leading=12,
                    leftIndent=7 * mm, firstLineIndent=0, textColor=MUTED,
                ),
            ]
            story.append(toc)
            in_toc = True
            index += 1
            continue
        if in_toc:
            if stripped == "<!-- pagebreak -->":
                story.append(PageBreak())
                in_toc = False
            index += 1
            continue
        if stripped == "<!-- pagebreak -->":
            flush_paragraph()
            story.append(PageBreak())
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[3:]), st["h2"]))
            index += 1
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[4:]), st["h3"]))
            index += 1
            continue
        if stripped.startswith("> "):
            flush_paragraph()
            story.append(callout(stripped[2:], st["callout"]))
            story.append(Spacer(1, 3 * mm))
            index += 1
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            table_lines = []
            while index < len(lines):
                candidate = lines[index].strip()
                if not (candidate.startswith("|") and candidate.endswith("|")):
                    break
                cells = [cell.strip() for cell in candidate.strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    table_lines.append(cells)
                index += 1
            story.append(markdown_table(table_lines, st["body"], st["table_header"]))
            story.append(Spacer(1, 3 * mm))
            continue
        if re.match(r"^-\s+", stripped):
            flush_paragraph()
            items = []
            while index < len(lines) and re.match(r"^-\s+", lines[index].strip()):
                text = re.sub(r"^-\s+", "", lines[index].strip())
                items.append(ListItem(Paragraph(inline_markup(text), st["bullet"])))
                index += 1
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="circle",
                    leftIndent=6 * mm,
                    bulletFontName=FONT,
                    bulletFontSize=7,
                    spaceAfter=5,
                )
            )
            continue
        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            items = []
            while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                raw = lines[index].strip()
                number, text = raw.split(".", 1)
                items.append(
                    [
                        Paragraph(f"<b>{number}</b>", st["bullet"]),
                        Paragraph(inline_markup(text.strip()), st["bullet"]),
                    ]
                )
                index += 1
            numbered = Table(items, colWidths=[8 * mm, 158 * mm], hAlign="LEFT")
            numbered.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (0, -1), 4),
                        ("RIGHTPADDING", (1, 0), (1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                    ]
                )
            )
            story.append(numbered)
            story.append(Spacer(1, 2 * mm))
            continue
        if stripped.startswith("```"):
            flush_paragraph()
            index += 1
            code = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            story.append(Paragraph("<br/>".join(html.escape(row) for row in code), st["code"]))
            index += 1
            continue
        paragraph.append(stripped)
        index += 1
    flush_paragraph()
    return story


def build(source, output, language="it"):
    output.parent.mkdir(parents=True, exist_ok=True)
    labels = LANGUAGE_TEXT[language]
    document = ManualDocTemplate(
        str(output),
        language=language,
        pagesize=A4,
        leftMargin=19 * mm,
        rightMargin=19 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=labels["title"],
        author=labels["author"],
        subject=labels["subject"],
    )
    document.multiBuild(parse_manual(source, language=language))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--language", choices=sorted(LANGUAGE_TEXT), default=None)
    args = parser.parse_args()
    language = args.language or ("en" if args.source.stem.lower().endswith("_en") else "it")
    build(args.source.resolve(), args.output.resolve(), language=language)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
