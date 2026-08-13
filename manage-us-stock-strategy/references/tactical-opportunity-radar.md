# Tactical Opportunity Radar

## Purpose

Run a compact morning research monitor without turning watchlist inclusion into
trade permission. The active daily universe is exactly:

- leveraged semiconductor: `MVLL` with `MRVL`, and `SOXL` with `SOXX`;
- AI infrastructure: `NBIS`, `BE`;
- user-defined AI-agent exploration: `TOST`, `NOW`, `FSLY`.

The AI-agent label is an exploratory organizational tag, not a pure-play or
revenue-exposure claim. Historical registry records remain available but are
not active daily candidates.

## Authority model

Use `workspace/policies/instrument_registry.json` as the only canonical
instrument registry. Validate its referenced hash against the active alert
policy. A mismatch is `POLICY_REGISTRY_MISMATCH`: continue research from the
canonical file, display the conflict, and set execution review to
`DATA_BLOCKED`.

Keep two independent state machines:

- opportunity quality: `READY`, `NEAR_TRIGGER`, `WATCH`, `NOT_READY`,
  `DATA_BLOCKED`;
- execution eligibility: `ELIGIBLE_FOR_REVIEW`, `VERIFICATION_PENDING`,
  `WATCH_ONLY`, `NOT_APPROVED`, `CASH_BLOCKED`, `PORTFOLIO_BLOCKED`,
  `DATA_BLOCKED`.

Cash, portfolio permission, or new-buy approval cannot alter the opportunity
quality label. They constrain only execution review. Quantity stays `null`; no
order is placed or scheduled.

The primary yfinance row may establish `PRIMARY_VALIDATED` opportunity quality
after deterministic validation. Only `READY`, deterministic material
`NEAR_TRIGGER`, and approved decision-boundary cases enter the independent
close queue. Missing queued evidence leaves `READY` visible but changes
execution to `VERIFICATION_PENDING`. A true direct conflict blocks that ticker;
an empty queue is `NOT_REQUIRED` and must not generate an outage.

## Required disposition

Return for all seven candidates:

- ticker and lane;
- opportunity and execution state;
- evidence, thesis, valuation, technical, event, risk/liquidity, portfolio-fit,
  and identity statuses;
- new-buy approval;
- primary blocker and remaining conditions;
- next review trigger and evidence cutoff;
- `quantity=null` and `order_authority=false`.

Event data incompleteness remains visible. A known `CONTEXT_ONLY` event does
not downgrade opportunity state; only a validated, applicable
`WAIT_REQUIRED` event policy may do so. Missing event coverage can keep a setup
at `NEAR_TRIGGER`, but the radar may not invent an event window.

## Bounded research

First build the canonical market and event snapshots. Then run the light screen
for all seven. Deep-research only `READY`, `NEAR_TRIGGER`, a material upgrade,
material issuer/news/event/valuation change, or a user-requested case. Use the
role-separated Bull/Bear, Research Manager, Trader, Risk Controller, Portfolio
Manager, and deterministic gate sequence. Normally shortlist three to five,
but record `shortlist_below_target_due_to_gates` when fewer qualify.

`screen_survivors` must pass identity/evidence and have no explicit thesis,
valuation, technical, risk/liquidity, or portfolio veto. `deep_research_completed`
requires a validated research result and immutable packet hash. Do not name a
preferred candidate before its deep research completes. Tie-break completed
candidates by ordered gates, then lower verified leverage and stable universe
order; never average the gates into a score.

Use only existing approved technical conditions for `NEAR_TRIGGER`. Examples
include validated EMA reclaim, breakout acceptance, pullback confirmation,
event clearance, valuation refresh, and evidence refresh. Do not create new
numeric thresholds.

## State and notifications

Write only the separate radar runtime state using an atomic replacement. Track
`NEW_READY`, `NEW_NEAR_TRIGGER`, `OPPORTUNITY_UPGRADE`,
`OPPORTUNITY_DOWNGRADE`, `DATA_BLOCKED`, and `NO_MATERIAL_CHANGE`. Use a stable
event key, session-specific delivery ID, and signal fingerprint.

The routine schedule is Tuesday through Saturday at 07:45 Asia/Seoul, subject
to the official completed U.S. session gate. The caller must supply the newly
verified latest completed session separately from the market snapshot, and the
two must match. Do not catch up old sessions.
Return `NO_NEW_SESSION` for duplicates. A valid new session always gets one
compact grouped summary; unchanged `READY` candidates do not receive a second
urgent notification.

The automation may update radar runtime, audit, research, and decision-journal
artifacts only. It must never modify source policy, the canonical registry,
portfolio state, cash, holdings, cost basis, fills, or broker state.

The CLI reads cash only from the canonical operational portfolio state. Output
and shadow runtime files are restricted to `workspace/outputs`; the only live
runtime input is `workspace/state/tactical_radar_runtime.json`. Report and
runtime schemas validate before any write.
