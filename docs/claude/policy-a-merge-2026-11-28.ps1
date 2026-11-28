# Merge policy-a (manual route, K3 exposure limit): cap buys that increase a 3x-leveraged product so that the
# 3x weight sum stays <= 0.10 of the account, and change the S7 fill default from SOXL to card-ADD-only.
# Approval: owner decision card 2026-11-26 22:28:38 KST 'an 1 start' (policy-a-1126); merge held by owner card 2026-11-27 00:35 KST,
# then owner typed 'merge go' 2026-11-28 08:57 KST; merge = the owner's own run of this script (replaces the unused 11/27 script).
# Builder: worktree .claude/worktrees/unruffled-fermat-725de3 (branch worktree-policy-a, HEAD 9e48ef2, UNCOMMITTED changes).
# Judge: independent read-only session, VERDICT: PASS, report written in its own worktree
#        .claude/worktrees/keen-borg-7d091b/docs/claude/policy-a-judge-report.md (main docs/claude write was blocked there).
# This script copies the 16 reviewed files from the Builder worktree and the Judge report into the main tree and makes
# ONE commit on codex/master-recovery-expansion. Every check runs before anything is changed; any mismatch stops with
# no change (fail-closed). No order, no Kiwoom, no auto_core run, no state, ledger or journal write. ASCII only (PS 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('POLICY_A_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class PolicyAConsoleHandles {
            [DllImport("kernel32.dll")]
            static extern IntPtr GetStdHandle(int which);
            [DllImport("kernel32.dll")]
            static extern bool GetConsoleMode(IntPtr handle, out uint mode);
            public static bool Both() {
                uint mode;
                return GetConsoleMode(GetStdHandle(-10), out mode) && GetConsoleMode(GetStdHandle(-11), out mode);
            }
        }
'@
    $consoleHandles = [PolicyAConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge policy-a (3x cap 0.10 + card-ADD-only fill). Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$kst = [DateTime]::UtcNow.AddHours(9)
$approvedKst = '2026-11-28'
if ($kst.ToString('yyyy-MM-dd') -ne $approvedKst) { Stop-Merge ('merge approved only on ' + $approvedKst + ' KST') }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\unruffled-fermat-725de3'
$wtBranch = 'worktree-policy-a'
$baseCommit = '9e48ef285e152ef156efdf86ade82d0fbdad9c14'
$judgeSrc = Join-Path $repo '.claude\worktrees\keen-borg-7d091b\docs\claude\policy-a-judge-report.md'
$judgeRel = 'docs/claude/policy-a-judge-report.md'
$judgeSha = '9973796fcea7969d6afd7b6c1a8400cdcbd9d4d1ef1d24e1121a411b3a4176d2'
# sha256 of each Builder worktree file as reviewed by the Judge (Builder report section 8 + the report itself).
$expected = [ordered]@{
    'stock-strategy-system/alert_policy.json'                                   = '96d076adeaa73a199b76534d47360a6cefcfd4ea3936df3aaf5c0922f88096b1'
    'manage-us-stock-strategy/scripts/portfolio_exposure.py'                    = 'e0b59e7cd238ba6e477f29c39e7113b94b172d4bafde2ffef165e745c4cb0b90'
    'manage-us-stock-strategy/scripts/auto_core_decide.py'                      = '89d7cd8da31b291b9c57a3b6ee55c7b9131f7d1b57f9aedf203a86c2528533db'
    'manage-us-stock-strategy/tests/test_policy_a.py'                           = 'd377be71d6ffadece0e77046a7b3fc768cf33ede57f44f18fc06c23e32d31de6'
    'manage-us-stock-strategy/tests/test_qqq_registration.py'                   = '8393018e73b333a09e5ba4c4d971ad2c49bfa04f742f9975948dfdbd4e619b5b'
    'manage-us-stock-strategy/tests/test_swing_k3_registration.py'              = 'af4db41063e3cdec5f48bd568a3722bab1dfe41683f6d426a8e4a4577e25458a'
    'manage-us-stock-strategy/tests/test_portfolio_exposure.py'                 = '2878700d4b037e0bf734009c05ba0999cb406374feb9bb55e3c835e251683cc3'
    'manage-us-stock-strategy/tests/test_portfolio_exposure_fail_closed.py'     = '30a376d9a6b25a2342f01c340448d56d3291d7684ec81af1668baca2e86f045c'
    'manage-us-stock-strategy/tests/test_run_portfolio_exposure_review.py'      = '3d2f40a4a8adcb8d7a75295be2f97457fc9bd4fa926de276efe31859b5582723'
    'manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py'             = '5b488a3739a714ea6297d73a96dd0fc78beaf5987db786600823217a45e89c47'
    'manage-us-stock-strategy/tests/test_auto_core_tickets.py'                  = '08311c7121a864bcbff3ac1dec3f153eed4c870c0699a3422c1a03b4636e423e'
    'manage-us-stock-strategy/tests/test_auto_core_hold_range.py'               = '52916d61cb2016676baaf16f98300f3748a04ce84d9bf832bb1d838679f8f77b'
    'manage-us-stock-strategy/tests/test_auto_core_risk1r.py'                   = 'b6301ad934e8c8f4fd2df48a7a8300eddcedfcebc927232d4c2b30c9f9b89a70'
    'manage-us-stock-strategy/tests/test_auto_core_enter_window.py'             = 'f49917ca78cc3ca3911c7beacc0fc1ecdd5ae14881c2397dcb3fe0a16c6f3290'
    'docs/claude/policy-a-BLOCKED.md'                                           = 'a9611cb67bb4add373bf3d022c21912bd2121779f12e777405d753c53cfdd38a'
    'docs/claude/policy-a-report.md'                                            = '1b7e90084e4e0905846035b63d5fb26118edd49dbdb5656bf76298f8698da192'
}
$paths = @($expected.Keys)
$allPaths = @($paths + $judgeRel)
$docPaths = @($allPaths | Where-Object { $_.StartsWith('docs/claude/') })
$codePaths = @($allPaths | Where-Object { -not $_.StartsWith('docs/claude/') })
function Get-Sha([string]$full) {
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { return '' }
    return (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Get-Full([string]$root, [string]$rel) { return (Join-Path $root ($rel -replace '/', '\')) }
function Get-Expected([string]$rel) { if ($rel -eq $judgeRel) { return $judgeSha } return $expected[$rel] }

# --- operating windows and locks (checked at start and again right before the copy) ---
function Test-Windows {
    $now = [DateTime]::UtcNow.AddHours(9)
    if ($now.ToString('yyyy-MM-dd') -ne $approvedKst) { Stop-Merge ('merge approved only on ' + $approvedKst + ' KST') }
    $tueSat = @('Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday') -contains $now.DayOfWeek.ToString()
    $minute = $now.Hour * 60 + $now.Minute
    if ($tueSat -and $minute -ge 345 -and $minute -lt 540) { Stop-Merge 'inside Tue-Sat 05:45-09:00 KST (auto-core)' }
    if ($minute -ge 1385 -and $minute -lt 1425) { Stop-Merge 'inside 23:05-23:45 KST (docs-commit)' }
    if (Test-Path -LiteralPath (Join-Path $repo 'workspace\outputs\dev-runs\_lock')) { Stop-Merge 'dev-run lock held' }
    $queued = @(Get-ChildItem -LiteralPath (Join-Path $repo 'docs\claude\_dev-queue') -Filter '*.txt' -File -ErrorAction SilentlyContinue)
    if ($queued.Count -ne 0) { Stop-Merge 'dev queue not empty' }
    foreach ($t in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide', 'InvestmentV2-DevQueue', 'InvestmentV2-DocsCommit',
                     'InvestmentV2-T2rcCheck')) {
        $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
        if ($task -and $task.State -eq 'Running') { Stop-Merge ($t + ' running') }
    }
}
Test-Windows

# --- Judge report (in the Judge worktree) ---
if ((Get-Sha $judgeSrc) -ne $judgeSha) { Stop-Merge 'judge report missing or changed since review' }
$judgeLast = @(Get-Content -LiteralPath $judgeSrc -Encoding UTF8 | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1)
if ($judgeLast.Count -ne 1 -or $judgeLast[0].Trim() -ne 'VERDICT: PASS') { Stop-Merge 'judge verdict is not PASS' }
if (-not (Select-String -LiteralPath $judgeSrc -SimpleMatch '9e48ef285e152ef156efdf86ade82d0fbdad9c14' -Quiet)) { Stop-Merge 'judge report does not name the reviewed base' }

# --- main tree: branch, base, clean target paths ---
$mainBranch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
if ($mainBranch -ne 'codex/master-recovery-expansion') { Stop-Merge ('main branch ' + $mainBranch) }
git -C $repo merge-base --is-ancestor $baseCommit HEAD
if ($LASTEXITCODE -ne 0) { Stop-Merge 'main HEAD does not contain the reviewed base 9e48ef2' }
$moved = @(git -C $repo diff --name-only $baseCommit HEAD)
$notDocs = @($moved | Where-Object { $_ -and (-not $_.StartsWith('docs/claude/')) })
if ($notDocs.Count -ne 0) { Stop-Merge ('main changed outside docs/claude since 9e48ef2: ' + ($notDocs -join ',')) }
$movedTargets = @($moved | Where-Object { $allPaths -contains $_ })
foreach ($m in $movedTargets) {
    if ((Get-Sha (Get-Full $repo $m)) -ne (Get-Expected $m)) { Stop-Merge ('a merged doc path changed on main since base: ' + $m) }
}
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$dirtyCode = @(git -C $repo status --porcelain --untracked-files=all -- $codePaths)
if ($dirtyCode.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirtyCode -join ' | ')) }
$otherCode = @(git -C $repo status --porcelain --untracked-files=no -- manage-us-stock-strategy stock-strategy-system workspace/policies)
if ($otherCode.Count -ne 0) { Stop-Merge ('main has other uncommitted code changes: ' + ($otherCode -join ' | ')) }
foreach ($d in $docPaths) {
    $h = Get-Sha (Get-Full $repo $d)
    if ($h -ne '' -and $h -ne (Get-Expected $d)) { Stop-Merge ('main copy differs from the reviewed file: ' + $d) }
}

# --- Builder worktree: head, exact change set, hashes ---
if (-not (Test-Path -LiteralPath $wt)) { Stop-Merge 'Builder worktree missing' }
if ((git -C $wt rev-parse HEAD).Trim() -ne $baseCommit) { Stop-Merge 'worktree head is not 9e48ef2' }
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $wtBranch) { Stop-Merge 'worktree branch is not worktree-policy-a' }
function Test-WorktreeSet {
    $st = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3).Trim('"') } | Sort-Object)
    if (($st -join '|') -ne (($paths | Sort-Object) -join '|')) { Stop-Merge ('worktree change set: ' + ($st -join ',')) }
    foreach ($p in $paths) {
        if ((Get-Sha (Get-Full $wt $p)) -ne $expected[$p]) { Stop-Merge ('worktree file changed since Judge: ' + $p) }
    }
}
Test-WorktreeSet

# --- targeted tests in the worktree before anything changes (no writes: -B) ---
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
Push-Location $wt
$fails = 0
foreach ($p in @('test_policy_a.py', 'test_portfolio_exposure*.py', 'test_run_portfolio_exposure_review*.py',
                 'test_qqq_registration.py', 'test_swing_k3_registration.py', 'test_auto_core_t2rc_corefix.py',
                 'test_auto_core_tickets.py', 'test_auto_core_hold_range.py', 'test_auto_core_risk1r.py',
                 'test_auto_core_enter_window.py')) {
    python -B -m unittest discover -s manage-us-stock-strategy/tests -p $p 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) { $fails += 1; Write-Output ('FAILED ' + $p) }
}
# test_auto_core_decide.py: exactly the one baseline failure is allowed = RegistryTests real registry, subTest SOXL,
# assertIsNone(trim_target_weight) on the SOXL card TRIM 0.10 (policy-a-BLOCKED.md baseline table). 2026-11-28 fix: the
# 11/28 first run stopped because the line carries the subTest suffix " (symbol='SOXL')" that the old pattern did not allow.
$decideOut = @(python -B -m unittest discover -s manage-us-stock-strategy/tests -p 'test_auto_core_decide.py' 2>&1 | ForEach-Object { "$_".TrimEnd() })
$decideExit = $LASTEXITCODE
$decideOut | Select-Object -Last 3
$bad = @($decideOut | Where-Object { $_ -match '^(FAIL|ERROR): ' })
$asserts = @($decideOut | Where-Object { $_ -match '^AssertionError' })
$baselineLine = '^FAIL: test_real_registry_is_schema_valid_and_every_hash_matches \(.*RegistryTests\.test_real_registry_is_schema_valid_and_every_hash_matches\) \(symbol=''SOXL''\)$'
$baselineAssert = '^AssertionError: 0\.1 is not None$'
if ($bad.Count -gt 1 -or ($bad.Count -eq 1 -and ($bad[0] -notmatch $baselineLine -or $asserts.Count -ne 1 -or $asserts[0] -notmatch $baselineAssert))) {
    $fails += 1; Write-Output ('FAILED test_auto_core_decide.py beyond the baseline: ' + (($bad + $asserts) -join ' | '))
}
if ((@(0, 1) -notcontains $decideExit) -or (-not ($decideOut -match '^Ran \d+ tests? in ')) -or
    (-not ($decideOut -match '^(OK( \(.*\))?|FAILED \(failures=1(, skipped=\d+)?\))$'))) {
    $fails += 1; Write-Output 'FAILED test_auto_core_decide.py did not finish as expected'
}
python -B manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Select-Object -Last 3
if ($LASTEXITCODE -ne 0) { $fails += 1; Write-Output 'FAILED validate_schema_contracts (worktree)' }
Pop-Location
if ($fails -ne 0) { Stop-Merge 'targeted tests failed before merge' }
Test-WorktreeSet
if ((Get-Sha $judgeSrc) -ne $judgeSha) { Stop-Merge 'judge report changed during checks' }
Test-Windows
Write-Output 'CHECKS_OK'

# --- apply: copy the 16 files + Judge report, verify, test on main, one commit; roll back on any failure ---
$existed = @{}
foreach ($p in $allPaths) { $existed[$p] = Test-Path -LiteralPath (Get-Full $repo $p) -PathType Leaf }
function Restore-Main {
    git -C $repo reset -q -- $allPaths 2>&1 | Out-Null
    foreach ($p in $allPaths) {
        $full = Get-Full $repo $p
        if ($existed[$p]) {
            git -C $repo cat-file -e ('HEAD:' + $p) 2>$null
            if ($LASTEXITCODE -eq 0) { git -C $repo checkout -q HEAD -- $p 2>&1 | Out-Null }
        } elseif (Test-Path -LiteralPath $full) {
            Remove-Item -LiteralPath $full -Force -ErrorAction SilentlyContinue
        }
    }
    $left = @(git -C $repo status --porcelain --untracked-files=all -- $allPaths | Where-Object { $_ -notmatch '^\?\? docs/claude/' })
    $leftNew = @($allPaths | Where-Object { (-not $existed[$_]) -and (Test-Path -LiteralPath (Get-Full $repo $_)) })
    if ($left.Count -ne 0 -or $leftNew.Count -ne 0) { Write-Output ('ROLLBACK_INCOMPLETE ' + (($left + $leftNew) -join ' | ')) }
}
$committed = $false
function Undo-Copy([string]$why) { Restore-Main; $script:committed = $true; Stop-Merge ($why + ' (rolled back)') }
try {
foreach ($p in $paths) {
    try {
        Copy-Item -LiteralPath (Get-Full $wt $p) -Destination (Get-Full $repo $p) -Force -ErrorAction Stop
    } catch {
        Undo-Copy ('copy failed: ' + $p)
    }
}
try {
    Copy-Item -LiteralPath $judgeSrc -Destination (Get-Full $repo $judgeRel) -Force -ErrorAction Stop
} catch {
    Undo-Copy 'copy failed: judge report'
}
foreach ($p in $allPaths) {
    if ((Get-Sha (Get-Full $repo $p)) -ne (Get-Expected $p)) { Undo-Copy ('main copy hash mismatch: ' + $p) }
}
Push-Location $repo
python -B -m unittest discover -s manage-us-stock-strategy/tests -p 'test_policy_a.py' 2>&1 | Select-Object -Last 3
$mc = $LASTEXITCODE
python -B manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Select-Object -Last 3
$sc = $LASTEXITCODE
Pop-Location
if ($mc -ne 0) { Undo-Copy 'test_policy_a failed on main copies' }
if ($sc -ne 0) { Undo-Copy 'validate_schema_contracts failed on main copies' }
git -C $repo add -- $allPaths
if ($LASTEXITCODE -ne 0) { Undo-Copy 'git add failed' }
$stagedNow = @(git -C $repo diff --cached --name-only)
$extra = @($stagedNow | Where-Object { $allPaths -notcontains $_ })
if ($extra.Count -ne 0) { Undo-Copy ('unexpected staged path: ' + ($extra -join ',')) }
foreach ($c in $codePaths) {
    if ($stagedNow -notcontains $c) { Undo-Copy ('code path not staged: ' + $c) }
}
git -C $repo commit -q -m 'policy(policy-a): cap buys that raise 3x-leveraged weight above 0.10 and make the S7 fill default card-ADD-only' -m 'Owner card 2026-11-26 22:28 KST (policy-a-1126); owner merge go 2026-11-28 08:57 KST. Judge: docs/claude/policy-a-judge-report.md PASS'
if ($LASTEXITCODE -ne 0) { Undo-Copy 'git commit failed' }
$committed = $true
} finally {
    if (-not $committed) { Restore-Main; Write-Output 'POLICY_A_INTERRUPTED (main restored)' }
}
$after = @(git -C $repo status --porcelain -- $allPaths)
if ($after.Count -ne 0) { Write-Output ('WARN paths not clean after commit: ' + ($after -join ' | ')) }
Write-Output ('COMMITTED main=' + (git -C $repo rev-parse --short HEAD).Trim() + ' files=' + $stagedNow.Count)
Write-Output 'POLICY_A_DONE'
