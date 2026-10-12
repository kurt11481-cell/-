"""Redesign T2 F10: replay harness (prompt appendix C): E-R1 earnings, anchors, oracle against the ticket path.

Synthetic data (TEST_ONLY). The real-data smoke runs only where the saved 30-minute pages exist (the main
checkout); in a worktree it is skipped.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_replay as replay  # noqa: E402
import auto_core_tickets as tk  # noqa: E402
import helpers  # noqa: E402
from portfolio_exposure import earnings_blackout  # noqa: E402
from test_auto_core_tickets import CALENDAR_DAYS, LAST, Scenario  # noqa: E402
from validation_common import validate_instance  # noqa: E402

PAGES = ROOT / "workspace/outputs/regular-session-closes/pages"
MEASUREMENTS = ROOT / "docs/claude/redesign-t2-measurements-2026-10-10.json"


class EarningsTests(unittest.TestCase):
    RECORDS = [{"symbol": "MU", "announcement_session": "2026-09-30", "timing": "AFTER_CLOSE",
                "source_kind": "SEC_FILING", "source_url": "https://www.sec.gov/mu"},
               {"symbol": "PWR", "announcement_session": "2026-07-30", "timing": "BEFORE_OPEN",
                "source_kind": "SEC_FILING", "source_url": "https://www.sec.gov/pwr"}]
    SESSIONS = helpers.sessions("2026-07-01", 80)

    def test_verified_from_30_days_before_and_not_announced_otherwise(self):
        verified = replay.earnings_for("2026-09-10", self.RECORDS, self.SESSIONS, ["MU", "NBIS"])
        self.assertEqual(verified["MU"]["status"], "VERIFIED")
        self.assertNotIn("NBIS", verified)  # no 2.02 record: left out = blackout (fail closed)
        early = replay.earnings_for("2026-08-20", self.RECORDS, self.SESSIONS, ["MU"])
        self.assertEqual(early["MU"]["status"], "NOT_ANNOUNCED")
        after = replay.earnings_for("2026-10-05", self.RECORDS, self.SESSIONS, ["MU"])
        self.assertEqual(after["MU"]["status"], "NOT_ANNOUNCED")

    def test_records_feed_the_real_blackout_rule(self):
        session = "2026-09-29"
        buy = self.SESSIONS[self.SESSIONS.index(session) + 1]
        record = replay.earnings_for(session, self.RECORDS, self.SESSIONS, ["MU"])
        self.assertTrue(earnings_blackout("MU", record, self.SESSIONS, buy)[0])
        quiet = replay.earnings_for("2026-08-20", self.RECORDS, self.SESSIONS, ["MU"])
        blackout, code = earnings_blackout("MU", quiet, self.SESSIONS, "2026-08-21", evaluation_session="2026-08-20",
                                           generated_at="2026-08-20T21:00:00Z")
        self.assertEqual((blackout, code), (False, "EARNINGS_NOT_ANNOUNCED_CHECKED"))
        self.assertTrue(earnings_blackout("NBIS", {}, self.SESSIONS, buy)[0])


class AnchorTests(unittest.TestCase):
    def test_anchor_maps_to_the_session_a_decide_run_would_evaluate(self):
        calendar = helpers.calendar(helpers.sessions("2026-10-01", 8))
        self.assertEqual(replay.anchor_session("2026-10-09", calendar), "2026-10-08")
        self.assertEqual(replay.anchor_session("2026-10-05", calendar), "2026-10-02")  # Monday KST -> Friday

    def test_anchors_are_unique_day_symbol_side(self):
        rows = [{"order_date_kst": "2026-10-06", "symbol": "MVLL", "side": "sell"}] * 3 + [
            {"order_date_kst": "2026-10-09", "symbol": "SOXL", "side": "sell"}]
        anchors = replay.anchors_from({replay.ANCHOR_KEY: {"rows": rows}})
        self.assertEqual(len(anchors), 2)


class OracleTests(unittest.TestCase):
    def oracle_for(self, scenario):
        result = scenario.run()
        should = replay.oracle(result, holdings=scenario.holdings, checks=scenario.checks,
                               m6_docs=[("m6-relative-comparison-7stock-TEST.md", "MU PWR SOXL")],
                               earnings=scenario.earnings, calendar_sessions=CALENDAR_DAYS, evaluation_session=LAST,
                               policy=scenario.policy, cash=scenario.cash, facts=scenario.facts)
        return result, should

    def test_oracle_and_ticket_path_agree_on_an_open_buy(self):
        result, should = self.oracle_for(Scenario())
        self.assertIn({"session": LAST, "symbol": "MU", "side": "buy"}, should)
        self.assertTrue(any(ticket["ticker"] == "MU" for ticket in result["planned"]["tickets"]))

    def test_oracle_closed_without_new_evidence(self):
        _result, should = self.oracle_for(Scenario(facts=False))
        self.assertEqual([item for item in should if item["side"] == "buy"], [])

    def test_oracle_is_a_different_code_path(self):
        import inspect
        source = inspect.getsource(replay.oracle)
        for name in ("plan(", "buy_requirements(", "evidence_summary(", "_buy_ticket(", "_sell_ticket("):
            self.assertNotIn(name, source)


def session_row(*, tickets=(), blocked=(), oracle=(), candidates=(), status="OK"):
    return {"session": "2026-10-08", "status": status, "tickets": list(tickets), "blocked": list(blocked),
            "candidates": list(candidates), "no_action": {"value": not tickets, "reasons": ["NO_CIRCUIT_OPEN"]},
            "oracle": list(oracle), "gate1": [], "E": 1.5, "band": "WITHIN_BAND"}


class JudgeTests(unittest.TestCase):
    CALENDAR = helpers.calendar(helpers.sessions("2026-10-01", 8))

    def judge(self, rows_r1, rows_r2=None, external=None, anchors=()):
        results = {"P-R1": {"cash": 1.0, "holdings": {"SOXL": 53}, "sessions": rows_r1, "no_data": []},
                   "P-R2": {"cash": 1.0, "holdings": {"NBIS": 13}, "sessions": rows_r2 or [session_row()],
                            "no_data": []}}
        out = replay._judge(results, list(anchors), self.CALENDAR, external, "2026-10-01", "2026-10-09",
                            {"sha256": None})
        self.assertEqual(validate_instance(out, replay.REPLAY_SCHEMA), [])
        return out

    def test_allowed_reason_is_not_a_leak_and_other_reasons_are(self):
        should = [{"session": "2026-10-08", "symbol": "SOXL", "side": "sell"}]
        allowed = self.judge([session_row(oracle=should, blocked=[{"symbol": "SOXL", "side": "sell",
                                                                    "reasons": ["DEADBAND"]}])])
        self.assertEqual(allowed["R_B"]["verdict"], "PASS")
        leak = self.judge([session_row(oracle=should, blocked=[{"symbol": "SOXL", "side": "sell",
                                                                 "reasons": ["REQ4_M6:no"]}])])
        self.assertEqual(leak["R_B"]["verdict"], "FAIL")
        self.assertEqual(len(leak["R_B"]["by_portfolio"]["P-R1"]["leaks"]), 1)
        issued = self.judge([session_row(oracle=should, tickets=[{"symbol": "SOXL", "side": "sell", "qty": 1,
                                                                   "price": 1.0, "r": "1/2"}])])
        self.assertEqual(issued["R_B"]["verdict"], "PASS")

    def test_external_oracle_misses_fail(self):
        external = [{"session": "2026-10-08", "symbol": "SOXL", "side": "sell"}]
        out = self.judge([session_row()], external=external)
        self.assertEqual(out["R_B"]["verdict"], "FAIL")
        self.assertEqual(out["R_B"]["by_portfolio"]["P-R1"]["oracle_difference"]["external_only"],
                         [["2026-10-08", "SOXL", "sell"]])

    def test_r_c_not_met_without_p_r2_buys_and_met_with_one(self):
        self.assertEqual(self.judge([session_row()])["R_C"]["verdict"], "NOT_MET")
        buy = session_row(tickets=[{"symbol": "NBIS", "side": "buy", "qty": 1, "price": 1.0, "r": "1/2"}])
        self.assertEqual(self.judge([session_row()], [buy])["R_C"]["verdict"], "MET")

    def test_anchor_codes(self):
        anchors = [{"order_date_kst": "2026-10-09", "symbol": "SOXL", "side": "sell"},
                   {"order_date_kst": "2026-10-09", "symbol": "MVLL", "side": "sell"},
                   {"order_date_kst": "2026-09-01", "symbol": "SOXL", "side": "sell"}]
        out = self.judge([session_row()], anchors=anchors)
        codes = {(item["portfolio"], item["symbol"], item["order_date_kst"]): item["code"] for item in out["R_A"]["anchors"]}
        self.assertEqual(codes[("P-R1", "SOXL", "2026-10-09")], "SELL_CIRCUIT_CLOSED")
        self.assertEqual(codes[("P-R1", "MVLL", "2026-10-09")], "NOT_HELD_IN_PORTFOLIO")
        self.assertEqual(codes[("P-R1", "SOXL", "2026-09-01")], "NO_DATA")
        self.assertEqual(out["R_A"]["verdict"], "NOT_PASSED")

    def test_pre_registered_values(self):
        self.assertEqual(replay.PERIOD, ("2026-07-10", "2026-10-09"))
        self.assertEqual(replay.PORTFOLIOS["P-R1"]["holdings"], {"MVLL": 159, "SOXL": 53, "NBIS": 13})
        self.assertEqual(replay.PORTFOLIOS["P-R1"]["cash"], Decimal("12467.71"))
        self.assertEqual(replay.PORTFOLIOS["P-R2"]["holdings"], {"NBIS": 13})
        self.assertEqual(set(tk.ALLOWED_NO_TICKET), {"DEADBAND", "LOT_ZERO", "CASH_ZERO", "REGRET_ZERO", "G2B_CAP"})
        self.assertEqual(replay.EARNINGS_KNOWN_DAYS, 30)


class OneImplementationTests(unittest.TestCase):
    def test_session_end_and_order_window_have_one_implementation(self):
        """r3 R3-4: decide's F6 uses tickets_module.ticket_session_ended and order_days; the replay has no outcome
        path of its own (each session independent) and no copy of either rule."""
        import inspect

        import auto_core_decide as decide_module

        source = inspect.getsource(decide_module.read_outcomes)
        self.assertIn("tickets_module.ticket_session_ended", source)
        self.assertIn("tickets_module.order_days", source)
        self.assertNotIn("timedelta", source)
        replay_source = inspect.getsource(replay)
        for word in ("classify_outcome", "read_outcomes", "issued_day", "ord_dt"):
            self.assertNotIn(word, replay_source)
        scripts = Path(replay.__file__).parent
        for name in ("def ticket_session_ended", "def order_days"):
            owners = [path.name for path in sorted(scripts.glob("auto_core*.py")) if name in path.read_text(encoding="utf-8")]
            self.assertEqual(owners, ["auto_core_tickets.py"], name)


@unittest.skipUnless(PAGES.is_dir() and MEASUREMENTS.is_file(), "saved 30-minute pages exist only in the main checkout")
class RealDataSmokeTests(unittest.TestCase):
    def test_four_symbol_replay_finishes_without_exceptions(self):
        with tempfile.TemporaryDirectory() as folder:
            out = io.StringIO()
            with redirect_stdout(out):
                code = replay.main(["--start", "2026-09-01", "--end", "2026-10-09", "--run-id", "smoke",
                                    "--output-root", folder])
            summary = json.loads(out.getvalue().strip().splitlines()[-1])
            self.assertEqual((code, summary["exceptions"], summary["schema_errors"]), (0, 0, []))


if __name__ == "__main__":
    unittest.main()
