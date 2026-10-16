"""Render a frozen prospective study as a ranked, human-readable forecast.

Writes ``results/<study>/forecast.csv`` and ``results/<study>/FORECAST.md``.

Usage:
    python -m forecast.forecast_table prospective2026
    python -m forecast.forecast_table paper2_prospective2026
"""

from __future__ import annotations

import sys

import pandas as pd

from forecast.common import ROOT, read_jsonl, study_dir
from forecast.cohort import STUDIES

ACTION_TEXT = {
    "collect_observation": "new independent observation",
    "rerun_analysis": "re-run existing analysis",
    "compare_datasets": "cross-check independent datasets",
    "run_simulation": "simulation / modelling test",
    "search_archive": "archival / survey search",
    "search_review": "consolidate via reviews",
    "read_paper": "read key paper",
}


def main() -> None:
    name = sys.argv[1]
    study = STUDIES[name]
    d = study_dir(name)
    pred = pd.DataFrame(read_jsonl(d / "predictions.jsonl"))
    plans = {p["question_id"]: p for p in read_jsonl(d / "planner.jsonl") if p["planner_config"] == "default"} \
        if (d / "planner.jsonl").exists() else {}
    pred["next_action"] = [
        "; ".join(dict.fromkeys(ACTION_TEXT.get(r["action_type"], r["action_type"])
                                for r in plans[q]["recommendations"][:3]))
        if q in plans and plans[q]["recommendations"] else ""
        for q in pred["question_id"]
    ]
    pred["why_up"] = [", ".join(f["feature"] for f in fs[:3]) for fs in pred["main_positive_factors"]]
    pred["why_down"] = [", ".join(f["feature"] for f in fs[:3]) for fs in pred["main_negative_factors"]]
    # Out-of-distribution flag: features outside the training 1st-99th
    # percentile range. A linear model extrapolates there, so those
    # probabilities say more about the question's format than its science.
    from forecast.predict import paper3_table
    from pipeline import models

    train = paper3_table()
    cols = models.feature_columns(train)
    lo_q, hi_q = train[cols].quantile(0.01), train[cols].quantile(0.99)
    seen = {c: set(train[c].unique()) for c in cols if train[c].nunique() <= 2}  # binary: rare is not OOD
    feats = pd.DataFrame(read_jsonl(d / "features.jsonl")).set_index("question_id")

    def ood(q: str, c: str) -> bool:
        v = feats.loc[q, c]
        return v not in seen[c] if c in seen else not lo_q[c] <= v <= hi_q[c]

    pred["ood_features"] = [", ".join(c for c in cols if ood(q, c)) for q in pred["question_id"]]
    pred["n_ood"] = [len([x for x in s.split(", ") if x]) for s in pred["ood_features"]]
    v2p = d / "predictions_v2.jsonl"
    has_v2 = v2p.exists()
    if has_v2:  # round-2 model (docs/PREREGISTRATION_v2.md), frozen in FREEZE_v2.json
        v2 = pd.DataFrame(read_jsonl(v2p))[["question_id", "v2_ens_cal__all"]].rename(columns={"v2_ens_cal__all": "p_v2"})
        pred = pred.merge(v2, on="question_id")
    key = "p_v2" if has_v2 else "p_attention"
    pred = pred.sort_values(key, ascending=False).reset_index(drop=True)
    pred["rank"] = pred.index + 1
    lo, hi = study["future_window"]
    out = ROOT / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    cols = ["rank", "question_id", "subfield", "source"] + (["p_v2"] if has_v2 else []) + [
            "p_attention", "s_structure__all", "question",
            "next_action", "why_up", "why_down", "n_ood", "ood_features"]
    pred[cols].to_csv(out / "forecast.csv", index=False)

    lo, hi = study["future_window"]
    def pcell(r) -> str:
        dag = " †" if r.n_ood >= 2 else ""
        return (f"{r.p_v2:.2f} | {r.p_attention:.2f}{dag}" if has_v2 else f"{r.p_attention:.2f}{dag}")

    phead = "p (v2) | p (v1)" if has_v2 else "p"
    pdash = "---|---" if has_v2 else "---"
    lines = [
        f"# Forecast: {name}",
        "",
        f"Cutoff {study['cutoff_date']}. The question is whether each question will be *substantively addressed* "
        f"by arXiv astro-ph papers in {lo} .. {hi}, as judged by Paper 3's label (top-8 retrieved papers, "
        "strict gpt-4o judge).",
        "",
    ]
    if has_v2:
        lines += [
            "- **p (v2)**: the round-2 model `v2_ens_cal` (question embedding + source fixed effect + Paper 3 "
            "features, calibrated), frozen in `FREEZE_v2.json`. On the fresh 2019 + 2022 backtests it scored "
            "pooled AUC 0.74 and Brier 0.207 (results/round2). **Ranked by this column.**",
            "- **p (v1)**: Paper 3's logistic model, the original frozen forecast (`FREEZE.json`): pooled AUC 0.66, "
            "Brier 0.240, over-confident at the top.",
            "",
        ]
    else:
        lines += ["`p` = Paper 3 logistic trained on all 980 labelled questions (frozen in `FREEZE.json`).", ""]
    lines += [
        f"Out-of-distribution: {int((pred.n_ood > 0).sum())} of {len(pred)} questions have at least one Paper 3 "
        "feature outside the training 1st-99th percentile (column `ood_features` in the CSV); † marks 2+ such "
        "features, where the v1 probability should not be trusted.",
        "",
        "## Mean forecast by subfield and source",
        "",
        pred.pivot_table(index="subfield", columns="source", values=key, aggfunc="mean").round(2).to_markdown(),
        "",
        "## Top 25 — most likely to be taken up",
        "",
        f"| # | {phead} | subfield | source | question | Paper 4 next step |",
        f"|---|{pdash}|---|---|---|---|",
    ]
    for r in pred.head(25).itertuples():
        lines.append(f"| {r.rank} | {pcell(r)} | {r.subfield} | {r.source} | {r.question} | {r.next_action or '—'} |")
    lines += ["", "## Bottom 15 — least likely", "", f"| # | {phead} | subfield | source | question |",
              f"|---|{pdash}|---|---|---|"]
    for r in pred.tail(15).itertuples():
        lines.append(f"| {r.rank} | {pcell(r)} | {r.subfield} | {r.source} | {r.question} |")
    tension = pred[pred.source == "evidence_tension"]
    if len(tension):
        lines += [
            "", "## Evidence-tension questions ranked", "",
            "Across three backtests (2019, 2021, 2022) the models mostly separate *kinds* of question; within the "
            "Paper 1-style tension questions the v2 model's ranking is weaker but real (AUC 0.61 on the fresh "
            "cohorts, CI 0.52-0.69). `structure` is Paper 3's evidence-graph structure prior. Paper 4's next steps "
            "are nearly identical for every question (see README).", "",
            f"| # | {phead} | structure | subfield | question | Paper 4 next steps |", f"|---|{pdash}|---|---|---|---|",
        ]
        for i, r in enumerate(tension.itertuples(), 1):
            st = f"{r.s_structure__all:.2f}" if pd.notna(r.s_structure__all) else "—"
            lines.append(f"| {i} | {pcell(r)} | {st} | {r.subfield} | {r.question} | {r.next_action or '—'} |")
    lines += ["", f"Full ranked table: `results/{name}/forecast.csv`.", ""]
    (out / "FORECAST.md").write_text("\n".join(lines))
    print(f"[forecast] {name}: {len(pred)} questions -> {out / 'FORECAST.md'}")


if __name__ == "__main__":
    main()
