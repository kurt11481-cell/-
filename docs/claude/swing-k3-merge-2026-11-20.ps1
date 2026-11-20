# Merge swing-k3 (manual route, K3 approved products): approve PLTR/CRWD as new-buy products and record
# verified identity for approved products missing from the canonical registry (LITE, PWR, MU, DELL, AMD, TQQQ).
# Builder: worktree .claude/worktrees/swing-k3 (branch worktree-swing-k3, HEAD 0878e76, UNCOMMITTED changes).
# Judge: docs/claude/swing-k3-judge-report.md (verdict: PASS, 2026-11-20 ~17:13 KST, independent read-only session).
# Because the Builder left its changes uncommitted, this script copies the 9 allowed files from the worktree
# into the main tree and makes ONE commit on codex/master-recovery-expansion (registry and policy together:
# their hashes are bound, one without the other fails closed with POLICY_REGISTRY_MISMATCH).
# Every check runs before anything is changed; any mismatch stops with no change (fail-closed).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no auto_core run, no state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('SWING_K3_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class SwingK3ConsoleHandles {
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
    $consoleHandles = [SwingK3ConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge swing-k3 (approved products). Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$kst = [DateTime]::UtcNow.AddHours(9)
$approvedKst = '2026-11-20'
if ($kst.ToString('yyyy-MM-dd') -ne $approvedKst) { Stop-Merge ('merge approved only on ' + $approvedKst + ' KST') }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\swing-k3'
$wtBranch = 'worktree-swing-k3'
$baseCommit = '0878e761e5fe60f037cd1ff362d9c9fb41499449'
$judge = Join-Path $repo 'docs\claude\swing-k3-judge-report.md'
$judgeSha = 'aa6240d71572f66b49d53a4f7334c2cb2634cb133a1f231e08e61b55f38859db'
$registryPath = 'workspace/policies/instrument_registry.json'
$policyPath = 'stock-strategy-system/alert_policy.json'
# sha256 of each worktree file as reviewed by the Judge (all last written 16:15-16:55 KST, before the Judge began).
$expected = [ordered]@{
    'workspace/policies/instrument_registry.json'                  = '1ae1e71836f568c25b5a41352a6a56f1988b0ef507fac4df6634918d1d408f79'
    'stock-strategy-system/alert_policy.json'                      = '06fdb67264aa7a9a90b81d0dacac13822a9e49070dd87dc5488ec9a9d0171580'
    'manage-us-stock-strategy/scripts/auto_core_tickets.py'        = 'bc2b852f9a19786c8ab587fbf93afd210c25ed49732db194eb8f2886c09265ed'
    'manage-us-stock-strategy/tests/test_swing_k3_registration.py' = 'fc7df3e86e449f2695ea517b7625034482459616ed98f390d5134e1d01c89e25'
    'manage-us-stock-strategy/tests/test_portfolio_exposure.py'    = '38294834c4b06ee56b360281fd17f3cfa94f73edffbaa0e9411c60aa1f9ef338'
    'manage-us-stock-strategy/tests/test_qqq_registration.py'      = '16ddd4acf39234539ad68e2d0f0c3840b43eb58138fa3d52ad6bd8dc326c1331'
    'manage-us-stock-strategy/tests/test_auto_core_qqq_b.py'       = '9d56b6808be2e3c9e4b52a47bc74ad2294a1f3d7e9a9b880bd787558ff8dd438'
    'docs/claude/swing-k3-report.md'                               = '6712906f7bfb95f432324f6c53121fc5821baba8a919badccfc77eb5fbdbdc77'
    'docs/claude/swing-k3-BLOCKED.md'                              = '59ba299639aaafc15c921f203ed7abf76d5358a9a7b832f7e8a9e26cf367e243'
}
$paths = @($expected.Keys)
$docPaths = @($paths | Where-Object { $_.StartsWith('docs/claude/') })
$codePaths = @($paths | Where-Object { -not $_.StartsWith('docs/claude/') })
function Get-Sha([string]$full) {
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { return '' }
    return (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Get-Full([string]$root, [string]$rel) { return (Join-Path $root ($rel -replace '/', '\')) }

# --- operating windows and locks ---
$tueSat = @('Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday') -contains $kst.DayOfWeek.ToString()
$minute = $kst.Hour * 60 + $kst.Minute
if ($tueSat -and $minute -ge 360 -and $minute -lt 540) { Stop-Merge 'inside Tue-Sat 06:00-09:00 KST' }
if ($minute -ge 1400 -and $minute -lt 1425) { Stop-Merge 'inside 23:20-23:45 KST (docs-commit)' }
if (Test-Path -LiteralPath (Join-Path $repo 'workspace\outputs\dev-runs\_lock')) { Stop-Merge 'dev-run lock held' }
$queued = @(Get-ChildItem -LiteralPath (Join-Path $repo 'docs\claude\_dev-queue') -Filter '*.txt' -File -ErrorAction SilentlyContinue)
if ($queued.Count -ne 0) { Stop-Merge 'dev queue not empty' }
foreach ($t in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide', 'InvestmentV2-DevQueue', 'InvestmentV2-DocsCommit',
                 'InvestmentV2-T2rcCheck')) {
    $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') { Stop-Merge ($t + ' running') }
}

# --- Judge report ---
if ((Get-Sha $judge) -ne $judgeSha) { Stop-Merge 'judge report missing or changed since copy' }
if (-not (Select-String -LiteralPath $judge -Pattern '^verdict: PASS\s*$' -Quiet)) { Stop-Merge 'judge verdict is not PASS' }
if (-not (Select-String -LiteralPath $judge -SimpleMatch '0878e76' -Quiet)) { Stop-Merge 'judge report does not name the reviewed base' }

# --- main tree: branch, base, clean target paths ---
$mainBranch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
if ($mainBranch -ne 'codex/master-recovery-expansion') { Stop-Merge ('main branch ' + $mainBranch) }
git -C $repo merge-base --is-ancestor $baseCommit HEAD
if ($LASTEXITCODE -ne 0) { Stop-Merge 'main HEAD does not contain the reviewed base 0878e76' }
$moved = @(git -C $repo diff --name-only $baseCommit HEAD)
$notDocs = @($moved | Where-Object { $_ -and (-not $_.StartsWith('docs/claude/')) })
if ($notDocs.Count -ne 0) { Stop-Merge ('main changed outside docs/claude since 0878e76: ' + ($notDocs -join ',')) }
$movedTargets = @($moved | Where-Object { $paths -contains $_ })
foreach ($m in $movedTargets) {
    if ((Get-Sha (Get-Full $repo $m)) -ne $expected[$m]) { Stop-Merge ('a merged doc path changed on main since base: ' + $m) }
}
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$dirtyCode = @(git -C $repo status --porcelain --untracked-files=all -- $codePaths)
if ($dirtyCode.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirtyCode -join ' | ')) }
foreach ($d in $docPaths) {
    $h = Get-Sha (Get-Full $repo $d)
    if ($h -ne '' -and $h -ne $expected[$d]) { Stop-Merge ('main copy differs from the reviewed file: ' + $d) }
}

# --- Builder worktree: head, exact change set, hashes ---
if (-not (Test-Path -LiteralPath $wt)) { Stop-Merge 'worktree swing-k3 missing' }
if ((git -C $wt rev-parse HEAD).Trim() -ne $baseCommit) { Stop-Merge 'worktree head is not 0878e76' }
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $wtBranch) { Stop-Merge 'worktree branch is not worktree-swing-k3' }
function Test-WorktreeSet {
    $st = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3).Trim('"') } | Sort-Object)
    if (($st -join '|') -ne (($paths | Sort-Object) -join '|')) { Stop-Merge ('worktree change set: ' + ($st -join ',')) }
    foreach ($p in $paths) {
        if ((Get-Sha (Get-Full $wt $p)) -ne $expected[$p]) { Stop-Merge ('worktree file changed since Judge: ' + $p) }
    }
}
Test-WorktreeSet

# --- targeted tests and registry/policy hash binding in the worktree (no writes) ---
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
Push-Location $wt
$fails = 0
foreach ($p in @('test_swing_k3_registration.py', 'test_portfolio_exposure*.py', 'test_qqq_registration.py',
                 'test_auto_core_qqq_b.py', 'test_reconcile_broker_state.py', 'test_validate_decision_record.py')) {
    python -B -m unittest discover -s manage-us-stock-strategy/tests -p $p 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) { $fails += 1; Write-Output ('FAILED ' + $p) }
}
python -B manage-us-stock-strategy/scripts/validate_registry_consistency.py --registry $registryPath --policy $policyPath 2>&1 | Select-Object -Last 4
if ($LASTEXITCODE -ne 0) { $fails += 1; Write-Output 'FAILED validate_registry_consistency (worktree)' }
Pop-Location
if ($fails -ne 0) { Stop-Merge 'targeted tests failed before merge' }
Test-WorktreeSet
Write-Output 'CHECKS_OK'

# --- apply: copy the 9 files, verify, one commit; roll back on any failure ---
$existed = @{}
foreach ($p in $paths) { $existed[$p] = Test-Path -LiteralPath (Get-Full $repo $p) -PathType Leaf }
function Undo-Copy([string]$why) {
    git -C $repo reset -q -- $paths 2>&1 | Out-Null
    foreach ($p in $paths) {
        $full = Get-Full $repo $p
        if ($existed[$p]) {
            git -C $repo cat-file -e ('HEAD:' + $p) 2>$null
            if ($LASTEXITCODE -eq 0) { git -C $repo checkout -q HEAD -- $p 2>&1 | Out-Null }
        } elseif (Test-Path -LiteralPath $full) {
            Remove-Item -LiteralPath $full -Force
        }
    }
    Stop-Merge ($why + ' (rolled back)')
}
foreach ($p in $paths) {
    try {
        Copy-Item -LiteralPath (Get-Full $wt $p) -Destination (Get-Full $repo $p) -Force -ErrorAction Stop
    } catch {
        Undo-Copy ('copy failed: ' + $p)
    }
}
foreach ($p in $paths) {
    if ((Get-Sha (Get-Full $repo $p)) -ne $expected[$p]) { Undo-Copy ('main copy hash mismatch: ' + $p) }
}
Push-Location $repo
python -B manage-us-stock-strategy/scripts/validate_registry_consistency.py --registry $registryPath --policy $policyPath 2>&1 | Select-Object -Last 4
$vc = $LASTEXITCODE
Pop-Location
if ($vc -ne 0) { Undo-Copy 'validate_registry_consistency failed on main copies' }
git -C $repo add -- $paths
if ($LASTEXITCODE -ne 0) { Undo-Copy 'git add failed' }
$stagedNow = @(git -C $repo diff --cached --name-only)
$extra = @($stagedNow | Where-Object { $paths -notcontains $_ })
if ($extra.Count -ne 0) { Undo-Copy ('unexpected staged path: ' + ($extra -join ',')) }
foreach ($c in $codePaths) {
    if ($stagedNow -notcontains $c) { Undo-Copy ('code path not staged: ' + $c) }
}
git -C $repo commit -q -m 'policy(swing-k3): approve PLTR/CRWD as new-buy products and record verified identity for approved products missing from the canonical registry (LITE, PWR, MU, DELL, AMD, TQQQ)' -m 'Judge: docs/claude/swing-k3-judge-report.md PASS'
if ($LASTEXITCODE -ne 0) { Undo-Copy 'git commit failed' }
$after = @(git -C $repo status --porcelain -- $paths)
if ($after.Count -ne 0) { Write-Output ('WARN paths not clean after commit: ' + ($after -join ' | ')) }
Write-Output ('COMMITTED main=' + (git -C $repo rev-parse --short HEAD).Trim() + ' files=' + $stagedNow.Count)
Write-Output 'SWING_K3_DONE'
