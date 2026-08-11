# SOXL EMA timing-policy audit and one-year backtest

## Conclusion first

**Validation label: in-sample mechanical replay only — not predictive
validation.**  The policy was versioned on 2026-08-05 and mechanically replayed
through 2026-08-04.  The test therefore has no untouched holdout and cannot
establish expected future performance.

The active `2026-08-05-ema-timing-v2` policy is defensible as a conservative,
human-reviewed **holding-risk alert overlay**, but it is not a complete trading
strategy and should not be judged or deployed as one.  In the exact one-year
study from **2025-08-05 through 2026-08-04**, the active 24/24/24-share reduction
overlay reduced maximum drawdown from **-69.41% to -57.00%**, but returned only
**+120.13%** versus **+449.84%** for 99-share buy-and-hold.  It sold 48 shares on
two consecutive sessions near the start of the test and had no approved re-entry
or reset path.  This is evidence that the current rules need a distinct-signal
reset/cooldown and a separately approved re-entry framework; it is not evidence
that EMA risk controls should be removed.

Two predeclared diagnostics were added without changing the active policy.
Diagnostic A added a distinct weakness-signal reset plus a three-completed-
session cooldown; Diagnostic B added the same controls and made
`weakness_10ema` watch-only.  They improved return to **+131.96%** and
**+133.52%** and maximum drawdown to **-55.34%** and **-55.12%**, respectively.
The improvement is real but modest: both still permanently sold 72 shares and
lacked re-entry.  Neither diagnostic is active or parameter-optimized.

## Point-in-time data and execution

- Test window: 2025-08-05 through 2026-08-04, inclusive.
- Warm-up: 2024-06-03 onward; at least 252 completed bars before any signal.
- Primary raw OHLCV: Nasdaq historical web API.
- Independent check and corporate-action factors: Yahoo chart API.
- Official NYSE calendar audit: **passed**.  Both final input files contain all
  544 expected sessions from 2024-06-03 through 2026-08-04; no silent inner
  join or session deletion remains.
- SOXL source counts: 544 Nasdaq response rows, 543 valid Nasdaq bars, 544 Yahoo
  bars, 543 raw common valid bars, and 544 final calendar-complete rows.
- SOXL repair provenance: Nasdaq emitted an N/A placeholder for **2026-04-20**,
  so that session's raw OHLCV was restored from Yahoo
  (`95.970001 / 96.930000 / 92.029999 / 95.940002`, volume `49,367,800`).
  Nasdaq's **2026-04-17** volume placeholder `9,999,999` was replaced by the
  Yahoo volume `67,081,400`; Nasdaq OHLC remained the primary source.
  The repaired dates were independently checked against the historical tables
  at https://chartexchange.com/symbol/nyse-soxl/historical/ and
  https://chartexchange.com/symbol/nasdaq-soxx/historical/; small consolidated-
  volume differences are retained as source-specific provenance rather than
  averaged.
- SOXX source counts: 544 Nasdaq response/valid bars, 544 Yahoo bars, 544 raw
  common valid bars, and 544 final rows.  No fallback session was needed.
- Maximum absolute Nasdaq/Yahoo close differences were $0.0000122 for SOXL and
  $0.0000293 for SOXX; tolerance failures: 0.
- Indicators: distribution/split-adjusted OHLC normalized to each signal day's
  executable raw-close scale; `EMA(adjust=False)` and Wilder ATR14 exactly as in
  the active policy.
- Signal: only after a completed regular-session close.
- Hypothetical fill: following regular-session open; the overnight gap is
  therefore included.
- Base friction: 10 basis points per fill, with 0/5/10/20-bp sensitivity.
- Cash yield, taxes, and KRW/USD conversion: excluded.
- Dividends: credited in cash on the recorded ex-date.
- Point-in-time audit: eight independently truncated histories for both SOXL and
  SOXX; zero flag mismatches and maximum numerical differences of 3.55e-15 and
  1.14e-13, respectively.
- Early-close signal gate: unadjusted early-close volume observations are
  rejected as grade F, matching the active snapshot validator.

Official session calendar:
https://www.nyse.com/markets/hours-calendars

Nasdaq input endpoints are recorded in the JSON result.  Official SOXL product
objective and daily-reset warning:
https://www.direxion.com/product/daily-semiconductor-bull-bear-3x-etfs

Official SOXX benchmark identity:
https://www.ishares.com/us/products/239705/fund

## Results at 10 bp per fill

| Study | Total return | Max drawdown | Ann. vol. | Sharpe (rf=0) | Downside dev. (target 0) | Sortino (target 0) | Trades | Avg. exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 99-share buy-and-hold | +449.84% | -69.41% | 132.12% | 1.97 | 88.99% | 2.92 | 1 | 99.99% |
| Active staged-overlay event replay | +120.13% | -57.00% | 82.90% | 1.38 | 57.95% | 1.97 | 4 | 52.18% |
| Diagnostic A: reset + 3-session cooldown, **not active** | +131.96% | -55.34% | 83.11% | 1.44 | 58.25% | 2.06 | 4 | 56.84% |
| Diagnostic B: A + 10EMA weakness watch-only, **not active** | +133.52% | -55.12% | 82.58% | 1.45 | 57.86% | 2.07 | 4 | 56.38% |
| Research binary long/cash, **not active** | +11.40% | -23.38% | 33.91% | 0.49 | 23.33% | 0.71 | 8 | 19.12% |

Downside deviation and Sortino now use the standard zero-target definition:
positive daily returns are replaced by zero and **all** observations remain in
the downside-deviation denominator.  This replaces the non-standard deviation
of negative-return observations only.

SOXX buy-and-hold adjusted-basis total return before trading cost was
**+125.3227%**.  SOXX and SOXL both reference the **NYSE Semiconductor Index**;
SOXX is used as the policy confirmation proxy.  SOXL's +449.84% does not mean it
targets three times SOXX's multi-day return because SOXL resets leverage daily.
In a persistent trend, compounding may help; in a volatile range, it may
severely hurt.

Cost sensitivity did not change the conclusion:

| Per-fill cost | Buy-and-hold | Active overlay | Diagnostic A | Diagnostic B | Research binary |
|---|---:|---:|---:|---:|---:|
| 0 bp | +450.39% | +120.42% | +132.28% | +133.84% | +12.30% |
| 5 bp | +450.12% | +120.28% | +132.12% | +133.68% | +11.85% |
| 10 bp | +449.84% | +120.13% | +131.96% | +133.52% | +11.40% |
| 20 bp | +449.29% | +119.84% | +131.65% | +133.21% | +10.51% |

## Active staged-overlay event replay

The period-start buy is only a common 99-share normalization anchor.  Every B
review below is assumed approved by a human and filled next open.  That
assumption is necessary for simulation and is not an execution recommendation.

| Signal close | Next-open hypothetical fill | Trigger | Shares | Slot |
|---|---|---|---:|---|
| 2025-08-05 | 2025-08-06 at $23.81616 | weakness_10ema | 24 | SOXL-R25 |
| 2025-08-06 | 2025-08-07 at $25.45452 | weakness_20ema | 24 | SOXL-R50 |
| 2025-09-03 | 2025-09-04 at $24.38559 | technical_stop | 24 | SOXL-R75 |

The final 27 shares remained held because their active slot has no EMA trigger.
The study therefore demonstrates the policy's path dependence: early correlated
weakness signals permanently cut later upside exposure.

## Diagnostic sensitivities — NOT ACTIVE

These diagnostics use the same frozen data, point-in-time indicators,
next-open execution, 10-bp cost, and look-ahead audit as the active event
replay.  They are diagnostic ablations, not an optimization exercise.

### Diagnostic A: distinct reset plus 3-session cooldown

After a weakness-trigger fill, both SOXL and SOXX must close above the EMA
associated with that trigger before another weakness tranche can be scheduled.
Every B-grade reduction must also wait until three subsequently completed
sessions have elapsed since the prior fill.  The unsized D-grade hard-risk
review remains unaffected.

| Hypothetical fill | Trigger | Shares |
|---|---|---:|
| 2025-08-06 at $23.81616 | weakness_10ema | 24 |
| 2025-09-04 at $24.38559 | technical_stop | 24 |
| 2025-11-17 at $37.86210 | technical_stop | 24 |

The August 6 `weakness_20ema` review was suppressed by the cooldown, and SOXL
and SOXX rearmed the weakness gate above EMA10 on August 8.

### Diagnostic B: A plus `weakness_10ema` watch-only

`weakness_10ema` is recorded but cannot schedule a sale for default-hold SOXL.
All other Diagnostic-A conditions remain unchanged.

| Hypothetical fill | Trigger | Shares |
|---|---|---:|
| 2025-08-07 at $25.45452 | weakness_20ema | 24 |
| 2025-09-04 at $24.38559 | technical_stop | 24 |
| 2025-11-17 at $37.86210 | technical_stop | 24 |

Diagnostic B was the best of the two fixed ablations, but its +13.39 percentage-
point improvement over the active overlay came with nearly the same residual
drawdown.  One sample does not justify activation.  The dominant unresolved
problem remains the absence of a re-entry/reset framework after 72 shares have
been sold.

## What cannot be fairly backtested as current policy

1. The actual current SOXL average cost of about $123.32 cannot be projected
   backward before the unknown acquisition dates.  Doing so would be look-ahead
   and would create a false hard-loss event when SOXL traded near $25.
2. The D-grade hard maximum-loss rule has no deterministic sale quantity.  It
   can be logged but cannot be converted into a fair simulated sale.
3. Live B alerts require explicit human approval and confirmed fills.  The
   backtest has to assume every B review is approved to unlock the next slot.
4. The live policy has no approved SOXL buy size, re-entry, or reset rule.  The
   binary long/cash study fills those gaps for research and is not active policy.
5. R-multiple targets are disabled for this pre-existing position because no
   versioned initial stop exists.
6. One exceptional bull/volatility year is not sufficient to optimize or claim
   robustness.  A longer multi-regime walk-forward study is required.

## Reproducibility and frozen hashes

The JSON result contains a SHA-256 manifest for every policy/code input and
generated CSV.  Hashes below identify the exact rule set used for this run:

| Frozen input | SHA-256 |
|---|---|
| `alert_policy.json` | `b643b61eb4d3495ffc742e0fc0db03a77102faedb3bf712ed7426a4f1a65087c` |
| `portfolio_state.json` | `baa48644bec90f2902062517359ef9515cea9610ad1cba1bee0a9b54840f65e8` |
| `timing_engine.py` | `a5918ccf0ba8dc57db6e727c52d9112aeb32dab4e57159c7c6d3db8ebb6e875b` |
| `build_market_snapshot.py` | `bcbfcbdc3d3722aaeca4b8421de41e04f708beef941c099bb7bcb0d330e0c700` |
| `backtest_soxl_ema_policy_2026-08-05.py` | `519c41b730455652ddde503ddcce82c6a55c0d41d4ae55e5ec8369b6d21b3029` |
| SOXL source-input CSV | `4bca72ba388b8117a5152199321d0b65594d153a61cacdf4421917ee3889d1ac` |
| SOXX source-input CSV | `59f820855a290085384545041451c1e7e36f8c00114796eb6972dcb23c749f49` |

The generated CSV hashes were independently compared with the bytes on disk;
all matched the manifest.  Results were generated at
`2026-08-05T10:41:12.388715+00:00`.

## Policy audit and proposed improvements

1. **Keep B-only human review.**  The rules are useful as evidence-backed risk
   prompts, not autonomous orders.
2. **Require a distinct-signal reset between slots.**  After a confirmed
   weakness fill, require at least one close back above the relevant EMA and a
   subsequent new breach before the next weakness slot can activate.  A simple
   three-to-five-session cooldown is a secondary safeguard, not a substitute
   for the reset.
3. **Separate `hold` and `reduce` behavior.**  For default-hold SOXL,
   `weakness_10ema` alone should be a watch/escalation signal unless 20EMA or
   broader-market confirmation also deteriorates.  It is too sensitive for a
   3x daily-reset ETF when it can consume the first slot immediately.
4. **Approve an explicit hard-risk response.**  The current hard boundary is an
   alert, not an enforceable loss cap.  Quantity/percentage and gap handling must
   be user-approved before it can be backtested as an exit rule.
5. **Add a re-entry/reset framework before evaluating total returns.**  Any
   reduction system without a defined way to restore exposure is structurally
   biased toward underexposure in long bull trends.
6. **Add a peak-drawdown review distinct from cost-basis loss.**  A -20% cost
   boundary does not prevent a much larger drawdown from a profitable peak.  The
   study's staged portfolio still suffered -57.00% peak-to-trough.
7. **Treat macro as a risk modifier, not an untested buy button.**  The active
   policy currently contains SOXX direction confirmation but no explicit VIX,
   credit-spread, rates, breadth, or broad-index regime.  Candidate additions
   for forward testing are QQQ/SPY trend, VIX level/change, ICE BofA high-yield
   OAS, and 10-year real yield.  Thresholds should be predeclared and tested
   across multiple regimes; they should freeze additions or reduce size before
   they are allowed to force a sale.
8. **Add a short/medium-horizon time-stop review.**  The active policy references
   no approved holding-period or minimum favorable-excursion deadline.

## Reproducible files

- `backtest_soxl_ema_policy_2026-08-05.py`
- `soxl_ema_policy_2025-08-05_2026-08-04_results.json`
- `soxl_ema_policy_2025-08-05_2026-08-04_trades.csv`
- `soxl_ema_policy_2025-08-05_2026-08-04_SOXL_input.csv`
- `soxl_ema_policy_2025-08-05_2026-08-04_SOXX_input.csv`
- `soxl_ema_policy_2025-08-05_2026-08-04_SOXL_adjusted_OHLCV.csv`
- `soxl_ema_policy_2025-08-05_2026-08-04_SOXX_adjusted_OHLCV.csv`

No brokerage order was placed or scheduled.
