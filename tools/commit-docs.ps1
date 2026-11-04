# commit-docs.ps1 - commit docs/claude changes listed by Cowork sessions (one commit per pending file).
#
# Pending files: docs/claude/_pending/<task-id>.txt (UTF-8, git-ignored)
#   line 1      = commit message
#   other lines = repo-relative paths, each under docs/claude/ (blank lines ignored)
#
# Safety: only paths under docs/claude/ are accepted; stops if anything is already staged;
# commits only the listed paths; never pushes; -DryRun shows what would happen and changes nothing.
# Protected docs (cd-guard): docs/claude/ lines of tools/dev_pipeline/authority-paths.txt except card-evidence-registry.json.
# A pending file that changes one is a HOLD (kept, counted as a problem); -ApproveProtected commits it after Enter.
# If that list cannot be read or has no docs/claude line, every pending file is a HOLD (fail closed).
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as the ANSI code page.
#
# Usage (Windows PowerShell, repo root):  .\tools\commit-docs.ps1 -DryRun   then   .\tools\commit-docs.ps1
# Protected docs (interactive console only, Enter once):  .\tools\commit-docs.ps1 -ApproveProtected

param([switch]$DryRun, [switch]$ApproveProtected)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repo

$pendingDir = Join-Path $repo 'docs\claude\_pending'
if (-not (Test-Path -LiteralPath $pendingDir)) { Write-Host 'NOTHING: no docs\claude\_pending folder.'; exit 0 }
$files = @(Get-ChildItem -LiteralPath $pendingDir -Filter '*.txt' | Sort-Object Name)
if ($files.Count -eq 0) { Write-Host 'NOTHING: no pending commit files.'; exit 0 }

& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  Write-Host 'STOP: other changes are already staged. Commit or unstage them first (git status).'
  exit 1
}

$utf8 = New-Object System.Text.UTF8Encoding($false)
$failed = 0
$committed = 0

# Protected list: glob -> regex (** = .*, * = [^/]*, rest escaped), anchored, case-insensitive.
$protected = @()
try {
  $authorityFile = Join-Path $repo 'tools\dev_pipeline\authority-paths.txt'
  foreach ($line in [System.IO.File]::ReadAllLines($authorityFile, $utf8)) {
    $g = $line.Trim()
    if ($g -eq '' -or $g.StartsWith('#')) { continue }
    if (-not $g.StartsWith('docs/claude/') -or $g -eq 'docs/claude/card-evidence-registry.json') { continue }
    $rx = ''
    for ($i = 0; $i -lt $g.Length; $i++) {
      if ($g[$i] -eq '*' -and $i + 1 -lt $g.Length -and $g[$i + 1] -eq '*') { $rx += '.*'; $i++ }
      elseif ($g[$i] -eq '*') { $rx += '[^/]*' }
      else { $rx += [regex]::Escape([string]$g[$i]) }
    }
    $protected += New-Object System.Text.RegularExpressions.Regex(('^' + $rx + '$'), 'IgnoreCase')
  }
} catch {
  $protected = @()
}
$protectedOk = ($protected.Count -gt 0)
if (-not $protectedOk) { Write-Host 'WARN: tools/dev_pipeline/authority-paths.txt unreadable or has no docs/claude line; every pending file is a HOLD.' }

$plans = @()
foreach ($f in $files) {
  $raw = [System.IO.File]::ReadAllLines($f.FullName, $utf8)
  $lines = @($raw | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
  if ($lines.Count -lt 2) { Write-Host ("SKIP  {0}: needs a message line and at least one path." -f $f.Name); $failed++; continue }

  $message = $lines[0]
  $paths = @()
  $bad = @()
  foreach ($p in $lines[1..($lines.Count - 1)]) {
    $n = $p.Replace('\', '/')
    if ($n -notmatch '^docs/claude/[^/]' -or $n.Contains('..') -or $n.StartsWith('docs/claude/_pending/')) { $bad += $p } else { $paths += $n }
  }
  if ($bad.Count -gt 0) {
    Write-Host ("STOP  {0}: paths outside docs/claude/ are not allowed: {1}" -f $f.Name, ($bad -join ', '))
    $failed++; continue
  }

  $changed = @()
  foreach ($p in $paths) {
    $st = & git status --porcelain -- $p
    if ($st) { $changed += $p }
  }
  if ($changed.Count -eq 0) {
    Write-Host ("SKIP  {0}: no listed file has changes (probably committed already)." -f $f.Name)
    if (-not $DryRun) { Remove-Item -LiteralPath $f.FullName }
    continue
  }

  if (-not $protectedOk) {
    Write-Host ("HOLD  {0}: protected list unreadable; nothing is committed from this file." -f $f.Name)
    $failed++; continue
  }
  $hits = @()
  foreach ($p in $changed) {
    $c = $p.Replace('\', '/')
    foreach ($r in $protected) { if ($r.IsMatch($c)) { $hits += $p; break } }
  }
  if ($hits.Count -gt 0 -and ($DryRun -or -not $ApproveProtected)) {
    Write-Host ("HOLD  {0}: protected docs need .\tools\commit-docs.ps1 -ApproveProtected" -f $f.Name)
    foreach ($p in $hits) { Write-Host ("      ! {0}" -f $p) }
    $failed++; continue
  }
  $plans += ,@($f, $message, $changed, $hits)
}

# -ApproveProtected: once per run, only when a protected doc is planned (same checks as dev-merge.ps1 39-85).
$approveList = @($plans | ForEach-Object { $_[3] } | Where-Object { $_ })
if (-not $DryRun -and $approveList.Count -gt 0) {
  $interactive = $true
  if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or $Host.Name -ne 'ConsoleHost' -or
      -not [Environment]::UserInteractive) { $interactive = $false }
  if ($interactive) {
    # Both standard handles must be console handles (GetConsoleMode); if the check cannot run, it fails closed.
    $consoleHandles = $false
    try {
      Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class CommitDocsConsoleHandles {
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
      $consoleHandles = [CommitDocsConsoleHandles]::Both()
    } catch {
      $consoleHandles = $false
    }
    if ($consoleHandles -ne $true) { $interactive = $false }
  }
  if ($interactive) {
    # Enter once; what is typed is not compared. End of input ($null) or any error stops (fail closed).
    Write-Host 'Protected docs to commit:'
    foreach ($p in $approveList) { Write-Host ("      ! {0}" -f $p) }
    $entered = $null
    try {
      Write-Host -NoNewline 'Protected docs commit. Press Enter to continue (Ctrl+C cancels): '
      $entered = [Console]::ReadLine()
    } catch {
      $entered = $null
    }
    if ($null -eq $entered) { $interactive = $false }
  }
  if (-not $interactive) {
    Write-Host 'STOP_NOT_INTERACTIVE: -ApproveProtected needs an interactive console. Nothing was committed.'
    exit 2
  }
}

foreach ($plan in $plans) {
  $f = $plan[0]; $message = $plan[1]; $changed = $plan[2]

  Write-Host ("PLAN  {0}: ""{1}""" -f $f.Name, $message)
  foreach ($p in $changed) { Write-Host ("      + {0}" -f $p) }
  if ($DryRun) { continue }

  & git add -- $changed
  if ($LASTEXITCODE -ne 0) { Write-Host ("STOP  {0}: git add failed." -f $f.Name); & git reset -q -- $changed; $failed++; continue }

  # Message goes through a UTF-8 file under .git with a relative ASCII path (pipes would turn Korean into '?').
  $tmp = Join-Path $repo '.git\COMMIT_DOCS_MSG'
  [System.IO.File]::WriteAllText($tmp, $message + "`n", $utf8)
  & git commit -q -F '.git/COMMIT_DOCS_MSG' -- $changed
  $code = $LASTEXITCODE
  Remove-Item -LiteralPath $tmp
  if ($code -ne 0) { Write-Host ("STOP  {0}: git commit failed (exit {1})." -f $f.Name, $code); & git reset -q -- $changed; $failed++; continue }

  $hash = (& git rev-parse --short HEAD).Trim()
  Write-Host ("OK    {0} -> {1}" -f $f.Name, $hash)
  Remove-Item -LiteralPath $f.FullName
  $committed++
}

if ($DryRun) { Write-Host 'DRY RUN: nothing was staged or committed.' }
else { Write-Host ("DONE: {0} commit(s), {1} problem(s). Nothing was pushed." -f $committed, $failed) }
if ($failed -gt 0) { exit 1 }
