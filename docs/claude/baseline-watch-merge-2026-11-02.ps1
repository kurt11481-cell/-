# Merge baseline-watch (manual route, K3): dev pipeline compares each new baseline with the previous ancestor baseline.
# B plan: +1..+9 failures = warning only, +10 or more = STOP_BASELINE_REGRESSED (accept-<sha8>.txt made by the user lowers it).
# User approval: re-approval card 2026-11-02 07:31:57 KST + typed "run" 07:34:10 KST, merge-ready card 08:37:22 KST
# (record: docs/claude/baseline-watch-proposal-2026-11-01.md last sections). Builder report: docs/claude/baseline-watch-report.md
# (in the worktree, merged with this commit). Judge: docs/claude/baseline-watch-judge-report.md (last line must be VERDICT: PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'baseline-watch'
function Stop-Merge([string]$why) { Write-Output ('BASELINE_WATCH_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
# hnd-check2 (tools/dev_pipeline/README.md): both standard handles must be console handles (GetConsoleMode);
# if the check cannot be built or run it stops (fail closed). Then the person at the keyboard presses Enter once.
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class BaselineWatchConsoleHandles {
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
    $consoleHandles = [BaselineWatchConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge baseline-watch. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\baseline-watch'
$base = (git -C $repo rev-parse d7b8b99f79f33654ea9453c6e39146b0c57c74b0).Trim()
$branch = 'worktree-baseline-watch'
$judge = Join-Path $repo 'docs\claude\baseline-watch-judge-report.md'
$hashes = @{
    'docs/claude/baseline-watch-report.md' = '6314e23852bbcac93b689adc03660489529c51ddead6f2be9d2a8bc32217d664'
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = '1a2a16990e99a204e135e1f54e43cb2c3672b7776ff10f9d5a20df948af1fee7'
    'tools/dev_pipeline/README.md' = '0565a6ad1a03aae7a16de981049b680eb3f6a385291a470d71b09575f0dd7245'
    'tools/dev_pipeline/devpipe.py' = 'eec24aec51b74419b919266655d994e3ca2f0153e7ecce59cee18f52823fac86'
}
$paths = @($hashes.Keys | Sort-Object)

$kst = [DateTime]::UtcNow.AddHours(9)
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
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-baseline-watch' }
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

$msgFile = Join-Path $env:TEMP 'baseline-watch-commit-message.txt'
$msg = "feat(dev-pipeline): watch baseline failure count against the previous ancestor baseline (baseline-watch)`n`n" +
       "baseline-watch (K3, manual route; user re-approval card 2026-11-02 07:31:57 KST, typed run 07:34:10 KST,`n" +
       "merge-ready card 08:37:22 KST in the CEO-office project thread; merge by the user's own PowerShell line).`n" +
       "B plan: +1..+9 new baseline failures = notice BASELINE_FAILURES_ROSE (status unchanged), +10 or more =`n" +
       "STOP_BASELINE_REGRESSED with baseline-regressed.txt; a user-made _baseline/accept-<sha8>.txt lowers it to a notice.`n" +
       "Known limits (Judge notes B, C): a stop clears at the next base; dev-merge rebase gets the same stop.`n" +
       "Builder docs/claude/baseline-watch-report.md, Judge docs/claude/baseline-watch-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKjpH54uB5vufnKJNHV`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge baseline-watch (baseline failure-count watch, B plan; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'BASELINE_WATCH_DONE'
