"""Count corpus papers matching each case in its first 24 months (data-only inclusion check)."""
import json, re, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cases import CASES, PROSPECTIVE

def months_after(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    return date(d.year + y, mo + 1, min(d.day, 28))

corpus = Path(__file__).resolve().parents[1] / "data/raw/corpus_classified.jsonl"
cases = CASES + PROSPECTIVE
rx = {c["key"]: re.compile(c["query"], re.I) for c in cases}
win = {c["key"]: (date.fromisoformat(c["onset"]), months_after(date.fromisoformat(c["onset"]), 24)) for c in cases}
n = {c["key"]: 0 for c in cases}; pre = dict(n)
with corpus.open() as f:
    for line in f:
        p = json.loads(line); d = date.fromisoformat(p["published"]); text = p["title"] + " " + p["abstract"]
        for k, r in rx.items():
            a, b = win[k]
            if a <= d < b and r.search(text): n[k] += 1
            elif months_after(a, -24) <= d < a and r.search(text): pre[k] += 1
for c in cases:
    print(f"{c['key']:22s} {c.get('outcome','prospective'):10s} window={n[c['key']]:5d}  pre-onset={pre[c['key']]:4d}")
