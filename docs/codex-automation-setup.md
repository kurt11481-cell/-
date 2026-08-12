# Codex Automation Setup: v2.4 Dual Phase

Use Codex Scheduled Tasks/heartbeat automations only. No Windows Task
Scheduler, service, startup script, cron workaround, or background daemon is
permitted.

## Morning Portfolio Strategy

- Run phase: `POST_MARKET`
- Schedule: Tuesday-Saturday 07:45 `Asia/Seoul`
- Workspace: `E:\사업\##금동한\코덱스저장소`
- Source: committed `main`
- Prompt:
  `stock-strategy-system/POST_MARKET_PORTFOLIO_STRATEGY_AUTOMATION_PROMPT_EN.md`
- Codex automation ID: `automation`
- Configuration status: `FIRST_RUN_PENDING`
- Delivery status: not yet verified

The existing automation was updated in place; no duplicate was created.

## Pre-Open Portfolio Risk Refresh

- Run phase: `PRE_OPEN`
- Schedule: Monday-Friday 08:45 `America/New_York`
- Workspace: `E:\사업\##금동한\코덱스저장소`
- Source: committed `main`
- Prompt:
  `stock-strategy-system/PREOPEN_PORTFOLIO_REFRESH_AUTOMATION_PROMPT_EN.md`
- Configuration status: `NOT_CONFIGURED`
- Delivery status: not verified

The Codex automation API rejected immediate creation with an anchored `DTSTART`
because timezone-specific wall-clock semantics require an explicit suggested
task confirmation. A correctly timezone-anchored task card was rendered in the
app. Accept that card to complete setup; do not replace it with a fixed KST time
because U.S. daylight-saving changes would make the schedule wrong.

Operational result: `CODEX_AUTOMATION_REQUIRES_MANUAL_SETUP` for PRE_OPEN only.

## First-run verification

Configuration never equals delivery success. After each task's first valid run,
verify:

1. output commit/policy versions match committed main;
2. report, runtime, baseline/manifest schemas pass;
3. portfolio-state hashes before and after are identical;
4. no policy/source/registry mutation occurred;
5. `order_authority=false` and quantity remains unauthorized.

Only then may `workspace/state/automation_delivery_runtime.json` move that task
to `DELIVERY_VERIFIED`.

`WINDOWS_TASK_SCHEDULER_INSTALLED = false`.
