# Ordinal Scoring and Forecast Calibration

## Do not create false precision

Use gate labels, evidence, and dominance comparisons instead of a weighted
master score. A score such as `87/100` is prohibited unless every component,
weight, scale, validation set, and calibration result was fixed before the
outcome period.

## Candidate comparison

Candidate A dominates candidate B only when:

- A is no worse on every required gate;
- A is better on at least one decision-relevant gate; and
- neither candidate has an unresolved authority or data failure.

When candidates trade strengths across gates, report the trade-off rather than
manufacturing a rank. Use deterministic tie-breaks only after all mandatory
gates pass: lower verified portfolio overlap, lower verified effective leverage,
better liquidity, and then alphabetical ticker.

## Confidence labels

- `HIGH`: primary evidence and market data agree, material contradictions are
  resolved, and the conclusion is stable under the stated sensitivity range.
- `MEDIUM`: evidence is adequate but one material input or scenario remains
  conditional.
- `LOW`: evidence is incomplete, weak, stale, or highly sensitive. A low-
  confidence output cannot upgrade an action.

Confidence measures evidence support, not expected return.

## Probability forecasts

Use a numerical probability only when the forecast defines:

- event and horizon;
- evidence cutoff;
- base rate or model basis;
- mutually exclusive outcome set;
- resolution source and date;
- later scoring method.

Otherwise rank scenarios without percentages. When probabilities are used,
require them to sum to one within one percentage point.

## Calibration review

Evaluate comparable forecasts with:

- Brier score for binary or categorical probabilities;
- reliability bins only when the sample is large enough to avoid disclosure of
  misleading percentages;
- directional hit rate and benchmark-relative result as secondary context;
- calibration by forecast type, horizon, and regime;
- explicit unresolved and censored outcomes.

Run calibration no more frequently than monthly or after twenty comparable
resolved forecasts. Never change policy from one successful or failed trade.
Require a versioned proposal, out-of-sample evidence, and human approval before
any calibration finding changes a deterministic threshold.
