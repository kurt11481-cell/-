---
id: t1-safety-builder-prompt
title: "켜" 전 안전 수정 2건 — HOLD/FAIL 날 EV4 유실(judge2 G 5) · F6 중복 ord_no(judge2 G 2, r4 F)
date: 2026-10-13
class: 권한 경로(auto_core*.py) — dev-run class authority(경로 때문). 의미: fail-open 경계 2곳을 막는 쪽으로만 좁힘. 관문 기준값·주문표 수량/가격 규칙 불변
decision: 사용자 "결정 autocore-on: 1"(2026-10-13 21:01 KST) — docs/claude/autocore-on-decision-2026-10-13.md 2-1
evidence: docs/claude/redesign-t2-judge2-report-2026-10-11.md G절 "켜" 전 2·5
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 t1-safety -ApproveAuthority — 경로 때문에 붙는 플래그)
---

```dev-run
{"task_id": "t1-safety", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/scripts/auto_core_rules.py", "manage-us-stock-strategy/schemas/auto-core-decision.schema.json", "manage-us-stock-strategy/tests/test_auto_core_t1_safety.py", "docs/claude/t1-safety-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core decide): EV4 of sessions whose record ended before F1 is rebuilt or held; F6 duplicate ord_no rows fail closed"}
```

[Claude Code 실행 권장] 모델: Opus · 추론 노력: high · 세션: 파이프라인 헤드리스(dev-run) · 이유: 판정 코어 fail-open 경계 수정

## 목표

T1(기록 모드)을 켜기 전에, 판정 코어(decide)가 위험 신호를 조용히 놓치는 경계 2곳을 막는 쪽으로 고친다. 그 밖의 동작은 한 글자도 바꾸지 않는다.

## 수정 1 — HOLD/FAIL로 F1 전에 끝난 날의 EV4 유실 (judge2 G 5)

현재: 지난 세션의 EV4는 F1까지 간 기록의 `account.ev4_open`에서만 모은다(`auto_core_decide.py` 610~611행 `ev4_sessions`). 기록이 F1 전에 끝났거나(DecideFailure·kill·입력 누락) 그날 decide 기록이 아예 없으면, 그 세션에 계좌가 EV4 선(`rules.ev4_open`: 총자산 ≤ V6 1차 선 또는 ≤ S7 hwm × 0.9) 아래였어도 R-REC1 사건 목록에 들어가지 않는다(fail-open).

바꿀 것:
1. **대상 세션**: R-REC1 창(평가 세션까지 60세션) 안, **첫 decide 기록의 evaluation_session 이후**(그 전 세션은 대상 아님 — 결정 기록 도입 전), 오늘 평가 세션보다 앞선 세션 중 `account.ev4_open`이 bool로 남은 기록이 없는 세션.
2. **다시 구하기**: 그 세션을 evaluation_session으로 가진 run day(달력상 그 세션 다음 KST 실행일)의 auto-core 폴더 `kiwoom_broker_snapshot.shadow.json`(T1 daily가 씀)과 그 세션의 종가(decide가 이미 읽은 bars의 raw 종가)로 F1과 **같은 함수**(equity_cash → tickets.rule_file_nominal → rules.ev4_open)를 써서 EV4를 계산한다. S7 hwm은 그 기록의 값이 있으면 그것, 없으면 오늘 결정에 쓰는 S7 hwm. 새 계산 경로를 만들지 말고 F1과 같은 코드를 부른다(복제 금지).
3. **못 구하면**(스냅샷 없음·종가 없음·보유 종목 봉 없음): 그 세션의 앞뒤로 구할 수 있는 가장 가까운 세션 총자산 중 하나라도 EV4 선의 1.03배 이내이면(= `rules.ev4_open(total / Decimal("1.03"), hwm)`이 True, V6 접근선과 같은 3% 여유) **EV4 열림으로 본다**(보수적). 아니면 열림 아님. 어느 쪽이든 결정 기록에 `ev4_backfill` 목록(세션·방법 REBUILT|NEIGHBOR_NEAR|NEIGHBOR_CLEAR·결과)을 남기고, 못 구한 세션이 하나라도 있으면 alerts에 push 줄 하나(`EV4_UNDETERMINED:<세션들>`).
4. 다시 구한 EV4 열림 세션은 기존 `ev4_sessions`에 더한다(908행 `ev4_all`로 R-REC1에 들어감). 리플레이(auto_core_replay)는 바꾸지 않는다(리플레이는 이미 세션마다 계산).
5. 스키마가 결정 기록 최상위 키를 막으면 `ev4_backfill`만 선택 속성으로 추가.

## 수정 2 — F6 같은 날 조회 안의 중복 ord_no (judge2 G 2, r4 F)

현재: `auto_core_tickets.ticket_rows`(531~562행)는 같은 (ord_dt, ord_no) 행이 두 번 오면 둘 다 더해 수량을 두 배로 센다. 체결분은 T1 대조가 잡지만 미체결은 "changed"로 잘못 분류된다.

바꿀 것: T1의 `FILL_ROW_DUPLICATE_CONFLICT`(auto_core_reconcile.py 291~294행)와 같은 규칙 — 같은 (ord_dt, ord_no)가 **완전히 같은 행**이면 한 번만 쓰고, **다른 행**이면 그 주문표 결과를 unknown으로 두고 note `ORD_NO_DUPLICATE_CONFLICT`(지금 `ORD_NO_UNREADABLE`처럼 fail closed). 그 밖의 분류 규칙은 그대로.

## 테스트 — 새 파일 `manage-us-stock-strategy/tests/test_auto_core_t1_safety.py`

기존 픽스처(tests/fixtures/auto_core_t2/helpers.py, test_auto_core_tickets.py의 Scenario 방식)를 참고한다.
- S1 전날 기록이 F1 전에 끝남(account 없음) + 그날 스냅샷 총자산이 EV4 선 아래 → 오늘 R-REC1 사건 목록에 그 세션 EV4, `ev4_backfill` REBUILT.
- S2 같은데 총자산이 선 위 → EV4 없음, REBUILT·결과 false, 다른 결과 불변(골든).
- S3 그날 기록·스냅샷 둘 다 없음 + 이웃 총자산이 선의 1.03배 이내 → EV4 열림(NEIGHBOR_NEAR) + alert push `EV4_UNDETERMINED`.
- S4 S3인데 이웃이 멀다 → 열림 아님(NEIGHBOR_CLEAR) + alert push.
- S5 첫 decide 기록 이전 세션은 대상 아님(기존 픽스처 결과 불변).
- S6 모든 기록이 F1까지 감(정상 운영) → `ev4_backfill` [] 이고 결정 기록의 나머지 값(주문표·관문·shock·account)이 변경 전과 같다.
- F1 같은 (ord_dt, ord_no) 같은 행 2번 → 한 번만 셈(수량 두 배 아님).
- F2 같은 (ord_dt, ord_no) 다른 행 → outcome unknown, note ORD_NO_DUPLICATE_CONFLICT.
- F3 중복 없음 → 변경 전과 같은 분류.
- 기존 테스트 파일은 고치지 않는다. 깨지면 멈추고 BLOCKED.md에 이유를 적는다.

## 지켜야 할 것

1. 바뀐 파일은 dev-run allowed_paths 안. auto_core_compare·replay·reconcile·inputs·bars는 바꾸지 않는다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY` 줄을 만들거나 바꾸지 않는다. 주문 경로 문자열 없음. 키움·auto_core.py 실행 없음(테스트는 -p "test_auto_core*.py").
3. 관문 기준값(rules.CONSTANTS·tickets 상수·POLICY_EXPECTED)·주문표 수량/가격·EV1~EV5 정의·RG1~RG4 불변. 새 상수는 위 1.03(V6 접근선과 같은 값)이 기존 상수에서 오면 그것을 쓰고, 없을 때만 auto_core_rules CONSTANTS에 출처 문장과 함께 하나 추가.
4. 스크립트 ASCII만(한국어는 \u 이스케이프). 커밋은 파이프라인이 한다.

## 보고 `docs/claude/t1-safety-report.md`

바꾼 함수·줄, 두 규칙 한 문단씩, 테스트 목록·결과(대상·전체 새 실패 0), 실데이터(읽기 전용): 2026-10-13 결정 기록 입력으로 오늘 결정을 다시 만들었을 때 ev4_backfill과 shock이 어떻게 되는지(10/12 세션 이전은 첫 기록 이전이라 대상 아님 예상), 남은 위험.

## Judge 확인 항목

1. 범위: allowed_paths 안, 다른 동작 불변(S6 골든).
2. 수정 1: F1과 같은 함수를 부른다(복제 없음). 대상 세션 범위(첫 기록 이후·창 안·평가 세션 앞). 못 구한 세션은 3% 이웃 규칙으로 보수적, push 줄 있음. fail-open 남은 경로가 있으면 적는다.
3. 수정 2: 같은 행 1번, 다른 행 unknown — T1 규칙과 같다.
4. 권한 표지·주문 경로·정책/상태 쓰기·키움 호출 없음. 대상·전체 테스트 새 실패 0.
