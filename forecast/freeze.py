"""Freeze a cohort's questions and predictions with SHA-256 digests.

Writes ``data/<study>/FREEZE.json``. ``forecast.label`` refuses to run
without it, and the freeze commit is pushed before any label exists, so the
public git history shows the predictions predate the outcomes.

Usage:
    python -m forecast.freeze backtest2021
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time

from forecast.common import ROOT, sha256, study_dir
from forecast.cohort import STUDIES
from forecast.predict import PRIMARY_TRAIN, TRAIN_SETS

FILES = (
    "questions.jsonl",
    "features.jsonl",
    "structure_features.jsonl",
    "planner.jsonl",
    "predictions.jsonl",
    "predictions_v2.jsonl",
)


def main() -> None:
    name = sys.argv[1]
    d = study_dir(name)
    digests = {f: sha256(d / f) for f in FILES if (d / f).exists()}
    combined = hashlib.sha256("".join(f"{v}  {k}\n" for k, v in sorted(digests.items())).encode()).hexdigest()
    corpus_manifest = ROOT / "data" / "corpus" / "corpus_manifest.json"
    freeze = {
        "study": name,
        "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cutoff_date": STUDIES[name]["cutoff_date"],
        "past_window": STUDIES[name]["past_window"],
        "outcome_window": STUDIES[name]["future_window"],
        "primary_score": f"m_logistic__{PRIMARY_TRAIN[name]}",
        "training_cutoffs": {k: list(v) for k, v in TRAIN_SETS.items()},
        "sha256": digests,
        "combined_sha256": combined,
        "corpus_sha256": json.loads(corpus_manifest.read_text())["corpus_sha256"] if corpus_manifest.exists() else None,
        "code_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
        or None,
        "preregistration": "docs/PREREGISTRATION.md",
    }
    (d / "FREEZE.json").write_text(json.dumps(freeze, indent=2))
    print(json.dumps(freeze, indent=2))


if __name__ == "__main__":
    main()
