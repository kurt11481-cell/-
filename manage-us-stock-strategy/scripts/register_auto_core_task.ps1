[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [string]$RepositoryRoot = ""
)

# Redesign T1 F5: registers the Windows task InvestmentV2-AutoCore (same pattern as
# register_sec_scheduled_shadow_task.ps1: Interactive logon, Limited run level, start when available,
# no wake, one instance). Trigger: Tuesday-Saturday 06:15 local time, which must be Korea Standard Time
# (06:15 KST is after the U.S. regular close in both summer and winter time).
# The task runs run_auto_core.ps1 only. It never places, changes or cancels an order.
# The user runs this script once; -PlanOnly prints the plan without registering.

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$taskName = "InvestmentV2-AutoCore"
$wrapperPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\run_auto_core.ps1"
$triggerTime = "06:15"
$executionLimitMinutes = 60

if (-not (Test-Path -LiteralPath $wrapperPath -PathType Leaf)) { throw "WRAPPER_NOT_FOUND" }
$timezoneId = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
$timezoneReady = $timezoneId -eq "Korea Standard Time"

function Get-TaskExistence {
    if ($null -eq (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) { return "UNKNOWN" }
    try {
        $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($null -eq $existing) { return "NO" }
        return "YES"
    } catch {
        return "UNKNOWN"
    }
}

function Write-TaskPlan {
    param([string]$Mode, [string]$ExistsBefore, [string]$ExistsAfter)
    ([ordered]@{
        TASK_NAME = $taskName
        MODE = $Mode
        TRIGGER = "Tue-Sat " + $triggerTime + " local (KST)"
        WINDOWS_TIMEZONE = $timezoneId
        TIMEZONE_READY = $timezoneReady
        RUN_LEVEL = "LIMITED"
        LOGON_TYPE = "INTERACTIVE"
        START_WHEN_AVAILABLE = $true
        WAKE_COMPUTER = $false
        EXECUTION_LIMIT_MINUTES = $executionLimitMinutes
        MULTIPLE_INSTANCES = "IGNORE_NEW"
        ACTION = $wrapperPath
        TASK_EXISTS_BEFORE = $ExistsBefore
        TASK_EXISTS_AFTER = $ExistsAfter
        ORDER_AUTHORITY = $false
    }).GetEnumerator() | ForEach-Object { "{0} = {1}" -f $_.Key, $_.Value }
}

$existsBefore = Get-TaskExistence
if ($PlanOnly) {
    Write-TaskPlan -Mode "PLAN_ONLY" -ExistsBefore $existsBefore -ExistsAfter $existsBefore
    exit 0
}
if (-not $timezoneReady) {
    Write-TaskPlan -Mode "APPLY_BLOCKED_TIMEZONE" -ExistsBefore $existsBefore -ExistsAfter $existsBefore
    exit 2
}

$powerShellExecutable = (Get-Command powershell.exe -ErrorAction Stop).Source
$actionArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RepositoryRoot "{1}"' -f $wrapperPath, $resolvedRepository
$action = New-ScheduledTaskAction -Execute $powerShellExecutable -Argument $actionArguments -WorkingDirectory $resolvedRepository
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Tuesday, Wednesday, Thursday, Friday, Saturday -At $triggerTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun:$false `
    -ExecutionTimeLimit (New-TimeSpan -Minutes $executionLimitMinutes) `
    -MultipleInstances IgnoreNew
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $currentIdentity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Investment_V2 auto-core (redesign T1): read-only Kiwoom reads, reconciliation under invariants, close histories, exposure review; no order authority" `
    -Force | Out-Null
Write-TaskPlan -Mode "APPLY" -ExistsBefore $existsBefore -ExistsAfter (Get-TaskExistence)
exit 0
