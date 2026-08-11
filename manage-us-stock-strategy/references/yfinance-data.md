# yfinance Market-Data Contract

Use yfinance only as an unofficial raw market-data collector. It does not own
the technical rules, determine the official completed session, validate an
instrument's identity, or provide the independent close cross-check required by
the live timing policy.

## Collection settings

Run `scripts/build_market_snapshot.py` with its default yfinance provider, or
state the settings explicitly:

```powershell
python scripts/build_market_snapshot.py --state portfolio_state.json --output snapshot.json --provider yfinance --request-delay-seconds 1.0
```

The collector must request one ticker at a time with:

- `interval="1d"`;
- `auto_adjust=False` so raw close remains available for executable levels and
  average-cost loss boundaries;
- `actions=True` so splits and dividends can be audited;
- `prepost=False` so premarket and after-hours observations do not contaminate
  the completed regular-session bar;
- `threads=False` so requests remain sequential and rate limiting is effective;
- `repair=False` in live monitoring so silently repaired vendor estimates are
  not treated as observed prices.

Compute EMA, ATR, RSI, MACD, moving averages, stochastic, relative volume, and
other approved indicators locally from the returned OHLCV. Record the package
version, request mode, adjustment settings, formula version, and raw-versus-
adjusted price basis in the snapshot.

## Rate limiting and failure handling

yfinance accesses Yahoo Finance through an unofficial interface that can change
or temporarily throttle clients. Enforce a minimum one-second interval between
external ticker requests. For larger symbol sets, keep sequential collection,
cache one completed-session result per symbol, and reuse the transient snapshot
instead of downloading again in each module.

On HTTP 429, an empty response, timeout, or apparent throttling:

1. retry no more than the bounded retry count with backoff;
2. never start parallel retries, rotate IP addresses, or bypass throttling;
3. do not substitute stale bars silently;
4. mark the affected symbol unavailable; and
5. apply the policy's fail-closed scope: missing held-symbol OHLCV is `F`, while
   a missing watch-only symbol disables only that watch item.

Increasing the delay above one second is allowed. Reducing it below one second
for live collection is not allowed.

## Independent validation

Before a technical signal can enter the live evaluator:

- verify the U.S. trading day and early-close status from an official exchange
  or regulator calendar;
- cross-check the completed raw close with a second timestamped source that is
  independent of Yahoo Finance and yfinance;
- run `scripts/validate_technical_snapshot.py` and require verified indicator
  recomputation and provenance; and
- reject a session mismatch or a close difference outside the active policy
  tolerance.

Another Yahoo page, yfinance `Ticker.history`, or the legacy Yahoo chart
endpoint is not an independent cross-check for a yfinance download because the
underlying source is the same.
