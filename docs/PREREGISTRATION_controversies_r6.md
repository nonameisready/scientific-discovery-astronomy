# Pre-registration 6: confirmatory test of "early decline" and "over-claiming"

Round 5 (`results/controversies/RESULTS.md`) did not support its primary score. Two signals came out of it:
- **Early decline**: pre-specified, AUC 0.71, p = 0.051.
- **Over-claiming**: post hoc, AUC 0.75, p = 0.021.

This round tests both on new cases. Three rules make the test honest:
- the cases are selected by a mechanical rule;
- the outcomes are labelled by people who never see the features;
- the analyst does not see outcome labels until predictions are frozen.

## Frozen in advance (nothing is refitted on round-6 data)

**Lexicon and features.** These are byte-identical to round 5 (`controversies/features.py`, commit 8179b27):
- `confirm`: the share of window abstracts with "we detect / confirm / detection of" language;
- `growth`: log((papers in months 12–24 + 1) / (papers in months 0–12 + 1)).

**Normalisation.** The z-norms are taken from round 5 and not refitted:

| Feature | Mean | SD |
|---|---|---|
| confirm | 0.22234 | 0.13806 |
| growth | −0.50568 | 0.80063 |

**Primary score.** T = z(confirm) − z(growth). A higher T predicts *dissolved*.

## Case selection (mechanical, outcome-blind)

1. **Candidate claim papers.** These are astro-ph primary papers with:
   - a v1 date between 2006-01-01 and 2021-10-14, which leaves at least five years for an outcome to emerge by 2026-10;
   - a claim word in the title: evidence for/of, detection of, discovery of, hint(s) of/for, anomaly/anomalous, excess, tension, discrepancy, unexpected, puzzle, signal/signature of, indication.
2. **Ranking.** Candidates are ranked by Semantic Scholar citations per year since publication. The top 200 go to screening. Ties are broken by arXiv id.
3. **Screening (Packet A).** Labellers see only the title, abstract and arXiv id. They answer two questions:
   - Is this a claim of an anomalous or unexpected result that other groups went on to test or dispute? Yes / no.
   - If yes, what short key phrase identifies it in later papers?

   Cases where both labellers say yes enter the study. Duplicates of one claim are merged, keeping the earliest paper. The 23 round-5 cases are removed.
4. **Queries and features.** The analyst writes each case's query from the key phrases, before any outcome label exists. The case keeps its onset date (the claim paper's v1 date) and its 24-month window.
5. **Inclusion.** A case is kept only if both:
   - its window has at least 10 papers;
   - its window is complete, meaning it ends before the corpus end. This rule was missing in round 5.

## Outcome labelling (Packet B, blind)

**Who labels.** At least two people with astronomy training who are not the analyst. They see only the claim paper and the case description. They never see features, scores or the hypotheses' direction.

**Labels**, as of 2026-10, following the round-5 definitions:

| Label | Meaning |
|---|---|
| dissolved | attributed to systematics, instruments, data processing or a mundane cause, or failed confirmation with more sensitive data |
| confirmed | accepted as real |
| open | still contested |
| can't tell | the labeller cannot judge |

Each labeller also gives a one-line reason and, where possible, a reference.

**Final label.** A case is in the analysis only if both labellers give the same label, with "can't tell" counting as disagreement. Agreement (Cohen's κ) is reported.

## Freeze order (enforced by commit history)

1. This document and the selection code.
2. The Packet A pool, before screening.
3. The screened case list, queries, window papers, features and **T scores**. These are frozen with SHA-256 digests (`FREEZE_r6.json`), before Packet B is sent.
4. Packet B labels are committed as returned.
5. The analysis.

## Hypotheses

- **H1 (primary).** AUC of T for dissolved vs not dissolved (confirmed + open) > 0.5. Test: one-sided permutation p < 0.05 (20,000 permutations, seed 7). Also reported: a stratified bootstrap 95% CI.
- **H2.** AUC of −growth > 0.5, one-sided.
- **H3.** AUC of confirm > 0.5, one-sided.
- **Baseline.** Window size alone, −log n.
- **Power.** With about 30 agreed cases, an AUC of about 0.70 is detectable at p < 0.05. If fewer than 20 cases have agreed labels, the round is reported as underpowered and is not interpreted.

## What would count as failure

H1 not significant means the round-5 signals were noise, or were specific to cases the analyst picked. That will be reported as such. No feature, lexicon or normalisation will be changed after Packet B arrives.

## Amendment 1 (2026-10-17, before any screening or outcome label exists)

Only one human labeller is available. The labelling panel is therefore:

| Labeller | Identity |
|---|---|
| H | Hui Mao |
| A1 | OpenAI `gpt-5.5-2026-04-23` |
| A2 | Google `gemini-3.1-pro-preview` |

Each labeller works independently.

**AI labellers.** A1 and A2 receive exactly the human instructions (`INSTRUCTIONS_packet_A.md`, and later Packet B's). Each row is sent in a separate request. They never receive features, scores or hypotheses. Their outputs are written to `data/controversies/r6/sealed/`. A SHA-256 digest of those outputs is committed before H returns a sheet. H agrees not to open the sealed folder until H's own sheet is committed.

**Screening.** A case enters the study if at least 2 of the 3 labellers say yes.

**Outcome.** The label is the 2-of-3 majority among dissolved, confirmed and open. "Can't tell" is not a vote. Cases without a majority are excluded.

**Agreement.** Pairwise Cohen's κ is reported for H–A1, H–A2 and A1–A2.

**Sensitivity analyses** (H1 repeated on each):
- H's labels alone;
- cases where A1 and A2 agree, which is the AI-only panel.

**Disclosed limitations:**
- Unlike the original plan, H knows the hypotheses. H should base each outcome label on the literature and cite a reference.
- The two AI labellers may know outcomes from their training data. This is acceptable for outcome labelling, which needs truth, not blindness. It is the reason they never see features.

## Amendment 2 (2026-10-17, before any human label exists)

**What changed.** A2 is now Google `gemini-3.8-flash`. It replaces `gemini-3.1-pro-preview`, which A2 was assigned in Amendment 1.

**Why.**
- The available Google key is on the free tier.
- On that tier, Pro models have zero quota. Every request in the first A2 run returned HTTP 429. That run is kept in git history (commit 258f5f2) and contains no labels.
- A2 is rerun with lower concurrency to stay within free-tier rate limits.

**What did not change.** The prompt and the rows are identical.
