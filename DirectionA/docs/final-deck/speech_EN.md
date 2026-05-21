# CausalStock — Presentation Script (English)

For `CausalStock_CS173_Final_EN.pptx` (23 slides). ~16–18 min.
Report-aligned: no ODE, no 0.709 ensemble — present the stratified 0.693 /
chronological 0.337 story honestly. The method section now gives each of the
three phases its own detailed treatment (Phase 1 ×2, Phase 2 ×2, Phase 3 ×3).

---

### Slide 1 — Title
Good morning. We are Team 2, and our project is **CausalStock** —
event-structured temporal causal modeling for news-driven stock prediction.
In one line: a data-driven, structured, and honestly-evaluated framework for
predicting stock movement from financial news.

### Slide 2 — Agenda
Five parts: the problem and the baseline; an exploratory data analysis that
drives our design; the method — where we walk through each of the three phases
in detail; the experiments; and a multi-axis comparison with the baseline
before we conclude.

### Slide 3 — What Prior Methods Get Wrong
Most news-driven models compress an article into a single sentiment score, and
three things break. One — information loss: a scalar discards the event's
type, magnitude, and the entity it hit. Two — lack of causality: the model
sees surface correlation, not the logic linking events, and cannot explain its
prediction. Three — ignoring temporal dynamics: a news impact is treated as
instantaneous, missing lag and gradual diffusion. These three gaps define what
we set out to fix.

### Slide 4 — Baseline: CausalStock (NeurIPS 2024)
Our baseline is the NeurIPS 2024 CausalStock. It does two things: an LLM
compresses each article into one dense embedding, and it learns a causal graph
between individual stocks. That leaves two blind spots. One — a single vector
per article hides what type of event occurred, how large it was, and which
entity it hit. Two — a stock-level graph can say stock A leads stock B, but
not what kind of event drove that link. Our two design changes target exactly
these gaps: we restore event structure, and we move causality to the
transferable event-type level.

### Slide 5 — What We Change: Three Innovations
Each problem maps to one design change. Information loss → we extract a
**structured event**: subject, action, object, magnitude, plus an impact
profile. Lack of causality → **lag-aware causal discovery over 20 event
types**. Ignoring time → we learn an explicit **lag matrix** and gate
attention by it. Two principles run through all three: data-driven — the
schema is earned from a measured EDA, not assumed; and honest — every result
is reported on both a stratified and a chronological split.

### Slide 6 — End-to-End Pipeline
Here is the whole pipeline. News text enters Phase 1, structured event
extraction. Phase 2 learns the lag-aware event-type graph. Phase 3 assembles
price, event, and stock features and predicts the next-day movement with a
transparent tabular model. The rest of the talk walks through each stage.

### Slide 7 — EDA (1/4): Dataset Snapshot & Field Completeness
We start from the data. The 5% FNSPID subset yields 10,901 structured events
and 9,566 ticker-aligned examples over 22 stocks. The field-completeness audit
is revealing: the URL is present for essentially every article, but publisher
and author are missing 79% and 68% of the time — too sparse to supervise on,
so credibility instead comes from the URL domain. And 29% of headlines are
duplicates, which motivates a novelty attribute.

### Slide 8 — EDA (2/4): Event-Clue Density
Why extract events at all? Because the corpus is event-dense: 88% of articles
carry explicit price-movement language, 77% a numeric comparison, 56% concern
earnings. This is not a stream of diffuse opinion — it is a stream of
discrete, typable events with quantitative arguments. That density is our
empirical justification for structured event extraction over sentiment
scoring.

### Slide 9 — EDA (3/4): Data Findings Drive the Schema
This is the core of our data-driven design. Three measured properties, three
event attributes. 29% duplicate headlines → a **novelty** attribute that
down-weights repeats. Missing provenance → a **credibility** attribute from
the URL domain. 89% multi-scope news → a **scope** attribute that localizes
the impact. These attributes are earned from the data, not assumed.

### Slide 10 — EDA (4/4): Event Distribution & Attribute Coverage
Two properties of the extracted stream shape the modeling. The event-type
distribution is long-tailed — the top three types are 55% of all events, so
training must be class-aware. On coverage: polarity, scope, novelty, and
credibility are dense, around 85%, and used as standard attributes; surprise
is sparse, only 6.6%, treated as a high-value indicator. A manual audit of 50
samples found 84% event-type, 78% action, and 91% polarity agreement.

### Slide 11 — Phase 1 (1/2): The Structured Event Schema
Now the method, starting with Phase 1. Phase 1 turns each free-text article
into one structured event record, and the record has two parts. First, an
**event core** — a quadruple: a type drawn from a 20-class ontology, a subject
that acts, an action, an object that is affected, and a signed magnitude. The
20 classes group into four families — macro, corporate, knowledge, and
geopolitics. Second, an **impact profile** — five attributes on every event:
polarity, surprise, and the three EDA-driven ones, scope, novelty, and
credibility. Where are they used? The profile becomes Phase-3 event features
and weights events in the Phase-2 causal aggregation.

### Slide 12 — Phase 1 (2/2): Extraction Model & Weak Supervision
How do we extract that record? A FinBERT encoder — pretrained on financial
text — feeds a multi-head decoder: head one classifies the event type, head
two extracts the subject and object spans, head three regresses the magnitude.
The heads share the encoder and train jointly. The harder problem is labels:
there are no gold labels at scale. So we use a four-step weak-supervision
pipeline — an LLM produces a silver label, a rule layer corrects it with
financial keywords, market data grounds the magnitude against the realized
return, and a final filter removes hallucinations. The result: 10,901
structured events, 20 types, about 85% average attribute coverage, with audit
agreement of 84% on type, 78% on action, 91% on polarity.

### Slide 13 — Phase 2 (1/2): Lag-Aware Causal Discovery (STACD)
Phase 2 is causal discovery. The goal is two 20-by-20 matrices: A, the
directed causal strength — how strongly event type i drives type j — and
T_lag, the expected lag in days between cause and effect. Both are learned
end-to-end from the event stream. The mechanism, STACD, has five components: a
sparse temporal attention over the event sequence; a time-direction mask so
only the past attends to the future; a lag-aware Gaussian gate that peaks when
the observed gap matches the learned lag; a causal-strength gate that
modulates attention by A; and a NOTEARS-style regularizer that keeps the graph
a valid DAG.

### Slide 14 — Phase 2 (2/2): Attention Modulation & Interpretability
Here is how those gates combine. The three gates enter the attention score
additively in log-space: the modulated score is the raw score plus log of the
direction mask, plus log of the lag gate, plus log of the causal strength A.
A softmax over that gives the attention weights, and the loss adds an
L1 sparsity term and the acyclicity penalty. The key design point is on the
bottom: the nodes are event types, not individual stocks. A 20-node event-type
graph stays the same across companies and markets, so it is designed to
support interpretable, transferable event-chain analysis — a stock-level graph
is bound to a fixed company universe.

### Slide 15 — Phase 3 (1/3): Problem Setup & Dataset
Phase 3 predicts. For each example the input is 32 recent events, a 30-day
OHLCV window, and the stock identity. The output is the next-day direction
with a half-percent threshold — up, down, or flat. The classes are imbalanced;
FLAT is the minority at 17%, so we emphasize macro-F1. The study covers 9,566
examples over 22 stocks, 2010 to 2023.

### Slide 16 — Phase 3 (2/3): Feature Engineering
We flatten everything into one 132-dimensional vector with three blocks. The
**price block, 28 dimensions** — multi-horizon returns over 1, 5, 10, 20 days,
realized volatility, log-volume, OHLC ratios, and short-term momentum. The
**event block, 82 dimensions** — per-type event counts, signed and absolute
magnitude sums, the means of the five impact-profile attributes, and the
last-event type one-hot. The **stock block, 22 dimensions** — a one-hot ticker
identity. Crucially, every feature is an aggregate over the 32-event,
30-day window — strictly past information, no look-ahead.

### Slide 17 — Phase 3 (3/3): Model — HistGradientBoosting
The classifier over that 132-d vector is histogram gradient boosting. Why not
a neural net? Because the features are heterogeneous — counts, ratios,
one-hots; HGB handles them natively, its tree splits are scale-invariant so
feature engineering is minimal, it is a strong and interpretable baseline that
lets us read each source's contribution, and it is robust on a 9,566-example
dataset without needing big data. Configuration: 150 iterations, learning rate
0.04, L2 0.05, early stopping; a three-class softmax output; macro-F1 as the
headline metric; and we evaluate under both a stratified and a chronological
split.

### Slide 18 — Key Result: Stratified vs Chronological
This is our key result. Under a stratified random split, macro-F1 is 0.693 and
accuracy 0.728 — well above the 0.43 majority-class and 0.33 random baselines:
the features carry usable signal. But a random split on time-series data mixes
market regimes across train and test. So we also run a chronological split,
and there macro-F1 falls to 0.337 — near random, consistent with semi-strong
market efficiency. We report both deliberately; reporting only the stratified
number would overstate real-world predictive power.

### Slide 19 — Ablation: Feature-Group Contribution
The ablation shows where performance comes from. Price plus event features
reach 0.684; adding stock identity lifts it to 0.693 — ticker-specific
volatility and reaction patterns remain useful even after price and event
statistics. The combined representation is what we report, and it is learnable
under a stratified split.

### Slide 20 — Comparison with the Baseline: Multi-Axis
Now a structured comparison with the NeurIPS 2024 CausalStock. They model
causality between individual stocks; we model it between event types —
transferable across companies. They use a dense embedding; we use a structured
event. They predict binary up/down; we predict three classes with a flat zone.
They mostly use a random split; we report stratified and chronological. And
their data is larger and multi-dataset; ours is a 5% FNSPID subset. The two
formulations are complementary, not competing.

### Slide 21 — Comparison: An Interpretable Reading of the Gap
We are honest that our setup is harder and stricter, and the gap is
explainable along four axes. Task — we predict three classes with a FLAT dead
zone; the baseline is binary, an easier target. Data — a 5% subset over 22
stocks; at that scale cross-stock relational signal is limited. Protocol — our
directly comparable number is the chronological one; a random split inflates
apparent performance. Method — the baseline couples news with a price-derived
causal backbone end-to-end, while our evaluated layer is a transparent tabular
model over aggregated event statistics — interpretable but lossier. We do not
claim to beat the baseline; we contribute a transferable formulation and a
stricter, honest evaluation.

### Slide 22 — Conclusion & Future Work
To conclude. We contribute a clearer event-structured problem formulation; an
EDA-driven event schema whose attributes are earned from data; a
mathematically specified lag-aware event-causal model; and an honest analysis
that separates in-distribution information content from forward-time
predictability. Future work: integrate the causal matrix directly into the
predictor, model cross-stock propagation, and adopt rolling walk-forward
validation. We do not claim solved stock prediction — we claim a clean
formulation and an honest study.

### Slide 23 — Q&A
Thank you — we are happy to take questions.

---

## Anticipated Q&A

**Q: How do the three stages connect — does the Phase-2 graph feed Phase 3?**
The evaluated predictor uses price, event-statistics, and stock-identity
features. The Phase-2 matrices A and T_lag are an interpretability product;
integrating them directly as Phase-3 features is stated future work.

**Q: Why 0.693 stratified but 0.337 chronological?**
A random split on time series leaks — adjacent days of the same stock land in
both train and test. The chronological number is the honest one; 0.337 ≈
random reflects semi-strong market efficiency. We report both on purpose.

**Q: Does the 0.693 come from news or from price?**
Feature importance shows price-history features dominate; event features add a
smaller increment. The in-distribution score is largely a price signal — we
say so explicitly.

**Q: Is the causal graph real causality?**
We use "causal" in a predictive-temporal sense — directed, time-ordered
dependence under sparsity and a DAG constraint — not intervention-level
causality. Unobserved macro variables can confound.

**Q: Are the LLM silver labels reliable?**
We inject rule- and market-grounded anchors before each LLM call to suppress
hallucination; a manual audit of 50 samples found 84% event-type, 78% action,
and 91% polarity agreement.

**Q: Why only 22 stocks / a 5% subset?**
Annotation and compute budget for a course project; the small scale is a
stated limitation and bounds the cross-stock and high-capacity components.

**Q: What exactly are the three decoder heads in Phase 1?**
Head one is a 20-way softmax for the event type; head two extracts the subject
and object token spans; head three regresses the signed magnitude. All three
sit on a shared FinBERT encoder and are trained jointly.

**Q: Why does the data flow through 32 events and a 30-day window?**
Each Phase-3 example aggregates the 32 most recent events and the last 30
trading days of OHLCV for the target stock. Both windows look strictly
backward from the prediction date, so there is no look-ahead leakage.
