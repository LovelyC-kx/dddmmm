# CausalStock: Event-Structured Temporal Causal Modeling for News-Driven Stock Prediction

CS173 Data Mining — Team 2. This repository (Direction A) implements the
three-stage pipeline described in the final report
(`docs/final-report/report.tex`).

## Overview

CausalStock predicts next-day stock movement (UP / DOWN / FLAT, threshold
±0.5%) from financial news and price history, while keeping event structure
explicit. It has three stages:

1. **Phase 1 — Event extraction.** Convert each news article into a structured
   financial event: a `(subject, action, object, magnitude)` quadruple plus an
   impact profile (polarity, surprise, scope, novelty, credibility), over a
   20-class event ontology.
2. **Phase 2 — Lag-aware causal discovery (STACD).** Learn an event-type
   strength matrix `A` and lag matrix `T_lag` with sparse temporal attention
   and NOTEARS-style acyclicity regularization.
3. **Phase 3 — Stock-movement prediction.** Assemble price, event, and
   stock-identity features and predict direction with an interpretable tabular
   (histogram gradient-boosting) classifier, reported under both stratified
   and chronological splits.

## Repository layout

```text
src/
  phase1/   event extraction
  phase2/   causal discovery
  phase3/   dataset build + tabular prediction + figures
  data/     auxiliary knowledge-base utilities
data/       tiny runnable sample artifacts (see "Data samples")
docs/       report, math model, framework notes, figures, slides
configs/    default.yaml — shared hyper-parameters
requirements.txt
```

## Code files — purpose and how to run

Run all commands from the `DirectionA/` directory.

### Phase 1 — `src/phase1/`

| File | Purpose | Run |
|---|---|---|
| `event_types.py` | Shared 20-class event ontology (M1–M6, C1–C8, K1–K4, G1–G2). | imported as a module |
| `download_data.py` | Downloads raw datasets (FNSPID news+prices, and related sources). | `python src/phase1/download_data.py --fnspid --prices` |
| `llm_event_labeling.py` | LLM (DeepSeek / GPT) silver-labels news into structured events with rule- and market-grounded corrections; writes a JSONL label file. Set the API key via `--api-key-file` or the `LLM_API_KEY` environment variable. | `python src/phase1/llm_event_labeling.py --input <news.csv> --output data/labels/silver_labels.jsonl --api-key-file <keys.txt> --use-article` |
| `event_extractor.py` | FinBERT + multi-head event decoder (event-type, argument-span, magnitude heads). | imported as a module |
| `train.py` | Phase 1 training entry point — trains the event extractor on silver labels. | `python src/phase1/train.py --labels data/labels/sample_labels.jsonl --output-dir outputs/phase1` |
| `01_phase1_event_extraction_training.ipynb` | Notebook walkthrough of Phase 1 extraction/training. | open in Jupyter |

### Phase 2 — `src/phase2/`

| File | Purpose | Run |
|---|---|---|
| `download_data.py` | Dataset download helper for Phase 2 inputs. | `python src/phase2/download_data.py --fnspid` |
| `preprocess.py` | Preprocesses label files into Phase-2 event sequences. | `python src/phase2/preprocess.py --labels data/labels/sample_labels.jsonl --output-dir outputs/phase2_pre` |
| `dataset.py` | Phase-2 dataset class — loads embeddings, metadata, and prices into event sequences. | imported as a module |
| `causal_discovery.py` | STACD network — learnable Fourier temporal encoder, lag-aware sparse causal attention, NOTEARS DAG regularization, and causal-graph extraction. | imported as a module |
| `model_wrapper.py` | Thin wrapper exposing the STACD model to the trainer. | imported as a module |
| `train.py` | Phase 2 training entry point — trains STACD and writes causal-graph checkpoints (`best_graph.pt`, `causal_epoch_*.pt`). | `python src/phase2/train.py --embeddings data/embeddings/emb.pt --meta data/embeddings/meta.json --price-dir data/sp100_prices --output-dir outputs/phase2 --device cpu` |
| `README.md` | Phase-2 module notes. | — |

### Phase 3 — `src/phase3/`

| File | Purpose | Run |
|---|---|---|
| `download_label_prices.py` | Downloads Yahoo OHLCV histories for the tickers referenced by the Phase-3 labels. | `python src/phase3/download_label_prices.py --labels data/labels/sample_labels.jsonl --output-dir data/sp100_prices` |
| `build_dataset.py` | Builds the Phase-3 tensor dataset from labels, embeddings, prices, and the Stage-2 causal graph. | `python src/phase3/build_dataset.py --labels data/labels/sample_labels.jsonl --embeddings data/embeddings/emb.pt --price-dir data/sp100_prices --stage2-dir data/stage2 --output data/stage3/phase3_dataset.pt --context-mode ticker` |
| `tabular_baseline.py` | **Evaluated Phase-3 model.** Builds price + event + stock-identity features and trains a histogram gradient-boosting classifier; reports macro-F1 and accuracy under a stratified or chronological split. | `python src/phase3/tabular_baseline.py --data data/stage3/phase3_dataset.pt --model hgb --split stratified_random` |
| `generate_figures.py` | Generates EDA and result figures from the Phase-3 dataset. | `python src/phase3/generate_figures.py` |

### Auxiliary — `src/data/`

| File | Purpose |
|---|---|
| `knowledge_base.py` | Auxiliary financial knowledge-base utilities (dense/sparse news indexing). Not required by the core three-phase pipeline. |

## Data samples

To stay small and runnable, this repository ships **tiny synthetic sample
artifacts**, not the full data. They use three placeholder tickers
(`AAA`, `BBB`, `CCC`) and are only meant for smoke runs.

| Path | What it is |
|---|---|
| `data/labels/sample_labels.jsonl` | ~240 sample silver-labelled events, one JSON object per line: `event_type`, `subject/action/object/magnitude`, impact profile (`polarity/surprise/scope/novelty/credibility`), `source_date`, `source_ticker`. |
| `data/embeddings/emb.pt` | `(240, 768)` tensor of per-event FinBERT `[CLS]` embeddings (sample). |
| `data/embeddings/meta.json` | Per-event metadata aligned with `emb.pt`: `event_type`, `timestamp`, `ticker`. |
| `data/sp100_prices/{AAA,BBB,CCC}.csv` | Sample daily OHLCV price tables (`date, open, high, low, close, volume`). |
| `data/stage2/best_graph.pt`, `causal_epoch_0.pt` | Sample Stage-2 causal-graph checkpoints (20×20 `causal_matrix` and `lag_matrix`); placeholders so the Phase-3 build can run. |

**Full experiments.** The results in the report use a 5% subset of FNSPID:
after LLM labelling and deduplication this yields **10,901 structured events**
and a downstream study of **9,566 ticker-aligned examples over 22 stocks,
2010–2023**. To reproduce them, replace the sample files above with the full
downloaded artifacts and rerun the same commands with full `seq-len`,
`price-window`, and epoch settings.

## Environment

```bash
pip install -r requirements.txt
```

Phase 1 uses the `ProsusAI/finbert` checkpoint via Hugging Face
`transformers`; the weights are downloaded/cached on first run and are not
bundled here.

## Quick start (smoke pipeline)

```bash
cd DirectionA
# Phase 2 — causal discovery on the sample embeddings
python src/phase2/train.py --embeddings data/embeddings/emb.pt \
  --meta data/embeddings/meta.json --price-dir data/sp100_prices \
  --output-dir outputs/stage2_smoke --epochs 1 --batch-size 8 --seq-len 8 --device cpu
# Phase 3 — build the tensor dataset from the Stage-2 graph
python src/phase3/build_dataset.py --labels data/labels/sample_labels.jsonl \
  --embeddings data/embeddings/emb.pt --price-dir data/sp100_prices \
  --stage2-dir outputs/stage2_smoke --output data/stage3/phase3_sample.pt \
  --seq-len 8 --price-window 10 --context-mode ticker
# Phase 3 — tabular prediction baseline
python src/phase3/tabular_baseline.py --data data/stage3/phase3_sample.pt \
  --output-dir outputs/phase3_smoke --model hgb --split stratified_random
```

## Documentation

- `docs/final-report/report.tex` — the final report (compile with
  `pdflatex` + `bibtex`).
- `docs/DirectionA_Math_Model.md` — equations and notation.
- `docs/CausalStock_Framework.md` — framework design notes.
- `docs/TRAINING_PARAMS.md` — training hyper-parameters.
- `docs/figures/` — generated figures and the scripts that produce them.
