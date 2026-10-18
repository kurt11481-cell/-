# Merge ev-rg1-hyper (manual route, K3: R-REC1 RG1 official thesis damage blocks buys until the card is accepted
# again + hyperscaler damage-only domains + independent calculator RG1 and its runner pin) after the independent
# re-judge PASS. Cowork, 2026-10-18. ASCII only.
# Checks: no dev-run lock and no auto-core / decide / dev / docs-commit / t2rc-check task running; not inside the
# Tue-Sat 06:00-09:00 KST or the 23:20-23:45 KST window; re-judge report ends with VERDICT: PASS; main moved only by
# docs/claude commits since base 073582d and not at all on the calculator and its runner; no uncommitted main change on
# a merged path; the worktree changed exactly the 13 listed paths with the sha256 the re-judge measured. Then it
# commits the 13 paths in the worktree, merges --no-ff into the main branch and checks on main: runner pin = calculator
# sha256 over LF bytes, calculator selftest PASS, auto-core tests, schema contracts, registry damage domains.
# No order, no Kiwoom, no policy, state, ledger or journal write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\ev-rg1-hyper'
$base = '073582db663633c6c5b860ad5ddcec18b2990f40'
$branch = 'worktree-ev-rg1-hyper'
$judge = Join-Path $repo 'docs\claude\ev-rg1-hyper-judge2-report.md'
$oracleLf = '9f0e2238f2a8238016be5406cd2e195aaf24c232adeda5f1fba3a52cd09b1aae'
$hashes = @{
    'manage-us-stock-strategy/scripts/auto_core_rules.py' = '48433ab8d4c5eae45f9c6e54740e282cf5004807f5ce75842f64ea8cc4fbab4e';
    'manage-us-stock-strategy/scripts/auto_core_inputs.py' = '6e0f2cf1d6302c87612a41fb06b0ddd347eb279aef0f45d5bccd26b013b49201';
    'manage-us-stock-strategy/scripts/auto_core_decide.py' = '1013da08704fb74d7afb30455403d6d3e31f67d75392e93d1242f3c5cb7448f1';
    'manage-us-stock-strategy/scripts/auto_core_tickets.py' = '2393fa7b19352fd435846aa67d68604b74ca1d73fb9a0e51b845931433afb8c1';
    'manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json' = '5b69e590f16542306ba2af88e72d9e3db434e29e50b3b7cfc3834def713c791e';
    'docs/claude/card-evidence-registry.json' = '1654aa0d7a525e167452d62800cb9f80237d29649b95e52f0343498cc83abdb8';
    'manage-us-stock-strategy/references/auto-core-decision.md' = 'c47bbc876a12a9263b1d24f6d058131c01ba019a6a0aad7d6ba4c50ad09886a8';
    'manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py' = 'd4c8e9a202f145130b404b490caec9d3f41ce4e38285f400eaef32a05a0b4464';
    'manage-us-stock-strategy/tests/test_auto_core_decide.py' = '0b6866a2f564b5faa342d662df478644dc72ffb85b77f2b8c36412533c98519c';
    'docs/claude/t2rc-oracle.py' = 'e41a79033a73a4662361a2daeaa79a6c40421069d5e7a889dc353f4e8ba7bb67';
    'docs/claude/t2rc-check-run.ps1' = '3735492e3f6a803ee7be4a7ed2251ea2df0499e83270cd7bdaa77ca6c6cff167';
    'manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py' = 'a2a5982fc52d887b6d4f214c15ca58bc7b4873d2f9790201caf14e332a4dc4b1';
    'docs/claude/ev-rg1-hyper-report.md' = '00ed0a1cee732f2fc100a7303b559e363c6e00537b6d395f1211b6ec50829b24'
}
$paths = @($hashes.Keys | Sort-Object)
function Stop-Merge([string]$why) { Write-Output ('EVRG1_STOP ' + $why); exit 2 }

$kst = [DateTime]::UtcNow.AddHours(9)
$tueSat = @('Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday') -contains $kst.DayOfWeek.ToString()
$minute = $kst.Hour * 60 + $kst.Minute
if ($tueSat -and $minute -ge 360 -and $minute -lt 540) { Stop-Merge 'inside Tue-Sat 06:00-09:00 KST (auto-core, decide, t2rc-check)' }
if ($minute -ge 1400 -and $minute -lt 1425) { Stop-Merge 'inside 23:20-23:45 KST (docs-commit)' }
if (Test-Path -LiteralPath (Join-Path $repo 'workspace\outputs\dev-runs\_lock')) { Stop-Merge 'dev-run lock held' }
foreach ($t in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide', 'InvestmentV2-DevQueue', 'InvestmentV2-DocsCommit',
                 'InvestmentV2-T2rcCheck')) {
    $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') { Stop-Merge ($t + ' running') }
}
if (-not (Test-Path -LiteralPath $judge)) { Stop-Merge 're-judge report missing' }
$last = (Get-Content -LiteralPath $judge -Encoding UTF8 | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1).Trim()
if ($last -ne 'VERDICT: PASS') { Stop-Merge ('re-judge verdict: ' + $last) }

$mainBranch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
if ($mainBranch -ne 'codex/master-recovery-expansion') { Stop-Merge ('main branch ' + $mainBranch) }
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$moved = @(git -C $repo diff --name-only $base HEAD)
$nonDocs = @($moved | Where-Object { -not $_.StartsWith('docs/claude/') })
if ($nonDocs.Count -ne 0) { Stop-Merge ('main moved with non-docs commits: ' + ($nonDocs -join ',')) }
$pinned = @($moved | Where-Object { $_ -in @('docs/claude/t2rc-oracle.py', 'docs/claude/t2rc-check-run.ps1') })
if ($pinned.Count -ne 0) { Stop-Merge ('calculator or runner changed on main since base: ' + ($pinned -join ',')) }
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

$msgFile = Join-Path $repo 'workspace\outputs\ev-rg1-hyper-commit-message.txt'
$msg = "fix(r-rec1 rg1): official thesis damage blocks buys until the card is accepted again (ev-rg1-hyper)`n`n" +
       "ev-rg1-hyper (K3, manual route; user decisions ev-rg1-hyper a 2026-10-14, rrec-k3-timing d 2026-10-16,`n" +
       "D1 c 2026-10-17): a root-thesis damage fact in the 60-session R-REC1 window keeps RG1 at no until the candidate's`n" +
       "registry card is accepted again on or after the fact's release day (max of event session and KST announcement`n" +
       "day; no retroactive release), whatever the event day, re-basing, time decay or closure. Time decay does not close`n" +
       "an event while RG1 is no; a closed or absent event with uncleared damage gives status no and buy requirement 5`n" +
       "blocks. Registry thesis_damage_domains (microsoft.com, abc.xyz, atmeta.com, aboutamazon.com) are accepted only for`n" +
       "root_thesis_damage facts and only feed RG1 (never evidence, C7 or EV3b). One alert when the uncleared set changes.`n" +
       "The independent calculator t2rc-oracle.py follows the same rule (loader checks aligned), drops the lines_open term`n" +
       "of G2 (D1 c), and the runner pin moves to its new LF sha256 9f0e2238. No damage facts: decisions, tickets and`n" +
       "hashes unchanged. Builder docs/claude/ev-rg1-hyper-report.md, Judge docs/claude/ev-rg1-hyper-judge-report.md (FAIL,`n" +
       "fixed) and ev-rg1-hyper-judge2-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_019RFs7279KmenihAG7cLG4n`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge ev-rg1-hyper (R-REC1 RG1 thesis damage until card re-acceptance + oracle RG1, K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$failed = $false
$oracleText = [System.IO.File]::ReadAllText((Join-Path $repo 'docs\claude\t2rc-oracle.py'), [System.Text.Encoding]::UTF8)
$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($oracleText.Replace("`r`n", "`n"))
$lf = (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '')
$pinLine = (Get-Content -LiteralPath (Join-Path $repo 'docs\claude\t2rc-check-run.ps1') -Encoding UTF8 | Select-Object -Index 15)
Write-Output ('ORACLE_LF ' + $lf + ' PIN ' + $pinLine.Trim())
if ($lf -ne $oracleLf -or -not $pinLine.Contains($oracleLf)) { Write-Output 'PIN_MISMATCH'; $failed = $true }

$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $repo
$self = (python docs\claude\t2rc-oracle.py selftest --repo $repo 2>&1 | Out-String)
if ($self -notmatch '"selftest": "PASS"') { Write-Output 'ORACLE_SELFTEST_FAILED'; $failed = $true } else { Write-Output 'ORACLE_SELFTEST PASS' }
Write-Output 'TESTS test_auto_core*.py'
$out = @(python -m unittest discover -s manage-us-stock-strategy/tests -p 'test_auto_core*.py' 2>&1 | ForEach-Object { "$_" })
$out | Select-Object -Last 3 | ForEach-Object { Write-Output ('  ' + $_) }
# Known before this change (Builder and both Judge reports): RegistryTests PLTR registry entry / watchlist state.
$bad = @($out | Where-Object { $_ -match '^(FAIL|ERROR):' } |
         Where-Object { -not ($_ -match 'test_real_registry_is_schema_valid_and_every_hash_matches' -and $_ -match "symbol='PLTR'") })
if ($bad.Count -ne 0) { $bad | ForEach-Object { Write-Output ('  NEW ' + $_) }; $failed = $true }
if (-not ($out -match '^Ran \d+ tests')) { Write-Output '  TESTS_DID_NOT_RUN'; $failed = $true }
python manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Select-Object -Last 2 | ForEach-Object { Write-Output ('  SCHEMA ' + $_) }
if ($LASTEXITCODE -ne 0) { $failed = $true }
$reg = (python -c "import sys; sys.path.insert(0, 'manage-us-stock-strategy/scripts'); import auto_core_inputs as I; r = I.load_registry(); print(r['status'], r['committed'], ','.join(r.get('damage_domains') or []))" 2>&1 | Out-String).Trim()
Write-Output ('REGISTRY ' + $reg)
if ($reg -notmatch '^OK True microsoft\.com,abc\.xyz,atmeta\.com,aboutamazon\.com') { $failed = $true }
Pop-Location
if ($failed) { Write-Output 'EVRG1_POSTCHECK_FAILED (merge kept; Cowork review)'; exit 2 }
Write-Output 'EVRG1_DONE'
