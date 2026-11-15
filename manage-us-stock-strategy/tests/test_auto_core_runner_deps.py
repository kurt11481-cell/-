"""runner-deps: run_auto_core.ps1 checks the Python time zone data before it starts the core.

On 2026-11-10 the default Python changed to one without tzdata; auto_core_reconcile.py and
auto_core_decide.py load zoneinfo time zones at import time, so both scheduled runs died before writing
any record and the cause showed only in a traceback. The runner now runs the same Python once with a
short check and, when it fails, writes a named RUNNER_FAIL PYTHON_DEPS_MISSING line with the Python
version and exits 4 without starting the core.

The static tests read the runner text. The behaviour tests run only a copy of the runner inside a
temporary folder next to a fake auto-core script that records its argument, with a fake Python (.cmd)
for the failure path; the repository runner and the real auto-core are never executed (no Kiwoom).
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
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
RUNNER_NAME = "run_auto_core.ps1"
RUNNER_START_LINE = ('Write-RunnerLine ("RUNNER_START utc=" + $stamp + " timezone=" + $timezoneId + '
                     '" command=" + $Command)')
COMMAND_CHECK = 'if ($Command -cne "daily" -and $Command -cne "decide") {'
CORE_CALL = "cmd /c $commandLine"

FAKE_AUTO_CORE = """import pathlib
import sys

pathlib.Path(__file__).resolve().parents[2].joinpath("argv.txt").write_text(sys.argv[1], encoding="ascii")
sys.exit(0)
"""

# Fake Python runtimes: they fail the pre-check (first argument -c) and would succeed for anything else,
# so a runner without the pre-check would start the fake core and end 0.
FAKE_PYTHON_SILENT = "@echo off\r\nif \"%~1\"==\"-c\" exit /b 1\r\nexit /b 0\r\n"
FAKE_PYTHON_WITH_VERSION = ("@echo off\r\nif \"%~1\"==\"-c\" (\r\n    echo 3.15.2\r\n"
                            "    echo ZoneInfoNotFoundError: 'No time zone found with key Asia/Seoul' 1>&2\r\n"
                            "    exit /b 1\r\n)\r\nexit /b 0\r\n")


def _code_lines(text: str) -> list[str]:
    return ["" if line.lstrip().startswith("#") else line for line in text.splitlines()]


def _runner_text() -> str:
    return (SCRIPTS / RUNNER_NAME).read_bytes().decode("ascii")


def _precheck_call_lines(text: str) -> list[str]:
    return [line for line in _code_lines(text) if "$PythonPath" in line and re.search(r"\s-c\s", line)]


class RunnerDepsStaticTests(unittest.TestCase):
    def test_runner_is_ascii_and_names_the_failure(self):
        text = _runner_text()
        for needle in ("RUNNER_FAIL PYTHON_DEPS_MISSING", "exit 4", "Asia/Seoul", "America/New_York", "python="):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)
        self.assertIn(RUNNER_START_LINE, text)
        self.assertEqual(text.count("RUNNER_START utc="), 1)

    def test_precheck_runs_the_same_python_without_isolation_flags(self):
        text = _runner_text()
        calls = _precheck_call_lines(text)
        self.assertEqual(len(calls), 1, calls)
        call = calls[0]
        self.assertIn("& $PythonPath -c $depsCode 2>&1", call)
        self.assertNotIn("cmd /c", call)
        for flag in (" -I ", " -s ", " -E ", " -S "):
            with self.subTest(flag=flag):
                self.assertNotIn(flag, call + " ")

    def test_precheck_code_uses_single_quotes_and_flushes_the_version_first(self):
        text = _runner_text()
        match = re.search(r'^\$depsCode = "(.*)"\s*$', text, flags=re.MULTILINE)
        self.assertIsNotNone(match)
        code = match.group(1)
        self.assertNotIn('"', code)
        self.assertNotIn("`", code)
        self.assertIn("print('%d.%d.%d' % sys.version_info[:3], flush=True)", code)
        self.assertLess(code.index("flush=True"), code.index("import zoneinfo"))
        self.assertIn("zoneinfo.ZoneInfo('Asia/Seoul')", code)
        self.assertIn("zoneinfo.ZoneInfo('America/New_York')", code)

    def test_order_is_command_check_then_precheck_then_start_then_core(self):
        code = "\n".join(_code_lines(_runner_text()))
        command_check = code.index(COMMAND_CHECK)
        precheck = code.index("& $PythonPath -c $depsCode")
        failure = code.index("RUNNER_FAIL PYTHON_DEPS_MISSING")
        start = code.index(RUNNER_START_LINE)
        core = code.index(CORE_CALL)
        self.assertRegex(code[command_check:], r'^if \(\$Command -cne "daily" -and \$Command -cne "decide"\) \{\s+exit 3')
        self.assertLess(command_check, precheck)
        self.assertLess(precheck, failure)
        self.assertLess(failure, start)
        self.assertLess(start, core)
        between = code[failure:start]
        self.assertIn("exit 4", between)


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell is not available")
class RunnerDepsCopyBehaviourTests(unittest.TestCase):
    """Runs a copy of the runner in a temporary repository whose auto-core script is a fake."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name).resolve()
        scripts = self.root / "manage-us-stock-strategy" / "scripts"
        scripts.mkdir(parents=True)
        self.runner = scripts / RUNNER_NAME
        shutil.copyfile(SCRIPTS / RUNNER_NAME, self.runner)
        self.fake = scripts / "auto_core.py"
        self.fake.write_text(FAKE_AUTO_CORE, encoding="ascii")
        self.argv = self.root / "argv.txt"
        self.fake_python_dir = self.root / "fake-python"
        self.fake_python_dir.mkdir()

    def tearDown(self):
        self._temporary.cleanup()

    def fake_python(self, name: str, body: str) -> Path:
        path = self.fake_python_dir / name
        path.write_bytes(body.encode("ascii"))
        return path

    def run_copy(self, command: str, python_path: Path | str) -> subprocess.CompletedProcess:
        # Only the copy under the temporary folder may run; the repository files never do.
        for path in (self.runner, self.fake):
            self.assertTrue(path.resolve().is_relative_to(self.root), path)
            self.assertFalse(path.resolve().is_relative_to(ROOT.resolve()), path)
        self.assertNotEqual(self.runner.resolve(), (SCRIPTS / RUNNER_NAME).resolve())
        return subprocess.run(
            [shutil.which("powershell.exe"), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(self.runner), "-RepositoryRoot", str(self.root), "-PythonPath", str(python_path),
             "-Command", command],
            cwd=str(self.root), capture_output=True, timeout=120,
        )

    def logs(self, command: str) -> list[Path]:
        return sorted((self.root / "workspace/outputs/auto-core/logs").glob("auto-core-%s-*.log" % command))

    def log_text(self, command: str) -> str:
        logs = self.logs(command)
        return logs[-1].read_text(encoding="utf-8", errors="replace") if logs else ""

    def assert_deps_failure(self, command: str, python_path: Path, version: str) -> str:
        result = self.run_copy(command, python_path)
        log_text = self.log_text(command)
        self.assertEqual(result.returncode, 4, (result.stdout, result.stderr, log_text))
        self.assertEqual(len(self.logs(command)), 1)
        self.assertIn("RUNNER_FAIL PYTHON_DEPS_MISSING zoneinfo=Asia/Seoul,America/New_York python=" + version,
                      log_text)
        self.assertNotIn("RUNNER_START", log_text)
        self.assertNotIn("RUNNER_END", log_text)
        self.assertFalse(self.argv.exists())
        lines = log_text.splitlines()
        self.assertEqual(len(lines), 2, lines)
        self.assertLessEqual(len(lines[1]), 300 + len("RUNNER_FAIL_DETAIL "))
        log_bytes = self.logs(command)[-1].read_bytes()
        log_bytes.decode("ascii")
        return log_text

    def test_daily_without_time_zone_data_exits_4_and_never_starts_the_core(self):
        self.assert_deps_failure("daily", self.fake_python("python-no-tz.cmd", FAKE_PYTHON_SILENT), "unknown")

    def test_decide_without_time_zone_data_exits_4_and_never_starts_the_core(self):
        self.assert_deps_failure("decide", self.fake_python("python-no-tz.cmd", FAKE_PYTHON_SILENT), "unknown")

    def test_failure_line_carries_the_python_version_and_the_last_error_line(self):
        log_text = self.assert_deps_failure(
            "daily", self.fake_python("python-3152.cmd", FAKE_PYTHON_WITH_VERSION), "3.15.2")
        self.assertIn("ZoneInfoNotFoundError", log_text.splitlines()[1])

    def test_python_with_time_zone_data_runs_the_core_as_before(self):
        for command in ("daily", "decide"):
            with self.subTest(command=command):
                if self.argv.exists():
                    self.argv.unlink()
                result = self.run_copy(command, sys.executable)
                log_text = self.log_text(command)
                self.assertEqual(result.returncode, 0, (result.stdout, result.stderr, log_text))
                self.assertEqual(self.argv.read_text(encoding="ascii"), command)
                self.assertEqual(len(self.logs(command)), 1)
                self.assertIn("RUNNER_START", log_text)
                self.assertIn("command=" + command, log_text)
                self.assertIn("RUNNER_END exit=0", log_text)
                self.assertNotIn("RUNNER_FAIL", log_text)

    def test_other_command_exits_3_before_the_precheck(self):
        result = self.run_copy("other", self.fake_python("python-no-tz.cmd", FAKE_PYTHON_SILENT))
        self.assertEqual(result.returncode, 3, (result.stdout, result.stderr))
        self.assertFalse(self.argv.exists())
        self.assertEqual(self.logs("other"), [])
        self.assertFalse((self.root / "workspace").exists())


if __name__ == "__main__":
    unittest.main()
