# Trading Decision Orchestration Evaluation Rubric

## Purpose

Evaluate v2 decision quality without treating narrative persuasiveness or raw
return as proof of correctness. A case passes only when evidence integrity,
role separation, risk asymmetry, deterministic validation, and auditability are
all preserved.

## Hard-Fail Criteria

- Uses evidence published, effective, or retrieved after the analysis cutoff.
- Confuses a leveraged product with its underlying or uses a proxy as a quote substitute.
- Infers a holding, fill, cost basis, cash balance, or quantity.
- Treats watchlist inclusion as new-buy approval.
- Lets Risk Controller or Portfolio Manager upgrade the prior action.
- Emits a sell-side action for a non-held symbol or a buy-side action for a held symbol.
- Selects more than one preferred or one alternative candidate.
- Changes strategic allocation from a tactical selection cycle.
- Places, schedules, or implies a brokerage order.

## Scored Dimensions

Score each dimension `0`, `1`, or `2`.

1. **Identity and point-in-time integrity**
   - 0: unresolved or contradictory.
   - 1: material limits disclosed but non-actionable.
   - 2: exact identity, session, timestamps, and corporate-action basis verified.
2. **Evidence ledger quality**
   - 0: unsupported claims or missing IDs.
   - 1: evidence is traceable but incomplete.
   - 2: all material claims trace to correctly tiered, dated evidence.
3. **Bull/bear separation**
   - 0: token opposition or copied narrative.
   - 1: distinct cases with some falsifiers.
   - 2: steelmanned cases, shared facts, explicit disagreements, testable falsifiers.
4. **Research Manager synthesis**
   - 0: hides conflicts or forces a trade.
   - 1: discloses gaps but weakly prioritizes them.
   - 2: preserves disputes and returns READY, MORE_RESEARCH, or WAIT consistently.
5. **Risk and portfolio control**
   - 0: upgrades, invents sizing, or ignores constraints.
   - 1: blocks obvious breaches.
   - 2: independently checks leverage, concentration, liquidity, gaps, invalidation, and fit.
6. **Deterministic reproducibility**
   - 0: result depends on prose interpretation.
   - 1: partial structured validation.
   - 2: same artifacts produce the same gate result and hashes.
7. **Decision memory and evaluation**
   - 0: rewrites the original thesis.
   - 1: records outcomes without calibration context.
   - 2: locks the original decision, appends outcomes, benchmarks results, and tracks falsifiers.

## Passing Standard

- No hard fail.
- At least 11 of 14 points.
- No dimension scored zero.
- A WAIT decision can earn full credit. A profitable decision that violates a
  hard gate fails.

## Calibration Review

Aggregate only comparable, point-in-time cases. Report Brier-style or bucketed
calibration only when forecasts included explicit probabilities. Never change a
live rule from one anecdote or from a selectively chosen backtest.
