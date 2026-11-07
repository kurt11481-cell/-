[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$PythonPath = ""
)

# API pilots: Windows task entry of the pilot runner (InvestmentV2-LLMPilots, every 10 minutes).
# Runs llm_runner.py once. The runner decides which switched-on pilot slot is due (committed switch file
# docs/claude/llm-pilots-schedule.json) and writes only under workspace\outputs\llm. This wrapper writes only
# workspace\outputs\llm\runner\logs\<yyyyMMdd>.log (local date = KST, one file per day, appended, ASCII).
# The pilot key is handed from the user scope to this process only when the process value is empty; its value
# is never logged or written, only whether it is present. No broker call and no network call on this path.
# Exit code = the Python exit code; 3 when the runner cannot start; 4 on an unexpected wrapper exception.

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$scriptPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\llm_runner.py"
$logDirectory = Join-Path $resolvedRepository "workspace\outputs\llm\runner\logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$started = Get-Date
$logPath = Join-Path $logDirectory ($started.ToString("yyyyMMdd") + ".log")

function Write-RunnerLine {
    param([string]$Text)
    Add-Content -LiteralPath $logPath -Value $Text -Encoding ASCII
}

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL RUNNER_SCRIPT_NOT_FOUND"
    exit 3
}
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $candidates = @(
        (Join-Path $resolvedRepository ".venv\Scripts\python.exe"),
        (Join-Path $resolvedRepository "venv\Scripts\python.exe")
    )
    $PythonPath = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) { $pythonCommand = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $pythonCommand) { $PythonPath = $pythonCommand.Source }
    }
}
if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND"
    exit 3
}

# From here on any unexpected exception ends in the catch block at the bottom (exit 4).
try {
    # Key hand-over (design section 3 item 1): the user-scope value is read only when the process value is empty.
    if ([string]::IsNullOrEmpty($env:INVESTV2_ANTHROPIC_API_KEY)) {
        $userValue = [Environment]::GetEnvironmentVariable('INVESTV2_ANTHROPIC_API_KEY', 'User')
        if (-not [string]::IsNullOrEmpty($userValue)) { $env:INVESTV2_ANTHROPIC_API_KEY = $userValue }
        $userValue = $null
    }
    $keyPresent = if ([string]::IsNullOrEmpty($env:INVESTV2_ANTHROPIC_API_KEY)) { "NO" } else { "YES" }

    $timezoneId = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
    Write-RunnerLine ("RUNNER_START local=" + $started.ToString("yyyy-MM-ddTHH:mm:ss") + " timezone=" + $timezoneId + " key_present=" + $keyPresent)

    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    Set-Location -LiteralPath $resolvedRepository
    $commandLine = '"' + $PythonPath + '" "' + $scriptPath + '" >> "' + $logPath + '" 2>&1'
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
} catch {
    $failureLine = "RUNNER_FAIL RUNNER_EXCEPTION"
    try {
        $failureType = $_.Exception.GetType().FullName
        $failureMessage = ([string]$_.Exception.Message -replace "[\r\n]+", " ") -replace "[^\x20-\x7E]", "?"
        if ($failureMessage.Length -gt 300) { $failureMessage = $failureMessage.Substring(0, 300) }
        $failureLine = "RUNNER_FAIL RUNNER_EXCEPTION type=" + $failureType + " message=" + $failureMessage
    } catch {
    }
    try { Write-RunnerLine $failureLine } catch { }
    exit 4
}
