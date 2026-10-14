---
id: open-items-review-2026-10-14
title: 남은 미해결 4건 검토 (b2_wide · MVLL info · 정산일 I3 · R-C)
date: 2026-10-14
class: 검토 기록(문서). 코드·규칙 파일·정책·상태·예약 작업 변경 없음
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: 관제판 redesign-t2 · 다음 Cowork 아침 점검(10/15 대조 설명) · c3-state-decision-2026-10-14.md 3절(“일반 변경” 표기 정정) · redesign-t2-day2-check-2026-10-14.md 4절
status: 1~4절 재검토 2회 반영 · 5절 위원회 Full + 재검토 2회 반영
---

# 남은 미해결 4건 검토

## 요약
| # | 항목 | 결론 | 지금 막는 것 | 사용자 손 |
|---|---|---|---|---|
| 1 | b2_wide DELL·PWR trend_recover | NO_CHANGE | 없음 | 0 |
| 2 | MVLL + 쪽 LLM info | 보류(기본 NO_CHANGE). 4번이 열릴 때만 의미 → 그때 규칙 115행 안(K1) 우선 | T2 R2 연속 일수(일부 날) — 단 T2는 4번으로 이미 막혀 있음 | 0 |
| 3 | 정산일 06:15 I3 멈춤 | NO_CHANGE + 사전 등록: 다음 매도 결제일에 또 멈추면 권한 경로로 재설계 | 매도 결제 뒤 첫 06:15 그날 주문표(매도 포함) | 0 |
| 4 | 리플레이 R-C NOT_MET | 사전 등록대로 NO_CHANGE(비교 모드 유지). 기준 대체는 사용자 결정(K3) | T2 "켜" | 결정 시 1번 |

정정: c3-state-decision-2026-10-14.md 25행과 이 문서 초안의 "일반 변경(dev 파이프라인)"은 틀렸다. auto_core*.py·test_auto_core*.py·run/register_auto_core_task.ps1은 권한 경로(tools/dev_pipeline/authority-paths.txt) → NEEDS_APPROVAL, `dev-merge -ApproveAuthority`.

## 1. b2_wide — NO_CHANGE
- 규칙 적용: EMA 계열은 알려진 정의 차이로 여유 3%까지 B2(auto_core_compare.py 45·102~108행). 10-14 DELL 0.028558·PWR 0.026966(decision.json 2026-10-14 compare.b2_wide) → 사전 등록 규칙대로.
- 결함 관점: 원인은 정의 차이가 아니라 LLM의 C3 "유지 중" 누락(10-13 같은 항목은 3% 초과 → B7 → LLM_ERROR, redesign-t2-compare-explained.json).
- 연속 일수 영향 없음: B2 통과 = B7+LLM_ERROR 통과(day_passes 313~318행). 3% 안에서 숨을 수 있는 코어 오류는 결정 c3-state a로 trend_recover 코어 = 규칙 확인됨.
- 원인 제거 진행 중: v3.12.5 113행 보완(10/15 07:35 교체, 10/16 06:40부터, integrated-check-v3.12.5-change 7행).
- 바뀔 조건: 10/16 뒤에도 DELL·PWR류 trend_recover 차이가 남으면 재검토.

## 2. MVLL + 쪽 LLM info — 보류
- 사실: 10-14 연구 기록 MVLL C6+ state "info", label "매수 불가 상품". 규칙 115행 "+ 쪽은 계산·표시만" → LLM은 규칙대로. 대조는 hit만 충족(64~65행) → B7. info→B5 분기는 매수 요건 3칸만(238~239행). 설명 verdict는 LLM_ERROR·CORE_BUG 둘뿐(schema explained_file) → 그날은 연속 일수 0.
- 범위 정정: MVLL도 여유 3%까지 B2(105행). 막히는 날 = C6+ 등 사건형 5세션 창 안이거나 C3+ 여유 3% 초과인 날. 10-14는 MU C6 CORE_BUG로 이미 빠졌고 MVLL:trend_recover는 LLM_ERROR로 설명됨.
- 10-14 MVLL C6+는 고친 규칙(1a2b7d6)으로도 성립(재검토 서브에이전트 재계산) → 숨은 코어 결함 없음.
- 선택지(검토 순서):
  - NO_CHANGE(기본): T2는 4번 R-C로 이미 막혀 있어 지금 고쳐도 T2가 열리지 않는다.
  - REPLACE(K1, 규칙 파일): 115행을 "state는 계산 결과 그대로, label만 매수 불가 상품, 알림 없음"으로. 대조가 B1로 남고 MVLL + 쪽 코어 오류도 계속 잡힌다. 사전 등록 불변. 손: 규칙 파일 재서명 1번. 코어는 integrated_check_run을 대조에만 쓴다(auto_core_inputs.py 259행, decide 775행) → 확인 필요는 LLM 알림·통합점검 화면뿐.
  - ADD(권한 경로 + 부록 B 사후 개정): 대조 코드에서 `buy_approved`(auto_core_tickets.py 61행 APPROVED_BUY, decide 995행)가 false이고 + 쪽이면 B5. tactical_candidate_universe.json은 SOXL·NBIS·BE도 new_buy_approved false라 쓰면 안 됨. 결과를 본 뒤 R2 통과를 쉽게 하는 개정이라 독립 Judge 필요. 그 종목 + 쪽 코어 오류를 못 잡게 됨 → 비권장.
- 처리 규칙(그동안): MVLL + 쪽 info로 생긴 B7은 설명 파일에 적지 않고 미설명으로 둔다(LLM_ERROR로 적지 않음, 그날 연속 일수 0 수용). decide의 "판정 차이 n건 — 설명 기록 필요"(auto_core_decide.py 783~784행)가 그날 나와도 이 규칙으로 처리.
- 바뀔 조건: 4번에서 사용자가 B를 고르면 → REPLACE(115행)를 그 일정에 붙인다.

## 3. 정산일 06:15 I3 — NO_CHANGE + 사전 등록
- 사실: 기준 = 10-13 18:40 KST 원장 제안 스냅숏 주문가능 12,469.18(SOXL 체결 뒤 → 기준 뒤 체결 0). 06:15 스냅숏(kiwoom_broker_snapshot.09f2d6795cd88b15.shadow.json, 21:15Z) 12,472.23 → 차이 +3.05 → I3 CASH_CHANGE_NOT_EXPLAINED → HOLD(day2-check 4행). 결제 08:07:05 뒤 08:37 읽기 12,469.19(+0.01) → OK(현재 result.json은 08:37 실행으로 덮어써짐). +3.05의 원인 확인 필요.
- 기존 D0 처리(auto_core_reconcile.py 501~553행)는 기준 뒤 체결이 있을 때만 쓰인다 → 이번 경우를 못 덮는다(1.00 허용, 747~748행).
- 영향(기간별): T1 켜기 전 = daily 연속 일수 0(auto_core.py compare_streak). T1 켠 뒤 = 그날 상태 기록 하루 늦음 + decide G1 → 매도 포함 주문표 0(실제 손실은 T2 켠 뒤 또는 이번 주 exc-1부터, 그 전 주문표는 "비교 중")(auto_core_tickets.py 690·817~819행). 다음 날 저절로 풀림, 사람 손 필요 없음. 10-14 수동 재실행은 t1-safety 병합(08:35) 직후라 정산 때문이라고 입증 안 됨.
- 처음 낸 "조건부 재실행" 안은 철회: T2 기록 모드에서는 같은 날 두 번째 decide가 다른 결정이면 HOLD·주문표 0·rerun 파일·푸시로 끝난다(auto_core_decide.py 807~820·871~889행, R2-5) → 효과 없음. 07:45 decide가 08:30까지 연구 기록을 기다리고 실행 한도 60분이라 겹침 위험도 있음(decide 64·568행, register_auto_core_task.ps1 11~12·27행).
- 남은 대안(권한 경로): daily 재시도(그날 OK 아닐 때만) → decide를 결제 처리 뒤 한 번만(예 08:15 뒤, 08:50 알림 전). 근거가 관측 1건(08:07)이라 지금 하지 않는다.
- 사전 등록: 다음 매도 결제 KST일 06:15 result에서 I3 CASH_CHANGE_NOT_EXPLAINED(D0_ONLY 아님)면 → 위 대안을 권한 작업으로 올려 사용자에게 묻는다. 통과하면 NO_CHANGE 확정. 기한 없음, 답 없으면 NO_CHANGE.

## 4. 리플레이 R-C NOT_MET — 사전 등록대로 NO_CHANGE
- 정의: P-R2(NBIS 13 + 현금) 3개월 매수 주문표 0 → R-C 미달, 기본 처분 = 비교 모드 유지 + 막힌 사유 순위 한 번 알림(builder-prompt 472행, auto_core_replay.py 19~20·379행). R1(R-A·R-B·R-C) 통과는 T2 조건(builder-prompt 46행), autocore-on 2-3 "원안 그대로"로 유지.
- 사전 등록 기간(07-10~10-09) 이번 세션 재실행(읽기 전용, 저장소 밖): R-A PASS · R-B PASS · R-C NOT_MET, P-R1·P-R2 각 65세션, 예외 0, 자료 없음 0. 판정 기록: redesign-t2-replay-2026-10-14.md.
  - 막힌 사유 순위 P-R2: NO_CIRCUIT_OPEN 64 · G2 EARNINGS_DATE_UNVERIFIED 1 · G2 PEAK_REVIEW_PAUSE 1 · REQ1_EARNINGS 1 · REQ2 1.
  - P-R1: NO_CIRCUIT_OPEN 63 · REQ2 2 · REQ5_RREC1 2 · G2 PEAK_REVIEW_PAUSE 1 · G2 PROPOSAL_NOT_AN_INCREASE 1.
  - R-B는 열린 세션 0이라 실질 검사 0건(oracle_open_checked 0, external_checked 0).
- 원인: 매수 회로는 "오늘 새 공식 강한 근거" 또는 "오늘 새 가격 단서 2종 이상"일 때만 열린다(auto_core_tickets.py 141행). 리플레이는 사전 등록상 공식 사실 없음 → 구조적으로 드물다. R-C 미달은 "관문 상시 닫힘"의 증거라기보다 리플레이 가정의 결과(등급 D).
- 결함 관점: 기간이 고정이라 다시 돌려도 판정이 같다 → 현 기준으로 T2 "켜"는 계속 막힌다.
- 6단계 기록: redesign-t2-replay-2026-10-14.md에 남김(외부 오라클 선커밋 없음·결과 먼저 봄을 명시). 1회 알림 = 이 검토 보고 전달(2026-10-14).
- 선택지: A NO_CHANGE(T2 비교 모드 유지, 이번 주 exc-1 예외만) / B R-C를 실운영 기준으로 대체(예: 비교 모드 decide가 실제 연구 기록으로 낸 매수 주문표를 Cowork가 재계산해 일치한 건수 — 기간·건수는 결과 보기 전 사전 등록). B는 T2 조건 변경 = K3: 사용자 결정, 위원회, 독립 Judge, 권한 작업 1개 한도.
- 바뀔 조건: 실운영 비교 모드에서도 매수 주문표가 계속 0이면 "관문 상시 닫힘"이 실제 문제 → 회로 조건 자체 검토.

## 미해결(기본 처분 NO_CHANGE, 알림만)
- +3.05 원인과 키움 결제 처리 시각(관측 1건).
- 2번 REPLACE 안의 hit 소비처 확인(4번 B 선택 시에만).

## 5. t2-rc A·B 검토 (2026-10-14 17:3x, 사용자 요청, 위원회 Full)
- R-C의 원래 목적(재설계 문서 automation-redesign-2026-10-10.md 163행 사전 부검): "코어는 매일 도는데 사용자는 여전히 Cowork에서 결정" 방지 → "최근 3개월 리플레이에서 주문표가 나왔어야 할 날에 실제로 나오는지". 구현(builder-prompt 472행)은 "P-R2 매수 주문표 ≥ 1"로 단순화됨. 리플레이에서 "나왔어야 할 날"(오라클 열림)은 0일 → 원래 질문에는 답이 없다(R-B와 같은 빈 통과).
- 실운영: decide 기록 10-13(HOLD)·10-14(OK) 모두 주문표 0·후보 0. 매수·매도 어느 경로도 리플레이·실운영에서 주문표를 낸 적이 없다.
- A(현행 유지): 코드를 고쳐 리플레이를 다시 돌리거나 K3로 기준을 바꾸지 않는 한 T2는 안 켜진다 → 사전 부검이 막으려던 상태가 그대로 굳는다. 안전은 늘지도 줄지도 않는다(비교 모드 유지, R-C는 틀린 주문표를 못 잡는다).
- B(처음 안, "첫 매수 주문표 재계산 일치"): 위원회 2명(비판자·실용주의자)이 조건부 찬성, 1명(회의론자) 지금은 보류. 공통 지적 → 처음 안은 약하다: ① 빈도 질문이 사라짐 ② 매도 경로 미검증인 채 T2 전체가 켜짐 ③ 결과를 본 뒤 기준 변경(골대 이동)이라 옛 기준보다 느슨하면 안 됨.
- 내장 재검토(Opus, 14건) 반영: B+ 첫 판은 ⑤ 코어가 안 연 회로(거짓 음성)를 못 봄 ⑥ 막힌 후보만으로 통과 가능(옛 R-C는 주문표 1건 필요) ⑦ 빈도 항목이 회로 열림만 셈 ⑧ 같은 코드 재실행이면 순환 판정 ⑩ 매도 후보는 E ≥ 1.85(ABOVE_BAND, alert_policy.json 687행, portfolio_exposure.py 1187행) 또는 카드 EXIT/TRIM일 때만(보유 3종 카드 모두 HOLD, 현재 E 1.5037) → 매도 2회 요건은 사실상 무기한 → 아래로 고침.
- 보강안 B+ (2판, 숫자는 Judge 검토 뒤 첫 실운영 후보 전에 고정):
  1. 누수: 비교 모드 각 세션에서 Cowork가 규칙 파일·설계 원문으로(코어 코드 재실행이 아니라) 전 종목·방향의 회로 열림을 따로 계산해 decision.json candidates와 같은지 본다. 근거 기록: evidence(방향별 basis_met·new_basis_met), inputs의 s7_review·registry·snapshot sha. 그날 계산(입력 파일이 바뀔 수 있음). 통과 = 사전 등록 뒤 모든 비교 세션 불일치 0(불일치 = CORE_BUG로 고친 뒤 다시 셈).
  2. 매수: 실제 매수 주문표 1건 이상이 수량·LOC 가격·요건 ①~⑤·관문·현금까지 독립 계산과 일치(exc-1 확인 목록 재사용). 옛 R-C의 "주문표 1건"을 실운영 자료로 바꾼 것.
  3. 매도: 횟수 요건 없음(매도 후보는 E ≥ 1.85 또는 카드 EXIT/TRIM이라 무기한일 수 있음). 대신 켠 뒤 방향별 첫 주문표는 Cowork 확인 기록 파일(경로 사전 등록)이 있어야 알림이 입력 안내를 보낸다. apply 모드에서는 decide(auto_core_decide.py 463~469·797~798행)와 알림 지시문(auto-core-alert.txt 68~70·82·85행)이 확인 없이 "주문표 N건 — 저녁 키움 입력"을 보내므로, 알림 지시문에 "확인 기록 없으면 '주문표 확인 대기 — 입력 금지'" 규칙 1개를 넣는다(K1, 같은 Judge 범위, 예약 작업 재서명 1번).
  4. 빈도: 실운영 6주 동안 회로 열림 수·주문표 수·막힌 사유 순위를 세고 주문표 0이면 회로·관문 검토를 알림(자동 변경 없음).
  5. 일몰: 사전 등록 뒤 12주 안에 2번이 안 채워지면 회로 열림 수·막힌 사유를 붙여 사용자에게 1회 알림. 답이 없으면 T2 비교 모드 유지·B+ 기준 유지(옛 R-C로 돌아가지 않음).
  6. R-B는 "PASS(실질 0건) = 미검증"으로 다시 적는다. 2번 항목(MVLL + 쪽 info) 규칙 115행 보완(K1)을 같은 일정에 붙인다.
- 리플레이 기저율: 회로 열린 세션 = 매수 3(P-R1 08-13 NBIS·08-20 MVLL, P-R2 08-13 NBIS, 모두 요건으로 막힘), 매도 0. 외부 오라클은 리플레이 전에 커밋하지 않았다(redesign-t2-replay-2026-10-14.md).
- 방향별 켜기(매수만 먼저): decision_mode가 값 하나라(auto_core_decide.py 505행) 코드 필요·권한 경로 → 비권장.
- 회의론자 대안 C(시점 기준 공식 사실을 넣어 리플레이 재실행): 원래 빈도 질문을 지키지만 과거 공식 사실 재구성(LLM 판정 포함)이 크고, 고정된 가정을 바꾸는 것이라 역시 결과 본 뒤 변경 → 비권장.
- 경로: B+는 판정 기준 문서 + 알림 지시문 규칙 1개, Python 코드 없음. 다만 T2 켜 조건 = K3 → 독립 Judge(별도 Claude Code 세션, 사용자 1번) + 사용자 승인. 진행 중 권한 작업 0(git log 1a2b7d6 c6-fix2 14:37·47e35fe event-ctx4 일반, _dev-queue 비어 있음) → 한도 안.
- 권고: B 결정 시 Cowork가 B+ 2판 사전 등록 문서를 쓰고 독립 Judge → 사용자 승인. 그때까지 비교 모드 그대로(NO_CHANGE).
- 바뀔 조건: 실운영에서 후보 재계산 불일치가 1건이라도 나오면 B+ 판정 실패 → CORE_BUG 경로. 6주 안에 매수 주문표가 1건 이상 나오면 빈도 항목 해소.
