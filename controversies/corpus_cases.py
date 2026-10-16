"""Extract each case's window papers (first 24 months after onset) from the corpus.

Writes data/controversies/papers.jsonl: one row per (case, paper) with id, date,
title, abstract and month offset from onset. Inclusion rule (pre-registered):
a case enters the analysis only if it has >= 10 window papers.
"""
import json, re, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cases import CASES, PROSPECTIVE

ROOT = Path(__file__).resolve().parents[1]
WINDOW_MONTHS, MIN_PAPERS = 24, 10


def months_after(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    return date(d.year + y, mo + 1, min(d.day, 28))


def month_offset(onset, d):
    return (d.year - onset.year) * 12 + d.month - onset.month - (d.day < onset.day)


def main():
    cases = CASES + PROSPECTIVE
    rx = {c["key"]: re.compile(c["query"], re.I) for c in cases}
    win = {c["key"]: (date.fromisoformat(c["onset"]), months_after(date.fromisoformat(c["onset"]), WINDOW_MONTHS)) for c in cases}
    out = ROOT / "data" / "controversies"; out.mkdir(parents=True, exist_ok=True)
    rows = []
    with (ROOT / "data/raw/corpus_classified.jsonl").open() as f:
        for line in f:
            p = json.loads(line); d = date.fromisoformat(p["published"]); text = p["title"] + " " + p["abstract"]
            for k, r in rx.items():
                a, b = win[k]
                if a <= d < b and r.search(text):
                    rows.append(dict(case=k, id=p["id"], published=p["published"], month=month_offset(a, d),
                                     title=p["title"], abstract=p["abstract"]))
    rows.sort(key=lambda r: (r["case"], r["published"], r["id"]))
    with (out / "papers.jsonl").open("w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts = {c["key"]: sum(r["case"] == c["key"] for r in rows) for c in cases}
    manifest = [dict(key=c["key"], outcome=c.get("outcome", "prospective"), provisional=c.get("provisional"),
                     n_window=counts[c["key"]], included=counts[c["key"]] >= MIN_PAPERS) for c in cases]
    (out / "cases_manifest.json").write_text(json.dumps(manifest, indent=1))
    for m in manifest: print(f"{m['key']:22s} {m['outcome']:11s} n={m['n_window']:4d} {'IN' if m['included'] else 'excluded'}")


if __name__ == "__main__":
    main()
