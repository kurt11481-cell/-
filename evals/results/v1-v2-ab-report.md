# v1 vs v2 A/B Evaluation

## Conclusion

**OVERALL A/B STATUS: UNAVAILABLE**

An exact pre-v2 code snapshot exists at Git commit
`2419497e1f11873fa758dfc8eecdefa2e64572d0`. However, no case contains an
immutable evidence bundle that proves the publication time, effective time,
retrieval time, analysis cutoff, completed-session market data, portfolio
context, and valuation inputs seen identically by both versions. A true
code-version v1 vs v2 decision A/B test is therefore not possible from the
available evidence.

The v2 regression suite and the current shadow run are reported separately.
They are not relabeled as A/B evidence.

## Baseline Provenance

- Source: local Git history on `main`.
- Exact baseline: `2419497e1f11873fa758dfc8eecdefa2e64572d0`.
- Relationship: immediate parent of the v2 implementation commit.
- Code reconstruction: none.
- Point-in-time evidence bundles: unavailable.
- Details: `evals/baselines/v1/manifest.json`.

## Case Results

| Ticker | Cutoff | Baseline validity | v1 decision | v2 decision | Evidence difference | Risk difference | Decision-quality comparison | Critical-safety comparison | Outcome comparison |
|---|---|---|---|---|---|---|---|---|---|
| MRVL | unavailable | `INELIGIBLE_FOR_A_B` | not run | not run | no immutable shared bundle | not comparable | `NOT COMPARABLE` | `NOT COMPARABLE` | not eligible |
| SNDK | unavailable | `INELIGIBLE_FOR_A_B` | not run | not run | no immutable shared bundle | not comparable | `NOT COMPARABLE` | `NOT COMPARABLE` | not eligible |
| NBIS | unavailable | `INELIGIBLE_FOR_A_B` | not run | not run | no immutable shared bundle | not comparable | `NOT COMPARABLE` | `NOT COMPARABLE` | not eligible |
| AVGO | unavailable | `INELIGIBLE_FOR_A_B` | not run | not run | no immutable shared bundle | not comparable | `NOT COMPARABLE` | `NOT COMPARABLE` | not eligible |
| LITE | unavailable | `INELIGIBLE_FOR_A_B` | not run | not run | no immutable shared bundle | not comparable | `NOT COMPARABLE` | `NOT COMPARABLE` | not eligible |
| SOXL | unavailable | `INELIGIBLE_FOR_A_B` | not run | not run | no immutable shared bundle | not comparable | `NOT COMPARABLE` | `NOT COMPARABLE` | not eligible |

## Why the Case READMEs Are Insufficient

The case directories describe desired evaluation subjects but do not include
frozen filings, news, macro data, OHLCV, independent close checks, portfolio
state, valuation inputs, or prior v1 normalized outputs. Using newly downloaded
or remembered facts would introduce look-ahead and input drift.

## What Is Required for a Future A/B

1. Freeze one evidence bundle per ticker and cutoff.
2. Record source, publication time, effective time, retrieval time, and cutoff
   for every item.
3. Calculate deterministic market fields once and share the exact result with
   both versions.
4. Preserve normalized v1 and v2 outputs without post-hoc editing.
5. Evaluate outcomes later without modifying either original decision.

Until those conditions are met, the correct result remains `UNAVAILABLE`.
