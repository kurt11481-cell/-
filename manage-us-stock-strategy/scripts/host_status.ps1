# Read-only host status check: reads core task settings, AutoAdminLogon only, sleep timeouts, update active hours, pending reboot, uptime and session; changes no setting, makes no broker or network call, writes one JSON file.
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$OutputPath = ""
)

# C1 (docs/claude/f-trading-infra-gap-review-2026-10-12.md 4): the auto-core tasks run as "logged-on user,
# no wake, start when available". Sleep, hibernate or an update reboot without logon stops them silently.
# This script only reads; the only write is OutputPath (default workspace\outputs\host-status\LATEST.json),
# written to a .tmp file first and then swapped in. Every check is isolated: a read failure gives
# state UNKNOWN for that check only. From Winlogon only AutoAdminLogon is read (no other Winlogon values).
# powercfg is used with query options only. Exit code is always 0 so a check failure never fails the task.
# Consumer: the 08:50 alert (docs/claude/scheduled-prompts/auto-core-alert.txt).
# InvestmentV2-JournalScore (weekly, f-evo-loop) uses the same rules: not registered, disabled, or a nonzero last result within 7 days gives WARN.
# backup_recent reads workspace\outputs\backup\LATEST.json (offsite_backup.ps1, daily 23:50): missing, older than 26 hours,
# a dry run or a status other than OK gives WARN; unreadable or another schema gives UNKNOWN.

$ErrorActionPreference = "Stop"
$coreTaskNames = @("InvestmentV2-AutoCore", "InvestmentV2-AutoCoreDecide", "InvestmentV2-JournalScore")

function ConvertTo-OneLine {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    $line = ($Text -replace "[\r\n]+", " ").Trim()
    if ($line.Length -gt 200) { $line = $line.Substring(0, 200) }
    return $line
}

function Format-Time {
    param($Value)
    if ($null -eq $Value) { return $null }
    return ([DateTime]$Value).ToString("o")
}

function New-CheckResult {
    param([string]$Id, [string]$State, $Value, [string]$Note)
    return [ordered]@{ id = $Id; state = $State; value = $Value; note = $Note }
}

function Invoke-Check {
    param([string]$Id, [scriptblock]$Body)
    try {
        $result = & $Body
        if ($result -isnot [System.Collections.IDictionary] -or @("OK", "WARN", "UNKNOWN") -notcontains $result.state) {
            return New-CheckResult -Id $Id -State "UNKNOWN" -Value $null -Note "internal: check returned no result"
        }
        return New-CheckResult -Id $Id -State $result.state -Value $result.value -Note $result.note
    } catch {
        return New-CheckResult -Id $Id -State "UNKNOWN" -Value $null -Note ("read failed: " + (ConvertTo-OneLine $_.Exception.Message))
    }
}

function Open-LocalMachineKey {
    param([string]$SubKey)
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
    return $base.OpenSubKey($SubKey, $false)
}

function Read-LocalMachineValue {
    # Reads exactly one named value; returns $null when the key or the value is missing.
    param([string]$SubKey, [string]$Name)
    $key = Open-LocalMachineKey -SubKey $SubKey
    if ($null -eq $key) { return $null }
    try { return $key.GetValue($Name) } finally { $key.Close() }
}

function Test-LocalMachineKey {
    param([string]$SubKey)
    $key = Open-LocalMachineKey -SubKey $SubKey
    if ($null -eq $key) { return $false }
    $key.Close()
    return $true
}

function Test-ActiveHoursCover {
    # Active hours run from Start (inclusive) to End (exclusive) and may cross midnight (e.g. 8 -> 2).
    # True when the window 05:00-09:00 lies fully inside them. Start = End gives length 0 (not covered).
    param([int]$Start, [int]$End)
    $length = ($End - $Start + 24) % 24
    $offset = (5 - $Start + 24) % 24
    return (($offset + 4) -le $length)
}

function Read-PowerAcIndex {
    param([string]$SettingAlias)
    $ErrorActionPreference = "Continue"
    $lines = @(& powercfg.exe /query SCHEME_CURRENT SUB_SLEEP $SettingAlias 2>$null)
    if ($LASTEXITCODE -ne 0) { throw ("powercfg query " + $SettingAlias + " returned " + $LASTEXITCODE) }
    foreach ($line in $lines) {
        if ([string]$line -match 'AC[^:]*:\s*0x([0-9A-Fa-f]+)') { return [Convert]::ToInt64($Matches[1], 16) }
    }
    return $null
}

function Read-ActiveScheme {
    $ErrorActionPreference = "Continue"
    $lines = @(& powercfg.exe /getactivescheme 2>$null)
    if ($LASTEXITCODE -ne 0) { throw ("powercfg getactivescheme returned " + $LASTEXITCODE) }
    foreach ($line in $lines) {
        if ([string]$line -match '([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\s*(\((.*)\))?') {
            $name = $null
            if ($Matches.ContainsKey(3)) { $name = $Matches[3] }
            return [ordered]@{ guid = $Matches[1]; name = $name }
        }
    }
    return $null
}

function Get-CoreTaskCheck {
    if ($null -eq (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) { throw "Get-ScheduledTask not available" }
    $now = Get-Date
    $entries = New-Object System.Collections.ArrayList
    $warnings = New-Object System.Collections.ArrayList
    $unknowns = New-Object System.Collections.ArrayList
    $notes = New-Object System.Collections.ArrayList
    foreach ($taskName in $coreTaskNames) {
        $task = @(Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) | Select-Object -First 1
        if ($null -eq $task) {
            [void]$entries.Add([ordered]@{ name = $taskName; registered = $false })
            [void]$warnings.Add($taskName + ": task not registered")
            continue
        }
        $entry = [ordered]@{
            name = $taskName
            registered = $true
            logon_type = [string]$task.Principal.LogonType
            wake_to_run = [bool]$task.Settings.WakeToRun
            start_when_available = [bool]$task.Settings.StartWhenAvailable
            state = [string]$task.State
            last_run_time = $null
            last_task_result = $null
            next_run_time = $null
        }
        if ($entry.logon_type -eq "Interactive") { [void]$notes.Add($taskName + ": requires logged-on user (Interactive logon)") }
        if ($entry.state -eq "Disabled") { [void]$warnings.Add($taskName + ": task disabled") }
        try {
            $info = Get-ScheduledTaskInfo -InputObject $task -ErrorAction Stop
            $entry.last_run_time = Format-Time $info.LastRunTime
            $entry.last_task_result = [int64]$info.LastTaskResult
            $entry.next_run_time = Format-Time $info.NextRunTime
            if ($null -ne $info.LastRunTime -and [int64]$info.LastTaskResult -ne 0) {
                $lastRun = [DateTime]$info.LastRunTime
                if ($lastRun -ge $now.AddDays(-7) -and $lastRun -le $now.AddMinutes(5)) {
                    [void]$warnings.Add(("{0}: last result 0x{1:X8} at {2}" -f $taskName, [int64]$info.LastTaskResult, $entry.last_run_time))
                }
            }
        } catch {
            [void]$unknowns.Add($taskName + ": task info read failed: " + (ConvertTo-OneLine $_.Exception.Message))
        }
        [void]$entries.Add($entry)
    }
    $state = "OK"
    if ($warnings.Count -gt 0) { $state = "WARN" } elseif ($unknowns.Count -gt 0) { $state = "UNKNOWN" }
    $noteParts = @($warnings) + @($unknowns) + @($notes)
    return [ordered]@{ state = $state; value = $entries.ToArray(); note = ($noteParts -join "; ") }
}

function Get-AutoLogonCheck {
    $raw = Read-LocalMachineValue -SubKey "SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name "AutoAdminLogon"
    if ($null -eq $raw) {
        return [ordered]@{ state = "WARN"; value = $null; note = "AutoAdminLogon not set: after a reboot the core tasks wait for a user logon" }
    }
    $text = ([string]$raw).Trim()
    if ($text -eq "1") {
        return [ordered]@{ state = "OK"; value = $text; note = "automatic logon on" }
    }
    return [ordered]@{ state = "WARN"; value = $text; note = "automatic logon off: after a reboot the core tasks wait for a user logon" }
}

function Get-PowerSleepCheck {
    $scheme = $null
    $schemeError = $null
    try { $scheme = Read-ActiveScheme } catch { $schemeError = ConvertTo-OneLine $_.Exception.Message }
    $standby = $null
    $hibernate = $null
    $readErrors = New-Object System.Collections.ArrayList
    try { $standby = Read-PowerAcIndex -SettingAlias "STANDBYIDLE" } catch { [void]$readErrors.Add("STANDBYIDLE: " + (ConvertTo-OneLine $_.Exception.Message)) }
    try { $hibernate = Read-PowerAcIndex -SettingAlias "HIBERNATEIDLE" } catch { [void]$readErrors.Add("HIBERNATEIDLE: " + (ConvertTo-OneLine $_.Exception.Message)) }
    $value = [ordered]@{
        scheme_guid = $null
        scheme_name = $null
        standby_ac_seconds = $standby
        hibernate_ac_seconds = $hibernate
    }
    if ($null -ne $scheme) {
        $value.scheme_guid = $scheme.guid
        $value.scheme_name = $scheme.name
    }
    $warnings = New-Object System.Collections.ArrayList
    $unknowns = New-Object System.Collections.ArrayList
    if ($null -eq $standby) { [void]$unknowns.Add("AC sleep timeout not read") }
    elseif ($standby -ne 0) { [void]$warnings.Add(("sleep after {0} min on AC" -f [Math]::Round($standby / 60.0, 1))) }
    if ($null -eq $hibernate) { [void]$unknowns.Add("AC hibernate timeout not read") }
    elseif ($hibernate -ne 0) { [void]$warnings.Add(("hibernate after {0} min on AC" -f [Math]::Round($hibernate / 60.0, 1))) }
    $state = "OK"
    if ($warnings.Count -gt 0) { $state = "WARN" } elseif ($unknowns.Count -gt 0) { $state = "UNKNOWN" }
    $noteParts = @($warnings) + @($unknowns) + @($readErrors)
    if ($null -ne $schemeError) { $noteParts += ("scheme name not read: " + $schemeError) }
    if ($noteParts.Count -eq 0) { $noteParts = @("sleep and hibernate never on AC") }
    return [ordered]@{ state = $state; value = $value; note = ($noteParts -join "; ") }
}

function Get-UpdateActiveHoursCheck {
    $subKey = "SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
    $startRaw = Read-LocalMachineValue -SubKey $subKey -Name "ActiveHoursStart"
    $endRaw = Read-LocalMachineValue -SubKey $subKey -Name "ActiveHoursEnd"
    $value = [ordered]@{ active_hours_start = $startRaw; active_hours_end = $endRaw }
    if ($null -eq $startRaw -or $null -eq $endRaw) {
        return [ordered]@{ state = "UNKNOWN"; value = $value; note = "active hours not set" }
    }
    $start = [int]$startRaw
    $end = [int]$endRaw
    if ($start -lt 0 -or $start -gt 23 -or $end -lt 0 -or $end -gt 23) {
        return [ordered]@{ state = "UNKNOWN"; value = $value; note = "active hours out of range 0-23" }
    }
    if (Test-ActiveHoursCover -Start $start -End $end) {
        return [ordered]@{ state = "OK"; value = $value; note = ("active hours {0}-{1} cover 05:00-09:00" -f $start, $end) }
    }
    return [ordered]@{ state = "WARN"; value = $value; note = ("active hours {0}-{1} do not cover 05:00-09:00: update reboot possible 06:15-08:50" -f $start, $end) }
}

function Get-PendingRebootCheck {
    $paths = [ordered]@{
        reboot_required_key = "SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"
        reboot_pending_key = "SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"
    }
    $value = [ordered]@{ reboot_required_key = $null; reboot_pending_key = $null }
    $warnings = New-Object System.Collections.ArrayList
    $unknowns = New-Object System.Collections.ArrayList
    foreach ($field in @($paths.Keys)) {
        try {
            $exists = Test-LocalMachineKey -SubKey $paths[$field]
            $value[$field] = $exists
            if ($exists) { [void]$warnings.Add($field + " present: reboot pending") }
        } catch {
            [void]$unknowns.Add($field + " read failed: " + (ConvertTo-OneLine $_.Exception.Message))
        }
    }
    $state = "OK"
    if ($warnings.Count -gt 0) { $state = "WARN" } elseif ($unknowns.Count -gt 0) { $state = "UNKNOWN" }
    $noteParts = @($warnings) + @($unknowns)
    if ($noteParts.Count -eq 0) { $noteParts = @("no pending reboot") }
    return [ordered]@{ state = $state; value = $value; note = ($noteParts -join "; ") }
}

function Get-UptimeCheck {
    $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
    $boot = [DateTime]$os.LastBootUpTime
    $hours = [Math]::Round(((Get-Date) - $boot).TotalHours, 1)
    return [ordered]@{ state = "OK"; value = [ordered]@{ last_boot_time = (Format-Time $boot); uptime_hours = $hours }; note = "reference only" }
}

function Get-SessionCheck {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $sessionId = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
    $value = [ordered]@{ user = $identity; session_name = $env:SESSIONNAME; session_id = $sessionId }
    return [ordered]@{ state = "OK"; value = $value; note = "reference only" }
}

function Get-BackupRecentCheck {
    # The backup runs at 23:50 and this check at 05:50 (normal age 6 hours); one missed night gives about 30 hours.
    $backupPath = Join-Path $resolvedRepository "workspace\outputs\backup\LATEST.json"
    if (-not [System.IO.File]::Exists($backupPath)) {
        return [ordered]@{ state = "WARN"; value = $null; note = "no backup record" }
    }
    try {
        $record = Get-Content -LiteralPath $backupPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return [ordered]@{ state = "UNKNOWN"; value = $null; note = ("backup record not readable: " + (ConvertTo-OneLine $_.Exception.Message)) }
    }
    if ($null -eq $record -or [string]$record.schema -ne "backup-status/v1") {
        return [ordered]@{ state = "UNKNOWN"; value = $null; note = "backup record schema is not backup-status/v1" }
    }
    $value = [ordered]@{
        generated_at_kst = [string]$record.generated_at_kst
        push_state = [string]$record.push.state
        copy_state = [string]$record.copy.state
        copy_bytes = $record.copy.bytes
    }
    $generated = $null
    if ($record.generated_at -is [DateTime]) {
        $generated = ([DateTime]$record.generated_at).ToUniversalTime()
    } else {
        $styles = [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal
        $parsed = [DateTime]::MinValue
        if ([DateTime]::TryParseExact([string]$record.generated_at, "yyyy-MM-ddTHH:mm:ssZ", [System.Globalization.CultureInfo]::InvariantCulture, $styles, [ref]$parsed)) {
            $generated = $parsed
        }
    }
    if ($null -eq $generated) {
        return [ordered]@{ state = "UNKNOWN"; value = $value; note = "backup record generated_at not readable" }
    }
    $ageHours = [Math]::Round(([DateTime]::UtcNow - $generated).TotalHours, 1)
    $stateText = "push " + $value.push_state + ", copy " + $value.copy_state
    if ($ageHours -lt -1) {
        return [ordered]@{ state = "UNKNOWN"; value = $value; note = ("backup record time is {0}h in the future" -f (-$ageHours)) }
    }
    if ($ageHours -gt 26) {
        return [ordered]@{ state = "WARN"; value = $value; note = ("backup older than 26h ({0}h): {1}" -f $ageHours, $stateText) }
    }
    if ($record.dry_run -eq $true) {
        return [ordered]@{ state = "WARN"; value = $value; note = ("last backup was a dry run: " + $stateText) }
    }
    if ([string]$record.status -ne "OK") {
        return [ordered]@{ state = "WARN"; value = $value; note = ("backup status " + [string]$record.status + ": " + $stateText) }
    }
    return [ordered]@{ state = "OK"; value = $value; note = ("backup {0}h old: {1}" -f $ageHours, $stateText) }
}

try {
    if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
        # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
        $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    }
    $resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        $OutputPath = Join-Path $resolvedRepository "workspace\outputs\host-status\LATEST.json"
    }
    $fullOutputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)

    $checks = @(
        (Invoke-Check -Id "task_logon_type" -Body { Get-CoreTaskCheck }),
        (Invoke-Check -Id "auto_logon" -Body { Get-AutoLogonCheck }),
        (Invoke-Check -Id "power_sleep" -Body { Get-PowerSleepCheck }),
        (Invoke-Check -Id "update_active_hours" -Body { Get-UpdateActiveHoursCheck }),
        (Invoke-Check -Id "pending_reboot" -Body { Get-PendingRebootCheck }),
        (Invoke-Check -Id "uptime" -Body { Get-UptimeCheck }),
        (Invoke-Check -Id "session" -Body { Get-SessionCheck })
    )
    # Added after the seven checks so the existing array lines stay unchanged; the leading comma keeps it one element.
    $checks += ,(Invoke-Check -Id "backup_recent" -Body { Get-BackupRecentCheck })
    $warnCount = @($checks | Where-Object { $_.state -eq "WARN" }).Count
    $unknownCount = @($checks | Where-Object { $_.state -eq "UNKNOWN" }).Count
    $status = "OK"
    if ($warnCount -gt 0) { $status = "WARN" } elseif ($unknownCount -gt 0) { $status = "UNKNOWN" }

    $nowUtc = [DateTime]::UtcNow
    $invariant = [System.Globalization.CultureInfo]::InvariantCulture
    $timezoneId = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
    $report = [ordered]@{
        schema = "host-status/v1"
        generated_at = $nowUtc.ToString("yyyy-MM-ddTHH:mm:ssZ", $invariant)
        generated_at_kst = $nowUtc.AddHours(9).ToString("yyyy-MM-ddTHH:mm:ss", $invariant) + "+09:00"
        timezone = $timezoneId
        hostname = $env:COMPUTERNAME
        status = $status
        warn_count = $warnCount
        unknown_count = $unknownCount
        checks = $checks
        read_only = $true
        order_authority = $false
    }
    $json = $report | ConvertTo-Json -Depth 8

    $outputDirectory = [System.IO.Path]::GetDirectoryName($fullOutputPath)
    [void][System.IO.Directory]::CreateDirectory($outputDirectory)
    $temporaryPath = $fullOutputPath + ".tmp"
    [System.IO.File]::WriteAllText($temporaryPath, $json, (New-Object System.Text.UTF8Encoding($false)))
    if ([System.IO.File]::Exists($fullOutputPath)) {
        # [NullString]::Value passes a real null (no backup file); a plain $null could arrive as "".
        [System.IO.File]::Replace($temporaryPath, $fullOutputPath, [NullString]::Value)
    } else {
        [System.IO.File]::Move($temporaryPath, $fullOutputPath)
    }
    Write-Output ("HOST_STATUS status=" + $status + " warn=" + $warnCount + " unknown=" + $unknownCount + " path=" + $fullOutputPath)
} catch {
    Write-Output ("HOST_STATUS_FAIL " + (ConvertTo-OneLine $_.Exception.Message))
}
exit 0
