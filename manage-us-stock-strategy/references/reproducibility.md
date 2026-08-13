# Reproducibility and Provenance

## v2.6 immutable research and cohort provenance

Record the active baseline ID, baseline hash, research-packet hash, current
overlay hash, compiler semantic fingerprint, selective evidence queue hash,
and live/Shadow comparison states. Ordinary baseline content refreshes are
recorded per session but do not reset the cohort. Validator/compiler/schema or
activation-policy semantics do reset it. Session-attempt records are append-only
and hash-chained.

Every high-consequence analysis, shortlist deep analysis, historical evaluation,
and live shadow review must write a validated `run_manifest.json` without
secrets.

## Levels

1. Numeric reproducibility is mandatory for deterministic EMA, ATR, RVOL,
   leverage, risk-boundary, and position arithmetic.
2. Evidence reproducibility is mandatory for A/B and regression comparison;
   reuse the same immutable evidence bundle and hashes.
3. LLM decision stability compares authority outcomes, not identical prose.
   Track action class, Risk Controller result, dominant thesis, invalidation,
   and preferred tactical candidate.

Do not promise perfect LLM determinism. Use an explicit model/configuration
record and bounded debate/risk rounds. If no policy count exists, three repeated
runs may be used only as a labelled validation setting.

Identical inputs that produce materially opposite outcomes such as
`BUY_REVIEW` versus `VETO` or `STOP_REVIEW` create
`DECISION_STABILITY_RISK`. Minor wording differences do not.

Use `scripts/build_run_manifest.py`, validate with
`scripts/validate_run_manifest.py`, and retain code, LLM, input, tool, and result
provenance. Never record API keys.

For v2.4, each post-market run also writes an immutable
`post_market_baseline.json`. A pre-open run validates its session, report hash,
policy/strategy versions, and generation time, then writes its own PRE_OPEN
manifest. Premarket evidence is a separate immutable bundle and is never mixed
into completed-session OHLCV or daily indicator hashes.
