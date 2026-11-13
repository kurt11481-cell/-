---
id: bar-isolate-report
title: bar-isolate Builder 보고 — 관심 종목 하나의 30분봉 수집 실패는 그 종목만 격리
date: 2026-11-13
prompt: docs/claude/bar-isolate-builder-prompt.md
class: authority (경로 때문 — auto_core*.py). 권한·한도·주문 단계·대조 불변식·킬 스위치 불변
authority: 권한 표지 4종 줄 변경 없음 · 주문 경로 없음 · 스키마 변경 없음 · 키움 호출 없음
---

# bar-isolate Builder 보고

## 1. 바꾼 줄

### `manage-us-stock-strategy/scripts/auto_core.py` (daily)

| 줄 | 내용 |
|---|---|
| 15~21 | 모듈 docstring: "the first failure stops it" → 보유·extra·노출 검토·decide 기준 종목 실패와 전역 실패는 멈춤, 관심 종목만의 거래소 읽기·30분봉·이력 실패는 격리(steps.bars.isolated), 집합을 못 읽으면 격리 없음 |
| 98~110 | `_held_symbols` — `symbols_for_run`의 보유 종목 부분을 그대로 떼어 냄(이번 run의 `kiwoom_broker_snapshot.shadow.json`, 없으면 상태 파일) |
| 113~119 | `_watch_members` — 같은 함수의 관심 명단 부분(`WATCHLIST_UNREADABLE` 그대로) |
| 122~127 | `symbols_for_run` — 서명·결과·예외 순서 그대로, 위 두 도우미를 부름 |
| 130~131 | `ISOLATABLE_REASONS = ("EXCHANGE_UNRESOLVED:", "BAR_COLLECTION_FAILED:", "CLOSE_HISTORY_FAILED:")` |
| 134~154 | `exposure_review_symbols` — `run_portfolio_exposure_review.py` 527~530행과 같은 출처: `exposure_config(<alert 정책>)`의 benchmark·supplement + `ledger_status`·`read_ledger_entries`·`reconstruct_snapshots`(장부 기본 경로 `default_ledger_path(state)`, 읽기만)로 복원한 모든 스냅숏의 보유 종목. 읽기 문제는 예외 |
| 157~172 | `isolatable_symbols` (새 도우미) = 관심 members − 보유 − `symbols_extra` − 노출 검토 종목 − `auto_core_rules.C`의 `RREC_BENCHMARK`·`RREC_POWER_BENCHMARK`. 어느 하나라도 읽다 예외면 빈 집합(fail-closed) |
| 408~432 | 수집 루프: 종목 하나의 처리(`known_exchange`·`resolve_exchange`·`collector`·`history_updater`)를 `try`로 감쌈. `StepFailure`이고 격리 가능 종목이며 사유가 `ISOLATABLE_REASONS`로 시작하면 `{"symbol", "reason"}`를 격리 목록에 넣고 다음 종목(이력 갱신 없음). 그 밖은 `raise`(→ FAIL). `StepFailure`가 아닌 예외는 잡지 않음(→ `UNEXPECTED_ERROR` FAIL 그대로). 격리 목록이 있을 때만 `steps.bars.isolated`를 넣음. `steps.bars.status`·`result.status`·`reasons`·`warnings`는 손대지 않음. 노출 계산은 그대로 돎 |

### `manage-us-stock-strategy/scripts/auto_core_decide.py`

| 줄 | 내용 |
|---|---|
| 179~180 | 상수 `T1_BARS_ISOLATED`, `T1_BARS_ISOLATED_INVALID` |
| 183~207 | `t1_isolated(t1, holdings, benchmarks)` — `steps`·`steps.bars`·`isolated`가 없으면 빈 목록(옛 기록·기존 fixture `{"status": "OK"}`). 있으면: 비지 않은 list, 항목 키가 정확히 `symbol`(비지 않은 대문자 str)·`reason`(str), 중복 없음, 보유·기준 종목 아님. `steps`·`bars`가 dict가 아니어도 어긋남. 어긋나면 `DecideFailure("T1_BARS_ISOLATED_INVALID")`(기존 FAIL 경로, 새 상태값 없음) |
| 657~658 | `benchmarks`(현 655행) 바로 뒤, holdings(현 579행)도 정해진 뒤 대조. 새 세션 없는 날 일찍 끝나는 경로(`_no_new_session`)보다 뒤라 그 경로에서는 대조하지 않음. 437행 T1 FAIL → HOLD `T1_NOT_OK`는 그대로 |
| 662~679 | 봉 불러오기 루프: 불러온 결과(`bars_loader` 또는 `load_symbol`)를 격리 종목이면 **새 dict** `{**loaded, "status": "ISOLATED", "errors": ["T1_BARS_ISOLATED"], "split_suspects": []}`로 덮고 다음 종목(그 종목에는 `SPLIT_SUSPECTED` 예외 없음). 격리 아닌 종목은 지금과 같음(`bars_loader`면 split 예외 없음, `load_symbol`이면 split 예외) |
| 680~686 | 격리 종목이 있으면 `exceptions`에 `("T1_BARS_ISOLATED", "관심 종목 30분봉 수집 실패 <종목들 ', '> — 오늘 그 종목 매수 막힘(보유 종목 매도·노출 판정은 계속) — Cowork 원인 확인")` 1건(→ alerts `push: True`, 기존 366~367행 경로). 한국어는 `\uXXXX` 이스케이프, 사유 문자열은 넣지 않음 |

결과에 새 필드 없음: 격리는 `alerts`, 그 종목의 `symbols.<X>.status "UNK"`·`reasons ["BARS_ISOLATED"]`(auto_core_rules.py 539~548행 기존 자료 문제 경로), `inputs.t1_result`로만 보인다. 매수 문턱·한도·R-REC1·재배치 순위 계산식·주문표 형식·`input_block`·연구 기록 문턱·T1 FAIL 처리·first-collect는 바꾸지 않았다.

## 2. 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py` (18개)

`load_tests`로 이 파일의 테스트만 돈다(상속한 `DailyTests` 테스트는 다시 돌지 않음). fixture NOW·RECORD·보유 AAA·BBB·관심 NEWW·extra SOXX 그대로. 격리 테스트는 `mock.patch.object(auto_core, "exposure_review_symbols", return_value={"SOXL"})`로 노출 검토 종목을 고정(기존 테스트는 patch 없음 → fixture 정책 `{}`로 격리 꺼짐).

daily (`BarIsolateDailyTests(base.DailyTests)`):
1. `test_watch_only_collection_failure_is_isolated` — NEWW `BAR_COLLECTION_FAILED:NEWW:1` → status OK, reasons `[]`, `isolated == [{"symbol": "NEWW", "reason": ...}]`, histories AAA·BBB·SOXX(NEWW 없음), 노출 실행기 1회·`steps.exposure.status OK`, warnings는 reconcile의 것 그대로, 결과 스키마 통과
2. `test_close_history_failure_is_isolated` (`CLOSE_HISTORY_FAILED:NEWW:x`), `test_exchange_unresolved_is_isolated` (실제 `resolve_exchange`가 `EXCHANGE_UNRESOLVED:NEWW`) → 각각 격리
3. `test_held_symbol_failure_still_fails` (AAA → FAIL), `test_extra_symbol_failure_still_fails` (SOXX → FAIL, patch {"SOXL"}), `test_watch_member_that_is_a_configured_extra_still_fails` (extra에 NEWW를 더하면 NEWW 실패 → FAIL: 보유·노출·기준 어느 쪽도 아닌 종목으로 extra 제외만 보임 — SOXX는 RREC_BENCHMARK이기도 해서 추가)
4. `test_exposure_review_symbol_failure_still_fails` (patch {"SOXL", "NEWW"} → FAIL), `test_decide_benchmark_failure_still_fails` (`auto_core_rules.C["RREC_POWER_BENCHMARK"] = "NEWW"` patch → FAIL)
5. `test_run_wide_reason_still_fails` (NEWW `SESSION_CALENDAR_UNAVAILABLE:x` → FAIL), `test_non_step_failure_still_fails` (NEWW `RuntimeError` → FAIL `UNEXPECTED_ERROR:RuntimeError...`)
6. `test_unreadable_exposure_settings_turn_isolation_off` (patch 없음: fixture 정책 `{}`에서 `exposure_review_symbols`가 예외, NEWW 실패 → FAIL), `test_exposure_review_symbols_are_settings_and_ledger_holdings` (patch 없이 실제 함수: decide 테스트가 읽는 alert 정책(읽기만)으로 benchmark·supplement + 장부 복원 보유 AAA·BBB, 그리고 `isolatable_symbols == {"NEWW"} − 그 집합`)
7. `test_no_failure_keeps_bars_as_before` — 실패 없으면 `steps.bars` 키가 정확히 {"status", "histories"}

decide (`BarIsolateDecideTests`):
8. `test_isolated_watch_symbol_gets_no_buy_and_one_alert` — env는 아래 3절. 격리 run에서 MU 매수 주문표 0건(주문표는 격리 없는 run의 주문표에서 MU를 뺀 것과 같음), `redeploy_ranking` 결과에 MU 없음, 주문표 `swap_pair`에 MU 없음, `symbols.MU` UNK·`BARS_ISOLATED`, `env.bars["MU"]["status"]`가 여전히 OK(불러온 dict 안 바뀜), alerts `T1_BARS_ISOLATED` 정확히 1건(push True, 줄 전문 한국어 대조, 사유 문자열 없음), 보유 매도(sell 주문표·후보·막힘·SOXL/SOXX evidence sell)가 'MU를 재배치 후보에서 뺀' 격리 없는 run과 같음. 격리 없는 run에서 MU가 재배치 후보였음을 단언(배제가 실제임을 보임)
   - `test_two_isolated_symbols_share_one_alert` — 두 종목은 알림 1줄 "MU, ZZZZ"
9. `test_invalid_isolated_entries_fail` — reason 누락·여분 키·소문자·빈 symbol·reason 비문자열·보유 SOXL·기준 SOXX·중복·빈 list·list 아님·bars가 dict 아님 → 각각 status FAIL, reasons에 `T1_BARS_ISOLATED_INVALID`, 주문표 0
   - `test_t1_fail_is_still_a_hold` — 격리 항목이 있어도 T1 FAIL이면 HOLD `["T1_NOT_OK"]`(437행 경로 그대로)
10. `test_t1_without_isolated_key_decides_as_before` — 기존 fixture T1(`{"status": "OK"}`, steps 없음)과 `steps.bars`에 isolated 없는 T1의 decide 결과(status·reasons·symbols·evidence·buy_requirements·candidates·blocked·no_action·alerts·exposure·주문표)가 같음. 주문표의 `inputs`만 뺌(T1 파일 sha256이 파일 바이트로 달라짐)

## 3. 테스트 8의 env

`test_auto_core_decide.py` 390~397행 `TicketFlowTests.test_compare_ticket_is_not_for_entry`와 같은 env: `Env(holdings={"SOXL": 10})` + `env.write_good_news()`. 보유는 SOXL 10주(현금 30000), 관심 명단은 MU 하나(cardStatus 수락, sector B1 → decide 기준 종목은 SOXX뿐). `write_good_news`가 MU에 새 공식 호재 사실(SEC_FILING, criterion_a, 카드 트리거 U2)과 '실적 미발표 확인'을 연구 기록에 넣어, 격리 없으면 MU 매수 주문표 1건(compare 모드)이 나온다. 격리 있는/없는 실행은 각각 새 Env(compare 모드)로 했다. 격리 없는 run에서 MU는 `redeploy_ranking` 결과에 들어 있으므로(단언함) 매도 비교 기준은 `redeploy_ranking` 결과에서 MU를 뺀 격리 없는 run이다.

재배치 후보 확인 칸: `redeploy_ranking`(auto_core_decide.py 현 1262행)을 감싼 `mock.patch.object(..., side_effect=...)`로 실제 결과를 받아 MU가 없음을 확인했고, decision 쪽에서는 그것이 보이는 유일한 칸인 매도 주문표의 `swap_pair`(auto_core_tickets.py 1295~1312행)에 MU가 없음을 확인했다.

## 4. 테스트 결과

- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_bar_isolate.py"` → Ran 18, OK
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` → **Ran 622, OK (skipped=1)**. skip 1건은 기존 `test_auto_core_replay.py` 186행(저장된 30분봉이 본 저장소에만 있음, worktree에서는 skip)
- `test_auto_core.py` `test_first_failure_stops_the_run`(보유 AAA가 먼저 실패)는 고치지 않고 통과. `test_auto_core_hold_range.py`의 decide 해시 대조도 통과(격리 없는 날 decide 출력 불변)
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → PASS, errors []
- 변이 확인(바로 되돌림): daily의 격리 분기를 끄면 테스트 1·2(3건)가 `'FAIL' != 'OK'`로 실패, decide의 덮어쓰기를 끄면 테스트 8이 '매수 주문표 0건' 단언(`[{'ticket_id': 'AT-20261010-MU-1', ...}] != []`)에서 실패
- 줄바꿈: `git diff --stat`과 `git diff --ignore-cr-at-eol --stat`가 같음(CRLF 유지). 두 스크립트 비 ASCII 0건

`git diff --ignore-cr-at-eol --stat` (새 테스트 파일·이 보고는 추적 전이라 빠짐):

```
 manage-us-stock-strategy/scripts/auto_core.py      | 108 +++++++++++++++++----
 .../scripts/auto_core_decide.py                    |  58 ++++++++++-
 2 files changed, 143 insertions(+), 23 deletions(-)
```

## 5. 남은 위험

- 수집 시간 초과(`subprocess.TimeoutExpired`, collect_bars `timeout=3600`)는 `StepFailure`가 아니므로 여전히 run 전체 FAIL(`UNEXPECTED_ERROR`)이다.
- 같은 종목이 여러 날 격리되면 그동안 그 종목 매수가 계속 막힌다(알림은 매일 1줄). 이력을 갱신하지 않으므로 다음 성공 수집은 마지막 이력 세션부터 다시 받는다.
- 노출 설정(alert 정책 S5 절)·상태·장부 읽기가 실패하는 날은 격리가 꺼진다(지금처럼 첫 실패에서 FAIL).
- 격리 판정의 노출 검토 종목은 `paths["alert"]`·`paths["state"]`(운영 기본값 = 노출 검토 기본 경로)로 읽는다. 둘이 갈라지는 경로는 테스트 주입뿐이다.
- 07:45 decide가 T1 뒤 관심 명단이 바뀐 종목을 격리 목록에서 만나면(명단에 없음) 덮어쓰기 대상이 아니어서 무시되고 알림 줄에만 나온다.
- 08:40 독립 대조(`docs/claude/t2rc-oracle.py`)는 페이지를 직접 읽고 격리를 모른다. 격리 날 그 종목이 대조 쪽 후보로만 나오면 `missing_in_core`(1571행) → 알림 ⑫ "독립 대조 MISMATCH"가 날 수 있다(아래 연결표 3행, 별도 승인 경로).

## 6. 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| T1 결과 `steps.bars.isolated`(격리 종목·사유, 실패 날만) — workspace/outputs/auto-core/<날짜>/result.json·LATEST.json | 예약 InvestmentV2-AutoCore 화~토 06:15 KST(`register_auto_core_task.ps1` 25행) → `auto_core.py` daily 수집 루프(408~432행, 이번 변경) | 예약 InvestmentV2-AutoCoreDecide 07:45 KST(같은 파일 27행) → `auto_core_decide.py` `t1_isolated`(183~207행)·657~686행(이번 변경) | 그 종목 매수 요건 UNK·매수 주문표 없음·재배치 후보 제외. 보유 매도·노출 E·줄이기 판정은 계속(지금은 전부 없음) | 아래 알림 행. decide가 격리를 못 읽으면 저장된 최신 페이지로 그 종목 매수 판정이 날 수 있다(collect_30m.ps1 43~67행 최신부터 저장) — 막는 것은 decide 덮어쓰기와 새 테스트 8뿐 | 연결 |
| decide `alerts`의 예외 `T1_BARS_ISOLATED`(push) | `auto_core_decide.py` 예외(680~686행) → alerts(366~367행 경로), 07:45 KST | 자동 운영 코어 결과 알림 trig_01D5KxMSJgbeRG1ZL5ox3Fna 화~토 08:50(`docs/claude/scheduled-prompts/auto-core-alert.txt` 42행 ⑦, `auto-core-alert/read.py` 44행 'D PUSH') + 사장실 알림 올리기 — 아침 trig_01KkJL5f5ttgyM2NT2xSC5Vk 09:05 재사용 | 사장 폰 알림 1줄·사장실 글 → Cowork가 수집 실패 원인 확인(키움 자료 범위·조회 제한) | 알림 예약이 돌았으나 실패하면 사장실 결과 모음 trig_01GrAs6UCfspeTBK3mMncyrd(월~토 09:35)·trig_01XChapmUEKxAcjKF9AFiERJ(일 10:05)(`docs/claude/active-decisions.md` 62행)이 "실패"로 이름을 올림(`docs/claude/scheduled-prompts/room-digest.txt` 2행 '08:50 코어 알림 … "돌았는지"만 본다', 5행 list_triggers last_run 상태가 SUCCEEDED가 아니면 "실패" 후보, 28행 '실패 <이름들>'). 아예 안 돈 날은 끊김 — 같은 지시문 2) 표(7~20행)에 08:50 알림 행이 없어 이름으로 안 나오고 "예약 N개 돌았음" 수로만 보임 · 메울 변경: room-digest 2) 표에 '코어 결과 알림 화~토 08:50' 행 추가 · 승인 경로: 결과 모음 지시문은 그 예약이 글을 올리는 알림 스레드의 카드 탭으로만 바뀜(active-decisions.md 62행), bar-isolate 범위 밖·기존 끊김. 알림 줄 회귀는 새 테스트 8(`manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py` 228~255행) | 연결(안 돈 날 감지는 끊김 — ⑤) |
| decide `candidates`(격리 종목 없음) | `auto_core_decide.py` 762행(`candidates=session["planned"]["candidates"]`) · 예약 InvestmentV2-AutoCoreDecide 07:45 KST(`manage-us-stock-strategy/scripts/register_auto_core_task.ps1` 27행) | 독립 대조 08:40(`docs/claude/t2rc-oracle.py` 214행 페이지 직접 읽음·1569~1571행 `missing_in_core`) → `auto-core-alert.txt` 47행 ⑫ | 격리 날 그 종목이 대조 쪽 후보로 나오면 거짓 MISMATCH 알림 → Cowork 확인 | ⑫ 알림 자체로 보임(`docs/claude/scheduled-prompts/auto-core-alert.txt` 47행 ⑫ 'VERDICT가 MISMATCH 또는 ERROR → "독립 대조 <VERDICT>(…) — Cowork 확인"', D PUSH 격리 줄과 같은 날) | 끊김 — 메울 변경: t2rc-oracle가 T1 `steps.bars.isolated` 종목을 비교에서 뺌 · 승인 경로: 예약 작업 변경(사장 직접 입력 승인), bar-isolate 병합 뒤 따로 제안 |

연결표 ②③의 auto_core·decide 행 번호와 register_auto_core_task.ps1 25·27행, t2rc-oracle.py 1571행은 이 세션에서 열어 확인했다. 수정 1회차에서 auto_core_decide.py 762행, register_auto_core_task.ps1 27행, auto-core-alert.txt 42·47행, room-digest.txt 2·5·7~20·28행, active-decisions.md 62행, 새 테스트 228~255행을 열어 확인했다. collect_30m.ps1 43~67행, read.py 44행, t2rc-oracle.py 214행은 지시문의 인용을 그대로 옮겼고 이 세션에서 다시 열지 않았다(Judge G9 대조 대상).
