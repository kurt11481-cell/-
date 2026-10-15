"""C1 host status: static checks of host_status.ps1 and register_host_status_task.ps1.

The tests read the script text only and never run PowerShell, so they also run on Linux. host_status.ps1
must stay read-only (no setting, registry, task or service change, no broker or network call), read only
the AutoAdminLogon value from Winlogon, isolate every check and always exit 0. The registration script
handles the one task InvestmentV2-HostStatus and registers nothing in -PlanOnly.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from test_auto_core_runner import case_only_parameter_assignments, script_parameters

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
HOST_STATUS = SCRIPTS / "host_status.ps1"
REGISTER = SCRIPTS / "register_host_status_task.ps1"

# Commands that change power, registry, task, service or process state, or reach the network.
FORBIDDEN_IN_HOST_STATUS = (
    "powercfg /change", "powercfg /setactive", "/hibernate", "Set-ItemProperty", "New-ItemProperty",
    "Register-ScheduledTask", "Unregister-ScheduledTask", "Restart-", "Stop-Service", "Invoke-WebRequest",
    "Invoke-RestMethod", "kiwoom", "DefaultPassword",
)
# Order names that must not appear in either script ("order_authority" is the only allowed order_ name).
ORDER_NAMES = ("/api/us/ordr", "kiwoom_order", "order_submit", "ust2000", "place_order", "cancel_order")
ORDER_IDENTIFIER = re.compile(r"order_(?!authority\b)\w+", flags=re.IGNORECASE)
CHECK_IDS = ("task_logon_type", "auto_logon", "power_sleep", "update_active_hours", "pending_reboot", "uptime",
             "session")


def read_ascii(path: Path) -> str:
    return path.read_bytes().decode("ascii").replace("\r\n", "\n")


def cmdlet_calls(text: str) -> set[str]:
    """Verb-Noun command names used in the code (comments removed)."""
    code = "\n".join("" if line.lstrip().startswith("#") else line for line in text.splitlines())
    return set(re.findall(r"(?<![\w$.-])([A-Z][a-z]+-[A-Z][A-Za-z]+)\b", code))


def active_hours_cover(start: int, end: int) -> bool:
    """Same formula as Test-ActiveHoursCover in host_status.ps1."""
    length = (end - start + 24) % 24
    offset = (5 - start + 24) % 24
    return offset + 4 <= length


class HostStatusScriptTests(unittest.TestCase):
    def setUp(self):
        self.text = read_ascii(HOST_STATUS)

    def test_ascii_cmdletbinding_and_stop_preference(self):
        self.assertIn("[CmdletBinding()]", self.text)
        self.assertIn('$ErrorActionPreference = "Stop"', self.text)
        self.assertEqual(script_parameters(self.text)[0], ["RepositoryRoot", "OutputPath"])
        self.assertEqual(case_only_parameter_assignments(self.text), [])
        self.assertIn("Join-Path $PSScriptRoot", self.text)

    def test_first_line_states_read_only_scope(self):
        first = self.text.splitlines()[0]
        self.assertTrue(first.startswith("# Read-only host status check"), first)
        self.assertIn("changes no setting", first)

    def test_forbidden_tokens_absent_everywhere(self):
        lowered = self.text.lower()
        for token in FORBIDDEN_IN_HOST_STATUS:
            with self.subTest(token=token):
                self.assertNotIn(token.lower(), lowered)
        self.assertIn("other Winlogon values", self.text)

    def test_only_reading_cmdlets_are_called(self):
        allowed = {"Get-Command", "Get-ScheduledTask", "Get-ScheduledTaskInfo", "Get-CimInstance", "Get-Date",
                   "Get-TimeZone", "Resolve-Path", "Join-Path", "Select-Object", "Where-Object", "New-Object",
                   "ConvertTo-Json", "Write-Output", "ConvertTo-OneLine", "Format-Time", "New-CheckResult",
                   "Invoke-Check", "Open-LocalMachineKey", "Read-LocalMachineValue", "Test-LocalMachineKey",
                   "Test-ActiveHoursCover", "Read-PowerAcIndex", "Read-ActiveScheme", "Get-CoreTaskCheck",
                   "Get-AutoLogonCheck", "Get-PowerSleepCheck", "Get-UpdateActiveHoursCheck",
                   "Get-PendingRebootCheck", "Get-UptimeCheck", "Get-SessionCheck"}
        self.assertEqual(cmdlet_calls(self.text) - allowed, set())

    def test_powercfg_uses_query_options_only(self):
        calls = re.findall(r"powercfg(?:\.exe)?\s+(/\w+)", self.text, flags=re.IGNORECASE)
        self.assertTrue(calls)
        self.assertEqual(set(option.lower() for option in calls) - {"/query", "/getactivescheme"}, set())

    def test_registry_opened_read_only_and_only_named_values_read(self):
        self.assertIn("OpenSubKey($SubKey, $false)", self.text)
        self.assertEqual(re.findall(r"\.GetValue\(([^)]*)\)", self.text), ["$Name"])
        names = set(re.findall(r'Read-LocalMachineValue\s+-SubKey\s+(?:"[^"]*"|\S+)\s+-Name\s+"(\w+)"', self.text))
        self.assertEqual(names, {"AutoAdminLogon", "ActiveHoursStart", "ActiveHoursEnd"})
        winlogon_reads = re.findall(r'Read-LocalMachineValue[^\n]*Winlogon[^\n]*', self.text)
        self.assertEqual(len(winlogon_reads), 1)
        self.assertIn('-Name "AutoAdminLogon"', winlogon_reads[0])
        self.assertNotIn("GetValueNames", self.text)
        self.assertNotIn("Get-ItemProperty", self.text)

    def test_required_markers_present(self):
        for token in ("AutoAdminLogon", "STANDBYIDLE", "HIBERNATEIDLE", "ActiveHoursStart", "ActiveHoursEnd",
                      "RebootRequired", "RebootPending", "host-status/v1", "read_only", "order_authority",
                      "LastBootUpTime", "WindowsIdentity]::GetCurrent().Name", "InvestmentV2-AutoCore",
                      "InvestmentV2-AutoCoreDecide", r"workspace\outputs\host-status\LATEST.json"):
            with self.subTest(token=token):
                self.assertIn(token, self.text)
        self.assertIn("read_only = $true", self.text)
        self.assertIn("order_authority = $false", self.text)

    def test_seven_checks_each_isolated(self):
        ids = re.findall(r'Invoke-Check -Id "(\w+)"', self.text)
        self.assertEqual(tuple(ids), CHECK_IDS)
        invoke = self.text[self.text.index("function Invoke-Check"):self.text.index("function Open-LocalMachineKey")]
        self.assertIn("try {", invoke)
        self.assertIn('-State "UNKNOWN" -Value $null', invoke)

    def test_exit_code_always_zero_and_outer_catch(self):
        self.assertEqual(re.findall(r"\bexit\s+(\S+)", self.text), ["0"])
        self.assertTrue(self.text.rstrip().endswith("exit 0"))
        self.assertIn('Write-Output ("HOST_STATUS_FAIL "', self.text)

    def test_output_written_as_utf8_without_bom_through_temporary_file(self):
        self.assertIn("New-Object System.Text.UTF8Encoding($false)", self.text)
        self.assertIn('$temporaryPath = $fullOutputPath + ".tmp"', self.text)
        self.assertIn("WriteAllText($temporaryPath", self.text)
        self.assertIn("[System.IO.File]::Replace($temporaryPath, $fullOutputPath, [NullString]::Value)", self.text)
        self.assertIn("[System.IO.File]::Move($temporaryPath, $fullOutputPath)", self.text)
        writes = re.findall(r"\[System\.IO\.File\]::(\w+)\(", self.text)
        self.assertEqual(set(writes), {"WriteAllText", "Exists", "Replace", "Move"})

    def test_top_level_status_rule(self):
        self.assertIn(
            'if ($warnCount -gt 0) { $status = "WARN" } elseif ($unknownCount -gt 0) { $status = "UNKNOWN" }',
            self.text)
        for field in ("schema", "generated_at", "generated_at_kst", "timezone", "hostname", "status",
                      "warn_count", "unknown_count", "checks"):
            with self.subTest(field=field):
                self.assertRegex(self.text, r"\n\s+%s = " % field)

    def test_active_hours_formula_matches_and_handles_midnight(self):
        self.assertIn("$length = ($End - $Start + 24) % 24", self.text)
        self.assertIn("$offset = (5 - $Start + 24) % 24", self.text)
        self.assertIn("return (($offset + 4) -le $length)", self.text)
        cases = {(8, 17): False, (5, 9): True, (4, 10): True, (6, 18): False, (0, 9): True,
                 (22, 10): True, (8, 2): False, (1, 9): True, (5, 8): False, (7, 7): False, (23, 9): True}
        for (start, end), expected in cases.items():
            with self.subTest(start=start, end=end):
                self.assertIs(active_hours_cover(start, end), expected)

    def test_auto_logon_missing_is_warn_and_task_rules_present(self):
        auto_logon = self.text[self.text.index("function Get-AutoLogonCheck"):
                               self.text.index("function Get-PowerSleepCheck")]
        self.assertIn('if ($text -eq "1")', auto_logon)
        self.assertEqual(auto_logon.count('state = "WARN"'), 2)
        self.assertEqual(auto_logon.count('state = "OK"'), 1)
        task = self.text[self.text.index("function Get-CoreTaskCheck"):self.text.index("function Get-AutoLogonCheck")]
        self.assertIn("task not registered", task)
        self.assertIn("requires logged-on user", task)
        self.assertIn("$now.AddDays(-7)", task)
        self.assertIn("[int64]$info.LastTaskResult -ne 0", task)


class RegisterHostStatusTaskTests(unittest.TestCase):
    def setUp(self):
        self.text = read_ascii(REGISTER)

    def test_ascii_cmdletbinding_and_stop_preference(self):
        self.assertIn("[CmdletBinding()]", self.text)
        self.assertIn('$ErrorActionPreference = "Stop"', self.text)
        self.assertEqual(script_parameters(self.text)[0], ["PlanOnly", "RepositoryRoot"])
        self.assertEqual(case_only_parameter_assignments(self.text), [])

    def test_required_settings_present(self):
        for token in ("InvestmentV2-HostStatus", '"05:50"', "PlanOnly", "-LogonType Interactive",
                      "-RunLevel Limited", "-StartWhenAvailable", "WakeToRun:$false", "-MultipleInstances IgnoreNew",
                      "LimitMinutes = 10", "Korea Standard Time", "host_status.ps1",
                      "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File",
                      "Investment_V2 host status check (read-only)", "-Force"):
            with self.subTest(token=token):
                self.assertIn(token, self.text)

    def test_handles_only_the_host_status_task(self):
        self.assertEqual(re.findall(r'Name\s*=\s*"([^"]+)"', self.text), ["InvestmentV2-HostStatus"])
        self.assertNotIn("InvestmentV2-AutoCore", self.text)
        self.assertNotIn("run_auto_core.ps1", self.text)
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
        for path in (HOST_STATUS, REGISTER):
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
