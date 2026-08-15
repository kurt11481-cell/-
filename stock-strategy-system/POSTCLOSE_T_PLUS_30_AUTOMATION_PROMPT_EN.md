# REGULAR_CLOSE_T_PLUS_30

Use `$manage-us-stock-strategy` from committed `main` in
`E:\사업\##금동한\코덱스저장소`.

Before any operational recording or delivery, load and validate the immutable
deployment provenance artifact for the configured clean scheduled-runtime
worktree. Its runtime HEAD, task-config hashes, policy hashes, provider-scope
hash, semantic cohort, and clean-worktree state must match the files actually
used. If it is missing or mismatched, return
`DEPLOYMENT_PROVENANCE_NOT_VERIFIED`; delivery and all session counters remain
disabled.

Execute code only from `E:\사업\##금동한\runtime\stock-strategy-scheduled`.
Read the canonical portfolio state only from
`E:\사업\##금동한\코덱스저장소\stock-strategy-system\portfolio_state.json`;
do not copy results back, write it, or substitute a worktree-local state file.
The deployment manifest is
`E:\사업\##금동한\runtime\stock-strategy-scheduled\workspace\outputs\activation\deployment-provenance\current.json`.

Run one read-only `REGULAR_CLOSE_T_PLUS_30` phase for the official U.S. trading
date. Verify the official exchange calendar. On a normal session the scheduled
time is 16:30 America/New_York. On an early-close session a later 16:30 check is
allowed only when it is at least 30 minutes after the official close and uses
the correct trading date.

Query the Kiwoom completed daily bar. On a normal session, if it is not yet a
stable finalized `REGULAR_COMPLETED` `CLOSE`, retry internally at T+40, T+50,
and T+60 under the same `scheduled_run_id`. Retries are not new scheduled runs
or sessions. At T+60 return `FINALIZATION_PENDING` and add zero sessions. Never
substitute a current, premarket, after-hours, day-market, or overnight price for
the completed close. Deliver at most once.

After finalization, enforce this exact order:

`KIWOOM_COMPLETED_BAR_FINALIZED -> POST_CLOSE_EVENT_REFRESH ->
EVENT_CUTOFF_VALIDATION -> EVENT_BUNDLE_HASH -> HOLDING_STRATEGY_COMPILE ->
PORTFOLIO_REALLOCATION_SHADOW`.

Require `event_cutoff >= market_data_cutoff`, reject evidence later than
`decision_as_of`, and preserve decision, market-data, event, broker, and
candidate cutoffs in every decision artifact. Every verified positive holding
must evaluate `ADD_CASE`, `HOLD_CASE`, `TRIM_CASE`, and `EXIT_CASE`; a
non-breached maximum-loss rule is not by itself a HOLD decision.

Run the deterministic Shadow engine with the current versioned
`workspace/policies/portfolio_reallocation_shadow_policy.json` and validate its
context and report schemas. Expected sale proceeds and hypothetical sale
quantities remain `SHADOW_ONLY`; they never become verified broker cash,
execution quantity, or an order. Recompile the full eligible opportunity set
and compare existing-holding adds, new-buy reviews, and `KEEP_CASH`. Preserve
the separate portfolio-decision cohort without changing scheduler/provider
operational counters or backfilling observations.

Keep the ten readiness axes independent. Kiwoom is canonical price authority
when self-integrity passes; yfinance and Web are diagnostic only. MVLL
DAILY_VOLUME/RVOL20 uses its exact accepted Kiwoom scope. Never infer a fill or
cash, create execution quantity, mutate portfolio facts, or place/schedule an
order. Execution quantity is null, quantity authority is none, and order
authority is false. Verify protected hashes before and after.
