---
id: decide-gap2-builder-prompt
title: decide 대기 중 Ctrl+C로 끊겨도 판정 기록(매도·무행동)을 남기게 한다 (관제판 작업 ID decide-research-gap)
date: 2026-10-21
class: authority(경로 규칙: auto_core*.py가 authority-paths.txt에 있음). 내용은 한도·권한·관문 불변, 중단 처리만
source: 사용자 지시 "아침 점검 기록이 없어도 자동 판정이 매도 쪽은 끝까지 내게 고치기 진행"(2026-10-21 Cowork 세션)
evidence: workspace/outputs/auto-core/logs/auto-core-decide-20261020T224500Z.log = "RUNNER_START ... command=decide" 다음 줄바꿈 없는 "^C", RUNNER_END 없음, 수정 2026-10-21 07:58 KST · auto_core_decide.py:64-65(RESEARCH_WAIT_UNTIL 08:30, POLL 300초), 471-483(_wait_for_research), 553(호출), 446-451(`except DecideFailure`/`except Exception`)(KeyboardInterrupt는 BaseException이라 안 잡힘 → _finish 미호출 → decision.json 없음) · 연구 기록 없음 자체는 매수만 막는다(CLAUDE.md: 기록 없음 = 매수 티켓 전부 막음, 매도 아님)
authority: order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음
rerun: decide-gap(2026-10-21, NEEDS_APPROVAL, Judge PASS)를 새 기준에서 다시 실행 — 본 저장소에 문서 아닌 커밋(b7d3e4a·2b5a542, dc-dev 규칙 문구)이 들어와 dev-merge가 STOP_BASE_MOVED가 되므로. 사장 결정 "결정 decide-gap: 승인"(2026-10-22 15:37 KST, Cowork 대화). 지시 내용은 decide-gap과 같다(보고 파일 이름만 decide-gap2).
weekly_user_touch: 0 (병합 1번 + -ApproveAuthority 1번 — 사용자 지시 있음)
---

```dev-run
{"task_id": "decide-gap2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py", "docs/claude/decide-gap2-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): decide keeps going without the research record when the wait is interrupted and leaves a FAIL record on Ctrl+C"}
```

## 목표

2026-10-21 07:45 decide가 연구 기록을 기다리는 중 07:58에 `^C`로 끊겨 decision.json이 없었고 매도 판정도 안 나왔다. 원인은 둘이다. (1) 대기(sleep) 중 KeyboardInterrupt가 처리되지 않아 대기가 곧 판정 전체의 단일 실패 지점이다. (2) `decide()`는 `except Exception`만 잡으므로(주석 "a scheduled run must always leave a FAIL record") 중단 때는 FAIL 기록도 없다. 창 숨김(hide-task-window, 병합됨)이 입력 원인을 줄였고, 이 작업은 입력이 와도 결과가 남게 한다. 연구 기록이 없어도 매도·무행동 판정은 끝까지 나와야 한다(매수만 막힘 = 현행 규칙 그대로).

## 바꿀 내용 (auto_core_decide.py 한 파일, 작게)

1. `_wait_for_research`: `sleeper(...)` 호출을 `try/except KeyboardInterrupt`로 감싸 중단되면 대기를 끝내고 `interrupted=True`로 돌려준다. 이미 쓰는 반환 dict의 키를 추가할 수 있는지 `schemas/auto-core-decision.schema.json`의 `inputs.research_record.wait` 정의를 먼저 읽는다. 스키마가 추가 키를 막으면 스키마는 allowed_paths 밖이므로 고치지 말고, 같은 정보를 `exceptions`(code `RESEARCH_WAIT_INTERRUPTED`, 한국어 한 줄 "연구 기록 대기 중 중단 — 매수 티켓 없음, 매도 판정은 계속")로만 남긴다. 둘 다 막히면 BLOCKED.md에 이유를 쓴다.
2. 중단 뒤에는 대기만 끝내고 나머지 흐름은 그대로 간다: 기록 없음 → 매수 막힘, 매도·무행동은 현행 로직 그대로. 대기 시각·간격(08:30, 300초)은 바꾸지 않는다(NO_CHANGE).
3. `decide()` 바깥에 `except KeyboardInterrupt`를 추가해 `status=FAIL`, `reasons`에 `INTERRUPTED:KeyboardInterrupt`를 넣고 `_finish`로 기록을 남긴 뒤 정상 반환한다(기존 두 except와 같은 방식). 기존 `except Exception` 동작은 바꾸지 않는다.
4. FAIL 기록이 같은 날 재실행(R2-5 `_rerun`, 저널 중복 방지)을 막거나 저널에 쓰는지 읽고, 쓰지 않음을 보고에 한 줄로 적는다. 저널·상태·정책 파일 쓰기가 늘면 안 된다.
5. 검토 순서 NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD를 보고에 한 줄씩 적고, 위 1~3이 최소임을 보인다.

## 테스트 (새 파일 manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py, 기존 test_auto_core_decide.py의 Env 방식을 재사용, 기존 테스트 파일은 고치지 않음)

1. 첫 sleep에서 KeyboardInterrupt를 던지는 sleeper + 연구 기록 없음: status가 FAIL이 아니고, `wait.found` false, `waited_seconds` 0, 중단 표지(`interrupted` 또는 예외 code)가 남고, 매수 요건은 연구 없음으로 막히며, 매도·무행동 결과는 `research=False` 기준 실행(5분 간격 완주)과 같다(티켓·no_action 비교, 예외 목록 차이는 허용).
2. 대기 밖(예: bars_loader)에서 KeyboardInterrupt: decision.json이 만들어지고 status FAIL, reasons에 `INTERRUPTED:KeyboardInterrupt`, LATEST_DECISION.json 갱신, 예외가 밖으로 새지 않는다.
3. 기록이 이미 있으면 대기 없이(waited_seconds 0, interrupted 없음) 지금과 같은 결과.
4. 테스트는 sleeper·bars_loader 주입만 쓴다. 실제 sleep·키움 호출·네트워크 없음.

## 보고 docs/claude/decide-gap2-report.md

바뀐 줄, 테스트 결과, 남은 위험을 적는다. 반드시 포함: (a) 10/21 로그에는 `^C`만 있고 파이썬 트레이스백이 없다 — 파이썬이 KeyboardInterrupt를 받았는지, 콘솔·cmd가 먼저 종료돼 프로세스가 통째로 죽었는지는 확인 필요. 후자면 이 수정은 그 경로를 못 막는다(창 숨김이 입력 원인을 줄이는 쪽). (b) 콘솔 닫힘·강제 종료·PC 재부팅은 잡을 수 없다. (c) 더 강한 대안(08:30 이후 별도 재판정 예약, 대기 전 임시 기록)은 예약 작업 변경이나 큰 구조 변경이라 이 작업에서 하지 않았다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. `auto_core.py`·작업 등록 스크립트·`kiwoomcli`를 실행하지 않는다. Windows 예약 작업을 만들거나 바꾸거나 실행하지 않는다. 키움 호출 없음.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어 있는 줄을 만들거나 지우거나 바꾸지 않는다. 한도·예산·관문 규칙·RESEARCH_WAIT_UNTIL·RESEARCH_POLL_SECONDS를 바꾸지 않는다.
3. 매도를 막는 조건을 추가하지 않는다. 연구 기록 없음·중단은 매수만 막는다(실패 시 매수 쪽으로 막힘).
4. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`처럼 패턴으로만 돌린다("auto_core.py"가 들어간 명령 금지). 기존 테스트 파일 무변경.
5. allowed_paths 밖 파일을 만들거나 고치지 않는다. CRLF 줄바꿈을 일괄 변환하지 않는다(auto_core_decide.py의 기존 줄바꿈 유지).

## Judge 확인 항목

1. auto_core_decide.py diff가 대기 함수의 KeyboardInterrupt 처리 + decide() 바깥 except 하나 + 필요한 예외 표지뿐이다. 대기 시각·간격·게이트·티켓 규칙 변경 없음.
2. 매도·무행동 경로에 새 차단 조건이 없고, 중단 시 매수만 막힌다(테스트 1이 증명).
3. 대기 밖 KeyboardInterrupt가 FAIL 기록을 남기고 밖으로 새지 않는다(테스트 2).
4. 저널·상태·정책 파일 쓰기 증가 없음, 스키마 변경 없음(막히면 예외 표지만), 주문·권한 줄 변경 없음.
5. 보고에 파이썬이 ^C를 받았는지 미확인 상태와 한계가 적혀 있다. target_tests 통과, 기준선 대비 새 실패 0.
