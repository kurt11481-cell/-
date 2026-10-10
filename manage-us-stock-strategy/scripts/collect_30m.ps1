# Read-only Kiwoom 30-minute bar collection (kiwoomcli overseas candles stock-minute = usa06011).
# No order, account or write command is used. Output: <OutRoot>\<SYMBOL>\<symbol>_30m_<from>_p<pages>.json
# OutRoot defaults to workspace\outputs\regular-session-closes\pages of this repository (unchanged folder).
# Tracked copy (redesign T1 F5) of workspace\outputs\regular-session-closes\collect_30m.ps1 (local version
# with -KiwoomProfile, sha256 9717579c80ed4f8780caf9d3efb3f853c8eae2bc2711b1c07cef266c32b18b49); the original
# stays where it is.
# Each fetch is one file. Fetches step back StepDays calendar days and cover Pages*100 bars, so they
# overlap; the newest bar of each file (ignored by the history builder) is covered by the newer file.
# Stops at the first failure (no retry). Re-running skips files that already have content.
# -KiwoomProfile is required (standing rule 2026-10-07, T1 r3 C6): every call passes --profile and
# --mode real; without a profile nothing is fetched.
param(
  [Parameter(Mandatory = $true)][string]$Symbol,
  [Parameter(Mandatory = $true)][ValidateSet('NASDAQ', 'NYSE', 'AMEX')][string]$Exchange,
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$KiwoomProfile,
  [string]$Newest = '20261001',
  [string]$Oldest = '20260401',
  [int]$Pages = 3,
  [int]$StepDays = 7,
  [int]$PauseSeconds = 3,
  [string]$OutRoot = ''
)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
if ($Symbol -notmatch '^[A-Z][A-Z0-9.]{0,11}$') {
  Write-Host "STOP $Symbol (symbol not allowed)"
  exit 1
}
if ($KiwoomProfile.Trim() -eq '') {
  Write-Host "STOP $Symbol (Kiwoom profile alias required)"
  exit 1
}
if ($OutRoot -eq '') {
  # Windows PowerShell 5.1 leaves $PSScriptRoot empty inside param defaults of advanced scripts.
  $OutRoot = Join-Path $PSScriptRoot '..\..\workspace\outputs\regular-session-closes\pages'
}
$outDir = Join-Path $OutRoot $Symbol
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$day = [datetime]::ParseExact($Newest, 'yyyyMMdd', $null)
$stop = [datetime]::ParseExact($Oldest, 'yyyyMMdd', $null)
$done = 0
$profileArg = " --profile $KiwoomProfile --mode real"
while ($day -ge $stop) {
  $from = $day.ToString('yyyyMMdd')
  $file = Join-Path $outDir ('{0}_30m_{1}_p{2}.json' -f $Symbol.ToLower(), $from, $Pages)
  if ((Test-Path $file) -and ((Get-Item $file).Length -gt 0)) {
    Write-Host "SKIP $Symbol $from (already saved)"
  } else {
    cmd /c "kiwoomcli overseas candles stock-minute --exchange $Exchange --code $Symbol --from $from --interval 30 --adjusted 0 --fx-applied no --pages $Pages --format json$profileArg > `"$file`""
    $code = $LASTEXITCODE
    $size = (Get-Item $file).Length
    # Exit code 0 alone is not success: the saved page must be a return_code 0 response with rows.
    # A bad page is removed so it is never reused as "already saved"; the next run fetches it again.
    $valid = $false
    if ($code -eq 0 -and $size -gt 0) {
      try {
        $page = Get-Content -Raw -Encoding UTF8 -LiteralPath $file | ConvertFrom-Json
        $valid = ($page.return_code -eq 0) -and (@($page.result_list).Count -gt 0)
      } catch { $valid = $false }
    }
    if (-not $valid) {
      Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
      Write-Host "STOP $Symbol $from (exit=$code, bytes=$size, page rejected)."
      exit 1
    }
    Write-Host "OK   $Symbol $from ($size bytes)"
    $done++
    Start-Sleep -Seconds $PauseSeconds
  }
  $day = $day.AddDays(-$StepDays)
}
Write-Host "DONE $Symbol new_files=$done folder=$outDir"
