# Portfolio Construction and Validation

## Objective

Maximize realistic long-run geometric wealth subject to drawdown, recovery time, downside risk, cost, tax, turnover, and behavioral sustainability. Do not optimize only for the highest historical CAGR.

Keep the default plan spot-only. Exclude options, futures, leverage, and inverse products. Review securities-backed borrowing only in a separate stress-tested appendix and exclude it from the base plan unless it robustly improves outcomes.

## Candidate universe

Use the user-approved universe unless explicitly changed:

- broad/core: SPYM;
- dividend/value: DGRO, DVY, SCHD, FNDX;
- growth/momentum: QQQM, SPMO;
- semiconductor/memory: SOXX, DRAM;
- defense: XLV;
- reserve: SGOV and brokerage cash.

Treat DIVB as an exit-only legacy holding when the active policy marks its target as zero.

## Compare a limited strategy set

At minimum compare:

- SPYM buy-and-hold;
- QQQM buy-and-hold;
- equal-weight approved universe;
- strategic core only;
- six-month relative momentum;
- relative momentum plus absolute-trend filter;
- volatility-adjusted momentum;
- valuation-aware momentum;
- a restrained adaptive multi-asset variant.

Compare core/satellite splits of 70/30, 60/40, and 50/50 and satellite selection of Top 1, Top 2, and Top 3 only. Compare monthly, quarterly, and semiannual rebalance schedules. Predeclare the parameter grid and stop adding variants after observing results.

## Default signals

- Rank by six-month dividend-reinvested total return.
- Test 3, 6, 9, and 12 months, recent-one-month exclusion, and volatility-adjusted momentum only as sensitivity checks.
- Calculate monthly signals from the final completed U.S. trading session and execute hypothetically on the next session.
- Use a 10-month moving average, 200-day moving average, or 12-month absolute total return as limited absolute-trend alternatives.
- Move an ineligible satellite allocation to SGOV or cash rather than automatically substituting an unapproved asset.
- Use valuation as an overheating penalty or cap, not a precise short-term timing switch.

Require adequate history. Do not use a proxy to promote a newly launched ETF into a live momentum slot unless the user explicitly approves a separate proxy study.

## Control risk and overlap

Test equal weight, inverse volatility, maximum-weight caps, target volatility, rebalance buffers, and minimum trade thresholds. Prefer the simplest rule that produces a material and stable improvement after costs.

Check holdings overlap and common factor exposure. Multiple ETFs do not create diversification when they hold the same megacap, semiconductor, dividend, duration, or country risk.

Apply constraints in this order:

1. data integrity and legal/account constraints;
2. verified holdings and settled/available cash;
3. no-order-without-approval boundary;
4. hard exposure caps;
5. stage and cadence rules;
6. strategic target weights;
7. baseline target shares;
8. tracking-share preferences.

### Control effective leverage deterministically

For a leveraged portfolio, distinguish capital weight from effective daily
factor exposure. With the currently approved products, calculate:

`gross effective leverage = 3*abs(SOXL weight) + 2*abs(MVLL weight) + 2*abs(NBIL weight)`

and separately:

`semiconductor-cluster leverage = 3*abs(SOXL weight) + 2*abs(MVLL weight)`

These are portfolio exposure coefficients, not evidence that SOXL must return
exactly three times SOXX on any observed day. Use `SOXL -> SOXX` for sector
direction context only. Use `MVLL -> MRVL` as a supplemental daily-multiple
diagnostic, never as a substitute close and never with an unstated live
tolerance.

Include even a de-minimis position in the arithmetic, though policy may suppress
its recurring alerts. Use verified current market values and total account
equity; do not use cost basis as portfolio weight. A free-form LLM may explain
macro or regime evidence but may not raise a numeric cap. Any daily cap must be
a versioned lookup table or target-volatility formula validated at portfolio
level, with maximum one-day step-up, concentration, liquidity, and gap-risk
constraints.

## Backtest without contamination

- Use adjusted total returns and retain executable raw prices separately.
- Prevent look-ahead, survivorship, and corporate-action errors.
- Do not synthesize pre-inception ETF returns in the primary test.
- Use the same comparable period across strategies. Disclose when a new ETF shortens the sample.
- Use a rolling six-year train and next-one-year validation only when at least seven years of valid common history exist.
- Prefer out-of-sample performance and a stable neighborhood of parameters over the single best backtest point.
- Include expense ratios, commissions, spread, slippage, dividend tax, capital-gains assumptions, FX conversion, and turnover.
- State Korean-resident and account-type assumptions before presenting after-tax KRW results.

For a return-seeking change to a leveraged SOXL timing policy, require at least
five years of stitched out-of-sample results spanning bull, bear, range, and
high-volatility regimes when data permit. A suitable minimum is a 24-month
training window followed by a six-month test, stepped across ten folds. Carry
cash, holdings, vacant slots, rearm state, entry/R anchors, and high-water marks
through the primary stitched test; also show fold-reset robustness.

Pre-register indicator semantics, fill timing, corporate-action treatment,
gap/halt behavior, cash yield, whole-share rounding, transaction costs, and
selection tie-breaks before seeing results. Require 20-bp cost-stress survival,
directional robustness at 50 bp, adjacent-parameter stability, improvement in
at least seven of ten folds including bull and bear/high-volatility periods, and
at least 20 independent trigger/re-entry cycles. If full history is unavailable,
fail closed: do not replace it with a shorter favorable sample.

Safety controls that reduce authority--such as turning a weak signal into
watch-only, requiring post-fill rearm, and freezing on gaps, halts, or evidence
failure--may be adopted separately. Re-entry, peak/time exits, extra indicator
votes, and dynamic leverage caps remain inactive until the return gate and a
subsequent 3-to-6-month or 20-signal forward shadow test pass.

Report CAGR/geometric return, volatility, maximum drawdown, recovery time, Sharpe, Sortino, Calmar, downside deviation, worst 1/3/12 months, positive-year rate, turnover, pre/post-cost returns, upside/downside capture, real return, and KRW sensitivity.

## Select one base plan

Return:

1. one-paragraph decision;
2. data period and market regime;
3. one 100%-summing base allocation and each holding's role;
4. core rules;
5. satellite algorithm;
6. in-sample, out-of-sample, and sensitivity findings;
7. monthly and quarterly operating instructions;
8. bull, range, crash, rate-shock, KRW-strength, and KRW-weakness responses;
9. borrowing appendix, normally `Do not use`;
10. failure conditions and why the selected plan beat the alternatives.

Do not present a menu without choosing a base plan.
