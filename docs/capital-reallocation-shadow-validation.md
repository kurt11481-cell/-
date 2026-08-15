# Capital Reallocation Shadow Validation

## Scope

This change adds a deterministic Shadow review layer after the finalized
post-close event refresh and holding compile. It does not modify Live strategy,
portfolio facts, broker cash, scheduler timing, operational maturity counters,
quantity authority, or order authority.

The implementation is in
`manage-us-stock-strategy/scripts/portfolio_reallocation_shadow.py`. The
versioned action matrix and safety policy are in
`workspace/policies/portfolio_reallocation_shadow_policy.json`.

## Decision behavior

Every verified positive holding emits `ADD_CASE`, `HOLD_CASE`, `TRIM_CASE`, and
`EXIT_CASE`. Selection priority is hard risk, thesis exit, risk-reducing trim,
rotation review, add review, then hold. A non-breached maximum-loss rule does
not by itself prove a hold case.

Event readiness is evaluated separately for NEW_BUY, ADD, HOLD, TRIM, and EXIT.
Insufficient material-event evidence blocks BUY/ADD. It does not alone veto a
risk-reducing trim, and a verified hard-risk or thesis-invalidating exit can
proceed to human review while retaining the evidence limitation.

Profit protection has no fixed production percentage. A trim requires an
approved upstream deterministic trigger; a large profit with strong trend and
healthy volume can remain `HOLD_TIGHTEN_STOP`.

## Capital and portfolio safety

Hypothetical trim ratios require policy authority. Test-only ratios are allowed
only in fixtures. Full thesis/hard-stop exits can use a 100% Shadow ratio.
Expected proceeds and hypothetical post-sale cash are both `SHADOW_ONLY`.
`verified_orderable_cash_from_expected_proceeds_usd` is fixed at zero and the
funding authority remains `VERIFIED_ACTUAL_CASH_ONLY`.

The portfolio optimizer exposes risk before and after the hypothetical sale,
but its numeric diagnostics have no decision authority. It compares only
hard/risk/event/portfolio-fit eligible candidates with `KEEP_CASH`; it does not
create a direct sell-to-buy link. Sell and buy risk decisions remain separate.

## Cohort and scheduler

The portfolio-decision semantic cohort begins at 0 with no backfill. Existing
scheduler/provider operational counters remain intact. The scheduled runtime's
09:00 ET Pre-Open, 16:30 ET Post-Close, and T+30/T+40/T+50/T+60 finalization
model were not changed. Manual and test-only validation does not count as a
genuine operational pair.

## Validation evidence

The deterministic fixture is explicitly `TEST_ONLY` and covers SOXL, MVLL, and
NBIS with different synthetic decision paths. It is not a live strategy
recommendation. The generated report and Judge artifact are stored under
`workspace/outputs/activation/capital-reallocation-shadow/2026-08-15-test-only/`.

The independent Judge recomputes the event matrix, post-close ordering, all
four holding cases, profit-protection policy, reallocation/optimizer output,
ten axes, cash separation, portfolio hash, recursive authority safety,
scheduler hash equality, schemas, and targeted tests.

## Remaining operational boundary

The repository prompt now requires the Shadow layer after event refresh, but a
future genuine scheduled Post-Close run is still required to prove operational
delivery of this new layer. The test-only run does not increment scheduler or
portfolio-decision observations. Future actual execution remains not ready
while order/fill/open-order visibility and explicit execution authority are
absent.
