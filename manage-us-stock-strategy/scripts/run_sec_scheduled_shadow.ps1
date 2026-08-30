[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$PythonPath = "",
    [string]$OutputRoot = "",
    [string]$RunId = ""
)

$ErrorActionPreference = "Stop"

function Write-SanitizedFailure {
    param([string]$Code)
    [ordered]@{
        SCHEDULE_STATUS = $Code
        USER_AGENT_SOURCE = "ENVIRONMENT_VARIABLE"
        USER_AGENT_VALUE = "REDACTED"
        ORDER_AUTHORITY = $false
        EXECUTION_QUANTITY = $null
        AUTOMATIC_ORDER = $false
    } | ConvertTo-Json -Compress | Write-Output
}

if ([string]::IsNullOrWhiteSpace($env:SEC_USER_AGENT)) {
    Write-SanitizedFailure -Code "SEC_USER_AGENT_REQUIRED"
    exit 2
}

$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$contractPath = Join-Path $resolvedRepository "manage-us-stock-strategy\assets\sec-scheduled-shadow-contract-v0.1.json"
$intakePath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\sec_official_event_intake.py"
$postprocessorPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\sec_scheduled_shadow.py"
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $resolvedRepository "workspace\outputs\official-event-intake\sec"
}

foreach ($requiredPath in @($contractPath, $intakePath, $postprocessorPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        Write-SanitizedFailure -Code "PROCESS_ERROR"
        exit 3
    }
}

$contract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json
if ($contract.schema_version -ne "0.1" -or [int]$contract.lookback_days -ne 7) {
    Write-SanitizedFailure -Code "PROCESS_ERROR"
    exit 3
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $pythonCandidates = @(
        (Join-Path $resolvedRepository ".venv\Scripts\python.exe"),
        (Join-Path $resolvedRepository "venv\Scripts\python.exe")
    )
    $PythonPath = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) {
            $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        }
        if ($null -ne $pythonCommand) {
            $PythonPath = $pythonCommand.Source
        }
    }
}
if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-SanitizedFailure -Code "PROCESS_ERROR"
    exit 3
}

if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = "sec-scheduled-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffffffZ")
}

$intakeArguments = @(
    $intakePath,
    "--output-root", $OutputRoot,
    "--lookback-days", ([string][int]$contract.lookback_days),
    "--run-id", $RunId
)
$intakeOutput = @(& $PythonPath @intakeArguments 2>&1)
$intakeExitCode = $LASTEXITCODE
$intakeOutput | ForEach-Object { $_.ToString() } | Write-Output

if ($intakeExitCode -ne 0) {
    $failureCode = "PROCESS_ERROR"
    foreach ($line in $intakeOutput) {
        try {
            $parsed = $line.ToString() | ConvertFrom-Json -ErrorAction Stop
            if ($parsed.code -in @(
                "SEC_USER_AGENT_REQUIRED", "SEC_ACCESS_BLOCKED", "SEC_RATE_LIMITED",
                "SEC_SOURCE_INVALID", "SEC_IDENTITY_CONFLICT", "NETWORK_SCOPE_VIOLATION",
                "RUN_COLLISION"
            )) {
                $failureCode = $parsed.code
            }
        } catch {
            continue
        }
    }
    & $PythonPath $postprocessorPath "--output-root" $OutputRoot "--failure-code" $failureCode
    exit $intakeExitCode
}

& $PythonPath $postprocessorPath "--output-root" $OutputRoot "--current-run-id" $RunId
$postprocessorExitCode = $LASTEXITCODE
if ($postprocessorExitCode -ne 0) {
    exit 3
}
exit 0
