# Tactical Candidate Selection

## Scope

Use this workflow to rank user-approved research candidates without converting
watchlist inclusion into permission to buy. Keep tactical selection separate
from strategic allocation, recurring alerts, and brokerage state.

## Two-stage process

### Stage 1: deterministic or light screen

Screen the registered tactical universe with point-in-time inputs only:

- exact identity and registry status;
- watchlist approval;
- data availability and completed-session integrity;
- upcoming verified material events, event coverage quality, and reproducible
  sessions or time remaining;
- minimum liquidity and tradability evidence;
- corporate-action, gap, and halt flags;
- high-level thesis relevance;
- current valuation availability;
- technical regime availability;
- verified leverage factor when leverage arithmetic is needed;
- portfolio overlap and concentration inputs.

Missing held-symbol evidence is not a screening failure; it is a portfolio data
failure under the active policy. Missing watch-only evidence removes only that
candidate from the current shortlist.

### Stage 2: bounded deep research

Keep four machine-readable collections separate:

- `screen_survivors`: every active candidate that passed the light screen;
- `deep_research_shortlist`: normally three to five decision-relevant
  candidates, but fewer are valid when gates allow fewer;
- `deep_research_completed`: only candidates whose bounded analyst workflow
  completed against the immutable evidence bundle;
- `deep_research_skipped`: every other active candidate with a machine-readable
  reason.

Set `shortlist_below_target_due_to_gates=true` rather than filling the list
with weak candidates. Run full role-separated research only for `READY`,
`NEAR_TRIGGER`, a material opportunity upgrade, a material news/event/valuation
change, or an explicit user request. Do not run the full analyst graph for every
universe member. Preserve the screen cutoff and rejected reasons so the
shortlist can be reproduced.

## Candidate lanes

Keep independent lanes:

- `leveraged_semiconductor`: MVLL and SOXL, evaluated with verified daily-reset
  leverage and their approved non-leveraged confirmation proxies;
- `ai_infrastructure`: NBIS and BE;
- `user_defined_ai_agent`: TOST, NOW, and FSLY as initial exploratory
  candidates. Theme tags describe research organization only and are not
  claims about revenue purity.

Do not compare a leveraged ETF and an ordinary stock as if they shared the same
risk, valuation, or holding-period assumptions. Compare within a lane first,
then perform portfolio-fit review across lanes.

## Ordered gates

Apply these ordinal gates:

1. `evidence`: `PASS`, `CONDITIONAL`, or `FAIL`;
2. `thesis`: `STRONG`, `CONTESTED`, `WEAK`, or `UNVERIFIED`;
3. `valuation`: `ATTRACTIVE`, `FAIR`, `STRETCHED`, or `UNVERIFIED`;
4. `technical`: `READY`, `WATCH`, `INVALID`, or `UNAVAILABLE`;
5. `event_risk`: `CLEAR`, `KNOWN_EVENT`, or `EVENT_DATA_INCOMPLETE`;
6. `risk_liquidity`: `ACCEPTABLE`, `CONSTRAINED`, or `VETO`;
7. `portfolio_fit`: `FITS`, `CONSTRAINED`, or `BLOCKED`.

Never average these labels into a master score. A later strong gate cannot
offset an earlier failure. Use [scoring-calibration.md](scoring-calibration.md)
for comparison and calibration.

## Selection output

For every active candidate, expose an opportunity state and an independent
execution state. Opportunity states are `READY`, `NEAR_TRIGGER`, `WATCH`,
`NOT_READY`, and `DATA_BLOCKED`. Execution states are
`ELIGIBLE_FOR_REVIEW`, `WATCH_ONLY`, `NOT_APPROVED`, `CASH_BLOCKED`,
`PORTFOLIO_BLOCKED`, and `DATA_BLOCKED`.

Missing cash or missing new-buy approval must not erase a high-quality
opportunity state. Keep quantity `null` unless separate explicit authority
exists. A `READY` opportunity with no new-buy approval is `NOT_APPROVED`; a
`READY` opportunity with explicit instrument approval but unavailable cash is
`CASH_BLOCKED`. Neither is an order.

`NEAR_TRIGGER` may reference only conditions already approved by the technical
policy, such as a validated EMA reclaim, breakout acceptance, pullback
confirmation, event clearance, valuation refresh, or evidence refresh. Do not
invent a new price or indicator threshold inside the radar.

Return at most one preferred candidate and one alternative. Both remain review
candidates, require validated bounded deep research, and must state:

- lane and exact ticker;
- watchlist and new-buy approval status separately;
- passed, conditional, and failed gates;
- evidence cutoff;
- next material event, source, event time, coverage status, and policy effect;
- strongest counter-case;
- valuation and technical conditions still required;
- objective invalidation;
- why `WAIT` remains valid.

When no candidate clears every required gate, the portfolio conclusion may be
`WAIT` or `NO_TRADE`, while all seven dispositions remain visible. If the scan
failed because data are incomplete, return `DATA_INCOMPLETE`, never
`NO_TRADE`. Do not force turnover or a bullish selection.

For securities not verified as held, never emit a sell-side review. Without
explicit short approval, never emit a short thesis as an action.

## Registry and policy

Read the workspace tactical-universe and canonical instrument-registry files
explicitly. `workspace/policies/instrument_registry.json` is the only canonical
research authority. Any embedded policy registry is a non-authoritative
operational cache and must match the referenced canonical hash. On
`POLICY_REGISTRY_MISMATCH`, research scanning may continue from the canonical
registry while execution review fails closed.
Do not infer leverage from a ticker. A null or unverified factor is unavailable
for effective-leverage arithmetic. Preserve existing approved values and fail
closed when registry entries conflict with the active deterministic policy.
