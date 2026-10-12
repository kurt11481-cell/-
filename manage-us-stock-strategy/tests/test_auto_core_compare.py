"""Redesign T2 F9: pre-registered compare categories (prompt appendix B) and the explained-day streak."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manage-us-stock-strategy/scripts"))

import auto_core_compare as cmp  # noqa: E402
from validation_common import write_json  # noqa: E402


def decision(**overrides):
    base = {
        "run_day_kst": "2026-10-13", "evaluation_session": "2026-10-12",
        "symbols": {"SOXL": {"indicators": {"close": 100.0}, "margins": {"trend_break": 0.002, "overheat": 0.2,
                                                                         "rsi_gap": 15.0, "new_high": 0.2},
                             "groups": {"trend_break": {"state": "hit"}, "overheat": {"state": "none"},
                                        "good_news_drop": {"state": "none"}, "new_high": {"state": "none"}}}},
        "buy_requirements": [{"code": "MU", "c": [{"s": "no", "t": "막힘 EARNINGS_DATE_UNVERIFIED"},
                                                  {"s": "ok", "t": ""}, {"s": "ok", "t": ""}, {"s": "ok", "t": ""},
                                                  {"s": "ok", "t": ""}, {"s": "wait", "t": ""}]}],
        "exposure": {"N": 1.30, "caps": [], "peaks": [{"symbol": "SOXL", "state": "none"}]},
        "shock": {"open": True, "rg": {"RG1": "no", "RG2": "ok", "RG3": "no", "RG4": "ok"}},
    }
    base.update(overrides)
    return base


def run(**overrides):
    base = {
        "date": "2026-10-13", "basis": "2026-10-12 미국 정규장 종가 (잠정)",
        "status": [{"label": "점검 상태", "value": "정상"}],
        "tickers": [{"code": "SOXL", "close": 100.0}],
        "triggers": [{"code": "SOXL", "items": [{"id": "C3-·S4", "state": "hit"}, {"id": "S2", "state": "wait"},
                                                {"id": "C1-", "state": "near"}]}],
        "buyReq": {"rows": [{"code": "MU", "c": [{"s": "ok"}, {"s": "ok"}, {"s": "ok"}, {"s": "ok"}, {"s": "ok"},
                                                 {"s": "wait"}]}]},
        "account": {"exposure": {"n": 1.305, "capBreaches": []}},
        "peakReviews": [{"code": "SOXL", "state": "none"}],
        "shock": {"open": True, "rg": {"rg1": "no", "rg2": "ok", "rg3": "no", "rg4": "ok"}},
    }
    base.update(overrides)
    return base


REGISTRY = {"SOXL": {"card_triggers": [{"id": "S4", "kind": "ema20_below_twice"}, {"id": "S6", "kind": "drop_alert"}]}}


def items(block):
    return {item["item_key"]: item for item in block["items"]}


class CategoryTests(unittest.TestCase):
    def test_same_and_llm_only_and_near_is_not_a_hit(self):
        block = cmp.compare(decision(), run(), REGISTRY, research_ok=True)
        found = items(block)
        self.assertEqual(found["SOXL:trend_break"]["category"], "B1")
        self.assertEqual(found["SOXL:S2"]["category"], "B3")
        self.assertEqual(found["SOXL:overheat"]["category"], "B1")  # LLM near = not hit, core none
        self.assertEqual(found["exposure:N"]["category"], "B1")
        self.assertEqual(found["RREC:RG3"]["category"], "B1")

    def test_p_earn_precedence_is_b5(self):
        found = items(cmp.compare(decision(), run(), REGISTRY, research_ok=True))
        self.assertEqual(found["buyReq:MU:1"]["category"], "B5")

    def test_missing_research_record_is_b4(self):
        found = items(cmp.compare(decision(), run(), REGISTRY, research_ok=False))
        self.assertEqual(found["buyReq:MU:1"]["category"], "B4")
        core = decision()
        core["symbols"]["SOXL"]["groups"]["good_news_drop"]["state"] = "unk"
        llm = run()
        llm["triggers"][0]["items"].append({"id": "C7-", "state": "hit"})
        self.assertEqual(items(cmp.compare(core, llm, REGISTRY, research_ok=False))["SOXL:good_news_drop"]["category"],
                         "B4")

    def test_other_session_or_incomplete_run_is_b6(self):
        found = items(cmp.compare(decision(), run(basis="2026-10-09 미국 정규장 종가"), REGISTRY, research_ok=True))
        self.assertEqual(found["buyReq:MU:1"]["category"], "B6")
        llm = run(status=[{"label": "점검 상태", "value": "불완전(㉢)"}])
        llm["triggers"][0]["items"][0]["state"] = "none"
        self.assertEqual(items(cmp.compare(decision(), llm, REGISTRY, research_ok=True))["SOXL:trend_break"]["category"],
                         "B6")

    def test_near_the_line_is_b2_and_far_is_b7(self):
        llm = run()
        llm["triggers"][0]["items"][0]["state"] = "none"
        self.assertEqual(items(cmp.compare(decision(), llm, REGISTRY, research_ok=True))["SOXL:trend_break"]["category"],
                         "B2")  # margin 0.2% of the close
        core = decision()
        core["symbols"]["SOXL"]["margins"]["trend_break"] = 0.08
        block = cmp.compare(core, llm, REGISTRY, research_ok=True)
        self.assertEqual(items(block)["SOXL:trend_break"]["category"], "B7")
        self.assertEqual(block["unexplained"], ["SOXL:trend_break"])

    def test_no_run_record(self):
        block = cmp.compare(decision(), None, REGISTRY, research_ok=True)
        self.assertEqual((block["status"], block["items"]), ("NO_RECORD", []))

    def test_categories_are_the_pre_registered_seven(self):
        self.assertEqual(list(cmp.CATEGORIES), ["B1", "B2", "B3", "B4", "B5", "B6", "B7"])
        self.assertEqual((cmp.B2_PRICE_MARGIN, cmp.B2_RSI_MARGIN, cmp.B2_HLV_MARGIN, cmp.B2_KNOWN_MARGIN),
                         (0.01, 2.0, 0.03, 0.03))


class StrictCategoryTests(unittest.TestCase):
    """r2 R2-10: N and R5 differences are B2 only near the line; wide B2 items are listed (b2_wide)."""

    def n_category(self, llm_n):
        llm = run()
        llm["account"]["exposure"]["n"] = llm_n
        return items(cmp.compare(decision(), llm, REGISTRY, research_ok=True))["exposure:N"]["category"]

    def test_n_difference_boundary(self):
        self.assertEqual(self.n_category(1.33), "B2")    # |dN| = 0.03
        self.assertEqual(self.n_category(1.3301), "B7")  # above 0.03
        self.assertEqual(self.n_category(1.27), "B2")
        self.assertEqual(self.n_category(1.305), "B1")

    def r5_category(self, close):
        core = decision()
        core["exposure"]["peaks"] = [{"symbol": "SOXL", "state": "none", "peak": "100", "close": close}]
        llm = run()
        llm["peakReviews"] = [{"code": "SOXL", "state": "hit"}]
        return items(cmp.compare(core, llm, REGISTRY, research_ok=True))["R5:SOXL"]["category"]

    def test_r5_difference_boundary(self):
        self.assertEqual(self.r5_category("71"), "B2")     # 0.71: 1 point from 0.70
        self.assertEqual(self.r5_category("71.01"), "B7")  # 1.01 points from 0.70, 3.99 from 0.75
        self.assertEqual(self.r5_category("76"), "B2")     # 1 point from 0.75
        self.assertEqual(self.r5_category("76.01"), "B7")

    def test_wide_b2_items_are_listed(self):
        llm = run()
        llm["triggers"][0]["items"][0]["state"] = "none"
        core = decision()
        core["symbols"]["SOXL"]["margins"]["trend_break"] = 0.0101  # EMA group: B2 up to 3%
        block = cmp.compare(core, llm, REGISTRY, research_ok=True)
        self.assertEqual(items(block)["SOXL:trend_break"]["category"], "B2")
        self.assertEqual(block["b2_wide"], [{"item_key": "SOXL:trend_break", "margin": 0.0101, "limit": 0.03}])
        self.assertEqual(block["b2_wide_count"], 1)
        core["symbols"]["SOXL"]["margins"]["trend_break"] = 0.01
        narrow = cmp.compare(core, llm, REGISTRY, research_ok=True)
        self.assertEqual((narrow["b2_wide"], narrow["b2_wide_count"]), ([], 0))
        self.assertEqual(cmp.compare(decision(), None, REGISTRY, research_ok=True)["b2_wide"], [])

    def test_fail_or_early_end_resets_the_streak(self):
        compared = {"status": "COMPARED", "unexplained": []}
        self.assertEqual(cmp.streak([("2026-10-13", compared), ("2026-10-14", {"status": "NO_RECORD"}),
                                     ("2026-10-15", compared)], []), 2)
        for block in (cmp.streak_block({"status": "FAIL", "compare": compared}),
                      cmp.streak_block({"status": "HOLD", "compare": {"status": cmp.NOT_COMPARED}}),
                      cmp.streak_block(None)):
            with self.subTest(block=block):
                self.assertEqual(cmp.streak([("2026-10-13", compared), ("2026-10-14", block),
                                             ("2026-10-15", compared)], []), 1)
        self.assertEqual(cmp.streak_block({"status": "HOLD", "compare": compared}), compared)


class StreakTests(unittest.TestCase):
    def test_streak_counts_explained_days_and_skips_days_without_a_record(self):
        explained = [{"date": "2026-10-14", "item_key": "SOXL:trend_break", "verdict": "LLM_ERROR",
                      "rule_quote": "x", "note": ""}]
        days = [("2026-10-13", {"status": "COMPARED", "unexplained": []}),
                ("2026-10-14", {"status": "COMPARED", "unexplained": ["SOXL:trend_break"]}),
                ("2026-10-15", {"status": "NO_RECORD", "unexplained": []}),
                ("2026-10-16", {"status": "COMPARED", "unexplained": []})]
        self.assertEqual(cmp.streak(days, explained), 3)
        self.assertEqual(cmp.streak(days, []), 1)  # 10/14 unexplained resets to 0, then 10/16 counts
        bug = explained + [{"date": "2026-10-16", "item_key": "MU:x", "verdict": "CORE_BUG", "rule_quote": "x",
                            "note": ""}]
        self.assertEqual(cmp.streak(days, bug), 0)

    def test_a_no_new_session_day_keeps_the_streak(self):
        # r3 R3-3: a run without a new session judges nothing new; the count is neither raised nor reset.
        compared = {"status": "COMPARED", "unexplained": []}
        quiet = {"status": "OK", "no_new_session": True, "compare": {"status": cmp.NO_NEW_SESSION}}
        self.assertEqual(cmp.streak_block(quiet), {"status": cmp.NO_NEW_SESSION})
        self.assertEqual(cmp.streak([("2026-10-17", compared), ("2026-10-20", cmp.streak_block(quiet)),
                                     ("2026-10-21", compared)], []), 2)
        self.assertEqual(cmp.streak([("2026-10-17", compared), ("2026-10-20", cmp.streak_block(quiet))], []), 1)

    def test_explained_file_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "explained.json"
            write_json(path, {"schema_version": "redesign-t2-compare-explained-1.0", "items": [
                {"date": "2026-10-14", "item_key": "k", "verdict": "LLM_ERROR", "rule_quote": "q", "note": ""}]})
            self.assertEqual(len(cmp.load_explained(path)[0]), 1)
            write_json(path, {"schema_version": "redesign-t2-compare-explained-1.0", "items": [
                {"date": "2026-10-14", "item_key": "k", "verdict": "MAYBE", "rule_quote": "q", "note": ""}]})
            self.assertEqual(cmp.load_explained(path)[1][0], "EXPLAINED_FILE_INVALID")
            self.assertEqual(cmp.load_explained(Path(folder) / "missing.json"), ([], []))

    def test_cli_prints_the_block(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decision.json"
            write_json(path, {"run_day_kst": "2026-10-13", "compare": {"status": "COMPARED", "streak": 2,
                                                                     "unexplained": [], "categories": {}}})
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cmp.main(["--decision", str(path), "--explained", str(Path(folder) / "none.json")]), 0)
            self.assertEqual(json.loads(out.getvalue())["streak"], 2)


if __name__ == "__main__":
    unittest.main()
