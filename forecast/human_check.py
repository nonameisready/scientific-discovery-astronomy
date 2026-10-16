"""Human validation of the outcome judge.

Paper 2's blinded annotation study (vendored verbatim under
``vendor/paper2/annotation/``) has two independent human annotators label 90
questions, each shown with the same <= 8 post-cutoff abstracts a judge sees.
This runs Paper 3's strict judge -- the instrument behind every label in
this repository -- on exactly those 90 items, and measures agreement with
each human on the binary outcome used everywhere here (``addressed`` =
anything other than ``not_addressed``), next to the humans' agreement with
each other.

Usage:
    python -m forecast.human_check
"""

from __future__ import annotations

import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from forecast.common import PAPER2, ROOT

from pipeline import labeling  # noqa: E402

ANN = PAPER2 / "annotation"
CUTOFF = "2020-12-31"  # Paper 2's astronomy instance (codebook: written before 2021)


def parse_packet() -> dict[str, dict]:
    text = (ANN / "annotation_packet.md").read_text()
    items = {}
    parts = re.split(r"^## (item_\d+)\s*$", text, flags=re.M)
    for iid, body in zip(parts[1::2], parts[2::2]):
        q = re.search(r"\*\*Question \(sys_\w+\):\*\*\s*(.+)", body).group(1).strip()
        cands = []
        for m in re.finditer(r"\*\*\[(\d+)\] (.+?)\*\* \((\d{4}-\d{2})-\d{2}\)\s*\n\s*\n(.+?)(?=\n\s*\n\*\*\[|\n---|\Z)",
                             body, flags=re.S):
            cands.append({"id": f"c{m.group(1)}", "title": m.group(2).strip(), "published": m.group(3),
                          "abstract": re.sub(r"\s+", " ", m.group(4)).strip()})
        items[iid] = {"question": q, "candidates": cands}
    return items


def kappa(a, b) -> float:
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = np.mean(a == b)
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def kappa_ci(a, b, n_boot: int = 2000, seed: int = 7) -> list[float]:
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, int), np.asarray(b, int)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(a), len(a))
        k = kappa(a[i], b[i])
        if not np.isnan(k):
            vals.append(k)
    return [round(float(np.percentile(vals, q)), 3) for q in (2.5, 97.5)]


def main() -> None:
    items = parse_packet()
    humans = {}
    for k in (1, 2):
        rows = list(csv.DictReader((ANN / f"annotator_{k}_sheet.csv").open()))
        humans[f"human_{k}"] = {r["item_id"]: r["outcome"] for r in rows}
    decode = json.loads((ANN / "decode.json").read_text())
    ids = sorted(items)

    def judge(iid: str, model: str) -> dict:
        it = items[iid]
        return labeling.judge_question(it["question"], CUTOFF, it["candidates"], model=model)

    raters = {h: {i: v != "not_addressed" for i, v in humans[h].items()} for h in humans}
    status = {}
    for model in ("gpt-4o", "gpt-4o-mini"):
        with ThreadPoolExecutor(max_workers=8) as pool:
            res = dict(zip(ids, pool.map(lambda i: judge(i, model), ids)))
        raters[model] = {i: bool(r["addressed"]) for i, r in res.items()}
        status[model] = {i: r["answer_status"] for i, r in res.items()}

    names = list(raters)
    pairs = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            x = [raters[a][k] for k in ids]
            y = [raters[b][k] for k in ids]
            pairs[f"{a} vs {b}"] = {"agreement": round(float(np.mean(np.array(x) == np.array(y))), 3),
                                    "kappa": round(kappa(x, y), 3), "kappa_ci95": kappa_ci(x, y)}
    both = [k for k in ids if raters["human_1"][k] == raters["human_2"][k]]
    consensus = {}
    for model in ("gpt-4o", "gpt-4o-mini"):
        x = [raters[model][k] for k in both]
        y = [raters["human_1"][k] for k in both]
        consensus[model] = {"n_items_humans_agree": len(both),
                            "agreement_with_human_consensus": round(float(np.mean(np.array(x) == np.array(y))), 3),
                            "kappa": round(kappa(x, y), 3), "kappa_ci95": kappa_ci(x, y)}
    report = {
        "n_items": len(ids),
        "binary_outcome": "addressed = outcome != not_addressed",
        "addressed_rate": {r: round(float(np.mean([raters[r][k] for k in ids])), 3) for r in names},
        "pairwise": pairs,
        "on_items_where_humans_agree": consensus,
        "by_system": {
            s: {r: round(float(np.mean([raters[r][k] for k in ids if decode[k]["system"] == s])), 3) for r in names}
            for s in sorted({decode[k]["system"] for k in ids})
        },
    }
    out = ROOT / "results" / "human_check.json"
    out.write_text(json.dumps({"report": report, "items": [
        {"item_id": k, "system": decode[k]["system"], **{r: raters[r][k] for r in names},
         "gpt-4o_status": status["gpt-4o"][k], "human_1_outcome": humans["human_1"][k],
         "human_2_outcome": humans["human_2"][k]} for k in ids]}, indent=2))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
