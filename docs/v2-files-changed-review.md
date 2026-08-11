# v2 Files Changed Review

## Conclusion First

The appropriate base is `main` at
`2419497e1f11873fa758dfc8eecdefa2e64572d0`. The complete staged Pull Request
diff changes 52 files with 3,886 insertions and 10 deletions. The underlying v2
implementation commit accounts for 42 files, 2,944 insertions, and 10 deletions;
the remainder is final validation evidence. No v2 feature change modifies
operational portfolio state, runtime/dedup state, or the active alert policy.
High-risk changes are concentrated in schema authority, decision validation,
technical proxy validation, and research-only instrument policy.

## Comparison Method

```powershell
git diff --stat main...feature/v2-final-validation
git diff --name-status main...feature/v2-final-validation
git diff --check main...feature/v2-final-validation
```

At validation start, `main...34ee4b4` reported 42 changed files, 2,944
insertions, and 10 deletions. After staging the validation artifacts,
`git diff --cached --shortstat main` reported 52 files, 3,886 insertions, and 10
deletions. Final validation artifacts are additive reports and read-only shadow
outputs.

## HIGH RISK

### `workspace/policies/instrument_registry.json`

- Before: no v2 research registry.
- After: exact identity, leverage, proxy, watchlist, new-buy, short, tactical,
  and reference classifications.
- Authority change: research classification increased; execution authority
  stayed constant at none. Every tactical symbol has new-buy false and short
  false; quantity and order authority are false.
- Validation: JSON parse; exact 13-name cross-check; MVLL/MRVL and SOXL/SOXX
  relationships traced to existing active policy; no strategic effect.

### `workspace/policies/tactical_candidate_universe.json`

- Before: no separate v2 tactical-screen contract.
- After: three lanes, deterministic Stage 1, selective Stage 2, no master score,
  at most one preferred and one alternative, and valid `WAIT`.
- Authority change: research-watchlist scope increased; new-buy, sizing, short,
  strategic-allocation, and order authority stayed absent.
- Validation: all 13 names exactly present; `watchlist_approved=true`,
  `new_buy_approved=false`, `short_approved=false`.

### `manage-us-stock-strategy/schemas/`

- Before: no v2 structured role/decision schema set.
- After: analyst, evidence, research packet, trade proposal, risk review,
  portfolio decision, and decision record contracts.
- Authority change: execution authority did not increase; schemas constrain
  quantity and role transitions. Schema surface is nevertheless high risk
  because it defines what downstream tools may accept.
- Validation: all JSON parses and local `$ref` targets pass. Independent Draft
  2020-12 runtime validation is not tested.

### `manage-us-stock-strategy/scripts/validate_decision_record.py`

- Before: no v2 end-to-end decision-record gate.
- After: enforces evidence cutoff, held/non-held action boundaries, risk
  downgrade-only behavior, portfolio review, and no external execution.
- Authority change: deterministic rejection authority increased; LLM/order
  authority stayed none.
- Validation: self-test and unit tests pass, including intentional look-ahead,
  non-held sell, and Risk Controller upgrade rejection.
- Residual risk: the standard-library validator does not execute every JSON
  Schema keyword and is not itself the active alert evaluator.

### `manage-us-stock-strategy/scripts/validate_technical_snapshot.py`

- Before: validated official session, critical closes, indicators, and related
  technical fields without the optional leveraged-proxy block.
- After: when proxy evidence is present, requires verified direct product close,
  verified proxy close, explicit tracking tolerance, and consistency.
- Authority change: decreased; proxy evidence adds a fail-closed requirement and
  cannot substitute for MVLL/SOXL direct price.
- Validation: technical suite and leveraged resolver tests pass; current MVLL,
  MRVL, SOXL, and SOXX shadow data passed.

### Timing and portfolio authority references

- Files: `references/trade-timing-validation.md`,
  `references/portfolio-policy.md`, and deterministic alert/timing scripts as
  inherited from the base.
- Before/after: v2 only adds related-underlying confirmation language; it does
  not change the existing hard-loss, staged-reduction, rearm, cooldown, or
  effective-leverage policy.
- Authority change: stayed constant.
- Validation: 44-test suite covers rearm, cooldown, hard-risk precedence,
  technical failure, no inferred fills, and stale state.

## MEDIUM RISK

- `references/multi-agent-research.md` and
  `references/decision-orchestration.md`: add role routing and transitions but
  explicitly subordinate them to deterministic policy.
- `references/candidate-selection.md`: adds shortlist logic with no trade
  authority and permits an empty shortlist.
- `references/decision-memory.md`, `references/research-lifecycle.md`, and
  `scripts/evaluate_outcome.py`: define immutable decision/outcome separation;
  no approved production writer exists.
- `scripts/resolve_leveraged_quote.py`: read-only identity/corroboration resolver;
  proxy substitution is rejected.
- `SKILL.md` and `AGENTS.md`: route additional workflows. They do not grant
  brokerage authority, but routing changes affect which validators are used.
- `templates/research-report.md`: contains a legacy Research Manager enum that
  does not match the canonical validator and must be fixed before live review.

## LOW RISK

- `CHANGELOG.md`.
- `docs/` migration, readiness, runbook, and final-validation reports.
- `evals/` rubric, A/B eligibility report, baseline manifest, and regression
  report.
- `workspace/outputs/` read-only tactical shadow output.
- Test fixtures and unit tests, except where they are evidence for a high-risk
  contract.

## Explicit No-Change Findings

- `stock-strategy-system/portfolio_state.json`: not changed or staged.
- `stock-strategy-system/alert_runtime_state.json`: not changed or staged.
- `stock-strategy-system/alert_policy.json`: no v2 feature diff.
- `workspace/state/`: does not exist; no state migration occurred.
- Options safety methodology: not weakened.
- No new-buy true, short true, or automatic-order permission was found.

## Unresolved Cross-Layer Findings

1. Active policy and automation prompt refer to a missing
   `validate_research_cycle.py` instead of the canonical v2 decision validator.
2. Automation prompt prose still says verified cash is USD 0, conflicting with
   verified state USD 3,264.31.
3. Research template disposition names differ from canonical enum values.

These issues are why the recommendation is `DO NOT MERGE YET`, even though the
validation/report commit itself is safe to create for review.
