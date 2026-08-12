# Codex Automation Setup: Morning Portfolio Strategy

## Intended configuration

- Name: `Morning Portfolio Strategy`
- Platform: Codex automation/heartbeat only
- Schedule: Tuesday through Saturday at approximately 07:45 `Asia/Seoul`
- Workspace: `E:\사업\##금동한\코덱스저장소`
- Source branch: committed `main`
- Windows Task Scheduler: not installed and prohibited by this design

Use the exact prompt in
`stock-strategy-system/PORTFOLIO_STRATEGY_AUTOMATION_PROMPT_EN.md`.

The combined workflow supersedes a separate morning tactical-only heartbeat for
this task. It does not replace the lower-level deterministic engines; it invokes
or consumes them in authority order. Avoid running both a 07:30 holding-only
heartbeat and a 07:45 tactical-only heartbeat when one combined morning
automation can do both.

## Native automation status

`CODEX_AUTOMATION_CONFIGURED`

The existing heartbeat automation `automation` was updated in place. It is
active Tuesday-Saturday at 07:45 `Asia/Seoul`, targets the existing stock
strategy task, and points to
`stock-strategy-system/PORTFOLIO_STRATEGY_AUTOMATION_PROMPT_EN.md`. No duplicate
heartbeat, cron job, or Windows Task Scheduler task was created.

Notification preferences remain outside the analytical prompt. The first
scheduled production run must still be audited for output-boundary compliance
and byte-identical `stock-strategy-system/portfolio_state.json`.

The first valid run must show all holding strategies, all seven tactical
opportunities, verified cash separately from projected/unconfirmed proceeds,
and `order_authority=false`.
