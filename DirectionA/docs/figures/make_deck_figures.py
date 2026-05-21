"""Generate polished presentation figures for the EventChain deck.

All numbers are the real reported values (ablation run logs + EDA audit).
Style: rounded gradient bars, soft drop shadows, flat-but-elevated look.
Run:  python docs/figures/make_deck_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#1d3a5f"
BLUE = "#2e6f9e"
ORANGE = "#e3861f"
GOLD = "#f2a93b"
GRAY = "#aab6c3"
GREEN = "#2f9e74"
RED = "#c2492f"
INK = "#243748"

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
    "savefig.facecolor": "white", "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
    "axes.titlesize": 13.5, "axes.titleweight": "bold", "axes.titlecolor": INK,
})

SHADOW = [pe.SimplePatchShadow(offset=(3, -3), shadow_rgbFace="#9aa6b3",
                               alpha=0.33, rho=0.5), pe.Normal()]
SOFT = [pe.SimplePatchShadow(offset=(2, -2), shadow_rgbFace="#9aa6b3",
                             alpha=0.28, rho=0.5), pe.Normal()]


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lighten(h, f):
    r, g, b = _rgb(h)
    return "#%02x%02x%02x" % tuple(int(c + (255 - c) * f) for c in (r, g, b))


def darken(h, f):
    r, g, b = _rgb(h)
    return "#%02x%02x%02x" % tuple(int(c * (1 - f)) for c in (r, g, b))


def grad_bar(ax, x, y, w, h, base, vertical=False):
    """Flat bar with a cylinder-style gradient sheen and a soft drop shadow."""
    rect = Rectangle((x, y), w, h, fc=base, ec="none", zorder=3)
    rect.set_path_effects(SHADOW)
    ax.add_patch(rect)
    stops = [darken(base, 0.14), lighten(base, 0.36), darken(base, 0.14)]
    cmap = LinearSegmentedColormap.from_list("", stops)
    if vertical:                       # standing bar -> left/right shading
        grad = np.linspace(0, 1, 256).reshape(1, -1)
    else:                              # lying bar -> top/bottom shading
        grad = np.linspace(0, 1, 256).reshape(-1, 1)
    im = ax.imshow(grad, extent=[x, x + w, y, y + h], aspect="auto",
                   cmap=cmap, zorder=4, origin="lower")
    clip = Rectangle((x, y), w, h)
    clip.set_transform(ax.transData)
    im.set_clip_path(clip)
    # thin highlight edge for a crisp top
    if vertical:
        ax.plot([x, x + w], [y + h, y + h], color=lighten(base, 0.45),
                lw=1.1, zorder=5, solid_capstyle="round")
    else:
        ax.plot([x + w, x + w], [y, y + h], color=lighten(base, 0.45),
                lw=1.1, zorder=5, solid_capstyle="round")


def save(name):
    p = OUT / f"{name}.png"
    plt.savefig(p)
    plt.close()
    print("saved", p)


# ---------------------------------------------------------------- ablation
def fig_ablation():
    labels = ["Majority-class baseline", "ODE only", "ODE + news",
              "ODE fused", "Tabular (news+price+stock)",
              "Causal ensemble v2", "Causal ensemble v1"]
    vals = [0.201, 0.552, 0.595, 0.623, 0.693, 0.705, 0.709]
    base = [GRAY, "#8f9fb1", "#8f9fb1", "#8f9fb1", NAVY, ORANGE, ORANGE]
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    ax.set_xlim(0, 0.84)
    ax.set_ylim(-0.7, len(vals) - 0.3)
    for i, (v, c) in enumerate(zip(vals, base)):
        grad_bar(ax, 0, i - 0.34, v, 0.68, c)
        ax.text(v + 0.012, i, f"{v:.3f}", va="center", ha="left",
                fontsize=11, fontweight="bold", color=darken(c, 0.15))
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10.5, color=INK)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8])
    ax.tick_params(length=0)
    ax.axvline(0.333, color=RED, ls=(0, (4, 3)), lw=1.4, zorder=2)
    ax.text(0.333, len(vals) - 0.55, " random 0.333", color=RED,
            fontsize=9, va="center")
    ax.set_xlabel("Macro-F1   (stratified random split, test)",
                  fontsize=10.5, color=INK)
    ax.set_title("Ablation — where does performance come from?", pad=14)
    ax.text(0.012, 1.0, "ODE-only variants — not featured", fontsize=8.6,
            style="italic", color="#6b7785")
    plt.tight_layout()
    save("fig_ablation")


# ------------------------------------------------------------------- split
def fig_split():
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    groups = ["Stratified random", "Chronological"]
    f1 = [0.6929, 0.3366]
    acc = [0.7281, 0.3969]
    ax.set_xlim(-0.6, 1.7)
    ax.set_ylim(0, 0.86)
    w = 0.34
    for i in range(2):
        grad_bar(ax, i - w - 0.03, 0, w, f1[i], NAVY, vertical=True)
        grad_bar(ax, i + 0.03, 0, w, acc[i], ORANGE, vertical=True)
        ax.text(i - w / 2 - 0.03, f1[i] + 0.018, f"{f1[i]:.3f}", ha="center",
                fontsize=10, fontweight="bold", color=darken(NAVY, 0.1))
        ax.text(i + w / 2 + 0.03, acc[i] + 0.018, f"{acc[i]:.3f}", ha="center",
                fontsize=10, fontweight="bold", color=darken(ORANGE, 0.15))
    ax.axhline(0.333, color=RED, ls=(0, (4, 3)), lw=1.4)
    ax.text(1.62, 0.345, "random 0.333", color=RED, fontsize=9, ha="right")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(groups, fontsize=11, color=INK)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8])
    ax.tick_params(length=0)
    ax.set_ylabel("Score", color=INK)
    ax.set_title("Honest evaluation: in-distribution vs forward-time", pad=14)
    h = [plt.Rectangle((0, 0), 1, 1, fc=NAVY), plt.Rectangle((0, 0), 1, 1, fc=ORANGE)]
    ax.legend(h, ["Macro-F1", "Accuracy"], frameon=False, ncol=2,
              loc="upper right", fontsize=10)
    plt.tight_layout()
    save("fig_split")


# ----------------------------------------------------------- event-type dist
def fig_event_dist():
    et = ["C1\nearnings", "NONE", "C6\nsplit/cap.", "C4\nproduct", "G1\ngeopol.",
          "M2\necon data", "M4\nmonetary", "C2\nM&A", "K1\nanalyst", "M1\nint.rate"]
    share = [29.2, 15.2, 10.9, 6.7, 6.3, 4.9, 4.6, 4.4, 3.7, 2.9]
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    ax.set_xlim(-0.7, len(et) - 0.3)
    ax.set_ylim(0, 33)
    for i, v in enumerate(share):
        c = ORANGE if i == 0 else NAVY
        grad_bar(ax, i - 0.36, 0, 0.72, v, c, vertical=True)
        ax.text(i, v + 0.7, f"{v}", ha="center", fontsize=9.5,
                fontweight="bold", color=darken(c, 0.1))
    ax.set_xticks(range(len(et)))
    ax.set_xticklabels(et, fontsize=9, color=INK)
    ax.set_yticks([0, 10, 20, 30])
    ax.tick_params(length=0)
    ax.set_ylabel("Share of 10,901 events (%)", color=INK)
    ax.set_title("Event-type distribution is long-tailed (top 10 of 20)", pad=14)
    ax.text(0.97, 0.9, "Top-3 = 55.3%  →  class-aware training",
            transform=ax.transAxes, ha="right", fontsize=9.5,
            style="italic", color="#6b7785")
    plt.tight_layout()
    save("fig_event_dist")


# ----------------------------------------------------------------- missing
def fig_eda_missing():
    fields = ["URL", "Stock_symbol", "Author", "Publisher"]
    miss = [0.02, 33.28, 68.44, 79.46]
    cols = [GREEN, ORANGE, RED, RED]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.7, len(fields) - 0.3)
    for i, (v, c) in enumerate(zip(miss, cols)):
        grad_bar(ax, 0, i - 0.32, max(v, 0.6), 0.64, c)
        ax.text(max(v, 0.6) + 1.6, i, f"{v}%", va="center", fontsize=10.5,
                fontweight="bold", color=darken(c, 0.12))
    ax.set_yticks(range(len(fields)))
    ax.set_yticklabels(fields, fontsize=10.5, color=INK)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(length=0)
    ax.set_xlabel("Missing rate (%)", color=INK)
    ax.set_title("Field-completeness audit (raw FNSPID 5% subset)", pad=14)
    ax.text(0.97, 0.12, "URL ~complete  →  basis for credibility score",
            transform=ax.transAxes, ha="right", fontsize=9,
            style="italic", color=GREEN)
    plt.tight_layout()
    save("fig_eda_missing")


# -------------------------------------------------------------- event clues
def fig_eda_clues():
    clue = ["Scope: market/sector/index", "Price-movement language",
            "Expectation / numeric", "Earnings / revenue", "M&A / contract",
            "Dividend / buyback / split", "Analyst rating", "Legal / regulatory"]
    prev = [89.2, 88.0, 77.4, 56.6, 17.6, 16.7, 12.8, 7.4]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.7, len(clue) - 0.3)
    n = len(clue)
    for i, v in enumerate(prev):
        c = ORANGE if i == 0 else NAVY
        grad_bar(ax, 0, (n - 1 - i) - 0.32, v, 0.64, c)
        ax.text(v + 1.6, n - 1 - i, f"{v}%", va="center", fontsize=10,
                fontweight="bold", color=darken(c, 0.12))
    ax.set_yticks(range(n))
    ax.set_yticklabels(clue[::-1], fontsize=10, color=INK)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(length=0)
    ax.set_xlabel("Share of stock-candidate articles (%)", color=INK)
    ax.set_title("The corpus is event-dense  →  event extraction is justified",
                 pad=14)
    plt.tight_layout()
    save("fig_eda_clues")


# ----------------------------------------------------------------- coverage
def fig_coverage():
    attr = ["Polarity", "Scope", "Novelty", "Credibility", "Surprise"]
    cov = [84.8, 84.7, 84.8, 84.8, 6.6]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.set_xlim(-0.7, len(attr) - 0.3)
    ax.set_ylim(0, 100)
    for i, v in enumerate(cov):
        c = ORANGE if attr[i] == "Surprise" else NAVY
        grad_bar(ax, i - 0.34, 0, 0.68, v, c, vertical=True)
        ax.text(i, v + 2.3, f"{v}%", ha="center", fontsize=10.5,
                fontweight="bold", color=darken(c, 0.12))
    ax.set_xticks(range(len(attr)))
    ax.set_xticklabels(attr, fontsize=10.5, color=INK)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.tick_params(length=0)
    ax.set_ylabel("Coverage (% of 10,901 events)", color=INK)
    ax.set_title("Auxiliary attribute coverage", pad=14)
    ax.text(0.97, 0.5, "Surprise: sparse but high-value\n(earnings & macro releases)",
            transform=ax.transAxes, ha="right", fontsize=8.8,
            style="italic", color=darken(ORANGE, 0.1))
    plt.tight_layout()
    save("fig_coverage")


# -------------------------------------------------------------- card helper
def card(ax, x, y, w, h, text, fc, tc="white", fs=9.5, bold=True,
         rs=0.5, soft=False):
    base = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0,rounding_size={rs}",
                          fc=fc, ec="none", zorder=3)
    base.set_path_effects(SOFT if soft else SHADOW)
    ax.add_patch(base)
    grad = np.linspace(0, 1, 128).reshape(-1, 1)
    cmap = LinearSegmentedColormap.from_list("", [darken(fc, 0.07),
                                                  lighten(fc, 0.16)])
    im = ax.imshow(grad, extent=[x, x + w, y, y + h], aspect="auto",
                   cmap=cmap, zorder=4, origin="lower")
    clip = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0,rounding_size={rs}")
    clip.set_transform(ax.transData)
    im.set_clip_path(clip)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold" if bold else "normal",
            linespacing=1.4, zorder=5)


def arrow(ax, x1, y1, x2, y2, color=NAVY, lw=2.2):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                        mutation_scale=16, color=color, lw=lw, zorder=2)
    ax.add_patch(a)


# ------------------------------------------------------------ architecture
def fig_architecture():
    fig, ax = plt.subplots(figsize=(13.0, 7.4))
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 72)
    ax.axis("off")
    ax.text(60, 69, "EventChain — Data-Driven Structured Event-Chain Framework",
            ha="center", fontsize=14.5, fontweight="bold", color=INK)

    ax.text(6, 65, "EDA  FINDINGS", fontsize=9.5, fontweight="bold", color=ORANGE)
    finds = [("29.0%\nduplicate headlines", 6),
             ("68–79%\npublisher / author missing", 44),
             ("89.2%\nmulti-scope news cues", 82)]
    for txt, x in finds:
        card(ax, x, 55, 32, 8, txt, "#fbe9d2", tc=INK, fs=9.3, rs=0.9)

    ax.text(6, 51.6, "DATA-DRIVEN  ATTRIBUTES", fontsize=9.5,
            fontweight="bold", color=ORANGE)
    attrs = [("Novelty", 11), ("Credibility", 49), ("Scope", 87)]
    for (txt, x), (_, fx) in zip(attrs, finds):
        card(ax, x, 43, 22, 6.6, txt, ORANGE, fs=12, rs=0.8)
        arrow(ax, fx + 16, 55, x + 11, 49.8, color=ORANGE, lw=1.9)

    ax.text(6, 37.4, "PIPELINE", fontsize=9.5, fontweight="bold", color=INK)
    P = [("Phase 1\nEvent extraction\nFinBERT + multi-head\n→ 10,901 events", 6, 30),
         ("Phase 2\nCausal discovery\nSTACD → A, T_lag\n(20×20)", 40, 26),
         ("Phase 3\nFeature stack +\ncausal ensemble\n(HistGradientBoosting)", 70, 30),
         ("Predict\nUP / DOWN\n/ FLAT\nδ = 0.5%", 104, 14)]
    for (txt, x, w) in P:
        fc = BLUE if txt.startswith("Predict") else NAVY
        card(ax, x, 28, w, 11, txt, fc, fs=8.9, rs=0.9)
    for i in range(3):
        x1 = P[i][1] + P[i][2]
        arrow(ax, x1, 33.5, P[i + 1][1], 33.5)
    arrow(ax, 49, 43, 21, 39.3, color=ORANGE, lw=1.9)
    ax.text(35, 41.4, "event schema", fontsize=8.3, style="italic", color=ORANGE)

    arrow(ax, 111, 28, 111, 20.6, color="#8a96a3", lw=1.6)
    card(ax, 6, 11, 52, 7, "Stratified split:  0.709 macro-F1\n"
         "tabular 0.693  →  causal ensemble 0.709",
         "#e3f1ea", tc=INK, fs=9.3, rs=0.8, soft=True)
    card(ax, 64, 11, 50, 7, "Chronological split:  0.337 macro-F1\n"
         "≈ random 0.333   (honest forward-time gap)",
         "#f7e2dd", tc=INK, fs=9.3, rs=0.8, soft=True)
    arrow(ax, 108, 20.4, 40, 18.2, color="#8a96a3", lw=1.3)
    arrow(ax, 111, 20.4, 99, 18.2, color="#8a96a3", lw=1.3)
    ax.text(60, 5.4, "Every attribute traces to a measured data finding;  "
            "every result is reported on both an in-distribution and a "
            "forward-time split.", ha="center", fontsize=9,
            style="italic", color="#6b7785")
    save("fig_architecture")


# ---------------------------------------------------------- data-driven map
def fig_datadriven_map():
    fig, ax = plt.subplots(figsize=(11.4, 5.6))
    ax.set_xlim(0, 114)
    ax.set_ylim(0, 54)
    ax.axis("off")
    ax.text(57, 50, "Three data findings  →  three new event attributes",
            ha="center", fontsize=14.5, fontweight="bold", color=INK)
    cols = [
        ("29.0% of headlines\nare duplicates",
         "Repeats of the same event\ninflate its weight",
         "NOVELTY", "1 − max similarity to\nrecent same-ticker news", 4),
        ("Publisher 79% / Author 68%\nmissing — URL ~complete",
         "No usable provenance\nfield for source trust",
         "CREDIBILITY", "Authority score from\nURL-domain whitelist", 41),
        ("89.2% of articles carry\nmarket / sector scope cues",
         "Many items are not\nsingle-stock events",
         "SCOPE", "single / sector /\nmarket / global", 78),
    ]
    for finding, problem, attr, attrdef, x in cols:
        card(ax, x, 39, 32, 8.6, finding, "#fbe9d2", tc=INK, fs=9, rs=0.9)
        ax.text(x + 16, 36, problem, ha="center", va="top", fontsize=8.4,
                style="italic", color="#6b7785")
        arrow(ax, x + 16, 31.5, x + 16, 26.4, color=ORANGE, lw=2.3)
        card(ax, x + 3, 17, 26, 8.4, attr, NAVY, fs=12.5, rs=0.9)
        ax.text(x + 16, 13.4, attrdef, ha="center", va="top", fontsize=8.5,
                color=INK)
    ax.text(57, 3.4, "Schema is matched to the corpus, not assumed in advance.",
            ha="center", fontsize=9.6, style="italic", color="#6b7785")
    save("fig_datadriven_map")


if __name__ == "__main__":
    fig_ablation()
    fig_split()
    fig_event_dist()
    fig_eda_missing()
    fig_eda_clues()
    fig_coverage()
    # fig_architecture()  # superseded by make_architecture.py
    fig_datadriven_map()
    print("all deck figures rebuilt")
