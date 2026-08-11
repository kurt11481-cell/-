# Investment Research Lifecycle

## Purpose

Use this workflow to make investment reasoning repeatable and auditable without
giving an LLM or automation authority to place an order.

## Required cycle

Run these stages in order:

1. **Research**: verify identity, completed-session market data, filings,
   valuation, latest material news, macro transmission, and portfolio exposure.
2. **Counter-case**: steelman the strongest bearish or opportunity-cost case.
   State evidence that would prove the current thesis wrong.
3. **Scenario analysis**: record bull, base, and bear paths across relevant
   growth, range, recession/risk-off, rate-shock, and liquidity regimes. Link
   every factual input to the research packet evidence ledger.
4. **Pre-trade decision**: before any user-executed buy, add, reduction, or
   thesis-based exit, record the action under review, horizon, rationale,
   valuation gate, technical gate, portfolio gate, invalidation conditions,
   and review checkpoints. A technical risk alert may still be emitted when
   qualitative research is unavailable, but it must be labelled as such.
5. **Disclosure**: save the packet, validation result, policy/state/snapshot
   hashes, and decision record as a local audit artifact. Do not publish it to
   an external audience without separate user authorization.
6. **Post-evaluation**: append outcomes at the predefined checkpoints. Classify
   the original decision as `confirmed`, `failed`, `pending`, or `revised`
   using only the conditions written before the result. Record missed risks,
   calibration errors, benchmark-relative outcome, and whether the process or
   thesis failed.
7. **Reflection**: propose a policy change only after repeated, comparable
   evidence. Reflection cannot edit holdings, fills, cash, thresholds, or the
   locked decision record.

## Cadence

- Run the deterministic post-market monitor every completed U.S. session.
- Run a bounded latest-news scan when a new held-position `B` or `D` event is
  created, when a material issuer/sector/macro event occurs, and before every
  new-buy or add review.
- Refresh the full holding/watchlist thesis weekly after the final completed
  U.S. session of the week and monthly with valuation and scenario updates.
- Evaluate a user-confirmed trade or explicit no-trade decision at 5, 20, and
  60 completed sessions, plus any named catalyst date. Do not infer a fill.

Routine `E` monitoring does not justify broad free-form research on every run.
Reuse current evidence until its policy freshness limit expires, while keeping
material new events visible.

## Artifacts and validation

Use one directory per cycle:

```text
research-cycles/<cycle_id>/
  decision_record.json
  decision_validation.json
  decision_card.md
  outcomes.jsonl
  postmortems/
```

For legacy schema-1.1 research packets, keep using
`scripts/validate_research_packet.py`. For v2 cycles, embed the research packet
in the locked decision record and run `scripts/validate_decision_record.py`.
Append observed outcomes and run `scripts/evaluate_outcome.py`; never rewrite
the original record. A valid cycle is still research input; the deterministic
alert evaluator remains the only source of next-session candidates.

The lifecycle record must include:

- latest-news search cutoff and coverage window;
- bull/base/bear scenarios, confirmations, and invalidations;
- strongest counter-thesis and falsification tests;
- pre-trade thesis, action under review, horizon, and objective failure rules;
- local disclosure status and immutable decision fingerprint;
- scheduled outcome checkpoints and later append-only evaluations.

If a material claim lacks a current source, if a scenario has no invalidation,
or if the decision predates its evidence, fail closed at `research_incomplete`.
