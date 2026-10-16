"""Round-2 evaluation (docs/PREREGISTRATION_v2.md): R1-R6 on the fresh 2019 and
2022 cohorts pooled, plus a descriptive three-cohort view including 2021.

Usage:
    python -m forecast.evaluate_v2
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from forecast.common import ROOT, read_jsonl, study_dir
from forecast.predict import PRIMARY_TRAIN

N_BOOT = 2000
SEED = 7
FRESH = ("backtest2019", "backtest2022")
ALL = ("backtest2019", "backtest2021", "backtest2022")
MODELS = {
    "v1": "m_logistic",
    "source_prior": "b_source",
    "constant": "b_constant",
    "text_tfidf": "b_text",
    "v1_gbm": "m_gbm",
    "v2_struct_src": "v2_struct_src",
    "v2_embed_src": "v2_embed_src",
    "v2_ens": "v2_ens",
    "v2_ens_cal": "v2_ens_cal",
}


def load_cohort(name: str, judge: str) -> pd.DataFrame:
    d = study_dir(name)
    tag = PRIMARY_TRAIN[name]
    v1 = pd.DataFrame(read_jsonl(d / "predictions.jsonl"))
    v2 = pd.DataFrame(read_jsonl(d / "predictions_v2.jsonl")).drop(columns=["source", "subfield"])
    lab = pd.DataFrame(read_jsonl(d / ("labels_L2.jsonl" if judge == "gpt-4o" else "labels_L1.jsonl")))
    df = v1.merge(v2, on="question_id").merge(lab[["question_id", "addressed"]], on="question_id")
    out = pd.DataFrame({"question_id": df.question_id, "cohort": name, "source": df.source,
                        "subfield": df.subfield, "y": df.addressed.astype(int)})
    for k, col in MODELS.items():
        out[k] = df[f"{col}__{tag}"].astype(float).values
    return out


def _strata(df):
    return [np.flatnonzero(((df.cohort == c) & (df.source == s)).values)
            for c, s in sorted(set(zip(df.cohort, df.source)))]


def _within(y, s, strata):
    a = [roc_auc_score(y[i], s[i]) for i in strata if len(np.unique(y[i])) > 1]
    return float(np.mean(a)) if a else float("nan")


def _pooled(y, s, _strata_unused=None):
    return float(roc_auc_score(y, s)) if len(np.unique(y)) > 1 else float("nan")


def boot(df: pd.DataFrame, stat, model: str, ref: str | None = None) -> dict:
    rng = np.random.default_rng(SEED)
    y = df.y.values
    strata = _strata(df)
    s, r = df[model].values, (df[ref].values if ref else None)
    point = stat(y, s, strata)
    vals, diffs = [], []
    for _ in range(N_BOOT):
        idx = np.concatenate([rng.choice(i, len(i), replace=True) for i in strata])
        # re-index strata inside the resample
        yy, ss = y[idx], s[idx]
        offs = np.cumsum([0] + [len(i) for i in strata])
        st = [np.arange(offs[k], offs[k + 1]) for k in range(len(strata))]
        v = stat(yy, ss, st)
        if np.isnan(v):
            continue
        vals.append(v)
        if ref:
            diffs.append(v - stat(yy, r[idx], st))
    out = {"value": round(point, 4), "ci95": [round(float(np.percentile(vals, q)), 4) for q in (2.5, 97.5)]}
    if ref:
        out["ref"] = ref
        out["delta"] = round(point - stat(y, r, strata), 4)
        out["delta_ci95"] = [round(float(np.percentile(diffs, q)), 4) for q in (2.5, 97.5)]
    return out


def brier(df, m):
    return round(float(np.mean((df[m] - df.y) ** 2)), 4)


def report(df: pd.DataFrame) -> dict:
    t = df[df.source == "evidence_tension"]
    res = {
        "n": int(len(df)),
        "base_rate": round(float(df.y.mean()), 4),
        "base_rate_by_cohort": df.groupby("cohort").y.mean().round(3).to_dict(),
        "R1_v1_pooled_auc": boot(df, _pooled, "v1"),
        "R1_v1_auc_by_cohort": {c: round(_pooled(g.y.values, g.v1.values), 4) for c, g in df.groupby("cohort")},
        "R2_v2_within_source": boot(df, _within, "v2_embed_src"),
        "R3_v2_vs_v1_within_source": boot(df, _within, "v2_embed_src", ref="v1"),
        "R4_v2_vs_source_prior_pooled": boot(df, _pooled, "v2_embed_src", ref="source_prior"),
        "R5_brier": {m: brier(df, m) for m in ("v2_ens_cal", "v1", "constant", "source_prior", "v2_embed_src")},
        "R6_v2_tension_auc": boot(t, _pooled, "v2_embed_src"),
        "all_models": {
            m: {"pooled": boot(df, _pooled, m), "within_source": boot(df, _within, m),
                "tension": round(_pooled(t.y.values, t[m].values), 4), "brier": brier(df, m)}
            for m in MODELS if m != "constant"
        },
        "per_source_auc": {
            m: {s: round(_pooled(g.y.values, g[m].values), 4) for s, g in df.groupby("source")}
            for m in ("v1", "v2_embed_src", "v2_ens_cal")
        },
        "by_cohort": {
            c: {m: {"pooled": round(_pooled(g.y.values, g[m].values), 4),
                    "within_source": round(_within(g.y.values, g[m].values, _strata(g)), 4)}
                for m in ("v1", "source_prior", "text_tfidf", "v2_embed_src", "v2_ens_cal")}
            for c, g in df.groupby("cohort")
        },
    }
    return res


def figure(df_all: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    models = [("v1", "Paper 3 v1"), ("source_prior", "source prior"), ("text_tfidf", "TF-IDF text"),
              ("v2_embed_src", "v2 embed+source"), ("v2_ens_cal", "v2 ensemble (cal.)")]
    cohorts = list(ALL)
    w = 0.16
    for k, (m, lab) in enumerate(models):
        for ax, stat in ((axes[0], "pooled"), (axes[1], "within")):
            vals = []
            for c in cohorts:
                g = df_all[df_all.cohort == c]
                vals.append(_pooled(g.y.values, g[m].values) if stat == "pooled"
                            else _within(g.y.values, g[m].values, _strata(g)))
            ax.bar(np.arange(len(cohorts)) + (k - 2) * w, vals, w, label=lab)
    for ax, title in ((axes[0], "Pooled AUC"), (axes[1], "Within-source AUC")):
        ax.axhline(0.5, color="k", lw=0.8, ls="--")
        ax.set_xticks(range(len(cohorts)), [c.replace("backtest", "cutoff ") + (" (dev)" if c == "backtest2021" else "")
                                            for c in cohorts])
        ax.set_ylim(0.3, 0.9)
        ax.set_title(title)
    axes[0].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    out = ROOT / "results" / "round2"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "auc_by_cohort.png", dpi=150)


def main() -> None:
    out = ROOT / "results" / "round2"
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for judge in ("gpt-4o", "gpt-4o-mini"):
        fresh = pd.concat([load_cohort(c, judge) for c in FRESH], ignore_index=True)
        allc = pd.concat([load_cohort(c, judge) for c in ALL], ignore_index=True)
        results[judge] = {"fresh_2019_2022": report(fresh), "all_three_descriptive": report(allc)}
        if judge == "gpt-4o":
            allc.to_csv(out / "per_question.csv", index=False)
            figure(allc)
    (out / "evaluation.json").write_text(json.dumps(results, indent=2))
    r = results["gpt-4o"]["fresh_2019_2022"]
    print(json.dumps({k: r[k] for k in r if k.startswith(("R", "base"))}, indent=1))


if __name__ == "__main__":
    main()
