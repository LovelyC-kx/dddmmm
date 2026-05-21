"""Build the CausalStock CS173 final-presentation deck (16:9).

Content follows the final report (docs/final-report/report.tex): the
three-stage framework, the EDA-driven schema, the tabular prediction layer,
and the stratified-vs-chronological result. No ODE, no 0.709 ensemble, no
negative-result slide — the deck and the report tell one story.

Opening funnel: prior-method problems -> what we change -> the pipeline.

  python docs/final-deck/build_deck.py
"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
FIG = HERE.parent / "figures"

NAVY = RGBColor(0x1D, 0x3A, 0x5F)
BLUE = RGBColor(0x2E, 0x6F, 0x9E)
ORANGE = RGBColor(0xE3, 0x86, 0x1F)
INK = RGBColor(0x24, 0x37, 0x48)
GRAY = RGBColor(0x6B, 0x77, 0x85)
LIGHT = RGBColor(0xEE, 0xF2, 0xF7)
CREAM = RGBColor(0xFB, 0xE9, 0xD2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x2F, 0x9E, 0x74)
RED = RGBColor(0xC2, 0x49, 0x2F)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
PAGE = [0]


def tb(slide, x, y, w, h, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = p.get("align", align)
        para.space_after = Pt(p.get("sa", 4))
        para.space_before = Pt(p.get("sb", 0))
        if "lh" in p:
            para.line_spacing = p["lh"]
        for r in p.get("runs", [p]):
            run = para.add_run()
            run.text = r["text"]
            f = run.font
            f.size = Pt(r.get("size", 16))
            f.bold = r.get("bold", False)
            f.italic = r.get("italic", False)
            f.color.rgb = r.get("color", INK)
            f.name = r.get("font", "Calibri")
    return box


def rect(slide, x, y, w, h, fill, rounded=False, line=None):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is not None:
        shp.line.color.rgb = line
        shp.line.width = Pt(1.25)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def pic(slide, name, y, max_w, max_h, x=None, dpi=200):
    path = FIG / name
    iw, ih = Image.open(path).size
    wi, hi = iw / dpi, ih / dpi
    sc = min(max_w / wi, max_h / hi)
    w, h = wi * sc, hi * sc
    if x is None:
        x = (13.333 - w) / 2
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    return x, w, h


def base(kicker, title):
    PAGE[0] += 1
    s = prs.slides.add_slide(BLANK)
    rect(s, 0, 0, 13.333, 0.98, NAVY)
    rect(s, 0, 0.98, 13.333, 0.055, ORANGE)
    tb(s, 0.55, 0.10, 12, 0.3,
       [{"runs": [{"text": kicker, "size": 12, "bold": True, "color": ORANGE}]}])
    tb(s, 0.55, 0.33, 12.2, 0.62,
       [{"runs": [{"text": title, "size": 23, "bold": True, "color": WHITE}]}])
    tb(s, 0.55, 7.10, 9, 0.3,
       [{"runs": [{"text": "CausalStock  ·  CS173 Data Mining  ·  Team 2",
                   "size": 9, "color": GRAY}]}])
    tb(s, 12.1, 7.10, 0.8, 0.3,
       [{"runs": [{"text": str(PAGE[0]), "size": 9, "color": GRAY}]}],
       align=PP_ALIGN.RIGHT)
    return s


def bullets(slide, x, y, w, h, items, size=15, gap=7):
    paras = []
    for it in items:
        lvl, txt, bold, color = 0, it, False, INK
        if isinstance(it, tuple):
            txt = it[0]
            lvl = it[1] if len(it) > 1 else 0
            bold = it[2] if len(it) > 2 else False
            color = it[3] if len(it) > 3 else INK
        mark = "" if lvl else "▪  "
        ind = "      " if lvl else ""
        paras.append({"sa": gap, "lh": 1.12, "runs": [
            {"text": ind + mark, "size": size,
             "color": ORANGE if not lvl else GRAY, "bold": True},
            {"text": txt, "size": size if not lvl else size - 1.5,
             "bold": bold, "color": color}]})
    return tb(slide, x, y, w, h, paras)


def table(slide, x, y, w, data, col_w, fs=11.5, row_h=0.42):
    rows, cols = len(data), len(data[0])
    gt = slide.shapes.add_table(rows, cols, Inches(x), Inches(y),
                                Inches(w), Inches(row_h * rows)).table
    gt.first_row = False
    for ci, cw in enumerate(col_w):
        gt.columns[ci].width = Inches(cw)
    for ri, row in enumerate(data):
        gt.rows[ri].height = Inches(row_h)
        for ci, val in enumerate(row):
            cell = gt.cell(ri, ci)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.09)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.fill.solid()
            if ri == 0:
                cell.fill.fore_color.rgb = NAVY
            else:
                cell.fill.fore_color.rgb = LIGHT if ri % 2 else WHITE
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
            run = para.add_run()
            run.text = str(val)
            run.font.size = Pt(fs)
            run.font.bold = (ri == 0) or (ci == 0)
            run.font.color.rgb = WHITE if ri == 0 else INK
    return gt


def chip(slide, x, y, w, h, head, body):
    rect(slide, x, y, w, h, LIGHT, rounded=True)
    rect(slide, x, y, 0.12, h, ORANGE)
    tb(slide, x + 0.25, y + 0.12, w - 0.4, h - 0.2, [
        {"sa": 3, "runs": [{"text": head, "size": 14, "bold": True, "color": NAVY}]},
        {"runs": [{"text": body, "size": 11, "color": INK}]}])


# ============================================================ S1  TITLE
s = prs.slides.add_slide(BLANK)
PAGE[0] += 1
rect(s, 0, 0, 13.333, 7.5, NAVY)
rect(s, 0, 3.04, 13.333, 0.06, ORANGE)
tb(s, 0.9, 0.95, 12, 0.4, [{"runs": [
    {"text": "CS173  ·  DATA MINING  ·  FINAL PROJECT", "size": 13,
     "bold": True, "color": ORANGE}]}])
tb(s, 0.86, 1.35, 12, 1.4, [{"runs": [
    {"text": "CausalStock", "size": 64, "bold": True, "color": WHITE}]}])
tb(s, 0.9, 2.42, 12, 0.6, [{"runs": [
    {"text": "Event-Structured Temporal Causal Modeling for News-Driven "
     "Stock Prediction", "size": 19, "color": RGBColor(0xC9, 0xD6, 0xE3)}]}])
cards = [("Data-driven", "3 EDA findings  →  3 new event attributes"),
         ("Structured", "20-class events instead of one sentiment score"),
         ("Honest", "stratified + chronological dual reporting")]
for i, (hd, bd) in enumerate(cards):
    cx = 0.9 + i * 3.95
    rect(s, cx, 3.95, 3.7, 1.25, RGBColor(0x27, 0x4A, 0x73), rounded=True)
    tb(s, cx + 0.25, 4.1, 3.3, 0.4, [{"runs": [
        {"text": hd, "size": 15, "bold": True, "color": ORANGE}]}])
    tb(s, cx + 0.25, 4.5, 3.3, 0.7, [{"lh": 1.1, "runs": [
        {"text": bd, "size": 11.5, "color": WHITE}]}])
tb(s, 0.9, 6.4, 12, 0.4, [{"runs": [
    {"text": "Team 2     ·     CS173 Final Project     ·     May 2026",
     "size": 13, "color": RGBColor(0x9D, 0xB0, 0xC4)}]}])

# ============================================================ S2  AGENDA
s = base("AGENDA", "Roadmap")
ag = [("01", "Problem & Innovation", "What prior methods get wrong, and the three "
       "things we change"),
      ("02", "Framework & Data", "The three-stage pipeline; exploratory data "
       "analysis that drives the schema"),
      ("03", "Method", "Phase 1 event extraction · Phase 2 causal discovery · "
       "Phase 3 prediction"),
      ("04", "Experiments & Conclusion", "Results, ablation, comparison, and an "
       "honest read")]
for i, (no, hd, bd) in enumerate(ag):
    y = 1.7 + i * 1.25
    tb(s, 0.7, y, 1.0, 0.8, [{"runs": [
        {"text": no, "size": 30, "bold": True, "color": RGBColor(0xD9, 0xE2, 0xEC)}]}])
    rect(s, 1.85, y + 0.07, 0.06, 0.7, ORANGE)
    tb(s, 2.15, y, 10.5, 0.5, [{"runs": [
        {"text": hd, "size": 19, "bold": True, "color": NAVY}]}])
    tb(s, 2.15, y + 0.46, 10.6, 0.5, [{"lh": 1.1, "runs": [
        {"text": bd, "size": 12.5, "color": GRAY}]}])

# ============================================================ S3  PROBLEM
s = base("01  ·  PROBLEM", "What Prior Methods Get Wrong")
tb(s, 0.6, 1.35, 12, 0.4, [{"runs": [
    {"text": "Most news-driven models compress each article into one sentiment "
     "score. Three things break:", "size": 13, "color": INK}]}])
probs = [("Information Loss",
          "A single sentiment score discards the event's type, magnitude, and "
          "affected entity.",
          "\"Apple launches a new iPhone, outlook +20%\"  →  sentiment +0.8"),
         ("Lack of Causality",
          "Models capture surface correlation, not the logic between events, and "
          "cannot explain a prediction.",
          "Cannot tell a rate hike acting directly vs. via lowered earnings."),
         ("Ignoring Temporal Dynamics",
          "A news impact is treated as instantaneous — missing lag, diffusion, "
          "and gradual effects.",
          "A policy change may surface in prices only days or weeks later.")]
for i, (hd, bd, eg) in enumerate(probs):
    y = 1.95 + i * 1.62
    rect(s, 0.6, y, 12.15, 1.42, LIGHT, rounded=True)
    rect(s, 0.6, y, 0.14, 1.42, RED)
    tb(s, 0.95, y + 0.12, 3.4, 0.5, [{"runs": [
        {"text": f"{i+1}.  {hd}", "size": 15, "bold": True, "color": NAVY}]}])
    tb(s, 0.95, y + 0.52, 7.9, 0.85, [{"lh": 1.12, "runs": [
        {"text": bd, "size": 11.5, "color": INK}]}])
    tb(s, 9.0, y + 0.2, 3.55, 1.05, [{"lh": 1.15, "runs": [
        {"text": eg, "size": 9.5, "italic": True, "color": GRAY}]}])

# ============================================================ S4  WHAT WE CHANGE
s = base("01  ·  INNOVATION", "What We Change — Three Innovations")
tb(s, 0.6, 1.35, 12, 0.4, [{"runs": [
    {"text": "Each prior-method problem maps to one design change in CausalStock:",
     "size": 13, "color": INK}]}])
table(s, 0.6, 1.85, 12.15, [
    ["Prior-method problem", "CausalStock innovation"],
    ["Information loss (sentiment scalar)",
     "Structured event:  (subject, action, object, magnitude) + impact profile"],
    ["Lack of causality",
     "Lag-aware causal discovery over 20 event types  —  a transferable graph"],
    ["Ignoring temporal dynamics",
     "A learned lag matrix T_lag and lag-gated attention"]],
    [5.6, 6.55], fs=12.5, row_h=0.72)
rect(s, 0.6, 5.05, 12.15, 1.6, NAVY, rounded=True)
tb(s, 0.95, 5.22, 11.6, 0.45, [{"runs": [
    {"text": "Two principles cut across all three:", "size": 13, "bold": True,
     "color": ORANGE}]}])
tb(s, 0.95, 5.62, 11.6, 0.95, [{"lh": 1.2, "runs": [{"text":
    "Data-driven — the event schema is earned from a measured EDA of the corpus, "
    "not assumed.   Honest — every result is reported under both a stratified and "
    "a chronological split.", "size": 12.5, "color": WHITE}]}])

# ============================================================ S5  PIPELINE
s = base("01  ·  FRAMEWORK", "End-to-End Pipeline")
pic(s, "fig_architecture.png", 1.45, 5.5, 12.5)
tb(s, 0.6, 6.95, 12, 0.35, [{"align": PP_ALIGN.CENTER, "runs": [
    {"text": "Three stages: extract structured events, learn lag-aware event-type "
     "structure, predict with a transparent tabular model.", "size": 10.5,
     "italic": True, "color": GRAY}]}], align=PP_ALIGN.CENTER)

# ============================================================ S6  EDA
s = base("02  ·  DATA", "Exploratory Data Analysis — The Data Drives the Schema")
pic(s, "fig_datadriven_map.png", 3.0, 11.6, 3.4)
rect(s, 0.6, 1.5, 12.15, 1.35, LIGHT, rounded=True)
tb(s, 0.9, 1.62, 11.6, 0.4, [{"runs": [
    {"text": "We profiled the raw FNSPID 5% subset before fixing the schema:",
     "size": 12.5, "bold": True, "color": NAVY}]}])
tb(s, 0.9, 2.02, 11.6, 0.75, [{"lh": 1.15, "runs": [{"text":
    "88% of articles carry price-movement language and 77% a numeric comparison — "
    "the corpus is event-dense, so structured event extraction is justified over "
    "sentiment scoring. Three further findings each motivate one attribute:",
    "size": 11.5, "color": INK}]}])

# ============================================================ S7  PHASE 1
s = base("03  ·  METHOD — PHASE 1", "Phase 1 — Structured Event Extraction")
rect(s, 0.6, 1.45, 6.05, 3.0, LIGHT, rounded=True)
tb(s, 0.85, 1.6, 5.6, 0.4, [{"runs": [
    {"text": "STRUCTURED EVENT", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 2.05, 5.6, 2.3, [
    "e = (type, subject, object, magnitude)",
    "20-class event ontology (Macro / Corporate / Knowledge / Geopolitical)",
    "+ impact profile: polarity, surprise, scope, novelty, credibility"], size=12.5)
rect(s, 6.8, 1.45, 5.95, 3.0, LIGHT, rounded=True)
tb(s, 7.05, 1.6, 5.5, 0.4, [{"runs": [
    {"text": "FinBERT + MULTI-HEAD DECODER", "size": 12.5, "bold": True,
     "color": ORANGE}]}])
bullets(s, 7.05, 2.05, 5.5, 2.3, [
    "Encoder: ProsusAI/finbert for financial text",
    "Three heads: event-type, argument spans, magnitude",
    "Weak supervision: LLM silver labels + rule/market corrections"], size=12.5)
for i, (big, lb) in enumerate([("10,901", "structured events"), ("20", "event types"),
                               ("84.8%", "avg attribute coverage"),
                               ("ProsusAI", "finbert encoder")]):
    cx = 0.6 + i * 3.07
    rect(s, cx, 4.85, 2.9, 1.2, NAVY, rounded=True)
    tb(s, cx, 5.0, 2.9, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": big, "size": 18, "bold": True, "color": ORANGE}]}],
       align=PP_ALIGN.CENTER)
    tb(s, cx, 5.5, 2.9, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": lb, "size": 10.5, "color": WHITE}]}], align=PP_ALIGN.CENTER)

# ============================================================ S8  PHASE 2
s = base("03  ·  METHOD — PHASE 2", "Phase 2 — Lag-Aware Causal Discovery (STACD)")
rect(s, 0.6, 1.45, 5.7, 4.8, LIGHT, rounded=True)
tb(s, 0.85, 1.6, 5.3, 0.4, [{"runs": [
    {"text": "GOAL — TWO MATRICES", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 2.0, 5.25, 1.5, [
    "A ∈ (0,1)²⁰ˣ²⁰ — directed event-type strength",
    "T_lag — expected lag, in days"], size=12)
tb(s, 0.85, 3.25, 5.3, 0.4, [{"runs": [
    {"text": "MECHANISM — STACD", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 3.65, 5.25, 2.4, [
    "Sparse temporal attention",
    "Time-direction mask — only past attends to future",
    "Lag-aware Gaussian gate + causal-strength gate",
    "NOTEARS-style acyclicity (DAG) regularizer"], size=12)
rect(s, 6.55, 1.45, 6.2, 4.8, NAVY, rounded=True)
tb(s, 6.85, 1.62, 5.7, 0.4, [{"runs": [
    {"text": "ATTENTION MODULATION", "size": 12.5, "bold": True, "color": ORANGE}]}])
for i, eq in enumerate([
    "g_ij = exp( −(|t_i−t_j| − T_lag[k_j,k_i])² / 2σ² )",
    "s̃_ij = s_ij + log m_ij + log g_ij + log A[k_j,k_i]",
    "α_ij = softmax_j ( s̃_ij )",
    "L = L_pred + λ₁‖A‖₁ + λ_DAG · h(A)²"]):
    tb(s, 6.95, 2.2 + i * 0.66, 5.6, 0.5, [{"runs": [
        {"text": eq, "size": 12, "color": WHITE, "font": "Consolas"}]}])
tb(s, 6.95, 5.0, 5.6, 1.1, [{"lh": 1.2, "runs": [{"text":
    "Nodes are event types, not stocks — the resulting graph is designed to "
    "support interpretable, transferable event-chain analysis.", "size": 10.5,
    "italic": True, "color": RGBColor(0xC9, 0xD6, 0xE3)}]}])

# ============================================================ S9  PHASE 3 SETUP
s = base("03  ·  METHOD — PHASE 3", "Phase 3 — Problem Setup & Dataset")
rect(s, 0.6, 1.45, 6.0, 3.05, LIGHT, rounded=True)
tb(s, 0.85, 1.6, 5.6, 0.4, [{"runs": [
    {"text": "INPUTS  →  OUTPUT", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 2.05, 5.6, 2.4, [
    "32 recent news events",
    "30-day OHLCV price window",
    "Target stock identity",
    "Output: next-day direction, threshold ±0.5%"], size=13)
rect(s, 6.85, 1.45, 5.9, 3.05, LIGHT, rounded=True)
tb(s, 7.1, 1.6, 5.5, 0.4, [{"runs": [
    {"text": "THREE-CLASS DISTRIBUTION", "size": 13, "bold": True,
     "color": ORANGE}]}])
for i, (lb, pc, cl) in enumerate([("UP", "39.4%", GREEN), ("DOWN", "43.3%", RED),
                                   ("FLAT", "17.3%", GRAY)]):
    cx = 7.15 + i * 1.92
    rect(s, cx, 2.2, 1.7, 1.6, WHITE, rounded=True)
    tb(s, cx, 2.4, 1.7, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": pc, "size": 21, "bold": True, "color": cl}]}],
       align=PP_ALIGN.CENTER)
    tb(s, cx, 3.0, 1.7, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": lb, "size": 13, "bold": True, "color": INK}]}],
       align=PP_ALIGN.CENTER)
tb(s, 7.1, 3.95, 5.5, 0.4, [{"runs": [
    {"text": "FLAT is the minority class — macro-F1 is emphasized.",
     "size": 10.5, "italic": True, "color": GRAY}]}])
for i, (big, lb) in enumerate([("9,566", "ticker-aligned examples"),
                               ("22", "stocks"), ("2010–2023", "time span")]):
    cx = 0.6 + i * 4.07
    rect(s, cx, 4.8, 3.85, 1.2, NAVY, rounded=True)
    tb(s, cx, 4.95, 3.85, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": big, "size": 19, "bold": True, "color": ORANGE}]}],
       align=PP_ALIGN.CENTER)
    tb(s, cx, 5.47, 3.85, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": lb, "size": 11, "color": WHITE}]}], align=PP_ALIGN.CENTER)

# ============================================================ S10  PHASE 3 MODEL
s = base("03  ·  METHOD — PHASE 3", "Phase 3 — Feature Engineering & Model")
rect(s, 0.6, 1.45, 12.15, 1.4, LIGHT, rounded=True)
tb(s, 0.85, 1.58, 11.6, 0.4, [{"runs": [
    {"text": "x = [ price ‖ event ‖ stock-ID ]   —   a 132-dimensional vector",
     "size": 13, "bold": True, "color": ORANGE}]}])
for i, (d, lb) in enumerate([("Price  28-d", "returns, volatility, log-volume, OHLC"),
                             ("Event  82-d", "type counts, signed/abs magnitude, last type"),
                             ("Stock  22-d", "one-hot ticker identity")]):
    cx = 0.85 + i * 4.0
    tb(s, cx, 1.98, 3.8, 0.4, [{"runs": [
        {"text": d, "size": 13, "bold": True, "color": NAVY}]}])
    tb(s, cx, 2.34, 3.8, 0.5, [{"lh": 1.05, "runs": [
        {"text": lb, "size": 10, "color": GRAY}]}])
rect(s, 0.6, 3.15, 12.15, 3.0, NAVY, rounded=True)
tb(s, 0.95, 3.32, 11.6, 0.4, [{"runs": [
    {"text": "Why HistGradientBoosting (HGB) over a neural net?", "size": 13.5,
     "bold": True, "color": ORANGE}]}])
bullets(s, 0.95, 3.8, 11.6, 2.2, [
    ("Heterogeneous features — handles counts, ratios, and one-hots natively.",
     0, False, WHITE),
    ("Strong, interpretable baseline — quantifies each source's contribution.",
     0, False, WHITE),
    ("Scale-invariant tree splits — minimal feature engineering.", 0, False, WHITE),
    ("Configuration: max_iter 150 · learning_rate 0.04 · l2 0.05.", 0, False,
     RGBColor(0xC9, 0xD6, 0xE3))], size=12.5, gap=9)

# ============================================================ S11  FEATURE DETAIL
s = base("03  ·  METHOD — PHASE 3", "Phase 3 — Feature Detail")
rect(s, 0.6, 1.45, 6.05, 4.7, LIGHT, rounded=True)
tb(s, 0.85, 1.6, 5.6, 0.4, [{"runs": [
    {"text": "PRICE FEATURES  (28-d)", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 2.0, 5.55, 3.9, [
    "Daily returns — 10",
    "Return statistics (mean, std, 5-day) — 4",
    "Log-volume statistics — 2",
    "Relative OHLC summaries — 12"], size=12.5)
rect(s, 6.8, 1.45, 5.95, 4.7, LIGHT, rounded=True)
tb(s, 7.05, 1.6, 5.5, 0.4, [{"runs": [
    {"text": "EVENT FEATURES  (82-d)", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 7.05, 2.0, 5.5, 3.9, [
    "Per-type event counts — 20",
    "Signed magnitude sums — 20",
    "Absolute magnitude sums — 20",
    "Last-event one-hot — 20",
    "Global magnitude statistics — 2"], size=12.5)

# ============================================================ S12  KEY RESULT
s = base("04  ·  EXPERIMENTS", "Key Result — Stratified vs Chronological")
pic(s, "fig_split.png", 1.5, 4.55, 6.0, x=0.6)
rect(s, 7.0, 1.5, 5.8, 5.05, LIGHT, rounded=True)
tb(s, 7.25, 1.66, 5.4, 0.4, [{"runs": [
    {"text": "TWO HONEST READINGS", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 7.25, 2.12, 5.35, 4.2, [
    "Stratified random — macro-F1 0.693, accuracy 0.728. Well above the 0.43 "
    "majority and 0.33 random baselines: the features carry usable signal.",
    "Chronological — macro-F1 0.337. Near random, consistent with semi-strong "
    "market efficiency: forward-time prediction is genuinely hard.",
    ("We report both splits — reporting only the stratified number would "
     "overstate real-world predictive power.", 1, True, NAVY)], size=12)

# ============================================================ S13  ABLATION
s = base("04  ·  EXPERIMENTS", "Ablation — Feature-Group Contribution")
tb(s, 0.6, 1.4, 12, 0.4, [{"runs": [
    {"text": "Stratified-random macro-F1 for the combined-feature models:",
     "size": 13, "color": INK}]}])
table(s, 1.7, 1.95, 9.9, [
    ["Feature set", "Dim.", "Macro-F1"],
    ["Price + events", "110", "0.684"],
    ["Full model:  price + events + stock ID", "132", "0.693"]],
    [6.4, 1.6, 1.9], fs=13, row_h=0.62)
rect(s, 0.6, 4.0, 12.15, 2.3, LIGHT, rounded=True)
tb(s, 0.95, 4.18, 11.6, 0.4, [{"runs": [
    {"text": "Reading", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 0.95, 4.6, 11.6, 1.6, [
    "Adding stock identity lifts macro-F1 from 0.684 to 0.693 — ticker-specific "
    "volatility and reaction patterns remain useful.",
    "The combined price-event-stock representation is learnable under a "
    "stratified split; it is the configuration we report."], size=12)

# ============================================================ S14  COMPARISON
s = base("04  ·  EXPERIMENTS", "Comparison with the NeurIPS 2024 CausalStock")
table(s, 0.55, 1.5, 12.25, [
    ["Axis", "CausalStock (NeurIPS 2024)", "Ours"],
    ["Causality level", "Stock-level graph", "Event-type graph (20×20)"],
    ["News representation", "Dense denoised embedding",
     "Structured event + impact profile"],
    ["Prediction task", "Binary up / down", "3-class with a ±0.5% FLAT zone"],
    ["Evaluation", "Mostly random split", "Stratified + chronological"]],
    [2.8, 4.5, 4.95], fs=11.5, row_h=0.66)
rect(s, 0.55, 5.0, 12.25, 1.55, NAVY, rounded=True)
tb(s, 0.9, 5.18, 11.6, 0.45, [{"runs": [
    {"text": "Complementary, not competing", "size": 13, "bold": True,
     "color": ORANGE}]}])
tb(s, 0.9, 5.58, 11.6, 0.85, [{"lh": 1.18, "runs": [{"text":
    "Event-type causality transfers across companies and markets; stock-level "
    "causality is bound to a fixed company universe. We evaluate on a stricter, "
    "dual-split protocol.", "size": 12, "color": WHITE}]}])

# ============================================================ S15  CONCLUSION
s = base("04  ·  CONCLUSION", "Conclusion & Future Work")
rect(s, 0.6, 1.5, 6.0, 4.7, LIGHT, rounded=True)
rect(s, 0.6, 1.5, 6.0, 0.5, GREEN)
tb(s, 0.8, 1.58, 5.6, 0.4, [{"runs": [
    {"text": "WHAT WE CONTRIBUTE", "size": 12.5, "bold": True, "color": WHITE}]}])
bullets(s, 0.8, 2.15, 5.6, 3.9, [
    "A clearer event-structured problem formulation.",
    "An EDA-driven event schema — three attributes earned from measured data.",
    "A mathematically specified lag-aware event-causal model.",
    "An honest analysis separating in-distribution information content from "
    "forward-time predictability."], size=11.5, gap=9)
rect(s, 6.75, 1.5, 6.0, 4.7, LIGHT, rounded=True)
rect(s, 6.75, 1.5, 6.0, 0.5, BLUE)
tb(s, 6.95, 1.58, 5.6, 0.4, [{"runs": [
    {"text": "FUTURE WORK", "size": 12.5, "bold": True, "color": WHITE}]}])
bullets(s, 6.95, 2.15, 5.6, 3.9, [
    "Integrate A and T_lag directly as Phase-3 features.",
    "Model cross-stock event propagation.",
    "Regime-aware temporal encoding against distribution shift.",
    "Rolling walk-forward validation as the default protocol."], size=11.5, gap=9)
tb(s, 0.6, 6.35, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
    {"text": "We do not claim solved stock prediction — we claim a clean "
     "formulation and an honest study of where structured news helps.",
     "size": 11, "italic": True, "color": GRAY}]}], align=PP_ALIGN.CENTER)

# ============================================================ S16  Q&A
s = base("THANK YOU", "Q & A")
rect(s, 0.6, 2.4, 12.15, 2.6, NAVY, rounded=True)
tb(s, 0.6, 3.0, 12.15, 0.7, [{"align": PP_ALIGN.CENTER, "runs": [
    {"text": "Q & A   —   Thank you for listening", "size": 24, "bold": True,
     "color": WHITE}]}], align=PP_ALIGN.CENTER)
tb(s, 0.6, 3.85, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
    {"text": "CausalStock  ·  CS173 Data Mining Final  ·  Team 2",
     "size": 13, "color": RGBColor(0x9D, 0xB0, 0xC4)}]}], align=PP_ALIGN.CENTER)

out = HERE / "CausalStock_CS173_Final.pptx"
prs.save(out)
print("saved", out, "—", len(prs.slides._sldIdLst), "slides")
