"""cowork-to-room-k3: reconciliation apply and two S5 journal entries from the CEO-office company-PC thread (R1, R2),
and propose refused without cash-flow evidence after S5 activation (R3). Pre-registered tests T1-T20
(docs/claude/cowork-to-room-k3-proposal-2026-11-20.md section 4).

All data is synthetic (TEST_ONLY). Temp folders only: no real state, journal, ledger or backup is read or written,
no Kiwoom runtime (the reader is a stub that counts its calls).
"""

from __future__ import annotations

import ast
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import apply_user_confirmed_broker_snapshot as apply_module  # noqa: E402
import portfolio_review_journal as journal_module  # noqa: E402
import reconcile_broker_state as cli  # noqa: E402
import s5_exposure_fixtures as fx  # noqa: E402
import validation_common  # noqa: E402
from portfolio_exposure import journal_view  # noqa: E402
from test_cash_flow_evidence import DEPOSIT, DIVIDEND, evidence  # noqa: E402
from test_holding_card import make_card  # noqa: E402
from test_portfolio_exposure import EVAL, Scenario  # noqa: E402
from test_portfolio_exposure_fail_closed import line_scenario  # noqa: E402
from test_portfolio_review_journal import not_activated_review  # noqa: E402
from test_reconcile_broker_state import (  # noqa: E402
    ALL_OPERATIONS, TempStateCase, account_results, base_state, make_proposal, utc,
)
from validation_common import load_json  # noqa: E402

THREAD = "PROJECT_THREAD_USER_DECISION"
BASE_COMMIT = "22d44cf"


def thread_message(text: str, *, message_id: str = "cmsg_TEST", account: str = "user_TEST",
                   time: str = "2026-11-20 13:10:00 KST") -> str:
    return f"{message_id} | {account} | {time} | {text}"


# ---------------------------------------------------------------------------------------------
# R1: reconciliation apply (library)
# ---------------------------------------------------------------------------------------------

class ReconcileThreadLibraryTests(TempStateCase):
    def setUp(self):
        super().setUp()
        self.state = base_state()
        self.original = self.write_state(self.state)
        self.proposal = make_proposal(self.state)
        self.code = self.proposal["confirm_code"]

    def thread(self, message, **kwargs):
        return self.apply(self.proposal, self.confirmation(self.proposal, method=THREAD, message=message), **kwargs)

    def ledger_entry(self):
        return json.loads((self.directory / "reconciliation_ledger.jsonl").read_text(encoding="utf-8"))

    def assert_rejected(self, reason, message, **kwargs):
        with self.assertRaisesRegex(ValueError, reason):
            self.thread(message, **kwargs)
        self.assert_nothing_written(self.original)

    def test_t1_thread_apply_records_method_and_four_fields(self):
        message = thread_message(f"확인 {self.code}")
        audit = self.thread(message)
        self.assertEqual(audit["state_revision_after"], 8)
        entry = self.ledger_entry()
        self.assertEqual(entry["confirmation_method"], THREAD)
        self.assertEqual(entry["user_message"], message)
        self.assertEqual(load_json(self.state_path)["last_confirmed_broker_snapshot"]["confirmation_method"], THREAD)

    def test_t1_lower_case_code_in_verbatim_field_is_accepted_like_the_other_methods(self):
        self.thread(thread_message(f"확인 {self.code.lower()}"))
        self.assertEqual(self.ledger_entry()["confirmation_method"], THREAD)

    def test_t2_thread_without_message_is_rejected_by_the_library(self):
        for message in (None, "", "   "):
            with self.subTest(message=message):
                self.assert_rejected("PROJECT_THREAD_MESSAGE_INVALID", message)

    def test_t3_bad_four_field_format_is_rejected_by_the_library(self):
        for message in (
                f"cmsg_TEST | user_TEST | 확인 {self.code}",                                  # three fields
                f"cmsg_TEST | | 2026-11-20 13:10:00 KST | 확인 {self.code}",                  # empty field
                f"cmsg_TEST |    | 2026-11-20 13:10:00 KST | 확인 {self.code}",               # blank field
                f"cmsg_TEST | acct_TEST | 2026-11-20 13:10:00 KST | 확인 {self.code}",        # no user_
                f"cmsg_TEST | user_TEST | 2026-11-20 13:10:00 | 확인 {self.code}",            # no KST
                f"cmsg_TEST | user_TEST | 2026-11-20 13:10:00 UTC | 확인 {self.code}",        # wrong zone
                f"cmsg | x | user_TEST | 2026-11-20 13:10:00 KST | 확인 {self.code}",         # shifted by a |
                f"확인 {self.code}"):                                                         # Cowork-style text
            with self.subTest(message=message):
                self.assert_rejected("PROJECT_THREAD_MESSAGE_INVALID", message)

    def test_t4_four_fields_without_this_code_are_rejected(self):
        other = "0" * 8 if self.code != "0" * 8 else "1" * 8
        for message in (thread_message("확인"), thread_message(f"확인 {other}"), thread_message("취소")):
            with self.subTest(message=message):
                self.assert_rejected("CONFIRM_CODE_NOT_IN_USER_MESSAGE", message)

    def test_t5_cowork_and_terminal_paths_are_unchanged(self):
        with self.assertRaisesRegex(ValueError, "USER_CONFIRMATION_MESSAGE_REQUIRED"):
            self.apply(self.proposal, self.confirmation(self.proposal, message="확인"))
        with self.assertRaisesRegex(ValueError, "USER_CONFIRMATION_MESSAGE_REQUIRED"):
            self.apply(self.proposal, self.confirmation(self.proposal, method="USER_TERMINAL", message="yes"))
        self.assert_nothing_written(self.original)
        self.apply(self.proposal, self.confirmation(self.proposal, method="USER_TERMINAL", message=self.code))
        self.assertEqual(self.ledger_entry()["confirmation_method"], "USER_TERMINAL")

    def test_t5_cowork_message_with_the_code_still_applies(self):
        self.apply(self.proposal, self.confirmation(self.proposal))
        self.assertEqual(self.ledger_entry()["confirmation_method"], "COWORK_CHAT_USER_MESSAGE")

    def test_t15_code_only_in_the_id_account_or_time_field_is_rejected(self):
        for message in (thread_message("확인", message_id=f"cmsg_{self.code}"),
                        thread_message("확인", account=f"user_{self.code}"),
                        thread_message("확인", time=f"2026-11-20 {self.code} KST")):
            with self.subTest(message=message):
                self.assert_rejected("CONFIRM_CODE_NOT_IN_USER_MESSAGE", message)

    def test_t16_four_field_message_under_the_cowork_method_still_passes(self):
        """Recorded current behaviour: the script cannot tell which session chose the method. The thread is kept
        to PROJECT_THREAD_USER_DECISION by the CLAUDE.md rule only (proposal section 3)."""
        message = thread_message(f"확인 {self.code}")
        self.apply(self.proposal, self.confirmation(self.proposal, method="COWORK_CHAT_USER_MESSAGE",
                                                    message=message))
        self.assertEqual(self.ledger_entry()["confirmation_method"], "COWORK_CHAT_USER_MESSAGE")

    def test_t19_forged_but_well_formed_fields_pass_the_script(self):
        """Recorded limit: the script checks the format only; who typed it is proven by the harness mark."""
        message = thread_message(f"확인 {self.code}", message_id="cmsg_FORGED", account="user_FORGED",
                                 time="2000-01-01 00:00:00 KST")
        self.thread(message)
        self.assertEqual(self.ledger_entry()["user_message"], message)

    def test_t20_expired_proposal_is_rejected_even_with_valid_fields(self):
        expires = datetime.fromisoformat(self.proposal["expires_at"].replace("Z", "+00:00"))
        self.assert_rejected("BROKER_PROPOSAL_EXPIRED", thread_message(f"확인 {self.code}"),
                             now=expires + timedelta(seconds=1))


class SharedHelperTests(unittest.TestCase):
    def test_one_definition_is_shared_by_reconciliation_and_journal(self):
        self.assertIs(journal_module.PROJECT_THREAD_METHOD, validation_common.PROJECT_THREAD_METHOD)
        self.assertIn(validation_common.PROJECT_THREAD_METHOD, apply_module.CONFIRMATION_METHODS)
        self.assertIs(apply_module.project_thread_message_valid, validation_common.project_thread_message_valid)
        self.assertIs(apply_module.project_thread_code_in_verbatim, validation_common.project_thread_code_in_verbatim)
        self.assertIs(journal_module.project_thread_code_in_verbatim,
                      validation_common.project_thread_code_in_verbatim)
        tree = ast.parse((SCRIPTS / "apply_user_confirmed_broker_snapshot.py").read_text(encoding="utf-8"))
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} | {
            alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertNotIn("portfolio_review_journal", modules)

    def test_verbatim_field_rule(self):
        check = validation_common.project_thread_code_in_verbatim
        self.assertTrue(check("a | user_x | t KST | 확인 abcd1234", "ABCD1234"))
        self.assertTrue(check("a | user_x | t KST | 확인 | ABCD1234", "ABCD1234"))  # extra | inside field 4
        self.assertFalse(check("ABCD1234 | user_x | t KST | 확인", "ABCD1234"))
        self.assertFalse(check("a | user_x | t KST | 확인 ABCD1234", " "))
        self.assertFalse(check(None, "ABCD1234"))


# ---------------------------------------------------------------------------------------------
# R1 through the CLI, and R3 propose
# ---------------------------------------------------------------------------------------------

class CliCase(TempStateCase):
    def setUp(self):
        super().setUp()
        self.runtime = self.directory / "runtime"
        self.runtime.mkdir()
        self.output_root = self.directory / "outputs"
        self.journal_path = self.directory / "decision_journal.json"
        self.policies = {}
        for name, value in (("readonly", {"official_runtime_path": str(self.runtime)}), ("rate", {}),
                            ("broker", {"maximum_age_seconds": 900}),
                            ("alert", {"daily_engine_scope": "TEST_ONLY_NOT_LEVERAGED"})):
            path = self.directory / f"{name}.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            self.policies[name] = path
        self.original = self.write_state(base_state())
        self.calls = 0

    def run_cli(self, argv, reader=None):
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(argv, reader=reader)
        return code, output.getvalue()

    def propose(self, *extra):
        def reader(requests, *, runtime, policy):
            self.calls += 1
            self.assertEqual([item["operation"] for item in requests], list(ALL_OPERATIONS))
            return account_results(utc(datetime.now(timezone.utc)))
        return self.run_cli([
            "propose", "--readonly-policy", str(self.policies["readonly"]), "--rate-policy", str(self.policies["rate"]),
            "--broker-policy", str(self.policies["broker"]), "--alert-policy", str(self.policies["alert"]),
            "--portfolio-state", str(self.state_path), "--output-root", str(self.output_root),
            "--journal", str(self.journal_path), *extra], reader=reader)

    def latest(self):
        return load_json(cli.resolve_proposal_path("latest", self.output_root))

    def apply_cli(self, *extra):
        return self.run_cli(["apply", "--output-root", str(self.output_root), "--portfolio-state", str(self.state_path),
                             *extra])

    def activate_journal(self):
        review = not_activated_review()
        proposal = journal_module.build_proposal(
            entry_type="s5_activation", payload=journal_module.activation_payload(review), review=review,
            journal=journal_module.load_journal(self.journal_path), now=datetime.now(timezone.utc))
        journal_module.apply_proposal(journal_path=self.journal_path, proposal=proposal, confirmation={
            "confirm_code": proposal["confirm_code"], "confirmation_method": "COWORK_CHAT_USER_MESSAGE",
            "user_message": f"확인 {proposal['confirm_code']}"})
        self.assertIsNotNone(journal_view(journal_module.load_journal(self.journal_path))["activation"])

    def assert_refused_before_read(self, code, output, reason):
        self.assertEqual(code, 2)
        self.assertEqual(self.calls, 0)
        self.assertIn(reason, output)
        self.assertFalse(self.output_root.exists())
        self.assertEqual(self.state_path.read_bytes(), self.original)


class ThreadCliTests(CliCase):
    def test_t1_cli_apply_with_thread_fields(self):
        self.assertEqual(self.propose()[0], 0)
        proposal = self.latest()
        message = thread_message(f"확인 {proposal['confirm_code']}")
        code, output = self.apply_cli("--confirm", proposal["confirm_code"], "--confirmed-via", THREAD,
                                      "--user-message", message)
        self.assertEqual(code, 0, output)
        entry = json.loads((self.directory / "reconciliation_ledger.jsonl").read_text(encoding="utf-8"))
        self.assertEqual((entry["confirmation_method"], entry["user_message"]), (THREAD, message))

    def test_t2_cli_thread_without_user_message_is_rejected(self):
        self.propose()
        code, output = self.apply_cli("--confirm", self.latest()["confirm_code"], "--confirmed-via", THREAD)
        self.assertEqual(code, 2)
        self.assertIn(cli._messages()["apply_user_message_required"], output)
        self.assert_nothing_written(self.original)

    def test_t3_cli_bad_format_is_rejected(self):
        self.propose()
        code_text = self.latest()["confirm_code"]
        code, output = self.apply_cli("--confirm", code_text, "--confirmed-via", THREAD,
                                      "--user-message", f"확인 {code_text}")
        self.assertEqual(code, 2)
        self.assertIn("PROJECT_THREAD_MESSAGE_INVALID", output)
        self.assert_nothing_written(self.original)


class ProposeEvidenceTests(CliCase):
    def test_t10_activation_without_evidence_is_refused_before_any_read(self):
        self.activate_journal()
        code, output = self.propose()
        self.assert_refused_before_read(code, output, "CASH_FLOW_EVIDENCE_REQUIRED_AFTER_ACTIVATION")
        self.assertIn("cash_flow_evidence.py normalize", output)

    def test_t11_journal_without_activation_proposes_as_before(self):
        card, pack = make_card()
        proposal = journal_module.build_card_proposal(
            card=card, fact_pack=pack, journal=journal_module.load_journal(self.journal_path),
            now=datetime.now(timezone.utc))
        journal_module.apply_proposal(journal_path=self.journal_path, proposal=proposal, confirmation={
            "confirm_code": proposal["confirm_code"], "confirmation_method": "COWORK_CHAT_USER_MESSAGE",
            "user_message": f"확인 {proposal['confirm_code']}"})
        self.assertEqual(journal_module.load_journal(self.journal_path)["status"], "OK")
        code, output = self.propose()
        self.assertEqual((code, self.calls), (0, 1), output)
        self.assertEqual(self.latest()["status"], "USER_CONFIRMATION_REQUIRED")

    def test_t12_corrupt_or_unreadable_journal_is_refused_before_any_read(self):
        self.journal_path.write_text("{broken", encoding="utf-8")
        code, output = self.propose()
        self.assert_refused_before_read(code, output, "DECISION_JOURNAL_CORRUPT: JOURNAL_NOT_JSON")

    def test_t12_journal_view_corrupt_is_refused_even_when_load_journal_is_ok(self):
        """journal_view returns activation None for its own CORRUPT; that must never read as 'not activated'."""
        cases = (
            (fx.journal(fx.activation_entry("2026-10-01", "10000"), fx.activation_entry("2026-10-02", "10000")),
             "MULTIPLE_S5_ACTIVATION_ENTRIES"),
            (fx.journal(fx.activation_entry("2026-10-01", "0")), "S5_ACTIVATION_ENTRY_INVALID"),
        )
        for loaded, reason in cases:
            with self.subTest(reason=reason), mock.patch("portfolio_review_journal.load_journal",
                                                         return_value=loaded):
                self.assertEqual(loaded["status"], "OK")
                self.assertIsNone(journal_view(loaded)["activation"])
                code, output = self.propose()
                self.assert_refused_before_read(code, output, f"DECISION_JOURNAL_CORRUPT: {reason}")

    def test_t12_read_error_is_refused_before_any_read(self):
        with mock.patch("portfolio_review_journal.load_journal", side_effect=OSError("TEST_ONLY")):
            code, output = self.propose()
        self.assert_refused_before_read(code, output, "DECISION_JOURNAL_UNREADABLE: TEST_ONLY")

    def test_t13_activation_with_evidence_proposes_as_before(self):
        self.activate_journal()
        evidence_path = self.directory / "cash_flow_evidence.json"
        evidence_path.write_text(json.dumps(evidence([DEPOSIT, DIVIDEND]), ensure_ascii=False), encoding="utf-8")
        code, output = self.propose("--cash-flow-evidence", str(evidence_path))
        self.assertEqual((code, self.calls), (0, 1), output)
        self.assertEqual(self.latest()["cash_flow_declaration"]["declaration_status"], "UNDECLARED")

    def test_t18_missing_journal_proposes_as_before(self):
        self.assertFalse(self.journal_path.exists())
        code, output = self.propose()
        self.assertEqual((code, self.calls), (0, 1), output)
        self.assertFalse(self.journal_path.exists())


class AutoPathUnchangedTests(unittest.TestCase):
    """T14: R3 is in propose only. The auto path functions are byte-identical to the base commit."""

    FUNCTIONS = ("reconcile_auto", "cmd_auto", "previous_reconcile", "compare_reference", "_auto_stop")

    @staticmethod
    def functions(source: str) -> dict[str, str]:
        tree = ast.parse(source)
        return {node.name: ast.get_source_segment(source, node) for node in tree.body
                if isinstance(node, ast.FunctionDef)}

    def test_t14_auto_functions_are_unchanged_and_never_call_the_r3_check(self):
        current = self.functions((SCRIPTS / "reconcile_broker_state.py").read_text(encoding="utf-8"))
        for name in self.FUNCTIONS:
            self.assertNotIn("activation_evidence_rejection", current[name], name)
        if shutil.which("git") is None:
            self.skipTest("git not available")
        base = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{BASE_COMMIT}:manage-us-stock-strategy/scripts/reconcile_broker_state.py"],
            capture_output=True, check=False)
        if base.returncode != 0:
            self.skipTest("base commit not available")
        before = self.functions(base.stdout.decode("utf-8"))
        for name in self.FUNCTIONS:
            self.assertEqual(current[name], before[name], name)

    def test_t14_propose_journal_default_is_the_auto_default(self):
        commands = cli.build_parser()._subparsers._group_actions[0].choices
        defaults = {name: next(action.default for action in commands[name]._actions if action.dest == "journal")
                    for name in ("propose", "auto")}
        self.assertEqual(defaults["propose"], defaults["auto"])


# ---------------------------------------------------------------------------------------------
# R2: decision journal from the thread
# ---------------------------------------------------------------------------------------------

class JournalThreadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cowork_to_room_k3_journal_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "decision_journal.json"
        self.now = datetime.now(timezone.utc)

    def build(self, entry_type, payload, review):
        return journal_module.build_proposal(entry_type=entry_type, payload=payload, review=review,
                                             journal=journal_module.load_journal(self.path), now=self.now)

    def apply(self, proposal, message, *, method=THREAD):
        return journal_module.apply_proposal(journal_path=self.path, proposal=proposal, confirmation={
            "confirm_code": proposal["confirm_code"], "confirmation_method": method, "user_message": message})

    def activate(self):
        review = not_activated_review()
        proposal = self.build("s5_activation", journal_module.activation_payload(review), review)
        return self.apply(proposal, f"확인 {proposal['confirm_code']}", method="COWORK_CHAT_USER_MESSAGE")

    def line_proposal(self):
        review = line_scenario(["100", "80", "80", "60", "60"]).review()
        return self.build("line_review_completed",
                          journal_module.line_review_payload(review, "L1", "continue", "TEST_ONLY"), review)

    def peak_proposal(self):
        scenario = Scenario({"SOXL": 3}, "9700")
        index = scenario.sessions.index(EVAL)
        scenario.journal = fx.journal(fx.activation_entry(scenario.sessions[index - 3], "10150"))
        for offset, price in ((3, "150"), (2, "150"), (1, "104"), (0, "100")):
            scenario.closes["SOXL"][scenario.sessions[index - offset]] = price
        scenario.snapshots = [fx.snapshot(scenario.sessions[index - 3], {"SOXL": 3}, "9700"),
                              fx.snapshot(scenario.sessions[index - 1], {"SOXL": 3}, "9700")]
        review = scenario.review()
        return self.build("peak_review_card_completed", journal_module.peak_review_payload(review, "SOXL"), review)

    def verify(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = journal_module.main(["verify", "--journal", str(self.path)])
        return code, json.loads(output.getvalue())

    def test_t6_line_and_peak_review_from_the_thread_are_recorded_and_verify(self):
        self.activate()
        for proposal in (self.line_proposal(), None):
            proposal = proposal or self.peak_proposal()
            message = thread_message(f"확인 {proposal['confirm_code']}")
            entry = self.apply(proposal, message)
            self.assertEqual((entry["confirmation_method"], entry["user_message"]), (THREAD, message))
        code, report = self.verify()
        self.assertEqual((code, report["status"], report["entry_count"]), (0, "OK", 3))

    def test_t7_s5_review_entries_need_the_code_in_the_verbatim_field(self):
        self.activate()
        before = self.path.read_bytes()
        for proposal in (self.line_proposal(), self.peak_proposal()):
            with self.subTest(entry_type=proposal["entry_type"]):
                with self.assertRaisesRegex(journal_module.JournalError, "CONFIRM_CODE_NOT_IN_USER_MESSAGE"):
                    self.apply(proposal, thread_message("완료"))
                self.assertEqual(self.path.read_bytes(), before)

    def test_t7_hand_edited_s5_review_entry_without_code_is_caught_by_verify(self):
        self.activate()
        proposal = self.line_proposal()
        self.apply(proposal, thread_message(f"확인 {proposal['confirm_code']}"))
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["entries"][-1]["user_message"] = thread_message("완료")
        self.path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        loaded = journal_module.load_journal(self.path)
        self.assertEqual((loaded["status"], loaded["errors"]),
                         ("CORRUPT", ["JOURNAL_ENTRY_INCONSISTENT:2:CONFIRM_CODE_NOT_IN_USER_MESSAGE"]))
        self.assertEqual(self.verify()[1]["status"], "CORRUPT")

    def test_t8_s5_activation_is_never_a_thread_entry(self):
        review = not_activated_review()
        proposal = self.build("s5_activation", journal_module.activation_payload(review), review)
        with self.assertRaisesRegex(journal_module.JournalError, "PROJECT_THREAD_ENTRY_TYPE_INVALID"):
            self.apply(proposal, thread_message(f"확인 {proposal['confirm_code']}"))
        self.assertFalse(self.path.exists())
        # A hand-made thread activation entry (code in the verbatim field) is caught by verify.
        entry = self.activate()
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["entries"][-1].update(confirmation_method=THREAD,
                                       user_message=thread_message(f"확인 {entry['confirm_code']}"))
        self.path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        loaded = journal_module.load_journal(self.path)
        self.assertEqual((loaded["status"], loaded["errors"]),
                         ("CORRUPT", ["JOURNAL_ENTRY_INCONSISTENT:1:PROJECT_THREAD_ENTRY_TYPE_INVALID"]))
        self.assertEqual(self.verify()[1]["status"], "CORRUPT")

    def test_t8_allowed_thread_types_are_an_explicit_list_of_four(self):
        self.assertEqual(set(journal_module.PROJECT_THREAD_ENTRY_TYPES),
                         {"card_decision", "card_user_decision", "line_review_completed",
                          "peak_review_card_completed"})
        self.assertNotIn("s5_activation", journal_module.PROJECT_THREAD_ENTRY_TYPES)

    def test_t9_card_entries_from_the_thread_still_need_no_code(self):
        card, pack = make_card()
        proposal = journal_module.build_card_proposal(card=card, fact_pack=pack,
                                                      journal=journal_module.load_journal(self.path), now=self.now)
        message = thread_message("카드 탭: 기록")
        self.assertNotIn(proposal["confirm_code"], message.upper())
        self.apply(proposal, message)
        self.assertEqual(journal_module.load_journal(self.path)["status"], "OK")

    def test_t15_code_only_in_the_id_or_account_field_is_rejected(self):
        self.activate()
        proposal = self.line_proposal()
        code = proposal["confirm_code"]
        for message in (thread_message("완료", message_id=f"cmsg_{code}"),
                        thread_message("완료", account=f"user_{code}")):
            with self.subTest(message=message):
                with self.assertRaisesRegex(journal_module.JournalError, "CONFIRM_CODE_NOT_IN_USER_MESSAGE"):
                    self.apply(proposal, message)

    def test_t17_thread_review_entries_keep_the_activation(self):
        self.activate()
        before = journal_view(journal_module.load_journal(self.path))
        for build in (self.line_proposal, self.peak_proposal):
            proposal = build()
            self.apply(proposal, thread_message(f"확인 {proposal['confirm_code']}"))
        loaded = journal_module.load_journal(self.path)
        after = journal_view(loaded)
        self.assertEqual(loaded["status"], "OK")
        self.assertEqual(after["activation"], before["activation"])
        self.assertEqual(after["activation"]["activation_date"], before["activation"]["activation_date"])
        self.assertEqual((len(after["line_reviews"]), len(after["peak_reviews"])), (1, 1))


if __name__ == "__main__":
    unittest.main()
