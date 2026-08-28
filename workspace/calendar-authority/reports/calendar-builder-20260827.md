# Calendar Authority Bounded Refresh Builder Report

```text
[Repository]

REPOSITORY =
E:\사업\##금동한\코덱스저장소

BRANCH =
codex/master-recovery-expansion

HEAD =
24560b7d3f673f97a98907e8c9b5a3e4e02687c1

PRE_WORKTREE_STATUS =
DIRTY (6 modified, 69 untracked)

POST_WORKTREE_STATUS =
DIRTY (6 modified, 73 untracked)

INTENDED_NEW_UNTRACKED_PATHS =
workspace/calendar-authority/reviewed-inputs/us-equities-core-session-2026-through-20260827.reviewed.json
workspace/calendar-authority/source-bundles/7573ddcf589c67792e40a63939e02ba4c2b890c1c9cfa4f00a18540ec64e9440/us-equities-core-session-v2.sources.json
workspace/calendar-authority/artifacts/b201f6208e10fcd18efb0aa56906f60bdbaf20a053878f44b6780eae56467336/us-equities-core-session-v2.calendar.json
workspace/calendar-authority/reports/calendar-builder-20260827.md

UNRELATED_REPOSITORY_MUTATION =
NO

SOURCE_CHANGE =
NO


[Existing Lifecycle]

CALENDAR_MATERIALIZER =
manage-us-stock-strategy/scripts/materialize_session_calendar_artifact.py

CALENDAR_VALIDATOR =
materialize_session_calendar_artifact.py --dry-run
+ validation_common.validate_instance
+ session_calendar_artifact._semantic_validate_artifact

CANDIDATE_SCHEMA =
manage-us-stock-strategy/schemas/session-calendar-artifact.schema.json

SOURCE_BUNDLE_SCHEMA =
manage-us-stock-strategy/schemas/session-calendar-source-bundle.schema.json

EXISTING_LIFECYCLE_REUSED =
YES

NEW_STATE_OR_ENGINE =
NO


[Current Active Authority]

ACTIVE_IDENTITY =
502148a4fd4fa9f4b06365f0b02c630839315c79c8bfddcfac4addf7519261d6

ACTIVE_CALENDAR =
fa1ce8ae37e065f54158ae3f70e9d05672f51a8d202d7ec51c95939f7af74d17

ACTIVE_K2_ACCEPTANCE =
2994192ec8e370607f60661758a69777b150d510fe841d759c936b24fea0e295

ACTIVE_AUTHORITY_CHANGED =
NO


[Calendar Candidate]

OLD_ACTIVE_CALENDAR =
fa1ce8ae37e065f54158ae3f70e9d05672f51a8d202d7ec51c95939f7af74d17

OLD_COVERAGE =
2026-01-01 .. 2026-08-26

NEW_CALENDAR_CANDIDATE =
b201f6208e10fcd18efb0aa56906f60bdbaf20a053878f44b6780eae56467336

CANDIDATE_STATUS =
INACTIVE

CANDIDATE_COVERAGE_START =
2026-01-01

CANDIDATE_COVERAGE_END =
2026-08-27

TARGET_DATE_INCLUDED =
YES

CANDIDATE_MANIFEST_PATH =
workspace/calendar-authority/artifacts/b201f6208e10fcd18efb0aa56906f60bdbaf20a053878f44b6780eae56467336/us-equities-core-session-v2.calendar.json

CANDIDATE_SHA256 =
b201f6208e10fcd18efb0aa56906f60bdbaf20a053878f44b6780eae56467336


[Provenance]

SOURCE_TYPE =
REVIEWED_OFFICIAL_EXCHANGE_CALENDAR_METADATA

SOURCE_IDENTITY =
US_EQUITIES_CORE_SESSION_2026_THROUGH_20260827_V1

SOURCE_IDS =
NYSE_HOURS_CALENDAR_2026
NASDAQ_TRADER_CALENDAR_2026
NASDAQ_MARKET_HOURS_2026
CBOE_US_EQUITIES_HOURS_2026

SOURCE_TIMESTAMP =
2026-08-27T19:34:38-04:00

SOURCE_CONTENT_BYTES_CAPTURED =
NO

SOURCE_CONTENT_HASH_STATUS =
NOT_CAPTURED

MATERIALIZATION_METHOD =
EXISTING_CREATE_ONLY_CONTENT_ADDRESSED_SESSION_CALENDAR_MATERIALIZER

SOURCE_BUNDLE_PATH =
workspace/calendar-authority/source-bundles/7573ddcf589c67792e40a63939e02ba4c2b890c1c9cfa4f00a18540ec64e9440/us-equities-core-session-v2.sources.json

SOURCE_BUNDLE_SHA256 =
7573ddcf589c67792e40a63939e02ba4c2b890c1c9cfa4f00a18540ec64e9440


[Validation]

CANDIDATE_VALIDATION =
PASS

SCHEMA_CONTRACT_VALIDATION =
PASS

MATERIALIZER_TESTS =
19 / 19 PASS

SESSION_AUTHORITY_TESTS =
41 / 41 PASS

IDEMPOTENT_REBUILD =
PASS (ALREADY_PRESENT_VERIFIED)

HASH_PATH_BINDING =
PASS

DATE_CONTINUITY =
PASS

HISTORICAL_SESSION_PREFIX_UNCHANGED =
PASS

HISTORICAL_CLOSURE_PREFIX_UNCHANGED =
PASS

TARGET_DATE_CLASSIFICATION =
2026-08-27 / REGULAR / 09:30:00-04:00 .. 16:00:00-04:00

DUPLICATE_OR_AMBIGUOUS_TARGET_END_CANDIDATES =
0 (exactly one candidate has coverage_end 2026-08-27)

IDENTITY_CALENDAR_COMPATIBILITY =
PASS

SUPPORTED_PORTFOLIO_MIC_BINDING =
MVLL=XNAS
NBIS=XNAS
SOXL=XNYS

COHORT_REQUIREMENT =
NEW_COORDINATED_IDENTITY_CALENDAR_ACTIVATION_COHORT_REQUIRED_BEFORE_ACTIVATION

ACTIVATION_READY =
NO


[Authority Firewall Fingerprints]

INSTRUMENT_IDENTITY_ACTIVATION_SHA256_BEFORE_AFTER =
c8396d4ed8789e7e2ae08e4ac517c2477afca1b0e8d555606c16f7ec596a838e / MATCH

SESSION_CALENDAR_ACTIVATION_SHA256_BEFORE_AFTER =
4ca2d231d82b416f28fc2c98f6fc93dcdd645f0a7393f47334d14eb9e30a2e8b / MATCH

KIWOOM_PRIORITY_POLICY_SHA256_BEFORE_AFTER =
53dd98717cf453d6120468a3430a9e98eab0f7c63ee87525dde8c5974c66eb0e / MATCH

PORTFOLIO_STATE_SHA256_BEFORE_AFTER =
017225ec657c3fd3e6a6be7de9bb92296839411e98d74cb4627a4b0de605192a / MATCH

ALERT_POLICY_SHA256_BEFORE_AFTER =
255ca47ecdf3d8036f7b7dd996a49f09c826c4c5c103a58c932b98fe04ec349f / MATCH

ALERT_RUNTIME_STATE_SHA256_BEFORE_AFTER =
5a4e611f3dcf2a7dde4b530400099f94134029289e856035a8410013f42e1355 / MATCH


[Operational Safety]

KIWOOM_ACQUISITION_COUNT =
0

GRADE_B_RUN_STARTED =
NO

OFFICIAL_RUNNER_INVOCATION_COUNT =
0

ORDERS =
NONE

HOLDINGS_MUTATION =
NO

AVERAGE_COST_MUTATION =
NO

SYSTEM_PORTFOLIO_MUTATION =
NO

ORDER_AUTHORITY =
false

QUANTITY_AUTHORITY =
none

EXECUTION_QUANTITY =
null


[Builder Verdict]

BUILDER_RESULT =
PASS

NEXT_ACTION =
INDEPENDENT_CALENDAR_JUDGE_REQUIRED
```

## Evidence notes

- The candidate is inactive because the production activation manifest still points to `fa1ce8ae37e065f54158ae3f70e9d05672f51a8d202d7ec51c95939f7af74d17`; the materializer also returned `ready_for_activation=false`.
- The existing active Calendar and Identity activation manifests share `identity-calendar-coordinated-activation-20260826T2102KST`. The production orchestration contract requires those cohort identifiers to match. A later activation therefore requires a new coordinated cohort step; this Builder did not perform it.
- Official source URLs and reviewed metadata were retained through the existing provenance contract. Publisher content bytes were not captured, so no publisher-content hash is claimed.
- The first test attempt exposed an unwritable default system temporary directory. The Calendar test suites were rerun with `TEMP` and `TMP` scoped to a disposable directory under `workspace/calendar-authority`; all 60 applicable tests passed. That empty temporary directory was deleted separately after a narrowly scoped user approval.
- `pytest` was unavailable, so the repository's `unittest` suites were used directly.

Candidate is not activation. No Grade B run, Kiwoom acquisition, order, reconciliation, or portfolio mutation occurred.
