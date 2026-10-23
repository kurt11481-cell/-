---
id: recon-hold-2026-10-23
title: "자동 대조 HOLD 2일째(10/22·10/23) 원인 — 체결 날짜 해석 + 출금 증거 없음"
date: "2026-10-23"
status: "결정됨 recon-dt a(2026-10-23 08:45) · (a) 수동 경로 Builder 실행 중 · (b) cashflow-api-gap 10/30까지 결정"
class: "고칠 곳 = 대조 불변 조건이 읽는 체결·현금 증거(auto_core_reconcile.py, references/broker-snapshot-reconciliation.md) → 권한·한도(K3): 사장 직접 승인 → 수동 경로 Builder(worktree) + 별도 읽기 전용 Judge(Opus) → 병합 결정"
authority: "order_authority=false · 상태 파일은 대조 통과 때만 자동 코어가 씀 · 이 문서는 읽기 전용 진단"
consumers: "관제판 recon-dt · r-wd-1022 · cashflow-api-gap · redesign-t2(C1·R2) · 08:50 코어 알림"
---

## 결론
HOLD는 안전하게 막힌 것(상태 불변)이고, 기다려도 풀리지 않는다. 원인 둘, 둘 다 고쳐야 풀린다.
- **A. 체결 날짜 해석 결함.** auto_core_reconcile.py 285~286행은 체결 시각을 "주문일(ord_dt) + cntr_time, KST"로 만든다(references/broker-snapshot-reconciliation.md 231행 같은 규칙). 키움 ust21150의 ord_dt는 **미국 주문일**이라, KST 이른 아침(미국 전날 시간외) 체결이 하루 앞당겨진다. MVLL 159주 매도(실제 10/22 06:13:18 KST — 10-22 06:15 스냅숏의 당일체결 ust21510에 처음 보임)가 10/21 06:13으로 계산돼 기준 시각(10/21 06:15:04 KST) 앞이 되고 fills_after(300~301행)에서 빠짐 → I2 "QUANTITY_CHANGE_NOT_EXPLAINED_BY_FILLS:MVLL". 같은 이유로 BE·NBIS의 session_date가 10-20으로 잘못 잡혀 체결 금액 0 → I3 "FILL_AMOUNT_UNAVAILABLE". T1 보고서(redesign-t1-builder-report-2026-10-10.md 33행)의 "ord_dt가 KST인지 미국 날짜인지 확인 필요"가 이것.
- **B. 출금 $82.93 증거 없음.** 거래내역 API(ust21100)에 출금이 안 나온다(cashflow-api-gap). A만 고치면 현금식이 150.01 − 82.93 − 정산 순액 150.03 = −82.95로 여전히 실패. 출금까지 넣으면 −0.02(허용 $1 안). 예수금 흐름 12,469.19 → 12,386.26(정확히 −82.93) → 0.01(SOXL 정산).
- 안전성: A는 체결을 빠뜨리기만 해서 늘 HOLD 쪽(잘못 기록되지 않음). 다만 그대로 두면 상태 파일이 계속 옛 값(MVLL 159·NBIS 13·SOXL 179)이고, 14일 조회 한도로 11/03 실행부터는 다른 실패로 바뀜(하위 에이전트 계산, 확인 필요).

## HOLD 동안 막히는 것
- decide: G1_RECONCILE_NOT_OK·G1_STATE_NOT_EQUAL_BROKER·G1_S7_FAIL_CLOSED → 주문표 0(비교 모드라 입력 대상은 원래 없음). G1 사유는 **매도 주문표에도 붙음**(auto_core_tickets.py 782·1063~1066행, 하위 에이전트) — "매도는 막지 않는다" 원칙과 어긋나는지 별도 검토 필요.
- 독립 대조: 10-22 t2rc-check ERROR — S7 equity None에서 docs/claude/t2rc-oracle.py 1734행 TypeError(하위 에이전트). 대조기가 판정 대신 죽는 것은 별도 결함.
- S7·HWM: 상태가 옛 값이라 오늘 S7 계산 불가. 통합점검(키움 잔고 기준)은 총자산 $21,488.74를 냈음.

## 선택지 (V3 순서)
| 안 | 내용 | 판단 |
|---|---|---|
| NO_CHANGE | HOLD 유지, 알림만 | 기본값. 상태가 매일 더 낡음 |
| REUSE | 확인 코드 경로(reconcile_broker_state.py apply + "확인 <코드>") | CLAUDE.md는 "T1 기록이 켜지기 전까지"만 허용 → 지금 쓰려면 권한 결정. 써도 출금은 NO_EXTERNAL_FLOW로 기록돼 HWM이 출금을 손실로 반영 → 비권장 |
| REPLACE(권장) | 한 K3 묶음: (a) ord_dt를 미국 주문일로 해석(KST 날짜 = ET 날짜가 ord_dt와 같은 쪽) + 참조 문서 231행 (b) 출금 증거 경로 — 예: 같은 조회에서 체결로 설명되지 않는 예수금 감소가 정확히 일치할 때 외부 흐름으로 인정(허용 범위 넓히기 금지) | 불변 조건을 완화하지 않고 정확하게 만듦. 사장 직접 승인 → Builder·Judge(Opus) → 병합 결정 |
| ADD | 사람이 출금을 선언 | r-wd-1022 사전 등록에서 제외(사람 선언 없음) |

## 바뀔 조건
- ord_dt가 KST라는 키움 명세·재조회 결과 → A 진단 철회.
- ust21100에 82.93 출금 행이 나중에 나타남 → B 해소, A만 남음.

검토 완결: 원문 확인 — auto_core_reconcile.py 280~301행, 10-22 스냅숏 MVLL fills[1](cntr_time 06:13:18), 참조 문서 229~232행, 10-23 reconcile.json(I2·I3·NO_EXTERNAL_FLOW)은 비서실이 직접 열어 확인 · 현금 재계산·tickets 782행·oracle 1734행·T1 보고 33행은 하위 에이전트 보고(파일 명시) · 내장 재검토 0회(이 문서는 착수 여부를 묻는 진단 — 설계안은 Builder 지시문 단계에서 재검토) · 미해결 2(매도 주문표 G1 차단, oracle 크래시) · 자료 시점 2026-10-23 06:15 KST 실행분.

## 독립 재검토 반영 (2026-10-23 08:2x, Opus, 6렌즈 — 결론 변경 1건)
- **근거 정정:** "10-22 스냅숏 fills[1]"은 당일체결 ust21510(날짜 칸 없음)이라 ord_dt 근거가 아님. 더 강한 근거(비서실 원문 확인): 10-23 reconcile.json fills에 order_date 20261021인 BE 19주(계산 06:15:28)·NBIS 13주(06:20:18)·BE 9주(06:40:50)가 있는데, 10-22 06:15 스냅숏에서는 BE 19주가 아직 '접수'(미체결), NBIS 13주가 보유 → 실제 체결은 10/22 KST. KST 해석이면 10/21 06:15~06:40 체결이 되어 모순 → **ord_dt = 미국 주문일**만 맞음. 키움 사양(usa ust21150)은 ord_dt를 "주문일자"로만 적어 시간대 확인 필요. 주간거래(KST 낮) 체결은 관측 없음 — 두 해석이 갈리는 구간이라 미검증.
- **범위 누락:** 같은 "ord_dt = KST" 가정이 auto_core_tickets.py 520~533행(주문표 order_days 독스트링 "KST order days (ust21150 ord_dt)")·559~604행, auto_core_decide.py 199행, 참조 문서 215행에도 있음 → (a)에 포함.
- **(a) 정밀 규칙:** D = ord_dt(ET 거래일). cntr_time·ord_time 각각 KST 날짜 k ∈ {D, D+1} 중 (k,시각,KST)→ET가 D 04:00~20:00 ET 안인 쪽(zoneinfo America/New_York, DST 자동 — 11/01 뒤 경계 1시간 이동). 둘 다 아니면(주간거래 등) FILL_TIME_OUTSIDE_US_SESSION으로 HOLD. 추가 검사: 주문 ≤ 체결 ≤ 스냅숏, session_date == D. 시험: 이번 6건·10-07 사례·자정 넘김·EST.
- **(b)는 분리:** "잔액 차이가 정확히 맞으면 외부 흐름 인정"은 브로커 거래 기록이 아니라 잔액 추론이라 "브로커 기록으로 설명될 때만 기록"을 약하게 함. hwm-fix Judge 보고도 cashflow-api-gap을 별도 K3로 정함. 먼저 키움에 환전·출금 기록 TR이 있는지 조사. 꼭 둔다면 가장 엄격한 형태(유출만·연속 두 스냅숏에서 예수금 = 출금가능액 변화 = −X·그 구간 정산·거래내역 없음·UNVERIFIED_EXTERNAL_OUTFLOW·HWM 조정 없음·알림).
- 브로커 자료로는 −82.93이 출금인지 환전인지 구분 안 됨(cash_flow_evidence.py 39행 둘 다 외부 흐름) — 출금은 사장 원문 기준.
- 10-22 HOLD에는 OPEN_ORDERS_PRESENT:1(당시 정당)·SETTLEMENT_NOT_MATCHED도 있었음 — "원인 둘"은 10-23 기준.
- (1차 권고였던 "(a) 병합 뒤 cashflow-api-gap 순서"는 2차에서 철회 — 아래.)

검토 완결(갱신): 원문 확인 — 위 + 10-23 reconcile.json fills 6건·auto_core_tickets.py 520~533행·키움 사양 ust21150 · 내장 재검토 1회(반영 4건: 근거 정정·범위 추가·규칙 정밀화·권고 변경) · 미해결 3(ord_dt 시간대 공식 문구, 매도 주문표 G1 차단, oracle 크래시) · 바뀔 조건: 사양에 "현지 주문일자" 문구(A 확정) / 주간거래 체결 관측(경계 확정) / ust21100에 −82.93 행 출현(B 해소).

## 2차 재검토 반영 (변경분만, Opus — 결론 변경 1건, 최대 2회 도달)
- ord_dt 근거 보강: 10-21 06:15 스냅숏에는 BE 주문이 아예 없음(open_orders 없음, 당일 목록 SOXL뿐), 10-22 당일 목록에 10/21 17:49 KST ~ 10/22 06:13 KST가 한 미국 거래일로 함께 들어 있음, 10-23 사유 FILL_AMOUNT_UNAVAILABLE:2026-10-20도 세션 오판을 보여 줌.
- **11/03 기한(비서실 원문 확인):** plan_reads(auto_core_reconcile.py 184~191행)는 체결 조회를 "마지막 기록일 − 1"(10/20)부터 오늘까지 읽고, FILL_WINDOW_MAXIMUM_DAYS = 14(82행)를 넘으면 FILL_WINDOW_TOO_LONG(955행). 기록이 성공해야만 창이 줄고, 기록은 B(−82.95) 때문에 막혀 있으므로 **(a)와 무관하게 11/03 실행부터 다른 실패**. 1차의 "(a)가 11/03 문제를 없앰"은 틀림.
- (a) 범위 정리: 필수 = reconcile 체결 시각(285~290행)·참조 문서 231행. 주문표 쪽(auto_core_tickets.py 520~533·559~604, decide 195~199)은 주문표 원장만 바뀌는 별개 결함(KST 자정 뒤 주문 누락·다음 세션 주문 오귀속) → 같은 K3 안 **별도 커밋·별도 시험**. ust21100 deal_dt KST 가정(reconcile 590~612행)은 cashflow-api-gap 조사 항목.
- 시간 규칙 보정: 체결 시각에만 D 04:00~20:00 ET 창, 주문 시각은 "주문 ≤ 체결, D−1 20:00 ET 이후"로(예약·주간거래 시간 주문을 막지 않게). 주간거래 체결은 창 밖이라 HOLD(fail-closed).
- 주의: 당일 정산이 안 보이는 날에는 −82.95가 수수료 허용 범위 안이라 사유가 SETTLEMENT_D0_NOT_SHOWN만 보일 수 있음(HOLD는 유지).
- **최종 권고:** a) (a) K3 지금 착수 + **동시에** 키움 환전·출금 기록 TR 조사(읽기 전용, 비서실이 바로 함 — 승인 불요) → 10/30까지 B 경로가 없으면 확인 코드 경로(REUSE) 권한 결정을 11/03 전에 올림. b) (a)+(b 엄격한 형태) 한 묶음. c) 현행 유지(기본값 — 11/03부터 FILL_WINDOW_TOO_LONG).

검토 완결(최종): 원문 확인 — 위 전부 + plan_reads 184~191행·82행·955행 · 내장 재검토 2회(1차 반영 4건, 2차 반영 4건, 결론 변경 2건) · 미해결 3(ord_dt 시간대 공식 문구, 매도 주문표 G1 차단, oracle 크래시) · 자료 시점 2026-10-23 06:15 KST 실행분 · 바뀔 조건 위와 같음.

## TR 조사 (B 경로, 읽기 전용 — 2026-10-23 08:3x, kiwoom_query 실전계좌·real)
- 키움 사양 검색(해외 "환전", 전체 "입출금"): 환전·출금 **거래 기록** TR은 없음. 있는 것은 환전 신청(ust31302, 주문 성격 — 쓰지 않음)·환전 예상·환율, 잔액 조회(ust21120 통화별 예수금, ust21132 특정일 통화별 예수금), 거래내역 ust21100(출금 안 나옴).
- ust21132(특정일 통화별 예수금) 일자별 USD 외화예수금: 10/19 12,469.19 → 10/20 82.94 → 10/21 150.02 → 10/22 150.04. 원화 예수금은 네 날 모두 0. → 10/20→10/21 사이에 체결 정산만으로는 설명 안 되는 감소가 있고(정산 순액 +150.03 기준 −82.9 안팎, 정산 시점 차이로 2센트 단위는 확인 필요), 계좌 안 원화로 바뀐 흔적은 없음(환전 뒤 원화가 같은 날 빠졌는지는 구분 불가).
- 결론: B는 **거래 기록이 아니라 잔액 추론**으로만 증명 가능 → cashflow-api-gap K3에서 "가장 엄격한 형태"(유출만·연속 잔액 일치·HWM 조정 없음·UNVERIFIED_EXTERNAL_OUTFLOW) 또는 확인 코드 경로 권한 결정 중 하나를 사장이 정해야 함. 11/03 전 결정 필요.
- 소비처: cashflow-api-gap · recon-dt.

## 결정 기록
- 사장 원문 "결정 recon-dt: a"(2026-10-23 08:45 KST, 투자_V2 비서실 — 직접 입력, 바로 앞 제안 1건·같은 날).
- 실행(dc-dev Q2 a 수동 경로): Builder 지시문 docs/claude/recon-dt-builder-prompt.md → 회사PC `claude -p --worktree recon-dt --model opus --effort high`(acceptEdits, permission-prompts none, 허용 = unittest·git 읽기만, 커밋 없음), 실행 파일 workspace/outputs/dev-runs/recon-dt/run-builder.cmd, 출력 builder-2.json.
- 사고 기록(08:48): 첫 실행을 PowerShell 한 줄로 넘기다 따옴표가 깨져 허용 목록이 잘못 넘어간 Builder(PID 5152, 허용 칸에 맨 "Bash")가 1분쯤 돌았다 → 즉시 종료(자식 bash·python 포함). 그 사이 실행된 것은 읽기 전용뿐: worktree에서 기준선 시험(unittest test_auto_core*), 저장소 밖 폴더에서 git status/diff/log(실패). worktree 변경 0 확인. 재실행은 .cmd 파일로(인자 확인 뒤 08:5x).
- 다음: Builder 완료 → 별도 읽기 전용 Judge(Opus xhigh, Read·Grep·Glob) → 사장 병합 결정 → 커밋 2개로 병합.

