# CausalStock Deck — English Slide Copy

Drop-in English text for the existing 16-slide deck. Layout / style / images
unchanged — only swap the text. `[CHANGE]` marks content that must change for
consistency with the final report; `[FIX]` marks small corrections.
Two extra slides are proposed at the end.

---

## Slide 1 — Title
**Title:** CausalStock
**Subtitle:** Event-Structured Temporal Causal Modeling for News-Driven Stock Prediction
**Footer:** Team 2 · CS173 Data Mining · Final
**Speak:** "Good morning. We are Team 2. Our project is CausalStock — a
data-driven, interpretable framework for predicting stock movement from
financial news."

## Slide 2 — Agenda
- 01 Introduction & Problem — limitations of prior methods, and our design
- 02 Framework Recap — Phase 1 (event extraction), Phase 2 (causal discovery)
- 03 Phase 3 In Depth — the prediction module: design, experiments, findings
- 04 Conclusion & Future Work
**Speak:** "Five minutes of setup, then we go deep on Phase 3 and an honest
read of the results."

## Slide 3 — Three Limitations of Prior Methods
**Title:** Introduction — Three Limitations of Prior Methods
- **Information Loss.** Compressing an article into one sentiment score
  discards the event's subject, action, object, and magnitude.
  *e.g.* "Apple launches a new iPhone, sales outlook raised 20%" → sentiment +0.8
- **Lack of Causality.** Models capture surface correlation, not the logic
  between events, and cannot explain a prediction. *e.g.* they cannot tell
  whether a rate hike moves prices directly or via lowered earnings expectations.
- **Ignoring Temporal Dynamics.** Treating a news impact as instantaneous
  misses lag, diffusion, and gradual effects. *e.g.* a policy change may surface
  in prices only over the following days or weeks.
**Speak:** "Most news models compress an article into a sentiment score — that
throws away three things event-driven markets depend on: what happened, to
whom, and when the effect arrives."

## Slide 4 — Three Core Ideas  `[CHANGE]`
**Title:** Introduction — Three Core Ideas of CausalStock
*(Replace the old three; drop "Neural-ODE causal propagation" — it is not in
the report.)*
- **EDA-driven event schema.** We profile the raw corpus first; three measured
  findings — ~29% duplicate headlines, 68–79% missing provenance, ~89%
  multi-scope news — directly motivate three event attributes: novelty,
  credibility, scope.
- **Lag-aware event-type causal discovery (STACD).** We learn directed
  strength A and lag T_lag between 20 event *types* — causality at the
  event-type level, transferable across companies rather than bound to a fixed
  stock universe.
- **Interpretable prediction, honestly evaluated.** A transparent tabular
  model, reported under both stratified and chronological splits.
**Speak:** "Our core principle is data-driven design — every schema choice is
earned from a measured property of the data, not assumed in advance."

## Slide 5 — End-to-End Pipeline  `[FIX]`
**Title:** Introduction — End-to-End Pipeline
- **Raw News Text** — unstructured financial news input.
- **Phase 1: Structured Event Extraction** — extract financial event quadruples.
- **Phase 2: Lag-Aware Causal Discovery** — learn strength matrix A and lag
  matrix T_lag over event types.
- **Phase 3: Tabular Stock-Movement Prediction** — combine price, event, and
  stock features; predict next-day direction with a gradient-boosting model.
  *(was "Causal Propagation & Prediction" — change to tabular prediction.)*
**Speak:** "Three stages: extract structured events, learn lag-aware
event-type structure, and predict with a transparent tabular model."

## Slide 6 — Phase 1: Structured Event Extraction
**Title:** Framework Recap — Phase 1: Structured Event Extraction
- **Core goal.** Turn unstructured news into a structured tuple
  e\_i = (k\_i, S\_i, O\_i, M\_i): k\_i event type (20 classes), S\_i subject,
  O\_i object, M\_i magnitude (positive / negative / neutral).
- **FinBERT + multi-head decoder.** Encoder: ProsusAI/finbert for
  financial-text features. Decoder: three parallel heads — event-type
  classification, argument-span extraction, magnitude estimation.
- **20-class taxonomy.** Macro (rates, economic data, trade, FX…), Corporate
  (earnings, M&A, executive change, launches…), Knowledge (analyst ratings,
  insider trading, IP…), Geopolitical (conflict, sanctions, disasters…).
**Speak:** "Phase 1 turns each article into a typed, structured event with a
FinBERT multi-head extractor."

## Slide 7 — Phase 2: Lag-Aware Causal Discovery (STACD)
**Title:** Framework Recap — Phase 2: Lag-Aware Causal Discovery (STACD)
- **Goal — two matrices.** A: directed causal strength between event types.
  T_lag: expected lag, in days, from cause to effect.
- **Mechanism — Sparse Temporal Attention for Causal Discovery.** A
  time-direction mask prevents reversed causality; a lag-aware Gaussian gate
  and a causal-strength gate capture time-varying, non-linear dependencies.
- **Structural constraint.** A NOTEARS-style regularizer keeps the learned
  graph a directed acyclic graph, ruling out illogical cyclic causality.
**Speak:** "Phase 2 attempts to learn causal structure between event types
with sparse, lag-aware attention under a DAG constraint."

## Slide 8 — Reading the Causal Graph  `[CHANGE]`
**Title:** Framework Recap — Reading the Causal Graph *(Illustrative)*
*(The old slide presented specific edge values as discovered results. Per the
report, the graph is a design product, not a validated result — relabel as an
illustrative schematic, or cut the slide.)*
- Label the matrix clearly: **"Illustrative example — schematic, not measured
  output."**
- **How to read it.** Entry A[a,b] is the directed strength from event type a
  to b; T_lag[a,b] is the expected delay. The framework is designed to surface
  readable chains such as rate → earnings → analyst rating.
**Speak:** "This is an illustrative schematic of how the graph is meant to be
read — A gives directed strength, T_lag the delay. We treat the learned graph
as an interpretability tool by design, not as a validated causal claim."
*(Alternative: remove this slide entirely.)*

## Slide 9 — Phase 3: Problem Setup & Dataset
**Title:** Phase 3 — Problem Setup & Dataset
- **Positioning.** Combine the Phase 1–2 outputs with price history; through
  feature engineering, produce a classification of next-day movement.
- **Inputs.** 32 recent news events; a 30-day OHLCV window; target stock ID.
- **Output (3-class).** UP > +0.5% (39.4%) · DOWN < −0.5% (43.3%) · FLAT (17.3%).
- **Dataset.** 9,566 examples · 22 stocks · 2010–2023.
**Speak:** "Phase 3 predicts next-day direction in three classes from 32 events
and 30 days of prices."

## Slide 10 — Feature Engineering & Model Choice  `[FIX]`
**Title:** Phase 3 — Feature Engineering & Model Choice
- **Design.** Flatten all heterogeneous information into a single
  132-dimensional feature vector for a strong tabular model.
- **Model — HistGradientBoosting (HGB).** Why HGB over a neural net: handles
  heterogeneous features (counts, ratios, one-hots); a strong, interpretable
  baseline that quantifies each source's contribution; scale-invariant.
- x\_i = [x\_price ‖ x\_event ‖ x\_stock] — **Price 28-d · Event 82-d · Stock 22-d**.
  *(was 31 / 79 — correct to 28 / 82 to match the code, or just say "132-d".)*
**Speak:** "Phase 3 is deliberately a transparent tabular model, so we can read
which information source actually helps."

## Slide 11 — Feature Engineering Detail (1/2)  `[FIX]`
**Title:** Phase 3 — Feature Engineering Detail (1/2)
- **Price features (28-d).** Daily returns (10); return statistics — mean, std,
  5-day mean/std (4); log-volume statistics (2); relative OHLC summaries (12).
  *(was relative OHLCV 15-d — correct to 12.)*
- **Event features (82-d).** Per-type counts (20); signed magnitude sums (20);
  absolute magnitude sums (20); last-event one-hot (20); global magnitude
  statistics (2). *(was 79 — correct to 82.)*
**Speak:** "Price features capture trend and volatility; event features
summarize the recent news stream by type and magnitude."

## Slide 12 — Feature Engineering Detail (2/2)  `[FIX]`
**Title:** Phase 3 — Feature Engineering Detail (2/2)
- **Stock identity (22-d).** One-hot over the 22 target stocks; lets the model
  learn ticker-specific volatility and reaction bias — the same "earnings beat"
  moves a growth stock and a bank differently.
- **Model configuration.** HistGradientBoostingClassifier; max_iter 150,
  learning_rate 0.04, l2_regularization 0.05.
- **Current limitation.** The Phase-2 STACD outputs — strength matrix A and lag
  matrix T_lag — are not yet integrated as Phase-3 input features; this is a
  key direction for future work. *(was "Granger causal analysis" — correct to
  STACD, matching Slide 7.)*
**Speak:** "One honest limitation: the Phase-2 graph is not yet wired into the
Phase-3 features."

## Slide 13 — Key Result: Stratified vs Chronological
**Title:** Phase 3 — Key Result: Stratified vs Chronological Split
- **Stratified Random.** Macro-F1 0.6929 · Accuracy 0.7281 — the features carry
  usable, non-random signal in-distribution.
- **Chronological.** Macro-F1 0.3366 · Accuracy 0.3969 — forward-time
  predictive ability; near the random baseline, consistent with semi-strong
  market efficiency.
- **Takeaway.** 0.69 is well above the 0.43 majority-class and 0.33 random
  baselines. We deliberately report both splits — reporting only the stratified
  number would overstate real-world predictive power.
**Speak:** "In-distribution we reach 0.69, clearly above the majority and
random baselines. Forward-time it falls to 0.34 — near random, as semi-strong
market efficiency predicts. Reporting both is the honest standard, and that
honesty is part of our contribution."

## Slide 14 — Ablation  `[CHANGE]`
**Title:** Phase 3 — Ablation: Where Does Performance Come From?
*(Remove the old "price-only 0.705" and "events-only 0.529" rows — those are
not in the report. Use the report rows; add real price-only / events-only
numbers once the running ablation finishes.)*
| Feature set | Dim. | Macro-F1 (stratified) |
|---|---|---|
| Price + events | 110 | 0.684 |
| Full: price + events + stock ID | 132 | 0.693 |
| *(price-only / events-only — fill from the current run)* | | |
- **Reading.** Adding stock identity lifts macro-F1 from 0.684 to 0.693; the
  combined representation is learnable under a random split.
**Speak:** "Each information source contributes; the combined price-event-stock
model is what we report. The remaining rows come from the ablation we are
running now."

## Slide 15 — Conclusion & Future Work  `[CHANGE]`
**Title:** Conclusion & Future Work
- **Summary.** CausalStock builds an end-to-end three-stage framework —
  structured event extraction, lag-aware causal discovery, and tabular
  prediction. The contribution is a clearer problem formulation, a
  mathematically specified event-causal model, and an honest analysis that
  separates in-distribution information content from genuine forward-time
  predictability. *(Remove "effectively discovers latent causal structure" and
  "fully validates effectiveness and robustness" — the report does not claim
  this.)*
- **Future work.** Integrate A / T_lag as Phase-3 features; model cross-stock
  propagation; add regime-aware temporal encoding against distribution shift;
  adopt rolling walk-forward validation.
**Speak:** "We do not claim solved stock prediction. We claim a clean
formulation and an honest, end-to-end study of where structured news helps and
where forward-time prediction is still hard."

## Slide 16 — Q&A
**Title:** Q & A — Thank You
**Speak:** "Thank you — we are happy to take questions."

---

## Proposed extra slide A — Exploratory Data Analysis  `[ADD]`
*(Insert after Slide 3, or just before Slide 9. The deck has no dedicated EDA
slide — this is the strongest place to show data-mining depth.)*
**Title:** Exploratory Data Analysis — The Data Drives the Schema
- **Field completeness.** URL present ~100%; Stock_symbol 67%; Author 32%;
  Publisher 21%.
- **Headline duplication.** ~29% of stock-candidate rows repeat an earlier
  headline.
- **Event-clue density.** 88% of articles carry price-movement language, 77% a
  numeric comparison, 56% earnings — the corpus is event-dense.
- **Long-tailed event types.** The top three event types are 55% of all events.
- **Findings → schema.** duplication → novelty; missing provenance →
  credibility; multi-scope news → scope.
**Figures:** `fig_eda_missing.png`, `fig_eda_clues.png`, `fig_event_dist.png`.
**Speak:** "We profiled the raw corpus before fixing the schema. Three measured
properties each motivate one event attribute — the schema is matched to the
data, not assumed."

## Proposed extra slide B — Comparison with the Baseline  `[ADD]`
*(Insert before Slide 15. Fill the numeric column from the comparison run in
progress.)*
**Title:** Comparison with the NeurIPS 2024 CausalStock Baseline
| Axis | Baseline CausalStock | CausalStock (ours) |
|---|---|---|
| Causality level | Stock-level graph | Event-type graph (20×20) |
| News representation | Dense denoised embedding | Structured event + impact profile |
| Prediction task | Binary up/down | 3-class with a ±0.5% FLAT zone |
| Evaluation | Mostly random split | Stratified + chronological dual report |
| Result | *(fill from the run)* | *(fill from the run)* |
**Speak:** "The two formulations are complementary — event-type causality
transfers across companies, stock-level causality does not. We evaluate on a
stricter, dual-split protocol."
