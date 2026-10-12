# redesign-t2-merge-2026-10-12.ps1 - one-time deployment of redesign T2 (auto-core decide, compare mode).
# User decision 2026-10-12 11:21 KST: Q1 a, Q2 b, Q3 c, Q4 a, P-1 apply, P-2 apply
# (P-2 tests updated by Builder r5; see docs/claude/redesign-t2-merge-decision-2026-10-12.md).
# Steps: 0 checks -> 1 commit worktree t2-core code (Judge 2 PASS-WITH-CONDITIONS + r5 tests) -> 2 commit P-1 + P-2
#        -> 3 merge into the main checkout branch -> 4 schema/config/tests -> 5 register the two auto-core tasks.
# Never places, changes or cancels an order. Does not run the auto-core. Stops at the first failed check.
# ASCII only on purpose (Windows PowerShell 5.1).
# Usage (Windows PowerShell, repo root):  .\docs\claude\redesign-t2-merge-2026-10-12.ps1

$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$wt = Join-Path $repo '.claude\worktrees\t2-core'
$branch = 'worktree-t2-core'
$mainBranch = 'codex/master-recovery-expansion'
$configPath = 'workspace/policies/auto_core.json'
$configSha = '7fcb0efe543425041d4737fda050f1fca74adb7dcd4039eb2a6351879e575cf4'
$policyPath = 'stock-strategy-system/alert_policy.json'
$policySha = '98ef14e0dfe1d56104a2863fcf7a61a1a9db9907355f923fde3bb5309f3e77a7'
$trailer = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`nClaude-Session: https://claude.ai/code/session_01JtukjYCrCwTYR2XExRBiUk"
$codePaths = @(
    'docs/claude/card-evidence-registry.json',
    'docs/claude/redesign-t2-builder-report-2026-10-10.md',
    'docs/claude/redesign-t2-policy-proposals.json',
    'manage-us-stock-strategy/references/auto-core-decision.md',
    'manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json',
    'manage-us-stock-strategy/schemas/auto-core-compare.schema.json',
    'manage-us-stock-strategy/schemas/auto-core-config.schema.json',
    'manage-us-stock-strategy/schemas/auto-core-decision.schema.json',
    'manage-us-stock-strategy/schemas/auto-core-replay.schema.json',
    'manage-us-stock-strategy/schemas/auto-core-research-record.schema.json',
    'manage-us-stock-strategy/schemas/auto-core-ticket.schema.json',
    'manage-us-stock-strategy/schemas/portfolio-review-journal-payload.schema.json',
    'manage-us-stock-strategy/schemas/portfolio-review-journal.schema.json',
    'manage-us-stock-strategy/scripts/auto_core.py',
    'manage-us-stock-strategy/scripts/auto_core_bars.py',
    'manage-us-stock-strategy/scripts/auto_core_compare.py',
    'manage-us-stock-strategy/scripts/auto_core_decide.py',
    'manage-us-stock-strategy/scripts/auto_core_inputs.py',
    'manage-us-stock-strategy/scripts/auto_core_replay.py',
    'manage-us-stock-strategy/scripts/auto_core_rules.py',
    'manage-us-stock-strategy/scripts/auto_core_tickets.py',
    'manage-us-stock-strategy/scripts/portfolio_review_journal.py',
    'manage-us-stock-strategy/scripts/register_auto_core_task.ps1',
    'manage-us-stock-strategy/scripts/run_auto_core.ps1',
    'manage-us-stock-strategy/tests/fixtures/auto_core_t2/g3-closes-2026-10-08.json',
    'manage-us-stock-strategy/tests/fixtures/auto_core_t2/helpers.py',
    'manage-us-stock-strategy/tests/test_auto_core_compare.py',
    'manage-us-stock-strategy/tests/test_auto_core_decide.py',
    'manage-us-stock-strategy/tests/test_auto_core_replay.py',
    'manage-us-stock-strategy/tests/test_auto_core_rules.py',
    'manage-us-stock-strategy/tests/test_auto_core_tickets.py',
    'manage-us-stock-strategy/tests/test_portfolio_exposure.py'
)

function Git-Out {
    param([string]$Dir, [string[]]$GitArgs)
    $out = & git -C $Dir @GitArgs
    if ($LASTEXITCODE -ne 0) { throw ('STOP GIT_FAILED: git ' + ($GitArgs -join ' ')) }
    # foreach emits nothing for no output (return $null would count as one line).
    foreach ($line in $out) { $line }
}

function Write-Message {
    param([string]$Text)
    $path = Join-Path ([System.IO.Path]::GetTempPath()) ('t2-msg-' + [guid]::NewGuid().ToString('N') + '.txt')
    [System.IO.File]::WriteAllText($path, $Text.Replace("`r`n", "`n"), (New-Object System.Text.UTF8Encoding $false))
    return $path
}

Write-Host '== 0 checks'
$current = @(Git-Out $repo @('branch', '--show-current'))[0]
if ($current -ne $mainBranch) { throw "STOP MAIN_BRANCH_UNEXPECTED: $current" }
if (@(Git-Out $repo @('diff', '--cached', '--name-only')).Count -gt 0) { throw 'STOP MAIN_HAS_STAGED_CHANGES' }
$mainDirty = @(Git-Out $repo @('status', '--porcelain', '--', 'manage-us-stock-strategy', 'workspace/policies', 'stock-strategy-system/alert_policy.json'))
if ($mainDirty.Count -gt 0) { throw ('STOP MAIN_PATHS_DIRTY: ' + ($mainDirty -join '; ')) }
if (-not (Test-Path -LiteralPath $wt -PathType Container)) { throw 'STOP WORKTREE_MISSING' }
$wtBranch = @(Git-Out $wt @('branch', '--show-current'))[0]
if ($wtBranch -ne $branch) { throw "STOP WORKTREE_BRANCH_UNEXPECTED: $wtBranch" }
$wtHead = @(Git-Out $wt @('rev-parse', 'HEAD'))[0]
if (-not $wtHead.StartsWith('cd6a56d')) { throw "STOP WORKTREE_HEAD_UNEXPECTED: $wtHead" }
$found = @(Git-Out $wt @('status', '--porcelain', '--untracked-files=all') | ForEach-Object { $_.Substring(3).Trim('"') } | Sort-Object)
$expected = @(($codePaths + $configPath + $policyPath) | Sort-Object)
if ($found.Count -eq 0) { throw 'STOP WORKTREE_HAS_NO_CHANGES' }
$difference = Compare-Object $expected $found
if ($difference) { $difference | Format-Table -AutoSize | Out-Host; throw 'STOP WORKTREE_FILES_UNEXPECTED (see table: => only in worktree, <= missing)' }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $configPath)).Hash.ToLower()
if ($hash -ne $configSha) { throw "STOP CONFIG_SHA_UNEXPECTED: $hash" }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $wt $policyPath)).Hash.ToLower()
if ($hash -ne $policySha) { throw "STOP POLICY_SHA_UNEXPECTED: $hash" }
Write-Host 'OK  main branch, worktree branch/head, 32 code files + P-1 config + P-2 policy'

Write-Host '== 1 commit T2 code in the worktree'
Git-Out $wt (@('add', '--') + $codePaths) | Out-Null
$stagedNow = @(Git-Out $wt @('diff', '--cached', '--name-only'))
if ($stagedNow.Count -ne 32) { throw "STOP STAGED_COUNT_UNEXPECTED: $($stagedNow.Count)" }
$message = Write-Message ("feat: auto-core T2 decide (rules, gates, LOC order tickets stage 1, outcomes, auto journal, compare, replay)`n`n" +
    "Redesign T2 Builder r1-r4 (worktree t2-core). Judge 1 FAIL F-1..F-4 fixed in r2; Judge 2 PASS-WITH-CONDITIONS " +
    "(r5: two tests follow the P-2 policy, tests only) " +
    "(docs/claude/redesign-t2-judge2-report-2026-10-11.md). order_authority=false, execution_quantity=null; " +
    "quantity_authority ORDER_TICKET_HUMAN_ENTRY on tickets only.`n`n" + $trailer)
Git-Out $wt @('commit', '-q', '-F', $message) | Out-Null
Remove-Item -LiteralPath $message

Write-Host '== 2 commit P-1 config and P-2 policy in the worktree'
Git-Out $wt @('add', '--', $configPath, $policyPath) | Out-Null
$message = Write-Message ("chore: auto-core T2 deploy P-1 config and P-2 policy (decide compare 5 days, 07:45, GRID, Q2 b, Q4 a; PWR, LITE)`n`n" +
    "workspace/policies/auto_core.json per docs/claude/redesign-t2-policy-proposals.json P-1 and the user decision of " +
    "2026-10-12 11:21 KST: Q2 b -> reissue_buy_cap_not_above_first false, Q3 c -> no size or count keys, " +
    "Q4 a -> research_only_strong_r_cap 1/2. stock-strategy-system/alert_policy.json per P-2: nominal_multipliers PWR 1, " +
    "LITE 1 and card_stock_core + PWR, LITE (product approval 2026-10-08). Applied by Cowork after the user's approval " +
    "(docs/claude/redesign-t2-merge-decision-2026-10-12.md).`n`n" + $trailer)
Git-Out $wt @('commit', '-q', '-F', $message) | Out-Null
Remove-Item -LiteralPath $message
if (@(Git-Out $wt @('status', '--porcelain')).Count -gt 0) { throw 'STOP WORKTREE_NOT_CLEAN_AFTER_COMMITS' }

Write-Host '== 3 merge into the main checkout'
$message = Write-Message ("Merge worktree-t2-core: redesign T2 auto-core decide (compare mode)`n`n" +
    "User decision 2026-10-12 11:21 KST: Q1 a, Q2 b, Q3 c, Q4 a, P-1 and P-2 applied.`n`n" + $trailer)
& git -C $repo merge --no-ff -q -F $message $branch
$mergeCode = $LASTEXITCODE
Remove-Item -LiteralPath $message
if ($mergeCode -ne 0) { throw 'STOP MERGE_FAILED: nothing else was done. Run  git merge --abort  and send this output to Cowork.' }

Write-Host '== 4 checks (main checkout)'
Push-Location $repo
try {
    $schema = @(& python manage-us-stock-strategy/scripts/validate_schema_contracts.py)
    if ($LASTEXITCODE -ne 0 -or -not ($schema -match '"status": "PASS"')) { $schema | Select-Object -Last 5 | Out-Host; throw 'STOP SCHEMA_AUDIT_FAILED' }
    Write-Host 'OK  schema audit PASS'
    $config = @(& python -c "import sys; sys.path.insert(0, 'manage-us-stock-strategy/scripts'); import auto_core_reconcile as c; cfg, r = c.load_config(); print('CONFIG_OK' if cfg and not r and cfg.get('decision_mode') == 'compare' else 'CONFIG_BAD ' + str(r))")
    if (($config -join ' ') -notmatch 'CONFIG_OK') { $config | Out-Host; throw 'STOP CONFIG_CHECK_FAILED' }
    Write-Host 'OK  auto_core.json valid, decision_mode compare'
    foreach ($pattern in @('test_auto_core*', 'test_portfolio_exposure*', 'test_run_portfolio_exposure_review*', 'test_portfolio_review_journal*', 'test_decision_journal_cards*')) {
        $out = @(cmd /c "python -m unittest discover -s manage-us-stock-strategy/tests -p $pattern 2>&1")
        $code = $LASTEXITCODE
        $tail = ($out | Select-Object -Last 3) -join ' '
        Write-Host ('{0}  {1}  {2}' -f $(if ($code -eq 0) { 'OK ' } else { 'BAD' }), $pattern, $tail)
        if ($code -ne 0) { $out | Select-Object -Last 40 | Out-Host; throw "STOP TESTS_FAILED: $pattern (merged, tasks not registered)" }
    }
} finally {
    Pop-Location
}

Write-Host '== 5 register the auto-core tasks'
$register = Join-Path $repo 'manage-us-stock-strategy\scripts\register_auto_core_task.ps1'
& $register
if ($LASTEXITCODE -ne 0) { throw "STOP REGISTER_FAILED: exit $LASTEXITCODE (merged, tasks not registered)" }
foreach ($name in @('InvestmentV2-AutoCore', 'InvestmentV2-AutoCoreDecide')) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($null -eq $task) { throw "STOP TASK_MISSING: $name" }
    $info = $task | Get-ScheduledTaskInfo
    Write-Host ('OK  {0}  state={1}  next={2}' -f $name, $task.State, $info.NextRunTime)
}

Write-Host '== done'
& git -C $repo log --oneline -4
Write-Host 'T2_MERGE_DONE'
