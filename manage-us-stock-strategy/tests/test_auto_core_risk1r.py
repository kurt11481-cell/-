"""risk1r: display-only 1R (EMA20 - 0.75 ATR14 invalidation) on buy tickets, journal and ticket scoring.

GOLDEN holds the canonical hashes of the ticket and blocked lists of the existing fixtures, measured on the
code before this change (base 5ed21b4); with the risk_1r key removed the tickets must hash the same (T4).
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "manage-us-stock-strategy/tests"
sys.path.insert(0, str(TESTS))

import test_auto_core_decide as decide_tests  # noqa: E402
import test_auto_core_tickets as tickets_tests  # noqa: E402
import test_score_ticket_outcomes as score_tests  # noqa: E402

decide_module = tickets_tests.decide_module
tk = tickets_tests.tk
helpers = tickets_tests.helpers
validate_instance = tickets_tests.validate_instance
TICKET_SCHEMA = tickets_tests.TICKET_SCHEMA
journal_module = decide_tests.journal_module
scorer = score_tests.scorer
forbidden_keys = score_tests.forbidden_keys

# Measured on base 5ed21b4 (before risk1r) with the same fixtures; a change here means a ticket changed.
GOLDEN = {
    "default": "a62e2e538cebc610e15f771d84754ec18d9f5b3b145aa00e35900780f60b3d2c",
    "g2b": "0857c795b26629af20982b09bb815f995ccb1d7340b9ea580031b3c6ac28bca9",
    "cash5": "c3ad82a2d647e0da1a14fa5a65fe7545f52cf509d16af8e576b1826c0f4ec4c8",
    "research_block": "8254e97e2e1ea50b89e966120d83e942bc32d1bd34a0c19eaac3e83252273091",
    # t2rc-corefix2: MU (R-REC1 open, requirement 5 no) is no longer the redeployment candidate, so the SOXL sell
    # regret table keeps only the cash columns (qty 19, r 1/3 unchanged); docs/claude/t2rc-corefix2-report.md.
    "sell": "07c781346ca9dfa243a83e826f83759e0e57751b7f1b02eb3fb52b9e716cdfb0",
    "pwr": "85e3651e053e32a99d1c61ace526692810c14a2c76b7ce3a32fce0aca53d7133",
    "decide_compare": "929a8d0059f7743b733826bc6f731d47d07a9f2868349c681173b06aab323492",
    "decide_apply": "431712bf43bcbb315a612c6f56492e7dc2e4fa175910f409aec84c281f383e71",
}
OK_LINE = "1R(표시만) 무효선 $95.00 · 기준가 대비 -5.0% (2.0σ) · 약 $50 = 자산 0.50% · 자동 매도 없음"


def _strip(ticket):
    return {key: value for key, value in ticket.items() if key != "risk_1r"}


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode()).hexdigest()


def _plan_view(planned):
    return {"tickets": [_strip(ticket) for ticket in planned["tickets"]], "blocked": planned["blocked"],
            "no_action": planned["no_action"], "candidates": planned["candidates"]}


def _scenarios():
    scenario = tickets_tests.Scenario
    sell = scenario(holdings={"SOXL": 120}, cash="300",
                    soxx=helpers.zigzag(len(tickets_tests.DAYS) - 1, 500, 2.0, 0.3) + [470.0])
    sell.bars["SOXL"] = helpers.bars("SOXL", tickets_tests.DAYS, tickets_tests.SellTicketTests().falling())
    pwr = scenario(extra_members=("PWR",))
    pwr.facts.append({**pwr.facts[0], "fact_id": "PWR-FACT-1", "symbol": "PWR"})
    return {"default": scenario(), "g2b": scenario(config={"max_buy_ticket_pct_of_equity": 0.02}),
            "cash5": scenario(cash="5"), "research_block": scenario(research_block="MISSING"), "sell": sell, "pwr": pwr}


def _decide(mode):
    env = decide_tests.Env(holdings={"SOXL": 10}, decision_mode=mode)
    try:
        env.write_good_news()
        decision = env.run()
        entries = journal_module.load_journal(env.journal)
    finally:
        env.close()
    return decision, entries


def _buy_ctx(indicators=None):
    """A ctx for _buy_ticket alone: MU at 100, sigma 0.02, equity 10,000, target 0.4 -> 20 shares at r 1."""
    days = helpers.sessions("2026-10-01", 10)
    ctx = {"policy_instruments": {"MU"}, "equity": Decimal("10000"), "holdings": {}, "weights": {},
           "proposal_results": [{"symbol": "MU", "target_weight": 0.4, "status": "DISPLAY", "reasons": []}],
           "closes": {"MU": Decimal("100")}, "sigmas": {"MU": 0.02}, "cash": Decimal("100000"),
           "scenarios": {"MU": {"status": "ok", "up": 0.02, "down": -0.02, "worst_day": -0.03}},
           "checks": {"MU": {"entry": {}}}, "keys": {}, "config": {}, "mode": "compare",
           "issued_at": "2026-10-10 07:45 KST", "run_day": "2026-10-10", "evaluation_session": days[6],
           "buy_session": days[7], "calendar": helpers.calendar(days), "input_hashes": {}}
    if indicators is not None:
        ctx["indicators"] = indicators
    return ctx


def _buy(ctx):
    row = {"code": "MU", "add": False, "c": [{"s": "ok", "t": ""}] * 5 + [{"s": "wait", "t": ""}]}
    evidence = {"r_max": "1", "ids": ["MU:x"], "strong": ["MU-SE1"], "weak_kinds": ["trend"], "composition": "TEST"}
    blocked = []
    ticket = tk._buy_ticket(ctx, "MU", row, evidence, [], blocked)
    if ticket is not None:
        ticket["ticket_id"] = "AT-20261010-MU-1"  # plan() numbers tickets; _buy_ticket alone leaves None
    return ticket, blocked


class FormulaTests(unittest.TestCase):
    def test_t1_ok(self):
        item = tk.risk_1r(Decimal("100.00"), 98.0, 4.0, 0.025, 10, Decimal("10000"))
        self.assertEqual((item["status"], item["invalidation"], item["r_pct"], item["r_sigma"], item["loss_usd"],
                          item["loss_pct_equity"]), ("ok", "95.00", "0.050000", "2.00", "50.00", "0.005000"))
        self.assertEqual((item["basis"], item["grade"], item["display_only"]),
                         ("EMA20-0.75xATR14@evaluation_session", "D", True))
        for part in ("-5.0%", "2.0σ", "$50", "0.50%"):
            self.assertIn(part, item["line"])
        self.assertEqual(item["line"], OK_LINE)
        self.assertEqual(tk.risk_1r_share_text(item), "0.50")

    def test_invalidation_rounds_cents_down_and_ratios_half_up(self):
        # 98.333 - 0.75 x 2.111 = 96.74975 -> 96.74 (cent down); 3.26 / 100 = 0.0326 -> 1.304 sigma -> 1.30;
        # 7 x 3.26 = 22.82; 22.82 / 30,000 = 0.00076066.. -> 0.000761 (half up).
        item = tk.risk_1r(Decimal("100"), 98.333, 2.111, 0.025, 7, Decimal("30000"))
        self.assertEqual((item["invalidation"], item["r_pct"], item["r_sigma"], item["loss_usd"],
                          item["loss_pct_equity"]), ("96.74", "0.032600", "1.30", "22.82", "0.000761"))
        self.assertIn("-3.3%", item["line"])  # 3.26% -> 3.3 (half up)
        self.assertIn("1.3σ", item["line"])

    def test_t2_below_band(self):
        item = tk.risk_1r(Decimal("94.00"), 98.0, 4.0, 0.025, 10, Decimal("10000"))
        self.assertEqual((item["status"], item["invalidation"]), ("below_band", "95.00"))
        self.assertEqual([item[key] for key in ("r_pct", "r_sigma", "loss_usd", "loss_pct_equity")], [None] * 4)
        self.assertEqual(item["line"], "1R(표시만) 기준가가 무효선 $95.00 아래 — 셋업 없음")
        self.assertEqual(tk.risk_1r(Decimal("95.00"), 98.0, 4.0, 0.025, 10, Decimal("10000"))["status"], "below_band")
        self.assertIsNone(tk.risk_1r_share_text(item))

    def test_t3_missing_or_invalid_indicator_is_unk(self):
        for args in ((Decimal("100"), None, 4.0, 0.025, 10, Decimal("10000")),
                     (Decimal("100"), 98.0, None, 0.025, 10, Decimal("10000")),
                     (Decimal("100"), 98.0, 4.0, None, 10, Decimal("10000")),
                     (Decimal("100"), float("nan"), 4.0, 0.025, 10, Decimal("10000"))):
            item = tk.risk_1r(*args)
            self.assertEqual((item["status"], item["reason"], item["line"]), ("unk", "INDICATOR_MISSING",
                                                                             "1R 확인 필요(지표 없음)"))
            self.assertEqual([item[key] for key in ("invalidation", "r_pct", "r_sigma", "loss_usd",
                                                    "loss_pct_equity")], [None] * 5)
        self.assertEqual(tk.risk_1r(Decimal("100"), 98.0, 4.0, 0.0, 10, Decimal("10000"))["reason"],
                         "INDICATOR_INVALID")
        self.assertIsNone(tk.risk_1r_share_text(None))


class BuyTicketRiskTests(unittest.TestCase):
    def test_t3_ticket_is_issued_the_same_with_or_without_indicators(self):
        full, blocked_full = _buy(_buy_ctx({"MU": {"ema20": 98.0, "atr14": 4.0}}))
        missing, blocked_missing = _buy(_buy_ctx())
        empty, _ = _buy(_buy_ctx({"MU": {"ema20": None, "atr14": None}}))
        self.assertIsNotNone(full, blocked_full)
        self.assertEqual(blocked_full, blocked_missing)
        self.assertEqual(full["risk_1r"]["status"], "ok")
        self.assertEqual((full["qty"], full["risk_1r"]["loss_usd"]), (20, "100.00"))
        for other in (missing, empty):
            self.assertEqual(other["risk_1r"]["status"], "unk")
            self.assertEqual(_strip(other), _strip(full))
        for ticket in (full, missing, empty):
            self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [])

    def test_a_failing_calculation_is_unk_and_the_ticket_stays(self):
        reference, _ = _buy(_buy_ctx({"MU": {"ema20": 98.0, "atr14": 4.0}}))
        with mock.patch.object(tk, "risk_1r", side_effect=[ArithmeticError("boom"), tk.risk_1r(
                None, None, None, None, None, None)]):
            ticket, blocked = _buy(_buy_ctx({"MU": {"ema20": 98.0, "atr14": 4.0}}))
        self.assertEqual(blocked, [])
        self.assertEqual((ticket["risk_1r"]["status"], ticket["risk_1r"]["reason"]), ("unk", "CALC_FAILED"))
        self.assertEqual(_strip(ticket), _strip(reference))
        self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [])

    def test_1r_is_computed_after_the_final_quantity(self):
        # Cash caps 20 shares to 9: the 1R loss uses the final 9.
        ctx = _buy_ctx({"MU": {"ema20": 98.0, "atr14": 4.0}})
        ctx["cash"] = Decimal("1000")
        ticket, _ = _buy(ctx)
        self.assertEqual(ticket["qty"], 9)
        self.assertEqual(ticket["risk_1r"]["loss_usd"], format(Decimal(9) * (Decimal("100") - Decimal("95.00")), "f"))


class UnchangedTicketTests(unittest.TestCase):  # T4, T5
    def test_tickets_without_risk_1r_hash_as_before(self):
        results = {name: item.run() for name, item in _scenarios().items()}
        views = {name: _plan_view(result["planned"]) for name, result in results.items()}
        decisions = {"decide_compare": _decide("compare")[0], "decide_apply": _decide("apply")[0]}
        for name, decision in decisions.items():
            views[name] = {"tickets": [_strip(ticket) for ticket in decision["tickets"]],
                           "blocked": decision["blocked"], "no_action": decision["no_action"], "keys": decision["keys"]}
        measured = {name: _digest(view) for name, view in views.items()}
        self.assertEqual(measured, GOLDEN, json.dumps(measured, indent=1))
        # The comparison is not empty: buy tickets exist and carry a computed 1R (indicators reached the ticket).
        buys = [ticket for result in results.values() for ticket in result["planned"]["tickets"]
                if ticket["side"] == "buy"] + [ticket for decision in decisions.values()
                                               for ticket in decision["tickets"] if ticket["side"] == "buy"]
        self.assertGreaterEqual(len(buys), 4)
        for ticket in buys:
            self.assertIn(ticket["risk_1r"]["status"], ("ok", "below_band"), ticket["risk_1r"])
            self.assertEqual(validate_instance(ticket, TICKET_SCHEMA), [])

    def test_t5_sell_tickets_have_no_1r(self):
        results = [item.run() for item in _scenarios().values()]
        sells = [ticket for result in results for ticket in result["planned"]["tickets"] if ticket["side"] == "sell"]
        ctx = {"gate0": {"ok": True}, "gate1": {"ok": True}, "closes": {"SOXL": Decimal("100")},
               "sigmas": {"SOXL": 0.03}, "equity": Decimal("20000"), "holdings": {"SOXL": 100}, "weights": {"SOXL": 0.5},
               "cash": Decimal("1000"), "scenarios": {"SOXL": {"status": "ok", "up": 0.05, "down": -0.05,
                                                                "worst_day": -0.04}},
               "keys": {}, "config": {}, "mode": "compare", "issued_at": "2026-10-10 07:45 KST", "run_day": "2026-10-10",
               "indicators": {"SOXL": {"ema20": 98.0, "atr14": 4.0}}, "input_hashes": {}, "model_for": None}
        days = helpers.sessions("2026-10-01", 10)
        ctx.update(evaluation_session=days[6], buy_session=days[7], calendar=helpers.calendar(days))
        evidence = {"r_max": "1", "ids": ["SOXL:x"], "strong": ["F"], "weak_kinds": [], "composition": "TEST"}
        direct = tk._sell_ticket(ctx, "SOXL", "CARD_EXIT", Decimal(0), evidence, {"entry": {}}, [], [])
        self.assertIsNotNone(direct)
        for ticket in sells + [direct]:
            self.assertEqual(ticket["side"], "sell")
            self.assertNotIn("risk_1r", ticket)
            self.assertIsNone(decide_module._risk1r_line(ticket))


class DisplayTests(unittest.TestCase):  # T6, T7
    def test_compare_mode_shows_the_line_on_run_core_tickets(self):
        decision, _ = _decide("compare")
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
        ticket = decision["tickets"][0]
        self.assertEqual(ticket["note"], decide_module.NOT_FOR_ENTRY)
        row = decision["dashboard"]["runCore"]["tickets"][0]
        self.assertEqual(row["risk1r"], ticket["risk_1r"]["line"])
        self.assertTrue(row["risk1r"].startswith("1R"))
        self.assertEqual(decision["dashboard"]["orders"], [])

    def test_apply_mode_order_evidence_and_ticket_alert(self):
        decision, entries = _decide("apply")
        self.assertEqual(decision["status"], "OK", decision["reasons"])
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
        ticket = decision["tickets"][0]
        risk = ticket["risk_1r"]
        order = decision["dashboard"]["orders"][0]
        base = ticket["evidence"]["composition"] + f" · r {ticket['evidence']['r']}"
        self.assertEqual(order["evidence"], base + " · " + risk["line"])
        alert = next(item for item in decision["alerts"] if item["code"] == f"TICKET:{ticket['ticket_id']}")
        head = f"주문표 {ticket['ticker']} {ticket['qty']}주 LOC 매수 상한 ${ticket['price']}"
        if risk["status"] == "ok":
            self.assertEqual(alert["line"], head + f" · 1R 자산 {tk.risk_1r_share_text(risk)}%")
        else:
            self.assertEqual(alert["line"], head)
        self.assertEqual(entries["status"], "OK", entries["errors"])

    def test_alert_and_order_suffix_by_status(self):
        decision, _ = _decide("apply")
        base = copy.deepcopy(decision)
        ticket = base["tickets"][0]
        head = f"주문표 {ticket['ticker']} {ticket['qty']}주 LOC 매수 상한 ${ticket['price']}"
        for reference, ema20, suffix in (("100", 98.0, " · 1R 자산 0.50%"), ("94", 98.0, ""), ("100", None, "")):
            item = tk.risk_1r(Decimal(reference), ema20, 4.0, 0.025, 10, Decimal("10000"))
            base["tickets"][0] = {**ticket, "risk_1r": item}
            alerts, _states = decide_module.alert_candidates(decision=base, previous=None, mode="apply", exceptions=[],
                                                             previous_run_missing=False)
            line = next(alert["line"] for alert in alerts if alert["code"] == f"TICKET:{ticket['ticket_id']}")
            self.assertEqual(line, head + suffix)
            orders = decide_module._dashboard(base, "apply")["orders"]
            self.assertTrue(orders[0]["evidence"].endswith(" · " + item["line"]))
            self.assertEqual(decide_module._dashboard(base, "compare")["runCore"]["tickets"][0]["risk1r"], item["line"])

    def test_schemas_accept_each_status_and_no_key(self):
        decision, _ = _decide("compare")
        ticket = decision["tickets"][0]
        for item in (tk.risk_1r(Decimal("100"), 98.0, 4.0, 0.025, 10, Decimal("10000")),
                     tk.risk_1r(Decimal("94"), 98.0, 4.0, 0.025, 10, Decimal("10000")),
                     tk.risk_1r(Decimal("100"), None, 4.0, 0.025, 10, Decimal("10000"))):
            self.assertEqual(validate_instance({**ticket, "risk_1r": item}, TICKET_SCHEMA), [])
        self.assertEqual(validate_instance(_strip(ticket), TICKET_SCHEMA), [])
        self.assertNotEqual(validate_instance({**ticket, "risk_1r": {**ticket["risk_1r"], "extra": 1}}, TICKET_SCHEMA), [])


class JournalTests(unittest.TestCase):  # T6, T8
    def decision(self):
        decision, _ = _decide("compare")
        decision = copy.deepcopy(decision)
        buy = decision["tickets"][0]
        sell = {**_strip(buy), "ticket_id": "AT-20261010-SOXL-1", "ticker": "SOXL", "side": "sell"}
        decision["tickets"] = [sell, buy]
        return decision, buy

    def test_t8_payloads(self):
        decision, buy = self.decision()
        payloads = [payload for kind, payload in journal_module.auto_core_payloads(decision, "e" * 64)
                    if kind == "order_ticket"]
        sell_payload, buy_payload = payloads
        self.assertEqual(buy_payload["risk_1r"], {key: buy["risk_1r"][key] for key in
                                                  ("status", "invalidation", "r_pct", "r_sigma", "loss_pct_equity",
                                                   "grade")})
        self.assertEqual(buy_payload["evidence_weak_kinds"], buy["evidence"]["weak"])
        self.assertNotIn("risk_1r", sell_payload)
        self.assertEqual(sell_payload["evidence_weak_kinds"], buy["evidence"]["weak"])
        for payload in payloads:
            self.assertEqual(validate_instance(payload, journal_module.PAYLOAD_SCHEMA), [])
            self.assertEqual(payload["authority"], journal_module.TICKET_AUTHORITY)
            for key in ("ticket_id", "ticker", "side", "order_type", "price", "qty", "amount", "buy_session",
                        "decision_key", "price_rule", "evidence_r"):
                self.assertIn(key, payload)

    def test_apply_run_journals_the_1r_and_old_entries_still_load(self):
        _decision, entries = _decide("apply")
        self.assertEqual(entries["status"], "OK", entries["errors"])
        ticket_entry = next(entry for entry in entries["entries"] if entry["entry_type"] == "order_ticket")
        self.assertIn("risk_1r", ticket_entry["payload"])
        self.assertIn("evidence_weak_kinds", ticket_entry["payload"])
        old = copy.deepcopy(ticket_entry)
        for key in ("risk_1r", "evidence_weak_kinds"):
            old["payload"].pop(key)
        self.assertIsNone(journal_module._auto_core_inconsistency(old))
        extra = copy.deepcopy(ticket_entry)
        extra["payload"]["loss_note"] = "x"
        self.assertEqual(journal_module._auto_core_inconsistency(extra), "PAYLOAD_FIELDS_INVALID")
        missing = copy.deepcopy(ticket_entry)
        missing["payload"].pop("evidence_r")
        self.assertEqual(journal_module._auto_core_inconsistency(missing), "PAYLOAD_FIELDS_INVALID")


def _risk(status="ok", r_pct="0.050000"):
    return {"status": status, "invalidation": "95.00", "r_pct": r_pct if status == "ok" else None,
            "r_sigma": "2.00" if status == "ok" else None, "loss_pct_equity": "0.005000" if status == "ok" else None,
            "grade": "D"}


def _entry(ticket_id, risk=None, **kwargs):
    entry = score_tests.ticket_entry(ticket_id, **kwargs)
    if risk is not None:
        entry["payload"]["risk_1r"] = risk
    entry["payload"]["evidence_weak_kinds"] = ["trend"]
    return entry


class ScoreTests(unittest.TestCase):  # T9
    def test_r_multiple_only_for_filled_ok_buys(self):
        entries = [_entry("OK", _risk()), _entry("MISS", _risk(), cap="99"), _entry("BELOW", _risk("below_band")),
                   _entry("UNK", _risk("unk")), _entry("SELL", _risk(), side="sell", cap="99"), _entry("NONE"),
                   _entry("USER", _risk()), score_tests.outcome_entry("USER", "filled", filled=10, average="95"),
                   _entry("SKIP", _risk()), score_tests.outcome_entry("SKIP", "not_entered")]
        compare = {**score_tests.compare_ticket("CMP"), "risk_1r": {**_risk(), "loss_usd": "50.00", "line": "x"},
                   "evidence": {"weak": ["trend", "volume"]}}
        report = score_tests.score(entries, records=[compare])
        row = score_tests.row_of(report, "OK")
        self.assertEqual(row["risk_1r"], {"status": "ok", "r_pct": "0.050000", "r_sigma": "2.00"})
        self.assertEqual(row["evidence_weak_kinds"], ["trend"])
        self.assertEqual(score_tests.horizon(row["horizons"], 5)["vs_no_action"], "0.100000")
        self.assertEqual(score_tests.horizon(row["horizons"], 5)["r_multiple"], "2.000000")
        self.assertEqual(score_tests.horizon(row["horizons"], 20)["r_multiple"], "-2.000000")
        self.assertIsNone(score_tests.horizon(row["horizons"], 60)["r_multiple"])  # pending: no later close used
        for name in ("MISS", "BELOW", "UNK", "SELL", "NONE"):
            other = score_tests.row_of(report, name)
            self.assertEqual({item["r_multiple"] for item in other["horizons"]}, {None}, name)
        self.assertIsNone(score_tests.row_of(report, "NONE")["risk_1r"])
        user = score_tests.row_of(report, "USER")["user"]
        self.assertEqual(score_tests.horizon(user["horizons"], 5)["r_multiple"], "3.157900")  # 0.157895 / 0.05
        skipped = score_tests.row_of(report, "SKIP")["user"]
        self.assertEqual({item["r_multiple"] for item in skipped["horizons"]}, {None})
        cmp_row = score_tests.row_of(report, "CMP")
        self.assertEqual((cmp_row["risk_1r"]["r_pct"], cmp_row["evidence_weak_kinds"]), ("0.050000", ["trend", "volume"]))
        self.assertEqual(score_tests.horizon(cmp_row["horizons"], 5)["r_multiple"], "2.000000")
        self.assertEqual(report["ticket_summary"]["risk_1r_ok"], 6)  # OK, MISS, SELL, USER, SKIP, CMP (as recorded)
        self.assertFalse(report["ticket_summary"]["conclusion_allowed"])
        self.assertEqual(forbidden_keys(report), [])

    def test_render_adds_the_r_multiple_line_end(self):
        report = score_tests.score([_entry("OK", _risk()), _entry("NONE")])
        lines = scorer.render_report(report)
        ok_line = next(line for line in lines if line.startswith("- AAA buy apply") and "R 배수" in line)
        self.assertTrue(ok_line.endswith("R 배수(계획 1R 0.050000 대비, 등급 D) 5:2.000000 / 20:-2.000000 / 60:-"))
        self.assertEqual(sum(1 for line in lines if "R 배수" in line), 1)


if __name__ == "__main__":
    unittest.main()
