# v2 Regression Report

## Conclusion

The implemented v2 safety and deterministic regression suite passed all
applicable bundled tests. Formal JSON Schema execution, exact v1-v2 outcome
comparison, and end-to-end append-only memory storage remain **NOT TESTED**.
Two cross-layer operational contract inconsistencies remain unresolved and
prevent readiness beyond controlled shadow use.

## PASS

- Python unit tests: **44 passed, 0 failed**.
- Python compile check: passed for all scripts and tests.
- Script self-tests: **8 passed, 0 failed**:
  `build_market_snapshot.py`, `evaluate_alerts.py`, `evaluate_outcome.py`,
  `option_analyzer.py`, `timing_engine.py`, `validate_decision_record.py`,
  `validate_research_packet.py`, and `validate_technical_snapshot.py`.
- JSON parsing: 59 repository JSON files parsed successfully in the validation
  audit; no parse errors.
- Local JSON Schema `$ref` resolution: no missing local reference.
- Markdown relative-link scan: no broken relative link.
- Skill frontmatter: valid canonical name and required description.
- Secret-pattern scan: no credential-like token or private-key marker found.
- Technical safety: official-session, raw-close, independent-close, indicator,
  early-close-volume, and required-symbol failures remain fail-closed.
- Leveraged quote safety: the direct leveraged-product close is mandatory;
  MRVL/SOXX proxy data can corroborate but cannot replace MVLL/SOXL price.
- Timing safety: EMA rearm, cooldown, hard-risk priority, gap/halt watch-only,
  no inferred fill, and SOXL 10-EMA watch-only behavior passed.
- Decision safety: non-held sell, look-ahead evidence, and Risk Controller
  action upgrade are rejected; valid watch-only fixture passes.
- Approval separation: watchlist inclusion does not grant new-buy, short,
  quantity, leverage-budget, strategic-allocation, or order authority.
- Current deterministic shadow evaluator: `DAILY_REVIEW`, grade `E`, no
  actionable candidate, no order placed or scheduled.

## FAIL / UNRESOLVED PRODUCT CONTRACT

1. `stock-strategy-system/alert_policy.json` and
   `stock-strategy-system/AUTOMATION_PROMPT_EN.md` reference
   `scripts/validate_research_cycle.py`, while the v2 Skill ships and documents
   `scripts/validate_decision_record.py`. The referenced cycle validator is not
   present in the canonical Skill package.
2. `stock-strategy-system/AUTOMATION_PROMPT_EN.md` contains a stale narrative
   statement that available cash is USD 0, while verified portfolio state is
   USD 3,264.31. The deterministic evaluator correctly reads state, but the
   prose can mislead an operator or free-form research layer.
3. `manage-us-stock-strategy/templates/research-report.md` uses legacy Research
   Manager disposition names that differ from the canonical validator contract.

These findings do not authorize automatic fixes to active policy or portfolio
state. They require a separately reviewed operational-contract migration.

## NOT TESTED

- Draft 2020-12 JSON Schema execution with an independent schema engine:
  `jsonschema` is not bundled. The standard-library validator was tested, but
  full contract equivalence is not proven.
- Official `skill-creator` quick validation: PyYAML is not bundled. Manual
  frontmatter and package checks passed.
- True point-in-time v1-v2 A/B: no eligible immutable evidence bundle.
- Historical outcome comparison, MAE, and MFE: no eligible A/B decision case.
- Live primary-source identity, fundamentals, valuation, and technical evidence
  for all ten user-defined AI Agent theme names in one common cutoff.
- Append-only production decision-memory writer and retention controls.
- Brokerage integration or order execution, which is intentionally outside
  scope.

## Evidence Commands

```powershell
& '<bundled-python>' -m unittest discover -s manage-us-stock-strategy/tests -p 'test_*.py' -v
& '<bundled-python>' -m compileall -q manage-us-stock-strategy/scripts manage-us-stock-strategy/tests
& '<bundled-python>' manage-us-stock-strategy/scripts/evaluate_alerts.py `
  --state stock-strategy-system/portfolio_state.json `
  --policy stock-strategy-system/alert_policy.json `
  --snapshot stock-strategy-system/transient_snapshot_2026-08-10.json `
  --output-locale en-US
```

## Regression Verdict

**PARTIAL PASS FOR SHADOW USE.** Bundled deterministic controls pass. The
unresolved operational contract references must be reconciled and re-tested
before human-assisted live review is approved.
