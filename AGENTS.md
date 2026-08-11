# Stock Strategy Workspace

Use `$manage-us-stock-strategy` for U.S. stock/ETF research, semiconductor-infrastructure analysis, technical trade planning, option-chain context, portfolio design, and recurring post-market alerts.

Operational files:

- State: `stock-strategy-system/portfolio_state.json`
- Policy: `stock-strategy-system/alert_policy.json`
- Runtime/dedup state: `stock-strategy-system/alert_runtime_state.json`
- Automation prompt: `stock-strategy-system/AUTOMATION_PROMPT_EN.md`

Never place or schedule a brokerage order. Treat every alert as a next-session review candidate. Never infer a fill from price movement; update portfolio facts only from explicit user confirmation or a verified read-only broker snapshot. A scheduled agent may atomically update runtime/dedup metadata, but not portfolio holdings, cash, stage, cost basis, or fills.
