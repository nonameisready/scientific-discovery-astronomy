"""Evaluate frozen backtest predictions against outcome labels (H1-H7).

Usage:
    python -m forecast.evaluate backtest2021
"""

from __future__ import annotations

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from forecast.common import ROOT, read_jsonl, study_dir

N_BOOT = 2000
SEED = 7
N_PERM = 5000


def auc(y, s) -> float:
    y, s = np.asarray(y), np.asarray(s, float)
    return float(roc_auc_score(y, s)) if len(np.unique(y)) > 1 else float("nan")


def boot_auc(y, s, ref=None, strata=None) -> dict:
    """AUC with percentile bootstrap CI; paired difference vs ``ref`` if given.
    ``strata`` resamples within groups (keeps the source mix fixed)."""
    rng = np.random.default_rng(SEED)
    y, s = np.asarray(y), np.asarray(s, float)
    ref = None if ref is None else np.asarray(ref, float)
    idx_groups = [np.arange(len(y))] if strata is None else [np.flatnonzero(strata == g) for g in np.unique(strata)]
    vals, diffs = [], []
    for _ in range(N_BOOT):
        idx = np.concatenate([rng.choice(g, len(g), replace=True) for g in idx_groups])
        if len(np.unique(y[idx])) < 2:
            continue
        a = roc_auc_score(y[idx], s[idx])
        vals.append(a)
        if ref is not None:
            diffs.append(a - roc_auc_score(y[idx], ref[idx]))
    out = {"auc": round(auc(y, s), 4), "ci95": [round(float(np.percentile(vals, q)), 4) for q in (2.5, 97.5)]}
    if ref is not None:
        out["delta_vs_ref"] = round(auc(y, s) - auc(y, ref), 4)
        out["delta_ci95"] = [round(float(np.percentile(diffs, q)), 4) for q in (2.5, 97.5)]
    return out


def within_source_auc(df: pd.DataFrame, score: str, y: str) -> dict:
    """Mean of per-source AUCs (sources with both outcome classes), with a
    bootstrap that resamples within each source."""
    def stat(d):
        aucs = [auc(g[y], g[score]) for _, g in d.groupby("source") if g[y].nunique() > 1]
        return float(np.mean(aucs)) if aucs else float("nan")

    rng = np.random.default_rng(SEED)
    groups = [g for _, g in df.groupby("source")]
    vals = []
    for _ in range(N_BOOT):
        d = pd.concat([g.sample(len(g), replace=True, random_state=int(rng.integers(1 << 31))) for g in groups])
        v = stat(d)
        if not np.isnan(v):
            vals.append(v)
    per = {s: round(auc(g[y], g[score]), 4) for s, g in df.groupby("source") if g[y].nunique() > 1}
    return {"mean_within_source_auc": round(stat(df), 4),
            "ci95": [round(float(np.percentile(vals, q)), 4) for q in (2.5, 97.5)], "per_source": per}


def load(name: str) -> pd.DataFrame:
    d = study_dir(name)
    pred = pd.DataFrame(read_jsonl(d / "predictions.jsonl"))
    l1 = pd.DataFrame(read_jsonl(d / "labels_L1.jsonl"))
    l2 = pd.DataFrame(read_jsonl(d / "labels_L2.jsonl"))
    cit = pd.DataFrame(read_jsonl(d / "labels_citation.jsonl"))
    df = pred.merge(
        l1[["question_id", "addressed", "answer_status", "premise_status", "future_paper_count", "lead_time_months"]],
        on="question_id",
    )
    df["y_L1"] = df["addressed"].astype(int)
    df = df.merge(l2[["question_id", "addressed"]].rename(columns={"addressed": "addressed_L2"}), on="question_id")
    df["y_L2"] = df["addressed_L2"].astype(int)
    df = df.merge(cit[["question_id", "addressed", "n_candidates"]].rename(
        columns={"addressed": "addressed_cit", "n_candidates": "n_citing_candidates"}), on="question_id")
    df["y_L3"] = (df["y_L1"].astype(bool) | df["addressed_cit"].fillna(False).astype(bool)).astype(int)
    return df


def hypotheses(df: pd.DataFrame, y: str) -> dict:
    p = "m_logistic__asof2021"
    res: dict = {"label": y, "n": int(len(df)), "base_rate": round(float(df[y].mean()), 4)}
    res["H1_primary_auc"] = boot_auc(df[y], df[p])
    res["H2_vs_environment"] = boot_auc(df[y], df[p], ref=df["b_environment__asof2021"])
    res["H2_vs_source"] = boot_auc(df[y], df[p], ref=df["b_source__asof2021"])
    res["H3_within_source"] = within_source_auc(df, p, y)
    res["H4_brier"] = {
        "model": round(float(brier_score_loss(df[y], df[p])), 4),
        "constant_training_base_rate": round(float(brier_score_loss(df[y], df["b_constant__asof2021"])), 4),
        "mean_predicted": round(float(df[p].mean()), 4),
        "observed_rate": round(float(df[y].mean()), 4),
    }
    t = df[df["s_structure__asof2021"].notna()]
    res["H5_structure_prior_tension"] = boot_auc(t[y], t["s_structure__asof2021"]) if t[y].nunique() > 1 else None
    res["H6_planner_utility"] = {
        cfg: boot_auc(t[y], t[f"p4_top_k_utility__{cfg}"])
        for cfg in ("default", "paper3_informed")
        if f"p4_top_k_utility__{cfg}" in t and t[y].nunique() > 1
    }
    res["all_scores"] = {
        c: boot_auc(df[y], df[c])
        for c in df.columns
        if "__" in c and not c.startswith(("p4_top_action", "s_structure", "p4_top_k", "b_constant"))
    }
    res["by_source"] = {
        s: {"n": int(len(g)), "rate": round(float(g[y].mean()), 3), "mean_p": round(float(g[p].mean()), 3)}
        for s, g in df.groupby("source")
    }
    q = pd.qcut(df[p].rank(method="first"), 5, labels=False)
    res["quintiles"] = [
        {"quintile": int(k + 1), "n": int((q == k).sum()), "mean_p": round(float(df[p][q == k].mean()), 3),
         "observed_rate": round(float(df[y][q == k].mean()), 3)}
        for k in range(5)
    ]
    return res


def h7_actions(name: str, df: pd.DataFrame) -> dict:
    rows = read_jsonl(study_dir(name) / "action_types.jsonl")
    obs = {r["question_id"]: set(r["action_types"]) for r in rows if r["action_types"]}
    out = {}
    for cfg in ("default", "paper3_informed"):
        col = f"p4_top_action__{cfg}"
        sub = df[df["question_id"].isin(obs) & df[col].notna()]
        if sub.empty:
            continue
        top = sub[col].tolist()
        sets = [obs[q] for q in sub["question_id"]]
        match = float(np.mean([t in s for t, s in zip(top, sets)]))
        rng = np.random.default_rng(SEED)
        null = []
        for _ in range(N_PERM):
            perm = rng.permutation(top)
            null.append(np.mean([t in s for t, s in zip(perm, sets)]))
        counts: dict[str, int] = {}
        for s in sets:
            for t in s:
                counts[t] = counts.get(t, 0) + 1
        best = max(counts, key=counts.get)
        out[cfg] = {
            "n_questions": len(sub),
            "planner_top1_distribution": pd.Series(top).value_counts().to_dict(),
            "observed_type_counts": counts,
            "top1_match_rate": round(match, 4),
            "permutation_null_mean": round(float(np.mean(null)), 4),
            "permutation_p_one_sided": round(float((np.sum(np.array(null) >= match) + 1) / (N_PERM + 1)), 4),
            "oracle_constant_guess": {"type": best, "match_rate": round(float(np.mean([best in s for s in sets])), 4)},
        }
    return out


def figure(df: pd.DataFrame, name: str) -> None:
    from sklearn.metrics import roc_curve

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for col, lab in (
        ("m_logistic__asof2021", "Paper 3 logistic (as of 2021)"),
        ("m_logistic__all", "Paper 3 logistic (all cutoffs)"),
        ("b_source__asof2021", "baseline: source prior"),
        ("b_environment__asof2021", "baseline: subfield popularity"),
    ):
        fpr, tpr, _ = roc_curve(df["y_L1"], df[col])
        axes[0].plot(fpr, tpr, label=f"{lab}  AUC={auc(df['y_L1'], df[col]):.2f}")
    axes[0].plot([0, 1], [0, 1], "k--", lw=0.8)
    axes[0].set(xlabel="false positive rate", ylabel="true positive rate", title="2021 cohort, label L1")
    axes[0].legend(fontsize=7, loc="lower right")
    q = pd.qcut(df["m_logistic__asof2021"].rank(method="first"), 5, labels=False)
    for y, lab in (("y_L1", "L1"), ("y_L2", "L2"), ("y_L3", "L3")):
        axes[1].plot(range(1, 6), [df[y][q == k].mean() for k in range(5)], marker="o", label=f"observed {lab}")
    axes[1].plot(range(1, 6), [df["m_logistic__asof2021"][q == k].mean() for k in range(5)], "k--", marker="x",
                 label="mean predicted")
    axes[1].set(xlabel="predicted-attention quintile", ylabel="rate addressed by 2026-10", title="Calibration by quintile")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    out = ROOT / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "backtest_roc_calibration.png", dpi=150)


def main() -> None:
    name = sys.argv[1]
    df = load(name)
    results = {y: hypotheses(df, y) for y in ("y_L1", "y_L2", "y_L3")}
    results["H7_planner_action_match"] = h7_actions(name, df)
    results["label_agreement"] = {
        "L1_vs_L2_agreement": round(float((df.y_L1 == df.y_L2).mean()), 4),
        "L1_vs_L2_kappa": round(float(_kappa(df.y_L1, df.y_L2)), 4),
        "L3_minus_L1_rate": round(float(df.y_L3.mean() - df.y_L1.mean()), 4),
        "answer_status_L1": df["answer_status"].value_counts().to_dict(),
    }
    out = ROOT / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "evaluation.json").write_text(json.dumps(results, indent=2))
    df.drop(columns=["main_positive_factors", "main_negative_factors"]).to_csv(out / "per_question.csv", index=False)
    figure(df, name)
    print(json.dumps({y: {k: results[y][k] for k in ("base_rate", "H1_primary_auc", "H2_vs_environment",
                                                     "H2_vs_source", "H4_brier")} for y in ("y_L1", "y_L2", "y_L3")},
                     indent=1))


def _kappa(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    po = np.mean(a == b)
    pe = np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b))
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


if __name__ == "__main__":
    main()
