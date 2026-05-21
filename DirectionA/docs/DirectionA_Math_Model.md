# Direction A Mathematical Model

This document matches the current implementation in:

- `src/models/event_extractor.py`
- `src/models/causal_discovery.py`
- `src/models/causal_propagation.py`
- `src/data/knowledge_base.py`
- `src/retrieval/multi_path.py`
- `src/reasoning/ea_cot.py`
- `src/verification/fv.py`

The codebase contains two tracks:

1. **CausalStock**: event extraction, temporal causal discovery, Neural ODE propagation, and stock prediction.
2. **GroundedStock**: retrieval-augmented LLM reasoning with faithfulness verification.

---

## 1. CausalStock

### 1.1 Problem Definition

Given a timestamped financial news stream

$$
\mathcal{X}=\{(x_i,t_i,s_i)\}_{i=1}^{N},
$$

where $x_i$ is the text, $t_i$ is the timestamp, and $s_i$ is the related stock ticker, the goal is to predict stock movement:

$$
\hat{y}^{dir}\in\{\text{DOWN},\text{FLAT},\text{UP}\}, \qquad
\hat{y}^{mag}\in\mathbb{R}.
$$

The model first maps text to structured events, learns type-level causal lags, then propagates event shocks to stocks.

---

## 2. Phase 1: Event Extraction

Implemented by `FinBERTEventExtractor`.

### 2.1 Event Schema

The event extractor predicts:

$$
e_i=(k_i,S_i,O_i,M_i),
$$

where:

- $k_i$ is one of 20 event types
- $S_i$ is a subject span
- $O_i$ is an object span
- $M_i\in[-10,10]$ is event magnitude

The implemented event classes are:

$$
\{M1,\ldots,M6,C1,\ldots,C8,K1,\ldots,K4,G1,G2\}.
$$

### 2.2 Encoder

For tokenized text, FinBERT returns:

$$
H = [h_1,\ldots,h_L]\in\mathbb{R}^{L\times d},
\qquad h_{cls}=h_1\in\mathbb{R}^{d}.
$$

Default FinBERT has $d=768$.

### 2.3 Event Type Head

The event type classifier is:

$$
z^{type}=W_2\,\mathrm{GELU}(W_1h_{cls}),
$$

followed by dropout between the hidden layer and output layer in code. The predicted event type is:

$$
\hat{k}=\arg\max_c \mathrm{softmax}(z^{type})_c.
$$

### 2.4 Argument Span Heads

The subject/object extractor predicts start and end logits for each token:

$$
Z^{start}_{\ell,r}=W^{start}_{r}h_\ell,\qquad
Z^{end}_{\ell,r}=W^{end}_{r}h_\ell,
$$

where $r\in\{\text{subject},\text{object}\}$. Padding positions are masked with a large negative value before decoding or loss computation.

For inference, the decoder searches:

$$
(\hat{a}_r,\hat{b}_r)
=
\arg\max_{1\le a\le b\le L,\;b-a+1\le L_{max}}
\left(Z^{start}_{a,r}+Z^{end}_{b,r}\right).
$$

The default max span length in `predict()` is 12 tokens.

### 2.5 Magnitude Head

The magnitude head embeds the event type and concatenates it with the CLS vector:

$$
u=[h_{cls}\Vert E_k],
$$

then predicts:

$$
\hat{M}=10\tanh(W_2\,\mathrm{Dropout}(\mathrm{GELU}(W_1u))).
$$

The `tanh` scaling is important: the implemented output is bounded to `[-10, 10]`.

### 2.6 Phase 1 Loss

The type loss is cross entropy:

$$
\mathcal{L}_{type}=\mathrm{CE}(z^{type},k).
$$

The argument loss is masked cross entropy. If a subject/object span is missing, its mask can be zero:

$$
\mathcal{L}_{arg}
=\frac{1}{4}
\left(
\mathcal{L}_{S,start}
+\mathcal{L}_{S,end}
+\mathcal{L}_{O,start}
+\mathcal{L}_{O,end}
\right).
$$

The implemented magnitude loss is **Smooth L1**, not MSE:

$$
\mathcal{L}_{mag}
=
\frac{\sum_i m_i^{mask}\,\mathrm{SmoothL1}(\hat{M}_i,M_i)}
{\max(1,\sum_i m_i^{mask})}.
$$

Total loss:

$$
\mathcal{L}_{P1}
=
\lambda_{type}\mathcal{L}_{type}
+\lambda_{arg}\mathcal{L}_{arg}
+\lambda_{mag}\mathcal{L}_{mag}.
$$

Defaults in code are:

$$
\lambda_{type}=1,\quad \lambda_{arg}=1,\quad \lambda_{mag}=0.5.
$$

---

## 3. Phase 2: Sparse Temporal Attention Causal Discovery

Implemented by `STACD` in `causal_discovery.py`.

### 3.1 Input Representation

For event $i$, the model uses:

- text embedding $u_i\in\mathbb{R}^{768}$
- event-type embedding $E(k_i)\in\mathbb{R}^{128}$
- learnable Fourier time encoding $\phi(t_i)\in\mathbb{R}^{128}$

The time encoder computes:

$$
\phi(t)
=
W_t
\left[
\cos(2\pi f\odot t+p)
\Vert
\sin(2\pi f\odot t+p)
\right],
$$

where $f$ and $p$ are learnable frequency and phase parameters.

The initial event representation is:

$$
z_i
=
W_{in}[u_i\Vert E(k_i)\Vert\phi(t_i)]
\in\mathbb{R}^{d_{model}}.
$$

Default:

$$
d_{model}=256,\quad n_{heads}=8,\quad n_{layers}=4.
$$

### 3.2 Learnable Causal Parameters

Each attention layer references shared raw parameters:

$$
A=\sigma(A_{raw})\in(0,1)^{K\times K},
$$

$$
T=\mathrm{softplus}(T_{raw})\in\mathbb{R}_{>0}^{K\times K},
$$

where $A_{ab}$ is the strength from event type $b$ to event type $a$ as used in the attention lookup for target event $i$ and source event $j$, and $T_{ab}$ is the preferred lag.

All STACD layers share the same `causal_raw` and `lag_raw`.

### 3.3 Sparse Temporal Attention

For a target event $i$ attending to source event $j$:

$$
s_{ij}^{(h)}
=
\frac{q_i^{(h)\top}k_j^{(h)}}{\sqrt{d_k}}.
$$

The implementation applies three multiplicative constraints by adding log terms to the attention score.

Temporal direction:

$$
m_{ij}=\mathbf{1}(t_i-t_j>0).
$$

Lag compatibility:

$$
g_{ij}
=
\exp\left(
-\frac{1}{2}
\frac{(|t_i-t_j|-T_{k_i,k_j})^2}{\sigma^2}
\right).
$$

Causal strength:

$$
a_{ij}=A_{k_i,k_j}.
$$

Final score:

$$
\tilde{s}_{ij}^{(h)}
=
s_{ij}^{(h)}
+\log(m_{ij}+\epsilon)
+\log(g_{ij}+\epsilon)
+\log(a_{ij}+\epsilon).
$$

Attention weights:

$$
\alpha_{ij}^{(h)}
=
\mathrm{softmax}_j(\tilde{s}_{ij}^{(h)}).
$$

Layer output uses standard multi-head value aggregation, output projection, residual connection, and layer normalization.

### 3.4 Feed-Forward Block

After the stack of causal attention layers, STACD applies:

$$
Z'=\mathrm{LayerNorm}(Z+\mathrm{FFN}(Z)).
$$

### 3.5 Causal Regularization

The sparsity loss is:

$$
\mathcal{L}_{sparse}
=
\lambda_{sparse}\sum_{a,b}|A_{ab}|.
$$

The DAG penalty follows NOTEARS, using a truncated matrix-exponential series in code:

$$
h(A)=\mathrm{tr}(\exp(A\odot A))-K,
$$

$$
\mathcal{L}_{dag}
=
\lambda_{dag}h(A)^2.
$$

Total regularization:

$$
\mathcal{L}_{reg}
=
\mathcal{L}_{sparse}+\mathcal{L}_{dag}.
$$

---

## 4. Phase 3: Causal Propagation and Prediction

Implemented in `causal_propagation.py`.

### 4.1 Impact Initialization

For an event type $k$, representation $u$, and magnitude $m$, `ImpactInitializer` computes:

$$
r_0
=
\tanh
\left(
W_2\,\mathrm{LayerNorm}
\left(
\mathrm{GELU}(W_1[E(k)\Vert u\Vert m])
\right)
\right).
$$

The output dimension is `impact_dim`, default 64.

Implementation note: `ImpactInitializer` defaults to `text_emb_dim=768`. The current `CausalStock.forward()` passes the final STACD representation, which is 256-dimensional by default. Therefore, the wrapper needs a dimension-alignment fix before end-to-end execution.

### 4.2 Neural ODE Event Propagation

Let:

$$
H(t)\in\mathbb{R}^{K\times d_r}
$$

be event-type impact states.

The lag gate is:

$$
G(t)=\sigma(5(t\mathbf{1}-T)).
$$

The time-gated adjacency is:

$$
\tilde{A}(t)=A\odot G(t).
$$

Neighbor aggregation:

$$
\mathrm{Agg}(t)=\tilde{A}(t)^\top H(t).
$$

The ODE function is:

$$
\frac{dH(t)}{dt}
=
f_\theta([H(t)\Vert \mathrm{Agg}(t)\Vert t])
-
\mathrm{softplus}(\delta)\odot H(t),
$$

where $\delta\in\mathbb{R}^{K}$ is a learnable decay parameter.

### 4.3 ODE Solver

The default path is:

$$
H(t_1),\ldots,H(t_S)
=
\mathrm{odeint}(f_\theta,H(0),[t_1,\ldots,t_S]).
$$

The code uses:

```python
odeint(..., method="dopri5", rtol=1e-3, atol=1e-4)
```

If `torchdiffeq` is unavailable, it falls back to fixed-step Euler:

$$
H_{n+1}=H_n+\Delta t\,f_\theta(t_n,H_n).
$$

### 4.4 Event-to-Stock Mapping

The learnable event-stock affinity is:

$$
W_{es}=\sigma(B)\in(0,1)^{K\times N}.
$$

With optional binary prior mask $M_{es}$:

$$
\tilde{W}_{es}=W_{es}\odot M_{es}.
$$

Stock impacts:

$$
V=\tilde{W}_{es}^{\top}H_{final}
\in\mathbb{R}^{N\times d_r}.
$$

### 4.5 Stock Graph Propagation

`StockGraphPropagation` is a dense-adjacency, one-layer, GAT-like propagation module.

First transform stock impacts:

$$
\bar{v}_i=Wv_i.
$$

For each attention head:

$$
e_{ij}^{(h)}
=
\mathrm{LeakyReLU}
\left(
a_{src}^{(h)\top}\bar{v}_i^{(h)}
+
a_{dst}^{(h)\top}\bar{v}_j^{(h)}
\right).
$$

The stock adjacency masks invalid neighbors:

$$
\alpha_{ij}^{(h)}
=
\mathrm{softmax}_{j:A_{ij}^{stock}=1}
(e_{ij}^{(h)}).
$$

Neighbor signal:

$$
n_i=\mathrm{concat}_h\sum_j\alpha_{ij}^{(h)}\bar{v}_j^{(h)}.
$$

Gate and residual update:

$$
\gamma_i=\sigma(W_g[v_i\Vert n_i]),
\qquad
\tilde{v}_i=v_i+\gamma_i\odot n_i.
$$

### 4.6 Multi-Signal Aggregation

The stock/event impact matrix is attention pooled:

$$
\alpha_i
=
\mathrm{softmax}_i
\left(
w^\top\tanh(W_av_i)
\right),
$$

$$
r=\sum_i\alpha_i v_i.
$$

Price history is encoded by a two-layer GRU over OHLCV input:

$$
p_{1:T}=\mathrm{GRU}(\mathrm{OHLCV}_{1:T}),
\qquad p=p_T.
$$

Fusion:

$$
z=\mathrm{MLP}([r\Vert p]).
$$

### 4.7 Prediction Head

Direction logits and magnitude:

$$
\hat{y}^{dir}=W_dz,\qquad
\hat{y}^{mag}=W_mz.
$$

A standard supervised prediction objective would be:

$$
\mathcal{L}_{pred}
=
\mathrm{CE}(\hat{y}^{dir},y^{dir})
+
\beta\,\mathrm{MSE}(\hat{y}^{mag},y^{mag}).
$$

If jointly trained with STACD regularization:

$$
\mathcal{L}_{total}
=
\mathcal{L}_{pred}
+
\lambda_{sparse}\|A\|_1
+
\lambda_{dag}h(A)^2.
$$

---

## 5. GroundedStock

GroundedStock is implemented in `pipeline.py` and related modules. It is not the same computation graph as CausalStock. It uses retrieval, LLM reasoning, and verification.

### 5.1 Knowledge Base

The Financial Knowledge Base contains:

$$
\mathcal{K}
=
\mathcal{K}_{news}
\cup
\mathcal{K}_{event}
\cup
\mathcal{K}_{macro}
\cup
\mathcal{K}_{fund}.
$$

`news_semantic` uses:

- dense FinBERT embeddings
- FAISS inner-product search on L2-normalized vectors
- BM25 sparse retrieval

The dense similarity for query $q$ and document $d$ is:

$$
\mathrm{sim}_{dense}(q,d)
=
\frac{e_q^\top e_d}{\|e_q\|\|e_d\|}.
$$

### 5.2 Hybrid Retrieval with Reciprocal Rank Fusion

For semantic retrieval, dense and sparse ranks are fused as:

$$
\mathrm{RRF}(d)
=
\frac{1}{k+r_{dense}(d)}
+
\frac{1}{k+r_{sparse}(d)}.
$$

The implementation uses `rrf_k=60` by default.

### 5.3 Four Retrieval Paths

For a news item $(q,s,t)$, the retriever returns evidence from:

1. semantic historical news:

$$
\mathcal{E}_1=\mathrm{HybridSearch}(q,t)
$$

2. same-event historical outcomes:

$$
\mathcal{E}_2=\{e: e.event\_type=\hat{k}(q),\ e.ticker\in\{s,\mathrm{ALL}\},\ e.time<t\}
$$

3. macro context:

$$
\mathcal{E}_3=\mathrm{MacroSnapshot}(t)\cup\mathrm{RecentMacroEvents}(t-7,t)
$$

4. fundamentals:

$$
\mathcal{E}_4=\mathrm{FundamentalSnapshot}(s,t)
$$

The event type in retrieval is currently keyword-based, not the trained Phase 1 FinBERT extractor.

### 5.4 Evidence Ranking

Each evidence item receives:

$$
\mathrm{score}(e)
=
0.5\,R(e)+0.3\,C(e,t)+0.2\,I(e),
$$

where:

- $R(e)$ is retrieval relevance
- $C(e,t)$ is recency score
- $I(e)$ is informativeness

The recency score is:

$$
C(e,t)
=
\exp\left(
-0.693\frac{\Delta days(e,t)}{20}
\right).
$$

Informativeness is 1.0 when the evidence contains a numerical outcome, otherwise 0.6.

Near-duplicate evidence items are removed by Jaccard overlap over word sets.

### 5.5 Evidence-Anchored CoT Reasoning

The reasoner maps:

$$
(q,\mathcal{E})\rightarrow
\{\mathrm{steps},\hat{y}^{dir},c,\mathrm{primary\_evidence},\mathrm{risks}\}.
$$

The output must be valid JSON and each reasoning step is expected to cite evidence IDs:

$$
\mathrm{step}_j=(\mathrm{text}_j,\mathrm{citations}_j,\mathrm{signal}_j,c_j).
$$

Citation coverage is:

$$
\mathrm{coverage}
=
\frac{
|\{E_i:E_i\ \text{is cited in any step}\}|
}{
|\mathcal{E}|
}.
$$

If citation coverage is below 0.5, the reasoner reruns at temperature 0 unless parsing already failed.

### 5.6 Faithfulness Verification

For each step $j$, the verifier computes:

1. citation validity:

$$
S^{cite}_j
=
\frac{
|\mathrm{citations}_j\cap \mathrm{validEvidenceIds}|
}{
|\mathrm{citations}_j|
}.
$$

If no valid citation exists, the step score is 0.

2. factual entailment:

The step text is decomposed into atomic claims $\{c_{j,l}\}$, then each claim is compared against concatenated cited evidence:

$$
S^{fact}_j
=
\frac{1}{L_j}
\sum_{l=1}^{L_j}
P_{\mathrm{NLI}}(\mathrm{entailment}\mid E_j,c_{j,l}).
$$

If the NLI model cannot load, code falls back to keyword-overlap scoring.

3. numerical consistency:

Numbers in the step are matched to numbers in cited evidence with 5 percent relative tolerance:

$$
S^{num}_j
=
\frac{
\#\{\text{matched step numbers}\}
}{
\#\{\text{step numbers}\}
}.
$$

If the step has no numbers, $S^{num}_j=1$.

Composite step score:

$$
S_j=0.6S^{fact}_j+0.4S^{num}_j.
$$

Overall faithfulness verification score:

$$
\mathrm{FV}
=
\frac{1}{m}\sum_{j=1}^{m}S_j.
$$

The pipeline marks a result trustworthy only when:

$$
\mathrm{FV}\ge \tau_{trust}
\quad\text{and}\quad
\text{no step is below the hallucination threshold}.
$$

Default thresholds in `pipeline.py` are:

$$
\tau_{trust}=0.5,\quad
\tau_{confidence}=0.55.
$$

### 5.7 Calibrated Confidence

The final `PredictionResult` stores:

$$
\mathrm{calibrated\_conf}
=
c_{LLM}\cdot \mathrm{FV}.
$$

The slow path is triggered when:

$$
\mathrm{FV}<0.5
\quad\text{or}\quad
c_{LLM}<0.55
\quad\text{or}\quad
\mathrm{parse\_failed}
\quad\text{or}\quad
\mathrm{citation\_coverage}<0.5.
$$

---

## 6. Current Implementation Notes

- `CausalStock` Phase 1, Phase 2, and Phase 3 modules are implemented, but the wrapper in `CausalStock.forward()` has a default dimension mismatch between STACD output (`d_model=256`) and `ImpactInitializer` input (`text_emb_dim=768`).
- `GroundedStock` is a separate inference pipeline and expects a `configs/groundedstock.yaml` file, which is referenced by code but not present in the current folder.
- Retrieval event typing is currently keyword-based; it does not call the trained Phase 1 extractor.
- The Phase 1 magnitude loss in code is Smooth L1, even though older notes may describe MSE.
- `torchdiffeq` gives the default ODE solver; Euler is only the fallback path.
