# Merge t2-equity-cash (manual route, K3) after the independent Judge PASS. Cowork, 2026-10-13. ASCII only.
# Checks: no dev-run lock and no auto-core task running; Judge report ends with VERDICT: PASS; main moved only by
# docs/claude commits since base 1fe378b; the worktree changed exactly the 4 listed paths; the 3 code/test files
# still have the sha256 the Builder reported (nothing changed after the Judge read them). Then it commits the 4 paths
# in the worktree, merges --no-ff into the main branch and runs the auto-core tests on main.
# No order, no Kiwoom, no policy or state write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\t2-equity-cash'
$base = '1fe378b5a14501a5ccfe2456dc2591b9142fd95d'
$branch = 'worktree-t2-equity-cash'
$judge = Join-Path $repo 'docs\claude\t2-equity-cash-judge-report-2026-10-13.md'
$paths = @('docs/claude/t2-equity-cash-report.md', 'manage-us-stock-strategy/scripts/auto_core_decide.py',
           'manage-us-stock-strategy/scripts/auto_core_tickets.py', 'manage-us-stock-strategy/tests/test_auto_core_equity_cash.py')
$hashes = @{
    'manage-us-stock-strategy/scripts/auto_core_decide.py' = '88621ca9c0201ef732e7e10ee084492ecccbb527fb29498ec0dfbe067d611bca';
    'manage-us-stock-strategy/scripts/auto_core_tickets.py' = 'b6e8f73a7fa05960c0bd0d300b1ef6ca48f46a06c4a34cb9e71ab5bc2460e973';
    'manage-us-stock-strategy/tests/test_auto_core_equity_cash.py' = 'a564f1d6be76ce141fadf26e842b8d0edfcdfbe2695cd46e81fd1d19409dafd0'
}
function Stop-Merge([string]$why) { Write-Output ('EQCASH_STOP ' + $why); exit 2 }

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

$msgFile = Join-Path $repo 'workspace\outputs\t2-equity-cash-commit-message.txt'
$msg = "fix(auto-core decide): total equity cash = order-available behind T1's cash check, else the smallest known value`n`n" +
       "t2-equity-cash (K3, manual route): rule-file N, V6 account line and R-REC1 EV4 now use the approved cash`n" +
       "definition; buy cash, G1, S7, gates and tickets unchanged. Builder report docs/claude/t2-equity-cash-report.md,`n" +
       "Judge docs/claude/t2-equity-cash-judge-report-2026-10-13.md. User decisions 2026-10-13 09:21 and 13:00 KST.`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01JtukjYCrCwTYR2XExRBiUk`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge t2-equity-cash (total equity cash, K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $repo
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { Write-Output ('  ' + $_) }
$testCode = $LASTEXITCODE
Pop-Location
if ($testCode -ne 0) { Write-Output 'EQCASH_TESTS_FAILED_ON_MAIN (merge kept; Cowork review)'; exit 2 }
Write-Output 'EQCASH_DONE'
