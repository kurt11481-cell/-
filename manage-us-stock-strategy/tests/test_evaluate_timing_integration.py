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

# Test-only copy of the MVLL/SOXL timing slots that I0-b removed from
# alert_policy.json (2026-10-06). The engine still enforces them when present.
RETIRED_TIMING_POSITIONS = {
    "SOXL": {
        "anchor_shares": 99,
        "confirmation_symbol": "SOXX",
        "default_direction": "hold",
        "r_multiple_targets_enabled": False,
        "watch_only_triggers": ["weakness_10ema", "gap_risk", "halt_risk"],
        "slots": [
            {"id": "SOXL-R25", "quantity": 24, "allowed_triggers": ["technical_stop", "weakness_20ema", "weakness_failed_reclaim", "take_profit_rejection"]},
            {"id": "SOXL-R50", "quantity": 24, "allowed_triggers": ["technical_stop", "weakness_20ema", "weakness_failed_reclaim", "take_profit_rejection"]},
            {"id": "SOXL-R75", "quantity": 24, "allowed_triggers": ["technical_stop", "weakness_20ema", "weakness_failed_reclaim"]},
            {"id": "SOXL-FINAL-RESIDUAL", "quantity": 27, "allowed_triggers": []},
        ],
        "final_residual_policy": "hard-risk review or later explicit user instruction only",
    },
    "MVLL": {
        "anchor_shares": 396,
        "confirmation_symbol": "MRVL",
        "default_direction": "reduce",
        "r_multiple_targets_enabled": False,
        "watch_only_triggers": ["gap_risk", "halt_risk"],
        "slots": [
            {"id": "MVLL-R25", "quantity": 99, "allowed_triggers": ["technical_stop", "weakness_20ema", "weakness_failed_reclaim", "weakness_10ema", "strength_20ema_reclaim", "strength_10ema_reclaim", "strength_extension"]},
            {"id": "MVLL-R50", "quantity": 99, "allowed_triggers": ["technical_stop", "weakness_20ema", "weakness_failed_reclaim", "strength_20ema_reclaim", "strength_extension"]},
            {"id": "MVLL-R75", "quantity": 99, "allowed_triggers": ["technical_stop", "weakness_20ema", "weakness_failed_reclaim", "strength_extension"]},
            {"id": "MVLL-FINAL-RESIDUAL", "quantity": 99, "allowed_triggers": ["technical_stop"]},
        ],
    },
}


def with_timing_positions(policy: dict, *symbols: str) -> dict:
    synthetic = copy.deepcopy(policy)
    synthetic["holding_timing_rules"]["positions"] = {
        symbol: copy.deepcopy(RETIRED_TIMING_POSITIONS[symbol]) for symbol in symbols
    }
    return synthetic


class EvaluateTimingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads((SYSTEM_ROOT / "alert_policy.json").read_text(encoding="utf-8"))
        self.state = json.loads((SYSTEM_ROOT / "portfolio_state.json").read_text(encoding="utf-8"))
        # The generic technical fixture trades near USD 102. Normalize the NBIS
        # test-only cost so unrelated integration cases do not accidentally
        # trigger the live 10% NBIS hard-risk boundary.
        if self.state.get("holdings", {}).get("NBIS", 0) > 0:
            self.state["average_cost_usd"]["NBIS"] = 100.0
            self.state["position_cost_basis_usd"]["NBIS"] = (
                100.0 * self.state["holdings"]["NBIS"]
            )
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
        # Since I0-b the active policy has no timing positions: no timing candidate.
        result = EVALUATOR.evaluate(self.state, self.policy, self.snapshot, {})
        self.assertNotEqual(result["state"], "STATE_MISMATCH", result)
        self.assertEqual(
            [
                item
                for item in result["candidates"]
                if item["event_type"] in {"holding_timing_review", "holding_timing_watch"}
            ],
            [],
        )
        self.assertTrue(all(item["quantity"] is None for item in result["candidates"]))
        self.assertTrue(all(item["quantity"] is None for item in result["watchlist"]))
        cash_verified = (
            self.state["last_confirmed_broker_snapshot"].get("cash_verified") is True
        )
        available_cash = self.state.get("available_cash_usd")
        if not cash_verified:
            expected_watch_status = "watch_only_cash_unverified"
        elif isinstance(available_cash, (int, float)) and available_cash <= 0:
            expected_watch_status = "watch_only_zero_cash"
        else:
            expected_watch_status = "watch_only_entry_rules_not_approved"
        self.assertTrue(
            all(item["status"] == expected_watch_status for item in result["watchlist"])
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
        policy = with_timing_positions(self.policy, "SOXL")
        result = EVALUATOR.evaluate(broken, policy, self.snapshot, {})
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
        broken["average_cost_usd"]["NBIL"] = 65.2
        broken["position_cost_basis_usd"]["NBIL"] = 130.4
        result = EVALUATOR.evaluate(broken, self.policy, self.snapshot, {})
        self.assertEqual(result["state"], "STATE_MISMATCH")
        self.assertEqual(result["grade"], "F")
        self.assertTrue(any("1-share cap" in item for item in result["warnings"]))

    def test_nbil_de_minimis_cost_basis_cap_fails_closed(self) -> None:
        broken = copy.deepcopy(self.state)
        broken["holdings"]["NBIL"] = 1
        broken["average_cost_usd"]["NBIL"] = 65.2
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

    def test_nbis_exact_ten_percent_boundary_generates_hard_risk_review(self) -> None:
        state = copy.deepcopy(self.state)
        state["average_cost_usd"]["NBIS"] = 100.0
        state["position_cost_basis_usd"]["NBIS"] = 1500.0
        snapshot = copy.deepcopy(self.snapshot)
        row = snapshot["symbols"]["NBIS"]
        row.update({"open": 91.0, "high": 92.0, "low": 89.0, "close": 90.0})
        row["quote_crosscheck"].update({"close": 90.0, "difference_fraction": 0.0})
        result = EVALUATOR.evaluate(state, self.policy, snapshot, {})
        hard = next(
            item
            for item in result["candidates"]
            if item["event_type"] == "holding_max_loss_breach"
            and item["symbol"] == "NBIS"
        )
        self.assertEqual(result["grade"], "D", result)
        self.assertEqual(hard["hard_boundary_usd"], 90.0)
        self.assertTrue(hard["breached"])
        self.assertIsNone(hard["quantity"])
        self.assertFalse(hard["actionable"])

    def test_missing_held_ohlcv_provenance_fails_closed(self) -> None:
        broken = copy.deepcopy(self.snapshot)
        broken["symbols"]["SOXL"]["source"] = None
        result = EVALUATOR.evaluate(self.state, self.policy, broken, {})
        self.assertEqual(result["state"], "DATA_INCOMPLETE")
        self.assertEqual(result["grade"], "F")
        self.assertTrue(any("market-data source" in item for item in result["warnings"]))

    def test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch(self) -> None:
        policy = with_timing_positions(self.policy, "MVLL", "SOXL")
        state = copy.deepcopy(self.state)
        state["holdings"]["MVLL"] = 396  # synthetic holding equal to the retained state anchor
        result = EVALUATOR.evaluate(state, policy, self.snapshot, {})
        self.assertNotEqual(result["state"], "STATE_MISMATCH", result)
        active = [item for item in result["candidates"] if item["grade"] == "B"]
        self.assertEqual(
            [(item["symbol"], item["tranche_id"], item["quantity"], item["actionable"]) for item in active],
            [("MVLL", "MVLL-R25", 99, False)],
        )
        self.assertTrue(active[0]["evidence_verification"]["all_required_evidence_verified"])
        state["holdings"]["MVLL"] = 395
        result = EVALUATOR.evaluate(state, policy, self.snapshot, {})
        self.assertEqual((result["state"], result["grade"]), ("STATE_MISMATCH", "F"))
        self.assertIn(
            "MVLL: holdings 395 do not equal anchor less confirmed tranches 396",
            result["warnings"],
        )

    def test_i0b_t2_holding_risk_checks_still_run_without_timing_positions(self) -> None:
        self.assertEqual(self.policy["holding_timing_rules"]["positions"], {})
        snapshot = copy.deepcopy(self.snapshot)
        row = snapshot["symbols"]["NBIS"]
        row.update({"open": 91.0, "high": 92.0, "low": 89.0, "close": 90.0})
        row["quote_crosscheck"].update({"close": 90.0, "difference_fraction": 0.0})
        result = EVALUATOR.evaluate(self.state, self.policy, snapshot, {})
        self.assertEqual(result["grade"], "D", result)
        hard = {
            item["symbol"]: item
            for item in result["candidates"]
            if item["event_type"] == "holding_max_loss_breach"
        }
        self.assertEqual(set(hard), set(self.policy["holding_risk_rules"]["positions"]))
        self.assertEqual((hard["NBIS"]["hard_boundary_usd"], hard["NBIS"]["breached"]), (90.0, True))
        unregistered = copy.deepcopy(self.state)
        unregistered["holdings"]["ZZZT"] = 5
        unregistered["average_cost_usd"]["ZZZT"] = 10.0
        unregistered["position_cost_basis_usd"]["ZZZT"] = 50.0
        result = EVALUATOR.evaluate(unregistered, self.policy, self.snapshot, {})
        self.assertEqual((result["state"], result["grade"]), ("STATE_MISMATCH", "F"))
        self.assertTrue(
            any("neither a holding-risk rule" in item and "ZZZT" in item for item in result["warnings"])
        )
        zero = copy.deepcopy(self.state)
        zero["holdings"]["NBIS"] = 0
        result = EVALUATOR.evaluate(zero, self.policy, self.snapshot, {})
        self.assertEqual((result["state"], result["grade"]), ("STATE_MISMATCH", "F"))
        self.assertIn(
            "holding-risk policy symbols are not positive verified holdings: NBIS",
            result["warnings"],
        )

    def test_i0b_t3_real_policy_and_state_pass_integrity_without_state_write(self) -> None:
        state_path = SYSTEM_ROOT / "portfolio_state.json"
        before = state_path.read_bytes()
        state = json.loads(before.decode("utf-8"))
        policy = json.loads((SYSTEM_ROOT / "alert_policy.json").read_text(encoding="utf-8"))
        session_date = state["last_confirmed_broker_snapshot"]["as_of"]
        self.assertEqual(
            EVALUATOR.leveraged_state_integrity_errors(state, policy, session_date), []
        )
        self.assertEqual(state_path.read_bytes(), before)

    def test_i0b_t4_timing_plan_policy_version_mismatch_still_fails(self) -> None:
        state = copy.deepcopy(self.state)
        state["timing_plan"]["policy_version"] = "SYNTHETIC-STALE-TIMING-PLAN"
        result = EVALUATOR.evaluate(state, self.policy, self.snapshot, {})
        self.assertEqual((result["state"], result["grade"]), ("STATE_MISMATCH", "F"))
        self.assertIn(
            "timing-plan policy version does not match active timing policy",
            result["warnings"],
        )


if __name__ == "__main__":
    unittest.main()
