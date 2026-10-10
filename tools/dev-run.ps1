# dev-run.ps1 - run one dev task through the headless pipeline (redesign T3).
#
# Usage (Windows PowerShell, main checkout):  .\tools\dev-run.ps1 <id> [-Preflight]
# Normally started by tools\dev-queue.ps1 (Windows task InvestmentV2-DevQueue), not by hand.
#
# Flow: preflight -> lock -> init -> baseline worktree (synchronous; cached per base SHA + python + method)
# -> baseline suite in the background while the headless Builder works in worktree <id> -> wait for the
# baseline -> deterministic checks -> headless Judge (Read, Grep, Glob only) -> at most one fix pass -> result.
# Between steps the run records (run.json, baseline, markers) are compared with the sha256 this process
# keeps in memory, and right before each check the main checkout is compared with its pre-Builder snapshot.
# Every decision, parse and hash is made by tools\dev_pipeline\devpipe.py; this script only starts
# processes. Output of claude and python is saved byte for byte through cmd /c redirection; prompts are
# one English line naming a file (nothing is piped into claude). Records live in the main checkout under
# workspace\outputs\dev-runs\<id>\ (outside the Builder's folder). The console gets one line.
# This script never commits, merges, publishes, registers tasks or touches orders or broker access.
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as the ANSI code page.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Id,
    [switch]$Preflight
)

$ErrorActionPreference = 'Stop'

# ---- constants (a task prompt cannot change these) ----
$IdPattern = '^[a-z0-9][a-z0-9-]{1,47}$'
$JudgeMaxTurns = 80
$JudgeTimeoutMinutes = 45
# Outer cap for the background baseline; devpipe keeps its own limits inside (full suite 60 + schema audit
# 10 minutes, the same as before), so this only catches a baseline process that hangs: 60 + 10 + 5 spare.
$BaselineLimitMinutes = 75
$BuilderToolSet = 'Read,Edit,Write,Grep,Glob,Bash,PowerShell'
# P8: test and read-only git commands only. Nothing that overlaps the project deny/ask rules (commit,
# publish, reconcile or journal apply, auto-core, policy or state edits). No bare tool names (Read, Edit,
# Write, Grep, Glob): a bare name matches every path, also outside the worktree. Reads inside the worktree
# need no rule and acceptEdits approves edits there; anything outside would ask and is refused.
$BuilderAllowedTools = @(
    'Bash(python -m unittest *)', 'PowerShell(python -m unittest *)',
    'Bash(python manage-us-stock-strategy/scripts/validate_schema_contracts.py)',
    'PowerShell(python manage-us-stock-strategy/scripts/validate_schema_contracts.py)',
    'Bash(git status)', 'Bash(git status *)', 'Bash(git diff)', 'Bash(git diff *)', 'Bash(git log)', 'Bash(git log *)',
    'PowerShell(git status)', 'PowerShell(git status *)', 'PowerShell(git diff)', 'PowerShell(git diff *)',
    'PowerShell(git log)', 'PowerShell(git log *)'
)
# Deny wins over allow: git diff/log must not write a file (--output) or read any file (--no-index).
$BuilderDisallowedTools = @(
    'mcp__*',
    'Bash(git *--output*)', 'PowerShell(git *--output*)',
    'Bash(git *--no-index*)', 'PowerShell(git *--no-index*)'
)

function Get-AsciiText([string]$Text) {
    if ($null -eq $Text) { return '' }
    $chars = foreach ($c in $Text.ToCharArray()) { if ([int]$c -ge 32 -and [int]$c -lt 127) { $c } else { '?' } }
    return (-join $chars)
}

if ($Id -cnotmatch $IdPattern) {
    Write-Output ('DEV-RUN ' + (Get-AsciiText $Id) + ' STOP_PREFLIGHT reason=ID_FORMAT')
    exit 2
}

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$devpipe = Join-Path $PSScriptRoot 'dev_pipeline\devpipe.py'
$runsRoot = Join-Path $repo 'workspace\outputs\dev-runs'
$lockPath = Join-Path $runsRoot '_lock'
$worktree = Join-Path $repo ('.claude\worktrees\' + $Id)
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$cmdExe = $env:ComSpec
if ([string]::IsNullOrWhiteSpace($cmdExe)) { $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe' }

$script:runDir = Join-Path $runsRoot $Id
$script:consoleDir = Join-Path $runsRoot ('_preflight\' + $stamp + '-' + $Id)
$script:logPath = Join-Path $script:consoleDir 'log.txt'
$script:devpipeCalls = 0
$script:lockHeld = $false
$script:claude = ''
$script:builderModel = ''
$script:builderEffort = ''
$script:baselineProc = $null
$script:baselineOut = ''
$script:baselineStarted = [DateTime]::UtcNow
$script:baselineCleanupDue = $false
$script:records = @{}
New-Item -ItemType Directory -Force -Path $script:consoleDir | Out-Null

function Write-Log([string]$Text) {
    $line = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') + ' ' + (Get-AsciiText $Text)
    Add-Content -LiteralPath $script:logPath -Value $line -Encoding ASCII
}

function Find-Python {
    # Same lookup as manage-us-stock-strategy\scripts\run_auto_core.ps1.
    $candidates = @((Join-Path $repo '.venv\Scripts\python.exe'), (Join-Path $repo 'venv\Scripts\python.exe'))
    $found = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($found)) {
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $command) { $found = $command.Source }
    }
    return $found
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

# Starts one cmd.exe command line (redirections inside it keep the bytes) and returns the process.
function Start-Captured([string]$CommandLine, [string]$WorkingDirectory) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $cmdExe
    $psi.Arguments = '/d /s /c "' + $CommandLine + '"'
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    return [System.Diagnostics.Process]::Start($psi)
}

# Runs one cmd.exe command line and waits. Optional timeout kills the tree.
function Invoke-Captured([string]$CommandLine, [string]$WorkingDirectory, [int]$TimeoutSeconds = 0) {
    $proc = Start-Captured -CommandLine $CommandLine -WorkingDirectory $WorkingDirectory
    $timedOut = $false
    if ($TimeoutSeconds -gt 0) {
        if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
            $timedOut = $true
            Stop-ProcessTree -ProcessId $proc.Id
            [void]$proc.WaitForExit(60000)
        }
    }
    $code = $null
    if (-not $timedOut) {
        $proc.WaitForExit()
        $code = $proc.ExitCode
    }
    return [pscustomobject]@{ Code = $code; TimedOut = $timedOut }
}

function Get-LineStatus([string]$Line) {
    $parts = @($Line -split ' ')
    if ($parts.Count -ge 2 -and $parts[1] -match '^[A-Z][A-Z0-9_]*$') { return $parts[1] }
    return 'STOP_NO_OUTPUT'
}

function Get-LineReason([string]$Line) {
    if ($Line -match 'reason=(\S*)') { return $Matches[1] }
    return ''
}

function Read-FirstLine([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return '' }
    $lines = @([System.IO.File]::ReadAllLines($Path))
    if ($lines.Count -gt 0) { return [string]$lines[0] }
    return ''
}

function Get-DevpipeCall([string]$Tag, [string[]]$Arguments) {
    $script:devpipeCalls++
    $base = Join-Path $script:consoleDir (('{0:D2}-' -f $script:devpipeCalls) + $Tag)
    $quoted = ($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $command = '"' + $python + '" "' + $devpipe + '" ' + $quoted + ' < NUL > "' + $base + '.out" 2> "' + $base + '.err"'
    return [pscustomobject]@{ Base = $base; Command = $command }
}

function Invoke-Devpipe([string]$Tag, [string[]]$Arguments) {
    $call = Get-DevpipeCall -Tag $Tag -Arguments $Arguments
    $result = Invoke-Captured -CommandLine $call.Command -WorkingDirectory $repo
    $line = Read-FirstLine ($call.Base + '.out')
    Write-Log ($Tag + ' exit=' + $result.Code + ' ' + $line)
    return [pscustomobject]@{ Code = $result.Code; Line = $line; Status = (Get-LineStatus $line) }
}

# ---- D3: baseline suite in the background (its own temporary worktree, never the Builder's) ----
function Start-Baseline {
    $call = Get-DevpipeCall -Tag 'baseline-run' -Arguments @('baseline-run', '--run-dir', $script:runDir)
    $script:baselineOut = $call.Base + '.out'
    $script:baselineStarted = [DateTime]::UtcNow
    $script:baselineProc = Start-Captured -CommandLine $call.Command -WorkingDirectory $repo
    Write-Log ('BASELINE start pid=' + $script:baselineProc.Id)
}

function Wait-Baseline {
    $proc = $script:baselineProc
    $leftMs = [int64]($BaselineLimitMinutes * 60000) - [int64](([DateTime]::UtcNow - $script:baselineStarted).TotalMilliseconds)
    if ($leftMs -lt 0) { $leftMs = 0 }
    if (-not $proc.WaitForExit([int]$leftMs)) {
        Stop-ProcessTree -ProcessId $proc.Id
        [void]$proc.WaitForExit(60000)
        $script:baselineProc = $null
        Write-Log 'BASELINE end timeout=True'
        return [pscustomobject]@{ Code = $null; Line = ''; Status = 'STOP_BASELINE_TIMEOUT' }
    }
    $proc.WaitForExit()
    $code = $proc.ExitCode
    $script:baselineProc = $null
    $line = Read-FirstLine $script:baselineOut
    Write-Log ('BASELINE end exit=' + $code + ' ' + $line)
    return [pscustomobject]@{ Code = $code; Line = $line; Status = (Get-LineStatus $line) }
}

# Every exit path (and right after the baseline ends): a baseline still running is stopped (process tree),
# then devpipe removes the temporary worktree and the branch baseline-prepare created. --repo is this
# script's own path. Called before the lock is released.
function Stop-Baseline {
    if ($null -ne $script:baselineProc) {
        if (-not $script:baselineProc.HasExited) {
            Stop-ProcessTree -ProcessId $script:baselineProc.Id
            [void]$script:baselineProc.WaitForExit(60000)
            Write-Log 'BASELINE stopped before it ended (run is ending)'
        }
        $script:baselineProc = $null
    }
    if ($script:baselineCleanupDue) {
        $script:baselineCleanupDue = $false
        [void](Invoke-Devpipe -Tag 'baseline-cleanup' -Arguments @('baseline-cleanup', '--repo', $repo, '--run-dir', $script:runDir))
    }
}

# ---- O3a: sha256 of the run records, kept in this process between steps ----
function Save-Records {
    $saved = Invoke-Devpipe -Tag 'records' -Arguments @('records', '--run-dir', $script:runDir)
    if ($saved.Code -ne 0) { return 'records_unreadable' }
    $script:records = @{}
    foreach ($token in @($saved.Line -split ' ')) {
        if ($token -cmatch '^([a-z][a-z.-]*)=([0-9a-f]{64})$') { $script:records[$Matches[1]] = $Matches[2] }
    }
    return ''
}

function Test-Records([string]$Step) {
    $arguments = @('records', '--run-dir', $script:runDir)
    foreach ($name in @($script:records.Keys | Sort-Object)) { $arguments += @('--expect', ($name + '=' + $script:records[$name])) }
    $checked = Invoke-Devpipe -Tag ('records-' + $Step) -Arguments $arguments
    if ($checked.Code -eq 0) { return '' }
    $reason = Get-LineReason $checked.Line
    if ([string]::IsNullOrWhiteSpace($reason)) { $reason = 'records_unreadable' }
    return ($Step + ':' + $reason)
}

# run.json may no longer be trusted, so the result goes to LATEST.json only (no result.json, no merge).
function Stop-RecordChanged([string]$Reason) {
    Stop-Baseline
    Write-Log ('RECORD changed ' + $Reason)
    [void](Invoke-Devpipe -Tag 'write-latest' -Arguments @('write-latest', '--repo', $repo, '--id', $Id, '--status', 'STOP_RUN_RECORD_CHANGED', '--reason', $Reason))
    return [pscustomobject]@{ Line = ('DEV-RUN ' + $Id + ' STOP_RUN_RECORD_CHANGED reason=' + $Reason); Code = 2 }
}

function Get-LockState {
    if (-not (Test-Path -LiteralPath $lockPath)) { return 'NONE' }
    $info = $null
    try { $info = [System.IO.File]::ReadAllText($lockPath) | ConvertFrom-Json } catch { $info = $null }
    if ($null -eq $info -or $null -eq $info.pid) {
        # Unreadable lock: it may be in the middle of being written. Treat as held for two minutes.
        $age = ([DateTime]::UtcNow - (Get-Item -LiteralPath $lockPath).LastWriteTimeUtc).TotalSeconds
        if ($age -lt 120) { return 'ALIVE' }
        return 'STALE'
    }
    $holder = Get-Process -Id ([int]$info.pid) -ErrorAction SilentlyContinue
    if ($null -eq $holder) { return 'STALE' }
    try {
        if ($holder.StartTime.ToUniversalTime().Ticks -ne [int64]$info.start_ticks) { return 'STALE' }
    } catch {
        return 'ALIVE'
    }
    return 'ALIVE'
}

function Enter-Lock {
    if ((Get-LockState) -eq 'STALE') {
        Write-Log 'LOCK stale lock removed'
        Remove-Item -LiteralPath $lockPath
    }
    $me = Get-Process -Id $PID
    $payload = '{"pid": ' + $PID + ', "start_ticks": ' + $me.StartTime.ToUniversalTime().Ticks + ', "id": "' + $Id +
        '", "utc": "' + [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') + '"}'
    try {
        $stream = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    } catch {
        return $false
    }
    try {
        $bytes = [System.Text.Encoding]::ASCII.GetBytes($payload)
        $stream.Write($bytes, 0, $bytes.Length)
    } finally {
        $stream.Close()
    }
    $script:lockHeld = $true
    Write-Log ('LOCK taken pid=' + $PID)
    return $true
}

function Exit-Lock {
    if (-not $script:lockHeld) { return }
    try {
        $info = [System.IO.File]::ReadAllText($lockPath) | ConvertFrom-Json
        if ([int]$info.pid -eq $PID) { Remove-Item -LiteralPath $lockPath }
    } catch {
        Write-Log 'LOCK release failed'
    }
    $script:lockHeld = $false
}

function Send-Toast([string]$Text) {
    # Best effort only: the result does not depend on it.
    try {
        $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $nodes = $template.GetElementsByTagName('text')
        [void]$nodes.Item(0).AppendChild($template.CreateTextNode('Investment_V2 dev-run'))
        [void]$nodes.Item(1).AppendChild($template.CreateTextNode($Text))
        $toast = New-Object Windows.UI.Notifications.ToastNotification $template
        $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
    } catch {
        Write-Log ('TOAST failed ' + $_.Exception.GetType().Name)
    }
}

function Get-QuotedList([string[]]$Items) {
    return (($Items | ForEach-Object { '"' + $_ + '"' }) -join ' ')
}

# Headless Builder. Permission flags and allowed tools are constants; only model, effort, turns and
# time come from the validated dev-run block. acceptEdits + --permission-prompts none: anything that
# would ask is refused.
function Start-Builder([int]$Attempt, [string]$PromptText, [string]$WorkingDirectory, [bool]$NewWorktree, [int]$MaxTurns, [int]$TimeoutMinutes) {
    $out = Join-Path $script:runDir ('builder-' + $Attempt + '.json')
    $err = Join-Path $script:runDir ('builder-' + $Attempt + '.err')
    $worktreeArgument = ''
    if ($NewWorktree) { $worktreeArgument = ' --worktree ' + $Id }
    $command = '"' + $script:claude + '" -p "' + $PromptText + '"' + $worktreeArgument +
        ' --model ' + $script:builderModel + ' --effort ' + $script:builderEffort +
        ' --permission-mode acceptEdits --permission-prompts none --max-turns ' + $MaxTurns +
        ' --output-format json --strict-mcp-config --setting-sources project' +
        ' --tools "' + $BuilderToolSet + '" --disallowedTools ' + (Get-QuotedList $BuilderDisallowedTools) +
        ' --allowedTools ' + (Get-QuotedList $BuilderAllowedTools) +
        ' < NUL > "' + $out + '" 2> "' + $err + '"'
    Write-Log ('BUILDER start attempt=' + $Attempt + ' turns=' + $MaxTurns + ' timeout_min=' + $TimeoutMinutes)
    $result = Invoke-Captured -CommandLine $command -WorkingDirectory $WorkingDirectory -TimeoutSeconds ($TimeoutMinutes * 60)
    Write-Log ('BUILDER end attempt=' + $Attempt + ' exit=' + $result.Code + ' timeout=' + $result.TimedOut)
    return $result
}

# Headless Judge: model, effort, tools and turns are script constants; it runs inside the worktree and
# reads only the files devpipe copied from the main checkout records and the base commit.
function Start-Judge([int]$Attempt) {
    $out = Join-Path $script:runDir ('judge-' + $Attempt + '.json')
    $err = Join-Path $script:runDir ('judge-' + $Attempt + '.err')
    $promptText = 'Read workspace/outputs/dev-runs/' + $Id + '/judge-prompt.md and follow it exactly.'
    $command = '"' + $script:claude + '" -p "' + $promptText + '" --model opus --effort xhigh --tools "Read,Grep,Glob"' +
        ' --permission-prompts none --output-format json --strict-mcp-config --setting-sources project' +
        ' --disallowedTools "mcp__*" --max-turns ' + $JudgeMaxTurns +
        ' < NUL > "' + $out + '" 2> "' + $err + '"'
    Write-Log ('JUDGE start attempt=' + $Attempt)
    $result = Invoke-Captured -CommandLine $command -WorkingDirectory $worktree -TimeoutSeconds ($JudgeTimeoutMinutes * 60)
    Write-Log ('JUDGE end attempt=' + $Attempt + ' exit=' + $result.Code + ' timeout=' + $result.TimedOut)
    return $result
}

function Complete-Run([string]$Status, [int]$Retries, [string]$Reason) {
    Stop-Baseline
    $changed = Test-Records 'write-result'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    $arguments = @('write-result', '--run-dir', $script:runDir, '--status', $Status, '--retries', [string]$Retries)
    if (-not [string]::IsNullOrWhiteSpace($Reason)) { $arguments += @('--reason', $Reason) }
    $written = Invoke-Devpipe -Tag 'write-result' -Arguments $arguments
    $line = $written.Line
    if ([string]::IsNullOrWhiteSpace($line)) { $line = 'DEV-RUN ' + $Id + ' ' + $Status + ' (write-result failed)' }
    $code = 1
    if ($written.Code -eq 0) { $code = 0 }
    return [pscustomobject]@{ Line = $line; Code = $code }
}

function Invoke-FixPass([int]$Turns, [int]$TimeoutMinutes) {
    $changed = Test-Records 'fix-prep-1'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    $prep = Invoke-Devpipe -Tag 'fix-prep-1' -Arguments @('fix-prep', '--run-dir', $script:runDir, '--attempt', '1')
    if ($prep.Code -ne 0) { return (Complete-Run $prep.Status 1 (Get-LineReason $prep.Line)) }
    $fixTurns = [int][Math]::Ceiling($Turns / 2)
    $fixTimeout = [int][Math]::Ceiling($TimeoutMinutes / 2)
    $promptText = 'Read workspace/outputs/dev-runs/' + $Id + '/fix-1.md and follow it exactly.'
    $changed = Test-Records 'builder-2'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    $fix = Start-Builder -Attempt 2 -PromptText $promptText -WorkingDirectory $worktree -NewWorktree $false -MaxTurns $fixTurns -TimeoutMinutes $fixTimeout
    if ($fix.TimedOut) { return (Complete-Run 'TIMEOUT' 1 'fix_pass') }
    return $null
}

function Invoke-Pipeline {
    $init = Invoke-Devpipe -Tag 'init-run' -Arguments @('init-run', '--repo', $repo, '--id', $Id)
    if ($init.Code -ne 0) {
        [void](Invoke-Devpipe -Tag 'write-latest' -Arguments @('write-latest', '--repo', $repo, '--id', $Id, '--status', $init.Status, '--reason', (Get-LineReason $init.Line)))
        return [pscustomobject]@{ Line = ('DEV-RUN ' + $Id + ' ' + $init.Status + ' reason=' + (Get-LineReason $init.Line)); Code = 2 }
    }
    if (-not ($init.Line -match 'model=(opus|sonnet) effort=(low|medium|high|xhigh) turns=(\d{1,3}) timeout=(\d{1,3})')) {
        return [pscustomobject]@{ Line = ('DEV-RUN ' + $Id + ' STOP_INTERNAL reason=init_line'); Code = 2 }
    }
    $script:builderModel = $Matches[1]
    $script:builderEffort = $Matches[2]
    $turns = [int]$Matches[3]
    $timeout = [int]$Matches[4]
    if ($turns -lt 1 -or $turns -gt 300 -or $timeout -lt 1 -or $timeout -gt 120) {
        return [pscustomobject]@{ Line = ('DEV-RUN ' + $Id + ' STOP_INTERNAL reason=init_range'); Code = 2 }
    }

    # From here every record goes to the run folder in the main checkout.
    $previousLog = $script:logPath
    $script:consoleDir = Join-Path $script:runDir 'console'
    New-Item -ItemType Directory -Force -Path $script:consoleDir | Out-Null
    $script:logPath = Join-Path $script:runDir 'log.txt'
    Copy-Item -LiteralPath $previousLog -Destination $script:logPath
    $runInfo = [System.IO.File]::ReadAllText((Join-Path $script:runDir 'run.json'), [System.Text.Encoding]::UTF8) | ConvertFrom-Json
    $script:claude = [string]$runInfo.claude_exe
    if ([string]::IsNullOrWhiteSpace($script:claude) -or -not (Test-Path -LiteralPath $script:claude -PathType Leaf)) {
        return (Complete-Run 'STOP_CLAUDE_NOT_FOUND' 0 '')
    }
    $saved = Save-Records
    if ($saved -ne '') { return (Stop-RecordChanged ('init-run:' + $saved)) }

    # D3: a cached baseline is used at once. Otherwise baseline-prepare creates the temporary baseline
    # worktree now (synchronously, so it never overlaps the Builder's own worktree creation) and the suite
    # runs in the background while the Builder works. Cleanup is due from here on every exit path.
    $changed = Test-Records 'baseline-prepare'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    $script:baselineCleanupDue = $true
    $prepare = Invoke-Devpipe -Tag 'baseline-prepare' -Arguments @('baseline-prepare', '--run-dir', $script:runDir)
    if ($prepare.Code -eq 0 -and $prepare.Status -eq 'PENDING') {
        Start-Baseline
    } elseif ($prepare.Code -ne 0 -or $prepare.Status -ne 'OK') {
        return (Complete-Run $prepare.Status 0 (Get-LineReason $prepare.Line))
    }
    $saved = Save-Records
    if ($saved -ne '') { return (Stop-RecordChanged ('baseline-prepare:' + $saved)) }

    # Re-measure the copied ignored files right before Claude Code creates the worktree. The fix pass keeps
    # this snapshot: its worktree copies were made at this creation.
    $changed = Test-Records 'snapshot-includes'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    $snapshot = Invoke-Devpipe -Tag 'snapshot-includes' -Arguments @('snapshot-includes', '--run-dir', $script:runDir)
    if ($snapshot.Code -ne 0) { return (Complete-Run $snapshot.Status 0 (Get-LineReason $snapshot.Line)) }
    $saved = Save-Records
    if ($saved -ne '') { return (Stop-RecordChanged ('snapshot-includes:' + $saved)) }

    # O3b: the main checkout before Builder attempt 1, compared right before every check.
    $changed = Test-Records 'main-snapshot'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    $main = Invoke-Devpipe -Tag 'main-snapshot' -Arguments @('main-snapshot', '--run-dir', $script:runDir)
    if ($main.Code -ne 0) { return (Complete-Run $main.Status 0 (Get-LineReason $main.Line)) }
    $saved = Save-Records
    if ($saved -ne '') { return (Stop-RecordChanged ('main-snapshot:' + $saved)) }

    $changed = Test-Records 'builder-1'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    $promptText = 'Read tools/dev_pipeline/builder-rules.md and docs/claude/' + $Id + '-builder-prompt.md, then follow them exactly.'
    $builder = Start-Builder -Attempt 1 -PromptText $promptText -WorkingDirectory $repo -NewWorktree $true -MaxTurns $turns -TimeoutMinutes $timeout
    if ($builder.TimedOut) { return (Complete-Run 'TIMEOUT' 0 'builder') }

    # The Builder has ended: wait for the baseline (same base, python and branch condition; its own limits),
    # then remove its temporary worktree and branch before any check runs.
    $changed = Test-Records 'baseline-wait'
    if ($changed -ne '') { return (Stop-RecordChanged $changed) }
    if ($null -ne $script:baselineProc) {
        $waited = Wait-Baseline
        Stop-Baseline
        if ($waited.Code -ne 0 -or $waited.Status -ne 'OK') {
            $status = $waited.Status
            if ($status -cnotmatch '^STOP_[A-Z0-9_]+$') { $status = 'STOP_BASELINE' }
            return (Complete-Run $status 0 (Get-LineReason $waited.Line))
        }
        $saved = Save-Records
        if ($saved -ne '') { return (Stop-RecordChanged ('baseline:' + $saved)) }
    } else {
        Stop-Baseline
    }

    $attempt = 1
    while ($true) {
        $changed = Test-Records ('check-' + $attempt)
        if ($changed -ne '') { return (Stop-RecordChanged $changed) }
        $mainCheck = Invoke-Devpipe -Tag ('main-compare-' + $attempt) -Arguments @('main-compare', '--run-dir', $script:runDir, '--name', ('check-' + $attempt))
        if ($mainCheck.Code -ne 0) { return (Complete-Run $mainCheck.Status ($attempt - 1) (Get-LineReason $mainCheck.Line)) }
        $check = Invoke-Devpipe -Tag ('check-' + $attempt) -Arguments @('check', '--run-dir', $script:runDir, '--attempt', [string]$attempt)
        if ($check.Code -eq 1) {
            if ($attempt -eq 1) {
                $stopped = Invoke-FixPass -Turns $turns -TimeoutMinutes $timeout
                if ($null -ne $stopped) { return $stopped }
                $attempt = 2
                continue
            }
            return (Complete-Run 'FAIL' 1 'checks_failed_after_fix')
        }
        if ($check.Code -ne 0) { return (Complete-Run $check.Status ($attempt - 1) '') }

        $changed = Test-Records ('judge-prep-' + $attempt)
        if ($changed -ne '') { return (Stop-RecordChanged $changed) }
        $prep = Invoke-Devpipe -Tag ('judge-prep-' + $attempt) -Arguments @('judge-prep', '--run-dir', $script:runDir, '--attempt', [string]$attempt)
        if ($prep.Code -ne 0) { return (Complete-Run $prep.Status ($attempt - 1) (Get-LineReason $prep.Line)) }
        $changed = Test-Records ('judge-' + $attempt)
        if ($changed -ne '') { return (Stop-RecordChanged $changed) }
        $judge = Start-Judge -Attempt $attempt
        if ($judge.TimedOut) { return (Complete-Run 'TIMEOUT' ($attempt - 1) 'judge') }
        $changed = Test-Records ('parse-judge-' + $attempt)
        if ($changed -ne '') { return (Stop-RecordChanged $changed) }
        $parsed = Invoke-Devpipe -Tag ('parse-judge-' + $attempt) -Arguments @('parse-judge', '--run-dir', $script:runDir, '--attempt', [string]$attempt)
        if ($parsed.Code -eq 0) { return (Complete-Run 'PASS' ($attempt - 1) '') }
        if ($parsed.Code -eq 1) {
            if ($attempt -eq 1) {
                $stopped = Invoke-FixPass -Turns $turns -TimeoutMinutes $timeout
                if ($null -ne $stopped) { return $stopped }
                $attempt = 2
                continue
            }
            return (Complete-Run 'FAIL' 1 'judge_fail_after_fix')
        }
        return (Complete-Run $parsed.Status ($attempt - 1) (Get-LineReason $parsed.Line))
    }
}

# ---- main ----
$python = Find-Python
if ([string]::IsNullOrWhiteSpace($python) -or -not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Write-Output ('DEV-RUN ' + $Id + ' STOP_PREFLIGHT reason=PYTHON_NOT_FOUND')
    exit 2
}
New-Item -ItemType Directory -Force -Path $runsRoot | Out-Null
Write-Log ('START id=' + $Id + ' preflight=' + [bool]$Preflight + ' pid=' + $PID)

$mode = 'run'
if ($Preflight) { $mode = 'preflight' }
if ((Get-LockState) -eq 'ALIVE') {
    if (-not $Preflight) {
        [void](Invoke-Devpipe -Tag 'write-latest' -Arguments @('write-latest', '--repo', $repo, '--id', $Id, '--status', 'STOP_PREFLIGHT', '--reason', 'LOCKED'))
    }
    Write-Output ('DEV-RUN ' + $Id + ' STOP_PREFLIGHT reason=LOCKED')
    exit 2
}
$check = Invoke-Devpipe -Tag 'preflight' -Arguments @('preflight', '--repo', $repo, '--id', $Id, '--mode', $mode)
if ($check.Code -ne 0) {
    $line = $check.Line
    if ([string]::IsNullOrWhiteSpace($line)) { $line = 'DEV-RUN ' + $Id + ' STOP_PREFLIGHT reason=DEVPIPE_FAILED' }
    Write-Output $line
    exit 2
}
if ($Preflight) {
    Write-Output $check.Line
    exit 0
}
if (-not (Enter-Lock)) {
    [void](Invoke-Devpipe -Tag 'write-latest' -Arguments @('write-latest', '--repo', $repo, '--id', $Id, '--status', 'STOP_PREFLIGHT', '--reason', 'LOCKED'))
    Write-Output ('DEV-RUN ' + $Id + ' STOP_PREFLIGHT reason=LOCKED')
    exit 2
}

$final = $null
try {
    $final = Invoke-Pipeline
} catch {
    Write-Log ('RUNNER_ERROR ' + $_.Exception.GetType().Name + ' ' + $_.Exception.Message)
    if (Test-Path -LiteralPath (Join-Path $script:runDir 'run.json')) {
        $final = Complete-Run 'STOP_RUNNER_ERROR' 0 $_.Exception.GetType().Name
    } else {
        [void](Invoke-Devpipe -Tag 'write-latest' -Arguments @('write-latest', '--repo', $repo, '--id', $Id, '--status', 'STOP_RUNNER_ERROR', '--reason', $_.Exception.GetType().Name))
        $final = [pscustomobject]@{ Line = ('DEV-RUN ' + $Id + ' STOP_RUNNER_ERROR'); Code = 2 }
    }
} finally {
    # Normally already done by Complete-Run; this covers an error thrown anywhere before it.
    try { Stop-Baseline } catch { Write-Log ('BASELINE cleanup error ' + $_.Exception.GetType().Name) }
    Exit-Lock
}
Write-Log ('END ' + $final.Line)
Write-Output (Get-AsciiText $final.Line)
Send-Toast (Get-AsciiText $final.Line)
exit $final.Code
