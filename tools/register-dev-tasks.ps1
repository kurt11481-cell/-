# register-dev-tasks.ps1 - registers the two Windows tasks of the dev pipeline (redesign T3).
#
#   InvestmentV2-DocsCommit : daily 23:30 local time (KST), limit 15 minutes, runs tools\run-docs-commit.ps1
#   InvestmentV2-DevQueue   : every 15 minutes without end, limit 6 hours, runs tools\dev-queue.ps1
#
# Same pattern as manage-us-stock-strategy\scripts\register_auto_core_task.ps1: Interactive logon,
# Limited run level, start when available, no wake, one instance (IgnoreNew); applying is refused unless
# Windows uses Korea Standard Time. Only these two task names are created or overwritten; no other task
# is read for change, changed or deleted. Tasks start hidden through conhost.exe --headless when it
# exists (no console window); otherwise powershell.exe -WindowStyle Hidden (a short flash can remain).
# The user runs this script once; -PlanOnly prints the plan without registering. Nothing here starts
# either task.
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as the ANSI code page.

[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [string]$RepositoryRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$docsTaskName = "InvestmentV2-DocsCommit"
$queueTaskName = "InvestmentV2-DevQueue"
$docsScript = Join-Path $resolvedRepository "tools\run-docs-commit.ps1"
$queueScript = Join-Path $resolvedRepository "tools\dev-queue.ps1"
$docsTime = "23:30"
$docsLimitMinutes = 15
$queueIntervalMinutes = 15
$queueLimitHours = 6

foreach ($path in @($docsScript, $queueScript)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw ("SCRIPT_NOT_FOUND " + $path) }
}
$timezoneId = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
$timezoneReady = $timezoneId -eq "Korea Standard Time"
$powerShellExecutable = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$conhost = Join-Path $env:SystemRoot "System32\conhost.exe"
$launcher = "POWERSHELL_HIDDEN"
if (Test-Path -LiteralPath $conhost -PathType Leaf) { $launcher = "CONHOST_HEADLESS" }

function Get-TaskExistence([string]$Name) {
    if ($null -eq (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) { return "UNKNOWN" }
    try {
        $existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
        if ($null -eq $existing) { return "NO" }
        return "YES"
    } catch {
        return "UNKNOWN"
    }
}

function Get-ActionParts([string]$ScriptPath) {
    $psArguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $ScriptPath + '"'
    if ($launcher -eq "CONHOST_HEADLESS") {
        return @($conhost, ('--headless "' + $powerShellExecutable + '" ' + $psArguments))
    }
    return @($powerShellExecutable, $psArguments)
}

function New-TaskPlan([string]$Name, [string]$ScriptPath, [string]$TriggerText, [int]$LimitMinutes, $Trigger) {
    $parts = Get-ActionParts $ScriptPath
    return [pscustomobject]@{
        Name = $Name
        Script = $ScriptPath
        TriggerText = $TriggerText
        Trigger = $Trigger
        LimitMinutes = $LimitMinutes
        Execute = $parts[0]
        Arguments = $parts[1]
    }
}

$docsTrigger = New-ScheduledTaskTrigger -Daily -At $docsTime
$queueTrigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).Date) -RepetitionInterval (New-TimeSpan -Minutes $queueIntervalMinutes)
$plans = @(
    (New-TaskPlan $docsTaskName $docsScript ("daily " + $docsTime + " local (KST)") $docsLimitMinutes $docsTrigger),
    (New-TaskPlan $queueTaskName $queueScript ("every " + $queueIntervalMinutes + " minutes, no end") ($queueLimitHours * 60) $queueTrigger)
)

function Write-TaskPlan([string]$Mode, $Plan, [string]$ExistsBefore, [string]$ExistsAfter) {
    $repetition = ""
    if ($null -ne $Plan.Trigger.Repetition -and $Plan.Trigger.Repetition.Interval) {
        $repetition = "interval=" + $Plan.Trigger.Repetition.Interval + " duration=" + $(if ($Plan.Trigger.Repetition.Duration) { $Plan.Trigger.Repetition.Duration } else { "INDEFINITE" })
    }
    ([ordered]@{
        TASK_NAME = $Plan.Name
        MODE = $Mode
        TRIGGER = $Plan.TriggerText
        TRIGGER_START_BOUNDARY = $Plan.Trigger.StartBoundary
        TRIGGER_REPETITION = $repetition
        WINDOWS_TIMEZONE = $timezoneId
        TIMEZONE_READY = $timezoneReady
        RUN_LEVEL = "LIMITED"
        LOGON_TYPE = "INTERACTIVE"
        START_WHEN_AVAILABLE = $true
        WAKE_COMPUTER = $false
        EXECUTION_LIMIT_MINUTES = $Plan.LimitMinutes
        MULTIPLE_INSTANCES = "IGNORE_NEW"
        LAUNCHER = $launcher
        EXECUTE = $Plan.Execute
        ARGUMENTS = $Plan.Arguments
        TASK_EXISTS_BEFORE = $ExistsBefore
        TASK_EXISTS_AFTER = $ExistsAfter
        ORDER_AUTHORITY = $false
    }).GetEnumerator() | ForEach-Object { "{0} = {1}" -f $_.Key, $_.Value }
    ""
}

$before = @{}
foreach ($plan in $plans) { $before[$plan.Name] = Get-TaskExistence $plan.Name }
if ($PlanOnly) {
    foreach ($plan in $plans) { Write-TaskPlan "PLAN_ONLY" $plan $before[$plan.Name] $before[$plan.Name] }
    exit 0
}
if (-not $timezoneReady) {
    foreach ($plan in $plans) { Write-TaskPlan "APPLY_BLOCKED_TIMEZONE" $plan $before[$plan.Name] $before[$plan.Name] }
    exit 2
}

$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $currentIdentity -LogonType Interactive -RunLevel Limited
foreach ($plan in $plans) {
    $action = New-ScheduledTaskAction -Execute $plan.Execute -Argument $plan.Arguments -WorkingDirectory $resolvedRepository
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -WakeToRun:$false `
        -ExecutionTimeLimit (New-TimeSpan -Minutes $plan.LimitMinutes) `
        -MultipleInstances IgnoreNew
    Register-ScheduledTask `
        -TaskName $plan.Name `
        -Action $action `
        -Trigger $plan.Trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Investment_V2 dev pipeline (redesign T3); no order authority" `
        -Force | Out-Null
    Write-TaskPlan "APPLY" $plan $before[$plan.Name] (Get-TaskExistence $plan.Name)
}
exit 0
