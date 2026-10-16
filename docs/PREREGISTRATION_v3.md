# Pre-registration, round 3: topic momentum for ranking within a source

Written 2026-10-16. Committed before any question for the 2017 or 2023
cohort was generated.

## Background

Round 2 showed that `v2_embed_src` ranks questions within a generation
source at AUC about 0.65. Its improvement over Paper 3's model inside a source
was not significant.

Round 3 adds **topic momentum**: how much, and how recently, the field was
already publishing close to the question at its cutoff. The question and every
pre-cutoff paper of its subfield are embedded with the same model and compared
by cosine similarity (`forecast/momentum.py`).

To support this, the corpus was extended back to 2005 so that Paper 3's
training questions get the same features. The per-year counts match Paper 3's
harvest for 2005–2012.

## Development, already seen and not evidence

All labelled data so far serves as development data: the 2019, 2021 and 2022
cohorts, plus Paper 3's 980 questions evaluated leave-one-cutoff-out. The
results are in `results/round3/dev_v3.json`.

The momentum similarity thresholds (0.58 / 0.65) were set from the feature
distribution, not from outcomes.

| Model | Dev cohorts, within-source | Paper 3 LOCO, within-source |
| --- | --- | --- |
| v2 `v2_embed_src` | 0.646 | 0.689 |
| momentum + source FE | 0.676 | 0.667 |
| **v2 + momentum ensemble (= v3)** | **0.701** | **0.728** |

**The v3 model is fixed** in `forecast/models_v3.py` as `v3_ens` and its
calibrated version `v3_ens_cal`. It is not changed after this commit.

## Fresh test cohorts

Both cohorts use Paper 3's generators, unchanged: 8 subfields × 25 questions.

| Cohort | Cutoff | Past window | Outcome window | Leak-free training cutoffs |
| --- | --- | --- | --- | --- |
| `backtest2017` | 2017-12-31 | 2010–2017 | 2018-01-01 – 2022-12-31 (5 y) | 2012 only (labels end 2017) |
| `backtest2023` | 2023-12-31 | 2016–2023 | 2024-01-01 – 2026-10-14 (2.79 y) | 2012, 2014, 2016, 2018 (labels end ≤ 2023) |

**Training on a single cutoff.** The 2017 cohort has only one training cutoff,
about 200 questions. For it, the embedding model's C is fixed at 10 and Platt
calibration uses 5-fold cross-validation. This is stated in advance in
`models_v3.py`.

**Freeze.** v1, v2 and v3 predictions are frozen and pushed before labelling.

**Label.** Paper 3's label: TF-IDF top-8 candidates plus the strict gpt-4o
judge. The gpt-4o-mini label is also reported.

## Hypotheses

The 2017 and 2023 cohorts are pooled. Bootstraps use 2,000 resamples, seed 7,
stratified by source × cohort. Within-source AUC is the mean over source ×
cohort strata.

| ID | Hypothesis | Decision rule |
| --- | --- | --- |
| T1 | v3 ranks within a source | within-source AUC of `v3_ens` CI > 0.5 |
| T2 | **v3 ranks within a source better than v2** | paired Δ within-source AUC (`v3_ens` − `v2_embed_src`) CI > 0 |
| T3 | v3 ranks within a source better than v1 | paired Δ vs `m_logistic` CI > 0 |
| T4 | v3 beats the source prior | paired Δ pooled AUC vs `b_source` CI > 0 |
| T5 | v3 probabilities beat v2's | Brier(`v3_ens_cal`) < Brier(`v2_ens_cal`) |
| T6 | v3 ranks evidence-tension questions | AUC of `v3_ens` within `evidence_tension` CI > 0.5 |

T2 is the main claim of this round. All results will be reported whatever
they show. Per-cohort results are descriptive, as is the five-cohort view
(2017, 2019, 2021, 2022, 2023).
