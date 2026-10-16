# Pre-registration, round 4: generator leakage

Written 2026-10-16. Committed before any template question was generated or
labelled.

## Threat

Every backtest question was phrased by gpt-4o-mini, whose training data
postdates all of the backtest cutoffs (2017–2023). A question phrased with
hindsight may be "about" what the field later did. That could inflate both
outcome rates and the forecaster's apparent skill.

## Design: LLM-free questions from the same evidence

For each backtest cutoff (2017, 2019, 2021, 2022, 2023) and each of the 8
subfields, `forecast/templates.py` builds questions **with no language model**.

**Tension templates.** It uses Paper 3's deterministic tension miner and
clusterer, the same clusters the LLM tension questions came from, and takes
the first 10 clusters. The cluster's focal sentence is inserted verbatim into
a fixed template:

> What explains the tension reported here, and does it reflect a real effect
> or a systematic or analysis artifact? "<sentence>"

**Future-work templates.** Paper 3's future-work statements are picked with
its selection rule and the cell's seed, 5 per cell. This is a fresh draw: the
LLM generator consumes random draws first, so these are **not paired** with
the LLM future-work questions. Each statement is inserted verbatim:

> How can this open problem be resolved? "<sentence>"

Every template tension question shares its cluster, meaning the same source
arXiv ids, with one LLM-phrased `evidence_tension` question in the frozen
cohort. That gives a **paired** comparison.

## Predictions, freeze and labels

- **Model.** v3 (`v3_ens`) scores every template question. It is fitted
  exactly as for the frozen cohorts: same leak-free training set per cutoff.
  The source fixed effect is all-zero, because the template sources were not
  seen in training. Momentum features are computed at each cutoff.
- **Freeze.** The scores are frozen with SHA-256 digests and pushed before
  labelling.
- **Label.** Paper 3's label: TF-IDF top-8 candidates plus the strict gpt-4o
  judge, over the same outcome window as the cohort of that cutoff.

## Hypotheses

All five cutoffs are pooled. Bootstraps use 2,000 resamples, seed 7, and are
stratified by cutoff × template type.

| ID | Hypothesis | Decision rule |
| --- | --- | --- |
| G1 | v3 predicts outcomes of questions no LLM wrote | pooled AUC CI > 0.5 |
| G2 | …and ranks within a template type | within-type AUC (mean over cutoff × type strata) CI > 0.5 |
| G3 | LLM phrasing inflates the outcome rate (leakage + phrasing) | report the paired difference in addressed rate, LLM-phrased minus template, on the same clusters, with a bootstrap CI over clusters. This is descriptive; no direction is assumed. |
| G4 | v3's skill does not depend on LLM phrasing | AUC of v3 on template tension questions vs on their paired LLM tension questions: paired-cluster bootstrap Δ, reported with CI. "Not dependent" if the CI includes 0 or favours the templates. |

All results will be reported.
