# Calendar Authority Bounded Refresh Builder Report

```text
[Temporal]

CURRENT_ET_DATETIME =
2026-08-29T01:11:49-04:00

CURRENT_ET_DATE =
2026-08-29

ACTIVE_CALENDAR_COVERAGE_START =
2026-01-01

ACTIVE_CALENDAR_COVERAGE_END =
2026-08-28

TARGET_COVERAGE_END =
2026-08-29

TARGET_SUFFICIENT_FOR_CURRENT_ET =
YES


[Production Baseline]

ACTIVE_IDENTITY =
d8b03aa434c969e8fba338865eb3e6567bc78821d9b7b702e47d7403f2bc5e60

ACTIVE_CALENDAR =
0553eb641cc932fd8fe9a00d910f5b782cb2459df5a75f556282ccee89ff772f

ACTIVE_COHORT =
identity-calendar-coordinated-activation-20260829T0948KST

ACTIVE_K2 =
f0bab7101b618a0598a6c4faf0c1feabd2b9e9617352df697d27f75df5267c25

ACTIVE_PROVIDER_SCOPE =
9604570d9fa1b21095bd03b2c3ca7aee4cd1ba12308ea3fff8c2829342befa29

SPLIT_AUTHORITY =
NO


[Calendar Evidence]

DATE =
2026-08-29

SESSION_CLASS =
NON_TRADING_DAY (SATURDAY / WEEKEND; RANGE-COVERED, NO EXPLICIT SESSION OR CLOSURE ROW)

SOURCE =
NYSE Holidays & Trading Hours — https://www.nyse.com/trade/hours-calendars
Nasdaq Trader U.S. Equity and Options Markets Holiday Schedule 2026 — https://www.nasdaqtrader.com/Trader.aspx?id=Calendar
Nasdaq Stock Market Holiday Schedule and Market Hours — https://www.nasdaq.com/market-activity/stock-market-holiday-schedule
Cboe U.S. Equities Hours & Holidays — https://www.cboe.com/about/hours/

SOURCE_TIMESTAMP =
2026-08-29 (DATE_ONLY_ET_FROM_RECORDED_REVIEW_WINDOW)

RETRIEVAL_TIMESTAMP =
2026-08-29T01:08:48-04:00

EVIDENCE_STATUS =
VERIFIED


[Historical Integrity]

HISTORICAL_ROW_COUNT_BEFORE =
172

HISTORICAL_ROW_COUNT_AFTER =
172

HISTORICAL_CHANGED_ROW_COUNT =
0

APPEND_ONLY =
YES


[Candidate]

CALENDAR_CANDIDATE_CREATED =
YES

CALENDAR_CANDIDATE_ID =
d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe

CALENDAR_CANDIDATE_RAW_SHA =
d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe

CALENDAR_CANDIDATE_PATH =
workspace/calendar-authority/artifacts/d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe/us-equities-core-session-v2.calendar.json

CALENDAR_CANDIDATE_STATUS =
INACTIVE

CANDIDATE_COVERAGE_START =
2026-01-01

CANDIDATE_COVERAGE_END =
2026-08-29

SOURCE_BUNDLE_ID =
US_EQUITIES_CORE_SESSION_2026_THROUGH_20260829_V1

SOURCE_BUNDLE_RAW_SHA =
cac93d52fa145f0b63092bde95122ba92c44b8c32f96bc61042a143ed177f24c

SOURCE_BUNDLE_PATH =
workspace/calendar-authority/source-bundles/cac93d52fa145f0b63092bde95122ba92c44b8c32f96bc61042a143ed177f24c/us-equities-core-session-v2.sources.json


[Validation]

SCHEMA_VALIDATION =
PASS

APPEND_ONLY_VALIDATION =
PASS

HISTORICAL_IMMUTABILITY_VALIDATION =
PASS

PROVENANCE_VALIDATION =
PASS

DETERMINISTIC_VALIDATION =
PASS

REPEAT_RESULT =
ALREADY_PRESENT_VERIFIED / SAME_ID

TEST_COUNT =
60

PASS_COUNT =
60

FAIL_COUNT =
0


[Authority Safety]

ACTIVE_IDENTITY_UNCHANGED =
YES

ACTIVE_CALENDAR_UNCHANGED =
YES

ACTIVE_COHORT_UNCHANGED =
YES

ACTIVE_K2_UNCHANGED =
YES

ACTIVATION_PERFORMED =
NO

WORKSPACE_POLICIES_MUTATION =
NO


[Operational Safety]

KIWOOM_QUOTE_REQUEST_COUNT =
0

ACCOUNT_REQUEST_COUNT =
0

GRADE_B_RUN_STARTED =
NO

PORTFOLIO_DECISION_RECALCULATED =
NO

ORDER_ENDPOINT_CALL_COUNT =
0

ORDERS =
NONE

ORDER_AUTHORITY =
false

EXECUTION_QUANTITY =
null


[Final]

CALENDAR_REFRESH_RESULT =
PASS

CALENDAR_CANDIDATE_READY =
YES

READY_FOR_ACTIVATION =
false

NEXT_ACTION =
INDEPENDENT_CALENDAR_JUDGE_REQUIRED
```

## Evidence and integrity notes

- The active production baseline matched every expected identifier before mutation. The active Identity and Calendar pointers are both `ACTIVE` and share the same activation cohort, so `SPLIT_AUTHORITY=NO`.
- The active Calendar artifact raw SHA-256 matches its hash-derived path and covers `2026-01-01 .. 2026-08-28`.
- The active K2 policy binds the acceptance manifest `f0bab7101b618a0598a6c4faf0c1feabd2b9e9617352df697d27f75df5267c25`; that manifest's raw SHA-256 matches its path and binds provider scope `9604570d9fa1b21095bd03b2c3ca7aee4cd1ba12308ea3fff8c2829342befa29`.
- The four official exchange pages were reviewed on `2026-08-29` ET. Nasdaq explicitly defines stock-market trading hours as Monday through Friday. The official 2026 NYSE, Nasdaq, and Cboe holiday calendars contain no special Saturday session for `2026-08-29`.
- Source page bytes were not persisted, so the canonical packet honestly retains `source_content_bytes_captured=NO` and `source_content_hash_status=NOT_CAPTURED`. URL, source family, MIC, scope, effective range, retrieval date, and exact ET review cutoff are retained.
- The existing Calendar schema stores weekday sessions and weekday holiday closures only. Saturday is represented semantically by the covered date range plus the deterministic weekday rule; adding a weekend closure row would violate the existing schema/materializer contract. Therefore the only append is `coverage_end: 2026-08-28 -> 2026-08-29`, with no explicit target-date row.
- All 172 historical material rows (165 sessions and 7 weekday closures) are byte-equivalent after canonical row serialization. `HISTORICAL_CHANGED_ROW_COUNT=0`.
- The official create-only materializer first returned `CREATED`, then returned `ALREADY_PRESENT_VERIFIED` for both the source bundle and candidate artifact. Candidate ID and raw SHA-256 are identical on repetition.
- Canonical unittest suites passed: `test_materialize_session_calendar_artifact.py` 19/19 and `test_session_authority.py` 41/41.
- Protected file SHA-256 values were identical before and after the builder run: Instrument Identity activation `db2ff8e2a90500084c352cb53be9ba915f9bb599b4f040d91fa3e7d75cd418fd`; Session Calendar activation `ad11e7517236e9ac843c6b9fae7bc0588493c9518a771e5fb2b68c70571802e3`; K2 policy `a3d2ae10c853af388758260746bc652472196c83571bc150c9d94a116ae114b2`; portfolio state `017225ec657c3fd3e6a6be7de9bb92296839411e98d74cb4627a4b0de605192a`.
- Candidate creation is not activation. No active pointer, policy, Identity/K2 artifact, Kiwoom runtime, account state, portfolio state, or order endpoint was mutated.
