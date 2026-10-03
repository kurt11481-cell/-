# p-earn Builder 보고 — 실적 금지 구간 개정 구현 (2026-10-03, K3)

- 지시: `docs/claude/p-earn-builder-prompt-2026-10-03.md` 3절 상자. 범위: `docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md`(r1) 2~5절.
- 승인 근거: 사용자 승인(2026-10-03) "p-earn r1 승인: 확인된 미공지는 금지 구간 아님, 확인 못 함은 금지 유지, D2는 S7 2단계로 이관, J4 남은 위험(표시 전용) 수용".
- 실행: Claude Code, worktree `p-earn-impl`(브랜치 `worktree-p-earn-impl`, HEAD `906f765`; 브랜치 표기는 Judge 2 지적으로 Cowork가 K0 정정), Opus 5.5 · xhigh.
- 권한: `order_authority=false`, `quantity_authority=none`, `execution_quantity=null` 그대로. 키움 도구·네트워크·`.env`·비밀 접근 없음. **커밋하지 않음.**
- 상태: 구현 완료, Judge 2 대기.

## 결론

1. 확인된 미공지(`NOT_ANNOUNCED`, 정확히 이 문자열)는 7단계를 모두 통과할 때만 `(False, "EARNINGS_NOT_ANNOUNCED_CHECKED")`. 어느 단계에서 걸려도 금지다.
2. `VERIFIED` 경로(구간 계산·코드·순서)는 그대로다. 그 밖의 상태·기록 없음은 `EARNINGS_DATE_UNVERIFIED`로 계속 막는다.
3. 대상 테스트: 7개 파일 전부 통과, `test_v2_6_7_session_aware_kiwoom_priority.py`는 기준과 같은 14건 실패(새 실패 0). 스키마 감사 PASS. 전체 테스트 새 실패: 0(기준 314건과 ID 동일).
4. 의미 지문 전후 같음: `628c60818f3beeb255e28e28abd99677f4848f3833fe5a0c83c14e7d304011a0`.
5. `alert_policy.json` 키 경로 변경은 정확히 5개(`portfolio_exposure_policy` 안).

## 1. 0단계 기준 (고치기 전)

| 항목 | 결과 |
|---|---|
| a. blob (`git rev-parse HEAD:<경로>`) | 5개 모두 지시와 같음: `alert_policy.json` `0a40505…`, `portfolio_exposure.py` `87d2920…`, `run_portfolio_exposure_review.py` `4bef669…`, `test_portfolio_exposure.py` `0b5cbfb…`, `s5_exposure_fixtures.py` `60e62ed…`. 작업 트리 깨끗함 |
| a. "Token order" 절 | `references/portfolio-exposure-review.md:168`에 있음(변경 뒤 `:209`, 문구 무변경) |
| b. `semantic_fingerprint(<worktree 루트>)` | `628c60818f3beeb255e28e28abd99677f4848f3833fe5a0c83c14e7d304011a0` (integrated shadow 코호트 `628c6081…`와 같음) |
| c. 대상 테스트 기준 | `test_portfolio_exposure` 43 OK, `_display` 7 OK, `_fail_closed` 32 OK, `_judge_fixes` 29 OK, `test_run_portfolio_exposure_review` 22 OK, `test_s7_calendar_binding` 10 OK, `test_corporate_actions` 27 OK, `test_v2_6_7_session_aware_kiwoom_priority` 42개 중 **14 실패**(모두 "current Acceptance binding must resolve to exactly one manifest … matches=[]") |
| c. 전체 기준(서브에이전트 1회) | `Ran 2293 tests`, `FAILED (failures=23, errors=291, skipped=1)`, 실패·오류 ID 314건 |
| d. 새 테스트, 고치기 전 | 새 테스트 16개 **모두 실패**: `test_portfolio_exposure.py` 14개(서브테스트 포함 41항목: 실패 1·오류 40 — 오류는 새 키워드 인자 `TypeError`, 실패는 정책 계약), `test_run_portfolio_exposure_review.py` 2개(실패 2) |

기준 실패 314건의 원인(서브에이전트 분류, 이번 변경과 무관): ① `IntegratedAuthorityLoadError: INTEGRITY_FAILURE` 268건 ② Kiwoom Acceptance 바인딩 해시 불일치 29건 ③ Git 무시 대상 산출물 없음(`workspace/outputs/activation/…` 등) 8건, `pypdf` 미설치 1건, `test_sec_scheduled_shadow`의 PowerShell `Join-Path`·`SEC_ACCESS_BLOCKED` 5건, 신원 권한 2건, 대시보드 1건. ①②는 이 worktree가 `core.autocrlf=true`로 LF blob을 CRLF로 체크아웃해 원시 해시가 달라진 것으로 보인다(확인은 안 함).

## 2. 바꾼 파일

```
 docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md       |   1 +
 manage-us-stock-strategy/references/portfolio-exposure-review.md     |  43 ++-
 manage-us-stock-strategy/scripts/portfolio_exposure.py               | 107 +++++--
 manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py    |  13 +-
 manage-us-stock-strategy/tests/test_portfolio_exposure.py            | 291 ++++++++++
 manage-us-stock-strategy/tests/test_run_portfolio_exposure_review.py |  46 ++
 stock-strategy-system/alert_policy.json                              |   6 +-
 7 files changed, 488 insertions(+), 19 deletions(-)
```

- 새 파일: `docs/claude/p-earn-builder-report-2026-10-03.md`(이 보고, UTF-8·BOM 없음·LF, 미추적).
- 허용 목록 밖 파일은 바꾸지 않았다. `s5_exposure_fixtures.py`, `shadow_acceptance.py`, 스키마, `workspace/*`, `portfolio_state.json`, 키움 고정 스크립트, `deployment_gate` 무변경(`git diff --name-only`가 위 7개뿐). 두 스크립트는 키움 수락 매니페스트·`deployment_gate`(`alert_policy.json:30-51`) 고정 대상이 아니다(검색 0건).
- 참고: worktree의 `stock-strategy-system/portfolio_state.json`·`alert_runtime_state.json`(Git 무시)은 worktree 생성 때 복사된 것(수정 시각 08-12·10-02)이며 읽지도 고치지도 않았다.

## 3. 구현 (R1~R7)

| 요구 | 구현 |
|---|---|
| R1 | `portfolio_exposure.earnings_blackout(symbol, earnings, calendar_sessions, buy_session, *, evaluation_session=None, generated_at=None)`. 기록이 dict 아님 → `EARNINGS_DATE_UNVERIFIED`. `status == "NOT_ANNOUNCED"` → `_not_announced_check`(아래 7단계, 순서 그대로). `status != "VERIFIED"` → `EARNINGS_DATE_UNVERIFIED`. VERIFIED 본문은 한 줄도 바꾸지 않았다 |
| R1 1단계 | `buy_session`·`evaluation_session`이 `None`이거나 `calendar_sessions`에 없음 → `EARNINGS_WINDOW_NOT_CHECKABLE`. 달력에 있어도 날짜로 읽히지 않으면 같은 코드(실제 달력 값에서는 도달 불가, fail-closed 보강) |
| 2단계 | `"announcement_session" in record or "timing" in record` → `EARNINGS_RECORD_CONTRADICTORY`(값이 `null`이어도) |
| 3단계 | `source_kind` ∈ (`COMPANY_IR`, `COMPANY_PRESS_RELEASE`, `SEC_FILING`)(튜플, 해시 불가 값도 예외 없음), `source_url`은 str·`"https://"`로 시작·`urlsplit(url).hostname` 비어 있지 않고 공백 없음, `checked_at`은 오프셋 있는 ISO. 아니면 `EARNINGS_CHECK_SOURCE_INVALID` |
| 4단계 | `generated_at`이 str 아님·파싱 불가·오프셋 없음 → `EARNINGS_CHECK_GENERATED_AT_INVALID` |
| 5단계 | `checked_at > generated_at`(시각 비교) → `EARNINGS_CHECK_FUTURE_TIMESTAMP` |
| 6단계 | `checked_at < datetime.combine(평가 세션 날짜, 16:00, tzinfo=ZoneInfo("America/New_York"))` → `EARNINGS_CHECK_STALE`. 16:00 정각 통과. 조기 폐장일도 16:00 |
| 7단계 | `(False, "EARNINGS_NOT_ANNOUNCED_CHECKED")` |
| 파싱 | `_aware_timestamp`: str만, 끝 `"Z"`→`"+00:00"`(3.10 호환), `datetime.fromisoformat`, 잡는 예외는 `ValueError`·`TypeError`뿐이고 `None` → 해당 금지 코드. `_https_url_with_host`도 `ValueError`·`TypeError`만 잡아 `False`. 넓은 except·통과 기본값 없음. 모듈은 시계를 읽지 않는다 |
| R2 | `increase_blockers(..., evaluation_session=None, generated_at=None)` → 본 종목 판정과 MU→DRAM 대체 판정 모두 같은 인자. `build_exposure_review(..., generated_at=None)`의 `blockers()`가 자기 `evaluation_session`과 `generated_at`을 넘긴다 → add 경로와 제안 경로(`_evaluate_proposal`의 `blockers(symbol)`, 옛 `:1293`) 모두 적용. 기본 `None`이면 NOT_ANNOUNCED만 금지(`EARNINGS_WINDOW_NOT_CHECKABLE` 또는 `…GENERATED_AT_INVALID`), VERIFIED·기타는 전과 같다 |
| R3 | `run_portfolio_exposure_review.py`: `generated_at` 문자열을 한 번 만들어 `inputs["generated_at"]`과 `build_exposure_review(generated_at=...)`에 같은 값으로 넘김. `--earnings` 도움말에 VERIFIED·NOT_ANNOUNCED 형식 추가. 그 밖의 동작 무변경 |
| R4 | `alert_policy.json` 704줄 값 1개, 813줄 → 3줄(같은 위치·들여쓰기). 5절 참고 |
| R5 | `references/portfolio-exposure-review.md` 26줄 R3 문구 교체, "Corporate-action record" 절과 "Routine" 절 사이에 "Earnings blackout input (R3, p-earn r1)" 절(입력 형식, VERIFIED 구간 읽기 규칙, NOT_ANNOUNCED 7단계와 코드, 남은 위험). "Token order" 절 무변경 |
| R6 | S5 확정안 문서 10줄 제목 바로 아래 개정 메모 1줄. 본문 무변경 |
| R7 | 모듈 docstring(zoneinfo 조회 1줄, R3 개정 표시), `earnings_blackout`·`increase_blockers`·`build_exposure_review` docstring, 상수 주석. 새 의존성 없음(`zoneinfo`·`urllib.parse`는 표준 라이브러리, `tzdata`는 러너가 이미 씀) |

## 4. 파일별 sha256·줄바꿈

raw sha256은 이 worktree 작업 트리 바이트 기준(전 = 0단계 기록). 모든 대상 파일의 HEAD blob은 **LF(CR 0)**이고, 이 worktree는 시스템 gitconfig `core.autocrlf=true`라 작업 트리에서 CRLF로 보인다. 지시문 C1의 "CRLF"는 작업 트리 형식과 같다.

| 파일 | raw sha256 전 | raw sha256 후 | 작업 트리(후) | 커밋될 blob |
|---|---|---|---|---|
| `stock-strategy-system/alert_policy.json` | `8e0965147600b85bbab8879692c95ea5d53a57b92b5925928b754e47915dd17b` | `ebc8b8b28bf2620629ed8a8d2259761921d006060321162c9f0d85a5dc12f2c2` | CRLF 960줄, bare LF 0, BOM 없음 | `b593448f…` CR 0 |
| `manage-us-stock-strategy/scripts/portfolio_exposure.py` | `585803c220bfcf1dbef9282799e77dad0101a447f6a5cc3c8479f997073477fc` | `81130d05c8ab7a96d2368aa456a2224fb44ee998e9385257e4e28a683f17a75a` | CRLF 1471줄, bare LF 0, BOM 없음 | `9e8d0340…` CR 0 |
| `manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py` | `14a69b5bca15a82b1c114b38c261c77654d5f4cfdc722b713a40393d9fddd095` | `aa137f200371ccf4f0b53605a7aa2d6e0bd53c65226bf302c871e775fc95f0e8` | CRLF 494줄, bare LF 0, BOM 없음 | `2e46e2c3…` CR 0 |
| `manage-us-stock-strategy/tests/test_portfolio_exposure.py` | `3da8d3a35788bc609c87805d03622df0aedd097a012d6c5bfc43c5a8a6211b0c` | `6c739196dded1ed8d92620a6879661da2e4cff874c2455560db6792ba3254903` | CRLF 877줄, bare LF 0, BOM 없음 | `cc9c2e06…` CR 0 |
| `manage-us-stock-strategy/tests/test_run_portfolio_exposure_review.py` | `0116608366a4927d2c4baf25fe1b7e67868e085ca1db2af4072b4ec0981752d1` | `77d0acf0c09a50e6037675397cfeb63a325c2d09e664160b04c7aae0d372aeac` | CRLF 669줄, bare LF 0, BOM 없음 | `9267d4e3…` CR 0 |
| `manage-us-stock-strategy/references/portfolio-exposure-review.md` | `0ea1429e2e60772b87cf364db9f1787e5e63fa7dbea1de9c396abb1254563898` | `ad931fd49fb465735edeb90fc98202ccd3c82f0175bbed2cef57e055694d02dd` | CRLF 334줄, bare LF 0, BOM 없음 | `eeef00d9…` CR 0 |
| `docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md` | `4f0235c84056961ba8ca35164a7b6115eb5f1adebbe6dca9ae659a7d06b2ee56` | `6ace18abab7bdf571e4e9cbd8dac07e191367ec21f269bebe25d86d96d856021` | CRLF 851줄, bare LF 0, BOM 없음 | `32aadfa5…` CR 0 |

- 앞 4개 파일의 "전" 값 앞 16자는 수정안 기준표와 같다(`8e0965147600b85b`, `585803c220bfcf1d`, `3da8d3a35788bc60`, `0ea1429e2e60772b`).
- **S5 확정안 문서(지시문 C1·R6 "LF")**: 메인 체크아웃에서는 LF였으나(기준표 `4b1ebaddabd363f7`), 이 worktree에서는 같은 LF blob이 CRLF로 체크아웃됐다(raw `4f0235c8…`). 일괄 변환 금지 원칙에 따라 작업 파일 형식(CRLF)대로 1줄만 더했고 `git diff`는 1줄 추가뿐이다. 커밋될 blob은 LF(CR 0, `git hash-object` = LF 정규화 내용의 blob id). LF 기준 sha256: 전 `4b1ebaddabd363f7…`, 후 `17d2920832f138522683a659dce0bbc7614c297ea885b822f1d563a1336c2d04`.
- 나머지 파일의 LF 정규화 sha256(후): `alert_policy.json` `ba0ab8b99146565d…`, `portfolio_exposure.py` `e68ec6248757ec8c…`, `run_portfolio_exposure_review.py` `2736e7d475a2c2d8…`, `test_portfolio_exposure.py` `f0e46c59a99c2154…`, `test_run_portfolio_exposure_review.py` `5b95b787dfb2f172…`, `references/portfolio-exposure-review.md` `cd9debcc392847ce…`.

## 5. `alert_policy.json` 키 경로 diff (JSON을 경로로 펴서 비교)

| 종류 | 경로 | 전 | 후 |
|---|---|---|---|
| 값 변경 | `portfolio_exposure_policy.policy_version` | `2026-10-01-s5-r2` | `2026-10-03-s5-r2-p-earn` |
| 삭제 | `portfolio_exposure_policy.earnings_date_unverified` | `treat_as_blackout` | — |
| 추가 | `portfolio_exposure_policy.earnings_blackout_window_reading` | — | 수정안 3절 문구 그대로 |
| 추가 | `portfolio_exposure_policy.earnings_date_not_announced` | — | `not_a_blackout_only_with_official_check_after_evaluation_session_close` |
| 추가 | `portfolio_exposure_policy.earnings_check_missing_stale_or_unknown` | — | `treat_as_blackout` |

- 합계 5개. 줄 958 → 960(704줄 1줄 변경, 813줄 1줄 → 3줄). 다른 줄 바이트 무변경(줄 단위 재조립, CRLF).
- 무변경 확인: `portfolio_review_lines.policy_version`(834줄) `2026-10-01-s5-r2`, `holding_timing_rules` 전체(539줄 포함), `holding_risk_rules`, 최상위 `policy_version`·`strategy_version`, 권한 필드, `deployment_gate`. 새 세 키는 `earnings_blackout_ref`와 `blackout_substitution_prohibited` 사이(계약 테스트로 고정).
- `alert_policy.json` 원시 바이트가 바뀌었으므로 예약 런타임 배포 때 provenance manifest를 다시 만들어야 한다(수정안 6절, 관제판 `p-deploy`). 이 저장소 병합만으로는 예약 런타임에 영향 없음.

## 6. 의미 지문

| 시점 | `shadow_acceptance.semantic_fingerprint(<worktree 루트>)` |
|---|---|
| 0단계 b(고치기 전) | `628c60818f3beeb255e28e28abd99677f4848f3833fe5a0c83c14e7d304011a0` |
| 변경 뒤(정책 수정 직후, 보고 직전 두 번 계산) | `628c60818f3beeb255e28e28abd99677f4848f3833fe5a0c83c14e7d304011a0` |

- 같음. 바뀐 파일은 지문 경로 목록(`SEMANTIC_DEFAULTS`)에 없고, 지문이 읽는 `alert_policy.json` 부분(`strategy_version`·`holding_risk_rules`·`holding_timing_rules`·권한)은 무변경. `test_v2_6_7…test_provider_authority_change_starts_zero_count_cohort`(`:505-515`, 진행 파일 지문 = 현재 지문) 통과.

## 7. 테스트

새 테스트(수정안 5절 1~12번):

| 5절 | 테스트 |
|---|---|
| 1 | `NotAnnouncedEarningsTests.test_01_*`: 세 출처 종류, `Z`·`+00:00`·`-04:00`·소수 초, `checked_at == generated_at` 통과. MU·DRAM `blockers == []` |
| 2 | `test_02_*`(EDT, EVAL 2026-09-30: 19:59Z·19:59:59.999999Z·15:59:59-04:00 금지, 20:00Z·16:00-04:00 통과), `test_03_*`(EST: 승인 달력 아티팩트 `2421eeb7…`에서 2026-11-02 이후 첫 정규장 = 2026-11-02, `core_close_at` 16:00-05:00 확인. 20:00Z·20:59Z·16:30-04:00 금지 — 고정 −04:00 구현이면 실패, 21:00Z·16:00-05:00 통과. 추가: 조기 폐장일 2026-11-27(13:00 EST)도 20:59:59Z 금지·21:00Z 통과) |
| 3 | `test_04_*`: 미래 시각, 다른 오프셋 표기도 시각으로 비교 |
| 4 | `test_05_*`: 인자 생략·`None`·빈 값·파싱 불가·오프셋 없음·날짜만·소문자 `z`·숫자·`datetime` 객체 |
| 5 | `test_06_*`(서브테스트 28개): `checked_at` 오프셋 없음·파싱 불가·숫자·`null`·키 없음·빈 값·날짜만·소문자 `z`·리스트, `source_kind` 목록 밖·빈 값·`null`·키 없음·소문자·리스트, `source_url` 키 없음·`null`·빈 값·숫자·`http://`·`HTTPS://`·스킴 없음·`"https://"`·`https:///…`·`https://:443/…`·`https://user@/…`·공백 호스트·`https://[::1/…`(`urlsplit` `ValueError`) — 모두 예외 없이 `EARNINGS_CHECK_SOURCE_INVALID` |
| 6 | `test_07_*`: `announcement_session`·`timing` 키(값 `null` 포함) |
| 7 | `test_08_*`: buy·evaluation 세션 없음·주말·달력 밖. 새 인자 없이 부르면 MU `EARNINGS_WINDOW_NOT_CHECKABLE`, DRAM `BLACKOUT_SUBSTITUTION_PROHIBITED:MU` |
| (순서) | `test_09_*`: 1→2→3→4→5→6 단계 순서 |
| 8 | `test_10_*`: `not_announced`·대소문자 혼합·앞뒤 공백·`TBD`·`UNVERIFIED`·빈 값·`null`·status 키 없음, 기록 없음·`earnings=None`·`{}`·다른 종목만·문자열·리스트·`null` 기록 → `EARNINGS_DATE_UNVERIFIED`, DRAM `BLACKOUT_SUBSTITUTION_PROHIBITED:MU` |
| 9 | 기존 `EarningsBlackoutTests` 그대로 통과 + `test_11_*`: VERIFIED 오프셋 3·2·1·0·−1·−2 표, `timing` 없음·`null`·`DURING_MARKET`·`after_close`는 AFTER_CLOSE와 같은 끝 세션, BEFORE_OPEN 경계, 달력 밖. 새 인자(유효·`None`·쓰레기 값)를 줘도 결과가 옛 호출과 같음 |
| 10 | `test_12_*`: 디스크 정책 — 세 키 값·위치, `earnings_date_unverified` 없음, 두 `policy_version`, 539줄 문구 그대로 |
| 11 | `NotAnnouncedEarningsReviewTests.test_13_*`(MU ADD 카드: 통과 시 add `["MU"]`·실적 코드 없음, STALE·GENERATED_AT_INVALID·FUTURE 시 `omitted`, `generated_at` 없이 만든 리뷰는 GENERATED_AT_INVALID), `test_14_*`(제안 경로: `new_buy_within_band` MU DISPLAY / `EARNINGS_CHECK_STALE`, `swap_buy_leg` 매수 다리 DISPLAY / WITHHELD) |
| 11(러너) | `EarningsInputTests.test_generated_at_reaches_the_review_and_decides_a_not_announced_check`(러너가 넘긴 `generated_at` = 출력 `inputs.generated_at`, `--earnings` 파일로 통과·STALE·FUTURE), `test_earnings_help_shows_both_record_formats` |
| 12 | 6절(지문 전후 같음) + `test_v2_6_7…:505-515` 통과 |

대상 테스트(변경 뒤, 파일마다 `-p`):

| 파일 | 결과 |
|---|---|
| `test_portfolio_exposure.py` | Ran 57, OK (기존 43 + 새 14) |
| `test_portfolio_exposure_display.py` | Ran 7, OK |
| `test_portfolio_exposure_fail_closed.py` | Ran 32, OK |
| `test_portfolio_exposure_judge_fixes.py` | Ran 29, OK |
| `test_run_portfolio_exposure_review.py` | Ran 24, OK (기존 22 + 새 2) |
| `test_s7_calendar_binding.py` | Ran 10, OK |
| `test_corporate_actions.py` | Ran 27, OK |
| `test_v2_6_7_session_aware_kiwoom_priority.py` | Ran 42, FAILED (failures=14) — 0단계 기준 14건과 ID가 정확히 같음(새 실패 0) |
| `validate_schema_contracts.py` | `{"status": "PASS", "errors": []}` |

전체(서브에이전트 1회): `Ran 2309 tests`(기준 2293 + 새 16), `FAILED (failures=23, errors=291, skipped=1)`. 실패·오류 ID 314건이 0단계 목록과 정확히 같다 — **새 실패 0**, 사라진 실패 0. 실행 중 생긴 임시 sqlite 파일(`tests/.test-only-scheduler-*.sqlite3`)은 테스트가 스스로 지웠다.

## 8. 지시와 다르게 하거나 판단한 점

1. S5 문서 줄바꿈: 4절 참고. 지시문은 LF라 했으나 이 worktree 작업 트리는 CRLF(같은 LF blob). 작업 파일 형식을 따랐고 커밋될 blob은 LF다.
2. S5 메모의 줄 번호: 수정안 4절 문구의 `:34`·`:397`·`:574`·`:579`는 메모를 넣기 전 번호다. 메모 1줄이 들어가 1씩 밀리므로 메모에는 `:35`·`:398`·`:575`·`:580`을 쓰고 괄호에 원래 번호를 적었다(네 줄 내용은 삽입 스크립트에서 확인).
3. `source_url` 호스트: "비어 있지 않음"에 더해 공백이 든 호스트(`"https:// /x"`)도 무효로 했다(fail-closed 방향).
4. 평가 세션이 달력에 있으나 날짜로 읽히지 않는 경우를 1단계 코드(`EARNINGS_WINDOW_NOT_CHECKABLE`)로 보냈다(fail-closed 방향, 실제 달력에서는 도달 불가).
5. 테스트 도우미: 기존 `Scenario`는 고치지 않고 테스트 파일 안에 하위 클래스 `CheckedScenario`(리뷰에 `generated_at` 전달)와 `checked_record()`를 두었다. 테스트 파일 import 2줄(`json`, `datetime`·`timezone`) 추가. 기존 단언 무변경(두 테스트 파일 diff는 추가만).
6. 5절 2번 "달력에서 고름": 테스트가 승인 달력 아티팩트(`workspace/calendar-authority/artifacts/2421eeb7…/us-equities-core-session-v2.calendar.json`, 러너 테스트가 이미 쓰는 파일)를 읽어 EST 세션을 고른다.

## 9. 남은 문제 (Judge 2 확인 요청)

1. **NOT_ANNOUNCED 기록의 다른 키는 무시된다.** 2단계는 지시대로 `announcement_session`·`timing` 두 키만 모순으로 본다. 예를 들어 오타 키 `"announcement_date"`가 있는 NOT_ANNOUNCED 기록은 나머지 조건을 채우면 통과한다(통과 조건 자체는 허용 목록). 더 막을지는 Judge 판단.
2. **buy_session과 evaluation_session의 인접성은 함수가 확인하지 않는다.** `build_exposure_review`는 늘 평가 세션 다음 달력 세션을 매수 세션으로 넘기므로 실제 경로에서는 성립한다. 직접 호출(테스트 등)에서는 임의 조합이 가능하다.
3. `tzdata`가 없는 환경이면 `ZoneInfoNotFoundError`(KeyError 계열)로 NOT_ANNOUNCED 판정이 실패하고 러너는 `FAIL`(exit 2)로 끝난다. 조용히 통과하지는 않는다. 사용자 PC는 Python 3.13.15 + tzdata 2026.3, 러너가 이미 같은 `ZoneInfo`를 쓴다.
4. Python 3.10의 `fromisoformat`은 3.11+보다 받는 형식이 좁다. 3.10에서는 일부 형식이 `EARNINGS_CHECK_SOURCE_INVALID`로 막힌다(막는 쪽). 소문자 `z`는 3.13에서도 거부돼 버전 간 차이 없음.
5. `--earnings` 파일의 `"earnings"`가 dict가 아니면(예: 리스트) 기존처럼 `AttributeError`로 러너가 끝난다(기존 동작, 범위 밖).
6. J4 남은 위험(확인 뒤 공지 + 2세션 안 발표)은 승인 때 수용됨. 참조 문서 새 절에 적었다.
7. 수정안 7절 F1~F7(옛 경로, 2027 달력, 생성기, VERIFIED 출처 요구, D2, v3.8 ① 칸, MU·NBIS 리드타임)은 범위 밖 그대로.

## 10. 자기 점검

fail-open 6종(Partial·Stale·Missing·Unknown·Deny-list·Swallowed)을 새 결정 경로마다 대어 봤다: **예**(아래).

| 결정 경로 | Partial | Stale | Missing | Unknown | Deny-list | Swallowed |
|---|---|---|---|---|---|---|
| 상태 분기(dict·VERIFIED·NOT_ANNOUNCED·기타) | 일부 종목만 있는 파일 → 없는 종목 UNVERIFIED | VERIFIED 지난 날짜 STALE(유지) | 파일·기록·status 없음 → UNVERIFIED | 소문자·공백·다른 값 → UNVERIFIED | 통과는 정확한 문자열 두 개뿐(허용 목록) | 예외 없음 |
| NOT_ANNOUNCED 7단계 | 필드 일부 없음 → SOURCE_INVALID, `generated_at` 없음 → GENERATED_AT_INVALID | 평가 세션 16:00 ET 전 확인 → STALE, 미래 → FUTURE | 세션 없음 → NOT_CHECKABLE | 목록 밖 출처·스킴 → SOURCE_INVALID | 출처·스킴은 허용 목록. 모순 키 2개는 추가 차단이며 다른 키는 무시(9절 1번) | `ValueError`·`TypeError`만 잡아 금지 코드로, 넓은 except 없음, `ZoneInfo` 실패는 위로 올라감 |
| `increase_blockers`·MU→DRAM | 같은 인자를 두 판정에 모두 전달 | 같음 | 기본 `None` → NOT_ANNOUNCED 금지 | MU가 어떤 이유로든 금지면 DRAM 금지 | 해당 없음 | 해당 없음 |
| `build_exposure_review`(add·제안) | 자기 `evaluation_session` 전달(매수 세션에서 추정 안 함) | 같음 | `generated_at` 없으면 금지 | 해당 없음 | 해당 없음 | 해당 없음 |
| 러너 `generated_at` | 출력과 같은 문자열 전달(테스트로 고정) | 실행 시각(`--now`면 그 값, 기존처럼 비표준 입력 표시) | 해당 없음 | 해당 없음 | 해당 없음 | 기존 예외 처리 무변경 |

## 11. 다음 (지시문 5절)

1. Cowork: worktree 읽기 전용 확인(git status·diff --stat, 허용 목록, 금지 파일 무변경, 줄바꿈, 키 경로 diff, 대상 테스트 재실행).
2. Cowork: Judge 2 지시문 → 사용자가 별도 세션에서 실행.
3. Judge 2 PASS → 사용자 커밋·병합(Windows 터미널).
