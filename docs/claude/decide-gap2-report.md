---
id: decide-gap2-report
title: decide 대기 중 Ctrl+C 처리 — Builder 보고 (관제판 작업 ID decide-research-gap)
date: 2026-10-22
prompt: docs/claude/decide-gap2-builder-prompt.md
base: 59c4f4887a8898a4e36fc1f21b74585e67cbbcd6
class: authority (경로 규칙). 한도·권한·관문·대기 시각 불변
weekly_user_touch: 0
---

# decide-gap2 Builder 보고

## 바뀐 것 (manage-us-stock-strategy/scripts/auto_core_decide.py 한 파일, +13 −2)

1. `_wait_for_research` (auto_core_decide.py:474-493): `sleeper(RESEARCH_POLL_SECONDS)` 호출을 `try/except KeyboardInterrupt`로 감쌌다. 중단되면 대기 루프만 끝내고(`interrupted = True`, `break`), 반환 dict에 `"interrupted": <bool>` 키를 더했다. `waited_seconds`는 끝까지 잔 횟수만 센다(첫 sleep에서 중단 = 0). 그 뒤 `found`는 지금처럼 다시 확인한다.
   - 스키마 확인: `schemas/auto-core-decision.schema.json:27` `"inputs": {"type": "object"}` — `inputs` 아래 키를 막지 않으므로 키 추가가 허용된다. 그래서 `exceptions`의 `RESEARCH_WAIT_INTERRUPTED` 대안은 쓰지 않았다(알림·결정 해시를 바꾸지 않는 쪽이 더 작음). 스키마 변경 없음.
   - `wait` 블록은 이미 결정 해시에서 빠진다(`decision_identity_hash`, auto_core_decide.py:775-777 부근 `if key != "wait"`) → 중단 표지가 저널 review_id(R2-5 같은 날 재실행 판별)를 바꾸지 않는다(테스트로 확인).
2. 중단 뒤 흐름은 그대로: 연구 기록 없음 → `research_block` → 매수만 막힘. 매도·무행동 로직, `RESEARCH_WAIT_UNTIL`(08:30)·`RESEARCH_POLL_SECONDS`(300) 변경 없음.
3. `decide()` 바깥 (auto_core_decide.py:452-454): `except KeyboardInterrupt:` 하나를 더해 `status=FAIL`, `reasons += ["INTERRUPTED:KeyboardInterrupt"]` 후 기존처럼 `_finish`로 decision.json·LATEST_DECISION.json을 쓰고 정상 반환한다. 기존 `except DecideFailure`·`except Exception` 무변경. (KeyboardInterrupt는 Exception 하위가 아니라 순서와 무관.)
- `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 든 줄은 만들거나 지우거나 바꾸지 않았다(git diff 확인). 매도를 막는 조건 추가 없음.

## 4. FAIL 기록이 재실행·저널에 미치는 영향 (읽은 결과)

- 바깥 except 경로는 저널에 쓰지 않는다. 저널 쓰기는 `_run`의 apply 분기 `append_auto_core_entries` (auto_core_decide.py:751) 한 곳뿐이고 그대로다. `_finish`→`_settle`(1248-1270)은 FAIL이면 f6_ran false, 원장·미분류 티켓은 직전 원장 출처에서 그대로 옮기고 티켓을 비운다(커밋 없음). 저널·상태·정책 파일 쓰기는 늘지 않았다.
- 같은 날 재실행(R2-5, 728-736)은 decision.json이 아니라 저널의 같은 평가 세션·같은 run day `core_decision`만 본다. 중단 FAIL은 저널 항목을 남기지 않으므로 재실행을 막지 않는다 — 테스트 `test_a_same_day_rerun_after_the_fail_record_runs_normally`가 FAIL 뒤 같은 날 apply 재실행이 정상(티켓 발행, core_decision 1건, rerun 파일 없음)임을 보인다. 다음 날 실행은 `ledger_carry`가 f6_ran false 기록을 건너뛰므로 원장도 영향 없음(기존 `except Exception` FAIL과 같은 경로).

## 5. 검토 순서

- NO_CHANGE: 안 됨 — 10/21처럼 대기 중 중단이면 decision.json이 없고 매도 판정도 없다(지시문 근거, 아래 a).
- REMOVE/SIMPLIFY: 대기 자체를 없애면 연구 기록이 07:45~08:30 사이에 늦게 오는 날 매수 판정을 잃는다(현행 규칙 변경) → 하지 않음.
- REUSE: 기존 `except Exception` → `_finish`/`_settle` FAIL 경로와 기존 "기록 없음 = 매수만 막힘" 경로를 그대로 다시 썼다. 새 예외 코드·새 알림 없음.
- REPLACE: 대기 구조를 바꿀(별도 재판정 예약 등) 필요 없음 — 아래 c.
- ADD: try/except 두 곳 + `interrupted` 키 하나만. 1(대기 중 중단 → 계속)이 없으면 매도 판정이 안 나오고, 3(밖 중단 → FAIL 기록)이 없으면 기록이 남지 않는다. 둘 다 빼면 목표를 못 채우므로 최소다.

## 테스트

새 파일 manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py (기존 test_auto_core_decide.py의 `Env` 재사용, 기존 테스트 파일 무변경, sleeper·bars_loader 주입만, 실제 sleep·키움·네트워크 없음). 매도 티켓이 실제로 나오도록 SOXL 120주·현금 $300·하락 SOXL·SOXX −2σ 날(test_auto_core_tickets의 매도 경우)을 decide 경로로 돌린다.

| 테스트 | 확인 |
|---|---|
| test_ctrl_c_in_the_wait_keeps_the_sell_and_no_action_judgment | 첫 sleep에서 중단 + 기록 없음: FAIL 아님, 스키마 통과, found false, waited 0, interrupted true, 매도 티켓 있음, status·reasons·tickets·no_action·blocked·candidates·buy_requirements·symbols 등이 08:30까지 다 기다린 실행(45분, interrupted false)과 같음, 매수 티켓 없음, MU 매수 요건 ① no |
| test_ctrl_c_in_the_wait_in_recording_mode_journals_like_the_full_wait | apply 모드에서도 같은 저널 항목 종류, wait 블록이 결정 해시 밖 |
| test_ctrl_c_on_a_later_sleep_keeps_the_time_already_waited | 세 번째 sleep에서 중단: waited 600초, interrupted true |
| test_a_present_record_does_not_wait | 기록이 있으면 sleep 호출 없음, waited 0, interrupted false, 판정이 지금과 같음 |
| test_ctrl_c_outside_the_wait_leaves_a_fail_record | bars_loader에서 중단(apply): 예외가 새지 않음, decision.json FAIL + `INTERRUPTED:KeyboardInterrupt`, LATEST_DECISION.json 같음, 스키마 통과, 티켓 없음, f6_ran false, DECIDE_FAIL 푸시, 저널 바이트 무변경 |
| test_a_same_day_rerun_after_the_fail_record_runs_normally | 위 FAIL 뒤 같은 날 재실행 정상(위 4) |

결과 (2026-10-22, base 59c4f48 + 이 변경):
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_decide_interrupt.py"`: 6 OK
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`: 494건, 실패 1, skip 1. 실패는 `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches` (symbol=PLTR, `CARD_SECTION_CHANGED`, `CARD_NOT_ACCEPTED_IN_WATCHLIST`). 이 테스트는 실제 docs/claude 등록부·관심목록을 `inputs.card_check`로 읽을 뿐(test_auto_core_decide.py:1332-1339) 바뀐 함수를 지나지 않으므로 이 변경과 무관한 자료 상태다. 기준선 대비 판정은 파이프라인 기준선 측정으로 확인.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`: PASS (errors 0)

## 남은 위험

- (a) 10/21 로그(workspace/outputs/auto-core/logs/auto-core-decide-20261020T224500Z.log)에는 `^C`만 있고 파이썬 트레이스백이 없다(지시문 근거, 이 세션에서 로그 원문은 열지 않음). 파이썬이 KeyboardInterrupt를 받았는지, 콘솔·cmd가 먼저 끝나 프로세스가 통째로 죽었는지는 **확인 필요**. 후자라면 이 수정은 그 경로를 막지 못한다(창 숨김 hide-task-window가 입력 원인을 줄이는 쪽).
- (b) 콘솔 창 닫힘(CTRL_CLOSE_EVENT)·작업 강제 종료·PC 재부팅·전원 차단은 파이썬 안에서 잡을 수 없다. 그때는 여전히 decision.json이 없고, 다음 실행의 알림 11(직전 decide 누락)만 남는다.
- (c) 더 강한 대안(08:30 이후 별도 재판정 예약, 대기 전 임시 기록 쓰기)은 예약 작업 변경이나 큰 구조 변경이라 이 작업에서 하지 않았다.
- 대기의 sleep 밖(기록 존재 확인·clock 호출 순간)이나 `_finish` 쓰기 중의 두 번째 Ctrl+C는 그대로 밖으로 나간다(창이 매우 짧음).
- apply 모드에서 저널 쓰기(751) 직후, 채점기 실행(756) 중 또는 `_finish` 전에 중단되면 저널에는 그날 결정이 있고 decision.json은 FAIL이 된다. 같은 날 재실행은 R2-5에서 같은 해시면 아무것도 쓰지 않고 돌아가므로 그날 decision.json은 FAIL로 남는다. 기존 `except Exception`이 같은 자리에서 내는 결과와 같은 기존 한계이며(새 쓰기 없음, 매수 쪽으로 막힘), 고치려면 R2-5·저널 흐름을 바꿔야 해서 범위 밖이다.

## 지킨 것

auto_core.py·작업 등록 스크립트·kiwoomcli 실행 없음, 예약 작업 무변경, 키움 호출 없음, 정책·상태·저널 파일 쓰기 없음, allowed_paths 밖 변경 없음, auto_core_decide.py 줄바꿈 CRLF 유지(`git ls-files --eol` = w/crlf), 커밋·git add 없음.
