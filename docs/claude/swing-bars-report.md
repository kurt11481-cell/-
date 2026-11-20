---
id: swing-bars-report
title: 자동 코어 daily — 스윙 관찰 종목 종가 별도 수집(swing-bars) Builder 보고
date: 2026-11-20
task_id: swing-bars
class: authority (경로 때문 — 권한 표지 줄 변경 없음, 주문 경로 없음, 스키마 변경 없음)
prompt: docs/claude/swing-bars-builder-prompt.md
---

# swing-bars Builder 보고

## 1. 바꾼 것 — `manage-us-stock-strategy/scripts/auto_core.py`

| 줄 | 내용 |
|---|---|
| 12 | 모듈 docstring daily 단계 목록에 `6 (best effort, after 5) swing watch list closes -> swing-bars.json, never changes the result` (ASCII) |
| 36·38·41 | `import functools`, `import re`, `import time` |
| 68~76 | 상수 `SWING_WATCH_PATH`(REPO_ROOT/docs/claude/swing-watch.json), `SWING_FILE`, `SWING_SCHEMA_VERSION`("auto-core-swing-bars-1.0"), `SWING_LIST_SCHEMA`("swing-watch-1"), `SWING_SYMBOL_PATTERN`(`[A-Z][A-Z0-9.]{0,11}`, fullmatch), `SWING_TIME_BUDGET_MIN`=20, `SWING_SYMBOL_TIMEOUT_S`=600, `SWING_REASON_MAX`=200 |
| 219·226 | `collect_bars`에 키워드 `timeout: int = 3600`, runner 호출이 `timeout=timeout` (기본값 3600 그대로 — 코어 동작 불변) |
| 254~359 | 새 swing 절: `SwingListInvalid`, `read_swing_watch`(utf-8-sig, 파일 없음 → None, 그 밖 오류·형식 틀림 → LIST_INVALID 사유, 중복 제거·알파벳 순), `_verified_sessions`(장부 `load_closes`와 같은 기준 — verified true이고 close 있음; 갱신 뒤 history를 못 읽으면 그 종목 failed), `_swing_reason`(StepFailure 그대로, TimeoutExpired는 `BAR_COLLECTION_TIMEOUT:<SYM>:<초>` — 명령줄·프로필 별칭을 남기지 않음, 그 밖 `UNEXPECTED_ERROR:<SYM>:<형>:<글>`, 200자), `write_swing_record`(쓰기 실패 삼킴), `collect_swing_bars`(대상 = 목록 − 코어 종목, 종목마다 코어 루프와 같은 known_exchange·resolve_exchange·첫 수집 150일·history_updater, 모든 예외를 그 종목 failed로, 시작 전 남은 예산 < 600초면 그 종목부터 deferred) |
| 471~476 | `daily` 새 인자 `swing_watch_path: Path \| None = None`, `swing_collector = functools.partial(collect_bars, timeout=SWING_SYMBOL_TIMEOUT_S)`, `swing_clock = time.monotonic`. 공용 `collector`에는 timeout을 넘기지 않음 |
| 537~539 | 코어 수집 루프의 `symbols_for_run(...)` 결과를 `core_symbols`에 담아 그대로 순회(호출 1번 그대로, swing 단계에 같은 목록을 넘김) |
| 576~592 | 마지막 코어 `_finish`(result.json·LATEST.json 쓰기) 뒤 한 곳: `swing_watch_path`가 None이 아니고 끝난 결과 status가 OK·HOLD일 때만 `collect_swing_bars` 호출, 전체 `try/except Exception`(예외 시 가능하면 swing-bars.json에 status PARTIAL + reason `UNEXPECTED_ERROR:...`), 반환은 `_finish`의 반환값 그대로 |
| 636 | `main()` daily만 `swing_watch_path=SWING_WATCH_PATH`를 넘김 |

호출 지점이 아닌 곳: 킬 스위치 이른 HOLD 반환(525행), StepFailure·그 밖 예외 FAIL 반환(565·570행)에는 swing 호출이 없다. 코어 결과 status가 `_finish`의 스키마 검사로 FAIL이 된 날도 돌지 않는다(끝난 결과의 status를 봄).

바꾸지 않은 것: `symbols_for_run`·`isolatable_symbols`·bar-isolate·노출 검토·결과 스키마·`auto_core_decide.py`·첫 수집 시작일·코어 수집 timeout 3600·result에 더한 키 없음. 권한 표지 줄 변경 없음, 주문 경로 문자열 없음(Grep 0건), scripts 파일 ASCII 전용(비ASCII 0건).

**지시문에서 Builder가 정한 세부(판단 기록)**
- `deferred`는 종목 코드 문자열 배열(`["SWB", "SWC"]`)로 적었다(지시문은 형식을 정하지 않음; `failed`만 `{"symbol","reason"}`).
- swing 단계 바깥 예외(목록 읽기 함수 자체의 버그 등)는 status `PARTIAL` + `reason`으로 적었다. 지시문 10번은 "failed·deferred 모두 비면 OK"라 그대로면 실패가 OK로 보이므로, 숨기지 않는 쪽(fail-closed)을 골랐다. 이 경우 failed·deferred는 비어 있다.
- `histories[].sessions`는 history_updater 반환의 `sessions`(실제 update_history의 session_count), `verified_sessions`는 갱신된 history 파일에서 센다. 갱신 뒤 그 파일을 못 읽으면 장부도 못 읽으므로 그 종목을 failed(`CLOSE_HISTORY_UNREADABLE:<SYM>:<형>`)로 적는다.
- 시간 예산 경계: 남은 예산이 정확히 600초면 시작한다("적으면" 미룸).

## 2. 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_swing_bars.py` (23개)

`test_auto_core.DailyTests` 상속, `load_tests`로 이 클래스에 정의된 테스트만 실행. 목록 파일은 임시 경로, swing collector·시계는 가짜. 키움·kiwoomcli·PowerShell 호출 없음.

| 지시문 | 테스트 |
|---|---|
| 1 | `test_swing_no_watch_path_runs_as_before`(swing 인자 없이 — 기존 호출자와 같음, collector {AAA,BBB,NEWW,SOXX} 4회, swing-bars.json 없음, 기본값 None) · `test_swing_spy_without_watch_path_is_not_called` |
| 2 | `test_swing_missing_list_file_writes_nothing` |
| 3 | `test_swing_collects_listed_symbols_once_after_the_core_result`(["SWA","AAA","SWA"] → SWA 1회, 거래소 조회·첫 수집 2026-05-17, swing collector 안에서 읽은 result.json·LATEST.json 바이트 = 반환 뒤 바이트, `load_json(result.json) == 반환값`, steps 키 불변, 스키마 통과, 기록 전체 일치) · `test_swing_known_history_continues_from_its_last_session` |
| 4 | `test_swing_symbol_failures_never_change_the_core`(SWA StepFailure·SWB TimeoutExpired·SWC RuntimeError·SWD 정상, `main()` 경유 종료 코드 0, 3번 방식 바이트 확인, PARTIAL) · `test_swing_exchange_and_history_failures_are_recorded`(EXCHANGE_UNRESOLVED·CLOSE_HISTORY_FAILED·CLOSE_HISTORY_UNREADABLE) · `test_swing_long_reason_is_cut`(200자) |
| 5 | `test_swing_time_budget_defers_everything_when_spent`(collector 0회, 전부 deferred) · `test_swing_time_budget_defers_the_rest` · `test_swing_time_budget_boundary_starts_with_exactly_one_timeout_left`(상수 20·600 확인) |
| 6 | `test_swing_not_run_on_a_failed_day`(보유 AAA 수집 실패) · `test_swing_not_run_when_the_finished_result_is_a_fail`(`_finish` 스키마 검사 FAIL) |
| 7 | `test_swing_not_run_on_the_halted_day`(킬 스위치 HOLD: 계좌 조회·수집·노출 0, swing 0회, 파일 없음) · `test_swing_runs_on_an_ordinary_hold_day`(설명 안 되는 날 HOLD → swing 단계 돎, 2026-10-15 기록 OK, 코어 바이트 불변) |
| 8 | `test_swing_invalid_list_is_recorded_and_not_collected`(schema 다름·소문자·깨진 JSON·객체 아님·symbols 리스트 아님·문자열 아님·13자·`A/B`·끝 줄바꿈 → LIST_INVALID, reason 1~200자, collector 0회) · `test_swing_list_with_bom_and_dotted_code_is_read`(BOM·`BRK.B`) |
| 9 | `test_swing_list_of_core_symbols_only`(["AAA","NEWW"] → 0회, OK, 빈 배열) · `test_swing_empty_list_is_ok` |
| 10 | `test_swing_record_write_failure_never_changes_the_core`(같은 이름 폴더, `main()` 종료 코드 0, 3번 방식 확인) · `test_swing_unexpected_step_error_never_changes_the_core`(단계 바깥 예외 → 코어 그대로, PARTIAL+reason) |
| 11 | `test_swing_default_collector_uses_the_symbol_timeout`(가짜 runner: 기본 swing collector 600, 코어 `collect_bars` 3600) |
| (Judge 3) | `test_swing_main_passes_the_repository_list`(`main()`이 `SWING_WATCH_PATH`를 넘김) |

## 3. 테스트 결과

- 새 파일: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_swing*"` → Ran 23, OK.
- 대상 전체: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` → Ran 654(기준선 631 + 새 23), FAILED (failures=1, skipped=1). 실패 1건은 아래 기준선과 같은 기존 실패이고, 새로 생긴 실패는 0건이다. 기존 test_auto_core*.py는 고치지 않았다.
- 기준선(변경 전, 같은 명령): Ran 631, FAILED (failures=1, skipped=1). 그 1건은 `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(symbol='SOXL', `entry["trim_target_weight"]` 0.1 is not None — 실제 저장소 카드 등록부 자료) — 이번 변경과 무관한 기존 실패이며 고치지 않았다(기존 테스트·등록부는 범위 밖). 지시문 '지켜야 할 것' 1번의 BLOCKED 조건은 이번 변경이 기존 테스트를 깨뜨린 경우로 읽었다. 변경 전후 실패가 같은 1건(같은 테스트·같은 단언·같은 값)이라 BLOCKED.md는 쓰지 않았다. 파이프라인의 기준선 비교가 이를 판정한다.
- 줄바꿈: auto_core.py 작업 트리 CRLF 644줄, LF 단독 0줄(git i/lf w/crlf 유지). `git diff --stat`와 `git diff --ignore-cr-at-eol --stat`가 같다.

```
git diff --ignore-cr-at-eol --stat
 manage-us-stock-strategy/scripts/auto_core.py | 158 ++++++++++++++++++++++++--
 1 file changed, 150 insertions(+), 8 deletions(-)
```
(새 테스트 파일과 이 보고는 추적 전 새 파일이라 위 stat에 나오지 않는다: `?? manage-us-stock-strategy/tests/test_auto_core_swing_bars.py`, `?? docs/claude/swing-bars-report.md`.)

## 4. Judge 8번 — 소비 쪽이 swing을 읽지 않음

Grep `(?i)swing` 대상: `manage-us-stock-strategy/scripts/auto_core_decide.py`, `docs/claude/t2rc-oracle.py`, `docs/claude/scheduled-prompts/auto-core-alert.txt`(및 pending-* 보관본 auto-core-alert*.txt 5개) → **0건**. decide·오라클·알림은 swing-bars.json도 목록 종목도 읽지 않는다.

## 5. 연결표 원문 대조(G9용 — 이 세션에서 연 원문)

- ② `manage-us-stock-strategy/scripts/register_auto_core_task.ps1` 25행: `Name = "InvestmentV2-AutoCore"; Command = "daily"; TriggerTime = "06:15"; LimitMinutes = 60` — 일치.
- ② 호출 지점: `auto_core.py` 576~592행(코어 `_finish` 뒤) — 이번 변경.
- ③ `docs/claude/swing_shadow_ledger.py` 85~96행 `load_closes`: `<SYM>.close-history.json`의 `sessions` 중 `verified is True`이고 close가 있는 것만 씀 — `verified_sessions` 셈과 같은 기준.
- ③ `docs/claude/scheduled-prompts/secretary-daily.txt` 17행: ㉰ 재개 가능 — `resume.type`이 date이고 `resume.date ≤ TODAY`인 작업을 올림 — 일치.
- ⑤ `manage-us-stock-strategy/scripts/host_status.ps1` 142~145행: 지난 7일 안 마지막 실행 결과가 0이 아니면 `"{작업}: last result 0x... at ..."` 경고 — 일치.
- 끊김 행(swing-bars.json status를 읽는 점검 없음)은 지시문 연결표에 메울 변경(주간 점검이 status를 읽음)·승인 경로(예약 지시문 변경, 사장 직접 입력)가 적혀 있다. 이번 변경으로 메우지 않는다.

## 6. 남은 위험

- daily 예약 한도 60분(`register_auto_core_task.ps1` 25행). 종목 상한 600초와 예산 20분으로 최악 약 33분(코어 약 3분 + 20분 + 마지막 종목 10분 + 그 종목 history 갱신)이지만, 예약이 끊기면 `host_status.ps1` 142~145행이 작업 종료 코드 경고를 낸다. 코어 결과는 이미 쓰였으므로 decide에는 닿지 않는다.
- 목록 종목 수집은 키움 읽기 조회를 늘린다(rate 정책 안). 첫 수집은 150일치라 길다. verified=false 세션은 장부가 버리므로 histories의 verified_sessions를 본다.
- `docs/claude/strategy1101_score.py` 259행은 history 폴더의 모든 `*.close-history.json`을 읽는다(입력 목록이 늘어남). **영향 확인 결과**: 계산에 쓰는 종목은 그 파일이 정한다(`price()` 368행 `self.closes.get(sym)` — 스냅숏 보유 종목·기준 SOXX). 다만 입력이 늘면 세 가지가 함께 바뀐다. (a) 입력 해시 목록(`self.inputs`, 280행)에 새 파일이 더해진다. (b) 계산 달력 `self.cal`이 **모든 history 날짜의 합집합**이다(287행) — 새 history는 같은 운영 세션 달력으로 만들어지므로 보통 날짜가 늘지 않지만, 기존 history 모두에 없는 세션이 새 파일에만 있으면 달력에 더해져 800·1165행 창(252세션)이 달라질 수 있다. (c) 새 파일에 필드가 빠졌거나 close가 유한·양수가 아니면 그 채점이 `STOP[restage]`/`STOP[wait]`로 멈춘다(268~279행) — 같은 빌더가 쓰므로 형식은 같지만 자료 한 파일이 채점 전체를 멈출 수 있다. 계산 종목 자체는 바뀌지 않는다.
- 목록 종목이 나중에 보유·관심이 되면 코어 수집으로 넘어간다(7번 빼기 — 대상 = 목록 − 코어 종목).
- `docs/claude/swing-watch.json`은 만들지 않았다(사장 결정 뒤 별도 커밋). 그 파일이 생기기 전까지 daily는 swing 단계에서 아무것도 하지 않고 파일도 쓰지 않는다.
- swing-bars.json의 status(LIST_INVALID·매일 deferred)를 읽는 점검이 아직 없다(연결표 끊김 행 — 위 5절).
