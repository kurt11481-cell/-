[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [string]$RepositoryRoot = ""
)

# t2-rc M2: registers one Windows task (same pattern as manage-us-stock-strategy\scripts\register_auto_core_task.ps1:
# Interactive logon, Limited run level, start when available, no wake, one instance). Local time must be Korea
# Standard Time.
#   InvestmentV2-T2rcCheck  Tuesday-Saturday 08:40  docs\claude\t2rc-check-run.ps1 (limit 15 min)
# Only this task name is created or overwritten. The task runs the read-only independent calculator; it never places,
# changes or cancels an order and writes only workspace\outputs\auto-core\<day>\t2rc-check.json,
# LATEST_T2RC_CHECK.json and its log. The user runs this script once after the Judge PASS and the approval;
# -PlanOnly prints the plan without registering. Registering does not run the task.

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$wrapperPath = Join-Path $resolvedRepository "docs\claude\t2rc-check-run.ps1"
$task = [ordered]@{ Name = "InvestmentV2-T2rcCheck"; TriggerTime = "08:40"; LimitMinutes = 15;
                    Description = "Investment_V2 t2-rc M2: independent recomputation of the decide circuit set and tickets (read-only, no order authority)" }

if (-not (Test-Path -LiteralPath $wrapperPath -PathType Leaf)) { throw "WRAPPER_NOT_FOUND" }
$timezoneId = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
$timezoneReady = $timezoneId -eq "Korea Standard Time"

function Get-TaskExistence {
    param([string]$TaskName)
    if ($null -eq (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) { return "UNKNOWN" }
    try {
        $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($null -eq $existing) { return "NO" }
        return "YES"
    } catch {
        return "UNKNOWN"
    }
}

function Write-TaskPlan {
    param([string]$Mode, [string]$ExistsBefore, [string]$ExistsAfter)
    ([ordered]@{
        TASK_NAME = $task.Name
        MODE = $Mode
        TRIGGER = "Tue-Sat " + $task.TriggerTime + " local (KST)"
        WINDOWS_TIMEZONE = $timezoneId
        TIMEZONE_READY = $timezoneReady
        RUN_LEVEL = "LIMITED"
        LOGON_TYPE = "INTERACTIVE"
        START_WHEN_AVAILABLE = $true
        WAKE_COMPUTER = $false
        EXECUTION_LIMIT_MINUTES = $task.LimitMinutes
        MULTIPLE_INSTANCES = "IGNORE_NEW"
        ACTION = $wrapperPath
        TASK_EXISTS_BEFORE = $ExistsBefore
        TASK_EXISTS_AFTER = $ExistsAfter
        ORDER_AUTHORITY = $false
    }).GetEnumerator() | ForEach-Object { "{0} = {1}" -f $_.Key, $_.Value }
}

$before = Get-TaskExistence -TaskName $task.Name
if ($PlanOnly) {
    Write-TaskPlan -Mode "PLAN_ONLY" -ExistsBefore $before -ExistsAfter $before
    exit 0
}
if (-not $timezoneReady) {
    Write-TaskPlan -Mode "APPLY_BLOCKED_TIMEZONE" -ExistsBefore $before -ExistsAfter $before
    exit 2
}

$powerShellExecutable = (Get-Command powershell.exe -ErrorAction Stop).Source
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
# Hidden window: keyboard Ctrl+C in the visible window stopped the decide run on 2026-10-21.
$actionArguments = '-WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RepositoryRoot "{1}"' -f $wrapperPath, $resolvedRepository
$action = New-ScheduledTaskAction -Execute $powerShellExecutable -Argument $actionArguments -WorkingDirectory $resolvedRepository
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Tuesday, Wednesday, Thursday, Friday, Saturday -At $task.TriggerTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun:$false `
    -ExecutionTimeLimit (New-TimeSpan -Minutes $task.LimitMinutes) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $currentIdentity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask `
    -TaskName $task.Name `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description $task.Description `
    -Force | Out-Null
Write-TaskPlan -Mode "APPLY" -ExistsBefore $before -ExistsAfter (Get-TaskExistence -TaskName $task.Name)
exit 0
