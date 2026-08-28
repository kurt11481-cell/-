# Calendar Authority Bounded Refresh Builder Report

```text
[Time]

CURRENT_ET_DATETIME =
2026-08-28T00:54:32-04:00

CURRENT_ET_DATE =
2026-08-28

TARGET_DATE =
2026-08-28


[Repository]

REPOSITORY =
E:\사업\##금동한\코덱스저장소

BRANCH =
codex/master-recovery-expansion

HEAD =
24560b7d3f673f97a98907e8c9b5a3e4e02687c1

PRE_WORKTREE_STATUS =
DIRTY (6 modified, 73 untracked; Git status blob SHA-1 3f38227e0d737725b355b3467a029992277bd674)

POST_WORKTREE_STATUS =
DIRTY (6 modified, 77 untracked; four intended new untracked artifacts)

INTENDED_NEW_ARTIFACTS =
workspace/calendar-authority/reviewed-inputs/us-equities-core-session-2026-through-20260828.reviewed.json
workspace/calendar-authority/source-bundles/6e156ee1facca818b32d7ad0d581de1b4c4a7f94af980a821b3ef6f10ee07015/us-equities-core-session-v2.sources.json
workspace/calendar-authority/artifacts/0553eb641cc932fd8fe9a00d910f5b782cb2459df5a75f556282ccee89ff772f/us-equities-core-session-v2.calendar.json
workspace/calendar-authority/reports/calendar-builder-20260828.md

UNRELATED_REPOSITORY_MUTATION =
NO

SOURCE_CHANGE =
NO


[Active Authority]

ACTIVE_IDENTITY_BEFORE =
502148a4fd4fa9f4b06365f0b02c630839315c79c8bfddcfac4addf7519261d6

ACTIVE_CALENDAR_BEFORE =
b201f6208e10fcd18efb0aa56906f60bdbaf20a053878f44b6780eae56467336

ACTIVE_CALENDAR_COVERAGE_BEFORE =
2026-01-01 .. 2026-08-27

ACTIVE_COHORT_BEFORE =
identity-calendar-coordinated-activation-20260828T1132KST

ACTIVE_K2_BEFORE =
2994192ec8e370607f60661758a69777b150d510fe841d759c936b24fea0e295

AUTHORITY_BASELINE_VALID =
YES


[Source Evidence]

SOURCE_EVIDENCE_READY =
YES

TARGET_DATE_SOURCE_SUPPORT =
PASS

SOURCE_TYPE =
REVIEWED_OFFICIAL_EXCHANGE_CALENDAR_METADATA_FROM_EXISTING_CANONICAL_EVIDENCE

SOURCE_IDENTITY =
US_EQUITIES_CORE_SESSION_2026_THROUGH_20260828_V1

SOURCE_TIMESTAMP =
2026-08-28T00:57:26-04:00

REVIEWED_INPUT =
workspace/calendar-authority/reviewed-inputs/us-equities-core-session-2026-through-20260828.reviewed.json

REVIEWED_INPUT_SHA256 =
0a44c6bf4965fb547c204dcb78bb35a9c069a1f17aea9b3b53bac6a89f94acbb

SOURCE_BUNDLE =
workspace/calendar-authority/source-bundles/6e156ee1facca818b32d7ad0d581de1b4c4a7f94af980a821b3ef6f10ee07015/us-equities-core-session-v2.sources.json

SOURCE_BUNDLE_SHA256 =
6e156ee1facca818b32d7ad0d581de1b4c4a7f94af980a821b3ef6f10ee07015

SOURCE_CONTENT_BYTES_CAPTURED =
NO

SOURCE_CONTENT_HASH_STATUS =
NOT_CAPTURED


[Candidate]

CANDIDATE_GENERATED =
YES

NEW_CALENDAR_CANDIDATE =
0553eb641cc932fd8fe9a00d910f5b782cb2459df5a75f556282ccee89ff772f

CANDIDATE_STATUS =
INACTIVE

CANDIDATE_COVERAGE_START =
2026-01-01

CANDIDATE_COVERAGE_END =
2026-08-28

TARGET_DATE_INCLUDED =
YES

TARGET_DATE_CLASSIFICATION =
2026-08-28 / REGULAR / 09:30:00-04:00 .. 16:00:00-04:00

CANDIDATE_PATH =
workspace/calendar-authority/artifacts/0553eb641cc932fd8fe9a00d910f5b782cb2459df5a75f556282ccee89ff772f/us-equities-core-session-v2.calendar.json

CANDIDATE_SHA256 =
0553eb641cc932fd8fe9a00d910f5b782cb2459df5a75f556282ccee89ff772f


[Validation]

SCHEMA_VALIDATION =
PASS

CANDIDATE_VALIDATION =
PASS

HISTORICAL_RANGE_CHECKED =
2026-01-01 .. 2026-08-27

HISTORICAL_CONTENT_UNCHANGED =
YES

HISTORICAL_SESSION_PREFIX_UNCHANGED =
YES

HISTORICAL_CLOSURE_CONTENT_UNCHANGED =
YES

TARGET_DATE_SOURCE_FAMILY_AGREEMENT =
NYSE_GROUP / NASDAQ / CBOE all REGULAR

DUPLICATE_OR_AMBIGUOUS_TARGET_END_CANDIDATES =
0 (exactly one candidate has coverage_end 2026-08-28)

SOURCE_BUNDLE_HASH_PATH_BINDING =
PASS

CANDIDATE_HASH_PATH_BINDING =
PASS

IDEMPOTENT_REBUILD =
PASS (ALREADY_PRESENT_VERIFIED)

ACTIVE_INACTIVE_SEPARATION =
PASS

READY_FOR_ACTIVATION =
false

TEST_COUNT =
60

PASS_COUNT =
60

FAIL_COUNT =
0

TEST_RESULT =
PASS


[Post-Builder Authority]

ACTIVE_IDENTITY_AFTER =
502148a4fd4fa9f4b06365f0b02c630839315c79c8bfddcfac4addf7519261d6

ACTIVE_CALENDAR_AFTER =
b201f6208e10fcd18efb0aa56906f60bdbaf20a053878f44b6780eae56467336

ACTIVE_CALENDAR_COVERAGE_AFTER =
2026-01-01 .. 2026-08-27

ACTIVE_COHORT_AFTER =
identity-calendar-coordinated-activation-20260828T1132KST

ACTIVE_K2_AFTER =
2994192ec8e370607f60661758a69777b150d510fe841d759c936b24fea0e295

ACTIVE_AUTHORITY_CHANGED =
NO


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


[Final]

BUILDER_RESULT =
PASS

NEXT_ACTION =
INDEPENDENT_CALENDAR_JUDGE_REQUIRED
```

## Evidence notes

- The four existing official source records retain their original `retrieved_date=2026-08-27`, official URLs, capabilities, and `effective_to=2026-12-31`. No network-derived fact or new source claim was introduced.
- The reviewed input records `authority_as_of_time_basis=EXACT_ET_EXISTING_CANONICAL_OFFICIAL_SOURCE_EVIDENCE_REVIEW_CUTOFF`; this distinguishes the local 8/28 review cutoff from the unchanged 8/27 source retrieval date.
- The official create-only materializer returned `MATERIALIZED_INACTIVE_CANDIDATE`, `activation_unchanged=true`, and `ready_for_activation=false`.
- A second create-only materialization returned `ALREADY_PRESENT_VERIFIED` for both the source bundle and candidate artifact.
- The target date is supported by three agreeing source-family claims: XNYS, XNAS, and XCBO all classify 2026-08-28 as a regular 09:30-16:00 ET session.
- The prior active Calendar session prefix and closure content are canonically identical. The only added common-session entry is 2026-08-28.
- Canonical unittest suites passed: `test_materialize_session_calendar_artifact.py` 19/19 and `test_session_authority.py` 41/41.
- After excluding the four intended paths, the post-worktree status hashes to the same Git blob SHA-1 as the pre-worktree status: `3f38227e0d737725b355b3467a029992277bd674`.
- Candidate is not activation. No Independent Judge, coordinated activation, Kiwoom acquisition, Grade B run, order, reconciliation, or portfolio mutation was performed.
