# v2 Operator Runbook

## v2.6 integrated Shadow operation

1. Run the ordinary v2.5 post-market read-only workflow from committed `main`.
2. Validate the active NBIS, MVLL, and SOXL slow baselines.
3. Build current overlays from the same canonical completed-session data and
   compile Shadow contexts. Never reuse baseline technical/portfolio fields.
4. Browse only a non-empty selective close queue. Unknown/stale routes remain
   pending; snippets and Yahoo-origin evidence are rejected.
5. Keep live and Shadow results side by side. Shadow never creates execution,
   quantity, policy, portfolio, or order changes.
6. Render the beginner Korean summary and broker snapshot request using the
   existing v2.5 confirmation boundary.
7. Record every scheduled attempt. Count only an actual delivered scheduled
   post-market run that satisfies the cohort policy. Manual smoke never counts.

At 5, 20, and 60 valid sessions, create an audit checkpoint. Never promote
automatically. A 20-session pass still requires independent-price coverage,
promotion review, and explicit user approval.

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

## K. v2.4 Post-Market Full Strategy

1. Verify the latest completed U.S. regular session.
2. Run one independent-close provider preflight before symbol processing.
3. Build one canonical market/event snapshot and read canonical broker state.
4. Produce separate holding Risk/Strategy states, Tactical Radar, strict Cash
   Status, redeployment review, POST_MARKET manifest, and immutable baseline.
5. Aggregate a provider-wide outage once; isolate symbol failures.
6. Hash portfolio state before and after. Any difference is critical failure.

`VERIFIED_ZERO` cash yields `NO_FUNDED_ACTION`; projected/unsettled proceeds do
not create purchasing power. A hard-risk threshold with unverified action
authority requires policy reconciliation, not automatic exit mapping.

## M. v2.5 Selective Price Evidence

1. Validate primary completed-session OHLCV and local technical calculations.
2. Build provisional opportunity and holding strategy states.
3. Queue independent close evidence only for decision-changing candidates.
4. Treat an empty queue as `NOT_REQUIRED`; do not call it a provider outage.
5. Preserve READY as `READY / VERIFICATION_PENDING` when queued evidence is
   unavailable. Keep quantity null.
6. Reject search snippets and Yahoo-origin web pages as independent evidence.
7. Keep direct conflicts ticker-local and never average raw/adjusted prices.

## N. Broker Snapshot Reconciliation

1. Ingest supported screenshots as one untrusted bundle. Never commit raw
   images or expose login, OTP, name, or full account number.
2. Validate structured extraction and choose the narrowest scope: full
   portfolio, holdings only, cash only, or one position.
3. Show a proposal and all unresolved fields to the user. Upload or extraction
   does not update state.
4. Apply only after explicit confirmation of proposal ID, bundle ID, state
   revision, and portfolio hash. The apply is atomic and audited.
5. Do not infer fills, tranche state, settlement, cash, or an order. Broker
   display price is never completed-close evidence.

## L. v2.4 Pre-Open Delta Refresh

1. Verify the upcoming official session and latest post-market baseline.
2. Validate baseline/report/session/hash/commit/policy/strategy compatibility.
3. Refresh only authoritative overnight events, indicative premarket data, and
   optional fresh verified read-only broker facts.
4. Preserve completed-session strategy/opportunity states. Premarket cannot
   confirm daily indicators or hard-risk breach.
5. Apply only approved gap/event/liquidity downgrades; otherwise show context.
6. If unchanged, return `NO_MATERIAL_PREOPEN_CHANGE`.
7. Write PRE_OPEN manifest/runtime and confirm no portfolio/policy mutation.

Use Codex Scheduled Tasks only. Configuration starts as `FIRST_RUN_PENDING` and
does not become `DELIVERY_VERIFIED` until the first valid output passes hash,
schema, commit, and policy checks.
