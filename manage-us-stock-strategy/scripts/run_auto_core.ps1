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
# (0 OK or HOLD, 1 FAIL); 3 when the runner itself cannot start or the command is not daily or decide;
# 4 when the Python runtime cannot load the time zone data (tzdata missing) - the run did not start.

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
        # PowerShell variable names ignore case: a name equal to a parameter ($Command) would overwrite it.
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) { $pythonCommand = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $pythonCommand) { $PythonPath = $pythonCommand.Source }
    }
}
if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND"
    exit 3
}

# Pre-check (runner-deps): auto_core_reconcile.py and auto_core_decide.py load zoneinfo time zones at import time,
# so a Python without the time zone data (tzdata) dies before writing any record. The same Python runs the check
# with no isolation flag (-I/-s/-E/-S): tzdata may sit in the user site-packages. The code uses single quotes only: Windows
# PowerShell 5.1 does not escape double quotes inside native arguments. The version line is flushed first so it
# comes before any traceback. Output stays in variables; only the failure lines go to the runner log.
$depsCode = "import sys; print('%d.%d.%d' % sys.version_info[:3], flush=True); import zoneinfo; zoneinfo.ZoneInfo('Asia/Seoul'); zoneinfo.ZoneInfo('America/New_York')"
$depsOutput = @()
$depsExitCode = $null
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $depsOutput = @(& $PythonPath -c $depsCode 2>&1)
    $depsExitCode = $LASTEXITCODE
} catch {
    $depsOutput = @($depsOutput) + @([string]$_.Exception.Message)
    $depsExitCode = $null
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}
if ($null -eq $depsExitCode -or $depsExitCode -ne 0) {
    # Version = first stdout line in the form 1.2.3; error = last non-empty stderr line (else last other stdout line).
    $depsVersion = "unknown"
    $depsLastError = ""
    $depsLastOther = ""
    foreach ($depsItem in $depsOutput) {
        $depsText = ([string]$depsItem).Trim()
        if ($depsText.Length -eq 0) { continue }
        if ($depsItem -is [System.Management.Automation.ErrorRecord]) {
            $depsLastError = $depsText
        } elseif ($depsText -match '^\d+\.\d+\.\d+$') {
            if ($depsVersion -eq "unknown") { $depsVersion = $depsText }
        } else {
            $depsLastOther = $depsText
        }
    }
    if ($depsLastError.Length -eq 0) { $depsLastError = $depsLastOther }
    if ($depsLastError.Length -eq 0) { $depsLastError = "exit=" + $depsExitCode }
    $depsLastError = ($depsLastError -replace "[\r\n]+", " ") -replace "[^\x20-\x7E]", "?"
    if ($depsLastError.Length -gt 300) { $depsLastError = $depsLastError.Substring(0, 300) }
    Write-RunnerLine ("RUNNER_FAIL PYTHON_DEPS_MISSING zoneinfo=Asia/Seoul,America/New_York python=" + $depsVersion)
    Write-RunnerLine ("RUNNER_FAIL_DETAIL " + $depsLastError)
    exit 4
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
