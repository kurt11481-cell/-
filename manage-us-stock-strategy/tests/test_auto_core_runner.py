"""runner-fix: run_auto_core.ps1 must not overwrite its own parameters.

PowerShell variable names ignore case, so `$command = Get-Command ...` in the runner overwrote the
`[string]$Command` parameter and every scheduled run ended RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND
(2026-10-13). The static tests look for that mistake in the auto-core PowerShell files. The behaviour
tests run only a copy of the runner inside a temporary folder next to a fake auto-core script that
records its argument; the repository runner and the real auto-core are never executed (no Kiwoom).
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
CHECKED_FILES = ("run_auto_core.ps1", "collect_30m.ps1", "register_auto_core_task.ps1")
AUTOMATIC_VARIABLES = {"true", "false", "null"}

# The pre-fix runner (base 1bd7bc4), reduced to the lines that matter.
PRE_FIX_RUNNER = """[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$PythonPath = "",
    [string]$Command = "daily"
)
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $PythonPath = $candidates | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $command) { $PythonPath = $command.Source }
    }
}
"""

FAKE_AUTO_CORE = """import pathlib
import sys

pathlib.Path(__file__).resolve().parents[2].joinpath("argv.txt").write_text(sys.argv[1], encoding="ascii")
sys.exit(0)
"""


def _strip_comments(text: str) -> str:
    text = re.sub(r"<#.*?#>", "", text, flags=re.DOTALL)
    return "\n".join("" if line.lstrip().startswith("#") else line for line in text.splitlines())


def _closing_paren(text: str, open_index: int) -> int:
    depth = 0
    quote = None
    for index in range(open_index, len(text)):
        char = text[index]
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("PARAM_BLOCK_NOT_CLOSED")


def script_parameters(text: str) -> tuple[list[str], str]:
    """Names of the script-level param(...) block and the code after it.

    Only a param block before the first function counts; param blocks inside functions belong to the
    function scope and are not script parameters.
    """
    code = _strip_comments(text)
    param_match = re.search(r"^\s*param\s*\(", code, flags=re.IGNORECASE | re.MULTILINE)
    function_match = re.search(r"^\s*function\s", code, flags=re.IGNORECASE | re.MULTILINE)
    if param_match is None or (function_match is not None and function_match.start() < param_match.start()):
        return [], code
    open_index = param_match.end() - 1
    close_index = _closing_paren(code, open_index)
    # Variables used as values (Mandatory = $true, defaults) are not parameter names.
    block = re.sub(r"=\s*\$[\w:]+", "=", code[open_index + 1:close_index])
    names = [match.group(1) for match in re.finditer(r"\$(\w+)\s*(?=[=,)]|$)", block, flags=re.MULTILINE)
             if match.group(1).lower() not in AUTOMATIC_VARIABLES]
    return names, code[close_index + 1:]


def case_only_parameter_assignments(text: str) -> list[str]:
    """Assignments in the script body to a variable that differs from a parameter only by case."""
    names, body = script_parameters(text)
    by_lower = {name.lower(): name for name in names}
    assigned = re.findall(r"\$(?:script:|local:|global:)?(\w+)\s*[+\-*/%]?=(?!=)", body, flags=re.IGNORECASE)
    assigned += re.findall(r"\bforeach\s*\(\s*\$(\w+)\s+in\b", body, flags=re.IGNORECASE)
    return [name for name in assigned if name.lower() in by_lower and name != by_lower[name.lower()]]


class ParameterShadowStaticTests(unittest.TestCase):
    def test_checker_catches_the_pre_fix_runner(self):
        self.assertEqual(script_parameters(PRE_FIX_RUNNER)[0], ["RepositoryRoot", "PythonPath", "Command"])
        self.assertEqual(case_only_parameter_assignments(PRE_FIX_RUNNER), ["command", "command"])

    def test_checker_catches_foreach_and_allows_same_case_reassignment(self):
        text = 'param(\n  [string]$Symbol,\n  [int]$Pages = 3\n)\n$Pages = 4\nforeach ($symbol in $list) { }\n'
        self.assertEqual(script_parameters(text)[0], ["Symbol", "Pages"])
        self.assertEqual(case_only_parameter_assignments(text), ["symbol"])

    def test_checker_ignores_function_parameters_and_automatic_values(self):
        text = ('param(\n  [Parameter(Mandatory = $true)][string]$Name\n)\n'
                'function Write-Line {\n    param([string]$Text)\n}\n$text = "x"\n')
        self.assertEqual(script_parameters(text)[0], ["Name"])
        self.assertEqual(case_only_parameter_assignments(text), [])
        function_first = 'function Write-Line {\n    param([string]$Text)\n}\n$text = "x"\n'
        self.assertEqual(script_parameters(function_first)[0], [])

    def test_auto_core_powershell_files_never_overwrite_a_parameter(self):
        expected = {
            "run_auto_core.ps1": ["RepositoryRoot", "PythonPath", "Command"],
            "collect_30m.ps1": ["Symbol", "Exchange", "KiwoomProfile", "Newest", "Oldest", "Pages", "StepDays",
                                "PauseSeconds", "OutRoot"],
            "register_auto_core_task.ps1": ["PlanOnly", "RepositoryRoot"],
        }
        for name in CHECKED_FILES:
            with self.subTest(file=name):
                text = (SCRIPTS / name).read_text(encoding="ascii")
                self.assertEqual(script_parameters(text)[0], expected[name])
                self.assertEqual(case_only_parameter_assignments(text), [])

    def test_runner_python_lookup_uses_its_own_variable(self):
        text = (SCRIPTS / RUNNER_NAME).read_text(encoding="ascii")
        self.assertIn("$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue", text)
        self.assertIn("if ($null -ne $pythonCommand) { $PythonPath = $pythonCommand.Source }", text)
        self.assertNotRegex(text, r"\$command\b")


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell is not available")
class RunnerCopyBehaviourTests(unittest.TestCase):
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

    def tearDown(self):
        self._temporary.cleanup()

    def run_copy(self, command: str) -> subprocess.CompletedProcess:
        # Only the copy under the temporary folder may run; the repository files never do.
        for path in (self.runner, self.fake):
            self.assertTrue(path.resolve().is_relative_to(self.root), path)
            self.assertFalse(path.resolve().is_relative_to(ROOT.resolve()), path)
        self.assertNotEqual(self.runner.resolve(), (SCRIPTS / RUNNER_NAME).resolve())
        environment = dict(os.environ)
        environment["PATH"] = os.path.dirname(sys.executable) + os.pathsep + environment.get("PATH", "")
        return subprocess.run(
            [shutil.which("powershell.exe"), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(self.runner), "-RepositoryRoot", str(self.root), "-Command", command],
            cwd=str(self.root), env=environment, capture_output=True, timeout=120,
        )

    def assert_ran(self, command: str):
        result = self.run_copy(command)
        logs = sorted((self.root / "workspace/outputs/auto-core/logs").glob("auto-core-%s-*.log" % command))
        log_text = logs[-1].read_text(encoding="utf-8", errors="replace") if logs else ""
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr, log_text))
        self.assertEqual(self.argv.read_text(encoding="ascii"), command)
        self.assertEqual(len(logs), 1)
        self.assertIn("RUNNER_START", log_text)
        self.assertIn("command=" + command, log_text)
        self.assertIn("RUNNER_END exit=0", log_text)
        self.assertNotIn("RUNNER_FAIL", log_text)

    def test_daily_finds_python_on_path_without_python_path(self):
        self.assert_ran("daily")

    def test_decide_finds_python_on_path_without_python_path(self):
        self.assert_ran("decide")

    def test_other_command_exits_3_without_running_the_script(self):
        result = self.run_copy("other")
        self.assertEqual(result.returncode, 3, (result.stdout, result.stderr))
        self.assertFalse(self.argv.exists())


if __name__ == "__main__":
    unittest.main()
