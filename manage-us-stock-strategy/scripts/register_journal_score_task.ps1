[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [string]$RepositoryRoot = ""
)

# f-evo-loop step 1: registers the Windows task of the weekly journal scoring (same pattern as the other task
# registration scripts: Interactive logon, Limited run level, start when available, no wake, one instance).
# Local time must be Korea Standard Time.
#   InvestmentV2-JournalScore  weekly, Sunday 09:20  run_journal_score.ps1  (limit 15 min)
# Only this one task name is created or overwritten; no other task is read or changed. The task runs
# run_journal_score.ps1 only, which runs the read-only scorer with --learning and writes under
# workspace\outputs\journal-scores. The user runs this script once; -PlanOnly prints the plan without registering.
# Registering does not run the task.

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$scriptPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\run_journal_score.ps1"
$tasks = @(
    [ordered]@{ Name = "InvestmentV2-JournalScore"; Command = "run_journal_score"; TriggerDay = "Sunday"; TriggerTime = "09:20"; LimitMinutes = 15;
                Description = "Investment_V2 weekly journal scoring with the learning block (display only, writes journal-scores only, no order authority)" }
)

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "JOURNAL_SCORE_SCRIPT_NOT_FOUND" }
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
        TRIGGER = "Weekly " + $Task.TriggerDay + " " + $Task.TriggerTime + " local (KST)"
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
    $trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $task.TriggerTime
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
