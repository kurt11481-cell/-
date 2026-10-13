# Merge rrec-rg1 (manual route, K3: R-REC1 RG1 bootstrap B) after the independent Judge PASS. Cowork, 2026-10-13. ASCII only.
# Checks: no dev-run lock and no auto-core task running; Judge report ends with VERDICT: PASS; main moved only by
# docs/claude commits since base da5d85e; the worktree changed exactly the 4 listed paths; the 3 code/test files
# still have the sha256 Cowork checked (nothing changed after the review). Then it commits the 4 paths in the
# worktree, merges --no-ff into the main branch and runs the auto-core tests on main.
# No order, no Kiwoom, no policy or state write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\rrec-rg1'
$base = 'da5d85e6417dbfc0af630ccf4b51ab9f4a07c4a8'
$branch = 'worktree-rrec-rg1'
$judge = Join-Path $repo 'docs\claude\rrec-rg1-judge-report.md'
$paths = @('docs/claude/rrec-rg1-report.md', 'manage-us-stock-strategy/scripts/auto_core_rules.py',
           'manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py',
           'manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py')
$hashes = @{
    'manage-us-stock-strategy/scripts/auto_core_rules.py' = '8ce52c9566cd775e8a3bd039d3b125abcb79aaedec9411c7cf51513b177fc10d';
    'manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py' = '9eab605dea99a2f30b6a437c114fc75d4bf32e50d2d6c02b0c3084a2a4387452';
    'manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py' = '0e52f6f5016de7987e6ba9d480f6cd21ee5d23ce183134e5b400f4bb08c07507'
}
function Stop-Merge([string]$why) { Write-Output ('RRECRG1_STOP ' + $why); exit 2 }

if (Test-Path -LiteralPath (Join-Path $repo 'workspace\outputs\dev-runs\_lock')) { Stop-Merge 'dev-run lock held' }
foreach ($t in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide')) {
    if ((Get-ScheduledTask -TaskName $t).State -eq 'Running') { Stop-Merge ($t + ' running') }
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
if (($status -join '|') -ne (($paths | Sort-Object) -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $repo 'workspace\outputs\rrec-rg1-commit-message.txt'
$msg = "fix(auto-core rules): R-REC1 RG1 needs research records only from the first record in the window on`n`n" +
       "rrec-rg1-bootstrap B (K3, manual route): sessions after the event but before the first valid research record`n" +
       "(ev3b_coverage_start) are left out of the RG1 record requirement and listed in rg1_coverage.before_first_record;`n" +
       "no record in the window keeps RG1 unknown. EV3 (b) gaps, events, DS1, RG2-RG4, closing rule and constants unchanged.`n" +
       "One cmp-fix3 test input moved its first record before the event to keep testing a real gap. Builder report`n" +
       "docs/claude/rrec-rg1-report.md, Judge docs/claude/rrec-rg1-judge-report.md. User decision 2026-10-13 18:43 KST.`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_014qfok7Y7iswfusa5exqred`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge rrec-rg1 (R-REC1 RG1 bootstrap B, K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $repo
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { Write-Output ('  ' + $_) }
$testCode = $LASTEXITCODE
Pop-Location
if ($testCode -ne 0) { Write-Output 'RRECRG1_TESTS_FAILED_ON_MAIN (merge kept; Cowork review)'; exit 2 }
Write-Output 'RRECRG1_DONE'
