# Merge close-confirm-e (manual route, K3: every decide ticket carries priceCalc band and hold; a buy's lo-hi is
# its hold range, an unverified buy gets no ticket - HOLD_RANGE_UNVERIFIED; a sell keeps lo-hi = band) after the
# independent Judge PASS (docs/claude/close-confirm-e-judge-report.md). User approval: the merge approval line
# for close-confirm-e in the Cowork chat (2026-10-21 19:13 KST). Cowork, 2026-10-21. ASCII only.
# Checks: no dev-run lock and no auto-core / decide / dev / docs-commit / t2rc-check task running; not inside the
# Tue-Sat 06:00-09:00 KST or the 23:20-23:45 KST window; Judge report ends with VERDICT: PASS; since base 3e753f3 main
# moved only by docs/claude commits plus the six known hide-task-window paths (commit 4797161, Judge report) and on none
# of the merged paths; no uncommitted main change on a merged path; the worktree changed exactly the 8 listed paths with
# the sha256 the Judge measured. Then it commits the 8 paths in the worktree, merges --no-ff into the main branch and
# checks on main: calculator LF sha256 = runner pin (unchanged), auto-core tests (only the known PLTR registry failure
# allowed), schema contracts, hold_range present and the replay without hold_range.
# No order, no Kiwoom, no policy, state, ledger or journal write.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\work-close-confirm-e'
$base = '3e753f3b6cee0e0ed1a1720809ef7c759c779f39'
$branch = 'worktree-work-close-confirm-e'
$judge = Join-Path $repo 'docs\claude\close-confirm-e-judge-report.md'
$oracleLf = '6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64'
$hashes = @{
    'docs/claude/close-confirm-e-report.md' = '427a58ed787df0fbe6fe81321c7398ceb61e49733ec817aeac9b53aba014393d';
    'manage-us-stock-strategy/references/auto-core-decision.md' = '00ea53c0504746301faf72b15f168ce4f96c7eba1f222fb3811ab58d12e77643';
    'manage-us-stock-strategy/schemas/auto-core-ticket.schema.json' = '68a11bf7da1939b01c047b1ffcffc0183da8ae2a2283b1374e4f290c33fdce60';
    'manage-us-stock-strategy/scripts/auto_core_decide.py' = '0d09ba0e690d8063110343258fe091c59285005c5d33afdb57fe47cd83aee089';
    'manage-us-stock-strategy/scripts/auto_core_tickets.py' = '8fe20bf3a0e606f5cc318486b02b6cd57b9c11e6ece6aec22b7c35bfe41a5b54';
    'manage-us-stock-strategy/tests/test_auto_core_enter_window.py' = '7f4eac19dc0846f73ddf163de73821935cf10b9764e88b41d450bf72c42123f4';
    'manage-us-stock-strategy/tests/test_auto_core_hold_range.py' = '2b81f4464ab995c2c7a08726b13091c7913244321b56981e3457052a603c5aff';
    'manage-us-stock-strategy/tests/test_auto_core_risk1r.py' = 'b7ca38b726cc7d3286ec17f742c8790a7fd656cc1bdff2fb5fc35bf1afcf5b3b'
}
# Non-docs paths main gained after base, known at Judge time (4797161 hide-task-window, its own manual route).
$knownMoved = @('manage-us-stock-strategy/scripts/register_auto_core_task.ps1',
                'manage-us-stock-strategy/scripts/register_host_status_task.ps1',
                'manage-us-stock-strategy/scripts/register_journal_score_task.ps1',
                'manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1',
                'manage-us-stock-strategy/scripts/register_sec_scheduled_shadow_task.ps1',
                'manage-us-stock-strategy/tests/test_task_window_hidden.py')
$paths = @($hashes.Keys | Sort-Object)
function Stop-Merge([string]$why) { Write-Output ('CCE_STOP ' + $why); exit 2 }

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
git -C $repo merge-base --is-ancestor $base HEAD
if ($LASTEXITCODE -ne 0) { Stop-Merge 'base is not an ancestor of main' }
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$moved = @(git -C $repo diff --name-only $base HEAD)
$unknown = @($moved | Where-Object { -not $_.StartsWith('docs/claude/') -and ($knownMoved -notcontains $_) })
if ($unknown.Count -ne 0) { Stop-Merge ('main moved with unreviewed non-docs paths: ' + ($unknown -join ',')) }
$overlap = @($moved | Where-Object { $paths -contains $_ -or $_ -eq 'docs/claude/t2rc-oracle.py' -or $_ -eq 'docs/claude/t2rc-check-run.ps1' })
if ($overlap.Count -ne 0) { Stop-Merge ('a merged path, the calculator or its runner changed on main since base: ' + ($overlap -join ',')) }
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

$msgFile = Join-Path $env:TEMP 'close-confirm-e-commit-message.txt'
$msg = "feat(auto-core): hold range per ticket - priceCalc band and hold (close-confirm-e)`n`n" +
       "close-confirm-e (K3, manual route; user decision 'close-confirm: e before ON' 2026-10-20 19:43 KST,`n" +
       "docs/claude/close-confirm-monday-gap-2026-10-20.md 2 e; merge approved 2026-10-21 19:13 KST). decide passes`n" +
       "hold_range=True: every ticket gets priceCalc.band (the +/-1% lo-hi of loc_price) and priceCalc.hold, the cent`n" +
       "range in which the same judgment comes out when only that symbol's evaluation-session close is each cent of the`n" +
       "band (S7, the other symbols, cash fixed; the same code called again). A buy's lo-hi becomes the hold range; a buy`n" +
       "whose range is unverified gets no ticket (blocked HOLD_RANGE_UNVERIFIED, candidates kept); a sell keeps lo-hi =`n" +
       "band. Outcome classification keeps the band. The replay (hold_range False) is unchanged (E1). Price formula,`n" +
       "quantities, gates G0-G5, evidence, candidates, ledger, journal, policy and state unchanged.`n" +
       "Builder docs/claude/close-confirm-e-report.md, Judge docs/claude/close-confirm-e-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01STi72NGVtqo1GAyNevGGkD`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge close-confirm-e (ticket hold range, priceCalc band/hold, K3, Judge PASS)" $branch
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
Write-Output 'TESTS test_auto_core*.py (about 2-3 minutes)'
$out = @(python -m unittest discover -s manage-us-stock-strategy/tests -p 'test_auto_core*.py' 2>&1 | ForEach-Object { "$_" })
$out | Select-Object -Last 3 | ForEach-Object { Write-Output ('  ' + $_) }
# Known before this change (Builder and Judge reports): RegistryTests PLTR registry entry / watchlist state.
$bad = @($out | Where-Object { $_ -match '^(FAIL|ERROR):' } |
         Where-Object { -not ($_ -match 'test_real_registry_is_schema_valid_and_every_hash_matches' -and $_ -match "symbol='PLTR'") })
if ($bad.Count -ne 0) { $bad | ForEach-Object { Write-Output ('  NEW ' + $_) }; $failed = $true }
if (-not ($out -match '^Ran \d+ tests')) { Write-Output '  TESTS_DID_NOT_RUN'; $failed = $true }
python manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Select-Object -Last 2 | ForEach-Object { Write-Output ('  SCHEMA ' + $_) }
if ($LASTEXITCODE -ne 0) { $failed = $true }
$probe = (python -c "import sys, inspect; sys.path.insert(0, 'manage-us-stock-strategy/scripts'); import auto_core_tickets as T, auto_core_decide as D, auto_core_replay as R; print(hasattr(T, 'hold_range'), inspect.signature(D.evaluate_session).parameters['hold_range'].default, 'hold_range' in inspect.getsource(R))" 2>&1 | Out-String).Trim()
Write-Output ('HOLD_PROBE ' + $probe)
if ($probe -ne 'True False False') { $failed = $true }
Pop-Location
if ($failed) { Write-Output 'CCE_POSTCHECK_FAILED (merge kept; Cowork review)'; exit 2 }
Write-Output 'CCE_DONE'
