"""Outcome labels for a frozen cohort (run only after predictions are frozen).

- L1  Paper 3's label, unchanged: TF-IDF top-8 future candidates in the
      subfield + the strict gpt-4o-mini judge (``pipeline.labeling``).
- L2  The same candidates re-judged by gpt-4o (Paper 3's second judge).
- L3  Paper 4's correction: candidates that *cite* the question's source
      papers (Semantic Scholar citation graph) and fall inside the outcome
      window, top-8 by similarity, judged by the L1 judge. The L3 label is
      ``addressed_L1 or addressed_citation``.
- Action types (H7): for addressed tension questions, gpt-4o classifies
      what kind of evidence step each direct follow-up paper took, in Paper
      4's action vocabulary.

Usage:
    python -m forecast.label backtest2021
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from forecast.common import ROOT, read_jsonl, study_dir, write_jsonl
from forecast.cohort import STUDIES

from pipeline import corpus, labeling  # noqa: E402
from pipeline.llm import SECOND_JUDGE_MODEL, chat_json  # noqa: E402

S2_CACHE = ROOT / "data" / "cache" / "s2"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/arXiv:{}/citations"


# ------------------------------------------------------------ L1 and L2


def label_l1(questions: list[dict], study: dict) -> tuple[list[dict], dict]:
    ctxs, out = {}, []
    for key in sorted({q["subfield"] for q in questions}):
        docs = corpus.load_subfield_docs(key, *study["future_window"])
        ctx = labeling.FutureContext(docs, study["cutoff_year"])
        ctxs[key] = ctx
        qs = [q for q in questions if q["subfield"] == key]
        with ThreadPoolExecutor(max_workers=8) as pool:
            out.extend(pool.map(lambda q: labeling.label_question(q, ctx), qs))
        print(f"[L1] {key}: {len(qs)} questions, future corpus {len(docs)}", flush=True)
    return out, ctxs


def label_l2(questions: list[dict], l1: list[dict], ctxs: dict) -> list[dict]:
    by_id = {q["question_id"]: q for q in questions}

    def judge(rec: dict) -> dict:
        q = by_id[rec["question_id"]]
        if rec["judge_model"] == "auto_threshold":
            return {"question_id": rec["question_id"], **{k: rec[k] for k in (
                "addressed", "answer_status", "premise_status", "supporting_ids", "judge_model")}}
        ctx = ctxs[q["subfield"]]
        id_to_doc = {d["id"]: d for d in ctx.future_docs}
        docs = [id_to_doc[i] for i in rec["top_ids"] if i in id_to_doc]
        return {"question_id": rec["question_id"],
                **labeling.judge_question(q["question"], q["cutoff_date"], docs, model=SECOND_JUDGE_MODEL)}

    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(judge, l1))


# ------------------------------------------------------------------- L3


def source_arxiv_ids(q: dict) -> list[str]:
    m = q.get("source_material") or {}
    ids = [c.get("arxiv_id") for c in m.get("cluster", [])]
    if "statement" in m:
        ids.append(m["statement"].get("arxiv_id"))
    for k in ("claim_a", "claim_b"):
        if k in m:
            ids.append(m[k].get("arxiv_id"))
    if "arxiv_id" in m:
        ids.append(m["arxiv_id"])
    return sorted({i for i in ids if i})


def s2_citations(arxiv_id: str) -> list[dict]:
    S2_CACHE.mkdir(parents=True, exist_ok=True)
    cache = S2_CACHE / f"{arxiv_id.replace('/', '_')}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rows, offset = [], 0
    while True:
        params = urllib.parse.urlencode(
            {"fields": "externalIds,title,abstract,publicationDate,year", "limit": 1000, "offset": offset}
        )
        url = S2_URL.format(arxiv_id) + "?" + params
        payload = None
        for attempt in range(8):
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    payload = json.loads(resp.read())
                break
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    payload = {"data": []}
                    break
                time.sleep(5 * (attempt + 1))
            except Exception:  # noqa: BLE001
                time.sleep(5 * (attempt + 1))
        if payload is None:
            raise RuntimeError(f"S2 failed for {arxiv_id}")
        for item in payload.get("data", []):
            p = item.get("citingPaper") or {}
            rows.append(
                {
                    "arxiv_id": (p.get("externalIds") or {}).get("ArXiv"),
                    "title": p.get("title") or "",
                    "abstract": p.get("abstract") or "",
                    "date": p.get("publicationDate") or (f"{p['year']}-07-01" if p.get("year") else None),
                }
            )
        if payload.get("next") is None or len(payload.get("data", [])) == 0:
            break
        offset = payload["next"]
        time.sleep(1.2)
    cache.write_text(json.dumps(rows))
    time.sleep(1.2)
    return rows


def label_citation(questions: list[dict], study: dict, ctxs: dict) -> list[dict]:
    lo, hi = study["future_window"]
    # Prefer this study's arXiv records (true v1 date, full abstract).
    arxiv_docs: dict[str, dict] = {}
    for ctx in ctxs.values():
        for d in ctx.future_docs:
            arxiv_docs[d["id"]] = d
    out = []
    for q in questions:
        src = source_arxiv_ids(q)
        if not src:
            out.append({"question_id": q["question_id"], "n_source_papers": 0, "n_candidates": 0,
                        "addressed": None, "answer_status": None, "supporting_ids": []})
            continue
        cands: dict[str, dict] = {}
        for aid in src:
            for c in s2_citations(aid):
                if c["arxiv_id"] and c["arxiv_id"] in arxiv_docs:
                    d = arxiv_docs[c["arxiv_id"]]
                elif c["date"] and lo <= c["date"] <= hi and (c["abstract"] or c["title"]):
                    key = c["arxiv_id"] or f"s2:{c['title'][:80]}"
                    d = {"id": key, "title": c["title"], "abstract": c["abstract"] or "", "published": c["date"]}
                else:
                    continue
                if lo <= d["published"] <= hi:
                    cands[d["id"]] = d
        rec = {"question_id": q["question_id"], "n_source_papers": len(src), "n_candidates": len(cands)}
        if not cands:
            rec.update({"addressed": False, "answer_status": "not_addressed", "supporting_ids": [],
                        "judge_model": "no_citing_candidates"})
            out.append(rec)
            continue
        ctx = ctxs[q["subfield"]]
        docs = list(cands.values())
        qv = ctx.vectorizer.transform([q["question"]])
        dv = ctx.vectorizer.transform([f"{d['title']}. {d['abstract']}" for d in docs])
        sims = cosine_similarity(qv, dv)[0]
        top = [docs[i] for i in np.argsort(-sims)[: labeling.TOP_K_JUDGE]]
        judged = labeling.judge_question(q["question"], q["cutoff_date"], top)
        rec.update({"top_ids": [d["id"] for d in top], **judged})
        out.append(rec)
    return out


# --------------------------------------------------------- action types

ACTION_TYPES = {
    "collect_observation": "obtains NEW observations or measurements of the objects in question",
    "rerun_analysis": "re-analyses EXISTING data of the same objects with different methods, models or assumptions",
    "compare_datasets": "combines or cross-checks independent datasets/instruments for consistency",
    "run_simulation": "uses simulations or theoretical modelling to test the mechanism",
    "search_archive": "mines archival data or large survey catalogs (statistical/population study)",
    "search_review": "reviews or synthesizes existing literature",
}

_ACTION_PROMPT = (
    "A research question and papers that directly engaged it are listed below. "
    "For EACH paper, classify the main kind of evidence step it took, choosing exactly one of:\n"
    + "\n".join(f'- "{k}": {v}' for k, v in ACTION_TYPES.items())
    + '\n\nQuestion: {question}\n\nPapers:\n{papers}\n\n'
    'Reply as JSON: {{"papers": [{{"id": "...", "action_type": "..."}}, ...]}}'
)


def classify_actions(questions: list[dict], labels: dict[str, list[str]], docs: dict[str, dict]) -> list[dict]:
    by_id = {q["question_id"]: q for q in questions}
    out = []
    for qid, sup in labels.items():
        papers = [docs[i] for i in sup if i in docs]
        if not papers:
            continue
        listing = "\n".join(f"[{d['id']}] {d['title']} — {d['abstract'][:700]}" for d in papers)
        resp = chat_json(
            [{"role": "user", "content": _ACTION_PROMPT.format(question=by_id[qid]["question"], papers=listing)}],
            model=SECOND_JUDGE_MODEL,
            max_tokens=600,
        )
        types = [str(p.get("action_type")) for p in resp.get("papers", []) if str(p.get("action_type")) in ACTION_TYPES]
        out.append({"question_id": qid, "paper_ids": [d["id"] for d in papers], "action_types": types})
    return out


def main() -> None:
    name = sys.argv[1]
    study = STUDIES[name]
    d = study_dir(name)
    if not (d / "FREEZE.json").exists():
        raise SystemExit("refusing to label: predictions are not frozen (FREEZE.json missing)")
    questions = read_jsonl(d / "questions.jsonl")

    l1, ctxs = label_l1(questions, study)
    write_jsonl(d / "labels_L1.jsonl", l1)
    l2 = label_l2(questions, l1, ctxs)
    write_jsonl(d / "labels_L2.jsonl", l2)
    cit = label_citation(questions, study, ctxs)
    write_jsonl(d / "labels_citation.jsonl", cit)

    # Action types for addressed tension questions, using every direct
    # supporting paper found by L1 or the citation judge.
    tension = {q["question_id"] for q in questions if q["source"] == "evidence_tension"}
    docs: dict[str, dict] = {}
    for ctx in ctxs.values():
        docs.update({x["id"]: x for x in ctx.future_docs})
    sup: dict[str, list[str]] = {}
    for rec in l1 + [c for c in cit if c.get("addressed")]:
        if rec["question_id"] in tension and rec.get("addressed"):
            sup.setdefault(rec["question_id"], [])
            sup[rec["question_id"]] += [i for i in rec.get("supporting_ids", []) if i not in sup[rec["question_id"]]]
    write_jsonl(d / "action_types.jsonl", classify_actions(questions, sup, docs))
    print(f"[label] {name}: L1/L2/citation/action labels written")


if __name__ == "__main__":
    main()
