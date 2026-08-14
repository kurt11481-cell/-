# v2.1 Production Readiness

## v2.6.8 Finalized Post-Market Automation Addendum — 2026-08-14

**AUTOMATION STATUS: CONFIGURED_FIRST_RUN_PENDING**

The existing `Morning Portfolio Strategy` task is the only intended operational
post-market task. Its operating mode is `SINGLE_FINALIZED_RUN`, scheduled for
Tuesday-Saturday 10:15 Asia/Seoul. The analytical components retain
`POST_MARKET`; delivery and operational Shadow counting require the separately
validated `POST_MARKET_FINALIZED` envelope.

Every critical direct daily record must be the stable, same-session USD
`REGULAR_COMPLETED` Raw close with `bar_finalized=true`. Extended-session values
stay separate and cannot overwrite the close, enter daily indicators, confirm
hard risk, upgrade readiness, create quantity, or place an order. FSLY and MVLL
scope limitations remain intact, and event readiness is reported separately
from provider readiness.

The prior zero-session cohort is preserved as superseded. The new semantic
cohort starts at 0 and receives no replay, manual, preliminary, or configuration
backfill. Configuration is not delivery verification; the first eligible real
scheduled run remains pending.

## v2.6.7 Session-Aware Kiwoom Priority Addendum — 2026-08-14

**MARKET-DATA STATUS: KIWOOM_PRIMARY_GUARDED_SCOPED**

Kiwoom is operationally prioritized for verified broker facts,
broker-observable live quotes, finalized archived Raw regular closes, and
validated Adjusted completed-daily history. yfinance remains a diagnostic
Shadow and explicit ticker-local fallback. Codex Web remains restricted to
unresolved comparable finalized regular-close conflicts.

The scope is intentionally not full. A same-ET-date Kiwoom daily row lacks a
deterministic finalization field and therefore remains `FINALIZATION_PENDING`.
FSLY has only 170 Kiwoom daily rows versus the policy minimum of 252 and uses a
complete yfinance technical fallback. MVLL retains a decision-class-local
`EMA10_RECLAIM_RVOL20` technical boundary conflict. Event incompleteness stays
visible as `EVENT_REVIEW_PENDING` without invalidating market-provider health.

The prior 2026-08-13 numerical differences were not comparable finalized-close
conflicts: all 11 Kiwoom same-day rows were unfinalized. The archived
2026-08-12 regular Raw comparison passed 11/11. The after-hours quote sample
kept every record indicative and without daily-indicator or hard-risk
authority; NBIS and BE quote-field failures remained ticker-local.

This provider change starts a new semantic cohort at 0. It adds no order,
quantity, fill, portfolio mutation, or policy-threshold authority.

## v2.6.3 Massive-Free New-Buy Addendum — 2026-08-13

**SYSTEM STATUS: READY_FOR_SHADOW_USE / FIRST_VALID_SESSION_PENDING**

Research-only discovery and unsized new-buy strategy drafting now continue
without Massive or an independent completed-close provider. Selective Codex Web
acquisition is exact-route, ticker-local, original-page only, and separately
validated. All seeded routes are pending five-session acceptance, so Web price
evidence cannot currently unlock a guarded human-review scope.

The 1/5/10/20/60 model is implemented with no automatic promotion. Stage 1
still requires a genuine delivered scheduled post-market run from committed
main; manual smoke and tests do not count. Pre-open remains governed by its
existing baseline prerequisites. The system remains human-review only and has
no order or quantity authority.

## v2.6 Integrated Shadow Addendum — 2026-08-13

**SYSTEM STATUS: READY_FOR_SHADOW_USE / FIRST_VALID_SESSION_PENDING**

All new holding-baseline, Codex Web, provider-onboarding, compiled-strategy, and
20-session acceptance features are Shadow-only. The live v2.5 read-only result
remains authoritative. Three held-ticker baselines are activated, but NBIS and
MVLL direct/underlying valuation remain explicitly unverified and therefore
cannot silently produce a baseline-driven hold or add.

No completed-close Web route or structured provider is operationally approved.
Consequently independent-price operational coverage is pending and final
decision-review activation remains blocked. Morning task configuration is not
delivery verification; the v2.6 cohort starts at `0/20`. Pre-open remains
`NOT_CONFIGURED`.

## v2.5 Shadow Addendum — 2026-08-13

**SYSTEM STATUS: READY_FOR_SHADOW_USE**

Selective price evidence no longer blocks ordinary primary-validated research.
Decision-changing candidates retain their opportunity/strategy state while
independent evidence is pending, but execution remains blocked and quantity is
null. Direct conflicts remain ticker-local. No live provider was silently
activated.

Broker screenshot support is limited to untrusted ingestion, structured
reconciliation, explicit user confirmation, and atomic audited application.
The automated acceptance used a sanitized fixture; no raw account screenshot
was committed or visually parsed. Live scheduled tasks and live runtime were not
modified. This addendum does not claim delivery verification or automated
trading readiness.

## v2.4 Dual-Phase Addendum — 2026-08-13

**SYSTEM SAFETY: READY_FOR_HUMAN_REVIEW_USE**

Subsystem readiness is intentionally separate:

| Subsystem | Status | Reason |
|---|---|---|
| Holding Hard-Risk Monitor | READY_FOR_HUMAN_REVIEW_USE | Raw completed-close warning and policy provenance remain visible; no unsupported action mapping |
| Holding Strategy Engine | READY_FOR_HUMAN_REVIEW_USE | Risk/Strategy states separated and all strategy-state fixtures pass |
| Tactical New-Buy Radar | DATA_PROVIDER_BLOCKED | No approved live independent completed-close provider is configured |
| Capital Redeployment | READY_FOR_HUMAN_REVIEW_USE | Strict cash and zero-funding semantics pass; no quantity authority |
| Post-Market Orchestrator | READY_FOR_SHADOW_USE | Fail-closed shadow passed; live Radar component is provider blocked |
| Pre-Open Refresh | TESTED_ONLY | Deterministic/CLI fixtures pass; real scheduled delivery not yet verified |
| Post-Market Automation | CONFIGURED_FIRST_RUN_PENDING | Delivery must be proven by a valid scheduled artifact |
| Pre-Open Automation | NOT_CONFIGURED | Timezone-anchored Codex task card requires user confirmation; no OS workaround used |
| Installed Skill Deployment | READY_FOR_HUMAN_REVIEW_USE | 123 canonical files match the installed Skill; all six policy-gated normalized hashes validate |

This is not automated-trading readiness. External provider unavailability is
disclosed and does not justify stale fallback or reduced evidence standards.

## v2.2 Tactical Radar Addendum — 2026-08-12

**READINESS: READY_FOR_HUMAN_REVIEW_USE**

The v2.2 tactical radar preserves the v2.1 authority boundary and passed 92
workspace tests plus two forward-test reviews after remediation. Its current
shadow outcome is `DATA_INCOMPLETE`, because the independent completed-close
cross-check was unavailable; this is accepted fail-closed safety behavior.
Opportunity and execution states remain separate, preferred-candidate output
requires validated deep research, and no order/quantity authority was added.

Native creation of a second task heartbeat was not available because this task
already has an active 07:30 automation. The existing automation was preserved;
the separate 07:45 radar heartbeat requires the documented manual setup in a
separate Codex task. This operational limitation does not weaken the code merge
gate and does not authorize an OS scheduler workaround.

## Conclusion First

**READINESS: READY_FOR_HUMAN_REVIEW_USE**

V2.1 is eligible for a conditional main merge after the feature commit and
post-merge smoke suite pass. It is a research and trade-review decision-support
system with human approval. It is not an automated brokerage system.

## Readiness Assessment

| Area | Status | Evidence |
|---|---|---|
| Architecture | PASS | Role authority and ordered deterministic gates remain intact. |
| Evidence integrity | PASS | Unsupported, stale, conflicting, or future-known evidence fails closed. |
| Data-provider resilience | PASS | Bounded retry, workspace cache, circuit state, and no stale silent fallback are tested. |
| Point-in-time integrity | PASS | Current social and future publications are rejected from historical runs. |
| Event risk | PARTIAL | CPI/PPI/PCE are surfaced; missing corporate/options/index coverage remains explicit and context-only. |
| Technical validation | PASS | Official session, 16 independent closes, 15 technical rows, and leveraged proxies passed. |
| Options safety | PASS | Options remain secondary research with no order authority. |
| Portfolio safety | PASS | No portfolio or runtime state was mutated; no cash, fill, or quantity was inferred. |
| Alert separation | PASS | Research cannot enter or upgrade the deterministic alert engine. |
| Reproducibility | PASS WITH LIMITS | Numeric/evidence hashes and manifests pass; exact LLM prose is not promised. |
| Decision stability | PASS | Three immutable NBIS public-data runs produced identical material authority outcomes. |
| Evaluation harness | PASS WITH LIMITS | Safety and decision quality pass; costs and benchmark mapping remain `ASSUMPTION_REQUIRED`. |
| Tactical engine | PASS | Exact universe and watchlist/new-buy separation are enforced. |
| Current shadow | PASS / WAIT | Data-complete session 2026-08-10; shortlist MVLL/SOXL/NBIS; no trade forced. |
| Git integrity | PASS BEFORE MERGE | Feature work is isolated from main and no remote is configured. |

## Current Shadow Result

The collector excluded the in-progress 2026-08-11 daily bar, verified the
2026-08-10 NYSE session, and cross-checked every required close against Nasdaq.
The tactical screen shortlisted MVLL, SOXL, and NBIS. NBIS was used for the
privacy-safe repeated LLM test. All three runs returned `WAIT`,
`ALLOW_REVIEW`, the same dominant thesis, and the same invalidation set.

Private holdings, cash, cost basis, fills, and runtime state were not sent to
the model. Decision records validated as `WATCH_ONLY`, which correctly exposes
the missing new-buy authority.

## Known Limitations

- Event coverage is incomplete for corporate earnings, options expiration, and
  index events; missing coverage is never reported as no event.
- yfinance remains an unofficial collector and Nasdaq/NYSE availability remains
  an external dependency.
- LLM behavior remains probabilistic despite the passing three-run sample.
- Transaction costs, slippage, and benchmark mappings require explicit approval
  before economic backtest claims can be activated.
- True v1/v2 point-in-time A/B remains unavailable.

There is no `READY_FOR_AUTOMATED_TRADING` state.
