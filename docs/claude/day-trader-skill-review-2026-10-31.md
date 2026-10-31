---
id: day-trader-skill-review-2026-10-31
type: external-review
status: 검토 완료 — 스킬 묶음 설치 안 함(NO_CHANGE). P1(위험 지도 전·후 비교, 코드 0)은 사장 채택(2026-10-31 17:25 KST 결정 카드 "P1 적용", 9절). P2(SEC 숫자 표)는 기존 SEC 수집 규칙과 부딪혀 보류
as_of: 2026-10-31 13:55 KST
tools: [day-trader-skill v2.0.0 (Jakeschincariol/day-trader-skill, 커밋 3d0f4ef 2026-10-20, MIT)]
evidence_grade: D (외부 오픈소스 README·SKILL.md·소스 = 가설. Notion 소개 페이지 = 커뮤니티 자료)
consumers: 사장실(외부 트레이딩 도구 질문이 오면 trading-tools-review-2026-10-29.md와 함께 먼저 검색) · 재량 주문 전 점검을 받는 사장실 스레드(P1) · 카드 작성 세션(P2 재개 조건) · active-decisions.md(결정이 나면 한 줄)
default: NO_CHANGE (코드·설정·예약 작업·정책·상태·카드·코어 변경 0, 설치 0)
order_authority: false
quantity_authority: none
---

# 데이트레이더 스킬 11종 검토 (2026-10-31)

부딪히는 결정: 묶음 설치 = CLAUDE.md 19행(주문·키움 주문 도구 금지)과 정면 충돌. P2 = e-filing-feed-review-2026-10-05.md 3절 1·3번(Claude는 sec.gov를 스크립트로 가져오지 않음, 채택·통합 점검 v3.11에 반영)과 충돌 → 보류. P1 = 부딪히는 결정 없음(evolve-1029 위험 지도·사장 2026-10-29 "4가지 상황 승인"의 범위 안에서 입력 비중만 하나 더).

요청: 사장 2026-10-31 13:10 KST "1. 다음 도구 기능을 분석하라 2. 낡은 현재 시스템 진화 개선 도입할것을 찾아라 3. 설치 및 적용을 진행하라" + Notion 페이지(PICK IT 「클로드 주식 스킬 11개 — day-trader-skill」).
방법: Notion 공개 페이지 본문을 내려받아 읽음(사본: 프로젝트 파일 tool-review/day-trader-skill/notion-page-2026-10-31.txt). GitHub 저장소를 클라우드 컨테이너에 받아 README·SKILL.md 11개·소스 일부를 읽음. **외부 코드는 실행하지 않음**(테스트 포함 — 컨테이너 실행도 자동 판정에서 막힘). 회사PC는 읽기만.

## 0. 결론

**스킬 묶음은 설치하지 않는다(NO_CHANGE).** 이 묶음은 미국 주식 당일 매매(장중 5분봉 중심) 도구이고 주문 스킬(trader-broker)이 들어 있다. 그 스킬은 "buy it"·"execute"·"get me out" 같은 말에 반응해 증권사 MCP 주문을 부르도록 쓰여 있어(trader-broker/SKILL.md 2~17행), 키움 MCP가 붙은 회사PC에 들이면 안 된다. 설치 방식도 `.claude/`(보호 경로)나 플러그인 설정을 바꾼다.

가져올 만한 생각은 2개였고, 1개만 제안한다.

| 번호 | 순서 | 가져올 생각 | 우리 쪽 적용 | 판정 |
|---|---|---|---|---|
| P1 | REUSE | 타임머신의 "돈을 걸기 전에 결과를 먼저 본다" | 재량 매수 주문 전 점검에서 이미 승인된 위험 지도를 **지금 비중**과 **주문 후 비중**으로 두 번 계산해 차이를 보여 줌 | **제안**(코드 0) |
| P2 | ADD | 애널리스트의 "SEC에 낸 숫자를 기계로 읽는다" | SEC XBRL 분기 숫자 표 | **보류**(5-2절) |

```
[스킬 11개]
   ↓
[주문을 내는가?]
   ├─ 예 → [broker: 금지]
   └─ 아니오 ↓
[수량을 정하는가?]
   ├─ 예 → [budget: 재량 주문엔 수량 제안 안 함]
   └─ 아니오 ↓
[장중 5분봉 매매용인가?]
   ├─ 예 → [entry·scanner orb·alerts·exit: 해당 없음]
   └─ 아니오 ↓
[우리에게 이미 있나?]
   ├─ 있음 → [risk·news·scanner daily·pelosi: 그대로]
   └─ 생각만 쓸 만함 ↓
[가져올 생각]
   ├─ timemachine → P1 위험 지도 전·후 (제안)
   └─ analyst → P2 SEC 숫자 표 (보류)
```

## 1. 스킬 11개가 하는 일 (README·SKILL.md, 커밋 3d0f4ef)

| 명령 | 하는 일 | 자료 |
|---|---|---|
| trader-scanner | 장중: 개장 15분 범위 돌파(orb). 개장 전: 일봉 종가로 20일 고점 돌파·깃발·20일선 회복·과매도·과매도 반등(daily, SKILL.md 7~9행). 대상 = 미국 상장 약 5,900종목 | Nasdaq Trader 목록 · Yahoo 차트(비공식) |
| trader-news | 관심 종목 뉴스 제목·8-K·오늘 움직임 | Yahoo RSS · SEC `cgi-bin/browse-edgar` Atom(news.py 23·57행) |
| trader-entry | 5분봉마다 "대기/진입/만료" 판정 | Yahoo 1·5분봉 |
| trader-exit | 들어가기 전 손절가(범위 가운데 등)·목표가(위험의 n배)·장 마감 전 정리 시각 | 계획 파일 |
| trader-timemachine | 남은 장을 1만 번 다시 뽑기(최근 약 60일 같은 시각 5분봉 비율을 무작위로 이어 붙임, 시드 19) + 같은 규칙의 과거 실제 기록 → "동전 던지기" 같은 판정 1줄 | Yahoo 60일 5분봉 |
| trader-risk | 1회 최대 손실·하루 손실·하루 횟수·손익비·진입 시간대·크기·현금 → PASS/BLOCK | 자체 상태 파일 |
| trader-budget | 1회 최대 손실 ÷ 1주 위험으로 몇 주 살지 계산, 묶음 주문(손절·익절) 작성 | 계획 파일 |
| trader-broker | trader-risk PASS + 사장 "yes" + Claude 승인 창, 세 관문 뒤 Alpaca MCP `place_stock_order` 호출(모의 기본, SKILL.md 26~31행). IBKR 연결 안내 포함 | 증권사 MCP |
| trader-alerts | 가격·손절·목표·장 마감 전 알림 | Yahoo · Stooq |
| trader-analyst | SEC XBRL companyfacts로 분기 매출·이익률·순이익·희석 EPS·전년 대비. 4분기는 "10-K 연간 − 3개 분기"로 만들고 EPS는 근사(facts.py 26~28행). us-gaap 항목만 읽음(133행) | sec.gov company_tickers · data.sec.gov(이름·이메일 User-Agent 필요) |
| trader-pelosi | 하원 의원 주식 거래 신고서(PTR) 읽어 표로 | House Clerk 공개 자료(거래 뒤 최대 45일 늦음) |

원문 예시(테슬라 2026-10-19): 1만 번 중 목표 먼저 29.4% · 손절 먼저 25.5% · 둘 다 아님 45.1%, 과거 59일 중 33번 발생해 목표 13·손절 15·없음 5 → "Close to a coin flip". 제작자 예시이며 우리가 돌린 결과가 아니다.

## 2. 안전 대조

| 항목 | 내용 | 우리 규칙 |
|---|---|---|
| 주문 | trader-broker가 증권사 MCP 주문을 부름 | CLAUDE.md 19행 · 지침 1절 — **정면 충돌** |
| 설치 방식 | 플러그인 설치 또는 `~/.claude/skills/`·저장소 `.claude/skills/` 복사 | `.claude/**` = 보호 경로, Claude Code 세션은 .claude 설정 수정 금지(CLAUDE.md 수동 경로 항목). 회사PC 스레드 셸은 읽기만(지침 3절) |
| 가격 자료 | Yahoo 비공식 API·Stooq | 가격 증거 = 키움(지침 8절) |
| SEC 경로 | news.py가 `sec.gov/cgi-bin/browse-edgar` 사용 | robots `Disallow: /cgi-bin` → 스크립트에 넣지 않음(e-filing-feed-review-2026-10-05.md 22·53행) |
| SEC 수집 주체 | analyst·news는 대화 중 Claude가 스크립트로 sec.gov를 부름 | Claude는 sec.gov를 bash·python·curl로 가져오지 않고, 수집은 PC 작업 스케줄러의 저장소 스크립트가 사용자 User-Agent로 함(e-filing-feed-review 49~52행, 통합 점검 v3.11 변경 문서 86행) |
| 개인정보 | SEC 도구는 이름·이메일을 User-Agent로 보냄 | 사장 확인 없이 이메일을 외부로 보내지 않음 |
| 키·비밀 | Alpaca 키는 데스크톱 설정 파일에 | 비밀 읽기 금지(CLAUDE.md 46행) — broker를 안 들이면 해당 없음 |
| 외부 코드 실행 | 표준 라이브러리 파이썬, pip 없음. pelosi만 pdftotext를 subprocess로 부름 | 이번 검토에서는 실행하지 않음 |

## 3. 이미 있는 것과 겹침

| 스킬 기능 | 우리에게 있는 것 | 원문 |
|---|---|---|
| risk(한도 PASS/BLOCK) | 코어 관문(노출 목표 1.55·하드 상한 1.9·종목 0.4배·상품 승인·R-REC1) + 재량 주문 전 점검(통과/경고, 주문은 막지 않음) | order-process-2026-10-27.md 20~23행 · active-decisions.md G절 S7 승인 |
| budget(수량 계산) | 재량 주문에는 수량을 제안하지 않음(코어 주문표만 수량을 냄, 사장이 키움에 입력) | order-process-2026-10-27.md 23행 · CLAUDE.md 5~7행 |
| exit(손절·목표 먼저) | 카드의 무효·검토선(모든 보유 종목 고점 −30%에서 카드 재작성). SOXL 레버리지 손절선 매도표는 2026-10-28 사전 등록 시험 기준 미달(MVLL은 그 시험으로 닫지 않음) | active-decisions.md 140행(iv-1022, 작업 트리 기준) · rule1028-a3-results-2026-10-28.md 17·30행 |
| timemachine(돈 걸기 전 결과 보기) | 위험 지도(계좌 꼬리 손실 R1~R5, 표시 전용, 요청 때 계산) + "비중 확대·주문 전 점검이면 위험 지도 다시 계산할까요?" 먼저 묻기 | trading-tools-review-2026-10-29.md 225·239행(위험 지도 계산·보는 방법) · 사장실 스레드 「트레이딩 도구 4종 도입 검토」 2026-10-29 21:14 KST 제안 · 21:15 KST 사장 직접 입력 "4가지 상황 승인" |
| news(공시) | PC의 SEC submissions 결정론 수집기(사용자 User-Agent, robots 준수) + 통합 점검 연구 기록 | sec_official_event_intake.py 42행 · e-filing-feed-review 104~109행 · CLAUDE.md 48행 |
| analyst(SEC 숫자) | **코드는 없음** — 저장소 .py에서 companyfacts·xbrl 0건. 조사 문서 2건(에이전트 조사 보고서)이 SEC XBRL 값을 읽어 씀. LLM이 data.sec.gov JSON을 웹으로 읽으면 잘려서 틀린 사례가 있어 "쓰지 않음"으로 둠 | library/research/next-sandisk-2026-10-04/scan-power-nonai-roots.md 120행 · scn27h1-discovery-2026-10-10/sector-nonai.md 6행 · official-source-alt-paths-2026-10-04.md 24행 |
| scanner daily(개장 전 후보 찾기) | 관심 명단 주간 재채점(매주 토) + 매월 첫 토요일 전체 발굴. 수익 추구 신호는 5년 walk-forward 관문 + forward shadow 뒤에만(지금 fail-closed) | active-decisions.md G절 관심 명단 D1~D4 · trading-tools-review-2026-10-29.md 3절(alert_policy.json 612·614~624행 인용) |
| pelosi(의원 거래) | 외부 주장 원장(공개·커뮤니티 자료 = 가설 등록 경로) | external-claims-ledger.md · 지침 8절 |
| alerts | 자동 코어 예외 알림·통합 점검. 새 예약 작업은 만들지 않음 | active-decisions.md A절 board-merge '하지 않음' |
| entry·scanner orb(장중 돌파) | 해당 없음 — 장중 매매를 하지 않음(코어는 하루 1회 LOC 주문표) | CLAUDE.md 1~8행 |

## 4. 판단 순서 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)

| 순서 | 판정 |
|---|---|
| NO_CHANGE | 묶음 설치 안 함. 11개 모두 저장소·회사PC에 들이지 않음 |
| REMOVE/SIMPLIFY | broker는 어떤 PC에도 들이지 않음(주문). news의 cgi-bin 경로는 쓰지 않음 |
| REUSE | **P1** — 타임머신 생각은 이미 있는 위험 지도로 충분. 입력 비중만 "주문 후"로 한 번 더 |
| REPLACE | 없음 |
| ADD | P2(SEC 숫자 표)는 보류 — 5-2절 |

## 5. 제안

### 5-1 P1 (REUSE) 재량 매수 주문 전 점검 때 위험 지도 "전·후" 비교
- 언제: 사장이 `주문 전 점검: <티커> 매수 <수량> <가격>`을 보내고, 기존 규칙대로 "위험 지도 다시 계산할까요?"에 **사장 본인이 이 스레드에서 OK** 했을 때만(그 OK가 키움 읽기 조회 요청이 된다. 코디네이터 전달·예약 턴은 해당 없음). 매도 전 점검에는 묻지 않는다(승인된 4가지 상황에 없음). 체결 보고 뒤에는 지금처럼 1회.
- 무엇: 같은 docs/claude/risk_map.py(sha256 eb20909d…, trading-tools-review 12-1절 고정값과 같아야 함)를 비중 파일 2개로 돌린다(risk_map.py는 `--weights` 파일을 받으므로 코드 변경 0, 223행).
  1. 키움 읽기 조회(profile 실전계좌·mode real): 잔고(ust21070, 응답에 계좌번호 필드 없음)·현금(주문가능액)·보유 종목과 새 종목의 일봉. 금액은 버리고 비중만 남긴다(trading-tools-review 212행). 8005나 다른 인증 오류면 재인증 없이 멈추고 "확인 필요"(CLAUDE.md 56행).
  2. 비중 파일 ① 지금: 보유 비중 + 새 종목을 **비중 0**으로 넣어 두 계산의 종목 집합을 같게 한다(R5 적합 구간이 종목 집합에 따라 바뀜, risk_map.py 279~283행).
  3. 비중 파일 ② 주문 후: 사장이 적은 수량 × 가격만큼 새 종목 비중을 올리고 현금을 줄인다. **주문 금액이 주문가능액보다 크면 계산하지 않고** "현금보다 큰 주문 — 같이 팔 종목을 알려 주시면 계산" 한 줄.
  4. asof = 키움 일봉의 마지막 **완성된** 세션(마지막 행은 다음 날 바뀜, trading-tools-review 12-2절).
  5. 답: "R2 20거래일 나쁜 5% 평균(CVaR): 계좌 −a% → −b%" · "R5 SOXX −20%일 때 중앙값: −c% → −d%" 두 줄 + R5 제외 비중·대리 비중·현금으로 돌린 비중 + 머리 표시(보정 여부). 숫자는 그때 계산하며 여기 적지 않는다.
  6. 새 종목의 실제 이력이 60세션 미만이면 위험 지도가 그 비중을 현금으로 센다(risk_map.py 32·120~124·138~142행, 결과 current_to_cash_share 305행). 주문 후 계산에서 현금으로 돌린 비중이 0보다 크면 "계산 못 함 — 새 종목 이력 부족"으로 답한다(덜 나쁘게 보이는 숫자를 내지 않음).
- 하지 않음: 수량·가격 제안, 주문 막기, 한도·관문·카드·코어 입력 변경, 새 예약·새 화면, 결과로 "사라/말라" 판정.
- 승인 방식: 표시·운영 방식 결정이라 사장실 회사PC 스레드의 선택 카드로 받는다(지침 4절 버튼 기본. CLAUDE.md에 직접 입력 요구 없음). 기억에는 규칙 문장을 쓰지 않는다.
- 기록: 이 문서 9절(선택 카드 응답 — 선택지 문구·누른 계정·KST 시각) + active-decisions.md 한 줄(2026-10-29 21:15 KST "4가지 상황 승인"도 색인에 없어 함께 한 줄) + 프로젝트 기억은 위치 안내 1줄.
- 무응답 기한: 2026-11-07 KST → NO_CHANGE(지금처럼 지금 비중으로 한 번만 계산).

### 5-2 P2 (보류) SEC XBRL 분기 숫자 표
보류 이유(1차 재검토에서 원문 확인):
1. **기존 결정과 충돌**: "Claude(Cowork·예약 점검)는 sec.gov를 bash·python·curl로 가져오지 않는다" · "수집 주체 = 사용자 PC의 Windows 작업 스케줄러가 돌리는 저장소 스크립트" · "Claude는 로컬 산출물 파일만 읽는다"(e-filing-feed-review-2026-10-05.md 49~51행, 사용자 채택 106행, 통합 점검 v3.11 변경 문서 86행). 클라우드 컨테이너에서 Claude가 스크립트로 부르는 안은 이 규칙을 푸는 일(제약 완화)이다. 이 규칙의 현행 효력은 **확인 필요** — 통합 점검 v3.12.10 사본에는 그 문장이 없고 로컬 산출물만 읽는 구조만 남아 있다(scheduled-prompts/pending-iv-c1c2/integrated-check-prompt-v3.12.10-2026-10-22.txt 69·72행). 확인 전에는 fail-closed로 충돌로 본다.
2. **쓸 자리가 좁음**: 지금 원장 트리거 후보는 XBRL 매출·EPS가 아니다 — MU는 DRAM bit 공급 증가율 문장(external-claims-ledger.md 153~157행), NBIS는 MW당 ACV·계약 기간(55~59행). NBIS는 6-K 제출 회사라(e-filing-feed-review 109행) 분기 XBRL 값이 없을 수 있다(확인 필요).
3. **시험 기준을 다시 세워야 함**: 연속 4분기에는 늘 회계 4분기가 들어가는데, 4분기는 "연간 − 3개 분기"로 만든 값이고 EPS는 근사다(facts.py 26~28행). 10-Q 분기만 대조하거나 8-K 보도자료(EX-99.1)와 대조해야 하고, companyfacts가 최신 10-Q보다 늦으면 "시험 무효·재시도"로 정해야 한다(SKILL.md 64~66행).
- 재개 조건: 카드 작성에서 "공식 분기 숫자 대조"가 실제로 필요한 종목이 생기면, 클라우드 스크립트가 아니라 **이미 있는 PC SEC 수집기(sec_official_event_intake.py)에 companyfacts 읽기를 더하는 일반 변경(개발 큐)**으로 제안한다. 그때 지킬 것:
  - 숫자 표는 **별도 출력 파일**에 쓰고 통합 점검은 그 파일을 읽지 않는다. 통합 점검은 이 수집기의 기존 출력(scheduled-dashboard.json·normalized-events.json)을 읽고(v3.12.10 사본 69·72행), 통합 점검 연구 기록은 코어의 유일한 LLM 입력이다(CLAUDE.md 48행). 통합 점검이 읽게 하려면 B종류 예약 변경(active-decisions.md A절 예약 작업 변경 승인 문구)과 K3 경로를 따로 밟는다.
  - 3번 시험 기준(10-Q 분기만 또는 8-K EX-99.1 대조, 늦은 자료는 시험 무효·재시도)을 계산 전에 고정한다.
  - 수집기가 지금도 도는지(확인 필요), User-Agent는 PC의 기존 SEC_USER_AGENT(e-filing-feed-review 18행), CIK는 고정 목록, 코드를 빌리면 MIT 고지.

## 6. 이 결론을 바꿀 조건
- 묶음 설치: 주문 스킬을 뺀 연구 전용 판이 나오고, 키움 가격을 쓰며, 일봉 기준 판이 생기면 다시 본다.
- P1: 위험 지도 보정 시험이 다음 계산에서도 "꼬리를 덜 잡음"이면 전·후 숫자 모두 덜 나쁘게 나온다는 경고를 첫 줄에 붙인다. 주문 후 비중 계산에 쓸 새 종목 일봉을 키움이 주지 않으면 그 주문은 "계산 못 함 — 확인 필요".
- P2: 5-2절 재개 조건.
- 공통: 사장이 주문 2단계(redesign-t5)를 승인해도 broker는 들이지 않는다(키움 미지원, 주문 금지 규칙은 별도).
- 들이지 않은 생각 중 하나: trader-risk의 "하루 재량 주문 횟수·하루 손실" 경고는 새 한도 성격이라 이 검토에서 제안하지 않는다(D3 동결·한도는 K3). 사장이 원하면 따로 검토한다.

## 7. 원문·자료 시점
- Notion: whimsical-weeder-523.notion.site 공개 페이지, 2026-10-31 13:1x KST 내려받음(페이지 끝 "2026-10-30에 원문을 다시 열어 확인", 사본 159행 부근).
- GitHub: `git clone --depth 1` 2026-10-31 13:1x KST → 커밋 3d0f4ef6986f(2026-10-20 09:17 -0500). sha256: README.md ec48389f… · LICENSE 857c8d52… · trader-analyst/facts.py 6cd7e245… · trader-timemachine/timemachine.py 5e73d566… · trader-broker/SKILL.md d1a34683…
- 저장소: codex/master-recovery-expansion 2269a50(2026-10-30 23:30 KST). active-decisions.md 행 번호는 **작업 트리 기준**(미커밋 +2행) — HEAD에서는 1~2행 앞.
- 못 한 것: 외부 코드 실행·테스트(실행하지 않음), .py 전체 정독(SKILL.md 11개는 정독, .py는 요청 주소·쓰기 위치·필요한 함수만), Notion 이미지 3장, PC SEC 수집기가 지금도 도는지.

## 8. 내장 재검토 기록
- 1회차(독립 subagent, 비 Haiku, 2026-10-31 13시대 KST): 발견 10건. 본 세션이 원문을 다시 열어 확인 — e-filing-feed-review 44~56·104~110행, 통합 점검 v3.11 변경 문서 84~88행, 원장 55~59·153~157행, active-decisions 140행·git diff, facts.py 14~30·131~135행, analyst SKILL.md 60~66행, risk_map.py 224~242·276~284행, 조사 문서 2곳. 10건 반영(e-filing 3절 규칙의 현행 효력은 2회차에서 "확인 필요"로 남김).
  - **결론 바뀜 1건: P2 제안 → 보류**(SEC 수집 주체 규칙 충돌·쓸 자리 좁음·시험 기준 결함).
  - P1 보강: 새 종목 일봉 조회, 두 비중 파일의 종목 집합 맞추기, 완성 세션 asof, R2는 CVaR로 명시, 현금 초과 주문 처리, 예시 숫자 삭제, 무응답 기한, 기억은 위치 안내만.
  - 표기 정정: budget 행 "재량 주문에는", scanner 개장 전 스캔 추가, broker 세 관문, 그림의 분류 정리, 인용 행(작업 트리 기준·140행·rule1028 파일·Notion 위치·제안 규칙 원문 = 스레드), analyst "코드는 없음"으로 좁힘.
- 2회차(같은 subagent, 바뀐 부분만, 2026-10-31 13시대 KST): 발견 6묶음. 본 세션이 원문을 다시 열어 확인 — risk_map.py 32·120~124·138~142·303~306행, rule1028-a3-results 17·30행, scan-power-nonai-roots.md 3행, v3.12.10 사본 69·72행, CLAUDE.md 56행, trading-tools-review 212행. 모두 반영: P2 재개 조건(별도 출력 파일·통합 점검이 읽지 않음·B종류+K3·시험 기준 사전 고정), P1(현금으로 돌린 비중 표시·이력 부족이면 계산 못 함, 인증 오류 전체, 사장 본인 OK = 조회 요청, ust21070·금액 버림, 매도 전 점검은 묻지 않음, 카드 승인·기록 형식, 10/29 결정 색인 한 줄), 표기(에이전트 보고서, SOXL만, 인용문 원문대로, 관문 출처). **결론 바뀜 0** → 3회차 없음(CLAUDE.md 118행).

검토 완결: 원문 확인 — 결론에 쓴 주장은 모두 이번 세션에 연 원문(파일·행, 커밋, 스레드 메시지)으로 확인, 확인 필요 3건(PC SEC 수집기가 지금도 도는지 · e-filing 3절 규칙의 현행 효력 · NBIS 분기 XBRL 유무 — 모두 보류한 P2에만 걸림) · 내장 재검토 2회(반영 16건) · 미해결 0 · 자료 시점 2026-10-31 13:55 KST(저장소 2269a50 + 작업 트리, 외부 3d0f4ef) · 바뀔 조건 6절

## 9. 사장 결정 기록
- 2026-10-31 17:25:50 KST, 사장실 회사PC 스레드 결정 카드 "매수 주문 전 점검 때 위험 지도를 주문 전·후로 두 번 계산할까요?" → **"P1 적용"** 선택(선택지 문구: "매수 점검 때 재계산에 OK 하시면, 지금 비중과 주문 후 비중으로 두 번 계산해 손실 차이를 두 줄로 보여 드립니다." · 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 플랫폼이 본인 앱의 탭으로 확인).
- 적용 범위: 5-1절 그대로. 다음에 사장이 `주문 전 점검: <티커> 매수 …`을 보내고 "위험 지도 다시 계산할까요?"에 사장실 스레드에서 본인이 OK 할 때부터. 매도 전 점검·체결 보고 뒤는 지금처럼 1회. 코드·한도·관문·카드·코어 입력·예약 작업 변경 0.
- 같은 스레드 17:26 KST 사장 "위험지도 다시 계산"(승인된 상황 ③, SOXX 10/30 하루 −8.24%) → 주문이 없어 전·후 비교는 해당 없음, 지금 비중으로 1회 계산. 결과는 trading-tools-review-2026-10-29.md 12-4절.
- 색인: active-decisions.md A절 "p1-1031: P1 적용" 행.
