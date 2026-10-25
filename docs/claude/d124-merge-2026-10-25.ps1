# Merge d124-approval-venue (manual route, K3: approval venue D4 b, official terminal route D2, dashboard updater D1 a).
# User approval: user's own thread messages "D4 b 승인, D2 승인, D1 a 승인" (2026-10-25 08:15Z), "제안 수락" (08:18Z), Q1 "아니오" (08:17Z).
# Judge: docs/claude/d124-judge-report.md (PASS_WITH_FIX, fix applied and re-checked read-only by the project thread).
# The merge itself is the user's one line in their own interactive Windows PowerShell. Only CLAUDE.md and the Builder report change.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'd124'
function Stop-Merge([string]$why) { Write-Output ('D124_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
Write-Host ('Authority merge. To approve, type the id exactly: ' + $Id) -NoNewline
Write-Host ' > ' -NoNewline
$typed = [Console]::ReadLine()
if ($typed -cne $Id) { Stop-Merge 'id not confirmed' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\d124-approval-venue'
$base = (git -C $repo rev-parse b6a83e2).Trim()
$branch = 'worktree-d124-approval-venue'
$judge = Join-Path $repo 'docs\claude\d124-judge-report.md'
$hashes = @{
    'CLAUDE.md' = '1feb18f5ee10bb5d4e16a5e3a76f6aca4c58cde80e7d0a1fe7d2da62790c8159';
    'docs/claude/d124-builder-report.md' = '896a466248d2bdb108c1d8b9c7c6d578ecc2a8c2f8028e38c9faf40ad73aa8c0'
}
$paths = @($hashes.Keys | Sort-Object)
$hardSafety = '7d60922e76a9fb08a2996bcfae8aff455807cd0c04249645ea78d0491fee8232'

$kst = [DateTime]::UtcNow.AddHours(9)
$tueSat = @('Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday') -contains $kst.DayOfWeek.ToString()
$minute = $kst.Hour * 60 + $kst.Minute
if ($tueSat -and $minute -ge 360 -and $minute -lt 540) { Stop-Merge 'inside Tue-Sat 06:00-09:00 KST' }
if ($minute -ge 1400 -and $minute -lt 1425) { Stop-Merge 'inside 23:20-23:45 KST (docs-commit)' }
if (Test-Path -LiteralPath (Join-Path $repo 'workspace\outputs\dev-runs\_lock')) { Stop-Merge 'dev-run lock held' }
foreach ($t in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide', 'InvestmentV2-DevQueue', 'InvestmentV2-DocsCommit',
                 'InvestmentV2-T2rcCheck')) {
    $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') { Stop-Merge ($t + ' running') }
}
if (-not (Test-Path -LiteralPath $judge)) { Stop-Merge 'judge report missing' }
$last = (Get-Content -LiteralPath $judge -Encoding UTF8 | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1).Trim()
if ($last -ne 'VERDICT: PASS_WITH_FIX_APPLIED') { Stop-Merge ('judge verdict: ' + $last) }
$mainBranch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
if ($mainBranch -ne 'codex/master-recovery-expansion') { Stop-Merge ('main branch ' + $mainBranch) }
git -C $repo merge-base --is-ancestor $base HEAD
if ($LASTEXITCODE -ne 0) { Stop-Merge 'base is not an ancestor of main' }
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$moved = @(git -C $repo diff --name-only $base HEAD)
$unknown = @($moved | Where-Object { -not $_.StartsWith('docs/claude/') })
if ($unknown.Count -ne 0) { Stop-Merge ('main moved with non-docs paths: ' + ($unknown -join ',')) }
$overlap = @($moved | Where-Object { $paths -contains $_ })
if ($overlap.Count -ne 0) { Stop-Merge ('a merged path changed on main since base: ' + ($overlap -join ',')) }
$dirty = @(git -C $repo status --porcelain -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
if ((git -C $wt rev-parse HEAD).Trim() -ne $base) { Stop-Merge 'worktree head is not base' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $paths) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
# Hard safety section (lines 18-44, CR stripped) must equal the reviewed hash in the worktree file.
$text = [System.IO.File]::ReadAllText((Join-Path $wt 'CLAUDE.md'), (New-Object System.Text.UTF8Encoding($false)))
$lines = $text -split "`r?`n"
$section = (($lines[17..43]) -join "`n") + "`n"
$sha = [System.Security.Cryptography.SHA256]::Create()
$hs = -join ($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($section)) | ForEach-Object { $_.ToString('x2') })
if ($hs -ne $hardSafety) { Stop-Merge 'Hard safety section changed' }
if (-not $text.Contains('In this item, the current conversation may also be')) { Stop-Merge 'scope fix missing' }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'd124-commit-message.txt'
$msg = "docs(rules): approval venue, terminal route wording and dashboard updater (d124)`n`n" +
       "d124 (K3, manual route; user messages 'D4 b approve, D2 approve, D1 a approve' 2026-10-25 08:15Z, merge by the`n" +
       "user's own PowerShell line). CLAUDE.md Change classes: the user's own message in the interactive Claude Code project`n" +
       "thread counts as approval for this item only (relayed quotes, buttons, cards, scheduled turns do not); official script`n" +
       "route is the user's PowerShell line; the project thread may start manual-route Builder/Judge after approval. Session`n" +
       "hygiene: the project thread may update the dashboard. Hard safety section unchanged (sha256 7d60922e...). Builder`n" +
       "docs/claude/d124-builder-report.md, Judge docs/claude/d124-judge-report.md.`n`n" +
       "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_018DzzzHWRE89kp8opAxHjeV`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge d124 (approval venue, terminal route, dashboard updater wording; K3, Judge PASS_WITH_FIX applied)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'D124_DONE'
