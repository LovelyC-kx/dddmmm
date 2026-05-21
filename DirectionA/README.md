# CausalStock: Temporal Causal Event Chain Modeling for News-Driven Stock Prediction

## Overview

CausalStock predicts stock movement from financial news by preserving event structure and modeling time-lagged propagation. Direction A is organized as three phases:

1. **Phase 1: Event extraction** converts news into structured financial events.
2. **Phase 2: Causal discovery** learns event-type dependency strength `A` and lag matrix `T` with sparse temporal attention.
3. **Phase 3: Causal propagation and prediction** consumes Phase 2 embeddings plus `A/T`, propagates impact with a Neural ODE, maps event impact to stocks, and predicts direction/magnitude.

## Canonical Source Layout

```text
src/
  phase1/
    event_types.py                  # Shared 20-type event ontology
    event_extractor.py              # FinBERT + multi-head event decoder
    train.py                        # Phase 1 training entrypoint
  phase2/
    causal_discovery.py             # STACD sparse temporal attention
  phase3/
    causal_propagation.py           # Neural ODE propagation model
    train.py                        # Phase 3 train/eval + SVG plots
```

Documentation:

```text
docs/
  DirectionA_Math_Model.md          # Single source of truth for equations
  PHASE3_RUNBOOK.md                 # How to run Phase 3 training/evaluation
  figures/causalstock_pipeline.svg  # Clean pipeline figure
```

## Phase 3 Quick Start

Synthetic smoke run:

```powershell
cd DirectionA
python src\phase3\train.py --epochs 8 --synthetic-samples 160 --output-dir outputs\phase3_synthetic
```

Real Phase 2-output run:

```powershell
cd DirectionA
python src\phase3\train.py --data outputs\phase2\phase3_dataset.pt --epochs 30 --batch-size 64 --output-dir outputs\phase3_real
```

See `docs/PHASE3_RUNBOOK.md` for the required `.pt` tensor schema and generated evaluation plots.

## Dependencies

```powershell
pip install -r requirements.txt
```

Phase 3 can train from precomputed Phase 2 tensors without downloading a pretrained language model. The full Phase 1 -> Phase 3 pipeline requires Hugging Face `transformers` and the `ProsusAI/finbert` checkpoint.
