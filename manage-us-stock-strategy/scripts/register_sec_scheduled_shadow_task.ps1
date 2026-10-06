[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$SkipTaskQuery,
    [string]$RepositoryRoot = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$contractPath = Join-Path $resolvedRepository "manage-us-stock-strategy\assets\sec-scheduled-shadow-contract-v0.1.json"
$wrapperPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\run_sec_scheduled_shadow.ps1"
$preflightPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\sec_scheduled_shadow_preflight.ps1"
$contract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json

if (-not (Test-Path -LiteralPath $preflightPath -PathType Leaf)) { throw "PREFLIGHT_HELPER_NOT_FOUND" }
. $preflightPath

function Assert-ScheduleContract {
    param([object]$Value)
    if ($Value.schema_version -ne "0.1") { throw "CONTRACT_SCHEMA_VERSION_INVALID" }
    if ($Value.task_name -ne "GuardedPortfolio-SEC-Shadow-v0.1") { throw "TASK_NAME_INVALID" }
    if ($Value.timezone_assumption -ne "WINDOWS_LOCAL_ASIA_SEOUL") { throw "TIMEZONE_ASSUMPTION_INVALID" }
    if ([int]$Value.lookback_days -ne 7) { throw "LOOKBACK_DAYS_INVALID" }
    if (@($Value.triggers).Count -ne 2) { throw "TRIGGER_COUNT_INVALID" }
    $expectedA = "Monday,Tuesday,Wednesday,Thursday,Friday"
    $expectedB = "Tuesday,Wednesday,Thursday,Friday,Saturday"
    if (($Value.triggers[0].days_of_week -join ",") -ne $expectedA -or $Value.triggers[0].local_time -ne "22:00") {
        throw "TRIGGER_A_INVALID"
    }
    if (($Value.triggers[1].days_of_week -join ",") -ne $expectedB -or $Value.triggers[1].local_time -ne "12:30") {
        throw "TRIGGER_B_INVALID"
    }
    if ($Value.settings.logon_type -ne "INTERACTIVE" -or $Value.settings.run_level -ne "LIMITED") {
        throw "RUN_LEVEL_INVALID"
    }
    if (-not $Value.settings.start_when_available -or $Value.settings.wake_to_run) {
        throw "POWER_SETTINGS_INVALID"
    }
    if ([int]$Value.settings.execution_time_limit_minutes -ne 10) { throw "EXECUTION_LIMIT_INVALID" }
    if ($Value.settings.multiple_instances -ne "IGNORE_NEW") { throw "MULTIPLE_INSTANCES_INVALID" }
    if ($Value.user_agent.source -ne "ENVIRONMENT_VARIABLE" -or $Value.user_agent.variable_name -ne "SEC_USER_AGENT") {
        throw "USER_AGENT_CONTRACT_INVALID"
    }
    if ($Value.user_agent.plaintext_artifact_storage -or $Value.user_agent.plaintext_task_arguments) {
        throw "USER_AGENT_PLAINTEXT_CONTRACT_INVALID"
    }
}

function Get-TaskExistence {
    param([string]$TaskName)
    if ($SkipTaskQuery) { return "NOT_OBSERVED" }
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
    param(
        [string]$Mode,
        [string]$ExistsBefore,
        [string]$ExistsAfter,
        [bool]$Mutation,
        [object]$Preflight
    )
    ([ordered]@{
        TASK_NAME = $contract.task_name
        MODE = $Mode
        TRIGGER_A = "Mon-Fri 22:00 KST"
        TRIGGER_B = "Tue-Sat 12:30 KST"
        LOOKBACK_DAYS = [int]$contract.lookback_days
        TIMEZONE_ASSUMPTION = "Windows local time = Asia/Seoul"
        MULTIPLE_INSTANCES = $contract.settings.multiple_instances
        RUN_LEVEL = "NORMAL_USER"
        LOGON_TYPE = "RUN_ONLY_WHEN_USER_LOGGED_ON"
        START_WHEN_AVAILABLE = [bool]$contract.settings.start_when_available
        WAKE_COMPUTER = [bool]$contract.settings.wake_to_run
        EXECUTION_LIMIT = "10_MINUTES"
        WINDOWS_TIMEZONE = $Preflight.TimezoneDisplay
        TIMEZONE_PREFLIGHT = $Preflight.TimezonePreflight
        PROCESS_USER_AGENT = $Preflight.ProcessUserAgent
        USER_AGENT = $Preflight.ProcessUserAgent
        PERSISTENT_USER_AGENT = $Preflight.PersistentUserAgent
        PERSISTENT_USER_ENV = $Preflight.PersistentUserAgent
        NEW_LOGON_SESSION_REQUIRED_AFTER_CHANGE = $Preflight.NewLogonSessionRequiredAfterChange
        ACTIVATION_READY = [bool]$Preflight.ActivationReady
        FAILURE_CODE = if ($null -eq $Preflight.FailureCode) { "NONE" } else { $Preflight.FailureCode }
        USER_AGENT_VALUE = "REDACTED"
        TASK_EXISTS_BEFORE = $ExistsBefore
        TASK_EXISTS_AFTER = $ExistsAfter
        TASK_CREATED = if ($Mutation -and $ExistsBefore -eq "NO") { "YES" } else { "NO" }
        TASK_UPDATED = if ($Mutation -and $ExistsBefore -eq "YES") { "YES" } else { "NO" }
        TASK_DELETED = "NO"
        TASK_MUTATION = if ($Mutation) { "YES" } else { "NO" }
    }).GetEnumerator() | ForEach-Object {
        $displayValue = if ($_.Value -is [bool]) { $_.Value.ToString().ToUpperInvariant() } else { $_.Value.ToString() }
        "{0} = {1}" -f $_.Key, $displayValue
    }
}

Assert-ScheduleContract -Value $contract
$preflight = Get-SecScheduledShadowSystemPreflight

if (-not $Apply) {
    if (-not (Test-Path -LiteralPath $wrapperPath -PathType Leaf)) { throw "WRAPPER_NOT_FOUND" }
    $taskExistsBefore = Get-TaskExistence -TaskName $contract.task_name
    Write-TaskPlan `
        -Mode "PLAN_ONLY" `
        -ExistsBefore $taskExistsBefore `
        -ExistsAfter $taskExistsBefore `
        -Mutation $false `
        -Preflight $preflight
    exit 0
}

if (-not $preflight.ActivationReady) {
    Write-TaskPlan `
        -Mode "APPLY_BLOCKED" `
        -ExistsBefore "NOT_OBSERVED" `
        -ExistsAfter "NOT_OBSERVED" `
        -Mutation $false `
        -Preflight $preflight
    exit 2
}

if (-not (Test-Path -LiteralPath $wrapperPath -PathType Leaf)) { throw "WRAPPER_NOT_FOUND" }
$taskExistsBefore = Get-TaskExistence -TaskName $contract.task_name

$powerShellExecutable = (Get-Command powershell.exe -ErrorAction Stop).Source
$actionArguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RepositoryRoot "{1}"' -f $wrapperPath, $resolvedRepository
$action = New-ScheduledTaskAction -Execute $powerShellExecutable -Argument $actionArguments -WorkingDirectory $resolvedRepository
$triggerA = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At "22:00"
$triggerB = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Tuesday, Wednesday, Thursday, Friday, Saturday -At "12:30"
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun:$false `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $currentIdentity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask `
    -TaskName $contract.task_name `
    -Action $action `
    -Trigger @($triggerA, $triggerB) `
    -Settings $settings `
    -Principal $principal `
    -Description "Read-only SEC Scheduled Shadow v0.1; no order authority" `
    -Force | Out-Null
$taskExistsAfter = Get-TaskExistence -TaskName $contract.task_name
Write-TaskPlan `
    -Mode "APPLY" `
    -ExistsBefore $taskExistsBefore `
    -ExistsAfter $taskExistsAfter `
    -Mutation $true `
    -Preflight $preflight
