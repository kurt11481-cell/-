# Merge btn-approval (manual route, K3: button tap on the thread's decision card counts as approval in the Change classes item).
# User approval: 'btn-approval 착수 승인' typed in the project thread 2026-10-27 10:20 KST; card tap T0 10:22 KST (proposal doc, decision record).
# Judge: docs/claude/btn-approval-judge-report.md (PASS_WITH_FIX, fix applied and re-checked read-only by the project thread).
# The merge itself is the user's one line in their own interactive Windows PowerShell. Only CLAUDE.md and the Builder report change.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'btn-approval'
function Stop-Merge([string]$why) { Write-Output ('BTN_APPROVAL_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
Write-Host ('Authority merge. To approve, type the id exactly: ' + $Id) -NoNewline
Write-Host ' > ' -NoNewline
$typed = [Console]::ReadLine()
if ($typed -cne $Id) { Stop-Merge 'id not confirmed' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\btn-approval'
$base = (git -C $repo rev-parse 672f52c).Trim()
$branch = 'worktree-btn-approval'
$judge = Join-Path $repo 'docs\claude\btn-approval-judge-report.md'
$hashes = @{
    'CLAUDE.md' = '460ac219b052b98817f0848a01c202860868a963a7c0c93baad6efc70f8340df';
    'docs/claude/btn-approval-builder-report.md' = '0b86d4d1d67b3e045855fe2dc6d4c24b8f58c49102bec90acce731c1710226d5'
}
$paths = @($hashes.Keys | Sort-Object)
# Hard safety lines 18-45, CR stripped (LF form).
$hardSafety = '93d87a33b42d2a14d030bf4b4431019f0f0f771ef93b364c59a71ed1392173ec'

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
# Main may have moved (other merges); only the merged paths must be untouched since base.
$moved = @(git -C $repo diff --name-only $base HEAD)
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
$text = [System.IO.File]::ReadAllText((Join-Path $wt 'CLAUDE.md'), (New-Object System.Text.UTF8Encoding($false)))
$lines = $text -split "`r?`n"
$section = (($lines[17..44]) -join "`n") + "`n"
$sha = [System.Security.Cryptography.SHA256]::Create()
$hs = -join ($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($section)) | ForEach-Object { $_.ToString('x2') })
if ($hs -ne $hardSafety) { Stop-Merge 'Hard safety section changed' }
if (-not $text.Contains('any other button or card')) { Stop-Merge 'judge fix 1 missing' }
if (-not $text.Contains('In this item, the current conversation may also be')) { Stop-Merge 'scope phrase missing' }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'btn-approval-commit-message.txt'
$msg = "docs(rules): button tap on the thread's decision card counts as approval in Change classes (btn-approval)`n`n" +
       "btn-approval (K3, manual route; user message 'btn-approval start approval' 2026-10-27 10:20 KST, card tap T0 10:22 KST,`n" +
       "merge by the user's own PowerShell line). CLAUDE.md Change classes: the user's own tap on a decision card that the same`n" +
       "thread posted for that proposal counts, only with the four-field record from the harness wake; any other button or card,`n" +
       "relayed quotes, summaries and scheduled turns do not. Hard safety section unchanged. Builder`n" +
       "docs/claude/btn-approval-builder-report.md, Judge docs/claude/btn-approval-judge-report.md.`n`n" +
       "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKhoFkD8XAg8TK9Qouz`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge btn-approval (button approval in Change classes; K3, Judge PASS_WITH_FIX applied)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'BTN_APPROVAL_DONE'
