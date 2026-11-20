# llm-newsdiag Builder 보고 — 뉴스 시범 기사 가져오기 실패 원인 남기기(진단만)

- 지시문: docs/claude/llm-newsdiag-builder-prompt.md · 작성 2026-11-19 · Builder(파이프라인, 커밋 없음)
- 바꾼 파일 3개: `manage-us-stock-strategy/scripts/llm_pilot_news.py`(CRLF 유지) · `manage-us-stock-strategy/tests/test_llm_pilot_news.py`(CRLF 유지, 새 시험만 더함) · 이 보고(LF, 새 파일)
- 권한 표지 4종 줄 변경 없음. 키움 호출·키 값 읽기·정책·상태·일지 쓰기 없음. 저장소 루트에 대고 스크립트를 돌리지 않음.

## (a) 바꾼 함수와 새 파일 모양

`manage-us-stock-strategy/scripts/llm_pilot_news.py`

| 행 | 이름 | 내용 |
|---|---|---|
| 64-65 | `ERROR_MESSAGE_MAX_CHARS = 200`, `ERROR_TYPE_MAX_CHARS = 80` | 정리 길이 상한 |
| 68 | `FETCH_ERRORS_SCHEMA = "llm-news-fetch-errors-1"` | 새 파일 schema |
| 306 | `_printable_ascii` (새) | 0x20~0x7E 밖 글자 → `?` |
| 310 | `_clean_error_message` (새) | `str(exc)` → (1) `_URL`로 주소 → `[url]` (2) `\r`·`\n`·`\t` → 공백 (3) 인쇄 가능 ASCII 밖 → `?` (4) 앞 200자. 도중 예외면 빈 글 |
| 321 | `_clean_type_name` (새) | type 칸에 (3) 적용, 80자 자름 |
| 325 | `fetch_items_detail(symbol, fetcher=None)` (새) | 성공 `(list(raw), None)` · 예외 `(None, {"symbol","kind":"exception","type","message"})` · 목록 아님 `(None, {...,"kind":"not_list","type":type(raw).__name__,"message":""})`. `except Exception`만 — `KeyboardInterrupt`·`SystemExit`는 잡지 않음(전과 같은 범위) |
| 351 | `fetch_items` (고침) | `fetch_items_detail(...)[0]`만 돌려줌. 시그니처·반환 그대로 |
| 356 | `fetch_errors_path` (새) | `news/<날짜>/fetch-errors.json` |
| 360 | `_write_fetch_errors` (새) | `atomic_write_text`, UTF-8, `ensure_ascii=True`, `sort_keys=True`. `OSError`는 삼키고 남은 `.tmp`를 지워 봄 |
| 382 | `_remove_fetch_errors` (새) | 남아 있는 파일 지우기, `OSError` 삼킴 |
| 521-543 | `run_submit` 6단계 (고침) | `fetch_items_detail` 사용, 실패를 사전 등록 `universe` 순서로 모음. dry run이 아니면 실패 ≥1 → 쓰기(덮어쓰기), 실패 0 → 지우기. 모두 실패면 `failed.md` 사유 = `REASON_KO["fetch_failed"] + " [" + 첫 실패 symbol + " " + type + "]"` |

새 파일 `workspace/outputs/llm/news/<날짜>/fetch-errors.json` 모양:

```json
{
 "day": "2026-11-18",
 "errors": [
  {"kind": "exception", "message": "rate limited [url] more", "symbol": "MRVL", "type": "YFRateLimitError"},
  {"kind": "not_list", "message": "", "symbol": "AMD", "type": "NoneType"}
 ],
 "schema": "llm-news-fetch-errors-1",
 "symbols_failed": 2,
 "symbols_total": 30,
 "written_kst": "2026-11-18T19:30:00+09:00"
}
```

(값은 보기용. 성공 종목은 넣지 않음. 같은 날 다시 불리면 가장 최근 시도로 덮어씀.)

모두 실패한 날 `failed.md` 한 줄: `검토 못 함: 기사 가져오기 실패 [MRVL YFRateLimitError] (FETCH_FAILED)`

## (b) 새 시험 (test_llm_pilot_news.py에 더함, 기존 시험 무수정)

| 행 | 시험 | 단언 요약 |
|---|---|---|
| 532 | `test_fetch_items_detail_exception` | `RuntimeError("rate limited https://x.example/a?b=1\nmore")` → kind exception, type RuntimeError, 메시지 = `rate limited [url] more`(주소·https 없음, `\r\n\t` 없음, ≤200자), 키 4개뿐. 목록·튜플 성공은 `(list, None)` |
| 551 | `test_fetch_items_detail_not_list` | `{"a": 1}` → `{"symbol":"MU","kind":"not_list","type":"dict","message":""}`; `None` → type NoneType |
| 559 | `test_fetch_items_detail_non_ascii_and_long` | 한글·탭·500자 → `?? x...`, 정확히 200자, 전부 인쇄 가능 ASCII. 긴 비ASCII 예외 이름 → type 80자, `?` 치환. `__str__`이 예외를 내면 메시지 빈 글 |
| 578 | `test_fetch_items_detail_keeps_interrupts` | `KeyboardInterrupt`·`SystemExit`가 그대로 올라옴 (지시문 목록 밖 추가 시험 — Judge 항목 5 확인용) |
| 586 | `test_all_fetches_failed_writes_errors` | 30종목 예외 → (11, FETCH_FAILED), 줄 `... FETCH_FAILED symbols_failed=30` 그대로, 호출 없음. 파일 30건 universe 순서, schema·day·written_kst·symbols_total 30, 파일 바이트 ASCII. `failed.md` = `검토 못 함: 기사 가져오기 실패 [<첫 symbol> RuntimeError] (FETCH_FAILED)` |
| 607 | `test_some_fetches_failed_writes_errors` | AMD(None)·TSM(예외) 실패 → SUBMITTED 줄·counts 그대로, 파일 2건 universe 순서, 각 dict 값 고정, `failed.md` 없음 |
| 626 | `test_dry_run_writes_no_fetch_errors` | dry run 일부 실패·모두 실패 둘 다 `workspace` 폴더 자체가 안 생김 |
| 638 | `test_no_fetch_errors_file_when_all_ok` | 실패 0 → 파일 없음 |
| 642 | `test_stale_fetch_errors_removed_when_retry_ok` | FETCH_FAILED 뒤 같은 날 성공 제출 → 파일·`failed.md` 지워짐, 줄 그대로 |
| 652 | `test_fetch_errors_overwritten_by_latest_attempt` | 같은 날 두 번 실패 → 두 번째 시도의 written_kst·type으로 덮어씀, `failed.md`도 최신 type (지시문 3-39줄 확인용 추가 시험) |
| 664 | `test_fetch_errors_write_oserror_does_not_change_outcome` | 같은 이름 폴더를 미리 만들어 쓰기 `OSError` → 줄·코드·counts 그대로, `.tmp` 안 남음. 지우기 `OSError`(실패 0인 날)도 줄·코드 그대로 |

기존 시험(356행 `test_fetch_items_failure_is_none`, 511행 `test_all_fetches_failed`, 520행 `test_some_fetches_failed_are_counted`, `REASON_KO` 고정 시험, dry run 시험, `test_script_source_contract`, `test_no_key_value_and_writes_under_llm_only` 등)은 한 줄도 고치지 않았고 모두 통과.

## (c) 시험 결과 · diff stat

`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_news*.py"` 마지막 3줄:

```
----------------------------------------------------------------------
Ran 61 tests in 0.819s

OK
```

스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`: `"status": "PASS"`, `"errors": []`.

`git diff --stat` (보고 파일은 새 파일이라 미추적, 목록에 없음):

```
 manage-us-stock-strategy/scripts/llm_pilot_news.py | 105 ++++++++++++--
 .../tests/test_llm_pilot_news.py                   | 154 +++++++++++++++++++++
 2 files changed, 251 insertions(+), 8 deletions(-)
```

`git diff --ignore-cr-at-eol --stat`:

```
 manage-us-stock-strategy/scripts/llm_pilot_news.py | 105 ++++++++++++--
 .../tests/test_llm_pilot_news.py                   | 154 +++++++++++++++++++++
 2 files changed, 251 insertions(+), 8 deletions(-)
```

두 숫자가 같다 — 줄바꿈 전체 변환 없음(두 기존 파일 CRLF 유지).

## (d) 바뀌지 않은 것 대조

| 항목 | 그대로인 근거 |
|---|---|
| stdout 마지막 줄 | `done(...)`의 extra 문자열을 고치지 않음. 기존 시험 516·525·820·899행 줄 단언 통과, 새 시험도 같은 줄을 단언 |
| 종료 코드 | `EXIT_CODES` 무수정. 기존 515행 (11, FETCH_FAILED) 통과 |
| `batch.json`의 `counts` | 7~12단계 무수정. 425·526행 단언 통과 |
| `REASON_KO` | 사전 값 무수정(첫 실패는 사유 문자열 뒤에 덧붙일 뿐). 고정 시험 통과 |
| 요청 모양 | `build_requests`·가리기·고르기·기록 사슬·수거 경로 무수정. `test_request_shape` 통과 |
| 금지어 | `test_script_source_contract` 통과(새 네트워크 모듈·금지어 없음, 스크립트 ASCII) |
| 쓰는 곳 | 새 파일은 `workspace/outputs/llm/news/<날짜>/` 아래뿐, dry run은 쓰지 않음 |

## (e) 병합 뒤 확인

- 다음 19:30 KST 자동 제출(InvestmentV2-LLMPilots → `llm_runner.py` news-submit) 뒤 `workspace/outputs/llm/news/<날짜>/fetch-errors.json`의 `errors[].type`·`message`와 `failed.md`의 `[symbol type]`을 본다. 사장 손 없음.
- 원인이 반환 꼴(not_list)이면 정규화 고침, 예외(예: 차단·요청 제한)면 출처 대안 검토 — 둘 다 별도 개발 큐·사장 승인(지시문 연결표 ④).
- 알림 끊김은 기존과 같다(지시문 연결표 ⑤): 실행기 하루 기록·`failed.md`를 자동으로 읽는 예약은 이 작업 밖.
