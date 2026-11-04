# Merge cd-guard (CD-1, manual route, K3): commit-docs.ps1 holds _pending files that change protected docs/claude
# paths read from authority-paths.txt; -ApproveProtected commits them only after an interactive console check + Enter.
# User approval: typed "commit-docs protect, run it" in the CEO-office room 2026-11-04 08:02:48 KST and chose
# "approve, today" on the card 2026-11-04 08:04:23 KST.
# Builder report: docs/claude/cd-guard-report.md (worktree .claude/worktrees/cd-guard, branch worktree-cd-guard,
# base aad5fbe). Judge: docs/claude/cd-guard-judge-report.md in the main checkout (separate Remote Control Judge
# session, all 9 items PASS, queued for the docs commit; last line VERDICT: PASS). The Judge report is checked by
# hash and verdict only and is never staged here.
# Main moved past the base (docs commits and 7f4bbad ri1-session2): the merge is a --no-ff merge of the worktree
# branch and stops if any merged path changed on main since the base.
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'cd-guard'
function Stop-Merge([string]$why) { Write-Output ('CD_GUARD_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
# hnd-check2 (tools/dev_pipeline/README.md): both standard handles must be console handles (GetConsoleMode);
# if the check cannot be built or run it stops (fail closed). Then the person at the keyboard presses Enter once.
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class CdGuardMergeConsoleHandles {
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
    $consoleHandles = [CdGuardMergeConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge cd-guard. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$wt = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$repo = (Resolve-Path -LiteralPath (Join-Path $wt '..\..\..')).Path
$base = (git -C $repo rev-parse aad5fbe0db85ffe66af4caf71b2cf6c80a851bb6).Trim()
$branch = 'worktree-cd-guard'
$self = 'docs/claude/cd-guard-merge-2026-11-04.ps1'
$judge = Join-Path $repo 'docs\claude\cd-guard-judge-report.md'
$judgeHash = '49bbebb29552285383500773c9c0cf2970f9da5bc7e24f9da20add8916e53cca'
$hashes = @{
    'tools/commit-docs.ps1' = '819fa3e1474f0823569c882cddff42b41c16a7cff1d57e27e35aec0f3e311d58'
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = '5ec97a391eed25aa8e1bf956d17513cc7b259bc8278077ef8957eed4be994a47'
    'docs/claude/cd-guard-report.md' = '412e169d6d79d20cd3030f00f9a2511eb2b7c1386e9224975098cb0f627eeebf'
}
$paths = @(@($hashes.Keys) + $self | Sort-Object)
$tests = @('test_dev_pipeline.py')

function Run-Tests([string]$dir, [string]$pattern) {
    Push-Location -LiteralPath $dir
    $out = @(python -B -m unittest discover -s manage-us-stock-strategy/tests -p $pattern 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
    Pop-Location
    $result = $out | Where-Object { $_ -match '^(OK|FAILED)' } | Select-Object -Last 1
    return [pscustomobject]@{ Code = $code; Result = "$result" }
}

$kst = [DateTime]::UtcNow.AddHours(9)
if ($kst.ToString('yyyy-MM-dd') -ne '2026-11-04') { Stop-Merge 'approval is for 2026-11-04 KST only' }
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
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $judge).Hash.ToLower() -ne $judgeHash) { Stop-Merge 'judge report changed' }
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
$dirty = @(git -C $repo status --porcelain --untracked-files=all -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
if ((git -C $wt rev-parse HEAD).Trim() -ne $base) { Stop-Merge 'worktree head is not base' }
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-cd-guard' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
foreach ($pattern in $tests) {
    $r = Run-Tests $wt $pattern
    Write-Output ($pattern + ' ' + $r.Result)
    if ($r.Code -ne 0) { Stop-Merge ($pattern + ' failed before merge') }
}
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'cd-guard-commit-message.txt'
$msg = "fix(docs-commit): hold _pending files that change protected docs/claude paths (cd-guard, CD-1)`n`n" +
       "cd-guard (K3, manual route; user typed 'commit-docs protect, run it' 2026-11-04 08:02:48 KST and chose`n" +
       "'approve, today' on the card 08:04:23 KST; merge by the user's own PowerShell line).`n" +
       "commit-docs.ps1 reads the docs/claude lines of authority-paths.txt (card-evidence-registry.json excluded) and`n" +
       "leaves a _pending file that changes one of them as HOLD, counted as a failure and not deleted. If the list cannot`n" +
       "be read or is empty, every file is held (fail closed). -ApproveProtected commits held files only after the same`n" +
       "interactive console check as dev-merge.ps1 and one Enter. One new text test in test_dev_pipeline.py.`n" +
       "Builder docs/claude/cd-guard-report.md, Judge docs/claude/cd-guard-judge-report.md (PASS, 9/9).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
$committed = @(git -C $wt show --name-only --format= HEAD | Where-Object { $_ } | Sort-Object)
if (($committed -join '|') -ne ($paths -join '|')) { Stop-Merge ('commit paths: ' + ($committed -join ',')) }
git -C $repo merge --no-ff -q -m "Merge cd-guard (commit-docs holds protected docs/claude paths; CD-1, K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$bad = @()
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { $bad += $p }
}
$left = @(git -C $repo status --porcelain -- $paths)
if (($bad.Count -ne 0) -or ($left.Count -ne 0)) {
    Write-Output ('CD_GUARD_CHECK_AFTER_MERGE hash_mismatch=' + ($bad -join ',') + ' status=' + $left.Count)
    exit 3
}
Write-Output 'MAIN_FILES_OK files=3'
Write-Output 'CD_GUARD_DONE'
