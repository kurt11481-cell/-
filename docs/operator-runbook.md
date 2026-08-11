# v2 Operator Runbook

## Operating Rule

Use the system for research and review candidates only. A valid result may be
`WAIT`, `NO TRADE`, or failed validation. Never interpret a touched price as a
fill and never let a research role override deterministic policy.

## A. Single-Stock Analysis

Example request: `MRVL 분석`.

1. Confirm the exact ticker and security identity.
2. Set the analysis cutoff and latest completed U.S. session.
3. Prefer filings, IR, and official sources; timestamp every material claim.
4. Build the causal thesis, strongest counter-thesis, valuation conclusion,
   validated technical regime, invalidation, and unresolved conditions.
5. Return a review state, not an order.

## B. Tactical Candidate Scan

Request a scan of MVLL, SOXL, NBIS, and the user-defined AI Agent universe.

1. Stage 1 checks identity, evidence, liquidity, valuation rejection, technical
   validity, and portfolio eligibility.
2. Deep-research only three to five eligible names. If none pass, stop.
3. Compare within lanes; do not create one fake master score across leveraged
   ETFs, infrastructure, and software/security names.
4. Select at most one preferred and one alternative candidate. Neither is
   required.

## C. Held-Position Review

1. Read verified broker state; do not infer holdings from an old report.
2. Verify direct instrument close and, for MVLL/SOXL, the MRVL/SOXX proxy.
3. Check hard loss, peak drawdown, time stop, gap/halt, EMA rearm/cooldown, and
   approved staged-reduction slots.
4. Only held positions may receive `TAKE_PROFIT_REVIEW`, `REDUCTION_REVIEW`, or
   `STOP_REVIEW`.

## D. Post-Market Alert Review

1. Confirm the latest completed regular session on the official calendar.
2. Build a fresh market snapshot sequentially with the configured request pace.
3. Validate the snapshot and run `evaluate_alerts.py` without `--commit-runtime`
   for a dry run.
4. Treat every output as a next-session human review candidate.
5. Commit runtime/dedup metadata only in the approved scheduled monitor; never
   change portfolio facts.

## E. Decision-Memory Review

Use memory only for the original thesis, evidence IDs, decision, invalidation,
and later calibration. Memory is not current-market evidence. Never rewrite the
original decision after observing the outcome.

## F. Outcome / Postmortem Review

After the defined horizon, use `evaluate_outcome.py` with a valid benchmark and
complete price path. Keep confirmation/invalidation and outcome facts separate.
Do not change policy because of one memorable result.

## G. When Data Validation Fails

- Stop the affected decision path.
- Label the missing or conflicting field.
- Use `WAIT`, watch-only, or grade `F/E` as required.
- Do not substitute MRVL for MVLL or SOXX for SOXL.
- Retry only with a new verified completed-session snapshot.

## H. Before Accepting `BUY_REVIEW`

Confirm all of the following: exact instrument approval, verified cash,
approved quantity/risk budget, thesis pass, valuation pass, technical pass,
liquidity pass, portfolio concentration/effective-leverage pass, and explicit
human approval. Watchlist membership alone is insufficient.

## I. Before Accepting Reduction or Stop Review

Confirm verified current shares, the exact active policy rule, completed-session
market evidence, slot/rearm/cooldown status, and a non-null policy-authorized
quantity where required. A price crossing without a user-confirmed fill does
not update holdings.

## J. Never Automatic

The system must never place or schedule orders, infer fills or cash, invent
quantities, grant leverage or short authority, move tactical names into the
strategic portfolio, or let LLM consensus override the deterministic gate.
