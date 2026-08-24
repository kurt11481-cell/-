# Integrated Instrument Identity + Session Authority Implementation Specification

Specification ID: `II-SA-SPEC-1.0`

Repository basis: current workspace observed on `2026-08-22` KST

Implementation status: specification only

Builder authority: not granted

Network acquisition: not performed

Production artifacts or activation: not created

## A. SPECIFICATION VERDICT

```text
INTEGRATED_SPEC_STATUS = PASS
```

승인된 Instrument Identity Architecture, 8-symbol official-evidence verdict, and Session Authority operating-MIC amendment 사이에 해결되지 않은 Architecture contradiction은 없다. 구현 경계는 다음과 같이 고정한다.

```text
Instrument Identity Authority
  -> explicit verified primary_listing_operating_mic
  -> Session Authority V2 operating-MIC scope gate
  -> expected_completed_session
  -> unchanged M1 finalized-bar candidate selector
```

이번 PASS는 구현·materialization·activation의 PASS가 아니다. 현재 사실은 계속 다음과 같다.

```text
VERIFIED_RESEARCH_EVIDENCE != ACTIVATED_AUTHORITY
IDENTITY_ARTIFACT_EXISTS = false
IDENTITY_AUTHORITY_ACTIVE = false
PRODUCTION_CUTOVER_APPROVED = false
```

## B. ARCHITECTURE ALIGNMENT

### B.1 Authority ownership

| Authority | Owns | Does not own |
|---|---|---|
| Instrument Identity Authority | exact security identity, canonical ticker namespace, ticker, instrument type, security class, primary listing venue, segment MIC, operating MIC, effective interval, authority cutoff, evidence provenance | sessions, prices, holdings, cash, quantities, orders, strategy, execution |
| Session Authority | operating-MIC scope, official common calendar, ET session phase, `expected_completed_session` | ticker identity, segment-to-operating conversion, prices, execution |
| Broker Evidence | broker-observable read-only facts within its validated field semantics | primary MIC, official calendar, price finality by assertion, identity activation |
| Price Authority | a validated price/bar within its approved basis and session | security identity, session-calendar activation, execution |
| Execution Authority | none in this Specification | every analytical or research result |

No combined `VerifiedMarketContext` or other authority-collapsing object is permitted.

### B.2 MIC semantics

```text
primary_listing_segment_mic   = listing segment/audit metadata
primary_listing_operating_mic = primary listing operating MIC
Session Authority input       = primary_listing_operating_mic only
```

`ARCX`, `BATS`, `XNGS`, and `XNMS` are never Session Authority inputs. They remain identity/audit metadata. No component may derive an operating MIC from a segment MIC at runtime. A validator-only approved pair table may reject an inconsistent explicit pair; it may never fill, repair, or convert a missing operating MIC.

### B.3 Existing research registry

`workspace/policies/instrument_registry.json` remains a research registry and scope seed. Its current `canonical_authority` flag is interpreted only within its existing research-registry domain. It is not Instrument Identity Authority and must not be imported by the new resolver.

The separate authoritative registry is required because the research registry currently has no MIC contract, no stable identity contract, a policy hash mismatch, and a stale `DRAM.instrument_type = spot_etf`. Instrument Identity Authority controls exact identity/class/MIC facts after activation; the research registry continues to control only its separately approved research metadata until a later reconciliation.

## C. EXACT IMPLEMENTATION PHASES

### C.1 Phase order

| Phase | Scope | Real evidence/artifact | Activation |
|---|---|---:|---:|
| `II-SA-SPEC` | This integrated Specification | No | No |
| `II-B1` | Identity runtime/contracts, shared immutable-authority I/O primitive, Session V2 scope/schema alignment, M1 trusted resolver integration, synthetic temporary fixtures only | No | No |
| `II-J1` | Independent adversarial Judge of `II-B1` | No | No |
| `II-B2` | Approved machine-readable 8-symbol evidence packet and normalized immutable identity registry candidate | Yes, identity only | No |
| `II-J2` | Independent byte/hash/provenance/record Judge | Yes, identity only | No |
| `SA-B2` | Official NYSE Group/Nasdaq/Cboe source review, acquisition, agreement evaluation, calendar source bundle and candidate artifact | Yes, calendar only | No |
| `SA-J2` | Independent calendar source/materialization Judge | Yes, calendar only | No |
| `II-RM1` | Separately approved research-registry DRAM reconciliation and dependent policy-hash/cache proposal | No new Authority | No |
| `ACT-J1` | Coordinated identity/calendar activation-candidate and cohort review | Accepted candidates only | Candidate/Shadow only |
| `SHADOW-ACT` | Isolated-root coordinated Shadow activation with a new cohort | Accepted candidates | Shadow only |
| `PROD-ACT` | Fixed-root production activation after explicit user approval | Accepted candidates | Yes |
| `LIVE-M1` | One separately approved Live Manual read-only preflight | Active Authorities | No execution |
| `M2` | Separate future boundary | Out of this Specification | Out of scope |

### C.2 Recommended Builder order

`Option 2` is selected:

```text
Identity runtime/contracts
+ Session scope amendment
+ M1 resolver integration
+ synthetic fixtures only
-> independent Judge
-> official identity materialization
```

This order prevents official research facts from becoming code constants, exercises the complete trust boundary before production bytes exist, and avoids implementing M1 twice against incompatible old/new MIC semantics. Identity materialization and calendar acquisition remain separate phases.

### C.3 First Builder fixture rule

`II-B1` may create activation/artifact bytes only below temporary test roots. The fixture uses explicit `synthetic` identifiers and synthetic names. It may use the approved eight-symbol scope as a policy constant, but must not embed the eight official symbol-to-venue/MIC/name records as production or source-code constants.

No file may be created under either production namespace during `II-B1`:

```text
workspace/instrument-identity-authority/
workspace/calendar-authority/artifacts/
workspace/policies/instrument_identity_activation.json
workspace/policies/session_calendar_activation.json
```

## D. EXACT FILE / MODULE PLAN

### D.1 Current Specification deliverable

| Path | Action | Responsibility | Why required |
|---|---|---|---|
| `docs/integrated-instrument-identity-session-authority-implementation-spec.md` | NEW | This contract | Gives Builder and Judge one canonical boundary document |

### D.2 `II-B1` files

| Path | Action | Responsibility | Why required |
|---|---|---|---|
| `manage-us-stock-strategy/scripts/authority_artifact_io.py` | NEW | Narrow shared canonical-JSON and fixed-root, no-reparse, single-handle read primitives | Reuses verified Session loader security without duplicating it or creating a generic filesystem framework |
| `manage-us-stock-strategy/scripts/instrument_identity_artifact.py` | NEW | Fixed paths, identity artifact/activation schema validation, raw-byte hash binding, semantic validation, immutable loaded snapshot | Separates artifact integrity from identity resolution |
| `manage-us-stock-strategy/scripts/instrument_identity_authority.py` | NEW | Frozen identity view, CURRENT temporal rules, trusted ticker resolver and failure mapping | Supplies the missing Production trusted resolver |
| `manage-us-stock-strategy/schemas/instrument-identity-artifact.schema.json` | NEW | Closed structural contract for the bounded eight-symbol immutable registry | Schema is required before any official candidate bytes |
| `manage-us-stock-strategy/schemas/instrument-identity-activation.schema.json` | NEW | Closed fixed-manifest binding contract | Artifact existence must remain distinct from activation |
| `manage-us-stock-strategy/tests/test_instrument_identity_authority.py` | NEW | Loader, resolver, temporal, duplicate, MIC-pair, binding, path and substitution attacks | One focused identity test module is sufficient for MVP |
| `manage-us-stock-strategy/scripts/session_calendar_artifact.py` | MODIFY | Import shared I/O primitives; adopt V2 names, fixed filename, exact operating scope, source families, cohort binding and V2 semantic checks | Removes segment-MIC ambiguity and binds Cboe inclusion |
| `manage-us-stock-strategy/scripts/session_authority.py` | MODIFY | V2 field/parameter names and exact operating-MIC gate; preserve date/phase derivation | Aligns runtime semantics without changing finalization basis |
| `manage-us-stock-strategy/schemas/session-calendar-artifact.schema.json` | MODIFY | V2 operating scope/source-family/common-day contract | Old ARCX-scope artifacts must be structurally invalid |
| `manage-us-stock-strategy/schemas/session-calendar-activation.schema.json` | MODIFY | V2 operating scope/source-family/cohort binding | Old manifests must not activate new runtime semantics |
| `manage-us-stock-strategy/tests/test_session_authority.py` | MODIFY | Replace old scope fixtures and add old-manifest, segment-MIC, XCBO, source-family and shared-I/O regressions | Proves SA-B1 derivation/security remain intact |
| `manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py` | MODIFY | Remove caller MIC map; resolve identity first; call Session only for verified identity; emit separate audit fields | Completes the trusted M1 success path without touching selector semantics |
| `manage-us-stock-strategy/schemas/manual-portfolio-analysis.schema.json` | MODIFY | Manual report schema `2.0` identity/session audit fields and exact operating-MIC naming | Prevents failure masking and ambiguous MIC audit output |
| `manage-us-stock-strategy/tests/test_manual_portfolio_analysis.py` | MODIFY | Synthetic identity resolver/fixture, call-order assertions, end-to-end attacks, protected-state/dependency checks | Proves upstream trust and selector isolation |

`authority_artifact_io.py` is deliberately narrow. It owns only the already verified canonical bytes, descendant confinement, Windows handle/final-path/reparse checks, POSIX no-symlink checks, single-handle read, and canonical-object decode. It owns no authority paths, schema names, policy identities, MICs, activation fields, or reason codes. The Session and Identity loaders retain those semantics separately.

### D.3 Later materialization-only files

| Path | Phase | Action | Responsibility |
|---|---|---|---|
| `manage-us-stock-strategy/schemas/instrument-identity-evidence-packet.schema.json` | `II-B2` | NEW | Machine-readable official identity evidence packet |
| `manage-us-stock-strategy/scripts/materialize_instrument_identity_artifact.py` | `II-B2` | NEW | Offline packet-to-candidate normalizer; no network and no activation |
| `workspace/instrument-identity-authority/source-packets/<source_packet_hash>/us-equity-instrument-identity-current-v1.sources.json` | `II-B2` | NEW candidate | Immutable approved-source packet |
| `workspace/instrument-identity-authority/artifacts/<registry_hash>/us-equity-instrument-identity-current-v1.registry.json` | `II-B2` | NEW candidate | Immutable identity artifact |
| `manage-us-stock-strategy/schemas/session-calendar-source-bundle.schema.json` | `SA-B2` | NEW | Three-family day-by-day source/evidence contract |
| `manage-us-stock-strategy/scripts/materialize_session_calendar_artifact.py` | `SA-B2` | NEW | Official-source bundle comparison and common candidate materialization; no activation |
| `workspace/calendar-authority/source-bundles/<source_bundle_hash>/us-equities-core-session-v2.sources.json` | `SA-B2` | NEW candidate | Immutable NYSE/Nasdaq/Cboe normalized evidence |
| `workspace/calendar-authority/artifacts/<calendar_hash>/us-equities-core-session-v2.calendar.json` | `SA-B2` | NEW candidate | Immutable common calendar V2 artifact |

These later paths reserve ownership; they do not authorize file creation now.

### D.4 Activation and research-reconciliation files

| Path | Phase | Action | Rule |
|---|---|---|---|
| `workspace/policies/instrument_identity_activation.json` | `SHADOW-ACT`/`PROD-ACT` | NEW only after approval | Fixed Git-tracked active identity pointer; never created by `II-B1` or `II-B2` |
| `workspace/policies/session_calendar_activation.json` | `SHADOW-ACT`/`PROD-ACT` | NEW/MODIFY only after approval | Fixed Git-tracked active calendar pointer; never created by `II-B1` or `SA-B2` |
| `workspace/policies/instrument_registry.json` | `II-RM1` | MODIFY only after separate approval | Correct DRAM research classification; does not become Identity Authority |
| `stock-strategy-system/alert_policy.json` | `II-RM1` | MODIFY only after explicit policy approval | Rebind canonical research-registry hash and reconcile non-authoritative DRAM cache |

## E. INSTRUMENT IDENTITY ARTIFACT CONTRACT

### E.1 Fixed location and identity

```text
AUTHORITY_ID = US_EQUITY_INSTRUMENT_IDENTITY_CURRENT_V1
TICKER_NAMESPACE = US_EXCHANGE_LISTED
ARTIFACT_SCHEMA_VERSION = 1.0
EXPECTED_SCOPE = [BE, DRAM, FSLY, MVLL, NBIS, NOW, SOXL, TOST]
ARTIFACT_DIRECTORY = workspace/instrument-identity-authority/artifacts
ARTIFACT_FILENAME = us-equity-instrument-identity-current-v1.registry.json
```

The scope array order above is canonical. Schema and semantic validation require the exact array and exactly one record for each ticker.

### E.2 Top-level JSON shape

```json
{
  "artifact_schema_version": "1.0",
  "authority_id": "US_EQUITY_INSTRUMENT_IDENTITY_CURRENT_V1",
  "registry_version": "<immutable-nonempty-version>",
  "ticker_namespace": "US_EXCHANGE_LISTED",
  "scope": ["BE", "DRAM", "FSLY", "MVLL", "NBIS", "NOW", "SOXL", "TOST"],
  "generated_at": "<RFC3339 timestamp>",
  "authority_as_of": "<RFC3339 timestamp>",
  "source_packet_id": "<immutable packet id>",
  "source_packet_hash": "<lowercase SHA-256>",
  "order_authority": false,
  "records": []
}
```

All objects use `additionalProperties: false`. `generated_at >= authority_as_of`. The array is sorted by ticker and contains exactly eight records.

### E.3 Per-record JSON shape

```json
{
  "record_status": "VERIFIED",
  "ticker": "<canonical ticker>",
  "security_name": "<official security name>",
  "instrument_type": "EQUITY | ETF",
  "security_class": "COMMON_STOCK | CLASS_A_COMMON_STOCK | CLASS_A_ORDINARY_SHARES | ACTIVELY_MANAGED_ETF | LEVERAGED_ETF",
  "primary_listing_venue_name": "<official venue name>",
  "primary_listing_segment_mic": "<explicit segment MIC>",
  "primary_listing_operating_mic": "XNYS | XNAS | XCBO",
  "effective_from": "<date or null>",
  "effective_from_basis": "VERIFIED_DATE | CURRENT_AS_OF_ONLY",
  "effective_to": null,
  "source_ref_ids": ["<source_ref_id>"]
}
```

Required semantic rules:

1. `ticker` is strict uppercase namespace syntax and is unique.
2. Record ticker set equals top-level `scope`; missing, extra, duplicate, or ambiguous records invalidate the artifact.
3. `record_status` is exactly `VERIFIED`; an active artifact cannot carry partially verified records.
4. `primary_listing_segment_mic` and `primary_listing_operating_mic` are both explicit. Neither may be inferred from the other.
5. Validator-only accepted pairs for MVP are `(XNYS,XNYS)`, `(ARCX,XNYS)`, `(BATS,XCBO)`, `(XNGS,XNAS)`, and `(XNMS,XNAS)`. This table rejects mismatch only and is forbidden from producing a value.
6. `EQUITY` permits only equity security classes; `ETF` permits only ETF security classes.
7. `VERIFIED_DATE` requires a date-valued `effective_from` not after the artifact cutoff date.
8. `CURRENT_AS_OF_ONLY` requires `effective_from = null`; null never means an unbounded historical interval.
9. Non-null `effective_to` must be on or after `effective_from` when the latter is known and must not precede `authority_as_of` for a CURRENT candidate.
10. Every record has at least one unique `source_ref_id`. `II-J2` proves the referenced claims exist in the bound evidence packet.

### E.4 Fields intentionally omitted

- `record_hash`: omitted. The raw-byte artifact hash protects every record and array order; a record hash adds no independent security boundary.
- `record_schema_version`: omitted. The closed artifact schema versions every record.
- per-record `ticker_namespace`: omitted. It is artifact-wide and bound by activation.
- per-record `authority_as_of`: omitted. The conservative artifact cutoff governs all records; per-source timestamps live in the evidence packet.
- per-record `order_authority`: omitted. Artifact and all resolver views fix `order_authority=false`.
- `issuer_or_sponsor`: omitted from MVP runtime because the approved input supplies official security names but not a complete normalized issuer/sponsor field set. It may be added only through a schema-version review.
- `instrument_identity_id`: omitted for CURRENT MVP under E.5.

### E.5 Internal identity ID decision

| Option | Verdict | Reason |
|---|---|---|
| Content-derived key | Reject | Changes when a name/classification correction occurs and is therefore not identity-stable |
| Static/monotonic registry ID | Reserve for future | Can survive ticker rename, but assigning IDs now creates unsupported governance and migration work |
| No separate ID in CURRENT MVP | Select | Exact bounded lookup is namespace+ticker with one current record; replay/rename is explicitly forbidden |

Future rename/replay work must add an opaque static ID through a versioned schema and approval. Ticker-derived IDs such as `BE-US` are permanently forbidden.

## F. IDENTITY ACTIVATION CONTRACT

### F.1 Fixed manifest

```text
ACTIVATION_PATH = workspace/policies/instrument_identity_activation.json
ACTIVATION_SCHEMA_VERSION = 1.0
```

The file is a fixed Git-tracked manifest. No public API accepts an activation path, artifact path, registry hash, scope, source URL, or caller mapping.

### F.2 Manifest shape

```json
{
  "activation_schema_version": "1.0",
  "activation_status": "ACTIVE | INACTIVE",
  "activation_reason_code": "INITIAL_BOOTSTRAP | REGISTRY_REFRESH | MANUAL_DEACTIVATION | IDENTITY_CONFLICT",
  "activation_reason": "<nonempty audit text>",
  "authority_id": "US_EQUITY_INSTRUMENT_IDENTITY_CURRENT_V1",
  "active_registry_hash": "<lowercase SHA-256>",
  "active_registry_version": "<registry_version>",
  "ticker_namespace": "US_EXCHANGE_LISTED",
  "scope": ["BE", "DRAM", "FSLY", "MVLL", "NBIS", "NOW", "SOXL", "TOST"],
  "source_packet_id": "<source_packet_id>",
  "source_packet_hash": "<source_packet_hash>",
  "authority_as_of": "<artifact authority_as_of>",
  "activated_at": "<RFC3339 timestamp>",
  "authority_modes_allowed": ["CURRENT"],
  "activation_cohort_id": "<approved shared identity/calendar cohort id>"
}
```

### F.3 Activation semantics

```text
artifact present + manifest absent       -> ARTIFACT_NOT_ACTIVATED
manifest INACTIVE                        -> ARTIFACT_NOT_ACTIVATED
activation_reason_code IDENTITY_CONFLICT -> INTEGRITY_FAILURE and no resolution
ACTIVE + every binding/integrity check   -> eligible for temporal resolution
```

The manifest binds `authority_id`, version, namespace, exact scope, source packet ID/hash, authority cutoff, and raw artifact hash. It also requires `authority_modes_allowed = [CURRENT]` and `authority_as_of <= generated_at <= activated_at`.

`activation_cohort_id` is activation provenance, not a combined Authority. M1 compares it with the active Session Authority cohort; the Authorities otherwise remain separate.

## G. IDENTITY HASH / PROVENANCE CONTRACT

### G.1 Canonical bytes and artifact hash

Reuse the Session loader convention exactly:

```text
UTF-8
JSON object only
sort_keys = true
separators = (",", ":")
allow_nan = false
exactly one trailing LF
no BOM
SHA-256 over exact raw bytes
```

The loader reads the activation once from an already checked handle, derives a fixed content-addressed artifact path from `active_registry_hash`, reads the artifact once from an already checked handle, hashes those exact bytes, compares the hash, then canonical-decodes and schema-validates the same bytes. Reopen-for-hash and mutable alias reads are forbidden.

### G.2 Evidence packet model

Use one artifact-level immutable source packet and per-record `source_ref_ids`. Do not duplicate full provenance on every record.

The later evidence packet requires:

```text
packet_schema_version
source_packet_id
ticker_namespace
scope
generated_at
authority_as_of
claims[]:
  source_ref_id
  ticker
  source_family
  publisher
  source_reference
  retrieved_at
  publication_or_effective_date (date or null)
  claim_scope[]
  content_sha256
```

`claim_scope` supports at least `SECURITY_IDENTITY`, `CURRENT_PRIMARY_LISTING_VENUE`, `SEGMENT_MIC`, `PRIMARY_OPERATING_MIC`, `INSTRUMENT_CLASSIFICATION`, and `EFFECTIVE_DATE_BASIS`.

The runtime loader binds the packet ID/hash declarations but does not fetch or parse the research packet on every M1 call. `II-J2` independently verifies the actual packet bytes, hash, source-ref coverage, and record claims before candidate acceptance. This keeps research evidence out of the runtime hot path without severing provenance.

## H. IDENTITY RESOLVER API

### H.1 Production API

```python
def resolve_instrument_identity(
    ticker: str,
    *,
    decision_as_of: str | None = None,
    authority_mode: Literal["CURRENT"] = "CURRENT",
) -> InstrumentIdentityView:
    ...
```

`ticker` must already be canonical uppercase syntax. The resolver does not trim, uppercase, alias-map, discover, or search. M1's existing syntactic ticker normalization may produce a canonical lookup key, but that normalization grants no identity authority; success still requires an exact active-registry record.

`decision_as_of=None` is permitted only for an ordinary CURRENT call and captures one current UTC cutoff internally. Reproducible M1 and every Judge call pass an explicit cutoff.

### H.2 Test-only seam

```python
def _resolve_instrument_identity_from_root(
    ticker: str,
    *,
    trusted_root: Path,
    decision_as_of: str,
    authority_mode: Literal["CURRENT"] = "CURRENT",
) -> InstrumentIdentityView:
    ...
```

The only seam is an underscore-prefixed fixed-layout temporary-root seam. Production code never exposes or forwards it. M1 tests patch the imported resolver symbol or use this seam against a temporary root; `run_manual_preflight` receives no resolver, mapping, path, or hash argument.

### H.3 Forbidden API surface

The resolver and M1 CLI/function signatures must not accept:

```text
primary_mic
exchange
instrument_primary_mics
artifact_path
activation_path
registry_hash
caller authority mapping
arbitrary source URL
Kiwoom market category
```

No `--primary-mic`, `--exchange`, identity artifact path, activation path, or registry hash CLI flag may be added.

### H.4 Frozen derived view

Use one internal `@dataclass(frozen=True)`; no persisted derived-view schema is required.

```text
authority_status
authority_reason
authority_id
registry_version
registry_hash
activation_cohort_id
ticker_namespace
ticker
security_name
instrument_type
security_class
primary_listing_venue_name
primary_listing_segment_mic
primary_listing_operating_mic
effective_from
effective_from_basis
effective_to
authority_as_of
source_packet_id
source_packet_hash
source_ref_ids
decision_as_of
order_authority = false
```

Failure views preserve only safe audit identifiers and set security/MIC/record fields to null. They never echo an untrusted MIC.

## I. IDENTITY FAILURE SEMANTICS

Use the same top-level status vocabulary as Session Authority:

```text
authority_status = VERIFIED | NOT_VERIFIED
```

Identity-specific reason set:

| Reason | Exact use |
|---|---|
| `OK` | One eligible verified record returned |
| `INVALID_INPUT` | Non-string/noncanonical ticker, invalid timestamp, or mode other than CURRENT |
| `ARTIFACT_NOT_ACTIVATED` | Manifest missing or inactive |
| `UNKNOWN_SYMBOL` | Canonical ticker absent from exact active scope/records |
| `AMBIGUOUS_SECURITY` | Defense-in-depth: more than one eligible record; semantic validation should normally reject first |
| `OUT_OF_EFFECTIVE_RANGE` | Record exists but no interval is eligible at the cutoff |
| `PRIMARY_MIC_NOT_VERIFIED` | Defense-in-depth: eligible record lacks an independently explicit valid operating MIC; never derive it |
| `INTEGRITY_FAILURE` | Schema, hash, binding, scope, duplicate, ordering, MIC-pair, canonical-byte, path, reparse, or substitution failure |
| `TEMPORAL_VIOLATION` | Artifact/generated/activation time is after the decision cutoff, including pre-activation replay attempts |

`UNSUPPORTED_INSTRUMENT` and `TEMPORAL_EVIDENCE_UNAVAILABLE` are omitted. Unsupported types are schema/integrity failures; CURRENT pre-activation replay is a `TEMPORAL_VIOLATION`. This avoids redundant reason proliferation.

M1 may render an orchestration label `IDENTITY_NOT_VERIFIED:<reason>`, but `IDENTITY_NOT_VERIFIED` is not an Identity Authority reason and must not replace the specific reason.

`WRONG_EXCHANGE_SCOPE` is never emitted by Identity Authority. It is reserved for a verified explicit operating MIC that Session Authority does not support.

## J. CURRENT 8-SYMBOL RECORD CONTRACT

The following is the only approved candidate normalization. It is Specification input, not a production artifact or source-code constant.

| Ticker | security_name | instrument_type | security_class | primary_listing_venue_name | segment MIC | operating MIC | effective_from | basis | effective_to |
|---|---|---|---|---|---|---|---|---|---|
| `BE` | Bloom Energy Corporation Common Stock | `EQUITY` | `COMMON_STOCK` | New York Stock Exchange | `XNYS` | `XNYS` | null | `CURRENT_AS_OF_ONLY` | null |
| `DRAM` | Roundhill Memory ETF | `ETF` | `ACTIVELY_MANAGED_ETF` | Cboe BZX Exchange | `BATS` | `XCBO` | `2026-04-02` | `VERIFIED_DATE` | null |
| `FSLY` | Fastly, Inc. Class A Common Stock | `EQUITY` | `CLASS_A_COMMON_STOCK` | Nasdaq Global Select Market | `XNGS` | `XNAS` | `2025-12-09` | `VERIFIED_DATE` | null |
| `MVLL` | GraniteShares 2x Long MRVL Daily ETF | `ETF` | `LEVERAGED_ETF` | Nasdaq Global Market | `XNMS` | `XNAS` | `2025-03-07` | `VERIFIED_DATE` | null |
| `NBIS` | Nebius Group N.V. Class A Ordinary Shares | `EQUITY` | `CLASS_A_ORDINARY_SHARES` | Nasdaq Global Select Market | `XNGS` | `XNAS` | `2024-10-21` | `VERIFIED_DATE` | null |
| `NOW` | ServiceNow, Inc. Common Stock | `EQUITY` | `COMMON_STOCK` | New York Stock Exchange | `XNYS` | `XNYS` | null | `CURRENT_AS_OF_ONLY` | null |
| `SOXL` | Direxion Daily Semiconductor Bull 3X ETF | `ETF` | `LEVERAGED_ETF` | NYSE Arca | `ARCX` | `XNYS` | null | `CURRENT_AS_OF_ONLY` | null |
| `TOST` | Toast, Inc. Class A Common Stock | `EQUITY` | `CLASS_A_COMMON_STOCK` | New York Stock Exchange | `XNYS` | `XNYS` | `2021-09-22` | `VERIFIED_DATE` | null |

Every later materialized record also requires `record_status=VERIFIED` and approved `source_ref_ids`. Those IDs cannot be invented from this table; they come from the independently hash-verified evidence packet.

DRAM is authoritatively normalized as an actively managed ETF, not a spot ETF. The new resolver never reads the stale research-registry classification.

## K. CURRENT_AS_OF_ONLY / TEMPORAL CONTRACT

### K.1 Typed representation

Do not use a mixed string sentinel such as `effective_from: "CURRENT_AS_OF_ONLY"` and do not invent a listing date.

```text
known verified start:
  effective_from = YYYY-MM-DD
  effective_from_basis = VERIFIED_DATE

current evidence only:
  effective_from = null
  effective_from_basis = CURRENT_AS_OF_ONLY
```

For a CURRENT_AS_OF_ONLY record, `effective_from=null` does not authorize history. Its eligible floor is the active artifact's `authority_as_of` and `activated_at` temporal gate.

### K.2 CURRENT resolver eligibility

For cutoff `D = decision_as_of`:

```text
authority_mode == CURRENT
artifact.authority_as_of <= D
artifact.generated_at <= D
activation.activated_at <= D
record is current at D
```

CURRENT MVP does not permit pre-activation replay even when a record has a historical `VERIFIED_DATE`. `effective_from` preserves evidence for future versioned replay work; it does not grant replay authority now.

No `REPLAY_AS_KNOWN`, `REPLAY_AS_TRADED_RESTATED`, successor graph, listing-history reconstruction, or automatic delisting logic is implemented.

## L. SESSION AUTHORITY SCOPE AMENDMENT

### L.1 Version boundary

The operating-MIC correction is a semantic contract change, not a string-only patch.

```text
SESSION_VIEW_CONTRACT_VERSION = 2.0
CALENDAR_POLICY_IDENTITY = US_EQUITIES_CORE_SESSION_V2
SESSION_ARTIFACT_SCHEMA_VERSION = 2.0
SESSION_ACTIVATION_SCHEMA_VERSION = 2.0
EXPECTED_OPERATING_MIC_SCOPE = [XNYS, XNAS, XCBO]
```

The conceptual authority remains the common U.S. equities core-session calendar, but its version changes because the operating-market set, source-family completeness, field names, and activation semantics change.

### L.2 Required symbol/field renames

| Old | New |
|---|---|
| `EXPECTED_VENUE_SCOPE` | `EXPECTED_OPERATING_MIC_SCOPE` |
| artifact/activation `venue_scope` | `operating_mic_scope` |
| `venue_agreement_status` | `operating_mic_agreement_status` |
| `SessionAuthorityView.venue_scope` | `SessionAuthorityView.operating_mic_scope` |
| `instrument_primary_mic` parameter/field | `primary_listing_operating_mic` |
| `us-equities-core-session-v1.calendar.json` | `us-equities-core-session-v2.calendar.json` |

No backward-compatible alias is allowed in the production API or schemas. Old field names are accepted only as negative-test inputs and must fail.

### L.3 Scope semantics

```text
accepted operating MICs: XNYS, XNAS, XCBO
rejected segment MICs:   ARCX, BATS, XNGS, XNMS
```

Direct Session Authority calls outside exact scope return `WRONG_EXCHANGE_SCOPE` only after the calendar loads successfully. Production M1 reaches this check only after a verified identity view supplies an explicit operating MIC.

### L.4 Preserved derivation semantics

The following current SA-B1 behavior is unchanged:

- strict RFC3339 and ET conversion;
- `decision_as_of <= observed_at`;
- artifact/generated/activation timestamps not after cutoff;
- `NON_TRADING_DATE`, `PRE_CORE`, `CORE_OPEN`, `POST_CORE` classification;
- current-date session view;
- `expected_completed_session` is the latest session strictly before the current ET date;
- Monday, weekend, holiday, early-close and DST handling;
- coverage checks;
- `NEXT_ET_CALENDAR_DAY_PROVIDER_ARCHIVE` finalization basis;
- no same-day completed-bar authority.

## M. SESSION ARTIFACT / ACTIVATION AMENDMENT

### M.1 Calendar artifact V2

Required top-level fields are:

```text
artifact_schema_version = 2.0
calendar_policy_identity = US_EQUITIES_CORE_SESSION_V2
timezone_identity = America/New_York
operating_mic_scope = [XNYS, XNAS, XCBO]
source_families = [NYSE_GROUP, NASDAQ, CBOE]
coverage_start
coverage_end
source_bundle_id
source_bundle_hash
calendar_version
generated_at
authority_as_of
operating_mic_agreement_status = VERIFIED
sessions[]
closures[]
```

`sessions[]` remains:

```text
session_date
core_open_at
core_close_at
close_type = REGULAR | EARLY
```

`closures[]` becomes minimal:

```text
closure_date
```

The common artifact does not require a cross-exchange `closure_type` label. Publisher-specific closure labels are descriptive source-bundle metadata and may differ without causing failure. `close_type` for an open session is different: it is decision-relevant and must agree with the open/close schedule.

The current separate `sessions` and `closures` arrays are retained instead of creating a new day-state engine. Their membership is the common artifact representation of `is_session=true/false`.

### M.2 Day-by-day materialization equality

For every covered weekday, each of XNYS, XNAS, and XCBO must independently provide a normalized row. Materialization requires:

```text
is_session equality
session_date equality
if is_session:
  core_open_at equality
  core_close_at equality
  close_type equality
if not is_session:
  exchange-specific closure label equality is not required
```

Missing family data, missing day rows, or any decision-relevant mismatch produces `CONFLICTING_CALENDAR` and no activatable artifact. Union, intersection, majority vote, carrying forward a prior venue row, or silent label/time normalization is forbidden.

### M.3 Calendar activation V2

The fixed path remains `workspace/policies/session_calendar_activation.json`, but its closed V2 schema requires and binds:

```text
activation_schema_version = 2.0
activation_status
activation_reason_code
activation_reason
calendar_policy_identity = US_EQUITIES_CORE_SESSION_V2
active_calendar_hash
active_calendar_version
timezone_identity
operating_mic_scope = [XNYS, XNAS, XCBO]
source_families = [NYSE_GROUP, NASDAQ, CBOE]
coverage_start
coverage_end
source_bundle_id
source_bundle_hash
authority_as_of
activated_at
authority_modes_allowed = [CURRENT]
activation_cohort_id
```

An old V1 manifest, old filename, old policy identity, `venue_scope`, or `[XNYS,ARCX,XNAS]`/`[ARCX,XNAS,XNYS]` scope fails schema or binding with no migration fallback.

The loader also requires `authority_as_of <= generated_at <= activated_at` and exposes `activation_cohort_id` in the frozen Session view for M1 cohort comparison.

## N. CBOE SOURCE-FAMILY IMPACT

The future official calendar source allowlist is exactly:

```text
NYSE_GROUP
NASDAQ
CBOE
```

`DRAM -> BATS segment -> XCBO operating` makes CBOE source evidence mandatory. A source bundle with only NYSE Group and Nasdaq cannot set `operating_mic_agreement_status=VERIFIED`, cannot produce an activatable V2 artifact, and cannot pass `SA-J2`.

This Specification does not invent or approve a Cboe URL:

```text
CBOE_EXACT_SOURCE_REFERENCE = TO_BE_VERIFIED_IN_SA_B2_SOURCE_REVIEW
```

`SA-B2` must establish an official Cboe source capability, immutable raw/normalized evidence, retrieval cutoff, parse provenance, and provider-failure state before materialization. Missing or stale Cboe evidence remains visible and fails closed.

## O. IDENTITY -> SESSION INTERFACE

The interface is a single explicit value plus separate audit provenance:

```text
identity_view.authority_status == VERIFIED
identity_view.primary_listing_operating_mic is explicit and verified
-> derive_us_market_session_authority(
     ..., primary_listing_operating_mic=<that exact value>
   )
```

The Session function does not receive the whole identity object, segment MIC, Kiwoom category, research registry row, venue name, or caller mapping. This preserves authority separation.

The orchestration invariants are:

1. Identity failure means Session Authority is not called for that ticker.
2. Segment MIC is retained only in identity/report audit fields.
3. M1 never converts segment to operating MIC.
4. A verified explicit operating MIC outside Session scope produces `WRONG_EXCHANGE_SCOPE`.
5. Identity and Session active `activation_cohort_id` values must match before finalized-bar success.
6. All successful tickers in one M1 report must share one identity registry hash, one calendar hash, and one activation cohort. Mixed snapshots fail `INTEGRITY_FAILURE`; a null audit hash cannot pass.

## P. M1 INTEGRATION CONTRACT

### P.1 Production flow

```text
selected canonical ticker
-> resolve_instrument_identity(ticker, decision_as_of=cutoff)
-> if NOT_VERIFIED:
     no Session call
     no daily-chart finalized request
     no selector call
     finalized path FAIL
-> if VERIFIED:
     retain segment MIC for audit only
     pass primary_listing_operating_mic to Session Authority
-> if Session NOT_VERIFIED:
     no selector call
     finalized path FAIL
-> if Session VERIFIED:
     request exact expected_completed_session
     call unchanged _select_last_verified_finalized_bar
```

### P.2 Function/API change

Remove this parameter from `run_manual_preflight`:

```python
instrument_primary_mics: Mapping[str, str] | None
```

Do not replace it with another caller-supplied resolver, map, path, hash, exchange, or MIC parameter. Tests patch the imported trusted resolver or use temporary fixed-root seams.

### P.3 Report schema V2

Set `manual-portfolio-analysis.schema.json` top-level `schema_version = 2.0`. Add required top-level fields:

```text
identity_authority_status = VERIFIED | NOT_VERIFIED
identity_authority_reasons[]
identity_authority_id = string | null
identity_registry_version = string | null
identity_registry_hash = lowercase SHA-256 | null
identity_activation_cohort_id = string | null
session_activation_cohort_id = string | null
integrated_authority_cohort_status = MATCHED | NOT_VERIFIED
```

Per `last_verified_finalized_bars[]`, replace `instrument_primary_mic` with and add:

```text
identity_authority_status
identity_authority_reason
primary_listing_segment_mic = string | null
primary_listing_operating_mic = string | null
session_authority_status
session_authority_reason
```

When identity fails, report:

```text
identity_authority_status = NOT_VERIFIED
identity_authority_reason = <specific identity reason>
session_authority_status = NOT_VERIFIED
session_authority_reason = UPSTREAM_IDENTITY_NOT_VERIFIED
status = NOT_VERIFIED
reason = IDENTITY_NOT_VERIFIED:<specific identity reason>
```

`UPSTREAM_IDENTITY_NOT_VERIFIED` is an M1 orchestration reason only and is not added to `SessionAuthority.AUTHORITY_REASONS`.

Top-level finalized success requires all of the following:

```text
all identities VERIFIED
one non-null identity registry hash
all Sessions VERIFIED
one non-null calendar hash
non-null identity and Session cohort IDs that are exactly equal
integrated_authority_cohort_status = MATCHED
one common expected_completed_session
every selected bar matches ticker and expected session
```

Identity failure adds a visible `IDENTITY_AUTHORITY_NOT_VERIFIED:<reasons>` partial reason and forces `finalized_bar_preflight_status=FAIL`. It does not create execution authority or mutate state.

### P.4 Selector freeze

The source and semantics of `_select_last_verified_finalized_bar` and public legacy-disable wrapper remain unchanged. The existing test that hashes/AST-compares the private selector is extended to assert no semantic change. All work occurs upstream.

## Q. SECURITY TEST MATRIX

### Q.1 Identity loader/resolver

| Attack/case | Required result |
|---|---|
| Unknown canonical ticker | `UNKNOWN_SYMBOL`; no Session call |
| Lowercase/whitespace alias passed directly | `INVALID_INPUT`; no uppercase/trim aliasing in resolver |
| Ticker reuse represented by duplicate current records | `INTEGRITY_FAILURE` or defense-in-depth `AMBIGUOUS_SECURITY`; never pick one |
| Overlapping effective ranges | Fail closed; never latest/first-wins |
| Expired record at cutoff | `OUT_OF_EFFECTIVE_RANGE` |
| Artifact/activation/source cutoff after decision | `TEMPORAL_VIOLATION` |
| Pre-activation historical replay | `TEMPORAL_VIOLATION` |
| Missing or inactive manifest | `ARTIFACT_NOT_ACTIVATED` |
| Artifact exists outside active hash namespace | Ignored; no directory scan |
| Duplicate/missing/extra scope record | `INTEGRITY_FAILURE` |
| Wrong segment MIC or wrong operating MIC | `INTEGRITY_FAILURE`/`PRIMARY_MIC_NOT_VERIFIED` |
| Invalid segment/operating pair | `INTEGRITY_FAILURE`; no conversion |
| One-byte artifact mutation | `INTEGRITY_FAILURE` |
| Activation hash spoof/wrong version/scope/source packet binding | `INTEGRITY_FAILURE` |
| Noncanonical JSON/BOM/extra properties | `INTEGRITY_FAILURE` |
| Activation/artifact symlink, junction, reparse or outside-root substitution | `INTEGRITY_FAILURE` |
| Path traversal or alternate artifact filename | No public surface; internal load fails |
| TOCTOU/mutable alias/hash-after-reopen attack | Same-handle read/hash/parse or fail closed |
| Caller MIC mapping injection | Parameter absent; static signature test |
| Kiwoom market-category injection | No import/data path; cannot produce a MIC |
| Research registry fallback | No import/path/reference; inactive identity remains NOT_VERIFIED |
| `DRAM=spot_etf` contamination | Identity result comes only from active authoritative artifact; test poisons research registry and result is unchanged |

### Q.2 Session amendment

| Attack/case | Required result |
|---|---|
| `ARCX` supplied as operating MIC | `WRONG_EXCHANGE_SCOPE` |
| `BATS` supplied as operating MIC | `WRONG_EXCHANGE_SCOPE` |
| `XNGS` supplied as operating MIC | `WRONG_EXCHANGE_SCOPE` |
| `XNMS` supplied as operating MIC | `WRONG_EXCHANGE_SCOPE` |
| `XCBO` omitted from artifact or activation scope | schema/binding `INTEGRITY_FAILURE` |
| Identity VERIFIED for DRAM/XCBO and V2 calendar valid | Session scope gate accepts XCBO |
| DRAM/XCBO with old ARCX-scope activation | old manifest rejected; no fallback |
| XNYS/XNAS/XCBO `is_session` disagreement | `CONFLICTING_CALENDAR`; no artifact activation |
| Open/close/close_type disagreement | `CONFLICTING_CALENDAR` |
| Only descriptive closed-day label differs | permitted; raw labels retained in source bundle |
| CBOE family missing/stale/unavailable | no VERIFIED common artifact; fail closed |
| Old `venue_scope` field or V1 policy/filename | schema/integrity failure |
| Activation/artifact operating scope mismatch | `INTEGRITY_FAILURE` |
| Legacy fixture silently maps ARCX to XNYS | test must fail; no normalizer is allowed |
| Existing Monday/holiday/early-close/DST cases | identical expected sessions to SA-B1 baseline |

### Q.3 M1 end-to-end

| Flow attack | Session called? | Selector called? | Result |
|---|---:|---:|---|
| Unknown ticker | No | No | finalized FAIL |
| Identity inactive/integrity/temporal failure | No | No | finalized FAIL with identity reason |
| Identity verified but explicit operating MIC unsupported | Yes | No | `WRONG_EXCHANGE_SCOPE`, finalized FAIL |
| Calendar inactive/integrity/temporal/conflict | Yes | No | finalized FAIL with Session reason |
| Identity/calendar cohort mismatch | Yes | No | integrated `INTEGRITY_FAILURE` |
| Mixed registry/calendar hashes in one run | As applicable | No success | integrated `INTEGRITY_FAILURE` |
| Same-day candidate | Yes | Yes | rejected by unchanged selector |
| Stale candidate | Yes | Yes | rejected by unchanged selector |
| Wrong ticker candidate | Yes | Yes | rejected by unchanged selector |
| Wrong reported/expected session | Yes | Yes | rejected by unchanged selector |
| All upstream Authorities and exact prior bar verified | Yes | Yes | `LAST_VERIFIED_FINALIZED_BAR` only |

### Q.4 Independent Judge plan

`II-J1` occurs in a new chat and must not import or trust Builder fixture writers or canonical-byte helpers. The Judge independently:

1. serializes bytes and computes SHA-256 with an independent implementation;
2. builds activation/artifact fixtures under a separate temporary root;
3. mutates bytes, scope, timestamps, records, effective ranges and MIC pairs;
4. attacks symlink/junction/reparse/substitution paths where the OS permits;
5. inspects public signatures/AST for forbidden path/hash/MIC/mapping inputs and forbidden registry/Kiwoom/legacy imports;
6. proves identity failure prevents Session invocation and selector invocation;
7. proves verified identity forwards only the exact operating MIC;
8. repeats every existing Session derivation case against the V2 scope;
9. independently hashes the M1 selector source/AST before and after;
10. hashes protected portfolio/policy/runtime state and `requirements.txt` before and after;
11. confirms no production artifact/activation namespace was created.

Judge outcome is layer-separated: safety failures block merge regardless of ordinary test pass; semantic/decision quality is reported separately; economic performance is not applicable.

## R. BUILDER SUCCESS CRITERIA

`II-B1` PASS requires every item:

- [ ] Identity artifact exact raw-byte SHA-256 verification passes.
- [ ] Identity activation binds hash, version, authority, namespace, exact scope, packet ID/hash and CURRENT mode.
- [ ] Artifact presence without active manifest fails closed.
- [ ] Unknown symbol fails `UNKNOWN_SYMBOL`.
- [ ] Duplicate/ambiguous identity fails closed.
- [ ] Effective interval and all temporal cutoffs are validated.
- [ ] `CURRENT_AS_OF_ONLY` uses null + basis and never backdates evidence.
- [ ] Primary segment MIC is preserved for audit.
- [ ] Primary operating MIC is explicit and independently used.
- [ ] Segment/operating validator rejects mismatch but never converts.
- [ ] Kiwoom category cannot create MIC authority.
- [ ] Caller MIC mapping cannot create authority and the old parameter is absent.
- [ ] Existing research registry cannot create or replace identity authority.
- [ ] DRAM stale `spot_etf` data cannot contaminate identity results.
- [ ] Session Authority exact scope is `[XNYS, XNAS, XCBO]`.
- [ ] `ARCX`, `BATS`, `XNGS`, and `XNMS` are rejected as operating-MIC inputs.
- [ ] XCBO is accepted when explicit identity and calendar contracts are valid.
- [ ] Session artifact/activation fields use `operating_mic_scope`, not `venue_scope`.
- [ ] Calendar source-family contract is exactly `[NYSE_GROUP, NASDAQ, CBOE]`.
- [ ] Old V1/ARCX activation and artifact contracts are rejected.
- [ ] Existing Session current/expected-session derivation semantics are unchanged.
- [ ] Existing canonical-byte/reparse/TOCTOU Session security remains verified after shared-helper extraction.
- [ ] Identity failure prevents Session Authority call.
- [ ] Identity VERIFIED passes only `primary_listing_operating_mic`.
- [ ] Identity and Session cohort/hash consistency is required for finalized success.
- [ ] Identity failure is not reported as `WRONG_EXCHANGE_SCOPE`.
- [ ] M1 selector source and semantics are unchanged.
- [ ] Same-day, stale, wrong-ticker and wrong-session candidates remain rejected.
- [ ] Manual report schema V2 exposes separate identity and Session audit fields.
- [ ] `order_authority=false`, `quantity_authority=none`, `execution_quantity=null` everywhere applicable.
- [ ] Protected state hashes are unchanged.
- [ ] `manage-us-stock-strategy/requirements.txt` and all dependency manifests are unchanged.
- [ ] No production identity/calendar artifact, source packet, source bundle, or activation manifest exists because of the Builder.
- [ ] No network call, Live Kiwoom call, scheduler change, M2, quantity, fill, order, or portfolio mutation occurs.
- [ ] Independent `II-J1` passes.

## S. BUILDER STOP CONDITIONS

The Builder must stop with `USER_APPROVAL_REQUIRED` before any of the following:

- official source download or network acquisition;
- actual identity evidence packet or eight-symbol registry materialization;
- actual calendar source bundle or artifact materialization;
- fixed-root production or Shadow activation manifest creation;
- research-registry or approved alert-policy modification;
- new dependency or runtime network dependency;
- persistent mutable runtime state;
- Live Kiwoom execution;
- cohort activation, production cutover, Live Manual preflight, or M2;
- any order, quantity, fill, cash/holding/stage mutation.

The Builder must stop with `BOUNDARY_RESET_REVIEW_REQUIRED` before any of the following:

- a new engine or generic filesystem framework;
- M1 selector semantic change;
- same-day finality or finalization-basis change;
- automatic Kiwoom-to-MIC or segment-to-operating conversion;
- a new operating MIC beyond XNYS/XNAS/XCBO;
- union/intersection/majority calendar logic;
- regulator override, scheduler, replay, or execution semantics;
- weakening exact hash, canonical byte, fixed path, reparse, cohort, scope, or fail-closed checks;
- adding historical replay or ticker-successor identity semantics.

Synthetic temporary fixture creation required by tests is not production materialization or activation. Any write outside the test temporary root is a stop-condition violation.

## T. COHORT / ROLLBACK CONTRACT

### T.1 Cohort

```text
NEW_COHORT_REQUIRED_NOW = NO
NEW_COHORT_REQUIRED_ON_ACTIVATION = YES
```

Identity and Session Authority V2 must be activated in the same semantic cohort because M1 finalized success depends on both. Separate manifests carry the same `activation_cohort_id`; M1 checks equality. No combined Authority or new mutable cohort counter is created.

Shadow activation begins the cohort at zero in an isolated approved root. Manual fixtures, dry runs, replay, backfill, and pre-activation runs do not increase maturity. Production activation preserves provenance but does not backfill the cohort.

### T.2 Partial activation

- Identity active + calendar inactive/invalid: identity may resolve, Session fails, M1 finalized path fails.
- Calendar active + identity inactive/invalid: Identity fails first, Session is not called, M1 finalized path fails.
- Both active but cohort IDs differ: integrated integrity failure.

No partial state can produce finalized success.

### T.3 Rollback

On Identity or Calendar failure, return NOT_VERIFIED and do not fall back to:

```text
caller MIC
Kiwoom ND/NY category
old research registry
market_context.current.json
legacy verify_market_session
directory scan for an old artifact
automatic prior-authority restore
```

Rollback to a previously accepted immutable V2 identity/calendar pair requires a new explicit activation decision with a matched cohort. Restoring the old ARCX-scope V1 calendar is not a compatible rollback and requires a boundary reset review.

## U. USER APPROVAL GATES

| Gate | Approval authorizes | Authority impact | Does not authorize |
|---|---|---|---|
| `GATE 1 - Integrated Builder` | `II-B1` code/schema/test work with synthetic fixtures | No active Authority; boundary-reset implementation only | Evidence download, artifact, activation, Live M1 |
| `GATE 2 - Identity materialization` | Build machine-readable evidence packet and identity candidate from already approved official evidence | Candidate bytes only | Activation or production use |
| `GATE 3 - Calendar SA-B2` | Official NYSE/Nasdaq/Cboe source review, acquisition, comparison and candidate materialization | Candidate calendar evidence only | Activation or Cboe URL assumption before review |
| `GATE 4 - Identity candidate acceptance` | Accept exact identity packet/artifact hashes after `II-J2` | Accepted but inactive identity candidate | Resolver production success |
| `GATE 5 - Calendar candidate acceptance` | Accept exact source bundle/calendar hashes after `SA-J2` | Accepted but inactive calendar candidate | Session production success |
| `GATE 6 - Coordinated Shadow activation` | Activate both accepted candidates in an isolated Shadow root with one new cohort | Shadow read-only Authority only | Production activation, maturity backfill, execution |
| `GATE 7 - Production activation` | Commit/enable both fixed-root manifests with matching cohort after Shadow acceptance | Production read-only identity/session authority | Live broker run or execution |
| `GATE 8 - Live Manual Preflight` | One bounded read-only M1 run using active Authorities | Live evidence collection/report only | M2, scheduler, orders, quantities, state mutation |
| `GATE 9 - M2` | Separately specified future work | Not defined here | Any implicit extension from M1 |

`II-RM1` research-registry/alert-policy reconciliation requires its own explicit policy approval and cannot be inferred from Gates 2, 4, 6, or 7.

## V. FINAL JUDGMENT

```text
INTEGRATED_IMPLEMENTATION_SPEC_READY = YES
IDENTITY_RUNTIME_MVP_READY_TO_BUILD = YES
SESSION_SCOPE_AMENDMENT_READY_TO_BUILD = YES
COMBINED_FIRST_BUILDER_RECOMMENDED = YES
RECOMMENDED_FIRST_BUILDER_PHASE = II-B1
IDENTITY_ARTIFACT_SCHEMA_REQUIRED = YES
IDENTITY_ACTIVATION_MANIFEST_REQUIRED = YES
IDENTITY_DERIVED_VIEW_SCHEMA_REQUIRED = NO
NEW_DEPENDENCY_REQUIRED_FOR_RUNTIME_MVP = NO
NEW_PERSISTENT_RUNTIME_STATE_REQUIRED = NO
NEW_ENGINE_REQUIRED = NO
SESSION_OPERATING_MIC_SCOPE = [XNYS, XNAS, XCBO]
SEGMENT_MIC_ALLOWED_AS_SESSION_INPUT = NO
CBOE_CALENDAR_SOURCE_REQUIRED = YES
SESSION_AUTHORITY_SEMANTICS_CHANGE = YES
FINALIZATION_BASIS_CHANGE = NO
M1_SELECTOR_CHANGE_REQUIRED = NO
M1_INTEGRATION_CHANGE_REQUIRED = YES
IDENTITY_ACTIVATION_REQUIRED_NOW = NO
CALENDAR_ACTIVATION_REQUIRED_NOW = NO
NEW_COHORT_REQUIRED_NOW = NO
NEW_COHORT_REQUIRED_ON_ACTIVATION = YES
EXECUTION_AUTHORITY_CHANGE = NO
BOUNDARY_RESET_REQUIRED = YES
READY_FOR_BUILDER = YES
READY_FOR_IDENTITY_MATERIALIZATION = NO
READY_FOR_SA_B2 = NO
READY_FOR_ACTIVATION = NO
READY_FOR_LIVE_MANUAL_PREFLIGHT = NO
READY_FOR_M2 = NO
RECOMMENDED_BUILDER_REASONING = EXTRA HIGH
RECOMMENDED_BUILDER_CHAT = NEW_CHAT_STRONGLY_RECOMMENDED
RECOMMENDED_NEXT_STEP = Obtain GATE 1 approval, then run II-B1 in a new chat using this Specification and synthetic temporary fixtures only.
```

`READY_FOR_BUILDER=YES` means the implementation contract is complete enough to execute after Gate 1; it is not approval to start. `BOUNDARY_RESET_REQUIRED=YES` is satisfied only by explicit Gate 1 authorization because Session contract/schema version, M1 upstream authority, and report schema boundaries change.

Final safety invariants remain:

```text
ANALYSIS != EXECUTION
RESEARCH_FINDING != PRODUCTION_POLICY
VERIFIED_RESEARCH_EVIDENCE != ACTIVATED_AUTHORITY
CALLER_MAPPING != INSTRUMENT_IDENTITY_AUTHORITY
BROKER_MARKET_CATEGORY != PRIMARY_MIC_AUTHORITY
SESSION_AUTHORITY != IDENTITY_AUTHORITY
BETTER_INTELLIGENCE != MORE_EXECUTION_AUTHORITY
order_authority = false
quantity_authority = none
execution_quantity = null
```

The Specification terminates here. It authorizes no Builder, code/schema changes beyond this document, artifact creation, activation, network acquisition, Live Manual run, scheduler change, cohort activation, M2, quantity calculation, or order.
