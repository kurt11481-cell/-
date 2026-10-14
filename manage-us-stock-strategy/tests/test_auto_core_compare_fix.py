"""cmp-fix: an event group that is hit gets its B2 margin from the session that fired it; the single-stock cap
set is compared by ticker. Display and compare classification only (states, tickets, gates unchanged)."""

from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
TESTS = ROOT / "manage-us-stock-strategy/tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(TESTS))

import auto_core_compare as cmp  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import helpers  # noqa: E402
import test_auto_core_decide as decide_fixture  # noqa: E402
from portfolio_review_journal import auto_core_payloads  # noqa: E402
from auto_core_rules import C, _at  # noqa: E402


def old_group_margins(series, c8):
    """group_margins as it was before cmp-fix (every group at the last session), kept verbatim as the reference."""
    t = len(series["close"]) - 1
    close = series["close"][t]
    p_e20, p_atr = _at(series["ema20"], t - 1), _at(series["atr14"], t - 1)

    def gap(value, line):
        return None if value is None or line is None or not close else abs(value - line) / close

    def least(*values):
        known = [value for value in values if value is not None]
        return min(known) if known else None

    band1 = None if p_e20 is None or p_atr is None else C["C1_ATR_BAND"] * p_atr
    band2 = None if p_e20 is None or p_atr is None else C["C2_ATR_BAND"] * p_atr
    e20, e10 = series["ema20"][t], series["ema10"][t]
    hi_prev, lo_prev = _at(series["hi20"], t - 1), _at(series["lo20"], t - 1)
    rsi = series["rsi14"][t]
    one = c8.get("one_day")
    ret = series["ret1"][t]
    return {
        "overheat": gap(close, None if band1 is None else p_e20 + band1),
        "oversold": gap(close, None if band1 is None else p_e20 - band1),
        "overheat_fade": gap(series["high"][t], None if band2 is None else p_e20 + band2),
        "oversold_rebound": gap(series["low"][t], None if band2 is None else p_e20 - band2),
        "trend_break": gap(close, e20), "trend_recover": gap(close, e20),
        "false_breakout": gap(close, hi_prev), "false_breakdown": gap(close, lo_prev),
        "new_high": least(gap(close, series["hi20"][t]), gap(close, e10)),
        "new_low": least(gap(close, series["lo20"][t]), gap(close, e10)),
        "rebound_fail": gap(close, e20), "pullback_rebound": gap(close, e20),
        "crash_alert": None if ret is None or one is None else abs(abs(ret) - one),
        "spike_alert": None if ret is None or one is None else abs(abs(ret) - one),
        "rsi_gap": None if rsi is None else min(abs(rsi - C["RSI_OVERBOUGHT"]), abs(rsi - C["RSI_OVERSOLD"])),
    }


def old_margins_patch():
    return mock.patch.object(rules, "group_margins", lambda series, c8, event_days=None: old_group_margins(series, c8))


BASE = helpers.zigzag(60, 100, 0.5)  # prior-20 close high 100.5, low 99.5


def false_breakout_closes(event_close, after):
    """C4- fires on the session after the breakout close 103 (event_close below the line 100.5), then `after`."""
    return BASE + [103.0, event_close] + list(after)


def evaluate(closes, *, entry=None):
    days = helpers.sessions("2026-01-05", len(closes))
    return rules.evaluate_symbol(symbol="X", role="held", bars=helpers.bars("X", days, closes),
                                 calendar=helpers.calendar(days), evaluation_session=days[-1], registry_entry=entry,
                                 held=True, member=False, multiplier=1, facts=[], buy_approved=True)


def series_of(closes):
    days = helpers.sessions("2026-01-05", len(closes))
    return rules.build_series(helpers.bars("X", days, closes)["adjusted"], days, days[-1])


def run_without_hit(result):
    """An integrated check run copy without any trigger hit (same close as the core)."""
    return {"date": "2026-10-13", "basis": "2026-10-12 TEST", "status": [], "triggers": [],
            "tickers": [{"code": "X", "close": result["indicators"]["close"]}]}


def decision_of(result, **extra):
    return {"evaluation_session": "2026-10-12", "symbols": {"X": result}, "buy_requirements": [], "exposure": {},
            **extra}


class EventDayMarginTests(unittest.TestCase):
    def test_t1_hit_event_group_uses_the_firing_session(self):
        closes = false_breakout_closes(100.4, [97.0, 96.0])  # fired at t-2
        series = series_of(closes)
        t, event = len(closes) - 1, len(closes) - 3
        raw = rules.raw_common(series, rules.c8_thresholds(None, 1))
        self.assertEqual([i for i in range(t - 4, t + 1) if raw["C4-"][i] is True], [event])
        self.assertEqual(rules._event_day(raw["C4-"], raw["C4+"], t), event)
        line = max(closes[event - 21:event - 1])
        expected = abs(closes[event] - line) / closes[event]
        self.assertLessEqual(expected, 0.01)
        self.assertGreater(old_group_margins(series, rules.c8_thresholds(None, 1))["false_breakout"], 0.05)
        result = evaluate(closes)
        self.assertEqual(result["groups"]["false_breakout"]["state"], "hit")
        self.assertAlmostEqual(result["margins"]["false_breakout"], expected, places=12)
        found = cmp.compare(decision_of(result), run_without_hit(result), {}, research_ok=True)
        item = next(item for item in found["items"] if item["item_key"] == "X:false_breakout")
        self.assertEqual((item["category"], item["core"], item["llm"]), ("B2", "hit", False))
        # Before cmp-fix the same difference was B7 (the last-session margin).
        with old_margins_patch():
            before = evaluate(closes)
        found = cmp.compare(decision_of(before), run_without_hit(before), {}, research_ok=True)
        item = next(item for item in found["items"] if item["item_key"] == "X:false_breakout")
        self.assertEqual(item["category"], "B7")
        # Every other group keeps its last-session value.
        old = old_group_margins(series, rules.c8_thresholds(None, 1))
        self.assertEqual({k: v for k, v in result["margins"].items() if k != "false_breakout"},
                         {k: v for k, v in old.items() if k != "false_breakout"})

    def test_be_case_2026_10_13_numbers(self):
        # BE: breakout close 295.852 over the line 291.300, event close 291.22 (10-07), last close 262.33 (10-12).
        closes = helpers.zigzag(60, 290.8, 0.5) + [295.852, 291.22, 280.0, 270.0, 262.33]
        result = evaluate(closes)
        self.assertEqual(result["groups"]["false_breakout"]["state"], "hit")
        self.assertAlmostEqual(result["margins"]["false_breakout"], (291.3 - 291.22) / 291.22, places=9)
        self.assertAlmostEqual(old_group_margins(series_of(closes), rules.c8_thresholds(None, 1))["false_breakout"],
                               (295.852 - 262.33) / 262.33, places=9)
        found = cmp.compare(decision_of(result), run_without_hit(result), {}, research_ok=True)
        item = next(item for item in found["items"] if item["item_key"] == "X:false_breakout")
        self.assertEqual((item["category"], item["detail"]), ("B2", "MARGIN:0.0003<=0.01"))

    def test_t2_wide_event_day_margin_stays_b7(self):
        closes = false_breakout_closes(95.714, [95.0, 94.0])
        result = evaluate(closes)
        event = len(closes) - 3
        line = max(closes[event - 21:event - 1])
        self.assertEqual(result["groups"]["false_breakout"]["state"], "hit")
        self.assertAlmostEqual(result["margins"]["false_breakout"], abs(closes[event] - line) / closes[event], places=12)
        self.assertGreater(result["margins"]["false_breakout"], 0.049)
        found = cmp.compare(decision_of(result), run_without_hit(result), {}, research_ok=True)
        item = next(item for item in found["items"] if item["item_key"] == "X:false_breakout")
        self.assertEqual((item["category"], item["detail"]), ("B7", "UNEXPLAINED"))

    def test_t3_not_hit_event_groups_and_state_groups_keep_the_last_session(self):
        cases = {
            "out_of_window": false_breakout_closes(100.4, [97.0, 96.0, 96.5, 96.2, 96.4]),  # fired at t-5: none
            "flat": helpers.zigzag(70, 100, 1.0, 0.05),
            "falling": helpers.zigzag(70, 100, 1.0, 0.05) + [96.0, 95.0, 94.0],
        }
        for name, closes in cases.items():
            with self.subTest(case=name):
                result = evaluate(closes)
                old = old_group_margins(series_of(closes), rules.c8_thresholds(None, 1))
                self.assertEqual(set(result["margins"]), set(old))
                for group, value in result["margins"].items():
                    if group in rules.EVENT_MARGIN_GROUPS and result["groups"][group]["state"] == "hit":
                        continue
                    self.assertEqual(value, old[group], group)
        out_of_window = evaluate(cases["out_of_window"])
        self.assertEqual(out_of_window["groups"]["false_breakout"]["state"], "none")
        self.assertEqual(out_of_window["margins"],
                         old_group_margins(series_of(cases["out_of_window"]), rules.c8_thresholds(None, 1)))

    def test_unknown_event_state_keeps_the_last_session(self):
        closes = false_breakout_closes(100.4, [97.0, 96.0])
        days = helpers.sessions("2026-01-05", len(closes))
        bars = helpers.bars("X", days, closes, incomplete={days[-2]})
        result = rules.evaluate_symbol(symbol="X", role="held", bars=bars, calendar=helpers.calendar(days),
                                       evaluation_session=days[-1], registry_entry=None, held=True, member=False,
                                       multiplier=1, facts=[], buy_approved=True)
        series = rules.build_series(bars["adjusted"], days, days[-1])
        old = old_group_margins(series, rules.c8_thresholds(None, 1))
        for group in ("overheat_fade", "oversold_rebound"):
            self.assertNotEqual(result["groups"][group]["state"], "hit")
            self.assertEqual(result["margins"][group], old[group])

    def test_event_day_is_none_unless_hit(self):
        fired = [False] * 30
        fired[25] = True
        opposite = [False] * 30
        self.assertEqual(rules._event_day(fired, opposite, 29), 25)
        self.assertIsNone(rules._event_day(fired, opposite, -1))           # before the series: not hit
        resolved = list(opposite)
        resolved[27] = True
        self.assertIsNone(rules._event_day(fired, resolved, 29))           # opposite side fired since: none
        self.assertIsNone(rules._event_day([False] * 24 + [True] + [False] * 5, opposite, 29))  # t-5: none
        unknown = [False] * 30
        unknown[28] = None
        self.assertIsNone(rules._event_day(unknown, opposite, 29))         # unk
        both = list(fired)
        both[28] = True
        self.assertEqual(rules._event_day(both, resolved, 29), 28)         # the last firing, after the opposite

    def test_card_alias_of_an_event_rule_uses_its_firing_session(self):
        closes = [100.0] * 60 + [100.5, 100.3, 101.0, 100.9, 100.85]  # C6+ fires at t-2 only
        series = series_of(closes)
        t, event = len(closes) - 1, len(closes) - 3
        raw = rules.raw_common(series, rules.c8_thresholds(None, 1))
        self.assertEqual([i for i in range(t - 4, t + 1) if raw["C6+"][i] is True], [event])
        expected = abs(closes[event] - series["ema20"][event]) / closes[event]
        last = abs(closes[t] - series["ema20"][t]) / closes[t]
        self.assertGreater(abs(expected - last), 1e-4)
        card = [{"id": "U6", "kind": "pullback_rebound", "side": "+", "strength": "weak", "params": {},
                 "active_when": "held", "source": "docs/claude/x.md:1"}]
        for entry in (None, helpers.entry("X", role="holding", triggers=card)):
            with self.subTest(card=entry is not None):
                result = evaluate(closes, entry=entry)
                group = result["groups"]["pullback_rebound"]
                self.assertEqual((group["state"], group["ids"]), ("hit", ["U6"] if entry else ["C6+"]))
                self.assertAlmostEqual(result["margins"]["pullback_rebound"], expected, places=12)

    def test_research_groups_are_not_moved(self):
        self.assertNotIn("good_news_drop", rules.EVENT_MARGIN_GROUPS)
        self.assertNotIn("bad_news_rise", rules.EVENT_MARGIN_GROUPS)
        margins = rules.group_margins(series_of(BASE), rules.c8_thresholds(None, 1), {"trend_break": 3})
        self.assertEqual(margins, old_group_margins(series_of(BASE), rules.c8_thresholds(None, 1)))


NOTIONAL = chr(0xBA85) + chr(0xBAA9)  # Korean "notional" (ASCII source)
EXCESS = chr(0xCD08) + chr(0xACFC)    # Korean "excess"


class CapSetTests(unittest.TestCase):
    def caps(self, core, llm, basis="2026-10-12 TEST"):
        decision = {"evaluation_session": "2026-10-12", "symbols": {}, "buy_requirements": [],
                    "exposure": {"caps": core}}
        run = {"date": "2026-10-13", "basis": basis, "status": [], "account": {"exposure": {"capBreaches": llm}}}
        return next(item for item in cmp.compare(decision, run, {}, research_ok=True)["items"]
                    if item["item_key"] == "exposure:caps")

    def test_t4_cap_set_by_ticker(self):
        llm = [f"MVLL {NOTIONAL} 0.4111 > 0.4"]
        same = self.caps(["MVLL"], llm)
        self.assertEqual((same["category"], same["detail"], same["llm"], same["core"]), ("B1", "SAME", llm, ["MVLL"]))
        other = self.caps(["MVLL"], [f"SOXL {NOTIONAL} 0.5 > 0.4"])
        self.assertEqual((other["category"], other["detail"]), ("B7", "CAP_SET"))
        unparsed = self.caps(["MVLL"], [f"{NOTIONAL} {EXCESS}"])
        self.assertEqual((unparsed["category"], unparsed["detail"]), ("B7", "CAP_SET_UNPARSED"))
        empty = self.caps([], [])
        self.assertEqual((empty["category"], empty["detail"]), ("B1", "SAME"))

    def test_partial_parse_and_timing(self):
        mixed = self.caps(["MVLL"], [f"MVLL {NOTIONAL} 0.41 > 0.4", EXCESS])
        joined = self.caps(["MVLL"], [f"MVLL{NOTIONAL} 0.41"])  # no boundary after the ticker
        self.assertEqual((joined["category"], joined["detail"]), ("B7", "CAP_SET_UNPARSED"))
        self.assertEqual((mixed["category"], mixed["detail"]), ("B7", "CAP_SET_UNPARSED"))
        extra = self.caps(["MVLL"], ["MVLL 0.41", "SOXL 0.5"])
        self.assertEqual((extra["category"], extra["detail"]), ("B7", "CAP_SET"))
        lower = self.caps(["MVLL"], ["mvll 0.41"])
        self.assertEqual(lower["category"], "B7")
        late = self.caps(["MVLL"], ["SOXL 0.5"], basis="2026-10-09 TEST")
        self.assertEqual((late["category"], late["detail"]), ("B6", "CAP_SET"))
        plain = self.caps(["MVLL", "SOXL"], ["SOXL", "MVLL"])
        self.assertEqual(plain["category"], "B1")


def _without_margins(decision, root):
    """The record without margins and the journal block (it carries the identity hash over the margins), with
    the temporary folder replaced so two environments compare."""
    view = copy.deepcopy(decision)
    for symbol in (view.get("symbols") or {}).values():
        symbol.pop("margins", None)
    view.pop("journal", None)
    text = json.dumps(view, sort_keys=True, ensure_ascii=True)
    return json.loads(re.sub(re.escape(root.name), "<ROOT>", text))


SOXL_EVENT_BEFORE_T = helpers.zigzag(len(decide_fixture.DAYS) - 4, 100, 0.5) + [103.0, 100.4, 97.0, 96.0]


class InvarianceTests(unittest.TestCase):
    """T5: decide fixtures give the same record apart from the margins (and the identity hash over it)."""

    def run_pair(self, soxl_closes=None):
        decisions, roots = [], []
        for patched in (False, True):
            env = decide_fixture.Env()
            self.addCleanup(env.close)
            if soxl_closes is not None:
                env.bars["SOXL"] = helpers.bars("SOXL", decide_fixture.DAYS, soxl_closes)
            roots.append(env.root)
            if patched:
                with old_margins_patch():
                    decisions.append(env.run())
            else:
                decisions.append(env.run())
        return decisions, roots

    def test_t5_decide_record_unchanged_except_margins(self):
        for name, closes in (("default", None), ("two_new_cues", decide_fixture._soxl_two_new_cues()),
                             ("event_before_t", SOXL_EVENT_BEFORE_T)):
            with self.subTest(fixture=name):
                (new, old), (new_root, old_root) = self.run_pair(closes)
                for key in ("status", "reasons", "tickets", "blocked", "candidates", "buy_requirements", "evidence",
                            "no_action", "alerts", "alert_states", "exposure", "shock", "compare", "dashboard"):
                    self.assertEqual(new.get(key), old.get(key), key)
                for symbol, result in new["symbols"].items():
                    for key in ("groups", "triggers", "indicators", "status", "reasons"):
                        self.assertEqual(result[key], old["symbols"][symbol][key], f"{symbol}:{key}")
                self.assertEqual(_without_margins(new, new_root), _without_margins(old, old_root))
                self.assertEqual([t["decision_key"] for t in new["tickets"]], [t["decision_key"] for t in old["tickets"]])
                strip = [(kind, {k: v for k, v in payload.items() if k != "decision_sha256"})
                         for kind, payload in auto_core_payloads(new, "x")]
                self.assertEqual(strip, [(kind, {k: v for k, v in payload.items() if k != "decision_sha256"})
                                         for kind, payload in auto_core_payloads(old, "x")])

    def test_t5_margins_differ_only_for_hit_event_groups(self):
        (new, old), _roots = self.run_pair(SOXL_EVENT_BEFORE_T)
        changed = 0
        for symbol, result in new["symbols"].items():
            groups = result["groups"]
            for group, value in result["margins"].items():
                if value != old["symbols"][symbol]["margins"][group]:
                    self.assertIn(group, rules.EVENT_MARGIN_GROUPS, f"{symbol}:{group}")
                    self.assertEqual(groups[group]["state"], "hit", f"{symbol}:{group}")
                    changed += 1
        self.assertEqual(new["symbols"]["SOXL"]["groups"]["false_breakout"]["state"], "hit")
        self.assertEqual(changed, 1)  # SOXL false_breakout, measured on its firing session (t-2)


if __name__ == "__main__":
    unittest.main()
