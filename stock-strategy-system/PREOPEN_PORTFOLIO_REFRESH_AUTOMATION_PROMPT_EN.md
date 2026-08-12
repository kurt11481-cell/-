# Pre-Open Portfolio Risk Refresh

Use `$manage-us-stock-strategy` from
`E:\사업\##금동한\코덱스저장소` on committed `main` only.

Run the read-only `PRE_OPEN_DELTA_REFRESH` for the upcoming verified U.S.
regular session. Load the latest immutable post-market baseline and report.
Validate the baseline session, report hash, manifest hash, commit, strategy and
policy versions, and generation time before using it.

Before reading the baseline, run the installed-Skill deployment validator
against `alert_policy.json`, the committed canonical Skill, and the installed
Codex Skill directory. A hash/status mismatch returns `DATA_INCOMPLETE`; do not
refresh execution eligibility or mark delivery successful.

Refresh only authoritative overnight events, indicative premarket quotes, and
an optional fresh verified read-only broker state. Premarket prices never enter
completed-session OHLCV; never confirm EMA/ATR/RVOL, breakout, or daily volume;
never create `HARD_RISK_BREACH`; never upgrade WATCH from price alone. A quote
below a configured loss boundary is `PREMARKET_RISK_WATCH` only.

Use approved event/gap/liquidity rules only. With no approved gap rule, report
`GAP_CONTEXT_ONLY`. Run bounded role-separated research only for a material
official overnight event, a materially changed counter-case, or an explicit
user request. Preserve the underlying post-market Opportunity and Strategy
states while showing separate Pre-Open Readiness and refreshed Execution State.

Fresh fully verified broker cash may re-evaluate a prior cash block. The task
must never invent broker facts, projected proceeds, quantity, or an order. A
global premarket outage creates one deduplicated incident; one ticker failure
blocks only that ticker.

Write a compact delta report, PRE_OPEN run manifest, and non-broker runtime
artifact below `workspace/outputs/preopen-refresh/<SESSION>/`. If unchanged,
return `NO_MATERIAL_PREOPEN_CHANGE`; do not repeat the full post-market report.
Hash portfolio state before and after and require equality. Return the
conclusion first in Korean and explicitly state that no brokerage order was
placed or scheduled.
