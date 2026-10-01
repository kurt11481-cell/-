"""End-to-end S5 exposure review runner: read-only inputs, ledger replay, display outputs. Temp folders only."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_user_confirmed_broker_snapshot as apply_module  # noqa: E402
import cash_flow_evidence as cfe  # noqa: E402
import portfolio_review_journal as journal_module  # noqa: E402
import portfolio_status  # noqa: E402
import regular_session_close_history as rsch  # noqa: E402
import run_portfolio_exposure_review as runner  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
from portfolio_exposure import exposure_display_block  # noqa: E402
from validation_common import canonical_hash, validate_instance  # noqa: E402

CALENDAR = (ROOT / "workspace/calendar-authority/artifacts"
            / "2421eeb7e115ad640b6b0ec76d0d88cfe2a49499c12c39dc35ea5f71c1fed22b/us-equities-core-session-v2.calendar.json")
POLICY = ROOT / "stock-strategy-system/alert_policy.json"
EVAL = "2026-09-30"
NOW = "2026-10-01T12:00:00+00:00"


def calendar_sessions(count: int, end: str = EVAL) -> list[str]:
    sessions = sorted(row["session_date"] for row in json.loads(CALENDAR.read_text(encoding="utf-8"))["sessions"])
    return sessions[:sessions.index(end) + 1][-count:]


def broker_record(as_of: str) -> dict[str, Any]:
    return {"verified": True, "holdings_complete": True, "cash_verified": True, "source": "TEST_ONLY", "as_of": as_of}


class RunnerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="exposure_runner_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.state_path = self.root / "state/portfolio_state.json"
        self.ledger_path = self.root / "state/reconciliation_ledger.jsonl"
        self.journal_path = self.root / "state/decision_journal.json"
        self.closes_root = self.root / "closes"
        self.output_root = self.root / "out"
        self.activation = self.root / "calendar_activation.json"
        self.activation.write_text(json.dumps({
            "activation_status": "ACTIVE",
            "active_calendar_hash": hashlib.sha256(CALENDAR.read_bytes()).hexdigest()}), encoding="utf-8")
        # Calendar authority has no command-line override; tests point the module constants at fixtures.
        # The production default paths and the clock are patched the same way, so these runs count as
        # "default inputs" (an activation proposal is refused for anything else).
        for name, value in (("DEFAULT_ACTIVATION", self.activation), ("DEFAULT_STATE", self.state_path),
                            ("DEFAULT_JOURNAL", self.journal_path), ("DEFAULT_CLOSES_ROOT", self.closes_root)):
            patcher = mock.patch.object(runner, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        clock = mock.patch.object(runner, "current_time", side_effect=lambda: datetime.fromisoformat(self.next_now()))
        clock.start()
        self.addCleanup(clock.stop)
        self.sessions = calendar_sessions(70)
        self.state_path.parent.mkdir(parents=True)
        self.runs = 0

    def next_now(self) -> str:
        """Each run gets its own clock second, like real runs (result files are create-only)."""
        self.runs += 1
        return f"2026-10-01T12:00:{self.runs:02d}+00:00"

    def write_state(self, holdings: dict[str, int], cash: float, *, as_of: str = "2026-09-29", revision: int = 16,
                    ledger: bool = True) -> dict:
        """State file plus (by default) the one ledger entry that confirms this revision, as a real apply leaves it."""
        state = {"schema_version": "1.3", "state_revision": revision, "holdings": holdings,
                 "available_cash_usd": cash, "last_confirmed_broker_snapshot": broker_record(as_of),
                 "timing_plan": {"policy_version": "TEST_ONLY"}}
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if self.ledger_path.exists():
            self.ledger_path.unlink()
        if ledger:
            before = dict(state, state_revision=revision - 1, available_cash_usd=cash - 1.0)
            self.append_ledger(before, state, [
                {"field": "available_cash_usd", "key": None, "old_value": cash - 1.0, "new_value": cash}])
        return state

    def write_history(self, symbol: str, closes: dict[str, str], *, keep_pages: bool = True) -> None:
        """Synthetic pages (15:30 bar and 16:00 bar per session) -> verified history file."""
        rows = []
        for session in sorted(closes, reverse=True):
            day = session.replace("-", "")
            for label, price in (("160000", "1.0000"), ("153000", closes[session])):
                rows.append({"cur_prc": price, "trde_qty": "1", "open_pric": price, "high_pric": price,
                             "low_pric": price, "cntr_tm": day + label, "bus_dt": day, "upd_stkpc_tp": "", "upd_rt": ""})
        for index, row in enumerate(rows):
            if index % 100 == 99 or index == len(rows) - 1:
                row["upd_stkpc_tp"] = "1f"
        folder = self.closes_root / "pages" / symbol
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "p1.json").write_text(json.dumps({"result": {"result_list": rows, "return_code": 0}}), encoding="utf-8")
        history = rsch.build_history(symbol=symbol, exchange="NASDAQ", page_paths=[folder / "p1.json"],
                                     calendar=rsch.load_calendar(CALENDAR, self.activation))
        target = self.closes_root / "history" / f"{symbol}.close-history.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(history), encoding="utf-8")
        if not keep_pages:
            shutil.rmtree(folder)

    def write_default_histories(self) -> None:
        bench = fx.benchmark_returns(len(self.sessions))
        self.write_history("SOXX", fx.series(self.sessions, bench, last="500"))
        self.write_history("SOXL", fx.series(self.sessions, bench, last="100", multiple=2.9))

    def run_review(self, *extra: str) -> tuple[int, str, dict | None]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = runner.main([
                "--policy", str(POLICY), "--state", str(self.state_path), "--journal", str(self.journal_path),
                "--closes-root", str(self.closes_root), "--calendar", str(CALENDAR), "--session", EVAL,
                "--output-root", str(self.output_root), *extra])
        files = sorted(self.output_root.glob(f"{EVAL}/portfolio-exposure-review.*.json"))
        return code, buffer.getvalue(), json.loads(files[-1].read_text(encoding="utf-8")) if files else None

    def confirm_journal(self, proposal: dict) -> dict:
        return journal_module.apply_proposal(
            journal_path=self.journal_path, proposal=proposal,
            confirmation={"confirm_code": proposal["confirm_code"], "confirmation_method": "COWORK_CHAT_USER_MESSAGE",
                          "user_message": f"확인 {proposal['confirm_code']}"})

    def activate(self, review: dict) -> None:
        proposal = journal_module.build_proposal(
            entry_type="s5_activation", payload=journal_module.activation_payload(review), review=review,
            journal=journal_module.load_journal(self.journal_path), now=datetime.now(timezone.utc))
        self.confirm_journal(proposal)

    def append_ledger(self, before: dict, after: dict, changes: list[dict], block: Any = None) -> None:
        status = apply_module.ledger_status(self.ledger_path)
        entry = {"schema_version": "1.0", "event": "APPLY", "proposal_schema_version": "kiwoom-reconciliation-1.0",
                 "confirmed_at": "2026-09-30T00:00:00+00:00", "state_revision_before": before["state_revision"],
                 "state_revision_after": after["state_revision"], "portfolio_hash_before": canonical_hash(before),
                 "portfolio_hash_after": canonical_hash(after), "changes": changes,
                 "state_changed_outside_ledger": False, "previous_entry_sha256": status["last_entry_sha256"]}
        if block is not None:
            entry["cash_flow_declaration"] = block
        apply_module._append_ledger(self.ledger_path, entry)


class EndToEndTests(RunnerCase):
    def test_activation_then_verified_review_and_displays(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()
        before = {path: path.read_bytes() for path in (self.state_path, POLICY)}
        code, output, review = self.run_review()
        self.assertEqual(code, 0)
        self.assertEqual(validate_instance(review, runner.REVIEW_SCHEMA), [])
        active = [item["id"] for item in review["fail_closed"]["triggers"] if item["active"]]
        self.assertEqual(active, ["hwm_line_or_pause_state_missing_or_corrupt", "decision_journal_missing_or_corrupt"])
        self.assertEqual(review["recommendations"]["add"], [])
        self.assertEqual((review["activation_candidate"]["status"], review["activation_candidate"]["hwm_usd"]),
                         ("READY", "10000.0"))
        self.assertIn("노출 E 0.90(미확인)(짧은 이력)", output)
        self.assertIn("검토선 미적용", output)
        self.assertIn("주문·수량 권한 없음", output)
        self.assertFalse(self.journal_path.exists())  # the runner never writes the journal

        self.activate(review)
        code, output, review = self.run_review()
        self.assertEqual(code, 0)
        self.assertFalse(review["fail_closed"]["active"], review["fail_closed"])
        self.assertEqual((review["exposure"]["status"], review["exposure"]["return_sessions_used"],
                          review["exposure"]["short_history"]), ("VERIFIED", 69, True))
        self.assertEqual([item["symbol"] for item in review["recommendations"]["add"]], ["SOXL"])
        self.assertEqual(review["review_lines"]["status"], "EVALUATED")
        self.assertIn("노출 E 0.90(짧은 이력)", output)
        self.assertIn("다음 검토선 L1까지 10.0%", output)
        self.assertIn("채우기 권고 1건(미검증 사용자 위험 예산, 표시 전용)", output)
        self.assertEqual((review["order_authority"], review["quantity_authority"], review["execution_quantity"]),
                         (False, "none", None))
        self.assertEqual(review["inputs"]["calendar"]["authority_status"], "ACTIVE")
        self.assertTrue(all(item["reproduced_from_pages"] for item in review["inputs"]["close_histories"].values()))
        self.assertEqual(review["inputs"]["non_default_inputs"], [])
        self.assertEqual(review["inputs"]["evaluation_session_status"], "LATEST_COMPLETED_SESSION")
        self.assertNotIn("[비표준 입력]", output)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)  # inputs are never written
        self.assertEqual(len(list(self.output_root.glob(f"{EVAL}/*.json"))), 2)
        self.assertEqual(sorted(path.name for path in self.state_path.parent.iterdir()),
                         ["decision_journal.json", "portfolio_state.json", "reconciliation_ledger.jsonl"])

        # Status one-liner picks up the latest review and does not count S5 entries as pending scoring.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            portfolio_status.main(["--root", str(self.root / "empty"), "--journal", str(self.journal_path),
                                   "--exposure-dir", str(self.output_root), "--output", str(self.root / "status.json"),
                                   "--now", NOW])
        status = json.loads((self.root / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["exposure_review"]["status"], "OK")
        self.assertEqual(status["exposure_review"]["review_id"], review["review_id"])
        self.assertEqual((status["scoring_pending"]["entry_count"], status["scoring_pending"]["pending_count"]), (1, 0))
        self.assertIn("노출 E 0.90(짧은 이력)", buffer.getvalue())

    def test_non_default_inputs_are_labelled_and_cannot_start_activation(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()
        other_journal = self.root / "other" / "decision_journal.json"
        code, output, review = self.run_review("--journal", str(other_journal), "--now", "2026-10-01T13:00:00+00:00")
        self.assertEqual(code, 0)
        self.assertEqual(review["inputs"]["non_default_inputs"], ["journal", "now"])
        self.assertTrue(output.splitlines()[0].endswith(" [비표준 입력]"))
        candidate = review["activation_candidate"]
        self.assertEqual((candidate["status"], candidate["reasons"]), ("NOT_READY", ["NON_DEFAULT_INPUTS:journal,now"]))
        with self.assertRaisesRegex(journal_module.JournalError, "ACTIVATION_CANDIDATE_NOT_READY"):
            journal_module.activation_payload(review)

    def test_a_journal_proposal_must_come_from_a_review_of_the_current_journal(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()
        _, _, stale = self.run_review()
        self.activate(stale)
        with self.assertRaisesRegex(journal_module.JournalError, "REVIEW_JOURNAL_HEAD_MISMATCH"):
            journal_module.build_proposal(
                entry_type="line_review_completed", payload={}, review=stale,
                journal=journal_module.load_journal(self.journal_path), now=datetime.now(timezone.utc))

    def test_missing_or_unverified_closes_fail_closed_but_keep_values_visible(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        bench = fx.benchmark_returns(len(self.sessions))
        self.write_history("SOXL", fx.series(self.sessions, bench, last="100", multiple=2.9))
        code, _, review = self.run_review()  # no SOXX history at all
        self.assertEqual(code, 0)
        self.assertEqual(review["inputs"]["close_histories"]["SOXX"], {"status": "MISSING"})
        self.assertIsNone(review["exposure"]["effective"])
        self.assertAlmostEqual(review["exposure"]["effective_lower_bound"], 0.9, places=6)
        self.assertIn(f"CLOSE_MISSING:SOXX:{EVAL}",
                      next(item for item in review["fail_closed"]["triggers"]
                           if item["id"] == "required_price_missing")["reasons"])
        self.write_history("SOXX", fx.series(self.sessions, bench, last="500"), keep_pages=False)
        _, _, review = self.run_review()
        reasons = next(item for item in review["fail_closed"]["triggers"] if item["id"] == "required_price_missing")
        self.assertEqual(reasons["reasons"], ["CLOSE_UNVERIFIED:SOXX:CLOSE_HISTORY_PAGES_NOT_VERIFIED"])
        self.assertEqual(review["exposure"]["status"], "UNVERIFIED")
        self.assertIsNotNone(review["exposure"]["effective"])

    def test_calendar_that_is_not_active_leaves_every_close_unverified(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.activation.write_text(json.dumps({"activation_status": "ACTIVE", "active_calendar_hash": "0" * 64}),
                                   encoding="utf-8")
        self.write_default_histories()
        _, output, review = self.run_review()
        reasons = next(item for item in review["fail_closed"]["triggers"] if item["id"] == "required_price_missing")
        self.assertEqual(reasons["reasons"], ["CLOSE_UNVERIFIED:SOXL:SESSION_CALENDAR_NOT_ACTIVE",
                                              "CLOSE_UNVERIFIED:SOXX:SESSION_CALENDAR_NOT_ACTIVE"])
        self.assertEqual(review["inputs"]["calendar"]["authority_status"], "EXPLICIT_ARTIFACT_NOT_ACTIVE")
        self.assertIn("(미확인)", output)
        # Judge fix b: no activation proposal while closes are unverified, even with default inputs.
        self.assertEqual(review["inputs"]["non_default_inputs"], [])
        self.assertEqual(review["activation_candidate"]["status"], "NOT_READY")
        with self.assertRaisesRegex(journal_module.JournalError, "ACTIVATION_CANDIDATE_NOT_READY"):
            journal_module.activation_payload(review)

    def test_history_file_cannot_claim_an_active_calendar_or_verified_closes_by_itself(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()  # built while the fixture activation said ACTIVE
        for symbol in ("SOXX", "SOXL"):
            history = json.loads((self.closes_root / f"history/{symbol}.close-history.json").read_text(encoding="utf-8"))
            self.assertEqual(history["calendar"]["authority_status"], "ACTIVE")
        self.activation.write_text(json.dumps({"activation_status": "ACTIVE", "active_calendar_hash": "0" * 64}),
                                   encoding="utf-8")
        _, _, review = self.run_review()  # this run's calendar is not the active one
        reasons = next(item for item in review["fail_closed"]["triggers"] if item["id"] == "required_price_missing")
        self.assertEqual(reasons["reasons"], ["CLOSE_UNVERIFIED:SOXL:SESSION_CALENDAR_NOT_ACTIVE",
                                              "CLOSE_UNVERIFIED:SOXX:SESSION_CALENDAR_NOT_ACTIVE"])
        self.assertNotIn("calendar_activation", " ".join(runner.build_parser().format_help().split()))

    def test_edited_history_with_a_recomputed_hash_is_not_reproducible_from_the_pages(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()
        path = self.closes_root / "history/SOXL.close-history.json"
        history = json.loads(path.read_text(encoding="utf-8"))
        history["sessions"][-1]["close"] = "150"
        history["history_hash"] = rsch.history_content_hash(history)
        self.assertEqual(rsch.history_errors(history, pages_dir=self.closes_root / "pages/SOXL"), [])
        path.write_text(json.dumps(history), encoding="utf-8")
        _, _, review = self.run_review()
        self.assertEqual(review["inputs"]["close_histories"]["SOXL"],
                         {"status": "INVALID", "errors": ["CLOSE_HISTORY_NOT_REPRODUCIBLE_FROM_PAGES"]})
        self.assertEqual(review["equity"]["status"], "UNAVAILABLE")
        # A page that is saved but not yet built into the history makes the history stale.
        self.write_default_histories_overwrite()
        extra = self.closes_root / "pages/SOXX/p0.json"
        extra.write_text(json.dumps({"result": {"return_code": 0, "result_list": [
            {"cur_prc": "1", "trde_qty": "1", "open_pric": "1", "high_pric": "1", "low_pric": "1",
             "cntr_tm": "20261001040000", "bus_dt": "20261001", "upd_stkpc_tp": "1f", "upd_rt": ""}]}}),
            encoding="utf-8")
        _, _, review = self.run_review()
        self.assertEqual(review["inputs"]["close_histories"]["SOXX"]["errors"],
                         ["CLOSE_HISTORY_NOT_REPRODUCIBLE_FROM_PAGES"])

    def test_tampered_history_or_page_is_treated_as_absent(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()
        path = self.closes_root / "history/SOXL.close-history.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"close": "100"', '"close": "150"'), encoding="utf-8")
        _, _, review = self.run_review()
        self.assertEqual(review["inputs"]["close_histories"]["SOXL"],
                         {"status": "INVALID", "errors": ["CLOSE_HISTORY_HASH_MISMATCH"]})
        self.assertEqual(review["equity"]["status"], "UNAVAILABLE")
        self.write_default_histories_overwrite()
        page = self.closes_root / "pages/SOXX/p1.json"
        page.write_bytes(page.read_bytes().replace(b'"500"', b'"501"'))
        _, _, review = self.run_review()
        self.assertEqual(review["inputs"]["close_histories"]["SOXX"]["errors"],
                         ["CLOSE_HISTORY_PAGE_HASH_MISMATCH:p1.json"])

    def write_default_histories_overwrite(self) -> None:
        shutil.rmtree(self.closes_root)
        self.write_default_histories()

    def test_output_root_inside_protected_folders_and_bad_sessions_are_rejected(self) -> None:
        self.write_state({"SOXL": 30}, 7000.0)
        self.write_default_histories()
        for extra in (("--output-root", str(ROOT / "stock-strategy-system/s5-test-output")),
                      ("--output-root", str(ROOT / "workspace/policies/s5-test-output")),
                      ("--session", "2026-10-03")):
            with self.subTest(extra=extra):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = runner.main([
                        "--policy", str(POLICY), "--state", str(self.state_path), "--journal", str(self.journal_path),
                        "--closes-root", str(self.closes_root), "--calendar", str(CALENDAR), "--session", EVAL,
                        "--output-root", str(self.output_root), *extra])
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(buffer.getvalue())["status"], "FAIL")
        self.assertFalse((ROOT / "stock-strategy-system/s5-test-output").exists())

    def test_expected_completed_session_comes_from_the_calendar(self) -> None:
        calendar = rsch.load_calendar(CALENDAR, None)
        for now, expected in (("2026-09-30T19:59:00+00:00", "2026-09-29"), ("2026-09-30T20:00:00+00:00", "2026-09-30"),
                              ("2026-10-04T12:00:00+00:00", "2026-10-02")):
            self.assertEqual(runner.expected_completed_session(calendar, datetime.fromisoformat(now)), expected)


class LedgerReplayTests(RunnerCase):
    def states(self) -> list[dict]:
        base = {"schema_version": "1.3", "state_revision": 14, "holdings": {"SOXL": 30, "MVLL": 10},
                "available_cash_usd": 6500.0, "last_confirmed_broker_snapshot": broker_record("2026-09-25")}
        second = dict(base, state_revision=15, holdings={"SOXL": 30}, available_cash_usd=6500.0,
                      last_confirmed_broker_snapshot=broker_record("2026-09-28"))
        third = dict(second, state_revision=16, available_cash_usd=7000.0,
                     last_confirmed_broker_snapshot=broker_record("2026-09-29"))
        return [base, second, third]

    def write_ledger(self, blocks: tuple[Any, Any] = (None, None)) -> list[dict]:
        base, second, third = self.states()
        self.append_ledger(base, second, [
            {"field": "holdings", "key": "MVLL", "old_value": 10, "new_value": None},
            {"field": "last_confirmed_broker_snapshot", "key": "as_of", "old_value": "2026-09-25",
             "new_value": "2026-09-28"}], blocks[0])
        self.append_ledger(second, third, [
            {"field": "available_cash_usd", "key": None, "old_value": 6500.0, "new_value": 7000.0},
            {"field": "last_confirmed_broker_snapshot", "key": "as_of", "old_value": "2026-09-28",
             "new_value": "2026-09-29"}], blocks[1])
        self.state_path.write_text(json.dumps(third, indent=2), encoding="utf-8")
        return [base, second, third]

    def replay(self) -> tuple[list[dict], list[str], list[str]]:
        status = apply_module.ledger_status(self.ledger_path)
        entries = runner.read_ledger_entries(self.ledger_path) if status["exists"] and status["chain_ok"] else []
        return runner.reconstruct_snapshots(
            json.loads(self.state_path.read_text(encoding="utf-8")), entries,
            chain_ok=status["chain_ok"], ledger_exists=status["exists"])

    def test_holdings_history_is_rebuilt_from_the_ledger(self) -> None:
        self.write_ledger()
        snapshots, reasons, notes = self.replay()
        self.assertEqual((reasons, notes), ([], []))
        self.assertEqual([(item["state_revision"], item["as_of"], item["holdings"], item["cash_usd"],
                           item["holdings_decreased"], item["from_ledger_entry"]) for item in snapshots], [
            (14, "2026-09-25", {"SOXL": 30, "MVLL": 10}, "6500.0", False, False),
            (15, "2026-09-28", {"SOXL": 30}, "6500.0", True, True),
            (16, "2026-09-29", {"SOXL": 30}, "7000.0", False, True)])

    def test_state_changed_outside_the_ledger_is_not_trusted(self) -> None:
        self.write_ledger()
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["holdings"]["SOXL"] = 31
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        snapshots, reasons, _ = self.replay()
        self.assertEqual((len(snapshots), reasons), (1, ["STATE_CHANGED_OUTSIDE_LEDGER"]))
        self.write_default_histories()
        _, _, review = self.run_review()
        trigger = next(item for item in review["fail_closed"]["triggers"]
                       if item["id"] == "exposure_or_equity_or_v_unavailable")
        self.assertIn("STATE_CHANGED_OUTSIDE_LEDGER", trigger["reasons"])

    def test_broken_ledger_chain_is_not_trusted(self) -> None:
        self.write_ledger()
        lines = self.ledger_path.read_bytes().splitlines()
        self.ledger_path.write_bytes(lines[1] + b"\n")
        snapshots, reasons, _ = self.replay()
        self.assertEqual((len(snapshots), reasons), (1, ["LEDGER_INTEGRITY_FAILED"]))

    def test_unverified_broker_record_and_missing_ledger(self) -> None:
        state = self.write_state({"SOXL": 30}, 7000.0, ledger=False)
        snapshots, reasons, notes = self.replay()
        self.assertEqual((len(snapshots), reasons, notes), (1, [], ["RECONCILIATION_LEDGER_EMPTY_STATE_SNAPSHOT_ONLY"]))
        state["last_confirmed_broker_snapshot"]["cash_verified"] = False
        state["last_confirmed_broker_snapshot"]["holdings_complete"] = False
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.replay()[1], ["BROKER_SNAPSHOT_NOT_VERIFIED_COMPLETE", "BROKER_CASH_NOT_VERIFIED"])

    def test_entry_that_recorded_an_outside_change_ends_the_history(self) -> None:
        base, second, third = self.states()
        self.append_ledger(base, second, [{"field": "holdings", "key": "MVLL", "old_value": 10, "new_value": None}])
        status = apply_module.ledger_status(self.ledger_path)
        entry = {"schema_version": "1.0", "event": "APPLY", "proposal_schema_version": "kiwoom-reconciliation-1.0",
                 "state_revision_before": 15, "state_revision_after": 16, "portfolio_hash_before": "x",
                 "portfolio_hash_after": canonical_hash(third), "state_changed_outside_ledger": True,
                 "changes": [{"field": "available_cash_usd", "key": None, "old_value": 1.0, "new_value": 7000.0}],
                 "previous_entry_sha256": status["last_entry_sha256"]}
        apply_module._append_ledger(self.ledger_path, entry)
        self.state_path.write_text(json.dumps(third), encoding="utf-8")
        snapshots, reasons, notes = self.replay()
        self.assertEqual(([item["state_revision"] for item in snapshots], reasons), ([16], []))
        self.assertEqual(notes, ["LEDGER_ENTRY_RECORDED_OUTSIDE_CHANGE_AT_REVISION:16"])

    def test_post_activation_reconciliation_needs_a_cash_flow_declaration(self) -> None:
        deposit = {"deal_dt": "20260929", "deal_no": "000000001", "deal_kind_nm": "입출금",
                   "rmrk_nm": "이체입금", "fc_exct_amt": "500.00", "crnc_code": "USD"}
        evidence = cfe.normalize_transaction_history(
            {"result": {"return_code": 0, "result_list": [deposit]}}, period_from="2026-09-28",
            period_to="2026-09-30", raw_sha256="e" * 64)
        bench = fx.benchmark_returns(len(self.sessions))
        soxl = fx.series(self.sessions, bench, last="100", multiple=2.9)
        soxl.update({session: "100" for session in self.sessions[-3:]})  # flat closes: equity moves only by cash
        self.write_history("SOXX", fx.series(self.sessions, bench, last="500"))
        self.write_history("SOXL", soxl)
        for declared, expect_hold in ((None, True), ("500.00", False)):
            with self.subTest(declared=declared):
                if self.ledger_path.exists():
                    self.ledger_path.unlink()
                block = cfe.build_declaration(evidence, declared_usd=declared, prior_blocks=[])
                self.write_ledger((None, block))
                self.journal_path.write_text(json.dumps({
                    "schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL",
                    "order_authority": False, "quantity_authority": "none", "entries": []}), encoding="utf-8")
                # Activation at revision 15: only the 15 -> 16 reconciliation needs cash-flow coverage.
                journal = journal_module.load_journal(self.journal_path)
                entry = {"entry_type": "s5_activation", "entry_id": "a" * 64, "sequence": 1,
                         "previous_entry_sha256": journal["head_sha256"], "confirm_code": "AAAAAAAA",
                         "confirmation_method": "USER_TERMINAL", "user_message": "AAAAAAAA",
                         "user_confirmed_at": "2026-09-28T21:00:00Z", "review_id": "b" * 64,
                         "evaluation_session": "2026-09-28",
                         "payload": {"activation_date": "2026-09-28", "hwm_usd": "9500", "hwm_as_of": "2026-09-28",
                                     "hwm_policy_initial_usd": "28473.94", "hwm_difference_usd": "-18973.94",
                                     "state_revision": 15, "window_start": "2026-09-28", "window_end": "2026-09-28",
                                     "close_basis": "FINAL_REGULAR_SESSION_30M_BAR_CLOSE"},
                         "order_authority": False, "quantity_authority": "none"}
                self.journal_path.write_text(json.dumps({
                    "schema_version": "decision-journal-1.0", "journal_type": "DECISION_JOURNAL",
                    "order_authority": False, "quantity_authority": "none", "entries": [entry]}), encoding="utf-8")
                _, _, review = self.run_review()
                trigger = next(item for item in review["fail_closed"]["triggers"] if item["id"] == "undeclared_cash_flow")
                self.assertEqual(trigger["active"], expect_hold)
                if expect_hold:
                    self.assertEqual(review["review_lines"]["status"], "HELD")
                    self.assertEqual(review["review_lines"]["hwm_usd"], "9500")
                else:
                    self.assertEqual((review["review_lines"]["status"], review["review_lines"]["hwm_usd"]),
                                     ("EVALUATED", "10000.00"))  # 9,500 + declared 500; equity 10,000 is not a gain
                    self.assertEqual(review["review_lines"]["hwm_date"], "2026-09-28")


class DisplayTests(RunnerCase):
    def test_display_block_never_carries_recommendation_targets(self) -> None:
        self.write_state({"SOXL": 62}, 3800.0)  # above band: reduce recommendations exist
        self.write_default_histories()
        _, _, review = self.run_review()
        self.assertTrue(review["recommendations"]["reduce"])
        block = exposure_display_block(review)
        self.assertNotIn("target", json.dumps(block))
        self.assertNotIn("recommendations", block)


if __name__ == "__main__":
    unittest.main()
