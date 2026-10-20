# Offsite backup (InvestmentV2-OffsiteBackup, daily 23:50): A) pushes the current branch to origin, B) writes a dated
# zip of the untracked record files to the OneDrive folder, then writes one result file read by the 05:50 host status check.
# Does: one push of the current branch to the same branch name on origin (never main, never a detached HEAD), a zip
# copy outside the repository, deletion of old YYYY-MM-DD.zip files in the backup folder only.
# Does not: no broker call, no web call, no forced push, does not commit, does not modify tracked files, does not
# change git settings, does not touch the task scheduler. The only write inside the repository is the result file
# (default workspace\outputs\backup\LATEST.json), written to a .tmp file first and then swapped in.
# Every failure is recorded in the result file (status WARN); the exit code is always 0.
# Consumer: host_status.ps1 check backup_recent (workspace\outputs\host-status\LATEST.json, 05:50).
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$BackupRoot = "",
    [string]$OutputPath = "",
    [ValidateRange(1, 3650)][int]$KeepCount = 30,
    [switch]$SkipPush,
    [switch]$SkipCopy,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Same rule as SECRET_NAME_RE in tools/dev_pipeline/devpipe.py, applied to the file name (last path part).
$secretNamePattern = '^(\.env.*|.*\.(pem|key|p12|pfx|ppk)|credentials.*\.json|secrets.*\.json|tokens?\.json|id_(rsa|dsa|ecdsa|ed25519).*)$'
$dailyZipPattern = '^\d{4}-\d{2}-\d{2}\.zip$'
$branchNamePattern = '^[A-Za-z0-9._/-]+$'
# Folders under workspace\outputs copied whole. Left out on purpose: official-event-intake (large, can be fetched
# again from the official sources), activation, dev-runs, and the private inputs folder (may hold account data).
$outputFolders = @("auto-core", "regular-session-closes", "research-records", "journal-scores", "decisions",
    "reconciliation", "exposure-review", "holding-cards", "status", "host-status")
$stateExcludedPrefixes = @("stock-strategy-system/.tmp_skill_validation/", "stock-strategy-system/skill-staging/")

function ConvertTo-OneLine {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    $line = ($Text -replace "[\r\n]+", " ").Trim()
    $line = $line -replace '://[^/@\s]+@', '://***@'
    if ($line.Length -gt 300) { $line = $line.Substring(0, 300) }
    return $line
}

function Test-SecretPath {
    # True when the file name matches the secret name rule, or the path has a secrets folder or auth.json.
    param([string]$RelativePath)
    $normalized = ($RelativePath -replace '\\', '/').Trim()
    $name = ($normalized -split '/')[-1]
    if ($name -match $secretNamePattern) { return $true }
    if (("/" + $normalized).ToLowerInvariant().Contains("/secrets/")) { return $true }
    if ($normalized.ToLowerInvariant().Contains("auth.json")) { return $true }
    return $false
}

function Read-CaptureLines {
    param([string]$Path)
    if (-not [System.IO.File]::Exists($Path)) { return @() }
    $lines = @([System.IO.File]::ReadAllLines($Path, (New-Object System.Text.UTF8Encoding($false))))
    [System.IO.File]::Delete($Path)
    return $lines
}

function Invoke-GitCapture {
    # Runs one git command through cmd /c with stdout and stderr redirected to files (bytes kept, read as UTF-8).
    # git writes progress to stderr, so only this call runs with Continue and success is judged from LASTEXITCODE.
    param([string]$ArgumentText)
    $stamp = [guid]::NewGuid().ToString("N")
    $stdoutPath = Join-Path $workDirectory ("git-" + $stamp + ".out")
    $stderrPath = Join-Path $workDirectory ("git-" + $stamp + ".err")
    $commandLine = 'git -C "' + $resolvedRepository + '" ' + $ArgumentText + ' > "' + $stdoutPath + '" 2> "' + $stderrPath + '"'
    $exitCode = -1
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        cmd /c $commandLine | Out-Null
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $stdoutLines = @(Read-CaptureLines -Path $stdoutPath)
    $stderrLines = @(Read-CaptureLines -Path $stderrPath)
    return [ordered]@{ exit_code = $exitCode; lines = $stdoutLines; errors = $stderrLines }
}

function Get-LastLines {
    param($Result, [int]$Count)
    $all = @($Result.lines) + @($Result.errors) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }
    $tail = @($all | Select-Object -Last $Count)
    return ConvertTo-OneLine ($tail -join " | ")
}

function Get-PathList {
    # Paths printed by git, one per line, without empty lines and surrounding quotes.
    param($Result)
    $paths = New-Object System.Collections.ArrayList
    foreach ($line in @($Result.lines)) {
        $text = ([string]$line).Trim()
        if ($text.Length -ge 2 -and $text.StartsWith('"') -and $text.EndsWith('"')) { $text = $text.Substring(1, $text.Length - 2) }
        if ($text.Length -gt 0) { [void]$paths.Add($text) }
    }
    return $paths.ToArray()
}

function Hide-OneDrivePath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $Path }
    if (-not [string]::IsNullOrWhiteSpace($env:OneDrive) -and $Path.StartsWith($env:OneDrive, [System.StringComparison]::OrdinalIgnoreCase)) {
        return "<OneDrive>" + $Path.Substring($env:OneDrive.Length)
    }
    return $Path
}

function Invoke-PushStage {
    $push = [ordered]@{ state = "FAIL"; branch = $null; local_sha = $null; ahead_before = $null; note = "" }
    if ($SkipPush) {
        $push.state = "SKIPPED"
        $push.note = "skipped by -SkipPush"
        return $push
    }
    try {
        $branchResult = Invoke-GitCapture -ArgumentText "rev-parse --abbrev-ref HEAD"
        if ($branchResult.exit_code -ne 0 -or @($branchResult.lines).Count -lt 1) {
            $push.note = "branch not read: " + (Get-LastLines -Result $branchResult -Count 3)
            return $push
        }
        $branch = ([string]@($branchResult.lines)[0]).Trim()
        $push.branch = $branch
        if ($branch -eq "HEAD") {
            $push.state = "SKIPPED"
            $push.note = "detached HEAD: nothing pushed"
            return $push
        }
        if ($branch -eq "main") {
            $push.state = "SKIPPED"
            $push.note = "main is PR-only: nothing pushed"
            return $push
        }
        if ($branch -notmatch $branchNamePattern) {
            $push.note = "branch name has characters this script does not pass to git: nothing pushed"
            return $push
        }
        $shaResult = Invoke-GitCapture -ArgumentText "rev-parse HEAD"
        if ($shaResult.exit_code -eq 0 -and @($shaResult.lines).Count -ge 1) { $push.local_sha = ([string]@($shaResult.lines)[0]).Trim() }
        $remoteResult = Invoke-GitCapture -ArgumentText "remote"
        if ($remoteResult.exit_code -ne 0 -or @(Get-PathList -Result $remoteResult) -notcontains "origin") {
            $push.note = "remote origin not found: nothing pushed"
            return $push
        }
        $aheadResult = Invoke-GitCapture -ArgumentText "rev-list --count HEAD --not --remotes=origin"
        if ($aheadResult.exit_code -eq 0 -and @($aheadResult.lines).Count -ge 1) { $push.ahead_before = [int64](([string]@($aheadResult.lines)[0]).Trim()) }

        # Every path changed by the commits that are not yet on origin (merge commits included, added-then-removed included).
        $logResult = Invoke-GitCapture -ArgumentText "-c core.quotePath=false log -m --name-only --format= HEAD --not --remotes=origin"
        if ($logResult.exit_code -ne 0) {
            $push.note = "outgoing path list not read: nothing pushed: " + (Get-LastLines -Result $logResult -Count 3)
            return $push
        }
        $secretPaths = @(Get-PathList -Result $logResult | Where-Object { Test-SecretPath -RelativePath $_ } | Select-Object -Unique)
        if ($secretPaths.Count -gt 0) {
            $push.state = "BLOCKED_SECRET"
            $push.note = ConvertTo-OneLine ("secret-like path names in outgoing commits, nothing pushed: " + ((@($secretPaths | Select-Object -First 10)) -join ", "))
            return $push
        }
        if ($DryRun) {
            $push.state = "PLANNED"
            $push.note = "dry run: would push origin " + $branch + ":refs/heads/" + $branch
            return $push
        }
        $env:GIT_TERMINAL_PROMPT = "0"
        $env:GCM_INTERACTIVE = "never"
        $pushResult = Invoke-GitCapture -ArgumentText ("push origin " + $branch + ":refs/heads/" + $branch)
        if ($pushResult.exit_code -eq 0) {
            $push.state = "OK"
            $push.note = Get-LastLines -Result $pushResult -Count 1
        } else {
            $push.state = "FAIL"
            $push.note = ("push returned " + $pushResult.exit_code + ": " + (Get-LastLines -Result $pushResult -Count 3))
        }
    } catch {
        $push.state = "FAIL"
        $push.note = "push stage failed: " + (ConvertTo-OneLine $_.Exception.Message)
    }
    return $push
}

function Get-CopyPlan {
    # Returns the files to copy as (source, relative) pairs and fills the missing and skip counters of $copy.
    param($Copy, $Notes)
    $plan = New-Object System.Collections.ArrayList
    $stateRoot = Join-Path $resolvedRepository "stock-strategy-system"
    if (-not [System.IO.Directory]::Exists($stateRoot)) {
        [void]$Copy.missing.Add("stock-strategy-system")
    } else {
        # Untracked files only (tracked files are already backed up by the push): untracked plus ignored.
        $untracked = Invoke-GitCapture -ArgumentText "-c core.quotePath=false ls-files --others --exclude-standard stock-strategy-system"
        $ignored = Invoke-GitCapture -ArgumentText "-c core.quotePath=false ls-files --others --ignored --exclude-standard stock-strategy-system"
        if ($untracked.exit_code -ne 0 -or $ignored.exit_code -ne 0) { throw "untracked file list of stock-strategy-system not read" }
        $relativePaths = @(@(Get-PathList -Result $untracked) + @(Get-PathList -Result $ignored) | Select-Object -Unique)
        $hidden = 0
        foreach ($relative in $relativePaths) {
            $normalized = $relative -replace '\\', '/'
            $excluded = $false
            foreach ($prefix in $stateExcludedPrefixes) { if ($normalized.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) { $excluded = $true } }
            if ($excluded) { continue }
            if (Test-SecretPath -RelativePath $normalized) { $Copy.skipped_secret_files++; continue }
            $source = Join-Path $resolvedRepository ($normalized -replace '/', '\')
            $info = New-Object System.IO.FileInfo($source)
            if (-not $info.Exists) { continue }
            # Hidden files are left out so the count matches Get-ChildItem and Compress-Archive (no -Force).
            if (($info.Attributes -band [System.IO.FileAttributes]::Hidden) -ne 0) { $hidden++; continue }
            [void]$plan.Add([ordered]@{ source = $info.FullName; relative = ($normalized -replace '/', '\'); length = $info.Length })
        }
        if ($hidden -gt 0) { [void]$Notes.Add("hidden files left out: " + $hidden) }
    }
    foreach ($folder in $outputFolders) {
        $folderPath = Join-Path $resolvedRepository ("workspace\outputs\" + $folder)
        if (-not [System.IO.Directory]::Exists($folderPath)) {
            [void]$Copy.missing.Add("workspace/outputs/" + $folder)
            continue
        }
        foreach ($file in @(Get-ChildItem -LiteralPath $folderPath -Recurse -File)) {
            $relative = $file.FullName.Substring($resolvedRepository.Length).TrimStart('\')
            if (Test-SecretPath -RelativePath $relative) { $Copy.skipped_secret_files++; continue }
            [void]$plan.Add([ordered]@{ source = $file.FullName; relative = $relative; length = $file.Length })
        }
    }
    return $plan.ToArray()
}

function Invoke-CopyStage {
    $copy = [ordered]@{
        state = "FAIL"; path = $null; bytes = 0; files = 0; entries = 0; kept = 0
        deleted = (New-Object System.Collections.ArrayList); missing = (New-Object System.Collections.ArrayList)
        skipped_secret_files = 0; locked_files = 0; onedrive_running = $false; note = ""
    }
    $notes = New-Object System.Collections.ArrayList
    [void]$notes.Add("sync completion not verified")
    [void]$notes.Add("excluded: official-event-intake, activation, dev-runs, private inputs")
    try {
        $copy.onedrive_running = ($null -ne (Get-Process -Name OneDrive -ErrorAction SilentlyContinue))
        if (-not $copy.onedrive_running) { [void]$notes.Add("OneDrive not running: copy stays on this PC") }
        if ($SkipCopy) {
            $copy.state = "SKIPPED"
            [void]$notes.Add("skipped by -SkipCopy")
            return $copy
        }
        $parent = $null
        if (-not [string]::IsNullOrWhiteSpace($BackupRoot)) { $parent = [System.IO.Path]::GetDirectoryName($BackupRoot.TrimEnd('\')) }
        if ([string]::IsNullOrWhiteSpace($BackupRoot) -or [string]::IsNullOrWhiteSpace($parent) -or -not [System.IO.Directory]::Exists($parent)) {
            $copy.state = "FAIL"
            [void]$notes.Add("OneDrive folder not found")
            return $copy
        }
        $zipPath = Join-Path $BackupRoot ($dateKst + ".zip")
        $temporaryZip = Join-Path $BackupRoot ($dateKst + ".tmp.zip")
        $copy.path = Hide-OneDrivePath $zipPath

        $plan = @(Get-CopyPlan -Copy $copy -Notes $notes)
        if ($plan.Count -eq 0) {
            $copy.state = "FAIL"
            [void]$notes.Add("no files to copy")
            return $copy
        }
        if ($DryRun) {
            $copy.state = "PLANNED"
            $copy.files = $plan.Count
            $copy.bytes = [int64](($plan | ForEach-Object { $_.length } | Measure-Object -Sum).Sum)
            [void]$notes.Add("dry run: files and bytes are the planned source files, nothing written")
            return $copy
        }

        $stagingRoot = Join-Path $workDirectory "staging"
        [void][System.IO.Directory]::CreateDirectory($stagingRoot)
        foreach ($entry in $plan) {
            $target = Join-Path $stagingRoot $entry.relative
            try {
                [void][System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($target))
                [System.IO.File]::Copy($entry.source, $target, $true)
            } catch {
                $copy.locked_files++
            }
        }
        if ($copy.locked_files -gt 0) { [void]$notes.Add("files not copied (locked or unreadable): " + $copy.locked_files) }
        $copy.files = @(Get-ChildItem -LiteralPath $stagingRoot -Recurse -File).Count
        if ($copy.files -eq 0) {
            $copy.state = "FAIL"
            [void]$notes.Add("no file could be copied")
            return $copy
        }

        [void][System.IO.Directory]::CreateDirectory($BackupRoot)
        if ([System.IO.File]::Exists($temporaryZip)) { [System.IO.File]::Delete($temporaryZip) }
        $topItems = @(Get-ChildItem -LiteralPath $stagingRoot | ForEach-Object { $_.FullName })
        Compress-Archive -LiteralPath $topItems -DestinationPath $temporaryZip -CompressionLevel Optimal

        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive = [System.IO.Compression.ZipFile]::OpenRead($temporaryZip)
        try {
            $copy.entries = @($archive.Entries | Where-Object { $_.Name.Length -gt 0 }).Count
        } finally {
            $archive.Dispose()
        }
        if ($copy.entries -ne $copy.files) {
            [System.IO.File]::Delete($temporaryZip)
            $copy.state = "FAIL"
            [void]$notes.Add(("zip entry count {0} differs from copied file count {1}: zip removed" -f $copy.entries, $copy.files))
            return $copy
        }
        if ([System.IO.File]::Exists($zipPath)) {
            [System.IO.File]::Replace($temporaryZip, $zipPath, [NullString]::Value)
        } else {
            [System.IO.File]::Move($temporaryZip, $zipPath)
        }
        $copy.bytes = (New-Object System.IO.FileInfo($zipPath)).Length
        $copy.state = "OK"

        # Retention runs only after today's zip is OK, and only on YYYY-MM-DD.zip files directly in the backup folder.
        $dailyZips = @(Get-ChildItem -LiteralPath $BackupRoot -File | Where-Object { $_.Name -match $dailyZipPattern } | Sort-Object -Property Name -Descending)
        $oldZips = @($dailyZips | Select-Object -Skip $KeepCount)
        foreach ($old in $oldZips) {
            try {
                Remove-Item -LiteralPath $old.FullName
                [void]$copy.deleted.Add($old.Name)
            } catch {
                [void]$notes.Add("old zip not deleted: " + $old.Name)
            }
        }
        $copy.kept = @(Get-ChildItem -LiteralPath $BackupRoot -File | Where-Object { $_.Name -match $dailyZipPattern }).Count
    } catch {
        $copy.state = "FAIL"
        [void]$notes.Add("copy stage failed: " + (ConvertTo-OneLine $_.Exception.Message))
    } finally {
        $copy.note = ConvertTo-OneLine ($notes -join "; ")
    }
    return $copy
}

$workDirectory = $null
try {
    $nowUtc = [DateTime]::UtcNow
    $invariant = [System.Globalization.CultureInfo]::InvariantCulture
    $dateKst = $nowUtc.AddHours(9).ToString("yyyy-MM-dd", $invariant)
    if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
        # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
        $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    }
    $resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path.TrimEnd('\')
    if ([string]::IsNullOrWhiteSpace($BackupRoot) -and -not [string]::IsNullOrWhiteSpace($env:OneDrive)) {
        $BackupRoot = Join-Path $env:OneDrive "InvestmentV2-Backup"
    }
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        $OutputPath = Join-Path $resolvedRepository "workspace\outputs\backup\LATEST.json"
    }
    $fullOutputPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
    $workDirectory = Join-Path $env:TEMP ("InvestmentV2-Backup-" + [guid]::NewGuid().ToString("N"))
    [void][System.IO.Directory]::CreateDirectory($workDirectory)

    $push = Invoke-PushStage
    $copy = Invoke-CopyStage
    $copy.deleted = $copy.deleted.ToArray()
    $copy.missing = $copy.missing.ToArray()

    $passStates = @("OK", "SKIPPED")
    $status = "OK"
    if ($passStates -notcontains $push.state -or $passStates -notcontains $copy.state -or -not $copy.onedrive_running -or $copy.locked_files -gt 0) {
        $status = "WARN"
    }
    $report = [ordered]@{
        schema = "backup-status/v1"
        generated_at = $nowUtc.ToString("yyyy-MM-ddTHH:mm:ssZ", $invariant)
        generated_at_kst = $nowUtc.AddHours(9).ToString("yyyy-MM-ddTHH:mm:ss", $invariant) + "+09:00"
        hostname = $env:COMPUTERNAME
        dry_run = [bool]$DryRun
        push = $push
        copy = $copy
        status = $status
        read_only_repo = $true
    }
    $json = $report | ConvertTo-Json -Depth 6

    $outputDirectory = [System.IO.Path]::GetDirectoryName($fullOutputPath)
    [void][System.IO.Directory]::CreateDirectory($outputDirectory)
    $temporaryPath = $fullOutputPath + ".tmp"
    [System.IO.File]::WriteAllText($temporaryPath, $json, (New-Object System.Text.UTF8Encoding($false)))
    if ([System.IO.File]::Exists($fullOutputPath)) {
        # [NullString]::Value passes a real null (no backup file); a plain $null could arrive as "".
        [System.IO.File]::Replace($temporaryPath, $fullOutputPath, [NullString]::Value)
    } else {
        [System.IO.File]::Move($temporaryPath, $fullOutputPath)
    }
    Write-Output ("OFFSITE_BACKUP status=" + $status + " push=" + $push.state + " copy=" + $copy.state + " path=" + $fullOutputPath)
} catch {
    Write-Output ("OFFSITE_BACKUP_FAIL " + (ConvertTo-OneLine $_.Exception.Message))
} finally {
    if ($null -ne $workDirectory -and [System.IO.Directory]::Exists($workDirectory)) {
        try { [System.IO.Directory]::Delete($workDirectory, $true) } catch { Write-Output ("OFFSITE_BACKUP_TEMP_LEFT " + $workDirectory) }
    }
}
exit 0
