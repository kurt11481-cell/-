#!/usr/bin/env python3
"""ORDER_INTENT_ONLY runtime safety and boundary tests."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from portfolio_decision_dashboard import (  # noqa: E402
    DEFAULT_RISK_POLICY,
    compile_dashboard,
    implementation_provenance_paths,
    write_run,
)
from portfolio_decision_order_intent import (  # noqa: E402
    MANUAL_SELL_PRICE_RULE,
    ORDER_INTENT_SCHEMA,
    compile_order_intent_artifact,
    plan_delivery,
    write_order_intent_artifact,
)
import portfolio_decision_order_intent as intent  # noqa: E402
from validation_common import canonical_hash, file_hash, load_json, validate_instance  # noqa: E402


DASHBOARD_TEST = ROOT / "manage-us-stock-strategy/tests/test_portfolio_decision_dashboard.py"
REGISTRY_PATH = ROOT / "workspace/policies/instrument_registry.json"
ALERT_POLICY_PATH = ROOT / "stock-strategy-system/alert_policy.json"
CANDIDATE_PATH = ROOT / "workspace/outputs/lmt-instrument-registry-candidate-prep/lmt-instrument-registry-patch-candidate-v1.json"
_spec = importlib.util.spec_from_file_location("order_intent_dashboard_fixture", DASHBOARD_TEST)
assert _spec and _spec.loader
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)


def unit_identity_snapshot(source: dict):
    """Supply a trusted in-memory owner at the compiler unit-test seam only.

    The synthetic version/hash retain the old fixed-LIMIT fixture vocabulary.
    This is not a loaded Production artifact; real-byte loader tests below use
    session_k3_inputs instead. No identity record is derived from Risk mappings.
    """
    from integrated_authority_snapshot import IntegratedAuthoritySnapshot
    from instrument_identity_artifact import LoadedInstrumentIdentityRegistry
    from session_calendar_artifact import LoadedSessionCalendar

    fixture_root = REGISTRY_PATH.parents[2]
    activation = load_json(fixture_root / "workspace/policies/integrated_identity_session_activation.json")
    identity_hash = activation["instrument_identity"]["active_registry_hash"]
    artifact = load_json(fixture_root / "workspace/instrument-identity-authority/artifacts" /
                         identity_hash / "us-equity-instrument-identity-current-v1.registry.json")
    artifact.update(registry_version=load_json(REGISTRY_PATH)["registry_version"],
                    authority_as_of="2026-08-01T00:00:00+00:00", generated_at="2026-08-01T00:00:00+00:00")
    cohort = "synthetic-shared-authority-cohort"
    return IntegratedAuthoritySnapshot(
        "a" * 64, cohort,
        LoadedInstrumentIdentityRegistry(
            {"activated_at": "2026-08-01T00:00:00+00:00", "activation_cohort_id": cohort},
            artifact, file_hash(REGISTRY_PATH)),
        LoadedSessionCalendar({}, {"calendar_version": "unit-session-v1",
                                   "calendar_policy_identity": "US_EQUITIES_CORE_SESSION_V2"}, "c" * 64),
        source["decision_as_of"], source["decision_as_of"], source["manual_run_id"],
    )


def bind_unit_identity_provenance(source: dict) -> dict:
    source["integrated_authority_snapshot_provenance"] = unit_identity_snapshot(source).provenance(
        authority_source="K3_COMBINED_PRODUCTION")
    return source


def order_terms(*, quantity: int = 4, limit_price: float = 100.0,
                valid_until: str = "2026-08-22T20:00:00+00:00",
                funding_source: str = "VERIFIED_ORDERABLE_CASH") -> dict:
    return {
        "terms_status": "APPROVED_ORDER_INTENT_ONLY",
        "production_target_approval_status": "APPROVED_PRODUCTION_TARGET",
        "proposed_quantity": quantity,
        "order_type": "LIMIT",
        "limit_price": limit_price,
        "approved_price_rule": None,
        "time_in_force": "DAY",
        "valid_from": "2026-08-22T13:30:00+00:00",
        "valid_until": valid_until,
        "why_now": "Approved next-session rebalance review",
        "decision_change_trigger": "Fresh broker or price evidence changes",
        "thesis_status": "ACTIVE",
        "kill_condition": "Approved thesis invalidation occurs",
        "funding_source": funding_source,
    }


def buy_plan() -> dict:
    return {
        "plan_id": "order-intent-buy-v1",
        "as_of": "2026-08-21T22:00:00+00:00",
        "plan_status": "CURRENT_APPROVED",
        "evidence_binding": {
            "expected_run_id": "manual-synthetic-grade-b",
            "expected_decision_as_of": "2026-08-21T22:00:00+00:00",
        },
        "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET",
        "cash_target_pct": 90.0,
        "positions": [
            {
                "ticker": "PGR", "action": "HOLD", "target_weight_pct": 2.0,
                "rationale": "Existing low-weight holding", "investment_horizon": "long",
                "target_status": "APPROVED",
            },
            {
                "ticker": "JPM", "action": "ADD", "target_weight_pct": 8.0,
                "rationale": "Approved production diversification target",
                "investment_horizon": "long", "target_status": "APPROVED",
                "order_intent_terms": order_terms(),
            },
        ],
        "material_unknowns": [],
        "decision_change_triggers": ["Fresh broker or price evidence changes"],
    }


def sell_plan(*, action: str = "TRIM") -> dict:
    target = 10.0 if action == "TRIM" else 0.0
    cash = 90.0 if action == "TRIM" else 100.0
    quantity = 5 if action == "TRIM" else 10
    terms = order_terms(quantity=quantity, limit_price=200.0, funding_source="NOT_APPLICABLE")
    terms["thesis_status"] = "IMPAIRED" if action == "TRIM" else "KILLED"
    return {
        "plan_id": f"order-intent-{action.lower()}-v1",
        "as_of": "2026-08-21T22:00:00+00:00",
        "plan_status": "CURRENT_APPROVED",
        "evidence_binding": {
            "expected_run_id": "manual-synthetic-grade-b",
            "expected_decision_as_of": "2026-08-21T22:00:00+00:00",
        },
        "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET",
        "cash_target_pct": cash,
        "positions": [{
            "ticker": "PGR", "action": action, "target_weight_pct": target,
            "rationale": "Approved risk reduction", "investment_horizon": "transition",
            "target_status": "APPROVED", "order_intent_terms": terms,
        }],
        "material_unknowns": [],
        "decision_change_triggers": ["Fresh broker or price evidence changes"],
    }


def source_for_buy() -> dict:
    source = _fixture.evidence(cash=9800.0, holdings={"PGR": 1, "JPM": 0})
    source["identity_registry_version"] = load_json(REGISTRY_PATH)["registry_version"]
    source["identity_registry_hash"] = file_hash(REGISTRY_PATH)
    return bind_unit_identity_provenance(source)


def source_for_sell() -> dict:
    source = _fixture.evidence(cash=8000.0, holdings={"PGR": 10})
    source["identity_registry_version"] = load_json(REGISTRY_PATH)["registry_version"]
    source["identity_registry_hash"] = file_hash(REGISTRY_PATH)
    return bind_unit_identity_provenance(source)


class OrderIntentOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_json(DEFAULT_RISK_POLICY)
        self.registry_path = REGISTRY_PATH
        self.registry = load_json(self.registry_path)
        self.risk_hash = file_hash(DEFAULT_RISK_POLICY)
        self.alert_policy = load_json(ALERT_POLICY_PATH)
        self.alert_hash = file_hash(ALERT_POLICY_PATH)

    def compile_dashboard(self, source: dict, plan: dict):
        evidence_sha = hashlib.sha256(_fixture.evidence_raw_bytes(source)).hexdigest()
        return compile_dashboard(
            source, plan, self.policy, registry=self.registry,
            run_id="order-intent-test", generated_at=source["decision_as_of"],
            evidence_sha256=evidence_sha,
            current_session_context=_fixture.current_context(source, evidence_sha),
            current_session_authority_resolver=_fixture.canonical_runtime_resolver(source),
        )

    def build(self, source: dict | None = None, plan: dict | None = None, **kwargs):
        source = source or source_for_buy()
        plan = plan or buy_plan()
        report, validation = self.compile_dashboard(source, plan)
        hashes = {
            "portfolio_evidence": canonical_hash(source),
            "decision_plan": canonical_hash(plan),
            "portfolio_decision": canonical_hash(report),
            "validation_report": canonical_hash(validation),
            "risk_policy": self.risk_hash,
            "instrument_registry": file_hash(self.registry_path),
            "alert_policy": self.alert_hash,
        }
        return compile_order_intent_artifact(
            report, validation, plan, source, self.policy, self.registry,
            integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
            risk_envelope_sha256=self.risk_hash, input_hashes=hashes,
            now=kwargs.pop("now", source["decision_as_of"]), **kwargs,
        )

    @staticmethod
    def instruction(artifact: dict, ticker: str) -> dict:
        return next(item for item in artifact["instructions"] if item["ticker"] == ticker)

    def test_add_all_gates_pass_is_buy_ready(self):
        artifact = self.build()
        row = self.instruction(artifact, "JPM")
        self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY")
        self.assertEqual(row["side"], "BUY")
        self.assertEqual(row["proposed_quantity"], 4)
        self.assertEqual(row["risk_gate_status"], "PASS")

    def test_trim_all_gates_pass_is_sell_ready(self):
        row = self.instruction(self.build(source_for_sell(), sell_plan()), "PGR")
        self.assertEqual((row["state"], row["side"], row["proposed_quantity"]),
                         ("ORDER_INSTRUCTION_READY", "SELL", 5))

    def test_exit_all_gates_pass_is_sell_ready(self):
        row = self.instruction(self.build(source_for_sell(), sell_plan(action="EXIT")), "PGR")
        self.assertEqual((row["state"], row["side"], row["proposed_quantity"]),
                         ("ORDER_INSTRUCTION_READY", "SELL", 10))

    def test_hold_is_no_order(self):
        row = self.instruction(self.build(), "PGR")
        self.assertEqual(row["state"], "NO_ORDER")
        self.assertIsNone(row["side"])
        self.assertIsNone(row["proposed_quantity"])

    def test_stale_kiwoom_price_blocks_only_affected_instruction(self):
        source = source_for_buy()
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "JPM":
                item["bar_date"] = "2000-01-01"
        row = self.instruction(self.build(source, buy_plan()), "JPM")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("CANONICAL_REFERENCE_PRICE_NOT_VERIFIED", row["blockers"])

    def test_provider_observed_date_must_follow_reported_session_ticker_local(self):
        source = source_for_buy()
        plan = buy_plan()
        plan["cash_target_pct"] = 82.0
        pgr = plan["positions"][0]
        pgr.update({
            "action": "ADD",
            "target_weight_pct": 10.0,
            "order_intent_terms": order_terms(quantity=2, limit_price=200.0),
        })
        report, validation = self.compile_dashboard(source, plan)
        for item in source["last_verified_finalized_bars"]:
            if item["ticker"] == "JPM":
                item["bar"]["provider_timestamp"] = "2026-08-20T22:00:00+00:00"
        artifact = compile_order_intent_artifact(
            report, validation, plan, source, self.policy, self.registry,
            integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
            risk_envelope_sha256=self.risk_hash,
            input_hashes={
                "portfolio_evidence": canonical_hash(source),
                "portfolio_decision": canonical_hash(report),
                "validation_report": canonical_hash(validation),
                "risk_policy": self.risk_hash,
                "instrument_registry": file_hash(self.registry_path),
                "alert_policy": self.alert_hash,
            },
            now=source["decision_as_of"],
        )
        jpm = self.instruction(artifact, "JPM")
        self.assertEqual(jpm["state"], "ORDER_BLOCKED")
        self.assertIn(
            "PROVIDER_OBSERVED_DATE_NOT_AFTER_REPORTED_SESSION", jpm["blockers"],
        )
        self.assertEqual(
            self.instruction(artifact, "PGR")["state"], "ORDER_INSTRUCTION_READY",
        )

    def test_missing_holdings_blocks_instruction(self):
        source = source_for_buy()
        source["broker_observed_state"]["holdings"] = []
        row = self.instruction(self.build(source, buy_plan()), "JPM")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("PORTFOLIO_DECISION_VALIDATION_NOT_PASS", row["blockers"])

    def test_missing_verified_orderable_cash_blocks_buy(self):
        source = source_for_buy()
        source["orderable_cash_status"] = "NOT_VERIFIED"
        source["verified_orderable_cash_usd"] = None
        row = self.instruction(self.build(source, buy_plan()), "JPM")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("VERIFIED_ORDERABLE_CASH_REQUIRED", row["blockers"])

    def test_expected_sale_proceeds_only_blocks_buy(self):
        plan = buy_plan()
        plan["positions"][1]["order_intent_terms"]["funding_source"] = "PENDING_SELL_PROCEEDS"
        row = self.instruction(self.build(source_for_buy(), plan), "JPM")
        self.assertIn("PENDING_SELL_FILL_RECONCILIATION", row["blockers"])
        self.assertEqual(row["state"], "ORDER_BLOCKED")

    def test_unapproved_production_target_blocks_buy(self):
        plan = buy_plan()
        plan["positions"][1]["target_status"] = "PROVISIONAL"
        row = self.instruction(self.build(source_for_buy(), plan), "JPM")
        self.assertIn("PRODUCTION_TARGET_NOT_APPROVED", row["blockers"])

    def test_new_position_over_half_target_blocks_without_clipping(self):
        plan = buy_plan()
        plan["positions"][1]["order_intent_terms"]["proposed_quantity"] = 5
        row = self.instruction(self.build(source_for_buy(), plan), "JPM")
        self.assertEqual(row["proposed_quantity"], 5)
        self.assertIn("NEW_POSITION_INITIAL_ENTRY_EXCEEDS_50_PERCENT", row["blockers"])
        self.assertEqual(row["state"], "ORDER_BLOCKED")

    def test_hard_cap_violation_fails_closed(self):
        source = source_for_buy()
        plan = buy_plan()
        report, validation = self.compile_dashboard(source, plan)
        report["portfolio"]["current_risk"]["hard_cap_violations"] = ["POSITION_PCT:PGR"]
        hashes = {
            "risk_policy": self.risk_hash,
            "portfolio_decision": canonical_hash(report),
            "instrument_registry": file_hash(self.registry_path),
            "alert_policy": self.alert_hash,
        }
        artifact = compile_order_intent_artifact(
            report, validation, plan, source, self.policy, self.registry,
            integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
            risk_envelope_sha256=self.risk_hash, input_hashes=hashes, now=source["decision_as_of"],
        )
        row = self.instruction(artifact, "JPM")
        self.assertIn("CURRENT_HARD_CAP_VIOLATION", row["blockers"])

    def test_thesis_kill_prevents_deadband_suppression(self):
        source = source_for_sell()
        plan = sell_plan()
        plan["positions"][0]["thesis_kill"] = True
        report, validation = self.compile_dashboard(source, plan)
        report["portfolio"]["positions"][0]["deadband_status"] = "NO_TRADE_PREFERRED"
        hashes = {
            "risk_policy": self.risk_hash,
            "portfolio_decision": canonical_hash(report),
            "instrument_registry": file_hash(self.registry_path),
            "alert_policy": self.alert_hash,
        }
        artifact = compile_order_intent_artifact(
            report, validation, plan, source, self.policy, self.registry,
            integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
            risk_envelope_sha256=self.risk_hash, input_hashes=hashes, now=source["decision_as_of"],
        )
        self.assertEqual(
            self.instruction(artifact, "PGR")["state"], "ORDER_INSTRUCTION_READY",
        )

    def test_buy_source_thesis_kill_is_blocked(self):
        plan = buy_plan()
        plan["positions"][1]["thesis_kill"] = True
        row = self.instruction(self.build(source_for_buy(), plan), "JPM")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("BUY_SOURCE_THESIS_KILL_ACTIVE", row["blockers"])

    def test_buy_approved_terms_killed_is_blocked(self):
        plan = buy_plan()
        plan["positions"][1]["order_intent_terms"]["thesis_status"] = "KILLED"
        row = self.instruction(self.build(source_for_buy(), plan), "JPM")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("BUY_APPROVED_TERMS_THESIS_STATUS_KILLED", row["blockers"])

    def test_missing_instrument_classification_is_ticker_scoped(self):
        unknown_ticker = "ZZZZ.TESTONLY"
        self.assertNotIn(unknown_ticker, self.registry["instruments"])
        self.assertNotIn(unknown_ticker, self.policy["fallback_instrument_mapping"])
        plan = buy_plan()
        plan["cash_target_pct"] = 82.0
        unknown = copy.deepcopy(plan["positions"][1])
        unknown["ticker"] = unknown_ticker
        unknown["target_weight_pct"] = 8.0
        unknown["rationale"] = "Classification must be verified"
        plan["positions"].append(unknown)
        artifact = self.build(source_for_buy(), plan)
        unknown_row = self.instruction(artifact, unknown_ticker)
        self.assertEqual(unknown_row["state"], "ORDER_BLOCKED")
        self.assertIn("INSTRUMENT_CLASSIFICATION_NOT_VERIFIED", unknown_row["blockers"])
        self.assertEqual(self.instruction(artifact, "JPM")["state"], "ORDER_INSTRUCTION_READY")

    def test_lmt_candidate_classification_is_verified_but_non_actionable(self):
        candidate = load_json(CANDIDATE_PATH)
        operation = candidate["operations"][0]
        self.assertEqual((operation["op"], operation["path"]), ("add", "/instruments/LMT"))
        lmt_record = operation["value"]
        candidate_registry = copy.deepcopy(self.registry)
        candidate_registry["instruments"]["LMT"] = copy.deepcopy(lmt_record)
        plan = buy_plan()
        plan["plan_status"] = "PROVISIONAL"
        plan["cash_target_pct"] = 92.0
        lmt = copy.deepcopy(plan["positions"][0])
        lmt.update({
            "ticker": "LMT",
            "action": "HOLD",
            "target_weight_pct": 8.0,
            "target_status": "PROVISIONAL",
            "rationale": "Classification-only non-authoritative fixture",
        })
        plan["positions"] = [lmt]
        source = source_for_buy()
        original_registry, original_path = self.registry, self.registry_path
        try:
            with tempfile.TemporaryDirectory() as temp:
                candidate_path = Path(temp) / "instrument_registry.candidate.json"
                candidate_path.write_text(
                    json.dumps(candidate_registry, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                source["identity_registry_version"] = candidate_registry["registry_version"]
                source["identity_registry_hash"] = file_hash(candidate_path)
                self.registry, self.registry_path = candidate_registry, candidate_path
                artifact = self.build(source, plan)
        finally:
            self.registry, self.registry_path = original_registry, original_path
        row = self.instruction(artifact, "LMT")
        self.assertIsNone(row["instrument_identity"])
        mapping, issue = intent._instrument_mapping("LMT", self.policy, candidate_registry)
        self.assertIsNone(issue)
        self.assertEqual(mapping["instrument_class"], "NORMAL_STOCK")
        self.assertEqual(mapping["leverage_factor"], 1.0)
        self.assertFalse(mapping["growth_ai_semiconductor_cluster"])
        self.assertFalse(lmt_record["watchlist_approved"])
        self.assertFalse(lmt_record["new_buy_instrument_approved"])
        self.assertFalse(lmt_record["short_sale_approved"])
        self.assertEqual(row["state"], "NO_ORDER")
        self.assertNotEqual(row["state"], "ORDER_INSTRUCTION_READY")
        self.assertNotIn("INSTRUMENT_CLASSIFICATION_NOT_VERIFIED", row["blockers"])
        self.assertFalse(artifact["order_authority"])
        self.assertIsNone(artifact["execution_quantity"])
        self.assertFalse(artifact["automatic_order"])
        self.assertEqual(artifact["broker_submission"], "DISABLED")

    def test_forged_identity_registry_hash_blocks_only_actionable_ticker(self):
        source = source_for_buy()
        source["identity_registry_hash"] = "0" * 64
        artifact = self.build(source, buy_plan())
        jpm = self.instruction(artifact, "JPM")
        pgr = self.instruction(artifact, "PGR")
        self.assertEqual(jpm["state"], "ORDER_BLOCKED")
        self.assertIn("INTEGRATED_AUTHORITY_SNAPSHOT_PROVENANCE_MISMATCH", jpm["blockers"])
        self.assertEqual(pgr["state"], "NO_ORDER")
        self.assertNotIn("INTEGRATED_AUTHORITY_SNAPSHOT_PROVENANCE_MISMATCH", pgr["blockers"])

    def test_duplicate_same_session_same_decision_is_suppressed(self):
        artifact = self.build()
        delivery_id = artifact["delivery"]["delivery_id"]
        result = plan_delivery(artifact, successful_delivery_ids={delivery_id})
        self.assertEqual(result["status"], "DUPLICATE_SUPPRESSED")
        self.assertFalse(result["delivery_attempted"])

    def test_expired_instruction_is_not_reusable(self):
        artifact = self.build(now="2026-08-23T00:00:00+00:00")
        row = self.instruction(artifact, "JPM")
        self.assertEqual(row["state"], "ORDER_EXPIRED")
        self.assertEqual(artifact["delivery"]["status"], "NOT_ELIGIBLE")

    def test_last_known_evidence_cannot_be_current_intent(self):
        source = source_for_buy()
        plan = buy_plan()
        report, validation = self.compile_dashboard(source, plan)
        report["evidence"]["current_freshness"] = "HISTORICAL_REPLAY"
        report["current_context"]["verified"] = False
        hashes = {
            "risk_policy": self.risk_hash,
            "portfolio_decision": canonical_hash(report),
            "instrument_registry": file_hash(self.registry_path),
            "alert_policy": self.alert_hash,
        }
        artifact = compile_order_intent_artifact(
            report, validation, plan, source, self.policy, self.registry,
            integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
            risk_envelope_sha256=self.risk_hash, input_hashes=hashes, now=source["decision_as_of"],
        )
        row = self.instruction(artifact, "JPM")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("CURRENT_SESSION_EVIDENCE_NOT_VERIFIED", row["blockers"])

    def test_manual_and_scheduled_have_identical_semantics(self):
        manual = self.build()
        scheduled = self.build(trigger_provenance={
            "trigger_type": "SCHEDULED_GENUINE",
            "run_provenance_status": "VERIFIED_SCHEDULED_GENUINE",
            "actual_scheduled_run": True,
            "scheduled_occurrence_id": "scheduled-20260822",
            "operational_grade": "GRADE_A_CANDIDATE",
            "scheduled_maturity_promoted": False,
        })
        self.assertEqual(manual["semantic_digest"], scheduled["semantic_digest"])
        self.assertEqual(
            [item["instruction_id"] for item in manual["instructions"]],
            [item["instruction_id"] for item in scheduled["instructions"]],
        )
        self.assertNotEqual(manual["trigger_provenance"], scheduled["trigger_provenance"])

    def test_run_metadata_does_not_change_stable_intent_identity(self):
        source, plan = source_for_buy(), buy_plan()
        first_report, first_validation = self.compile_dashboard(source, plan)
        second_report = copy.deepcopy(first_report)
        second_validation = copy.deepcopy(first_validation)
        second_report["run_id"] = "order-intent-test-retry"
        second_report["generated_at"] = "2026-08-21T22:00:01+00:00"
        second_validation["run_id"] = "order-intent-test-retry"
        second_validation["generated_at"] = "2026-08-21T22:00:01+00:00"

        def compile_from(report, validation):
            return compile_order_intent_artifact(
                report, validation, plan, source, self.policy, self.registry,
                integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
                risk_envelope_sha256=self.risk_hash,
                input_hashes={
                    "portfolio_evidence": canonical_hash(source),
                    "decision_plan": canonical_hash(plan),
                    "portfolio_decision": canonical_hash(report),
                    "validation_report": canonical_hash(validation),
                    "risk_policy": self.risk_hash,
                    "instrument_registry": file_hash(self.registry_path),
                    "alert_policy": self.alert_hash,
                },
                now=source["decision_as_of"],
            )

        first = compile_from(first_report, first_validation)
        second = compile_from(second_report, second_validation)
        self.assertNotEqual(
            first["input_provenance_digest"], second["input_provenance_digest"],
        )
        self.assertEqual(first["decision_digest"], second["decision_digest"])
        self.assertEqual(first["semantic_digest"], second["semantic_digest"])
        self.assertEqual(
            [item["instruction_id"] for item in first["instructions"]],
            [item["instruction_id"] for item in second["instructions"]],
        )
        self.assertEqual(first["delivery"]["delivery_id"], second["delivery"]["delivery_id"])

    def test_delivery_failure_does_not_mutate_or_remove_artifact(self):
        artifact = self.build()
        original = copy.deepcopy(artifact)
        with tempfile.TemporaryDirectory() as temp:
            path = write_order_intent_artifact(Path(temp) / "intent.json", artifact)
            before = path.read_bytes()
            delivery = plan_delivery(artifact, successful_delivery_ids=set(), delivery_error="TEST_FAILURE")
            self.assertEqual(delivery["status"], "DELIVERY_FAILED")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(artifact, original)

    def test_authority_invariants_hold_for_every_instruction(self):
        artifact = self.build()
        self.assertFalse(artifact["order_authority"])
        self.assertIsNone(artifact["execution_quantity"])
        self.assertFalse(artifact["automatic_order"])
        self.assertEqual(artifact["submission_status"], "NOT_SUBMITTED")
        self.assertEqual(artifact["broker_submission"], "DISABLED")
        for row in artifact["instructions"]:
            self.assertFalse(row["order_authority"])
            self.assertIsNone(row["execution_quantity"])
            self.assertFalse(row["automatic_order"])
            self.assertEqual(row["submission_status"], "NOT_SUBMITTED")

    def test_no_order_modify_cancel_gateway_is_called(self):
        with patch("future_order_shadow.build_gateway_dry_run") as gateway:
            self.build()
            gateway.assert_not_called()
        source = (SCRIPTS / "portfolio_decision_order_intent.py").read_text(encoding="utf-8")
        for forbidden in ("ust20000", "ust20001", "ust20002", "ust20003", "/api/us/ordr"):
            self.assertNotIn(forbidden, source)

    def test_inputs_and_portfolio_facts_are_not_mutated(self):
        source = source_for_buy()
        plan = buy_plan()
        before_source, before_plan = copy.deepcopy(source), copy.deepcopy(plan)
        self.build(source, plan)
        self.assertEqual(source, before_source)
        self.assertEqual(plan, before_plan)

    def test_absent_exact_request_accounting_is_not_inferred_zero(self):
        artifact = self.build()
        self.assertIn(artifact["request_accounting_status"], {"PARTIAL", "NOT_VERIFIED"})
        self.assertEqual(artifact["order_endpoint_evidence"], "STATICALLY_BLOCKED")
        self.assertNotIn("order_endpoint_call_count", artifact)

    def test_risk_envelope_hash_mismatch_blocks_ready(self):
        source, plan = source_for_buy(), buy_plan()
        report, validation = self.compile_dashboard(source, plan)
        artifact = compile_order_intent_artifact(
            report, validation, plan, source, self.policy, self.registry,
            integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
            risk_envelope_sha256=self.risk_hash,
            input_hashes={
                "risk_policy": "0" * 64,
                "instrument_registry": file_hash(self.registry_path),
                "alert_policy": self.alert_hash,
            },
            now=source["decision_as_of"],
        )
        self.assertIn("RISK_ENVELOPE_HASH_NOT_VERIFIED", artifact["run_blockers"])
        self.assertEqual(self.instruction(artifact, "JPM")["state"], "ORDER_BLOCKED")

    def test_unimplemented_price_rule_fails_closed(self):
        plan = buy_plan()
        terms = plan["positions"][1]["order_intent_terms"]
        terms["order_type"] = "PRICE_RULE"
        terms["limit_price"] = None
        terms["approved_price_rule"] = "NEXT_REGULAR_SESSION_LIMIT_RULE_V1"
        row = self.instruction(self.build(source_for_buy(), plan), "JPM")
        self.assertIn("APPROVED_PRICE_RULE_RUNTIME_NOT_IMPLEMENTED", row["blockers"])

    def test_missing_quantity_fails_closed_without_assumption(self):
        source, plan = source_for_buy(), buy_plan()
        report, validation = self.compile_dashboard(source, plan)
        del plan["positions"][1]["order_intent_terms"]["proposed_quantity"]
        artifact = compile_order_intent_artifact(
            report, validation, plan, source, self.policy, self.registry,
            integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
            risk_envelope_sha256=self.risk_hash,
            input_hashes={
                "risk_policy": self.risk_hash,
                "instrument_registry": file_hash(self.registry_path),
                "alert_policy": self.alert_hash,
            },
            now=source["decision_as_of"],
        )
        row = self.instruction(artifact, "JPM")
        self.assertIsNone(row["proposed_quantity"])
        self.assertIn("PROPOSED_QUANTITY_NOT_APPROVED", row["blockers"])

    def test_artifact_validates_against_schema(self):
        artifact = self.build()
        self.assertEqual(validate_instance(artifact, ORDER_INTENT_SCHEMA), [])

    def test_fixed_limit_artifacts_ignore_manual_session_arguments(self):
        for source, plan in ((source_for_buy(), buy_plan()), (source_for_sell(), sell_plan()),
                             (source_for_sell(), sell_plan(action="EXIT"))):
            expected = self.build(source, plan)
            with patch.object(intent, "_manual_session_window",
                              side_effect=AssertionError("Fixed LIMIT session behavior must stay unchanged")) as gate:
                actual = self.build(source, plan, current_session_context={"context_status": "NOT_VERIFIED"})
                gate.assert_not_called()
            self.assertEqual(actual, expected)

    def test_dashboard_run_writes_independent_intent_and_manifest_hash(self):
        source, plan = source_for_buy(), buy_plan()
        report, validation = self.compile_dashboard(source, plan)
        artifact = self.build(source, plan)
        with tempfile.TemporaryDirectory(dir=ROOT / "manage-us-stock-strategy/tests") as temp:
            run_dir = write_run(
                report, validation, output_root=Path(temp), root=ROOT,
                source_paths={"portfolio_evidence": None, "decision_plan": None},
                implementation_paths=implementation_provenance_paths(DEFAULT_RISK_POLICY),
                order_intent_artifact=artifact,
            )
            intent_path = run_dir / "portfolio-decision-order-intent.json"
            manifest = load_json(run_dir / "run-manifest.json")
            self.assertTrue(intent_path.is_file())
            self.assertEqual(file_hash(intent_path), manifest["artifact_hashes"][intent_path.name])


class ManualSellRuleTests(unittest.TestCase):
    setUp = OrderIntentOnlyTests.setUp
    instruction = staticmethod(OrderIntentOnlyTests.instruction)

    def inputs(self, *, source=None, plan=None, opened="2026-08-21T13:30:00+00:00",
               closed="2026-08-21T20:00:00+00:00", now="2026-08-21T14:00:00+00:00"):
        source = source if source is not None else source_for_sell()
        plan = plan if plan is not None else sell_plan()
        for key in ("decision_as_of", "observed_at", "broker_snapshot_as_of"):
            source[key] = now
        source["broker_observed_state"]["as_of"] = now
        source["broker_observed_state"]["open_order_evidence"]["retrieved_at"] = now
        source["market_phase"] = "REGULAR_INTRADAY"
        source["session_authority_market_phase"] = "CORE_OPEN"
        for bar in source["last_verified_finalized_bars"]:
            bar["bar"]["provider_timestamp"] = now
        plan["as_of"] = now
        plan["evidence_binding"]["expected_decision_as_of"] = now
        for position in plan["positions"]:
            terms = position.get("order_intent_terms")
            if terms is not None:
                terms.update(limit_price=None, approved_price_rule=MANUAL_SELL_PRICE_RULE,
                             valid_from=opened, valid_until=closed)
        bind_unit_identity_provenance(source)
        hashes = {"portfolio_evidence": hashlib.sha256(_fixture.evidence_raw_bytes(source)).hexdigest(),
                  "risk_policy": self.risk_hash, "instrument_registry": file_hash(self.registry_path),
                  "alert_policy": self.alert_hash,
                  "alert_policy": self.alert_hash}
        context = _fixture.current_context(source, hashes["portfolio_evidence"])
        authority = _fixture.canonical_runtime_resolver(source)()
        authority.current_date_session = SimpleNamespace(
            session_date=opened[:10], core_open_at=opened, core_close_at=closed,
        )
        report, validation = compile_dashboard(
            source, plan, self.policy, registry=self.registry,
            run_id="manual-rule-test", generated_at=now, evidence_sha256=hashes["portfolio_evidence"],
            current_session_context=context, current_session_authority_resolver=lambda *a, **k: authority,
        )
        self.assertEqual(validation["status"], "PASS", validation)
        hashes.update(portfolio_decision=canonical_hash(report), validation_report=canonical_hash(validation),
                      decision_plan=canonical_hash(plan))
        return dict(report=report, validation=validation, plan=plan, evidence=source,
                    integrated_snapshot=unit_identity_snapshot(source), alert_policy=self.alert_policy,
                    risk_policy=self.policy, registry=self.registry, risk_envelope_sha256=self.risk_hash,
                    input_hashes=hashes, now=now, current_session_context=context,
                    current_session_authority_resolver=lambda *a, **k: authority), authority

    def row(self, args):
        return self.instruction(compile_order_intent_artifact(**args), "PGR")

    def assert_blocked(self, args, reason=None):
        row = self.row(args)
        self.assertEqual(row["state"], "ORDER_BLOCKED", row["blockers"])
        self.assertEqual(row["risk_gate_status"], "BLOCKED")
        if reason:
            self.assertIn(reason, row["blockers"])
        return row

    def test_manual_sell_ready_with_null_prices_and_firewall(self):
        args, _ = self.inputs()
        row = self.row(args)
        self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY", row["blockers"])
        self.assertEqual(row["risk_gate_status"], "PASS")
        self.assertEqual((row["side"], row["order_type"], row["time_in_force"]), ("SELL", "LIMIT", "DAY"))
        self.assertIsNone(row["limit_price"])
        self.assertIsNone(row["estimated_order_value"])
        self.assertEqual(row["canonical_reference_price"], 200)
        self.assertEqual(row["market_session_date"], args["evidence"]["expected_completed_us_session"])
        self.assertNotEqual(row["market_session_date"], args["now"][:10])
        for item in (row, compile_order_intent_artifact(**args)):
            self.assertFalse(item["order_authority"])
            self.assertIsNone(item["execution_quantity"])
            self.assertFalse(item["automatic_order"])
            self.assertFalse(item["portfolio_mutation"])
            self.assertEqual(item["broker_submission"], "DISABLED")
            self.assertEqual(item["submission_status"], "NOT_SUBMITTED")

    def test_projection_called_with_reference_proceeds_only(self):
        args, _ = self.inputs()
        before = copy.deepcopy({k: v for k, v in args.items() if not callable(v)})
        with patch.object(intent, "_projected_risk", wraps=intent._projected_risk) as projection, \
                patch.object(intent, "calculate_risk_metrics", wraps=intent.calculate_risk_metrics) as metrics:
            row = self.row(args)
        projection.assert_called_once()
        self.assertEqual(projection.call_args.args[4], Decimal(5) * Decimal(200))
        self.assertEqual(metrics.call_args.args[1], Decimal(90))
        self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY")
        self.assertIsNone(row["estimated_order_value"])
        self.assertIsNone(row["limit_price"])
        self.assertEqual({k: v for k, v in args.items() if not callable(v)}, before)

    def test_buy_rule_and_invalid_rule_combinations_blocked(self):
        cases = [
            {"approved_price_rule": "UNKNOWN"}, {"approved_price_rule": ""},
            {"approved_price_rule": MANUAL_SELL_PRICE_RULE[:-1]},
            {"approved_price_rule": MANUAL_SELL_PRICE_RULE.replace("V1", "V2")},
            {"approved_price_rule": " " + MANUAL_SELL_PRICE_RULE},
            {"approved_price_rule": MANUAL_SELL_PRICE_RULE.lower()},
            {"approved_price_rule": None}, {"time_in_force": None},
            {"limit_price": 200}, {"order_type": "PRICE_RULE"},
        ]
        for change in cases:
            with self.subTest(change=change):
                args, _ = self.inputs()
                args["plan"]["positions"][0]["order_intent_terms"].update(change)
                self.assert_blocked(args)
        args, _ = self.inputs(source=source_for_buy(), plan=buy_plan())
        row = self.instruction(compile_order_intent_artifact(**args), "JPM")
        self.assertEqual(row["state"], "ORDER_BLOCKED")
        self.assertIn("APPROVED_LIMIT_PRICE_REQUIRED", row["blockers"])

    def test_missing_or_blocked_projection_cannot_pass(self):
        args, _ = self.inputs()
        with patch.object(intent, "_projected_risk", wraps=intent._projected_risk) as original:
            self.row(args)
        complete_risk, _ = intent._projected_risk(*original.call_args.args)
        cases = [(None, []), ({}, []), (complete_risk, ["TEST_PROJECTION_BLOCKED"])]
        for field in ("checks", "cash_pct", "hard_cap_violations", "status"):
            risk = copy.deepcopy(complete_risk)
            risk.pop(field)
            cases.append((risk, []))
        for metric in complete_risk["checks"]:
            risk = copy.deepcopy(complete_risk)
            risk["checks"] = [item for item in risk["checks"] if item["metric"] != metric["metric"]]
            cases.append((risk, []))
        for status in ("BLOCKED", "VIOLATION", None):
            risk = copy.deepcopy(complete_risk)
            risk["status"] = status
            cases.append((risk, []))
        for field, value in (("value", None), ("status", "BLOCKED"), ("status", "VIOLATION")):
            risk = copy.deepcopy(complete_risk)
            risk["checks"][0][field] = value
            cases.append((risk, []))
        for risk, blockers in cases:
            with self.subTest(risk=risk, blockers=blockers), \
                    patch.object(intent, "_projected_risk", return_value=(risk, blockers.copy())) as projection:
                self.assert_blocked(args)
                projection.assert_called_once()

    def test_missing_threshold_mapping_price_and_quantity_fail_closed(self):
        for section, field in (("cash", "hard_floor_pct"),
                               ("single_normal_stock", "hard_cap_pct"),
                               ("growth_ai_semiconductor_cluster", "book_hard_cap_pct")):
            for value in (None, "not-numeric"):
                with self.subTest(section=section, value=value):
                    args, _ = self.inputs()
                    args["risk_policy"] = copy.deepcopy(self.policy)
                    args["risk_policy"][section][field] = value
                    self.assert_blocked(args)
        args, _ = self.inputs()
        args["risk_policy"] = copy.deepcopy(self.policy)
        del args["risk_policy"]["cash"]["hard_floor_pct"]
        self.assert_blocked(args)
        for field in ("leverage_factor", "growth_ai_semiconductor_cluster", "instrument_class"):
            args, _ = self.inputs()
            args["risk_policy"] = copy.deepcopy(self.policy)
            del args["risk_policy"]["fallback_instrument_mapping"]["PGR"][field]
            self.assert_blocked(args)
        for field in ("canonical_price_usd", "current_quantity"):
            args, _ = self.inputs()
            args["report"]["portfolio"]["positions"][0][field]["value"] = None
            self.assert_blocked(args)
        for quantity in (None,):
            args, _ = self.inputs()
            args["plan"]["positions"][0]["order_intent_terms"]["proposed_quantity"] = quantity
            self.assert_blocked(args)

    def test_schema_invalid_tif_and_quantity_are_rejected_without_schema_changes(self):
        for field, value in (("time_in_force", "GTC"), ("proposed_quantity", 0),
                             ("proposed_quantity", True)):
            args, _ = self.inputs()
            args["plan"]["positions"][0]["order_intent_terms"][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(intent.OrderIntentContractError):
                    self.row(args)

    def test_target_risk_incomplete_or_violation_blocks(self):
        for risk in (None, {}, {"status": "BLOCKED", "hard_cap_violations": []},
                     {"status": "VIOLATION", "hard_cap_violations": ["CASH_PCT"]}):
            with self.subTest(risk=risk):
                args, _ = self.inputs()
                args["report"]["portfolio"]["target_reference_risk"] = risk
                self.assert_blocked(args)

    def diversified_inputs(self, quantities=(6, 3)):
        """A consistent $10,000 fixture with 5% cash and diversified 1x holdings."""
        source = source_for_sell()
        positions = {"PGR": 15, "JPM": 15, "CME": 13, "V": 13, "NBIS": 13, "LMT": 13, "TOST": 13}
        source["broker_observed_state"]["cash"]["foreign_currency_deposit"] = 500
        source["verified_orderable_cash_usd"] = 500
        holding = source["broker_observed_state"]["holdings"][0]
        bar = source["last_verified_finalized_bars"][0]
        source["broker_observed_state"]["holdings"] = []
        source["last_verified_finalized_bars"] = []
        plan = sell_plan()
        plan["positions"] = []
        for ticker, quantity in positions.items():
            item = copy.deepcopy(holding)
            item.update(ticker=ticker, security_name=ticker, settled_quantity=quantity,
                        held_quantity=quantity, available_shares=quantity)
            source["broker_observed_state"]["holdings"].append(item)
            item = copy.deepcopy(bar)
            item["ticker"] = ticker
            item["bar"].update(ticker=ticker, price=100)
            source["last_verified_finalized_bars"].append(item)
            target = 9 if ticker in {"PGR", "JPM"} else quantity
            position = {"ticker": ticker, "action": "TRIM" if ticker in {"PGR", "JPM"} else "HOLD",
                        "target_weight_pct": target, "rationale": "Synthetic independent risk test",
                        "investment_horizon": "transition", "target_status": "APPROVED"}
            if ticker in {"PGR", "JPM"}:
                position["order_intent_terms"] = order_terms(
                    quantity=quantities[0 if ticker == "PGR" else 1], funding_source="NOT_APPLICABLE")
            plan["positions"].append(position)
        plan["cash_target_pct"] = 17
        return self.inputs(source=source, plan=plan)

    def test_cash_floor_pass_and_failure_use_independent_sell(self):
        args, _ = self.diversified_inputs()
        with patch.object(intent, "calculate_risk_metrics", wraps=intent.calculate_risk_metrics) as metrics:
            artifact = compile_order_intent_artifact(**args)
        self.assertEqual([call.args[1] for call in metrics.call_args_list], [Decimal(11), Decimal(8)])
        self.assertEqual(self.instruction(artifact, "PGR")["state"], "ORDER_INSTRUCTION_READY")
        jpm = self.instruction(artifact, "JPM")
        self.assertEqual(jpm["state"], "ORDER_BLOCKED")
        self.assertIn("PROJECTED_HARD_CAP_VIOLATION:CASH_PCT", jpm["blockers"])
        self.assertEqual(args["report"]["cash_semantics"]["verified_orderable_cash_usd"]["value"], 500)

    def test_combined_sells_that_clear_floor_do_not_make_individuals_ready(self):
        args, _ = self.diversified_inputs((3, 3))
        artifact = compile_order_intent_artifact(**args)
        for ticker in ("PGR", "JPM"):
            row = self.instruction(artifact, ticker)
            self.assertEqual(row["state"], "ORDER_BLOCKED")
            self.assertIn("PROJECTED_HARD_CAP_VIOLATION:CASH_PCT", row["blockers"])

    def test_other_hard_risk_remaining_blocks_sell(self):
        args, _ = self.inputs()
        args["plan"]["positions"][0]["order_intent_terms"]["proposed_quantity"] = 1
        self.assert_blocked(args, "PROJECTED_HARD_CAP_VIOLATION:POSITION_PCT:PGR")

    def test_sell_proceeds_do_not_fund_a_buy(self):
        source, plan = source_for_sell(), sell_plan()
        source["verified_orderable_cash_usd"] = 0
        plan["cash_target_pct"] = 82
        plan["positions"].append(buy_plan()["positions"][1])
        args, _ = self.inputs(source=source, plan=plan)
        terms = args["plan"]["positions"][1]["order_intent_terms"]
        terms.update(approved_price_rule=None, limit_price=100)
        artifact = compile_order_intent_artifact(**args)
        self.assertEqual(self.instruction(artifact, "PGR")["state"], "ORDER_INSTRUCTION_READY")
        buy = self.instruction(artifact, "JPM")
        self.assertEqual(buy["state"], "ORDER_BLOCKED")
        self.assertEqual(buy["verified_orderable_cash"], 0)
        self.assertIn("VERIFIED_ORDERABLE_CASH_INSUFFICIENT", buy["blockers"])
        terms["funding_source"] = "PENDING_SELL_PROCEEDS"
        buy = self.instruction(compile_order_intent_artifact(**args), "JPM")
        self.assertIn("PENDING_SELL_FILL_RECONCILIATION", buy["blockers"])

    def test_session_requires_current_verified_core_open(self):
        for phase in ("PRE_CORE", "POST_CORE", "NON_TRADING_DATE", None):
            with self.subTest(phase=phase):
                args, authority = self.inputs()
                authority.market_phase = phase
                self.assert_blocked(args, "MANUAL_RULE_CORE_OPEN_REQUIRED")
        args, authority = self.inputs()
        authority.authority_status = "NOT_VERIFIED"
        self.assert_blocked(args, "MANUAL_RULE_CURRENT_SESSION_AUTHORITY_NOT_VERIFIED")
        for context in (None, {}, [], {"context_status": "NOT_VERIFIED"}):
            args, _ = self.inputs()
            args["current_session_context"] = context
            self.assert_blocked(args)
        args, authority = self.inputs()
        authority.current_date_session = None
        self.assert_blocked(args, "MANUAL_RULE_CORE_WINDOW_NOT_VERIFIED")

    def test_validity_start_inclusive_and_end_exclusive(self):
        args, _ = self.inputs()
        terms = args["plan"]["positions"][0]["order_intent_terms"]
        terms["valid_from"] = "2026-08-21T14:01:00+00:00"
        self.assert_blocked(args, "MANUAL_RULE_VALIDITY_NOT_STARTED")
        terms["valid_from"] = args["now"]
        self.assertEqual(self.row(args)["state"], "ORDER_INSTRUCTION_READY")
        terms["valid_until"] = "2026-08-21T14:05:00+00:00"
        args["now"] = terms["valid_until"]
        self.assertEqual(self.row(args)["state"], "ORDER_EXPIRED")

    def test_early_close_and_dst_use_supplied_authority_boundary(self):
        for opened, closed, now in (
            ("2026-08-21T13:30:00+00:00", "2026-08-21T17:00:00+00:00", "2026-08-21T16:55:00+00:00"),
            ("2026-11-27T14:30:00+00:00", "2026-11-27T18:00:00+00:00", "2026-11-27T17:55:00+00:00"),
        ):
            with self.subTest(opened=opened):
                args, authority = self.inputs(opened=opened, closed=closed, now=now)
                args["plan"]["positions"][0]["order_intent_terms"]["valid_until"] = closed[:11] + "22:00:00+00:00"
                row = self.row(args)
                self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY", row["blockers"])
                self.assertEqual(row["valid_until"], closed)
                args["now"] = closed
                authority.market_phase = "POST_CORE"
                self.assertEqual(self.row(args)["state"], "ORDER_EXPIRED")

    def test_next_session_never_rolls_over(self):
        args, authority = self.inputs()
        terms = args["plan"]["positions"][0]["order_intent_terms"]
        terms["valid_until"] = "2026-08-25T20:00:00+00:00"
        authority.current_date_session = SimpleNamespace(
            session_date="2026-08-24", core_open_at="2026-08-24T13:30:00+00:00",
            core_close_at="2026-08-24T20:00:00+00:00")
        row = self.assert_blocked(args, "MANUAL_RULE_SESSION_ROLLOVER_FORBIDDEN")
        args["now"] = "2026-08-24T14:00:00+00:00"
        row = self.row(args)
        self.assertEqual(row["state"], "ORDER_EXPIRED")
        self.assertIn("MANUAL_RULE_SESSION_ROLLOVER_FORBIDDEN", row["blockers"])

    def test_freshness_is_checked_at_evaluation_and_bounds_identity(self):
        args, _ = self.inputs()
        row = self.row(args)
        self.assertEqual(row["valid_until"], "2026-08-21T14:15:00+00:00")
        args["now"] = "2026-08-21T14:14:59+00:00"
        self.assertEqual(self.row(args)["state"], "ORDER_INSTRUCTION_READY")
        args["now"] = "2026-08-21T14:15:00+00:00"
        stale = self.row(args)
        self.assertEqual(stale["state"], "ORDER_EXPIRED")
        self.assertEqual(stale["risk_gate_status"], "BLOCKED")
        self.assertIn("BROKER_SNAPSHOT_STALE", stale["blockers"])
        self.assertEqual(row["instruction_id"], stale["instruction_id"])
        self.assertNotEqual(row["record_hash"], stale["record_hash"])
        args, _ = self.inputs()
        args["evidence"]["broker_snapshot_as_of"] = None
        self.assert_blocked(args, "MANUAL_RULE_CURRENT_FRESHNESS_NOT_VERIFIED")

    def test_future_context_and_evidence_are_blocked(self):
        for field in ("observed_at", "broker_snapshot_as_of", "decision_as_of"):
            args, _ = self.inputs()
            args["evidence"][field] = "2026-08-21T14:01:00+00:00"
            self.assert_blocked(args, "MANUAL_RULE_EVIDENCE_FROM_FUTURE")
        args, _ = self.inputs()
        args["current_session_context"]["context_generated_at"] = "2026-08-21T14:01:00+00:00"
        self.assert_blocked(args, "MANUAL_RULE_CURRENT_CONTEXT_TIME_NOT_VERIFIED")

    def test_id_hash_tracks_actual_semantics_and_output_expiry(self):
        args, authority = self.inputs()
        original = self.row(args)
        self.assertEqual(original, self.row(args))
        semantic = {field: original[field] for field in (
            "decision_digest", "market_session_date", "ticker", "side", "proposed_quantity",
            "order_type", "limit_price", "approved_price_rule", "time_in_force", "valid_from", "valid_until")}
        self.assertEqual(original["instruction_id"], canonical_hash(semantic))
        unhashed = {k: v for k, v in original.items() if k != "record_hash"}
        self.assertEqual(original["record_hash"], canonical_hash(unhashed))
        terms = args["plan"]["positions"][0]["order_intent_terms"]
        for field, value in (("proposed_quantity", 4), ("time_in_force", None),
                             ("approved_price_rule", MANUAL_SELL_PRICE_RULE.replace("V1", "V2")),
                             ("valid_until", "2026-08-21T14:10:00+00:00")):
            saved = terms[field]
            terms[field] = value
            self.assertNotEqual(original["instruction_id"], self.row(args)["instruction_id"])
            terms[field] = saved
        authority.current_date_session.core_close_at = "2026-08-21T14:05:00+00:00"
        changed = self.row(args)
        self.assertNotEqual(original["instruction_id"], changed["instruction_id"])
        semantic["valid_until"] = changed["valid_until"]
        self.assertEqual(changed["instruction_id"], canonical_hash(semantic))

    def test_historical_and_default_clock_do_not_promote_prior_artifacts(self):
        args, _ = self.inputs()
        args["report"]["evidence"]["current_freshness"] = "HISTORICAL_REPLAY"
        self.assert_blocked(args, "CURRENT_SESSION_EVIDENCE_NOT_VERIFIED")
        args, _ = self.inputs()
        args.pop("current_session_context")
        historical = compile_order_intent_artifact(**args)
        before = copy.deepcopy(historical)
        compile_order_intent_artifact(**args)
        self.assertEqual(historical, before)
        args, _ = self.inputs()
        args.pop("now")
        with patch.object(intent, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime.fromisoformat("2026-08-24T14:00:00+00:00")
            self.assertEqual(self.row(args)["state"], "ORDER_EXPIRED")

    def test_existing_deadband_and_input_binding_gates_remain(self):
        args, _ = self.inputs()
        report = args["report"]
        report["portfolio"]["current_risk"]["hard_cap_violations"] = []
        report["portfolio"]["positions"][0]["deadband_status"] = "NO_TRADE_PREFERRED"
        self.assertEqual(self.row(args)["state"], "NO_ORDER")
        for field, value in (("expected_evidence_sha256", "0" * 64),
                             ("expected_completed_us_session", "2026-08-19"),
                             ("calendar_hash", "0" * 64)):
            args, _ = self.inputs()
            args["current_session_context"][field] = value
            self.assert_blocked(args)
        args, _ = self.inputs()
        args["input_hashes"]["risk_policy"] = "0" * 64
        self.assert_blocked(args, "RISK_ENVELOPE_HASH_NOT_VERIFIED")

    def test_no_broker_quote_http_or_socket_call_and_no_input_mutation(self):
        args, _ = self.inputs()
        before = copy.deepcopy({k: v for k, v in args.items() if not callable(v)})
        with ExitStack() as stack:
            spies = [stack.enter_context(patch(name, side_effect=AssertionError("Network forbidden"))) for name in (
                "socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                "urllib.request.urlopen", "http.client.HTTPConnection.request",
                "future_order_shadow.build_gateway_dry_run",
            )]
            self.assertEqual(self.row(args)["state"], "ORDER_INSTRUCTION_READY")
            for spy in spies:
                spy.assert_not_called()
        self.assertEqual({k: v for k, v in args.items() if not callable(v)}, before)

    def test_missing_portfolio_inputs_and_reference_price_block(self):
        for field in ("nav_usd", "current_cash_usd"):
            args, _ = self.inputs()
            owner = args["report"]["portfolio" if field == "nav_usd" else "cash_semantics"]
            owner[field]["value"] = None
            self.assert_blocked(args)
        args, _ = self.inputs()
        for item in args["evidence"]["last_verified_finalized_bars"]:
            if item["ticker"] == "PGR":
                item["bar"]["price"] = None
        self.assert_blocked(args, "CANONICAL_REFERENCE_PRICE_NOT_VERIFIED")
        for missing in ("mapping", "price", "quantity"):
            args, _ = self.diversified_inputs()
            row = args["report"]["portfolio"]["positions"][-1]
            if missing == "mapping":
                row["ticker"] = "UNMAPPED.TESTONLY"
            else:
                row["canonical_price_usd" if missing == "price" else "current_quantity"]["value"] = None
            self.assert_blocked(args)

    def test_plan_and_broker_evidence_gates_are_rechecked_for_manual_rule(self):
        for field, value in (("expected_run_id", "incorrect-run"),
                             ("expected_decision_as_of", "2026-08-21T13:59:00+00:00")):
            args, _ = self.inputs()
            args["plan"]["evidence_binding"][field] = value
            self.assert_blocked(args)
        for operation in ("account_holdings_read", "account_deposit_read"):
            args, _ = self.inputs()
            args["evidence"]["broker_observed_state"]["operation_statuses"][operation] = "FAIL"
            self.assert_blocked(args)
        for field, value in (("plan_status", "PROVISIONAL"),):
            args, _ = self.inputs()
            args["plan"][field] = value
            self.assert_blocked(args)


class IdentityProvenanceK3Tests(unittest.TestCase):
    instruction = staticmethod(OrderIntentOnlyTests.instruction)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args, self.snapshot, self.manifest = _fixture.session_k3_inputs(self.root)
        self.args["integrated_snapshot"] = self.snapshot
        from functools import partial
        from integrated_authority_snapshot import derive_us_market_session_authority_from_snapshot
        self.args["current_session_authority_resolver"] = partial(
            derive_us_market_session_authority_from_snapshot, self.snapshot)

    def row(self):
        return self.instruction(compile_order_intent_artifact(**self.args), "PGR")

    def test_independently_valid_unequal_authorities_are_ready(self):
        self.assertNotEqual(self.snapshot.identity.artifact["registry_version"], self.args["registry"]["registry_version"])
        self.assertNotEqual(self.snapshot.identity.registry_hash, self.args["input_hashes"]["instrument_registry"])
        digest = canonical_hash(self.args["registry"])
        self.assertNotEqual(self.snapshot.identity.registry_hash, digest)
        self.assertNotEqual(digest, self.args["input_hashes"]["instrument_registry"])
        required = self.args["alert_policy"]["decision_harness"]["instrument_registry_authority"]["required_canonical_sha256"]
        self.assertEqual(digest, required)
        row = self.row()
        self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY", row["blockers"])
        self.assertEqual(row["instrument_identity"]["identity_registry_hash"], self.snapshot.identity.registry_hash)

    def test_each_identity_provenance_mismatch_blocks(self):
        source = self.args["evidence"]
        for field in ("identity_registry_version", "identity_registry_hash", "identity_activation_cohort_id",
                      "identity_authority_id"):
            with self.subTest(field=field), patch.dict(source, {field: "f" * 64}):
                row = self.row()
                self.assertEqual(row["state"], "ORDER_BLOCKED")
                self.assertIn("INTEGRATED_AUTHORITY_SNAPSHOT_PROVENANCE_MISMATCH", row["blockers"])
        supplied = source["integrated_authority_snapshot_provenance"]
        for field in ("authority_source", "activation_cohort_id", "instrument_identity_artifact_sha256",
                      "identity_registry_version", "run_id", "snapshot_decision_as_of"):
            with self.subTest(field=field), patch.dict(supplied, {field: "invalid"}):
                self.assertIn("INTEGRATED_AUTHORITY_SNAPSHOT_PROVENANCE_MISMATCH", self.row()["blockers"])

    def test_missing_snapshot_and_unverified_status_fail_closed(self):
        with patch.dict(self.args, {"integrated_snapshot": None}):
            self.assertIn("INSTRUMENT_IDENTITY_NOT_VERIFIED", self.row()["blockers"])
        with patch.dict(self.args["evidence"], {"identity_authority_status": "NOT_VERIFIED"}):
            self.assertIn("INSTRUMENT_IDENTITY_NOT_VERIFIED", self.row()["blockers"])

    def test_real_ticker_resolver_uses_same_snapshot_without_reads(self):
        import integrated_authority_snapshot as integrated
        with patch.object(integrated, "read_once_no_reparse", side_effect=AssertionError("Authority reread")) as reads, \
             patch.object(intent, "resolve_instrument_identity_from_snapshot", wraps=integrated.resolve_instrument_identity_from_snapshot) as resolve:
            row = self.row()
        reads.assert_not_called()
        resolve.assert_called_once()
        self.assertIs(resolve.call_args.args[0], self.snapshot)
        self.assertEqual(resolve.call_args.args[1], "PGR")
        self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY")

    def test_financial_fallbacks_require_independent_identity_and_mapping(self):
        for ticker in ("PGR", "JPM", "CME", "V"):
            with self.subTest(ticker=ticker):
                self.assertNotIn(ticker, self.args["registry"]["instruments"])
                mapping, identity, blockers = intent._identity(
                    ticker, self.args["evidence"], self.args["risk_policy"], self.args["registry"], self.snapshot)
                self.assertEqual(blockers, [])
                self.assertEqual(mapping["mapping_source"], "USER_APPROVED_FALLBACK")
                self.assertEqual(identity["identity_authority_status"], "VERIFIED")
        self.args["risk_policy"]["fallback_instrument_mapping"].pop("PGR")
        self.assertIn("INSTRUMENT_CLASSIFICATION_NOT_VERIFIED", self.row()["blockers"])
        self.assertEqual(self.row()["state"], "ORDER_BLOCKED")

    def test_lmt_risk_record_cannot_verify_identity_or_authorize_order(self):
        mapping, issue = intent._instrument_mapping("LMT", self.args["risk_policy"], self.args["registry"])
        self.assertIsNone(issue)
        self.assertEqual((mapping["instrument_class"], mapping["leverage_factor"],
                          mapping["growth_ai_semiconductor_cluster"]), ("NORMAL_STOCK", Decimal(1), False))
        record = self.args["registry"]["instruments"]["LMT"]
        self.assertTrue(all(record[field] is False for field in
                            ("new_buy_instrument_approved", "watchlist_approved", "short_sale_approved")))
        resolved = intent.resolve_instrument_identity_from_snapshot(self.snapshot, "LMT", decision_as_of=self.args["now"])
        self.assertNotEqual(resolved.authority_status, "VERIFIED")
        self.assertEqual(resolved.authority_reason, "UNKNOWN_SYMBOL")
        self.args["plan"]["positions"][0]["ticker"] = "LMT"
        self.args["report"]["portfolio"]["positions"][0]["ticker"] = "LMT"
        for action in ("ADD", "TRIM", "EXIT", "HOLD"):
            with self.subTest(action=action):
                self.args["plan"]["positions"][0]["action"] = action
                row = self.instruction(compile_order_intent_artifact(**self.args), "LMT")
                self.assertIsNone(row["instrument_identity"])
                self.assertEqual(row["state"], "NO_ORDER" if action == "HOLD" else "ORDER_BLOCKED")
                if action != "HOLD":
                    self.assertIn("INSTRUMENT_IDENTITY_NOT_VERIFIED", row["blockers"])

    def test_registry_integrity_cannot_be_bypassed_by_fallback(self):
        self.assertIn("PGR", self.args["risk_policy"]["fallback_instrument_mapping"])
        original = self.args["registry"]
        invalid = copy.deepcopy(original)
        invalid["canonical_authority"] = False
        mismatch = copy.deepcopy(original)
        mismatch["registry_version"] += "-changed"
        for registry in (None, [], {}, invalid, mismatch):
            with self.subTest(registry_type=type(registry).__name__), patch.dict(self.args, {"registry": registry}):
                row = self.row()
                self.assertEqual(row["state"], "ORDER_BLOCKED")
                self.assertIn("POLICY_REGISTRY_MISMATCH", row["blockers"])

    def test_policy_canonical_mismatch_and_missing_consumed_hash_fail_closed(self):
        reference = self.args["alert_policy"]["decision_harness"]["instrument_registry_authority"]
        for field, value in (("required_canonical_sha256", "0" * 64),
                             ("canonical_path", "arbitrary/registry.json")):
            with self.subTest(field=field), patch.dict(reference, {field: value}):
                self.assertIn("POLICY_REGISTRY_MISMATCH", self.row()["blockers"])
        for field in ("instrument_registry", "alert_policy"):
            hashes = {k: v for k, v in self.args["input_hashes"].items() if k != field}
            with self.subTest(field=field), patch.dict(self.args, {"input_hashes": hashes}):
                self.assertIn("POLICY_REGISTRY_MISMATCH", self.row()["blockers"])
            with patch.dict(self.args["input_hashes"], {field: "invalid"}), \
                 self.assertRaisesRegex(intent.OrderIntentContractError, "ORDER_INTENT_SCHEMA_INVALID"):
                self.row()
        with patch.dict(self.args, {"alert_policy": None}):
            self.assertIn("POLICY_REGISTRY_MISMATCH", self.row()["blockers"])

    def test_raw_formatting_changes_provenance_but_not_canonical_binding(self):
        before = self.row()
        raw = json.dumps(self.args["registry"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(), self.args["input_hashes"]["instrument_registry"])
        self.args["registry"] = json.loads(raw)
        self.args["input_hashes"]["instrument_registry"] = hashlib.sha256(raw).hexdigest()
        after = self.row()
        self.assertEqual(after["state"], "ORDER_INSTRUCTION_READY")
        self.assertEqual(before["instruction_id"], after["instruction_id"])
        self.assertNotEqual(before["input_provenance_digest"], after["input_provenance_digest"])
        self.assertNotEqual(before["record_hash"], after["record_hash"])
        self.assertEqual(intent._risk_registry_blockers(self.args["registry"], self.args["alert_policy"], self.args["input_hashes"]), [])

    def test_false_or_missing_action_flags_do_not_add_new_gates(self):
        case = OrderIntentOnlyTests()
        case.setUp()
        for action, source, plan in (("ADD", source_for_buy(), buy_plan()),
                                      ("TRIM", source_for_sell(), sell_plan()),
                                      ("EXIT", source_for_sell(), sell_plan(action="EXIT"))):
            for missing in (False, True):
                with self.subTest(action=action, missing=missing):
                    registry = copy.deepcopy(case.registry)
                    for ticker in ("PGR", "JPM"):
                        registry["instruments"][ticker] = dict(
                            leverage_factor=1.0, leverage_factor_status="verified", theme="financials")
                        if not missing:
                            registry["instruments"][ticker].update(new_buy_instrument_approved=False,
                                watchlist_approved=False, short_sale_approved=False)
                    policy = copy.deepcopy(case.alert_policy)
                    policy["decision_harness"]["instrument_registry"] = {}
                    policy["decision_harness"]["instrument_registry_authority"]["required_canonical_sha256"] = canonical_hash(registry)
                    case.registry, case.alert_policy = registry, policy
                    case.registry_path = self.root / "approval-flags-registry.json"
                    case.registry_path.write_bytes(_fixture.evidence_raw_bytes(registry))
                    case.alert_hash = hashlib.sha256(_fixture.evidence_raw_bytes(policy)).hexdigest()
                    row = case.instruction(case.build(source, plan), "JPM" if action == "ADD" else "PGR")
                    self.assertEqual(row["state"], "ORDER_INSTRUCTION_READY", row["blockers"])
                    if action == "ADD":
                        self.assertEqual(case.instruction(case.build(source, plan), "PGR")["state"], "NO_ORDER")

    def test_historical_evidence_is_not_rewritten_or_currently_promoted(self):
        before = copy.deepcopy(self.args["evidence"])
        self.args["evidence"]["integrated_authority_snapshot_provenance"]["authority_source"] = "LEGACY_INDEPENDENT"
        historical = copy.deepcopy(self.args["evidence"])
        with patch.dict(self.args, {"integrated_snapshot": None}):
            artifact = compile_order_intent_artifact(**self.args)
        self.assertEqual(self.args["evidence"], historical)
        self.assertEqual(historical["identity_registry_hash"], before["identity_registry_hash"])
        self.assertNotEqual(artifact["run_state"], "ORDER_INSTRUCTION_READY")
        self.assertEqual(artifact["input_hashes"]["instrument_registry"], file_hash(REGISTRY_PATH))
        self.assertEqual(artifact["input_hashes"]["alert_policy"], file_hash(ALERT_POLICY_PATH))

    def test_current_inputs_snapshot_and_execution_firewall_are_immutable(self):
        import socket
        import urllib.request
        evidence_before = copy.deepcopy(self.args["evidence"])
        policy_before = copy.deepcopy(self.args["alert_policy"])
        registry_before = copy.deepcopy(self.args["registry"])
        provenance_before = self.snapshot.provenance(authority_source="K3_COMBINED_PRODUCTION")
        with patch.object(socket, "create_connection", side_effect=AssertionError("Network")) as network, \
             patch.object(urllib.request, "urlopen", side_effect=AssertionError("HTTP")) as http:
            artifact = compile_order_intent_artifact(**self.args)
        network.assert_not_called()
        http.assert_not_called()
        self.assertEqual(self.args["evidence"], evidence_before)
        self.assertEqual(self.args["alert_policy"], policy_before)
        self.assertEqual(self.args["registry"], registry_before)
        self.assertEqual(self.snapshot.provenance(authority_source="K3_COMBINED_PRODUCTION"), provenance_before)
        with self.assertRaises(TypeError):
            self.snapshot.identity.artifact["registry_version"] = "forged"
        for value in (artifact, *artifact["instructions"]):
            self.assertFalse(value["order_authority"])
            self.assertIsNone(value["execution_quantity"])
            self.assertFalse(value["automatic_order"])
            self.assertEqual(value["broker_submission"], "DISABLED")


class SessionK3StandaloneTests(unittest.TestCase):
    def run_cli(self, root, args, *, context_change=None, failure=None, numeric=False):
        import integrated_authority_snapshot as integrated
        import session_authority
        from contextlib import redirect_stdout, redirect_stderr
        from io import StringIO

        context = copy.deepcopy(args["current_session_context"])
        if context_change is not None:
            context = context_change(context)
        plan = copy.deepcopy(args["plan"])
        if numeric:
            for position in plan["positions"]:
                terms = position.get("order_intent_terms")
                if terms:
                    terms.update(limit_price=100.0, approved_price_rule=None)
        values = {"portfolio-decision": args["report"], "validation-report": args["validation"],
                  "decision-plan": plan, "portfolio-evidence": args["evidence"]}
        argv = ["intent", "--now", args["now"], "--instrument-registry", str(REGISTRY_PATH),
                "--output", str(root / "intent.json")]
        for name, value in values.items():
            path = root / (name + ".json")
            path.write_bytes(_fixture.evidence_raw_bytes(value))
            argv += ["--" + name, str(path)]
        if context is not None:
            path = root / "current-context.json"
            path.write_bytes(_fixture.evidence_raw_bytes(context))
            argv += ["--current-session-context", str(path)]
        manifest = root / integrated.COMBINED_ACTIVATION_RELATIVE_PATH
        if failure == "missing":
            manifest.unlink()
        elif failure == "invalid":
            manifest.write_text("INVALID", encoding="utf-8")
        elif failure in {"identity_hash", "session_hash"}:
            artifact = next(root.rglob("*.registry.json" if failure == "identity_hash" else "*.calendar.json"))
            artifact.write_bytes(artifact.read_bytes() + b" ")
        snapshots = []

        def load(**kwargs):
            kwargs["trusted_root"] = root
            snapshot = integrated.load_production_integrated_authority_snapshot(**kwargs)
            snapshots.append(snapshot)
            return snapshot

        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, "argv", argv))
            stack.enter_context(redirect_stdout(StringIO()))
            stack.enter_context(redirect_stderr(StringIO()))
            loader = stack.enter_context(patch.object(intent, "load_production_integrated_authority_snapshot", side_effect=load))
            reads = stack.enter_context(patch.object(integrated, "read_once_no_reparse", wraps=integrated.read_once_no_reparse))
            legacy = stack.enter_context(patch.object(session_authority, "load_active_session_calendar",
                                                      side_effect=AssertionError("Legacy forbidden")))
            network = stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")))
            evaluate = stack.enter_context(patch.object(intent, "_evaluate_current_session_context", wraps=intent._evaluate_current_session_context))
            compiler = stack.enter_context(patch.object(intent, "compile_order_intent_artifact", wraps=intent.compile_order_intent_artifact))
            writer = stack.enter_context(patch.object(intent, "write_order_intent_artifact", wraps=intent.write_order_intent_artifact))
            derive = stack.enter_context(patch.object(intent, "derive_us_market_session_authority_from_snapshot",
                                                      wraps=integrated.derive_us_market_session_authority_from_snapshot))
            exit_code = 0
            try:
                intent.main()
            except SystemExit as exc:
                exit_code = exc.code
            legacy.assert_not_called()
            network.assert_not_called()
            return SimpleNamespace(exit_code=exit_code, loader=loader, reads=reads, snapshots=snapshots,
                                   evaluate=evaluate, compiler=compiler, writer=writer, derive=derive)

    def test_owns_one_snapshot_validates_context_and_reuses_resolver(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args, snapshot, manifest = _fixture.session_k3_inputs(root)
            before = copy.deepcopy(args)
            observed = self.run_cli(root, args)
            self.assertEqual(observed.exit_code, 0)
            observed.loader.assert_called_once()
            self.assertEqual(observed.reads.call_count, 3)
            self.assertEqual(sum(c.args[0] == manifest for c in observed.reads.call_args_list), 1)
            resolver = observed.compiler.call_args.kwargs["current_session_authority_resolver"]
            self.assertIs(observed.evaluate.call_args_list[0].args[-1], resolver)
            self.assertIs(resolver.args[0], observed.snapshots[0])
            self.assertIs(observed.evaluate.call_args_list[0].args[0], observed.compiler.call_args.kwargs["current_session_context"])
            self.assertEqual(observed.evaluate.call_args_list[0].args[-2], observed.compiler.call_args.kwargs["now"])
            self.assertGreaterEqual(observed.derive.call_count, 2)
            self.assertTrue(all(c.args[0] is observed.snapshots[0] for c in observed.derive.call_args_list))
            artifact = load_json(root / "intent.json")
            self.assertEqual(artifact["input_hashes"]["combined_activation_manifest_sha256"], snapshot.combined_activation_manifest_sha256)
            self.assertEqual(artifact["input_provenance_digest"], canonical_hash(artifact["input_hashes"]))
            self.assertEqual(artifact["run_state"], "ORDER_INSTRUCTION_READY")
            self.assertIs(observed.compiler.call_args.kwargs["integrated_snapshot"], observed.snapshots[0])
            self.assertEqual(artifact["input_hashes"]["alert_policy"], file_hash(ALERT_POLICY_PATH))
            self.assertEqual(args, before)
            self.assertFalse(artifact["order_authority"])
            self.assertIsNone(artifact["execution_quantity"])
            self.assertFalse(artifact["automatic_order"])
            self.assertEqual(artifact["submission_status"], "NOT_SUBMITTED")
            self.assertEqual(artifact["broker_submission"], "DISABLED")

    def test_combined_failure_context_missing_and_mismatch_create_no_output(self):
        cases = [(name, None) for name in ("missing", "invalid", "identity_hash", "session_hash")]
        cases += [(None, lambda c: None)]
        for field, value in (("expected_evidence_run_id", "wrong"), ("expected_evidence_sha256", "f" * 64),
                             ("expected_evidence_decision_as_of", "2026-09-02T13:59:00+00:00"),
                             ("expected_completed_us_session", "2026-08-31"), ("calendar_hash", "f" * 64),
                             ("context_generated_at", "2026-09-02T14:01:00+00:00")):
            cases.append((None, lambda c, f=field, v=value: dict(c, **{f: v})))
        for index, (failure, change) in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args, _, _ = _fixture.session_k3_inputs(root)
                observed = self.run_cli(root, args, context_change=change, failure=failure)
                self.assertEqual(observed.exit_code, 2)
                observed.loader.assert_called_once()
                observed.compiler.assert_not_called()
                observed.writer.assert_not_called()
                self.assertFalse((root / "intent.json").exists())

    def test_provenance_mismatch_and_out_of_coverage_fail_closed(self):
        for kind in ("cohort", "hash", "coverage", "provenance_time", "provenance_run", "provenance_version"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                args, _, _ = _fixture.session_k3_inputs(root)
                if kind == "coverage":
                    args["now"] = "2030-09-03T14:00:00+00:00"
                else:
                    key = {"cohort": "activation_cohort_id", "hash": "combined_activation_manifest_sha256",
                           "provenance_time": "snapshot_decision_as_of", "provenance_run": "run_id",
                           "provenance_version": "session_calendar_version"}[kind]
                    value = "2030-09-03T14:00:00+00:00" if kind == "provenance_time" else "f" * 64
                    args["evidence"]["integrated_authority_snapshot_provenance"][key] = value
                observed = self.run_cli(root, args)
                self.assertEqual(observed.exit_code, 2)
                observed.writer.assert_not_called()

    def test_fixed_limit_cli_context_gate_is_separate_from_compiler_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args, _, _ = _fixture.session_k3_inputs(root)
            observed = self.run_cli(root, args, numeric=True, context_change=lambda c: None)
            self.assertEqual(observed.exit_code, 2)
            observed.compiler.assert_not_called()
        case = OrderIntentOnlyTests()
        case.setUp()
        for source, plan in ((source_for_buy(), buy_plan()), (source_for_sell(), sell_plan()),
                             (source_for_sell(), sell_plan(action="EXIT"))):
            expected = case.build(copy.deepcopy(source), copy.deepcopy(plan))
            with patch.object(intent, "_manual_session_window", side_effect=AssertionError("Fixed LIMIT cannot require CORE_OPEN")) as manual:
                actual = case.build(source, plan, current_session_context=None,
                                    current_session_authority_resolver=lambda *a, **k: self.fail("Fixed compiler resolved Session"))
                self.assertEqual(actual, expected)
                manual.assert_not_called()


if __name__ == "__main__":
    unittest.main()
