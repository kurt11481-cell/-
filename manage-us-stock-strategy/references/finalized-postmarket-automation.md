# Finalized Post-Market Automation

## Operating mode

Use `SINGLE_FINALIZED_RUN`. The one `Morning Portfolio Strategy` Codex task runs
Tuesday through Saturday at 10:15 Asia/Seoul, after the U.S. extended-hours
session plus a conservative safety buffer. Do not retain the former 07:45 KST
run as an operational-counting run.

The completed-session analysis components retain `POST_MARKET`. The delivery
and Shadow-counting envelope is exactly `POST_MARKET_FINALIZED`.
`POST_MARKET_PRELIMINARY`, generic `POST_MARKET`, `FINALIZATION_PENDING`, manual,
test, replay, pre-open, stale, catch-up, dirty-worktree, undelivered, and
portfolio-hash-mismatched attempts are observable but excluded.

## Finalization authority

Before delivery and counting, verify one official completed U.S. session and
require every critical direct daily record to be:

- the same canonical ticker and session;
- `REGULAR_COMPLETED`;
- `RAW_REGULAR_SESSION_CLOSE` for both price basis and quote type;
- USD, stable, and `bar_finalized=true`.

Store premarket, after-hours, day-market, and overnight observations separately.
They may add caution or downgrade readiness but cannot overwrite a completed
bar, enter daily indicators, create hard-risk breach authority, upgrade WATCH,
create quantity, or place an order.

## Provider and event scope

Apply the active session-aware Kiwoom provider-scope manifest. Preserve FSLY's
complete yfinance technical-history fallback without merging histories or
lowering the minimum. Preserve MVLL's `EMA10_RECLAIM_RVOL20` block as a
decision-class-local limitation while retaining Kiwoom Raw price authority.

Provider readiness and event readiness are separate. Missing event data may
produce `EVENT_REVIEW_PENDING`; it does not invalidate provider infrastructure.

## Delivery and cohort

Configuration is `FIRST_RUN_PENDING`, never `DELIVERY_VERIFIED`. Only an actual
delivered scheduled finalized run from clean committed `main`, with matching
deployment/registry evidence and identical portfolio hashes, may count. Record
the delivery ID before appending the attempt. Update the new zero-based semantic
cohort atomically. Never backfill preliminary, manual, replay, or dry-run work.

Use a phase-neutral urgent-state fingerprint to suppress an unchanged state
across phases, while retaining phase in audit and delivery identifiers.

This workflow grants no order, fill, quantity, policy, or portfolio authority.
