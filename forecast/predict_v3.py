"""Score a cohort with the version-3 model (``forecast.models_v3``).

Same leak-free training set as the cohort's primary v1/v2 models; writes
``predictions_v3.jsonl``. Needs ``momentum.jsonl`` for the cohort and
``data/paper3_momentum.jsonl`` (``python -m forecast.momentum``).

Usage:
    python -m forecast.predict_v3 backtest2023
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from forecast.common import ROOT, read_jsonl, study_dir, write_jsonl
from forecast.models_v3 import fit_predict_v3
from forecast.predict import PRIMARY_TRAIN, TRAIN_SETS, TRAIN_SETS_V2, cohort_table, paper3_table


def main() -> None:
    name = sys.argv[1]
    tag = PRIMARY_TRAIN[name]
    cutoffs = {**TRAIN_SETS, **TRAIN_SETS_V2}[tag]
    train = paper3_table().merge(pd.DataFrame(read_jsonl(ROOT / "data" / "paper3_momentum.jsonl")), on="question_id")
    train = train[train.cutoff_year.isin(cutoffs)].reset_index(drop=True)
    test = cohort_table(name).merge(pd.DataFrame(read_jsonl(study_dir(name) / "momentum.jsonl")), on="question_id")
    scores, info = fit_predict_v3(train, test, tag)
    scores.insert(1, "source", test["source"].values)
    scores.insert(2, "subfield", test["subfield"].values)
    write_jsonl(study_dir(name) / "predictions_v3.jsonl", scores.to_dict(orient="records"))
    (study_dir(name) / "models_v3_info.json").write_text(
        json.dumps({"train_tag": tag, "train_cutoffs": list(cutoffs), "n_train": len(train), **info}, indent=2)
    )
    print(f"[predict_v3] {name}: {len(scores)} rows, {info}")


if __name__ == "__main__":
    main()
