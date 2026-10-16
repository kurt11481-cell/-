"""Static checks of the weekly journal scoring task scripts (f-evo-loop step 1). PowerShell is never run here."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import score_decision_journal as scorer  # noqa: E402

RUN = SCRIPTS / "run_journal_score.ps1"
REGISTER = SCRIPTS / "register_journal_score_task.ps1"


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


class ScriptTextTests(unittest.TestCase):
    def test_both_scripts_are_ascii_advanced_scripts(self) -> None:
        for path in (RUN, REGISTER):
            with self.subTest(script=path.name):
                raw = path.read_bytes()
                self.assertTrue(all(byte < 128 for byte in raw), "new .ps1 files are ASCII only")
                self.assertIn("[CmdletBinding()]", text(path))

    def test_register_script_handles_one_weekly_task(self) -> None:
        content = text(REGISTER)
        for required in ("InvestmentV2-JournalScore", "-Weekly", "Sunday", "09:20", "PlanOnly", "Interactive",
                         "WakeToRun:$false", "IgnoreNew", "Korea Standard Time", "StartWhenAvailable",
                         "LimitMinutes = 15", "Register-ScheduledTask", "-Force", "run_journal_score.ps1",
                         "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File",
                         "Investment_V2 weekly journal scoring with the learning block (display only, writes "
                         "journal-scores only, no order authority)"):
            with self.subTest(required=required):
                self.assertIn(required, content)
        self.assertEqual(set(re.findall(r"InvestmentV2-[A-Za-z0-9]+", content)), {"InvestmentV2-JournalScore"})
        self.assertEqual(content.count("Register-ScheduledTask"), 1)
        for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Tue-Sat"):
            self.assertNotIn(weekday, content)
        # -PlanOnly prints the plan and exits before anything is registered.
        self.assertLess(content.index("if ($PlanOnly)"), content.index("Register-ScheduledTask"))
        plan_block = content[content.index("if ($PlanOnly)"):content.index("if (-not $timezoneReady)")]
        self.assertIn("exit 0", plan_block)
        self.assertNotIn("Unregister-ScheduledTask", content)
        self.assertNotIn("Set-ScheduledTask", content)

    def test_run_script_writes_only_the_weekly_status_and_logs(self) -> None:
        content = text(RUN)
        for required in ("--learning", "WEEKLY_LATEST.json", "journal-score-weekly/v1", "order_authority",
                         "LEARNING_FAILED", "learning_failed", "learning_present", "report_path", "exit_code",
                         "Move-Item", "-Force", "UTF8Encoding($false)", "score_decision_journal.py",
                         "workspace\\outputs\\journal-scores", "journal-scores.json"):
            with self.subTest(required=required):
                self.assertIn(required, content)
        lowered = content.lower()
        for forbidden in ("Invoke-WebRequest", "Invoke-RestMethod", "kiwoom", "Remove-Item", "Start-Sleep"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.lower(), lowered)
        authority_lines = [line for line in content.splitlines() if "order_authority" in line and "=" in line]
        self.assertEqual([line.split("=", 1)[1].strip() for line in authority_lines], ["$false"])
        self.assertIn('$status = "FAIL"', content)
        self.assertIn('$why = "LEARNING_FAILED"', content)

    def test_no_state_policy_or_ledger_path_in_either_script(self) -> None:
        for path in (RUN, REGISTER):
            content = text(path)
            for forbidden in ("stock-strategy-system", "workspace\\policies", "workspace/policies",
                              "decision_journal.json"):
                with self.subTest(script=path.name, forbidden=forbidden):
                    self.assertNotIn(forbidden, content)


class FailedBlockShapeTests(unittest.TestCase):
    """The runner marks a report FAIL when learning.errors has a reason starting with LEARNING_FAILED: the scorer
    must keep writing that shape."""

    def test_the_failed_block_carries_the_reason_the_runner_looks_for(self) -> None:
        block = scorer.failed_learning(RuntimeError("broken input"))
        self.assertTrue(isinstance(block["errors"], list) and block["errors"])
        self.assertTrue(block["errors"][0]["reason"].startswith("LEARNING_FAILED"))
        self.assertTrue(scorer.LEARNING_FAILED == "LEARNING_FAILED")
        self.assertIn('StartsWith("' + scorer.LEARNING_FAILED + '")', text(RUN))
        self.assertIn('Get-JsonValue -Object $learning -Name "errors"', text(RUN))
        self.assertIn('-Name "reason"', text(RUN))


if __name__ == "__main__":
    unittest.main()
