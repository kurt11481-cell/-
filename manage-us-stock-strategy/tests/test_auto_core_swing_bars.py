"""swing-bars: after the daily core result (result.json, LATEST.json) is written, the closes of the swing shadow
watch list (docs/claude/swing-watch.json) are collected in a separate best-effort step that writes only
swing-bars.json and never changes the core result, the return value or the exit code.

Uses test_auto_core's daily fixture (NOW: KST 2026-10-14; held AAA and BBB, watch NEWW, extra SOXX). The list
file is a temporary path passed as swing_watch_path and the swing collector is a fake passed as swing_collector.
No network, no Kiwoom runtime, no kiwoomcli, no PowerShell.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import itertools
import json
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core  # noqa: E402
import test_auto_core as base  # noqa: E402
from validation_common import load_json, validate_instance  # noqa: E402

DAY = "2026-10-14"
CORE_SYMBOLS = {"AAA", "BBB", "NEWW", "SOXX"}


class SwingBarsDailyTests(base.DailyTests):
    """Only the tests defined in this class run (load_tests); the inherited DailyTests tests run in test_auto_core."""

    def setUp(self):
        super().setUp()
        self.watch = self.root / "swing-watch.json"
        self.swing_calls: list[tuple] = []
        self.seen: list[tuple[bytes, bytes]] = []
        self.swing_errors: dict[str, Exception] = {}
        self.ticks = 0.0
        self.tick_per_symbol = 0.0

    # -- fixture helpers -------------------------------------------------------------------------

    def write_watch(self, symbols, schema="swing-watch-1"):
        self.watch.write_text(json.dumps({"schema": schema, "symbols": list(symbols)}), encoding="utf-8")

    def history_writer(self, symbol, exchange, *, now, closes_root):
        """A history file as regular_session_close_history writes it: 2 sessions, 1 of them verified."""
        sessions = [{"session_date": "2026-10-12", "close": "10.00", "verified": True},
                    {"session_date": "2026-10-13", "close": "11.00", "verified": False}]
        (closes_root / "history" / f"{symbol}.close-history.json").write_text(json.dumps(
            {"symbol": symbol, "exchange": exchange, "last_session": "2026-10-13", "session_count": 2,
             "sessions": sessions}), encoding="utf-8")
        return {"symbol": symbol, "last_session": "2026-10-13", "sessions": 2, "continuity": "OK"}

    def day_dir(self, day=DAY):
        return self.output_root / day

    def swing_collect(self, symbol, exchange, *, newest, oldest, profile, pages_root):
        """The fake swing collector: records the call and the core result bytes on disk at that moment."""
        self.swing_calls.append((symbol, exchange, newest.isoformat(), oldest.isoformat(), profile, pages_root))
        self.seen.append(((self.day_dir(newest.isoformat()) / "result.json").read_bytes(),
                          (self.output_root / "LATEST.json").read_bytes()))
        self.ticks += self.tick_per_symbol
        if symbol in self.swing_errors:
            raise self.swing_errors[symbol]

    def run_daily(self, *, broker=None, now=base.NOW, watch=True, collector=None, halt=False, function=None,
                  clock=None, swing=True):
        self.config("compare", halt)
        provenance = {"status": "OK", "commit_sha": base.COMMIT, "dirty_paths": [], "guarded_dirty_paths": []}
        base.FrozenClock.moment = now
        kwargs = dict(
            output_root=self.output_root, config_path=self.config_path, now=now, reader=broker or base.sale_broker(),
            exchange_reader=self.exchange_reader, collector=collector or self.collector,
            history_updater=self.history_writer, exposure_runner=self.exposure, provenance=provenance,
            policy_paths=self.policies, closes_root=self.closes, watchlist_path=self.watchlist,
            evidence_root=self.evidence_root, provenance_source=lambda: dict(provenance))
        if swing:
            kwargs.update(swing_collector=self.swing_collect, swing_clock=clock or (lambda: self.ticks))
            if watch:
                kwargs["swing_watch_path"] = self.watch
        return (function or auto_core.daily)(**kwargs)

    def run_main(self, **options):
        """main daily with the fixture: main's own daily arguments are checked and its exit code returned."""
        real = auto_core.daily
        passed: dict = {}

        def wrapper(**kwargs):
            passed.update(kwargs)
            return self.run_daily(function=real, **options)
        with mock.patch.object(auto_core, "daily", side_effect=wrapper), contextlib.redirect_stdout(io.StringIO()):
            code = auto_core.main(["daily", "--output-root", str(self.output_root), "--config", str(self.config_path)])
        self.assertEqual(passed["swing_watch_path"], auto_core.SWING_WATCH_PATH)
        return code

    def swing_record(self, day=DAY):
        return load_json(self.day_dir(day) / "swing-bars.json")

    def assert_core_untouched(self, result, day=DAY):
        """The core result on disk before the swing step equals it after, and equals the return value."""
        self.assertTrue(self.seen, "the swing collector was not called")
        result_bytes = (self.day_dir(day) / "result.json").read_bytes()
        latest_bytes = (self.output_root / "LATEST.json").read_bytes()
        for inside_result, inside_latest in self.seen:
            self.assertEqual(inside_result, result_bytes)
            self.assertEqual(inside_latest, latest_bytes)
        self.assertEqual(load_json(self.day_dir(day) / "result.json"), result)
        self.assertEqual(load_json(self.output_root / "LATEST.json"), result)
        self.assertEqual(set(result["steps"]), {"reconcile", "bars", "exposure"})
        self.assertNotIn("swing", json.dumps(result))
        self.assertEqual(validate_instance(result, base.SCHEMAS / "auto-core-result.schema.json"), [])

    def core_collected(self):
        return {item[0] for item in self.collected}

    # -- 1 -----------------------------------------------------------------------------------------

    def test_swing_no_watch_path_runs_as_before(self):
        result = self.run_daily(swing=False)  # no swing argument at all (the existing callers)
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertFalse((self.day_dir() / "swing-bars.json").exists())
        self.assertEqual(self.core_collected(), CORE_SYMBOLS)
        self.assertEqual(len(self.collected), 4)
        self.assertIsNone(inspect.signature(auto_core.daily).parameters["swing_watch_path"].default)

    def test_swing_spy_without_watch_path_is_not_called(self):
        self.write_watch(["SWA"])
        result = self.run_daily(watch=False)
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(self.swing_calls, [])
        self.assertFalse((self.day_dir() / "swing-bars.json").exists())

    # -- 2 -----------------------------------------------------------------------------------------

    def test_swing_missing_list_file_writes_nothing(self):
        self.assertFalse(self.watch.exists())
        result = self.run_daily()
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(self.swing_calls, [])
        self.assertFalse((self.day_dir() / "swing-bars.json").exists())

    # -- 3 -----------------------------------------------------------------------------------------

    def test_swing_collects_listed_symbols_once_after_the_core_result(self):
        self.write_watch(["SWA", "AAA", "SWA"])
        result = self.run_daily()
        self.assertEqual(result["status"], "OK", result["reasons"])
        # SWA once (no history yet: exchange lookup and the first-collection start); AAA was the core's.
        self.assertEqual(self.swing_calls, [("SWA", "NASDAQ", DAY, "2026-05-17", "TEST_PROFILE", self.closes / "pages")])
        self.assertEqual(self.core_collected(), CORE_SYMBOLS)
        self.assertEqual(len(self.collected), 4)
        self.assert_core_untouched(result)
        self.assertEqual(self.swing_record(), {
            "schema_version": "auto-core-swing-bars-1.0", "run_day_kst": DAY, "status": "OK",
            "histories": [{"symbol": "SWA", "sessions": 2, "verified_sessions": 1}], "failed": [], "deferred": []})

    def test_swing_known_history_continues_from_its_last_session(self):
        (self.closes / "history" / "SWK.close-history.json").write_text(json.dumps(
            {"symbol": "SWK", "exchange": "NYSE", "last_session": "2026-10-09"}), encoding="utf-8")
        self.write_watch(["SWK"])
        self.run_daily()
        self.assertEqual(self.swing_calls, [("SWK", "NYSE", DAY, "2026-10-09", "TEST_PROFILE", self.closes / "pages")])

    # -- 4 -----------------------------------------------------------------------------------------

    def test_swing_symbol_failures_never_change_the_core(self):
        self.write_watch(["SWA", "SWB", "SWC", "SWD"])
        self.swing_errors = {
            "SWA": auto_core.StepFailure("BAR_COLLECTION_FAILED:SWA:1"),
            "SWB": subprocess.TimeoutExpired(cmd=["powershell.exe", "-File", "x"], timeout=600),
            "SWC": RuntimeError("boom"),
        }
        code = self.run_main()
        self.assertEqual(code, 0)
        result = load_json(self.day_dir() / "result.json")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual([call[0] for call in self.swing_calls], ["SWA", "SWB", "SWC", "SWD"])
        self.assert_core_untouched(result)
        record = self.swing_record()
        self.assertEqual(record["status"], "PARTIAL")
        self.assertEqual(record["failed"], [
            {"symbol": "SWA", "reason": "BAR_COLLECTION_FAILED:SWA:1"},
            {"symbol": "SWB", "reason": "BAR_COLLECTION_TIMEOUT:SWB:600"},
            {"symbol": "SWC", "reason": "UNEXPECTED_ERROR:SWC:RuntimeError:boom"}])
        self.assertEqual(record["histories"], [{"symbol": "SWD", "sessions": 2, "verified_sessions": 1}])
        self.assertEqual(record["deferred"], [])

    def test_swing_exchange_and_history_failures_are_recorded(self):
        self.write_watch(["SWE", "SWH", "SWU"])
        plain_reader, writer = self.exchange_reader, self.history_writer

        def reader(requests, *, runtime, policy):  # no row for SWE: resolve_exchange raises
            if requests[0]["ticker"] == "SWE":
                return [{"bridge_status": "PASS", "data": []}]
            return plain_reader(requests, runtime=runtime, policy=policy)

        def updater(symbol, exchange, *, now, closes_root):
            if symbol == "SWH":
                raise auto_core.StepFailure("CLOSE_HISTORY_FAILED:SWH:x")
            if symbol == "SWU":  # an update that leaves no readable history file
                return {"symbol": symbol, "sessions": 1}
            return writer(symbol, exchange, now=now, closes_root=closes_root)
        self.exchange_reader, self.history_writer = reader, updater
        result = self.run_daily()
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assert_core_untouched(result)
        record = self.swing_record()
        self.assertEqual(record["status"], "PARTIAL")
        self.assertEqual(record["failed"], [
            {"symbol": "SWE", "reason": "EXCHANGE_UNRESOLVED:SWE"},
            {"symbol": "SWH", "reason": "CLOSE_HISTORY_FAILED:SWH:x"},
            {"symbol": "SWU", "reason": "CLOSE_HISTORY_UNREADABLE:SWU:FileNotFoundError"}])
        self.assertEqual(record["histories"], [])

    def test_swing_long_reason_is_cut(self):
        self.write_watch(["SWA"])
        self.swing_errors = {"SWA": RuntimeError("x" * 500)}
        self.run_daily()
        self.assertEqual(len(self.swing_record()["failed"][0]["reason"]), 200)

    # -- 5 -----------------------------------------------------------------------------------------

    def test_swing_time_budget_defers_everything_when_spent(self):
        self.write_watch(["SWA", "SWB", "SWC"])
        clock = itertools.count(0, 700)  # step start 0, first check 700: 1200 - 700 < 600
        result = self.run_daily(clock=lambda: next(clock))
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(self.swing_calls, [])
        record = self.swing_record()
        self.assertEqual((record["status"], record["deferred"], record["histories"]), ("PARTIAL", ["SWA", "SWB", "SWC"], []))

    def test_swing_time_budget_defers_the_rest(self):
        self.write_watch(["SWA", "SWB", "SWC"])
        self.tick_per_symbol = 700  # SWA starts at 0; at 700 less than 600 s of the 1200 s budget is left
        result = self.run_daily()
        self.assertEqual([call[0] for call in self.swing_calls], ["SWA"])
        self.assert_core_untouched(result)
        record = self.swing_record()
        self.assertEqual((record["status"], record["deferred"]), ("PARTIAL", ["SWB", "SWC"]))
        self.assertEqual([item["symbol"] for item in record["histories"]], ["SWA"])

    def test_swing_time_budget_boundary_starts_with_exactly_one_timeout_left(self):
        self.write_watch(["SWA", "SWB", "SWC"])
        self.tick_per_symbol = 600  # SWB starts with exactly 600 s left; SWC with 0 s left is deferred
        self.run_daily()
        self.assertEqual([call[0] for call in self.swing_calls], ["SWA", "SWB"])
        self.assertEqual(self.swing_record()["deferred"], ["SWC"])
        self.assertEqual((auto_core.SWING_TIME_BUDGET_MIN, auto_core.SWING_SYMBOL_TIMEOUT_S), (20, 600))

    # -- 6 -----------------------------------------------------------------------------------------

    def test_swing_not_run_on_a_failed_day(self):
        self.write_watch(["SWA"])

        def failing(symbol, exchange, **kwargs):
            if symbol == "AAA":
                raise auto_core.StepFailure(f"BAR_COLLECTION_FAILED:{symbol}:1")
            self.collector(symbol, exchange, **kwargs)
        result = self.run_daily(collector=failing)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(self.swing_calls, [])
        self.assertFalse((self.day_dir() / "swing-bars.json").exists())

    def test_swing_not_run_when_the_finished_result_is_a_fail(self):
        # _finish turns an invalid result into FAIL (schema check): the swing step reads the finished status.
        self.write_watch(["SWA"])
        with mock.patch.object(auto_core, "validate_instance", return_value=["broken"]):
            result = self.run_daily()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(self.swing_calls, [])
        self.assertFalse((self.day_dir() / "swing-bars.json").exists())

    # -- 7 -----------------------------------------------------------------------------------------

    def test_swing_not_run_on_the_halted_day(self):
        # The halted config (config's second argument): the early HOLD return, no reads at all.
        self.write_watch(["SWA"])
        broker = base.sale_broker()
        result = self.run_daily(broker=broker, halt=True)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual((broker.requests, self.collected, self.exposure_calls), ([], [], 0))
        self.assertEqual(self.swing_calls, [])
        self.assertFalse((self.day_dir() / "swing-bars.json").exists())

    def test_swing_runs_on_an_ordinary_hold_day(self):
        self.run_daily(swing=False)
        self.write_watch(["SWA"])
        later = base.NOW + timedelta(days=1)
        wrong = base.FakeBroker(holdings=[base.holding("AAA", 6, settled=10), base.holding("BBB", 5)],
                                ord_cash="1329.17", pymn_cash="1000.00", retrieved=later - timedelta(seconds=5))
        self.seen.clear()
        result = self.run_daily(broker=wrong, now=later)
        self.assertEqual(result["status"], "HOLD")
        self.assertTrue(result["reasons"])
        self.assertEqual([call[0] for call in self.swing_calls], ["SWA"])
        self.assertEqual(self.swing_calls[0][2], "2026-10-15")
        self.assert_core_untouched(result, day="2026-10-15")
        record = self.swing_record("2026-10-15")
        self.assertEqual((record["status"], record["run_day_kst"]), ("OK", "2026-10-15"))

    # -- 8 -----------------------------------------------------------------------------------------

    def test_swing_invalid_list_is_recorded_and_not_collected(self):
        cases = {
            "schema differs": json.dumps({"schema": "swing-watch-2", "symbols": ["SWA"]}),
            "lower case code": json.dumps({"schema": "swing-watch-1", "symbols": ["swa"]}),
            "broken json": '{"schema": "swing-watch-1", "symbols": [',
            "not an object": json.dumps(["SWA"]),
            "symbols not a list": json.dumps({"schema": "swing-watch-1", "symbols": "SWA"}),
            "code not a string": json.dumps({"schema": "swing-watch-1", "symbols": [1]}),
            "code too long": json.dumps({"schema": "swing-watch-1", "symbols": ["ABCDEFGHIJKLM"]}),
            "code with a path": json.dumps({"schema": "swing-watch-1", "symbols": ["A/B"]}),
            "trailing newline": json.dumps({"schema": "swing-watch-1", "symbols": ["SWA\n"]}),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.watch.write_text(text, encoding="utf-8")
                self.swing_calls.clear()
                result = self.run_daily()
                self.assertEqual(result["status"], "OK", result["reasons"])
                self.assertEqual(self.swing_calls, [])
                record = self.swing_record()
                self.assertEqual(record["status"], "LIST_INVALID")
                self.assertTrue(0 < len(record["reason"]) <= 200)
                self.assertEqual((record["histories"], record["failed"], record["deferred"]), ([], [], []))

    def test_swing_list_with_bom_and_dotted_code_is_read(self):
        self.watch.write_bytes(b"\xef\xbb\xbf" + json.dumps({"schema": "swing-watch-1", "symbols": ["BRK.B"]}).encode())
        self.run_daily()
        self.assertEqual([call[0] for call in self.swing_calls], ["BRK.B"])
        self.assertEqual(self.swing_record()["status"], "OK")

    # -- 9 -----------------------------------------------------------------------------------------

    def test_swing_list_of_core_symbols_only(self):
        self.write_watch(["AAA", "NEWW"])
        result = self.run_daily()
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(self.swing_calls, [])
        record = self.swing_record()
        self.assertEqual((record["status"], record["histories"], record["failed"], record["deferred"]),
                         ("OK", [], [], []))

    def test_swing_empty_list_is_ok(self):
        self.write_watch([])
        self.run_daily()
        self.assertEqual(self.swing_calls, [])
        self.assertEqual(self.swing_record()["status"], "OK")

    # -- 10 ----------------------------------------------------------------------------------------

    def test_swing_record_write_failure_never_changes_the_core(self):
        self.write_watch(["SWA"])
        (self.day_dir() / "swing-bars.json").mkdir(parents=True)  # the record path is taken by a folder
        code = self.run_main()
        self.assertEqual(code, 0)
        result = load_json(self.day_dir() / "result.json")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual([call[0] for call in self.swing_calls], ["SWA"])
        self.assert_core_untouched(result)
        self.assertTrue((self.day_dir() / "swing-bars.json").is_dir())

    def test_swing_unexpected_step_error_never_changes_the_core(self):
        self.write_watch(["SWA"])
        with mock.patch.object(auto_core, "read_swing_watch", side_effect=KeyError("boom")):
            code = self.run_main()
        self.assertEqual(code, 0)
        result = load_json(self.day_dir() / "result.json")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(load_json(self.output_root / "LATEST.json"), result)
        record = self.swing_record()
        self.assertEqual(record["status"], "PARTIAL")
        self.assertTrue(record["reason"].startswith("UNEXPECTED_ERROR:KeyError"))

    # -- 11 ----------------------------------------------------------------------------------------

    def test_swing_default_collector_uses_the_symbol_timeout(self):
        calls = []

        class Done:
            returncode = 0

        def runner(command, **kwargs):
            calls.append(kwargs["timeout"])
            return Done()
        default = inspect.signature(auto_core.daily).parameters["swing_collector"].default
        arguments = dict(newest=date(2026, 10, 14), oldest=date(2026, 10, 12), profile="TEST_PROFILE",
                         pages_root=self.closes / "pages", runner=runner)
        default("SWA", "NASDAQ", **arguments)
        auto_core.collect_bars("AAA", "NASDAQ", **arguments)  # the core collection keeps 3600
        self.assertEqual(calls, [600, 3600])

    def test_swing_main_passes_the_repository_list(self):
        self.assertEqual(auto_core.SWING_WATCH_PATH, auto_core.REPO_ROOT / "docs/claude/swing-watch.json")
        returned = {"status": "OK", "mode": "compare", "reasons": [], "compare": {"streak": 0},
                    "next_action_for_user": None}
        with mock.patch.object(auto_core, "daily", return_value=returned) as patched, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(auto_core.main(["daily"]), 0)
        self.assertEqual(patched.call_args.kwargs["swing_watch_path"], auto_core.SWING_WATCH_PATH)


def load_tests(loader, standard_tests, pattern):
    names = [name for name in SwingBarsDailyTests.__dict__ if name.startswith("test_")]
    return unittest.TestSuite(SwingBarsDailyTests(name) for name in names)


if __name__ == "__main__":
    unittest.main()
