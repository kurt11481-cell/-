---
id: recon-dt-judge-report
title: "recon-dt 독립 Judge 보고 (읽기 전용, Opus xhigh, Read·Grep·Glob)"
date: "2026-10-23"
verdict: PASS
source: "workspace/outputs/dev-runs/recon-dt/judge-1.json (Judge 출력 원문을 Cowork 비서실이 옮김, 10:26 KST 종료, 43턴)"
inputs: "worktree .claude/worktrees/recon-dt (base e33756c, 커밋 전 변경) · judge-input: builder 지시문·fix-1·diff.patch·tests-base/after·fail-compare"
---

# recon-dt Judge 결과 (커밋 1 + fix-1 픽스처 수정)

결론: 6개 항목 모두 PASS이고, 막는 문제는 없습니다. 아래 근거는 전부 이번 세션에서 직접 연 파일에서 확인했습니다.

## 항목별 판정

**1. `auto_core_reconcile.py` 변경 범위 — PASS**
- diff.patch의 이 파일 hunk는 6개이고, 줄 번호 오프셋(+4, +6, +19, +29, +35)이 서로 맞습니다. 숨은 변경은 없습니다.
- 바뀐 곳은 다음뿐입니다.
  - 상수 `US_DAY_OPEN/CLOSE`와 근거 주석: `auto_core_reconcile.py:92-95`
  - `plan_reads` 독스트링만 바뀌고 계산은 그대로: `:189-198`
  - 체결·주문 시각의 KST 날짜를 정하는 `_kst_moment`: `:249-257`
  - `parse_fills` 독스트링과 판정 블록: `:261-264`, `:305-319`. 기록되는 `session_date`는 D입니다(`:319`).
  - `fills_after_snapshot`: `:329-332`
  - `run_auto`에 한 줄 추가: `:1005`
- 바뀌지 않은 것:
  - `CASH_TOLERANCE_USD`(`:66`)
  - `FILL_WINDOW_MAXIMUM_DAYS`(`:82`)
  - `explain_change`의 I2·I3 판정식(`:738-783`)
  - 정산 규칙(`:452-589`)
  - `flow_cash`(`:623-678`)
- `cash_flow_evidence.py`는 git status에 없으므로 바뀌지 않았습니다.

**2. 새 규칙은 판정을 느슨하게 하지 않음 — PASS**
- 오류가 HOLD로 이어지는 경로를 코드에서 따라가 확인했습니다.
  1. `parse_fills`의 오류 목록과 스냅숏 뒤 체결 오류가 `fill_errors`에 모입니다(`:999`, `:1005`).
  2. 이것이 I2 사유가 되어 I2가 FAIL이 됩니다(`i2_reasons = list(fill_errors)` `:740`, `:785`).
  3. 실패한 불변 조건이 사유 목록에 들어갑니다(`:1084-1085`).
  4. 기록이 막힙니다: `recordable=False`, `would_apply=None`, apply 조건 불충족(`:1089-1094`).
  5. 최종 상태는 `"HOLD"`입니다(`:1108`).
- 판단이 안 되는 경우(후보 0개 또는 2개)는 `None`을 돌려 오류가 됩니다(`:257`).
- 테스트로 확인된 것:
  - 창 밖 체결: `test_auto_core_reconcile_orddt.py:104-115`
  - 주문이 체결보다 늦거나, 창 밖이거나, 비어 있는 경우: `:117-124`
  - 스냅숏 뒤 체결: `:132-136`
  - 끝까지 돌린 HOLD와 `applied None`: `:215-222`

**3. 10-21 ET 주문일 재현과 경계 사례 — PASS**
- 시간외 4건은 KST 10/22, 정규장 3건은 KST 10/21, `session_date`는 모두 10/21입니다(`:62-76`). EDT 창(KST 17:00~익일 09:00)으로 직접 다시 계산해도 같습니다.
- 기록 시각 10/21 06:15:04 뒤로 MVLL을 포함한 7건이 모두 잡힙니다(`:78-85`).
- 경계 사례:
  - 자정 넘김: `:87-91`
  - EST(KST 08:30·10:00 포함, 10:30·17:59:59 창 밖)와 EDT 대비: `:93-110`
  - 키움 주간거래(KST 12:00): `:112-115`
  - 예약 주문 허용: `:126-130`
- 10-23 재생(`:173-181`): I2 PASS(7건), I3 사유는 `CASH_CHANGE_NOT_EXPLAINED:-82.93` 하나, FILL_AMOUNT_UNAVAILABLE 없음. 직접 다시 계산했습니다.
  - 수량: 모든 종목에서 기록 수량 + 체결 순증감 = 브로커 수량
  - 총액: 매도 8580, 매수 4915
  - 수수료 범위 안: 8.58 ≤ 43.4, 2.46 ≤ 25.08
  - 정산 금액: 3653.96
  - 잔차: −82.93

**4. `test_auto_core.py` 수정 — PASS**
- 바뀐 것은 정확히 두 줄입니다(diff hunk `-1409,9 +1409,10`).
  - 주석 한 줄 추가: `test_auto_core.py:1412`
  - 픽스처 키 `"20261015"` → `"20261014"`: `:1415`
- 기대값(`:1427-1437`)과 day_trades 키 `"20261014"`(`:1417`)는 그대로입니다.
- 기존 주석(`:1410`, "U.S. 10/14 session … KST 10/15 07:07")과 새 규칙이 맞습니다. 새 규칙으로 계산해도 체결 시각은 KST 10/15 07:07, 세션은 10/14로 수정 전과 같습니다.

**5. 권한 줄·매도 차단·파일 범위·줄바꿈·전체 테스트 — PASS**
- 권한 줄: diff에서 `order_authority`, `quantity_authority`, `execution_quantity`, `kill_switch`, `ORDER_TICKET_HUMAN_ENTRY`가 든 `+`/`-` 줄은 0건입니다. `kill_switch`는 hunk 머리글(문맥)에만 나옵니다. 새 테스트 파일에도 이 단어는 없습니다.
- 매도 차단: 관문 코드는 바뀌지 않았습니다. 새 HOLD 사유는 기존 `G1_RECONCILE_NOT_OK` 관문(`auto_core_decide.py:549-550`, `auto_core_tickets.py:782`)으로만 들어갑니다.
- 파일 범위: git status에 있는 것은 수정 3개와 새 파일 2개뿐이고, 모두 허용 목록(fix-1에서 추가된 `test_auto_core.py` 포함) 안입니다. `auto_core_tickets.py`는 바뀌지 않았습니다.
- 줄바꿈: 수정된 세 파일은 전 줄이 CR로 끝납니다. 세 파일 모두 CR 줄 수와 전체 줄 수가 같아 섞임이 없습니다(1617/1617, 1257/1257, 326/326).
- 전체 테스트(`tests-after.txt:445-447`): 3295건, 실패 22, 오류 9.
  - `fail-compare.txt`에서 기준선에만 있던 실패(GONE)는 0건입니다. 기준선 실패 6건(`tests-base.txt:4-65`)은 이후에도 모두 그대로 있습니다.
  - 이후에 새로 보이는 25건은 이번 변경과 무관한 환경 차이로 보입니다. 근거: 사유가 모두 worktree에 없는 workspace 자료 때문이고(`FileNotFoundError`, `source artifact missing`, acceptance manifest `matches=[]`), 해당 14개 모듈은 바뀐 파일(`auto_core_reconcile`, `parse_fills`, `broker-snapshot-reconciliation`, `test_auto_core`)을 참조하지 않습니다(grep 0건).
  - `test_auto_core*` 쪽 실패는 기준선과 같은 PLTR 1건뿐입니다.

**6. 보고서 필수 항목 — PASS**
- (a) 키움 사양에 ord_dt 시간대 문구가 없고 실관측으로만 확정, 주간거래 체결은 관측 없음(창 밖 → HOLD): `recon-dt-report.md:81`
- (b) 고친 뒤에도 10-23은 출금 −82.93 때문에 HOLD(cashflow-api-gap): `:82`
- (c) 11/03 실행부터 FILL_WINDOW_TOO_LONG: `:83`. 다시 계산하면 10/20~11/03은 15일로 14일을 넘습니다.
- (d) flow_cash의 deal_dt KST 가정 미수정: `:42-43`, `:84`
- 정산일 규칙이 여전히 성립한다는 확인도 있습니다: `:39-40`

## 발견 사항

**막는 문제 (blocking): 없음**

**참고 사항 (non-blocking)**
1. 10-23 재생 테스트는 `explain_change` 단계까지만 돌립니다. HOLD와 상태 미기록은 코드 추적(`auto_core_reconcile.py:1084-1108`)으로만 확인됩니다. 실행 전체를 돌려 HOLD와 `applied None`을 확인하는 테스트는 FILL_AFTER_SNAPSHOT 사례(`orddt.py:215-222`)뿐입니다.
2. `FILL_SESSION_DATE_MISMATCH`(`:314-316`)는 구조상 도달할 수 없는 방어 검사라 테스트가 없습니다. 해는 없습니다.
3. 새 테스트 파일만 작업 트리에서 LF입니다(CR 0줄). 지킬 기존 줄바꿈이 없는 새 파일이라 위반은 아니지만, Cowork가 커밋할 때 참고하면 됩니다.
4. 같은 환경 기준선(worktree에서 실패 22·오류 9)은 Builder가 보고한 수치이고 이름 목록 원본은 없습니다. 이름 단위 대조는 메인 체크아웃 기준선과의 비교와 참조 grep으로 대신했습니다. 같은 환경 기준의 이름 대조는 "확인 필요"로 남깁니다. 다만 결론을 바꿀 근거는 없습니다.
5. 보고서의 행 번호 몇 곳이 조금 어긋납니다. 실질 내용은 맞습니다.
   - 참조 문서 "231~241" → 실제 232~243
   - flow_cash "615~639" → 실제 623~678
   - reconcile_mismatch "tickets:682~690" → 실제 680~688, 사유가 나오는 곳은 `auto_core_decide.py:244-246`
6. 남은 위험(보고서 f): 커밋 1만 들어가면 주문표 귀속(KST 가정)과 대조의 `session_date`가 어긋날 수 있습니다. 조용히 틀리지 않고 `OUTCOME_MISMATCH_WITH_RECONCILE`로 드러납니다(`auto_core_decide.py:244-246`). 커밋 2 후속이 필요합니다.
7. 새 HOLD 사유는 기존 G1 관문을 통해 모든 주문표에 붙습니다. 관문 규칙 변경은 아니지만, 이상 행이 있는 날에는 HOLD 원인이 늘 수 있습니다.
8. 출금액이 목표 절(−82.95)과 테스트 절(−82.93)에서 다릅니다. 보고서가 이미 짚었고(`:82`), 실제 값은 실행 결과로 확인해야 합니다.

VERDICT: PASS
