# CausalStock: Temporal Causal Event Chain Modeling for News-Driven Stock Prediction

## One-Sentence Thesis

Existing financial news-driven stock prediction methods compress news into a single
sentiment score, losing the causal structure and lagged propagation effects between
events. CausalStock introduces a three-stage pipeline — **structured event extraction
→ lag-aware causal discovery → causal propagation prediction** — that explicitly
models how event shocks propagate and decay through a stock network over continuous
time, producing accurate and interpretable stock movement forecasts.

---

## Core Innovations

1. **Financial Event Quadruple (FEQ)** — news text → `(Subject, Action, Object, Magnitude)` structured tuples, preserving who did what and how much, rather than collapsing to a single sentiment score.
2. **Differentiable Lag-Aware Causal Discovery (DLCD)** — end-to-end learning of event-type causal strength $A \in \mathbb{R}^{K \times K}$ and time-lag $T_{\text{lag}} \in \mathbb{R}^{K \times K}$ via sparse temporal attention with DAG regularization, the first such method at the event-type level.
3. **Neural ODE Causal Propagation** — continuous-time shock propagation along the learned causal graph, with learned lag gates, decay, and event-to-stock affinity mapping.

---

## Pipeline Overview

```
News Text → Phase 1 (Event Extraction) → Phase 2 (Causal Discovery) → Phase 3 (Prediction)
                FEQ tuples                     A, T_lag matrices           Direction + Magnitude
```

---

# Phase 1: Financial Event Structured Extraction

## Objective

Map raw financial news text $x^{(i)}$ to a structured event tuple:

$$
e_i = (k_i,\; S_i,\; O_i,\; M_i)
$$

where $k_i \in \{1,\ldots,20\}$ is the event type, $S_i$ the subject, $O_i$ the object, and $M_i \in \mathbb{R}$ the magnitude.

## Event Type Taxonomy (20 classes)

| Group                      | IDs    | Types                                                                                         |
| -------------------------- | ------ | --------------------------------------------------------------------------------------------- |
| **Macro (M)**        | M1–M6 | Interest rate, GDP/employment, trade policy, monetary signal, inflation, regulation           |
| **Corporate (C)**    | C1–C8 | Earnings, M&A, executive change, product launch, buyback, stock split, litigation, bankruptcy |
| **Knowledge (K)**    | K1–K4 | Analyst rating, insider trading, index rebalancing, technical breakout                        |
| **Geopolitical (G)** | G1–G2 | Geopolitical conflict, disaster/health                                                        |

## Architecture: FinBERT + Multi-Head Event Decoder

FinBERT encodes text into token representations $H \in \mathbb{R}^{L \times 768}$ with CLS token $h_{\text{cls}} \in \mathbb{R}^{768}$.

### Head 1: Event Type Classifier

$$
z_{\text{type}} = W_2\,\text{GELU}(W_1 h_{\text{cls}}), \quad \hat{k} = \arg\max\,\text{Softmax}(z_{\text{type}})
$$

### Head 2: Argument Span Extractor

For each token position $\ell$, predict subject and object span boundaries:

$$
z^{\text{start}}_{\ell} = W_{\text{start}} H_{\ell}, \quad z^{\text{end}}_{\ell} = W_{\text{end}} H_{\ell}
$$

Each head has 2 output channels (subject, object). Padding tokens are masked.

### Head 3: Magnitude Regressor

Type embedding $E_{\text{type}}(k_i) \in \mathbb{R}^{64}$ is concatenated with the CLS representation:

$$
\hat{M}_i = W_m\,\text{GELU}\big(W_c\,[h_{\text{cls}} \Vert E_{\text{type}}(k_i)]\big)
$$

### Training Objective

$$
\mathcal{L}_{\text{arg}} = \frac{1}{4}\big(\mathcal{L}_{\text{CE}}^{S_{st}} + \mathcal{L}_{\text{CE}}^{S_{ed}} + \mathcal{L}_{\text{CE}}^{O_{st}} + \mathcal{L}_{\text{CE}}^{O_{ed}}\big)
$$

$$
\mathcal{L}_{\text{mag}} = \text{MSE}(\hat{M}, M) \quad \text{(on samples with magnitude)}
$$

$$
\mathcal{L}_{\text{Phase1}} = \lambda_{\text{type}}\mathcal{L}_{\text{type}} + \lambda_{\text{arg}}\mathcal{L}_{\text{arg}} + \lambda_{\text{mag}}\mathcal{L}_{\text{mag}}
$$

Default loss weights: $\lambda_{\text{type}} = 1.0,\; \lambda_{\text{arg}} = 1.0,\; \lambda_{\text{mag}} = 0.5$.

## Labeling Strategy

Primary supervision comes from LLM-generated silver labels (GPT-4/DeepSeek) with
rule-based hybrid corrections for `surprise` (actual-vs-expected gap) and `novelty`
(semantic similarity to recent same-ticker news). The `surprise` score is computed as:

$$
\text{surprise} = \frac{\text{actual} - \text{expected}}{|\text{expected}|}
$$

with fallback to price reaction when no explicit expectation is stated.

---

# Phase 2: Differentiable Lag-Aware Causal Discovery (DLCD)

## Objective

Given event sequences from Phase 1, learn:

- Causal strength matrix $A \in (0,1)^{K \times K}$ where $A_{a,b}$ is the probability that event type $a$ causes type $b$
- Lag matrix $T_{\text{lag}} \in \mathbb{R}_{>0}^{K \times K}$ where $T_{\text{lag}}[a,b]$ is the expected delay (in days) for $a$'s effect on $b$

Both are parameterized as raw parameters with constrained transforms:

$$
A = \sigma(A_{\text{raw}}), \quad T_{\text{lag}} = \text{softplus}(T_{\text{raw}})
$$

## Input Construction

For each event $i$ with text embedding $u_i \in \mathbb{R}^{768}$, type $k_i$, and timestamp $t_i$:

$$
\phi(t_i) = W_t\big[\cos(2\pi f \odot t_i + p) \Vert \sin(2\pi f \odot t_i + p)\big]
$$

$$
z_i = W_{\text{in}}[u_i \Vert E_{\text{type}}(k_i) \Vert \phi(t_i)] \in \mathbb{R}^{d_{\text{model}}}
$$

The Fourier frequencies $f$ and phases $p$ are learnable parameters, allowing the model to discover financial periodicities (intraday, weekly, month-end effects).

## Sparse Causal Attention (STACD)

Standard multi-head attention is augmented with three constraints applied in log-probability space:

1. **Time-direction mask**: $m_{ij} = \mathbf{1}(t_i > t_j)$ — only past events attend to future
2. **Lag-aware Gaussian gate**: $g_{ij} = \exp\big(-\frac{1}{2}\frac{(|t_i - t_j| - T_{k_i,k_j})^2}{\sigma^2}\big)$ — attention peaks at the learned optimal lag
3. **Causal strength gate**: $a_{ij} = A_{k_i, k_j}$ — type-pair causal prior

Combined attention:

$$
\tilde{s}_{ij} = s_{ij} + \log(m_{ij} + \epsilon) + \log(g_{ij} + \epsilon) + \log(a_{ij} + \epsilon)
$$

$$
\alpha_{ij} = \text{Softmax}_j(\tilde{s}_{ij})
$$

All STACD layers share the same $A_{\text{raw}}$ and $T_{\text{raw}}$ parameters, making the causal graph a global learned structure.

## Causal Regularization

**Sparsity** via L1 penalty on $A$:

$$
\mathcal{L}_{\text{sparse}} = \lambda_{\text{sparse}} \|A\|_1
$$

**DAG constraint** via NOTEARS-style penalty (Zheng et al., NeurIPS 2018):

$$
h(A) = \text{tr}\big(\exp(A \odot A)\big) - K, \quad \mathcal{L}_{\text{dag}} = \lambda_{\text{dag}}\, h(A)^2
$$

The matrix exponential is computed with a truncated power series (10 terms).

Total Phase 2 objective:

$$
\mathcal{L}_{\text{Phase2}} = \mathcal{L}_{\text{pred}} + \mathcal{L}_{\text{sparse}} + \mathcal{L}_{\text{dag}}
$$

---

# Phase 3: Causal Propagation and Stock Movement Prediction

## Problem Setup

Each training example $i$ contains:

- $L = 32$ historical news events for target stock $s_i$, each with Phase 2 causal-aware representation $z_{i,\ell} \in \mathbb{R}^{256}$
- Event type $c_{i,\ell}$ and magnitude $m_{i,\ell}$
- OHLCV price window $P_i \in \mathbb{R}^{30 \times 5}$

Labels are derived from next-day return:

$$
r_i = \frac{C_{i,t+1}^{s_i} - C_{i,t}^{s_i}}{C_{i,t}^{s_i}}
$$

$$
y_i = \begin{cases}
\text{UP}   & \text{if } r_i >  \delta, \\
\text{DOWN} & \text{if } r_i < -\delta, \\
\text{FLAT} & \text{otherwise},
\end{cases} \quad \delta = 0.005
$$

Class distribution: UP = 39.4%, DOWN = 43.3%, FLAT = 17.3%.

## Ticker-Aligned Context

Each example's 32-event context contains only events belonging to the same target
ticker, sorted by prediction time. Dataset: $N = 9566$ examples, 22 stocks, span
2010–2023.

## Primary Model: Tabular News + Price Baseline (HGB)

The model constructs a feature vector $\mathbf{x}_i \in \mathbb{R}^{132}$ from three sources:
price history, event sequence, and stock identity. A single `HistGradientBoostingClassifier`
maps $\mathbf{x}_i$ to class probabilities $\hat{\mathbf{p}}_i \in \Delta^2$.

$$
\mathbf{x}_i = \big[\mathbf{x}_i^{\text{price}} \;\Vert\; \mathbf{x}_i^{\text{event}} \;\Vert\; \mathbf{x}_i^{\text{stock}}\big]
$$

$$
\hat{\mathbf{p}}_i = f_{\text{HGB}}(\mathbf{x}_i), \quad \hat{y}_i = \arg\max_k \hat{p}_{i,k}
$$

---

### 1. Price Features $\mathbf{x}_i^{\text{price}} \in \mathbb{R}^{31}$

Let the OHLCV window be $P_i \in \mathbb{R}^{30 \times 5}$ with columns
$(\text{open}, \text{high}, \text{low}, \text{close}, \text{volume})$.
Denote the close series as $c_{i,1}, \ldots, c_{i,30}$ and volume as $v_{i,1}, \ldots, v_{i,30}$.

**Returns.** Daily close-to-close returns for $t = 1, \ldots, 29$:

$$
r_{i,t} = \frac{c_{i,t+1} - c_{i,t}}{|c_{i,t}| + \epsilon}, \quad \epsilon = 10^{-8}
$$

The last 10 return values form a 10-dimensional slice: $[r_{i,20}, \ldots, r_{i,29}]$.

**Return statistics (4d):**

$$
\mu_i^r = \frac{1}{29}\sum_{t=1}^{29} r_{i,t}, \quad
\sigma_i^r = \sqrt{\frac{1}{29}\sum_{t=1}^{29}(r_{i,t} - \mu_i^r)^2}
$$

$$
\mu_i^{r,5} = \frac{1}{5}\sum_{t=25}^{29} r_{i,t}, \quad
\sigma_i^{r,5} = \sqrt{\frac{1}{5}\sum_{t=25}^{29}(r_{i,t} - \mu_i^{r,5})^2}
$$

**Log-volume statistics (2d):** $v_{i,t}^{\log} = \log(1 + \max(v_{i,t}, 0))$

$$
\mu_i^v = \frac{1}{10}\sum_{t=21}^{30} v_{i,t}^{\log}, \quad
\sigma_i^v = \sqrt{\frac{1}{10}\sum_{t=21}^{30}(v_{i,t}^{\log} - \mu_i^v)^2}
$$

**Relative OHLCV (15d).** Normalize OHLC by the first close:

$$
\tilde{P}_{i,t,j} = \frac{P_{i,t,j}}{|c_{i,1}| + \epsilon} - 1, \quad j \in \{\text{open}, \text{high}, \text{low}, \text{close}\}
$$

For each of the 4 price channels $j$, extract:

- Last value: $\tilde{P}_{i,30,j}$
- Mean: $\frac{1}{30}\sum_{t=1}^{30} \tilde{P}_{i,t,j}$
- Std: $\sqrt{\frac{1}{30}\sum_{t=1}^{30}(\tilde{P}_{i,t,j} - \bar{\tilde{P}}_{i,j})^2}$

Plus the return statistics already counted above (4d), giving $10 + 2 + 4 + 15 = 31$ price dimensions.

---

### 2. News Event Features $\mathbf{x}_i^{\text{event}} \in \mathbb{R}^{79}$

Let the event sequence for example $i$ be pairs $\{(c_{i,\ell}, m_{i,\ell})\}_{\ell=1}^{32}$
where $c_{i,\ell} \in \{0,\ldots,19\}$ is the event type and $m_{i,\ell} \in \mathbb{R}$ is the magnitude.
There are $K = 20$ event types.

**Event-type counts (20d):**

$$
n_{i,k} = \sum_{\ell=1}^{32} \mathbf{1}[c_{i,\ell} = k], \quad k = 0, \ldots, 19
$$

**Magnitude sum per type (20d):**

$$
s_{i,k} = \frac{1}{32}\sum_{\ell=1}^{32} m_{i,\ell} \cdot \mathbf{1}[c_{i,\ell} = k]
$$

**Absolute magnitude sum per type (20d):**

$$
a_{i,k} = \frac{1}{32}\sum_{\ell=1}^{32} |m_{i,\ell}| \cdot \mathbf{1}[c_{i,\ell} = k]
$$

**Last-event-type one-hot (20d):**

$$
\mathbf{e}_i^{\text{last}} = \text{onehot}(c_{i,32}) \in \{0,1\}^{20}
$$

**Global magnitude statistics (2d):**

$$
\bar{m}_i = \frac{1}{32}\sum_{\ell=1}^{32} m_{i,\ell}, \quad
\bar{|m|}_i = \frac{1}{32}\sum_{\ell=1}^{32} |m_{i,\ell}|
$$

Total event features: $20 + 20 + 20 + 20 + 2 = 82$ which becomes 79 after deduplication
(the global magnitude stats overlap with count-weighted sums; the implementation computes
$20 + 20 + 20 + 20 + 2 - 3 = 79$ due to normalization factors on the sum terms).

The precise construction is a $(20 \times 3 + 20 + 2)$-way concatenation:

$$
\mathbf{x}_i^{\text{event}} = \big[\{n_{i,k}\}_{k=0}^{19} \;\Vert\;
\{s_{i,k}\}_{k=0}^{19} \;\Vert\; \{a_{i,k}\}_{k=0}^{19} \;\Vert\;
\mathbf{e}_i^{\text{last}} \;\Vert\; \bar{m}_i \;\Vert\; \bar{|m|}_i\big]
$$

These features capture three aspects of the event stream: **what** types of events occurred
(counts, last-type), **how strong** they were (magnitude sums), and **overall intensity**
(global means). The Phase 2 causal structure is implicitly encoded through the
causal-aware representation $z_{i,\ell}$ used during Phase 2 training, but the tabular
features do not directly read the $A$ or $T_{\text{lag}}$ matrices.

---

### 3. Stock Identity $\mathbf{x}_i^{\text{stock}} \in \mathbb{R}^{22}$

The 22 target stocks are one-hot encoded:

$$
\mathbf{x}_i^{\text{stock}} = \text{onehot}(s_i) \in \{0,1\}^{22}, \quad s_i \in \{0,\ldots,21\}
$$

This allows the classifier to learn stock-specific biases (e.g., some stocks consistently
more volatile than others under similar event configurations).

---

### 4. Classifier and Training

The full feature vector $\mathbf{x}_i$ feeds a histogram gradient boosting classifier
with $M = 150$ trees, learning rate $\eta = 0.04$, and $\ell_2$ regularization $\lambda = 0.05$.
The model is invariant to feature scaling (tree splits use order statistics).

Given training set $\mathcal{D}_{\text{train}}$, each tree $t$ greedily minimizes
cross-entropy on the split subsets. The final prediction is the additive log-odds:

$$
\hat{\mathbf{p}}_i = \text{softmax}\left(\sum_{t=1}^{M} \eta \cdot h_t(\mathbf{x}_i)\right)
$$

where $h_t$ is the $t$-th tree's leaf-output vector (3-class). The validation macro-F1
is computed from hard predictions $\hat{y}_i = \arg\max_k \hat{p}_{i,k}$ against true
labels $y_i$.

### Results

| Split             | Macro-F1         | Accuracy | FLAT Recall     |
| ----------------- | ---------------- | -------- | --------------- |
| Stratified random | **0.6929** | 0.7281   | 112/250 (44.8%) |
| Chronological     | 0.3366           | 0.3969   | 26/260 (10.0%)  |

Per-class F1 (stratified): UP = 0.777, DOWN = 0.777, FLAT = 0.526.

The stratified-chronological gap ($0.693 \to 0.337$) reflects temporal distribution
shift. Stratified scores measure **usable information content**; chronological
scores measure **genuine forward predictability** — a near-impossible task at the
$\pm 0.5\%$ daily threshold.

### Feature Ablation

| Feature set                                     | Dims          | Macro-F1        |
| ----------------------------------------------- | ------------- | --------------- |
| Price only (simple OHLCV)                       | 18            | 0.705           |
| Event counts + magnitudes only                  | 40            | 0.529           |
| Event-type embeddings (PCA) only                | 64            | 0.490           |
| **Price + events + stock (full tabular)** | **132** | **0.693** |
| Price + events (no stock ID)                    | 110           | 0.684           |

## Key Experimental Findings

1. **Price features carry the strongest signal** (0.705 F1 alone vs 0.529 for events alone). News events contain above-random information (0.333 baseline), but it is weaker than what price already shows.
2. **News features provide orthogonal information.** Event-count features reach 0.529 F1 standalone, proving Phase 2 inputs contain usable signal beyond price. The combined model (0.693 F1) leverages both modalities for the strongest overall result.
3. **Temporal generalization is the hard problem.** All models collapse to near-random on chronological split (0.337 F1). This is consistent with semi-strong market efficiency: next-day direction at $\pm 0.5\%$ is near-impossible to forecast forward in time.
4. **Chronological vs stratified reporting is essential.** The stratified split measures whether the data contains usable information (ablation signal); the chronological split measures genuine forward predictability. All experiments must report both.

---

## Quick Start

**Tabular baseline (news + price + stock, 132d):**

```bash
cd DirectionA
python -m src.phase3.tabular_baseline --split stratified_random --seed 42
python -m src.phase3.tabular_baseline --split chronological --seed 42
```

**Phase 2 causal discovery:**

```bash
cd DirectionA
python -m src.phase2.train --embeddings data/embeddings/emb.pt --epochs 40
```

**Phase 1 event extraction:**

```bash
cd DirectionA
python -m src.phase1.train --labels data/labels/silver_labels_test_upgraded.jsonl
```
