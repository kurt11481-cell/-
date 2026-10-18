[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$PythonPath = ""
)

# f-evo-loop step 1: Windows task entry of the weekly journal scoring (InvestmentV2-JournalScore, Sunday 09:20 KST).
# Runs score_decision_journal.py --learning once. The scorer reads only and writes its own report folder under
# workspace\outputs\journal-scores; this runner writes only logs\<UTC time>.log and WEEKLY_LATEST.json there
# (through a temp file). No broker call and no network call exist on this path. No retry: next week's run is the retry.
# WEEKLY_LATEST.json names the latest report written after the start that has a learning block. status FAIL when
# the Python exit code is not 0, no such report exists, the report is not readable JSON, or its learning block failed
# as a whole (an errors reason starting with LEARNING_FAILED; learning_failed true), or the runner itself threw after
# RUNNER_START (reason RUNNER_EXCEPTION; log line RUNNER_FAIL RUNNER_EXCEPTION type=... message=...; exit_code is -1
# when Python had not finished, so a missing value never reads as success; if the status write fails too, only the log line remains).
# Exit code = the Python exit code; 1 when no report with a learning block was found; 1 also when the status is FAIL
# but Python exited 0 (LEARNING_FAILED), so the task scheduler's last result shows every FAIL (the exit_code field
# stays the Python exit code); 3 when the runner cannot start; 4 on an unexpected runner exception.

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$scriptPath = Join-Path $resolvedRepository "manage-us-stock-strategy\scripts\score_decision_journal.py"
$scoresRoot = Join-Path $resolvedRepository "workspace\outputs\journal-scores"
$logDirectory = Join-Path $scoresRoot "logs"
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$startedUtc = [DateTime]::UtcNow
$stamp = $startedUtc.ToString("yyyyMMddTHHmmssZ")
$logPath = Join-Path $logDirectory ($stamp + ".log")
$latestPath = Join-Path $scoresRoot "WEEKLY_LATEST.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-RunnerLine {
    param([string]$Text)
    Add-Content -LiteralPath $logPath -Value $Text -Encoding ASCII
}

function Write-WeeklyLatest {
    param([int]$ExitCode, [string]$Status, [string]$Reason, $ReportPath, [bool]$LearningPresent, [bool]$LearningFailed)
    $document = [ordered]@{
        schema = "journal-score-weekly/v1"
        started_at = $startedUtc.ToString("o")
        finished_at = [DateTime]::UtcNow.ToString("o")
        exit_code = $ExitCode
        status = $Status
        reason = $Reason
        report_path = $ReportPath
        learning_present = $LearningPresent
        learning_failed = $LearningFailed
        order_authority = $false
    }
    $temporary = $latestPath + ".tmp"
    [System.IO.File]::WriteAllText($temporary, ($document | ConvertTo-Json -Depth 3), $utf8NoBom)
    Move-Item -LiteralPath $temporary -Destination $latestPath -Force
}

# Large reports: the .NET serializer with no length limit when it is available, ConvertFrom-Json otherwise.
$serializer = $null
try {
    Add-Type -AssemblyName System.Web.Extensions -ErrorAction Stop
    $serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
    $serializer.MaxJsonLength = [int]::MaxValue
    $serializer.RecursionLimit = 1024
} catch {
    $serializer = $null
}

function Read-JsonDocument {
    param([string]$Path)
    $text = [System.IO.File]::ReadAllText($Path, $utf8NoBom)
    if ($null -ne $serializer) { return ,$serializer.DeserializeObject($text) }
    return ,($text | ConvertFrom-Json)
}

function Get-JsonValue {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) {
        if (-not ($Object.Keys -ccontains $Name)) { return $null }
        $value = $Object[$Name]
    } else {
        $property = $Object.PSObject.Properties[$Name]
        if ($null -eq $property) { return $null }
        $value = $property.Value
    }
    if ($null -eq $value) { return $null }
    return ,$value
}

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL SCORER_SCRIPT_NOT_FOUND"
    Write-WeeklyLatest -ExitCode 3 -Status "FAIL" -Reason "SCORER_SCRIPT_NOT_FOUND" -ReportPath $null -LearningPresent $false -LearningFailed $false
    exit 3
}
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $candidates = @(
        (Join-Path $resolvedRepository ".venv\Scripts\python.exe"),
        (Join-Path $resolvedRepository "venv\Scripts\python.exe")
    )
    $PythonPath = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) { $pythonCommand = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $pythonCommand) { $PythonPath = $pythonCommand.Source }
    }
}
if ([string]::IsNullOrWhiteSpace($PythonPath) -or -not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    Write-RunnerLine "RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND"
    Write-WeeklyLatest -ExitCode 3 -Status "FAIL" -Reason "PYTHON_RUNTIME_NOT_FOUND" -ReportPath $null -LearningPresent $false -LearningFailed $false
    exit 3
}
$timezoneId = try { (Get-TimeZone -ErrorAction Stop).Id } catch { "NOT_VERIFIED" }
Write-RunnerLine ("RUNNER_START utc=" + $stamp + " timezone=" + $timezoneId)

# From here on any unexpected exception ends in the catch block at the bottom (exit 4). -1 marks "Python did not finish".
$exitCode = -1
$reportPath = $null
$learningPresent = $false
$learningFailed = $false
try {
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    Set-Location -LiteralPath $resolvedRepository
    $commandLine = '"' + $PythonPath + '" "' + $scriptPath + '" --learning >> "' + $logPath + '" 2>&1'
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        cmd /c $commandLine
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    # The report: the latest <UTC time> folder created after the start whose journal-scores.json has a learning block
    # (a report the auto-core wrote in the meantime has none and is not picked).
    $unreadable = $false
    $folders = @(Get-ChildItem -LiteralPath $scoresRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^[0-9]{8}T[0-9]{6}Z(-[0-9]+)?$' -and $_.Name.Substring(0, 16) -ge $stamp } |
        Sort-Object -Descending -Property @{ Expression = { $_.Name.Substring(0, 16) } },
            @{ Expression = { if ($_.Name.Length -gt 17) { [int]$_.Name.Substring(17) } else { 0 } } })
    foreach ($folder in $folders) {
        $candidate = Join-Path $folder.FullName "journal-scores.json"
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            $report = Read-JsonDocument -Path $candidate
        } catch {
            $unreadable = $true
            continue
        }
        $learning = Get-JsonValue -Object $report -Name "learning"
        if ($null -eq $learning) { continue }
        $reportPath = $candidate
        $learningPresent = $true
        # Assigned first: @(function call) would wrap the returned array once more.
        $learningErrors = Get-JsonValue -Object $learning -Name "errors"
        foreach ($item in @($learningErrors)) {
            $reason = [string](Get-JsonValue -Object $item -Name "reason")
            if ($reason.StartsWith("LEARNING_FAILED")) { $learningFailed = $true }
        }
        break
    }

    $status = "OK"
    $why = $null
    $finalExit = $exitCode
    if ($null -eq $reportPath) {
        $status = "FAIL"
        $why = if ($unreadable) { "REPORT_NOT_JSON" } else { "NO_LEARNING_REPORT" }
        $finalExit = 1
    } elseif ($learningFailed) {
        $status = "FAIL"
        $why = "LEARNING_FAILED"
    } elseif ($exitCode -ne 0) {
        $status = "FAIL"
        $why = "SCORER_EXIT"
    }
    Write-WeeklyLatest -ExitCode $exitCode -Status $status -Reason $why -ReportPath $reportPath -LearningPresent $learningPresent -LearningFailed $learningFailed
    # A FAIL status never ends with process exit 0, so the task scheduler's last result shows it.
    if ($status -eq "FAIL" -and $finalExit -eq 0) { $finalExit = 1 }
    Write-RunnerLine ("RUNNER_END exit=" + $finalExit + " status=" + $status)
    exit $finalExit
} catch {
    # Each step is guarded alone: a failing status write must not hide the log line.
    $failureLine = "RUNNER_FAIL RUNNER_EXCEPTION"
    try {
        $failureType = $_.Exception.GetType().FullName
        $failureMessage = ([string]$_.Exception.Message -replace "[\r\n]+", " ") -replace "[^\x20-\x7E]", "?"
        if ($failureMessage.Length -gt 300) { $failureMessage = $failureMessage.Substring(0, 300) }
        $failureLine = "RUNNER_FAIL RUNNER_EXCEPTION type=" + $failureType + " message=" + $failureMessage
    } catch {
    }
    try { Write-RunnerLine $failureLine } catch { }
    try {
        Write-WeeklyLatest -ExitCode $exitCode -Status "FAIL" -Reason "RUNNER_EXCEPTION" -ReportPath $reportPath -LearningPresent $learningPresent -LearningFailed $learningFailed
    } catch {
    }
    exit 4
}
