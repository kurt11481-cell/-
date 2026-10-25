# Merge hnd-check (manual route, K3: interactive-console check for USER_TERMINAL apply and -ApproveAuthority merges)
# after the independent Judge PASS (docs/claude/hnd-check-judge-report.md).
# User approval: the user's message "apply the recommendation" (2026-10-25 03:57Z, project room), the merge itself
# is the user's one line in their own Windows PowerShell. Prepared by Claude Code (project room thread), 2026-10-25.
# Checks: runs only in an interactive console and asks the user to retype the id; no dev-run lock and no auto-core /
# decide / dev / docs-commit / t2rc-check task running; not inside the Tue-Sat 06:00-09:00 KST or 23:20-23:45 KST
# windows; Judge report ends with VERDICT: PASS; since base b2cd42e main moved only by docs/claude commits and on none
# of the merged paths; no uncommitted main change on a merged path; the worktree changed exactly the 12 listed paths
# with the sha256 measured before the Judge (files unchanged since).
# Then it commits the 12 paths in the worktree, merges --no-ff into main and runs on main the targeted tests, the
# auto-core tests (only the known PLTR registry failure allowed) and the schema contracts.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'hnd-check'
function Stop-Merge([string]$why) { Write-Output ('HND_STOP ' + $why); exit 2 }

# The check this change introduces, applied to its own merge.
if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
Write-Host ('Authority merge. To approve, type the id exactly: ' + $Id) -NoNewline
Write-Host ' > ' -NoNewline
$typed = [Console]::ReadLine()
if ($typed -cne $Id) { Stop-Merge 'id not confirmed' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\hnd-check'
$base = (git -C $repo rev-parse b2cd42e).Trim()
$branch = 'worktree-hnd-check'
$judge = Join-Path $repo 'docs\claude\hnd-check-judge-report.md'
$hashes = @{
    'docs/claude/hnd-check-report.md' = '91125f1c8e59d56219e7bd39c8dcf4615799441c81f573c416d942e40d535889';
    'manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json' = '68c241ae7fea10d819ccdf524d73357f57920ae9d0c2ff1500593a764168b1d5';
    'manage-us-stock-strategy/references/broker-snapshot-reconciliation.md' = 'f8f9c8a8218bfbcbd6e5671963baad93e83c903920aff6c4480da3392f649005';
    'manage-us-stock-strategy/scripts/portfolio_review_journal.py' = '2ea8239b646585802bd3223bfacd2139293bbc4c37a40e87a204774bd46fe629';
    'manage-us-stock-strategy/scripts/reconcile_broker_state.py' = '956f685813040739dda9210c78114215449e777da832b4e086b44ef217fe08ed';
    'manage-us-stock-strategy/tests/test_approval_human_check.py' = 'bbf8f3204a3be4cf0dd15a538243c6e814ac09f1ebc83f274a4f8aae7acb1960';
    'manage-us-stock-strategy/tests/test_decision_journal_cards.py' = '378dcc225c0208f2a5556d6fb698ad6e93f5d716b37bc5e1e7434a49695a4d7b';
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = '5bbc7c97bcd8c824ce28cf1839d3f905942b16a2c80bea8673dc7cd93722e7a2';
    'manage-us-stock-strategy/tests/test_portfolio_review_journal.py' = '181a46690afccdbd70c1907b9594af0a7da520ae2ae877bc41e8f81881531849';
    'manage-us-stock-strategy/tests/test_reconcile_broker_state.py' = '32bc07abe77a33809661194ebca11a1ae272c5c8c1bcc9f5e7bc1f9c0d8c4521';
    'tools/dev-merge.ps1' = '81839bf904ae5def09939c506a333ca817c8d9c16e2e87a40794aff70b9614bf';
    'tools/dev_pipeline/README.md' = '1e8be02e16a22a920d3f8c3d885631082cf91c76b2f2c23b1eb01864cd0f4ca2'
}
$paths = @($hashes.Keys | Sort-Object)

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
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'hnd-check-commit-message.txt'
$msg = "feat(approval): require an interactive console for USER_TERMINAL apply and -ApproveAuthority merges (hnd-check)`n`n" +
       "hnd-check (K3, manual route; user message 'apply the recommendation' 2026-10-25 03:57Z, merge by the user's own`n" +
       "PowerShell line). dev-merge.ps1 -ApproveAuthority, reconcile_broker_state.py apply and portfolio_review_journal.py`n" +
       "apply with --confirmed-via USER_TERMINAL now refuse when stdin/stdout is not a console and ask the user to retype`n" +
       "the id or confirmation code. Only adds refusals: the Cowork, AUTO_CORE and plain-merge paths and the apply library`n" +
       "are unchanged. Limit: a pseudo console or GUI automation is not blocked (procedure rules stay). Builder`n" +
       "docs/claude/hnd-check-report.md, Judge docs/claude/hnd-check-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_017mp4f86N9tNMoTeZM9Rzqj`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge hnd-check (interactive-console check for USER_TERMINAL apply and authority merge, K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$failed = $false
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $repo
foreach ($pattern in @('test_approval_human_check*.py', 'test_reconcile_broker_state*.py', 'test_portfolio_review_journal*.py',
                       'test_decision_journal_cards*.py', 'test_dev_pipeline*.py', 'test_auto_core*.py')) {
    Write-Output ('TESTS ' + $pattern)
    $out = @(python -m unittest discover -s manage-us-stock-strategy/tests -p $pattern 2>&1 | ForEach-Object { "$_" })
    $out | Select-Object -Last 3 | ForEach-Object { Write-Output ('  ' + $_) }
    $bad = @($out | Where-Object { $_ -match '^(FAIL|ERROR):' } |
             Where-Object { -not ($_ -match 'test_real_registry_is_schema_valid_and_every_hash_matches' -and $_ -match "symbol='PLTR'") })
    if ($bad.Count -ne 0) { $bad | ForEach-Object { Write-Output ('  NEW ' + $_) }; $failed = $true }
    if (-not ($out -match '^Ran \d+ tests')) { Write-Output '  TESTS_DID_NOT_RUN'; $failed = $true }
}
python manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Select-Object -Last 2 | ForEach-Object { Write-Output ('  SCHEMA ' + $_) }
if ($LASTEXITCODE -ne 0) { $failed = $true }
Pop-Location
if ($failed) { Write-Output 'HND_POSTCHECK_FAILED (merge kept; review needed)'; exit 2 }
Write-Output 'HND_DONE'
