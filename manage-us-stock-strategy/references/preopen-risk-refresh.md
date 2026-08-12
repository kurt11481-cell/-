# Pre-Open Risk Refresh

## Purpose and authority

The PRE_OPEN phase answers whether the latest immutable post-market strategy is
still safe for human review before the upcoming regular-session open. It does
not rebuild daily strategy and cannot place an order, create quantity, or
mutate portfolio or policy state.

The post-market baseline is authoritative for completed-session EMA, ATR, RVOL,
breakout acceptance, Opportunity State, Strategy State, and hard-risk results.
Validate its session, report hash, run-manifest hash, commit, strategy version,
policy version, and generation time. Missing or invalid baseline fails closed.

## Premarket limitations

Premarket quotes are indicative. Keep them outside completed-session OHLCV.
They cannot confirm a daily EMA reclaim, daily volume, breakout, ATR/RVOL, or a
completed-close hard-risk breach. A quote below a configured cost-loss boundary
is `PREMARKET_RISK_WATCH` only.

Readiness states are `CLEAR`, `CAUTION`, `RESEARCH_REFRESH_REQUIRED`,
`GAP_INVALIDATED`, `EVENT_BLOCKED`, `LIQUIDITY_BLOCKED`, and
`DATA_INCOMPLETE`. Keep the underlying post-market strategy/opportunity visible
beside the readiness result.

## Allowed changes

Pre-open may maintain or downgrade execution, request bounded research after a
validated official overnight event, or re-evaluate a cash block after a fresh
verified broker-state update. It may never upgrade WATCH from price alone. A
gap or liquidity block requires an already approved rule; absent such a rule,
report `GAP_CONTEXT_ONLY` or liquidity context only.

Check only authoritative events published or effective after the post-market
cutoff and before the pre-open cutoff. Social or aggregator content cannot
create an authoritative event. Material evidence may require refresh but cannot
create an order.

## Output, dedup, and automation

Emit a PRE_OPEN report and run manifest with baseline/session hashes, provider
health, event changes, broker status, per-ticker readiness, refreshed execution,
remaining conditions, and null quantity. Include `run_phase` in dedup keys.
Aggregate global provider outages and isolate ticker failures. If nothing
material changed, return `NO_MATERIAL_PREOPEN_CHANGE` rather than repeating the
full post-market report.
