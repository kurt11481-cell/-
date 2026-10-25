# dev-merge.ps1 - the user's one step after a dev-run: merge a READY_TO_MERGE task (redesign T3).
#
# Usage (Windows PowerShell, main checkout):  .\tools\dev-merge.ps1 <id> [-ApproveAuthority]
# -ApproveAuthority works only in an interactive console (ConsoleHost, nothing redirected, console handles),
# then waits for Enter once.
#
# Trusts only workspace\outputs\dev-runs\<id>\result.json in the main checkout (files inside the worktree
# are not evidence). tools\dev_pipeline\devpipe.py recomputes every condition before anything changes:
# status, Judge file sha256 and a fresh PASS parse, diff_hash, protected and allowed paths, no BLOCKED.md,
# worktree HEAD = base, main branch as recorded, nothing staged in main. Authority-class changes stop with
# NEEDS_APPROVAL unless -ApproveAuthority is given, and that switch is accepted only for NEEDS_APPROVAL.
# Then it commits only the changed paths in the worktree (message from a UTF-8 file, git commit -F) and
# fast-forwards the main branch (git merge --ff-only). If main moved on with docs/claude-only commits that
# do not touch these paths, it rebases in the worktree, checks the patch-id and reruns the tests first.
# Never publishes to a remote, never forces, never deletes branches or worktrees.
# Exit codes: 0 merged, 2 stopped, 3 user approval needed.
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as the ANSI code page.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Id,
    [switch]$ApproveAuthority
)

$ErrorActionPreference = 'Stop'
$IdPattern = '^[a-z0-9][a-z0-9-]{1,47}$'

function Get-AsciiText([string]$Text) {
    if ($null -eq $Text) { return '' }
    $chars = foreach ($c in $Text.ToCharArray()) { if ([int]$c -ge 32 -and [int]$c -lt 127) { $c } else { '?' } }
    return (-join $chars)
}

if ($Id -cnotmatch $IdPattern) {
    Write-Output ('DEV-MERGE ' + (Get-AsciiText $Id) + ' STOP_ID_FORMAT')
    exit 2
}

if ($ApproveAuthority) {
    # hnd-check: an authority merge only when run by hand at an interactive console. This stops piped,
    # redirected and headless runs; it is not proof of a person: a pseudo console, or automation typing into
    # a real or a new console window (which waits at the Enter step below), still passes.
    if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or $Host.Name -ne 'ConsoleHost' -or
            -not [Environment]::UserInteractive) {
        Write-Output ('DEV-MERGE ' + $Id + ' STOP_NOT_INTERACTIVE')
        exit 2
    }
    # hnd-check2: both standard handles must also be console handles (GetConsoleMode; a pipe, a file or NUL
    # fails it). If the check cannot be built or run, it stops the same way (fail closed).
    $consoleHandles = $false
    try {
        Add-Type -TypeDefinition @'
            using System;
            using System.Runtime.InteropServices;
            public static class DevMergeConsoleHandles {
                [DllImport("kernel32.dll")]
                static extern IntPtr GetStdHandle(int which);
                [DllImport("kernel32.dll")]
                static extern bool GetConsoleMode(IntPtr handle, out uint mode);
                public static bool Both() {
                    uint mode;
                    return GetConsoleMode(GetStdHandle(-10), out mode) && GetConsoleMode(GetStdHandle(-11), out mode);
                }
            }
'@
        $consoleHandles = [DevMergeConsoleHandles]::Both()
    } catch {
        $consoleHandles = $false
    }
    if ($consoleHandles -ne $true) {
        Write-Output ('DEV-MERGE ' + $Id + ' STOP_NOT_INTERACTIVE')
        exit 2
    }
    # hnd-check2 fix 1: after every check above, the person at the keyboard presses Enter once. What is typed
    # is not compared. A new console window nobody types into waits here; the end of input ($null) or any
    # error stops the same way (fail closed).
    $entered = $null
    try {
        Write-Host -NoNewline 'Authority merge. Press Enter to continue (Ctrl+C cancels): '
        $entered = [Console]::ReadLine()
    } catch {
        $entered = $null
    }
    if ($null -eq $entered) {
        Write-Output ('DEV-MERGE ' + $Id + ' STOP_NOT_INTERACTIVE')
        exit 2
    }
}

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$devpipe = Join-Path $PSScriptRoot 'dev_pipeline\devpipe.py'
$runsRoot = Join-Path $repo 'workspace\outputs\dev-runs'
$cmdExe = $env:ComSpec
if ([string]::IsNullOrWhiteSpace($cmdExe)) { $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe' }

$candidates = @((Join-Path $repo '.venv\Scripts\python.exe'), (Join-Path $repo 'venv\Scripts\python.exe'))
$python = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($python)) {
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -eq $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
    if ($null -ne $command) { $python = $command.Source }
}
if ([string]::IsNullOrWhiteSpace($python)) {
    Write-Output ('DEV-MERGE ' + $Id + ' STOP_PYTHON_NOT_FOUND')
    exit 2
}

$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$consoleDir = Join-Path $runsRoot ('_merge\' + $stamp + '-' + $Id)
New-Item -ItemType Directory -Force -Path $consoleDir | Out-Null
$base = Join-Path $consoleDir 'merge'

$arguments = @('merge', '--repo', $repo, '--id', $Id)
if ($ApproveAuthority) { $arguments += '--approve-authority' }
$quoted = ($arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
$commandLine = '"' + $python + '" "' + $devpipe + '" ' + $quoted + ' < NUL > "' + $base + '.out" 2> "' + $base + '.err"'

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $cmdExe
$psi.Arguments = '/d /s /c "' + $commandLine + '"'
$psi.WorkingDirectory = $repo
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$proc = [System.Diagnostics.Process]::Start($psi)
$proc.WaitForExit()
$code = $proc.ExitCode

$line = ''
if (Test-Path -LiteralPath ($base + '.out')) {
    $lines = @([System.IO.File]::ReadAllLines($base + '.out'))
    if ($lines.Count -gt 0) { $line = [string]$lines[0] }
}
if ([string]::IsNullOrWhiteSpace($line)) { $line = 'DEV-MERGE ' + $Id + ' STOP_NO_OUTPUT (see ' + $base + '.err)' }
Write-Output (Get-AsciiText $line)
if ($code -ne 0 -and $code -ne 3) { $code = 2 }
exit $code
