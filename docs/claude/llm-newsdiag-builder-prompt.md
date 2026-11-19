---
id: llm-newsdiag-builder-prompt
title: "API 시범 2 뉴스 — 기사 가져오기 실패 원인 남기기(진단만) — llm-newsdiag"
date: 2026-11-19
class: "general(기존 시범 스크립트 1개와 그 시험만, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork가 dev-merge"
source: "진단 docs/claude/backlog-review-2026-11-19.md 3절(11/18·11/19 19:30 news-submit 두 번 FETCH_FAILED symbols_failed=30, 원인이 남지 않음). 개발 큐 등록 승인 = 사장 결정 카드 '오류 기록 고치기(개발 큐)'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9G2jN3URHaiDhhPkAaJbUV6, 2026-11-19 19:41:54 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 사장실 회사PC 스레드 '밀린 검토 3건 결론 내기')"
authority: "권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · 계좌·보유 자료를 읽지 않음 · API 키 값을 읽거나 출력하지 않음 · 켜기 파일을 바꾸지 않음 · 사전 등록 두 파일을 바꾸지 않음"
---

## 목표
- `llm_pilot_news.py` 제출 단계가 기사 가져오기에 실패한 종목마다 **왜 실패했는지**(예외 종류·짧은 메시지, 또는 목록이 아닌 반환 꼴)를 남기게 한다. 지금은 `fetch_items`(303~312행)가 `except Exception: return None`으로 원인을 버려 `failed.md`에 '기사 가져오기 실패 (FETCH_FAILED)'만 남는다.
- **진단만 더한다.** 무엇을 보내는지·고르는지·가리는지·점수·기록 사슬·종료 코드·stdout 마지막 줄은 한 글자도 바뀌지 않는다. 사전 등록 v1과 무관한 변경이다.

## 바꿀 파일 (이 3개만)
- manage-us-stock-strategy/scripts/llm_pilot_news.py (기존, CRLF — 원래 줄바꿈을 지킨다)
- manage-us-stock-strategy/tests/test_llm_pilot_news.py (기존, CRLF — 원래 줄바꿈을 지킨다. 기존 시험은 고치지 않고 새 시험만 더한다)
- docs/claude/llm-newsdiag-report.md (새 파일, 보고)

두 기존 파일은 CRLF다. 편집 도구가 LF로 바꾸면 안 된다. 보고 (c)에 `git diff --ignore-cr-at-eol --stat`과 `git diff --stat`을 둘 다 적어, 두 숫자가 같음(줄바꿈 전체 변환 없음)을 보인다.

## 먼저 읽을 것 (고치지 않는다)
- `manage-us-stock-strategy/scripts/llm_pilot_news.py` 전체. 특히 `_URL`(127행), `fetch_items`(303행), `run_submit` 6단계(444~454행), `fail`(403행), `REASON_KO`(110행), `EXIT_CODES`.
- `manage-us-stock-strategy/scripts/llm_pilot_common.py`의 `write_failed`(369행)·`atomic_write_text`.
- `manage-us-stock-strategy/tests/test_llm_pilot_news.py`의 `Fetcher` 가짜, `test_fetch_items_failure_is_none`(356행), `test_all_fetches_failed`(511행), `test_some_fetches_failed_are_counted`(520행), `REASON_KO` 고정 시험(876행 근처), dry run 시험(820행 근처).

## 구현 요구 (ASCII만, `scripts/*.py` 언어 계약)
1. 새 함수 `fetch_items_detail(symbol, fetcher=None) -> (list | None, dict | None)`.
   - 성공(목록·튜플): `(list(raw), None)`.
   - 예외: `(None, {"symbol": symbol, "kind": "exception", "type": type(exc).__name__, "message": <정리한 메시지>})`.
   - 목록이 아님: `(None, {"symbol": symbol, "kind": "not_list", "type": type(raw).__name__, "message": ""})`.
   - `<정리한 메시지>` = `str(exc)`를 이 순서로 정리한다: (1) `_URL`로 주소 → `[url]` (2) `\r`·`\n`·`\t` → 공백 (3) 0x20~0x7E 밖 글자 → `?` (4) 앞 200자. 메시지를 만들다 다시 예외가 나면 빈 글.
   - `type` 칸에도 (3)을 적용하고 80자에서 자른다.
   - `BaseException` 중 `KeyboardInterrupt`·`SystemExit`는 잡지 않는다(지금 `except Exception`과 같은 범위).
2. `fetch_items(symbol, fetcher=None)`는 `fetch_items_detail`의 첫 값만 돌려준다(동작·시그니처 그대로 — 356행 시험이 그대로 통과).
3. `run_submit` 6단계에서 `fetch_items_detail`을 쓰고 실패 정보를 사전 등록 `universe` 순서대로 모은다.
   - 실패가 1건 이상이고 dry run이 아니면 `news/<날짜>/fetch-errors.json`을 원자적으로 쓴다(`atomic_write_text`, UTF-8, `ensure_ascii=True`, 키 정렬): `{"schema": "llm-news-fetch-errors-1", "day": <날짜>, "written_kst": <stamp>, "symbols_failed": N, "symbols_total": M, "errors": [ ...1의 dict... ]}`. 성공 종목은 넣지 않는다.
   - 모두 실패(`FETCH_FAILED`)면 `failed.md` 사유를 `REASON_KO["fetch_failed"] + " [" + <첫 실패 symbol> + " " + <type> + "]"`로 쓴다. `REASON_KO` 사전 값은 바꾸지 않는다(876행 시험). 결과 줄은 `검토 못 함: 기사 가져오기 실패 [MRVL YFRateLimitError] (FETCH_FAILED)` 꼴이 된다.
   - stdout 마지막 줄·종료 코드·`batch.json`의 `counts`는 지금과 같다(515·516·525·425행 시험이 그대로 통과).
   - 같은 날 제출을 다시 불러 실패하면 `fetch-errors.json`을 덮어쓴다(가장 최근 시도). 제출에 성공하는 날에도 일부 실패가 있으면 쓴다.
   - 이번 시도에서 실패가 0건이고 dry run이 아니면, 남아 있는 `fetch-errors.json`을 지운다(513~515행의 낡은 `failed.md` 지우기와 같은 방식).
   - `fetch-errors.json`을 쓰거나 지우다 `OSError`가 나면 삼키고 계속한다(진단 파일은 제출을 막지 않는다, 종료 코드는 그대로).
4. 그 밖의 경로(가리기·고르기·요청·수거·기록)는 고치지 않는다. 주석을 포함해 `test_script_source_contract`(시험 849행)의 금지어(environ·zoneinfo·subprocess·import requests·urllib·fallbacks·advisor·socket·http.client·auto_core·kiwoom)를 쓰지 않는다.

## 시험 (test_llm_pilot_news.py에 새 시험만 더함)
- `test_fetch_items_detail_exception`: 가짜 fetcher가 `RuntimeError("rate limited https://x.example/a?b=1\nmore")` → kind exception, type RuntimeError, 메시지에 주소 대신 `[url]`, 줄바꿈 없음, 200자 이하.
- `test_fetch_items_detail_not_list`: 반환 `{"a": 1}` → kind not_list, type dict.
- `test_fetch_items_detail_non_ascii_and_long`: 비ASCII·500자 메시지 → `?`로 바뀜, 200자.
- `test_all_fetches_failed_writes_errors`: 30종목 모두 예외 → 기존 줄·코드 그대로 + `fetch-errors.json` 30건이 universe 순서, `failed.md`에 `[<첫 symbol> RuntimeError]`와 `(FETCH_FAILED)`.
- `test_some_fetches_failed_writes_errors`: 2종목 실패 → SUBMITTED 줄 그대로 + `fetch-errors.json` 2건.
- `test_dry_run_writes_no_fetch_errors`: dry run에서 실패가 있어도 파일을 쓰지 않음.
- `test_no_fetch_errors_file_when_all_ok`: 실패 0이면 파일 없음.
- `test_stale_fetch_errors_removed_when_retry_ok`: 남아 있던 `fetch-errors.json`이 실패 0인 제출 뒤 지워짐.
- `test_fetch_errors_write_oserror_does_not_change_outcome`: 쓰기가 `OSError`를 내도(예: 같은 이름 폴더를 미리 만들어 둠) 일부 실패 제출의 줄·코드가 그대로.
- Builder 시험 명령(이 글자 그대로): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_news*.py"`. 전체 시험은 돌리지 않는다(파이프라인이 한다).
- 모든 시험은 임시 루트·가짜 fetcher·가짜 client만 쓴다. 네트워크·yfinance·SDK·실제 키 없음.

## 지켜야 할 것
1. 위 3개 파일 밖은 손대지 않는다. 새 보고 파일은 LF로 쓴다. 사전 등록 두 파일·`llm-pilots-schedule.json`·`llm_pilot_common.py`·`llm_pilot_iccheck.py`·`llm_runner.py`와 그 시험을 고치지 않는다.
2. 기존 시험을 고치거나 지우지 않는다. 기존 시험이 깨지면 구현을 고친다.
3. 키 값을 읽지 않는다. 비밀(.env*·토큰·계좌번호) 파일을 열지 않는다.
4. 어떤 시범도 켜지 않는다. Windows 작업을 등록·실행·변경하지 않는다. 저장소 루트에 대고 스크립트를 돌리지 않는다(`--dry-run` 포함).
5. 주문·키움·일지·원장·예약·정책·상태와 무관하다. auto_core.py·kiwoomcli 실행 금지. git은 status·diff·log만. commit·push·병합 없음. `python -c`·pip 쓰지 않음.
6. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/llm-newsdiag-report.md
- (a) 바꾼 함수(파일:행)와 새 파일 이름 `fetch-errors.json` 모양
- (b) 새 시험 이름과 단언 요약, 기존 시험이 그대로임
- (c) 시험 결과 마지막 3줄 · `git diff --stat` · `git diff --ignore-cr-at-eol --stat`
- (d) 바뀌지 않은 것 대조: stdout 마지막 줄·종료 코드·`counts`·`REASON_KO`·요청 모양
- (e) 병합 뒤 확인: 다음 19:30 KST 자동 제출 뒤 `workspace/outputs/llm/news/<날짜>/fetch-errors.json`과 `failed.md`의 `[symbol type]`을 본다. 사장 손 없음.
- 수량·금액·키 값을 적지 않는다. 주문·권한 표지 문자열도 적지 않고 '권한 표지 4종 줄 변경 없음'이라고만 쓴다.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| `workspace/outputs/llm/news/<날짜>/fetch-errors.json`(이 작업이 새로 만드는 파일) · `failed.md`의 `[symbol type]` | Windows 작업 InvestmentV2-LLMPilots → `manage-us-stock-strategy/scripts/llm_runner.py:55` news-submit 19:30 KST → 이 스크립트 | 사람 단계 — 자동으로 읽는 예약 없음. 사장실 회사PC 스레드가 원인 진단 때 직접 읽음(원문 `docs/claude/backlog-review-2026-11-19.md:58-62`) | 원인이 ②(반환 꼴)면 정규화 고침, ①(Yahoo 차단)이면 출처 대안 검토 — 둘 다 별도 개발 큐·사장 승인(원문 `docs/claude/backlog-review-2026-11-19.md:60`) | 끊김 — 실행기 하루 기록 `workspace/outputs/llm/runner/<날짜>.json` status와 `failed.md`를 읽는 예약이 없다(`docs/claude/llm-news2-builder-prompt.md:186`과 같은 끊김). 메울 변경: 사장실 결과 모음 예약이 실행기 하루 기록을 읽게 하기 · 승인 경로: 지침 4절 `예약 작업 변경 승인: <이름>`(이 작업 밖) | 사람 단계 · 알림 끊김(기존과 같음) |

기존 산출(records.jsonl·digest.md·usage.jsonl·batch.json)의 연결은 이 작업으로 바뀌지 않는다 — `docs/claude/llm-news2-builder-prompt.md:186-188` 그대로.

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이다. 두 기존 파일의 줄바꿈이 CRLF 그대로다(checks.json 위생에 EOL_CRLF_BROKEN 없음 + 보고 (c)의 두 stat).
2. stdout 마지막 줄·종료 코드·`counts`·`REASON_KO` 값·요청 모양이 그대로다(기존 시험 무수정 통과).
3. `fetch-errors.json`은 dry run에서 쓰지 않고, 실패 0이면 쓰지 않으며, 쓰기는 `workspace/outputs/llm/news/<날짜>/` 아래뿐이다.
4. 메시지 정리: 주소 가림·ASCII·200자·줄바꿈 없음이 시험으로 단언된다. 키 값·계좌 자료가 들어갈 길이 없다.
5. `KeyboardInterrupt`·`SystemExit`를 새로 삼키지 않는다. 새 네트워크 모듈 없음.
6. 기존 시험 변경 없음, 새 실패 0. 보고서 (a)~(e) 있음, 표지 문자열 없음.

```dev-run
{"task_id": "llm-newsdiag", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_pilot_news.py", "manage-us-stock-strategy/tests/test_llm_pilot_news.py", "docs/claude/llm-newsdiag-report.md"], "target_tests": ["test_llm_pilot_news*.py"], "commit_message": "fix(llm-pilot): record per-symbol news fetch errors (fetch-errors.json, failed.md first error) - diagnosis only, no change to selection, scoring or exit codes (llm-newsdiag)"}
```
