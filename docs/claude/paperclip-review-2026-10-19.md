---
id: paperclip-review-2026-10-19
type: review
status: 결정 완료 (Q1 = 주간 팀장회의 v1.3에 포함 2026-10-19 23:07 · Q2 a 2026-10-19 23:12 → v1.4)
as_of: 2026-10-19 22:30 KST
tickers: [ALL]
class: K0 검토(문서만). 설치·실행·런타임·정책·예약 작업 변경 0
authority: order_authority=false · quantity_authority=none · execution_quantity=null
evidence: paperclipai/paperclip shallow clone f96a1e6(2026-10-19, MIT, 추적 파일 10,731개) 원문 직접 확인(파일:줄) + 투자_V2 관제판 done 150건 집계(2026-10-19 22:2x) + 기존 검토 2건 대조
consumers: 관제판 paperclip-1019(결정) · docs/claude/future-tools-roadmap-2026-10-05.md 진행 기록 · 주간 팀장회의 v1.3 후보(docs/claude/ceo-weekly-v1-change-2026-10-19.md) · docs/claude/company-org-plan-2026-10-19.md 2단계 평가
summary: Paperclip(AI 에이전트 회사 운영 도구)을 사장 요청으로 다시 검토 — 도구는 기결정대로 들이지 않고, 주간 팀장회의에 붙일 작은 장치 2개(예약 작업 출근부·반복 지적 구분)만 채택 권장, 3개는 측정 뒤 결정, 나머지는 이미 있음.
---

# Paperclip 검토 — 운용회사 구조에 붙일 것 추리기 (2026-10-19)

## 0. 결론
- **도구 설치: 안 함(기결정 유지).** 10/05 "패턴 차용, 도구 보류"(`future-tools-roadmap-2026-10-05.md:101-114`), 10/12 "보류 유지"(사용자 승인, `f-trading-infra-gap-review-2026-10-12.md:32`). 재검토 조건("예약 작업이 관제판으로 감당 안 되고 비용 초과 반복", "승인 채널을 직접 만들기 어려울 때")이 아직 안 왔다. 사실도 그대로다: 상시 서비스는 systemd·launchd만(`cli/src/services/service-manager.ts:11`, Windows 없음), 추적 파일 10,731개(10/05 약 8,300개에서 늘어남), Node 24.11+·내장 Postgres, 사용 통계 전송이 기본으로 켜짐(`README.md:554`).
- **채택 권장 2개(주간 팀장회의 v1.3으로 묶어 지시문 승인 1회):** ① 예약 작업 출근부 ② 반복 지적 "새로/계속" 구분.
- **측정 뒤 결정 3개:** 제안 담당 배정, 비용 예산, 결정 "수정 요청" 답.
- **지금은 불필요 1개:** 완료 주장 검증(이번 주 완료 40건 모두 근거 칸 있음).
- **이미 있음 7개:** 아래 3절.

## 1. 채택 권장 (v1.3 — 권한·정책 변화 없음, 사람 손 일상 0)

| # | Paperclip 기능(원문) | 우리 공백(원문) | 붙일 것 | 크기 |
|---|---|---|---|---|
| A1 | 하트비트 감시 — "know when agents are alive, idle, or stuck"(`doc/GOAL.md:41`), 대시보드 "Stale tasks"(`docs/guides/board-operator/dashboard.md`) | 예약 작업들이 제때 돌았는지 아무도 보지 않는다. 주간 팀장회의 5)는 list_triggers에서 이름·수정 시각·cron·다음 실행만 뽑고 마지막 실행 시각·상태는 버린다(지시문 5단계). 코어만 08:50 알림이 날짜를 본다(`f-trading-infra-gap-review-2026-10-12.md` ①) | 운영관리팀 "예약 작업 출근부": 켜진 반복 작업마다 cron으로 직전 예정 시각을 계산해 마지막 실행(last_fired_at)·상태(last_run.status)와 비교 → 안 돌았거나 실패면 발견 F-OPS-6, 대시보드에 출근부 표 | 작음(지시문 5·6단계 + ceo.py) |
| A3 | 정지 지문 — 같은 정지 상태는 다시 검토하지 않고, 상태가 바뀌면 다시 깨움(`doc/TASK-WATCHDOG.md:89-94`) | 같은 관제판 지적·발견이 매주 다시 🟠로 세어진다(예: README를 가리키는 두 작업의 R2, 변경 기록 2-1 ④·5절) | 발견·관제판 점검 줄마다 "새로 / 계속(n주째)"를 붙이고, 알림 문구는 새로 생긴 것만 센다. 계속 중인 것은 대시보드에 그대로 보인다(숨기지 않음) | 작음(ceo.py만, 지시문 sha 갱신) |

## 2. 측정 뒤 결정 (지금은 현행 유지)

| # | Paperclip 기능(원문) | 우리 상황 | 결정 시점 |
|---|---|---|---|
| B1 | 언급만으로는 일이 배정되지 않는다 — "A mention alone does not assign work or wake another agent"(`README.md:469`), 다른 팀에 일 넘기기는 담당 지정 작업으로(courier, `doc/execution-semantics.md:317-319`) | 팀장 제안·협조 부탁은 보고에만 있고 맡아서 처리할 실행자가 깨지 않는다 → 사장이 Cowork를 열 때까지 기다린다(숨은 사람 손). 선택지: (a) 현행 (b) 회의가 후속 목록 파일을 쓰고 Cowork 세션 시작 때 읽기 (c) 일요일 후속 처리 예약 작업이 안전한 종류(관제판 기록 갱신·문서 정리)만 처리 — (c)는 "예약 작업은 관제판에 쓰지 않는다" 규칙을 바꾸므로 사장 결정 | 2단계 평가(보고 4회 뒤). 근거 = 대시보드 "지난주 제안 추적"의 "이번 주에도 같은 발견" 비율 |
| B2 | 회사·에이전트 예산, 80% 경고·100% 자동 정지(`docs/guides/board-operator/costs-and-budgets.md`) | 예약 작업 1회 토큰 비용을 아직 못 잰다(확인 필요, 변경 기록 5절). 잴 수 없으면 한도도 걸 수 없다 | 측정 수단 확인 뒤(예약 세션에서 사용량 확인 방법 — 확인 필요) |
| B3 | 승인 흐름 대기 → 승인/거절/수정 요청 → 재제출(`docs/guides/board-operator/approvals.md`) | 사장 답은 자유 문장 하나. "수정해서 다시 올려라"의 정해진 길이 없다. 다만 지금까지 사장 결정 0건 | 첫 실제 결정이 생긴 뒤 |
| A2 | 멈춘 일 = 주장, 근거로 확인(`doc/TASK-WATCHDOG.md:28-30, 102`) | 관제판 done 150건 중 근거 칸(commit·doc·verify)이 모두 빈 것 7건(전부 이전 주), 10/11~10/17 완료 40건은 0건 | 비면 다시 본다(2단계 평가 때 한 번 더 집계) |

## 3. 이미 있음 (NO_CHANGE)
- 실행 정책(실행자 ≠ 검토자, 검토·승인 단계, `docs/guides/execution-policy.md`) → Builder → 별도 세션 Judge → 사용자 병합.
- 활동 기록(`docs/guides/board-operator/activity-log.md`) → 관제판 log·git 이력·README 변경 기록.
- 설정 변경 이력·되돌리기(`README.md:216`) → 지시문 파일·sha256·되돌리기 판(v1.0·v1.1 보관).
- 목표 정렬(`README.md:125`) → 헌법 §3 순위로 팀장 제안 순위, 관제판 why·stream.
- 작업 체크아웃 잠금(`README.md:213`) → if_version·expectedMtimeMs·sha256 대조로 겹쳐 쓰기 방지(충돌 사례 없음).
- 연결 도구 허용/먼저 묻기/끔(`README.md:163`) → 키움 주문 도구 금지·주문 게이트 0(주문 2단계 T5 때 승인 채널로 다시 본다 — 기결정).
- 변화가 있을 때만 갱신·일일 토큰 한도(`docs/guides/board-operator/status-cards.md`) → 예외일 때만 알림(코어 결과 알림).
- 모의·대본 결과 ≠ 실제 증거(`doc/evals.md:1-12`) → 증거 등급 A~D.
- 조직도·보고선(`docs/guides/board-operator/org-structure.md`) → 4팀·감사실·위원회(`company-org-plan-2026-10-19.md`).

## 4. 하지 않는 것
- Paperclip 설치·Docker·상시 서비스·새 데이터베이스 — 0절.
- 예산 자동 정지·후속 처리 예약 작업 — 2절 조건 전에는 만들지 않는다.

## 5. 결정 (관제판 paperclip-1019)
- 질문: Q1 A1 예약 작업 출근부(a 채택 / b 보류) · Q2 A3 새로·계속 구분(a 채택 / b 보류). 둘 다 a면 주간 팀장회의 v1.3으로 묶어 지시문 승인 1회.
- 권장: Q1 a, Q2 a — 둘 다 결정론 코드, 권한·정책 변화 없음, 사장 신호(급한 것만 보이기)를 좋게 한다.
- 기한 2026-10-24(다음 회의 전날). 무응답 = 현행 유지(v1.2 그대로).
- 답 양식: `결정 paperclip-1019: Q1 a, Q2 a`

## 6. 확인 필요
- 예약 세션의 list_triggers 응답에서 last_fired_at·last_run이 모든 작업에 오는지(이 세션 조회에서는 4건 모두 있음).
- 토큰 사용량을 예약 세션 안에서 잴 수 있는지(B2).

## 7. 결정 기록 (덧붙이기만)
- 2026-10-19 23:07 KST — Q1(A1 예약 작업 출근부): 사장 요청(모든 점검 결과를 팀에 — 자동 운영 코어 결과 알림 전달 확인)에 필요해 주간 팀장회의 v1.3에 넣어 사용자 승인·재서명(F-OPS-6, 받은 결과 S-OPS-1).
- 2026-10-19 23:12 KST — 사용자 원문 "결정 paperclip-1019: Q2 a" → 23:39 주간 팀장회의 v1.4: 발견·관제판 점검 줄 새로/계속 n주째, 알림은 새로 것만, 색은 그대로(docs/claude/ceo-weekly-v1-change-2026-10-19.md 10절).
