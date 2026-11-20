---
id: backlog-review-2026-11-19
type: review-record
status: current
as_of: 2026-11-19 16:50 KST
summary: "밀린 검토 3건(토큰 줄이기 · 마스터플랜 검수 반영 · 뉴스 요약 첫 실행 실패)을 원문으로 다시 확인한 기록. 1·2는 이미 결정·반영이 끝나 사장이 지금 정할 것이 없다. 3은 원인 후보를 둘로 좁혔고 오늘 19:30 자동 재시도로 가린다."
consumers: "사장실 코디네이터(프로젝트 대화 보고) · 관제판 api-pilots-1106 · token-usage-1118 · masterplan-1118"
authority: "읽기·docs/claude 문서 쓰기만. order_authority=false · quantity_authority=none. 예약·정책·상태·코드 변경 없음"
---

# 밀린 검토 3건 정리 (2026-11-19)

시각은 KST.

## 0. 결론

| 건 | 지금 상태 | 사장이 지금 정할 것 |
|---|---|---|
| 1. 토큰 줄이기·API 크레딧 | 결정은 11/18에 끝남. 남은 것은 11/25 다시 재기뿐 | 없음 |
| 2. 마스터플랜 검수 | 11/18 15:46 반영·채택 끝. 다만 '켜'(16:05) 뒤 '지금 위치'가 낡아 roadmap.md 1절만 고침 | 없음 |
| 3. 뉴스 자동 요약 실패 | 30종목 모두 기사 가져오기 실패. 원인 후보 2개, 오늘 19:30 재시도로 가림 | 없음(재시도도 실패하면 고치는 길을 카드로) |

## 1. 토큰 사용량 줄이기·API 크레딧 (token-usage-1118)

원문: token-usage-api-credit-review-2026-11-18.md 9·12절 · model-usage-plan-2026-11-18.md 17행 · active-decisions.md 72행 · 시나리오 스레드 세션 기록(2026-11-19 16:4x 조회).

- 끝난 것: B(재검토를 API로) = 닫아 둠(11/18 09:25 카드) · T1b 알림 스레드 Sonnet·low, 수집 스레드 Sonnet·medium(11/18 09:30·09:40 사장 입력) · T1a 시나리오 스레드 추론 노력 high(세션 기록 effort_level high 확인 — 계획 문서 17행의 '1개 남음'은 이제 끝) · T3은 하지 않음 · 지침 7절 v2.4~v2.6(G2) 적용 · `/advisor`는 회사PC만 됨.
- 남은 것(모두 날짜·조건이 이미 있음, 새 결정 없음):
  - 11/25 다시 재기(관제판 token-usage-1118) → 그 값으로 T2(지침 6절 줄이기)·T4(결과 모음 미리 모으기) 진행/닫음을 그때 카드로.
  - T5(결정 색인 줄이기)는 시범 1 채점(10거래일, 11/24 기록) 뒤.
  - G3 CLAUDE.md 정리 안건(Session hygiene 문구 맞춤)은 급하지 않음, Opus·xhigh 절차.
- 새로 본 것 1건: 시나리오 스레드 맥락 330,212 토큰 — 자동 요약 한도 384,000까지 약 5.4만 남음(11/10 통합 점검이 같은 한도에서 끊긴 적 있음, ic-context-1110). 11/25 재기 때 함께 본다. 지금 손댈 일은 아님(확인 필요: 요약 뒤 예약 실행이 정상인지).
- 권고: NO_CHANGE. 11/25까지 기다린다.

## 2. 마스터플랜 독립 검수 (masterplan-1118)

원문: masterplan-2026-11-18.md 4행(status)·14·15절 · masterplan-review-2026-11-18.md · git d161553 · auto_core.json 12행 · git e095f2e(2026-11-18 16:05:58 KST).

- '반영 전'은 낡은 표시다. 검수 지적(틀림 5·약함 5·순서 4·빠짐 12) 가운데 T1~T11·S1~S4·M1~M9가 3판에 반영됐고, 사장이 15:46:45 카드 '채택, 로드맵은 링크만'으로 채택했다(14·15절). 남긴 것 M10(11/22 예약 — 지워짐 확인)·M11·M12(관제판 문구 — 채택 뒤 고침)·조직 짝(12절)뿐.
- 아직 사장 카드로 남은 것(날짜가 정해져 있어 지금 묻지 않음): G3 오류 셈 규칙 · G7 개발 자리 순번 · G8 D3 범위 해석 · G10 기간 성적 비교 기준 · G11 목표 숫자 → 첫 분기 갱신 2027-02-18. 수익 목표 줄(5-1절)은 내장 재검토 1회만 거쳤고 독립 검수는 그 분기 갱신 때 함께 보면 된다(권고).
- **새로 찾은 어긋남:** 사장 '켜'(2026-11-18 16:05 KST, decision_mode apply)가 채택(15:46) 뒤에 들어왔는데 roadmap.md 1절과 마스터플랜 0절 그림·2절이 여전히 '1기 · 비교 중 · 주문표는 입력 대상 아님'이었다. roadmap.md 3행 규칙("시기가 바뀌면 그 세션이 고친다")이 지켜지지 않음.
  - 고침: roadmap.md 1절 '지금' 줄을 2기로(이 스레드, 2026-11-19).
  - 고치지 않음: 마스터플랜 본문 — 같은 날 다른 스레드가 이 파일을 편집 중(커밋 안 된 1줄, 2027-10-09 달력 행). 겹쳐 쓰지 않으려고 손대지 않았다. 0절 그림 29행 · 2절 '실행' 행 · 5절 1기 '가' 줄의 갱신은 그 스레드 또는 다음 회사PC 스레드 몫(확인 필요).

## 3. 뉴스 자동 요약 첫 실행 실패 (api-pilots-1106 시범 2 llm-news)

원문: workspace/outputs/llm/runner/2026-11-18.json · news/2026-11-18/failed.md · usage.jsonl · llm_pilot_news.py 297~312·444~454행 · llm-news2-builder-prompt.md 60~66행 · 예약 작업 InvestmentV2-LLMPilots 동작(읽기 조회) · 회사PC Python 설치 폴더 목록(읽기).

- 일어난 일: 11/18 19:30:02~19:30:12 KST news-submit이 `FETCH_FAILED symbols_failed=30`(종료 11). 30종목 모두 기사 가져오기 실패라 API는 부르지 않음(비용 0, usage.jsonl에 news 줄 없음). 22:00·23:00 수거는 낼 묶음이 없어 `NO_BATCH`(정상). 11/19 19:30에 실행기가 자동으로 다시 시도한다(켜기 목록에 news-submit 있음).
- 확인해서 **지운 원인**:
  - 패키지 없음 아님: 예약은 run_llm_pilots.ps1 → 저장소에 .venv가 없어 PATH의 python.exe = Python313 사용. 그 site-packages에 yfinance 1.5.2 · curl_cffi 0.16.0 · anthropic 2.3.0이 있다(11/11 iccheck의 ModuleNotFoundError와는 다른 일로 보임).
  - 종목 이름 아님: 사전 등록 universe 30개는 모두 미국 티커(MRVL … ON).
  - 키·예산·사전 등록 아님: 그 단계에서 막혔으면 상태가 NO_KEY·BUDGET_STOP·PREREG_MISMATCH로 나왔을 것.
- **남은 원인 후보 2개(확인 필요):**
  - ① Yahoo 쪽 차단·속도 제한(yfinance가 예외를 냄). 30종목에 10초 = 종목당 약 0.3초로, 네트워크 응답이 빨리 거절된 모양과 맞는다.
  - ② yfinance 1.5.2의 `.news`가 목록이 아닌 꼴을 돌려줌(코드 309행: 목록이 아니면 실패로 셈). 지시문 66행이 '실제 꼴은 첫 실행에서 확인 필요'로 남긴 바로 그 점.
- 왜 못 가렸나(설계 빈칸): fetch_items 307행이 예외를 `except Exception: return None`으로 삼키고 failed.md에 예외 종류를 남기지 않는다(iccheck는 'ModuleNotFoundError'를 적음). 이 스레드는 규칙상 파이썬을 실행하지 않으므로 직접 시험하지 않았다.
- 다음(기본 처분): 오늘 19:30 자동 재시도 결과를 본다.
  - 성공하면 → 일시적 Yahoo 문제로 닫음.
  - 또 FETCH_FAILED면 → 작은 일반 변경 1건을 카드로 올린다: failed.md·runner 줄에 첫 실패 종목의 예외 종류/반환 꼴을 적게 하기(진단만, 판정·점수 불변 → 사전 등록 불변). 원인이 ②면 정규화 고침, ①이면 출처 대안 검토.
  - 빠르게 가리고 싶을 때(선택, 사장 터미널 한 줄): `python -c "import yfinance as y; n=y.Ticker('MU').news; print(type(n).__name__, len(n) if hasattr(n,'__len__') else n)"` — 예외가 나면 ①, list가 아니면 ②.
- **재시도 결과(2026-11-19 19:41 KST 확인):** 19:30 news-submit 또 `FETCH_FAILED symbols_failed=30`, failed.md 같은 문구, usage.jsonl에 news 줄 없음(비용 0). 일시적 문제가 아니므로 기본 처분대로 진단 변경(예외 종류·반환 꼴 기록)을 사장 결정 카드로 올림.
- 영향: 그림자 점수 시범이라 코어·주문표에는 영향 없음. 182일 그림자 기간에서 하루가 빠짐(사전 등록상 결측일로 셈 — 확인 필요).

## 4. 연결표

| ① 산출 | ② 만든 곳 | ③ 읽는 곳 | ④ 바뀌는 행동 | ⑤ 끊기면 | ⑥ 상태 |
|---|---|---|---|---|---|
| 이 기록 | 사장실 회사PC 스레드 '밀린 검토 3건 결론 내기' 2026-11-19 | 코디네이터 보고 · 관제판 token-usage-1118(11/25) · api-pilots-1106 | 뉴스: 재시도 실패 시 진단 변경 카드 | 이 스레드가 19:40 결과 확인 | 연결 |
| roadmap.md 1절 고침 | 같음 | 모든 스레드 시작 입구(00-home → roadmap) | '지금 2기' 인식 | — | 연결 |
| 마스터플랜 0·2절 낡음 | — | 분기 갱신·편집 중 스레드 | 문구 갱신 | 확인 필요 | 끊김(알림만) |

## 5. 뒤이은 기록 (2026-11-19 21시대 KST)

- 사장 결정 카드 '오류 기록 고치기(개발 큐)'(cmsg_0137MRzn9nuDvvQmVxm6WeX9G2jN3URHaiDhhPkAaJbUV6, 2026-11-19 19:41:54 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH) → 지시문 llm-newsdiag-builder-prompt.md 작성, 개발 큐 _dev-queue/llm-newsdiag.txt 등록.
- Fable 조언 1번(medium): 지적 8건 중 7건 반영(연결표 ③④⑤ 파일:줄 · 기존 산출 행을 표 밖 한 줄로 · 재시도 성공 때 낡은 fetch-errors.json 지움 · 메시지 정리 순서·type 칸 · 쓰기 OSError 삼킴 · 줄 번호·금지어·LF·Judge 근거). 1건(인용 문서 커밋 여부)은 _pending/llm-newsdiag-2026-11-19.txt로 처리(개발 큐가 실행 전 commit-docs를 돌림 — tools/dev_pipeline/README.md 9행).
- 참고: stdout 마지막 줄은 기존 시험(516행)이 고정해 그대로 둔다. 원인은 실행기 하루 기록이 아니라 news/<날짜>/fetch-errors.json·failed.md에 남는다.
- 병합 9d93ff7(2026-11-20 사장 실행, workspace/outputs/dev-runs/LATEST.json `DEV-MERGE llm-newsdiag MERGED`).

## 6. 원인 확인 (2026-11-20 19:41 KST)

- 19:30 news-submit 또 FETCH_FAILED. fetch-errors.json: 30/30 모두 같은 오류 — `SSLError: Failed to perform, curl: (77) error adding trust anchors from locations: CAfile: C:\Users\???\AppData\Roaming\Python\Python315\site-packages\certifi\cacert.pem CApath: none`.
- 뜻: Yahoo 차단(①)도 반환 꼴(②)도 아니다. yfinance가 쓰는 curl_cffi가 인증서 묶음 파일을 열지 못해 Yahoo에 접속도 못 했다. 파일은 있다(Test-Path True). 경로에 한글 사용자 이름이 있어(로그에 ???로 찍힘) curl이 비ASCII 경로를 못 여는 것이 가장 가능성 큰 원인이다(확인 필요 — 이 PC에서 직접 시험하지 않음).
- 실행 Python은 C:\Python315(PATH 첫 python, 사용자 site-packages에 yfinance 1.8.0·curl_cffi 0.17.0·certifi 2026.10.23). 3절에 적은 'Python313'은 Desktop Commander 셸의 PATH 기준이라 틀렸다 — 예약 작업은 python315-tzdata 기록대로 3.15를 쓴다.
- 환경 변수 SSL_CERT_FILE·CURL_CA_BUNDLE·REQUESTS_CA_BUNDLE·PYTHONPATH·PYTHONUSERBASE 없음(사용자·시스템).
- 고칠 자리(설치본 읽기): curl_cffi requests/session.py 268·315~319행(Session verify, 환경 변수 없으면 그대로), utils.py 915~922행(verify가 문자열이면 CAINFO로 씀) · yfinance base.py 82행 Ticker(session=) · _http.py 61행 기본 Session(impersonate="chrome") · data.py 136~150행 curl_cffi Session 허용.
- 사장 결정 카드 '스크립트에서 고침(개발 큐)'(cmsg_0137MRzn9nuDvvQmVxm6WeX9WPJfBVNfJ7ktcnpBrnjqPf, 2026-11-20 19:56:21 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH) → 지시문 llm-newsca-builder-prompt.md, 개발 큐 llm-newsca.
