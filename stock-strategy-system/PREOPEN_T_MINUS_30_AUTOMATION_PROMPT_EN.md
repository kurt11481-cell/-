# PRE_OPEN_T_MINUS_30

Use `$manage-us-stock-strategy` from committed `main` in
`E:\사업\##금동한\코덱스저장소`.

Before any operational recording, load and validate the immutable deployment
provenance artifact for the configured clean scheduled-runtime worktree. Its
runtime HEAD, task-config hashes, policy hashes, provider-scope hash, semantic
cohort, and clean-worktree state must match the files actually used. If it is
missing or mismatched, return `DEPLOYMENT_PROVENANCE_NOT_VERIFIED` and do not
record a Pre-Open success.

Execute code only from `E:\사업\##금동한\runtime\stock-strategy-scheduled`.
Read the canonical portfolio state only from
`E:\사업\##금동한\코덱스저장소\stock-strategy-system\portfolio_state.json`;
do not copy results back, write it, or substitute a worktree-local state file.
The deployment manifest is
`E:\사업\##금동한\runtime\stock-strategy-scheduled\deployment-provenance.json`.

Run one read-only `PRE_OPEN_T_MINUS_30` phase for the upcoming official U.S.
regular session. Verify the official exchange calendar and upcoming session
before doing work; return `MARKET_HOLIDAY` or `OFFICIAL_SESSION_UNVERIFIED`
without substituting a date.

Load the most recent immutable post-close baseline. Refresh only Kiwoom
executable/current price and market phase, current event evidence, the Kiwoom
read-only broker Shadow snapshot, hard-risk context, and portfolio fit. Preserve
or lower readiness. Never create or finalize a daily close, increment a
finalized-session count, upgrade WATCH to READY, create ADD, infer a fill,
create quantity, mutate the portfolio, or place/schedule an order.

Keep the six readiness axes independent. Kiwoom is canonical price authority
when self-integrity passes; yfinance and Web are diagnostic only. MVLL DAILY_VOLUME/RVOL20
uses its exact accepted Kiwoom scope. Quantity is null, quantity authority is
none, and order authority is false. Verify protected hashes before and after.
