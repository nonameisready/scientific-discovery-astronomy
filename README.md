# scientific-discovery-astronomy

**Does the Paper 1–4 stack actually predict where astronomy goes next?**
This repository combines the four earlier papers into one astronomy forecaster
and tests it the only honest way available:

1. a pre-registered **out-of-time backtest** at a cutoff the stack has never
   seen (2021-12-31, outcomes 2022-01 → 2026-10);
2. a frozen **prospective forecast** made today (cutoff 2026-10-14), to be
   scored no earlier than 2031-10-15.

## 中文摘要

**结论：有效果，而且第二版比第一版明显好；但它主要还是在判断"哪类问题会火"，对同一类问题内部的排序只是中等水平。**

一共考了三次，截止点分别是 2019、2021、2022，共 600 道题。每次只用当时就能拿到的数据训练，预测先冻结、推送，然后才对答案。

- **Paper 3 原始模型（v1）三次都稳定有效**：AUC 分别是 0.65、0.66、0.68，明显强于随机（0.5）。
- **第二版模型（v2）**：问题的语义向量，加上"问题来源"作为已知项，再加概率校准。
  - 两个新考场（2019 和 2022）是预注册后才生成的，v2 在这两组上的总体 AUC 是 **0.74**（0.69–0.78）。
  - v2 **显著超过了**"只看问题来源"的基线（+0.07）。v1 做不到这一点。
  - 同一类问题内部的排序：AUC 0.65（0.58–0.71），显著强于随机。不过比 v1（0.60）的提升没有达到显著。
  - 概率更可信：Brier 分数从 0.240 降到 0.207，越低越好。
  - 在 Paper 1 式的"证据张力"问题里，排序能力勉强显著：AUC 0.61。
- Paper 4 的规划器仍然没有预测力，它几乎给每个问题推荐同一个下一步。
- 2026→2031 的前瞻预测已加入 v2 分数，并单独冻结在 `FREEZE_v2.json`。v1 原版不动。

## The stack

| Paper | Repository | Role here |
| --- | --- | --- |
| 1 | [scientific-question-discovery](https://github.com/nonameisready/scientific-question-discovery) | evidence-tension question generation (via Paper 3's `evidence_tension` source) |
| 2 | [scientific-question-discovery-benchmark](https://github.com/nonameisready/scientific-question-discovery-benchmark) | freeze → temporal isolation → outcome labels; its 200-question 2026 instance is scored here too |
| 3 | [scientific-question-outcome-prediction-indicators](https://github.com/nonameisready/scientific-question-outcome-prediction-indicators) | the predictor: generators, six feature groups, models, outcome judge |
| 4 | [scientific-evidence-planner](https://github.com/nonameisready/scientific-evidence-planner) | ranked next-evidence actions; planner utility as a candidate predictor |

All upstream code and training data are vendored **unmodified** at pinned
commits under [`vendor/`](vendor/README.md).

The vendored predictor reproduces Paper 3's published temporal-split result
exactly: logistic AUC 0.7126.

## Order of events

The git history on GitHub timestamps each step.

| Commit | What | Labels exist? |
| --- | --- | --- |
| `bcf8469` | code + [pre-registration](docs/PREREGISTRATION.md) (H1–H7) | no questions yet |
| `60f0f5d` | 2021 cohort + all predictions frozen ([FREEZE.json](data/backtest2021/FREEZE.json)) | **no** |
| `2a896d8` | 2026 forecasts frozen | 2021 labels being computed, not yet seen |
| `5292d2c` | 2021 labels, evaluation, README | yes |
| `a4eea0f` | round-2 [pre-registration](docs/PREREGISTRATION_v2.md) + v2 models | no 2019/2022 questions yet |
| `bd84ebc`, `58fe4b7` | 2022 and 2019 cohorts + v1/v2 predictions frozen | **no** |
| `cc7892b` | 2019/2022 labels | yes |

## Data

- arXiv astro-ph, including cross-lists, 2013-01-01 → 2026-10-14: 236,290 papers.
- Harvested via OAI-PMH with v1 dates, classified by Paper 3's subfield rules.
- The harvest matches Paper 3's corpus per year and per subfield to within
  0.3% ([comparison](data/corpus/harvest_comparison.json)), so features are
  measured the way the model was trained.
- The raw corpus is not committed; rebuild it with `forecast.harvest_oai` and
  `forecast.corpus_build`.

## Study 1: out-of-time backtest (cutoff 2021-12-31)

### Setup

**Questions.** 200 questions from Paper 3's generators, unchanged: 8 subfields
× 25 = 10 evidence-tension, 5 direct-LLM, 5 author-future-work and 5 controls
per subfield. Past window 2014–2021.

**Primary model.** Paper 3's logistic model, trained **only on Paper 3's
2012/2014/2016 cutoffs**. Their labels end by 2021-12-31, so this is the model a
forecaster could actually have fit on the cutoff day. Paper 3's 2018 and 2020
labels run to 2023 and 2025, which overlaps this outcome window and would leak.

**Outcome.** "Substantively addressed" between 2022-01-01 and 2026-10-14,
using Paper 3's label: top-8 retrieved future papers plus the strict judge.

### Results

Paper 3 label (gpt-4o judge), n = 200, base rate 0.505.

| Hypothesis | Result | Verdict |
| --- | --- | --- |
| H1 discriminates out of time | AUC **0.656** [0.583, 0.733] | ✅ supported |
| H2a beats subfield popularity | ΔAUC +0.102 [+0.039, +0.167] | ✅ supported |
| H2b beats the generation-source prior | ΔAUC −0.024 [−0.109, +0.073]; source prior alone AUC 0.680 | ❌ not supported |
| H3 discriminates *within* source | mean 0.569 [0.496, 0.650] | ❌ not supported (details below) |
| H4 Brier below the constant | 0.2465 vs 0.2503 | ✅ by the rule, but negligible |
| H5 structure prior, tension questions | AUC 0.629 [0.505, 0.752] (n = 80) | ✅ barely |
| H6 Paper 4 utility does *not* predict attention | AUC 0.419 [0.305, 0.537] | ✅ null replicated (leans negative) |
| H7 Paper 4 top action matches the field's follow-up | pending (needs the citation crawl) | — |

**H3, per source.** Within-source AUC was 0.84 for controls, 0.64 for evidence
tension, 0.52 for future work, and 0.27 for direct LLM (inverted).

**Calibration by predicted quintile.**

| Quintile | Mean predicted | Observed rate |
| --- | --- | --- |
| 1 | 0.21 | 0.25 |
| 2 | 0.42 | 0.43 |
| 3 | 0.56 | 0.58 |
| 4 | 0.74 | 0.70 |
| 5 | 0.90 | **0.58** |

The bottom four quintiles are well calibrated. The top quintile is overconfident.

**Rates by source.** Direct-LLM questions were addressed 85% of the time,
future-work 48%, evidence-tension 45%, and controls 30%. This is the ordering
Paper 3 found, and most of what the model "knows".

**Not pre-registered, reported for completeness.**
- A plain TF-IDF text model trained on the same 2012–2016 data scored AUC 0.714
  [0.640, 0.781], at least as good as the structured model.
- Paper 3's GBM scored 0.654.
- Training on all five cutoffs (`m_logistic__all`, leaky for this window)
  scored 0.674.

![ROC and calibration](results/backtest2021/backtest_roc_calibration.png)

Full numbers are in [`results/backtest2021/evaluation.json`](results/backtest2021/evaluation.json)
and per question in [`per_question.csv`](results/backtest2021/per_question.csv).

### What this says about the stack

1. **Paper 3's predictor transfers forward in time.** It is a little weaker
   than in its own era (0.66 vs 0.71), and it clearly beats field popularity.
2. **Most of its skill is knowing what kind of question it is looking at.**
   It does not beat a one-number-per-source prior. Broad LLM-written
   questions are almost always "engaged". Within those, the model's ranking
   is backwards.
3. **The question-level signal that does exist sits where Paper 1 placed it.**
   It is in ranking evidence-tension questions: model AUC 0.64, and the Paper 2/3
   structure prior 0.63. It also separates the weak controls well.
4. **Paper 4's planner is not a forecaster.** Its utility does not predict
   uptake, consistent with Paper 4's own retraction. Its top action is nearly
   constant: `run_simulation` for 77 of 78 questions under the default config,
   and `search_review` for all 78 under the Paper-3-informed config. So in its
   current form its recommendations carry little question-specific information.

## Round 2: two more cutoffs and a within-source model

[Pre-registered](docs/PREREGISTRATION_v2.md) after round 1. The v2 models
were designed on the 2021 cohort, which therefore serves as their
development set. Both test cohorts were generated, scored and frozen
before any of their labels existed:

- 2019: frozen at commit `58fe4b7`, outcome window 2020–2024, trained on
  cutoffs 2012 and 2014 only.
- 2022: frozen at commit `bd84ebc`, outcome window 2023 to 2026-10, trained
  on cutoffs 2012–2016.

**v2 models** ([`forecast/models_v2.py`](forecast/models_v2.py)):
- `v2_embed_src`: the question's embedding (`text-embedding-3-small`) plus a
  source fixed effect, so the rest of the model must explain variation
  *within* a source.
- `v2_ens_cal`: averages `v2_embed_src` with Paper 3's features (also with a
  source fixed effect), then applies Platt calibration on out-of-fold
  training predictions.

### Results on the fresh 2019 + 2022 cohorts

Paper 3 label (gpt-4o judge), n = 400, base rate 0.57.

| Hypothesis | Result | Verdict |
| --- | --- | --- |
| R1 v1 discriminates out of time | pooled AUC 0.659 [0.603, 0.709]; 2019: 0.654, 2022: 0.677 | ✅ replicated |
| R2 v2 ranks within a source | within-source AUC **0.646** [0.583, 0.710] | ✅ |
| R3 v2 beats v1 within a source | Δ +0.048 [−0.046, +0.142] | ❌ not significant |
| R4 v2 beats the source prior | pooled AUC **0.737** vs 0.669; Δ +0.068 [+0.019, +0.117] | ✅ |
| R5 calibrated v2 has the best Brier | v2 0.207 < source prior 0.224 < v1 0.240 < constant 0.248 | ✅ |
| R6 v2 ranks evidence-tension questions | AUC 0.606 [0.515, 0.694] | ✅ (barely) |

### All three cutoffs

This view is descriptive, because 2021 was the v2 development set.

| Model | 2019 pooled / within | 2021 (dev) pooled / within | 2022 pooled / within |
| --- | --- | --- | --- |
| v1 (Paper 3 logistic) | 0.654 / 0.548 | 0.656 / 0.569 | 0.677 / 0.648 |
| source prior | 0.667 / 0.500 | 0.680 / 0.500 | 0.667 / 0.500 |
| TF-IDF text | 0.697 / 0.647 | 0.714 / 0.597 | 0.683 / 0.602 |
| **v2 embed + source** | **0.730 / 0.642** | 0.745 / 0.646 | **0.747 / 0.650** |
| v2 ensemble, calibrated | 0.738 / 0.617 | 0.759 / 0.604 | 0.758 / 0.664 |

![AUC by cohort](results/round2/auc_by_cohort.png)

### What round 2 changes

- **Round 1's main result replicates.** Paper 3's model scores 0.65–0.68 at
  every new cutoff.
- **Round 1's H3 failure was partly noise in the 2021 cohort.** On the fresh
  cohorts v1's within-source AUC is 0.598 [0.531, 0.667]. Its inverted
  ranking of direct-LLM questions in 2021 (0.27) was 0.52 on the fresh
  cohorts.
- **v2 is the better forecaster.** It is the first model in this study to
  clearly beat the source-type prior. Its probabilities are also the
  best calibrated.
- **The within-source gain is real but modest.** v2 ranks questions inside a
  source at about 0.65, and inside tension questions at about 0.61. It is
  not yet significantly better than v1 *within* a source.
- **Under the lenient gpt-4o-mini label**, where 90% of questions count as
  addressed, the same picture holds more weakly: R1 0.651; R4 Δ +0.074
  [+0.009, +0.140].

Full numbers: [`results/round2/evaluation.json`](results/round2/evaluation.json).

## Study 2: the prospective forecast (cutoff 2026-10-14 → scored ≥ 2031-10-15)

Both tables are now ranked by the v2 model, frozen separately in
`FREEZE_v2.json`. The original v1 scores stay alongside, unchanged.

- **[`results/prospective2026/FORECAST.md`](results/prospective2026/FORECAST.md)**
  covers 200 new questions across the 8 subfields. It includes a ranking of the
  80 evidence-tension questions with Paper 4's next steps, which is the slice
  the backtest supports.
- **[`results/paper2_prospective2026/FORECAST.md`](results/paper2_prospective2026/FORECAST.md)**
  scores Paper 2's 200 questions frozen on 2026-08-17.
  - Mean `p_attention` by generator: direct LLM 0.48, tension-LLM 0.38,
    random claim 0.24, tension-template 0.02.
  - The template questions are ~80-word quoted statements, far outside the
    training distribution (flagged †). Their near-zero scores are an
    extrapolation artifact, not a forecast.

Every forecast table flags features outside the training 1st–99th percentile.
Pre-registered claims to check in 2031: **P1** AUC > 0.5, and **P2** the top
quintile is addressed more often than the bottom quintile.

## Deviations from the pre-registration

1. **Wrong judge named.**
   - What happened: the pre-registration called gpt-4o-mini "Paper 3's label,
     unchanged". That is the code's default, but Paper 3's committed labels
     were made with gpt-4o (956/980), and its paper calls mini the "lenient
     first-pass judge".
   - Check: re-judging 120 of Paper 3's own questions today on their own
     candidates, gpt-4o reproduces the published labels (agreement 0.92,
     κ = 0.83, identical 50.8% rate). gpt-4o-mini marks 93% as addressed
     (κ = 0.14). See [`results/judge_drift.json`](results/judge_drift.json).
   - Consequence: the analysis matching the pre-registered *intent* ("the label
     Paper 3's model was trained to predict") uses gpt-4o, which is the label
     shown above.
   - The as-written gpt-4o-mini label is also reported: base rate 0.86;
     H1 AUC 0.707 [0.590, 0.818]; H2b ΔAUC vs source +0.116 [−0.022, +0.253];
     H3 within-source 0.682 [0.567, 0.798].
   - Under that lenient label H3 would pass. We do not adopt it, because it is
     not the measurement the model was trained on.
2. **L3 citation source.** Semantic Scholar was used as pre-registered, but
   its anonymous API is heavily rate-limited, so the citation crawl runs
   slowly. L3 and H7 will be added when it completes.
3. **Outcome window** of 4.79 years instead of Paper 3's 5. This was stated in
   advance.

## Limitations

- **Hindsight in question generation.** Questions are written by gpt-4o-mini,
  whose training data postdates the 2021 cutoff, so some questions may encode
  hindsight; Paper 2 found this inflates direct-LLM engagement. The
  *predictor* is unaffected: it saw no post-2021 outcome.
- **The label is retrieval-bounded.** Paper 4 showed abstract retrieval misses
  engagement with narrow questions. The citation-graph label (L3) addresses
  this when the crawl finishes.
- **Sample size.** Three cohorts of 200 questions each, with one primary judge.
  The intervals are still about ±0.05 AUC.

## Reproduce

```bash
pip install -r requirements.txt            # OPENAI_API_KEY needed only for uncached LLM calls
python -m forecast.harvest_oai --from 2013-01-01 --until 2017-12-31 --tag w1   # (+ w2..w4, see corpus_manifest.json)
python -m forecast.corpus_build
python -m forecast.cohort backtest2021 && python -m forecast.predict backtest2021 && python -m forecast.freeze backtest2021
python -m forecast.label backtest2021 && python -m forecast.evaluate backtest2021
python -m forecast.judge_drift
python -m forecast.cohort prospective2026 && python -m forecast.predict prospective2026 && python -m forecast.forecast_table prospective2026
# round 2
python -m forecast.cohort backtest2019 && python -m forecast.predict backtest2019 && python -m forecast.predict_v2 backtest2019 && python -m forecast.freeze backtest2019
python -m forecast.label backtest2019 --no-citation    # same for backtest2022
python -m forecast.evaluate_v2
```

Every LLM response is cached under `data/cache/llm/` and committed, so all
results reproduce offline.
