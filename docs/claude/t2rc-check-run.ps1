[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$PythonPath = "",
    [string]$Day = ""
)

# t2-rc M2 (docs/claude/t2-rc-preregistration-2026-10-14.md section 3): Windows task InvestmentV2-T2rcCheck,
# Tuesday-Saturday 08:40 KST. Runs the independent calculator docs/claude/t2rc-oracle.py once for the KST day and
# writes its result to workspace\outputs\auto-core\<YYYY-MM-DD>\t2rc-check.json (only when the decide folder of that
# day exists) and always to workspace\outputs\auto-core\LATEST_T2RC_CHECK.json. Read-only otherwise: no Kiwoom call,
# no order path, no policy/state/journal write. The calculator file is pinned by sha256: a different file is not run
# (LF-normalized) and the result says ORACLE_SHA_MISMATCH (a calculator change needs a new pin and Judge confirmation, prereg C1).
# No retry. Exit code = calculator exit code (0 MATCH or NOT_CHECKED, 2 MISMATCH, 1 error); 3 = runner cannot start.

$ExpectedOracleSha256 = "6f0484322212d394d6c297944cabee797062c08e0c131affedddbc566e3435f6"

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$oraclePath = Join-Path $resolvedRepository "docs\claude\t2rc-oracle.py"
$autoCoreRoot = Join-Path $resolvedRepository "workspace\outputs\auto-core"
$logDirectory = Join-Path $autoCoreRoot "logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$logPath = Join-Path $logDirectory ("t2rc-check-" + $stamp + ".log")
$latestPath = Join-Path $autoCoreRoot "LATEST_T2RC_CHECK.json"

function Write-RunnerLine {
    param([string]$Text)
    Add-Content -LiteralPath $logPath -Value $Text -Encoding ASCII
}

function Write-RunnerResult {
    # Minimal result when the calculator is not run, so the 08:50 alert sees the failure instead of an old file.
    param([string]$Reason, [string]$DayKst)
    $json = '{"schema": "t2rc-check-1.0", "day_kst": "' + $DayKst + '", "verdict": "ERROR", "reason": "' + $Reason +
            '", "counts_for_c1": false, "order_authority": false, "quantity_authority": "none", "execution_quantity": null}'
    [System.IO.File]::WriteAllText($latestPath, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
}

# KST date from UTC (independent of the Windows time zone setting)
if ([string]::IsNullOrWhiteSpace($Day)) {
    $Day = [DateTime]::UtcNow.AddHours(9).ToString("yyyy-MM-dd")
}
if ($Day -notmatch '^\d{4}-\d{2}-\d{2}$') {
    Write-RunnerLine "RUNNER_FAIL DAY_FORMAT"
    Write-RunnerResult -Reason "DAY_FORMAT" -DayKst "invalid"
    exit 3
}

if (-not (Test-Path -LiteralPath $oraclePath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL ORACLE_NOT_FOUND"
    Write-RunnerResult -Reason "ORACLE_NOT_FOUND" -DayKst $Day
    exit 3
}
# sha256 over LF-normalized bytes, so a CRLF checkout of the same file keeps the pin (README convention for prompts)
$oracleText = [System.IO.File]::ReadAllText($oraclePath, (New-Object System.Text.UTF8Encoding($false))).Replace("`r`n", "`n")
$hasher = [System.Security.Cryptography.SHA256]::Create()
$actualSha = (($hasher.ComputeHash((New-Object System.Text.UTF8Encoding($false)).GetBytes($oracleText))) | ForEach-Object { $_.ToString("x2") }) -join ""
if ($actualSha -ne $ExpectedOracleSha256) {
    Write-RunnerLine ("RUNNER_FAIL ORACLE_SHA_MISMATCH actual=" + $actualSha)
    Write-RunnerResult -Reason ("ORACLE_SHA_MISMATCH:" + $actualSha) -DayKst $Day
    exit 3
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $candidates = @(
        (Join-Path $resolvedRepository ".venv\Scripts\python.exe"),
        (Join-Path $resolvedRepository "venv\Scripts\python.exe")
    )
    $PythonPath = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        # Variable names ignore case in PowerShell: never reuse a parameter name ($Day, $PythonPath) for other values.
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) { $pythonCommand = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $pythonCommand) { $PythonPath = $pythonCommand.Source }
    }
}
if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND"
    Write-RunnerResult -Reason "PYTHON_RUNTIME_NOT_FOUND" -DayKst $Day
    exit 3
}

$dayFolder = Join-Path $autoCoreRoot $Day
if (Test-Path -LiteralPath $dayFolder -PathType Container) {
    $outPath = Join-Path $dayFolder "t2rc-check.json"
} else {
    # Do not create the day folder (decide creates it); keep the result next to the logs.
    $outPath = Join-Path $logDirectory ("t2rc-check-" + $Day + ".json")
}
Write-RunnerLine ("RUNNER_START utc=" + $stamp + " day_kst=" + $Day + " oracle_sha256=" + $actualSha)

# python -I ignores PYTHON* variables; the calculator opens every file with an explicit utf-8 encoding.
Set-Location -LiteralPath $resolvedRepository
# never let an earlier result of the same day stand in for this run (a crash below leaves no output -> ERROR)
if (Test-Path -LiteralPath $outPath -PathType Leaf) { Remove-Item -LiteralPath $outPath -Force }
$commandLine = '"' + $PythonPath + '" -I "' + $oraclePath + '" check --day ' + $Day + ' --repo "' + $resolvedRepository + '" --out "' + $outPath + '" >> "' + $logPath + '" 2>&1'
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    cmd /c $commandLine
    $exitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}
if (Test-Path -LiteralPath $outPath -PathType Leaf) {
    Copy-Item -LiteralPath $outPath -Destination $latestPath -Force
} else {
    Write-RunnerResult -Reason ("ORACLE_NO_OUTPUT:exit=" + $exitCode) -DayKst $Day
}
Write-RunnerLine ("RUNNER_END exit=" + $exitCode + " out=" + $outPath)
exit $exitCode
