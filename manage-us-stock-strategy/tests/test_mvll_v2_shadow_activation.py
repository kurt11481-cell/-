from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("build_mvll_v2", SCRIPTS / "build_mvll_v2_shadow_activation.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class MVLLV2ShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mvll_price = load("workspace/research/mvll-shadow-activation/2026-08-13/v3/mvll-price-authority-v3.json")
        cls.mrvl_price = load("workspace/research/mvll-shadow-activation/2026-08-13/v3/mrvl-price-authority-v3.json")
        cls.valuation = load("workspace/research/valuation-snapshots/2026-08-13/mrvl-valuation-snapshot-v3.json")
        cls.baseline = load("workspace/research/holding-baseline-candidates/2026-08-14/mvll-20260814-v3.json")
        cls.compile = load("workspace/research/shadow-compiles/2026-08-13/mvll-shadow-compile-v3.json")
        cls.mvll_link = load("workspace/research/baseline-event-links/2026-08-13/v2.6.14/mvll-v3-product-event-link.json")
        cls.mrvl_link = load("workspace/research/baseline-event-links/2026-08-13/v2.6.14/mrvl-v3-underlying-event-link.json")

    def test_mvll_01_kiwoom_is_direct_authority(self):
        self.assertEqual(self.mvll_price["canonical_provider"], "KIWOOM_REST")

    def test_mvll_02_yfinance_divergence_is_nonblocking(self):
        self.assertTrue(self.mvll_price["diagnostics"]["cross_provider_divergence"])
        self.assertFalse(self.mvll_price["diagnostics"]["divergence_blocking"])

    def test_mvll_03_no_provider_price_averaging(self):
        self.assertFalse(self.mvll_price["diagnostics"]["provider_price_averaged"])

    def test_mvll_04_mvll_identity_is_etf(self):
        self.assertIn("2X LONG MRVL DAILY ETF", self.mvll_price["security_identity"])

    def test_mvll_05_mrvl_is_independent_issuer_price(self):
        self.assertEqual(self.mrvl_price["ticker"], "MRVL")
        self.assertEqual(self.mrvl_price["canonical_provider"], "KIWOOM_REST")

    def test_mvll_06_mrvl_divergence_is_nonblocking(self):
        self.assertTrue(self.mrvl_price["diagnostics"]["cross_provider_divergence"])
        self.assertFalse(self.mrvl_price["blocking"])

    def test_mvll_07_mrvl_times_two_is_prohibited(self):
        self.assertNotEqual(self.mvll_price["canonical_price"], self.mrvl_price["canonical_price"] * 2)
        self.assertFalse(self.baseline["linked_components"][0]["product_close_substitution"])

    def test_mvll_08_series_a_is_in_stress_only(self):
        stress = next(x for x in self.valuation["valuation_scenarios"] if x["scenario_type"] == "STRESS_DILUTED")
        self.assertIn("SERIES_A_CONVERTED", stress["assumption_ids"])
        self.assertTrue(stress["convertible_share_equivalent_included"])

    def test_mvll_09_celestial_share_and_cash_overhang_quantified(self):
        bridge = self.valuation["derived_values"]["known_stress_share_bridge_millions"]
        self.assertEqual(bridge["celestial"], 24.4)
        self.assertEqual(self.valuation["balance_sheet"]["other_claims"]["value"], 233.0)

    def test_mvll_10_customer_warrant_quantified(self):
        self.assertEqual(self.valuation["derived_values"]["known_stress_share_bridge_millions"]["customer_warrant"], 4.2)

    def test_mvll_11_forward_pe_is_not_evaluated(self):
        method = next(x for x in self.valuation["valuation_methods"] if x["method"] == "FORWARD_PE")
        self.assertEqual(method["status"], "NOT_EVALUATED")

    def test_mvll_12_local_fcf_proxy_not_company_reported(self):
        method = next(x for x in self.valuation["valuation_methods"] if x["method"] == "LOCAL_OCF_MINUS_CAPEX_PROXY_YIELD")
        self.assertFalse(method["company_reported_fcf"])

    def test_mvll_13_unclassified_is_not_add_authority(self):
        self.assertEqual(self.valuation["valuation_judgement_status"], "UNCLASSIFIED")
        self.assertNotEqual(self.compile["strategy_signal"], "ADD_CANDIDATE")

    def test_mvll_14_product_and_issuer_events_are_separate(self):
        self.assertEqual(self.mvll_link["ticker"], "MVLL")
        self.assertEqual(self.mrvl_link["ticker"], "MRVL")
        self.assertNotEqual(self.mvll_link["baseline_event_link_id"], self.mrvl_link["baseline_event_link_id"])

    def test_mvll_15_ema_rvol_boundary_block_preserved(self):
        self.assertIn("EMA10_RECLAIM_RVOL20", self.compile["blocked_decision_classes"])

    def test_mvll_16_compile_is_non_authoritative_ready(self):
        self.assertEqual(self.compile["mode"], "NON_AUTHORITATIVE_SHADOW")
        self.assertEqual(self.compile["shadow_compile_status"], "PASSED")

    def test_mvll_17_quantity_and_order_are_forbidden(self):
        self.assertIsNone(self.compile["quantity"])
        self.assertEqual(self.compile["quantity_authority"], "none")
        self.assertFalse(self.compile["order_authority"])

    def test_mvll_18_kiwoom_integrity_failure_blocks(self):
        record = {
            "ticker": "MVLL", "requested_ticker": "MVLL", "security_identity": "MVLL",
            "security_identity_status": "VERIFIED", "currency": "USD", "fx_applied": False,
            "canonical_price": 27.9, "api_status": "FAILED", "source_api_id": "usa06012",
            "source_endpoint": "/api/us/chart", "source_field": "result_list.cur_prc",
            "official_field_meaning": "CURRENT_PRICE_CLOSE_IN_DAILY_CHART", "target_session": "2026-08-13",
            "returned_row_date": "2026-08-13", "market_phase": "COMPLETED_DAILY",
            "price_semantics": "COMPLETED_DAILY_CLOSE", "price_basis": "RAW_REGULAR_SESSION_CLOSE",
            "retrieval_timestamp": "2026-08-14T05:11:43Z", "retrieval_market_phase": "MARKET_CLOSED_ARCHIVED_DAILY_QUERY",
            "request_parameters": {"stex_tp": "ND", "stk_cd": "MVLL", "strt_dt": "20260813", "upd_stkpc_tp": "0", "exrt_appl_tp": "0"},
            "bar_finalized": True, "stale_record": False, "corporate_action_ambiguity": False, "scale_error": False,
        }
        built = module.build_us_stock_price_authority(record, yfinance_reference=27.81, external_reference=None,
                                                       authority_policy_version="test", generated_at="2026-08-14T06:00:00Z")
        self.assertTrue(built["blocking"])


if __name__ == "__main__":
    unittest.main()
