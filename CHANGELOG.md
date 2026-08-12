# Changelog

## v2.3 - Portfolio Strategy Orchestrator

- Added a read-only combined holding-strategy, tactical-opportunity, and capital-
  redeployment orchestrator for human review.
- Added strict holding-strategy, capital-redeployment, and combined-report
  schemas with separate strategy, execution, and data-domain statuses.
- Preserved operational hard-risk precedence and exact deterministic tranche
  provenance while leaving quantity null when current authority is absent.
- Separated verified cash, projected sale proceeds, and unsettled or unconfirmed
  proceeds; only verified cash contributes to execution purchasing power.
- Added transition/dedup runtime metadata, a combined morning automation prompt,
  Korean-facing decision-card labels, and a fail-closed current shadow run.
- Preserved the exact v2.2 tactical universe: MVLL, SOXL, NBIS, BE, TOST, NOW,
  and FSLY.
- Did not add brokerage execution, inferred fills, inferred cash, automatic
  quantity, leverage approval, short approval, or portfolio-state mutation.

## v2.2 - Tactical Opportunity Radar

- Added a seven-symbol morning tactical research radar for MVLL, SOXL, NBIS,
  BE, TOST, NOW, and FSLY.
- Separated opportunity quality from execution eligibility so missing cash or
  permission cannot erase research visibility.
- Made the workspace instrument registry the canonical research authority and
  added deterministic policy-cache drift validation.
- Added candidate-disposition, radar-report, runtime-state, and transition-event
  schemas plus state-transition/dedup tests.
- Added bounded deep-research shortlist semantics and preserved inactive
  historical AI-agent registry records.
- Added a Codex-only morning automation contract and read-only shadow run.
- Added forward-tested fail-closed controls for stale sessions, context-based
  technical upgrades, event-policy authority, condition IDs, output paths,
  schema-before-write validation, and validated deep-research completion.
- Did not add brokerage execution, inferred fills, quantities, leverage
  approval, short approval, or portfolio-state mutation.

## Unreleased

### Added

- V2 role-separated decision orchestration with deterministic authority gates.
- Research-only tactical candidate universe and instrument registry.
- Locked decision records, append-only outcome evaluation, and calibration guidance.
- Leveraged-product direct-close resolution with proxy corroboration.
- Evaluation rubric and point-in-time case requirements.
- V2.1 Event Risk Layer with explicit incomplete-coverage status and historical
  knowledge-time validation.
- Source Capability Registry, provider-health circuit state, approved-fallback
  checks, and canonical market-record contract.
- Run manifests, result/input hashing, schema-contract audit, repeated-decision
  stability comparison, and three-layer evaluation harness.
- Current fail-closed tactical shadow artifacts for the 2026-08-10 completed
  session.
- Privacy-safe OpenAI repeated-decision stability harness and immutable public
  NBIS validation artifacts.

### Changed

- Extended Skill routing and multi-agent documentation without changing active policy.
- Extended technical validation for optional leveraged-proxy integrity evidence.
- Updated the timing integration test to follow verified cash state.
- Corrected operational validator paths, removed stale hard-coded cash prose,
  and aligned the research-template disposition enum with the v2 schema.
- Added event visibility to tactical Stage 1 without changing trade authority.
- Added a writable yfinance cache, excluded incomplete current-day daily bars,
  verified exact official market sessions, and aligned the tactical calendar
  enum with the canonical snapshot contract.

### Safety

- No new-buy, short-sale, quantity, execution, or policy authority was granted.
- Portfolio state, alert runtime state, and active strategy policy remain unchanged.
- Provider failure cannot silently reuse stale data or become a market signal.
- Historical current-social and future-published evidence are rejected.
- No event, fallback, benchmark proposal, or research consensus grants purchase,
  quantity, leverage, short-sale, alert, or brokerage authority.
- Private holdings, cash, cost basis, fills, and runtime state are excluded from
  external LLM stability inputs.
