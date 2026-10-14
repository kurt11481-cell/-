"""Event exposure from the official event calendar (event-ctx4, display and scoring only).

Synthetic inputs and temp folders only: the repository's event calendar, decision files and the operating session
calendar are never read here (the session calendar is a fixture built in this file and injected into the CLI).
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import event_calendar as ec  # noqa: E402
from validate_holding_card import forbidden_keys  # noqa: E402

ET = ZoneInfo("America/New_York")
HOLIDAYS = {"2026-11-26", "2026-12-25"}
EARLY = {"2026-11-27", "2026-12-24"}


def session_calendar(start: str = "2026-10-01", end: str = "2026-12-31") -> dict:
    """A fixture shaped like load_session_calendar output: 16:00 ET closes, 13:00 ET on early-close days."""
    sessions, cursor = {}, date.fromisoformat(start)
    while cursor <= date.fromisoformat(end):
        day = cursor.isoformat()
        if cursor.weekday() < 5 and day not in HOLIDAYS:
            close = datetime.combine(cursor, time(13 if day in EARLY else 16, 0), ET)
            sessions[day] = {"session_date": day, "core_open_at": datetime.combine(cursor, time(9, 30), ET).isoformat(),
                             "core_close_at": close.isoformat(), "close_type": "EARLY" if day in EARLY else "REGULAR"}
        cursor += timedelta(days=1)
    return {"sessions": sessions}


def event(name: str, *, kind: str = "macro_release", tier: str = "A", day: str, at: str | None = None,
          report: str | None = None, status: str = "VERIFIED", label: str | None = None, **extra: object) -> dict:
    return {"id": name, "kind": kind, "tier": tier, "label": label or name.upper(), "event_date": day, "time_et": at,
            "time_kst": None, "report_date": report, "status": status, "source_url": "https://example.test/",
            "result_url": None, **extra}


EVENTS = [
    event("fomc", kind="central_bank", day="2026-10-28", at="14:00", report="2026-10-29", label="FOMC"),
    event("msft", kind="earnings", day="2026-10-28", at="16:05", report="2026-10-29", label="MSFT"),
    event("googl", kind="earnings", day="2026-10-28", at="16:30", report="2026-10-29", label="GOOGL"),
    event("gdp", tier="B", day="2026-10-29", at="08:30", report="2026-10-29", label="GDP"),
    event("boj", kind="central_bank", tier="B", day="2026-10-29", report="2026-10-30", label="BOJ"),
    event("aapl", kind="earnings", day="2026-11-02", at="16:30", report="2026-11-03", status="REPORTED", label="AAPL"),
    event("vote", kind="election", day="2026-11-03", report="2026-11-04", label="VOTE"),
    event("amzn", kind="earnings", day="2026-10-29", status="NOT_ANNOUNCED", label="AMZN",
          window=["2026-10-26", "2026-10-30"]),
    event("opex", kind="options_expiration", tier="C", day="2026-10-30", at="16:00", report="2026-10-30",
          status="COMPUTED"),
    event("thanks", kind="market_holiday", tier="B", day="2026-11-26", report="2026-11-26"),
    event("minor", tier="C", day="2026-10-28", at="10:00", report="2026-10-28"),
    event("nodate", tier="B", day="2026-10-29", label="NODATE"),
    event("noon", tier="B", day="2026-11-27", at="12:00", report="2026-11-27", label="NOON"),
    event("late", tier="B", day="2026-11-27", at="14:00", report="2026-11-27", label="LATE"),
]
CAL = session_calendar()


def expose(session: str, *, events: list | None = None, earnings: object = None, coverage: str = "2026-10-14",
           horizon: str = "2026-12-31") -> dict:
    return ec.exposure(session=session, sessions=CAL, events=EVENTS if events is None else events,
                       coverage_start=coverage, horizon_end=horizon, earnings=earnings)


class LandingTests(unittest.TestCase):  # T1
    def test_landing_rules(self) -> None:
        by_id = {row["id"]: row for row in EVENTS}
        self.assertEqual(ec.landing(by_id["fomc"]), datetime(2026, 10, 28, 14, 0, tzinfo=ET))
        self.assertEqual(ec.landing(by_id["boj"]), datetime(2026, 10, 30, 9, 0, tzinfo=ET))  # report_date 09:00 ET
        for name in ("amzn", "opex", "thanks", "minor", "nodate"):
            with self.subTest(name=name):
                self.assertIsNone(ec.landing(by_id[name]))

    def test_daylight_saving_is_applied(self) -> None:
        by_id = {row["id"]: row for row in EVENTS}
        self.assertEqual(ec.landing(by_id["fomc"]).utcoffset(), timedelta(hours=-4))
        self.assertEqual(ec.landing(by_id["aapl"]).astimezone(timezone.utc),
                         datetime(2026, 11, 2, 21, 30, tzinfo=timezone.utc))  # EST after 2026-11-01


class ExposureTests(unittest.TestCase):  # T2, T3
    def test_session_before_the_fomc_and_earnings_night(self) -> None:
        found = expose("2026-10-28")
        self.assertEqual(found["status"], "OK")
        self.assertEqual(found["before_fill"], ["fomc"])
        self.assertEqual(found["overnight"], ["msft", "googl", "gdp"])
        self.assertIn("boj", found["within_5"])
        self.assertNotIn("boj", found["overnight"])
        self.assertEqual(found["within_5"], ["msft", "googl", "gdp", "boj", "aapl", "vote"])
        self.assertEqual(found["possible"], ["amzn"])
        self.assertEqual(found["unplaced"], ["nodate"])
        self.assertNotIn("minor", json.dumps(found))
        self.assertNotIn("opex", json.dumps(found))

    def test_next_session_carries_the_overnight_results(self) -> None:
        found = expose("2026-10-29")
        self.assertEqual(found["before_fill"], ["msft", "googl", "gdp"])  # after the prior close, before this close
        self.assertEqual(found["overnight"], ["boj"])

    def test_after_daylight_saving_ends(self) -> None:
        found = expose("2026-11-02")
        self.assertEqual(found["overnight"], ["aapl"])  # 16:30 EST is after the 16:00 EST close
        self.assertIn("vote", found["within_5"])
        self.assertNotIn("vote", found["overnight"])
        self.assertEqual(expose("2026-11-03")["overnight"], ["vote"])

    def test_early_close_is_the_fill_time(self) -> None:
        found = expose("2026-11-27")
        self.assertEqual(found["before_fill"], ["noon"])
        self.assertEqual(found["overnight"], ["late"])  # 14:00 ET is after the 13:00 ET early close
        before = expose("2026-11-25")  # the next session is 11/27 (11/26 has no session)
        self.assertEqual(before["overnight"], ["noon"])
        self.assertIn("late", before["within_5"])
        self.assertNotIn("thanks", json.dumps(before))

    def test_unknown_and_uncovered_sessions(self) -> None:
        unknown = expose("2026-11-26")
        self.assertEqual(unknown["status"], "SESSION_UNKNOWN")
        self.assertEqual((unknown["before_fill"], unknown["overnight"], unknown["within_5"]), ([], [], []))
        self.assertEqual(expose("2026-12-23")["status"], "OK")  # the fifth next session is 12/31
        late = expose("2026-12-24")
        self.assertEqual((late["status"], late["within_5"]), ("NOT_COVERED", None))
        early = expose("2026-10-13")
        self.assertEqual(early["status"], "NOT_COVERED")  # before coverage_start, filled anyway
        self.assertEqual(expose("2026-12-21", horizon="2026-12-24")["status"], "NOT_COVERED")


class OwnEarningsTests(unittest.TestCase):  # T8
    def own(self, session: str, record: object) -> object:
        return expose(session, events=[], earnings=record)["own_earnings"]

    def test_positions(self) -> None:
        def record(day: str, timing: str | None) -> dict:
            found = {"status": "VERIFIED", "announcement_session": day, "source_kind": "IR", "source_url": "x"}
            return found if timing is None else {**found, "timing": timing}

        self.assertEqual(self.own("2026-10-28", record("2026-10-28", "AFTER_CLOSE"))["position"], "overnight")
        self.assertEqual(self.own("2026-10-28", record("2026-10-29", "BEFORE_OPEN"))["position"], "overnight")
        self.assertEqual(self.own("2026-10-28", record("2026-10-28", "BEFORE_OPEN"))["position"], "before_fill")
        self.assertEqual(self.own("2026-10-28", record("2026-10-30", "AFTER_CLOSE"))["position"], "within_5")
        self.assertEqual(self.own("2026-10-28", record("2026-12-01", "AFTER_CLOSE"))["position"], "later")
        self.assertEqual(self.own("2026-10-28", record("2026-10-29", None))["position"], "unplaced")
        self.assertIsNone(self.own("2026-10-28", None))
        # AFTER_CLOSE is the announcement session's core close + 1 minute: 13:01 ET on an early-close day.
        self.assertEqual(self.own("2026-11-25", record("2026-11-27", "AFTER_CLOSE"))["position"], "within_5")
        self.assertEqual(self.own("2026-11-25", record("2026-11-25", "AFTER_CLOSE"))["position"], "overnight")

    def test_the_line_names_own_earnings_for_both_sides(self) -> None:
        found = expose("2026-10-28", events=[], earnings={"status": "VERIFIED", "announcement_session": "2026-10-28",
                                                          "timing": "AFTER_CLOSE"})
        suffix = "자기 실적 10/28(장 후) — 밤새"
        self.assertTrue(ec.exposure_line("sell", found, []).endswith(suffix))
        self.assertTrue(ec.exposure_line("buy", found, []).endswith(suffix))
        unplaced = expose("2026-10-28", events=[], earnings={"status": "VERIFIED", "announcement_session": "2026-10-29"})
        self.assertIn("시각 미정", ec.exposure_line("buy", unplaced, []))
        later = expose("2026-10-28", events=[], earnings={"status": "VERIFIED", "announcement_session": "2026-12-01",
                                                          "timing": "AFTER_CLOSE"})
        self.assertNotIn("자기 실적", ec.exposure_line("buy", later, []))

    def test_no_timing_on_the_previous_session_is_unplaced(self) -> None:
        # 10/27 is the previous session: before or after its close cannot be told without a timing.
        found = expose("2026-10-28", events=[], earnings={"status": "VERIFIED", "announcement_session": "2026-10-27"})
        self.assertEqual(found["own_earnings"]["position"], "unplaced")
        line = ec.exposure_line("buy", found, [])
        self.assertIn("시각 미정", line)
        self.assertIn("시점 확인 필요", line)
        # A non-session day between the previous session (10/23) and the ticket session (10/26) is unplaced too.
        weekend = expose("2026-10-26", events=[], earnings={"status": "VERIFIED", "announcement_session": "2026-10-24"})
        self.assertEqual(weekend["own_earnings"]["position"], "unplaced")

    def test_no_timing_before_the_previous_session_is_earlier(self) -> None:
        found = expose("2026-10-28", events=[], earnings={"status": "VERIFIED", "announcement_session": "2026-10-26"})
        self.assertEqual(found["own_earnings"]["position"], "earlier")
        self.assertNotIn("자기 실적", ec.exposure_line("buy", found, []))


class LineTests(unittest.TestCase):  # T4
    def test_buy_carries_and_sell_avoids(self) -> None:
        found = expose("2026-10-28")
        self.assertEqual(ec.exposure_line("buy", found, EVENTS),
                         "이벤트(표시만): 체결 전 반영 — FOMC"
                         " · 체결 뒤 떠안음(다음 종가까지)"
                         " — MSFT·GOOGL·GDP · 발표일 미정 — AMZN")
        sell = ec.exposure_line("sell", found, EVENTS)
        self.assertIn("체결 뒤 피함(다음 종가까지) — MSFT", sell)
        self.assertNotIn("떠안음", sell)

    def test_more_than_four_none_and_uncovered(self) -> None:
        many = {**ec._empty("OK"), "overnight": ["a", "b", "c", "d", "e", "f"]}
        self.assertTrue(ec.exposure_line("buy", many, []).endswith("a·b·c·d 외 2건"))
        empty = ec._empty("OK")
        self.assertEqual(ec.exposure_line("buy", empty, []), "이벤트(표시만): 해당 없음")
        uncovered = ec.exposure_line("buy", ec._empty("NOT_COVERED"), [])
        self.assertTrue(uncovered.endswith(" · 일정표 범위 밖 — 확인 필요"))
        for status in ("SESSION_UNKNOWN", "EVENT_CALENDAR_MISSING", "EVENT_CALENDAR_INVALID"):
            with self.subTest(status=status):
                self.assertEqual(ec.exposure_line("sell", ec._empty(status), []),
                                 f"이벤트(표시만): 확인 필요({status})")


class LoadTests(unittest.TestCase):  # T5
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="event_calendar_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "event-calendar.json"

    def write(self, document: object) -> dict:
        self.path.write_text(document if isinstance(document, str) else json.dumps(document), encoding="utf-8")
        return ec.load_event_calendar(self.path)

    def test_missing_invalid_and_broken_rows(self) -> None:
        self.assertEqual(ec.load_event_calendar(self.path)["status"], "MISSING")
        self.assertEqual(self.write("{broken")["status"], "INVALID")
        good = {"schema": "event-calendar/1", "coverage_start": "2026-10-14", "horizon_end": "2026-12-31",
                "events": EVENTS[:2]}
        self.assertEqual(self.write({**good, "schema": "event-calendar/2"})["status"], "INVALID")
        self.assertEqual(self.write({**good, "events": {}})["status"], "INVALID")
        self.assertEqual(self.write({**good, "horizon_end": "end"})["status"], "INVALID")
        rows = [EVENTS[0], {**EVENTS[1], "event_date": "10/28"}, {**EVENTS[2], "kind": None},
                {key: value for key, value in EVENTS[3].items() if key != "status"}, EVENTS[0], "row"]
        loaded = self.write({**good, "events": rows})
        self.assertEqual(loaded["status"], "OK")
        self.assertEqual([row["id"] for row in loaded["events"]], ["fomc"])
        self.assertEqual(len(loaded["reasons"]), 5)
        self.assertTrue(any("msft" in reason for reason in loaded["reasons"]))
        self.assertTrue(any("EVENT_ROW_DUPLICATE:fomc" == reason for reason in loaded["reasons"]))
        self.assertEqual(len(loaded["sha256"]), 64)


class CliTests(unittest.TestCase):  # T7
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="event_cli_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.decision = self.tmp / "decision.json"
        self.calendar = self.tmp / "event-calendar.json"
        self.calendar.write_text(json.dumps({"schema": "event-calendar/1", "coverage_start": "2026-10-14",
                                             "horizon_end": "2026-12-31", "events": EVENTS}), encoding="utf-8")
        self.decision.write_text(json.dumps({
            "buy_session": "2026-10-28", "decision_mode": "compare",
            "earnings_calendar": {"AAA": {"status": "VERIFIED", "announcement_session": "2026-10-28",
                                          "timing": "AFTER_CLOSE", "source_kind": "IR", "source_url": "x"}},
            "tickets": [{"ticket_id": "T-BUY", "ticker": "AAA", "side": "buy", "mode": "compare",
                         "session": "2026-10-28"},
                        {"ticket_id": "T-SELL", "ticker": "BBB", "side": "sell", "mode": "compare",
                         "session": "2026-10-28"},
                        {"ticket_id": "", "ticker": "CCC", "side": "buy", "session": "2026-10-28"}]}),
            encoding="utf-8")

    def snapshot(self) -> dict:
        return {str(path): path.read_bytes() for path in sorted(self.tmp.rglob("*")) if path.is_file()}

    def run_cli(self, *args: str, loader=lambda now: CAL) -> tuple[int, dict]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = ec.main(list(args), session_loader=loader)
        return code, json.loads(buffer.getvalue())

    def test_view_for_todays_tickets_writes_nothing(self) -> None:
        before = self.snapshot()
        code, view = self.run_cli("--decision", str(self.decision), "--event-calendar", str(self.calendar),
                                  "--today-et", "2026-10-28")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(code, 0)
        self.assertEqual((view["status"], view["decision_buy_session"], view["today_et"], view["session_match"]),
                         ("OK", "2026-10-28", "2026-10-28", True))
        self.assertEqual(set(view["event_calendar"]), {"status", "sha256", "coverage_start", "horizon_end", "reasons"})
        self.assertEqual(view["session"]["exposure"]["overnight"], ["msft", "googl", "gdp"])
        self.assertIn("떠안음", view["session"]["line_buy"])
        self.assertIn("피함", view["session"]["line_sell"])
        self.assertEqual([(row["ticket_id"], row["side"]) for row in view["tickets"]], [("T-BUY", "buy"),
                                                                                         ("T-SELL", "sell")])
        buy, sell = view["tickets"]
        self.assertEqual(buy["exposure"]["own_earnings"]["position"], "overnight")
        self.assertIn("자기 실적 10/28", buy["line"])
        self.assertIsNone(sell["exposure"]["own_earnings"])
        self.assertIn("피함", sell["line"])
        self.assertEqual(forbidden_keys(view), [])

        def keys(value: object) -> list[str]:
            if isinstance(value, dict):
                return list(value) + [name for child in value.values() for name in keys(child)]
            return [name for child in value for name in keys(child)] if isinstance(value, list) else []

        for name in keys(view):
            for word in ("stop", "limit", "qty", "price"):
                self.assertNotIn(word, name)

    def test_failures_are_statuses_with_exit_zero(self) -> None:
        code, view = self.run_cli("--decision", str(self.tmp / "absent.json"), "--event-calendar", str(self.calendar))
        self.assertEqual((code, view["status"], view["reason"]), (0, "DECISION_UNAVAILABLE", "DECISION_MISSING"))

        def broken(now: datetime) -> dict:
            raise ValueError("SESSION_CALENDAR_UNAVAILABLE:TEST")

        code, view = self.run_cli("--decision", str(self.decision), "--event-calendar", str(self.calendar),
                                  loader=broken)
        self.assertEqual((code, view["status"]), (0, "SESSION_CALENDAR_UNAVAILABLE"))
        self.assertIn("TEST", view["reason"])
        self.assertEqual({row["exposure"]["status"] for row in view["tickets"]}, {"SESSION_CALENDAR_UNAVAILABLE"})
        code, view = self.run_cli("--decision", str(self.decision), "--event-calendar", str(self.tmp / "none.json"))
        self.assertEqual((code, view["status"], view["event_calendar"]["status"]),
                         (0, "EVENT_CALENDAR_MISSING", "MISSING"))
        self.assertIn("EVENT_CALENDAR_MISSING", view["tickets"][0]["line"])

    def test_only_argument_errors_exit_two(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            ec.main(["--decision", str(self.decision), "--today-et", "10/28"], session_loader=lambda now: CAL)
        self.assertEqual(raised.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            ec.main([], session_loader=lambda now: CAL)
        self.assertEqual(raised.exception.code, 2)


class HygieneTests(unittest.TestCase):  # J-g
    def test_script_is_ascii_and_writes_nothing(self) -> None:
        for name in ("event_calendar.py", "score_decision_journal.py"):
            with self.subTest(name=name):
                (SKILL_ROOT / "scripts" / name).read_bytes().decode("ascii")
        tree = ast.parse((SKILL_ROOT / "scripts/event_calendar.py").read_text(encoding="utf-8"))
        self.assertEqual(sorted({node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
                                 and node.attr in {"write_text", "write_bytes", "rename", "unlink", "mkdir",
                                                   "touch", "truncate"}}), [])
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        modules |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertFalse({name for name in modules if name and name.startswith("auto_core")})


if __name__ == "__main__":
    unittest.main()
