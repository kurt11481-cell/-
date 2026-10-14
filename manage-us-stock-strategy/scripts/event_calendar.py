#!/usr/bin/env python3
"""Event exposure of an order ticket from the official event calendar (cold path, display and scoring only).

The event calendar (docs/claude/event-calendar.json, schema "event-calendar/1") lists dated official events. For a
ticket session this module says which events land before the fill (previous session close < landing <= the
session's core close), which land after the fill up to the next close (overnight), and which land within the
5-session scoring window. The fill time is always the session calendar's core_close_at (early closes included),
never a fixed 16:00.

Display and scoring only: nothing here is a gate, evidence, budget, size, price or decision input, and the auto-core
decide run does not read the event calendar. A missing or broken calendar is a status, never an exception.

Landing time (America/New_York, daylight saving applied):
  - excluded (None): kind market_holiday or options_expiration, tier C, status NOT_ANNOUNCED;
  - time_et set: event_date + time_et;
  - no time_et: report_date 09:00 ET (results that land overnight, before the U.S. open);
  - neither: None ("unplaced").

CLI (read only, writes no file, no network, no broker call):
  python manage-us-stock-strategy/scripts/event_calendar.py --decision <decision.json>
      [--event-calendar <path>] [--today-et YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
LOCALE_PATH = SKILL_ROOT / "assets/locales/portfolio-exposure-ko-KR.json"
DEFAULT_EVENT_CALENDAR = REPO_ROOT / "docs/claude/event-calendar.json"
SCHEMA = "event-calendar/1"
ET = ZoneInfo("America/New_York")
KINDS = ("macro_release", "central_bank", "earnings", "election", "options_expiration", "market_holiday")
TIERS = ("A", "B", "C")
STATUSES = ("VERIFIED", "REPORTED", "COMPUTED", "NOT_ANNOUNCED")
EXCLUDED_KINDS = ("market_holiday", "options_expiration")
EXCLUDED_TIERS = ("C",)
NOT_ANNOUNCED = "NOT_ANNOUNCED"
REPORT_TIME = time(9, 0)
SCORING_SESSIONS = 5
LIST_LIMIT = 4
TIME_ET = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")
TIMING_BEFORE_OPEN = "BEFORE_OPEN"
TIMING_AFTER_CLOSE = "AFTER_CLOSE"
SIDES = ("buy", "sell")
SHOWN_OWN_POSITIONS = ("before_fill", "overnight", "within_5", "unplaced")


def _day(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value) if len(value) == 10 else None
    except ValueError:
        return None


def _aware(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _row_errors(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["ROW_NOT_OBJECT"]
    errors = []
    if not isinstance(row.get("id"), str) or not row["id"].strip():
        errors.append("ID")
    if row.get("kind") not in KINDS:
        errors.append("KIND")
    if row.get("tier") not in TIERS:
        errors.append("TIER")
    if _day(row.get("event_date")) is None:
        errors.append("EVENT_DATE")
    if row.get("status") not in STATUSES:
        errors.append("STATUS")
    clock = row.get("time_et")
    if clock is not None and not (isinstance(clock, str) and TIME_ET.fullmatch(clock)):
        errors.append("TIME_ET")
    if row.get("report_date") is not None and _day(row.get("report_date")) is None:
        errors.append("REPORT_DATE")
    window = row.get("window")
    if window is not None:
        days = [_day(item) for item in window] if isinstance(window, list) and len(window) == 2 else [None]
        if None in days or days[0] > days[1]:
            errors.append("WINDOW")
    return errors


def load_event_calendar(path: Path | str) -> dict[str, Any]:
    """{status OK|MISSING|INVALID, sha256 (raw bytes), coverage_start, horizon_end, events, reasons}. Never raises.

    A broken row is left out and named in reasons (the file stays OK); a broken file is INVALID with no events."""
    result: dict[str, Any] = {"status": "MISSING", "sha256": None, "coverage_start": None, "horizon_end": None,
                              "events": [], "reasons": []}
    target = Path(path)
    try:
        raw = target.read_bytes()
    except FileNotFoundError:
        return {**result, "reasons": ["EVENT_CALENDAR_MISSING"]}
    except OSError as exc:
        return {**result, "status": "INVALID", "reasons": [f"EVENT_CALENDAR_UNREADABLE:{type(exc).__name__}"]}
    result["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return {**result, "status": "INVALID", "reasons": ["EVENT_CALENDAR_NOT_JSON"]}
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        return {**result, "status": "INVALID", "reasons": ["EVENT_CALENDAR_SCHEMA"]}
    reasons = []
    if not isinstance(document.get("events"), list):
        reasons.append("EVENT_CALENDAR_EVENTS_NOT_LIST")
    for key in ("coverage_start", "horizon_end"):
        if _day(document.get(key)) is None:
            reasons.append(f"EVENT_CALENDAR_{key.upper()}")
    if reasons:
        return {**result, "status": "INVALID", "reasons": reasons}
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(document["events"]):
        name = row.get("id") if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"] else f"#{index}"
        errors = _row_errors(row)
        if errors:
            reasons.append(f"EVENT_ROW_INVALID:{name}:{'+'.join(errors)}")
        elif row["id"] in seen:
            reasons.append(f"EVENT_ROW_DUPLICATE:{name}")
        else:
            seen.add(row["id"])
            events.append(dict(row))
    return {**result, "status": "OK", "coverage_start": document["coverage_start"],
            "horizon_end": document["horizon_end"], "events": events, "reasons": reasons}


def _placement(row: dict[str, Any]) -> tuple[datetime | None, str | None]:
    """(landing time in ET, why there is none: EXCLUDED | NO_TIME)."""
    if row.get("kind") in EXCLUDED_KINDS or row.get("tier") in EXCLUDED_TIERS or row.get("status") == NOT_ANNOUNCED:
        return None, "EXCLUDED"
    event_day = _day(row.get("event_date"))
    clock = row.get("time_et")
    if event_day is not None and isinstance(clock, str) and TIME_ET.fullmatch(clock):
        hour, minute = (int(part) for part in clock.split(":"))
        return datetime.combine(event_day, time(hour, minute), ET), None
    report_day = _day(row.get("report_date"))
    if report_day is not None:
        return datetime.combine(report_day, REPORT_TIME, ET), None
    return None, "NO_TIME"


def landing(row: dict[str, Any]) -> datetime | None:
    """When the event lands in prices (America/New_York), or None (excluded or unplaced)."""
    return _placement(row)[0]


def _session_rows(sessions: dict[str, Any]) -> dict[str, Any]:
    """Accepts the session calendar dict ({"sessions": {...}}) or its sessions mapping."""
    inner = sessions.get("sessions") if isinstance(sessions, dict) else None
    rows = inner if isinstance(inner, dict) else sessions
    return rows if isinstance(rows, dict) else {}


def _close(rows: dict[str, Any], session: str | None) -> datetime | None:
    row = rows.get(session) if session is not None else None
    return _aware(row.get("core_close_at")) if isinstance(row, dict) else None


def _bucket(moment: datetime, prev: datetime, fill: datetime, next_close: datetime | None,
            fifth_close: datetime | None) -> str:
    """before_fill | overnight | within_5 | later | earlier | unplaced (a boundary outside the session calendar)."""
    if moment <= prev:
        return "earlier"
    if moment <= fill:
        return "before_fill"
    if next_close is None:
        return "unplaced"
    if moment <= next_close:
        return "overnight"
    if fifth_close is None:
        return "unplaced"
    return "within_5" if moment <= fifth_close else "later"


def _own_earnings(record: Any, *, rows: dict[str, Any], prev_day: str, last_day: str, prev: datetime,
                  fill: datetime, next_close: datetime | None, fifth_close: datetime | None) -> dict[str, Any] | None:
    """The ticket symbol's own earnings (decision.json earnings_calendar[symbol]); None without a record.

    prev_day = the previous session's date (the ticket session's own date when it is the first calendar session)."""
    if not isinstance(record, dict):
        return None
    announced, timing = record.get("announcement_session"), record.get("timing")
    result = {"status": record.get("status"), "announcement_session": announced, "timing": timing}
    announced_day = _day(announced)
    moment: datetime | None = None
    if announced_day is not None and timing == TIMING_BEFORE_OPEN:
        moment = datetime.combine(announced_day, REPORT_TIME, ET)
    elif announced_day is not None and timing == TIMING_AFTER_CLOSE:
        closed = _close(rows, announced)
        moment = closed + timedelta(minutes=1) if closed is not None else None
    if moment is not None:
        return {**result, "position": _bucket(moment, prev, fill, next_close, fifth_close)}
    # No placeable time: only a date before the previous session or after the window is placed by its date; the
    # previous session's date or a non-session day up to the ticket session could land either side of prev.
    if announced_day is not None and announced < prev_day:
        return {**result, "position": "earlier"}
    if announced_day is not None and fifth_close is not None and announced > last_day:
        return {**result, "position": "later"}
    return {**result, "position": "unplaced"}


def _empty(status: str) -> dict[str, Any]:
    return {"status": status, "before_fill": [], "overnight": [], "within_5": [], "possible": [], "unplaced": [],
            "own_earnings": None}


def exposure(*, session: str, sessions: dict[str, Any], events: list[dict[str, Any]], coverage_start: str | None,
             horizon_end: str | None, earnings: Any = None) -> dict[str, Any]:
    """Event ids by position against the ticket session's fill (its core_close_at).

    prev = core close of the session before (or the session day 00:00 ET), F = the session's core close,
    F1 = the next session's, F5 = the fifth next session's.
      before_fill: prev < landing <= F   overnight: F < landing <= F1   within_5: F < landing <= F5 (null without F5)
      possible: NOT_ANNOUNCED rows whose window overlaps [session day, fifth next session day]
      unplaced: rows with neither time_et nor report_date whose event_date falls in the same range
    status OK | SESSION_UNKNOWN (empty lists) | NOT_COVERED (session before coverage_start, F5 after horizon_end
    or outside the session calendar; filled as far as computable)."""
    rows = _session_rows(sessions)
    fill = _close(rows, session) if _day(session) is not None else None
    if fill is None:
        return _empty("SESSION_UNKNOWN")
    ordered = sorted(day for day in rows if _day(day) is not None and _close(rows, day) is not None)
    index = ordered.index(session)
    prev = (_close(rows, ordered[index - 1]) if index > 0
            else datetime.combine(date.fromisoformat(session), time(0, 0), ET))
    next_close = _close(rows, ordered[index + 1]) if index + 1 < len(ordered) else None
    fifth = ordered[index + SCORING_SESSIONS] if index + SCORING_SESSIONS < len(ordered) else None
    fifth_close = _close(rows, fifth) if fifth is not None else None
    last_day = ordered[min(index + SCORING_SESSIONS, len(ordered) - 1)]
    covered = not ((coverage_start is not None and session < coverage_start) or fifth is None
                   or (horizon_end is not None and fifth > horizon_end))
    result = _empty("OK" if covered else "NOT_COVERED")
    result["within_5"] = [] if fifth_close is not None else None
    placed: list[tuple[datetime, str, str]] = []
    possible: list[tuple[str, str]] = []
    unplaced: list[tuple[str, str]] = []
    for row in events:
        moment, why = _placement(row)
        if moment is not None:
            placed.append((moment, row["id"], _bucket(moment, prev, fill, next_close, fifth_close)))
            continue
        excluded_kind = row.get("kind") in EXCLUDED_KINDS or row.get("tier") in EXCLUDED_TIERS
        window = row.get("window")
        if not excluded_kind and row.get("status") == NOT_ANNOUNCED and isinstance(window, list) and len(window) == 2:
            if window[0] <= last_day and window[1] >= session:
                possible.append((window[0], row["id"]))
        elif why == "NO_TIME" and session <= row.get("event_date", "") <= last_day:
            unplaced.append((row["event_date"], row["id"]))
    for moment, name, bucket in sorted(placed):
        if bucket == "before_fill":
            result["before_fill"].append(name)
        elif bucket == "overnight":
            result["overnight"].append(name)
        if bucket in ("overnight", "within_5") and result["within_5"] is not None:
            result["within_5"].append(name)
    result["possible"] = [name for _start, name in sorted(possible)]
    result["unplaced"] = [name for _start, name in sorted(unplaced)]
    prev_day = ordered[index - 1] if index > 0 else session
    result["own_earnings"] = _own_earnings(earnings, rows=rows, prev_day=prev_day, last_day=last_day, prev=prev,
                                           fill=fill, next_close=next_close, fifth_close=fifth_close)
    return result


def _messages() -> dict[str, str]:
    return json.loads(LOCALE_PATH.read_text(encoding="utf-8-sig"))["messages"]


def _labels(ids: list[str], events: list[dict[str, Any]], messages: dict[str, str]) -> str:
    names = {row.get("id"): row.get("label") for row in events if isinstance(row, dict)}
    shown = [names.get(name) if isinstance(names.get(name), str) and names.get(name) else name for name in ids]
    text = messages["event_label_join"].join(shown[:LIST_LIMIT])
    if len(shown) > LIST_LIMIT:
        text = messages["event_more"].format(labels=text, count=len(shown) - LIST_LIMIT)
    return text


def exposure_line(side: str, exp: dict[str, Any], events: list[dict[str, Any]]) -> str:
    """One Korean display line (buy: events after the fill are carried; sell: they are avoided)."""
    messages = _messages()
    prefix = messages["event_line_prefix"]
    status = exp.get("status") if isinstance(exp, dict) else None
    if status not in ("OK", "NOT_COVERED"):
        return prefix + messages["event_check_needed"].format(reason=status or "EXPOSURE_MISSING")
    if side not in SIDES:
        return prefix + messages["event_check_needed"].format(reason="TICKET_SIDE_INVALID")
    parts = []
    if exp.get("before_fill"):
        parts.append(messages["event_before_fill"].format(labels=_labels(exp["before_fill"], events, messages)))
    if exp.get("overnight"):
        parts.append(messages[f"event_overnight_{side}"].format(labels=_labels(exp["overnight"], events, messages)))
    if exp.get("possible"):
        parts.append(messages["event_possible"].format(labels=_labels(exp["possible"], events, messages)))
    own = exp.get("own_earnings")
    if isinstance(own, dict) and own.get("position") in SHOWN_OWN_POSITIONS:
        day = _day(own.get("announcement_session"))
        timing = {TIMING_BEFORE_OPEN: "event_timing_before_open", TIMING_AFTER_CLOSE: "event_timing_after_close"}.get(
            own.get("timing"), "event_timing_unknown")
        parts.append(messages["event_own_earnings"].format(
            date=day.strftime("%m/%d") if day is not None else messages["event_own_date_unknown"],
            timing=messages[timing], position=messages[f"event_own_{own['position']}"]))
    line = prefix + (messages["event_separator"].join(parts) if parts else messages["event_none"])
    if status == "NOT_COVERED":
        line += messages["event_not_covered"]
    return line


def _default_session_loader(now: datetime) -> dict[str, Any]:
    from run_portfolio_exposure_review import load_session_calendar  # noqa: PLC0415 - heavy import only when run

    calendar, _authority = load_session_calendar(None, now)
    return calendar


def _load_decision(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None, "DECISION_MISSING"
    except (OSError, UnicodeDecodeError, ValueError):
        return None, "DECISION_NOT_JSON"
    if not isinstance(document, dict):
        return None, "DECISION_NOT_OBJECT"
    return document, None


def _valid_tickets(decision: dict[str, Any]) -> list[dict[str, Any]]:
    tickets = decision.get("tickets")
    return [ticket for ticket in (tickets if isinstance(tickets, list) else []) if isinstance(ticket, dict)
            and all(isinstance(ticket.get(key), str) and ticket.get(key) for key in ("ticket_id", "ticker", "side",
                                                                                      "session"))]


def build_view(*, decision: dict[str, Any], event_calendar: dict[str, Any], session_calendar: dict[str, Any] | None,
               session_failure: str | None, today_et: str) -> dict[str, Any]:
    """The pre-open display JSON for one decision (pure)."""
    events = event_calendar["events"]
    buy_session = decision.get("buy_session") if isinstance(decision.get("buy_session"), str) else None
    earnings = decision.get("earnings_calendar") if isinstance(decision.get("earnings_calendar"), dict) else {}

    def one(session: Any, record: Any) -> dict[str, Any]:
        if session_calendar is None:
            return _empty("SESSION_CALENDAR_UNAVAILABLE")
        if event_calendar["status"] != "OK":
            return _empty(f"EVENT_CALENDAR_{event_calendar['status']}")
        return exposure(session=session, sessions=session_calendar, events=events,
                        coverage_start=event_calendar["coverage_start"], horizon_end=event_calendar["horizon_end"],
                        earnings=record)

    status = ("SESSION_CALENDAR_UNAVAILABLE" if session_calendar is None else
              "OK" if event_calendar["status"] == "OK" else f"EVENT_CALENDAR_{event_calendar['status']}")
    view: dict[str, Any] = {"status": status}
    if session_failure is not None:
        view["reason"] = session_failure
    session_exposure = one(buy_session, None)
    view.update({
        "decision_buy_session": buy_session, "today_et": today_et, "session_match": buy_session == today_et,
        "session": {"exposure": session_exposure, "line_buy": exposure_line("buy", session_exposure, events),
                    "line_sell": exposure_line("sell", session_exposure, events)},
        "tickets": []})
    for ticket in _valid_tickets(decision):
        ticket_exposure = one(ticket["session"], earnings.get(ticket["ticker"]))
        view["tickets"].append({"ticket_id": ticket["ticket_id"], "ticker": ticket["ticker"], "side": ticket["side"],
                                "mode": ticket.get("mode"), "session": ticket["session"], "exposure": ticket_exposure,
                                "line": exposure_line(ticket["side"], ticket_exposure, events)})
    return view


def _calendar_block(loaded: dict[str, Any]) -> dict[str, Any]:
    return {key: loaded[key] for key in ("status", "sha256", "coverage_start", "horizon_end", "reasons")}


def main(argv: list[str] | None = None,
         session_loader: Callable[[datetime], dict[str, Any]] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Event exposure of today's order tickets (read only, display only)")
    parser.add_argument("--decision", type=Path, required=True, help="auto-core decision.json")
    parser.add_argument("--event-calendar", type=Path, default=DEFAULT_EVENT_CALENDAR)
    parser.add_argument("--today-et", default=None, help="YYYY-MM-DD; default today in America/New_York")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    today_et = args.today_et if args.today_et is not None else now.astimezone(ET).date().isoformat()
    if _day(today_et) is None:
        parser.error("--today-et must be YYYY-MM-DD")
    loaded = load_event_calendar(args.event_calendar)
    decision, decision_failure = _load_decision(args.decision)
    if decision is None:
        view: dict[str, Any] = {"status": "DECISION_UNAVAILABLE", "reason": decision_failure,
                                "decision_buy_session": None, "today_et": today_et, "session_match": False,
                                "session": None, "tickets": []}
    else:
        session_calendar: dict[str, Any] | None = None
        failure: str | None = None
        try:
            session_calendar = (session_loader or _default_session_loader)(now)
        except Exception as exc:  # noqa: BLE001 - a display tool reports a status and never stops the check
            failure = str(exc) or type(exc).__name__
        if session_calendar is not None and not _session_rows(session_calendar):
            session_calendar, failure = None, "SESSION_CALENDAR_EMPTY"
        view = build_view(decision=decision, event_calendar=loaded, session_calendar=session_calendar,
                          session_failure=failure, today_et=today_et)
    view["event_calendar"] = _calendar_block(loaded)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(view, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
