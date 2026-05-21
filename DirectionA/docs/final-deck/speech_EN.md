# CausalStock — Presentation Script (English)

For `CausalStock_CS173_Final_EN.pptx` (17 slides). ~13–15 min.
Report-aligned: no ODE, no 0.709 ensemble — present the stratified 0.693 /
chronological 0.337 story honestly.

---

### Slide 1 — Title
Good morning. We are Team 2, and our project is **CausalStock** —
event-structured temporal causal modeling for news-driven stock prediction.
In one line: a data-driven, structured, and honestly-evaluated framework for
predicting stock movement from financial news.

### Slide 2 — Agenda
Four parts: the problem and our innovations; the framework and the data
analysis behind it; the three-stage method; and the experiments, with an
honest read of the results.

### Slide 3 — What Prior Methods Get Wrong
Most news-driven models compress an article into a single sentiment score, and
three things break. One — information loss: a scalar discards the event's
type, magnitude, and the entity it hit. Two — lack of causality: the model
sees surface correlation, not the logic linking events, and cannot explain its
prediction. Three — ignoring temporal dynamics: a news impact is treated as
instantaneous, missing lag and gradual diffusion. These three gaps define what
we set out to fix.

### Slide 4 — What We Change: Three Innovations
Each problem maps to one design change. Information loss → we extract a
**structured event**: subject, action, object, magnitude, plus an impact
profile. Lack of causality → **lag-aware causal discovery over 20 event
types** — a graph that transfers across companies. Ignoring time → we learn an
explicit **lag matrix** and gate attention by it. Two principles run through
all three: data-driven — the schema is earned from a measured EDA, not
assumed; and honest — every result is reported on both a stratified and a
chronological split.

### Slide 5 — End-to-End Pipeline
Here is the whole pipeline. News text enters Phase 1, structured event
extraction. Phase 2 learns the lag-aware event-type graph. Phase 3 assembles
price, event, and stock features and predicts the next-day movement with a
transparent tabular model. The rest of the talk walks through each stage.

### Slide 6 — EDA: Missingness, Duplication, Event Density
We start from data. We profiled the raw FNSPID subset. On the left — field
completeness: the URL is present for essentially every article, but publisher
and author are missing 79% and 68% of the time. So we cannot supervise on
publisher; instead we derive a credibility signal from the URL domain. On the
right — the corpus is event-dense: 88% of articles use explicit price-movement
language and 77% a numeric comparison. That density is the empirical
justification for extracting structured events rather than scoring sentiment.

### Slide 7 — EDA: Data Findings Drive the Schema
This is the core of our data-driven design. Three measured properties, three
event attributes. 29% duplicate headlines → a **novelty** attribute that
down-weights repeats. Missing provenance → a **credibility** attribute from
the URL domain. 89% multi-scope news → a **scope** attribute that localizes
the impact. The point is: these attributes are earned from the data, not
assumed in advance.

### Slide 8 — Phase 1: Structured Event Extraction
Phase 1 turns each article into a structured event — a type, a
subject-action-object-magnitude quadruple, and the impact profile. A FinBERT
encoder feeds a multi-head decoder: event-type classification, argument spans,
and magnitude. Because there are no gold labels at scale, we use LLM silver
labels with rule- and market-grounded corrections to suppress hallucination.
The result: 10,901 structured events, 20 types, about 85% average attribute
coverage.

### Slide 9 — Event Stream: Distribution & Coverage
Two properties of the extracted stream shape the modeling. On the left, the
event-type distribution is long-tailed — the top three types are 55% of all
events, so training must be class-aware. On the right, attribute coverage:
polarity, scope, novelty, and credibility are dense, around 85%, so we use
them as standard attributes; surprise is sparse — only 6.6% — so we treat it
as a sparse, high-value indicator rather than a universal feature.

### Slide 10 — Phase 2: Lag-Aware Causal Discovery (STACD)
Phase 2 is causal discovery. We learn two 20-by-20 matrices: A, the directed
strength between event types, and T_lag, the expected lag in days. The
mechanism is sparse temporal attention — a time-direction mask so only the
past attends to the future, a lag-aware Gaussian gate, and a causal-strength
gate, with a NOTEARS-style acyclicity regularizer. Crucially, the nodes are
event types, not stocks, so the graph is designed to be interpretable and
transferable across companies.

### Slide 11 — Phase 3: Problem Setup & Dataset
Phase 3 predicts. For each example the input is 32 recent events, a 30-day
OHLCV window, and the stock identity. The output is the next-day direction
with a half-percent threshold — up, down, or flat. The classes are imbalanced;
FLAT is the minority, so we emphasize macro-F1. The study covers 9,566
examples over 22 stocks, 2010 to 2023.

### Slide 12 — Phase 3: Feature Engineering & Model
We flatten everything into one 132-dimensional vector — 28 price dimensions,
82 event dimensions, and 22 for stock identity. The classifier is histogram
gradient boosting. Why not a neural net? Because the features are
heterogeneous — counts, ratios, one-hots; HGB handles them natively, is
scale-invariant, and gives a strong, interpretable baseline that lets us read
each information source's contribution.

### Slide 13 — Key Result: Stratified vs Chronological
This is our key result. Under a stratified random split, macro-F1 is 0.693 and
accuracy 0.728 — well above the 0.43 majority-class and 0.33 random baselines:
the features carry usable signal. But a random split on time-series data mixes
market regimes across train and test. So we also run a chronological split,
and there macro-F1 falls to 0.337 — near random, consistent with semi-strong
market efficiency. We report both deliberately; reporting only the stratified
number would overstate real-world predictive power.

### Slide 14 — Ablation: Feature-Group Contribution
The ablation shows where performance comes from. Price plus event features
reach 0.684; adding stock identity lifts it to 0.693 — ticker-specific
volatility and reaction patterns remain useful even after price and event
statistics. The combined representation is what we report, and it is learnable
under a stratified split.

### Slide 15 — Comparison with the NeurIPS 2024 CausalStock
How does this relate to the NeurIPS 2024 CausalStock? They model causality
between individual stocks; we model it between event types — transferable
across companies, not bound to a fixed universe. They use a dense embedding;
we use a structured event. They predict binary up/down; we predict three
classes with a flat zone. And we evaluate on a stricter, dual-split protocol.
The two formulations are complementary, not competing.

### Slide 16 — Conclusion & Future Work
To conclude. We contribute a clearer event-structured problem formulation; an
EDA-driven event schema whose attributes are earned from data; a
mathematically specified lag-aware event-causal model; and an honest analysis
that separates in-distribution information content from forward-time
predictability. Future work: integrate the causal matrix directly into the
predictor, model cross-stock propagation, and adopt rolling walk-forward
validation. We do not claim solved stock prediction — we claim a clean
formulation and an honest study of where structured news helps.

### Slide 17 — Q&A
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
smaller increment. We are explicit that the in-distribution score is largely a
price signal.

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
stated limitation and bounds the high-capacity modules.
