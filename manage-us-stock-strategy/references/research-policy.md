# Research and Evidence Policy

## Decision standard

Start with the answer that best fits the verified evidence. Do not force a bullish, bearish, or tradeable conclusion. Use `High`, `Medium`, or `Low` conviction only after stating why.

## Establish the clock

- Record the current KST timestamp and the relevant exchange timezone.
- For prices, identify the last completed regular session. Label intraday, pre-market, after-hours, delayed, and completed-close data separately.
- For options, require an exact snapshot timestamp and the matching underlying-price timestamp.
- For filings, use the latest filed 10-K, 10-Q, 8-K, proxy, registration statement, or Form 4 relevant to the claim.
- For 13F data, state the reporting period and filing lag. Never call it current institutional flow.
- For macro series, use the latest official observation and its release date rather than imposing a universal age limit.

## Use an evidence hierarchy

1. SEC, exchanges, index providers, regulators, central banks, and official statistics
2. Audited reports, company IR releases, and official call transcripts
3. Independent reporting such as Reuters for confirmation and context
4. Reputable market-data services with an identified timestamp
5. Social media, videos, screenshots, and unsourced summaries only as hypotheses or sentiment evidence

Do not require a redundant secondary link for every routine fact. Require primary evidence plus independent confirmation for disputed, surprising, or market-moving claims when practical.

## Resolve conflicts instead of averaging them

When values disagree, inspect:

- quote timestamp and session;
- split, spin-off, dividend, or other corporate action;
- currency and unit;
- fiscal year and revision;
- GAAP versus non-GAAP definition;
- basic versus diluted share count;
- total return versus price return;
- stale cache or delayed feed.

Choose the authoritative value and explain the discrepancy. Never average conflicting prices.

## Gate every actionable technical claim

Before a technical level can support `Buy`, `Take profit`, `Reduce`, or `Stop`:

1. Build the completed-session snapshot with `scripts/build_market_snapshot.py`.
2. Verify the expected U.S. regular-session date against an exchange or other primary calendar source and record the source, source type, and verification timestamp.
3. Run `scripts/validate_technical_snapshot.py` without bypass flags. A rejected result forces `Wait` or `F`; do not quote the rejected indicator as actionable.
4. Independently cross-check the decision price against a timestamped exchange, broker, or reputable second quote source. The internal validator checks consistency and provenance, not the external truth of Yahoo data.
5. Record every cited technical value with ticker, value, units, price basis, bar date, formula version, source, retrieval timestamp, and validator fingerprint.
6. Run `scripts/validate_research_packet.py` for any portfolio-changing conclusion so cited factual claims resolve to the evidence ledger and pass date/source-tier checks.

If the primary and secondary quote disagree beyond ordinary rounding, stop and resolve the session, adjustment, currency, or corporate-action discrepancy. Never silently substitute a number or cite an indicator computed from a different session than the decision price.

## Analyze a security

Use only relevant items from this sequence:

1. Business model and economic profit pool
2. Growth driver and evidence stage
3. Competitive advantage and substitution risk
4. Customer and supplier concentration
5. Revenue quality, margin structure, cash conversion, and working capital
6. Balance sheet, debt maturity, stock compensation, and dilution
7. Capital allocation and financing dependence
8. Regulatory, legal, geopolitical, and supply-chain exposure
9. Valuation and expectations embedded in price
10. Strongest counter-thesis and objective invalidation conditions

Searching and finding nothing is not a clean bill of health. Say which sources and periods were reviewed.

## Review dilution and forensic risk

Inspect, when relevant:

- ATM, shelf, registered direct offering, PIPE, and resale registration;
- convertible, exchangeable, preferred, and warrant terms;
- lockups, earn-outs, secondary sales, and equity compensation;
- related-party transactions and off-balance-sheet commitments;
- revenue recognition, receivables, inventory, goodwill, and cash-flow divergence;
- auditor or CFO changes, material weaknesses, subpoenas, litigation, and government investigations.

Report the observed fact, its possible implication, a reasonable alternative explanation, and the remaining unknown. Do not infer fraud from a keyword or infer safety from silence.

## Value the security

- Treat current valuation as a required gate before issuing a new-buy recommendation. If reliable valuation inputs are unavailable or the business is not meaningfully valueable with the selected method, return `Wait` or a conditional watchlist decision and explain why.
- Label GAAP/non-GAAP and TTM/NTM/fiscal-year inputs.
- Use normalized earnings or cash flow when a cycle or acquisition distorts the current period.
- Treat PEG as a secondary heuristic, not intrinsic value.
- Use DCF only when cash-flow visibility supports it. Use sector-appropriate alternatives for banks, REITs, pre-profit biotechnology, and deeply cyclical businesses.
- Use reverse DCF only when the implied-growth calculation is actually performed.
- Present a valuation range with key sensitivities. Do not issue a precise target from a single multiple.

## Validate a report, article, or video

For each material claim, classify it as:

- Verified
- Broadly reasonable
- Overstated or missing conditions
- Not verifiable from available evidence
- Contradicted by stronger evidence

Separate immediate liquidity or positioning effects from medium-term earnings effects. Identify the transmission path, lag, beneficiaries, losers, and variables that would falsify the argument.

## Construct scenarios

For bull, base, and bear cases, state:

- operating assumptions;
- valuation assumption;
- catalyst and likely timing;
- observable confirmation;
- invalidation condition;
- price range only when reproducible inputs exist.

Use probabilities only when a documented model or explicit estimation basis exists. Otherwise rank scenarios without artificial precision.
