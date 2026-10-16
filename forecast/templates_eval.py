"""Round 4: label the LLM-free template questions and test G1-G4
(docs/PREREGISTRATION_v4.md).

Usage:
    python -m forecast.templates_eval label      # Paper 3 label (gpt-4o judge), after the freeze
    python -m forecast.templates_eval evaluate
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from forecast.common import ROOT, read_jsonl, study_dir, write_jsonl
from forecast.cohort import STUDIES
from forecast.evaluate_v2 import _pooled, _strata, _within, boot
from forecast.label import label_l1, label_l2
from forecast.predict import PRIMARY_TRAIN
from forecast.templates import COHORTS, OUT

N_BOOT = 2000
SEED = 7


def label() -> None:
    if not (OUT / "FREEZE.json").exists():
        raise SystemExit("refusing to label: template predictions are not frozen")
    for name in COHORTS:
        qs = read_jsonl(OUT / name / "questions.jsonl")
        l1, ctxs = label_l1(qs, STUDIES[name])
        write_jsonl(OUT / name / "labels_L1.jsonl", l1)
        write_jsonl(OUT / name / "labels_L2.jsonl", label_l2(qs, l1, ctxs))
        print(f"[templates] {name}: labelled", flush=True)


def _cluster_key(q: dict) -> frozenset:
    return frozenset(x["arxiv_id"] for x in q["source_material"]["cluster"])


def load_templates() -> pd.DataFrame:
    rows = []
    for name in COHORTS:
        d = OUT / name
        p = pd.DataFrame(read_jsonl(d / "predictions_v3.jsonl"))
        lab = pd.DataFrame(read_jsonl(d / "labels_L2.jsonl"))[["question_id", "addressed"]]
        df = p.merge(lab, on="question_id")
        tag = PRIMARY_TRAIN[name]
        rows.append(pd.DataFrame({"question_id": df.question_id, "cohort": name, "source": df.source,
                                  "y": df.addressed.astype(int), "v3_ens": df[f"v3_ens__{tag}"].values}))
    return pd.concat(rows, ignore_index=True)


def paired() -> pd.DataFrame:
    """One row per cluster: template vs LLM-phrased tension question."""
    rows = []
    for name in COHORTS:
        tag = PRIMARY_TRAIN[name]
        llm_q = {_cluster_key(q): q["question_id"] for q in read_jsonl(study_dir(name) / "questions.jsonl")
                 if q["source"] == "evidence_tension"}
        llm_p = {r["question_id"]: r[f"v3_ens__{tag}"] for r in read_jsonl(study_dir(name) / "predictions_v3.jsonl")}
        llm_y = {r["question_id"]: int(r["addressed"]) for r in read_jsonl(study_dir(name) / "labels_L2.jsonl")}
        tp = {r["question_id"]: r[f"v3_ens__{tag}"] for r in read_jsonl(OUT / name / "predictions_v3.jsonl")}
        ty = {r["question_id"]: int(r["addressed"]) for r in read_jsonl(OUT / name / "labels_L2.jsonl")}
        for q in read_jsonl(OUT / name / "questions.jsonl"):
            if q["source"] != "template_tension":
                continue
            lq = llm_q[_cluster_key(q)]
            rows.append({"cohort": name, "template_id": q["question_id"], "llm_id": lq,
                         "y_template": ty[q["question_id"]], "y_llm": llm_y[lq],
                         "s_template": tp[q["question_id"]], "s_llm": llm_p[lq]})
    return pd.DataFrame(rows)


def evaluate() -> None:
    df = load_templates()
    pr = paired()
    rng = np.random.default_rng(SEED)
    diffs, dauc = [], []
    for _ in range(N_BOOT):
        b = pr.iloc[rng.integers(0, len(pr), len(pr))]
        diffs.append(b.y_llm.mean() - b.y_template.mean())
        if b.y_llm.nunique() > 1 and b.y_template.nunique() > 1:
            dauc.append(roc_auc_score(b.y_template, b.s_template) - roc_auc_score(b.y_llm, b.s_llm))
    ci = lambda v: [round(float(np.percentile(v, q)), 4) for q in (2.5, 97.5)]  # noqa: E731
    auc_t, auc_l = roc_auc_score(pr.y_template, pr.s_template), roc_auc_score(pr.y_llm, pr.s_llm)
    res = {
        "n_template_questions": int(len(df)),
        "base_rate": round(float(df.y.mean()), 4),
        "base_rate_by_type": df.groupby("source").y.mean().round(3).to_dict(),
        "G1_v3_pooled_auc": boot(df, _pooled, "v3_ens"),
        "G2_v3_within_type_auc": boot(df, _within, "v3_ens"),
        "per_type_auc": {s: round(_pooled(g.y.values, g.v3_ens.values), 4) for s, g in df.groupby("source")},
        "by_cohort": {c: round(_pooled(g.y.values, g.v3_ens.values), 4) for c, g in df.groupby("cohort")},
        "G3_paired_rate": {
            "n_clusters": int(len(pr)),
            "addressed_llm_phrased": round(float(pr.y_llm.mean()), 4),
            "addressed_template": round(float(pr.y_template.mean()), 4),
            "difference_llm_minus_template": round(float(pr.y_llm.mean() - pr.y_template.mean()), 4),
            "ci95": ci(diffs),
            "agreement_same_cluster": round(float((pr.y_llm == pr.y_template).mean()), 4),
        },
        "G4_auc_template_vs_llm_same_clusters": {
            "auc_template": round(float(auc_t), 4), "auc_llm_phrased": round(float(auc_l), 4),
            "delta_template_minus_llm": round(float(auc_t - auc_l), 4), "ci95": ci(dauc),
        },
    }
    (ROOT / "results" / "templates_leakage.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"label": label, "evaluate": evaluate}[sys.argv[1]]()
