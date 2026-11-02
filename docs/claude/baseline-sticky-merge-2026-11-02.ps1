# Merge baseline-sticky (manual route, K3): previous_baseline skips a stopped baseline
# (own added_failures >= BASELINE_ROSE_STOP and no accept-<sha8>.txt), so a stop no longer clears at the next base.
# User approval: card 2026-11-02 09:02:56 KST ("approve, today") + typed run line 09:40:20 KST in the CEO-office
# execution thread, typed "proceed" 11:38:25 KST for the merge script (record: docs/claude/baseline-sticky-proposal-2026-11-02.md).
# Builder report: docs/claude/baseline-sticky-report.md (in the worktree, merged with this commit).
# Judge: docs/claude/baseline-sticky-judge-report.md (last line must be VERDICT: PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'baseline-sticky'
function Stop-Merge([string]$why) { Write-Output ('BASELINE_STICKY_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
# hnd-check2 (tools/dev_pipeline/README.md): both standard handles must be console handles (GetConsoleMode);
# if the check cannot be built or run it stops (fail closed). Then the person at the keyboard presses Enter once.
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class BaselineStickyConsoleHandles {
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
    $consoleHandles = [BaselineStickyConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge baseline-sticky. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\baseline-sticky'
$base = (git -C $repo rev-parse 8615efb27e7977ed3c05f32cb64612fafe22c76d).Trim()
$branch = 'worktree-baseline-sticky'
$judge = Join-Path $repo 'docs\claude\baseline-sticky-judge-report.md'
$hashes = @{
    'docs/claude/baseline-sticky-report.md' = '4768988b8a1fa78276f528f34221922436ed437e65fa0914dc193fc3e31db068'
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = 'e710adf8592f379080b1e32289b6ae471d2463bce3c4c6c130a2dc815c4507d7'
    'tools/dev_pipeline/README.md' = '5601c19a4ead5d41b861c69b83dfa129e7c7f3297e1b3eae6ec5d5a60db74b1d'
    'tools/dev_pipeline/devpipe.py' = 'ba9fa1a508c4cdbea71e517d378f2352284acb0d1bffaa421189ccac69050f0a'
}
$paths = @($hashes.Keys | Sort-Object)

$kst = [DateTime]::UtcNow.AddHours(9)
if ($kst.ToString('yyyy-MM-dd') -ne '2026-11-02') { Stop-Merge 'approval is for 2026-11-02 KST only' }
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
$overlap = @($moved | Where-Object { $paths -contains $_ })
if ($overlap.Count -ne 0) { Stop-Merge ('a merged path changed on main since base: ' + ($overlap -join ',')) }
$dirty = @(git -C $repo status --porcelain -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
if ((git -C $wt rev-parse HEAD).Trim() -ne $base) { Stop-Merge 'worktree head is not base' }
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-baseline-sticky' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $paths) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
Push-Location $wt
python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py" 2>&1 | Select-Object -Last 3
$t1 = $LASTEXITCODE
Pop-Location
if ($t1 -ne 0) { Stop-Merge 'test_dev_pipeline failed before merge' }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'baseline-sticky-commit-message.txt'
$msg = "feat(dev-pipeline): skip stopped baselines when picking the previous baseline (baseline-sticky)`n`n" +
       "baseline-sticky (K3, manual route; user card 2026-11-02 09:02:56 KST, typed run 09:40:20 KST in the`n" +
       "CEO-office execution thread; merge by the user's own PowerShell line). Follow-up to baseline-watch Judge note B.`n" +
       "previous_baseline drops a cached baseline whose own added_failures >= BASELINE_ROSE_STOP and that has no`n" +
       "_baseline/accept-<sha8>.txt, so a stop stays until the failures are fixed or the user accepts it.`n" +
       "Old caches without the key, 1..9 warning baselines and accepted baselines stay candidates. Threshold, names unchanged.`n" +
       "Builder docs/claude/baseline-sticky-report.md, Judge docs/claude/baseline-sticky-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKj7daFfn4GjcXfMsBG`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge baseline-sticky (stopped baselines stay stopped; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'BASELINE_STICKY_DONE'
