# Finalized Post-Market Full Portfolio Strategy

Use `$manage-us-stock-strategy` from
`E:\사업\##금동한\코덱스저장소` on committed `main` only.

Run the read-only `POST_MARKET_FINALIZED` operational phase at the configured
Tuesday-Saturday 10:15 Asia/Seoul schedule. The underlying completed-session
analysis phase remains `POST_MARKET`; only the validated finalized envelope may
be delivered or counted. Read the canonical portfolio state, alert
policy/runtime, instrument registry, tactical universe/policy, event policy,
source-capability registry, and monitoring runtimes before analysis.

Before market-data work, run the installed-Skill deployment validator against
`alert_policy.json`, the committed canonical `manage-us-stock-strategy/`, and
the installed Codex Skill directory. A hash/status mismatch is a global
`DATA_INCOMPLETE` failure: stop before market collection and do not update
runtime delivery state as successful.

Apply `workspace/policies/kiwoom-session-aware-priority-policy.json` before
market collection. Kiwoom is the guarded operational priority only for its
accepted scope: broker-observable session quotes, finalized Raw regular daily
closes, and validated Adjusted completed-daily technical history. A same-ET-date
Kiwoom daily row without a deterministic finalization field is
`FINALIZATION_PENDING`, not a completed close. Keep yfinance as the independent
diagnostic Shadow and approved ticker-local fallback. Compare providers only
after ticker, identity, session type, reported session, quote type, price basis,
currency, timestamp, stability, and finalization all pass. Non-comparable
extended-session differences are not conflicts. Use Codex Web only for an
unresolved comparable finalized regular-close conflict. Never average values.

Also load `workspace/policies/finalized_postmarket_automation_policy.json`.
Before delivery, build and validate `finalization_evidence` against
`manage-us-stock-strategy/schemas/finalized-postmarket-evidence.schema.json`.
Every critical direct daily record must be the same official completed session,
`REGULAR_COMPLETED`, `RAW_REGULAR_SESSION_CLOSE`, stable, USD, and
`bar_finalized=true`. Extended-session records must remain separate. A
`POST_MARKET_PRELIMINARY`, legacy generic `POST_MARKET`,
`FINALIZATION_PENDING`, manual, replay, pre-open, dirty-worktree, stale,
undelivered, or portfolio-hash-mismatched attempt is observed but never counted
and can never create `DELIVERY_VERIFIED`.

Reuse one canonical completed-session market snapshot and one event snapshot.
Do not
require Massive credentials or Massive MCP for startup. Do not register
Codex Web as a structured market-data provider.

Build research and new-buy strategy drafts before independent-close
acquisition. Preserve `READY` and `NEAR_TRIGGER` opportunity quality when
independent evidence is unavailable; keep execution at
`VERIFICATION_PENDING`. Build the deterministic selective price-evidence queue.
An empty queue is `NOT_REQUIRED` and performs no Web acquisition. For a
non-empty queue, select only an exact route from
`workspace/policies/web_completed_close_route_registry.json`, open the original
source page (never a search snippet or Yahoo-origin page), write untrusted Web
evidence, then run deterministic evidence and numerical validators. A route or
evidence failure is ticker-local unless the common market/session authority
failed. Never substitute a second Yahoo endpoint as an independent close and
never turn unavailable Web evidence alone into `NO_TRADE`.

Produce every verified holding's separate Risk State and Strategy State, the
seven-symbol Tactical Radar (`MVLL`, `SOXL`, `NBIS`, `BE`, `TOST`, `NOW`,
`FSLY`), strict Cash Status, capital-redeployment review, immutable post-market
baseline, and validated POST_MARKET run manifest. Preserve opportunity quality
when cash or execution approval is blocked.

Apply 1/5/10/20/60 promotion only through exact ticker, decision-class, and
source-route scope. Historical route acceptance does not count as an
operational Shadow session. No stage auto-promotes, and every human-review
entitlement requires an explicit user approval reference. Web `MATCH` changes
only price evidence; it never approves an instrument, risk budget, maximum-loss
rule, quantity, or order.

Only fresh fully verified available broker cash is purchasing power. Zero cash
means `NO_FUNDED_ACTION`, not `KEEP_CASH`. Projected or unsettled proceeds are
never cash. Held Radar names are `EXISTING_HOLDING_ADD`, never duplicate
`NEW_POSITION` entries.

Routine execution may update only runtime/dedup and output artifacts. It must
not mutate portfolio state, holdings, cash, average cost, fills, policy, source
code, or registry. Never create quantity or an order. Hash portfolio state
before and after and require equality.

Write outputs below `workspace/outputs/portfolio-strategy/<SESSION>/`. Update
automation delivery runtime only after schema validation and portfolio hash
verification. Return the conclusion first in Korean and state the commit,
policy version, provider status, subsystem statuses, and that no brokerage
order was placed or scheduled.

After actual delivery, record the phase-specific delivery ID and the scheduled
attempt, then update the active cohort atomically. Configuration or manual smoke
does not count. Apply phase-neutral urgent-state deduplication so an unchanged
state is never delivered twice across preliminary and finalized observations.
Keep provider readiness and event readiness separate: `EVENT_DATA_INCOMPLETE`
maps to `EVENT_REVIEW_PENDING` where required and does not invalidate the
session-aware Kiwoom provider scope.

Extended-session Kiwoom observations must remain separate from completed daily
bars. They may add caution or downgrade readiness, but may not confirm daily
EMA/ATR/RSI/MACD/RVOL, create a completed-session hard-risk breach, upgrade
WATCH to READY, create quantity, or change portfolio facts.
