#!/usr/bin/env python3
"""Pinned analysis -> state-write boundary tests (I4 R6).

test_04 and test_08 originally lived in the released
test_manual_portfolio_analysis.py; they are kept there and repeated here, in a
pinned file, with the same assertions and a wider sentinel set. The fixture
helpers are copied into this file, so it imports nothing from that module.
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import manual_data_guards as guards  # noqa: E402
import run_manual_portfolio_analysis as manual  # noqa: E402
from validation_common import validate_instance  # noqa: E402

# Fixture helpers copied verbatim from test_manual_portfolio_analysis.py (I4 R6, commit e42f9db)
# so this pinned file does not depend on the released test module.
from instrument_identity_authority import InstrumentIdentityView  # noqa: E402
from session_authority import SessionAuthorityView, SessionWindow  # noqa: E402

OBSERVED_AT = "2026-08-21T22:00:00+00:00"
SAME_DAY = "2026-08-21"
PREVIOUS_DAY = "2026-08-20"
AUTHORITY_COHORT = "synthetic-shared-authority-cohort"


def synthetic_identity_view(
    *, ticker: str, operating_mic: str | None = "XNAS",
    status: str = "VERIFIED", reason: str = "OK",
    cohort: str | None = AUTHORITY_COHORT,
) -> InstrumentIdentityView:
    verified = status == "VERIFIED"
    return InstrumentIdentityView(
        authority_status=status,
        authority_reason=reason,
        authority_id="US_EQUITY_INSTRUMENT_IDENTITY_CURRENT_V1",
        registry_version="synthetic-registry-v1" if verified else None,
        registry_hash="b" * 64 if verified else None,
        activation_cohort_id=cohort if verified else None,
        ticker_namespace="US_EXCHANGE_LISTED",
        ticker=ticker,
        security_name=f"Synthetic {ticker}" if verified else None,
        instrument_type="EQUITY" if verified else None,
        security_class="COMMON_STOCK" if verified else None,
        primary_listing_venue_name="Synthetic Venue" if verified else None,
        primary_listing_segment_mic=("XNGS" if verified else None),
        primary_listing_operating_mic=(operating_mic if verified else None),
        effective_from=None,
        effective_from_basis="CURRENT_AS_OF_ONLY" if verified else None,
        effective_to=None,
        authority_as_of="2026-08-01T00:00:00+00:00" if verified else None,
        source_packet_id="synthetic-packet" if verified else None,
        source_packet_hash="a" * 64 if verified else None,
        source_ref_ids=(f"synthetic-{ticker}",) if verified else (),
        decision_as_of=OBSERVED_AT,
    )


def synthetic_authority_view(
    *, mic: str | None, expected_session: str | None = PREVIOUS_DAY,
    status: str = "VERIFIED", reason: str = "OK",
    cohort: str | None = AUTHORITY_COHORT,
) -> SessionAuthorityView:
    expected = None
    if expected_session is not None and status == "VERIFIED":
        expected = SessionWindow(
            session_date=expected_session,
            core_open_at=f"{expected_session}T09:30:00-04:00",
            core_close_at=f"{expected_session}T16:00:00-04:00",
            close_type="REGULAR",
        )
    return SessionAuthorityView(
        contract_version="2.0",
        authority_mode="CURRENT",
        authority_status=status,
        authority_reason=reason,
        calendar_policy_identity="US_EQUITIES_CORE_SESSION_V2",
        primary_listing_operating_mic=mic,
        operating_mic_scope=("XNYS", "XNAS", "XCBO"),
        timezone_identity="America/New_York",
        calendar_version="synthetic-m1-v1",
        calendar_hash="c" * 64,
        source_bundle_id="synthetic-m1-bundle",
        coverage_start="2026-08-01",
        coverage_end="2026-08-31",
        authority_as_of="2026-08-01T00:00:00+00:00",
        activation_cohort_id=cohort,
        observed_at=OBSERVED_AT,
        decision_as_of=OBSERVED_AT,
        current_et_date=SAME_DAY,
        market_phase="POST_CORE",
        current_date_session=None,
        expected_completed_session=expected,
    )


def account_reader_for(
    holdings: dict[str, float],
    costs: dict[str, float],
    *,
    holdings_status: str = "PASS",
    holdings_complete: bool = True,
    orderable_cash: float | None = 25.0,
    retrieved_at: str | None = OBSERVED_AT,
):
    def reader(requests):
        results = []
        for request in requests:
            operation = request["operation"]
            data = []
            status = "PASS"
            complete = True
            if operation == "account_holdings_read":
                status = holdings_status
                complete = holdings_complete
                data = [
                    {
                        "stex_nm": "NASDAQ",
                        "crnc_code": "USD",
                        "stk_cd": ticker,
                        "frgn_stk_nm": ticker,
                        "qty": quantity,
                        "poss_qty": quantity,
                        "sell_alowq": quantity,
                        "frgn_stk_book_uv": costs.get(ticker),
                        "now_pric": None,
                        "evlt_amt": None,
                        "pl_amt": None,
                        "pl_rt": None,
                    }
                    for ticker, quantity in holdings.items()
                ] if status in {"PASS", "PARTIAL"} else []
            elif operation == "account_deposit_read":
                data = [{
                    "crnc_code": "USD",
                    "crnc_nm": "US Dollar",
                    "fc_entra": orderable_cash,
                    "fc_pymn_alowa": orderable_cash,
                    "fc_ord_alowa": orderable_cash,
                }]
            elif operation == "account_deposit_detail_read":
                data = [{}]
            result = {
                "bridge_status": status,
                "operation": operation,
                "data": data,
                "pagination": {
                    "api_id": ("ust21070" if operation == "account_holdings_read" else
                               "ust21050" if operation == "account_open_items" else "READ_ONLY"),
                    "pages": 1,
                    "complete": complete,
                    "exhausted": complete,
                },
                "portfolio_mutation": False,
                "quantity_authority": "none",
                "order_authority": False,
            }
            if retrieved_at is not None:
                result["retrieved_at"] = retrieved_at
            results.append(result)
        return results

    return reader


def market_reader_for(
    tickers: list[str],
    *,
    health: bool = True,
    quote_missing: set[str] | None = None,
    include_same_day: set[str] | None = None,
    include_previous: set[str] | None = None,
    request_log: list[dict] | None = None,
    call_log: list[list[dict]] | None = None,
    retrieved_at_by_operation: dict[str, str | None] | None = None,
):
    quote_missing = set(quote_missing or set())
    same_day = set(tickers) if include_same_day is None else set(include_same_day)
    previous = set(tickers) if include_previous is None else set(include_previous)
    retrieved_at_by_operation = dict(retrieved_at_by_operation or {})

    def reader(requests):
        if request_log is not None:
            request_log.extend(dict(request) for request in requests)
        if call_log is not None:
            call_log.append([dict(request) for request in requests])
        results = []
        for request in requests:
            operation = request["operation"]
            ticker = request.get("ticker")
            if operation == "oauth_health":
                result = {
                    "bridge_status": "PASS" if health else "KIWOOM_API_UNAVAILABLE",
                    "failure_type": None if health else "AUTHENTICATION_FAILURE",
                    "authenticated": health,
                    "operation": operation,
                    "order_authority": False,
                }
            elif operation == "market_quote":
                missing = ticker in quote_missing
                result = {
                    "bridge_status": "KIWOOM_API_UNAVAILABLE" if missing else "PASS",
                    "operation": operation,
                    "ticker": ticker,
                    "data": [] if missing else [{"cur_prc": 100.0}],
                    "order_authority": False,
                }
            elif operation == "daily_chart":
                rows = []
                if ticker in same_day:
                    rows.append({"dt": "20260821", "cur_prc": 101.0,
                                 "open_pric": 100.0, "high_pric": 102.0,
                                 "low_pric": 99.0, "acc_trde_qty": 1000000})
                if ticker in previous:
                    rows.append({"dt": "20260820", "cur_prc": 99.0,
                                 "open_pric": 98.0, "high_pric": 100.0,
                                 "low_pric": 97.0, "acc_trde_qty": 1000000})
                result = {
                    "bridge_status": "PASS",
                    "operation": operation,
                    "ticker": ticker,
                    "data": rows,
                    "pagination": {"api_id": "usa06012", "status": "SUFFICIENT",
                                   "pages_fetched": 1,
                                   "pages": [{"page_index": 1, "api_id": "usa06012",
                                              "retrieved_at": OBSERVED_AT}]},
                    "requested_price_basis": "RAW",
                    "order_authority": False,
                }
            timestamp_key = f"{operation}:{ticker}" if ticker is not None else operation
            retrieved_at = retrieved_at_by_operation.get(
                timestamp_key,
                retrieved_at_by_operation.get(operation, OBSERVED_AT),
            )
            if retrieved_at is not None:
                result["retrieved_at"] = retrieved_at
            results.append(result)
        return results

    return reader


def system_portfolio(
    holdings: dict[str, float] | None = None,
    costs: dict[str, float] | None = None,
    cash: float = 25.0,
) -> dict:
    return {
        "state_revision": 7,
        "last_updated_at": "2026-08-20T00:00:00+00:00",
        "holdings": holdings or {"AAA": 1.0},
        "average_cost_usd": costs or {"AAA": 80.0},
        "available_cash_usd": cash,
    }


MODULE_PATH = SCRIPTS / "run_manual_portfolio_analysis.py"
PINNED_MANUAL_MODULES = (
    SCRIPTS / "manual_data_guards.py",
    SCRIPTS / "scheduled_input_gate.py",
)
SCHEMA = ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
PROVENANCE_POLICY = ROOT / "workspace/policies/continuous_improvement_policy.json"
FORBIDDEN_MODULES = {
    "run_portfolio_strategy_orchestrator",
    "automation_delivery",
    "shadow_acceptance",
    "apply_user_confirmed_broker_snapshot",
    "migrate_integrated_shadow_cohort",
    # R6 additions: other state or journal writers stay out of the analysis path.
    "reconcile_broker_state",
    "portfolio_review_journal",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    return imported


class ManualAnalysisStateWriteBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance_policy = json.loads(PROVENANCE_POLICY.read_text(encoding="utf-8"))

    def setUp(self):
        def identity_resolver(ticker, *, decision_as_of=None, authority_mode="CURRENT"):
            del decision_as_of, authority_mode
            return synthetic_identity_view(ticker=ticker, operating_mic="XNAS")

        def session_resolver(observed_at, *, primary_listing_operating_mic,
                             decision_as_of=None, authority_mode="CURRENT"):
            del observed_at, decision_as_of, authority_mode
            return synthetic_authority_view(mic=primary_listing_operating_mic,
                                            expected_session=PREVIOUS_DAY)

        for name, side_effect in (("resolve_instrument_identity", identity_resolver),
                                  ("derive_us_market_session_authority", session_resolver)):
            patcher = patch.object(manual, name, side_effect=side_effect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def build_report(self, *, run_manual_preflight=None, **kwargs) -> dict:
        state = system_portfolio()
        return (run_manual_preflight or manual.run_manual_preflight)(
            manual_run_id=kwargs.pop("manual_run_id", "manual-boundary-test-0001"),
            system_portfolio=state,
            system_portfolio_source="TEST_ONLY/system-portfolio.json",
            system_portfolio_sha256="a" * 64,
            provenance_policy=self.provenance_policy,
            account_reader=account_reader_for(state["holdings"], state["average_cost_usd"]),
            market_reader=market_reader_for(sorted(state["holdings"])),
            maximum_broker_age_seconds=900,
            decision_as_of=OBSERVED_AT,
            observed_at=OBSERVED_AT,
            **kwargs,
        )

    def test_04_writer_order_and_mutation_sentinels_are_never_called(self):
        calls = []

        def fail(name):
            def sentinel(*args, **kwargs):
                calls.append(name)
                raise AssertionError(f"forbidden capability called: {name}")
            return sentinel

        with patch("pathlib.Path.write_text", side_effect=fail("file_writer")), \
             patch("pathlib.Path.write_bytes", side_effect=fail("byte_writer")), \
             patch("pathlib.Path.unlink", side_effect=fail("file_delete")), \
             patch("os.replace", side_effect=fail("atomic_overwrite")), \
             patch("os.rename", side_effect=fail("rename")):
            report = self.build_report()
        self.assertEqual([], calls)
        self.assertEqual("REPORT_ONLY_CREATE_ONLY", report["mutation_status"])
        self.assertFalse(report["order_authority"])
        self.assertEqual("none", report["quantity_authority"])
        self.assertIsNone(report["execution_quantity"])
        self.assertEqual([], validate_instance(report, SCHEMA))

    def test_08_forbidden_high_level_entrypoints_are_absent_and_not_called(self):
        self.assertTrue(FORBIDDEN_MODULES.isdisjoint(_imported_modules(MODULE_PATH)))
        for pinned in PINNED_MANUAL_MODULES:
            with self.subTest(module=pinned.name):
                self.assertTrue(FORBIDDEN_MODULES.isdisjoint(_imported_modules(pinned)))

        calls = []
        fake_modules = {}
        for name in FORBIDDEN_MODULES:
            fake = types.ModuleType(name)
            fake.main = lambda *args, _name=name, **kwargs: calls.append(_name)
            fake_modules[name] = fake
        spec = importlib.util.spec_from_file_location("manual_boundary_isolated_import", MODULE_PATH)
        self.assertIsNotNone(spec)
        isolated = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, fake_modules):
            assert spec.loader is not None
            spec.loader.exec_module(isolated)
            with patch.object(isolated, "resolve_instrument_identity", manual.resolve_instrument_identity), \
                 patch.object(isolated, "derive_us_market_session_authority",
                              manual.derive_us_market_session_authority):
                self.build_report(run_manual_preflight=isolated.run_manual_preflight)
        self.assertEqual([], calls)

    def test_normalization_failure_hard_fails_and_never_uses_empty_broker_holdings(self):
        with patch.object(guards, "normalize_snapshot", side_effect=ValueError("BROKER_OPERATION_NOT_ALLOWLISTED")):
            report = self.build_report()
        self.assertIn(guards.BROKER_NORMALIZATION_FAILED, report["hard_fail_reasons"])
        self.assertIn("BROKER_HOLDINGS_UNAVAILABLE", report["hard_fail_reasons"])
        self.assertEqual("FAIL", report["preflight_status"])
        self.assertEqual("UNVERIFIED", report["evidence_grade"])
        self.assertEqual("UNAVAILABLE", report["broker_snapshot_status"])
        self.assertEqual("UNKNOWN", report["broker_diff_status"])
        self.assertEqual("SYSTEM_PORTFOLIO_STATE_FALLBACK", report["manual_analysis_view"]["holding_source"])
        self.assertEqual({"AAA": 1.0}, report["manual_analysis_view"]["holdings"])
        self.assertFalse(report["order_authority"])
        self.assertEqual([], validate_instance(report, SCHEMA))


if __name__ == "__main__":
    unittest.main()
