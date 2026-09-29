#!/usr/bin/env python3
"""Negative and isolation tests for the M1 manual portfolio preflight."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
SCHEMA = ROOT / "manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json"
PROVENANCE_POLICY = ROOT / "workspace/policies/continuous_improvement_policy.json"
MODULE_PATH = SCRIPTS / "run_manual_portfolio_analysis.py"
sys.path.insert(0, str(SCRIPTS))

import run_manual_portfolio_analysis as manual_preflight_module  # noqa: E402
from instrument_identity_authority import InstrumentIdentityView  # noqa: E402
from run_manual_portfolio_analysis import (  # noqa: E402
    ACCOUNT_READ_OPERATIONS,
    _acquisition_complete_cutoff,
    _current_price_record,
    _number,
    _select_last_verified_finalized_bar,
    _temporal_evidence_valid,
    _write_immutable_report,
    run_manual_preflight,
    select_last_verified_finalized_bar,
)
from session_aware_market_data import kiwoom_daily_observation  # noqa: E402
from session_authority import (  # noqa: E402
    SessionAuthorityView,
    SessionWindow,
    _derive_us_market_session_authority_from_root,
)
from validation_common import validate_instance  # noqa: E402


OBSERVED_AT = "2026-08-21T22:00:00+00:00"
ACCOUNT_RETRIEVED_AT = "2026-08-21T22:00:02+00:00"
HEALTH_RETRIEVED_AT = "2026-08-21T22:00:03+00:00"
QUOTE_RETRIEVED_AT = "2026-08-21T22:00:04+00:00"
HISTORY_RETRIEVED_AT = "2026-08-21T22:00:06+00:00"
POST_CUTOFF_RETRIEVED_AT = "2026-08-21T22:00:07+00:00"
ROLLOVER_RETRIEVED_AT = "2026-08-22T04:01:00+00:00"
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


def write_independent_m1_calendar_fixture(trusted_root: Path) -> None:
    sessions = [
        {
            "session_date": session_date,
            "core_open_at": f"{session_date}T09:30:00-04:00",
            "core_close_at": f"{session_date}T16:00:00-04:00",
            "close_type": "REGULAR",
        }
        for session_date in ("2026-08-19", "2026-08-20", "2026-08-21")
    ]
    artifact = {
        "artifact_schema_version": "2.0",
        "calendar_policy_identity": "US_EQUITIES_CORE_SESSION_V2",
        "timezone_identity": "America/New_York",
        "operating_mic_scope": ["XNYS", "XNAS", "XCBO"],
        "source_families": ["NYSE_GROUP", "NASDAQ", "CBOE"],
        "coverage_start": "2026-08-19",
        "coverage_end": "2026-08-21",
        "source_bundle_id": "independent-m1-fixture",
        "source_bundle_hash": "d" * 64,
        "calendar_version": "independent-m1-v1",
        "generated_at": "2026-08-18T01:00:00+00:00",
        "authority_as_of": "2026-08-18T00:00:00+00:00",
        "operating_mic_agreement_status": "VERIFIED",
        "sessions": sessions,
        "closures": [],
    }

    def canonical_bytes(value):
        return (
            json.dumps(
                value, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )

    artifact_bytes = canonical_bytes(artifact)
    artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()
    activation = {
        "activation_schema_version": "2.0",
        "activation_status": "ACTIVE",
        "activation_reason_code": "INITIAL_BOOTSTRAP",
        "activation_reason": "Independent M1 synthetic fixture",
        "calendar_policy_identity": artifact["calendar_policy_identity"],
        "active_calendar_hash": artifact_hash,
        "active_calendar_version": artifact["calendar_version"],
        "timezone_identity": artifact["timezone_identity"],
        "operating_mic_scope": artifact["operating_mic_scope"],
        "source_families": artifact["source_families"],
        "coverage_start": artifact["coverage_start"],
        "coverage_end": artifact["coverage_end"],
        "source_bundle_id": artifact["source_bundle_id"],
        "source_bundle_hash": artifact["source_bundle_hash"],
        "authority_as_of": artifact["authority_as_of"],
        "activated_at": "2026-08-18T02:00:00+00:00",
        "authority_modes_allowed": ["CURRENT"],
        "activation_cohort_id": AUTHORITY_COHORT,
    }
    activation_path = trusted_root / "workspace/policies/session_calendar_activation.json"
    artifact_path = (
        trusted_root / "workspace/calendar-authority/artifacts" / artifact_hash
        / "us-equities-core-session-v2.calendar.json"
    )
    activation_path.parent.mkdir(parents=True)
    artifact_path.parent.mkdir(parents=True)
    activation_path.write_bytes(canonical_bytes(activation))
    artifact_path.write_bytes(artifact_bytes)


def create_directory_reparse(link: Path, target: Path) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr or completed.stdout)
        return
    link.symlink_to(target, target_is_directory=True)


def remove_directory_reparse(link: Path) -> None:
    if os.name == "nt":
        os.rmdir(link)
    else:
        link.unlink()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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



def captured_handoff_fixture(*, mutate_capture=None, mutate_results=None, observed_at=POST_CUTOFF_RETRIEVED_AT):
    """Synthetic local capture bytes; never an acquisition approval."""
    import copy
    import hashlib
    state = system_portfolio()
    tickers = sorted(state["holdings"])
    account_requests = [{"operation": op} for op in manual_preflight_module.ACCOUNT_READ_OPERATIONS]
    market_requests = [{"operation": "oauth_health"}]
    market_requests += [{"operation": "market_quote", "ticker": t, "fx_applied": False} for t in tickers]
    market_requests += [{"operation": "daily_chart", "ticker": t, "completed_session": PREVIOUS_DAY,
                         "price_basis": "RAW", "fx_applied": False} for t in tickers]
    accounts = account_reader_for(state["holdings"], state["average_cost_usd"])(account_requests)
    markets = market_reader_for(tickers, include_same_day=set())(market_requests)
    if mutate_results:
        mutate_results(accounts + markets)
    document = {"run_id": "manual-test-run-0001", "started_at": "2026-08-21T21:59:59+00:00",
                "observed_at": "2026-08-21T22:00:01+00:00", "results": copy.deepcopy(accounts + markets),
                "requests": copy.deepcopy(account_requests + market_requests),
                "request_sha256": manual_preflight_module.canonical_hash(account_requests + market_requests)}
    if mutate_capture:
        mutate_capture(document)
    raw = json.dumps(document, sort_keys=True).encode("utf-8")
    artifacts = [(raw, hashlib.sha256(raw).hexdigest())]
    def account_reader(requests):
        return copy.deepcopy(accounts)
    def market_reader(requests):
        return copy.deepcopy(markets)
    return {"observed_at": observed_at, "decision_as_of": observed_at,
            "parent_capture_artifacts": artifacts, "account_reader_override": account_reader,
            "market_reader_override": market_reader}, artifacts


class ManualPortfolioAnalysisTest(unittest.TestCase):
    def direction_fixture(self, *, omitted=False, mutate_results=None):
        def fail_auxiliary(rows):
            item = next(x for x in rows if x["operation"] == "account_open_items")
            item.update(bridge_status="KIWOOM_API_RESPONSE_ERROR", failure_type="API_RESPONSE_ERROR",
                        data=[], retrieved_at=None, pagination={"complete": False})
            if mutate_results:
                mutate_results(rows)
        kwargs, artifacts = captured_handoff_fixture(mutate_results=fail_auxiliary)
        if omitted:
            doc = json.loads(artifacts[0][0])
            accounts = ["account_deposit_read", "account_holdings_read", "account_open_items"]
            pairs = [(q, r) for q, r in zip(doc["requests"], doc["results"])
                     if not q["operation"].startswith("account_") or q["operation"] in accounts]
            doc["requests"], doc["results"] = map(list, zip(*pairs))
            doc["request_sha256"] = manual_preflight_module.canonical_hash(doc["requests"])
            raw = json.dumps(doc, sort_keys=True).encode()
            artifacts = [(raw, hashlib.sha256(raw).hexdigest())]
            kwargs["parent_capture_artifacts"] = artifacts
            kwargs["account_operations"] = accounts
            kwargs["account_reader_override"] = lambda reqs: [dict(r) for q, r in pairs if q in reqs]
        kwargs["direction_only"] = True
        return kwargs, artifacts

    def test_direction_alignment_auxiliary_failure_and_omission(self):
        for omitted in (False, True):
            with self.subTest(omitted=omitted):
                kwargs, artifacts = self.direction_fixture(omitted=omitted)
                report = self.build_report(**kwargs)
                self.assertEqual(report["preflight_status"], "PARTIAL")
                self.assertEqual(report["evidence_grade"], "GRADE_B")
                self.assertTrue(report["provenance"]["decision_quality_eligible"])
                self.assertFalse(report["broker_observed_state"]["scope_complete"])
                self.assertEqual(report["broker_observed_state"]["operation_statuses"]["account_open_items"],
                                 "KIWOOM_API_RESPONSE_ERROR")
                self.assertIsNone(report["broker_observed_state"]["open_order_evidence"]["retrieved_at"])
                if omitted:
                    self.assertEqual(report["broker_observed_state"]["operation_statuses"]["account_fills_read"], "NOT_REQUESTED")
                self.assertTrue(manual_preflight_module.validate_manual_acquisition_handoff(
                    report, artifacts, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT, maximum_age_seconds=900))
                self.assertEqual(validate_instance(report, SCHEMA), [])
                self.assertEqual(report["quantity_authority"], "none")
                self.assertIsNone(report["execution_quantity"])
                self.assertFalse(report["order_authority"])

    def test_local_same_day_completed_bar_can_be_grade_b_without_provider_finalization(self):
        import copy
        from continuous_improvement_sidecar import manual_grade_b_eligible
        kwargs, artifacts = captured_handoff_fixture()
        doc = json.loads(artifacts[0][0])
        for request in doc["requests"]:
            if request["operation"] == "daily_chart":
                request["completed_session"] = SAME_DAY
        daily = next(item for item in doc["results"] if item["operation"] == "daily_chart")
        daily["data"] = [{"dt": "20260821", "cur_prc": 101.0, "open_pric": 100.0,
                          "high_pric": 102.0, "low_pric": 99.0, "acc_trde_qty": 1000000}]
        doc["request_sha256"] = manual_preflight_module.canonical_hash(doc["requests"])
        raw = json.dumps(doc, sort_keys=True).encode()
        artifacts = [(raw, hashlib.sha256(raw).hexdigest())]
        market = [item for item in doc["results"] if item["operation"] in
                  {"oauth_health", "market_quote", "daily_chart"}]
        kwargs.update(parent_capture_artifacts=artifacts, direction_only=True,
                      expected_completed_session=SAME_DAY,
                      market_reader_override=lambda requests: copy.deepcopy(market))
        report = self.build_report(**kwargs)
        self.assertEqual(report["finalized_bar_preflight_status"], "FAIL")
        self.assertEqual(report["last_verified_finalized_bar_status"], "NOT_VERIFIED")
        self.assertEqual(report["manual_analysis_view"]["provider_finalization_verified"], "NOT_VERIFIED")
        self.assertEqual(report["manual_analysis_view"]["local_regular_bar_coherence"]["AAA"]["status"], "PASS")
        self.assertEqual(report["evidence_grade"], "GRADE_B")
        run = dict(report, execution_origin="MANUAL", decision_mode="MANUAL_READ_ONLY",
                   provenance_evidence={"manual_run_id": report["manual_run_id"]})
        self.assertTrue(manual_grade_b_eligible(
            run, direction_evidence=report, parent_capture_artifacts=artifacts,
            analysis_observed_at=POST_CUTOFF_RETRIEVED_AT,
        ))
        self.assertEqual(validate_instance(report, SCHEMA), [])

    def test_direction_alignment_missing_core_values(self):
        def missing_cash(rows):
            item = next(x for x in rows if x["operation"] == "account_deposit_read")
            item["data"] = []
        kwargs, _ = self.direction_fixture(mutate_results=missing_cash)
        self.assertEqual(self.build_report(**kwargs)["evidence_grade"], "UNVERIFIED")

    def test_direction_alignment_rejects_status_and_source_forgery(self):
        import copy
        kwargs, artifacts = self.direction_fixture()
        report = self.build_report(**kwargs)
        mutations = [
            lambda r: r.update(identity_registry_hash="f" * 64),
            lambda r: r.update(calendar_hash="f" * 64),
            lambda r: r.update(preflight_status="PASS"),
            lambda r: r["manual_analysis_view"].pop("decision_evidence_scope"),
            lambda r: r.update(run_mode="LIVE_READ_ONLY"),
            lambda r: r["current_price_evidence"][0]["record"].update(close=999999),
            lambda r: r["manual_analysis_view"]["acquisition_handoff"]["bindings"][0].update(source_sha256="f" * 64),
            lambda r: r["manual_analysis_view"]["local_regular_bar_coherence"]["AAA"].update(input_sha256="f" * 64),
            lambda r: r["manual_analysis_view"]["local_regular_bar_coherence"]["AAA"].update(status="FAIL"),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(report); mutate(bad)
            self.assertFalse(manual_preflight_module.validate_manual_direction_evidence(
                bad, artifacts, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT))
        self.assertFalse(manual_preflight_module.validate_manual_direction_evidence(
            report, None, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT))
        changed = json.loads(artifacts[0][0])
        daily = next(x for x in changed["results"] if x["operation"] == "daily_chart")
        daily["data"][-1].update(cur_prc=98.0, high_pric=100.0)
        changed_bytes = json.dumps(changed, sort_keys=True).encode()
        self.assertFalse(manual_preflight_module.validate_manual_direction_evidence(
            report, [(changed_bytes, hashlib.sha256(changed_bytes).hexdigest())],
            analysis_observed_at=POST_CUTOFF_RETRIEVED_AT))

    def test_direction_alignment_stale_future_and_identity(self):
        kwargs, artifacts = self.direction_fixture()
        report = self.build_report(**kwargs)
        for at in ("2026-08-21T22:20:00+00:00", "2026-08-21T21:59:59+00:00"):
            self.assertFalse(manual_preflight_module.validate_manual_direction_evidence(
                report, artifacts, analysis_observed_at=at))
        self.identity_forced_reason = "IDENTITY_TEST_MISMATCH"
        self.assertEqual(self.build_report(**kwargs)["evidence_grade"], "UNVERIFIED")

    def test_direction_alignment_general_manual_is_unchanged(self):
        kwargs, _ = self.direction_fixture()
        kwargs.pop("direction_only")
        report = self.build_report(**kwargs)
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")

    def test_direction_alignment_core_operation_failure_cannot_be_promoted(self):
        for op in ("account_holdings_read", "account_deposit_read", "oauth_health", "market_quote", "daily_chart"):
            with self.subTest(operation=op):
                def fail(rows):
                    item = next(x for x in rows if x["operation"] == op)
                    item.update(bridge_status="KIWOOM_API_RESPONSE_ERROR", failure_type="API_RESPONSE_ERROR",
                                data=[], retrieved_at=None, pagination={"complete": False})
                kwargs, _ = self.direction_fixture(mutate_results=fail)
                self.assertNotEqual(self.build_report(**kwargs)["evidence_grade"], "GRADE_B")

    def test_direction_alignment_sidecar_requires_bytes_and_exact_run_binding(self):
        import copy
        from continuous_improvement_sidecar import manual_grade_b_eligible
        kwargs, artifacts = self.direction_fixture()
        report = self.build_report(**kwargs)
        run = dict(report, execution_origin="MANUAL", decision_mode="MANUAL_READ_ONLY",
                   provenance_evidence={"manual_run_id": report["manual_run_id"]})
        context = dict(direction_evidence=report, parent_capture_artifacts=artifacts,
                       analysis_observed_at=POST_CUTOFF_RETRIEVED_AT)
        self.assertFalse(manual_grade_b_eligible(run))
        self.assertTrue(manual_grade_b_eligible(run, **context))
        for mutate in (
            lambda r: r.update(execution_origin="REPLAY"),
            lambda r: r.update(execution_origin="SCHEDULED_GENUINE"),
            lambda r: r.update(decision_mode="LIVE_READ_ONLY"),
            lambda r: r["provenance_evidence"].update(manual_run_id="different-run"),
            lambda r: r.update(manual_data_verification_status="FAILED"),
        ):
            bad = copy.deepcopy(run); mutate(bad)
            self.assertFalse(manual_grade_b_eligible(bad, **context))

    def test_direction_alignment_cash_zero_unknown_and_proceeds(self):
        def zero_cash(rows):
            item = next(x for x in rows if x["operation"] == "account_deposit_read")
            for row in item["data"]:
                for field in ("fc_entra", "fc_pymn_alowa", "fc_ord_alowa"):
                    row[field] = "0"
        kwargs, _ = self.direction_fixture(mutate_results=zero_cash)
        report = self.build_report(**kwargs)
        self.assertEqual(report["evidence_grade"], "GRADE_B")
        self.assertEqual(report["verified_orderable_cash_usd"], 0)
        self.assertEqual(report["broker_observed_state"]["cash"]["cash_status"], "VERIFIED_ZERO")
        for field in ("fc_entra", "fc_pymn_alowa", "fc_ord_alowa"):
            def missing(rows):
                item = next(x for x in rows if x["operation"] == "account_deposit_read")
                for row in item["data"]:
                    row.pop(field, None)
                    row["expected_sale_proceeds_usd"] = "9999"
            kwargs, _ = self.direction_fixture(mutate_results=missing)
            self.assertNotEqual(self.build_report(**kwargs)["evidence_grade"], "GRADE_B")

    def test_direction_alignment_default_handoff_rejects_forged_upgrade(self):
        kwargs, artifacts = self.direction_fixture()
        kwargs.pop("direction_only")
        report = self.build_report(**kwargs)
        report.update(evidence_grade="GRADE_B", manual_data_verification_status="VERIFIED_REAL_DATA")
        self.assertFalse(manual_preflight_module.validate_manual_acquisition_handoff(
            report, artifacts, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT, maximum_age_seconds=900))

    def test_direction_alignment_dashboard_rechecks_consumed_inputs(self):
        from portfolio_decision_dashboard import _canonical_evidence_gate, MANUAL_EVIDENCE_SCHEMA
        kwargs, artifacts = self.direction_fixture()
        report = self.build_report(**kwargs)
        plan = {"evidence_binding": {"manual_run_id": report["manual_run_id"], "decision_as_of": report["decision_as_of"]}}
        def blockers(mode="INITIAL_COMPILE", inputs=artifacts, input_mode="MANUAL_READ_ONLY"):
            return _canonical_evidence_gate(report, plan, mode, MANUAL_EVIDENCE_SCHEMA.read_bytes(),
                input_mode=input_mode, parent_capture_artifacts=inputs,
                analysis_observed_at=POST_CUTOFF_RETRIEVED_AT)[1]
        self.assertNotIn("PREFLIGHT_NOT_PASS", blockers())
        self.assertIn("PREFLIGHT_NOT_PASS", blockers(inputs=None))
        self.assertIn("PREFLIGHT_NOT_PASS", blockers(mode="HISTORICAL_REPLAY"))
        self.assertIn("PREFLIGHT_NOT_PASS", blockers(input_mode="LIVE_READ_ONLY"))

    def _assert_direction_compile(self, *, full_scope=False):
        import copy
        import portfolio_decision_dashboard as dashboard
        from test_portfolio_decision_dashboard import current_context, canonical_runtime_resolver
        kwargs, artifacts = captured_handoff_fixture() if full_scope else self.direction_fixture()
        kwargs["direction_only"] = True
        evidence = self.build_report(**kwargs)
        self.assertEqual(evidence["preflight_status"], "PASS" if full_scope else "PARTIAL")
        policy = json.loads(dashboard.DEFAULT_RISK_POLICY.read_bytes())
        tickers = [row["ticker"] for row in evidence["broker_observed_state"]["holdings"]]
        # Synthetic instruments reuse the existing normal-stock fixture mapping.
        for ticker in tickers:
            policy["fallback_instrument_mapping"][ticker] = copy.deepcopy(policy["fallback_instrument_mapping"]["NBIS"])
        plan = {"plan_id": "synthetic-direction-only-plan", "as_of": evidence["decision_as_of"],
                "plan_status": "CURRENT_APPROVED", "target_type": "TRANSITIONAL_RISK_FEASIBLE_TARGET",
                "cash_target_pct": 80, "evidence_binding": {"expected_run_id": evidence["manual_run_id"],
                "expected_decision_as_of": evidence["decision_as_of"]}, "material_unknowns": [],
                "decision_change_triggers": [], "positions": [
                    {"ticker": t, "action": "TRIM", "target_weight_pct": 10,
                     "rationale": "synthetic", "investment_horizon": "synthetic", "target_status": "APPROVED"}
                    for t in tickers]}
        digest = hashlib.sha256(dashboard._json_bytes(evidence)).hexdigest()
        context = current_context(evidence)
        context["context_generated_at"] = POST_CUTOFF_RETRIEVED_AT
        context["expected_evidence_sha256"] = digest
        report, validation = dashboard.compile_dashboard(
            evidence, plan, policy, generated_at=POST_CUTOFF_RETRIEVED_AT,
            current_session_context=context, current_session_authority_resolver=canonical_runtime_resolver(context),
            evidence_sha256=digest, parent_capture_artifacts=artifacts,
        )
        self.assertEqual(report["evidence"]["portfolio_evidence_status"], "BLOCKED")
        self.assertIn("FINALIZED_BAR_PREFLIGHT_NOT_PASS", report["evidence"]["canonical_gate_blockers"])
        self.assertIn("FINALIZED_BAR_NOT_VERIFIED", report["evidence"]["canonical_gate_blockers"])
        self.assertEqual(validation["status"], "BLOCKED")
        self.assertEqual(report["stage1"]["status"], "BLOCKED")
        self.assertEqual(report["stage2"]["status"], "BLOCKED")
        self.assertEqual(report["stage2"]["buy_advisories"], [])
        for row in report["portfolio"]["positions"]:
            self.assertIsNone(row["target_shares_reference"]["value"])
            self.assertIsNone(row["share_delta"]["value"])
            self.assertIn("DIRECTION_ONLY_EVIDENCE_NO_QUANTITY_AUTHORITY", row["blockers"])
        for row in report["swing_action_plan"]["rows"]:
            self.assertEqual(row["direction"], "DEFERRED")
            self.assertIsNone(row["price"])
            self.assertIsNone(row["shadow_sell_qty"])
            self.assertEqual(row["execution_status"], "DISABLED")

    def test_direction_alignment_full_compile_never_unlocks_quantity(self):
        self._assert_direction_compile()

    def test_direction_alignment_full_scope_still_has_no_quantity_authority(self):
        self._assert_direction_compile(full_scope=True)
        # Opt-in without captured bytes does not inherit the generic PASS route.
        self.assertEqual(self.build_report(direction_only=True)["evidence_grade"], "UNVERIFIED")

    def test_direction_alignment_pass_label_cannot_remove_source_boundary(self):
        import copy
        from continuous_improvement_sidecar import manual_grade_b_eligible
        from portfolio_decision_dashboard import _canonical_evidence_gate, MANUAL_EVIDENCE_SCHEMA
        kwargs, artifacts = self.direction_fixture()
        report = self.build_report(**kwargs)
        forged = copy.deepcopy(report)
        forged.update(preflight_status="PASS", observed_at=forged["decision_as_of"])
        forged["manual_analysis_view"].pop("acquisition_handoff")
        run = dict(forged, execution_origin="MANUAL", decision_mode="MANUAL_READ_ONLY",
                   provenance_evidence={"manual_run_id": forged["manual_run_id"]})
        self.assertFalse(manual_grade_b_eligible(run))
        plan = {"evidence_binding": {"expected_run_id": forged["manual_run_id"],
                                     "expected_decision_as_of": forged["decision_as_of"]}}
        blockers = _canonical_evidence_gate(forged, plan, "INITIAL_COMPILE", MANUAL_EVIDENCE_SCHEMA.read_bytes(),
                                           analysis_observed_at=POST_CUTOFF_RETRIEVED_AT)[1]
        self.assertIn("DIRECTION_SCOPE_INPUTS_NOT_VERIFIED", blockers)

    @classmethod
    def setUpClass(cls):
        cls.provenance_policy = json.loads(PROVENANCE_POLICY.read_text(encoding="utf-8"))

    def setUp(self):
        self.authority_expected_session = PREVIOUS_DAY
        self.authority_expected_session_by_boundary = {}
        self.authority_forced_reason = None
        self.identity_forced_reason = None
        self.identity_operating_mics = {"AAA": "XNAS"}
        self.identity_cohort = AUTHORITY_COHORT
        self.session_cohort = AUTHORITY_COHORT

        def identity_resolver(ticker, *, decision_as_of=None, authority_mode="CURRENT"):
            del decision_as_of, authority_mode
            if self.identity_forced_reason is not None:
                return synthetic_identity_view(
                    ticker=ticker,
                    status="NOT_VERIFIED",
                    reason=self.identity_forced_reason,
                    cohort=None,
                )
            operating_mic = self.identity_operating_mics.get(ticker)
            if operating_mic is None:
                return synthetic_identity_view(
                    ticker=ticker,
                    status="NOT_VERIFIED",
                    reason="PRIMARY_MIC_NOT_VERIFIED",
                    cohort=None,
                )
            return synthetic_identity_view(
                ticker=ticker,
                operating_mic=operating_mic,
                cohort=self.identity_cohort,
            )

        def resolver(
            observed_at, *, primary_listing_operating_mic,
            decision_as_of=None, authority_mode="CURRENT",
        ):
            del authority_mode
            if self.authority_forced_reason is not None:
                return synthetic_authority_view(
                    mic=primary_listing_operating_mic,
                    expected_session=None,
                    status="NOT_VERIFIED",
                    reason=self.authority_forced_reason,
                )
            if primary_listing_operating_mic not in {"XNYS", "XNAS", "XCBO"}:
                return synthetic_authority_view(
                    mic=primary_listing_operating_mic,
                    expected_session=None,
                    status="NOT_VERIFIED",
                    reason="WRONG_EXCHANGE_SCOPE",
                )
            return synthetic_authority_view(
                mic=primary_listing_operating_mic,
                expected_session=self.authority_expected_session_by_boundary.get(
                    decision_as_of or observed_at,
                    self.authority_expected_session,
                ),
                cohort=self.session_cohort,
            )

        self.identity_patch = patch.object(
            manual_preflight_module, "resolve_instrument_identity", side_effect=identity_resolver,
        )
        self.authority_patch = patch.object(
            manual_preflight_module, "derive_us_market_session_authority", side_effect=resolver,
        )
        self.identity_mock = self.identity_patch.start()
        self.authority_mock = self.authority_patch.start()

    def tearDown(self):
        self.authority_patch.stop()
        self.identity_patch.stop()


    def test_handoff_rewire_late_complete_capture_is_eligible_without_backdating(self):
        kwargs, artifacts = captured_handoff_fixture()
        report = self.build_report(**kwargs)
        self.assertEqual(report["observed_at"], POST_CUTOFF_RETRIEVED_AT)
        self.assertEqual(report["decision_as_of"], OBSERVED_AT)
        self.assertEqual(report["preflight_status"], "PASS")
        self.assertEqual(report["evidence_grade"], "GRADE_B")
        self.assertEqual(validate_instance(report, SCHEMA), [])
        proof = report["manual_analysis_view"]["acquisition_handoff"]
        self.assertEqual(proof["assurance"], "CONSUMED_INPUT_CONSISTENCY_ONLY")
        self.assertTrue(manual_preflight_module.validate_manual_acquisition_handoff(
            report, artifacts, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT, maximum_age_seconds=900))
        self.assertNotIn('"data"', json.dumps(proof))
        self.assertFalse(report["order_authority"])
        self.assertIsNone(report["execution_quantity"])

    def test_handoff_rewire_incomplete_or_changed_capture_never_unlocks(self):
        for change in [lambda d: d["results"].pop(),
                       lambda d: d["results"][0].update(data=[]),
                       lambda d: d["results"].append(dict(d["results"][0]))]:
            with self.subTest(change=change):
                kwargs, _ = captured_handoff_fixture(mutate_capture=change)
                report = self.build_report(**kwargs)
                self.assertIn("POST_ACQUISITION_ANALYSIS_REQUIRES_FRESH_EVIDENCE", report["partial_reasons"])
                self.assertNotIn("acquisition_handoff", report["manual_analysis_view"])

    def test_handoff_rewire_capture_hash_and_run_mismatch_fail_closed(self):
        kwargs, artifacts = captured_handoff_fixture()
        kwargs["parent_capture_artifacts"] = [(artifacts[0][0], "0" * 64)]
        with self.assertRaisesRegex(ValueError, "^PARENT_CAPTURE_BINDING_INVALID$"):
            self.build_report(**kwargs)
        kwargs, _ = captured_handoff_fixture(mutate_capture=lambda d: d.update(run_id="manual-other-run"))
        with self.assertRaisesRegex(ValueError, "^PARENT_CAPTURE_BINDING_INVALID$"):
            self.build_report(**kwargs)

    def test_handoff_rewire_age_and_future_capture_fail_closed(self):
        kwargs, _ = captured_handoff_fixture(observed_at="2026-08-21T22:15:01+00:00")
        report = self.build_report(**kwargs)
        self.assertIn("PARENT_CAPTURE_REPLAY_STALE", report["hard_fail_reasons"])
        self.assertNotEqual(report["preflight_status"], "PASS")
        kwargs, _ = captured_handoff_fixture(mutate_capture=lambda d: d.update(observed_at="2026-08-21T22:00:08+00:00"))
        with self.assertRaisesRegex(ValueError, "^PARENT_CAPTURE_BINDING_INVALID$"):
            self.build_report(**kwargs)


    def test_handoff_rewire_bound_failure_is_never_broker_success(self):
        def fail_open(rows):
            row = next(x for x in rows if x["operation"] == "account_open_items")
            row.update(bridge_status="KIWOOM_API_RESPONSE_ERROR", failure_type="API_RESPONSE_ERROR",
                       retrieved_at=None, data=[], pagination={"complete": False})
        kwargs, artifacts = captured_handoff_fixture(mutate_results=fail_open)
        report = self.build_report(**kwargs)
        self.assertIn("acquisition_handoff", report["manual_analysis_view"])
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertIn("ACCOUNT_EVIDENCE_NOT_VERIFIED:account_open_items", report["partial_reasons"])
        self.assertNotEqual(report["evidence_grade"], "GRADE_B")
        self.assertIsNone(report["broker_observed_state"]["open_order_evidence"]["retrieved_at"])
        self.assertTrue(manual_preflight_module.validate_manual_acquisition_handoff(
            report, artifacts, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT, maximum_age_seconds=900))


    def test_handoff_rewire_failed_input_cannot_claim_verified_grade(self):
        def fail_open(rows):
            row = next(x for x in rows if x["operation"] == "account_open_items")
            row.update(bridge_status="KIWOOM_API_RESPONSE_ERROR", failure_type="API_RESPONSE_ERROR",
                       retrieved_at=None, data=[], pagination={"complete": False})
        kwargs, artifacts = captured_handoff_fixture(mutate_results=fail_open)
        report = self.build_report(**kwargs)
        report.update(preflight_status="PASS", evidence_grade="GRADE_B",
                      manual_data_verification_status="VERIFIED_REAL_DATA")
        self.assertFalse(manual_preflight_module.validate_manual_acquisition_handoff(
            report, artifacts, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT, maximum_age_seconds=900))

    def test_handoff_rewire_missing_or_contradictory_original_requests_fail_closed(self):
        mutations = [
            lambda d: d.pop("requests"),
            lambda d: d.update(requests=[{"operation": "daily_chart", "ticker": "WRONG",
                                         "price_basis": "ADJUSTED", "completed_session": "2000-01-01",
                                         "fx_applied": True}], request_sha256="f" * 64),
            lambda d: d.update(request_sha256="f" * 64),
            lambda d: d["requests"][-1].update(price_basis="ADJUSTED"),
            lambda d: d["requests"].reverse(),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                def mutation(document):
                    mutate(document)
                    if mutations.index(mutate) >= 3:
                        document["request_sha256"] = manual_preflight_module.canonical_hash(document["requests"])
                kwargs, artifacts = captured_handoff_fixture(mutate_capture=mutation)
                report = self.build_report(**kwargs)
                self.assertNotIn("acquisition_handoff", report["manual_analysis_view"])
                self.assertNotEqual("PASS", report["preflight_status"])
                self.assertFalse(manual_preflight_module.validate_manual_acquisition_handoff(
                    report, artifacts, analysis_observed_at=POST_CUTOFF_RETRIEVED_AT,
                    maximum_age_seconds=900))

    def test_handoff_rewire_result_outside_capture_window_is_rejected(self):
        kwargs, _ = captured_handoff_fixture(
            mutate_capture=lambda d: d.update(started_at="2026-08-21T22:00:00.500000+00:00"))
        report = self.build_report(**kwargs)
        self.assertNotIn("acquisition_handoff", report["manual_analysis_view"])
        self.assertNotEqual(report["preflight_status"], "PASS")


    def test_loop_fix_cash_preserves_broker_orderable_separate_from_settled(self):
        state = system_portfolio()
        base = account_reader_for(state["holdings"], state["average_cost_usd"], orderable_cash=2.97)
        def reader(requests):
            values = base(requests)
            for value in values:
                if value["operation"] == "account_deposit_read":
                    value["data"][0]["fc_pymn_alowa"] = "0.00"
                    value["data"][0]["fc_entra"] = "0.00"
            return values
        report = self.build_report(account_reader_override=reader)
        self.assertEqual(report["verified_orderable_cash_usd"], 2.97)
        self.assertEqual(report["manual_analysis_view"]["verified_orderable_cash_usd"], 2.97)
        self.assertEqual(report["broker_observed_state"]["cash"]["settled_available_cash"], 0)
        self.assertEqual(validate_instance(report, SCHEMA), [])

    def test_loop_fix_later_analysis_keeps_original_cutoff_and_is_not_fresh(self):
        report = self.build_report(observed_at=POST_CUTOFF_RETRIEVED_AT)
        self.assertEqual(report["observed_at"], POST_CUTOFF_RETRIEVED_AT)
        self.assertEqual(report["decision_as_of"], OBSERVED_AT)
        self.assertEqual(report["manual_analysis_view"]["analysis_observed_at"], POST_CUTOFF_RETRIEVED_AT)
        self.assertEqual(report["manual_analysis_view"]["acquisition_completed_at"], OBSERVED_AT)
        self.assertIn("POST_ACQUISITION_ANALYSIS_REQUIRES_FRESH_EVIDENCE", report["partial_reasons"])
        self.assertNotEqual(report["preflight_status"], "PASS")
        self.assertNotEqual(report["evidence_grade"], "GRADE_B")

    def build_report(
        self,
        *,
        portfolio: dict | None = None,
        broker_holdings: dict[str, float] | None = None,
        broker_costs: dict[str, float] | None = None,
        holdings_status: str = "PASS",
        holdings_complete: bool = True,
        orderable_cash: float | None = 25.0,
        health: bool = True,
        quote_missing: set[str] | None = None,
        include_same_day: set[str] | None = None,
        include_previous: set[str] | None = None,
        expected_completed_session: str | None = PREVIOUS_DAY,
        manual_run_id: str = "manual-test-run-0001",
        identity_operating_mics: dict[str, str] | None = None,
        market_request_log: list[dict] | None = None,
        market_call_log: list[list[dict]] | None = None,
        account_retrieved_at: str | None = OBSERVED_AT,
        market_retrieved_at_by_operation: dict[str, str | None] | None = None,
        observed_at: str = OBSERVED_AT,
        decision_as_of: str = OBSERVED_AT,
        account_operations=None, market_operations=None, parent_capture_artifacts=None,
        account_reader_override=None, market_reader_override=None, direction_only=False,
    ) -> dict:
        self.authority_expected_session = expected_completed_session
        state = portfolio or system_portfolio()
        holdings = broker_holdings if broker_holdings is not None else dict(state["holdings"])
        costs = broker_costs if broker_costs is not None else dict(state["average_cost_usd"])
        tickers = sorted(set(state["holdings"]) | set(holdings))
        self.identity_operating_mics = (
            {ticker: "XNAS" for ticker in tickers}
            if identity_operating_mics is None
            else identity_operating_mics
        )
        return run_manual_preflight(
            manual_run_id=manual_run_id,
            system_portfolio=state,
            system_portfolio_source="TEST_ONLY/system-portfolio.json",
            system_portfolio_sha256="a" * 64,
            provenance_policy=self.provenance_policy,
            account_reader=account_reader_override or account_reader_for(
                holdings,
                costs,
                holdings_status=holdings_status,
                holdings_complete=holdings_complete,
                orderable_cash=orderable_cash,
                retrieved_at=account_retrieved_at,
            ),
            market_reader=market_reader_override or market_reader_for(
                tickers,
                health=health,
                quote_missing=quote_missing,
                include_same_day=include_same_day,
                include_previous=include_previous,
                request_log=market_request_log,
                call_log=market_call_log,
                retrieved_at_by_operation=market_retrieved_at_by_operation,
            ),
            maximum_broker_age_seconds=900,
            decision_as_of=decision_as_of,
            observed_at=observed_at,
            account_operations=account_operations, market_operations=market_operations,
            parent_capture_artifacts=parent_capture_artifacts,
            direction_only=direction_only,
        )

    @staticmethod
    def captured_failure(*, run_id="manual-test-run-0001", operation="account_open_items",
                         started_at=OBSERVED_AT, observed_at=ACCOUNT_RETRIEVED_AT,
                         retrieved_at=None, uppercase=False, mutate=None):
        failure = {
            "operation": operation, "bridge_status": "KIWOOM_API_RESPONSE_ERROR",
            "failure_type": "API_RESPONSE_ERROR", "retrieved_at": retrieved_at,
            "runtime_commit": None, "data": [], "order_authority": False,
            "quantity_authority": "none", "portfolio_mutation": False,
        }
        document = {"run_id": run_id, "started_at": started_at, "observed_at": observed_at,
                    "safe_bridge_results": [failure], "diagnostic": "SYNTHETIC_NOT_FOR_OUTPUT"}
        if uppercase:
            for key in ("run_id", "started_at", "observed_at"):
                document[key.upper()] = document.pop(key)
        if mutate is not None:
            mutate(document)
        raw = json.dumps(document).encode("utf-8")
        return failure, (raw, hashlib.sha256(raw).hexdigest())

    def report_with_failure(self, failure, artifacts=None, **kwargs):
        normal = account_reader_for({"AAA": 1.0}, {"AAA": 80.0})
        def reader(requests):
            return [dict(failure) if r["operation"] == failure["operation"] else normal([r])[0]
                    for r in requests]
        return self.build_report(account_reader_override=reader, parent_capture_artifacts=artifacts,
                                 observed_at=kwargs.pop("observed_at", POST_CUTOFF_RETRIEVED_AT), **kwargs)

    def report_with_quote_failures(self, failures, captures, *, tickers=("AAA",)):
        normal = market_reader_for(list(tickers))
        def reader(requests):
            rows = []
            for request in requests:
                if request["operation"] == "market_quote":
                    failure = next((r for r in failures if r.get("ticker") == request["ticker"]), failures[0])
                    rows.append(dict(failure))
                else:
                    rows.extend(normal([request]))
            return rows
        return self.build_report(
            portfolio=system_portfolio({ticker: 1.0 for ticker in tickers}, {ticker: 80.0 for ticker in tickers}),
            market_reader_override=reader, parent_capture_artifacts=captures,
            observed_at=POST_CUTOFF_RETRIEVED_AT,
        )

    def test_judgefix_f1_market_failure_is_not_hidden_by_daily_fallback(self):
        failure, capture = self.captured_failure(operation="market_quote",
            mutate=lambda d: d["safe_bridge_results"][0].update(ticker="AAA"))
        report = self.report_with_quote_failures([failure], [capture])
        self.assertEqual(report["current_price_status"], "AVAILABLE")
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertIn("MARKET_EVIDENCE_NOT_VERIFIED:market_quote:AAA", report["partial_reasons"])
        self.assertEqual(report["decision_as_of"], ACCOUNT_RETRIEVED_AT)
        self.assertEqual(validate_instance(report, SCHEMA), [])

    def test_judgefix_f2_tickerless_capture_does_not_bind_multiple_requests(self):
        failure, capture = self.captured_failure(operation="market_quote")
        report = self.report_with_quote_failures([failure], [capture], tickers=("AAA", "BBB"))
        self.assertEqual(report["broker_observed_state"]["acquisition_scope"]["parent_failure_timing"], [])
        self.assertIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")

    def test_judgefix_f3_failure_parent_time_is_not_broker_snapshot_time(self):
        failure, capture = self.captured_failure()
        report = self.report_with_failure(failure, [capture],
            account_operations=["account_open_items"], market_operations=[])
        self.assertEqual(report["decision_as_of"], ACCOUNT_RETRIEVED_AT)
        self.assertIsNone(report["broker_snapshot_as_of"])
        self.assertIsNone(report["broker_observed_state"]["as_of"])
        self.assertIsNone(report["broker_observed_state"]["open_order_evidence"]["retrieved_at"])
        self.assertIsNone(report["verified_orderable_cash_usd"])
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertEqual(validate_instance(report, SCHEMA), [])

    def test_judgefix_market_failure_with_own_timestamp_stays_partial(self):
        failure, _ = self.captured_failure(operation="market_quote", retrieved_at=OBSERVED_AT,
            mutate=lambda d: d["safe_bridge_results"][0].update(ticker="AAA"))
        report = self.report_with_quote_failures([failure], None)
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertIn("MARKET_EVIDENCE_NOT_VERIFIED:market_quote:AAA", report["partial_reasons"])

    def test_judgefix_explicit_ticker_captures_remain_separately_bound(self):
        failures, captures = [], []
        for ticker in ("AAA", "BBB"):
            failure, capture = self.captured_failure(operation="market_quote",
                mutate=lambda d, t=ticker: d["safe_bridge_results"][0].update(ticker=t))
            failures.append(failure)
            captures.append(capture)
        report = self.report_with_quote_failures(failures, captures, tickers=("AAA", "BBB"))
        bindings = report["broker_observed_state"]["acquisition_scope"]["parent_failure_timing"]
        self.assertEqual([(r["ticker"], r["source_sha256"]) for r in bindings],
                         [(ticker, capture[1]) for ticker, capture in zip(("AAA", "BBB"), captures)])
        self.assertNotIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])

    def test_judgefix_broker_time_uses_actual_success_timestamp(self):
        failure, _ = self.captured_failure(retrieved_at=ACCOUNT_RETRIEVED_AT)
        report = self.report_with_failure(failure)
        self.assertEqual(report["broker_snapshot_as_of"], OBSERVED_AT)
        self.assertEqual(report["broker_observed_state"]["as_of"], OBSERVED_AT)
        self.assertEqual(report["decision_as_of"], ACCOUNT_RETRIEVED_AT)

    def test_scope_limited_dispatch_and_not_requested_are_distinct(self):
        accounts = ["account_holdings_read", "account_deposit_read", "account_open_items"]
        seen, market = [], []
        normal = account_reader_for({"AAA": 1.0}, {"AAA": 80.0})
        def reader(requests):
            seen.extend(requests)
            return normal(requests)
        report = self.build_report(account_operations=accounts, market_operations=["daily_chart"],
                                   account_reader_override=reader, market_request_log=market)
        self.assertEqual([r["operation"] for r in seen], accounts)
        self.assertEqual([r["operation"] for r in market], ["daily_chart"])
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertEqual(report["finalized_bar_preflight_status"], "PASS")
        self.assertNotIn("KIWOOM_UNAVAILABLE", report["hard_fail_reasons"])
        self.assertNotIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
        state = report["broker_observed_state"]
        self.assertFalse(state["scope_complete"])
        self.assertEqual(state["operation_statuses"]["account_fills_read"], "NOT_REQUESTED")
        self.assertEqual(validate_instance(report, SCHEMA), [])

    def test_scope_empty_does_not_call_readers_or_manufacture_zero_cash(self):
        with patch.object(manual_preflight_module, "_safe_reader_call", side_effect=AssertionError) as read:
            report = self.build_report(account_operations=[], market_operations=[])
        read.assert_not_called()
        self.assertIsNone(report["verified_orderable_cash_usd"])
        self.assertIsNone(report["broker_observed_state"]["open_order_evidence"])
        self.assertNotEqual(report["evidence_grade"], "GRADE_B")
        self.assertNotIn("BROKER_HOLDINGS_UNAVAILABLE", report["hard_fail_reasons"])

    def test_scope_invalid_scope_blocks_before_any_reader(self):
        for key, value in [("account_operations", v) for v in
                           ("account_holdings_read", ["SYNTHETIC_SECRET"], ["account_holdings_read"] * 2, [{}])
                          ] + [("market_operations", ["account_holdings_read"])]:
            with self.subTest(key=key, value=value), patch.object(manual_preflight_module, "_safe_reader_call") as read:
                with self.assertRaisesRegex(ValueError, "^INVALID_ACQUISITION_SCOPE$"):
                    self.build_report(**{key: value})
                read.assert_not_called()

    def test_scope_explicit_full_scope_preserves_success(self):
        baseline = self.build_report()
        explicit = self.build_report(account_operations=list(ACCOUNT_READ_OPERATIONS),
                                     market_operations=["oauth_health", "market_quote", "daily_chart"])
        explicit["broker_observed_state"].pop("acquisition_scope")
        self.assertEqual(baseline, explicit)

    def test_scope_parent_failure_time_is_not_broker_time_or_success(self):
        failure, capture = self.captured_failure()
        before = dict(failure)
        report = self.report_with_failure(failure, [capture])
        self.assertEqual(report["decision_as_of"], ACCOUNT_RETRIEVED_AT)
        self.assertEqual(report["broker_snapshot_as_of"], OBSERVED_AT)
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertNotIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
        self.assertEqual(report["finalized_bar_preflight_status"], "PASS")
        state = report["broker_observed_state"]
        self.assertEqual(state["open_order_evidence"]["failure_type"], "API_RESPONSE_ERROR")
        self.assertIsNone(state["open_order_evidence"]["retrieved_at"])
        self.assertFalse(state["scope_complete"])
        binding = state["acquisition_scope"]["parent_failure_timing"][0]
        self.assertEqual(binding["source_sha256"], capture[1])
        self.assertEqual(binding["run_id"], "manual-test-run-0001")
        self.assertEqual(binding["timestamp_role"], "FAILURE_OBSERVATION_ONLY")
        self.assertEqual(before, failure)
        self.assertNotIn("SYNTHETIC_NOT_FOR_OUTPUT", json.dumps(report))
        self.assertFalse(report["order_authority"])
        self.assertEqual(report["quantity_authority"], "none")
        self.assertIsNone(report["execution_quantity"])
        self.assertEqual(validate_instance(report, SCHEMA), [])

    def test_scope_bound_failure_and_limited_daily_path(self):
        failure, capture = self.captured_failure()
        report = self.report_with_failure(failure, [capture],
            account_operations=["account_holdings_read", "account_deposit_read", "account_open_items"],
            market_operations=["daily_chart"])
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["hard_fail_reasons"], [])
        self.assertEqual(report["finalized_bar_preflight_status"], "PASS")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")

    def test_scope_error_with_own_timestamp_stays_unverified(self):
        failure, _ = self.captured_failure(retrieved_at=OBSERVED_AT)
        report = self.report_with_failure(failure)
        self.assertEqual(report["preflight_status"], "PARTIAL")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertIn("ACCOUNT_EVIDENCE_NOT_VERIFIED:account_open_items", report["partial_reasons"])

    def test_scope_missing_capture_or_worker_assertion_cannot_fill_failure_time(self):
        failure, _ = self.captured_failure()
        for metadata in ({}, {"parent_observed_at": ACCOUNT_RETRIEVED_AT, "source_sha256": "a" * 64}):
            with self.subTest(metadata=metadata):
                report = self.report_with_failure({**failure, **metadata})
                self.assertIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
                self.assertEqual(report["evidence_grade"], "UNVERIFIED")

    def test_scope_invalid_capture_blocks_before_readers_with_safe_diagnostic(self):
        _, good = self.captured_failure()
        invalid = [(good[0], "0" * 64), (b"invalid", hashlib.sha256(b"invalid").hexdigest())]
        for kwargs in ({"run_id": "SYNTHETIC_SECRET"}, {"observed_at": ROLLOVER_RETRIEVED_AT},
                       {"started_at": HISTORY_RETRIEVED_AT}, {"observed_at": "invalid"},
                       {"observed_at": "2026-08-21T22:00:02"},
                       {"mutate": lambda d: d.update(RUN_ID="SYNTHETIC_SECRET")},
                       {"mutate": lambda d: d.update(results=[])},
                       {"mutate": lambda d: d.update(safe_bridge_results=[])}):
            invalid.append(self.captured_failure(**kwargs)[1])
        for capture in invalid:
            with self.subTest(hash=capture[1]), patch.object(manual_preflight_module, "_safe_reader_call") as read:
                with self.assertRaisesRegex(ValueError, "^PARENT_CAPTURE_BINDING_INVALID$"):
                    self.build_report(parent_capture_artifacts=[capture], observed_at=POST_CUTOFF_RETRIEVED_AT)
                read.assert_not_called()

    def test_scope_capture_must_match_exact_operation_ticker_and_response(self):
        failure, _ = self.captured_failure()
        variants = [self.captured_failure(operation="account_fills_read")[1],
                    self.captured_failure(mutate=lambda d: d["safe_bridge_results"][0].update(ticker="WRONG"))[1],
                    self.captured_failure(mutate=lambda d: d["safe_bridge_results"][0].update(failure_type="EMPTY_RESPONSE"))[1]]
        for other in variants:
            with self.subTest(hash=other[1]):
                report = self.report_with_failure(failure, [other])
                self.assertIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
                self.assertEqual(report["broker_observed_state"]["acquisition_scope"]["parent_failure_timing"], [])

    def test_scope_duplicate_or_ambiguous_capture_is_rejected(self):
        failure, capture = self.captured_failure()
        with self.assertRaisesRegex(ValueError, "^PARENT_CAPTURE_BINDING_INVALID$"):
            self.report_with_failure(failure, [capture, capture])
        _, second = self.captured_failure(observed_at=HEALTH_RETRIEVED_AT)
        with self.assertRaisesRegex(ValueError, "^PARENT_CAPTURE_BINDING_AMBIGUOUS$"):
            self.report_with_failure(failure, [capture, second])

    def test_scope_parent_time_does_not_repair_success_or_malformed_timestamp(self):
        for status, timestamp in (("PASS", None), ("PARTIAL", None),
                                  ("KIWOOM_API_RESPONSE_ERROR", "invalid")):
            with self.subTest(status=status, timestamp=timestamp):
                failure, capture = self.captured_failure(retrieved_at=timestamp,
                    mutate=lambda d: d["safe_bridge_results"][0].update(bridge_status=status))
                report = self.report_with_failure(failure, [capture])
                self.assertIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
                self.assertEqual(report["evidence_grade"], "UNVERIFIED")

    def test_scope_stale_replay_is_not_freshened(self):
        failure, capture = self.captured_failure()
        report = self.report_with_failure(failure, [capture], observed_at="2026-08-21T22:20:00+00:00")
        self.assertEqual(report["decision_as_of"], ACCOUNT_RETRIEVED_AT)
        self.assertIn("PARENT_CAPTURE_REPLAY_STALE", report["hard_fail_reasons"])
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")

    def test_scope_future_success_cannot_hide_behind_valid_failure_capture(self):
        failure, capture = self.captured_failure()
        report = self.report_with_failure(failure, [capture],
            market_retrieved_at_by_operation={"market_quote": ROLLOVER_RETRIEVED_AT})
        self.assertIn("PARENT_CAPTURE_REPLAY_FUTURE", report["hard_fail_reasons"])
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")

    def test_scope_existing_uppercase_parent_artifact_is_supported(self):
        failure, capture = self.captured_failure(uppercase=True)
        report = self.report_with_failure(failure, [capture])
        self.assertNotIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
        self.assertEqual(report["decision_as_of"], ACCOUNT_RETRIEVED_AT)

    def test_01_same_day_usa06012_is_current_candidate_not_finalized(self):
        same_day = kiwoom_daily_observation(
            ticker="AAA",
            reported_session=SAME_DAY,
            close=101.0,
            provider_timestamp=OBSERVED_AT,
        )
        selected = _select_last_verified_finalized_bar(
            [same_day],
            observed_at=OBSERVED_AT,
            expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        spoofed = {
            **same_day,
            "market_session_type": "REGULAR_COMPLETED",
            "price_basis": "RAW_REGULAR_SESSION_CLOSE",
            "quote_type": "REGULAR_SESSION_LAST",
            "session_classification_basis": "NEXT_ET_CALENDAR_DAY_PROVIDER_ARCHIVE",
            "bar_finalized": True,
            "stable": True,
            "comparable_to_regular_close": True,
            "daily_indicator_authority": True,
            "hard_risk_authority": True,
        }
        spoofed_selected = _select_last_verified_finalized_bar(
            [spoofed], observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session=SAME_DAY,
        )
        self.assertEqual("BROKER_MARK", same_day["quote_type"])
        self.assertFalse(same_day["bar_finalized"])
        self.assertFalse(same_day["daily_indicator_authority"])
        self.assertEqual("NOT_VERIFIED", selected["status"])
        self.assertFalse(selected["technical_authority"])
        self.assertEqual("NOT_VERIFIED", spoofed_selected["status"])
        self.assertFalse(spoofed_selected["technical_authority"])

        report = self.build_report(
            quote_missing={"AAA"},
            include_same_day={"AAA"},
            include_previous=set(),
        )
        current = report["current_price_evidence"][0]
        finalized = report["last_verified_finalized_bars"][0]
        self.assertEqual("AVAILABLE", current["status"])
        self.assertEqual("usa06012:/api/us/chart", current["record"]["source_identifier"])
        self.assertEqual("NOT_VERIFIED", finalized["status"])
        self.assertFalse(finalized["technical_authority"])

    def test_02_previous_verified_bar_is_selected(self):
        same_day = kiwoom_daily_observation(
            ticker="AAA", reported_session=SAME_DAY, close=101.0,
            provider_timestamp=OBSERVED_AT,
        )
        previous = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        selected = _select_last_verified_finalized_bar(
            [previous, same_day], observed_at=OBSERVED_AT,
            expected_ticker="AAA", expected_completed_session=PREVIOUS_DAY,
        )
        self.assertEqual("VERIFIED", selected["status"])
        self.assertEqual(PREVIOUS_DAY, selected["bar_date"])
        self.assertTrue(selected["technical_authority"])
        self.assertTrue(selected["bar"]["bar_finalized"])

    def test_02a_stale_archived_row_is_not_verified(self):
        stale = kiwoom_daily_observation(
            ticker="AAA", reported_session="2020-01-02", close=50.0,
            provider_timestamp=OBSERVED_AT,
        )
        selected = _select_last_verified_finalized_bar(
            [stale], observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        self.assertEqual("NOT_VERIFIED", selected["status"])

    def test_02b_wrong_or_missing_ticker_is_not_verified(self):
        valid = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        wrong = {**valid, "ticker": "BBB"}
        missing = dict(valid)
        missing.pop("ticker")
        for candidate in (wrong, missing):
            selected = _select_last_verified_finalized_bar(
                [candidate], observed_at=OBSERVED_AT, expected_ticker="AAA",
                expected_completed_session=PREVIOUS_DAY,
            )
            self.assertEqual("NOT_VERIFIED", selected["status"])

    def test_02c_wrong_expected_or_reported_session_is_not_verified(self):
        valid = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        wrong_expected = _select_last_verified_finalized_bar(
            [valid], observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session="2026-08-19",
        )
        wrong_reported = _select_last_verified_finalized_bar(
            [{**valid, "reported_session": "2026-08-19"}],
            observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        self.assertEqual("NOT_VERIFIED", wrong_expected["status"])
        self.assertEqual("NOT_VERIFIED", wrong_reported["status"])

    def test_02d_cross_field_session_mismatch_is_not_verified(self):
        candidate = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        candidate["exchange_timestamp"] = "2026-08-21T16:00:00-04:00"
        selected = _select_last_verified_finalized_bar(
            [candidate], observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        self.assertEqual("NOT_VERIFIED", selected["status"])

    def test_02e_malformed_timestamp_and_missing_authority_are_not_verified(self):
        valid = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        malformed = {**valid, "provider_timestamp": "not-a-timestamp"}
        missing = dict(valid)
        missing.pop("daily_indicator_authority")
        for candidate in (malformed, missing):
            selected = _select_last_verified_finalized_bar(
                [candidate], observed_at=OBSERVED_AT, expected_ticker="AAA",
                expected_completed_session=PREVIOUS_DAY,
            )
            self.assertEqual("NOT_VERIFIED", selected["status"])

    def test_02f_future_session_is_not_verified(self):
        future = kiwoom_daily_observation(
            ticker="AAA", reported_session="2026-08-22", close=99.0,
            provider_timestamp="2026-08-23T22:00:00+00:00",
        )
        selected = _select_last_verified_finalized_bar(
            [future], observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session="2026-08-22",
        )
        self.assertEqual("NOT_VERIFIED", selected["status"])

    def test_02g_self_asserted_session_evidence_cannot_create_authority(self):
        stale = kiwoom_daily_observation(
            ticker="AAA", reported_session="2020-01-02", close=50.0,
            provider_timestamp=OBSERVED_AT,
        )
        recent = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        for session, candidate in (("2020-01-02", stale), (PREVIOUS_DAY, recent)):
            forged = {
                "expected_us_session_date": session,
                "us_session_date": session,
                "regular_session_complete": True,
                "is_trading_day": True,
                "is_early_close": False,
                "official_calendar_verified": True,
                "calendar_verification_status": "verified_trading_day",
                "calendar_source_type": "official_exchange_or_regulator",
                "calendar_source": "https://attacker.example/fake-calendar",
                "calendar_verified_at_utc": OBSERVED_AT,
            }
            selected = select_last_verified_finalized_bar(
                [candidate], observed_at=OBSERVED_AT, expected_ticker="AAA",
                official_session_evidence=forged,
            )
            self.assertEqual("NOT_VERIFIED", selected["status"])
            self.assertEqual("LEGACY_SESSION_AUTHORITY_DISABLED", selected["reason"])

    def test_02h_production_preflight_uses_session_authority(self):
        self.assertNotIn(
            "official_session_evidence",
            inspect.signature(run_manual_preflight).parameters,
        )
        with patch.object(
            manual_preflight_module,
            "_select_last_verified_finalized_bar",
            wraps=manual_preflight_module._select_last_verified_finalized_bar,
        ) as selector:
            report = self.build_report()
        self.assertEqual(2, self.authority_mock.call_count)
        self.assertEqual(1, selector.call_count)
        self.assertEqual("MATCHED", report["integrated_authority_cohort_status"])
        self.assertEqual("VERIFIED", report["last_verified_finalized_bar_status"])
        self.assertEqual("PASS", report["finalized_bar_preflight_status"])

    def test_02h1_identity_failure_prevents_session_and_selector_calls(self):
        for reason in ("ARTIFACT_NOT_ACTIVATED", "UNKNOWN_SYMBOL"):
            with self.subTest(reason=reason):
                self.identity_forced_reason = reason
                self.identity_mock.reset_mock()
                self.authority_mock.reset_mock()
                requests = []
                with patch.object(
                    manual_preflight_module, "_select_last_verified_finalized_bar"
                ) as selector:
                    report = self.build_report(market_request_log=requests)
                self.assertEqual(2, self.identity_mock.call_count)
                self.authority_mock.assert_not_called()
                selector.assert_not_called()
                self.assertFalse(any(item["operation"] == "daily_chart" for item in requests))
                self.assertEqual("NOT_VERIFIED", report["identity_authority_status"])
                self.assertEqual([reason], report["identity_authority_reasons"])
                self.assertEqual(
                    "UPSTREAM_IDENTITY_NOT_VERIFIED",
                    report["last_verified_finalized_bars"][0]["session_authority_reason"],
                )

    def test_02h2_verified_identity_forwards_exact_operating_mic_only(self):
        for mic in ("XNYS", "XNAS", "XCBO"):
            with self.subTest(mic=mic):
                self.identity_operating_mics = {"AAA": mic}
                self.identity_mock.reset_mock()
                self.authority_mock.reset_mock()
                report = self.build_report(identity_operating_mics={"AAA": mic})
                self.assertEqual(
                    mic,
                    self.authority_mock.call_args.kwargs["primary_listing_operating_mic"],
                )
                row = report["last_verified_finalized_bars"][0]
                self.assertEqual(mic, row["primary_listing_operating_mic"])
                self.assertEqual("XNGS", row["primary_listing_segment_mic"])

    def test_02h3_identity_session_cohort_mismatch_blocks_selector(self):
        self.identity_cohort = "different-identity-cohort"
        requests = []
        with patch.object(
            manual_preflight_module, "_select_last_verified_finalized_bar"
        ) as selector:
            report = self.build_report(market_request_log=requests)
        self.assertEqual(2, self.authority_mock.call_count)
        selector.assert_not_called()
        self.assertEqual("NOT_VERIFIED", report["integrated_authority_cohort_status"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertFalse(any(item["operation"] == "daily_chart" for item in requests))

    def test_02h4_empty_identity_cohort_blocks_selector(self):
        self.identity_cohort = ""
        requests = []
        with patch.object(
            manual_preflight_module, "_select_last_verified_finalized_bar"
        ) as selector:
            report = self.build_report(market_request_log=requests)
        selector.assert_not_called()
        self.assertEqual("NOT_VERIFIED", report["integrated_authority_cohort_status"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertFalse(any(item["operation"] == "daily_chart" for item in requests))

    def test_02h5_empty_session_cohort_blocks_selector(self):
        self.session_cohort = ""
        requests = []
        with patch.object(
            manual_preflight_module, "_select_last_verified_finalized_bar"
        ) as selector:
            report = self.build_report(market_request_log=requests)
        selector.assert_not_called()
        self.assertEqual("NOT_VERIFIED", report["integrated_authority_cohort_status"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertFalse(any(item["operation"] == "daily_chart" for item in requests))

    def test_02h6_both_empty_cohorts_block_selector(self):
        self.identity_cohort = ""
        self.session_cohort = ""
        requests = []
        with patch.object(
            manual_preflight_module, "_select_last_verified_finalized_bar"
        ) as selector:
            report = self.build_report(market_request_log=requests)
        selector.assert_not_called()
        self.assertEqual("NOT_VERIFIED", report["integrated_authority_cohort_status"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertFalse(any(item["operation"] == "daily_chart" for item in requests))

    def test_02i_mutable_market_context_cannot_affect_session_authority(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("CANONICAL_MARKET_CONTEXT_PATH", source)
        self.assertNotIn("market_context.current.json", source)
        with tempfile.TemporaryDirectory() as directory:
            mutable = Path(directory) / "market_context.current.json"
            mutable.write_text('{"expected_completed_session":"1900-01-01"}', encoding="utf-8")
            first = self.build_report()
            mutable.write_text('{"expected_completed_session":"2099-12-31"}', encoding="utf-8")
            second = self.build_report()
        self.assertEqual(PREVIOUS_DAY, first["expected_completed_us_session"])
        self.assertEqual(first["expected_completed_us_session"], second["expected_completed_us_session"])
        self.assertEqual(first["calendar_hash"], second["calendar_hash"])

    def test_02j_verify_market_session_fake_success_creates_no_authority(self):
        self.authority_forced_reason = "ARTIFACT_NOT_ACTIVATED"
        with patch.object(
            manual_preflight_module,
            "verify_market_session",
            return_value={"session": {"official_calendar_verified": True}},
            create=True,
        ) as legacy_verifier, patch.object(
            manual_preflight_module,
            "_select_last_verified_finalized_bar",
            wraps=manual_preflight_module._select_last_verified_finalized_bar,
        ) as selector:
            report = self.build_report()
        legacy_verifier.assert_not_called()
        selector.assert_not_called()
        self.assertEqual("NOT_VERIFIED", report["session_authority_status"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])

    def test_02k_caller_completed_session_is_disabled(self):
        candidate = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        selected = select_last_verified_finalized_bar(
            [candidate],
            observed_at=OBSERVED_AT,
            expected_ticker="AAA",
            completed_session=PREVIOUS_DAY,
        )
        self.assertEqual("NOT_VERIFIED", selected["status"])
        self.assertEqual("LEGACY_SESSION_AUTHORITY_DISABLED", selected["reason"])

    def test_02l_not_verified_authority_never_calls_selector(self):
        self.authority_forced_reason = "INTEGRITY_FAILURE"
        with patch.object(
            manual_preflight_module,
            "_select_last_verified_finalized_bar",
            side_effect=AssertionError("selector must not be called"),
        ) as selector:
            report = self.build_report()
        selector.assert_not_called()
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertEqual("INTEGRITY_FAILURE", report["last_verified_finalized_bars"][0]["reason"])

    def test_02m_verified_authority_passes_exact_expected_session_to_selector(self):
        requests = []
        with patch.object(
            manual_preflight_module,
            "_select_last_verified_finalized_bar",
            wraps=manual_preflight_module._select_last_verified_finalized_bar,
        ) as selector:
            report = self.build_report(
                expected_completed_session=PREVIOUS_DAY,
                market_request_log=requests,
            )
        self.assertEqual(PREVIOUS_DAY, selector.call_args.kwargs["expected_completed_session"])
        self.assertEqual(PREVIOUS_DAY, report["expected_completed_us_session"])
        daily = [request for request in requests if request["operation"] == "daily_chart"]
        self.assertEqual([PREVIOUS_DAY], [request["completed_session"] for request in daily])

    def test_02n_synthetic_fixture_authority_reaches_m1_selector_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture_root = Path(directory)
            write_independent_m1_calendar_fixture(fixture_root)

            def fixture_resolver(
                observed_at, *, primary_listing_operating_mic,
                decision_as_of=None, authority_mode="CURRENT",
            ):
                return _derive_us_market_session_authority_from_root(
                    observed_at,
                    primary_listing_operating_mic=primary_listing_operating_mic,
                    trusted_root=fixture_root,
                    decision_as_of=decision_as_of,
                    authority_mode=authority_mode,
                )

            self.authority_mock.side_effect = fixture_resolver
            report = self.build_report()
        self.assertEqual("VERIFIED", report["session_authority_status"])
        self.assertEqual(PREVIOUS_DAY, report["expected_completed_us_session"])
        self.assertEqual("PASS", report["finalized_bar_preflight_status"])
        self.assertEqual(PREVIOUS_DAY, report["last_verified_finalized_bars"][0]["bar_date"])

    def test_02o_normal_latency_uses_acquisition_complete_cutoff(self):
        requests = []
        report = self.build_report(
            account_retrieved_at=ACCOUNT_RETRIEVED_AT,
            market_retrieved_at_by_operation={
                "oauth_health": HEALTH_RETRIEVED_AT,
                "market_quote": QUOTE_RETRIEVED_AT,
                "daily_chart": HISTORY_RETRIEVED_AT,
            },
            market_request_log=requests,
        )
        self.assertEqual(HISTORY_RETRIEVED_AT, report["decision_as_of"])
        self.assertNotIn("TEMPORAL_EVIDENCE_VIOLATION", report["hard_fail_reasons"])
        self.assertNotIn("ACQUISITION_SESSION_ROLLOVER", report["hard_fail_reasons"])
        self.assertEqual("PASS", report["preflight_status"])
        self.assertEqual("PASS", report["finalized_bar_preflight_status"])
        self.assertEqual("GRADE_B", report["evidence_grade"])
        self.assertEqual(
            [OBSERVED_AT, HISTORY_RETRIEVED_AT],
            [call.kwargs["decision_as_of"] for call in self.identity_mock.call_args_list],
        )
        self.assertEqual(
            [OBSERVED_AT, HISTORY_RETRIEVED_AT],
            [call.args[0] for call in self.authority_mock.call_args_list],
        )
        daily = [request for request in requests if request["operation"] == "daily_chart"]
        self.assertEqual([PREVIOUS_DAY], [request["completed_session"] for request in daily])

    def test_02p_old_preacquisition_cutoff_would_reject_same_evidence(self):
        account_results = [{"retrieved_at": ACCOUNT_RETRIEVED_AT}]
        market_results = [
            {"retrieved_at": HEALTH_RETRIEVED_AT},
            {"retrieved_at": QUOTE_RETRIEVED_AT},
            {"retrieved_at": HISTORY_RETRIEVED_AT},
        ]
        cutoff = _acquisition_complete_cutoff(account_results, market_results)
        self.assertEqual(HISTORY_RETRIEVED_AT, cutoff)
        self.assertFalse(_temporal_evidence_valid(OBSERVED_AT, account_results, market_results))
        self.assertTrue(_temporal_evidence_valid(cutoff, account_results, market_results))

    def test_02q_frozen_cutoff_rejects_later_evidence(self):
        account_results = [{"retrieved_at": ACCOUNT_RETRIEVED_AT}]
        market_results = [{"retrieved_at": HISTORY_RETRIEVED_AT}]
        cutoff = _acquisition_complete_cutoff(account_results, market_results)
        self.assertEqual(HISTORY_RETRIEVED_AT, cutoff)
        market_results.append({"retrieved_at": POST_CUTOFF_RETRIEVED_AT})
        self.assertFalse(_temporal_evidence_valid(cutoff, account_results, market_results))

    def test_02r_missing_or_invalid_required_retrieved_at_fails_closed(self):
        for retrieved_at in (None, "not-a-timestamp"):
            with self.subTest(retrieved_at=retrieved_at):
                report = self.build_report(account_retrieved_at=retrieved_at)
                self.assertEqual(OBSERVED_AT, report["decision_as_of"])
                self.assertIn("ACQUISITION_TIMESTAMP_INVALID", report["hard_fail_reasons"])
                self.assertIn("TEMPORAL_EVIDENCE_VIOLATION", report["hard_fail_reasons"])
                self.assertEqual("FAIL", report["preflight_status"])
                self.assertEqual("UNVERIFIED", report["evidence_grade"])

    def test_02s_finalized_selector_uses_same_latency_boundary(self):
        candidate = kiwoom_daily_observation(
            ticker="AAA",
            reported_session=PREVIOUS_DAY,
            close=99.0,
            provider_timestamp=HISTORY_RETRIEVED_AT,
        )
        accepted = _select_last_verified_finalized_bar(
            [candidate],
            observed_at=HISTORY_RETRIEVED_AT,
            expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        rejected_by_old_boundary = _select_last_verified_finalized_bar(
            [candidate],
            observed_at=OBSERVED_AT,
            expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        self.assertEqual("VERIFIED", accepted["status"])
        self.assertEqual("NOT_VERIFIED", rejected_by_old_boundary["status"])

    def test_02t_et_date_rollover_changes_expected_session_and_fails_closed(self):
        self.authority_expected_session_by_boundary[ROLLOVER_RETRIEVED_AT] = SAME_DAY
        market_calls = []
        report = self.build_report(
            account_retrieved_at=ACCOUNT_RETRIEVED_AT,
            market_retrieved_at_by_operation={
                "oauth_health": ROLLOVER_RETRIEVED_AT,
                "market_quote": ROLLOVER_RETRIEVED_AT,
                "daily_chart": ROLLOVER_RETRIEVED_AT,
            },
            market_call_log=market_calls,
        )
        self.assertEqual(ROLLOVER_RETRIEVED_AT, report["decision_as_of"])
        self.assertEqual(SAME_DAY, report["expected_completed_us_session"])
        self.assertIn("ACQUISITION_SESSION_ROLLOVER", report["hard_fail_reasons"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertEqual(1, len(market_calls))
        daily = [request for request in market_calls[0] if request["operation"] == "daily_chart"]
        self.assertEqual([PREVIOUS_DAY], [request["completed_session"] for request in daily])

    def test_02u_calendar_session_identity_change_same_et_date_fails_closed(self):
        self.authority_expected_session_by_boundary[HISTORY_RETRIEVED_AT] = "2026-08-19"
        report = self.build_report(
            account_retrieved_at=ACCOUNT_RETRIEVED_AT,
            market_retrieved_at_by_operation={
                "oauth_health": HEALTH_RETRIEVED_AT,
                "market_quote": QUOTE_RETRIEVED_AT,
                "daily_chart": HISTORY_RETRIEVED_AT,
            },
        )
        self.assertEqual(SAME_DAY, report["trading_date"])
        self.assertEqual("2026-08-19", report["expected_completed_us_session"])
        self.assertIn("ACQUISITION_SESSION_ROLLOVER", report["hard_fail_reasons"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])

    def test_02v_temporal_and_finalized_gates_are_independent(self):
        finalized = kiwoom_daily_observation(
            ticker="AAA", reported_session=PREVIOUS_DAY, close=99.0,
            provider_timestamp=OBSERVED_AT,
        )
        finalized_pass = _select_last_verified_finalized_bar(
            [finalized], observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        self.assertEqual("VERIFIED", finalized_pass["status"])
        self.assertFalse(_temporal_evidence_valid(
            OBSERVED_AT, [{"retrieved_at": POST_CUTOFF_RETRIEVED_AT}],
        ))

        wrong_session = kiwoom_daily_observation(
            ticker="AAA", reported_session="2026-08-19", close=98.0,
            provider_timestamp=OBSERVED_AT,
        )
        finalized_fail = _select_last_verified_finalized_bar(
            [wrong_session], observed_at=OBSERVED_AT, expected_ticker="AAA",
            expected_completed_session=PREVIOUS_DAY,
        )
        self.assertTrue(_temporal_evidence_valid(
            OBSERVED_AT, [{"retrieved_at": OBSERVED_AT}],
        ))
        self.assertEqual("NOT_VERIFIED", finalized_fail["status"])

    def test_03_broker_system_divergence_is_ephemeral_and_canonical_unchanged(self):
        canonical = ROOT / "stock-strategy-system/portfolio_state.json"
        before = canonical.read_bytes()
        report = self.build_report(
            portfolio=system_portfolio({"AAA": 1.0}, {"AAA": 80.0}),
            broker_holdings={"AAA": 2.0},
            broker_costs={"AAA": 70.0},
        )
        self.assertEqual("DIFFERENT", report["broker_diff_status"])
        self.assertEqual(2.0, report["manual_analysis_view"]["holdings"]["AAA"])
        self.assertTrue(report["manual_analysis_view"]["ephemeral"])
        self.assertTrue(report["manual_analysis_view"]["memory_only"])
        self.assertEqual(before, canonical.read_bytes())

    def test_current_broker_missing_cost_is_not_filled_from_internal_history(self):
        report = self.build_report(broker_costs={})
        self.assertEqual(report["manual_analysis_view"]["holding_source"], "BROKER_OBSERVED_STATE")
        self.assertEqual(report["manual_analysis_view"]["holdings"]["AAA"], 1.0)
        self.assertIsNone(report["manual_analysis_view"]["average_cost_usd"]["AAA"])
        self.assertEqual(report["system_portfolio_state"]["average_cost_usd"]["AAA"], 80.0)
        self.assertFalse(report["manual_analysis_view"]["portfolio_mutation"])

    def test_invalid_broker_keeps_history_diagnostic_not_current_evidence(self):
        report = self.build_report(holdings_status="KIWOOM_ACCOUNT_UNAVAILABLE", orderable_cash=None)
        self.assertEqual(report["manual_analysis_view"]["holding_source"], "SYSTEM_PORTFOLIO_STATE_FALLBACK")
        self.assertEqual(report["broker_observed_state"]["status"], "UNAVAILABLE")
        self.assertEqual(report["evidence_grade"], "UNVERIFIED")
        self.assertFalse(report["provenance"]["decision_quality_eligible"])
        self.assertIsNone(report["verified_orderable_cash_usd"])
        self.assertIsNone(report["manual_analysis_view"]["verified_orderable_cash_usd"])
        self.assertFalse(report["order_authority"])

    def test_04_writer_order_and_mutation_sentinels_are_never_called(self):
        calls = []

        def fail(name):
            def sentinel(*args, **kwargs):
                calls.append(name)
                raise AssertionError(f"forbidden capability called: {name}")
            return sentinel

        with patch("pathlib.Path.write_text", side_effect=fail("file_writer")), \
             patch("os.replace", side_effect=fail("atomic_overwrite")):
            report = self.build_report()
        self.assertEqual([], calls)
        self.assertEqual("REPORT_ONLY_CREATE_ONLY", report["mutation_status"])
        self.assertFalse(report["order_authority"])
        self.assertEqual("none", report["quantity_authority"])
        self.assertIsNone(report["execution_quantity"])

    def test_05_protected_state_hashes_are_unchanged(self):
        candidates = [
            ROOT / "stock-strategy-system/portfolio_state.json",
            ROOT / "stock-strategy-system/alert_policy.json",
            ROOT / "stock-strategy-system/alert_runtime_state.json",
            ROOT / "workspace/state/automation_delivery_runtime.json",
            ROOT / "workspace/state/integrated_shadow/shadow_progress.json",
            ROOT / "workspace/state/portfolio_decision_cohort.json",
            ROOT / "workspace/state/strategy_evolution/strategy_evolution_cohort.json",
            ROOT / "workspace/state/continuous_improvement/improvement_analytics_cohort.json",
        ]
        protected = [path for path in candidates if path.is_file()]
        self.assertGreaterEqual(len(protected), 3)
        before = {str(path): sha256(path) for path in protected}
        canonical = json.loads((ROOT / "stock-strategy-system/portfolio_state.json").read_text(encoding="utf-8"))
        holdings = dict(canonical.get("holdings") or {})
        costs = dict(canonical.get("average_cost_usd") or {})
        cash = float(canonical.get("available_cash_usd") or 0.0)
        report = run_manual_preflight(
            manual_run_id="manual-protected-state-test",
            system_portfolio=canonical,
            system_portfolio_source="stock-strategy-system/portfolio_state.json",
            system_portfolio_sha256=before[str(ROOT / "stock-strategy-system/portfolio_state.json")],
            provenance_policy=self.provenance_policy,
            account_reader=account_reader_for(holdings, costs, orderable_cash=cash),
            market_reader=market_reader_for(sorted(holdings)),
            maximum_broker_age_seconds=900,
            decision_as_of=OBSERVED_AT,
            observed_at=OBSERVED_AT,
        )
        with tempfile.TemporaryDirectory() as directory:
            trusted = Path(directory)
            _write_immutable_report(
                report, output_root=trusted / "approved", schema_path=SCHEMA,
                trusted_root=trusted,
            )
        after = {str(path): sha256(path) for path in protected}
        self.assertEqual(before, after)

    def test_06_report_write_is_create_only_and_never_overwrites(self):
        report = self.build_report(manual_run_id="manual-immutable-test")
        with tempfile.TemporaryDirectory() as directory:
            trusted = Path(directory)
            root = trusted / "approved"
            target = _write_immutable_report(
                report, output_root=root, schema_path=SCHEMA, trusted_root=trusted,
            )
            first = target.read_bytes()
            with self.assertRaises(FileExistsError):
                _write_immutable_report(
                    report, output_root=root, schema_path=SCHEMA, trusted_root=trusted,
                )
            self.assertEqual(first, target.read_bytes())
            self.assertEqual(1, len(list(root.rglob("manual-portfolio-analysis.json"))))

    def test_06a_namespace_and_parent_reparse_points_fail_closed(self):
        report = self.build_report(manual_run_id="manual-reparse-test-0001")
        with tempfile.TemporaryDirectory() as directory:
            trusted = Path(directory)
            outside = trusted / "outside"
            outside.mkdir()
            namespace = trusted / "approved"
            create_directory_reparse(namespace, outside)
            try:
                with self.assertRaises((OSError, ValueError)):
                    _write_immutable_report(
                        report, output_root=namespace, schema_path=SCHEMA,
                        trusted_root=trusted,
                    )
                self.assertFalse((outside / report["manual_run_id"]).exists())
            finally:
                remove_directory_reparse(namespace)

            parent = trusted / "parent-link"
            create_directory_reparse(parent, outside)
            try:
                with self.assertRaises((OSError, ValueError)):
                    _write_immutable_report(
                        report, output_root=parent / "approved", schema_path=SCHEMA,
                        trusted_root=trusted,
                    )
                self.assertFalse((outside / "approved").exists())
            finally:
                remove_directory_reparse(parent)

    def test_06b_existing_run_directory_reparse_fails_closed(self):
        report = self.build_report(manual_run_id="manual-reparse-test-0002")
        with tempfile.TemporaryDirectory() as directory:
            trusted = Path(directory)
            output = trusted / "approved"
            outside = trusted / "outside"
            output.mkdir()
            outside.mkdir()
            run_link = output / report["manual_run_id"]
            create_directory_reparse(run_link, outside)
            try:
                with self.assertRaises(FileExistsError):
                    _write_immutable_report(
                        report, output_root=output, schema_path=SCHEMA,
                        trusted_root=trusted,
                    )
                self.assertFalse((outside / "manual-portfolio-analysis.json").exists())
            finally:
                remove_directory_reparse(run_link)

    @unittest.skipUnless(os.name == "nt", "Windows junction race regression")
    def test_06c_toctou_junction_swap_fails_closed(self):
        report = self.build_report(manual_run_id="manual-reparse-test-0003")
        with tempfile.TemporaryDirectory() as directory:
            trusted = Path(directory)
            output = trusted / "approved"
            outside = trusted / "outside"
            outside.mkdir()
            original_open = Path.open
            attack_attempted = False

            def racing_open(path, *args, **kwargs):
                nonlocal attack_attempted
                if path.name == "manual-portfolio-analysis.json" and not attack_attempted:
                    attack_attempted = True
                    os.rmdir(path.parent)
                    create_directory_reparse(path.parent, outside)
                return original_open(path, *args, **kwargs)

            with patch("pathlib.Path.open", new=racing_open):
                with self.assertRaises(OSError):
                    _write_immutable_report(
                        report, output_root=output, schema_path=SCHEMA,
                        trusted_root=trusted,
                    )
            self.assertTrue(attack_attempted)
            self.assertFalse((outside / "manual-portfolio-analysis.json").exists())

    def test_07a_kiwoom_unavailable_is_fail(self):
        report = self.build_report(health=False)
        self.assertEqual("FAIL", report["preflight_status"])
        self.assertIn("KIWOOM_UNAVAILABLE", report["hard_fail_reasons"])
        self.assertEqual("FAILED", report["manual_data_verification_status"])
        self.assertEqual("UNVERIFIED", report["evidence_grade"])
        self.assertEqual("UNVERIFIED", report["provenance"]["evidence_grade"])
        self.assertFalse(report["provenance"]["decision_quality_eligible"])

    def test_07b_broker_holdings_unavailable_is_fail(self):
        report = self.build_report(holdings_status="KIWOOM_ACCOUNT_UNAVAILABLE")
        self.assertEqual("FAIL", report["preflight_status"])
        self.assertIn("BROKER_HOLDINGS_UNAVAILABLE", report["hard_fail_reasons"])
        self.assertEqual("UNVERIFIED", report["evidence_grade"])
        fallback = report["manual_analysis_view"]
        self.assertEqual("SYSTEM_PORTFOLIO_STATE_FALLBACK", fallback["holding_source"])
        self.assertTrue(fallback["ephemeral"])
        self.assertTrue(fallback["memory_only"])
        self.assertFalse(fallback["portfolio_mutation"])
        self.assertFalse(fallback["order_authority"])
        self.assertEqual("none", fallback["quantity_authority"])
        self.assertIsNone(fallback["execution_quantity"])

    def test_07b2_broker_holdings_incomplete_is_fail(self):
        report = self.build_report(holdings_status="PARTIAL", holdings_complete=False)
        self.assertEqual("FAIL", report["preflight_status"])
        self.assertIn("BROKER_HOLDINGS_INCOMPLETE", report["hard_fail_reasons"])

    def test_07c_orderable_cash_unavailable_is_partial(self):
        report = self.build_report(orderable_cash=None)
        self.assertEqual("PARTIAL", report["preflight_status"])
        self.assertIn("ORDERABLE_CASH_NOT_VERIFIED", report["partial_reasons"])
        self.assertEqual("NOT_VERIFIED", report["orderable_cash_status"])
        self.assertIsNone(report["manual_analysis_view"]["verified_orderable_cash_usd"])
        self.assertEqual("UNVERIFIED", report["evidence_grade"])

    def test_07d_some_current_prices_unavailable_is_partial(self):
        portfolio = system_portfolio(
            {"AAA": 1.0, "BBB": 2.0},
            {"AAA": 80.0, "BBB": 90.0},
        )
        report = self.build_report(
            portfolio=portfolio,
            quote_missing={"BBB"},
            include_same_day={"AAA"},
            include_previous={"AAA", "BBB"},
        )
        self.assertEqual("PARTIAL", report["current_price_status"])
        self.assertEqual("PARTIAL", report["preflight_status"])
        self.assertIn("CURRENT_PRICE_UNAVAILABLE:BBB", report["partial_reasons"])

    def test_07e_current_session_finalization_unavailable_is_visible_unknown(self):
        report = self.build_report()
        self.assertEqual("VERIFIED_REAL_DATA", report["manual_data_verification_status"])
        self.assertEqual("NOT_VERIFIED", report["current_session_finalization_status"])
        self.assertEqual("VERIFIED", report["last_verified_finalized_bar_status"])
        self.assertEqual("PASS", report["preflight_status"])
        self.assertNotIn("CURRENT_SESSION_FINALIZATION_NOT_VERIFIED", report["partial_reasons"])
        self.assertIn("CURRENT_SESSION_FINALIZATION_NOT_VERIFIED", report["unknowns"])
        self.assertEqual(PREVIOUS_DAY, report["last_verified_finalized_bar_date"])
        self.assertEqual("GRADE_B", report["evidence_grade"])

    def test_07e1_generator_partial_preflight_cannot_receive_grade_b(self):
        report = self.build_report(orderable_cash=None)
        self.assertEqual("PARTIAL", report["preflight_status"])
        self.assertIn("ORDERABLE_CASH_NOT_VERIFIED", report["partial_reasons"])
        self.assertEqual("UNVERIFIED", report["evidence_grade"])
        self.assertFalse(report["provenance"]["decision_quality_eligible"])

    def test_07e2_finalized_bar_failure_cannot_receive_grade_b(self):
        report = self.build_report(include_previous=set())
        self.assertEqual("AVAILABLE", report["historical_daily_evidence_status"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertEqual("NOT_VERIFIED", report["last_verified_finalized_bar_status"])
        self.assertEqual("NOT_VERIFIED", report["manual_data_verification_status"])
        self.assertEqual("UNVERIFIED", report["evidence_grade"])

    def test_07f_missing_mic_fails_finalized_bar_preflight(self):
        requests = []
        report = self.build_report(identity_operating_mics={}, market_request_log=requests)
        self.assertEqual("NOT_VERIFIED", report["identity_authority_status"])
        self.assertEqual(["PRIMARY_MIC_NOT_VERIFIED"], report["identity_authority_reasons"])
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])
        self.assertEqual(
            "IDENTITY_NOT_VERIFIED:PRIMARY_MIC_NOT_VERIFIED",
            report["last_verified_finalized_bars"][0]["reason"],
        )
        self.assertFalse(any(request["operation"] == "daily_chart" for request in requests))
        self.assertEqual("UNVERIFIED", report["evidence_grade"])

    def test_07g_mixed_ticker_authority_fails_finalized_bar_preflight(self):
        portfolio = system_portfolio(
            {"AAA": 1.0, "BBB": 1.0},
            {"AAA": 80.0, "BBB": 90.0},
        )
        report = self.build_report(
            portfolio=portfolio,
            identity_operating_mics={"AAA": "XNAS", "BBB": "ARCX"},
        )
        statuses = {item["ticker"]: item["session_authority_status"] for item in report["last_verified_finalized_bars"]}
        self.assertEqual({"AAA": "VERIFIED", "BBB": "NOT_VERIFIED"}, statuses)
        self.assertEqual("FAIL", report["finalized_bar_preflight_status"])

    def test_07h_all_authorities_and_selectors_verified_pass_finalized_preflight(self):
        portfolio = system_portfolio(
            {"AAA": 1.0, "BBB": 1.0},
            {"AAA": 80.0, "BBB": 90.0},
        )
        report = self.build_report(portfolio=portfolio)
        self.assertEqual("VERIFIED", report["session_authority_status"])
        self.assertEqual(PREVIOUS_DAY, report["expected_completed_us_session"])
        self.assertEqual("PASS", report["finalized_bar_preflight_status"])
        self.assertEqual("PASS", report["preflight_status"])
        self.assertEqual("VERIFIED", report["identity_authority_status"])
        self.assertEqual("VERIFIED", report["session_authority_status"])
        self.assertEqual("MATCHED", report["integrated_authority_cohort_status"])
        self.assertTrue(all(
            item["bar_date"] == PREVIOUS_DAY
            for item in report["last_verified_finalized_bars"]
        ))

    def test_07i_current_price_and_execution_boundaries_are_unchanged(self):
        report = self.build_report()
        current = report["current_price_evidence"][0]
        self.assertEqual("AVAILABLE", current["status"])
        self.assertEqual("KIWOOM_REST", current["record"]["provider"])
        self.assertFalse(report["order_authority"])
        self.assertEqual("none", report["quantity_authority"])
        self.assertIsNone(report["execution_quantity"])

    def test_07i1_signed_cur_prc_normalizes_to_positive_price(self):
        cases = (
            ("MVLL", "-30.6390", 30.639),
            ("NBIS", "-218.6500", 218.65),
            ("SOXL", "+115.8200", 115.82),
        )
        for ticker, raw_price, expected in cases:
            with self.subTest(ticker=ticker, raw_price=raw_price):
                record = _current_price_record(
                    ticker=ticker,
                    quote_response={
                        "bridge_status": "PASS",
                        "data": [{"cur_prc": raw_price}],
                        "retrieved_at": QUOTE_RETRIEVED_AT,
                    },
                    daily_records=[],
                    trading_date=SAME_DAY,
                    observed_at=OBSERVED_AT,
                    market_phase="AFTER_HOURS",
                )
                self.assertIsNotNone(record)
                self.assertEqual(expected, record["price"])

    def test_07i2_invalid_cur_prc_values_fail_closed(self):
        cases = (
            "",
            " ",
            "0",
            "+0.0000",
            "-0.0000",
            "-+1.0000",
            "+-1.0000",
            "++1.0000",
            "--1.0000",
            "+ 1.0000",
            "- 1.0000",
            "+\t1.0000",
            "-\t1.0000",
            "1e2",
            "1E2",
            "+1e2",
            "-1e2",
            "+",
            "-",
            ".",
            "+.",
            "-.",
            "not-a-price",
            float("nan"),
            float("inf"),
            float("-inf"),
            "NaN",
            "Infinity",
            "+Infinity",
            "-Infinity",
        )
        for raw_price in cases:
            with self.subTest(raw_price=raw_price):
                record = _current_price_record(
                    ticker="MVLL",
                    quote_response={
                        "bridge_status": "PASS",
                        "data": [{"cur_prc": raw_price}],
                        "retrieved_at": QUOTE_RETRIEVED_AT,
                    },
                    daily_records=[],
                    trading_date=SAME_DAY,
                    observed_at=OBSERVED_AT,
                    market_phase="AFTER_HOURS",
                )
                self.assertIsNone(record)

    def test_07i3_generic_positive_number_behavior_is_unchanged(self):
        self.assertIsNone(_number("-30.6390", positive=True))
        self.assertIsNone(_number("0", positive=True))
        self.assertEqual(115.82, _number("+115.8200", positive=True))

    def test_08_forbidden_high_level_entrypoints_are_absent_and_not_called(self):
        forbidden_modules = {
            "run_portfolio_strategy_orchestrator",
            "automation_delivery",
            "shadow_acceptance",
            "apply_user_confirmed_broker_snapshot",
            "migrate_integrated_shadow_cohort",
        }
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
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
        self.assertTrue(forbidden_modules.isdisjoint(imported))

        calls = []
        fake_modules = {}
        for name in forbidden_modules:
            fake = types.ModuleType(name)
            fake.main = lambda *args, _name=name, **kwargs: calls.append(_name)
            fake_modules[name] = fake
        module_name = "manual_preflight_isolated_import"
        spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
        self.assertIsNotNone(spec)
        isolated = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, fake_modules):
            assert spec.loader is not None
            spec.loader.exec_module(isolated)
            isolated.run_manual_preflight(
                manual_run_id="manual-sentinel-import-test",
                system_portfolio=system_portfolio(),
                system_portfolio_source="TEST_ONLY/system-portfolio.json",
                system_portfolio_sha256="b" * 64,
                provenance_policy=self.provenance_policy,
                account_reader=account_reader_for({"AAA": 1.0}, {"AAA": 80.0}),
                market_reader=market_reader_for(["AAA"]),
                maximum_broker_age_seconds=900,
                decision_as_of=OBSERVED_AT,
                observed_at=OBSERVED_AT,
            )
        self.assertEqual([], calls)

    def test_09_report_schema_and_manual_provenance_invariants(self):
        report = self.build_report()
        self.assertEqual([], validate_instance(report, SCHEMA))
        self.assertEqual("2.1", report["schema_version"])
        self.assertEqual("VERIFIED", report["identity_authority_status"])
        self.assertEqual("MATCHED", report["integrated_authority_cohort_status"])
        self.assertEqual("VERIFIED_MANUAL", report["run_provenance_status"])
        self.assertEqual("GRADE_B", report["evidence_grade"])
        self.assertEqual("GRADE_B", report["provenance"]["evidence_grade"])
        self.assertEqual("VERIFIED_REAL_DATA", report["manual_data_verification_status"])
        self.assertEqual("HEALTHY", report["kiwoom_health_status"])
        self.assertEqual("AVAILABLE", report["broker_snapshot_status"])
        self.assertEqual("VERIFIED", report["orderable_cash_status"])
        self.assertEqual("PASS", report["finalized_bar_preflight_status"])
        self.assertTrue(report["operator_initiated"])
        self.assertEqual("VERIFIED_READ_ONLY", report["kiwoom_capability_status"])
        self.assertFalse(report["maturity_eligible"])
        self.assertFalse(report["operational_maturity_eligible"])
        self.assertFalse(report["policy_evolution_eligible"])
        self.assertFalse(report["backfill"])
        self.assertIsNone(report["scheduled_occurrence_id"])
        self.assertFalse(report["scheduled_pair_eligible"])

    def test_09a_private_selector_source_is_semantically_unchanged(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        start = source.index("def _select_last_verified_finalized_bar(")
        end = source.index("\ndef select_last_verified_finalized_bar(", start)
        selector_source = source[start:end]
        self.assertEqual(
            "279879d8c9403e70cf3f1391232064b64ece6bd362c8e567eb27d2e44a0f2406",
            hashlib.sha256(selector_source.encode("utf-8")).hexdigest(),
        )

    def test_10_production_cli_exposes_no_arbitrary_output_root(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("instrument_primary_mics", inspect.signature(run_manual_preflight).parameters)
        self.assertNotIn('add_argument("--output-root"', source)
        self.assertNotIn('add_argument("--repo-root"', source)
        self.assertNotIn('add_argument("--official-session-evidence"', source)
        self.assertNotIn('add_argument("--primary-mic"', source)
        self.assertNotIn('add_argument("--exchange"', source)
        self.assertNotIn('add_argument("--registry-path"', source)
        self.assertNotIn('add_argument("--activation-path"', source)
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--official-session-evidence", "{}"],
            cwd=ROOT, check=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        self.assertEqual(2, completed.returncode)
        self.assertIn("unrecognized arguments", completed.stderr)




class ScheduledInputRunnerTests(unittest.TestCase):
    def test_explicit_scheduled_cli_routes_only_to_existing_compiler(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            guards = [stack.enter_context(patch.object(manual_preflight_module, name,
                       side_effect=AssertionError("Scheduled input cannot collect or write manual reports")))
                      for name in ("run_manual_preflight", "invoke_account_bridge_batch", "invoke_bridge_batch", "write_immutable_report")]
            compiler = stack.enter_context(patch("portfolio_decision_dashboard.main", return_value=0))
            stack.enter_context(patch.object(sys, "argv", ["runner", "--input-mode", "LIVE_READ_ONLY",
                "--portfolio-evidence", "evidence.json", "--scheduled-provenance", "run.json",
                "--decision-plan", "plan.json", "--expected-runtime-head", "a" * 40]))
            self.assertEqual(manual_preflight_module.main(), 0)
            compiler.assert_called_once()
            self.assertIn("--decision-plan", compiler.call_args.args[0])
            for guard in guards: guard.assert_not_called()

    def test_label_only_and_missing_plan_never_collect_or_compile(self):
        from contextlib import redirect_stderr
        from io import StringIO
        for extra in ([], ["--portfolio-evidence", "evidence.json", "--scheduled-provenance", "run.json",
                           "--expected-runtime-head", "a" * 40]):
            with self.subTest(extra=extra), patch.object(sys, "argv", ["runner", "--input-mode", "LIVE_READ_ONLY", *extra]), \
                    patch.object(manual_preflight_module, "run_manual_preflight") as collect, \
                    patch("portfolio_decision_dashboard.main") as compile_, redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as error: manual_preflight_module.main()
                self.assertEqual(error.exception.code, 2)
                collect.assert_not_called()
                compile_.assert_not_called()


class ScheduledRegisteredTaskBindingTests(unittest.TestCase):
    def setUp(self):
        from test_portfolio_decision_dashboard import scheduled_compilation_fixture
        from test_deployment_provenance import fixture_git
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args = scheduled_compilation_fixture(self.root)
        self.home = self.root / "test-home"
        for mocked in (patch("deployment_provenance.Path.home", return_value=self.home),
                       patch("deployment_provenance._git", side_effect=fixture_git)):
            mocked.start()
            self.addCleanup(mocked.stop)

    def validate(self):
        import copy
        source, supplied = self.args["evidence"], self.args["scheduled_provenance"]
        before = copy.deepcopy((source, supplied))
        files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        try:
            return manual_preflight_module.validate_scheduled_input(
                source, supplied, evidence_sha256=self.args["input_hashes"]["portfolio_evidence"],
                expected_head="a" * 40, runtime_repo=self.root,
                session_authority_resolver=self.args["current_session_authority_resolver"],
            )
        finally:
            self.assertEqual((source, supplied), before)
            self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, files)

    def test_t1_canonical_registered_provenance_passes_fixture(self):
        result = self.validate()
        self.assertEqual(result["run_provenance_status"], "VERIFIED_SCHEDULED_GENUINE")
        self.assertTrue(result["actual_scheduled_run"])
        self.assertEqual(result["operational_grade"], "GRADE_A_CANDIDATE")
        self.assertFalse(result["scheduled_maturity_promoted"])

    def test_t8_internally_consistent_scheduled_masquerade_with_alternate_config_blocks(self):
        from test_deployment_provenance import supply_task_config
        supplied = self.args["scheduled_provenance"]
        task_id = supplied["task_id"]
        canonical = self.home / ".codex/automations" / task_id / "automation.toml"
        alternate = self.root / "forged-active.toml"
        alternate.write_bytes(canonical.read_bytes())
        canonical.write_bytes(canonical.read_bytes().replace(b'"ACTIVE"', b'"PAUSED"'))
        supply_task_config(supplied["deployment_provenance"], task_id, alternate)
        digest = supplied["deployment_provenance"]["record_hash"]
        supplied["run"]["runtime_manifest_hash"] = digest
        supplied["run"]["provenance_evidence"]["runtime_manifest_hash"] = digest
        # Every other scheduled claim is consistent: this formerly returned genuine.
        with patch("deployment_provenance._read_registered_task_config", side_effect=lambda task, p: Path(p).read_bytes()):
            self.assertTrue(self.validate()["actual_scheduled_run"])
        with patch.object(manual_preflight_module, "derive_run_provenance", wraps=manual_preflight_module.derive_run_provenance) as derive:
            with self.assertRaisesRegex(ValueError, "SCHEDULED_DEPLOYMENT_NOT_VERIFIED:.*CURRENT_TASK_NOT_VERIFIED"):
                self.validate()
            derive.assert_not_called()

    def test_canonical_path_does_not_promote_grade_b(self):
        from test_portfolio_decision_dashboard import bind_scheduled_fixture
        self.args["evidence"]["evidence_grade"] = "GRADE_B"
        self.args["evidence"]["provenance"]["evidence_grade"] = "GRADE_B"
        bind_scheduled_fixture(self.args)
        with self.assertRaisesRegex(ValueError, "SCHEDULED_EVIDENCE_MODE_MISMATCH"):
            self.validate()


class LocalRegularBarCoherenceTests(unittest.TestCase):
    """Offline consumed-byte contract for the Manual holding timing lane."""

    def setUp(self):
        import copy
        self.copy = copy
        _, artifacts = captured_handoff_fixture()
        self.document = json.loads(artifacts[0][0])
        self.request = next(item for item in self.document["requests"]
                            if item["operation"] == "daily_chart")

    def check(self, mutate=None, *, extra_document=None, observed_at=POST_CUTOFF_RETRIEVED_AT,
              request=None, core_close_at="2026-08-20T20:00:00+00:00", bind=True):
        doc = self.copy.deepcopy(self.document)
        if mutate:
            mutate(doc)
        raw = json.dumps(doc, sort_keys=True).encode()
        artifacts = [(raw, hashlib.sha256(raw).hexdigest())]
        if extra_document is not None:
            extra = json.dumps(extra_document, sort_keys=True).encode()
            artifacts.append((extra, hashlib.sha256(extra).hexdigest()))
        captures = manual_preflight_module._parent_capture_evidence(
            artifacts, run_id=doc["run_id"], observed_at=observed_at,
        ) if bind else []
        response = next(item for item in doc["results"] if item["operation"] == "daily_chart")
        return manual_preflight_module.local_regular_bar_coherence(
            response, request=request or self.request, captures=captures,
            expected_completed_session=PREVIOUS_DAY, core_close_at=core_close_at,
            observed_at=observed_at,
        )

    def test_p1_p2_previous_regular_bar_during_day_is_local_only(self):
        result = self.check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["provider_finalization_verified"], "NOT_VERIFIED")
        self.assertEqual(result["bar"]["session"], PREVIOUS_DAY)
        self.assertEqual(result["bar"]["close"], 99.0)
        # 10:00 ET on the next day is a Day query of a prior regular bar.
        def day_capture(doc):
            doc.update(started_at="2026-08-21T13:59:59+00:00",
                       observed_at="2026-08-21T14:00:01+00:00")
            for item in doc["results"]:
                if item.get("retrieved_at") is not None:
                    item["retrieved_at"] = "2026-08-21T14:00:00+00:00"
                if item["operation"] == "daily_chart":
                    item["pagination"]["pages"][0]["retrieved_at"] = "2026-08-21T14:00:00+00:00"
        during_day = self.check(day_capture, observed_at="2026-08-21T14:00:07+00:00")
        self.assertEqual(during_day["status"], "PASS")

    def test_n1_invalid_ohlcv_fails_without_repair(self):
        def invalid(doc):
            row = next(x for x in doc["results"] if x["operation"] == "daily_chart")["data"][-1]
            row["cur_prc"] = 90.0
        result = self.check(invalid)
        self.assertEqual((result["status"], result["reason"]), ("FAIL", "LOCAL_BAR_OHLCV_INVALID"))
        self.assertIsNone(result["bar"])

    def test_n2_n3_time_and_session_mismatch_fail_closed(self):
        self.assertEqual(self.check(observed_at="2026-08-21T22:20:00+00:00")["status"], "FAIL")
        def future(doc):
            response = next(x for x in doc["results"] if x["operation"] == "daily_chart")
            response["data"].append({"dt": "20260821", "open_pric": 100,
                                     "high_pric": 102, "low_pric": 99,
                                     "cur_prc": 101, "acc_trde_qty": 1000})
        self.assertEqual(self.check(future)["reason"], "LOCAL_BAR_FUTURE_ROW")
        self.assertEqual(self.check(request=dict(self.request, completed_session=SAME_DAY))["status"], "FAIL")
        self.assertEqual(self.check(core_close_at="2026-08-21T20:00:00+00:00")["status"], "FAIL")

    def test_n4_basis_api_and_page_binding_mismatch(self):
        self.assertEqual(self.check(request=dict(self.request, price_basis="ADJUSTED"))["status"], "FAIL")
        self.assertEqual(self.check(request=dict(self.request, fx_applied=True))["status"], "FAIL")
        for change in (
            lambda r: r["pagination"].update(api_id="wrong"),
            lambda r: r["pagination"]["pages"][0].update(api_id="wrong"),
            lambda r: r["data"][-1].update(upd_stkpc_tp="1"),
            lambda r: r.update(ticker="WRONG"),
        ):
            def mutate(doc):
                change(next(x for x in doc["results"] if x["operation"] == "daily_chart"))
            with self.subTest(change=change):
                self.assertEqual(self.check(mutate)["status"], "FAIL")

    def test_n6_same_scope_conflicting_capture_is_not_verified(self):
        other = self.copy.deepcopy(self.document)
        row = next(x for x in other["results"] if x["operation"] == "daily_chart")["data"][-1]
        row.update(cur_prc=98.0, high_pric=100.0)
        result = self.check(extra_document=other)
        self.assertEqual((result["status"], result["reason"]),
                         ("NOT_VERIFIED", "LOCAL_BAR_SAME_SCOPE_CONFLICT"))

    def test_n6_same_close_high_only_and_all_ohlcv_fields_are_compared(self):
        baseline = next(x for x in self.document["results"]
                        if x["operation"] == "daily_chart")["data"][-1]
        for field, value in (("open_pric", 99.5), ("high_pric", 131.0),
                             ("low_pric", 98.0), ("cur_prc", 98.5),
                             ("acc_trde_qty", 1001)):
            with self.subTest(field=field):
                other = self.copy.deepcopy(self.document)
                row = next(x for x in other["results"]
                           if x["operation"] == "daily_chart")["data"][-1]
                row[field] = value
                if field != "cur_prc":
                    self.assertEqual(row["cur_prc"], baseline["cur_prc"])
                result = self.check(extra_document=other)
                self.assertEqual((result["status"], result["reason"]),
                                 ("NOT_VERIFIED", "LOCAL_BAR_SAME_SCOPE_CONFLICT"))
        same = self.copy.deepcopy(self.document)
        row = next(x for x in same["results"] if x["operation"] == "daily_chart")["data"][-1]
        row["high_pric"] = str(float(row["high_pric"]))
        self.assertEqual(self.check(extra_document=same)["status"], "PASS")

    def test_n7_n8_price_equality_and_base_close_are_not_authority(self):
        def equal_quote(doc):
            next(x for x in doc["results"] if x["operation"] == "market_quote")["data"][0]["cur_prc"] = 99.0
        self.assertEqual(self.check(equal_quote, bind=False)["status"], "NOT_VERIFIED")
        def base_mismatch(doc):
            response = next(x for x in doc["results"] if x["operation"] == "daily_chart")
            response["base_close_pric"] = "9000"
        self.assertEqual(self.check(base_mismatch)["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
