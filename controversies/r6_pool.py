"""Round 6 step 2: mechanical candidate pool and Packet A (screening sheet).

Selects astro-ph primary papers (v1 2006-01-01..2021-10-14) with a claim word in
the title, ranks them by Semantic Scholar citations per year, and writes the top
200 as an outcome-free screening sheet. Needs S2_API_KEY.
"""
import csv, json, os, re, sys, time, urllib.error, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/controversies/r6"
CLAIM = re.compile(r"\b(evidence (for|of)|detection of|discovery of|hints? (of|for)|anomal(y|ies|ous)|excess|tension|discrepanc(y|ies)|unexpected|puzzl\w*|signal of|signature of|indication)\b", re.I)
START, END, AS_OF, TOP = "2006-01-01", "2021-10-14", date(2026, 10, 14), 200
sys.path.insert(0, str(Path(__file__).parent))
from cases import CASES  # round-5 cases, flagged so screeners can skip them
R5 = [(c["key"], re.compile(c["query"], re.I)) for c in CASES]


def citation_counts(ids):
    counts, key = {}, os.environ["S2_API_KEY"]
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        req = urllib.request.Request("https://api.semanticscholar.org/graph/v1/paper/batch?fields=citationCount",
                                     data=json.dumps({"ids": [f"arXiv:{x}" for x in chunk]}).encode(),
                                     headers={"x-api-key": key, "content-type": "application/json"})
        for attempt in range(8):
            try:
                with urllib.request.urlopen(req, timeout=120) as r: rows = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504): raise
                time.sleep(2 ** attempt)
        for x, row in zip(chunk, rows):
            if row: counts[x] = row.get("citationCount") or 0
        time.sleep(1.1)
    return counts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pool = []
    for line in (ROOT / "data/raw/corpus_classified.jsonl").open():
        p = json.loads(line)
        if START <= p["published"] <= END and p["primary_category"].startswith("astro-ph") and CLAIM.search(p["title"]):
            pool.append(p)
    counts = citation_counts([p["id"] for p in pool])
    for p in pool:
        years = max((AS_OF - date.fromisoformat(p["published"])).days / 365.25, 1.0)
        p["citations"] = counts.get(p["id"]); p["cites_per_year"] = (p["citations"] or 0) / years
    pool.sort(key=lambda p: (-p["cites_per_year"], p["id"]))
    (OUT / "pool.jsonl").write_text("".join(json.dumps({k: p[k] for k in ("id", "published", "title", "citations", "cites_per_year")}) + "\n" for p in pool))
    with (OUT / "packet_A_screening.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "arxiv_id", "date", "title", "abstract", "round5_case_flag", "is_contested_anomalous_claim (yes/no)", "key_phrase_used_by_later_papers", "notes"])
        for i, p in enumerate(pool[:TOP], 1):
            flag = ";".join(k for k, rx in R5 if rx.search(p["title"] + " " + p["abstract"]))
            w.writerow([i, p["id"], p["published"], p["title"], p["abstract"], flag, "", "", ""])
    print(f"pool {len(pool)}, with S2 counts {len(counts)}, packet A rows {min(TOP, len(pool))}")


if __name__ == "__main__":
    main()
