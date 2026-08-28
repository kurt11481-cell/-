param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Install", "Disable", "Enable", "Start", "Stop", "Status", "Remove")]
    [string]$Operation,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^StockStrategy-TESTONLY-[A-Za-z0-9-]+$")]
    [string]$TaskName,
    [string]$PythonPath,
    [string]$ScriptPath,
    [string]$ConfigPath,
    [datetime]$AtLocal,
    [string]$WorkingDirectory,
    [ValidateSet("Fire", "Watchdog", "RuntimePreflight")]
    [string]$ActionMode = "Fire"
)

$ErrorActionPreference = "Stop"
$taskPath = "\CodexTestOnly\"

function Get-TestOnlyTask {
    Get-ScheduledTask -TaskPath $taskPath -TaskName $TaskName -ErrorAction Stop
}

if ($Operation -eq "Install") {
    foreach ($required in @($PythonPath, $ScriptPath, $ConfigPath, $WorkingDirectory)) {
        if ([string]::IsNullOrWhiteSpace($required)) {
            throw "Install requires PythonPath, ScriptPath, ConfigPath, and WorkingDirectory"
        }
    }
    if ($AtLocal -le (Get-Date)) {
        throw "TEST_ONLY task time must be in the future"
    }
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        throw "Python executable not found"
    }
    if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
        throw "TEST_ONLY script not found"
    }
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "TEST_ONLY config not found"
    }
    if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) {
        throw "Working directory not found"
    }

    $subcommand = if ($ActionMode -eq "Watchdog") { "os-watchdog" } elseif ($ActionMode -eq "RuntimePreflight") { "run" } else { "os-fire" }
    $arguments = '"' + $ScriptPath + '" ' + $subcommand + ' --config "' + $ConfigPath + '"'
    $action = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument $arguments `
        -WorkingDirectory $WorkingDirectory
    $trigger = New-ScheduledTaskTrigger -Once -At $AtLocal
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable:$false `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Limited
    Register-ScheduledTask `
        -TaskPath $taskPath `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "TEST_ONLY stock-strategy scheduler diagnostic; never production or maturity eligible" `
        -Force | Out-Null
}
elseif ($Operation -eq "Disable") {
    Get-TestOnlyTask | Disable-ScheduledTask | Out-Null
}
elseif ($Operation -eq "Enable") {
    Get-TestOnlyTask | Enable-ScheduledTask | Out-Null
}
elseif ($Operation -eq "Start") {
    Start-ScheduledTask -TaskPath $taskPath -TaskName $TaskName
}
elseif ($Operation -eq "Stop") {
    Stop-ScheduledTask -TaskPath $taskPath -TaskName $TaskName -ErrorAction SilentlyContinue
}
elseif ($Operation -eq "Remove") {
    Unregister-ScheduledTask -TaskPath $taskPath -TaskName $TaskName -Confirm:$false
}

if ($Operation -ne "Remove") {
    $task = Get-TestOnlyTask
    $info = Get-ScheduledTaskInfo -TaskPath $taskPath -TaskName $TaskName
    $taskXml = Export-ScheduledTask -TaskPath $taskPath -TaskName $TaskName
    $taskXmlHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::Unicode.GetBytes($taskXml)))
    $lastRunUtc = if ($null -eq $info.LastRunTime -or $info.LastRunTime -eq [datetime]::MinValue) { $null } else { $info.LastRunTime.ToUniversalTime().ToString("o") }
    $nextRunUtc = if ($null -eq $info.NextRunTime -or $info.NextRunTime -eq [datetime]::MinValue) { $null } else { $info.NextRunTime.ToUniversalTime().ToString("o") }
    [pscustomobject]@{
        task_path = $task.TaskPath
        task_name = $task.TaskName
        state = [string]$task.State
        enabled = ([string]$task.State -ne "Disabled")
        last_run_time = $lastRunUtc
        next_run_time = $nextRunUtc
        last_task_result = $info.LastTaskResult
        execution_identity = $task.Principal.UserId
        logon_type = [string]$task.Principal.LogonType
        run_level = [string]$task.Principal.RunLevel
        start_when_available = $task.Settings.StartWhenAvailable
        multiple_instances = [string]$task.Settings.MultipleInstances
        executable = $task.Actions[0].Execute
        arguments = $task.Actions[0].Arguments
        working_directory = $task.Actions[0].WorkingDirectory
        task_xml_sha256 = $taskXmlHash
        test_only = $true
        maturity_eligible = $false
        production_scheduler = $false
    } | ConvertTo-Json -Depth 4
}
else {
    [pscustomobject]@{
        task_path = $taskPath
        task_name = $TaskName
        removed = $true
        test_only = $true
        maturity_eligible = $false
        production_scheduler = $false
    } | ConvertTo-Json
}
