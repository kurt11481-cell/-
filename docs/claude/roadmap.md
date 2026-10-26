---
id: roadmap
type: roadmap
status: current
as_of: 2026-10-26
summary: "투자_V2 개발·운영 로드맵 한 장 — 단계와 다음 순번. 세부 진행의 원본은 개발 관제판, 이 노트는 단계가 바뀔 때만 Cowork가 고친다(T4 정본 SYSTEM.md의 첫 판)."
consumers: "사장(Obsidian·GitHub) · Cowork 세션(재개 입구) · redesign-t4(정본 흡수)"
source_decision: "duet-1022 Q1 a (2026-10-22 18:41) = obs-1022b Q1 a ③"
---

# 투자_V2 로드맵

목표(2026-10-10 재설계): **자동 운영이 먼저** — 매일 결정론 코어가 수집 → 대조 → 판정 → 주문표 → 기록 → 예외 알림을 하고, 사장은 결과만 받는다. 일상 손 0(주문 1단계의 키움 입력만 예외). 설계: [automation-redesign-2026-10-10.md](automation-redesign-2026-10-10.md) 4절.

## 1. 재설계 단계
| 단계 | 내용 | 상태(2026-10-26 KST) | 관제판 |
|---|---|---|---|
| T0 | 결정·지침 교체·관제판 정리 | 끝(10/10) | — |
| T1 | 코어 v1: 수집·자동 대조·노출 | 끝 — 기록 모드 켜짐(10/15). **10/22~10/24 대조 HOLD**(체결 날짜 해석·출금 증거, recon-hold-2026-10-23.md). 수정 병합 5a289b8·b2cd42e(10/25), 첫 확인 10/27 06:15 | recon-dt · cashflow-api-gap |
| T2 | 판정·주문표·일지 자동 | 병합(10/12), **비교 모드**(auto_core.json decision_mode compare). "켜" 조건 전부: R1 리플레이 통과 · R2 비교 차이 전부 분류(10/26 t2-gate REMOVE-v2로 "5거래일 연속" 대신 — C1 창 COMPARED 5일 이상, trig: 4건 미분류) · 대조 OK 연속 5회(0/5) · CORE_BUG 해소 커밋 목록(없음) · C1 독립 계산기 일치 10세션(공식 셈 2/10 — 사전 등록 53행, 10/22~24 오류 — eqnone4 c1a6a6e로 수정) · C2 매수 주문표 1건 일치(0) · R3 사장 "켜"(redesign-t2-builder-prompt-2026-10-10.md 46-48행, t2-rc-preregistration-2026-10-14.md 22·25행) | redesign-t2 · t2-rc |
| T3 | 개발 파이프라인·문서 자동 커밋 | 끝(10/10~), Cowork가 일반 변경 병합(dc-dev 10/22) | — |
| T4 | 옛 경로 은퇴·docs/claude → archive/·정본 3개(SYSTEM·RUNBOOK·DECISIONS) | T2 뒤 대기 | redesign-t4 |
| T5 | 주문 2단계(코어가 키움 주문 대기 → 사장 승인 1번) | 조건 미충족 | redesign-t5 |

주문 단계(헌법 §14): 1 주문표(지금, ORDER_INTENT_ONLY) → 2 주문마다 승인(HUMAN_PER_ORDER) → 3 봉투 안 자동(GUARDED_AUTOMATIC_APPROVAL). 헌법의 마지막 단계 AUTONOMOUS_GUARDED_EXECUTION은 이 로드맵 범위 밖. 시스템은 스스로 단계를 올리지 않는다.

성과 측정: 결정별 SPY 대비 채점 코드는 있으나 SPY 일봉 입력이 없어 벤치마크 MISSING(journal-scores 2026-10-25, 진단 D10 미결). 채점 결론에는 30건 필요, 지금 주문표 1건.

## 2. 창구 (duet-1022, 2026-10-22)
- 지금: Cowork 투자_V2 대화 = 결정 · 08:50 코어 결과 알림 · 09:25 비서 제안 · 주간 팀장회의(일 09:47).
- Duet 열린 뒤: 1주 시험([계약 문서](duet-interface-contract-2026-10-22.md)) → 통과하면 창구 정리(duet-redesign 3-2). 실행층(PC 자동 코어)은 그대로.

## 3. 다음 순번
- **맨 앞(자동 운영 막힘 — 헌법 §3 141-157행)**: 대조 HOLD 해소 확인(10/27 06:15, 안 풀리면 11/03 전 결정 — 조회 창 14일) → t2rc 독립 계산기 재실행 확인 → "켜" 관문 R2 연속 셈 제거(t2-gate: REMOVE-v2 10/26 16:07 → Judge 2차 PASS, 효력 — 남은 일: trig: 차이 4건 분류·CORE_BUG 해소 커밋 목록) · SPY 벤치마크 공급(d10: REUSE 10/26, 개발 큐 d10-spy + 사장 정책 1줄). 근거 roadmap-fix-decisions-2026-10-26.md.
- 개발 자리(진행 3개 상한): 비서 v1.1(duet-sec) → 일지 확인 코드 제거(duet-r3a) → 연구 자료 자동 목록(duet-idx) → 결정 원장 K-1(duet-k1, CLAUDE.md 정리 묶음).
- 권한·한도 자리(한 번에 1개, 착수 조건이 먼저 채워지는 순): 2027 달력(cal-2027) · 자동 코어 입력 문서 보호(duet-q4-coreinput) → 대조 확인 코드 경로 판단(duet-q4-recon).
- 평가일: 플레이북 11/07(pb-1022) · 주간 팀장회의 2단계 = 보고 4회 뒤(org-setup).

## 4. 이 노트 고치는 규칙
단계 상태가 바뀌면 그 세션의 Cowork가 관제판과 함께 이 표를 고친다(dev-dashboard-protocol.md). 작업 하나하나의 진행은 관제판이 원본이다.
