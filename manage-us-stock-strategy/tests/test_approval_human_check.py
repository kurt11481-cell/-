"""hnd-check: a USER_TERMINAL apply needs an interactive console and the code typed once more.

reconcile_broker_state.py apply and portfolio_review_journal.py apply, run in-process with stand-in streams.
Synthetic proposals in temp folders only: the real state, ledger, journal, policy and Kiwoom are never touched.
The tools/dev-merge.ps1 side (-ApproveAuthority) is tested in test_dev_pipeline.py.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_review_journal as journal_module  # noqa: E402
import reconcile_broker_state as cli  # noqa: E402
import test_reconcile_broker_state as reconcile_fixtures  # noqa: E402
from test_portfolio_review_journal import not_activated_review  # noqa: E402
from validation_common import load_json  # noqa: E402

NOT_INTERACTIVE = "USER_TERMINAL_NOT_INTERACTIVE"
NOT_RETYPED = "USER_TERMINAL_CODE_NOT_RETYPED"
# stdin, stdout: what an agent's pipe, a redirect or a headless shell gives (at least one is not a terminal).
NOT_A_CONSOLE = ((False, False), (False, True), (True, False))


class Console(io.StringIO):
    """A stand-in stream that reports a terminal, as a person's console window does."""

    def isatty(self) -> bool:
        return True


def run_with_streams(main, argv, *, typed, stdin_tty, stdout_tty):
    """Run a CLI main with stand-in streams. typed is what is on stdin (None: nothing, as with NUL)."""
    stdin = (Console if stdin_tty else io.StringIO)("" if typed is None else typed + "\n")
    stdout = (Console if stdout_tty else io.StringIO)()
    with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
        code = main(argv)
    return code, stdout.getvalue()


class TerminalCheckTests(unittest.TestCase):
    def check(self, stdin, stdout, code="ABCD1234"):
        with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
            return journal_module.user_terminal_rejection(code)

    def test_both_streams_must_be_a_terminal(self):
        for stdin_tty, stdout_tty in NOT_A_CONSOLE:
            with self.subTest(stdin_tty=stdin_tty, stdout_tty=stdout_tty):
                stdin = (Console if stdin_tty else io.StringIO)("ABCD1234\n")  # piping the right code does not help
                stdout = (Console if stdout_tty else io.StringIO)()
                self.assertEqual(self.check(stdin, stdout), NOT_INTERACTIVE)
                self.assertEqual((stdin.tell(), stdout.getvalue()), (0, ""))  # refused before any prompt or read

    def test_missing_closed_or_unclear_streams_are_not_a_terminal(self):
        closed = io.StringIO()
        closed.close()
        for stream in (None, closed, mock.MagicMock()):  # MagicMock().isatty() returns a mock, not True
            with self.subTest(stream=stream):
                self.assertEqual(self.check(stream, Console()), NOT_INTERACTIVE)
                self.assertEqual(self.check(Console("ABCD1234\n"), stream), NOT_INTERACTIVE)

    def test_the_code_is_typed_once_more(self):
        # "" is the end of input: NUL, which Windows reports as a terminal, gives nothing to read.
        for typed, expected in (("ABCD1234\n", None), ("  abcd1234  \n", None), ("ABCD1235\n", NOT_RETYPED),
                                ("\n", NOT_RETYPED), ("", NOT_RETYPED)):
            with self.subTest(typed=typed):
                stdout = Console()
                self.assertEqual(self.check(Console(typed), stdout, code=" abcd1234 "), expected)
                self.assertEqual(stdout.getvalue(), journal_module.TERMINAL_RETYPE_PROMPT)

    def test_no_bypass_input_in_the_check(self):
        source = inspect.getsource(journal_module.user_terminal_rejection)
        for word in ("environ", "getenv", "argv", "skip", "bypass"):
            self.assertNotIn(word, source.lower())
        self.assertEqual(list(inspect.signature(journal_module.user_terminal_rejection).parameters),
                         ["confirm_code", "prompt"])


class ReconcileApplyTests(reconcile_fixtures.TempStateCase):
    def setUp(self):
        super().setUp()
        runtime = self.directory / "runtime"
        runtime.mkdir()
        self.output_root = self.directory / "outputs"
        policies = {}
        for name, value in (("readonly", {"official_runtime_path": str(runtime)}), ("rate", {}),
                            ("broker", {"maximum_age_seconds": 900}),
                            ("alert", {"daily_engine_scope": "TEST_ONLY_NOT_LEVERAGED"})):
            policies[name] = self.directory / f"{name}.json"
            policies[name].write_text(json.dumps(value), encoding="utf-8")
        self.original = self.write_state(reconcile_fixtures.base_state())
        retrieved_at = reconcile_fixtures.utc(datetime.now(timezone.utc))
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(["propose", "--readonly-policy", str(policies["readonly"]),
                             "--rate-policy", str(policies["rate"]), "--broker-policy", str(policies["broker"]),
                             "--alert-policy", str(policies["alert"]), "--portfolio-state", str(self.state_path),
                             "--output-root", str(self.output_root)],
                            reader=lambda requests, **kwargs: reconcile_fixtures.account_results(retrieved_at))
        self.assertEqual(code, 0)
        self.code = load_json(cli.resolve_proposal_path("latest", self.output_root))["confirm_code"]
        self.messages = cli._messages()

    def apply(self, *extra, typed=None, stdin_tty=True, stdout_tty=True):
        argv = ["apply", "--output-root", str(self.output_root), "--portfolio-state", str(self.state_path), *extra]
        return run_with_streams(cli.main, argv, typed=typed, stdin_tty=stdin_tty, stdout_tty=stdout_tty)

    def terminal(self, confirm=None, **kwargs):
        return self.apply("--confirm", self.code if confirm is None else confirm, "--confirmed-via", "USER_TERMINAL",
                          **kwargs)

    def assert_unchanged(self):
        self.assert_nothing_written(self.original)
        self.assertEqual(list(self.output_root.glob("*/apply_audit.*.json")), [])

    def ledger_entry(self):
        return json.loads((self.directory / "reconciliation_ledger.jsonl").read_text(encoding="utf-8"))

    def test_terminal_apply_without_a_console_is_refused(self):
        for stdin_tty, stdout_tty in NOT_A_CONSOLE:
            with self.subTest(stdin_tty=stdin_tty, stdout_tty=stdout_tty):
                code, output = self.terminal(typed=self.code, stdin_tty=stdin_tty, stdout_tty=stdout_tty)
                self.assertEqual((code, output.strip()), (2, self.messages["apply_terminal_not_interactive"]))
                self.assert_unchanged()

    def test_refused_before_the_proposal_is_read(self):
        code, output = self.apply("--confirm", self.code, "--confirmed-via", "USER_TERMINAL",
                                  "--proposal", str(self.directory / "missing.json"), stdin_tty=False)
        self.assertEqual((code, output.strip()), (2, self.messages["apply_terminal_not_interactive"]))

    def test_console_apply_needs_the_same_code_again(self):
        for typed in ("00000000", "", None):  # wrong code, empty line, end of input
            with self.subTest(typed=typed):
                code, output = self.terminal(typed=typed)
                self.assertEqual(code, 2)
                self.assertIn(self.messages["apply_terminal_retype"], output)
                self.assertIn(self.messages["apply_rejected"].format(reason=NOT_RETYPED), output)
                self.assert_unchanged()

    def test_retyping_never_replaces_the_code_check(self):
        code, output = self.terminal(confirm="00000000", typed="00000000")
        self.assertEqual(code, 2)
        self.assertIn("CONFIRM_CODE_MISMATCH", output)
        self.assert_unchanged()

    def test_console_apply_with_the_code_typed_again_applies(self):
        code, output = self.terminal(typed=" " + self.code.lower() + " ")
        self.assertEqual(code, 0, output)
        self.assertIn(self.messages["apply_terminal_retype"], output)
        self.assertEqual(load_json(self.state_path)["state_revision"], 8)
        entry = self.ledger_entry()
        self.assertEqual((entry["confirmation_method"], entry["confirm_code"]), ("USER_TERMINAL", self.code))

    def test_cowork_path_is_unchanged_without_a_console(self):
        with mock.patch.object(journal_module, "user_terminal_rejection", side_effect=AssertionError("called")):
            code, output = self.apply("--confirm", self.code, "--confirmed-via", "COWORK_CHAT_USER_MESSAGE",
                                      "--user-message", f"확인 {self.code}", stdin_tty=False, stdout_tty=False)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.ledger_entry()["confirmation_method"], "COWORK_CHAT_USER_MESSAGE")

    def test_cowork_path_still_needs_the_user_message(self):
        code, output = self.apply("--confirm", self.code, "--confirmed-via", "COWORK_CHAT_USER_MESSAGE",
                                  stdin_tty=False, stdout_tty=False)
        self.assertEqual((code, output.strip()), (2, self.messages["apply_user_message_required"]))
        self.assert_unchanged()


class JournalApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hnd_check_journal_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "decision_journal.json"
        review_path = self.tmp / "review.json"
        review_path.write_text(json.dumps(not_activated_review()), encoding="utf-8")
        output_root = self.tmp / "proposals"
        with contextlib.redirect_stdout(io.StringIO()):
            code = journal_module.main(["propose-activation", "--review", str(review_path), "--journal",
                                        str(self.path), "--output-root", str(output_root)])
        self.assertEqual(code, 0)
        self.proposal = next(output_root.glob("*/journal_proposal.json"))
        self.code = load_json(self.proposal)["confirm_code"]
        self.messages = journal_module._messages()

    def apply(self, *extra, typed=None, stdin_tty=True, stdout_tty=True):
        argv = ["apply", "--proposal", str(self.proposal), "--journal", str(self.path), *extra]
        return run_with_streams(journal_module.main, argv, typed=typed, stdin_tty=stdin_tty, stdout_tty=stdout_tty)

    def terminal(self, **kwargs):
        return self.apply("--confirm", self.code, "--confirmed-via", "USER_TERMINAL", **kwargs)

    def cowork(self, **kwargs):
        return self.apply("--confirm", self.code, "--confirmed-via", "COWORK_CHAT_USER_MESSAGE",
                          "--user-message", f"확인 {self.code}", **kwargs)

    def rejected(self, reason):
        return self.messages["journal_apply_rejected"].format(reason=reason)

    def test_terminal_apply_without_a_console_is_refused(self):
        for stdin_tty, stdout_tty in NOT_A_CONSOLE:
            with self.subTest(stdin_tty=stdin_tty, stdout_tty=stdout_tty):
                code, output = self.terminal(typed=self.code, stdin_tty=stdin_tty, stdout_tty=stdout_tty)
                self.assertEqual((code, output.strip(), self.path.exists()), (2, self.rejected(NOT_INTERACTIVE), False))

    def test_an_existing_journal_stays_byte_identical(self):
        self.assertEqual(self.cowork(stdin_tty=False, stdout_tty=False)[0], 0)
        before = self.path.read_bytes()
        for typed, stdin_tty, reason in ((self.code, False, NOT_INTERACTIVE), ("00000000", True, NOT_RETYPED)):
            with self.subTest(reason=reason):
                code, output = self.terminal(typed=typed, stdin_tty=stdin_tty)
                self.assertEqual(code, 2)
                self.assertIn(self.rejected(reason), output)  # refused by the new check, before the library runs
                self.assertEqual(self.path.read_bytes(), before)

    def test_console_apply_needs_the_same_code_again(self):
        for typed in ("00000000", "", None):
            with self.subTest(typed=typed):
                code, output = self.terminal(typed=typed)
                self.assertEqual(code, 2)
                self.assertIn(journal_module.TERMINAL_RETYPE_PROMPT, output)
                self.assertIn(self.rejected(NOT_RETYPED), output)
                self.assertFalse(self.path.exists())

    def test_console_apply_with_the_code_typed_again_records(self):
        code, output = self.terminal(typed=self.code.lower())
        self.assertEqual(code, 0, output)
        entries = journal_module.load_journal(self.path)["entries"]
        self.assertEqual([entry["confirmation_method"] for entry in entries], ["USER_TERMINAL"])

    def test_cowork_path_is_unchanged_without_a_console(self):
        with mock.patch.object(journal_module, "user_terminal_rejection", side_effect=AssertionError("called")):
            code, output = self.cowork(stdin_tty=False, stdout_tty=False)
        self.assertEqual(code, 0, output)
        entries = journal_module.load_journal(self.path)["entries"]
        self.assertEqual([entry["confirmation_method"] for entry in entries], ["COWORK_CHAT_USER_MESSAGE"])


if __name__ == "__main__":
    unittest.main()
