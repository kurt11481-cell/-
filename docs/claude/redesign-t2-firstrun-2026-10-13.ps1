# redesign-t2-firstrun-2026-10-13.ps1 - one-time, after the scheduled auto-core runs of 2026-10-13 stopped at start
# (RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND at 06:15 daily and 07:45 decide).
# 1) writes workspace\outputs\auto-core\logs\env-diag-20261013.txt (where Python and kiwoomcli come from, and how the
#    InvestmentV2 tasks are registered) so Cowork can choose the permanent fix;
# 2) runs today's daily and then decide once from this console with an explicit Python path (compare mode).
# Read-only Kiwoom queries only, as in the scheduled tasks. Never places, changes or cancels an order.
# ASCII only (Windows PowerShell 5.1). Usage (repo root): .\docs\claude\redesign-t2-firstrun-2026-10-13.ps1

$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$logs = Join-Path $repo 'workspace\outputs\auto-core\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$diag = Join-Path $logs 'env-diag-20261013.txt'

$py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
$kw = (Get-Command kiwoomcli -ErrorAction SilentlyContinue).Source
$userPath = @([Environment]::GetEnvironmentVariable('Path', 'User') -split ';' | Where-Object { $_ })
$machinePath = @([Environment]::GetEnvironmentVariable('Path', 'Machine') -split ';' | Where-Object { $_ })
function In-Registry([string]$file) {
    if (-not $file) { return 'NO_FILE' }
    $dir = (Split-Path -Parent $file).TrimEnd('\')
    $u = $userPath | Where-Object { [Environment]::ExpandEnvironmentVariables($_).TrimEnd('\') -ieq $dir }
    $m = $machinePath | Where-Object { [Environment]::ExpandEnvironmentVariables($_).TrimEnd('\') -ieq $dir }
    return ('USER=' + [bool]$u + ' MACHINE=' + [bool]$m)
}
$lines = @()
$lines += 'DIAG_AT=' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
$lines += 'PY_CONSOLE=' + $py
$lines += 'PY_IN_REGISTRY_PATH=' + (In-Registry $py)
if ($py) {
    $item = Get-Item -LiteralPath $py -ErrorAction SilentlyContinue
    $lines += 'PY_ITEM=' + ($(if ($item) { 'len=' + $item.Length + ' attr=' + $item.Attributes } else { 'NOT_FOUND' }))
    $lines += 'PY_TESTPATH_LEAF=' + (Test-Path -LiteralPath $py -PathType Leaf)
    $lines += 'PY_EXECUTABLE=' + (& $py -c "import sys; print(sys.executable)")
    $lines += 'PY_VERSION=' + (& $py -c "import sys; print(sys.version.split()[0])")
}
$lines += 'KIWOOM_CONSOLE=' + $kw
$lines += 'KIWOOM_IN_REGISTRY_PATH=' + (In-Registry $kw)
$lines += 'PROFILE_EXISTS=' + (Test-Path -LiteralPath $PROFILE)
if (Test-Path -LiteralPath $PROFILE) {
    $lines += 'PROFILE_PATH_LINES=' + ((Select-String -LiteralPath $PROFILE -Pattern 'PATH|python|conda|pyenv|kiwoom' -SimpleMatch:$false | ForEach-Object { $_.LineNumber }) -join ',')
}
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match 'InvestmentV2|SEC|Sec' } | ForEach-Object {
    $a = $_.Actions | Select-Object -First 1
    $args1 = [string]$a.Arguments
    $args1 = $args1 -replace '(?i)(user[-_ ]?agent\S*\s+)("[^"]*"|\S+)', '$1<hidden>'
    $lines += ('TASK ' + $_.TaskName + ' | user=' + $_.Principal.UserId + ' | logon=' + $_.Principal.LogonType + ' | run=' + $_.Principal.RunLevel + ' | exe=' + $a.Execute + ' | args=' + $args1)
}
$lines | Out-File -LiteralPath $diag -Encoding utf8
Write-Host ('diag written: ' + $diag)
if (-not $py) { Write-Host 'STOP PYTHON_NOT_FOUND_IN_THIS_CONSOLE (send this line to Cowork)'; exit 1 }

$runner = Join-Path $repo 'manage-us-stock-strategy\scripts\run_auto_core.ps1'
Write-Host '== daily (several minutes: 30-minute pages, first run)'
& $runner -Command daily -PythonPath $py
$dailyExit = $LASTEXITCODE
Write-Host ('DAILY_EXIT=' + $dailyExit)
Write-Host '== decide'
& $runner -Command decide -PythonPath $py
$decideExit = $LASTEXITCODE
Write-Host ('DECIDE_EXIT=' + $decideExit)
foreach ($f in @('LATEST.json', 'LATEST_DECISION.json')) {
    $p = Join-Path $repo ('workspace\outputs\auto-core\' + $f)
    if (Test-Path -LiteralPath $p) {
        $j = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Host ($f + ' status=' + $j.status + ' reasons=' + (@($j.reasons) -join ' | '))
    } else { Write-Host ($f + ' MISSING') }
}
Write-Host 'T2_FIRSTRUN_DONE'
