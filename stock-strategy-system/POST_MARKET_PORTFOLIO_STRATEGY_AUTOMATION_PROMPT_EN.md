# Post-Market Full Portfolio Strategy

Use `$manage-us-stock-strategy` from
`E:\사업\##금동한\코덱스저장소` on committed `main` only.

Run the read-only `POST_MARKET_FULL_STRATEGY` workflow for the latest verified
completed U.S. regular session. Read the canonical portfolio state, alert
policy/runtime, instrument registry, tactical universe/policy, event policy,
source-capability registry, and monitoring runtimes before analysis.

Before market-data work, run the installed-Skill deployment validator against
`alert_policy.json`, the committed canonical `manage-us-stock-strategy/`, and
the installed Codex Skill directory. A hash/status mismatch is a global
`DATA_INCOMPLETE` failure: stop before market collection and do not update
runtime delivery state as successful.

Run one independent completed-close provider preflight before scanning. Reuse
one canonical completed-session market snapshot and one event snapshot. Keep
global failures separate from ticker failures and aggregate a provider-wide
outage into one incident. Never substitute a second Yahoo endpoint as an
independent close.

Produce every verified holding's separate Risk State and Strategy State, the
seven-symbol Tactical Radar (`MVLL`, `SOXL`, `NBIS`, `BE`, `TOST`, `NOW`,
`FSLY`), strict Cash Status, capital-redeployment review, immutable post-market
baseline, and validated POST_MARKET run manifest. Preserve opportunity quality
when cash or execution approval is blocked.

Only fresh fully verified available broker cash is purchasing power. Zero cash
means `NO_FUNDED_ACTION`, not `KEEP_CASH`. Projected or unsettled proceeds are
never cash. Held Radar names are `EXISTING_HOLDING_ADD`, never duplicate
`NEW_POSITION` entries.

Routine execution may update only runtime/dedup and output artifacts. It must
not mutate portfolio state, holdings, cash, average cost, fills, policy, source
code, or registry. Never create quantity or an order. Hash portfolio state
before and after and require equality.

Write outputs below `workspace/outputs/portfolio-strategy/<SESSION>/`. Update
automation delivery runtime only after schema validation and portfolio hash
verification. Return the conclusion first in Korean and state the commit,
policy version, provider status, subsystem statuses, and that no brokerage
order was placed or scheduled.
