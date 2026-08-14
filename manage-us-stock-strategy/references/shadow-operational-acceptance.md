# Cohort-Based Shadow Operational Acceptance

The coverage-weighted 1/5/10/20/60-session process measures scheduled finalized
post-market delivery and safety. Only `POST_MARKET_FINALIZED` may count. It is
not a counter that preliminary or generic post-market analysis, a manual smoke
test, manual Run Now, historical replay, route-acceptance replay, or pre-open run
may advance.

Stage 1 verifies live read-only scheduled delivery. Stage 5 may only generate a
limited exact-scope approval proposal after replay, fault injection, broker
workflow, accepted-route, evidence, MATCH, research/baseline, and overlay gates
pass. Stage 10 adds queue coverage, correct unavailable/inconclusive handling,
ticker-local isolation, route health, and leveraged product/proxy separation.
Stage 20 is a maturity review. Stage 60 is append-only long-horizon evaluation.
No stage automatically mutates policy or authority.

The promotion scope is exactly `ticker + decision_class + source_route_id` and
also retains research/baseline hashes. Approval for one scope never extends to
another ticker, decision class, or route. Opportunity, price-evidence,
new-buy-approval, execution, and promotion states remain separate.

## Eligible session

One session counts only when the official completed session is validated, every
critical direct daily bar is the same-session stable `REGULAR_COMPLETED` Raw
close with `bar_finalized=true`, and the run is an actual delivered
`Morning Portfolio Strategy` `POST_MARKET_FINALIZED` scheduled run from
committed `main`. Deployment and registry hashes must pass, portfolio hashes
before and after must match, all three held-ticker baseline states must be
present, and no critical violation may exist.

Manual runs, unit tests, pre-open runs, backfills, unverified delivery, dirty
worktrees, and missing expected-session evidence are logged but excluded.
Session records form an append-only hash chain. Semantic code/policy changes
create a new cohort; ordinary evidence, URL, baseline-content, and market-data
changes do not.

Checkpoints occur at 5, 20, and 60 valid sessions. None promotes automatically.
The 20-session checkpoint requires zero critical violations, complete held-
ticker baseline coverage, at least five valid overlays per held ticker, no
stale technical/portfolio reuse, no raw LLM signal, no cross-ticker failure
propagation, and observed independent-price coverage. Promotion also requires
an audit, an approval record, and explicit user approval.

The task must record successful and failed scheduled attempts where possible.
Configuration and manual smoke never mean delivery verification.
