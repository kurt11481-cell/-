from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def locate_strategy_system_root() -> Path:
    configured = os.environ.get("STOCK_STRATEGY_SYSTEM_ROOT")
    if configured:
        candidate = Path(configured).resolve()
        if (candidate / "alert_policy.json").is_file():
            return candidate
        raise RuntimeError(
            "STOCK_STRATEGY_SYSTEM_ROOT does not contain alert_policy.json: "
            f"{candidate}"
        )

    candidates = [
        SKILL_ROOT.parent / "stock-strategy-system",
        SKILL_ROOT.parents[1],
        Path.cwd() / "stock-strategy-system",
    ]
    for candidate in candidates:
        candidate = candidate.resolve()
        if (candidate / "alert_policy.json").is_file():
            return candidate
    raise RuntimeError("cannot locate stock-strategy-system from the skill test path")


SYSTEM_ROOT = locate_strategy_system_root()
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVALUATOR = load_module("evaluate_alerts_integration", SCRIPTS / "evaluate_alerts.py")
VALIDATOR = load_module(
    "validate_technical_snapshot_integration",
    SCRIPTS / "validate_technical_snapshot.py",
)


class EvaluateTimingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads((SYSTEM_ROOT / "alert_policy.json").read_text(encoding="utf-8"))
        self.state = json.loads((SYSTEM_ROOT / "portfolio_state.json").read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc)
        session_date = now.date()
        self.state["last_confirmed_broker_snapshot"]["as_of"] = session_date.isoformat()
        self.state["last_confirmed_broker_snapshot"]["as_of_timestamp_kst"] = now.isoformat()
        fixture = VALIDATOR.valid_fixture()
        fixture["generated_at_utc"] = now.isoformat()
        fixture["session"].update(
            {
                "us_session_date": session_date.isoformat(),
                "expected_us_session_date": session_date.isoformat(),
                "is_trading_day": True,
                "regular_session_complete": True,
                "is_early_close": False,
                "official_calendar_verified": True,
                "calendar_verification_status": "verified_trading_day",
                "calendar_source_type": "official_exchange_or_regulator",
                "calendar_verified_at_utc": now.isoformat(),
            }
        )
        template = fixture["symbols"]["TEST"]
        symbols = {}
        fixed_end = date.fromisoformat(template["timing_window"][-1]["bar_date"])
        shift = session_date - fixed_end
        for symbol in ("SOXL", "MVLL", "SOXX", "MRVL", "DRAM", "NBIS", "BE"):
            row = copy.deepcopy(template)
            row["ticker"] = symbol
            row["bar_date"] = session_date.isoformat()
            row["quote_crosscheck"]["bar_date"] = session_date.isoformat()
            row["quote_crosscheck"]["verified_at_utc"] = now.isoformat()
            for bar in row["timing_window"]:
                original = date.fromisoformat(bar["bar_date"])
                bar["bar_date"] = (original + shift).isoformat()
            symbols[symbol] = row
        fixture["symbols"] = symbols
        self.snapshot = fixture

    def test_active_policy_generates_only_review_candidate(self) -> None:
        result = EVALUATOR.evaluate(self.state, self.policy, self.snapshot, {})
        self.assertEqual(result["grade"], "B", result)
        active = [item for item in result["candidates"] if item["grade"] == "B"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["symbol"], "MVLL")
        self.assertEqual(active[0]["tranche_id"], "MVLL-R25")
        self.assertEqual(active[0]["quantity"], 99)
        self.assertFalse(active[0]["actionable"])
        self.assertTrue(all(item["quantity"] is None for item in result["watchlist"]))
        self.assertTrue(active[0]["evidence_verification"]["all_required_evidence_verified"])
        self.assertTrue(
            all(item["status"] == "watch_only_zero_cash" for item in result["watchlist"])
        )

    def test_stale_broker_state_fails_closed(self) -> None:
        stale = copy.deepcopy(self.state)
        session = date.fromisoformat(self.snapshot["session"]["us_session_date"])
        stale["last_confirmed_broker_snapshot"]["as_of"] = (
            session - timedelta(days=5)
        ).isoformat()
        result = EVALUATOR.evaluate(stale, self.policy, self.snapshot, {})
        self.assertEqual(result["grade"], "F")

    def test_unreconciled_holding_change_fails_closed(self) -> None:
        broken = copy.deepcopy(self.state)
        broken["holdings"]["SOXL"] = 98
        result = EVALUATOR.evaluate(broken, self.policy, self.snapshot, {})
        self.assertEqual(result["grade"], "F")
        self.assertTrue(any("anchor" in item for item in result["warnings"]))

    def test_exact_one_share_nbil_de_minimis_exception_does_not_cause_mismatch(self) -> None:
        result = EVALUATOR.evaluate(self.state, self.policy, self.snapshot, {})
        self.assertNotEqual(result["state"], "STATE_MISMATCH", result)
        self.assertNotIn(
            "NBIL", [item["symbol"] for item in result["candidates"]]
        )

    def test_nbil_de_minimis_share_cap_fails_closed(self) -> None:
        broken = copy.deepcopy(self.state)
        broken["holdings"]["NBIL"] = 2
        broken["position_cost_basis_usd"]["NBIL"] = 130.4
        result = EVALUATOR.evaluate(broken, self.policy, self.snapshot, {})
        self.assertEqual(result["state"], "STATE_MISMATCH")
        self.assertEqual(result["grade"], "F")
        self.assertTrue(any("1-share cap" in item for item in result["warnings"]))

    def test_nbil_de_minimis_cost_basis_cap_fails_closed(self) -> None:
        broken = copy.deepcopy(self.state)
        broken["position_cost_basis_usd"]["NBIL"] = 65.21
        result = EVALUATOR.evaluate(broken, self.policy, self.snapshot, {})
        self.assertEqual(result["state"], "STATE_MISMATCH")
        self.assertEqual(result["grade"], "F")
        self.assertTrue(any("cost-basis cap" in item for item in result["warnings"]))

    def test_explicitly_confirmed_nbil_exit_can_leave_zero_without_inferred_fill(self) -> None:
        reconciled = copy.deepcopy(self.state)
        reconciled["holdings"]["NBIL"] = 0
        reconciled["position_cost_basis_usd"]["NBIL"] = 0
        reconciled["average_cost_usd"]["NBIL"] = 0
        result = EVALUATOR.evaluate(reconciled, self.policy, self.snapshot, {})
        self.assertNotEqual(result["state"], "STATE_MISMATCH", result)

    def test_technical_validation_failure_does_not_hide_hard_risk(self) -> None:
        broken = copy.deepcopy(self.snapshot)
        broken["symbols"]["SOXL"]["quote_crosscheck"] = None
        broken["symbols"]["SOXL"]["close"] = 90.0
        broken["symbols"]["SOXL"]["low"] = 89.0
        result = EVALUATOR.evaluate(self.state, self.policy, broken, {})
        self.assertEqual(result["grade"], "D", result)
        hard = [
            item
            for item in result["candidates"]
            if item["event_type"] == "holding_max_loss_breach"
            and item["symbol"] == "SOXL"
        ][0]
        self.assertEqual(hard["evaluated_grade"], "D")

    def test_missing_held_ohlcv_provenance_fails_closed(self) -> None:
        broken = copy.deepcopy(self.snapshot)
        broken["symbols"]["SOXL"]["source"] = None
        result = EVALUATOR.evaluate(self.state, self.policy, broken, {})
        self.assertEqual(result["state"], "DATA_INCOMPLETE")
        self.assertEqual(result["grade"], "F")
        self.assertTrue(any("market-data source" in item for item in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
