# Options Positioning Methodology

## Scope and trigger

Enter this module only for an explicit option-chain request such as `MRVL options`, its localized equivalent defined by the active locale resource, or when an option snapshot is supplied. Normalize the localized request to the canonical English `{TICKER} options` form before routing. Use options to contextualize spot risk and volatility. Do not turn the analysis into an automatic order or add derivatives to the default portfolio.

## Use the bundled analyzer

Run:

```powershell
python scripts/option_analyzer.py TICKER --expiries 2 --risk-free-rate 0.045 --dividend-yield 0.0 --expected-session-date YYYY-MM-DD --calendar-source "DIRECT_OFFICIAL_SOURCE" --output-root "ABSOLUTE_WRITABLE_WORKSPACE_PATH"
```

Pass a current maturity-appropriate rate and dividend yield when verified. If they are unavailable, use explicit assumptions and downgrade confidence. Run `--self-test` after modifying the script.

Verify the latest completed U.S. session from an official exchange or regulator calendar before running. Pass the verified date and direct source identifier together. Missing or mismatched session evidence makes the descriptive report ineligible. A valid descriptive report exits normally even though its Yahoo-only directional-alert eligibility remains false.

Yahoo's unofficial endpoint can reject automated requests. Treat HTTP 401/429 or schema failure as a data outage, not a market signal. Do not substitute remembered values. Request a timestamped chain export or use another lawful read-only source when collection fails.

Yahoo does not reliably timestamp the displayed option bid/ask. `lastTradeDate` timestamps an execution, not the live quote. Therefore a Yahoo-only run may produce a descriptive research report, but `alert_eligible` must remain false until a timestamped chain source is supplied. Never wire Yahoo-only option output into the recurring buy/sell alert engine.

## Validate the snapshot

Require:

- a validated ticker;
- HTTP and JSON success;
- no `optionChain.error`;
- a non-empty result, quote, expiration list, and at least one usable call/put side;
- underlying and chain timestamps from the same market context;
- America/New_York session handling;
- valid strike, IV, OI, bid/ask, last-trade time, and contract multiplier where available;
- a liquidity summary and stale-quote warning.

Use the first liquid expiry with at least three calendar days to expiry and the next suitable monthly or liquid expiry by default. Isolate 0DTE analysis as high risk.

Reject crossed, one-sided, or excessively wide quotes and every contract whose standard 100-share multiplier is not explicitly verified. Search fallback expiries until the requested number of `PASS` expiries is obtained; use `LIMITED` expiries only to document gaps, never to qualify an alert. The default underlying quote-age ceiling is 96 hours for weekend tolerance, but the latest completed-session check remains mandatory.

## Separate observations from models

Observed fields include quotes, volume, OI, strike, expiry, and reported IV. Delta, Gamma, Vanna, Theta, DEX, GEX, VEX, and theta-weighted OI are model-derived.

The bundled script uses a European Black-Scholes approximation with continuous dividend yield. U.S. equity options are generally American style; deep-ITM, dividend-sensitive, and adjusted contracts can deviate materially.

Use:

- `Vanna = -exp(-q*t) * phi(d1) * d2 / sigma` for `dDelta/dVol`;
- actual time to the assumed New York expiry close;
- an explicit rate and dividend assumption;
- clear units for every exposure.

## Do not overstate positioning

Yahoo OI does not reveal who is long or short. Therefore:

- present Call and Put OI-weighted sensitivities separately;
- call any signed Call-minus-Put value a **heuristic signed proxy** under a stated convention;
- never call the proxy actual dealer GEX, VEX, or HEX;
- do not infer volatility stabilization or acceleration from the proxy alone;
- treat `HEX` as an internal theta-weighted OI measure, not a universal market standard.

Max Pain is an OI payout summary, not a directional magnet. Do not infer up or down solely from its position relative to spot.

The 25-delta strikes are risk-neutral skew reference points, not an expected price interval. Estimate implied move separately from the ATM straddle or an explicitly stated IV model.

`last price * OI * 100` is not cash invested or true open-interest notional. Prefer midpoint-based indicative mark value when quotes are valid and label it accordingly.

## Suppress conclusions when quality fails

Do not generate directional positioning conclusions when critical timestamps are stale, a chain side is missing, quotes are unusable, valid IV/OI strikes are too few, a corporate action created adjusted contracts, or the API schema is inconsistent.

## Report contract

1. Conclusion first
2. Ticker, exact timestamp, underlying price, expiries, DTE, source, and assumptions
3. Data-quality gate and liquidity limitations
4. Observed Call/Put OI and volume concentrations
5. IV level, smile/skew, and ATM implied move
6. Max Pain as a descriptive reference only
7. Separate Call/Put model sensitivities and any explicitly labeled proxy scenario
8. Price zones that align with the spot chart, if available
9. Invalidation and next reassessment time
10. Mandatory warning:

> This analysis uses an unofficial Yahoo Finance option chain and OI-weighted model estimates. It cannot identify actual dealer or institutional positions or trade direction and must not be used as a standalone trading signal.
