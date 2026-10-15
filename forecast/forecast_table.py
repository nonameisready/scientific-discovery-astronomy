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
    pred = pred.sort_values("p_attention", ascending=False).reset_index(drop=True)
    pred["rank"] = pred.index + 1
    out = ROOT / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    cols = ["rank", "question_id", "subfield", "source", "p_attention", "s_structure__all", "question",
            "next_action", "why_up", "why_down", "n_ood", "ood_features"]
    pred[cols].to_csv(out / "forecast.csv", index=False)

    lo, hi = study["future_window"]
    lines = [
        f"# Forecast: {name}",
        "",
        f"Cutoff {study['cutoff_date']}; questions and scores frozen in `data/{name}/FREEZE.json`.",
        f"`p_attention` = probability (Paper 3 logistic, trained on all 980 labelled questions) that the "
        f"question is *substantively addressed* by arXiv astro-ph papers in {lo} .. {hi}, under Paper 3's L1 label.",
        "",
        "Calibration warning: on the 2021 backtest the absolute probabilities are only roughly calibrated "
        "(see results/backtest2021); read them as a ranking first.",
        "",
        f"Out-of-distribution: {int((pred.n_ood > 0).sum())} of {len(pred)} questions have at least one feature "
        "outside the training 1st-99th percentile (column `ood_features` in the CSV); questions marked † below "
        "have 2+ such features and their probability should not be trusted.",
        "",
        "## Mean forecast by subfield and source",
        "",
        pred.pivot_table(index="subfield", columns="source", values="p_attention", aggfunc="mean")
        .round(2).to_markdown(),
        "",
        "## Top 25 — most likely to be taken up",
        "",
        "| # | p | subfield | source | question | Paper 4 next step |",
        "|---|---|---|---|---|---|",
    ]
    for r in pred.head(25).itertuples():
        dag = " †" if r.n_ood >= 2 else ""
        lines.append(f"| {r.rank} | {r.p_attention:.2f}{dag} | {r.subfield} | {r.source} | {r.question} | {r.next_action or '—'} |")
    lines += ["", "## Bottom 15 — least likely", "", "| # | p | subfield | source | question |", "|---|---|---|---|---|"]
    for r in pred.tail(15).itertuples():
        dag = " †" if r.n_ood >= 2 else ""
        lines.append(f"| {r.rank} | {r.p_attention:.2f}{dag} | {r.subfield} | {r.source} | {r.question} |")
    lines += ["", f"Full ranked table: `results/{name}/forecast.csv`.", ""]
    (out / "FORECAST.md").write_text("\n".join(lines))
    print(f"[forecast] {name}: {len(pred)} questions -> {out / 'FORECAST.md'}")


if __name__ == "__main__":
    main()
