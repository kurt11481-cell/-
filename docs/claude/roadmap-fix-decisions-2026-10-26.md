---
id: roadmap-fix-decisions-2026-10-26
type: decision
status: "t2-gate REMOVE = 결정됨, 효력은 독립 Judge PASS 뒤 · d10 REUSE = 결정됨, 정책 1줄은 사장 실행 대기, 채점기 변경은 개발 큐(d10-spy)"
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

## 2. d10: REUSE (SPY 벤치마크 공급) — 정책 1줄 + 일반 변경 1건

- **정책(사장 실행)**: workspace/policies/auto_core.json symbols_extra에 "SPY" 추가. 자동 코어가 SOXX·GRID처럼 30분봉 종가를 받아 workspace/outputs/regular-session-closes/history/SPY.close-history.json에 쌓는다(auto_core.py 93-110·348행).
  - 영향 확인: decide는 보유+관심 명단만 판정한다(auto_core_decide.py 993행 `set(holdings) | set(members)`) → SPY로 주문표·관문 판정은 생기지 않는다. 키움 조회 대상이 1개 늘어남(읽기 조회, 주문 아님).
  - 이 프로젝트는 정책 파일을 쓰지 않는다(지침 4절). 사장 PowerShell 한 줄 또는 Cowork.
- **일반 변경(개발 큐 d10-spy)**: score_decision_journal.py가 reference-closes/SPY.json이 없으면 history/SPY.close-history.json을 같은 검증(달력·분할 의심)으로 읽는다. 라벨은 계속 REFERENCE_ONLY(매매 근거 아님, 증거 등급 영향 없음).
- 바뀔 조건: 첫 수집에서 키움이 SPY 30분봉을 주지 않으면 REUSE 불가 → 사장에게 다시 묻는다.

## 기록
- 2026-10-26 15:33 KST 사장 결정 2건.
- 같은 날: 이 문서, t2-gate-judge-prompt.md, d10-spy-builder-prompt.md 작성, 개발 큐 d10-spy 등록, active-decisions.md 2줄 추가.
