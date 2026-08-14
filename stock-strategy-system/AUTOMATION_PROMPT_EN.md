# Deterministic Finalized Post-Market Monitoring Prompt

Use `$manage-us-stock-strategy` to run the read-only U.S. post-market holding-risk,
EMA timing, and watchlist workflow. Follow the active JSON policy exactly. Never
place or schedule a brokerage order.

## Sources of operational truth

Resolve operational files relative to the directory containing this prompt,
then read these files before doing anything else:

- `portfolio_state.json`
- `alert_policy.json`
- `alert_runtime_state.json`
- the alert and trade-timing references bundled with the skill

Portfolio state contains broker facts and explicitly confirmed tranche fills.
Runtime state contains only signal/delivery metadata. A scheduled run may update
only runtime state. It must never edit holdings, cash, cost basis, timing anchors,
or completed tranche IDs.

Before any market-data work, enforce `alert_policy.json.deployment_gate`. If
`automatic_timing_monitor_allowed` is not exactly `true`, return grade `F` with
the deployment mismatch and stop. Do not run an older installed evaluator
against a newer policy. Manual read-only arithmetic may still explain the
verified average-cost hard-risk boundaries, but it cannot emit a timing
candidate or mutate runtime state.

## Required workflow

### v2.6.8 finalized operational phase

This scheduled task uses `SINGLE_FINALIZED_RUN` at Tuesday-Saturday 10:15
Asia/Seoul. Load and enforce
`workspace/policies/finalized_postmarket_automation_policy.json`. The delivered
and count-eligible phase is exactly `POST_MARKET_FINALIZED`; the underlying
completed-session analytical components may retain `POST_MARKET`.

Capture the portfolio hash before work. Verify the official latest completed
U.S. regular session, then run Kiwoom OAuth/IP/lock/rate-limit/circuit preflight,
resolve identities, and collect Kiwoom Raw and Adjusted completed-daily history.
Require each critical direct daily record to be the same session,
`REGULAR_COMPLETED`, `RAW_REGULAR_SESSION_CLOSE`, USD, stable, and
`bar_finalized=true`. Calculate indicators locally from validated Kiwoom
Adjusted history, subject to the active ticker scopes. Collect yfinance only as
diagnostic Shadow or the explicit FSLY technical-history fallback. Compare only
same-ticker, same-session, same-quote-type, compatible-basis finalized records;
non-comparable extended-session observations are not price conflicts. Codex Web
is restricted to unresolved comparable finalized regular-close conflicts.

Build holding strategies, Tactical opportunities, unsized new-buy drafts, and
event readiness as separate axes. Preserve FSLY's complete yfinance history
fallback without history mixing or a reduced lookback. Preserve MVLL's
decision-class-local `EMA10_RECLAIM_RVOL20` block while retaining its Kiwoom Raw
close. Map `EVENT_DATA_INCOMPLETE` to `EVENT_REVIEW_PENDING` where policy
requires without invalidating provider readiness.

Render the beginner-facing Korean result, perform actual delivery, record its
delivery ID, capture the portfolio hash after, validate equality, then record
the scheduled attempt and update cohort progress atomically. Only that actual
delivered finalized run from clean committed `main` may count. Preliminary,
legacy generic POST_MARKET, finalization-pending, manual, test, replay, stale,
catch-up, dirty, undelivered, or pre-open attempts are excluded. Configuration
leaves lifecycle at `FIRST_RUN_PENDING`.

### Session-aware Kiwoom operational priority

Load `workspace/policies/kiwoom-session-aware-priority-policy.json` through the
canonical repository. Kiwoom is operationally primary only for the accepted
guarded scope. yfinance remains the diagnostic Shadow and explicit scoped
fallback. A same-ET-date Kiwoom daily row without deterministic finalization is
`FINALIZATION_PENDING`; premarket, after-hours, day-market, overnight, broker
mark, bid, or ask values are not comparable to a completed regular Raw close.
Do not calculate conflict tolerance until session, reported date, quote type,
price basis, timestamp, stability, currency, and finalization gates pass. Only
a persistent comparable finalized regular-close conflict may invoke an exact
Codex Web original-source route.

Extended-session observations cannot overwrite the completed daily bar, enter
daily indicators, confirm hard risk, upgrade WATCH to READY, create quantity,
or affect order authority. FSLY history fallback and the MVLL
`EMA10_RECLAIM_RVOL20` conflict remain ticker/decision-class local. Event-data
incompleteness remains an event/strategy gate, not a market-provider failure.

### v2.6.8 Massive-free staged new-buy and integrated Shadow extension

Run the ordinary v2.5 read-only post-market workflow first. Then, without
changing its live conclusion or any portfolio/policy fact:

1. Load the active immutable NBIS, MVLL/MRVL, and SOXL/sector holding-research
   baselines and validate their local hashes and point-in-time evidence.
2. Build current completed-session overlays from the already validated
   canonical snapshots; never reuse historical baseline technical or portfolio
   fields.
3. Compile Shadow holding contexts deterministically. Preserve live and Shadow
   strategy states separately.
4. Build discovery/onboarding proposals and deterministic unsized new-buy
   strategy drafts before independent price acquisition. Discovery does not
   edit the active universe, watchlist approval, new-buy approval, leverage
   permission, risk budget, maximum-loss rule, cash, or quantity.
5. Build the selective decision-changing completed-close queue. An empty queue
   is `NOT_REQUIRED` and performs no Web acquisition. When non-empty, use Codex
   Web only through an exact route in
   `workspace/policies/web_completed_close_route_registry.json`; open the
   original final page, reject snippets and Yahoo-origin evidence, and keep
   unknown or unaccepted routes `SOURCE_ROUTE_PENDING_REVIEW`.
6. Validate any raw Web evidence and compare only through deterministic code.
   Shadow `MATCH` or `CONFLICT` cannot upgrade live execution, create quantity,
   or mutate state.
7. Keep MVLL product close separate from MRVL and use MRVL only under
   `DAILY_MULTIPLE`; keep SOXL product close separate from SOXX and use SOXX
   `DIRECTION_ONLY`.
8. Evaluate the existing broker-snapshot request and render the beginner Korean
   summary without exposing account identifiers or treating broker display
   prices as market evidence.
9. Capture the portfolio hash before and after all work.
10. Record a v2.6.8 integrated Shadow attempt for both scheduled success and
   scheduled failure where possible, classify it, update the append-only cohort
   progress atomically, and generate a due checkpoint.

Do not require `MASSIVE_API_KEY`, Massive MCP, Massive OAuth, or a structured
independent provider at startup. Codex Web is an acquisition method, not a
provider-capability record. Missing Massive configuration is never a global
failure. Web unavailability preserves `READY`/`NEAR_TRIGGER` research quality,
leaves execution `VERIFICATION_PENDING`, and is ticker-local unless the common
session or primary snapshot failed.

Apply the 1/5/10/20/60 promotion model only to an exact
`ticker + decision_class + source_route_id` scope. Route acceptance replays do
not count as operational Shadow sessions. No stage auto-promotes. A Web MATCH
changes only price evidence and cannot approve the instrument, entry rule,
maximum-loss rule, risk budget, cash, quantity, or order.

Only an actual delivered `Morning Portfolio Strategy` `POST_MARKET_FINALIZED`
scheduled run from committed `main`, with validated finalization evidence, may
count. Configuration, preliminary or legacy generic POST_MARKET, manual smoke,
unit tests, pre-open,
historical backfill, unverified delivery, dirty worktrees, hash mismatch, or a
critical Shadow violation must be logged but excluded. Do not import any prior
v2.5 session into the new cohort. Do not claim delivery verification or advance
the 20-session count merely because this prompt was configured.

If Shadow observability fails, preserve the ordinary read-only report, record
`SHADOW_OBSERVABILITY_FAILURE` where possible, keep promotion blocked, and do
not mutate portfolio or policy. Pre-open remains separately governed and must
not be configured or upgraded by this prompt.

1. Determine the latest completed U.S. regular session in
   `America/New_York`. Verify trading-day status, holidays, and early-close status
   from an official exchange or regulator calendar. Record the direct source,
   expected ET session date, verification time, and KST run time. If this cannot
   be verified, return grade `F` and stop.
2. If runtime state already records that session as processed, return a compact
   no-new-alert result. Do not replay the session after a policy migration.
3. Build one transient snapshot using the session-aware Kiwoom guarded scope
   for every available completed daily bar for:
   `SOXL`, `MVLL`, `NBIL`, `SOXX`, `MRVL`, `NBIS`, `DRAM`, and `BE`.
   Use the installed Kiwoom read-only Adapter and its dynamic identity resolver
   for Primary Raw and Adjusted history. Run requests under the approved pacing,
   bounded retry, single-session lock, and circuit policy. Use yfinance only as
   diagnostic Shadow or an exact ticker-local fallback; keep `threads=False`,
   `prepost=False`, `auto_adjust=False`, and `repair=False`. Compute every
   indicator locally and reuse the canonical snapshots instead of downloading
   the same session again.
   Require at least 252 completed bars whenever the selected formula or
   validator requires a one-year history. For an inception-limited instrument,
   preserve its verified raw close for a separately approved hard-risk review,
   but reject EMA/watch timing that cannot pass the history gate.
   - `SOXX` is the non-leveraged NYSE Semiconductor Index proxy used to confirm
     SOXL direction.
   - `MRVL` is the reference stock used to confirm MVLL direction.
   - `NBIS` is the reference stock for NBIL. NBIL is covered only by the exact
     one-share/USD 65.20 de-minimis manual-exit exception; do not infer a
     maximum-loss or timing rule from NBIS or another ETF.
   - Use raw completed close for average-cost loss boundaries.
   - Use split-adjusted OHLC rescaled to the latest raw close for EMA/ATR rules.
4. The builder deliberately leaves authoritative fields incomplete. Populate in
   the transient snapshot only:
   `official_calendar_verified=true`,
   `calendar_verification_status=verified_trading_day`,
   `calendar_source_type=official_exchange_or_regulator`,
   `calendar_source`, `calendar_verified_at_utc`,
   `expected_us_session_date`, `is_trading_day=true`, and the verified boolean
   `is_early_close`.
5. For every deterministic selective queue item, attempt to verify the
   completed close against an exact registered, accepted, timestamped original
   source independent of Yahoo Finance and yfinance. Do not request independent
   evidence for an empty queue or ordinary HOLD. The legacy Yahoo chart
   endpoint, another Yahoo page, or `Ticker.history` is not an independent
   source for this purpose.
   Add `quote_crosscheck` to the transient symbol row with:
   `status=verified`, `independent_of_builder=true`, source, direct URL,
   `bar_date`, `completed_close`, `verified_at_utc`, `difference_usd`, and
   `tolerance_usd`. Reject only the queued decision-changing technical or
   execution review if the absolute difference is greater than
   `max(USD 0.05, 0.10% of the builder close)`.
   If yfinance is throttled, times out, or returns an empty frame, use only the
   builder's bounded backoff. Never parallelize retries, rotate IP addresses,
   or silently substitute stale bars. Missing held-symbol OHLCV is grade `F`;
   a missing watch-only symbol disables only that watch item. A missing or
   pending registered Web route preserves the opportunity label and leaves
   execution `VERIFICATION_PENDING`; it does not become `NO_TRADE`.
6. Run `validate_technical_snapshot.py` for each holding/proxy pair and each
   watch symbol. The evaluator repeats this validation internally. A rejected
   technical check disables only EMA/watch timing; it must not hide a valid raw-
   close maximum-loss event. An unadjusted early-close volume comparison is not
   valid for timing.
7. Run `evaluate_alerts.py` with portfolio state, policy, the transient snapshot,
   and runtime state under its exclusive lock. Commit runtime state only after a
   non-`F` result.

## Active holding rules

Always evaluate the exact average-cost maximum-loss boundary first:

- SOXL: `average_cost * (1 - 0.20)`; current unrounded reference is USD
  98.66008 only while average cost remains USD 123.3251.
- MVLL: `average_cost * (1 - 0.60)`; current unrounded reference is USD
  16.71164 only while average cost remains USD 41.7791.
- NBIL: ignore the one-share holding for recurring risk timing only while both
  the verified share count is no more than one and verified position cost basis
  is no more than USD 65.20. The exception creates no candidate, quantity,
  order, or fill. Exceeding either exact cap is `STATE_MISMATCH/F`.

A raw completed close at or below the exact unrounded boundary is a grade `D`
hard-risk review. It is not a stop-market instruction, inferred fill, or order.
It freezes every new-buy watch from promotion.

EMA timing is active only as a grade `B` next-session human-review candidate.
Apply the conflict priority in policy and emit at most one timing candidate per
symbol per session. Shared slots prevent the strength and weakness paths from
selling the same tranche twice.

- SOXL anchor: 99 shares; review slots `24 / 24 / 24`; final residual 27 shares.
  The residual has no automatic EMA-sale rule. Approved triggers by the next
  unlocked slot include technical stop, confirmed 20EMA/failed-reclaim weakness,
  and--only while above average cost--objective overheat rejection or a confirmed
  failed higher high. SOXL 10EMA weakness alone is observation-only and never a
  reduction trigger.
- MVLL anchor: 396 shares; shared review slots `99 / 99 / 99 / 99`.
  Strength path: confirmed 10EMA reclaim, then 20EMA reclaim, then prior-20-day
  high/overheat. Weakness path: confirmed falling-10EMA weakness, decisive
  20EMA weakness, failed reclaim, or the technical stop.

The technical stop is the higher of prior-10-session low minus `0.25 ATR14`,
20EMA minus `0.75 ATR14`, and the exact hard-loss boundary. Confirm it with one
close at least `0.25 ATR14` below that dynamic level or two consecutive closes
at or below it. It remains a review candidate, never an automatic sale.

Do not unlock a later slot because price touched a level. The next slot opens
only after the user confirms the fill and portfolio state is updated in a
separate interactive turn. If current holdings do not equal anchor shares minus
confirmed completed tranches, return `F` for state mismatch.

Every confirmed timing fill record must contain tranche ID, completed-session
date, confirmed trigger path, and confirmed quantity. After a confirmed
reduction, keep the next technical-stop or weakness slot locked for three
completed sessions and until both the holding and confirmation proxy recover
above the EMA related to that confirmed trigger. Only the unsized hard
average-cost maximum-loss review bypasses this rearm gate. SOXL 10EMA weakness
alone is watch-only with `quantity=null` and cannot consume a reduction slot.

An excessive opening gap or an explicit provider halt/suspension flag cancels a
stale timing candidate and emits only a grade-`B`, `quantity=null` human-review
watch. Never assume a fill at a stop price. Zero volume alone is not proof of a
halt. Missing first-tradable OHLCV or a missing held-symbol completed close is
`DATA_INCOMPLETE/F`.

## Active watch-only entry detection

Detect only these long setups:

- aligned-uptrend pullback and confirmed 10EMA/20EMA reclaim;
- aligned-uptrend prior-20-day breakout followed by next-session acceptance.

Use the exact definitions in `alert_policy.json`, including ATR-normalized EMA
direction, volume confirmation, gap limit, extension limit, dollar-volume gate,
earnings blackout, and leveraged-proxy confirmation. Do not enable an aligned-
downtrend or early-recovery buy.

Read brokerage and available cash only from the current verified
`portfolio_state.json` on every run. Never copy a historical cash value from
this prompt, a prior report, or a market snapshot. Missing or unverified cash
keeps every new-buy item non-actionable. Positive verified cash removes only
the zero-cash gate; it cannot create grade `A`. The user must still separately
approve the exact instrument, risk budget, concentration cap, initial stop,
quantity, and research/valuation gates. Do not invent a leveraged ticker for
DRAM, NBIS, or BE.

## Inactive return-seeking research

The five-year multi-regime walk-forward gate is currently `failed_closed`
because the audited local SOXL/SOXX history begins after the required
2018-08-01 boundary. Do not generate a quantity or change a live review from
any of the following research blocks, even if their draft conditions appear
true: post-reduction re-entry, peak drawdown, time stop, dynamic gross-leverage
cap, or MA/MACD/RVOL/Stochastic/Chaikin added indicator votes. Their
`activation_eligible` and `active_candidate_generation` fields must both be
true in a later versioned policy before they can enter the evaluator.

The SOXL-only 0.75x/1.50x/2.25x/3.00x tier study is not a live portfolio cap
and cannot be extrapolated to MVLL or NBIL. A free-form or multi-agent LLM may
describe the regime but may never choose, raise, or optimize a numeric daily
leverage cap.

## Evidence and research gate

Apply `evidence_validation_policy` on every run: official calendar, official
issuer identity for each positive holding, same-session completed OHLCV,
raw-versus-adjusted price basis, independent close cross-check, formula
recomputation, and provenance ledger. Missing timing evidence disables timing
but cannot hide a valid raw-close hard-risk review; missing held raw OHLCV is
`DATA_INCOMPLETE/F`.

For any qualitative escalation, treat multi-agent or free-form LLM proposals as
untrusted research. Use separate identity/data, technical, bear-case, and risk-
controller roles and record an evidence ledger. Validate a canonical v2 record
with `manage-us-stock-strategy/scripts/validate_decision_record.py`; validate a
clearly labelled legacy schema-1.1 packet only with
`manage-us-stock-strategy/scripts/validate_research_packet.py`. Resolve both
from the workspace root. A validator may reject or downgrade a proposal, but it
cannot create cash, approve a ticker or quantity, override policy, or authorize
an order.

Apply `research_lifecycle_policy` for every qualitative escalation. Run a
bounded latest-news scan when a new held-position B or D event appears, before
any new-buy/add review, after a material issuer/sector/macro event, or when the
user requests a strategy review. Refresh holding and watchlist theses weekly
after the final completed U.S. session of the week and run a full valuation and
scenario refresh after month-end. Record bull/base/bear scenarios, the strongest
counter-thesis, objective invalidations, and the pre-trade decision before any
user-executed transaction. Save a local disclosure artifact and validate the
canonical v2 decision record with
`manage-us-stock-strategy/scripts/validate_decision_record.py`, resolved from
the workspace root. Legacy schema-1.1 packets may still use
`manage-us-stock-strategy/scripts/validate_research_packet.py`; they must not be
presented as v2 decision records. External publication is not authorized.
After an explicit user-confirmed fill or explicit no-trade decision, append
post-evaluations at 5, 20, and 60 completed sessions and named catalyst dates.
Never rewrite the locked decision or let reflection mutate policy, holdings,
cash, fills, thresholds, or candidate quantities.

## Deduplication and output

- Ordinary grade `B` timing events alert only on a false-to-true transition,
  changed trigger/quantity/rule version, or explicit rearm.
- A candidate expires after the next regular session, a state/policy change, a
  corporate action, or invalidation.
- Preserve event and delivery IDs in runtime state. Never infer execution.

Keep the internal task specification, policy evaluation, identifiers, and audit
record in English. Write the user-facing result in Korean by rendering exactly
one canonical headline key through the installed `ko-KR` locale resource:

- `alert_present`
- `alert_none`

Then show the verified session and KST time, state/policy/rules fingerprint,
technical validator status, SOXL/MVLL shares and cost/risk boundaries, the one
highest-priority timing tranche if present, and watch-only setup status. For
grade `F`, show no more than the three most important errors. End with the
localized `no_order_notice` message from the same locale resource.
