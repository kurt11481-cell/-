# commit-docs.ps1 - commit docs/claude changes listed by Cowork sessions (one commit per pending file).
#
# Pending files: docs/claude/_pending/<task-id>.txt (UTF-8, git-ignored)
#   line 1      = commit message
#   other lines = repo-relative paths, each under docs/claude/ (blank lines ignored)
#
# Safety: only paths under docs/claude/ are accepted; stops if anything is already staged;
# commits only the listed paths; never pushes; -DryRun shows what would happen and changes nothing.
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as the ANSI code page.
#
# Usage (Windows PowerShell, repo root):  .\tools\commit-docs.ps1 -DryRun   then   .\tools\commit-docs.ps1

param([switch]$DryRun)

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
