# Merge gitattr-bytes (manual route, K3): raw-byte authority files skip CRLF conversion in worktrees.
# User approval: card 2026-11-02 18:54:38 KST ("approve, today"), typed run line 18:59:43 KST and typed
# "proceed with 14" 19:12:19 KST in the CEO-office execution thread
# (record: docs/claude/gitattr-bytes-proposal-2026-11-02.md, last section).
# Builder report: docs/claude/gitattr-bytes-report.md. Judge: docs/claude/gitattr-bytes-judge-report.md
# (last line must be VERDICT: PASS). Both, and this script, go in the worktree commit: the execution
# session cannot write to the main checkout.
# Two test_v2_6_7 failures are expected and unrelated to this change (Acceptance implementation hashes).
# The merge itself is the user's one line in their own interactive Windows PowerShell.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
$Id = 'gitattr-bytes'
function Stop-Merge([string]$why) { Write-Output ('GITATTR_BYTES_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
# hnd-check2 (tools/dev_pipeline/README.md): both standard handles must be console handles (GetConsoleMode);
# if the check cannot be built or run it stops (fail closed). Then the person at the keyboard presses Enter once.
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class GitattrBytesConsoleHandles {
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
    $consoleHandles = [GitattrBytesConsoleHandles]::Both()
} catch {
    $consoleHandles = $false
}
if ($consoleHandles -ne $true) { Stop-Merge 'not an interactive console (handles)' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge gitattr-bytes. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch {
    $entered = $null
}
if ($null -eq $entered) { Stop-Merge 'not an interactive console (input)' }

$wt = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$repo = (Resolve-Path -LiteralPath (Join-Path $wt '..\..\..')).Path
$base = (git -C $repo rev-parse 6aea772ccb456d1f3bfd560cd4507d6681d00200).Trim()
$branch = 'worktree-gitattr-bytes'
$self = 'docs/claude/gitattr-bytes-merge-2026-11-02.ps1'
$judge = Join-Path $wt 'docs\claude\gitattr-bytes-judge-report.md'
$hashes = @{
    '.gitattributes' = '11e9f729b81218bb8ddb6a47c6bdd2184b37e4810a6eb4a8ff9f6b7f7793f18c'
    'docs/claude/gitattr-bytes-judge-report.md' = '0d669ba2f55e5d193f2d384aa331cdbf411c5b63088ad0b26026d391155ec6d0'
    'docs/claude/gitattr-bytes-report.md' = 'bb3f078c63cd9f94b76e193b6341a5e1a650c8e130cac0ee7da3cc7c360f251f'
    'manage-us-stock-strategy/tests/test_gitattributes_authority_bytes.py' = '9e96a18c3b68e9cc1a1351990b43769b8afc9056c0edbbc8637dc071b1a35966'
}
$paths = @(@($hashes.Keys) + $self | Sort-Object)
$scope = @('workspace/research/provider-evidence', 'workspace/instrument-identity-authority',
           'workspace/policies/instrument_identity_activation.json', 'workspace/policies/session_calendar_activation.json')

function Run-Tests([string]$dir, [string]$pattern) {
    Push-Location -LiteralPath $dir
    $out = @(python -B -m unittest discover -s manage-us-stock-strategy/tests -p $pattern 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
    Pop-Location
    $result = $out | Where-Object { $_ -match '^(OK|FAILED)' } | Select-Object -Last 1
    return [pscustomobject]@{ Code = $code; Result = "$result" }
}

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
if ((git -C $wt rev-parse --abbrev-ref HEAD).Trim() -ne $branch) { Stop-Merge 'worktree branch is not worktree-gitattr-bytes' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($paths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $hashes.Keys) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found' }
foreach ($pattern in @('test_gitattributes_authority_bytes.py', 'test_instrument_identity_authority.py',
                       'test_materialize_instrument_identity_artifact.py')) {
    $r = Run-Tests $wt $pattern
    Write-Output ($pattern + ' ' + $r.Result)
    if ($r.Code -ne 0) { Stop-Merge ($pattern + ' failed before merge') }
}
$r = Run-Tests $wt 'test_v2_6_7_session_aware_kiwoom_priority.py'
Write-Output ('test_v2_6_7 ' + $r.Result + ' (2 failures expected)')
if ($r.Result -ne 'FAILED (failures=2)') { Stop-Merge ('test_v2_6_7 result changed: ' + $r.Result) }
Write-Output 'CHECKS_OK'

$msgFile = Join-Path $env:TEMP 'gitattr-bytes-commit-message.txt'
$msg = "fix(gitattributes): keep raw-byte authority files out of CRLF conversion (gitattr-bytes)`n`n" +
       "gitattr-bytes (K3, manual route; user card 2026-11-02 18:54:38 KST, typed run 18:59:43 KST and typed`n" +
       "'proceed with 14' 19:12:19 KST in the CEO-office execution thread; merge by the user's own PowerShell line).`n" +
       "core.autocrlf=true gave worktrees CRLF copies of files read over raw bytes, so 16 authority tests failed there.`n" +
       "Adds -text for Kiwoom provider evidence, instrument identity authority and two activation files, and keeps 7`n" +
       "past CRLF evidence files on text so the main checkout does not change. 14 of the 16 tests pass again; the other 2`n" +
       "fail on Acceptance implementation hashes changed after 2026-10-07, a separate cause left out of scope.`n" +
       "Builder docs/claude/gitattr-bytes-report.md, Judge docs/claude/gitattr-bytes-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge gitattr-bytes (raw-byte authority files skip CRLF conversion; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

$after = @(git -C $repo status --porcelain -- $scope)
if ($after.Count -ne 0) {
    Write-Output ('GITATTR_BYTES_CHECK_AFTER_MERGE main scope changed: ' + ($after -join ' | '))
    exit 3
}
Write-Output 'MAIN_SCOPE_UNCHANGED'
$r = Run-Tests $repo 'test_v2_6_7_session_aware_kiwoom_priority.py'
Write-Output ('MAIN_TEST_V2_6_7 ' + $r.Result)
Write-Output 'GITATTR_BYTES_DONE'
