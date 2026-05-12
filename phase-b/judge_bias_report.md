# Judge Bias Report

## Summary

- Pairwise comparisons: 30
- A wins when listed first: 20/30 (66.7%)
- First-position wins after swap run: 4/30 (13.3%)
- Swap disagreement rate: 1/30 (3.3%)
- Longer answer win rate: 4/22 (18.2%)
- Cross-judge tie/escalation rate: 10/30 (33.3%)

## Bias 1: Position Bias

The judge was run twice for each pair: original order and swapped order. The swapped result was normalized back to A/B before aggregation.

| Metric | Value | Interpretation |
|---|---:|---|
| A-first win rate | 66.7% | Expected near content quality, not necessarily 50% because A is the production answer. |
| Swap disagreement rate | 3.3% | Disagreements are converted to tie to avoid overclaiming. |

Mitigation: keep swap-and-average for production monitoring and send ties to human review or a stronger judge.

## Bias 2: Length Bias

| Metric | Value | Interpretation |
|---|---:|---|
| Longer answer win rate | 18.2% | Values far above 55% would suggest length bias. |

Mitigation: score conciseness independently and cap answer length in the production prompt.

## Bonus: Cross-Judge Protocol

This repo implements a lightweight cross-judge protocol: an accuracy-first judge and a conciseness-aware judge. If they disagree, the aggregate winner is `tie`, which is safer for monitoring than forcing a winner.

## Production Decision

Use pairwise judge for regression detection, not as the only source of truth. Keep human calibration weekly and re-run Cohen's kappa whenever the prompt or model changes.
