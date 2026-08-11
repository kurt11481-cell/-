from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "timing_engine.py"
SPEC = importlib.util.spec_from_file_location("timing_engine", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def technical_row() -> dict:
    return {
        "open": 100.0,
        "close": 100.0,
        "close_prev": 101.0,
        "ema10": 102.0,
        "ema20": 103.0,
        "ema20_prev": 103.5,
        "ema10_above_ema20": False,
        "ema10_direction_3d": "falling",
        "ema20_direction_3d": "falling",
        "atr14": 4.0,
        "atr14_prev": 4.0,
        "prior_10d_low": 96.0,
        "prior_10d_low_prev": 95.0,
        "prior_20d_high": 115.0,
        "close_below_ema10_consecutive": 2,
        "decisive_breach_ema20": True,
        "ema20_failed_reclaim_confirmed": False,
        "ema10_reclaim_confirmed": False,
        "ema20_reclaim_confirmed": False,
        "overheat_rejection_confirmed": False,
        "failed_higher_high_confirmed": False,
        "average_dollar_volume_20d_usd": 50_000_000.0,
        "opening_gap_fraction": 0.01,
        "extension_above_ema20_atr": -0.75,
        "ma50": 98.0,
        "ma50_5d_ago": 97.0,
    }


class TimingEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = {
            "holding_timing_rules": {
                "status": "approved_review_only",
                "policy_version": "timing-v1",
                "positions": {
                    "SOXL": {
                        "anchor_shares": 99,
                        "confirmation_symbol": "SOXX",
                        "slots": [
                            {
                                "id": "SOXL-R25",
                                "quantity": 24,
                                "allowed_triggers": [
                                    "technical_stop",
                                    "weakness_20ema",
                                    "weakness_10ema",
                                ],
                            },
                            {
                                "id": "SOXL-R50",
                                "quantity": 24,
                                "allowed_triggers": ["technical_stop", "weakness_20ema"],
                            },
                            {
                                "id": "SOXL-FINAL-RESIDUAL",
                                "quantity": 51,
                                "allowed_triggers": [],
                            },
                        ],
                        "watch_only_triggers": [],
                    }
                },
                "weakness_rearm": {
                    "required_ema_by_confirmed_trigger": {
                        "technical_stop": 20,
                        "weakness_10ema": 10,
                        "weakness_20ema": 20,
                        "weakness_failed_reclaim": 20,
                        "strength_10ema_reclaim": 10,
                        "strength_20ema_reclaim": 20,
                        "strength_extension": 20,
                        "take_profit_rejection": 20,
                    },
                    "minimum_common_recovery_sessions": 1,
                    "minimum_completed_sessions_after_fill": 3,
                },
            }
        }
        self.state = {
            "strategy_version": "strategy-v1",
            "holdings": {"SOXL": 99},
            "average_cost_usd": {"SOXL": 123.32},
            "timing_plan": {
                "policy_version": "timing-v1",
                "positions": {
                    "SOXL": {
                        "anchor_id": "anchor-99",
                        "anchor_shares": 99,
                        "completed_tranche_ids": [],
                        "confirmed_tranche_fills": {},
                    }
                },
            },
        }

    def test_anchor_equation_and_first_slot_quantity(self) -> None:
        self.assertEqual(MODULE.timing_anchor_errors(self.state, self.policy), [])
        row = technical_row()
        proxy = technical_row()
        candidate, warnings = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=row,
            proxy_row=proxy,
            hard_boundary=98.656,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertEqual(warnings, [])
        self.assertEqual(candidate["tranche_id"], "SOXL-R25")
        self.assertEqual(candidate["quantity"], 24)
        self.assertEqual(candidate["trigger_path"], "weakness_20ema")
        self.assertEqual(candidate["grade"], "B")

    def test_next_slot_requires_confirmed_fill_and_holding_update(self) -> None:
        self.state["timing_plan"]["positions"]["SOXL"]["completed_tranche_ids"] = [
            "SOXL-R25"
        ]
        self.state["timing_plan"]["positions"]["SOXL"][
            "confirmed_tranche_fills"
        ] = {
            "SOXL-R25": {
                "session": "2026-01-02",
                "trigger_path": "weakness_20ema",
                "quantity": 24,
            }
        }
        self.assertNotEqual(MODULE.timing_anchor_errors(self.state, self.policy), [])
        self.state["holdings"]["SOXL"] = 75
        self.assertEqual(MODULE.timing_anchor_errors(self.state, self.policy), [])
        row = technical_row()
        row["timing_window"] = [
            {"bar_date": "2026-01-02", "close": 99.0, "ema10": 102.0, "ema20": 103.0},
            {"bar_date": "2026-01-05", "close": 110.0, "ema10": 104.0, "ema20": 105.0},
            {"bar_date": "2026-01-06", "close": 108.0, "ema10": 104.0, "ema20": 105.0},
            {"bar_date": "2026-01-07", "close": 100.0, "ema10": 102.0, "ema20": 103.0},
        ]
        proxy = technical_row()
        proxy["timing_window"] = list(row["timing_window"])
        candidate, _ = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=row,
            proxy_row=proxy,
            hard_boundary=98.656,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertEqual(candidate["tranche_id"], "SOXL-R50")
        self.assertTrue(candidate["rearm_gate"]["passed"])

    def test_next_weakness_slot_fails_closed_until_related_ema_recovery(self) -> None:
        plan = self.state["timing_plan"]["positions"]["SOXL"]
        plan["completed_tranche_ids"] = ["SOXL-R25"]
        plan["confirmed_tranche_fills"] = {
            "SOXL-R25": {
                "session": "2026-01-02",
                "trigger_path": "weakness_20ema",
                "quantity": 24,
            }
        }
        self.state["holdings"]["SOXL"] = 75
        row = technical_row()
        row["timing_window"] = [
            {"bar_date": "2026-01-02", "close": 99.0, "ema10": 102.0, "ema20": 103.0},
            {"bar_date": "2026-01-05", "close": 100.0, "ema10": 102.0, "ema20": 103.0},
        ]
        proxy = technical_row()
        proxy["timing_window"] = list(row["timing_window"])
        candidate, _ = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=row,
            proxy_row=proxy,
            hard_boundary=98.656,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertEqual(candidate["grade"], "E")
        self.assertIsNone(candidate["quantity"])
        self.assertTrue(any("no verified" in item for item in candidate["missing_conditions"]))

    def test_completed_tranche_without_exact_fill_record_fails_anchor_validation(self) -> None:
        plan = self.state["timing_plan"]["positions"]["SOXL"]
        plan["completed_tranche_ids"] = ["SOXL-R25"]
        self.state["holdings"]["SOXL"] = 75
        errors = MODULE.timing_anchor_errors(self.state, self.policy)
        self.assertTrue(any("fill record" in item for item in errors))

    def test_second_technical_stop_requires_ema20_rearm_and_three_session_cooldown(self) -> None:
        plan = self.state["timing_plan"]["positions"]["SOXL"]
        plan["completed_tranche_ids"] = ["SOXL-R25"]
        plan["confirmed_tranche_fills"] = {
            "SOXL-R25": {
                "session": "2026-01-02",
                "trigger_path": "weakness_20ema",
                "quantity": 24,
            }
        }
        self.state["holdings"]["SOXL"] = 75
        row = technical_row()
        row.update({"close": 90.0, "close_prev": 91.0})
        row["timing_window"] = [
            {"bar_date": "2026-01-02", "close": 99.0, "ema10": 102.0, "ema20": 103.0},
            {"bar_date": "2026-01-05", "close": 110.0, "ema10": 104.0, "ema20": 105.0},
            {"bar_date": "2026-01-06", "close": 90.0, "ema10": 102.0, "ema20": 103.0},
        ]
        proxy = technical_row()
        proxy["timing_window"] = list(row["timing_window"])
        candidate, _ = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=row,
            proxy_row=proxy,
            hard_boundary=80.0,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertTrue(candidate["trigger_states"]["technical_stop"])
        self.assertEqual(candidate["grade"], "E")
        self.assertTrue(
            any("cooldown" in item for item in candidate["missing_conditions"])
        )

        row["timing_window"] = [
            {"bar_date": "2026-01-02", "close": 99.0, "ema10": 102.0, "ema20": 103.0},
            {"bar_date": "2026-01-05", "close": 110.0, "ema10": 104.0, "ema20": 105.0},
            {"bar_date": "2026-01-06", "close": 108.0, "ema10": 104.0, "ema20": 105.0},
            {"bar_date": "2026-01-07", "close": 90.0, "ema10": 102.0, "ema20": 103.0},
        ]
        proxy["timing_window"] = list(row["timing_window"])
        candidate, _ = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=row,
            proxy_row=proxy,
            hard_boundary=80.0,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertEqual(candidate["trigger_path"], "technical_stop")
        self.assertEqual(candidate["grade"], "B")
        self.assertTrue(candidate["rearm_gate"]["cooldown_passed"])

    def test_soxl_weakness10_can_be_watch_only_without_reduction_quantity(self) -> None:
        rule = self.policy["holding_timing_rules"]["positions"]["SOXL"]
        rule["watch_only_triggers"] = ["weakness_10ema"]
        rule["slots"][0]["allowed_triggers"] = ["technical_stop", "weakness_20ema"]
        row = technical_row()
        row["decisive_breach_ema20"] = False
        candidate, _ = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=row,
            proxy_row=technical_row(),
            hard_boundary=80.0,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertEqual(candidate["event_type"], "holding_timing_watch")
        self.assertEqual(candidate["trigger_path"], "weakness_10ema")
        self.assertEqual(candidate["grade"], "B")
        self.assertIsNone(candidate["quantity"])
        self.assertIsNone(candidate["post_trade_shares"])

    def test_explicit_gap_and_halt_are_watch_only(self) -> None:
        rule = self.policy["holding_timing_rules"]["positions"]["SOXL"]
        rule["watch_only_triggers"] = ["gap_risk", "halt_risk"]
        rule["slots"][0]["allowed_triggers"] = ["technical_stop"]
        row = technical_row()
        row.update(
            {
                "open": 75.0,
                "close": 70.0,
                "opening_gap_fraction": 75.0 / 101.0 - 1,
                "close_below_ema10_consecutive": 0,
            }
        )
        candidate, _ = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=row,
            proxy_row=technical_row(),
            hard_boundary=80.0,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertEqual(candidate["trigger_path"], "gap_risk")
        self.assertIsNone(candidate["quantity"])

        halted = technical_row()
        halted.update(
            {
                "trading_status": "halted",
                "close": 70.0,
                "close_below_ema10_consecutive": 0,
            }
        )
        candidate, _ = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=halted,
            proxy_row=technical_row(),
            hard_boundary=80.0,
            rules_hash="rules",
            suppress_for_hard_risk=False,
        )
        self.assertEqual(candidate["trigger_path"], "halt_risk")
        self.assertIsNone(candidate["quantity"])

    def test_hard_risk_suppresses_timing_grade(self) -> None:
        candidate, warnings = MODULE.evaluate_holding_timing(
            state=self.state,
            policy=self.policy,
            symbol="SOXL",
            row=technical_row(),
            proxy_row=technical_row(),
            hard_boundary=98.656,
            rules_hash="rules",
            suppress_for_hard_risk=True,
        )
        self.assertEqual(candidate["grade"], "E")
        self.assertIsNone(candidate["quantity"])
        self.assertTrue(any("hard-risk" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
