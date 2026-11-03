# Merge basefail-include (manual route, K3): 19 past output paths in .worktreeinclude and 2 .gitignore lines.
# User approval: card 2026-11-02 19:53:58 KST ("approve both, today"), typed run line 21:44:39 KST and typed
# "include LMT" 21:57:18 KST in the CEO-office execution thread; that day lapsed, the user typed "continue" there on
# 2026-11-03 11:44:42 KST, chose "approve, merge today" on the Judge thread card 2026-11-03 15:40:36 KST and typed
# "review PASS, make the merge script" in the execution thread 15:54:25 KST.
# Builder report: docs/claude/basefail-include-report.md (worktree). Judge: docs/claude/basefail-include-judge-report.md
# in the main checkout (written by the separate Judge session, queued for the docs commit; last line VERDICT: PASS).
# The copied files stay git-ignored and are never committed: only the 4 paths below are staged.
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'basefail-include'
function Stop-Merge([string]$why) { Write-Output ('BASEFAIL_INCLUDE_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
# hnd-check2 (tools/dev_pipeline/README.md): both standard handles must be console handles (GetConsoleMode);
# if the check cannot be built or run it stops (fail closed). Then the person at the keyboard presses Enter once.
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class BasefailIncludeConsoleHandles {
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
    $consoleHandles = [BasefailIncludeConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge basefail-include. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$wt = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$repo = (Resolve-Path -LiteralPath (Join-Path $wt '..\..\..')).Path
$base = (git -C $repo rev-parse c81ac2e6805462b998d5720a1d10a0fa15328b08).Trim()
$branch = 'worktree-basefail-include'
$self = 'docs/claude/basefail-include-merge-2026-11-03.ps1'
$judge = Join-Path $repo 'docs\claude\basefail-include-judge-report.md'
$judgeHash = 'e120f759c5bf8aabb6a61477f557e718ae76b1d38a59642e4d26434192d82a61'
$hashes = @{
    '.gitignore' = '3c8590f7903381e6d693f9afcc5b97ef7af38e10cf14ad9f419372e767e49c97'
    '.worktreeinclude' = '166d4b2502d4844834e6a98a59b6892ebb31a47199f2c60fbc8f5f8faf19f8b1'
    'docs/claude/basefail-include-report.md' = '196be62666773ce812a8ef99a8c9aa85f18a74d160127b9f7b40697f5f56ee71'
}
$paths = @(@($hashes.Keys) + $self | Sort-Object)
$tests = @('test_holding_baseline_observation_audit.py', 'test_mvll_canonical_volume_lineage.py',
           'test_provider_limitation_audit.py', 'test_nbis_v3_shadow_activation.py',
           'test_nbis_v4_kiwoom_price_authority.py', 'test_portfolio_decision_order_intent.py',
           'test_validate_research_packet.py', 'test_portfolio_decision_dashboard.py',
           'test_materialize_kiwoom_session_aware_acceptance_candidate.py')

function Run-Tests([string]$dir, [string]$pattern) {
    Push-Location -LiteralPath $dir
    $out = @(python -B -m unittest discover -s manage-us-stock-strategy/tests -p $pattern 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
    Pop-Location
    $result = $out | Where-Object { $_ -match '^(OK|FAILED)' } | Select-Object -Last 1
    return [pscustomobject]@{ Code = $code; Result = "$result" }
}
function Include-Paths([string[]]$lines) {
    return @($lines | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') } | Select-Object -Skip 2)
}

$kst = [DateTime]::UtcNow.AddHours(9)
if ($kst.ToString('yyyy-MM-dd') -ne '2026-11-03') { Stop-Merge 'approval is for 2026-11-03 KST only' }
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
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-basefail-include' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
$include = Include-Paths (Get-Content -LiteralPath (Join-Path $wt '.worktreeinclude') -Encoding UTF8)
if ($include.Count -ne 19) { Stop-Merge ('include path count ' + $include.Count) }
$trackedInclude = @(git -C $repo ls-files -- $include)
if ($trackedInclude.Count -ne 0) { Stop-Merge ('an include path is tracked on main: ' + ($trackedInclude -join ',')) }
foreach ($rel in $include) {
    $source = Join-Path $repo $rel
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { Stop-Merge ('include file missing on main: ' + $rel) }
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
    $copyHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $rel)).Hash
    if ($sourceHash -ne $copyHash) { Stop-Merge ('include copy differs from main: ' + $rel) }
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
foreach ($pattern in $tests) {
    $r = Run-Tests $wt $pattern
    Write-Output ($pattern + ' ' + $r.Result)
    if ($r.Code -ne 0) { Stop-Merge ($pattern + ' failed before merge') }
}
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'basefail-include-commit-message.txt'
$msg = "fix(worktree): copy past test artifacts into baseline worktrees by exact path (basefail-include)`n`n" +
       "basefail-include (K3, manual route; user card 2026-11-02 19:53:58 KST, typed run 21:44:39 KST and 'include LMT'`n" +
       "21:57:18 KST; after the day lapsed, typed 'continue' 2026-11-03 11:44:42 KST, merge card 15:40:36 KST and typed`n" +
       "'make the merge script' 15:54:25 KST; merge by the user's own PowerShell line).`n" +
       "11 baseline failures in 9 test files read past outputs that exist only on the company PC. .worktreeinclude now`n" +
       "lists those 19 exact paths and .gitignore gains 2 lines, so devpipe copies them into baseline worktrees and the`n" +
       "files stay out of git. 18 are dated 2026-08; the LMT candidate is 2026-09-02, included by the user's decision.`n" +
       "Tests, devpipe code, policy and state are unchanged.`n" +
       "Builder docs/claude/basefail-include-report.md, Judge docs/claude/basefail-include-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
$committed = @(git -C $wt show --name-only --format= HEAD | Where-Object { $_ } | Sort-Object)
if (($committed -join '|') -ne ($paths -join '|')) { Stop-Merge ('commit paths: ' + ($committed -join ',')) }
git -C $repo merge --no-ff -q -m "Merge basefail-include (past test artifacts by exact path in .worktreeinclude; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$after = Include-Paths (git -C $repo show HEAD:.worktreeinclude)
$ignored = @(git -C $repo check-ignore -- $after)
$tracked = @(git -C $repo ls-files -- $after)
$left = @(git -C $repo status --porcelain -- 'workspace/outputs/lmt-instrument-registry-candidate-prep' 'workspace/outputs/manual-portfolio-analysis')
if (($after.Count -ne 19) -or ($ignored.Count -ne 19) -or ($tracked.Count -ne 0) -or ($left.Count -ne 0)) {
    Write-Output ('BASEFAIL_INCLUDE_CHECK_AFTER_MERGE include=' + $after.Count + ' ignored=' + $ignored.Count +
                  ' tracked=' + $tracked.Count + ' status=' + $left.Count)
    exit 3
}
Write-Output 'MAIN_INCLUDE_OK include=19 ignored=19 tracked=0'
Write-Output 'BASEFAIL_INCLUDE_DONE'
