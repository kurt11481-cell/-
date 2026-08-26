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
                    "api_id": "ust21070" if operation == "account_holdings_read" else "READ_ONLY",
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
                    rows.append({"dt": "20260821", "cur_prc": 101.0})
                if ticker in previous:
                    rows.append({"dt": "20260820", "cur_prc": 99.0})
                result = {
                    "bridge_status": "PASS",
                    "operation": operation,
                    "ticker": ticker,
                    "data": rows,
                    "pagination": {"api_id": "usa06012", "status": "SUFFICIENT"},
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


class ManualPortfolioAnalysisTest(unittest.TestCase):
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
            account_reader=account_reader_for(
                holdings,
                costs,
                holdings_status=holdings_status,
                holdings_complete=holdings_complete,
                orderable_cash=orderable_cash,
                retrieved_at=account_retrieved_at,
            ),
            market_reader=market_reader_for(
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
        )

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
        self.assertEqual("2.0", report["schema_version"])
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
