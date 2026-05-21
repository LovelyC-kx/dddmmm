"""Build the CausalStock CS173 final-presentation deck (16:9).

Rebuilds the deck from corrected content: CausalStock naming, comparison +
data front-loaded, real ablation numbers, ODE demoted, honest causal-graph
slide. Figures are pulled from ../figures (run make_deck_figures.py first).

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
    {"text": "CausalStock", "size": 66, "bold": True, "color": WHITE}]}])
tb(s, 0.9, 2.45, 12, 0.6, [{"runs": [
    {"text": "Structured Event-Chain Modeling for News-Driven Stock Prediction",
     "size": 21, "color": RGBColor(0xC9, 0xD6, 0xE3)}]}])
tb(s, 0.9, 3.25, 12, 0.5, [{"runs": [
    {"text": "数据驱动的结构化事件链建模", "size": 16,
     "color": RGBColor(0x9D, 0xB0, 0xC4)}]}])
cards = [("Data-driven", "3 EDA findings  →  3 new event attributes"),
         ("Interpretable", "structured events + transparent tabular model"),
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
ag = [("01", "Data & Problem", "FNSPID task; the CausalStock (NeurIPS'24) baseline and its gap"),
      ("02", "EDA", "Missingness, headline duplication, event-clue density"),
      ("03", "Method", "Structured events + lag-aware event-type causal discovery"),
      ("04", "Experiments", "Attribute coverage, ablation, stratified vs chronological"),
      ("05", "Discussion", "Limits, what we learned, future work")]
for i, (no, hd, bd) in enumerate(ag):
    y = 1.5 + i * 1.07
    tb(s, 0.7, y, 1.0, 0.8, [{"runs": [
        {"text": no, "size": 30, "bold": True, "color": RGBColor(0xD9, 0xE2, 0xEC)}]}])
    rect(s, 1.85, y + 0.07, 0.06, 0.62, ORANGE)
    tb(s, 2.15, y, 10.5, 0.5, [{"runs": [
        {"text": hd, "size": 19, "bold": True, "color": NAVY}]}])
    tb(s, 2.15, y + 0.46, 10.5, 0.4, [{"runs": [
        {"text": bd, "size": 12.5, "color": GRAY}]}])

# ============================================================ S3  PROBLEM
s = base("01  ·  PROBLEM", "Task: News-Driven Stock Movement Prediction")
rect(s, 0.6, 1.45, 6.0, 3.0, LIGHT, rounded=True)
tb(s, 0.85, 1.6, 5.6, 0.4, [{"runs": [
    {"text": "SETUP", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 2.05, 5.6, 2.4, [
    "Input:  32 recent events  +  30-day OHLCV  +  ticker ID",
    "Output:  next-day direction  —  UP / DOWN / FLAT",
    "Decision threshold  δ = 0.5%",
    "Dataset:  5% FNSPID subset  ·  22 stocks  ·  2010–2023"], size=13.5)
rect(s, 6.85, 1.45, 5.9, 3.0, LIGHT, rounded=True)
tb(s, 7.1, 1.6, 5.5, 0.4, [{"runs": [
    {"text": "CLASS DISTRIBUTION (3-class, imbalanced)", "size": 13,
     "bold": True, "color": ORANGE}]}])
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
    {"text": "FLAT is the hard minority class — central to the honest evaluation.",
     "size": 10.5, "italic": True, "color": GRAY}]}])
rect(s, 0.6, 4.7, 12.15, 1.55, NAVY, rounded=True)
tb(s, 0.95, 4.9, 11.6, 0.45, [{"runs": [
    {"text": "Why it is hard", "size": 14, "bold": True, "color": ORANGE}]}])
tb(s, 0.95, 5.3, 11.6, 0.85, [{"lh": 1.15, "runs": [{"text":
    "A news item is not a standalone signal: a rate hike triggers a chain — credit "
    "tightening → tech-sector revaluation → supply-chain cooling — over hours to "
    "weeks. Sentiment scores collapse this structure.", "size": 12.5,
    "color": WHITE}]}])

# ============================================================ S4  BASELINE
s = base("01  ·  BASELINE", "Baseline — CausalStock (NeurIPS 2024)")
tb(s, 0.6, 1.4, 12, 0.4, [{"runs": [
    {"text": "What it does", "size": 14, "bold": True, "color": ORANGE}]}])
for i, (hd, bd) in enumerate([
    ("Denoised news encoder",
     "An LLM compresses each article into one dense embedding vector."),
    ("Stock-level causal graph",
     "Lag-dependent causality is learned between stocks (s₁ ↔ s₂).")]):
    chip(s, 0.6 + i * 6.15, 1.8, 5.85, 1.15, hd, bd)
tb(s, 0.6, 3.2, 12, 0.4, [{"runs": [
    {"text": "Two blind spots — and our response", "size": 14, "bold": True,
     "color": ORANGE}]}])
table(s, 0.6, 3.6, 12.15, [
    ["Baseline blind spot", "CausalStock response"],
    ["One vector per article hides event type, magnitude, affected entity",
     "Structured event:  (S, A, O, M)  +  impact profile"],
    ["Stock-level graph cannot say what kind of event drove a link",
     "Causal graph over 20 event types, transferable across firms"]],
    [6.07, 6.08], fs=12.5, row_h=0.62)
rect(s, 0.6, 5.75, 12.15, 0.95, CREAM, rounded=True)
tb(s, 0.95, 5.92, 11.5, 0.65, [{"lh": 1.12, "runs": [
    {"text": "Takeaway:  ", "size": 12.5, "bold": True, "color": NAVY},
    {"text": "the baseline is strong but structure-blind — CausalStock restores "
     "event structure and moves causality to the transferable event-type level.",
     "size": 12.5, "color": INK}]}])

# ============================================================ S5  COMPARE
s = base("01  ·  POSITIONING", "Positioning — Ours vs the NeurIPS 2024 Baseline")
table(s, 0.55, 1.45, 12.25, [
    ["Dimension", "CausalStock (NeurIPS 2024)", "Ours", "Data evidence"],
    ["News representation", "Denoised dense embedding",
     "(S,A,O,M) + impact profile", "88% price / 77% numeric cues"],
    ["Causal graph nodes", "Stock-level  (22×22)",
     "Event-type level  (20×20)", "long-tailed event distribution"],
    ["Source trust", "—", "URL-domain credibility",
     "Publisher 79% / Author 68% missing"],
    ["Repetition", "—", "Novelty attribute", "29% duplicate headlines"],
    ["Multi-stock news", "implicit", "explicit Scope attribute",
     "89.2% multi-scope cues"],
    ["Evaluation", "mostly random split", "stratified + chronological",
     "0.69 → 0.34 temporal drift"]],
    [2.5, 3.05, 3.2, 3.5], fs=11.5, row_h=0.6)
rect(s, 0.55, 6.05, 12.25, 0.92, NAVY, rounded=True)
tb(s, 0.9, 6.24, 11.6, 0.6, [{"runs": [
    {"text": "Core claim:  ", "size": 13, "bold": True, "color": ORANGE},
    {"text": "every method choice in CausalStock is justified by a specific, "
     "measured finding in the FNSPID data.", "size": 13, "color": WHITE}]}])

# ============================================================ S6  EDA-1
s = base("02  ·  EDA  (1/2)", "Dataset Snapshot & Missingness Audit")
for i, (big, lb) in enumerate([("10,901", "structured events"),
                               ("9,566", "ticker-aligned examples"),
                               ("22", "stocks"), ("2010–23", "time span")]):
    cx = 0.6 + i * 1.62
    rect(s, cx, 1.45, 1.5, 1.0, LIGHT, rounded=True)
    tb(s, cx, 1.56, 1.5, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": big, "size": 17, "bold": True, "color": NAVY}]}],
       align=PP_ALIGN.CENTER)
    tb(s, cx, 2.04, 1.5, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": lb, "size": 9, "color": GRAY}]}], align=PP_ALIGN.CENTER)
pic(s, "fig_eda_missing.png", 2.65, 6.2, 3.6, x=0.6)
rect(s, 7.5, 1.45, 5.3, 4.7, LIGHT, rounded=True)
tb(s, 7.75, 1.6, 4.9, 0.4, [{"runs": [
    {"text": "OBSERVATIONS", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 7.75, 2.05, 4.85, 4.0, [
    "Publisher 79% / Author 68% missing — cannot be used as supervision.",
    "URL missing only 0.02% — a clean, near-complete signal.",
    ("→ derive a credibility score from the URL domain", 1),
    "Duplicate headlines 29.0% — the same event reported many times.",
    ("→ first report carries peak impact; repeats decay → novelty", 1)], size=12.5)

# ============================================================ S7  EDA-2
s = base("02  ·  EDA  (2/2)", "Event Density & Long-Tailed Distribution")
pic(s, "fig_eda_clues.png", 1.4, 4.3, 6.2, x=0.55)
pic(s, "fig_event_dist.png", 1.4, 4.3, 6.4, x=6.7)
rect(s, 0.55, 5.95, 12.25, 1.0, NAVY, rounded=True)
tb(s, 0.9, 6.07, 11.6, 0.8, [
    {"sa": 2, "runs": [{"text": "Two design drivers:", "size": 12.5,
                        "bold": True, "color": ORANGE}]},
    {"lh": 1.12, "runs": [{"text":
        "(1)  the corpus is event-dense (88% price, 77% numeric cues) → a "
        "structured event representation is justified over sentiment;   "
        "(2)  event types are long-tailed (top-3 = 55%) → class-aware training.",
        "size": 11.5, "color": WHITE}]}])

# ============================================================ S8  INNOVATION
s = base("02  ·  FROM DATA TO DESIGN", "The Innovation — Three Findings, Three Attributes")
pic(s, "fig_datadriven_map.png", 1.5, 4.5, 11.6)
rect(s, 0.8, 6.25, 11.7, 0.82, CREAM, rounded=True)
tb(s, 1.1, 6.41, 11.2, 0.55, [{"runs": [
    {"text": "Not bolted on:  ", "size": 12.5, "bold": True, "color": NAVY},
    {"text": "novelty, credibility and scope are each earned from a measured "
     "property of the FNSPID corpus.", "size": 12.5, "color": INK}]}])

# ============================================================ S9  FRAMEWORK
s = base("03  ·  METHOD", "End-to-End Framework")
pic(s, "fig_architecture.png", 1.35, 5.6, 12.5)

# ============================================================ S10  PHASE 1
s = base("03  ·  METHOD — PHASE 1", "Structured Event Extraction")
rect(s, 0.6, 1.45, 6.05, 3.05, LIGHT, rounded=True)
tb(s, 0.85, 1.6, 5.6, 0.4, [{"runs": [
    {"text": "EXTRACTOR — FinBERT + multi-head decoder", "size": 12.5,
     "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 2.05, 5.6, 2.4, [
    "Type head — 20-way event-type softmax",
    "Span heads — subject / object boundaries",
    "Magnitude head — scalar event intensity",
    "Aux heads — scope / novelty / credibility"], size=12.5)
rect(s, 6.8, 1.45, 5.95, 3.05, LIGHT, rounded=True)
tb(s, 7.05, 1.6, 5.5, 0.4, [{"runs": [
    {"text": "WEAK SUPERVISION + HYBRID CORRECTION", "size": 12.5,
     "bold": True, "color": ORANGE}]}])
bullets(s, 7.05, 2.05, 5.5, 2.4, [
    "Silver labels from GPT-4 / DeepSeek",
    "Rule correction for surprise:  (actual − expected) / |expected|",
    "Novelty from sentence-embedding similarity",
    "Credibility from a URL-domain whitelist"], size=12.5)
tb(s, 0.6, 4.7, 12, 0.4, [{"runs": [
    {"text": "Event  =  (Subject, Action, Object, Magnitude)  +  impact profile "
     "{ polarity, surprise, scope, novelty, credibility }", "size": 13,
     "bold": True, "color": NAVY}]}])
for i, (big, lb) in enumerate([("10,901", "events extracted"), ("20", "event types"),
                               ("4", "decoder heads"), ("84.8%", "avg attr. coverage")]):
    cx = 0.6 + i * 3.07
    rect(s, cx, 5.2, 2.9, 1.15, NAVY, rounded=True)
    tb(s, cx, 5.34, 2.9, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": big, "size": 20, "bold": True, "color": ORANGE}]}],
       align=PP_ALIGN.CENTER)
    tb(s, cx, 5.86, 2.9, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": lb, "size": 11, "color": WHITE}]}], align=PP_ALIGN.CENTER)

# ============================================================ S11  ATTRS
s = base("03  ·  METHOD — PHASE 1", "The Three Data-Driven Attributes")
defs = [("Novelty", "novelty = 1 − max sim(textᵢ, recent same-ticker news)",
         "Decays the weight of repeated reporting; novel = 1.", GREEN),
        ("Credibility", "credibility = score( domain(URLᵢ) )",
         "3-tier domain whitelist; robust to missing Publisher / Author.", BLUE),
        ("Scope", "scope ∈ { single, sector, market, global }",
         "Down-weights ticker assignment when news is not single-stock.", ORANGE)]
for i, (hd, eq, bd, cl) in enumerate(defs):
    y = 1.5 + i * 1.72
    rect(s, 0.6, y, 12.15, 1.5, LIGHT, rounded=True)
    rect(s, 0.6, y, 0.14, 1.5, cl)
    tb(s, 0.95, y + 0.13, 3.0, 0.5, [{"runs": [
        {"text": hd, "size": 18, "bold": True, "color": NAVY}]}])
    tb(s, 0.95, y + 0.62, 5.4, 0.8, [{"lh": 1.1, "runs": [
        {"text": bd, "size": 11.5, "color": INK}]}])
    rect(s, 6.5, y + 0.42, 6.0, 0.66, WHITE, rounded=True)
    tb(s, 6.7, y + 0.55, 5.7, 0.5, [{"runs": [
        {"text": eq, "size": 12, "bold": True, "color": INK, "font": "Consolas"}]}])

# ============================================================ S12  PHASE 2
s = base("03  ·  METHOD — PHASE 2", "Lag-Aware Event-Type Causal Discovery (STACD)")
rect(s, 0.6, 1.45, 5.7, 4.7, LIGHT, rounded=True)
tb(s, 0.85, 1.6, 5.3, 0.4, [{"runs": [
    {"text": "OBJECTIVE", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 2.0, 5.25, 1.5, [
    "A ∈ (0,1)²⁰ˣ²⁰ — directed event-type strength",
    "T_lag ∈ ℝ₊²⁰ˣ²⁰ — expected delay (days)"], size=12)
tb(s, 0.85, 3.15, 5.3, 0.4, [{"runs": [
    {"text": "DESIGN CHOICES", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 0.85, 3.5, 5.25, 2.5, [
    "Time-direction mask — only past attends to future",
    "Gaussian lag gate — attention peaks at the learned lag",
    "Causal-strength gate — type-pair prior in log-space",
    "DAG regularization — NOTEARS acyclicity"], size=12)
rect(s, 6.55, 1.45, 6.2, 4.7, NAVY, rounded=True)
tb(s, 6.85, 1.62, 5.7, 0.4, [{"runs": [
    {"text": "MECHANISM — sparse temporal attention", "size": 12.5,
     "bold": True, "color": ORANGE}]}])
for i, eq in enumerate([
    "gᵢⱼ = exp( −(|tᵢ−tⱼ| − T_lag[kⱼ,kᵢ])² / 2σ² )",
    "s̃ᵢⱼ = sᵢⱼ + log mᵢⱼ + log gᵢⱼ + log A[kⱼ,kᵢ]",
    "αᵢⱼ = softmaxⱼ ( s̃ᵢⱼ )",
    "L = L_pred + λ₁‖A‖₁ + λ_DAG · h(A)²",
    "h(A) = tr( e^{A⊙A} ) − K        (NOTEARS)"]):
    tb(s, 6.95, 2.15 + i * 0.62, 5.6, 0.5, [{"runs": [
        {"text": eq, "size": 12.5, "color": WHITE, "font": "Consolas"}]}])
tb(s, 6.95, 5.45, 5.6, 0.55, [{"lh": 1.1, "runs": [{"text":
    "Nodes are event types, not stocks — the graph transfers across companies.",
    "size": 10.5, "italic": True, "color": RGBColor(0xC9, 0xD6, 0xE3)}]}])

# ============================================================ S13  GRAPH (honest)
s = base("03  ·  METHOD — PHASE 2", "Phase 2 Result — The Causal Graph Did Not Learn")
tb(s, 0.6, 1.35, 12, 0.4, [{"runs": [
    {"text": "STACD trained 12 epochs on 9,527 real event sequences — a clear, "
     "honestly-reported negative result:", "size": 12.5, "color": INK}]}])
pic(s, "fig_causal_matrix.png", 1.95, 3.55, 7.6, x=0.5)
rect(s, 8.3, 1.85, 4.5, 4.45, LIGHT, rounded=True)
tb(s, 8.55, 2.0, 4.05, 0.4, [{"runs": [
    {"text": "DIAGNOSED NEGATIVE RESULT", "size": 12, "bold": True, "color": RED}]}])
bullets(s, 8.55, 2.45, 4.1, 3.8, [
    "Trained A: mean 0.267, std 0.048 — identical to its initialization (0.269 / 0.048).",
    "Across 12 epochs A barely moves (mean change 0.005 per entry).",
    "STACD prediction head ≈ 0.5 (random) — almost no gradient reaches the graph.",
    ("→ same weak forward signal as the chronological collapse", 1, True, NAVY)],
    size=11)
rect(s, 0.6, 6.4, 12.2, 0.72, CREAM, rounded=True)
tb(s, 0.9, 6.54, 11.6, 0.5, [{"runs": [
    {"text": "Honest takeaway:  ", "size": 11.5, "bold": True, "color": NAVY},
    {"text": "end-to-end causal discovery is not identifiable on a low-signal "
     "target — next step: estimate the graph from observed lagged co-occurrence.",
     "size": 11.5, "color": INK}]}])

# ============================================================ S14  PHASE 3
s = base("03  ·  METHOD — PHASE 3", "Prediction Layer")
rect(s, 0.6, 1.45, 12.15, 1.5, LIGHT, rounded=True)
tb(s, 0.85, 1.58, 11.6, 0.4, [{"runs": [
    {"text": "FEATURE STACK  —  132-dimensional vector", "size": 12.5,
     "bold": True, "color": ORANGE}]}])
for i, (d, lb) in enumerate([("Price  28-d", "returns, volatility, log-volume, OHLC"),
                             ("Event  82-d", "type counts, signed/abs magnitude, last type"),
                             ("Stock  22-d", "one-hot ticker identity")]):
    cx = 0.85 + i * 4.0
    tb(s, cx, 2.0, 3.8, 0.4, [{"runs": [
        {"text": d, "size": 13, "bold": True, "color": NAVY}]}])
    tb(s, cx, 2.36, 3.8, 0.5, [{"lh": 1.05, "runs": [
        {"text": lb, "size": 10, "color": GRAY}]}])
rect(s, 0.6, 3.2, 5.95, 2.95, LIGHT, rounded=True)
tb(s, 0.85, 3.35, 5.5, 0.4, [{"runs": [
    {"text": "WHY HISTGRADIENTBOOSTING", "size": 12.5, "bold": True,
     "color": ORANGE}]}])
bullets(s, 0.85, 3.75, 5.45, 2.3, [
    "Handles heterogeneous features (counts, ratios, one-hots)",
    "Strong yet transparent — readable vs heavy neural nets",
    "Scale-invariant tree splits — no feature scaling",
    "max_iter 150 · lr 0.04 · L2 0.05"], size=12)
rect(s, 6.8, 3.2, 5.95, 2.95, NAVY, rounded=True)
tb(s, 7.05, 3.35, 5.5, 0.4, [{"runs": [
    {"text": "CAUSAL ENSEMBLE", "size": 12.5, "bold": True, "color": ORANGE}]}])
bullets(s, 7.05, 3.75, 5.45, 2.3, [
    ("Tabular features  +  learned causal-temporal", 0, False, WHITE),
    ("event representations from Phase 2 / 3", 1, False, RGBColor(0xC9, 0xD6, 0xE3)),
    ("Meta-ensemble over several gradient-boosted heads", 0, False, WHITE),
    ("→ this is the configuration that reaches 0.709", 1, False,
     RGBColor(0xC9, 0xD6, 0xE3))], size=12)

# ============================================================ S15  EXP-1
s = base("04  ·  EXPERIMENTS", "Experiment 1 — Auxiliary Attribute Coverage")
px, pw, ph = pic(s, "fig_coverage.png", 1.55, 4.4, 7.0, x=0.55)
rect(s, 8.0, 1.55, 4.8, 4.5, LIGHT, rounded=True)
tb(s, 8.25, 1.7, 4.4, 0.4, [{"runs": [
    {"text": "TAKEAWAYS", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 8.25, 2.15, 4.4, 3.7, [
    "Polarity, scope, novelty, credibility — ~85% coverage: dense, usable signals.",
    "Surprise — only 6.6%: sparse but high-value, concentrated in earnings & macro.",
    ("→ treat the four as standard features; treat surprise as a "
     "sparse high-information indicator", 1)], size=12.5)

# ============================================================ S16  EXP-2
s = base("04  ·  EXPERIMENTS", "Experiment 2 — Main Results & Ablation")
pic(s, "fig_ablation.png", 1.5, 4.05, 8.4, x=0.55)
rect(s, 9.2, 1.5, 3.6, 5.1, LIGHT, rounded=True)
tb(s, 9.42, 1.65, 3.3, 0.4, [{"runs": [
    {"text": "READING", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 9.42, 2.1, 3.25, 4.4, [
    "Tabular news+price+stock — 0.693 macro-F1.",
    "Causal ensemble — 0.709: a consistent +1.6-point gain.",
    "ODE-only variants stay below the tabular baseline — not featured.",
    ("single seed — read as a preliminary point estimate", 1)], size=11.5)

# ============================================================ S17  EXP-3
s = base("04  ·  EXPERIMENTS", "Experiment 3 — Honest Evaluation")
pic(s, "fig_split.png", 1.5, 4.5, 6.0, x=0.6)
rect(s, 7.0, 1.5, 5.8, 5.05, LIGHT, rounded=True)
tb(s, 7.25, 1.66, 5.4, 0.4, [{"runs": [
    {"text": "THREE HONEST READINGS", "size": 13, "bold": True, "color": ORANGE}]}])
bullets(s, 7.25, 2.12, 5.35, 4.2, [
    "Stratified 0.693 — features carry usable signal in-distribution.",
    "Chronological 0.337 ≈ random 0.333 — forward-time direction at ±0.5% is "
    "near-impossible (consistent with semi-strong market efficiency).",
    "FLAT collapses under the time split — the model degenerates to the "
    "majority classes.",
    ("Stratified-only reporting would overstate real predictive power.", 1,
     True, NAVY)], size=12)

# ============================================================ S18  DISCUSSION
s = base("05  ·  DISCUSSION", "Limits, What We Learned, Future Work")
cols = [("WHAT WE LEARNED", GREEN, [
    "EDA-driven attribute design is the strongest, most defensible contribution.",
    "Three negative results share one cause — the weak forward-time signal.",
    "Stratified-only reporting overstates real-world power."]),
        ("LIMITS", RED, [
    "End-to-end causal discovery did not learn — graph stays at initialization.",
    "Neural-ODE propagation overfits — low-SNR daily data, high-capacity "
    "continuous-time models fit noise.",
    "Single seed; 5% subset; 22 tickers limit regime coverage."]),
        ("FUTURE WORK", BLUE, [
    "Event-type graph from lagged co-occurrence (no end-to-end gradient).",
    "Multi-seed confidence intervals; rolling walk-forward validation.",
    "LLM-assisted surprise extraction to lift its 6.6% coverage."])]
for i, (hd, cl, items) in enumerate(cols):
    cx = 0.6 + i * 4.07
    rect(s, cx, 1.5, 3.85, 4.95, LIGHT, rounded=True)
    rect(s, cx, 1.5, 3.85, 0.5, cl, rounded=False)
    tb(s, cx + 0.2, 1.58, 3.5, 0.4, [{"runs": [
        {"text": hd, "size": 12.5, "bold": True, "color": WHITE}]}])
    bullets(s, cx + 0.2, 2.15, 3.5, 4.1, items, size=11, gap=8)

# ============================================================ S19  REFS
s = base("REFERENCES & Q&A", "Key References  ·  Thank You")
refs = [("Baseline", "Li et al.  CausalStock: Deep End-to-end Causal Discovery for "
         "News-driven Stock Movement Prediction.  NeurIPS 2024."),
        ("Data", "Dong et al.  FNSPID: A Comprehensive Financial News Dataset in "
         "Time Series.  KDD ADS 2024."),
        ("NLP", "Araci.  FinBERT: Financial Sentiment Analysis with Pre-trained "
         "Language Models.  arXiv 2019."),
        ("Causal", "Zheng et al.  DAGs with NO TEARS.  NeurIPS 2018."),
        ("Causal", "Tank et al.  Neural Granger Causality.  TPAMI 2022."),
        ("Caveat", "Reisach et al.  Beware of the Simulated DAG!  NeurIPS 2021.")]
for i, (tag, txt) in enumerate(refs):
    y = 1.5 + i * 0.62
    rect(s, 0.6, y, 1.25, 0.46, NAVY, rounded=True)
    tb(s, 0.6, y + 0.08, 1.25, 0.35, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": tag, "size": 10, "bold": True, "color": ORANGE}]}],
       align=PP_ALIGN.CENTER)
    tb(s, 2.0, y + 0.06, 10.7, 0.5, [{"runs": [
        {"text": txt, "size": 11.5, "color": INK}]}])
rect(s, 0.6, 5.45, 12.15, 1.5, NAVY, rounded=True)
tb(s, 0.6, 5.75, 12.15, 0.6, [{"align": PP_ALIGN.CENTER, "runs": [
    {"text": "Q & A   —   Thank you for listening", "size": 22, "bold": True,
     "color": WHITE}]}], align=PP_ALIGN.CENTER)
tb(s, 0.6, 6.35, 12.15, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
    {"text": "CausalStock  ·  CS173 Data Mining Final  ·  Team 2",
     "size": 12, "color": RGBColor(0x9D, 0xB0, 0xC4)}]}], align=PP_ALIGN.CENTER)

out = HERE / "CausalStock_CS173_Final.pptx"
prs.save(out)
print("saved", out, "—", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
