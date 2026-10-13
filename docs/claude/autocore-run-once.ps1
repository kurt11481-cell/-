# Run the auto-core once now through its real Windows tasks: InvestmentV2-AutoCore (daily), wait, then
# InvestmentV2-AutoCoreDecide (decide). Cowork, 2026-10-13. ASCII only. Reusable for a same-day rerun.
# Read-only Kiwoom inside the tasks; in compare mode no state, journal or order is written.
# Refuses to start while a dev-run holds workspace\outputs\dev-runs\_lock.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if (Test-Path -LiteralPath (Join-Path $repo 'workspace\outputs\dev-runs\_lock')) { Write-Output 'RUNONCE_STOP dev-run lock held'; exit 2 }
$logs = Join-Path $repo 'workspace\outputs\auto-core\logs'
foreach ($task in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide')) {
    if ((Get-ScheduledTask -TaskName $task).State -eq 'Running') { Write-Output ('RUNONCE_STOP ' + $task + ' already running'); exit 2 }
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
Write-Output 'RUNONCE_DONE'
