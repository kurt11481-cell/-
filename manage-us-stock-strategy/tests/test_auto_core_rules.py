"""Redesign T2 F1: daily bars, indicators, common rules C1-C8, card triggers, V6, R5 and R-REC1.

Synthetic series and pages only (TEST_ONLY). Boundaries are tested one tick (0.01) on each side.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))

import auto_core_bars as bars_module  # noqa: E402
import auto_core_rules as rules  # noqa: E402
import helpers  # noqa: E402
from portfolio_exposure import _sample_std  # noqa: E402


def series(n=30, **overrides):
    """A flat synthetic series: close 100, EMA 100, ATR 5, RSI 50, prior-20 high 105 / low 95, volume 1000."""
    days = helpers.sessions("2026-06-01", n)
    base = {"days": days, "close": [100.0] * n, "high": [101.0] * n, "low": [99.0] * n, "volume": [1000.0] * n,
            "ret1": [0.0] * n, "ret5": [0.0] * n, "sigma60": [0.02] * n, "hi20": [105.0] * n, "lo20": [95.0] * n,
            "avgv20": [1000.0] * n, "position": [0.5] * n, "ema10": [100.0] * n, "ema20": [100.0] * n,
            "ema50": [100.0] * n, "rsi14": [50.0] * n, "atr14": [5.0] * n}
    for key, value in overrides.items():
        base[key] = value
    return base


def at(values, index, value):
    values = list(values)
    values[index] = value
    return values


C8 = {"one_day": 0.10, "five_day": None}


class IndicatorTests(unittest.TestCase):
    def test_ema_seeded_with_simple_mean(self):
        self.assertEqual(rules.ema_series([1.0, 2.0, 3.0, 4.0, 5.0], 3), [None, None, 2.0, 3.0, 4.0])

    def test_rsi_wilder(self):
        out = rules.rsi_series([1.0, 2.0, 3.0, 2.0, 3.0], 2)
        self.assertEqual(out[:2], [None, None])
        self.assertAlmostEqual(out[2], 100.0)
        self.assertAlmostEqual(out[3], 50.0)
        self.assertAlmostEqual(out[4], 75.0)

    def test_atr_wilder_and_incomplete_session_breaks_the_chain(self):
        highs = [None, 11.0, 12.0, 13.0, 14.0]
        lows = [None, 9.0, 10.0, 11.0, 12.0]
        closes = [10.0, 10.0, 11.0, 12.0, 13.0]
        out = rules.atr_series(highs, lows, closes, 2)
        self.assertEqual(out[1], None)
        self.assertAlmostEqual(out[2], 2.0)        # mean of TR 2, 2
        self.assertAlmostEqual(out[3], 2.0)        # (2 + 2) / 2
        broken = rules.atr_series([None, 11.0, None, 13.0, 14.0], [None, 9.0, None, 11.0, 12.0], closes, 2)
        self.assertEqual(broken[2:4], [None, None])
        self.assertAlmostEqual(broken[4], 2.0)     # re-seeded after two new true ranges

    def test_series_values(self):
        days = helpers.sessions("2026-01-05", 70)
        closes = helpers.zigzag(70, 100, 1.0, 0.1)
        built = rules.build_series(helpers.bars("X", days, closes)["adjusted"], days, days[-1])
        returns = [closes[index] / closes[index - 1] - 1 for index in range(1, 70)]
        self.assertAlmostEqual(built["sigma60"][-1], _sample_std(returns[-60:]))
        self.assertEqual(built["hi20"][-1], max(closes[-21:-1]))
        self.assertEqual(built["lo20"][-1], min(closes[-21:-1]))
        self.assertIsNone(built["sigma60"][59])
        self.assertIsNotNone(built["sigma60"][60])
        row = rules.indicator_row(built, 69)
        self.assertTrue(row["approximate_close"])
        self.assertAlmostEqual(row["intraday_drop"], built["low"][69] / closes[68] - 1)

    def test_series_starts_after_a_calendar_gap_and_missing_session_is_none(self):
        days = helpers.sessions("2026-01-05", 30)
        kept = days[:10] + days[11:]
        built = rules.build_series(helpers.bars("X", kept, [100.0] * 29)["adjusted"], days, kept[-1])
        self.assertEqual(built["days"][0], days[11])
        self.assertIsNone(rules.build_series(helpers.bars("X", kept, [100.0] * 29)["adjusted"], days, days[10]))


class CommonRuleBoundaryTests(unittest.TestCase):
    """One tick on each side of every line (t = last index; bands use EMA20 and ATR14 of t-1)."""

    def state(self, rule, data, opposite=None):
        raw = rules.raw_common(data, C8)
        return rules._status(rules.COMMON_RULES[rule][2], raw[rule], len(data["close"]) - 1,
                             raw.get(opposite) if opposite else None)

    def test_c1(self):
        self.assertEqual(self.state("C1-", series(close=at([100.0] * 30, 29, 110.00))), "hit")
        self.assertEqual(self.state("C1-", series(close=at([100.0] * 30, 29, 109.99))), "none")
        self.assertEqual(self.state("C1-", series(rsi14=at([50.0] * 30, 29, 70.0))), "hit")
        self.assertEqual(self.state("C1-", series(rsi14=at([50.0] * 30, 29, 69.99))), "none")
        self.assertEqual(self.state("C1+", series(close=at([100.0] * 30, 29, 90.00))), "hit")
        self.assertEqual(self.state("C1+", series(close=at([100.0] * 30, 29, 90.01))), "none")
        self.assertEqual(self.state("C1+", series(rsi14=at([50.0] * 30, 29, 30.0))), "hit")
        self.assertEqual(self.state("C1+", series(rsi14=at([50.0] * 30, 29, 30.01))), "none")

    def test_c2(self):
        hot = dict(position=at([0.5] * 30, 29, 0.35), volume=at([1000.0] * 30, 29, 1200.0))
        self.assertEqual(self.state("C2-", series(high=at([101.0] * 30, 29, 112.50), **hot)), "hit")
        self.assertEqual(self.state("C2-", series(high=at([101.0] * 30, 29, 112.49), **hot)), "none")
        self.assertEqual(self.state("C2-", series(high=at([101.0] * 30, 29, 112.50),
                                                  position=at([0.5] * 30, 29, 0.36),
                                                  volume=at([1000.0] * 30, 29, 1200.0))), "none")
        self.assertEqual(self.state("C2-", series(high=at([101.0] * 30, 29, 112.50),
                                                  position=at([0.5] * 30, 29, 0.35),
                                                  volume=at([1000.0] * 30, 29, 1199.0))), "none")
        cold = dict(position=at([0.5] * 30, 29, 0.65), volume=at([1000.0] * 30, 29, 1200.0))
        self.assertEqual(self.state("C2+", series(low=at([99.0] * 30, 29, 87.50), **cold)), "hit")
        self.assertEqual(self.state("C2+", series(low=at([99.0] * 30, 29, 87.51), **cold)), "none")

    def test_c2_incomplete_session_is_unknown(self):
        data = series(high=at([101.0] * 30, 29, None), low=at([99.0] * 30, 29, None),
                      volume=at([1000.0] * 30, 29, None), position=at([0.5] * 30, 29, None))
        self.assertEqual(self.state("C2-", data), "unk")

    def test_c3_needs_two_closes_and_the_one_before_on_the_other_side(self):
        closes = [101.0] * 27 + [101.0, 99.99, 99.99]
        self.assertEqual(self.state("C3-", series(close=closes)), "hit")
        self.assertEqual(self.state("C3-", series(close=[101.0] * 28 + [101.0, 99.99])), "none")
        self.assertEqual(self.state("C3-", series(close=[101.0] * 27 + [101.0, 100.0, 99.99])), "none")  # 100 not below
        self.assertEqual(self.state("C3+", series(close=[99.0] * 27 + [99.0, 100.01, 100.01])), "hit")

    def test_c4(self):
        closes = [100.0] * 28 + [105.01, 104.99]
        self.assertEqual(self.state("C4-", series(close=closes)), "hit")
        self.assertEqual(self.state("C4-", series(close=[100.0] * 28 + [105.01, 105.00])), "none")
        self.assertEqual(self.state("C4-", series(close=[100.0] * 28 + [105.00, 104.99])), "none")
        self.assertEqual(self.state("C4+", series(close=[100.0] * 28 + [94.99, 95.01])), "hit")

    def test_c5_two_session_hold_and_failed_breakout(self):
        hi = [105.0] * 30
        ema10 = [100.0] * 30
        one = series(close=[100.0] * 29 + [105.01], hi20=hi, ema10=ema10)
        self.assertEqual(self.state("C5+", one), "pending")
        two = series(close=[100.0] * 28 + [105.01, 105.01], hi20=hi, ema10=ema10)
        self.assertEqual(self.state("C5+", two), "hit")
        failed = series(close=[100.0] * 28 + [105.01, 104.99], hi20=hi, ema10=ema10)
        self.assertEqual(rules.raw_common(failed, C8)["C5+"][29], "fail")
        self.assertEqual(self.state("C5+", failed), "none")
        below_ema = series(close=[100.0] * 28 + [105.01, 105.01], hi20=hi, ema10=at(ema10, 29, 105.02))
        self.assertEqual(self.state("C5+", below_ema), "none")
        down = series(close=[100.0] * 28 + [94.99, 94.99], lo20=[95.0] * 30, ema10=ema10)
        self.assertEqual(self.state("C5-", down), "hit")

    def test_c6_within_one_and_a_half_percent(self):
        e20 = [100.0] * 30
        rebound = series(close=[100.0] * 27 + [102.0, 101.50, 101.60], ema20=e20)
        self.assertEqual(self.state("C6+", rebound), "hit")
        too_far = series(close=[100.0] * 27 + [102.0, 101.51, 101.60], ema20=e20)
        self.assertEqual(self.state("C6+", too_far), "none")
        fail = series(close=[100.0] * 27 + [98.0, 98.50, 98.40], ema20=e20)
        self.assertEqual(self.state("C6-", fail), "hit")
        self.assertEqual(self.state("C6-", series(close=[100.0] * 27 + [98.0, 98.49, 98.40], ema20=e20)), "none")

    def test_c6_minus_needs_the_rebound_session_to_close_up(self):
        # Rule line 110 "rebounded session" = c(t-1) > c(t-2), strict (prereg 79 (ii)).
        e20 = [100.0] * 30
        self.assertEqual(self.state("C6-", series(close=[100.0] * 27 + [98.0, 98.50, 98.40], ema20=e20)), "hit")
        self.assertEqual(self.state("C6-", series(close=[100.0] * 27 + [98.60, 98.50, 98.40], ema20=e20)), "none")
        self.assertEqual(self.state("C6-", series(close=[100.0] * 27 + [98.50, 98.50, 98.40], ema20=e20)), "none")

    def test_c6_plus_needs_the_pullback_session_to_close_down(self):
        # Rule line 110 "pulled-back session" = c(t-1) < c(t-2), strict (prereg 79 (ii)).
        e20 = [100.0] * 30
        self.assertEqual(self.state("C6+", series(close=[100.0] * 27 + [102.0, 101.50, 101.60], ema20=e20)), "hit")
        self.assertEqual(self.state("C6+", series(close=[100.0] * 27 + [101.40, 101.50, 101.60], ema20=e20)), "none")
        self.assertEqual(self.state("C6+", series(close=[100.0] * 27 + [101.50, 101.50, 101.60], ema20=e20)), "none")

    def test_c6_missing_close_two_sessions_back_is_unknown(self):
        e20 = [100.0] * 30
        minus = rules.raw_common(series(close=[100.0] * 27 + [None, 98.50, 98.40], ema20=e20), C8)
        self.assertIsNone(minus["C6-"][29])
        plus = rules.raw_common(series(close=[100.0] * 27 + [None, 101.50, 101.60], ema20=e20), C8)
        self.assertIsNone(plus["C6+"][29])

    def test_c6_mu_shape_falling_session_is_not_a_rebound(self):
        # MU 2026-10-05..10-13 closes and EMA20; 10-09 fell 0.72%, so 10-12 is not a C6- (it was before the fix).
        closes = [1063.71, 1045.44, 1087.84, 1035.47, 1028.00, 988.96, 953.19]
        e20 = [1035.27, 1036.24, 1041.15, 1040.61, 1039.41, 1034.60, 1026.85]
        data = series(close=[1200.0] * 23 + closes, ema20=[1000.0] * 23 + e20)
        raw = rules.raw_common(data, C8)
        self.assertIs(raw["C6+"][25], True)    # 10-07: 10-06 pulled back to within 1.5% above EMA20
        self.assertIs(raw["C6-"][28], False)   # 10-12: 10-09 closed below 10-08
        self.assertEqual([index for index in range(30) if raw["C6+"][index]], [25])
        self.assertEqual([index for index in range(30) if raw["C6-"][index]], [])
        self.assertEqual(self.state("C6+", data, "C6-"), "hit")
        self.assertEqual(self.state("C6-", data, "C6+"), "none")

    def test_c8_thresholds(self):
        self.assertEqual(self.state("C8-", series(ret1=at([0.0] * 30, 29, -0.10))), "hit")
        self.assertEqual(self.state("C8-", series(ret1=at([0.0] * 30, 29, -0.0999))), "none")
        self.assertEqual(self.state("C8+", series(ret1=at([0.0] * 30, 29, 0.10))), "hit")
        five = rules.raw_common(series(ret5=at([0.0] * 30, 29, -0.25)), {"one_day": 0.20, "five_day": 0.25})
        self.assertTrue(five["C8-"][29])
        self.assertEqual(rules.c8_thresholds(None, 3)["one_day"], 0.20)
        self.assertEqual(rules.c8_thresholds(None, 2)["one_day"], 0.15)
        self.assertEqual(rules.c8_thresholds(None, None)["one_day"], 0.10)

    def test_event_window_is_five_sessions_and_the_opposite_resolves(self):
        fired = [False] * 30
        self.assertEqual(rules._event_state(at(fired, 25, True), [False] * 30, 29), "hit")   # t-4
        self.assertEqual(rules._event_state(at(fired, 24, True), [False] * 30, 29), "none")  # t-5
        self.assertEqual(rules._event_state(at(fired, 25, True), at([False] * 30, 27, True), 29), "none")
        self.assertEqual(rules._event_state(at(at(fired, 25, True), 28, True), at([False] * 30, 27, True), 29), "hit")
        self.assertEqual(rules._event_state(at(fired, 28, None), [False] * 30, 29), "unk")


class C7Tests(unittest.TestCase):
    def setUp(self):
        self.days = helpers.sessions("2026-06-01", 30)
        self.calendar = helpers.calendar(self.days)

    def fact(self, direction="+", criterion=True, kind="contract", announced=None):
        return {"fact_id": "F1", "symbol": "X", "direction": direction, "kind": kind, "criterion_a": criterion,
                "announced_at": announced or f"{self.days[26]}T17:00:00-04:00", "event_session": self.days[26]}

    def test_good_news_then_close_below_pre_announcement_close(self):
        data = series(close=[100.0] * 27 + [101.0, 99.99, 100.0])
        data["days"] = self.days
        minus, plus, notes = rules.raw_c7(data, self.calendar, [self.fact()])
        self.assertTrue(minus[28])
        self.assertEqual(notes[0]["reference_close"], 100.0)
        self.assertEqual(rules._event_state(minus, plus, 29), "hit")

    def test_criterion_a_false_or_no_record(self):
        data = series(close=[100.0] * 27 + [101.0, 99.99, 100.0])
        data["days"] = self.days
        self.assertFalse(any(rules.raw_c7(data, self.calendar, [self.fact(criterion=False)])[0]))
        self.assertEqual(rules.raw_c7(data, self.calendar, None)[0][29], None)

    def test_bad_news_then_close_above(self):
        data = series(close=[100.0] * 27 + [99.0, 100.01, 100.0])
        data["days"] = self.days
        _minus, plus, _notes = rules.raw_c7(data, self.calendar, [self.fact(direction="-", kind="guidance")])
        self.assertTrue(plus[28])


class SymbolMergeTests(unittest.TestCase):
    def evaluate(self, closes, *, entry=None, held=True, member=False, approved=True, multiplier=1):
        days = helpers.sessions("2026-01-05", len(closes))
        return rules.evaluate_symbol(symbol="X", role="held" if held else "member",
                                     bars=helpers.bars("X", days, closes), calendar=helpers.calendar(days),
                                     evaluation_session=days[-1], registry_entry=entry, held=held, member=member,
                                     multiplier=multiplier, facts=[], buy_approved=approved)

    def falling(self):
        return helpers.zigzag(70, 100, 1.0, 0.05) + [96.0, 95.0, 94.0]

    def test_same_group_counts_once_with_the_card_alias_replacing_the_common_rule(self):
        triggers = [{"id": "S4", "kind": "ema20_below_twice", "side": "-", "strength": "weak", "params": {},
                     "active_when": "held", "source": "docs/claude/x.md:1"},
                    {"id": "V3", "kind": "ema_below", "side": "-", "strength": "weak", "params": {"ema": 10},
                     "active_when": "held", "source": "docs/claude/x.md:1"}]
        result = self.evaluate(self.falling(), entry=helpers.entry("X", role="holding", triggers=triggers))
        ids = [trigger["id"] for trigger in result["triggers"]]
        self.assertIn("S4", ids)
        self.assertNotIn("C3-", ids)  # replaced by the card definition
        group = result["groups"]["trend_break"]
        self.assertEqual(sorted(group["ids"]), ["S4", "V3"])
        evidence = rules.price_evidence(result, "-")
        self.assertEqual(evidence["groups"].count("trend_break"), 1)
        self.assertTrue(evidence["card_defined"])

    def test_card_trigger_only_when_held_or_member(self):
        trigger = [{"id": "U7", "kind": "ema20_below_twice", "side": "-", "strength": "weak", "params": {},
                    "active_when": "held_or_member", "source": "docs/claude/x.md:1"}]
        result = self.evaluate(self.falling(), entry=helpers.entry("X", triggers=trigger), held=False, member=False)
        self.assertNotIn("U7", [trigger["id"] for trigger in result["triggers"]])

    def test_buy_not_approved_instrument_is_labelled(self):
        result = self.evaluate(helpers.zigzag(70, 100, 1.0, 0.3), approved=False)
        plus = [trigger for trigger in result["triggers"] if trigger["side"] == "+"]
        self.assertTrue(plus and all(trigger.get("note") == "BUY_NOT_APPROVED_INSTRUMENT" for trigger in plus))

    def test_nocard_holding(self):
        result = self.evaluate(helpers.zigzag(70, 100, 1.0, 0.1))
        self.assertTrue(result["nocard"])
        self.assertIn(("NOCARD", "review"), [(t["id"], t["state"]) for t in result["triggers"]])

    def test_alert_state_is_review_not_evidence(self):
        result = self.evaluate(helpers.zigzag(70, 100, 1.0, 0.0) + [80.0])
        crash = next(trigger for trigger in result["triggers"] if trigger["id"] == "C8-")
        self.assertEqual(crash["state"], "review")
        self.assertNotIn("crash_alert", rules.price_evidence(result, "-")["groups"])

    def test_split_suspected_makes_everything_unknown(self):
        days = helpers.sessions("2026-01-05", 70)
        closes = [100.0] * 69 + [33.4]
        data = helpers.bars("X", days, closes)
        data["split_suspects"] = bars_module.split_suspects(data["adjusted"], days[-1])
        self.assertEqual(data["split_suspects"], [f"SPLIT_SUSPECTED:X:{days[-1]}"])
        result = rules.evaluate_symbol(symbol="X", role="held", bars=data, calendar=helpers.calendar(days),
                                       evaluation_session=days[-1], registry_entry=None, held=True, member=False,
                                       multiplier=1, facts=[], buy_approved=True)
        self.assertEqual(result["status"], "UNK")
        self.assertTrue(all(trigger["state"] in ("unk", "review") for trigger in result["triggers"]))
        self.assertEqual(rules.price_evidence(result, "-")["groups"], [])


class BarsFromPagesTests(unittest.TestCase):
    """auto_core_bars on saved-page shaped files: OHLCV of regular bars, INCOMPLETE, split adjustment."""

    def write_pages(self, folder: Path, days: list[str], *, missing: tuple[str, str] | None = None) -> None:
        rows = []
        for index, day in enumerate(days):
            opened = datetime.fromisoformat(f"{day}T09:30:00")
            for bar in range(13):
                stamp = (opened + timedelta(minutes=30 * bar)).strftime("%Y%m%d%H%M%S")
                if missing and (day, stamp[8:]) == missing:
                    continue
                price = 100 + index + bar * 0.1
                rows.append({"cur_prc": f"{price:.4f}", "trde_qty": "100", "open_pric": f"{price - 0.05:.4f}",
                             "high_pric": f"{price + 0.5:.4f}", "low_pric": f"{price - 0.5:.4f}", "cntr_tm": stamp,
                             "bus_dt": stamp[:8], "upd_stkpc_tp": "", "upd_rt": ""})
        last = days[-1].replace("-", "")
        rows.append({"cur_prc": "1.0000", "trde_qty": "1", "open_pric": "1.0000", "high_pric": "1.0000",
                     "low_pric": "1.0000", "cntr_tm": last + "160000", "bus_dt": last, "upd_stkpc_tp": "", "upd_rt": ""})
        rows.sort(key=lambda row: row["cntr_tm"], reverse=True)
        folder.mkdir(parents=True)
        (folder / "page.json").write_text(json.dumps({"return_code": 0, "result_list": rows}), encoding="utf-8")

    def test_regular_bars_make_the_daily_bar_and_close_equals_the_history(self):
        days = helpers.sessions("2026-07-06", 3)
        calendar = helpers.calendar(days)
        with tempfile.TemporaryDirectory() as root:
            self.write_pages(Path(root) / "X", days, missing=(days[1], "120000"))
            result = bars_module.daily_bars("X", Path(root) / "X", calendar)
        self.assertEqual(result["status"], "OK", result["errors"])
        first = result["sessions"][days[0]]
        self.assertEqual(first["close"], Decimal("101.2000"))      # 15:30 bar close (bar 12)
        self.assertEqual(first["open"], Decimal("99.9500"))        # 09:30 bar open
        self.assertEqual(first["high"], Decimal("101.7000"))
        self.assertEqual(first["low"], Decimal("99.5000"))
        self.assertEqual(first["volume"], Decimal("1300"))
        self.assertTrue(first["complete"])
        second = result["sessions"][days[1]]
        self.assertFalse(second["complete"])
        self.assertIsNone(second["high"])
        self.assertEqual(second["close"], Decimal("102.2000"))

    def test_split_record_adjusts_prices_and_volume(self):
        days = helpers.sessions("2026-07-06", 4)
        raw = helpers.bars("X", days, [300.0, 300.0, 100.0, 100.0])["raw"]
        action = {"symbol": "X", "effective_session": days[2], "new_shares": 3, "old_shares": 1,
                  "official_source": {"url": "https://example.com"}}
        adjusted, applied = bars_module.adjust_bars(raw, [action], days[-1])
        self.assertEqual(adjusted["sessions"][days[0]]["close"], Decimal("100"))
        self.assertEqual(adjusted["sessions"][days[0]]["volume"], Decimal("3000"))
        self.assertEqual(adjusted["sessions"][days[3]]["close"], Decimal("100.0"))
        self.assertEqual(applied[0]["price_factor"][:6], "0.3333")
        self.assertEqual(bars_module.split_suspects(adjusted, days[-1]), [])
        self.assertEqual(bars_module.split_suspects(raw, days[-1]), [f"SPLIT_SUSPECTED:X:{days[2]}"])

    def test_non_split_move_is_not_suspected(self):
        days = helpers.sessions("2026-07-06", 3)
        self.assertEqual(bars_module.split_suspects(helpers.bars("X", days, [100.0, 60.0, 61.0])["raw"], days[-1]), [])


class AccountAndShockTests(unittest.TestCase):
    def test_v6_lines(self):
        self.assertEqual(rules.v6_account(Decimal("26395.34"))["state"], "near")
        self.assertEqual(rules.v6_account(Decimal("26395.35"))["state"], "none")
        self.assertEqual(rules.v6_account(Decimal("25626.55"))["state"], "review")
        self.assertTrue(rules.v6_account(Decimal("22779.15"))["max_reached"])
        self.assertEqual(rules.v6_account(None)["state"], "unk")

    def test_r5_near_and_review(self):
        self.assertEqual(rules.r5_state({"status": "REVIEW_OPEN"}), "review")
        self.assertEqual(rules.r5_state({"status": "OK", "peak": "100", "close": "75"}), "near")
        self.assertEqual(rules.r5_state({"status": "OK", "peak": "100", "close": "75.01"}), "none")

    def test_ev3_dates_from_the_document_line(self):
        text = "- 이벤트 2026-10-08(EV3, 사용자 지정): ...\n- 이벤트 2026-1-1(EV3\nx - 이벤트 2026-10-09(EV3"
        self.assertEqual(rules.ev3_dates(text), ["2026-10-08"])

    def bench(self, closes, lows=None):
        days = helpers.sessions("2026-03-02", len(closes))
        data = helpers.bars("SOXX", days, closes, lows=lows)
        return rules.build_series(data["adjusted"], days, days[-1]), days

    def test_no_event_is_closed_and_missing_benchmark_is_unknown(self):
        quiet, _days = self.bench(helpers.zigzag(80, 500, 2.0, 0.3))
        result = rules.rrec1(benchmark=quiet, candidate=None, evaluation_session=quiet["days"][-1], ev3_user_dates=[],
                             thesis_damage=[])
        self.assertEqual((result["status"], result["open"]), ("ok", False))
        missing = rules.rrec1(benchmark=None, candidate=None, evaluation_session="2026-10-09", ev3_user_dates=[],
                              thesis_damage=[])
        self.assertEqual(missing["status"], "unk")

    def test_event_opens_and_gates_need_two_sessions_and_the_research_record(self):
        closes = helpers.zigzag(79, 500, 2.0, 0.3) + [470.0]
        crash, days = self.bench(closes)
        result = rules.rrec1(benchmark=crash, candidate=None, evaluation_session=days[-1], ev3_user_dates=[],
                             thesis_damage=[])
        self.assertTrue(result["open"])
        self.assertIn("EV1", result["event"]["kinds"])
        self.assertEqual(result["rg"]["RG1"], "no")      # 0 sessions after the event
        unknown = rules.rrec1(benchmark=crash, candidate=None, evaluation_session=days[-1], ev3_user_dates=[],
                              thesis_damage=None)
        self.assertEqual(unknown["rg"]["RG1"], "unk")   # no research record: RG1 unknown (buy blocked)
        user = rules.rrec1(benchmark=self.bench(helpers.zigzag(80, 500, 2.0, 0.3))[0], candidate=None,
                           evaluation_session=days[-1], ev3_user_dates=[days[-3]], thesis_damage=[])
        self.assertEqual(user["event"]["kinds"], ["EV3a"])

    def test_benchmark_choice(self):
        self.assertEqual(rules.rg2_benchmark("A1 전력(그리드 시공)"), "GRID")
        self.assertEqual(rules.rg2_benchmark("B1 메모리"), "SOXX")
        self.assertEqual(rules.rg2_benchmark(None), "SOXX")

    def test_m6_listing(self):
        self.assertEqual(rules.m6_listed("MU", [("m6-relative-comparison-7stock-x.md", "MU BE")])["s"], "ok")
        self.assertEqual(rules.m6_listed("AMD", [("m6-relative-comparison-7stock-x.md", "MU BE")])["s"], "no")
        self.assertEqual(rules.m6_listed("MU", [])["s"], "no")


class RecoveryCoverageTests(unittest.TestCase):
    """r2 R2-3 / R2-4: this session's EV4, RG1 over every session after the event, EV3 (b) record gaps."""

    def bench(self, closes):
        days = helpers.sessions("2026-03-02", len(closes))
        return rules.build_series(helpers.bars("SOXX", days, closes)["adjusted"], days, days[-1]), days

    def run_rrec1(self, data, **kwargs):
        arguments = dict(benchmark=data, candidate=None, evaluation_session=data["days"][-1], ev3_user_dates=[],
                         thesis_damage=[])
        arguments.update(kwargs)
        return rules.rrec1(**arguments)

    def crash(self, back):
        closes = helpers.zigzag(80, 500, 2.0, 0.3)
        index = len(closes) - 1 - back
        closes[index] = round(closes[index - 1] * 0.95, 4)  # EV1 (-2 sigma60 or worse)
        return closes, index

    def test_damage_fact_fifteen_sessions_back_keeps_rg1_no(self):
        closes, event = self.crash(17)
        data, days = self.bench(closes)
        clean = self.run_rrec1(data, research_sessions=days)
        self.assertEqual((clean["status"], clean["open"]), ("ok", False))  # recovered and closed
        damage = [{"fact_id": "D1", "event_session": days[event + 2], "root_thesis_damage": True}]
        damaged = self.run_rrec1(data, thesis_damage=damage, research_sessions=days)
        self.assertEqual((damaged["open"], damaged["rg"]["RG1"]), (True, "no"))
        self.assertEqual(damaged["rg1_coverage"], {"from": days[event + 1], "to": days[-1], "missing_sessions": []})

    def test_one_unrecorded_session_after_the_event_makes_rg1_unknown(self):
        closes, event = self.crash(8)
        data, days = self.bench(closes)
        missing = days[event + 1]  # the rebound day: not a 1-sigma fall, so no EV3 (b) gap
        result = self.run_rrec1(data, research_sessions=[day for day in days if day != missing])
        self.assertEqual((result["status"], result["open"], result["rg"]["RG1"]), ("unk", True, "unk"))
        self.assertEqual(result["rg1_coverage"]["missing_sessions"], [missing])
        self.assertFalse(any(reason.startswith("EV3B_RECORD_GAP") for reason in result["reasons"]))

    def fall(self, back, factor):
        closes = helpers.zigzag(80, 500, 2.0, 0.3)
        index = len(closes) - 1 - back
        closes[index] = round(closes[index - 1] * factor, 4)
        return closes, index

    def test_unrecorded_one_sigma_fall_after_the_first_record_is_unknown(self):
        closes, index = self.fall(5, 0.988)  # about -1.2%: at most -1 sigma60, above -2 sigma60
        data, days = self.bench(closes)
        self.assertLessEqual(data["ret1"][index], -data["sigma60"][index])
        self.assertGreater(data["ret1"][index], -2 * data["sigma60"][index])
        self.assertEqual(self.run_rrec1(data, research_sessions=days)["status"], "ok")
        gap = self.run_rrec1(data, research_sessions=[day for day in days if day != days[index]])
        self.assertEqual((gap["status"], gap["open"]), ("unk", None))
        self.assertIn(f"EV3B_RECORD_GAP:{days[index]}", gap["reasons"])

    def test_unrecorded_milder_day_has_no_effect(self):
        data, days = self.bench(helpers.zigzag(80, 500, 2.0, 0.3))
        mild = len(days) - 4
        self.assertLess(data["ret1"][mild], 0)
        self.assertGreater(data["ret1"][mild], -data["sigma60"][mild])
        result = self.run_rrec1(data, research_sessions=[day for day in days if day != days[mild]])
        self.assertEqual((result["status"], result["open"]), ("ok", False))

    def test_before_the_first_record_only_ev3a_counts(self):
        closes, index = self.fall(10, 0.988)
        data, days = self.bench(closes)
        later = days[index + 1:]  # the first research record comes after the fall
        result = self.run_rrec1(data, research_sessions=later)
        self.assertEqual((result["status"], result["open"], result["ev3b_coverage_start"]), ("ok", False, later[0]))
        user = self.run_rrec1(data, research_sessions=later, ev3_user_dates=[days[index]])
        self.assertEqual((user["status"], user["event"]["date"], user["event"]["kinds"]), ("ok", days[index], ["EV3a"]))


class ConstantsTableTests(unittest.TestCase):
    def test_every_constant_names_its_source(self):
        for name, (value, source) in rules.CONSTANTS.items():
            with self.subTest(constant=name):
                self.assertTrue(source.strip())
        expected = {"V6_HWM_USD": Decimal("28473.94"), "V6_FIRST_LINE_USD": Decimal("25626.55"),
                    "V6_APPROACH_USD": Decimal("26395.34"), "V6_MAX_LINE_USD": Decimal("22779.15"),
                    "RSI_OVERBOUGHT": 70, "RSI_OVERSOLD": 30, "C1_ATR_BAND": 2.0, "C2_ATR_BAND": 2.5,
                    "C6_BAND": 0.015, "RREC_EV1_SIGMA": 2.0, "RREC_EV2_SIGMA": 3.0, "RREC_RG4_SHORT_RATIO": 1.5,
                    "R5_NEAR_FRACTION": Decimal("0.75")}
        for name, value in expected.items():
            self.assertEqual(rules.C[name], value, name)


if __name__ == "__main__":
    unittest.main()
