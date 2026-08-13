# Kiwoom Candidate-Primary Replay Hardening

Use this contract only for read-only provider validation. It does not change
the live provider role, portfolio facts, strategy thresholds, quantity, or
order authority.

## Two authority planes

`MARKET_DATA_PROVIDER_REPLAY` evaluates identity, exchange mapping, official
session, Raw and Adjusted OHLCV, history sufficiency, local indicators,
yfinance Shadow comparison, decision-boundary comparison, pagination, locking,
and provider-failure isolation.

`FULL_STRATEGY_CONTEXT_REPLAY` evaluates only immutable point-in-time portfolio,
event, thesis, valuation, baseline, and broker context. Missing historical
archives must be reported as `PARTIAL_EXPECTED_NO_ARCHIVE`; current portfolio or
research facts must never be applied backward.

Provider transition readiness may use a passing market-data replay, passing
fault injection, and a current-session read-only context check. A current live
decision still requires all live research, event, portfolio, policy, and human
approval gates.

## History and technical authority

- Read the minimum history from the versioned Kiwoom rate-limit policy.
- Follow the official `usa06012` `cont-yn` and `next-key` continuation contract.
- Fetch Raw with `upd_stkpc_tp=0` and Adjusted with `upd_stkpc_tp=1`.
- Keep `exrt_appl_tp=0` for both.
- Stop at sufficient validated history, official exhaustion, bounded maximum
  pages, no-progress failure, or circuit opening.
- Deduplicate identical dates and reject conflicting duplicates or future bars.
- Calculate EMA, ATR, RSI, MACD, RVOL, and timing decisions locally with the
  existing deterministic formulas.
- Raw remains the completed-close and hard-risk basis. Adjusted history is for
  technical continuity and never overwrites Raw.

## Adjusted evidence

Kiwoom adjustment semantics and Yahoo adjustment semantics are distinct.
Classify them as `COMPATIBLE`, `INCOMPATIBLE`, or `UNKNOWN`. Do not report a
numeric Adjusted `MATCH` unless the basis and an applicable tolerance are
approved. `INCOMPATIBLE` and `UNKNOWN` remain explicit and inconclusive.

Always preserve Raw comparison separately. Same-basis Adjusted corruption must
produce `ADJUSTED_SERIES_CONFLICT`. A policy timing decision difference must
produce `TECHNICAL_DECISION_FLIP` and block provider transition readiness.

SOXL must use direct SOXL data; SOXX is direction-only. MVLL must use direct
MVLL data; MRVL is supplemental. SOXX x3 and MRVL x2 substitutions are
prohibited.

## Lock ownership

Use an atomic exclusive-create lock with an unguessable owner token. Release a
lock only if the caller acquired it and the stored token still matches. A
foreign or uncertain lock must remain byte-for-byte unchanged. Quarantine a
stale lock only when the TTL has elapsed and the owner process is proven dead.

## Forward-only context

Capture future completed-session context append-only with a hash chain. Store
portfolio state revision and hash, event evidence cutoff and bundle hash,
active baseline IDs and hashes, policy hashes, registry hash, previous record
hash, and `order_authority=false`. Never archive broker screenshots, account
numbers, credentials, or tokens. Never backfill prior sessions.

Replay, dry-run, and fault artifacts must not increment operational Shadow
sessions, deliver alerts, mutate runtime, or promote Kiwoom.
