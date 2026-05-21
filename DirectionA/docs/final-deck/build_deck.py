"""Build the CausalStock CS173 final-presentation deck (16:9), EN + ZH.

Content follows the final report (docs/final-report/report.tex): three-stage
framework, EDA-driven schema, tabular prediction, stratified-vs-chronological
result. No ODE, no 0.709 ensemble, no negative-result slide.

23 slides. A dedicated baseline slide + a two-slide comparison block; a
four-slide data-analysis (EDA) block; a seven-slide method block that gives
each of the three phases its own detailed treatment (Phase 1 x2, Phase 2 x2,
Phase 3 x3). Seven report-aligned figures.

  python docs/final-deck/build_deck.py     # writes _EN.pptx and _ZH.pptx
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
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x2F, 0x9E, 0x74)
RED = RGBColor(0xC2, 0x49, 0x2F)
PALE = RGBColor(0xC9, 0xD6, 0xE3)

STATE = {"prs": None, "page": 0, "font": "Calibri"}


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
            f.name = r.get("font", STATE["font"])
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


def base(kicker, title, footer):
    STATE["page"] += 1
    s = STATE["prs"].slides.add_slide(STATE["prs"].slide_layouts[6])
    rect(s, 0, 0, 13.333, 0.98, NAVY)
    rect(s, 0, 0.98, 13.333, 0.055, ORANGE)
    tb(s, 0.55, 0.10, 12, 0.3,
       [{"runs": [{"text": kicker, "size": 12, "bold": True, "color": ORANGE}]}])
    tb(s, 0.55, 0.33, 12.2, 0.62,
       [{"runs": [{"text": title, "size": 21, "bold": True, "color": WHITE}]}])
    tb(s, 0.55, 7.10, 9, 0.3,
       [{"runs": [{"text": footer, "size": 9, "color": GRAY}]}])
    tb(s, 12.1, 7.10, 0.8, 0.3,
       [{"runs": [{"text": str(STATE["page"]), "size": 9, "color": GRAY}]}],
       align=PP_ALIGN.RIGHT)
    return s


def bullets(slide, x, y, w, h, items, size=14, gap=6):
    paras = []
    for it in items:
        lvl, txt, color = 0, it, INK
        if isinstance(it, tuple):
            txt, lvl = it[0], (it[1] if len(it) > 1 else 0)
            color = it[2] if len(it) > 2 else INK
        mark = "" if lvl else "▪  "
        ind = "      " if lvl else ""
        paras.append({"sa": gap, "lh": 1.13, "runs": [
            {"text": ind + mark, "size": size,
             "color": ORANGE if not lvl else GRAY, "bold": True},
            {"text": txt, "size": size if not lvl else size - 1.5, "color": color}]})
    return tb(slide, x, y, w, h, paras)


def table(slide, x, y, w, data, col_w, fs=11, row_h=0.42):
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
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.05)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if ri == 0 else (
                LIGHT if ri % 2 else WHITE)
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
            run = para.add_run()
            run.text = str(val)
            run.font.size = Pt(fs)
            run.font.bold = (ri == 0) or (ci == 0)
            run.font.color.rgb = WHITE if ri == 0 else INK
            run.font.name = STATE["font"]
    return gt


def stat(slide, x, y, w, big, lb, fc=NAVY, tc=ORANGE):
    rect(slide, x, y, w, 1.15, fc, rounded=True)
    tb(slide, x, y + 0.13, w, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": big, "size": 17, "bold": True, "color": tc}]}],
       align=PP_ALIGN.CENTER)
    tb(slide, x, y + 0.62, w, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
        {"text": lb, "size": 9.5, "color": WHITE}]}], align=PP_ALIGN.CENTER)


def panel(slide, x, y, w, h, title, fill=LIGHT):
    """A light card with an orange-kicker title; returns the body y."""
    rect(slide, x, y, w, h, fill, rounded=True)
    tb(slide, x + 0.25, y + 0.14, w - 0.5, 0.4, [{"runs": [
        {"text": title, "size": 12.5, "bold": True, "color": ORANGE}]}])
    return y + 0.58


def build(lang):
    EN = lang == "en"

    def t(en, zh):
        return en if EN else zh

    STATE["prs"] = Presentation()
    STATE["prs"].slide_width = Inches(13.333)
    STATE["prs"].slide_height = Inches(7.5)
    STATE["page"] = 0
    STATE["font"] = "Calibri" if EN else "Microsoft YaHei"
    prs = STATE["prs"]
    BLANK = prs.slide_layouts[6]
    foot = t("CausalStock  ·  CS173 Data Mining  ·  Team 2",
             "CausalStock  ·  CS173 数据挖掘  ·  第二组")

    # ---------------------------------------------------- S1 TITLE
    s = prs.slides.add_slide(BLANK)
    STATE["page"] += 1
    rect(s, 0, 0, 13.333, 7.5, NAVY)
    rect(s, 0, 3.04, 13.333, 0.06, ORANGE)
    tb(s, 0.9, 0.95, 12, 0.4, [{"runs": [{"text": t(
        "CS173  ·  DATA MINING  ·  FINAL PROJECT",
        "CS173  ·  数据挖掘  ·  期末项目"), "size": 13, "bold": True,
        "color": ORANGE}]}])
    tb(s, 0.86, 1.35, 12, 1.4, [{"runs": [
        {"text": "CausalStock", "size": 64, "bold": True, "color": WHITE}]}])
    tb(s, 0.9, 2.42, 12, 0.6, [{"runs": [{"text": t(
        "Event-Structured Temporal Causal Modeling for News-Driven Stock "
        "Prediction", "面向新闻驱动股价预测的事件结构化时序因果建模"),
        "size": 19, "color": PALE}]}])
    cards = [(t("Data-driven", "数据驱动"),
              t("3 EDA findings  →  3 new event attributes",
                "3 个 EDA 发现 → 3 个新事件属性")),
             (t("Structured", "结构化"),
              t("20-class events, not one sentiment score",
                "20 类结构化事件,而非单一情感分")),
             (t("Honest", "诚实"),
              t("stratified + chronological dual reporting",
                "分层 + 时间 双划分报告"))]
    for i, (hd, bd) in enumerate(cards):
        cx = 0.9 + i * 3.95
        rect(s, cx, 3.95, 3.7, 1.25, RGBColor(0x27, 0x4A, 0x73), rounded=True)
        tb(s, cx + 0.25, 4.1, 3.3, 0.4, [{"runs": [
            {"text": hd, "size": 15, "bold": True, "color": ORANGE}]}])
        tb(s, cx + 0.25, 4.5, 3.3, 0.7, [{"lh": 1.12, "runs": [
            {"text": bd, "size": 11.5, "color": WHITE}]}])
    tb(s, 0.9, 6.4, 12, 0.4, [{"runs": [{"text": t(
        "Team 2     ·     CS173 Final Project     ·     May 2026",
        "第二组     ·     CS173 期末项目     ·     2026 年 5 月"),
        "size": 13, "color": RGBColor(0x9D, 0xB0, 0xC4)}]}])

    # ---------------------------------------------------- S2 AGENDA
    s = base(t("AGENDA", "汇报目录"), t("Roadmap", "目录"), foot)
    ag = [("01", t("Problem & Baseline", "问题与基线"),
           t("Prior-method limits, the CausalStock baseline, our innovations",
             "现有方法的局限、CausalStock 基线、我们的创新")),
          ("02", t("Data Analysis (EDA)", "数据分析 (EDA)"),
           t("A four-part exploratory analysis that drives the event schema",
             "四部分的探索性数据分析,驱动事件 schema 设计")),
          ("03", t("Method — the Three Phases in Depth",
                   "方法 —— 三个阶段逐一详解"),
           t("Phase 1 extraction · Phase 2 causal discovery · Phase 3 "
             "prediction — each covered in detail",
             "Phase 1 抽取 · Phase 2 因果发现 · Phase 3 预测 —— 每个阶段都详细展开")),
          ("04", t("Experiments", "实验"),
           t("Stratified vs chronological results, and an ablation",
             "分层 vs 时间 划分结果,以及消融实验")),
          ("05", t("Comparison & Conclusion", "对比与结论"),
           t("A multi-axis comparison with the baseline, and future work",
             "与基线的多维对比,以及未来工作"))]
    for i, (no, hd, bd) in enumerate(ag):
        y = 1.4 + i * 1.06
        tb(s, 0.7, y, 1.0, 0.7, [{"runs": [
            {"text": no, "size": 26, "bold": True,
             "color": RGBColor(0xD9, 0xE2, 0xEC)}]}])
        rect(s, 1.8, y + 0.05, 0.06, 0.62, ORANGE)
        tb(s, 2.1, y, 10.6, 0.45, [{"runs": [
            {"text": hd, "size": 18, "bold": True, "color": NAVY}]}])
        tb(s, 2.1, y + 0.44, 10.7, 0.45, [{"lh": 1.1, "runs": [
            {"text": bd, "size": 12, "color": GRAY}]}])

    # ---------------------------------------------------- S3 PROBLEM
    s = base(t("01  ·  PROBLEM", "01  ·  问题"),
             t("What Prior Methods Get Wrong", "现有方法的三大问题"), foot)
    tb(s, 0.6, 1.35, 12, 0.4, [{"runs": [{"text": t(
        "Most news-driven models compress each article into one sentiment "
        "score. Three things break:",
        "多数新闻驱动模型把每篇文章压成一个情感分数,由此带来三个问题:"),
        "size": 13, "color": INK}]}])
    probs = [(t("Information Loss", "信息损失"),
              t("A single sentiment score discards the event's type, "
                "magnitude, and affected entity.",
                "单一情感分丢掉了事件的类型、幅度与影响对象。"),
              t("\"Apple launches iPhone, outlook +20%\" → sentiment +0.8",
                "「苹果发布 iPhone,预期上调 20%」→ 情感分 +0.8")),
             (t("Lack of Causality", "缺乏因果"),
              t("Models capture surface correlation, not the logic between "
                "events, and cannot explain a prediction.",
                "模型只抓表面相关,不理解事件间逻辑,也无法解释预测。"),
              t("Cannot tell a rate hike acting directly vs. via earnings.",
                "无法区分加息是直接作用还是经由盈利预期间接作用。")),
             (t("Ignoring Temporal Dynamics", "忽视时间动态"),
              t("A news impact is treated as instantaneous — missing lag, "
                "diffusion, and gradual effects.",
                "把新闻影响当作瞬时的,忽略滞后、扩散与持续发酵。"),
              t("A policy change may surface in prices only days later.",
                "政策变动可能数天后才在价格上显现。"))]
    for i, (hd, bd, eg) in enumerate(probs):
        y = 1.95 + i * 1.62
        rect(s, 0.6, y, 12.15, 1.42, LIGHT, rounded=True)
        rect(s, 0.6, y, 0.14, 1.42, RED)
        tb(s, 0.95, y + 0.12, 4.0, 0.5, [{"runs": [
            {"text": f"{i+1}.  {hd}", "size": 15, "bold": True, "color": NAVY}]}])
        tb(s, 0.95, y + 0.54, 7.8, 0.85, [{"lh": 1.13, "runs": [
            {"text": bd, "size": 11.5, "color": INK}]}])
        tb(s, 8.95, y + 0.2, 3.6, 1.05, [{"lh": 1.18, "runs": [
            {"text": eg, "size": 9.5, "italic": True, "color": GRAY}]}])

    # ---------------------------------------------------- S4 BASELINE
    s = base(t("01  ·  BASELINE", "01  ·  基线"),
             t("Baseline — CausalStock (NeurIPS 2024)",
               "基线 —— CausalStock (NeurIPS 2024)"), foot)
    tb(s, 0.6, 1.4, 12, 0.4, [{"runs": [{"text": t(
        "What the baseline does", "基线做了什么"),
        "size": 14, "bold": True, "color": ORANGE}]}])
    for i, (hd, bd) in enumerate([
            (t("Denoised news encoder", "去噪新闻编码器"),
             t("An LLM compresses each article into one dense embedding vector.",
               "用 LLM 把每篇文章压成一个稠密嵌入向量。")),
            (t("Stock-level causal graph", "个股级因果图"),
             t("Lag-dependent causality is learned between individual stocks.",
               "在个股之间学习带滞后的因果关系。"))]):
        cx = 0.6 + i * 6.15
        rect(s, cx, 1.82, 5.85, 1.15, LIGHT, rounded=True)
        rect(s, cx, 1.82, 0.12, 1.15, ORANGE)
        tb(s, cx + 0.25, 1.94, 5.45, 0.4, [{"runs": [
            {"text": hd, "size": 13, "bold": True, "color": NAVY}]}])
        tb(s, cx + 0.25, 2.32, 5.45, 0.6, [{"lh": 1.12, "runs": [
            {"text": bd, "size": 10.5, "color": INK}]}])
    tb(s, 0.6, 3.2, 12, 0.4, [{"runs": [{"text": t(
        "Two blind spots — and our response", "两个盲点 —— 以及我们的对策"),
        "size": 14, "bold": True, "color": ORANGE}]}])
    table(s, 0.6, 3.62, 12.15, [
        [t("Baseline blind spot", "基线的盲点"),
         t("CausalStock (ours) response", "我们的对策")],
        [t("One vector per article hides event type, magnitude, entity",
           "一篇一个向量,藏掉了事件类型、幅度、影响对象"),
         t("A structured event: (S,A,O,M) + impact profile",
           "结构化事件:(主体,行为,对象,幅度) + 影响画像")],
        [t("A stock-level graph cannot say what kind of event drove a link",
           "个股级的图说不出是什么事件驱动了这条边"),
         t("A causal graph over 20 event types, transferable across firms",
           "20 个事件类型上的因果图,可跨公司迁移")]],
        [6.05, 6.1], fs=11.5, row_h=0.62)
    rect(s, 0.6, 5.75, 12.15, 0.95, NAVY, rounded=True)
    tb(s, 0.95, 5.93, 11.5, 0.6, [{"lh": 1.12, "runs": [
        {"text": t("Takeaway:  ", "结论:  "), "size": 12.5, "bold": True,
         "color": ORANGE},
        {"text": t("the baseline is strong but structure-blind — we restore "
                   "event structure and move causality to the event-type level.",
                   "基线很强但对结构盲视 —— 我们恢复事件结构,并把因果移到事件类型级。"),
         "size": 12.5, "color": WHITE}]}])

    # ---------------------------------------------------- S5 INNOVATION
    s = base(t("01  ·  INNOVATION", "01  ·  创新"),
             t("What We Change — Three Innovations",
               "我们改变了什么 —— 三个创新点"), foot)
    tb(s, 0.6, 1.35, 12, 0.4, [{"runs": [{"text": t(
        "Each prior-method problem maps to one design change:",
        "现有方法的每个问题,精确对应一项设计改变:"),
        "size": 13, "color": INK}]}])
    table(s, 0.6, 1.85, 12.15, [
        [t("Prior-method problem", "现有方法的问题"),
         t("CausalStock innovation", "CausalStock 的创新")],
        [t("Information loss (sentiment scalar)", "信息损失(情感标量)"),
         t("Structured event: (S, A, O, magnitude) + impact profile",
           "结构化事件:(主体,行为,对象,幅度) + 影响画像")],
        [t("Lack of causality", "缺乏因果"),
         t("Lag-aware causal discovery over 20 event types",
           "在 20 个事件类型上做滞后感知因果发现")],
        [t("Ignoring temporal dynamics", "忽视时间动态"),
         t("A learned lag matrix T_lag and lag-gated attention",
           "学习滞后矩阵 T_lag 与滞后门控注意力")]],
        [5.5, 6.65], fs=12.5, row_h=0.72)
    rect(s, 0.6, 5.05, 12.15, 1.6, NAVY, rounded=True)
    tb(s, 0.95, 5.22, 11.6, 0.45, [{"runs": [{"text": t(
        "Two principles cut across all three:", "两条原则贯穿这三点:"),
        "size": 13, "bold": True, "color": ORANGE}]}])
    tb(s, 0.95, 5.62, 11.6, 0.95, [{"lh": 1.2, "runs": [{"text": t(
        "Data-driven — the event schema is earned from a measured EDA, not "
        "assumed.   Honest — every result is reported under both a stratified "
        "and a chronological split.",
        "数据驱动 —— 事件 schema 由实测 EDA 得来,而非预设。  诚实 —— 每个结果"
        "都同时在分层划分与时间划分下报告。"),
        "size": 12.5, "color": WHITE}]}])

    # ---------------------------------------------------- S6 PIPELINE
    s = base(t("01  ·  FRAMEWORK", "01  ·  框架"),
             t("End-to-End Pipeline", "端到端技术流程"), foot)
    pic(s, "fig_architecture.png", 1.45, 5.5, 12.5)
    tb(s, 0.6, 6.95, 12, 0.35, [{"align": PP_ALIGN.CENTER, "runs": [{"text": t(
        "Three stages: extract structured events, learn lag-aware event-type "
        "structure, predict with a transparent tabular model.",
        "三阶段:抽取结构化事件 → 学习滞后感知的事件类型结构 → 用透明表格模型预测。"),
        "size": 10.5, "italic": True, "color": GRAY}]}], align=PP_ALIGN.CENTER)

    # ---------------------------------------------------- S7 EDA-1
    s = base(t("02  ·  DATA ANALYSIS  (1/4)", "02  ·  数据分析  (1/4)"),
             t("Dataset Snapshot & Field Completeness",
               "数据集概览与字段完整度"), foot)
    for i, (big, lb) in enumerate([
            ("10,901", t("structured events", "结构化事件")),
            ("9,566", t("ticker-aligned examples", "个股对齐样本")),
            ("22", t("stocks", "只股票")),
            ("2010–23", t("time span", "时间跨度"))]):
        stat(s, 0.6 + i * 1.62, 1.5, 1.5, big, lb)
    pic(s, "fig_eda_missing.png", 2.95, 3.5, 6.0, x=0.6)
    rect(s, 7.5, 1.5, 5.3, 5.05, LIGHT, rounded=True)
    tb(s, 7.75, 1.66, 4.9, 0.4, [{"runs": [{"text": t(
        "OBSERVATIONS", "观察"), "size": 13, "bold": True, "color": ORANGE}]}])
    bullets(s, 7.75, 2.12, 4.9, 4.3, [
        t("URL present 99.98%, Stock_symbol 67%, Author 32%, Publisher 21%.",
          "URL 完整 99.98%,Stock_symbol 67%,Author 32%,Publisher 21%。"),
        (t("→ publisher / author too sparse to supervise on; credibility "
           "instead comes from the URL domain.",
           "→ publisher / author 太稀疏无法监督;credibility 改由 URL 域名导出。"),
         1),
        t("Duplicate-headline rows: 36,248 (~29%).",
          "重复标题行:36,248 条(约 29%)。"),
        (t("→ the same event reported many times; motivates a novelty "
           "attribute.",
           "→ 同一事件被反复报道;由此引出 novelty 属性。"), 1),
        t("Article length: median 3,724 / p90 6,949 / p99 29,925 chars.",
          "文章长度:中位 3,724 / p90 6,949 / p99 29,925 字符。")], size=11.5)

    # ---------------------------------------------------- S8 EDA-2
    s = base(t("02  ·  DATA ANALYSIS  (2/4)", "02  ·  数据分析  (2/4)"),
             t("Event-Clue Density — Why Event Extraction",
               "事件线索密度 —— 为何要做事件抽取"), foot)
    pic(s, "fig_eda_clues.png", 1.6, 4.3, 7.4, x=0.55)
    rect(s, 0.55, 5.7, 12.25, 1.25, NAVY, rounded=True)
    tb(s, 0.9, 5.85, 11.6, 0.95, [{"lh": 1.18, "runs": [{"text": t(
        "88% of articles carry explicit price-movement language and 77% a "
        "numeric comparison — the corpus is not diffuse opinion but a stream "
        "of discrete, typable events. This is the empirical justification for "
        "structured event extraction over sentiment scoring.",
        "88% 的文章带明确的价格变动语言、77% 带数值比较 —— 语料不是弥散的观点,"
        "而是一串离散、可归类的事件。这就是「做结构化事件抽取而非打情感分」的"
        "实证依据。"), "size": 11.5, "color": WHITE}]}])

    # ---------------------------------------------------- S9 EDA-3
    s = base(t("02  ·  DATA ANALYSIS  (3/4)", "02  ·  数据分析  (3/4)"),
             t("Data Findings Drive the Schema", "数据发现驱动 schema 设计"), foot)
    pic(s, "fig_datadriven_map.png", 2.7, 11.6, 3.6)
    tb(s, 0.6, 6.5, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [{"text": t(
        "Three measured properties — 29% duplicates, 68–79% missing "
        "provenance, 89% multi-scope — each motivate one event attribute.",
        "三个实测特性 —— 29% 重复、68–79% 来源缺失、89% 多范围 —— 各自推导出"
        "一个事件属性。"), "size": 11, "italic": True, "color": GRAY}]}],
       align=PP_ALIGN.CENTER)

    # ---------------------------------------------------- S10 EDA-4
    s = base(t("02  ·  DATA ANALYSIS  (4/4)", "02  ·  数据分析  (4/4)"),
             t("Event Stream — Distribution & Attribute Coverage",
               "事件流 —— 分布与属性覆盖率"), foot)
    pic(s, "fig_event_dist.png", 1.5, 3.6, 6.3, x=0.55)
    pic(s, "fig_coverage.png", 1.65, 3.45, 6.1, x=7.0)
    rect(s, 0.55, 5.45, 12.25, 1.5, NAVY, rounded=True)
    tb(s, 0.9, 5.6, 11.6, 1.2, [{"lh": 1.16, "runs": [{"text": t(
        "Event types are long-tailed — the top three are 55% of all events, "
        "so training must be class-aware. Polarity / scope / novelty / "
        "credibility reach ~85% coverage and are used as standard attributes; "
        "surprise is sparse (6.6%), treated as a high-value indicator. A "
        "50-sample audit: 84% type, 78% action, 91% polarity agreement.",
        "事件类型长尾 —— 前三类占全部事件的 55%,所以训练必须类别感知。极性 / "
        "范围 / 新颖度 / 可信度覆盖约 85%,作为标准属性;意外度稀疏(6.6%),"
        "作为高价值指示器。50 样本抽审:类型一致 84%、动作 78%、极性 91%。"),
        "size": 11.5, "color": WHITE}]}])

    # ---------------------------------------------------- S11 PHASE 1a
    s = base(t("03  ·  METHOD — PHASE 1  (1/2)", "03  ·  方法 — PHASE 1  (1/2)"),
             t("Phase 1 — The Structured Event Schema",
               "Phase 1 —— 结构化事件 schema"), foot)
    tb(s, 0.6, 1.32, 12.2, 0.4, [{"runs": [{"text": t(
        "Phase 1 turns each free-text article into ONE structured event "
        "record — a core quadruple plus a five-attribute impact profile.",
        "Phase 1 把每篇自由文本文章变成一条结构化事件记录 —— 一个核心四元组,"
        "外加一个五属性的影响画像。"), "size": 12.5, "color": INK}]}])
    by = panel(s, 0.6, 1.78, 6.05, 2.5,
               t("EVENT CORE  —  (type, S, A, O, M)", "事件核心 —— (类型, S, A, O, M)"))
    bullets(s, 0.85, by, 5.6, 1.9, [
        t("type — one of a 20-class event ontology", "type —— 20 类事件本体之一"),
        t("subject (S) — the entity that acts", "subject (S) —— 发起动作的主体"),
        t("action (A) — the relation or verb", "action (A) —— 关系或行为动词"),
        t("object (O) — the entity affected", "object (O) —— 被影响的对象"),
        t("magnitude (M) — signed numeric size of the move",
          "magnitude (M) —— 带符号的数值幅度")], size=10.8, gap=4)
    by = panel(s, 6.8, 1.78, 5.95, 2.5,
               t("20-CLASS ONTOLOGY  —  FOUR FAMILIES", "20 类本体 —— 四大族"))
    bullets(s, 7.05, by, 5.5, 1.9, [
        t("Macro — rate decisions, inflation, GDP, jobs",
          "宏观 —— 利率决议、通胀、GDP、就业"),
        t("Corporate — earnings, M&A, guidance, products",
          "公司 —— 财报、并购、业绩指引、产品"),
        t("Knowledge — analyst ratings, research, forecasts",
          "知识 —— 分析师评级、研究、预测"),
        t("Geopolitics — regulation, sanctions, conflict",
          "地缘 —— 监管、制裁、冲突")], size=10.8, gap=4)
    rect(s, 0.6, 4.45, 12.15, 2.35, NAVY, rounded=True)
    tb(s, 0.85, 4.58, 11.6, 0.4, [{"runs": [{"text": t(
        "IMPACT PROFILE  —  5 ATTRIBUTES ATTACHED TO EVERY EVENT",
        "影响画像 —— 附在每个事件上的 5 个属性"),
        "size": 12.5, "bold": True, "color": ORANGE}]}])
    profile = [
        (t("polarity", "极性"), t("directional sign", "影响的方向"), NAVY),
        (t("surprise", "意外度"), t("vs. expectation", "相对预期的偏离"), NAVY),
        (t("scope", "范围"), t("breadth of entities", "影响实体的广度"), ORANGE),
        (t("novelty", "新颖度"), t("first report vs repeat", "首报 vs 重复"), ORANGE),
        (t("credibility", "可信度"), t("source reliability", "来源可靠度"), ORANGE)]
    for i, (nm, ds, cl) in enumerate(profile):
        cx = 0.9 + i * 2.4
        rect(s, cx, 5.0, 2.2, 1.0, WHITE, rounded=True)
        tb(s, cx, 5.12, 2.2, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
            {"text": nm, "size": 11.5, "bold": True, "color": cl}]}],
           align=PP_ALIGN.CENTER)
        tb(s, cx + 0.05, 5.5, 2.1, 0.45, [{"align": PP_ALIGN.CENTER, "lh": 1.05,
            "runs": [{"text": ds, "size": 8.4, "color": GRAY}]}],
           align=PP_ALIGN.CENTER)
    tb(s, 0.9, 6.18, 11.6, 0.5, [{"lh": 1.12, "runs": [
        {"text": t("Where used:  ", "用在哪里:  "),
         "size": 10, "bold": True, "color": ORANGE},
        {"text": t("scope · novelty · credibility are EDA-driven; the profile "
                   "becomes Phase-3 event features and weights events in the "
                   "Phase-2 causal aggregation.",
                   "范围 · 新颖度 · 可信度 由 EDA 驱动;影响画像进入 Phase 3 成为事件"
                   "特征,并在 Phase 2 的因果聚合中给事件加权。"),
         "size": 10, "color": PALE}]}])

    # ---------------------------------------------------- S12 PHASE 1b
    s = base(t("03  ·  METHOD — PHASE 1  (2/2)", "03  ·  方法 — PHASE 1  (2/2)"),
             t("Phase 1 — Extraction Model & Weak Supervision",
               "Phase 1 —— 抽取模型与弱监督"), foot)
    tb(s, 0.6, 1.32, 12.2, 0.4, [{"runs": [{"text": t(
        "A FinBERT encoder with a multi-head decoder, trained on labels built "
        "by a four-step weak-supervision pipeline.",
        "FinBERT 编码器接多头解码器,标签由一条四步弱监督流水线生成。"),
        "size": 12.5, "color": INK}]}])
    by = panel(s, 0.6, 1.78, 6.05, 3.55,
               t("MODEL  —  FinBERT + MULTI-HEAD DECODER",
                 "模型 —— FinBERT + 多头解码器"))
    bullets(s, 0.85, by, 5.6, 2.9, [
        t("Encoder — ProsusAI/finbert, pretrained on financial text",
          "编码器 —— ProsusAI/finbert,金融文本预训练"),
        t("Head 1 — event-type classification (20-way softmax)",
          "头 1 —— 事件类型分类(20 类 softmax)"),
        t("Head 2 — argument spans (subject / object token spans)",
          "头 2 —— 论元跨度(主体 / 对象 的 token 跨度)"),
        t("Head 3 — magnitude regression (signed scalar)",
          "头 3 —— 幅度回归(带符号标量)"),
        t("Heads share the encoder and are trained jointly",
          "三个头共享编码器,联合训练")], size=10.8, gap=5)
    by = panel(s, 6.8, 1.78, 5.95, 3.55,
               t("WEAK-SUPERVISION PIPELINE", "弱监督流水线"))
    steps = [
        t("1 — LLM silver label  (no gold labels at scale)",
          "1 — LLM 银标(大规模无金标)"),
        t("2 — rule correction  (finance keyword / regex)",
          "2 — 规则校正(金融关键词 / 正则)"),
        t("3 — market grounding  (check M vs realized return)",
          "3 — 市场校正(用真实收益核对幅度 M)"),
        t("4 — hallucination filter  →  accept event",
          "4 — 幻觉过滤  →  接受事件")]
    for i, st in enumerate(steps):
        sy = by + i * 0.66
        rect(s, 7.05, sy, 5.45, 0.54, WHITE, rounded=True, line=PALE)
        tb(s, 7.25, sy + 0.10, 5.1, 0.4, [{"runs": [
            {"text": st, "size": 9.8, "color": INK}]}])
    for i, (big, lb) in enumerate([
            ("10,901", t("structured events", "结构化事件")),
            ("20", t("event types", "事件类型")),
            ("84.8%", t("avg attribute coverage", "平均属性覆盖率")),
            ("84 / 78 / 91%", t("audit: type / action / polarity",
                                "抽审:类型 / 动作 / 极性"))]):
        stat(s, 0.6 + i * 3.07, 5.55, 2.9, big, lb)

    # ---------------------------------------------------- S13 PHASE 2a
    s = base(t("03  ·  METHOD — PHASE 2  (1/2)", "03  ·  方法 — PHASE 2  (1/2)"),
             t("Phase 2 — Lag-Aware Causal Discovery (STACD)",
               "Phase 2 —— 滞后感知因果发现 (STACD)"), foot)
    tb(s, 0.6, 1.32, 12.2, 0.4, [{"runs": [{"text": t(
        "Phase 2 learns the temporal causal structure between the 20 event "
        "types — what drives what, and after how long.",
        "Phase 2 学习 20 个事件类型之间的时序因果结构 —— 谁驱动谁、滞后多久。"),
        "size": 12.5, "color": INK}]}])
    by = panel(s, 0.6, 1.78, 5.4, 4.6,
               t("GOAL  —  TWO LEARNED MATRICES", "目标 —— 两个学习的矩阵"))
    for i, (nm, ds) in enumerate([
            ("A  ∈  (0,1)²⁰ˣ²⁰",
             t("directed causal strength — A[i,j] = how strongly type i "
               "drives type j",
               "有向因果强度 —— A[i,j] = 类型 i 驱动类型 j 的强度")),
            ("T_lag  ∈  ℝ²⁰ˣ²⁰",
             t("expected lag in days between cause and effect",
               "因与果之间的预期滞后(天)"))]):
        ry = by + i * 1.45
        rect(s, 0.85, ry, 4.9, 1.25, WHITE, rounded=True, line=PALE)
        tb(s, 1.05, ry + 0.12, 4.5, 0.4, [{"runs": [
            {"text": nm, "size": 13, "bold": True, "color": NAVY,
             "font": "Consolas"}]}])
        tb(s, 1.05, ry + 0.5, 4.5, 0.65, [{"lh": 1.13, "runs": [
            {"text": ds, "size": 9.8, "color": GRAY}]}])
    tb(s, 0.85, by + 3.0, 4.9, 0.7, [{"lh": 1.15, "runs": [{"text": t(
        "Both matrices are learned end-to-end from the event stream.",
        "两个矩阵都从事件流端到端学习得到。"),
        "size": 9.6, "italic": True, "color": GRAY}]}])
    rect(s, 6.25, 1.78, 6.5, 4.6, NAVY, rounded=True)
    tb(s, 6.55, 1.92, 5.9, 0.4, [{"runs": [{"text": t(
        "MECHANISM  —  STACD COMPONENTS", "机制 —— STACD 的组件"),
        "size": 12.5, "bold": True, "color": ORANGE}]}])
    comps = [
        (t("Sparse temporal attention", "稀疏时序注意力"),
         t("attention over the event sequence, sparsified to keep real links",
           "在事件序列上做注意力,稀疏化以保留真实连边")),
        (t("Time-direction mask", "时间方向掩码"),
         t("only the past attends to the future — no leakage backward",
           "只允许过去影响未来 —— 不向后泄漏")),
        (t("Lag-aware Gaussian gate", "滞后感知高斯门"),
         t("peaks when the observed gap matches the learned T_lag",
           "当观测到的时间间隔接近学到的 T_lag 时取峰值")),
        (t("Causal-strength gate", "因果强度门"),
         t("modulates each attention weight by the learned strength A",
           "用学到的强度 A 调制每个注意力权重")),
        (t("NOTEARS-style regularizer", "NOTEARS 式正则项"),
         t("an acyclicity penalty that keeps the graph a valid DAG",
           "无环惩罚项,使图保持为合法的 DAG"))]
    for i, (hd, bd) in enumerate(comps):
        cy = 2.36 + i * 0.79
        tb(s, 6.55, cy, 5.9, 0.32, [{"runs": [
            {"text": "▪  " + hd, "size": 11, "bold": True, "color": WHITE}]}])
        tb(s, 6.85, cy + 0.3, 5.6, 0.42, [{"lh": 1.1, "runs": [
            {"text": bd, "size": 9.2, "color": PALE}]}])

    # ---------------------------------------------------- S14 PHASE 2b
    s = base(t("03  ·  METHOD — PHASE 2  (2/2)", "03  ·  方法 — PHASE 2  (2/2)"),
             t("Phase 2 — Attention Modulation & Interpretability",
               "Phase 2 —— 注意力调制与可解释性"), foot)
    tb(s, 0.6, 1.32, 12.2, 0.4, [{"runs": [{"text": t(
        "The three gates enter the attention score additively in log-space; "
        "the loss adds sparsity and an acyclicity penalty.",
        "三个门以对数空间相加的方式进入注意力打分;损失再加稀疏项与无环惩罚。"),
        "size": 12.5, "color": INK}]}])
    rect(s, 0.6, 1.78, 7.1, 3.45, NAVY, rounded=True)
    tb(s, 0.9, 1.92, 6.5, 0.4, [{"runs": [{"text": t(
        "ATTENTION MODULATION", "注意力调制"), "size": 12.5, "bold": True,
        "color": ORANGE}]}])
    for i, eq in enumerate([
            "g_ij = exp( -(|t_i-t_j| - T_lag[k_j,k_i])^2 / 2σ^2 )",
            "s_ij' = s_ij + log m_ij + log g_ij + log A[k_j,k_i]",
            "α_ij = softmax_j ( s_ij' )",
            "L = L_pred + λ1·||A||1 + λ_DAG·h(A)^2"]):
        tb(s, 0.95, 2.42 + i * 0.62, 6.6, 0.5, [{"runs": [
            {"text": eq, "size": 11, "color": WHITE, "font": "Consolas"}]}])
    tb(s, 0.95, 4.95, 6.6, 0.3, [{"runs": [{"text": t(
        "k_j = event type of token j", "k_j = token j 的事件类型"),
        "size": 8.6, "italic": True, "color": PALE}]}])
    by = panel(s, 7.85, 1.78, 4.9, 3.45, t("TERMS", "符号说明"))
    bullets(s, 8.05, by, 4.55, 2.7, [
        t("s_ij — raw attention score", "s_ij —— 原始注意力打分"),
        t("m_ij — time-direction mask", "m_ij —— 时间方向掩码"),
        t("g_ij — lag-aware Gaussian gate", "g_ij —— 滞后感知高斯门"),
        t("A — causal-strength matrix", "A —— 因果强度矩阵"),
        t("h(A) — DAG acyclicity penalty", "h(A) —— DAG 无环惩罚")],
        size=10.2, gap=6)
    rect(s, 0.6, 5.4, 12.15, 1.4, NAVY, rounded=True)
    tb(s, 0.95, 5.54, 11.5, 0.4, [{"runs": [{"text": t(
        "Why nodes are event types, not stocks", "为什么节点是事件类型而非个股"),
        "size": 12, "bold": True, "color": ORANGE}]}])
    tb(s, 0.95, 5.92, 11.5, 0.8, [{"lh": 1.16, "runs": [{"text": t(
        "A 20-node event-type graph stays the same across companies and "
        "markets, so it is designed to support interpretable, transferable "
        "event-chain analysis — a stock-level graph is bound to a fixed "
        "company universe.",
        "一张 20 节点的事件类型图在不同公司、不同市场之间保持不变,因此该图为"
        "可解释、可迁移的事件链分析而设计 —— 个股级的图则绑定在固定的股票池上。"),
        "size": 11, "color": WHITE}]}])

    # ---------------------------------------------------- S15 PHASE 3a
    s = base(t("03  ·  METHOD — PHASE 3  (1/3)", "03  ·  方法 — PHASE 3  (1/3)"),
             t("Phase 3 — Problem Setup & Dataset", "Phase 3 —— 问题设定与数据集"),
             foot)
    rect(s, 0.6, 1.45, 6.0, 3.05, LIGHT, rounded=True)
    tb(s, 0.85, 1.6, 5.6, 0.4, [{"runs": [{"text": t(
        "INPUTS  →  OUTPUT", "输入 → 输出"), "size": 13, "bold": True,
        "color": ORANGE}]}])
    bullets(s, 0.85, 2.05, 5.6, 2.4, [
        t("32 recent news events", "最近 32 个新闻事件"),
        t("30-day OHLCV price window", "30 天 OHLCV 价格窗口"),
        t("Target stock identity", "目标股票身份"),
        t("Output: next-day direction, threshold ±0.5%",
          "输出:次日方向,阈值 ±0.5%")], size=13)
    rect(s, 6.85, 1.45, 5.9, 3.05, LIGHT, rounded=True)
    tb(s, 7.1, 1.6, 5.5, 0.4, [{"runs": [{"text": t(
        "THREE-CLASS DISTRIBUTION", "三分类分布"), "size": 13, "bold": True,
        "color": ORANGE}]}])
    for i, (lb, pc, cl) in enumerate([("UP", "39.4%", GREEN),
                                      ("DOWN", "43.3%", RED),
                                      ("FLAT", "17.3%", GRAY)]):
        cx = 7.15 + i * 1.92
        rect(s, cx, 2.2, 1.7, 1.6, WHITE, rounded=True)
        tb(s, cx, 2.4, 1.7, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [
            {"text": pc, "size": 21, "bold": True, "color": cl}]}],
           align=PP_ALIGN.CENTER)
        tb(s, cx, 3.0, 1.7, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
            {"text": lb, "size": 13, "bold": True, "color": INK}]}],
           align=PP_ALIGN.CENTER)
    tb(s, 7.1, 3.95, 5.5, 0.4, [{"runs": [{"text": t(
        "FLAT is the minority class — macro-F1 is emphasized.",
        "FLAT 是少数类 —— 因此主看 macro-F1。"),
        "size": 10.5, "italic": True, "color": GRAY}]}])
    for i, (big, lb) in enumerate([
            ("9,566", t("ticker-aligned examples", "个股对齐样本")),
            ("22", t("stocks", "只股票")),
            ("2010–2023", t("time span", "时间跨度"))]):
        stat(s, 0.6 + i * 4.07, 4.8, 3.85, big, lb)

    # ---------------------------------------------------- S16 PHASE 3b
    s = base(t("03  ·  METHOD — PHASE 3  (2/3)", "03  ·  方法 — PHASE 3  (2/3)"),
             t("Phase 3 — Feature Engineering (132-d)",
               "Phase 3 —— 特征工程(132 维)"), foot)
    rect(s, 0.6, 1.4, 12.15, 0.92, NAVY, rounded=True)
    tb(s, 0.6, 1.58, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [{"text": t(
        "x = [ price ‖ event ‖ stock-ID ]   =   132-dimensional feature vector",
        "x = [ 价格 ‖ 事件 ‖ 股票身份 ]   =   132 维特征向量"),
        "size": 14, "bold": True, "color": WHITE}]}], align=PP_ALIGN.CENTER)
    fcards = [
        (t("PRICE  ·  28-d", "价格  ·  28 维"), [
            t("Multi-horizon returns — 1 / 5 / 10 / 20-day",
              "多周期收益率 —— 1 / 5 / 10 / 20 日"),
            t("Realized volatility & ranges", "已实现波动率与振幅"),
            t("Log-volume & volume trend", "对数成交量与量能趋势"),
            t("OHLC ratios & gaps", "OHLC 比率与跳空"),
            t("Short-term momentum", "短期动量")]),
        (t("EVENT  ·  82-d", "事件  ·  82 维"), [
            t("Per-type event counts (20-d)", "各类型事件计数(20 维)"),
            t("Signed magnitude sums per family", "各族带符号幅度和"),
            t("Absolute magnitude sums", "绝对幅度和"),
            t("Impact-profile means — polarity, surprise, "
              "scope, novelty, credibility",
              "影响画像均值 —— 极性、意外度、范围、新颖度、可信度"),
            t("Last-event type one-hot", "末事件类型 one-hot")]),
        (t("STOCK-ID  ·  22-d", "股票身份  ·  22 维"), [
            t("One-hot ticker identity", "股票 one-hot 身份"),
            t("22 stocks in the universe", "股票池共 22 只"),
            t("Lets the model learn ticker-specific volatility "
              "and reaction patterns",
              "让模型学到个股特有的波动与反应模式")])]
    for i, (hd, items) in enumerate(fcards):
        cx = 0.6 + i * 4.16
        rect(s, cx, 2.6, 3.83, 3.4, LIGHT, rounded=True)
        rect(s, cx, 2.6, 3.83, 0.5, NAVY)
        tb(s, cx, 2.68, 3.83, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
            {"text": hd, "size": 12, "bold": True, "color": WHITE}]}],
           align=PP_ALIGN.CENTER)
        bullets(s, cx + 0.22, 3.25, 3.5, 2.6, items, size=9.6, gap=6)
    tb(s, 0.6, 6.2, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [{"text": t(
        "Every feature is an aggregate over the 32-event / 30-day window — "
        "strictly past information, no look-ahead.",
        "每个特征都是 32 事件 / 30 天窗口上的聚合量 —— 严格只用过去信息,无未来泄漏。"),
        "size": 10.5, "italic": True, "color": GRAY}]}], align=PP_ALIGN.CENTER)

    # ---------------------------------------------------- S17 PHASE 3c
    s = base(t("03  ·  METHOD — PHASE 3  (3/3)", "03  ·  方法 — PHASE 3  (3/3)"),
             t("Phase 3 — Model: HistGradientBoosting",
               "Phase 3 —— 模型:HistGradientBoosting"), foot)
    tb(s, 0.6, 1.32, 12.2, 0.4, [{"runs": [{"text": t(
        "The classifier over the 132-d vector is HistGradientBoosting (HGB) — "
        "a histogram-based gradient-boosted tree ensemble.",
        "132 维向量上的分类器是 HistGradientBoosting(HGB)—— 一个基于直方图的"
        "梯度提升树集成。"), "size": 12.5, "color": INK}]}])
    by = panel(s, 0.6, 1.78, 6.05, 4.05,
               t("WHY HGB OVER A NEURAL NET", "为什么用 HGB 而非神经网络"))
    bullets(s, 0.85, by, 5.6, 3.3, [
        t("Heterogeneous features — counts, ratios, one-hots handled natively",
          "异构特征 —— 计数、比率、one-hot 都能原生处理"),
        t("Scale-invariant tree splits — minimal feature engineering",
          "树分裂对尺度不敏感 —— 特征工程量极小"),
        t("Strong, interpretable baseline — reads each source's contribution",
          "强且可解释的基线 —— 能读出各信息源的贡献"),
        t("Robust on a 9,566-example dataset — no large-data requirement",
          "在 9,566 样本规模上稳健 —— 不依赖大数据")], size=11, gap=11)
    by = panel(s, 6.8, 1.78, 5.95, 4.05,
               t("CONFIGURATION & TRAINING", "配置与训练"), fill=NAVY)
    bullets(s, 7.05, by, 5.5, 3.3, [
        (t("max_iter 150 · learning_rate 0.04 · L2 0.05", "max_iter 150 · "
           "learning_rate 0.04 · L2 0.05"), 0, WHITE),
        (t("Early stopping on a held-out validation loss",
           "在留出验证损失上早停"), 0, WHITE),
        (t("3-class softmax output — UP / DOWN / FLAT",
           "三类 softmax 输出 —— UP / DOWN / FLAT"), 0, WHITE),
        (t("macro-F1 as the headline metric (FLAT is the minority class)",
           "以 macro-F1 为主指标(FLAT 为少数类)"), 0, WHITE),
        (t("Evaluated under both stratified and chronological splits",
           "在分层划分与时间划分下分别评估"), 0, PALE)], size=11, gap=11)

    # ---------------------------------------------------- S18 KEY RESULT
    s = base(t("04  ·  EXPERIMENTS", "04  ·  实验"),
             t("Key Result — Stratified vs Chronological",
               "核心结果 —— 分层划分 vs 时间划分"), foot)
    pic(s, "fig_split.png", 1.5, 4.55, 6.0, x=0.6)
    rect(s, 7.0, 1.5, 5.8, 5.05, LIGHT, rounded=True)
    tb(s, 7.25, 1.66, 5.4, 0.4, [{"runs": [{"text": t(
        "TWO HONEST READINGS", "两个诚实的解读"), "size": 13, "bold": True,
        "color": ORANGE}]}])
    bullets(s, 7.25, 2.12, 5.35, 4.2, [
        t("Stratified random — macro-F1 0.693, accuracy 0.728. Well above the "
          "0.43 majority and 0.33 random baselines: the features carry signal.",
          "分层随机 —— macro-F1 0.693、准确率 0.728。明显高于 0.43 多数类与 "
          "0.33 随机基线:特征含有效信号。"),
        t("Chronological — macro-F1 0.337. Near random, consistent with "
          "semi-strong market efficiency: forward-time prediction is hard.",
          "时间顺序 —— macro-F1 0.337。接近随机,与半强式市场有效一致。"),
        (t("We report both — reporting only the stratified number would "
           "overstate real predictive power.",
           "我们两个都报 —— 只报分层那个数会高估真实预测力。"), 1, NAVY)],
        size=12)

    # ---------------------------------------------------- S19 ABLATION
    s = base(t("04  ·  EXPERIMENTS", "04  ·  实验"),
             t("Ablation — Feature-Group Contribution", "消融实验 —— 各信息源的贡献"),
             foot)
    tb(s, 0.6, 1.4, 12, 0.4, [{"runs": [{"text": t(
        "Stratified-random macro-F1 for the combined-feature models:",
        "组合特征模型在分层随机划分下的 macro-F1:"),
        "size": 13, "color": INK}]}])
    table(s, 1.7, 1.95, 9.9, [
        [t("Feature set", "特征集"), t("Dim.", "维度"), "Macro-F1"],
        [t("Price + events", "价格 + 事件"), "110", "0.684"],
        [t("Full:  price + events + stock ID", "完整:价格 + 事件 + 股票身份"),
         "132", "0.693"]],
        [6.4, 1.6, 1.9], fs=13, row_h=0.62)
    rect(s, 0.6, 4.0, 12.15, 2.3, LIGHT, rounded=True)
    tb(s, 0.95, 4.18, 11.6, 0.4, [{"runs": [{"text": t("Reading", "解读"),
        "size": 13, "bold": True, "color": ORANGE}]}])
    bullets(s, 0.95, 4.6, 11.6, 1.6, [
        t("Adding stock identity lifts macro-F1 from 0.684 to 0.693 — "
          "ticker-specific volatility and reaction patterns remain useful.",
          "加入股票身份把 macro-F1 从 0.684 提到 0.693 —— 个股特有的波动与反应"
          "模式仍有用。"),
        t("The combined representation is learnable under a stratified split — "
          "it is the configuration we report.",
          "组合表示在分层划分下可学习 —— 这是我们汇报的配置。")], size=12)

    # ---------------------------------------------------- S20 COMPARISON TABLE
    s = base(t("05  ·  COMPARISON", "05  ·  对比"),
             t("Comparison with the Baseline — Multi-Axis",
               "与基线的多维对比"), foot)
    table(s, 0.55, 1.5, 12.25, [
        [t("Axis", "维度"), t("CausalStock (NeurIPS 2024)",
                              "CausalStock(NeurIPS 2024)"), t("Ours", "我们")],
        [t("Causality level", "因果层级"),
         t("Stock-level graph", "个股级图"),
         t("Event-type graph (20×20)", "事件类型级图(20×20)")],
        [t("News representation", "新闻表示"),
         t("Dense denoised embedding", "稠密去噪嵌入"),
         t("Structured event + impact profile", "结构化事件 + 影响画像")],
        [t("Prediction task", "预测任务"),
         t("Binary up / down", "二分类 涨/跌"),
         t("3-class with a ±0.5% FLAT zone", "三分类,带 ±0.5% FLAT 区")],
        [t("Evaluation protocol", "评估协议"),
         t("Mostly random split", "多为随机划分"),
         t("Stratified + chronological", "分层 + 时间 双划分")],
        [t("Data scale", "数据规模"),
         t("Larger, multi-dataset", "更大,多数据集"),
         t("5% FNSPID subset, 22 stocks", "5% FNSPID 子集,22 股")]],
        [2.6, 4.6, 5.05], fs=11, row_h=0.62)
    rect(s, 0.55, 5.7, 12.25, 1.0, NAVY, rounded=True)
    tb(s, 0.9, 5.84, 11.6, 0.75, [{"lh": 1.16, "runs": [{"text": t(
        "Complementary, not competing — event-type causality transfers across "
        "companies and markets; stock-level causality is bound to a fixed "
        "company universe.",
        "互补而非竞争 —— 事件类型级因果可跨公司、跨市场迁移;个股级因果绑定"
        "在固定股票池。"), "size": 12, "color": WHITE}]}])

    # ---------------------------------------------------- S21 COMPARISON ANALYSIS
    s = base(t("05  ·  COMPARISON", "05  ·  对比"),
             t("Comparison — An Interpretable Reading of the Gap",
               "对比 —— 对差距的可解释分析"), foot)
    tb(s, 0.6, 1.35, 12, 0.4, [{"runs": [{"text": t(
        "Our setup is harder and stricter than the baseline's — the gap is "
        "explainable along four axes:",
        "我们的设定比基线更难、更严格 —— 差距可沿四个维度解释:"),
        "size": 12.5, "color": INK}]}])
    items = [
        (t("Task", "任务"),
         t("We predict 3 classes with a ±0.5% FLAT dead zone; the baseline "
           "predicts binary up/down. FLAT is the hard minority class.",
           "我们做带 ±0.5% FLAT 死区的三分类;基线是二分类涨/跌。FLAT 是最难的"
           "少数类。")),
        (t("Data", "数据"),
         t("A 5% FNSPID subset over 22 stocks — far smaller; cross-stock "
           "relational signal is limited at this scale.",
           "5% FNSPID 子集、22 只股票 —— 规模小得多;此规模下跨股票的关系信号"
           "有限。")),
        (t("Protocol", "协议"),
         t("Our directly comparable number is the chronological one; a random "
           "split mixes market regimes and inflates apparent performance.",
           "真正可比的是我们的时间划分数;随机划分混合市场体制,会高估表现。")),
        (t("Method", "方法"),
         t("The baseline couples news with a price-derived causal backbone "
           "end-to-end; our evaluated layer is a transparent tabular model "
           "over aggregated event statistics — interpretable but lossier.",
           "基线把新闻与价格导出的因果骨架端到端耦合;我们评测的是聚合事件统计"
           "上的透明表格模型 —— 可解释但有损。"))]
    for i, (hd, bd) in enumerate(items):
        y = 1.85 + i * 1.05
        rect(s, 0.6, y, 12.15, 0.92, LIGHT, rounded=True)
        rect(s, 0.6, y, 1.55, 0.92, NAVY)
        tb(s, 0.6, y + 0.27, 1.55, 0.4, [{"align": PP_ALIGN.CENTER, "runs": [
            {"text": hd, "size": 12.5, "bold": True, "color": ORANGE}]}],
           align=PP_ALIGN.CENTER)
        tb(s, 2.35, y + 0.10, 10.2, 0.78, [{"lh": 1.13, "runs": [
            {"text": bd, "size": 10.8, "color": INK}]}])
    tb(s, 0.6, 6.2, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [{"text": t(
        "We do not claim to beat the baseline — we contribute a transferable "
        "event-type formulation and a stricter, honest evaluation.",
        "我们不声称击败基线 —— 我们的贡献是可迁移的事件类型形式化,以及更严格、"
        "更诚实的评估。"), "size": 11, "italic": True, "color": GRAY}]}],
       align=PP_ALIGN.CENTER)

    # ---------------------------------------------------- S22 CONCLUSION
    s = base(t("05  ·  CONCLUSION", "05  ·  结论"),
             t("Conclusion & Future Work", "总结与未来工作"), foot)
    rect(s, 0.6, 1.5, 6.0, 4.7, LIGHT, rounded=True)
    rect(s, 0.6, 1.5, 6.0, 0.5, GREEN)
    tb(s, 0.8, 1.58, 5.6, 0.4, [{"runs": [{"text": t(
        "WHAT WE CONTRIBUTE", "我们的贡献"), "size": 12.5, "bold": True,
        "color": WHITE}]}])
    bullets(s, 0.8, 2.15, 5.6, 3.9, [
        t("A clearer event-structured problem formulation.",
          "更清晰的事件结构化问题形式化。"),
        t("An EDA-driven event schema — attributes earned from measured data.",
          "EDA 驱动的事件 schema —— 属性由实测数据得来。"),
        t("A mathematically specified lag-aware event-causal model.",
          "数学上明确定义的滞后感知事件因果模型。"),
        t("An honest analysis separating information content from "
          "forward-time predictability.",
          "把信息含量与前向可预测性分开的诚实分析。")], size=11.5, gap=9)
    rect(s, 6.75, 1.5, 6.0, 4.7, LIGHT, rounded=True)
    rect(s, 6.75, 1.5, 6.0, 0.5, BLUE)
    tb(s, 6.95, 1.58, 5.6, 0.4, [{"runs": [{"text": t(
        "FUTURE WORK", "未来工作"), "size": 12.5, "bold": True, "color": WHITE}]}])
    bullets(s, 6.95, 2.15, 5.6, 3.9, [
        t("Integrate A and T_lag directly as Phase-3 features.",
          "把 A 与 T_lag 直接作为 Phase-3 特征整合进去。"),
        t("Model cross-stock event propagation.", "建模跨股票的事件传播。"),
        t("Regime-aware temporal encoding against distribution shift.",
          "引入体制感知的时间编码以缓解分布漂移。"),
        t("Rolling walk-forward validation as the default protocol.",
          "以滚动前向验证作为默认协议。")], size=11.5, gap=9)
    tb(s, 0.6, 6.35, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [{"text": t(
        "We do not claim solved stock prediction — we claim a clean "
        "formulation and an honest study of where structured news helps.",
        "我们不声称解决了股价预测 —— 我们给出的是清晰的形式化,以及结构化新闻"
        "在哪里有用的诚实研究。"),
        "size": 11, "italic": True, "color": GRAY}]}], align=PP_ALIGN.CENTER)

    # ---------------------------------------------------- S23 Q&A
    s = base(t("THANK YOU", "致谢"), "Q & A", foot)
    rect(s, 0.6, 2.4, 12.15, 2.6, NAVY, rounded=True)
    tb(s, 0.6, 3.0, 12.15, 0.7, [{"align": PP_ALIGN.CENTER, "runs": [{"text": t(
        "Q & A   —   Thank you for listening", "Q & A   —   感谢聆听"),
        "size": 24, "bold": True, "color": WHITE}]}], align=PP_ALIGN.CENTER)
    tb(s, 0.6, 3.85, 12.15, 0.5, [{"align": PP_ALIGN.CENTER, "runs": [{"text":
        "CausalStock  ·  CS173 Data Mining Final  ·  Team 2",
        "size": 13, "color": RGBColor(0x9D, 0xB0, 0xC4)}]}],
       align=PP_ALIGN.CENTER)

    out = HERE / f"CausalStock_CS173_Final_{lang.upper()}.pptx"
    prs.save(out)
    print("saved", out, "—", len(prs.slides._sldIdLst), "slides")


if __name__ == "__main__":
    build("en")
    build("zh")
