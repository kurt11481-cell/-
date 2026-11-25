# Merge layer-audit (layer-audit-1125 items 4-5, manual route for protected paths CLAUDE.md and AGENTS.md):
# CLAUDE.md gains a Precedence paragraph (summary of constitution section 1), two pointer lines (constitution,
# scheduled tasks), a corrected name for the identity/calendar activation file and the SCN-27H1 premise suspension
# note; AGENTS.md gains one line saying CLAUDE.md wins. No authority, limit or approval venue changes.
# User decision: typed approval in the project thread 2026-11-25 18:59:35 KST and the order-change card
# 2026-11-25 19:00:53 KST ('pull forward, start today'). The merge itself is the user's one line in their own
# interactive Windows PowerShell. Builder report: worktree docs/claude/layer-audit-1125-report.md (branch
# worktree-layer-audit). Judge: docs/claude/layer-audit-1125-judge-report.md in the main checkout (separate read-only
# session); checked for VERDICT: PASS and the two reviewed hashes, never staged here.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('LAYER_AUDIT_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class LayerAuditMergeConsoleHandles {
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
    $consoleHandles = [LayerAuditMergeConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Protected-path merge layer-audit (CLAUDE.md, AGENTS.md). Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$branch = 'worktree-layer-audit'
$wt = $null
# Find the worktree by scanning .claude\worktrees\* folders (paths from Resolve-Path stay Unicode-safe; git text
# output is decoded with the console code page in Windows PowerShell 5.1 and breaks Korean folder names).
$found = @()
foreach ($d in @(Get-ChildItem -LiteralPath (Join-Path $repo '.claude\worktrees') -Directory -ErrorAction SilentlyContinue)) {
    $b = (git -C $d.FullName rev-parse --abbrev-ref HEAD 2>$null)
    if ($LASTEXITCODE -eq 0 -and ("$b".Trim() -eq $branch)) { $found += $d.FullName }
}
if ($found.Count -ne 1) { Stop-Merge ('worktrees on branch worktree-layer-audit: ' + $found.Count) }
$wt = $found[0]
if (-not (Test-Path -LiteralPath $wt)) { Stop-Merge 'worktree path missing' }
$judge = Join-Path $repo 'docs\claude\layer-audit-1125-judge-report.md'
$hashes = @{
    'CLAUDE.md' = 'cd0868ce97165d4c605c9e558b023b85ef9dcc0575ab5000797eaae5093ad63c'
    'AGENTS.md' = 'c07e509436fff943054a90f58c8f7f7bde3caddc77c953eab71de43a44ecf718'
}
$report = 'docs/claude/layer-audit-1125-report.md'
$paths = @(@($hashes.Keys) + $report | Sort-Object)
# test_scheduled_prompt_kiwoom_profile.py is not run here: it reads docs/claude/scheduled-prompts/*.txt only and fails
# before this change (pending-wl-fetch-1122/diff.txt, commit b25f569); the Judge confirms it fails the same on main.
$tests = @('test_reconcile_broker_state.py', 'test_cowork_to_room_k3.py')

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
if (($day -lt '2026-11-25') -or ($day -gt '2026-11-28')) { Stop-Merge 'merge window is 2026-11-25..2026-11-28 KST' }
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
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-layer-audit' }
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

$msgFile = Join-Path $env:TEMP 'layer-audit-commit-message.txt'
$msg = "docs(rules): precedence summary and pointers in CLAUDE.md, Codex note in AGENTS.md (layer-audit-1125)`n`n" +
       "Manual route for protected paths. User typed approval in the project thread 2026-11-25 18:59:35 KST and`n" +
       "chose 'pull forward, start today' on the order card 19:00:53 KST; merge by the user's own PowerShell line.`n" +
       "CLAUDE.md: Precedence paragraph (constitution section 1 items 1-4, then this file, then project`n" +
       "instructions limited to session operations); pointer lines for constitution changes and scheduled tasks`n" +
       "(no new venue or rule); identity/calendar activation file renamed (it holds no order or quantity authority);`n" +
       "SCN-27H1 premise B0 suspension noted. AGENTS.md: CLAUDE.md wins where it differs. No authority change.`n" +
       "Builder docs/claude/layer-audit-1125-report.md, Judge docs/claude/layer-audit-1125-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKjoK2KtaKpJ1Xu1noh`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
$committed = @(git -C $wt show --name-only --format= HEAD | Where-Object { $_ } | Sort-Object)
if (($committed -join '|') -ne ($paths -join '|')) { Stop-Merge ('commit paths: ' + ($committed -join ',')) }
git -C $repo merge --no-ff -q -m "Merge layer-audit (CLAUDE.md precedence and pointers, AGENTS.md note; layer-audit-1125, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$bad = @()
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { $bad += $p }
}
$left = @(git -C $repo status --porcelain -- $paths)
if (($bad.Count -ne 0) -or ($left.Count -ne 0)) {
    Write-Output ('LAYER_AUDIT_CHECK_AFTER_MERGE hash_mismatch=' + ($bad -join ',') + ' status=' + $left.Count)
    exit 3
}
Write-Output 'MAIN_FILES_OK files=2'
Write-Output 'LAYER_AUDIT_DONE'
