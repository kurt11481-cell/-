---
id: analysis-linkage-map
type: design
status: current
as_of: 2026-10-05 (2026-10-12 재설계 T2 행 추가, 2026-11-07 시나리오 확률 매일 점검·llm-iccheck 행 추가, 2026-11-07 ops-link-1107 연결표 6칸 — 0절 1줄·1절 머리·1절 8번·2절 칸 2개)
tickers: [ALL]
evidence_grade: n/a (운영 규칙)
summary: 모든 분석·조회·발굴 결과가 어디에 남고 누가 읽는지의 지도와, 새 작업을 만들 때 지켜야 할 연결 규칙(사용자 상시 지시 2026-10-05).
---

# 분석 결과 연결 지도 (2026-10-05)

## 0. 규칙 (사용자 상시 지시, 2026-10-05)
"서로 연계되지 않으면 분석하는 의미가 없다. 앞으로 생성되는 모든 분석 작업 결과는 시스템 내 다른 분석·조회·발굴 작업들과 서로 연계되도록 한다."

- 모든 분석·조회·발굴 작업(예약·수시·Cowork·Claude Code 산출물)은 결과를 **다른 작업이 읽을 수 있는 곳**에 남긴다. 알림이나 대화로만 끝나는 분석은 만들지 않는다.
- 결과마다 **읽는 작업(소비자)을 최소 1개** 정하고, 그 소비자 쪽 지시문·절차에 읽기 단계를 함께 넣는다(쓰기만 하고 아무도 안 읽으면 연결이 아니다).
- 이 표에 1줄을 추가하고 library/INDEX.md(포인터)와 관제판 schedules를 갱신한다.
- 2026-11-07 사장 지시(ops-link-1107, "매번 새로 기능을 만들어 놔도 회사 행동까지 이어지지 않으면 의미가 없다"): 위 읽기 단계에 더해, 결과가 회사 행동(알림·주문 칸·카드·원장·규칙 후보, 주문표는 연구 기록 경유)까지 이어지는지와 끊기면 누가 아는지·칸마다 상태를 1절 8번 연결표로 설계 때 확인한다.

## 1. 새 작업·변경 체크리스트 (Cowork·사장실 스레드·대화형 Claude Code가 예약·분석·새 기능을 만들거나 바꿀 때 필수. 예약 작업이 실행될 때와 예약이 깨운 스레드 턴, Builder·Judge·하위 에이전트는 자기 지시문대로)
1. 쓰는 곳: 파일(저장소 workspace/outputs/<종류>/ 또는 docs/claude/) 또는 Artifact 저장소. 같은 이름은 덮어쓰지 않거나 날짜로 나눈다.
2. 머리말: id · type · status · as_of · tickers · evidence(등급) · consumers(읽는 작업) · summary.
3. 증거 분리: 공식 사실(출처 URL) / 외부 참고(SAVE·보도·커뮤니티, 강도 0) / 가격 참고(판정 미사용)를 절로 나눈다. 공식 사실과 외부 참고를 한 줄에 섞지 않는다.
4. 캐시는 권한을 물려받지 않는다: 다른 작업의 기록에 있는 공식 사실을 "충족"·"예" 근거로 쓰려면 URL 원문을 확인하거나 출처를 그대로 표시한다(fail-open 체크리스트: 대체 출처의 권한 상속 금지).
5. 읽는 쪽은 기록을 못 읽어도 기존 방식으로 진행하고 "확인 필요"만 남긴다(Cold Path 장애가 Hot Path를 막지 않게).
6. 같은 사실의 반복 검색을 줄이는 방향으로 읽는다(먼저 기록, 그 이후 것만 새로 검색).
7. 권한 변화 없음: 연결은 읽기·표시만 넓힌다. 주문·수량·정책·상태 파일 권한은 바뀌지 않는다(order_authority=false).
8. **연결표 6칸(2026-11-07 사장 지시 ops-link-1107 — docs/claude/ops-linkage-guideline-2026-11-07.md 3절)**: 새 기능·새 산출(파일·알림·화면 칸·점검)·예약 작업 만들기/바꾸기·전략 분석(갈래)을 제안하는 설계 문서에 아래 표를 붙인다. 표가 없거나 ⑥이 빈 제안은 제안이 아니다.
   | ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
   |---|---|---|---|---|---|
   - ②③⑤는 원문 행으로 적는다(지시문 파일:행, 코드 파일:행, 예약 trig id + 지시문 원본·보관본 행). 행이 아직 없으면 '끊김 — 메울 변경 · 승인 경로'를 같은 제안에 붙인다(사장 질문을 기다리지 않는다).
   - ④ 행동은 기존 경로만: 알림·대시보드 주문 칸·결정 카드·원장 판정·규칙 후보(헌법 §20 시험). 주문표는 06:40 연구 기록을 거치거나 §20을 통과한 규칙으로만 닿는다(CLAUDE.md 48~50행). 새 매매 규칙·새 종류의 징후 알림을 만들지 않는다(헌법 §2-1 3항 — 따로 승인).
   - ⑥ 상태 = 연결 / 끊김(메울 승인) / 의도적 없음. **'의도적 없음'은 그 '없음'을 다른 선택지와 나란히 보고 고른 사장 결정(카드 id 또는 결정 문서:행)이 있을 때만이다.** 문서 규칙(CONTEXT_ONLY 등)만 있거나, 사장 결정이 있어도 그 선택지가 없었으면 '끊김'으로 적어 사장에게 보인다.
   - 헌법 §2-1 6항(1.5.0, 2026-11-07 확정): 그런 사장 결정이 이미 있으면 인용하고 새로 묻지 않는다. 승인이 필요 없는 끊김은 제안한 자리에서 바로 메우고(§24 순서), 승인이 필요한 끊김은 그 승인 경로와 한 번에 묶어 올린다. 사장이 닫은 질문(결정 색인)은 '끊김(닫힌 질문)'으로 보이기만 하고 다시 제안하지 않는다. 답이 없으면 끊김으로 남기고 사정이 바뀌기 전에는 같은 것을 다시 묻지 않는다(§21).
   - 사람 손이 필요한 칸은 '사람 단계'로 표시하고 헌법 §3 결함인지 같은 자리에서 판단한다.
   - 늦추지 않는다: 줄이기·사건 대응 카드는 먼저 올리고 연결표는 같은 날 뒤에 붙인다(매도 쪽을 막지 않음).
   - 새 산출이 있는 개발 지시문(<id>-builder-prompt.md)은 '## 연결표'를 넣고 '## Judge 확인 항목'에 "연결표 ②③⑤의 원문 행 대조" 1줄을 둔다(Judge 공통 G8이 하나씩 본다).

## 2. 현재 연결 지도

| 작업(주기) | 쓰는 곳 | 읽는 작업 | 상태 | 바뀌는 행동(④) | 끊기면 누가 아나(⑤) |
|---|---|---|---|---|---|
| SAVE 시장환경 메모 v2.2(매일 06:15) | workspace/outputs/save-daily-offline-replay/LATEST_MARKET_ENV_MEMO.md + web-feed/<날짜>/ + LATEST_TICKER_LEADS.json(종목 단서, 2026-10-14 st-1014 B) | 통합 점검 4), 통합 점검 6)(단서 → 공식 확인 → 연구 기록), Next 샌디스크 L1, 월요일 점검 2), 카드 작성(INDEX) | 연결(단서 파일 첫 실행 10/15) | (소급 전) | (소급 전) |
| 월요일 개장 전 점검(월 21:20) | SAVE 메모 + workspace/outputs/pre-open/<날짜>-monday.md | 통합 점검 2-1, Next 샌디스크 L1b, Cowork(예약 누락) | 연결(10/5, 첫 기록 확인) | (소급 전) | (소급 전) |
| 개장 전 이벤트 일회성(10/14·10/15·11/6·11/10·11/13) | workspace/outputs/pre-open/<날짜>-<이벤트>.md | 통합 점검 2-1(공식 사실 재사용·TSMC→S2·S3·U2), Next 샌디스크 L1b, M6 v2·카드(INDEX) | 연결(10/5) | (소급 전) | (소급 전) |
| 개장 전 이벤트 점검(일정표) v1.1(평일 09:20 ET, 2026-10-13 결정 ev-calendar-auto a, 10/14 v1.1) | workspace/outputs/pre-open/<날짜>-events.md — "## 공식 사실"·"## 다음 작업이 확인할 항목"(빅테크 실적 → SOXL S3 판정)·오늘 주문표 이벤트 노출(event_calendar.py, event-ctx2 병합 뒤). 일정 없는 날은 기록 없음. 입력: docs/claude/event-calendar.json, LATEST_DECISION.json(읽기만), 케이스 판정표 docs/claude/event-strategy-2026-10-13.md 4절 | 통합 점검 2-1(두 절·머리말만 읽음), Next 샌디스크 L1b, 카드·M6(INDEX), 이벤트 대비 전략 | 연결(v1.1 10/14 00:2x 교체, 첫 실행 10/14 09:20 ET) | (소급 전) | (소급 전) |
| 주문표 이벤트 노출 event-ctx2(개발 중, 일반 등급 — 원안 event-ctx 폐기: 코어가 일정표를 읽지 않음) | 채점 보고서 ticket_results[].event_exposure(사후 분류, own_earnings 포함)·event_calendar, 요약 event_overnight / CLI event_calendar.py(읽기 전용) | 개장 전 이벤트 점검 v1.1 0-1, fx-6 뒤 r-rec1 사전 등록("이벤트 날 매수 보류" 판정 자료) | 예정(큐 등록 10/14) | (소급 전) | (소급 전) |
| 보유·관심 통합 점검 v3.12.4(화~토 06:40, 2026-10-14 교체) | 통합점검 대시보드 Artifact 저장소 runs | 개장 전 일회성 3), 월요일 4b, Next 샌디스크 L2, MVLL 알림, Cowork 카드 | 연결 | (소급 전) | (소급 전) |
| 외부자료 PDF 처리(수시, 스킬) | 외부자료 .md 캐시 + docs/claude/external-claims-ledger.md | 통합 점검 7), Next 샌디스크 L3·R4 | 연결 | (소급 전) | (소급 전) |
| 카드·M6 비교(Cowork 수시) | docs/claude 카드 문서 + INDEX | 통합 점검(문서 읽기), Next 샌디스크, 관심 명단 | 연결 | (소급 전) | (소급 전) |
| Next 샌디스크 발굴 v3.2(토 07:32, 2026-10-19 v3.2 주간 결과 파일) | docs/claude/next-sandisk-scan-*.md + library/research/(월간) · workspace/outputs/next-sandisk-weekly/<날짜>.md(주간) | INDEX → 관심 명단 재평가(예정)·M6 v2·카드 (사람 수락 뒤) · 주간 팀장회의 투자리서치 받은 결과 S-RES-6 | 연결 | (소급 전) | (소급 전) |
| 종목 분석·옵션 분석(Chat/수시) | chatgpt_종목분석결과/종목분석·옵션분석/<티커_날짜>/ | INDEX 포인터 → 카드·Next 샌디스크·M6 | 연결(10/5 INDEX 등록, SNDK) | (소급 전) | (소급 전) |
| 미국주식 현황판(화~토 09:10) | 현황판 Artifact snapshots | 사람(표시). 계좌·가격은 키움 재조회 원칙이라 다른 작업은 읽지 않음 | 표시 전용(의도) | (소급 전) | (소급 전) |
| 주간 팀장회의 v1.4(일 09:47, 2026-10-19 — 관제판 주간 점검을 바꿔 씀, 결정 org-setup; v1.1 대시보드, v1.2 팀 간 연계, v1.4 새로/계속·비서 보고 대시보드, v1.3 팀별 받은 결과: 통합점검 runs·외부 자료 원장·SAVE 메모·Next 샌디스크·관심 명단 weeklyRun·개장 전 기록·이번 주 점검·검토 문서·예약 작업 출근부를 읽음) | docs/claude/ceo-weekly-report.md(매주 절 덧붙이기, 머리말 consumers) + 알림 1줄 + 대시보드 '주간 팀장회의'(보고 파일을 옮긴 자료, https://claude.ai/artifact/GccBmdQcQopX415T5TRFWN) | 사장(사용자) · 다음 주간 회의(결정·답 줄) · Cowork(`결정 ceo-<날짜>` 처리, dev-dashboard-protocol 3절) · 2단계 평가(company-org-plan 7절) · redesign-t4(법률 정리 안건) | 연결(첫 실행 10/19 수동) | (소급 전) | (소급 전) |
| SEC 섀도 수집기(Windows 작업, 월~금 22:00·화~토 12:30) | workspace/outputs/official-event-intake/sec/ | 통합 점검 2-2)(v3.11) | 연결(10/5 적용, 10/6 06:40 첫 실행 확인 대기) | (소급 전) | (소급 전) |
| 주문 지시서(봉인 SHADOW 시범, Cowork·트리거 날 09:30~12:00) | docs/claude/order-instructions/OI-<날짜>-<티커>-<번호>.md (봉인 해시·사용자 결정·결과) · 설계 order-instruction-design-2026-10-06.md | 다음 날 Cowork 대조(결과 분류)·다음 카드/M6 카드(INDEX)·관제판 oi-*·통합점검 대시보드 "주문 지시" 칸(저장소 orders, 공개 뒤 Cowork 기록, 10/7 — dashboard-order-panel-2026-10-07.md). 통합 점검 직접 읽기는 v3.12 승인 뒤 | 시범(10/6 설계, 첫 회 10/8로 이동) | (소급 전) | (소급 전) |
| 주문가 옵션 층(가격 결정 때마다, 10/7 사용자 승인) | 주문 지시서 본문 4줄 · 수시 가격 제안 문서(chatgpt_종목분석결과/…) 4줄 · 설계 order-instruction-design-2026-10-06.md 7-5 | 같은 지시서의 가격 칸 대조·경고 → 다음 날 Cowork 대조·채점(원장 30건 뒤 가격 산식 반영 검증, K3) | 연결(10/7 첫 적용 MVLL ②) | (소급 전) | (소급 전) |
| 관심 명단 주간 재평가(예정, 미생성) | docs/claude/watchlist-registry.json history | 통합 점검(관심 명단) | 예정 | (소급 전) | (소급 전) |
| 시장 시나리오 지침 SCN-27H1(사용자 지정 10/9, 2027-06-30까지) | docs/claude/market-scenario-27h1-2026-10-09.md (3절 트리거 표는 판단 때 부록 A로 갱신) | Cowork 수시: 카드·M6·주문 지시서 위원회·발굴 수락(CLAUDE.md 1줄) · Next 샌디스크 수시(INDEX) · 통합 점검(로더 3단계)·Next 샌디스크 월간(10))·관심 명단 재채점(추가 단계) | 연결(10/9 22:27, 사용자 FX 동결 예외) | (소급 전) | (소급 전) |
| 연구 기록(통합 점검 로더 4단계, 화~토 06:40 실행 끝, 재설계 T2) | workspace/outputs/research-records/<날짜>/research-record.json(실적일 p-earn 형식·회사 공식 사실·뿌리 테제 훼손·그날 점검 기록 사본, 스키마 auto-core-research-record) | 자동 운영 코어 decide(07:45, 08:30까지 기다림 — 없으면 매수 막힘) · 다음 날 연구 기록(실적일 VERIFIED 이어받기) | 연결(10/12 13:24 로더 교체, 첫 실행 10/13) | (소급 전) | (소급 전) |
| 자동 운영 코어 decide(화~토 07:45, Windows 작업 InvestmentV2-AutoCoreDecide, 재설계 T2) | workspace/outputs/auto-core/<날짜>/decision.json·compare.json·s7/, LATEST_DECISION.json | 결과 알림(08:50: 푸시 · 통합점검 대시보드 runs.core · 기록 모드 orders 새 문서) · 다음 decide(원장·미분류 주문표) · Cowork 비교 모드 B7 설명(redesign-t2-compare-explained.json) · 일지 decision_journal(기록 모드만) | 연결(10/12 병합, 비교 모드) | (소급 전) | (소급 전) |
| 카드 근거 등록부(Cowork, 카드 수락·재작성 때) | docs/claude/card-evidence-registry.json(스키마 auto-core-card-registry: 카드 표 근거·트리거·절 해시·수락 줄) | 자동 운영 코어 decide(주문표 자격·정적 근거) | 연결 — **카드를 고치거나 수락하는 Cowork 세션은 같은 세션에서 등록부 항목·절 해시를 갱신하고 커밋 목록에 넣는다**(안 하면 그 종목 주문표가 CARD_SECTION_CHANGED·REGISTRY_UNCOMMITTED로 막힘) | (소급 전) | (소급 전) |
| 결정 일지 채점(Cowork 수시 — 평가·카드·M6 세션에서 읽기 전용 실행, 2026-10-15 결정 learn-loop a. 주 1회 자동 = Windows 작업 InvestmentV2-JournalScore 일 09:20 `--learning`(evo-s2 병합 c3bd452·사용자 등록 2026-10-16, 첫 예약 실행 10/18: 보고서 OK·WEEKLY_LATEST 없음 = 실행기 결함, 수정 evo-s3 — docs/claude/f-evo-loop-s1-weekly-check-2026-10-18.md). 정의: docs/claude/f-evo-loop-s1-preregistration-2026-10-16.md) | workspace/outputs/journal-scores/<시각>/journal-scores.json(5·20·60세션 현금 대비, 주문표 반사실 D; learning 블록 = 관문별 소급·매도 하한·시나리오 대역·트리거 종류·Museum 후보, 표시 전용 D) · workspace/outputs/journal-scores/WEEKLY_LATEST.json | Cowork 카드·M6 세션("직전 결정 결과" + docs/claude/failure-museum.json 칸 채우기), 관문·근거 규칙 병합 확인 세션(docs/claude/gate-rule-epochs.json 한 줄), 관제판 f-evo-loop 2단계 발견, PC 상태 점검 → 08:50 알림 ⑭(주간 작업 실패, evo-s3 병합 67e781d), 다음 리플레이 사전 등록, docs/claude/cpi-shock-review-2026-10-15.md 같은 사후 평가 | 연결(주 1회 자동 + Cowork 수시) — 실행기 수정 evo-s3 병합 67e781d(2026-10-18), WEEKLY_LATEST 첫 확인 10/25 | (소급 전) | (소급 전) |
| 시나리오 확률 매일 점검 v2.1(클라우드 예약, 06:45·19:45 KST + 결과 시각 21:45·22:45, 사장 지시 2026-11-06 22:11·22:13, v2.1 적용 2026-11-07 08:24 KST — active-decisions.md 107·135행) | 프로젝트 공유 폴더 scenario-odds/(registry.json·responses.json·out/) · 관제판 db scenarios/<날짜> | 관제판 '시나리오 확률' 칸·'오늘 키움에 넣을 주문' 안 '시나리오 대응' · 문턱 넘음 → 회사 전략 점검(사장실) | 연결(2026-11-07 적용) | (소급 전) | (소급 전) |
| API 시범 1 기록 대조 검토자 llm-iccheck(시범, 2026-11-07 병합 559efb9 · 첫 실행 사장 수동 11/07, 매일 실행은 작업 2 실행기 등록·켜기 승인 뒤 07:30 KST) | workspace/outputs/llm/iccheck/<날짜>/review.json·alert.md·failed.md · 사용량 workspace/outputs/llm/usage.jsonl | 사장실 스레드의 10거래일 채점(docs/claude/llm-iccheck-score.md). 화면 연결 없음 — 합격(맞은 비율 ≥ 70%) 때만 통합점검 대시보드 연결을 따로 제안 | 시범(채점 중) | (소급 전) | (소급 전) |

## 3. 미연결·남은 일
- SEC 수집기 → 통합 점검: 연결 완료(10/5 v3.11 적용). 10/6 첫 실행 확인과 5회 대조(onlyInSearch)는 관제판 e-filing-k1·e-filing-k4.
- 종목 분석 폴더(chatgpt_종목분석결과)는 새 분석이 생길 때마다 INDEX "문서 밖 최신본"에 1줄 추가(수동, 체크리스트 5).
- 관제판 주간 점검에 "연결 지도에 없는 예약 작업" 탐지 규칙 추가는 미적용(필요 시 별도 승인).
- 재설계 T2(10/12): 연구 기록 → decide → 결과 알림·대시보드 연결 완료. 카드 등록부 갱신은 Cowork 수동 절차(위 표). 판정 대조 5거래일 뒤 사용자 "켜"로 기록 모드.
- SCN-27H1 → 예약 작업 3개 연결 완료(10/9 22:27, 사용자 FX 동결 예외). 통합 점검을 v3.12.3-L로 바꿀 때 로더 '3단계' 블록을 옮길 것(fx-2, scheduled-prompts/README.md 변경 기록).
