"""Static checks that every scheduled-task registration script starts PowerShell with a hidden window.

2026-10-21 07:58 KST the decide run of InvestmentV2-AutoCoreDecide ended with "^C" in its log and no RUNNER_END:
the task window was visible on the logged-on desktop and took a keyboard Ctrl+C. The scripts are read as text
only; no registration script is run here.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "manage-us-stock-strategy" / "scripts"

REGISTER_SCRIPTS = (
    SCRIPTS / "register_auto_core_task.ps1",
    SCRIPTS / "register_host_status_task.ps1",
    SCRIPTS / "register_journal_score_task.ps1",
    SCRIPTS / "register_offsite_backup_task.ps1",
    SCRIPTS / "register_sec_scheduled_shadow_task.ps1",
    REPO_ROOT / "docs" / "claude" / "t2rc-register-task.ps1",
)

HIDDEN_PREFIX = "-WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File"
ASSIGNMENT = re.compile(r"^\s*\$actionArguments\s*=\s*'([^']*)'", re.MULTILINE)


def action_argument_problems(content: str) -> list[str]:
    """Return why the task action arguments are not started hidden (empty list = hidden)."""
    found = ASSIGNMENT.findall(content)
    if len(found) != 1:
        return ["expected exactly one $actionArguments assignment, found %d" % len(found)]
    problems = []
    if not found[0].startswith(HIDDEN_PREFIX):
        problems.append("action arguments do not start with " + HIDDEN_PREFIX)
    if "-Argument $actionArguments" not in content:
        problems.append("the task action does not use $actionArguments")
    return problems


def text(path: Path) -> str:
    return path.read_bytes().decode("ascii")


class TaskWindowHiddenTests(unittest.TestCase):
    def test_every_registration_starts_powershell_hidden(self) -> None:
        for path in REGISTER_SCRIPTS:
            with self.subTest(script=path.name):
                self.assertEqual(action_argument_problems(text(path)), [])

    def test_logon_type_and_run_level_are_unchanged(self) -> None:
        for path in REGISTER_SCRIPTS:
            with self.subTest(script=path.name):
                content = text(path)
                self.assertIn("-LogonType Interactive", content)
                self.assertIn("-RunLevel Limited", content)
                self.assertNotIn("conhost", content.lower())

    def test_the_check_catches_the_visible_window_form(self) -> None:
        before = ("    $actionArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"{0}\" "
                  "-RepositoryRoot \"{1}\"' -f $scriptPath, $resolvedRepository\n"
                  "    $action = New-ScheduledTaskAction -Execute $powerShellExecutable -Argument $actionArguments\n")
        self.assertTrue(action_argument_problems(before))
        after = before.replace("'-NoProfile", "'-WindowStyle Hidden -NoProfile")
        self.assertEqual(action_argument_problems(after), [])
        # -WindowStyle after -File would be passed to the script, not to PowerShell.
        late = before.replace("-File \"{0}\"", "-File \"{0}\" -WindowStyle Hidden")
        self.assertTrue(action_argument_problems(late))
        self.assertTrue(action_argument_problems(""))
        self.assertTrue(action_argument_problems(after + after))


if __name__ == "__main__":
    unittest.main()
