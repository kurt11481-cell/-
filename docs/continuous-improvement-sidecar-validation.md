# Continuous Improvement Sidecar Validation

## Scope

This change adds a read-only analytics sidecar around immutable strategy
evidence. It does not modify the Stage-7 scheduler, operational maturity state,
portfolio state, alert policy, provider authority, or broker truth.

## Implemented contracts

- evidence-derived run provenance and maturity isolation;
- append-only, hash-chained, idempotent Unified Run Ledger;
- strict `decision_as_of` look-ahead rejection;
- separate immutable decision and +1/+5/+10/+20 completed-session outcomes;
- decision-quality and blocked-opportunity review;
- `MODELLED_ONLY` capital-reallocation counterfactuals;
- decision-flip and drift baseline observation without new thresholds;
- genuine-scheduled-only operational denominators;
- improvement findings, non-applying policy proposals, and Shadow experiments;
- independent read-only Judge.
- explicit TEST/LIVE decision-mode firewall and canonical run origins;
- independent Core, Portfolio Decision, and Improvement Analytics counter
  firewalls;
- versioned analytics engine/metric definitions and a zero-count v2 analytics
  cohort, with the empty v1 cohort preserved as superseded.

## Validation fixture boundary

The checked-in fixture is `TEST_ONLY`. It contains one verified Manual, Replay,
Test-Only, and Shadow-Counterfactual record, and no genuine Scheduled record.
Therefore its
maturity-eligible count is zero. It uses a bounded historical completed-session
series only to test outcome indexing. It does not claim an operational run or
future outcome that has not occurred.

## Preserved invariants

- `portfolio_state.json` hash unchanged;
- integrated Shadow progress hash and counters unchanged;
- scheduler configuration hash unchanged;
- no live Kiwoom or order endpoint calls;
- `execution_quantity=null`;
- `quantity_authority=none`;
- `order_authority=false`;
- `POLICY_CHANGE_PROPOSAL.auto_apply=false`.

## Operational limitation

The production ledger begins empty. Real operational analytics remain pending
until genuine scheduled artifacts are ingested through verified deployment and
schedule provenance. Outcome horizons that lack completed future sessions stay
`OUTCOME_PENDING`.

The v2 analytics definition deliberately does not alter the Core Operational
or Portfolio Decision cohorts. It cannot be deployed from an uncommitted or
dirty working tree; the Scheduled Runtime continues using its previously
verified committed deployment until a separately authorized clean deployment.
