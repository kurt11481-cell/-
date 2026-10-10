# run-docs-commit.ps1 - started daily at 23:30 by the Windows task InvestmentV2-DocsCommit (redesign T3).
#
# Calls tools\commit-docs.ps1 unchanged (docs/claude paths only, stops when anything is staged, never
# publishes) and appends all of its output to workspace\outputs\docs-commit\<YYYY-MM-DD>.log as ASCII
# (*.log is git-ignored; non-ASCII characters become '?'). Exit code = commit-docs.ps1 exit code.
# commit-docs.ps1 runs as its own powershell.exe process through cmd /c so its git output goes to the
# file untouched. -DryRun is passed through (nothing is staged or committed).
# ASCII only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as the ANSI code page.

[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$commitDocs = Join-Path $PSScriptRoot 'commit-docs.ps1'
$powershellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$cmdExe = $env:ComSpec
if ([string]::IsNullOrWhiteSpace($cmdExe)) { $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe' }
$logDir = Join-Path $repo 'workspace\outputs\docs-commit'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir ([DateTime]::Now.ToString('yyyy-MM-dd') + '.log')
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$raw = Join-Path $logDir ($stamp + '-commit-docs.tmp')

$dryRunArgument = ''
if ($DryRun) { $dryRunArgument = ' -DryRun' }
$commandLine = '"' + $powershellExe + '" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $commitDocs + '"' +
    $dryRunArgument + ' < NUL > "' + $raw + '" 2>&1'

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $cmdExe
$psi.Arguments = '/d /s /c "' + $commandLine + '"'
$psi.WorkingDirectory = $repo
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$proc = [System.Diagnostics.Process]::Start($psi)
$proc.WaitForExit()
$code = $proc.ExitCode

$builder = New-Object System.Text.StringBuilder
if (Test-Path -LiteralPath $raw) {
    foreach ($b in [System.IO.File]::ReadAllBytes($raw)) {
        if (($b -ge 32 -and $b -lt 127) -or $b -eq 9 -or $b -eq 10) { [void]$builder.Append([char]$b) }
        elseif ($b -ne 13) { [void]$builder.Append('?') }
    }
    Remove-Item -LiteralPath $raw
}
$text = $builder.ToString().TrimEnd()
$header = '== ' + [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') + ' run-docs-commit dryrun=' + [bool]$DryRun
$footer = '== exit=' + $code
Add-Content -LiteralPath $logPath -Value @($header, $text, $footer) -Encoding ASCII
Write-Output $text
Write-Output $footer
exit $code
