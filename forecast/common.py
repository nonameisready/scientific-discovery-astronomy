"""Shared configuration: vendored Papers 2-4, study windows, file layout.

Every path is relative to the repository root, which is also the working
directory Paper 3's pipeline expects (it resolves ``data/raw/...``,
``data/corpus/...`` and ``data/cache/llm`` against the CWD).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

PAPER2 = ROOT / "vendor" / "paper2"
PAPER3 = ROOT / "vendor" / "paper3"
PAPER4 = ROOT / "vendor" / "paper4"
for p in (PAPER3, PAPER4 / "src", PAPER4 / "experiments"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Last complete day of the arXiv snapshot harvested for this study.
SNAPSHOT_END = "2026-10-14"

# Study 1 - out-of-time backtest at a cutoff Paper 3 never used. Paper 3's
# model was fit on cutoffs 2012-2020 with labels through 2025-12-31; the
# 2021 cohort's questions, features and outcomes are all new.
BACKTEST = {
    "name": "backtest2021",
    "cutoff_year": 2021,
    "cutoff_date": "2021-12-31",
    "past_window": ("2014-01-01", "2021-12-31"),  # Paper 3: 8 years
    # Paper 3 uses 5 years; the snapshot allows 4.79 (2022-01-01 .. 2026-10-14).
    "future_window": ("2022-01-01", SNAPSHOT_END),
}

# Extra out-of-time cohorts added in round 2 (pre-registered in
# docs/PREREGISTRATION_v2.md before generation). 2019 keeps Paper 3's full
# 5-year window; 2022's window is limited by the snapshot (3.79 years).
BACKTEST_2019 = {
    "name": "backtest2019",
    "cutoff_year": 2019,
    "cutoff_date": "2019-12-31",
    "past_window": ("2012-01-01", "2019-12-31"),
    "future_window": ("2020-01-01", "2024-12-31"),
}
BACKTEST_2022 = {
    "name": "backtest2022",
    "cutoff_year": 2022,
    "cutoff_date": "2022-12-31",
    "past_window": ("2015-01-01", "2022-12-31"),
    "future_window": ("2023-01-01", SNAPSHOT_END),
}

# Round-3 fresh cohorts (docs/PREREGISTRATION_v3.md). 2017 is the earliest
# cutoff with any leak-free Paper 3 training labels (cutoff 2012, window to
# 2017); 2023's window is limited by the snapshot (2.79 years).
BACKTEST_2017 = {
    "name": "backtest2017",
    "cutoff_year": 2017,
    "cutoff_date": "2017-12-31",
    "past_window": ("2010-01-01", "2017-12-31"),
    "future_window": ("2018-01-01", "2022-12-31"),
}
BACKTEST_2023 = {
    "name": "backtest2023",
    "cutoff_year": 2023,
    "cutoff_date": "2023-12-31",
    "past_window": ("2016-01-01", "2023-12-31"),
    "future_window": ("2024-01-01", SNAPSHOT_END),
}

# Study 2 - genuinely prospective forecast, scored no earlier than 2031-10-15.
PROSPECTIVE = {
    "name": "prospective2026",
    "cutoff_year": 2026,
    "cutoff_date": SNAPSHOT_END,
    "past_window": ("2018-10-15", SNAPSHOT_END),
    "future_window": ("2026-10-15", "2031-10-14"),
}

# Paper 2's frozen prospective instance (cutoff 2026-08-17), scored with the
# same model in its own subfield and cutoff.
PAPER2_PROSPECTIVE = {
    "name": "paper2_prospective2026",
    "cutoff_year": 2026,
    "cutoff_date": "2026-08-17",
    "past_window": ("2018-08-18", "2026-08-17"),
    "future_window": ("2027-01-01", "2030-12-31"),  # Paper 2's pre-registered window
}


def study_dir(name: str) -> Path:
    d = ROOT / "data" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).open(encoding="utf-8") if l.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
