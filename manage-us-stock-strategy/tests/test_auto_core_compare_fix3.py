"""cmp-fix3: an R-REC1 RG1 difference where the core is unknown because a session after the event has no valid
research record (r2 R2-4, shock.rg1_coverage.missing_sessions) is the pre-registered B4 RG1_NEEDS_RESEARCH_RECORD,
also when today's record is OK. Compare classification only (states, tickets, gates unchanged)."""

from __future__ import annotations

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))

import auto_core_compare as cmp  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import auto_core_tickets as tickets  # noqa: E402
import helpers  # noqa: E402


GAP = {"from": "2026-10-09", "to": "2026-10-12", "missing_sessions": ["2026-10-09"]}
NO_GAP = {"from": "2026-10-09", "to": "2026-10-12", "missing_sessions": []}
OK = {"s": "ok", "t": "x"}


def core_shock(rg1="unk", coverage=GAP, by_symbol=None, **gates):
    """The decide record's top-level shock as on 2026-10-13 14:33 KST (EV3a 2026-10-08, RG2 and RG3 not met)."""
    rg = {"RG1": rg1, "RG2": "no", "RG3": "no", "RG4": "ok", **gates}
    return {"status": "unk", "open": True, "event": {"date": "2026-10-08", "kinds": ["EV3a"]}, "rg": rg,
            "reasons": [], "rg1_coverage": copy.deepcopy(coverage), "by_symbol": by_symbol or {}}


def run_copy(basis="2026-10-12 TEST", rg=None, rows=None):
    """The integrated check run copy: RG1 met, RG2 and RG3 not met, RG4 met (rg1 true on 2026-10-13)."""
    return {"date": "2026-10-13", "basis": basis, "status": [], "triggers": [],
            "shock": {"open": True, "rg": rg or {"rg1": True, "rg2": False, "rg3": False, "rg4": True}},
            "buyReq": {"rows": rows or []}}


def decision(shock, rows=None):
    return {"evaluation_session": "2026-10-12", "symbols": {}, "buy_requirements": rows or [], "exposure": {},
            "shock": shock}


def items(found):
    return {item["item_key"]: item for item in found["items"]}


def rrec(shock, *, research_ok=True, basis="2026-10-12 TEST", rg=None):
    found = cmp.compare(decision(shock), run_copy(basis=basis, rg=rg), {}, research_ok=research_ok)
    return items(found), found


class RgGapHelperTests(unittest.TestCase):
    def test_rg1_record_gap(self):
        self.assertTrue(cmp._rg1_record_gap({"rg1_coverage": GAP}))
        for value in (None, {}, [], "x", {"rg1_coverage": None}, {"rg1_coverage": NO_GAP},
                      {"rg1_coverage": {"missing_sessions": None}}, {"rg1_coverage": {"missing_sessions": "2026-10-09"}},
                      {"rg1_coverage": ["2026-10-09"]}, {"rg1_coverage": {}}):
            with self.subTest(value=value):
                self.assertFalse(cmp._rg1_record_gap(value))

    def test_rrec1_output_carries_the_gap_the_helper_reads(self):
        # The real R-REC1 function: EV3a three sessions back, no research record on the session after it.
        days = helpers.sessions("2026-06-01", 75)
        bench = rules.build_series(helpers.bars("SOXX", days, helpers.zigzag(75, 100, 0.5))["adjusted"], days, days[-1])
        result = rules.rrec1(benchmark=bench, candidate=None, evaluation_session=days[-1], ev3_user_dates=[days[-4]],
                             thesis_damage=[], ev4_sessions=[], research_sessions=days[-2:])
        self.assertEqual(result["event"]["date"], days[-4])
        self.assertEqual(result["rg1_coverage"]["missing_sessions"], [days[-3]])
        self.assertEqual(result["rg"]["RG1"], "unk")
        self.assertTrue(cmp._rg1_record_gap(result))
        covered = rules.rrec1(benchmark=bench, candidate=None, evaluation_session=days[-1], ev3_user_dates=[days[-4]],
                              thesis_damage=[], ev4_sessions=[], research_sessions=days[-3:])
        self.assertEqual(covered["rg1_coverage"]["missing_sessions"], [])
        self.assertNotEqual(covered["rg"]["RG1"], "unk")
        self.assertFalse(cmp._rg1_record_gap(covered))


class RrecGateTests(unittest.TestCase):
    def test_t1_case_2026_10_13_is_b4(self):
        found, block = rrec(core_shock())
        item = found["RREC:RG1"]
        self.assertEqual((item["category"], item["detail"], item["core"], item["llm"]),
                         ("B4", "RG1_NEEDS_RESEARCH_RECORD", "unk", True))
        self.assertNotIn("RREC:RG1", block["unexplained"])
        for gate in ("RG2", "RG3", "RG4"):
            self.assertEqual(found[f"RREC:{gate}"]["category"], "B1", gate)
        self.assertEqual(block["categories"]["B4"], 1)
        self.assertEqual(block["categories"]["B7"], 0)

    def test_t2_unknown_without_a_gap_stays_b7(self):
        for coverage in (NO_GAP, None):
            with self.subTest(coverage=coverage):
                found, block = rrec(core_shock(coverage=coverage))
                self.assertEqual((found["RREC:RG1"]["category"], found["RREC:RG1"]["detail"]), ("B7", "UNEXPLAINED"))
                self.assertIn("RREC:RG1", block["unexplained"])

    def test_t3_damage_fact_with_a_gap_stays_b7(self):
        found, block = rrec(core_shock(rg1="no"))
        self.assertEqual((found["RREC:RG1"]["category"], found["RREC:RG1"]["detail"]), ("B7", "UNEXPLAINED"))
        self.assertIn("RREC:RG1", block["unexplained"])

    def test_core_ok_is_unchanged(self):
        found, _block = rrec(core_shock(rg1="ok"))
        self.assertEqual(found["RREC:RG1"]["category"], "B1")
        found, block = rrec(core_shock(rg1="ok"), rg={"rg1": False, "rg2": False, "rg3": False, "rg4": True})
        self.assertEqual((found["RREC:RG1"]["category"], found["RREC:RG1"]["detail"]), ("B7", "UNEXPLAINED"))

    def test_t4_research_record_not_ok_is_b4_as_before(self):
        for shock in (core_shock(), core_shock(coverage=NO_GAP), core_shock(rg1="no", coverage=None)):
            with self.subTest(rg1=shock["rg"]["RG1"], coverage=shock["rg1_coverage"]):
                found, _block = rrec(shock, research_ok=False)
                self.assertEqual((found["RREC:RG1"]["category"], found["RREC:RG1"]["detail"]),
                                 ("B4", "RG1_NEEDS_RESEARCH_RECORD"))

    def test_t6_timing_comes_first(self):
        found, _block = rrec(core_shock(), basis="2026-10-09 TEST")
        self.assertEqual((found["RREC:RG1"]["category"], found["RREC:RG1"]["detail"]),
                         ("B6", "LLM_RUN_SESSION_OR_INCOMPLETE"))

    def test_other_gates_keep_their_categories(self):
        # A gap never moves RG2-RG4: RG3 stays B2 (L0 definition), RG2 and RG4 stay B7.
        found, _block = rrec(core_shock(), rg={"rg1": True, "rg2": True, "rg3": True, "rg4": False})
        self.assertEqual(found["RREC:RG2"]["category"], "B7")
        self.assertEqual((found["RREC:RG3"]["category"], found["RREC:RG3"]["detail"]), ("B2", "L0_REGULAR_LOW_DEFINITION"))
        self.assertEqual(found["RREC:RG4"]["category"], "B7")


def symbol_shock(rg1="unk", rg2="ok", rg3="ok", rg4="ok", *, open_=True, status="unk"):
    return {"status": status, "open": open_, "rg": {"RG1": rg1, "RG2": rg2, "RG3": rg3, "RG4": rg4}}


def fifth_cell(shock):
    """Cell (5) as decide builds it (auto_core_tickets.buy_requirements) for a held index ETF."""
    row = tickets.buy_requirements(
        symbol="SOXL", held=True, s7={"fresh": True, "e": 1.0}, nominal={"n": 1.0}, peaks={}, earnings=None,
        calendar_sessions=[], buy_session=None, evaluation_session="2026-10-12", generated_at=None,
        cash=Decimal("1000"), close=Decimal("10"), check={"entry": {}}, evidence={"basis_met": True, "composition": "x"},
        watch_status=None, m6={"s": "ok", "t": "x"}, shock={**shock, "reasons": []}, research_block=None)
    return row["c"][4]


class BuyRequirementFiveTests(unittest.TestCase):
    def fifth(self, by_symbol_entry, *, coverage=GAP, research_ok=True, basis="2026-10-12 TEST", llm_s="ok",
              core_cell=None):
        by_symbol = {} if by_symbol_entry is None else {"SOXL": by_symbol_entry}
        cell = core_cell or fifth_cell(by_symbol_entry or symbol_shock())
        rows = [{"code": "SOXL", "add": True, "c": [OK, OK, OK, OK, cell]}]
        llm_rows = [{"code": "SOXL", "c": [OK, OK, OK, OK, {"s": llm_s, "t": "y"}]}]
        found = cmp.compare(decision(core_shock(coverage=coverage, by_symbol=by_symbol), rows),
                            run_copy(basis=basis, rows=llm_rows), {}, research_ok=research_ok)
        return items(found)["buyReq:SOXL:5"], found

    def test_cell_five_is_unknown_for_rg1_alone(self):
        self.assertEqual(fifth_cell(symbol_shock())["s"], "unk")
        self.assertEqual(fifth_cell(symbol_shock(rg2="no"))["s"], "unk")
        self.assertEqual(fifth_cell(symbol_shock(rg1="no", rg2="no", status="no"))["s"], "no")
        self.assertEqual(fifth_cell(symbol_shock(open_=None))["s"], "unk")  # EV3 (b) record gap
        self.assertEqual(fifth_cell(symbol_shock(open_=False, status="ok"))["s"], "ok")

    def test_t5_rg1_alone_with_a_gap_is_b4(self):
        item, found = self.fifth(symbol_shock())
        self.assertEqual((item["category"], item["detail"], item["core"], item["llm"]),
                         ("B4", "RG1_NEEDS_RESEARCH_RECORD", "unk", "ok"))
        self.assertNotIn("buyReq:SOXL:5", found["unexplained"])
        for index in (1, 2, 3, 4):
            self.assertEqual(items(found)[f"buyReq:SOXL:{index}"]["category"], "B1")

    def test_t5_other_gate_not_ok_stays_b7(self):
        for gates in ({"rg2": "no"}, {"rg3": "no"}, {"rg4": "unk"}, {"rg2": "unk"}):
            with self.subTest(gates=gates):
                item, found = self.fifth(symbol_shock(**gates))
                self.assertEqual((item["category"], item["detail"]), ("B7", "UNEXPLAINED"))
                self.assertIn("buyReq:SOXL:5", found["unexplained"])

    def test_t5_narrowing_other_reasons_stay_b7(self):
        cases = {
            "no_symbol_entry": dict(by_symbol_entry=None),
            "no_gap": dict(by_symbol_entry=symbol_shock(), coverage=NO_GAP),
            "no_coverage": dict(by_symbol_entry=symbol_shock(), coverage=None),
            "ev3b_record_gap": dict(by_symbol_entry=symbol_shock(open_=None)),   # settle(): open None
            "event_closed": dict(by_symbol_entry=symbol_shock(open_=False, status="ok"),
                                 core_cell={"s": "unk", "t": "x"}),
            "rg1_no": dict(by_symbol_entry=symbol_shock(rg1="no", status="no")),
            "core_cell_no": dict(by_symbol_entry=symbol_shock(), core_cell={"s": "no", "t": "x"}),
        }
        for name, kwargs in cases.items():
            with self.subTest(case=name):
                item, _found = self.fifth(**kwargs)
                self.assertEqual((item["category"], item["detail"]), ("B7", "UNEXPLAINED"))

    def test_research_not_ok_and_timing_as_before(self):
        item, _found = self.fifth(symbol_shock(rg2="no"), research_ok=False)
        self.assertEqual((item["category"], item["detail"]), ("B4", "RG1_NEEDS_RESEARCH_RECORD"))
        item, _found = self.fifth(symbol_shock(), basis="2026-10-09 TEST")
        self.assertEqual((item["category"], item["detail"]), ("B6", "LLM_RUN_SESSION_OR_INCOMPLETE"))

    def test_same_state_stays_b1(self):
        item, _found = self.fifth(symbol_shock(), llm_s="unk")
        self.assertEqual(item["category"], "B1")


class DayPassesTests(unittest.TestCase):
    def test_t7_day_passes_when_other_b7_are_llm_errors(self):
        # T1 record with two more B7 (RG2, RG4: core no / LLM met), both explained as LLM_ERROR.
        rg = {"rg1": True, "rg2": True, "rg3": False, "rg4": True}
        found, block = rrec(core_shock(RG4="no"), rg=rg)
        self.assertEqual(found["RREC:RG1"]["category"], "B4")
        self.assertEqual(sorted(block["unexplained"]), ["RREC:RG2", "RREC:RG4"])
        explained = [{"date": "2026-10-13", "item_key": key, "verdict": "LLM_ERROR"} for key in block["unexplained"]]
        self.assertTrue(cmp.day_passes("2026-10-13", block["unexplained"], explained))
        self.assertEqual(cmp.streak([("2026-10-13", block)], explained), 1)
        # Without the gap the same day keeps RG1 unexplained and does not pass.
        _found, before = rrec(core_shock(RG4="no", coverage=NO_GAP), rg=rg)
        self.assertIn("RREC:RG1", before["unexplained"])
        self.assertFalse(cmp.day_passes("2026-10-13", before["unexplained"], explained))
        self.assertEqual(cmp.streak([("2026-10-13", before)], explained), 0)
        # A CORE_BUG on that day still fails it.
        bug = explained + [{"date": "2026-10-13", "item_key": "RREC:RG3", "verdict": "CORE_BUG"}]
        self.assertFalse(cmp.day_passes("2026-10-13", block["unexplained"], bug))


if __name__ == "__main__":
    unittest.main()
