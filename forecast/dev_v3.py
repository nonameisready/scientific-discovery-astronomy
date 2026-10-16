"""Round-3 development: candidate within-source rankers, compared on data
whose labels are already known (so these numbers are NOT test evidence).

Two development views:
- ``dev_cohorts``: the 2019 / 2021 / 2022 cohorts, each scored by models
  fitted on its own leak-free Paper 3 training set (as in round 2);
- ``paper3_loco``: Paper 3's 980 questions, leave-one-cutoff-out.

Metric of interest: within-source AUC (mean over cutoff x source strata).

Usage:
    python -m forecast.dev_v3
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from forecast.common import ROOT, read_jsonl, study_dir
from forecast.models_v2 import SOURCES, embed, source_dummies
from forecast.predict import PRIMARY_TRAIN, TRAIN_SETS, TRAIN_SETS_V2, cohort_table, paper3_table

from pipeline import models  # noqa: E402

DEV = ("backtest2019", "backtest2021", "backtest2022")


def with_momentum(df: pd.DataFrame, path) -> pd.DataFrame:
    return df.merge(pd.DataFrame(read_jsonl(path)), on="question_id", how="left")


def p3_cols(df):
    return models.feature_columns(df)


def dm_cols(df):
    return [c for c in df.columns if c.startswith("dm_")]


def demean(X: np.ndarray, groups: np.ndarray) -> np.ndarray:
    X = X.copy()
    for g in np.unique(groups):
        m = groups == g
        X[m] -= X[m].mean(axis=0)
    return X


# ---------------------------------------------------------------- models
# Each returns (pooled_score, within_score) on the test frame; within_score
# only has to rank correctly inside a (cutoff, source) stratum.


def m_v2_embed(tr, te, C=10.0):
    Xtr = np.column_stack([embed(tr.question.tolist()), source_dummies(tr)])
    Xte = np.column_stack([embed(te.question.tolist()), source_dummies(te)])
    s = LogisticRegression(max_iter=5000, C=C).fit(Xtr, tr.y).decision_function(Xte)
    return s, s


def _lr(cols, C=1.0, fe=True):
    def f(tr, te):
        Xtr, Xte = tr[cols].values, te[cols].values
        sc = StandardScaler().fit(Xtr)
        Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
        if fe:
            Xtr, Xte = np.column_stack([Xtr, source_dummies(tr)]), np.column_stack([Xte, source_dummies(te)])
        s = LogisticRegression(max_iter=5000, C=C).fit(Xtr, tr.y).decision_function(Xte)
        return s, s
    return f


def _cond(cols, C=1.0):
    """Within-stratum (conditional) logistic: features demeaned inside each
    training (cutoff, source) stratum, so only within-stratum contrasts are
    learned. Pooled score adds the source prior's log-odds."""
    def f(tr, te):
        sc = StandardScaler().fit(tr[cols].values)
        g = (tr.cutoff_year.astype(str) + "|" + tr.source).values
        Xtr = demean(sc.transform(tr[cols].values), g)
        ytr = tr.y.values - pd.Series(tr.y.values).groupby(g).transform("mean").values
        clf = LogisticRegression(max_iter=5000, C=C).fit(Xtr, tr.y)  # slope from demeaned X
        w = sc.transform(te[cols].values) @ clf.coef_[0]
        rate = tr.groupby("source").y.mean()
        prior = np.log(te.source.map(rate).fillna(tr.y.mean()).clip(0.02, 0.98).values)
        prior = prior - np.log(1 - np.exp(prior))
        _ = ytr
        return prior + w, w
    return f


def _ens(*fs):
    def f(tr, te):
        outs = [fn(tr, te) for fn in fs]
        z = lambda v: (v - v.mean()) / (v.std() + 1e-9)  # noqa: E731
        return (sum(z(o[0]) for o in outs) / len(outs), sum(z(o[1]) for o in outs) / len(outs))
    return f


def candidates(df):
    p3, dm = p3_cols(df), dm_cols(df)
    return {
        "v2_embed_src": m_v2_embed,
        "p3_src": _lr(p3),
        "dm_src": _lr(dm),
        "p3+dm_src": _lr(p3 + dm),
        "cond_dm": _cond(dm),
        "cond_p3+dm": _cond(p3 + dm, C=0.3),
        "ens_embed+dm": _ens(m_v2_embed, _lr(dm)),
        "ens_embed+cond_dm": _ens(m_v2_embed, _cond(dm)),
        "ens_embed+p3dm": _ens(m_v2_embed, _lr(p3 + dm)),
    }


def within_auc(te, s):
    aucs = [roc_auc_score(g.y, s[g.index]) for _, g in te.groupby(["cutoff_year", "source"]) if g.y.nunique() > 1]
    return float(np.mean(aucs)), len(aucs)


def main() -> None:
    p3 = with_momentum(paper3_table(), ROOT / "data" / "paper3_momentum.jsonl")
    p3["y"] = p3.y_addressed
    p3 = p3[p3.source.isin(SOURCES)].reset_index(drop=True)
    res = {"dev_cohorts": {}, "paper3_loco": {}}
    cands = candidates(p3)

    for name in DEV:
        tag = PRIMARY_TRAIN[name]
        tr = p3[p3.cutoff_year.isin({**TRAIN_SETS, **TRAIN_SETS_V2}[tag])].reset_index(drop=True)
        te = with_momentum(cohort_table(name), study_dir(name) / "momentum.jsonl")
        lab = pd.DataFrame(read_jsonl(study_dir(name) / "labels_L2.jsonl"))[["question_id", "addressed"]]
        te = te.merge(lab, on="question_id").reset_index(drop=True)
        te["y"] = te.addressed.astype(int)
        for k, f in cands.items():
            pooled, within = f(tr, te)
            res["dev_cohorts"].setdefault(k, {})[name] = {
                "pooled": round(roc_auc_score(te.y, pooled), 4),
                "within": round(within_auc(te, pd.Series(within))[0], 4),
            }
    for cy in sorted(p3.cutoff_year.unique()):
        tr, te = p3[p3.cutoff_year != cy].reset_index(drop=True), p3[p3.cutoff_year == cy].reset_index(drop=True)
        for k, f in cands.items():
            pooled, within = f(tr, te)
            res["paper3_loco"].setdefault(k, {})[int(cy)] = {
                "pooled": round(roc_auc_score(te.y, pooled), 4),
                "within": round(within_auc(te, pd.Series(within))[0], 4),
            }
    rows = []
    for k in cands:
        d, l = res["dev_cohorts"][k], res["paper3_loco"][k]
        rows.append({
            "model": k,
            "dev_within": np.mean([v["within"] for v in d.values()]),
            "dev_pooled": np.mean([v["pooled"] for v in d.values()]),
            "loco_within": np.mean([v["within"] for v in l.values()]),
            "loco_pooled": np.mean([v["pooled"] for v in l.values()]),
            **{f"w{n[-4:]}": d[n]["within"] for n in DEV},
        })
    table = pd.DataFrame(rows).round(3)
    print(table.to_string(index=False))
    out = ROOT / "results" / "round3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dev_v3.json").write_text(json.dumps({"summary": table.to_dict(orient="records"), **res}, indent=2))


if __name__ == "__main__":
    main()
