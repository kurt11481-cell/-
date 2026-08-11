# v2.1 Production Readiness

## Conclusion First

**READINESS: READY_FOR_SHADOW_USE**

The v2.1 branch is safer and more auditable than the pre-hardening v2 tag, but
it is not yet eligible for main merge. The current live shadow failed closed
when yfinance was unreachable, so no candidate reached the repeated live LLM
decision path. The required live identical-input authority-stability gate is
therefore `NOT TESTED`, which blocks `READY_FOR_HUMAN_REVIEW_USE`.

Automated brokerage execution is outside scope in every readiness state.

## Readiness Assessment

| Area | Status | Evidence |
|---|---|---|
| Architecture | PASS | Role authority and deterministic gate order remain intact. |
| Evidence integrity | PASS | Unsupported or future-known historical evidence fails closed. |
| Data-provider resilience | PASS | Provider state, bounded retry, no stale fallback, and approved-fallback checks are tested. |
| Point-in-time integrity | PASS | Current social data and future publications are rejected in historical runs. |
| Event risk | PARTIAL | Macro events surfaced; corporate, options, and index-event coverage remains incomplete and visible. |
| Technical validation | PASS | Existing technical, proxy, gap/halt, EMA rearm, and hard-risk controls still pass. |
| Options safety | PASS | Existing option analyzer self-tests pass; no option output creates order authority. |
| Portfolio safety | PASS | Portfolio state was not mutated; no cash, fill, quantity, or approval was inferred. |
| Alert separation | PASS | Research cannot escalate directly to the alert engine or place an order. |
| Reproducibility | PARTIAL | Numeric/evidence contracts and manifest pass; exact LLM prose is not promised. |
| Decision stability | BLOCKED | Test fixture is stable across three runs; current live candidate repetition is `NOT TESTED`. |
| Evaluation harness | PASS WITH LIMITS | Safety/quality/economic layers execute; costs and active benchmark mapping still require approval. |
| Tactical engine | PASS | Exact 13-name universe, event gate, and approval separation are enforced. |
| Current shadow | SAFE FAIL-CLOSED | yfinance unavailable; final status `DATA_INCOMPLETE`, no shortlist, `WAIT`. |
| Git integrity | PASS BEFORE MERGE | Work is isolated on `feature/v2.1-production-hardening`; main is unchanged. |

## Resolved v2 Operational Contract Issues

1. Operational validator paths now resolve from the workspace root to existing
   canonical v2, legacy packet, and schema-contract validators.
2. Current cash is read only from verified `portfolio_state.json`; stale cash
   prose was removed from the automation prompt and README.
3. The research template uses the canonical Research Manager enum:
   `RESEARCH_COMPLETE`, `RESEARCH_CONDITIONAL`, `RESEARCH_REJECTED`.
4. Repository schemas are executed by an independent deterministic supported-
   dialect validator and audited to reject unsupported keywords. A separately
   installed external Draft 2020-12 package is still `NOT TESTED`.

## Merge Blocker

The current immutable live bundle produced no Stage-2 candidate because the
market provider failed. The fixed three-run validation fixture proves the
stability harness, not live LLM authority stability. Merge gate 18 therefore
remains unmet.

## Explicit Exclusion

There is no `READY_FOR_AUTOMATED_TRADING` state. Every trade remains an external
human decision and manual broker action.
