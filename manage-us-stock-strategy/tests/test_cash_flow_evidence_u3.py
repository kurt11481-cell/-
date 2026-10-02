"""S7 U3: cash-flow evidence for empty periods (Kiwoom 501724) and par-value split/merge rows.

Strings are the values measured on 2026-10-02. Amounts and the account label are fictional (TEST_ONLY).
No real account data, no network, no state writes.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cash_flow_evidence as cfe  # noqa: E402
from test_cash_flow_evidence import ACCOUNT_LABEL, raw_history  # noqa: E402
from validation_common import canonical_hash, load_json, validate_instance  # noqa: E402

PERIOD = ("2026-10-01", "2026-10-05")
NO_DATA_MESSAGE = "[2000](501724:관련자료가 없습니다)"
OUT_OF_RANGE_MESSAGE = "[2000](501058:조회기간은 1년 이내로만 가능합니다.)"
EXPECTED_CORPORATE_ACTION_RULE = {"classification": "CORPORATE_ACTION", "fields": ["deal_kind_nm", "rmrk_nm"],
                                  "match_any": ["액면", "단주대금"]}
MEASURED_ROWS = [
    {"deal_dt": "20261002", "deal_kind_nm": "입출금", "rmrk_nm": "배당금(외화)입금", "fc_exct_amt": "12.34"},
    {"deal_dt": "20261002", "deal_kind_nm": "입출금", "rmrk_nm": "병합단주대금입금(외화)", "fc_exct_amt": "3.21"},
    {"deal_dt": "20261002", "deal_kind_nm": "입출고", "rmrk_nm": "액면병합출고", "fc_exct_amt": "0.00"},
    {"deal_dt": "20261002", "deal_kind_nm": "입출고", "rmrk_nm": "액면분할병합입고", "fc_exct_amt": "0.00"},
    {"deal_dt": "20261002", "deal_kind_nm": "입출고", "rmrk_nm": "액면분할병합출고", "fc_exct_amt": "0.00"},
    {"deal_dt": "20261002", "deal_kind_nm": "매매", "rmrk_nm": "매수", "fc_exct_amt": "100.00", "fc_cmsn": "0.50"},
    {"deal_dt": "20261002", "deal_kind_nm": "매매", "rmrk_nm": "매도", "fc_exct_amt": "90.00", "fc_cmsn": "0.40"},
]


def no_data_body(**extra) -> dict:
    return dict({"return_msg": NO_DATA_MESSAGE, "return_code": 20}, **extra)


def normalize(raw, period: tuple[str, str] = PERIOD) -> dict:
    return cfe.normalize_transaction_history(raw, period_from=period[0], period_to=period[1], raw_sha256="a" * 64)


class ClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = cfe.load_classification()

    def test_measured_strings(self) -> None:
        cases = [
            ("입출금", "배당금(외화)입금", ("DIVIDEND", None)),
            ("입출금", "병합단주대금입금(외화)", ("CORPORATE_ACTION", None)),
            ("입출고", "액면병합출고", ("CORPORATE_ACTION", None)),
            ("입출고", "액면분할병합입고", ("CORPORATE_ACTION", None)),
            ("입출고", "액면분할병합출고", ("CORPORATE_ACTION", None)),
            ("매매", "매수", ("TRADE", None)),
            ("매매", "매도", ("TRADE", None)),
        ]
        for kind, memo, expected in cases:
            with self.subTest(kind=kind, memo=memo):
                self.assertEqual(cfe.classify_row(kind, memo, self.table), expected)

    def test_rule_is_placed_after_fee_tax_interest_and_before_fx(self) -> None:
        classifications = [rule["classification"] for rule in self.table["rules"]]
        self.assertEqual(classifications, ["DIVIDEND", "FEE_TAX_INTEREST", "CORPORATE_ACTION", "FX", "TRADE", "TRANSFER"])
        self.assertEqual(self.table["rules"][2], EXPECTED_CORPORATE_ACTION_RULE)
        self.assertEqual(self.table["rule_order"], "first_match_wins")
        self.assertIn("corporate-action rows (par-value split/merge transfers and fractional-share cash) are not "
                      "external cash flows", self.table["purpose"])
        self.assertEqual(self.table["status"], "dividend_trade_split_and_fractional_cash_strings_verified_2026_10_02_"
                                               "transfer_and_fx_strings_unobserved")

    def test_only_deposit_withdrawal_and_fx_are_external(self) -> None:
        self.assertEqual(cfe.EXTERNAL_CLASSES, ("DEPOSIT", "WITHDRAWAL", "FX"))
        self.assertIn("CORPORATE_ACTION", cfe.NON_EXTERNAL_CLASSES)
        declaration_schema = load_json(ROOT / "manage-us-stock-strategy/schemas/cash-flow-declaration.schema.json")
        external_row = declaration_schema["properties"]["external_rows"]["items"]
        self.assertEqual(external_row["properties"]["classification"]["enum"], ["DEPOSIT", "WITHDRAWAL", "FX"])

    def test_regressions_stay_unchanged(self) -> None:
        cases = [
            ("입출고", "타사대체입고", ("UNCLASSIFIED", None)),
            ("입출고", "타사대체출고", ("UNCLASSIFIED", None)),
            ("입출금", "이체입금", ("DEPOSIT", 1)),
            ("입출금", "이체출금", ("WITHDRAWAL", -1)),
            ("환전", "환전매수", ("FX", 1)),
            ("입출금", "수수료출금", ("FEE_TAX_INTEREST", None)),
        ]
        for kind, memo, expected in cases:
            with self.subTest(kind=kind, memo=memo):
                self.assertEqual(cfe.classify_row(kind, memo, self.table), expected)

    def test_other_transfer_rows_still_stop_the_evidence(self) -> None:
        result = normalize(raw_history([{"deal_dt": "20261002", "deal_kind_nm": "입출고", "rmrk_nm": "타사대체입고"}]))
        self.assertEqual(result["unresolved"], ["CASH_FLOW_ROW_UNCLASSIFIED:2026-10-02:000000001"])


class MeasuredRowEvidenceTests(unittest.TestCase):
    def test_seven_measured_rows_leave_nothing_unresolved_and_no_external_flow(self) -> None:
        result = normalize(raw_history(MEASURED_ROWS))
        self.assertEqual([row["classification"] for row in result["rows"]],
                         ["DIVIDEND", "CORPORATE_ACTION", "CORPORATE_ACTION", "CORPORATE_ACTION", "CORPORATE_ACTION",
                          "TRADE", "TRADE"])
        self.assertEqual(result["unresolved"], [])
        self.assertEqual(result["totals"]["external_net_usd"], "0.00")
        self.assertEqual(cfe.evidence_errors(result), [])
        block = cfe.build_declaration(result, declared_usd=None, prior_blocks=[])
        self.assertEqual((block["declaration_status"], block["external_rows"]), ("NO_EXTERNAL_FLOW", []))
        self.assertEqual(cfe.declaration_block_errors(block), [])

    def test_corporate_action_amounts_enter_no_total(self) -> None:
        result = normalize(raw_history(MEASURED_ROWS))
        corporate = [row for row in result["rows"] if row["classification"] == "CORPORATE_ACTION"]
        self.assertTrue(all(row["signed_amount_usd"] is None and row["unresolved"] == [] for row in corporate))
        self.assertEqual(result["totals"], {"external_net_usd": "0.00", "dividend_settlement_usd": "12.34",
                                            "fees_usd": "0.90", "taxes_usd": "0.00"})
        block = cfe.build_declaration(result, declared_usd=None, prior_blocks=[])
        self.assertEqual(block["excluded_from_cash_flow"],
                         {"dividend_settlement_usd": "12.34", "fees_usd": "0.90", "taxes_usd": "0.00"})
        with self.assertRaisesRegex(cfe.CashFlowError, "EXCEEDS_LIMIT"):
            cfe.build_declaration(result, declared_usd="3.21", prior_blocks=[])

    def test_table_hash_follows_the_table_in_use(self) -> None:
        result = normalize(raw_history(MEASURED_ROWS))
        self.assertEqual(result["classification_table_sha256"], canonical_hash(cfe.load_classification()))


class EmptyPeriodTests(unittest.TestCase):
    def assert_empty_evidence(self, result: dict) -> None:
        self.assertEqual((result["row_count"], result["rows"], result["unresolved"]), (0, [], []))
        self.assertEqual(result["totals"], {"external_net_usd": "0.00", "dividend_settlement_usd": "0.00",
                                            "fees_usd": "0.00", "taxes_usd": "0.00"})
        self.assertIs(result["account_identifier_stored"], False)
        self.assertEqual((result["order_authority"], result["quantity_authority"]), (False, "none"))
        self.assertEqual(result["source"]["api_id"], "ust21100")
        self.assertEqual(validate_instance(result, cfe.EVIDENCE_SCHEMA), [])
        self.assertEqual(cfe.evidence_errors(result), [])
        self.assertNotIn("acnt_print", json.dumps(result))
        block = cfe.build_declaration(result, declared_usd=None, prior_blocks=[])
        self.assertEqual((block["declaration_status"], block["external_rows"], block["new_external_net_usd"]),
                         ("NO_EXTERNAL_FLOW", [], "0.00"))

    def test_no_data_response_wrapped_and_unwrapped(self) -> None:
        for name, raw in (("wrapped", {"result": no_data_body()}), ("unwrapped", no_data_body()),
                          ("wrapped_with_empty_list", {"result": no_data_body(result_list=[])}),
                          ("unwrapped_with_empty_list", no_data_body(result_list=[]))):
            with self.subTest(shape=name):
                self.assert_empty_evidence(normalize(raw))

    def test_empty_evidence_has_the_same_hash_for_both_shapes(self) -> None:
        self.assertEqual(normalize({"result": no_data_body()}), normalize(no_data_body()))

    def test_no_data_response_with_rows_fails(self) -> None:
        row = raw_history([{"deal_dt": "20261002", "deal_kind_nm": "입출금", "rmrk_nm": "이체입금",
                            "fc_exct_amt": "5.00"}])["result"]["result_list"]
        for raw in ({"result": no_data_body(result_list=row)}, no_data_body(result_list=row)):
            with self.assertRaises(cfe.CashFlowError) as caught:
                normalize(raw)
            self.assertEqual(str(caught.exception), "CASH_FLOW_EVIDENCE_EMPTY_RESPONSE_HAS_ROWS")

    def test_other_failures_are_kept(self) -> None:
        cases = {
            "out_of_range_without_list": ({"return_msg": OUT_OF_RANGE_MESSAGE, "return_code": 20},
                                          "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "out_of_range_wrapped": ({"result": {"return_msg": OUT_OF_RANGE_MESSAGE, "return_code": 20}},
                                     "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "out_of_range_with_list": ({"return_msg": OUT_OF_RANGE_MESSAGE, "return_code": 20, "result_list": []},
                                       "CASH_FLOW_EVIDENCE_RETURN_CODE_NOT_ZERO"),
            "code_20_without_message": ({"return_code": 20}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_20_other_message": ({"return_msg": "[2000](500000:other)", "return_code": 20},
                                      "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "message_without_colon": ({"return_msg": "501724", "return_code": 20},
                                      "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "message_not_text": ({"return_msg": 501724, "return_code": 20}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_not_20": ({"return_msg": NO_DATA_MESSAGE, "return_code": 0}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_other_nonzero": ({"return_msg": NO_DATA_MESSAGE, "return_code": 21},
                                   "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_text": ({"return_msg": NO_DATA_MESSAGE, "return_code": "20"}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_float": ({"return_msg": NO_DATA_MESSAGE, "return_code": 20.0}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_bool": ({"return_msg": NO_DATA_MESSAGE, "return_code": True}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_zero_without_list": ({"return_code": 0}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "code_zero_wrapped_without_list": ({"result": {"return_code": 0}}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "empty_wrapper": ({"result": {}}, "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "not_object": ([], "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "list_not_a_list": (no_data_body(result_list="x"), "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"),
            "rows_with_code_20_and_no_message": (raw_history([{"deal_dt": "20261002", "deal_kind_nm": "매매",
                                                                "rmrk_nm": "매수"}], return_code=20),
                                                 "CASH_FLOW_EVIDENCE_RETURN_CODE_NOT_ZERO"),
        }
        for name, (raw, code) in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(cfe.CashFlowError) as caught:
                    normalize(raw)
                self.assertEqual(str(caught.exception), code)

    def test_period_is_checked_for_an_empty_response_too(self) -> None:
        for raw in ({"result": no_data_body()}, no_data_body()):
            for period in (("2026-10-05", "2026-10-01"), ("not-a-date", "2026-10-01")):
                with self.subTest(period=period), self.assertRaises(cfe.CashFlowError) as caught:
                    normalize(raw, period=period)
                self.assertEqual(str(caught.exception), "CASH_FLOW_EVIDENCE_PERIOD_INVALID")


class EmptyEvidenceChainTests(unittest.TestCase):
    def block(self, period: tuple[str, str]) -> dict:
        return cfe.build_declaration(normalize({"result": no_data_body()}, period=period), declared_usd=None,
                                     prior_blocks=[])

    def test_empty_period_is_clear_and_advances_coverage(self) -> None:
        first = self.block(("2026-10-01", "2026-10-05"))
        result = cfe.cash_flow_chain([{"as_of": "2026-10-05", "state_revision": 2, "block": first,
                                       "post_activation": True}], start_date="2026-10-01")
        self.assertEqual([step["status"] for step in result["steps"]], ["CLEAR"])
        self.assertEqual((result["steps"][0]["reasons"], result["adjustments"], result["hold_active"]), ([], [], False))
        self.assertEqual(result["covered_through"], "2026-10-05")

    def test_contiguous_empty_periods_chain(self) -> None:
        second = self.block(("2026-10-06", "2026-10-12"))
        result = cfe.cash_flow_chain(
            [{"as_of": "2026-10-05", "state_revision": 2, "block": self.block(("2026-10-01", "2026-10-05")),
              "post_activation": True},
             {"as_of": "2026-10-12", "state_revision": 3, "block": second, "post_activation": True}],
            start_date="2026-10-01")
        self.assertEqual([step["status"] for step in result["steps"]], ["CLEAR", "CLEAR"])
        self.assertEqual((result["adjustments"], result["covered_through"]), ([], "2026-10-12"))

    def test_a_gap_after_an_empty_period_still_holds(self) -> None:
        result = cfe.cash_flow_chain(
            [{"as_of": "2026-10-05", "state_revision": 2, "block": self.block(("2026-10-01", "2026-10-05")),
              "post_activation": True},
             {"as_of": "2026-10-20", "state_revision": 3, "block": self.block(("2026-10-10", "2026-10-20")),
              "post_activation": True}], start_date="2026-10-01")
        self.assertEqual(result["steps"][1]["reasons"], ["CASH_FLOW_COVERAGE_GAP"])
        self.assertTrue(result["hold_active"])


class NormalizeCliTests(unittest.TestCase):
    def run_cli(self, raw: dict) -> tuple[int, dict, dict | None]:
        with tempfile.TemporaryDirectory() as directory:
            raw_path, target = Path(directory) / "raw.json", Path(directory) / "evidence.json"
            raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                code = cfe.main(["normalize", "--raw", str(raw_path), "--from", PERIOD[0], "--to", PERIOD[1],
                                 "--output", str(target)])
            written = load_json(target) if target.exists() else None
            if written is not None:
                self.assertNotIn(ACCOUNT_LABEL, target.read_text(encoding="utf-8"))
        return code, json.loads(output.getvalue()), written

    def test_empty_raw_file_normalizes(self) -> None:
        for raw in ({"result": no_data_body()}, no_data_body()):
            code, printed, written = self.run_cli(raw)
            self.assertEqual((code, printed["status"], printed["row_count"], printed["unresolved_count"]),
                             (0, "OK", 0, 0))
            self.assertEqual(printed["external_net_usd"], "0.00")
            self.assertEqual(validate_instance(written, cfe.EVIDENCE_SCHEMA), [])
            self.assertEqual(cfe.evidence_errors(written), [])

    def test_out_of_range_raw_file_still_fails(self) -> None:
        code, printed, written = self.run_cli({"return_msg": OUT_OF_RANGE_MESSAGE, "return_code": 20})
        self.assertEqual((code, printed, written),
                         (2, {"status": "FAIL", "error": "CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID"}, None))


if __name__ == "__main__":
    unittest.main()
