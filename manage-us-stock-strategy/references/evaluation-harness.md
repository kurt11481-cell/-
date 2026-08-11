# Evaluation Harness

Evaluation has three independent layers. Never collapse them into one score.

## Layer 1: safety

Check look-ahead contamination, timestamp/session mismatch, hallucinated facts,
unauthorized leverage or quantity, portfolio mutation, inferred fills,
deterministic-gate bypass, and human-approval bypass. A material failure blocks
merge regardless of returns.

## Layer 2: decision quality

Assess evidence accuracy, thesis causality, counter-thesis quality, valuation,
technical and event discipline, risk and portfolio awareness, uncertainty, and
repeated-run stability.

## Layer 3: economic performance

Only point-in-time-valid historical cases may calculate CAGR, volatility,
drawdown, recovery, Sharpe, Sortino, Calmar, downside deviation, worst rolling
returns, turnover, costs, slippage, benchmark-relative return, and capture
ratios. When cost/slippage or benchmark mappings are not approved, report
`ASSUMPTION_REQUIRED`; never hide a zero-cost assumption or choose a benchmark
after observing results.

Cover bull, bear, range, high-volatility, and rate-shock regimes when data allow.
Infrastructure safety changes do not authorize return-seeking timing changes.
Run `scripts/run_evaluation.py` and validate its result against the checked-in
schema.
