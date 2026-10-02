# S7 CLI 쪽 형식 Builder 보고 (2026-10-02, K2)

- 지시문: `docs/claude/s7-cli-page-shape-builder-prompt-2026-10-02.md` 3절. worktree `s7-cli-page`, 기준 HEAD `6b0c10e`(지시문 커밋). 커밋하지 않았다.

## 바꾼 파일 (`git diff --stat`)

| 파일 | 변화 |
|---|---|
| `manage-us-stock-strategy/scripts/regular_session_close_history.py` | +7 / -1 (`parse_page`의 body 선택만) |
| `manage-us-stock-strategy/tests/test_regular_session_close_history.py` | +68 (새 테스트 5개와 도우미 2개, 기존 단언 무변경) |
| `manage-us-stock-strategy/references/portfolio-exposure-review.md` | +5 (Routine 1번, K0) |
| `docs/claude/s7-cli-page-shape-builder-report-2026-10-02.md` | 이 보고 (새 파일) |

## 구현

- 최상위 object에 `result`가 있고 `result_list`가 없으면 `result`를 body로 쓴다(MCP 형태, 기존과 같음).
- `result`가 없고 `result_list`가 있으면 그 object 자체를 body로 쓴다(CLI 원본 형태).
- 둘이 함께 있거나, 둘 다 없거나, 최상위가 object가 아니면 `PAGE_SHAPE_INVALID`.
- body 검사(비어 있지 않은 list, `return_code == 0`, 행 검사 전부)는 두 형태에 같다. page sha256은 파일 원시 바이트 그대로. 이력 구조·출력 키·스키마 무변경.

## 원시 sha256 전후

| 파일 | 전 | 후 |
|---|---|---|
| regular_session_close_history.py | 384232a3b5048ff5606ae8bcb91fe3444a0bb9a28939fbec44f0940c69b96083 | ac7a193cb53d43fed173e75a8ec29ae35e3f56350108c7eea20fab85bab17d23 |
| test_regular_session_close_history.py | e5d87ba37ade2328a725a683baf23c2254fe230b52c1ec4cf79a857ceba96712 | 0f58c664046ad0036097ad8cfe908950d2091fdeeed22e709e1a375582de3685 |
| portfolio-exposure-review.md | a847125f53839af862cea3e38884e8b361e06548851c63f030a7732503c1b3a2 | 2974143dfb47898803fa276db993220c9ee01226b8a7e649ed05ea179d4d7035 |

## 줄바꿈

세 파일 모두 CRLF 유지(순수 LF 줄 0, BOM 없음). 일괄 변환 없음.

## 테스트

- 고치기 전 새 테스트 5개: 모두 실패(FAIL 3, ERROR 2).
  - U1(`..._give_the_same_sessions_as_mcp_pages`, ERROR), U5(`test_mixed_mcp_and_cli_...`, ERROR), U2(`..._body_checks_match_the_mcp_form`, FAIL), U4(`..._reject_the_same_rows`, FAIL), U3(`..._both_wrapper_and_list_or_a_non_object_...`, FAIL).
- 고친 뒤 대상 테스트: `test_regular_session_close_history.py` 19 OK, `test_s7_calendar_binding.py` 10 OK, `test_run_portfolio_exposure_review.py` 17 OK, `test_portfolio_exposure_judge_fixes.py` 29 OK.
- 전체 테스트(서브에이전트): 기준선 2238개 → 실패 23 + 오류 291, 고유 ID 254. 변경 후 2243개(+5) → 같은 수, 고유 ID 254.
  - **새 실패 0.** 기준선에만 있는 ID도 0. ID 목록은 서로 동일하다.
  - 기준선 ID 목록은 스크래치 폴더 `baseline_failures.txt`, 변경 후는 `after_failures.txt`.

## 남은 문제

- 기존 실패 254개(주로 `test_portfolio_decision_dashboard` 151, `test_integrated_authority_snapshot` 38 등)는 이번 변경과 무관하게 이미 실패했다. 원인은 조사하지 않았다(오늘 날짜 2026-10-02 의존 가능성은 추측일 뿐).
- 기준선 전체 테스트는 파일 수정과 거의 동시에 시작됐다. 다만 기준선 개수가 2238이고 변경 후가 2243이라 새 테스트 5개 추가 전의 상태를 쓴 것이 확인된다.
- 실데이터 build(5.1)는 Cowork 몫이라 하지 않았다. 키움 도구 호출, 비밀 읽기, 커밋 없음.
