# Pre-registration 5: forecasting how astronomy controversies end

Committed before any feature in `controversies/features.py` was computed and before `controversies/analyze.py` was run. The case list, the window papers (`data/controversies/papers.jsonl`) and their counts had been extracted at that point. Only paper counts and a few random titles per case were inspected, to check query precision.

## Question

Rounds 1–4 forecast whether a question would be *taken up*, not how it would end. Here we ask:

> From the first 24 months of arXiv literature after a claimed anomaly appears, can we tell whether it will **dissolve** or not?

Dissolving means being traced to systematics, instruments, data processing or a mundane cause, or failing confirmation with better data. Not dissolving means being confirmed or still being open.

## Cases and outcomes (`controversies/cases.py`)

**Candidates.** 33 historical candidates. The list was extended once, before any features were computed, to add dissolved cases. Each case has:
- an onset date: the v1 date of the first claim;
- a regex over title + abstract;
- an outcome as of 2026-10:
  - `dissolved`: 19 candidates;
  - `confirmed`: 6;
  - `open`: 8;
- a one-line justification;
- a `provisional` flag where a reasonable expert could dispute the label.

There are also five live controversies with unknown outcomes: JWST early massive galaxies, little red dots, DESI evolving dark energy, the K2-18 b biosignature claim, and the KM3NeT 220 PeV neutrino.

**Inclusion rule.** A case enters the analysis if it has at least 10 window papers in the 332k-paper astro-ph corpus. This rule depends on data volume only.

| | Cases |
|---|---|
| Included | 23 historical: 13 dissolved (5 provisional) and 10 not dissolved (4 confirmed, 6 open, 1 of them provisional); all 5 live cases |
| Excluded by the rule | dark flow, α-dipole, perytons, α Cen Bb, Barnard b, Fomalhaut b, FRB 2007–09, odd radio circles, S8 tension, Galactic-centre GeV excess |

A note on the GeV excess: it was described in the earlier plan as a "dissolved" case. That was wrong. It is labelled `open` here, and it is excluded because its 2009–11 literature is too sparse to match the query.

**Query fixes.** Before features existed, three queries were corrected for precision, based on sampled titles:
- `ARCADE` and `EDGES` are now case-sensitive. Case-insensitive, they matched "coronal arcade" and "edges".
- `GC` was removed from the Galactic-centre query. It matched globular clusters.

## Features (`controversies/features.py`, no language model)

Each feature is the share of window abstracts matching a fixed, generic lexicon:

| Feature | What it captures |
|---|---|
| `null` | non-detection or refutation language |
| `systematics` | systematics or instrumental language |
| `confirm` | confirmation or detection language |
| `exotic` | new-physics language (exploratory only) |
| `growth` | log ratio of papers in months 12–24 to months 0–12 |
| `log_n` | log of the window size (baseline) |

No language model reads any text, so what a model knows about how a case ended cannot leak in. This follows the "no rater in the loop" rule of the claim-verifier repository. Note that the claim-verifier itself checks physical consistency, not stance, so it is not used.

## Hypotheses (one-sided unless noted)

- **H1 (primary).** The pre-specified score S = z(null) + z(systematics) − z(confirm) − z(growth) has AUC > 0.5 for dissolved vs not dissolved.
  - Test: permutation p < 0.05 (20,000 permutations, seed 7).
  - Also reported: a stratified bootstrap 95% CI.
- **H2.** H1 still holds without the provisional labels. This is reported as a sensitivity check whatever its outcome.
- **H3.** Each component has AUC > 0.5 in its signed direction: null↑, systematics↑, confirm↓, growth↓.
- **H4 (baseline).** Window size alone (smaller means more likely to dissolve) is reported for comparison. S should beat it.
- **Leave-one-out.** For each case, z-norms and the logistic model are refitted without that case before predicting it. The resulting AUC is reported.
- **Exploratory.** The `exotic` share, two-sided.

## Sealed forecast

A logistic model on S, fitted on all included historical cases, gives P(dissolved) for each live controversy. Predictions and SHA-256 digests are written to `results/controversies/FREEZE_forecast.json` and committed.

They will be scored in **2031-10** against the same outcome definitions. A live case counts as dissolved if a collaboration paper or review published by then attributes it to systematics or a mundane cause, or reports a more sensitive non-confirmation.

## Known threats, stated in advance

- **The analyst knew the historical outcomes when choosing cases, queries and lexicons.** Mitigations:
  - lexicons contain only generic terms; case-specific causes such as "dust", "stellar activity" and "interference" are left out;
  - no feature values were seen before this commit;
  - the sealed live forecast is the only fully clean test.
- **The sample is small.** With n = 23 (13 vs 10), an AUC of about 0.72 is needed for p < 0.05, so this is a pilot.
- **Dissolved cases are skewed toward single-object and exoplanet claims.** Window size is reported as a baseline to show how much of the signal is just volume.
