"""Exploratory (not pre-registered): do the forecasters predict *human*
judgments of engagement?

Scores Paper 2's 90 human-annotated questions (cutoff 2020-12-31, exoplanet
atmospheres; ``vendor/paper2/annotation``) with the v3 model and with its
momentum-only and embedding-only parts, trained only on Paper 3 cutoffs
whose labels close by 2020 (2012, 2014). Reports AUC against each human's
binary label, against their mean, and against the gpt-4o judge on the same
items (``results/human_check.json``). Paper 2's generators are not Paper 3
sources, so the source fixed effect is zero for every item.

Usage:
    python -m forecast.human_predict
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from forecast.common import ROOT, read_jsonl
from forecast.human_check import parse_packet
from forecast.models_v2 import _Embed
from forecast.models_v3 import _Momentum
from forecast.momentum import SubfieldIndex, features_for
from forecast.predict import paper3_table

from pipeline import corpus  # noqa: E402

N_BOOT = 2000


def auc_ci(y, s, seed=7):
    y, s = np.asarray(y), np.asarray(s)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(y), len(y))
        if len(np.unique(y[i])) > 1:
            vals.append(roc_auc_score(y[i], s[i]))
    return {"auc": round(float(roc_auc_score(y, s)), 3),
            "ci95": [round(float(np.percentile(vals, q)), 3) for q in (2.5, 97.5)]}


def main() -> None:
    items = parse_packet()
    hc = {r["item_id"]: r for r in json.loads((ROOT / "results" / "human_check.json").read_text())["items"]}
    ids = sorted(items)
    test = pd.DataFrame({"question_id": ids, "question": [items[i]["question"] for i in ids],
                         "source": [hc[i]["system"] for i in ids]})
    mom = pd.DataFrame(features_for(test.to_dict(orient="records"), SubfieldIndex("exoplanet_atmospheres"),
                                    corpus.past_window(2020), 2020))
    test = test.merge(mom, on="question_id")

    train = paper3_table().merge(pd.DataFrame(read_jsonl(ROOT / "data" / "paper3_momentum.jsonl")), on="question_id")
    train = train[train.cutoff_year.isin((2012, 2014))].reset_index(drop=True)
    y = train["y_addressed"].values
    mo, em = _Momentum().fit(train, y), _Embed(10.0).fit(train, y)
    scores = {"v3_momentum": mo.logit(test), "v3_embedding": em.logit(test)}
    scores["v3_ens"] = (scores["v3_momentum"] + scores["v3_embedding"]) / 2

    targets = {
        "human_1": np.array([hc[i]["human_1"] for i in ids], int),
        "human_2": np.array([hc[i]["human_2"] for i in ids], int),
        "both_humans_say_addressed": np.array([hc[i]["human_1"] and hc[i]["human_2"] for i in ids], int),
        "gpt-4o_judge": np.array([hc[i]["gpt-4o"] for i in ids], int),
    }
    report = {"n_items": len(ids), "note": "exploratory, not pre-registered; training cutoffs 2012+2014",
              "base_rates": {t: round(float(v.mean()), 3) for t, v in targets.items()},
              "auc": {t: {m: auc_ci(v, s) for m, s in scores.items()} for t, v in targets.items()}}
    (ROOT / "results" / "human_predict.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
