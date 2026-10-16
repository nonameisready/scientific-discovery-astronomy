# Pre-registration, round 2: more cutoffs, and ranking within a source

This file was written on 2026-10-16 and is committed before any question for the
2019 or 2022 cohort was generated.

## Why a second round

Round 1 (cutoff 2021, `docs/PREREGISTRATION.md`) found two things:

- Paper 3's model beats chance out of time, with AUC 0.66.
- It does **not** beat a source-type prior, and it does not rank questions
  *within* a generation source (within-source AUC 0.57).

Round 2 asks two questions:

1. Does round 1's result replicate at two new cutoffs?
2. Can a model built to rank within a source do better?

## What was designed after seeing round-1 outcomes

The v2 models in `forecast/models_v2.py` were designed after the 2021 labels
were known. The 2021 cohort is therefore their **development set**. Their
2021 numbers are reported but are not evidence.

Development-set results under the Paper 3 label (gpt-4o judge):

| Model | Pooled AUC | Within-source AUC |
| --- | --- | --- |
| v1 | 0.656 | 0.569 |
| `v2_embed_src` | 0.745 | 0.646 |
| `v2_ens` | 0.758 | 0.604 |

On this basis, `v2_embed_src` is fixed as the primary v2 model. `v2_ens_cal`
is fixed as the probability model.

## Fresh test cohorts

Both cohorts are built with Paper 3's generators, unchanged:
8 subfields × (10 tension, 5 direct-LLM, 5 future-work, 5 control).

| Cohort | Cutoff | Past window | Outcome window | Leak-free training cutoffs |
| --- | --- | --- | --- | --- |
| `backtest2019` | 2019-12-31 | 2012–2019 | 2020-01-01 – 2024-12-31 (5 y, as Paper 3) | 2012, 2014 (labels end ≤ 2019) |
| `backtest2022` | 2022-12-31 | 2015–2022 | 2023-01-01 – 2026-10-14 (3.79 y) | 2012, 2014, 2016 (labels end ≤ 2021) |

## Freeze, labels and models

**Freeze.** Predictions from v1 (`forecast.predict`) and v2 (`forecast.predict_v2`)
are frozen with SHA-256 digests and pushed before labelling.

**Label.** Paper 3's label: TF-IDF top-8 future candidates and the strict
**gpt-4o** judge. Round 1 verified that this reproduces Paper 3's committed
labels (κ = 0.83). The gpt-4o-mini label is also computed and reported, as
in round 1.

The citation-graph label is not used in round 2, because Semantic Scholar's
anonymous API rate limit makes it impractical.

**Models compared.** All are fitted on the cohort's leak-free training set
only.

- `m_logistic` (v1): Paper 3's structured logistic model.
- `b_source`: the training addressed-rate of the question's source.
- `v2_embed_src`: question embedding (`text-embedding-3-small`) plus a source
  fixed effect, logistic. C is chosen by leave-one-cutoff-out AUC inside the
  training set.
- `v2_ens_cal`: the mean log-odds of `v2_embed_src` and `v2_struct_src`,
  Platt-calibrated on out-of-fold training predictions.

## Hypotheses

The 2019 and 2022 cohorts are pooled for each test. Bootstraps use 2,000
resamples, seed 7, stratified by source × cohort. "Within-source AUC" means
the mean, over source × cohort strata that contain both outcome classes, of
the AUC inside each stratum.

| ID | Hypothesis | Decision rule |
| --- | --- | --- |
| R1 | v1 discriminates out of time (replicating round-1 H1) | pooled AUC 95% CI > 0.5, and AUC > 0.5 in each cohort |
| R2 | `v2_embed_src` ranks within a source | within-source AUC CI > 0.5 |
| R3 | `v2_embed_src` ranks within a source better than v1 | paired ΔAUC (within-source) CI > 0 |
| R4 | `v2_embed_src` beats the source prior | paired Δ pooled AUC vs `b_source` CI > 0 |
| R5 | calibrated v2 probabilities beat v1's | Brier(`v2_ens_cal`) < Brier(v1) and < Brier(constant) |
| R6 | v2 ranks evidence-tension questions | AUC of `v2_embed_src` within `evidence_tension` CI > 0.5 |

All results are reported regardless of outcome. Results for each cohort
alone, and the three-cohort picture including 2021, are descriptive.
