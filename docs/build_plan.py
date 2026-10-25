# -*- coding: utf-8 -*-
"""Render docs/plan_content.py to the PDF and the Markdown copy (same source, so they agree).

Usage (from the repository root):  python docs/build_plan.py
Requires reportlab (plan generator only; not a project dependency).
"""
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import plan_content as C  # noqa: E402

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4, landscape  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas as rl_canvas  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak,  # noqa: E402
                                PageTemplate, Paragraph, Preformatted, Spacer, Table,
                                TableStyle, CondPageBreak, HRFlowable)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402

FONT_DIR = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Body", os.path.join(FONT_DIR, "segoeui.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", os.path.join(FONT_DIR, "segoeuib.ttf")))
pdfmetrics.registerFont(TTFont("Mono", os.path.join(FONT_DIR, "consola.ttf")))
pdfmetrics.registerFont(TTFont("Mono-Bold", os.path.join(FONT_DIR, "consolab.ttf")))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold", italic="Mono", boldItalic="Mono-Bold")

NAVY = colors.HexColor("#1F3A5F")
TEAL = colors.HexColor("#1E8C80")
LIGHT = colors.HexColor("#F2F5F9")
RULE = colors.HexColor("#C9D3DF")
INK = colors.HexColor("#1B2430")
GREY = colors.HexColor("#5B6676")
CODE_BG = colors.HexColor("#F4F6F8")
NOTE_BG = colors.HexColor("#FFF6E0")
NOTE_BAR = colors.HexColor("#E0A100")

S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8, leading=10.4, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Body-Bold", fontSize=8, leading=10.4, textColor=colors.white),
    "H1": ParagraphStyle("H1", fontName="Body-Bold", fontSize=17, leading=21, textColor=NAVY,
                         spaceBefore=4, spaceAfter=5),
    "H2": ParagraphStyle("H2", fontName="Body-Bold", fontSize=11.5, leading=15, textColor=TEAL,
                         spaceBefore=9, spaceAfter=4),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=9.5, leading=13.2, textColor=INK,
                             leftIndent=14, bulletIndent=3, spaceAfter=2.5),
    "note": ParagraphStyle("note", fontName="Body", fontSize=9, leading=12.5, textColor=INK),
    "toc1": ParagraphStyle("toc1", fontName="Body", fontSize=10, leading=15, textColor=INK, leftIndent=0),
    "tocT": ParagraphStyle("tocT", fontName="Body-Bold", fontSize=17, leading=21, textColor=NAVY, spaceAfter=8),
    "covT": ParagraphStyle("covT", fontName="Body-Bold", fontSize=54, leading=58, textColor=colors.white),
    "covS": ParagraphStyle("covS", fontName="Body", fontSize=17, leading=22, textColor=colors.white),
    "covD": ParagraphStyle("covD", fontName="Body-Bold", fontSize=22, leading=27, textColor=NAVY, spaceAfter=3),
    "covM": ParagraphStyle("covM", fontName="Body", fontSize=10.5, leading=15, textColor=GREY, spaceAfter=2),
}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


PRI = {"P0": "#B3261E", "P1": "#B26A00", "P2": "#5B6676"}


def _plain(e):
    return re.sub(r"\b(P[012])\b", lambda m: '<font color="%s">%s</font>' % (PRI[m.group(1)], m.group(1)), esc(e))


def inline(t):
    """Markup (**bold**, `code`) to reportlab XML. Priorities P0/P1/P2 are coloured. Code may sit inside bold."""
    parts = re.split(r"(\*\*[^*]+\*\*)", t)
    out = []
    for p in parts:
        if p.startswith("**") and p.endswith("**") and len(p) > 3:
            out.append("<b>%s</b>" % _codes(p[2:-2]))
        else:
            out.append(_codes(p))
    return "".join(out).replace("\n", "<br/>")


def _codes(t):
    out = []
    for p in re.split(r"(`[^`]+`)", t):
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append('<font name="Mono" size="7.4">%s</font>' % esc(p[1:-1]))
        else:
            out.append(_plain(p))
    return "".join(out)


class NumberedCanvas(rl_canvas.Canvas):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for i, st in enumerate(self._saved, 1):
            self.__dict__.update(st)
            if i > 1:
                w, h = self._pagesize
                self.setFont("Body", 8)
                self.setFillColor(GREY)
                self.drawString(36, 22, "STRATOS  |  Game Theory CSE3145  |  Manipal University Jaipur")
                self.drawRightString(w - 36, 22, "Page %d of %d" % (i, total))
            super().showPage()
        super().save()


class Doc(BaseDocTemplate):
    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("H1", "H2"):
            text = fl.getPlainText()
            key = "k" + hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
            self.canv.bookmarkPage(key)
            lvl = 0 if fl.style.name == "H1" else 1
            self.canv.addOutlineEntry(text, key, lvl, 0)
            if lvl == 0:
                self.notify("TOCEntry", (0, text, self.page, key))


def header(canv, doc):
    w, h = canv._pagesize
    canv.saveState()
    canv.setFont("Body-Bold", 8.5)
    canv.setFillColor(NAVY)
    canv.drawString(36, h - 28, "STRATOS  -  " + C.DOC_TITLE)
    canv.setStrokeColor(RULE)
    canv.setLineWidth(0.6)
    canv.line(36, h - 33, w - 36, h - 33)
    canv.line(36, 32, w - 36, 32)
    canv.restoreState()


def cover_page(canv, doc):
    w, h = A4
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, h - 330, w, 330, stroke=0, fill=1)
    canv.setFillColor(TEAL)
    canv.rect(0, h - 336, w, 6, stroke=0, fill=1)
    canv.restoreState()


def build_pdf(path):
    pw, ph = A4
    lw, lh = landscape(A4)
    doc = Doc(path, pagesize=A4, title="STRATOS - " + C.DOC_TITLE, author="Aryan Rajguru",
              subject="Game Theory CSE3145 project plan")
    cover_f = Frame(48, 60, pw - 96, ph - 120, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    port_f = Frame(40, 42, pw - 80, ph - 42 - 46, id="p")
    land_f = Frame(36, 42, lw - 72, lh - 42 - 46, id="l")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_f], onPage=cover_page, pagesize=A4),
        PageTemplate(id="portrait", frames=[port_f], onPage=header, pagesize=A4),
        PageTemplate(id="landscape", frames=[land_f], onPage=header, pagesize=landscape(A4)),
    ])

    story = []
    # ---- cover
    story.append(Spacer(1, 40))
    story.append(Paragraph(C.TITLE, S["covT"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(esc(C.SUBTITLE), S["covS"]))
    story.append(Spacer(1, 150))
    story.append(Paragraph(esc(C.DOC_TITLE), S["covD"]))
    story.append(Paragraph(esc(C.COURSE), S["covM"]))
    story.append(Paragraph("%s  |  %s" % (esc(C.VERSION), esc(C.DATE)), S["covM"]))
    story.append(Spacer(1, 16))
    rows = [[Paragraph("Member", S["cellh"]), Paragraph("Role", S["cellh"]), Paragraph("Tools", S["cellh"])]]
    for m in C.TEAM:
        rows.append([Paragraph("<b>%s</b>" % esc(m[0]), S["cell"]), Paragraph(esc(m[1]), S["cell"]), Paragraph(esc(m[2]), S["cell"])])
    t = Table(rows, colWidths=[110, 210, 160])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Status: planning deliverable. No implementation exists yet; every test is planned, none executed, "
                           "and no result is claimed.", S["covM"]))
    story.append(NextPageTemplate("portrait"))
    story.append(PageBreak())
    # ---- contents
    story.append(Paragraph("Contents", S["tocT"]))
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"]]
    toc.dotsMinLevel = 0
    story.append(toc)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Reading guide: <b>P0</b> required for the MVP, <b>P1</b> strong enhancement, <b>P2</b> optional. "
                           "Times are written T+hours:minutes from kickoff. Task IDs: A = Aryan, F = Frontend (Harsh), "
                           "Q = Quality/docs (Ayush); test IDs: E engine, I integration, S UI smoke, O oracle, M manual.", S["body"]))
    story.append(PageBreak())

    first_h1 = True
    for blk in C.BLOCKS:
        k = blk[0]
        if k == "h1":
            story.append(CondPageBreak(170))
            story.append(Paragraph(inline(blk[1]), S["H1"]))
            story.append(_rule())
        elif k == "h2":
            story.append(CondPageBreak(110))
            story.append(Paragraph(inline(blk[1]), S["H2"]))
        elif k == "p":
            story.append(Paragraph(inline(blk[1]), S["body"]))
        elif k == "bullets":
            for b in blk[1]:
                story.append(Paragraph(inline(b), S["bullet"], bulletText="\u2022"))
            story.append(Spacer(1, 3))
        elif k == "numbered":
            for n, b in enumerate(blk[1], 1):
                story.append(Paragraph(inline(b), S["bullet"], bulletText="%d." % n))
            story.append(Spacer(1, 3))
        elif k == "code":
            story.append(_code(blk[1]))
            story.append(Spacer(1, 6))
        elif k == "note":
            story.append(_note(blk[1]))
            story.append(Spacer(1, 6))
        elif k == "table":
            story.append(_table(blk[1], blk[2], blk[3], landscape_mode=_cur_land[0]))
            story.append(Spacer(1, 7))
        elif k == "landscape":
            _cur_land[0] = True
            story.append(NextPageTemplate("landscape"))
            story.append(PageBreak())
        elif k == "portrait":
            _cur_land[0] = False
            story.append(NextPageTemplate("portrait"))
            story.append(PageBreak())
    doc.multiBuild(story, canvasmaker=NumberedCanvas)


_cur_land = [False]


def _rule():
    return HRFlowable(width=60, thickness=2.5, color=TEAL, hAlign="LEFT", spaceBefore=0, spaceAfter=7)


def _code(text):
    pre = Preformatted(text, ParagraphStyle("code", fontName="Mono", fontSize=7.6, leading=9.8, textColor=INK))
    t = Table([[pre]], colWidths=[(A4[0] - 80) if not _cur_land[0] else (A4[1] - 72)])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CODE_BG), ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def _note(text):
    t = Table([[Paragraph(inline(text), S["note"])]], colWidths=[(A4[0] - 80) if not _cur_land[0] else (A4[1] - 72)])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NOTE_BG), ("LINEBEFORE", (0, 0), (0, -1), 3, NOTE_BAR),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def _table(header_row, rows, weights, landscape_mode=False):
    width = (A4[1] - 72) if landscape_mode else (A4[0] - 80)
    tot = float(sum(weights))
    widths = [width * w / tot for w in weights]
    data = [[Paragraph(inline(h), S["cellh"]) for h in header_row]]
    for r in rows:
        data.append([Paragraph(inline(c), S["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, RULE), ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


# ----------------------------------------------------------------------------------------------
def build_md(path):
    L = []
    L.append("# %s: %s" % (C.TITLE, C.DOC_TITLE))
    L.append("")
    L.append("**%s**" % C.SUBTITLE)
    L.append("")
    L.append("%s | %s | %s" % (C.COURSE, C.VERSION, C.DATE))
    L.append("")
    L.append("| Member | Role | Tools |")
    L.append("|---|---|---|")
    for m in C.TEAM:
        L.append("| **%s** | %s | %s |" % tuple(m))
    L.append("")
    L.append("> Status: planning deliverable. No implementation exists yet; every test is planned, none executed, and no result is claimed. "
             "This file is generated from `docs/plan_content.py` by `docs/build_plan.py` and is identical in content to "
             "`%s`." % C.PDF_NAME)
    L.append("")
    L.append("Reading guide: **P0** required for the MVP, **P1** strong enhancement, **P2** optional. Times are written T+hours:minutes from kickoff. "
             "Task IDs: A = Aryan, F = Frontend (Harsh), Q = Quality/docs (Ayush); test IDs: E engine, I integration, S UI smoke, O oracle, M manual.")
    L.append("")
    L.append("## Contents")
    L.append("")
    for blk in C.BLOCKS:
        if blk[0] == "h1":
            L.append("- " + blk[1])
    L.append("")
    for blk in C.BLOCKS:
        k = blk[0]
        if k == "h1":
            L += ["", "---", "", "## " + blk[1], ""]
        elif k == "h2":
            L += ["", "### " + blk[1], ""]
        elif k == "p":
            L += [blk[1], ""]
        elif k == "bullets":
            L += ["- " + b for b in blk[1]] + [""]
        elif k == "numbered":
            L += ["%d. %s" % (n, b) for n, b in enumerate(blk[1], 1)] + [""]
        elif k == "code":
            L += ["```text", blk[1], "```", ""]
        elif k == "note":
            L += ["> " + blk[1], ""]
        elif k == "table":
            cell = lambda c: c.replace("|", "\\|").replace("\n", "<br>")  # noqa: E731
            L.append("| " + " | ".join(cell(h) for h in blk[1]) + " |")
            L.append("|" + "---|" * len(blk[1]))
            for r in blk[2]:
                L.append("| " + " | ".join(cell(c) for c in r) + " |")
            L.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L).rstrip() + "\n")


if __name__ == "__main__":
    build_pdf(os.path.join(ROOT, C.PDF_NAME))
    build_md(os.path.join(ROOT, C.MD_PATH))
    print("wrote", C.PDF_NAME, "and", C.MD_PATH)
