---
id: roadmap-fix-decisions-2026-10-26
type: decision
status: "t2-gate REMOVE = Judge 1차 FAIL(2026-10-26 15:52 KST) → 사장 '결정 t2-gate: REMOVE-v2'(16:07 KST) = 1-1절 반영안, 효력은 Judge 2차 PASS 뒤(그전에는 이전 조건 유지) · d10 REUSE = 결정됨, 정책 1줄은 사장 실행 대기, 채점기 변경은 개발 큐(d10-spy)"
date: 2026-10-26
authority: "order_authority=false · quantity_authority=none · execution_quantity=null. 주문·decision_mode 변경 없음"
consumers: "redesign-t2 '켜' 판정 세션 · 08:50 코어 알림 · 주간 팀장회의 · score_decision_journal.py(주간 채점) · roadmap.md"
source_decision: "사장 원문(사장실 스레드 직접 입력, 2026-10-26 15:33 KST): '결정 t2-gate: REMOVE' / '결정 d10: REUSE' — 바로 앞 제안 1건(roadmap-fix 계획, 15:3x KST), 같은 날, 1회"
---

# 로드맵 고치기 결정 2건 (2026-10-26)

부딪히는 결정: D3 동결(operating-diagnosis-2026-10-25.md 84행 — 이 문서는 사장 결정 기록이라 예외) · t2-rc 사전 등록(t2-rc-preregistration-2026-10-14.md, 해시 고정 — 원문은 고치지 않고 이 문서가 개정을 기록) · 재설계 A7 a(주문 1단계 유지, 바뀌지 않음).

## 1. t2-gate: REMOVE ("켜" 관문 R2 제거) — 권한·한도(K3), 제약 완화(H2)

**이전**(redesign-t2-builder-prompt-2026-10-10.md 46-48행, t2-rc-preregistration 18·22·25행): R1 리플레이 · R2 코어 판정 = 통합 점검(LLM) 판정 5거래일 연속(CORE_BUG 0) · C1 · C2 · R3 사장 "켜".

**이후**(Judge PASS 뒤 효력):
- R1: 그대로.
- **R2: "켜" 조건에서 뺀다.** 코어 vs LLM 비교(auto_core_compare.py, compare.json, streak)는 계속 돌고 기록·표시만 한다. CORE_BUG로 분류된 차이가 나오면 그 원인을 고칠 때까지 "켜" 판정을 하지 않는다(코어 결함 신호는 유지).
- **새로 넣는 것(기존 출력 재사용, 새 계산 없음): 대조 OK 연속 5거래일** — workspace/outputs/auto-core/<날짜>/reconcile.json status = "OK"인 실행이 연속 5회. HOLD 1회면 0부터.
- C1: 그대로(독립 계산기 일치 10세션, 불일치 0). NOT_CHECKED·ERROR는 세지 않는다.
- C2: 그대로(매수 주문표 1건 이상, 수량·LOC 가격·요건·관문·현금이 계산기와 일치).
- C3·C5: 그대로.
- R3: 그대로 — 모든 조건이 채워져도 decision_mode apply는 사장 별도 결정.

**이유**: R2 streak 10/15~10/24 매일 0/5(compare.json). 차이는 LLM 오류·입력 시각 차이(코어 06:15 스냅숏 vs LLM 06:4x 잔고)였고 코드 수정 필요 0(redesign-t2-compare-b7-2026-10-23.md 11-21행). 더 정확한 쪽을 덜 정확한 쪽에 맞추는 검증이라 구조적으로 통과가 어렵다. 같은 위험(틀린 판정)은 C1(독립 계산기)이 더 엄격하게 본다. 대신 실제로 위험한 "틀린 장부 위의 주문표"를 대조 OK 연속 조건으로 직접 막는다.

**제약 완화 표시(H2)**: 검사 1개(R2)를 관문에서 빼고 1개(대조 OK 연속)를 넣는다. 노출·예산·권한은 바뀌지 않는다.

**다음 단계**: 독립 Judge(Opus, 읽기 전용) — 지시문 t2-gate-judge-prompt.md. PASS면 이 문서 status를 "효력"으로 고치고 roadmap.md T2 칸을 갱신. FAIL이면 지적 반영 후 사장에게 다시 묻는다. 무응답·FAIL = 이전 조건 유지.

## 1-1. Judge 1차 FAIL 반영안 (위 1절을 대체) — 사장 원문 "결정 t2-gate: REMOVE-v2"(사장실 스레드 직접 입력, 2026-10-26 16:07 KST, 바로 앞 제안 1건·같은 날·1회). 효력은 Judge 2차(t2-gate-judge2-prompt.md) PASS 뒤

Judge 원문: 저장소 루트 t2-gate-judge-1.txt(UTF-16, 2026-10-26 15:52 KST, VERDICT FAIL). 비서실이 원문 대조: explained.json에 10-23·10-24 항목 없음, CORE_BUG 8건은 10-13·14, 사전 등록 48-54행은 덧붙임 방식(해시 파일 뒤에도 추가) — Judge 지적과 같다.

**정정**: 1절의 "같은 위험은 C1이 더 엄격하게 본다"는 틀렸다. C1은 후보·주문표는 더 엄격하지만, 중간 판정(후보를 바꾸지 않는 트리거·지표·근거 차이, 주문표 없는 날의 요건, R-REC1·RG1~4, 노출 N·V·E)과 S7 파생값(코어와 계산기가 같이 씀)은 보지 않는다. 실제 코어 결함 8건(CORE_BUG)은 모두 R2의 차이 분류에서 나왔다. "틀린 장부 위의 주문표"는 매일 G1(auto_core_decide.py 549-559행)이 막는다. 대조 OK 연속은 대조 경로가 안정됐는지 보는 조건이다.

**반영안 — 빼는 것은 R2의 "5거래일 연속"뿐, 차이 설명 의무는 남긴다** (모두 1절보다 엄격하게만):
1. **차이 분류 의무**: C1 10세션 창의 첫 세션부터 "켜" 판정일까지 모든 비교일의 compare.json `unexplained`가 설명 기록(explained.json LLM_ERROR·CORE_BUG) 또는 설명 문서의 "미설명 — 사유"(compare-b7-2026-10-23 16-18행 형식, 입력 시각 차이 허용)로 분류돼 있어야 한다. 하나라도 미분류면 판정하지 않는다. 연속일 아님, 전부 LLM_ERROR일 필요 없음(재설계 4절 "차이는 목록으로 설명").
2. **계산기 중간 차이**: 같은 창의 t2rc-check.json `requirements.diffs`와 diagnostics의 basis_met·new_basis_met·지표 차이가 0이거나 원인이 분류돼 있어야 한다. 코어 결함이면 CORE_BUG와 같게 다룬다.
3. **CORE_BUG 해소 정의**: 고친 커밋이 병합되고 그 SHA가 설명 문서나 이 문서에 적혀야 해소. 그 수정이 후보·주문표·요건·관문 계산을 바꾸면 C1은 0부터(사전 등록 24행과 같은 규칙). "켜" 전에 기존 8건(10-13·14)의 해소 커밋 목록을 적는다.
4. **대조 OK 셈**: 화~토 daily 실행일마다 그 날짜 폴더의 마지막 reconcile.json. status "OK" 그리고 mode "apply"일 때만 +1. HOLD·파일 없음·daily 실패·mode compare면 0부터.
5. **기록 연결**: 효력이 생기면 사전 등록 변경 기록(48-54행 방식)에 한 줄 덧붙인다. 부딪히는 결정에 재설계 4절 T2 행(automation-redesign 143행)·6절 이행 중 공백(161행) 추가.
6. **근거 문구**: 위 "정정" 문단으로 1절 근거를 대체.

참고(Judge): roadmap.md의 "C1 MATCH 4"는 공식 셈 "C1 2/10"(10-17·10-20, 사전 등록 53행)이 맞다. 10-15·16은 초기화로 빠짐.

지금 상태(이 반영안 기준): 미분류 차이 10-14 6·10-15 1·10-23 3·10-24 7건 → 분류 작업이 먼저 필요(읽기 작업, 사장실 스레드가 할 수 있음). 대조 OK 0/5.

## 1-2. 효력 기록 — Judge 2차 PASS (저장소 루트 t2-gate-judge-2.txt, 2026-10-26 16:2x KST). status: **효력**(아래 조건을 붙여서, 모두 1-1절보다 엄격하게만)

효력 조건(Judge 2차):
1. **범위**: 1-1절은 R1·C1·C2·C3·C5·R3, CORE_BUG 미해소 시 보류, "대조 OK 연속 5회"를 그대로 둔다. 분류 창은 2026-10-17 실행분부터이고, C1이 0부터 다시 시작하면 창도 다시 시작한다.
2. **비교일 수**: 창 안에 compare.json status COMPARED인 날이 5일 이상이어야 한다. NO_RECORD·NO_NEW_SESSION 날은 세지 않는다.
3. **비교 못 한 날**: decide FAIL·NOT_COMPARED·읽기 불가인 날은 날짜와 원인을 적는다. 원인이 코어 쪽이면 CORE_BUG로 다룬다.
4. **"미설명 — 사유"**: 그날 원자료로 코어 밖 원인을 보여야 한다. "원인 미상"·"확인 필요"는 미분류로 본다.
5. **계산기 범위**: 1-1절 조건 2는 diagnostics.items 전부(ind:·trig:·basis_met·new_basis_met)와 t2rc-check 노출 블록(N·V·E·equity)을 포함한다. 표기만 다른 차이는 "표기 차이"로 분류할 수 있다.
6. **오라클 결과 없는 날**: 결과가 없거나 ERROR·NOT_CHECKED인 날은 "차이 0"으로 세지 않고 "조건 1로만 확인"으로 적는다(지금 10-21, 10-22~24).

문구 정정(Judge 2차):
- a. **H2 표시**: 빼는 것은 R2의 연속 셈과 "전부 LLM_ERROR여야 함" 두 가지다. 노출·예산·권한은 그대로.
- b. 1절의 "해시 재고정"은 틀렸다. 사전 등록 문서는 해시를 다시 고정하지 않고 끝의 변경 기록에 덧붙인다(16행).
- c. 1-1절 "정정"의 CORE_BUG 8건 원인은 C6, 총자산 현금, 비교 모듈 2건이다(explained.json 10-13·14).
- d. **지금 상태(10-26 기준)**: 계산기 trig: 차이 4건(10-17 3건·10-20 1건) 미분류, CORE_BUG 해소 커밋 목록 아직 없음, 10-13 RREC:RG1은 조건 3에 걸려 판정을 막는다. 대조 OK 0/5.

기록 연결: 사전 등록 변경 기록 55행 추가(t2-rc-preregistration-2026-10-14.md), active-decisions.md t2-gate 행·roadmap.md T2 행 갱신.
"켜"(decision_mode apply)는 여전히 사장 별도 결정(R3).

## 1-3. 효력 조건 이행 기록 (2026-10-28 KST, 읽기 작업)

**trig: 차이 4건 — 모두 "표기 차이"(조건 5)**: t2rc-check.json diagnostics 2026-10-17 [NBIS trig:N9, SOXL trig:S6, SOXL trig:S8], 2026-10-20 [NBIS trig:N9], 형식 [종목, 항목, 코어, 계산기] = […, "review", "hit"]. 세 규칙 모두 side "alert"(같은 날 decision.json). 코어는 alert 쪽 hit를 "review"로 바꿔 적는다(auto_core_rules.py 582-585행, 순위 rank hit=review=5, 598행). 판정은 같고 이름만 다르다 → 표기 차이. 미분류 0.

**CORE_BUG 8건 해소 커밋 목록(조건 3)** — 출처 redesign-t2-compare-explained.json, git log:
| 날짜 · 항목 | 원인 | 해소 커밋 |
|---|---|---|
| 10-13·10-14 MU:rebound_fail, MU:pullback_rebound (4건) | C6 반등·눌림 조건 없음 | 1a2b7d6 (c6-fix2, 10-14 14:37 KST) |
| 10-13 BE:false_breakout | 대조 모듈 사건일 여유 | 9f554fc (cmp-fix2, 10-13 11:09) |
| 10-13 exposure:caps | 대조 모듈 문자열 비교 | 9f554fc (cmp-fix2) |
| 10-13 exposure:N | 총자산 현금 | 73e18b4 (t2-equity-cash 병합, 10-13 14:06) |
| 10-13 RREC:RG1 | 총자산 현금(EV4) + 연구 기록 공백 unk | 73e18b4 + da5d85e (cmp-fix3, 공백 unk를 사전 등록 B4로 분류, 10-13 16:14) — **해소로 볼지 Judge 확인 필요**(Judge 2차 d는 이 항목이 조건 3에 걸린다고 봄) |

모두 C1 창(10-17 실행분) 전에 병합됨 → C1 초기화에 영향 없음. 남은 "켜" 조건: 대조 OK 0/5(별도 스레드), C1 2/10, C2 0, 비교일 COMPARED 수 확인, RG1 해소 판단.

## 2. d10: REUSE (SPY 벤치마크 공급) — 정책 1줄 + 일반 변경 1건

- **정책(사장 실행)**: workspace/policies/auto_core.json symbols_extra에 "SPY" 추가. 자동 코어가 SOXX·GRID처럼 30분봉 종가를 받아 workspace/outputs/regular-session-closes/history/SPY.close-history.json에 쌓는다(auto_core.py 93-110·348행).
  - 영향 확인: decide는 보유+관심 명단만 판정한다(auto_core_decide.py 993행 `set(holdings) | set(members)`) → SPY로 주문표·관문 판정은 생기지 않는다. 키움 조회 대상이 1개 늘어남(읽기 조회, 주문 아님).
  - 이 프로젝트는 정책 파일을 쓰지 않는다(지침 4절). 사장 PowerShell 한 줄 또는 Cowork.
- **일반 변경(개발 큐 d10-spy)**: score_decision_journal.py가 reference-closes/SPY.json이 없으면 history/SPY.close-history.json을 같은 검증(달력·분할 의심)으로 읽는다. 라벨은 계속 REFERENCE_ONLY(매매 근거 아님, 증거 등급 영향 없음).
- 바뀔 조건: 첫 수집에서 키움이 SPY 30분봉을 주지 않으면 REUSE 불가 → 사장에게 다시 묻는다.

## 기록
- 2026-10-26 15:33 KST 사장 결정 2건.
- 같은 날: 이 문서, t2-gate-judge-prompt.md, d10-spy-builder-prompt.md 작성, 개발 큐 d10-spy 등록, active-decisions.md 2줄 추가.
- 2026-10-26 15:52 KST Judge 1차 FAIL → 16:07 사장 "결정 t2-gate: REMOVE-v2" → Judge 2차 PASS(조건부) → 16:3x 1-2절 효력 기록.
- 2026-10-26 16:16 KST dev-run d10-spy READY_TO_MERGE(Judge 1차 FAIL 보고서 문구 → 2차 PASS, 새 실패 0, diff_hash 52f66f26…). 16:36 KST 사장 원문 "결정 d10-spy 병합: 승인"(사장실 스레드 직접 입력). 병합은 사장 PowerShell `.\tools\dev-merge.ps1 d10-spy`. 참고: 종가 검증이 -04:00 세션만 인정 → 11/01 서머타임 종료 뒤 SPY 세션 제외(Judge G4 참고).
- 2026-10-26 16:52 KST d10-spy 병합 a9e653a(ff). 남은 일: 정책 auto_core.json symbols_extra에 SPY 추가(사장 실행, 10/27 대조 확인 뒤).
