# Data Provider Resilience

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

## v2.4 completed-close preflight

Run `scripts/provider_preflight.py` once before a post-market scan. The
`INDEPENDENT_COMPLETED_CLOSE` capability must be enabled, Yahoo-independent,
session compatible, timestamped, and explicitly eligible in the capability
registry. `build_independent_close_snapshot.py` is provider-agnostic; it does
not select or silently activate a vendor. A second Yahoo endpoint never counts
as independent.

When no approved provider is healthy, return one global
`GLOBAL_INDEPENDENT_CLOSE_OUTAGE`, suppress per-ticker retries, keep affected
rows visible as data blocked, and report `DATA_PROVIDER_BLOCKED`. A symbol-level
missing record or mismatch blocks only that ticker when common infrastructure
and the official session remain valid.
