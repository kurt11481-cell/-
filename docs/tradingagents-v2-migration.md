# TradingAgents-Informed V2 Migration

## 1. Original Architecture

The original system separated evidence research, deterministic market and
technical calculations, portfolio state, alert policy, runtime deduplication,
and human approval. Legacy schema-1.1 research packets were validated before
the independent alert evaluator reconstructed any next-session candidate.

## 2. Preserved Functionality

- `stock-strategy-system/portfolio_state.json` remains the operational source
  of holdings, verified cash, cost basis, and user-confirmed fills.
- `stock-strategy-system/alert_policy.json` remains the active deterministic
  alert and timing policy.
- `stock-strategy-system/alert_runtime_state.json` remains runtime/dedup state.
- Existing market snapshot, technical timing, options, portfolio, alert,
  localization, and legacy research-packet paths remain stable.
- Human approval remains mandatory; no code places or schedules orders.

## 3. Extended Functionality

- Added explicit Research Manager, Trader, independent Risk Controller, and
  Portfolio Manager contracts.
- Added canonical review labels and deterministic transition constraints.
- Added two-stage tactical candidate selection with one preferred and one
  alternative maximum and `WAIT` as a valid result.
- Added locked decision records, append-only outcome evaluation, and future
  calibration guidance.
- Added a research-only instrument registry and tactical universe.
- Added direct leveraged-product quote resolution with proxy corroboration.

## 4. Refactored Functionality

The canonical Skill remains `manage-us-stock-strategy/`. The duplicate
`stock-strategy-system/skill-staging/manage-us-stock-strategy/` tree is retained
but excluded from Git and is not an authority source. Its direct leveraged
quote safety design was incorporated into the canonical technical validator.
The old staging lifecycle validator was not promoted: v2 decision validation
and append-only outcome evaluation supersede that duplicate path while the
legacy schema-1.1 validator remains intact.

## 5. New Files

- References: `decision-orchestration.md`, `decision-memory.md`,
  `scoring-calibration.md`, `candidate-selection.md`, `research-lifecycle.md`.
- Schemas: evidence, analyst, research packet, trade proposal, risk review,
  portfolio decision, and decision record v2 schemas.
- Templates: research report, decision card, and postmortem.
- Scripts: `validate_decision_record.py`, `evaluate_outcome.py`, and
  `resolve_leveraged_quote.py`.
- Policies: `workspace/policies/instrument_registry.json` and
  `workspace/policies/tactical_candidate_universe.json`.
- Evaluation: rubric plus MRVL, SNDK, NBIS, AVGO, LITE, and SOXL case guides.

## 6. Modified Files

- `SKILL.md`: added minimal routing to v2 orchestration, tactical selection,
  memory, and outcome evaluation; existing routes and authority order remain.
- `references/multi-agent-research.md`: preserved legacy schema-1.1 behavior
  and pinned provenance while adding the v2 role chain.
- `references/trade-timing-validation.md` and `references/yfinance-data.md`:
  clarified that an underlying proxy corroborates but never substitutes for a
  direct leveraged-product close.
- `scripts/validate_technical_snapshot.py`: validates optional leveraged proxy
  evidence and recomputes tracking error.
- `tests/test_evaluate_timing_integration.py`: derives the watch-only reason
  from verified cash state instead of assuming zero cash.
- `AGENTS.md`: added concise authority, language, validation, and canonical-path
  rules without duplicating investment methodology.

## 7. TradingAgents Concepts Adapted

Role separation, analyst specialization, bull/bear steelmanning, Research
Manager resolution, Trader proposal structure, independent risk review,
Portfolio Manager review, decision memory, reflection, and calibration were
adapted conceptually. TradingAgents execution and simulated brokerage paths were
not adopted.

## 8. TradingAgents Provenance

The existing pin is unchanged:

- Commit: `a33fd4c0f134485a43553a2c23a63cb14adbd88f`
- Package version: `0.3.1`
- Source: https://github.com/TauricResearch/TradingAgents/tree/a33fd4c0f134485a43553a2c23a63cb14adbd88f
- Paper: https://arxiv.org/abs/2412.20138

## 9. Third-Party Code

No TradingAgents source code was copied. The implementation is an independent
conceptual adaptation, so no new third-party code attribution block was needed.

## 10. Tactical Universe Added

Research-only watchlist candidates are MVLL, SOXL, NBIS, FSLY, RBRK, NET, NOW,
MDB, DDOG, SNOW, CRWD, PANW, and PLTR. MRVL and SOXX are registered as reference
proxies. Every tactical candidate has `watchlist_approved=true` and
`new_buy_approved=false`. Short approval is false for every entry.

User-defined organizational subthemes are:

- application/workflow: NOW, PLTR
- data/database: MDB, SNOW
- runtime/edge/observability: DDOG, NET, FSLY
- security/data protection: CRWD, PANW, RBRK

These tags do not claim AI revenue purity, product availability, or verified
monetization.

## 11. Strategic Versus Tactical Separation

The tactical universe has `strategic_allocation_effect=none`. It does not add
symbols to the strategic core, activate a recurring alert, or authorize an
order. The existing portfolio policy continues to govern strategic allocation.

## 12. Workspace Policy Values Moved

No active operational value was moved. New research-only policy now owns:

- tactical candidate membership;
- organizational lane and subtheme tags;
- explicit watchlist status;
- explicit absence of new-buy and short approval;
- known proxy relationships and leverage factors already present in active
  policy for MVLL/MRVL and SOXL/SOXX.

## 13. Values Intentionally Not Moved

Holdings, cash, fills, cost basis, timing stages, loss boundaries, EMA rules,
alert grades, approved quantities, freshness windows, dedup metadata, and active
strategy versions remain in `stock-strategy-system/`. Effective leverage is not
replaced by a new registry formula until an equivalence test proves the active
result is unchanged.

## 14. Unresolved Classification Issues

- FSLY, RBRK, NET, NOW, MDB, DDOG, SNOW, CRWD, PANW, and PLTR identities are
  user-supplied and require primary-source verification before live policy use.
- The research-only registry is intentionally broader than the operational
  alert registry. A later user-approved migration is required before any new
  candidate enters active alert logic.
- No approved new-buy quantity or new-buy instrument permission was found.
- The operational README contains legacy encoded and duplicated state text; it
  was not used as authority and should be cleaned in a separate documentation
  change to avoid mixing that cleanup with v2 behavior.

## 15. Backward Compatibility

All active operational file paths remain unchanged. Legacy research packets,
market snapshots without leveraged proxy evidence, options analysis, timing
policy, alert evaluation, localization, and automation remain supported. The
technical validator only evaluates the new proxy block when it is present.

## 16. Validation Performed

- Parsed 11 new schema, policy, and decision-fixture JSON files and resolved all
  local schema references.
- Verified all 13 tactical symbols are watchlist-approved but not new-buy or
  short-approved in both policy layers.
- Skill package validation: passed.
- Python compile check: passed.
- Full Skill test suite: 44 tests passed, 0 failed.
- Existing and new script self-tests: passed.
- Valid test-only decision: deterministically returned `WATCH_ONLY`.
- Intentional look-ahead/non-held-sell fixture: deterministically rejected.
- Markdown relative-link scan: 29 files checked, no broken link found.
- Secret and authority-language scan: no credential-like secret found; all
  order references preserve no-order or review-only authority.
- `git diff --check`: passed before final staging and is repeated before commit.

Before the v2 work, one existing integration test failed because it hard-coded
the former zero-cash watch reason after verified positive cash entered state.
The operational evaluator was correct. The test now derives its expected reason
from verified cash; this was a stale-test correction, not a policy change.

## 17. Remaining Risks

- JSON Schema files are contracts, while the runtime validator uses standard
  library checks because no JSON Schema package is bundled. Both must be kept in
  sync through tests.
- Candidate identity and current fundamentals still require live primary
  evidence at decision time.
- LLM research remains non-deterministic; only structured artifacts and the
  deterministic gate are reproducible.
- Outcome calibration can be misleading with small, selected, or regime-biased
  samples.

## 18. TODOs

- Add frozen point-in-time evaluation fixtures when legally and operationally
  available.
- Add an approved schema-validation dependency only through a separate reviewed
  dependency change.
- Evaluate registry-driven effective leverage against the current active
  calculation before any migration.
- Add an append-only decision-memory writer after storage location and retention
  policy receive explicit user approval.

## 19. Exact Next Steps Before Merge

1. Review the feature-branch diff and this migration report.
2. Confirm that no tactical symbol should receive new-buy or short approval.
3. Confirm that the broader research universe must remain separate from alerts.
4. Review all validation output and any pre-existing failures.
5. Open a Pull Request from `feature/tradingagents-v2` to `main`.
6. Merge only after explicit user approval; do not push or merge automatically.
