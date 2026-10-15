---
id: autocore-on-decision-2026-10-13
title: 자동 코어 "켜" — 결정 autocore-on: 1 (T1 먼저 + 이번 주 매수 주문표 1회 예외)
date: 2026-10-13
decision: 사용자 "결정 autocore-on: 1" (2026-10-13 21:01 KST, Cowork)
council: decision-council Full(설계자·회의론자·실용주의자·비판자, 2026-10-13 20:5x) — 지금 둘 다 켜기 3명 반대
consumers: 관제판 autocore-on·t1-safety·redesign-t1·redesign-t2 · 10/14 08:05 확인 예약(trig_015gsZE9RmktsZVPqLDaQnfX) · 다음 Cowork 세션
authority: 주문 권한 없음(사용자 직접 입력) · 정책 문턱·예산·상한 불변 · 매도 주문표는 예외 대상 아님
---

## 1. 위원회 요약
- 회의론자: 비교 일수 대기. 매수를 막는 것은 스위치가 아니라 시장 회복 관문. 주문표 없는 날의 일치는 매수 경로를 검증하지 못한다.
- 실용주의자: T1 먼저(체결 뒤 사람 대조를 없애는 쪽). 수정은 묶어서.
- 비판자(가장 강한 반대): T2 조기 반대 — 매도 주문표는 관문 없이 나와 검증 안 된 경로가 실제 입력된다. "그날 버그 없음"은 기계 판정이 순환이거나 사람 단계다.
- 설계자: 조기 T2 입장 철회(반대 2명 이상 = 신호).

## 2. 사전 등록 (사람 판단 없이 기계로 확인)
### 2-1. 안전 수정 t1-safety (파이프라인, 사용자 병합 1번)
- G5(judge2 G "켜" 전 5): HOLD/FAIL로 F1 전에 끝난 날의 EV4 유실 → 그날 브로커 스냅샷과 그 세션 종가로 EV4를 다시 구한다. 못 구하면 docs/claude/t1-safety-builder-prompt.md 규칙대로 막는 쪽.
- r4 F(judge2 G "켜" 전 2): F6 같은 날 조회 안 중복 ord_no → 같은 행은 한 번만, 다른 행이면 결과 unknown(fail closed).
- G3(재실행 push 전달): 알림 v2.1(2026-10-13 09:05)이 decision.rerun-*.json을 읽고 push 줄을 낸다(scheduled-prompts/auto-core-alert.txt 10·12·53행) → 이미 해소, 작업 없음.
### 2-2. T1(기록 모드) 켜기 조건 — 모두 참이면 Cowork가 실행
1. t1-safety 병합 완료(메인 test_auto_core* 통과).
2. workspace/outputs/auto-core/LATEST.json: status OK, mode compare, compare.streak ≥ 2, guarded_dirty_paths [].
3. 실행: workspace/policies/auto_core.json "mode" compare → apply 한 칸만(사용자 승인 = 이 결정). 정책 파일 커밋 명령은 사용자 1번. decision_mode는 compare 그대로.
- 가장 이른 날: 10/15 아침 결과로 확인 → 10/16 06:15부터 기록(확인 필요: 그 사이 HOLD 없을 때).
### 2-3. T2(판정 모드)
- 원안 그대로: 5거래일 대조(compare.streak ≥ 5, B7은 LLM_ERROR 설명만) + "켜" 전 회차 나머지 항목 뒤. 조기 켜기 없음.
### 2-4. 이번 주 매수 주문표 1회 예외
- 대상: 2026-10-14~10-17 KST decide가 낸 **첫 매수 주문표 1건**("비교 중" 표시). 매도·재발행·두 번째 주문표는 대상 아님. T2가 켜지거나 10/17 세션이 끝나면 소멸.
- Cowork 확인(그날 아침, 읽기 전용): 결정 기록 입력으로 수량·LOC 가격을 auto_core_tickets 규칙대로 다시 계산해 같은지, 매수 요건 ①~⑤ 모두 통과·G0/G1 없음, S7 신선·멈춤 없음, 상태 = 브로커, 주문가능 현금 ≥ 주문 금액. 하나라도 다르면 예외 불가로 보고.
- 사용자 결정: "결정 exc-1: 입력" 또는 "결정 exc-1: 안 함". 입력이면 Cowork가 portfolio_review_journal.py로 일지 기록(--confirmed-via COWORK_CHAT_USER_MESSAGE, 사용자 문장 그대로). 답이 없으면 입력하지 않음(기본값).
- 체결 뒤: T1이 아직 꺼져 있으면 다음 decide가 G1_STATE_NOT_EQUAL_BROKER로 멈추므로 확인 코드 대조 1번 필요(T1이 켜져 있으면 자동).

## 3. 진행 기록
- 2026-10-14 08:35 t1-safety 병합 4051391(사용자 dev-merge, rebase) — 2-2 조건 1 충족.
- 2026-10-14 08:3x 사용자 autocore-run-once(결제 08:07 뒤): daily OK(I1~I5 PASS, 주문가능 12,469.19), compare.streak 1(HUMAN_LEDGER_ENTRY), decide OK·G1 없음·ev4_backfill []. 매수 요건 막힘은 ⑤ RG2·RG3(+NBIS·SOXL ③, MVLL ②)뿐. 06:15 HOLD(I3 +$3.05)는 SOXL 22주 매도 결제 전 중간값이었다(결제 08:07: 총 3,074.72 − 수수료 2.15 − 세금 0.06 = 3,072.51).
- 2026-10-14 08:38 사용자 "결정 exc-1: 조건부 입력" — 2-4의 예외를 미리 승인. 첫 매수 주문표가 나오고 Cowork 확인 항목이 모두 맞으면 다시 묻지 않고 "입력하세요"로 알린다(수량·LOC 가격·입력 기한 포함). 하나라도 다르면 입력하지 않음으로 보고. 매도·재발행·두 번째 주문표 제외, 10/17 세션 끝나면 소멸. 일지 기록은 사용자가 입력했다고 알릴 때 그 문장으로 portfolio_review_journal.py에 남긴다.
- T1 켜기: 10/15 06:15 daily가 OK·streak 2면 2-2 조건 모두 충족 → 10/15 아침 점검에서 정책 파일 변경, 10/16 06:15부터 기록.
- 2026-10-15 08:0x 아침 점검: T1 daily 06:15 다시 HOLD — I3 CASH_CHANGE_NOT_EXPLAINED:3.06 + PROPOSAL_BLOCKED:CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS(주문가능 12,472.24 vs 예수금·출금가능 12,469.19, 미결제 매도 없음). T1 streak 0 → 2-2 조건 2 불충족, 정책 파일 변경 안 함.
  - **원인 정정(10/14 판단 수정)**: +$3.05는 결제 중간값이 아니라 **06:15 무렵에만 주문가능액에 원화 예수금 ₩4,227이 가환율(약 1,386원)로 더해지는 현상**으로 보인다(추정, 확인 필요). 근거: 06:15 KST 읽기 2번(10/14·10/15) 모두 기준 + 약 $3.05, 그 밖의 시각(10/13 08:46~18:40, 10/14 08:37·18:30, 10/15 08:06 직접 조회)은 모두 주문가능 = 예수금. ₩4,227 / 3.05 ≈ 1,386. 10/14 결제(08:07)와 겹쳐 결제 중간값으로 잘못 봤다.
  - 영향: 매일 06:15 T1 HOLD → decide G1 → 주문표 0, T1 연속 일수 영구 0 = 자동 운영 심각 결함.
  - 해소안: (A) 원화 예수금 ₩4,227 출금(사용자 1회, 원인 제거 — 권장) (B) T1·decide 실행 시각을 08:10 이후로(겨울 시간 효과 확인 필요) (C) 코드에서 원화 환산분 제외(K3).
- 시장: 10/14 새 R-REC1 사건 EV2+EV4(SOXX C0 519.38·L0 517.47, 계좌 총액 25,548 < V6 1차 선 25,626.55), S7 L1(−10%) 도달(가벼운 점검 카드, 멈춤 없음), SOXL 고점 −30% 검토(R5), MVLL·NBIS 근접. 매수 요건 ⑤ RG1·RG2·RG3 미충족.
- 2026-10-15 08:21 사용자 "결정 krw-0615-cash: A" + "원화 예수금 ₩4,227 출금 완료". Cowork 08:2x 조회: krw_entra 0, 달러 예수금·출금가능·주문가능 모두 12,469.19(변화 없음). 확인 방법: 다음 06:15 읽기에서 주문가능 = 예수금이면 원인 확정.
- 2026-10-15 08:2x 사용자 재실행: daily OK(I1~I5 PASS), compare.streak 2(EXPLAINED_BY_FILLS), guarded_dirty_paths [], 커밋 cf2c86c(t1-safety 4051391 포함) → 2-2 조건 모두 충족. Cowork가 workspace/policies/auto_core.json "mode" compare → apply 한 칸만 변경(CRLF 유지, sha256 7fcb0efe…cf4 → fc912735…09b, load_config OK, decision_mode compare 그대로). 정책 커밋은 사용자 1번. 10/16 06:15부터 코어가 불변 조건 통과 시 상태 기록(확인 코드 경로 은퇴 시작). 되돌리기: mode를 compare로 또는 kill_switch true.
