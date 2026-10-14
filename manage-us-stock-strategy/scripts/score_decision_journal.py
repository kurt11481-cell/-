#!/usr/bin/env python3
"""Score the card decisions in the decision journal (Cold Path, read only).

The journal (stock-strategy-system/decision_journal.json) is only READ here, through load_journal. Scores
are written to a new folder under workspace/outputs/journal-scores/ and never into the journal: the
journal holds what a person confirmed, a score is a recomputable view of it.

For every card_decision entry (the card's analysis action) and for the latest card_user_decision of that
decision (what the user actually did) the scorer reports, at 5, 20 and 60 U.S. sessions after the
start session:
  vs cash : ADD/HOLD  = stock return - 0 ; TRIM/EXIT = 0 - stock return
  vs SPY  : ADD/HOLD  = stock return - SPY return ; TRIM/EXIT = SPY return - stock return
Start session (score-fix 2026-10-12): the first session whose core close is strictly after the decision's
decision_as_of (the earliest close a LOC order could have used). A user decision starts at its effective
session when that session closes after decision_as_of, otherwise at the same first session. The move from
the decision session close to the start close is shown as pre_action_move and is not part of the score.
Auto-core order tickets (journal order_ticket entries and compare-mode tickets of the daily decision.json
files) are scored in ticket_results only, from the ticket session close: a hypothetical LOC fill (buy when
the close is at or below the ticket's cap, sell when at or above), vs no action, and the user's recorded
outcome. Hypothetical fills are evidence grade D (COUNTERFACTUAL_D), never a judgment basis.
Each ticket row also carries event_exposure (event_calendar.py): the official events of
docs/claude/event-calendar.json landing before the fill, overnight to the next close or within 5 sessions of the
ticket session's core close. It is classified ex post with the current calendar, is display and scoring only and
changes no score value; a missing or broken calendar is a status.
Rules (same point-in-time rule as the sidecar forward outcomes, which are not touched):
  - only finished sessions count: the target session's core close must be <= evaluation_as_of;
  - closes are the verified Kiwoom 30-minute-bar approximate closes of regular_session_close_history.
    A close with unverified reasons is labelled REFERENCE_ONLY;
  - SPY is outside the Kiwoom scope: its closes come from an optional reference file
    <closes_root>/reference-closes/SPY.json and are always labelled REFERENCE_ONLY;
  - corporate actions (splits) are applied from <closes_root>/corporate-actions.json; an invalid file or an
    unexplained jump in the window makes the result NOT_SCORABLE instead of a wrong number;
  - a failure is a status, never an exception: PENDING (with the sessions left), NOT_SCORABLE (with a reason).
No order, quantity or price target exists in the output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from corporate_actions import STATUS_INVALID, STATUS_OK, adjust_closes, applicable_actions
from event_calendar import DEFAULT_EVENT_CALENDAR, exposure, load_event_calendar
from portfolio_exposure import SPLIT_GUARD_HIGH, SPLIT_GUARD_LOW
from portfolio_review_journal import (
    DEFAULT_JOURNAL_PATH, JOURNAL_CARD_DECISION, JOURNAL_CARD_USER_DECISION, JOURNAL_ORDER_TICKET,
    JOURNAL_TICKET_OUTCOME, load_journal,
)
from validation_common import load_json, write_json

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
LOCALE_PATH = SKILL_ROOT / "assets/locales/portfolio-exposure-ko-KR.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "workspace/outputs/journal-scores"
DEFAULT_CLOSES_ROOT = REPO_ROOT / "workspace/outputs/regular-session-closes"
PROTECTED_OUTPUT_PARENTS = ("stock-strategy-system", "workspace/policies", "workspace/state")
REPORT_FILE = "journal-scores.json"
SCHEMA_VERSION = "journal-score-1.0"
REPORT_TYPE = "DECISION_JOURNAL_SCORES"
HORIZONS = (5, 20, 60)
BENCHMARK_SYMBOL = "SPY"
REFERENCE_CLOSES_DIR = "reference-closes"
REFERENCE_CLOSES_VERSION = "reference-closes-1.0"
MIN_SCORED_FOR_CONCLUSION = 30
LONG_ACTIONS = ("ADD", "HOLD")
REDUCE_ACTIONS = ("TRIM", "EXIT")
PRICE_SOURCE = "KIWOOM_30M_APPROX_CLOSE"
PLACES = Decimal("0.000001")
ZERO_TEXT = "0.000000"
START_FIRST_CLOSE = "FIRST_CLOSE_AFTER_DECISION"
START_EFFECTIVE = "EFFECTIVE_SESSION"
START_TICKET = "TICKET_SESSION_CLOSE"
# Auto-core decide output (kept here: this scorer imports no auto-core module).
DEFAULT_DECISIONS_ROOT = REPO_ROOT / "workspace/outputs/auto-core"
DECISION_FILE = "decision.json"
DAY_FOLDER = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
TICKET_SIGNS = {"buy": 1, "sell": -1}
TICKET_MODES = ("apply", "compare")
COUNTERFACTUAL_GRADE = "D"
COUNTERFACTUAL_LABEL = "COUNTERFACTUAL_D"
EVENT_CLASSIFICATION = "EX_POST_CURRENT_CALENDAR"
EVENT_LISTS = ("before_fill", "overnight", "within_5", "possible")


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() and number > 0 else None


def _text(number: Decimal) -> str:
    return format(number.quantize(PLACES, rounding=ROUND_HALF_EVEN), "f")


def _moment(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def load_reference_closes(closes_root: Path, symbol: str = BENCHMARK_SYMBOL) -> dict[str, Any]:
    """{status: MISSING|OK|INVALID, closes: {session: text}, errors: [...]} from reference-closes/<SYMBOL>.json."""
    path = Path(closes_root) / REFERENCE_CLOSES_DIR / f"{symbol}.json"
    if not path.is_file():
        return {"status": "MISSING", "closes": {}, "errors": []}
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"status": "INVALID", "closes": {}, "errors": ["REFERENCE_CLOSES_NOT_JSON"]}
    errors: list[str] = []
    if not isinstance(document, dict) or set(document) != {"schema_version", "symbol", "source_note", "closes"}:
        return {"status": "INVALID", "closes": {}, "errors": ["REFERENCE_CLOSES_KEYS"]}
    if document["schema_version"] != REFERENCE_CLOSES_VERSION or document["symbol"] != symbol:
        errors.append("REFERENCE_CLOSES_IDENTITY")
    if not isinstance(document["source_note"], str) or not document["source_note"].strip():
        errors.append("REFERENCE_CLOSES_SOURCE_NOTE")
    closes: dict[str, str] = {}
    raw = document["closes"]
    if not isinstance(raw, dict) or not raw:
        errors.append("REFERENCE_CLOSES_EMPTY")
    else:
        for session, value in raw.items():
            try:
                datetime.strptime(session, "%Y-%m-%d")
            except (TypeError, ValueError):
                errors.append(f"REFERENCE_CLOSES_DATE:{session}")
                continue
            if _decimal(value) is None:
                errors.append(f"REFERENCE_CLOSES_VALUE:{session}")
            else:
                closes[session] = str(value)
    if errors:
        return {"status": "INVALID", "closes": {}, "errors": errors[:5]}
    return {"status": "OK", "closes": closes, "errors": []}


def _split_suspect(closes: dict[str, str], window: list[str]) -> bool:
    """True when two consecutive sessions of the window jump like an unadjusted split."""
    previous: Decimal | None = None
    for session in window:
        current = _decimal(closes.get(session))
        if current is None:
            previous = None
            continue
        if previous is not None:
            ratio = current / previous
            if ratio <= Decimal(str(SPLIT_GUARD_LOW)) or ratio >= Decimal(str(SPLIT_GUARD_HIGH)):
                return True
        previous = current
    return False


def _not_scorable(horizon: int, reason: str, **extra: Any) -> dict[str, Any]:
    return {"horizon_sessions": horizon, "status": "NOT_SCORABLE", "reason": reason, **extra}


def _score_horizon(*, horizon: int, symbol: str, direction: str, start_session: str, sessions: list[str],
                   calendar_rows: dict[str, Any], completed: list[str], closes: dict[str, dict[str, str]],
                   unverified: dict[str, dict[str, list[str]]], benchmark: dict[str, Any],
                   evaluation_as_of: datetime) -> dict[str, Any]:
    index = sessions.index(start_session)
    if index + horizon >= len(sessions):
        return _not_scorable(horizon, "CALENDAR_DOES_NOT_COVER_HORIZON")
    target = sessions[index + horizon]
    target_closed = _moment(calendar_rows[target].get("core_close_at"))
    if target_closed is None:
        return _not_scorable(horizon, "CALENDAR_CLOSE_TIME_INVALID", target_session=target)
    if target_closed > evaluation_as_of:
        elapsed = sum(1 for session in completed if session > start_session)
        return {"horizon_sessions": horizon, "status": "PENDING", "target_session": target,
                "remaining_sessions": max(horizon - elapsed, 1)}
    per_symbol = closes.get(symbol)
    if per_symbol is None:
        return _not_scorable(horizon, f"CLOSE_HISTORY_MISSING:{symbol}", target_session=target)
    start_close, target_close = _decimal(per_symbol.get(start_session)), _decimal(per_symbol.get(target))
    if start_close is None:
        return _not_scorable(horizon, "START_CLOSE_MISSING", target_session=target)
    if target_close is None:
        return _not_scorable(horizon, "TARGET_CLOSE_MISSING", target_session=target)
    window = sessions[index:index + horizon + 1]
    if _split_suspect(per_symbol, window):
        return _not_scorable(horizon, "POSSIBLE_UNADJUSTED_SPLIT", target_session=target)
    reasons = sorted({reason for session in (start_session, target)
                      for reason in (unverified.get(symbol) or {}).get(session, [])})
    stock_return = target_close / start_close - 1
    sign = 1 if direction == "LONG" else -1
    result: dict[str, Any] = {
        "horizon_sessions": horizon, "status": "SCORED", "target_session": target,
        "observed_at": target_closed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "price_source": PRICE_SOURCE, "price_grade": "REFERENCE_ONLY" if reasons else "GRADE_B",
        "unverified_reasons": reasons, "stock_return": _text(stock_return),
        "vs_cash": _text(sign * stock_return),
    }
    spy_start, spy_target = _decimal(benchmark["closes"].get(start_session)), _decimal(benchmark["closes"].get(target))
    if benchmark["status"] != "OK":
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "BENCHMARK_UNAVAILABLE",
                                  "reason": f"REFERENCE_CLOSES_{benchmark['status']}"}
    elif spy_start is None or spy_target is None:
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "BENCHMARK_UNAVAILABLE",
                                  "reason": "BENCHMARK_CLOSE_MISSING"}
    elif _split_suspect(benchmark["closes"], window):
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "BENCHMARK_UNAVAILABLE",
                                  "reason": "POSSIBLE_UNADJUSTED_SPLIT"}
    else:
        benchmark_return = spy_target / spy_start - 1
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "OK", "label": "REFERENCE_ONLY",
                                  "benchmark_return": _text(benchmark_return),
                                  "value": _text(sign * (stock_return - benchmark_return))}
    return result


def _completed_sessions(calendar: dict[str, Any], evaluation_as_of: datetime) -> list[str]:
    """Sessions whose core close is at or before the evaluation time (the only closes that may be used)."""
    done = []
    for session in sorted(calendar["sessions"]):
        closed = _moment(calendar["sessions"][session].get("core_close_at"))
        if closed is not None and closed <= evaluation_as_of:
            done.append(session)
    return done


def _subjects(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One ANALYSIS subject per card_decision and one USER subject for the latest user decision of it."""
    latest_user: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if entry.get("entry_type") == JOURNAL_CARD_USER_DECISION:
            latest_user[entry["payload"]["decision_id"]] = entry  # a correction is a later entry: the last one wins
    subjects: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("entry_type") != JOURNAL_CARD_DECISION:
            continue
        payload = entry["payload"]
        subjects.append({
            "decision_id": payload["decision_id"], "kind": "ANALYSIS", "ticker": payload["ticker"],
            "action": payload["analysis_action"], "sidecar_action": payload["sidecar_action"],
            "conviction": payload["conviction"], "decision_session": payload["decision_session"],
            "decision_as_of": payload.get("decision_as_of"), "effective_session": None,
            "recorded_reference_close": payload["reference_close"], "sequence": entry["sequence"]})
        user = latest_user.get(payload["decision_id"])
        if user is not None:
            subjects.append({
                "decision_id": payload["decision_id"], "kind": "USER", "ticker": payload["ticker"],
                "action": user["payload"]["user_action"], "sidecar_action": None, "conviction": None,
                "decision_session": payload["decision_session"], "decision_as_of": payload.get("decision_as_of"),
                "effective_session": user["payload"]["effective_session"], "recorded_reference_close": None,
                "sequence": user["sequence"]})
    return subjects


def _first_close_after(moment: datetime, sessions: list[str],
                       calendar_rows: dict[str, Any]) -> tuple[str | None, str | None]:
    """(first session whose core close is strictly after moment, failure reason)."""
    for session in sessions:
        closed = _moment(calendar_rows[session].get("core_close_at"))
        if closed is None:
            return None, "CALENDAR_CLOSE_TIME_INVALID"
        if closed > moment:
            return session, None
    return None, "CALENDAR_DOES_NOT_COVER_START"


def _start(subject: dict[str, Any], sessions: list[str],
           calendar_rows: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """(start session, start basis, failure reason) of one card subject.

    ANALYSIS: the first session closing after decision_as_of. USER: its effective session when that session
    closes after decision_as_of, otherwise the same first session. The decision session must be in the calendar
    so a calendar that starts after the decision cannot move the start later."""
    decided = _moment(subject["decision_as_of"])
    if decided is None:
        return None, None, "DECISION_AS_OF_INVALID"
    if subject["decision_session"] not in calendar_rows:
        return None, None, "DECISION_SESSION_NOT_IN_CALENDAR"
    effective = subject["effective_session"]
    if effective is not None:
        if effective not in calendar_rows:
            return None, None, "DECISION_SESSION_NOT_IN_CALENDAR"
        closed = _moment(calendar_rows[effective].get("core_close_at"))
        if closed is None:
            return None, None, "CALENDAR_CLOSE_TIME_INVALID"
        if closed > decided:
            return effective, START_EFFECTIVE, None
    session, failure = _first_close_after(decided, sessions, calendar_rows)
    return session, (START_FIRST_CLOSE if session is not None else None), failure


def _pre_action_move(per_symbol: dict[str, str], sessions: list[str], completed: set[str],
                     decision_session: str, start_session: str) -> str | None:
    """Decision session close -> start close return; None when a close is missing, not yet final or split-like."""
    if decision_session not in completed or start_session not in completed:
        return None
    first, last = sessions.index(decision_session), sessions.index(start_session)
    if last < first:
        return None
    begin, end = _decimal(per_symbol.get(decision_session)), _decimal(per_symbol.get(start_session))
    if begin is None or end is None or _split_suspect(per_symbol, sessions[first:last + 1]):
        return None
    return _text(end / begin - 1)


def _journal_tickets(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """(recorded tickets, latest outcome payload by ticket id). Cap and size stay internal to the scorer."""
    tickets: list[dict[str, Any]] = []
    outcomes: dict[str, dict[str, Any]] = {}
    for entry in entries:
        payload = entry.get("payload") or {}
        if entry.get("entry_type") == JOURNAL_ORDER_TICKET:
            tickets.append({"ticket_id": payload.get("ticket_id"), "ticker": payload.get("ticker"),
                            "side": payload.get("side"), "mode": "apply", "session": payload.get("buy_session"),
                            "cap": payload.get("price"), "size": payload.get("qty"),
                            "risk_1r": payload.get("risk_1r"), "weak": payload.get("evidence_weak_kinds")})
        elif entry.get("entry_type") == JOURNAL_TICKET_OUTCOME:
            outcomes[payload.get("ticket_id")] = payload  # a later classification of the same ticket wins
    return tickets, outcomes


def _compare_tickets(records: list[dict[str, Any]], seen: set[Any]) -> tuple[list[dict[str, Any]], int]:
    """(compare-mode tickets not already recorded in the journal, duplicates skipped)."""
    tickets: list[dict[str, Any]] = []
    skipped = 0
    for record in records:
        if not isinstance(record, dict) or record.get("mode") != "compare":
            continue
        if record.get("ticket_id") in seen:
            skipped += 1
            continue
        seen.add(record.get("ticket_id"))
        evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
        tickets.append({"ticket_id": record.get("ticket_id"), "ticker": record.get("ticker"),
                        "side": record.get("side"), "mode": "compare", "session": record.get("session"),
                        "cap": record.get("price"), "size": record.get("qty"),
                        "risk_1r": record.get("risk_1r"), "weak": evidence.get("weak")})
    return tickets, skipped


def _ticket_risk_1r(value: Any) -> dict[str, Any] | None:
    """risk1r: the planned 1R recorded with the ticket (status, r_pct, r_sigma only), or None."""
    if not isinstance(value, dict):
        return None
    return {key: value.get(key) for key in ("status", "r_pct", "r_sigma")}


def _weak_kinds(value: Any) -> list[str] | None:
    return list(value) if isinstance(value, list) and all(isinstance(item, str) for item in value) else None


def _with_r_multiple(item: dict[str, Any], r_pct: Decimal | None, filled: bool) -> dict[str, Any]:
    """risk1r: r_multiple = vs_no_action / planned r_pct of a filled buy (hypothetical or the user's) with a 1R of
    status ok; null otherwise. vs_no_action is already a finished-session value, so nothing later is read."""
    value = item.get("vs_no_action") if item.get("status") == "SCORED" else None
    multiple = None
    if filled and r_pct is not None and value is not None:
        try:
            multiple = _text(Decimal(str(value)) / r_pct)
        except InvalidOperation:
            multiple = None
    return {**item, "r_multiple": multiple}


def _planned_r_pct(ticket: dict[str, Any]) -> Decimal | None:
    risk = ticket.get("risk_1r")
    if ticket.get("side") != "buy" or not isinstance(risk, dict) or risk.get("status") != "ok":
        return None
    return _decimal(risk.get("r_pct"))


def _ticket_horizon(item: dict[str, Any], would_fill: bool | None) -> dict[str, Any]:
    """A hypothetical LOC fill: filled = the side-signed return; not filled = no position change, 0."""
    if item["status"] != "SCORED" or would_fill is None:
        return item
    result = {key: value for key, value in item.items() if key != "vs_cash"}
    if would_fill:
        result["vs_no_action"] = item["vs_cash"]
    else:
        result.update({"vs_no_action": ZERO_TEXT, "reason": "NOT_FILLED_AT_CAP",
                       "vs_benchmark": {"symbol": BENCHMARK_SYMBOL, "status": "NOT_APPLICABLE",
                                        "reason": "NOT_FILLED_AT_CAP"}})
    return result


def _user_zero(item: dict[str, Any]) -> dict[str, Any]:
    if item["status"] != "SCORED":
        return item
    return {key: item[key] for key in ("horizon_sessions", "status", "target_session", "observed_at")} | {
        "vs_no_action": ZERO_TEXT}


def _user_filled(item: dict[str, Any], *, start: Decimal | None, sign: int, per_symbol: dict[str, str],
                 benchmark: dict[str, Any], session: str) -> dict[str, Any]:
    if item["status"] != "SCORED":
        return item
    target_close = _decimal(per_symbol.get(item["target_session"]))
    if start is None or target_close is None:
        return _not_scorable(item["horizon_sessions"], "START_CLOSE_MISSING", target_session=item["target_session"])
    stock_return = target_close / start - 1
    result = {key: item[key] for key in ("horizon_sessions", "status", "target_session", "observed_at",
                                         "price_source", "price_grade", "unverified_reasons")}
    result.update({"stock_return": _text(stock_return), "vs_no_action": _text(sign * stock_return)})
    if item["vs_benchmark"]["status"] == "OK":
        spy_return = (_decimal(benchmark["closes"].get(item["target_session"]))
                      / _decimal(benchmark["closes"].get(session)) - 1)
        result["vs_benchmark"] = {"symbol": BENCHMARK_SYMBOL, "status": "OK", "label": "REFERENCE_ONLY",
                                  "benchmark_return": _text(spy_return),
                                  "value": _text(sign * (stock_return - spy_return))}
    else:
        result["vs_benchmark"] = item["vs_benchmark"]
    return result


def _filled_fraction(outcome: dict[str, Any], size: Any) -> str | None:
    filled, total = outcome.get("filled_qty"), _decimal(size)
    if isinstance(filled, bool) or not isinstance(filled, int) or filled < 0 or total is None:
        return None
    return _text(Decimal(filled) / total)


def _user_result(ticket: dict[str, Any], outcome: dict[str, Any] | None, base: list[dict[str, Any]], *,
                 sign: int | None, raw_start: Decimal | None, per_symbol: dict[str, str],
                 benchmark: dict[str, Any]) -> dict[str, Any]:
    """What the user actually did with the ticket, from the journal's latest ticket_outcome only."""
    if ticket["mode"] == "compare":
        return {"state": "NOT_ENTERED_COMPARE_MODE"}
    if outcome is None:
        return {"state": "PENDING_OUTCOME"}
    state = outcome.get("outcome_state")
    if state == "changed":
        return {"state": state, "horizons": [_not_scorable(horizon, "USER_CHANGED_ORDER") for horizon in HORIZONS]}
    if state in ("unfilled", "not_entered"):
        return {"state": state, "horizons": [_user_zero(item) for item in base]}
    if state not in ("filled", "partial") or sign is None:
        return {"state": "NOT_SCORABLE",
                "horizons": [_not_scorable(horizon, "USER_OUTCOME_INVALID") for horizon in HORIZONS]}
    adjusted_start = _decimal(per_symbol.get(ticket["session"]))
    fill = _decimal(outcome.get("average_fill_price"))
    if fill is not None and adjusted_start is not None and raw_start is not None:
        start = fill * adjusted_start / raw_start  # the fill price on the same split basis as the later closes
    else:
        start = adjusted_start
    return {"state": state, "start_price_basis": "SESSION_CLOSE" if fill is None else "AVERAGE_FILL_PRICE",
            "filled_fraction": _filled_fraction(outcome, ticket["size"]),
            "horizons": [_user_filled(item, start=start, sign=sign, per_symbol=per_symbol, benchmark=benchmark,
                                      session=ticket["session"]) for item in base]}


def _score_ticket(ticket: dict[str, Any], outcome: dict[str, Any] | None, *, calendar: dict[str, Any] | None,
                  sessions: list[str], completed: list[str], raw: dict[str, dict[str, str]],
                  adjusted: dict[str, dict[str, str]], unverified: dict[str, dict[str, list[str]]],
                  benchmark: dict[str, Any], corporate_status: str, evaluation_as_of: datetime) -> dict[str, Any]:
    sign = TICKET_SIGNS.get(ticket["side"])
    session = ticket["session"]
    row: dict[str, Any] = {"ticket_id": ticket["ticket_id"], "ticker": ticket["ticker"], "side": ticket["side"],
                           "mode": ticket["mode"], "session": session, "start_basis": START_TICKET,
                           "evidence_grade": COUNTERFACTUAL_GRADE, "would_fill": None}
    failure = ("TICKET_SIDE_INVALID" if sign is None else
               "SESSION_CALENDAR_UNAVAILABLE" if calendar is None else
               "CORPORATE_ACTIONS_INVALID" if corporate_status == STATUS_INVALID else
               "TICKET_SESSION_NOT_IN_CALENDAR" if session not in calendar["sessions"] else
               "CALENDAR_CLOSE_TIME_INVALID" if _moment(calendar["sessions"][session].get("core_close_at")) is None
               else None)
    raw_start = _decimal((raw.get(ticket["ticker"]) or {}).get(session))
    per_symbol = adjusted.get(ticket["ticker"]) or {}
    if failure is not None:
        base = [_not_scorable(horizon, failure) for horizon in HORIZONS]
    else:
        base = [_score_horizon(horizon=horizon, symbol=ticket["ticker"], direction="LONG" if sign > 0 else "REDUCE",
                               start_session=session, sessions=sessions, calendar_rows=calendar["sessions"],
                               completed=completed, closes=adjusted, unverified=unverified, benchmark=benchmark,
                               evaluation_as_of=evaluation_as_of) for horizon in HORIZONS]
        cap = _decimal(ticket["cap"])
        if session in completed and raw_start is not None:
            if cap is None:
                base = [_not_scorable(horizon, "TICKET_CAP_INVALID") for horizon in HORIZONS]
            else:
                # The cap was set on the ticket session's own price basis, so the raw close is compared.
                row["would_fill"] = raw_start <= cap if sign > 0 else raw_start >= cap
    row["horizons"] = [_ticket_horizon(item, row["would_fill"]) for item in base]
    row["user"] = _user_result(ticket, outcome, base, sign=sign, raw_start=raw_start, per_symbol=per_symbol,
                               benchmark=benchmark)
    # risk1r: the planned 1R and evidence kinds as recorded, and the R multiple of each horizon.
    row["risk_1r"] = _ticket_risk_1r(ticket.get("risk_1r"))
    row["evidence_weak_kinds"] = _weak_kinds(ticket.get("weak"))
    r_pct = _planned_r_pct(ticket)
    row["horizons"] = [_with_r_multiple(item, r_pct, row["would_fill"] is True) for item in row["horizons"]]
    if "horizons" in row["user"]:
        user_filled = row["user"]["state"] in ("filled", "partial")
        row["user"] = {**row["user"], "horizons": [_with_r_multiple(item, r_pct, user_filled)
                                                   for item in row["user"]["horizons"]]}
    return row


def _ticket_earnings(ticket: dict[str, Any], decision_earnings: dict[str, Any] | None) -> Any:
    """The ticket symbol's own earnings record: a compare ticket from the decision.json it came from, a journal
    ticket from the decision.json holding the same ticket id, else the one with the same buy_session. None if absent."""
    if not isinstance(decision_earnings, dict) or not isinstance(ticket["ticket_id"], str):
        return None
    calendar = (decision_earnings.get("by_ticket") or {}).get(ticket["ticket_id"])
    if calendar is None and ticket["mode"] == "apply" and isinstance(ticket["session"], str):
        calendar = (decision_earnings.get("by_session") or {}).get(ticket["session"])
    return calendar.get(ticket["ticker"]) if isinstance(calendar, dict) and isinstance(ticket["ticker"], str) else None


def _event_exposure(ticket: dict[str, Any], *, calendar: dict[str, Any] | None,
                    event_calendar: dict[str, Any] | None, earnings: Any) -> dict[str, Any]:
    """Event ids by position against the ticket session's core close (ex post, display and scoring only)."""
    if calendar is None:
        status = "SESSION_CALENDAR_UNAVAILABLE"
    elif event_calendar is None or event_calendar.get("status") != "OK":
        status = ("EVENT_CALENDAR_INVALID" if (event_calendar or {}).get("status") == "INVALID"
                  else "EVENT_CALENDAR_MISSING")
    else:
        found = exposure(session=ticket["session"], sessions=calendar["sessions"], events=event_calendar["events"],
                         coverage_start=event_calendar["coverage_start"], horizon_end=event_calendar["horizon_end"],
                         earnings=earnings)
        return {"status": found["status"], **{key: found[key] for key in EVENT_LISTS},
                "own_earnings": found["own_earnings"]}
    return {"status": status, **{key: [] for key in EVENT_LISTS}, "own_earnings": None}


def _event_calendar_block(event_calendar: dict[str, Any] | None) -> dict[str, Any]:
    loaded = event_calendar or {"status": "MISSING", "reasons": ["EVENT_CALENDAR_NOT_SUPPLIED"]}
    return {"status": loaded.get("status"), "sha256": loaded.get("sha256"),
            "coverage_start": loaded.get("coverage_start"), "horizon_end": loaded.get("horizon_end"),
            "reasons": list(loaded.get("reasons") or []), "classification": EVENT_CLASSIFICATION}


def _ticket_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored_by_horizon = {str(horizon): sum(1 for row in rows for item in row["horizons"]
                                           if item["horizon_sessions"] == horizon and item["status"] == "SCORED")
                         for horizon in HORIZONS}
    best = max(scored_by_horizon.values(), default=0)
    return {
        "ticket_total": len(rows),
        "by_mode": {mode: sum(1 for row in rows if row["mode"] == mode) for mode in TICKET_MODES},
        "pending_tickets": sum(1 for row in rows if any(item["status"] == "PENDING" for item in row["horizons"])),
        "scored_by_horizon": scored_by_horizon,
        "min_scored_for_conclusion": MIN_SCORED_FOR_CONCLUSION,
        "conclusion_allowed": best >= MIN_SCORED_FOR_CONCLUSION,
        "label": COUNTERFACTUAL_LABEL,
        "risk_1r_ok": sum(1 for row in rows if (row.get("risk_1r") or {}).get("status") == "ok"),
        "event_exposure_ok": sum(1 for row in rows if row["event_exposure"]["status"] == "OK"),
        "event_overnight": sum(1 for row in rows if row["event_exposure"]["overnight"]),
    }


def score_journal(journal: dict[str, Any], *, calendar: dict[str, Any] | None, calendar_failure: str | None = None,
                  closes: dict[str, dict[str, str]], unverified: dict[str, dict[str, list[str]]],
                  benchmark: dict[str, Any], corporate_actions: dict[str, Any],
                  evaluation_as_of: datetime, ticket_records: list[dict[str, Any]] | None = None,
                  event_calendar: dict[str, Any] | None = None,
                  decision_earnings: dict[str, Any] | None = None) -> dict[str, Any]:
    """The score report. Pure: no file is read or written here.

    ticket_records: compare-mode tickets read by the caller from the daily decision.json files; a ticket id
    already recorded in the journal is scored once, from the journal.
    event_calendar: load_event_calendar output (None = not supplied); decision_earnings: the earnings_calendar of
    those decision.json files by ticket id and by buy_session. Both only feed event_exposure, never a score value."""
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "report_type": REPORT_TYPE,
        "evaluation_as_of": evaluation_as_of.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "journal": {"status": journal["status"], "entry_count": len(journal["entries"]),
                    "head_sha256": journal["head_sha256"], "errors": journal["errors"]},
        "calendar": ({"status": "LOADED", **calendar["identity"]} if calendar is not None
                     else {"status": "UNAVAILABLE", "reason": calendar_failure}),
        "corporate_actions": {"status": corporate_actions["status"], "sha256": corporate_actions.get("sha256"),
                              "errors": list(corporate_actions.get("errors") or [])},
        "benchmark": {"symbol": BENCHMARK_SYMBOL, "label": "REFERENCE_ONLY", "status": benchmark["status"],
                      "errors": list(benchmark.get("errors") or [])},
        "horizons": list(HORIZONS), "results": [],
        "ticket_results": [],
        "ticket_sources": {"journal_tickets": 0, "compare_tickets": 0, "duplicates_skipped": 0, "errors": []},
        "event_calendar": _event_calendar_block(event_calendar),
        "writes_journal": False, "order_authority": False, "quantity_authority": "none",
    }
    if journal["status"] == "CORRUPT":
        report["summary"] = _summary([])
        report["ticket_summary"] = _ticket_summary([])
        return report
    sessions = sorted(calendar["sessions"]) if calendar is not None else []
    completed = _completed_sessions(calendar, evaluation_as_of) if calendar is not None else []
    done = set(completed)
    adjusted = closes
    if calendar is not None and corporate_actions["status"] == STATUS_OK and completed:
        actions = applicable_actions(corporate_actions["actions"], completed[-1])
        adjusted = adjust_closes({**closes, BENCHMARK_SYMBOL: benchmark["closes"]}, actions)
        benchmark = {**benchmark, "closes": adjusted.pop(BENCHMARK_SYMBOL, benchmark["closes"])}
    for subject in _subjects(journal["entries"]):
        direction = ("LONG" if subject["action"] in LONG_ACTIONS else
                     "REDUCE" if subject["action"] in REDUCE_ACTIONS else None)
        row = {key: subject[key] for key in ("decision_id", "kind", "ticker", "action", "sidecar_action",
                                             "conviction", "decision_session", "sequence")}
        row["recorded_reference_close"] = subject["recorded_reference_close"]
        start, basis, failure = (_start(subject, sessions, calendar["sessions"]) if calendar is not None
                                 else (None, None, "SESSION_CALENDAR_UNAVAILABLE"))
        row.update({"start_session": start, "start_basis": basis, "pre_action_move": None})
        if direction is None:
            row["horizons"] = [_not_scorable(horizon, "USER_ACTION_NOT_SCORABLE") for horizon in HORIZONS]
        elif calendar is None:
            row["horizons"] = [_not_scorable(horizon, "SESSION_CALENDAR_UNAVAILABLE") for horizon in HORIZONS]
        elif corporate_actions["status"] == STATUS_INVALID:
            row["horizons"] = [_not_scorable(horizon, "CORPORATE_ACTIONS_INVALID") for horizon in HORIZONS]
        elif failure is not None:
            row["horizons"] = [_not_scorable(horizon, failure) for horizon in HORIZONS]
        else:
            row["horizons"] = [
                _score_horizon(horizon=horizon, symbol=subject["ticker"], direction=direction,
                               start_session=start, sessions=sessions,
                               calendar_rows=calendar["sessions"], completed=completed, closes=adjusted,
                               unverified=unverified, benchmark=benchmark, evaluation_as_of=evaluation_as_of)
                for horizon in HORIZONS]
            per_symbol = adjusted.get(subject["ticker"]) or {}
            row["pre_action_move"] = _pre_action_move(per_symbol, sessions, done, subject["decision_session"], start)
            # Same-session data check: the decision session close against the close recorded with the decision.
            decision_close = (_decimal(per_symbol.get(subject["decision_session"]))
                              if subject["decision_session"] in done else None)
            recorded = _decimal(subject["recorded_reference_close"])
            if decision_close is not None and recorded is not None:
                row["start_close_vs_recorded_reference"] = _text(decision_close - recorded)
        report["results"].append(row)
    report["summary"] = _summary(report["results"])
    tickets, outcomes = _journal_tickets(journal["entries"])
    compare, skipped = _compare_tickets(list(ticket_records or []), {ticket["ticket_id"] for ticket in tickets})
    report["ticket_sources"].update({"journal_tickets": len(tickets), "compare_tickets": len(compare),
                                     "duplicates_skipped": skipped})
    for ticket in tickets + compare:
        row = _score_ticket(
            ticket, outcomes.get(ticket["ticket_id"]) if ticket["mode"] == "apply" else None, calendar=calendar,
            sessions=sessions, completed=completed, raw=closes, adjusted=adjusted, unverified=unverified,
            benchmark=benchmark, corporate_status=corporate_actions["status"], evaluation_as_of=evaluation_as_of)
        row["event_exposure"] = _event_exposure(ticket, calendar=calendar, event_calendar=event_calendar,
                                                earnings=_ticket_earnings(ticket, decision_earnings))
        report["ticket_results"].append(row)
    report["ticket_summary"] = _ticket_summary(report["ticket_results"])
    return report


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    analysis = [row for row in results if row["kind"] == "ANALYSIS"]

    def statuses(row: dict[str, Any]) -> set[str]:
        return {item["status"] for item in row["horizons"]}

    scored_by_horizon = {str(horizon): sum(1 for row in analysis for item in row["horizons"]
                                           if item["horizon_sessions"] == horizon and item["status"] == "SCORED")
                         for horizon in HORIZONS}
    best = max(scored_by_horizon.values(), default=0)
    return {
        "decision_count": len(analysis),
        "pending_decisions": sum(1 for row in analysis if "PENDING" in statuses(row)),
        "fully_scored_decisions": sum(1 for row in analysis if statuses(row) == {"SCORED"}),
        "unscorable_decisions": sum(1 for row in analysis if "NOT_SCORABLE" in statuses(row)),
        "scored_by_horizon": scored_by_horizon,
        "min_scored_for_conclusion": MIN_SCORED_FOR_CONCLUSION,
        "conclusion_allowed": best >= MIN_SCORED_FOR_CONCLUSION,
    }


def _messages() -> dict[str, str]:
    return load_json(LOCALE_PATH)["messages"]


def _horizon_text(item: dict[str, Any], messages: dict[str, str]) -> str:
    horizon = item["horizon_sessions"]
    if item["status"] == "SCORED":
        benchmark = item["vs_benchmark"]
        spy = messages["score_vs_spy"].format(value=benchmark["value"]) if benchmark["status"] == "OK" \
            else messages["score_vs_spy_unavailable"]
        return messages["score_h_scored"].format(horizon=horizon, vs_cash=item["vs_cash"], spy=spy,
                                                 grade=item["price_grade"])
    if item["status"] == "PENDING":
        return messages["score_h_pending"].format(horizon=horizon, remaining=item["remaining_sessions"])
    return messages["score_h_unscorable"].format(horizon=horizon, reason=item["reason"])


def render_report(report: dict[str, Any]) -> list[str]:
    messages = _messages()
    if report["journal"]["status"] == "CORRUPT":
        return [messages["score_journal_unreadable"].format(reason=",".join(report["journal"]["errors"]))]
    summary = report["summary"]
    lines = [messages["score_summary"].format(
        total=summary["decision_count"], pending=summary["pending_decisions"],
        done=summary["fully_scored_decisions"], unscorable=summary["unscorable_decisions"])]
    for row in report["results"]:
        lines.append(messages["score_row"].format(
            ticker=row["ticker"], kind=row["kind"], action=row["action"],
            session=row["start_session"] or row["decision_session"],
            horizons=" / ".join(_horizon_text(item, messages) for item in row["horizons"])))
    if not summary["conclusion_allowed"]:
        lines.append(messages["score_no_conclusion"].format(
            minimum=summary["min_scored_for_conclusion"], best=max(summary["scored_by_horizon"].values())))
    lines.extend(_ticket_lines(report, messages))
    lines.append(messages["summary_no_order"])
    return lines


def _ticket_horizon_text(item: dict[str, Any], messages: dict[str, str]) -> str:
    if item["status"] != "SCORED":
        return _horizon_text(item, messages)
    benchmark = item["vs_benchmark"]
    spy = messages["score_vs_spy"].format(value=benchmark["value"]) if benchmark["status"] == "OK" \
        else messages["score_vs_spy_unavailable"]
    return messages["score_ticket_h_scored"].format(horizon=item["horizon_sessions"], value=item["vs_no_action"],
                                                    spy=spy)


def _ticket_lines(report: dict[str, Any], messages: dict[str, str]) -> list[str]:
    summary = report["ticket_summary"]
    lines = [messages["score_ticket_summary"].format(
        total=summary["ticket_total"], recorded=summary["by_mode"]["apply"], compare=summary["by_mode"]["compare"],
        scored=" / ".join(f"{horizon}:{count}" for horizon, count in summary["scored_by_horizon"].items()),
        minimum=summary["min_scored_for_conclusion"], errors=len(report["ticket_sources"]["errors"]))]
    event_status = (report.get("event_calendar") or {}).get("status")
    lines[0] += (messages["score_ticket_event_summary"].format(count=summary.get("event_overnight", 0))
                 if event_status == "OK" else messages["score_ticket_event_unavailable"].format(status=event_status))
    for row in report["ticket_results"]:
        line = messages["score_ticket_row"].format(
            ticker=row["ticker"], side=row["side"], mode=row["mode"], session=row["session"],
            fill="-" if row["would_fill"] is None else str(row["would_fill"]).lower(), user=row["user"]["state"],
            horizons=" / ".join(_ticket_horizon_text(item, messages) for item in row["horizons"]))
        risk = row.get("risk_1r") or {}
        if row["side"] == "buy" and risk.get("status") == "ok":
            line += messages["score_ticket_r_multiple"].format(r_pct=risk.get("r_pct"), values=" / ".join(
                f"{item['horizon_sessions']}:{item.get('r_multiple') or '-'}" for item in row["horizons"]))
        overnight = (row.get("event_exposure") or {}).get("overnight")
        if overnight:
            line += messages["score_ticket_event_overnight"].format(ids=",".join(overnight))
        lines.append(line)
    if report["ticket_results"]:
        lines.append(messages["score_ticket_reference_only"])
    return lines


def check_output_root(output_root: Path, journal_path: Path, repo_root: Path = REPO_ROOT) -> Path:
    """The only place scores may be written: never the journal, never state, policy or a parent of the journal."""
    root = Path(output_root).resolve()
    journal = Path(journal_path).resolve()
    if journal == root or journal.parent == root or root in journal.parents:
        raise ValueError("OUTPUT_ROOT_CONTAINS_JOURNAL")
    for protected in PROTECTED_OUTPUT_PARENTS:
        guarded = (Path(repo_root) / protected).resolve()
        if root == guarded or guarded in root.parents:
            raise ValueError("OUTPUT_ROOT_IN_PROTECTED_FOLDER")
    return root


def write_report(report: dict[str, Any], output_root: Path, journal_path: Path, now: datetime) -> Path:
    root = check_output_root(output_root, journal_path)
    directory = root / now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    index = 1
    while directory.exists():
        directory = root / f"{now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{index}"
        index += 1
    write_json(directory / REPORT_FILE, report)
    return directory / REPORT_FILE


def load_inputs(*, tickers: list[str], closes_root: Path, calendar_path: Path | None, now: datetime) -> dict[str, Any]:
    """Calendar, close histories, corporate actions and the SPY reference file. Failures stay statuses."""
    from run_portfolio_exposure_review import (  # noqa: PLC0415 - heavy imports only when scoring from files
        ReviewRunError, load_close_histories, load_corporate_actions, load_session_calendar,
    )

    calendar: dict[str, Any] | None = None
    failure: str | None = None
    try:
        calendar, _authority = load_session_calendar(calendar_path, now)
    except (ReviewRunError, OSError, ValueError) as exc:
        failure = str(exc) or type(exc).__name__
    closes: dict[str, dict[str, str]] = {}
    unverified: dict[str, dict[str, list[str]]] = {}
    histories: dict[str, Any] = {}
    corporate: dict[str, Any] = {"status": "MISSING", "sha256": None, "errors": [], "actions": []}
    if calendar is not None:
        closes, unverified, histories = load_close_histories(sorted(set(tickers)), closes_root, calendar)
        corporate = load_corporate_actions(closes_root, sorted(calendar["sessions"]))
    return {"calendar": calendar, "calendar_failure": failure, "closes": closes, "unverified": unverified,
            "close_histories": histories, "corporate_actions": corporate,
            "benchmark": load_reference_closes(closes_root)}


def load_compare_tickets(decisions_root: Path) -> dict[str, Any]:
    """Compare-mode tickets of every <YYYY-MM-DD>/decision.json under the auto-core output folder.

    decision.rerun-*.json files are not read. An unreadable file is skipped and named in errors (file name and
    reason only); it never stops the other files. earnings: the earnings_calendar of each file by ticket id (the
    first file holding that id) and by buy_session (the latest folder), for event_exposure only."""
    root = Path(decisions_root)
    earnings: dict[str, dict[str, Any]] = {"by_ticket": {}, "by_session": {}}
    if not root.is_dir():
        return {"status": "MISSING", "records": [], "errors": [], "earnings": earnings}
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in sorted(root.glob(f"*/{DECISION_FILE}")):
        if not DAY_FOLDER.fullmatch(path.parent.name):
            continue
        name = f"{path.parent.name}/{DECISION_FILE}"
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            errors.append({"file": name, "reason": "DECISION_NOT_JSON"})
            continue
        tickets = document.get("tickets") if isinstance(document, dict) else None
        if not isinstance(tickets, list):
            errors.append({"file": name, "reason": "DECISION_TICKETS_INVALID"})
            continue
        calendar = document.get("earnings_calendar")
        if isinstance(calendar, dict):
            if isinstance(document.get("buy_session"), str):
                earnings["by_session"][document["buy_session"]] = calendar
            for ticket in tickets:
                if isinstance(ticket, dict) and isinstance(ticket.get("ticket_id"), str):
                    earnings["by_ticket"].setdefault(ticket["ticket_id"], calendar)
        for ticket in tickets:
            if not isinstance(ticket, dict) or ticket.get("mode") != "compare":
                continue
            if not all(isinstance(ticket.get(key), str) and ticket.get(key)
                       for key in ("ticket_id", "ticker", "side", "session")):
                errors.append({"file": name, "reason": "TICKET_FIELDS_INVALID"})
                continue
            records.append(ticket)
    return {"status": "OK", "records": records, "errors": errors, "earnings": earnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the card decisions in the decision journal (read only)")
    parser.add_argument("--journal", type=Path, default=REPO_ROOT / DEFAULT_JOURNAL_PATH)
    parser.add_argument("--closes-root", type=Path, default=DEFAULT_CLOSES_ROOT)
    parser.add_argument("--calendar", type=Path, default=None, help="explicit session calendar artifact (labelled if not active)")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--evaluation-as-of", default=None, help="ISO time with offset; default now")
    parser.add_argument("--decisions-root", type=Path, default=DEFAULT_DECISIONS_ROOT,
                        help="auto-core output folder holding <YYYY-MM-DD>/decision.json (compare-mode tickets)")
    parser.add_argument("--event-calendar", type=Path, default=DEFAULT_EVENT_CALENDAR,
                        help="official event calendar (event exposure per ticket, display and scoring only)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    now = datetime.now(timezone.utc)
    evaluation_as_of = _moment(args.evaluation_as_of) if args.evaluation_as_of else now
    messages = _messages()
    if evaluation_as_of is None:
        print(messages["score_journal_unreadable"].format(reason="EVALUATION_AS_OF_INVALID"))
        return 2
    try:
        check_output_root(args.output_root, args.journal)
    except ValueError as exc:
        print(messages["score_journal_unreadable"].format(reason=str(exc)))
        return 2
    journal = load_journal(args.journal)
    compare = load_compare_tickets(args.decisions_root) if journal["status"] != "CORRUPT" else {
        "status": "NOT_READ", "records": [], "errors": [], "earnings": None}
    tickers = [entry["payload"]["ticker"] for entry in journal["entries"]
               if entry.get("entry_type") in (JOURNAL_CARD_DECISION, JOURNAL_ORDER_TICKET)]
    tickers += [record["ticker"] for record in compare["records"]]
    inputs = load_inputs(tickers=tickers, closes_root=args.closes_root, calendar_path=args.calendar,
                         now=evaluation_as_of) if journal["status"] == "OK" or (
        journal["status"] == "MISSING" and compare["records"]) else {
        "calendar": None, "calendar_failure": None, "closes": {}, "unverified": {}, "close_histories": {},
        "corporate_actions": {"status": "MISSING", "sha256": None, "errors": [], "actions": []},
        "benchmark": {"status": "MISSING", "closes": {}, "errors": []}}
    report = score_journal(journal, evaluation_as_of=evaluation_as_of, ticket_records=compare["records"],
                           event_calendar=load_event_calendar(args.event_calendar),
                           decision_earnings=compare.get("earnings"), **{
        key: inputs[key] for key in ("calendar", "calendar_failure", "closes", "unverified", "benchmark",
                                     "corporate_actions")})
    report["ticket_sources"].update({"decisions_root_status": compare["status"], "errors": compare["errors"]})
    report["close_histories"] = inputs["close_histories"]
    path = write_report(report, args.output_root, args.journal, now)
    print("\n".join(render_report(report)))
    print(messages["score_path"].format(path=str(path)))
    return 2 if journal["status"] == "CORRUPT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
