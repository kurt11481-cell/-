# Holding Strategy Orchestration

## Purpose and authority

This layer answers what strategy should be reviewed for each verified positive
holding. It reads `stock-strategy-system/portfolio_state.json` as the only
operational portfolio source and consumes existing deterministic risk and
technical results. It never calculates a second stop, infers a holding or fill,
changes cash, selects an unauthorized quantity, or places an order.

Authority order remains:

`state/data integrity -> hard risk -> approved stop/timing review -> qualitative reduction/exit -> hold/add -> new opportunity -> verified cash -> human review`.

## State model

Every verified positive holding receives exactly one strategy state:

- `HOLD`: validated evidence does not justify a portfolio-changing review.
- `ADD_ON_WATCH`: the holding case remains valid, but an observable entry or
  event condition is pending.
- `ADD_REVIEW`: validated thesis, valuation, technical entry, event, risk, and
  portfolio-fit gates support a human add review.
- `REDUCTION_REVIEW`: validated risk, thesis, valuation, technical, or portfolio
  evidence supports partial-reduction review.
- `EXIT_REVIEW`: validated thesis invalidation or an applicable severe existing
  risk mechanism supports full-exit review.
- `STRATEGY_REFRESH_REQUIRED`: the holding is verified but current thesis,
  valuation, or issuer evidence is stale or incomplete.
- `DATA_BLOCKED`: critical state, holding, identity, market, technical, or event
  inputs prevent a reliable review.

Strategy state is separate from execution eligibility:

`ELIGIBLE_FOR_REVIEW`, `HUMAN_REVIEW_REQUIRED`, `WATCH_ONLY`, `CASH_BLOCKED`,
`POLICY_BLOCKED`, `PORTFOLIO_BLOCKED`, `VERIFICATION_PENDING`, `DATA_BLOCKED`,
or `NOT_APPLICABLE`.

Cash and approval constraints may downgrade execution eligibility, but they must
not erase a valid strategy state. A zero-cash `ADD_REVIEW` remains visible as
`ADD_REVIEW / CASH_BLOCKED`.

## Evidence and refresh

No holding strategy may be based only on current profit/loss, one moving
average, one LLM opinion, radar status, or chat memory. A current validated
research context must retain evidence-packet validation, deterministic-gate
status, risk-controller status, a research-packet hash, claims, counter-case,
invalidation, and review trigger. Otherwise return
`STRATEGY_REFRESH_REQUIRED` unless higher-priority deterministic risk or data
failure controls the state.

Use the existing role-separated research pipeline for a refresh. Deep research
is bounded to stale strategy, material thesis/news/event changes, material risk
changes, possible add reviews, qualitative reduction/exit cases, or explicit
user requests. Routine `HOLD` monitoring does not trigger full research daily.

## Quantity and hard risk

Default `quantity=null` and `quantity_authority=none`. An exact quantity may be
carried only from a currently approved deterministic holding-timing result, with
`policy_rule_id`, `tranche_id`, and `trigger_path`. Research cannot create,
round, or alter it.

A valid grade-D maximum-loss review is never hidden by bullish research,
redeployment benefits, or a tactical `READY` candidate. It remains an unsized
human review and freezes new-buy execution under current policy while preserving
opportunity visibility.

## Runtime and outputs

`workspace/state/holding_strategy_runtime.json` stores monitoring metadata only:
last session, prior state, fingerprint, deep-research session, and delivery IDs.
It never stores brokerage holdings, cash, cost basis, or fills. Only material
state transitions generate urgent delivery candidates. Reflection may record a
lesson but cannot mutate policy or portfolio state.

## v2.4 risk and strategy separation

Store `holding_risk_state` separately from `strategy_state`. Risk values are
`NO_HARD_RISK`, `HARD_RISK_WATCH`, `HARD_RISK_BREACH`,
`POLICY_AUTHORITY_UNVERIFIED`, and `DATA_BLOCKED`. A completed-close breach may
map to `EXIT_REVIEW` or `REDUCTION_REVIEW` only when the exact rule provenance
and `action_on_breach` approval both pass. Otherwise retain the warning, set
`STRATEGY_REFRESH_REQUIRED`, require human review, and leave quantity null.

Expose primary-close, independent-close, policy-approval, rule-ID,
average-cost, execution, and quantity authority independently. Premarket quotes
may create only `PREMARKET_RISK_WATCH`; they cannot create a completed-session
hard-risk breach.

## v2.5 selective price evidence

Routine `HOLD` and `ADD_ON_WATCH` do not require daily independent acquisition.
`ADD_REVIEW`, `REDUCTION_REVIEW`, `EXIT_REVIEW`, and hard-risk boundaries enter
the queue. A primary completed-close warning survives independent evidence that
is pending or conflicting. Report `primary_close_status`,
`independent_close_status`, `policy_authority_status`, and
`action_on_breach_authority` separately. Without verified action authority,
never convert the warning into an automatic exit/reduction or quantity.
