"""LLM-free features of a controversy's first 24 months of literature.

Every feature is a share of window abstracts (or a count ratio) computed with
fixed, generic lexicons. No language model reads any text, so nothing a model
knows about how a controversy ended can leak into the features.
"""
import json, math, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEX = {
    # F1: non-detection / refutation language
    "null": r"\bno (evidence|detection|signal|significant|sign)\b|\bnot (detect|confirm|find|found|see|seen|observed)|non.?detection|upper limits?|\brule[sd]? out|\bdisfavou?r|inconsistent with|(cannot|could not|fail(s|ed)? to) (confirm|reproduce|detect)|\babsence of\b|\bspurious\b",
    # F2: systematics / instrumental language (generic terms only)
    "systematics": r"\bsystematics?\b|\bsystematic (error|effect|uncertaint)|contaminat|calibrat|\binstrumental\b|\bartifacts?\b|\bartefacts?\b",
    # F5: confirmation language
    "confirm": r"\bconfirm(s|ed|ing|ation)?\b|independent(ly)? (detect|measur|observ)|\bwe (detect|find evidence|observe)\b|\bdetection of\b",
    # F3 (exploratory): new-physics / exotic-explanation language
    "exotic": r"dark matter|new physics|beyond the standard model|\bexotic\b|modified gravity|\baxions?\b|sterile neutrino|primordial black hole|extraterrestrial|technosignature|annihilat",
}
RX = {k: re.compile(v, re.I) for k, v in LEX.items()}


def case_features(rows):
    n = len(rows)
    text = [r["title"] + " " + r["abstract"] for r in rows]
    share = {k: sum(bool(rx.search(t)) for t in text) / n for k, rx in RX.items()}
    early = sum(r["month"] < 12 for r in rows); late = n - early
    return dict(n=n, log_n=math.log(n), null=share["null"], systematics=share["systematics"],
                confirm=share["confirm"], exotic=share["exotic"], growth=math.log((late + 1) / (early + 1)))


def load():
    by = defaultdict(list)
    for line in (ROOT / "data/controversies/papers.jsonl").open():
        r = json.loads(line); by[r["case"]].append(r)
    return by


if __name__ == "__main__":
    manifest = json.loads((ROOT / "data/controversies/cases_manifest.json").read_text())
    by = load()
    feats = {m["key"]: {**case_features(by[m["key"]]), "outcome": m["outcome"], "provisional": m["provisional"]}
             for m in manifest if m["included"]}
    (ROOT / "data/controversies/features.json").write_text(json.dumps(feats, indent=1))
    print(f"wrote features for {len(feats)} cases")
