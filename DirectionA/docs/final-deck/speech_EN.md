# EventChain — Presentation Script (English)

**Target: ~13–15 min · 19 slides · CS173 Data Mining Final · Team 2**
Pacing: ~40–60 s per slide. Honest-audit framing — do not claim the model
"predicts well" or that the causal graph "works".

---

### Slide 1 — Title
Good morning. We're Team 2, and our project is **EventChain** — structured
event-chain modeling for news-driven stock prediction. The one sentence to
keep in mind: this is a **data-driven, honest audit** of whether — and how —
financial news can predict stock movements. Three words frame everything we
did: data-driven, interpretable, and honest.

### Slide 2 — Agenda
We'll move through five parts: the data and the problem; our exploratory data
analysis; the method; the experiments; and an honest discussion of what
worked and what did not.

### Slide 3 — Problem & Task
The task is news-driven stock movement prediction. For each stock on each day,
the input is its 32 most recent news events, a 30-day price window, and the
ticker. The output is the next day's direction — up, down, or flat — with a
half-percent threshold. We use a 5% subset of FNSPID: 22 stocks, 2010 to 2023.
The task is fragile, because a news item is never a standalone signal — a rate
hike triggers a chain of effects over days to weeks, and a single sentiment
score throws that structure away.

### Slide 4 — Baseline: CausalStock (NeurIPS 2024)
Our baseline is CausalStock, from NeurIPS 2024. It does two things: it
compresses each article into one dense embedding, and it learns a causal graph
between individual stocks. That leaves two blind spots. One — a single vector
per article hides what type of event occurred, how large it was, and which
entity it hit. Two — a stock-level graph can say stock A leads stock B, but
not what kind of event drove that link. EventChain targets exactly those gaps.

### Slide 5 — Positioning: EventChain vs CausalStock
This slide is the heart of our positioning. Every design choice in EventChain
is justified by a specific, measured finding in the FNSPID data. Where the
baseline uses a dense embedding, we use a structured event with an impact
profile — because 88% of articles carry explicit price language. Where it
builds a stock-level graph, we build a 20-by-20 event-type graph, transferable
across companies. We add source credibility, a novelty attribute, and an
explicit scope attribute — and each one, as you'll see next, comes from a
number in the data.

### Slide 6 — EDA (1/2): Dataset & Missingness
So let's look at the data. From the 5% subset we built 10,901 structured
events and 9,566 ticker-aligned examples. The missingness audit is revealing:
publisher is missing 79% of the time, author 68% — we cannot supervise on
those. But the URL is present essentially always. So we derive a credibility
score from the URL domain. And 29% of headlines are duplicates — the same
event reported many times — which motivates a novelty attribute.

### Slide 7 — EDA (2/2): Event Density & Long Tail
Two more findings drive design. First, the corpus is event-dense: 88% of
articles contain price-movement language, 77% a numeric comparison, 56%
earnings. This is not diffuse opinion — it is a stream of discrete, typable
events. That is our empirical justification for extracting structured events
rather than scoring sentiment. Second, the event-type distribution is
long-tailed — the top three classes are 55% of the data — so training must be
class-aware; and scope cues appear in 89% of articles, which motivates scope.

### Slide 8 — The Innovation: Three Findings, Three Attributes
Here is our core innovation in one slide. Three measured data findings, three
new event attributes. Duplicate headlines, 29%, give us novelty — one minus
similarity to recent same-ticker news. Missing provenance gives us credibility
— a URL-domain authority score. Multi-scope news gives us scope — single,
sector, market, or global. The point is: these attributes are not assumed,
they are earned from the data.

### Slide 9 — Framework Overview
This is the full pipeline. Exploratory analysis drives the schema. Phase 1, a
FinBERT multi-head extractor, turns news into structured events. Phase 2,
STACD, attempts lag-aware causal discovery over event types. Phase 3 is the
prediction layer — a tabular model plus a causal ensemble — producing the
next-day movement.

### Slide 10 — Phase 1: Structured Event Extraction
Phase 1 in detail. A FinBERT encoder feeds four decoder heads: event type,
argument spans, magnitude, and the auxiliary attributes. Because there are no
gold labels at scale, we use LLM silver labels with a hybrid correction:
before each LLM call we inject rule- and market-grounded anchors — surprise
from actual-versus-expected numbers, novelty from embedding similarity — to
suppress hallucination. The result is 10,901 events over 20 types, with about
85% average attribute coverage.

### Slide 11 — The Three Data-Driven Attributes
The three attributes precisely. Novelty is one minus the maximum similarity to
recent same-ticker news — it decays repeated reporting. Credibility is a
three-tier URL-domain authority score — robust to the missing publisher field.
Scope is single, sector, market, or global — it down-weights ticker assignment
when the news is not a single-stock event.

### Slide 12 — Phase 2: STACD Causal Discovery
Phase 2 is STACD — sparse temporal attention for causal discovery. It learns
two 20-by-20 matrices: a directed-strength matrix A and a lag matrix. The
attention is modulated three ways: a time-direction mask, so only the past
attends to the future; a Gaussian lag gate that peaks at the learned delay;
and a causal-strength prior. A NOTEARS term encourages acyclicity. Whether
this objective actually recovers structure is an empirical question — and the
next slide answers it honestly.

### Slide 13 — Phase 2 Result: The Causal Graph Did Not Learn
This is where we are most honest. We trained STACD for 12 epochs on the full
corpus. The result is a *diagnosed negative one*. The trained causal matrix
has mean 0.27 and standard deviation 0.05 — statistically identical to its
initialization — and across all 12 epochs it barely moves. Why? STACD's
prediction head sits near 50%, random, so almost no gradient reaches the
graph. The same weak forward-time signal that we'll see collapse prediction is
what starves the causal discovery. We report this honestly: under an
end-to-end objective on a low-signal target, event-type causal discovery is
not identifiable here. Our next step is to estimate the graph descriptively,
from observed lagged co-occurrence.

### Slide 14 — Phase 3: Prediction Layer
Phase 3, the prediction layer. We deliberately keep it transparent and
tabular. Each example becomes a 132-dimensional vector — price features, event
statistics, and a stock identity — and a histogram gradient-boosting model
predicts the class. We also build a causal ensemble that adds the learned
causal-temporal representations. We explored a Neural-ODE propagation network
as well, but, as the experiments show, it did not help.

### Slide 15 — Experiment 1: Attribute Coverage
Experiment one — attribute coverage. Polarity, scope, novelty, and credibility
are dense — about 85% coverage — so we treat them as standard features.
Surprise is sparse, only 6.6%, concentrated in earnings and macro releases —
so we treat it as a sparse, high-information indicator rather than a universal
feature.

### Slide 16 — Experiment 2: Main Results & Ablation
Experiment two — where does performance come from. A majority-class baseline
is 0.20 macro-F1. Our tabular model — price, news, and stock — reaches 0.69.
The causal ensemble reaches 0.71. But two honest caveats: that gain is
single-seed and small; and the ODE-only variants all sit below the tabular
baseline — so we do not feature the ODE stage.

### Slide 17 — Experiment 3: Honest Evaluation
Experiment three is our most important result. Under a stratified random
split, the model reaches 0.69. But a random split on time-series data leaks —
examples from the same period land in both training and test. So we also run a
chronological split. There, macro-F1 falls to 0.34 — essentially the random
baseline. This is the central finding: in-distribution, the features carry
usable structure; but forward-time direction at half a percent is, on this
data, near-impossible — consistent with semi-strong market efficiency.
Reporting only the stratified number would overstate real predictive power.

### Slide 18 — Discussion: Limits, Learned, Future
What we learned: the EDA-driven schema is our strongest, most defensible
contribution; and three negative results — the static causal graph, the
overfitting ODE, the chronological collapse — share one cause, the weak
forward-time signal. Our limits: end-to-end causal discovery did not learn
here; results are single-seed; the subset is small. Future work: estimate the
event-type graph from lagged co-occurrence — no end-to-end gradient needed —
add multi-seed confidence intervals, and adopt rolling walk-forward validation.

### Slide 19 — References & Q&A
To summarize: EventChain is an honest, end-to-end audit of news-driven stock
prediction. We contribute a data-grounded event schema, a reproducible
extraction pipeline, and a clear diagnosis of where — and why — an end-to-end
causal objective fails on low-signal financial data. Thank you — we're happy
to take questions.

---

## Anticipated Q&A

**Q: Why is the stratified score 0.69 but the chronological score 0.34?**
A random split on time series leaks information — adjacent days of the same
stock land in both train and test. The chronological split is the honest
number. We deliberately report both; the gap *is* the finding.

**Q: The causal graph did not learn — isn't the project a failure?**
No. It is a diagnosed negative result with a mechanism: the prediction signal
is near-random, so the gradient that would shape the graph is negligible. The
contributions — the EDA-driven schema and the honest end-to-end audit — stand
on their own. Negative results with a diagnosis are legitimate scientific
output.

**Q: Does the 0.69 come from the news, or just from price?**
Feature importance shows price-history features dominate; the causal ensemble
adds only about 1.6 points, single-seed. We are explicit that the
in-distribution score is largely a price signal — that honesty is part of the
contribution.

**Q: Why not compare head-to-head with CausalStock's numbers?**
Different task (our 3-class with a flat zone vs their binary), different data
scale, different split protocol — the numbers are not directly comparable. We
compare conceptually, along data, method, and protocol axes.

**Q: What is the single most useful next step?**
Estimating the event-type graph from observed lagged co-occurrence statistics.
It is descriptive, needs no end-to-end gradient, and would give Phase 2 a real
positive interpretability product.
