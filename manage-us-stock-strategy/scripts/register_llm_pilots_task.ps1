[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [string]$RepositoryRoot = ""
)

# API pilots: registers the Windows task of the pilot runner (same pattern as the other task registration
# scripts: Interactive logon, Limited run level, start when available, no wake, one instance).
# Local time must be Korea Standard Time.
#   InvestmentV2-LLMPilots  daily 00:00, repeat every 10 minutes for 1 day  run_llm_pilots.ps1  (limit 30 min)
# Only this one task name is created or overwritten; no other task is read or changed. The task runs
# run_llm_pilots.ps1 only, which runs llm_runner.py and writes under workspace\outputs\llm. Which pilot runs is
# decided by the committed switch file docs/claude/llm-pilots-schedule.json (all off until the user approves one).
# The user runs this script once; -PlanOnly prints the plan without registering. Registering does not run the task.

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$scriptPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\run_llm_pilots.ps1"
$tasks = @(
    [ordered]@{ Name = "InvestmentV2-LLMPilots"; Command = "llm_pilots"; LimitMinutes = 30;
                Description = "Investment_V2 API pilots runner every 10 minutes (display only, writes workspace\outputs\llm only, no order authority)" }
)

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "LLM_PILOTS_RUNNER_NOT_FOUND" }
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
        TRIGGER = "Daily 00:00 local (KST), repeat every 10 minutes for 1 day"
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
    # Hidden window: keyboard Ctrl+C in the visible window stopped the decide run on 2026-10-21.
    $actionArguments = '-WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RepositoryRoot "{1}"' -f $scriptPath, $resolvedRepository
    $action = New-ScheduledTaskAction -Execute $powerShellExecutable -Argument $actionArguments -WorkingDirectory $resolvedRepository
    $trigger = New-ScheduledTaskTrigger -Daily -At "00:00"
    $trigger.Repetition = (New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 1)).Repetition
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
