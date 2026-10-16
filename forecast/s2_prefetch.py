"""Fill the citation cache with Semantic Scholar's batch endpoint.

``forecast.label.citing_papers`` fetches one paper's citations per request,
which a rate-limited key turns into hours. The batch endpoint returns the
nested citation lists of up to 100 papers per request; this writes them in
exactly the cache format ``citing_papers`` reads. Papers whose nested list
comes back shorter than their citation count are left uncached, so the
per-paper (paginated) path still handles them.

Usage:
    S2_API_KEY=... python -m forecast.s2_prefetch backtest2017 backtest2019 ...
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from forecast.common import read_jsonl, study_dir
from forecast.label import CIT_CACHE, source_arxiv_ids

URL = ("https://api.semanticscholar.org/graph/v1/paper/batch?fields=citationCount,"
       "citations.externalIds,citations.title,citations.abstract,citations.publicationDate,citations.year")
BATCH = 6  # the server caps nested-citation responses (~6 papers with abstracts)


class TooLarge(Exception):
    def __init__(self, n: int):
        self.n = n


def post(ids: list[str]) -> list:
    key = os.environ.get("S2_API_KEY")
    body = json.dumps({"ids": [f"arXiv:{i}" for i in ids]}).encode()
    for attempt in range(12):
        req = urllib.request.Request(URL, data=body, method="POST",
                                     headers={"Content-Type": "application/json", **({"x-api-key": key} if key else {})})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as err:
            if err.code == 400:  # "Response would exceed maximum size. Please retry with N or fewer ids"
                m = re.search(r"(\d+) or fewer", err.read().decode("utf-8", "replace"))
                raise TooLarge(max(1, int(m.group(1)) if m else len(ids) // 2)) from err
            print(f"[s2] HTTP {err.code}, retry", flush=True)
        except Exception as err:  # noqa: BLE001
            print(f"[s2] {err!r}, retry", flush=True)
        time.sleep(min(60, 3 * 2 ** attempt))
    raise RuntimeError("batch request failed")


def main() -> None:
    CIT_CACHE.mkdir(parents=True, exist_ok=True)
    wanted = sorted({i for name in sys.argv[1:] for q in read_jsonl(study_dir(name) / "questions.jsonl")
                     for i in source_arxiv_ids(q)})
    todo = [i for i in wanted if not (CIT_CACHE / f"{i.replace('/', '_')}.json").exists()]
    print(f"[s2] {len(wanted)} source papers, {len(todo)} to fetch", flush=True)
    short = []

    def fetch(chunk: list[str]) -> list[tuple[str, dict | None]]:
        try:
            return list(zip(chunk, post(chunk)))
        except TooLarge as err:
            n = min(err.n, len(chunk) - 1) if len(chunk) > 1 else 0
            if n == 0:  # a single paper too large for batch: leave it to the per-paper path
                short.append(chunk[0])
                return []
            out = []
            for j in range(0, len(chunk), n):
                out += fetch(chunk[j:j + n])
            return out

    for k in range(0, len(todo), BATCH):
        chunk = todo[k:k + BATCH]
        for aid, p in fetch(chunk):
            path = CIT_CACHE / f"{aid.replace('/', '_')}.json"
            if p is None:  # not in Semantic Scholar: same as the per-paper 404 path
                path.write_text("[]")
                continue
            cits = p.get("citations") or []
            if len(cits) < (p.get("citationCount") or 0) * 0.95:
                short.append(aid)
                continue
            rows = [{
                "arxiv_id": (c.get("externalIds") or {}).get("ArXiv"),
                "title": c.get("title") or "",
                "abstract": c.get("abstract") or "",
                "date": c.get("publicationDate") or (f"{c['year']}-07-01" if c.get("year") else None),
            } for c in cits]
            path.write_text(json.dumps(rows))
        if (k // BATCH) % 10 == 0:
            print(f"[s2] {min(k + BATCH, len(todo))}/{len(todo)}", flush=True)
        time.sleep(1.5)
    print(f"[s2] done; {len(short)} papers left to the per-paper path: {short[:10]}", flush=True)


if __name__ == "__main__":
    main()
