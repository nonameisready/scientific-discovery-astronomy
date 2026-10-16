"""Round-3 evaluation (docs/PREREGISTRATION_v3.md): T1-T6 on the fresh 2017
and 2023 cohorts pooled, plus a descriptive five-cohort view.

Usage:
    python -m forecast.evaluate_v3
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from forecast.common import ROOT, read_jsonl, study_dir
from forecast.evaluate_v2 import _pooled, _strata, _within, boot, brier
from forecast.predict import PRIMARY_TRAIN

FRESH = ("backtest2017", "backtest2023")
ALL = ("backtest2017", "backtest2019", "backtest2021", "backtest2022", "backtest2023")
DEV_FOR_V3 = ("backtest2019", "backtest2021", "backtest2022")
MODELS = {
    "v1": "m_logistic",
    "source_prior": "b_source",
    "constant": "b_constant",
    "v2_embed_src": "v2_embed_src",
    "v2_ens_cal": "v2_ens_cal",
    "v3_dm_src": "v3_dm_src",
    "v3_ens": "v3_ens",
    "v3_ens_cal": "v3_ens_cal",
}


def load_cohort(name: str, judge: str) -> pd.DataFrame:
    d = study_dir(name)
    tag = PRIMARY_TRAIN[name]
    df = pd.DataFrame(read_jsonl(d / "predictions.jsonl"))
    for v in ("v2", "v3"):
        df = df.merge(pd.DataFrame(read_jsonl(d / f"predictions_{v}.jsonl")).drop(columns=["source", "subfield"]),
                      on="question_id")
    lab = pd.DataFrame(read_jsonl(d / ("labels_L2.jsonl" if judge == "gpt-4o" else "labels_L1.jsonl")))
    df = df.merge(lab[["question_id", "addressed"]], on="question_id")
    out = pd.DataFrame({"question_id": df.question_id, "cohort": name, "source": df.source,
                        "subfield": df.subfield, "y": df.addressed.astype(int)})
    for k, col in MODELS.items():
        out[k] = df[f"{col}__{tag}"].astype(float).values
    return out


def report(df: pd.DataFrame) -> dict:
    t = df[df.source == "evidence_tension"]
    return {
        "n": int(len(df)),
        "base_rate": round(float(df.y.mean()), 4),
        "base_rate_by_cohort": df.groupby("cohort").y.mean().round(3).to_dict(),
        "T1_v3_within_source": boot(df, _within, "v3_ens"),
        "T2_v3_vs_v2_within_source": boot(df, _within, "v3_ens", ref="v2_embed_src"),
        "T3_v3_vs_v1_within_source": boot(df, _within, "v3_ens", ref="v1"),
        "T4_v3_vs_source_prior_pooled": boot(df, _pooled, "v3_ens", ref="source_prior"),
        "T5_brier": {m: brier(df, m) for m in ("v3_ens_cal", "v2_ens_cal", "v1", "source_prior", "constant")},
        "T6_v3_tension_auc": boot(t, _pooled, "v3_ens"),
        "all_models": {
            m: {"pooled": round(_pooled(df.y.values, df[m].values), 4),
                "within_source": round(_within(df.y.values, df[m].values, _strata(df)), 4),
                "tension": round(_pooled(t.y.values, t[m].values), 4), "brier": brier(df, m)}
            for m in MODELS if m != "constant"
        },
        "per_source_auc": {
            m: {s: round(_pooled(g.y.values, g[m].values), 4) for s, g in df.groupby("source")}
            for m in ("v1", "v2_embed_src", "v3_ens")
        },
        "by_cohort": {
            c: {m: {"pooled": round(_pooled(g.y.values, g[m].values), 4),
                    "within_source": round(_within(g.y.values, g[m].values, _strata(g)), 4)}
                for m in ("v1", "source_prior", "v2_embed_src", "v3_ens", "v3_ens_cal")}
            for c, g in df.groupby("cohort")
        },
    }


def figure(df_all: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    models = [("v1", "v1 Paper 3"), ("source_prior", "source prior"), ("v2_embed_src", "v2 embed+source"),
              ("v3_ens", "v3 embed+momentum")]
    w = 0.2
    for k, (m, lab) in enumerate(models):
        for ax, stat in ((axes[0], "pooled"), (axes[1], "within")):
            vals = []
            for c in ALL:
                g = df_all[df_all.cohort == c]
                vals.append(_pooled(g.y.values, g[m].values) if stat == "pooled"
                            else _within(g.y.values, g[m].values, _strata(g)))
            ax.bar(np.arange(len(ALL)) + (k - 1.5) * w, vals, w, label=lab)
    labels = [c[-4:] + ("\n(test)" if c in FRESH else "\n(v3 dev)") for c in ALL]
    for ax, title in ((axes[0], "Pooled AUC"), (axes[1], "Within-source AUC")):
        ax.axhline(0.5, color="k", lw=0.8, ls="--")
        ax.set_xticks(range(len(ALL)), labels)
        ax.set_ylim(0.3, 0.9)
        ax.set_title(title + " by cutoff")
    axes[0].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    out = ROOT / "results" / "round3"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "auc_by_cohort.png", dpi=150)


def main() -> None:
    out = ROOT / "results" / "round3"
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for judge in ("gpt-4o", "gpt-4o-mini"):
        fresh = pd.concat([load_cohort(c, judge) for c in FRESH], ignore_index=True)
        allc = pd.concat([load_cohort(c, judge) for c in ALL], ignore_index=True)
        results[judge] = {"fresh_2017_2023": report(fresh), "all_five_descriptive": report(allc)}
        if judge == "gpt-4o":
            allc.to_csv(out / "per_question.csv", index=False)
            figure(allc)
    (out / "evaluation.json").write_text(json.dumps(results, indent=2))
    r = results["gpt-4o"]["fresh_2017_2023"]
    print(json.dumps({k: r[k] for k in r if k.startswith(("T", "base"))}, indent=1))


if __name__ == "__main__":
    main()
