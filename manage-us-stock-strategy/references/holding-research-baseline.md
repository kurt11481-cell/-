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
