# Restore hash check (D11, docs/claude/new-pc-recovery-procedure.md): extracts the newest offsite backup zip
# (written by manage-us-stock-strategy/scripts/offsite_backup.ps1) into a new temporary folder and compares the
# sha256 of every extracted file with the same repository-relative file in the working copy.
# Read-only: never writes, moves or deletes anything in the repository or in the backup folder. The only write is
# the temporary extraction folder under %TEMP%, removed at the end. Results go to the screen only (no result file).
# No broker call, no web call, no git call, no secret file is opened (the backup itself leaves secret names out).
# Windows PowerShell 5.1. Example:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\docs\claude\restore-hash-check-2026-10-25.ps1
# A DIFF is not damage by itself: files the daily tasks rewrite after 23:50 (LATEST.json files, new records) differ
# from the zip. Run right after the 23:50 backup, or read each DIFF line against the file's own update time.
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$BackupRoot = "",
    [string]$ZipPath = "",
    [ValidateRange(0, 100000)][int]$ShowLimit = 40
)

$ErrorActionPreference = "Stop"
$dailyZipPattern = '^\d{4}-\d{2}-\d{2}\.zip$'

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$workDirectory = $null
$exitCode = 2
try {
    if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
        # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
        $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    }
    $repository = (Resolve-Path -LiteralPath $RepositoryRoot).Path.TrimEnd('\')

    if ([string]::IsNullOrWhiteSpace($ZipPath)) {
        if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
            if ([string]::IsNullOrWhiteSpace($env:OneDrive)) { throw "OneDrive folder not set: pass -BackupRoot or -ZipPath" }
            $BackupRoot = Join-Path $env:OneDrive "InvestmentV2-Backup"
        }
        if (-not [System.IO.Directory]::Exists($BackupRoot)) { throw ("backup folder not found: " + $BackupRoot) }
        $newest = @(Get-ChildItem -LiteralPath $BackupRoot -File | Where-Object { $_.Name -match $dailyZipPattern } |
            Sort-Object -Property Name -Descending | Select-Object -First 1)
        if ($newest.Count -eq 0) { throw ("no YYYY-MM-DD.zip in " + $BackupRoot) }
        $ZipPath = $newest[0].FullName
    }
    if (-not [System.IO.File]::Exists($ZipPath)) { throw ("zip not found: " + $ZipPath) }

    Write-Output ("RESTORE_CHECK repository=" + $repository)
    Write-Output ("RESTORE_CHECK zip=" + $ZipPath + " bytes=" + (New-Object System.IO.FileInfo($ZipPath)).Length +
        " modified=" + (Get-Item -LiteralPath $ZipPath).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"))

    $workDirectory = Join-Path $env:TEMP ("InvestmentV2-RestoreCheck-" + [guid]::NewGuid().ToString("N"))
    [void][System.IO.Directory]::CreateDirectory($workDirectory)
    $extractRoot = [System.IO.Path]::GetFullPath($workDirectory).TrimEnd('\') + '\'

    # Entry by entry so both "/" and "\" separators work and no entry can land outside the temporary folder.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $relativePaths = New-Object System.Collections.ArrayList
    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        foreach ($entry in $archive.Entries) {
            if ($entry.Name.Length -eq 0) { continue }
            $relative = ($entry.FullName -replace '/', '\').TrimStart('\')
            $target = [System.IO.Path]::GetFullPath((Join-Path $workDirectory $relative))
            if (-not $target.StartsWith($extractRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw ("zip entry outside the extraction folder: " + $entry.FullName)
            }
            [void][System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($target))
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $false)
            [void]$relativePaths.Add($relative)
        }
    } finally {
        $archive.Dispose()
    }

    $match = 0
    $diff = New-Object System.Collections.ArrayList
    $missing = New-Object System.Collections.ArrayList
    foreach ($relative in $relativePaths) {
        $original = Join-Path $repository $relative
        if (-not [System.IO.File]::Exists($original)) { [void]$missing.Add($relative); continue }
        $restoredHash = Get-Sha256 -Path (Join-Path $workDirectory $relative)
        $originalHash = Get-Sha256 -Path $original
        if ($restoredHash -eq $originalHash) {
            $match++
        } else {
            $stamp = (Get-Item -LiteralPath $original).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            [void]$diff.Add(("{0} (original modified {1})" -f $relative, $stamp))
        }
    }

    Write-Output ("RESTORE_CHECK extracted={0} match={1} diff={2} missing_original={3}" -f $relativePaths.Count, $match, $diff.Count, $missing.Count)
    foreach ($line in @($diff | Select-Object -First $ShowLimit)) { Write-Output ("DIFF " + $line) }
    if ($diff.Count -gt $ShowLimit) { Write-Output ("DIFF ... " + ($diff.Count - $ShowLimit) + " more") }
    foreach ($line in @($missing | Select-Object -First $ShowLimit)) { Write-Output ("MISSING_ORIGINAL " + $line) }
    if ($missing.Count -gt $ShowLimit) { Write-Output ("MISSING_ORIGINAL ... " + ($missing.Count - $ShowLimit) + " more") }

    $latestPath = Join-Path $repository "workspace\outputs\backup\LATEST.json"
    if ([System.IO.File]::Exists($latestPath)) {
        $latest = Get-Content -LiteralPath $latestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Output ("RESTORE_CHECK latest_json generated_at_kst={0} status={1} copy_files={2} copy_entries={3} copy_path={4}" -f
            $latest.generated_at_kst, $latest.status, $latest.copy.files, $latest.copy.entries, $latest.copy.path)
    } else {
        Write-Output "RESTORE_CHECK latest_json not found"
    }

    if ($relativePaths.Count -gt 0 -and $diff.Count -eq 0 -and $missing.Count -eq 0) {
        Write-Output "RESTORE_CHECK result=PASS"
        $exitCode = 0
    } else {
        Write-Output "RESTORE_CHECK result=REVIEW (read the DIFF and MISSING_ORIGINAL lines; see the header note)"
        $exitCode = 1
    }
} catch {
    Write-Output ("RESTORE_CHECK_FAIL " + (($_.Exception.Message -replace "[\r\n]+", " ").Trim()))
    $exitCode = 2
} finally {
    if ($null -ne $workDirectory -and [System.IO.Directory]::Exists($workDirectory)) {
        try { [System.IO.Directory]::Delete($workDirectory, $true) } catch { Write-Output ("RESTORE_CHECK_TEMP_LEFT " + $workDirectory) }
    }
}
exit $exitCode
