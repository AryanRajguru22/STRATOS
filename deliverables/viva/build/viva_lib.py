"""Shared layout helpers for the STRATOS viva PDFs (ReportLab).

Only a document-building dependency: `pip install -r requirements-docs.txt`.
Fonts: DejaVu Sans / Serif / Sans Mono (full Greek and math coverage), looked up in the usual system font folders.
"""
from __future__ import annotations

import io
import os
import re
import sys

from PIL import Image
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle, Image as RLImage)
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.tableofcontents import TableOfContents

# ----------------------------------------------------------------------------------------------------------------
# fonts
# ----------------------------------------------------------------------------------------------------------------
_FONT_DIRS = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", os.path.expanduser("~/.fonts")]


def _font(name: str) -> str:
    for d in _FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise SystemExit(f"font {name} not found; install DejaVu fonts (searched {_FONT_DIRS})")


for reg, file in (("Body", "DejaVuSans.ttf"), ("Body-Bold", "DejaVuSans-Bold.ttf"), ("Body-Italic", "DejaVuSans-Oblique.ttf"),
                  ("Body-BoldItalic", "DejaVuSans-BoldOblique.ttf"), ("Mono", "DejaVuSansMono.ttf"),
                  ("Mono-Bold", "DejaVuSansMono-Bold.ttf"), ("Serif", "DejaVuSerif.ttf"), ("Serif-Bold", "DejaVuSerif-Bold.ttf"),
                  ("Serif-Italic", "DejaVuSerif-Italic.ttf"), ("Serif-BoldItalic", "DejaVuSerif-BoldItalic.ttf")):
    pdfmetrics.registerFont(TTFont(reg, _font(file)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-BoldItalic")
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold", italic="Mono", boldItalic="Mono-Bold")
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold", italic="Serif-Italic", boldItalic="Serif-BoldItalic")

# ----------------------------------------------------------------------------------------------------------------
# palette and styles
# ----------------------------------------------------------------------------------------------------------------
NAVY = colors.HexColor("#14325c")
TEAL = colors.HexColor("#0f766e")
INK = colors.HexColor("#1b1b1b")
GREY = colors.HexColor("#5b6470")
LIGHT = colors.HexColor("#eef2f7")
ZEBRA = colors.HexColor("#f6f8fb")
RULE = colors.HexColor("#c9d2de")
AMBER = colors.HexColor("#b45309")
AMBER_BG = colors.HexColor("#fff4e0")
RED = colors.HexColor("#b42318")
RED_BG = colors.HexColor("#fdecea")
GREEN = colors.HexColor("#1a7f37")
GREEN_BG = colors.HexColor("#e8f5ec")
BLUE_BG = colors.HexColor("#e8f0fb")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
FRAME_W = PAGE_W - 2 * MARGIN

S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=9.6, leading=13.6, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.4, leading=11.4, textColor=INK, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.3, leading=10.8, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Body-Bold", fontSize=8.3, leading=10.8, textColor=colors.white),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.3, leading=10.8, textColor=INK),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=18, leading=22, textColor=NAVY, spaceBefore=14, spaceAfter=8, keepWithNext=1),
    "h1x": ParagraphStyle("h1x", fontName="Body-Bold", fontSize=18, leading=22, textColor=NAVY, spaceBefore=0, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=12.5, leading=16, textColor=TEAL, spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=10.4, leading=14, textColor=NAVY, spaceBefore=6, spaceAfter=3, keepWithNext=1),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=9.6, leading=13.4, textColor=INK, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "eq": ParagraphStyle("eq", fontName="Serif", fontSize=11.2, leading=17, textColor=INK, alignment=TA_CENTER),
    "eqs": ParagraphStyle("eqs", fontName="Serif", fontSize=10, leading=15, textColor=INK, alignment=TA_LEFT),
    "q": ParagraphStyle("q", fontName="Body-Bold", fontSize=9.4, leading=12.8, textColor=NAVY, spaceAfter=2),
    "a": ParagraphStyle("a", fontName="Body", fontSize=9.2, leading=12.8, textColor=INK),
    "cap": ParagraphStyle("cap", fontName="Body-Italic", fontSize=8.2, leading=10.8, textColor=GREY, spaceAfter=7),
    "speech": ParagraphStyle("speech", fontName="Body", fontSize=10.2, leading=15.6, textColor=INK, spaceAfter=5),
    "toc1": ParagraphStyle("toc1", fontName="Body-Bold", fontSize=10, leading=15, textColor=INK),
    "toc2": ParagraphStyle("toc2", fontName="Body", fontSize=9, leading=12.5, textColor=GREY, leftIndent=14),
    "covT": ParagraphStyle("covT", fontName="Body-Bold", fontSize=30, leading=35, textColor=colors.white),
    "covS": ParagraphStyle("covS", fontName="Body", fontSize=13, leading=18, textColor=colors.white),
}


def md(text: str) -> str:
    """Tiny markup: **bold**, __italic__, `code`; & < > are escaped. Other tags need RAW()."""
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"__(.+?)__", r"<i>\1</i>", t, flags=re.S)
    t = re.sub(r"(?<![*\w])\*(?!\*)([^*\n]+?)(?<!\*)\*(?![*\w])", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r'<font name="Mono" size="8.6">\1</font>', t)
    for tag in ("sub", "super", "br/", "/sub", "/super"):  # allow these simple tags straight through
        t = t.replace(f"&lt;{tag}&gt;", f"<{tag}>")
    return t


def glyph_report(pdf_path: str) -> list:
    """Return (page, font, char) triples for characters in the PDF that the embedded font has no glyph for."""
    import fitz  # PyMuPDF
    stems = {"DejaVuSans": "Body", "DejaVuSans-Bold": "Body-Bold", "DejaVuSans-Oblique": "Body-Italic", "DejaVuSans-BoldOblique": "Body-BoldItalic",
             "DejaVuSansMono": "Mono", "DejaVuSansMono-Bold": "Mono-Bold", "DejaVuSerif": "Serif", "DejaVuSerif-Bold": "Serif-Bold",
             "DejaVuSerif-Italic": "Serif-Italic", "DejaVuSerif-BoldItalic": "Serif-BoldItalic"}
    missing = []
    doc = fitz.open(pdf_path)
    for pno, page in enumerate(doc, 1):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    stem = span["font"].split("+")[-1]
                    reg = stems.get(stem)
                    if not reg:
                        continue
                    cmap = pdfmetrics.getFont(reg).face.charToGlyph
                    for ch in span["text"]:
                        if ch not in (" ", "\n", " ") and ord(ch) not in cmap:
                            missing.append((pno, reg, ch, hex(ord(ch))))
    return missing


class RAW(str):
    """Marks a string as ready-made Paragraph markup (not escaped)."""


def _m(x) -> str:
    return str(x) if isinstance(x, RAW) else md(str(x))


# ----------------------------------------------------------------------------------------------------------------
# document with numbered pages, header/footer, TOC
# ----------------------------------------------------------------------------------------------------------------
class NumberedCanvas(rl_canvas.Canvas):
    footer_left = ""
    header_text = ""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self._chrome(total)
            super().showPage()
        super().save()

    def _chrome(self, total: int):
        self.saveState()
        self.setStrokeColor(RULE)
        self.setLineWidth(0.5)
        self.line(MARGIN, PAGE_H - 13 * mm, PAGE_W - MARGIN, PAGE_H - 13 * mm)
        self.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
        self.setFont("Body", 7.8)
        self.setFillColor(GREY)
        self.drawString(MARGIN, PAGE_H - 10.5 * mm, self.header_text)
        self.drawString(MARGIN, 9 * mm, self.footer_left)
        self.drawRightString(PAGE_W - MARGIN, 9 * mm, f"Page {self._pageNumber} of {total}")
        self.restoreState()


class Doc(BaseDocTemplate):
    def __init__(self, path, title, header_text, footer_left, cover_fn):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=20 * mm, bottomMargin=19 * mm,
                         title=title, author="STRATOS project team", subject="STRATOS viva preparation")
        self._cover_fn = cover_fn
        self.header_text, self.footer_left = header_text, footer_left
        cover = Frame(MARGIN, 18 * mm, FRAME_W, PAGE_H - 36 * mm, id="cover", leftPadding=0, rightPadding=0)
        body = Frame(MARGIN, 19 * mm, FRAME_W, PAGE_H - 39 * mm, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate("cover", [cover], onPage=self._draw_cover), PageTemplate("body", [body])])

    def _draw_cover(self, canv, doc):
        self._cover_fn(canv, doc)

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1", "h2"):
            level = 0 if fl.style.name == "h1" else 1
            text = fl.getPlainText()
            key = f"toc{self.seq.nextf('toc')}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level, closed=level == 1)
            self.notify("TOCEntry", (level, text, self.page, key))

    def build_doc(self, story):
        header, footer = self.header_text, self.footer_left

        class _C(NumberedCanvas):
            header_text = header
            footer_left = footer

        self.multiBuild(story, canvasmaker=_C)


def make_toc() -> TableOfContents:
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    toc.dotsMinLevel = 0
    return toc


# ----------------------------------------------------------------------------------------------------------------
# flowable builders
# ----------------------------------------------------------------------------------------------------------------
def H1(t): return Paragraph(md(t), S["h1"])
def H1X(t): return Paragraph(md(t), S["h1x"])
def CODEM(t): return f"<font name='Mono' size='8'>{t}</font>"
def H2(t): return Paragraph(md(t), S["h2"])
def H3(t): return Paragraph(md(t), S["h3"])
def P(t, style="body"): return Paragraph(_m(t), S[style])
def SP(h=4): return Spacer(1, h)
def PB(): return PageBreak()


def BL(items, style="bullet"):
    return [Paragraph(_m(i), S[style], bulletText="•") for i in items]


def NL(items):
    return [Paragraph(_m(i), S["bullet"], bulletText=f"{n}.") for n, i in enumerate(items, 1)]


def EQ(markup: str, note: str | None = None, small: bool = False):
    """Boxed equation. `markup` is ready-made Paragraph markup (<sub>, <super>, <i> allowed)."""
    rows = [[Paragraph(markup, ParagraphStyle("eqq", parent=S["eq"], fontSize=9.6, leading=15) if small else S["eq"])]]
    if note:
        rows.append([Paragraph(md(note), S["small"])])
    t = Table(rows, colWidths=[FRAME_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("LINEBEFORE", (0, 0), (0, -1), 3, NAVY),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return KeepTogether([t, SP(5)])


def CALL(kind: str, title: str, body):
    """Callout box. kind: note | warn | viva | ok | pending."""
    bg, bar = {"note": (BLUE_BG, NAVY), "warn": (AMBER_BG, AMBER), "viva": (LIGHT, TEAL), "ok": (GREEN_BG, GREEN),
               "pending": (RED_BG, RED)}[kind]
    paras = [Paragraph(f"<b>{md(title)}</b>", ParagraphStyle("ct", parent=S["small"], textColor=bar, spaceAfter=2))]
    for b in (body if isinstance(body, list) else [body]):
        paras.append(b if isinstance(b, Flowable) else Paragraph(_m(b), S["small"]))
    t = Table([[paras]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return KeepTogether([t, SP(5)])


def QA(q: str, a, tag: str | None = None):
    qp = Paragraph(("<font color='#0f766e'>[%s]</font> " % tag if tag else "") + "Q. " + _m(q), S["q"])
    ans = a if isinstance(a, list) else [a]
    ap = [Paragraph(_m(x), S["a"]) if not isinstance(x, Flowable) else x for x in ans]
    t = Table([[qp], [ap]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7)]))
    return [KeepTogether([t]), SP(4)]


def T(rows, widths, header=True, size=None, zebra=True, align_right_cols=(), bold_first_col=False, valign="TOP"):
    """Table from a list of rows of strings (md markup) or flowables. widths in mm or fractions (<=1 of frame)."""
    cw = [(w * FRAME_W if w <= 1 else w * mm) for w in widths]
    data = []
    for r, row in enumerate(rows):
        out = []
        for c, cell in enumerate(row):
            if isinstance(cell, Flowable):
                out.append(cell)
            else:
                st = S["cellh"] if (header and r == 0) else (S["cellb"] if bold_first_col and c == 0 else S["cell"])
                if size:
                    st = ParagraphStyle("x", parent=st, fontSize=size, leading=size + 2.5)
                out.append(Paragraph(_m(cell), st))
        data.append(out)
    t = Table(data, colWidths=cw, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), valign), ("GRID", (0, 0), (-1, -1), 0.4, RULE),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if (r % 2) == 0:
                style.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    t.setStyle(TableStyle(style))
    return [t, SP(6)]


def CODE(text: str, size: float = 8):
    pre = Preformatted(text, ParagraphStyle("code", fontName="Mono", fontSize=size, leading=size + 2.4, textColor=INK))
    t = Table([[pre]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")), ("BOX", (0, 0), (-1, -1), 0.4, RULE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return [t, SP(6)]


def SHOT(path: str, caption: str, crop=None, max_w_mm=170, max_h_mm=118):
    """Embed a screenshot, optionally cropped to (left, top, right, bottom) pixels and trimmed of empty bottom area."""
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(crop)
    # trim blank bottom (the app background is near-uniform)
    px = im.load()
    w, h = im.size
    bg = px[w - 5, h - 5]
    last = 0
    for y in range(h - 1, 0, -1):
        if any(sum(abs(a - b) for a, b in zip(px[x, y], bg)) > 24 for x in range(0, w, 7)):
            last = y
            break
    im = im.crop((0, 0, w, min(h, last + 16)))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    buf.seek(0)
    w, h = im.size
    scale = min(max_w_mm * mm / w, max_h_mm * mm / h)
    img = RLImage(buf, width=w * scale, height=h * scale)
    box = Table([[img]], colWidths=[FRAME_W])
    box.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return KeepTogether([box, Paragraph(md(caption), S["cap"])])


def CHECK(items, cols=(0.06, 0.94)):
    rows = [["☐", i] for i in items]
    t = Table([[Paragraph("☐", ParagraphStyle("cb", fontName="Body", fontSize=11, leading=13)), Paragraph(_m(i), S["cell"])] for i in items],
              colWidths=[c * FRAME_W for c in cols])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return [t, SP(6)]


# ----------------------------------------------------------------------------------------------------------------
# diagrams (ReportLab graphics)
# ----------------------------------------------------------------------------------------------------------------
def _box(d, x, y, w, h, title, sub="", fill=LIGHT, stroke=NAVY, tcolor=NAVY):
    d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill, strokeColor=stroke, strokeWidth=1))
    d.add(String(x + w / 2, y + h - 12, title, textAnchor="middle", fontName="Body-Bold", fontSize=8.6, fillColor=tcolor))
    for k, line in enumerate(sub.split("\n") if sub else []):
        d.add(String(x + w / 2, y + h - 24 - k * 9.5, line, textAnchor="middle", fontName="Body", fontSize=7.2, fillColor=INK))


def _arrow(d, x1, y1, x2, y2, color=GREY, label=None, lx=0, ly=0):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.2))
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 6
    d.add(Polygon([x2, y2, x2 - L * math.cos(ang - 0.45), y2 - L * math.sin(ang - 0.45),
                   x2 - L * math.cos(ang + 0.45), y2 - L * math.sin(ang + 0.45)], fillColor=color, strokeColor=color))
    if label:
        d.add(String((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, textAnchor="middle", fontName="Body-Italic", fontSize=6.8, fillColor=GREY))


def architecture_diagram() -> Drawing:
    W, H = FRAME_W, 235
    d = Drawing(W, H)
    _box(d, 0, 190, W, 38, "User / browser", "Streamlit page at http://localhost:8501   |   sidebar controls + four tabs", fill=BLUE_BG)
    _box(d, 0, 125, 250, 52, "app.py  (UI layer)", "page layout, sidebar, st.session_state\nScenario | Assignment | Equilibrium | Simulation")
    _box(d, 262, 125, W - 262, 52, "app_helpers.py", "load_engine_bundle (real vs mock), DataFrame builders,\nPlotly charts, header and badges")
    _box(d, 0, 45, 200, 62, "game_engine.py  (ENGINE)", "validate, utility, welfare, potential, teams,\nis_nash, best_response_dynamics,\nenumerate_equilibria, CLI --report", fill=GREEN_BG, stroke=GREEN, tcolor=GREEN)
    _box(d, 212, 45, 140, 62, "sample_data.py", "tiny 2x2 example,\n8-student default scenario,\ndemo start profile", fill=GREEN_BG, stroke=GREEN, tcolor=GREEN)
    _box(d, 364, 45, W - 364, 62, "docs/", "MODEL.md, INTERFACE.md,\nresults/ (engine_report.json,\npytest_output.txt, timing.txt)", fill=AMBER_BG, stroke=AMBER, tcolor=AMBER)
    _box(d, 0, 0, 200, 33, "tests/", "engine, integration, UI-smoke, cross-check", fill=colors.HexColor("#f3e8ff"), stroke=colors.HexColor("#6b21a8"), tcolor=colors.HexColor("#6b21a8"))
    _box(d, 212, 0, W - 212, 33, "scripts/", "generate_results.py, independent_crosscheck.py", fill=colors.HexColor("#f3e8ff"), stroke=colors.HexColor("#6b21a8"), tcolor=colors.HexColor("#6b21a8"))
    _arrow(d, 60, 190, 60, 177, label="widgets", lx=22)
    _arrow(d, 190, 177, 190, 190, label="rendered page", lx=-34)
    _arrow(d, 250, 150, 262, 150)
    _arrow(d, 100, 125, 100, 107, color=GREEN, label="engine calls", lx=30)
    _arrow(d, 330, 125, 290, 107, color=GREEN, label="scenario dicts", lx=40, ly=2)
    _arrow(d, 212, 76, 200, 76, color=GREEN)
    return d


def dataflow_diagram() -> Drawing:
    W, H = FRAME_W, 140
    d = Drawing(W, H)
    bw, bh, gap = 82, 46, 12
    steps = [("1  Widget", "selectbox per student\nstate -> session_state"), ("2  Profile", "list of project\nindices, 0-based"),
             ("3  Validate", "engine.validate_\nprofile / scenario"), ("4  Engine", "utilities, teams,\nwelfare, potential"),
             ("5  Helpers", "DataFrames and\nPlotly figures")]
    x = 0
    for i, (t, s) in enumerate(steps):
        fill = GREEN_BG if i in (2, 3) else LIGHT
        _box(d, x, 80, bw, bh, t, s, fill=fill, stroke=GREEN if i in (2, 3) else NAVY, tcolor=GREEN if i in (2, 3) else NAVY)
        if i < len(steps) - 1:
            _arrow(d, x + bw, 103, x + bw + gap, 103)
        x += bw + gap
    _box(d, 0, 8, 150, 50, "6  Tab output", "metrics, tables, charts,\nstable / not-stable message")
    _box(d, 170, 8, 170, 50, "Simulation tab only", "best_response_dynamics -> steps\nthen a FRESH is_nash(final)", fill=AMBER_BG, stroke=AMBER, tcolor=AMBER)
    _arrow(d, x - bw / 2 - gap, 80, 75, 58, label="st.dataframe / plotly_chart", lx=-20, ly=-12)
    _arrow(d, 150, 33, 170, 33)
    d.add(String(350, 40, "StratosError is caught in the UI", fontName="Body-Italic", fontSize=7, fillColor=GREY))
    d.add(String(350, 30, "and shown with st.error", fontName="Body-Italic", fontSize=7, fillColor=GREY))
    return d


def potential_chart(points) -> Drawing:
    """Tiny line chart of welfare and potential along a dynamics trace. points = [(step, welfare, potential)]."""
    W, H = 250, 130
    d = Drawing(W, H)
    x0, y0, x1, y1 = 34, 22, W - 8, H - 14
    d.add(Line(x0, y0, x1, y0, strokeColor=GREY)); d.add(Line(x0, y0, x0, y1, strokeColor=GREY))
    ys = [v for _, w, p in points for v in (w, p)]
    lo, hi = min(ys), max(ys)
    span = (hi - lo) or 1
    n = len(points) - 1 or 1
    def X(i): return x0 + (x1 - x0) * i / n
    def Y(v): return y0 + (y1 - y0) * (v - lo) / span
    for idx, color, name in ((1, NAVY, "welfare W"), (2, TEAL, "potential Φ")):
        pts = [(X(i), Y(p[idx])) for i, p in enumerate(points)]
        for a, b in zip(pts, pts[1:]):
            d.add(Line(a[0], a[1], b[0], b[1], strokeColor=color, strokeWidth=1.6))
        for (px_, py_), p in zip(pts, points):
            d.add(Rect(px_ - 2, py_ - 2, 4, 4, fillColor=color, strokeColor=color))
    for i, p in enumerate(points):
        d.add(String(X(i), y0 - 10, str(p[0]), textAnchor="middle", fontName="Body", fontSize=6.8, fillColor=GREY))
    d.add(String(x0 - 4, Y(lo) - 2, str(lo), textAnchor="end", fontName="Body", fontSize=6.8, fillColor=GREY))
    d.add(String(x0 - 4, Y(hi) - 2, str(hi), textAnchor="end", fontName="Body", fontSize=6.8, fillColor=GREY))
    d.add(String(x0 + 6, H - 8, "■ welfare W", fontName="Body", fontSize=7.4, fillColor=NAVY))
    d.add(String(x0 + 70, H - 8, "■ potential Φ", fontName="Body", fontSize=7.4, fillColor=TEAL))
    d.add(String((x0 + x1) / 2, 2, "move number (0 = start)", textAnchor="middle", fontName="Body-Italic", fontSize=6.8, fillColor=GREY))
    return d


def cover_painter(title_lines, subtitle, meta_rows, accent=NAVY):
    def paint(canv, doc):
        canv.saveState()
        canv.setFillColor(accent)
        canv.rect(0, PAGE_H - 118 * mm, PAGE_W, 118 * mm, stroke=0, fill=1)
        canv.setFillColor(colors.HexColor("#5eead4"))
        canv.rect(0, PAGE_H - 120 * mm, PAGE_W, 2 * mm, stroke=0, fill=1)
        y = PAGE_H - 40 * mm
        canv.setFillColor(colors.HexColor("#99f6e4"))
        canv.setFont("Body-Bold", 11)
        canv.drawString(MARGIN, y + 14 * mm, "STRATOS  ·  Game Theory course project")
        canv.setFillColor(colors.white)
        canv.setFont("Body-Bold", 27)
        for line in title_lines:
            canv.drawString(MARGIN, y, line)
            y -= 11.5 * mm
        canv.setFont("Body", 12)
        for line in subtitle:
            canv.drawString(MARGIN, y - 2 * mm, line)
            y -= 6.5 * mm
        yy = PAGE_H - 134 * mm
        for k, v in meta_rows:
            canv.setFillColor(GREY)
            canv.setFont("Body-Bold", 9)
            canv.drawString(MARGIN, yy, k)
            canv.setFillColor(INK)
            canv.setFont("Body", 9.2)
            canv.drawString(MARGIN + 42 * mm, yy, v)
            yy -= 6.4 * mm
        canv.restoreState()
    return paint


def check_environment():
    if sys.version_info < (3, 9):
        raise SystemExit("Python 3.9+ required")
