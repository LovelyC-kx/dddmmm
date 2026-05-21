# Direction A Submission

This package is capped below 10 MB, so it includes code plus tiny runnable
sample artifacts instead of the full Yahoo/FNSPID data, pretrained language
model weights, or trained checkpoints.

## Contents

- `src/phase1`: FinBERT event extraction training/inference code.
- `src/phase2`: STACD causal discovery training code.
- `src/phase3`: Stage 3 dataset builder, tabular baseline, and figure tools.
- `data/labels/sample_labels.jsonl`: compact labeled event sample.
- `data/embeddings/emb.pt` and `data/embeddings/meta.json`: compact synthetic
  embeddings for Stage 2 and Stage 3 smoke runs.
- `data/sp100_prices/*.csv`: compact OHLCV sample tables.
- `data/stage2/best_graph.pt`: compact sample causal graph for Stage 3 build.
- `scripts/make_tiny_submission_data.py`: regenerates the included tiny data.

## Environment

```powershell
pip install -r requirements.txt
```

Phase 1 uses `ProsusAI/finbert` through Hugging Face. The model weights are not
included because they exceed the submission size cap; they download/cache in the
normal Hugging Face cache when Phase 1 is run.

## Runnable Smoke Pipeline

Run commands from the package root:

```powershell
cd DirectionA
```

Regenerate the tiny sample data if needed:

```powershell
python scripts\make_tiny_submission_data.py
```

Stage 1 event extractor smoke run:

```powershell
python src\phase1\train.py --labels data\labels\sample_labels.jsonl --output-dir outputs\phase1_smoke --epochs 1 --batch-size 4 --max-length 64
```

Stage 2 causal discovery smoke run:

```powershell
python src\phase2\train.py --embeddings data\embeddings\emb.pt --meta data\embeddings\meta.json --price-dir data\sp100_prices --output-dir outputs\stage2_smoke --epochs 1 --batch-size 8 --seq-len 8 --device cpu
```

Stage 3 dataset build from the Stage 2 smoke graph:

```powershell
python src\phase3\build_dataset.py --labels data\labels\sample_labels.jsonl --embeddings data\embeddings\emb.pt --price-dir data\sp100_prices --stage2-dir outputs\stage2_smoke --output data\stage3\phase3_sample.pt --seq-len 8 --price-window 10 --context-mode ticker
```

Stage 3 prediction baseline:

```powershell
python src\phase3\tabular_baseline.py --data data\stage3\phase3_sample.pt --output-dir outputs\phase3_smoke --model hgb --split stratified_random
```

## Full Data

For full experiments, replace the tiny sample files with the full downloaded
Yahoo/FNSPID artifacts and rerun the same commands with larger `seq_len`,
`price-window`, and epoch settings.
