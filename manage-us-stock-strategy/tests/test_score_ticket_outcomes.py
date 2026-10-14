"""Auto-core ticket scoring in the read-only journal scorer (score-fix 2026-10-12).

Synthetic inputs and temp folders only. The real journal, decide output, state and policy files are never touched.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import portfolio_review_journal as journal_module  # noqa: E402
import score_decision_journal as scorer  # noqa: E402
from validate_holding_card import forbidden_keys  # noqa: E402


def weekdays(start: str, count: int) -> list[str]:
    days, cursor = [], date.fromisoformat(start)
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days


SESSIONS = weekdays("2026-10-01", 70)
CALENDAR = {"sessions": {day: {"core_close_at": f"{day}T20:00:00+00:00"} for day in SESSIONS},
            "identity": {"calendar_version": "test", "calendar_sha256": "0" * 64,
                         "coverage_start": SESSIONS[0], "coverage_end": SESSIONS[-1], "authority_status": "ACTIVE"}}
SESSION = SESSIONS[2]  # the ticket session (2026-10-05)
S5, S20 = SESSIONS[7], SESSIONS[22]
NO_ACTIONS = {"status": "MISSING", "sha256": None, "errors": [], "actions": []}
NO_SPY = {"status": "MISSING", "closes": {}, "errors": []}


def after(session: str) -> datetime:
    return datetime.fromisoformat(f"{session}T21:00:00+00:00")


def closes_with(**overrides: dict[str, str]) -> dict[str, dict[str, str]]:
    base = {symbol: {day: "100" for day in SESSIONS} for symbol in ("AAA", "BBB")}
    base["AAA"][S5] = "110"
    base["AAA"][S20] = "90"
    for symbol, values in overrides.items():
        base[symbol].update(values)
    return base


def ticket_entry(ticket_id: str, *, side: str = "buy", cap: str = "101", size: int = 10, session: str = SESSION,
                 ticker: str = "AAA") -> dict:
    return {"entry_type": "order_ticket", "sequence": 0, "payload": {
        "ticket_id": ticket_id, "ticker": ticker, "side": side, "price": cap, "qty": size, "buy_session": session}}


def outcome_entry(ticket_id: str, state: str, *, filled: int = 0, average: str | None = None) -> dict:
    return {"entry_type": "ticket_outcome", "sequence": 0, "payload": {
        "ticket_id": ticket_id, "ticker": "AAA", "side": "buy", "outcome_state": state, "filled_qty": filled,
        "average_fill_price": average}}


def compare_ticket(ticket_id: str, *, side: str = "buy", cap: float = 101.0, size: int = 10,
                   session: str = SESSION, ticker: str = "AAA") -> dict:
    return {"ticket_id": ticket_id, "mode": "compare", "ticker": ticker, "side": side, "type": "LOC", "price": cap,
            "qty": size, "session": session}


def synthetic_journal(entries: list[dict]) -> dict:
    return {"status": "OK", "entries": entries, "errors": [], "head_sha256": "0" * 64}


def score(entries: list[dict] | None = None, *, records: list[dict] | None = None, closes: dict | None = None,
          benchmark: dict | None = None, corporate: dict | None = None,
          evaluation_as_of: datetime | None = None) -> dict:
    return scorer.score_journal(
        synthetic_journal(entries or []), calendar=CALENDAR, closes=closes if closes is not None else closes_with(),
        unverified={}, benchmark=benchmark or NO_SPY, corporate_actions=corporate or NO_ACTIONS,
        evaluation_as_of=evaluation_as_of or after(S20), ticket_records=records)


def row_of(report: dict, ticket_id: str) -> dict:
    return next(row for row in report["ticket_results"] if row["ticket_id"] == ticket_id)


def horizon(items: list[dict], sessions: int) -> dict:
    return next(item for item in items if item["horizon_sessions"] == sessions)


class CounterfactualFillTests(unittest.TestCase):
    def test_buy_fills_when_the_session_close_is_at_or_below_the_cap(self) -> None:  # T6
        report = score([ticket_entry("T-UP", cap="101"), ticket_entry("T-EQ", cap="100"),
                        ticket_entry("T-LOW", cap="99")])
        filled = row_of(report, "T-UP")
        self.assertEqual((filled["would_fill"], filled["start_basis"], filled["evidence_grade"]),
                         (True, "TICKET_SESSION_CLOSE", "D"))
        self.assertEqual(horizon(filled["horizons"], 5)["vs_no_action"], "0.100000")
        self.assertEqual(horizon(filled["horizons"], 20)["vs_no_action"], "-0.100000")
        self.assertTrue(row_of(report, "T-EQ")["would_fill"])
        missed = row_of(report, "T-LOW")
        item = horizon(missed["horizons"], 5)
        self.assertEqual((missed["would_fill"], item["status"], item["vs_no_action"], item["reason"]),
                         (False, "SCORED", "0.000000", "NOT_FILLED_AT_CAP"))
        self.assertEqual(item["vs_benchmark"]["status"], "NOT_APPLICABLE")
        self.assertNotIn("vs_cash", item)

    def test_sell_fills_when_the_session_close_is_at_or_above_the_cap_and_the_sign_flips(self) -> None:  # T7
        report = score([ticket_entry("S-LOW", side="sell", cap="99"), ticket_entry("S-EQ", side="sell", cap="100"),
                        ticket_entry("S-UP", side="sell", cap="101")])
        filled = row_of(report, "S-LOW")
        self.assertTrue(filled["would_fill"])
        self.assertEqual(horizon(filled["horizons"], 5)["vs_no_action"], "-0.100000")  # sold before a +10% move
        self.assertEqual(horizon(filled["horizons"], 20)["vs_no_action"], "0.100000")  # sold before a -10% move
        self.assertTrue(row_of(report, "S-EQ")["would_fill"])
        missed = row_of(report, "S-UP")
        self.assertEqual((missed["would_fill"], horizon(missed["horizons"], 5)["vs_no_action"]), (False, "0.000000"))

    def test_a_ticket_session_that_has_not_closed_is_pending(self) -> None:  # T8
        just_before = datetime.fromisoformat(f"{SESSION}T19:59:59+00:00")
        row = row_of(score([ticket_entry("T-1")], evaluation_as_of=just_before), "T-1")
        self.assertIsNone(row["would_fill"])
        self.assertEqual({item["status"] for item in row["horizons"]}, {"PENDING"})
        self.assertEqual(horizon(row["horizons"], 5)["remaining_sessions"], 5)
        # After the session close but before the day-5 close: the fill is known, the score is not.
        row = row_of(score([ticket_entry("T-1")], evaluation_as_of=after(SESSION)), "T-1")
        self.assertTrue(row["would_fill"])
        self.assertEqual(horizon(row["horizons"], 5)["status"], "PENDING")

    def test_spy_is_reference_only_and_missing_data_is_not_scorable(self) -> None:
        spy = {"status": "OK", "closes": {**{day: "400" for day in SESSIONS}, S5: "404"}, "errors": []}
        item = horizon(row_of(score([ticket_entry("T-1")], benchmark=spy), "T-1")["horizons"], 5)
        self.assertEqual((item["vs_benchmark"]["label"], item["vs_benchmark"]["value"]), ("REFERENCE_ONLY", "0.090000"))
        gap = closes_with(AAA={SESSION: ""})
        row = row_of(score([ticket_entry("T-1")], closes=gap), "T-1")
        self.assertIsNone(row["would_fill"])
        self.assertEqual(horizon(row["horizons"], 5)["reason"], "START_CLOSE_MISSING")
        outside = row_of(score([ticket_entry("T-1", session="2026-09-30")]), "T-1")
        self.assertEqual(horizon(outside["horizons"], 5)["reason"], "TICKET_SESSION_NOT_IN_CALENDAR")
        no_calendar = scorer.score_journal(
            synthetic_journal([ticket_entry("T-1")]), calendar=None, calendar_failure="TEST", closes=closes_with(),
            unverified={}, benchmark=NO_SPY, corporate_actions=NO_ACTIONS, evaluation_as_of=after(S20))
        self.assertEqual({item["reason"] for item in no_calendar["ticket_results"][0]["horizons"]},
                         {"SESSION_CALENDAR_UNAVAILABLE"})
        jump = closes_with(AAA={day: "40" for day in SESSIONS[4:]})
        self.assertEqual(horizon(row_of(score([ticket_entry("T-1")], closes=jump), "T-1")["horizons"], 5)["reason"],
                         "POSSIBLE_UNADJUSTED_SPLIT")

    def test_a_split_after_the_session_compares_the_cap_with_the_raw_close(self) -> None:
        halved = closes_with()
        for day in SESSIONS[4:]:
            halved["AAA"][day] = "50"
        halved["AAA"][S5] = "55"
        action = {"symbol": "AAA", "action_type": "SPLIT", "effective_session": SESSIONS[4], "new_shares": 2,
                  "old_shares": 1, "official_source": {}, "kiwoom_crosscheck": {}, "recorded_by": "t",
                  "recorded_at": "2026-10-01T00:00:00Z"}
        corporate = {"status": "OK", "sha256": "1" * 64, "errors": [], "actions": [action]}
        report = score([ticket_entry("T-1", cap="101"), outcome_entry("T-1", "filled", filled=10, average="95")],
                       closes=halved, corporate=corporate)
        row = row_of(report, "T-1")
        self.assertTrue(row["would_fill"])  # raw close 100 <= cap 101, not the adjusted 50
        self.assertEqual(horizon(row["horizons"], 5)["vs_no_action"], "0.100000")
        self.assertEqual(horizon(row["user"]["horizons"], 5)["vs_no_action"], "0.157895")  # 55 / (95 / 2) - 1


class UserOutcomeTests(unittest.TestCase):  # T10
    def test_each_recorded_outcome_state(self) -> None:
        entries = [ticket_entry(name) for name in ("FILLED", "PARTIAL", "NOAVG", "UNFILLED", "SKIPPED", "CHANGED",
                                                    "NONE")]
        entries += [outcome_entry("FILLED", "unfilled"), outcome_entry("FILLED", "filled", filled=10, average="95"),
                    outcome_entry("PARTIAL", "partial", filled=3, average="100"),
                    outcome_entry("NOAVG", "filled", filled=10), outcome_entry("UNFILLED", "unfilled"),
                    outcome_entry("SKIPPED", "not_entered"), outcome_entry("CHANGED", "changed")]
        report = score(entries, records=[compare_ticket("CMP")])
        filled = row_of(report, "FILLED")["user"]  # the later outcome of the same ticket wins
        self.assertEqual((filled["state"], filled["start_price_basis"], filled["filled_fraction"]),
                         ("filled", "AVERAGE_FILL_PRICE", "1.000000"))
        self.assertEqual(horizon(filled["horizons"], 5)["vs_no_action"], "0.157895")  # 110 / 95 - 1
        partial = row_of(report, "PARTIAL")["user"]
        self.assertEqual((partial["state"], partial["filled_fraction"], horizon(partial["horizons"], 5)["vs_no_action"]),
                         ("partial", "0.300000", "0.100000"))
        no_average = row_of(report, "NOAVG")["user"]
        self.assertEqual((no_average["start_price_basis"], horizon(no_average["horizons"], 5)["vs_no_action"]),
                         ("SESSION_CLOSE", "0.100000"))
        for name in ("UNFILLED", "SKIPPED"):
            item = horizon(row_of(report, name)["user"]["horizons"], 5)
            self.assertEqual((item["status"], item["vs_no_action"]), ("SCORED", "0.000000"))
        changed = row_of(report, "CHANGED")["user"]
        self.assertEqual({item["reason"] for item in changed["horizons"]}, {"USER_CHANGED_ORDER"})
        self.assertEqual({item["status"] for item in changed["horizons"]}, {"NOT_SCORABLE"})
        self.assertEqual(row_of(report, "NONE")["user"], {"state": "PENDING_OUTCOME"})
        self.assertEqual(row_of(report, "CMP")["user"], {"state": "NOT_ENTERED_COMPARE_MODE"})

    def test_user_scores_use_only_finished_sessions(self) -> None:
        entries = [ticket_entry("T-1"), outcome_entry("T-1", "filled", filled=10, average="95")]
        user = row_of(score(entries, evaluation_as_of=after(SESSIONS[5])), "T-1")["user"]
        self.assertEqual({item["status"] for item in user["horizons"]}, {"PENDING"})


class CompareFileTests(unittest.TestCase):  # T9
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="score_tickets_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "auto-core"
        self.journal_path = self.tmp / "decision_journal.json"

    def write(self, relative: str, content: object) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")

    def record_journal_ticket(self) -> None:
        # An empty journal: the fixed top-level values come from the journal schema itself.
        schema = json.loads(journal_module.JOURNAL_SCHEMA.read_text(encoding="utf-8"))
        document = {key: rule["const"] for key, rule in schema["properties"].items() if "const" in rule}
        self.journal_path.write_text(json.dumps({**document, "entries": []}), encoding="utf-8")
        decision = {"run_day_kst": "2026-10-03", "buy_session": SESSION, "decision_mode": "apply",
                    "evaluation_session": SESSIONS[1], "no_action": {"value": False, "reasons": []},
                    "commit_sha": "a" * 40, "outcomes": [],
                    "tickets": [{"ticket_id": "AT-20261003-AAA-1", "ticker": "AAA", "side": "buy", "type": "LOC",
                                 "price": 101, "qty": 10, "amount": 1010, "session": SESSION,
                                 "decision_key": "d" * 64, "priceRule": "TEST_ONLY", "evidence": {"r": "1/2"}}]}
        journal_module.append_auto_core_entries(journal_path=self.journal_path, decision=decision,
                                                decision_sha256="e" * 64, expected_head=journal_module.GENESIS_HASH,
                                                recheck=lambda: [])

    def test_reader_skips_rerun_files_and_names_broken_files(self) -> None:
        self.write("2026-10-03/decision.json", {"tickets": [compare_ticket("CMP-1"),
                                                            dict(compare_ticket("APPLY-1"), mode="apply")]})
        self.write("2026-10-03/decision.rerun-101500.json", {"tickets": [compare_ticket("RERUN-1")]})
        self.write("2026-10-04/decision.json", "{broken")
        self.write("2026-10-05/decision.json", {"tickets": "none"})
        self.write("latest/decision.json", {"tickets": [compare_ticket("NOT-A-DAY")]})
        loaded = scorer.load_compare_tickets(self.root)
        self.assertEqual(loaded["status"], "OK")
        self.assertEqual([record["ticket_id"] for record in loaded["records"]], ["CMP-1"])
        self.assertEqual(loaded["errors"], [{"file": "2026-10-04/decision.json", "reason": "DECISION_NOT_JSON"},
                                            {"file": "2026-10-05/decision.json", "reason": "DECISION_TICKETS_INVALID"}])
        self.assertEqual(scorer.load_compare_tickets(self.tmp / "absent")["status"], "MISSING")

    def test_cli_scores_journal_and_compare_tickets_once_each(self) -> None:
        self.record_journal_ticket()
        self.write("2026-10-03/decision.json", {"tickets": [compare_ticket("AT-20261003-AAA-1"), compare_ticket(
            "CMP-1", ticker="BBB")]})
        self.write("2026-10-04/decision.json", {"tickets": [compare_ticket("CMP-1", ticker="BBB")]})
        self.write("2026-10-04/decision.rerun-090000.json", {"tickets": [compare_ticket("RERUN-1")]})
        self.write("2026-10-05/decision.json", "{broken")
        inputs = {"calendar": CALENDAR, "calendar_failure": None, "closes": closes_with(), "unverified": {},
                  "close_histories": {}, "corporate_actions": NO_ACTIONS, "benchmark": NO_SPY}
        seen: list[list[str]] = []

        def fake_inputs(**kwargs: object) -> dict:
            seen.append(sorted(kwargs["tickers"]))
            return inputs

        output_root = self.tmp / "scores"
        buffer = io.StringIO()
        with mock.patch.object(scorer, "load_inputs", side_effect=fake_inputs), contextlib.redirect_stdout(buffer):
            code = scorer.main(["--journal", str(self.journal_path), "--output-root", str(output_root),
                                "--decisions-root", str(self.root), "--evaluation-as-of", after(S20).isoformat(),
                                "--event-calendar", str(self.tmp / "no-event-calendar.json")])
        self.assertEqual(code, 0)
        self.assertEqual(set(seen[0]), {"AAA", "BBB"})
        report = json.loads(next(output_root.glob("*/" + scorer.REPORT_FILE)).read_text(encoding="utf-8"))
        self.assertEqual([(row["ticket_id"], row["mode"]) for row in report["ticket_results"]],
                         [("AT-20261003-AAA-1", "apply"), ("CMP-1", "compare")])
        sources = report["ticket_sources"]
        self.assertEqual((sources["journal_tickets"], sources["compare_tickets"], sources["duplicates_skipped"],
                          sources["decisions_root_status"]), (1, 1, 2, "OK"))
        self.assertEqual(sources["errors"], [{"file": "2026-10-05/decision.json", "reason": "DECISION_NOT_JSON"}])
        self.assertEqual(report["results"], [])  # tickets never enter the card results
        self.assertEqual(report["journal"]["head_sha256"], journal_module.load_journal(self.journal_path)["head_sha256"])
        summary = report["ticket_summary"]
        self.assertEqual((summary["by_mode"], summary["label"], summary["conclusion_allowed"],
                          summary["min_scored_for_conclusion"]),
                         ({"apply": 1, "compare": 1}, "COUNTERFACTUAL_D", False, 30))
        self.assertEqual(summary["scored_by_horizon"], {"5": 2, "20": 2, "60": 0})
        output = buffer.getvalue()
        self.assertIn("주문표 채점", output)
        self.assertIn("등급 D", output)


class OutputSafetyTests(unittest.TestCase):  # T11, T12
    def test_no_cap_size_or_order_field_reaches_the_report(self) -> None:
        report = score([ticket_entry("T-1", cap="123.4567", size=37), outcome_entry("T-1", "partial", filled=5,
                                                                                    average="99.5")],
                       records=[compare_ticket("CMP-1", cap=123.4567, size=37)])
        self.assertEqual(forbidden_keys(report), [])
        text = json.dumps(report["ticket_results"])
        self.assertNotIn("123.4567", text)
        self.assertNotIn("99.5", text)

        def walk(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key, {"price", "qty", "amount", "type", "cap", "size", "authority",
                                           "filled_qty", "average_fill_price", "decision_key"})
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
            else:
                self.assertNotEqual(value, 37)

        walk(report["ticket_results"])
        walk(report["ticket_summary"])
        self.assertEqual(set(report["ticket_results"][0]), {"ticket_id", "ticker", "side", "mode", "session",
                                                            "start_basis", "evidence_grade", "would_fill",
                                                            "horizons", "user", "risk_1r", "evidence_weak_kinds",
                                                            "event_exposure"})
        # risk1r: without a recorded 1R both are null and every horizon's R multiple is null.
        self.assertEqual((report["ticket_results"][0]["risk_1r"], report["ticket_results"][0]["evidence_weak_kinds"]),
                         (None, None))
        self.assertEqual({item["r_multiple"] for item in report["ticket_results"][0]["horizons"]}, {None})

    def test_the_call_without_ticket_records_still_works(self) -> None:
        plain = scorer.score_journal(
            synthetic_journal([]), calendar=CALENDAR, closes=closes_with(), unverified={}, benchmark=NO_SPY,
            corporate_actions=NO_ACTIONS, evaluation_as_of=after(S20))
        self.assertEqual((plain["results"], plain["ticket_results"], plain["ticket_summary"]["ticket_total"]),
                         ([], [], 0))
        journal_only = scorer.score_journal(
            synthetic_journal([ticket_entry("T-1")]), calendar=CALENDAR, closes=closes_with(), unverified={},
            benchmark=NO_SPY, corporate_actions=NO_ACTIONS, evaluation_as_of=after(S20))
        self.assertEqual([row["ticket_id"] for row in journal_only["ticket_results"]], ["T-1"])
        corrupt = scorer.score_journal(
            {"status": "CORRUPT", "entries": [], "errors": ["JOURNAL_NOT_JSON"], "head_sha256": "0" * 64},
            calendar=CALENDAR, closes={}, unverified={}, benchmark=NO_SPY, corporate_actions=NO_ACTIONS,
            evaluation_as_of=after(S20), ticket_records=[compare_ticket("CMP-1")])
        self.assertEqual((corrupt["ticket_results"], corrupt["ticket_summary"]["ticket_total"]), ([], 0))


EVENT_DOCUMENT = {"schema": "event-calendar/1", "coverage_start": SESSIONS[0], "horizon_end": "2026-12-31", "events": [
    {"id": "ev-before", "kind": "macro_release", "tier": "A", "label": "BEFORE", "event_date": SESSION,
     "time_et": "10:00", "report_date": SESSION, "status": "VERIFIED"},
    {"id": "ev-night", "kind": "earnings", "tier": "A", "label": "NIGHT", "event_date": SESSION,
     "time_et": "16:30", "report_date": SESSIONS[3], "status": "VERIFIED"},
    {"id": "ev-later", "kind": "central_bank", "tier": "B", "label": "LATER", "event_date": SESSIONS[5],
     "time_et": None, "report_date": SESSIONS[6], "status": "VERIFIED"},
    {"id": "ev-maybe", "kind": "earnings", "tier": "A", "label": "MAYBE", "event_date": SESSIONS[4],
     "time_et": None, "report_date": None, "status": "NOT_ANNOUNCED", "window": [SESSIONS[3], SESSIONS[5]]}]}
NEW_PHRASES = re.compile(r" · (이벤트 밤새 \S+|밤새 이벤트 노출 \d+건"
                         r"|이벤트 노출 확인 필요\([A-Z_]+\))")


def without_event_fields(report: dict) -> dict:
    """The report minus the event-ctx keys (event_calendar, event_exposure and the two summary counts)."""
    copy = json.loads(json.dumps(report))
    copy.pop("event_calendar")
    for row in copy["ticket_results"]:
        row.pop("event_exposure")
    for key in ("event_exposure_ok", "event_overnight"):
        copy["ticket_summary"].pop(key)
    return copy


class EventExposureTests(unittest.TestCase):  # T6 golden, own earnings in the scorer
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="score_events_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.good = self.tmp / "event-calendar.json"
        self.good.write_text(json.dumps(EVENT_DOCUMENT), encoding="utf-8")
        self.broken = self.tmp / "broken.json"
        self.broken.write_text("{broken", encoding="utf-8")
        self.entries = [ticket_entry("T-UP", cap="101"), ticket_entry("T-LOW", cap="99"),
                        ticket_entry("S-1", side="sell", cap="99"), ticket_entry("T-OUT", session="2026-09-30"),
                        outcome_entry("T-UP", "filled", filled=10, average="95"), outcome_entry("T-LOW", "unfilled")]
        self.records = [compare_ticket("CMP-1"), compare_ticket("CMP-2", side="sell", ticker="BBB")]

    def report(self, event_calendar: object = "omit", **kwargs: object) -> dict:
        extra = {} if event_calendar == "omit" else {"event_calendar": event_calendar}
        spy = {"status": "OK", "closes": {**{day: "400" for day in SESSIONS}, S5: "404"}, "errors": []}
        return scorer.score_journal(
            synthetic_journal(self.entries), calendar=CALENDAR, closes=closes_with(), unverified={}, benchmark=spy,
            corporate_actions=NO_ACTIONS, evaluation_as_of=after(S20), ticket_records=self.records, **extra, **kwargs)

    def test_scores_are_identical_with_missing_present_and_broken_calendars(self) -> None:  # T6
        baseline = self.report()  # the call as it was before event-ctx (no event calendar argument)
        loaded = {name: scorer.load_event_calendar(path) for name, path in (
            ("missing", self.tmp / "absent.json"), ("present", self.good), ("broken", self.broken))}
        self.assertEqual({name: item["status"] for name, item in loaded.items()},
                         {"missing": "MISSING", "present": "OK", "broken": "INVALID"})
        reports = {name: self.report(item) for name, item in loaded.items()}
        self.assertEqual(len(baseline["ticket_results"]), 6)
        for name, report in reports.items():
            with self.subTest(calendar=name):
                self.assertEqual(without_event_fields(report), without_event_fields(baseline))
                stripped = [NEW_PHRASES.sub("", line) for line in scorer.render_report(report)]
                self.assertEqual(stripped, [NEW_PHRASES.sub("", line) for line in scorer.render_report(baseline)])
                self.assertEqual(report["event_calendar"]["classification"], "EX_POST_CURRENT_CALENDAR")
        self.assertEqual({row["event_exposure"]["status"] for row in reports["missing"]["ticket_results"]},
                         {"EVENT_CALENDAR_MISSING"})
        self.assertEqual({row["event_exposure"]["status"] for row in reports["broken"]["ticket_results"]},
                         {"EVENT_CALENDAR_INVALID"})
        present = reports["present"]
        self.assertEqual(present["event_calendar"]["sha256"], loaded["present"]["sha256"])
        exposure = row_of(present, "T-UP")["event_exposure"]
        self.assertEqual(exposure, {"status": "OK", "before_fill": ["ev-before"], "overnight": ["ev-night"],
                                    "within_5": ["ev-night", "ev-later"], "possible": ["ev-maybe"],
                                    "own_earnings": None})
        self.assertEqual(row_of(present, "T-OUT")["event_exposure"]["status"], "SESSION_UNKNOWN")
        summary = present["ticket_summary"]
        self.assertEqual((summary["event_exposure_ok"], summary["event_overnight"]), (5, 5))
        for name in ("missing", "broken"):
            self.assertEqual((reports[name]["ticket_summary"]["event_exposure_ok"],
                              reports[name]["ticket_summary"]["event_overnight"]), (0, 0))
        lines = scorer.render_report(present)
        summary_line = next(line for line in lines if line.startswith("[주문표 채점]"))
        self.assertTrue(summary_line.endswith(" · 밤새 이벤트 노출 5건"))
        self.assertTrue(any(line.endswith(" · 이벤트 밤새 ev-night") for line in lines))
        no_calendar = scorer.score_journal(
            synthetic_journal(self.entries), calendar=None, calendar_failure="TEST", closes=closes_with(),
            unverified={}, benchmark=NO_SPY, corporate_actions=NO_ACTIONS, evaluation_as_of=after(S20),
            event_calendar=loaded["present"])
        self.assertEqual({row["event_exposure"]["status"] for row in no_calendar["ticket_results"]},
                         {"SESSION_CALENDAR_UNAVAILABLE"})

    def test_own_earnings_from_the_decision_files(self) -> None:
        night = {"status": "VERIFIED", "announcement_session": SESSION, "timing": "AFTER_CLOSE"}
        early = {"status": "VERIFIED", "announcement_session": SESSIONS[3], "timing": "BEFORE_OPEN"}
        earnings = {"by_ticket": {"CMP-1": {"AAA": early}}, "by_session": {SESSION: {"AAA": night}}}
        report = self.report(scorer.load_event_calendar(self.good), decision_earnings=earnings)
        self.assertEqual(row_of(report, "T-UP")["event_exposure"]["own_earnings"]["position"], "overnight")
        self.assertEqual(row_of(report, "CMP-1")["event_exposure"]["own_earnings"]["position"], "overnight")
        self.assertEqual(row_of(report, "CMP-1")["event_exposure"]["own_earnings"]["timing"], "BEFORE_OPEN")
        self.assertIsNone(row_of(report, "CMP-2")["event_exposure"]["own_earnings"])  # BBB has no record
        self.assertEqual(without_event_fields(report), without_event_fields(self.report()))

    def test_cli_reads_the_event_calendar_and_earnings_and_a_broken_calendar_only_changes_the_status(self) -> None:
        root = self.tmp / "auto-core"
        (root / "2026-10-03").mkdir(parents=True)
        (root / "2026-10-03" / "decision.json").write_text(json.dumps({
            "buy_session": SESSION, "earnings_calendar": {"BBB": {"status": "VERIFIED", "announcement_session": SESSION,
                                                                  "timing": "BEFORE_OPEN"}},
            "tickets": [compare_ticket("CMP-9", ticker="BBB")]}), encoding="utf-8")
        inputs = {"calendar": CALENDAR, "calendar_failure": None, "closes": closes_with(), "unverified": {},
                  "close_histories": {}, "corporate_actions": NO_ACTIONS, "benchmark": NO_SPY}
        reports = {}
        for name, path in (("present", self.good), ("broken", self.broken)):
            output_root = self.tmp / f"scores-{name}"
            with mock.patch.object(scorer, "load_inputs", return_value=inputs), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = scorer.main(["--journal", str(self.tmp / "no-journal.json"), "--output-root", str(output_root),
                                    "--decisions-root", str(root), "--evaluation-as-of", after(S20).isoformat(),
                                    "--event-calendar", str(path)])
            self.assertEqual(code, 0)
            reports[name] = json.loads(next(output_root.glob("*/" + scorer.REPORT_FILE)).read_text(encoding="utf-8"))
        row = reports["present"]["ticket_results"][0]
        self.assertEqual((row["ticket_id"], row["event_exposure"]["status"]), ("CMP-9", "OK"))
        self.assertEqual(row["event_exposure"]["own_earnings"]["position"], "before_fill")
        self.assertEqual(reports["broken"]["event_calendar"]["status"], "INVALID")
        self.assertEqual(without_event_fields(reports["broken"]), without_event_fields(reports["present"]))
        self.assertEqual(forbidden_keys(reports["present"]), [])


if __name__ == "__main__":
    unittest.main()
