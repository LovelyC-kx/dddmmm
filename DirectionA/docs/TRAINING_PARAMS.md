# CausalStock: Training Parameters Reference

All training parameters across the three-stage pipeline, keyed by file and default value.

---

## Phase 1: Event Extraction (`src/phase1/train.py`)

CLI-based training. Run with `python -m src.phase1.train`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--labels` | path | *required* | Input JSONL silver labels |
| `--output-dir` | path | `outputs/phase1` | Output directory for checkpoints and metrics |
| `--model-name` | str | `ProsusAI/finbert` | HuggingFace FinBERT model |
| `--freeze-layers` | int | `8` | Number of frozen bottom FinBERT layers |
| `--dropout` | float | `0.3` | Dropout probability in classifier heads |
| `--max-length` | int | `128` | Max token length for tokenizer |
| `--batch-size` | int | `16` | Training batch size |
| `--epochs` | int | `5` | Number of training epochs |
| `--lr` | float | `2e-5` | AdamW learning rate |
| `--weight-decay` | float | `0.01` | AdamW weight decay |
| `--train-ratio` | float | `0.7` | Fraction for training split |
| `--val-ratio` | float | `0.15` | Fraction for validation split |
| `--seed` | int | `42` | Random seed |
| `--grad-clip` | float | `1.0` | Gradient clipping norm |
| `--lambda-type` | float | `1.0` | Event type classification loss weight |
| `--lambda-arg` | float | `1.0` | Argument span extraction loss weight |
| `--lambda-mag` | float | `0.5` | Magnitude regression loss weight |
| `--drop-none` | flag | `False` | Drop `NONE`-type rows before training |

### Model Architecture (hardcoded)

| Parameter | Value |
|---|---|
| FinBERT hidden dim | 768 |
| Classifier hidden dim | 256 |
| Event type embedding dim | 64 |
| Magnitude regressor hidden dim | 128 |
| Number of event types | 20 |

### Loss Components

$$\mathcal{L}_{\text{Phase1}} = \lambda_{\text{type}}\,\text{CE}(\hat{k}, k) + \lambda_{\text{arg}}\,\mathcal{L}_{\text{span}} + \lambda_{\text{mag}}\,\text{MSE}(\hat{M}, M)$$

where $\mathcal{L}_{\text{span}}$ averages 4 cross-entropy losses (subject start/end, object start/end),
with padding positions masked and magnitude loss applied only on samples with `magnitude_mask = 1`.

---

## Phase 2: Causal Discovery (`src/phase2/train.py`)

CLI-based training. Run with `python -m src.phase2.train`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--embeddings` | path | `data/embeddings/emb.pt` | FinBERT text embeddings |
| `--meta` | path | `data/embeddings/meta.json` | Metadata (timestamps, types, tickers) |
| `--price-dir` | path | `data/sp100_prices` | Price CSV directory |
| `--output-dir` | path | `data/stage2_repaired` | Output directory |
| `--epochs` | int | `40` | Training epochs |
| `--batch-size` | int | `32` | Batch size |
| `--lr` | float | `3e-5` | AdamW learning rate |
| `--weight-decay` | float | `0.02` | AdamW weight decay |
| `--seq-len` | int | `32` | Event context sequence length |
| `--label-threshold` | float | `0.0` | Binary label threshold for UP/DOWN |
| `--train-ratio` | float | `0.8` | Chronological train split fraction |
| `--reg-weight` | float | `0.2` | Causal regularization weight |
| `--seed` | int | `42` | Random seed |
| `--device` | str | `cuda` | Torch device |

### Model Architecture (hardcoded in `model_wrapper.py` / `causal_discovery.py`)

| Parameter | Value |
|---|---|
| Model dim $d_{\text{model}}$ | 256 |
| Number of heads | 8 |
| Number of STACD layers | 4 |
| Type embedding dim | 128 |
| Fourier frequencies | 64 |
| Attention dropout | 0.1 |
| Number of event types $K$ | 20 |

### Loss Components

$$\mathcal{L}_{\text{Phase2}} = \underbrace{\text{CE}(\hat{y}, y)}_{\text{classification}} + \lambda_{\text{sparse}}\underbrace{\|A\|_1}_{\text{sparsity}} + \lambda_{\text{dag}}\underbrace{h(A)^2}_{\text{DAG penalty}}$$

with $h(A) = \text{tr}(\exp(A \odot A)) - K$, $\lambda_{\text{sparse}}$ and $\lambda_{\text{dag}}$ controlled by `--reg-weight`.

### Causal Graph Parameters (learned)

| Parameter | Shape | Constraint | Init |
|---|---|---|---|
| $A_{\text{raw}}$ | $20 \times 20$ | $A = \sigma(A_{\text{raw}})$ | $\sigma^{-1}(0.05)$ |
| $T_{\text{raw}}$ | $20 \times 20$ | $T = \text{softplus}(T_{\text{raw}})$ | $\text{softplus}^{-1}(1.0)$ |

---

## Phase 3: Stock Prediction

### Tabular Baseline (`src/phase3/tabular_baseline.py`)

CLI-based. Run with `python -m src.phase3.tabular_baseline`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `--data` | path | `data/stage3/phase3_dataset_ticker_precomputed.pt` | Dataset path |
| `--output-dir` | path | `outputs/phase3/tabular_baseline` | Output directory |
| `--model` | choice | `hgb` | Model: `hgb`, `hgb_regularized`, `extra_trees`, `random_forest` |
| `--split` | choice | `stratified_random` | `stratified_random` or `chronological` |
| `--train-ratio` | float | `0.70` | Training fraction |
| `--val-ratio` | float | `0.15` | Validation fraction |
| `--seed` | int | `42` | Random seed |

#### Built-in Model Configs

| Model | Hyperparameters |
|---|---|
| `hgb` | `max_iter=150, lr=0.04, l2=0.05` |
| `hgb_regularized` | `max_iter=250, lr=0.025, l2=0.2, min_samples_leaf=30` |
| `extra_trees` | `n_estimators=300, min_samples_leaf=4, class_weight=balanced` |
| `random_forest` | `n_estimators=300, max_depth=12, min_samples_leaf=4, class_weight=balanced` |

#### Feature Dimensions

| Group | Dims | Content |
|---|---|---|
| Price | 31 | Returns(-10:), mean/std, 5d stats, log-vol stats, relative OHLCV |
| Events | 79 | Type counts(20), mag sums(20), abs mag sums(20), last-type(20), global stats(2) |
| Stock ID | 22 | One-hot target stock encoding |
| **Total** | **132** | |

---

## Dataset Dimensions Summary

| Parameter | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Event types $K$ | 20 | 20 | 20 |
| Stocks $S$ | — | — | 22 |
| Context length $L$ | 1 (per news) | 32 | 32 |
| Text embedding dim | 768 | 768 | 256 (Phase 2 output) |
| Price window $T$ | — | — | 30 days |
| Dataset size | 10,901 | 9,566 | 9,566 |
| Date range | 2010–2023 | 2010–2023 | 2010–2023 |

---

## Reproducibility

All stages accept `--seed` (default 42). Phase 2 uses a chronological
(time-ordered) split by default, while Phase 3 uses stratified random for
diagnostic runs and chronological for honest forecasting.
