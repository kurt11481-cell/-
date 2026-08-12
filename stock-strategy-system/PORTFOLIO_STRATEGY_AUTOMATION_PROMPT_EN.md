# Morning Portfolio Strategy

Use `$manage-us-stock-strategy` from
`E:\사업\##금동한\코덱스저장소` on committed `main` only.

Run the read-only `portfolio_strategy_orchestrator` workflow for the latest
completed U.S. regular session:

Official Session Gate
-> Canonical Market Snapshot
-> Event Snapshot
-> Verified Portfolio State
-> Held-Position Risk Review
-> Holding Strategy Review
-> Tactical Opportunity Radar
-> Cash/Funding Classification
-> Capital Redeployment Review
-> Morning Portfolio Strategy Report

Read the operational sources of truth before any market-data work:

- `stock-strategy-system/portfolio_state.json`
- `stock-strategy-system/alert_policy.json`
- `stock-strategy-system/alert_runtime_state.json`
- `workspace/policies/instrument_registry.json`
- `workspace/policies/tactical_candidate_universe.json`
- `workspace/policies/tactical_radar_policy.json`
- `workspace/state/tactical_radar_runtime.json`
- `workspace/state/holding_strategy_runtime.json`

Follow the event-risk, provider-resilience, point-in-time, reproducibility,
holding-strategy, capital-redeployment, portfolio-policy, and alert-automation
references bundled with the Skill. Use one canonical validated market snapshot
and one event snapshot across all roles and engines. Verify the official latest
completed session separately and reject stale catch-up processing.

Every verified positive holding must receive one strategy state. Preserve hard
maximum-loss precedence and exact deterministic tranche provenance. Default
quantity to `null`; never infer, round, or substitute a quantity. Missing current
holding research normally requires `STRATEGY_REFRESH_REQUIRED`, not reuse of an
old chat conclusion.

Show all seven tactical candidates exactly:

`MVLL`, `SOXL`, `NBIS`, `BE`, `TOST`, `NOW`, `FSLY`.

Opportunity state is independent of cash and execution state. A valid `READY`
or `NEAR_TRIGGER` opportunity must remain visible when cash is zero, approval is
missing, or a held hard-risk freeze blocks execution.

Keep funding categories separate:

- verified available cash;
- projected sale proceeds;
- unsettled or unconfirmed proceeds.

Only verified available cash from canonical portfolio state may satisfy a buy
execution gate. Projected proceeds require deterministic quantity authority and
a validated completed-session reference price; label them projected only and
never add them to execution purchasing power. Do not infer a fill.

Routine automation may atomically update only monitoring runtime/dedup metadata
and write research, audit, run-manifest, and report artifacts below
`workspace/outputs/portfolio-strategy/<SESSION>/`. It must never modify portfolio
state, holdings, cash, average cost, fills, timing anchors, policy, source code,
or the instrument registry.

If held-position data fail, return held `DATA_BLOCKED` without erasing valid
tactical research. If tactical cross-checks fail, return tactical
`DATA_BLOCKED`, not `NO_TRADE`. Keep incomplete event coverage visible. A safe
`WAIT`, `DATA_INCOMPLETE`, `NO_VERIFIED_FUNDING`, or
`UNFUNDED_PROJECTED_PLAN` is valid.

Return the conclusion first in Korean. Show critical risk, every current
holding, all seven tactical dispositions, the three funding categories,
preferred/alternative/keep-cash capital uses, and final human-review items.
Explicitly state that no brokerage order was placed or scheduled.
