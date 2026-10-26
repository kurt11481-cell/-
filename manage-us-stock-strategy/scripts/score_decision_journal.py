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
  - SPY closes come from an optional reference file <closes_root>/reference-closes/SPY.json; only when that file
    is absent, from the auto-core history/SPY.close-history.json (verified sessions only, source
    KIWOOM_CLOSE_HISTORY). They are always labelled REFERENCE_ONLY;
  - corporate actions (splits) are applied from <closes_root>/corporate-actions.json; an invalid file or an
    unexplained jump in the window makes the result NOT_SCORABLE instead of a wrong number;
  - a failure is a status, never an exception: PENDING (with the sessions left), NOT_SCORABLE (with a reason).
No order, quantity or price target exists in the output.
--learning (f-evo-loop step 1, opt-in) adds a display-only grade D learning block; without it the report is unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
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
BENCHMARK_HISTORY_SOURCE = "KIWOOM_CLOSE_HISTORY"
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


def load_benchmark_closes(closes_root: Path, calendar: dict[str, Any] | None, load_close_histories: Any,
                          symbol: str = BENCHMARK_SYMBOL) -> dict[str, Any]:
    """Benchmark closes: reference-closes/<SYMBOL>.json wins unchanged; only when that file is absent the
    auto-core history/<SYMBOL>.close-history.json is read through load_close_histories (same checks as the
    stock closes). A failed history, or a session it marks unverified, gives no benchmark close (fail closed)."""
    reference = load_reference_closes(closes_root, symbol)
    if reference["status"] != "MISSING" or calendar is None:
        return reference
    closes, unverified, report = load_close_histories([symbol], closes_root, calendar)
    entry = report.get(symbol) or {"status": "MISSING"}
    if entry["status"] == "MISSING":
        return reference
    if entry["status"] != "OK":
        return {"status": "INVALID", "closes": {}, "errors": list(entry.get("errors") or [])[:5],
                "source": BENCHMARK_HISTORY_SOURCE}
    skipped = unverified.get(symbol) or {}
    verified = {session: value for session, value in (closes.get(symbol) or {}).items()
                if session not in skipped and _decimal(value) is not None}
    if not verified:
        return {"status": "INVALID", "closes": {}, "errors": ["CLOSE_HISTORY_NO_VERIFIED_SESSIONS"],
                "source": BENCHMARK_HISTORY_SOURCE}
    return {"status": "OK", "closes": verified, "errors": [], "source": BENCHMARK_HISTORY_SOURCE}


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
                      "errors": list(benchmark.get("errors") or []),
                      **({"source": benchmark["source"]} if "source" in benchmark else {})},
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
            "benchmark": load_benchmark_closes(closes_root, calendar, load_close_histories)}


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


# ---------------------------------------------------------------------------------------------
# Learning block (opt-in --learning; f-evo-loop step 1). Definitions: sections 3 and 4 of
# docs/claude/f-evo-loop-s1-preregistration-2026-10-16.md. Display only, grade D: counterfactual values of what the
# auto-core held back, never a rule, policy or ticket input. The default run (no --learning, the call the auto-core
# makes) never reaches this code. Only the decision.json files, their S7 reviews, closes and the two docs files
# (failure museum, rule epochs) are read; nothing is written outside the report.
# ---------------------------------------------------------------------------------------------

LEARNING_SCHEMA = "journal-learning-1.0"
PREREGISTRATION = {"id": "f-evo-loop-s1-preregistration-2026-10-16",
                   "sha256": "cd3709820e2d16d6d941679327783a0fa73356e8600cea6589d610830b183d53"}
GATE_HORIZONS = (5, 20, 60)
GATE_PRIMARY = 20
PATH_SESSIONS = 20
FLOOR_HORIZONS = (1, 5, 20)
FLOOR_PRIMARY = 5
NEXT_FILL_WINDOW = 5
BAND_RETURNS = 60
BAND_HORIZON = 5
BAND_UP = 0.9
BAND_DOWN = 0.1
BAND_PRIMARY = 5
TRIGGER_HORIZONS = (5, 20, 60)
TRIGGER_PRIMARY = 20
TAIL_SHARE = Decimal("0.2")
COVERAGE_MAX_UNSCORABLE = Decimal("0.1")
MUSEUM_HORIZON = 20
REQ_LABELS = ("REQ1_EARNINGS", "REQ2_EXPOSURE_CASH_PRODUCT", "REQ3_EVIDENCE", "REQ4_M6", "REQ5_RREC1")
REQ5_GATE = "REQ5_RREC1"
REQ5_UNK_GATE = "REQ5_RREC1_UNK"
RESEARCH_GATE = "RESEARCH_RECORD_NOT_OK"
REQUIREMENT_CELLS = 6
DECISION_REQUIRED_KEYS = ("blocked", "candidates", "buy_requirements", "evidence", "symbols", "shock", "buy_session")
DECISION_DAY_FIRST_KEYS = ("first_sha256", "first_generated_at", "first_evaluation_session", "first_buy_session")
S7_PATH_PREFIX = "workspace/outputs/auto-core/"
RREC1_DISPLAY_KEYS = ("SYMBOL_ONLY", "UNKNOWN", "NONE")
DEFAULT_MUSEUM_PATH = REPO_ROOT / "docs/claude/failure-museum.json"
DEFAULT_EPOCHS_PATH = REPO_ROOT / "docs/claude/gate-rule-epochs.json"
MUSEUM_SCHEMA = "failure-museum-1.0"
EPOCHS_SCHEMA = "gate-rule-epochs-1.0"
MUSEUM_CATEGORIES = ("THESIS", "EVIDENCE", "TIMING", "SIZE", "DATA", "RULE", "TAIL_EVENT", "NONE")
LEARNING_FAILED = "LEARNING_FAILED"
REPORT_FOLDER = re.compile(r"([0-9]{8}T[0-9]{6}Z)(?:-([0-9]+))?")
TICKET_DAY = re.compile(r"AT-([0-9]{4})([0-9]{2})([0-9]{2})-")
KST_ZONE = timezone(timedelta(hours=9))
NO_BENCHMARK = {"status": "MISSING", "closes": {}, "errors": []}
BUCKET_PRIMARY = {"GATE": GATE_PRIMARY, "GATE_RREC1_UNIT": GATE_PRIMARY, "SELL_FLOOR": FLOOR_PRIMARY,
                  "SCENARIO_BAND": BAND_PRIMARY, "TRIGGER_KIND": TRIGGER_PRIMARY}
SHOWN_FINDINGS = ("COST", "PROTECT", "STRONG", "WEAK", "DOWN_TAIL_UNDERSTATED", "UP_TAIL_UNDERSTATED")
# Screen lines of the learning block (kept here, not in the locale file).
LEARNING_MESSAGES = {
    "days": "[\U0000d559\U0000c2b5 \U0000cc44\U0000c810] \U0000acb0\U0000c815 \U0000b0a0\U0000c9dc {total}\U0000c77c"
            " \U000000b7 \U0000c790\U0000aca9 {eligible} \U000000b7 \U0000c81c\U0000c678 {excluded} \U000000b7 "
            "\U0000bcf4\U0000c874 \U0000ae68\U0000c9d0 {broken} (\U0000d45c\U0000c2dc \U0000c804\U0000c6a9 D)",
    "buckets": "[\U0000d559\U0000c2b5 \U0000cc44\U0000c810] \U0000bc84\U0000d0b7 {buckets}\U0000ac1c \U000000b7 "
               "\U0000acb0\U0000b860 \U0000d5c8\U0000c6a9 {allowed}\U0000ac1c (\U0000b3c5\U0000b9bd "
               "\U0000b2e8\U0000c704 {minimum}\U0000ac74 \U0000ae30\U0000c900)",
    "finding": "[\U0000d559\U0000c2b5 \U0000bc1c\U0000acac] {family} {key} {finding} \U000000b7 n {n} \U000000b7 "
               "\U0000d3c9\U0000ade0 {mean} \U000000b7 \U0000c911\U0000c559\U0000ac12 {median} \U00002014 "
               "\U0000d45c\U0000c2dc \U0000c804\U0000c6a9 D \U00002014 \U0000addc\U0000ce59 \U0000bcc0\U0000acbd "
               "\U0000adfc\U0000ac70 \U0000c544\U0000b2d8",
    "museum": "[Failure Museum] {status} \U000000b7 \U0000d6c4\U0000bcf4 {candidates} \U000000b7 "
              "\U0000cc44\U0000c6c0 {filled} \U000000b7 \U0000b300\U0000ae30 {pending}",
    "errors": "[\U0000d559\U0000c2b5 \U0000cc44\U0000c810] \U0000c624\U0000b958 {count}\U0000ac74: {reasons}",
    "failed": "[\U0000d559\U0000c2b5 \U0000cc44\U0000c810] \U0000c2e4\U0000d328 {reason} \U00002014 "
              "\U0000ae30\U0000c874 \U0000cc44\U0000c810 \U0000acb0\U0000acfc\U0000b294 \U0000adf8\U0000b300\U0000b85c",
}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _kst_day(value: Any) -> str | None:
    moment = value if isinstance(value, datetime) else _moment(value)
    return moment.astimezone(KST_ZONE).date().isoformat() if moment is not None else None


def _iso_day(value: Any) -> bool:
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _learning_failed(learning: Any) -> bool:
    """True for a learning block that failed as a whole (its errors carry a LEARNING_FAILED reason)."""
    return any(isinstance(item, dict) and str(item.get("reason") or "").startswith(LEARNING_FAILED)
               for item in (_dict(learning).get("errors") or []))


def load_decision_days(decisions_root: Path) -> dict[str, Any]:
    """Every <YYYY-MM-DD>/decision.json (decision.rerun-* are not read) with the sha256 of its raw bytes.

    A file that cannot be read keeps its day with an error (DECISION_UNREADABLE without a hash, DECISION_NOT_JSON with
    the hash of the bytes read); it never stops the other days."""
    root = Path(decisions_root)
    if not root.is_dir():
        return {"status": "MISSING", "days": []}
    days: list[dict[str, Any]] = []
    for path in sorted(root.glob(f"*/{DECISION_FILE}")):
        if not DAY_FOLDER.fullmatch(path.parent.name):
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            days.append({"day": path.parent.name, "sha256": None, "error": "DECISION_UNREADABLE"})
            continue
        digest = hashlib.sha256(raw).hexdigest()
        try:
            document = json.loads(raw.decode("utf-8-sig"))
        except ValueError:
            days.append({"day": path.parent.name, "sha256": digest, "error": "DECISION_NOT_JSON"})
            continue
        days.append({"day": path.parent.name, "sha256": digest, "document": document})
    return {"status": "OK", "days": days}


def load_s7_reduce(document: Any, decisions_root: Path) -> dict[str, Any]:
    """{status: OK|S7_PATH_OUTSIDE|S7_REVIEW_UNREADABLE, reduce: [symbols]} of a decision's own S7 review file.

    The recorded path is repository-relative; its workspace/outputs/auto-core/ prefix is dropped and the rest is
    resolved under decisions_root. A path that resolves outside decisions_root is not read."""
    record = _dict(_dict(_dict(document).get("inputs")).get("s7_review"))
    text = record.get("path")
    if not isinstance(text, str) or not text.strip():
        return {"status": "S7_REVIEW_UNREADABLE", "reduce": []}
    text = text.replace("\\", "/")
    if text.startswith(S7_PATH_PREFIX):
        text = text[len(S7_PATH_PREFIX):]
    root = Path(decisions_root).resolve()
    target = (root / text).resolve()
    if root not in target.parents:
        return {"status": "S7_PATH_OUTSIDE", "reduce": []}
    try:
        review = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"status": "S7_REVIEW_UNREADABLE", "reduce": []}
    items = _dict(_dict(review).get("recommendations")).get("reduce")
    if not isinstance(items, list):
        return {"status": "S7_REVIEW_UNREADABLE", "reduce": []}
    return {"status": "OK", "reduce": sorted({item["symbol"] for item in items
                                              if isinstance(item, dict) and isinstance(item.get("symbol"), str)})}


def load_learning_document(path: Path, schema: str, list_key: str) -> dict[str, Any]:
    """{status: OK|MISSING|INVALID, document, errors} of a docs file the learning block reads (never writes)."""
    target = Path(path)
    if not target.is_file():
        return {"status": "MISSING", "document": None, "errors": []}
    try:
        document = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"status": "INVALID", "document": None, "errors": ["NOT_JSON"]}
    if not isinstance(document, dict) or document.get("schema") != schema or not isinstance(document.get(list_key), list):
        return {"status": "INVALID", "document": None, "errors": ["SHAPE_INVALID"]}
    return {"status": "OK", "document": document, "errors": []}


def _folder_order(name: str) -> tuple[str, int]:
    match = REPORT_FOLDER.fullmatch(name)
    return (match.group(1), int(match.group(2) or 0)) if match else ("", 0)


def find_previous_learning(output_root: Path) -> dict[str, Any] | None:
    """The latest earlier report with a usable learning block: {path, decision_days}, or None.

    A report whose learning block failed as a whole (LEARNING_FAILED) is skipped, so the preservation marks of the
    last good block are carried on; an unreadable report is skipped too."""
    root = Path(output_root)
    if not root.is_dir():
        return None
    folders = sorted((path for path in root.iterdir() if path.is_dir() and REPORT_FOLDER.fullmatch(path.name)),
                     key=lambda path: _folder_order(path.name), reverse=True)
    for folder in folders:
        try:
            document = json.loads((folder / REPORT_FILE).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        learning = _dict(document).get("learning")
        if not isinstance(learning, dict) or _learning_failed(learning):
            continue
        days = learning.get("decision_days")
        if not isinstance(days, list):
            continue
        return {"path": folder.name,
                "decision_days": [row for row in days if isinstance(row, dict) and isinstance(row.get("day"), str)]}
    return None


# --- decision days, preservation marks ---------------------------------------------------------------------------

def _plan_shape_reason(document: dict[str, Any]) -> str | None:
    """PLAN_NOT_RUN for an empty decision frame, DECISION_SHAPE_UNKNOWN for an unexpected shape, else None."""
    if any(key not in document for key in DECISION_REQUIRED_KEYS):
        return "DECISION_SHAPE_UNKNOWN"
    if document.get("evaluation_session") is None or document.get("buy_session") is None \
            or not document.get("symbols") or not document.get("buy_requirements"):
        return "PLAN_NOT_RUN"
    if not (isinstance(document["evaluation_session"], str) and isinstance(document["buy_session"], str)
            and isinstance(document["symbols"], dict) and isinstance(document["evidence"], dict)
            and isinstance(document["shock"], dict) and isinstance(document["blocked"], list)
            and isinstance(document["candidates"], list) and isinstance(document["buy_requirements"], list)):
        return "DECISION_SHAPE_UNKNOWN"
    for row in document["buy_requirements"]:
        cells = _dict(row).get("c")
        if not isinstance(_dict(row).get("code"), str) or not isinstance(cells, list) \
                or len(cells) != REQUIREMENT_CELLS or not all(isinstance(_dict(cell).get("s"), str) for cell in cells):
            return "DECISION_SHAPE_UNKNOWN"
    for item in document["blocked"]:
        if not isinstance(_dict(item).get("symbol"), str) or not isinstance(_dict(item).get("reasons"), list):
            return "DECISION_SHAPE_UNKNOWN"
    if not all(isinstance(item, dict) for item in document["candidates"]):
        return "DECISION_SHAPE_UNKNOWN"
    return None


def _eligibility(item: dict[str, Any]) -> str | None:
    if "error" in item:
        return item["error"]
    document = item.get("document")
    if not isinstance(document, dict):
        return "DECISION_SHAPE_UNKNOWN"
    if document.get("status") not in ("OK", "HOLD"):
        return f"STATUS_{document.get('status')}"
    if document.get("no_new_session") is True:
        return "NO_NEW_SESSION"
    if document.get("carried_from") is not None:
        return "CARRIED_FROM"
    return _plan_shape_reason(document)


def _day_row(item: dict[str, Any], previous: dict[str, Any] | None, as_of_day: str | None) -> dict[str, Any]:
    day = item["day"]
    document = _dict(item.get("document"))
    readable = "document" in item
    row: dict[str, Any] = {
        "day": day, "evaluation_session": document.get("evaluation_session"), "buy_session": document.get("buy_session"),
        "status": document.get("status"), "commit_sha": document.get("commit_sha"),
        "generated_at": document.get("generated_at"), "eligible": False, "exclude_reason": None,
        "sha256": item.get("sha256")}
    flags = list((previous or {}).get("flags") or [])
    history = list((previous or {}).get("flag_history") or [])
    first = ({key: previous.get(key) for key in DECISION_DAY_FIRST_KEYS}
             if previous is not None and previous.get("first_sha256") else None)
    digest = item.get("sha256")
    if first is None:
        # A file that was not read as JSON never becomes the first hash.
        first = ({"first_sha256": digest, "first_generated_at": row["generated_at"],
                  "first_evaluation_session": row["evaluation_session"], "first_buy_session": row["buy_session"]}
                 if readable else {key: None for key in DECISION_DAY_FIRST_KEYS})
    elif digest is not None and digest != first["first_sha256"]:
        returned = (previous or {}).get("exclude_reason") == "MISSING_NOW"
        same_run_day = (readable and not returned and _kst_day(row["generated_at"]) == day
                        and row["evaluation_session"] == first["first_evaluation_session"]
                        and row["buy_session"] == first["first_buy_session"])
        flag = "REWRITTEN" if same_run_day else "PRESERVATION_BROKEN"
        if flag not in flags or digest != (previous or {}).get("sha256"):
            history.append({"as_of": as_of_day, "event": flag, "sha256": digest})
        if flag not in flags:
            flags.append(flag)
    elif digest is not None and (previous or {}).get("exclude_reason") == "MISSING_NOW":
        history.append({"as_of": as_of_day, "event": "RETURNED", "sha256": digest})
    reason = _eligibility(item)
    if reason is None and "PRESERVATION_BROKEN" in flags:
        reason = "PRESERVATION_BROKEN"
    row.update(eligible=reason is None, exclude_reason=reason, **first, flags=flags, flag_history=history)
    return row


def _missing_row(previous: dict[str, Any], as_of_day: str | None) -> dict[str, Any]:
    """A day of the earlier block whose file is gone: kept as it was, not eligible this week only."""
    history = list(previous.get("flag_history") or [])
    if previous.get("exclude_reason") != "MISSING_NOW":
        history.append({"as_of": as_of_day, "event": "MISSING_NOW", "sha256": None})
    return {**previous, "eligible": False, "exclude_reason": "MISSING_NOW", "flag_history": history}


def _decision_rows(decision_days: list[dict[str, Any]], previous_days: list[dict[str, Any]] | None,
                   root_status: str, as_of_day: str | None
                   ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """(decision_days rows, eligible documents by day, errors)."""
    previous = {row["day"]: row for row in previous_days or []}
    errors = [{"reason": item["error"], "file": f"{item['day']}/{DECISION_FILE}"}
              for item in decision_days if "error" in item]
    if root_status != "OK" and not previous:
        errors.append({"reason": "DECISIONS_ROOT_MISSING", "decisions_root_status": root_status})
    if previous and not any("document" in item for item in decision_days):
        # A folder that could not be read at all this week changes no mark: the earlier rows stay as they were.
        errors.append({"reason": "DECISIONS_ROOT_UNREADABLE", "decisions_root_status": root_status})
        return [dict(previous[day]) for day in sorted(previous)], {}, errors
    rows: dict[str, dict[str, Any]] = {}
    documents: dict[str, dict[str, Any]] = {}
    for item in decision_days:
        row = _day_row(item, previous.get(item["day"]), as_of_day)
        rows[item["day"]] = row
        if row["eligible"]:
            documents[item["day"]] = item["document"]
    for day, row in previous.items():
        if day not in rows:
            rows[day] = _missing_row(row, as_of_day)
    by_session: dict[str, list[str]] = {}
    for day in sorted(documents):
        by_session.setdefault(documents[day]["evaluation_session"], []).append(day)
    for days in by_session.values():
        for day in days[:-1]:  # the same evaluation session twice: only the later run day counts
            rows[day].update(eligible=False, exclude_reason="DUPLICATE_SESSION")
            documents.pop(day)
    return [rows[day] for day in sorted(rows)], documents, errors


# --- epochs --------------------------------------------------------------------------------------------------------

def _epoch_context(loaded: dict[str, Any]) -> dict[str, Any]:
    if loaded.get("status") != "OK":
        return {"status": loaded.get("status") or "MISSING", "entries": []}
    entries = []
    for entry in loaded["document"]["epochs"]:
        scope = _dict(entry).get("scope")
        valid_scope = scope in ("ALL", "EVIDENCE_BUY", "EVIDENCE_SELL") or (
            isinstance(scope, str) and scope.startswith("GATE:") and len(scope) > len("GATE:"))
        if not valid_scope or not _iso_day(_dict(entry).get("first_run_day")):
            return {"status": "INVALID", "entries": []}  # one bad line: no epoch at all (fail closed)
        entries.append({"scope": scope, "first_run_day": entry["first_run_day"]})
    return {"status": "OK", "entries": entries}


def _epoch_applies(scope: str, side: str, gates: list[str], extra: str | None) -> bool:
    if scope == "ALL" or scope == f"EVIDENCE_{str(side).upper()}":
        return True
    if scope.startswith("GATE:"):
        name = scope[len("GATE:"):]
        return name == extra or any(gate in (name, name + "_UNK") for gate in gates)
    return False


def _epoch(context: dict[str, Any], side: str, gates: list[str], extra: str | None, day: str | None) -> int | None:
    """Number of epoch entries for this unit whose first_run_day is on or before day (None without epochs or day)."""
    if context["status"] != "OK" or day is None:
        return None
    return sum(1 for entry in context["entries"]
               if _epoch_applies(entry["scope"], side, gates, extra) and entry["first_run_day"] <= day)


# --- values --------------------------------------------------------------------------------------------------------

def _learning_env(calendar: dict[str, Any] | None, closes: dict[str, dict[str, str]],
                  unverified: dict[str, dict[str, list[str]]], corporate_actions: dict[str, Any],
                  evaluation_as_of: datetime) -> dict[str, Any]:
    """Calendar, finished sessions and split-adjusted closes, the same way score_journal derives them."""
    if calendar is None:
        return {"failure": "SESSION_CALENDAR_UNAVAILABLE", "sessions": [], "order": {}, "rows": {}, "completed": [],
                "adjusted": {}, "unverified": {}, "as_of": evaluation_as_of}
    sessions = sorted(calendar["sessions"])
    completed = _completed_sessions(calendar, evaluation_as_of)
    adjusted = closes
    if corporate_actions.get("status") == STATUS_OK and completed:
        adjusted = adjust_closes(dict(closes), applicable_actions(corporate_actions["actions"], completed[-1]))
    return {"failure": "CORPORATE_ACTIONS_INVALID" if corporate_actions.get("status") == STATUS_INVALID else None,
            "sessions": sessions, "order": {session: index for index, session in enumerate(sessions)},
            "rows": calendar["sessions"], "completed": completed, "adjusted": adjusted, "unverified": unverified,
            "as_of": evaluation_as_of}


def _gap(env: dict[str, Any], earlier: Any, later: Any) -> int | None:
    order = env["order"]
    return order[later] - order[earlier] if earlier in order and later in order else None


def _cf(env: dict[str, Any], horizon: int, symbol: Any, side: Any, start: Any) -> dict[str, Any]:
    """cf_value = the held-back action's return (buy r, sell -r): _score_horizon's vs_cash. Never raises."""
    direction = {"buy": "LONG", "sell": "REDUCE"}.get(side)
    if env["failure"] is not None:
        return _not_scorable(horizon, env["failure"])
    if direction is None or not isinstance(symbol, str):
        return _not_scorable(horizon, "UNIT_SIDE_OR_SYMBOL_INVALID")
    if not isinstance(start, str) or start not in env["order"]:
        return _not_scorable(horizon, "START_SESSION_NOT_IN_CALENDAR")
    item = _score_horizon(horizon=horizon, symbol=symbol, direction=direction, start_session=start,
                          sessions=env["sessions"], calendar_rows=env["rows"], completed=env["completed"],
                          closes=env["adjusted"], unverified=env["unverified"], benchmark=NO_BENCHMARK,
                          evaluation_as_of=env["as_of"])
    view = {key: item[key] for key in ("horizon_sessions", "status", "target_session", "reason", "remaining_sessions",
                                       "price_grade", "stock_return") if key in item}
    if item["status"] == "SCORED":
        view["cf_value"] = item["vs_cash"]
    return view


def _path_20(env: dict[str, Any], symbol: str, start: Any) -> dict[str, Any]:
    """Lowest and highest stock return (sign kept) of the 20 closes after the start close, once all are final."""
    if env["failure"] is not None:
        return {"status": "NOT_SCORABLE", "reason": env["failure"]}
    if not isinstance(start, str) or start not in env["order"]:
        return {"status": "NOT_SCORABLE", "reason": "START_SESSION_NOT_IN_CALENDAR"}
    index = env["order"][start]
    if index + PATH_SESSIONS >= len(env["sessions"]):
        return {"status": "NOT_SCORABLE", "reason": "CALENDAR_DOES_NOT_COVER_HORIZON"}
    window = env["sessions"][index:index + PATH_SESSIONS + 1]
    closed = _moment(env["rows"][window[-1]].get("core_close_at"))
    if closed is None:
        return {"status": "NOT_SCORABLE", "reason": "CALENDAR_CLOSE_TIME_INVALID"}
    if closed > env["as_of"]:
        return {"status": "PENDING", "target_session": window[-1]}
    per_symbol = env["adjusted"].get(symbol) or {}
    values = [_decimal(per_symbol.get(session)) for session in window]
    if any(value is None for value in values):
        return {"status": "NOT_SCORABLE", "reason": "PATH_CLOSE_MISSING"}
    if _split_suspect(per_symbol, window):
        return {"status": "NOT_SCORABLE", "reason": "POSSIBLE_UNADJUSTED_SPLIT"}
    returns = [value / values[0] - 1 for value in values[1:]]
    return {"status": "SCORED", "target_session": window[-1], "min": _text(min(returns)), "max": _text(max(returns))}


def _band_quantile(values: list[float], fraction: float) -> float:
    """Linear interpolation between the closest ranks (the same formula as the core's scenario quantile)."""
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def scenario_band(closes: list[float]) -> dict[str, Any]:
    """Up/down = 90th/10th percentile of the last 60 five-session returns (65 closes); kept here, not imported."""
    if len(closes) < BAND_RETURNS + BAND_HORIZON:
        return {"status": "SHORT", "reason": "SCENARIO_HISTORY_SHORT"}
    window = closes[-(BAND_RETURNS + BAND_HORIZON):]
    returns = [window[index] / window[index - BAND_HORIZON] - 1 for index in range(BAND_HORIZON, len(window))]
    return {"status": "ok", "up": _band_quantile(returns, BAND_UP), "down": _band_quantile(returns, BAND_DOWN),
            "returns_used": len(returns)}


def band_closes(per_symbol: dict[str, str], sessions: list[str], through: str) -> list[float]:
    """Adjusted closes of the contiguous run of calendar sessions ending at `through` (a session without a close
    ends the run, as the core's series builder does)."""
    if through not in sessions:
        return []
    values: list[float] = []
    for session in reversed(sessions[:sessions.index(through) + 1]):
        value = _decimal(per_symbol.get(session))
        if value is None:
            break
        values.append(float(value))
    return list(reversed(values))


def _scored_values(items: list[dict[str, Any]], field: str = "cf_value") -> list[Decimal]:
    return [Decimal(item[field]) for item in items if item.get("status") == "SCORED" and item.get(field) is not None]


def _mean(values: list[Decimal]) -> Decimal | None:
    return sum(values, Decimal(0)) / len(values) if values else None


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _quantile_decimal(values: list[Decimal], fraction: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = int(position.to_integral_value(rounding="ROUND_FLOOR"))
    high = int(position.to_integral_value(rounding="ROUND_CEILING"))
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _maybe_text(value: Decimal | None) -> str | None:
    return _text(value) if value is not None else None


def _combined(items: list[dict[str, Any]], horizon: int) -> dict[str, Any]:
    """A bundle value: the mean of the members' SCORED values; PENDING while any member is still pending."""
    if any(item.get("status") == "PENDING" for item in items):
        return {"horizon_sessions": horizon, "status": "PENDING"}
    values = _scored_values(items)
    if values:
        return {"horizon_sessions": horizon, "status": "SCORED", "cf_value": _text(_mean(values)),
                "n_scored": len(values)}
    reasons = [item.get("reason") for item in items if item.get("status") == "NOT_SCORABLE"]
    return _not_scorable(horizon, reasons[0] if reasons else "NO_MEMBER")


# --- gate units, shock periods, episodes, R-REC1 bundles -----------------------------------------------------------

def _shock_periods(documents: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Runs of eligible days with shock.open true (a day without a boolean open is skipped, false ends the run)."""
    periods: list[dict[str, Any]] = []
    by_day: dict[str, str] = {}
    current: dict[str, Any] | None = None
    for day in sorted(documents, key=lambda name: (documents[name]["evaluation_session"], name)):
        shock = documents[day]["shock"]
        state = shock.get("open")
        if not isinstance(state, bool):
            continue
        if state is False:
            current = None
            continue
        if current is None:
            current = {"period_id": documents[day]["evaluation_session"], "days": [], "event_dates": [], "c0s": []}
            periods.append(current)
        current["days"].append(day)
        event = _dict(shock.get("event"))
        if event.get("date") is not None and event["date"] not in current["event_dates"]:
            current["event_dates"].append(event["date"])
        if event.get("c0") is not None and event["c0"] not in current["c0s"]:
            current["c0s"].append(event["c0"])
        by_day[day] = current["period_id"]
    return periods, by_day


def _blocked_gate(reason: str, req1_text: str) -> str:
    head, _separator, tail = reason.partition(":")
    if head in REQ_LABELS:
        if tail == "unk":
            return head + "_UNK"
        if head == REQ_LABELS[0] and tail == "no" and RESEARCH_GATE in req1_text:
            return RESEARCH_GATE
    return head


def _cell_gates(row: dict[str, Any]) -> set[str]:
    gates: set[str] = set()
    for index, cell in enumerate(row["c"][:len(REQ_LABELS)]):
        state = cell.get("s")
        if state == "ok":
            continue
        if index == 0 and RESEARCH_GATE in str(cell.get("t") or ""):
            gates.add(RESEARCH_GATE)
        else:
            gates.add(REQ_LABELS[index] + ("_UNK" if state == "unk" else ""))
    return gates


def _has_req5(gates: list[str]) -> bool:
    return REQ5_GATE in gates or REQ5_UNK_GATE in gates


def _day_units(day: str, document: dict[str, Any], s7: dict[str, Any], period_id: str | None,
               epochs: dict[str, Any]) -> list[dict[str, Any]]:
    """The gate units of one eligible day (what held back a buy with evidence or a held symbol's sell)."""
    symbols, evidence = document["symbols"], document["evidence"]
    rows = {row["code"]: row for row in document["buy_requirements"]}
    candidates = {(item.get("symbol"), item.get("side")) for item in document["candidates"]}
    listed = document.get("tickets") if isinstance(document.get("tickets"), list) else []
    ticketed = {(item.get("ticker"), item.get("side")) for item in listed if isinstance(item, dict)}
    blocked: dict[tuple[Any, Any], list[str]] = {}
    for item in document["blocked"]:
        blocked.setdefault((item["symbol"], item.get("side")), []).extend(
            reason for reason in item["reasons"] if isinstance(reason, str))
    research_ok = _dict(_dict(document.get("inputs")).get("research_record")).get("status") == "OK"
    day_gates = ({reason.split(":")[0] for reason in document.get("reasons") or [] if isinstance(reason, str)}
                 if document.get("status") == "HOLD" else set())
    shock = document["shock"]
    by_symbol = _dict(shock.get("by_symbol"))
    units: list[dict[str, Any]] = []

    def add(symbol: str, side: str, gates: set[str], status: str | None = None, reason: str | None = None) -> None:
        names = sorted(gates | day_gates)
        unit: dict[str, Any] = {"day": day, "symbol": symbol, "side": side, "gates": names,
                                "binding": len(names) == 1, "binding_scope": "EVALUATED_GATES_ONLY",
                                "start_session": document["buy_session"],
                                "epoch": _epoch(epochs, side, names, None, day)}
        if status is not None:
            unit.update(status=status, reason=reason)
        if _has_req5(names):
            own = _dict(by_symbol.get(symbol))
            event = _dict(shock.get("event"))
            unit.update(shock_open=shock.get("open"), symbol_open=own.get("open"),
                        event={"date": event.get("date"), "c0": event.get("c0")}, rg=own.get("rg"),
                        rrec1_key=(period_id if shock.get("open") is True and period_id is not None else
                                   "SYMBOL_ONLY" if own.get("open") is True else
                                   "UNKNOWN" if not isinstance(shock.get("open"), bool) else "NONE"))
        units.append(unit)

    for symbol in sorted(symbols):
        view = _dict(symbols[symbol])
        own_evidence = _dict(evidence.get(symbol))
        row = rows.get(symbol)
        req1_text = str(_dict(row["c"][0]).get("t") or "") if row else ""
        if view.get("buy_approved") is True and _dict(own_evidence.get("buy")).get("basis_met") is True:
            if (symbol, "buy") not in candidates:
                if row is None:
                    add(symbol, "buy", {"CIRCUIT_NEW_EVIDENCE"}, "NOT_SCORABLE", "BUY_REQUIREMENT_ROW_MISSING")
                else:
                    gates = {"CIRCUIT_NEW_EVIDENCE"} | _cell_gates(row)
                    if not research_ok:
                        gates.add(RESEARCH_GATE)
                    if view.get("status") != "OK" or _dict(view.get("indicators")).get("sigma60") is None:
                        gates.add("G1_SYMBOL_DATA")
                    add(symbol, "buy", gates)
            elif (symbol, "buy") not in ticketed:
                gates = {_blocked_gate(reason, req1_text) for reason in blocked.get((symbol, "buy"), [])}
                if gates or day_gates:
                    add(symbol, "buy", gates)
        if view.get("role") != "held":
            continue
        sell_gates = {_blocked_gate(reason, req1_text) for reason in blocked.get((symbol, "sell"), [])}
        basis = _dict(own_evidence.get("sell")).get("basis_met") is True
        if (symbol, "sell") in candidates:
            if (symbol, "sell") not in ticketed and (sell_gates or day_gates):
                add(symbol, "sell", sell_gates)
            continue
        if "CARD_TRIM_SIZE_MISSING" in sell_gates:
            add(symbol, "sell", sell_gates if basis else sell_gates | {"CIRCUIT_SELL_NO_EVIDENCE"})
        elif basis:
            add(symbol, "sell", sell_gates | {"CIRCUIT_SELL_NO_GAP"})
        elif s7["status"] != "OK":
            # Whether S7 asked for a reduction is unknown that day: this judgment only is not scorable.
            add(symbol, "sell", sell_gates | {"CIRCUIT_SELL_NO_EVIDENCE"}, "NOT_SCORABLE", s7["status"])
        elif symbol in s7["reduce"]:
            add(symbol, "sell", sell_gates | {"CIRCUIT_SELL_NO_EVIDENCE"})
    return units


def _episodes(units: list[dict[str, Any]], documents: dict[str, dict[str, Any]], env: dict[str, Any],
              epochs: dict[str, Any], commits: dict[str, Any]) -> list[dict[str, Any]]:
    """Runs of the same (symbol, side, gates[, R-REC1 key]) over eligible days; an ineligible day neither joins nor
    breaks a run, an eligible day without the key ends it."""
    by_day: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = {}
    for unit in units:
        if unit.get("status") == "NOT_SCORABLE":
            continue
        key = (unit["symbol"], unit["side"], tuple(unit["gates"]),
               unit.get("rrec1_key") if _has_req5(unit["gates"]) else None)
        by_day.setdefault(unit["day"], {})[key] = unit
    episodes: list[dict[str, Any]] = []
    running: dict[tuple[Any, ...], dict[str, Any]] = {}
    for day in sorted(documents, key=lambda name: (documents[name]["evaluation_session"], name)):
        today = by_day.get(day, {})
        for key in [key for key in running if key not in today]:
            del running[key]
        for key in sorted(today, key=lambda item: (item[0], item[1], item[2], item[3] or "")):
            if key in running:
                running[key]["last_day"] = day
                running[key]["days"] += 1
                continue
            unit = today[key]
            episode = {"episode_id": f"{day}:{unit['symbol']}:{unit['side']}:{'+'.join(unit['gates'])}"
                                     + (f"@{key[3]}" if key[3] is not None else ""),
                       "symbol": unit["symbol"], "side": unit["side"], "gates": list(unit["gates"]),
                       "binding": unit["binding"], "first_day": day, "last_day": day, "days": 1,
                       "start_session": unit["start_session"], "commit_sha": commits.get(day)}
            if key[3] is not None:
                episode["rrec1_key"] = key[3]
            running[key] = episode
            episodes.append(episode)
    last_unit: dict[tuple[Any, ...], str] = {}
    for episode in sorted(episodes, key=lambda item: (item["start_session"] or "", item["first_day"], item["symbol"])):
        episode["epoch"] = _epoch(epochs, episode["side"], episode["gates"], None, episode["first_day"])
        key = (episode["symbol"], episode["side"], tuple(episode["gates"]))
        gap = _gap(env, last_unit.get(key), episode["start_session"])
        episode["unit"] = key not in last_unit or gap is None or gap >= GATE_PRIMARY
        if episode["unit"]:
            last_unit[key] = episode["start_session"]
        episode["horizons"] = [_cf(env, horizon, episode["symbol"], episode["side"], episode["start_session"])
                               for horizon in GATE_HORIZONS]
        episode["path_20"] = _path_20(env, episode["symbol"], episode["start_session"])
    return episodes


def _rrec1_bundles(episodes: list[dict[str, Any]], gate: str, env: dict[str, Any]) -> list[dict[str, Any]]:
    """R-REC1 independent units: inside one shock period, binding episodes whose start is less than 20 sessions after
    the bundle's first start and that share its epoch form one bundle."""
    chosen = [episode for episode in episodes if episode["binding"] and episode["gates"] == [gate]
              and episode.get("rrec1_key") is not None
              and (gate == REQ5_UNK_GATE or episode["rrec1_key"] not in RREC1_DISPLAY_KEYS)]
    by_period: dict[str, list[dict[str, Any]]] = {}
    for episode in sorted(chosen, key=lambda item: (item["start_session"] or "", item["symbol"])):
        by_period.setdefault(episode["rrec1_key"], []).append(episode)
    bundles: list[dict[str, Any]] = []
    for period_id in sorted(by_period):
        current: dict[str, Any] | None = None
        count = 0
        for episode in by_period[period_id]:
            gap = _gap(env, current["start_session"], episode["start_session"]) if current else None
            if current is None or gap is None or gap >= GATE_PRIMARY or episode["epoch"] != current["epoch"]:
                count += 1
                current = {"unit_id": f"{period_id}#{count}", "period_id": period_id,
                           "start_session": episode["start_session"], "epoch": episode["epoch"], "members": [],
                           "commit_sha": episode.get("commit_sha")}
                bundles.append(current)
            current["members"].append(episode)
    out = []
    for bundle in bundles:
        members = bundle.pop("members")
        paths = [member["path_20"] for member in members]
        path_min = _mean([Decimal(item["min"]) for item in paths if item.get("status") == "SCORED"])
        out.append({**bundle, "n_episodes": len(members), "symbols": sorted({member["symbol"] for member in members}),
                    "episode_ids": [member["episode_id"] for member in members],
                    "horizons": [_combined([next(item for item in member["horizons"]
                                                 if item["horizon_sessions"] == horizon) for member in members], horizon)
                                 for horizon in GATE_HORIZONS],
                    "path_20_min_mean": _maybe_text(path_min)})
    return out


# --- ticket-based units ---------------------------------------------------------------------------------------------

def _ticket_day(ticket: dict[str, Any]) -> str | None:
    match = TICKET_DAY.match(str(ticket.get("ticket_id") or ""))
    if match:
        text = "-".join(match.groups())
        if _iso_day(text):
            return text
    return ticket.get("folder_day") if _iso_day(ticket.get("folder_day")) else None


def _horizon_of(items: list[dict[str, Any]], horizon: int) -> dict[str, Any]:
    return next((item for item in items if item.get("horizon_sessions") == horizon),
                _not_scorable(horizon, "HORIZON_MISSING"))


def _next_fill(ticket: dict[str, Any], tickets: list[dict[str, Any]], env: dict[str, Any]) -> dict[str, Any]:
    if env["failure"] is not None:
        return {"status": "NOT_SCORABLE", "reason": env["failure"]}
    session = ticket.get("session")
    if session not in env["order"]:
        return {"status": "NOT_SCORABLE", "reason": "START_SESSION_NOT_IN_CALENDAR"}
    index = env["order"][session]
    later = sorted((item for item in tickets if item.get("side") == "sell" and item.get("ticker") == ticket.get("ticker")
                    and item.get("would_fill") is True and item.get("session") in env["order"]
                    and 0 < env["order"][item["session"]] - index <= NEXT_FILL_WINDOW),
                   key=lambda item: (env["order"][item["session"]], str(item.get("ticket_id"))))
    if later:
        fill = later[0]["session"]
        per_symbol = env["adjusted"].get(ticket.get("ticker")) or {}
        start, end = _decimal(per_symbol.get(session)), _decimal(per_symbol.get(fill))
        result: dict[str, Any] = {"status": "FILLED_LATER", "session": fill,
                                  "sessions_after": env["order"][fill] - index, "delay_value": None}
        if start is None or end is None:
            result["reason"] = "CLOSE_MISSING"
        elif _split_suspect(per_symbol, env["sessions"][index:env["order"][fill] + 1]):
            result["reason"] = "POSSIBLE_UNADJUSTED_SPLIT"
        else:
            result["delay_value"] = _text(-(end / start - 1))
        return result
    if index + NEXT_FILL_WINDOW >= len(env["sessions"]):
        return {"status": "NOT_SCORABLE", "reason": "CALENDAR_DOES_NOT_COVER_HORIZON"}
    end_session = env["sessions"][index + NEXT_FILL_WINDOW]
    closed = _moment(env["rows"][end_session].get("core_close_at"))
    if closed is None or closed > env["as_of"]:
        return {"status": "PENDING", "window_end": end_session}
    return {"status": "NO_LATER_FILL_WITHIN_5", "window_end": end_session}


def _spaced(env: dict[str, Any], last: dict[Any, str], key: Any, session: Any, sessions: int) -> bool:
    """True (and remembered) when key has no earlier unit or its last unit started `sessions` or more before."""
    gap = _gap(env, last.get(key), session)
    unit = key not in last or gap is None or gap >= sessions
    if unit:
        last[key] = session
    return unit


def _sell_floor(tickets: list[dict[str, Any]], env: dict[str, Any], epochs: dict[str, Any]) -> list[dict[str, Any]]:
    """Sell tickets the floor kept from filling (hypothetical not filled, or the user's recorded unfilled)."""
    targets = sorted((ticket for ticket in tickets if ticket.get("side") == "sell" and (
        ticket.get("would_fill") is False or (ticket.get("mode") == "apply" and ticket.get("user_state") == "unfilled"))),
        key=lambda ticket: (str(ticket.get("session")), str(ticket.get("ticket_id"))))
    seen: set[Any] = set()
    last: dict[Any, str] = {}
    rows = []
    for ticket in targets:
        key = ticket.get("decision_key") or ticket.get("ticket_id")
        unit = key not in seen and _spaced(env, last, ticket.get("ticker"), ticket.get("session"), FLOOR_PRIMARY)
        seen.add(key)
        first_day = _ticket_day(ticket)
        rows.append({"ticket_id": ticket.get("ticket_id"), "ticker": ticket.get("ticker"),
                     "session": ticket.get("session"), "decision_key": ticket.get("decision_key"), "unit": unit,
                     "first_day": first_day, "epoch": _epoch(epochs, "sell", [], "SELL_FLOOR", first_day),
                     "horizons": [_cf(env, horizon, ticket.get("ticker"), "sell", ticket.get("session"))
                                  for horizon in FLOOR_HORIZONS],
                     "next_fill": _next_fill(ticket, tickets, env)})
    return rows


def _ticket_band(env: dict[str, Any], ticket: dict[str, Any]) -> dict[str, Any]:
    if env["failure"] is not None:
        return {"status": "NOT_SCORABLE", "reason": env["failure"]}
    session = ticket.get("session")
    if session not in env["order"]:
        return {"status": "NOT_SCORABLE", "reason": "START_SESSION_NOT_IN_CALENDAR"}
    index = env["order"][session]
    closes = (band_closes(env["adjusted"].get(ticket.get("ticker")) or {}, env["sessions"], env["sessions"][index - 1])
              if index > 0 else [])
    band = scenario_band(closes)
    if band["status"] != "ok":
        return {"status": "NOT_SCORABLE", "reason": band["reason"], "closes_used": len(closes)}
    return {"status": "OK", "up": format(band["up"], ".9f"), "down": format(band["down"], ".9f"),
            "returns_used": band["returns_used"], "_up": band["up"], "_down": band["down"]}


def _scenario_band_rows(tickets: list[dict[str, Any]], env: dict[str, Any],
                        epochs: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[Any] = set()
    last: dict[Any, str] = {}
    rows = []
    for ticket in sorted(tickets, key=lambda item: (str(item.get("session")), str(item.get("ticket_id")))):
        key = ticket.get("decision_key") or ticket.get("ticket_id")
        side = ticket.get("side")
        unit = key not in seen and _spaced(env, last, (ticket.get("ticker"), side), ticket.get("session"), BAND_PRIMARY)
        seen.add(key)
        band = _ticket_band(env, ticket)
        realised = _cf(env, BAND_HORIZON, ticket.get("ticker"), "buy", ticket.get("session"))
        verdict, path = "NOT_SCORABLE", None
        reason = band.get("reason") if band["status"] != "OK" else realised.get("reason")
        if band["status"] == "OK" and realised["status"] == "PENDING":
            verdict, reason = "PENDING", None
        elif band["status"] == "OK" and realised["status"] == "SCORED":
            per_symbol = env["adjusted"][ticket["ticker"]]
            value = float(_decimal(per_symbol[realised["target_session"]])) / float(
                _decimal(per_symbol[ticket["session"]])) - 1
            verdict = "UP_TAIL" if value >= band["_up"] else "DOWN_TAIL" if value <= band["_down"] else "INSIDE"
            reason = None
            tails = {"DOWN_TAIL": "PREMORTEM", "UP_TAIL": "PRECELEBRATION"} if side == "buy" else \
                {"DOWN_TAIL": "PRECELEBRATION", "UP_TAIL": "PREMORTEM"}
            path = tails.get(verdict)
        elif band["status"] == "OK" and realised["status"] != "SCORED" and reason is None:
            reason = "REALISED_RETURN_UNAVAILABLE"
        first_day = _ticket_day(ticket)
        rows.append({"ticket_id": ticket.get("ticket_id"), "ticker": ticket.get("ticker"), "side": side,
                     "session": ticket.get("session"), "decision_key": ticket.get("decision_key"), "unit": unit,
                     "first_day": first_day, "epoch": _epoch(epochs, side, [], "SCENARIO_BAND", first_day),
                     "band": {key: value for key, value in band.items() if not key.startswith("_")},
                     "r5": realised, "verdict": verdict, "reason": reason, "path": path})
    return rows


def _trigger_kinds(ticket_results: list[dict[str, Any]], tickets: dict[Any, dict[str, Any]], env: dict[str, Any],
                   epochs: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[Any] = set()
    last: dict[Any, str] = {}
    rows = []
    for result in sorted(ticket_results, key=lambda item: (str(item.get("session")), str(item.get("ticket_id")))):
        source = tickets.get(result.get("ticket_id")) or {}
        key = source.get("decision_key") or result.get("ticket_id")
        if key in seen:
            continue
        seen.add(key)
        kinds = result.get("evidence_weak_kinds")
        kinds = ["WEAK_KINDS_NOT_RECORDED"] if kinds is None else (sorted(set(kinds)) or ["NO_WEAK_KIND"])
        horizons = [_cf(env, horizon, result.get("ticker"), result.get("side"), result.get("session"))
                    for horizon in TRIGGER_HORIZONS]
        first_day = _ticket_day(source or result)
        for kind in kinds:
            unit = _spaced(env, last, (result.get("ticker"), result.get("side"), kind), result.get("session"),
                           TRIGGER_PRIMARY)
            rows.append({"ticket_id": result.get("ticket_id"), "ticker": result.get("ticker"),
                         "side": result.get("side"), "session": result.get("session"), "kind": kind,
                         "overlap": len(kinds), "unit": unit, "first_day": first_day,
                         "epoch": _epoch(epochs, result.get("side"), [], None, first_day), "horizons": horizons})
    return rows


# --- buckets and findings ------------------------------------------------------------------------------------------

def _bucket_items(episodes: list[dict[str, Any]], bundles: list[dict[str, Any]], floor: list[dict[str, Any]],
                  band: list[dict[str, Any]], triggers: list[dict[str, Any]], commits: dict[str, Any]
                  ) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for episode in episodes:
        if not (episode["binding"] and episode["unit"] and len(episode["gates"]) == 1):
            continue
        gate, display = episode["gates"][0], None
        if gate in (REQ5_GATE, REQ5_UNK_GATE):
            if episode.get("rrec1_key") in RREC1_DISPLAY_KEYS:
                gate, display = f"{gate}@{episode['rrec1_key']}", "DISPLAY_ONLY"
            else:
                display = "SEE_RREC1_UNITS"
        path = episode["path_20"]
        items.append({"family": "GATE", "key": [episode["side"], gate, episode["epoch"]], "side": episode["side"],
                      "gates": list(episode["gates"]), "extra": None, "epoch": episode["epoch"],
                      "start_session": episode["start_session"], "symbol": episode["symbol"],
                      "unit_id": episode["episode_id"], "commit": episode.get("commit_sha"), "display": display,
                      "primary": _horizon_of(episode["horizons"], GATE_PRIMARY),
                      "path_min": path.get("min") if path.get("status") == "SCORED" else None})
    for bundle in bundles:
        items.append({"family": "GATE_RREC1_UNIT", "key": [bundle["epoch"]], "side": "buy", "gates": [REQ5_GATE],
                      "extra": None, "epoch": bundle["epoch"], "start_session": bundle["start_session"],
                      "symbol": ",".join(bundle["symbols"]), "unit_id": bundle["unit_id"],
                      "commit": bundle.get("commit_sha"), "display": None,
                      "primary": _horizon_of(bundle["horizons"], GATE_PRIMARY), "path_min": bundle["path_20_min_mean"]})
    for row in floor:
        if row["unit"]:
            items.append({"family": "SELL_FLOOR", "key": [row["epoch"]], "side": "sell", "gates": [],
                          "extra": "SELL_FLOOR", "epoch": row["epoch"], "start_session": row["session"],
                          "symbol": row["ticker"], "unit_id": row["ticket_id"], "commit": commits.get(row["first_day"]),
                          "display": None, "primary": _horizon_of(row["horizons"], FLOOR_PRIMARY), "path_min": None})
    for row in band:
        if not row["unit"]:
            continue
        judged = row["verdict"] in ("UP_TAIL", "DOWN_TAIL", "INSIDE")
        primary = ({"horizon_sessions": BAND_PRIMARY, "status": "SCORED", "cf_value": row["r5"]["stock_return"]}
                   if judged else {"horizon_sessions": BAND_PRIMARY, "status": row["verdict"], "reason": row["reason"]})
        items.append({"family": "SCENARIO_BAND", "key": [row["side"], row["epoch"]], "side": row["side"], "gates": [],
                      "extra": "SCENARIO_BAND", "epoch": row["epoch"], "start_session": row["session"],
                      "symbol": row["ticker"], "unit_id": row["ticket_id"], "commit": commits.get(row["first_day"]),
                      "display": None, "primary": primary, "path_min": None, "verdict": row["verdict"]})
    for row in triggers:
        if row["unit"]:
            items.append({"family": "TRIGGER_KIND", "key": [row["side"], row["kind"], row["epoch"]], "side": row["side"],
                          "gates": [], "extra": None, "epoch": row["epoch"], "start_session": row["session"],
                          "symbol": row["ticker"], "unit_id": row["ticket_id"], "commit": commits.get(row["first_day"]),
                          "display": "DISPLAY_ONLY" if row["kind"] == "WEAK_KINDS_NOT_RECORDED" else None,
                          "primary": _horizon_of(row["horizons"], TRIGGER_PRIMARY), "path_min": None})
    return items


def _ratio(rows: list[dict[str, Any]], verdict: str) -> Decimal | None:
    return Decimal(sum(1 for row in rows if row["verdict"] == verdict)) / len(rows) if rows else None


def _bucket(family: str, items: list[dict[str, Any]], epochs: dict[str, Any], as_of_day: str | None) -> dict[str, Any]:
    sample = items[0]
    epoch = sample["epoch"]
    current = _epoch(epochs, sample["side"], [gate for gate in sample["gates"]], sample["extra"], as_of_day)
    scored = sorted((item for item in items if item["primary"].get("status") == "SCORED"),
                    key=lambda item: (str(item["start_session"]), str(item["symbol"]), str(item["unit_id"])))
    unscorable: dict[str, int] = {}
    calendar_out = pending = 0
    for item in items:
        status, reason = item["primary"].get("status"), item["primary"].get("reason")
        if status == "PENDING":
            pending += 1
        elif status == "NOT_SCORABLE" and reason == "CALENDAR_DOES_NOT_COVER_HORIZON":
            calendar_out += 1
        elif status != "SCORED":
            unscorable[str(reason)] = unscorable.get(str(reason), 0) + 1
    missing = sum(unscorable.values())
    denominator = len(scored) + missing
    coverage_ok = denominator > 0 and Decimal(missing) / denominator <= COVERAGE_MAX_UNSCORABLE
    values = [Decimal(item["primary"]["cf_value"]) for item in scored]
    half = len(values) // 2
    first_mean, second_mean = _mean(values[:half]), _mean(values[half:])
    mean, median = _mean(values), _median(values)
    epochs_ok = epochs["status"] == "OK"
    bucket: dict[str, Any] = {
        "family": family, "key": sample["key"], "primary_horizon": BUCKET_PRIMARY[family], "current_epoch": current,
        "n_units": len(items), "n_scored": len(scored),
        "n_unscorable": {"total": missing, "by_reason": dict(sorted(unscorable.items()))},
        "n_calendar_out": calendar_out, "n_pending": pending, "coverage_ok": coverage_ok,
        "distinct_start_sessions": len({item["start_session"] for item in items}),
        "distinct_commits": len({item["commit"] for item in items if item["commit"] is not None}),
        "mean": _maybe_text(mean), "median": _maybe_text(median),
        "p10": _maybe_text(_quantile_decimal(values, Decimal("0.1"))),
        "first_half_mean": _maybe_text(first_mean), "second_half_mean": _maybe_text(second_mean)}
    if family in ("GATE", "GATE_RREC1_UNIT"):
        bucket["path_min_mean"] = _maybe_text(_mean([Decimal(item["path_min"]) for item in scored
                                                     if item["path_min"] is not None]))
    if family == "SCENARIO_BAND":
        first, second = scored[:half], scored[half:]
        bucket["tail_ratios"] = {name: {"up": _maybe_text(_ratio(rows, "UP_TAIL")),
                                        "down": _maybe_text(_ratio(rows, "DOWN_TAIL"))}
                                 for name, rows in (("all", scored), ("first_half", first), ("second_half", second))}
    bucket["conclusion_allowed"] = (sample["display"] is None and len(scored) >= MIN_SCORED_FOR_CONCLUSION
                                    and coverage_ok and epochs_ok and epoch is not None and epoch == current)
    if sample["display"] is not None:
        finding: Any = sample["display"]
    elif not epochs_ok:
        finding = "EPOCHS_UNAVAILABLE"
    elif epoch is None or current is None:
        finding = "EPOCH_UNKNOWN"
    elif epoch < current:
        finding = "EARLIER_EPOCH"
    elif epoch != current:
        finding = "EPOCH_MISMATCH"
    elif len(scored) < MIN_SCORED_FOR_CONCLUSION:
        finding = "INSUFFICIENT_SAMPLE"
    elif not coverage_ok:
        finding = "INSUFFICIENT_COVERAGE"
    elif family == "SCENARIO_BAND":
        first, second = scored[:half], scored[half:]
        found = [name for verdict, name in (("DOWN_TAIL", "DOWN_TAIL_UNDERSTATED"), ("UP_TAIL", "UP_TAIL_UNDERSTATED"))
                 if all((_ratio(rows, verdict) or Decimal(0)) >= TAIL_SHARE and rows for rows in (first, second))]
        finding = found[0] if len(found) == 1 else found if found else "MIXED"
    else:
        four = [mean, median, first_mean, second_mean]
        positive, negative = ("STRONG", "WEAK") if family == "TRIGGER_KIND" else ("COST", "PROTECT")
        finding = (positive if all(value is not None and value > 0 for value in four) else
                   negative if all(value is not None and value < 0 for value in four) else "MIXED")
    bucket["finding"] = finding
    return bucket


def _buckets(items: list[dict[str, Any]], epochs: dict[str, Any], as_of_day: str | None) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(json.dumps([item["family"], item["key"]]), []).append(item)
    return [_bucket(group[0]["family"], group, epochs, as_of_day) for _name, group in sorted(groups.items())]


def _overlap_summary(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for episode in episodes:
        if not episode["binding"]:
            groups.setdefault(json.dumps([episode["side"], sorted(episode["gates"]), episode["epoch"]]), []).append(episode)
    out = []
    for name, group in sorted(groups.items()):
        side, gates, epoch = json.loads(name)
        values = _scored_values([_horizon_of(episode["horizons"], GATE_PRIMARY) for episode in group])
        out.append({"side": side, "gates": gates, "epoch": epoch, "n": len(group), "n_scored_20": len(values),
                    "mean_20": _maybe_text(_mean(values))})
    return out


# --- failure museum -------------------------------------------------------------------------------------------------

def _museum_entry_errors(entry: Any) -> list[str]:
    if not isinstance(entry, dict):
        return ["ENTRY_NOT_OBJECT"]
    errors = [f"FIELD_MISSING:{key}" for key in ("candidate_id", "failed_assumption", "written_by", "written_at")
              if not isinstance(entry.get(key), str) or not entry[key].strip()]
    if entry.get("category") not in MUSEUM_CATEGORIES:
        errors.append("FIELD_INVALID:category")
    if not isinstance(entry.get("evidence"), list) or not entry["evidence"]:
        errors.append("FIELD_MISSING:evidence")
    return errors


def _museum(results: list[dict[str, Any]], ticket_results: list[dict[str, Any]],
            loaded: dict[str, Any]) -> dict[str, Any]:
    """Candidates (20-session SCORED results that lost) and the control list; entries are written by Cowork."""
    candidates: list[dict[str, Any]] = []
    control: list[str] = []

    def consider(candidate_id: str, item: dict[str, Any], field: str) -> None:
        if item.get("status") != "SCORED" or item.get(field) is None:
            return
        value = Decimal(item[field])
        if value < 0:
            candidates.append({"candidate_id": candidate_id, "value": item[field]})
        elif value > 0:
            control.append(candidate_id)

    for row in results:
        consider(f"RESULT:{row.get('decision_id')}:{row.get('kind')}:h{MUSEUM_HORIZON}",
                 _horizon_of(row.get("horizons") or [], MUSEUM_HORIZON), "vs_cash")
    for row in ticket_results:
        user = _dict(row.get("user"))
        if user.get("state") in ("filled", "partial"):
            consider(f"TICKET:{row.get('ticket_id')}:USER:h{MUSEUM_HORIZON}",
                     _horizon_of(user.get("horizons") or [], MUSEUM_HORIZON), "vs_no_action")
        if row.get("mode") == "compare" and row.get("would_fill") is True:
            consider(f"TICKET:{row.get('ticket_id')}:HYPOTHETICAL:h{MUSEUM_HORIZON}",
                     _horizon_of(row.get("horizons") or [], MUSEUM_HORIZON), "vs_no_action")
    errors: list[dict[str, Any]] = [{"reason": reason} for reason in loaded.get("errors") or []]
    entries: dict[str, dict[str, Any]] = {}
    if loaded.get("status") == "OK":
        for index, entry in enumerate(loaded["document"]["entries"]):
            problems = _museum_entry_errors(entry)
            if problems:
                errors.append({"index": index, "reasons": problems})
                continue
            entries[entry["candidate_id"]] = {**entry, "grade": entry.get("grade") or COUNTERFACTUAL_GRADE}
    ids = [item["candidate_id"] for item in candidates]
    return {"status": loaded.get("status"), "errors": errors, "candidates": candidates, "control": control,
            "filled": sum(1 for candidate_id in ids if candidate_id in entries),
            "pending": [candidate_id for candidate_id in ids if candidate_id not in entries],
            "entries": [{"candidate_id": candidate_id, "category": entry["category"], "grade": entry["grade"]}
                        for candidate_id, entry in sorted(entries.items())]}


# --- the block ------------------------------------------------------------------------------------------------------

def score_learning(*, decision_days: list[dict[str, Any]], s7_by_day: dict[str, dict[str, Any]],
                   results: list[dict[str, Any]], ticket_results: list[dict[str, Any]], tickets: list[dict[str, Any]],
                   calendar: dict[str, Any] | None, closes: dict[str, dict[str, str]],
                   unverified: dict[str, dict[str, list[str]]], corporate_actions: dict[str, Any],
                   museum: dict[str, Any], epochs: dict[str, Any], previous_days: list[dict[str, Any]] | None,
                   evaluation_as_of: datetime, decisions_root_status: str = "OK") -> dict[str, Any]:
    """The learning block. Pure: no file is read or written here.

    decision_days: load_decision_days rows ({day, sha256, document | error}); s7_by_day: {day: load_s7_reduce output};
    results / ticket_results: the report's rows; tickets: one row per ticket_results row with its decision_key,
    would_fill, user_state and folder_day; museum / epochs: load_learning_document outputs; previous_days: the
    decision_days of the latest earlier usable learning block (None = none)."""
    as_of_day = _kst_day(evaluation_as_of)
    env = _learning_env(calendar, closes, unverified, corporate_actions, evaluation_as_of)
    epoch_context = _epoch_context(epochs)
    rows, documents, errors = _decision_rows(decision_days, previous_days, decisions_root_status, as_of_day)
    commits = {row["day"]: row.get("commit_sha") for row in rows}
    periods, period_by_day = _shock_periods(documents)
    units: list[dict[str, Any]] = []
    for day in sorted(documents, key=lambda name: (documents[name]["evaluation_session"], name)):
        try:
            units += _day_units(day, documents[day],
                                s7_by_day.get(day) or {"status": "S7_REVIEW_UNREADABLE", "reduce": []},
                                period_by_day.get(day), epoch_context)
        except Exception as exc:  # noqa: BLE001 - one odd file is an error of that day, the other days go on
            errors.append({"reason": f"DAY_UNITS_FAILED:{type(exc).__name__}", "file": f"{day}/{DECISION_FILE}"})
    episodes = _episodes(units, documents, env, epoch_context, commits)
    bundles = _rrec1_bundles(episodes, REQ5_GATE, env)
    unk_bundles = _rrec1_bundles(episodes, REQ5_UNK_GATE, env)
    by_ticket = {ticket.get("ticket_id"): ticket for ticket in tickets}
    floor = _sell_floor(tickets, env, epoch_context)
    band = _scenario_band_rows(tickets, env, epoch_context)
    triggers = _trigger_kinds(ticket_results, by_ticket, env, epoch_context)
    buckets = _buckets(_bucket_items(episodes, bundles, floor, band, triggers, commits), epoch_context, as_of_day)
    return {
        "schema": LEARNING_SCHEMA, "preregistration": dict(PREREGISTRATION), "label": COUNTERFACTUAL_LABEL,
        "display_only": True, "evaluation_day_kst": as_of_day,
        "epochs": {"status": epoch_context["status"], "count": len(epoch_context["entries"])},
        "errors": errors, "decisions_root_status": decisions_root_status, "decision_days": rows,
        "gate_units": units, "shock_periods": periods, "gate_episodes": episodes, "rrec1_units": bundles,
        "rrec1_unk_units": unk_bundles, "sell_floor": floor, "scenario_band": band, "trigger_kinds": triggers,
        "buckets": buckets, "overlap_summary": _overlap_summary(episodes),
        "museum": _museum(results, ticket_results, museum),
        "counts": {"days": len(rows), "eligible": sum(1 for row in rows if row["eligible"]),
                   "excluded": sum(1 for row in rows if not row["eligible"]),
                   "preservation_broken": sum(1 for row in rows if "PRESERVATION_BROKEN" in (row.get("flags") or [])),
                   "buckets": len(buckets),
                   "conclusion_allowed": sum(1 for bucket in buckets if bucket["conclusion_allowed"])},
    }


def failed_learning(exc: BaseException) -> dict[str, Any]:
    """The block of a learning run that failed as a whole: visible, and skipped as the next week's earlier block."""
    return {"schema": LEARNING_SCHEMA, "preregistration": dict(PREREGISTRATION), "label": COUNTERFACTUAL_LABEL,
            "display_only": True, "decision_days": [],
            "errors": [{"reason": f"{LEARNING_FAILED}:{type(exc).__name__}:{str(exc)[:200]}"}]}


def _learning_tickets(entries: list[dict[str, Any]], records: list[dict[str, Any]],
                      decision_days: list[dict[str, Any]], ticket_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One source row per scored ticket: decision_key from the journal payload or the compare record, the folder day
    of the decision.json that held it, would_fill and the user's state from the ticket result."""
    keys: dict[Any, Any] = {}
    for entry in entries:
        if entry.get("entry_type") == JOURNAL_ORDER_TICKET:
            payload = entry.get("payload") or {}
            keys.setdefault(payload.get("ticket_id"), payload.get("decision_key"))
    for record in records:
        keys.setdefault(record.get("ticket_id"), record.get("decision_key"))
    folders: dict[Any, str] = {}
    for item in decision_days:
        listed = _dict(item.get("document")).get("tickets")
        for ticket in listed if isinstance(listed, list) else []:
            if isinstance(ticket, dict) and isinstance(ticket.get("ticket_id"), str):
                folders.setdefault(ticket["ticket_id"], item["day"])
    return [{"ticket_id": row["ticket_id"], "ticker": row["ticker"], "side": row["side"], "mode": row["mode"],
             "session": row["session"], "decision_key": keys.get(row["ticket_id"]), "would_fill": row["would_fill"],
             "user_state": _dict(row.get("user")).get("state"), "folder_day": folders.get(row["ticket_id"])}
            for row in ticket_results]


def learning_symbols(decision_days: list[dict[str, Any]]) -> list[str]:
    """The symbols keys of every readable decision.json (their closes are read with the report's tickers)."""
    found: set[str] = set()
    for item in decision_days:
        symbols = _dict(item.get("document")).get("symbols")
        if isinstance(symbols, dict):
            found.update(symbol for symbol in symbols if isinstance(symbol, str))
    return sorted(found)


def render_learning(learning: dict[str, Any]) -> list[str]:
    if _learning_failed(learning):
        return [LEARNING_MESSAGES["failed"].format(reason=learning["errors"][0]["reason"])]
    counts = learning["counts"]
    lines = [LEARNING_MESSAGES["days"].format(total=counts["days"], eligible=counts["eligible"],
                                              excluded=counts["excluded"], broken=counts["preservation_broken"]),
             LEARNING_MESSAGES["buckets"].format(buckets=counts["buckets"], allowed=counts["conclusion_allowed"],
                                                 minimum=MIN_SCORED_FOR_CONCLUSION)]
    for bucket in learning["buckets"]:
        names = bucket["finding"] if isinstance(bucket["finding"], list) else [bucket["finding"]]
        for name in names:
            if name in SHOWN_FINDINGS:
                lines.append(LEARNING_MESSAGES["finding"].format(
                    family=bucket["family"], key="/".join(str(part) for part in bucket["key"]), finding=name,
                    n=bucket["n_scored"], mean=bucket["mean"], median=bucket["median"]))
    museum = learning["museum"]
    lines.append(LEARNING_MESSAGES["museum"].format(status=museum["status"], candidates=len(museum["candidates"]),
                                                    filled=museum["filled"], pending=len(museum["pending"])))
    if learning["errors"]:
        lines.append(LEARNING_MESSAGES["errors"].format(count=len(learning["errors"]), reasons=",".join(
            sorted({str(item.get("reason")) for item in learning["errors"]}))))
    return lines


def _learning_block(*, args: argparse.Namespace, journal: dict[str, Any], compare: dict[str, Any],
                    loaded_days: dict[str, Any], report: dict[str, Any], inputs: dict[str, Any],
                    evaluation_as_of: datetime) -> dict[str, Any]:
    """Reads the learning inputs and scores them; any exception leaves a LEARNING_FAILED block, never a crash."""
    try:
        days = loaded_days["days"]
        s7_by_day = {item["day"]: load_s7_reduce(item["document"], args.decisions_root)
                     for item in days if isinstance(item.get("document"), dict)}
        previous = find_previous_learning(check_output_root(args.output_root, args.journal))
        tickets = _learning_tickets(journal["entries"], compare["records"], days, report["ticket_results"])
        learning = score_learning(
            decision_days=days, s7_by_day=s7_by_day, results=report["results"],
            ticket_results=report["ticket_results"], tickets=tickets, calendar=inputs["calendar"],
            closes=inputs["closes"], unverified=inputs["unverified"], corporate_actions=inputs["corporate_actions"],
            museum=load_learning_document(args.museum, MUSEUM_SCHEMA, "entries"),
            epochs=load_learning_document(args.epochs, EPOCHS_SCHEMA, "epochs"),
            previous_days=previous["decision_days"] if previous else None, evaluation_as_of=evaluation_as_of,
            decisions_root_status=loaded_days["status"])
        learning["previous_report"] = previous["path"] if previous else None
        return learning
    except Exception as exc:  # noqa: BLE001 - a learning failure is a status in the report, never an exception
        return failed_learning(exc)


def _no_inputs() -> dict[str, Any]:
    return {"calendar": None, "calendar_failure": None, "closes": {}, "unverified": {}, "close_histories": {},
            "corporate_actions": {"status": "MISSING", "sha256": None, "errors": [], "actions": []},
            "benchmark": {"status": "MISSING", "closes": {}, "errors": []}}


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
    parser.add_argument("--learning", action="store_true",
                        help="add the display-only learning block (f-evo-loop step 1, grade D)")
    parser.add_argument("--museum", type=Path, default=DEFAULT_MUSEUM_PATH,
                        help="failure museum entries (learning block only, read only)")
    parser.add_argument("--epochs", type=Path, default=DEFAULT_EPOCHS_PATH,
                        help="gate rule epochs (learning block only, read only)")
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
    scored_load = journal["status"] == "OK" or (journal["status"] == "MISSING" and bool(compare["records"]))
    loaded_days = {"status": "NOT_READ", "days": []}
    learning_load = False
    if args.learning:
        try:
            loaded_days = load_decision_days(args.decisions_root)
            learning_load = journal["status"] != "CORRUPT"
            if learning_load:
                tickers += learning_symbols(loaded_days["days"])
        except Exception:  # noqa: BLE001 - the learning block reports the failure, the scores stay as they are
            loaded_days = {"status": "UNREADABLE", "days": []}
    loaded = load_inputs(tickers=tickers, closes_root=args.closes_root, calendar_path=args.calendar,
                         now=evaluation_as_of) if scored_load or learning_load else _no_inputs()
    # The scores see exactly what they saw before --learning existed; only close_histories may hold more symbols.
    inputs = loaded if scored_load else _no_inputs()
    report = score_journal(journal, evaluation_as_of=evaluation_as_of, ticket_records=compare["records"],
                           event_calendar=load_event_calendar(args.event_calendar),
                           decision_earnings=compare.get("earnings"), **{
        key: inputs[key] for key in ("calendar", "calendar_failure", "closes", "unverified", "benchmark",
                                     "corporate_actions")})
    report["ticket_sources"].update({"decisions_root_status": compare["status"], "errors": compare["errors"]})
    report["close_histories"] = loaded["close_histories"]
    if args.learning:
        report["learning"] = _learning_block(args=args, journal=journal, compare=compare, loaded_days=loaded_days,
                                             report=report, inputs=loaded, evaluation_as_of=evaluation_as_of)
    path = write_report(report, args.output_root, args.journal, now)
    print("\n".join(render_report(report)))
    if args.learning:
        print("\n".join(render_learning(report["learning"])))
    print(messages["score_path"].format(path=str(path)))
    return 2 if journal["status"] == "CORRUPT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
