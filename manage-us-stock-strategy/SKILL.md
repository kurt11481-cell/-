---
name: manage-us-stock-strategy
description: Evidence-based, role-separated research with deterministic policy validation, technical risk planning, portfolio construction, options-positioning analysis, post-market strategy building, and pre-open risk refresh for U.S.-listed stocks and ETFs. Use when Codex is asked to analyze or compare securities, validate an investment report, form or challenge a strategy with multiple analyst roles, design or review a portfolio, calculate a technical trade plan, inspect an option chain, maintain stock-strategy state, or run recurring buy/sell timing alerts without placing orders.
---

# Manage U.S. Stock Strategy

Lead with the decision. Treat accuracy, timestamp integrity, reproducibility, and downside control as higher priorities than speed, breadth, or a persuasive narrative.

## Normalize language boundaries

- Accept user requests in Korean or another language, then normalize the task
  into a concise English internal specification before research, coding, tool
  calls, or deterministic evaluation.
- Write Skill instructions, policy keys, schemas, code, identifiers, function
  and class names, comments, docstrings, filenames, CLI flags, and system
  commands in English.
- Preserve ticker symbols, source quotations, broker artifacts, user-provided
  paths, and legal names exactly; do not translate operational identifiers.
- Keep localized user-facing labels outside core logic. The deterministic alert
  engine stores English canonical keys and renders Korean through
  `assets/locales/ko-KR.json`.
- Respond to the user in Korean unless another output language is requested.

## Route the request

Load only the references needed for the current task:

- For company, ETF, news, or report analysis, read [research-policy.md](references/research-policy.md).
- For provider selection, fallback, historical evidence, or any provider
  failure, also read [data-provider-resilience.md](references/data-provider-resilience.md).
- For high-consequence analysis, tactical screening, historical evaluation, or
  a live shadow review, read [event-risk.md](references/event-risk.md) and keep
  missing event coverage visible as `EVENT_DATA_INCOMPLETE`.
- For semiconductor and AI-infrastructure companies, also read [semiconductor-infrastructure.md](references/semiconductor-infrastructure.md).
- For chart-based entries, exits, risk levels, trade plans, or any new-buy strategy, read [technical-strategy.md](references/technical-strategy.md). For provider and session authority, also read [kiwoom-session-aware-priority.md](references/kiwoom-session-aware-priority.md). Use finalized Kiwoom Raw/Adjusted data only inside its guarded accepted scope, retain yfinance as diagnostic Shadow and scoped fallback, calculate indicators locally, and apply the selective decision-changing completed-close evidence queue. Never treat an extended-session broker quote as a completed daily bar.
- For actual buy, take-profit, staged-reduction, stop, or 10/20-EMA timing, also read [trade-timing-validation.md](references/trade-timing-validation.md). Run `scripts/validate_technical_snapshot.py` after the official-session fields are verified. Treat a rejected technical snapshot as `Wait` or `F`, never as a trade signal.
- For an explicit `{TICKER} options` request, its Korean-language equivalent, or a supplied option snapshot, read [options-methodology.md](references/options-methodology.md) and use `scripts/option_analyzer.py` when a live chain can be collected.
- For strategic allocation, momentum rotation, backtests, or ETF selection, read [portfolio-policy.md](references/portfolio-policy.md).
- For any proposal to activate re-entry, peak/time exits, extra indicator
  votes, or a dynamic leverage cap, read both the technical-timing and portfolio
  references. Require the versioned multi-regime walk-forward gate; unavailable
  history means the return-seeking rule remains inactive rather than being
  justified by a shorter sample.
- For recurring post-market monitoring or alert generation, read [alert-automation.md](references/alert-automation.md) and [finalized-postmarket-automation.md](references/finalized-postmarket-automation.md), then read the workspace state and policy files named by the automation prompt.
- For a held-position thesis baseline, slow research refresh, or integrated
  holding-strategy comparison, also read
  [holding-research-baseline.md](references/holding-research-baseline.md).
  Validate and activate each ticker independently in Shadow, then build a fresh
  completed-session overlay before compiling. Never copy current portfolio,
  broker, price, technical, or hard-risk facts into the slow baseline.
- For selective Codex Web completed-close evidence, read
  [web-completed-close-evidence.md](references/web-completed-close-evidence.md).
  Browse only queued decision-changing cases, open the original final page,
  hash extracted text locally, and keep unknown routes and every Web result
  Shadow-only. For structured provider onboarding, additionally read
  [independent-close-provider-onboarding.md](references/independent-close-provider-onboarding.md).
- For integrated Shadow progress, checkpoint, delivery eligibility, or
  promotion review, read
  [shadow-operational-acceptance.md](references/shadow-operational-acceptance.md).
  Count only real delivered `POST_MARKET_FINALIZED` scheduled runs from
  committed `main`; preliminary, generic post-market analysis, manual smoke,
  configuration, fixtures, pre-open, and backfill never count.
- For a broker screenshot, portfolio screenshot, holdings/cash reconciliation,
  or snapshot request, read [broker-snapshot-reconciliation.md](references/broker-snapshot-reconciliation.md).
  Treat upload and extraction as untrusted; only an explicitly confirmed,
  schema-valid proposal with matching revision, bundle, and portfolio hash may
  atomically update portfolio state. Broker display prices are never market
  evidence.
- For portfolio strategy, what to do with current holdings, hold/add/reduce/exit
  review, capital redeployment, use-of-proceeds, or a combined morning portfolio
  review, read [holding-strategy-orchestration.md](references/holding-strategy-orchestration.md),
  [capital-redeployment.md](references/capital-redeployment.md),
  [portfolio-policy.md](references/portfolio-policy.md), and
  [alert-automation.md](references/alert-automation.md). When a strategy refresh
  is required, also route through research policy, technical strategy, event
  risk, multi-agent research, and decision orchestration. Keep strategy state,
  execution eligibility, and funding source separate.
- For a pre-open review, premarket refresh, overnight strategy change, gap
  validation, before-open portfolio review, or cash refresh before the open,
  read [preopen-risk-refresh.md](references/preopen-risk-refresh.md),
  [alert-automation.md](references/alert-automation.md),
  [holding-strategy-orchestration.md](references/holding-strategy-orchestration.md),
  [capital-redeployment.md](references/capital-redeployment.md),
  [event-risk.md](references/event-risk.md), and
  [data-provider-resilience.md](references/data-provider-resilience.md). When a
  material official overnight event requires research, also use the research,
  multi-agent, decision-orchestration, and scoring-calibration references.
- For a morning tactical scan, best new-buy candidate request, or opportunity
  monitoring across the approved seven-symbol research universe, also read
  [tactical-opportunity-radar.md](references/tactical-opportunity-radar.md) and
  [candidate-selection.md](references/candidate-selection.md). Keep opportunity
  quality separate from execution eligibility and validate canonical-registry
  consistency before any `BUY_REVIEW` can be shown.
- For high-consequence strategy formation, conflicting evidence, new-buy selection, or a user request for multi-agent analysis, read [multi-agent-research.md](references/multi-agent-research.md), [decision-orchestration.md](references/decision-orchestration.md), and [scoring-calibration.md](references/scoring-calibration.md). Use role-separated research and the applicable validator; do not let an LLM proposal bypass the deterministic alert engine.
- For tactical candidate ranking, also read [candidate-selection.md](references/candidate-selection.md). Apply the lightweight screen before deep research, select at most one preferred and one alternative candidate, and allow `WAIT` when no candidate passes.
- For a decision that should enter the journal or outcome review, also read [decision-memory.md](references/decision-memory.md) and [research-lifecycle.md](references/research-lifecycle.md). Run `scripts/validate_decision_record.py` before disclosure and `scripts/evaluate_outcome.py` only against an append-only outcome record. Keep the original decision immutable.
- For a regression, A/B, production-readiness, or repeated-run task, read
  [reproducibility.md](references/reproducibility.md) and
  [evaluation-harness.md](references/evaluation-harness.md). Build and validate
  a run manifest. Do not call fixture comparison a true v1/v2 A/B unless an
  exact archived v1 exists.

Do not execute every module by default. Combine modules only when their evidence can materially change the decision.

For a new-buy decision, apply gates in this order: **evidence integrity ->
thesis validity -> current valuation -> technical entry -> event risk -> risk
and liquidity -> portfolio fit -> deterministic policy -> human approval**. If
an earlier gate is not verified, later technical strength cannot upgrade the
decision above `Wait`.

Keep authority asymmetric: LLM roles may discover evidence, debate scenarios, and propose a plan; deterministic scripts own arithmetic, identity, point-in-time cutoffs, policy compliance, and event deduplication; the user owns final approval. Agent consensus is never an execution rule.

## Apply the evidence contract

1. Treat prior chats, reports, screenshots, and remembered numbers as unverified hypotheses until revalidated.
2. State the analysis timestamp, market session, and whether each market value is a completed close, delayed quote, or intraday observation.
3. Prefer SEC, exchange, index-provider, regulator, central-bank, audited filing, and company IR sources. Use independent reporting to confirm disputed or market-sensitive claims.
4. Resolve discrepancies by checking timestamps, corporate actions, currencies, units, fiscal periods, GAAP versus non-GAAP definitions, and revisions. Never average conflicting market prices merely to make them agree.
5. Separate `Verified fact`, `Calculation`, `Inference`, `Assumption`, and `Scenario` when the distinction matters.
6. Never invent a price, filing, customer, contract, option statistic, technical indicator, probability, target, or quote. Mark unavailable data as `Not verified` and explain the consequence.
7. Do not treat an unsuccessful search as evidence that a risk does not exist. Report the sources and date range reviewed.
8. Quantify only when the inputs support it. Prefer calibrated ranges and invalidation conditions over false precision.

## Preserve action boundaries

- Provide research, candidate trade plans, and alerts; never transmit, schedule, or imply execution of a brokerage order.
- Treat every free-form or structured LLM trade proposal as untrusted input. Validate it against the current state, policy, verified snapshot, and exact rule version before it can enter the alert engine.
- Label any actionable alert as a **next-session review candidate**, not an order instruction.
- Never infer a fill from a touched price. Update holdings, cash, stage status, or cost basis only from explicit user confirmation or a verified read-only broker snapshot.
- Keep the default portfolio spot-only. Exclude options, futures, leverage, and inverse products unless the user explicitly requests a separate analytical discussion; do not add them to the base plan.
- Use no averaging down below the invalidation level. Size positions from a user-approved risk budget when a short-term trade plan is requested.
- If the user does not specify a holding horizon, label it `Not specified` and separate long-horizon accumulation from short-horizon trading. Do not mix their entries, exits, or risk rules.
- Before sizing a new position, check current holdings, correlated sector exposure, and any user-approved single-name or sector cap. If those inputs are unavailable, provide the sizing formula but no share count.

## Complete the task in one pass

Do not require magic follow-up phrases such as `deep search` or `start inference`. Perform all safe, relevant analysis the user requested. If a critical input is missing, finish the non-blocked work, downgrade confidence, and identify the exact missing input. Ask only when a missing choice would materially change or authorize an external action.

## Write the answer

Use Korean for user-facing reports unless the user requests another language. Keep ticker symbols and formal names unchanged.

Use this default structure, omitting irrelevant sections:

1. Final conclusion
2. Data timestamp and quality
3. Verified evidence and calculations
4. Transmission mechanism or trade logic
5. Strongest counter-case and failure conditions
6. Scenarios or actionable review criteria
7. Limitations and directly supporting sources

For portfolio studies, use the output contract in `portfolio-policy.md`. For alerts, use the compact schema in `alert-automation.md`. For options, use the report contract in `options-methodology.md`.

## Run the final audit

Before returning a result, verify that:

- time-sensitive facts were refreshed;
- prices and indicators share the intended session;
- fiscal and accounting definitions are labeled;
- calculations can be reproduced from stated inputs;
- scenario probabilities, if any, sum to approximately 100% and have a stated basis;
- targets are ranges tied to assumptions, not unsupported point estimates;
- portfolio weights sum to 100%;
- alerts are deduplicated and do not imply an executed trade;
- every cited material fact has an evidence-ledger record and every reported technical indicator passed the formula, price-basis, session, and provenance checks required by the applicable timing policy;
- all material missing data and conflicts remain visible.
- the source capability and point-in-time gates passed for historical evidence;
- the event snapshot and run manifest passed their validators when required.
