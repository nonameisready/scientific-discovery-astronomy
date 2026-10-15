# scientific-discovery-astronomy

**Does the Paper 1–4 stack actually predict where astronomy goes next?**
This repository combines the four earlier papers into one astronomy forecaster
and tests it the only honest way available:

1. a pre-registered **out-of-time backtest** at a cutoff the stack has never
   seen (2021-12-31, outcomes 2022-01 → 2026-10);
2. a frozen **prospective forecast** made today (cutoff 2026-10-14), to be
   scored no earlier than 2031-10-15.

## 中文摘要

**结论：有效果，但有限。**

在从未见过的 2021 年截止点上，Paper 3 的预测器确实能区分哪些天文问题会在之后约 5 年里被学界实质性跟进。

- 区分度明显高于随机：AUC 0.66，95% 置信区间 0.58–0.73。Paper 3 原文报告的是 0.71。
- 它比"子领域热度"基线强。
- 它**没有**超过一个最简单的基线：只看问题是由哪种方法生成的。直接让 LLM 写的问题 85% 被跟进，对照问题只有 30%。
- 在同一来源内部，它的区分力不显著：AUC 0.57，置信区间 0.50–0.65。
  - 真正有效的部分是：给 Paper 1 式的"证据张力"问题排序（AUC 0.64），以及识别对照问题（AUC 0.84）。
  - 对直接 LLM 问题，它的排序甚至是反的（AUC 0.27）。
- 概率偏自信：最高五分位预测 0.90，实际只有 0.58。
- Paper 3 的证据图结构先验在张力问题内勉强有效：AUC 0.63，置信区间 0.50–0.75。
- Paper 4 的效用分数不能预测关注度：AUC 0.42，置信区间 0.31–0.54。这与 Paper 4 自己撤回的结论一致。
- Paper 4 对几乎所有问题给出同一个"下一步"，没有区分度。

基于这些结果，本仓库给出了 2026→2031 的前瞻预测：200 个新问题，外加 Paper 2 冻结的 200 个问题。这些预测已用 SHA-256 冻结，2031 年才能评分。

另有一处方法上的发现：预注册时写错了评审模型。Paper 3 的标签实际是用 GPT-4o 判的，GPT-4o-mini 宽松得多（93% 判为"已跟进"，κ=0.14）。这一点已作为偏差如实报告，见下文。

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
| later | labels, evaluation, this README | yes |

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

## Study 2: the prospective forecast (cutoff 2026-10-14 → scored ≥ 2031-10-15)

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
- **Single run.** One cohort of 200 questions and one judge; the confidence
  intervals are wide.

## Reproduce

```bash
pip install -r requirements.txt            # OPENAI_API_KEY needed only for uncached LLM calls
python -m forecast.harvest_oai --from 2013-01-01 --until 2017-12-31 --tag w1   # (+ w2..w4, see corpus_manifest.json)
python -m forecast.corpus_build
python -m forecast.cohort backtest2021 && python -m forecast.predict backtest2021 && python -m forecast.freeze backtest2021
python -m forecast.label backtest2021 && python -m forecast.evaluate backtest2021
python -m forecast.judge_drift
python -m forecast.cohort prospective2026 && python -m forecast.predict prospective2026 && python -m forecast.forecast_table prospective2026
```

Every LLM response is cached under `data/cache/llm/` and committed, so all
results reproduce offline.
