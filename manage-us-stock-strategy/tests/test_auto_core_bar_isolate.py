"""bar-isolate: a watch-only symbol whose own 30-minute collection fails is isolated (no buy for it, one alert)
instead of failing the daily run; held, configured extra, exposure-review and decide benchmark symbols and
run-wide failures still fail closed.

Uses test_auto_core's daily fixture (NOW, RECORD: held AAA and BBB, watch NEWW, extra SOXX) and
test_auto_core_decide's Env unchanged. The fixture alert policy is {} (the exposure review's symbols cannot be
read, so isolation is off), so the isolating tests fix those symbols with mock.patch. No network, no Kiwoom
runtime, no PowerShell.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core  # noqa: E402
import auto_core_rules  # noqa: E402
import test_auto_core as base  # noqa: E402
import test_auto_core_decide as decide_base  # noqa: E402
from portfolio_exposure import exposure_config  # noqa: E402
from validation_common import load_json, validate_instance, write_json  # noqa: E402

decide_module = decide_base.decide_module
helpers = decide_base.helpers
EXPOSURE_SYMBOLS = "exposure_review_symbols"
ISOLATED_LINE = ("관심 종목 30분봉 수집 실패 {symbols} — 오늘 그 종목 매수 막힘(보유 종목 매도·노출 판정은 계속)"
                 " — Cowork 원인 확인")


# ---------------------------------------------------------------------------------------------
# daily (T1)
# ---------------------------------------------------------------------------------------------

class BarIsolateDailyTests(base.DailyTests):
    """Only the tests below run (load_tests); the inherited DailyTests tests run in test_auto_core."""

    def run_daily(self, *, collector=None, history_updater=None, exchange_reader=None, extra=("SOXX",)):
        config = self.config("compare")
        if list(extra) != config["symbols_extra"]:
            config["symbols_extra"] = list(extra)
            write_json(self.config_path, config)
        provenance = {"status": "OK", "commit_sha": base.COMMIT, "dirty_paths": [], "guarded_dirty_paths": []}
        base.FrozenClock.moment = base.NOW
        return auto_core.daily(
            output_root=self.output_root, config_path=self.config_path, now=base.NOW, reader=base.sale_broker(),
            exchange_reader=exchange_reader or self.exchange_reader, collector=collector or self.collector,
            history_updater=history_updater or self.updater, exposure_runner=self.exposure,
            provenance=provenance, policy_paths=self.policies, closes_root=self.closes,
            watchlist_path=self.watchlist, evidence_root=self.evidence_root,
            provenance_source=lambda: dict(provenance))

    def failing_collector(self, target, reason=None):
        def collect(symbol, exchange, **kwargs):
            if symbol == target:
                raise auto_core.StepFailure(reason or f"BAR_COLLECTION_FAILED:{symbol}:1")
            self.collector(symbol, exchange, **kwargs)
        return collect

    def assert_isolated(self, result, reason):
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(result["reasons"], [])  # a run without a failure has no reason (status OK)
        self.assertEqual(result["steps"]["bars"]["status"], "OK")
        self.assertEqual(result["steps"]["bars"]["isolated"], [{"symbol": "NEWW", "reason": reason}])
        self.assertEqual(sorted(item["symbol"] for item in result["steps"]["bars"]["histories"]), ["AAA", "BBB", "SOXX"])
        self.assertEqual(self.exposure_calls, 1)
        self.assertEqual(result["steps"]["exposure"]["status"], "OK")
        # warnings are the reconciliation's only (the fixture's own), nothing about the isolation.
        reconcile = load_json(self.output_root / "2026-10-14" / "reconcile.json")
        self.assertEqual(result["warnings"], list(reconcile.get("warnings") or []))
        self.assertEqual(validate_instance(result, base.SCHEMAS / "auto-core-result.schema.json"), [])
        self.assertEqual(load_json(self.output_root / "LATEST.json"), result)

    def assert_fail(self, result, reason):
        self.assertEqual(result["status"], "FAIL")
        self.assertIn(reason, result["reasons"])
        self.assertNotIn("bars", result["steps"])
        self.assertEqual(self.exposure_calls, 0)

    # 1
    def test_watch_only_collection_failure_is_isolated(self):
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(collector=self.failing_collector("NEWW"))
        self.assert_isolated(result, "BAR_COLLECTION_FAILED:NEWW:1")
        self.assertEqual(sorted(item[0] for item in self.collected), ["AAA", "BBB", "SOXX"])

    # 2
    def test_close_history_failure_is_isolated(self):
        def updater(symbol, exchange, *, now, closes_root):
            if symbol == "NEWW":
                raise auto_core.StepFailure("CLOSE_HISTORY_FAILED:NEWW:x")
            return self.updater(symbol, exchange, now=now, closes_root=closes_root)
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(history_updater=updater)
        self.assert_isolated(result, "CLOSE_HISTORY_FAILED:NEWW:x")

    def test_exchange_unresolved_is_isolated(self):
        def reader(requests, *, runtime, policy):  # no row for the symbol: resolve_exchange raises
            return [{"bridge_status": "PASS", "data": []}]
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(exchange_reader=reader)
        self.assert_isolated(result, "EXCHANGE_UNRESOLVED:NEWW")
        self.assertNotIn("NEWW", [item[0] for item in self.collected])

    # 3
    def test_held_symbol_failure_still_fails(self):
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(collector=self.failing_collector("AAA"))
        self.assert_fail(result, "BAR_COLLECTION_FAILED:AAA:1")

    def test_extra_symbol_failure_still_fails(self):
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(collector=self.failing_collector("SOXX"))
        self.assert_fail(result, "BAR_COLLECTION_FAILED:SOXX:1")

    def test_watch_member_that_is_a_configured_extra_still_fails(self):
        # NEWW is neither held, an exposure symbol nor a benchmark here: only the extra exclusion stops isolation.
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(collector=self.failing_collector("NEWW"), extra=("SOXX", "NEWW"))
        self.assert_fail(result, "BAR_COLLECTION_FAILED:NEWW:1")

    # 4
    def test_exposure_review_symbol_failure_still_fails(self):
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL", "NEWW"}):
            result = self.run_daily(collector=self.failing_collector("NEWW"))
        self.assert_fail(result, "BAR_COLLECTION_FAILED:NEWW:1")

    def test_decide_benchmark_failure_still_fails(self):
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}), \
                mock.patch.dict(auto_core_rules.C, {"RREC_POWER_BENCHMARK": "NEWW"}):
            result = self.run_daily(collector=self.failing_collector("NEWW"))
        self.assert_fail(result, "BAR_COLLECTION_FAILED:NEWW:1")

    # 5
    def test_run_wide_reason_still_fails(self):
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(collector=self.failing_collector("NEWW", "SESSION_CALENDAR_UNAVAILABLE:x"))
        self.assert_fail(result, "SESSION_CALENDAR_UNAVAILABLE:x")

    def test_non_step_failure_still_fails(self):
        def collect(symbol, exchange, **kwargs):
            if symbol == "NEWW":
                raise RuntimeError("boom")
            self.collector(symbol, exchange, **kwargs)
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily(collector=collect)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(reason.startswith("UNEXPECTED_ERROR:RuntimeError") for reason in result["reasons"]),
                        result["reasons"])
        self.assertEqual(self.exposure_calls, 0)

    # 6
    def test_unreadable_exposure_settings_turn_isolation_off(self):
        # No patch: the fixture alert policy {} has no exposure section, so exposure_config raises.
        with self.assertRaises(Exception):
            auto_core.exposure_review_symbols(alert_policy_path=self.policies["alert"], state_path=self.state_path)
        result = self.run_daily(collector=self.failing_collector("NEWW"))
        self.assert_fail(result, "BAR_COLLECTION_FAILED:NEWW:1")

    def test_exposure_review_symbols_are_settings_and_ledger_holdings(self):
        policy = helpers.POLICY_PATH  # the alert policy decide's tests read (read only)
        config = exposure_config(load_json(policy))
        symbols = auto_core.exposure_review_symbols(alert_policy_path=policy, state_path=self.state_path)
        self.assertEqual(symbols, {config["benchmark"].upper(), config["supplement"].upper(), "AAA", "BBB"})
        isolatable = auto_core.isolatable_symbols(
            output_directory=self.output_root / "2026-10-14", state_path=self.state_path,
            watchlist_path=self.watchlist, extra=["SOXX"], alert_policy_path=policy)
        self.assertEqual(isolatable, {"NEWW"} - symbols)

    # 7
    def test_no_failure_keeps_bars_as_before(self):
        with mock.patch.object(auto_core, EXPOSURE_SYMBOLS, return_value={"SOXL"}):
            result = self.run_daily()
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(set(result["steps"]["bars"]), {"status", "histories"})
        self.assertEqual(sorted(item["symbol"] for item in result["steps"]["bars"]["histories"]),
                         ["AAA", "BBB", "NEWW", "SOXX"])


# ---------------------------------------------------------------------------------------------
# decide (T2)
# ---------------------------------------------------------------------------------------------

def _isolated_t1(*entries):
    return {"status": "OK", "steps": {"bars": {"status": "OK", "histories": [], "isolated": list(entries)}}}


def _sells(decision):
    return ([item for item in decision["tickets"] if item["side"] == "sell"],
            [item for item in decision["candidates"] if item["side"] == "sell"],
            [item for item in decision["blocked"] if item["side"] == "sell"],
            {symbol: (item or {}).get("sell") for symbol, item in decision["evidence"].items()
             if symbol in ("SOXL", "SOXX")})


class BarIsolateDecideTests(unittest.TestCase):
    """test_auto_core_decide TicketFlowTests' env: SOXL 10 held, watch MU with a new official good-news fact and a
    confirmed 'not announced' earnings check gives one MU buy ticket (test_compare_ticket_is_not_for_entry)."""

    def env(self, t1=None):
        env = decide_base.Env(holdings={"SOXL": 10})
        self.addCleanup(env.close)
        env.write_good_news()
        if t1 is not None:
            write_json(env.day_dir / "result.json", t1)
        return env

    @staticmethod
    def run_capturing(env, *, drop=()):
        """decide with redeploy_ranking's results captured (and `drop` symbols left out of them)."""
        real = decide_module.redeploy_ranking
        captured = []

        def ranking(**kwargs):
            ranked = [item for item in real(**kwargs) if item["symbol"] not in drop]
            captured.append(ranked)
            return ranked
        with mock.patch.object(decide_module, "redeploy_ranking", side_effect=ranking):
            decision = env.run()
        return decision, captured

    # 8
    def test_isolated_watch_symbol_gets_no_buy_and_one_alert(self):
        plain, plain_ranked = self.run_capturing(self.env())
        self.assertEqual([(t["ticker"], t["side"]) for t in plain["tickets"]], [("MU", "buy")], plain["blocked"])
        self.assertFalse(any(alert["code"] == "T1_BARS_ISOLATED" for alert in plain["alerts"]))
        # The comparison run without MU as a redeployment candidate (sells see no candidate in it either).
        no_mu, _ = self.run_capturing(self.env(), drop=("MU",))
        env = self.env(_isolated_t1({"symbol": "MU", "reason": "BAR_COLLECTION_FAILED:MU:1"}))
        decision, ranked = self.run_capturing(env)
        self.assertIn(decision["status"], ("OK", "HOLD"), decision["reasons"])
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
        self.assertEqual([t for t in decision["tickets"] if t["ticker"] == "MU" and t["side"] == "buy"], [])
        self.assertEqual(decision["tickets"], [t for t in plain["tickets"] if t["ticker"] != "MU"])
        # Not a redeployment candidate: redeploy_ranking's result and the sell tickets' swap pairs.
        self.assertTrue(ranked)
        self.assertNotIn("MU", [item["symbol"] for result in ranked for item in result])
        self.assertFalse(any("MU" in str(t.get("swap_pair") or "") for t in decision["tickets"]))
        # MU is read as a data problem (UNK, BARS_ISOLATED) and its buy row is not passed.
        self.assertEqual(decision["symbols"]["MU"]["status"], "UNK")
        self.assertIn("BARS_ISOLATED", decision["symbols"]["MU"]["reasons"])
        self.assertEqual(env.bars["MU"]["status"], "OK")  # the loaded dict is not changed
        alerts = [alert for alert in decision["alerts"] if alert["code"] == "T1_BARS_ISOLATED"]
        self.assertEqual(alerts, [{"code": "T1_BARS_ISOLATED", "line": ISOLATED_LINE.format(symbols="MU"), "push": True}])
        self.assertNotIn("BAR_COLLECTION_FAILED", alerts[0]["line"])
        # Held sells and the sell judgments are those of the run without MU as a redeployment candidate.
        self.assertEqual(_sells(decision), _sells(no_mu))
        self.assertIsNotNone(_sells(decision)[3]["SOXL"])
        # The fixture's MU is a redeployment candidate when it is not isolated, so the exclusion above is real.
        self.assertIn("MU", [item["symbol"] for result in plain_ranked for item in result])

    def test_two_isolated_symbols_share_one_alert(self):
        env = self.env(_isolated_t1({"symbol": "MU", "reason": "BAR_COLLECTION_FAILED:MU:1"},
                                    {"symbol": "ZZZZ", "reason": "EXCHANGE_UNRESOLVED:ZZZZ"}))
        decision = env.run()
        alerts = [alert for alert in decision["alerts"] if alert["code"] == "T1_BARS_ISOLATED"]
        self.assertEqual([alert["line"] for alert in alerts], [ISOLATED_LINE.format(symbols="MU, ZZZZ")])

    # 9
    def test_invalid_isolated_entries_fail(self):
        good = {"symbol": "MU", "reason": "BAR_COLLECTION_FAILED:MU:1"}
        cases = {
            "missing reason": _isolated_t1({"symbol": "MU"}),
            "extra key": _isolated_t1({**good, "note": "x"}),
            "lower case": _isolated_t1({"symbol": "mu", "reason": "x"}),
            "empty symbol": _isolated_t1({"symbol": "", "reason": "x"}),
            "reason not str": _isolated_t1({"symbol": "MU", "reason": 1}),
            "held": _isolated_t1(good, {"symbol": "SOXL", "reason": "x"}),
            "benchmark SOXX": _isolated_t1({"symbol": "SOXX", "reason": "x"}),
            "duplicate": _isolated_t1(good, dict(good)),
            "empty list": _isolated_t1(),
            "not a list": {"status": "OK", "steps": {"bars": {"status": "OK", "isolated": {"MU": "x"}}}},
            "bars not an object": {"status": "OK", "steps": {"bars": []}},
        }
        for name, t1 in cases.items():
            with self.subTest(case=name):
                decision = self.env(t1).run()
                self.assertEqual(decision["status"], "FAIL")
                self.assertIn("T1_BARS_ISOLATED_INVALID", decision["reasons"])
                self.assertEqual(decision["tickets"], [])

    def test_t1_fail_is_still_a_hold(self):
        t1 = _isolated_t1({"symbol": "MU", "reason": "BAR_COLLECTION_FAILED:MU:1"})
        t1["status"] = "FAIL"
        decision = self.env(t1).run()
        self.assertEqual((decision["status"], decision["reasons"]), ("HOLD", ["T1_NOT_OK"]))

    # 10
    def test_t1_without_isolated_key_decides_as_before(self):
        def view(decision):
            return {key: decision[key] for key in ("status", "reasons", "symbols", "evidence", "buy_requirements",
                                                   "candidates", "blocked", "no_action", "alerts", "exposure")} | {
                # A ticket's inputs carry the T1 file's sha256, which differs with the file bytes.
                "tickets": [{k: v for k, v in t.items() if k != "inputs"} for t in decision["tickets"]]}
        old = self.env().run()  # the existing fixture's T1: {"status": "OK"} (no steps)
        bars_only = self.env({"status": "OK", "steps": {"bars": {"status": "OK", "histories": []}}}).run()
        self.assertEqual([(t["ticker"], t["side"]) for t in old["tickets"]], [("MU", "buy")])
        self.assertEqual(view(bars_only), view(old))
        self.assertFalse(any(alert["code"] == "T1_BARS_ISOLATED" for alert in old["alerts"]))


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    for name in ("test_watch_only_collection_failure_is_isolated",
                 "test_close_history_failure_is_isolated",
                 "test_exchange_unresolved_is_isolated",
                 "test_held_symbol_failure_still_fails",
                 "test_extra_symbol_failure_still_fails",
                 "test_watch_member_that_is_a_configured_extra_still_fails",
                 "test_exposure_review_symbol_failure_still_fails",
                 "test_decide_benchmark_failure_still_fails",
                 "test_run_wide_reason_still_fails",
                 "test_non_step_failure_still_fails",
                 "test_unreadable_exposure_settings_turn_isolation_off",
                 "test_exposure_review_symbols_are_settings_and_ledger_holdings",
                 "test_no_failure_keeps_bars_as_before"):
        suite.addTest(BarIsolateDailyTests(name))
    suite.addTests(loader.loadTestsFromTestCase(BarIsolateDecideTests))
    return suite


if __name__ == "__main__":
    unittest.main()
