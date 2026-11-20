# Merge cowork-to-room-k3 (manual route, K3): the CEO-office company-PC project thread may run broker
# reconciliation apply and the S5 line/peak review journal entries on the user's own typed message
# (PROJECT_THREAD_USER_DECISION, 4 fields, code in the verbatim field), propose rejects a missing
# cash-flow evidence file after S5 activation, and manual reconciliation is the documented way out of a HOLD.
# User approval: direction card 2026-11-20 11:55:27 KST, run card 13:06:03 KST, 3rd-ed. continuation card
# 14:14:06 KST, merge card 14:38:17 KST (proposal id cowork-to-room-k3-proposal-2026-11-20).
# Builder commit 13c5261 (branch worktree-cowork-to-room-k3). Judge: docs/claude/cowork-to-room-k3-judge-report.md (VERDICT: PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('COWORK_TO_ROOM_K3_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class CoworkToRoomConsoleHandles {
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
    $consoleHandles = [CoworkToRoomConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge cowork-to-room-k3. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$kst = [DateTime]::UtcNow.AddHours(9)
$approvedKst = '2026-11-20'
if ($kst.ToString('yyyy-MM-dd') -ne $approvedKst) { Stop-Merge ('merge approved only on ' + $approvedKst + ' KST') }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\serene-albattani-2f3079'
$branch = 'worktree-cowork-to-room-k3'
$commit = '13c52614f6ebb829411175bf042d79263e0fe4a9'
$judge = Join-Path $repo 'docs\claude\cowork-to-room-k3-judge-report.md'
$paths = @(
    'CLAUDE.md',
    'docs/claude/cowork-to-room-k3-report.md',
    'manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json',
    'manage-us-stock-strategy/references/broker-snapshot-reconciliation.md',
    'manage-us-stock-strategy/references/portfolio-exposure-review.md',
    'manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json',
    'manage-us-stock-strategy/scripts/apply_user_confirmed_broker_snapshot.py',
    'manage-us-stock-strategy/scripts/portfolio_review_journal.py',
    'manage-us-stock-strategy/scripts/reconcile_broker_state.py',
    'manage-us-stock-strategy/scripts/validation_common.py',
    'manage-us-stock-strategy/tests/test_approval_human_check.py',
    'manage-us-stock-strategy/tests/test_auto_core.py',
    'manage-us-stock-strategy/tests/test_cash_flow_evidence.py',
    'manage-us-stock-strategy/tests/test_cowork_to_room_k3.py',
    'manage-us-stock-strategy/tests/test_reconcile_broker_state.py'
)

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
if (-not (Test-Path -LiteralPath $judge)) { Stop-Merge 'judge report missing' }
$last = (Get-Content -LiteralPath $judge -Encoding UTF8 | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1).Trim()
if ($last -ne 'VERDICT: PASS') { Stop-Merge ('judge verdict: ' + $last) }
if (-not (Select-String -LiteralPath $judge -SimpleMatch $commit -Quiet)) { Stop-Merge 'judge report does not name the reviewed commit' }
$mainBranch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
if ($mainBranch -ne 'codex/master-recovery-expansion') { Stop-Merge ('main branch ' + $mainBranch) }
if ((git -C $repo rev-parse $branch).Trim() -ne $commit) { Stop-Merge 'branch head is not the reviewed commit' }
$base = (git -C $repo merge-base HEAD $commit).Trim()
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$changed = @(git -C $repo diff --name-only $base $commit | Sort-Object)
if (($changed -join '|') -ne (($paths | Sort-Object) -join '|')) { Stop-Merge ('branch paths: ' + ($changed -join ',')) }
$moved = @(git -C $repo diff --name-only $base HEAD)
$overlap = @($moved | Where-Object { $paths -contains $_ })
if ($overlap.Count -ne 0) { Stop-Merge ('a merged path changed on main since base: ' + ($overlap -join ',')) }
$dirty = @(git -C $repo status --porcelain -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
if ((git -C $wt rev-parse HEAD).Trim() -ne $commit) { Stop-Merge 'worktree head is not the reviewed commit' }
$wtStatus = @(git -C $wt status --porcelain --untracked-files=all)
if ($wtStatus.Count -ne 0) { Stop-Merge ('worktree not clean: ' + ($wtStatus -join ',')) }
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
Push-Location $wt
$fails = 0
foreach ($p in @('test_cowork_to_room_k3.py', 'test_reconcile_broker_state.py', 'test_approval_human_check.py',
                 'test_portfolio_review_journal.py', 'test_cash_flow_evidence.py')) {
    python -B -m unittest discover -s manage-us-stock-strategy/tests -p $p 2>&1 | Select-Object -Last 3
    if ($LASTEXITCODE -ne 0) { $fails += 1 }
}
Pop-Location
if ($fails -ne 0) { Stop-Merge 'targeted tests failed before merge' }
Write-Output 'CHECKS_OK'

git -C $repo merge --no-ff -q -m "Merge cowork-to-room-k3 (project thread runs reconcile apply and S5 review journal on the user's typed message; evidence required after activation; K3, Judge PASS)" $commit
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'COWORK_TO_ROOM_K3_DONE'
