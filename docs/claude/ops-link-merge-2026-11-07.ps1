# Merge ops-link (ops-link-1107 A, manual route for protected paths, non-authority): CLAUDE.md line 111 extends the
# 2026-10-05 linkage rule through to company action with the linkage table (analysis-linkage-map section 1 item 8),
# judge-prompt.md adds G9, README line 18 names the "## linkage table" section, one new text test.
# User decision: typed "A, B, C (all of them)" (Korean) in the project thread 2026-11-07 12:01:27 KST (all three options of the card
# before it; this typed message is the S4 start input). The merge itself is the user's one line in their own
# interactive Windows PowerShell. Builder report: worktree docs/claude/ops-link-report.md (.claude/worktrees/ops-link,
# branch worktree-ops-link). Judge: docs/claude/ops-link-judge-report.md in the main checkout (separate read-only
# Remote Control Judge session); checked for VERDICT: PASS and the four reviewed hashes, never staged here.
# The four changed files must match hashes fixed before the Builder ran (docs/claude/ops-link-builder-prompt.md).
# Waits while a pipeline run is unmerged: merging protected paths first would make that run's dev-merge stop
# (STOP_BASE_MOVED, review-stability 109-113).
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'ops-link'
function Stop-Merge([string]$why) { Write-Output ('OPS_LINK_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
# hnd-check2 (tools/dev_pipeline/README.md): both standard handles must be console handles (GetConsoleMode);
# if the check cannot be built or run it stops (fail closed). Then the person at the keyboard presses Enter once.
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class OpsLinkMergeConsoleHandles {
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
    $consoleHandles = [OpsLinkMergeConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Protected-path merge ops-link. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\ops-link'
if (-not (Test-Path -LiteralPath $wt)) { Stop-Merge 'worktree .claude/worktrees/ops-link missing' }
$branch = 'worktree-ops-link'
$judge = Join-Path $repo 'docs\claude\ops-link-judge-report.md'
$hashes = @{
    'CLAUDE.md' = 'd2f22333b02712d64303ff6348941018b9dbae1536d17a4998e1048003ca4cfc'
    'tools/dev_pipeline/judge-prompt.md' = '768ee9aa82f6a67cabee9cb8074a3ad973c47a8ba607e81c5adaf78461b463c0'
    'tools/dev_pipeline/README.md' = '103a55cf2773787780884ce8eddfa54c412170211003553507b18969591cfa26'
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = 'daa31643a922748d58dca6d2f3451e60faf53d6b825316c24941206a29b6ae8a'
}
$report = 'docs/claude/ops-link-report.md'
$paths = @(@($hashes.Keys) + $report | Sort-Object)
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
$day = $kst.ToString('yyyy-MM-dd')
if (($day -lt '2026-11-07') -or ($day -gt '2026-11-10')) { Stop-Merge 'merge window is 2026-11-07..2026-11-10 KST' }
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
$queued = @(Get-ChildItem -LiteralPath (Join-Path $repo 'docs\claude\_dev-queue') -Filter '*.txt' -File -ErrorAction SilentlyContinue)
if ($queued.Count -ne 0) { Stop-Merge ('dev queue not empty: ' + (($queued | ForEach-Object { $_.Name }) -join ',')) }
$latestPath = Join-Path $repo 'workspace\outputs\dev-runs\LATEST.json'
if (Test-Path -LiteralPath $latestPath) {
    try { $latest = Get-Content -LiteralPath $latestPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Stop-Merge 'LATEST.json unreadable' }
    if (@('READY_TO_MERGE', 'NEEDS_APPROVAL') -contains "$($latest.status)") {
        $done = @(git -C $repo log --format=%H --grep ('Dev-Run: ' + $latest.id + ' ') HEAD)
        if ($done.Count -eq 0) { Stop-Merge ('pipeline run ' + $latest.id + ' is ' + $latest.status + ' and not merged yet - merge it first') }
    }
}
if (-not (Test-Path -LiteralPath $judge)) { Stop-Merge 'judge report missing' }
$judgeText = Get-Content -LiteralPath $judge -Raw -Encoding UTF8
$last = (Get-Content -LiteralPath $judge -Encoding UTF8 | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1).Trim()
if ($last -ne 'VERDICT: PASS') { Stop-Merge ('judge verdict: ' + $last) }
foreach ($p in $hashes.Keys) { if (-not $judgeText.Contains($hashes[$p])) { Stop-Merge ('judge report lacks reviewed hash of ' + $p) } }
$mainBranch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
if ($mainBranch -ne 'codex/master-recovery-expansion') { Stop-Merge ('main branch ' + $mainBranch) }
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-ops-link' }
$base = (git -C $wt rev-parse HEAD).Trim()
if (-not $judgeText.Contains($base.Substring(0, 7))) { Stop-Merge ('judge report does not name base ' + $base.Substring(0, 7)) }
git -C $repo merge-base --is-ancestor $base HEAD
if ($LASTEXITCODE -ne 0) { Stop-Merge 'base is not an ancestor of main' }
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$moved = @(git -C $repo diff --name-only $base HEAD)
$overlap = @($moved | Where-Object { $paths -contains $_ })
if ($overlap.Count -ne 0) { Stop-Merge ('a merged path changed on main since base: ' + ($overlap -join ',')) }
$dirty = @(git -C $repo status --porcelain --untracked-files=all -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash differs from the fixed target: ' + $p) }
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
foreach ($pattern in $tests) {
    $r = Run-Tests $wt $pattern
    Write-Output ($pattern + ' ' + $r.Result)
    if ($r.Code -ne 0) { Stop-Merge ($pattern + ' failed before merge') }
}
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'ops-link-commit-message.txt'
$msg = "docs(rules): link design to company action with the linkage table (ops-link-1107 A)`n`n" +
       "Manual route for protected paths, non-authority. User typed 'A, B, C' (all three options) in the project`n" +
       "thread 2026-11-07 12:01:27 KST; merge by the user's own PowerShell line.`n" +
       "CLAUDE.md line 111: analysis outputs, new features and scheduled-task changes carry the linkage table of`n" +
       "analysis-linkage-map section 1 item 8 (cells 2, 3, 5 cited by file:line or trigger id; breaks shown with the`n" +
       "approval that closes them; urgent reduce/incident cards first). Design/proposal sessions only; adds no`n" +
       "authority or trading rule (a new market-signal alert kind still needs its own approval).`n" +
       "judge-prompt.md G9 checks the linkage table section (prompts dated 2026-11-07 or earlier: not applicable).`n" +
       "README line 18 names the section. One new text test in test_dev_pipeline.py.`n" +
       "Builder docs/claude/ops-link-report.md, Judge docs/claude/ops-link-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKjtixctFi1qB5ExVnT`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
$committed = @(git -C $wt show --name-only --format= HEAD | Where-Object { $_ } | Sort-Object)
if (($committed -join '|') -ne ($paths -join '|')) { Stop-Merge ('commit paths: ' + ($committed -join ',')) }
git -C $repo merge --no-ff -q -m "Merge ops-link (linkage table through to company action; ops-link-1107 A, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$bad = @()
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { $bad += $p }
}
$left = @(git -C $repo status --porcelain -- $paths)
if (($bad.Count -ne 0) -or ($left.Count -ne 0)) {
    Write-Output ('OPS_LINK_CHECK_AFTER_MERGE hash_mismatch=' + ($bad -join ',') + ' status=' + $left.Count)
    exit 3
}
Write-Output 'MAIN_FILES_OK files=4'
Write-Output 'OPS_LINK_DONE'
