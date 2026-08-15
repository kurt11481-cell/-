# Portfolio Reallocation Shadow

## Purpose and authority

`CAPITAL_REALLOCATION_SHADOW` is a deterministic, hypothetical portfolio
review. It evaluates every verified positive holding through `ADD_CASE`,
`HOLD_CASE`, `TRIM_CASE`, and `EXIT_CASE`, then recompiles the complete
portfolio opportunity set. It grants no order, quantity, fill, cash, or
portfolio-mutation authority.

The holding decision priority is:

`Hard Risk -> Exit/Risk Reduction -> Event Completeness -> Hold -> Add/New Buy`.

A non-breached maximum-loss boundary is not sufficient evidence for `HOLD`.
The engine must also evaluate thesis, valuation, technical, event, risk,
concentration, time-stop, and relative-opportunity inputs that are available
under approved policy.

## Event actionability

Maintain separate readiness for `NEW_BUY`, `ADD`, `HOLD`, `TRIM`, and `EXIT`.
New buys and adds fail closed when material event readiness is insufficient.
Partial non-blocking evidence can retain a holding review. Event incompleteness
alone never vetoes a risk-reducing trim. A verified hard-risk or
thesis-invalidating exit can override event incompleteness while retaining the
evidence limitation in the report.

Use the versioned matrix in
`workspace/policies/portfolio_reallocation_shadow_policy.json`. Do not convert
missing evidence into “no event.” Material categories use only `VERIFIED`,
`NOT_YET_ANNOUNCED`, `NO_NEW_DISCLOSURE_FOUND`, `SOURCE_UNAVAILABLE`, or
`REVIEW_REQUIRED`.

## Post-close ordering

The mandatory order is:

`KIWOOM_COMPLETED_BAR_FINALIZED -> POST_CLOSE_EVENT_REFRESH ->
EVENT_CUTOFF_VALIDATION -> EVENT_BUNDLE_HASH -> HOLDING_STRATEGY_COMPILE ->
PORTFOLIO_REALLOCATION_SHADOW`.

Every decision preserves `decision_as_of`, `market_data_cutoff`, `event_cutoff`,
`broker_cutoff`, and the candidate cutoff when applicable. The event cutoff
must not precede the market-data/strategy cutoff. Evidence later than
`decision_as_of` is rejected.

## Profit protection and action taxonomy

The action taxonomy is `HOLD_CORE`, `HOLD_TIGHTEN_STOP`, `ADD_REVIEW`,
`TRIM_PROFIT`, `TRIM_VALUATION`, `TRIM_TECHNICAL`, `TRIM_CONCENTRATION`,
`TRIM_RISK`, `EXIT_THESIS`, `EXIT_HARD_STOP`, and `ROTATE_REVIEW`.

Profit protection is multi-factor. A fixed unrealized-profit percentage cannot
produce an automatic sale. Until a numeric production rule is explicitly
approved, an upstream deterministic policy result is required. A large profit
with an intact trend and healthy volume may remain `HOLD_TIGHTEN_STOP`.

## Hypothetical proceeds and optimizer

For a trim, the hypothetical ratio and quantity remain null unless an approved
policy or explicitly labelled test scenario supplies ratio authority. A full
thesis or hard-stop exit can use a 100% Shadow ratio. All resulting proceeds
are `SHADOW_ONLY` and never become verified or orderable broker cash.

The optimizer compares existing-holding adds, new-buy reviews, and `KEEP_CASH`
only after hard, risk, event, and portfolio-fit gates. It never creates a hard
`SELL A -> BUY B` link and never lets a numeric score override a blocker.
`SELL_RISK_DECISION` and `BUY_RISK_DECISION` remain separate and require the
independent Risk Kernel in any future execution architecture.

## Cohort and dedup

Portfolio-decision semantics use a separate
`PORTFOLIO_DECISION_SEMANTIC_COHORT`. Start a changed semantic cohort at zero,
without backfill, and preserve scheduler/provider operational counters. Use one
`portfolio_reallocation_cycle_id` to suppress repeated interpretation of the
same event. No production cooldown or hysteresis number is active until
explicitly approved.

## Output and invariants

Every holding output includes all four cases, the selected action, rejected
alternatives, reason codes, event actionability, technical and valuation
conditions, and all ten independent state axes. The portfolio output includes
risk before/after, the hypothetical post-sale portfolio, candidate comparison,
`KEEP_CASH`, turnover/cooldown state, and the best Shadow decision.

Always preserve `execution_quantity=null`, `quantity_authority=none`,
`order_authority=false`, and `portfolio_mutation=false`. Open-order visibility
that is unknown remains unknown. This workflow never changes scheduler timing
or operational-maturity counters.
