# Independent Judge Package: Calendar Authority 2026 Currentization Preparation

## Proposed judge disposition

`ACCEPT_INACTIVE_CANDIDATE_FOR_SEPARATE_PROD_ACT_REVIEW`

This package prepares a target-sufficient reviewed packet and inactive calendar candidate for `2026-09-02 America/New_York`. It does not activate the candidate and grants no scheduler, order, fill, portfolio, or policy authority.

## Review cutoff and repository state

- Official-source review cutoff: `2026-09-02T00:04:01-04:00`
- KST equivalent: `2026-09-02T13:04:01+09:00`
- Repository: `E:\사업\##금동한\코덱스저장소`
- Branch: `codex/master-recovery-expansion`
- Git commit: `0026e79fc52468172f6b228333633077baf62556`
- Worktree status: dirty before this resumed run; unrelated tracked and untracked changes were preserved.
- Protected activation path: `E:\사업\##금동한\코덱스저장소\workspace\policies\session_calendar_activation.json`
- Protected activation SHA-256 before and after candidate materialization: `ae67d222897998c234d265205d15441260a5da932cdee3958ad2866fe4981eaf`
- Materializer boundary result: `activation_unchanged=true`

## Current active authority and rollback reference

- Active artifact: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\artifacts\d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe\us-equities-core-session-v2.calendar.json`
- Active artifact SHA-256: `d6d1ecd2258554faf9b9d76f740bab9e7abcfe6ea5f84fd198e961fae74794fe`
- Active calendar version: `2026-08-29.1`
- Active coverage: `2026-01-01` through `2026-08-29`
- Active source-bundle SHA-256: `cac93d52fa145f0b63092bde95122ba92c44b8c32f96bc61042a143ed177f24c`
- Rollback activation-byte reference SHA-256: `ae67d222897998c234d265205d15441260a5da932cdee3958ad2866fe4981eaf`

Any future PROD-ACT must preserve the exact pre-activation bytes for rollback. Rollback must restore those bytes rather than reconstructing an approximate JSON object, then re-run the production loader and binding/hash checks.

## Newly reviewed official evidence

The official pages were opened and reviewed again after the temporal blocker cleared. No previous attempted packet or hash was treated as current evidence.

1. [NYSE Holidays & Trading Hours](https://www.nyse.com/trade/hours-calendars)
   - Core Trading Session: `09:30–16:00 ET`.
   - 2026 closures: `01-01`, `01-19`, `02-16`, `04-03`, `05-25`, `06-19`, `07-03`, `09-07`, `11-26`, `12-25`.
   - 2026 early closes: `11-27` and `12-24` at `13:00 ET`.
2. [Nasdaq Trader U.S. Equity and Options Markets Holiday Schedule 2026](https://www.nasdaqtrader.com/Trader.aspx?id=Calendar)
   - Confirms the same closure dates and `13:00 ET` early closes.
3. [Nasdaq Stock Market Holiday Schedule and Market Hours](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule)
   - Confirms the same annual dates and regular `09:30–16:00 ET` hours.
4. [Cboe U.S. Equities Hours & Holidays](https://www.cboe.com/about/hours/)
   - Confirms the same U.S. equities closure and early-close dates and regular `09:30–16:00 ET` hours.
5. [Cboe EDGX 2026 official rule filing](https://cdn.cboe.com/resources/regulation/rule_filings/pending/2026/CboeEDGX-2026-019.pdf)
   - Confirms regular trading hours on early-close days are `09:30–13:00 ET`.

Claim-specific conclusion: `2026-09-02` is a Wednesday, is absent from all official closure and early-close lists, and precedes the `2026-09-07` Labor Day closure. It is therefore a regular `09:30–16:00 ET` session.

Source bytes were not captured. The reviewed packet truthfully records `content_capture_status=NOT_CAPTURED` and `content_sha256=null`; direct official URLs, source identities, retrieval date, capabilities, and effective range are retained.

## Target-sufficient reviewed packet and inactive candidate

- Reviewed packet: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\reviewed-inputs\us-equities-core-session-2026-through-20260902.reviewed.json`
- Reviewed packet SHA-256: `2e63d304043f20e3ea1abcf831baaf4f75586aa63b924c7c9fd929942ec341ff`
- Reviewed source bundle: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\source-bundles\41e13e4fbc3d35a97adde99c5f953a7fd1f28cde25a09b9b986158906893eee5\us-equities-core-session-v2.sources.json`
- Reviewed source-bundle SHA-256: `41e13e4fbc3d35a97adde99c5f953a7fd1f28cde25a09b9b986158906893eee5`
- Inactive candidate: `E:\사업\##금동한\코덱스저장소\workspace\calendar-authority\artifacts\a8a3aef243c2be0abaa10b82663db383143f1fdd6c98e243b0663467d3bc7ed7\us-equities-core-session-v2.calendar.json`
- Candidate SHA-256: `a8a3aef243c2be0abaa10b82663db383143f1fdd6c98e243b0663467d3bc7ed7`
- Candidate calendar version: `2026-09-02.1`
- Candidate coverage: `2026-01-01` through `2026-09-02`
- Counts: 4 official sources, 525 family-specific claims, 700 claim-source edges, 168 sessions, 7 closures.
- Materialization status: `MATERIALIZED_INACTIVE_CANDIDATE`
- Activation readiness flag emitted by the preparation workflow: `ready_for_activation=false`, as expected before Independent Judge and explicit user approval.

## Coverage limitation

Annual coverage through `2026-12-31` was preferred but is not supported by the unchanged canonical temporal contract at this cutoff. The materializer requires `coverage_end <= authority_as_of` in America/New_York. A validation-only attempt with `coverage_end=2026-12-31` failed closed as `TEMPORAL_VIOLATION / coverage_end`.

No schema, validator, materializer, activation semantics, or calendar engine was changed to bypass this rule. The minimum target-sufficient existing form is therefore coverage through `2026-09-02`.

## Deterministic validation results

- Reviewed packet internal validation: `DRY_VALIDATED`.
- Source-bundle JSON Schema errors: `[]`.
- Candidate artifact JSON Schema errors: `[]`.
- Candidate semantic validation: `PASS`.
- Content-address binding: source bundle and candidate file hashes equal their directory/hash identities.
- Candidate coverage closures: `2026-01-01`, `2026-01-19`, `2026-02-16`, `2026-04-03`, `2026-05-25`, `2026-06-19`, `2026-07-03`.
- Candidate coverage early closes: none; the two official early closes occur after the permitted coverage end.
- Target row: `2026-09-02`, `REGULAR`, `09:30:00-04:00` through `16:00:00-04:00`.
- Existing early-close regression fixture materializes `2026-11-27` as `EARLY` with `13:00 ET`; it passed without changing runtime semantics.
- Regression command: `python -m unittest test_materialize_session_calendar_artifact test_session_authority test_manual_portfolio_analysis test_portfolio_decision_dashboard`
- Regression result: `Ran 186 tests in 2.879s — OK`.

## Independent Judge procedure

The Judge must treat this package and every artifact as untrusted input and independently:

1. Record the protected activation hash and require `ae67d222897998c234d265205d15441260a5da932cdee3958ad2866fe4981eaf` throughout review.
2. Open every official URL above and verify regular hours, all 2026 closure dates, both early-close dates, and the `13:00 ET` early-close time.
3. Verify that `2026-09-02` is a normal session and that the candidate target row exactly matches `09:30–16:00 ET`.
4. Recompute the reviewed packet SHA-256 and require `2e63d304043f20e3ea1abcf831baaf4f75586aa63b924c7c9fd929942ec341ff`.
5. Re-run the materializer dry run and require source-bundle hash `41e13e4fbc3d35a97adde99c5f953a7fd1f28cde25a09b9b986158906893eee5` and candidate hash `a8a3aef243c2be0abaa10b82663db383143f1fdd6c98e243b0663467d3bc7ed7`.
6. Run the source-bundle schema, artifact schema, semantic validator, content-address checks, and all 186 calendar/session-dependent tests.
7. Confirm `candidate.coverage_end >= 2026-09-02` and `candidate.coverage_start=2026-01-01`.
8. Confirm the candidate remains inactive and the production activation bytes are unchanged.
9. If every check passes, return `ACCEPT_INACTIVE_CANDIDATE_FOR_SEPARATE_PROD_ACT_REVIEW`; otherwise fail closed with the exact failing gate.
10. Do not perform PROD-ACT. A separate explicit user approval remains mandatory.

## Exact future PROD-ACT mutation — not authorized or executed

After Independent Judge acceptance and separate explicit user approval, a future PROD-ACT would atomically replace only the candidate-bound fields in `workspace/policies/session_calendar_activation.json` with:

- `active_calendar_hash`: `a8a3aef243c2be0abaa10b82663db383143f1fdd6c98e243b0663467d3bc7ed7`
- `active_calendar_version`: `2026-09-02.1`
- `coverage_start`: `2026-01-01`
- `coverage_end`: `2026-09-02`
- `source_bundle_id`: `US_EQUITIES_CORE_SESSION_2026_THROUGH_20260902_V1`
- `source_bundle_hash`: `41e13e4fbc3d35a97adde99c5f953a7fd1f28cde25a09b9b986158906893eee5`
- `authority_as_of`: `2026-09-02T00:04:01-04:00`
- `activation_reason_code`: `CALENDAR_REFRESH`
- `activation_reason`: an approved description of this calendar refresh
- `activated_at`: the actual approved PROD-ACT timestamp
- `activation_cohort_id`: the separately approved cohort identifier

These identity fields must remain unchanged: `activation_schema_version=2.0`, `activation_status=ACTIVE`, `calendar_policy_identity=US_EQUITIES_CORE_SESSION_V2`, `timezone_identity=America/New_York`, `operating_mic_scope=[XNYS,XNAS,XCBO]`, `source_families=[NYSE_GROUP,NASDAQ,CBOE]`, and `authority_modes_allowed=[CURRENT]`.

No part of this section authorizes that mutation.
