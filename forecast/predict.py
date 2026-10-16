"""Fit Paper 3's predictors on Paper 3's labelled questions and score a cohort.

Two training sets, both from Paper 3's committed data (980 questions):

- ``asof2021``: cutoffs 2012, 2014, 2016 only. Their outcome windows end
  2017, 2019 and 2021, so this is exactly the model a forecaster could have
  fit on 2021-12-31. It is the primary model for the 2021 backtest: any
  later training label (cutoff 2018 -> 2023, cutoff 2020 -> 2025) overlaps
  the backtest's own outcome window 2022-2026 and would leak field dynamics.
- ``all``: all five cutoffs. Used for the prospective 2026 forecast, and
  reported as a secondary model on the backtest.

Scores written per question (all fitted on the training set named):

- ``m_logistic``     Paper 3's structured logistic (all six feature groups)
- ``m_gbm``          Paper 3's gradient-boosting model
- ``b_environment``  subfield-popularity baseline (environment features only)
- ``b_source``       training addressed-rate of the question's generation source
- ``b_text``         TF-IDF question-text baseline
- ``s_structure``    Paper 3's structure-only prior (tension questions only)
- Paper 4 planner utility and top-ranked action (tension questions only)

Usage:
    python -m forecast.predict backtest2021
    python -m forecast.predict prospective2026
    python -m forecast.predict paper2_prospective2026
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from forecast.common import PAPER3, read_jsonl, study_dir, write_jsonl

from pipeline import models  # noqa: E402  (Paper 3, vendored)



def _structure_columns() -> list[str]:
    from pipeline.structure import STRUCTURE_COLUMNS

    return STRUCTURE_COLUMNS + ["str_recurrent"]


TRAIN_SETS = {"asof2021": (2012, 2014, 2016), "all": (2012, 2014, 2016, 2018, 2020)}
# Round 2: a 2019 forecaster only has labels whose windows closed by 2019.
TRAIN_SETS_V2 = {"asof2019": (2012, 2014), "asof2017": (2012,), "asof2023": (2012, 2014, 2016, 2018)}
PRIMARY_TRAIN = {
    "backtest2017": "asof2017",  # cutoff-2012 labels end 2017-12-31
    "backtest2023": "asof2023",  # cutoff-2018 labels end 2023-12-31
    "backtest2019": "asof2019",
    "backtest2021": "asof2021",
    "backtest2022": "asof2021",  # cutoff-2016 labels end 2021-12-31; cutoff-2018 labels run to 2023
    "prospective2026": "all",
    "paper2_prospective2026": "all",
}


def paper3_table() -> pd.DataFrame:
    d = PAPER3 / "data"
    qs = pd.DataFrame(read_jsonl(d / "questions" / "questions_v1.jsonl"))
    fs = pd.DataFrame(read_jsonl(d / "features" / "features_v1.jsonl"))
    ls = pd.DataFrame(read_jsonl(d / "labels" / "labels_v1.jsonl"))
    st = pd.DataFrame(read_jsonl(d / "features" / "structure_features_v1.jsonl"))
    df = qs.merge(fs, on="question_id").merge(
        ls[["question_id", "addressed", "answer_status", "future_paper_count"]], on="question_id"
    )
    df = df.merge(st, on="question_id", how="left")
    df["y_addressed"] = df["addressed"].astype(int)
    return df


def cohort_table(name: str) -> pd.DataFrame:
    d = study_dir(name)
    qs = pd.DataFrame(read_jsonl(d / "questions.jsonl"))
    fs = pd.DataFrame(read_jsonl(d / "features.jsonl"))
    df = qs.merge(fs, on="question_id")
    sp = d / "structure_features.jsonl"
    if sp.exists() and sp.stat().st_size:
        df = df.merge(pd.DataFrame(read_jsonl(sp)), on="question_id", how="left")
    return df


def fit_and_score(train: pd.DataFrame, test: pd.DataFrame, tag: str) -> pd.DataFrame:
    cols = models.feature_columns(train)
    missing = [c for c in cols if c not in test.columns]
    if missing:
        raise ValueError(f"cohort lacks Paper 3 features: {missing}")
    y = train["y_addressed"].values
    out = pd.DataFrame({"question_id": test["question_id"].values})

    for kind, col in (("logistic", "m_logistic"), ("gbm", "m_gbm")):
        m = models.make_model(kind)
        m.fit(train[cols], y)
        out[f"{col}__{tag}"] = m.predict_proba(test[cols])[:, 1]

    env = models.feature_columns(train, ["environment"])
    m = models.make_model("logistic").fit(train[env], y)
    out[f"b_environment__{tag}"] = m.predict_proba(test[env])[:, 1]

    rates = train.groupby("source")["y_addressed"].mean().to_dict()
    overall = float(train["y_addressed"].mean())
    out[f"b_source__{tag}"] = [rates.get(s, overall) for s in test["source"]]
    out[f"b_constant__{tag}"] = overall

    vec = TfidfVectorizer(stop_words="english", max_features=3000, sublinear_tf=True)
    clf = LogisticRegression(max_iter=5000, C=1.0).fit(vec.fit_transform(train["question"]), y)
    out[f"b_text__{tag}"] = clf.predict_proba(vec.transform(test["question"]))[:, 1]

    scols = _structure_columns()
    tr_s = train.dropna(subset=["str_n_claims"])
    te_mask = test["str_n_claims"].notna().values if "str_n_claims" in test.columns else np.zeros(len(test), bool)
    s_scores = np.full(len(test), np.nan)
    if te_mask.any():
        scaler = StandardScaler().fit(tr_s[scols])
        sclf = LogisticRegression(max_iter=5000).fit(scaler.transform(tr_s[scols]), tr_s["y_addressed"])
        s_scores[te_mask] = sclf.predict_proba(scaler.transform(test.loc[te_mask, scols]))[:, 1]
    out[f"s_structure__{tag}"] = s_scores
    return out


def explain(train: pd.DataFrame, test: pd.DataFrame, k: int = 4) -> list[dict]:
    """Per-question top +/- standardized contributions of the logistic model
    (Paper 3's prediction-card format)."""
    cols = models.feature_columns(train)
    m = models.make_model("logistic").fit(train[cols], train["y_addressed"].values)
    scaler, clf = m.named_steps["scale"], m.named_steps["clf"]
    contrib = scaler.transform(test[cols]) * clf.coef_[0]
    cards = []
    for row in contrib:
        order = np.argsort(row)
        cards.append(
            {
                "main_positive_factors": [
                    {"feature": cols[i], "contribution": round(float(row[i]), 3)} for i in order[::-1][:k] if row[i] > 0
                ],
                "main_negative_factors": [
                    {"feature": cols[i], "contribution": round(float(row[i]), 3)} for i in order[:k] if row[i] < 0
                ],
            }
        )
    return cards


def main() -> None:
    name = sys.argv[1]
    train_all = paper3_table()
    test = cohort_table(name)
    scores = test[["question_id", "question", "source", "subfield", "cutoff_date"]].copy()
    sets = dict(TRAIN_SETS)
    if name in ("backtest2017", "backtest2019", "backtest2022", "backtest2023"):  # 2021's frozen file stays as it was
        sets.update(TRAIN_SETS_V2)
    for tag, cutoffs in sets.items():
        s = fit_and_score(train_all[train_all.cutoff_year.isin(cutoffs)], test, tag)
        scores = scores.merge(s, on="question_id")
    primary = PRIMARY_TRAIN[name]
    scores["p_attention"] = scores[f"m_logistic__{primary}"]
    scores["primary_training_set"] = primary

    cards = explain(train_all[train_all.cutoff_year.isin({**TRAIN_SETS, **TRAIN_SETS_V2}[primary])], test)
    plans = {}
    pp = study_dir(name) / "planner.jsonl"
    if pp.exists():
        for p in read_jsonl(pp):
            plans.setdefault(p["question_id"], {})[p["planner_config"]] = p

    rows = []
    for rec, card in zip(scores.to_dict(orient="records"), cards):
        rec = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in rec.items()}
        plan = plans.get(rec["question_id"], {})
        for cfg, p in plan.items():
            rec[f"p4_top_k_utility__{cfg}"] = p["top_k_utility"]
            rec[f"p4_top_action__{cfg}"] = p["recommendations"][0]["action_type"] if p["recommendations"] else None
        rec.update(card)
        rows.append(rec)
    out = study_dir(name) / "predictions.jsonl"
    write_jsonl(out, rows)
    s = pd.DataFrame(rows)
    print(f"[predict] {name}: {len(rows)} predictions -> {out}")
    print(s.groupby("source")["p_attention"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
