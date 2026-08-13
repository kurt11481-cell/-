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
5. Compare deterministically with the approved tolerance only after the route
   is `SHADOW_APPROVED`.

Unknown routes remain `SOURCE_ROUTE_PENDING_REVIEW`. Inability to browse or to
find an exact dated close remains `INCONCLUSIVE`; do not fall back to a snippet,
an adjusted close, an intraday quote, or a second Yahoo endpoint.

The result exposes live and Shadow statuses separately. Shadow `MATCH` cannot
remove `VERIFICATION_PENDING`, create a quantity, mutate policy/portfolio
state, or create an order. Shadow `CONFLICT` is visible but remains non-live.
