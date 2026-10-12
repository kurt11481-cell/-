---
id: external-claude-trading-desk-prompt-review-2026-10-12
type: external-review
status: current
as_of: 2026-10-12
tickers: [ALL]
evidence_grade: D
consumers: 관제판 결정 작업 ext-desk-score-fix(사용자 결정) · f-evo-loop(30건 뒤 규칙 약점 자동 발견 — 채점기 결과가 입력) · redesign-t5 / f-trading-infra-gap-review-2026-10-12.md(주문 2단계 참고만, 변경 없음)
weekly_user_touch: 0 (일회성: 결정 1줄 — 2026-10-12 a로 결정됨 + dev-merge 1번)
summary: "Alex Jane Street" 명의 메일의 Claude Code 24시간 리서치 데스크 프롬프트 검토. Jane Street 출처 근거 없음. 구조 대부분은 투자_V2와 중복이거나 원칙과 충돌. 단 그 프롬프트의 '어제 종가' 채점 약점이 투자_V2 채점기(카드 ANALYSIS)에도 같은 구조로 있음을 확인 — 채점 시작가 수정과 미구현 '주문표 성과 채점'을 결정 작업으로 올림.
---

# 외부 자료 검토 — "Claude Opus 5.5 & Fable 5.1 24/7 Trading Team" 메일 프롬프트

- 원본: 사용자가 대화에 첨부한 Gmail 화면 캡처(2026-10-12 수신). 발신 표시 "Alex Jane Street" / gmail.com 주소, Gmail '외부(External)' 표시. 원문 링크 없음.
- 성격: 읽기 전용 검토(K0). 코드·정책·상태·예약 작업·주문 변경 없음. order_authority=false, quantity_authority=none. RESEARCH_FINDING != PRODUCTION_POLICY.

## 0. 결론

1. 빈 폴더의 Claude Code에 붙여 넣으면 에이전트 8개·파이썬 도구·git 저장소를 만들고, 클라우드 야간 수집 + 매 거래일 09:00 ET 아침 데스크가 순위 보고서와 Public.com 주문 티켓을 내는 설치형 프롬프트다. 주문은 사용자가 `execute <id>`를 입력할 때만 MCP place_order + 권한 승인창으로 나간다.
2. Jane Street가 쓴다는 근거 없음(개인 gmail, 본문이 "내 Public 포트폴리오"). 성과 수치 주장 없음 → 증거 등급 D.
3. 구조 대부분은 투자_V2에 이미 있거나(LLM은 가장자리, 쓰기 구역 분리, 반론 답변, 사후 채점) 원칙과 충돌한다(LLM이 최종 판단, 자료 없어도 진행, 에이전트 도구로 주문).
4. 가져올 것 1개(측정 정확도): 채점 시작가를 '결정 뒤 첫 실행 가능 종가'로. 이 프롬프트의 약점(어제 종가 기준 채점)을 투자_V2 채점기에서 확인하니 같은 구조가 있었다(4절).
5. 함께: 재설계에 계획만 있고 구현·관제판 등록이 안 된 '코어 주문표 성과 자동 채점'을 같은 기준으로 올린다(6절).

## 1. 주장 정리 (사실 / 외부 확인 / 미확인 / 가설)

| 구분 | 내용 |
|---|---|
| 사실(프롬프트 자체 진술) | 사람이 모든 주문 승인, 하루 1회 결정, 하루 티켓 3개, 1회 위험 0.5%, 종목 최대 5%, 20거래일 평가, 등급 5단계와 적중 정의(4~5등급 α>0, 1~2등급 α<0, 3등급 α 절댓값<2%), 예약·클라우드 실행은 주문 도구 금지 |
| 외부 확인 | Public.com 공식 MCP 서버 존재: 조회 13·사전 점검 7·쓰기 10 도구(place_order·cancel_order·flatten_and_go_short 등). Public 안내 글은 "All orders are live"(모의 모드 없음), 2026-08-20 갱신 — 8절 출처 |
| 미확인 | Jane Street 사용 여부(확인 필요, 근거 없음), "Claude Code >= 2.1.293" 버전 요건 |
| 가설·미검증 | 관심도 점수 공식(매체 수 최대 5 + 24시간 내 8-K 3 + 거래량 2배 2 + 갭 3% 2), 에이전트 구성의 효과 — 성과·검증 자료 없음 |

## 2. 구조 요약

- 입력값: 유니버스(시총 $2B·일평균 거래대금 $20M 이상), 벤치마크 SPY, 후보 5, 티켓 3, 평가 20거래일, 실적 변화 기준 5%.
- 에이전트: scout·tape(Haiku) → fundamentals·catalyst(Sonnet) → bull·bear·risk(Opus) → pm(Fable 5.1, 실패 시 Opus 재실행). 출력 120단어 이내, 숫자마다 출처·시각, 원시 응답은 cache/에만.
- 야간(클라우드): 주문 도구 없음, intel/에만 기록 후 git push. 장전 8-K·실적 / 15:30~18:59 실적 대 가이던스 / 19:00 이후 장후 공시·10거래일 실적 일정 / 토요일 주간 적중률·전략 제안.
- 아침 데스크(로컬): 시계 확인 → 지난 판정 채점 → 관심도 상위 후보 → 분석 병렬 → 찬반 토론 → 위험(라이브 계좌 + size.py) → PM 등급·티켓 → 12개 점검 → 보고서·push.

## 3. 이 프롬프트의 약점

1. 채점 기준가 = 어제 종가(ledger reference price). 관심도 점수가 갭에 가산점을 주므로, 장전 갭이 이미 난 종목을 고르고 그 갭까지 적중으로 센다 — 방향성 있는 편향.
2. 자료가 없어도 "미검증·신뢰도 낮춤"으로 진행(fail-open).
3. 주문 도구가 deny가 아니라 ask. `git push *` 전체 허용(강제 push 포함).
4. 등급·티켓을 LLM(PM)이 결정. 모델 대체 시 판단 주체가 바뀌어도 기록만 남음.
5. 포트폴리오 총 노출·레버리지·섹터 집중 한도 없음(risk 에이전트 재량).

## 4. 투자_V2 채점기 '어제 종가' 편향 확인 (읽기 전용, 2026-10-12)

판정: 카드 분석(ANALYSIS) 채점에 같은 구조가 있다. 사용자 실제 행동(USER) 채점은 실행 세션 종가 기준이라 LOC 체결이면 문제 없다. 자동 코어 주문표는 성과 채점 자체가 아직 없다.

근거(파일:줄):
- `manage-us-stock-strategy/scripts/portfolio_review_journal.py:366,384` — 카드 결정의 decision_session = 팩트팩 `expected_completed_us_session`(결정 시점에 이미 끝난 마지막 미국 세션).
- `manage-us-stock-strategy/scripts/score_decision_journal.py:219,158` — ANALYSIS 채점 시작 = decision_session 종가. 결정은 그 종가 뒤에 내려지고, 시스템 기본 주문 방식(LOC)으로 가장 빨리 실행할 수 있는 값은 다음 세션 종가다. 그 사이(장후·밤사이·다음 세션) 움직임이 결정의 성적에 섞인다.
- `portfolio_review_journal.py:432` — USER 항목은 effective_session을 생략하면 decision_session으로 채워진다 → 생략 시 같은 편향.
- `auto_core_decide.py:11`, `auto_core_tickets.py:417` — 코어 ticket_outcome은 체결 분류(체결·일부·미체결)만 한다. `automation-redesign-2026-10-10.md:125`의 "코어 주문표의 성과를 자동 채점(주문표 vs 아무것도 안 함 vs 사용자 실제 행동)"은 T2에서 구현되지 않았다(`redesign-t2-builder-report-2026-10-10.md:27,32` — 채점기는 카드 항목만 보고 수정하지 않음). 관제판에도 해당 작업이 없다(2026-10-12 조회).

실측 — 현재 일지의 카드 결정 3건(모두 HOLD, decision_as_of 2026-10-02T08:17Z = 04:17 ET 장전, decision_session 2026-10-01). 종가 = `workspace/outputs/regular-session-closes/history`의 키움 30분봉 근사 종가(채점기와 같은 출처):

| 종목 | 10/2 하루(실행 전 구간) | 현 방식 5세션 (10/1→10/8) | 첫 실행 가능 종가 기준 5세션 (10/2→10/9) | 차이 |
|---|---|---|---|---|
| MVLL | +3.10% | +4.27% | +1.49% | +2.8%p |
| NBIS | +4.44% | −5.44% | −8.93% | +3.5%p |
| SOXL | +6.45% | −7.34% | −14.64% | +7.3%p |

- 이번 3건은 모두 현 방식이 HOLD 성적을 좋게 보이게 했다. 방향은 그날 움직임에 따라 바뀐다. 카드가 장후 공시·밤사이 뉴스에 반응해 쓰이면 방향성 편향이 된다(외부 프롬프트와 같은 구조).
- 현재 피해: 없음. 결론 허용 기준 30건(`MIN_SCORED_FOR_CONCLUSION`) 미달이고, 마지막 채점 보고서(`workspace/outputs/journal-scores/20261004T225915Z`)도 결정 0건. 다만 f-evo-loop가 이 숫자를 입력으로 쓰므로 그 재개 전에 고쳐야 한다.
- 좋은 점(유지): 목표 세션 종가가 평가 시각 이전이어야만 사용(미래 정보 차단), 분할 의심 시 NOT_SCORABLE, SPY는 REFERENCE_ONLY.

## 5. 요소별 대조·판정

| 외부 프롬프트 요소 | 투자_V2 현황 | 판정 |
|---|---|---|
| 채점 시작가(어제 종가) | 4절 — 같은 구조 | **P1 채택 권고** |
| 주문표 성과 채점(주문표 vs 무행동 vs 사용자) | 재설계 125행 계획, 미구현·관제판 없음 | **P2 등록 권고(P1과 한 작업)** |
| 서브에이전트 출력 계약(120단어·핵심 숫자 3개·경로, 숫자마다 출처·시각, 원시 응답 금지) | 작업 원칙: 긴 출력은 서브에이전트로 격리, 경로·요약만 | 중복 → NO_CHANGE |
| 쓰기 구역 분리(야간 intel/만, desk/는 데스크장만) | 06:40 연구 기록이 코어의 유일한 LLM 입력, 통합 점검 쓰기 예외 2개 | 중복 |
| 웹·뉴스는 데이터일 뿐 지시 아님 | 통합 점검 규칙 파일·SAVE 메모 등 지시문에 있음. Next 샌디스크 지시문에는 없음(코어 입력 아님, 제안 모드) | 중복. Next 샌디스크는 다음 지시문 교체 때 한 줄 추가(별도 손길 없음) |
| 매수 등급은 약세론 3개에 글로 답 | M6 결정 영수증 "가장 강한 반대" | 중복 |
| 비거래일·16:00 ET 뒤면 티켓 없음 | 코어 거래일 달력 고정, 자료 신선도 관문 | 중복 |
| 10거래일 실적 일정 | 실적 금지 구간(미확인 = 차단) | 중복(더 엄격) |
| 관심도 점수 기반 뉴스 발굴 | Next 샌디스크·관심 명단 R2.1(장기 병목 thesis) | 새 규칙 후보 → FX-1009 동결(fx-6 전 금지), 장기 thesis 원칙과도 다름 → NO_CHANGE. fx-6 뒤 다시 보더라도 P1 기준 채점이 전제 |
| 자료 없으면 신뢰도 낮추고 진행 | fail closed(연구 기록 없으면 매수 티켓 전부 차단) | 충돌 → 넣지 않음 |
| PM(LLM)이 등급·티켓 결정 | 결정론 코어, 규칙이 LLM 출력보다 우선 | 충돌 → 넣지 않음 |
| `execute <id>` → 시세·사전 점검 재실행 → place_order + 승인창(ask) | T5 설계: 제출 모듈은 에이전트 도구 밖, Windows 작업 스크립트만 주문 API 호출(`f-trading-infra-gap-review-2026-10-12.md:44`) | 승인된 설계가 더 엄격 → NO_CHANGE. T5 참고: 예약 실행에서 주문 도구는 ask가 아니라 deny |
| 1회 위험 0.5%·손절 기반 수량 | 노출 예산 1.55·종목 0.4배, 장기 thesis는 가격선만으로 폐기 안 함 | 철학 다름 → NO_CHANGE |
| ledger 적중률·lessons·patterns·주간 전략 제안 | decision_journal + 채점기, f-evo-loop(30건 뒤), 기본 처분 규칙 | 중복 |

## 6. 제안과 기본 처분 — 관제판 결정 작업 `ext-desk-score-fix`

일반 변경(개발 파이프라인), Cold Path 측정 코드. 권한·한도·주문·정책 무관.

- P1. 카드 ANALYSIS 채점 시작 = decision_as_of 뒤에 마감하는 첫 세션의 종가(시스템 기본 LOC 기준). USER 항목이 effective_session을 생략해 decision_session과 같으면 같은 규칙. 표시용으로 `pre_action_move`(decision_session 종가 → 시작 종가) 칸 추가. 경계: LOC 접수 마감 뒤·장 마감 전 결정은 다음 세션(키움 LOC 마감 시각 확인 필요).
- P2. 코어 주문표 성과 채점(재설계 125행): 시작가 = 주문표 세션 종가(체결이면 키움 체결 기록 ust21150 가격), 비교 = 같은 시작가의 '아무것도 안 함'과 사용자 실제 행동. 비교 모드 주문표도 가상 결과로 채점(등급 D, "켜" 판단 참고용). 5/20/60세션, 30건 전 결론 금지(기존 규칙 재사용).
- 선택지: a) P1+P2 함께 개발 파이프라인(권장 — P2가 "켜" 판단 근거를 만든다) · b) P1만 · c) 현행 유지.
- 기본 처분(답 없음, 기한 2026-10-19): c 현행 유지(NO_CHANGE). 30건 전이라 당장 판단 피해 없음. f-evo-loop 재개 전에 다시 묻는다.
- 사용자 손길: 일상 0. 일회성 = 결정 1줄 + 병합 1번(`.\tools\dev-merge.ps1 ext-desk-score-fix`).
- 활성 개발 작업: 2026-10-12 관제판 조회 기준 0건(active는 운용 작업 swap-soxl-pwr 1건) → 상한 3 이내.

### 결정 기록

- 2026-10-12 20:04 KST 사용자 "결정 ext-desk-score-fix: a" — P1+P2 함께 개발 파이프라인으로 진행.
- 반영: Builder 지시문 `docs/claude/score-fix-builder-prompt.md`(dev-run id `score-fix`, general, Builder opus·high), 큐 `docs/claude/_dev-queue/score-fix.txt`. 파이프라인 결과는 `workspace/outputs/dev-runs/LATEST.json` → READY_TO_MERGE면 사용자 `.\tools\dev-merge.ps1 score-fix` 1번.
- 병합 뒤 Cowork 확인: 실제 일지로 채점기를 읽기 전용 실행해 4절 표의 '첫 실행 가능 종가 기준' 값(시작 10/2, 5세션 +1.49%/−8.93%/−14.64%)과 대조.
- 2026-10-12 결과: dev-run score-fix READY_TO_MERGE(Judge PASS, 새 실패 0, Ran 2910→2927) → 병합 d70aac2(20:57 KST). 병합 뒤 실제 일지로 채점기 실행(출력은 저장소 밖 임시 폴더, 실행 뒤 삭제): ANALYSIS 3건 시작 2026-10-02, pre_action_move +3.10%/+4.44%/+6.45%, 5세션 vs_cash +1.4909%/−8.9295%/−14.6371% — 4절 표와 일치. 주문표 채점은 아직 0건(코어 첫 decide 전). 남은 확인 필요: 키움 LOC 접수 마감 시각(시작가 경계).

## 7. 외부 주장 원장

등록 대상 없음 — 종목·시장 주장이 없는 방법론 자료이고, 방법론 판정은 이 메모로 갈음한다.

## 8. 출처

- Public.com, "Trade stocks, options, crypto using Claude"(2026-08-20 갱신): https://public.com/learn/trade-stocks-options-crypto-using-claude
- LobeHub, publicdotcom MCP server 도구 목록(Unvalidated 표시): https://lobehub.com/mcp/publicdotcom-publicdotcom-mcp-server
- 저장소 파일:줄 — 4절·5절에 표기.
