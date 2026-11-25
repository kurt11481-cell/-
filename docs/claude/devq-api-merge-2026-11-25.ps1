# Merge devq-api (manual route, K3): dev-queue Judge may run on API credits via the Agent SDK when switched on;
# merged SWITCHED OFF (docs/claude/devq-api-route.json judge_enabled false). Builder unchanged.
# User approval: card cmsg_0137MRzn9nuDvvQmVxm6WeX9YEvrpbLTSAKYXCJHcm1KZm option A 2026-11-25 09:32:27 KST
# (proposal devq-api-1125, record docs/claude/devq-api-proposal-2026-11-25.md section 7) + typed run 2026-11-25 09:54 KST.
# Builder report: docs/claude/devq-api-report.md (in the worktree, merged with this commit).
# Judge: docs/claude/devq-api-judge-report.md (last non-empty line must be VERDICT: PASS).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no API call, no key read, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('DEVQ_API_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class DevqApiConsoleHandles {
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
    $consoleHandles = [DevqApiConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge devq-api (switched off). Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$kst = [DateTime]::UtcNow.AddHours(9)
$approvedKst = '2026-11-25'
if ($kst.ToString('yyyy-MM-dd') -ne $approvedKst) { Stop-Merge ('merge approved only on ' + $approvedKst + ' KST') }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\magical-chatterjee-dc076d'
$base = (git -C $repo rev-parse 113727c5d66bb4d47c081d33e3a5af18121171ed).Trim()
$branch = 'worktree-devq-api'
$judge = Join-Path $repo 'docs\claude\devq-api-judge-report.md'
$judgeHash = '09b51c1375f058e2eb3d0706632fbe5fa460e83a5c704404b9f1ebd89ea10fd7'
$hashes = @{
    'docs/claude/devq-api-report.md' = 'cae93b7cb3fd5d667f693b8d7f5a8a63b4f18cd1e991a545202b07c09cac04d4'
    'docs/claude/devq-api-route.json' = 'ff97a24d2259fabf21705a207c3fa167022507979f8452e5d1dea0886ba5b54a'
    'manage-us-stock-strategy/tests/test_dev_pipeline_api_route.py' = '1a63188bd8e42ff9ebcc1689596b3f5d89c5b53663669f2a8a2cd191c29f2ec7'
    'tools/dev-run.ps1' = '3d77cd0b890becf18d05428d4b9e1a54b333e5336ae787e314070af20f673b13'
    'tools/dev_pipeline/README.md' = '1e6c4f64308bf390f9072c8721999663569ef4bbb4f78f9d84a3c295ba86e3cc'
    'tools/dev_pipeline/devpipe.py' = 'cbb2e1d4b6f11d7b9ce0202578b181959dab53a1fcfc09dd68a04fd2ee172281'
    'tools/dev_pipeline/requirements-sdk.txt' = '83fef5b2e8fd30cf93e92ba3b5efabae7c5c51209bff15682b5ee90540036357'
    'tools/dev_pipeline/sdk_agent.py' = '28fc309fd7e7b2f357b3817ecbc005b5d98d73270bf4f6e9c951c03aaad25c42'
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
# llm-pdfcmp (dev queue, READY_TO_MERGE) must be merged first so its dev-merge does not hit STOP_BASE_MOVED.
$pdfcmp = Join-Path $repo 'workspace\outputs\dev-runs\llm-pdfcmp'
if ((Test-Path -LiteralPath (Join-Path $pdfcmp 'result.json')) -and `
    (-not (Test-Path -LiteralPath (Join-Path $pdfcmp 'commit-message.txt')))) {
    Stop-Merge 'merge llm-pdfcmp first: .\tools\dev-merge.ps1 llm-pdfcmp'
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
$dirty = @(git -C $repo status --porcelain --untracked-files=all -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
if ((git -C $wt rev-parse HEAD).Trim() -ne $base) { Stop-Merge 'worktree head is not base' }
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-devq-api' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $paths) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
$routeJson = Get-Content -LiteralPath (Join-Path $wt 'docs\claude\devq-api-route.json') -Raw | ConvertFrom-Json
if ($routeJson.judge_enabled -ne $false) { Stop-Merge 'devq-api-route.json is not switched off' }
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
Push-Location $wt
python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline_api_route.py" 2>&1 | Select-Object -Last 3
$t1 = $LASTEXITCODE
python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py" 2>&1 | Select-Object -Last 3
$t2 = $LASTEXITCODE
Pop-Location
if ($t1 -ne 0) { Stop-Merge 'test_dev_pipeline_api_route failed before merge' }
if ($t2 -ne 0) { Stop-Merge 'test_dev_pipeline failed before merge' }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'devq-api-commit-message.txt'
$msg = "feat(dev-pipeline): optional API-credit route for the dev-queue Judge via Agent SDK, merged switched off (devq-api)`n`n" +
       "devq-api (K3, manual route; user card 2026-11-25 09:32:27 KST option A 'Judge only', typed run 2026-11-25 09:54 KST`n" +
       "in the CEO-office project thread; merge by the user's own PowerShell line).`n" +
       "devpipe: pick-route, api-spend-record, route-fallback, judge_routes in result.json, test_env drops key names.`n" +
       "dev-run.ps1: clears key vars at start, picks the Judge route, falls back once to the subscription CLI on pre-work failure.`n" +
       "New sdk_agent.py and requirements-sdk.txt. Builder command unchanged. docs/claude/devq-api-route.json judge_enabled false.`n" +
       "Builder docs/claude/devq-api-report.md, Judge docs/claude/devq-api-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_01KuMGKgx3ZEmXteF89BusCr`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge devq-api (dev-queue Judge API route, switched off; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())
Write-Output 'DEVQ_API_DONE'
