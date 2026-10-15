"""Instrument check: is today's judge the judge that made Paper 3's labels?

Paper 3's committed labels were judged by ``gpt-4o`` in July 2026 (956 of
980; the rest auto-thresholded). Model aliases can be re-pointed, so before
using "the same judge" as the outcome measure here, re-judge a random sample
of Paper 3's own questions on their own stored candidates (``top_ids``, all
in this harvest) and measure agreement with the committed labels. The
sample comes from cutoffs 2018 and 2020, whose candidates fall in 2019-2025.

Usage:
    python -m forecast.judge_drift
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from forecast.common import PAPER3, ROOT, read_jsonl

from pipeline import corpus, labeling  # noqa: E402

N = 120


def kappa(a, b) -> float:
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = np.mean(a == b)
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe))


def main() -> None:
    qs = {q["question_id"]: q for q in read_jsonl(PAPER3 / "data" / "questions" / "questions_v1.jsonl")}
    labels = [
        r for r in read_jsonl(PAPER3 / "data" / "labels" / "labels_v1.jsonl")
        if r["judge_model"] == "gpt-4o" and qs[r["question_id"]]["cutoff_year"] in (2018, 2020)
    ]
    sample = random.Random(7).sample(labels, N)
    wanted = {i for r in sample for i in r["top_ids"]}
    docs = {d["id"]: d for d in corpus.iter_processed() if d["id"] in wanted}

    def rejudge(rec: dict) -> dict:
        q = qs[rec["question_id"]]
        cands = [docs[i] for i in rec["top_ids"] if i in docs]
        out = {"question_id": rec["question_id"], "n_candidates_found": len(cands),
               "paper3_addressed": bool(rec["addressed"]), "paper3_status": rec["answer_status"]}
        for model in ("gpt-4o", "gpt-4o-mini"):
            j = labeling.judge_question(q["question"], q["cutoff_date"], cands, model=model)
            out[f"{model}_addressed"] = j["addressed"]
            out[f"{model}_status"] = j["answer_status"]
        return out

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(rejudge, sample))
    p3 = [r["paper3_addressed"] for r in rows]
    report = {
        "n": len(rows),
        "candidates_recovered": float(np.mean([r["n_candidates_found"] == 8 for r in rows])),
        "paper3_rate": float(np.mean(p3)),
    }
    for model in ("gpt-4o", "gpt-4o-mini"):
        now = [r[f"{model}_addressed"] for r in rows]
        report[model] = {
            "rate_today": float(np.mean(now)),
            "agreement_with_paper3": float(np.mean(np.array(now) == np.array(p3))),
            "kappa_with_paper3": round(kappa(now, p3), 4),
        }
    out = ROOT / "results" / "judge_drift.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"report": report, "rows": rows}, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
