[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [string]$RepositoryRoot = ""
)

# C1: registers the Windows task of the read-only host status check (same pattern as
# register_auto_core_task.ps1: Interactive logon, Limited run level, start when available, no wake,
# one instance). Local time must be Korea Standard Time.
#   InvestmentV2-HostStatus  Tuesday-Saturday 05:50  host_status.ps1  (limit 10 min)
# Only this one task name is created or overwritten; the auto-core tasks are not touched. The task runs
# host_status.ps1 only, which reads host settings and writes workspace\outputs\host-status\LATEST.json.
# The user runs this script once; -PlanOnly prints the plan without registering. Registering does not run the task.

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$scriptPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\host_status.ps1"
$tasks = @(
    [ordered]@{ Name = "InvestmentV2-HostStatus"; Command = "host_status"; TriggerTime = "05:50"; LimitMinutes = 10;
                Description = "Investment_V2 host status check (read-only): core task settings, automatic logon, sleep, update active hours, pending reboot; changes no setting; no order authority" }
)

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "HOST_STATUS_SCRIPT_NOT_FOUND" }
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
    param($Task, [string]$Mode, [string]$ExistsBefore, [string]$ExistsAfter)
    ([ordered]@{
        TASK_NAME = $Task.Name
        MODE = $Mode
        COMMAND = $Task.Command
        TRIGGER = "Tue-Sat " + $Task.TriggerTime + " local (KST)"
        WINDOWS_TIMEZONE = $timezoneId
        TIMEZONE_READY = $timezoneReady
        RUN_LEVEL = "LIMITED"
        LOGON_TYPE = "INTERACTIVE"
        START_WHEN_AVAILABLE = $true
        WAKE_COMPUTER = $false
        EXECUTION_LIMIT_MINUTES = $Task.LimitMinutes
        MULTIPLE_INSTANCES = "IGNORE_NEW"
        ACTION = $scriptPath
        TASK_EXISTS_BEFORE = $ExistsBefore
        TASK_EXISTS_AFTER = $ExistsAfter
        ORDER_AUTHORITY = $false
    }).GetEnumerator() | ForEach-Object { "{0} = {1}" -f $_.Key, $_.Value }
}

$before = @{}
foreach ($task in $tasks) { $before[$task.Name] = Get-TaskExistence -TaskName $task.Name }
if ($PlanOnly) {
    foreach ($task in $tasks) { Write-TaskPlan -Task $task -Mode "PLAN_ONLY" -ExistsBefore $before[$task.Name] -ExistsAfter $before[$task.Name] }
    exit 0
}
if (-not $timezoneReady) {
    foreach ($task in $tasks) { Write-TaskPlan -Task $task -Mode "APPLY_BLOCKED_TIMEZONE" -ExistsBefore $before[$task.Name] -ExistsAfter $before[$task.Name] }
    exit 2
}

$powerShellExecutable = (Get-Command powershell.exe -ErrorAction Stop).Source
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
foreach ($task in $tasks) {
    $actionArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RepositoryRoot "{1}"' -f $scriptPath, $resolvedRepository
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
    Write-TaskPlan -Task $task -Mode "APPLY" -ExistsBefore $before[$task.Name] -ExistsAfter (Get-TaskExistence -TaskName $task.Name)
}
exit 0
