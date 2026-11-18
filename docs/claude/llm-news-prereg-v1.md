# 시범 2 사전 등록 v1 (초안) — 익명 뉴스 점수의 그림자 기록 (llm-news-prereg-v1)

- 상태: **초안**. 작업 3(`llm-news`) 등록 때 이 파일과 `llm-news-prereg-v1.json`을 회사PC `docs/claude/`에 그대로 올리고, 그 뒤로는 고치지 않는다. 고치려면 v2와 새 시작일이 필요하다.
- 근거: 사장 결정 2026-11-06 14:26:18 KST "세개 다 시범으로 도입"(시범 2 = 공시·뉴스 요약 + 그림자 점수).
- 권한: 그림자 기록이다. 점수는 화면에 보이지 않고 어떤 판단·알림·주문과도 연결하지 않는다. 채점에서 합격해도 할 수 있는 일은 '카드 재검토 알림' 제안(별도 승인)뿐이다. 매매 규칙은 §20 사전 등록 시험 경로다.
- 왜 앞으로만 하나: LLM으로 과거 뉴스를 채점하면 모델이 결과를 이미 알고 있을 수 있어 무효다(Glasserman·Lin — api-credits-max-1106 메모). 그래서 이름을 지우고 앞으로 나오는 뉴스만 기록한다.

## 고정값 (JSON이 원본)

| 항목 | 값 |
|---|---|
| JSON 정규 sha256 | `a8b6f930d7a06ff73f146bfee0236e8f4f6169fbeed7663eacaa4ab43f3262e8`(2026-11-06 재검토 2회차 반영판) — `json.dumps(값, ensure_ascii=False, sort_keys=True, separators=(",",":"))`의 UTF-8 sha256(validation_common.canonical_hash와 같은 방식, 35~37행) |
| 점수 지시문 sha256 | `448d2519a4726f600f83e05c750107aaf290756a9c66a6c23d98d59979351db5`(990 B, JSON의 label_system_prompt) |
| 대상 30종목 | MRVL NBIS MU BE DELL PWR LITE NVDA AVGO AMD TSM ASML QCOM TXN INTC AMAT LRCX KLAC ADI ARM SMCI ANET COHR CIEN VRT PLTR SNDK WDC MPWR ON |
| 모델 | `claude-haiku-5-5`, Message Batches, effort low, 구조화 출력 `{label: good/bad/unknown, reason}`, 서버 대체 모델 없음 |
| 이름 지우기 | 대상 종목의 별칭·기호 → `[COMPANY]`, 다른 29종목 → `[OTHER]`, URL 삭제. 기호는 대문자 그대로, 기호 형식일 때만 바꾼다: 거래소 표기 NASDAQ·NYSE 뒤(표기의 대소문자·콜론 앞뒤 띄어쓰기·괄호 유무와 무관 — (NASDAQ: MU) · NASDAQ:MU · Nasdaq: MU), 괄호 안 기호 하나((MU)), $BE, BE.O, 3글자 이상 대문자 낱말. 대소문자를 구분하는 별칭은 닫힌 목록 `case_sensitive_aliases` 6개(Arm·Coherent·Dell·Intel·Micron·Quanta)뿐이고 나머지 별칭은 구분하지 않는다 — 'be'·'on'·'arm' 같은 낱말이 가려져 제목이 깨지지 않게 |
| 기사 | yfinance `Ticker.news`, 제출 때 처음 보고 발행 24시간 안인 것 |
| 시각 | 매일 19:30 KST 제출, 22:00·23:00 KST 수거(받은 시각 = 수거 스크립트가 받은 KST 시각. 여름 개장 22:30·겨울 23:30보다 30분 앞이라 실행기 10분 간격으로 늦어져도 개장 전). 대상 장 s(d) = 제출 뒤 처음 열리는 미국 정규장. **s(d) 개장 전에 받은 점수만 표본**(늦게 받은 것은 기록만 하고 빼며, 다음 장으로 미루지 않음) |
| 단위 | (종목, s(d)) — s(d)가 같은 KST 날들(토·일·월 → 같은 월요일 장)의 기사를 합친다. 점수 = 기사 label 평균(good +1 · bad −1 · unknown 0). 양수 = 좋음 무리, 음수 = 나쁨 무리, 0 = 제외 |
| 결과 | R = (s(d)+4 종가 / s(d) 시가) − SPY 같은 값 — 5세션 초과 수익 |
| 주 통계 | D = 평균(R | 좋음) − 평균(R | 나쁨). s(d)의 ISO 주 단위 블록 부트스트랩 10,000회, 시드 20261106 |
| 비교 기준 | D_base = 직전 5세션 초과 수익의 부호로 나눈 같은 D(추세 따라가기) |
| 합격 | D의 한쪽 95% 하한 > 0 **그리고** D > D_base |
| 최소 표본 | 좋음 60 · 나쁨 60 단위, 미국 장날의 70% 이상에서 개장 전 점수 받음. 못 채우면 판단 보류 |
| 채점 | 시작일(첫 제출, records.jsonl 첫 줄) + 182일에 1번 |
| 결과별 행동 | 합격 → 카드 재검토 알림 제안(별도 승인) · 불합격 → 질문 닫음(NO_CHANGE) · 보류 → 한 번 묻고 무응답이면 닫음 |
| 멈춤 | 응답 모델이 `claude-haiku-5-5`도 `claude-haiku-5-5-YYYYMMDD`(하이픈 + 숫자 8자리)도 아님 · 모델 404 · 사전 등록 sha 불일치 |
| 기록 | `workspace/outputs/llm/news/records.jsonl` 덧붙이기만, 줄마다 앞 줄 sha256 |

## 시험(작업 3 Builder가 만드는 것)
- 시험이 이 JSON 파일을 읽어 정규 sha256이 위 값과 같은지, 지시문 sha256이 위 값과 같은지 단언한다. Builder는 해시를 직접 계산하지 않는다(builder-allowlist 메모).
- 이름 지우기 시험: 'Nvidia invests in Nebius' 같은 문장에서 대상이 NBIS면 'Nvidia' → `[OTHER]`, 'Nebius' → `[COMPANY]`. 대상이 MU면 'Micron Technology (MU)'·'NASDAQ:MU'·'Nasdaq: MU' → 모두 `[COMPANY]`, 'micron-scale'은 그대로.
- 늦게 받은 결과는 표본 표시가 false인지, 기록 줄의 앞 줄 해시가 이어지는지 단언한다.

## 한계 (미리 적음)
- 6개월 표본에서 단위 수는 종목·뉴스량에 달려 있어 최소 표본을 못 채울 수 있다(확인 필요). 못 채우면 판단 보류다.
- yfinance 뉴스는 비공식 경로라 끊길 수 있다. 끊긴 날은 실패일로 세고, 70% 기준에 반영한다.
- Haiku 지시문은 약 250토큰이라 캐시 최소 길이(512토큰)에 못 미쳐 캐시되지 않는다. 비용 영향은 거의 없다.
