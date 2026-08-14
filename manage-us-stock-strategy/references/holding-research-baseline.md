# Holding Research Baselines

Use this contract for the slow, immutable research layer for verified holdings.
It is a Shadow research artifact, not a portfolio-state or trade-authority
artifact.

## Layer ownership

- The baseline owns issuer/product identity, point-in-time evidence, thesis,
  counter-thesis, valuation status, invalidations, and research triggers.
- The completed-session overlay owns current price, technical state, event
  state, hard-risk observation, portfolio fit, cash, broker status, timing slot,
  and rearm state.
- The deterministic compiler combines one active baseline with one validated
  current overlay. Raw LLM signals never control the result.

Never store holdings, average cost, cash, broker data, current prices, current
hard-risk results, fills, orders, or quantities in a baseline. Historical
technical and portfolio views may appear only as context and never override the
overlay.

## Lifecycle

1. Build a point-in-time evidence packet from direct, reachable sources.
2. Recompute the research-packet and baseline SHA-256 values locally.
3. Validate against `holding-research-baseline.schema.json` and the semantic
   validator.
4. Activate independently in `SHADOW` or `MIGRATION` mode. Activation writes a
   new immutable version and atomically updates the active index.
5. Refresh by creating a new version; never overwrite an active artifact.

`PARTIAL` means the identified missing evidence remains visible. Direct or
underlying valuation marked `UNVERIFIED`, unverified fundamental risk, stale
evidence, or failed hashes must produce `STRATEGY_REFRESH_REQUIRED`, not a
baseline-driven hold or add. A failure for one ticker must not propagate to
another ticker.

## Leveraged holdings

- MVLL is a single-stock daily leveraged ETF. MRVL owns the issuer thesis and
  valuation basis; MRVL is not an MVLL close or target price.
- SOXL is a sector daily leveraged ETF. SOXX is direction-only; `SOXX return ×
  3` is not an SOXL return or close.
- Direct product-close evidence, daily reset, path dependence, liquidity,
  structure, policy slots, and rearm state remain explicit.

All compiled output is `SHADOW_ONLY` until a separately approved promotion
gate passes. Quantity remains null unless an already approved deterministic
policy supplies exact authority. `order_authority` is always false.

## Point-in-time valuation and event links

Issuer-equity and underlying-issuer research uses an immutable valuation
snapshot. Its price input must be a finalized Kiwoom Raw regular-session close;
yfinance remains a same-ticker, same-session diagnostic Shadow. A difference
between an internally valid Kiwoom price and yfinance or issuer/Web reference
is non-blocking diagnostic divergence. It cannot override Kiwoom and the values
must not be averaged. Only a Kiwoom self-integrity failure—such as stale data,
wrong identity, unknown semantics/session, API failure, scale/currency error or
corporate-action ambiguity—prevents valuation judgement and baseline
activation. Basic, base-diluted, and stress-diluted share bases remain separate,
as do unrestricted cash, restricted cash, debt, convertibles, preferred claims,
and locally calculated OCF-minus-CAPEX proxies.

Each candidate baseline links by hash to the current event bundle. Product and
underlying links remain separate (`SOXL != SOXX`, `MVLL != MRVL`). A stale or
blocking link constrains only the affected strategy scope and never changes
market-data provider readiness.

The non-authoritative compiler consumes the candidate baseline, valuation
snapshot when applicable, event link, completed-session overlay, current
portfolio state, and versioned policy. Only a `PASSED` compile may enter atomic
per-ticker Shadow activation. Manual compilation cannot update live strategy,
notification runtime, quantities, or orders.

After activation, a separate five-session observation state starts at
`FIRST_OBSERVATION_SESSION_PENDING`. Only a future officially verified,
finalized, delivered Post-Market run from clean committed main with unchanged
portfolio and policy hashes can count. Manual, replay, duplicate, preliminary,
unverified, or backfilled sessions never count, and five observations require a
human review rather than automatic promotion.
