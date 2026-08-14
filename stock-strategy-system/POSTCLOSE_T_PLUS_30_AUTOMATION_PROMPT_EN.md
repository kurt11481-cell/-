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
`E:\사업\##금동한\runtime\stock-strategy-scheduled\deployment-provenance.json`.

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

After finalization, calculate indicators locally, refresh the post-close event
checkpoint, compile deterministically, and apply delivery/counting gates. Keep
the six readiness axes independent. Kiwoom is canonical price authority when
self-integrity passes; yfinance and Web are diagnostic only. MVLL DAILY_VOLUME/RVOL20
uses its exact accepted Kiwoom scope. Never infer a fill or cash, create
quantity, mutate portfolio facts, or place/schedule an order. Quantity is null,
quantity authority is none, and order authority is false. Verify protected
hashes before and after.
