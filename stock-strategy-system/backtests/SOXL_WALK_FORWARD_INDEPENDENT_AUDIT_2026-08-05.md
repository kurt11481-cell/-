# SOXL five-year walk-forward independent audit

## Conclusion first

**Status: fail closed; no five-year performance result was produced and no
return-seeking policy change is eligible from this audit.**

The pre-registered protocol requires primary/raw, independently cross-checked
SOXL and SOXX history from at least 2018-08-01 and an unshortened stitched OOS
interval from 2021-08-05 through 2026-08-04. The audited local cache begins on
2024-06-03; only 2025-08-05 through 2026-08-04 was used by the separate
one-year study. Direct market-data
retrieval through the bundled Python runtime was blocked by the sandbox, and
the required network escalation was rejected because the current account usage
limit had been reached.  Reusing the one-year cache as if it were five years
would violate the frozen protocol.

## Reproducible failure evidence

- Attempted source path: Yahoo chart API plus Nasdaq historical API, following
  the existing one-year backtest's primary/cross-check design.
- Python runtime: `C:/Users/금동한/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
- Sandboxed result: `urllib.error.URLError` caused by Windows connection refusal.
- Escalated retry: rejected by the approval reviewer because the current usage
  limit was reached.
- Local data audit: the earliest audited SOXL/SOXX row is 2024-06-03, which is
  still more than five years short of the required 2018-08-01 input boundary.

The accompanying script validates exact input endpoints, duplicate/null OHLCV,
matching SOXL/SOXX calendars, SHA-256 hashes, and the ten fixed 24-month
training/6-month test fold definitions.  It intentionally stops before
strategy statistics because full audited inputs are absent.

## Required artifacts

- Script: `backtest_soxl_walk_forward_independent_audit_2026-08-05.py`
- Machine result: `soxl_walk_forward_independent_audit_results.json`
- Daily output: `soxl_walk_forward_independent_audit_daily.csv` (header-only;
  no fabricated rows)
- Trade output: `soxl_walk_forward_independent_audit_trades.csv` (header-only;
  no fabricated fills)

## Policy consequence

The protocol itself explicitly says not to shorten the test when full audited
history cannot be obtained.  Therefore re-entry quantities, peak/time exits,
added indicator votes, and a dynamic leverage cap remain research-only on the
basis of this independent audit.  Safety-only restrictions that reduce action
authority may still be considered under the protocol's separate exception.

No brokerage order was placed or scheduled, and no fill was inferred.

## Static audit of the separate full-run implementation

The independently inspected `walk_forward_soxl_policy_2026-08-05.py` is a
substantial implementation, but its current output must not be treated as a
complete protocol pass until these issues are corrected:

1. Its `existing` replay selects from the entire timing-engine priority list,
   including strength triggers, rather than enforcing the original SOXL
   per-slot allowed-trigger lists.  That can create reductions the existing
   policy never authorized.
2. Fold/regime comparisons and acceptance-gate records are generated only for
   the walk-forward-selected indicator.  Rearm, restoration, peak/time, and
   each indicator ablation therefore do not receive the required candidate-
   level pass/fail audit.
3. The 20/50-bp stress loop covers only revised simple, selected indicator, and
   dynamic factor cap.  Adjacent-parameter stability is stored as text rather
   than tested as a Boolean acceptance criterion.
4. Fold-independent reset results cover revised simple, selected indicator,
   and buy-and-hold only; they cannot establish the seven-of-ten-fold rule for
   every requested candidate.
5. The dynamic factor-cap simulation does not accrue the protocol's cash yield,
   while its zero-yield sensitivity is not separately reported.

These are fail-closed audit findings, not permission to change the policy.
