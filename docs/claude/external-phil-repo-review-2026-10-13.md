---
id: external-phil-repo-review-2026-10-13
type: external-review
status: current — 결정 완료 2026-10-13 22:30 KST 사용자 원문 "결정 ev-calendar-auto: a" → 일정표 docs/claude/event-calendar.json + 반복 예약 '개장 전 이벤트 점검(일정표) v1'(trig_015WVdwRscJ2tQqjPputAxsU) 생성. 나머지 NO_CHANGE
as_of: 2026-10-13
tickers: [ALL]
evidence_grade: D (외부 저장소의 자기 기록. 성과는 저장소 journal 원자료로 독립 재계산, phil 코드는 실행하지 않음)
consumers: 관제판 ev-calendar-auto(결정) · 이벤트 대비 전략 작업(재개 때 1단계) · f-evo-loop(관문 반사실 채점·자기 수정 교훈) · redesign-t5 / f-trading-infra-gap C2·C3(설계 참고, 변경 없음)
weekly_user_touch: 0 (일회성: 결정 1줄)
summary: github.com/bennyjo/phil(HEAD 26e8a7a, 2026-10-13) — Claude Code가 Polymarket 단기 예측시장을 매시간 모의 거래하며 자기 전략 파일을 고치는 실험. 75일 성과는 시장 가격보다 나쁘다(모의 베팅 66건 −$17·ROI −5.2%, Brier 차 +0.061). 실거래 주문 0건. 쓸 만한 것은 전략이 아니라 운영 장치이고, 대부분은 투자_V2에 이미 있다. 새로 가져올 것 1개: 공식 일정표 기반 이벤트 점검(손으로 만든 일회성 예약 5개 대체).
---

# 외부 시스템 검토 — phil (자기 개선형 예측시장 트레이더, 2026-10-13)

- 권한: 읽기 전용 분석. 저장소는 이 세션 임시 폴더에 복제(깊이 50)해 읽기만 했고 phil 코드는 실행하지 않았다. 투자_V2 주문·정책·상태·카드·일지·규칙 변경 없음.
- 동결 확인: FX-1009(fx-6 전 새 규칙 후보·리플레이 주제 금지). 아래 제안 1은 표시·자동화(재설계 A2 허용 범위)이고 규칙 후보가 아니다.

## 0. 결론

1. 트레이딩 시스템으로는 우위가 없다. 75일(7/30~10/13) 모의 베팅 66건 −$17(투입 $330, −5.2%), 승리 32건 — 자기 추정 기대 43.2건, 시장 가격 기대 34.5건. 자기 확률이 시장보다 나쁘다(Brier 0.230 vs 0.170, 차 +0.061). 베팅 안 한 예측 1,826건도 시장과 같거나 약간 나쁘다(+0.0055). 실거래 장부에는 주문 행이 없다. 저장소 자체 분석도 "연구는 받은 가격과 같은 수준"(+0.0080 ± 0.0091)이라고 결론냈다.
2. 교훈은 투자_V2 방향을 지지한다. LLM이 75일 동안 자기 전략을 고쳤지만 우위는 생기지 않았고, 전략 파일은 9,254줄로 불었다. 반면 결정론 거부 관문(outside-view-veto·category-bar)은 LLM의 가장 나쁜 판단을 걸러냈다(거부된 예측 Brier 차 +0.024·+0.031 = 거부가 옳았음). "결정론 규칙 > LLM 출력, 규칙 변경은 사람 승인"을 그대로 둔다.
3. 운영 장치 대부분은 이미 있다: 보호 영역 경계(guarded files·개발 파이프라인 범위 검사), 키움 호출 직렬화(C2), 멱등·ACK_UNKNOWN(C3), 사전 등록·기본 처분, 재개 조건 관제판, 정직한 가상 체결(LOC 종가).
4. 새로 가져올 것 1개: phil의 `release_calendar.py` 교훈 "아무도 적어 두지 않은 발표는 아무도 지켜보지 않는다". 투자_V2의 개장 전 이벤트 점검은 손으로 만든 일회성 예약 5개(10/14·10/15·11/6·11/10·11/13)뿐이라 FOMC·ECB(10/29)·BOJ(10/30)·빅테크 실적·11/3 중간선거가 빠졌고 11/13 이후는 없다. 공식 일정표 파일 1개 + 반복 점검 1개로 바꾸는 것을 제안한다(4절). 답이 없으면 현행 유지.

## 1. 무엇인가

| 항목 | 내용 |
|---|---|
| 대상 | Polymarket 단기 시장(실적 발표·스포츠·경제 지표·뉴스). 코인 단기 등락 금지 |
| 운영 | 매시간 사이클(정산 → 채점 → 회고 → 전략 파일 수정 → 탐색·Haiku 선별 → 조사 → 예측 기록 → 모의 베팅 → 커밋), 15분 감시(가격 변동·새 시장·달력)로 조기 사이클, 매일 심층 회고가 시간별 수정을 유지·보완·되돌림 판정 |
| 소유 경계 | 보호(사람): `core/`·한도 `config/protected.json`·절차 `CYCLE.md`. 에이전트: `strategy/`(플레이북·위험·도구·탐색·속도). `loop.sh`가 보호 경로 수정을 되돌리고 CI가 `operator:` 접두어 없는 커밋의 보호 경로 변경을 실패 처리 |
| 실거래 | Pearl Connect 서명 경유 $1/건·하루 $5·10포지션, 정산된 증거가 양(+)인 edge class(현재 cross-market 1개)만. 자금 접근 코드는 `core/real.py` 하나 |
| 측정 | `brier_delta`(내 확률 vs 진입 시 시장 가격), 조사한 모든 후보의 예측 기록(베팅 안 한 것 포함), 거부된 후보의 반사실 장부(`counterfactual.py`), 고정된 예측 위 정책의 walk-forward 리플레이, 사전 등록 전방 시험(조건 충족 시 이슈 1회 자동 생성) |
| 동시성 | 클라우드·로컬 두 실행기 충돌(같은 다리 이중 베팅) 뒤 `lease.py`: main 위 파일 잠금, 빨리감기 푸시로 원자적 획득, 50분 TTL |

## 2. 성과 독립 재계산 (journal 원자료, D)

| 지표 | 값 |
|---|---|
| 모의 베팅 | 70건(정산 66, 열림 4), $5 고정 |
| 손익 | −$17.00 / $330 = −5.2% |
| 승리 수 | 32 (자기 추정 기대 43.2 · 시장 기대 34.5) → 자기 확신 과대 |
| Brier | 자기 0.2300 · 시장 0.1695 · 차 +0.0605(양수 = 시장보다 나쁨). 저장소 risk.json 기록(+0.061)과 일치 |
| edge class별 | other 40건 +$23.65(차 +0.005) · 미표기 18건 −$46.89(+0.126) · info-race 5건 +$11.23(+0.303) · book-devig 2건 · cross-market 1건 −$5 |
| 예측(베팅 외 포함) | 1,826건 차 +0.0055. 거부 사유별: outside-view-veto 250건 +0.024, category-bar 98건 +0.031, no-edge 683건 0.000, 실제 베팅 50건 +0.031 |
| 실거래 | real-ledger 56행 전부 settle(정리) 행, 주문 행 0 |

- 읽는 법: 표본이 작고 대부분 수익이 롱샷 2건에서 나왔다(저장소 기록). 우위 없음이 확정은 아니지만 "자기 개선 루프가 우위를 만든다"는 증거도 없다.

## 3. 요소별 판정 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)

| # | phil 요소 | 투자_V2 현재 | 판정 | 주간 사용자 손 |
|---|---|---|---|---|
| 1 | 공식 발표 일정 → 감시 달력 항목(`release_calendar.py`, 현재 휴면) | 손으로 만든 일회성 개장 전 점검 5개. 각 4.5KB 지시문 사본(10/6 키움 규칙 추가 때 5개를 각각 고침) | **REPLACE 제안(4절)** | 0 |
| 2 | 거부된 후보의 반사실 장부(관문별 비용·이득) | score-fix가 주문표(비교 모드 포함)의 vs_no_action을 채점. 관문에 막혀 주문표가 안 나온 날은 채점 없음 | 조건 뒤 입력(f-evo-loop) — 일별 `workspace/outputs/auto-core/<날짜>/decision.json`이 보존되면 나중에 소급 계산 가능. 지금 기록 안 해도 잃지 않음(보존 정책 확인 필요) | 0 |
| 3 | 실거래는 정산 증거가 양(+)인 유형만, 아주 작은 한도부터 | T5 질문 조건 = 1단계 10거래일 또는 주문표 5건 오류 0(운영 오류 기준) | T5 설계 입력: 첫 자동 제출 범위를 "성적이 확인된 주문표 유형"으로 좁히는 선택지(예: 위험 축소 매도 먼저). 권한 변경이라 T5 결정 때만 | 0 |
| 4 | 실행기 잠금(lease) | f-trading-infra-gap C2 "키움 호출 직렬화(파일 잠금) + 토큰 단일 소유" 후보 | REUSE — C2 설계 참고(TTL 자동 만료, 획득 실패 시 그 실행 중단, 잠금 쓰기는 한 곳) | 0 |
| 5 | 비멱등 주문 맹목 재시도 금지, 미대조 주문 있으면 새 주문 차단, 자금 접근 코드 1곳 | C3 설계(ACK_UNKNOWN 대조, 제출 전 미체결 조회, future_order_shadow idempotency_key) | REUSE | — |
| 6 | 보호 영역 되돌림 + CI 경계 검사 | auto-core guarded 파일 검사(F6), 개발 파이프라인 범위 검사·권한 승격(-ApproveAuthority), 설정 deny | REUSE | — |
| 7 | 사전 등록 전방 시험 자동 알림 | 사전 등록·기본 처분, 관제판 재개 조건, 토요일 관제판 점검 | REUSE | — |
| 8 | 미룬 의무의 운반체(매 실행이 읽는 파일), 다 끝난 항목 보관 이동 | 관제판 resume·next_action_for_cowork | REUSE | — |
| 9 | LLM이 매시간 전략·위험 파일을 직접 고침, 심층 회고가 감사 | 규칙 변경은 사용자 승인 + Judge, f-evo-loop는 표시 전용(EVOLUTION_4 상한) | 넣지 않음 — 권한 순서와 충돌, 2절 성과로도 근거 없음 | — |
| 10 | Haiku 하위 에이전트 무리로 300개 시장 선별 | Haiku는 기계적 작업만(10/8 사용자 승인) | 넣지 않음 — 선별은 투자 판단 | — |
| 11 | 매시간 사이클·15분 가격 감시 | 일봉·LOC 기준 하루 단위 코어 | 넣지 않음 — 비용 대비 이득 없음(장중 감시는 f-trading-infra-gap 3단계 항목) | — |
| 12 | 유료 외부 예측(mech) 2차 의견 | 외부 주장 근거 강도 0 | 넣지 않음 | — |

## 4. 제안 — 공식 일정표 기반 개장 전 이벤트 점검 (관제판 ev-calendar-auto)

- 문제(확인한 것): 예약 목록(2026-10-13 조회)의 이벤트 점검은 일회성 5개가 전부다 — 10/14 CPI, 10/15 TSMC+PPI, 11/6 고용, 11/10 CPI, 11/13 PPI. 공식 일정으로 확인한 ECB(10/29)·BOJ(10/30, 전망 보고서)와 11/3 중간선거, FOMC·빅테크 실적(날짜 확인 필요)이 빠졌고 11/13 뒤에는 아무것도 없다. 공통 규칙이 바뀌면 사본 5개를 각각 고쳐야 한다.
- 바꿀 모양(설계 개요, 구현은 승인 뒤):
  1. 일정표 파일 1개(예: `docs/claude/event-calendar.json`): 날짜·시각(ET/KST)·이벤트·공식 출처 URL·확인일. 공식 출처(BLS·연준·ECB·BOJ·기업 IR)로만 채우고 실적 일정은 auto-core earnings_calendar를 그대로 읽는다(중복 수집 없음).
  2. 반복 예약 1개(평일 개장 전): 오늘 일정표에 항목이 없으면 기록 없이 끝, 있으면 지금 일회성 점검과 같은 일(공식 결과·프리마켓 %·`workspace/outputs/pre-open/` 기록·푸시 1건).
  3. 첫 정상 실행 확인 뒤 남은 일회성 예약을 끈다.
- 경계: 표시·기록 전용, 근거 강도 0, 주문·관문·예산 연결 없음(event_risk_policy.json의 CPI·FOMC = CONTEXT_ONLY 그대로). 규칙 후보 아님 → FX-1009 동결 대상 아님(재설계 A2: 자동화 작업 허용).
- 사용자 손: 일상 0. 일회성: 결정 1줄 + 새 예약 승인 카드 1번.
- 이벤트 대비 전략 작업(10/13 시작 후 일정 확인 단계에서 멈춤)의 1단계와 겹치므로, 채택하면 그 작업을 재개할 때 같이 만든다.
- 기본 처분: 답이 없으면 현행 유지(일회성 5개 그대로).

## 5. 틀릴 수 있는 이유

- 예측시장(이진 결과, 가격 = 확률)과 주식(연속 수익, 확률 가격 없음)은 채점 방식이 다르다. phil의 "LLM ≈ 시장 가격" 결과를 주식 카드에 그대로 옮길 수는 없다.
- 깊이 50 복제라 커밋 역사 전체는 보지 않았다. 성과는 journal 파일 전체 기준이다.
- 저장소 기록(retro·결정 문서)은 자기 보고다. 재계산한 수치만 저널 원자료와 맞춰 봤다.

## 6. 확인 필요

- 일별 `workspace/outputs/auto-core/<날짜>/` 보존 정책(2번 소급 채점 가능 여부).
- FOMC 10월 회의일·빅테크 실적일(이벤트 대비 전략 작업에서 공식 출처로 확인).

## Sources

- https://github.com/bennyjo/phil (HEAD 26e8a7a, 2026-10-13 12:48 UTC): README.md, CLAUDE.md, CYCLE.md, REAL.md, config/protected.json, strategy/risk.json, core/{score,counterfactual,lease,watch,release_calendar,validate,replay,real}.py 머리 설명, .github/scripts/boundary.sh, loop.sh, journal/{ledger,forecasts,real-ledger}.jsonl, journal/screener-value-decision.md
- 투자_V2: 예약 목록(list_triggers 2026-10-13), docs/claude/scheduled-prompts/README.md, f-trading-infra-gap-review-2026-10-12.md(C2·C3), score_decision_journal.py(COUNTERFACTUAL_D), workspace/policies/event_risk_policy.json
- ECB 일정 https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html · BOJ 일정 https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm
