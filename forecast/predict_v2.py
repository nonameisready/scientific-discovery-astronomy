"""Score a cohort with the version-2 models (``forecast.models_v2``).

Uses the same leak-free training set as the cohort's primary v1 model
(``forecast.predict.PRIMARY_TRAIN``) and writes ``predictions_v2.jsonl``
next to the frozen v1 predictions, which are left untouched.

Usage:
    python -m forecast.predict_v2 backtest2019
"""

from __future__ import annotations

import json
import sys

from forecast.common import study_dir, write_jsonl
from forecast.models_v2 import fit_predict_v2
from forecast.predict import PRIMARY_TRAIN, TRAIN_SETS, TRAIN_SETS_V2, cohort_table, paper3_table


def main() -> None:
    name = sys.argv[1]
    tag = PRIMARY_TRAIN[name]
    cutoffs = {**TRAIN_SETS, **TRAIN_SETS_V2}[tag]
    train = paper3_table()
    train = train[train.cutoff_year.isin(cutoffs)].reset_index(drop=True)
    test = cohort_table(name)
    scores, info = fit_predict_v2(train, test, tag)
    scores.insert(1, "source", test["source"].values)
    scores.insert(2, "subfield", test["subfield"].values)
    write_jsonl(study_dir(name) / "predictions_v2.jsonl", scores.to_dict(orient="records"))
    (study_dir(name) / "models_v2_info.json").write_text(
        json.dumps({"train_tag": tag, "train_cutoffs": list(cutoffs), "n_train": len(train), **info}, indent=2)
    )
    print(f"[predict_v2] {name}: {len(scores)} rows, {info}")


if __name__ == "__main__":
    main()
