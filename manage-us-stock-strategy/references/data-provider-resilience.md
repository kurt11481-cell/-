# Data Provider Resilience

## Active session-aware market-data authority

The active guarded scope prioritizes Kiwoom for verified broker facts,
broker-observable session quotes, finalized archived Raw regular closes, and
validated Adjusted technical history. yfinance remains a diagnostic Shadow and
explicit ticker-local fallback; it is not an official close source. Apply the
full session, quote-type, price-basis, timestamp, stability, and finalization
comparability gate in
[kiwoom-session-aware-priority.md](kiwoom-session-aware-priority.md) before any
numerical vendor comparison. Non-comparable values are never price conflicts.

Use one canonical validated snapshot per run. Analysts must not fetch competing
prices independently.

`workspace/policies/source_capabilities.json` declares source capability by
evidence type. Unknown capability is false or `UNKNOWN`, never inferred.
Historical evidence is rejected when the applicable capability does not support
point-in-time use. Current Reddit or StockTwits data is live, low-authority
sentiment context only and cannot enter a historical packet.

## Failure handling

Track lightweight provider state with `last_success`, `last_failure`,
`consecutive_failures`, `failure_type`, `circuit_state`, and `retry_after`.
Allowed circuit states are `HEALTHY`, `DEGRADED`, and `OPEN`.

HTTP 429, timeout, empty response, schema mismatch, and authentication failure
must not cause retry storms, IP rotation, stale-data substitution, or a market
signal. A fallback is allowed only when its evidence capability, session,
timestamp, point-in-time eligibility, and provenance all pass.

Preserve the yfinance contract: `auto_adjust=False`, `actions=True`,
`prepost=False`, `threads=False`, sequential requests, bounded retry, and
`repair=False` where required. yfinance remains an unofficial raw collector; it
is not an official exchange calendar or independent Yahoo-free cross-check.

Normalize accepted records to symbol, field, value, units, exchange session,
timestamp, provider, retrieval time, raw/adjusted basis, quality status, and
source identifier.

## v2.5 selective completed-close acquisition

Run `scripts/provider_preflight.py` once before a post-market scan. Build the
provisional holding and opportunity states first, then create one selective
price-verification queue. The
`INDEPENDENT_COMPLETED_CLOSE` capability must be enabled, Yahoo-independent,
session compatible, timestamped, and explicitly eligible in the capability
registry. `build_independent_close_snapshot.py` is provider-agnostic; it does
not select or silently activate a vendor. A second Yahoo endpoint never counts
as independent.

Web acquisition is recorded as `CODEX_WEB`, but the provider and source type
must identify the actual page/domain. Search snippets and Yahoo-origin pages are
not independent evidence. When the queue is empty, return `NOT_REQUIRED` and do
not create an outage. When queued evidence is unavailable, aggregate one global
provider incident while preserving each candidate as `VERIFICATION_PENDING`;
do not erase a valid `READY` state. A validated symbol-level conflict blocks
only that ticker.
