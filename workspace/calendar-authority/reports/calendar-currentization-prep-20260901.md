# Calendar Authority 2026 Currentization Preparation

## Decision

`PARTIAL` — official 2026 exchange evidence is available and a schema-valid inactive candidate was materialized, but the candidate can cover only through `2026-09-01` under the unchanged canonical temporal contract. At the review cutoff (`2026-09-01T22:11:49-04:00`), `2026-09-02` was still a future America/New_York date. The current materializer rejects coverage beyond the ET date of `authority_as_of` with `TEMPORAL_VIOLATION`.

Do not activate this candidate as a remedy for the `2026-09-02` target session. A fresh reviewed packet and candidate with an honest ET cutoff on or after `2026-09-02` are required first.

## Repository and protected-state audit

- Repository: `E:\사업\##금동한\코덱스저장소`
- Branch: `codex/master-recovery-expansion`
- HEAD: `0026e79fc52468172f6b228333633077baf62556`
- The worktree was already dirty before this goal. `workspace/policies/session_calendar_activation.json` was already listed as modified, along with unrelated tracked and untracked work.
- Protected activation path: `E:\사업\##금동한\코덱스저장소\workspace\policies\session_calendar_activation.json`
- Protected activation SHA-256 before and after materialization: `ae67d222897998c234d265205d15441260a5da932cdee3958ad2866fe4981eaf`
- Materializer result: `activation_unchanged=true`
- No scheduler, production pointer, portfolio state, policy semantics, or broker state was changed.

## Active authority reference

- Active calendar path: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\artifacts\d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe\us-equities-core-session-v2.calendar.json`
- Active calendar SHA-256: `d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe`
- Active calendar version: `2026-08-29.1`
- Active coverage: `2026-01-01` through `2026-08-29`
- Active source-bundle SHA-256: `cac93d52fa145f0b63092bde95122ba92c44b8c32f96bc61042a143ed177f24c`
- Active source-bundle path: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\source-bundles\cac93d52fa145f0b63092bde95122ba92c44b8c32f96bc61042a143ed177f24c\us-equities-core-session-v2.sources.json`

## Official evidence inventory

The reviewed packet retains four official source identities required by the existing three-family/XNYS-XNAS-XCBO workflow. Source bytes were not captured, so the packet truthfully records `content_capture_status=NOT_CAPTURED` and `content_sha256=null`.

1. [NYSE Holidays & Trading Hours](https://www.nyse.com/trade/hours-calendars)
   - 2026 full closures include Labor Day on `2026-09-07`, Thanksgiving on `2026-11-26`, and Christmas on `2026-12-25`.
   - 2026 equity early closes are `2026-11-27` and `2026-12-24` at `13:00 ET`.
   - NYSE Core Trading Session is `09:30–16:00 ET`.
2. [Nasdaq Trader U.S. Equity and Options Markets Holiday Schedule 2026](https://www.nasdaqtrader.com/Trader.aspx?id=Calendar)
   - Confirms the same 2026 closures and `13:00 ET` early closes on `2026-11-27` and `2026-12-24`.
3. [Nasdaq Stock Market Holiday Schedule and Market Hours](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule)
   - Confirms the same holiday/early-close dates and regular `09:30–16:00 ET` hours.
4. [Cboe U.S. Equities Hours & Holidays](https://www.cboe.com/about/hours/)
   - Confirms the same 2026 U.S. equities closure/early-close dates and regular `09:30–16:00 ET` session.

Claim-specific conclusion: `2026-09-02` is a Wednesday, is absent from every official 2026 closure and early-close list above, precedes the `2026-09-07` Labor Day closure, and therefore follows the published regular `09:30–16:00 ET` session rule. This official-calendar conclusion does not override the repository's separate temporal gate.

## Reviewed packet and inactive candidate

- Reviewed packet: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\reviewed-inputs\us-equities-core-session-2026-through-20260901.reviewed.json`
- Reviewed packet SHA-256: `6430993e9810feaf2f33aa896de35a22f7b4d04d5ac85d45a3d8b6880023196d`
- Reviewed source bundle: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\source-bundles\c80036e0393edbbba6c0ce8a6481937ce1d9e06a6f8ab780076fc276e929c7e9\us-equities-core-session-v2.sources.json`
- Reviewed source-bundle SHA-256: `c80036e0393edbbba6c0ce8a6481937ce1d9e06a6f8ab780076fc276e929c7e9`
- Inactive candidate: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\artifacts\08028f5856f7f4866f966dfb7e61413944304351c71caa45ee6b5fb8c5a83f94\us-equities-core-session-v2.calendar.json`
- Candidate SHA-256: `08028f5856f7f4866f966dfb7e61413944304351c71caa45ee6b5fb8c5a83f94`
- Candidate calendar version: `2026-09-01.1`
- Candidate coverage: `2026-01-01` through `2026-09-01`
- Counts: 4 sources, 522 family-specific claims, 696 claim-source edges, 167 sessions, 7 closures.
- Materialization status: `MATERIALIZED_INACTIVE_CANDIDATE`; `ready_for_activation=false`.

## Validation results

- Reviewed-input/internal-schema dry run: `DRY_VALIDATED`.
- Source-bundle JSON Schema: valid during materialization.
- Candidate artifact JSON Schema: valid during materialization.
- Candidate semantic validator: valid during materialization.
- Content-address binding: candidate file SHA-256 equals its directory/hash identity.
- Full closures within candidate coverage: `2026-01-01`, `2026-01-19`, `2026-02-16`, `2026-04-03`, `2026-05-25`, `2026-06-19`, `2026-07-03`.
- Early closes within candidate coverage: none; this is correct because the official 2026 early closes occur after the candidate's allowed coverage end.
- Future early-close semantics: existing regression fixture materializes `2026-11-27 13:00 ET` as `close_type=EARLY`; this test passed without changing runtime semantics.
- Target-boundary negative check: changing only `coverage_end` to `2026-09-02` at the recorded cutoff returns `EXPECTED_FAIL_CLOSED / TEMPORAL_VIOLATION / coverage_end`.
- Regression command: `python -m unittest test_materialize_session_calendar_artifact test_session_authority test_manual_portfolio_analysis test_portfolio_decision_dashboard`
- Regression result: `Ran 186 tests in 2.826s — OK`.
- `pytest` was unavailable in the environment; the repository's unittest suite completed successfully.

## Independent Judge instructions

The Independent Judge must treat all artifacts and this report as untrusted input and perform these checks independently:

1. Record the protected activation SHA-256 and require it to remain `ae67d222897998c234d265205d15441260a5da932cdee3958ad2866fe4981eaf` throughout review.
2. Open the four official URLs above and independently confirm the 2026 regular hours, full closures, and early closes. Do not accept search snippets or an unofficial calendar as canonical evidence.
3. Recompute the reviewed packet SHA-256 and require `6430993e9810feaf2f33aa896de35a22f7b4d04d5ac85d45a3d8b6880023196d`.
4. Re-run `materialize_session_calendar_artifact.py --dry-run` and require candidate hash `08028f5856f7f4866f966dfb7e61413944304351c71caa45ee6b5fb8c5a83f94` and source-bundle hash `c80036e0393edbbba6c0ce8a6481937ce1d9e06a6f8ab780076fc276e929c7e9`.
5. Recompute both content-addressed file hashes and run the source-bundle schema, artifact schema, and semantic validator.
6. Re-run the 186 calendar/session-dependent tests.
7. Apply the target sufficiency gate: because `candidate.coverage_end=2026-09-01 < 2026-09-02`, verdict must be `DEFER_TARGET_CURRENTIZATION`. This candidate must not receive PROD-ACT approval as the remedy for the target session.
8. On or after `2026-09-02` ET, re-review the official sources, record a truthful new `authority_as_of`, create a fresh reviewed packet with `coverage_end >= 2026-09-02`, materialize new content-addressed hashes, and repeat steps 1–7.
9. Only after a target-sufficient candidate passes may the Judge issue a separate written PROD-ACT recommendation. User approval remains mandatory and is outside this goal.

## Exact future PROD-ACT mutation boundary — do not execute

No mutation is authorized now. The eventual separate PROD-ACT may modify only `workspace/policies/session_calendar_activation.json` and must atomically replace these bindings with values from the independently accepted target-sufficient candidate:

- `active_calendar_hash`
- `active_calendar_version`
- `coverage_start`
- `coverage_end`
- `source_bundle_id`
- `source_bundle_hash`
- `authority_as_of`
- `activated_at` using the actual approved activation time
- `activation_cohort_id` using the approved cohort identifier
- `activation_reason_code` = `CALENDAR_REFRESH`
- `activation_reason` describing the approved calendar refresh

The unchanged identity fields must remain exactly:

- `activation_schema_version` = `2.0`
- `activation_status` = `ACTIVE`
- `calendar_policy_identity` = `US_EQUITIES_CORE_SESSION_V2`
- `timezone_identity` = `America/New_York`
- `operating_mic_scope` = `["XNYS", "XNAS", "XCBO"]`
- `source_families` = `["NYSE_GROUP", "NASDAQ", "CBOE"]`
- `authority_modes_allowed` = `["CURRENT"]`

The present candidate's known bindings are not target-sufficient and therefore must not be used for the requested PROD-ACT: hash `08028f...a83f94`, version `2026-09-01.1`, coverage end `2026-09-01`, bundle hash `c80036...9c7e9`.

## Rollback and reference

Before any future activation, preserve the current activation bytes identified by SHA-256 `ae67d222897998c234d265205d15441260a5da932cdee3958ad2866fe4981eaf`. The current rollback/reference tuple is:

- Calendar hash: `d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe`
- Calendar version: `2026-08-29.1`
- Coverage end: `2026-08-29`
- Source-bundle hash: `cac93d52fa145f0b63092bde95122ba92c44b8c32f96bc61042a143ed177f24c`

Rollback must restore the exact preserved activation bytes, not reconstruct an approximate JSON object. After rollback, reload through the production loader and re-verify activation/artifact binding and both hashes.
