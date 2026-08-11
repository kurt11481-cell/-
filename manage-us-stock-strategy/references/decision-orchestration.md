# Decision Orchestration

## Purpose and authority

Use this workflow for a portfolio-changing research review, tactical candidate
selection, or a material thesis reassessment. It adds structured roles without
changing the authority of the existing evidence, technical, portfolio, options,
or alert policies.

Apply authority in this order:

1. evidence integrity and point-in-time identity;
2. business thesis and falsification tests;
3. current valuation;
4. technical entry or exit timing;
5. portfolio fit, sizing inputs, and verified instrument leverage;
6. deterministic policy validation;
7. explicit human approval.

An earlier failed gate cannot be repaired by a later role. Agent agreement is
not a policy exception. No role may create cash, holdings, fills, quantities,
price bands, leverage approvals, short authority, or a brokerage instruction.

## Canonical decision chain

Run only decision-relevant analysts, then preserve the following hand-offs:

1. **Identity and data gate** verifies the exact security, instrument type,
   leverage factor, proxy, corporate action state, evidence cutoff, and completed
   market session.
2. **Fundamental analyst** evaluates business quality, commercialization stage,
   cash conversion, financing, dilution, and valuation inputs.
3. **Technical analyst** interprets a separately validated technical snapshot.
   It does not recompute or repair rejected indicators in prose.
4. **News and macro analyst** records event time, publication time, transmission
   path, lag, and look-ahead exclusion.
5. **Sentiment analyst** is optional and may add only low-authority positioning
   context.
6. **Bull and Bear Researchers** steelman opposite cases from the same evidence
   ledger and identify disconfirming observations.
7. **Research Manager** resolves claim conflicts, lists unresolved issues, and
   returns `RESEARCH_COMPLETE`, `RESEARCH_CONDITIONAL`, or `RESEARCH_REJECTED`.
8. **Trader** maps the research state to one canonical review action. It cannot
   select a quantity or bypass the technical and portfolio gates.
9. **Independent Risk Controller** returns only `ALLOW_REVIEW`, `DOWNGRADE`, or
   `VETO`. It may preserve or reduce action intensity; it may never upgrade it.
10. **Portfolio Manager** selects at most one preferred candidate, one
    alternative, or `WAIT`, while keeping strategic and tactical lanes separate.
11. **Deterministic gate** validates identity, source cutoff, holdings, cash,
    action eligibility, registry permissions, policy version, technical status,
    concentration inputs, and no-order boundaries.
12. **Human reviewer** accepts, rejects, or revises the review candidate. A human
    decision is not a fill; fills require separate explicit confirmation.
13. **Decision memory and outcome reflection** lock the original decision and
    append later observations without mutating policy or portfolio state.

## Canonical Trader actions

Use only:

- `WAIT`
- `CONDITIONAL_BUY`
- `BUY_REVIEW`
- `HOLD`
- `TAKE_PROFIT_REVIEW`
- `REDUCTION_REVIEW`
- `STOP_REVIEW`

For a security not verified as held, the maximum allowed actions are `WAIT`,
`CONDITIONAL_BUY`, or `BUY_REVIEW`. For a verified holding, sell-side review
actions are allowed only when the applicable deterministic policy permits them.
Without explicit short approval, no short action exists.

Every action is a review label, not an order. `BUY_REVIEW` does not authorize a
purchase and `STOP_REVIEW` does not imply a stop order or fill.

## Risk downgrade order

Risk Controller may move an action only toward lower intensity:

```text
BUY_REVIEW -> CONDITIONAL_BUY -> WAIT
TAKE_PROFIT_REVIEW -> HOLD -> WAIT
REDUCTION_REVIEW -> HOLD -> WAIT
STOP_REVIEW -> REDUCTION_REVIEW -> HOLD -> WAIT
```

`VETO` forces `WAIT`. `ALLOW_REVIEW` does not upgrade an input action. A risk
review with missing held-risk, gap, halt, liquidity, or leverage evidence must
return `DOWNGRADE` or `VETO` according to the active deterministic policy.

## Research Manager contract

Require:

- evidence cutoff and session;
- accepted and rejected claim IDs;
- Bull/Bear disagreement matrix;
- unresolved data, valuation, and thesis conditions;
- explicit strongest counter-thesis;
- objective invalidation conditions;
- status and reason.

The manager may request another bounded evidence pass only when it names the
missing claim or contradiction. Stop debate when a round adds no new claim ID,
contradiction, or decision-changing condition.

## Portfolio Manager contract

Keep strategic allocation and tactical candidates in separate fields. Tactical
universe inclusion never changes a strategic target. Return at most:

- one preferred tactical review candidate;
- one alternative candidate; and
- `WAIT` when no candidate clears every earlier gate.

Do not force a selection. Do not transform an ordinal assessment into a false
master score. Use the lane and gate rules in
[candidate-selection.md](candidate-selection.md).

## Deterministic transition rules

- Identity or point-in-time failure: `WAIT` and rejected record.
- Research Manager `RESEARCH_REJECTED`: `WAIT`.
- Unverified valuation for a new buy: maximum `CONDITIONAL_BUY` if policy allows
  research watch; otherwise `WAIT`.
- Rejected technical snapshot: maximum `WAIT` for timing.
- Missing verified cash, risk budget, quantity authority, or new-buy approval:
  maximum `CONDITIONAL_BUY` with quantity `null`.
- Risk `VETO`: `WAIT`.
- Portfolio Manager selection without deterministic eligibility: `WAIT`.
- Deterministic `WATCH_ONLY`: retain the review label only as non-actionable
  research context with quantity `null`.
- Deterministic `REJECTED`: `WAIT`.

The alert engine remains a separate deterministic runtime. A v2 record cannot
be inserted, copied, or transformed into its candidate list.
