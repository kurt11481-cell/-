# Portfolio Exposure Review (S5 r2, first stage)

Display-only measurement of portfolio exposure, review lines and target-weight
recommendations approved as "S5 final proposal r2" (user approvals S7 1-7,
2026-10-01). It grants no order or quantity authority: every output keeps
`order_authority=false`, `quantity_authority="none"`, `execution_quantity=null`
and shows target weights only. The decision is always the user's.

First stage (`status: approved_display_only_old_controls_retained`): the rules
below are added next to the existing controls. Cost-basis loss limits, SOXL/MVLL
timing slots, `weakness_10ema` and the rearm rule stay active and unchanged.
Retiring them, the instrument registry change and the pinned evaluator/timing
engine belong to the second stage (separate approval and Judge).

## Policy source

`stock-strategy-system/alert_policy.json`, sections `portfolio_exposure_policy`
and `portfolio_review_lines`. Scripts read every threshold from there and never
default a missing value.

| Rule | Meaning |
|---|---|
| R0 | Fail closed: any of seven triggers pauses add and new-buy recommendations; reduce recommendations and warnings continue with an UNVERIFIED label |
| R1 | E = max(N, V). N = sum(multiplier x weight). V = stdev(portfolio daily return) / stdev(SOXX), current weights fixed, common window of up to 252 returns, minimum 60 |
| R2 | Target 1.55. E >= 1.85: reduce + pause new buys. E >= 1.9: block all new buys + urgent reduce. E <= 1.25: add. Every exposure-increasing recommendation needs projected E <= 1.55 and the single-stock cap |
| R3 | Single-stock nominal cap 0.4 (stocks, MVLL, DRAM; SOXL and TQQQ exempt). Earnings blackout (p-earn r1): an announced date blocks its window; a confirmed "not announced yet" from an official source, checked after the evaluation session close, is not a blackout; a missing, stale, unknown or failed check stays a blackout. DRAM never substitutes MU during MU's blackout |
| R4 | Review lines at HWM x 0.90, 0.80, 0.70 ...; compared before rounding with `<=`; once per line per drawdown; re-armed by a new HWM; L2 and below pause recommendations until a journal review |
| R5 | Instrument peak since activation (or first reconciled date); close <= peak x 0.70 asks for a card rewrite and pauses adds for that instrument |
| R6 | Deposits and withdrawals are declared at reconciliation; undeclared flows hold HWM and line evaluation |
| R9 | Swap: sell leg first; the buy leg needs verified cash |

Alert grades (user decision P2): L1 = C, L2 and further lines = D, E >= 1.9 = D,
E >= 1.85 = B, peak review = B, fail-closed = B with the UNVERIFIED label, add = B.

## Files

| Path | Role | Written by |
|---|---|---|
| `scripts/portfolio_exposure.py` | Pure calculation, no file or clock access | - |
| `scripts/run_portfolio_exposure_review.py` | Reads inputs, writes one result file | any session (read-only inputs) |
| `scripts/regular_session_close_history.py` | Verifies saved 30-minute pages, writes close history | Cowork / user |
| `scripts/cash_flow_evidence.py` | Sanitizes a saved transaction history, builds the declaration block | Cowork / user |
| `scripts/portfolio_review_journal.py` | Human confirmations only | `apply`: Cowork after "확인 <code>", or the user's terminal |
| `workspace/outputs/regular-session-closes/pages/<SYMBOL>/*.json` | Saved Kiwoom CLI pages (evidence) | Cowork |
| `workspace/outputs/regular-session-closes/history/<SYMBOL>.close-history.json` | Normalized closes | `regular_session_close_history.py build` |
| `scripts/corporate_actions.py` | Pure validation and split adjustment of the corporate-action record | - |
| `workspace/outputs/regular-session-closes/corporate-actions.json` | Official split record (read-only input of the runner) | Cowork conversation only |
| `workspace/outputs/exposure-review/<session>/portfolio-exposure-review.<time>.json` | Review result | runner |
| `workspace/private_inputs/cash_flow_evidence/` | Sanitized transaction histories | Cowork |
| `stock-strategy-system/decision_journal.json` | Confirmation journal (hash chain) | journal `apply` only |

All of these outputs hold holdings, equity or account activity and are
Git-ignored. Never commit or paste them elsewhere.

## Close definition (user decision P3)

The close is the close of the last 30-minute bar of the regular session. Bars
are labelled by their start time in U.S. Eastern time: the 15:30 bar on a
regular day, the bar starting 30 minutes before `core_close_at` on an
early-close day. Pre-market, after-hours and overnight bars are dropped. The
value is an approximate close, not the official closing-auction price, and is
shown as such. A reference close, when supplied, is shown as a difference only.
Low and high prices are never used. The page-end marker `upd_stkpc_tp = "1f"`
is not an adjusted-price flag.

A close is unverified (values stay visible, R0 applies) when:

- the session calendar used is not the ACTIVE production calendar,
- the session's UTC offset is not one under which bar labels were measured
  (only `-04:00` so far; remeasure after 2026-11-02),
- the saved pages are missing (a history without its pages is never verified).

The runner decides this itself. It rebuilds every history from the saved pages
with its own calendar and uses a close only when the stored history matches the
rebuild exactly; an edited or stale history is treated as absent. Calendar
authority always comes from the Production integrated authority
(`workspace/policies/integrated_identity_session_activation.json`, loaded by
`load_production_integrated_authority_snapshot`; there is no command-line or
environment override). A `--calendar` artifact counts as ACTIVE only when its
raw sha256 equals the calendar hash that authority activates. A review built
from files other than the production defaults (`--state`, `--journal`,
`--closes-root`, `--policy`, `--ledger`, `--now`) or from a `--calendar` that is
not the active calendar is labelled `[비표준 입력]` on every display line.

Raw (unadjusted) prices are collected. A session-to-session close ratio of 0.5
or lower, or 2.0 or higher, is treated as a possible unadjusted split and makes
V unavailable until the history is reviewed. The guard (bounds and operator
unchanged) is applied after the split adjustment from the corporate-action
record below, so a recorded split no longer trips it and a mis-dated or
mis-sized record still does.

V uses the last 252 returns, or fewer only when the available history itself
starts later (listing date or the provider's retention start); that case is
labelled "short history". A close missing after that start is a gap: the window
is never shortened around it and V is unavailable (R0).

The evaluation session is the latest completed session. If the calendar does
not cover today the default run fails instead of presenting the calendar's last
session as the latest. An explicitly requested older session (`--session`) is
labelled `[최신 세션 아님]` and fails closed.

A reconciliation dated after the evaluation session is not used for that
session and cannot lift a hold that covers it. While line evaluation is on hold
(`HELD`), R0 applies.

## Corporate-action record (split adjustment)

The policy basis is `sox_equivalent.return_basis =
split_adjusted_regular_session_close` (`technical_price_basis_required =
split_adjusted_ohlc_rescaled_to_latest_raw_close`). The saved closes stay raw;
the runner reads `<closes-root>/corporate-actions.json` (follows `--closes-root`,
no option of its own) and rescales on every run. The file is never written by
the runner or any script.

```json
{"schema_version": "corporate-actions-1.0", "artifact_type": "CORPORATE_ACTIONS",
 "actions": [{"symbol": "MVLL", "action_type": "SPLIT", "effective_session": "2026-06-26",
   "new_shares": 3, "old_shares": 1,
   "official_source": {"issuer": "GraniteShares", "url": "https://...", "published_date": "2026-06-12"},
   "kiwoom_crosscheck": {"api_id": "usa06012", "adjusted": "1", "dt": "20260626",
                         "upd_stkpc_tp": "3231", "upd_rt": "-66.66700"},
   "recorded_by": "cowork", "recorded_at": "2026-10-02"}]}
```

`effective_session` is the first session traded at the post-split price. One
old share becomes `new_shares / old_shares` shares (3:1 is 3/1, a 1:10 reverse
split is 1/10). Schema: `schemas/corporate-actions.schema.json`; keys are exact
and extra keys are rejected.

A file with any defect is `INVALID` as a whole: not JSON or not schema-valid;
`action_type` other than `SPLIT`; shares not integers of at least 1 or equal;
duplicate (symbol, effective session); an effective session outside this run's
calendar; `kiwoom_crosscheck.dt` not the effective session as `YYYYMMDD`;
`upd_stkpc_tp` empty or the page-end marker `1f` (its value is not
interpreted); `upd_rt` differing from `(old/new - 1) x 100` by more than
0.005; `official_source.url` not `https://`; `published_date` after the
effective session. A missing file is `MISSING` and behaves as before (the
guard catches a large split).

Effect:

- Every close before an effective session is multiplied by `old/new`
  (records for one symbol multiply). A record applies only from its effective
  session on, so an older `--session` run does not see a later split.
- The adjusted closes feed only V (return window) and the single-stock peak
  review. Equity, review lines, the activation candidate, the displayed
  position close and the benchmark close check keep the raw closes: a
  snapshot quantity is a raw share count of that session.
- `INVALID`: V is unavailable (`V_UNAVAILABLE:CORPORATE_ACTIONS_INVALID`) and
  every held instrument's peak review is `UNVERIFIED`. Equity and the lines
  are not affected.
- A snapshot dated before the effective session of a recorded split cannot
  value that session or later ones for a holding it lists: the session's
  equity is unverified with `SPLIT_RECONCILIATION_REQUIRED:<SYMBOL>:<session>`
  (same handling as a missing close). Quantities are never rescaled by the
  ratio; a reconciliation dated on or after the effective session clears it.
- The review echoes `inputs.corporate_actions` (`status`, raw-byte `sha256`,
  `errors`, `applied` with `price_factor`). The file is a watched input: a change
  during a run is `READ_ONLY_INPUT_MUTATION_DETECTED`.

Records are added only in a Cowork conversation, and only with both
evidence kinds: the issuer's official announcement and the Kiwoom adjusted
daily-price flag. Scheduled tasks, Claude Code, Codex and Judge sessions never
add or edit one. Dividend adjustment is not part of this basis.

## Earnings blackout input (R3, p-earn r1)

Source: `docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md` (r1, user approval
2026-10-03). It applies to the card stock core (BE, MU, NBIS, DELL, AMD) and, through the MU -> DRAM
ban, to DRAM. Being outside the blackout is never a reason to buy (display only).

`--earnings` holds one record per symbol (values are format examples only). Cowork writes it from
official sources; nothing generates it automatically.

```json
{"earnings": {
  "MU":   {"status": "NOT_ANNOUNCED", "source_kind": "COMPANY_IR", "source_url": "https://<issuer IR page>", "checked_at": "<ISO time with offset>"},
  "DELL": {"status": "VERIFIED", "announcement_session": "<YYYY-MM-DD>", "timing": "AFTER_CLOSE"}
}}
```

- `VERIFIED`: window reading (`earnings_blackout_window_reading`) — from the second regular session
  before the announcement session through the first regular session after results; `BEFORE_OPEN`
  ends at the announcement session; any other timing, missing included, is read as after-close.
  Codes: `EARNINGS_BLACKOUT`, `OUTSIDE_EARNINGS_BLACKOUT`, `EARNINGS_DATE_STALE` (the window ended
  before the next session), `EARNINGS_WINDOW_NOT_CHECKABLE` (outside the approved calendar).
- `NOT_ANNOUNCED` (exactly this string) passes only when every step holds, in this order; the
  first failure is the code:
  1. next session and evaluation session in the calendar, else `EARNINGS_WINDOW_NOT_CHECKABLE`;
  2. no `announcement_session` or `timing` key, else `EARNINGS_RECORD_CONTRADICTORY`;
  3. `source_kind` is `COMPANY_IR`, `COMPANY_PRESS_RELEASE` or `SEC_FILING`, `source_url` starts
     with `https://` and has a host, `checked_at` is ISO with a UTC offset, else
     `EARNINGS_CHECK_SOURCE_INVALID`;
  4. the review's `generated_at` (passed by the runner) is ISO with an offset, else
     `EARNINGS_CHECK_GENERATED_AT_INVALID`;
  5. `checked_at` is not after `generated_at`, else `EARNINGS_CHECK_FUTURE_TIMESTAMP`;
  6. `checked_at` is at or after 16:00 New York time (EDT or EST for that date; 16:00 on an
     early-close day too) on the evaluation session date, else `EARNINGS_CHECK_STALE`;
  7. then `EARNINGS_NOT_ANNOUNCED_CHECKED`: not a blackout.
- No `--earnings`, no record, or any other status (lower case included): `EARNINGS_DATE_UNVERIFIED`.
  Every blocking code omits the increase recommendation, an MU blackout of any kind omits DRAM
  (`BLACKOUT_SUBSTITUTION_PROHIBITED:MU`), and Cowork reports each as "실적일 확인 필요" (the review shows the raw code).
- Accepted remaining risk: a date announced after the check, with the announcement within two
  sessions of the next session, can leave a recommendation inside the window. Read the integrated
  check's earnings-announcement alert before any buy.

## Routine (Cowork, after the U.S. close, read-only Kiwoom CLI)

Token (updated 2026-10-07; kiwoom-token-reuse `5269cfd`, live check passed 2026-10-06, acceptance
re-pinned to `835d4f46` in `fdddc87`). The bridges (broker-shadow proposal, manual analysis) reuse
the same file token as kiwoomcli (policy alias `token_profile_alias` in
`workspace/policies/kiwoom-readonly-policy.json`; a new token only when none is saved or it is
within 10 minutes of expiry, and at most one recovery per bridge session). No token order is
needed and no `kiwoomcli auth refresh` / `auth login` before the routine. If a kiwoomcli command
or a bridge run still reports an auth failure (8005), do not run auth, login or token reissue from
Claude: mark that step failed, keep the gap visible and report it. A kiwoomcli exit code 0 is not
proof of success: open each saved file and check that `return_code` is 0 (an auth failure can be
saved with exit code 0). Never run kiwoomcli while a bridge run is in progress.

1. Save the 30-minute bars of each symbol (SOXX and every held instrument) into
   `workspace/outputs/regular-session-closes/pages/<SYMBOL>/`:
   `kiwoomcli overseas candles stock-minute` with `interval=30`, `adjusted=0`.
   Save the kiwoomcli standard output as it is (UTF-8; on Windows set
   `PYTHONIOENCODING=utf-8` and redirect in cmd); a saved Kiwoom MCP response is
   read as well. `--pages 0` can fail with HTTP 429, so fetch at most 3 pages at
   a time and pause between requests. The ranges of the split files must overlap
   (the newest bar of each file is discarded).
   The first collection needs all pages back to 2026-04-01. Save each fetch as
   one cumulative file (a multi-page fetch stays one file): the newest bar of
   every file is ignored as possibly unfinished, so a fetch split into separate
   100-row files would lose the first bar of each older file. The folder name is
   the only binding between a file and its symbol; never put another symbol's
   file in it.
2. After the 30-minute bars, query the Kiwoom adjusted daily prices
   (`usa06012`, `adjusted=1`, read-only) of each symbol for the same period.
   If any row outside the page end carries an `upd_stkpc_tp` other than `"1f"`
   or a non-empty `upd_rt`, find the issuer's official announcement and add a
   record (previous section). The 0.5 / 2.0 guard cannot catch a small split
   such as 3:2, so this check is what covers it.
3. Build or extend the history. `--update` never changes an earlier close:

   ```powershell
   python manage-us-stock-strategy/scripts/regular_session_close_history.py build --symbol SOXX --exchange NASDAQ --pages-dir workspace/outputs/regular-session-closes/pages/SOXX --calendar <calendar artifact> --output workspace/outputs/regular-session-closes/history/SOXX.close-history.json --update
   ```

4. Reconcile the broker state with the cash-flow evidence (see
   [broker-snapshot-reconciliation.md](broker-snapshot-reconciliation.md) section 4).
5. Run the review and read the one-line summary:

   ```powershell
   python manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py
   ```

   Optional inputs: `--cards` with `--fact-pack` (only a card that passes
   `validate_holding_card.py` for the same session is used), `--earnings`,
   `--proposals`.
6. To show the line on cards, pass the result to
   `build_holding_fact_pack.py --exposure-review <file>`.

## Activation and journal entries

HWM, line breaches, pauses and instrument peaks are recomputed on every run
from the reconciliation ledger and the close histories (user decision P1). The
journal stores only what a person confirmed:

| Entry | When | Effect |
|---|---|---|
| `s5_activation` | once, after the first complete review | fixes the activation date and the rechecked starting HWM (closing-equity high from 2026-09-30 through activation, same close definition) |
| `line_review_completed` | after a line review | closes that line event; for L2 and below it releases the pause. Conclusion `continue` keeps the HWM |
| `peak_review_card_completed` | after the card rewrite | releases the add pause for that instrument |

```powershell
python manage-us-stock-strategy/scripts/portfolio_review_journal.py propose-activation --review <review file>
python manage-us-stock-strategy/scripts/portfolio_review_journal.py propose-line-review --review <review file> --line-id L2 --conclusion continue
python manage-us-stock-strategy/scripts/portfolio_review_journal.py propose-peak-review --review <review file> --symbol SOXL
python manage-us-stock-strategy/scripts/portfolio_review_journal.py apply --proposal <file> --confirm <code> --confirmed-via COWORK_CHAT_USER_MESSAGE --user-message "<the user's message>"
```

`apply` runs only in Cowork after the user sent "확인 <code>" for that proposal
in the current conversation, or from the user's own terminal
(`--confirmed-via USER_TERMINAL`). Claude Code, Codex, scheduled tasks and Judge
sessions never run it and never type or guess the code (`.claude/settings.json`
denies the command and direct edits of the journal file). Values in a proposal
are copied from the review; they are never typed by hand. Without an activation
entry the lines are not judged and R0 applies.

An activation can be proposed only from a review in which nothing but "not
activated yet" and "no journal yet" is open: every close used since 2026-09-30
is verified, the reconciliation is at most 4 days old, the state is confirmed
by a ledger entry, V is available, the session is the latest completed one and
all inputs are the production defaults. Otherwise the candidate is `NOT_READY`
with its reasons. Record the activation only after the close histories and the
cash-flow evidence routine are in place and the transaction-history wording
has been checked against real rows.

From the activation revision on, every state revision must be confirmed by a
reconciliation ledger entry. A state that changed without one (ledger missing
or not replayable) is not evaluated and R0 applies.

## Cash-flow declaration (R6)

1. Cowork saves the Kiwoom transaction history for the period since the last
   covered day (read-only CLI, `ust21100`) and sanitizes it:

   ```powershell
   python manage-us-stock-strategy/scripts/cash_flow_evidence.py normalize --raw <saved raw file> --from YYYY-MM-DD --to YYYY-MM-DD --output workspace/private_inputs/cash_flow_evidence/<name>.json
   ```

   The sanitized file never contains the account label. Delete the raw file
   after normalizing.
2. Deposits, withdrawals and currency exchanges are external flows. Dividends,
   fees, taxes and interest (deposit usage fee) are not, even when the memo also
   says deposit or withdrawal. A row that matches no keyword rule, or whose
   direction is unknown, makes the evidence unresolved (fail closed).
   - A Kiwoom "no data" response (message code 501724) is normalized as evidence with zero rows; any other non-zero
     return code still fails.
   - Par-value split/merge transfer rows and fractional-share cash rows (CORPORATE_ACTION) are not external flows.
     Quantity changes from splits are handled by the split record (corporate-actions.json) and the broker reconciliation.
3. The declaration is embedded in the reconciliation proposal. Coverage must be
   contiguous: the evidence starts no later than the day after the last covered
   day (activation date at first) and reaches the reconciliation date. Rows that
   an earlier, fully declared reconciliation already counted are not counted again.
4. Missing evidence, an undeclared or partly declared flow, or a coverage gap
   holds HWM and line evaluation from that reconciliation until a later one
   covers the period and declares it in full.
5. After a reconciliation that shows a smaller holding, line evaluation is on
   hold until a reconciliation with a later date confirms the cash (sale proceeds
   are not cash until then).

## Not in the first stage

- Retirement of cost-basis limits, timing slots, `weakness_10ema`, rearm (#1-#8, #13, #14).
- Instrument registry approvals (#12), `tactical_candidate_universe.json`.
- `timing_engine.py`, `evaluate_alerts.py`, `deployment_gate` hashes.
- K132-G report-only ledger (policy carries the settings only).
- Dashboard risk envelope; scheduled-task wiring.
