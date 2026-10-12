"""Redesign T2 F7/F8/F11: the decide run, the journal entries and the Windows task scripts.

All inputs are synthetic (TEST_ONLY): temporary output, state, journal, research and registry folders, a fake
read-only bridge, a fixed clock and a fake S7 runner built on the real S7 module. No network, no Kiwoom.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
FIXTURES = ROOT / "manage-us-stock-strategy/tests/fixtures/auto_core_t2"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(FIXTURES))

import auto_core_decide as decide_module  # noqa: E402
import auto_core_inputs as inputs  # noqa: E402
import helpers  # noqa: E402
import portfolio_review_journal as journal_module  # noqa: E402
from portfolio_exposure import journal_view  # noqa: E402
from validation_common import canonical_hash, load_json, validate_instance, write_json  # noqa: E402

DAYS = helpers.sessions("2026-06-01", 95)
LAST = DAYS[-1]
# The calendar runs past the last saved session (the buy session and later exist, as in production).
CALENDAR_DAYS = helpers.sessions("2026-06-01", 100)
# 07:45 KST on the day after the last session.
NOW = datetime.fromisoformat(f"{LAST}T16:00:00-04:00").astimezone(timezone.utc) + timedelta(hours=2, minutes=45)
RUN_DAY = (NOW + timedelta(hours=9)).date().isoformat()
COMMIT = "a" * 40
CARD_TEXT = "# Test card\n\n## MU\n\nTEST_ONLY section body.\n\n## Other\n\nmore\n"


class FakeReader:
    def __init__(self, *, fills=None, open_items=None, failing=()):
        self.fills, self.open_items, self.failing = fills or {}, open_items or [], set(failing)
        self.requests = []

    def __call__(self, requests, *, runtime, policy):
        self.requests.extend(requests)
        out = []
        for request in requests:
            operation = request["operation"]
            day = (request.get("params") or {}).get("ord_dt")
            if operation in self.failing or (day and day in self.failing):
                out.append({"operation": operation, "bridge_status": "KIWOOM_API_RESPONSE_ERROR", "data": [],
                            "request_params": request.get("params")})
                continue
            data = self.open_items if operation == "account_open_items" else self.fills.get(day, [])
            out.append({"operation": operation, "bridge_status": "PASS", "data": data,
                        "pagination": {"complete": True}, "request_params": request.get("params")})
        return out


class Env:
    """A temporary repository-like folder with everything decide reads. The default cash keeps the account above
    the V6 first line (r2 R2-3: this session's EV4 now opens R-REC1)."""

    def __init__(self, *, holdings=None, cash="30000.00", decision_mode="compare", kill=False, profile=True,
                 research=True, members=("MU",), soxl_closes=None, journal_entries=True):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.holdings = holdings if holdings is not None else {"SOXL": 40}
        self.cash = Decimal(cash)
        self.output = self.root / "auto-core"
        self.day_dir = self.output / RUN_DAY
        self.day_dir.mkdir(parents=True)
        self.docs = self.root / "docs/claude"
        self.docs.mkdir(parents=True)
        (self.docs / "TEST_ONLY.md").write_text(CARD_TEXT, encoding="utf-8")
        (self.docs / "m6-relative-comparison-7stock-TEST.md").write_text("MU SOXL", encoding="utf-8")
        (self.docs / "recovery-gate-R-REC1-2026-10-09.md").write_text("no event line\n", encoding="utf-8")
        self.config = self.root / "auto_core.json"
        write_json(self.config, {"mode": "compare", "kill_switch": kill, "compare_days_required": 3,
                                 "schedule_kst": "06:15", "symbols_extra": ["SOXX"], "decision_mode": decision_mode})
        self.readonly = self.root / "readonly.json"
        write_json(self.readonly, {"token_profile_alias": "TEST" if profile else "", "official_runtime_path": str(self.root)})
        self.rate = self.root / "rate.json"
        write_json(self.rate, {})
        self.state = self.root / "portfolio_state.json"
        write_json(self.state, {"holdings": dict(self.holdings), "available_cash_usd": float(self.cash)})
        self.journal = self.root / "decision_journal.json"
        if journal_entries:
            write_json(self.journal, {"schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL",
                                      "order_authority": False, "quantity_authority": "none", "entries": []})
        write_json(self.day_dir / "result.json", {"status": "OK"})
        write_json(self.day_dir / "reconcile.json", {"status": "OK", "fills": []})
        write_json(self.day_dir / "kiwoom_broker_snapshot.shadow.json", {
            "holdings": [{"ticker": symbol, "held_quantity": quantity} for symbol, quantity in self.holdings.items()],
            "cash": {"order_available_cash": float(self.cash), "foreign_currency_deposit": float(self.cash)}})
        self.watchlist = self.docs / "watchlist-registry.json"
        write_json(self.watchlist, {"members": [{"code": code, "cardStatus": "수락(2026-10-02)", "sector": "B1"}
                                                for code in members]})
        entry = helpers.entry("MU", triggers=[], static=[{
            "id": "MU-SE1", "e1_kind": "thesis", "strength": "strong", "direction": "+", "as_of": "2026-10-02",
            "source": "docs/claude/TEST_ONLY.md:3", "quote": "TEST_ONLY"}])
        entry.update(card_doc="docs/claude/TEST_ONLY.md", card_section="## MU",
                     section_sha256=inputs.section_sha256(CARD_TEXT, "## MU"))
        soxl = helpers.entry("SOXL", role="holding", action="HOLD")
        soxl.update(card_doc="docs/claude/TEST_ONLY.md", card_section="## MU",
                    section_sha256=inputs.section_sha256(CARD_TEXT, "## MU"))
        self.registry = self.docs / "card-evidence-registry.json"
        write_json(self.registry, {"schema_version": "card-evidence-registry-1.0", "registry_type": "AUTO_CORE_CARD_REGISTRY",
                                   "updated_at": "2026-10-10", "updated_by": "TEST_ONLY", "rule": "TEST_ONLY",
                                   "order_authority": False, "quantity_authority": "none",
                                   "symbols": {"MU": entry, "SOXL": soxl}})
        self.research_root = self.root / "research-records"
        if research:
            self.write_research()
        count = len(DAYS)
        self.bars = {
            "SOXL": helpers.bars("SOXL", DAYS, soxl_closes or helpers.zigzag(count, 100, 2.0, 0.05)),
            "SOXX": helpers.bars("SOXX", DAYS, helpers.zigzag(count, 500, 4.0, 0.3)),
            "MU": helpers.bars("MU", DAYS, helpers.zigzag(count, 200, 3.0, 0.2)),
        }
        self.policy = helpers.policy()

    def write_research(self, *, facts=None, run=None, written=None, earnings=None):
        folder = self.research_root / RUN_DAY
        folder.mkdir(parents=True, exist_ok=True)
        write_json(folder / "research-record.json", {
            "schema_version": "auto-core-research-record-1.0", "record_day_kst": RUN_DAY, "evaluation_session": LAST,
            "written_at": written or (NOW - timedelta(minutes=50)).isoformat(), "writer": "TEST_ONLY",
            "earnings": earnings or {"MU": {"status": "VERIFIED", "announcement_session": DAYS[-30],
                                            "timing": "AFTER_CLOSE", "source_kind": "SEC_FILING",
                                            "source_url": "https://www.sec.gov/test"}},
            "official_facts": facts or [], "integrated_check_run": run, "order_authority": False,
            "quantity_authority": "none"})

    def write_good_news(self):
        """MU: a new official good-news fact (criterion (a)) and a confirmed 'not announced' earnings check."""
        self.write_research(
            facts=[{"fact_id": "MU-FACT-1", "symbol": "MU", "direction": "+", "kind": "contract",
                    "card_trigger_ids": ["U2"], "event_session": LAST, "announced_at": f"{LAST}T16:30:00-04:00",
                    "source_kind": "SEC_FILING", "source_url": "https://www.sec.gov/test", "criterion_a": True,
                    "root_thesis_damage": False, "summary_ko": "TEST_ONLY"}],
            earnings={"MU": {"status": "NOT_ANNOUNCED", "source_kind": "SEC_FILING",
                             "source_url": "https://www.sec.gov/test", "checked_at": f"{LAST}T16:40:00-04:00"}})

    def bars_loader(self, symbol, evaluation_session):
        return self.bars.get(symbol) or helpers.missing_bars(symbol)

    def exposure_runner(self, output_directory, earnings, proposals):
        closes = helpers.closes_of(self.bars)
        runner = helpers.s7_runner(policy_value=self.policy, days=CALENDAR_DAYS, evaluation_session=LAST,
                                   holdings=self.holdings, cash=self.cash, closes=closes, earnings=earnings)
        return {"review": runner(proposals), "path": None}

    def run(self, **overrides):
        clock_value = [NOW]

        def clock():
            return clock_value[0]

        def sleeper(seconds):
            clock_value[0] = clock_value[0] + timedelta(seconds=seconds)

        arguments = dict(
            output_root=self.output, config_path=self.config, now=NOW, clock=clock, sleeper=sleeper,
            reader=FakeReader(), exposure_runner=self.exposure_runner,
            provenance={"status": "OK", "commit_sha": COMMIT, "dirty_paths": [], "guarded_dirty_paths": []},
            provenance_source=lambda: {"status": "OK", "commit_sha": COMMIT, "dirty_paths": [], "guarded_dirty_paths": []},
            policy_paths={"readonly": self.readonly, "rate": self.rate, "alert": helpers.POLICY_PATH,
                          "state": self.state, "journal": self.journal},
            research_root=self.research_root, registry_path=self.registry, watchlist_path=self.watchlist,
            docs_dir=self.docs, explained_path=self.root / "explained.json", repo=self.root,
            registry_committed_check=lambda path, repo: (True, None), calendar_loader=lambda now: helpers.calendar(CALENDAR_DAYS),
            score_runner=lambda path: None, bars_loader=self.bars_loader)
        arguments.update(overrides)
        self.last_clock = clock_value
        return decide_module.decide(**arguments)

    def close(self):
        self.temp.cleanup()


class DecideRunTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def test_compare_run_is_schema_valid_and_writes_no_journal(self):
        before = self.env.journal.read_bytes()
        decision = self.env.run()
        self.assertEqual(validate_instance(decision, decide_module.DECISION_SCHEMA), [])
        self.assertIn(decision["status"], ("OK", "HOLD"), decision["reasons"])
        self.assertEqual(decision["decision_mode"], "compare")
        self.assertEqual(decision["journal"]["appended"], [])
        self.assertIn("core_decision", decision["journal"]["would_append"])
        self.assertEqual(self.env.journal.read_bytes(), before)
        self.assertTrue((self.env.day_dir / "decision.json").is_file())
        self.assertTrue((self.env.output / "LATEST_DECISION.json").is_file())
        self.assertTrue((self.env.day_dir / "compare.json").is_file())
        self.assertFalse(decision["order_authority"])
        self.assertIsNone(decision["execution_quantity"])
        self.assertEqual(decision["dashboard"]["orders"], [])

    def test_t1_result_missing_is_hold_without_tickets(self):
        (self.env.day_dir / "result.json").unlink()
        decision = self.env.run()
        self.assertEqual(decision["status"], "HOLD")
        self.assertEqual(decision["reasons"], ["T1_RESULT_MISSING"])
        self.assertEqual(decision["tickets"], [])

    def test_t1_failed_is_hold(self):
        write_json(self.env.day_dir / "result.json", {"status": "FAIL"})
        decision = self.env.run()
        self.assertEqual((decision["status"], decision["reasons"]), ("HOLD", ["T1_NOT_OK"]))

    def test_kill_switch_holds_before_any_read(self):
        env = Env(kill=True)
        try:
            reader = FakeReader()
            decision = env.run(reader=reader)
            self.assertEqual((decision["status"], decision["reasons"]), ("HOLD", ["KILL_SWITCH_ON"]))
            self.assertEqual(reader.requests, [])
        finally:
            env.close()

    def test_profile_alias_missing_fails_before_any_read(self):
        env = Env(profile=False)
        try:
            reader = FakeReader()
            decision = env.run(reader=reader)
            self.assertEqual(decision["status"], "FAIL")
            self.assertIn("KIWOOM_PROFILE_ALIAS_MISSING", decision["reasons"])
            self.assertEqual(reader.requests, [])
        finally:
            env.close()

    def test_apply_mode_with_uncommitted_guarded_file_fails(self):
        env = Env(decision_mode="apply")
        try:
            decision = env.run(provenance={"status": "OK", "commit_sha": COMMIT, "dirty_paths": ["x"],
                                           "guarded_dirty_paths": ["manage-us-stock-strategy/scripts/x.py"]})
            self.assertEqual(decision["status"], "FAIL")
            self.assertTrue(decision["reasons"][0].startswith("GUARDED_FILES_UNCOMMITTED"))
        finally:
            env.close()

    def test_research_wait_polls_every_five_minutes_until_0830(self):
        env = Env(research=False)
        try:
            decision = env.run()
            wait = decision["inputs"]["research_record"]["wait"]
            self.assertFalse(wait["found"])
            self.assertEqual(wait["waited_seconds"], 45 * 60)  # 07:45 -> 08:30 in 5-minute steps
            self.assertEqual(decision["inputs"]["research_record"]["status"], "MISSING")
            mu = next(row for row in decision["buy_requirements"] if row["code"] == "MU")
            self.assertEqual(mu["c"][0]["s"], "no")  # no earnings record = blackout (fail closed)
        finally:
            env.close()

    def test_same_day_twice_gives_the_same_judgments(self):
        first = self.env.run()
        second = self.env.run()
        for key in ("status", "reasons", "tickets", "buy_requirements", "symbols", "no_action", "evidence"):
            self.assertEqual(first[key], second[key], key)

    def test_research_record_written_too_early_counts_as_missing(self):
        self.env.write_research(written=f"{LAST}T15:00:00-04:00")
        decision = self.env.run()
        self.assertEqual(decision["inputs"]["research_record"]["status"], "INVALID")
        self.assertIn("RESEARCH_RECORD_WRITTEN_AT_OUT_OF_RANGE", decision["inputs"]["research_record"]["reasons"])

    def test_state_not_equal_to_broker_blocks_every_ticket(self):
        write_json(self.env.state, {"holdings": {"SOXL": 41}, "available_cash_usd": float(self.env.cash)})
        decision = self.env.run()
        self.assertIn("G1_STATE_NOT_EQUAL_BROKER", decision["reasons"])
        self.assertEqual(decision["tickets"], [])

    def test_open_orders_fail_g0(self):
        decision = self.env.run(reader=FakeReader(open_items=[{"stk_cd": "SOXL"}]))
        self.assertIn("G0_OPEN_ORDERS:1", decision["reasons"])
        self.assertEqual(decision["tickets"], [])

    def test_outcome_read_failure_keeps_ticket_open_and_fails_g0(self):
        first = self.env.run()
        previous = _as_of(copy.deepcopy(first), "2026-10-01")
        ticket = _fake_ticket("SOXL", "sell", 5, 95.0)
        previous["tickets"] = [ticket]
        folder = self.env.output / "2026-10-01"
        folder.mkdir()
        write_json(folder / "decision.json", previous)
        decision = self.env.run(reader=FakeReader(failing={"20261001"}))
        self.assertTrue(any(reason.startswith("OUTCOME_UNKNOWN") for reason in decision["reasons"]))
        self.assertEqual([item["ticket_id"] for item in decision["open_tickets"]], [ticket["ticket_id"]])
        self.assertTrue(any(alert["code"] == "OUTCOME_UNKNOWN" and alert["push"] for alert in decision["alerts"]))


def _fake_ticket(symbol, side, qty, price, mode="compare"):
    return {"ticket_id": f"AT-20261001-{symbol}-1", "mode": mode, "issuedAt": "2026-10-01 07:45 KST",
            "session": "2026-10-01", "ticker": symbol, "side": side, "type": "LOC", "price": price, "qty": qty,
            "priceCalc": {"mult": 0.95, "round": "up", "lo": 99.0, "hi": 101.0, "label": "TEST_ONLY"},
            "decision_key": "b" * 64, "issued_day": "2026-10-01"}


def _as_of(record, run_day):
    """A copied record dated run_day with that day's evaluation and buy sessions. r3 R3-3 reads a record that
    keeps the copied run's sessions (a record of 10/01 that evaluated 10/09) as 'no new session since'."""
    from run_portfolio_exposure_review import expected_completed_session

    evaluation = expected_completed_session(helpers.calendar(CALENDAR_DAYS), _morning(run_day))
    record.update(run_day_kst=run_day, evaluation_session=evaluation,
                  buy_session=next(day for day in CALENDAR_DAYS if day > evaluation))
    return record


class JournalEntryTests(unittest.TestCase):
    """F7: recording mode appends core_decision (+ tickets, outcomes); compare mode never writes."""

    def setUp(self):
        self.env = Env(decision_mode="apply")

    def tearDown(self):
        self.env.close()

    def test_apply_appends_a_hash_chained_core_decision_once(self):
        decision = self.env.run()
        self.assertEqual(decision["status"], "OK", decision["reasons"])
        self.assertEqual(decision["journal"]["appended"][0], "core_decision")
        loaded = journal_module.load_journal(self.env.journal)
        self.assertEqual(loaded["status"], "OK", loaded["errors"])
        entry = loaded["entries"][0]
        self.assertEqual(entry["confirmation_method"], "AUTO_CORE")
        self.assertIsNone(entry["confirm_code"])
        self.assertIsNone(entry["user_message"])
        self.assertEqual(entry["review_id"], decision["journal"]["decision_sha256"])
        self.assertEqual(entry["quantity_authority"], "none")
        # r2 R2-5 (prompt F8 "the same day twice = the same result"): the rerun writes nothing and stays OK.
        before = (self.env.day_dir / "decision.json").read_bytes()
        again = self.env.run()
        self.assertEqual(again["status"], "OK", again["reasons"])
        self.assertEqual(again["journal"]["appended"], [])
        self.assertEqual(again["journal"]["decision_sha256"], decision["journal"]["decision_sha256"])
        self.assertEqual(again["journal"]["already_recorded"], decision["journal"]["decision_sha256"])
        self.assertEqual(len(journal_module.load_journal(self.env.journal)["entries"]), len(loaded["entries"]))
        self.assertEqual((self.env.day_dir / "decision.json").read_bytes(), before)
        self.assertEqual(list(self.env.day_dir.glob("decision.rerun-*.json")), [])

    def test_recheck_failure_writes_nothing(self):
        before = self.env.journal.read_bytes()
        decision = self.env.run(provenance_source=lambda: {"status": "OK", "commit_sha": COMMIT, "dirty_paths": ["x"],
                                                            "guarded_dirty_paths": ["manage-us-stock-strategy/scripts/x.py"]})
        self.assertEqual(decision["status"], "FAIL")
        self.assertTrue(any("AUTO_CORE_RECHECK_FAILED" in reason for reason in decision["reasons"]))
        self.assertEqual(self.env.journal.read_bytes(), before)

    def test_journal_changed_since_start_writes_nothing(self):
        original = journal_module.append_auto_core_entries

        def changed(**kwargs):
            return original(**{**kwargs, "expected_head": "f" * 64})

        journal_module.append_auto_core_entries = changed
        try:
            before = self.env.journal.read_bytes()
            decision = self.env.run()
        finally:
            journal_module.append_auto_core_entries = original
        self.assertEqual(decision["status"], "FAIL")
        self.assertEqual(self.env.journal.read_bytes(), before)

    def test_crlf_journal_keeps_crlf(self):
        raw = self.env.journal.read_bytes().replace(b"\n", b"\r\n")
        self.env.journal.write_bytes(raw)
        self.env.run()
        data = self.env.journal.read_bytes()
        self.assertIn(b"\r\n", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))


class TicketFlowTests(unittest.TestCase):
    """A ticket in each mode, its journal entry and dashboard row, and the next day's classification."""

    def test_compare_ticket_is_not_for_entry(self):
        env = Env(holdings={"SOXL": 10})
        self.addCleanup(env.close)
        env.write_good_news()
        decision = env.run()
        self.assertEqual(len(decision["tickets"]), 1, decision["blocked"])
        ticket = decision["tickets"][0]
        self.assertEqual((ticket["ticker"], ticket["side"], ticket["mode"]), ("MU", "buy", "compare"))
        self.assertEqual(ticket["note"], decide_module.NOT_FOR_ENTRY)
        self.assertEqual(decision["dashboard"]["orders"], [])
        self.assertEqual(decision["dashboard"]["runCore"]["tickets"][0]["note"], decide_module.NOT_FOR_ENTRY)
        self.assertFalse(any(alert["push"] for alert in decision["alerts"]))

    def test_apply_ticket_reaches_journal_and_dashboard(self):
        env = Env(holdings={"SOXL": 10}, decision_mode="apply")
        self.addCleanup(env.close)
        env.write_good_news()
        decision = env.run()
        self.assertEqual(decision["status"], "OK", decision["reasons"])
        self.assertEqual(decision["journal"]["appended"], ["core_decision", "order_ticket"])
        order = decision["dashboard"]["orders"][0]
        self.assertEqual((order["status"], order["source"], order["outcome"]), ("official", "auto-core", {"state": "pending"}))
        self.assertNotIn("option", order)
        self.assertTrue(any(alert["code"].startswith("TICKET:") and alert["push"] for alert in decision["alerts"]))
        self.assertIsNotNone(decision["next_action_for_user"])
        entries = journal_module.load_journal(env.journal)["entries"]
        payload = entries[1]["payload"]
        self.assertEqual((payload["ticker"], payload["qty"], payload["authority"]["quantity_authority"]),
                         ("MU", decision["tickets"][0]["qty"], "ORDER_TICKET_HUMAN_ENTRY"))

    def test_previous_apply_ticket_is_classified_journaled_and_ends_its_key(self):
        env = Env(decision_mode="apply")
        self.addCleanup(env.close)
        previous = env.run()
        journal_module.load_journal(env.journal)
        env.journal.write_text(json.dumps({"schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL",
                                           "order_authority": False, "quantity_authority": "none", "entries": []}),
                               encoding="utf-8")
        ticket = _fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")
        _as_of(previous, "2026-10-01").update(tickets=[ticket], open_tickets=[])
        folder = env.output / "2026-10-01"
        folder.mkdir()
        write_json(folder / "decision.json", previous)
        write_json(env.day_dir / "reconcile.json", {"status": "OK", "fills": [
            {"ticker": "SOXL", "side": "SELL", "quantity": 5, "session_date": "2026-10-01"}]})
        reader = FakeReader(fills={"20261001": [helpers.fill_row("SOXL", "매도", ordered=5, filled=5,
                                                                   price="95.00", fill_price="96.10")]})
        decision = env.run(reader=reader)
        self.assertEqual(decision["status"], "OK", decision["reasons"])
        self.assertEqual([(item["state"], item["filled_qty"]) for item in decision["outcomes"]], [("filled", 5)])
        self.assertEqual(decision["keys"]["b" * 64]["closed_reason"], "FILLED")
        self.assertIn("ticket_outcome", decision["journal"]["appended"])
        self.assertEqual(decision["open_tickets"], [])

    def test_outcome_that_disagrees_with_t1_fills_is_not_journaled(self):
        env = Env(decision_mode="apply")
        self.addCleanup(env.close)
        previous = env.run()
        env.journal.write_text(json.dumps({"schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL",
                                           "order_authority": False, "quantity_authority": "none", "entries": []}),
                               encoding="utf-8")
        _as_of(previous, "2026-10-01").update(tickets=[_fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")])
        (env.output / "2026-10-01").mkdir()
        write_json(env.output / "2026-10-01" / "decision.json", previous)
        reader = FakeReader(fills={"20261001": [helpers.fill_row("SOXL", "매도", ordered=5, filled=5,
                                                                   price="95.00")]})
        decision = env.run(reader=reader)
        self.assertTrue(decision["outcomes"][0]["reconcile_mismatch"])
        self.assertNotIn("ticket_outcome", decision["journal"]["appended"])
        self.assertTrue(any(alert["code"] == "OUTCOME_MISMATCH_WITH_RECONCILE" and alert["push"]
                            for alert in decision["alerts"]))


EMPTY_JOURNAL = {"schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL",
                 "order_authority": False, "quantity_authority": "none", "entries": []}
D_DAY = (datetime.fromisoformat(RUN_DAY) - timedelta(days=2)).date().isoformat()   # D (RUN_DAY is D+2)
D1_DAY = (datetime.fromisoformat(RUN_DAY) - timedelta(days=1)).date().isoformat()  # D+1
CLOSED_KEY = "c" * 64
CLOSED = {"first_cap": 95.0, "market_tests": 2, "consecutive_not_entered": 0, "closed": True,
          "closed_reason": "UNFILLED_TWICE", "last_ticket_id": "AT-20261001-SOXL-1"}


def _morning(day):
    """07:45 KST of a KST day."""
    return datetime.fromisoformat(f"{day}T07:45:00+09:00").astimezone(timezone.utc)


def _soxl_two_new_cues():
    """SOXL closes whose last session newly hits two + kinds (new high held C5+, pullback rebound C6+)."""
    closes = [round(100 + (0.1 if index % 2 else -0.1), 4) for index in range(len(DAYS) - 3)]
    closes[-1] = 99.9
    return closes + [100.05, 100.3, 100.5]


class ResearchRecordBuyGateTests(unittest.TestCase):
    """r2 R2-1 (Judge F-1, J6) through decide: a missing, schema-invalid or out-of-time record blocks every buy
    (the index ETF SOXL here); a record that only lost one item stays OK."""

    def env(self, **kwargs):
        env = Env(**kwargs)
        self.addCleanup(env.close)
        env.bars["SOXL"] = helpers.bars("SOXL", DAYS, _soxl_two_new_cues())
        return env

    def soxl(self, decision):
        reasons = [reason for item in decision["blocked"] if item["symbol"] == "SOXL" and item["side"] == "buy"
                   for reason in item["reasons"]]
        row = next(row for row in decision["buy_requirements"] if row["code"] == "SOXL")
        return reasons, row["c"][0]

    def test_record_not_ok_blocks_the_index_etf_buy(self):
        bad_fact = {"fact_id": "MU-1", "symbol": "MU", "direction": "+", "kind": "rumor", "card_trigger_ids": [],
                    "event_session": LAST, "announced_at": f"{LAST}T16:30:00-04:00", "source_kind": "SEC_FILING",
                    "source_url": "https://www.sec.gov/x", "criterion_a": True, "root_thesis_damage": False,
                    "summary_ko": "TEST_ONLY"}
        cases = (("RESEARCH_RECORD_MISSING", {"research": False}, None),
                 ("RESEARCH_RECORD_SCHEMA_INVALID", {}, {"facts": [bad_fact]}),
                 ("RESEARCH_RECORD_WRITTEN_AT_OUT_OF_RANGE", {}, {"written": f"{LAST}T15:00:00-04:00"}))
        for reason, env_kwargs, record in cases:
            with self.subTest(reason=reason):
                env = self.env(**env_kwargs)
                if record is not None:
                    env.write_research(**record)
                decision = env.run()
                self.assertIn({"symbol": "SOXL", "side": "buy", "trigger": "NEW_EVIDENCE"}, decision["candidates"])
                reasons, cell = self.soxl(decision)
                self.assertIn(f"RESEARCH_RECORD_NOT_OK:{reason}", reasons)
                self.assertEqual(cell["s"], "no")
                self.assertEqual([t for t in decision["tickets"] if t["side"] == "buy"], [])

    def test_one_dropped_item_keeps_the_record_ok(self):
        env = self.env()
        env.write_research(facts=[{"fact_id": "MU-9", "symbol": "MU", "direction": "+", "kind": "contract",
                                   "card_trigger_ids": [], "event_session": LAST,
                                   "announced_at": f"{LAST}T16:30:00-04:00", "source_kind": "SEC_FILING",
                                   "source_url": "https://news.example.org/x", "criterion_a": True,
                                   "root_thesis_damage": False, "summary_ko": "TEST_ONLY"}])
        decision = env.run()
        record = decision["inputs"]["research_record"]
        self.assertEqual((record["status"], [item["reason"] for item in record["dropped"]]),
                         ("OK", ["SOURCE_HOST_NOT_OFFICIAL"]))
        reasons, cell = self.soxl(decision)
        self.assertFalse(any(reason.startswith("RESEARCH_RECORD_NOT_OK") for reason in reasons))
        self.assertEqual(cell["s"], "ok")


class LedgerCarryTests(unittest.TestCase):
    """r2 R2-2 (Judge F-2, J10/K4): the re-issue ledger and an unclassified ticket survive HOLD/FAIL days."""

    def setUp(self):
        self.env = Env(decision_mode="apply")
        self.addCleanup(self.env.close)
        base = self.env.run()  # a real record to copy (its journal entry is dropped again below)
        write_json(self.env.journal, EMPTY_JOURNAL)
        self.ticket = _fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")
        self.ticket.update(ticket_id=f"AT-{D_DAY.replace('-', '')}-SOXL-1", session=D_DAY,
                           issuedAt=f"{D_DAY} 07:45 KST")
        del self.ticket["issued_day"]
        record = copy.deepcopy(base)
        _as_of(record, D_DAY).update(tickets=[self.ticket], open_tickets=[], keys={CLOSED_KEY: dict(CLOSED)},
                                     f6_ran=True, carried_from=None)
        (self.env.output / D_DAY).mkdir()
        write_json(self.env.output / D_DAY / "decision.json", record)

    def copy_t1(self, day):
        folder = self.env.output / day
        folder.mkdir(exist_ok=True)
        for name in ("result.json", "reconcile.json", "kiwoom_broker_snapshot.shadow.json"):
            shutil.copyfile(self.env.day_dir / name, folder / name)

    def assert_carried(self, record):
        self.assertFalse(record["f6_ran"])
        self.assertEqual(record["carried_from"], D_DAY)
        self.assertEqual(record["keys"], {CLOSED_KEY: CLOSED})
        self.assertEqual([(item["ticket_id"], item["issued_day"]) for item in record["open_tickets"]],
                         [(self.ticket["ticket_id"], D_DAY)])
        self.assertEqual((record["tickets"], record["outcomes"]), ([], []))

    def run_d2(self, reader):
        write_json(self.env.day_dir / "reconcile.json", {"status": "OK", "fills": [
            {"ticker": "SOXL", "side": "SELL", "quantity": 5, "session_date": D_DAY}]})
        return self.env.run(reader=reader)

    def assert_classified_on_d2(self):
        reader = FakeReader(fills={D_DAY.replace("-", ""): [helpers.fill_row("SOXL", "매도", ordered=5, filled=5,
                                                                             price="95.00", fill_price="96.10")]})
        decision = self.run_d2(reader)
        self.assertEqual(decision["status"], "OK", decision["reasons"])
        self.assertEqual([(item["ticket_id"], item["state"]) for item in decision["outcomes"]],
                         [(self.ticket["ticket_id"], "filled")])
        self.assertEqual(decision["keys"][CLOSED_KEY], CLOSED)  # the closed key stays closed
        self.assertEqual(decision["keys"]["b" * 64]["closed_reason"], "FILLED")
        self.assertIn("ticket_outcome", decision["journal"]["appended"])
        self.assertIn(D_DAY.replace("-", ""), [(request.get("params") or {}).get("ord_dt") for request in reader.requests])
        self.assertEqual((decision["f6_ran"], decision["carried_from"], decision["open_tickets"]), (True, None, []))
        outcomes = [entry for entry in journal_module.load_journal(self.env.journal)["entries"]
                    if entry["entry_type"] == "ticket_outcome"]
        self.assertEqual([entry["payload"]["ticket_id"] for entry in outcomes], [self.ticket["ticket_id"]])

    def test_t1_missing_hold_between(self):
        held = self.env.run(now=_morning(D1_DAY))
        self.assertEqual((held["status"], held["reasons"]), ("HOLD", ["T1_RESULT_MISSING"]))
        self.assert_carried(load_json(self.env.output / D1_DAY / "decision.json"))
        self.assert_classified_on_d2()

    def test_unexpected_exception_fail_between(self):
        self.copy_t1(D1_DAY)

        def broken(now):
            raise RuntimeError("TEST_ONLY")

        failed = self.env.run(now=_morning(D1_DAY), calendar_loader=broken)
        self.assertEqual(failed["status"], "FAIL")
        self.assertTrue(any(alert["code"] == "DECIDE_FAIL" and alert["push"] for alert in failed["alerts"]))
        self.assert_carried(load_json(self.env.output / D1_DAY / "decision.json"))
        self.assert_classified_on_d2()

    def test_failure_after_f6_commits_nothing(self):
        self.copy_t1(D1_DAY)
        reader = FakeReader(fills={D_DAY.replace("-", ""): [helpers.fill_row("SOXL", "매도", ordered=5, filled=5,
                                                                             price="95.00", fill_price="96.10")]})

        def broken(output_directory, earnings, proposals):
            raise RuntimeError("TEST_ONLY")

        failed = self.env.run(now=_morning(D1_DAY), reader=reader, exposure_runner=broken)
        self.assertEqual(failed["status"], "FAIL")
        self.assertTrue(reader.requests)  # F6 ran that day, but nothing of it stood
        self.assert_carried(load_json(self.env.output / D1_DAY / "decision.json"))
        self.assertEqual(journal_module.load_journal(self.env.journal)["entries"], [])
        self.assert_classified_on_d2()

    def test_g0_does_not_pass_on_an_empty_list_in_between(self):
        self.env.run(now=_morning(D1_DAY))
        decision = self.run_d2(FakeReader(failing={D_DAY.replace("-", "")}))
        self.assertEqual(decision["status"], "HOLD")
        self.assertIn(f"OUTCOME_UNKNOWN:{self.ticket['ticket_id']}", decision["reasons"])
        self.assertEqual([item["ticket_id"] for item in decision["open_tickets"]], [self.ticket["ticket_id"]])
        self.assertEqual(decision["tickets"], [])

    def test_unreadable_record_after_the_source_fails_g0(self):
        (self.env.output / D1_DAY).mkdir()
        (self.env.output / D1_DAY / "decision.json").write_text("{broken", encoding="utf-8")
        reader = FakeReader(fills={D_DAY.replace("-", ""): [helpers.fill_row("SOXL", "매도", ordered=5, filled=5,
                                                                             price="95.00", fill_price="96.10")]})
        decision = self.run_d2(reader)
        self.assertIn("G0_PREVIOUS_DECISION_UNREADABLE", decision["reasons"])
        self.assertEqual([item["state"] for item in decision["outcomes"]], ["filled"])


class DamageWindowTests(unittest.TestCase):
    """r2 R2-4 (Judge F-4) through decide: a damage fact of a record 15 record days back still keeps RG1 no."""

    def write_record(self, env, session, facts=()):
        day = (datetime.fromisoformat(session) + timedelta(days=1)).date().isoformat()
        write_json(env.research_root / day / "research-record.json", {
            "schema_version": "auto-core-research-record-1.0", "record_day_kst": day, "evaluation_session": session,
            "written_at": f"{session}T17:00:00-04:00", "writer": "TEST_ONLY", "earnings": {}, "official_facts": list(facts),
            "integrated_check_run": None, "order_authority": False, "quantity_authority": "none"})
        return day

    def test_old_damage_fact_keeps_rg1_no(self):
        env = Env()
        self.addCleanup(env.close)
        closes = helpers.zigzag(len(DAYS), 500, 4.0, 0.3)
        event = len(DAYS) - 1 - 17
        closes[event] = round(closes[event - 1] * 0.93, 4)  # EV1
        env.bars["SOXX"] = helpers.bars("SOXX", DAYS, closes)
        damage = {"fact_id": "SOXL-DMG-1", "symbol": "SOXL", "direction": "-", "kind": "thesis",
                  "card_trigger_ids": [], "event_session": DAYS[event + 2], "announced_at": f"{DAYS[event + 2]}T16:30:00-04:00",
                  "source_kind": "SEC_FILING", "source_url": "https://www.sec.gov/x", "criterion_a": False,
                  "root_thesis_damage": True, "summary_ko": "TEST_ONLY"}
        record_days = [self.write_record(env, session, [damage] if session == DAYS[event + 2] else [])
                       for session in DAYS[-25:-1]]
        damaged_day = record_days[DAYS[-25:-1].index(DAYS[event + 2])]
        decision = env.run()
        loaded = inputs.load_research(root=env.research_root, run_day=RUN_DAY, calendar_sessions=CALENDAR_DAYS,
                                      decide_time=NOW, registry=inputs.load_registry(
                                          env.registry, repo=env.root, committed_check=lambda path, repo: (True, None)),
                                      window_start=DAYS[-60])
        self.assertNotIn(damaged_day, loaded["days"])  # older than the 10 record days C7 uses
        self.assertEqual([fact["fact_id"] for fact in loaded["damage"]], ["SOXL-DMG-1"])
        self.assertEqual([fact["fact_id"] for fact in loaded["facts"]], [])
        self.assertEqual(decision["shock"]["event"]["date"], DAYS[event])
        self.assertEqual((decision["shock"]["open"], decision["shock"]["rg"]["RG1"]), (True, "no"))
        self.assertEqual(decision["shock"]["rg1_coverage"]["missing_sessions"], [])


class RerunAndScorerTests(unittest.TestCase):
    def env(self, **kwargs):
        env = Env(decision_mode="apply", **kwargs)
        self.addCleanup(env.close)
        return env

    def test_a_different_rerun_is_kept_aside_as_hold(self):
        # r2 R2-5: the journal keeps the first decision; decision.json and LATEST stay; the rerun is HOLD aside.
        env = self.env()
        first = env.run()
        before = (env.day_dir / "decision.json").read_bytes()
        latest = (env.output / "LATEST_DECISION.json").read_bytes()
        count = len(journal_module.load_journal(env.journal)["entries"])
        env.bars["SOXL"] = helpers.bars("SOXL", DAYS, helpers.zigzag(len(DAYS), 101, 2.0, 0.05))
        again = env.run()
        self.assertEqual(again["status"], "HOLD")
        self.assertIn("CORE_DECISION_ALREADY_RECORDED_DIFFERENT", again["reasons"])
        self.assertNotEqual(again["journal"]["decision_sha256"], first["journal"]["decision_sha256"])
        self.assertEqual(again["journal"]["already_recorded"], first["journal"]["decision_sha256"])
        self.assertEqual(len(journal_module.load_journal(env.journal)["entries"]), count)
        self.assertEqual((env.day_dir / "decision.json").read_bytes(), before)
        self.assertEqual((env.output / "LATEST_DECISION.json").read_bytes(), latest)
        reruns = list(env.day_dir.glob("decision.rerun-*.json"))
        self.assertEqual([path.name for path in reruns], [again["journal"]["rerun_file"]])
        kept = load_json(reruns[0])
        self.assertEqual(validate_instance(kept, decide_module.DECISION_SCHEMA), [])
        self.assertTrue(any(alert["code"] == "CORE_DECISION_ALREADY_RECORDED_DIFFERENT" and alert["push"]
                            for alert in kept["alerts"]))
        self.assertEqual(kept["dashboard"]["orders"], [])

    def test_mismatched_outcome_leaves_its_key_as_it_was(self):
        # r2 R2-7: an outcome that disagrees with T1's explained fills neither closes nor reopens its key.
        env = self.env()
        previous = env.run()
        write_json(env.journal, EMPTY_JOURNAL)
        state = {"first_cap": 95.0, "market_tests": 0, "consecutive_not_entered": 1, "closed": False,
                 "closed_reason": None}
        _as_of(previous, "2026-10-01").update(tickets=[_fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")],
                                              open_tickets=[], keys={"b" * 64: dict(state)})
        (env.output / "2026-10-01").mkdir()
        write_json(env.output / "2026-10-01" / "decision.json", previous)
        reader = FakeReader(fills={"20261001": [helpers.fill_row("SOXL", "매도", ordered=5, filled=5, price="95.00")]})
        decision = env.run(reader=reader)
        self.assertTrue(decision["outcomes"][0]["reconcile_mismatch"])
        self.assertEqual(decision["keys"]["b" * 64], state)

    def test_scorer_exit_code_is_a_warning(self):
        # r2 R2-8: a non-zero return of the scorer is kept like an exception.
        warned = self.env().run(score_runner=lambda path: 2)
        self.assertEqual(warned["status"], "OK", warned["reasons"])
        self.assertEqual(warned["journal"]["score_warning"], "SCORER_EXIT:2")
        self.assertNotIn("score_warning", self.env().run(score_runner=lambda path: 0)["journal"])


R3_DAYS = helpers.sessions("2026-06-01", 110)  # r3: a calendar to 2026-10-30 (no holiday)
SATURDAY, MONDAY, TUESDAY, WEDNESDAY = "2026-10-17", "2026-10-19", "2026-10-20", "2026-10-21"


class OrderWindowTests(unittest.TestCase):
    """r3 R3-1/R3-2 through decide: a ticket is classified only after its session ended, from the order rows of
    its issue KST day to the KST day of its session's close (a Saturday ticket for Monday reads Saturday to
    Tuesday, a weekday ticket its issue day and the next)."""

    def setUp(self):
        self.env = Env(decision_mode="apply")
        self.addCleanup(self.env.close)
        self.base = self.env.run()  # a real record to copy (its journal entry is dropped again below)
        write_json(self.env.journal, EMPTY_JOURNAL)

    def source(self, run_day, evaluation, buy):
        """The ledger source: a record of run_day (evaluation and buy sessions as that day) with one apply ticket."""
        ticket = _fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")
        ticket.update(ticket_id=f"AT-{run_day.replace('-', '')}-SOXL-1", session=buy, issuedAt=f"{run_day} 07:45 KST")
        del ticket["issued_day"]
        record = copy.deepcopy(self.base)
        record.update(run_day_kst=run_day, evaluation_session=evaluation, buy_session=buy, tickets=[ticket],
                      open_tickets=[], keys={}, f6_ran=True, carried_from=None,
                      dashboard={"runCore": {**self.base["dashboard"]["runCore"], "tickets": [{"id": ticket["ticket_id"]}]},
                                 "orders": [{"id": ticket["ticket_id"], "session": buy, "outcome": {"state": "pending"}}]})
        (self.env.output / run_day).mkdir()
        write_json(self.env.output / run_day / "decision.json", record)
        return ticket

    def run_on(self, day, days, reader, fills=()):
        folder = self.env.output / day
        folder.mkdir(exist_ok=True)
        for name in ("result.json", "kiwoom_broker_snapshot.shadow.json"):
            shutil.copyfile(self.env.day_dir / name, folder / name)
        write_json(folder / "reconcile.json", {"status": "OK", "fills": list(fills)})
        return self.env.run(now=_morning(day), reader=reader, calendar_loader=lambda now: helpers.calendar(days))

    @staticmethod
    def order_days(reader):
        return [request["params"]["ord_dt"] for request in reader.requests
                if request["operation"] == "account_daily_fills_read"]

    @staticmethod
    def sold(session):
        return [{"ticker": "SOXL", "side": "SELL", "quantity": 5, "session_date": session}]

    @staticmethod
    def row():
        return helpers.fill_row("SOXL", "매도", ordered=5, filled=5, price="95.00", fill_price="96.10")

    def journaled_states(self):
        return [entry["payload"]["outcome_state"] for entry in journal_module.load_journal(self.env.journal)["entries"]
                if entry["entry_type"] == "ticket_outcome"]

    def test_saturday_ticket_for_monday_reads_saturday_to_tuesday(self):
        ticket = self.source(SATURDAY, "2026-10-16", MONDAY)
        for rows, fills, state in (([self.row()], self.sold(MONDAY), "filled"), ([], [], "not_entered")):
            with self.subTest(state=state):
                write_json(self.env.journal, EMPTY_JOURNAL)
                reader = FakeReader(fills={MONDAY.replace("-", ""): rows})  # entered Monday evening KST
                decision = self.run_on(TUESDAY, R3_DAYS, reader, fills)
                self.assertEqual((decision["evaluation_session"], decision["no_new_session"]), (MONDAY, False))
                self.assertEqual(self.order_days(reader), ["20261017", "20261018", "20261019", "20261020"])
                self.assertEqual([(item["ticket_id"], item["state"]) for item in decision["outcomes"]],
                                 [(ticket["ticket_id"], state)])
                self.assertEqual(decision["open_tickets"], [])
                self.assertEqual(self.journaled_states(), [state])

    def test_weekday_ticket_reads_its_issue_day_and_the_next(self):
        ticket = self.source("2026-10-14", "2026-10-13", "2026-10-14")
        reader = FakeReader(fills={"20261014": [self.row()]})
        decision = self.run_on("2026-10-15", R3_DAYS, reader, self.sold("2026-10-14"))
        self.assertEqual(self.order_days(reader), ["20261014", "20261015"])
        self.assertEqual([(item["ticket_id"], item["state"]) for item in decision["outcomes"]],
                         [(ticket["ticket_id"], "filled")])

    def test_monday_holiday_is_a_no_new_session_day_then_wednesday_classifies(self):
        days = [day for day in R3_DAYS if day != MONDAY]  # U.S. holiday on Monday 10/19
        ticket = self.source(SATURDAY, "2026-10-16", TUESDAY)
        journal_before = self.env.journal.read_bytes()
        reader = FakeReader()
        quiet = self.run_on(TUESDAY, days, reader)
        # Tuesday 07:45 KST: the evaluation session is still Friday 10/16 (the source's) - R3-3.
        self.assertEqual((quiet["status"], quiet["reasons"], quiet["no_new_session"]), ("OK", [], True))
        self.assertEqual((quiet["evaluation_session"], quiet["f6_ran"], quiet["carried_from"]),
                         ("2026-10-16", True, SATURDAY))
        self.assertEqual((quiet["tickets"], quiet["outcomes"], quiet["journal"]["appended"]), ([], [], []))
        self.assertEqual([(item["ticket_id"], item["issued_day"]) for item in quiet["open_tickets"]],
                         [(ticket["ticket_id"], SATURDAY)])
        self.assertEqual(quiet["inputs"]["no_new_session"]["not_yet"], [ticket["ticket_id"]])
        self.assertEqual(self.env.journal.read_bytes(), journal_before)  # no journal entry
        self.assertFalse(any(alert["push"] for alert in quiet["alerts"]))  # no push
        self.assertEqual(reader.requests, [])  # no broker read
        self.assertEqual(quiet["compare"]["status"], "NO_NEW_SESSION")
        self.assertEqual(quiet["alert_states"], self.base["alert_states"])  # the next run's repetition base
        # The ticket still before its session stays on the dashboard for entry (not a new ticket, no push).
        self.assertEqual([order["id"] for order in quiet["dashboard"]["orders"]], [ticket["ticket_id"]])
        self.assertEqual([item["id"] for item in quiet["dashboard"]["runCore"]["tickets"]], [ticket["ticket_id"]])
        self.assertIsNotNone(quiet["next_action_for_user"])
        written = load_json(self.env.output / TUESDAY / "decision.json")
        self.assertEqual(validate_instance(written, decide_module.DECISION_SCHEMA), [])
        self.assertTrue(written["no_new_session"])
        # The same run day again: the same result, no rerun file (R2-5 is not involved).
        again = self.run_on(TUESDAY, days, FakeReader())
        self.assertEqual((again["status"], again["no_new_session"], again["carried_from"]), ("OK", True, SATURDAY))
        self.assertEqual(list((self.env.output / TUESDAY).glob("decision.rerun-*.json")), [])
        # Wednesday 07:45 KST: Tuesday's session has ended; Saturday's ticket is read from Saturday to Wednesday.
        reader = FakeReader(fills={TUESDAY.replace("-", ""): [self.row()]})
        decision = self.run_on(WEDNESDAY, days, reader, self.sold(TUESDAY))
        self.assertEqual((decision["evaluation_session"], decision["no_new_session"]), (TUESDAY, False))
        self.assertEqual(self.order_days(reader), ["20261017", "20261018", "20261019", "20261020", "20261021"])
        self.assertEqual([(item["ticket_id"], item["state"]) for item in decision["outcomes"]],
                         [(ticket["ticket_id"], "filled")])
        self.assertEqual((decision["f6_ran"], decision["carried_from"], decision["open_tickets"]), (True, None, []))
        self.assertEqual(self.journaled_states(), ["filled"])
        self.assertNotIn("11", [alert["code"] for alert in decision["alerts"]])  # Tuesday's record exists


    def test_a_ticket_left_by_a_failed_read_waits_for_the_next_new_session(self):
        # r3 R3-3 (Builder choice): Friday's ticket that Saturday could not classify (a failed read there) is not
        # classified on the no-new-session Tuesday (no journal entry that day); Wednesday classifies it.
        days = [day for day in R3_DAYS if day != MONDAY]
        ticket = self.source(SATURDAY, "2026-10-16", TUESDAY)
        friday = _fake_ticket("SOXL", "buy", 3, 95.0, mode="apply")
        friday.update(ticket_id="AT-20261016-SOXL-1", session="2026-10-16", issued_day="2026-10-16",
                      decision_key="d" * 64)
        record = load_json(self.env.output / SATURDAY / "decision.json")
        record["open_tickets"] = [friday]
        write_json(self.env.output / SATURDAY / "decision.json", record)
        reader = FakeReader()
        quiet = self.run_on(TUESDAY, days, reader)
        self.assertEqual((quiet["status"], quiet["no_new_session"], quiet["outcomes"], reader.requests), ("OK", True, [], []))
        self.assertEqual(quiet["inputs"]["no_new_session"]["deferred"], [friday["ticket_id"]])
        self.assertEqual(quiet["inputs"]["no_new_session"]["not_yet"], [ticket["ticket_id"]])
        self.assertEqual([item["ticket_id"] for item in quiet["open_tickets"]], [friday["ticket_id"], ticket["ticket_id"]])
        self.assertEqual([order["id"] for order in quiet["dashboard"]["orders"]], [ticket["ticket_id"]])
        reader = FakeReader(fills={"20261016": [helpers.fill_row("SOXL", "매수", ordered=3, filled=0, price="95.00")],
                                   TUESDAY.replace("-", ""): [self.row()]})
        decision = self.run_on(WEDNESDAY, days, reader, self.sold(TUESDAY))
        self.assertEqual(self.order_days(reader),
                         ["20261016", "20261017", "20261018", "20261019", "20261020", "20261021"])
        self.assertEqual([(item["ticket_id"], item["state"]) for item in decision["outcomes"]],
                         [(friday["ticket_id"], "unfilled"), (ticket["ticket_id"], "filled")])
        self.assertEqual(sorted(self.journaled_states()), ["filled", "unfilled"])
        self.assertEqual(decision["open_tickets"], [])


class TicketSessionNotYetTests(unittest.TestCase):
    def test_a_ticket_before_its_session_blocks_new_tickets(self):
        # r3 R3-1: a ticket whose session is after this run's evaluation session is not classified (no read of its
        # days); it stays open and G0 blocks today's new tickets.
        env = Env(holdings={"SOXL": 10})
        self.addCleanup(env.close)
        env.write_good_news()
        first = env.run()
        self.assertEqual(len(first["tickets"]), 1)  # without the open ticket MU gets one
        early = _fake_ticket("SOXL", "sell", 5, 95.0)
        early["session"] = "2026-10-12"  # after this run's evaluation session 2026-10-09
        previous = _as_of(copy.deepcopy(first), "2026-10-01")
        previous.update(tickets=[early], open_tickets=[])
        (env.output / "2026-10-01").mkdir()
        write_json(env.output / "2026-10-01" / "decision.json", previous)
        reader = FakeReader()
        decision = env.run(reader=reader)
        self.assertIn(f"G0_TICKET_SESSION_NOT_YET:{early['ticket_id']}", decision["reasons"])
        self.assertEqual((decision["status"], decision["tickets"], decision["outcomes"]), ("HOLD", [], []))
        self.assertEqual([item["ticket_id"] for item in decision["open_tickets"]], [early["ticket_id"]])
        self.assertEqual([request["operation"] for request in reader.requests], ["account_open_items"])


class SameSessionOtherDayTests(unittest.TestCase):
    """r3 R3-3 before R2-5: another run day with the journal's evaluation session is a no-new-session day; R2-5
    is only for a rerun of the same run day."""

    def setUp(self):
        self.env = Env(decision_mode="apply")
        self.addCleanup(self.env.close)
        self.first = self.env.run()  # Saturday 2026-10-10, evaluation session 2026-10-09, journaled
        self.assertEqual(self.first["journal"]["appended"], ["core_decision"])
        self.journal = self.env.journal.read_bytes()

    def copy_t1(self, day):
        folder = self.env.output / day
        folder.mkdir(exist_ok=True)
        for name in ("result.json", "reconcile.json", "kiwoom_broker_snapshot.shadow.json"):
            shutil.copyfile(self.env.day_dir / name, folder / name)
        return folder

    def test_next_day_with_the_same_session_is_no_new_session_not_a_rerun(self):
        folder = self.copy_t1("2026-10-11")
        decision = self.env.run(now=_morning("2026-10-11"))
        self.assertEqual((decision["status"], decision["no_new_session"], decision["carried_from"]), ("OK", True, RUN_DAY))
        self.assertNotIn("CORE_DECISION_ALREADY_RECORDED_DIFFERENT", decision["reasons"])
        self.assertEqual(self.env.journal.read_bytes(), self.journal)
        self.assertTrue((folder / "decision.json").is_file())
        self.assertEqual(list(folder.glob("decision.rerun-*.json")), [])

    def test_r2_5_is_only_for_the_same_run_day(self):
        (self.env.output / "2026-10-11").mkdir()
        (self.env.output / "2026-10-11" / "decision.json").write_text("{broken", encoding="utf-8")
        folder = self.copy_t1("2026-10-12")
        decision = self.env.run(now=_morning("2026-10-12"))
        self.assertEqual((decision["evaluation_session"], decision["no_new_session"]), (LAST, False))
        self.assertEqual(decision["status"], "FAIL")
        self.assertIn("JOURNAL_WRITE_REFUSED:CORE_DECISION_ALREADY_RECORDED", decision["reasons"])
        self.assertEqual(list(folder.glob("decision.rerun-*.json")), [])
        self.assertEqual(self.env.journal.read_bytes(), self.journal)
        self.assertTrue(any(alert["code"] == "DECIDE_FAIL" and alert["push"] for alert in decision["alerts"]))


D_R4, D1_R4, D2_R4, D3_R4 = "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17"  # Wednesday to Saturday


def _order_row(number, placed, *, filled=5):
    """A SOXL sell row (5 at 95.00) with its order number and KST order time."""
    row = helpers.fill_row("SOXL", "매도", ordered=5, filled=filled, price="95.00", fill_price="96.10" if filled else None)
    row.update(ord_no=number, ord_time=placed)
    return row


class OrderAttributionTests(unittest.TestCase):
    """r4 R4-1 through decide: an order row counts for one ticket only (attributed_orders in the recording-mode
    ledger, carried like the keys), and issue-day rows placed before the ticket was issued are not its."""

    def make_env(self, mode="apply"):
        self.env = Env(decision_mode=mode)
        self.addCleanup(self.env.close)
        self.base = self.env.run()  # a real record to copy (its journal entry is dropped again below)
        write_json(self.env.journal, EMPTY_JOURNAL)

    def setUp(self):
        self.make_env()

    @staticmethod
    def ticket(run_day, session, key="b" * 64, number=1):
        ticket = _fake_ticket("SOXL", "sell", 5, 95.0, mode="apply")
        ticket.update(ticket_id=f"AT-{run_day.replace('-', '')}-SOXL-{number}", session=session,
                      issuedAt=f"{run_day} 07:45 KST", decision_key=key)
        del ticket["issued_day"]
        return ticket

    def source(self, run_day, evaluation, tickets, open_tickets=(), attributed=()):
        record = copy.deepcopy(self.base)
        record.update(run_day_kst=run_day, evaluation_session=evaluation, buy_session=run_day, tickets=list(tickets),
                      open_tickets=list(open_tickets), keys={}, attributed_orders=list(attributed), f6_ran=True,
                      carried_from=None)
        (self.env.output / run_day).mkdir()
        write_json(self.env.output / run_day / "decision.json", record)

    def add_ticket(self, run_day, ticket):
        """That day's real record also issued a ticket of the same symbol and side (as if its plan had made it)."""
        path = self.env.output / run_day / "decision.json"
        record = load_json(path)
        record["tickets"] = [ticket]
        write_json(path, record)

    def run_on(self, day, reader=None, fills=(), t1=True, days=R3_DAYS):
        folder = self.env.output / day
        folder.mkdir(exist_ok=True)
        if t1:
            for name in ("result.json", "kiwoom_broker_snapshot.shadow.json"):
                shutil.copyfile(self.env.day_dir / name, folder / name)
            write_json(folder / "reconcile.json", {"status": "OK", "fills": list(fills)})
        return self.env.run(now=_morning(day), reader=reader or FakeReader(),
                            calendar_loader=lambda now: helpers.calendar(days))

    @staticmethod
    def sold(session):
        return [{"ticker": "SOXL", "side": "SELL", "quantity": 5, "session_date": session}]

    @staticmethod
    def states(decision):
        return [(item["ticket_id"], item["state"]) for item in decision["outcomes"]]

    def journaled(self):
        return [(entry["payload"]["ticket_id"], entry["payload"]["outcome_state"])
                for entry in journal_module.load_journal(self.env.journal)["entries"]
                if entry["entry_type"] == "ticket_outcome"]

    def written(self, day):
        record = load_json(self.env.output / day / "decision.json")
        self.assertEqual(validate_instance(record, decide_module.DECISION_SCHEMA), [])
        return record

    def test_a_row_entered_after_midnight_counts_only_for_its_ticket(self):
        # T (issued Wednesday D, session D) is entered at 00:30 KST on D+1, during its session.
        old = {"ord_dt": "2026-09-15", "ord_no": "0000901", "ticket_id": "AT-20260914-SOXL-1"}
        kept = {"ord_dt": "2026-09-16", "ord_no": "0000902", "ticket_id": "AT-20260915-SOXL-1"}
        first = self.ticket(D_R4, D_R4)
        self.source(D_R4, "2026-10-13", [first], attributed=[old, kept])
        row = _order_row("0000101", "00:30:00")
        reader = FakeReader(fills={"20261015": [row]})
        d1 = self.run_on(D1_R4, reader, self.sold(D_R4))
        self.assertEqual(OrderWindowTests.order_days(reader), ["20261014", "20261015"])
        self.assertEqual(self.states(d1), [(first["ticket_id"], "filled")])
        mine = {"ord_dt": D1_R4, "ord_no": "0000101", "ticket_id": first["ticket_id"]}
        # The 30 calendar days of D+1 start on 2026-09-16: the 2026-09-15 entry is dropped.
        self.assertEqual(self.written(D1_R4)["attributed_orders"], [kept, mine])
        # T' (same symbol and side) issued on D+1 at 07:45 KST; the user does not enter it.
        second = self.ticket(D1_R4, D1_R4, key="e" * 64)
        self.add_ticket(D1_R4, second)
        reader = FakeReader(fills={"20261015": [row]})  # the D+1 00:30 row is read again for T'
        d2 = self.run_on(D2_R4, reader)
        self.assertEqual(OrderWindowTests.order_days(reader), ["20261015", "20261016"])
        self.assertEqual(self.states(d2), [(second["ticket_id"], "not_entered")])
        self.assertEqual(d2["outcomes"][0]["rows"], 0)
        # The window moves with the run day: from D+2 it starts on 2026-09-17.
        self.assertEqual(self.written(D2_R4)["attributed_orders"], [mine])
        self.assertEqual(self.journaled(), [(first["ticket_id"], "filled"), (second["ticket_id"], "not_entered")])

    def test_the_ledger_alone_keeps_a_later_row_out_across_a_hold_day(self):
        # The D+1 run reads the broker after its research wait: a row placed at 08:10 KST on D+1 (after T's
        # session closed, after T' was issued at 07:45) was counted for T. Only the ledger keeps it from T'.
        first = self.ticket(D_R4, D_R4)
        self.source(D_R4, "2026-10-13", [first])
        late = _order_row("0000102", "08:10:00")
        d1 = self.run_on(D1_R4, FakeReader(fills={"20261015": [late]}), self.sold(D_R4))
        self.assertEqual(self.states(d1), [(first["ticket_id"], "filled")])
        mine = [{"ord_dt": D1_R4, "ord_no": "0000102", "ticket_id": first["ticket_id"]}]
        self.assertEqual(d1["attributed_orders"], mine)
        second = self.ticket(D1_R4, D1_R4, key="e" * 64)
        self.add_ticket(D1_R4, second)
        held = self.run_on(D2_R4, t1=False)  # T1 missing on D+2: HOLD before F6
        self.assertEqual((held["status"], held["reasons"]), ("HOLD", ["T1_RESULT_MISSING"]))
        record = self.written(D2_R4)
        self.assertEqual((record["f6_ran"], record["carried_from"], record["attributed_orders"]), (False, D1_R4, mine))
        reader = FakeReader(fills={"20261015": [late]})
        d3 = self.run_on(D3_R4, reader)
        self.assertEqual(OrderWindowTests.order_days(reader), ["20261015", "20261016"])
        self.assertEqual(self.states(d3), [(second["ticket_id"], "not_entered")])
        self.assertEqual(d3["attributed_orders"], mine)

    def test_compare_mode_keeps_no_list(self):
        # Compare mode: no ledger update, so the D+1 row of T is read again for T' (as before r4).
        self.make_env("compare")
        first = self.ticket(D_R4, D_R4)
        self.source(D_R4, "2026-10-13", [first])
        late = _order_row("0000102", "08:10:00")
        d1 = self.run_on(D1_R4, FakeReader(fills={"20261015": [late]}), self.sold(D_R4))
        self.assertEqual((self.states(d1), d1["attributed_orders"]), ([(first["ticket_id"], "filled")], []))
        second = self.ticket(D1_R4, D1_R4, key="e" * 64)
        self.add_ticket(D1_R4, second)
        d2 = self.run_on(D2_R4, FakeReader(fills={"20261015": [late]}), self.sold(D1_R4))
        self.assertEqual((self.states(d2), d2["attributed_orders"]), ([(second["ticket_id"], "filled")], []))

    def test_within_one_run_a_row_counts_once_in_both_modes(self):
        # A (issued Tuesday, session Tuesday, left open) and B (issued Wednesday D) are classified in the same run.
        # A's window ends on D; a row at 08:00 KST on D (after B was issued) is taken by the older A.
        for mode in ("compare", "apply"):
            with self.subTest(mode=mode):
                self.make_env(mode)
                older = self.ticket("2026-10-13", "2026-10-13", key="d" * 64)
                older["issued_day"] = "2026-10-13"
                newer = self.ticket(D_R4, D_R4)
                self.source(D_R4, "2026-10-13", [newer], open_tickets=[older])
                reader = FakeReader(fills={"20261014": [_order_row("0000301", "08:00:00")]})
                decision = self.run_on(D1_R4, reader, self.sold("2026-10-13"))
                self.assertEqual(self.states(decision),
                                 [(older["ticket_id"], "filled"), (newer["ticket_id"], "not_entered")])
                expected = [{"ord_dt": D_R4, "ord_no": "0000301", "ticket_id": older["ticket_id"]}]
                self.assertEqual(self.written(D1_R4)["attributed_orders"], expected if mode == "apply" else [])

    def test_issue_day_row_before_the_issue_time_is_not_the_tickets(self):
        # A SOXL sell placed at 07:00 KST on the issue day, before the 07:45 ticket existed.
        first = self.ticket(D_R4, D_R4)
        self.source(D_R4, "2026-10-13", [first])
        decision = self.run_on(D1_R4, FakeReader(fills={"20261014": [_order_row("0000201", "07:00:00")]}))
        self.assertEqual(self.states(decision), [(first["ticket_id"], "not_entered")])
        self.assertEqual(decision["attributed_orders"], [])

    def test_an_issue_day_row_without_an_order_time_is_unknown(self):
        first = self.ticket(D_R4, D_R4)
        self.source(D_R4, "2026-10-13", [first])
        decision = self.run_on(D1_R4, FakeReader(fills={"20261014": [_order_row("0000201", "")]}))
        self.assertEqual(decision["outcomes"], [])
        self.assertIn(f"OUTCOME_UNKNOWN:{first['ticket_id']}", decision["reasons"])
        self.assertEqual([item["ticket_id"] for item in decision["open_tickets"]], [first["ticket_id"]])

    def test_an_outcome_that_disagrees_with_t1_adds_nothing(self):
        # r2 R2-7: such an outcome does not update the ledger (keys or attributed orders).
        first = self.ticket(D_R4, D_R4)
        self.source(D_R4, "2026-10-13", [first])
        decision = self.run_on(D1_R4, FakeReader(fills={"20261015": [_order_row("0000101", "00:30:00")]}))
        self.assertTrue(decision["outcomes"][0]["reconcile_mismatch"])
        self.assertEqual(decision["attributed_orders"], [])

    def test_a_no_new_session_day_carries_the_list(self):
        days = [day for day in R3_DAYS if day != MONDAY]  # U.S. holiday on Monday 10/19
        listed = [{"ord_dt": "2026-10-16", "ord_no": "0000401", "ticket_id": "AT-20261015-SOXL-1"}]
        self.source(SATURDAY, "2026-10-16", [self.ticket(SATURDAY, TUESDAY)], attributed=listed)
        quiet = self.run_on(TUESDAY, days=days)
        self.assertEqual((quiet["no_new_session"], quiet["attributed_orders"]), (True, listed))
        self.assertEqual(self.written(TUESDAY)["attributed_orders"], listed)


class S7OutputTests(unittest.TestCase):
    """r2 R2-11: decide's S7 review goes under workspace/outputs/auto-core/<day>/s7/, never exposure-review."""

    def test_decide_writes_its_s7_review_under_the_day_folder(self):
        import run_portfolio_exposure_review as review_module

        env = Env()
        self.addCleanup(env.close)
        seen = []

        def fake_run(args):  # the real S7 build on the synthetic portfolio, written where the arguments say
            seen.append(args)
            proposals = load_json(args.proposals)["proposals"] if args.proposals else []
            earnings = load_json(args.earnings)["earnings"] if args.earnings else None
            review = env.exposure_runner(None, earnings, proposals)["review"]
            target = Path(args.output_root) / review["evaluation_session"] / "portfolio-exposure-review.TEST.json"
            write_json(target, review)
            return review, target

        def files():
            root = review_module.DEFAULT_OUTPUT_ROOT
            return sorted(str(path) for path in root.rglob("*") if path.is_file()) if root.is_dir() else []

        before = files()
        original = review_module.run
        review_module.run = fake_run
        try:
            decision = env.run(exposure_runner=decide_module.run_s7)
        finally:
            review_module.run = original
        self.assertIn(decision["status"], ("OK", "HOLD"), decision["reasons"])
        folder = env.day_dir / "s7"
        self.assertEqual({Path(args.output_root) for args in seen}, {folder})
        self.assertEqual(Path(seen[-1].earnings).parent, folder)
        self.assertTrue((folder / LAST / "portfolio-exposure-review.TEST.json").is_file())
        self.assertEqual(files(), before)


class JournalReaderTests(unittest.TestCase):
    """F7 reader protection: AUTO_CORE entries load, S7 view is unchanged, the scorer ignores them."""

    def _journal_with_auto_entry(self, root: Path) -> Path:
        path = root / "decision_journal.json"
        write_json(path, {"schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL",
                          "order_authority": False, "quantity_authority": "none", "entries": []})
        decision = {"run_day_kst": "2026-10-10", "buy_session": "2026-10-12", "decision_mode": "apply",
                    "evaluation_session": "2026-10-09", "no_action": {"value": False, "reasons": []},
                    "commit_sha": COMMIT, "outcomes": [{"ticket_id": "AT-20261009-SOXL-1", "ticker": "SOXL",
                                                        "side": "sell", "state": "filled", "filled_qty": 5,
                                                        "average_fill_price": 95.5, "decision_key": "c" * 64,
                                                        "mode": "apply"}],
                    "tickets": [{"ticket_id": "AT-20261010-SOXL-1", "ticker": "SOXL", "side": "sell", "type": "LOC",
                                 "price": 94.12, "qty": 5, "amount": 470.6, "session": "2026-10-12",
                                 "decision_key": "d" * 64, "priceRule": "TEST_ONLY", "evidence": {"r": "1/2"}}]}
        journal_module.append_auto_core_entries(journal_path=path, decision=decision, decision_sha256="e" * 64,
                                                expected_head=journal_module.GENESIS_HASH, recheck=lambda: [])
        return path

    def test_auto_core_entries_load_without_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._journal_with_auto_entry(Path(folder))
            loaded = journal_module.load_journal(path)
            self.assertEqual(loaded["status"], "OK", loaded["errors"])
            self.assertEqual([entry["entry_type"] for entry in loaded["entries"]],
                             ["core_decision", "order_ticket", "ticket_outcome"])
            ticket = loaded["entries"][1]["payload"]
            self.assertEqual(ticket["authority"]["quantity_authority"], "ORDER_TICKET_HUMAN_ENTRY")
            self.assertFalse(ticket["authority"]["order_authority"])

    def test_null_message_on_a_human_entry_is_corrupt_not_an_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._journal_with_auto_entry(Path(folder))
            document = load_json(path)
            document["entries"][0]["confirmation_method"] = "USER_TERMINAL"
            write_json(path, document)
            loaded = journal_module.load_journal(path)
            self.assertEqual(loaded["status"], "CORRUPT")

    def test_s7_journal_view_is_the_same_with_auto_core_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self._journal_with_auto_entry(Path(folder))
            loaded = journal_module.load_journal(path)
            view = journal_view(loaded)
            empty = journal_view({"status": "OK", "errors": [], "entries": []})
            self.assertEqual({key: view[key] for key in ("status", "activation", "line_reviews", "peak_reviews")},
                             {key: empty[key] for key in ("status", "activation", "line_reviews", "peak_reviews")})

    def test_scorer_ignores_auto_core_entries_and_head_matches(self):
        import score_decision_journal
        with tempfile.TemporaryDirectory() as folder:
            path = self._journal_with_auto_entry(Path(folder))
            loaded = journal_module.load_journal(path)
            report = score_decision_journal.score_journal(
                loaded, calendar=None, calendar_failure="TEST_ONLY", closes={}, unverified={},
                benchmark={"status": "MISSING", "closes": {}, "errors": []},
                corporate_actions={"status": "MISSING", "sha256": None, "errors": []},
                evaluation_as_of=datetime(2026, 10, 10, tzinfo=timezone.utc))
            self.assertEqual(report["results"], [])
            self.assertEqual(report["journal"]["head_sha256"], canonical_hash(loaded["entries"][-1]))

    def test_journal_pending_is_current_after_the_scorer_runs(self):
        import portfolio_status
        import score_decision_journal
        with tempfile.TemporaryDirectory() as folder:
            path = self._journal_with_auto_entry(Path(folder))
            document = load_json(path)
            # A card decision before the auto entries makes journal_pending compare the report head.
            scores = Path(folder) / "scores"
            report = score_decision_journal.score_journal(
                journal_module.load_journal(path), calendar=None, calendar_failure="TEST_ONLY", closes={},
                unverified={}, benchmark={"status": "MISSING", "closes": {}, "errors": []},
                corporate_actions={"status": "MISSING", "sha256": None, "errors": []},
                evaluation_as_of=datetime(2026, 10, 10, tzinfo=timezone.utc))
            score_decision_journal.write_report(report, scores, path, datetime(2026, 10, 10, tzinfo=timezone.utc))
            self.assertEqual(report["journal"]["head_sha256"], canonical_hash(document["entries"][-1]))
            pending = portfolio_status.journal_pending(path, scores)
            self.assertEqual(pending["status"], "OK")

    def test_human_apply_path_still_rejects_auto_core(self):
        self.assertNotIn("AUTO_CORE", journal_module.CONFIRMATION_METHODS)
        parser = journal_module.build_parser()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            parser.parse_args(["apply", "--proposal", "x", "--confirm", "ABCDEF12", "--confirmed-via", "AUTO_CORE"])
        proposal = {"entry_type": "s5_activation"}
        with self.assertRaises(journal_module.JournalError):
            journal_module.apply_proposal_entries(journal_path=Path("unused.json"), proposal=proposal, confirmation={
                "confirm_code": "ABCDEF12", "confirmation_method": "AUTO_CORE", "user_message": "ABCDEF12"})


class RegistryTests(unittest.TestCase):
    """F2: section hash, acceptance, commit check -> ticket eligibility."""

    TEXT = "# Card\n\n## 2. A\nbody a\n### 2-1 sub\nsub body\n## 3. B\nbody b\n"

    def test_section_hash_spans_subsections_and_ignores_line_endings(self):
        body = inputs.section_text(self.TEXT, "## 2. A")
        self.assertEqual(body, "## 2. A\nbody a\n### 2-1 sub\nsub body")
        self.assertEqual(inputs.section_sha256(self.TEXT, "## 2. A"),
                         inputs.section_sha256(self.TEXT.replace("\n", "\r\n"), "## 2. A"))
        self.assertEqual(inputs.section_text(self.TEXT, "# Card").splitlines()[-1], "body b")
        self.assertIsNone(inputs.section_text(self.TEXT, "## 9. none"))
        self.assertEqual(inputs.section_text("## A\n#hashtag line\n## B\n", "## A"), "## A\n#hashtag line")

    def env(self):
        env = Env()
        self.addCleanup(env.close)
        return env

    def test_card_check_reasons(self):
        env = self.env()
        registry = inputs.load_registry(env.registry, repo=env.root, committed_check=lambda path, repo: (True, None))
        watchlist = inputs.load_watchlist(env.watchlist)
        self.assertEqual(registry["status"], "OK", registry["errors"])
        self.assertTrue(inputs.card_check("MU", registry, watchlist, repo=env.root, held=False)["eligible"])
        self.assertEqual(inputs.card_check("NBIS", registry, watchlist, repo=env.root, held=True)["reasons"], ["NOCARD"])
        self.assertEqual(inputs.card_check("BE", registry, watchlist, repo=env.root, held=False)["reasons"],
                         ["REGISTRY_ENTRY_MISSING"])
        (env.docs / "TEST_ONLY.md").write_text(CARD_TEXT.replace("TEST_ONLY section body", "changed"), encoding="utf-8")
        changed = inputs.card_check("MU", registry, watchlist, repo=env.root, held=False)
        self.assertEqual((changed["eligible"], changed["hash_ok"], changed["reasons"]),
                         (False, False, ["CARD_SECTION_CHANGED"]))
        unaccepted = {"status": "OK", "members": {"MU": {"cardStatus": "제안"}}}
        self.assertIn("CARD_NOT_ACCEPTED_IN_WATCHLIST",
                      inputs.card_check("MU", registry, unaccepted, repo=env.root, held=False)["reasons"])
        uncommitted = inputs.load_registry(env.registry, repo=env.root,
                                           committed_check=lambda path, repo: (False, "REGISTRY_UNCOMMITTED"))
        self.assertIn("REGISTRY_UNCOMMITTED", inputs.card_check("SOXL", uncommitted, watchlist, repo=env.root,
                                                                 held=True)["reasons"])

    def test_registry_file_problems(self):
        env = self.env()
        self.assertEqual(inputs.load_registry(env.root / "none.json", repo=env.root)["status"], "MISSING")
        document = load_json(env.registry)
        document["symbols"]["MU"]["static_evidence"][0]["quote"] = "x" * 161
        write_json(env.registry, document)
        self.assertEqual(inputs.load_registry(env.registry, repo=env.root, committed_check=lambda p, r: (True, None))["status"],
                         "INVALID")
        document["symbols"]["MU"]["card_action"] = "BUY"
        write_json(env.registry, document)
        self.assertEqual(inputs.load_registry(env.registry, repo=env.root, committed_check=lambda p, r: (True, None))["status"],
                         "INVALID")

    def test_commit_check_uses_git_tracked_and_clean(self):
        class Done:
            def __init__(self, code, out=""):
                self.returncode, self.stdout = code, out

        def runner(outputs):
            values = iter(outputs)
            return lambda *args, **kwargs: next(values)

        path, repo = ROOT / "docs/claude/x.json", ROOT
        self.assertEqual(inputs.registry_committed(path, repo, runner([Done(0), Done(0, "")])), (True, None))
        self.assertEqual(inputs.registry_committed(path, repo, runner([Done(1), Done(0, "")])),
                         (False, "REGISTRY_UNCOMMITTED"))
        self.assertEqual(inputs.registry_committed(path, repo, runner([Done(0), Done(0, " M docs/claude/x.json")])),
                         (False, "REGISTRY_UNCOMMITTED"))

    def test_real_registry_is_schema_valid_and_every_hash_matches(self):
        registry = inputs.load_registry(committed_check=lambda path, repo: (True, None))
        self.assertEqual(registry["status"], "OK", registry["errors"])
        watchlist = inputs.load_watchlist()
        for symbol in registry["entries"]:
            with self.subTest(symbol=symbol):
                check = inputs.card_check(symbol, registry, watchlist, held=symbol in ("MVLL", "SOXL", "NBIS"))
                self.assertTrue(check["hash_ok"], check["reasons"])
                entry = registry["entries"][symbol]
                self.assertIsNone(entry["trim_target_weight"])
                for item in entry["static_evidence"]:
                    self.assertNotEqual(item["e1_kind"], "technical")

    def test_kind_and_side_go_together(self):
        # r2 R2-9: an alert kind written as evidence (S8 close_at_or_below with side "-") loses eligibility.
        self.assertEqual(inputs.load_registry(committed_check=lambda path, repo: (True, None))["kind_side_invalid"], {})
        document = load_json(inputs.REGISTRY_PATH)
        for trigger in document["symbols"]["SOXL"]["card_triggers"]:
            if trigger["id"] == "S8":
                trigger["side"] = "-"
        watchlist = inputs.load_watchlist()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "card-evidence-registry.json"
            write_json(path, document)
            registry = inputs.load_registry(path, repo=ROOT, committed_check=lambda path, repo: (True, None))
            self.assertEqual((registry["status"], registry["kind_side_invalid"]), ("OK", {"SOXL": ["S8"]}))
            check = inputs.card_check("SOXL", registry, watchlist, repo=ROOT, held=True)
            self.assertFalse(check["eligible"])
            self.assertIn("REGISTRY_KIND_SIDE_INVALID", check["reasons"])
            self.assertTrue(inputs.card_check("NBIS", registry, watchlist, repo=ROOT, held=True)["eligible"])
        self.assertEqual(inputs.kind_side_mismatches({"card_triggers": [
            {"id": "S4", "kind": "ema20_below_twice", "side": "alert"}, {"id": "N1", "kind": "earnings_notice",
                                                                         "side": "info"}]}), ["S4"])


class ResearchRecordTests(unittest.TestCase):
    """F3: deterministic checks; a failing item is dropped, a failing file counts as missing."""

    def setUp(self):
        self.env = Env()
        self.registry = inputs.load_registry(self.env.registry, repo=self.env.root,
                                             committed_check=lambda path, repo: (True, None))

    def tearDown(self):
        self.env.close()

    def fact(self, **overrides):
        base = {"fact_id": "MU-1", "symbol": "MU", "direction": "+", "kind": "contract", "card_trigger_ids": ["U2"],
                "event_session": LAST, "announced_at": f"{LAST}T16:30:00-04:00", "source_kind": "SEC_FILING",
                "source_url": "https://www.sec.gov/x", "criterion_a": True, "root_thesis_damage": False,
                "summary_ko": "TEST_ONLY"}
        base.update(overrides)
        return base

    def load(self):
        return inputs.load_research(root=self.env.research_root, run_day=RUN_DAY, calendar_sessions=CALENDAR_DAYS,
                                    decide_time=NOW, registry=self.registry)

    def test_url_domain_kind_session_and_length_checks(self):
        facts = [self.fact(), self.fact(fact_id="MU-2", source_url="https://investors.example.com/pr"),
                 self.fact(fact_id="MU-3", source_url="https://news.example.org/x"),
                 self.fact(fact_id="MU-4", source_url="http://www.sec.gov/x"),
                 self.fact(fact_id="MU-5", event_session="2026-10-10"),
                 self.fact(fact_id="MU-6", summary_ko="x" * 201)]
        self.env.write_research(facts=facts)
        today = self.load()["today"]
        self.assertEqual(today["status"], "OK")
        self.assertEqual([fact["fact_id"] for fact in today["facts"]], ["MU-1", "MU-2"])
        self.assertEqual({item["fact_id"]: item["reason"] for item in today["dropped"]},
                         {"MU-3": "SOURCE_HOST_NOT_OFFICIAL", "MU-4": "SOURCE_HOST_NOT_OFFICIAL",
                          "MU-5": "EVENT_SESSION_INVALID", "MU-6": "SUMMARY_TOO_LONG"})

    def test_schema_failure_counts_as_missing_record(self):
        self.env.write_research(facts=[self.fact(kind="rumor")])
        self.assertEqual(self.load()["today"]["status"], "INVALID")

    def test_written_after_decide_time_is_invalid(self):
        self.env.write_research(written=(NOW + timedelta(minutes=1)).isoformat())
        self.assertIn("RESEARCH_RECORD_WRITTEN_AT_OUT_OF_RANGE", self.load()["today"]["reasons"])

    def test_recent_records_supply_earlier_facts_and_later_days_are_ignored(self):
        self.env.write_research(facts=[self.fact()])
        earlier = self.env.research_root / "2026-10-01"
        earlier.mkdir(parents=True)
        later = self.env.research_root / "2099-01-01"
        later.mkdir(parents=True)
        write_json(later / "research-record.json", {"broken": True})
        loaded = self.load()
        self.assertEqual(loaded["days"][-1], RUN_DAY)
        self.assertNotIn("2099-01-01", loaded["days"])


class WindowsTaskTests(unittest.TestCase):
    def test_powershell_files_are_ascii(self):
        for name in ("run_auto_core.ps1", "register_auto_core_task.ps1"):
            with self.subTest(file=name):
                (SCRIPTS / name).read_bytes().decode("ascii")

    def test_runner_accepts_only_daily_or_decide(self):
        text = (SCRIPTS / "run_auto_core.ps1").read_text(encoding="ascii")
        self.assertIn('[string]$Command = "daily"', text)
        self.assertIn('if ($Command -cne "daily" -and $Command -cne "decide") {', text)
        self.assertRegex(text, r'if \(\$Command -cne "daily" -and \$Command -cne "decide"\) \{\s+exit 3')
        self.assertIn('("auto-core-" + $Command + "-" + $stamp + ".log")', text)

    def test_registration_has_exactly_the_two_tasks_and_never_runs_them(self):
        text = (SCRIPTS / "register_auto_core_task.ps1").read_text(encoding="ascii")
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        self.assertEqual(sorted(set(re.findall(r'Name = "([^"]+)"', code))),
                         ["InvestmentV2-AutoCore", "InvestmentV2-AutoCoreDecide"])
        self.assertIn('TriggerTime = "07:45"; LimitMinutes = 60', code)
        self.assertIn('Command = "decide"', code)
        self.assertIn("-MultipleInstances IgnoreNew", code)
        self.assertIn('$timezoneReady = $timezoneId -eq "Korea Standard Time"', code)
        self.assertIn("if ($PlanOnly)", code)
        self.assertNotRegex(code, r"Start-ScheduledTask|schtasks\s+/run")


class NoOrderPathTests(unittest.TestCase):
    NEW_FILES = ("auto_core_bars.py", "auto_core_rules.py", "auto_core_inputs.py", "auto_core_tickets.py",
                 "auto_core_decide.py", "auto_core_compare.py", "auto_core_replay.py", "run_auto_core.ps1",
                 "register_auto_core_task.ps1", "portfolio_review_journal.py")

    def test_no_order_command_api_or_tool(self):
        # Written in parts so this test file itself carries none of the strings it looks for.
        forbidden = re.compile("(" + "|".join([r"/api/us/" + "ordr", "ust200" + r"0\d", r"overseas\s+" + "orders",
                                               "kiwoom_" + "order", "order_" + "submit", "place_" + "order"]) + ")",
                               re.IGNORECASE)
        for name in self.NEW_FILES:
            with self.subTest(file=name):
                self.assertIsNone(forbidden.search((SCRIPTS / name).read_text(encoding="utf-8")))

    def test_only_the_two_read_operations_are_called(self):
        text = (SCRIPTS / "auto_core_decide.py").read_text(encoding="utf-8")
        operations = set(re.findall(r'"operation": "([a-z_]+)"', text))
        self.assertEqual(operations, {"account_open_items", "account_daily_fills_read"})

    def test_no_account_identifier_in_outputs(self):
        env = Env()
        try:
            decision = env.run()
            text = json.dumps(decision, ensure_ascii=False)
            for marker in ("acnt", "account_no", "acnt_print"):
                self.assertNotIn(marker, text)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
