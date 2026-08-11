# MVLL Quote Resolution and Research-Cycle Review

## Conclusion

- The MVLL completed-session close for 2026-08-10 is verified at USD 24.61.
- The conflicting historical-table value from the same independent page is not
  used because the timestamped regular-session header is the direct close field.
- MRVL is used only as a supplemental leveraged-return integrity check. It never
  substitutes for a direct MVLL quote.
- The corrected snapshot passes technical validation. MVLL currently has no
  active deterministic timing candidate; this is a no-signal result, not a data
  validation failure.
- The research system now has an auditable cycle from evidence collection to
  counter-case, scenario analysis, pre-trade decision, local disclosure, and
  append-only post-evaluation. It never places or schedules an order.

## MVLL resolution evidence

For the completed 2026-08-10 U.S. regular session:

- MVLL raw close: 24.610000610351562
- MVLL previous close: 27.110000610351562
- MVLL daily return: -9.221689%
- MRVL raw close: 208.55999755859375
- MRVL previous close: 218.72000122070312
- MRVL daily return: -4.645210%
- Expected MVLL daily return at 2x: -9.290420%
- Tracking error: +0.068731 percentage points
- Proxy tolerance: 1.00 percentage point

The small tracking difference strongly corroborates the direct MVLL close, but
does not independently establish it. The direct independent close still must
match the raw completed-session MVLL close within the configured tolerance.

## Deterministic resolution order

1. Require a raw, unadjusted, completed regular-session MVLL close.
2. Require a direct independent MVLL close with an explicit session timestamp.
3. Reject stale dates, after-hours values, adjusted values, and historical-table
   rows that conflict with the timestamped completed-session header.
4. Compare the direct close using `max(USD 0.05, 0.10%)` tolerance.
5. Optionally compare MVLL daily return with `2 x MRVL daily return`, allowing a
   separate 1.00 percentage-point tracking tolerance.
6. Fail closed if the direct MVLL check fails. A passing MRVL proxy cannot rescue
   a missing or failed direct MVLL quote.

## Repeatable investment-research cycle

Each qualitative escalation must use these immutable stages:

1. Research current filings, market data, material news, macro transmission,
   valuation, technical state, and portfolio exposure.
2. Write the strongest opposing thesis and objective falsification tests.
3. Record bull, base, and bear scenarios with confirmation and invalidation
   conditions under relevant market regimes.
4. Before a user-executed transaction, record the proposed action, horizon,
   rationale, gates, failure conditions, and review dates.
5. Save a local disclosure artifact with evidence and state/policy/snapshot
   hashes. External publication requires separate authorization.
6. After an explicit fill or explicit no-trade decision, append evaluations at
   5, 20, and 60 completed sessions and at named catalyst dates.
7. Never rewrite the original decision. Proposed policy changes require repeated
   comparable evidence and cannot mutate holdings, cash, fills, or orders.

## Validation performed

- Installed-skill unit tests: 42 passed.
- Skill package structural validation: passed.
- Corrected MVLL technical snapshot validation: passed.
- Deterministic monitor on the corrected snapshot: passed.
- Current monitor result: SOXL B-grade 20EMA reduction review candidate for 24
  shares; MVLL has no active timing candidate; no order was placed or scheduled.

