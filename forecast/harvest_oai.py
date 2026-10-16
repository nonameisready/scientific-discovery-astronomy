"""Harvest arXiv astro-ph metadata through OAI-PMH (arXivRaw format).

Produces shards in exactly the record schema Paper 3's harvester writes
(id, title, abstract, published, primary_category, categories), so Paper 3's
``corpus.build_processed`` consumes them unchanged.

Why OAI-PMH instead of Paper 3's search API: the bulk interface returns
~1,300 records per request without the per-query pagination limits, so a
14-year harvest takes under an hour instead of several.

``published`` is the v1 submission date taken from the arXivRaw version
history. The plain ``arXiv`` OAI format's ``<created>`` field is NOT used: on
the current OAI server it reports the latest version's date (e.g. 2508.12372,
first submitted 2025-08-17, shows created=2026-09-30), which would silently
move revised papers into the future window.

The OAI set ``physics:astro-ph`` includes cross-listed papers, matching
Paper 3's ``cat:astro-ph.*`` queries.

Each OAI record carries exactly one datestamp, so disjoint datestamp windows
can be harvested in parallel without overlap (``--from/--until/--tag``).

Usage:
    python -m forecast.harvest_oai --from 2013-01-01 --until 2016-12-31 --tag w1
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

OAI_URL = "https://oaipmh.arxiv.org/oai"
NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "raw": "http://arxiv.org/OAI/arXivRaw/",
}
OUT_DIR = Path("data/raw/arxiv")
DELAY_S = 1.0
MAX_RETRIES = 8


def _fetch(params: dict) -> bytes:
    url = f"{OAI_URL}?{urllib.parse.urlencode(params)}"
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            wait = 10 * (attempt + 1)
            if err.code == 503:
                wait = int(err.headers.get("Retry-After", wait))
            print(f"[oai] HTTP {err.code}, retry in {wait}s", flush=True)
            time.sleep(wait)
        except Exception as err:  # noqa: BLE001 - network flakiness is expected
            print(f"[oai] {err!r}, retry", flush=True)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"OAI request failed: {url}")


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_records(payload: bytes) -> tuple[list[dict], str | None]:
    root = ET.fromstring(payload)
    out = []
    for rec in root.iter(f"{{{NS['oai']}}}record"):
        header = rec.find("oai:header", NS)
        if header is not None and header.get("status") == "deleted":
            continue
        meta = rec.find("oai:metadata/raw:arXivRaw", NS)
        if meta is None:
            continue
        v1 = None
        for ver in meta.findall("raw:version", NS):
            if ver.get("version") == "v1":
                v1 = ver.findtext("raw:date", namespaces=NS)
        if not v1:
            continue
        cats = _clean(meta.findtext("raw:categories", namespaces=NS)).split()
        out.append(
            {
                "id": _clean(meta.findtext("raw:id", namespaces=NS)),
                "title": _clean(meta.findtext("raw:title", namespaces=NS)),
                "abstract": _clean(meta.findtext("raw:abstract", namespaces=NS)),
                "published": parsedate_to_datetime(v1).strftime("%Y-%m-%d"),
                "primary_category": cats[0] if cats else "",
                "categories": cats,
            }
        )
    tok = root.find(".//oai:resumptionToken", NS)
    token = tok.text.strip() if tok is not None and tok.text and tok.text.strip() else None
    return out, token


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="date_from", default="2013-01-01")
    ap.add_argument("--until", dest="date_until", default=None)
    ap.add_argument("--tag", default="all", help="shard/state prefix for parallel windows")
    ap.add_argument("--min-year", type=int, default=2013)
    ap.add_argument("--max-year", type=int, default=9999, help="keep v1 years <= this (backfills)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE = OUT_DIR / f"_oai_state_{args.tag}.json"

    state = json.loads(STATE.read_text()) if STATE.exists() else {"token": None, "pages": 0, "n": 0}
    if state.get("done"):
        print("[oai] already complete")
        return
    files: dict[int, object] = {}
    try:
        while True:
            if state["token"]:
                params = {"verb": "ListRecords", "resumptionToken": state["token"]}
            elif state["pages"] == 0:
                params = {
                    "verb": "ListRecords",
                    "metadataPrefix": "arXivRaw",
                    "set": "physics:astro-ph",
                    "from": args.date_from,
                }
                if args.date_until:
                    params["until"] = args.date_until
            else:
                break
            records, token = parse_records(_fetch(params))
            for r in records:
                year = int(r["published"][:4])
                if year < args.min_year or year > args.max_year:
                    continue
                if year not in files:
                    files[year] = (OUT_DIR / f"oai_{args.tag}_{year}.jsonl").open("a", encoding="utf-8")
                files[year].write(json.dumps(r, ensure_ascii=False) + "\n")
                state["n"] += 1
            for fh in files.values():
                fh.flush()
            state["pages"] += 1
            state["token"] = token
            STATE.write_text(json.dumps(state))
            print(f"[oai {args.tag}] page {state['pages']}: +{len(records)} kept_total={state['n']}", flush=True)
            if not token:
                state["done"] = True
                state["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                STATE.write_text(json.dumps(state))
                break
            time.sleep(DELAY_S)
    finally:
        for fh in files.values():
            fh.close()


if __name__ == "__main__":
    main()
