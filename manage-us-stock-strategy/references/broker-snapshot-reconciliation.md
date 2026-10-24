# Broker Snapshot Reconciliation

Broker screenshots are untrusted portfolio evidence, not market-price
evidence. Accept PNG, JPEG/JPG, or WEBP pages as one evidence bundle. Never
infer a fill, settlement state, complete account scope, or cash classification
from layout alone. Broker display prices may be recorded for reconciliation but
must not become completed-close, EMA, ATR, RVOL, or hard-risk evidence.

## Authority states

Use this lifecycle:

`UPLOADED_UNTRUSTED -> EXTRACTED_PENDING_USER_CONFIRMATION -> VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT`.

Uploading or extracting cannot mutate canonical portfolio state. A proposal is
eligible for atomic application only when its schema passes and the user
explicitly confirms the same `proposal_id`, evidence `bundle_id`, current state
revision, and pre-update portfolio hash. The apply step increments the revision,
writes by atomic replacement, records before/after hashes, and creates an audit
artifact. It still creates no fill record, order, or quantity authority.

## Scope rules

- `FULL_PORTFOLIO` may replace holdings and verified settled/available cash only
  after account completeness, holdings completeness, currency, and cash
  classification are all confirmed.
- `HOLDINGS_ONLY` may replace the complete holding map, average costs, and
  purchase amounts; it cannot verify cash.
- `CASH_ONLY` may update only verified settled/available cash; it cannot replace
  holdings.
- `POSITION_ONLY` may merge only explicitly confirmed ticker records; it cannot
  imply that omitted positions are absent.

Margin buying power and unfilled or unconfirmed proceeds never become
`available_cash_usd`. (For a Kiwoom read, the proceeds of a filled sale are part
of the order-available amount before settlement; see the I0 section below.) A
cropped or partial screenshot remains incomplete.

## Privacy and retention

Mask account identifiers, exclude names, login fields, OTPs, and credentials,
and require re-upload if sensitive login or OTP content is visible. Raw images
belong under `workspace/private_inputs/broker_snapshots/` and must remain Git
ignored. Commit only sanitized structured fixtures with fictional/masked
identifiers. Keep dates as unverified when the screen does not show a capture
date; a ranking date is not a capture date.

## Snapshot requests

Request the narrowest remediable scope only when fresh broker facts could change
an otherwise viable review. Use reason codes such as stale holdings, stale cash,
holdings reconciliation, cash verification, or full-portfolio reconciliation.
Do not request a broker snapshot to repair market-data, event, policy-authority,
or provider failures. Deduplicate request delivery separately from trade-review
delivery.

## Kiwoom read-only reconciliation (I0)

`manage-us-stock-strategy/scripts/reconcile_broker_state.py` is the only
portfolio-state write path. `propose` reads the Kiwoom account (read-only) and
never writes state; `apply` writes one proposal only after the user's explicit
confirmation code; `auto` (redesign T1, section 5) writes only in apply mode and
only when invariants I1-I5 pass. Screenshot proposals (schema 2.5) have no apply
command in v1, and the apply library refuses them (`SCREENSHOT_PROPOSAL_APPLY_NOT_SUPPORTED`).
The ledger and backups always sit next to the state file; there are no options
to move them.

### 1. Windows terminal: analysis, then proposal

The Kiwoom runtime lives on Windows, so the user runs both lines there (one
paste). The manual analysis command is unchanged:

```powershell
cd "E:\사업\##금동한\코덱스저장소"
python manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py
python manage-us-stock-strategy/scripts/reconcile_broker_state.py propose
```

`propose` prints one of three results and the proposal path under the
Git-ignored `workspace/outputs/reconciliation/<UTC time>/`:

- `브로커와 상태 일치. 조정 필요 없음.`: done.
- `... Cowork에서 "조정 확인해줘"라고 보내 주세요. 유효: HH:MM KST까지.`:
  continue in Cowork. The metadata-only variant means holdings, costs and cash
  already match and only the broker confirmation record (`as_of`, scope) is old.
- `조정 제안을 만들 수 없습니다: <codes>`: nothing to apply. Required reads
  (holdings `ust21070`, deposit `ust21110`, fills `ust21510`) must all pass;
  retry `propose` at most three times, then stop and diagnose.

The proposal holds holdings (held quantity, integer), average cost, derived
cost basis (quantity x average cost, rounded half-up to cents), and
`available_cash_usd` = the Kiwoom order-available amount (`fc_ord_alowa`, basis
`KIWOOM_ORDER_AVAILABLE_USD`, redesign T1 F1, user 2026-10-09/10-10). It
includes the proceeds of a filled sale before settlement (Kiwoom lets them buy
right after the fill); it is not settled cash (`cash_verified_scope=available_cash_only`,
`unsettled_funds_included=true`). One check on the same read guards it:
order-available above withdrawable (`fc_pymn_alowa`) by more than 1.00 USD needs
a filled, unsettled sale in the same holdings read (`qty > poss_qty` for at least
one row), else `CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS`; order-available
below withdrawable by more than 1.00 USD is `CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE`.
Both block the proposal. The foreign-currency deposit (`fc_entra`) shows settled
money only and is never compared. The proposal records `cash_components`
(deposit, withdrawable, order-available, unsettled component) for review. The
snapshot's `settled_available_cash` keeps its old meaning (the minimum), so the
dashboard buy-funding cap does not widen, and unfilled sale proceeds are never cash.
Open orders are display-only: when that read fails the proposal carries
`OPEN_ORDERS_UNVERIFIED` and state records `open_orders_verified=false`.
`never_touched` fields (stage, timing_plan, confirmed trades, candidates,
broker display snapshot, strategy fields) are never written, and no fill is
recorded or inferred.

### 2. Cowork: "조정 확인해줘"

1. Read this file first. Then run
   `python manage-us-stock-strategy/scripts/reconcile_broker_state.py show`
   and show its output to the user verbatim. Do not recompute or reformat the
   values.
2. Stop instead of asking for a code when the table says the proposal cannot be
   applied or has expired. On expiry (15 minutes after the oldest required read,
   policy `maximum_age_seconds=900`) ask the user to rerun only `propose`.
3. If the table stops with `LEDGER_INTEGRITY_FAILED`, or with the
   `STATE_CHANGED_OUTSIDE_LEDGER` stop message (the ledger recorded the last
   apply but the state file is still the state before it, i.e. the state write
   failed), stop all applies (P4 1-12 damage). Preserve backups and the ledger,
   and report; a restore procedure is designed separately (K3). Apply also
   refuses a state file that is not valid JSON.
   If `STATE_CHANGED_OUTSIDE_LEDGER` is only a warning (the state changed
   outside the ledger after the last apply), tell the user before any
   confirmation: the "current" column shows the file as it is now. If the user
   still confirms, apply proceeds and records the outside change in its ledger
   line.
4. If the table shows `TIMING_PLAN_TICKER_CHANGED`, `POLICY_POSITIONS_MISMATCH`,
   or a failed post-apply alert-engine check, tell the user before any
   confirmation and let them choose: apply or hold. Timing slots were removed
   from the approved policy (`holding_timing_rules.positions` is empty since
   I0-b, 2026-10-06), so the check should not report timing-anchor errors. If
   the post-apply check fails, explain its errors to the user before any
   confirmation; if the cause is unknown, do not apply.
5. Apply only when the user, in this conversation and after seeing this table,
   sends `확인 <code>` with exactly this proposal's code. Never type, complete,
   or guess the code yourself; never reuse a confirmation from an earlier
   proposal or conversation; never apply from a scheduled task. `취소` or any
   other reply means do not apply.
6. Run, with the user's message copied verbatim:

   ```
   python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm <code> --confirmed-via COWORK_CHAT_USER_MESSAGE --user-message "<user message>"
   ```

7. Report the one-line result (`revision a → b 적용. 백업: ...`). If apply is
   rejected, report the reason code; do not retry with other arguments.
8. Ask the user to rerun the manual analysis and confirm
   `broker_diff_status=MATCH`.

The confirmation code is a mistake guard, not proof of a human: any agent that
can read the proposal can read the code. The real controls are this rule, the
recorded user message, and the library checks (unresolved fields, expiry, state
hash and revision, proposal integrity, code match, ledger continuity). Claude
Code denies `reconcile_broker_state.py apply` and direct edits of the state,
ledger and backups.

Undo: v1 has no restore command. A wrong value is corrected by a new proposal
(the broker is the reference). Each apply first writes
`stock-strategy-system/backups/portfolio_state.r<rev>.<time>.json` and one line
in `stock-strategy-system/reconciliation_ledger.jsonl` (hash chain, canonical
state hash before and after), then replaces the state atomically, keeping the
file's existing line endings. Backups, ledger and proposals contain holdings
and cash; they are Git-ignored and must never be committed or pasted elsewhere.

### 3. Fallback: the user's own Windows terminal

If the Cowork VM cannot run apply, the user may apply from their own terminal
after reading the table:

```powershell
python manage-us-stock-strategy/scripts/reconcile_broker_state.py show
python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm <code> --confirmed-via USER_TERMINAL
```

### 4. S5 cash-flow declaration (R6, optional inputs of propose)

After the S5 activation record exists, every reconciliation should carry the
cash-flow block so that review lines can be judged
(see [portfolio-exposure-review.md](portfolio-exposure-review.md)):

```powershell
python manage-us-stock-strategy/scripts/reconcile_broker_state.py propose --cash-flow-evidence <evidence.json>
python manage-us-stock-strategy/scripts/reconcile_broker_state.py propose --cash-flow-evidence <evidence.json> --declare-cash-flow-usd 500.00
```

- The evidence file is a saved, sanitized Kiwoom transaction history
  (`cash_flow_evidence.py normalize`). `propose` reads no extra broker API for it.
- The block is inside the proposal hash. A declaration therefore always gives a
  new proposal and a new confirmation code; an earlier code never covers it.
- A declared amount beyond the deposits, withdrawals and currency exchanges in
  the evidence is rejected before any broker read. Dividends, fees and taxes
  are never cash flows.
- `show` prints the block in the same table. Apply records it in the ledger
  entry only; no state field is written for it and `timing_plan` stays untouched.
- Without the two options, propose, show and apply behave exactly as before.

### 5. Auto-core path (redesign T1, `reconcile_broker_state.py auto`)

The Windows task `InvestmentV2-AutoCore` (`auto_core.py daily`, Tue-Sat 06:15 KST)
runs this path; it can also be run by hand. Nobody types a code and nothing in
it can place, change or cancel an order. Configuration:
`workspace/policies/auto_core.json` (`mode` compare|apply, `kill_switch`,
`compare_days_required`, `schedule_kst`, `symbols_extra`; schema
`auto-core-config.schema.json`). Only a person changes it.

One read, all read-only through the account bridge (profile alias from
`kiwoom-readonly-policy.json`, the shared token, one recovery, no reissue on 8005):
holdings `ust21070`, deposit `ust21110`, deposit detail `ust21160`, open orders
`ust21050`, fills `ust21510`, realized P&L `ust21630` (display), daily order fills
`ust21150` for every order day (`ord_dt`, the U.S. ET order day) from the day
before the last record's KST day through today's KST day, day trades
`ust21610` for each U.S. session with a fill after the last record, and
transaction history `ust21100` for the evidence period. The dated
reads take only `YYYYMMDD` dates (`DATED_PARAMETERS`); nothing else reaches a
request body.

Invariants (all must pass before anything is recorded; `auto_core_reconcile.py`):

| | Rule | Fails as |
|---|---|---|
| I1 | every required read above returned `return_code` 0 (the measured no-data declarations of open orders, transaction history, daily order fills and day trades count as zero rows) | `REQUIRED_READ_NOT_PASS:<read>` |
| I2 | per ticker, held quantity now = recorded quantity + broker fills (buy - sell) filled after the last record; new and vanished tickers included | `QUANTITY_CHANGE_NOT_EXPLAINED_BY_FILLS:<ticker>`, `FILL_*` |
| I3 | order-available now = order-available of the last record's own snapshot + actual settlement amounts of the fills after that snapshot + classified transaction-history rows processed after it, within 1.00 USD; open orders reserve cash and hold | `BASELINE_ORDER_AVAILABLE_UNKNOWN:<why>`, `CASH_CHANGE_NOT_EXPLAINED:<usd>`, `FILL_SOURCES_DISAGREE`, `SETTLEMENT_*`, `FLOW_ROW_*`, `OPEN_ORDERS_PRESENT` |
| I4 | state hash and revision equal the last ledger entry; ledger hash chain intact | `STATE_CHANGED_OUTSIDE_LEDGER`, `LEDGER_INTEGRITY_FAILED`, `LEDGER_MISSING` |
| I5 | the write would change no field other than holdings, average cost, cost basis, cash and the broker record; the state is hashed again just before writing | `NEVER_TOUCHED_FIELD_CHANGED:<field>` |

- Fills come only from broker fill records. `ord_dt` is the U.S. (ET) order
  day D (observed 2026-10-21/22: after-hours fills at 06:13-06:40 KST on 10/22
  carry 20261021; the Kiwoom spec names no time zone). A fill's KST time is
  `cntr_time` on the KST day D or D+1 that puts it within D 04:00-20:00 ET
  (zoneinfo, so the KST bounds move with daylight saving time); its session is
  D. `ord_time` is placed the same way after D-1 20:00 ET and not after the
  fill. A fill outside that window (`FILL_TIME_OUTSIDE_US_SESSION`, e.g. a
  Kiwoom day-session fill, never observed), an order time that fits nowhere
  (`FILL_TIME_INVALID`) or a fill later than the snapshot
  (`FILL_AFTER_SNAPSHOT`) holds. Only fills after the last record's
  `as_of_timestamp` count. Average cost is the
  broker's `frgn_stk_book_uv` and is not part of the explanation.
- I3 baseline (broker to broker): the order-available cash and `generated_at` of
  the snapshot behind the last record. An auto-core ledger line names it
  (`auto_core.snapshot`, a create-once `kiwoom_broker_snapshot.<hash16>.shadow.json`);
  a human-path line names it through its `proposal_id` (the saved proposal under
  `workspace/outputs/reconciliation/` holds the snapshot path and hash). The
  snapshot must be schema-valid and hash to that value and to the state's
  `evidence_sha256`. If it cannot be found or has no order-available amount, I3
  holds `BASELINE_ORDER_AVAILABLE_UNKNOWN`; the state's cash (which may still be
  the old minimum definition) is never used instead.
- I3 fill amounts are the actual settlement amounts with fees: a pending one from
  the deposit-detail slot of its Korean settlement date (`dN_usd_sell_excta` /
  `dN_usd_buy_excta`, N = 1..4; D0 has no amount fields), a settled one from the
  transaction-history trade rows of that date (`fc_exct_amt`). The ust21610 fee
  column (`cmsn_altx`) is an estimate (measured about 0.25% against actual fees of
  about 0.07%) and is not used. ust21610 binds each (session, ticker) to the
  ust21150 quantities and gives the gross amounts. Amounts are known per
  settlement date, so sessions are matched to dates in order: the sessions on one
  date must equal its amounts within the fee range on each side
  (`|settlement - gross| <= gross x 0.5% + 0.50`), and a settled date's rows must
  carry exactly their quantities. A date can only hold fills of earlier KST days:
  slots and rows dated on or before the first counted fill's KST day belong to
  fills before the baseline and are never counted (a settlement does not move the
  order-available cash).
- A settlement due today (KST, D0) is not visible before the broker's morning
  processing (about 08:07): D0 has no slot amounts and the trade row comes later
  (T1 r3 C4). (a) When the previous run's `reconcile.json` recorded that date as a
  `PENDING` settlement (`invariants.I3.settlements`), that amount stands for it
  (source `PENDING_PREVIOUS_RUN`, with `carried_from`) and I3 is judged as usual.
  (b) Otherwise, if every other date matches with today's left open, I3 holds with
  the single reason `SETTLEMENT_D0_NOT_SHOWN:<date>`, and the cash residual must
  lie within the fee range of the sessions put on today (else also
  `SETTLEMENT_D0_OUTSIDE_FEE_RANGE`). Such a day never records; in compare mode it
  keeps the streak (no +1, no reset; `compare.basis`
  `KEPT_D0_SETTLEMENT_NOT_SHOWN`) and the next day compares from the run before it.
- Transaction-history rows (I3) count by KST day and processing time. Trades are
  explained by the fills; deposits, withdrawals and FX use the reviewed table's
  sign; dividends, fees, taxes, interest and corporate-action cash take their sign
  from the memo (`입금` +, `출금` -). Anything else holds.
- Cash-flow evidence (F3): the period starts on the last recorded evidence
  `period_to` (that day is covered again so rows processed later that day are
  never skipped; counted rows are deduplicated by key) or the S5 activation date,
  and ends today (KST). Only the sanitized evidence is kept
  (`workspace/private_inputs/cash_flow_evidence/auto-core-*.json`, collection
  `AUTO_CORE_BRIDGE_READ`). The external net is declared in full automatically,
  so the HWM needs no human declaration. A normalization failure or an
  unresolved row is a HOLD.
- compare mode never writes the state, ledger, backups or journal. It records
  `would_apply` in `workspace/outputs/auto-core/<YYYY-MM-DD>/reconcile.json`.
  When the fill window since the last record passes 80% of its 14-day limit,
  `LATEST.json` `next_action_for_user` says `기록 모드 켜기 필요(기준 오래됨)`
  (the run is not failed for it; over the limit the reconciliation still fails and
  writes nothing).
- apply mode writes through `apply_user_confirmed_broker_snapshot.apply_auto_core`
  only when I1-I5, the evidence and the kill switch all allow it, the run records
  a git commit SHA, and no guarded file has an uncommitted change: every tracked
  file under `manage-us-stock-strategy/{scripts,schemas,assets}/` plus the retired
  acceptance pin list and the auto-core's own files (checked before any read).
  Just before the write the library reads again `auto_core.json` (mode apply,
  kill switch off), the git provenance (no guarded change, same commit) and the
  proposal's cash-flow declaration (`NO_EXTERNAL_FLOW` or `DECLARED_IN_FULL`);
  any mismatch refuses the write (`AUTO_CORE_RECHECK_*`, FAIL, nothing written).
  It uses the same backup,
  ledger line, hash chain and atomic replacement as apply; the ledger line carries
  `confirmation_method=AUTO_CORE_INVARIANTS`, `confirm_code=null`,
  `user_message=null` and `auto_core` (the invariant results, commit SHA, dirty
  paths, the I3 baseline snapshot and this record's own snapshot, each as path and
  hash). The state record says `VERIFIED_AUTO_CORE_INVARIANTS_BROKER_SNAPSHOT`.
  No code is made, copied or recorded.
- `kill_switch: true` stops the run before any read (HOLD). A missing
  configuration runs compare only and reports HOLD `AUTO_CORE_CONFIG_MISSING`.
  A missing or empty `token_profile_alias` in `kiwoom-readonly-policy.json` fails
  the run before any read (`KIWOOM_PROFILE_ALIAS_MISSING`); `collect_30m.ps1`
  requires `-KiwoomProfile`.
- Any failed invariant is a HOLD: state unchanged, one alert line through
  `LATEST.json`, and the next run retries. A collection error is a FAIL (exit 1).
  A FAIL at any step (30-minute bars and exposure included) resets the compare
  streak to 0 (`RUN_FAILED`).
- Proposal warnings and post-apply alert check errors never hold a record; they
  are listed in `warnings[]` of `reconcile.json`, `result.json` and `LATEST.json`
  (`PROPOSAL_WARNING:<code>`, `POST_APPLY_CHECK_ERROR:<text>`) so the 06:40 check
  can push a record that carries them.
- The `propose` / `show` / `apply` path above stays as the transition fallback
  until recording is switched on; then the routine retires (redesign T4).
