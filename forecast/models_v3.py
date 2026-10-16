"""Version-3 predictor: v2's embedding model + topic-momentum model.

Chosen on development data (docs/PREREGISTRATION_v3.md; results/round3/
dev_v3.json): adding the dense-retrieval momentum features
(``forecast.momentum``) to v2's embedding model raised within-source AUC
from 0.646 to 0.701 on the 2019/2021/2022 cohorts and from 0.689 to 0.728
leave-one-cutoff-out on Paper 3's questions.

- ``v3_dm_src``   momentum features (standardized) + source one-hot, logistic (C=1)
- ``v3_ens``      mean log-odds of ``v3_dm_src`` and v2's ``v2_embed_src``
- ``v3_ens_cal``  ``v3_ens`` Platt-calibrated on out-of-fold training predictions
                  (leave-one-cutoff-out; 5-fold CV when the training set has a
                  single cutoff)

The embedding model's C is chosen by leave-one-cutoff-out AUC as in v2, and
fixed at 10 (v2's development choice) when there is only one training cutoff.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from forecast.models_v2 import _Embed, choose_C, source_dummies

DM_COLS = ["dm_top10", "dm_top50", "dm_n_lo", "dm_n_hi", "dm_share_lo", "dm_recent_top50",
           "dm_age_top20", "dm_growth", "dm_recent_n"]


class _Momentum:
    def fit(self, df, y):
        self.sc = StandardScaler().fit(df[DM_COLS].values)
        self.m = LogisticRegression(max_iter=5000, C=1.0)
        self.m.fit(np.column_stack([self.sc.transform(df[DM_COLS].values), source_dummies(df)]), y)
        return self

    def logit(self, df):
        return self.m.decision_function(np.column_stack([self.sc.transform(df[DM_COLS].values), source_dummies(df)]))


def _folds(train: pd.DataFrame):
    if train["cutoff_year"].nunique() >= 2:
        for cy in sorted(train["cutoff_year"].unique()):
            te = (train["cutoff_year"] == cy).values
            yield ~te, te
    else:
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
        for a, b in skf.split(train, train["y_addressed"]):
            tr, te = np.zeros(len(train), bool), np.zeros(len(train), bool)
            tr[a], te[b] = True, True
            yield tr, te


def fit_predict_v3(train: pd.DataFrame, test: pd.DataFrame, tag: str) -> tuple[pd.DataFrame, dict]:
    train = train.reset_index(drop=True)
    y = train["y_addressed"].values
    C = choose_C(train) if train["cutoff_year"].nunique() >= 2 else 10.0
    mo, em = _Momentum().fit(train, y), _Embed(C).fit(train, y)
    ens = (mo.logit(test) + em.logit(test)) / 2
    oof = np.zeros(len(train))
    for tr, te in _folds(train):
        a, b = train[tr], train[te]
        oof[te] = (_Momentum().fit(a, y[tr]).logit(b) + _Embed(C).fit(a, y[tr]).logit(b)) / 2
    platt = LogisticRegression(max_iter=5000, C=1e6).fit(oof.reshape(-1, 1), y)
    sig = lambda z: 1 / (1 + np.exp(-z))  # noqa: E731
    out = pd.DataFrame({
        "question_id": test["question_id"].values,
        f"v3_dm_src__{tag}": sig(mo.logit(test)),
        f"v3_ens__{tag}": sig(ens),
        f"v3_ens_cal__{tag}": platt.predict_proba(ens.reshape(-1, 1))[:, 1],
    })
    return out, {"embed_C": C, "platt_coef": float(platt.coef_[0][0]), "platt_intercept": float(platt.intercept_[0])}
