[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$PythonPath = "",
    [string]$Command = "daily"
)

# Redesign T1 F5: Windows task entry for the deterministic auto-core (InvestmentV2-AutoCore runs -Command daily;
# redesign T2 F11: InvestmentV2-AutoCoreDecide runs -Command decide). Read-only broker access only; no order
# command exists on this path. daily writes workspace\outputs\auto-core\<YYYY-MM-DD>\result.json and LATEST.json;
# decide writes decision.json and LATEST_DECISION.json there.
# Output of the Python run (and of kiwoomcli inside collect_30m.ps1) is redirected by cmd /c so the bytes
# are kept as written. No retry: the next scheduled run is the retry. Exit code = the Python exit code
# (0 OK or HOLD, 1 FAIL); 3 when the runner itself cannot start or the command is not daily or decide.

$ErrorActionPreference = "Stop"
if ($Command -cne "daily" -and $Command -cne "decide") {
    exit 3
}
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$scriptPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\auto_core.py"
$logDirectory = Join-Path $resolvedRepository "workspace\outputs\auto-core\logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$logPath = Join-Path $logDirectory ("auto-core-" + $Command + "-" + $stamp + ".log")

function Write-RunnerLine {
    param([string]$Text)
    Add-Content -LiteralPath $logPath -Value $Text -Encoding ASCII
}

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL AUTO_CORE_SCRIPT_NOT_FOUND"
    exit 3
}
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $candidates = @(
        (Join-Path $resolvedRepository ".venv\Scripts\python.exe"),
        (Join-Path $resolvedRepository "venv\Scripts\python.exe")
    )
    $PythonPath = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $command) { $PythonPath = $command.Source }
    }
}
if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND"
    exit 3
}
$timezoneId = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
Write-RunnerLine ("RUNNER_START utc=" + $stamp + " timezone=" + $timezoneId + " command=" + $Command)

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Set-Location -LiteralPath $resolvedRepository
$commandLine = '"' + $PythonPath + '" "' + $scriptPath + '" ' + $Command + ' >> "' + $logPath + '" 2>&1'
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    cmd /c $commandLine
    $exitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}
Write-RunnerLine ("RUNNER_END exit=" + $exitCode)
exit $exitCode
