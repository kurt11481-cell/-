# Merge kiwoom-block-fix3 (manual route, K3 follow-up: tests and docs only, no hook/settings/deny change).
# Why: after kiwoom-block was merged (main c9c0877) three tests failed because they pinned the old settings (deny count 23,
# "current settings vs proposed" comparison). fix3 rewrites those expectations (both states pass) and corrects the report.
# User approval: the user ran the fix3 Builder in the project room (2026-10-26 about 07:15 KST; "fix3 jinhaeng" requested in the
# thread) and merges by the user's own PowerShell line. Judge: workspace/outputs/manual-bj/kiwoom-block-fix3/judge-1.txt
# (the Judge ran the three test groups itself: 25 / 126 / 28 OK; last line VERDICT: PASS).
# Changes (4 paths): test_dev_pipeline.py, test_kiwoom_order_block_hook.py, kiwoom-block-builder-report.md (edits),
# kiwoom-block-fix3-report.md (new). .claude/settings.json and the hook are NOT touched.
# Checks: interactive console (four conditions, both handles are console handles, then one Enter); no dev-run lock and no
# auto-core / decide / dev / docs-commit / t2rc-check task running; not inside Tue-Sat 06:00-09:00 KST or 23:20-23:45 KST;
# Judge file ends with VERDICT: PASS; base c9c0877 is an ancestor of main and main touched no merged path since (and only
# docs/claude/ paths at all); worktree changed exactly the 4 paths with the sha256 measured before the merge; main
# settings and hook are the merged versions. NEW: the three test groups run in the worktree BEFORE the commit and the script
# stops on any failure (nothing is committed or merged then). After the merge they run once more on main.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('KWB3_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class KwbConsoleHandles {
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
    $consoleHandles = [KwbConsoleHandles]::Both()
} catch { $consoleHandles = $false }
if ($consoleHandles -ne $true) { Stop-Merge 'standard handles are not console handles' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge kiwoom-block-fix3. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch { $entered = $null }
if ($null -eq $entered) { Stop-Merge 'no Enter (end of input)' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\kiwoom-block-fix3'
$base = (git -C $repo rev-parse c9c0877).Trim()
$branch = 'worktree-kiwoom-block-fix3'
$judge = Join-Path $repo 'workspace\outputs\manual-bj\kiwoom-block-fix3\judge-1.txt'
$settingsSha = '459cd04f0dee5aa915fafc0397af2369b9348aab19632505df953d466ea36942'
$hookSha = '2818d79fcdd5ee2083be65c888447ea84a04f75188ca35376a5b2038c87cc81f'
$hashes = @{
    'docs/claude/kiwoom-block-builder-report.md' = '45eef8cb093b7481c5a71b1ed0c393b04822fc35fb36c12ec76179ee6434ce4a';
    'docs/claude/kiwoom-block-fix3-report.md' = '4c1cdf9eb6ce99acb45bc8d47ec36ec437826edfa1ea84fb751897ad35a6050c';
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = 'eff5db3ac07e04e263095ec3d6a1133f7500c0499d3bd3b8389c8bce7ba3ac61';
    'manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py' = '87c055b7d9c651239e359def8bb2e752c032425560c02dc26c300a588a9f0f5f'
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
if (-not (Test-Path -LiteralPath $judge)) { Stop-Merge 'judge file missing' }
$last = (Get-Content -LiteralPath $judge -Encoding UTF8 | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1).Trim()
if ($last -ne 'VERDICT: PASS') { Stop-Merge ('judge verdict: ' + $last) }
$mainBranch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
if ($mainBranch -ne 'codex/master-recovery-expansion') { Stop-Merge ('main branch ' + $mainBranch) }
git -C $repo merge-base --is-ancestor $base HEAD
if ($LASTEXITCODE -ne 0) { Stop-Merge 'base is not an ancestor of main' }
$staged = @(git -C $repo diff --cached --name-only)
if ($staged.Count -ne 0) { Stop-Merge 'main has staged changes' }
$moved = @(git -C $repo diff --name-only $base HEAD)
$unknown = @($moved | Where-Object { -not $_.StartsWith('docs/claude/') })
if ($unknown.Count -ne 0) { Stop-Merge ('main moved with non-docs paths: ' + ($unknown -join ',')) }
$overlap = @($moved | Where-Object { $paths -contains $_ })
if ($overlap.Count -ne 0) { Stop-Merge ('a merged path changed on main since base: ' + ($overlap -join ',')) }
$dirty = @(git -C $repo status --porcelain -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
$mainSettings = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo '.claude\settings.json')).Hash.ToLower()
if ($mainSettings -ne $settingsSha) { Stop-Merge 'main .claude/settings.json is not the merged kiwoom-block version' }
$mainHook = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo '.claude\hooks\kiwoom_order_block.py')).Hash.ToLower()
if ($mainHook -ne $hookSha) { Stop-Merge 'main hook is not the merged kiwoom-block version' }
if ((git -C $wt rev-parse HEAD).Trim() -ne $base) { Stop-Merge 'worktree head is not base' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $paths) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
foreach ($pair in @(@('.claude\settings.json', $settingsSha), @('.claude\hooks\kiwoom_order_block.py', $hookSha))) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $pair[0])).Hash.ToLower()
    if ($h -ne $pair[1]) { Stop-Merge ('worktree file changed: ' + $pair[0]) }
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found on PATH' }

# Tests BEFORE the commit, in the worktree (its settings.json is the merged state). Any failure stops everything.
# Native output is sent to the host so only the exit codes are returned.
function Run-Tests([string]$dir) {
    Push-Location $dir
    $codes = @()
    python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_order_block_hook.py" 2>&1 | Out-Host
    $codes += $LASTEXITCODE
    python -m unittest discover -s manage-us-stock-strategy/tests -p "test_approval_human_check*" 2>&1 | Out-Host
    $codes += $LASTEXITCODE
    python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline*" 2>&1 | Out-Host
    $codes += $LASTEXITCODE
    python manage-us-stock-strategy/scripts/validate_schema_contracts.py 2>&1 | Out-Host
    $codes += $LASTEXITCODE
    Pop-Location
    return $codes
}
$pre = Run-Tests $wt
Write-Output ('PRE_MERGE_TESTS hook=' + $pre[0] + ' approval=' + $pre[1] + ' dev_pipeline=' + $pre[2] + ' schema=' + $pre[3])
if (($pre | Where-Object { $_ -ne 0 }).Count -ne 0) { Stop-Merge 'a test failed before merge (nothing committed)' }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'kiwoom-block-fix3-commit-message.txt'
$msg = "test(safety): kiwoom-block fix3 - tests accept the merged settings, report corrections`n`n" +
       "fix3 (K3 follow-up, manual route; merge by the user's own PowerShell line). After kiwoom-block (c9c0877) three tests pinned`n" +
       "the old settings (deny count 23; current-vs-proposed comparison) and failed. Expectations now use the base 7f98f28 constants`n" +
       "and the 3 named deny lines, so they pass before and after. Report: limits added, count fixed. No hook, settings or deny change.`n" +
       "Judge workspace/outputs/manual-bj/kiwoom-block-fix3/judge-1.txt (PASS, ran 25/126/28).`n`n" +
       "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_015acr5wvrucCQSFMeZU95mK`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge kiwoom-block-fix3 (tests accept merged settings, report corrections; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$post = Run-Tests $repo
Write-Output ('POST_MERGE_TESTS hook=' + $post[0] + ' approval=' + $post[1] + ' dev_pipeline=' + $post[2] + ' schema=' + $post[3])
if (($post | Where-Object { $_ -ne 0 }).Count -ne 0) { Write-Output 'KWB3_WARN a test failed after merge: tell the project thread (nothing was undone)' }
Write-Output 'NEXT: in a NEW Claude Code session ask for the harmless test: echo ust20000 (Bash, then Monitor). Refused = the hook works.'
Write-Output 'KWB3_DONE'
