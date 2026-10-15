---
id: t2rc-judge3-report-2026-10-15
title: t2-rc 독립 Judge 3차 보고 — 2차 FAIL 계산기 4건 재판정 (읽기 전용)
date: 2026-10-15 KST (HEAD ef3bad1, 계산기·실행기는 작업 트리 수정본)
class: K3 판정 기준(T2 켜 조건 B+) 장치 재검토. 파일 수정 없음 — 이 보고서 1개만 씀
model: Opus 5.5 · high · Claude Code 새 세션(메인 체크아웃). 계산기를 고친 Cowork 세션과 다른 세션
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: 관제판 t2-rc · t2-rc 적용 승인 세션 · t2-rc-preregistration-2026-10-14.md 변경 기록
지시: docs/claude/t2rc-judge3-prompt-2026-10-15.md · 2차 보고: docs/claude/t2rc-judge2-report-2026-10-15.md
---

# t2-rc 독립 Judge 3차 보고

## 0. 결론
- **VERDICT PASS.** 2차 10절의 4건이 모두 고쳐졌다. 바뀐 4곳에서 새로 생긴 거짓 일치·거짓 허락 길은 없다. 2차 PASS 항목도 뒤집히지 않았다.
  - **⅓ 수량:** 정수 분수로 계산한다(:59, :1138-1139). 코어 step_quantity(tickets:304-305)와 비교했다.
    - 1~3000 전 행: 차이 0건. 옛 판은 556건이었다.
    - 무작위 20만 건(매수·매도, 교체 후보 포함), 고른 수량: 차이 0건. 옛 판은 같은 표본에서 11,651건이었다.
  - **C1 가드:** apply_gap_guard(:1545-1560)는 MATCH만 NOT_CHECKED로 바꾼다.
    - MISMATCH는 그대로다. 그래서 counts_for_c1이 true가 되고(:1540), 종료 코드는 2다(:2036). 알림 ⑫로 간다(alert v2.2:127).
  - **EV4 현금:** equity_cash_t2(:1644-1665)는 코어 equity_cash(decide:141-163)와 order_available_cash_errors(kiwoom_broker_shadow:252-267, 허용 $1 :43)와 같은 값을 낸다.
    - 무작위 30만 건(±$1 경계, 값 없음, 보유 행 None 포함): 차이 0건.
    - 실자료 10-13 self-check 총자산 27,695.1487은 코어 account.total과 같다. 옛 판은 24,622.6487이었다.
    - 10-14 총자산 27,750.0403, 10-15 총자산 25,548.2229도 코어와 같다.
  - **C7:** 이제 `<`이다(:576). 코어 _base_index(rules:436)와 같다.
    - 무작위 5만 건 중 16:00:00 사례가 8,209건이었다. 차이 0건. 옛 판은 5,584건이었다.
    - selftest G-9 PASS.
- **기본 처분:** 이 판정으로 상태가 바뀌는 것은 없다. 적용은 사용자 승인 묶음(5절)으로 한다. 승인 전까지는 옛 R-C 유지, T2 비교 모드 유지다. 노출·예산·권한 변화 없음. 주간 사용자 손 0.

## 1. 시작 조건
- 지시문 표 sha256 7개가 모두 일치한다. 계산기·실행기는 CR 0개(LF)다. FAIL로 적을 파일은 없다.
- HEAD의 계산기 = ae4a1e8e…(2차 판)다. 작업 트리 diff는 계산기 4곳 + selftest G-6~G-9, 실행기 :16 한 줄이다.

## 2. 판정 표
| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| 1-1 ⅓ 단계 수량 | PASS | t2rc-oracle.py:59 STEP_FRAC, :1138-1139 `int(delta) * sn // sd` = tickets:304-305 `floor(delta * Fraction)`. delta는 정수이고 > 0이다(:1956, :1961). 스크래치: 1~3000 행 0건, 무작위 20만 건 고른 수량 0건(옛 판 556·11,651). selftest G-6(:2152-2156) PASS |
| 1-2 C1 가드 | PASS | :1524에서 MATCH/MISMATCH를 정한 뒤 :1536 → :1545-1560. MATCH만 NOT_CHECKED(ORACLE_DATA_GAP)다. MISMATCH는 그대로이고 reason에 덧붙인다. 주문표 match false·c2_item_match false는 그대로다. counts_for_c1(:1540)은 MISMATCH를 센다. 종료 2(:2036). alert v2.2:127 ⑫는 MISMATCH를 푸시한다. selftest G-7 PASS |
| 1-3 EV4 현금 | PASS | :1644-1665 = decide:141-163 + broker_shadow:43·:252-267. 사용 :1680 → total_assets_v6 → rrec1(:1823). 무작위 30만 건 0건. 10-13 self-check 27,695.1487(ORDER_AVAILABLE) = decision 10-13 account.total. 10-14·10-15도 같다 |
| 1-4 C7 경계 | PASS | :576 `<` = rules:436 `<`(1차 3-5 "앞"). 무작위 5만 건(16:00:00 8,209건) 0건(옛 판 5,584). selftest G-9 PASS |
| 2 새 거짓 일치·거짓 허락 길 | PASS | 3절. 4곳 모두 코어와 같은 값이거나 더 엄격하다. 가드는 MATCH만 낮춘다. 주문표 match false는 유지되므로 c3 entry_allowed가 새로 열리지 않는다(:1587, :1591) |
| 3 2차 PASS 항목 유지 | PASS | 4절. import(:24-33) 그대로, 새 import 없음. 쓰기는 --out(:2030) 1곳. 권한 표지 :1343·:2058. 코어·알림·사전 등록·115행 관련 파일 변경 없음. M1 재현 같음 |
| 4 실행기 고정값 | PASS | t2rc-check-run.ps1:16 = 5607b09b…f02a26 = 현 계산기 LF sha. HEAD 대비 diff는 이 한 줄뿐이다. 실행기 sha 5d3502b9… = 지시문 표 |

고칠 최소 항목: **없음.**

## 3. 새로 생긴 경로 (바뀐 4곳만)
- **⅓ 수량:**
  - 코어와 같은 정수 내림이다. 음수·소수 delta에서도 floor 방향이 같다. 다만 호출부에서 delta는 늘 정수이고 0보다 크다.
  - 매도 "1" 행은 이전과 같다(delta 그대로).
- **C1 가드:**
  - 덮어쓰기 방향이 "MATCH → NOT_CHECKED" 하나뿐이다. 진짜 불일치는 숨지 않는다.
  - 갭 종목 때문에 생기는 불일치는 MISMATCH로 남는다. 이것은 거짓 불일치(입력 금지 쪽)다. 이유는 reason의 ORACLE_DATA_GAP로 보인다.
- **EV4 현금:**
  - 사용자 결정 t2-equity-cash(redesign-t2-merge-decision-2026-10-12.md:90)의 읽기를 계산기 코드로 따로 구현했다. 코어 import는 없다.
  - 정의가 같으므로 현금 정의 자체의 독립 확인은 아니다. 정의는 사용자 승인 사항이라 독립성 요구 대상이 아니다.
  - 참고: fnum(:119-126)은 bool을 1.0으로 읽고, 코어 _decimal(auto_core_bars.py:39-44)은 None으로 읽는다. 실제 스냅숏 현금 칸에는 bool이 없고(:1289 스키마 검사), 갈려도 거짓 불일치 쪽이다.
- **C7:**
  - 코어와 같은 기준 종가다.
  - 참고(diff 밖, 2차부터 있던 것): 계산기는 달력에 없는 세션을 만나면 멈추고(:576-579 break), 코어는 건너뛴다(rules:434-437). 그래서 그런 날에는 기준이 더 이르다. 결과는 거짓 불일치 쪽이고, 거짓 일치 길은 아니다. 지금 달력에서는 해당이 없다.

## 4. 2차 PASS 항목 유지
- **독립성:** import 목록은 HEAD와 같다. subprocess·importlib·네트워크·코어 import는 grep 0건이다. https 문자열은 URL 형식 검사(:819, :959)뿐이다.
- **M2:** t2rc-register-task.ps1 sha e03e74e0… 그대로. `-PlanOnly`(Windows PowerShell 5.1.26100.9444) 출력은 2차와 같다: 화~토 08:40 · Korea Standard Time · LIMITED · INTERACTIVE · StartWhenAvailable · WakeToRun False · 15분 · IGNORE_NEW · TASK_EXISTS_BEFORE/AFTER NO · exit 0.
- **사전 등록:** e798b8c5… 그대로.
- **115행:** 규칙 v3.12.6 129f78af…, 대기 로더 915e1966… 그대로다. 현행 v3.12.5 3e05c8ef…, 현행 로더 206782f6…도 그대로다. manage-us-stock-strategy/ 작업 트리 diff 0.
- **알림:** 대기 v2.2 eb2b9710… 그대로, 현행 v2.1 66548192… 그대로.
- **M1 재현(이번 세션):**
  - selftest PASS. open 1건(90분위 28.2% 확인 필요)은 그대로다.
  - 10-13: NOT_CHECKED(DECIDE_AFTER_0840).
  - 10-14: MATCH, counts_for_c1 true.
  - 10-15: MATCH, counts_for_c1 true.
  - 10-13 self-check: INFO_MATCH.
  - 리플레이 REPRODUCED(P-R1·P-R2 각 65세션).
- **기록 정정(참고, FAIL 사유 아님):**
  - 수정 기록(t2rc-oracle-report 10절 재현 줄)에 "10-13 self-check INFO_MATCH(이전 판은 ⑤ 8종목 차이)"라고 적혀 있다. 그러나 새 판도 ⑤ 8종목 차이(코어 unk 대 계산기 no)가 그대로다.
  - 옛 판으로 같은 명령을 돌려도 같은 8건이 나온다.
  - 원인은 현금이 아니다. 10-13 코어 shock.rg1_coverage가 10-09 기록 누락으로 RG1 unk이기 때문이다(cmp-fix3 B4 분류).
  - 2차 보고 0절의 "그래서 ⑤ 칸이 8종목 모두 다르다"도 원인을 잘못 짚었다. 현금 차이가 실제로 바꾼 것은 총자산(24,622.65 → 27,695.15)과 EV4 열림 여부다.
  - 요건 칸 차이는 진단 표시이고 판정(:1523)에 들지 않는다. 두 값 모두 매수를 막는다.

## 5. 사용자 적용 승인 묶음 (2차 11절에서 바뀐 것만)
- **실행기 고정값:** 5607b09b47585a8b0799ae84b93cff434ebecdfc2b30f305607c8641b8f02a26 (t2rc-check-run.ps1:16, 실행기 sha 5d3502b9…). 2차의 "10절 수정 뒤 새 sha" 자리에 이 값을 넣는다. ae4a1e8e…는 쓰지 않는다.
- **사전 등록 변경 기록 문안:** 2차 문안 그대로다. C1 문안("불일치는 그대로 센다")은 이제 계산기 동작과 같다.
- **묶음 실행 순서:** 3차 Judge PASS(이 보고) → 승인 1번. 계산기 수정 단계는 끝났다.
- 그 밖(알림 v2.2 eb2b9710…, S1·S3·S6·S8 제안, PowerShell 등록 1번, 115행 재서명, 주간 사용자 손 0)은 2차 그대로다.
- **커밋 필요:** 계산기·실행기·수정 기록은 아직 미커밋이다(git status M 3개). 이 보고서도 docs/claude/ 문서라 23:30 문서 커밋 대상이다. 승인 세션에서 sha가 위 값과 같은지 다시 확인한다.

## 6. 남은 위험 (기본 처분 NO_CHANGE, 알림만)
- 2차 12절 그대로: ⑤ 알려진 이벤트, W*, G0, C1·C4·C5 집계 장치 없음, 실행기의 실제 5.1 실행 확인 필요, 센트 반올림 순서(예산 경계).
- 2차 권장 R1~R5와 코어 의견(reduce_items)은 하지 않았다. 지금 자료에서는 해당이 없다(수정 기록 10절).
- 3절의 달력 누락 break 차이는 diff 밖이고 거짓 불일치 쪽이다.

## 7. 실행 기록·자료 시점
- **시점:** 2026-10-15 오후 KST, HEAD ef3bad1. 결정 파일 10-13 · 10-14 · 10-15는 2차와 같다.
- **돌린 것**(결과는 세션 스크래치, 저장소 밖):
  - `python -I docs/claude/t2rc-oracle.py selftest --repo .` → PASS, exit 0
  - `check --day 2026-10-13 / 10-14 / 10-15 --out <scratch>` → NOT_CHECKED / MATCH / MATCH, exit 0
  - `check --day 2026-10-13 --ignore-input-sha` → INFO_MATCH, 총자산 27,695.1487
  - 옛 판(HEAD ae4a1e8e…를 스크래치로 꺼냄) 같은 self-check → 24,622.6487
  - `replay --replay-json workspace/outputs/auto-core/replay/prereg1009/replay.json` → REPRODUCED, exit 0
  - `t2rc-register-task.ps1 -PlanOnly` → exit 0
- **스크래치 시험**(계산기는 파일 경로로 읽었고, 코어 식은 원문 줄에서 옮겨 적음. 저장소 코드 import 없음):
  - steps_test: tickets:304-363
  - cash_test: decide:141-163, broker_shadow:43·252-267, bars:39-44
  - c7_test: rules:427-468
  - 새 판은 모두 0건 차이다. 옛 판은 556 / 11,651 / 5,584건이 달라서, 시험이 결함을 잡는 것도 확인했다.
- **판정이 바뀔 조건:**
  - 계산기·실행기 sha가 위 값과 다르면 PASS가 무효다.
  - 사용자가 t2-equity-cash와 다른 현금 정의를 승인하면 1-3을 다시 판정한다.
  - 사용자가 C7 16:00 정각을 "장 마감 뒤"로 정하면, 코어와 계산기를 함께 바꿔야 한다.

VERDICT: PASS
