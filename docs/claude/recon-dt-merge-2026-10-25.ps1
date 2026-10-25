# Merge recon-dt commit 1 (manual route, K3: Kiwoom ust21150 ord_dt read as the U.S. ET order day when the
# auto-core reconciliation builds fill times) after the independent Judge PASS (docs/claude/recon-dt-judge-report.md).
# User approval: the merge approval line for recon-dt in the Cowork secretary chat (2026-10-25 08:06 KST). Cowork, 2026-10-25.
# Checks: no dev-run lock and no auto-core / decide / dev / docs-commit / t2rc-check task running; not inside the
# Tue-Sat 06:00-09:00 KST or 23:20-23:45 KST windows; Judge report ends with VERDICT: PASS; since base e33756c main
# moved only by docs/claude commits and on none of the merged paths; no uncommitted main change on a merged path; the
# worktree changed exactly the 5 listed paths with the sha256 measured before the Judge (files unchanged since).
# Then it commits the 5 paths in the worktree, merges --no-ff into main and runs on main: auto-core tests (only the
# known PLTR registry failure allowed) and schema contracts. No order, no Kiwoom, no policy, state, ledger or journal write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\recon-dt'
$base = 'e33756c617eaa2a29d57d517d185707e08628887'
$branch = 'worktree-recon-dt'
$judge = Join-Path $repo 'docs\claude\recon-dt-judge-report.md'
$hashes = @{
    'docs/claude/recon-dt-report.md' = 'e9ecb736a17b93316018b19661eefd69bce176084691dd77e07816533720babf';
    'manage-us-stock-strategy/references/broker-snapshot-reconciliation.md' = 'b6ff34c4e16045bd74241a739c4d8ac0f9253800c074989526847bfb817a5a02';
    'manage-us-stock-strategy/scripts/auto_core_reconcile.py' = '2613ddeb4288ae4b6bef036da6a8655e59a19719990f36107bc767c71ed0349a';
    'manage-us-stock-strategy/tests/test_auto_core.py' = 'b4f15e7d022f3e6384a873916153d245883f5f9c944ba4c1eaca30c832255001';
    'manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py' = '1f898a6b0e788f01e1ca2d349cb9a3518020a8a2e65fdf566558c9eeff92d9c7'
}
$paths = @($hashes.Keys | Sort-Object)
function Stop-Merge([string]$why) { Write-Output ('RDT_STOP ' + $why); exit 2 }

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

$msgFile = Join-Path $env:TEMP 'recon-dt-commit-message.txt'
$msg = "fix(auto-core): read ust21150 ord_dt as the U.S. ET order day in reconciliation (recon-dt)`n`n" +
       "recon-dt commit 1 (K3, manual route; user decision 'recon-dt: a' 2026-10-23 08:45 KST, merge approved`n" +
       "2026-10-25 08:06 KST). parse_fills puts a fill clock on the KST day D or D+1 that lies within D 04:00-20:00 ET`n" +
       "(zoneinfo DST) and the order clock after D-1 20:00 ET and not after the fill; outside the window, order after fill,`n" +
       "fill after the snapshot or session mismatch are errors (HOLD). session_date = D. I1-I5 formulas, cash tolerance,`n" +
       "fill window, settlement rules and cash_flow_evidence unchanged. Reference doc rule updated; one test fixture key`n" +
       "moved to the U.S. order day. Diagnosis docs/claude/recon-hold-2026-10-23.md, Builder docs/claude/recon-dt-report.md,`n" +
       "Judge docs/claude/recon-dt-judge-report.md (PASS). Ticket order-day window is follow-up recon-dt2.`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01JxSSyGocxdm4g6uX39cszu`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge recon-dt (ord_dt as U.S. order day in reconciliation, K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$failed = $false
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $repo
Write-Output 'TESTS test_auto_core*.py'
$out = @(python -m unittest discover -s manage-us-stock-strategy/tests -p 'test_auto_core*.py' 2>&1 | ForEach-Object { "$_" })
$out | Select-Object -Last 3 | ForEach-Object { Write-Output ('  ' + $_) }
$bad = @($out | Where-Object { $_ -match '^(FAIL|ERROR):' } |
         Where-Object { -not ($_ -match 'test_real_registry_is_schema_valid_and_every_hash_matches' -and $_ -match "symbol='PLTR'") })
if ($bad.Count -ne 0) { $bad | ForEach-Object { Write-Output ('  NEW ' + $_) }; $failed = $true }
if (-not ($out -match '^Ran \d+ tests')) { Write-Output '  TESTS_DID_NOT_RUN'; $failed = $true }
python manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Select-Object -Last 2 | ForEach-Object { Write-Output ('  SCHEMA ' + $_) }
if ($LASTEXITCODE -ne 0) { $failed = $true }
Pop-Location
if ($failed) { Write-Output 'RDT_POSTCHECK_FAILED (merge kept; Cowork review)'; exit 2 }
Write-Output 'RDT_DONE'
