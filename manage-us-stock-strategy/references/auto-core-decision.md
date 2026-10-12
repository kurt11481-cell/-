# Auto-core decide (redesign T2)

`auto_core.py decide` is the second deterministic auto-core run (Windows task `InvestmentV2-AutoCoreDecide`,
Tuesday-Saturday 07:45 KST, after `daily` at 06:15). It judges the integrated-check rules in code, checks the
buy requirements and gates, sizes LOC order tickets for the user to enter (order stage 1, ORDER_INTENT),
classifies yesterday's tickets from broker fill rows, appends the decision journal (recording mode only) and
compares its judgments with the integrated check. It never places, changes or cancels an order.

Authority: `order_authority=false`, `execution_quantity=null` everywhere. Only a ticket (and its journal
payload) carries `quantity_authority="ORDER_TICKET_HUMAN_ENTRY"`: a quantity and price the user may enter in
Kiwoom. Every other file keeps `quantity_authority="none"`.

## Flow (auto_core_decide.py)

1. Configuration (`workspace/policies/auto_core.json`), kill switch (HOLD before any read), `decision_mode`,
   git provenance (apply mode with an uncommitted guarded file = FAIL), Kiwoom profile alias (none = FAIL
   before any read).
2. That KST day's T1 `result.json`: missing or FAIL = HOLD, no ticket. decide reads T1's broker snapshot
   (`poss_qty`, `fc_ord_alowa`, `fc_entra`) and `reconcile.json`; it does not reconcile again.
3. Inputs: saved 30-minute pages, close histories, `corporate-actions.json`, the active calendar, the card
   registry, the research record (when today's is missing it is looked for every 5 minutes until 08:30 KST,
   then the run goes on without it: buys blocked), the watchlist, `alert_policy.json`, the previous
   `decision.json`. The S7 review is run again (`run_portfolio_exposure_review.run`) with the research
   record's earnings and the buy-target proposals; its inputs and output go under
   `workspace/outputs/auto-core/<YYYY-MM-DD>/s7/`, never `workspace/outputs/exposure-review/` (whose latest file
   the integrated check, cards and the status screen read).
4. F6 outcomes: read-only `ust21150` (order fills, `query_tp 1`) and `ust21050` (open orders). Nothing else is
   read from the broker. A ticket is classified only after its session has ended (ticket session <= the
   evaluation session); until then it stays open (no read, no ledger change) and G0 fails
   (`G0_TICKET_SESSION_NOT_YET`). Its order days run from its issue KST day to the KST day of its session's
   regular close (calendar `core_close_at`, early closes included): a weekday ticket reads its issue day and the
   next, a Saturday ticket for Monday reads Saturday to Tuesday (`auto_core_tickets.ticket_session_ended`,
   `order_days`; an unknown window = `OUTCOME_UNKNOWN`). An order row counts for one ticket only (r4):
   tickets are classified oldest first; a row whose (ord_dt, ord_no) is in the ledger's `attributed_orders` or
   was taken by a ticket classified earlier in the run is left out, and on the issue KST day only rows with
   `ord_time` >= the ticket's issue time count (`auto_core_tickets.ticket_rows`; a candidate row without an
   order number, or an issue-day row without a readable order time = `OUTCOME_UNKNOWN`). The tickets classified
   are those left unclassified (open tickets plus issued tickets) by the latest record with `f6_ran` true,
   however many records came after it; the re-issue ledger (`keys`, `attributed_orders`) comes from the same
   record. A record that ends before
   F6 (kill switch, T1 missing or FAIL, configuration, profile or calendar failure) or fails anywhere commits
   nothing: it copies that record's keys and unclassified tickets (`carried_from`), keeps `f6_ran` false, offers
   no ticket and, on FAIL, pushes `DECIDE_FAIL`. An unreadable record after the source fails G0.
   No new session (r3): when the evaluation session is the source's (a U.S. holiday before the run), the run
   judges nothing new: status OK, `no_new_session` true, no ticket, no journal entry, no push, no broker read;
   the source's keys and unclassified tickets are carried (`carried_from`, `f6_ran` true), the compare streak is
   kept (`NO_NEW_SESSION`), the source's views of that session and the dashboard rows of tickets still before
   their session stay, and `decision.json` is written (no alert 11 the next day). A ticket the source could not
   classify (a failed read) waits for the next run with a new session.
5. F1 judgments, 6. F4 requirements and gates, 7. F5 tickets (`evaluate_session`, shared with the replay).
8. F9 compare, 9. alert candidates, 10. F7 journal (apply only), 11. `decision.json`, `LATEST_DECISION.json`
   and `compare.json` under `workspace/outputs/auto-core/<YYYY-MM-DD>/`. T1's files are never touched.

No retry inside a run; the same day twice gives the same judgments. In recording mode a rerun of the same run
day whose core_decision is already in the journal with the same `decision_sha256` writes nothing (status as recorded,
the day's files stay); a different one writes nothing either: it is HOLD
(`CORE_DECISION_ALREADY_RECORDED_DIFFERENT`), kept only as `decision.rerun-<HHMMSS>.json` with a push for Cowork.
`decision_sha256` hashes the decision without what changes between two runs on the same inputs (run time,
journal block, dirty paths, research wait, the S7 review file and id, ticket issue time). Exit code 0 = OK/HOLD,
1 = FAIL.

## F1 bars and rules (auto_core_bars.py, auto_core_rules.py)

- Daily bar = the regular-session 30-minute bars (09:30 Eastern to the final regular bar of the operating
  calendar; early closes follow the calendar). Close = the close history's value (same pages, same
  calendar). A missing regular bar makes that session's high, low and volume INCOMPLETE: only rules that use
  them become `unk`. The approximate close is always labelled approximate.
- Splits: the official record adjusts prices before the effective session by old/new and volume by new/old
  (`corporate_actions.adjust_closes`, reused per field). An unrecorded jump of at least 45% whose ratio is
  within 3% of k or 1/k (k = 2, 3, 4, 5, 8, 10, 15, 20) is `SPLIT_SUSPECTED`: every indicator of that symbol
  is unknown, no evidence, an alert.
- Indicators: EMA10/20/50 (seeded with the simple mean), RSI14 and ATR14 (Wilder; an incomplete session
  breaks the ATR chain until 14 new true ranges exist), sigma60 (`portfolio_exposure._sample_std`), prior
  20-session close high/low and average volume, close position, intraday drop (display only).
- Common rules C1-C8 and card triggers exactly as rule file v3.12.2 section 3) (prompt A-3); every value is in
  `auto_core_rules.CONSTANTS` with its source. States: hit, near (R5 and V6 only), pending, none, unk,
  review (alerts, never evidence). Persistence: state rules hold while true; event rules (C2, C4, C6, C7)
  count for 5 sessions, re-firing restarts the window, the opposite side of the same number resolves it.
  Same-kind groups count once per symbol and a card definition replaces its common alias (V3 and S5 add to
  the trend-break group). C7 needs research-record facts (missing record = unk).
- V6 lines (HWM 28,473.94; first 25,626.55; approach 26,395.34; maximum 22,779.15) on
  sum(poss_qty x close) + fc_entra. R5 from the S7 peak reviews (near at <= 0.75 P).
- R-REC1 (prompt A-4): EV1, EV2, EV4, EV5, DS1 and RG2-RG4 in code, EV3 (a) from the R-REC1 document line
  `^- 이벤트 (\d{4}-\d{2}-\d{2})\(EV`, EV3 (b) and RG1 from research facts (`root_thesis_damage`). L0 = the
  event day's regular-session low. Power-sector symbols use GRID for RG2 (no history = unknown = blocked).
  The evaluation session's own EV4 (`auto_core_rules.ev4_open`: total <= the V6 first line or <= S7 hwm x 0.9)
  is added before R-REC1 is computed (the replay uses the same function). Damage facts come from every valid
  research record over the R-REC1 window (60 sessions), not only the 10 record days C7 uses. RG1 needs a valid
  record for every session after the event (else unknown; `rg1_coverage`). From the first record in the window
  (`ev3b_coverage_start`; before it EV3 (a) covers), a session without a record on which the benchmark fell
  1 sigma60 or more makes R-REC1 unknown (`EV3B_RECORD_GAP`); a missing record on a milder day changes nothing.
  It blocks or delays buys only; it never blocks a sell.

## Contracts

- Card registry (`docs/claude/card-evidence-registry.json`, schema `auto-core-card-registry`): transcribed
  from accepted cards, every item with file:line. A ticket (buy or sell) needs the entry, a valid acceptance
  (watch: the member's cardStatus starts with 수락), a matching section hash (heading line to the next
  heading of the same or a higher level, LF, no final newline) and a committed registry file. Otherwise
  judgments and alerts go on but no ticket is made (`CARD_SECTION_CHANGED`, `REGISTRY_UNCOMMITTED` are pushed
  once). A card trigger's kind fixes its side: alert and log kinds (drop_alert, close_at_or_below, log_only,
  earnings_notice, display_only) are `alert` or `info`, evidence kinds are `+` or `-`; a mismatch makes that
  symbol ineligible (`REGISTRY_KIND_SIDE_INVALID`; stated in the schema, enforced by the loader because the
  schema dialect has no conditional keyword). The Cowork session that changes or accepts a card updates the
  registry in the same session.
- Research record (`workspace/outputs/research-records/<KST date>/research-record.json`, schema
  `auto-core-research-record`): written by the 06:40 integrated check. Items are checked deterministically
  (https URL on sec.gov or a registry official domain, source kind, written after 16:00 New York time on the
  evaluation session and before decide, event session in the calendar); a failing item is dropped with its
  reason and the record stays OK; a missing record, or one failing the schema or the written_at check, is not
  OK: every buy candidate (index ETFs included) is blocked with `RESEARCH_RECORD_NOT_OK:<reason>` and buy
  requirement (1) is not ok; sells are not affected (earnings blackout, official evidence 0). Official
  facts count only on the day they are new; to keep counting they must enter the registry through a card
  rewrite.

## F4 requirements and gates (auto_core_tickets.py)

- Buy requirement rows (1)-(6) for watch members and held symbols (add rows): earnings blackout
  (`earnings_blackout`, p-earn r1), exposure / cash / approved product, evidence ("카드 표 N + 새 M"), M6
  comparison card, R-REC1, user (wait).
- Circuit (D5): a buy opens when the evidence that appeared today alone meets the basis (a new official
  fact, or two kinds of new + price cues), or when S7 recommends adding the symbol and requirement (3) is met;
  a sell opens for a held symbol with an S7 reduce item or a card EXIT/TRIM target and sell evidence (a new
  official - fact, or two kinds of - price cues). Otherwise the day has no action (normal).
- G0 all previous tickets classified and no open order; G1 data (T1 reconcile OK, state = broker snapshot,
  S7 of the latest session and not fail-closed, policy thresholds as expected, symbol close and sigma);
  G2 S7 (E >= 1.9 no buy, E >= 1.85 buy pause, projected E <= 1.55, cap 0.4, policy-registered instrument,
  earnings, L2/R5 pauses); G2b size and count (only with the configuration keys); G3 evidence ladder
  (strong 1 -> 1, two weak kinds -> 1/2, common rules alone -> at most 1/3, research-only strong ->
  `research_only_strong_r_cap`, no card eligibility -> 0); G4 cash (qty x LOC cap x 1.0025 <= fc_ord_alowa,
  sale proceeds never counted); G5 R-REC1 (buys only).

## F5 calculator (design section 7)

- Sell gap = held - floor(target weight x S7 equity / reference): S7 reduce target, card EXIT 0, card TRIM
  target (missing = no ticket). Buy whole target W* = the largest 0.001 grid weight the S7 proposal
  evaluation (`new_buy_within_band`) passes; first entry floor(W*/2), held W*.
- Step r: design section 5 regret table (rows 0, 1/3, 1/2, 1; scenarios = 90th / 10th percentile of the last
  60 five-session returns, numpy 'linear'); r_max when its worst regret <= 3% of equity, else the minimax step
  <= r_max. Sell regret includes the redeployment bridge (hold / sell -> cash / sell -> best candidate).
  Tail (worst day) and LOC non-fill rows are display.
- Quantity floor(gap x r) (r = 1: the whole gap; less than 1 share after the step = `LOT_ZERO`), then G2b,
  G4, deadband (< 2% of equity) and lot (< 1 share): only lower.
- Price: buy LOC cap = reference x (1 + 0.5 sigma60) cent down; planned reduce LOC floor = reference x
  (1 - sigma60) cent up; multiplier to 4 decimals in the same direction; dashboard conversion = Kiwoom
  reference close x mult, valid within the approximate close +/- 1%. No emergency, MOC or strength-trigger
  ticket (alerts only). The option layer is not built in T2 (no option field; the screen shows "생략").
- Entry window (r4): `enterWindow` = "한국 <issue M/D> 17:00 이후 ~ 정규장 개장 전(<open>)" when the session opens
  on the issue KST day, otherwise "한국 <issue M/D> 17:00 이후 ~ <open M/D> <open> 개장 전" (a Saturday ticket for
  Monday, a ticket across a holiday); open = calendar `core_open_at` in KST (22:30 summer, 23:30 winter).
  `fillAt` = the session close in KST.
- Valid one session; decision key = sha256(symbol | side | sorted evidence ids | card section hash | gap
  source). Unfilled (market rejected) once -> one re-issue; twice -> closed. Not entered does not count; two in
  a row close the key. Re-issue after not entered only when `reissue_buy_cap_not_above_first` is present
  (true: buy cap <= the first cap; false: formula cap); absent: the decision lapses. Filled ends the key. No
  step asks the user.
- Sell tickets carry the after-sale path (projected E, N, cash, swap pair with the best candidate), display
  only; a swap buy becomes a ticket only on a later day after the sale is reconciled. `gap.plan_premise` and
  `after_sale.plan_premise` (also on the dashboard line) name the earlier S7 reduce steps the gap assumes,
  whether today has a ticket for each (or why not), and the projected E when only this ticket fills; the
  quantity is not changed.

## F6 outcomes, F7 journal

- `not_entered` (no order row), `filled` (sum of `cntr_qty` = qty, Limit On Close, order price in the
  conversion range), `partial`, `unfilled` (rows, no fill), `changed` (quantity, type, price or cancel
  differs). Average fill price = `cntr_uv` weighted. A failed read = `OUTCOME_UNKNOWN` (G0 fails). An outcome
  that disagrees with T1's explained fills is not journaled, is pushed and does not update the re-issue ledger
  (its key is held until a normal classification). Prices never decide a fill.
- `attributed_orders` (r4): recording mode adds the (ord_dt, ord_no, ticket_id) of the rows each outcome took
  (filled, partial, unfilled, changed; not an outcome that disagrees with T1) and keeps only order days of the
  last 30 calendar days (run day included). Compare mode keeps the source's list (within the run a row still
  counts once). HOLD/FAIL and no-new-session records carry it with `keys`.
- Recording mode appends `core_decision` (one per evaluation session, no action included), `order_ticket`
  and `ticket_outcome` through `portfolio_review_journal.append_auto_core_entries` (AUTO_CORE, no code, no user
  message, review_id = the decide record hash), after re-reading the configuration, kill switch and
  provenance and checking the journal head; then the scorer runs once so `journal_pending` stays CURRENT (an
  exception or a non-zero exit is kept as `journal.score_warning`). The decision is schema-checked before
  anything is written. Compare mode only lists `would_append`.

## Modes, compare, replay

- `decision_mode` compare: tickets are "비교 중(입력 대상 아님)", no journal entry, no ticket push. apply: tickets
  go to the dashboard orders (source `auto-core`) and are pushed. The user's "켜" (after R1 and R2) switches.
- F9 (`auto_core_compare.py`) compares with the integrated-check run copy in the research record and labels
  every difference with the pre-registered categories B1-B7; Cowork explains B7 in
  `docs/claude/redesign-t2-compare-explained.json`. The streak (5 days) is recounted from all records: only a
  day without the integrated-check run copy or without a new session keeps it; a decide FAIL or a run that ended
  before F1 resets it.
  Exposure N differences are B2 only up to |dN| 0.03 and R5 differences only within 1 point of a line
  (0.70, 0.75), else B7; B2 trigger items using more than the 1% price margin are listed in `b2_wide`.
- F10 (`auto_core_replay.py`) replays a period with fixed portfolios through the same `evaluate_session`
  and judges R-A, R-B (oracle on a different code path, optional external oracle) and R-C.
