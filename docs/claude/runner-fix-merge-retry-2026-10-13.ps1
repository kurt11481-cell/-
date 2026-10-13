# runner-fix merge retry + one verification run of today's auto-core tasks (Cowork, 2026-10-13). ASCII only.
# Why: the first dev-merge (00:30Z) rebased runner-fix onto 1e0b511 and then failed with WinError 32 while
# removing the shared temp worktree _base-1e0b511c that dev-run cmp-fix was using. The rebase was left in place
# (worktree-runner-fix = 1066005 on 1e0b511). This script:
#   1. waits until no dev-run holds workspace\outputs\dev-runs\_lock (max 60 min),
#   2. undoes the half-done merge exactly like devpipe undo(): reset --keep to the first commit 8fee428,
#      reset --soft to base 6012f2f, unstage (changes stay in the worktree),
#   3. runs .\tools\dev-merge.ps1 runner-fix -ApproveAuthority (user decision 2026-10-13 08:58),
#   4. only if merged: starts the Windows task InvestmentV2-AutoCore (daily), waits, then
#      InvestmentV2-AutoCoreDecide (decide), and prints the runner log lines and LATEST statuses.
# No order, no state write (compare mode), no policy change. Read-only Kiwoom inside the tasks.

$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\runner-fix'
$lock = Join-Path $repo 'workspace\outputs\dev-runs\_lock'
$base = '6012f2f8ffd622da2f21e6fd808c83fcb147ee92'
$first = '8fee42848498f2692cf48d6a096b9a028e47dd17'
$rebased = '10660055c391d609a91ab6f04b30031c41eb9414'
$paths = @('docs/claude/runner-fix-report.md', 'manage-us-stock-strategy/scripts/run_auto_core.ps1',
           'manage-us-stock-strategy/tests/test_auto_core_runner.py')

# 1. wait for the dev-run lock
$waited = 0
while (Test-Path -LiteralPath $lock) {
    if ($waited -ge 3600) { Write-Output 'RETRY_STOP dev-run lock still held after 60 min'; exit 2 }
    if ($waited % 300 -eq 0) { Write-Output ('WAIT dev-run lock held, waited ' + $waited + 's') }
    Start-Sleep -Seconds 30
    $waited += 30
}
Write-Output 'LOCK_FREE'

# 2. undo the half-done merge
$head = (git -C $wt rev-parse HEAD).Trim()
if ($head -eq $rebased) {
    git -C $wt reset -q --keep $first
    if ($LASTEXITCODE -ne 0) { Write-Output 'RETRY_STOP reset_keep_failed'; exit 2 }
    git -C $wt reset -q --soft $base
    git -C $wt reset -q
    $head = (git -C $wt rev-parse HEAD).Trim()
} elseif ($head -ne $base) {
    Write-Output ('RETRY_STOP unexpected_worktree_head ' + $head); exit 2
}
if ($head -ne $base) { Write-Output ('RETRY_STOP head_not_base ' + $head); exit 2 }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
$staged = @(git -C $wt diff --cached --name-only)
if (($status -join '|') -ne (($paths | Sort-Object) -join '|') -or $staged.Count -ne 0) {
    Write-Output ('RETRY_STOP worktree_paths ' + ($status -join ',') + ' staged=' + $staged.Count); exit 2
}
Write-Output 'RESTORED head=base, 3 changed paths, nothing staged'

# 3. merge
& (Join-Path $repo 'tools\dev-merge.ps1') runner-fix -ApproveAuthority
$mergeCode = $LASTEXITCODE
if ($mergeCode -ne 0) { Write-Output ('RETRY_STOP dev-merge exit ' + $mergeCode); exit 2 }

# 4. one verification run through the real scheduled tasks
$logs = Join-Path $repo 'workspace\outputs\auto-core\logs'
foreach ($task in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide')) {
    $before = Get-Date
    Start-ScheduledTask -TaskName $task
    Start-Sleep -Seconds 10
    $t = 0
    while ((Get-ScheduledTask -TaskName $task).State -eq 'Running' -and $t -lt 2700) { Start-Sleep -Seconds 15; $t += 15 }
    $info = Get-ScheduledTaskInfo -TaskName $task
    Write-Output ('TASK ' + $task + ' state=' + (Get-ScheduledTask -TaskName $task).State + ' last_result=' + $info.LastTaskResult)
    $log = Get-ChildItem -LiteralPath $logs -Filter 'auto-core-*.log' | Where-Object { $_.LastWriteTime -ge $before } |
        Sort-Object LastWriteTime | Select-Object -Last 1
    if ($null -ne $log) { Get-Content -LiteralPath $log.FullName | Where-Object { $_ -like 'RUNNER_*' } | ForEach-Object { Write-Output ('  ' + $_) } }
    else { Write-Output '  NO_NEW_LOG' }
}
$ac = Join-Path $repo 'workspace\outputs\auto-core'
foreach ($f in @('LATEST.json', 'LATEST_DECISION.json')) {
    $p = Join-Path $ac $f
    if (Test-Path -LiteralPath $p) {
        $j = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Output ($f + ' status=' + $j.status + ' generated_at=' + $j.generated_at)
    }
}
Write-Output 'RUNNER_FIX_RETRY_DONE'
