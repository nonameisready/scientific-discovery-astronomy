"""Does the forecast survive a retrieval-independent outcome label?

Threat (README, round 3): the outcome label finds future papers by TF-IDF
similarity to the question, and topic-momentum features measure how many
past papers sit close to the question -- so momentum might partly predict
the retriever rather than the field. The citation-graph label avoids that
link: its candidates are papers that *cite the question's source papers*
(Semantic Scholar), judged by the same gpt-4o rubric.

Reports, over all five backtest cohorts (and the fresh round-3 pair):
AUC of v1 / v2 / v3 / momentum-only against
  - ``tfidf``     the Paper 3 label (TF-IDF candidates, gpt-4o)
  - ``citation``  citation-graph candidates only (gpt-4o)
  - ``union``     either
restricted to questions that have source papers (the citation label is
undefined otherwise). Exploratory: the citation label was not part of the
round-2/3 pre-registrations.

Usage:
    python -m forecast.evaluate_citation
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from forecast.common import ROOT, read_jsonl, study_dir
from forecast.evaluate_v2 import _pooled, _strata, _within, boot
from forecast.predict import PRIMARY_TRAIN

COHORTS = ("backtest2017", "backtest2019", "backtest2021", "backtest2022", "backtest2023")
FRESH_V3 = ("backtest2017", "backtest2023")
SCORES = {"v1": "m_logistic", "source_prior": "b_source", "v2_embed_src": "v2_embed_src",
          "v3_dm_src": "v3_dm_src", "v3_ens": "v3_ens"}


def load(name: str) -> pd.DataFrame | None:
    d = study_dir(name)
    if not (d / "labels_citation_gpt4o.jsonl").exists():
        return None
    tag = PRIMARY_TRAIN[name]
    df = pd.DataFrame(read_jsonl(d / "predictions.jsonl"))
    for v in ("v2", "v3"):
        p = d / f"predictions_{v}.jsonl"
        if p.exists():
            df = df.merge(pd.DataFrame(read_jsonl(p)).drop(columns=["source", "subfield"]), on="question_id")
    l2 = pd.DataFrame(read_jsonl(d / "labels_L2.jsonl"))[["question_id", "addressed"]].rename(
        columns={"addressed": "tfidf"})
    cit = pd.DataFrame(read_jsonl(d / "labels_citation_gpt4o.jsonl"))[
        ["question_id", "addressed", "n_source_papers", "n_candidates"]].rename(columns={"addressed": "citation"})
    df = df.merge(l2, on="question_id").merge(cit, on="question_id")
    df = df[df.n_source_papers > 0].copy()
    out = pd.DataFrame({"question_id": df.question_id, "cohort": name, "source": df.source,
                        "n_citing_candidates": df.n_candidates})
    out["tfidf"] = df.tfidf.astype(int).values
    out["citation"] = df.citation.fillna(False).astype(int).values
    out["union"] = (out.tfidf | out.citation).astype(int)
    for k, col in SCORES.items():
        c = f"{col}__{tag}"
        out[k] = df[c].astype(float).values if c in df else np.nan
    return out


def report(df: pd.DataFrame) -> dict:
    res = {"n": int(len(df)), "rates": {y: round(float(df[y].mean()), 3) for y in ("tfidf", "citation", "union")},
           "tfidf_vs_citation_agreement": round(float((df.tfidf == df.citation).mean()), 3)}
    for y in ("tfidf", "citation", "union"):
        d = df.assign(y=df[y])
        res[y] = {}
        for m in SCORES:
            if d[m].isna().any():
                continue
            res[y][m] = {"pooled": boot(d, _pooled, m), "within_source": round(
                _within(d.y.values, d[m].values, _strata(d)), 4)}
    return res


def main() -> None:
    frames = [f for f in (load(c) for c in COHORTS) if f is not None]
    allc = pd.concat(frames, ignore_index=True)
    out = {"cohorts_with_citation_labels": sorted(allc.cohort.unique()),
           "all": report(allc)}
    fresh = allc[allc.cohort.isin(FRESH_V3)]
    if fresh.cohort.nunique() == len(FRESH_V3):
        out["fresh_2017_2023"] = report(fresh)
    path = ROOT / "results" / "citation_label.json"
    path.write_text(json.dumps(out, indent=2))
    a = out["all"]
    print(json.dumps({"n": a["n"], "rates": a["rates"], "agree": a["tfidf_vs_citation_agreement"],
                      **{y: {m: (v["pooled"]["value"], v["pooled"]["ci95"], v["within_source"])
                             for m, v in a[y].items()} for y in ("tfidf", "citation", "union")}}, indent=1))


if __name__ == "__main__":
    main()
