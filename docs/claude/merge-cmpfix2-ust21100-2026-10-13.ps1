# Merge cmp-fix2 then ust21100-fix when both dev-runs have finished, then one verification run of the auto-core
# tasks (Cowork, 2026-10-13). ASCII only. User decisions (t2-equity-cash option 2 incl. the compare fix queue,
# ust21100-fix approved 10:33 KST) are recorded in docs/claude/redesign-t2-merge-decision-2026-10-12.md.
# Rule from today's incident: never merge while a dev-run holds workspace\outputs\dev-runs\_lock.
# Waits up to 150 minutes. Stops at the first problem and prints one MERGE2_STOP line.
# No order, no policy or state write (compare mode). Read-only Kiwoom inside the tasks.

$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$runs = Join-Path $repo 'workspace\outputs\dev-runs'
$lock = Join-Path $runs '_lock'
$queue = Join-Path $repo 'docs\claude\_dev-queue'
$ids = @('cmp-fix2', 'ust21100-fix')

function Get-RunStatus([string]$id) {
    $p = Join-Path (Join-Path $runs $id) 'result.json'
    if (-not (Test-Path -LiteralPath $p)) { return $null }
    try { return (Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}

$waited = 0
while ($true) {
    $done = @($ids | Where-Object { $null -ne (Get-RunStatus $_) })
    $queued = @(Get-ChildItem -LiteralPath $queue -Filter '*.txt' -ErrorAction SilentlyContinue)
    if ($done.Count -eq $ids.Count -and -not (Test-Path -LiteralPath $lock) -and $queued.Count -eq 0) { break }
    if ($waited -ge 9000) { Write-Output 'MERGE2_STOP waited 150 min for both runs to finish'; exit 2 }
    if ($waited % 600 -eq 0) { Write-Output ('WAIT finished=' + ($done -join ',') + ' lock=' + (Test-Path -LiteralPath $lock) + ' queued=' + $queued.Count + ' waited=' + $waited + 's') }
    Start-Sleep -Seconds 30
    $waited += 30
}

foreach ($id in $ids) {
    $r = Get-RunStatus $id
    if ($r.merged_at) { Write-Output ('SKIP ' + $id + ' already merged'); continue }
    if ($r.status -ne 'NEEDS_APPROVAL') { Write-Output ('MERGE2_STOP ' + $id + ' status=' + $r.status + ' (not merged, Cowork review)'); exit 2 }
    if (Test-Path -LiteralPath $lock) { Write-Output ('MERGE2_STOP lock appeared before ' + $id); exit 2 }
    & (Join-Path $repo 'tools\dev-merge.ps1') $id -ApproveAuthority
    if ($LASTEXITCODE -ne 0) { Write-Output ('MERGE2_STOP dev-merge ' + $id + ' exit ' + $LASTEXITCODE); exit 2 }
}

$logs = Join-Path $repo 'workspace\outputs\auto-core\logs'
foreach ($task in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide')) {
    $before = Get-Date
    Start-ScheduledTask -TaskName $task
    Start-Sleep -Seconds 10
    $t = 0
    while ((Get-ScheduledTask -TaskName $task).State -eq 'Running' -and $t -lt 2700) { Start-Sleep -Seconds 15; $t += 15 }
    Write-Output ('TASK ' + $task + ' last_result=' + (Get-ScheduledTaskInfo -TaskName $task).LastTaskResult)
    $log = Get-ChildItem -LiteralPath $logs -Filter 'auto-core-*.log' | Where-Object { $_.LastWriteTime -ge $before } |
        Sort-Object LastWriteTime | Select-Object -Last 1
    if ($null -ne $log) { Get-Content -LiteralPath $log.FullName | ForEach-Object { Write-Output ('  ' + $_) } } else { Write-Output '  NO_NEW_LOG' }
}
Write-Output 'MERGE2_DONE'
