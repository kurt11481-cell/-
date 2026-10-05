[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$PythonPath = "",
    [string]$OutputRoot = "",
    [string]$AttemptOutputRoot = "",
    [string]$RunId = "",
    [string]$AttemptId = ""
)

$ErrorActionPreference = "Stop"
$expectedTaskName = "GuardedPortfolio-SEC-Shadow-v0.1"
$attemptStartedAt = [DateTimeOffset]::UtcNow.ToString("o")
if ([string]::IsNullOrWhiteSpace($AttemptId)) {
    $AttemptId = "sec-scheduled-attempt-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffffffZ")
}
if ($AttemptId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$') { throw "ATTEMPT_ID_INVALID" }

$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$contractPath = Join-Path $resolvedRepository "manage-us-stock-strategy\assets\sec-scheduled-shadow-contract-v0.1.json"
$preflightPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\sec_scheduled_shadow_preflight.ps1"
$intakePath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\sec_official_event_intake.py"
$postprocessorPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\sec_scheduled_shadow.py"
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $resolvedRepository "workspace\outputs\official-event-intake\sec"
}
if ([string]::IsNullOrWhiteSpace($AttemptOutputRoot)) {
    $AttemptOutputRoot = Join-Path $resolvedRepository "workspace\outputs\official-event-intake\sec-scheduled-attempts"
}

function ConvertTo-LowerBoolean {
    param([bool]$Value)
    if ($Value) { return "true" }
    return "false"
}

function Get-AttemptArtifactPath {
    $dateDirectory = [DateTimeOffset]::Parse($attemptStartedAt).UtcDateTime.ToString("yyyy-MM-dd")
    Join-Path (Join-Path (Join-Path $AttemptOutputRoot $dateDirectory) $AttemptId) "scheduled-attempt.json"
}

function Test-AttemptPathCollision {
    $path = Get-AttemptArtifactPath
    $directory = Split-Path -Parent $path
    (Test-Path -LiteralPath $directory) -or (Test-Path -LiteralPath $path)
}

function Write-AttemptCollision {
    [ordered]@{
        SCHEDULE_STATUS = "RUN_COLLISION"
        ATTEMPT_RESULT = "BLOCKED"
        FAILURE_CODE = "RUN_COLLISION"
        FRESHNESS_STATUS = "NOT_AVAILABLE"
        LAST_KNOWN_RUN_ID = $null
        NETWORK_STARTED = $false
        SEC_RUNNER_INVOKED = $false
        TASK_MUTATION = $false
        USER_AGENT_SOURCE = "ENVIRONMENT_VARIABLE"
        USER_AGENT_VALUE = "REDACTED"
        ATTEMPT_ID = $AttemptId
        ORDER_AUTHORITY = $false
        EXECUTION_QUANTITY = $null
        AUTOMATIC_ORDER = $false
    } | ConvertTo-Json -Compress | Write-Output
}

function Get-CanonicalWatchlist {
    $rulesPath = Join-Path $resolvedRepository "manage-us-stock-strategy\assets\sec-official-event-intake-rules-v0.1.json"
    try {
        $rules = Get-Content -Raw -LiteralPath $rulesPath -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
        $symbols = @($rules.corporate_watchlist)
        if ($symbols.Count -eq 0 -or @($symbols | Where-Object { [string]::IsNullOrWhiteSpace([string]$_) }).Count -gt 0) { return $null }
        return ($symbols -join ",")
    } catch { return $null }
}

function Get-LatestFallbackSummary {
    $canonicalWatchlist = Get-CanonicalWatchlist
    if ($null -eq $canonicalWatchlist) { return $null }
    $candidates = @()
    if (Test-Path -LiteralPath $OutputRoot -PathType Container) {
        foreach ($path in Get-ChildItem -LiteralPath $OutputRoot -Filter "scheduled-dashboard.json" -File -Recurse -ErrorAction SilentlyContinue) {
            try {
                $value = Get-Content -Raw -LiteralPath $path.FullName | ConvertFrom-Json -ErrorAction Stop
                if (
                    $value.schema_version -eq "0.1" -and
                    $value.source -eq "SEC" -and
                    $value.freshness_status -eq "CURRENT_RUN" -and
                    ([string]::IsNullOrWhiteSpace($RunId) -or $value.run_id -ne $RunId) -and
                    [int]$value.lookback_days -eq 7 -and
                    $value.pipeline_version -eq "0.1" -and
                    ($value.watchlist -join ",") -eq $canonicalWatchlist -and
                    $value.pipeline_status -in @("PASS", "PARTIAL")
                ) { $candidates += $value }
            } catch { continue }
        }
    }
    if ($candidates.Count -eq 0) { return $null }
    $candidates | Sort-Object { [DateTimeOffset]::Parse($_.decision_as_of) } -Descending | Select-Object -First 1
}

function Write-FallbackAttempt {
    param(
        [string]$FailureCode,
        [string]$AttemptResult,
        [bool]$NetworkStarted,
        [Nullable[int]]$RunnerExitCode
    )
    $path = Get-AttemptArtifactPath
    $directory = Split-Path -Parent $path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $lastKnown = Get-LatestFallbackSummary
    $attempt = [ordered]@{
        schema_version = "0.1"
        attempt_id = $AttemptId
        task_name = $expectedTaskName
        started_at = $attemptStartedAt
        finished_at = [DateTimeOffset]::UtcNow.ToString("o")
        attempt_result = $AttemptResult
        failure_code = $FailureCode
        freshness_status = if ($null -eq $lastKnown) { "BASELINE_ONLY" } else { "LAST_KNOWN" }
        current_run_id = $null
        last_known_run_id = if ($null -eq $lastKnown) { $null } else { $lastKnown.run_id }
        last_known_run_as_of = if ($null -eq $lastKnown) { $null } else { $lastKnown.decision_as_of }
        diff_status = if ($null -eq $lastKnown) { "BASELINE_ONLY" } else { "PASS" }
        network_started = $NetworkStarted
        sec_live_request_count_if_known = $null
        runner_exit_code = $RunnerExitCode
        scheduler_mode = "SCHEDULED_SHADOW"
        lookback_days = 7
        user_agent_configured = $preflight.ProcessUserAgent -eq "CONFIGURED"
        persistent_user_agent_configured = $preflight.PersistentUserAgent -eq "CONFIGURED"
        timezone_id = $preflight.TimezoneId
        timezone_preflight_status = $preflight.TimezonePreflight
        portfolio_context_status = "NOT_ACCESSED_BY_SCHEDULED_ATTEMPT"
        order_authority = $false
        execution_quantity = $null
        automatic_order = $false
    }
    $json = ($attempt | ConvertTo-Json -Depth 8) + [Environment]::NewLine
    $stream = [System.IO.FileStream]::new($path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
        $writer = [System.IO.StreamWriter]::new($stream, [System.Text.UTF8Encoding]::new($false))
        try { $writer.Write($json) } finally { $writer.Dispose() }
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
    }
    $path
}

function Write-SanitizedFailure {
    param(
        [string]$Code,
        [string]$AttemptResult,
        [bool]$NetworkStarted,
        [Nullable[int]]$RunnerExitCode
    )
    $attemptPath = Get-AttemptArtifactPath
    if (Test-AttemptPathCollision) {
        Write-AttemptCollision
        exit 3
    }
    if (-not (Test-Path -LiteralPath $attemptPath -PathType Leaf)) {
        $writtenByPython = $false
        if (
            -not [string]::IsNullOrWhiteSpace($PythonPath) -and
            (Test-Path -LiteralPath $PythonPath -PathType Leaf) -and
            (Test-Path -LiteralPath $postprocessorPath -PathType Leaf)
        ) {
            $arguments = @(
                $postprocessorPath,
                "--output-root", $OutputRoot,
                "--attempt-output-root", $AttemptOutputRoot,
                "--attempt-id", $AttemptId,
                "--attempt-started-at", $attemptStartedAt,
                "--attempt-result", $AttemptResult,
                "--failure-code", $Code,
                "--network-started", (ConvertTo-LowerBoolean $NetworkStarted),
                "--user-agent-configured", (ConvertTo-LowerBoolean ($preflight.ProcessUserAgent -eq "CONFIGURED")),
                "--persistent-user-agent-configured", (ConvertTo-LowerBoolean ($preflight.PersistentUserAgent -eq "CONFIGURED")),
                "--timezone-id", $preflight.TimezoneId,
                "--timezone-preflight-status", $preflight.TimezonePreflight
            )
            if (-not [string]::IsNullOrWhiteSpace($RunId)) { $arguments += @("--exclude-run-id", $RunId) }
            if ($null -ne $RunnerExitCode) { $arguments += @("--runner-exit-code", [string]$RunnerExitCode) }
            & $PythonPath @arguments | Out-Null
            $writtenByPython = $LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $attemptPath -PathType Leaf)
        }
        if (-not $writtenByPython -and -not (Test-Path -LiteralPath $attemptPath -PathType Leaf)) {
            Write-FallbackAttempt -FailureCode $Code -AttemptResult $AttemptResult -NetworkStarted $NetworkStarted -RunnerExitCode $RunnerExitCode | Out-Null
        }
    }
    $attempt = Get-Content -Raw -LiteralPath $attemptPath | ConvertFrom-Json
    [ordered]@{
        SCHEDULE_STATUS = $Code
        ATTEMPT_RESULT = $AttemptResult
        FRESHNESS_STATUS = $attempt.freshness_status
        LAST_KNOWN_RUN_ID = $attempt.last_known_run_id
        NETWORK_STARTED = $NetworkStarted
        USER_AGENT_SOURCE = "ENVIRONMENT_VARIABLE"
        USER_AGENT_VALUE = "REDACTED"
        ATTEMPT_ID = $AttemptId
        ORDER_AUTHORITY = $false
        EXECUTION_QUANTITY = $null
        AUTOMATIC_ORDER = $false
    } | ConvertTo-Json -Compress | Write-Output
}

if (Test-AttemptPathCollision) {
    Write-AttemptCollision
    exit 3
}

$rawTimezone = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
$rawPersistentUserAgent = [Environment]::GetEnvironmentVariable("SEC_USER_AGENT", [EnvironmentVariableTarget]::User)
$preflight = [pscustomobject]@{
    TimezoneId = $rawTimezone
    TimezonePreflight = if ($rawTimezone -eq "Korea Standard Time") { "PASS" } else { "FAIL" }
    ProcessUserAgent = if ([string]::IsNullOrWhiteSpace($env:SEC_USER_AGENT)) { "NOT_CONFIGURED" } else { "CONFIGURED" }
    PersistentUserAgent = if ([string]::IsNullOrWhiteSpace($rawPersistentUserAgent)) { "NOT_CONFIGURED" } else { "CONFIGURED" }
}
if (Test-Path -LiteralPath $preflightPath -PathType Leaf) {
    . $preflightPath
    $preflight = Get-SecScheduledShadowSystemPreflight
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $pythonCandidates = @(
        (Join-Path $resolvedRepository ".venv\Scripts\python.exe"),
        (Join-Path $resolvedRepository "venv\Scripts\python.exe")
    )
    $PythonPath = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) { $pythonCommand = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $pythonCommand) { $PythonPath = $pythonCommand.Source }
    }
}

if ($preflight.TimezonePreflight -ne "PASS") {
    Write-SanitizedFailure -Code "WINDOWS_TIMEZONE_MISMATCH" -AttemptResult "BLOCKED" -NetworkStarted $false -RunnerExitCode $null
    exit 2
}
if ($preflight.ProcessUserAgent -ne "CONFIGURED") {
    Write-SanitizedFailure -Code "SEC_USER_AGENT_REQUIRED" -AttemptResult "BLOCKED" -NetworkStarted $false -RunnerExitCode $null
    exit 2
}
if ($preflight.PersistentUserAgent -ne "CONFIGURED") {
    Write-SanitizedFailure -Code "SEC_USER_AGENT_USER_ENV_REQUIRED" -AttemptResult "BLOCKED" -NetworkStarted $false -RunnerExitCode $null
    exit 2
}
if (
    -not (Test-Path -LiteralPath $contractPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $intakePath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $postprocessorPath -PathType Leaf)
) {
    Write-SanitizedFailure -Code "RUNNER_NOT_FOUND" -AttemptResult "BLOCKED" -NetworkStarted $false -RunnerExitCode $null
    exit 3
}
if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-SanitizedFailure -Code "PYTHON_RUNTIME_NOT_FOUND" -AttemptResult "BLOCKED" -NetworkStarted $false -RunnerExitCode $null
    exit 3
}

$contract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json
if ($contract.schema_version -ne "0.1" -or $contract.task_name -ne $expectedTaskName -or [int]$contract.lookback_days -ne 7) {
    Write-SanitizedFailure -Code "PROCESS_ERROR" -AttemptResult "BLOCKED" -NetworkStarted $false -RunnerExitCode $null
    exit 3
}

if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = "sec-scheduled-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffffffZ")
}
$intakeArguments = @($intakePath, "--output-root", $OutputRoot, "--lookback-days", ([string][int]$contract.lookback_days), "--run-id", $RunId)
$intakeOutput = @(& $PythonPath @intakeArguments 2>&1)
$intakeExitCode = $LASTEXITCODE
$intakeOutput | ForEach-Object { $_.ToString() } | Write-Output

$requestCount = $null
foreach ($line in $intakeOutput) {
    try {
        $parsed = $line.ToString() | ConvertFrom-Json -ErrorAction Stop
        if ($null -ne $parsed.http_request_count) { $requestCount = [int]$parsed.http_request_count }
    } catch { continue }
}

if ($intakeExitCode -ne 0) {
    $failureCode = "PROCESS_ERROR"
    foreach ($line in $intakeOutput) {
        try {
            $parsed = $line.ToString() | ConvertFrom-Json -ErrorAction Stop
            if ($parsed.code -in @(
                "SEC_USER_AGENT_REQUIRED", "SEC_ACCESS_BLOCKED", "SEC_RATE_LIMITED",
                "SEC_SOURCE_INVALID", "SEC_IDENTITY_CONFLICT", "NETWORK_SCOPE_VIOLATION", "RUN_COLLISION"
            )) { $failureCode = $parsed.code }
        } catch { continue }
    }
    Write-SanitizedFailure -Code $failureCode -AttemptResult "FAIL" -NetworkStarted $true -RunnerExitCode $intakeExitCode
    exit $intakeExitCode
}

$postprocessorArguments = @(
    $postprocessorPath,
    "--output-root", $OutputRoot,
    "--current-run-id", $RunId,
    "--attempt-output-root", $AttemptOutputRoot,
    "--attempt-id", $AttemptId,
    "--attempt-started-at", $attemptStartedAt,
    "--attempt-result", "PASS",
    "--network-started", "true",
    "--user-agent-configured", "true",
    "--persistent-user-agent-configured", "true",
    "--timezone-id", $preflight.TimezoneId,
    "--timezone-preflight-status", $preflight.TimezonePreflight,
    "--runner-exit-code", "0"
)
if ($null -ne $requestCount) { $postprocessorArguments += @("--sec-live-request-count", [string]$requestCount) }
$postprocessorOutput = @(& $PythonPath @postprocessorArguments 2>&1)
$postprocessorExitCode = $LASTEXITCODE
$postprocessorOutput | ForEach-Object { $_.ToString() } | Write-Output
if ($postprocessorExitCode -ne 0 -or -not (Test-Path -LiteralPath (Get-AttemptArtifactPath) -PathType Leaf)) {
    Write-SanitizedFailure -Code "PROCESS_ERROR" -AttemptResult "FAIL" -NetworkStarted $true -RunnerExitCode 3
    exit 3
}
exit 0
