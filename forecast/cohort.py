"""Build a question cohort with Paper 3's generators and cutoff-time features.

For each of Paper 3's eight subfields this:

1. generates questions with Paper 3's four sources and quotas (Paper 1's
   evidence-tension generator, direct LLM, author future-work, controls),
   seeing only the pre-cutoff window;
2. computes Paper 3's six feature groups at the cutoff;
3. computes the evidence-graph structure features (Paper 2's outlook /
   Paper 3's structure prior) for tension-mined questions;
4. runs Paper 4's planner on every tension question at its cutoff, recording
   the ranked next-evidence actions.

Nothing in this module reads a document dated after the cutoff.

Usage:
    python -m forecast.cohort backtest2021
    python -m forecast.cohort prospective2026
    python -m forecast.cohort paper2_prospective2026   # features only, Paper 2's frozen questions
"""

from __future__ import annotations

import json
import random
import sys

from forecast.common import (
    BACKTEST,
    PAPER2,
    PAPER2_PROSPECTIVE,
    PAPER3,
    PROSPECTIVE,
    read_jsonl,
    study_dir,
    write_jsonl,
)

from pipeline import corpus, features, generate, mine, subfields  # noqa: E402
from pipeline.structure import structure_features  # noqa: E402

STUDIES = {s["name"]: s for s in (BACKTEST, PROSPECTIVE, PAPER2_PROSPECTIVE)}


# ------------------------------------------------------------- generation


def generate_cell_at(past_docs: list[dict], sub, cutoff_year: int, cutoff_date: str) -> list[dict]:
    """Paper 3's ``generate.generate_cell`` with the cutoff date as a parameter.

    Paper 3 hard-codes ``f"{cutoff_year}-12-31"``; the prospective cohort's
    cutoff is the snapshot day instead. For a Dec-31 cutoff the two are
    identical (same quotas, same seeded RNG, same prompts, same dedup).
    """
    rng = random.Random(f"{sub.key}-{cutoff_year}")
    tension_sents = mine.mine_tension(past_docs)
    fw_sents = mine.mine_future_work(past_docs)
    q = generate.QUOTA

    questions: list[dict] = []
    clusters = generate.build_tension_clusters(tension_sents)
    questions += generate.generate_tension_questions(clusters, sub.name, cutoff_date, q["evidence_tension"])
    questions += generate.generate_direct_questions(past_docs, sub.name, cutoff_date, q["direct_llm"], rng)
    questions += generate.generate_future_work_questions(fw_sents, sub.name, cutoff_date, q["future_work"], rng)
    questions += generate.generate_control_questions(past_docs, sub.name, cutoff_date, rng)

    questions = generate._dedupe(questions)
    for i, rec in enumerate(questions):
        rec["question_id"] = f"{sub.key}-{cutoff_year}-{i:03d}"
        rec["subfield"] = sub.key
        rec["cutoff_year"] = cutoff_year
        rec["cutoff_date"] = cutoff_date
        rec.setdefault("control_subtype", None)
    return questions


def generate_cohort(study: dict) -> list[dict]:
    out = []
    for sub in subfields.SUBFIELDS:
        past = corpus.load_subfield_docs(sub.key, *study["past_window"])
        qs = generate_cell_at(past, sub, study["cutoff_year"], study["cutoff_date"])
        by_src: dict[str, int] = {}
        for rec in qs:
            by_src[rec["source"]] = by_src.get(rec["source"], 0) + 1
        print(f"[cohort] {sub.key}: past={len(past)} questions={len(qs)} {by_src}", flush=True)
        out.extend(qs)
    return out


def load_paper2_questions() -> list[dict]:
    """Paper 2's frozen 2026 instance, mapped to Paper 3's record shape."""
    out = []
    for gen_dir in sorted((PAPER2 / "prospective_2026").iterdir()):
        if not gen_dir.is_dir():
            continue
        for rec in read_jsonl(gen_dir / "questions.jsonl"):
            out.append(
                {
                    "question_id": f"p2-{gen_dir.name}-{rec['question_id']}",
                    "question": rec["question"],
                    "source": f"paper2_{gen_dir.name}",
                    "control_subtype": None,
                    "subfield": rec["domain"],
                    "cutoff_year": 2026,
                    "cutoff_date": rec["cutoff_date"],
                    "source_material": {
                        "generation_system": rec["generation_system"],
                        "source_evidence_ids": rec["source_evidence_ids"],
                        "paper2_rank": rec["rank"],
                    },
                }
            )
    return out


# --------------------------------------------------------------- features


def cohort_features(study: dict, questions: list[dict]) -> list[dict]:
    stats = json.loads(corpus.STATS_PATH.read_text())
    records: dict[str, dict] = {}
    for sub in subfields.SUBFIELDS:
        qs = [q for q in questions if q["subfield"] == sub.key]
        if not qs:
            continue
        past = corpus.load_subfield_docs(sub.key, *study["past_window"])
        feats = features.compute_cell_features(qs, past, stats, sub.key, study["cutoff_year"])
        for q, f in zip(qs, feats):
            records[q["question_id"]] = f
        print(f"[features] {sub.key}: {len(qs)} questions, past corpus {len(past)}", flush=True)
    codes = features.falsifiability_llm_codes([q["question"] for q in questions])
    for q, c in zip(questions, codes):
        records[q["question_id"]].update(c)
    return [{"question_id": q["question_id"], **records[q["question_id"]]} for q in questions]


def cohort_structure(questions: list[dict], earlier: list[dict]) -> list[dict]:
    """Structure features; ``str_recurrent`` against all earlier-cutoff tension
    questions (Paper 3's 2012-2020 set plus any earlier cohort here)."""
    prior_ids = []
    for q in earlier:
        cluster = (q.get("source_material") or {}).get("cluster")
        if cluster and q["cutoff_year"]:
            prior_ids.append((q["subfield"], q["cutoff_year"], {c.get("arxiv_id") for c in cluster}))
    out = []
    for q in questions:
        s = structure_features(q)
        if s is None:
            continue
        aids = {c.get("arxiv_id") for c in q["source_material"]["cluster"]}
        s["str_recurrent"] = int(
            any(sub == q["subfield"] and cy < q["cutoff_year"] and aids & a for sub, cy, a in prior_ids)
        )
        out.append(s)
    return out


# ----------------------------------------------------------- Paper 4 planner


def planner_outputs(questions: list[dict], structures: list[dict], config_name: str = "default") -> list[dict]:
    """Paper 4's scaled-benchmark conversion (tension cluster -> evidence graph)
    and planner run at the question's cutoff, unchanged."""
    import paper3_benchmark as p4  # vendored Paper 4 experiments script
    from planner import (
        ActionGenerator,
        GapAnalyzer,
        Planner,
        UtilityEstimator,
        load_question_dict,
        load_utility_config,
    )

    config = load_utility_config(p4.REPO_ROOT / "configs" / f"{config_name}.yaml")
    planner = Planner(UtilityEstimator(config=config))
    by_id = {s["question_id"]: s for s in structures}
    out = []
    for row in questions:
        s = by_id.get(row["question_id"])
        if s is None:
            continue
        question = load_question_dict(row)
        hypotheses = p4.make_hypotheses(question, s)
        hyp_ids = [h.hypothesis_id for h in hypotheses]
        graph = p4.build_graph(question, hyp_ids, s)
        visible = graph.filter_before(question.metadata["cutoff_date"])
        report = GapAnalyzer().analyze(question, hypotheses, visible)
        actions = ActionGenerator().generate(report)
        recs = planner.rank(actions, hypotheses, visible, top_k=p4.TOP_K)
        out.append(
            {
                "question_id": row["question_id"],
                "planner_config": config_name,
                "n_gaps": len(report.gaps),
                "top_k_utility": p4.top_k_utility(recs, p4.TOP_K),
                "expected_utility": p4.expected_utility(recs),
                "average_information_gain": p4.average_information_gain(recs),
                "hypotheses": [
                    {"id": h.hypothesis_id, "description": h.description, "prior": round(h.prior, 4)}
                    for h in hypotheses
                ],
                "recommendations": [
                    {
                        "rank": i + 1,
                        "action_type": r.action.action_type.value,
                        "description": r.action.description,
                        "reasoning": r.reasoning,
                        "utility": round(r.utility.total, 4),
                    }
                    for i, r in enumerate(recs)
                ],
            }
        )
    return out


def main() -> None:
    name = sys.argv[1]
    study = STUDIES[name]
    d = study_dir(name)
    qpath = d / "questions.jsonl"
    if qpath.exists():
        questions = read_jsonl(qpath)
        print(f"[cohort] reusing frozen {qpath} ({len(questions)})")
    else:
        questions = load_paper2_questions() if name == "paper2_prospective2026" else generate_cohort(study)
        write_jsonl(qpath, questions)

    write_jsonl(d / "features.jsonl", cohort_features(study, questions))

    earlier = read_jsonl(PAPER3 / "data" / "questions" / "questions_v1.jsonl")
    if name != "backtest2021" and (study_dir("backtest2021") / "questions.jsonl").exists():
        earlier += read_jsonl(study_dir("backtest2021") / "questions.jsonl")
    structures = cohort_structure(questions, earlier)
    write_jsonl(d / "structure_features.jsonl", structures)
    plans = planner_outputs(questions, structures, "default")
    plans += planner_outputs(questions, structures, "paper3_informed")
    write_jsonl(d / "planner.jsonl", plans)
    print(f"[cohort] {name}: {len(questions)} questions, {len(structures)} tension, {len(plans)} plans")


if __name__ == "__main__":
    main()
