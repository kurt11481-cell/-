# Tactical Candidate Selection

## Scope

Use this workflow to rank user-approved research candidates without converting
watchlist inclusion into permission to buy. Keep tactical selection separate
from strategic allocation, recurring alerts, and brokerage state.

## Two-stage process

### Stage 1: deterministic or light screen

Screen the registered tactical universe with point-in-time inputs only:

- exact identity and registry status;
- watchlist approval;
- data availability and completed-session integrity;
- minimum liquidity and tradability evidence;
- corporate-action, gap, and halt flags;
- high-level thesis relevance;
- current valuation availability;
- technical regime availability;
- verified leverage factor when leverage arithmetic is needed;
- portfolio overlap and concentration inputs.

Missing held-symbol evidence is not a screening failure; it is a portfolio data
failure under the active policy. Missing watch-only evidence removes only that
candidate from the current shortlist.

### Stage 2: bounded deep research

Run full role-separated research on only the top three to five screen survivors.
Do not run the full analyst graph for every universe member. Preserve the screen
cutoff and rejected reasons so the shortlist can be reproduced.

## Candidate lanes

Keep independent lanes:

- `leveraged_semiconductor`: MVLL and SOXL, evaluated with verified daily-reset
  leverage and their approved non-leveraged confirmation proxies;
- `ai_infrastructure`: NBIS;
- `ai_agent_theme`: user-defined organizational candidates. Theme tags describe
  research organization only and are not claims about revenue purity.

Do not compare a leveraged ETF and an ordinary stock as if they shared the same
risk, valuation, or holding-period assumptions. Compare within a lane first,
then perform portfolio-fit review across lanes.

## Ordered gates

Apply these ordinal gates:

1. `evidence`: `PASS`, `CONDITIONAL`, or `FAIL`;
2. `thesis`: `STRONG`, `CONTESTED`, `WEAK`, or `UNVERIFIED`;
3. `valuation`: `ATTRACTIVE`, `FAIR`, `STRETCHED`, or `UNVERIFIED`;
4. `technical`: `READY`, `WATCH`, `INVALID`, or `UNAVAILABLE`;
5. `risk_liquidity`: `ACCEPTABLE`, `CONSTRAINED`, or `VETO`;
6. `portfolio_fit`: `FITS`, `CONSTRAINED`, or `BLOCKED`.

Never average these labels into a master score. A later strong gate cannot
offset an earlier failure. Use [scoring-calibration.md](scoring-calibration.md)
for comparison and calibration.

## Selection output

Return at most one preferred candidate and one alternative. Both remain review
candidates and must state:

- lane and exact ticker;
- watchlist and new-buy approval status separately;
- passed, conditional, and failed gates;
- evidence cutoff;
- strongest counter-case;
- valuation and technical conditions still required;
- objective invalidation;
- why `WAIT` remains valid.

When no candidate clears every required gate, return only `WAIT`. Do not force
turnover or a bullish selection.

For securities not verified as held, never emit a sell-side review. Without
explicit short approval, never emit a short thesis as an action.

## Registry and policy

Read the workspace tactical-universe and instrument-registry files explicitly.
Do not infer leverage from a ticker. A null or unverified factor is unavailable
for effective-leverage arithmetic. Preserve existing approved values and fail
closed when registry entries conflict with the active deterministic policy.
