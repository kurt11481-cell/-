# Merge journal-venue (manual route, K3): the CEO-office company-PC project thread records holding-card S7b journal entries
# with --confirmed-via PROJECT_THREAD_USER_DECISION after the user's own typed decision or card tap in that thread.
# User approval: direction C typed 2026-10-27 14:59 KST; start approval card tap 15:27 KST (proposal doc section 8).
# Judge: docs/claude/journal-venue-judge-report.md (PASS_WITH_FIX, fixes applied, re-check PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'journal-venue'
function Stop-Merge([string]$why) { Write-Output ('JOURNAL_VENUE_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
Write-Host ('Authority merge. To approve, type the id exactly: ' + $Id) -NoNewline
Write-Host ' > ' -NoNewline
$typed = [Console]::ReadLine()
if ($typed -cne $Id) { Stop-Merge 'id not confirmed' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\journal-venue'
$base = (git -C $repo rev-parse 3542b10).Trim()
$branch = 'worktree-journal-venue'
$judge = Join-Path $repo 'docs\claude\journal-venue-judge-report.md'
$hashes = @{
    'CLAUDE.md' = 'fcf6d25bc6e5888a133eedc7a4d039fe4821b5a86d02ae73e319d381100c27b2';
    'docs/claude/journal-venue-builder-report.md' = 'c0a236a6427f469a427b6e13d5878e9722c31ebf11e825fd4adbdd80646a089d';
    'manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json' = '4ea21febc9b7cb2d0cd8d0a256a43405b90291de5c3e72568bbe1e5e5fc0a6f9';
    'manage-us-stock-strategy/scripts/portfolio_review_journal.py' = 'c29f9d87fd3d3762b0cfcc0807b1b5a846fee74bb04f6a01341c4ec216d6cb23';
    'manage-us-stock-strategy/tests/test_portfolio_review_journal.py' = 'b5b1c6ed4c557e5bf4a501dd0848b1aca7b165274001f30e5026d696969bb14a'
}
$paths = @($hashes.Keys | Sort-Object)
# Hard safety lines 18-53 after the change, CR stripped (LF form).
$hardSafety = 'feaf24629ea4703f5370bb2cc67a58729ed0b9782b4afb20241ce17d6ae0d267'

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
if ($last -ne 'VERDICT: PASS') { Stop-Merge ('judge verdict: ' + $last) }
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
$section = (($lines[17..52]) -join "`n") + "`n"
$sha = [System.Security.Cryptography.SHA256]::Create()
$hs = -join ($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($section)) | ForEach-Object { $_.ToString('x2') })
if ($hs -ne $hardSafety) { Stop-Merge 'Hard safety section changed after review' }
if (-not $text.Contains('Holding-card S7b entries (card_decision, card_user_decision) only.')) { Stop-Merge 'judge fix 2 missing' }
if (-not $text.Contains('PROJECT_THREAD_USER_DECISION')) { Stop-Merge 'exception sentence missing' }
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
Push-Location $wt
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_review_journal.py" 2>&1 | Select-Object -Last 3
$t1 = $LASTEXITCODE
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_decision_journal_cards.py" 2>&1 | Select-Object -Last 3
$t2 = $LASTEXITCODE
Pop-Location
if ($t1 -ne 0 -or $t2 -ne 0) { Stop-Merge 'targeted tests failed before merge' }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'journal-venue-commit-message.txt'
$msg = "feat(journal): project thread records holding-card S7b entries after the user's own decision (journal-venue)`n`n" +
       "journal-venue (K3, manual route; user direction C typed 2026-10-27 14:59 KST, start approval card tap 15:27 KST,`n" +
       "merge by the user's own PowerShell line). New confirmation method PROJECT_THREAD_USER_DECISION: only card_decision and`n" +
       "card_user_decision entries, user_message '<message or card id> | <account id> | <KST time> | <text>' (no code).`n" +
       "COWORK, USER_TERMINAL and AUTO_CORE paths unchanged. CLAUDE.md Hard safety exception and Decision journal line.`n" +
       "Builder docs/claude/journal-venue-builder-report.md, Judge docs/claude/journal-venue-judge-report.md (re-check PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKhT4YwBCwV2e9YM3JH`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge journal-venue (project thread records S7b journal; K3, Judge re-check PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'JOURNAL_VENUE_DONE'
