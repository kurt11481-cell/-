# Capital Redeployment

## Purpose

Compare the best review use of verified capital among a new tactical position,
an add to a verified existing holding, and `KEEP_CASH`. The engine uses ordered
gates and portfolio constraints; it does not create a universal investment
score or force deployment.

## Funding buckets

Keep these amounts separate:

1. `verified_available_cash`: cash explicitly verified in canonical portfolio
   state and usable for an execution review.
2. `projected_sale_proceeds`: hypothetical gross proceeds from a valid
   reduction/exit review with an approved deterministic quantity and validated
   completed-session price.
3. `unsettled_or_unconfirmed_proceeds`: reported or proposed proceeds that are
   not verified as available cash.

Only verified available cash is execution purchasing power. Never sum projected
or unsettled proceeds into that amount.

Projected proceeds require verified holding quantity, a valid reduction/exit
review, deterministic quantity authority, validated completed close, and no
unresolved corporate action. Label them
`PROJECTED_ONLY_NOT_AVAILABLE_CASH_NO_FILL_CONFIRMED`. If cost, slippage, and tax
assumptions are not approved, show gross proceeds and `ASSUMPTION_REQUIRED`.

Before a fill, a projected redeployment scenario is
`UNFUNDED_PROJECTED_PLAN`. It cannot unlock a buy, create quantity, modify
portfolio state, or assume execution. After explicit fill confirmation or a
verified read-only broker snapshot, rebuild the entire review from the new
canonical state; do not promote the old projection to cash.

## Candidate pool and comparison

New-position candidates come only from the exact active tactical universe:

`MVLL`, `SOXL`, `NBIS`, `BE`, `TOST`, `NOW`, `FSLY`.

Existing-add candidates must be verified current holdings in `ADD_REVIEW` or,
for comparison where policy permits, `ADD_ON_WATCH`. `KEEP_CASH` is always
present. Inactive watchlist names are not discovered or approved here.

Compare evidence, thesis, valuation, technical entry, event risk,
risk/liquidity, portfolio overlap, concentration, effective leverage, cash
buffer, and correlated drawdown risk. Leveraged instruments also require daily
reset/path-dependence, confirmation proxy, gap risk, and effective portfolio
leverage review. Existing adds are not presumed safer; new positions are not
presumed better diversification.

Name at most one preferred and one alternative use only when ordered gates
support that distinction. `KEEP_CASH`, `NO_VERIFIED_FUNDING`, and
`UNFUNDED_PROJECTED_PLAN` are valid outcomes. Every result remains a human
review with `order_authority=false`.
