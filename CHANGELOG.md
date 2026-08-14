# Changelog

## v2.6.9 - Forward-Only Current Event-Risk Capture

- Added a current immutable event-risk bundle contract with explicit source,
  publication/effective/retrieval times, point-in-time eligibility, severity,
  strategy relevance, verification state, and per-ticker missing fields.
- Added a forward-only append-only event checkpoint with a deterministic hash
  chain, portfolio-state hash proof, and explicit provider/strategy/quantity/
  order non-authority.
- Added cutoff, future-evidence, append-only hash-chain, ETF/underlying
  separation, ticker-local failure, and portfolio-immutability regressions.
- Locked a current 2026-08-13 event bundle from official SEC, issuer IR, ETF
  sponsor, BLS, BEA, Federal Reserve, and OCC sources. Incomplete negative-event
  coverage remains visible as `EVENT_DATA_INCOMPLETE`.
- No provider readiness, live strategy state, portfolio fact, quantity, or
  order authority was changed.

## v2.6.8 - Finalized Post-Market Automation

- Moved the existing `Morning Portfolio Strategy` operational schedule from
  07:45 to 10:15 Asia/Seoul and selected one `SINGLE_FINALIZED_RUN` rather than
  creating a duplicate task.
- Added a deterministic `POST_MARKET_FINALIZED` delivery/counting envelope.
  Preliminary, generic post-market, finalization-pending, manual, replay,
  pre-open, stale, dirty, undelivered, and hash-mismatched runs cannot count.
- Required every critical direct daily record to be a stable, same-session USD
  `REGULAR_COMPLETED` Raw close with `bar_finalized=true` before delivery
  verification or Shadow counting.
- Preserved FSLY's ticker-local yfinance technical-history fallback, MVLL's
  `EMA10_RECLAIM_RVOL20` decision-class block, and separation of event readiness
  from provider readiness.
- Added phase-neutral urgent-state deduplication, explicit delivery-ID and
  scheduled-attempt lifecycle fields, AUTO-01 through AUTO-11 regressions, and
  a new zero-session semantic cohort.
- No order, fill, quantity, portfolio mutation, hard-risk threshold, timing
  quantity, or rearm authority was added.

## v2.6.7 - Session-Aware Kiwoom Operational Priority

- Added explicit premarket, regular-intraday, regular-completed, after-hours,
  day-market, overnight, closed, and unknown session normalization plus price
  basis, quote type, timestamp, stability, and finalization metadata.
- Added a comparability gate that classifies session, quote-type, price-basis,
  timestamp, and finalization mismatches as `NOT_COMPARABLE` rather than false
  price conflicts. The existing Raw-close tolerance is applied only afterward.
- Promoted Kiwoom to `KIWOOM_PRIMARY_GUARDED_SCOPED` for broker facts,
  broker-session quotes, finalized archived Raw closes, and validated Adjusted
  technical history. yfinance remains diagnostic Shadow and scoped fallback;
  Codex Web remains finalized regular-close conflict resolution only.
- Preserved extended-session limits: no daily indicators, hard-risk breach,
  WATCH-to-READY upgrade, close overwrite, quantity, order, or portfolio
  mutation.
- Isolated FSLY's insufficient Kiwoom history, MVLL's RVOL boundary conflict,
  and event-data incompleteness to their correct ticker/decision/domain scopes.
- Locked a sanitized session-aware acceptance manifest and reset the semantic
  operational cohort without backfilling replay or manual validation sessions.

## v2.6.5 - Kiwoom Replay History and Lock Hardening

- Replaced unsafe replay-lock cleanup with an atomic owner-token lock that
  preserves foreign and uncertain locks and quarantines only proven-dead stale
  locks after the versioned TTL.
- Added policy-bounded official Kiwoom daily-chart pagination, 252-bar history
  sufficiency, conflicting-duplicate and future-bar rejection, and sanitized
  page provenance.
- Added local Kiwoom technical validation plus separate Raw, adjustment-basis,
  Adjusted, indicator-shadow, and technical-decision-flip comparisons.
- Separated market-data provider replay from unavailable historical strategy
  context and added forward-only append-only point-in-time context capture.
- Added a 31-case fault harness and current-session dry-run support. Replay and
  dry-run outputs cannot deliver alerts, count operational sessions, mutate the
  portfolio, or change provider authority.
- yfinance remains Primary; Kiwoom remains
  `SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED`; `order_authority=false`.

## v2.6.4 - Kiwoom Read-Only Shadow Adapter

- Added a strict local subprocess JSON boundary to the unchanged official
  Kiwoom REST runtime; credentials, tokens, account data, and raw environment
  content never enter strategy artifacts.
- Added dynamic U.S. instrument resolution, separate raw and adjusted daily
  series, session locking, provider preflight, policy-paced bounded retry, and
  deterministic Kiwoom/yfinance raw-close comparison.
- Added schema validation, atomic output writes, output-alias protection, and
  offline regressions for order blocking, secret sanitization, ticker-local
  failure, exchange ambiguity, FX rejection, and portfolio immutability.
- yfinance remains Primary. Kiwoom remains disabled and
  `SHADOW_NOT_YET_OPERATIONALLY_ACCEPTED`; no operational Shadow count,
  provider promotion, quantity, portfolio mutation, or order authority was
  added.

## v2.6.3 - Massive-Free New-Buy Research and Staged Web Evidence

- Added research-only external discovery proposals and deterministic unsized
  new-buy strategy/approval drafts.
- Added an exact ticker/source/field Web route registry, five-session route
  acceptance, route fingerprints, and route suspension after repeated failure.
- Preserved READY/NEAR_TRIGGER opportunity quality while independent evidence
  is pending; Web MATCH changes only price evidence.
- Added exact-scope 1/5/10/20/60 promotion audits with explicit user approval
  and no automatic promotion.
- Added Korean beginner messages, Massive-free automation instructions, CI
  hygiene scans, and 70 focused offline regression tests.
- Did not change strategy version, hard-risk thresholds, timing quantities,
  EMA rearm, portfolio facts, new-buy approval, quantity, or order authority.

## v2.6 - Integrated Holding Research and Operational Shadow Acceptance

- Added immutable Shadow research baselines and daily overlays for NBIS,
  MVLL/MRVL, and SOXL/semiconductor-sector contexts.
- Added deterministic compilation with explicit valuation, technical,
  portfolio, hard-risk, and leveraged-product authority separation.
- Added selective Codex Web completed-close evidence validation and a disabled
  structured-provider onboarding framework; no Web result can upgrade live
  execution.
- Added cohort-based 5/20/60 scheduled Shadow checkpoints, append-only attempt
  and session records, explicit-user-approval promotion, and manual/backfill
  exclusion.
- Preserved v2.5 broker snapshot reconciliation and added beginner Korean Shadow
  explanations.
- Added GitHub Actions deterministic safety CI.
- Did not change strategy version, hard-risk thresholds, timing quantities,
  rearm rules, portfolio facts, order authority, or Pre-Open activation.

## v2.5 - Selective Price Evidence and Broker Snapshot Reconciliation

- Separated primary completed-close validity, technical recomputation, and
  selective independent evidence for decision-changing candidates.
- Preserved READY opportunity quality as `VERIFICATION_PENDING` when a queued
  independent close is unavailable; empty queues no longer create outages.
- Added ticker-local price-conflict handling, web-evidence provenance checks,
  decision-boundary comparison, and explicit SOXL/MVLL confirmation modes.
- Added beginner-friendly Korean portfolio rendering with deterministic
  priority and an explicit no-order notice.
- Added privacy-safe broker snapshot ingestion, extraction validation,
  reconciliation proposals, explicit-confirmation atomic apply, narrow snapshot
  requests, and shadow-only runtime migration.
- No strategy rule, broker order, inferred fill, quantity authority, scheduled
  task, or live portfolio/runtime mutation was added.

## v2.4 - Dual-Phase Portfolio Strategy and Pre-Open Refresh

- Added authoritative POST_MARKET strategy builds and bounded PRE_OPEN delta
  refreshes with immutable baseline and phase-specific manifests.
- Added provider-agnostic independent-close adapter, one-shot preflight,
  global/ticker failure scoping, and aggregated provider incidents.
- Added explicit hard-risk rule provenance and separated holding Risk State from
  Strategy State; unsupported breach-to-action mappings now fail closed.
- Added strict cash freshness/completeness gates, correct zero-cash
  `NO_FUNDED_ACTION`, projected/unsettled-proceeds exclusion, and held-ticker
  capital-use deduplication.
- Added premarket/event/baseline/runtime/policy schemas, pre-open authority tests,
  and automation delivery lifecycle state.
- Added two Codex-only automation prompts. No Windows scheduler, brokerage order,
  inferred fill, quantity, leverage authority, or short authority was added.
- Repaired the legacy mixed raw/normalized deployment hashes, synchronized the
  installed Skill, and added a fail-closed deterministic deployment validator.

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
