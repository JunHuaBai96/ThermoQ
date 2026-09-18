# -*- coding: utf-8 -*-
"""ThermoQ user manuals: Times / YaHei typography and Al–Cu–Li COST cases."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"
FIG = OUT_DIR / "manual_figures"
WIN = Path(r"C:\Windows\Fonts")

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#4a4a4a")
RULE = colors.HexColor("#2c2c2c")
RULE_LT = colors.HexColor("#c8c8c8")
TH_BG = colors.HexColor("#2c2c2c")
ROW_BG = colors.HexColor("#f4f4f2")
CODE_BG = colors.HexColor("#f3f1eb")


class HRule(Flowable):
    def __init__(self, width, stroke=0.7, color=RULE, space_before=2, space_after=8):
        super().__init__()
        self.width = width
        self.height = space_before + space_after + 1
        self.stroke = stroke
        self.color = color
        self.space_before = space_before

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.stroke)
        y = self.height - self.space_before
        self.canv.line(0, y, self.width, y)


def _reg(name, filename, index=None):
    path = WIN / filename
    if not path.is_file():
        return False
    kwargs = {} if index is None else {"subfontIndex": index}
    pdfmetrics.registerFont(TTFont(name, str(path), **kwargs))
    return True


def register_fonts():
    ok = all(
        [
            _reg("TimesNR", "times.ttf"),
            _reg("TimesNR-Bold", "timesbd.ttf"),
            _reg("TimesNR-Italic", "timesi.ttf"),
            _reg("TimesNR-BoldItalic", "timesbi.ttf"),
            _reg("CourierNR", "cour.ttf"),
            _reg("YaHei", "msyh.ttc", 0),
            _reg("YaHei-Bold", "msyhbd.ttc", 0),
        ]
    )
    if not ok:
        raise RuntimeError("Required Windows fonts missing (Times New Roman / YaHei / Courier).")
    registerFontFamily(
        "TimesNR",
        normal="TimesNR",
        bold="TimesNR-Bold",
        italic="TimesNR-Italic",
        boldItalic="TimesNR-BoldItalic",
    )
    registerFontFamily("YaHei", normal="YaHei", bold="YaHei-Bold")


def styles_en():
    body = "TimesNR"
    return {
        "lang": "en",
        "cover_kicker": ParagraphStyle("k", fontName="TimesNR-Italic", fontSize=10, leading=13, alignment=TA_CENTER, textColor=MUTED, spaceAfter=10),
        "cover": ParagraphStyle("c", fontName="TimesNR-Bold", fontSize=26, leading=32, alignment=TA_CENTER, textColor=INK, spaceAfter=6),
        "cover_sub": ParagraphStyle("cs", fontName="TimesNR", fontSize=12, leading=16, alignment=TA_CENTER, textColor=MUTED, spaceAfter=4),
        "h1": ParagraphStyle("h1", fontName="TimesNR-Bold", fontSize=13, leading=17, textColor=INK, spaceBefore=14, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName="TimesNR-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("b", fontName=body, fontSize=10.5, leading=15.2, alignment=TA_JUSTIFY, textColor=INK, spaceAfter=6),
        "bullet": ParagraphStyle("bu", fontName=body, fontSize=10.5, leading=15, leftIndent=14, firstLineIndent=-10, textColor=INK, spaceAfter=3),
        "step": ParagraphStyle("st", fontName=body, fontSize=10.5, leading=15, leftIndent=18, firstLineIndent=-14, textColor=INK, spaceAfter=4),
        "cap": ParagraphStyle("cp", fontName="TimesNR-Italic", fontSize=9, leading=12, alignment=TA_CENTER, textColor=MUTED, spaceBefore=3, spaceAfter=10),
        "th": ParagraphStyle("th", fontName="TimesNR-Bold", fontSize=8.5, leading=11, textColor=colors.white),
        "td": ParagraphStyle("td", fontName=body, fontSize=8.5, leading=11.5, textColor=INK),
        "code": ParagraphStyle("cd", fontName="CourierNR", fontSize=8, leading=10.6, textColor=INK),
    }


def styles_zh():
    body = "YaHei"
    return {
        "lang": "zh",
        "cover_kicker": ParagraphStyle("k", fontName="YaHei", fontSize=9.5, leading=14, alignment=TA_CENTER, textColor=MUTED, spaceAfter=10),
        "cover": ParagraphStyle("c", fontName="YaHei-Bold", fontSize=24, leading=32, alignment=TA_CENTER, textColor=INK, spaceAfter=8),
        "cover_sub": ParagraphStyle("cs", fontName="YaHei", fontSize=11, leading=16, alignment=TA_CENTER, textColor=MUTED, spaceAfter=4),
        "h1": ParagraphStyle("h1", fontName="YaHei-Bold", fontSize=13, leading=20, textColor=INK, spaceBefore=14, spaceAfter=7),
        "h2": ParagraphStyle("h2", fontName="YaHei-Bold", fontSize=11, leading=17, textColor=INK, spaceBefore=10, spaceAfter=5),
        "body": ParagraphStyle("b", fontName=body, fontSize=10, leading=17, alignment=TA_JUSTIFY, firstLineIndent=22, textColor=INK, spaceAfter=6),
        "body0": ParagraphStyle("b0", fontName=body, fontSize=10, leading=17, alignment=TA_JUSTIFY, firstLineIndent=0, textColor=INK, spaceAfter=6),
        "bullet": ParagraphStyle("bu", fontName=body, fontSize=10, leading=16.5, leftIndent=16, firstLineIndent=-12, textColor=INK, spaceAfter=3),
        "step": ParagraphStyle("st", fontName=body, fontSize=10, leading=16.5, leftIndent=20, firstLineIndent=-16, textColor=INK, spaceAfter=4),
        "cap": ParagraphStyle("cp", fontName="YaHei", fontSize=8.5, leading=13, alignment=TA_CENTER, textColor=MUTED, spaceBefore=3, spaceAfter=10),
        "th": ParagraphStyle("th", fontName="YaHei-Bold", fontSize=8, leading=12, textColor=colors.white),
        "td": ParagraphStyle("td", fontName=body, fontSize=8, leading=12, textColor=INK),
        "code": ParagraphStyle("cd", fontName="CourierNR", fontSize=8, leading=10.6, textColor=INK),
    }


def P(text, style):
    return Paragraph(str(text).replace("\n", "<br/>"), style)


def bullets(items, s):
    return [P(f"—  {it}", s["bullet"]) for it in items]


def steps(items, s):
    out = []
    for i, t in enumerate(items, 1):
        out.append(P(f"<b>{i}.</b>  {t}", s["step"]))
    return out


def fig(name, caption, s, width_cm=15.6):
    path = FIG / name
    if not path.is_file():
        return [P(f"[missing {name}]", s["cap"])]
    im = PILImage.open(path)
    w_px, h_px = im.size
    w = width_cm * cm
    h = w * h_px / max(w_px, 1)
    max_h = 10.6 * cm
    if h > max_h:
        w *= max_h / h
        h = max_h
    img = Image(str(path), width=w, height=h)
    img.hAlign = "CENTER"
    return [KeepTogether([Spacer(1, 4), img, P(caption, s["cap"])])]


def table(rows, s, widths=None):
    data = []
    for i, row in enumerate(rows):
        st = s["th"] if i == 0 else s["td"]
        data.append([P(c, st) for c in row])
    t = Table(data, colWidths=widths or [4.8 * cm, 11.0 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TH_BG),
                ("GRID", (0, 0), (-1, -1), 0.25, RULE_LT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 1), (-1, -1), ROW_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def code_block(text, s):
    inner = P(text.replace(" ", "&nbsp;").replace("\n", "<br/>"), s["code"])
    t = Table([[inner]], colWidths=[15.8 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.3, RULE_LT),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def footer(canvas, doc, label):
    canvas.saveState()
    canvas.setStrokeColor(RULE_LT)
    canvas.setLineWidth(0.4)
    canvas.line(2.1 * cm, 1.45 * cm, A4[0] - 2.1 * cm, 1.45 * cm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Times-Roman", 8)
    canvas.drawString(2.1 * cm, 1.15 * cm, label)
    canvas.drawRightString(A4[0] - 2.1 * cm, 1.15 * cm, str(doc.page))
    canvas.restoreState()


PAGE_W = A4[0] - 4.2 * cm

TPL0 = """go da
sw tcal9
d-sys al cu li
l-s c
get
go p-3
s-c t=500,p=101325,n=1
s-c w(cu)=0.00001
s-c w(li)=0.00001
l-c
c-e
s-a-v 1 t 300 1000 12.5
save_workspace Al0.00Cu0.00Li_np-T.POL y
step normal
post
s-d-a x t
s-d-a y np(liquid)
make file Al0.00Cu0.00Li_np-T.exp"""

TPL_LOOP = """back
s-c w(cu)=%Cu%
s-c w(li)=%Li%
l-c
c-e
s-a-v 1 t 300 1000 12.5
save_workspace Al%Cu%Cu%Li%Li_np-T.POL y
step normal
post
s-d-a x t
s-d-a y np(liquid)
make file Al%Cu%Cu%Li%Li_np-T.exp"""

TPL_T0 = """back
s-c w(LI)=%LI%
l-c
c-e
S-A-V 1
w(Cu)
0
0.2
0.005
save AlCu-%LI%Li_T0.POL y
step
t-z
FCC_A1
liquid
po
s-d-a x w(CU)
s-d-a y t-k
make file AlCu-%LI%Li_T0.exp"""


def _mr_preview_rows():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_manual_figures as bf

    samples = [
        "Al0.000Cu0.000Li_np-T.exp",
        "Al0.050Cu0.010Li_np-T.exp",
        "Al0.100Cu0.020Li_np-T.exp",
        "Al0.150Cu0.030Li_np-T.exp",
        "Al0.180Cu0.005Li_np-T.exp",
    ]
    rows = [["File", "w(Cu)", "w(Li)", "TL / K", "TS / K", "ΔT / K"]]
    for name in samples:
        p = bf.MR_DIR / name
        if not p.is_file():
            continue
        _t, _f, tl, ts = bf._mr_temps(p)
        wcu, wli = bf._parse_w_cu_li(p.stem)
        if tl is None or ts is None:
            continue
        rows.append(
            [name, f"{wcu:.3f}", f"{wli:.3f}", f"{tl:.1f}", f"{ts:.1f}", f"{tl - ts:.1f}"]
        )
    return rows


def content_en(s, preview):
    b = s["body"]
    story = [
        Spacer(1, 2.4 * cm),
        P("ThermoQ", s["cover_kicker"]),
        P("User Manual", s["cover"]),
        HRule(PAGE_W, stroke=1.0, space_before=4, space_after=12),
        P("Version 1.0.1", s["cover_sub"]),
        P("A worked example on Al–Cu–Li (COST)", s["cover_sub"]),
        P("Using the calculation files shipped in test/", s["cover_sub"]),
        Spacer(1, 1.6 * cm),
        P(
            "Switch the interface with Help → Language. Help → User Manual opens this PDF "
            "in the language currently selected. Windows users may install ThermoQ-1.0.1-Windows-Setup.exe "
            "from GitHub Releases (no Python required).",
            s["cover_sub"],
        ),
        PageBreak(),
        P("1.  Scope", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        P(
            "This manual follows one alloy, Al–Cu–Li, with the COST assessment, from Thermo-Calc "
            "and Pandat batch files through extraction and plotting. The figures are computed from "
            "the .exp / CSV files in test/; they are the same objects ThermoQ writes to Excel.",
            b,
        ),
        P(
            "Menus: File, Import, Plot, Tools, Help. Calculate sits on the main window "
            "(single composition and composition-space batch). After Plot, figures preview in the window "
            "(Save As… / Open). Language labels refresh after Help → Language.",
            b,
        ),
        table(
            [
                ["Menu", "Purpose"],
                ["Import → Pandat to ThermoQ", "Load P.xlsx, Ts.xlsx (required); P-S.xlsx, Ts-S.xlsx (optional)."],
                ["Tools → Composition Converter", "Convert wt% ↔ at% compositions."],
                ["Tools → Generate Thermo-calc Batch File", "Build a .tcm from Template0 + loop body (%Element%, %T%)."],
                ["Tools → Generate Thermo-Calc Batch Data File", "Excel/CSV Data File for Property Model Calculator batch (General Models + Custom/Diffusion)."],
                ["Tools → Extract Thermo-calc Results", "Melting Range, Miscibility Gap, T-zero, TriST Zone."],
                ["Tools → Generate / Extract Pandat", ".pbfx batch (T-zero, Gibbs) and P/Ts, T0.xlsx, TriST."],
                ["Plot", "Phase surfaces, Qtrue, liquidus vectors, k, T-zero, miscibility gap; in-window preview."],
                ["Help → Language", "Switch UI English / 中文 (menus and open tool windows refresh)."],
                ["Help → User Manual / Example", "Open this PDF (by language) or the bundled Example/ folder."],
            ],
            s,
        ),
        Spacer(1, 6),
        P("1.1  Tools → Generate Thermo-Calc Batch Data File", s["h2"]),
        P(
            "Creates Property Model Calculator batch Data Files (.xlsx / .csv) with English headers "
            "(Id, element symbols, Composition unit, Temperature unit; optional Param … / Exp …). "
            "Choose a General Model (Coarsening, CET, Crack Susceptibility, Driving Force, Equilibrium, "
            "Freeze-in, Interfacial Energy, Liquidus/Solidus, Phase Transition, Scheil, Spinodal, T-Zero, "
            "Yield Strength) or Custom/Diffusion (Temperature column, as in Ti–Al–Mn–1173K.xlsx). "
            "One Balance (Bal) element plus a composition grid; the temperature grid maps to the model’s "
            "Param (e.g. Evaluation / Annealing / Start temperature). Phase dropdowns stay on the Thermo-Calc GUI. "
            "Sample: Example/Generate Thermo-Calc Batch Data File/.",
            b,
        ),
        Spacer(1, 8),
        P("2.  Installation", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        *bullets(
            [
                "Python 3.8+ with tkinter.  <font face='CourierNR'>pip install -r requirements.txt</font> then <font face='CourierNR'>python main.py</font>.",
                "TriST workbooks require matplotlib and scipy. Interactive HTML requires plotly.",
            ],
            s,
        ),
        P("3.  Case: melting range (Thermo-Calc)", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        P(
            "Folder for templates: test/Generate Thermo-calc Batch File-Melting Range/Al-Cu-Li/. "
            "Folder for results: test/Extract Thermo-calc Results-Melting Range/Al-Cu-Li_COST/exp/ "
            "(filenames such as Al0.050Cu0.010Li_np-T.exp).",
            b,
        ),
        P("3.1  Generate the .tcm", s["h2"]),
        *steps(
            [
                "Tools → Generate Thermo-calc Batch File.",
                "Template0 = template0.txt (database, system, baseline s-c, first make file).",
                "Loop template = template.txt. Placeholders %Cu% and %Li% are replaced on the Min/Max/Step grid (mass fraction).",
                "Write the merged .tcm (Alltcm.tcm is already in that folder) and run it in Thermo-Calc. Each composition produces one *_np-T.exp.",
            ],
            s,
        ),
        P("Template0 (baseline composition, excerpt):", s["h2"]),
        code_block(TPL0, s),
        Spacer(1, 6),
        P("Loop body (one block per grid point):", s["h2"]),
        code_block(TPL_LOOP, s),
        P("3.2  Extract liquidus and solidus", s["h2"]),
        *steps(
            [
                "Tools → Extract Thermo-calc Results → Melting Range. Select the exp folder. Default filter *_np-T.exp.",
                "The filename supplies w(Cu) and w(Li). Blocks between “$ PLOTTED COLUMNS ARE : T and NP(LIQUID)” and BLOCKEND are read.",
                "Liquidus is the lowest T with NP(LIQUID) = 1; solidus is the highest T with NP(LIQUID) = 0. Optional Template1 writes a .tcm for files listed as errors in Status.",
            ],
            s,
        ),
        *fig(
            "03_mr_npliquid.png",
            "Fig. 1.  NP(LIQUID) versus temperature for Al–0.050Cu–0.010Li (COST). Vertical lines are the liquidus and solidus reported in the extract Excel.",
            s,
        ),
        P("Five rows from that extract (same algorithm as the Melting Range tab):", s["body"]),
        table(preview, s, widths=[6.4 * cm, 1.7 * cm, 1.7 * cm, 1.9 * cm, 1.9 * cm, 1.8 * cm]),
        Spacer(1, 8),
        *fig(
            "04_mr_heatmaps.png",
            "Fig. 2.  Liquidus and melting range over the Al–Cu–Li COST grid in test/…/Al-Cu-Li_COST/exp. Dots are individual .exp files. Plot → Phase Surfaces → Thermo-calc loads the Excel of this map.",
            s,
        ),
        PageBreak(),
        P("4.  Case: T-zero", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        P(
            "Templates: test/Generate Thermo-calc Batch File-T0/Al-Cu-Li/. "
            "Results: test/Extract Thermo-calc Results-T0/Al-Cu-Li_COST/exp/AlCu-0.030Li_T0.exp, etc. "
            "The loop holds w(Li) fixed and scans w(Cu) from 0 to 0.2.",
            b,
        ),
        code_block(TPL_T0, s),
        Spacer(1, 6),
        *steps(
            [
                "Extract Thermo-calc Results → T-zero. Filename → w(Li); XTEXT W(CU) → scan axis; plotted Y → T0 (K).",
                "Save t_zero.xlsx. Plot → Plot T-zero Surface (Thermo-Calc), set the isotherm interval.",
            ],
            s,
        ),
        *fig("05_t0_lines.png", "Fig. 3.  T0(w(Cu)) at fixed w(Li) from every *_T0.exp in the COST folder.", s),
        *fig("05b_t0_surface.png", "Fig. 4.  Linear interpolation of those lines on the w(Cu)–w(Li) plane — the field drawn by Plot T-zero Surface.", s),
        P("5.  Case: liquid miscibility gap", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        P(
            "Files: test/Extract Thermo-calc Results-Miscibility Gap/Liquid/Al-Cu-Li_COST/exp/AlCuLi_800.exp "
            "(one temperature per file). Extract → Miscibility Gap parses T from the name, and XTEXT/YTEXT as mole % Cu and mole % Li.",
            b,
        ),
        *fig(
            "06_lmg_liquid.png",
            "Fig. 5.  Liquid miscibility-gap traces at 600–900 K from the COST .exp set. Plot → Plot Miscibility Gap reconstructs the same boundaries (with interpolation at a requested T).",
            s,
            width_cm=11.2,
        ),
        PageBreak(),
        P("6.  Case: Gibbs energies and TriST Zone", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        P(
            "Files: test/Extract Thermo-calc Results-Gibbs/Al-Cu-Li_COST/exp/, e.g. AlCu-0.050Li_650T_Gibbs.exp. "
            "Each file is one (w(Li), T); the scan axis is w(Cu). Sections are labelled "
            "“$ PLOTTED COLUMNS ARE : W(CU) and GMR(PHASE)”.",
            b,
        ),
        *steps(
            [
                "Extract Thermo-calc Results → TriST Zone. Folder search is recursive; default filter .*_Gibbs\\.exp$. Axes X/Y fill after Browse.",
                "Build TriST workbook (T0_tie_1D, T0_lines, TriST_boundaries, TriST_mask, optional _trist_cube.npz). Grid N is typically 40–80.",
                "Failed files go to Status; Template1 can emit one .tcm per error. Visualize with Plotly / 2D / 3D / GIF.",
            ],
            s,
        ),
        *fig(
            "07_gibbs_gmr.png",
            "Fig. 6.  Molar Gibbs energy of LIQUID and FCC_A1 versus w(Cu) at 650 K and w(Li) = 0.050, taken from one COST Gibbs .exp.",
            s,
        ),
        *fig(
            "09_trist_schematic.png",
            "Fig. 7.  ΔG = G(FCC) − G(L) at 900 K assembled from all *_900T_Gibbs.exp in the same folder. The black contour is ΔG = 0, i.e. the T0 / TriST boundary at that temperature.",
            s,
        ),
        P("7.  Case: Pandat Lever table (same alloy)", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        P(
            "Batch templates: test/Generate Pandat Batch File-T0/Al-Cu-Li_COST/ and …-Gibbs/. "
            "Solidification tables: test/Extract Pandat Results-P Ts (Lever Scheil)/Al-Cu-Li_COST/. "
            "Extract Pandat Results → P/Ts writes P.xlsx / Ts.xlsx / P-S.xlsx / Ts-S.xlsx, then Import to ThermoQ. "
            "Calculate uses Newton interpolation on those tables for Qtrue, Q/P/β, ΔT and ΔTs.",
            b,
        ),
        *fig(
            "08_pandat_lever.png",
            "Fig. 8.  One Lever CSV from that folder (Al–5 wt% Li, 0 Cu): solid fraction and k(Li). Plot → Solid–Liquid Partition Coefficients uses the same k = w(*@solid)/w(*@LIQUID).",
            s,
        ),
        P("8.  Plot tools after extract / import", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        *bullets(
            [
                "Phase Surfaces — Pandat P/Ts or the melting-range Excel of §3.",
                "Qtrue, liquidus vectors, partition k (liquidus / isotherm / isocomposition).",
                "T-zero Surface and Miscibility Gap — Excel from §4 and §5.",
                "Plot Labels: empty fields keep default axis names.",
            ],
            s,
        ),
        P("9.  Where the other test/ trees fit", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        table(
            [
                ["test/ folder", "ThermoQ command"],
                ["Generate Thermo-calc Batch File-{Melting Range, T0, Gibbs, Miscibility Gap}/", "Generate Thermo-calc Batch File"],
                ["Extract Thermo-calc Results-Melting Range/", "Extract → Melting Range"],
                ["Extract Thermo-calc Results-T0/", "Extract → T-zero"],
                ["Extract Thermo-calc Results-Gibbs/", "Extract → TriST Zone"],
                ["Extract Thermo-calc Results-Miscibility Gap/", "Extract → Miscibility Gap"],
                ["Generate Pandat Batch File-T0 / -Gibbs/", "Generate Pandat Batch File"],
                ["Extract Pandat Results-P Ts (Lever Scheil)/", "Extract Pandat → P/Ts"],
                ["Extract Pandat Results-T0/", "Extract Pandat → T-zero"],
                ["Extract Pandat Results-Gibbs/", "Extract Pandat → TriST Zone"],
            ],
            s,
        ),
        Spacer(1, 8),
        P(
            "The same layout is repeated for Al–Cu–Si, Al–Mg–Li, Al–Mg–Si and Ti–Fe–Cu, "
            "with COST, TCAL9, He2009, Peisheng2011 or Bo2013 in the folder name. Help → Example opens the smaller Example/ tree "
            "(includes Generate Thermo-Calc Batch Data File/Ti-Al-Mn-1173K.xlsx).",
            b,
        ),
        P("10.  Notes", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        *bullets(
            [
                "Close an extract workbook in Excel before overwriting it.",
                "Abnormal-point TCM files require a Template1 with %Element% and %T%, after Status has recorded failures.",
                "TriST needs scipy and matplotlib.",
            ],
            s,
        ),
    ]
    return story


def content_zh(s, preview):
    # body0: no indent (after headings / figures)
    b = s.get("body0", s["body"])
    bp = s["body"]

    def para(text):
        return P(text, bp)

    story = [
        Spacer(1, 2.4 * cm),
        P("ThermoQ", s["cover_kicker"]),
        P("软件说明书", s["cover"]),
        HRule(PAGE_W, stroke=1.0, space_before=4, space_after=12),
        P("版本 1.0.1", s["cover_sub"]),
        P("Al–Cu–Li（COST）完整算例", s["cover_sub"]),
        P("插图均由 test/ 中的计算文件直接绘制", s["cover_sub"]),
        Spacer(1, 1.6 * cm),
        P(
            "界面语言：Help → 界面语言。Help → 软件说明书 打开与当前语言对应的 PDF。"
            "Windows 用户可从 GitHub Releases 安装 ThermoQ-1.0.1-Windows-Setup.exe（无需 Python）。",
            s["cover_sub"],
        ),
        PageBreak(),
        P("1.  说明范围", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        para(
            "本说明书以 Al–Cu–Li、COST 热力学评估为一条完整工作链：从 Thermo-Calc / Pandat 批处理，"
            "到提取 Excel，再到绘图。图中曲线与等值线均由 test/ 目录下的 .exp、CSV 计算得到，与软件提取结果一致。"
        ),
        P(
            "菜单为 File、Import、Plot、Tools、Help。Calculate 在主窗口（单点与成分空间批量）。"
            "绘图后可在窗口内预览（另存为… / 打开）。切换语言后菜单与工具窗口文案会刷新。",
            b,
        ),
        table(
            [
                ["菜单", "作用"],
                ["Import → Pandat到ThermoQ", "导入 P.xlsx、Ts.xlsx（必需）及可选 P-S / Ts-S。"],
                ["Tools → 成分换算", "wt% ↔ at% 成分换算。"],
                ["Tools → 生成 Thermo-calc 批处理", "Template0 + 循环体（%元素%、%T%）生成 .tcm。"],
                ["Tools → 生成 Thermo-Calc 批处理 Data File", "Property Model 批处理 Excel/CSV（General Models + 自定义/扩散）。"],
                ["Tools → 提取 Thermo-calc 结果", "熔程、混溶隙、T-zero、TriST 区域。"],
                ["Tools → 生成 / 提取 Pandat", ".pbfx（T-zero、Gibbs）及 P/Ts、T0.xlsx、TriST。"],
                ["Plot", "相面、Qtrue、液相面向量、分配系数、T-zero、混溶隙；界面内预览。"],
                ["Help → Language", "切换英文 / 中文（菜单与已打开工具窗口刷新）。"],
                ["Help → 软件说明书 / 示例", "打开本 PDF（随语言）或随附 Example/ 文件夹。"],
            ],
            s,
        ),
        Spacer(1, 6),
        P("1.1  Tools → 生成 Thermo-Calc 批处理 Data File", s["h2"]),
        para(
            "为 Property Model Calculator 批计算生成 Data File（.xlsx / .csv），英文表头"
            "（Id、元素符号、Composition unit、Temperature unit；可选 Param … / Exp …）。"
            "可选 General Model（粗化、CET、裂纹敏感性、驱动力、平衡、冻结温度、界面能、液/固相线、"
            "相变点、Scheil、调幅、T0、屈服强度）或自定义/扩散（Temperature 列，如 Ti–Al–Mn–1173K.xlsx）。"
            "一个 Balance（Bal）组元加成分网格；温度网格写入对应 Param（如 Evaluation / Annealing / Start temperature）。"
            "相名下拉仍在 Thermo-Calc 界面设置。示例见 Example/Generate Thermo-Calc Batch Data File/。"
        ),
        Spacer(1, 8),
        P("2.  安装", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        *bullets(
            [
                "Python 3.8+（需 tkinter）。<font face='CourierNR'>pip install -r requirements.txt</font>，然后 <font face='CourierNR'>python main.py</font>。",
                "TriST 工作簿需要 matplotlib 与 scipy；交互 HTML 需要 plotly。",
            ],
            s,
        ),
        P("3.  案例：熔程（Thermo-Calc）", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        para(
            "模板目录：test/Generate Thermo-calc Batch File-Melting Range/Al-Cu-Li/。"
            "结果目录：test/Extract Thermo-calc Results-Melting Range/Al-Cu-Li_COST/exp/，"
            "文件名如 Al0.050Cu0.010Li_np-T.exp。"
        ),
        P("3.1  生成 .tcm", s["h2"]),
        *steps(
            [
                "Tools → 生成 Thermo-calc 批处理文件。",
                "Template0 选择 template0.txt（数据库、体系、基准 s-c、第一个 make file）。",
                "循环体选择 template.txt。占位符 %Cu%、%Li% 按 Min/Max/Step 网格替换（质量分数）。",
                "生成合并 .tcm（该目录已提供 Alltcm.tcm），在 Thermo-Calc 中运行，每个成分得到一个 *_np-T.exp。",
            ],
            s,
        ),
        P("Template0（基准成分，节选）：", s["h2"]),
        code_block(TPL0, s),
        Spacer(1, 6),
        P("循环体（每个网格点一块）：", s["h2"]),
        code_block(TPL_LOOP, s),
        P("3.2  提取液相线与固相线", s["h2"]),
        *steps(
            [
                "Tools → 提取 Thermo-calc 结果 → 熔程。选择 exp 文件夹。默认过滤 *_np-T.exp。",
                "文件名给出 w(Cu)、w(Li)。读取 “$ PLOTTED COLUMNS ARE : T and NP(LIQUID)” 至 BLOCKEND 的数据块。",
                "液相线取 NP(LIQUID)=1 的最低温度，固相线取 NP=0 的最高温度。Status 中的失败记录可用 Template1 生成异常点 TCM。",
            ],
            s,
        ),
        *fig(
            "03_mr_npliquid.png",
            "图 1.  Al–0.050Cu–0.010Li（COST）的 NP(LIQUID)–T。竖线为提取表中的液相线与固相线。",
            s,
        ),
        P("按熔程页同一算法得到的 5 行结果：", b),
        table(preview, s, widths=[6.4 * cm, 1.7 * cm, 1.7 * cm, 1.9 * cm, 1.9 * cm, 1.8 * cm]),
        Spacer(1, 8),
        *fig(
            "04_mr_heatmaps.png",
            "图 2.  test/…/Al-Cu-Li_COST/exp 网格上的液相线与熔程。黑点为各 .exp 文件。Plot → 相表面 → Thermo-calc 加载该 Excel。",
            s,
        ),
        PageBreak(),
        P("4.  案例：T-zero", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        para(
            "模板：test/Generate Thermo-calc Batch File-T0/Al-Cu-Li/。"
            "结果：test/Extract Thermo-calc Results-T0/Al-Cu-Li_COST/exp/。"
            "循环中固定 w(Li)，扫描 w(Cu) = 0–0.2。"
        ),
        code_block(TPL_T0, s),
        Spacer(1, 6),
        *steps(
            [
                "提取 → T-zero。文件名 → w(Li)；XTEXT W(CU) → 扫描轴；Y → T0 (K)。",
                "保存 t_zero.xlsx。Plot → Plot T-zero Surface，设置等温线间隔。",
            ],
            s,
        ),
        *fig("05_t0_lines.png", "图 3.  COST 目录中全部 *_T0.exp 的 T0(w(Cu)) 曲线。", s),
        *fig("05b_t0_surface.png", "图 4.  由上述曲线线性插值得到的 T0 面，与 Plot T-zero Surface 所用场相同。", s),
        P("5.  案例：液相混溶隙", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        para(
            "文件：test/Extract Thermo-calc Results-Miscibility Gap/Liquid/Al-Cu-Li_COST/exp/AlCuLi_800.exp（一文件一温度）。"
            "提取 → 混溶隙：从文件名读温度，从 XTEXT/YTEXT 读摩尔百分数。"
        ),
        *fig(
            "06_lmg_liquid.png",
            "图 5.  COST 液相混溶隙（600–900 K）。Plot → Plot Miscibility Gap 重建同一边界，并可在指定温度插值。",
            s,
            width_cm=11.2,
        ),
        PageBreak(),
        P("6.  案例：Gibbs 能与 TriST 区域", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        para(
            "文件：test/Extract Thermo-calc Results-Gibbs/Al-Cu-Li_COST/exp/，例如 AlCu-0.050Li_650T_Gibbs.exp。"
            "每个文件对应一组 (w(Li), T)，扫描轴为 w(Cu)。数据段标记为 “$ PLOTTED COLUMNS ARE : W(CU) and GMR(PHASE)”。"
        ),
        *steps(
            [
                "提取 → TriST 区域。递归搜索，默认过滤 .*_Gibbs\\.exp$。浏览文件夹后自动填充 X/Y。",
                "生成 TriST 工作簿（T0_tie_1D、T0_lines、TriST_boundaries、TriST_mask，可选 _trist_cube.npz）。网格 N 常用 40–80。",
                "失败文件记入 Status，可用 Template1 生成异常点 .tcm。可视化支持 Plotly / 2D / 3D / GIF。",
            ],
            s,
        ),
        *fig(
            "07_gibbs_gmr.png",
            "图 6.  650 K、w(Li)=0.050 时 LIQUID 与 FCC_A1 的摩尔 Gibbs 能随 w(Cu) 的变化（COST Gibbs .exp）。",
            s,
        ),
        *fig(
            "09_trist_schematic.png",
            "图 7.  由同目录全部 *_900T_Gibbs.exp 拼出的 900 K 下 ΔG = G(FCC)−G(L)。黑线为 ΔG=0，即该温度的 T0 / TriST 边界。",
            s,
        ),
        P("7.  案例：Pandat Lever 表（同一合金）", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        para(
            "批处理模板：test/Generate Pandat Batch File-T0/Al-Cu-Li_COST/ 与 -Gibbs/。"
            "凝固表：test/Extract Pandat Results-P Ts (Lever Scheil)/Al-Cu-Li_COST/。"
            "提取 Pandat → P/Ts 写出 P/Ts/P-S/Ts-S，再导入 ThermoQ。"
            "Calculate 在这些表上用 Newton 插值计算 Qtrue、Q/P/β、ΔT、ΔTs。"
        ),
        *fig(
            "08_pandat_lever.png",
            "图 8.  该目录一张 Lever CSV（Al–5 wt% Li，0 Cu）的固相分数与 k(Li)。Plot → 固-液分配系数使用同一 k 定义。",
            s,
        ),
        P("8.  提取 / 导入之后的 Plot", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        *bullets(
            [
                "相表面 — Pandat P/Ts，或第 3 节熔程 Excel。",
                "Qtrue、液相面向量、分配系数（液相线 / 等温 / 等成分）。",
                "T-zero 曲面与混溶隙 — 第 4、5 节 Excel。",
                "图名与坐标轴：留空则用默认轴名。",
            ],
            s,
        ),
        P("9.  其他 test/ 目录", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        table(
            [
                ["test/ 目录", "ThermoQ 中的入口"],
                ["Generate Thermo-calc Batch File-{Melting Range, T0, Gibbs, Miscibility Gap}/", "生成 Thermo-calc 批处理"],
                ["Extract Thermo-calc Results-Melting Range/", "提取 → 熔程"],
                ["Extract Thermo-calc Results-T0/", "提取 → T-zero"],
                ["Extract Thermo-calc Results-Gibbs/", "提取 → TriST 区域"],
                ["Extract Thermo-calc Results-Miscibility Gap/", "提取 → 混溶隙"],
                ["Generate Pandat Batch File-T0 / -Gibbs/", "生成 Pandat 批处理"],
                ["Extract Pandat Results-P Ts (Lever Scheil)/", "提取 Pandat → P/Ts"],
                ["Extract Pandat Results-T0/", "提取 Pandat → T-zero"],
                ["Extract Pandat Results-Gibbs/", "提取 Pandat → TriST Zone"],
            ],
            s,
        ),
        Spacer(1, 8),
        para(
            "Al–Cu–Si、Al–Mg–Li、Al–Mg–Si、Ti–Fe–Cu 的目录结构相同，文件夹名中的 COST、TCAL9、He2009、Peisheng2011、Bo2013 表示所用数据库。"
            "Help → 示例 打开精简的 Example/（含 Generate Thermo-Calc Batch Data File/Ti-Al-Mn-1173K.xlsx）。"
        ),
        P("10.  注意", s["h1"]),
        HRule(PAGE_W, stroke=0.5, color=RULE_LT, space_before=0, space_after=8),
        *bullets(
            [
                "覆盖写入提取结果前请关闭已打开的 Excel。",
                "异常点 TCM 需要含 %元素% 与 %T% 的 Template1，且 Status 中已有失败记录。",
                "TriST 需要 scipy 与 matplotlib。",
            ],
            s,
        ),
    ]
    return story


def build_pdf(path, story, label):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2.1 * cm,
        rightMargin=2.1 * cm,
        topMargin=1.9 * cm,
        bottomMargin=1.9 * cm,
        title="ThermoQ User Manual",
        author="ThermoQ",
    )
    doc.build(
        story,
        onFirstPage=lambda c, d: footer(c, d, label),
        onLaterPages=lambda c, d: footer(c, d, label),
    )
    print("Wrote", path)


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_manual_figures

    build_manual_figures.main()
    register_fonts()
    preview = _mr_preview_rows()
    build_pdf(OUT_DIR / "ThermoQ_User_Manual_EN.pdf", content_en(styles_en(), preview), "ThermoQ  ·  User Manual")
    build_pdf(OUT_DIR / "ThermoQ_User_Manual_ZH.pdf", content_zh(styles_zh(), preview), "ThermoQ  ·  软件说明书")


if __name__ == "__main__":
    main()
