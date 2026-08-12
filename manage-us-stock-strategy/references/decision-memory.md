# Decision Memory and Outcome Reflection

## Memory contract

Persist a decision only after its evidence and authority boundaries are
validated. A record must contain:

- immutable decision ID, schema version, creation time, and evidence cutoff;
- symbol, instrument registry version, portfolio state revision, and policy
  version;
- evidence records and role outputs;
- Research Manager status;
- Trader proposal;
- independent Risk Controller verdict;
- Portfolio Manager selection;
- deterministic gate result;
- final review action and human decision status;
- confirmation and invalidation condition IDs;
- canonical hashes of referenced artifacts.

Lock the decision fingerprint before an explicit user action or no-trade
decision. Never rewrite the thesis, conditions, cutoff, or action after an
outcome is known.

## Append-only outcomes

Store later observations separately. Each outcome must reference the original
decision fingerprint and include observation time, completed session, source
IDs, triggered condition IDs, security and benchmark returns when available,
cost and slippage assumptions, and unresolved data.

Classify deterministically:

- `FAILED` when a predefined invalidation condition is observed;
- `CONFIRMED` when a predefined confirmation is observed and no invalidation is
  observed;
- `REVISED` when both are observed or the security identity/corporate action
  makes the original comparison invalid;
- `PENDING` when neither condition is resolved.

Do not judge a `WAIT` decision solely by the security's later return. Evaluate
whether the stated missing gate resolved and whether the process avoided an
unapproved risk.

## Reflection boundary

Reflection may identify missed evidence, overconfidence, bad assumptions,
avoidable data failures, or a poorly specified invalidation. It may propose a
new version of a reference or policy. It may never mutate:

- portfolio holdings, cash, fills, or cost basis;
- locked decision records;
- approved price bands, loss limits, quantities, leverage permissions, or
  short authority;
- alert runtime state;
- a historical calibration result.

The tactical radar runtime is not brokerage memory. It may retain only the
candidate session, opportunity state, execution state, primary blocker,
remaining conditions, last deep-research session, signal fingerprint, and
delivery metadata. Keep stable transition `event_key` and session-specific
`delivery_id` values. Never copy a radar state change into holdings, cash,
cost basis, fills, or policy.

Use `scripts/validate_decision_record.py` before disclosure and
`scripts/evaluate_outcome.py` for a separate outcome artifact.
