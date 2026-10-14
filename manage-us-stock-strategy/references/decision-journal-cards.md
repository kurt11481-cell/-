# Decision Journal: Card Decisions and Scoring (S7b)

Records what a holding card decided and what the user did, then scores both 5, 20 and 60 U.S.
sessions later. It grants no order or quantity authority: every proposal, entry and score keeps
`order_authority=false`, `quantity_authority="none"` and carries no quantity, price target or order field.

There is **one ledger**: `stock-strategy-system/decision_journal.json` (git-ignored, hash chained). No
other ledger file exists. Scores are never stored in it. `load_journal` also recomputes each entry's own invariants (`JOURNAL_ENTRY_INCONSISTENT:<sequence>:<reason>` is CORRUPT, so R0), because the chain cannot see an edit of the last entry; it does not detect truncation, fields with no other source, or a forgery that stays self-consistent.

## Entry types

| entry_type | Meaning | Created by |
|---|---|---|
| `s5_activation`, `line_review_completed`, `peak_review_card_completed` | S5 human confirmations (unchanged) | `propose-activation`, `propose-line-review`, `propose-peak-review` |
| `card_decision` | One position of one validated card: analysis action, sidecar action, conviction, reference close, evidence grade, state revision, `card_sha256` | `propose-card` (one proposal, one code, one entry per recordable position) |
| `card_user_decision` | What the user actually did on a recorded card decision (`ADD/HOLD/TRIM/EXIT/OTHER`). A correction is a new entry; the last one wins when scoring | `propose-user-decision` |

For card entries `review_id` is the card sha256 and `evaluation_session` is the decision session
(the card's expected completed U.S. session; for a user decision, its `effective_session`).
`decision_id = sha256({card_sha256, ticker})` and is also the entry id of a `card_decision`.

Card action to sidecar action (G3 decision 4, 2026-09-30): HOLD -> `HOLD_CORE` (`HOLD_REVIEW_REQUIRED`
when the card says review required); ADD -> `ADD_REVIEW`; TRIM and EXIT use the card's `reason_tag`
(`TRIM_*`, `EXIT_HARD_STOP`, `EXIT_THESIS`, `ROTATE_REVIEW`, `KEEP_CASH`). WITHHELD positions are not recorded.

## Write path (unchanged rule)

Only `portfolio_review_journal.py apply` writes the journal, in Cowork after the user sends
`확인 <code>` for that proposal in the current conversation, or by the user in their own terminal
(`--confirmed-via USER_TERMINAL`). Claude Code, Codex, scheduled tasks and Judge sessions never run it
and never type or guess the code. A card proposal is built only from a card that passes
`validate_holding_card.py` against its fact pack; `apply` re-checks every decision (ids, sidecar names,
fields, session) and appends all entries of the proposal in one atomic write.

```
python scripts/portfolio_review_journal.py propose-card --card <card.json> --fact-pack <fact-pack.json>
python scripts/portfolio_review_journal.py show --proposal <journal_proposal.json>
python scripts/portfolio_review_journal.py apply --proposal <journal_proposal.json> --confirm <CODE> --confirmed-via COWORK_CHAT_USER_MESSAGE --user-message "<verbatim>"   # Cowork / user only
python scripts/portfolio_review_journal.py propose-user-decision --decision-id <8+ chars of decision_id> --user-action TRIM [--effective-session YYYY-MM-DD] [--note "..."]
python scripts/portfolio_review_journal.py verify
```

Recording a card moves the journal head, so an S5 proposal made before it expires with
`JOURNAL_CHANGED_SINCE_PROPOSAL` and must be proposed again from a fresh exposure review.

## Scoring (read only)

```
python scripts/score_decision_journal.py [--journal ...] [--closes-root ...] [--calendar ...] [--output-root ...] [--evaluation-as-of ISO] [--decisions-root ...] [--event-calendar ...]
```

- Reads the journal through `load_journal`; writes only `workspace/outputs/journal-scores/<time>/journal-scores.json`
  (git-ignored). The output folder may not contain the journal or sit in `stock-strategy-system`,
  `workspace/policies` or `workspace/state`.
- Horizons 5, 20, 60 sessions of the activated U.S. calendar. A close counts only when its session's core close is
  at or before `--evaluation-as-of`.
- Stock closes: verified Kiwoom 30-minute-bar approximate closes (`regular-session-closes/history`). A close with
  unverified reasons gets `price_grade=REFERENCE_ONLY`. Splits come from `corporate-actions.json`; an invalid
  file, or an unexplained jump (ratio <= 0.5 or >= 2.0) in the window, makes the result `NOT_SCORABLE`.
- SPY is outside the Kiwoom scope. Optional file `<closes-root>/reference-closes/SPY.json`:
  `{"schema_version": "reference-closes-1.0", "symbol": "SPY", "source_note": "<where it came from>", "closes": {"YYYY-MM-DD": "430.50"}}`.
  SPY numbers are always labelled `REFERENCE_ONLY`; without the file only the cash comparison is scored.
- vs cash: ADD/HOLD = stock return; TRIM/EXIT = minus stock return. vs SPY: ADD/HOLD = stock - SPY; TRIM/EXIT = SPY - stock.
  The analysis action and the user's decision are scored as separate rows.
- Failures are statuses, not exceptions: `PENDING` (with `remaining_sessions`) or `NOT_SCORABLE` (with a reason).
- No conclusion about judgment quality before 30 scored decisions in one horizon (`conclusion_allowed`).
- Start (score-fix 2026-10-12): the first session closing strictly after `decision_as_of` (`FIRST_CLOSE_AFTER_DECISION`);
  a user decision uses its `effective_session` if that closes after `decision_as_of` (`EFFECTIVE_SESSION`). `pre_action_move`
  (decision session close -> start close) is shown, not scored; `start_close_vs_recorded_reference` keeps the decision session.
- Auto-core tickets go to `ticket_results` / `ticket_summary` only: journal `order_ticket` entries plus compare-mode tickets
  of `<decisions-root>/<YYYY-MM-DD>/decision.json` (no rerun files; unreadable files in `ticket_sources.errors`; journal wins).
  From the ticket session close, hypothetical LOC fill = buy close <= cap, sell close >= cap, else `vs_no_action` 0; the user's
  latest `ticket_outcome` is scored apart (average fill price; changed = `USER_CHANGED_ORDER`). Grade D (`COUNTERFACTUAL_D`),
  no cap, size or order type in the output, no conclusion before 30 scored.
- 1R (risk1r, user decision ext-1012-setup B, 2026-10-12): a buy ticket carries `risk_1r` = loss down to the invalidation
  line EMA20 - 0.75 ATR14 of the evaluation session (cent down): `r_pct` of the reference, `r_sigma`, share of equity;
  status `ok` | `below_band` (reference at or below the line) | `unk` (indicator missing). Grade D, display and record only:
  no sell, gate, size, price or evidence input. The `order_ticket` payload copies it (buy only) with `evidence_weak_kinds`.
- `r_multiple` per horizon = `vs_no_action` / recorded `r_pct`, only for a buy with 1R `ok` that filled (hypothetical
  `would_fill` true, or the user's filled/partial outcome) and a scored horizon; otherwise null. `ticket_summary.risk_1r_ok` = tickets with 1R `ok`.
- Event exposure (event-ctx4, `--event-calendar`, default `docs/claude/event-calendar.json`; `scripts/event_calendar.py`):
  each ticket row gets `event_exposure` = official event ids by landing time against the ticket session's `core_close_at`
  (early closes included): `before_fill` (previous close < landing <= fill), `overnight` (fill < landing <= next close; a buy
  carries it, a sell avoids it), `within_5` (fill < landing <= fifth next close), `possible` (date not announced), plus the
  symbol's `own_earnings` from the decision.json `earnings_calendar`. The report's `event_calendar` keeps the file sha256 and
  `classification=EX_POST_CURRENT_CALENDAR`: past tickets are classified with today's calendar (a corrected row changes the
  class); the decision-time view stays in the pre-open record (`workspace/outputs/pre-open`, via `event_calendar.py --decision`).
  Display and scoring only: no score value, core decision, gate, evidence, budget or price input; a missing or broken
  calendar is a status (`EVENT_CALENDAR_MISSING` / `_INVALID`). `ticket_summary` adds `event_exposure_ok` and
  `event_overnight` counts only; conclusions keep the 30-scored rule.

`portfolio_status.py` shows the scoring-pending count from the newest score report only when that report was made
from the journal's current last entry (`score_report=CURRENT`); otherwise every card decision counts as waiting
(`MISSING` or `STALE`).
