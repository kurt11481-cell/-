# Technical Strategy and Risk Planning

For deterministic buy, take-profit, staged-reduction, stop, or 10/20-EMA
timing, also read [trade-timing-validation.md](trade-timing-validation.md).
Build the completed-session snapshot with `scripts/build_market_snapshot.py`,
verify the official exchange session, and run
`scripts/validate_technical_snapshot.py` before interpreting any indicator.
The validator checks calculation consistency and provenance; it does not turn
an unapproved rule, quantity, or instrument into an actionable candidate.
For yfinance collection settings, request pacing, and provider-failure handling,
follow [yfinance-data.md](yfinance-data.md).

## Require usable data

Use verified OHLCV data with the exchange timezone and the last completed bar. Use split-adjusted history for indicators and total-return calculations, but use executable raw prices for entry, stop, and limit ranges. Flag corporate actions that can distort indicators.

Treat yfinance as an unofficial collection layer, not an authoritative signal
source. Keep `auto_adjust=False`, `prepost=False`, and `threads=False`; request
symbols sequentially with at least one second between external calls. Compute
all technical indicators locally, record formula and provider versions, and
cross-check the completed raw close with a timestamped source independent of
Yahoo Finance.

If the user provides only a screenshot, report only values that are legible. Do not reconstruct exact indicators from pixels.

## Analyze in this order

1. Weekly and daily higher-high/higher-low structure
2. Regime: uptrend, downtrend, range, volatility contraction, breakout attempt, or failed breakout
3. Price acceptance around prior highs/lows and gaps
4. Volume-price behavior and closing location
5. Moving-average direction and spacing
6. Volatility and gap risk
7. Momentum indicators in trend context
8. Option positioning only as secondary evidence

Do not call volume `institutional accumulation` or `distribution` as fact. Use `possible accumulation`, `possible distribution`, `acceptance`, `rejection`, or `increased selling pressure`.

## Use indicators carefully

- Calculate 10EMA and 20EMA from the same split/distribution-adjusted daily
  close series normalized to the latest raw-close scale. Use the raw completed
  regular-session close for executable levels and average-cost loss boundaries.
- Interpret `10EMA > 20EMA` only as short-term trend alignment. Require price
  acceptance, EMA slope, volatility, and a defined invalidation before using it
  for timing.
- RSI above 70 is not an automatic sell; RSI below 30 is not an automatic buy.
- Stochastic and Bollinger Band touches are contextual, not buttons.
- Use the user's configured parameters. If none exist, disclose conventional defaults rather than pretending they are optimal.
- Mention chart patterns or Elliott Wave only when the structure is clear. Never force a count.
- Express support and resistance as zones with evidence, not exact guaranteed levels.

### Keep the active signal set small

Do not add an indicator to a live timing rule because it improves one recent
sample. Pre-register a one-at-a-time ablation and require a multi-regime
walk-forward result before activation. Until that evidence exists, use this
role map:

- EMA10/EMA20: active short-trend and reclaim context. For SOXL, a 10EMA
  weakness condition alone is observation-only and cannot consume a reduction
  slot.
- SMA200 and its slope on the non-leveraged confirmation proxy: preferred
  long-regime filter for future entry/re-entry research.
- SMA50 or SMA60: alternative medium-regime filters; never count both as
  independent votes.
- SMA20 and MACD(12,26,9): strongly overlap EMA trend. Test as alternatives,
  not extra confirmations.
- RVOL20: an orthogonal volume-confirmation candidate. Exclude the signal
  session from its denominator and reject unadjusted early-close comparisons.
- Stochastic(20,3,3): at most a future re-entry filter; never a standalone
  buy or sell.
- Chaikin Oscillator(3,10): low-priority research only. ETF volume and the
  oscillator do not prove institutional accumulation or distribution.

The default minimal research set is EMA10/EMA20, confirmation-proxy SMA200 and
slope, ATR14, RVOL20, and prior price structure. Keep every additional vote
inactive unless it independently passes the approved out-of-sample gate.

### Treat peak, time, gap, and halt risk separately

- A prospective peak-to-close drawdown rule needs an explicit high-water-mark
  anchor. A partial reduction does not reset the remaining lot's high-water
  mark; a confirmed re-entry receives a separate anchor.
- A time stop applies only to a future confirmed entry or re-entry with a
  versioned planned `R`. Never reconstruct it retrospectively for an existing
  holding.
- A gap through a review level uses the first tradable regular-session price;
  never assume execution at the stop.
- An explicit halt, suspension, or missing tradable OHLCV freezes the candidate.
  Zero volume alone is not proof of a halt.

## Build a trade-review candidate

State the intended holding horizon first. If the user did not specify one, keep long-horizon accumulation and short-horizon trading as separate alternatives rather than blending them.

State:

- setup and intended holding horizon;
- entry zone and required confirmation;
- invalidation zone and why the thesis fails there;
- first and second target zones with evidence;
- gap, halt, slippage, earnings, and liquidity risk;
- time stop, if relevant to the strategy;
- add and trim conditions;
- expected reward-to-risk from stated prices.

Treat a minimum reward-to-risk threshold, position-risk percentage, and time stop as configurable strategy settings. If no setting exists, present the calculation without declaring universal approval.

Use the position-sizing formula only when total capital and allowed loss are known:

`shares = floor((capital * allowed_risk_fraction) / abs(entry - stop))`

Apply post-trade exposure caps and liquidity constraints. A stop does not guarantee the loss because gaps and halts can bypass it.

Do not upgrade a setup above `Wait` when evidence integrity, business-thesis validity, or current valuation has not passed. Technical confirmation chooses timing; it does not repair an unverified thesis or an unjustified valuation.

## Validate prior analysis

Classify a prior call as:

- Confirmed: the predefined condition occurred;
- Failed: the predefined invalidation occurred;
- Pending: neither occurred;
- Revised: the directional thesis remains possible but the price structure changed.

Use the conditions written before the outcome. Do not move targets or stops retrospectively without recording the revision.

## Default output

1. Decision summary
2. Data status and completed session
3. Weekly and daily regime
4. Volume and volatility evidence
5. Support, resistance, and invalidation zones
6. Bull, neutral, and bear confirmation conditions
7. Candidate entry/stop/targets and reward-to-risk
8. Position-sizing inputs still required
9. Reasons to wait or reject the setup
