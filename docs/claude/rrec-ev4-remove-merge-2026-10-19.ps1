# Merge rrec-ev4-remove (manual route, K3: R-REC1 event EV4 - the account line - removed from the auto-core, the
# replay and the independent calculator, plus the calculator runner pin) after the independent Judge PASS.
# Cowork, 2026-10-19. ASCII only.
# Checks: no dev-run lock and no auto-core / decide / dev / docs-commit / t2rc-check task running; not inside the
# Tue-Sat 06:00-09:00 KST or the 23:20-23:45 KST window; Judge report ends with VERDICT: PASS; main moved only by
# docs/claude commits since base 80d3a1d and not at all on the calculator and its runner; no uncommitted main change on
# a merged path; the worktree changed exactly the 20 listed paths with the sha256 the Judge measured. Then it commits
# the 20 paths in the worktree, merges --no-ff into the main branch and checks on main: runner pin = calculator sha256
# over LF bytes, calculator selftest PASS, auto-core tests (only the known PLTR registry failure allowed), schema
# contracts, rules has no ev4_open, calculator check of 2026-10-17 (historical, --ignore-input-sha) INFO_MATCH.
# No order, no Kiwoom, no policy, state, ledger or journal write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\rrec-ev4-remove'
$base = '80d3a1da0957a872fc16b97ac204ee4d761198ca'
$branch = 'worktree-rrec-ev4-remove'
$judge = Join-Path $repo 'docs\claude\rrec-ev4-remove-judge-report.md'
$oracleLf = '6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64'
$hashes = @{
    'docs/claude/t2rc-check-run.ps1' = 'beaf8446802621e1a9cd29c2a6c025eef62a5c9bc6c8ceb3c247e8d2906a15a7';
    'docs/claude/t2rc-oracle.py' = 'd79b12212ee2c043e8c1ad8be739e84498506126b8ed42c60cc23f2a5ff42631';
    'manage-us-stock-strategy/references/auto-core-decision.md' = '61b0af682c1c43e6b750cf6312d8e6ff6a6a1d3f436dbf3d9afa53834c5c6010';
    'manage-us-stock-strategy/schemas/auto-core-decision.schema.json' = '3b540d749011d8ff953d8a81f621ecbbbedc66935252755da960c3782ee94514';
    'manage-us-stock-strategy/scripts/auto_core_decide.py' = '97b78ac5edfc1850267a8b1c70a3919c9dc2a0f93d8ed8534c54bd935e0d57ec';
    'manage-us-stock-strategy/scripts/auto_core_replay.py' = 'd346ba92f7839860b63295ff1e12ae26d7fefeb8e431a03959e4482d5b06dbd0';
    'manage-us-stock-strategy/scripts/auto_core_rules.py' = '187a46f628c621da908fe696eeb1c8a130ae01946b9533add393a9283d90ab56';
    'manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py' = 'e42fff9044295aca7e4c2d1b8518f99e2859d1c0ea10f351adfea9eb244faae9';
    'manage-us-stock-strategy/tests/test_auto_core_decide.py' = '6c6e8611f07a2e583f9da652d98c8b7e452d8c4bab5af05a297f6f21778fb644';
    'manage-us-stock-strategy/tests/test_auto_core_equity_cash.py' = '526d927485e8f02dc0040c2663f0915b8752845814695bee278369a8fc3b02b4';
    'manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py' = 'a1b5ad03926894ae94e3be0a839b928379ada3c1b6135dfb004e334b17cf082e';
    'manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py' = 'f0e93633139176dfc71ff4ea06178d64ab12f7849135835ed6523169ef1e6be0';
    'manage-us-stock-strategy/tests/test_auto_core_risk1r.py' = '2a95458c3563af25c077baa966f9ee8be918f78a9f18bfde407d6221672831f6';
    'manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py' = '7a1832d2ca1a40de851071aa897dbbcbff391f26f3552338aaa84aa8d0cdcd9e';
    'manage-us-stock-strategy/tests/test_auto_core_rrec_ev4_remove.py' = '6c8db4bc21fbaa51127d992ae82391773c5fba43fd955b6ff0f6775b06003f74';
    'manage-us-stock-strategy/tests/test_auto_core_rules.py' = '0b457f6c5b7864c7aaa9605713f7b985785dff0d2f9523aed104ef9de266f0b8';
    'manage-us-stock-strategy/tests/test_auto_core_t1_safety.py' = 'b6d00d34907df4237bab30935d074b43bd695d352e05b7a4428838e6a80f4a3d';
    'manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py' = 'a6402a15148f4f4facd9746445d4bfcd91c651fb588ab880633c1e2a800dd613';
    'manage-us-stock-strategy/tests/test_auto_core_tickets.py' = 'b687a826c725c28c78c2fb967d31fe82e885601e5a3c963664cab838d69eac42';
    'docs/claude/rrec-ev4-remove-report.md' = '93bdd50b0edcc39eff2e1949a8d93ad3fc1cc0fc67cb7215a38d33243bf9de3c'
}
$paths = @($hashes.Keys | Sort-Object)
function Stop-Merge([string]$why) { Write-Output ('RRECEV4_STOP ' + $why); exit 2 }

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
$pinned = @($moved | Where-Object { $_ -in @('docs/claude/t2rc-oracle.py', 'docs/claude/t2rc-check-run.ps1', 'docs/claude/rrec-ev4-remove-report.md') })
if ($pinned.Count -ne 0) { Stop-Merge ('calculator, runner or builder report changed on main since base: ' + ($pinned -join ',')) }
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

$msgFile = Join-Path $repo 'workspace\outputs\rrec-ev4-remove-commit-message.txt'
$msg = "fix(r-rec1): remove the account-line event EV4 from R-REC1 (rrec-ev4-remove)`n`n" +
       "rrec-ev4-remove (K3, manual route; user decision 'rrec-ev4: REMOVE' 2026-10-19 17:45 KST,`n" +
       "docs/claude/rrec-ev4-remove-decision-2026-10-19.md): R-REC1 events are EV1, EV2, EV3 (a)(b) and EV5. EV4`n" +
       "(total <= the V6 first line or <= S7 hwm x 0.9) re-opened an event every session the account stayed below the`n" +
       "line, so RG1, RG3 and the time decay could not be met until the account recovered; the account drawdown is left to`n" +
       "the S7 review lines (L2 and below pause buys until a journal review). Removed: rules.ev4_open and its constants,`n" +
       "the decide EV4 backfill (t1-safety) and the EV4_UNDETERMINED exception, account.ev4_open and ev4_backfill in new`n" +
       "decision records (schema property kept as legacy), the replay EV4 list, and EV4 in the independent calculator`n" +
       "t2rc-oracle.py (runner pin -> its new LF sha256 6a74f813). Equivalence: new rrec1(x) = base rrec1(x,`n" +
       "ev4_sessions=[]); calculator likewise. S7, exposure caps, requirements 1-4 and every other gate unchanged.`n" +
       "Builder docs/claude/rrec-ev4-remove-report.md, Judge docs/claude/rrec-ev4-remove-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_015N6rLwgVhCVafmuqAfVvgV`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge rrec-ev4-remove (R-REC1 EV4 account-line event removed + oracle, K3, Judge PASS)" $branch
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
$tmp = Join-Path $env:TEMP 'rrec-ev4-remove-check-2026-10-17.json'
python docs\claude\t2rc-oracle.py check --day 2026-10-17 --repo $repo --out $tmp --ignore-input-sha 2>&1 | Out-Null
$verdict = (python -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(d.get('verdict'), 'ev4_history' in d)" $tmp 2>&1 | Out-String).Trim()
Write-Output ('ORACLE_CHECK_1017 ' + $verdict)
if ($verdict -ne 'INFO_MATCH False') { $failed = $true }
Write-Output 'TESTS test_auto_core*.py'
$out = @(python -m unittest discover -s manage-us-stock-strategy/tests -p 'test_auto_core*.py' 2>&1 | ForEach-Object { "$_" })
$out | Select-Object -Last 3 | ForEach-Object { Write-Output ('  ' + $_) }
# Known before this change (Builder and Judge reports): RegistryTests PLTR registry entry / watchlist state.
$bad = @($out | Where-Object { $_ -match '^(FAIL|ERROR):' } |
         Where-Object { -not ($_ -match 'test_real_registry_is_schema_valid_and_every_hash_matches' -and $_ -match "symbol='PLTR'") })
if ($bad.Count -ne 0) { $bad | ForEach-Object { Write-Output ('  NEW ' + $_) }; $failed = $true }
if (-not ($out -match '^Ran \d+ tests')) { Write-Output '  TESTS_DID_NOT_RUN'; $failed = $true }
python manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Select-Object -Last 2 | ForEach-Object { Write-Output ('  SCHEMA ' + $_) }
if ($LASTEXITCODE -ne 0) { $failed = $true }
$gone = (python -c "import sys; sys.path.insert(0, 'manage-us-stock-strategy/scripts'); import auto_core_rules as R; print(hasattr(R, 'ev4_open'), 'RREC_EV4_HWM_FRACTION' in R.C)" 2>&1 | Out-String).Trim()
Write-Output ('EV4_IN_RULES ' + $gone)
if ($gone -ne 'False False') { $failed = $true }
Pop-Location
if ($failed) { Write-Output 'RRECEV4_POSTCHECK_FAILED (merge kept; Cowork review)'; exit 2 }
Write-Output 'RRECEV4_DONE'
