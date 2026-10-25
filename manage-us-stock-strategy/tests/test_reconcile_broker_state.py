"""I0 broker reconciliation: propose (read-only), user-confirmed apply, and their safety boundaries.

All account data here is synthetic (TEST_ONLY). No network, no Kiwoom runtime, no real state writes.
"""

from __future__ import annotations

import ast
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

import apply_user_confirmed_broker_snapshot as apply_module  # noqa: E402
import kiwoom_account_readonly_bridge as bridge  # noqa: E402
import reconcile_broker_state as cli  # noqa: E402
from apply_user_confirmed_broker_snapshot import (  # noqa: E402
    WRITTEN_STATE_FIELDS, apply_confirmed, ledger_status,
)
from build_broker_reconciliation_proposal import build_proposal  # noqa: E402
from kiwoom_broker_shadow import (  # noqa: E402
    NEVER_TOUCHED_FIELDS, normalize_snapshot, proposal_content_hash, reconciliation_proposal,
    validate_reconciliation_inputs,
)
from kiwoom_runtime_bridge import BLOCKED_TERMS, BridgeError, blocked_api_target  # noqa: E402
from run_kiwoom_broker_shadow import repo_relative  # noqa: E402
from validation_common import canonical_hash, load_json, validate_instance  # noqa: E402

PROPOSAL_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/kiwoom-reconciliation-proposal.schema.json"
SCREENSHOT_FIXTURE = ROOT / "manage-us-stock-strategy/tests/fixtures/v2_5/broker-snapshot-extraction.sample-korean.test-only.json"
SCREENSHOT_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/broker-reconciliation-proposal.schema.json"
ALL_OPERATIONS = ("account_deposit_read", "account_deposit_detail_read", "account_holdings_read",
                  "account_open_items", "account_fills_read", "account_realized_pnl_read")


def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def holding_row(ticker="AAA", quantity="10", cost="100.125", currency="USD", evaluation="1100", pnl="98.75"):
    return {"stex_nm": "TEST", "crnc_code": currency, "stk_cd": ticker, "frgn_stk_nm": "TEST_ONLY", "qty": quantity,
            "poss_qty": quantity, "sell_alowq": quantity, "frgn_stk_book_uv": cost, "now_pric": "110",
            "evlt_amt": evaluation, "pl_amt": pnl, "pl_rt": "0"}


def account_results(retrieved_at, *, holdings=None, deposit=None, statuses=None):
    """Synthetic sanitized bridge output in the exact order the reader returns it."""
    holdings = [holding_row(), holding_row("BBB", "3", "33.333", evaluation="120", pnl="20")] \
        if holdings is None else holdings
    # T1 F1: order-available equals withdrawable (no unsettled sale proceeds); fc_entra is never compared.
    deposit = [{"crnc_code": "USD", "crnc_nm": "TEST", "fc_entra": "1200", "fc_pymn_alowa": "1000.50",
                "fc_ord_alowa": "1000.50"}] if deposit is None else deposit
    statuses = {"account_open_items": "KIWOOM_API_RESPONSE_ERROR", **(statuses or {})}
    data = {"account_deposit_read": deposit, "account_deposit_detail_read": [{"d1_usd_sell_excta": "0"}],
            "account_holdings_read": holdings, "account_open_items": [], "account_fills_read": [],
            "account_realized_pnl_read": []}
    results = []
    for operation in ALL_OPERATIONS:
        status = statuses.get(operation, "PASS")
        if status in {"PASS", "PARTIAL"}:
            results.append({"bridge_status": status, "operation": operation, "data": data[operation],
                            "runtime_commit": "c" * 40, "retrieved_at": retrieved_at,
                            "pagination": {"api_id": bridge.ACCOUNT_APIS[operation][0], "pages": 1,
                                           "exhausted": True, "complete": status == "PASS",
                                           "secret_fields_retained": False},
                            "account_identifier_stored": False, "portfolio_mutation": False,
                            "quantity_authority": "none", "order_authority": False})
        else:
            results.append({"bridge_status": status, "failure_type": "API_RESPONSE_ERROR", "operation": operation,
                            "runtime_commit": None, "retrieved_at": None, "data": [],
                            "account_identifier_stored": False, "portfolio_mutation": False,
                            "quantity_authority": "none", "order_authority": False})
    return results


def base_state():
    return {
        "schema_version": "1.3", "strategy_version": "TEST-ONLY-v4", "state_revision": 7, "state_status": "TEST_ONLY",
        "strategy_mode": "leveraged_holding_risk_and_watchlist", "last_updated_at": "2026-08-12T21:24:00+09:00",
        "last_confirmed_broker_snapshot": {
            "verified": True, "authority_state": "VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT", "scope": "CASH_ONLY",
            "source": "TEST_ONLY", "as_of": "2026-08-14", "holdings_complete": True, "cash_verified": True,
            "cash_verified_scope": "available_cash_only", "account_id_masked": "****0000"},
        "holdings": {"AAA": 8, "BBB": 3}, "average_cost_usd": {"AAA": 100.125, "BBB": 33.333},
        "position_cost_basis_usd": {"AAA": 801.0, "BBB": 100.0}, "aggregate_cost_basis_usd": 901.0,
        "broker_display_snapshot": {"quote_status": "TEST_ONLY", "displayed_prices_usd": {"AAA": 1.0}},
        "brokerage_cash_usd": None, "available_cash_usd": 500.0, "cash_pct_estimate": None, "current_stage": None,
        "confirmed_trades": [{"trade_id": "TEST-1", "quantity": 1}], "unreconciled_holding_changes": [],
        "holding_change_reconciliations": [{"trade_id": "TEST-1", "symbol": "AAA"}], "pending_candidates": [],
        "timing_plan": {"policy_version": "TEST", "positions": {"CCC": {"anchor_shares": 5}}},
        "state_notes": ["TEST_ONLY"], "archived_prior_strategy": {"reason": "TEST_ONLY"},
    }


def passing_check(state, draft):
    return {"check": "TEST_ONLY_CHECK", "session_date": draft["confirmed_snapshot_record"]["as_of"],
            "status": "PASS", "errors": [], "policy_positions_mismatch": False}


def make_proposal(state, *, now=None, results=None, check=passing_check, age_seconds=30, **kwargs):
    now = now or datetime.now(timezone.utc)
    results = account_results(utc(now - timedelta(seconds=age_seconds))) if results is None else results
    snapshot = normalize_snapshot(results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT", generated_at=utc(now),
                                  maximum_age_seconds=900)
    return reconciliation_proposal(snapshot, state, results=results, maximum_age_seconds=900,
                                   post_apply_check=check, **kwargs)


def rehash(proposal):
    proposal["proposal_id"] = proposal_content_hash(proposal)
    proposal["confirm_code"] = proposal["proposal_id"][:8].upper()
    return proposal


class TempStateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.state_path = self.directory / "portfolio_state.json"
        self.audit_path = self.directory / "apply_audit.json"

    def write_state(self, state, newline="\r\n"):
        text = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        self.state_path.write_bytes(text.replace("\n", newline).encode("utf-8"))
        return self.state_path.read_bytes()

    def confirmation(self, proposal, *, code=None, method="COWORK_CHAT_USER_MESSAGE", message=None):
        code = proposal["confirm_code"] if code is None else code
        return {"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
                "confirm_code": code, "confirmation_method": method,
                "user_message": f"확인 {code}" if message is None else message}

    def apply(self, proposal, confirmation=None, **kwargs):
        return apply_confirmed(state_path=self.state_path, proposal=proposal,
                               confirmation=confirmation or self.confirmation(proposal),
                               audit_path=self.audit_path, **kwargs)

    def assert_nothing_written(self, original):
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertFalse((self.directory / "backups").exists())
        self.assertFalse((self.directory / "reconciliation_ledger.jsonl").exists())
        self.assertFalse(self.audit_path.exists())


class AccountReturnCodeTests(unittest.TestCase):
    def test_only_explicit_zero_return_code_passes(self):
        for body, expected in (({"return_code": 0}, True), ({"return_code": "0"}, True), ({}, False),
                               ({"return_code": None}, False), ({"return_code": False}, False),
                               ({"return_code": 20}, False), ({"return_code": "0000"}, False),
                               ({"return_code": 0.0}, False)):
            with self.subTest(body=body):
                self.assertIs(bridge._account_return_code_ok(body), expected)

    def test_missing_return_code_is_an_api_response_error(self):
        session = {"pacer": lambda: None, "maximum_attempts": 1, "retry_backoff_seconds": 0,
                   "immediate_open_failure_types": set(), "retryable_failure_types": set(),
                   "client": SimpleNamespace(fetch_page=lambda **kwargs: SimpleNamespace(
                       body={"result_list": []}, continuation=None))}
        with self.assertRaises(BridgeError) as caught:
            bridge._fetch_account_page(session, "account_holdings_read", {}, cont_yn=None, next_key=None)
        self.assertEqual(caught.exception.status, "KIWOOM_API_RESPONSE_ERROR")

    def test_account_routes_are_read_only(self):
        # T1 F2 adds three read-only account inquiries: ust21100, ust21150, ust21610; cf-b2n adds ust21132 (read-only).
        self.assertEqual({api for api, _ in bridge.ACCOUNT_APIS.values()},
                         {"ust21110", "ust21160", "ust21070", "ust21050", "ust21510", "ust21630",
                          "ust21100", "ust21150", "ust21610", "ust21132"})
        for api_id, path in bridge.ACCOUNT_APIS.values():
            self.assertEqual(path, "/api/us/acnt")
            self.assertFalse(any(term in f"{api_id} {path}".lower() for term in BLOCKED_TERMS))
            self.assertNotIn("ordr", path)
        self.assertTrue(blocked_api_target("usa10075", "/api/us/ordr"))


class InputValidationTests(unittest.TestCase):
    def blocked_codes(self, **kwargs):
        proposal = make_proposal(base_state(), **kwargs)
        self.assertEqual(proposal["status"], "BLOCKED")
        self.assertEqual(proposal["proposed_patch"], {})
        self.assertEqual(validate_instance(proposal, PROPOSAL_SCHEMA), [])
        return proposal["unresolved_fields"]

    def test_each_required_read_must_pass(self):
        now = datetime.now(timezone.utc)
        for operation in ("account_holdings_read", "account_deposit_read", "account_fills_read"):
            for status in ("KIWOOM_API_RESPONSE_ERROR", "PARTIAL", "BRIDGE_TRANSPORT_FAILURE"):
                with self.subTest(operation=operation, status=status):
                    results = account_results(utc(now - timedelta(seconds=10)), statuses={operation: status})
                    self.assertIn(f"REQUIRED_READ_NOT_PASS:{operation}", self.blocked_codes(now=now, results=results))

    def test_missing_required_read_fails(self):
        now = datetime.now(timezone.utc)
        results = [row for row in account_results(utc(now)) if row["operation"] != "account_fills_read"]
        self.assertIn("REQUIRED_READ_MISSING:account_fills_read", self.blocked_codes(now=now, results=results))

    def test_quantity_cost_and_currency_rules(self):
        cases = {
            "HOLDING_QUANTITY_NEGATIVE:AAA": holding_row(quantity="-1"),
            "HOLDING_QUANTITY_FRACTIONAL:AAA": holding_row(quantity="1.5"),
            "HOLDING_QUANTITY_INVALID:AAA": holding_row(quantity=None),
            "AVERAGE_COST_NEGATIVE:AAA": holding_row(cost="-3"),
            "AVERAGE_COST_INVALID:AAA": holding_row(cost=None),
            "HOLDING_CURRENCY_NOT_USD:AAA": holding_row(currency="KRW"),
        }
        now = datetime.now(timezone.utc)
        for code, row in cases.items():
            with self.subTest(code=code):
                results = account_results(utc(now), holdings=[row])
                self.assertIn(code, self.blocked_codes(now=now, results=results))
        for value in ("abc", "nan", "inf"):
            with self.subTest(quantity=value):
                results = account_results(utc(now), holdings=[holding_row(quantity=value)])
                self.assertIn("HOLDING_QUANTITY_INVALID:AAA", self.blocked_codes(now=now, results=results))

    def test_ticker_and_cash_row_rules(self):
        now = datetime.now(timezone.utc)
        cases = {
            "HOLDING_TICKER_DUPLICATE:AAA": {"holdings": [holding_row(), holding_row()]},
            "HOLDING_TICKER_MISSING": {"holdings": [holding_row(ticker="")]},
            "CASH_USD_ROW_MISSING": {"deposit": [{"crnc_code": "KRW", "fc_pymn_alowa": "1", "fc_ord_alowa": "1"}]},
            "CASH_USD_ROW_DUPLICATE": {"deposit": [{"crnc_code": "USD", "fc_pymn_alowa": "1", "fc_ord_alowa": "1"}] * 2},
            "CASH_VALUE_NEGATIVE:fc_pymn_alowa": {"deposit": [{"crnc_code": "USD", "fc_pymn_alowa": "-1",
                                                               "fc_ord_alowa": "1"}]},
            "CASH_VALUE_INVALID:fc_ord_alowa": {"deposit": [{"crnc_code": "USD", "fc_pymn_alowa": "1",
                                                             "fc_ord_alowa": None}]},
        }
        for code, overrides in cases.items():
            with self.subTest(code=code):
                results = account_results(utc(now), **overrides)
                self.assertIn(code, self.blocked_codes(now=now, results=results))

    def test_oldest_required_read_bounds_freshness(self):
        now = datetime.now(timezone.utc)
        results = account_results(utc(now - timedelta(seconds=10)))
        next(row for row in results if row["operation"] == "account_fills_read")["retrieved_at"] = \
            utc(now - timedelta(seconds=901))
        self.assertIn("BROKER_SNAPSHOT_TOO_OLD", self.blocked_codes(now=now, results=results))
        future = account_results(utc(now + timedelta(seconds=120)))
        self.assertIn("REQUIRED_READ_TIMESTAMP_IN_FUTURE:account_holdings_read",
                      self.blocked_codes(now=now, results=future))

    def test_display_only_failures_warn_but_do_not_block(self):
        now = datetime.now(timezone.utc)
        results = account_results(utc(now), statuses={"account_realized_pnl_read": "KIWOOM_API_UNAVAILABLE",
                                                      "account_deposit_detail_read": "KIWOOM_API_UNAVAILABLE"})
        proposal = make_proposal(base_state(), now=now, results=results)
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")
        self.assertIn("OPEN_ORDERS_UNVERIFIED", proposal["warnings"])
        self.assertFalse(proposal["open_orders_verified"])
        self.assertFalse(proposal["confirmed_snapshot_record"]["open_orders_verified"])

    def test_valid_inputs_have_no_errors_and_normalize_contract_is_unchanged(self):
        now = datetime.now(timezone.utc)
        results = account_results(utc(now))
        snapshot = normalize_snapshot(results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT", generated_at=utc(now),
                                      maximum_age_seconds=900)
        self.assertEqual(validate_reconciliation_inputs(results, snapshot, maximum_age_seconds=900), [])
        self.assertEqual(set(snapshot), {
            "schema_version", "snapshot_role", "status", "generated_at", "broker_snapshot_as_of",
            "broker_snapshot_age_seconds", "broker_snapshot_freshness_status", "account_identifier_stored",
            "scope_complete", "operation_statuses", "holdings", "cash", "open_orders", "fills", "realized_pnl",
            "fill_inference_performed", "portfolio_mutation", "quantity_authority", "order_authority",
            "snapshot_hash"})
        self.assertEqual(set(snapshot["holdings"][0]), {"ticker", "security_name", "currency", "settled_quantity",
                                                        "held_quantity", "available_shares", "average_cost"})


class ProposalFormatTests(unittest.TestCase):
    def test_unified_format_and_identity(self):
        state = base_state()
        before = canonical_hash(state)
        proposal = make_proposal(state)
        self.assertEqual(canonical_hash(state), before)
        self.assertEqual(validate_instance(proposal, PROPOSAL_SCHEMA), [])
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")
        self.assertEqual(proposal["change_kind"], "VALUES")
        self.assertEqual(proposal["expected_portfolio_hash_before"], before)
        self.assertEqual(proposal["expected_state_revision"], 7)
        self.assertEqual(proposal["scope"], "HOLDINGS_AND_AVAILABLE_CASH")
        self.assertEqual(proposal["proposal_id"], proposal_content_hash(proposal))
        self.assertEqual(proposal["confirm_code"], proposal["proposal_id"][:8].upper())
        for key in ("current_state_revision", "expected_before_hash", "verified_scope"):
            self.assertNotIn(key, proposal)
        self.assertFalse(proposal["order_authority"])
        self.assertEqual(proposal["quantity_authority"], "none")
        self.assertFalse(proposal["inferred_fills"])
        self.assertFalse(proposal["fill_inference_performed"])
        self.assertEqual(proposal["never_touched"], list(NEVER_TOUCHED_FIELDS))

    def test_patch_values_derivation_and_cash_semantics(self):
        proposal = make_proposal(base_state())
        patch = proposal["proposed_patch"]
        self.assertEqual(patch["holdings"], {"AAA": 10, "BBB": 3})
        self.assertTrue(all(type(value) is int for value in patch["holdings"].values()))
        self.assertEqual(patch["average_cost_usd"], {"AAA": 100.125, "BBB": 33.333})
        self.assertEqual(patch["position_cost_basis_usd"], {"AAA": 1001.25, "BBB": 100.0})
        self.assertEqual(patch["aggregate_cost_basis_usd"], 1101.25)
        self.assertEqual(patch["available_cash_usd"], 1000.5)
        self.assertEqual(proposal["cash_semantics"]["cash_verified_scope"], "available_cash_only")
        self.assertFalse(proposal["cash_semantics"]["settled_cash"])
        self.assertEqual(proposal["confirmed_snapshot_record"]["cash_verified_scope"], "available_cash_only")
        crosscheck = {item["ticker"]: item["status"] for item in proposal["cost_basis_crosscheck"]}
        self.assertEqual(crosscheck, {"AAA": "WITHIN_ONE_DOLLAR", "BBB": "WITHIN_ONE_DOLLAR"})

    def test_expiry_is_oldest_required_read_plus_policy_age(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        results = account_results(utc(now - timedelta(seconds=30)))
        next(row for row in results if row["operation"] == "account_deposit_read")["retrieved_at"] = \
            utc(now - timedelta(seconds=100))
        proposal = make_proposal(base_state(), now=now, results=results)
        self.assertEqual(proposal["expires_at"], utc(now - timedelta(seconds=100) + timedelta(seconds=900)))

    def test_paths_are_repository_relative(self):
        proposal = make_proposal(base_state(), snapshot_path=repo_relative(
            ROOT / "workspace/outputs/reconciliation/20260101T000000Z/kiwoom_broker_snapshot.shadow.json"))
        self.assertEqual(proposal["portfolio_state_path"], "stock-strategy-system/portfolio_state.json")
        self.assertEqual(proposal["source"]["snapshot_path"],
                         "workspace/outputs/reconciliation/20260101T000000Z/kiwoom_broker_snapshot.shadow.json")
        for value in (proposal["portfolio_state_path"], proposal["source"]["snapshot_path"]):
            self.assertNotIn("\\", value)
            self.assertFalse(Path(value).is_absolute())
            self.assertNotRegex(value, r"^[A-Za-z]:")

    def test_metadata_only_and_no_change(self):
        state = base_state()
        applied_values = make_proposal(state)["proposed_patch"]
        state.update(copy.deepcopy(applied_values))
        metadata = make_proposal(state)
        self.assertEqual(metadata["status"], "USER_CONFIRMATION_REQUIRED")
        self.assertEqual(metadata["change_kind"], "METADATA_ONLY")
        self.assertTrue(all(item["field"] == "last_confirmed_broker_snapshot" for item in metadata["changes"]))
        state["last_confirmed_broker_snapshot"].update(
            {key: metadata["confirmed_snapshot_record"][key] for key in
             ("source", "scope", "as_of", "holdings_complete", "cash_verified", "cash_verified_scope",
              "open_orders_verified")})
        unchanged = make_proposal(state)
        self.assertEqual(unchanged["status"], "NO_CHANGE_REQUIRED")
        self.assertEqual(unchanged["changes"], [])
        self.assertEqual(unchanged["proposed_patch"], {})

    def test_warnings_and_post_apply_check_are_recorded(self):
        state = base_state()
        state["timing_plan"]["positions"]["AAA"] = {"anchor_shares": 8}
        failing = lambda portfolio, draft: {"check": "TEST_ONLY_CHECK", "session_date": "2026-01-01",
                                            "status": "FAIL", "errors": ["TEST_ONLY reason"],
                                            "policy_positions_mismatch": True}
        proposal = make_proposal(state, check=failing)
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")
        for warning in ("OPEN_ORDERS_UNVERIFIED", "TIMING_PLAN_TICKER_CHANGED", "POLICY_POSITIONS_MISMATCH",
                        "POST_APPLY_ALERT_ENGINE_CHECK_FAILED"):
            self.assertIn(warning, proposal["warnings"])
        self.assertEqual(proposal["post_apply_checks"]["status"], "FAIL")
        self.assertEqual(proposal["post_apply_checks"]["errors"], ["TEST_ONLY reason"])
        table = "\n".join(cli.render_proposal(proposal))
        self.assertIn("TEST_ONLY reason", table)
        self.assertIn(proposal["confirm_code"], table)

    def test_missing_post_apply_check_blocks(self):
        proposal = make_proposal(base_state(), check=None)
        self.assertEqual(proposal["status"], "BLOCKED")
        self.assertIn("POST_APPLY_CHECK_NOT_RUN", proposal["unresolved_fields"])
        self.assertEqual(proposal["proposed_patch"], {})

    def test_state_changed_outside_ledger_blocks(self):
        """Only a state equal to the last entry's before-hash (state write failed) blocks; others warn."""
        state = base_state()
        messages = cli._messages()
        failed_write = make_proposal(state, ledger_last_hash_after="f" * 64,
                                     ledger_last_hash_before=canonical_hash(state))
        self.assertEqual(failed_write["status"], "BLOCKED")
        self.assertIn("STATE_CHANGED_OUTSIDE_LEDGER", failed_write["warnings"])
        self.assertIn("STATE_CHANGED_OUTSIDE_LEDGER", failed_write["unresolved_fields"])
        self.assertEqual(failed_write["proposed_patch"], {})
        table = "\n".join(cli.render_proposal(failed_write))
        self.assertIn(messages["blocked_STATE_CHANGED_OUTSIDE_LEDGER"], table)
        self.assertNotIn(messages["show_confirm"].split("{code}")[0], table)
        changed = make_proposal(state, ledger_last_hash_after="f" * 64, ledger_last_hash_before="e" * 64)
        self.assertEqual(validate_instance(changed, PROPOSAL_SCHEMA), [])
        self.assertEqual(changed["status"], "USER_CONFIRMATION_REQUIRED")
        self.assertIn("STATE_CHANGED_OUTSIDE_LEDGER", changed["warnings"])
        self.assertNotIn("STATE_CHANGED_OUTSIDE_LEDGER", changed["unresolved_fields"])
        table = "\n".join(cli.render_proposal(changed))
        self.assertIn(messages["warning_STATE_CHANGED_OUTSIDE_LEDGER"], table)
        self.assertIn(changed["confirm_code"], table)
        in_step = make_proposal(state, ledger_last_hash_after=canonical_hash(state), ledger_last_hash_before="e" * 64)
        self.assertNotIn("STATE_CHANGED_OUTSIDE_LEDGER", in_step["warnings"])
        broken = make_proposal(base_state(), ledger_integrity_ok=False)
        self.assertIn("LEDGER_INTEGRITY_FAILED", broken["unresolved_fields"])

    def test_real_alert_engine_check_runs_on_a_patched_copy(self):
        policy = load_json(ROOT / "stock-strategy-system/alert_policy.json")
        state = base_state()
        before = canonical_hash(state)
        proposal = make_proposal(state, check=cli.alert_engine_check(policy))
        self.assertEqual(canonical_hash(state), before)
        checks = proposal["post_apply_checks"]
        self.assertIn(checks["status"], {"PASS", "FAIL", "NOT_APPLICABLE"})
        if policy.get("daily_engine_scope") == "leveraged_holding_risk_and_watchlist":
            self.assertEqual(checks["check"], "evaluate_alerts.leveraged_state_integrity_errors")
            self.assertEqual(checks["status"], "FAIL")  # synthetic tickers are not policy positions
            self.assertTrue(checks["policy_positions_mismatch"])
            self.assertIn("POLICY_POSITIONS_MISMATCH", proposal["warnings"])


class LibraryRejectionTests(TempStateCase):
    """P3 4-6 item 1: direct library calls cannot apply unsafe proposals, and nothing is written."""

    def setUp(self):
        super().setUp()
        self.state = base_state()
        self.original = self.write_state(self.state)
        self.proposal = make_proposal(self.state)

    def assert_rejected(self, pattern, proposal=None, confirmation=None, **kwargs):
        with self.assertRaisesRegex(ValueError, pattern):
            self.apply(proposal or self.proposal, confirmation, **kwargs)
        self.assert_nothing_written(self.original)

    def test_unresolved_fields_rejected_even_with_valid_identity(self):
        forged = rehash(dict(copy.deepcopy(self.proposal), unresolved_fields=["TEST_ONLY_UNRESOLVED"]))
        self.assert_rejected("BROKER_PROPOSAL_UNRESOLVED_FIELDS", forged, self.confirmation(forged))

    def test_screenshot_proposal_with_unresolved_fields_rejected(self):
        state = {"schema_version": "1.3", "strategy_version": "2026-08-05-v4", "state_revision": 1,
                 "holdings": {"OLD": 1}, "average_cost_usd": {"OLD": 10.0}, "position_cost_basis_usd": {"OLD": 10.0},
                 "available_cash_usd": 0.0, "last_confirmed_broker_snapshot": {"verified": True}}
        self.original = self.write_state(state)
        proposal = build_proposal(load_json(SCREENSHOT_FIXTURE), state)
        self.assertTrue(proposal["unresolved_fields"])
        confirmation = {"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
                        "source": "TEST_ONLY_VERIFIED_BROKER_SNAPSHOT", "as_of": "2026-08-13",
                        "holdings_complete": True, "cash_verified": False}
        self.assert_rejected("BROKER_PROPOSAL_UNRESOLVED_FIELDS", proposal, confirmation,
                             proposal_schema=SCREENSHOT_SCHEMA)

    def test_expired_proposal_rejected(self):
        expires = datetime.fromisoformat(self.proposal["expires_at"].replace("Z", "+00:00"))
        self.assert_rejected("BROKER_PROPOSAL_EXPIRED", now=expires + timedelta(seconds=1))

    def test_caller_clock_cannot_turn_back_expiry(self):
        past = datetime.now(timezone.utc) - timedelta(seconds=2000)
        stale = make_proposal(self.state, now=past)  # expired about 1,130 seconds ago on the real clock
        self.assertEqual(stale["status"], "USER_CONFIRMATION_REQUIRED")
        self.assert_rejected("BROKER_PROPOSAL_EXPIRED", stale, self.confirmation(stale),
                             now=past + timedelta(seconds=60))

    def test_state_hash_and_revision_mismatch_rejected(self):
        changed = dict(self.state, state_notes=["TEST_ONLY changed after propose"])
        self.original = self.write_state(changed)
        self.assert_rejected("CONCURRENT_STATE_HASH_MISMATCH")
        self.original = self.write_state(dict(self.state, state_revision=8))
        self.assert_rejected("CONCURRENT_STATE_REVISION_MISMATCH")

    def test_confirm_code_missing_wrong_or_from_another_proposal_rejected(self):
        self.assert_rejected("CONFIRM_CODE_REQUIRED", confirmation=self.confirmation(self.proposal, code=""))
        self.assert_rejected("CONFIRM_CODE_MISMATCH", confirmation=self.confirmation(self.proposal, code="00000000"))
        other = make_proposal(self.state, age_seconds=45)
        self.assertNotEqual(other["confirm_code"], self.proposal["confirm_code"])
        self.assert_rejected("CONFIRM_CODE_MISMATCH",
                             confirmation=self.confirmation(self.proposal, code=other["confirm_code"]))

    def test_confirmation_method_and_user_message_required(self):
        self.assert_rejected("CONFIRMATION_METHOD_INVALID",
                             confirmation=self.confirmation(self.proposal, method="SCHEDULED_TASK"))
        self.assert_rejected("USER_CONFIRMATION_MESSAGE_REQUIRED",
                             confirmation=self.confirmation(self.proposal, message="yes please"))
        self.assert_rejected("EXPLICIT_USER_CONFIRMATION_REQUIRED",
                             confirmation=dict(self.confirmation(self.proposal), confirmed=False))

    def test_tampered_proposal_rejected(self):
        tampered = copy.deepcopy(self.proposal)
        tampered["proposed_patch"]["holdings"]["AAA"] = 999
        self.assert_rejected("BROKER_PROPOSAL_INTEGRITY_MISMATCH", tampered, self.confirmation(self.proposal))
        # Re-hashing a tampered proposal changes its code, so the code the user saw no longer matches.
        rehashed = rehash(copy.deepcopy(tampered))
        self.assert_rejected("CONFIRM_CODE_MISMATCH", rehashed,
                             dict(self.confirmation(rehashed), confirm_code=self.proposal["confirm_code"],
                                  user_message=f"확인 {self.proposal['confirm_code']}"))

    def test_not_applicable_statuses_and_unknown_types_rejected(self):
        blocked = make_proposal(self.state, check=None)
        self.assert_rejected("PROPOSAL_NOT_APPLYABLE", blocked, self.confirmation(blocked))
        unknown = dict(copy.deepcopy(self.proposal), schema_version="9.9")
        self.assert_rejected("BROKER_PROPOSAL_TYPE_UNSUPPORTED", unknown, self.confirmation(unknown))

    def test_caller_schema_cannot_relax_the_pinned_schema(self):
        lenient = self.directory / "lenient.schema.json"
        lenient.write_text('{"type": "object"}', encoding="utf-8")
        stripped = copy.deepcopy(self.proposal)
        del stripped["expires_at"]
        rehash(stripped)
        self.assert_rejected("BROKER_PROPOSAL_SCHEMA_INVALID", stripped, self.confirmation(stripped),
                             proposal_schema=lenient)

    def test_ledger_mismatch_or_broken_chain_rejected(self):
        ledger = self.directory / "reconciliation_ledger.jsonl"
        # The last entry was written but the state is still its before-state: the state write failed.
        entry = {"previous_entry_sha256": "0" * 64, "portfolio_hash_before": canonical_hash(self.state),
                 "portfolio_hash_after": "f" * 64}
        ledger.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        ledger_bytes = ledger.read_bytes()
        failed_write = make_proposal(self.state, ledger_last_hash_after="f" * 64,
                                     ledger_last_hash_before=canonical_hash(self.state))
        # A direct caller that drops the blocking code still cannot apply over a failed state write.
        forced = rehash(dict(copy.deepcopy(failed_write), status="USER_CONFIRMATION_REQUIRED", change_kind="VALUES",
                             unresolved_fields=[], proposed_patch=copy.deepcopy(self.proposal["proposed_patch"])))
        for proposal in (self.proposal, forced):
            with self.subTest(warnings=proposal["warnings"]), \
                    self.assertRaisesRegex(ValueError, "STATE_CHANGED_OUTSIDE_LEDGER: STATE_EQUALS_LAST_LEDGER_BEFORE"):
                self.apply(proposal, self.confirmation(proposal))
        # Any other outside change: the proposal the user confirmed must have shown the warning.
        ledger.write_text(json.dumps(dict(entry, portfolio_hash_before="e" * 64)) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "OUTSIDE_LEDGER_WARNING_NOT_IN_PROPOSAL"):
            self.apply(self.proposal)
        ledger.write_text(json.dumps(dict(entry, previous_entry_sha256="1" * 64)) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "LEDGER_INTEGRITY_FAILED"):
            self.apply(self.proposal)
        self.assertEqual(self.state_path.read_bytes(), self.original)
        self.assertFalse((self.directory / "backups").exists())
        self.assertFalse(self.audit_path.exists())
        ledger.write_bytes(ledger_bytes)
        self.assertEqual(ledger_status(ledger)["entries"], 1)

    def test_unparsable_state_rejected_as_changed_outside_ledger(self):
        for content in (b"{not json", b"\xff\xfe", b"[]"):
            with self.subTest(content=content):
                self.state_path.write_bytes(content)
                with self.assertRaisesRegex(ValueError, "STATE_CHANGED_OUTSIDE_LEDGER: STATE_FILE_NOT_JSON"):
                    self.apply(self.proposal)
                self.assertEqual(self.state_path.read_bytes(), content)
                self.assertFalse((self.directory / "backups").exists())
                self.assertFalse((self.directory / "reconciliation_ledger.jsonl").exists())
                self.assertFalse(self.audit_path.exists())

    def test_ledger_and_backup_locations_are_not_arguments(self):
        for keyword in ("ledger_path", "backup_directory"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                self.apply(self.proposal, **{keyword: self.directory / "elsewhere"})
        self.assert_nothing_written(self.original)
        self.assertFalse((self.directory / "elsewhere").exists())

    def test_path_aliases_and_protected_names_rejected(self):
        with self.assertRaisesRegex(ValueError, "BROKER_APPLY_PATH_ALIAS_REJECTED"):
            apply_confirmed(state_path=self.state_path, proposal=self.proposal,
                            confirmation=self.confirmation(self.proposal), audit_path=self.state_path)
        # The ledger path comes from the state path, so a state file named like the ledger aliases it.
        with self.assertRaisesRegex(ValueError, "BROKER_APPLY_PATH_ALIAS_REJECTED"):
            apply_confirmed(state_path=self.directory / "reconciliation_ledger.jsonl", proposal=self.proposal,
                            confirmation=self.confirmation(self.proposal), audit_path=self.audit_path)
        protected = self.directory / "alert_runtime_state.json"
        with self.assertRaisesRegex(ValueError, "PORTFOLIO_STATE_PATH_REQUIRED"):
            apply_confirmed(state_path=protected, proposal=self.proposal,
                            confirmation=self.confirmation(self.proposal), audit_path=self.audit_path)
        self.assert_nothing_written(self.original)


class LibraryApplyTests(TempStateCase):
    def test_apply_writes_only_reconciled_fields_with_backup_and_ledger(self):
        state = base_state()
        original = self.write_state(state, newline="\r\n")
        proposal = make_proposal(state)
        audit = self.apply(proposal)
        updated_bytes = self.state_path.read_bytes()
        updated = json.loads(updated_bytes.decode("utf-8"))
        self.assertEqual(updated_bytes.count(b"\r\n"), updated_bytes.count(b"\n"))  # CRLF preserved
        self.assertEqual(updated["state_revision"], 8)
        self.assertEqual(updated["holdings"], {"AAA": 10, "BBB": 3})
        self.assertEqual(updated["available_cash_usd"], 1000.5)
        self.assertEqual(updated["aggregate_cost_basis_usd"], 1101.25)
        self.assertNotEqual(updated["last_updated_at"], state["last_updated_at"])
        record = updated["last_confirmed_broker_snapshot"]
        self.assertEqual(record["scope"], "HOLDINGS_AND_AVAILABLE_CASH")
        self.assertEqual(record["source"], "KIWOOM_READONLY_API")
        self.assertEqual(record["as_of"], proposal["confirmed_snapshot_record"]["as_of"])
        self.assertTrue(record["holdings_complete"])
        self.assertEqual(record["cash_verified_scope"], "available_cash_only")
        self.assertFalse(record["open_orders_verified"])
        self.assertEqual(record["confirmation_method"], "COWORK_CHAT_USER_MESSAGE")
        self.assertIsNone(record["account_id_masked"])
        # P3 4-6 item 3: never_touched fields stay identical (canonical JSON), and so does every other field.
        for key in NEVER_TOUCHED_FIELDS:
            self.assertEqual(canonical_hash(updated[key]), canonical_hash(state[key]), key)
        for key in set(state) - WRITTEN_STATE_FIELDS:
            self.assertEqual(canonical_hash(updated[key]), canonical_hash(state[key]), key)
        reconciliation = updated["holding_change_reconciliations"][-1]
        self.assertEqual(updated["holding_change_reconciliations"][:-1], state["holding_change_reconciliations"])
        self.assertIsNone(reconciliation["trade_id"])
        self.assertFalse(reconciliation["fill_recorded"])
        self.assertEqual(reconciliation["share_changes"], [{"symbol": "AAA", "prior_verified_shares": 8,
                                                            "current_verified_shares": 10, "share_change": 2}])
        backups = list((self.directory / "backups").glob("portfolio_state.r7.*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        status = ledger_status(self.directory / "reconciliation_ledger.jsonl")
        self.assertTrue(status["chain_ok"])
        self.assertEqual(status["entries"], 1)
        self.assertEqual(status["last_portfolio_hash_after"], canonical_hash(updated))
        self.assertEqual(audit["portfolio_hash_after"], canonical_hash(updated))
        entry = json.loads((self.directory / "reconciliation_ledger.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(entry["previous_entry_sha256"], "0" * 64)
        self.assertEqual(entry["portfolio_hash_before"], canonical_hash(state))
        self.assertEqual(entry["confirm_code"], proposal["confirm_code"])
        self.assertIn(proposal["confirm_code"], entry["user_message"])
        self.assertFalse(entry["inferred_fills"])
        # Replaying the same confirmation cannot apply twice.
        with self.assertRaisesRegex(ValueError, "CONCURRENT_STATE_REVISION_MISMATCH"):
            self.apply(proposal)
        self.assertEqual(ledger_status(self.directory / "reconciliation_ledger.jsonl")["entries"], 1)

    def test_lf_state_stays_lf_and_ledger_chains_across_applies(self):
        state = base_state()
        self.write_state(state, newline="\n")
        self.apply(make_proposal(state))
        first = load_json(self.state_path)
        self.assertNotIn(b"\r\n", self.state_path.read_bytes())
        ledger = self.directory / "reconciliation_ledger.jsonl"
        second_proposal = make_proposal(first, ledger_last_hash_after=ledger_status(ledger)["last_portfolio_hash_after"],
                                        results=account_results(utc(datetime.now(timezone.utc)), deposit=[{
                                            "crnc_code": "USD", "fc_pymn_alowa": "10", "fc_ord_alowa": "10"}]))
        self.assertEqual(second_proposal["status"], "USER_CONFIRMATION_REQUIRED")
        self.apply(second_proposal)
        status = ledger_status(ledger)
        self.assertEqual((status["entries"], status["chain_ok"]), (2, True))
        self.assertEqual(status["last_portfolio_hash_after"], canonical_hash(load_json(self.state_path)))
        self.assertEqual(load_json(self.state_path)["available_cash_usd"], 10.0)

    def test_screenshot_path_with_resolved_fields_is_rejected_in_v1(self):
        # v1 applies Kiwoom proposals only; atomic apply is covered by the Kiwoom tests above and CliTests.
        state = {"schema_version": "1.3", "strategy_version": "2026-08-05-v4", "state_revision": 1,
                 "holdings": {"OLD": 1}, "average_cost_usd": {"OLD": 10.0}, "position_cost_basis_usd": {"OLD": 10.0},
                 "available_cash_usd": 0.0, "last_confirmed_broker_snapshot": {"verified": True}}
        original = self.write_state(state, newline="\n")
        sample = load_json(SCREENSHOT_FIXTURE)
        sample.update(capture_date_status="VERIFIED", holdings_complete_status="VERIFIED",
                      position_currency_status="VERIFIED")
        proposal = build_proposal(sample, state)
        self.assertEqual(proposal["unresolved_fields"], [])
        with self.assertRaisesRegex(ValueError, "SCREENSHOT_PROPOSAL_APPLY_NOT_SUPPORTED"):
            apply_confirmed(state_path=self.state_path, proposal=proposal, audit_path=self.audit_path,
                            proposal_schema=SCREENSHOT_SCHEMA,
                            confirmation={"confirmed": True, "proposal_id": proposal["proposal_id"],
                                          "bundle_id": proposal["bundle_id"], "as_of": "2026-08-13",
                                          "source": "TEST_ONLY_VERIFIED_BROKER_SNAPSHOT",
                                          "holdings_complete": True, "cash_verified": False,
                                          "confirmed_at": "2026-08-13T01:00:00+00:00"})
        self.assert_nothing_written(original)

    def test_caller_clock_cannot_backdate_confirmed_at(self):
        state = base_state()
        self.write_state(state)
        proposal = make_proposal(state)
        started = datetime.now(timezone.utc)
        audit = self.apply(proposal, now=started - timedelta(days=30))
        entry = json.loads((self.directory / "reconciliation_ledger.jsonl").read_text(encoding="utf-8"))
        confirmed = datetime.fromisoformat(entry["confirmed_at"])
        self.assertGreaterEqual(confirmed, started)
        updated = load_json(self.state_path)
        self.assertEqual(updated["last_updated_at"], entry["confirmed_at"])
        self.assertEqual(updated["last_confirmed_broker_snapshot"]["confirmed_at"], entry["confirmed_at"])
        self.assertEqual(audit["confirmed_at"], entry["confirmed_at"])

    def test_first_apply_with_a_missing_or_empty_ledger(self):
        ledger = self.directory / "reconciliation_ledger.jsonl"
        for existing in (None, b""):
            with self.subTest(ledger="missing" if existing is None else "empty file"):
                ledger.unlink(missing_ok=True)
                shutil.rmtree(self.directory / "backups", ignore_errors=True)
                if existing is not None:
                    ledger.write_bytes(existing)
                state = base_state()
                self.write_state(state)
                status = ledger_status(ledger)
                self.assertEqual((status["entries"], status["chain_ok"], status["last_portfolio_hash_after"],
                                  status["last_portfolio_hash_before"]), (0, True, None, None))
                proposal = make_proposal(state, ledger_last_hash_after=status["last_portfolio_hash_after"],
                                         ledger_last_hash_before=status["last_portfolio_hash_before"],
                                         ledger_integrity_ok=status["chain_ok"])
                self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")
                self.assertNotIn("STATE_CHANGED_OUTSIDE_LEDGER", proposal["warnings"])
                self.apply(proposal)
                lines = [line for line in ledger.read_bytes().splitlines() if line.strip()]
                self.assertEqual(len(lines), 1)
                entry = json.loads(lines[0])
                self.assertEqual(entry["previous_entry_sha256"], "0" * 64)
                self.assertEqual(entry["portfolio_hash_before"], canonical_hash(state))
                self.assertFalse(entry["state_changed_outside_ledger"])
                self.assertIsNone(entry["ledger_expected_portfolio_hash"])
                self.assertEqual(load_json(self.state_path)["state_revision"], 8)
                self.assertTrue(ledger_status(ledger)["chain_ok"])

    def test_outside_ledger_change_applies_after_confirmation_and_is_recorded(self):
        state = base_state()
        self.write_state(state)
        ledger = self.directory / "reconciliation_ledger.jsonl"
        first = {"previous_entry_sha256": "0" * 64, "portfolio_hash_before": "e" * 64, "portfolio_hash_after": "f" * 64}
        ledger.write_text(json.dumps(first) + "\n", encoding="utf-8")
        status = ledger_status(ledger)
        proposal = make_proposal(state, ledger_last_hash_after=status["last_portfolio_hash_after"],
                                 ledger_last_hash_before=status["last_portfolio_hash_before"])
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")
        self.assertIn("STATE_CHANGED_OUTSIDE_LEDGER", proposal["warnings"])
        self.apply(proposal)
        after = ledger_status(ledger)
        self.assertEqual((after["entries"], after["chain_ok"]), (2, True))
        self.assertEqual(after["last_portfolio_hash_after"], canonical_hash(load_json(self.state_path)))
        entry = json.loads(ledger.read_bytes().splitlines()[-1])
        self.assertTrue(entry["state_changed_outside_ledger"])
        self.assertEqual(entry["ledger_expected_portfolio_hash"], "f" * 64)
        self.assertEqual(entry["portfolio_hash_before"], canonical_hash(state))
        self.assertEqual(entry["previous_entry_sha256"], status["last_entry_sha256"])
        # The next apply follows the ledger again, so no outside change is recorded.
        updated = load_json(self.state_path)
        after_status = ledger_status(ledger)
        second = make_proposal(updated, ledger_last_hash_after=after_status["last_portfolio_hash_after"],
                               ledger_last_hash_before=after_status["last_portfolio_hash_before"],
                               results=account_results(utc(datetime.now(timezone.utc)), deposit=[{
                                   "crnc_code": "USD", "fc_pymn_alowa": "10", "fc_ord_alowa": "10"}]))
        self.assertNotIn("STATE_CHANGED_OUTSIDE_LEDGER", second["warnings"])
        self.apply(second)
        self.assertFalse(json.loads(ledger.read_bytes().splitlines()[-1])["state_changed_outside_ledger"])

    def test_untouched_guard_detects_other_field_changes(self):
        state = base_state()
        with self.assertRaisesRegex(ValueError, "NEVER_TOUCHED_FIELD_CHANGED: timing_plan"):
            apply_module._assert_untouched(state, dict(state, timing_plan={}))


class CliTests(TempStateCase):
    def setUp(self):
        super().setUp()
        self.runtime = self.directory / "runtime"
        self.runtime.mkdir()
        self.output_root = self.directory / "outputs"
        self.policies = {}
        for name, value in (("readonly", {"official_runtime_path": str(self.runtime)}), ("rate", {}),
                            ("broker", {"maximum_age_seconds": 900}),
                            ("alert", {"daily_engine_scope": "TEST_ONLY_NOT_LEVERAGED"})):
            path = self.directory / f"{name}.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            self.policies[name] = path
        self.state = base_state()
        self.original = self.write_state(self.state)
        # hnd-check: these runs have no console. The interactive-terminal check is tested in
        # test_approval_human_check.py; here it passes so the code checks keep their meaning.
        terminal = mock.patch("portfolio_review_journal.user_terminal_rejection", return_value=None)
        terminal.start()
        self.addCleanup(terminal.stop)

    def run_cli(self, argv, reader=None):
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(argv, reader=reader)
        return code, output.getvalue()

    def propose(self, results=None):
        calls = []

        def reader(requests, *, runtime, policy):
            calls.append((requests, runtime))
            return results if results is not None else account_results(utc(datetime.now(timezone.utc)))
        code, output = self.run_cli([
            "propose", "--readonly-policy", str(self.policies["readonly"]), "--rate-policy", str(self.policies["rate"]),
            "--broker-policy", str(self.policies["broker"]), "--alert-policy", str(self.policies["alert"]),
            "--portfolio-state", str(self.state_path), "--output-root", str(self.output_root)], reader=reader)
        self.assertEqual(len(calls), 1)
        self.assertEqual([item["operation"] for item in calls[0][0]], list(ALL_OPERATIONS))
        return code, output

    def latest(self):
        return load_json(cli.resolve_proposal_path("latest", self.output_root))

    def apply_cli(self, *extra):
        return self.run_cli(["apply", "--output-root", str(self.output_root), "--portfolio-state", str(self.state_path),
                             *extra])

    def test_propose_is_read_only_and_writes_outputs(self):
        code, output = self.propose()
        self.assertEqual(code, 0)
        self.assertEqual(self.state_path.read_bytes(), self.original)
        proposal = self.latest()
        self.assertEqual(validate_instance(proposal, PROPOSAL_SCHEMA), [])
        self.assertEqual(proposal["post_apply_checks"]["status"], "NOT_APPLICABLE")
        self.assertIn("reconciliation_proposal.json", output)
        self.assertTrue(list(self.output_root.glob("*/kiwoom_broker_snapshot.shadow.json")))
        self.assertFalse((self.directory / "reconciliation_ledger.jsonl").exists())
        code, output = self.run_cli(["show", "--output-root", str(self.output_root)])
        self.assertEqual(code, 0)
        self.assertIn(proposal["confirm_code"], output)

    def test_propose_blocked_when_a_required_read_fails(self):
        results = account_results(utc(datetime.now(timezone.utc)),
                                  statuses={"account_holdings_read": "KIWOOM_API_RESPONSE_ERROR"})
        code, _ = self.propose(results)
        self.assertEqual(code, 2)
        self.assertEqual(self.latest()["status"], "BLOCKED")
        self.assertEqual(self.state_path.read_bytes(), self.original)

    def test_propose_rejects_a_non_official_runtime(self):
        with self.assertRaises(SystemExit):
            self.run_cli(["propose", "--runtime", str(self.directory), "--readonly-policy",
                          str(self.policies["readonly"]), "--portfolio-state", str(self.state_path),
                          "--output-root", str(self.output_root)], reader=lambda *a, **k: [])

    def test_apply_requires_the_code(self):
        self.propose()
        with self.assertRaises(SystemExit) as caught, redirect_stdout(io.StringIO()), \
                mock.patch("sys.stderr", io.StringIO()):
            cli.main(["apply", "--confirmed-via", "USER_TERMINAL", "--output-root", str(self.output_root),
                      "--portfolio-state", str(self.state_path)])
        self.assertEqual(caught.exception.code, 2)
        self.assert_nothing_written(self.original)

    def test_apply_rejects_wrong_or_foreign_codes_and_missing_messages(self):
        self.propose()
        first = cli.resolve_proposal_path("latest", self.output_root)
        foreign_state = copy.deepcopy(self.state)
        foreign_state["state_notes"] = ["TEST_ONLY other state"]
        foreign = make_proposal(foreign_state)
        for argv in (["--confirm", "00000000", "--confirmed-via", "USER_TERMINAL"],
                     ["--confirm", foreign["confirm_code"], "--confirmed-via", "USER_TERMINAL"],
                     ["--confirm", self.latest()["confirm_code"], "--confirmed-via", "COWORK_CHAT_USER_MESSAGE"],
                     ["--confirm", self.latest()["confirm_code"], "--confirmed-via", "COWORK_CHAT_USER_MESSAGE",
                      "--user-message", "확인"]):
            with self.subTest(argv=argv):
                code, output = self.apply_cli("--proposal", str(first), *argv)
                self.assertEqual(code, 2)
                self.assert_nothing_written(self.original)

    def test_apply_with_the_users_code(self):
        self.propose()
        proposal = self.latest()
        message = f"확인 {proposal['confirm_code'].lower()}"
        code, output = self.apply_cli("--confirm", proposal["confirm_code"].lower(),
                                      "--confirmed-via", "COWORK_CHAT_USER_MESSAGE", "--user-message", message)
        self.assertEqual(code, 0, output)
        updated = load_json(self.state_path)
        self.assertEqual(updated["state_revision"], 8)
        self.assertEqual(updated["holdings"], {"AAA": 10, "BBB": 3})
        entry = json.loads((self.directory / "reconciliation_ledger.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(entry["confirmation_method"], "COWORK_CHAT_USER_MESSAGE")
        self.assertEqual(entry["user_message"], message)
        self.assertTrue(list((self.directory / "backups").glob("portfolio_state.r7.*.json")))
        self.assertTrue(list(self.output_root.glob("*/apply_audit.*.json")))
        # A second propose sees the ledger and state in agreement.
        self.propose()
        self.assertNotIn("STATE_CHANGED_OUTSIDE_LEDGER", self.latest()["warnings"])

    def test_apply_requires_explicit_state_path_for_non_default_proposals(self):
        self.propose()
        proposal = self.latest()
        code, output = self.run_cli(["apply", "--output-root", str(self.output_root), "--confirm",
                                     proposal["confirm_code"], "--confirmed-via", "USER_TERMINAL"])
        self.assertEqual(code, 2)
        self.assertIn("PROPOSAL_STATE_PATH_NOT_DEFAULT", output)
        self.assert_nothing_written(self.original)

    def test_terminal_fallback_applies_with_only_the_code(self):
        self.propose()
        code, output = self.apply_cli("--confirm", self.latest()["confirm_code"], "--confirmed-via", "USER_TERMINAL")
        self.assertEqual(code, 0, output)
        entry = json.loads((self.directory / "reconciliation_ledger.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(entry["confirmation_method"], "USER_TERMINAL")

    def test_ledger_and_backup_options_are_removed(self):
        elsewhere = str(self.directory / "elsewhere")
        for argv in (["propose", "--ledger", elsewhere],
                     ["apply", "--confirm", "00000000", "--confirmed-via", "USER_TERMINAL", "--ledger", elsewhere],
                     ["apply", "--confirm", "00000000", "--confirmed-via", "USER_TERMINAL",
                      "--backup-directory", elsewhere]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as caught, \
                    redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                cli.main(argv, reader=lambda *args, **kwargs: self.fail("no read expected"))
            self.assertEqual(caught.exception.code, 2)
        self.assert_nothing_written(self.original)
        self.assertFalse((self.directory / "elsewhere").exists())

    def test_propose_and_apply_use_the_ledger_next_to_the_state(self):
        ledger = self.directory / "reconciliation_ledger.jsonl"
        entry = {"previous_entry_sha256": "0" * 64, "portfolio_hash_before": canonical_hash(self.state),
                 "portfolio_hash_after": "f" * 64}
        ledger.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        code, output = self.propose()
        self.assertEqual(code, 2)
        self.assertIn("STATE_CHANGED_OUTSIDE_LEDGER", self.latest()["unresolved_fields"])
        code, output = self.run_cli(["show", "--output-root", str(self.output_root)])
        self.assertIn(cli._messages()["blocked_STATE_CHANGED_OUTSIDE_LEDGER"], output)
        ledger.write_text(json.dumps(dict(entry, portfolio_hash_before="e" * 64)) + "\n", encoding="utf-8")
        code, output = self.propose()
        self.assertEqual(code, 0)
        proposal = self.latest()
        self.assertIn("STATE_CHANGED_OUTSIDE_LEDGER", proposal["warnings"])
        self.assertEqual(proposal["unresolved_fields"], [])
        code, output = self.run_cli(["show", "--output-root", str(self.output_root)])
        self.assertIn(cli._messages()["warning_STATE_CHANGED_OUTSIDE_LEDGER"], output)
        self.assertEqual(self.state_path.read_bytes(), self.original)
        code, output = self.apply_cli("--confirm", proposal["confirm_code"], "--confirmed-via", "USER_TERMINAL")
        self.assertEqual(code, 0, output)
        last = json.loads(ledger.read_bytes().splitlines()[-1])
        self.assertTrue(last["state_changed_outside_ledger"])
        self.assertEqual(last["ledger_expected_portfolio_hash"], "f" * 64)
        self.assertEqual(ledger_status(ledger)["entries"], 2)


def _local_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return {name for name in names if (SCRIPTS / f"{name}.py").is_file()}


class BoundaryTests(unittest.TestCase):
    def test_analysis_path_never_reaches_the_apply_modules(self):
        """P3 2: manual analysis (and every local module it imports, transitively) cannot import apply."""
        seen, pending = set(), ["run_manual_portfolio_analysis"]
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            pending.extend(_local_imports(SCRIPTS / f"{name}.py") - seen)
        self.assertIn("kiwoom_broker_shadow", seen)
        self.assertIn("kiwoom_account_readonly_bridge", seen)
        self.assertTrue({"apply_user_confirmed_broker_snapshot", "reconcile_broker_state"}.isdisjoint(seen))

    def test_proposal_module_imports_only_the_standard_library_and_validation(self):
        self.assertEqual(_local_imports(SCRIPTS / "kiwoom_broker_shadow.py"), {"validation_common"})


class RepositoryRuleTests(unittest.TestCase):
    IGNORED = ("stock-strategy-system/backups/", "stock-strategy-system/reconciliation_ledger.jsonl",
               "workspace/outputs/reconciliation/")

    def test_state_backups_ledger_and_outputs_are_git_ignored(self):
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for entry in self.IGNORED:
            self.assertIn(entry, lines)
        if shutil.which("git") is None or not (ROOT / ".git").exists():
            self.skipTest("git checkout not available")
        samples = ["stock-strategy-system/backups/portfolio_state.r14.20261001T000000000000Z.json",
                   "stock-strategy-system/reconciliation_ledger.jsonl",
                   "workspace/outputs/reconciliation/20261001T000000Z/reconciliation_proposal.json"]
        result = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "--no-index", *samples],
                                capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(sorted(result.stdout.split()), sorted(samples))

    def test_agent_rules_require_snapshot_and_user_confirmation(self):
        # 2026-10-10 wording (redesign T1): portfolio facts change only from a verified read-only broker snapshot,
        # written through the user-confirmed apply path or by the auto-core only when its invariants pass;
        # fills come from broker records, never from prices.
        for name in ("CLAUDE.md", "AGENTS.md"):
            text = " ".join((ROOT / name).read_text(encoding="utf-8").split())
            self.assertIn("only from a verified read-only broker snapshot", text, name)
            self.assertNotIn("explicit user confirmation or a verified read-only broker snapshot", text, name)
            self.assertRegex(text, r"reconcile_broker_state\.py apply|auto-core[^.;]*invariant", name)
            self.assertRegex(text, r"Never infer (?:a fill|fills) from price mov", name)

    def test_claude_code_denies_apply_and_direct_state_edits(self):
        deny = set(load_json(ROOT / ".claude/settings.json")["permissions"]["deny"])
        for rule in ("Bash(*reconcile_broker_state.py apply*)", "PowerShell(*reconcile_broker_state.py apply*)",
                     "Edit(/stock-strategy-system/portfolio_state.json)",
                     "Edit(/stock-strategy-system/reconciliation_ledger.jsonl)",
                     "Edit(/stock-strategy-system/backups/**)"):
            self.assertIn(rule, deny)

    def test_cowork_procedure_documents_the_confirmation_rules(self):
        text = (ROOT / "manage-us-stock-strategy/references/broker-snapshot-reconciliation.md").read_text(
            encoding="utf-8")
        for fragment in ("reconcile_broker_state.py propose", "reconcile_broker_state.py show",
                         "--confirmed-via COWORK_CHAT_USER_MESSAGE", "--confirmed-via USER_TERMINAL",
                         "run_manual_portfolio_analysis.py"):
            self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
