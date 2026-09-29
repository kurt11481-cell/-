#!/usr/bin/env python3
"""Offline safety and negative tests for Portfolio Decision Dashboard v1.0."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from portfolio_decision_dashboard import (  # noqa: E402
    ContractError,
    CURRENT_SESSION_CONTEXT_SCHEMA,
    DEFAULT_RISK_POLICY,
    MANUAL_EVIDENCE_SCHEMA,
    REQUEST_ACCOUNTING_SCHEMA,
    compile_dashboard,
    discover_historical_replay,
    implementation_provenance_paths,
    manual_evidence_schema_bytes,
    render_html,
    render_markdown,
    validate_plan,
    write_run,
)
from validation_common import load_json, validate_instance  # noqa: E402
import portfolio_decision_dashboard as dashboard  # noqa: E402


MANUAL_TEST_PATH = ROOT / "manage-us-stock-strategy/tests/test_manual_portfolio_analysis.py"
_manual_spec = importlib.util.spec_from_file_location("dashboard_canonical_manual_fixture", MANUAL_TEST_PATH)
assert _manual_spec and _manual_spec.loader
_manual_module = importlib.util.module_from_spec(_manual_spec)
_manual_spec.loader.exec_module(_manual_module)


def evidence(
    *, market_phase: str = "REGULAR_COMPLETED", cash: float = 10_000.0,
    run_id: str = "manual-synthetic-grade-b", decision_as_of: str = "2026-08-21T22:00:00+00:00",
    holdings: dict[str, float] | None = None,
) -> dict:
    broker_holdings = holdings or {"MVLL": 100, "NBIS": 20, "SOXL": 20, "PGR": 0, "JPM": 0}
    costs = {"MVLL": 30.0, "NBIS": 90.0, "SOXL": 50.0, "PGR": 0.0, "JPM": 0.0}
    system = _manual_module.system_portfolio(
        {"MVLL": 99, "NBIS": 20, "SOXL": 20, "PGR": 0, "JPM": 0}, costs, cash,
    )
    case = _manual_module.ManualPortfolioAnalysisTest(methodName="runTest")
    case.setUpClass()
    case.setUp()
    try:
        value = case.build_report(
            portfolio=system, broker_holdings=broker_holdings, broker_costs=costs,
            orderable_cash=cash, manual_run_id=run_id, observed_at=decision_as_of,
            decision_as_of=decision_as_of, account_retrieved_at=decision_as_of,
            market_retrieved_at_by_operation={"oauth_health": decision_as_of, "market_quote": decision_as_of,
                                               "daily_chart": decision_as_of},
        )
    finally:
        case.tearDown()
    prices = {"MVLL": 20.0, "NBIS": 100.0, "SOXL": 40.0, "PGR": 200.0, "JPM": 100.0}
    for item in value["last_verified_finalized_bars"]:
        item["bar"]["price"] = prices[item["ticker"]]
    value["market_phase"] = market_phase
    value["current_session_finalization_status"] = "VERIFIED" if market_phase == "REGULAR_COMPLETED" else "NOT_VERIFIED"
    assert validate_instance(value, MANUAL_EVIDENCE_SCHEMA) == []
    return value


def plan(*, status: str = "CURRENT_APPROVED", include_priority: bool = True) -> dict:
    value = {
        "plan_id": "synthetic-plan-v1",
        "as_of": "2026-08-21T22:00:00+00:00",
        "plan_status": status,
        "evidence_binding": {
            "expected_run_id": "manual-synthetic-grade-b",
            "expected_decision_as_of": "2026-08-21T22:00:00+00:00",
        },
        "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET",
        "cash_target_pct": 61.5,
        "positions": [
            {"ticker": "MVLL", "action": "TRIM", "target_weight_pct": 5.0, "rationale": "leveraged concentration", "investment_horizon": "transition", "target_status": "APPROVED", "material_risk": "daily reset", "decision_change_triggers": ["risk cap changes"]},
            {"ticker": "NBIS", "action": "HOLD", "target_weight_pct": 13.5, "rationale": "hold reference", "investment_horizon": "long", "target_status": "APPROVED"},
            {"ticker": "SOXL", "action": "EXIT", "target_weight_pct": 0.0, "rationale": "reduce 3x exposure", "investment_horizon": "transition", "target_status": "APPROVED"},
            {"ticker": "PGR", "action": "ADD", "target_weight_pct": 10.0, "rationale": "diversifier", "investment_horizon": "long", "target_status": "APPROVED"},
            {"ticker": "JPM", "action": "ADD", "target_weight_pct": 10.0, "rationale": "diversifier", "investment_horizon": "long", "target_status": "APPROVED"},
        ],
        "material_unknowns": [],
        "decision_change_triggers": ["fresh broker snapshot"],
    }
    if include_priority:
        value["buy_priority"] = ["PGR", "JPM"]
    return value


def post_sell_evidence(*, cash: float = 13_000.0) -> dict:
    value = evidence(
        cash=cash, run_id="manual-post-sell-grade-b",
        decision_as_of="2026-08-21T22:05:00+00:00",
        holdings={"MVLL": 37, "NBIS": 20, "SOXL": 0, "PGR": 0, "JPM": 0},
    )
    value["broker_diff_status"] = "MATCH"
    return value


def post_sell_plan(*, cash_priority: bool = True) -> dict:
    value = plan(include_priority=cash_priority)
    value["post_sell_refresh"] = {
        "prior_run_id": value["evidence_binding"]["expected_run_id"],
        "prior_decision_as_of": value["evidence_binding"]["expected_decision_as_of"],
    }
    return value


def evidence_raw_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def current_context(value: dict, source_sha256: str | None = None) -> dict:
    return {
        "context_type": "PORTFOLIO_DECISION_CURRENT_SESSION_CONTEXT",
        "context_version": "1.0",
        "context_generated_at": value["decision_as_of"],
        "expected_evidence_run_id": value["manual_run_id"],
        "expected_evidence_sha256": source_sha256 or hashlib.sha256(evidence_raw_bytes(value)).hexdigest(),
        "expected_evidence_decision_as_of": value["decision_as_of"],
        "expected_completed_us_session": value["expected_completed_us_session"],
        "market_phase": value["market_phase"],
        "session_authority_market_phase": value["session_authority_market_phase"],
        "primary_listing_operating_mic": "XNAS",
        "calendar_policy_identity": value["calendar_policy_identity"],
        "calendar_hash": value["calendar_hash"],
        "session_activation_cohort_id": value["session_activation_cohort_id"],
        "context_status": "VERIFIED_CURRENT_SESSION",
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }


def verified_request_accounting(value: dict, source_sha256: str | None = None) -> dict:
    return {
        "schema_version": "1.0",
        "source_type": "KIWOOM_MANUAL_PORTFOLIO_ANALYSIS",
        "source_run_id": value["manual_run_id"],
        "source_artifact_sha256": source_sha256 or hashlib.sha256(evidence_raw_bytes(value)).hexdigest(),
        "generated_at": value["decision_as_of"],
        "verification_status": "VERIFIED_EXACT",
        "http_request_count": 5,
        "successful_request_count": 5,
        "failed_request_count": 0,
        "retry_count": 0,
        "operation_counts": {
            "account_holdings_read": 1, "account_deposit_read": 1,
            "oauth_health": 1, "market_quote": 1, "daily_chart": 1,
        },
        "endpoint_counts": {"account": 2, "oauth": 1, "quote": 1, "chart": 1},
        "order_authority": False,
        "execution_quantity": None,
        "automatic_order": False,
    }


def canonical_runtime_resolver(value: dict):
    def resolve(*_args, **_kwargs):
        return SimpleNamespace(
            authority_status="VERIFIED",
            expected_completed_session=SimpleNamespace(session_date=value["expected_completed_us_session"]),
            market_phase=value["session_authority_market_phase"],
            calendar_policy_identity=value["calendar_policy_identity"],
            calendar_hash=value["calendar_hash"],
            activation_cohort_id=value["session_activation_cohort_id"],
        )
    return resolve


class PortfolioDecisionDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_json(DEFAULT_RISK_POLICY)

    def compile(self, evidence_value=None, plan_value=None, **kwargs):
        source = evidence_value if evidence_value is not None else evidence()
        source_sha256 = hashlib.sha256(evidence_raw_bytes(source)).hexdigest()
        kwargs.setdefault("evidence_sha256", source_sha256)
        kwargs.setdefault("current_session_context", current_context(source, source_sha256))
        kwargs.setdefault("current_session_authority_resolver", canonical_runtime_resolver(source))
        return compile_dashboard(
            source, plan_value if plan_value is not None else plan(), self.policy,
            run_id="synthetic-run", generated_at=source["decision_as_of"], **kwargs,
        )

    def assert_display_line(self, report, label: str, value: str) -> None:
        self.assertIn(f"- {label}: {value}", render_markdown(report))
        self.assertIn(f"<p>{label}: {value}</p>", render_html(report))


    def captured_handoff_evidence(self):
        case = _manual_module.ManualPortfolioAnalysisTest(methodName="runTest")
        case.setUpClass()
        case.setUp()
        try:
            kwargs, artifacts = _manual_module.captured_handoff_fixture()
            source = case.build_report(**kwargs)
        finally:
            case.tearDown()
        proposal = plan(status="PROVISIONAL")
        proposal["evidence_binding"] = {"expected_run_id": source["manual_run_id"],
                                       "expected_decision_as_of": source["decision_as_of"]}
        proposal["as_of"] = source["decision_as_of"]
        return source, proposal, artifacts

    def handoff_gate(self, source, proposal, artifacts, generated=None):
        return dashboard._canonical_evidence_gate(
            source, proposal, "INITIAL_COMPILE", MANUAL_EVIDENCE_SCHEMA.read_bytes(),
            parent_capture_artifacts=artifacts,
            analysis_observed_at=generated or source["observed_at"])[1]

    def test_handoff_rewire_independent_consumed_bytes_unlock_time_gate(self):
        source, proposal, artifacts = self.captured_handoff_evidence()
        self.assertEqual(self.handoff_gate(source, proposal, artifacts), [])
        source_hash = hashlib.sha256(evidence_raw_bytes(source)).hexdigest()
        report, validation = compile_dashboard(
            source, proposal, self.policy, generated_at=source["observed_at"],
            parent_capture_artifacts=artifacts, evidence_sha256=source_hash)
        self.assertNotIn("EVIDENCE_FROM_FUTURE", validation["input_issues"])
        self.assertNotIn("POST_ACQUISITION_ANALYSIS_REQUIRES_FRESH_EVIDENCE", validation["input_issues"])
        self.assertNotIn("ACQUISITION_HANDOFF_NOT_VERIFIED", validation["input_issues"])
        self.assertFalse(report["authority"]["broker_order_authority"])

    def test_handoff_rewire_claim_without_consumed_bytes_stays_blocked(self):
        source, proposal, artifacts = self.captured_handoff_evidence()
        for supplied in [None, [], [(artifacts[0][0], "0" * 64)]]:
            with self.subTest(supplied=supplied is None):
                blockers = self.handoff_gate(source, proposal, supplied)
                self.assertIn("ACQUISITION_HANDOFF_NOT_VERIFIED", blockers)
                self.assertIn("POST_ACQUISITION_ANALYSIS_REQUIRES_FRESH_EVIDENCE", blockers)

    def test_handoff_rewire_analysis_clock_age_boundary(self):
        source, proposal, artifacts = self.captured_handoff_evidence()
        self.assertEqual(self.handoff_gate(source, proposal, artifacts, "2026-08-21T22:15:00+00:00"), [])
        for clock in ["2026-08-21T22:15:00.000001+00:00", "2026-08-21T22:00:06+00:00"]:
            with self.subTest(clock=clock):
                self.assertIn("ACQUISITION_HANDOFF_NOT_VERIFIED", self.handoff_gate(source, proposal, artifacts, clock))

    def test_handoff_rewire_evidence_projection_tampering_is_blocked(self):
        source, proposal, artifacts = self.captured_handoff_evidence()
        changes = [
            lambda d: d["broker_observed_state"]["cash"].update(order_available_cash=999),
            lambda d: d["broker_observed_state"]["holdings"][0].update(held_quantity=999),
            lambda d: d["current_price_evidence"][0]["record"].update(price=999),
            lambda d: d["historical_daily_evidence"][0]["records"][0].update(price=999),
            lambda d: d["last_verified_finalized_bars"][0]["bar"].update(price=999),
            lambda d: d.update(broker_snapshot_as_of="2026-08-21T22:00:02+00:00"),
            lambda d: d["manual_analysis_view"]["acquisition_handoff"].update(request_sha256="a" * 64),
        ]
        for change in changes:
            with self.subTest(change=change):
                altered = copy.deepcopy(source);change(altered)
                self.assertIn("ACQUISITION_HANDOFF_NOT_VERIFIED", self.handoff_gate(altered, proposal, artifacts))

    def test_handoff_rewire_request_scope_cannot_be_relabelled(self):
        source, proposal, artifacts = self.captured_handoff_evidence()
        source["broker_observed_state"]["acquisition_scope"]["account_operations"] = ["account_deposit_read"]
        self.assertIn("ACQUISITION_HANDOFF_NOT_VERIFIED", self.handoff_gate(source, proposal, artifacts))


    def test_loop_fix_orderable_display_does_not_expand_zero_funding(self):
        source = post_sell_evidence()
        cash = source["broker_observed_state"]["cash"]
        cash.update(order_available_cash=2.97, withdrawable_cash=0, settled_available_cash=0)
        source["verified_orderable_cash_usd"] = 2.97
        source["manual_analysis_view"]["verified_orderable_cash_usd"] = 2.97
        report, validation = self.compile(source, post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["cash_semantics"]["verified_orderable_cash_usd"]["value"], 2.97)
        self.assertEqual(report["swing_action_plan"]["cash"]["orderable_cash_usd"]["value"], 2.97)
        self.assertEqual(sum(r["calculated_buy_shares"] for r in report["stage2"]["buy_advisories"]), 0)
        self.assertFalse(report["authority"]["broker_order_authority"])
        self.assertTrue(validation["invariants"]["stage2_firewall"])

    def test_loop_fix_missing_conservative_cash_blocks_funding_not_zero(self):
        source = post_sell_evidence()
        source["broker_observed_state"]["cash"]["settled_available_cash"] = None
        report, _ = self.compile(source, post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("CONSERVATIVE_CASH_REQUIRED", report["stage2"]["blockers"])
        self.assertEqual(report["stage2"]["buy_advisories"], [])
        self.assertIsNone(report["cash_semantics"]["post_initial_buy_estimated_cash_usd"]["value"])

    def test_loop_fix_post_acquisition_diagnostic_never_unlocks_fresh_gate(self):
        source = evidence()
        later = "2026-08-21T22:00:02+00:00"
        source["observed_at"] = later
        source["manual_analysis_view"].update(
            analysis_observed_at=later, acquisition_completed_at=source["decision_as_of"])
        report, validation = self.compile(source)
        self.assertIn("POST_ACQUISITION_ANALYSIS_REQUIRES_FRESH_EVIDENCE", validation["input_issues"])
        self.assertNotEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertNotIn("EVIDENCE_FROM_FUTURE", validation["input_issues"])

    def test_loop_fix_unbound_observation_and_future_broker_still_block(self):
        for kind in ("unbound", "future_broker"):
            with self.subTest(kind=kind):
                source = evidence()
                later = "2026-08-21T22:00:02+00:00"
                if kind == "unbound":
                    source["observed_at"] = later
                else:
                    source["broker_snapshot_as_of"] = later
                report, validation = self.compile(source)
                self.assertIn("EVIDENCE_FROM_FUTURE", validation["input_issues"])
                self.assertNotEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def test_stage1_integer_floor_and_stage2_firewall(self):
        report, validation = self.compile()
        rows = {row["ticker"]: row for row in report["stage1"]["sell_advisories"]}
        self.assertEqual(rows["MVLL"]["target_shares_reference"], 37)
        self.assertEqual(rows["MVLL"]["calculated_sell_shares"], 63)
        self.assertEqual(rows["SOXL"]["calculated_sell_shares"], 20)
        self.assertEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED_POST_SELL_BROKER_REFRESH_REQUIRED")
        self.assertTrue(validation["invariants"]["stage2_firewall"])

    def test_swing_contract_is_inert_and_bound_to_consumed_inputs(self):
        source, decision = evidence(), plan()
        before = copy.deepcopy((source, decision, self.policy))
        report, validation = self.compile(source, decision)
        view = report["swing_action_plan"]
        self.assertEqual((source, decision, self.policy), before)
        self.assertTrue(validation["invariants"]["swing_action_contract"])
        self.assertEqual(view["stage"], "CONTRACT_ONLY")
        binding = view["source_binding"]
        self.assertEqual(binding["evidence_sha256"], hashlib.sha256(evidence_raw_bytes(source)).hexdigest())
        self.assertEqual(binding["plan_content_sha256"], hashlib.sha256(dashboard._json_bytes(decision)).hexdigest())
        self.assertEqual(binding["risk_policy_content_sha256"], hashlib.sha256(dashboard._json_bytes(self.policy)).hexdigest())
        self.assertEqual(binding["broker_snapshot_as_of"], source["broker_snapshot_as_of"])
        self.assertEqual(binding["policy_approval_binding"], "NOT_VERIFIED")
        for row in view["rows"]:
            for field in ("shadow_target_qty", "shadow_delta_qty", "shadow_buy_qty", "shadow_sell_qty", "shadow_cash_impact", "target_weight_pct"):
                self.assertIsNone(row[field])
            self.assertEqual(row["timing_status"], "NOT_VERIFIED")
            self.assertEqual(row["execution_status"], "DISABLED")
        self.assertFalse(view["order_authority"])
        self.assertEqual(view["quantity_authority"], "none")
        self.assertIsNone(view["execution_quantity"])
        self.assertEqual(view["broker_submission"], "disabled")
        again, _ = self.compile(source, decision)
        self.assertEqual(view, again["swing_action_plan"])

    def test_swing_action_quantity_conflicts_defer_only_affected_rows(self):
        cases = [
            ("HOLD", 12.0, "HOLD_TARGET_MUST_EQUAL_CURRENT"),
            ("EXIT", 10.0, "EXIT_TARGET_MUST_BE_ZERO"),
            ("TRIM", 0.0, "TRIM_FULL_REDUCTION_REQUIRES_EXIT_REVIEW"),
            ("TRIM", 14.0, "TRIM_TARGET_MUST_REDUCE_HOLDING"),
            ("ADD", 14.0, "BUY_ADD_TARGET_MUST_INCREASE_HOLDING"),
        ]
        for action, weight, issue in cases:
            with self.subTest(action=action, weight=weight):
                decision = plan()
                decision.pop("cash_target_pct")
                position = next(x for x in decision["positions"] if x["ticker"] == "NBIS")
                position.update(action=action, target_weight_pct=weight)
                report, _ = self.compile(plan_value=decision)
                rows = {x["ticker"]: x for x in report["swing_action_plan"]["rows"]}
                self.assertEqual(rows["NBIS"]["direction"], "DEFERRED")
                self.assertIn(issue, rows["NBIS"]["blockers"])
                self.assertEqual(rows["MVLL"]["direction"], "TRIM")

    def test_swing_candidate_semantics_hold_exit_buy_and_add(self):
        for action, weight, expected in [("HOLD", 14.0, "HOLD"), ("EXIT", 0.0, "EXIT"), ("ADD", 14.5, "ADD")]:
            with self.subTest(action=action):
                decision = plan()
                decision.pop("cash_target_pct")
                next(x for x in decision["positions"] if x["ticker"] == "NBIS").update(action=action, target_weight_pct=weight)
                report, _ = self.compile(plan_value=decision)
                rows = {x["ticker"]: x for x in report["swing_action_plan"]["rows"]}
                self.assertEqual(rows["NBIS"]["direction"], expected)
                self.assertEqual(rows["PGR"]["candidate_direction"], "BUY")
                self.assertIn("BUY_ADD_OUTSIDE_FIRST_SHADOW_SCOPE", rows["PGR"]["blockers"])
                self.assertIsNone(rows["NBIS"]["shadow_target_qty"])

    def test_swing_contract_rejects_quantity_and_authority_injection(self):
        report, _ = self.compile()
        mutations = [
            ("stage", "ACTIVE"), ("order_authority", True),
            ("quantity_authority", "approved"), ("execution_quantity", 1),
            ("broker_submission", "enabled"),
        ]
        for field, value in mutations:
            with self.subTest(field=field):
                bad = copy.deepcopy(report)
                bad["swing_action_plan"][field] = value
                self.assertTrue(dashboard.validate_swing_action_contract(bad))
        for field in ("shadow_target_qty", "shadow_delta_qty", "shadow_buy_qty", "shadow_sell_qty", "shadow_cash_impact", "target_weight_pct"):
            with self.subTest(field=field):
                bad = copy.deepcopy(report)
                bad["swing_action_plan"]["rows"][0][field] = 1
                self.assertTrue(dashboard.validate_swing_action_contract(bad))
        bad = copy.deepcopy(report)
        next(x for x in bad["swing_action_plan"]["rows"] if x["ticker"] == "NBIS")["direction"] = "HOLD"
        self.assertTrue(dashboard.validate_swing_action_contract(bad))

    def test_swing_contract_cash_types_remain_distinct_and_unknown_is_not_zero(self):
        source = evidence()
        source["verified_orderable_cash_usd"] = 123.0
        report, _ = self.compile(source)
        cash = report["swing_action_plan"]["cash"]
        self.assertEqual(cash["orderable_cash_usd"]["value"], 123.0)
        self.assertEqual(cash["nav_cash_usd"]["value"], 10000.0)
        self.assertEqual(cash["snapshot_alignment"], "NOT_VERIFIED")
        self.assertFalse(cash["expected_proceeds_are_orderable"])
        source["broker_observed_state"]["cash"]["cash_status"] = "NOT_VERIFIED"
        source["orderable_cash_status"] = "NOT_VERIFIED"
        report, _ = self.compile(source)
        cash = report["swing_action_plan"]["cash"]
        self.assertIsNone(cash["nav_cash_usd"]["value"])
        self.assertIsNone(cash["orderable_cash_usd"]["value"])

    def test_swing_contract_historical_or_unbound_evidence_stays_deferred(self):
        for kwargs in ({"compile_mode": "HISTORICAL_REPLAY"}, {"current_session_context": None}):
            with self.subTest(kwargs=kwargs):
                report, _ = self.compile(**kwargs)
                for row in report["swing_action_plan"]["rows"]:
                    self.assertEqual(row["direction"], "DEFERRED")
                    self.assertEqual(row["quantity_status"], "NOT_VERIFIED")

    def test_swing_missing_target_does_not_invent_hold_or_block_other_directions(self):
        decision = plan()
        next(x for x in decision["positions"] if x["ticker"] == "NBIS").pop("target_weight_pct")
        report, _ = self.compile(plan_value=decision)
        rows = {x["ticker"]: x for x in report["swing_action_plan"]["rows"]}
        self.assertEqual(rows["NBIS"]["direction"], "HOLD")
        self.assertEqual(rows["NBIS"]["quantity_status"], "NOT_VERIFIED")
        self.assertIsNone(rows["NBIS"]["shadow_target_qty"])
        self.assertEqual(rows["MVLL"]["direction"], "TRIM")
        decision["positions"] = [x for x in decision["positions"] if x["ticker"] != "NBIS"]
        report, _ = self.compile(plan_value=decision)
        row = next(x for x in report["swing_action_plan"]["rows"] if x["ticker"] == "NBIS")
        self.assertEqual(row["direction"], "DEFERRED")

    def test_swing_validator_rejects_cash_substitution_and_false_binding(self):
        report, _ = self.compile()
        for key, value in (("plan_id", "wrong-plan"), ("evidence_run_id", "wrong-run")):
            with self.subTest(key=key):
                bad = copy.deepcopy(report)
                bad["swing_action_plan"]["source_binding"][key] = value
                self.assertIn(f"SWING_SOURCE_BINDING_MISMATCH:{key}", dashboard.validate_swing_action_contract(bad))
        bad = copy.deepcopy(report)
        bad["swing_action_plan"]["cash"]["orderable_cash_usd"]["value"] += 1
        self.assertIn("SWING_CASH_SEMANTICS_MISMATCH:orderable_cash_usd", dashboard.validate_swing_action_contract(bad))

    def test_swing_contract_primary_render_and_legacy_compatibility(self):
        report, _ = self.compile()
        before = copy.deepcopy(report)
        for output in (render_markdown(report), render_html(report)):
            self.assertLess(output.index("[한눈에 보기]"), output.index("위험 축소 1단계"))
            for token in ("Swing Action Plan", "KEEP_CASH", "DISABLED", "POLICY_REQUIRED"):
                if token == "KEEP_CASH":
                    self.assertEqual(report["swing_action_plan"]["cash"]["alternative"], token)
                else:
                    self.assertIn(token, output)
        self.assertEqual(report, before)
        report.pop("swing_action_plan")
        self.assertEqual(dashboard.validate_swing_action_contract(report), [])
        self.assertNotIn("Swing Action Plan", render_markdown(report))
        self.assertNotIn("Swing Action Plan", render_html(report))

    def test_missing_holdings_fails_closed(self):
        source = evidence()
        source["broker_observed_state"]["holdings"] = []
        report, _ = self.compile(source)
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertIn("MISSING_HOLDINGS", report["evidence"]["issues"])

    def _assert_swing_r1_label_outputs(self, labels):
        for index, label in enumerate(labels):
            with self.subTest(label=label):
                secret = f"SYNTH_R1_PRIVATE_VALUE_{index}_x783"
                decision = plan()
                position = next(row for row in decision["positions"] if row["ticker"] == "MVLL")
                position["rationale"] = f"Review {label}: {secret}"
                position["decision_change_triggers"] = [f'"{label}" = "{secret}"']
                decision["decision_change_triggers"] = [f"{label}: {secret}"]
                original = copy.deepcopy(decision)
                report, validation = self.compile(plan_value=decision)
                self.assertTrue(validation["invariants"]["swing_action_contract"])
                self.assertEqual(decision, original)
                row = next(row for row in report["swing_action_plan"]["rows"] if row["ticker"] == "MVLL")
                self.assertEqual(row["reason"], "[민감정보 제거]")
                self.assertEqual(row["invalidation"], ["[민감정보 제거]"])
                outputs = [json.dumps(report["swing_action_plan"], ensure_ascii=False),
                           render_html(report), render_markdown(report)]
                with tempfile.TemporaryDirectory() as temp, patch.object(dashboard, "_git_commit", return_value=None):
                    root = Path(temp)
                    run = write_run(report, validation, output_root=root / "runs", root=root,
                                    source_paths={}, implementation_paths=[])
                    outputs.extend(p.read_text(encoding="utf-8") for p in run.iterdir() if p.is_file())
                for output in outputs:
                    self.assertNotIn(secret, output)

    def test_swing_r1_account_label_variants(self):
        self._assert_swing_r1_label_outputs(["account id", "account-id", "account_id", "accountId", "ACCOUNT_ID"])

    def test_swing_r1_app_key_label_variants(self):
        self._assert_swing_r1_label_outputs(["app key", "app-key", "app_key", "appKey", "APPKEY"])

    def test_swing_r1_app_secret_label_variants(self):
        self._assert_swing_r1_label_outputs(["app secret", "app-secret", "app_secret", "appSecret"])

    def test_swing_r1_order_label_variants(self):
        self._assert_swing_r1_label_outputs(["order id", "order-id", "order_id", "orderId"])

    def test_swing_r1_credential_label_variants(self):
        self._assert_swing_r1_label_outputs(["credential path", "credential-path", "credential_path", "credentialPath"])

    def test_swing_r1_existing_token_authorization_raw_labels(self):
        self._assert_swing_r1_label_outputs(["token", "TOKEN", "Authorization", "raw broker response",
                                           "raw-broker-response", "raw_broker_response", "rawBrokerResponse"])

    def test_swing_r1_unicode_label_normalization_only(self):
        self._assert_swing_r1_label_outputs(["ａｃｃｏｕｎｔ　ｉｄ", "ＡＰＰ－ＫＥＹ", "app\u00a0secret"])
        self.assertEqual(dashboard._safe_swing_text("ａｃｃｏｕｎｔ　ｉｄ：SYNTH_ONLY"), "[민감정보 제거]")
        self.assertEqual(dashboard._safe_swing_text("ａｐｐＫｅｙ＝SYNTH_ONLY"), "[민감정보 제거]")

    def test_swing_r1_loaded_report_variants_use_same_boundary(self):
        report, validation = self.compile()
        secret = "SYNTH_R1_LOADED_VALUE_x782"
        row = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "MVLL")
        row["rationale"] = f"account id: {secret}"
        row["decision_change_triggers"] = [f"appKey: {secret}"]
        report["swing_action_plan"]["rows"] = dashboard._swing_rows(report)
        original = copy.deepcopy(report)
        outputs = [json.dumps(report["swing_action_plan"]), render_html(report), render_markdown(report)]
        with tempfile.TemporaryDirectory() as temp, patch.object(dashboard, "_git_commit", return_value=None):
            root = Path(temp)
            run = write_run(report, validation, output_root=root / "runs", root=root,
                            source_paths={}, implementation_paths=[])
            outputs.extend(p.read_text(encoding="utf-8") for p in run.iterdir() if p.is_file())
        for output in outputs:
            self.assertNotIn(secret, output)
        self.assertEqual(report, original)

    def test_swing_r1_false_positive_general_labels_preserved(self):
        phrases = ["account identity status", "application key concept", "order policy",
                   "credential handling policy", "authorization status"]
        for phrase in phrases:
            for text in [phrase, phrase + ": reviewed", phrase + " = reviewed"]:
                with self.subTest(text=text):
                    self.assertEqual(dashboard._safe_swing_text(text), text)
        text = "authorization status: 정상 Kept ＡＢＣ"
        self.assertEqual(dashboard._safe_swing_text(text), text)

    def test_swing_r1_false_positive_all_output_paths_preserved(self):
        for phrase in ["account identity status", "application key concept", "order policy",
                       "credential handling policy", "authorization status"]:
            with self.subTest(phrase=phrase):
                text = phrase + ": reviewed"
                decision = plan()
                row = next(row for row in decision["positions"] if row["ticker"] == "MVLL")
                row["rationale"] = text
                row["decision_change_triggers"] = [text]
                decision["decision_change_triggers"] = [text]
                report, validation = self.compile(plan_value=decision)
                outputs = [json.dumps(report["swing_action_plan"]), render_html(report), render_markdown(report)]
                with tempfile.TemporaryDirectory() as temp, patch.object(dashboard, "_git_commit", return_value=None):
                    root = Path(temp)
                    run = write_run(report, validation, output_root=root / "runs", root=root,
                                    source_paths={}, implementation_paths=[])
                    outputs.extend((run / name).read_text(encoding="utf-8") for name in
                                   ["portfolio-decision.json", "portfolio-decision-dashboard.html", "portfolio-decision-dashboard.md"])
                for output in outputs:
                    self.assertIn(text, output)

    def test_swing_r1_fullwidth_account_label_outputs(self):
        self._assert_swing_r1_label_outputs(["ＡＣＣＯＵＮＴ＿ＩＤ"])

    def test_swing_r1_fullwidth_app_key_label_outputs(self):
        self._assert_swing_r1_label_outputs(["ＡＰＰ＿ＫＥＹ"])

    def test_swing_r1_fullwidth_order_label_outputs(self):
        self._assert_swing_r1_label_outputs(["ＯＲＤＥＲ＿ＩＤ"])

    def test_swing_r1_fullwidth_credential_label_outputs(self):
        self._assert_swing_r1_label_outputs(["ＣＲＥＤＥＮＴＩＡＬ＿ＰＡＴＨ"])

    def test_swing_r1_fullwidth_raw_broker_label_outputs(self):
        self._assert_swing_r1_label_outputs(["ＲＡＷ＿ＢＲＯＫＥＲ＿ＲＥＳＰＯＮＳＥ"])

    def test_swing_r1_fullwidth_mixed_labels_outputs(self):
        self._assert_swing_r1_label_outputs([
            "ACCOUNT＿ID", "APP＿KEY", "ORDER＿ID", "APP＿SECRET",
            "ＣＲＥＤＥＮＴＩＡＬ＿PATH", "RAW＿BROKER_RESPONSE"])

    def test_swing_r1_fullwidth_normal_unicode_preserved_in_outputs(self):
        text = "authorization status: 정상 한국어 설명 Kept ＡＢＣ＿１２３ ①"
        self.assertEqual(dashboard._safe_swing_text(text), text)
        decision = plan()
        row = next(row for row in decision["positions"] if row["ticker"] == "MVLL")
        row["rationale"] = text
        row["decision_change_triggers"] = [text]
        decision["decision_change_triggers"] = [text]
        original = copy.deepcopy(decision)
        report, validation = self.compile(plan_value=decision)
        self.assertEqual(decision, original)
        swing_row = next(row for row in report["swing_action_plan"]["rows"] if row["ticker"] == "MVLL")
        self.assertEqual(swing_row["reason"], text)
        self.assertEqual(swing_row["invalidation"], [text])
        outputs = [json.dumps(report["swing_action_plan"], ensure_ascii=False),
                   render_html(report), render_markdown(report)]
        with tempfile.TemporaryDirectory() as temp, patch.object(dashboard, "_git_commit", return_value=None):
            root = Path(temp)
            run = write_run(report, validation, output_root=root / "runs", root=root,
                            source_paths={}, implementation_paths=[])
            outputs.extend((run / name).read_text(encoding="utf-8") for name in
                           ["portfolio-decision.json", "portfolio-decision-dashboard.html", "portfolio-decision-dashboard.md"])
        for output in outputs:
            self.assertIn(text, output)

    def test_swing_fix_001_secret_categories_are_redacted_in_all_outputs(self):
        secrets = {
            "account_id": "SYNTH_ACCOUNT_847215", "token": "SYNTH_TOKEN_a903X",
            "APP_KEY": "SYNTH_APPKEY_f471X", "APP_SECRET": "SYNTH_APPSECRET_e833X",
            "Authorization": "Bearer SYNTH_AUTH_b621X", "raw_broker_response": "SYNTH_BROKER_RAW_f537X",
            "order_id": "SYNTH_ORDER_903772", "credential_path": r"C:\SYNTH_ONLY\secret_credentials.json",
        }
        for label, secret in secrets.items():
            with self.subTest(label=label):
                decision = plan()
                position = next(row for row in decision["positions"] if row["ticker"] == "MVLL")
                position["rationale"] = f"{label}={secret} trailing words"
                position["decision_change_triggers"] = [f"{label}: {secret}"]
                original = copy.deepcopy(decision)
                report, validation = self.compile(plan_value=decision)
                self.assertTrue(validation["invariants"]["swing_action_contract"])
                self.assertEqual(decision, original)
                row = next(row for row in report["swing_action_plan"]["rows"] if row["ticker"] == "MVLL")
                self.assertEqual(row["reason"], "[민감정보 제거]")
                self.assertEqual(row["invalidation"], ["[민감정보 제거]"])
                for output in (str(report), render_html(report), render_markdown(report),
                               dashboard._render_swing_action_plan(report, as_html=True)):
                    self.assertNotIn(secret, output)

    def test_swing_fix_001_persistence_is_safe_and_does_not_mutate_input(self):
        decision = plan()
        secret = "SYNTH_PERSIST_SECRET_xyz"
        position = next(row for row in decision["positions"] if row["ticker"] == "MVLL")
        position["rationale"] = f'"APP_SECRET": "{secret}"'
        position["decision_change_triggers"] = [f"token={secret}"]
        report, validation = self.compile(plan_value=decision)
        before = copy.deepcopy(report)
        with tempfile.TemporaryDirectory() as temp, patch.object(dashboard, "_git_commit", return_value=None):
            root = Path(temp)
            run_dir = write_run(report, validation, output_root=root / "runs", root=root,
                                source_paths={}, implementation_paths=[])
            for name in ("portfolio-decision.json", "portfolio-decision-dashboard.html",
                         "portfolio-decision-dashboard.md", "validation-report.json"):
                self.assertNotIn(secret, (run_dir / name).read_text(encoding="utf-8"))
            stored = load_json(run_dir / "portfolio-decision.json")
            self.assertEqual(dashboard.validate_swing_action_contract(stored), [])
        self.assertEqual(before, report)

    def test_swing_fix_001_loaded_report_repeats_are_safe(self):
        report, _ = self.compile()
        secret = "SYNTH_LOADED_SECRET_xyz"
        source = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "MVLL")
        source["rationale"] = "APP_SECRET=" + secret
        source["decision_change_triggers"] = ["token=" + secret]
        # Simulate an input-aware producer with safe derived rows but legacy repeats.
        report["swing_action_plan"]["rows"] = dashboard._swing_rows(report)
        report["stage1"]["sell_advisories"][0]["reason"] = "APP_SECRET=" + secret
        before = copy.deepcopy(report)
        for output in (render_html(report), render_markdown(report), str(dashboard._safe_swing_report(report))):
            self.assertNotIn(secret, output)
        self.assertEqual(before, report)

    def test_swing_fix_002_invalid_view_diagnostics_do_not_echo(self):
        report, _ = self.compile()
        secret = "SYNTH_AUTH_ERROR_b621X"
        for field in ("direction", "candidate_direction", "unexpected"):
            with self.subTest(field=field):
                bad = copy.deepcopy(report)
                row = bad["swing_action_plan"]["rows"][0]
                if field == "unexpected":
                    row[secret] = "Authorization=Bearer " + secret
                else:
                    row[field] = "Authorization=Bearer " + secret
                errors = dashboard.validate_swing_action_contract(bad)
                self.assertTrue(errors)
                self.assertNotIn(secret, str(errors))
                with self.assertRaisesRegex(ContractError, "^SWING_ACTION_CONTRACT_INVALID$"):
                    render_html(bad)

    def test_swing_fix_002_invalid_plan_action_does_not_echo(self):
        decision = plan()
        secret = "SYNTH_PLAN_SECRET_error"
        decision["positions"][0]["action"] = "Authorization=Bearer " + secret
        self.assertTrue(validate_plan(decision))
        self.assertNotIn(secret, str(validate_plan(decision)))
        with self.assertRaises(ContractError) as error:
            self.compile(plan_value=decision)
        self.assertNotIn(secret, str(error.exception))

    def test_swing_fix_003_all_derived_fields_are_bound(self):
        report, _ = self.compile()
        mutations = {
            "candidate_direction": "BUY", "direction": "HOLD", "price": 9999,
            "price_status": "NOT_VERIFIED", "price_session": "2099-01-01",
            "current_qty": 9999, "current_qty_status": "SYNTH_FAKE_VERIFIED",
            "reason": "forged rationale", "invalidation": ["forged condition"],
            "quantity_status": "NOT_VERIFIED", "blockers": [],
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                bad = copy.deepcopy(report)
                row = next(row for row in bad["swing_action_plan"]["rows"] if row["ticker"] == "MVLL")
                if row[field] == value:
                    value = "POLICY_REQUIRED" if field == "quantity_status" else "DERIVED"
                row[field] = value
                self.assertTrue(dashboard.validate_swing_action_contract(bad))

    def test_swing_fix_003_tampered_view_cannot_render_or_persist(self):
        report, validation = self.compile()
        next(row for row in report["swing_action_plan"]["rows"] if row["ticker"] == "MVLL")["candidate_direction"] = "BUY"
        for renderer in (render_html, render_markdown, dashboard._render_swing_action_plan):
            with self.subTest(renderer=renderer.__name__):
                with self.assertRaisesRegex(ContractError, "^SWING_ACTION_CONTRACT_INVALID$"):
                    renderer(report)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ContractError, "^SWING_ACTION_CONTRACT_INVALID$"):
                write_run(report, validation, output_root=root / "runs", root=root,
                          source_paths={}, implementation_paths=[])
            self.assertEqual(list(root.iterdir()), [])

    def test_swing_fix_003_canonical_change_invalidates_stale_view(self):
        report, _ = self.compile()
        source = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "MVLL")
        source["rationale"] = "updated canonical reason"
        self.assertTrue(dashboard.validate_swing_action_contract(report))
        report["swing_action_plan"]["rows"] = dashboard._swing_rows(report)
        self.assertEqual(dashboard.validate_swing_action_contract(report), [])
        self.assertIn("updated canonical reason", dashboard._render_swing_action_plan(report))

    def test_swing_fix_004_standalone_hash_checks_are_format_only(self):
        report, _ = self.compile()
        for field in ("evidence_sha256", "plan_content_sha256", "risk_policy_content_sha256"):
            with self.subTest(field=field):
                changed = copy.deepcopy(report)
                changed["swing_action_plan"]["source_binding"][field] = "f" * 64
                self.assertEqual(dashboard.validate_swing_action_contract(changed), [])
                self.assertIn("형식만 확인", dashboard._render_swing_action_plan(changed))
                self.assertIn("NOT_VERIFIED", dashboard._render_swing_action_plan(changed))
                changed["swing_action_plan"]["source_binding"][field] = "not-a-hash"
                self.assertTrue(dashboard.validate_swing_action_contract(changed))

    def test_swing_fix_004_consumed_inputs_detect_hash_and_metadata_tamper(self):
        source, decision = evidence(), plan()
        report, _ = self.compile(source, decision)
        inputs = dict(evidence=source, plan=decision, risk_policy=self.policy,
                      evidence_sha256=hashlib.sha256(evidence_raw_bytes(source)).hexdigest())
        self.assertEqual(dashboard.validate_swing_action_contract(report, **inputs), [])
        for field, value in (("evidence_sha256", "f" * 64), ("plan_content_sha256", "f" * 64),
                             ("risk_policy_content_sha256", "f" * 64),
                             ("broker_snapshot_as_of", "2099-01-01T00:00:00+00:00"),
                             ("risk_policy_version", "forged-version")):
            with self.subTest(field=field):
                bad = copy.deepcopy(report)
                bad["swing_action_plan"]["source_binding"][field] = value
                self.assertIn("SWING_CONSUMED_INPUT_BINDING_MISMATCH",
                              dashboard.validate_swing_action_contract(bad, **inputs))

    def test_swing_fix_004_incomplete_inputs_do_not_claim_provenance(self):
        report, _ = self.compile()
        for inputs in ({"plan": plan()}, {"evidence": evidence()}, {"evidence_sha256": "f" * 64}):
            with self.subTest(inputs=list(inputs)):
                self.assertIn("SWING_PROVENANCE_INPUTS_INCOMPLETE",
                              dashboard.validate_swing_action_contract(report, **inputs))

    def test_swing_fix_005_reason_and_invalidation_are_in_primary_table(self):
        report, _ = self.compile()
        rendered = dashboard._render_swing_action_plan(report, as_html=True)
        table = rendered.split("<table>", 1)[1].split("</table>", 1)[0]
        for text in ("근거", "무효화·재평가", "leveraged concentration", "risk cap changes"):
            self.assertIn(text, table)
        markdown = dashboard._render_swing_action_plan(report)
        row = next(line for line in markdown.splitlines() if line.startswith("| MVLL |"))
        self.assertIn("leveraged concentration", row)
        self.assertIn("risk cap changes", row)
        self.assertIn("<details>", rendered)
        self.assertIn("미산출", table)

    def test_swing_fix_005_concise_table_keeps_full_safe_details(self):
        decision = plan()
        position = next(row for row in decision["positions"] if row["ticker"] == "MVLL")
        position["rationale"] = "ordinary evidence " * 15
        report, _ = self.compile(plan_value=decision)
        rendered = dashboard._render_swing_action_plan(report, as_html=True)
        table = rendered.split("<table>", 1)[1].split("</table>", 1)[0]
        self.assertNotIn(position["rationale"], table)
        self.assertIn(position["rationale"], rendered.split("<details>", 1)[1])

    def test_swing_fix_legacy_absence_allowed_explicit_null_rejected(self):
        report, _ = self.compile()
        report["swing_action_plan"] = None
        self.assertTrue(dashboard.validate_swing_action_contract(report))
        with self.assertRaises(ContractError):
            render_html(report)
        report.pop("swing_action_plan")
        self.assertEqual(dashboard.validate_swing_action_contract(report), [])
        self.assertNotIn("Swing Action Plan", render_html(report))

    def test_missing_current_cash_blocks_nav(self):
        source = evidence()
        del source["broker_observed_state"]["cash"]["foreign_currency_deposit"]
        report, _ = self.compile(source)
        self.assertIsNone(report["portfolio"]["nav_usd"]["value"])
        self.assertIn("MISSING_CURRENT_CASH", report["evidence"]["issues"])

    def test_missing_orderable_cash_blocks_post_sell_stage2(self):
        source = post_sell_evidence()
        source["orderable_cash_status"] = "NOT_VERIFIED"
        source["verified_orderable_cash_usd"] = None
        report, _ = self.compile(source, post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("VERIFIED_ORDERABLE_CASH_REQUIRED", report["stage2"]["blockers"])

    def test_missing_price_blocks_only_affected_candidate(self):
        source = evidence()
        source["last_verified_finalized_bars"] = [item for item in source["last_verified_finalized_bars"] if item["ticker"] != "PGR"]
        report, _ = self.compile(source)
        pgr = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "PGR")
        self.assertIn("BLOCKED_CANONICAL_PRICE_REQUIRED", pgr["blockers"])
        self.assertIsNotNone(report["portfolio"]["nav_usd"]["value"])

    def test_duplicate_ticker_in_plan_rejected(self):
        value = plan()
        value["positions"].append(copy.deepcopy(value["positions"][0]))
        self.assertTrue(any("DUPLICATE_TICKER" in item for item in validate_plan(value)))
        with self.assertRaises(ContractError):
            self.compile(plan_value=value)

    def test_duplicate_broker_ticker_visible_and_blocked(self):
        source = evidence()
        source["broker_observed_state"]["holdings"].append(copy.deepcopy(source["broker_observed_state"]["holdings"][0]))
        report, _ = self.compile(source)
        self.assertTrue(any("DUPLICATE_BROKER_TICKER" in item for item in report["evidence"]["issues"]))

    def test_broker_system_mismatch_keeps_broker_canonical(self):
        report, _ = self.compile()
        mvll = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "MVLL")
        self.assertEqual(mvll["current_quantity"]["value"], 100)
        self.assertIn("BROKER_SYSTEM_MISMATCH_BROKER_CANONICAL", report["evidence"]["warnings"])

    def test_non_regular_market_is_provisional(self):
        report, _ = self.compile(evidence(market_phase="MARKET_CLOSED"))
        self.assertEqual(report["stage1"]["status"], "PROVISIONAL")
        self.assertEqual(report["evidence"]["current_freshness"], "CURRENT_SESSION_CONTEXT_VERIFIED")

    def test_historical_plan_is_replay_only(self):
        report, _ = self.compile(plan_value=plan(status="HISTORICAL"), compile_mode="HISTORICAL_REPLAY")
        self.assertEqual(report["stage1"]["status"], "REPLAY_ONLY")
        self.assertEqual(report["stage2"]["status"], "REPLAY_ONLY")
        self.assertEqual(report["evidence"]["current_freshness"], "HISTORICAL_REPLAY")
        self.assertEqual(report["evidence"]["portfolio_evidence_grade_display"], "GRADE_B_AT_ARTIFACT_TIME")
        self.assert_display_line(report, "현재 자료 상태", "과거 자료 / 현재 판단 사용 불가 (HISTORICAL_REPLAY)")
        for rendered in (render_markdown(report), render_html(report)):
            self.assertNotIn("현재 자료 (CURRENT_SESSION_CONTEXT_VERIFIED)", rendered)

    def test_schema_version_downgrade_is_rejected_outside_historical_replay(self):
        downgraded = evidence()
        downgraded["schema_version"] = "2.0"
        del downgraded["integrated_authority_snapshot_provenance"]

        current_report, current_validation = self.compile(downgraded)
        self.assertTrue(current_report["evidence"]["canonical_schema_errors"])
        self.assertEqual(current_report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertEqual(current_validation["status"], "FAIL")

        replay_report, replay_validation = self.compile(
            downgraded,
            plan(status="HISTORICAL"),
            compile_mode="HISTORICAL_REPLAY",
        )
        self.assertEqual(replay_report["evidence"]["canonical_schema_errors"], [])
        self.assertEqual(replay_report["stage1"]["status"], "REPLAY_ONLY")
        self.assertEqual(replay_validation["status"], "PASS")

    def test_input_order_authority_fails_closed(self):
        source = evidence()
        source["order_authority"] = True
        report, _ = self.compile(source)
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertIn("INPUT_ORDER_AUTHORITY_NOT_FALSE", report["evidence"]["issues"])

    def test_missing_target_weight_blocks_ticker_without_invention(self):
        value = plan()
        del value["positions"][3]["target_weight_pct"]
        report, _ = self.compile(plan_value=value)
        pgr = next(row for row in report["portfolio"]["positions"] if row["ticker"] == "PGR")
        self.assertIn("BLOCKED_TARGET_WEIGHT_REQUIRED", pgr["blockers"])
        self.assertIsNone(pgr["target_shares_reference"]["value"])

    def test_target_weight_outside_range_rejected(self):
        value = plan()
        del value["cash_target_pct"]
        value["positions"][0]["target_weight_pct"] = 101.0
        with self.assertRaises(ContractError):
            self.compile(plan_value=value)

    def test_deadband_prefers_no_trade(self):
        source = evidence(cash=900.0)
        source["broker_observed_state"]["holdings"] = [{"ticker": "PGR", "held_quantity": 1, "average_cost": 90.0}]
        source["last_verified_finalized_bars"] = [
            item for item in source["last_verified_finalized_bars"] if item["ticker"] == "PGR"
        ]
        source["last_verified_finalized_bars"][0]["bar"]["price"] = 100.0
        value = {
            "plan_id": "deadband", "as_of": "2026-08-21T22:00:00+00:00", "plan_status": "CURRENT_APPROVED",
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 89.0,
            "evidence_binding": {"expected_run_id": "manual-synthetic-grade-b", "expected_decision_as_of": "2026-08-21T22:00:00+00:00"},
            "positions": [{"ticker": "PGR", "action": "HOLD", "target_weight_pct": 11.0, "rationale": "inside deadband", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = report["portfolio"]["positions"][0]
        self.assertEqual(row["deadband_status"], "NO_TRADE_PREFERRED")
        self.assertEqual(row["share_delta"]["value"], 0)

    def test_hard_cap_violation_is_visible(self):
        report, _ = self.compile()
        violations = report["portfolio"]["current_risk"]["hard_cap_violations"]
        self.assertIn("POSITION_PCT:MVLL", violations)

    def test_expected_sale_proceeds_never_become_orderable_cash(self):
        report, _ = self.compile()
        self.assertGreater(report["stage1"]["expected_sale_proceeds_usd"]["value"], 0)
        self.assertEqual(report["cash_semantics"]["verified_orderable_cash_usd"]["value"], 10_000.0)
        self.assertFalse(report["cash_semantics"]["expected_proceeds_treated_as_orderable_cash"])
        self.assertIsNotNone(report["cash_semantics"]["full_target_reference_cash_usd"]["value"])

    def test_post_sell_verified_cash_permits_stage2(self):
        report, _ = self.compile(post_sell_evidence(), post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertTrue(report["stage2"]["buy_advisories"])
        self.assertTrue(all(row["calculated_buy_shares"] >= 0 for row in report["stage2"]["buy_advisories"]))

    def test_insufficient_buy_cash_requires_priority(self):
        report, _ = self.compile(post_sell_evidence(cash=50.0), post_sell_plan(cash_priority=False), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("BUY_ALLOCATION_PRIORITY_REQUIRED", report["stage2"]["blockers"])

    def test_open_items_and_request_accounting_remain_visible(self):
        source = evidence()
        source["broker_observed_state"]["operation_statuses"]["account_open_items"] = "KIWOOM_API_RESPONSE_ERROR"
        report, _ = self.compile(source)
        self.assertIn("OPEN_ITEMS_VISIBILITY_UNAVAILABLE", report["evidence"]["warnings"])
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")
        self.assertEqual(report["evidence"]["request_accounting"]["account_holdings_read"], "PASS")
        self.assertEqual(report["authority"]["artifact_time_quantity_authority"], "none")

    def test_no_event_context_and_high_event_context(self):
        without, _ = self.compile()
        with_high, _ = self.compile(event_context={"current_high_count": 2, "new_high_count": 1, "affected_tickers": ["MVLL"]})
        self.assertEqual(without["event_context"]["status"], "NOT_PROVIDED")
        self.assertEqual(with_high["event_context"]["current_high_count"], 2)
        self.assertFalse(with_high["event_context"]["automatic_target_change"])

    def test_no_order_path_and_renderer_parity(self):
        report, validation = self.compile()
        markdown = render_markdown(report)
        dashboard_html = render_html(report)
        for token in ("MVLL", "63", "Broker Order Authority", "FALSE"):
            self.assertIn(token, markdown)
            self.assertIn(token, dashboard_html)
        self.assertFalse(report["authority"]["broker_order_authority"])
        self.assertIsNone(report["authority"]["execution_quantity"])
        self.assertFalse(report["authority"]["automatic_order"])
        self.assertFalse(validation["network_used"])
        self.assertFalse(validation["broker_used"])
        self.assertFalse(validation["order_path_used"])

    def test_canonical_synthetic_fixture_is_schema_valid(self):
        source = evidence()
        self.assertEqual(validate_instance(source, MANUAL_EVIDENCE_SCHEMA), [])
        report, validation = self.compile(source)
        self.assertEqual(report["evidence"]["canonical_schema_errors"], [])
        self.assertEqual(report["evidence"]["canonical_schema_sha256"], hashlib.sha256(MANUAL_EVIDENCE_SCHEMA.read_bytes()).hexdigest())
        self.assertTrue(validation["invariants"]["canonical_evidence_schema"])

    def test_noncanonical_regular_literal_never_finalizes_stage1(self):
        source = evidence()
        source["market_phase"] = "REGULAR"
        report, validation = self.compile(source)
        self.assertNotEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertEqual(validation["status"], "FAIL")

    def test_decimal_floor_boundary_avoids_binary_float_underallocation(self):
        source = evidence(cash=1290.50, holdings={"PGR": 0})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 0.89
        value = {
            "plan_id": "decimal-boundary", "as_of": source["decision_as_of"],
            "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 98.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 2.0,
                           "rationale": "decimal boundary", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertEqual(row["target_shares_reference"]["value"], 29)

    def test_total_targets_over_100_rejected_without_cash_target(self):
        value = plan()
        del value["cash_target_pct"]
        value["positions"][0]["target_weight_pct"] = 70.0
        value["positions"][1]["target_weight_pct"] = 40.0
        self.assertTrue(any("TARGET_ALLOCATION_EXCEEDS_100_PERCENT" in item for item in validate_plan(value)))
        with self.assertRaises(ContractError):
            self.compile(plan_value=value)

    def test_target_hard_cap_blocks_deadband(self):
        source = evidence(cash=852.0, holdings={"PGR": 148})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 1.0
        value = {
            "plan_id": "target-hard-cap", "as_of": source["decision_as_of"], "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 84.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 16.0,
                           "rationale": "counterexample", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertIn("TARGET_HARD_CAP_VIOLATION", row["blockers"])
        self.assertEqual(row["deadband_status"], "NOT_APPLIED")

    def test_partial_priority_is_blocked_when_cash_is_insufficient(self):
        value = post_sell_plan()
        value["buy_priority"] = ["PGR"]
        report, _ = self.compile(post_sell_evidence(cash=50.0), value, compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("BUY_ALLOCATION_PRIORITY_INCOMPLETE", report["stage2"]["blockers"])
        self.assertEqual(report["stage2"]["buy_advisories"], [])

    def test_post_sell_requires_newer_bound_run_and_eligible_session(self):
        stale = evidence()
        value = post_sell_plan()
        stale_report, _ = self.compile(stale, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(stale_report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertIn("POST_SELL_FRESH_RUN_REQUIRED", stale_report["evidence"]["canonical_gate_blockers"])
        pre_market = post_sell_evidence()
        pre_market["market_phase"] = "PRE_MARKET"
        pre_market["current_session_finalization_status"] = "NOT_VERIFIED"
        pre_report, _ = self.compile(pre_market, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(pre_report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertIn("POST_SELL_SESSION_NOT_ELIGIBLE", pre_report["stage2"]["blockers"])

    def test_cli_authority_input_cannot_elevate_blocked_report(self):
        source = evidence(market_phase="PRE_MARKET")
        report, _ = self.compile(source, runtime_advisory_authority="CURRENT_MANUAL_ADVISORY_ELIGIBLE")
        self.assertEqual(report["authority"]["current_runtime_advisory_authority"], "NOT_VERIFIED_BY_RUNTIME")
        self.assertEqual(report["authority"]["runtime_authority_cli_input_effect"], "DISPLAY_ONLY_NO_AUTHORITY_EFFECT")

    def test_json_markdown_html_parity_for_buys_events_and_requests(self):
        report, _ = self.compile(
            post_sell_evidence(), post_sell_plan(), compile_mode="POST_SELL_RECOMPILE",
            event_context={"current_high_count": 2, "new_high_count": 1, "affected_tickers": ["MVLL"]},
        )
        markdown = render_markdown(report)
        dashboard_html = render_html(report)
        self.assertTrue(report["stage2"]["buy_advisories"])
        for row in report["stage2"]["buy_advisories"]:
            for token in (row["ticker"], str(row["calculated_buy_shares"])):
                self.assertIn(token, markdown)
                self.assertIn(token, dashboard_html)
        for token in ("Event context", "MVLL", "요청 회계 상태", "account_holdings_read", "현재 세션 확인 결과", "현재 자료 상태"):
            self.assertIn(token, markdown)
            self.assertIn(token, dashboard_html)

    def test_verified_request_accounting_plain_language_has_html_markdown_parity(self):
        source = evidence()
        report, _ = self.compile(source, request_accounting=verified_request_accounting(source))
        for rendered in (render_markdown(report), render_html(report)):
            self.assertIn("요청 회계 상태: 검증됨 (VERIFIED)", rendered)
            self.assertIn("원본 해시에 정확히 결속", rendered)
            self.assertIn("현재 세션 확인 자료", rendered)

    def test_renderers_do_not_mutate_semantics_or_authority(self):
        report, _ = self.compile(post_sell_evidence(), post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        before = copy.deepcopy(report)
        render_markdown(report)
        render_html(report)
        self.assertEqual(report, before)
        self.assertEqual(report["stage1"]["status"], before["stage1"]["status"])
        self.assertEqual(report["stage2"]["status"], before["stage2"]["status"])
        self.assertEqual(report["stage2"]["buy_advisories"], before["stage2"]["buy_advisories"])
        self.assertFalse(report["authority"]["broker_order_authority"])
        self.assertIsNone(report["authority"]["execution_quantity"])
        self.assertFalse(report["authority"]["automatic_order"])

    def test_schema_valid_but_unverified_and_preflight_fail_block_stage1(self):
        unverified = evidence()
        unverified["evidence_grade"] = "UNVERIFIED"
        unverified["manual_data_verification_status"] = "NOT_VERIFIED"
        unverified["provenance"]["evidence_grade"] = "UNVERIFIED"
        unverified["provenance"]["decision_quality_eligible"] = False
        self.assertEqual(validate_instance(unverified, MANUAL_EVIDENCE_SCHEMA), [])
        unverified_report, _ = self.compile(unverified)
        self.assertNotEqual(unverified_report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        failed = evidence()
        failed["preflight_status"] = "FAIL"
        failed_report, _ = self.compile(failed)
        self.assertNotEqual(failed_report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def test_plan_later_than_evidence_blocks_current_final(self):
        value = plan()
        value["as_of"] = "2026-08-21T22:00:01+00:00"
        report, _ = self.compile(plan_value=value)
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertIn("PLAN_AS_OF_AFTER_BOUND_EVIDENCE", report["evidence"]["canonical_gate_blockers"])

    def test_stage2_unverified_and_preflight_fail_are_blocked(self):
        value = post_sell_plan()
        unverified = post_sell_evidence()
        unverified["evidence_grade"] = "UNVERIFIED"
        unverified["manual_data_verification_status"] = "NOT_VERIFIED"
        unverified["provenance"]["evidence_grade"] = "UNVERIFIED"
        unverified["provenance"]["decision_quality_eligible"] = False
        report, _ = self.compile(unverified, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        failed = post_sell_evidence()
        failed["preflight_status"] = "FAIL"
        report, _ = self.compile(failed, value, compile_mode="POST_SELL_RECOMPILE")
        self.assertNotEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def test_decimal_floor_just_below_integer_boundary(self):
        source = evidence(cash=1290.49, holdings={"PGR": 0})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 0.89
        value = {
            "plan_id": "decimal-below", "as_of": source["decision_as_of"], "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 98.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 2.0,
                           "rationale": "below boundary", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertEqual(row["target_shares_reference"]["value"], 28)

    def test_position_targets_plus_cash_over_100_rejected(self):
        value = plan()
        value["cash_target_pct"] = 70.0
        self.assertTrue(any("TARGET_ALLOCATION_EXCEEDS_100_PERCENT" in item for item in validate_plan(value)))

    def test_current_hard_cap_prevents_deadband(self):
        source = evidence(cash=840.0, holdings={"PGR": 160})
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = 1.0
        value = {
            "plan_id": "current-hard-cap", "as_of": source["decision_as_of"], "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"], "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 85.5,
            "positions": [{"ticker": "PGR", "action": "TRIM", "target_weight_pct": 14.5,
                           "rationale": "current cap", "investment_horizon": "long", "target_status": "APPROVED"}],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "PGR")
        self.assertEqual(row["deadband_status"], "NOT_APPLIED")
        self.assertNotEqual(row["share_delta"]["value"], 0)

    def test_complete_priority_is_deterministic_without_ticker_fallback(self):
        first_source = post_sell_evidence(cash=250.0)
        second_source = post_sell_evidence(cash=250.0)
        for source in (first_source, second_source):
            next(item for item in source["broker_observed_state"]["holdings"] if item["ticker"] == "NBIS")["held_quantity"] = 100
        first_plan = post_sell_plan()
        first_plan["buy_priority"] = ["PGR", "JPM"]
        first, _ = self.compile(first_source, first_plan, compile_mode="POST_SELL_RECOMPILE")
        second_plan = post_sell_plan()
        second_plan["buy_priority"] = ["JPM", "PGR"]
        second, _ = self.compile(second_source, second_plan, compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual([row["ticker"] for row in first["stage2"]["buy_advisories"]], ["PGR", "JPM"])
        self.assertEqual([row["ticker"] for row in second["stage2"]["buy_advisories"]], ["JPM", "PGR"])

    def test_request_accounting_absent_and_arbitrary_shape_are_not_verified(self):
        absent = evidence()
        del absent["broker_observed_state"]["operation_statuses"]
        absent_report, _ = self.compile(absent)
        self.assertEqual(absent_report["evidence"]["request_accounting_status"], "ABSENT")
        invalid = evidence()
        invalid["broker_observed_state"]["operation_statuses"] = ["arbitrary"]
        invalid_report, _ = self.compile(invalid)
        self.assertEqual(invalid_report["evidence"]["request_accounting_status"], "PRESENT_INVALID")
        self.assertNotIn("VERIFIED", invalid_report["evidence"]["request_accounting_status"])

    def test_old_evidence_cannot_use_later_current_context(self):
        old = evidence()
        later = post_sell_evidence()
        later_hash = hashlib.sha256(evidence_raw_bytes(later)).hexdigest()
        report, _ = self.compile(old, current_session_context=current_context(later, later_hash))
        self.assertEqual(report["stage1"]["status"], "READY_FOR_DECISION_PLAN_PREPARATION")
        self.assertIn("CURRENT_CONTEXT_RUN_ID_MISMATCH", report["current_context"]["blockers"])

    def test_bound_old_context_cannot_pass_a_later_canonical_session(self):
        source = evidence()

        def later_session(*_args, **_kwargs):
            return SimpleNamespace(
                authority_status="VERIFIED",
                expected_completed_session=SimpleNamespace(session_date="2026-08-24"),
                market_phase=source["session_authority_market_phase"],
                calendar_policy_identity=source["calendar_policy_identity"],
                calendar_hash=source["calendar_hash"],
                activation_cohort_id=source["session_activation_cohort_id"],
            )

        report, _ = self.compile(source, current_session_authority_resolver=later_session)
        self.assertEqual(report["stage1"]["status"], "READY_FOR_DECISION_PLAN_PREPARATION")
        self.assertIn("CURRENT_CONTEXT_NOT_CURRENT_CANONICAL_SESSION", report["current_context"]["blockers"])

    def test_missing_current_context_allows_only_plan_preparation(self):
        report, _ = self.compile(current_session_context=None)
        self.assertEqual(report["stage1"]["status"], "READY_FOR_DECISION_PLAN_PREPARATION")
        self.assertEqual(report["current_context"]["status"], "ABSENT")
        self.assertTrue(report["authority"]["ready_for_decision_plan_preparation"])
        self.assertEqual(report["authority"]["current_runtime_advisory_authority"], "NOT_VERIFIED_BY_RUNTIME")
        self.assert_display_line(
            report, "현재 자료 상태", "현재 자료 여부 확인 불가 (CURRENT_SESSION_CONTEXT_NOT_VERIFIED)",
        )
        self.assert_display_line(report, "현재 세션 확인 결과", "확인되지 않음 (ABSENT)")

    def test_current_context_run_mismatch_blocks_final(self):
        source = evidence()
        context = current_context(source)
        context["expected_evidence_run_id"] = "manual-other-grade-b"
        report, _ = self.compile(source, current_session_context=context)
        self.assertIn("CURRENT_CONTEXT_RUN_ID_MISMATCH", report["current_context"]["blockers"])
        self.assertNotEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def test_current_context_sha_mismatch_blocks_final(self):
        source = evidence()
        context = current_context(source)
        context["expected_evidence_sha256"] = "0" * 64
        report, _ = self.compile(source, current_session_context=context)
        self.assertIn("CURRENT_CONTEXT_EVIDENCE_SHA256_MISMATCH", report["current_context"]["blockers"])

    def test_current_context_decision_as_of_mismatch_blocks_final(self):
        source = evidence()
        context = current_context(source)
        context["expected_evidence_decision_as_of"] = "2026-08-21T22:00:01+00:00"
        report, _ = self.compile(source, current_session_context=context)
        self.assertIn("CURRENT_CONTEXT_DECISION_AS_OF_MISMATCH", report["current_context"]["blockers"])

    def test_matching_current_context_allows_other_stage1_gates(self):
        report, validation = self.compile()
        self.assertEqual(report["current_context"]["status"], "VERIFIED")
        self.assertEqual(report["stage1"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")
        self.assertTrue(validation["invariants"]["current_session_context_gate_enforced"])
        self.assert_display_line(report, "현재 자료 상태", "현재 자료 (CURRENT_SESSION_CONTEXT_VERIFIED)")
        self.assert_display_line(report, "현재 세션 확인 결과", "확인됨 (VERIFIED)")

    def test_stage2_context_bound_to_prior_run_is_blocked(self):
        source = post_sell_evidence()
        prior = evidence()
        prior_hash = hashlib.sha256(evidence_raw_bytes(prior)).hexdigest()
        report, _ = self.compile(
            source, post_sell_plan(), compile_mode="POST_SELL_RECOMPILE",
            current_session_context=current_context(prior, prior_hash),
        )
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertIn("CURRENT_CONTEXT_RUN_ID_MISMATCH", report["stage2"]["blockers"])

    def test_stage2_matching_post_sell_context_passes_currentness(self):
        report, _ = self.compile(post_sell_evidence(), post_sell_plan(), compile_mode="POST_SELL_RECOMPILE")
        self.assertEqual(report["current_context"]["status"], "VERIFIED")
        self.assertEqual(report["stage2"]["status"], "FINAL_MANUAL_ADVISORY_ELIGIBLE")

    def _decimal_portfolio_case(self, pgr_price: float) -> tuple[dict, dict]:
        source = evidence(cash=0.01, holdings={"PGR": 1, "JPM": 1, "SOXL": 0})
        exact_prices = {"PGR": pgr_price, "JPM": 1289.37, "SOXL": 0.89}
        source["last_verified_finalized_bars"] = [
            item for item in source["last_verified_finalized_bars"] if item["ticker"] in exact_prices
        ]
        for item in source["last_verified_finalized_bars"]:
            item["bar"]["price"] = exact_prices[item["ticker"]]
        value = {
            "plan_id": "exact-decimal", "as_of": source["decision_as_of"],
            "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": source["manual_run_id"],
                                 "expected_decision_as_of": source["decision_as_of"]},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 98.0,
            "positions": [
                {"ticker": "PGR", "action": "HOLD", "target_weight_pct": 0.0,
                 "rationale": "NAV component A", "investment_horizon": "test", "target_status": "APPROVED"},
                {"ticker": "JPM", "action": "HOLD", "target_weight_pct": 0.0,
                 "rationale": "NAV component B", "investment_horizon": "test", "target_status": "APPROVED"},
                {"ticker": "SOXL", "action": "ADD", "target_weight_pct": 2.0,
                 "rationale": "exact target", "investment_horizon": "test", "target_status": "APPROVED"},
            ],
            "material_unknowns": [], "decision_change_triggers": [],
        }
        return source, value

    def test_decimal_nav_is_exact_before_serialization(self):
        source, value = self._decimal_portfolio_case(1.12)
        report, _ = self.compile(source, value)
        self.assertEqual(report["portfolio"]["nav_usd"]["value"], 1290.5)

    def test_decimal_multi_position_values_recompute_to_exact_nav(self):
        source, value = self._decimal_portfolio_case(1.12)
        report, _ = self.compile(source, value)
        values = {row["ticker"]: row["current_market_value_usd"]["value"] for row in report["portfolio"]["positions"]}
        self.assertEqual(values["PGR"], 1.12)
        self.assertEqual(values["JPM"], 1289.37)
        recomputed = Decimal("0.01") + Decimal(str(values["PGR"])) + Decimal(str(values["JPM"]))
        self.assertEqual(recomputed, Decimal(str(report["portfolio"]["nav_usd"]["value"])))

    def test_decimal_exact_target_yields_29_shares(self):
        source, value = self._decimal_portfolio_case(1.12)
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "SOXL")
        self.assertEqual(row["target_shares_reference"]["value"], 29)

    def test_decimal_just_below_target_yields_28_shares(self):
        source, value = self._decimal_portfolio_case(1.11)
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "SOXL")
        self.assertEqual(report["portfolio"]["nav_usd"]["value"], 1290.49)
        self.assertEqual(row["target_shares_reference"]["value"], 28)

    def test_decimal_exact_whole_share_boundary_is_not_underallocated(self):
        source, value = self._decimal_portfolio_case(1.12)
        value["positions"][2]["target_weight_pct"] = 2
        report, _ = self.compile(source, value)
        row = next(item for item in report["portfolio"]["positions"] if item["ticker"] == "SOXL")
        self.assertEqual(row["target_shares_reference"]["value"], 29)

    def test_decimal_cash_bound_has_no_epsilon_overspend(self):
        source = post_sell_evidence(cash=100.89)
        source["broker_observed_state"]["holdings"] = [
            {"ticker": "PGR", "held_quantity": 0, "average_cost": 0.0}
        ]
        source["verified_orderable_cash_usd"] = 0.89
        source["last_verified_finalized_bars"] = [
            item for item in source["last_verified_finalized_bars"] if item["ticker"] == "PGR"
        ]
        source["last_verified_finalized_bars"][0]["bar"]["price"] = 0.89
        value = {
            "plan_id": "cash-bound", "as_of": "2026-08-21T22:00:00+00:00",
            "plan_status": "CURRENT_APPROVED",
            "evidence_binding": {"expected_run_id": "manual-synthetic-grade-b",
                                 "expected_decision_as_of": "2026-08-21T22:00:00+00:00"},
            "post_sell_refresh": {"prior_run_id": "manual-synthetic-grade-b",
                                  "prior_decision_as_of": "2026-08-21T22:00:00+00:00"},
            "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET", "cash_target_pct": 90.0,
            "positions": [{"ticker": "PGR", "action": "ADD", "target_weight_pct": 10.0,
                           "rationale": "cash boundary", "investment_horizon": "test", "target_status": "APPROVED"}],
            "buy_priority": ["PGR"], "material_unknowns": [], "decision_change_triggers": [],
        }
        original_policy = self.policy
        self.policy = copy.deepcopy(self.policy)
        self.policy["cash"]["hard_floor_pct"] = 0
        try:
            exact, _ = self.compile(source, value, compile_mode="POST_SELL_RECOMPILE")
            self.assertEqual(exact["stage2"]["buy_advisories"][0]["calculated_buy_shares"], 1)
            self.assertEqual(exact["cash_semantics"]["post_initial_buy_estimated_cash_usd"]["value"], 0)
            source["verified_orderable_cash_usd"] = 0.8899999999999999
            below, _ = self.compile(source, value, compile_mode="POST_SELL_RECOMPILE")
            self.assertEqual(below["stage2"]["buy_advisories"][0]["calculated_buy_shares"], 0)
            self.assertGreaterEqual(below["cash_semantics"]["post_initial_buy_estimated_cash_usd"]["value"], 0)
        finally:
            self.policy = original_policy

    def test_request_accounting_verified_state_is_reachable(self):
        source = evidence()
        verified = verified_request_accounting(source)
        report, _ = self.compile(source, request_accounting=verified)
        self.assertEqual(report["evidence"]["request_accounting_status"], "VERIFIED")
        self.assert_display_line(report, "요청 회계 상태", "검증됨 (VERIFIED)")

    def test_request_accounting_present_unverified_state_is_reachable(self):
        source = evidence()
        unverified = verified_request_accounting(source)
        unverified["verification_status"] = "UNVERIFIED"
        report, _ = self.compile(source, request_accounting=unverified)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")
        self.assert_display_line(report, "요청 회계 상태", "미검증 (PRESENT_UNVERIFIED)")

    def test_request_accounting_present_invalid_state_is_reachable(self):
        report, _ = self.compile(request_accounting={"arbitrary": True})
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_INVALID")
        self.assert_display_line(report, "요청 회계 상태", "형식 오류 (PRESENT_INVALID)")

    def test_request_accounting_absent_state_is_reachable(self):
        source = evidence()
        del source["broker_observed_state"]["operation_statuses"]
        report, _ = self.compile(source, request_accounting=None)
        self.assertEqual(report["evidence"]["request_accounting_status"], "ABSENT")
        self.assert_display_line(report, "요청 회계 상태", "없음 (ABSENT)")

    def test_request_accounting_run_mismatch_is_unverified(self):
        source = evidence()
        wrong_run = verified_request_accounting(source)
        wrong_run["source_run_id"] = "manual-other-grade-b"
        report, _ = self.compile(source, request_accounting=wrong_run)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")
        self.assertIn("REQUEST_ACCOUNTING_RUN_ID_MISMATCH", report["evidence"]["request_accounting_issues"])

    def test_request_accounting_hash_mismatch_is_unverified(self):
        source = evidence()
        wrong_hash = verified_request_accounting(source)
        wrong_hash["source_artifact_sha256"] = "0" * 64
        report, _ = self.compile(source, request_accounting=wrong_hash)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_UNVERIFIED")
        self.assertIn("REQUEST_ACCOUNTING_SOURCE_SHA256_MISMATCH", report["evidence"]["request_accounting_issues"])

    def test_request_accounting_negative_counter_is_invalid(self):
        source = evidence()
        negative = verified_request_accounting(source)
        negative["retry_count"] = -1
        report, _ = self.compile(source, request_accounting=negative)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_INVALID")

    def test_request_accounting_consistency_violation_is_invalid(self):
        source = evidence()
        inconsistent = verified_request_accounting(source)
        inconsistent["successful_request_count"] = 4
        report, _ = self.compile(source, request_accounting=inconsistent)
        self.assertEqual(report["evidence"]["request_accounting_status"], "PRESENT_INVALID")
        self.assertIn("REQUEST_ACCOUNTING_RESULT_TOTAL_MISMATCH", report["evidence"]["request_accounting_issues"])

    def test_verified_request_accounting_never_changes_authority(self):
        source = evidence()
        report, _ = self.compile(source, request_accounting=verified_request_accounting(source))
        self.assertEqual(report["evidence"]["request_accounting_status"], "VERIFIED")
        self.assertFalse(report["authority"]["broker_order_authority"])
        self.assertIsNone(report["authority"]["execution_quantity"])
        self.assertFalse(report["authority"]["automatic_order"])

    def test_event_asset_review_required_is_visible_without_target_change(self):
        report, _ = self.compile(event_context={
            "status": "ASSET_REVIEW_REQUIRED", "current_high_count": 2,
            "new_high_count": 0, "affected_tickers": ["MVLL", "NBIS"],
        })
        self.assertFalse(report["event_context"]["automatic_target_change"])
        for rendered in (render_markdown(report), render_html(report)):
            self.assertIn("ASSET_REVIEW_REQUIRED", rendered)
            self.assertIn("MVLL", rendered)
            self.assertIn("NBIS", rendered)

    def test_historical_replay_cannot_be_forced_current_by_cli(self):
        report, _ = self.compile(
            plan_value=plan(status="HISTORICAL"), compile_mode="HISTORICAL_REPLAY",
            runtime_advisory_authority="CURRENT_MANUAL_ADVISORY_ELIGIBLE",
        )
        self.assertEqual(report["stage1"]["status"], "REPLAY_ONLY")
        self.assertEqual(report["authority"]["current_runtime_advisory_authority"], "NOT_VERIFIED_BY_RUNTIME")

    def test_validation_common_is_in_implementation_provenance(self):
        paths = implementation_provenance_paths(DEFAULT_RISK_POLICY)
        self.assertIn(SCRIPTS / "validation_common.py", paths)
        self.assertIn(SCRIPTS / "session_authority.py", paths)
        self.assertIn(SCRIPTS / "session_calendar_artifact.py", paths)
        self.assertIn(CURRENT_SESSION_CONTEXT_SCHEMA, paths)
        self.assertIn(REQUEST_ACCOUNTING_SCHEMA, paths)
        report, validation = self.compile()
        with tempfile.TemporaryDirectory(dir=ROOT / "manage-us-stock-strategy/tests") as temp:
            consumed = {"risk_policy": hashlib.sha256(DEFAULT_RISK_POLICY.read_bytes()).hexdigest()}
            run_dir = write_run(
                report, validation, output_root=Path(temp), root=ROOT,
                source_paths={"portfolio_evidence": None, "decision_plan": None},
                implementation_paths=paths, consumed_hashes=consumed,
            )
            manifest = load_json(run_dir / "run-manifest.json")
            self.assertIn("manage-us-stock-strategy/scripts/validation_common.py", manifest["implementation_hashes"])
            self.assertEqual(manifest["consumed_hashes"], consumed)

    def test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan(self):
        fixture = ROOT / "workspace/outputs/manual-portfolio-analysis/manual-20260829T153208101909Z-c32341e4e7f3/manual-portfolio-analysis.json"
        self.assertTrue(fixture.is_file())
        historical = load_json(fixture)
        self.assertEqual(historical["schema_version"], "2.0")
        self.assertEqual(
            validate_instance(
                historical,
                MANUAL_EVIDENCE_SCHEMA,
                schema_bytes=manual_evidence_schema_bytes(
                    historical, allow_legacy_replay=True,
                ),
            ),
            [],
        )
        discovery = discover_historical_replay(ROOT)
        self.assertEqual(discovery["status"], "BLOCKED_HISTORICAL_DECISION_PLAN_NOT_FOUND")
        self.assertFalse(discovery["current_advisory_created"])

    def test_create_only_collision(self):
        report, validation = self.compile()
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            implementation = temp_root / "implementation.py"
            implementation.write_text("# synthetic\n", encoding="utf-8")
            output = temp_root / "outputs"
            run_dir = write_run(report, validation, output_root=output, root=temp_root,
                                source_paths={"portfolio_evidence": None, "decision_plan": None},
                                implementation_paths=[implementation])
            manifest = json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))
            for name, expected in manifest["artifact_hashes"].items():
                self.assertEqual(hashlib.sha256((run_dir / name).read_bytes()).hexdigest(), expected)
            self.assertTrue(manifest["create_only"])
            with self.assertRaises(FileExistsError):
                write_run(report, validation, output_root=output, root=temp_root,
                          source_paths={"portfolio_evidence": None, "decision_plan": None},
                          implementation_paths=[implementation])

    def test_replay_discovery_requires_real_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema_target = root / MANUAL_EVIDENCE_SCHEMA.relative_to(ROOT)
            schema_target.parent.mkdir(parents=True)
            schema_target.write_bytes(MANUAL_EVIDENCE_SCHEMA.read_bytes())
            fixture_dir = root / "workspace/outputs/manual-portfolio-analysis/run-1"
            fixture_dir.mkdir(parents=True)
            (fixture_dir / "manual-portfolio-analysis.json").write_text(
                json.dumps(evidence()), encoding="utf-8",
            )
            result = discover_historical_replay(root)
            self.assertEqual(result["status"], "BLOCKED_HISTORICAL_DECISION_PLAN_NOT_FOUND")
            self.assertFalse(result["current_advisory_created"])


class IdentityK3RiskInputTests(unittest.TestCase):
    def setUp(self):
        self.risk = load_json(DEFAULT_RISK_POLICY)
        self.registry = load_json(ROOT / "workspace/policies/instrument_registry.json")

    def test_all_existing_classification_precedence_branches(self):
        mapping, issue = dashboard._instrument_mapping("LMT", self.risk, self.registry)
        self.assertIsNone(issue)
        self.assertEqual((mapping["instrument_class"], mapping["mapping_source"]),
                         ("NORMAL_STOCK", "INSTRUMENT_REGISTRY"))
        for ticker in ("PGR", "JPM", "CME", "V"):
            with self.subTest(ticker=ticker):
                self.assertNotIn(ticker, self.registry["instruments"])
                mapping, issue = dashboard._instrument_mapping(ticker, self.risk, self.registry)
                self.assertIsNone(issue)
                self.assertEqual(mapping["mapping_source"], "USER_APPROVED_FALLBACK")
                self.assertEqual(mapping["instrument_class"], "NORMAL_STOCK")
        self.assertEqual(dashboard._instrument_mapping("ZZZZ", self.risk, self.registry),
                         (None, "RISK_MAPPING_REQUIRED"))
        for ticker, klass, factor in (("MVLL", "SINGLE_2X_SINGLE_STOCK_ETF", 2),
                                     ("SOXL", "SINGLE_3X_ETF", 3)):
            with self.subTest(ticker=ticker):
                mapping, issue = dashboard._instrument_mapping(ticker, self.risk, self.registry)
                self.assertIsNone(issue)
                self.assertEqual((mapping["instrument_class"], mapping["leverage_factor"], mapping["mapping_source"]),
                                 (klass, Decimal(factor), "INSTRUMENT_REGISTRY_CONFIRMED"))
                conflict = copy.deepcopy(self.registry)
                conflict["instruments"][ticker]["leverage_factor"] = 1
                self.assertEqual(dashboard._instrument_mapping(ticker, self.risk, conflict),
                                 (None, "RISK_MAPPING_CONFLICT"))

    def test_detailed_leveraged_classes_retain_position_caps(self):
        for ticker, rule in (("MVLL", "single_2x_single_stock_etf"), ("SOXL", "single_3x_etf")):
            with self.subTest(ticker=ticker):
                mapping, _ = dashboard._instrument_mapping(ticker, self.risk, self.registry)
                cap = Decimal(str(self.risk[rule]["hard_cap_pct"]))
                at_cap = dashboard.calculate_risk_metrics({ticker: cap}, Decimal(80), {ticker: mapping}, self.risk)
                over_cap = dashboard.calculate_risk_metrics({ticker: cap + Decimal("0.01")}, Decimal(80),
                                                           {ticker: mapping}, self.risk)
                self.assertNotIn("POSITION_PCT:" + ticker, at_cap["hard_cap_violations"])
                self.assertIn("POSITION_PCT:" + ticker, over_cap["hard_cap_violations"])

    def test_canonical_input_paths_and_actual_consumed_hashes(self):
        registry_path = ROOT / "workspace/policies/instrument_registry.json"
        real_read = Path.read_bytes
        reads = []
        def read(path):
            reads.append(path)
            return real_read(path)
        with patch.object(Path, "read_bytes", read):
            registry, policy, hashes = dashboard._load_risk_registry_inputs(registry_path)
        self.assertEqual(reads, [registry_path.resolve(), dashboard.DEFAULT_ALERT_POLICY])
        self.assertEqual(registry, self.registry)
        self.assertEqual(hashes["instrument_registry"], hashlib.sha256(real_read(registry_path)).hexdigest())
        self.assertEqual(hashes["alert_policy"], hashlib.sha256(real_read(dashboard.DEFAULT_ALERT_POLICY)).hexdigest())
        from validate_registry_consistency import validate_registry_consistency
        self.assertEqual(validate_registry_consistency(registry, policy, registry_path)["status"], "VALIDATED")
        with tempfile.TemporaryDirectory() as temp:
            arbitrary = Path(temp) / "instrument_registry.json"
            arbitrary.write_bytes(real_read(registry_path))
            with self.assertRaisesRegex(ContractError, "POLICY_REGISTRY_MISMATCH"):
                dashboard._load_risk_registry_inputs(arbitrary)

    def test_missing_invalid_registry_or_policy_bytes_fail_closed(self):
        registry_path = ROOT / "workspace/policies/instrument_registry.json"
        real_read = Path.read_bytes
        for target in (registry_path.resolve(), dashboard.DEFAULT_ALERT_POLICY):
            for value in (None, b"INVALID JSON", b"[]"):
                with self.subTest(target=target.name, value=value):
                    def read(path):
                        if path == target:
                            if value is None:
                                raise FileNotFoundError(path)
                            return value
                        return real_read(path)
                    with patch.object(Path, "read_bytes", read), \
                         self.assertRaisesRegex(ContractError, "POLICY_REGISTRY_MISMATCH"):
                        dashboard._load_risk_registry_inputs(registry_path)

    def test_writer_uses_consumed_registry_and_policy_hashes_after_swap(self):
        from test_portfolio_decision_order_intent import OrderIntentOnlyTests, source_for_buy, buy_plan
        case = OrderIntentOnlyTests()
        case.setUp()
        source, decision_plan = source_for_buy(), buy_plan()
        report, validation = case.compile_dashboard(source, decision_plan)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {name: root / (name + ".json") for name in ("instrument_registry", "alert_policy")}
            consumed = {}
            for name, target in paths.items():
                payload = evidence_raw_bytes(self.registry if name == "instrument_registry" else case.alert_policy)
                target.write_bytes(payload)
                consumed[name] = hashlib.sha256(payload).hexdigest()
                target.write_bytes(b"SWAPPED AFTER CONSUMPTION")
            with patch.object(dashboard, "file_hash", side_effect=AssertionError("Consumed input reopened")):
                out = write_run(report, validation, output_root=root / "runs", root=root,
                                source_paths=paths, implementation_paths=[], consumed_hashes=consumed)
            manifest = load_json(out / "run-manifest.json")
            self.assertEqual(manifest["consumed_hashes"], consumed)
            for name in paths:
                self.assertEqual(manifest["source_artifacts"][name]["sha256"], consumed[name])
                self.assertNotEqual(hashlib.sha256(paths[name].read_bytes()).hexdigest(), consumed[name])


class ManualRuleCallerBindingTests(unittest.TestCase):
    def test_cli_passes_existing_current_context_to_intent_compiler(self):
        import portfolio_decision_order_intent as intent
        from test_portfolio_decision_order_intent import ManualSellRuleTests, REGISTRY_PATH

        case = ManualSellRuleTests()
        case.setUp()
        real_dashboard = dashboard.compile_dashboard
        real_intent = intent.compile_order_intent_artifact
        for supplied in (True, False):
            with self.subTest(supplied=supplied), tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
                args, authority = case.inputs()
                root = Path(temp)
                evidence_path, plan_path, context_path = (root / name for name in (
                    "evidence.json", "plan.json", "context.json"))
                evidence_path.write_bytes(dashboard._json_bytes(args["evidence"]))
                plan_path.write_bytes(dashboard._json_bytes(args["plan"]))
                context_path.write_bytes(dashboard._json_bytes(args["current_session_context"]))
                stack.enter_context(patch.object(dashboard, "_now", return_value=args["now"]))
                # Preserve the approved synthetic READY seam; real combined binding is tested below.
                stack.enter_context(patch.object(dashboard, "load_production_integrated_authority_snapshot",
                                                 return_value=args["integrated_snapshot"]))
                stack.enter_context(patch.object(dashboard, "derive_us_market_session_authority_from_snapshot",
                                                 side_effect=lambda *a, **k: authority))
                stack.enter_context(patch.object(dashboard, "compile_dashboard", wraps=real_dashboard))
                compiler = stack.enter_context(patch.object(intent, "compile_order_intent_artifact",
                    wraps=real_intent))
                writer = stack.enter_context(patch.object(dashboard, "write_run", return_value=root / "test-run"))
                network = stack.enter_context(patch("socket.socket.connect",
                    side_effect=AssertionError("Network forbidden")))
                stack.enter_context(patch.object(sys, "argv", [
                    "portfolio_decision_dashboard.py", "--portfolio-evidence", str(evidence_path),
                    "--decision-plan", str(plan_path), "--instrument-registry", str(REGISTRY_PATH),
                    "--output-root", str(root / "test-output"), "--run-id", "manual-rule-cli-test",
                    *(["--current-session-context", str(context_path)] if supplied else []),
                ]))
                stack.enter_context(redirect_stdout(StringIO()))
                dashboard.main()
                compiler.assert_called_once()
                self.assertEqual(compiler.call_args.kwargs["current_session_context"],
                                 args["current_session_context"] if supplied else None)
                row = writer.call_args.kwargs["order_intent_artifact"]["instructions"][0]
                self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY" if supplied else "ORDER_BLOCKED")
                self.assertIsNone(row["limit_price"])
                self.assertIsNone(row["estimated_order_value"])
                network.assert_not_called()
                self.assertFalse((root / "test-output").exists())


def session_k3_inputs(root, now="2026-09-02T14:00:00+00:00"):
    """Offline copied authority fixture with independently valid Identity and Risk."""
    import integrated_authority_snapshot as integrated
    from test_integrated_authority_snapshot import _copy_artifacts, _active_manifest
    from test_portfolio_decision_order_intent import ManualSellRuleTests

    _copy_artifacts(root)
    manifest_path = root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(evidence_raw_bytes(_active_manifest(root)))
    legacy = root / "workspace/policies/session_calendar_activation.json"
    legacy.write_text("CORRUPT STALE LEGACY FIXTURE", encoding="utf-8")
    snapshot = integrated.load_production_integrated_authority_snapshot(
        trusted_root=root, decision_as_of=now, resolved_at=now, run_id="session-k3-evidence",
    )
    case = ManualSellRuleTests()
    case.setUp()
    args, _ = case.inputs(now=now, opened=now[:10] + "T13:30:00+00:00",
                          closed=now[:10] + "T20:00:00+00:00")
    source = args["evidence"]
    authority = integrated.derive_us_market_session_authority_from_snapshot(
        snapshot, now, primary_listing_operating_mic="XNAS", decision_as_of=now,
    )
    session = authority.expected_completed_session.session_date
    source.update(
        manual_run_id="session-k3-evidence", expected_completed_us_session=session,
        identity_registry_version=snapshot.identity.artifact["registry_version"],
        identity_registry_hash=snapshot.identity.registry_hash,
        identity_activation_cohort_id=snapshot.activation_cohort_id,
        calendar_policy_identity=authority.calendar_policy_identity,
        calendar_hash=snapshot.session.calendar_hash,
        session_activation_cohort_id=snapshot.activation_cohort_id,
        session_authority_market_phase=authority.market_phase,
        integrated_authority_snapshot_provenance=snapshot.provenance(
            authority_source="K3_COMBINED_PRODUCTION"),
    )
    for bar in source["last_verified_finalized_bars"]:
        bar["bar_date"] = session
        bar["bar"]["reported_session"] = session
    args["plan"]["evidence_binding"].update(
        expected_run_id=source["manual_run_id"], expected_decision_as_of=now,
    )
    args["current_session_context"] = current_context(source)
    args["input_hashes"]["portfolio_evidence"] = hashlib.sha256(evidence_raw_bytes(source)).hexdigest()
    args["report"], args["validation"] = compile_dashboard(
        source, args["plan"], args["risk_policy"], registry=args["registry"],
        run_id="session-k3-evidence", generated_at=now,
        evidence_sha256=args["input_hashes"]["portfolio_evidence"],
        current_session_context=args["current_session_context"],
        current_session_authority_resolver=lambda *a, **k: authority,
    )
    args["input_hashes"].update(
        portfolio_decision=hashlib.sha256(evidence_raw_bytes(args["report"])).hexdigest(),
        validation_report=hashlib.sha256(evidence_raw_bytes(args["validation"])).hexdigest(),
        decision_plan=hashlib.sha256(evidence_raw_bytes(args["plan"])).hexdigest(),
    )
    return args, snapshot, manifest_path


class SessionK3DashboardBoundaryTests(unittest.TestCase):
    def run_current(self, root, args, *, mutate_context=None, swap=False, mode="INITIAL_COMPILE", scheduled=False):
        import integrated_authority_snapshot as integrated
        import portfolio_decision_order_intent as intent
        import session_authority
        from test_portfolio_decision_order_intent import REGISTRY_PATH

        context = copy.deepcopy(args["current_session_context"])
        if mutate_context is not None:
            context = mutate_context(context)
        paths = {}
        for name, value in (("evidence", args["evidence"]), ("plan", args["plan"]), ("context", context)):
            paths[name] = root / (name + ".json")
            paths[name].write_bytes(evidence_raw_bytes(value))
        read_paths, snapshots = [], []
        real_read = integrated.read_once_no_reparse

        def read(path, trusted_root):
            read_paths.append(Path(path))
            return real_read(path, trusted_root)

        def load(**kwargs):
            kwargs["trusted_root"] = root
            snapshot = integrated.load_production_integrated_authority_snapshot(**kwargs)
            snapshots.append(snapshot)
            if swap:
                (root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH).write_text("SWAPPED INVALID", encoding="utf-8")
            return snapshot

        with ExitStack() as stack:
            stack.enter_context(patch.object(dashboard, "_now", return_value=args["now"]))
            loader = stack.enter_context(patch.object(dashboard, "load_production_integrated_authority_snapshot", side_effect=load))
            stack.enter_context(patch.object(integrated, "read_once_no_reparse", side_effect=read))
            legacy = stack.enter_context(patch.object(session_authority, "load_active_session_calendar",
                                                      side_effect=AssertionError("Legacy read forbidden")))
            intent_load = stack.enter_context(patch.object(intent, "load_production_integrated_authority_snapshot",
                                                           side_effect=AssertionError("Second load forbidden")))
            derive = stack.enter_context(patch.object(dashboard, "derive_us_market_session_authority_from_snapshot",
                                                      wraps=integrated.derive_us_market_session_authority_from_snapshot))
            compiler = stack.enter_context(patch.object(intent, "compile_order_intent_artifact", wraps=intent.compile_order_intent_artifact))
            dashboard_compile = stack.enter_context(patch.object(dashboard, "compile_dashboard", wraps=dashboard.compile_dashboard))
            writer = stack.enter_context(patch.object(dashboard, "write_run", return_value=root / "not-written"))
            network = stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")))
            argv = ["dashboard", "--portfolio-evidence", str(paths["evidence"]), "--decision-plan", str(paths["plan"]),
                    "--instrument-registry", str(REGISTRY_PATH), "--run-id", "session-k3-dashboard", "--mode", mode]
            if scheduled:
                from test_deployment_provenance import fixture_git
                supplied_path = root / "scheduled-provenance.json"
                supplied_path.write_bytes(evidence_raw_bytes(args["scheduled_provenance"]))
                risk_inputs = dashboard._load_risk_registry_inputs(REGISTRY_PATH)
                stack.enter_context(patch.object(dashboard, "_load_risk_registry_inputs", return_value=risk_inputs))
                stack.enter_context(patch.object(dashboard, "ROOT", root))
                stack.enter_context(patch.object(dashboard, "MANUAL_EVIDENCE_SCHEMA", root / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"))
                stack.enter_context(patch("deployment_provenance._git", side_effect=fixture_git))
                stack.enter_context(patch("deployment_provenance.Path.home", return_value=root / "test-home"))
                argv += ["--input-mode", "LIVE_READ_ONLY", "--scheduled-provenance", str(supplied_path),
                         "--expected-runtime-head", "a" * 40]
            if context is not None:
                argv += ["--current-session-context", str(paths["context"])]
            stack.enter_context(patch.object(sys, "argv", argv))
            stack.enter_context(redirect_stdout(StringIO()))
            captured_stderr = stack.enter_context(redirect_stderr(StringIO()))
            exit_code = 0
            try:
                dashboard.main()
            except SystemExit as exc:
                exit_code = exc.code
            legacy.assert_not_called()
            intent_load.assert_not_called()
            network.assert_not_called()
            return SimpleNamespace(exit_code=exit_code, stderr=captured_stderr.getvalue(), reads=read_paths, snapshots=snapshots,
                                   loader=loader, compiler=compiler, dashboard=dashboard_compile,
                                   writer=writer, derive=derive)

    def test_one_snapshot_shared_resolver_zero_legacy_and_activation_swap(self):
        for swap in (False, True):
            with self.subTest(swap=swap), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args, expected, manifest = session_k3_inputs(root)
                before = copy.deepcopy(args)
                observed = self.run_current(root, args, swap=swap)
                self.assertEqual(observed.exit_code, 0)
                observed.loader.assert_called_once()
                self.assertEqual(len(observed.reads), 3, observed.reads)
                self.assertEqual(observed.reads.count(manifest), 1)
                self.assertEqual(sum(p.name.endswith("registry.json") for p in observed.reads), 1)
                self.assertEqual(sum(p.name.endswith("calendar.json") for p in observed.reads), 1)
                resolver = observed.dashboard.call_args.kwargs["current_session_authority_resolver"]
                self.assertIs(resolver, observed.compiler.call_args.kwargs["current_session_authority_resolver"])
                self.assertIs(resolver.args[0], observed.snapshots[0])
                self.assertGreaterEqual(observed.derive.call_count, 2)
                self.assertTrue(all(c.args[0] is observed.snapshots[0] for c in observed.derive.call_args_list))
                self.assertIs(observed.dashboard.call_args.kwargs["current_session_context"],
                              observed.compiler.call_args.kwargs["current_session_context"])
                self.assertTrue(observed.writer.call_args.args[0]["current_context"]["verified"])
                artifact = observed.writer.call_args.kwargs["order_intent_artifact"]
                row = next(r for r in artifact["instructions"] if r["ticker"] == "PGR")
                self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY", row["blockers"])
                self.assertIs(observed.compiler.call_args.kwargs["integrated_snapshot"], observed.snapshots[0])
                self.assertEqual(row["instrument_identity"]["identity_registry_hash"], expected.identity.registry_hash)
                self.assertFalse(any("CURRENT_CONTEXT" in b or "MANUAL_RULE_CORE" in b for b in row["blockers"]))
                hashes = observed.writer.call_args.kwargs["consumed_hashes"]
                self.assertEqual(hashes["alert_policy"], dashboard.file_hash(dashboard.DEFAULT_ALERT_POLICY))
                self.assertEqual(hashes["alert_policy"], artifact["input_hashes"]["alert_policy"])
                self.assertEqual(hashes["combined_activation_manifest_sha256"], expected.combined_activation_manifest_sha256)
                self.assertEqual(hashes["instrument_identity_artifact_sha256"], expected.identity.registry_hash)
                self.assertEqual(hashes["session_calendar_artifact_sha256"], expected.session.calendar_hash)
                self.assertEqual(hashes["integrated_authority_snapshot_provenance"],
                                 observed.compiler.call_args.kwargs["input_hashes"]["integrated_authority_snapshot_provenance"])
                self.assertEqual(args, before)
                self.assertEqual(artifact["submission_status"], "NOT_SUBMITTED")
                self.assertFalse(artifact["order_authority"])
                self.assertIsNone(artifact["execution_quantity"])
                self.assertFalse(artifact["automatic_order"])
                self.assertEqual(artifact["broker_submission"], "DISABLED")
                with self.assertRaises(TypeError):
                    observed.snapshots[0].session.artifact["calendar_version"] = "MUTATION"

    def test_combined_failures_never_fall_back_or_write_current_output(self):
        for failure in ("missing", "invalid", "identity_hash", "session_hash", "manifest_binding", "cohort", "provenance"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args, snapshot, manifest = session_k3_inputs(root)
                if failure == "missing":
                    manifest.unlink()
                elif failure == "invalid":
                    manifest.write_text("{invalid", encoding="utf-8")
                elif failure == "manifest_binding":
                    value = json.loads(manifest.read_bytes())
                    value["session_calendar"]["source_bundle_hash"] = "f" * 64
                    manifest.write_bytes(evidence_raw_bytes(value))
                elif failure in {"identity_hash", "session_hash"}:
                    pattern = "*.registry.json" if failure == "identity_hash" else "*.calendar.json"
                    artifact = next(root.rglob(pattern))
                    artifact.write_bytes(artifact.read_bytes() + b" ")
                else:
                    p = args["evidence"]["integrated_authority_snapshot_provenance"]
                    p["activation_cohort_id" if failure == "cohort" else "combined_activation_manifest_sha256"] = "f" * 64
                observed = self.run_current(root, args)
                self.assertEqual(observed.exit_code, 2)
                observed.loader.assert_called_once()
                observed.compiler.assert_not_called()
                observed.writer.assert_not_called()

    def test_current_context_missing_and_mismatched_fail_closed(self):
        mutations = {"missing": lambda c: None}
        for field, value in (
            ("expected_evidence_run_id", "wrong-run"), ("expected_evidence_sha256", "0" * 64),
            ("expected_evidence_decision_as_of", "2026-09-02T13:59:00+00:00"),
            ("expected_completed_us_session", "2026-08-31"), ("calendar_hash", "0" * 64),
            ("session_activation_cohort_id", "wrong-cohort"),
            ("context_generated_at", "2026-09-02T14:01:00+00:00"),
        ):
            mutations[field] = lambda c, f=field, v=value: dict(c, **{f: v})
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args, _, _ = session_k3_inputs(root)
                observed = self.run_current(root, args, mutate_context=mutate)
                self.assertEqual(observed.exit_code, 0)
                report = observed.writer.call_args.args[0]
                self.assertFalse(report["current_context"]["verified"])
                self.assertNotEqual(observed.writer.call_args.kwargs["order_intent_artifact"]["run_state"], "ORDER_INSTRUCTION_READY")

    def test_snapshot_session_non_core_and_out_of_coverage(self):
        for now in ("2026-09-03T12:00:00+00:00", "2026-09-03T21:00:00+00:00",
                    "2026-09-07T14:00:00+00:00", "2030-09-03T14:00:00+00:00"):
            with self.subTest(now=now), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args, _, _ = session_k3_inputs(root)
                args["now"] = now
                observed = self.run_current(root, args)
                self.assertEqual(observed.exit_code, 0)
                artifact = observed.writer.call_args.kwargs["order_intent_artifact"]
                self.assertNotEqual(artifact["run_state"], "ORDER_INSTRUCTION_READY")
                row = next(r for r in artifact["instructions"] if r["ticker"] == "PGR")
                self.assertEqual(row["state"], "ORDER_EXPIRED")
                self.assertTrue(any("CORE_OPEN" in b or "NOT_VERIFIED" in b for b in row["blockers"]))

    def test_explicit_legacy_replay_and_materialization_do_not_load_combined(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args, _, manifest = session_k3_inputs(root)
            args["evidence"]["schema_version"] = "2.0"
            del args["evidence"]["integrated_authority_snapshot_provenance"]
            args["plan"]["plan_status"] = "HISTORICAL"
            manifest.unlink()
            observed = self.run_current(root, args, mutate_context=lambda c: None, mode="HISTORICAL_REPLAY")
            self.assertEqual(observed.exit_code, 0)
            observed.loader.assert_not_called()
            self.assertEqual(observed.reads, [])
            self.assertNotEqual(observed.writer.call_args.kwargs["order_intent_artifact"]["run_state"], "ORDER_INSTRUCTION_READY")
        with patch.object(dashboard, "load_production_integrated_authority_snapshot",
                          side_effect=AssertionError("Materialization cannot load authority")) as loader:
            DecisionPlanMaterializationTests("test_cli_materialization_only_is_isolated").test_cli_materialization_only_is_isolated()
            loader.assert_not_called()


class DecisionPlanMaterializationTests(unittest.TestCase):
    def test_valid_materialization_is_deterministic_and_does_not_mutate_input(self):
        value = plan(status="PROVISIONAL")
        before = copy.deepcopy(value)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "workspace/outputs/run-1/portfolio-decision-plan.json"
            self.assertEqual(dashboard.validate_plan(value), [])
            self.assertEqual(dashboard.write_decision_plan(value, target, root=root), target.resolve())
            self.assertEqual(json.loads(target.read_bytes()), before)
            self.assertEqual(target.read_bytes(), dashboard._json_bytes(before))
            reordered = dict(reversed(list(value.items())))
            second = target.with_name("second.json")
            dashboard.write_decision_plan(reordered, second, root=root)
            self.assertEqual(target.read_bytes(), second.read_bytes())
        self.assertEqual(value, before)

    def test_invalid_plans_create_no_output(self):
        missing = plan()
        del missing["evidence_binding"]
        duplicate = plan()
        duplicate["positions"].append(copy.deepcopy(duplicate["positions"][0]))
        overallocated = plan()
        overallocated["cash_target_pct"] = 100
        malformed = plan()
        malformed["positions"] = [None]
        for value in (missing, duplicate, overallocated, malformed, [], None):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                target = root / "workspace/outputs/run/portfolio-decision-plan.json"
                with self.assertRaisesRegex(ContractError, "DECISION_PLAN_INVALID"):
                    dashboard.write_decision_plan(value, target, root=root)
                self.assertFalse((root / "workspace").exists())

    def test_collision_preserves_exact_existing_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "workspace/outputs/run/portfolio-decision-plan.json"
            target.parent.mkdir(parents=True)
            original = b"existing artifact\r\n\x00"
            target.write_bytes(original)
            with self.assertRaises(FileExistsError):
                dashboard.write_decision_plan(plan(), target, root=root)
            self.assertEqual(target.read_bytes(), original)

    def test_output_boundary_and_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "repo"
            root.mkdir()
            for target in (
                base / "outside.json",
                root / "stock-strategy-system/portfolio_state.json",
                root / "workspace/outputs-sibling/plan.json",
                root / "workspace/outputs/../plan.json",
                root / "workspace/outputs/run/../plan.json",
            ):
                with self.subTest(target=target):
                    with self.assertRaisesRegex(ContractError, "OUTPUT_"):
                        dashboard.write_decision_plan(plan(), target, root=root)
                    self.assertFalse(target.exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_resolved_output_alias_outside_boundary_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "workspace/outputs/alias/plan.json"
            outside = root / "protected/plan.json"
            # Model the resolved destination of an output symlink/junction.
            with patch.object(Path, "resolve", autospec=True,
                              side_effect=lambda value: outside if value == target else value):
                with self.assertRaisesRegex(ContractError, "OUTPUT_OUTSIDE_APPROVED_OUTPUTS"):
                    dashboard.write_decision_plan(plan(), target, root=root)
            self.assertFalse(outside.exists())
            self.assertFalse((root / "workspace").exists())

    def test_cli_materialization_only_is_isolated(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            value = plan(status="PROVISIONAL")
            source = root / "supplied.json"
            source.write_bytes(dashboard._json_bytes(value))
            output = root / "workspace/outputs/portfolio-decision-dashboard"
            guards = [stack.enter_context(patch.object(dashboard, name)) for name in (
                "compile_dashboard", "write_run", "discover_historical_replay",
                "derive_us_market_session_authority", "_git_commit",
            )]
            intent = SimpleNamespace(compile_order_intent_artifact=Mock(),
                                     write_order_intent_artifact=Mock())
            stack.enter_context(patch.dict(sys.modules, {"portfolio_decision_order_intent": intent}))
            stack.enter_context(patch.object(dashboard.subprocess, "Popen",
                                            side_effect=AssertionError("No external process allowed")))
            stack.enter_context(patch.object(dashboard, "ROOT", root))
            reader = stack.enter_context(patch.object(dashboard, "load_json", wraps=load_json))
            stack.enter_context(patch.object(sys, "argv", [
                "portfolio_decision_dashboard.py", "--materialize-plan-only",
                "--decision-plan", str(source), "--output-root", str(output), "--run-id", "synthetic",
                "--portfolio-evidence", str(root / "must-not-read-evidence.json"),
                "--risk-policy", str(root / "must-not-read-policy.json"),
            ]))
            stack.enter_context(redirect_stdout(StringIO()))
            self.assertEqual(dashboard.main(), 0)
            reader.assert_called_once_with(source)
            for guard in guards:
                guard.assert_not_called()
            intent.compile_order_intent_artifact.assert_not_called()
            intent.write_order_intent_artifact.assert_not_called()
            target = output / "synthetic/portfolio-decision-plan.json"
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertEqual(sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()),
                             ["supplied.json", "workspace/outputs/portfolio-decision-dashboard/synthetic/portfolio-decision-plan.json"])

    def test_cli_requires_explicit_input_and_safe_run_id(self):
        cases = [[], ["--decision-plan", "unused.json"], ["--run-id", "run"],
                 ["--decision-plan", "unused.json", "--run-id", "../escape"],
                 ["--decision-plan", "unused.json", "--run-id", "C:\\escape"],
                 ["--discover-historical-replay"]]
        for arguments in cases:
            with self.subTest(arguments=arguments), patch.object(sys, "argv", [
                "portfolio_decision_dashboard.py", "--materialize-plan-only", *arguments,
            ]), patch.object(dashboard, "write_decision_plan") as writer, \
                    patch.object(dashboard, "load_json") as reader, redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as error:
                    dashboard.main()
                self.assertEqual(error.exception.code, 2)
                writer.assert_not_called()
                reader.assert_not_called()




def scheduled_compilation_fixture(root):
    """Synthetic scheduled caller input; never operational Grade A evidence."""
    from dual_run_scheduler import build_session_schedule
    from integrated_authority_snapshot import derive_us_market_session_authority_from_snapshot
    from test_deployment_provenance import current_deployment_fixture
    from validation_common import canonical_hash
    args, snapshot, _ = session_k3_inputs(root, now="2026-09-02T20:30:00+00:00")
    source = args["evidence"]
    manifest = current_deployment_fixture(root)
    resolver = lambda *a, **k: derive_us_market_session_authority_from_snapshot(snapshot, *a, **k)
    authority = resolver(source["decision_as_of"], primary_listing_operating_mic="XNYS", decision_as_of=source["decision_as_of"])
    window = authority.current_date_session
    schedule = build_session_schedule({"official_calendar_verified": True, "is_trading_day": True,
        "session": window.session_date, "core_open_at": window.core_open_at,
        "core_close_at": window.core_close_at, "calendar_source": authority.calendar_hash})
    phase = "REGULAR_CLOSE_T_PLUS_30"
    scheduled_at = next(r["scheduled_at"] for r in schedule["runs"] if r["run_phase"] == phase)
    occurrence = canonical_hash({"task_id": "post-close-portfolio-strategy", "run_phase": phase,
                                "scheduled_run_id": schedule["scheduled_run_id"], "scheduled_at": scheduled_at})
    source.update(trading_date=window.session_date, report_type="SCHEDULED_PORTFOLIO_ANALYSIS_PREFLIGHT", run_mode="LIVE_READ_ONLY",
                  trigger_type="SCHEDULED_GENUINE", operator_initiated=False,
                  run_provenance_status="VERIFIED_SCHEDULED", evidence_grade="GRADE_A",
                  scheduled_occurrence_id=occurrence)
    source["provenance"].update(execution_origin="SCHEDULED_GENUINE", decision_mode="LIVE_READ_ONLY",
                                 run_provenance_status="VERIFIED_SCHEDULED", evidence_grade="GRADE_A")
    pe = {"task_id": phase, "expected_operational_phase": phase, "scheduled_run_id": schedule["scheduled_run_id"],
          "expected_trading_day": source["trading_date"], "operator_initiated": False, "trigger_type": "SCHEDULED_GENUINE",
          "deployment_provenance_valid": True, "runtime_head_matches": True, "semantic_cohort_matches": True,
          "schedule_provenance_valid": True, "runtime_manifest_hash": manifest["record_hash"], "clean_committed_main": True}
    run = {"run_id": source["manual_run_id"], "decision_as_of": source["decision_as_of"],
           "execution_origin": "SCHEDULED_GENUINE", "decision_mode": "LIVE_READ_ONLY", "provenance_evidence": pe,
           "git_sha": "a" * 40, "runtime_manifest_hash": manifest["record_hash"],
           "semantic_cohort": manifest["semantic_cohort_id"], "temporal_evidence_status": "TEMPORAL_EVIDENCE_VALID",
           "portfolio_hash_before": source["system_portfolio_state"]["source_sha256"],
           "portfolio_hash_after": source["system_portfolio_state"]["source_sha256"]}
    supplied = {"run": run, "deployment_provenance": manifest, "task_id": "post-close-portfolio-strategy",
                "scheduled_at": scheduled_at, "scheduled_occurrence_id": occurrence}
    args.update(scheduled_provenance=supplied, integrated_snapshot=snapshot, current_session_authority_resolver=resolver)
    bind_scheduled_fixture(args)
    return args


def bind_scheduled_fixture(args):
    source = args["evidence"]
    digest = hashlib.sha256(evidence_raw_bytes(source)).hexdigest()
    args["input_hashes"]["portfolio_evidence"] = digest
    args["current_session_context"] = current_context(source, digest)
    args["scheduled_provenance"]["run"]["source_artifacts"] = [{"sha256": digest, "observed_at": source["decision_as_of"]}]


class ScheduledCompilationTests(unittest.TestCase):
    def compile(self, root, args):
        from test_deployment_provenance import fixture_git
        from portfolio_decision_order_intent import compile_order_intent_artifact
        with patch.object(dashboard, "ROOT", root), patch("deployment_provenance._git", side_effect=fixture_git), \
                patch("deployment_provenance.Path.home", return_value=root / "test-home"):
            report, validation = compile_dashboard(
                args["evidence"], args["plan"], args["risk_policy"], registry=args["registry"],
                generated_at=args["now"], run_id="scheduled-fixture-compilation",
                evidence_sha256=args["input_hashes"]["portfolio_evidence"],
                current_session_context=args["current_session_context"],
                current_session_authority_resolver=args["current_session_authority_resolver"],
                evidence_schema_bytes=MANUAL_EVIDENCE_SCHEMA.read_bytes(),
                input_mode="LIVE_READ_ONLY", scheduled_provenance=args["scheduled_provenance"],
                expected_runtime_head="a" * 40,
            )
        hashes = dict(args["input_hashes"],
                      portfolio_decision=hashlib.sha256(evidence_raw_bytes(report)).hexdigest(),
                      validation_report=hashlib.sha256(evidence_raw_bytes(validation)).hexdigest(),
                      decision_plan=hashlib.sha256(evidence_raw_bytes(args["plan"])).hexdigest())
        artifact = compile_order_intent_artifact(
            report, validation, args["plan"], args["evidence"], args["risk_policy"], args["registry"],
            risk_envelope_sha256=args["risk_envelope_sha256"], input_hashes=hashes, now=args["now"],
            integrated_snapshot=args["integrated_snapshot"], alert_policy=args["alert_policy"],
            current_session_context=args["current_session_context"],
            current_session_authority_resolver=args["current_session_authority_resolver"],
            trigger_provenance=report["trigger_provenance"],
        )
        return report, validation, artifact

    def test_scheduled_cli_reuses_one_snapshot_and_passes_validated_trigger(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = scheduled_compilation_fixture(root)
            observed = SessionK3DashboardBoundaryTests().run_current(root, args, scheduled=True)
            self.assertEqual(observed.exit_code, 0, observed.stderr)
            observed.loader.assert_called_once()
            observed.compiler.assert_called_once()
            self.assertEqual(len(observed.reads), 3)
            self.assertIs(observed.compiler.call_args.kwargs["integrated_snapshot"], observed.snapshots[0])
            resolver = observed.dashboard.call_args.kwargs["current_session_authority_resolver"]
            self.assertIs(resolver, observed.compiler.call_args.kwargs["current_session_authority_resolver"])
            self.assertTrue(all(c.args[0] is observed.snapshots[0] for c in observed.derive.call_args_list))
            artifact = observed.writer.call_args.kwargs["order_intent_artifact"]
            self.assertEqual(artifact["trigger_provenance"]["trigger_type"], "SCHEDULED_GENUINE")
            digest = hashlib.sha256(evidence_raw_bytes(args["scheduled_provenance"])).hexdigest()
            self.assertEqual(artifact["input_hashes"]["scheduled_provenance"], digest)
            self.assertEqual(observed.writer.call_args.kwargs["consumed_hashes"]["scheduled_provenance"], digest)

    def test_valid_scheduled_compilation_preserves_manual_rule_and_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = scheduled_compilation_fixture(root)
            before = copy.deepcopy((args["evidence"], args["plan"], args["scheduled_provenance"]))
            report, validation, artifact = self.compile(root, args)
            self.assertEqual(validation["status"], "PASS", validation)
            self.assertEqual(report["evidence"]["canonical_gate_blockers"], [])
            self.assertEqual(artifact["trigger_provenance"]["run_provenance_status"], "VERIFIED_SCHEDULED_GENUINE")
            self.assertEqual(artifact["trigger_provenance"]["operational_grade"], "GRADE_A_CANDIDATE")
            self.assertFalse(artifact["trigger_provenance"]["scheduled_maturity_promoted"])
            row = next(r for r in artifact["instructions"] if r["ticker"] == "PGR")
            self.assertEqual(row["state"], "ORDER_EXPIRED", row)
            self.assertFalse(artifact["order_authority"])
            self.assertIsNone(artifact["execution_quantity"])
            self.assertFalse(artifact["automatic_order"])
            self.assertEqual(artifact["broker_submission"], "DISABLED")
            self.assertEqual((args["evidence"], args["plan"], args["scheduled_provenance"]), before)

    def test_manual_masquerade_labels_and_provenance_bindings_fail_closed(self):
        cases = ("manual", "label_only", "source_manual", "task", "occurrence", "run", "time", "schedule", "hash", "manifest", "grade", "temporal")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args = scheduled_compilation_fixture(root)
                supplied, source = args["scheduled_provenance"], args["evidence"]
                if case == "manual": source["operator_initiated"] = True
                elif case == "label_only": args["scheduled_provenance"] = {"scheduled": True}
                elif case == "source_manual": supplied["run"]["execution_origin"] = "MANUAL"
                elif case == "task": supplied["task_id"] = "REGULAR_CLOSE_T_PLUS_30"
                elif case == "occurrence": source["scheduled_occurrence_id"] = "wrong-occurrence"
                elif case == "run": supplied["run"]["run_id"] = "different-run"
                elif case == "time": supplied["run"]["decision_as_of"] = "2026-09-01T20:30:00+00:00"
                elif case == "schedule": supplied["scheduled_at"] = "2026-09-02T20:31:00+00:00"
                elif case == "hash": supplied["run"]["source_artifacts"][0]["sha256"] = "0" * 64
                elif case == "manifest": supplied["deployment_provenance"]["record_hash"] = "0" * 64
                elif case == "grade": source["evidence_grade"] = "GRADE_B"
                elif case == "temporal": del supplied["run"]["temporal_evidence_status"]
                with self.assertRaises(ContractError): self.compile(root, args)

    def test_missing_unapproved_and_invalid_plan_rejected(self):
        for status in (None, "PROVISIONAL", "HISTORICAL", "missing_plan_id"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args = scheduled_compilation_fixture(root)
                if status is None: args["plan"] = None
                elif status == "missing_plan_id": del args["plan"]["plan_id"]
                else: args["plan"]["plan_status"] = status
                with self.assertRaises(ContractError): self.compile(root, args)

    def test_plan_binding_session_and_stale_evidence_never_ready(self):
        for case in ("run", "decision_time", "session", "stale", "expired", "quantity", "next_day"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args = scheduled_compilation_fixture(root)
                plan = args["plan"]
                if case == "run": plan["evidence_binding"]["expected_run_id"] = "prior-run"
                elif case == "decision_time": plan["evidence_binding"]["expected_decision_as_of"] = "2026-09-01T20:30:00+00:00"
                elif case == "session": args["current_session_context"]["expected_completed_us_session"] = "2026-08-31"
                elif case == "stale":
                    args["evidence"]["broker_snapshot_as_of"] = "2026-09-01T20:30:00+00:00"
                    bind_scheduled_fixture(args)
                elif case == "expired":
                    for p in plan["positions"]:
                        if p.get("order_intent_terms"):
                            p["order_intent_terms"].update(valid_until="2026-09-02T19:59:00+00:00",
                                                            approved_price_rule=None, order_type="LIMIT", limit_price=200.0)
                elif case == "next_day": args["now"] = "2026-09-03T20:30:00+00:00"
                elif case == "quantity":
                    for p in plan["positions"]:
                        if p.get("order_intent_terms"): p["order_intent_terms"]["proposed_quantity"] = 1
                before = copy.deepcopy(plan)
                report, _, artifact = self.compile(root, args)
                self.assertNotEqual(artifact["run_state"], "ORDER_INSTRUCTION_READY")
                self.assertEqual(plan, before)
                if case == "run": self.assertIn("EVIDENCE_RUN_ID_BINDING_MISMATCH", report["evidence"]["canonical_gate_blockers"])
                elif case == "decision_time": self.assertIn("EVIDENCE_DECISION_AS_OF_BINDING_MISMATCH", report["evidence"]["canonical_gate_blockers"])
                elif case == "stale": self.assertIn("BROKER_SNAPSHOT_STALE", report["evidence"]["canonical_gate_blockers"])
                elif case == "session": self.assertFalse(report["current_context"]["verified"])
                elif case in {"expired", "next_day"}: self.assertEqual(next(r for r in artifact["instructions"] if r["ticker"] == "PGR")["state"], "ORDER_EXPIRED")
                elif case == "quantity": self.assertEqual(next(r for r in artifact["instructions"] if r["ticker"] == "PGR")["proposed_quantity"], 1)




def _technical_capture_fixture(snapshot, *, session, observed_at, run_id, confirmed=True):
    """Actual synthetic RAW/ADJUSTED history; no calculator or validator result mock."""
    from datetime import datetime, timedelta
    from build_kiwoom_market_snapshot import normalize_series
    from kiwoom_replay_validation import calculate_kiwoom_technical
    observed = datetime.fromisoformat(observed_at)
    doc = dict(run_id=run_id, started_at=(observed-timedelta(seconds=1)).isoformat(),
               observed_at=observed_at, requests=[], results=[])
    days = []; day = datetime.fromisoformat(session)
    while len(days) < 260:
        if day.weekday() < 5:
            days.append(day.strftime("%Y%m%d"))
        day -= timedelta(days=1)
    days.reverse()
    for ticker in ("MVLL", "MRVL", "SOXL", "SOXX"):
        data = []
        for i, date in enumerate(days):
            close = {257:126.0, 258:127.0, 259:130.0}.get(i, 100+i*0.1)
            opening = float(data[-1]["cur_prc"])+0.1 if data else close
            data.append(dict(dt=date, open_pric=str(opening), high_pric=str(max(opening,close)+1),
                low_pric=str(min(opening,close)-1), cur_prc=str(close), acc_trde_qty=str(500000+i)))
        series = {}
        for basis in ("RAW", "ADJUSTED"):
            rows = data[-30:] if basis == "RAW" else data
            pagination = dict(api_id="usa06012",status="SUFFICIENT",pages_fetched=1,
                pages=[dict(page_index=1,api_id="usa06012",retrieved_at=observed_at)])
            doc["requests"].append(dict(operation="daily_chart",ticker=ticker,fx_applied=False,
                completed_session=session,price_basis=basis))
            doc["results"].append(dict(operation="daily_chart",ticker=ticker,requested_price_basis=basis,
                source_provider="KIWOOM_REST",bridge_status="PASS",order_authority=False,
                retrieved_at=observed_at,data=copy.deepcopy(rows),pagination=pagination))
            series[basis] = normalize_series(rows,ticker=ticker,completed_session=session,
                price_basis=basis,minimum_history_bars=252 if basis=="ADJUSTED" else 1,pagination=pagination)
        calculated = calculate_kiwoom_technical(series["RAW"],series["ADJUSTED"],cutoff=session,
            minimum_history_bars=252,include_timing_record=True)
        assert calculated["status"] == "KIWOOM_TECHNICAL_VALIDATED"
        row = calculated["timing_record"]
        # The separate full synthetic CA fixture below is required at consumption.
        row["corporate_action_unresolved"] = False
        if confirmed:
            row["quote_crosscheck"] = dict(status="verified",independent_of_builder=True,
                bar_date=session,source="SYNTHETIC_INDEPENDENT",source_url="https://example.invalid/fixture",
                verified_at_utc=observed_at,completed_close=row["close"],
                difference_usd=0,tolerance_usd=max(.05,.001*row["close"]))
        snapshot["symbols"][ticker] = row
    doc["request_sha256"] = _manual_module.manual_preflight_module.canonical_hash(doc["requests"])
    return doc


class ManualStep2TimingTests(unittest.TestCase):
    """Synthetic inputs through the real Manual, timing and Swing producers."""

    def setUp(self):
        from datetime import date, datetime, timedelta, timezone
        from test_evaluate_timing_integration import EvaluateTimingIntegrationTests
        case = EvaluateTimingIntegrationTests(methodName="runTest")
        case.setUp()
        self.inputs = {"snapshot": case.snapshot, "state": case.state, "policy": case.policy}
        stamp = "2026-08-21T22:00:00+00:00"
        end = "2026-08-20"
        snap = self.inputs["snapshot"]
        shift = date.fromisoformat(end) - date.fromisoformat(snap["session"]["us_session_date"])
        snap["generated_at_utc"] = stamp
        snap["session"].update(us_session_date=end, expected_us_session_date=end, calendar_verified_at_utc=stamp)
        for row in snap["symbols"].values():
            row["bar_date"] = end
            row["corporate_action_unresolved"] = False
            row["quote_crosscheck"].update(bar_date=end, verified_at_utc=stamp)
            for bar in row["timing_window"]:
                bar["bar_date"] = (date.fromisoformat(bar["bar_date"]) + shift).isoformat()
        self.technical_doc = _technical_capture_fixture(snap, session=end,
            observed_at=stamp, run_id="manual-test-run-0001")
        self.inputs["capture_artifacts"] = [_ca_pair(self.technical_doc)]
        state = self.inputs["state"]
        state["last_confirmed_broker_snapshot"].update(as_of=end, as_of_timestamp_kst=stamp)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for key, constant in [("state", "DEFAULT_PORTFOLIO_STATE"), ("policy", "DEFAULT_ALERT_POLICY")]:
            path = root / (key + ".json"); path.write_text(json.dumps(self.inputs[key]), encoding="utf-8")
            self.stack.enter_context(patch.object(dashboard, constant, path))
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.fromisoformat("2026-08-21T22:00:03+00:00").astimezone(tz)
        self.stack.enter_context(patch("evaluate_alerts.datetime", Clock))
        # This is the external identity source contact, not a timing-result mock.
        self.identity = self.stack.enter_context(patch("instrument_identity_authority.resolve_instrument_identity",
            side_effect=lambda *a, **kw: SimpleNamespace(authority_status="VERIFIED")))
        self.manual = _manual_module.ManualPortfolioAnalysisTest(methodName="runTest")
        self.manual.setUpClass(); self.manual.setUp(); self.addCleanup(self.manual.tearDown)
        ops = list(_manual_module.manual_preflight_module.ACCOUNT_READ_OPERATIONS)
        ticks = sorted(state["holdings"])
        accounts = [{"operation": op} for op in ops]
        markets = [{"operation": "oauth_health"}] + [{"operation": "market_quote", "ticker": t, "fx_applied": False} for t in ticks]
        markets += [{"operation": "daily_chart", "ticker": t, "completed_session": end, "price_basis": "RAW", "fx_applied": False} for t in ticks]
        ar = _manual_module.account_reader_for(state["holdings"], state["average_cost_usd"])(accounts)
        mr = _manual_module.market_reader_for(ticks, include_same_day=set())(markets)
        for row in ar:
            if row["operation"] == "account_open_items":
                row.update(bridge_status="KIWOOM_API_RESPONSE_ERROR", failure_type="API_RESPONSE_ERROR", data=[], retrieved_at=None, pagination={"complete":False})
        for row in mr:
            if row["operation"] == "daily_chart":
                for bar in row["data"]:
                    technical = snap["symbols"].get(row["ticker"], snap["symbols"]["MVLL"])
                    bar.update(cur_prc=technical["close"], open_pric=technical["open"],
                               high_pric=technical["high"], low_pric=technical["low"],
                               acc_trde_qty=technical["volume"])
        doc = {"run_id":"manual-test-run-0001", "started_at":"2026-08-21T21:59:59+00:00",
               "observed_at":"2026-08-21T22:00:01+00:00", "requests":accounts+markets, "results":ar+mr,
               "request_sha256":_manual_module.manual_preflight_module.canonical_hash(accounts+markets)}
        raw=json.dumps(doc,sort_keys=True).encode()
        self.captures=[(raw,hashlib.sha256(raw).hexdigest())]
        self.ev=self.manual.build_report(portfolio=state, broker_holdings=state["holdings"], broker_costs=state["average_cost_usd"],
            parent_capture_artifacts=self.captures, direction_only=True,
            observed_at="2026-08-21T22:00:03+00:00", decision_as_of="2026-08-21T22:00:03+00:00",
            account_reader_override=lambda reqs: copy.deepcopy(ar), market_reader_override=lambda reqs:copy.deepcopy(mr))
        self.plan=plan();self.plan["evidence_binding"]={"expected_run_id":self.ev["manual_run_id"],"expected_decision_as_of":self.ev["decision_as_of"]}
        self.plan["positions"]=[x for x in self.plan["positions"] if x["ticker"] in {"MVLL","SOXL","NBIS"}]
        self.plan.pop("buy_priority",None)
        for pos in self.plan["positions"]:
            pos.pop("target_weight_pct",None); pos["action"]="TRIM" if pos["ticker"]=="MVLL" else "HOLD"
        self.risk=load_json(DEFAULT_RISK_POLICY)
        _attach_ca_fixture(SimpleNamespace(doc=self.technical_doc, case=SimpleNamespace(
            base=self, doc=doc, stamp=self.ev["decision_as_of"],
            manual=_manual_module.manual_preflight_module)))

    def step2_authority(self, *args, **kwargs):
        value = canonical_runtime_resolver(self.ev)(*args, **kwargs)
        # Synthetic official-calendar contact: real session-window field shape.
        value.expected_completed_session.core_close_at = "2026-08-20T20:00:00+00:00"
        return value

    def compile_step2(self, inputs=True, **kwargs):
        ev=kwargs.pop("evidence",self.ev)
        return compile_dashboard(ev,self.plan,self.risk,generated_at="2026-08-21T22:00:03+00:00",
            current_session_context=current_context(ev),current_session_authority_resolver=self.step2_authority,
            evidence_sha256=hashlib.sha256(evidence_raw_bytes(ev)).hexdigest(), parent_capture_artifacts=self.captures,
            holding_timing_inputs=self.inputs if inputs is True else inputs if isinstance(inputs,dict) else None, **kwargs)

    def timing_row(self, report):
        return next(x for x in report["swing_action_plan"]["rows"] if x["ticker"]=="MVLL")

    def test_step2_existing_reduce_producer_to_compiled_rendered_persisted_output(self):
        report,valid=self.compile_step2()
        self.assertEqual(valid["schema_errors"],[])
        self.assertEqual(valid["swing_action_contract_errors"],[])
        self.assertEqual(self.timing_row(report)["timing_status"],"VERIFIED_REDUCTION_REVIEW", (valid,report["evidence"]))
        self.assertIn("VERIFIED_REDUCTION_REVIEW", render_html(report))
        self.assertIn("VERIFIED_REDUCTION_REVIEW", render_markdown(report))
        self.assertEqual(report["swing_action_plan"]["source_binding"]["account_identity_status"],"NOT_VERIFIED")
        self.assertEqual(report["swing_action_plan"]["source_binding"]["policy_approval_binding"],"NOT_VERIFIED")
        for row in report["swing_action_plan"]["rows"]:
            self.assertIsNone(row["shadow_sell_qty"]);self.assertEqual(row["execution_status"],"DISABLED")
        out=write_run(report,valid,output_root=Path(self.temp.name)/"output",source_paths={},implementation_paths=[],root=Path(self.temp.name))
        self.assertTrue(out.exists())
        self.assertTrue(any("VERIFIED_REDUCTION_REVIEW" in p.read_text(encoding="utf-8") for p in out.glob("*.json")))

    def test_step2_missing_inputs_preserve_historical_contract(self):
        report,_=self.compile_step2(inputs=False)
        self.assertTrue(all(r["timing_status"]=="NOT_VERIFIED" for r in report["swing_action_plan"]["rows"]))
        old=copy.deepcopy(report);old.pop("swing_action_plan")
        self.assertEqual(dashboard.validate_swing_action_contract(old),[])

    def test_step2_forged_statuses_rejected(self):
        report,_=self.compile_step2(inputs=False)
        for field,value in [("timing_status","VERIFIED_REDUCTION_REVIEW"),("account_identity_status","VERIFIED"),("policy_approval_binding","VERIFIED")]:
            forged=copy.deepcopy(report)
            if field=="timing_status":self.timing_row(forged)[field]=value
            else:forged["swing_action_plan"]["source_binding"][field]=value
            with self.subTest(field=field):
                self.assertTrue(dashboard.validate_swing_action_contract(forged))
                with self.assertRaises(ContractError):render_markdown(forged)

    def test_step2_source_policy_state_mismatch_not_verified(self):
        for target,key,value in [("policy","policy_version","forged"),("state","strategy_version","forged")]:
            bad=copy.deepcopy(self.inputs);bad[target][key]=value
            report,_=self.compile_step2(inputs=bad)
            self.assertEqual(self.timing_row(report)["timing_status"],"NOT_VERIFIED")

    def test_step2_snapshot_time_future_stale_session_mismatch(self):
        for field,value in [("generated_at_utc","2026-08-21T22:00:04+00:00"),("generated_at_utc","2026-08-21T21:40:00+00:00"),("session","2026-08-19")]:
            bad=copy.deepcopy(self.inputs)
            if field=="session":bad["snapshot"]["session"]["us_session_date"]=value
            else:bad["snapshot"][field]=value
            with self.subTest(value=value):
                report,_=self.compile_step2(inputs=bad)
                self.assertEqual(self.timing_row(report)["timing_status"],"NOT_VERIFIED")

    def test_step2_missing_crosscheck_or_unverified_identity(self):
        bad=copy.deepcopy(self.inputs);bad["snapshot"]["symbols"]["MVLL"]["quote_crosscheck"]=None
        report,_=self.compile_step2(inputs=bad)
        # Full capture/CA fixture invokes the existing approved missing-close exception.
        self.assertEqual(self.timing_row(report)["timing_status"],"VERIFIED_REDUCTION_REVIEW")
        holding=next(r for r in report["portfolio"]["positions"] if r["ticker"]=="MVLL")
        self.assertEqual(holding["holding_timing_evidence"]["timing_source_mode"],"KIWOOM_ONLY")
        self.identity.side_effect=lambda *a,**kw:SimpleNamespace(authority_status="NOT_VERIFIED")
        report,_=self.compile_step2()
        self.assertEqual(self.timing_row(report)["timing_status"],"NOT_VERIFIED")

    def test_step2_input_aware_hash_binding_rejects_coherent_tamper(self):
        report,_=self.compile_step2()
        row=next(x for x in report["portfolio"]["positions"] if x["ticker"]=="MVLL")
        self.assertIn("holding_timing_evidence",row)
        row["holding_timing_evidence"]["snapshot_sha256"]="a"*64
        errors=dashboard.validate_swing_action_contract(report,evidence=self.ev,plan=self.plan,risk_policy=self.risk,
            evidence_sha256=hashlib.sha256(evidence_raw_bytes(self.ev)).hexdigest(),holding_timing_inputs=self.inputs,
            parent_capture_artifacts=self.captures,current_session_authority_resolver=self.step2_authority)
        self.assertIn("SWING_TIMING_CONSUMED_INPUT_MISMATCH",errors)

    def test_step2_input_aware_gate_requires_real_captures_and_core_evidence(self):
        report, _ = self.compile_step2()
        options = dict(evidence=self.ev, plan=self.plan, risk_policy=self.risk,
            evidence_sha256=hashlib.sha256(evidence_raw_bytes(self.ev)).hexdigest(),
            holding_timing_inputs=self.inputs, parent_capture_artifacts=self.captures,
            current_session_authority_resolver=self.step2_authority)
        self.assertEqual(dashboard.validate_swing_action_contract(report, **options), [])
        self.assertIn("SWING_TIMING_CONSUMED_INPUT_MISMATCH",
            dashboard.validate_swing_action_contract(report, **dict(options, parent_capture_artifacts=None)))
        bad = copy.deepcopy(self.ev)
        bad.pop("historical_daily_evidence")
        tampered = copy.deepcopy(report)
        row = next(x for x in tampered["portfolio"]["positions"] if x["ticker"] == "MVLL")
        row["holding_timing_evidence"]["manual_evidence_sha256"] = dashboard._sha256_bytes(dashboard._json_bytes(bad))
        new_hash = hashlib.sha256(evidence_raw_bytes(bad)).hexdigest()
        tampered["swing_action_plan"]["source_binding"]["evidence_sha256"] = new_hash
        self.assertIn("SWING_TIMING_CONSUMED_INPUT_MISMATCH",
            dashboard.validate_swing_action_contract(tampered, **dict(options, evidence=bad, evidence_sha256=new_hash)))

    def test_step2_crosscheck_before_official_completed_close_is_not_verified(self):
        for stamp in ("2020-01-01T00:00:00+00:00", "2026-08-20T19:59:59+00:00"):
            bad = copy.deepcopy(self.inputs)
            for row in bad["snapshot"]["symbols"].values():
                row["quote_crosscheck"]["verified_at_utc"] = stamp
            with self.subTest(stamp=stamp):
                report, _ = self.compile_step2(inputs=bad)
                self.assertEqual(self.timing_row(report)["timing_status"], "NOT_VERIFIED")

    def test_step2_missing_official_close_does_not_gain_timing(self):
        self.step2_authority = canonical_runtime_resolver(self.ev)
        report, _ = self.compile_step2()
        self.assertEqual(self.timing_row(report)["timing_status"], "NOT_VERIFIED")

    def test_step2_partial_inputs_cannot_silently_downgrade_to_format_only(self):
        report, _ = self.compile_step2()
        self.assertEqual(dashboard.validate_swing_action_contract(report), [])
        for kwargs in (
                {"holding_timing_inputs": {"snapshot": {}, "state": {}, "policy": {}}},
                {"holding_timing_inputs": {}},
                {"parent_capture_artifacts": [(b"{}", "a" * 64)]},
                {"parent_capture_artifacts": []}):
            with self.subTest(inputs=list(kwargs)):
                self.assertIn("SWING_PROVENANCE_INPUTS_INCOMPLETE",
                    dashboard.validate_swing_action_contract(report, **kwargs))

    def test_step2_non_trim_and_replay_do_not_gain_timing(self):
        self.plan["positions"][0]["action"]="HOLD"
        report,_=self.compile_step2()
        self.assertEqual(self.timing_row(report)["timing_status"],"NOT_VERIFIED")
        report,_=self.compile_step2(compile_mode="HISTORICAL_REPLAY")
        self.assertEqual(self.timing_row(report)["timing_status"],"NOT_VERIFIED")




class ManualCliInputWiringTests(unittest.TestCase):
    """Real CLI/compile/render/persist; only canonical authority contacts are synthetic."""

    def setUp(self):
        self.case = ManualStep2TimingTests(methodName="runTest")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root = Path(self.case.temp.name)
        self.stack = self.case.stack
        self.paths = {}
        for name, value in (("evidence", self.case.ev), ("plan", self.case.plan),
                            ("risk", self.case.risk), ("context", current_context(self.case.ev)),
                            ("snapshot", self.case.inputs["snapshot"])):
            path = self.root / (name + ".json")
            path.write_bytes(dashboard._json_bytes(value))
            self.paths[name] = path
        self.capture = self.root / "capture.json"
        self.capture.write_bytes(self.case.captures[0][0])
        registry = self.root / "workspace/policies/instrument_registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_bytes((dashboard.ROOT / "workspace/policies/instrument_registry.json").read_bytes())
        for name in ("MANUAL_EVIDENCE_SCHEMA", "PLAN_SCHEMA", "DASHBOARD_SCHEMA",
                     "CURRENT_SESSION_CONTEXT_SCHEMA", "REQUEST_ACCOUNTING_SCHEMA"):
            old = getattr(dashboard, name)
            dest = self.root / old.relative_to(dashboard.ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(old.read_bytes())
            self.stack.enter_context(patch.object(dashboard, name, dest))
        self.stack.enter_context(patch.object(dashboard, "ROOT", self.root))
        self.stack.enter_context(patch.object(dashboard, "_now", return_value="2026-08-21T22:00:03+00:00"))
        # Existing authority contacts are separately covered by integrated-boundary tests.
        self.stack.enter_context(patch.object(dashboard, "load_production_integrated_authority_snapshot", return_value=None))
        self.stack.enter_context(patch.object(dashboard, "_snapshot_authority_hashes", return_value={}))
        self.stack.enter_context(patch.object(dashboard, "derive_us_market_session_authority_from_snapshot",
            side_effect=lambda *a, **kw: self.case.step2_authority()))
        self.stack.enter_context(patch.object(dashboard, "implementation_provenance_paths", return_value=[]))
        self.stack.enter_context(patch.object(dashboard, "_git_commit", return_value=None))
        self.compiler = self.stack.enter_context(patch.object(dashboard, "compile_dashboard", wraps=dashboard.compile_dashboard))
        self.network = self.stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("OFFLINE_ONLY")))
        self.argv = ["--portfolio-evidence", str(self.paths["evidence"]), "--decision-plan", str(self.paths["plan"]),
            "--risk-policy", str(self.paths["risk"]), "--current-session-context", str(self.paths["context"]),
            "--output-root", str(self.root / "output"), "--run-id", "cli-synthetic"]

    def run_cli(self, *, timing=True, captures=True, extra=None):
        args = self.argv + (["--parent-capture", str(self.capture)] if captures else [])
        if timing:
            args += ["--holding-timing-snapshot", str(self.paths["snapshot"])]
        args += extra or []
        with redirect_stdout(StringIO()):
            result = dashboard.main(args)
        out = self.root / "output/cli-synthetic"
        return result, json.loads((out / "portfolio-decision.json").read_text(encoding="utf-8")), out

    def test_cli_real_path_passes_bytes_and_persists_only_hashes(self):
        raw = self.capture.read_bytes()
        result, report, out = self.run_cli()
        self.assertEqual(result, 0)
        self.assertEqual(self.case.timing_row(report)["timing_status"], "NOT_VERIFIED")
        # Existing CLI carries no CA artifacts; API normal paths are tested separately.
        self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")
        self.assertEqual(self.compiler.call_args.kwargs["parent_capture_artifacts"], [(raw, hashlib.sha256(raw).hexdigest())])
        supplied = self.compiler.call_args.kwargs["holding_timing_inputs"]
        self.assertEqual(supplied, {key:self.case.inputs[key] for key in ("snapshot","state","policy")})
        self.assertNotIn("corporate_action_artifacts", supplied)
        manifest = json.loads((out / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["consumed_hashes"]["parent_capture_0"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(manifest["consumed_hashes"]["holding_timing_snapshot"], hashlib.sha256(self.paths["snapshot"].read_bytes()).hexdigest())
        self.assertEqual(manifest["consumed_hashes"]["holding_timing_policy"], manifest["consumed_hashes"]["alert_policy"])
        self.assertFalse(report["swing_action_plan"]["order_authority"])
        self.assertIsNone(report["swing_action_plan"]["execution_quantity"])
        self.assertTrue(all(r["shadow_sell_qty"] is None for r in report["swing_action_plan"]["rows"]))
        self.assertNotIn("VERIFIED_REDUCTION_REVIEW", (out / "portfolio-decision-dashboard.html").read_text(encoding="utf-8"))
        self.network.assert_not_called()

    def test_cli_capture_only_preserves_direction_without_timing(self):
        _, report, _ = self.run_cli(timing=False)
        row = self.case.timing_row(report)
        self.assertEqual(row["direction"], "TRIM")
        self.assertEqual(row["timing_status"], "NOT_VERIFIED")
        self.assertEqual(row["reason"], "leveraged concentration")
        self.assertEqual(row["price_status"], "NOT_VERIFIED")
        self.assertEqual(row["execution_status"], "DISABLED")
        self.assertIsNone(row["shadow_sell_qty"])
        forged = copy.deepcopy(report)
        forged["evidence"].pop("manual_capture_only_direction")
        with self.assertRaises(ContractError):
            render_markdown(forged)

    def test_cli_missing_capture_and_mode_mix_block_before_read(self):
        combos = [["--holding-timing-snapshot", "unused.json"],
            ["--parent-capture", "unused.json", "--mode", "HISTORICAL_REPLAY"],
            ["--parent-capture", "unused.json", "--mode", "POST_SELL_RECOMPILE"],
            ["--parent-capture", "unused.json", "--input-mode", "LIVE_READ_ONLY"],
            ["--parent-capture", "unused.json", "--materialize-plan-only"],
            ["--parent-capture", "unused.json", "--discover-historical-replay"]]
        for args in combos:
            with self.subTest(args=args), patch.object(Path, "read_bytes", side_effect=AssertionError("MUST_NOT_READ")), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    dashboard.main(args)
                self.assertEqual(caught.exception.code, 2)
        self.compiler.assert_not_called()

    def test_cli_wrong_run_capture_cannot_unlock(self):
        doc = json.loads(self.capture.read_bytes())
        doc["run_id"] = "other-synthetic-run"
        self.capture.write_bytes(dashboard._json_bytes(doc))
        _, report, _ = self.run_cli()
        self.assertNotEqual(report["evidence"]["portfolio_evidence_status"], "VERIFIED")
        self.assertEqual(self.case.timing_row(report)["timing_status"], "NOT_VERIFIED")

    def test_cli_invalid_snapshot_has_safe_error(self):
        for raw in (b'{"token":"SYNTHETIC_PRIVATE_VALUE",broken', b'[]'):
            self.paths["snapshot"].write_bytes(raw)
            stderr = StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit):
                self.run_cli()
            self.assertIn("MANUAL_INPUT_ARTIFACT_INVALID", stderr.getvalue())
            self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", stderr.getvalue())
        self.compiler.assert_not_called()

    def test_cli_old_snapshot_stays_unverified(self):
        snapshot = copy.deepcopy(self.case.inputs["snapshot"])
        snapshot["generated_at_utc"] = "2026-08-21T21:40:00+00:00"
        self.paths["snapshot"].write_bytes(dashboard._json_bytes(snapshot))
        _, report, _ = self.run_cli()
        self.assertEqual(self.case.timing_row(report)["timing_status"], "NOT_VERIFIED")

    def test_cli_extra_sensitive_capture_metadata_is_not_persisted(self):
        doc = json.loads(self.capture.read_bytes())
        doc["Authorization"] = "SYNTHETIC_CAPTURE_SECRET_97"
        self.capture.write_bytes(dashboard._json_bytes(doc))
        _, _, out = self.run_cli()
        for path in out.iterdir():
            self.assertNotIn("SYNTHETIC_CAPTURE_SECRET_97", path.read_text(encoding="utf-8"))

    def test_cli_repeated_capture_arguments_keep_exact_order_and_reject_bad_extra(self):
        second = self.root / "unrelated-capture.json"
        second.write_bytes(b'{"run_id":"unrelated"}')
        _, report, _ = self.run_cli(extra=["--parent-capture", str(second)])
        consumed = self.compiler.call_args.kwargs["parent_capture_artifacts"]
        self.assertEqual(consumed, [(p.read_bytes(), hashlib.sha256(p.read_bytes()).hexdigest())
                                    for p in (self.capture, second)])
        self.assertEqual(self.case.timing_row(report)["timing_status"], "NOT_VERIFIED")

    def test_cli_missing_capture_file_is_safe_and_does_not_compile(self):
        self.capture.unlink()
        stderr = StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit):
            self.run_cli()
        self.assertIn("MANUAL_INPUT_ARTIFACT_INVALID", stderr.getvalue())
        self.assertNotIn(str(self.capture), stderr.getvalue())
        self.compiler.assert_not_called()


class TechnicalTimingConsumerAlignmentTests(unittest.TestCase):
    """Real capture replay, ACTIVE fixture loader, evaluator and Swing boundary.

    Fixtures live only in Temp; no broker, live authority activation or state
    reconciliation. The timing result itself is never mocked.
    """

    def setUp(self):
        from datetime import date, datetime
        from functools import partial
        import integrated_authority_snapshot as integrated
        import run_manual_portfolio_analysis as manual
        from test_integrated_authority_snapshot import ConfirmationIntegratedConsumerTest
        self.base = ManualStep2TimingTests("runTest")
        self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.authorities = ConfirmationIntegratedConsumerTest("runTest")
        self.authorities.setUp(); self.addCleanup(self.authorities.tearDown)
        self.root = self.authorities.root
        self.activation = self.root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
        self.activation.parent.mkdir(parents=True, exist_ok=True)
        manifest = copy.deepcopy(self.authorities.manifest)
        manifest["activation_status"] = "ACTIVE"
        self.activation.write_text(json.dumps(manifest), encoding="utf-8")
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(dashboard, "ROOT", self.root))
        self.stack.enter_context(patch.object(manual, "ROOT", self.root))
        self.manual = manual; self.integrated = integrated
        self.stamp = "2026-09-02T22:00:03+00:00"
        snap = self.base.inputs["snapshot"]
        shift = date(2026, 9, 1) - date(2026, 8, 20)
        snap["generated_at_utc"] = "2026-09-02T22:00:00+00:00"
        snap["session"].update(us_session_date="2026-09-01", expected_us_session_date="2026-09-01",
                               calendar_verified_at_utc="2026-09-02T22:00:00+00:00")
        for row in snap["symbols"].values():
            row["bar_date"] = "2026-09-01"
            row["quote_crosscheck"].update(bar_date="2026-09-01", verified_at_utc="2026-09-02T22:00:00+00:00")
            for bar in row["timing_window"]:
                bar["bar_date"] = (date.fromisoformat(bar["bar_date"]) + shift).isoformat()
        technical_doc = _technical_capture_fixture(snap, session="2026-09-01",
            observed_at="2026-09-02T22:00:00+00:00", run_id="manual-test-run-0001")
        self.base.inputs["capture_artifacts"] = [_ca_pair(technical_doc)]
        self.base.inputs["state"]["last_confirmed_broker_snapshot"].update(
            as_of="2026-09-01", as_of_timestamp_kst=self.stamp)
        self.save_fixture_state()
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.fromisoformat("2026-09-02T22:00:03+00:00").astimezone(tz)
        self.stack.enter_context(patch("evaluate_alerts.datetime", Clock))
        self.base.identity.side_effect = AssertionError("K3 must not call legacy identity")
        doc = self.base.captures[0][0].decode()
        self.doc = json.loads(doc.replace("2026-08-21", "2026-09-02")
                             .replace("2026-08-20", "2026-09-01").replace("20260820", "20260901"))
        self.doc["request_sha256"] = manual.canonical_hash(self.doc["requests"])
        self.bound = integrated.load_production_integrated_authority_snapshot(
            trusted_root=self.root, decision_as_of=self.stamp, resolved_at=self.stamp,
            run_id=self.doc["run_id"])
        self.resolver = partial(integrated.derive_us_market_session_authority_from_snapshot, self.bound)
        _attach_ca_fixture(SimpleNamespace(doc=technical_doc, case=self))

    def save_fixture_state(self):
        dashboard.DEFAULT_PORTFOLIO_STATE.write_text(json.dumps(self.base.inputs["state"]), encoding="utf-8")

    def compile(self, *, holdings_change=None, cost_change=None):
        doc = copy.deepcopy(self.doc)
        holdings = next(r for r in doc["results"] if r["operation"] == "account_holdings_read")
        for row in holdings["data"]:
            if holdings_change and row["stk_cd"] == holdings_change[0]:
                for key in ("qty", "poss_qty", "sell_alowq"):
                    row[key] = holdings_change[1]
            if cost_change and row["stk_cd"] == cost_change[0]:
                row["frgn_stk_book_uv"] = cost_change[1]
        raw = json.dumps(doc, sort_keys=True).encode()
        captures = [(raw, hashlib.sha256(raw).hexdigest())]
        def reader(requests):
            return [copy.deepcopy(doc["results"][doc["requests"].index(q)]) for q in requests]
        ev = self.manual.run_manual_preflight(
            manual_run_id=doc["run_id"], system_portfolio=self.base.inputs["state"],
            system_portfolio_source="TEST_ONLY/canonical-state.json", system_portfolio_sha256="a" * 64,
            provenance_policy=self.base.manual.provenance_policy, account_reader=reader, market_reader=reader,
            maximum_broker_age_seconds=900, observed_at=self.stamp, decision_as_of=self.stamp,
            k3_production_combined_activation=self.activation, parent_capture_artifacts=captures,
            direction_only=True)
        self.assertTrue(self.manual.validate_manual_direction_evidence(ev, captures, analysis_observed_at=self.stamp))
        plan_value = copy.deepcopy(self.base.plan)
        plan_value["evidence_binding"] = {"expected_run_id":ev["manual_run_id"], "expected_decision_as_of":ev["decision_as_of"]}
        self.evidence = ev; self.captures = captures
        self.plan_value = plan_value
        report, valid = compile_dashboard(ev, plan_value, self.base.risk, generated_at=self.stamp,
            evidence_schema_bytes=MANUAL_EVIDENCE_SCHEMA.read_bytes(),
            current_session_context=current_context(ev), current_session_authority_resolver=self.resolver,
            evidence_sha256=hashlib.sha256(evidence_raw_bytes(ev)).hexdigest(), parent_capture_artifacts=captures,
            holding_timing_inputs=self.base.inputs)
        self.assertEqual(valid["schema_errors"], [])
        self.assertEqual(valid["swing_action_contract_errors"], [])
        return report

    def timing(self, report):
        return self.base.timing_row(report)["timing_status"]

    def test_combined_confirmation_identity_through_real_projection(self):
        report = self.compile()
        self.assertEqual(self.timing(report), "VERIFIED_REDUCTION_REVIEW")
        self.base.identity.assert_not_called()
        self.assertIn("VERIFIED_REDUCTION_REVIEW", render_html(report))
        self.assertIn("VERIFIED_REDUCTION_REVIEW", render_markdown(report))
        for row in report["swing_action_plan"]["rows"]:
            self.assertIsNone(row["shadow_sell_qty"])
            self.assertIsNone(row["shadow_buy_qty"])
            self.assertEqual(row["execution_status"], "DISABLED")

    def test_unrelated_broker_mismatch_does_not_reconcile_or_block_matching_timing(self):
        before = copy.deepcopy(self.base.inputs)
        report = self.compile(holdings_change=("NBIS", 13))
        self.assertEqual(self.timing(report), "VERIFIED_REDUCTION_REVIEW")
        self.assertEqual(before, self.base.inputs)
        self.assertEqual(self.base.inputs["state"]["holdings"]["NBIS"], 15)
        self.assertNotEqual(self.evidence["broker_observed_state"], self.evidence["system_portfolio_state"])

    def test_timing_position_anchor_mismatch_stays_unverified(self):
        for kwargs in ({"holdings_change": ("MVLL", 395)}, {"holdings_change": ("MVLL", 0)}):
            with self.subTest(change=kwargs):
                self.assertEqual(self.timing(self.compile(**kwargs)), "NOT_VERIFIED")

    def test_fresh_broker_view_does_not_mutate_old_canonical_snapshot(self):
        self.base.inputs["state"]["last_confirmed_broker_snapshot"]["as_of"] = "2026-08-14"
        self.save_fixture_state()
        self.assertEqual(self.timing(self.compile()), "VERIFIED_REDUCTION_REVIEW")
        self.assertEqual(self.base.inputs["state"]["last_confirmed_broker_snapshot"]["as_of"], "2026-08-14")

    def test_bound_authority_swap_fails_closed_without_legacy_fallback(self):
        self.compile()
        manifest = json.loads(self.activation.read_text(encoding="utf-8"))
        manifest["activation_cohort_id"] = "TEST-SWAPPED"
        self.activation.write_text(json.dumps(manifest), encoding="utf-8")
        result = dashboard._holding_timing_projection(
            {"generated_at":self.stamp}, self.evidence, self.base.inputs,
            parent_capture_artifacts=self.captures, authority_resolver=self.resolver)
        self.assertEqual(result, {})
        self.base.identity.assert_not_called()

    def test_consumer_rejects_different_loader_provenance(self):
        report = self.compile()
        wrong = copy.deepcopy(self.evidence["integrated_authority_snapshot_provenance"])
        wrong["instrument_identity_artifact_sha256"] = "f" * 64
        # Only the external authority loader is substituted; its result must
        # still match consumed acquisition provenance before any timing use.
        with patch.object(dashboard, "load_production_integrated_authority_snapshot",
                          return_value=SimpleNamespace(provenance=lambda **kw: wrong)):
            self.assertEqual(dashboard._holding_timing_projection(report, self.evidence, self.base.inputs,
                parent_capture_artifacts=self.captures, authority_resolver=self.resolver), {})

    def test_future_stale_and_missing_confirmation_crosscheck_remain_blocked(self):
        before = copy.deepcopy(self.base.inputs)
        for stamp in ("2026-09-02T22:00:04+00:00", "2026-09-02T21:40:00+00:00"):
            self.base.inputs = copy.deepcopy(before)
            self.base.inputs["snapshot"]["generated_at_utc"] = stamp
            self.assertEqual(self.timing(self.compile()), "NOT_VERIFIED")
        self.base.inputs = before
        self.base.inputs["snapshot"]["symbols"]["MRVL"]["quote_crosscheck"] = None
        # Full evidence permits the approved missing-close fallback, not a stale/future input.
        report = self.compile()
        self.assertEqual(self.timing(report), "VERIFIED_REDUCTION_REVIEW")
        holding = next(r for r in report["portfolio"]["positions"] if r["ticker"] == "MVLL")
        self.assertEqual(holding["holding_timing_evidence"]["independent_close_status"], "NOT_VERIFIED")


class ManualTimingBrokerInputTests(unittest.TestCase):
    """Fresh Broker facts may feed an ephemeral timing input, never the ledger."""

    def setUp(self):
        self.case = TechnicalTimingConsumerAlignmentTests("runTest")
        self.case.setUp(); self.addCleanup(self.case.doCleanups)
        self.case.base.inputs["state"]["last_confirmed_broker_snapshot"]["as_of"] = "2026-08-14"
        self.case.save_fixture_state()

    def test_actual_broker_facts_and_timestamp_reach_evaluator_without_ledger_write(self):
        import evaluate_alerts
        state_before = copy.deepcopy(self.case.base.inputs["state"])
        canonical_before = dashboard.DEFAULT_PORTFOLIO_STATE.read_bytes()
        with patch.object(evaluate_alerts, "evaluate", wraps=evaluate_alerts.evaluate) as evaluator:
            report = self.case.compile(holdings_change=("NBIS", 13))
        self.assertEqual(self.case.timing(report), "VERIFIED_REDUCTION_REVIEW")
        self.assertTrue(evaluator.called)
        for call in evaluator.call_args_list:
            used = call.args[0]
            self.assertEqual(used["holdings"]["NBIS"], 13)
            self.assertEqual(used["position_cost_basis_usd"]["NBIS"], 1300)
            self.assertEqual(used["last_confirmed_broker_snapshot"]["as_of"], "2026-09-02")
            self.assertNotEqual(used["last_confirmed_broker_snapshot"]["as_of"], report["evidence"].get("expected_completed_us_session"))
            self.assertEqual(used["last_confirmed_broker_snapshot"]["as_of_timestamp_kst"], "2026-09-03T07:00:00+09:00")
            self.assertEqual(used["timing_plan"], state_before["timing_plan"])
        self.assertEqual(self.case.base.inputs["state"], state_before)
        self.assertEqual(dashboard.DEFAULT_PORTFOLIO_STATE.read_bytes(), canonical_before)

    def test_default_evaluator_still_rejects_old_snapshot(self):
        from evaluate_alerts import evaluate
        inputs = self.case.base.inputs
        result = evaluate(inputs["state"], inputs["policy"], inputs["snapshot"], {})
        self.assertEqual(result["state"], "STATE_MISMATCH")
        self.assertTrue(any("stale" in warning for warning in result["warnings"]))
        self.assertEqual(self.case.timing(self.case.compile()), "VERIFIED_REDUCTION_REVIEW")

    def test_stale_future_or_unbound_evidence_cannot_refresh_timing_input(self):
        import evaluate_alerts
        report = self.case.compile()
        for mode in ("stale", "future", "forged_timestamp", "missing_capture"):
            changed = copy.deepcopy(report); ev = copy.deepcopy(self.case.evidence)
            captures = self.case.captures
            if mode == "stale": changed["generated_at"] = "2026-09-02T22:16:00+00:00"
            if mode == "future": changed["generated_at"] = "2026-09-02T21:59:00+00:00"
            if mode == "forged_timestamp": ev["broker_observed_state"]["as_of"] = "2026-09-02T22:00:02+00:00"
            if mode == "missing_capture": captures = None
            with self.subTest(mode=mode), patch.object(evaluate_alerts, "evaluate", wraps=evaluate_alerts.evaluate) as evaluator:
                self.assertEqual(dashboard._holding_timing_projection(changed, ev, self.case.base.inputs,
                    parent_capture_artifacts=captures, authority_resolver=self.case.resolver), {})
                evaluator.assert_not_called()

    def test_anchor_fill_and_policy_errors_are_not_repaired_from_broker_facts(self):
        inputs = self.case.base.inputs
        original = copy.deepcopy(inputs["state"])
        for field, value in (("anchor_shares", 999), ("completed_tranche_ids", ["FAKE-FILL"])):
            inputs["state"] = copy.deepcopy(original)
            inputs["state"]["timing_plan"]["positions"]["MVLL"][field] = value
            self.case.save_fixture_state()
            self.assertEqual(self.case.timing(self.case.compile()), "NOT_VERIFIED")
        inputs["state"] = original
        inputs["state"]["strategy_version"] = "WRONG-APPROVED-POLICY"
        self.case.save_fixture_state()
        self.assertEqual(self.case.timing(self.case.compile()), "NOT_VERIFIED")

    def test_timing_position_mismatch_never_infers_a_fill(self):
        original = copy.deepcopy(self.case.base.inputs["state"]["timing_plan"])
        self.assertEqual(self.case.timing(self.case.compile(holdings_change=("MVLL", 395))), "NOT_VERIFIED")
        self.assertEqual(self.case.timing(self.case.compile(cost_change=("MVLL", 1.0))), "VERIFIED_REDUCTION_REVIEW")
        self.assertEqual(self.case.base.inputs["state"]["timing_plan"], original)

    def test_cash_is_not_promoted_and_quantities_remain_disabled(self):
        import evaluate_alerts
        with patch.object(evaluate_alerts, "evaluate", wraps=evaluate_alerts.evaluate) as evaluator:
            report = self.case.compile()
        for call in evaluator.call_args_list:
            self.assertIsNone(call.args[0]["available_cash_usd"])
            self.assertFalse(call.args[0]["last_confirmed_broker_snapshot"]["cash_verified"])
        self.assertEqual(self.case.evidence["verified_orderable_cash_usd"], 25.0)
        self.assertEqual(self.case.evidence["preflight_status"], "PARTIAL")
        self.assertEqual(self.case.evidence["broker_observed_state"]["operation_statuses"]["account_open_items"], "KIWOOM_API_RESPONSE_ERROR")
        for row in report["swing_action_plan"]["rows"]:
            for key in ("shadow_target_qty", "shadow_delta_qty", "shadow_buy_qty", "shadow_sell_qty"):
                self.assertIsNone(row[key])
            self.assertEqual(row["execution_status"], "DISABLED")


class BrokerCurrentStateAlignmentTests(unittest.TestCase):
    """Current Broker facts and historical strategy anchors have separate roles."""

    def setUp(self):
        self.case = TechnicalTimingConsumerAlignmentTests("runTest")
        self.case.setUp(); self.addCleanup(self.case.doCleanups)

    def assert_read_only(self, report, original, original_bytes):
        self.assertEqual(self.case.base.inputs["state"], original)
        self.assertEqual(dashboard.DEFAULT_PORTFOLIO_STATE.read_bytes(), original_bytes)
        for row in report["swing_action_plan"]["rows"]:
            for field in ("shadow_target_qty", "shadow_delta_qty", "shadow_buy_qty", "shadow_sell_qty"):
                self.assertIsNone(row[field])
            self.assertEqual(row["execution_status"], "DISABLED")
        swing = report["swing_action_plan"]
        self.assertFalse(swing["order_authority"])
        self.assertEqual(swing["quantity_authority"], "none")
        self.assertIsNone(swing["execution_quantity"])
        self.assertEqual(swing["broker_submission"], "disabled")

    def test_current_nbis_quantity_uses_broker_not_internal_history(self):
        original = copy.deepcopy(self.case.base.inputs["state"])
        before = dashboard.DEFAULT_PORTFOLIO_STATE.read_bytes()
        report = self.case.compile(holdings_change=("NBIS", 13))
        row = next(r for r in report["portfolio"]["positions"] if r["ticker"] == "NBIS")
        self.assertEqual(row["current_quantity"]["value"], 13)
        self.assertEqual(original["holdings"]["NBIS"], 15)
        self.assertIn("BROKER_SYSTEM_MISMATCH_BROKER_CANONICAL", report["evidence"]["warnings"])
        self.assertEqual(self.case.timing(report), "VERIFIED_REDUCTION_REVIEW")
        self.assert_read_only(report, original, before)

    def test_stale_internal_timing_quantity_does_not_override_valid_broker_and_anchor(self):
        state = self.case.base.inputs["state"]
        state["holdings"]["MVLL"] = 395
        state["last_confirmed_broker_snapshot"]["as_of"] = "2026-08-14"
        self.case.save_fixture_state()
        original = copy.deepcopy(state)
        before = dashboard.DEFAULT_PORTFOLIO_STATE.read_bytes()
        report = self.case.compile()  # Broker=396; approved anchor=396; no inferred fill.
        self.assertEqual(self.case.timing(report), "VERIFIED_REDUCTION_REVIEW")
        row = next(r for r in report["portfolio"]["positions"] if r["ticker"] == "MVLL")
        self.assertEqual(row["current_quantity"]["value"], 396)
        self.assertIn("BROKER_SYSTEM_MISMATCH_BROKER_CANONICAL", report["evidence"]["warnings"])
        self.assert_read_only(report, original, before)

    def test_fresh_broker_average_cost_does_not_require_internal_cost_match(self):
        import evaluate_alerts
        original = copy.deepcopy(self.case.base.inputs["state"])
        before = dashboard.DEFAULT_PORTFOLIO_STATE.read_bytes()
        with patch.object(evaluate_alerts, "evaluate", wraps=evaluate_alerts.evaluate) as evaluator:
            report = self.case.compile(cost_change=("MVLL", 1.0))
        self.assertEqual(self.case.timing(report), "VERIFIED_REDUCTION_REVIEW")
        self.assertTrue(evaluator.called)
        self.assertTrue(all(c.args[0]["average_cost_usd"]["MVLL"] == 1.0 for c in evaluator.call_args_list))
        self.assertIn("BROKER_SYSTEM_MISMATCH_BROKER_CANONICAL", report["evidence"]["warnings"])
        self.assert_read_only(report, original, before)

    def test_broker_quantity_conflicting_with_approved_anchor_still_blocks_timing(self):
        original = copy.deepcopy(self.case.base.inputs["state"])
        before = dashboard.DEFAULT_PORTFOLIO_STATE.read_bytes()
        report = self.case.compile(holdings_change=("MVLL", 395))
        self.assertEqual(self.case.timing(report), "NOT_VERIFIED")
        row = next(r for r in report["portfolio"]["positions"] if r["ticker"] == "MVLL")
        self.assertEqual(row["current_quantity"]["value"], 395)
        self.assert_read_only(report, original, before)


if __name__ == "__main__":
    unittest.main()


class ManualKiwoomOnlyTimingTests(unittest.TestCase):
    """K3 scope through real acquisition replay, calculator and Dashboard."""

    def setUp(self):
        from datetime import datetime, timedelta
        from build_kiwoom_market_snapshot import normalize_series
        from kiwoom_replay_validation import calculate_kiwoom_technical
        self.case = TechnicalTimingConsumerAlignmentTests("runTest")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.snapshot = self.case.base.inputs["snapshot"]
        self.doc = {"run_id": self.case.doc["run_id"], "started_at": "2026-09-02T21:59:59+00:00",
                    "observed_at": "2026-09-02T22:00:00+00:00", "requests": [], "results": []}
        end = datetime(2026, 9, 1)
        days = []
        day = end
        while len(days) < 260:
            if day.weekday() < 5:
                days.append(day.strftime("%Y%m%d"))
            day -= timedelta(days=1)
        days.reverse()
        for symbol in ("MVLL", "MRVL", "SOXL", "SOXX"):
            data = []
            for i, date in enumerate(days):
                close = 100 + i * 0.1
                if i >= 257:
                    close = {257: 126.0, 258: 127.0, 259: 130.0}[i]
                opening = float(data[-1]["cur_prc"]) + .1 if data else close
                data.append({"dt": date, "open_pric": str(opening), "high_pric": str(max(opening, close) + 1),
                             "low_pric": str(min(opening, close) - 1), "cur_prc": str(close),
                             "acc_trde_qty": str(500000 + i)})
            series = {}
            for basis in ("RAW", "ADJUSTED"):
                selected = data[-30:] if basis == "RAW" else data
                query = {"operation": "daily_chart", "ticker": symbol, "fx_applied": False,
                         "completed_session": "2026-09-01", "price_basis": basis}
                pagination = {"api_id": "usa06012", "status": "SUFFICIENT", "pages_fetched": 1,
                              "pages": [{"page_index": 1, "api_id": "usa06012",
                                         "retrieved_at": self.doc["observed_at"]}]}
                response = {"operation": "daily_chart", "ticker": symbol, "requested_price_basis": basis,
                            "bridge_status": "PASS", "order_authority": False,
                            "retrieved_at": self.doc["observed_at"], "data": copy.deepcopy(selected),
                            "pagination": pagination}
                self.doc["requests"].append(query); self.doc["results"].append(response)
                series[basis] = normalize_series(selected, ticker=symbol, completed_session="2026-09-01",
                    price_basis=basis, minimum_history_bars=252 if basis == "ADJUSTED" else 1, pagination=pagination)
            result = calculate_kiwoom_technical(series["RAW"], series["ADJUSTED"],
                cutoff="2026-09-01", minimum_history_bars=252, include_timing_record=True)
            self.assertEqual(result["status"], "KIWOOM_TECHNICAL_VALIDATED")
            record = result["timing_record"]
            record["corporate_action_unresolved"] = False  # Synthetic resolved external input, not producer approval.
            self.snapshot["symbols"][symbol] = record
            for response in self.case.doc["results"]:
                if response["operation"] == "daily_chart" and response["ticker"] == symbol:
                    for bar in response["data"]:
                        bar.update(cur_prc=record["close"], open_pric=record["close"],
                                   high_pric=record["close"] + 1,
                                   low_pric=record["close"] - 1)
        technical_raw = {r["ticker"]: r for r in self.doc["results"]
                         if r["requested_price_basis"] == "RAW"}
        for response in self.case.doc["results"]:
            if response["operation"] == "daily_chart" and response["ticker"] in technical_raw:
                matching = next(row for row in technical_raw[response["ticker"]]["data"]
                                if row["dt"] == response["data"][-1]["dt"])
                response["data"][-1] = copy.deepcopy(matching)
        self.bind()

    def bind(self):
        self.doc["request_sha256"] = self.case.manual.canonical_hash(self.doc["requests"])
        raw = json.dumps(self.doc, sort_keys=True).encode()
        self.case.base.inputs["capture_artifacts"] = [(raw, hashlib.sha256(raw).hexdigest())]
        _attach_ca_fixture(self)

    def timing(self, **kwargs):
        report = self.case.compile(**kwargs)
        return self.case.timing(report), report

    def test_fresh_bound_missing_close_is_visible_and_unsized(self):
        from datetime import datetime
        from validate_technical_snapshot import validate_manual_kiwoom_snapshot
        state_before = copy.deepcopy(self.case.base.inputs["state"])
        status, report = self.timing(holdings_change=("NBIS", 13))
        self.assertEqual(status, "VERIFIED_REDUCTION_REVIEW")
        local = self.case.evidence["manual_analysis_view"]
        self.assertEqual(local["provider_finalization_verified"], "NOT_VERIFIED")
        self.assertEqual(local["local_regular_bar_coherence"]["MVLL"]["status"], "PASS")
        validation = validate_manual_kiwoom_snapshot(
            self.snapshot, required_symbols=["MVLL", "MRVL"],
            expected_session_date="2026-09-01",
            capture_artifacts=self.case.base.inputs["capture_artifacts"],
            run_id=self.case.evidence["manual_run_id"],
            decision_as_of=self.case.evidence["decision_as_of"],
            analysis_observed_at=report["generated_at"],
            policy=self.case.base.inputs["policy"],
            corporate_action_artifacts=self.case.base.inputs["corporate_action_artifacts"],
            closed_at=[datetime.fromisoformat("2026-09-01T20:00:00+00:00")] * 2,
        )
        self.assertEqual(validation["provider_finalization_verified"], "NOT_VERIFIED")
        self.assertEqual(validation["local_regular_bar_coherence"], "PASS")
        self.assertEqual(validation["technical_analysis_eligibility"], "YES")
        self.assertEqual(report["evidence"]["provider_finalization_verified"], "NOT_VERIFIED")
        self.assertEqual(report["evidence"]["local_regular_bar_coherence"], "PASS")
        self.assertEqual(report["evidence"]["technical_analysis_eligibility"], "YES")
        row = next(p for p in report["portfolio"]["positions"] if p["ticker"] == "MVLL")
        self.assertEqual(row["holding_timing_evidence"]["independent_close_status"], "NOT_VERIFIED")
        self.assertEqual(row["holding_timing_evidence"]["timing_source_mode"], "KIWOOM_ONLY")
        for text in (json.dumps(report), render_html(report), render_markdown(report)):
            self.assertIn("KIWOOM_ONLY", text)
            self.assertIn("PROVIDER_FINALIZATION=NOT_VERIFIED", text)
        for row in report["swing_action_plan"]["rows"]:
            for key in ("shadow_target_qty", "shadow_delta_qty", "shadow_buy_qty", "shadow_sell_qty"):
                self.assertIsNone(row[key])
            self.assertEqual(row["execution_status"], "DISABLED")
        self.assertEqual(self.case.base.inputs["state"], state_before)
        self.assertFalse(report["authority"]["broker_order_authority"])
        self.assertIsNone(report["authority"]["execution_quantity"])
        self.assertEqual(report["swing_action_plan"]["quantity_authority"], "none")
        self.assertEqual(report["swing_action_plan"]["broker_submission"], "disabled")
        self.assertEqual(report["swing_action_plan"]["order_authority"], False)
        out = write_run(report, {}, output_root=Path(self.case.base.temp.name)/"k3-result",
                        source_paths={}, implementation_paths=[], root=Path(self.case.base.temp.name))
        self.assertIn("KIWOOM_ONLY", (out/"portfolio-decision.json").read_text(encoding="utf-8"))

    def test_parent_vs_technical_raw_high_conflict_blocks_local_timing(self):
        parent = next(r for r in self.case.doc["results"]
                      if r["operation"] == "daily_chart" and r["ticker"] == "MVLL")
        technical = next(r for r in self.doc["results"]
                         if r["ticker"] == "MVLL" and r["requested_price_basis"] == "RAW")
        self.assertEqual(parent["data"][-1]["cur_prc"], technical["data"][-1]["cur_prc"])
        parent["data"][-1]["high_pric"] = str(float(parent["data"][-1]["high_pric"]) + 7)
        status, report = self.timing()
        self.assertEqual(status, "NOT_VERIFIED")
        self.assertEqual(self.case.evidence["manual_analysis_view"]
                         ["local_regular_bar_coherence"]["MVLL"]["status"], "PASS")
        self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")
        self.assertNotEqual(report["evidence"].get("local_regular_bar_coherence"), "PASS")

    def test_verified_independent_close_cannot_bypass_raw_high_conflict(self):
        for symbol in self.snapshot["symbols"]:
            self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
        parent = next(r for r in self.case.doc["results"]
                      if r["operation"] == "daily_chart" and r["ticker"] == "MVLL")
        technical = next(r for r in self.doc["results"]
                         if r["ticker"] == "MVLL" and r["requested_price_basis"] == "RAW")
        self.assertEqual(parent["data"][-1]["cur_prc"], technical["data"][-1]["cur_prc"])
        parent["data"][-1]["high_pric"] = str(float(parent["data"][-1]["high_pric"]) + 7)
        status, report = self.timing()
        self.assertEqual(status, "NOT_VERIFIED")
        self.assertNotEqual(report["evidence"].get("local_regular_bar_coherence"), "PASS")
        self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")

    def test_ca_confirmation_required_with_or_without_independent_close(self):
        original = copy.deepcopy(self.snapshot)
        for independent in (False, True):
            for symbol in ("MVLL", "MRVL"):
                for value in (None, True, "False"):
                    with self.subTest(independent=independent, symbol=symbol, value=value):
                        self.snapshot.clear(); self.snapshot.update(copy.deepcopy(original))
                        if independent:
                            for ticker in self.snapshot["symbols"]:
                                self.snapshot["symbols"][ticker]["quote_crosscheck"] = self.crosscheck(ticker)
                        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
                        row = self.snapshot["symbols"][symbol]
                        if value is None:
                            row.pop("corporate_action_unresolved")
                        else:
                            row["corporate_action_unresolved"] = value
                        status, report = self.timing()
                        self.assertEqual(status, "NOT_VERIFIED")
                        self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")

    def test_verified_independent_close_cannot_bypass_future_technical_raw(self):
        import evaluate_alerts
        from run_manual_portfolio_analysis import _parent_capture_evidence, local_regular_bar_coherence
        for symbol in self.snapshot["symbols"]:
            self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
        response = next(r for r in self.doc["results"]
                        if r["ticker"] == "MVLL" and r["requested_price_basis"] == "RAW")
        response["retrieved_at"] = "2026-09-02T22:00:04+00:00"
        self.bind()
        captures = _parent_capture_evidence(self.case.base.inputs["capture_artifacts"],
            run_id=self.doc["run_id"], observed_at=self.case.stamp)
        request = next(r for r in self.doc["requests"]
                       if r["ticker"] == "MVLL" and r["price_basis"] == "RAW")
        local = local_regular_bar_coherence(response, request=request, captures=captures,
            expected_completed_session="2026-09-01", core_close_at="2026-09-01T20:00:00+00:00",
            observed_at=self.case.stamp)
        self.assertEqual(local["status"], "FAIL")
        self.assertEqual(local["reason"], "LOCAL_BAR_RETRIEVAL_TIME_INVALID")
        events = []
        real_evaluate = evaluate_alerts.evaluate
        def observe(*args, **kwargs):
            result = real_evaluate(*args, **kwargs)
            events.extend(result.get("candidates") or [])
            return result
        with patch.object(evaluate_alerts, "evaluate", side_effect=observe):
            status, report = self.timing()
        self.assertTrue(any(e.get("symbol") == "MVLL" and e.get("event_type") == "holding_timing_review"
                            for e in events))
        self.assertEqual(status, "NOT_VERIFIED")
        self.assertNotEqual(report["evidence"].get("local_regular_bar_coherence"), "PASS")
        self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")

    def test_explicit_invalid_technical_capture_cannot_use_legacy_path(self):
        import evaluate_alerts
        for symbol in self.snapshot["symbols"]:
            self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
        inputs = self.case.base.inputs
        valid_capture = inputs.pop("capture_artifacts")
        ordinary_events = []
        real_evaluate = evaluate_alerts.evaluate
        def observe(*args, **kwargs):
            evaluated = real_evaluate(*args, **kwargs)
            ordinary_events.extend(evaluated.get("candidates") or [])
            return evaluated
        with patch.object(evaluate_alerts, "evaluate", side_effect=observe):
            # P1/P2: an ordinary event cannot replace absent technical history.
            self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        self.assertTrue(any(event.get("symbol") == "MVLL"
                            and event.get("event_type") == "holding_timing_review"
                            for event in ordinary_events))
        for supplied in ([], None, {}, "", False, 0, [b"invalid-entry"]):
            with self.subTest(supplied=supplied):
                inputs["capture_artifacts"] = supplied
                status, report = self.timing()
                self.assertEqual(status, "NOT_VERIFIED")
                self.assertNotEqual(report["evidence"].get("local_regular_bar_coherence"), "PASS")
                self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")
                row = next(row for row in report["swing_action_plan"]["rows"] if row["ticker"] == "MVLL")
                self.assertEqual(row["candidate_direction"], "TRIM")
                self.assertEqual(row["execution_status"], "DISABLED")
        inputs["capture_artifacts"] = valid_capture
        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")

    def test_raw_and_adjusted_response_provider_binding_is_symmetric(self):
        import evaluate_alerts
        for independent in (False, True):
            if independent:
                for symbol in self.snapshot["symbols"]:
                    self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
            self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
            for basis in ("RAW", "ADJUSTED"):
                response = next(row for row in self.doc["results"]
                                if row["ticker"] == "MVLL"
                                and row["requested_price_basis"] == basis)
                for accepted in (None, "KIWOOM_REST"):
                    with self.subTest(independent=independent, basis=basis, accepted=accepted):
                        if accepted is None:
                            response.pop("source_provider", None)
                        else:
                            response["source_provider"] = accepted
                        self.bind()
                        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
                response["source_provider"] = "OTHER_PROVIDER"
                self.bind()
                ordinary_events = []
                real_evaluate = evaluate_alerts.evaluate
                def observe(*args, **kwargs):
                    evaluated = real_evaluate(*args, **kwargs)
                    ordinary_events.extend(evaluated.get("candidates") or [])
                    return evaluated
                with self.subTest(independent=independent, basis=basis, provider="OTHER_PROVIDER"):
                    with patch.object(evaluate_alerts, "evaluate", side_effect=observe):
                        status, report = self.timing()
                    if independent:
                        self.assertTrue(any(event.get("symbol") == "MVLL"
                                            and event.get("event_type") == "holding_timing_review"
                                            for event in ordinary_events))
                    self.assertEqual(status, "NOT_VERIFIED")
                    self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")
                response.pop("source_provider")
                self.bind()

    def test_t01_adjusted_latest_page_time_and_row_binding(self):
        from datetime import datetime
        from validate_technical_snapshot import validate_manual_kiwoom_snapshot
        original = copy.deepcopy(self.doc)
        close = "2026-09-01T20:00:00+00:00"

        def validation():
            return validate_manual_kiwoom_snapshot(
                self.snapshot, required_symbols=["MVLL", "MRVL"],
                expected_session_date="2026-09-01",
                capture_artifacts=self.case.base.inputs["capture_artifacts"],
                run_id=self.doc["run_id"], decision_as_of=self.case.doc["observed_at"],
                analysis_observed_at=self.case.stamp,
                policy=self.case.base.inputs["policy"],
                corporate_action_artifacts=self.case.base.inputs["corporate_action_artifacts"],
                closed_at=[datetime.fromisoformat(close)] * 2,
            )

        for independent in (False, True):
            self.doc = copy.deepcopy(original)
            if independent:
                for symbol in self.snapshot["symbols"]:
                    self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
            self.doc["started_at"] = "2026-09-01T19:59:58+00:00"
            adjusted = next(response for response in self.doc["results"]
                            if response["ticker"] == "MVLL"
                            and response["requested_price_basis"] == "ADJUSTED")
            self.assertEqual(adjusted["data"][-1]["dt"], "20260901")
            page = adjusted["pagination"]["pages"][0]
            page.update(row_count=len(adjusted["data"]),
                        first_session=adjusted["data"][0]["dt"],
                        last_session="20260901")
            page["retrieved_at"] = "2026-09-01T19:59:59+00:00"
            self.bind()
            with self.subTest(independent=independent, case="N1_PRE_CLOSE"):
                self.assertNotEqual(validation()["technical_analysis_eligibility"], "YES")
                status, report = self.timing()
                self.assertEqual(status, "NOT_VERIFIED")
                self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")

            for retrieved in (close, "2026-09-01T20:00:01+00:00"):
                page["retrieved_at"] = retrieved
                self.bind()
                with self.subTest(independent=independent, case="P1_POST_CLOSE", retrieved=retrieved):
                    self.assertEqual(validation()["technical_analysis_eligibility"], "YES")
                    self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")

            prior, latest = adjusted["data"][:-1], adjusted["data"][-1:]
            adjusted["pagination"]["pages"] = [
                {"page_index": 1, "api_id": "usa06012", "row_count": len(prior),
                 "first_session": prior[0]["dt"], "last_session": prior[-1]["dt"],
                 "retrieved_at": "2026-09-01T19:59:59+00:00"},
                {"page_index": 2, "api_id": "usa06012", "row_count": len(latest),
                 "first_session": latest[0]["dt"], "last_session": latest[-1]["dt"],
                 "retrieved_at": "2026-09-01T20:00:01+00:00"},
            ]
            adjusted["pagination"]["pages_fetched"] = 2
            self.bind()
            with self.subTest(independent=independent, case="P2_HISTORICAL_PRE_CLOSE"):
                self.assertEqual(validation()["technical_analysis_eligibility"], "YES")
                self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")

            for field, value in (("last_session", "20260901"), ("row_count", None)):
                saved = adjusted["pagination"]["pages"][0].get(field)
                if value is None:
                    adjusted["pagination"]["pages"][0].pop(field)
                else:
                    adjusted["pagination"]["pages"][0][field] = value
                self.bind()
                with self.subTest(independent=independent, case="N2_AMBIGUOUS", field=field):
                    self.assertNotEqual(validation()["technical_analysis_eligibility"], "YES")
                    self.assertEqual(self.timing()[0], "NOT_VERIFIED")
                adjusted["pagination"]["pages"][0][field] = saved

    def test_required_timing_gate_failure_overrides_valid_success_event(self):
        import evaluate_alerts

        for symbol in self.snapshot["symbols"]:
            self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
        baseline_doc = copy.deepcopy(self.doc)
        baseline_parent = copy.deepcopy(self.case.doc)
        baseline_snapshot = copy.deepcopy(self.snapshot)
        real_evaluate = evaluate_alerts.evaluate
        evaluations = []

        def observe_baseline(*args, **kwargs):
            result = real_evaluate(*args, **kwargs)
            evaluations.append(copy.deepcopy(result))
            return result

        with patch.object(evaluate_alerts, "evaluate", side_effect=observe_baseline):
            self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
        success_evaluation = next(result for result in evaluations
                                  if any(event.get("symbol") == "MVLL"
                                         and event.get("event_type") == "holding_timing_review"
                                         for event in result.get("candidates") or []))

        def technical(basis):
            return next(row for row in self.doc["results"]
                        if row["ticker"] == "MVLL" and row["requested_price_basis"] == basis)

        def damage(case):
            if case == "EMPTY_CAPTURE":
                self.case.base.inputs["capture_artifacts"] = []
            elif case == "MALFORMED_CAPTURE":
                self.case.base.inputs["capture_artifacts"] = [b"invalid-entry"]
            elif case in ("RAW_PROVIDER", "ADJUSTED_PROVIDER"):
                technical("RAW" if case == "RAW_PROVIDER" else "ADJUSTED")["source_provider"] = "OTHER_PROVIDER"
                self.bind()
            elif case == "CA_MISSING":
                self.snapshot["symbols"]["MVLL"].pop("corporate_action_unresolved")
            elif case == "CA_UNRESOLVED":
                self.snapshot["symbols"]["MVLL"]["corporate_action_unresolved"] = True
            elif case in ("FUTURE_RAW", "FUTURE_ADJUSTED"):
                technical("RAW" if case == "FUTURE_RAW" else "ADJUSTED")["retrieved_at"] = "2026-09-02T22:00:04+00:00"
                self.bind()
            elif case == "PRE_CLOSE_ADJUSTED_PAGE":
                self.doc["started_at"] = "2026-09-01T19:59:58+00:00"
                technical("ADJUSTED")["pagination"]["pages"][0]["retrieved_at"] = "2026-09-01T19:59:59+00:00"
                self.bind()
            elif case == "PARENT_TECHNICAL_OHLCV":
                parent = next(row for row in self.case.doc["results"]
                              if row["operation"] == "daily_chart" and row["ticker"] == "MVLL")
                parent["data"][-1]["high_pric"] = str(float(parent["data"][-1]["high_pric"]) + 7)
            elif case == "HASH_MISMATCH":
                raw, _ = self.case.base.inputs["capture_artifacts"][0]
                self.case.base.inputs["capture_artifacts"] = [(raw, "0" * 64)]
            elif case == "PAGE_MISMATCH":
                technical("ADJUSTED")["pagination"]["pages"][0]["page_index"] = 2
                self.bind()

        cases = ("EMPTY_CAPTURE", "MALFORMED_CAPTURE", "RAW_PROVIDER", "ADJUSTED_PROVIDER",
                 "CA_MISSING", "CA_UNRESOLVED", "FUTURE_RAW", "FUTURE_ADJUSTED",
                 "PRE_CLOSE_ADJUSTED_PAGE", "PARENT_TECHNICAL_OHLCV", "HASH_MISMATCH",
                 "PAGE_MISMATCH")
        for independent in (True, False):
            for case in cases:
                with self.subTest(independent=independent, case=case):
                    self.doc = copy.deepcopy(baseline_doc)
                    self.case.doc = copy.deepcopy(baseline_parent)
                    self.case.base.inputs["snapshot"] = copy.deepcopy(baseline_snapshot)
                    self.snapshot = self.case.base.inputs["snapshot"]
                    if not independent:
                        for row in self.snapshot["symbols"].values():
                            row.pop("quote_crosscheck")
                    self.bind()
                    damage(case)
                    # Hold the real baseline evaluator success constant even when an
                    # invalid capture would stop evaluation before that call.
                    with patch.object(evaluate_alerts, "evaluate",
                                      return_value=copy.deepcopy(success_evaluation)):
                        status, report = self.timing()
                    self.assertEqual(status, "NOT_VERIFIED")
                    self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")
                    self.assertNotEqual(report["evidence"].get("local_regular_bar_coherence"), "PASS")
                    self.assertFalse(report["swing_action_plan"]["order_authority"])
                    self.assertEqual(report["swing_action_plan"]["quantity_authority"], "none")
                    self.assertIsNone(report["swing_action_plan"]["execution_quantity"])
                    self.assertEqual(report["swing_action_plan"]["broker_submission"], "disabled")

    def test_cj01_absent_capture_required_ca_blocks_ordinary_event(self):
        import evaluate_alerts

        for symbol in self.snapshot["symbols"]:
            self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
        self.case.base.inputs.pop("capture_artifacts")
        baseline = copy.deepcopy(self.snapshot)
        # P1/P2: absence itself is insufficient, even before the CA row mutation.
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        real_evaluate = evaluate_alerts.evaluate
        for symbol, value in (("MRVL", True), ("MRVL", None), ("MRVL", "False"),
                              ("MVLL", None)):
            with self.subTest(symbol=symbol, value=value):
                self.case.base.inputs["snapshot"] = copy.deepcopy(baseline)
                self.snapshot = self.case.base.inputs["snapshot"]
                if value is None:
                    self.snapshot["symbols"][symbol].pop("corporate_action_unresolved")
                else:
                    self.snapshot["symbols"][symbol]["corporate_action_unresolved"] = value
                events = []

                def observe(*args, **kwargs):
                    result = real_evaluate(*args, **kwargs)
                    events.extend(result.get("candidates") or [])
                    return result

                with patch.object(evaluate_alerts, "evaluate", side_effect=observe):
                    status, report = self.timing()
                self.assertTrue(any(item.get("symbol") == "MVLL"
                                    and item.get("event_type") == "holding_timing_review"
                                    for item in events))
                self.assertEqual(status, "NOT_VERIFIED")
                self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")

    def test_cj02_absent_capture_parent_snapshot_ohlcv_conflict(self):
        import evaluate_alerts

        for symbol in self.snapshot["symbols"]:
            self.snapshot["symbols"][symbol]["quote_crosscheck"] = self.crosscheck(symbol)
        self.case.base.inputs.pop("capture_artifacts")
        baseline_parent = copy.deepcopy(self.case.doc)
        # Parent-only RAW equality is not a complete technical evidence path.
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        real_evaluate = evaluate_alerts.evaluate
        changes = (("open_pric", 0.1), ("high_pric", 7.0),
                   ("low_pric", -1.0), ("cur_prc", -1.0),
                   ("acc_trde_qty", 1.0))
        for field, delta in changes:
            with self.subTest(field=field):
                self.case.doc = copy.deepcopy(baseline_parent)
                parent = next(row for row in self.case.doc["results"]
                              if row["operation"] == "daily_chart" and row["ticker"] == "MVLL")
                bar = parent["data"][-1]
                bar[field] = str(float(bar[field]) + delta)
                events = []

                def observe(*args, **kwargs):
                    result = real_evaluate(*args, **kwargs)
                    events.extend(result.get("candidates") or [])
                    return result

                with patch.object(evaluate_alerts, "evaluate", side_effect=observe):
                    status, report = self.timing()
                self.assertTrue(any(item.get("symbol") == "MVLL"
                                    and item.get("event_type") == "holding_timing_review"
                                    for item in events))
                self.assertEqual(status, "NOT_VERIFIED")
                self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")


    def test_public_validator_and_scheduled_evaluator_stay_strict(self):
        from validate_technical_snapshot import validate_snapshot
        from evaluate_alerts import evaluate
        result = validate_snapshot(self.snapshot, required_symbols=["MVLL", "MRVL"])
        self.assertEqual(result["status"], "rejected")
        result = evaluate(self.case.base.inputs["state"], self.case.base.inputs["policy"], self.snapshot, {})
        self.assertFalse(any(x.get("event_type") == "holding_timing_review" and x.get("grade") == "B"
                             for x in result["candidates"]))

    def test_buy_add_and_nonmanual_projection_do_not_inherit_exception(self):
        report = self.case.compile()
        for mode in ("HISTORICAL_REPLAY", "POST_SELL_RECOMPILE"):
            bad = copy.deepcopy(report); bad["compile_mode"] = mode
            self.assertEqual(dashboard._holding_timing_projection(bad, self.case.evidence, self.case.base.inputs,
                parent_capture_artifacts=self.case.captures, authority_resolver=self.case.resolver), {})
        ev = copy.deepcopy(self.case.evidence); ev["run_mode"] = "SCHEDULED"
        self.assertEqual(dashboard._holding_timing_projection(report, ev, self.case.base.inputs,
            parent_capture_artifacts=self.case.captures, authority_resolver=self.case.resolver), {})
        for action in ("ADD", "BUY", "HOLD", "EXIT"):
            bad = copy.deepcopy(report)
            next(p for p in bad["portfolio"]["positions"] if p["ticker"] == "MVLL")["action"] = action
            self.assertNotIn("MVLL", dashboard._holding_timing_projection(
                bad, self.case.evidence, self.case.base.inputs, parent_capture_artifacts=self.case.captures,
                authority_resolver=self.case.resolver))

    def test_local_claim_cannot_unlock_buy_add_or_order_intent(self):
        from test_portfolio_decision_order_intent import OrderIntentOnlyTests, source_for_buy, buy_plan
        case = OrderIntentOnlyTests("runTest")
        case.setUp()
        source = source_for_buy()
        source["finalized_bar_preflight_status"] = "FAIL"
        source["last_verified_finalized_bar_status"] = "NOT_VERIFIED"
        source["manual_analysis_view"].update(
            provider_finalization_verified="NOT_VERIFIED",
            local_regular_bar_coherence={"JPM": {"status": "PASS"}},
        )
        plan_value = buy_plan()
        with patch.object(dashboard, "ROOT", ROOT):
            report, validation = case.compile_dashboard(source, plan_value)
            artifact = case.build(source, plan_value)
        self.assertIn("FINALIZED_BAR_PREFLIGHT_NOT_PASS", report["evidence"]["canonical_gate_blockers"])
        self.assertEqual(report["stage2"]["buy_advisories"], [])
        self.assertNotEqual(artifact["run_state"], "ORDER_INSTRUCTION_READY")
        self.assertTrue(all(item["state"] != "ORDER_INSTRUCTION_READY"
                            for item in artifact["instructions"]))

    def test_future_stale_and_session_mismatch_rejected(self):
        before = copy.deepcopy(self.snapshot)
        for value in ("2026-09-02T22:00:04+00:00", "2026-09-02T21:40:00+00:00"):
            self.snapshot["generated_at_utc"] = value
            self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        self.snapshot.clear(); self.snapshot.update(before)
        self.snapshot["session"]["us_session_date"] = "2026-08-31"
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")

    def test_producer_source_corporate_history_and_value_fail_closed(self):
        row = self.snapshot["symbols"]["MVLL"]; before = copy.deepcopy(row)
        for field, value in (("source_provider", "YFINANCE"), ("corporate_action_unresolved", True),
                             ("history_rows", 1), ("ema20", 999), ("technical_price_basis", "RAW")):
            row.clear(); row.update(before); row[field] = value
            with self.subTest(field=field):
                self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        row.clear(); row.update(before)

    def test_local_raw_pass_does_not_clear_ca_or_timing_gates(self):
        from datetime import datetime
        from validate_technical_snapshot import validate_manual_kiwoom_snapshot
        def validate():
            return validate_manual_kiwoom_snapshot(
                self.snapshot, required_symbols=["MVLL", "MRVL"],
                expected_session_date="2026-09-01",
                capture_artifacts=self.case.base.inputs["capture_artifacts"],
                run_id=self.case.doc["run_id"],
                decision_as_of=self.case.doc["observed_at"], analysis_observed_at=self.case.stamp,
                policy=self.case.base.inputs["policy"],
            corporate_action_artifacts=self.case.base.inputs["corporate_action_artifacts"],
                closed_at=[datetime.fromisoformat("2026-09-01T20:00:00+00:00")] * 2,
            )
        row = self.snapshot["symbols"]["MVLL"]
        original = copy.deepcopy(row)
        row["corporate_action_unresolved"] = True
        ca = validate()
        self.assertEqual(ca["local_regular_bar_coherence"], "PASS")
        self.assertEqual(ca["technical_analysis_eligibility"], "NO")
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        row.clear(); row.update(original)
        row["ema20"] = 999
        timing = validate()
        self.assertEqual(timing["local_regular_bar_coherence"], "PASS")
        self.assertEqual(timing["technical_analysis_eligibility"], "NO")
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")

    def test_invalid_raw_close_below_low_blocks_local_and_technical(self):
        from datetime import datetime
        from validate_technical_snapshot import validate_manual_kiwoom_snapshot
        raw = next(response for response in self.doc["results"]
                   if response["ticker"] == "MVLL"
                   and response["requested_price_basis"] == "RAW")
        raw["data"][-1]["cur_prc"] = "1"
        self.bind()
        validation = validate_manual_kiwoom_snapshot(
            self.snapshot, required_symbols=["MVLL", "MRVL"],
            expected_session_date="2026-09-01",
            capture_artifacts=self.case.base.inputs["capture_artifacts"],
            run_id=self.case.doc["run_id"], decision_as_of=self.case.doc["observed_at"],
            analysis_observed_at=self.case.stamp, policy=self.case.base.inputs["policy"],
            closed_at=[datetime.fromisoformat("2026-09-01T20:00:00+00:00")] * 2,
        )
        self.assertEqual(validation["local_regular_bar_coherence"], "FAIL")
        self.assertEqual(validation["technical_analysis_eligibility"], "NO")
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")

    def test_request_binding_basis_pages_and_time_rejected(self):
        original = copy.deepcopy(self.doc)
        changes = [
            lambda d: d["requests"][0].update(price_basis="ADJUSTED"),
            lambda d: d["requests"][0].update(ticker="NBIS"),
            lambda d: d["results"][0].update(bridge_status="KIWOOM_API_RESPONSE_ERROR"),
            lambda d: d["results"][0].update(retrieved_at="2026-09-02T21:00:00+00:00"),
            lambda d: d["results"][0].update(retrieved_at="2026-09-02T22:00:04+00:00"),
            lambda d: d["results"][0]["pagination"]["pages"][0].update(page_index=2),
            lambda d: d["results"][1].update(data=d["results"][1]["data"][-10:]),
        ]
        for change in changes:
            self.doc = copy.deepcopy(original); change(self.doc); self.bind()
            self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        self.doc = original; self.bind()
        raw, _ = self.case.base.inputs["capture_artifacts"][0]
        self.case.base.inputs["capture_artifacts"] = [(raw, "0"*64)]
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")

    def test_malformed_pagination_defers_timing_without_aborting_direction(self):
        original = copy.deepcopy(self.doc)
        cases = ["SYNTHETIC_BAD_PAGINATION", [],
                 {**original["results"][0]["pagination"], "pages": [None]},
                 {**original["results"][0]["pagination"], "pages": ["SYNTHETIC_BAD_PAGE"]}]
        for bad in cases:
            with self.subTest(bad_type=type(bad).__name__):
                self.doc = copy.deepcopy(original)
                self.doc["results"][0]["pagination"] = copy.deepcopy(bad)
                self.bind()
                status, report = self.timing()
                self.assertEqual(status, "NOT_VERIFIED")
                row = next(r for r in report["swing_action_plan"]["rows"] if r["ticker"] == "MVLL")
                self.assertEqual(row["candidate_direction"], "TRIM")
                self.assertEqual(row["execution_status"], "DISABLED")
                self.assertIsNone(row["shadow_sell_qty"])
                self.assertNotIn("SYNTHETIC_BAD", json.dumps(report))

    def crosscheck(self, symbol, delta=0):
        row = self.snapshot["symbols"][symbol]
        return {"status":"verified", "independent_of_builder":True, "bar_date":row["bar_date"],
                "source":"SYNTHETIC_INDEPENDENT", "source_url":"https://example.invalid/fixture",
                "verified_at_utc":"2026-09-02T22:00:00+00:00", "completed_close":row["close"]+delta,
                "difference_usd":abs(delta), "tolerance_usd":max(.05, .001*row["close"])}

    def test_present_conflict_and_malformed_are_not_missing(self):
        row = self.snapshot["symbols"]["MVLL"]
        for value in (self.crosscheck("MVLL", 2), {"status":"CONFLICT"}, {"status":"NOT_VERIFIED","completed_close":1},
                      {"status":"verified"}, {"status":"pending","source":"synthetic"}):
            row["quote_crosscheck"] = value
            self.assertEqual(self.timing()[0], "NOT_VERIFIED")

    def test_valid_independent_confirmation_legacy_and_mixed_preserved(self):
        self.snapshot["symbols"]["MVLL"]["quote_crosscheck"] = self.crosscheck("MVLL")
        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
        self.snapshot["symbols"]["MRVL"]["quote_crosscheck"] = self.crosscheck("MRVL")
        _, report = self.timing()
        row = next(p for p in report["portfolio"]["positions"] if p["ticker"] == "MVLL")
        self.assertNotIn("timing_source_mode", row["holding_timing_evidence"])

    def test_missing_capture_policy_and_anchor_do_not_pass(self):
        inputs = self.case.base.inputs; saved = copy.deepcopy(inputs)
        inputs.pop("capture_artifacts")
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        inputs.update(saved)
        inputs["policy"]["holding_timing_rules"]["second_quote_crosscheck"].pop("manual_existing_holding_exception")
        dashboard.DEFAULT_ALERT_POLICY.write_text(json.dumps(inputs["policy"]),encoding="utf-8")
        self.assertEqual(self.timing()[0], "NOT_VERIFIED")
        inputs.update(saved)
        dashboard.DEFAULT_ALERT_POLICY.write_text(json.dumps(inputs["policy"]),encoding="utf-8")
        self.assertEqual(self.timing(holdings_change=("MVLL", 395))[0], "NOT_VERIFIED")

    def test_secret_and_derived_claims_not_projected(self):
        self.doc["results"][0]["synthetic_secret"] = "SYNTHETIC_SECRET_NOT_REAL"
        self.bind()
        _, report = self.timing()
        for text in (json.dumps(report), render_html(report), render_markdown(report)):
            self.assertNotIn("SYNTHETIC_SECRET_NOT_REAL", text)
        forged = copy.deepcopy(report)
        row = next(p for p in forged["portfolio"]["positions"] if p["ticker"] == "MVLL")
        row["holding_timing_evidence"]["independent_close_status"] = "VERIFIED"
        with self.assertRaises(ContractError):
            render_markdown(forged)

    def test_soxl_reduction_uses_same_guarded_path(self):
        from build_kiwoom_market_snapshot import normalize_series
        from kiwoom_replay_validation import calculate_kiwoom_technical
        for symbol in ("SOXL", "SOXX"):
            series = {}
            for response in self.doc["results"]:
                if response["ticker"] != symbol:
                    continue
                response["data"][-1].update(cur_prc="100", low_pric="99")
                basis = response["requested_price_basis"]
                series[basis] = normalize_series(response["data"], ticker=symbol,
                    completed_session="2026-09-01", price_basis=basis,
                    minimum_history_bars=252 if basis == "ADJUSTED" else 1,
                    pagination=response["pagination"])
            record = calculate_kiwoom_technical(series["RAW"], series["ADJUSTED"],
                cutoff="2026-09-01", minimum_history_bars=252, include_timing_record=True)["timing_record"]
            record["corporate_action_unresolved"] = False
            self.snapshot["symbols"][symbol] = record
            for response in self.case.doc["results"]:
                if response.get("ticker") == symbol and response["operation"] == "daily_chart":
                    for bar in response["data"]:
                        bar.update(cur_prc=100, open_pric=100,
                                   high_pric=101, low_pric=99)
                    raw = next(item for item in self.doc["results"]
                               if item["ticker"] == symbol
                               and item["requested_price_basis"] == "RAW")
                    response["data"][-1] = copy.deepcopy(raw["data"][-1])
        next(p for p in self.case.base.plan["positions"] if p["ticker"] == "SOXL")["action"] = "TRIM"
        self.bind()
        report = self.case.compile()
        row = next(p for p in report["portfolio"]["positions"] if p["ticker"] == "SOXL")
        self.assertEqual(row["holding_timing_evidence"]["timing_source_mode"], "KIWOOM_ONLY")


class ManualKiwoomCaptureCliTests(unittest.TestCase):
    def setUp(self):
        self.case = ManualCliInputWiringTests("runTest")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_cli_binds_technical_capture_bytes_and_hash_without_serializing_raw(self):
        raw = self.case.capture.read_bytes()
        result, report, out = self.case.run_cli(extra=["--holding-timing-capture", str(self.case.capture)])
        self.assertEqual(result, 0)
        self.assertEqual(self.case.compiler.call_args.kwargs["holding_timing_inputs"]["capture_artifacts"],
                         [(raw, hashlib.sha256(raw).hexdigest())])
        manifest = json.loads((out/"run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["consumed_hashes"]["holding_timing_capture_0"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("capture_artifacts", json.dumps(report))

    def test_cli_mixed_or_incomplete_scope_is_blocked_before_read(self):
        for extra in ([], ["--input-mode","LIVE_READ_ONLY"], ["--mode","HISTORICAL_REPLAY"],
                      ["--holding-timing-snapshot","unused.json"]):
            with patch.object(Path, "read_bytes", side_effect=AssertionError("MUST_NOT_READ")):
                with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                    dashboard.main(["--holding-timing-capture","unused.json"] + extra)


def _ca_pair(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return (raw, hashlib.sha256(raw).hexdigest())


def _attach_ca_fixture(case, event_type=None, future=False):
    """Synthetic reviewed evidence only; canonical policy is a test Temp file."""
    from current_event_risk import record_hash, validate_bundle_semantics
    symbols = ["MVLL", "MRVL", "SOXL", "SOXX"]
    # The Manual cutoff is acquisition completion, not the later analysis clock.
    stamp = case.case.doc["observed_at"]
    session = case.case.base.inputs["snapshot"]["session"]["us_session_date"]
    start = min(r["dt"] for v in case.doc["results"] for r in v["data"])
    start = start[:4]+"-"+start[4:6]+"-"+start[6:]
    bundle = dict(schema_version="1.0", bundle_id="SYNTHETIC_CA", policy_version="SYNTHETIC",
        event_policy_hash="a"*64, active_research_baseline_index_hash="b"*64, active_research_baselines=[],
        market_session=session, analysis_cutoff=stamp, generated_at=stamp,
        retrieval_mode="LIVE_FORWARD_CAPTURE", bundle_status="COMPLETE",
        coverage_status="COMPLETE_FOR_REQUIRED_CATEGORIES", event_data_status="COMPLETE",
        universe={"direct":symbols,"supplemental":[]}, ticker_coverage=[], category_coverage=[], events=[],
        provider_readiness_mutated=False, strategy_state_mutated=False, quantity_authority=False, order_authority=False)
    sources = {}; event_ids = {}
    for ticker in symbols:
        eid = ticker+"-official"; cid = ticker+"-CA"
        doc = dict(evidence_id=eid,ticker=ticker,source_url="https://www.sec.gov/SYNTHETIC/"+ticker,
            source_type="SEC",retrieved_at=stamp,capture_kind="EXTRACTED_TEXT",
            extracted_text="SYNTHETIC DOCUMENT; NOT OFFICIAL OR LIVE EVIDENCE")
        sources[eid] = _ca_pair(doc)
        ids=[]
        if event_type:
            event=dict(event_id=ticker+"-event",ticker=ticker,instrument_role="DIRECT",event_type=event_type,
                source_url=doc["source_url"],source_type="SEC",published_at="2026-08-01T00:00:00+00:00",
                published_at_precision="EXACT",effective_at="2026-10-01T20:00:00+00:00" if future else "2026-08-20T13:30:00+00:00",
                effective_at_precision="EXACT",retrieved_at=stamp,first_seen_at=stamp,analysis_cutoff=stamp,
                point_in_time_eligible=True,severity="LOW",strategy_relevance="SYNTHETIC",verification_status="VERIFIED",
                policy_effect="CONTEXT_ONLY",applies_to=[ticker],supplemental_context_for=[],
                evidence_summary="SYNTHETIC",claim_ids=[ticker+"-claim"],evidence_ids=[eid],record_hash="0"*64)
            event["record_hash"]=record_hash(event);bundle["events"].append(event);ids=[event["event_id"]]
        event_ids[ticker]=ids
        cat=dict(category_id=cid,ticker=ticker,event_category="CORPORATE_ACTION",
            required_source_routes=["SEC"],checked_source_routes=["SEC"],coverage_start=start+"T00:00:00+00:00",
            coverage_end=stamp,last_checked_at=stamp,published_at=None,effective_at=None,retrieved_at=stamp,
            analysis_cutoff=stamp,materiality="LOW",coverage_status="COMPLETE_FOR_REQUIRED_CATEGORIES",
            event_effect="CONTEXT_ONLY",announcement_status="ANNOUNCED" if ids else "NOT_YET_ANNOUNCED_AS_OF_CUTOFF",
            next_refresh_trigger="NEXT_RUN_OR_CORRECTION",point_in_time_eligible=True,claim_ids=[ticker+"-claim"],
            evidence_ids=[eid],record_hash="0"*64,order_authority=False)
        cat["record_hash"]=record_hash(cat);bundle["category_coverage"].append(cat)
        bundle["ticker_coverage"].append(dict(ticker=ticker,instrument_role="DIRECT",
            coverage_status="COMPLETE_FOR_REQUIRED_CATEGORIES",event_effect="CONTEXT_ONLY",event_ids=ids,
            category_ids=[cid],checked_source_types=["SEC"],missing_fields=[],event_data_incomplete=False,notes=[]))
    assert validate_bundle_semantics(bundle)==[]
    policy=case.case.base.inputs["policy"]
    policy["holding_timing_rules"]["manual_corporate_action_clearance"]=dict(status="APPROVED",
        version="manual-ca-clearance-v1",scope="MANUAL_EXISTING_HOLDING_ONLY",
        approval_source="USER_APPROVED_CA_CLEARANCE_AND_INPUT_BINDING",reviewed_receipt_sha256=[])
    policy_context_hash=case.case.manual.canonical_hash(policy)
    bundle_pair=_ca_pair(bundle); bindings=[]; pins=[]
    capture_hash=case.case.base.inputs["capture_artifacts"][0][1]
    for ticker in symbols:
        eid=ticker+"-official"; rid=ticker+"-review"
        receipt=json.loads(sources[eid][0]);receipt["evidence_id"]=rid
        receipt["reviewed_treatment"]=dict(event_bundle_sha256=bundle_pair[1],
            capture_sha256={"RAW":capture_hash,"ADJUSTED":capture_hash},source_sha256={eid:sources[eid][1]},
            run_id=case.doc["run_id"],completed_session=session,decision_as_of=stamp,history_start=start,
            policy_context_sha256=policy_context_hash,
            technical_price_basis="split-adjusted OHLC rescaled to latest raw close",
            adjustment_semantics_verified=True,prehistory_effects_resolved=True,conflict=False,
            event_treatment={i:"NOT_YET_EFFECTIVE" if future else "VERIFIED_APPLIED" for i in event_ids[ticker]})
        sources[rid]=_ca_pair(receipt);pins.append(sources[rid][1])
        bindings.append(dict(ticker=ticker,event_ids=event_ids[ticker],evidence_ids=[eid],
            capture_sha256={"RAW":capture_hash,"ADJUSTED":capture_hash},treatment_evidence_ids=[rid]))
    policy=case.case.base.inputs["policy"]
    policy["holding_timing_rules"]["manual_corporate_action_clearance"]=dict(status="APPROVED",
        version="manual-ca-clearance-v1",scope="MANUAL_EXISTING_HOLDING_ONLY",
        approval_source="USER_APPROVED_CA_CLEARANCE_AND_INPUT_BINDING",reviewed_receipt_sha256=pins)
    dashboard.DEFAULT_ALERT_POLICY.write_text(json.dumps(policy),encoding="utf-8")
    case.case.base.inputs["corporate_action_artifacts"]=dict(event_bundle_artifact=bundle_pair,
        source_artifacts=sources,adjustment_bindings=bindings)


class ManualCorporateActionClearanceTests(ManualKiwoomOnlyTimingTests):
    """New tests use the actual Manual consumer, not a mocked timing result."""
    def proof_cutoff(self):
        return json.loads(self.proof()["event_bundle_artifact"][0])["analysis_cutoff"]

    def proof(self):
        return self.case.base.inputs["corporate_action_artifacts"]

    def test_ca_missing_or_self_asserted_proof_blocks(self):
        for value in (None, {}, {"status":"PASS"}):
            self.case.base.inputs["corporate_action_artifacts"]=value
            self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_old_policy_cannot_enable_missing_close(self):
        self.case.base.inputs["policy"]["holding_timing_rules"].pop("manual_corporate_action_clearance")
        dashboard.DEFAULT_ALERT_POLICY.write_text(json.dumps(self.case.base.inputs["policy"]),encoding="utf-8")
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_caller_rehash_cannot_forge_review(self):
        receipt=json.loads(self.proof()["source_artifacts"]["MVLL-review"][0])
        receipt["reviewed_treatment"]["adjustment_semantics_verified"]=False
        self.proof()["source_artifacts"]["MVLL-review"]=_ca_pair(receipt)
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_capture_substitution_blocks(self):
        self.proof()["adjustment_bindings"][0]["capture_sha256"]["RAW"]="f"*64
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_known_split_and_dividend_and_future_are_distinct(self):
        for kind,future in [("ETF_SPLIT_OR_REVERSE_SPLIT",False),("EX_DIVIDEND",False),("ETF_SPLIT_OR_REVERSE_SPLIT",True)]:
            _attach_ca_fixture(self,kind,future)
            self.assertEqual(self.timing()[0],"VERIFIED_REDUCTION_REVIEW")

    def test_ca_incomplete_coverage_even_rehashed_blocks(self):
        from current_event_risk import record_hash
        bundle=json.loads(self.proof()["event_bundle_artifact"][0])
        bundle["category_coverage"][0]["checked_source_routes"]=[]
        bundle["category_coverage"][0]["record_hash"]=record_hash(bundle["category_coverage"][0])
        self.proof()["event_bundle_artifact"]=_ca_pair(bundle)
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_unsafe_url_is_not_projected(self):
        doc=json.loads(self.proof()["source_artifacts"]["MVLL-official"][0])
        doc["source_url"]+="?token=SYNTHETIC_SECRET_CA"
        self.proof()["source_artifacts"]["MVLL-official"]=_ca_pair(doc)
        status,report=self.timing();self.assertEqual(status,"NOT_VERIFIED")
        for text in (json.dumps(report),render_html(report),render_markdown(report)):
            self.assertNotIn("SYNTHETIC_SECRET_CA",text)

    def test_ca_confirmed_close_does_not_bypass_clearance(self):
        for ticker in ("MVLL","MRVL"):
            self.snapshot["symbols"][ticker]["quote_crosscheck"]=self.crosscheck(ticker)
        self.case.base.inputs["corporate_action_artifacts"]=None
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_projection_and_compile_replay_use_same_proof(self):
        import bundle_support
        inputs=self.case.base.inputs
        records=bundle_support.technical_projection(inputs["capture_artifacts"],run_id=self.doc["run_id"],
            completed_session="2026-09-01",generated_at=self.case.stamp,policy=inputs["policy"],
            decision_as_of=self.proof_cutoff(),corporate_action_artifacts=self.proof())
        self.assertTrue(all(row["corporate_action_unresolved"] is False for row in records.values()))
        self.snapshot["symbols"].update(records)
        status,report=self.timing();self.assertEqual(status,"VERIFIED_REDUCTION_REVIEW")
        errors=dashboard.validate_swing_action_contract(report,evidence=self.case.evidence,plan=self.case.plan_value,
            risk_policy=self.case.base.risk,evidence_sha256=hashlib.sha256(evidence_raw_bytes(self.case.evidence)).hexdigest(),
            holding_timing_inputs=inputs,parent_capture_artifacts=self.case.captures,
            current_session_authority_resolver=self.case.resolver)
        self.assertEqual(errors,[])
        inputs["corporate_action_artifacts"]=None
        errors=dashboard.validate_swing_action_contract(report,evidence=self.case.evidence,plan=self.case.plan_value,
            risk_policy=self.case.base.risk,evidence_sha256=hashlib.sha256(evidence_raw_bytes(self.case.evidence)).hexdigest(),
            holding_timing_inputs=inputs,parent_capture_artifacts=self.case.captures,
            current_session_authority_resolver=self.case.resolver)
        self.assertTrue(errors)

    def test_ca_producer_without_proof_stays_unresolved(self):
        import bundle_support
        records=bundle_support.technical_projection(self.case.base.inputs["capture_artifacts"],
            run_id=self.doc["run_id"],completed_session="2026-09-01",generated_at=self.case.stamp)
        self.assertTrue(all(r["corporate_action_unresolved"] is True for r in records.values()))

    def repin_synthetic(self, ticker="MVLL", **changes):
        """Exercise semantic validation separately from the trusted pin gate."""
        sources=self.proof()["source_artifacts"];key=ticker+"-review"
        receipt=json.loads(sources[key][0]);receipt["reviewed_treatment"].update(changes)
        sources[key]=_ca_pair(receipt)
        policy=self.case.base.inputs["policy"]
        policy["holding_timing_rules"]["manual_corporate_action_clearance"]["reviewed_receipt_sha256"]=[
            sources[k][1] for k in sources if k.endswith("-review")]
        dashboard.DEFAULT_ALERT_POLICY.write_text(json.dumps(policy),encoding="utf-8")

    def test_ca_reviewed_but_wrong_context_or_unresolved_still_blocks(self):
        for key,value in (("run_id","OTHER_SYNTHETIC_RUN"),("completed_session","2026-08-31"),
                ("decision_as_of","2026-09-02T22:00:04+00:00"),("history_start","2026-09-01"),
                ("policy_context_sha256","f"*64),("technical_price_basis","total-return"),
                ("adjustment_semantics_verified",False),("prehistory_effects_resolved",False),("conflict",True)):
            with self.subTest(field=key):
                _attach_ca_fixture(self)
                self.repin_synthetic(**{key:value})
                self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_canonical_policy_change_invalidates_old_review(self):
        policy=self.case.base.inputs["policy"]
        policy["holding_timing_rules"]["policy_version"] += "-SYNTHETIC_CHANGE"
        dashboard.DEFAULT_ALERT_POLICY.write_text(json.dumps(policy),encoding="utf-8")
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_known_event_without_documented_treatment_blocks(self):
        for kind in ("ETF_SPLIT_OR_REVERSE_SPLIT","EX_DIVIDEND"):
            _attach_ca_fixture(self,kind)
            self.repin_synthetic(event_treatment={"MVLL-event":"UNKNOWN"})
            self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_effect_after_consumed_session_is_not_applied_history(self):
        from current_event_risk import record_hash
        _attach_ca_fixture(self,"ETF_SPLIT_OR_REVERSE_SPLIT")
        bundle=json.loads(self.proof()["event_bundle_artifact"][0])
        event=next(e for e in bundle["events"] if e["ticker"]=="MVLL")
        event["effective_at"]="2026-09-02T13:30:00+00:00"  # Before cutoff, after consumed Sep 1 history.
        event["record_hash"]=record_hash(event)
        self.proof()["event_bundle_artifact"]=_ca_pair(bundle)
        for ticker in ("MVLL","MRVL","SOXL","SOXX"):
            self.repin_synthetic(ticker,event_bundle_sha256=self.proof()["event_bundle_artifact"][1])
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")
        self.repin_synthetic(event_treatment={"MVLL-event":"NOT_YET_EFFECTIVE"})
        self.assertEqual(self.timing()[0],"VERIFIED_REDUCTION_REVIEW")

    def test_ca_wait_category_cannot_be_cleared_by_receipt(self):
        from current_event_risk import record_hash
        bundle=json.loads(self.proof()["event_bundle_artifact"][0]);cat=bundle["category_coverage"][0]
        cat["event_effect"]="WAIT_REQUIRED";cat["record_hash"]=record_hash(cat)
        self.proof()["event_bundle_artifact"]=_ca_pair(bundle)
        for ticker in ("MVLL","MRVL","SOXL","SOXX"):
            self.repin_synthetic(ticker,event_bundle_sha256=self.proof()["event_bundle_artifact"][1])
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_source_ticker_time_and_authority_binding(self):
        for key,value in (("ticker","SOXL"),("retrieved_at","2026-09-02T22:00:04+00:00"),
                          ("source_type","SOCIAL"),("source_url","https://sec.gov.example.invalid/doc")):
            with self.subTest(field=key):
                _attach_ca_fixture(self)
                source=json.loads(self.proof()["source_artifacts"]["MVLL-official"][0]);source[key]=value
                pair=_ca_pair(source);self.proof()["source_artifacts"]["MVLL-official"]=pair
                self.repin_synthetic(source_sha256={"MVLL-official":pair[1]})
                self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_valid_document_secret_text_never_persists(self):
        doc=json.loads(self.proof()["source_artifacts"]["MVLL-official"][0])
        secret="SYNTHETIC_CA_TOKEN_NOT_REAL"
        doc["extracted_text"]="Authorization: "+secret
        pair=_ca_pair(doc);self.proof()["source_artifacts"]["MVLL-official"]=pair
        self.repin_synthetic(source_sha256={"MVLL-official":pair[1]})
        status,report=self.timing();self.assertEqual(status,"VERIFIED_REDUCTION_REVIEW")
        out=write_run(report,{},output_root=Path(self.case.base.temp.name)/"ca-safe-output",
            source_paths={},implementation_paths=[],root=Path(self.case.base.temp.name))
        for text in (json.dumps(report),render_html(report),render_markdown(report),
                     (out/"portfolio-decision.json").read_text(encoding="utf-8")):
            self.assertNotIn(secret,text)

    def confirm_both(self):
        for ticker in ("MVLL","MRVL"):
            self.snapshot["symbols"][ticker]["quote_crosscheck"]=self.crosscheck(ticker)

    def test_ca_confirmed_closes_reject_response_before_request(self):
        self.confirm_both()
        self.doc["results"][0]["retrieved_at"]="2026-09-02T21:59:00+00:00"
        self.bind()
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_confirmed_closes_reject_different_consumed_history(self):
        self.confirm_both()
        adj=next(r for r in self.doc["results"] if r["ticker"]=="MVLL" and r["requested_price_basis"]=="ADJUSTED")
        adj["data"][-2].update(cur_prc="128",high_pric="130")
        self.bind()
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_confirmed_closes_reject_bad_page_chain(self):
        self.confirm_both()
        self.doc["results"][0]["pagination"]["pages"][0]["page_index"]=2
        self.bind()
        self.assertEqual(self.timing()[0],"NOT_VERIFIED")

    def test_ca_confirmed_projection_uses_external_compile_and_replay(self):
        # Only the approved offline r9 technical producer is exercised.
        import bundle_support
        inputs = self.case.base.inputs
        records = bundle_support.technical_projection(inputs["capture_artifacts"], run_id=self.doc["run_id"],
            completed_session="2026-09-01", generated_at=self.case.stamp, policy=inputs["policy"],
            decision_as_of=self.proof_cutoff(), corporate_action_artifacts=self.proof())
        self.snapshot["symbols"].update(records)
        self.confirm_both()
        status, report = self.timing()
        self.assertEqual(status, "VERIFIED_REDUCTION_REVIEW")
        errors = dashboard.validate_swing_action_contract(report, evidence=self.case.evidence,
            plan=self.case.plan_value, risk_policy=self.case.base.risk,
            evidence_sha256=hashlib.sha256(evidence_raw_bytes(self.case.evidence)).hexdigest(),
            holding_timing_inputs=inputs, parent_capture_artifacts=self.case.captures,
            current_session_authority_resolver=self.case.resolver)
        self.assertEqual(errors, [])
        for row in report["swing_action_plan"]["rows"]:
            self.assertIsNone(row["shadow_sell_qty"])
            self.assertEqual(row["execution_status"], "DISABLED")


class ManualTimingEvidenceContractTests(ManualCorporateActionClearanceTests):
    """P1–P5 and external-candidate data boundaries; never operating CA approval."""

    def test_p1_p3_ordinary_and_missing_close_require_full_ca(self):
        for confirmed in (False, True):
            with self.subTest(confirmed=confirmed):
                _attach_ca_fixture(self)
                for ticker in ("MVLL", "MRVL"):
                    self.snapshot["symbols"][ticker]["quote_crosscheck"] = self.crosscheck(ticker) if confirmed else None
                self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
                proof = self.proof()
                for bad in (None, {}, {"status": "PASS"}, {"corporate_action_unresolved": False}):
                    self.case.base.inputs["corporate_action_artifacts"] = bad
                    status, report = self.timing()
                    self.assertEqual(status, "NOT_VERIFIED")
                    self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")
                self.case.base.inputs["corporate_action_artifacts"] = proof

    def test_p2_absent_history_cannot_inherit_ordinary_event_or_saved_status(self):
        self.confirm_both()
        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
        self.case.base.inputs.pop("capture_artifacts")
        status, report = self.timing()
        self.assertEqual(status, "NOT_VERIFIED")
        self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")

    def test_p3_candidate_empty_pin_policy_cannot_consume_test_receipts(self):
        path = ROOT / "stock-strategy-system/alert_policy.json"
        original = path.read_bytes()
        canonical = json.loads(original)
        self.assertEqual(canonical["holding_timing_rules"]["manual_corporate_action_clearance"]["reviewed_receipt_sha256"], [])
        self.assertTrue(self.case.base.inputs["policy"]["holding_timing_rules"]["manual_corporate_action_clearance"]["reviewed_receipt_sha256"])
        self.assertEqual(self.timing()[0], "VERIFIED_REDUCTION_REVIEW")
        self.case.base.inputs["policy"] = canonical
        with patch.object(dashboard, "DEFAULT_ALERT_POLICY", path):
            status, report = self.timing()
        self.assertEqual(status, "NOT_VERIFIED")
        self.assertNotEqual(report["evidence"].get("technical_analysis_eligibility"), "YES")
        self.assertEqual(path.read_bytes(), original)

    def test_p5_historical_display_is_not_current_reacceptance(self):
        status, report = self.timing()
        self.assertEqual(status, "VERIFIED_REDUCTION_REVIEW")
        with patch.object(dashboard, "_holding_timing_projection", side_effect=AssertionError("DISPLAY_MUST_NOT_REACQUIRE")):
            for text in (render_markdown(report), render_html(report)):
                self.assertIn(report["generated_at"], text)
                self.assertIn("생성 당시 결과의 표시이며 현재 재수용 검증이 아닙니다", text)
        self.assertEqual(dashboard.validate_swing_action_contract(report), [])
        self.case.base.inputs["corporate_action_artifacts"] = None
        errors = dashboard.validate_swing_action_contract(report,
            evidence=self.case.evidence, plan=self.case.plan_value, risk_policy=self.case.base.risk,
            evidence_sha256=hashlib.sha256(evidence_raw_bytes(self.case.evidence)).hexdigest(),
            holding_timing_inputs=self.case.base.inputs, parent_capture_artifacts=self.case.captures,
            current_session_authority_resolver=self.case.resolver)
        self.assertIn("SWING_TIMING_CONSUMED_INPUT_MISMATCH", errors)

    def test_p5_policy_pin_removal_invalidates_current_replay(self):
        status, report = self.timing()
        self.assertEqual(status, "VERIFIED_REDUCTION_REVIEW")
        self.case.base.inputs["policy"]["holding_timing_rules"]["manual_corporate_action_clearance"]["reviewed_receipt_sha256"] = []
        dashboard.DEFAULT_ALERT_POLICY.write_text(json.dumps(self.case.base.inputs["policy"]), encoding="utf-8")
        errors = dashboard.validate_swing_action_contract(report,
            evidence=self.case.evidence, plan=self.case.plan_value, risk_policy=self.case.base.risk,
            evidence_sha256=hashlib.sha256(evidence_raw_bytes(self.case.evidence)).hexdigest(),
            holding_timing_inputs=self.case.base.inputs, parent_capture_artifacts=self.case.captures,
            current_session_authority_resolver=self.case.resolver)
        self.assertIn("SWING_TIMING_CONSUMED_INPUT_MISMATCH", errors)

    def test_ca_raw_material_never_serializes_to_dashboard_or_logs(self):
        import base64
        import os
        marker = "SYNTHETIC_CA_RAW_SENTINEL_20260927_NOT_REAL"
        document = json.loads(self.proof()["source_artifacts"]["MVLL-official"][0])
        document["extracted_text"] = marker
        pair = _ca_pair(document)
        self.proof()["source_artifacts"]["MVLL-official"] = pair
        self.repin_synthetic(source_sha256={"MVLL-official": pair[1]})
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status, report = self.timing()
            self.assertEqual(status, "VERIFIED_REDUCTION_REVIEW")
            out = write_run(report, {}, output_root=Path(self.case.base.temp.name)/"ca-boundary-output",
                source_paths={}, implementation_paths=[], root=Path(self.case.base.temp.name))
            rendered = [json.dumps(report), render_html(report), render_markdown(report)]
        emitted = rendered + [stdout.getvalue(), stderr.getvalue()]
        emitted += [p.read_text(encoding="utf-8") for p in out.rglob("*") if p.is_file()]
        for content in emitted:
            self.assertNotIn(marker, content)
            self.assertNotIn("corporate_action_artifacts", content)
            for raw, _ in self.proof()["source_artifacts"].values():
                for representation in (raw.decode(), raw.hex(), base64.b64encode(raw).decode()):
                    self.assertNotIn(representation, content)
        # Explicitly authorized raw fixture retention is separate from Dashboard output.
        retained = Path(tempfile.mkdtemp(prefix="test-only-ca-evidence-", dir=os.environ["TMP"]))
        fixture_manifest = {"synthetic_only": True, "operating_authority": False, "files": {}}
        artifacts = {"event-bundle.json": self.proof()["event_bundle_artifact"][0],
            "adjustment-bindings.json": _ca_pair({"bindings": self.proof()["adjustment_bindings"]})[0],
            "test-policy.json": _ca_pair(self.case.base.inputs["policy"])[0],
            "technical-capture.json": self.case.base.inputs["capture_artifacts"][0][0]}
        artifacts.update({key+".json": raw for key,(raw,_) in self.proof()["source_artifacts"].items()})
        for name, raw in artifacts.items():
            (retained/name).write_bytes(raw)
            fixture_manifest["files"][name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        (retained/"fixture-manifest.json").write_text(json.dumps(fixture_manifest, indent=2), encoding="utf-8")
        (retained/"serialization-check.json").write_text(json.dumps({"status":"PASS",
            "dashboard_file_count":len([p for p in out.rglob("*") if p.is_file()]),
            "stdout_empty":not stdout.getvalue(), "stderr_empty":not stderr.getvalue(),
            "test_policy_pins":self.case.base.inputs["policy"]["holding_timing_rules"]["manual_corporate_action_clearance"]["reviewed_receipt_sha256"]}),encoding="utf-8")
