# redesign-t3c-merge-2026-10-12.ps1 - merge of redesign T3c (authority paths +8, quantity_authority false, CLAUDE.md pin wording).
# Judge PASS without conditions: docs/claude/redesign-t3c-judge-report-2026-10-12.md. User decision: merge after Judge PASS.
# Steps: 0 checks -> 1 commit the 6 changed files + Builder report in worktree t3c -> 2 merge into the main checkout
#        -> 3 checks (schema audit, dev pipeline tests, snapshot-wording test, authority path count).
# Never places, changes or cancels an order. No scheduled task is registered or changed (no .ps1 file changed).
# Stops at the first failed check. ASCII only on purpose (Windows PowerShell 5.1).
# Usage (Windows PowerShell, repo root):  .\docs\claude\redesign-t3c-merge-2026-10-12.ps1

$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\t3c'
$branch = 'worktree-t3c'
$mainBranch = 'codex/master-recovery-expansion'
$trailer = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`nClaude-Session: https://claude.ai/code/session_01SNceM9kum37h9ouasfrqp1"
$expectedSha = [ordered]@{
    'CLAUDE.md' = '846f0fb240cdf8ca79f54ba6610c17c2fef98486710fa95f4a102d2ea585dd72'
    'tools/dev_pipeline/authority-paths.txt' = 'd6ad601250fcaecc0f4a2879a0f1dbe28f8a0b3f2c58ecfaf3f0f3480030e22e'
    'tools/dev_pipeline/devpipe.py' = '94c6e8bbe0f5ccbe34a5cccebaf7b1b93c9782a049abc7f001f34784b237d3fb'
    'tools/dev_pipeline/README.md' = '6a32133d02e9b0b1b2757652405d9053cd862530f4ddf9ceb065fd76a2b2db44'
    'tools/dev_pipeline/judge-prompt.md' = '877d34e27335bdc678e8ba2e707bca86bc913ec491cd7b216129c3c586632b6d'
    'manage-us-stock-strategy/tests/test_dev_pipeline.py' = '997a5251c3311ac7b2bce7c912930ba11dc90a7cfdcc042ab2f07113042cf5cd'
}
$reportPath = 'docs/claude/redesign-t3c-builder-report-2026-10-12.md'
$codePaths = @($expectedSha.Keys) + $reportPath

function Git-Out {
    param([string]$Dir, [string[]]$GitArgs)
    $out = & git -C $Dir @GitArgs
    if ($LASTEXITCODE -ne 0) { throw ('STOP GIT_FAILED: git ' + ($GitArgs -join ' ')) }
    foreach ($line in $out) { $line }
}

function Write-Message {
    param([string]$Text)
    $path = Join-Path ([System.IO.Path]::GetTempPath()) ('t3c-msg-' + [guid]::NewGuid().ToString('N') + '.txt')
    [System.IO.File]::WriteAllText($path, $Text.Replace("`r`n", "`n"), (New-Object System.Text.UTF8Encoding $false))
    return $path
}

Write-Host '== 0 checks'
$current = @(Git-Out $repo @('branch', '--show-current'))[0]
if ($current -ne $mainBranch) { throw "STOP MAIN_BRANCH_UNEXPECTED: $current" }
if (@(Git-Out $repo @('diff', '--cached', '--name-only')).Count -gt 0) { throw 'STOP MAIN_HAS_STAGED_CHANGES' }
$mainDirty = @(Git-Out $repo @('status', '--porcelain', '--', 'CLAUDE.md', 'tools', 'manage-us-stock-strategy/tests/test_dev_pipeline.py'))
if ($mainDirty.Count -gt 0) { throw ('STOP MAIN_PATHS_DIRTY: ' + ($mainDirty -join '; ')) }
if (-not (Test-Path -LiteralPath $wt -PathType Container)) { throw 'STOP WORKTREE_MISSING' }
$wtBranch = @(Git-Out $wt @('branch', '--show-current'))[0]
if ($wtBranch -ne $branch) { throw "STOP WORKTREE_BRANCH_UNEXPECTED: $wtBranch" }
$wtHead = @(Git-Out $wt @('rev-parse', 'HEAD'))[0]
if (-not $wtHead.StartsWith('f8185fc')) { throw "STOP WORKTREE_HEAD_UNEXPECTED: $wtHead" }
$found = @(Git-Out $wt @('status', '--porcelain', '--untracked-files=all') | ForEach-Object { $_.Substring(3).Trim('"') } | Sort-Object)
$expected = @($codePaths | Sort-Object)
$difference = Compare-Object $expected $found
if ($difference) { $difference | Format-Table -AutoSize | Out-Host; throw 'STOP WORKTREE_FILES_UNEXPECTED (=> only in worktree, <= missing)' }
foreach ($path in $expectedSha.Keys) {
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $path)).Hash.ToLower()
    if ($hash -ne $expectedSha[$path]) { throw "STOP SHA_UNEXPECTED: $path $hash" }
}
Write-Host 'OK  main branch clean for the 3 paths, worktree t3c head f8185fc, 7 files, 6 sha256 values'

Write-Host '== 1 commit in the worktree'
Git-Out $wt (@('add', '--') + $codePaths) | Out-Null
$stagedNow = @(Git-Out $wt @('diff', '--cached', '--name-only'))
if ($stagedNow.Count -ne 7) { throw "STOP STAGED_COUNT_UNEXPECTED: $($stagedNow.Count)" }
$message = Write-Message ("feat: dev pipeline T3c (auto-core contracts and card evidence registry as authority paths, quantity_authority false is no authority, CLAUDE.md pin wording)`n`n" +
    "Redesign T3c Builder (worktree t3c). Judge PASS without conditions (docs/claude/redesign-t3c-judge-report-2026-10-12.md). " +
    "authority-paths.txt +4 lines (60 -> 68 tracked files); devpipe ADDED_NONE_VALUES false and `$false for quantity_authority; " +
    "ORDER_TICKET_HUMAN_ENTRY stays authority (tests); CLAUDE.md pin wording follows T1. order_authority=false, execution_quantity=null.`n`n" + $trailer)
Git-Out $wt @('commit', '-q', '-F', $message) | Out-Null
Remove-Item -LiteralPath $message
if (@(Git-Out $wt @('status', '--porcelain')).Count -gt 0) { throw 'STOP WORKTREE_NOT_CLEAN_AFTER_COMMIT' }

Write-Host '== 2 merge into the main checkout'
$message = Write-Message ("Merge worktree-t3c: dev pipeline T3c`n`nJudge PASS without conditions (docs/claude/redesign-t3c-judge-report-2026-10-12.md).`n`n" + $trailer)
& git -C $repo merge --no-ff -q -F $message $branch
$mergeCode = $LASTEXITCODE
Remove-Item -LiteralPath $message
if ($mergeCode -ne 0) { throw 'STOP MERGE_FAILED: nothing else was done. Run  git merge --abort  and send this output to Cowork.' }

Write-Host '== 3 checks (main checkout)'
Push-Location $repo
try {
    $schema = @(& python manage-us-stock-strategy/scripts/validate_schema_contracts.py)
    if ($LASTEXITCODE -ne 0 -or -not ($schema -match '"status": "PASS"')) { $schema | Select-Object -Last 5 | Out-Host; throw 'STOP SCHEMA_AUDIT_FAILED (merged)' }
    Write-Host 'OK  schema audit PASS'
    foreach ($pattern in @('test_dev_pipeline*', 'test_reconcile_broker_state*')) {
        $out = @(cmd /c "python -m unittest discover -s manage-us-stock-strategy/tests -p $pattern 2>&1")
        $code = $LASTEXITCODE
        $tail = ($out | Select-Object -Last 3) -join ' '
        Write-Host ('{0}  {1}  {2}' -f $(if ($code -eq 0) { 'OK ' } else { 'BAD' }), $pattern, $tail)
        if ($code -ne 0) { $out | Select-Object -Last 40 | Out-Host; throw "STOP TESTS_FAILED: $pattern (merged)" }
    }
    $claudeText = Get-Content -LiteralPath (Join-Path $repo 'CLAUDE.md') -Raw
    if ($claudeText -notmatch 'Kiwoom acceptance pin: retired by redesign T1') { throw 'STOP CLAUDE_MD_WORDING_MISSING (merged)' }
    $pathsText = Get-Content -LiteralPath (Join-Path $repo 'tools\dev_pipeline\authority-paths.txt') -Raw
    if (($pathsText -notmatch 'docs/claude/card-evidence-registry\.json') -or ($pathsText -notmatch 'schemas/auto-core-\*\.schema\.json')) { throw 'STOP AUTHORITY_PATHS_MISSING (merged)' }
    Write-Host 'OK  CLAUDE.md wording and the two authority path lines are in the main checkout'
} finally {
    Pop-Location
}

Write-Host '== done'
& git -C $repo log --oneline -4
Write-Host 'T3C_MERGE_DONE'
