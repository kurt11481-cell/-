# Merge constitution-protect (manual route, K3): add the fund constitution files to the dev pipeline authority paths.
# tools/dev_pipeline/authority-paths.txt gains 3 lines at the end (blank, comment, docs/claude/constitution-v*.md).
# User approval: typed 2026-11-01 11:12:31 KST in the CEO-office company-PC project thread (record:
# docs/claude/top-guideline-review-2026-11-01.md section 10). Builder: docs/claude/constitution-protect-builder-report.md.
# Judge: docs/claude/constitution-protect-judge-report.md (last line must be VERDICT: PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'constitution-protect'
function Stop-Merge([string]$why) { Write-Output ('CONSTITUTION_PROTECT_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
# hnd-check2 (tools/dev_pipeline/README.md): both standard handles must be console handles (GetConsoleMode);
# if the check cannot be built or run it stops (fail closed). Then the person at the keyboard presses Enter once.
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class ConstitutionProtectConsoleHandles {
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
    $consoleHandles = [ConstitutionProtectConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge constitution-protect. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\constitution-protect'
$base = (git -C $repo rev-parse 6b0a248ff0a75f9d075f6095eb4873c98642f3e5).Trim()
$branch = 'worktree-constitution-protect'
$judge = Join-Path $repo 'docs\claude\constitution-protect-judge-report.md'
$target = 'tools/dev_pipeline/authority-paths.txt'
$hashes = @{ 'tools/dev_pipeline/authority-paths.txt' = 'a60a5f5f7c3a223285b5a781251aa82bbdc4186ce1f93011cab9e3c81d4d03b1' }
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
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-constitution-protect' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $paths) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
$numstat = (git -C $wt diff --numstat -- $target | Select-Object -First 1)
if ($numstat -notmatch '^3\s+0\s+tools/dev_pipeline/authority-paths\.txt$') { Stop-Merge ('diff is not 3 added lines: ' + $numstat) }
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
Push-Location $wt
python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py" -k authority_paths 2>&1 | Select-Object -Last 3
$t1 = $LASTEXITCODE
Pop-Location
if ($t1 -ne 0) { Stop-Merge 'targeted tests failed before merge' }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'constitution-protect-commit-message.txt'
$msg = "chore(dev-pipeline): fund constitution files are authority paths (constitution-protect)`n`n" +
       "constitution-protect (K3, manual route; user typed approval 2026-11-01 11:12:31 KST in the CEO-office project thread,`n" +
       "merge by the user's own PowerShell line). tools/dev_pipeline/authority-paths.txt gains docs/claude/constitution-v*.md,`n" +
       "so a dev-pipeline task that touches a constitution file ends as NEEDS_APPROVAL. Thread doc writes and the 23:30 docs`n" +
       "commit are unchanged. Builder docs/claude/constitution-protect-builder-report.md, Judge constitution-protect-judge-report.md.`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKgnV5Ua95KdwD51DT6`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge constitution-protect (constitution files as authority paths; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'CONSTITUTION_PROTECT_DONE'
