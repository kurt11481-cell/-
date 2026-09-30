from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import build_holding_fact_pack as builder  # noqa: E402
from validate_holding_card import forbidden_keys  # noqa: E402

RUN_ID = "manual-20260930T000000000000Z-abcdef012345"
DECISION_AS_OF = "2026-09-30T11:21:14.980095+00:00"
EXPECTED_SESSION = "2026-09-29"


def daily_record(session: str, price: float, **overrides: object) -> dict:
    record = {
        "reported_session": session,
        "market_session_type": "REGULAR_COMPLETED",
        "price_basis": "RAW_REGULAR_SESSION_CLOSE",
        "price": price,
        "bar_finalized": True,
        "hard_risk_authority": True,
    }
    record.update(overrides)
    return record


def mark_evidence(ticker: str, price: float) -> dict:
    return {
        "ticker": ticker,
        "status": "AVAILABLE",
        "record": {
            "price": price,
            "market_session_type": "PRE_MARKET",
            "price_basis": "BROKER_MARK",
            "provider_timestamp": DECISION_AS_OF,
            "indicative_only": True,
        },
    }


def make_analysis() -> dict:
    return {
        "manual_run_id": RUN_ID,
        "decision_as_of": DECISION_AS_OF,
        "observed_at": DECISION_AS_OF,
        "trading_date": "2026-09-30",
        "market_phase": "PRE_MARKET",
        "expected_completed_us_session": EXPECTED_SESSION,
        "evidence_grade": "UNVERIFIED",
        "preflight_status": "FAIL",
        "hard_fail_reasons": ["ACQUISITION_TIMESTAMP_INVALID"],
        "broker_diff_status": "MATCH",
        "identity_authority_status": "VERIFIED",
        "orderable_cash_status": "VERIFIED",
        "verified_orderable_cash_usd": 8.94,
        "event_evidence_status": "NOT_EVALUATED_M1",
        "technical_evidence_status": "REPORT_ONLY_M1",
        "broker_observed_state": {
            "status": "AVAILABLE",
            "holdings": [
                {"ticker": "AAA", "held_quantity": 100.0, "average_cost": 10.0},
                {"ticker": "BBB", "held_quantity": 10.0, "average_cost": 100.0},
            ],
            "cash": {"cash_status": "VERIFIED_POSITIVE", "foreign_currency_deposit": 50.0},
            "operation_statuses": {
                "account_open_items": "KIWOOM_API_RESPONSE_ERROR",
                "account_realized_pnl_read": "KIWOOM_API_RESPONSE_ERROR",
            },
        },
        "system_portfolio_state": {
            "state_revision": 16,
            "average_cost_usd": {"AAA": 10.0, "BBB": 100.0},
            "holdings": {"AAA": 100, "BBB": 10},
        },
        "current_price_evidence": [mark_evidence("AAA", 9.0), mark_evidence("BBB", 120.0)],
        "historical_daily_evidence": [
            {"ticker": "AAA", "status": "AVAILABLE",
             "records": [daily_record("2026-09-28", 8.5), daily_record(EXPECTED_SESSION, 8.0)]},
            {"ticker": "BBB", "status": "AVAILABLE",
             "records": [daily_record("2026-09-28", 105.0), daily_record(EXPECTED_SESSION, 110.0)]},
        ],
        "last_verified_finalized_bars": [
            {"ticker": "AAA", "identity_authority_status": "VERIFIED", "status": "NOT_VERIFIED"},
            {"ticker": "BBB", "identity_authority_status": "VERIFIED", "status": "NOT_VERIFIED"},
        ],
    }


def make_rule(rule_id: str, ticker: str, max_loss: float, direction: str, plan_status: str) -> dict:
    return {
        "rule_id": rule_id,
        "ticker": ticker,
        "maximum_loss_fraction_from_average_cost": max_loss,
        "calculation_basis": "basis",
        "approved_by": "user",
        "approval_status": "VERIFIED_USER_APPROVAL",
        "user_approval_reference": "reference",
        "average_cost_source_requirement": "requirement",
        "default_direction": direction,
        "reduction_plan_status": plan_status,
        "action_on_breach": None,
        "action_approval_status": "UNVERIFIED",
    }


def make_policy() -> dict:
    return {
        "holding_risk_rules": {
            "rule_version": "test-rule-version",
            "positions": {
                "AAA": make_rule("HR-AAA-MAXLOSS-60", "AAA", 0.6, "reduce", "approved"),
                "BBB": make_rule("HR-BBB-MAXLOSS-20", "BBB", 0.2, "hold", "not_applicable"),
            },
        },
        "holding_timing_rules": {
            "status": "approved_review_only",
            "positions": {"AAA": {}},
            "risk_overlay_rules": {
                "dynamic_gross_leverage_cap": {
                    "gross_effective_leverage_formula":
                        "3*abs(AAA market-value weight) + 2*abs(BBB market-value weight)",
                },
            },
        },
    }


def make_baselines() -> dict:
    return {
        "AAA": {
            "baseline_id": "aaa-v1",
            "baseline_version": 1,
            "analysis_cutoff": "2026-08-14T00:00:00+00:00",
            "thesis_status": "VALID",
            "valuation_status": "UNCLASSIFIED",
            "validation_status": "VALIDATED_SHADOW",
            "primary_reason": "reason",
            "strongest_counter_case": "counter",
            "invalidation_conditions": ["condition"],
        },
    }


def make_state() -> dict:
    return {"state_revision": 16}


def build(analysis: dict | None = None, policy: dict | None = None, state: dict | None = None,
          alert_result: dict | None = None) -> dict:
    return builder.build_fact_pack(
        analysis if analysis is not None else make_analysis(),
        state if state is not None else make_state(),
        make_baselines(),
        policy if policy is not None else make_policy(),
        alert_result,
    )


def release_analysis() -> dict:
    analysis = make_analysis()
    analysis.update(evidence_grade="GRADE_B", preflight_status="PASS")
    return analysis


class FactPackBasicsTests(unittest.TestCase):
    def test_same_inputs_give_identical_pack_and_hash(self) -> None:
        first, second = build(), build()
        self.assertEqual(first, second)
        self.assertEqual(builder.fact_pack_hash(first), builder.fact_pack_hash(second))
        self.assertEqual(
            json.dumps(first, sort_keys=True), json.dumps(copy.deepcopy(second), sort_keys=True)
        )

    def test_pack_never_reads_the_clock(self) -> None:
        text = json.dumps(build())
        self.assertNotIn("generated_at", text)
        self.assertEqual(build()["source"]["decision_as_of"], DECISION_AS_OF)

    def test_pack_has_no_order_or_quantity_authority_fields(self) -> None:
        pack = build()
        self.assertEqual(forbidden_keys(pack), [])
        self.assertIs(pack["order_authority"], False)
        self.assertEqual(pack["quantity_authority"], "none")
        self.assertIs(pack["display_only"], True)
        self.assertIs(pack["tickers"]["AAA"]["holding_observed"]["display_only"], True)

    def test_display_numbers_are_derived_from_broker_observation(self) -> None:
        display = build()["tickers"]["AAA"]["display"]
        self.assertEqual(display["held_quantity"], 100)
        self.assertEqual(display["average_cost_usd"], 10)
        self.assertEqual(display["mark_price_usd"], 9)
        self.assertEqual(display["market_value_usd"], 900.0)
        self.assertEqual(display["unrealized_pnl_usd"], -100.0)
        self.assertEqual(display["unrealized_pnl_pct"], -10.0)
        self.assertEqual(display["weight_pct"], 41.9)
        self.assertEqual(build()["tickers"]["BBB"]["display"]["weight_pct"], 55.8)
        self.assertEqual(build()["portfolio"]["total_value_usd"], 2150.0)
        self.assertEqual(build()["portfolio"]["cash_weight_pct"], 2.33)

    def test_orderable_cash_is_labeled_and_sale_proceeds_are_not_cash(self) -> None:
        cash = build()["portfolio"]["orderable_cash"]
        self.assertEqual((cash["usd"], cash["label"]), (8.94, "VERIFIED_ORDERABLE_CASH"))
        self.assertIs(cash["expected_sale_proceeds_counted_as_orderable_cash"], False)
        analysis = make_analysis()
        analysis["orderable_cash_status"] = "UNVERIFIED"
        cash = build(analysis)["portfolio"]["orderable_cash"]
        self.assertEqual((cash["usd"], cash["label"]), (None, "NOT_VERIFIED"))

    def test_open_order_and_realized_pnl_status_stay_visible(self) -> None:
        portfolio = build()["portfolio"]
        self.assertEqual(portfolio["open_orders_status"], "KIWOOM_API_RESPONSE_ERROR")
        self.assertEqual(portfolio["realized_pnl_status"], "KIWOOM_API_RESPONSE_ERROR")

    def test_leverage_comes_from_policy_formula_and_missing_is_visible(self) -> None:
        pack = build()
        self.assertEqual(pack["tickers"]["AAA"]["display"]["leverage_factor"], 3)
        self.assertEqual(pack["tickers"]["BBB"]["display"]["leverage_factor"], 2)
        policy = make_policy()
        policy["holding_timing_rules"]["risk_overlay_rules"]["dynamic_gross_leverage_cap"][
            "gross_effective_leverage_formula"] = "3*abs(AAA market-value weight)"
        row = build(policy=policy)["tickers"]["BBB"]
        self.assertIsNone(row["display"]["leverage_factor"])
        self.assertIn("LEVERAGE_FACTOR_NOT_IN_POLICY", row["missing"])

    def test_baseline_is_copied_with_age_and_missing_is_visible(self) -> None:
        pack = build()
        baseline = pack["tickers"]["AAA"]["baseline"]
        self.assertEqual((baseline["thesis_status"], baseline["age_days"]), ("VALID", 47))
        self.assertIsNone(pack["tickers"]["BBB"]["baseline"])
        self.assertIn("BASELINE_MISSING", pack["tickers"]["BBB"]["missing"])


class EmptyHoldingsTests(unittest.TestCase):
    def test_available_broker_with_empty_holdings_fails(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["holdings"] = []
        with self.assertRaises(builder.FactPackError) as raised:
            build(analysis)
        self.assertEqual(str(raised.exception), "EMPTY_HOLDINGS_WITH_AVAILABLE_BROKER")

    def test_available_broker_without_holdings_key_fails(self) -> None:
        analysis = make_analysis()
        del analysis["broker_observed_state"]["holdings"]
        with self.assertRaises(builder.FactPackError):
            build(analysis)

    def test_invalid_or_duplicate_holding_records_fail(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["holdings"][1]["ticker"] = "AAA"
        with self.assertRaises(builder.FactPackError) as raised:
            build(analysis)
        self.assertIn("DUPLICATE_BROKER_TICKER", str(raised.exception))
        analysis = make_analysis()
        analysis["broker_observed_state"]["holdings"][0]["held_quantity"] = 0
        with self.assertRaises(builder.FactPackError) as raised:
            build(analysis)
        self.assertIn("INVALID_HOLDING_RECORD", str(raised.exception))

    def test_unavailable_broker_uses_state_tickers_and_allows_withhold(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["status"] = "UNAVAILABLE"
        analysis["broker_observed_state"]["holdings"] = []
        pack = build(analysis)
        self.assertEqual(sorted(pack["tickers"]), ["AAA", "BBB"])
        self.assertIs(pack["tickers"]["AAA"]["withhold_allowed"]["BROKER_UNAVAILABLE"], True)
        self.assertIsNone(pack["tickers"]["AAA"]["display"]["held_quantity"])
        self.assertIn("BROKER_NOT_AVAILABLE", pack["status"]["confidence_cap"]["reasons"])
        self.assertIn("WEIGHT_NOT_COMPUTABLE", pack["tickers"]["AAA"]["missing"])

    def test_unavailable_broker_without_any_known_holding_fails(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"] = {"status": "UNAVAILABLE", "holdings": []}
        analysis["system_portfolio_state"]["holdings"] = {}
        with self.assertRaises(builder.FactPackError) as raised:
            build(analysis)
        self.assertEqual(str(raised.exception), "NO_HOLDINGS_KNOWN")

    def test_incomplete_broker_does_not_allow_withhold(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["status"] = "INCOMPLETE"
        analysis["broker_observed_state"]["holdings"] = []
        pack = build(analysis)
        self.assertIs(pack["tickers"]["AAA"]["withhold_allowed"]["BROKER_UNAVAILABLE"], False)

    def test_identity_unverified_allows_withhold_per_ticker(self) -> None:
        analysis = make_analysis()
        analysis["last_verified_finalized_bars"][0]["identity_authority_status"] = "NOT_VERIFIED"
        pack = build(analysis)
        self.assertIs(pack["tickers"]["AAA"]["withhold_allowed"]["IDENTITY_UNVERIFIED"], True)
        self.assertIs(pack["tickers"]["BBB"]["withhold_allowed"]["IDENTITY_UNVERIFIED"], False)


class HardRiskTests(unittest.TestCase):
    def test_remaining_distance_and_breach_use_confirmed_close(self) -> None:
        hard = build()["tickers"]["AAA"]["rule_results"]["hard_risk"]
        self.assertEqual(hard["status"], "EVALUATED")
        self.assertEqual((hard["boundary_usd"], hard["close_usd"]), (4.0, 8.0))
        self.assertIs(hard["breached"], False)
        self.assertEqual(hard["remaining_pct"], -50.0)
        self.assertEqual(hard["close_session"], EXPECTED_SESSION)
        self.assertEqual(hard["holding_risk_state"], "NO_HARD_RISK")
        self.assertEqual(hard["rule_id"], "HR-AAA-MAXLOSS-60")

    def test_breach_is_inclusive_like_the_alert_engine(self) -> None:
        analysis = make_analysis()
        analysis["historical_daily_evidence"][0]["records"][-1]["price"] = 4.0
        hard = build(analysis)["tickers"]["AAA"]["rule_results"]["hard_risk"]
        self.assertIs(hard["breached"], True)
        self.assertEqual(hard["remaining_pct"], 0.0)
        self.assertEqual(hard["holding_risk_state"], "POLICY_AUTHORITY_UNVERIFIED")

    def test_premarket_mark_is_reference_only(self) -> None:
        hard = build()["tickers"]["AAA"]["rule_results"]["hard_risk"]
        self.assertEqual(hard["premarket_reference_remaining_pct"], -55.6)
        self.assertEqual(hard["premarket_reference_note"], "REFERENCE_ONLY_NOT_HARD_RISK_AUTHORITY")
        self.assertIs(build()["tickers"]["AAA"]["mark"]["reference_only"], True)

    def test_loss_limit_is_not_evaluated_without_a_confirmed_close(self) -> None:
        analysis = make_analysis()
        analysis["historical_daily_evidence"][0]["records"] = [daily_record("2026-09-28", 8.5)]
        row = build(analysis)["tickers"]["AAA"]
        self.assertEqual(row["rule_results"]["hard_risk"]["status"], "NOT_EVALUATED")
        self.assertEqual(row["rule_results"]["hard_risk"]["reason"], "CONFIRMED_CLOSE_MISSING")
        self.assertIsNone(row["confirmed_close"])
        self.assertIn("LOSS_LIMIT_NOT_EVALUATED", row["missing"])
        self.assertIsNotNone(row["mark"])

    def test_close_must_be_finalized_regular_session_hard_risk_authority(self) -> None:
        for field, value in (
            ("bar_finalized", False), ("hard_risk_authority", False),
            ("market_session_type", "PRE_MARKET"), ("price_basis", "BROKER_MARK"),
        ):
            with self.subTest(field=field):
                analysis = make_analysis()
                analysis["historical_daily_evidence"][0]["records"][-1][field] = value
                row = build(analysis)["tickers"]["AAA"]
                self.assertIsNone(row["confirmed_close"])
                self.assertEqual(row["rule_results"]["hard_risk"]["status"], "NOT_EVALUATED")

    def test_missing_policy_rule_or_state_average_is_visible(self) -> None:
        policy = make_policy()
        del policy["holding_risk_rules"]["positions"]["AAA"]
        hard = build(policy=policy)["tickers"]["AAA"]["rule_results"]["hard_risk"]
        self.assertEqual((hard["status"], hard["reason"]), ("NOT_EVALUATED", "NO_POLICY_RULE"))
        analysis = make_analysis()
        del analysis["system_portfolio_state"]["average_cost_usd"]["AAA"]
        hard = build(analysis)["tickers"]["AAA"]["rule_results"]["hard_risk"]
        self.assertEqual(hard["reason"], "STATE_AVERAGE_COST_MISSING")

    def test_average_cost_broker_match_flag(self) -> None:
        self.assertIs(build()["tickers"]["AAA"]["rule_results"]["hard_risk"]["average_cost_matches_broker"], True)
        analysis = make_analysis()
        analysis["broker_observed_state"]["holdings"][0]["average_cost"] = 11.0
        self.assertIs(build(analysis)["tickers"]["AAA"]["rule_results"]["hard_risk"]["average_cost_matches_broker"], False)


class TimingAndDirectionTests(unittest.TestCase):
    def test_timing_status_variants(self) -> None:
        pack = build()
        self.assertEqual(pack["tickers"]["BBB"]["rule_results"]["timing"]["status"], "NOT_APPLICABLE")
        aaa = pack["tickers"]["AAA"]["rule_results"]["timing"]
        self.assertEqual((aaa["status"], aaa["reason"]), ("NOT_EVALUATED", "ALERT_RESULT_NOT_PROVIDED"))
        stale = {"us_session_date": "2026-09-01", "candidates": []}
        self.assertEqual(build(alert_result=stale)["tickers"]["AAA"]["rule_results"]["timing"]["reason"], "ALERT_RESULT_STALE")
        empty = {"us_session_date": EXPECTED_SESSION, "candidates": []}
        self.assertEqual(
            build(alert_result=empty)["tickers"]["AAA"]["rule_results"]["timing"]["reason"],
            "NO_TIMING_CANDIDATE_IN_ALERT_RESULT",
        )

    def test_timing_review_candidate_is_evaluated_and_can_set_direction(self) -> None:
        policy = make_policy()
        policy["holding_risk_rules"]["positions"]["AAA"]["default_direction"] = "hold"
        alert = {"us_session_date": EXPECTED_SESSION, "candidates": [
            {"symbol": "AAA", "event_type": "holding_timing_review", "side": "reduce", "grade": "B"},
        ]}
        rules = build(policy=policy, alert_result=alert)["tickers"]["AAA"]["rule_results"]
        self.assertEqual(rules["timing"]["status"], "EVALUATED")
        self.assertEqual(rules["rule_direction"], "REDUCE")
        self.assertEqual(rules["rule_direction_basis"], ["TIMING_REDUCE_REVIEW"])

    def test_direction_from_policy_default_and_breach(self) -> None:
        pack = build()
        self.assertEqual(pack["tickers"]["AAA"]["rule_results"]["rule_direction"], "REDUCE")
        self.assertEqual(pack["tickers"]["AAA"]["rule_results"]["rule_direction_basis"], ["POLICY_DEFAULT_REDUCE"])
        self.assertEqual(pack["tickers"]["BBB"]["rule_results"]["rule_direction"], "HOLD")
        analysis = make_analysis()
        analysis["historical_daily_evidence"][1]["records"][-1]["price"] = 80.0
        rules = build(analysis)["tickers"]["BBB"]["rule_results"]
        self.assertEqual(rules["rule_direction"], "REDUCE")
        self.assertEqual(rules["rule_direction_basis"], ["HARD_RISK_BREACH"])

    def test_no_policy_rule_gives_no_direction(self) -> None:
        policy = make_policy()
        del policy["holding_risk_rules"]["positions"]["BBB"]
        self.assertEqual(build(policy=policy)["tickers"]["BBB"]["rule_results"]["rule_direction"], "NONE")


class ConfidenceCapTests(unittest.TestCase):
    def cap(self, analysis: dict, state: dict | None = None) -> dict:
        return build(analysis, state=state)["status"]["confidence_cap"]

    def test_unverified_grade_keeps_low_cap(self) -> None:
        cap = self.cap(make_analysis())
        self.assertEqual(cap["max_conviction"], "LOW")
        self.assertIn("EVIDENCE_GRADE_NOT_ALLOWLISTED", cap["reasons"])
        self.assertIn("PREFLIGHT_NOT_PASS", cap["reasons"])

    def test_only_allowlisted_grade_with_all_conditions_releases_the_cap(self) -> None:
        for grade in ("GRADE_A", "GRADE_B"):
            with self.subTest(grade=grade):
                analysis = release_analysis()
                analysis["evidence_grade"] = grade
                self.assertEqual(self.cap(analysis), {
                    "max_conviction": "HIGH", "reasons": [], "release_grades": ["GRADE_A", "GRADE_B"],
                })

    def test_unknown_or_missing_grade_keeps_the_cap(self) -> None:
        analysis = release_analysis()
        analysis["evidence_grade"] = "GRADE_Z"
        self.assertEqual(self.cap(analysis)["max_conviction"], "LOW")
        del analysis["evidence_grade"]
        self.assertEqual(self.cap(analysis)["max_conviction"], "LOW")

    def test_each_extra_condition_keeps_the_cap(self) -> None:
        cases = {
            "PREFLIGHT_NOT_PASS": {"preflight_status": "FAIL"},
            "STATE_UNRECONCILED_BROKER_DIFF_NOT_MATCH": {"broker_diff_status": "DIFFERENT"},
        }
        for reason, change in cases.items():
            with self.subTest(reason=reason):
                analysis = release_analysis()
                analysis.update(change)
                cap = self.cap(analysis)
                self.assertEqual(cap["max_conviction"], "LOW")
                self.assertIn(reason, cap["reasons"])

    def test_state_changed_after_analysis_keeps_the_cap(self) -> None:
        cap = self.cap(release_analysis(), state={"state_revision": 17})
        self.assertEqual(cap["max_conviction"], "LOW")
        self.assertIn("STATE_CHANGED_SINCE_ANALYSIS", cap["reasons"])
        self.assertIs(
            build(release_analysis(), state={"state_revision": 17})["status"]["state_file_revision_matches_analysis"], False
        )

    def test_missing_state_file_is_not_a_cap_reason_but_stays_visible(self) -> None:
        pack = builder.build_fact_pack(release_analysis(), None, make_baselines(), make_policy(), None)
        self.assertEqual(pack["status"]["confidence_cap"]["max_conviction"], "HIGH")
        self.assertIsNone(pack["status"]["state_file_revision_matches_analysis"])


class WriteAndCliTests(unittest.TestCase):
    def test_write_is_create_only_and_limited_to_holding_cards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target_dir = root / "workspace/outputs/holding-cards/2026-09-30"
            path = builder.write_fact_pack(build(), target_dir, root=root)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["artifact_type"], "HOLDING_FACT_PACK")
            with self.assertRaises(builder.FactPackError) as raised:
                builder.write_fact_pack(build(), target_dir, root=root)
            self.assertEqual(str(raised.exception), "FACT_PACK_ALREADY_EXISTS")
            with self.assertRaises(builder.FactPackError) as raised:
                builder.write_fact_pack(build(), root / "elsewhere", root=root)
            self.assertEqual(str(raised.exception), "OUTPUT_OUTSIDE_HOLDING_CARDS")
            self.assertFalse((root / "elsewhere").exists())

    def test_cli_rejects_output_outside_holding_cards_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "analysis.json").write_text(json.dumps(make_analysis()), encoding="utf-8")
            (root / "policy.json").write_text(json.dumps(make_policy()), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = builder.main([
                    "--analysis", str(root / "analysis.json"), "--policy", str(root / "policy.json"),
                    "--state", str(root / "no-state.json"), "--baseline-index", str(root / "no-index.json"),
                    "--output-dir", str(root / "out"),
                ])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(buffer.getvalue())["error"], "OUTPUT_OUTSIDE_HOLDING_CARDS")
            self.assertFalse((root / "out").exists())

    def test_cli_reports_empty_holdings_failure(self) -> None:
        analysis = make_analysis()
        analysis["broker_observed_state"]["holdings"] = []
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
            (root / "policy.json").write_text(json.dumps(make_policy()), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = builder.main([
                    "--analysis", str(root / "analysis.json"), "--policy", str(root / "policy.json"),
                    "--state", str(root / "no-state.json"), "--baseline-index", str(root / "no-index.json"),
                    "--output-dir", str(root / "out"),
                ])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(buffer.getvalue())["error"], "EMPTY_HOLDINGS_WITH_AVAILABLE_BROKER")

    def test_load_baselines_stays_inside_the_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "b").mkdir()
            (root / "b/aaa.json").write_text(json.dumps(make_baselines()["AAA"]), encoding="utf-8")
            outside = root.parent / "outside-baseline.json"
            outside.write_text("{}", encoding="utf-8")
            try:
                index = {"active": {
                    "AAA": {"baseline_path": "b/aaa.json"},
                    "BBB": {"baseline_path": "../" + outside.name},
                }}
                (root / "index.json").write_text(json.dumps(index), encoding="utf-8")
                loaded = builder.load_baselines(root / "index.json", root=root)
            finally:
                outside.unlink()
            self.assertEqual(sorted(loaded), ["AAA"])


if __name__ == "__main__":
    unittest.main()
