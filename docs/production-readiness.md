# v2 Production Readiness

## Conclusion First

**READINESS: READY_FOR_SHADOW_USE**

The v2 framework is suitable for read-only research and deterministic shadow
monitoring. It is not yet approved for human-assisted live buy/reduction review
because three operational contracts are inconsistent and full JSON Schema
runtime validation is not available. Automated brokerage execution remains
outside scope in every readiness state.

## Readiness Assessment

| Area | Status | Evidence |
|---|---|---|
| A. Architecture | PASS | Role chain, ordered gates, and valid `WAIT` outcome are documented. |
| B. Data integrity | PASS for current shadow | Official completed session, raw close, independent close check, and hashed snapshot. |
| C. Technical validation | PASS | 44-test suite includes fail-closed calendar, close, indicator, gap/halt, and proxy checks. |
| D. Research validation | PARTIAL | Structured role outputs exist; complete schema-engine validation and current Lane C packets do not. |
| E. Policy/state separation | PASS | Research registry has no order authority; operational state was not migrated or mutated. |
| F. Tactical candidate engine | PASS for screening | 13 exact names, three lanes, Stage 1 before Stage 2, no forced ranking or trade. |
| G. A/B or regression evidence | PARTIAL | v1 code snapshot exists; true A/B unavailable; v2 regression passes. |
| H. Live shadow run | PASS | 2026-08-10 session returned grade E and `WAIT / NO TRADE`. |
| I. Git integrity | PASS | Existing history preserved; validation is isolated on `feature/v2-final-validation`. |
| J. Remaining risks | BLOCKING FOR LIVE REVIEW | Operational validator reference, stale cash prose, template enum, schema-engine gap. |

## Critical Safety Checks

- No order placement or scheduling path was added.
- No fill, holding, cash, cost basis, or quantity was inferred.
- Watchlist approval remains different from new-buy approval.
- No tactical name enters strategic allocation automatically.
- No short-selling approval exists.
- Risk Controller cannot upgrade a proposal.
- The direct leveraged-product close cannot be replaced with an underlying
  proxy close.
- Research packets remain untrusted until the deterministic evaluator
  reconstructs the applicable state and market facts.

## Blocking Issues Before `READY_FOR_HUMAN_REVIEW_USE`

1. Replace or implement the active `validate_research_cycle.py` contract through
   one reviewed migration and add integration tests from automation prompt to
   canonical validator.
2. Remove hard-coded cash prose from the automation prompt and require all cash
   language to be rendered from verified state.
3. Align template Research Manager enums with the canonical decision contract.
4. Run schemas through an independent Draft 2020-12 validator and prove the
   standard-library gate is not weaker.
5. Re-run the complete regression suite and one fresh completed-session shadow
   run after those corrections.

## Evidence Limitation

No true point-in-time v1-v2 A/B case was eligible. Readiness therefore relies on
static authority review, deterministic regression, and current shadow behavior.
That is sufficient for shadow use only.

## Explicit Exclusion

There is no `READY_FOR_AUTOMATED_TRADING` state. Every trade remains an external
human decision and manual broker action.
