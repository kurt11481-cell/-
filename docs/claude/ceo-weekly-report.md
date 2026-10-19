---
id: ceo-weekly-report
type: report
status: current
as_of: 각 주 절 머리(최신 = 맨 아래)
tickers: [ALL]
evidence: 코어·대조·채점·관제판 값은 결과 파일 그대로(등급은 원 파일 따름) / 팀장 제안·결정 문장 = 주간 팀장회의 LLM(근거 F-id) / 판정·매매 근거 아님
consumers: [사장(사용자) · 다음 주간 팀장회의(결정·답 줄) · Cowork(결정 ceo-<날짜> 처리) · 2단계 평가(docs/claude/company-org-plan-2026-10-19.md 7절) · redesign-t4(법률 정리 안건)]
summary: 투자_V2 주간 팀장회의 → 사장 보고. 매주 일요일 절을 덧붙인다(덧붙이기만). 조직·규칙 = docs/claude/company-org-plan-2026-10-19.md. 답 줄 형식 = 그 결정 줄 바로 아래 "  - 답: <원문>(<YYYY-MM-DD HH:MM KST>, Cowork)". 답이 없고 기한이 지난 결정은 다음 회의가 5절에 "기본값 기록"으로 닫는다.
---

# 주간 경영보고 (투자_V2)

## 주간 경영보고 2026-10-19 (기간 2026-10-11~2026-10-17) — 회사 상태 🟠 · 사장님 결정 0건(⚠ 이번 주 0건 · 답 대기 0건 · 지난 보고 없음)
<!-- id: ceo-2026-10-19 -->
### 1. 운용 (코어 파일 값 그대로, 기준 2026-10-17 · 모드 compare)
- 노출 E 1.28 (WITHIN_BAND, 세션 2026-10-16) · 멈춤: 신규 매수, 추가 매수 · 계좌 검토선 review(첫 쿠션 -7.5%)
- 종목 고점 검토: MVLL review · NBIS review · SOXL review
- 이번 주 주문표 0건 · 열린 주문표 0건 · 결과 기록 0건
### 2. 팀별
- 운영관리: 코어 정상 4/5(폴더 있는 날 5) · 예외 알림 0건 · 코어가 요청한 사람 손(주문 입력 제외) 0건 · PC 상태 WARN (2026-10-17) · 관제판 점검 발견 4
- 투자리서치: 연구 기록 OK 5/5 · 공식 사실 0건 · 이번 주 카드 수락 PLTR(2026-10-17) · 관심 명단 변경 2026-10-17 candidates-add PLTR,CRWD/ · 카드 {"holding": 3, "watch": 7}
- 연구개발: 진행 개발 2/3 · 권한·한도 변경 0/1 · 이번 주 완료 40건 · 최근 개발 실행 evo-s3 MERGED 2026-10-18 · 채점 주간 출력 없음
- 법률: CLAUDE.md 17515바이트 기준값 기록(첫 실행) · AGENTS.md 11507바이트 기준값 기록(첫 실행) · 정책 파일 수정 2건 · 예약 지시문·설정 수정 10건
팀장 제안:
- [운영관리] 10/13 판정(decide)의 HOLD(G1_S7_FAIL_CLOSED) 이후 10/14~17은 코어 정상 — 현행 유지하고 다음 주 재발 여부만 본다. — 근거 F-OPS-1-1013 · 순위 2 · 알림만
- [운영관리] 관제판 점검 4건 중 자동 운영 코어 결과 알림은 예약 지시문 v2.3인데 관제판 표기가 v2.2라 관제판 기록 갱신이 필요하고, 나머지 2건은 하위 폴더 문서(scheduled-prompts/README.md)를 점검기가 못 찾은 것이라 경로 확인이 필요하다. — 근거 F-OPS-4 · 순위 2 · 알림만
- [투자리서치] 제안 없음
- [연구개발] 판단 성적 채점 주간 출력(WEEKLY_LATEST)이 아직 없다 — 관제판 기록상 10/18 첫 예약 실행이 실행기 결함으로 실패했고 수정이 병합됐으므로, 다음 예약 실행(10/25 09:20)에서 생성 여부만 확인한다. — 근거 F-RND-3 · 순위 5 · 알림만
- [법률] 이번 주 정책 파일 2개(auto_core.json, alert_policy.json)가 수정됐다 — 사용자 승인 기록과 일치하는지 대조 필요(내용은 열지 않음). — 근거 F-LEG-2 · 순위 1 · 알림만
- [법률] 예약 지시문·설정 수정 10건은 이름 목록만 확인했고, 승인 이력과의 대조는 확인 필요로 둔다. — 근거 F-LEG-3 · 순위 2 · 알림만
### 3. 감사실 (원문 그대로)
- Judge 보고서(이번 주 수정): hwm-fix-judge-report.md PASS / t2rc-judge3-report-2026-10-15.md PASS / t2rc-judge2-report-2026-10-15.md FAIL / t2rc-judge-report-2026-10-15.md FAIL / rrec-rg1-judge-report.md PASS / t2-equity-cash-judge-report-2026-10-13.md PASS / redesign-t3c-judge-report-2026-10-12.md 판정 줄 없음 / redesign-t2-judge2-report-2026-10-11.md 판정 줄 없음 · 파이프라인 최근 실행 evo-s3 MERGED 2026-10-18
- 독립 대조 일별: 10-13 결과 없음 · 10-14 결과 없음 · 10-15 MATCH(C1 셈) · 10-16 MATCH(C1 셈) · 10-17 MATCH(C1 셈)
- C1 누계(관제판 redesign-t2 인용): "C1 10/20(화) 08:40 대조부터 0/10"
### 4. 사장님 결정
- 관제판 결정함 대기 0건: 없음
- 이번 주 새 결정 없음
### 5. 알림만
- 기본값으로 닫힌 결정 없음
- F-OPS-1-1013 [운영관리] 2026-10-13 코어 daily OK · decide HOLD — decide G1_S7_FAIL_CLOSED
- F-OPS-4 [운영관리] 관제판 점검 발견 4건(7절 원문)
- F-RND-3 [연구개발] 판단 성적 채점 주간 출력 없음
- F-LEG-2 [법률] 정책 파일 수정(이름·시각만, 승인 정책 포함): auto_core.json, alert_policy.json
- F-LEG-3 [법률] 예약 지시문·설정 수정 10건: t2-rc C5 12주 일몰 알림 (1회), t2-rc C4 6주 빈도 알림 (1회), DRAM 후보 재검토 (SK hynix 실적 뒤), t2rc-corefix2 개발 실행 확인
### 6. 다음 주
- 10-19 일회성 예약: 10/16 종가 확정 재확인 (L2 수락 1단계)
- 10-21 메타 3Q 실적(장 마감 뒤)
- 10-22 BE 실적(AFTER_CLOSE)
### 7. 관제판 점검 원문
```text
RESULT 4건 | 검사한 작업 183개 · 지금 할 수 있는 일 4개
R1 자동 운영 코어 결과 알림 (화~토 08:50): 예약 작업 수정 10/18 07:38 > 관제판 기록 10/17 12:10 (sch-autocore-alert)
R1 자동 운영 코어 결과 알림 (화~토 08:50): 지시문 v2.3 ≠ 관제판 표기 v2.2 (sch-autocore-alert)
R2 wl-v33-check 바꾼 관심 명단 주간 작업이 처음 돌 때 잘 됐는지 보기: 문서를 찾지 못함 scheduled-prompts/README.md (확인 필요)
R2 split-weekly-general 관심·후보 종목이 주식분할을 하면 주간 재채점이 멈추지 않게 하기: 문서를 찾지 못함 scheduled-prompts/README.md (확인 필요)
R1 제외: Windows 작업 8건 · 관제판에 올리지 않는 단발성/종료 예약 8건
```
<!-- ceo-state {"claude_md": [17515, "c669e6a9c03aaeef7b644cf704054917803ebc50c4e01deca074310c57809847"], "agents_md": [11507, "621c139f6042ffbe8c6999eafe195170568d0ecd76b59f9e3027da542bbb9149"], "d_hist": [0]} -->
