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

Margin buying power and unsettled or unconfirmed proceeds never become
`available_cash_usd`. A cropped or partial screenshot remains incomplete.

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
confirmation code. Screenshot proposals (schema 2.5) have no apply command in
v1, and the apply library refuses them (`SCREENSHOT_PROPOSAL_APPLY_NOT_SUPPORTED`).
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
`available_cash_usd` = min(withdrawable, order-available) USD. That cash is
"available now", not settled cash (`cash_verified_scope=available_cash_only`).
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
