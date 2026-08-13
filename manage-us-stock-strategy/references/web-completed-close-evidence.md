# Selective Codex Web Completed-Close Evidence

This route is a bounded Shadow cross-check for decision-changing completed
closes. It is not a general browsing substitute and cannot upgrade live
execution.

1. Build a deterministic queue only for holdings/candidates whose decision
   boundary needs independent price evidence.
2. Open the original final source page. Search snippets, quote cards, news
   prices, social posts, and Yahoo-origin pages are rejected.
3. Extract security identity, exact session date, exact regular-session close,
   currency, price basis, source label, source timestamp, retrieval timestamp,
   and the normalized source text.
4. Hash extracted text locally and validate identity, timestamps, route,
   currency, basis, and provenance before numerical comparison.
5. Resolve the exact route ID against
   `workspace/policies/web_completed_close_route_registry.json`. Domain-wide
   trust is prohibited; ticker, source type, URL, field label, and price basis
   must all match the registered route.
6. Compare deterministically with the approved tolerance only after five
   distinct accepted route sessions make the exact route `SHADOW_APPROVED`.

Unknown routes remain `SOURCE_ROUTE_PENDING_REVIEW`. Inability to browse or to
find an exact dated close remains `INCONCLUSIVE`; do not fall back to a snippet,
an adjusted close, an intraday quote, or a second Yahoo endpoint.

The result exposes live and Shadow statuses separately. Shadow `MATCH` cannot
remove `VERIFICATION_PENDING`, create a quantity, mutate policy/portfolio
state, or create an order. Shadow `CONFLICT` is visible but remains non-live.

Web is an acquisition method, not a provider-capability record. Route health is
tracked separately. Three consecutive route failures suspend that exact route;
fallbacks need their own route IDs and acceptance histories. Generic Nasdaq
historical pages are not NOCP unless the page explicitly exposes that field and
listing-market semantics are verified. ETF sponsor market price must remain
separate from NAV, and issuer IR records need an explicit date and close field.
