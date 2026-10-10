# dev-queue.ps1 - started every 15 minutes by the Windows task InvestmentV2-DevQueue (redesign T3).
#
# 1. If a dev-run holds the lock (workspace\outputs\dev-runs\_lock, live process), stop at once.
# 2. Take the oldest docs\claude\_dev-queue\<id>.txt (first line = id) and move it to
#    workspace\outputs\dev-runs\_taken\ so it never runs twice (dev-run creates the run folder itself).
# 3. If docs\claude\<id>-builder-prompt.md is not committed, run tools\commit-docs.ps1 once (its path
#    limits and staged-change stop stay as they are); if still not committed, record
#    STOP_PROMPT_NOT_COMMITTED in LATEST.json and stop.
# 4. Run tools\dev-run.ps1 <id>.
# Logs: workspace\outputs\dev-runs\_queue\ (ASCII). Never commits code, merges or publishes.
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as the ANSI code page.

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
# Limits must fit the 6-hour task limit (register-dev-tasks.ps1 $queueLimitHours):
# commit-docs 15 min + dev-run 340 min + 5 min spare = 360 min.
$CommitDocsLimitSeconds = 900
$DevRunLimitMinutes = 340
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$devpipe = Join-Path $PSScriptRoot 'dev_pipeline\devpipe.py'
$runsRoot = Join-Path $repo 'workspace\outputs\dev-runs'
$lockPath = Join-Path $runsRoot '_lock'
$queueDir = Join-Path $runsRoot '_queue'
$powershellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$cmdExe = $env:ComSpec
if ([string]::IsNullOrWhiteSpace($cmdExe)) { $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe' }
New-Item -ItemType Directory -Force -Path $queueDir | Out-Null
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$logPath = Join-Path $queueDir ([DateTime]::Now.ToString('yyyy-MM-dd') + '.log')
Set-Content -LiteralPath (Join-Path $queueDir 'heartbeat.txt') -Value ([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')) -Encoding ASCII

function Get-AsciiText([string]$Text) {
    if ($null -eq $Text) { return '' }
    $chars = foreach ($c in $Text.ToCharArray()) { if ([int]$c -ge 32 -and [int]$c -lt 127) { $c } else { '?' } }
    return (-join $chars)
}

function Write-Log([string]$Text) {
    $line = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') + ' ' + (Get-AsciiText $Text)
    Add-Content -LiteralPath $logPath -Value $line -Encoding ASCII
}

function Stop-ProcessTree([int]$ProcessId) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $cmdExe
    $psi.Arguments = '/d /s /c "taskkill /PID ' + $ProcessId + ' /T /F > NUL 2>&1"'
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $killer = [System.Diagnostics.Process]::Start($psi)
    [void]$killer.WaitForExit(60000)
}

function Invoke-Captured([string]$CommandLine, [int]$TimeoutSeconds = 0) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $cmdExe
    $psi.Arguments = '/d /s /c "' + $CommandLine + '"'
    $psi.WorkingDirectory = $repo
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    if ($TimeoutSeconds -gt 0 -and -not $proc.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-ProcessTree -ProcessId $proc.Id
        [void]$proc.WaitForExit(60000)
        return $null
    }
    $proc.WaitForExit()
    return $proc.ExitCode
}

function Read-FirstLine([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return '' }
    $lines = @([System.IO.File]::ReadAllLines($Path))
    if ($lines.Count -gt 0) { return [string]$lines[0] }
    return ''
}

function Invoke-Devpipe([string]$Tag, [string[]]$Arguments) {
    $base = Join-Path $queueDir ('last-' + $Tag)
    $quoted = ($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $code = Invoke-Captured ('"' + $python + '" "' + $devpipe + '" ' + $quoted + ' < NUL > "' + $base + '.out" 2> "' + $base + '.err"')
    return [pscustomobject]@{ Code = $code; Line = (Read-FirstLine ($base + '.out')) }
}

function Test-LockAlive {
    if (-not (Test-Path -LiteralPath $lockPath)) { return $false }
    $info = $null
    try { $info = [System.IO.File]::ReadAllText($lockPath) | ConvertFrom-Json } catch { $info = $null }
    if ($null -eq $info -or $null -eq $info.pid) {
        $age = ([DateTime]::UtcNow - (Get-Item -LiteralPath $lockPath).LastWriteTimeUtc).TotalSeconds
        return ($age -lt 120)
    }
    $holder = Get-Process -Id ([int]$info.pid) -ErrorAction SilentlyContinue
    if ($null -eq $holder) { return $false }
    try {
        return ($holder.StartTime.ToUniversalTime().Ticks -eq [int64]$info.start_ticks)
    } catch {
        return $true
    }
}

# Same lookup as manage-us-stock-strategy\scripts\run_auto_core.ps1.
$candidates = @((Join-Path $repo '.venv\Scripts\python.exe'), (Join-Path $repo 'venv\Scripts\python.exe'))
$python = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($python)) {
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -eq $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
    if ($null -ne $command) { $python = $command.Source }
}
if ([string]::IsNullOrWhiteSpace($python)) {
    Write-Log 'STOP PYTHON_NOT_FOUND'
    exit 3
}

if (Test-LockAlive) { exit 0 }

$taken = Invoke-Devpipe -Tag 'queue-take' -Arguments @('queue-take', '--repo', $repo)
if ($taken.Code -eq 1) { exit 0 }
Write-Log $taken.Line
if ($taken.Code -ne 0 -or -not ($taken.Line -match '^QUEUE TAKEN ([a-z0-9][a-z0-9-]{1,47})$')) { exit 1 }
$taskId = $Matches[1]

$prompt = Invoke-Devpipe -Tag 'prompt-committed' -Arguments @('prompt-committed', '--repo', $repo, '--id', $taskId)
if ($prompt.Code -ne 0) {
    Write-Log ($prompt.Line + ' -> running commit-docs.ps1 once')
    $raw = Join-Path $queueDir ($stamp + '-commit-docs.out')
    $commitDocs = Join-Path $PSScriptRoot 'commit-docs.ps1'
    $code = Invoke-Captured ('"' + $powershellExe + '" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $commitDocs + '" < NUL > "' + $raw + '" 2>&1') $CommitDocsLimitSeconds
    Write-Log ('commit-docs exit=' + $code + ' output=' + $raw)
    $prompt = Invoke-Devpipe -Tag 'prompt-committed' -Arguments @('prompt-committed', '--repo', $repo, '--id', $taskId)
    if ($prompt.Code -ne 0) {
        $latest = Invoke-Devpipe -Tag 'write-latest' -Arguments @('write-latest', '--repo', $repo, '--id', $taskId, '--status', 'STOP_PROMPT_NOT_COMMITTED', '--reason', (($prompt.Line -split ' ') | Select-Object -Last 1))
        Write-Log $latest.Line
        exit 1
    }
}

$out = Join-Path $queueDir ($stamp + '-' + $taskId + '.dev-run.out')
$err = Join-Path $queueDir ($stamp + '-' + $taskId + '.dev-run.err')
$devRun = Join-Path $PSScriptRoot 'dev-run.ps1'
Write-Log ('DEV-RUN start ' + $taskId)
$code = Invoke-Captured ('"' + $powershellExe + '" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $devRun + '" ' + $taskId + ' < NUL > "' + $out + '" 2> "' + $err + '"') ($DevRunLimitMinutes * 60)
if ($null -eq $code) {
    $latest = Invoke-Devpipe -Tag 'write-latest' -Arguments @('write-latest', '--repo', $repo, '--id', $taskId, '--status', 'STOP_QUEUE_TIMEOUT', '--reason', 'dev_run_over_limit')
    Write-Log $latest.Line
    exit 1
}
Write-Log ('DEV-RUN end exit=' + $code + ' ' + (Read-FirstLine $out))
exit $code
