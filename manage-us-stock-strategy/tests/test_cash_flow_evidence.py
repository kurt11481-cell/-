"""S5 R6: cash-flow evidence, declaration limit and the reconciliation proposal/apply path.

Every transaction row here is fictional (TEST_ONLY). No real account data, no network, no real state writes.
"""

from __future__ import annotations

import copy
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cash_flow_evidence as cfe  # noqa: E402
import reconcile_broker_state as cli  # noqa: E402
from test_reconcile_broker_state import (  # noqa: E402
    ALL_OPERATIONS, PROPOSAL_SCHEMA, TempStateCase, account_results, base_state, make_proposal, rehash, utc,
)
from validation_common import load_json, validate_instance  # noqa: E402

DECLARATION_SCHEMA = ROOT / "manage-us-stock-strategy/schemas/cash-flow-declaration.schema.json"
BASE_ROW = {"deal_kind_nm": "", "rmrk_nm": "", "fc_exct_amt": "0.00", "fc_deal_amt": "0.00", "fc_cmsn": "0.00",
            "fc_deal_tax": "0.00", "frgn_pay_txam": "0.00", "crnc_code": "USD", "fc_entra": "0.00"}
ACCOUNT_LABEL = "9999-0000-11 [TEST_ONLY]"


def raw_history(rows: list[dict[str, str]], return_code: int = 0) -> dict:
    return {"result": {"acnt_print": ACCOUNT_LABEL, "sell_sum": "0", "buy_sum": "0", "return_code": return_code,
                       "result_list": [dict(BASE_ROW, deal_no=f"{index + 1:09d}", **row)
                                       for index, row in enumerate(rows)]}}


def evidence(rows: list[dict[str, str]], period: tuple[str, str] = ("2026-10-01", "2026-10-05")) -> dict:
    return cfe.normalize_transaction_history(raw_history(rows), period_from=period[0], period_to=period[1],
                                             raw_sha256="a" * 64)


DEPOSIT = {"deal_dt": "20261002", "deal_kind_nm": "입출금", "rmrk_nm": "이체입금", "fc_exct_amt": "500.00"}
WITHDRAWAL = {"deal_dt": "20261002", "deal_kind_nm": "입출금", "rmrk_nm": "이체출금", "fc_exct_amt": "200.00"}
DIVIDEND = {"deal_dt": "20261002", "deal_kind_nm": "입출금", "rmrk_nm": "배당금(외화)입금", "fc_exct_amt": "42.50",
            "frgn_pay_txam": "7.50"}
BUY = {"deal_dt": "20261002", "deal_kind_nm": "매매", "rmrk_nm": "매수", "fc_exct_amt": "1085.30", "fc_cmsn": "2.70"}
SELL = {"deal_dt": "20261002", "deal_kind_nm": "매매", "rmrk_nm": "매도", "fc_exct_amt": "900.00", "fc_cmsn": "2.25",
        "fc_deal_tax": "0.03"}
FX_IN = {"deal_dt": "20261002", "deal_kind_nm": "환전", "rmrk_nm": "환전매수", "fc_exct_amt": "300.00"}


class EvidenceTests(unittest.TestCase):
    def test_rows_are_classified_and_only_deposits_withdrawals_and_fx_are_external(self) -> None:
        result = evidence([DEPOSIT, WITHDRAWAL, DIVIDEND, BUY, SELL, FX_IN])
        self.assertEqual([row["classification"] for row in result["rows"]],
                         ["DEPOSIT", "WITHDRAWAL", "DIVIDEND", "TRADE", "TRADE", "FX"])
        self.assertEqual([row["signed_amount_usd"] for row in result["rows"]],
                         ["500.00", "-200.00", None, None, None, "300.00"])
        self.assertEqual(result["totals"], {"external_net_usd": "600.00", "dividend_settlement_usd": "42.50",
                                            "fees_usd": "4.95", "taxes_usd": "7.53"})
        self.assertEqual(result["unresolved"], [])
        self.assertEqual(cfe.evidence_errors(result), [])

    def test_account_label_is_never_copied(self) -> None:
        result = evidence([DEPOSIT])
        self.assertIs(result["account_identifier_stored"], False)
        self.assertNotIn("acnt_print", json.dumps(result))
        self.assertNotIn(ACCOUNT_LABEL, json.dumps(result, ensure_ascii=False))

    def test_unknown_or_ambiguous_rows_are_unresolved(self) -> None:
        cases = {
            "CASH_FLOW_ROW_UNCLASSIFIED": {"deal_dt": "20261002", "deal_kind_nm": "입출고", "rmrk_nm": "타사대체입고"},
            "CASH_FLOW_SIGN_UNKNOWN": {"deal_dt": "20261002", "deal_kind_nm": "입출금", "rmrk_nm": "입금취소출금",
                                       "fc_exct_amt": "10.00"},
            "CASH_FLOW_FX_ROW_CURRENCY_NOT_USD": dict(FX_IN, crnc_code="KRW"),
            "CASH_FLOW_AMOUNT_INVALID": dict(DEPOSIT, fc_exct_amt="abc"),
            "CASH_FLOW_AMOUNT_NEGATIVE": dict(DEPOSIT, fc_exct_amt="-5.00"),
        }
        for code, row in cases.items():
            with self.subTest(code=code):
                result = evidence([row])
                self.assertEqual(result["unresolved"], [f"{code}:2026-10-02:000000001"])
                self.assertEqual(result["totals"]["external_net_usd"], "0.00")
        fx_without_direction = dict(FX_IN, rmrk_nm="환전")
        self.assertEqual(evidence([fx_without_direction])["unresolved"], ["CASH_FLOW_SIGN_UNKNOWN:2026-10-02:000000001"])

    def test_non_usd_deposit_is_ignored_not_counted(self) -> None:
        result = evidence([dict(DEPOSIT, crnc_code="KRW")])
        self.assertEqual((result["rows"][0]["classification"], result["totals"]["external_net_usd"], result["unresolved"]),
                         ("NON_USD_IGNORED", "0.00", []))

    def test_malformed_raw_files_are_rejected(self) -> None:
        with self.assertRaisesRegex(cfe.CashFlowError, "ROW_OUTSIDE_PERIOD"):
            evidence([dict(DEPOSIT, deal_dt="20260930")])
        with self.assertRaisesRegex(cfe.CashFlowError, "ROW_KEY_INVALID"):
            evidence([dict(DEPOSIT, deal_dt="2026-10-02")])
        with self.assertRaisesRegex(cfe.CashFlowError, "RETURN_CODE_NOT_ZERO"):
            cfe.normalize_transaction_history(raw_history([DEPOSIT], return_code=20), period_from="2026-10-01",
                                              period_to="2026-10-05", raw_sha256="a" * 64)
        with self.assertRaisesRegex(cfe.CashFlowError, "RAW_SHAPE_INVALID"):
            cfe.normalize_transaction_history({"result": {}}, period_from="2026-10-01", period_to="2026-10-05",
                                              raw_sha256="a" * 64)
        with self.assertRaisesRegex(cfe.CashFlowError, "PERIOD_INVALID"):
            evidence([DEPOSIT], period=("2026-10-05", "2026-10-01"))
        duplicate = raw_history([DEPOSIT, DEPOSIT])
        duplicate["result"]["result_list"][1]["deal_no"] = "000000001"
        with self.assertRaisesRegex(cfe.CashFlowError, "ROW_DUPLICATE"):
            cfe.normalize_transaction_history(duplicate, period_from="2026-10-01", period_to="2026-10-05",
                                              raw_sha256="a" * 64)

    def test_tampered_evidence_is_detected(self) -> None:
        result = evidence([DEPOSIT])
        result["rows"][0]["signed_amount_usd"] = "5000.00"
        self.assertEqual(cfe.evidence_errors(result), ["CASH_FLOW_EVIDENCE_HASH_MISMATCH"])
        with self.assertRaisesRegex(cfe.CashFlowError, "HASH_MISMATCH"):
            cfe.build_declaration(result, declared_usd="5000.00", prior_blocks=[])


class DeclarationTests(unittest.TestCase):
    def test_declaration_must_stay_within_the_unexplained_cash_change(self) -> None:
        source = evidence([DEPOSIT])  # +500.00
        for declared in ("500.01", "-0.01", "-500.00"):
            with self.subTest(declared=declared), self.assertRaisesRegex(cfe.CashFlowError, "EXCEEDS_LIMIT"):
                cfe.build_declaration(source, declared_usd=declared, prior_blocks=[])
        source = evidence([WITHDRAWAL])  # -200.00
        for declared in ("-200.01", "0.01"):
            with self.subTest(declared=declared), self.assertRaisesRegex(cfe.CashFlowError, "EXCEEDS_LIMIT"):
                cfe.build_declaration(source, declared_usd=declared, prior_blocks=[])
        with self.assertRaisesRegex(cfe.CashFlowError, "AMOUNT_INVALID"):
            cfe.build_declaration(source, declared_usd="-200.001", prior_blocks=[])
        with self.assertRaisesRegex(cfe.CashFlowError, "EXCEEDS_LIMIT"):
            cfe.build_declaration(evidence([DIVIDEND, BUY]), declared_usd="42.50", prior_blocks=[])  # not a cash flow

    def test_statuses(self) -> None:
        source = evidence([DEPOSIT, DIVIDEND, BUY])
        full = cfe.build_declaration(source, declared_usd="500.00", prior_blocks=[])
        self.assertEqual((full["declaration_status"], full["hwm_adjustment_usd"], full["undeclared_remainder_usd"]),
                         ("DECLARED_IN_FULL", "500.00", "0.00"))
        self.assertEqual(full["excluded_from_cash_flow"],
                         {"dividend_settlement_usd": "42.50", "fees_usd": "2.70", "taxes_usd": "7.50"})
        partial = cfe.build_declaration(source, declared_usd="300.00", prior_blocks=[])
        self.assertEqual((partial["declaration_status"], partial["hwm_adjustment_usd"], partial["undeclared_remainder_usd"]),
                         ("PARTIALLY_DECLARED", None, "200.00"))
        missing = cfe.build_declaration(source, declared_usd=None, prior_blocks=[])
        self.assertEqual((missing["declaration_status"], missing["declared_cash_flow_usd"]), ("UNDECLARED", None))
        none = cfe.build_declaration(evidence([DIVIDEND, BUY, SELL]), declared_usd=None, prior_blocks=[])
        self.assertEqual((none["declaration_status"], none["declared_cash_flow_usd"], none["hwm_adjustment_usd"]),
                         ("NO_EXTERNAL_FLOW", "0.00", "0.00"))
        unresolved = evidence([dict(DEPOSIT, rmrk_nm="입금취소출금")])
        block = cfe.build_declaration(unresolved, declared_usd=None, prior_blocks=[])
        self.assertEqual(block["declaration_status"], "EVIDENCE_UNRESOLVED")
        with self.assertRaisesRegex(cfe.CashFlowError, "BLOCKED_BY_UNRESOLVED_EVIDENCE"):
            cfe.build_declaration(unresolved, declared_usd="0.00", prior_blocks=[])
        for item in (full, partial, missing, none, block):
            self.assertEqual(validate_instance(item, DECLARATION_SCHEMA), [])
            self.assertEqual(cfe.declaration_block_errors(item), [])
            self.assertEqual((item["order_authority"], item["quantity_authority"]), (False, "none"))

    def test_rows_already_declared_are_not_counted_twice(self) -> None:
        first = cfe.build_declaration(evidence([DEPOSIT]), declared_usd="500.00", prior_blocks=[])
        later_rows = raw_history([DEPOSIT, dict(WITHDRAWAL, deal_dt="20261005")])
        later = cfe.normalize_transaction_history(later_rows, period_from="2026-10-02", period_to="2026-10-06",
                                                  raw_sha256="b" * 64)
        second = cfe.build_declaration(later, declared_usd="-200.00", prior_blocks=[first])
        self.assertEqual((second["previously_counted_keys"], second["new_external_net_usd"]),
                         (["2026-10-02:000000001"], "-200.00"))
        # A prior block that was not declared in full does not count, so its rows are still open.
        undeclared = cfe.build_declaration(evidence([DEPOSIT]), declared_usd=None, prior_blocks=[])
        third = cfe.build_declaration(later, declared_usd=None, prior_blocks=[undeclared])
        self.assertEqual((third["previously_counted_keys"], third["new_external_net_usd"]), ([], "300.00"))

    def test_hand_edited_block_is_inconsistent(self) -> None:
        block = cfe.build_declaration(evidence([DEPOSIT]), declared_usd="500.00", prior_blocks=[])
        edits = {
            "CASH_FLOW_DECLARATION_EXCEEDS_LIMIT": {"declared_cash_flow_usd": "900.00"},
            "CASH_FLOW_DECLARATION_NET_INCONSISTENT": {"new_external_net_usd": "900.00"},
            "CASH_FLOW_DECLARATION_STATUS_INCONSISTENT": {"declaration_status": "NO_EXTERNAL_FLOW"},
            "CASH_FLOW_DECLARATION_ADJUSTMENT_INCONSISTENT": {"hwm_adjustment_usd": "100.00"},
            "CASH_FLOW_DECLARATION_REMAINDER_INCONSISTENT": {"undeclared_remainder_usd": "1.00"},
            "CASH_FLOW_DECLARATION_KEYS_INCONSISTENT": {"previously_counted_keys": ["2026-01-01:x"]},
            "CASH_FLOW_DECLARATION_SCHEMA_VERSION": {"schema_version": "0"},
        }
        for code, change in edits.items():
            with self.subTest(code=code):
                self.assertEqual(cfe.declaration_block_errors(dict(block, **change)), [code])

    def test_chain_requires_contiguous_coverage_up_to_the_reconciliation_date(self) -> None:
        clear = cfe.build_declaration(evidence([], period=("2026-10-01", "2026-10-03")), declared_usd=None,
                                      prior_blocks=[])
        gap = cfe.build_declaration(evidence([], period=("2026-10-06", "2026-10-07")), declared_usd=None,
                                    prior_blocks=[])
        short = cfe.build_declaration(evidence([], period=("2026-10-04", "2026-10-06")), declared_usd=None,
                                      prior_blocks=[])

        def chain(*items):
            return cfe.cash_flow_chain(
                [{"as_of": as_of, "state_revision": index + 2, "block": block, "post_activation": True}
                 for index, (as_of, block) in enumerate(items)], start_date="2026-10-01")

        result = chain(("2026-10-03", clear), ("2026-10-07", gap))
        self.assertEqual([step["status"] for step in result["steps"]], ["CLEAR", "HOLD"])
        self.assertEqual(result["steps"][1]["reasons"], ["CASH_FLOW_COVERAGE_GAP"])
        self.assertEqual((result["hold_active"], result["hold_from"], result["covered_through"]),
                         (True, "2026-10-07", "2026-10-03"))
        result = chain(("2026-10-03", clear), ("2026-10-07", short))
        self.assertEqual(result["steps"][1]["reasons"], ["CASH_FLOW_COVERAGE_ENDS_BEFORE_AS_OF"])
        result = chain(("2026-10-03", clear), ("2026-10-06", short))
        self.assertEqual(([step["status"] for step in result["steps"]], result["hold_active"]), (["CLEAR", "CLEAR"], False))
        result = chain(("2026-10-03", None))
        self.assertEqual(result["steps"][0]["reasons"], ["CASH_FLOW_EVIDENCE_MISSING"])
        before_activation = cfe.cash_flow_chain(
            [{"as_of": "2026-09-30", "state_revision": 1, "block": None, "post_activation": False}],
            start_date="2026-10-01")
        self.assertEqual((before_activation["steps"][0]["status"], before_activation["hold_active"]),
                         ("NOT_REQUIRED", False))


class ReconciliationIntegrationTests(TempStateCase):
    def test_proposal_without_a_declaration_is_unchanged(self) -> None:
        now = datetime.now(timezone.utc)
        results = account_results(utc(now))
        plain = make_proposal(base_state(), now=now, results=results)
        same = make_proposal(base_state(), now=now, results=results, cash_flow_declaration=None)
        self.assertNotIn("cash_flow_declaration", plain)
        self.assertEqual(plain, same)

    def test_declaration_is_part_of_the_hash_and_gets_a_new_code(self) -> None:
        now = datetime.now(timezone.utc)
        results = account_results(utc(now))
        source = evidence([DEPOSIT])
        plain = make_proposal(base_state(), now=now, results=results)
        undeclared = make_proposal(base_state(), now=now, results=results,
                                   cash_flow_declaration=cfe.build_declaration(source, declared_usd=None, prior_blocks=[]))
        declared = make_proposal(base_state(), now=now, results=results,
                                 cash_flow_declaration=cfe.build_declaration(source, declared_usd="500.00", prior_blocks=[]))
        codes = {plain["confirm_code"], undeclared["confirm_code"], declared["confirm_code"]}
        self.assertEqual(len(codes), 3)
        for proposal in (undeclared, declared):
            self.assertEqual(validate_instance(proposal, PROPOSAL_SCHEMA), [])
            self.assertEqual((proposal["order_authority"], proposal["quantity_authority"]), (False, "none"))
        self.assertEqual(plain["proposed_patch"], declared["proposed_patch"])  # no state value depends on it

    def test_apply_records_the_declaration_in_the_ledger_only(self) -> None:
        state = base_state()
        self.write_state(state)
        block = cfe.build_declaration(evidence([DEPOSIT]), declared_usd="500.00", prior_blocks=[])
        proposal = make_proposal(state, cash_flow_declaration=block)
        self.apply(proposal)
        ledger = self.directory / "reconciliation_ledger.jsonl"
        entry = json.loads(ledger.read_bytes().splitlines()[-1])
        self.assertEqual(entry["cash_flow_declaration"], block)
        written = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(set(written), set(state))  # no new state field
        self.assertNotIn("cash_flow", json.dumps(written))
        self.assertEqual(cfe.read_ledger_blocks(ledger), [block])
        # The next reconciliation without a declaration keeps the old entry shape.
        follow = make_proposal(written, results=account_results(utc(datetime.now(timezone.utc)), deposit=[{
            "crnc_code": "USD", "fc_pymn_alowa": "10", "fc_ord_alowa": "20"}]))
        self.audit_path = self.directory / "apply_audit_2.json"
        self.apply(follow)
        self.assertNotIn("cash_flow_declaration", json.loads(ledger.read_bytes().splitlines()[-1]))
        self.assertEqual(cfe.read_ledger_blocks(ledger), [block])

    def test_apply_rejects_an_inconsistent_declaration_and_writes_nothing(self) -> None:
        state = base_state()
        original = self.write_state(state)
        block = cfe.build_declaration(evidence([DEPOSIT]), declared_usd="500.00", prior_blocks=[])
        proposal = make_proposal(state, cash_flow_declaration=block)
        tampered = copy.deepcopy(proposal)
        tampered["cash_flow_declaration"]["declared_cash_flow_usd"] = "900.00"
        with self.assertRaisesRegex(ValueError, "BROKER_PROPOSAL_INTEGRITY_MISMATCH"):
            self.apply(tampered, self.confirmation(proposal))
        rehash(tampered)  # even with a recomputed hash and its own code, the block itself is rejected
        with self.assertRaisesRegex(ValueError, "CASH_FLOW_DECLARATION_INVALID: CASH_FLOW_DECLARATION_EXCEEDS_LIMIT"):
            self.apply(tampered)
        unknown = rehash(dict(copy.deepcopy(proposal), cash_flow_declaration=dict(block, extra_field=1)))
        with self.assertRaisesRegex(ValueError, "BROKER_PROPOSAL_SCHEMA_INVALID"):
            self.apply(unknown)
        self.assert_nothing_written(original)


class ReconcileCliTests(TempStateCase):
    def setUp(self) -> None:
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
        self.original = self.write_state(base_state())
        self.evidence_path = self.directory / "cash_flow_evidence.json"
        self.evidence_path.write_text(json.dumps(evidence([DEPOSIT, DIVIDEND]), ensure_ascii=False), encoding="utf-8")
        self.calls = 0

    def propose(self, *extra: str) -> tuple[int, str]:
        def reader(requests, *, runtime, policy):
            self.calls += 1
            self.assertEqual([item["operation"] for item in requests], list(ALL_OPERATIONS))
            return account_results(utc(datetime.now(timezone.utc)))
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main([
                "propose", "--readonly-policy", str(self.policies["readonly"]), "--rate-policy",
                str(self.policies["rate"]), "--broker-policy", str(self.policies["broker"]), "--alert-policy",
                str(self.policies["alert"]), "--portfolio-state", str(self.state_path), "--output-root",
                str(self.output_root), *extra], reader=reader)
        return code, output.getvalue()

    def show(self) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            cli.main(["show", "--output-root", str(self.output_root)])
        return output.getvalue()

    def test_undeclared_then_declared_proposals_have_different_codes(self) -> None:
        code, _ = self.propose("--cash-flow-evidence", str(self.evidence_path))
        self.assertEqual(code, 0)
        first = load_json(cli.resolve_proposal_path("latest", self.output_root))
        self.assertEqual(first["cash_flow_declaration"]["declaration_status"], "UNDECLARED")
        shown = self.show()
        self.assertIn("입출금 신고(S5): 미신고", shown)
        self.assertIn("배당 42.50 USD", shown)
        code, _ = self.propose("--cash-flow-evidence", str(self.evidence_path), "--declare-cash-flow-usd", "500.00")
        self.assertEqual(code, 0)
        second = load_json(cli.resolve_proposal_path("latest", self.output_root))
        self.assertEqual(second["cash_flow_declaration"]["declaration_status"], "DECLARED_IN_FULL")
        self.assertNotEqual(first["confirm_code"], second["confirm_code"])
        self.assertIn("입출금 신고(S5): 500.00 USD 신고", self.show())
        self.assertEqual(self.state_path.read_bytes(), self.original)
        self.assertFalse((self.directory / "reconciliation_ledger.jsonl").exists())

    def test_over_limit_or_evidence_less_declaration_is_rejected_before_any_broker_read(self) -> None:
        for extra in (("--cash-flow-evidence", str(self.evidence_path), "--declare-cash-flow-usd", "542.50"),
                      ("--declare-cash-flow-usd", "500.00"),
                      ("--cash-flow-evidence", str(self.directory / "missing.json"))):
            with self.subTest(extra=extra):
                code, output = self.propose(*extra)
                self.assertEqual(code, 2)
                self.assertIn("입출금 신고를 받을 수 없습니다", output)
        self.assertEqual(self.calls, 0)
        self.assertFalse(self.output_root.exists())
        self.assertEqual(self.state_path.read_bytes(), self.original)

    def test_without_the_new_options_nothing_changes(self) -> None:
        code, _ = self.propose()
        self.assertEqual(code, 0)
        self.assertNotIn("cash_flow_declaration", load_json(cli.resolve_proposal_path("latest", self.output_root)))
        self.assertNotIn("입출금 신고", self.show())

    def test_normalize_cli_writes_sanitized_evidence_once(self) -> None:
        raw_path = self.directory / "raw.json"
        raw_path.write_text(json.dumps(raw_history([DEPOSIT]), ensure_ascii=False), encoding="utf-8")
        target = self.directory / "normalized.json"
        arguments = ["normalize", "--raw", str(raw_path), "--from", "2026-10-01", "--to", "2026-10-05",
                     "--output", str(target)]
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cfe.main(arguments), 0)
            self.assertEqual(cfe.main(arguments), 2)  # create-only
        self.assertNotIn(ACCOUNT_LABEL, target.read_text(encoding="utf-8"))
        self.assertNotIn(ACCOUNT_LABEL, output.getvalue())
        self.assertEqual(cfe.evidence_errors(load_json(target)), [])


if __name__ == "__main__":
    unittest.main()
