"""hnd-check / hnd-check2: a USER_TERMINAL apply needs an interactive console and one Enter; the code is not typed.

stdin and stdout must be a terminal (isatty) and, on Windows, console handles (GetConsoleMode), so NUL, which
Windows reports as a terminal, is refused as well. Then Enter is pressed once (hnd-check2 fix 1): what is typed is
not compared and the end of input is refused. reconcile_broker_state.py apply and portfolio_review_journal.py
apply run in-process with stand-in streams, and in child processes whose standard handles really are NUL, a pipe
or a file. Synthetic proposals in temp folders only: the real state, ledger, journal, policy and Kiwoom are never
touched. The tools/dev-merge.ps1 side (-ApproveAuthority) is tested in test_dev_pipeline.py.
"""

from __future__ import annotations

import contextlib
import ctypes
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_review_journal as journal_module  # noqa: E402
import reconcile_broker_state as cli  # noqa: E402
import test_reconcile_broker_state as reconcile_fixtures  # noqa: E402
from test_portfolio_review_journal import not_activated_review  # noqa: E402
from validation_common import load_json  # noqa: E402

NOT_INTERACTIVE = "USER_TERMINAL_NOT_INTERACTIVE"
ENTER = journal_module.TERMINAL_ENTER_PROMPT  # hnd-check2 fix 1: shown once, after the console checks
HANDLE_CHECK = journal_module.standard_handles_are_console  # the real function (in-process tests patch it)
# stdin, stdout: what an agent's pipe, a redirect or a headless shell gives (at least one is not a terminal).
NOT_A_CONSOLE = ((False, False), (False, True), (True, False))
ON_WINDOWS = os.name == "nt"
# A child process that reports what the check sees through its real standard handles.
CHILD_CHECK = """import json, sys
sys.path.insert(0, sys.argv[1])
import portfolio_review_journal as journal
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump({"isatty": [sys.stdin.isatty(), sys.stdout.isatty()],
               "handles": journal.standard_handles_are_console(),
               "rejection": journal.user_terminal_rejection()}, handle)
"""


class Console(io.StringIO):
    """A stand-in stream that reports a terminal, as a person's console window does."""

    def isatty(self) -> bool:
        return True


def run_with_streams(main, argv, *, typed, stdin_tty, stdout_tty):
    """Run a CLI main with stand-in streams. typed is what is on stdin (None: nothing)."""
    stdin = (Console if stdin_tty else io.StringIO)("" if typed is None else typed + "\n")
    stdout = (Console if stdout_tty else io.StringIO)()
    with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
        code = main(argv)
    return code, stdout.getvalue()


def run_child(argv, *, stdin, stdout):
    """Run a real Python child process with the given standard handles (stderr captured)."""
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")  # stdout may be a file or NUL: no console encoding
    return subprocess.run([sys.executable, *argv], stdin=stdin, stdout=stdout, stderr=subprocess.PIPE,
                          env=environment, timeout=120)


def assume_console_handles(case):
    """In-process runs have no console of their own: the GetConsoleMode check passes unless a test says so."""
    handles = mock.patch.object(journal_module, "standard_handles_are_console", return_value=True)
    case.addCleanup(handles.stop)
    return handles.start()


class FakeKernel32:
    """Stands in for kernel32: GetStdHandle gives the id itself as the handle, GetConsoleMode answers per id."""

    def __init__(self, answers):
        self.asked = []

        def get_console_mode(handle, mode):
            self.asked.append(handle)
            answer = answers[handle]
            if isinstance(answer, Exception):
                raise answer
            return answer

        self.GetStdHandle = lambda which: which
        self.GetConsoleMode = get_console_mode


class TerminalCheckTests(unittest.TestCase):
    def setUp(self):
        self.handles = assume_console_handles(self)

    def check(self, stdin, stdout):
        with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
            return journal_module.user_terminal_rejection()

    def test_both_streams_must_be_a_terminal(self):
        for stdin_tty, stdout_tty in NOT_A_CONSOLE:
            with self.subTest(stdin_tty=stdin_tty, stdout_tty=stdout_tty):
                stdin = (Console if stdin_tty else io.StringIO)("ABCD1234\n")  # piping the right code does not help
                stdout = (Console if stdout_tty else io.StringIO)()
                self.assertEqual(self.check(stdin, stdout), NOT_INTERACTIVE)
                self.assertEqual((stdin.tell(), stdout.getvalue()), (0, ""))  # refused before any prompt or read
        self.handles.assert_not_called()  # isatty refuses first, as before hnd-check2

    def test_missing_closed_or_unclear_streams_are_not_a_terminal(self):
        closed = io.StringIO()
        closed.close()
        for stream in (None, closed, mock.MagicMock()):  # MagicMock().isatty() returns a mock, not True
            with self.subTest(stream=stream):
                self.assertEqual(self.check(stream, Console()), NOT_INTERACTIVE)
                self.assertEqual(self.check(Console("ABCD1234\n"), stream), NOT_INTERACTIVE)

    def test_a_console_goes_on_after_one_enter_whatever_is_typed(self):
        # hnd-check2 fix 1 (was test_a_console_goes_on_without_reading_anything, before that
        # test_the_code_is_typed_once_more): after the console checks the prompt is shown once and one line is
        # read, Enter alone or any text, never compared with anything. Only that one line is read.
        self.assertEqual(ENTER, "Press Enter to apply (Ctrl+C cancels): ")
        for typed in ("\n", "ABCD1234\n", "00000000\n", "anything at all\n", "first\nsecond\n"):
            with self.subTest(typed=typed):
                stdin, stdout = Console(typed), Console()
                self.assertIsNone(self.check(stdin, stdout))
                self.assertEqual((stdin.tell(), stdout.getvalue()), (typed.index("\n") + 1, ENTER))
        self.assertEqual(self.handles.call_count, 5)

    def test_the_end_of_input_is_refused(self):
        # hnd-check2 fix 1: the console checks pass, as in a new console window (hidden or not), but nobody
        # presses Enter and the input ends: refused as not interactive.
        stdin, stdout = Console(""), Console()
        self.assertEqual(self.check(stdin, stdout), NOT_INTERACTIVE)
        self.assertEqual(stdout.getvalue(), ENTER)  # asked once
        with mock.patch("builtins.input", side_effect=EOFError) as asked:
            self.assertEqual(self.check(Console("\n"), Console()), NOT_INTERACTIVE)
        asked.assert_called_once_with(ENTER)

    def test_ctrl_c_at_the_enter_step_is_left_alone(self):
        # hnd-check2 fix 1: Ctrl+C stops the run as Python does; the check does not catch it.
        with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.check(Console("\n"), Console())

    def test_terminal_streams_without_console_handles_are_refused(self):
        # hnd-check2: isatty says terminal for both streams (as Windows does for NUL), but the standard handles
        # are not console handles. Only True goes on.
        for answer in (False, None, 1, "True", mock.MagicMock()):
            with self.subTest(answer=answer):
                self.handles.return_value = answer
                stdin, stdout = Console("ABCD1234\n"), Console()
                self.assertEqual(self.check(stdin, stdout), NOT_INTERACTIVE)
                self.assertEqual((stdin.tell(), stdout.getvalue()), (0, ""))

    def test_no_bypass_input_in_the_check(self):
        for function in (journal_module.user_terminal_rejection, HANDLE_CHECK):
            with self.subTest(function=function.__name__):
                source = inspect.getsource(function)
                for word in ("environ", "getenv", "argv", "skip", "bypass"):
                    self.assertNotIn(word, source.lower())
                self.assertEqual(list(inspect.signature(function).parameters), [])
        # hnd-check2 fix 1: the one Enter is the only read, after the console checks, and its line is never
        # kept, so nothing can be compared with it. The handle check reads nothing.
        self.assertNotIn("input(", inspect.getsource(HANDLE_CHECK))
        source = inspect.getsource(journal_module.user_terminal_rejection)
        self.assertEqual(source.count("input("), 1)
        self.assertRegex(source, r"(?m)^        input\(TERMINAL_ENTER_PROMPT\)\r?$")
        self.assertNotRegex(source, r"=\s*input\(")
        self.assertLess(source.index("standard_handles_are_console() is not True"),
                        source.index("input(TERMINAL_ENTER_PROMPT)"))


class ConsoleHandleTests(unittest.TestCase):
    """hnd-check2: standard_handles_are_console itself, with a stand-in kernel32."""

    IN, OUT = journal_module.STD_INPUT_HANDLE, journal_module.STD_OUTPUT_HANDLE

    def ask(self, answers):
        fake = FakeKernel32(answers)
        with mock.patch("ctypes.WinDLL", return_value=fake) as dll:
            result = journal_module.standard_handles_are_console()
        dll.assert_called_once_with("kernel32", use_last_error=True)
        return result, fake.asked

    @unittest.skipUnless(ON_WINDOWS, "the GetConsoleMode check runs on Windows only")
    def test_both_standard_handles_must_be_console_handles(self):
        self.assertEqual((self.IN, self.OUT), (0xFFFFFFF6, 0xFFFFFFF5))  # (DWORD)-10 and (DWORD)-11
        self.assertEqual(self.ask({self.IN: 1, self.OUT: 1}), (True, [self.IN, self.OUT]))
        for answers in ({self.IN: 0, self.OUT: 1}, {self.IN: 1, self.OUT: 0}, {self.IN: 0, self.OUT: 0}):
            with self.subTest(answers=answers):
                self.assertIs(self.ask(answers)[0], False)  # NUL, a pipe or a file on either side

    @unittest.skipUnless(ON_WINDOWS, "the GetConsoleMode check runs on Windows only")
    def test_an_error_or_an_unclear_answer_is_refused(self):
        for answer in (OSError("closed"), ctypes.ArgumentError("bad"), TypeError("odd"), None, "1",
                       mock.MagicMock()):
            with self.subTest(answer=answer):
                self.assertIs(self.ask({self.IN: 1, self.OUT: answer})[0], False)
        with mock.patch("ctypes.WinDLL", side_effect=OSError("no kernel32")):
            self.assertIs(journal_module.standard_handles_are_console(), False)

    def test_off_windows_isatty_is_the_whole_check(self):
        with mock.patch.object(journal_module, "os", types.SimpleNamespace(name="posix")), \
                mock.patch("ctypes.WinDLL", side_effect=AssertionError("called"), create=True):
            self.assertIs(journal_module.standard_handles_are_console(), True)


@unittest.skipUnless(ON_WINDOWS, "real Windows standard handles")
class RealHandleTests(unittest.TestCase):
    """hnd-check2: a child process whose standard handles really are NUL, a pipe or a file (no stand-ins)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hnd_check2_handles_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def seen(self, stdin, stdout):
        out = self.tmp / "seen.json"
        out.unlink(missing_ok=True)
        result = run_child(["-c", CHILD_CHECK, str(SCRIPTS), str(out)], stdin=stdin, stdout=stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_nul_looks_like_a_terminal_but_is_refused(self):
        # The hole hnd-check2 closes: isatty is True for NUL on Windows; GetConsoleMode fails on it.
        self.assertEqual(self.seen(subprocess.DEVNULL, subprocess.DEVNULL),
                         {"isatty": [True, True], "handles": False, "rejection": NOT_INTERACTIVE})

    def test_pipes_files_and_half_nul_are_refused(self):
        (self.tmp / "in.txt").write_bytes(b"ABCD1234\r\n")
        with (self.tmp / "in.txt").open("rb") as file_in, (self.tmp / "out.txt").open("wb") as file_out:
            for name, stdin, stdout in (("NUL in, pipe out", subprocess.DEVNULL, subprocess.PIPE),
                                        ("pipe in, NUL out", subprocess.PIPE, subprocess.DEVNULL),
                                        ("file in, file out", file_in, file_out)):
                with self.subTest(name):
                    seen = self.seen(stdin, stdout)
                    self.assertEqual((seen["handles"], seen["rejection"]), (False, NOT_INTERACTIVE))


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
        self.handles = assume_console_handles(self)

    def apply(self, *extra, typed=None, stdin_tty=True, stdout_tty=True):
        argv = ["apply", "--output-root", str(self.output_root), "--portfolio-state", str(self.state_path), *extra]
        return run_with_streams(cli.main, argv, typed=typed, stdin_tty=stdin_tty, stdout_tty=stdout_tty)

    def apply_argv(self):
        return [str(SCRIPTS / "reconcile_broker_state.py"), "apply", "--output-root", str(self.output_root),
                "--portfolio-state", str(self.state_path), "--confirm", self.code, "--confirmed-via", "USER_TERMINAL"]

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
        # no terminal; a terminal without console handles; a console whose input ends at the Enter step (fix 1)
        for handles, stdin_tty, asked in ((True, False, ""), (False, True, ""), (True, True, ENTER)):
            with self.subTest(handles=handles, stdin_tty=stdin_tty):
                self.handles.return_value = handles
                code, output = self.apply("--confirm", self.code, "--confirmed-via", "USER_TERMINAL",
                                          "--proposal", str(self.directory / "missing.json"), stdin_tty=stdin_tty)
                self.assertEqual((code, output), (2, asked + self.messages["apply_terminal_not_interactive"] + "\n"))

    def test_console_handles_are_needed_too(self):
        # hnd-check2 (was test_console_apply_needs_the_same_code_again): both streams report a terminal, as NUL
        # does on Windows, but the standard handles are not console handles.
        self.handles.return_value = False
        for typed in (self.code, None):  # the right code on stdin, or nothing
            with self.subTest(typed=typed):
                code, output = self.terminal(typed=typed)
                self.assertEqual((code, output.strip()), (2, self.messages["apply_terminal_not_interactive"]))
                self.assert_unchanged()

    @unittest.skipUnless(ON_WINDOWS, "real Windows standard handles")
    def test_terminal_apply_with_nul_is_refused_end_to_end(self):
        # hnd-check2: a real child process with NUL as stdin and stdout (no stand-ins, no patches).
        result = run_child(self.apply_argv(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        self.assertEqual((result.returncode, result.stderr), (2, b""))
        self.assert_unchanged()

    def test_the_console_check_never_replaces_the_code_check(self):
        # was test_retyping_never_replaces_the_code_check. hnd-check2 fix 1: Enter, or even the right code typed
        # at the Enter step, does not stand in for a wrong --confirm.
        for typed in ("", self.code):
            with self.subTest(typed=typed):
                code, output = self.terminal(confirm="00000000", typed=typed)
                self.assertEqual(code, 2)
                self.assertIn("CONFIRM_CODE_MISMATCH", output)
                self.assert_unchanged()

    def test_console_apply_goes_on_after_one_enter(self):
        # hnd-check2 fix 1 (was test_console_apply_goes_on_without_typing_the_code, before that
        # test_console_apply_with_the_code_typed_again_applies): Enter alone applies; the code is not typed.
        with mock.patch("builtins.input", wraps=input) as asked:
            code, output = self.terminal(typed="")
        self.assertEqual(code, 0, output)
        asked.assert_called_once_with(ENTER)
        self.assertTrue(output.startswith(ENTER + self.messages["apply_success"].format(before=7, after=8, backup="")),
                        output)
        self.assertEqual(load_json(self.state_path)["state_revision"], 8)
        entry = self.ledger_entry()
        self.assertEqual((entry["confirmation_method"], entry["confirm_code"]), ("USER_TERMINAL", self.code))
        self.handles.assert_called_once_with()

    def test_console_apply_without_an_enter_is_refused(self):
        # hnd-check2 fix 1: the console checks pass, as in a new console window (hidden or not), but the input
        # ends instead of Enter: refused before the proposal is read; state and audit untouched.
        code, output = self.terminal(typed=None)
        self.assertEqual((code, output), (2, ENTER + self.messages["apply_terminal_not_interactive"] + "\n"))
        self.assert_unchanged()

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
        self.handles = assume_console_handles(self)

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
        # no terminal; a terminal without console handles (hnd-check2, was the code typed wrong); a console whose
        # input ends at the Enter step (hnd-check2 fix 1)
        for handles, stdin_tty, typed in ((True, False, self.code), (False, True, self.code), (True, True, None)):
            with self.subTest(handles=handles, stdin_tty=stdin_tty, typed=typed):
                self.handles.return_value = handles
                code, output = self.terminal(typed=typed, stdin_tty=stdin_tty)
                self.assertEqual(code, 2)
                self.assertIn(self.rejected(NOT_INTERACTIVE), output)  # refused by the check, before the library
                self.assertEqual(self.path.read_bytes(), before)

    def test_console_handles_are_needed_too(self):
        # hnd-check2 (was test_console_apply_needs_the_same_code_again): both streams report a terminal, as NUL
        # does on Windows, but the standard handles are not console handles.
        self.handles.return_value = False
        for typed in (self.code, None):
            with self.subTest(typed=typed):
                code, output = self.terminal(typed=typed)
                self.assertEqual((code, output.strip(), self.path.exists()), (2, self.rejected(NOT_INTERACTIVE), False))

    @unittest.skipUnless(ON_WINDOWS, "real Windows standard handles")
    def test_terminal_apply_with_nul_is_refused_end_to_end(self):
        # hnd-check2: a real child process with NUL as stdin and stdout (no stand-ins, no patches).
        result = run_child([str(SCRIPTS / "portfolio_review_journal.py"), "apply", "--proposal", str(self.proposal),
                            "--journal", str(self.path), "--confirm", self.code, "--confirmed-via", "USER_TERMINAL"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        self.assertEqual((result.returncode, result.stderr, self.path.exists()), (2, b"", False))

    def test_console_apply_records_after_one_enter(self):
        # hnd-check2 fix 1 (was test_console_apply_records_without_typing_the_code, before that
        # test_console_apply_with_the_code_typed_again_records): any text and Enter goes on; it is not recorded.
        with mock.patch("builtins.input", wraps=input) as asked:
            code, output = self.terminal(typed="anything at all")
        self.assertEqual(code, 0, output)
        asked.assert_called_once_with(ENTER)
        self.assertTrue(output.startswith(ENTER), output)
        entries = journal_module.load_journal(self.path)["entries"]
        self.assertEqual([entry["confirmation_method"] for entry in entries], ["USER_TERMINAL"])
        self.assertEqual(entries[0]["confirm_code"], self.code)
        self.assertNotIn("anything at all", self.path.read_text(encoding="utf-8"))
        self.handles.assert_called_once_with()

    def test_console_apply_without_an_enter_is_refused(self):
        # hnd-check2 fix 1: the console checks pass, as in a new console window (hidden or not), but the input
        # ends instead of Enter: refused before the proposal is read; no journal.
        code, output = self.terminal(typed=None)
        self.assertEqual((code, output, self.path.exists()), (2, ENTER + self.rejected(NOT_INTERACTIVE) + "\n", False))

    def test_cowork_path_is_unchanged_without_a_console(self):
        with mock.patch.object(journal_module, "user_terminal_rejection", side_effect=AssertionError("called")):
            code, output = self.cowork(stdin_tty=False, stdout_tty=False)
        self.assertEqual(code, 0, output)
        entries = journal_module.load_journal(self.path)["entries"]
        self.assertEqual([entry["confirmation_method"] for entry in entries], ["COWORK_CHAT_USER_MESSAGE"])


if __name__ == "__main__":
    unittest.main()
