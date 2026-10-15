"""Build the classified corpus and the environment statistics.

1. Runs Paper 3's own ``corpus.build_processed`` over the OAI shards
   (dedup + the same keyword subfield classifier).
2. Computes per-subfield-per-year counts from this harvest and compares them
   with Paper 3's published counts for every overlapping year, so any drift
   between the two harvests is measured rather than assumed away.
3. Writes the statistics file the feature pipeline reads. Environment
   features must be measured the way the model was trained, so every year
   Paper 3 covers (<= 2025) uses Paper 3's committed counts verbatim. Only
   2026 comes from this harvest: scaled by the per-subfield ratio of the two
   harvests on 2024-2025 and annualized for the part-year to the snapshot
   end. The 2021 backtest touches only years <= 2021, so its environment
   features are exactly Paper 3's.

Usage:
    python -m forecast.corpus_build
"""

from __future__ import annotations

import json
from datetime import date

from forecast.common import PAPER3, ROOT, SNAPSHOT_END

from pipeline import corpus, subfields  # noqa: E402  (Paper 3, vendored)

OAI_STATS = ROOT / "data" / "corpus" / "oai_subfield_year_stats.json"
COMPARISON = ROOT / "data" / "corpus" / "harvest_comparison.json"
HYBRID_STATS = ROOT / corpus.STATS_PATH  # data/corpus/subfield_year_stats.json
PAPER3_STATS = PAPER3 / "data" / "corpus" / "subfield_year_stats.json"


def main() -> None:
    n = corpus.build_processed()
    print(f"[corpus] {n} deduplicated records")
    oai = corpus.build_stats(out_path=OAI_STATS)
    p3 = json.loads(PAPER3_STATS.read_text())

    comparison = {"total": {}, "subfields": {}}
    for y in range(2014, 2026):
        a = p3["total_by_year"].get(str(y), 0)
        b = oai["total_by_year"].get(y, 0)
        comparison["total"][y] = {"paper3": a, "this_harvest": b, "ratio": round(b / a, 4) if a else None}
    for key in subfields.SUBFIELD_KEYS:
        rows = {}
        for y in range(2014, 2026):
            a = p3["subfields"][key]["papers_by_year"].get(str(y), 0)
            b = oai["subfields"][key]["papers_by_year"].get(y, 0)
            rows[y] = {"paper3": a, "this_harvest": b, "ratio": round(b / a, 4) if a else None}
        comparison["subfields"][key] = rows

    # Hybrid statistics: Paper 3 verbatim for <= 2025, scaled 2026 from here.
    end = date.fromisoformat(SNAPSHOT_END)
    annualize = 365.0 / (end - date(end.year, 1, 1)).days
    hybrid = json.loads(PAPER3_STATS.read_text())
    tot_ratio = sum(p3["total_by_year"][str(y)] for y in (2024, 2025)) / max(
        1, sum(oai["total_by_year"].get(y, 0) for y in (2024, 2025))
    )
    hybrid["total_by_year"]["2026"] = round(oai["total_by_year"].get(2026, 0) * tot_ratio * annualize)
    scale_2026 = {}
    for key in subfields.SUBFIELD_KEYS:
        s3, so = p3["subfields"][key], oai["subfields"][key]
        ratio = sum(s3["papers_by_year"].get(str(y), 0) for y in (2024, 2025)) / max(
            1, sum(so["papers_by_year"].get(y, 0) for y in (2024, 2025))
        )
        scale_2026[key] = round(ratio * annualize, 4)
        hybrid["subfields"][key]["papers_by_year"]["2026"] = round(
            so["papers_by_year"].get(2026, 0) * ratio * annualize
        )
        hybrid["subfields"][key]["reviews_by_year"]["2026"] = round(
            so["reviews_by_year"].get(2026, 0) * ratio * annualize
        )
    hybrid["_provenance"] = {
        "years_le_2025": "Paper 3 committed statistics, verbatim",
        "year_2026": (
            f"this OAI harvest through {SNAPSHOT_END}, scaled by the Paper3/OAI "
            "2024-2025 ratio per subfield and annualized"
        ),
        "annualize_factor": round(annualize, 4),
        "scale_2026": scale_2026,
    }
    comparison["scale_2026"] = scale_2026
    HYBRID_STATS.write_text(json.dumps(hybrid, indent=2))
    COMPARISON.write_text(json.dumps(comparison, indent=2))
    print(json.dumps(comparison["total"], indent=1))


if __name__ == "__main__":
    main()
