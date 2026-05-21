"""Export the two deck figures that depend on real trained-model artifacts.

These cannot be drawn from summary numbers — they need run outputs:

  causal     20x20 learned causal-strength heatmap + ranked edge list,
             from a Stage-2 graph checkpoint (causal_matrix / lag_matrix).
  confusion  3x3 confusion matrix, from a Stage-3 run_meta.json
             (written by src/phase3/tabular_baseline.py).

Usage:
  python docs/figures/export_model_figures.py causal \
      --graph data/stage2/best_graph.pt
  python docs/figures/export_model_figures.py confusion \
      --run-meta outputs/phase3/tabular_hgb_stratified/run_meta.json

NOTE: data/stage2/best_graph.pt shipped in this repo is a SAMPLE artifact
(metrics={'sample_artifact': True}, near-uniform A) — running `causal` on it
produces a meaningless heatmap. Point --graph at a real trained Stage-2
checkpoint before putting the figure in the deck.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent
EVENTS = ["M1", "M2", "M3", "M4", "M5", "M6", "C1", "C2", "C3", "C4",
          "C5", "C6", "C7", "C8", "K1", "K2", "K3", "K4", "G1", "G2"]
INK = "#243748"


def export_causal(graph_path: Path) -> None:
    import torch
    payload = torch.load(graph_path, map_location="cpu", weights_only=False)
    A = payload["causal_matrix"].float().numpy()
    T = payload["lag_matrix"].float().numpy()
    metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
    if metrics.get("sample_artifact"):
        print("WARNING: this checkpoint is a SAMPLE artifact, not a trained "
              "graph. The figure will not be meaningful.")
    if float(A.max()) - float(A.min()) < 1e-3:
        print("WARNING: causal matrix is near-uniform — graph likely untrained.")

    fig, ax = plt.subplots(figsize=(8.4, 7.2))
    im = ax.imshow(A, cmap="YlOrRd", vmin=0.0, vmax=max(0.2, float(A.max())))
    ax.set_xticks(range(20)); ax.set_xticklabels(EVENTS, fontsize=8)
    ax.set_yticks(range(20)); ax.set_yticklabels(EVENTS, fontsize=8)
    ax.set_xlabel("Effect  (event type b)", color=INK)
    ax.set_ylabel("Cause  (event type a)", color=INK)
    ax.set_title("Learned event-type causal matrix  A", fontweight="bold",
                 color=INK, pad=12)
    fig.colorbar(im, fraction=0.046, pad=0.04, label="A[a,b]  directed strength")

    edges = [(A[i, j], i, j) for i in range(20) for j in range(20) if i != j]
    edges.sort(reverse=True)
    for s, i, j in edges[:6]:
        ax.text(j, i, f"{s:.2f}", ha="center", va="center", fontsize=6.5,
                fontweight="bold", color="white")
    plt.tight_layout()
    p = OUT / "fig_causal_matrix.png"
    plt.savefig(p, dpi=200, bbox_inches="tight"); plt.close()
    print("saved", p)

    print("\nTop-10 causal edges (cause -> effect, strength, lag days):")
    for s, i, j in edges[:10]:
        print(f"  {EVENTS[i]} -> {EVENTS[j]}   A={s:.3f}   lag={T[i, j]:.2f}")


def export_confusion(run_meta_path: Path) -> None:
    meta = json.loads(Path(run_meta_path).read_text(encoding="utf-8"))
    cm = np.array(meta["test"]["confusion"], dtype=float)
    names = ["UP", "DOWN", "FLAT"]
    row = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1e-9)

    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    im = ax.imshow(row, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(3)); ax.set_xticklabels(names)
    ax.set_yticks(range(3)); ax.set_yticklabels(names)
    ax.set_xlabel("Predicted", color=INK); ax.set_ylabel("True", color=INK)
    split = meta.get("split", "")
    ax.set_title(f"Confusion matrix ({split})", fontweight="bold", color=INK,
                 pad=10)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{int(cm[i, j])}\n{row[i, j]*100:.0f}%",
                    ha="center", va="center", fontsize=9,
                    color="white" if row[i, j] > 0.5 else INK)
    plt.tight_layout()
    p = OUT / "fig_confusion.png"
    plt.savefig(p, dpi=200, bbox_inches="tight"); plt.close()
    print("saved", p)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("causal")
    c.add_argument("--graph", default="data/stage2/best_graph.pt")
    f = sub.add_parser("confusion")
    f.add_argument("--run-meta",
                   default="outputs/phase3/tabular_hgb_stratified/run_meta.json")
    args = ap.parse_args()
    if args.cmd == "causal":
        export_causal(Path(args.graph))
    else:
        export_confusion(Path(args.run_meta))


if __name__ == "__main__":
    main()
