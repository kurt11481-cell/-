# Future Order Readiness

Current execution authority is `NONE`.

- Broker Event Shadow: `TESTED_ONLY`, live F4/F5 acceptance not verified.
- Reconciled Broker State: `TESTED_ONLY`, open-orders visibility is not sufficient.
- ORDER_INTENT_ONLY: `TESTED_ONLY`, proposed quantity remains null.
- Independent Risk Kernel: `TESTED_ONLY`, current incomplete broker state is rejected.
- Execution Gateway Dry-Run: `TESTED_ONLY`, write endpoints are identified but never called.
- Kiwoom open orders: `API_RESPONSE_ERROR`.
- Kiwoom current-day fills: query available; empty output is not interpreted as none.
- Kiwoom realized P/L: `API_RESPONSE_ERROR` for current adapter route.
- Daily/period order and realized-P/L coverage: `OFFICIAL_API_SUPPORTED_ADAPTER_MISSING`.
- Blind retry after `ACK_UNKNOWN`: prohibited; reconciliation is required.
- Manual HTS/MTS activity: classified as `EXTERNAL_MANUAL_ORDER_DETECTED`; never auto-canceled.

Stage 16 is not eligible. Future eligibility requires live broker-event
acceptance, sufficient open-order visibility, REST/event reconciliation,
duplicate protection, freshness, partial-fill and unknown-ack validation, a
kill switch, operational maturity, and explicit exact-scope user approval.
