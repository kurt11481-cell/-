# SOXL 5-year walk-forward result status

## Conclusion first

**Fail closed: no five-year performance result was produced.** The frozen
protocol requires audited SOXL/SOXX history from at least 2018-08-01 and an
unshortened ten-fold OOS interval from 2021-08-05 through 2026-08-04. The local
workspace has only the shorter cache. Sandboxed source retrieval failed with
`WinError 10061`; the scoped escalated run was rejected before execution because
the current Codex usage limit had been reached. The one-year result was not
misrepresented as five years.

Therefore **quantity-bearing re-entry, every peak/time-stop variant, the
dynamic factor-exposure cap, and all SMA/MACD/RVOL/Stochastic/Chaikin filters
have `activation_eligible=false`**. No acceptance criterion can pass without
OOS metrics, ten fold results, regime results, 20/50-bp stress, adjacent
parameter stability, and at least 20 independent observations.

## Completed safeguards and code audit

- Protocol-locked runner saved as `walk_forward_soxl_policy_2026-08-05.py`.
- Python syntax compilation: passed.
- Offline self-test: passed for ten fold dates, split quantity/cost adjustment,
  and halt/stale-open pending-action freeze.
- The existing-policy replay was corrected to exclude unintended strength
  reclaim/extension sells and to honor the take-profit restriction on only the
  first two common slots.
- Dynamic-factor research now accrues point-in-time DGS3MO cash yield when
  available; the intended full run also produces a zero-yield sensitivity.
- Gap-through-stop logic uses the first valid next open, never the stop price.
  Missing/zero/non-finite tradable opens freeze the pending simulated action.
- The independent audit separately reached the same fail-closed conclusion.

## What remains unvalidated

The following are explicitly **not activated**:

- re-entry restoration at 25%, 50%, 75%, or 100%;
- peak-to-close review at 20%, 25%, 30%, or 35%;
- future-lot time stop at 10, 20, or 30 sessions;
- the 0.75x/1.50x/2.25x/3.00x SOXL factor-exposure mapping;
- SMA20, SMA50, SMA60, SMA200, MACD(12,26,9), RVOL20,
  Stochastic(20,3,3), and Chaikin(3,10) entry/re-entry filters.

Safety-only restrictions that reduce action authority remain separable from a
return-seeking activation decision: `weakness_10ema` watch-only, distinct EMA
rearm, gap/halt fail-closed handling, and source/formula/session validation.
Those controls do not assert that an unrun backtest improved returns.

No brokerage order was placed or scheduled, and no fill was inferred.
