# Vendored upstream code and data (verbatim copies)

| Dir | Source repository | Commit | What is used |
| --- | --- | --- | --- |
| `paper2/prospective_2026/` | nonameisready/scientific-question-discovery-benchmark | `5adf210` | the 200 questions frozen 2026-08-17 (+ their SHA256SUMS) |
| `paper3/pipeline/` | nonameisready/scientific-question-outcome-prediction-indicators | `9b842fb` | generators, miners, subfield classifier, features, labeling judge, models, structure features |
| `paper3/data/` | same | `9b842fb` | the 980 frozen questions, features, labels and structure features used as training data |
| `paper3/run_models.py`, `run_structure_prior.py` | same | `9b842fb` | reference only |
| `paper4/src/`, `configs/`, `experiments/paper3_benchmark.py` | nonameisready/scientific-evidence-planner | `d3b6148` | planner, utility configs, tension-cluster → evidence-graph conversion |

Nothing under `vendor/` is modified. Paper 1 (nonameisready/scientific-question-discovery)
enters through Paper 3's `evidence_tension` generator, which re-implements its
evidence-tension mining over arXiv abstracts.
