"""EventChain pipeline architecture figure — clean horizontal flow.

Writes fig_architecture.png ; run:  python docs/figures/make_architecture.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent
NAVY = "#1d3a5f"; BLUE = "#2e6f9e"; ORANGE = "#e3861f"; INK = "#243748"
GRAY = "#6b7785"; LIGHT = "#eef2f7"; CREAM = "#fbe9d2"; GREEN = "#2f9e74"; RED = "#c2492f"
plt.rcParams.update({"font.family": "DejaVu Sans", "savefig.dpi": 200,
                     "savefig.bbox": "tight"})
SH = [pe.SimplePatchShadow(offset=(2.4, -2.4), shadow_rgbFace="#97a3b0",
                           alpha=0.3, rho=0.5), pe.Normal()]

fig, ax = plt.subplots(figsize=(14.0, 7.4))
ax.set_xlim(0, 140); ax.set_ylim(0, 72); ax.axis("off")


def box(x, y, w, h, fc, txt="", tc="white", fs=9, bold=True, rs=0.7, ec=None,
        dash=False, lh=1.3, shadow=True):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rs}",
                       fc=fc, ec=ec or fc, lw=1.3, ls=":" if dash else "-", zorder=3)
    if shadow and not dash:
        p.set_path_effects(SH)
    ax.add_patch(p)
    if txt:
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs,
                color=tc, fontweight="bold" if bold else "normal",
                linespacing=lh, zorder=5)


def arrow(x1, y1, x2, y2, color=NAVY, lw=2.4):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=16, color=color, lw=lw, zorder=2))


def cap(x, y, t, fs=8.4, color=GRAY, ha="center", bold=False, it=True):
    ax.text(x, y, t, fontsize=fs, color=color, ha=ha,
            fontweight="bold" if bold else "normal",
            style="italic" if it else "normal", zorder=6)


ax.text(70, 69, "EventChain — Pipeline Architecture", ha="center",
        fontsize=15.5, fontweight="bold", color=INK)

# ---------------- EDA band (drives the schema) ----------------
for k, t in enumerate(["29% duplicate headlines", "68–79% missing publisher/author",
                       "89% multi-scope news cues"]):
    box(3 + k * 25.5, 58, 24, 5, CREAM, t, tc=INK, fs=8.3, ec=ORANGE, rs=0.6)
cap(40, 64.6, "EXPLORATORY DATA ANALYSIS", fs=9, color=ORANGE, bold=True, it=False)
arrow(40, 58, 38, 53.2, color=ORANGE, lw=1.8)
cap(57, 55.4, "→ data-driven attributes:  novelty · credibility · scope",
    fs=8.4, color=ORANGE)

# ---------------- main pipeline row ----------------
y0, h0 = 41, 11
box(2, y0, 20, h0, "white", "News Corpora\n\n5% FNSPID subset\n22 stocks · 2010–23",
    tc=INK, fs=8.4, dash=True, ec=GRAY, bold=False, lh=1.4)
box(26, y0, 25, h0, NAVY, "Phase 1\nFinBERT Multi-Head\nEvent Extractor\n"
    "→ 10,901 events", fs=8.6, lh=1.35)
box(55, y0, 22, h0, NAVY, "Phase 2\nSTACD\nLag-Aware\nCausal Discovery", fs=8.6, lh=1.35)
box(81, y0, 28, h0, NAVY, "Phase 3\nFeature stack →\nHistGradientBoosting\n"
    "+ causal ensemble", fs=8.6, lh=1.35)
box(113, y0, 25, h0, "#fff8ec", "", ec=ORANGE)
cap(125.5, y0 + h0 - 1.6, "Next-day movement", fs=8.6, color=INK, bold=True, it=False)
for k, (t, c) in enumerate([("UP", GREEN), ("DOWN", RED), ("FLAT", GRAY)]):
    ax.add_patch(Circle((118 + k * 5, y0 + 4.2), 2.3, fc=c, ec="white", lw=1.3,
                 zorder=5))
    ax.text(118 + k * 5, y0 + 4.2, t, ha="center", va="center", fontsize=6.6,
            color="white", fontweight="bold", zorder=6)
for x1, x2 in [(22, 26), (51, 55), (77, 81), (109, 113)]:
    arrow(x1, y0 + h0 / 2, x2, y0 + h0 / 2)

# ---------------- detail callouts under the row ----------------
# C1: structured event record under Phase 1
box(24, 12, 29, 23, LIGHT, "", ec=GRAY, rs=0.6, shadow=False)
cap(38.5, 32.4, "Structured event record", fs=8.8, color=INK, bold=True, it=False)
prof = [NAVY, BLUE, ORANGE, GREEN, RED]
for c in range(5):
    ax.add_patch(Rectangle((28.5 + c * 3.4, 26.5), 3.1, 3.0, fc=prof[c],
                 ec="white", lw=0.7, zorder=4))
cap(38.5, 24.6, "(S, A, O, M)  +  impact profile", fs=8, color=INK)
for k, t in enumerate(["polarity", "surprise",
                       "scope        (EDA-driven)", "novelty     (EDA-driven)",
                       "credibility (EDA-driven)"]):
    ax.text(29.5, 22.0 - k * 1.9, "▪ " + t, fontsize=7.6,
            color=ORANGE if k >= 2 else GRAY, zorder=5)
arrow(38.5, 41, 38.5, 35.2, color=GRAY, lw=1.6)

# C2: causal graph under Phase 2
rng = np.random.default_rng(7)
A = np.clip(rng.normal(0.267, 0.048, (20, 20)), 0, 1)
cmap = LinearSegmentedColormap.from_list("", ["#fff3d6", "#e3861f", "#9c3b12"])
box(55, 12, 22, 23, LIGHT, "", ec=GRAY, rs=0.6, shadow=False)
cap(66, 32.4, "Event-type causal graph", fs=8.6, color=INK, bold=True, it=False)
ax.imshow(A, cmap=cmap, extent=[58, 74, 17, 30], aspect="auto", zorder=4,
          vmin=0, vmax=0.5)
ax.add_patch(Rectangle((58, 17), 16, 13, fc="none", ec=NAVY, lw=1.2, zorder=5))
cap(66, 15.0, "A (20×20) + lag T_lag", fs=7.6, color=GRAY)
arrow(66, 41, 66, 35.2, color=GRAY, lw=1.6)

# C3: price branch under Phase 3
box(81, 12, 30, 23, LIGHT, "", ec=GRAY, rs=0.6, shadow=False)
cap(96, 32.4, "Price-history features", fs=8.8, color=INK, bold=True, it=False)
tt = np.linspace(0, 6, 90)
for off, col in [(0, BLUE), (1.1, ORANGE), (2.0, GREEN)]:
    ax.plot(84 + tt * 4.0, 19 + off + 1.1 * np.sin(tt * 1.7 + off)
            + 0.35 * np.cos(tt * 5), color=col, lw=1.0, zorder=5)
cap(96, 15.2, "returns · volatility · log-volume · OHLCV", fs=7.6, color=GRAY)
arrow(96, 41, 96, 35.2, color=GRAY, lw=1.6)

# ---------------- result tags ----------------
box(8, 3, 58, 5.4, "#e3f1ea", "Stratified split:  0.709 macro-F1   "
    "(tabular 0.693 → ensemble 0.709)", tc=INK, fs=8.6, ec=GREEN, rs=0.6, shadow=False)
box(72, 3, 60, 5.4, "#f7e2dd", "Chronological split:  0.337 macro-F1   "
    "≈ random 0.333  (honest forward-time gap)", tc=INK, fs=8.6, ec=RED, rs=0.6,
    shadow=False)
cap(70, 0.6, "Architecture as designed.  Phase 2's graph and the Phase-3 ODE are "
    "reported as diagnosed negative results — see paper.", fs=7.8, color=GRAY)

plt.savefig(OUT / "fig_architecture.png")
print("saved fig_architecture.png")
