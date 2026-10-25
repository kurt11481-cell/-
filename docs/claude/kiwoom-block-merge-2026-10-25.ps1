# Merge kiwoom-block (manual route, K3: order-block hardening, only adds blocks, nothing is loosened).
# User approval: the user's own thread message "boganan 4 jinhaeng" (2026-10-25 10:44:51Z, Korean text in the thread) and the
# fix instructions pasted by the user (12:04:09Z, 13:07:28Z). Judge: docs/claude/kiwoom-block-judge-report.md (last line VERDICT: PASS).
# The merge is the user's one line in their own interactive PowerShell.
# Changes (6 paths): a new PreToolUse hook (.claude/hooks/kiwoom_order_block.py), .claude/settings.json (3 deny lines + hooks block,
# copied byte for byte from docs/claude/kiwoom-block-settings-proposed.json), its tests, the overseas-order guard note, the Builder
# report and the proposed settings file. Existing deny/ask entries are kept unchanged.
# Checks: interactive console (four conditions, both handles are console handles, then one Enter); no dev-run lock and no
# auto-core / decide / dev / docs-commit / t2rc-check task running; not inside Tue-Sat 06:00-09:00 KST or 23:20-23:45 KST;
# Judge report ends with VERDICT: PASS; base 7f98f28 is an ancestor of main and main touched no merged path since (and only
# docs/claude/ paths at all); .claude/settings.json on main is the measured pre-change file; the worktree changed exactly the
# 5 new paths with the sha256 measured before the merge; the hook runs on sample inputs (benign -> exit 0, order marker -> exit 2).
# Then it copies the proposed settings into the worktree, commits the 6 paths there, merges --no-ff into main and runs the
# targeted tests and the schema contracts on main.
# No order, no Kiwoom, no policy, state, ledger or journal write. ASCII only (Windows PowerShell 5.1).
$ErrorActionPreference = 'Continue'
function Stop-Merge([string]$why) { Write-Output ('KWB_STOP ' + $why); exit 2 }

if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or ($Host.Name -ne 'ConsoleHost') -or `
    (-not [Environment]::UserInteractive)) { Stop-Merge 'not an interactive console' }
$consoleHandles = $false
try {
    Add-Type -TypeDefinition @'
        using System;
        using System.Runtime.InteropServices;
        public static class KwbConsoleHandles {
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
    $consoleHandles = [KwbConsoleHandles]::Both()
} catch { $consoleHandles = $false }
if ($consoleHandles -ne $true) { Stop-Merge 'standard handles are not console handles' }
$entered = $null
try {
    Write-Host -NoNewline 'Authority merge kiwoom-block. Press Enter to continue (Ctrl+C cancels): '
    $entered = [Console]::ReadLine()
} catch { $entered = $null }
if ($null -eq $entered) { Stop-Merge 'no Enter (end of input)' }

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\kiwoom-block'
$base = (git -C $repo rev-parse 7f98f28).Trim()
$branch = 'worktree-kiwoom-block'
$judge = Join-Path $repo 'docs\claude\kiwoom-block-judge-report.md'
$settingsPath = '.claude/settings.json'
$settingsBefore = 'f793271fad76954a640e5111fd4d03293a265298ec664b8f8ab1aedfb5cfdfe5'
$proposedPath = 'docs/claude/kiwoom-block-settings-proposed.json'
$hashes = @{
    '.claude/hooks/kiwoom_order_block.py' = '2818d79fcdd5ee2083be65c888447ea84a04f75188ca35376a5b2038c87cc81f';
    'docs/claude/kiwoom-block-builder-report.md' = '58bd0cef162f23187c260edde869f985338696a1283125688a9c82b83492964b';
    'docs/claude/kiwoom-block-settings-proposed.json' = '459cd04f0dee5aa915fafc0397af2369b9348aab19632505df953d466ea36942';
    'docs/claude/kiwoom-overseas-order-guard-2026-10-25.md' = '36f4b3a928ac6074220f6bf1a42d4890e5cd3988ea3cbfae3cd63a7d94442864';
    'manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py' = '859b57e8d91cb8f18fa6353252021f893d580c37af40a7e409cc4fcfb8f5a30b'
}
$newPaths = @($hashes.Keys | Sort-Object)
$paths = @(($newPaths + $settingsPath) | Sort-Object)

$kst = [DateTime]::UtcNow.AddHours(9)
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
$unknown = @($moved | Where-Object { -not $_.StartsWith('docs/claude/') })
if ($unknown.Count -ne 0) { Stop-Merge ('main moved with non-docs paths: ' + ($unknown -join ',')) }
$overlap = @($moved | Where-Object { $paths -contains $_ })
if ($overlap.Count -ne 0) { Stop-Merge ('a merged path changed on main since base: ' + ($overlap -join ',')) }
$dirty = @(git -C $repo status --porcelain -- $paths)
if ($dirty.Count -ne 0) { Stop-Merge ('uncommitted main change on a merged path: ' + ($dirty -join ' | ')) }
$mainSettings = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo '.claude\settings.json')).Hash.ToLower()
if ($mainSettings -ne $settingsBefore) { Stop-Merge 'main .claude/settings.json is not the measured pre-change file' }
if ((git -C $wt rev-parse HEAD).Trim() -ne $base) { Stop-Merge 'worktree head is not base' }
$status = @(git -C $wt status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3) } | Sort-Object)
if (($status -join '|') -ne ($newPaths -join '|')) { Stop-Merge ('worktree paths: ' + ($status -join ',')) }
foreach ($p in $newPaths) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $p)).Hash.ToLower()
    if ($h -ne $hashes[$p]) { Stop-Merge ('hash changed after review: ' + $p) }
}
$wtSettings = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt '.claude\settings.json')).Hash.ToLower()
if ($wtSettings -ne $settingsBefore) { Stop-Merge 'worktree .claude/settings.json is not the measured pre-change file' }

# Smoke test the hook exactly as a PreToolUse command would run it: stdin JSON in, exit code out.
$hook = Join-Path $wt '.claude\hooks\kiwoom_order_block.py'
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Stop-Merge 'python not found on PATH (the hook command needs it)' }
function Run-Hook([string]$json) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $py.Source
    $psi.Arguments = '"' + $hook + '"'
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $proc = [System.Diagnostics.Process]::Start($psi)
    $proc.StandardInput.Write($json)
    $proc.StandardInput.Close()
    $null = $proc.StandardOutput.ReadToEnd()
    $null = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    return $proc.ExitCode
}
$ok1 = Run-Hook '{"tool_name":"Bash","tool_input":{"command":"git status"}}'
$ok2 = Run-Hook '{"tool_name":"Monitor","tool_input":{"command":"echo ust20000"}}'
$ok3 = Run-Hook '{"tool_name":"PowerShell","tool_input":{"command":"echo --con\"\"firm"}}'
$ok4 = Run-Hook 'not json'
if ($ok1 -ne 0) { Stop-Merge ('hook smoke test: benign command exit ' + $ok1) }
if ($ok2 -ne 2) { Stop-Merge ('hook smoke test: Monitor order marker exit ' + $ok2) }
if ($ok3 -ne 2) { Stop-Merge ('hook smoke test: PowerShell quoted marker exit ' + $ok3) }
if ($ok4 -ne 2) { Stop-Merge ('hook smoke test: broken input exit ' + $ok4) }
Write-Output 'CHECKS_OK'

# Install the proposed settings byte for byte, verify, then commit and merge.
Copy-Item -LiteralPath (Join-Path $wt $proposedPath) -Destination (Join-Path $wt '.claude\settings.json') -Force
$wtSettingsAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt '.claude\settings.json')).Hash.ToLower()
if ($wtSettingsAfter -ne $hashes[$proposedPath]) { Stop-Merge 'settings copy does not match the proposed file' }
$msgFile = Join-Path $env:TEMP 'kiwoom-block-commit-message.txt'
$msg = "feat(safety): kiwoom order-block hardening (hook, 3 deny lines, guard note) (kiwoom-block)`n`n" +
       "kiwoom-block (K3, manual route; user thread messages 2026-10-25 10:44:51Z, 12:04:09Z, 13:07:28Z, merge by the user's own`n" +
       "PowerShell line). Adds only blocks: PreToolUse hook .claude/hooks/kiwoom_order_block.py (order markers, fail closed),`n" +
       "deny mcp__*__kiwoom_order_preview and Bash/PowerShell *overseas orders*, settings hooks block. Existing deny/ask entries`n" +
       "unchanged. Overseas-order guard note (the CLI sends with --confirm; the switch KIWOOM_MCP_ALLOW_ORDERS covers MCP only).`n" +
       "Builder docs/claude/kiwoom-block-builder-report.md, Judge docs/claude/kiwoom-block-judge-report.md (PASS).`n`n" +
       "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`n" +
       "Claude-Session: https://claude.ai/code/session_015acr5wvrucCQSFMeZU95mK`n"
[System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
git -C $wt add -- $paths
git -C $wt commit -q -F $msgFile
if ($LASTEXITCODE -ne 0) { Stop-Merge 'worktree commit failed' }
$commit = (git -C $wt rev-parse HEAD).Trim()
git -C $repo merge --no-ff -q -m "Merge kiwoom-block (order-block hardening: hook, deny lines, guard note; K3, Judge PASS)" $branch
if ($LASTEXITCODE -ne 0) { git -C $repo merge --abort; Stop-Merge 'merge failed (aborted)' }
Write-Output ('MERGED worktree_commit=' + $commit.Substring(0, 8) + ' main=' + (git -C $repo rev-parse --short HEAD).Trim())

Push-Location $repo
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_order_block_hook.py"
$t1 = $LASTEXITCODE
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_approval_human_check*"
$t2 = $LASTEXITCODE
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline*"
$t3 = $LASTEXITCODE
python manage-us-stock-strategy/scripts/validate_schema_contracts.py
$t4 = $LASTEXITCODE
Pop-Location
Write-Output ('TESTS hook=' + $t1 + ' approval=' + $t2 + ' dev_pipeline=' + $t3 + ' schema=' + $t4)
if (($t1 + $t2 + $t3 + $t4) -ne 0) { Write-Output 'KWB_WARN a test failed after merge: tell the project thread (nothing was undone)' }
Write-Output 'NEXT: open a NEW Claude Code session and ask it to run the harmless test: echo ust20000 (Bash, then Monitor). Refused = hook works.'
Write-Output 'IF shell tools in new Claude Code sessions are blocked for everything: remove the "hooks" block from .claude/settings.json yourself (see the Builder report).'
Write-Output 'KWB_DONE'
