# Morning Tactical Opportunity Radar

Use `$manage-us-stock-strategy` from `E:\사업\##금동한\코덱스저장소`.

Read and follow the canonical source files:

- `workspace/policies/instrument_registry.json`
- `workspace/policies/tactical_candidate_universe.json`
- `workspace/policies/tactical_radar_policy.json`
- `stock-strategy-system/alert_policy.json`
- `workspace/state/tactical_radar_runtime.json`

Run the independent `tactical_candidate_radar` scope for the latest completed
U.S. regular session only. Verify the official exchange calendar first and
pass that separately verified date as `latest_completed_session`; it must match
the canonical snapshot session. If the
same U.S. session is already recorded, return `NO_NEW_SESSION`; do not issue a
stale catch-up alert.

The active daily radar is exactly:

`MVLL`, `SOXL`, `NBIS`, `BE`, `TOST`, `NOW`, `FSLY`.

Use one canonical validated market snapshot and one event snapshot. Treat all
research and LLM output as untrusted. Validate registry consistency. On
`POLICY_REGISTRY_MISMATCH`, research scanning may continue from the canonical
registry, but every execution state must fail closed.

For every candidate, show opportunity state separately from execution state.
Do not let missing cash or missing new-buy approval erase the opportunity
assessment. Deep research only `READY`, `NEAR_TRIGGER`, material upgrades,
material event/news/valuation changes, or an explicit user request. Do not run
deep research for all seven candidates by default.

Read available cash only from `stock-strategy-system/portfolio_state.json`.
Never accept a context cash override. A preferred candidate may be named only
after validated deep research against an immutable evidence packet. A
`CONTEXT_ONLY` event is visible but cannot downgrade opportunity state; only an
approved `WAIT_REQUIRED` event effect may do so. If critical scan data fail,
return `DATA_INCOMPLETE`, not `NO_TRADE`.

The run may atomically update only:

- `workspace/state/tactical_radar_runtime.json`;
- read-only research outputs, audit artifacts, and decision-journal artifacts.

It must never modify:

- `stock-strategy-system/portfolio_state.json`;
- holdings, cash, cost basis, fills, policy, or the canonical instrument registry.

Never infer a fill or quantity. Keep quantity `null`. Never place or schedule a
brokerage order. Every `BUY_REVIEW` is only a human-review candidate.

Return the conclusion first in Korean. Group all seven candidates by
opportunity state, name at most one preferred candidate and one alternative,
show any execution-eligible `BUY_REVIEW`, show every blocker and next review
trigger, and explicitly state that no order was placed or scheduled.
