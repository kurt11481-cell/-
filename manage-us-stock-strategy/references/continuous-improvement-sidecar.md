# Continuous Improvement Evidence Sidecar

## Purpose and authority

The sidecar consumes immutable run, decision, outcome, and counterfactual
artifacts without changing the operational Stage-7 pipeline. It has no
portfolio, broker, quantity, order, maturity-counter, or production-policy
authority. An analytics failure is isolated from the genuine scheduled run.

## Run provenance and maturity isolation

Derive provenance from task, schedule, deployment, runtime-HEAD, semantic
cohort, trading-day, and runtime-manifest evidence. Never trust a caller's
`execution_origin` label. Canonical origins are `SCHEDULED_GENUINE`, `MANUAL`,
`REPLAY`, `TEST_ONLY`, and `SHADOW_COUNTERFACTUAL`; legacy `TEST` and `SHADOW`
labels are normalized before validation. `MANUAL`, `REPLAY`, `TEST_ONLY`, and
`SHADOW_COUNTERFACTUAL` records are
always maturity-ineligible. `PRE_OPEN_T_MINUS_30` remains maturity-ineligible;
only an otherwise eligible delivered finalized scheduled phase can qualify for
the existing operational gate.

Every decision carries one explicit mode: `LIVE_READ_ONLY`,
`MANUAL_READ_ONLY`, `REPLAY`, `TEST_ONLY`, or `SHADOW_COUNTERFACTUAL`. A
production decision consumer accepts only `LIVE_READ_ONLY`; mode/origin
mismatches fail closed. Analytics records also bind `analytics_engine_version`,
`metric_definition_version`, and `schema_version`.

The Unified Run Ledger is append-only and hash-chained. Its deterministic run
fingerprint makes repeated ingestion idempotent. The sidecar ledger is not the
Stage-7 counter ledger.

## Temporal and outcome contract

Reject the entire evaluation as `TEMPORAL_EVIDENCE_VIOLATION` when evidence is
newer than `decision_as_of`. Never silently drop the future evidence and keep
the evaluation. Keep the original decision immutable and append a distinct
forward-outcome artifact.

Evaluate +1, +5, +10, and +20 completed trading sessions. Missing future
sessions remain `OUTCOME_PENDING`. Preserve provider, price, adjustment,
session, and source-hash lineage. Kiwoom remains canonical inside its accepted
scope; provider values are never averaged.

## Analytics and governance

Decision-quality, blocked-opportunity, counterfactual, decision-stability,
drift, and operational analytics are observational. A later price increase
does not prove that an earlier fail-closed decision was wrong. Counterfactual
proceeds remain `SHADOW_ONLY` and never become broker cash.

An `IMPROVEMENT_FINDING` is not a policy change. Every
`POLICY_CHANGE_PROPOSAL` uses `auto_apply=false`, exact scope, evidence and
counter-evidence, risk disclosures, semantic impact, and rollback planning.
`SHADOW_POLICY_CANDIDATE` experiments use the same eligible evidence without
mutating production decisions, policy, state, counters, quantity, or order
authority.

## Safety invariants

- Prefer archived immutable evidence and give genuine scheduled traffic
  priority over analytics.
- Keep actual broker events and Shadow simulation events in separate
  namespaces.
- Preserve `execution_quantity=null`, `quantity_authority=none`, and
  `order_authority=false`.
- Do not reset or backfill Stage-7 counters.
- Do not mutate the Portfolio Decision cohort or counters. Analytics metric
  changes start a new Improvement Analytics cohort only.
- Reject Shadow proceeds as broker cash, Shadow quantity as execution
  quantity, and Shadow fills as actual broker fills.
- Do not invent drift or operational SLA thresholds; build observational
  baselines first.
