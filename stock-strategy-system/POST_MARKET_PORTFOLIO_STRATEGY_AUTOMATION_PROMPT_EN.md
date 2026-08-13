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

Use yfinance as the primary full-universe completed-daily collector. Reuse one
canonical completed-session market snapshot and one event snapshot. Do not
require Massive credentials, Massive MCP, or another structured provider for
startup. Do not register Codex Web as a structured market-data provider.

Build research and new-buy strategy drafts before independent-close
acquisition. Preserve `READY` and `NEAR_TRIGGER` opportunity quality when
independent evidence is unavailable; keep execution at
`VERIFICATION_PENDING`. Build the deterministic selective price-evidence queue.
An empty queue is `NOT_REQUIRED` and performs no Web acquisition. For a
non-empty queue, select only an exact route from
`workspace/policies/web_completed_close_route_registry.json`, open the original
source page (never a search snippet or Yahoo-origin page), write untrusted Web
evidence, then run deterministic evidence and numerical validators. A route or
evidence failure is ticker-local unless the common market/session authority
failed. Never substitute a second Yahoo endpoint as an independent close and
never turn unavailable Web evidence alone into `NO_TRADE`.

Produce every verified holding's separate Risk State and Strategy State, the
seven-symbol Tactical Radar (`MVLL`, `SOXL`, `NBIS`, `BE`, `TOST`, `NOW`,
`FSLY`), strict Cash Status, capital-redeployment review, immutable post-market
baseline, and validated POST_MARKET run manifest. Preserve opportunity quality
when cash or execution approval is blocked.

Apply 1/5/10/20/60 promotion only through exact ticker, decision-class, and
source-route scope. Historical route acceptance does not count as an
operational Shadow session. No stage auto-promotes, and every human-review
entitlement requires an explicit user approval reference. Web `MATCH` changes
only price evidence; it never approves an instrument, risk budget, maximum-loss
rule, quantity, or order.

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
