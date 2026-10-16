"""Topic-momentum features: how much, and how recently, the field was
already working near a question at its cutoff.

Dense-retrieval analogue of Paper 3's TF-IDF evidence features: the
question and every pre-cutoff paper of its subfield are embedded with the
same model (text-embedding-3-small) and compared by cosine similarity.
Everything uses only papers published inside the question's past window.

Features (prefix ``dm_``):
- ``dm_top10``, ``dm_top50``     mean similarity of the 10 / 50 nearest papers
- ``dm_n_lo``, ``dm_n_hi``       papers above two similarity thresholds (log1p)
- ``dm_share_lo``                ``dm_n_lo`` as a share of the subfield's past window
- ``dm_recent_top50``            share of the 50 nearest papers from the last 2 years
- ``dm_age_top20``               mean age (years) of the 20 nearest papers
- ``dm_growth``                  log ratio of near papers in the last 2 years vs the 2 before
- ``dm_recent_n``                near papers (>= low threshold) in the last 2 years (log1p)

Usage:
    python -m forecast.momentum            # Paper 3 training questions + every cohort present
"""

from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from forecast.common import PAPER3, ROOT, read_jsonl, study_dir, write_jsonl
from forecast.cohort import STUDIES
from forecast.models_v2 import embed

from pipeline import corpus  # noqa: E402

EMB_DIR = ROOT / "data" / "raw" / "embeddings"
T_LO, T_HI = 0.58, 0.65  # set from the feature distribution (median top-10 similarity ~0.65), not outcomes
PAPER3_OUT = ROOT / "data" / "paper3_momentum.jsonl"


class SubfieldIndex:
    """Embeddings of one subfield's papers, with publication dates."""

    _cache: dict[int, dict[str, np.ndarray]] = {}

    def __init__(self, key: str):
        docs = corpus.load_subfield_docs(key, "0000-00-00", "9999-99-99")
        rows = defaultdict(list)
        for d in docs:
            rows[int(d["published"][:4])].append(d)
        ids, pub, mats = [], [], []
        for y, ds in sorted(rows.items()):
            emb = self._year(y)
            for d in ds:
                if d["id"] in emb:
                    ids.append(d["id"])
                    pub.append(d["published"])
                    mats.append(emb[d["id"]])
        self.ids = np.array(ids)
        self.pub = np.array(pub)
        self.year = np.array([int(p[:4]) for p in pub])
        self.X = np.vstack(mats).astype(np.float32)

    @classmethod
    def _year(cls, y: int) -> dict[str, np.ndarray]:
        if y not in cls._cache:
            z = np.load(EMB_DIR / f"{y}.npz")
            cls._cache[y] = dict(zip(z["ids"].tolist(), z["X"]))
        return cls._cache[y]


def features_for(questions: list[dict], idx: SubfieldIndex, window: tuple[str, str], cutoff_year: int) -> list[dict]:
    m = (idx.pub >= window[0]) & (idx.pub <= window[1])
    X, yrs = idx.X[m], idx.year[m]
    Q = embed([q["question"] for q in questions]).astype(np.float32)
    S = Q @ X.T
    out = []
    for q, s in zip(questions, S):
        order = np.argsort(-s)
        lo, hi = s >= T_LO, s >= T_HI
        recent = yrs >= cutoff_year - 1
        before = (yrs >= cutoff_year - 3) & (yrs <= cutoff_year - 2)
        out.append({
            "question_id": q["question_id"],
            "dm_top10": float(s[order[:10]].mean()),
            "dm_top50": float(s[order[:50]].mean()),
            "dm_n_lo": float(np.log1p(lo.sum())),
            "dm_n_hi": float(np.log1p(hi.sum())),
            "dm_share_lo": float(lo.sum() / max(1, len(s))),
            "dm_recent_top50": float(recent[order[:50]].mean()),
            "dm_age_top20": float((cutoff_year - yrs[order[:20]]).mean()),
            "dm_growth": float(np.log((np.sum(lo & recent) + 1) / (np.sum(lo & before) + 1))),
            "dm_recent_n": float(np.log1p(np.sum(lo & recent))),
        })
    return out


def run(groups: dict[tuple[str, int, tuple[str, str]], list[dict]]) -> list[dict]:
    out = []
    for key in sorted({k[0] for k in groups}):
        idx = SubfieldIndex(key)
        for (sub, cy, window), qs in sorted(groups.items()):
            if sub == key:
                out += features_for(qs, idx, window, cy)
        print(f"[momentum] {key}: index {len(idx.ids)} papers", flush=True)
    return out


def main() -> None:
    groups: dict = defaultdict(list)
    for q in read_jsonl(PAPER3 / "data" / "questions" / "questions_v1.jsonl"):
        groups[(q["subfield"], q["cutoff_year"], corpus.past_window(q["cutoff_year"]))].append(q)
    write_jsonl(PAPER3_OUT, run(groups))
    for name, study in STUDIES.items():
        qpath = study_dir(name) / "questions.jsonl"
        if not qpath.exists():
            continue
        groups = defaultdict(list)
        for q in read_jsonl(qpath):
            groups[(q["subfield"], study["cutoff_year"], tuple(study["past_window"]))].append(q)
        write_jsonl(study_dir(name) / "momentum.jsonl", run(groups))
        print(f"[momentum] {name} done", flush=True)


if __name__ == "__main__":
    main()
