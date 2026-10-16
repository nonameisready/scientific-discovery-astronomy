# Round 5 results: forecasting how astronomy controversies end

Pre-registration: `docs/PREREGISTRATION_controversies.md` (commit 8179b27). Full numbers: `analysis.json`. Sealed forecast: `FREEZE_forecast.json`.

## Pre-registered tests

| Test | n (dissolved / not) | AUC | One-sided p | 95% CI |
|---|---|---|---|---|
| H1: score S, all cases | 23 (13 / 10) | 0.531 | 0.42 | [0.28, 0.78] |
| H2: S, without provisional labels | 17 (8 / 9) | 0.625 | 0.21 | [0.33, 0.89] |
| H4: window-size baseline | 23 | 0.481 | – | – |
| Leave-one-out logistic on S | 23 | 0.04 | – | – |

H1 and H2 are **not supported**. The leave-one-out AUC of 0.04 is the usual artefact of fitting a model with no signal and leaving one case out each time; it is not a real anti-correlation.

### H3: single features, in their pre-registered direction

| Feature | Direction | AUC | Permutation p |
|---|---|---|---|
| growth | slower growth → dissolved | 0.708 | 0.051 |
| systematics | more → dissolved | 0.531 | – |
| null | more → dissolved | 0.485 | – |
| confirm | less → dissolved | **0.246** | – |

Only growth comes close to significance. The confirm feature points the *opposite* way from the hypothesis.

## Exploratory (post hoc, not pre-registered)

- **Confirmation language.** Taken in the reversed direction, more "we detect / confirm / detection of" language in the first two years → dissolved has AUC 0.754, p = 0.021. This is one of six feature tests and the direction was chosen after seeing the data. It reads as "hype predicts dissolution", but it is a hypothesis for the next round, not a finding.
- **Growth** is the only pre-specified signal near significance. Literature that shrinks in year 2 relative to year 1 tends to belong to claims that later dissolve: BICEP2, Venus phosphine, the 130 GeV line, GBM–GW150914.

## Sealed forecast (pre-registered model)

Because the logistic model on S carries almost no signal, its outputs sit near the base rate:

| Live case | P(dissolved) |
|---|---|
| JWST early massive galaxies | 0.63 |
| Little red dots | 0.63 |
| K2-18 b | 0.60 |
| DESI evolving dark energy | 0.58 |
| KM3NeT 220 PeV neutrino | 0.57 |

They are frozen as pre-registered and will be scored in 2031-10. They should not be read as informative.

## Deviation

KM3NeT's onset is 2025-02-12, so its 24-month window runs past the corpus end (2026-10-14). It has 20 of 24 months, which biases its growth feature downward. The window-completeness check should have been in the inclusion rule. KM3NeT's forecast is therefore marked uninterpretable.

## What to do next

A proper test of "hype and decline predict dissolution" needs:
- a fresh pre-registration with those two features in their now-stated directions;
- new cases not used here, for example from other fields' anomaly lists, or arXiv cases from before 2005 once the corpus is extended back;
- an outcome labelled blind by someone other than the analyst.
