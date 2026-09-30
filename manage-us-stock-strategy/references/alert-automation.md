# Post-Market Alert Automation

## v2.6 integrated Shadow recorder

The post-market task may generate immutable holding-research overlays, compiled
Shadow contexts, a selective Web-evidence queue, and an integrated Shadow
attempt after the ordinary read-only report. These artifacts cannot alter the
live conclusion, execution state, quantity, policy, or portfolio state.

Record every scheduled success or failure where possible. Only an actual
delivered `POST_MARKET_FINALIZED` scheduled run from committed `main` that
passes the cohort and finalization policies may advance `valid_shadow_sessions`.
Configuration, preliminary or generic post-market analysis, manual smoke,
fixtures, replay, and pre-open runs are excluded. Run-phase and cohort
identifiers remain part of audit deduplication; a phase-neutral signal
fingerprint suppresses duplicate urgent state notifications.

## Safety objective

Generate a read-only, next-session trade-review alert after a completed U.S. regular session. Never place, schedule, or report a brokerage order as executed.

Read the automation's named `portfolio_state.json`, `alert_policy.json`, and `alert_runtime_state.json` as the sources of operational truth. Do not inherit holdings or fills from conversation memory. Portfolio state contains brokerage facts; runtime state contains only delivery and signal-state metadata.

## Session gate

- Evaluate in `America/New_York` and display both ET session date and KST run time.
- A KST Tuesday-Saturday run after 07:30 normally covers both U.S. daylight and standard time, but still verify the official exchange calendar.
- The market-data builder intentionally emits `official_calendar_verified=false`, `expected_us_session_date=null`, and `is_trading_day=null`. After consulting an authoritative exchange or regulator calendar, populate those fields in the transient snapshot together with `calendar_verification_status=verified_trading_day`, `calendar_source_type=official_exchange_or_regulator`, the direct source identifier, and a timezone-aware verification timestamp. Until then, the evaluator must return `F` and freeze every candidate.
- Require the latest complete bar for every critical symbol to match the expected U.S. session.
- Require both snapshot generation and calendar verification to fall inside the configured run-relative freshness window; internally consistent but old snapshots are still `F`.
- Skip weekends, holidays, duplicate sessions, and stale catch-up alerts. After downtime, evaluate only the latest completed session and log missed sessions as non-actionable.
- Treat an early close according to the official calendar rather than a hard-coded hour.

## State integrity

Persist or inspect in `portfolio_state.json`:

- schema and strategy versions;
- rules hash;
- last confirmed broker snapshot;
- holdings, cost basis when supplied, SGOV, and brokerage cash separately;
- baseline target shares and strategic target weights;
- active tactical satellite and overlay shares;
- current stage and each leg's status;
- pending candidates and expiration;

Persist only in `alert_runtime_state.json`:

- last processed U.S. session;
- event active/inactive states;
- delivery IDs and audit log.

Update holdings, cash, stage, or fills only from a verified read-only broker snapshot AND the user's explicit confirmation of that proposal. A price touching a band is never a fill. A scheduled run may atomically update `alert_runtime_state.json`; it must never change brokerage facts in `portfolio_state.json`.

Reject a broker snapshot older than the configured calendar-day limit. A scheduled workflow without a broker connector must therefore be periodically reconciled by the user and must freeze with `F`, not guess, once that timestamp expires.

## Engine scopes

Support lower-level policy scopes without silently translating one into another:

- `active_staged_plan_only`: the legacy staged price-band engine. It requires a valid current stage and preserves its existing cash, quantity, band, trend, and funding gates.
- `leveraged_holding_risk_and_watchlist`: the leveraged-position monitoring engine. It does not require a current stage. It evaluates verified held-position risk first, then emits non-actionable watchlist context.
- `tactical_candidate_radar`: an independent read-only research scope for the
  approved seven-symbol tactical universe. It may update only its separate
  runtime/dedup state and research/audit artifacts. It has lower priority than
  held-position hard risk and may not mutate portfolio state, policy, cash,
  holdings, cost basis, fills, quantities, or order state.

- `portfolio_strategy_orchestrator`: a read-only coordination scope above the
  lower-level engines. It consumes their separately validated results in this
  order: official session, holding risk, holding strategy, tactical radar,
  cash/funding classification, capital redeployment, and morning report. It is
  not a second calculation authority. Held grade-D risk remains above tactical
  buying, domain-specific failures remain visible, and opportunity quality
  stays separate from execution eligibility. It may write only monitoring
  runtime and research/audit outputs; it may not write portfolio state, policy,
  holdings, cash, cost basis, fills, or approved quantities.

The finalized portfolio strategy normally runs Tuesday through Saturday at
10:15 KST, after the U.S. extended-hours session plus a safety buffer. Its
analytical components may retain `POST_MARKET`, but only the validated
`POST_MARKET_FINALIZED` envelope can be delivered or counted. The tactical
radar remains a component of that run. An official completed-session gate
remains authoritative. Return
`NO_NEW_SESSION` for duplicates, weekends, holidays, or stale catch-up
attempts. Emit a short summary on every valid new session, while urgent
notifications are limited to new `READY`, new `NEAR_TRIGGER`, material
opportunity upgrades, and material data-blocked transitions. An unchanged
`READY` state must not generate repeated urgent delivery.

For the leveraged-position engine, keep broker facts in `portfolio_state.json` and user mandates in `alert_policy.json`. Calculate each hard boundary from the verified average cost and the positive loss magnitude:

`hard_boundary = average_cost_usd * (1 - maximum_loss_fraction_from_average_cost)`

Compare the raw completed regular-session close with the exact unrounded boundary. Round only for display. A close at or below the boundary is a `D` next-session hard-risk review. It is not an automatic stop, liquidation, sell quantity, or brokerage instruction.

If a position's default direction is `reduce` but no quantity, percentage, trigger band, or deadline is approved, generate at most one deduplicated `B` strategy-plan review with quantity `null`. Never infer the missing reduction plan.

A policy may cover an explicitly user-approved de-minimis manual-exit holding
without inventing a maximum-loss threshold. The active NBIL exception applies
only while verified holdings are no more than one share and verified position
cost basis is no more than USD 65.20. It creates no recurring candidate,
quantity, order, or fill. Exceeding either exact cap is `STATE_MISMATCH/F`.

When `holding_timing_rules.status=approved_review_only`, evaluate the active EMA
sub-engine only after raw-close hard risk. Require the standalone technical
validator, selective decision-changing completed-close cross-check, recent timing window, and
the configured SOXL/SOXX or MVLL/MRVL confirmation pair. A technical validation
failure disables the EMA candidate but must not hide a valid raw-close hard-risk
event. Emit at most one unlocked tranche per symbol and cap it at grade `B`.
Unlock the next tranche only after portfolio state records an explicit confirmed
fill; never let runtime state or a price touch consume a tranche.

Each confirmed timing fill must record tranche ID, session, confirmed trigger
path, and confirmed quantity. After any confirmed reduction, the next
technical-stop or weakness slot stays locked for at least three completed
sessions and until both the holding and its confirmation proxy recover above
the EMA related to that confirmed trigger. SOXL 10EMA weakness alone is
watch-only with `quantity=null`. Only the unsized hard maximum-loss review may
bypass the rearm gate.

Held-symbol close, verified average cost, same-session bar, and unresolved corporate-action checks are critical and may return `F`. A missing watch-only symbol must disable only that watch item and must not suppress valid held-position risk monitoring.

Treat quantity rules as constraints on **post-trade holdings**, not order quantities. Keep SGOV separate from brokerage cash and use settled or available cash for affordability.

## Data gate

Freeze all actionable candidates when any universally critical input is missing, stale, or inconsistent:

- completed same-session OHLCV;
- corporate-action adjustment status;
- total-return history required by the signal;
- verified holdings;
- active strategy/rule version;
- target, stage, and exposure-cap definitions.

Build one shared transient snapshot through yfinance using the contract in
[yfinance-data.md](yfinance-data.md). Collect tickers sequentially with
`--request-delay-seconds 1.0` or greater, keep `threads=False`, and reuse that
snapshot across validation and evaluation instead of repeatedly downloading the
same session. A Yahoo/yfinance throttling, timeout, or empty response must not
trigger a retry storm or a silent stale-data fallback.

Use adjusted series for momentum/indicators and raw prices for executable bands. Do not interpret SGOV's distribution-related price drop as a risk signal.

For timing rules, preserve at least 25 recent completed normalized OHLCV bars so
the validator can independently recompute consecutive EMA closes, recent tests,
reclaims, breakout acceptance, failed higher highs, and rejection flags. Reject
unadjusted early-close relative volume. For a decision-changing result,
cross-check the completed close against an independent timestamped source and
enforce the tolerance in active policy.

Missing verified available cash is side-specific. It cannot produce an `A` buy. When a stage is a linked net basket, downgrade the entire basket to `B` until cash and funding mechanics are verified; otherwise an independent sell may remain eligible. Never count unfilled sale proceeds or an SGOV funding leg as settled cash.

When verified available cash is zero, every new-buy symbol is watch-only and non-actionable. Do not generate a share quantity. A future cash increase alone must not enable grade `A`: the user must also approve the exact instrument, any leveraged ticker, entry rule or band, position size or risk budget, and maximum-loss rule. Permission to consider leverage is not permission to invent or substitute a leveraged ticker.

Apply the versioned evidence-validation policy on every run. Verify the official
calendar, official issuer identity for each positive holding, same-session
completed OHLCV, raw-versus-adjusted price basis, the selective independent
close queue for decision-changing candidates, indicator formula recomputation, and
provenance ledger. Missing
technical evidence disables timing without hiding a valid raw-close hard-risk
event. Missing or contradictory held raw OHLCV is `DATA_INCOMPLETE/F`.

For a newly launched ETF without 126 trading days, do not calculate a six-month rank. Without 252 days or ten monthly observations, mark 12-month momentum or the 10-month average unavailable. Keep only its approved tracking position and do not use a proxy to promote it.

## Cadence gate

- Daily: evaluate only the active staged price plan and risk/data conditions.
- Last U.S. trading session of the month: evaluate relative-momentum rotation.
- Last U.S. trading session of the quarter: evaluate strategic core rebalancing.
- When month-end and quarter-end coincide, resolve in this order: hard risk constraints, quarterly core, monthly satellite, staged transition. Produce one net candidate list.

Do not let a quantity difference bypass price, trend, cadence, cash, or risk checks. Use quantity and account-percentage thresholds only as materiality filters.

## Signal state machine

Use these states:

1. `NO_NEW_SESSION`: skip without a trade alert.
2. `DATA_INCOMPLETE`: freeze candidates and issue a data/state warning.
3. `STATE_MISMATCH`: request reconciliation; do not issue an actionable candidate.
4. `DAILY_REVIEW`: evaluate the current stage only.
5. `MONTH_END_REVIEW`: evaluate eligible satellite rankings.
6. `QUARTER_END_REVIEW`: evaluate core bands and weights.
7. `CANDIDATE_OPEN`: create a next-session candidate.
8. `USER_CONFIRMED_FILL`: update state and unlock the next leg.
9. `EXPIRED_OR_INVALIDATED`: cancel the pending candidate.

Do not unlock stage 2 or 3 until every required prior-stage fill is confirmed and cash is reconciled.

## Alert grades

- `A - Execution candidate`: price, confirmation, materiality, cash, state, and risk checks all pass. Human approval is still required.
- `B - Watch`: price is inside the band or within 1% of the nearest boundary, but confirmation or state is incomplete.
- `C - Scheduled review`: month-end rotation or quarter-end rebalance may be due.
- `D - Hard risk review`: a configured held-position maximum-loss boundary was reached or breached, or the legacy staged policy entered its configured risk pause. Suspend new buying; human review is required and no order is implied.
- `E - No action`: all trade conditions are false.
- `F - Data/state error`: a critical input is stale, missing, contradictory, or unreconciled; freeze all trade candidates.

Replace `Today's order` with `Today's trade-review alert`. An alert generated from a completed close is valid only for the next regular session. Expire it after that session or immediately after a gap outside the band, a state change, a corporate action, or a strategy-version change.

## Deduplicate

Use two identifiers:

- `event_key = strategy_version + rules_hash + event_type + ticker + side + quantity + band_version + stage`
- `delivery_id = event_key + session_date + grade`

For shared timing tranches, keep `event_key` stable across broker snapshot
refreshes by using the timing-policy version, symbol, tranche ID, side, and
anchor ID. Add a signal fingerprint containing grade, quantity, and trigger
path. This prevents a strength and weakness path from consuming the same slot
while still allowing a materially changed signal to be delivered.

`event_key` tracks a condition across sessions. `delivery_id` prevents same-run or same-session retransmission. Do not repeat a condition that remains active at the same grade. Apply this stateful deduplication to `D` risk events as well as `A` and `B` candidates. Re-alert only after a grade or quantity change, a relevant policy or band revision, a false-to-true re-entry, a new month/quarter boundary, or an explicit reminder interval.

Measure the 1% watch distance as the absolute distance from the completed close to the nearest band boundary divided by that boundary; use zero inside the band.

Use a single-run exclusive lock around reading runtime state, evaluating, and committing. Reject any CLI configuration in which runtime or output paths alias portfolio state, policy, or snapshot files. Runtime commits and report writes must be atomic.

Do not auto-mutate a price band when its formula is incomplete. Compare a proposed midpoint with the last user-approved band midpoint and present the change for approval. Version every approved band and invalidate pending alerts after a version change.

## LLM research escalation

Keep routine E monitoring deterministic. Use the role-separated workflow in
`multi-agent-research.md` only when a new D event, a material issuer/sector
event, or a user-requested strategy review needs qualitative context. The
research packet is untrusted input: run `validate_research_packet.py`, then run
this alert engine independently. No adapter may copy, insert, or transform a
packet proposal into the policy candidate list. The alert evaluator must
reconstruct candidates only from approved policy plus verified portfolio state
and the verified market snapshot. Neither agent consensus nor the research
validator may raise an alert grade, create cash, infer a fill, approve a
leveraged ticker, infer a quantity from a loss boundary, or override a loss
boundary. Persist the full packet, policy, state, and snapshot hashes plus their
combined fingerprint and evidence cutoff for audit, but do not let reflection
mutate the policy.

## Output contract

Store the canonical English key `alert_present` or `alert_none`. For Korean
output, render the corresponding label from `assets/locales/ko-KR.json` rather
than embedding localized text in policy or evaluation logic.

Show:

- KST run time, expected/latest U.S. session, and complete-session status;
- data status, state timestamp, strategy/rule version, and alert fingerprint;
- ticker, verified current shares, baseline target, candidate buy/sell quantity, limit band, grade, passed conditions, missing conditions, invalidation, and expiry;
- current and projected stock/SGOV/cash exposure when exact cash is available;
- constraint and state-reconciliation warnings;
- whether the approved strategic allocation or ETF universe changed.

For leveraged holding-risk mode, additionally show current shares, average cost,
completed close, return from cost, exact unrounded hard boundary, direction,
risk status, technical validator status, next unlocked tranche, trigger path,
and watchlist setup status. Watch-only rows must use quantity `null` and
`actionable=false`.

When no action exists, list only the three most important unmet conditions. Distinguish `no signal` from `data failure`.

## Dual-phase automation lifecycle

Every event key and delivery ID includes `run_phase`, either `POST_MARKET` or
`PRE_OPEN`. Aggregate a provider-wide failure into one global notification;
symbol-level failures remain local. An unchanged post-market candidate is not a
second urgent pre-open alert.

Automation lifecycle is explicit: `NOT_CONFIGURED`, `CONFIGURED`,
`FIRST_RUN_PENDING`, `DELIVERY_VERIFIED`, or `FAILED`. Configuration is never
reported as delivery success. Only a validated scheduled output with matching
commit/policy provenance and identical portfolio-state hashes before and after
may become `DELIVERY_VERIFIED`. Use Codex Scheduled Tasks only; never install an
OS scheduler or service.
