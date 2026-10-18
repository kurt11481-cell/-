---
id: analysis-linkage-map
type: design
status: current
as_of: 2026-10-05 (2026-10-12 재설계 T2 행 추가)
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

## 1. 새 작업·변경 체크리스트 (Cowork에서 예약·분석을 만들거나 바꿀 때 필수)
1. 쓰는 곳: 파일(저장소 workspace/outputs/<종류>/ 또는 docs/claude/) 또는 Artifact 저장소. 같은 이름은 덮어쓰지 않거나 날짜로 나눈다.
2. 머리말: id · type · status · as_of · tickers · evidence(등급) · consumers(읽는 작업) · summary.
3. 증거 분리: 공식 사실(출처 URL) / 외부 참고(SAVE·보도·커뮤니티, 강도 0) / 가격 참고(판정 미사용)를 절로 나눈다. 공식 사실과 외부 참고를 한 줄에 섞지 않는다.
4. 캐시는 권한을 물려받지 않는다: 다른 작업의 기록에 있는 공식 사실을 "충족"·"예" 근거로 쓰려면 URL 원문을 확인하거나 출처를 그대로 표시한다(fail-open 체크리스트: 대체 출처의 권한 상속 금지).
5. 읽는 쪽은 기록을 못 읽어도 기존 방식으로 진행하고 "확인 필요"만 남긴다(Cold Path 장애가 Hot Path를 막지 않게).
6. 같은 사실의 반복 검색을 줄이는 방향으로 읽는다(먼저 기록, 그 이후 것만 새로 검색).
7. 권한 변화 없음: 연결은 읽기·표시만 넓힌다. 주문·수량·정책·상태 파일 권한은 바뀌지 않는다(order_authority=false).

## 2. 현재 연결 지도

| 작업(주기) | 쓰는 곳 | 읽는 작업 | 상태 |
|---|---|---|---|
| SAVE 시장환경 메모 v2.2(매일 06:15) | workspace/outputs/save-daily-offline-replay/LATEST_MARKET_ENV_MEMO.md + web-feed/<날짜>/ + LATEST_TICKER_LEADS.json(종목 단서, 2026-10-14 st-1014 B) | 통합 점검 4), 통합 점검 6)(단서 → 공식 확인 → 연구 기록), Next 샌디스크 L1, 월요일 점검 2), 카드 작성(INDEX) | 연결(단서 파일 첫 실행 10/15) |
| 월요일 개장 전 점검(월 21:20) | SAVE 메모 + workspace/outputs/pre-open/<날짜>-monday.md | 통합 점검 2-1, Next 샌디스크 L1b, Cowork(예약 누락) | 연결(10/5, 첫 기록 확인) |
| 개장 전 이벤트 일회성(10/14·10/15·11/6·11/10·11/13) | workspace/outputs/pre-open/<날짜>-<이벤트>.md | 통합 점검 2-1(공식 사실 재사용·TSMC→S2·S3·U2), Next 샌디스크 L1b, M6 v2·카드(INDEX) | 연결(10/5) |
| 개장 전 이벤트 점검(일정표) v1.1(평일 09:20 ET, 2026-10-13 결정 ev-calendar-auto a, 10/14 v1.1) | workspace/outputs/pre-open/<날짜>-events.md — "## 공식 사실"·"## 다음 작업이 확인할 항목"(빅테크 실적 → SOXL S3 판정)·오늘 주문표 이벤트 노출(event_calendar.py, event-ctx2 병합 뒤). 일정 없는 날은 기록 없음. 입력: docs/claude/event-calendar.json, LATEST_DECISION.json(읽기만), 케이스 판정표 docs/claude/event-strategy-2026-10-13.md 4절 | 통합 점검 2-1(두 절·머리말만 읽음), Next 샌디스크 L1b, 카드·M6(INDEX), 이벤트 대비 전략 | 연결(v1.1 10/14 00:2x 교체, 첫 실행 10/14 09:20 ET) |
| 주문표 이벤트 노출 event-ctx2(개발 중, 일반 등급 — 원안 event-ctx 폐기: 코어가 일정표를 읽지 않음) | 채점 보고서 ticket_results[].event_exposure(사후 분류, own_earnings 포함)·event_calendar, 요약 event_overnight / CLI event_calendar.py(읽기 전용) | 개장 전 이벤트 점검 v1.1 0-1, fx-6 뒤 r-rec1 사전 등록("이벤트 날 매수 보류" 판정 자료) | 예정(큐 등록 10/14) |
| 보유·관심 통합 점검 v3.12.4(화~토 06:40, 2026-10-14 교체) | 통합점검 대시보드 Artifact 저장소 runs | 개장 전 일회성 3), 월요일 4b, Next 샌디스크 L2, MVLL 알림, Cowork 카드 | 연결 |
| 외부자료 PDF 처리(수시, 스킬) | 외부자료 .md 캐시 + docs/claude/external-claims-ledger.md | 통합 점검 7), Next 샌디스크 L3·R4 | 연결 |
| 카드·M6 비교(Cowork 수시) | docs/claude 카드 문서 + INDEX | 통합 점검(문서 읽기), Next 샌디스크, 관심 명단 | 연결 |
| Next 샌디스크 발굴 v3.1(토 07:32) | docs/claude/next-sandisk-scan-*.md + library/research/ | INDEX → 관심 명단 재평가(예정)·M6 v2·카드 (사람 수락 뒤) | 연결 |
| 종목 분석·옵션 분석(Chat/수시) | chatgpt_종목분석결과/종목분석·옵션분석/<티커_날짜>/ | INDEX 포인터 → 카드·Next 샌디스크·M6 | 연결(10/5 INDEX 등록, SNDK) |
| 미국주식 현황판(화~토 09:10) | 현황판 Artifact snapshots | 사람(표시). 계좌·가격은 키움 재조회 원칙이라 다른 작업은 읽지 않음 | 표시 전용(의도) |
| 관제판 주간 점검(토 10:50) | 알림만 | 사람(관제판) | 메타(분석 아님) |
| SEC 섀도 수집기(Windows 작업, 월~금 22:00·화~토 12:30) | workspace/outputs/official-event-intake/sec/ | 통합 점검 2-2)(v3.11) | 연결(10/5 적용, 10/6 06:40 첫 실행 확인 대기) |
| 주문 지시서(봉인 SHADOW 시범, Cowork·트리거 날 09:30~12:00) | docs/claude/order-instructions/OI-<날짜>-<티커>-<번호>.md (봉인 해시·사용자 결정·결과) · 설계 order-instruction-design-2026-10-06.md | 다음 날 Cowork 대조(결과 분류)·다음 카드/M6 카드(INDEX)·관제판 oi-*·통합점검 대시보드 "주문 지시" 칸(저장소 orders, 공개 뒤 Cowork 기록, 10/7 — dashboard-order-panel-2026-10-07.md). 통합 점검 직접 읽기는 v3.12 승인 뒤 | 시범(10/6 설계, 첫 회 10/8로 이동) |
| 주문가 옵션 층(가격 결정 때마다, 10/7 사용자 승인) | 주문 지시서 본문 4줄 · 수시 가격 제안 문서(chatgpt_종목분석결과/…) 4줄 · 설계 order-instruction-design-2026-10-06.md 7-5 | 같은 지시서의 가격 칸 대조·경고 → 다음 날 Cowork 대조·채점(원장 30건 뒤 가격 산식 반영 검증, K3) | 연결(10/7 첫 적용 MVLL ②) |
| 관심 명단 주간 재평가(예정, 미생성) | docs/claude/watchlist-registry.json history | 통합 점검(관심 명단) | 예정 |
| 시장 시나리오 지침 SCN-27H1(사용자 지정 10/9, 2027-06-30까지) | docs/claude/market-scenario-27h1-2026-10-09.md (3절 트리거 표는 판단 때 부록 A로 갱신) | Cowork 수시: 카드·M6·주문 지시서 위원회·발굴 수락(CLAUDE.md 1줄) · Next 샌디스크 수시(INDEX) · 통합 점검(로더 3단계)·Next 샌디스크 월간(10))·관심 명단 재채점(추가 단계) | 연결(10/9 22:27, 사용자 FX 동결 예외) |
| 연구 기록(통합 점검 로더 4단계, 화~토 06:40 실행 끝, 재설계 T2) | workspace/outputs/research-records/<날짜>/research-record.json(실적일 p-earn 형식·회사 공식 사실·뿌리 테제 훼손·그날 점검 기록 사본, 스키마 auto-core-research-record) | 자동 운영 코어 decide(07:45, 08:30까지 기다림 — 없으면 매수 막힘) · 다음 날 연구 기록(실적일 VERIFIED 이어받기) | 연결(10/12 13:24 로더 교체, 첫 실행 10/13) |
| 자동 운영 코어 decide(화~토 07:45, Windows 작업 InvestmentV2-AutoCoreDecide, 재설계 T2) | workspace/outputs/auto-core/<날짜>/decision.json·compare.json·s7/, LATEST_DECISION.json | 결과 알림(08:50: 푸시 · 통합점검 대시보드 runs.core · 기록 모드 orders 새 문서) · 다음 decide(원장·미분류 주문표) · Cowork 비교 모드 B7 설명(redesign-t2-compare-explained.json) · 일지 decision_journal(기록 모드만) | 연결(10/12 병합, 비교 모드) |
| 카드 근거 등록부(Cowork, 카드 수락·재작성 때) | docs/claude/card-evidence-registry.json(스키마 auto-core-card-registry: 카드 표 근거·트리거·절 해시·수락 줄) | 자동 운영 코어 decide(주문표 자격·정적 근거) | 연결 — **카드를 고치거나 수락하는 Cowork 세션은 같은 세션에서 등록부 항목·절 해시를 갱신하고 커밋 목록에 넣는다**(안 하면 그 종목 주문표가 CARD_SECTION_CHANGED·REGISTRY_UNCOMMITTED로 막힘) |
| 결정 일지 채점(Cowork 수시 — 평가·카드·M6 세션에서 읽기 전용 실행, 2026-10-15 결정 learn-loop a. 주 1회 자동 = Windows 작업 InvestmentV2-JournalScore 일 09:20 `--learning`(evo-s2 병합 c3bd452·사용자 등록 2026-10-16, 첫 예약 실행 10/18: 보고서 OK·WEEKLY_LATEST 없음 = 실행기 결함, 수정 evo-s3 — docs/claude/f-evo-loop-s1-weekly-check-2026-10-18.md). 정의: docs/claude/f-evo-loop-s1-preregistration-2026-10-16.md) | workspace/outputs/journal-scores/<시각>/journal-scores.json(5·20·60세션 현금 대비, 주문표 반사실 D; learning 블록 = 관문별 소급·매도 하한·시나리오 대역·트리거 종류·Museum 후보, 표시 전용 D) · workspace/outputs/journal-scores/WEEKLY_LATEST.json | Cowork 카드·M6 세션("직전 결정 결과" + docs/claude/failure-museum.json 칸 채우기), 관문·근거 규칙 병합 확인 세션(docs/claude/gate-rule-epochs.json 한 줄), 관제판 f-evo-loop 2단계 발견, PC 상태 점검 → 08:50 알림 ⑭(주간 작업 실패, evo-s3 병합 뒤), 다음 리플레이 사전 등록, docs/claude/cpi-shock-review-2026-10-15.md 같은 사후 평가 | 연결(주 1회 자동 + Cowork 수시) — WEEKLY_LATEST는 evo-s3 병합 전까지 안 생김(2026-10-18 확인) |

## 3. 미연결·남은 일
- SEC 수집기 → 통합 점검: 연결 완료(10/5 v3.11 적용). 10/6 첫 실행 확인과 5회 대조(onlyInSearch)는 관제판 e-filing-k1·e-filing-k4.
- 종목 분석 폴더(chatgpt_종목분석결과)는 새 분석이 생길 때마다 INDEX "문서 밖 최신본"에 1줄 추가(수동, 체크리스트 5).
- 관제판 주간 점검에 "연결 지도에 없는 예약 작업" 탐지 규칙 추가는 미적용(필요 시 별도 승인).
- 재설계 T2(10/12): 연구 기록 → decide → 결과 알림·대시보드 연결 완료. 카드 등록부 갱신은 Cowork 수동 절차(위 표). 판정 대조 5거래일 뒤 사용자 "켜"로 기록 모드.
- SCN-27H1 → 예약 작업 3개 연결 완료(10/9 22:27, 사용자 FX 동결 예외). 통합 점검을 v3.12.3-L로 바꿀 때 로더 '3단계' 블록을 옮길 것(fx-2, scheduled-prompts/README.md 변경 기록).
