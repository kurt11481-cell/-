# SOXL five-year walk-forward protocol (pre-result specification)

## Status and authority

This protocol was fixed before inspecting the new five-year result. It is a
historical research specification, not an order, fill, forecast guarantee, or
authority to change `portfolio_state.json`. A tested rule may become at most a
next-session human-review rule after it passes the acceptance gate below and is
separately written into a versioned policy.

## Data and execution contract

- Out-of-sample evaluation interval: 2021-08-05 through 2026-08-04. Fetch raw
  history from at least 2018-08-01 so the first training fold and indicator
  warm-up are complete. If this cannot be obtained and audited, do not use a
  shorter result to activate a return-seeking rule.
- Warm-up: at least 252 completed regular-session bars before the first signal.
- Calendar: official NYSE calendar plus a same-session vendor completeness
  audit. Missing or duplicate expected sessions fail the run.
- Prices: split/distribution-adjusted OHLC for indicators and returns, rescaled
  to the signal-date raw-close basis; raw next-session regular open for fills.
- Signal timing: completed regular-session close only. Hypothetical execution:
  next regular-session open.
- Costs: 10 bp per fill base case, 20 bp primary stress case, and 50 bp severe
  directional-robustness case. Overnight gaps are paid in full. Taxes and FX
  are excluded. Accrue cash at an auditable point-in-time 3-month Treasury rate
  when available and always show a zero-yield sensitivity.
- A gap through a stop is filled only at the first available next-session open,
  never at the stop. A halt, missing tradable open, or unresolved corporate
  action freezes the simulated action and is reported separately.

## Walk-forward structure

- Rolling training window: 24 months.
- Out-of-sample test window: the next 6 months.
- Step: 6 months.
- Out-of-sample span: five years across ten folds, including 2022 as test data.
- All choices for a fold must be made using only that fold's training window.
- Primary OOS results are stitched: capital, cash, holdings, vacant/restored
  slots, rearm state, entry/R anchors, and high-water marks carry across the ten
  consecutive test folds. A rule selected from a new training window may govern
  only future completed-session signals; it cannot rewrite open lots or prior
  state. Also report fold-independent robustness checks that reset each fold to
  normalized capital, 99 SOXL shares at the first tradable open, zero cash, all
  reduction slots armed, and a new HWM.
- Within a training fold, choose the highest CAGR variant whose maximum
  drawdown is no worse than the revised-simple baseline. Tie-break in order by
  higher Calmar, lower turnover, then the simpler rule. Do not retune on test.
- The final report must also show each calendar/regime segment separately so a
  single exceptional bull period cannot hide failure elsewhere.

## Strategies and ablations

1. SOXL buy-and-hold benchmark.
2. Existing staged EMA reduction replay.
3. Revised simple state machine:
   - SOXL `weakness_10ema` is watch-only;
   - a confirmed reduction disarms the related weakness trigger;
   - both SOXL and SOXX must recover the related EMA before a fresh
     false-to-true weakness cycle can consume another slot;
   - the unsized hard maximum-loss review is not suppressed by rearm;
   - a technical-stop reduction is disarmed like an EMA20 weakness reduction
     and cannot consume another slot until EMA20 recovery plus cooldown;
   - re-entry can restore only a previously confirmed sold slot and never more
     than the approved anchor.
4. One-at-a-time indicator ablations on strategy 3:
   - SMA 20, 50, 60, and 200;
   - MACD(12,26,9);
   - RVOL20, excluding the signal session;
   - Stochastic(20,3,3);
   - Chaikin Oscillator(3,10).
5. One restrained combination selected inside each training fold. SMA50 and
   SMA60 are alternatives, not simultaneous votes. SMA20 and MACD may not be
  counted as independent confirmations of the same EMA trend.

### Fixed trigger semantics for indicator ablations

All added indicators are **entry/re-entry filters only**. They do not create an
exit by themselves. Apply them to SOXX unless stated otherwise:

- SMA20: SOXX completed close must be above SMA20.
- SMA50 or SMA60: SOXX close must be above the selected SMA and that SMA must be
  above its value five completed sessions earlier.
- SMA200: SOXX completed close must be above SMA200.
- MACD(12,26,9): SOXX MACD histogram must be positive.
- RVOL: keep the active SOXL reclaim/breakout volume rules; the ablation is
  active rules versus no volume filter.
- Stochastic(20,3,3): on SOXL, slow %K must be above slow %D and below 80 on
  the entry/re-entry signal close.
- Chaikin(3,10): SOXX oscillator must be above zero.

Stage the multiple tests. First validate the revised simple state machine.
Second, test each indicator once against that fixed baseline. Third, allow only
the single best qualifying indicator from the training window to join the
baseline. Do not search combinations of two or more added indicators.

## Exact indicator definitions

- SMA(n): arithmetic mean of the prior `n` adjusted closes including the
  completed signal close.
- MACD: EMA12 minus EMA26; signal is EMA9 of MACD; all EMAs use
  `adjust=False` and completed closes.
- RVOL20: completed signal-session volume divided by the mean of the preceding
  20 completed regular sessions. The signal session is excluded from the
  denominator. An unadjusted early-close observation is ineligible.
- Stochastic(20,3,3): raw `%K = 100*(close-low20)/(high20-low20)`, followed by a
  three-session mean for slow %K and a three-session mean of slow %K for %D.
- Chaikin(3,10): cumulative ADL where daily money-flow volume is
  `((close-low)-(high-close))/(high-low)*volume`, then EMA3(ADL)-EMA10(ADL).
  A zero-range bar contributes zero. Corporate-action and early-close volume
  integrity gates apply.

## Small predeclared sensitivity grid

- Peak-to-close drawdown review: 20%, 25%, 30%, or 35%. High-water mark is the
  highest completed close since the fold's initial acquisition or most recent
  confirmed re-entry for that lot. A partial reduction does not reset the HWM
  of the remaining existing lot; a re-entered slot receives a separate HWM.
  A reduction needs a fresh false-to-true threshold breach plus both SOXL and
  SOXX completed closes below EMA20. It consumes only the next common staged
  slot, executes at the next tradable open, then requires EMA20 rearm and a
  recovery back above the selected peak-drawdown threshold before another peak
  event can arm. No intraday stop fill is assumed.
- Future-trade time stop: 10, 20, or 30 completed sessions when MFE remains
  below 0.5 planned R and both SOXL and SOXX completed closes are below EMA20.
  It exits only the most recently re-entered slot at the next tradable open.
  Planned R is the confirmed re-entry price minus the higher valid level below
  entry of `prior 10-session low - 0.25 ATR14` and `20EMA - 0.75 ATR14`.
  Existing holdings without a versioned entry/initial stop cannot use this
  retrospectively.
- Rearm confirmation: one or two consecutive completed closes above the
  related EMA; every variant requires both SOXL and SOXX and at least three
  completed sessions after the reduction fill. A new false-to-true breach is
  required after rearm. Technical-stop, peak-drawdown, weakness20, and
  failed-reclaim reductions all use EMA20 rearm. The hard-risk review remains
  unsized and outside this slot state machine.
- Re-entry restoration: 25%, 50%, 75%, or 100% of the previously confirmed
  sold slot, whole shares rounded down, capped at the original anchor and
  settled simulated cash. Eligibility requires two consecutive closes with
  both SOXL and SOXX above EMA20, both `EMA10 > EMA20`, and both EMA20s rising.
  Entry then requires the existing pullback-reclaim or breakout-acceptance
  setup and occurs at the next regular open. Eligibility expires after ten
  completed sessions or immediately when either symbol closes below EMA20.
- SOXL-only daily factor-exposure research tiers: 0.75x, 1.50x, 2.25x, and
  3.00x of account equity. Map tiers deterministically from SOXX:
  - 0.75x: close below SMA200, or aligned EMA downtrend;
  - 1.50x: neither risk-off nor risk-on;
  - 2.25x: close above a rising SMA200 and EMA20, EMA10 above EMA20, EMA20 rising;
  - 3.00x: 2.25x conditions plus SMA50 above SMA200 and SMA50 rising over five
    sessions.
  Target SOXL capital weight is factor exposure divided by three. Rebalance at
  the next open only when the tier changes and the weight difference is at
  least 10 percentage points. This separate research strategy does not validate
  a live portfolio cap that also contains MVLL or NBIL.

Accrue cash with the point-in-time 3-month Treasury rate when an auditable
series is available and show a zero-yield sensitivity. If the rate series is
unavailable, use zero yield and label the resulting bias against reduction
strategies. Credit distributions to cash on ex-date. Use whole shares for the
99-share staged study and fractional weights only in the separately labeled
dynamic-exposure research.

For report-only regime labels, classify each six-month test fold by SOXX total
return: bull above +10%, bear below -10%, range otherwise. Mark high volatility
when the fold's annualized SOXX volatility exceeds the median annualized
volatility of its preceding 24-month training window. These ex-post labels may
not select a rule.

Do not add thresholds or indicator combinations after viewing the results.

## Acceptance gate

A new return-seeking rule is eligible for policy consideration only if all of
the following hold out of sample:

1. It improves CAGR by at least 5 percentage points without worsening maximum
   drawdown by more than 3 percentage points, **or** improves maximum drawdown
   by at least 5 percentage points while retaining at least 95% of the revised
   simple state machine's CAGR.
2. Calmar improves by at least 10% versus the revised simple state machine.
3. The direction of improvement appears in at least seven of ten folds and in
   at least one bear/high-volatility and one bull/trending segment.
4. It survives the 20-bp stress case, does not lose its directional advantage
   at 50 bp, and remains stable at adjacent parameter choices; the best isolated
   grid point is rejected.
5. No single fold contributes more than half of total excess return.
6. There are at least 20 independent trigger/re-entry observations; otherwise
   the result remains review-only and requires forward observation.

Safety-only restrictions that reduce action authority (10EMA watch-only,
distinct-signal rearm, gap/halt fail-closed handling, and citation validation)
may be activated as B-grade review controls even when they do not satisfy a
return-improvement test. Quantity-bearing re-entry, peak/time exits, indicator
votes, and dynamic leverage caps may not.

## Required report

Report total return, CAGR, annualized volatility, Sharpe, Sortino, maximum
drawdown, Calmar, recovery time, worst day/month, turnover, transaction cost,
average exposure, trade count, fold results, regime results, and parameter
stability. Label the study historical walk-forward research; it is not a truly
untouched future test.
