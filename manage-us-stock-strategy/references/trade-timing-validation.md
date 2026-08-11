# Trade Timing and Evidence Validation

## Contents

1. Authority and activation
2. Data and calculation gate
3. 10EMA and 20EMA regime model
4. Buy setups
5. Take-profit and trailing rules
6. Staged reduction
7. Stop and invalidation
8. Position sizing and portfolio gates
9. Evidence and citation verification
10. Output contract

## Authority and activation

Use this workflow for an actual buy, add, take-profit, trim, staged reduction,
or stop review. Keep research, deterministic policy, and human approval
separate.

- Treat every threshold and tranche as inactive until it appears in an
  approved, versioned policy. The workspace policy
  `2026-08-05-ema-timing-v4` is active for grade-B review candidates only.
- Treat a touched price as a condition observation, never as a fill.
- Emit a next-session review candidate only. Never place or schedule an order.
- The active harness caps deterministic alerts at `B` while its execution adapter
  is disabled. Do not describe a review candidate as an executable order.
- Preserve the existing average-cost maximum-loss boundary as the final hard
  risk constraint. A technical stop may be tighter but never looser.
- Do not promote a new buy above `Wait` unless evidence integrity, thesis,
  valuation, technical entry, concentration, cash, and sizing gates all pass.

## Data and calculation gate

Require all of the following before using a technical signal:

1. Verify the exact ticker, instrument type, exchange, currency, leverage
   multiple, daily-reset objective, and corporate-action state.
2. Verify the official exchange calendar and the latest completed regular
   session in `America/New_York`.
3. Build one same-session snapshot with raw OHLCV and adjusted history. The
   default collector is yfinance under [yfinance-data.md](yfinance-data.md): one
   ticker at a time, at least one second between external requests,
   `auto_adjust=False`, `prepost=False`, and `threads=False`. Compute indicators
   locally rather than accepting provider-supplied technical signals.
4. Preserve the builder's recent completed-bar `timing_window`, then run
   `scripts/validate_technical_snapshot.py` and require `verified` status. The
   validator independently recalculates signal flags from that window.
   The user-facing validator has no calendar-bypass mode; diagnostics and unit
   fixtures cannot authorize a live review.
5. For a live portfolio-changing proposal, cross-check the completed close
   against a second timestamped market-data source independent of both Yahoo
   Finance and yfinance. Treat a session mismatch or a difference above the
   approved tolerance as `F` or `Wait`.
6. Record source, observation session, retrieval time, units, price basis,
   formula version, and corporate-action treatment.

When a single-stock leveraged ETF quote source contains conflicting display
fields, do not replace the ETF with its underlying stock. Resolve a direct raw
completed ETF close first. The underlying may then corroborate the resolution
by comparing the ETF's daily return with the approved leverage multiple times
the underlying daily return. A passing proxy relationship is supporting
evidence only; without the direct ETF close the technical gate remains `Wait/F`.

If yfinance is throttled, times out, or returns an empty frame, use only bounded
backoff. Do not parallelize retries or silently substitute a stale bar. Missing
held-symbol OHLCV fails closed; a missing watch-only symbol disables only that
watch item.

Use these deterministic definitions:

- `EMA(n)`: `adjust=False`, alpha `2 / (n + 1)` on adjusted daily close,
  initialized from the first valid close and normalized to the latest raw-close
  scale. Require at least 252 valid completed daily bars as warm-up.
- `EMA rising`: `(EMA_t - EMA_t-3) / ATR14 > +0.10`; `EMA falling` is below
  `-0.10`; values in between are neutral.
- `ATR14`: true range on adjusted OHLC normalized to the latest raw-close scale;
  seed with the arithmetic mean of the first 14 true ranges, then use
  `ATR = ((prior ATR * 13) + current TR) / 14`.
- `prior 20-day high`: highest adjusted high in the 20 completed sessions before
  the signal session, normalized to the same latest raw-close scale as EMA and
  ATR. Exclude the signal session.
- `relative volume`: signal-session completed regular-session volume divided by
  the arithmetic mean of the preceding 20 completed regular sessions. Exclude
  the signal session; reject early-close comparisons unless an approved
  early-close adjustment exists.
- Use raw completed close for approved price bands, cost-basis loss boundaries,
  and next-session review levels.

Do not mix EMA values from one vendor or session with a close from another.
Do not copy an indicator from an article or screenshot when it can be calculated
from the verified snapshot.

Every approved policy must replace qualitative language with exact definitions.
The active workspace policy defines the EMA test, reclaim, decisive close,
breakout acceptance, extension, rejection, and failed-higher-high formulas.
No prose-only pattern may trigger a portfolio-changing review.

## 10EMA and 20EMA regime model

Classify the daily regime before evaluating a setup:

- `aligned_uptrend`: close above 20EMA, 10EMA above 20EMA, and 20EMA rising.
- `early_recovery`: close reclaimed 20EMA, 10EMA is rising, but 10EMA has not
  yet established alignment above 20EMA.
- `neutral_or_range`: 10EMA and 20EMA are flat or repeatedly crossing.
- `aligned_downtrend`: close below 20EMA, 10EMA below 20EMA, and 20EMA falling.
- `failed_reclaim`: price traded above 10EMA or 20EMA but closed back below the
  tested EMA, followed by a lower close or break of the signal low.

The policy must define the flatness tolerance, crossing lookback, test zone,
confirmation window, and whether a condition uses intraday high/low or completed
close. Do not classify a regime by visual judgment.

An EMA crossover alone is never a buy or sell. Require a setup, confirmation,
invalidation, reward-to-risk, cash, sizing, and evidence gates.

## Buy setups

Support two policy-selectable long setups. Do not combine them after the fact.

### Pullback and reclaim

Require:

1. `aligned_uptrend`, or an explicitly approved `early_recovery` exception;
2. price tested the approved 10EMA/20EMA zone;
3. completed close reclaimed the policy-selected EMA and closed above the prior
   completed close;
4. the test-day relative volume is no more than 1.0, while reclaim-day relative
   volume is at least 1.0 and at least 1.2 times the test-day value;
5. price is not more than the approved ATR extension above 20EMA;
6. initial stop is below entry and reward-to-risk meets the approved minimum;
7. valuation, concentration, verified cash, instrument, quantity, and
   maximum-loss rules pass.

The EMA test must occur within the approved number of completed sessions and use
the approved ATR tolerance. A stale test cannot be revived after the setup
expires.

### Breakout and acceptance

Require:

1. completed close above the prior 20-day high;
2. `10EMA > 20EMA`, both rising as required by policy;
3. approved relative-volume confirmation;
4. no unresolved gap, earnings, liquidity, or corporate-action risk;
5. no excessive ATR extension above 20EMA;
6. either next-session acceptance above the breakout level or another
   policy-defined confirmation; and
7. the same valuation, cash, sizing, concentration, and loss gates as a
   pullback entry.

Reject or defer a setup across an unapproved earnings window, an excessive gap,
an early-close session without volume adjustment, missing/duplicate bars, or a
failed minimum dollar-volume/spread test.

Reject a new long in `aligned_downtrend` unless a separately approved reversal
setup defines confirmation and a tighter invalidation.

## Take-profit and trailing rules

Define initial risk `R = planned entry - initial stop` before entry. If `R` is
not positive and reproducible, do not create the setup.

For a confirmed fill, record `actual R = confirmed average fill - approved
initial stop` without overwriting planned R. Existing holdings that lack a
versioned initial stop cannot use reconstructed R-multiple targets. They require
approved absolute/ATR/EMA reduction bands until a new anchor is explicitly set.

Use policy-approved tranches rather than an all-or-nothing narrative:

- First take-profit review: price reaches the approved first R multiple.
- Second take-profit review: price reaches the approved second R multiple.
- Extension review: price is an approved ATR multiple above 20EMA and shows
  objective rejection, momentum deceleration, or a failed higher high.
- Trend remainder: trail with the approved 10EMA/20EMA closing rule or a
  structural swing level.

RSI alone cannot trigger an exit. It may confirm an extension or momentum
failure only when paired with price and EMA evidence. Do not move the original
stop or target retrospectively without a new versioned policy decision.

## Staged reduction

For a holding whose approved direction is `reduce`, define both paths before a
signal occurs:

### Reduce into strength

- tranche review on an approved reclaim or test of 10EMA;
- next tranche review on an approved test or reclaim of 20EMA;
- optional final strength tranche at the prior 20-day high, an approved R
  target, or an approved ATR extension.

### Reduce on renewed weakness

- watch after the first completed close below the selected EMA;
- tranche review only after the approved confirmation, such as two closes below
  10EMA, one decisive close below 20EMA with `10EMA < 20EMA`, or a failed
  reclaim followed by a break of the signal low;
- hard-risk review at the existing exact average-cost loss boundary.

For SOXL, a 10EMA weakness condition by itself is observation-only. It may
produce a deduplicated grade-B watch with `quantity=null`, but it cannot consume
a reduction slot or imply a sale.

For every tranche, approve the percentage or shares, trigger, confirmation,
minimum remaining shares, expiry, and re-entry/reset rule. Never execute the
same tranche through both the strength and weakness paths. Require a
user-confirmed fill before unlocking the next tranche.

After a confirmed reduction, record an exact fill record containing tranche
ID, completed-session date, confirmed trigger path, and confirmed quantity.
Do not reconstruct the trigger from the slot ID or infer it from the broker
quantity. Before another technical-stop or weakness tranche may open, require:

- at least three completed common sessions after the confirmed fill;
- both the held instrument and confirmation proxy to have closed above the EMA
  related to the confirmed trigger after that fill; and
- a validated timing window that contains the fill and recovery evidence.

Map a confirmed 10EMA trigger to 10EMA; map a confirmed 20EMA, failed reclaim,
technical stop, extension, or take-profit rejection to 20EMA. Missing fill
metadata or a timing window that cannot prove recovery fails closed. A
technical stop does not bypass this slot rearm. Only the unsized hard
average-cost maximum-loss review bypasses it.

Keep rearm and re-entry as different state machines. Recovery above the related
EMA only re-enables observation of a fresh weakness cycle; it does not authorize
buying back shares. A re-entry needs a separately confirmed vacant slot, two
consecutive completed closes with both the holding and confirmation proxy above
EMA20, `EMA10 > EMA20`, rising EMA20s, an approved reclaim or breakout setup,
verified settled cash, risk budget, and post-trade leverage capacity. Cap the
quantity at the minimum of the confirmed sold slot, cash, risk-budget, and
portfolio-cap quantities. With verified available cash at or below zero, the
result is always `Watch/Wait` with `quantity=null`.

Give every tranche a stable ID and deduplication key. If strength and weakness
paths become true together, apply this priority unless the approved policy says
otherwise: `hard maximum-loss review > technical stop review > weakness
reduction > strength reduction > take-profit > buy`. Define strength-path order
separately for each regime; do not assume 10EMA is always reached before 20EMA.

The active holding plan uses shared cumulative slots:

- SOXL: `24 / 24 / 24` shares, with a 27-share final residual reserved for the
  hard-risk rule or later explicit instruction;
- MVLL: `99 / 99 / 99 / 99` shares.

SOXL must be confirmed by SOXX direction and MVLL by MRVL direction. These are
confirmation proxies/reference securities, not substitute holdings or inferred
fills.

## Stop and invalidation

Keep three concepts separate:

1. `setup invalidation`: the chart thesis is false;
2. `technical stop review`: an approved close-based technical boundary is
   breached;
3. `hard maximum-loss review`: the exact average-cost boundary is breached.

For a long setup, a proposed initial stop may use the tightest approved level
that remains below entry, for example the maximum of:

- structural swing-low invalidation adjusted by an approved ATR buffer;
- `20EMA - approved ATR multiple` (0.75 ATR in the active existing-holding
  timing policy); and
- the existing hard maximum-loss boundary.

Reject the setup if the resulting stop is at or above entry or if position size
would violate portfolio risk. Use completed closes unless the policy explicitly
defines an intraday emergency rule. A gap through a stop creates a human risk
review; it is not evidence of a fill at the stop price.

The active policy must specify one-close versus two-close confirmation,
swing-low lookback, ATR buffer, gap-down handling, halt handling, and expiry.
Recalculate an average-cost boundary only from a user-confirmed fill or fresh
broker snapshot; never infer a new average price.

An excessive opening gap or an explicit provider trading-halt status creates a
watch-only review with `quantity=null`. Cancel stale entry candidates and wait
for a first-tradable-price human review. Zero volume by itself is not proof of a
halt, and neither a gap nor a halt permits inferring a stop fill.

Define a time stop for short- or medium-horizon trades. A typical draft may
review a position when it fails to achieve the approved minimum favorable
excursion within the approved number of sessions and closes below 20EMA. Keep
both values inactive until approved.

Peak-drawdown and time-stop rules are return-seeking overlays, not emergency
facts. Keep them inactive until a pre-registered multi-regime walk-forward test
passes. Candidate research grids may test 20/25/30/35% prospective peak-to-close
drawdown and 10/20/30 completed-session time stops with `MFE < 0.5 planned R`,
but do not select or apply a threshold from a one-year sample. Existing holdings
without a versioned entry and initial stop cannot receive a retrospective time
stop.

## Position sizing and portfolio gates

Require verified available cash, total capital, approved per-trade risk,
initial stop, post-trade exposure cap, correlation, liquidity, and leveraged
ETF daily-reset risk before calculating shares.

Use:

`shares = floor((capital * allowed_risk_fraction) / abs(entry - stop))`

Cap the result by available cash, position concentration, sector exposure, and
liquidity. For leveraged ETFs, test multi-day path dependence and gap loss; do
not treat the stated daily leverage multiple as a multi-day return promise.

Reject quantity-dependent advice when the broker snapshot is stale under the
active policy. Zero verified available cash makes every new-buy condition
`Watch/Wait`, even if the technical setup passes.

## Evidence and citation verification

Create an evidence ledger for every portfolio-changing analysis. Each material
claim or number must be either a sourced fact or a reproducible calculation.

For sourced facts, record:

- claim ID and concise claim;
- direct source locator and source type;
- publication/effective time and retrieval time;
- observation session, currency, units, and accounting definition;
- confidence, contradiction status, and whether independent confirmation is
  required.

For calculations, record:

- formula version;
- input field names, values, units, source IDs, and session;
- output value and rounding policy;
- deterministic validation result.

Use official issuer/exchange/SEC sources for identity, product objective,
leverage terms, filings, and corporate actions. Use timestamped market data for
OHLCV. Require primary evidence plus independent confirmation for disputed or
market-moving claims when practical.

For every portfolio-changing proposal, run
`scripts/validate_research_packet.py`. A passed research packet remains
untrusted input to the separate policy evaluator and cannot create an order.

Before answering, explicitly report:

- technical snapshot validator status;
- completed session and price basis;
- indicator formula version;
- material source conflicts or missing citations;
- policy version and whether each threshold and quantity is approved;
- remaining conditions that cap the result at `Wait` or `B`.

## Output contract

Lead with `Buy review`, `Hold`, `Take-profit review`, `Reduction review`,
`Stop review`, or `Wait`. Then show:

1. completed session, quote status, and validation status;
2. 10EMA, 20EMA, their three-session slopes, ATR14, relative volume, and prior
   20-day high;
3. active setup and passed/failed conditions;
4. approved entry, tranche, stop, target, expiry, and quantity--or `Not
   approved`;
5. reward-to-risk and projected exposure when inputs are verified;
6. strongest failure case and exact invalidation;
7. evidence ledger status and direct supporting sources;
8. a statement that no order was placed or scheduled.
