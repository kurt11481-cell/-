# Merge hwm-fix (manual route, K3: S7 HWM held-session revaluation 1 + superseded line reviews 3) after the
# independent Judge PASS. Cowork, 2026-10-17. ASCII only.
# Checks: no dev-run lock and no auto-core / dev / docs-commit / t2rc-check task running; Judge report ends with
# VERDICT: PASS; main moved only by docs/claude commits since base 1259f56; the worktree changed exactly the 8 listed
# paths; the 8 files still have the sha256 the Judge measured (nothing changed after the review). Then it commits the
# 8 paths in the worktree, merges --no-ff into the main branch and runs the S7 and auto-core tests on main.
# No order, no Kiwoom, no policy, state, ledger or journal write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\hwm-fix'
$base = '1259f566c729f9a4197359b4495b60821adef59d'
$branch = 'worktree-hwm-fix'
$judge = Join-Path $repo 'docs\claude\hwm-fix-judge-report.md'
$hashes = @{
    'docs/claude/hwm-fix-report.md' = '325ce620907941870551ee0cda8b6680a7d8dd8f65ae21d4733cf5a9274e706f';
    'manage-us-stock-strategy/scripts/portfolio_exposure.py' = '9397108ee0f15696206f80681148cb20431d6deb72e915c5aa9774aff9b77a72';
    'manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py' = '4ae1eedfc2475a97819055af8f31c90841ee03958fe844502f198cdfc161fb78';
    'manage-us-stock-strategy/tests/test_portfolio_exposure_hwm_fix.py' = '5e19fa570fc9202c67c9ff2b77786603aa95a46ef699841872df8921d5359ae1';
    'manage-us-stock-strategy/tests/test_run_portfolio_exposure_review_hwm_fix.py' = '84382d5ba8cacb0975816934dfe46a1104b94a58a365258ecee764b83481eb1c';
    'manage-us-stock-strategy/tests/test_portfolio_exposure_fail_closed.py' = 'd3129cabff136db2d1c52a5f19e24448889df173e5e73714464fe774db7cee80';
    'manage-us-stock-strategy/tests/test_portfolio_exposure_judge_fixes.py' = '1a24514cde57a4671c812e1b6b9e1d6f37bc7f8f500e7a213f65732e0fdbd193';
    'manage-us-stock-strategy/tests/test_auto_core_risk1r.py' = 'e2f16d19214830e5d66b153c92ae354314acf9270faf9c8417905cc972a56e70'
}
$paths = @($hashes.Keys | Sort-Object)
function Stop-Merge([string]$why) { Write-Output ('HWMFIX_STOP ' + $why); exit 2 }

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
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$moved = @(git -C $repo diff --name-only $base HEAD)
$nonDocs = @($moved | Where-Object { -not $_.StartsWith('docs/claude/') })
if ($nonDocs.Count -ne 0) { Stop-Merge ('main moved with non-docs commits: ' + ($nonDocs -join ',')) }
if ((git -C $wt rev-parse HEAD).Trim() -ne $base) { Stop-Merge 'worktree head is not base' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $paths) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $repo 'workspace\outputs\hwm-fix-commit-message.txt'
$msg = "fix(s7 exposure): revalue released held sessions from the post-close broker snapshot (HWM D6)`n`n" +
       "hwm-fix (K3, manual route; user decisions hwm-fix a 2026-10-15 and rrec-k3-timing d 2026-10-16, scope 1+3):`n" +
       "a session whose cash-flow and sale holds have all ended is no longer skipped forever. It is revalued with the`n" +
       "first confirmed reconciliation captured after its close (or a bracketing pair with equal holdings and cash),`n" +
       "using the linked broker snapshot's order-available cash; anything it cannot revalue fails closed. R6 flows are`n" +
       "counted once, the HWM is never below the old rule, and the evaluation session's own hold stays HELD. Line reviews`n" +
       "recorded against an event the recomputation moved are listed as superseded, not completed. The runner supplies`n" +
       "broker captures and session times only. Past EV4 records, the t2rc oracle and auto-core code are unchanged;`n" +
       "risk1r GOLDEN updated for the new s7_review_id only. Real data: HWM 31711.76 (2026-10-06), L1 2026-10-12,`n" +
       "L2 2026-10-15. Builder docs/claude/hwm-fix-report.md, Judge docs/claude/hwm-fix-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KM6Hnjbw6Y2CKGRm5ECpPo`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge hwm-fix (S7 HWM held-session revaluation, K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $repo
$failed = $false
foreach ($pattern in @('test_portfolio_exposure*.py', 'test_run_portfolio_exposure_review*.py', 'test_auto_core*.py')) {
    Write-Output ('TESTS ' + $pattern)
    python -m unittest discover -s manage-us-stock-strategy/tests -p $pattern 2>&1 | Select-Object -Last 3 | ForEach-Object { Write-Output ('  ' + $_) }
    if ($LASTEXITCODE -ne 0) { $failed = $true }
}
Pop-Location
if ($failed) { Write-Output 'HWMFIX_TESTS_FAILED_ON_MAIN (merge kept; Cowork review)'; exit 2 }
Write-Output 'HWMFIX_DONE'
