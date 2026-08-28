# SA-B2 Calendar Acquisition / Materialization — Builder Final Report

```text
SA_B2_CALENDAR_ACQUISITION_MATERIALIZATION

BUILDER_ROLE =
SA-B2

GATE_3 =
APPROVED


[Repository]

REPOSITORY =
E:\사업\##금동한\코덱스저장소

BRANCH_BEFORE =
codex/master-recovery-expansion

BRANCH_AFTER =
codex/master-recovery-expansion

HEAD_BEFORE =
f9e6f9193d857c3e558cf21871b67a11ea75b057

HEAD_AFTER =
f9e6f9193d857c3e558cf21871b67a11ea75b057

CHANGED_FILES =
manage-us-stock-strategy/schemas/session-calendar-source-bundle.schema.json
manage-us-stock-strategy/scripts/materialize_session_calendar_artifact.py
manage-us-stock-strategy/tests/test_materialize_session_calendar_artifact.py
workspace/calendar-authority/reviewed-inputs/us-equities-core-session-2026-through-20260821.reviewed.json
workspace/calendar-authority/source-bundles/a23bffb956e63e57086994cae928c1a06378d747f6c261d40fbe47c2aebf4f07/us-equities-core-session-v2.sources.json
workspace/calendar-authority/artifacts/266d6c74bcf88dcb8affbfcc35140c69de8ba968668fb47b8ada9254a7a1e408/us-equities-core-session-v2.calendar.json
workspace/calendar-authority/reports/sa-b2-builder-20260823.md


[Official Sources]

NYSE_SOURCE_STATUS =
VERIFIED

NASDAQ_SOURCE_STATUS =
VERIFIED

CBOE_SOURCE_STATUS =
VERIFIED

SOURCE_CONTENT_BYTES_CAPTURED =
NO

SOURCE_CONTENT_HASH_STATUS =
NOT_CAPTURED


[Coverage]

OPERATING_MIC_SCOPE =
XNYS
XNAS
XCBO

COVERAGE_START =
2026-01-01

COVERAGE_END =
2026-08-21

CALENDAR_CONFLICTS =
NONE


[Evidence Packet]

EVIDENCE_PACKET_PATH =
workspace/calendar-authority/source-bundles/a23bffb956e63e57086994cae928c1a06378d747f6c261d40fbe47c2aebf4f07/us-equities-core-session-v2.sources.json

EVIDENCE_PACKET_SHA256 =
a23bffb956e63e57086994cae928c1a06378d747f6c261d40fbe47c2aebf4f07

SOURCE_COUNT =
4

CLAIM_COUNT =
501

CLAIM_SOURCE_EDGE_COUNT =
668

CLAIM_TRACEABILITY =
PASS


[Candidate Calendar Artifact]

CANDIDATE_ARTIFACT_PATH =
workspace/calendar-authority/artifacts/266d6c74bcf88dcb8affbfcc35140c69de8ba968668fb47b8ada9254a7a1e408/us-equities-core-session-v2.calendar.json

CANDIDATE_ARTIFACT_SHA256 =
266d6c74bcf88dcb8affbfcc35140c69de8ba968668fb47b8ada9254a7a1e408

ARTIFACT_SCOPE =
XNYS / XNAS / XCBO

SCHEMA_VALIDATION =
PASS

IMMUTABLE_CREATE_ONLY =
PASS

IDEMPOTENT_REBUILD =
PASS

MISMATCHED_EXISTING_NO_OVERWRITE =
PASS

CANDIDATE_LOADER_COMPATIBILITY =
PASS


[Session Semantics Regression]

EXPECTED_COMPLETED_SESSION_SEMANTICS =
UNCHANGED

SAME_DAY_FINALIZATION =
UNCHANGED

CALENDAR_CONFLICT_FAIL_CLOSED =
PASS

OPERATING_MIC_SCOPE =
UNCHANGED


[Activation Boundary]

IDENTITY_ACTIVATION_STATUS =
ABSENT

CALENDAR_ACTIVATION_STATUS =
ABSENT

ACTIVATION_CHANGED_BY_BUILDER =
NO


[Protected State]

PROTECTED_STATE_RECORD_COUNT =
3

PROTECTED_STATE_MISMATCH_COUNT =
0

PROTECTED_PROJECT_STATE_MUTATED =
NO


[Test Execution]

TARGETED_TESTS =
19 / 19 PASS

SESSION_REGRESSION_TESTS =
41 / 41 PASS

EXIT_CODE =
0

FAILURES =
0

ERRORS =
0

SKIPS =
0


[Complexity]

NEW_ENGINE =
NO

NEW_STATE =
NO

NEW_COUNTER =
NO

NEW_DATABASE =
NO

COMPLEXITY_CHANGE =
INCREASED_JUSTIFIED


[Final Decision]

SA_B2_BUILDER =
PASS

PRODUCTION_SEMANTICS_CHANGED =
NO

EXECUTION_AUTHORITY_CHANGED =
NO

READY_FOR_CALENDAR_INDEPENDENT_JUDGE =
YES

READY_FOR_ACTIVATION =
NO

NEXT_ACTION =
INDEPENDENT_CALENDAR_JUDGE
only if Builder PASS
```

## Official evidence ledger

- `NYSE_HOURS_CALENDAR_2026` — https://www.nyse.com/markets/hours-calendars
- `NASDAQ_TRADER_CALENDAR_2026` — https://www.nasdaqtrader.com/Trader.aspx?id=Calendar
- `NASDAQ_MARKET_HOURS_2026` — https://www.nasdaq.com/market-activity/stock-market-holiday-schedule
- `CBOE_US_EQUITIES_HOURS_2026` — https://www.cboe.com/about/hours

The sources were reviewed on `2026-08-23` with date-only KST precision. Raw publisher bytes were not retained, so every `content_sha256` is `null`; URL, title, or research-prose hashes are not represented as source-content hashes.

## Protected-state fingerprints

| Existing protected file | Before SHA-256 | After SHA-256 | Result |
| --- | --- | --- | --- |
| `stock-strategy-system/portfolio_state.json` | `017225ec657c3fd3e6a6be7de9bb92296839411e98d74cb4627a4b0de605192a` | `017225ec657c3fd3e6a6be7de9bb92296839411e98d74cb4627a4b0de605192a` | MATCH |
| `stock-strategy-system/alert_policy.json` | `255ca47ecdf3d8036f7b7dd996a49f09c826c4c5c103a58c932b98fe04ec349f` | `255ca47ecdf3d8036f7b7dd996a49f09c826c4c5c103a58c932b98fe04ec349f` | MATCH |
| `stock-strategy-system/alert_runtime_state.json` | `5a4e611f3dcf2a7dde4b530400099f94134029289e856035a8410013f42e1355` | `5a4e611f3dcf2a7dde4b530400099f94134029289e856035a8410013f42e1355` | MATCH |

All other protected-state candidates and both activation manifests were absent before and after the Builder run.

## Materialization evidence

- First write: source bundle `CREATED`; candidate artifact `CREATED`.
- Rebuild: source bundle `ALREADY_PRESENT_VERIFIED`; candidate artifact `ALREADY_PRESENT_VERIFIED`.
- The candidate contains 160 common sessions and 7 common closures across 167 covered weekdays.
- Candidate creation did not create or modify an identity/calendar activation manifest and did not connect the candidate to the production resolver.
