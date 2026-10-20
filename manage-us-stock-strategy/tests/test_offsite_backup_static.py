"""Offsite backup: static checks of offsite_backup.ps1 and register_offsite_backup_task.ps1.

The tests read the script text only and never run PowerShell or git. offsite_backup.ps1 pushes only the current
branch to the same branch on origin (never main or a detached HEAD, no forced or bulk push, hooks kept, no
credential prompt), refuses to push when an outgoing path has a secret-like name, zips untracked record files to
the OneDrive folder and always exits 0. The registration script handles the one task InvestmentV2-OffsiteBackup
(daily 23:50) and registers nothing in -PlanOnly.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from test_auto_core_runner import case_only_parameter_assignments, script_parameters
from test_host_status_static import ORDER_IDENTIFIER, ORDER_NAMES, read_ascii

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
BACKUP = SCRIPTS / "offsite_backup.ps1"
REGISTER = SCRIPTS / "register_offsite_backup_task.ps1"
DEVPIPE = ROOT / "tools/dev_pipeline/devpipe.py"

FORBIDDEN_IN_BACKUP = (
    "--force", "--mirror", "--all", "--tags", "--delete", "--no-verify", "git add", "git commit", "git reset",
    "git checkout", "git stash", "Invoke-WebRequest", "Invoke-RestMethod", "kiwoom", "private_inputs\\",
    "Register-ScheduledTask",
)
REQUIRED_IN_BACKUP = (
    "push origin", "GIT_TERMINAL_PROMPT", "GCM_INTERACTIVE", "--not --remotes=origin", "backup-status/v1",
    "KeepCount", r"'^\d{4}-\d{2}-\d{2}\.zip$'", "BLOCKED_SECRET", "onedrive_running", "LASTEXITCODE",
    "read_only_repo",
)
OUTPUT_FOLDERS = ["auto-core", "regular-session-closes", "research-records", "journal-scores", "decisions",
                  "reconciliation", "exposure-review", "holding-cards", "status", "host-status"]


def code_lines(text: str) -> str:
    return "\n".join("" if line.lstrip().startswith("#") else line for line in text.splitlines())


class OffsiteBackupScriptTests(unittest.TestCase):
    def setUp(self):
        self.text = read_ascii(BACKUP)
        self.code = code_lines(self.text)

    def test_ascii_cmdletbinding_and_stop_preference(self):
        self.assertIn("[CmdletBinding()]", self.text)
        self.assertIn('$ErrorActionPreference = "Stop"', self.text)
        self.assertEqual(script_parameters(self.text)[0],
                         ["RepositoryRoot", "BackupRoot", "OutputPath", "KeepCount", "SkipPush", "SkipCopy", "DryRun"])
        self.assertEqual(case_only_parameter_assignments(self.text), [])
        self.assertIn("Join-Path $PSScriptRoot", self.text)
        self.assertIn("[int]$KeepCount = 30", self.text)

    def test_header_states_what_it_does_not_do(self):
        header = self.text[:self.text.index("[CmdletBinding()]")]
        for phrase in ("no broker call", "no forced push", "does not commit", "does not modify tracked files"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, header)

    def test_required_markers_present(self):
        for token in REQUIRED_IN_BACKUP:
            with self.subTest(token=token):
                self.assertIn(token, self.text)
        self.assertIn('$env:GIT_TERMINAL_PROMPT = "0"', self.text)
        self.assertIn('$env:GCM_INTERACTIVE = "never"', self.text)
        self.assertIn("read_only_repo = $true", self.text)

    def test_forbidden_tokens_absent_everywhere(self):
        lowered = self.text.lower()
        for token in FORBIDDEN_IN_BACKUP:
            with self.subTest(token=token):
                self.assertNotIn(token.lower(), lowered)
        self.assertNotIn("private_inputs", lowered)
        self.assertIn("private inputs", self.text)
        for word in ("config", "gc", "tag", "merge", "rebase", "fetch", "pull", "clean", "rm", "mv", "restore",
                     "switch", "branch", "update-ref", "worktree"):
            with self.subTest(git_word=word):
                self.assertNotRegex(self.code, r"-ArgumentText\s+\(?\"(?:-c \S+ )?%s\b" % re.escape(word))

    def test_git_runs_only_read_commands_and_one_push(self):
        commands = re.findall(r'-ArgumentText\s+\(?"([^"]+)"', self.code)
        verbs = [re.sub(r"^-c \S+ ", "", command).split()[0] for command in commands]
        self.assertEqual(set(verbs), {"rev-parse", "remote", "rev-list", "log", "ls-files", "push"})
        self.assertEqual(verbs.count("push"), 1)
        self.assertIn('-ArgumentText ("push origin " + $branch + ":refs/heads/" + $branch)', self.code)
        self.assertEqual(len(re.findall(r"\bpush\s+-", self.code)), 0)
        self.assertIn('"-c core.quotePath=false log -m --name-only --format= HEAD --not --remotes=origin"', self.code)
        self.assertIn('"rev-list --count HEAD --not --remotes=origin"', self.code)
        self.assertIn('"-c core.quotePath=false ls-files --others --exclude-standard stock-strategy-system"', self.code)
        self.assertIn('"-c core.quotePath=false ls-files --others --ignored --exclude-standard stock-strategy-system"',
                      self.code)

    def test_main_and_detached_head_are_never_pushed(self):
        stage = self.text[self.text.index("function Invoke-PushStage"):self.text.index("function Get-CopyPlan")]
        push_at = stage.index('-ArgumentText ("push origin')
        for guard in ('if ($branch -eq "HEAD")', 'if ($branch -eq "main")', "main is PR-only",
                      "if ($branch -notmatch $branchNamePattern)", "if ($secretPaths.Count -gt 0)", "if ($DryRun)",
                      'if ($SkipPush)', '-notcontains "origin"'):
            with self.subTest(guard=guard):
                self.assertLess(stage.index(guard), push_at)
        self.assertLess(stage.index('$push.state = "BLOCKED_SECRET"'), push_at)
        self.assertLess(stage.index("$env:GCM_INTERACTIVE"), push_at)
        self.assertIn("if ($pushResult.exit_code -eq 0)", stage)

    def test_git_calls_use_continue_only_around_the_call_and_judge_by_exit_code(self):
        helper = self.text[self.text.index("function Invoke-GitCapture"):self.text.index("function Get-LastLines")]
        self.assertIn("$previousErrorActionPreference = $ErrorActionPreference", helper)
        self.assertIn('$ErrorActionPreference = "Continue"', helper)
        self.assertIn("cmd /c $commandLine | Out-Null", helper)
        self.assertIn("$exitCode = $LASTEXITCODE", helper)
        self.assertIn("} finally {\n        $ErrorActionPreference = $previousErrorActionPreference", helper)
        self.assertEqual(self.code.count('$ErrorActionPreference = "Continue"'), 1)
        self.assertEqual(len(re.findall(r"(?<![\w-])git(?:\.exe)?\s", self.code)), 1)
        self.assertIn("'git -C \"' + $resolvedRepository + '\" ' + $ArgumentText", helper)

    def test_secret_name_rule_matches_devpipe(self):
        match = re.search(r"^\$secretNamePattern = '([^']+)'$", self.text, flags=re.MULTILINE)
        self.assertIsNotNone(match)
        pattern = match.group(1)
        devpipe = DEVPIPE.read_text(encoding="utf-8")
        source = re.search(r"SECRET_NAME_RE = re\.compile\(\s*r\"([^\"]+)\"\s*r\"([^\"]+)\"", devpipe)
        self.assertIsNotNone(source)
        self.assertEqual(pattern, source.group(1) + source.group(2))
        rule = re.compile(pattern, re.I)
        for name in (".env", ".env.local", "server.PEM", "a.key", "credentials-x.json", "secrets.json", "token.json",
                     "tokens.json", "id_rsa", "id_ed25519.pub"):
            with self.subTest(name=name):
                self.assertIsNotNone(rule.match(name))
        for name in ("kiwoom-token-reuse-2026-10-06.md", "tokens.md", "keys.txt", "env.md"):
            with self.subTest(name=name):
                self.assertIsNone(rule.match(name))
        check = self.text[self.text.index("function Test-SecretPath"):self.text.index("function Read-CaptureLines")]
        self.assertIn("$name -match $secretNamePattern", check)
        self.assertIn('Contains("/secrets/")', check)
        self.assertIn('Contains("auth.json")', check)
        # Applied before the push (outgoing paths) and before the copy (each file); names only, contents never read.
        self.assertIn("Test-SecretPath -RelativePath $_", self.text)
        self.assertGreaterEqual(self.text.count("$Copy.skipped_secret_files++"), 2)
        # Both copy sources get the full rule (name, /secrets/ folder, auth.json) on the repository-relative path.
        self.assertIn("Test-SecretPath -RelativePath $normalized", self.text)
        self.assertNotIn("Test-SecretPath -RelativePath $file.Name", self.text)
        self.assertIn("Test-SecretPath -RelativePath $relative", self.text)
        loop = self.text[self.text.index("foreach ($folder in $outputFolders)"):self.text.index("function Invoke-CopyStage")]
        self.assertLess(loop.index("$relative = $file.FullName"), loop.index("Test-SecretPath -RelativePath $relative"))
        self.assertNotRegex(self.code, r"ReadAllText|ReadAllBytes|Get-Content")

    def test_copy_sources_and_exclusions(self):
        match = re.search(r"^\$outputFolders = @\((.*?)\)$", self.text, flags=re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match)
        self.assertEqual(re.findall(r'"([^"]+)"', match.group(1)), OUTPUT_FOLDERS)
        for left_out in ("official-event-intake", "activation", "dev-runs"):
            with self.subTest(left_out=left_out):
                self.assertNotIn('"%s"' % left_out, match.group(1))
        self.assertIn('"stock-strategy-system/.tmp_skill_validation/", "stock-strategy-system/skill-staging/"',
                      self.text)
        self.assertIn("Get-ChildItem -LiteralPath $folderPath -Recurse -File", self.text)
        self.assertNotRegex(self.code, r"Get-ChildItem[^\n]*-Force")

    def test_zip_verified_before_rename_and_retention_limited(self):
        stage = self.text[self.text.index("function Invoke-CopyStage"):self.text.index("$workDirectory = $null")]
        self.assertIn('$temporaryZip = Join-Path $BackupRoot ($dateKst + ".tmp.zip")', stage)
        self.assertIn('$zipPath = Join-Path $BackupRoot ($dateKst + ".zip")', stage)
        self.assertNotIn(".zip.tmp", stage)
        self.assertIn("Compress-Archive -LiteralPath $topItems -DestinationPath $temporaryZip", stage)
        self.assertIn("if ($copy.entries -ne $copy.files)", stage)
        self.assertIn("$copy.files = @(Get-ChildItem -LiteralPath $stagingRoot -Recurse -File).Count", stage)
        verify = stage.index("if ($copy.entries -ne $copy.files)")
        rename = stage.index("[System.IO.File]::Replace($temporaryZip, $zipPath")
        ok = stage.index('$copy.state = "OK"')
        retention = stage.index("$dailyZips = ")
        self.assertLess(verify, rename)
        self.assertLess(rename, ok)
        self.assertLess(ok, retention)
        self.assertIn("Get-ChildItem -LiteralPath $BackupRoot -File | Where-Object { $_.Name -match $dailyZipPattern }",
                      stage)
        self.assertIn("Select-Object -Skip $KeepCount", stage)
        self.assertEqual(self.code.count("Remove-Item"), 1)
        self.assertIn("Remove-Item -LiteralPath $old.FullName", stage)
        self.assertIn('"OneDrive folder not found"', stage)
        self.assertIn('"sync completion not verified"', stage)
        self.assertIn("Get-Process -Name OneDrive -ErrorAction SilentlyContinue", stage)
        self.assertIn("$copy.locked_files++", stage)
        self.assertIn('"<OneDrive>"', self.text)

    def test_status_rule_result_file_and_exit_code(self):
        self.assertIn(
            "if ($passStates -notcontains $push.state -or $passStates -notcontains $copy.state -or "
            "-not $copy.onedrive_running -or $copy.locked_files -gt 0) {", self.text)
        self.assertIn('$passStates = @("OK", "SKIPPED")', self.text)
        for field in ("schema", "generated_at", "generated_at_kst", "hostname", "dry_run", "push", "copy", "status",
                      "read_only_repo"):
            with self.subTest(field=field):
                self.assertRegex(self.text, r"\n\s+%s = " % field)
        self.assertIn(r'"workspace\outputs\backup\LATEST.json"', self.text)
        self.assertIn("New-Object System.Text.UTF8Encoding($false)", self.text)
        self.assertIn('$temporaryPath = $fullOutputPath + ".tmp"', self.text)
        self.assertIn("[System.IO.File]::Replace($temporaryPath, $fullOutputPath, [NullString]::Value)", self.text)
        self.assertIn("[System.IO.File]::Move($temporaryPath, $fullOutputPath)", self.text)
        self.assertEqual(re.findall(r"\bexit\s+(\S+)", self.code), ["0"])
        self.assertTrue(self.text.rstrip().endswith("exit 0"))
        self.assertIn('Write-Output ("OFFSITE_BACKUP_FAIL "', self.text)
        self.assertNotIn("order_authority", self.text.lower())


class RegisterOffsiteBackupTaskTests(unittest.TestCase):
    def setUp(self):
        self.text = read_ascii(REGISTER)

    def test_ascii_cmdletbinding_and_stop_preference(self):
        self.assertIn("[CmdletBinding()]", self.text)
        self.assertIn('$ErrorActionPreference = "Stop"', self.text)
        self.assertEqual(script_parameters(self.text)[0], ["PlanOnly", "RepositoryRoot"])
        self.assertEqual(case_only_parameter_assignments(self.text), [])

    def test_required_settings_present(self):
        for token in ("InvestmentV2-OffsiteBackup", "-Daily", '"23:50"', "PlanOnly", "-LogonType Interactive",
                      "-RunLevel Limited", "-StartWhenAvailable", "WakeToRun:$false", "-MultipleInstances IgnoreNew",
                      "LimitMinutes = 30", "Korea Standard Time", "offsite_backup.ps1",
                      "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File", "-RepositoryRoot", "-Force",
                      "Daily 23:50"):
            with self.subTest(token=token):
                self.assertIn(token, self.text)
        self.assertIn("New-ScheduledTaskTrigger -Daily -At $task.TriggerTime", self.text)
        self.assertNotIn("-Weekly", self.text)
        self.assertNotIn("Tue-Sat", self.text)
        self.assertNotIn("DaysOfWeek", self.text)

    def test_handles_only_the_offsite_backup_task(self):
        self.assertEqual(re.findall(r'Name\s*=\s*"([^"]+)"', self.text), ["InvestmentV2-OffsiteBackup"])
        for other in ("InvestmentV2-AutoCore", "InvestmentV2-HostStatus", "InvestmentV2-DocsCommit"):
            with self.subTest(other=other):
                self.assertNotIn(other, self.text)
        self.assertEqual(self.text.count("Register-ScheduledTask"), 1)
        self.assertIn("-TaskName $task.Name", self.text)
        self.assertNotIn("Unregister-ScheduledTask", self.text)
        self.assertNotRegex(self.text, r"\b(?:Set|Enable|Disable|Start|Stop)-ScheduledTask\b")

    def test_plan_only_exits_before_registering(self):
        plan = self.text.index("if ($PlanOnly) {")
        register = self.text.index("Register-ScheduledTask")
        self.assertLess(plan, register)
        plan_block = self.text[plan:self.text.index("}\n", self.text.index("exit 0", plan)) + 1]
        self.assertIn('-Mode "PLAN_ONLY"', plan_block)
        self.assertIn("exit 0", plan_block)
        self.assertNotIn("Register-ScheduledTask", plan_block)


class OrderNameTests(unittest.TestCase):
    def test_no_order_names_in_either_script(self):
        for path in (BACKUP, REGISTER):
            text = read_ascii(path)
            lowered = text.lower()
            for name in ORDER_NAMES:
                with self.subTest(file=path.name, name=name):
                    self.assertNotIn(name, lowered)
            with self.subTest(file=path.name, name="order_*"):
                self.assertEqual(ORDER_IDENTIFIER.findall(text), [])
            with self.subTest(file=path.name, name="kiwoom"):
                self.assertNotIn("kiwoom", lowered)


if __name__ == "__main__":
    unittest.main()
