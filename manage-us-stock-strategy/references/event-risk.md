# Event Risk

Use this layer for high-consequence research, tactical screening, historical
evaluation, and live shadow review. Event risk is contextual and deterministic;
it is not an order or automatic sell signal.

## Event classes

- Corporate: earnings, investor day, ex-dividend date, material shareholder
  meeting, announced offering, lock-up, or corporate action when relevant.
- Macro: FOMC decision, CPI, PPI, PCE, and employment reports when relevant.
- Market structure: monthly or quarterly expiration, index rebalance, and
  confirmed index inclusion or deletion.

Retain separate `scheduled_at`, `announced_at`, `effective_at`, and
`retrieved_at` fields. In a historical run, an event is eligible only when its
relevant public-knowledge timestamp is no later than `analysis_cutoff`.
Future-known event data and undated event evidence fail closed.

Prefer company IR, filings, exchanges, OCC, index providers, central banks, and
government statistical agencies. News aggregators and social posts cannot be an
authoritative calendar.

## Authority

Event status may expose risk or downgrade to `WAIT` only when an already
approved generic safety rule requires deferral. It may not create a threshold,
quantity, fill, holding change, or order. Do not invent T-5, T-3, or T-1 rules.
Where an approved event window exists, cite its exact policy rule. Otherwise use
`CONTEXT_ONLY`.

Use `EVENT_DATA_INCOMPLETE` when coverage cannot be verified. Never translate
missing evidence into "no upcoming event." A validated event snapshot must pass
`scripts/validate_event_snapshot.py` before it enters a decision record.
