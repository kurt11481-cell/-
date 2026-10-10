"""Redesign T1: auto-core reconciliation (F1-F6) under invariants I1-I5.

All account data is synthetic (TEST_ONLY). No network, no Kiwoom runtime, no kiwoomcli, and every
state, ledger and output path is a temporary directory.
"""

from __future__ import annotations

import ast
import copy
import json
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))

import apply_user_confirmed_broker_snapshot as apply_module  # noqa: E402
import auto_core  # noqa: E402
import auto_core_reconcile as core  # noqa: E402
import cash_flow_evidence as cfe  # noqa: E402
import kiwoom_account_readonly_bridge as bridge  # noqa: E402
import reconcile_broker_state as cli  # noqa: E402
from kiwoom_broker_shadow import (  # noqa: E402
    NEVER_TOUCHED_FIELDS, normalize_snapshot, proposal_content_hash, reconciliation_proposal,
)
from kiwoom_runtime_bridge import BridgeError, blocked_api_target  # noqa: E402
from manual_data_guards import compare_broker_and_system, normalize_broker_state  # noqa: E402
from validation_common import canonical_hash, load_json, validate_instance  # noqa: E402

SCHEMAS = ROOT / "manage-us-stock-strategy/schemas"
PROPOSAL_SCHEMA = SCHEMAS / "kiwoom-reconciliation-proposal.schema.json"
# Wednesday 2026-10-14 06:15 KST; the last record was the previous run, Tuesday 06:20 KST.
NOW = datetime(2026, 10, 13, 21, 15, tzinfo=timezone.utc)
RECORD = "2026-10-12T21:20:00Z"
SELL = "매도"  # 매도
BUY = "매수"  # 매수
DEPOSIT_KIND, DEPOSIT_MEMO = "입출금", "외화입금"  # 입출금, 외화입금
DIVIDEND_MEMO = "배당금(외화)입금"  # 배당금(외화)입금
TRADE_KIND = "매매"
COMMIT = "a" * 40
# Pending sale of sale_broker: AAA 3 x 110 (U.S. 10/13 session) settles on KST 10/15, proceeds after fees.
SALE_PENDING = {"d1_setl_dt": "20261015", "d1_usd_sell_excta": "329.17", "d1_usd_buy_excta": "0.00",
                "d2_setl_dt": "20261016", "d2_usd_sell_excta": "0.00", "d2_usd_buy_excta": "0.00"}


def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class GitDone:
    """A finished git command (stdout and return code) for git_provenance's runner."""

    def __init__(self, stdout, code=0):
        self.stdout, self.returncode = stdout, code


def fake_git(status_text):
    outputs = iter([GitDone(COMMIT + "\n"), GitDone(status_text)])
    return lambda *args, **kwargs: next(outputs)


def holding(ticker, held, settled=None, cost="100"):
    settled = held if settled is None else settled
    return {"stex_nm": "TEST", "crnc_code": "USD", "stk_cd": ticker, "frgn_stk_nm": "TEST_ONLY",
            "qty": str(settled), "poss_qty": str(held), "sell_alowq": str(held), "frgn_stk_book_uv": cost,
            "now_pric": "1", "evlt_amt": "0", "pl_amt": "0", "pl_rt": "0"}


def fill(ticker, side, quantity, price, *, order_no="0001", ord_time="21:30:00", cntr_time="05:00:01"):
    return {"ord_no": order_no, "crnc_code": "USD", "stk_cd": ticker, "slby_tp_nm": side, "frgn_trde_tp": "LOC",
            "ord_qty": f"{quantity:012d}", "cntr_qty": f"{quantity:012d}", "cncl_qty": "000000000000",
            "ord_remnq": "000000000000", "ord_uv": price, "cntr_uv": price, "ord_time": ord_time,
            "cntr_time": cntr_time, "ord_stat_nm": "TEST", "rsrv_tp": "0"}


def day_trade(ticker, *, bought=0, buy_amount="0", sold=0, sell_amount="0", fees="0"):
    return {"stk_cd": ticker, "tdy_buyq": f"{bought:015d}", "tdy_buy_amt": buy_amount, "tdy_avg_buy_uv": "0",
            "tdy_sellq": f"{sold:015d}", "tdy_sell_amt": sell_amount, "tdy_avg_sell_uv": "0", "cmsn_altx": fees}


def history_row(day, number, kind, memo, amount, clock="13:33:34", currency="USD"):
    return {"deal_dt": day, "deal_no": number, "deal_kind_nm": kind, "rmrk_nm": memo, "crnc_code": currency,
            "stk_cd": "", "deal_qty": "0", "uv_exrt": "0", "fc_deal_amt": amount, "fc_cmsn": "0",
            "fc_deal_tax": "0", "frgn_pay_txam": "0", "fc_exct_amt": amount, "proc_time": clock}


def trade_row(day, number, ticker, side, quantity, gross, fee, settled, clock="08:07:37"):
    """A settled fill in the transaction history: fc_exct_amt is the settled amount with the actual fee."""
    return {"deal_dt": day, "deal_no": number, "deal_kind_nm": TRADE_KIND, "rmrk_nm": side, "crnc_code": "USD",
            "stk_cd": ticker, "deal_qty": str(quantity), "uv_exrt": "0", "fc_deal_amt": gross, "fc_cmsn": fee,
            "fc_deal_tax": "0", "frgn_pay_txam": "0", "fc_exct_amt": settled, "proc_time": clock}


class FakeBroker:
    """Synthetic sanitized bridge results; validates every request exactly as the real bridge does."""

    def __init__(self, *, holdings, ord_cash, pymn_cash, fills=None, day_trades=None, history=None,
                 open_items=None, failing=None, retrieved=None, detail=None):
        self.holdings, self.ord_cash, self.pymn_cash = holdings, ord_cash, pymn_cash
        self.fills = fills or {}
        self.day_trades = day_trades or {}
        self.history = history or []
        self.open_items = open_items or []
        self.failing = failing or {}
        self.retrieved = retrieved or (NOW - timedelta(seconds=5))
        self.detail = detail if detail is not None else {"d1_usd_sell_excta": "0"}
        self.requests: list[dict] = []

    def data(self, request):
        operation, params = request["operation"], request.get("params") or {}
        return {
            "account_deposit_read": [{"crnc_code": "USD", "crnc_nm": "TEST", "fc_entra": self.pymn_cash,
                                      "fc_pymn_alowa": self.pymn_cash, "fc_ord_alowa": self.ord_cash}],
            "account_deposit_detail_read": [dict(self.detail)],
            "account_holdings_read": self.holdings, "account_open_items": self.open_items,
            "account_fills_read": [], "account_realized_pnl_read": [],
            "account_daily_fills_read": self.fills.get(params.get("ord_dt"), []),
            "account_day_trades_read": self.day_trades.get(params.get("base_dt"), []),
            "account_transaction_history_read": self.history,
        }[operation]

    def __call__(self, requests, *, runtime, policy):
        results = []
        for request in requests:
            validated = bridge.validate_request(request)
            self.requests.append(validated)
            operation = validated["operation"]
            key = (operation, json.dumps(validated.get("params"), sort_keys=True))
            if operation in self.failing or key in self.failing:
                result = {"bridge_status": "KIWOOM_API_RESPONSE_ERROR", "failure_type": "API_RESPONSE_ERROR",
                          "operation": operation, "provider_return_code": 20, "no_data_declared": True,
                          "runtime_commit": None, "retrieved_at": None, "data": [], "order_authority": False}
            else:
                result = {"bridge_status": "PASS", "operation": operation, "data": self.data(validated),
                          "pagination": {"api_id": bridge.ACCOUNT_APIS[operation][0], "pages": 1, "exhausted": True,
                                         "complete": True, "secret_fields_retained": False},
                          "runtime_commit": "c" * 40, "retrieved_at": utc(self.retrieved),
                          "account_identifier_stored": False, "portfolio_mutation": False,
                          "quantity_authority": "none", "order_authority": False}
            if "params" in validated:
                result["request_params"] = dict(validated["params"])
            results.append(result)
        return results


class FrozenClock(datetime):
    """The apply library's real clock, fixed at the run's time: a proposal expires 15 minutes after its read,
    so the synthetic dates never depend on the day the tests run."""
    moment = NOW

    @classmethod
    def now(cls, tz=None):
        return cls.moment if tz is None else cls.moment.astimezone(tz)


def empty_block(period_from="2026-10-12", period_to="2026-10-13"):
    evidence = cfe.normalize_transaction_history({"return_code": 0, "result_list": []}, period_from=period_from,
                                                 period_to=period_to, raw_sha256="0" * 64)
    return cfe.build_declaration(evidence, declared_usd=None, prior_blocks=[])


def base_state():
    return {
        "schema_version": "1.3", "strategy_version": "TEST-ONLY", "state_revision": 30, "state_status": "TEST_ONLY",
        "strategy_mode": "TEST_ONLY", "last_updated_at": "2026-10-13T06:21:00+09:00",
        "last_confirmed_broker_snapshot": {
            "verified": True, "authority_state": "VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT",
            "source": "KIWOOM_READONLY_API", "scope": "HOLDINGS_AND_AVAILABLE_CASH", "as_of": "2026-10-12",
            "as_of_timestamp": RECORD, "holdings_complete": True, "cash_verified": True,
            "cash_verified_scope": "available_cash_only", "open_orders_verified": True,
            "account_identifier_stored": False},
        "holdings": {"AAA": 10, "BBB": 5}, "average_cost_usd": {"AAA": 100.0, "BBB": 100.0},
        "position_cost_basis_usd": {"AAA": 1000.0, "BBB": 500.0}, "aggregate_cost_basis_usd": 1500.0,
        "broker_display_snapshot": {"quote_status": "TEST_ONLY"}, "brokerage_cash_usd": None,
        "available_cash_usd": 1000.0, "cash_pct_estimate": None, "current_stage": "TEST_STAGE",
        "confirmed_trades": [{"trade_id": "TEST-1"}], "unreconciled_holding_changes": [],
        "holding_change_reconciliations": [], "pending_candidates": [{"symbol": "ZZZ"}],
        "timing_plan": {"positions": {"AAA": {"anchor_shares": 10}}}, "state_notes": ["TEST_ONLY"],
        "archived_prior_strategy": {"reason": "TEST_ONLY"},
    }


class Workspace(unittest.TestCase):
    """Temporary state, ledger (one entry binding the state), policies and output folders."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state_path = self.root / "portfolio_state.json"
        self.ledger_path = self.root / "reconciliation_ledger.jsonl"
        self.output_root = self.root / "auto-core"
        self.evidence_root = self.root / "evidence"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.policies = {}
        for name, value in (("readonly", {"official_runtime_path": str(self.runtime),
                                          "token_profile_alias": "TEST_PROFILE"}), ("rate", {}),
                            ("broker", {"maximum_age_seconds": 900}), ("alert", {})):
            path = self.root / f"{name}.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            self.policies[name] = path
        self.policies["state"] = self.state_path
        self.policies["journal"] = self.root / "missing_journal.json"
        self.config_path = self.root / "auto_core.json"
        # R2-2: the human-path record's proposal (and through it its snapshot) is found under these roots.
        self.proposal_root = self.root / "reconciliation"
        roots = mock.patch.object(core, "BASELINE_SEARCH_ROOTS", (self.proposal_root, self.output_root))
        roots.start()
        self.addCleanup(roots.stop)
        FrozenClock.moment = NOW
        clock = mock.patch.object(apply_module, "datetime", FrozenClock)
        clock.start()
        self.addCleanup(clock.stop)
        self.write_state(base_state(), block=empty_block())

    def write_state(self, state, *, block=None, snapshot_broker=None):
        """State, its broker snapshot and proposal (human path), and one ledger entry binding them.

        The snapshot is read at the record time and generated one second later; by default it holds the
        state's holdings and an order-available amount equal to the state's cash.
        """
        record = state["last_confirmed_broker_snapshot"]
        read_at = datetime.fromisoformat(record["as_of_timestamp"].replace("Z", "+00:00"))
        broker = snapshot_broker or FakeBroker(
            holdings=[holding(ticker, quantity) for ticker, quantity in state["holdings"].items()],
            ord_cash=f"{state['available_cash_usd']:.2f}", pymn_cash=f"{state['available_cash_usd']:.2f}")
        broker.retrieved = read_at
        results = broker([{"operation": operation} for operation in core.SNAPSHOT_OPERATIONS], runtime=None, policy={})
        snapshot = normalize_snapshot(results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT",
                                      generated_at=utc(read_at + timedelta(seconds=1)), maximum_age_seconds=900)
        folder = self.proposal_root / read_at.strftime("%Y%m%dT%H%M%SZ")
        folder.mkdir(parents=True, exist_ok=True)
        self.baseline_snapshot_path = folder / "kiwoom_broker_snapshot.shadow.json"
        self.baseline_snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        proposal_id = canonical_hash({"test_proposal": snapshot["snapshot_hash"]})
        (folder / "reconciliation_proposal.json").write_text(json.dumps({
            "proposal_id": proposal_id, "source": {"snapshot_path": str(self.baseline_snapshot_path),
                                                   "snapshot_hash": snapshot["snapshot_hash"]}}), encoding="utf-8")
        record["evidence_sha256"] = snapshot["snapshot_hash"]
        text = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        self.state_path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        entry = {"schema_version": "1.0", "event": "APPLY", "proposal_schema_version": "kiwoom-reconciliation-1.0",
                 "proposal_id": proposal_id, "bundle_id": "KIWOOM-" + snapshot["snapshot_hash"][:20],
                 "state_revision_before": state["state_revision"] - 1, "state_revision_after": state["state_revision"],
                 "portfolio_hash_before": "b" * 64, "portfolio_hash_after": canonical_hash(state), "changes": [],
                 "confirmation_method": "USER_TERMINAL", "confirmed_at": "2026-10-12T21:21:00+00:00",
                 "previous_entry_sha256": apply_module.GENESIS_LEDGER_HASH}
        if block is not None:
            entry["cash_flow_declaration"] = block
        self.ledger_path.write_bytes(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
        return snapshot

    def config(self, mode="compare", kill_switch=False):
        value = {"mode": mode, "kill_switch": kill_switch, "compare_days_required": 3, "schedule_kst": "06:15",
                 "symbols_extra": ["SOXX"]}
        self.config_path.write_text(json.dumps(value), encoding="utf-8")
        return value

    def auto(self, broker, *, mode="compare", kill_switch=False, now=NOW, day=None, baseline=None,
             provenance=None, config=True, previous_run=None, provenance_source=None):
        config_value, reasons = (self.config(mode, kill_switch), []) if config else (None, ["AUTO_CORE_CONFIG_MISSING"])
        provenance = provenance or {"status": "OK", "commit_sha": COMMIT, "dirty_paths": [], "guarded_dirty_paths": []}
        FrozenClock.moment = now
        return cli.reconcile_auto(
            config=config_value, config_reasons=reasons, provenance=provenance,
            output_directory=self.output_root / (day or "2026-10-14"), compare_baseline=baseline,
            readonly_policy_path=self.policies["readonly"], rate_policy_path=self.policies["rate"],
            broker_policy_path=self.policies["broker"], alert_policy_path=self.policies["alert"],
            state_path=self.state_path, journal_path=self.policies["journal"], reader=broker,
            now=lambda: now, evidence_root=self.evidence_root, previous_run=previous_run,
            config_path=self.config_path, provenance_source=provenance_source or (lambda: dict(provenance)))

    def snapshot_files(self):
        return self.state_path.read_bytes(), self.ledger_path.read_bytes()

    def ledger_entries(self):
        return [json.loads(line) for line in self.ledger_path.read_bytes().splitlines() if line.strip()]


def sale_broker(**changes):
    """AAA 3 shares sold at 110 on the U.S. 10/13 session (KST 10/14 05:00); settles KST 10/15 for 329.17."""
    values = dict(
        holdings=[holding("AAA", 7, settled=10), holding("BBB", 5)], ord_cash="1329.17", pymn_cash="1000.00",
        fills={"20261013": [fill("AAA", SELL, 3, "110.0000")]},
        day_trades={"20261013": [day_trade("AAA", sold=3, sell_amount="330.00", fees="0.83")]},
        detail=dict(SALE_PENDING))
    values.update(changes)
    return FakeBroker(**values)


def settled_sale_broker(moment, **changes):
    """sale_broker after KST 10/15 08:07: the sale is a transaction-history trade row, nothing is pending."""
    values = dict(holdings=[holding("AAA", 7), holding("BBB", 5)], pymn_cash="1329.17", detail={},
                  history=[trade_row("20261015", "000000001", "AAA", SELL, 3, "330.00", "0.83", "329.17")],
                  retrieved=moment - timedelta(seconds=5))
    values.update(changes)
    return sale_broker(**values)


# ---------------------------------------------------------------------------------------------
# F1 cash = order-available amount
# ---------------------------------------------------------------------------------------------

class CashDefinitionTests(unittest.TestCase):
    def proposal(self, holdings, ord_cash, pymn_cash):
        broker = FakeBroker(holdings=holdings, ord_cash=ord_cash, pymn_cash=pymn_cash)
        results = broker([{"operation": operation} for operation in core.SNAPSHOT_OPERATIONS], runtime=None, policy={})
        snapshot = normalize_snapshot(results, snapshot_role="POST_CLOSE_BROKER_SNAPSHOT", generated_at=utc(NOW),
                                      maximum_age_seconds=900)
        proposal = reconciliation_proposal(snapshot, base_state(), results=results, maximum_age_seconds=900,
                                           post_apply_check=lambda state, draft: {"status": "PASS", "errors": []})
        self.assertEqual(validate_instance(proposal, PROPOSAL_SCHEMA), [])
        return proposal

    def test_filled_sale_before_settlement_passes_with_order_available_cash(self):
        proposal = self.proposal([holding("AAA", 7, settled=10), holding("BBB", 5)], "1329.17", "1000.00")
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")
        self.assertEqual(proposal["proposed_patch"]["available_cash_usd"], 1329.17)
        self.assertEqual(proposal["cash_semantics"]["available_cash_usd_basis"], "KIWOOM_ORDER_AVAILABLE_USD")
        self.assertTrue(proposal["cash_semantics"]["unsettled_funds_included"])
        self.assertEqual(proposal["cash_components"], {"deposit": 1000.0, "withdrawable": 1000.0,
                                                       "order_available": 1329.17, "unsettled_component": 329.17})

    def test_proceeds_without_a_sold_quantity_block(self):
        proposal = self.proposal([holding("AAA", 10), holding("BBB", 5)], "1329.17", "1000.00")
        self.assertEqual(proposal["status"], "BLOCKED")
        self.assertIn("CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS", proposal["unresolved_fields"])
        self.assertEqual(proposal["proposed_patch"], {})

    def test_order_available_below_withdrawable_blocks(self):
        proposal = self.proposal([holding("AAA", 10), holding("BBB", 5)], "998.99", "1000.00")
        self.assertIn("CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE", proposal["unresolved_fields"])
        self.assertEqual(proposal["status"], "BLOCKED")

    def test_one_dollar_boundaries(self):
        self.assertEqual(self.proposal([holding("AAA", 10)], "1001.00", "1000.00")["status"],
                         "USER_CONFIRMATION_REQUIRED")
        self.assertEqual(self.proposal([holding("AAA", 10)], "1001.01", "1000.00")["status"], "BLOCKED")
        self.assertEqual(self.proposal([holding("AAA", 10)], "999.00", "1000.00")["status"],
                         "USER_CONFIRMATION_REQUIRED")
        self.assertEqual(self.proposal([holding("AAA", 10)], "998.99", "1000.00")["status"], "BLOCKED")

    def test_deposit_is_never_compared(self):
        # fc_entra far below order-available (10/10 measurement) does not block.
        proposal = self.proposal([holding("AAA", 7, settled=10)], "4072.50", "1000.00")
        self.assertEqual(proposal["status"], "USER_CONFIRMATION_REQUIRED")

    def test_expected_proceeds_field_stays_zero(self):
        for name in ("continuous_improvement_sidecar.py", "portfolio_reallocation_shadow.py"):
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertRegex(text, r'"verified_orderable_cash_from_expected_proceeds_usd":\s*0')

    def test_dashboard_funding_cap_still_uses_the_settled_minimum(self):
        text = (SCRIPTS / "portfolio_decision_dashboard.py").read_text(encoding="utf-8")
        self.assertIn('.get("settled_available_cash")', text)

    def test_manual_comparison_uses_order_available_cash_only_when_the_check_passes(self):
        def compare(holdings, ord_cash, pymn_cash, system_cash):
            broker = FakeBroker(holdings=holdings, ord_cash=ord_cash, pymn_cash=pymn_cash)
            results = broker([{"operation": operation} for operation in core.SNAPSHOT_OPERATIONS], runtime=None,
                             policy={})
            state, _ = normalize_broker_state(results, observed_at=utc(NOW), maximum_age_seconds=900)
            system = {"holdings": {row["stk_cd"]: int(row["poss_qty"]) for row in holdings},
                      "average_cost_usd": {row["stk_cd"]: 100.0 for row in holdings}, "available_cash_usd": system_cash}
            return compare_broker_and_system(state, system)
        self.assertEqual(compare([holding("AAA", 7, settled=10)], "1329.17", "1000.00", 1329.17), ("MATCH", []))
        self.assertEqual(compare([holding("AAA", 7, settled=10)], "1329.17", "1000.00", 1000.0)[0], "DIFFERENT")
        self.assertEqual(compare([holding("AAA", 10)], "1329.17", "1000.00", 1329.17),
                         ("UNKNOWN", ["COMPARISON_FIELD_UNAVAILABLE"]))


# ---------------------------------------------------------------------------------------------
# F2 bridge reads
# ---------------------------------------------------------------------------------------------

class BridgeReadTests(unittest.TestCase):
    def test_dated_reads_take_only_valid_dates(self):
        good = {"operation": "account_transaction_history_read", "params": {"strt_dt": "20261012", "end_dt": "20261014"}}
        self.assertEqual(bridge.validate_request(good), good)
        body = bridge.request_body(bridge.validate_request(good))
        self.assertEqual((body["strt_dt"], body["end_dt"], body["tp"]), ("20261012", "20261014", "0"))
        for bad in ({"operation": "account_daily_fills_read"},
                    {"operation": "account_daily_fills_read", "params": {"ord_dt": "2026-10-13"}},
                    {"operation": "account_daily_fills_read", "params": {"ord_dt": "20261332"}},
                    {"operation": "account_daily_fills_read", "params": {"ord_dt": "20261013", "stk_cd": "AAA"}},
                    {"operation": "account_day_trades_read", "params": {"base_dt": 20261013}},
                    {"operation": "account_transaction_history_read", "params": {"strt_dt": "20261012"}}):
            with self.subTest(bad=bad):
                with self.assertRaises(BridgeError):
                    bridge.validate_request(bad)
        # An undated read keeps its fixed body; parameters never reach it.
        self.assertEqual(bridge.validate_request({"operation": "account_holdings_read", "params": {"x": "1"}}),
                         {"operation": "account_holdings_read"})

    def test_every_account_route_is_a_read_only_inquiry(self):
        from kiwoom_runtime_bridge import BLOCKED_TERMS

        for operation, (api_id, path) in bridge.ACCOUNT_APIS.items():
            self.assertEqual(path, "/api/us/acnt")
            self.assertFalse(any(term in f"{operation} {api_id} {path}".lower() for term in BLOCKED_TERMS))
            self.assertNotIn(api_id, {"ust20000", "ust20001", "ust20002", "ust20003"})
        self.assertTrue(blocked_api_target("ust20000", "/api/us/ordr"))
        self.assertNotIn("acnt_print", json.dumps(bridge.SAFE_FIELDS))

    def test_batch_echoes_the_validated_dates(self):
        class Completed:
            returncode = 0
            stdout = json.dumps({"results": [{"bridge_status": "PASS", "data": [], "retrieved_at": utc(NOW),
                                              "pagination": {"complete": True, "exhausted": True}}]})
        with mock.patch.object(Path, "is_file", return_value=True):
            results = bridge.invoke_account_bridge_batch(
                [{"operation": "account_day_trades_read", "params": {"base_dt": "20261013"}}],
                runtime=Path("offline"), policy={"external_python_relative_path": "python.exe",
                                                 "request_timeout_seconds": 1},
                runner=lambda *args, **kwargs: Completed())
        self.assertEqual(results[0]["request_params"], {"base_dt": "20261013"})


# ---------------------------------------------------------------------------------------------
# F3 evidence and flows
# ---------------------------------------------------------------------------------------------

class EvidenceTests(Workspace):
    def test_period_restarts_on_the_last_covered_day(self):
        self.assertEqual(core.evidence_period_start([empty_block()], "2026-10-01").isoformat(), "2026-10-13")
        self.assertEqual(core.evidence_period_start([], "2026-10-01").isoformat(), "2026-10-01")
        self.assertIsNone(core.evidence_period_start([], None))

    def test_deposit_is_declared_in_full_without_a_person(self):
        broker = sale_broker(ord_cash="1829.17", pymn_cash="1500.00",
                             history=[history_row("20261013", "000000001", DEPOSIT_KIND, DEPOSIT_MEMO, "500.00")])
        result = self.auto(broker)
        self.assertEqual(result["status"], "OK", result["reasons"])
        evidence = result["cash_flow_evidence"]
        self.assertEqual((evidence["declaration_status"], evidence["hwm_adjustment_usd"]), ("DECLARED_IN_FULL", "500.00"))
        self.assertEqual(result["invariants"]["I3"]["flow_cash_usd"], "500.00")
        saved_path = Path(evidence["evidence_path"])
        self.assertEqual(saved_path.parent, self.evidence_root.resolve())
        saved = load_json(saved_path)
        self.assertEqual(saved["source"]["collection"], "AUTO_CORE_BRIDGE_READ")
        self.assertEqual(saved["source"]["pagination_complete"], "VERIFIED_BY_BRIDGE")
        self.assertFalse(saved["account_identifier_stored"])
        self.assertEqual(cfe.evidence_errors(saved), [])

    def test_withdrawal_is_declared_in_full_as_a_negative_flow(self):
        memo = "외화출금"  # 외화출금
        broker = sale_broker(ord_cash="1129.17", pymn_cash="800.00",
                             history=[history_row("20261013", "000000001", DEPOSIT_KIND, memo, "200.00")])
        result = self.auto(broker)
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual((result["cash_flow_evidence"]["declaration_status"],
                          result["cash_flow_evidence"]["hwm_adjustment_usd"]), ("DECLARED_IN_FULL", "-200.00"))
        self.assertEqual(result["invariants"]["I3"]["flows"][0]["classification"], "WITHDRAWAL")

    def test_dividend_is_explained_but_not_an_external_flow(self):
        broker = sale_broker(ord_cash="1341.17", pymn_cash="1012.00",
                             history=[history_row("20261013", "000000001", DEPOSIT_KIND, DIVIDEND_MEMO, "12.00")])
        result = self.auto(broker)
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(result["cash_flow_evidence"]["declaration_status"], "NO_EXTERNAL_FLOW")
        self.assertEqual(result["invariants"]["I3"]["flows"][0]["classification"], "DIVIDEND")

    def test_unclassified_row_holds_and_writes_nothing(self):
        before = self.snapshot_files()
        broker = sale_broker(history=[history_row("20261013", "000000001", "TEST", "TEST_ONLY", "5.00")])
        result = self.auto(broker, mode="apply")
        self.assertEqual(result["status"], "HOLD")
        self.assertTrue(any(reason.startswith("CASH_FLOW_EVIDENCE_UNRESOLVED") for reason in result["reasons"]))
        self.assertIsNone(result["applied"])
        self.assertEqual(self.snapshot_files(), before)

    def test_cli_evidence_shape_is_unchanged(self):
        evidence = cfe.normalize_transaction_history({"return_code": 0, "result_list": []}, period_from="2026-10-12",
                                                     period_to="2026-10-13", raw_sha256="0" * 64)
        self.assertEqual(evidence["source"]["collection"], "COWORK_READ_ONLY_CLI_EVIDENCE_FILE")
        self.assertEqual(evidence["source"]["pagination_complete"], "ASSERTED_BY_COLLECTOR")
        forged = copy.deepcopy(evidence)
        forged["source"]["pagination_complete"] = "VERIFIED_BY_BRIDGE"
        forged["evidence_hash"] = cfe.evidence_content_hash(forged)
        self.assertIn("CASH_FLOW_EVIDENCE_COLLECTION_INCONSISTENT", cfe.evidence_errors(forged))


# ---------------------------------------------------------------------------------------------
# F4 invariants
# ---------------------------------------------------------------------------------------------

class ExplainedChangeTests(Workspace):
    def test_sale_buy_new_ticker_and_full_sale_are_explained(self):
        cases = {
            "sale": sale_broker(),
            "buy": FakeBroker(holdings=[holding("AAA", 10), holding("BBB", 7, settled=5)], ord_cash="899.75",
                              pymn_cash="899.75", fills={"20261013": [fill("BBB", BUY, 2, "50.0000")]},
                              day_trades={"20261013": [day_trade("BBB", bought=2, buy_amount="100.00", fees="0.25")]},
                              detail=dict(SALE_PENDING, d1_usd_sell_excta="0.00", d1_usd_buy_excta="100.25")),
            "new ticker": FakeBroker(
                holdings=[holding("AAA", 10), holding("BBB", 5), holding("CCC", 4, settled=0)], ord_cash="799.50",
                pymn_cash="799.50", fills={"20261013": [fill("CCC", BUY, 4, "50.0000")]},
                day_trades={"20261013": [day_trade("CCC", bought=4, buy_amount="200.00", fees="0.50")]},
                detail=dict(SALE_PENDING, d1_usd_sell_excta="0.00", d1_usd_buy_excta="200.50")),
            "full sale": FakeBroker(
                holdings=[holding("AAA", 10), holding("BBB", 0, settled=5)], ord_cash="1599.00", pymn_cash="1000.00",
                fills={"20261013": [fill("BBB", SELL, 5, "120.0000")]},
                day_trades={"20261013": [day_trade("BBB", sold=5, sell_amount="600.00", fees="1.00")]},
                detail=dict(SALE_PENDING, d1_usd_sell_excta="599.00")),
        }
        for name, broker in cases.items():
            with self.subTest(case=name):
                result = self.auto(broker, day=name.replace(" ", "-"))
                self.assertEqual(result["status"], "OK", result["reasons"])
                self.assertEqual({key: value["status"] for key, value in result["invariants"].items()},
                                 dict.fromkeys(("I1", "I2", "I3", "I4", "I5"), "PASS"))
                self.assertIsNotNone(result["would_apply"])
                self.assertIsNone(result["applied"])
        new = self.auto(cases["new ticker"], day="new-again")
        self.assertIn({"ticker": "CCC", "recorded": 0, "broker": 4, "fills_net": 4}, new["holdings_change"])

    def test_fill_before_the_last_record_is_not_counted_again(self):
        # Order of KST 10/12 filled at KST 10/13 05:00, before the 06:20 record: already in the state.
        broker = FakeBroker(holdings=[holding("AAA", 10), holding("BBB", 5)], ord_cash="1000.00", pymn_cash="1000.00",
                            fills={"20261012": [fill("AAA", SELL, 3, "110.0000")]})
        result = self.auto(broker)
        self.assertEqual(result["invariants"]["I2"]["status"], "PASS", result["reasons"])
        self.assertEqual(result["invariants"]["I2"]["fills_counted"], 0)


class InvariantFailureTests(Workspace):
    def assert_nothing_written(self, broker, code, **kwargs):
        before = self.snapshot_files()
        result = self.auto(broker, mode="apply", **kwargs)
        self.assertEqual(result["status"], "HOLD", result["reasons"])
        self.assertIsNone(result["applied"])
        self.assertIsNone(result["would_apply"])
        self.assertTrue(any(code in reason for reason in result["reasons"]), result["reasons"])
        self.assertEqual(self.snapshot_files(), before)
        self.assertFalse(list((self.root).glob("backups/*")))
        return result

    def test_i1_required_read_failure(self):
        self.assert_nothing_written(sale_broker(failing={"account_deposit_detail_read": True}),
                                    "I1:REQUIRED_READ_NOT_PASS:account_deposit_detail_read")
        result = self.assert_nothing_written(
            sale_broker(failing={("account_daily_fills_read", json.dumps({"ord_dt": "20261013"})): True}),
            "account_daily_fills_read:20261013:KIWOOM_API_RESPONSE_ERROR:20")
        self.assertEqual(result["invariants"]["I2"]["reasons"], ["I1_FAILED"])

    def test_i1_transaction_history_failure_also_stops_the_evidence(self):
        result = self.assert_nothing_written(sale_broker(failing={"account_transaction_history_read": True}),
                                             "account_transaction_history_read")
        self.assertIn("CASH_FLOW_EVIDENCE_NOT_READ", result["reasons"])

    def test_i2_quantity_change_without_a_fill(self):
        broker = sale_broker(fills={}, day_trades={})
        result = self.assert_nothing_written(broker, "I2:QUANTITY_CHANGE_NOT_EXPLAINED_BY_FILLS:AAA")
        self.assertIn("I3", result["invariants"])

    def test_i2_missing_ticker_in_broker_read(self):
        broker = FakeBroker(holdings=[holding("AAA", 10)], ord_cash="1000.00", pymn_cash="1000.00")
        self.assert_nothing_written(broker, "I2:QUANTITY_CHANGE_NOT_EXPLAINED_BY_FILLS:BBB")

    def test_i2_unknown_side_fails_closed(self):
        broker = sale_broker(fills={"20261013": [fill("AAA", "TEST", 3, "110.0000")]})
        self.assert_nothing_written(broker, "FILL_SIDE_UNKNOWN")

    def test_i3_cash_not_explained(self):
        self.assert_nothing_written(sale_broker(ord_cash="1331.20"), "I3:CASH_CHANGE_NOT_EXPLAINED:2.03")

    def test_i3_amount_sources_must_agree(self):
        broker = sale_broker(day_trades={"20261013": [day_trade("AAA", sold=2, sell_amount="330.00", fees="0.83")]})
        self.assert_nothing_written(broker, "FILL_SOURCES_DISAGREE:2026-10-13:AAA")

    def test_i3_open_orders_reserve_cash(self):
        broker = sale_broker(open_items=[{"crnc_code": "USD", "stk_cd": "BBB", "ord_qty": "1", "ord_remnq": "1",
                                          "slby_tp": "2"}])
        self.assert_nothing_written(broker, "I3:OPEN_ORDERS_PRESENT:1")

    def test_i4_state_changed_outside_ledger(self):
        state = base_state()
        state["available_cash_usd"] = 999.0
        text = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        self.state_path.write_bytes(text.encode("utf-8"))
        self.assert_nothing_written(sale_broker(ord_cash="1328.17"), "I4:STATE_CHANGED_OUTSIDE_LEDGER")

    def test_i4_broken_ledger_chain(self):
        entry = json.loads(self.ledger_path.read_bytes())
        entry["previous_entry_sha256"] = "f" * 64
        self.ledger_path.write_bytes(json.dumps(entry).encode("utf-8") + b"\n")
        self.assert_nothing_written(sale_broker(), "I4:LEDGER_INTEGRITY_FAILED")

    def test_i5_other_field_change_blocks(self):
        def preview(state, proposal):
            changed = copy.deepcopy(state)
            changed["timing_plan"] = {}
            return changed
        with mock.patch.object(core, "preview_updated_state", preview):
            self.assert_nothing_written(sale_broker(), "I5:NEVER_TOUCHED_FIELD_CHANGED: timing_plan")

    def test_i3_settlement_outside_the_fee_range(self):
        # Cash moved by exactly the pending amount, but 300.00 cannot be the settlement of a 330.00 sale.
        broker = sale_broker(ord_cash="1300.00", detail=dict(SALE_PENDING, d1_usd_sell_excta="300.00"))
        self.assert_nothing_written(broker, "I3:SETTLEMENT_OUTSIDE_FEE_RANGE:2026-10-15:SELL:-30.00")

    def test_i3_settlement_amount_not_found(self):
        self.assert_nothing_written(sale_broker(detail={}), "I3:SETTLEMENT_AMOUNT_NOT_FOUND:2026-10-13")

    def test_i3_settled_rows_must_carry_the_fill_quantities(self):
        moment = NOW + timedelta(days=2)
        broker = settled_sale_broker(moment, history=[
            trade_row("20261015", "000000001", "AAA", SELL, 2, "330.00", "0.83", "329.17")])
        self.assert_nothing_written(broker, "I3:SETTLEMENT_QUANTITY_MISMATCH:2026-10-15", now=moment)


# ---------------------------------------------------------------------------------------------
# T1 r2: actual settlement amounts (R2-1), broker-to-broker baseline (R2-2), measured no-data and
# invalid-order rows (R2-3). Numbers are the Cowork measurements M1-M8 of 2026-10-10 (no live call).
# ---------------------------------------------------------------------------------------------

M8_RECORD = "2026-10-09T23:52:04.178310Z"  # rev 24 record: KST 10/10 08:52, after the SOXL sale fill
M1_DETAIL = {"d1_setl_dt": "20261012", "d1_usd_sell_excta": "0.00", "d1_usd_buy_excta": "0.00",
             "d2_setl_dt": "20261013", "d2_usd_sell_excta": "3072.51", "d2_usd_buy_excta": "0.00"}
M1_READ = datetime(2026, 10, 10, 2, 0, tzinfo=timezone.utc)  # KST 10/10 11:00


def m8_state():
    """Rev 24: SOXL 75 -> 53 recorded, cash still in the old definition (withdrawable 9395.21)."""
    state = base_state()
    state.update(state_revision=24, holdings={"SOXL": 53}, average_cost_usd={"SOXL": 100.0},
                 position_cost_basis_usd={"SOXL": 5300.0}, aggregate_cost_basis_usd=5300.0,
                 available_cash_usd=9395.21, timing_plan={"positions": {}})
    state["last_confirmed_broker_snapshot"].update(as_of="2026-10-09", as_of_timestamp=M8_RECORD)
    return state


def m8_snapshot_broker():
    """Rev 24's snapshot: order-available 12467.71, withdrawable 9395.21, SOXL proceeds pending for 10/13."""
    return FakeBroker(holdings=[holding("SOXL", 53, settled=75)], ord_cash="12467.71", pymn_cash="9395.21",
                      detail=dict(M1_DETAIL))


def soxl_sale():
    """M1: SOXL 22 sold on the U.S. 10/9 session (ust21150 order day KST 10/9, filled KST 10/10 05:00)."""
    return {"20261009": [fill("SOXL", SELL, 22, "139.7600", order_no="0002")]}


def m6_row():
    """M6: an invalid limit sell (MVLL 118) with no fill quantity and no fill time."""
    return {"ord_no": "0000009", "crnc_code": "USD", "stk_cd": "MVLL", "slby_tp_nm": SELL, "frgn_trde_tp": "지정가",
            "ord_qty": "000000000118", "cntr_qty": "000000000000", "cncl_qty": "000000000000",
            "ord_remnq": "000000000000", "ord_uv": "20.0000", "cntr_uv": "0.0000", "ord_time": "21:31:00",
            "cntr_time": "", "ord_stat_nm": "무효주문", "rsrv_tp": "0"}


class SettlementAmountTests(Workspace):
    def i3(self, result):
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(result["invariants"]["I2"]["status"], "PASS")
        return result["invariants"]["I3"]

    def test_m1_settlement_row_of_a_fill_before_the_record_is_not_a_cash_change(self):
        # M1 as measured, then settled: after the record there is no fill, only the sale's settlement row.
        self.write_state(m8_state(), block=empty_block("2026-10-07", "2026-10-10"), snapshot_broker=m8_snapshot_broker())
        broker = FakeBroker(holdings=[holding("SOXL", 53)], ord_cash="12467.71", pymn_cash="12467.71", detail={},
                            fills=soxl_sale(), history=[
                                trade_row("20261013", "000000001", "SOXL", SELL, 22, "3074.72", "2.21", "3072.51",
                                          clock="08:07:26")])
        i3 = self.i3(self.auto(broker))
        self.assertEqual((i3["fills_counted"], i3["fill_cash_usd"], i3["flow_cash_usd"], i3["unexplained_usd"]),
                         (0, "0.00", "0.00", "0.00"))
        self.assertEqual(i3["settlements"], [])

    def test_sale_after_the_record_is_explained_by_the_pending_settlement_not_the_fee_estimate(self):
        state = m8_state()
        state.update(holdings={"SOXL": 75}, position_cost_basis_usd={"SOXL": 7500.0}, aggregate_cost_basis_usd=7500.0)
        state["last_confirmed_broker_snapshot"].update(as_of="2026-10-08", as_of_timestamp="2026-10-08T21:15:00Z")
        self.write_state(state, block=empty_block("2026-10-07", "2026-10-09"))
        broker = FakeBroker(
            holdings=[holding("SOXL", 53, settled=75)], ord_cash="12467.71", pymn_cash="9395.21",
            detail=dict(M1_DETAIL), fills=soxl_sale(), retrieved=M1_READ - timedelta(seconds=5),
            day_trades={"20261009": [day_trade("SOXL", sold=22, sell_amount="3074.7200", fees="7.7502")]})
        i3 = self.i3(self.auto(broker, now=M1_READ, day="2026-10-10"))
        self.assertEqual(i3["settlements"], [{
            "settlement_date": "2026-10-13", "source": "PENDING", "sessions": ["2026-10-09"], "sell_usd": "3072.51",
            "buy_usd": "0.00", "gross_sell_usd": "3074.72", "gross_buy_usd": "0.00"}])
        self.assertEqual((i3["fills_counted"], i3["fill_cash_usd"], i3["unexplained_usd"]), (1, "3072.51", "-0.01"))
        # The day-trade fee column (an estimate, 7.7502 against the actual 2.21) would leave 5.53 unexplained.
        self.assertEqual(Decimal("12467.71") - Decimal("9395.21") - (Decimal("3074.72") - Decimal("7.7502")),
                         Decimal("5.5302"))

    def test_buy_after_the_record_settled_before_the_run_is_explained_by_the_trade_row(self):
        # M2: NBIS 15 x 215.00 (U.S. 8/12 session), estimate 8.0625, settled 8/14 with the actual fee 2.25.
        state = base_state()
        state["available_cash_usd"] = 5000.0
        state["last_confirmed_broker_snapshot"].update(as_of="2026-08-11", as_of_timestamp="2026-08-11T21:15:00Z")
        self.write_state(state, block=empty_block("2026-08-10", "2026-08-12"))
        now = datetime(2026, 8, 14, 21, 15, tzinfo=timezone.utc)  # KST 8/15 06:15
        broker = FakeBroker(
            holdings=[holding("AAA", 10), holding("BBB", 5), holding("NBIS", 15)], ord_cash="1772.75",
            pymn_cash="1772.75", detail={}, fills={"20260812": [fill("NBIS", BUY, 15, "215.0000")]},
            day_trades={"20260812": [day_trade("NBIS", bought=15, buy_amount="3225.0000", fees="8.0625")]},
            history=[trade_row("20260814", "000000001", "NBIS", BUY, 15, "3225.00", "2.25", "3227.25")],
            retrieved=now - timedelta(seconds=5))
        i3 = self.i3(self.auto(broker, now=now, day="2026-08-15"))
        self.assertEqual(i3["settlements"], [{
            "settlement_date": "2026-08-14", "source": "SETTLED", "sessions": ["2026-08-12"], "sell_usd": "0.00",
            "buy_usd": "3227.25", "gross_sell_usd": "0.00", "gross_buy_usd": "3225.00"}])
        self.assertEqual((i3["fill_cash_usd"], i3["unexplained_usd"]), ("-3227.25", "0.00"))

    def test_pending_slot_of_a_fill_before_the_record_is_not_counted(self):
        # KST 10/13 06:15: the SOXL proceeds (filled before the record) still pending for 10/13, an NBIS buy of
        # the U.S. 10/12 session pending for 10/14. A date can only hold fills of earlier KST days.
        self.write_state(m8_state(), block=empty_block("2026-10-07", "2026-10-10"), snapshot_broker=m8_snapshot_broker())
        now = NOW - timedelta(days=1)
        broker = FakeBroker(
            holdings=[holding("SOXL", 53, settled=75), holding("NBIS", 15, settled=0)], ord_cash="9240.46",
            pymn_cash="6167.96", retrieved=now - timedelta(seconds=5),
            detail={"d1_setl_dt": "20261013", "d1_usd_sell_excta": "3072.51", "d1_usd_buy_excta": "0.00",
                    "d2_setl_dt": "20261014", "d2_usd_sell_excta": "0.00", "d2_usd_buy_excta": "3227.25"},
            fills={**soxl_sale(), "20261012": [fill("NBIS", BUY, 15, "215.0000", order_no="0003")]},
            day_trades={"20261012": [day_trade("NBIS", bought=15, buy_amount="3225.0000", fees="8.0625")]})
        i3 = self.i3(self.auto(broker, now=now, day="2026-10-13"))
        self.assertEqual([(item["settlement_date"], item["source"], item["buy_usd"]) for item in i3["settlements"]],
                         [("2026-10-14", "PENDING", "3227.25")])
        self.assertEqual((i3["fill_cash_usd"], i3["unexplained_usd"]), ("-3227.25", "0.00"))

    def test_sessions_are_matched_to_settlement_dates_in_order(self):
        sessions = [{"session_date": "2026-10-12", "last_fill_day": datetime(2026, 10, 13).date(),
                     "gross": {"SELL": Decimal("0"), "BUY": Decimal("100")}, "quantities": {("AAA", "BUY"): 1}},
                    {"session_date": "2026-10-13", "last_fill_day": datetime(2026, 10, 14).date(),
                     "gross": {"SELL": Decimal("200"), "BUY": Decimal("0")}, "quantities": {("BBB", "SELL"): 2}}]
        slots = [{"slot": "d1", "settlement_date": datetime(2026, 10, 14).date(), "SELL": Decimal("0"),
                  "BUY": Decimal("100.25")},
                 {"slot": "d2", "settlement_date": datetime(2026, 10, 15).date(), "SELL": Decimal("199.50"),
                  "BUY": Decimal("0")}]
        with mock.patch.object(core, "fill_sessions", return_value=(sessions, [])):
            total, details, errors = core.fill_settlement([{"filled_at_kst": "x"}], [], slots=slots, slot_errors=[],
                                                          trades=[])
        self.assertEqual(errors, [])
        self.assertEqual(total, Decimal("99.25"))
        self.assertEqual([item["sessions"] for item in details], [["2026-10-12"], ["2026-10-13"]])

    def test_later_settlement_slots_and_unreadable_amounts(self):
        detail = {"d1_setl_dt": "20261015", "d1_usd_sell_excta": "0", "d1_usd_buy_excta": "0",
                  "d3_setl_dt": "20261019", "d3_usd_sell_excta": "329.17", "d3_usd_buy_excta": "0",
                  "d4_setl_dt": "20261020", "d4_usd_sell_excta": "x", "d4_usd_buy_excta": "0"}
        self.assertTrue({"d3_setl_dt", "d3_usd_sell_excta", "d4_usd_buy_excta"}
                        <= set(bridge.SAFE_FIELDS["account_deposit_detail_read"]))
        result = {"operation": "account_deposit_detail_read", "bridge_status": "PASS", "data": [detail],
                  "pagination": {"complete": True}}
        slots, errors = core.settlement_slots([result])
        self.assertEqual(errors, [])
        self.assertEqual([(slot["slot"], slot["SELL"]) for slot in slots],
                         [("d1", Decimal("0")), ("d3", Decimal("329.17")), ("d4", None)])
        broker = sale_broker(detail=detail)
        held = self.auto(broker)
        self.assertIn("I3:SETTLEMENT_SLOT_AMOUNT_INVALID:d4", held["reasons"])


class BaselineSnapshotTests(Workspace):
    def unchanged_broker(self):
        return FakeBroker(holdings=[holding("AAA", 10), holding("BBB", 5)], ord_cash="1000.00", pymn_cash="1000.00")

    def test_unknown_baseline_holds_and_never_falls_back_to_the_state_cash(self):
        # The state's cash equals the broker's and nothing moved: only the unknown baseline can hold.
        def tamper():
            snapshot = load_json(self.baseline_snapshot_path)
            snapshot["cash"]["order_available_cash"] = 999.0
            self.baseline_snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        cases = {
            "snapshot missing": (lambda: self.baseline_snapshot_path.unlink(), "SNAPSHOT_NOT_FOUND", None),
            "proposal missing": (lambda: (self.baseline_snapshot_path.parent / "reconciliation_proposal.json").unlink(),
                                 "PROPOSAL_NOT_FOUND", None),
            "snapshot changed": (tamper, "SNAPSHOT_HASH_MISMATCH", None),
            "no order-available amount": (lambda: None, "ORDER_AVAILABLE_CASH_MISSING", FakeBroker(
                holdings=[holding("AAA", 10), holding("BBB", 5)], ord_cash=None, pymn_cash="1000.00")),
        }
        for name, (breaker, detail, snapshot_broker) in cases.items():
            with self.subTest(case=name):
                self.write_state(base_state(), block=empty_block(), snapshot_broker=snapshot_broker)
                breaker()
                before = self.snapshot_files()
                result = self.auto(self.unchanged_broker(), day=name.replace(" ", "-"))
                self.assertEqual(result["status"], "HOLD")
                self.assertIn(f"I3:BASELINE_ORDER_AVAILABLE_UNKNOWN:{detail}", result["reasons"])
                self.assertEqual(result["invariants"]["I3"]["baseline"], {"status": "UNKNOWN", "detail": detail})
                self.assertIsNone(result["would_apply"])
                self.assertEqual(self.snapshot_files(), before)

    def test_old_state_cash_definition_is_explained_from_the_first_day(self):
        # M8: the state holds 9395.21 (old minimum); the record's snapshot holds order-available 12467.71.
        self.write_state(m8_state(), block=empty_block("2026-10-07", "2026-10-10"), snapshot_broker=m8_snapshot_broker())
        broker = FakeBroker(holdings=[holding("SOXL", 53, settled=75)], ord_cash="12467.71", pymn_cash="9395.21",
                            detail=dict(M1_DETAIL), fills=soxl_sale(), retrieved=M1_READ - timedelta(seconds=5))
        result = self.auto(broker, now=M1_READ, day="2026-10-10")
        self.assertEqual(result["status"], "OK", result["reasons"])
        baseline = result["invariants"]["I3"]["baseline"]
        self.assertEqual((baseline["source"], baseline["order_available_cash_usd"], baseline["generated_at"]),
                         ("LEDGER_PROPOSAL_ID", "12467.71", "2026-10-09T23:52:05.178310Z"))
        self.assertEqual(result["invariants"]["I3"]["baseline_cash_usd"], "12467.71")
        self.assertEqual(result["would_apply"]["available_cash_usd"], 12467.71)

    def test_apply_names_both_snapshots_and_the_next_run_uses_its_own(self):
        baseline_hash = load_json(self.baseline_snapshot_path)["snapshot_hash"]
        first = self.auto(sale_broker(), mode="apply")
        self.assertIsNotNone(first["applied"])
        block = self.ledger_entries()[-1]["auto_core"]
        self.assertEqual(block["baseline_snapshot"], {"path": str(self.baseline_snapshot_path),
                                                      "snapshot_hash": baseline_hash})
        self.assertEqual(block["invariants"]["I3"]["baseline"]["snapshot_hash"], baseline_hash)
        own = Path(block["snapshot"]["path"])
        self.assertEqual(own.parent, (self.output_root / "2026-10-14").resolve())
        self.assertEqual(load_json(own)["snapshot_hash"], block["snapshot"]["snapshot_hash"])
        self.assertEqual(load_json(self.state_path)["last_confirmed_broker_snapshot"]["evidence_sha256"],
                         block["snapshot"]["snapshot_hash"])
        # A same-day rerun rewrites the plain snapshot file; the record's own copy stays as it was.
        later = NOW + timedelta(minutes=10)
        self.auto(sale_broker(retrieved=later - timedelta(seconds=5)), mode="apply", now=later)
        self.assertEqual(load_json(own)["snapshot_hash"], block["snapshot"]["snapshot_hash"])
        # After settlement the next run judges I3 from that snapshot (1329.17), not from the first baseline.
        moment = NOW + timedelta(days=2)
        result = self.auto(settled_sale_broker(moment), mode="apply", now=moment, day="2026-10-16")
        self.assertEqual(result["status"], "OK", result["reasons"])
        i3 = result["invariants"]["I3"]
        self.assertEqual((i3["baseline"]["source"], i3["baseline"]["snapshot_path"], i3["baseline_cash_usd"]),
                         ("AUTO_CORE_LEDGER_ENTRY", block["snapshot"]["path"], "1329.17"))
        self.assertEqual((i3["fills_counted"], i3["unexplained_usd"]), (0, "0.00"))

    def test_library_requires_the_baseline_reference(self):
        result = self.auto(sale_broker(), mode="compare")
        proposal = load_json(self.output_root / "2026-10-14/reconciliation_proposal.json")
        invariants = copy.deepcopy(result["invariants"])
        invariants["I3"].pop("baseline")
        with self.assertRaisesRegex(ValueError, "AUTO_CORE_BASELINE_SNAPSHOT_REQUIRED"):
            apply_module.apply_auto_core(state_path=self.state_path, proposal=proposal, invariants=invariants,
                                         provenance={"commit_sha": COMMIT, "mode": "apply"},
                                         audit_path=self.root / "audit.json")
        self.assertEqual(len(self.ledger_entries()), 1)


class NoDataAndInvalidOrderTests(Workspace):
    def test_m6_invalid_order_row_is_zero_fills(self):
        result = {"operation": "account_daily_fills_read", "bridge_status": "PASS", "data": [m6_row()],
                  "request_params": {"ord_dt": "20261005"}, "pagination": {"complete": True}}
        self.assertEqual(core.parse_fills([result]), ([], []))
        broker = FakeBroker(holdings=[holding("AAA", 10), holding("BBB", 5)], ord_cash="1000.00", pymn_cash="1000.00",
                            fills={"20261013": [m6_row()]})
        run = self.auto(broker)
        self.assertEqual(run["status"], "OK", run["reasons"])
        self.assertEqual((run["invariants"]["I2"]["fills_counted"], run["invariants"]["I3"]["fills_counted"]), (0, 0))

    def test_measured_no_data_declarations_are_listed_for_the_dated_reads(self):
        self.assertEqual(bridge.NO_DATA_PASS_MESSAGES["account_daily_fills_read"],
                         frozenset({"[2000](571758:해당 계좌의 체결내역이 없습니다.)"}))
        self.assertEqual(bridge.NO_DATA_PASS_MESSAGES["account_day_trades_read"],
                         frozenset({"[2000](571758:조회내역이 없습니다.)"}))


# ---------------------------------------------------------------------------------------------
# compare / apply / kill switch / idempotence
# ---------------------------------------------------------------------------------------------

class ModeTests(Workspace):
    def test_compare_mode_never_writes_state_ledger_or_journal(self):
        before = self.snapshot_files()
        result = self.auto(sale_broker(), mode="compare")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(result["would_apply"]["holdings"], {"AAA": 7, "BBB": 5})
        self.assertEqual(result["would_apply"]["available_cash_usd"], 1329.17)
        self.assertIsNone(result["applied"])
        self.assertEqual(self.snapshot_files(), before)
        self.assertFalse((self.root / "backups").exists())
        self.assertFalse(self.policies["journal"].exists())

    def test_apply_mode_writes_one_chained_ledger_line_and_a_backup(self):
        original = self.state_path.read_bytes()
        result = self.auto(sale_broker(), mode="apply")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(result["applied"]["state_revision_after"], 31)
        state = load_json(self.state_path)
        self.assertEqual(state["holdings"], {"AAA": 7, "BBB": 5})
        self.assertEqual(state["available_cash_usd"], 1329.17)
        self.assertEqual(state["last_confirmed_broker_snapshot"]["authority_state"],
                         "VERIFIED_AUTO_CORE_INVARIANTS_BROKER_SNAPSHOT")
        self.assertEqual(state["holding_change_reconciliations"][-1]["method"],
                         "KIWOOM_READONLY_SNAPSHOT_AUTO_CORE_INVARIANTS")
        for field in NEVER_TOUCHED_FIELDS:
            self.assertEqual(state.get(field), base_state().get(field), field)
        self.assertIn(b"\r\n", self.state_path.read_bytes())
        status = apply_module.ledger_status(self.ledger_path)
        self.assertEqual((status["entries"], status["chain_ok"]), (2, True))
        self.assertEqual(status["last_portfolio_hash_after"], canonical_hash(state))
        entry = self.ledger_entries()[-1]
        self.assertEqual(entry["confirmation_method"], "AUTO_CORE_INVARIANTS")
        self.assertIsNone(entry["confirm_code"])
        self.assertIsNone(entry["user_message"])
        self.assertEqual(entry["auto_core"]["commit_sha"], COMMIT)
        self.assertEqual({name: value["status"] for name, value in entry["auto_core"]["invariants"].items()},
                         dict.fromkeys(("I1", "I2", "I3", "I4", "I5"), "PASS"))
        self.assertFalse(entry["inferred_fills"])
        self.assertFalse(entry["order_authority"])
        self.assertEqual(entry["cash_flow_declaration"]["declaration_status"], "NO_EXTERNAL_FLOW")
        backups = list((self.root / "backups").glob("portfolio_state.r30.*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        text = self.ledger_path.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"\d{8}-\d{2}")  # no account-number-like value

    def test_kill_switch_stops_before_any_read(self):
        broker = sale_broker()
        before = self.snapshot_files()
        result = self.auto(broker, mode="apply", kill_switch=True)
        self.assertEqual((result["status"], result["reasons"]), ("HOLD", ["KILL_SWITCH_ON"]))
        self.assertEqual(broker.requests, [])
        self.assertEqual(self.snapshot_files(), before)

    def test_missing_config_compares_only(self):
        before = self.snapshot_files()
        result = self.auto(sale_broker(), config=False)
        self.assertEqual(result["mode"], "compare")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("AUTO_CORE_CONFIG_MISSING", result["reasons"])
        self.assertEqual(self.snapshot_files(), before)

    def test_apply_mode_with_uncommitted_guarded_file_fails_before_reading(self):
        broker = sale_broker()
        provenance = {"status": "OK", "commit_sha": COMMIT, "dirty_paths": ["manage-us-stock-strategy/scripts/x.py"],
                      "guarded_dirty_paths": ["manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py"]}
        result = self.auto(broker, mode="apply", provenance=provenance)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["reasons"],
                         ["GUARDED_FILES_UNCOMMITTED:manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py"])
        self.assertEqual(broker.requests, [])
        unknown = self.auto(sale_broker(), mode="apply", provenance={"status": "UNAVAILABLE", "commit_sha": None})
        self.assertEqual(unknown["reasons"], ["GIT_PROVENANCE_UNAVAILABLE"])
        # Compare mode records the dirty paths but still runs (it cannot write).
        compare = self.auto(sale_broker(), mode="compare", provenance=provenance)
        self.assertEqual(compare["status"], "OK", compare["reasons"])
        self.assertEqual(compare["provenance"]["guarded_dirty_paths"],
                         ["manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py"])

    def test_apply_guard_covers_files_outside_the_former_pin_list(self):
        # T1 r3 C2: any tracked file under scripts/, schemas/ or assets/ with an uncommitted change.
        for path in ("manage-us-stock-strategy/scripts/validation_common.py",
                     "manage-us-stock-strategy/scripts/evaluate_alerts.py",
                     "manage-us-stock-strategy/scripts/portfolio_exposure.py",
                     "manage-us-stock-strategy/scripts/portfolio_review_journal.py",
                     "manage-us-stock-strategy/schemas/kiwoom-broker-shadow.schema.json"):
            with self.subTest(path=path):
                self.assertNotIn(path, core.guarded_paths())
                provenance = core.git_provenance(runner=fake_git(f" M {path}\0"))
                broker = sale_broker()
                before = self.snapshot_files()
                result = self.auto(broker, mode="apply", provenance=provenance)
                self.assertEqual((result["status"], result["reasons"]), ("FAIL", [f"GUARDED_FILES_UNCOMMITTED:{path}"]))
                self.assertEqual(broker.requests, [])
                self.assertEqual(self.snapshot_files(), before)

    def test_same_day_twice_writes_once(self):
        first = self.auto(sale_broker(), mode="apply")
        self.assertIsNotNone(first["applied"])
        later = NOW + timedelta(minutes=10)
        second = self.auto(sale_broker(retrieved=later - timedelta(seconds=5)), mode="apply", now=later)
        self.assertEqual(second["status"], "OK", second["reasons"])
        self.assertEqual(second["proposal"]["status"], "NO_CHANGE_REQUIRED")
        self.assertIsNone(second["applied"])
        self.assertEqual(len(self.ledger_entries()), 2)
        self.assertEqual(second["would_apply"]["holdings"], first["would_apply"]["holdings"])


class CliTests(Workspace):
    def test_auto_subcommand_writes_only_its_result_in_compare_mode(self):
        now = datetime.now(timezone.utc)
        today = now.astimezone(core.KST).date()
        state = base_state()
        state["last_confirmed_broker_snapshot"]["as_of_timestamp"] = utc(now - timedelta(days=1))
        self.write_state(state, block=empty_block((today - timedelta(days=2)).isoformat(),
                                                  (today - timedelta(days=1)).isoformat()))
        self.config("compare")
        before = self.snapshot_files()
        broker = FakeBroker(holdings=[holding("AAA", 10), holding("BBB", 5)], ord_cash="1000.00",
                            pymn_cash="1000.00", retrieved=now)
        argv = ["auto", "--config", str(self.config_path), "--output-root", str(self.output_root),
                "--date", "2026-10-14", "--readonly-policy", str(self.policies["readonly"]),
                "--rate-policy", str(self.policies["rate"]), "--broker-policy", str(self.policies["broker"]),
                "--alert-policy", str(self.policies["alert"]), "--portfolio-state", str(self.state_path),
                "--journal", str(self.policies["journal"])]
        with mock.patch.object(core, "EVIDENCE_ROOT", self.evidence_root), \
                mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()):
            code = cli.main(argv, reader=broker)
        result = load_json(self.output_root / "2026-10-14/reconcile.json")
        self.assertEqual(code, 0)
        self.assertEqual((result["mode"], result["status"]), ("compare", "OK"), result["reasons"])
        self.assertIsNone(result["applied"])
        self.assertEqual(result["provenance"]["status"] in ("OK", "UNAVAILABLE"), True)
        self.assertEqual(self.snapshot_files(), before)
        self.assertTrue(all(request["operation"] in bridge.ACCOUNT_APIS for request in broker.requests))


class LibraryTests(Workspace):
    def proposal(self):
        result = self.auto(sale_broker(), mode="compare")
        return load_json(self.output_root / "2026-10-14/reconciliation_proposal.json"), result["invariants"]

    def test_library_refuses_without_all_invariants_or_commit(self):
        proposal, invariants = self.proposal()
        provenance = {"commit_sha": COMMIT, "mode": "apply"}
        for name in ("I1", "I3", "I5"):
            broken = copy.deepcopy(invariants)
            broken[name]["status"] = "FAIL"
            with self.subTest(invariant=name):
                with self.assertRaisesRegex(ValueError, "AUTO_CORE_INVARIANTS_NOT_PASSED"):
                    apply_module.apply_auto_core(state_path=self.state_path, proposal=proposal, invariants=broken,
                                                 provenance=provenance, audit_path=self.root / "audit.json")
        missing = {key: value for key, value in invariants.items() if key != "I4"}
        with self.assertRaisesRegex(ValueError, "AUTO_CORE_INVARIANTS_NOT_PASSED"):
            apply_module.apply_auto_core(state_path=self.state_path, proposal=proposal, invariants=missing,
                                         provenance=provenance, audit_path=self.root / "audit.json")
        for bad in ({"commit_sha": None, "mode": "apply"}, {"commit_sha": "x" * 40, "mode": "apply"},
                    {"commit_sha": COMMIT, "mode": "compare"}):
            with self.subTest(provenance=bad):
                with self.assertRaisesRegex(ValueError, "AUTO_CORE_(COMMIT_SHA_REQUIRED|MODE_NOT_APPLY)"):
                    apply_module.apply_auto_core(state_path=self.state_path, proposal=proposal, invariants=invariants,
                                                 provenance=bad, audit_path=self.root / "audit.json")
        self.assertEqual(len(self.ledger_entries()), 1)

    def test_library_refuses_a_state_changed_outside_the_ledger(self):
        proposal, invariants = self.proposal()
        state = base_state()
        state["state_notes"] = ["CHANGED_OUTSIDE"]
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "CONCURRENT_STATE_HASH_MISMATCH|STATE_CHANGED_OUTSIDE_LEDGER"):
            apply_module.apply_auto_core(state_path=self.state_path, proposal=proposal, invariants=invariants,
                                         provenance={"commit_sha": COMMIT, "mode": "apply"},
                                         audit_path=self.root / "audit.json")

    def test_human_code_path_rejects_the_auto_method_and_still_requires_its_code(self):
        proposal, _ = self.proposal()
        confirmation = {"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
                        "confirm_code": proposal["confirm_code"], "confirmation_method": "AUTO_CORE_INVARIANTS",
                        "user_message": proposal["confirm_code"]}
        with self.assertRaisesRegex(ValueError, "CONFIRMATION_METHOD_INVALID"):
            apply_module.apply_confirmed(state_path=self.state_path, proposal=proposal, confirmation=confirmation,
                                         audit_path=self.root / "audit.json")
        confirmation["confirmation_method"] = "USER_TERMINAL"
        confirmation["confirm_code"] = "00000000"
        with self.assertRaisesRegex(ValueError, "CONFIRM_CODE_MISMATCH"):
            apply_module.apply_confirmed(state_path=self.state_path, proposal=proposal, confirmation=confirmation,
                                         audit_path=self.root / "audit.json")
        self.assertEqual(apply_module.CONFIRMATION_METHODS, ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL"))
        apply_parser = cli.build_parser()._subparsers._group_actions[0].choices["apply"]
        method = next(action for action in apply_parser._actions if action.dest == "confirmed_via")
        self.assertEqual(tuple(method.choices), ("COWORK_CHAT_USER_MESSAGE", "USER_TERMINAL"))

    def test_human_code_path_still_applies(self):
        proposal, _ = self.proposal()
        confirmation = {"confirmed": True, "proposal_id": proposal["proposal_id"], "bundle_id": proposal["bundle_id"],
                        "confirm_code": proposal["confirm_code"], "confirmation_method": "USER_TERMINAL",
                        "user_message": proposal["confirm_code"]}
        audit = apply_module.apply_confirmed(state_path=self.state_path, proposal=proposal, confirmation=confirmation,
                                             audit_path=self.root / "audit.json")
        self.assertEqual(audit["state_revision_after"], 31)
        entry = self.ledger_entries()[-1]
        self.assertEqual((entry["confirmation_method"], entry["confirm_code"]), ("USER_TERMINAL", proposal["confirm_code"]))
        self.assertNotIn("auto_core", entry)
        self.assertEqual(load_json(self.state_path)["last_confirmed_broker_snapshot"]["authority_state"],
                         "VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT")


# ---------------------------------------------------------------------------------------------
# T1 r3 (Judge conditions): C1 the write re-check, C4 a settlement due today
# ---------------------------------------------------------------------------------------------

CLEAN = {"status": "OK", "commit_sha": COMMIT, "dirty_paths": [], "guarded_dirty_paths": []}


def rehashed(proposal, **changes):
    """The proposal after a change, with its identifiers derived again (None removes a field)."""
    changed = copy.deepcopy(proposal)
    for key, value in changes.items():
        if value is None:
            changed.pop(key, None)
        else:
            changed[key] = value
    changed["proposal_id"] = proposal_content_hash(changed)
    changed["confirm_code"] = changed["proposal_id"][:8].upper()
    return changed


class WriteRecheckTests(Workspace):
    """C1: just before writing, apply_auto_core reads the configuration, the code provenance and the cash-flow
    declaration again; each mismatch alone writes nothing (no state, ledger line, backup or audit)."""

    def setUp(self):
        super().setUp()
        result = self.auto(sale_broker(), mode="compare")
        self.proposal = load_json(self.output_root / "2026-10-14/reconciliation_proposal.json")
        self.invariants = result["invariants"]
        self.config("apply")

    def apply(self, proposal=None, source=None):
        return apply_module.apply_auto_core(
            state_path=self.state_path, proposal=proposal or self.proposal, invariants=self.invariants,
            provenance={**CLEAN, "mode": "apply"}, audit_path=self.root / "audit.json",
            config_path=self.config_path, provenance_source=source or (lambda: dict(CLEAN)))

    def assert_refused(self, code, **kwargs):
        before = self.snapshot_files()
        with self.assertRaisesRegex(ValueError, "^" + re.escape(code) + "$"):
            self.apply(**kwargs)
        self.assertEqual(self.snapshot_files(), before)
        self.assertFalse((self.root / "backups").exists())
        self.assertFalse((self.root / "audit.json").exists())

    def test_configuration_is_read_again(self):
        cases = {"kill switch on": (lambda: self.config("apply", kill_switch=True), "AUTO_CORE_RECHECK_KILL_SWITCH_ON"),
                 "back to compare": (lambda: self.config("compare"), "AUTO_CORE_RECHECK_MODE_NOT_APPLY"),
                 "file removed": (lambda: self.config_path.unlink(),
                                  "AUTO_CORE_RECHECK_CONFIG_UNAVAILABLE:AUTO_CORE_CONFIG_MISSING")}
        for name, (change, code) in cases.items():
            with self.subTest(case=name):
                change()
                self.assert_refused(code)
                self.config("apply")

    def test_provenance_is_computed_again(self):
        changed = "manage-us-stock-strategy/scripts/validation_common.py"
        cases = {
            "guarded file changed": (dict(CLEAN, dirty_paths=[changed], guarded_dirty_paths=[changed]),
                                     f"AUTO_CORE_RECHECK_GUARDED_FILES_UNCOMMITTED:{changed}"),
            "git unavailable": ({"status": "UNAVAILABLE", "commit_sha": None},
                                "AUTO_CORE_RECHECK_GIT_PROVENANCE_UNAVAILABLE"),
            "another commit": (dict(CLEAN, commit_sha="b" * 40), "AUTO_CORE_RECHECK_COMMIT_CHANGED"),
        }
        for name, (fresh, code) in cases.items():
            with self.subTest(case=name):
                self.assert_refused(code, source=lambda fresh=fresh: dict(fresh))

    def test_declaration_must_be_present_and_declared_in_full(self):
        self.assertEqual(self.proposal["cash_flow_declaration"]["declaration_status"], "NO_EXTERNAL_FLOW")
        self.assert_refused("AUTO_CORE_RECHECK_CASH_FLOW_DECLARATION_MISSING",
                            proposal=rehashed(self.proposal, cash_flow_declaration=None))
        evidence = cfe.normalize_transaction_history(
            {"return_code": 0, "result_list": [history_row("20261013", "000000001", DEPOSIT_KIND, DEPOSIT_MEMO,
                                                           "500.00")]},
            period_from="2026-10-13", period_to="2026-10-14", raw_sha256="0" * 64)
        undeclared = cfe.build_declaration(evidence, declared_usd=None, prior_blocks=[])
        self.assertEqual(undeclared["declaration_status"], "UNDECLARED")
        proposal = rehashed(self.proposal, cash_flow_declaration=undeclared)
        self.assertEqual(validate_instance(proposal, PROPOSAL_SCHEMA), [])
        self.assert_refused("AUTO_CORE_RECHECK_CASH_FLOW_NOT_DECLARED_IN_FULL:UNDECLARED", proposal=proposal)

    def test_everything_still_right_writes(self):
        self.assertEqual(self.apply()["state_revision_after"], 31)
        self.assertEqual(len(self.ledger_entries()), 2)

    def test_kill_switch_or_code_change_during_the_run_writes_nothing(self):
        # The run read the configuration at its start; the change comes while the broker is being read.
        before = self.snapshot_files()
        broker = sale_broker()

        def reader(requests, **kwargs):
            results = broker(requests, **kwargs)
            self.config("apply", kill_switch=True)
            return results
        result = self.auto(reader, mode="apply", day="kill")
        self.assertEqual((result["status"], result["reasons"]), ("FAIL", ["AUTO_CORE_RECHECK_KILL_SWITCH_ON"]))
        changed = dict(CLEAN, guarded_dirty_paths=["manage-us-stock-strategy/scripts/evaluate_alerts.py"])
        result = self.auto(sale_broker(), mode="apply", day="code", provenance_source=lambda: dict(changed))
        self.assertEqual((result["status"], result["reasons"]), ("FAIL", [
            "AUTO_CORE_RECHECK_GUARDED_FILES_UNCOMMITTED:manage-us-stock-strategy/scripts/evaluate_alerts.py"]))
        self.assertEqual(self.snapshot_files(), before)
        self.assertFalse((self.root / "backups").exists())


D0_DAY = NOW + timedelta(days=1)  # KST 10/15 06:15: sale_broker's sale settles today, before about 08:07


def d0_broker(moment=D0_DAY, **changes):
    """sale_broker on its settlement day before the broker's processing: no slot and no trade row for today."""
    values = dict(detail={"d1_setl_dt": "20261016", "d1_usd_sell_excta": "0.00", "d1_usd_buy_excta": "0.00"},
                  retrieved=moment - timedelta(seconds=5))
    values.update(changes)
    return sale_broker(**values)


class SettlementDueTodayTests(Workspace):
    """C4: a settlement due today (D0) has no amount in the cash detail and no trade row before ~08:07 KST."""

    def test_previous_runs_pending_amount_explains_todays_settlement(self):
        first = self.auto(sale_broker())
        self.assertEqual([(item["settlement_date"], item["source"]) for item in first["invariants"]["I3"]["settlements"]],
                         [("2026-10-15", "PENDING")])
        result = self.auto(d0_broker(), mode="apply", now=D0_DAY, day="2026-10-15", previous_run=first)
        self.assertEqual(result["status"], "OK", result["reasons"])
        i3 = result["invariants"]["I3"]
        self.assertEqual(i3["settlements"], [{
            "settlement_date": "2026-10-15", "source": "PENDING_PREVIOUS_RUN", "sessions": ["2026-10-13"],
            "sell_usd": "329.17", "buy_usd": "0.00", "gross_sell_usd": "330.00", "gross_buy_usd": "0.00",
            "carried_from": first["generated_at"]}])
        self.assertEqual((i3["fill_cash_usd"], i3["unexplained_usd"]), ("329.17", "0.00"))
        self.assertIsNotNone(result["applied"])
        self.assertEqual(self.ledger_entries()[-1]["auto_core"]["invariants"]["I3"]["settlements"][0]["source"],
                         "PENDING_PREVIOUS_RUN")

    def test_a_carried_amount_that_does_not_match_holds_as_usual(self):
        first = copy.deepcopy(self.auto(sale_broker()))
        first["invariants"]["I3"]["settlements"][0]["sell_usd"] = "300.00"
        result = self.auto(d0_broker(), now=D0_DAY, day="2026-10-15", previous_run=first)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("I3:SETTLEMENT_OUTSIDE_FEE_RANGE:2026-10-15:SELL:-30.00", result["reasons"])
        self.assertFalse(core.d0_only(result["reasons"]))

    def test_without_an_earlier_read_only_todays_settlement_is_left_open(self):
        before = self.snapshot_files()
        result = self.auto(d0_broker(), mode="apply", now=D0_DAY, day="2026-10-15")
        self.assertEqual((result["status"], result["reasons"]), ("HOLD", ["I3:SETTLEMENT_D0_NOT_SHOWN:2026-10-15"]))
        self.assertTrue(core.d0_only(result["reasons"]))
        self.assertEqual(result["invariants"]["I3"]["settlements"], [{
            "settlement_date": "2026-10-15", "source": "D0_NOT_SHOWN", "sessions": ["2026-10-13"], "sell_usd": None,
            "buy_usd": None, "gross_sell_usd": "330.00", "gross_buy_usd": "0.00", "residual_usd": "329.17"}])
        self.assertIsNone(result["would_apply"])
        self.assertIsNone(result["applied"])
        self.assertEqual(self.snapshot_files(), before)
        # A residual outside the fee range of the sessions put on today is a mismatch, not only D0.
        wrong = self.auto(d0_broker(ord_cash="1335.00"), now=D0_DAY, day="wrong")
        self.assertEqual(wrong["reasons"], ["I3:SETTLEMENT_D0_NOT_SHOWN:2026-10-15",
                                            "I3:SETTLEMENT_D0_OUTSIDE_FEE_RANGE:2026-10-15:5.00"])
        self.assertFalse(core.d0_only(wrong["reasons"]))

    def test_only_a_pending_entry_of_today_is_carried(self):
        today = D0_DAY.astimezone(core.KST).date()
        entry = {"settlement_date": "2026-10-15", "source": "PENDING", "sell_usd": "329.17", "buy_usd": "0.00"}
        previous = {"generated_at": "G", "invariants": {"I3": {"settlements": [entry]}}}
        self.assertEqual(core.carried_settlements(previous, today),
                         {today: {"SELL": Decimal("329.17"), "BUY": Decimal("0"), "carried_from": "G"}})
        for change in ({"source": "SETTLED"}, {"source": "PENDING_PREVIOUS_RUN"}, {"settlement_date": "2026-10-16"},
                       {"sell_usd": None}, {"buy_usd": "-1.00"}):
            with self.subTest(change=change):
                broken = {"generated_at": "G", "invariants": {"I3": {"settlements": [dict(entry, **change)]}}}
                self.assertEqual(core.carried_settlements(broken, today), {})
        self.assertEqual(core.carried_settlements(None, today), {})
        self.assertEqual(core.carried_settlements({"invariants": None}, today), {})


# ---------------------------------------------------------------------------------------------
# F5 orchestrator, F6 provenance, F7 configuration
# ---------------------------------------------------------------------------------------------

class DailyTests(Workspace):
    def setUp(self):
        super().setUp()
        self.closes = self.root / "closes"
        (self.closes / "history").mkdir(parents=True)
        for symbol, exchange in (("AAA", "NASDAQ"), ("BBB", "NYSE"), ("SOXX", "NASDAQ")):
            (self.closes / "history" / f"{symbol}.close-history.json").write_text(
                json.dumps({"symbol": symbol, "exchange": exchange, "last_session": "2026-10-12"}), encoding="utf-8")
        self.watchlist = self.root / "watchlist.json"
        self.watchlist.write_text(json.dumps({"members": [{"code": "NEWW"}]}), encoding="utf-8")
        self.collected: list[tuple] = []
        self.profiles: set = set()
        self.exposure_calls = 0

    def collector(self, symbol, exchange, *, newest, oldest, profile, pages_root):
        self.collected.append((symbol, exchange, newest.isoformat(), oldest.isoformat()))
        self.profiles.add(profile)

    def updater(self, symbol, exchange, *, now, closes_root):
        return {"symbol": symbol, "last_session": "2026-10-13", "sessions": 1, "continuity": "OK"}

    def exposure(self):
        self.exposure_calls += 1
        return {"E": 1.5, "N": 1.4, "status": "VERIFIED", "band": "WITHIN_BAND",
                "lines": {"status": "EVALUATED", "hwm_usd": "1", "next_line": "L1", "reasons": []},
                "holds": [], "evaluation_session": "2026-10-13", "path": "exposure.json"}

    def exchange_reader(self, requests, *, runtime, policy):
        return [{"bridge_status": "PASS", "data": [{"stk_cd": requests[0]["ticker"], "stex_tp": "ND"}]}]

    def daily(self, broker, *, now=NOW, collector=None, mode="compare", provenance=None, exposure_runner=None):
        self.config(mode)
        provenance = provenance or {"status": "OK", "commit_sha": COMMIT, "dirty_paths": [], "guarded_dirty_paths": []}
        FrozenClock.moment = now
        return auto_core.daily(
            output_root=self.output_root, config_path=self.config_path, now=now, reader=broker,
            exchange_reader=self.exchange_reader, collector=collector or self.collector,
            history_updater=self.updater, exposure_runner=exposure_runner or self.exposure,
            provenance=provenance, policy_paths=self.policies, closes_root=self.closes,
            watchlist_path=self.watchlist, evidence_root=self.evidence_root,
            provenance_source=lambda: dict(provenance))

    def test_daily_result_and_latest(self):
        result = self.daily(sale_broker())
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertEqual(validate_instance(result, SCHEMAS / "auto-core-result.schema.json"), [])
        self.assertEqual(load_json(self.output_root / "LATEST.json"), result)
        self.assertEqual(load_json(self.output_root / "2026-10-14/result.json"), result)
        self.assertTrue((self.output_root / "2026-10-14/reconcile.json").is_file())
        self.assertEqual(result["commit_sha"], COMMIT)
        self.assertEqual(result["exposure"]["E"], 1.5)
        self.assertEqual(result["compare"], {"streak": 0, "last_mismatch": {"reason": "NO_PREVIOUS_WOULD_APPLY",
                                                                            "codes": []}})
        self.assertIsNone(result["next_action_for_user"])
        symbols = {item[0] for item in self.collected}
        self.assertEqual(symbols, {"AAA", "BBB", "NEWW", "SOXX"})
        newcomer = next(item for item in self.collected if item[0] == "NEWW")
        self.assertEqual(newcomer, ("NEWW", "NASDAQ", "2026-10-14", "2026-04-01"))
        self.assertIn(("AAA", "NASDAQ", "2026-10-14", "2026-10-12"), self.collected)

    def test_first_failure_stops_the_run(self):
        def failing(symbol, exchange, **kwargs):
            raise auto_core.StepFailure(f"BAR_COLLECTION_FAILED:{symbol}:1")
        result = self.daily(sale_broker(), collector=failing)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("BAR_COLLECTION_FAILED:AAA:1", result["reasons"])
        self.assertEqual(self.exposure_calls, 0)
        self.assertEqual(load_json(self.output_root / "LATEST.json")["status"], "FAIL")

    def test_reconcile_failure_is_a_fail_and_stops(self):
        broker = sale_broker()
        with mock.patch.object(core, "normalize_snapshot", side_effect=core.AutoReconcileError("BROKEN")):
            result = self.daily(broker)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(self.collected, [])

    def test_kill_switch_daily_is_hold_without_reads(self):
        broker = sale_broker()
        self.config("compare", kill_switch=True)
        result = auto_core.daily(
            output_root=self.output_root, config_path=self.config_path, now=NOW, reader=broker,
            collector=self.collector, history_updater=self.updater, exposure_runner=self.exposure,
            provenance={"status": "OK", "commit_sha": COMMIT, "dirty_paths": [], "guarded_dirty_paths": []},
            policy_paths=self.policies, closes_root=self.closes, watchlist_path=self.watchlist,
            evidence_root=self.evidence_root)
        self.assertEqual((result["status"], result["reasons"]), ("HOLD", ["KILL_SWITCH_ON"]))
        self.assertEqual((broker.requests, self.collected, self.exposure_calls), ([], [], 0))

    def test_compare_streak_counts_explained_days_and_announces_readiness(self):
        # Runs on KST 10/14, 10/16, 10/17, 10/18: the streak counts runs, and from 10/16 the sale (settled on
        # KST 10/15 at 08:07, after that day's 06:15 run) is a transaction-history trade row.
        days = [NOW + timedelta(days=offset) for offset in (0, 2, 3, 4)]
        streaks = []
        for index, moment in enumerate(days):
            # Day 0 reads the filled sale; later days read the settled account (the fill stays in the history).
            broker = sale_broker() if index == 0 else settled_sale_broker(moment)
            result = self.daily(broker, now=moment)
            self.assertEqual(result["status"], "OK", result["reasons"])
            streaks.append(result["compare"]["streak"])
        self.assertEqual(streaks, [0, 1, 2, 3])
        self.assertEqual(result["next_action_for_user"], "기록 모드 켤 준비됨")
        # The same day again gives the same streak (counted against the previous day only).
        again = self.daily(settled_sale_broker(days[-1]), now=days[-1])
        self.assertEqual(again["compare"]["streak"], 3)

    def test_unexplained_day_resets_the_streak(self):
        self.daily(sale_broker())
        wrong = FakeBroker(holdings=[holding("AAA", 6, settled=10), holding("BBB", 5)], ord_cash="1329.17",
                           pymn_cash="1000.00", retrieved=NOW + timedelta(days=1, seconds=-5))
        result = self.daily(wrong, now=NOW + timedelta(days=1))
        self.assertEqual(result["compare"]["streak"], 0)
        self.assertEqual(result["status"], "HOLD")

    # T1 r3 ----------------------------------------------------------------------------------

    def quiet(self, moment):
        return FakeBroker(holdings=[holding("AAA", 10), holding("BBB", 5)], ord_cash="1000.00", pymn_cash="1000.00",
                          retrieved=moment - timedelta(seconds=5))

    def test_warnings_reach_result_and_latest_without_blocking_the_record(self):
        # C3: proposal warnings and post-apply check errors; the record is still written.
        def check(policy):
            return lambda state, proposal: {"check": "TEST", "session_date": "2026-10-13", "status": "FAIL",
                                            "errors": ["AAA anchor_shares 10 != holdings 7"],
                                            "policy_positions_mismatch": True}
        with mock.patch.object(cli, "alert_engine_check", check):
            result = self.daily(sale_broker(), mode="apply")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertIsNotNone(result["applied"])
        proposal = load_json(self.output_root / "2026-10-14/reconciliation_proposal.json")
        self.assertTrue({"TIMING_PLAN_TICKER_CHANGED", "POST_APPLY_ALERT_ENGINE_CHECK_FAILED",
                         "POLICY_POSITIONS_MISMATCH"} <= set(proposal["warnings"]))
        expected = [f"PROPOSAL_WARNING:{code}" for code in proposal["warnings"]] + [
            "POST_APPLY_CHECK_ERROR:AAA anchor_shares 10 != holdings 7"]
        self.assertEqual(result["warnings"], expected)
        self.assertEqual(load_json(self.output_root / "LATEST.json")["warnings"], expected)
        self.assertEqual(load_json(self.output_root / "2026-10-14/reconcile.json")["warnings"], expected)
        self.assertEqual(validate_instance(result, SCHEMAS / "auto-core-result.schema.json"), [])

    def test_settlement_day_counts_with_the_previous_runs_pending_amount(self):
        # C4 (a): runs on KST 10/14, 10/15 (the sale settles today, not shown before ~08:07), 10/16, 10/17.
        brokers = [sale_broker(), d0_broker()] + [settled_sale_broker(NOW + timedelta(days=offset))
                                                  for offset in (2, 3)]
        streaks = []
        for offset, broker in enumerate(brokers):
            result = self.daily(broker, now=NOW + timedelta(days=offset))
            self.assertEqual(result["status"], "OK", result["reasons"])
            streaks.append(result["compare"]["streak"])
        self.assertEqual(streaks, [0, 1, 2, 3])
        self.assertEqual(result["next_action_for_user"], "기록 모드 켤 준비됨")
        d0_day = load_json(self.output_root / "2026-10-15/reconcile.json")
        self.assertEqual(d0_day["invariants"]["I3"]["settlements"][0]["source"], "PENDING_PREVIOUS_RUN")

    def test_day_held_only_for_an_unseen_settlement_keeps_the_streak(self):
        # C4 (b): AAA 3 sold in the after-hours of the U.S. 10/14 session (KST 10/15 07:07, after that day's
        # run), settling KST 10/16. The 10/16 run has no earlier read of it.
        late = dict(holdings=[holding("AAA", 7, settled=10), holding("BBB", 5)], ord_cash="1329.17",
                    pymn_cash="1000.00",
                    fills={"20261015": [fill("AAA", SELL, 3, "110.0000", order_no="0007", ord_time="06:50:00",
                                             cntr_time="07:07:00")]},
                    day_trades={"20261014": [day_trade("AAA", sold=3, sell_amount="330.00", fees="0.83")]},
                    detail={"d1_setl_dt": "20261019", "d1_usd_sell_excta": "0.00", "d1_usd_buy_excta": "0.00"})
        days = [NOW + timedelta(days=offset) for offset in range(4)]
        brokers = [self.quiet(days[0]), self.quiet(days[1]),
                   FakeBroker(**late, retrieved=days[2] - timedelta(seconds=5)),
                   FakeBroker(**dict(late, holdings=[holding("AAA", 7), holding("BBB", 5)], pymn_cash="1329.17",
                                     detail={}, history=[trade_row("20261016", "000000001", "AAA", SELL, 3, "330.00",
                                                                   "0.83", "329.17")]),
                              retrieved=days[3] - timedelta(seconds=5))]
        results = [self.daily(broker, now=moment) for broker, moment in zip(brokers, days)]
        self.assertEqual([item["status"] for item in results], ["OK", "OK", "HOLD", "OK"],
                         [item["reasons"] for item in results])
        self.assertEqual([item["compare"]["streak"] for item in results], [0, 1, 1, 2])
        kept = results[2]
        self.assertEqual(kept["reasons"], ["I3:SETTLEMENT_D0_NOT_SHOWN:2026-10-16"])
        self.assertEqual(kept["compare"], {"streak": 1, "last_mismatch": None, "basis": "KEPT_D0_SETTLEMENT_NOT_SHOWN",
                                           "kept_reasons": ["I3:SETTLEMENT_D0_NOT_SHOWN:2026-10-16"]})
        self.assertIsNone(kept["next_action_for_user"])
        # The day after continues from the 10/15 would_apply (the held day has none).
        self.assertEqual(results[3]["compare"]["basis"], "EXPLAINED_BY_FILLS")
        self.assertEqual(validate_instance(kept, SCHEMAS / "auto-core-result.schema.json"), [])

    def test_old_record_in_compare_mode_asks_for_recording_instead_of_failing(self):
        # C4: the record is from KST 10/13; its fill window passes 80% of 14 days on KST 10/23 (12 days).
        line = "기록 모드 켜기 필요(기준 오래됨)"
        before_limit = NOW + timedelta(days=8)  # KST 10/22: 11 days
        result = self.daily(self.quiet(before_limit), now=before_limit)
        self.assertEqual((result["status"], result["next_action_for_user"]), ("OK", None), result["reasons"])
        stale = NOW + timedelta(days=9)  # KST 10/23: 12 days
        result = self.daily(self.quiet(stale), now=stale)
        self.assertEqual((result["status"], result["next_action_for_user"]), ("OK", line), result["reasons"])
        self.assertEqual(load_json(self.output_root / "LATEST.json")["next_action_for_user"], line)
        self.assertEqual(load_json(self.output_root / "2026-10-23/reconcile.json")["fill_window"],
                         {"days": 12, "maximum_days": 14})
        # Over the limit the reconciliation still fails and writes nothing; the line stays.
        before = self.snapshot_files()
        over = NOW + timedelta(days=12)  # KST 10/26: 15 days
        result = self.daily(self.quiet(over), now=over)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("FILL_WINDOW_TOO_LONG:15", result["reasons"])
        self.assertEqual(result["next_action_for_user"], line)
        self.assertEqual(self.snapshot_files(), before)

    def test_old_record_line_is_for_compare_mode_only(self):
        stale = NOW + timedelta(days=9)
        result = self.daily(self.quiet(stale), now=stale, mode="apply")
        self.assertEqual(result["status"], "OK", result["reasons"])
        self.assertIsNone(result["next_action_for_user"])

    def test_a_failed_step_never_counts_toward_the_streak(self):
        # C5: the reconciliation of 10/16 is explained, but a later step fails: the streak is not raised.
        self.daily(sale_broker())

        def failing(symbol, exchange, **kwargs):
            raise auto_core.StepFailure(f"BAR_COLLECTION_FAILED:{symbol}:1")

        def broken_exposure():
            raise auto_core.StepFailure("EXPOSURE_REVIEW_FAILED:TEST")
        moment = NOW + timedelta(days=2)
        for step, kwargs in {"bars": {"collector": failing}, "exposure": {"exposure_runner": broken_exposure}}.items():
            with self.subTest(step=step):
                result = self.daily(settled_sale_broker(moment), now=moment, **kwargs)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["steps"]["reconcile"]["status"], "OK")
                self.assertEqual(result["compare"]["streak"], 0)
                self.assertEqual(result["compare"]["last_mismatch"]["reason"], "RUN_FAILED")
                self.assertEqual(load_json(self.output_root / "LATEST.json")["compare"]["streak"], 0)
        # The next good day counts again from 0.
        later = NOW + timedelta(days=3)
        self.assertEqual(self.daily(settled_sale_broker(later), now=later)["compare"]["streak"], 1)

    def test_missing_profile_alias_fails_before_any_read(self):
        # C6: the token profile alias is required; nothing is read or collected without it.
        for name, policy in {"empty": {"official_runtime_path": str(self.runtime), "token_profile_alias": ""},
                             "blank": {"official_runtime_path": str(self.runtime), "token_profile_alias": "  "},
                             "missing": {"official_runtime_path": str(self.runtime)}}.items():
            with self.subTest(case=name):
                self.policies["readonly"].write_text(json.dumps(policy), encoding="utf-8")
                broker = sale_broker()
                before = self.snapshot_files()
                result = self.daily(broker)
                self.assertEqual((result["status"], result["reasons"]), ("FAIL", ["KIWOOM_PROFILE_ALIAS_MISSING"]))
                self.assertEqual((broker.requests, self.collected, self.exposure_calls), ([], [], 0))
                self.assertNotIn("reconcile", result["steps"])
                self.assertEqual(result["warnings"], [])
                self.assertEqual(self.snapshot_files(), before)
        self.policies["readonly"].write_text(json.dumps({"official_runtime_path": str(self.runtime),
                                                          "token_profile_alias": "TEST_PROFILE"}), encoding="utf-8")
        self.assertEqual(self.daily(sale_broker())["status"], "OK")
        self.assertEqual(self.profiles, {"TEST_PROFILE"})


class ProvenanceAndConfigTests(unittest.TestCase):
    def test_git_provenance_parses_status_and_guards_pinned_files(self):
        class Done:
            def __init__(self, stdout, code=0):
                self.stdout, self.returncode = stdout, code
        outputs = iter([Done(COMMIT + "\n"), Done(
            " M manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py\0?? workspace/outputs/auto-core/x.json\0"
            "R  docs/claude/new.md\0docs/claude/old.md\0")])
        value = core.git_provenance(guarded=["manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py"],
                                    runner=lambda *args, **kwargs: next(outputs))
        self.assertEqual(value["commit_sha"], COMMIT)
        self.assertEqual(value["dirty_paths"], ["docs/claude/new.md",
                                                "manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py"])
        self.assertEqual(value["guarded_dirty_paths"], ["manage-us-stock-strategy/scripts/kiwoom_broker_shadow.py"])
        self.assertEqual(core.apply_guard_reasons("compare", value), [])
        self.assertTrue(core.apply_guard_reasons("apply", value)[0].startswith("GUARDED_FILES_UNCOMMITTED"))
        failed = core.git_provenance(guarded=[], runner=lambda *args, **kwargs: Done("", 128))
        self.assertEqual(failed["status"], "UNAVAILABLE")

    def test_apply_guard_covers_every_tracked_file_under_scripts_schemas_and_assets(self):
        # T1 r3 C2: modified, staged, deleted and renamed (both names) tracked files; untracked files, tests,
        # references and docs only through the former pin list.
        root = "manage-us-stock-strategy/"
        status = "\0".join([
            f" M {root}scripts/validation_common.py", f"M  {root}schemas/kiwoom-broker-shadow.schema.json",
            f" D {root}scripts/evaluate_alerts.py", f"MM {root}scripts/portfolio_exposure.py",
            f" M {root}scripts/portfolio_review_journal.py", f"A  {root}assets/new-table.json",
            f"R  {root}scripts/renamed.py", f"{root}scripts/original.py",
            f" M {root}tests/test_state_write_boundary.py", f" M {root}tests/test_auto_core.py",
            f" M {root}references/portfolio-exposure-review.md", f"?? {root}scripts/scratch_note.py",
            " M docs/claude/redesign-t1-builder-report-2026-10-10.md"]) + "\0"
        value = core.git_provenance(runner=fake_git(status))
        self.assertEqual(value["guarded_dirty_paths"], sorted(root + path for path in (
            "scripts/validation_common.py", "schemas/kiwoom-broker-shadow.schema.json", "scripts/evaluate_alerts.py",
            "scripts/portfolio_exposure.py", "scripts/portfolio_review_journal.py", "assets/new-table.json",
            "scripts/renamed.py", "scripts/original.py", "tests/test_state_write_boundary.py")))
        self.assertIn(root + "scripts/scratch_note.py", value["dirty_paths"])
        self.assertTrue(core.apply_guard_reasons("apply", value)[0].startswith("GUARDED_FILES_UNCOMMITTED:"))
        self.assertEqual(core.apply_guard_reasons("compare", value), [])
        self.assertEqual(core.git_provenance(runner=fake_git(f" M {root}tests/test_auto_core.py\0"))
                         ["guarded_dirty_paths"], [])

    def test_retired_pin_scope_is_the_guarded_set(self):
        scope = load_json(ROOT / "manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json")
        self.assertEqual(scope["status"], "RETIRED")
        self.assertEqual(validate_instance(scope, SCHEMAS / "kiwoom-acceptance-pin-scope.schema.json"), [])
        guarded = set(core.guarded_paths())
        self.assertTrue(set(scope["required_implementation_paths"]) <= guarded)
        self.assertTrue(set(core.AUTO_CORE_GUARDED_PATHS) <= guarded)

    def test_policy_proposal_matches_the_config_schema(self):
        proposals = load_json(ROOT / "docs/claude/redesign-t1-policy-proposals.json")
        content = proposals["proposals"][0]["content"]
        self.assertEqual(proposals["proposals"][0]["path"], "workspace/policies/auto_core.json")
        self.assertEqual(content, {"mode": "compare", "kill_switch": False, "compare_days_required": 3,
                                   "schedule_kst": "06:15", "symbols_extra": ["SOXX"]})
        self.assertEqual(validate_instance(content, SCHEMAS / "auto-core-config.schema.json"), [])
        self.assertTrue(validate_instance(dict(content, mode="auto"), SCHEMAS / "auto-core-config.schema.json"))


class NoOrderPathTests(unittest.TestCase):
    FILES = ("auto_core.py", "auto_core_reconcile.py", "collect_30m.ps1", "run_auto_core.ps1",
             "register_auto_core_task.ps1")

    def test_no_order_command_or_tool_on_the_auto_core_path(self):
        forbidden = re.compile(r"(/api/us/ordr|ust2000\d|overseas\s+orders|kiwoom_order|place_order|"
                               r"order_submit|\bkt1000\d)", re.IGNORECASE)
        for name in self.FILES:
            with self.subTest(file=name):
                self.assertIsNone(forbidden.search((SCRIPTS / name).read_text(encoding="utf-8")))

    def test_powershell_files_are_ascii(self):
        for name in ("collect_30m.ps1", "run_auto_core.ps1", "register_auto_core_task.ps1"):
            with self.subTest(file=name):
                (SCRIPTS / name).read_bytes().decode("ascii")

    def test_kiwoomcli_call_is_the_read_only_candle_command_with_the_profile(self):
        text = (SCRIPTS / "collect_30m.ps1").read_text(encoding="ascii")
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        commands = re.findall(r"kiwoomcli [^\"$]+", code)
        self.assertEqual(commands, ["kiwoomcli overseas candles stock-minute --exchange "])
        self.assertIn("--profile $KiwoomProfile --mode real", text)
        self.assertIn("-KiwoomProfile", (SCRIPTS / "auto_core.py").read_text(encoding="utf-8"))

    def test_collection_requires_the_profile_alias(self):
        # T1 r3 C6: -KiwoomProfile is mandatory and every call carries --profile and --mode real.
        text = (SCRIPTS / "collect_30m.ps1").read_text(encoding="ascii")
        self.assertRegex(text, r"\[Parameter\(Mandatory = \$true\)\]\[ValidateNotNullOrEmpty\(\)\]\[string\]\$KiwoomProfile,")
        self.assertIn('$profileArg = " --profile $KiwoomProfile --mode real"', text)
        self.assertNotIn("$KiwoomProfile = ''", text)
        self.assertNotIn("if ($KiwoomProfile -ne '')", text)

    def test_claude_code_sessions_cannot_run_the_auto_core(self):
        # T1 r3 T1B-1: compare also reads Kiwoom; only the Windows task (not Claude Code) runs it.
        deny = set(load_json(ROOT / ".claude/settings.json")["permissions"]["deny"])
        self.assertTrue({"Bash(*auto_core.py*)", "PowerShell(*auto_core.py*)", "Bash(*reconcile_broker_state.py auto*)",
                         "PowerShell(*reconcile_broker_state.py auto*)"} <= deny)

    def test_auto_modules_import_no_order_module(self):
        for name in ("auto_core.py", "auto_core_reconcile.py"):
            tree = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
            modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
            modules |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
            with self.subTest(file=name):
                self.assertFalse({module for module in modules if "order" in module.lower()})


if __name__ == "__main__":
    unittest.main()
