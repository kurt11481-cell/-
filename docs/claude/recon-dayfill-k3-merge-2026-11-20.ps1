# Merge recon-dayfill-k3 (manual route, K3): broker reconciliation accepts Kiwoom day-session fills
# (fill window D-1 20:00 ET exclusive .. D 20:00 ET, segment DAY_SESSION) and the settlement base day
# becomes min(max(last KST fill day, session + 1 day)).
# User approval: direction card 2026-11-20 10:31:48 KST, run cards 10:46:50 / 11:12:57 KST (proposal id
# recon-dayfill-k3-proposal-2026-11-20, 3rd ed.), merge card recorded in that proposal section 0.
# Builder commit d9998bd (branch worktree-recon-dayfill-k3-t3). Judge: docs/claude/recon-dayfill-k3-judge-report.md (VERDICT: PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('RECON_DAYFILL_K3_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class ReconDayfillConsoleHandles {
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
    $consoleHandles = [ReconDayfillConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge recon-dayfill-k3. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$kst = [DateTime]::UtcNow.AddHours(9)
$approvedKst = '2026-11-20'
if ($kst.ToString('yyyy-MM-dd') -ne $approvedKst) { Stop-Merge ('merge approved only on ' + $approvedKst + ' KST') }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\clever-mayer-d73404'
$branch = 'worktree-recon-dayfill-k3-t3'
$commit = 'd9998bd9086c6d236defa9c843419d2869986776'
$judge = Join-Path $repo 'docs\claude\recon-dayfill-k3-judge-report.md'
$paths = @(
    'docs/claude/recon-dayfill-k3-report.md',
    'manage-us-stock-strategy/references/broker-snapshot-reconciliation.md',
    'manage-us-stock-strategy/scripts/auto_core_reconcile.py',
    'manage-us-stock-strategy/tests/test_auto_core_reconcile_dayfill.py',
    'manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py'
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
python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_reconcile*.py" 2>&1 | Select-Object -Last 3
$t1 = $LASTEXITCODE
Pop-Location
if ($t1 -ne 0) { Stop-Merge 'reconcile tests failed before merge' }
Write-Output 'CHECKS_OK'

git -C $repo merge --no-ff -q -m "Merge recon-dayfill-k3 (reconcile accepts Kiwoom day-session fills; K3, Judge PASS)" $commit
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'RECON_DAYFILL_K3_DONE'
