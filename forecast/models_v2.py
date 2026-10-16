"""Version-2 predictors, aimed at ranking *within* a generation source.

The 2021 backtest showed Paper 3's model mostly reproduces a source-type
prior (broad LLM-written questions are almost always taken up) and ranks
poorly inside a source. These models add the source as an explicit fixed
effect, so every other feature is forced to explain variation *within*
a source, and add a semantic text representation, since a plain TF-IDF
text model matched the structured model on the 2021 cohort.

All are fitted on Paper 3's labelled questions only (leak-free cutoffs per
test cohort, see ``forecast.predict``); hyper-parameters are fixed here or
chosen by a deterministic leave-one-cutoff-out search inside the training
set, never on a test cohort.

- ``v2_struct_src``  Paper 3's structured features + source one-hot, logistic (C=1, as Paper 3)
- ``v2_embed_src``   text-embedding-3-small question embedding + source one-hot,
                     logistic with C picked by leave-one-cutoff-out AUC
- ``v2_ens``         mean of the two models' log-odds
- ``v2_ens_cal``     ``v2_ens`` Platt-calibrated on leave-one-cutoff-out predictions
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from forecast.common import ROOT

from pipeline import models  # noqa: E402

EMBED_MODEL = "text-embedding-3-small"
EMBED_CACHE = ROOT / "data" / "cache" / "embeddings" / EMBED_MODEL
SOURCES = ("evidence_tension", "direct_llm", "future_work", "control")
C_GRID = (0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)

_client = None


def embed(texts: list[str]) -> np.ndarray:
    """Unit-normalized embeddings, cached per text on disk."""
    global _client
    EMBED_CACHE.mkdir(parents=True, exist_ok=True)
    keys = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts]
    missing = [(k, t) for k, t in zip(keys, texts) if not (EMBED_CACHE / f"{k}.json").exists()]
    if missing:
        if _client is None:
            from openai import OpenAI

            _client = OpenAI()
        for i in range(0, len(missing), 100):
            chunk = missing[i : i + 100]
            resp = _client.embeddings.create(model=EMBED_MODEL, input=[t for _, t in chunk])
            for (k, _), d in zip(chunk, resp.data):
                (EMBED_CACHE / f"{k}.json").write_text(json.dumps(d.embedding))
    X = np.array([json.loads((EMBED_CACHE / f"{k}.json").read_text()) for k in keys])
    return X / np.linalg.norm(X, axis=1, keepdims=True)


def source_dummies(df: pd.DataFrame) -> np.ndarray:
    """One-hot over Paper 3's four sources; any other source is all-zero."""
    return np.column_stack([(df["source"].values == s).astype(float) for s in SOURCES])


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


class _Struct:
    def fit(self, df, y):
        self.cols = models.feature_columns(df)
        self.m = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=5000, C=1.0))])
        self.m.fit(np.column_stack([df[self.cols].values, source_dummies(df)]), y)
        return self

    def logit(self, df):
        return _logit(self.m.predict_proba(np.column_stack([df[self.cols].values, source_dummies(df)]))[:, 1])


class _Embed:
    def __init__(self, C: float):
        self.C = C

    def fit(self, df, y):
        self.m = LogisticRegression(max_iter=5000, C=self.C)
        self.m.fit(np.column_stack([embed(df["question"].tolist()), source_dummies(df)]), y)
        return self

    def logit(self, df):
        return _logit(self.m.predict_proba(np.column_stack([embed(df["question"].tolist()), source_dummies(df)]))[:, 1])


def _loco(train: pd.DataFrame, make) -> np.ndarray:
    """Leave-one-cutoff-out log-odds for every training row."""
    out = np.zeros(len(train))
    for cy in sorted(train["cutoff_year"].unique()):
        te = (train["cutoff_year"] == cy).values
        m = make().fit(train[~te], train["y_addressed"].values[~te])
        out[te] = m.logit(train[te])
    return out


def choose_C(train: pd.DataFrame) -> float:
    y = train["y_addressed"].values
    scores = {C: roc_auc_score(y, _loco(train, lambda C=C: _Embed(C))) for C in C_GRID}
    return max(scores, key=scores.get)


def fit_predict_v2(train: pd.DataFrame, test: pd.DataFrame, tag: str) -> tuple[pd.DataFrame, dict]:
    y = train["y_addressed"].values
    C = choose_C(train)
    st, em = _Struct().fit(train, y), _Embed(C).fit(train, y)
    ens_test = (st.logit(test) + em.logit(test)) / 2
    # Platt calibration on out-of-fold ensemble log-odds of the training set.
    oof = (_loco(train, _Struct) + _loco(train, lambda: _Embed(C))) / 2
    platt = LogisticRegression(max_iter=5000, C=1e6).fit(oof.reshape(-1, 1), y)
    sig = lambda z: 1 / (1 + np.exp(-z))  # noqa: E731
    out = pd.DataFrame({
        "question_id": test["question_id"].values,
        f"v2_struct_src__{tag}": sig(st.logit(test)),
        f"v2_embed_src__{tag}": sig(em.logit(test)),
        f"v2_ens__{tag}": sig(ens_test),
        f"v2_ens_cal__{tag}": platt.predict_proba(ens_test.reshape(-1, 1))[:, 1],
    })
    return out, {"embed_C": C, "platt_coef": float(platt.coef_[0][0]), "platt_intercept": float(platt.intercept_[0])}
