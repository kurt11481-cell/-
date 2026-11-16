# Merge baseline-pyver (manual route, K3): when no previous baseline with the same Python exists, the dev pipeline
# compares with the nearest ancestor baseline of another Python (same thresholds: +1..+9 notice, +10 STOP_BASELINE_REGRESSED).
# User approval: run card 2026-11-16 16:34:11 KST (proposal id baseline-pyver-proposal-2026-11-13) + typed run 2026-11-16 16:55:07 KST,
# merge card 2026-11-16 18:39:18 KST (record: docs/claude/baseline-pyver-proposal-2026-11-13.md last sections).
# Builder report: docs/claude/baseline-pyver-report.md (in the worktree, merged with this commit).
# Judge: docs/claude/baseline-pyver-judge-report.md (last non-empty line must be VERDICT: PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'baseline-pyver'
function Stop-Merge([string]$why) { Write-Output ('BASELINE_PYVER_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class BaselinePyverConsoleHandles {
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
    $consoleHandles = [BaselinePyverConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge baseline-pyver. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$kst = [DateTime]::UtcNow.AddHours(9)
$approvedKst = '2026-11-16'
if ($kst.ToString('yyyy-MM-dd') -ne $approvedKst) { Stop-Merge ('merge approved only on ' + $approvedKst + ' KST') }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\goofy-tesla-d71591'
$base = (git -C $repo rev-parse 129eb9e7c5236eba86e9a29aa5f9b6bdd469aa29).Trim()
$branch = 'worktree-baseline-pyver'
$judge = Join-Path $repo 'docs\claude\baseline-pyver-judge-report.md'
$judgeHash = '3fcbff0c2a8dadf4401c7107f2a196c604c3b2ba145b4f0dbc8dcf7267551f1a'
$hashes = @{
    'docs/claude/baseline-pyver-report.md' = 'da6b7bb47e027701e42b52ecaf99dd872cd709c804508f0fe0105b8c32628e1c'
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = 'e6c872672c31e6b371c0afd65c78a0652b10b57c66433a3808db3e40db1dc40f'
    'tools/dev_pipeline/README.md' = '959e6739fea5e385594385b34041af634bac4149cbf5567fc1ffe6558774238a'
    'tools/dev_pipeline/devpipe.py' = '0dfeec1cc81c6a6fdd693d932f23a6555ed2680e2968b86fab9d176e54e12bf8'
}
$paths = @($hashes.Keys | Sort-Object)

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
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $judge).Hash.ToLower() -ne $judgeHash) { Stop-Merge 'judge report changed after review' }
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
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-baseline-pyver' }
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

$msgFile = Join-Path $env:TEMP 'baseline-pyver-commit-message.txt'
$msg = "feat(dev-pipeline): compare with the nearest ancestor baseline of another Python when none with the same Python exists (baseline-pyver)`n`n" +
       "baseline-pyver (K3, manual route; code review 2026-11-13 H-2; user run card 2026-11-16 16:34:11 KST,`n" +
       "typed run 2026-11-16 16:55:07 KST, merge card 2026-11-16 18:39:18 KST in the CEO-office project thread; merge by the user's own PowerShell line).`n" +
       "Same-Python previous baseline first (previous_baseline unchanged); else nearest ancestor of another Python, adds prev_python`n" +
       "and notice BASELINE_PREV_OTHER_PYTHON:<ver>; thresholds unchanged (+1..+9 notice, +10 STOP_BASELINE_REGRESSED, accept file lowers).`n" +
       "Builder docs/claude/baseline-pyver-report.md, Judge docs/claude/baseline-pyver-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKjEvrdWhziyZbD7DnU`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge baseline-pyver (baseline compare across Python versions; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'BASELINE_PYVER_DONE'
