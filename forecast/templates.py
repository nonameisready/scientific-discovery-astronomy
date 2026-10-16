"""Round 4 (docs/PREREGISTRATION_v4.md): LLM-free questions and their v3 scores.

Builds template questions from the same deterministic evidence Paper 3's
generators use -- tension clusters and author future-work statements -- with
no language model anywhere, computes their momentum features at the cutoff,
scores them with v3 (same leak-free training set as the cohort of that
cutoff), and writes ``data/templates/<cohort>/{questions,momentum,predictions_v3}.jsonl``.

Usage:
    python -m forecast.templates            # build + score all five cutoffs
"""

from __future__ import annotations

import random
from collections import defaultdict

import pandas as pd

from forecast.common import ROOT, read_jsonl, write_jsonl
from forecast.cohort import STUDIES
from forecast.models_v3 import fit_predict_v3
from forecast.momentum import SubfieldIndex, features_for
from forecast.predict import PRIMARY_TRAIN, TRAIN_SETS, TRAIN_SETS_V2, paper3_table

from pipeline import corpus, generate, mine, subfields  # noqa: E402

COHORTS = ("backtest2017", "backtest2019", "backtest2021", "backtest2022", "backtest2023")
OUT = ROOT / "data" / "templates"
TENSION_T = ('What explains the tension reported here, and does it reflect a real effect or a systematic '
             'or analysis artifact? "{s}"')
FUTURE_T = 'How can this open problem be resolved? "{s}"'


def build(name: str) -> list[dict]:
    study = STUDIES[name]
    cy = study["cutoff_year"]
    out = []
    for sub in subfields.SUBFIELDS:
        past = corpus.load_subfield_docs(sub.key, *study["past_window"])
        rng = random.Random(f"{sub.key}-{cy}")  # the cohort generator's seed
        clusters = generate.build_tension_clusters(mine.mine_tension(past))[: generate.QUOTA["evidence_tension"]]
        fw = generate.pick_future_work_sentences(mine.mine_future_work(past), generate.QUOTA["future_work"], rng)
        i = 0
        for cl in clusters:
            out.append({
                "question_id": f"tpl-{sub.key}-{cy}-{i:03d}", "question": TENSION_T.format(s=cl[0]["sentence"]),
                "source": "template_tension", "control_subtype": None, "subfield": sub.key, "cutoff_year": cy,
                "cutoff_date": study["cutoff_date"],
                "source_material": {"cluster": [{k: s[k] for k in ("arxiv_id", "published", "sentence")} for s in cl]},
            })
            i += 1
        for s in fw:
            out.append({
                "question_id": f"tpl-{sub.key}-{cy}-{i:03d}", "question": FUTURE_T.format(s=s["sentence"]),
                "source": "template_future_work", "control_subtype": None, "subfield": sub.key, "cutoff_year": cy,
                "cutoff_date": study["cutoff_date"],
                "source_material": {"statement": {k: s[k] for k in ("arxiv_id", "published", "sentence")}},
            })
            i += 1
    return out


def main() -> None:
    train_all = paper3_table().merge(pd.DataFrame(read_jsonl(ROOT / "data" / "paper3_momentum.jsonl")),
                                     on="question_id")
    questions = {name: build(name) for name in COHORTS}
    idx_cache: dict[str, SubfieldIndex] = {}
    for name, qs in questions.items():
        study = STUDIES[name]
        groups = defaultdict(list)
        for q in qs:
            groups[q["subfield"]].append(q)
        mom = []
        for key, g in groups.items():
            if key not in idx_cache:
                idx_cache[key] = SubfieldIndex(key)
            mom += features_for(g, idx_cache[key], tuple(study["past_window"]), study["cutoff_year"])
        d = OUT / name
        write_jsonl(d / "questions.jsonl", qs)
        write_jsonl(d / "momentum.jsonl", mom)
        tag = PRIMARY_TRAIN[name]
        train = train_all[train_all.cutoff_year.isin({**TRAIN_SETS, **TRAIN_SETS_V2}[tag])].reset_index(drop=True)
        test = pd.DataFrame(qs).merge(pd.DataFrame(mom), on="question_id")
        scores, info = fit_predict_v3(train, test, tag)
        scores.insert(1, "source", test["source"].values)
        write_jsonl(d / "predictions_v3.jsonl", scores.to_dict(orient="records"))
        print(f"[templates] {name}: {len(qs)} questions "
              f"({sum(q['source'] == 'template_tension' for q in qs)} tension), v3 {info}", flush=True)


if __name__ == "__main__":
    main()
