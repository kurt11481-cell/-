from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

from build_nbis_v4_shadow_successor import build_price_authority, build_valuation
from us_stock_price_authority import (
    build_us_stock_price_authority,
    validate_kiwoom_self_integrity,
    validate_price_authority_artifact,
)
from validation_common import load_json, validate_instance


class NBISV4KiwoomPriceAuthorityTests(unittest.TestCase):
    def record(self) -> dict:
        return {
            "ticker": "NBIS", "requested_ticker": "NBIS",
            "security_identity": "Nebius Group N.V. (NASDAQ:NBIS)",
            "security_identity_status": "VERIFIED", "currency": "USD",
            "fx_applied": False, "canonical_price": 255.84,
            "api_status": "SUCCESS", "source_api_id": "usa06012",
            "source_endpoint": "/api/us/chart", "source_field": "result_list.cur_prc",
            "target_session": "2026-08-13", "returned_row_date": "2026-08-13",
            "market_phase": "COMPLETED_DAILY", "price_semantics": "COMPLETED_DAILY_CLOSE",
            "price_basis": "RAW_REGULAR_SESSION_CLOSE",
            "retrieval_timestamp": "2026-08-14T05:11:43.232981+00:00",
            "retrieval_market_phase": "MARKET_CLOSED_ARCHIVED_DAILY_QUERY",
            "request_parameters": {"stex_tp": "ND", "stk_cd": "NBIS", "strt_dt": "20260813",
                                   "upd_stkpc_tp": "0", "exrt_appl_tp": "0"},
            "bar_finalized": True, "stale_record": False,
            "corporate_action_ambiguity": False, "scale_error": False,
        }

    def authority(self, yfinance: float = 255.0399932861328) -> dict:
        return build_us_stock_price_authority(
            self.record(), yfinance_reference=yfinance, external_reference=255.04,
            authority_policy_version="test-v1", generated_at="2026-08-14T10:00:00Z")

    def test_divergence_is_nonblocking(self):
        value = self.authority()
        self.assertEqual(value["self_integrity"]["status"], "KIWOOM_PRICE_VALIDATED")
        self.assertEqual(value["comparison_status"], "CROSS_PROVIDER_DIAGNOSTIC_DIVERGENCE")
        self.assertFalse(value["diagnostics"]["divergence_blocking"])

    def test_two_percent_divergence_is_nonblocking(self):
        value = self.authority(250.0)
        self.assertGreater(value["diagnostics"]["cross_provider_difference_pct"], 2.0)
        self.assertFalse(value["blocking"])

    def test_yfinance_cannot_override_kiwoom(self):
        self.assertEqual(self.authority(1.0)["canonical_price"], 255.84)

    def test_external_reference_cannot_override_kiwoom(self):
        value = build_us_stock_price_authority(
            self.record(), yfinance_reference=255.04, external_reference=1.0,
            authority_policy_version="test-v1", generated_at="2026-08-14T10:00:00Z")
        self.assertEqual(value["canonical_provider"], "KIWOOM_REST")
        self.assertEqual(value["canonical_price"], 255.84)

    def test_provider_prices_are_never_averaged(self):
        self.assertFalse(self.authority()["diagnostics"]["provider_price_averaged"])

    def test_stale_kiwoom_blocks(self):
        value = self.record(); value["stale_record"] = True
        self.assertIn("KIWOOM_STALE", validate_kiwoom_self_integrity(value)["errors"])

    def test_wrong_ticker_blocks(self):
        value = self.record(); value["requested_ticker"] = "AAPL"
        self.assertIn("KIWOOM_WRONG_TICKER", validate_kiwoom_self_integrity(value)["errors"])

    def test_unknown_price_semantics_blocks(self):
        value = self.record(); value["price_semantics"] = "UNKNOWN"
        self.assertIn("KIWOOM_UNKNOWN_PRICE_SEMANTICS", validate_kiwoom_self_integrity(value)["errors"])

    def test_api_error_blocks(self):
        value = self.record(); value["api_status"] = "ERROR"
        self.assertIn("KIWOOM_API_ERROR", validate_kiwoom_self_integrity(value)["errors"])

    def test_day_market_current_not_mislabeled_close(self):
        value = self.record(); value.update({"market_phase": "DAY_MARKET", "price_semantics": "DAY_MARKET_CURRENT", "source_api_id": "usa20100", "source_field": "cur_prc"})
        result = validate_kiwoom_self_integrity(value)
        self.assertNotIn("KIWOOM_UNKNOWN_MARKET_PHASE", result["errors"])
        self.assertNotEqual(value["price_semantics"], "COMPLETED_DAILY_CLOSE")

    def test_current_price_cannot_be_completed_daily(self):
        value = self.record(); value.update({"market_phase": "REGULAR", "price_semantics": "CURRENT_PRICE", "source_api_id": "usa20100", "source_field": "cur_prc"})
        self.assertNotEqual(value["price_semantics"], "COMPLETED_DAILY_CLOSE")

    def test_completed_daily_close_is_canonical(self):
        self.assertFalse(validate_kiwoom_self_integrity(self.record())["blocking"])

    def test_authority_is_deterministic(self):
        self.assertEqual(self.authority(), self.authority())

    def test_live_price_artifact_schema_and_semantics(self):
        value = build_price_authority(ROOT, "2026-08-14T10:00:00Z")
        self.assertEqual(validate_price_authority_artifact(value), [])
        self.assertEqual(validate_instance(value, ROOT / "manage-us-stock-strategy/schemas/us-stock-price-authority.schema.json"), [])
        self.assertAlmostEqual(value["canonical_price"], 255.84)

    def test_valuation_uses_kiwoom_and_no_double_count(self):
        price = build_price_authority(ROOT, "2026-08-14T10:00:00Z")
        capital = load_json(ROOT / "workspace/research/nbis-shadow-activation/2026-08-13/v3/nbis-capital-structure-v3.json")
        value = build_valuation(ROOT, price, capital, "2026-08-14T10:00:00Z")
        self.assertEqual(value["price"]["raw_regular_session_close"], 255.84)
        self.assertEqual(value["valuation_evidence_status"], "DIRECT_SCENARIO_VALIDATED")
        for scenario in value["valuation_scenarios"]:
            self.assertFalse(scenario["convertible_share_equivalent_included"] and scenario["convertible_debt_included"])
        scenarios = {item["scenario_id"]: item for item in value["valuation_scenarios"]}
        self.assertAlmostEqual(scenarios["LEGAL_BASIC_CARRYING_DEBT_CASE"]["equity_value"], 69551.439, places=3)
        self.assertAlmostEqual(scenarios["INITIAL_RATE_KNOWN_GROSS_STRESS_CASE"]["enterprise_value"], 90304.273, places=3)

    def test_authority_boundary(self):
        value = self.authority()
        self.assertIsNone(value["quantity"])
        self.assertEqual(value["quantity_authority"], "none")
        self.assertFalse(value["order_authority"])


if __name__ == "__main__":
    unittest.main()
