# Portfolio Reallocation Shadow

## Purpose and authority

`CAPITAL_REALLOCATION_SHADOW` is a deterministic, hypothetical portfolio
review. It evaluates every verified positive holding through `ADD_CASE`,
`HOLD_CASE`, `TRIM_CASE`, and `EXIT_CASE`, then recompiles the complete
portfolio opportunity set. It grants no order, quantity, fill, cash, or
portfolio-mutation authority.

The holding decision priority is:

`Hard Risk -> Exit/Risk Reduction -> Event Completeness -> Hold -> Add/New Buy`.

A non-breached maximum-loss boundary is not sufficient evidence for `HOLD`.
The engine must also evaluate thesis, valuation, technical, event, risk,
concentration, time-stop, and relative-opportunity inputs that are available
under approved policy.

## Event actionability

Maintain separate readiness for `NEW_BUY`, `ADD`, `HOLD`, `TRIM`, and `EXIT`.
New buys and adds fail closed when material event readiness is insufficient.
Partial non-blocking evidence can retain a holding review. Event incompleteness
alone never vetoes a risk-reducing trim. A verified hard-risk or
thesis-invalidating exit can override event incompleteness while retaining the
evidence limitation in the report.

Use the versioned matrix in
`workspace/policies/portfolio_reallocation_shadow_policy.json`. Do not convert
missing evidence into “no event.” Material categories use only `VERIFIED`,
`NOT_YET_ANNOUNCED`, `NO_NEW_DISCLOSURE_FOUND`, `SOURCE_UNAVAILABLE`, or
`REVIEW_REQUIRED`.

## Post-close ordering

The mandatory order is:

`KIWOOM_COMPLETED_BAR_FINALIZED -> POST_CLOSE_EVENT_REFRESH ->
EVENT_CUTOFF_VALIDATION -> EVENT_BUNDLE_HASH -> HOLDING_STRATEGY_COMPILE ->
PORTFOLIO_REALLOCATION_SHADOW`.

Every decision preserves `decision_as_of`, `market_data_cutoff`, `event_cutoff`,
`broker_cutoff`, and the candidate cutoff when applicable. The event cutoff
must not precede the market-data/strategy cutoff. Evidence later than
`decision_as_of` is rejected.

## Profit protection and action taxonomy

The action taxonomy is `HOLD_CORE`, `HOLD_TIGHTEN_STOP`, `ADD_REVIEW`,
`TRIM_PROFIT`, `TRIM_VALUATION`, `TRIM_TECHNICAL`, `TRIM_CONCENTRATION`,
`TRIM_RISK`, `EXIT_THESIS`, `EXIT_HARD_STOP`, and `ROTATE_REVIEW`.

Profit protection is multi-factor. A fixed unrealized-profit percentage cannot
produce an automatic sale. Until a numeric production rule is explicitly
approved, an upstream deterministic policy result is required. A large profit
with an intact trend and healthy volume may remain `HOLD_TIGHTEN_STOP`.

## Hypothetical proceeds and optimizer

For a trim, the hypothetical ratio and quantity remain null unless an approved
policy or explicitly labelled test scenario supplies ratio authority. A full
thesis or hard-stop exit can use a 100% Shadow ratio. All resulting proceeds
are `SHADOW_ONLY` and never become verified or orderable broker cash.

The optimizer compares existing-holding adds, new-buy reviews, and `KEEP_CASH`
only after hard, risk, event, and portfolio-fit gates. It never creates a hard
`SELL A -> BUY B` link and never lets a numeric score override a blocker.
`SELL_RISK_DECISION` and `BUY_RISK_DECISION` remain separate and require the
independent Risk Kernel in any future execution architecture.

## Cohort and dedup

Portfolio-decision semantics use a separate
`PORTFOLIO_DECISION_SEMANTIC_COHORT`. Start a changed semantic cohort at zero,
without backfill, and preserve scheduler/provider operational counters. Use one
`portfolio_reallocation_cycle_id` to suppress repeated interpretation of the
same event. No production cooldown or hysteresis number is active until
explicitly approved.

## Output and invariants

Every holding output includes all four cases, the selected action, rejected
alternatives, reason codes, event actionability, technical and valuation
conditions, and all ten independent state axes. The portfolio output includes
risk before/after, the hypothetical post-sale portfolio, candidate comparison,
`KEEP_CASH`, turnover/cooldown state, and the best Shadow decision.

Always preserve `execution_quantity=null`, `quantity_authority=none`,
`order_authority=false`, and `portfolio_mutation=false`. Open-order visibility
that is unknown remains unknown. This workflow never changes scheduler timing
or operational-maturity counters.

## Swing Action contract readiness (stage one)

The dashboard exposes an additive `swing_action_plan` view with
`stage=CONTRACT_ONLY`. This is a development-source output contract, not
activation of Shadow sizing, a new policy approval, or production deployment.
Historical dashboards without this field retain their existing interpretation.
Existing reference calculations remain in their original fields and are not
copied into the new Shadow quantity fields. Research `quantity` and execution
quantity remain null. No Order Intent compiler is invoked by this projection.

The first sizing pilot is existing NBIS/MVLL/SOXL holdings and Cash. BUY/ADD
appear as separate candidate types, but their sizing is outside the first pilot.
An account horizon of three years is not a per-position holding period. Swing
duration, monitoring availability and trade-risk budget are not inferred.

### Output mapping and invariants

| Output | Existing source / rule |
| --- | --- |
| current_qty, price, price_session | Original dashboard position values, with source status; never refresh historical values in the renderer |
| candidate_direction | Existing plan action; ADD with verified zero holdings displays BUY |
| direction | Candidate or DEFERRED on a conflicting action/target, missing direction evidence, or unverified current evidence; missing NAV/target alone affects quantity, not the supplied direction candidate |
| timing_status | NOT_VERIFIED by default; optional input-aware Manual projection may express VERIFIED_REDUCTION_REVIEW for an existing approved reduce-review event only; a completed candle alone is not a signal |
| quantity_status | POLICY_REQUIRED or NOT_VERIFIED; no active sizing in this stage |
| shadow_target_qty / delta / buy / sell / cash impact | Null in this stage, enforced by the existing dashboard schema |
| target_weight_pct | Null in the new view; original reference weight remains in the original position row |
| source_binding | Supplied evidence-file hash; hashes of normalized consumed plan/policy content, explicitly named content hashes, not original-file hashes |
| Cash | NAV cash and orderable cash remain separate; alignment is NOT_VERIFIED; KEEP_CASH is an alternative, not a selected decision |
| execution_status | DISABLED, regardless of any legacy reference calculation |

HOLD requires the target reference to equal the current holding. EXIT requires
zero target. TRIM requires a strictly smaller positive target; a full reduction
requires EXIT review. BUY/ADD requires an increasing target and does not acquire
product approval from an existing holding. Invalid candidates retain their
original direction for explanation but the current review direction is DEFERRED.
These checks do not rewrite legacy advisory fields or historical artifacts.

The new view does not establish account-identity or policy-approval binding.
Those fields explicitly remain NOT_VERIFIED. Matching numeric inputs or a policy
file's approved-reference label is not sufficient approval provenance.

The Swing rows are a DERIVED VIEW of the canonical dashboard positions. The
same projection supplies compilation and validation; render and persistence
boundaries reject inconsistent rows before output. Reason and invalidation are
shown in the primary table, with longer explanations in supplemental details.
Credential-labelled narrative is redacted as a whole field using the existing
manifest secret-key classification plus account/header labels. Shared schema
diagnostics are replaced by safe error codes at this boundary. This does not
detect every possible unlabelled secret, and no real credential is read.

Standalone validation checks hash syntax only (FORMAT_ONLY); it does not prove
provenance authenticity. During compilation, the existing validator also
compares the binding against the consumed evidence/plan/policy inputs. Plan and
policy hashes are normalized content hashes; the evidence hash is the supplied
file hash, not a hash reconstructed from parsed JSON. Missing provenance inputs
cannot establish authenticity. Existing file-consumption/manifests remain the
file-byte boundary; no new provenance engine or approval state is introduced.

### Policy approval checklist (no new values approved)

| Policy/input | Existing source | Readiness / affected decision |
| --- | --- | --- |
| Position, leverage, cluster and cash limits | portfolio-decision-risk-envelope-v0.2.json | Existing approved-reference label; original approval and account/scope binding still required for new sizing |
| Held loss-review boundaries | alert_policy.json holding_risk_rules | Preserve existing scope; not a trade budget or automatic full-exit instruction |
| Staged TRIM ratio/target | portfolio_reallocation_shadow_policy.json | Ratios remain null; POLICY_REQUIRED |
| Full exit | Existing hard-risk/thesis exit branches | Validated trigger and applicable action authority required |
| Trade-risk budget | Existing new-buy approval gate | POLICY_REQUIRED before BUY/ADD sizing |
| Drawdown and concurrent trade risk | No verified active rule established here | POLICY_REQUIRED when used; do not invent thresholds |
| Re-entry | Inactive research branch in alert_policy.json | Do not activate or borrow draft restoration fractions |
| Cost, minimum size, fractional shares, rounding | Existing floor calculations and trim minimum-one behavior | Applicable approval required; do not silently inherit the minimum-one correction |
| Broker identity, available shares, open items | Bound genuine evidence | Required for account applicability/execution feasibility; does not block unrelated research |
| NAV cash versus orderable cash | Existing distinct cash extraction | Never substitute projected proceeds or assume snapshots are simultaneous |

ATR sizing is optional for the first pilot. Target-based or approved staged
reduction plus portfolio caps is the minimum existing-holding combination.
Future BUY/ADD additionally requires product eligibility, entry timing, valuation,
approved trade-risk budget, verified funding and liquidity. Ordinary stocks and
daily-reset leveraged ETFs share arithmetic, not identical policy assumptions.

### Implementation and acceptance sequence

1. Implement this inert contract and policy checklist; preserve all authority.
2. Establish action-scoped Manual evidence/direction/timing readiness. Preserve
   previous PARTIAL reconciliation and historical gaps; do not auto-update state.
3. Only after the applicable policy approvals and Manual readiness, connect
   existing Shadow calculation helpers. No new engine or persistent state.
4. Validate sizing on synthetic cases and the approved extended Manual loop:
   action/quantity consistency, capital conservation including approved costs,
   distinct cash types, exposure caps, rounding, identical-input reproducibility,
   unavailable inputs, and unauthorized ADD prevention.
5. Direction-only scheduled analysis may be reviewed independently of sizing.
   Scheduled provenance grade, alert grade and operational maturity remain
   distinct; never relabel manual Grade B as scheduled Grade A.
6. Scheduled sizing and BUY/ADD expansion require their own readiness and policy
   gates. Order Intent and execution remain separate later authorizations.

The targeted stage-one tests exercise the actual dashboard compiler and both
renderers with synthetic fixtures. They do not establish Manual-loop stability,
quantity-policy acceptance, economic performance, or production readiness.

### Optional Manual timing projection (Step 2)

`compile_dashboard(..., holding_timing_inputs=...)` may consume the existing
`snapshot`, `state`, and `policy` objects. It re-evaluates the existing alert
producer and exposes only `holding_timing_review / reduce / B` as
`VERIFIED_REDUCTION_REVIEW` for a matching TRIM candidate. This is the existing
reduction-review meaning, not a general timing PASS or a quantity approval.
The supplied policy and anchor/fill state must equal their canonical local
sources. Broker holdings/costs, completed session/close, identity, source
validation, cutoff, freshness and the existing technical/rearm gates still apply.
Watch, missing inputs, no active trigger, NBIS rule absence, replay and Scheduled
inputs do not gain this status. Current account identity and whole-policy approval
binding remain NOT_VERIFIED; rule threshold approval is not whole-plan approval.

Only identifiers and consumed-content hashes are projected into the canonical
position row. Swing is derived from that row. Input-aware validation recomputes
from the consumed inputs and reuses the Manual request/response capture gate;
report flags and updated content hashes cannot replace those captures. The
existing session authority must provide the completed session's actual close:
independent close cross-check timestamps must be on or after it and no later
than the original decision cutoff. Missing session-close authority stays
NOT_VERIFIED. These checks do not authenticate arbitrary source labels or URLs;
the existing technical snapshot producer still owns source observation evidence.
Standalone validation/rendering checks schema and
canonical/derived consistency, not cryptographic authenticity of a coherently
replaced entire report. Hash fields alone remain FORMAT_ONLY. Historical
CONTRACT_ONLY reports without timing records retain their existing meaning.
No quantity from the alert producer is copied, and all Swing quantity/execution
fields remain disabled. This connection does not deploy a Runtime or complete a
live Manual loop.

The Dashboard CLI accepts `--holding-timing-snapshot <existing-json>` with
one or more `--parent-capture <existing-capture>` arguments. State and policy
come from the existing canonical local files; no CLI approval override exists.
Capture-only input is allowed for scoped direction evidence without timing.
These inputs are limited to Manual `INITIAL_COMPILE`; replay, Scheduled and
plan-only/discovery modes reject them before file reads. Missing captures with
a timing snapshot are rejected. The exact consumed capture bytes and snapshot
are hashed into the existing run manifest; raw captures are not copied into
outputs. This CLI connection does not acquire evidence or repair missing
identity, independent-close, rearm/fill or approval provenance.
