# Kiwoom Session-Aware Guarded Priority

## Purpose

Use Kiwoom as the operationally prioritized market-data source for the user's
Kiwoom brokerage context without misrepresenting every Kiwoom field as a
consolidated or official U.S. auction close. yfinance remains a diagnostic
Shadow and scoped fallback. Codex Web is restricted to unresolved,
decision-changing, comparable, finalized regular-close conflicts.

This contract never grants order, fill, quantity, portfolio-mutation, or policy
authority.

## Authority by data role

- Explicitly confirmed or verified read-only Kiwoom account facts:
  `KIWOOM_AUTHORITATIVE`.
- Kiwoom broker-observable live quote:
  `KIWOOM_OPERATIONAL_PRIMARY`.
- Archived and finalized Kiwoom raw regular daily close:
  `KIWOOM_REGULAR_CLOSE_PRIMARY_WHEN_FINALIZED`.
- Validated Kiwoom adjusted completed-daily history:
  `KIWOOM_ADJUSTED_LOCAL_DETERMINISTIC_SCOPED`.
- yfinance:
  `YFINANCE_DIAGNOSTIC_SHADOW`, with only the explicitly recorded ticker-local
  fallback scopes.
- Codex Web:
  `CODEX_WEB_ORIGINAL_SOURCE_COMPARABLE_FINALIZED_REGULAR_CLOSE_ONLY`.

Never call a Kiwoom field `OFFICIAL_EXCHANGE_AUCTION_CLOSE` without exact
official source evidence for that field.

## Session and quote normalization

Every observation must retain its ticker, provider, market-session type,
reported session, price basis, quote type, provider timestamp, exchange
timestamp when available, currency, finalization status, stability,
comparability, and `order_authority=false`.

Supported session types are:

- `PRE_MARKET`
- `REGULAR_INTRADAY`
- `REGULAR_COMPLETED`
- `AFTER_HOURS`
- `DAY_MARKET`
- `OVERNIGHT`
- `MARKET_CLOSED`
- `UNKNOWN`

Supported price or quote types include raw regular close, regular last,
premarket/after-hours/day-market/overnight last, bid, ask, mid, broker mark,
and unknown.

Clock time may classify the observation window, but it may not infer the price
basis. In particular, a same-ET-date Kiwoom `usa06012` row has no completed-bar
authority merely because it was retrieved after 16:00 ET. Until a deterministic
finalization rule passes, it is indicative, unstable, and not comparable to a
regular completed close.

## Comparability gate

Apply numerical tolerance only after all of these pass:

1. same canonical ticker and verified security identity;
2. same market-session type;
3. same reported session;
4. same quote type;
5. compatible price basis;
6. USD currency;
7. retrieval timestamps capable of observing the completed close;
8. stable records;
9. finalized daily bars when comparing regular closes.

Failure returns `NOT_COMPARABLE` with a specific reason such as
`NOT_COMPARABLE_SESSION`, `PRICE_BASIS_MISMATCH`, `QUOTE_TYPE_MISMATCH`,
`TIMESTAMP_MISMATCH`, or `FINALIZATION_PENDING`. It is not `CONFLICT`.

After comparability passes, use only the existing approved raw-close tolerance.
Never average provider values. A comparable decision-boundary flip remains a
ticker- and decision-class-local conflict and may enter the Codex Web queue.

## Extended-hours limits

Premarket, after-hours, day-market, and overnight observations may provide gap,
volatility, liquidity, spread, event-response, caution, or readiness-downgrade
context. They may not:

- upgrade `WATCH` to `READY`;
- confirm a completed-session hard-risk breach;
- overwrite the regular completed close;
- enter daily EMA, ATR, RSI, MACD, or RVOL;
- approve an instrument;
- create quantity;
- place or schedule an order.

Store them separately from completed-daily bars.

## Scoped limitations

- FSLY: when Kiwoom history remains below the policy minimum, use one complete
  yfinance technical-history fallback if permitted. Never merge histories or
  lower the minimum.
- MVLL: preserve Kiwoom Raw close authority while isolating unresolved
  `EMA10_RECLAIM_RVOL20` as a decision-class-local technical conflict.
- `EVENT_DATA_INCOMPLETE`: expose `EVENT_REVIEW_PENDING` and block strategy or
  execution where policy requires, but do not invalidate market-provider
  infrastructure.
- Any ticker-specific quote or history failure remains ticker-local when the
  common provider infrastructure is healthy.

## Semantic cohort

Any provider-authority change starts a new operational Shadow cohort at zero.
Preserve the prior cohort as `COHORT_SUPERSEDED`; never backfill replay, manual,
or dry-run sessions. Human approval remains mandatory at every promotion gate.
