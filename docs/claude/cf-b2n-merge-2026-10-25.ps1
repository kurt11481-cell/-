# Merge cf-b2n (manual route, K3: B2-N - an outflow missing from the transaction history passes I3 only when the
# snapshot residual equals the ust21132 ledger residual; HWM not adjusted) after the independent Judge PASS in two
# rounds (docs/claude/cf-b2n-judge-report.md).
# User approval: the merge approval line for cashflow-proof in the Cowork secretary chat (2026-10-25). Cowork, 2026-10-25.
# Checks: no dev-run lock and no auto-core / decide / dev / docs-commit / t2rc-check task running; not inside the
# Tue-Sat 06:00-09:00 KST or 23:20-23:45 KST windows; Judge report ends with VERDICT: PASS; since base 5a289b8 main
# moved only by docs/claude commits and on none of the merged paths; no uncommitted main change on a merged path; the
# worktree changed exactly the 8 listed paths with the sha256 measured before the Judge (files unchanged since).
# Then it commits the 8 paths in the worktree, merges --no-ff into main and runs on main: auto-core tests (only the
# known PLTR registry failure allowed) and schema contracts. No order, no Kiwoom, no policy, state, ledger or journal write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\cf-b2n'
$base = (git -C $repo rev-parse 5a289b8).Trim()
$branch = 'worktree-cf-b2n'
$judge = Join-Path $repo 'docs\claude\cf-b2n-judge-report.md'
$hashes = @{
    'docs/claude/automation-redesign-2026-10-10.md' = 'a07c36f10552c7777619128f3fcfddceaf2bc5a2e1f5dce98b71ea9f59bdfb59';
    'docs/claude/cf-b2n-report.md' = '41ed5c21c520c7a01058ba4b67296fb0985de07d5c91d75906c9bf45eb7e5ebc';
    'manage-us-stock-strategy/references/broker-snapshot-reconciliation.md' = '478a6eb1062238ea457df2b35553c963bb3790ec9d4c87846ff75030cabecc04';
    'manage-us-stock-strategy/scripts/auto_core_reconcile.py' = '53b57268a5a7ff911c44f1e45523e0dea10eac62402db766c95c92b88a29c11c';
    'manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py' = 'a22c84b0a0eebfbc400ef0392638cb67caa65967480a7e7d482ad93feacf76af';
    'manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py' = '0cf2fa758d40da03257926bddcc22caaf132e6d8af63e78764c7dfc3780b3614';
    'manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py' = '146e1510a52b79c51b89c6c6220dd3ec3d846d593ec0ac5d506ad55aeb4579c8';
    'manage-us-stock-strategy/tests/test_reconcile_broker_state.py' = '7731602ebecaf5b5385b78b2c0d6c48e4536e2611a7fa0d51f578298cdddcb95'
}
$paths = @($hashes.Keys | Sort-Object)
function Stop-Merge([string]$why) { Write-Output ('CFB_STOP ' + $why); exit 2 }

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

$msgFile = Join-Path $env:TEMP 'cf-b2n-commit-message.txt'
$msg = "feat(auto-core): B2-N - admit an unverified external outflow in reconciliation I3 (cf-b2n)`n`n" +
       "cf-b2n (K3, manual route; user decisions 'cashflow-proof: B2-N' 2026-10-23 09:25 KST and 'cashflow-proof`n" +
       "start' 2026-10-25 08:12 KST, merge approved 2026-10-25). When the only I3 reason is CASH_CHANGE_NOT_EXPLAINED for`n" +
       "an outflow, I3 passes only if the ust21132 deposit by U.S. trading day shows the same residual within 0.05 USD,`n" +
       "every fill is inside the ledger span, the amount is within the baseline order-available cash and the KRW deposit`n" +
       "did not rise; otherwise HOLD. Inflows are never admitted. The cash-flow declaration is untouched (HWM not`n" +
       "adjusted - the outflow stays a loss). ust21132 added to the read-only account bridge (top-level won_entr copied`n" +
       "onto rows), never an I1 read. Invariant 3 wording in redesign 3-5 and the reference doc updated; two pinned route`n" +
       "tests list the new read. Builder docs/claude/cf-b2n-report.md, Judge docs/claude/cf-b2n-judge-report.md (PASS x2).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01JxSSyGocxdm4g6uX39cszu`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge cf-b2n (B2-N unverified outflow in I3, K3, Judge PASS)" $branch
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
if ($failed) { Write-Output 'CFB_POSTCHECK_FAILED (merge kept; Cowork review)'; exit 2 }
Write-Output 'CFB_DONE'
