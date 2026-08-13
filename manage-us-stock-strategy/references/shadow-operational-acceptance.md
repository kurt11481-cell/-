# Cohort-Based Shadow Operational Acceptance

The 20-session process measures scheduled post-market delivery and safety. It
is not a counter that a manual smoke test or historical replay may advance.

## Eligible session

One session counts only when the official completed session is validated, the
run is an actual delivered `Morning Portfolio Strategy` scheduled run from
committed `main`, deployment and registry hashes pass, portfolio hashes before
and after match, all three held-ticker baseline states are present, and no
critical violation exists.

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
