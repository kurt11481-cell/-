"""Static checks of the API pilot task scripts, plus runs of a COPY of the wrapper (Windows only).

The repository wrapper, registration script and runner are never executed: the PowerShell half copies the wrapper
into a temporary repository next to a fake llm_runner.py. Every run puts a fake key into the process settings, so
the wrapper never reads a user-scope value. File text is compared with CRLF turned into LF first.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy" / "scripts"
RUN = SCRIPTS / "run_llm_pilots.ps1"
REGISTER = SCRIPTS / "register_llm_pilots_task.ps1"
KEY_NAME = "INVESTV2_ANTHROPIC_API_KEY"
FAKE_KEY = "fake-key-FOR-TEST-7Q9Z"
MODE_VARIABLE = "FAKE_RUNNER_MODE"

KEY_BLOCK = (
    "if ([string]::IsNullOrEmpty($env:INVESTV2_ANTHROPIC_API_KEY)) {",
    "$userValue = [Environment]::GetEnvironmentVariable('INVESTV2_ANTHROPIC_API_KEY', 'User')",
    "if (-not [string]::IsNullOrEmpty($userValue)) { $env:INVESTV2_ANTHROPIC_API_KEY = $userValue }",
    "$userValue = $null",
    "}",
    '$keyPresent = if ([string]::IsNullOrEmpty($env:INVESTV2_ANTHROPIC_API_KEY)) { "NO" } else { "YES" }',
)

# The fake runner records its arguments and whether the key is present (YES/NO only, never the value) and ends
# with the exit code the mode says.
FAKE_RUNNER = '''import os
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[2]
present = "YES" if os.environ.get("INVESTV2_ANTHROPIC_API_KEY") else "NO"
root.joinpath("fake-runner.txt").write_text(
    "argv=" + " ".join(sys.argv[1:]) + "\\nkey=" + present + "\\n", encoding="ascii")
print("llm-runner fake")
sys.exit(int(os.environ.get("FAKE_RUNNER_MODE", "0")))
'''


def text(path: Path) -> str:
    return path.read_bytes().replace(b"\r\n", b"\n").decode("ascii")


class ScriptTextTests(unittest.TestCase):
    def test_both_scripts_are_ascii_advanced_scripts(self) -> None:
        for path in (RUN, REGISTER):
            with self.subTest(script=path.name):
                raw = path.read_bytes().replace(b"\r\n", b"\n")
                self.assertTrue(all(byte < 128 for byte in raw), "new .ps1 files are ASCII only")
                self.assertIn("[CmdletBinding()]", text(path))

    def test_register_script_handles_one_ten_minute_task(self) -> None:
        content = text(REGISTER)
        for required in ("InvestmentV2-LLMPilots", "-Daily", '"00:00"',
                         "-RepetitionInterval (New-TimeSpan -Minutes 10)",
                         "-RepetitionDuration (New-TimeSpan -Days 1)", "PlanOnly", "Interactive",
                         "WakeToRun:$false", "IgnoreNew", "Korea Standard Time", "StartWhenAvailable",
                         "LimitMinutes = 30", "-Force", "run_llm_pilots.ps1",
                         "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File",
                         "Investment_V2 API pilots runner every 10 minutes (display only, writes "
                         "workspace\\outputs\\llm only, no order authority)",
                         '"Daily 00:00 local (KST), repeat every 10 minutes for 1 day"',
                         '$trigger = New-ScheduledTaskTrigger -Daily -At "00:00"',
                         '$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval '
                         '(New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 1)).Repetition'):
            with self.subTest(required=required):
                self.assertIn(required, content)
        self.assertEqual(set(re.findall(r"InvestmentV2-[A-Za-z0-9]+", content)), {"InvestmentV2-LLMPilots"})
        self.assertEqual(content.count("Register-ScheduledTask"), 1)
        for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"):
            with self.subTest(weekday=weekday):
                self.assertNotIn(weekday, content)
        # -PlanOnly prints the plan and exits before anything is registered.
        self.assertLess(content.index("if ($PlanOnly)"), content.index("Register-ScheduledTask"))
        plan_block = content[content.index("if ($PlanOnly)"):content.index("if (-not $timezoneReady)")]
        self.assertIn("exit 0", plan_block)
        self.assertIn("APPLY_BLOCKED_TIMEZONE", content)
        for forbidden in ("Unregister-ScheduledTask", "Set-ScheduledTask", "Start-ScheduledTask"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_wrapper_hands_over_the_key_without_writing_it(self) -> None:
        content = text(RUN)
        for required in ("llm_runner.py", "workspace\\outputs\\llm\\runner\\logs", "RUNNER_START", "RUNNER_END",
                         "RUNNER_FAIL RUNNER_EXCEPTION", "exit 4", "PYTHONUTF8", "key_present=",
                         "RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND", "RUNNER_FAIL RUNNER_SCRIPT_NOT_FOUND"):
            with self.subTest(required=required):
                self.assertIn(required, content)
        stripped = [line.strip() for line in content.splitlines()]
        for line in KEY_BLOCK:
            with self.subTest(block_line=line):
                self.assertIn(line, stripped)
        self.assertLess(content.index("[string]::IsNullOrEmpty($env:" + KEY_NAME + ")"),
                        content.index("GetEnvironmentVariable"))
        self.assertEqual([line for line in stripped if "$userValue" in line], list(KEY_BLOCK[1:4]))
        for line in content.splitlines():
            if KEY_NAME in line:
                for writer in ("Write-", "Add-Content", "Out-File", "Set-Content"):
                    with self.subTest(line=line, writer=writer):
                        self.assertNotIn(writer, line)
        lowered = content.lower()
        for forbidden in ("Invoke-WebRequest", "Invoke-RestMethod", "kiwoom", "Remove-Item", "Start-Sleep",
                          "Start-Transcript"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.lower(), lowered)

    def test_no_state_policy_or_ledger_path_in_either_script(self) -> None:
        for path in (RUN, REGISTER):
            content = text(path)
            for forbidden in ("stock-strategy-system", "workspace\\policies", "workspace/policies",
                              "decision_journal.json"):
                with self.subTest(script=path.name, forbidden=forbidden):
                    self.assertNotIn(forbidden, content)


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell is not available")
class WrapperCopyBehaviourTests(unittest.TestCase):
    """Runs a copy of the wrapper in a temporary repository whose runner is a fake."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name).resolve()
        scripts = self.root / "manage-us-stock-strategy" / "scripts"
        scripts.mkdir(parents=True)
        self.wrapper = scripts / "run_llm_pilots.ps1"
        shutil.copyfile(RUN, self.wrapper)
        self.fake = scripts / "llm_runner.py"
        self.fake.write_text(FAKE_RUNNER, encoding="ascii")
        self.logs = self.root / "workspace" / "outputs" / "llm" / "runner" / "logs"

    def tearDown(self):
        self._temporary.cleanup()

    def run_copy(self, mode: str) -> subprocess.CompletedProcess:
        # Only the copy under the temporary folder may run; the repository files never do.
        for path in (self.wrapper, self.fake):
            self.assertTrue(path.resolve().is_relative_to(self.root), path)
            self.assertFalse(path.resolve().is_relative_to(ROOT.resolve()), path)
        self.assertNotEqual(self.wrapper.resolve(), RUN.resolve())
        settings = dict(os.environ)
        settings[MODE_VARIABLE] = mode
        settings[KEY_NAME] = FAKE_KEY
        return subprocess.run(
            [shutil.which("powershell.exe"), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(self.wrapper), "-RepositoryRoot", str(self.root), "-PythonPath", sys.executable],
            cwd=str(self.root), env=settings, capture_output=True, timeout=180,
        )

    def log_text(self) -> str:
        logs = sorted(self.logs.glob("*.log"))
        self.assertEqual(len(logs), 1, logs)
        self.assertRegex(logs[0].name, r"^[0-9]{8}\.log$")
        return logs[0].read_text(encoding="utf-8", errors="replace")

    def assert_no_key_anywhere(self, result):
        needle = FAKE_KEY.encode("ascii")
        self.assertNotIn(needle, result.stdout)
        self.assertNotIn(needle, result.stderr)
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(needle, path.read_bytes(), path)

    def test_1_normal_run(self):
        result = self.run_copy("0")
        detail = (result.stdout, result.stderr)
        self.assertEqual(result.returncode, 0, detail)
        fake_out = (self.root / "fake-runner.txt").read_text(encoding="ascii")
        self.assertEqual(fake_out, "argv=\nkey=YES\n")
        log = self.log_text()
        self.assertRegex(log, r"RUNNER_START local=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2} "
                              r"timezone=\S.* key_present=YES")
        self.assertIn("llm-runner fake", log)
        self.assertIn("RUNNER_END exit=0", log)
        self.assertNotIn("RUNNER_FAIL", log)
        self.assert_no_key_anywhere(result)

    def test_2_runner_exit_code_is_kept(self):
        result = self.run_copy("2")
        self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
        self.assertIn("RUNNER_END exit=2", self.log_text())
        self.assert_no_key_anywhere(result)

    def test_3_missing_runner_exits_3(self):
        self.fake.unlink()
        result = self.run_copy("0")
        self.assertEqual(result.returncode, 3, (result.stdout, result.stderr))
        log = self.log_text()
        self.assertIn("RUNNER_FAIL RUNNER_SCRIPT_NOT_FOUND", log)
        self.assertNotIn("RUNNER_START", log)
        self.assertFalse((self.root / "fake-runner.txt").exists())
        self.assert_no_key_anywhere(result)


if __name__ == "__main__":
    unittest.main()
