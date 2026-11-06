# API 크레딧 시범 4개 + B(문서 독립 검토) — 설계·개발 큐 제안 (api-pilots-1106)

**첫 줄(부딪힘):**
- active-decisions.md D3 동결(81행 '새 규칙·문서·예약을 늘리지 않는다')과 부딪힌다. 새 스크립트 6개, Windows 작업 1개, 문서 몇 개가 는다.
  - 예외 근거는 사장 결정 2026-11-06 14:26:18 KST "세개 다 시범으로 도입"과 14:41:48 KST 카드 선택 "A 추가 + B 규칙 개정 검토"다(1절).
- 예약 작업 승인 기록과 다르다(여기 공개). 근거는 지금 프로젝트 지침 4절 ① 원문 "사장이 이 스레드에 직접 친 `예약 작업 변경 승인: <이름>` 한 줄 또는 사장이 직접 누른 승인 버튼"이다. 다음 세 기록은 예약 작업 변경을 직접 입력만으로 받는다고 적었다. 지침이 위라 지침을 따르고, 직접 입력도 그대로 된다.
  - sc-1022 S4(active-decisions.md 31행, 2026-10-23 — 카드로 받지 않음)
  - btn-approval(같은 파일 78행 — "'전부'가 아님 … 예약 작업 변경은 지금처럼 직접 입력")
  - 승인 장소 표 #7(approval-venue-table-2026-10-25.md 26행)
- 그래서 Windows 작업 `InvestmentV2-LLMPilots`의 등록은 `예약 작업 변경 승인: InvestmentV2-LLMPilots`, 시범 켜기는 `예약 작업 변경 승인: InvestmentV2-LLMPilots/<시범>` 직접 입력 **또는 이 스레드 카드의 직접 누른 승인 버튼**으로 받는다. 시각은 코드에 고정한다(3절 실행 방법).
- 예약 작업 변경 절차(active-decisions.md 32행 — H1 시험, scheduled-prompts README sha)는 Claude 예약 작업(list_triggers)용이라 이 Windows 작업에는 쓰지 않는다(README 3행). 대신 등록 스크립트와 커밋된 켜기 파일의 git 기록으로 추적한다.
- CLAUDE.md 48행('자동 코어의 LLM 입력은 06:40 통합점검 연구 기록 하나뿐')과 12행('LLM은 가장자리에서 일하고, 실패해도 코어를 막지 않는다')은 지킨다.
  - 시범 출력은 `workspace/outputs/llm/`에만 쓴다.
  - 연구 기록·코어 입력·원장·카드·통합점검 규칙에는 쓰지 않는다.
- 새 매매 규칙은 없다. 시범 2의 점수는 6개월 동안 화면에 보이지 않는 그림자 기록이다. 행동과 연결하려면 §20 사전 등록 시험을 거쳐야 한다(헌법 constitution-v1.4.0.md 130~137행).

- 상태: **승인 — 시범 1부터 차례로**(사장 카드 2026-11-06 16:44:47 KST, 1절 표). 11/07 06:40 통합점검(선거 건) 첫 실행 확인 뒤 작업 1부터 올리고, 앞 작업이 병합되면 다음 작업을 올린다. Windows 작업 등록과 시범마다 켜기는 그때마다 따로 승인받는다(6절).
- 관련 파일:
  - 시범 1 Builder 지시문 `docs/claude/llm-iccheck-builder-prompt.md`
  - B 제안서 `docs/claude/llm-review-claudemd-proposal-2026-11-06.md`
  - 시범 2 사전 등록 초안 `llm-news-prereg-v1.md`·`.json`: 작업 3 등록 때 `docs/claude/`에 올린다(그 전까지 초안은 사장실 프로젝트 파일 `api-pilots-1106/`, 정규 sha a8b6f930…).

## 1. 결정 원문

| 시각(KST) | 무엇 | 원문 | 기록 위치 |
|---|---|---|---|
| 2026-11-06 14:26:18 | 사장 메시지(사장실 다른 스레드) | "세개 다 시범으로 도입" | 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9WN4WgxbUVKevZGmkb4k24L |
| 2026-11-06 14:41:48 | 사장 결정 카드 선택 | "A 추가 + B 규칙 개정 검토" | 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9W8YcsLciv5wVPk5mhWRuUT · 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH |
| 2026-11-06 16:44:47 | 사장 결정 카드 선택(이 설계서 등록) | "시범 1부터 차례로" | 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9E3aPheNEEsLywwbJ1nm476 · 선택지 A · 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH |

- '세개' = 검토서(https://claude.ai/artifact/VykmvMwKY92KnL3j9BRPxx)의 시범 3개다: ① 기록 대조 검토자 ② 공시·뉴스 요약 + 그림자 점수 ③ 무거운 문서 일 옮기기.
- A = 출처 확인 자동화(시범 4). B = 문서 독립 검토를 API(Opus)로 돌리기 위한 CLAUDE.md 개정 검토다. 검토 결론은 **NO_CHANGE(닫음)**이다: 같은 모델이라 맹점이 그대로이고, API 경로는 저장소 밖 원천을 못 열며, 비교용 새 코드는 '검토' 승인 범위를 넘는다. 다시 열 조건(사용 한도 부담 기록 2회 또는 사장 요청)과 그때의 시범 6 사양은 B 제안서 1·3절.
- 키: 워크스페이스 키 'investv2-pilot'(만료 2027-06-30)이 사용자 환경 변수 `INVESTV2_ANTHROPIC_API_KEY`에 들어갔다(14:36 KST 보관, 다른 스레드 전달). 이 세션은 값을 읽지 않았다.

## 2. 결론

1. **개발 큐 작업 5개를 차례로 올린다**(앞 작업이 병합된 뒤 다음 작업. 동시에 돌리면 두 번째 병합이 STOP_BASE_MOVED로 멈춘다 — dev-queue 기록).
   - `llm-iccheck`(공통 모듈 + 시범 1)
   - `llm-runner`(실행기)
   - `llm-news`(시범 2)
   - `llm-pdfcmp`(시범 3)
   - `llm-srccheck`(시범 4)
   - B는 NO_CHANGE라 개발 큐 작업이 없다(시범 6은 다시 열 때만 별도 승인).
2. **모두 표시 전용 그림자다.** 시범마다 미리 정한 합격 기준(4절)이 있고, 넘으면 '표시 연결'을 따로 제안한다(별도 승인). 미달이면 끄고 질문을 닫는다.
3. **사장님 손**(6절):
   - 시범 1 첫 실행 PowerShell 1줄(키 확인 겸)
   - 실행기 등록 1줄(1번)
   - 등록 승인 1번(카드 버튼 또는 직접 입력 `예약 작업 변경 승인: InvestmentV2-LLMPilots`)
   - 시범마다 켜기 = 승인 1번(카드 버튼 또는 직접 입력 `예약 작업 변경 승인: InvestmentV2-LLMPilots/<시범>`)
   - 병합은 Cowork가 한다(CLAUDE.md 63~64행).
4. **비용**(4절 추정, 확인 필요): 월 약 $8~10이다. 시범별 월 상한(합 $26)을 스크립트가 지키고, 넘으면 그달은 멈춘다. B를 다시 열어 비교하는 달은 +$5~15다.
5. **시범 4는 e-filing 결정(2026-10-05)과 맞는다. 조건부다**(5절).
6. **설계 요구(코디네이터 전달)를 반영했다.** 다르게 한 곳은 하나, 캐싱이다(3절 6). 실효가 있는 곳은 도구를 반복해 같은 앞부분을 몇 분 안에 여러 번 보내는 B(시범 6, 지금은 닫음)뿐이다. 시범 1은 하루 1회라 표시를 붙이면 쓰기 할증(1.25배)만 생기고, 시범 2~4는 공통 앞부분이 최소 길이(512토큰)에 못 미칠 가능성이 크며 Batch 안 캐시 적중은 보장되지 않는다. 그래서 순서는 캐시용으로 맞추되 표시는 512토큰을 넘는 Batch 앞부분에만 붙인다.

## 3. 공통 설계 (`llm_pilot_common.py`, 작업 1이 만든다)

1. **키:**
   - 환경 변수 `INVESTV2_ANTHROPIC_API_KEY`만 읽는다. 없으면 NO_KEY로 끝나고 failed.md에 "검토 못 함: 키 없음" 1줄을 쓴다.
   - 키 값은 출력·로그·예외 문장 어디에도 쓰지 않는다. 오류는 예외 종류와 HTTP 상태만 적는다.
   - 클라이언트를 만들기 전에 이 프로세스 안의 `ANTHROPIC_API_KEY`·`ANTHROPIC_AUTH_TOKEN`·`ANTHROPIC_BASE_URL`·`ANTHROPIC_CUSTOM_HEADERS`·`ANTHROPIC_PROFILE`을 지우고 `base_url="https://api.anthropic.com"`을 명시한다. 다른 키·주소·헤더가 섞이지 않게 하려는 것이다(SDK 2.3.0 `_client.py`가 이 변수들을 읽음).
   - Windows 작업으로 돌 때는 실행기 래퍼 `run_llm_pilots.ps1`이 `[Environment]::GetEnvironmentVariable('INVESTV2_ANTHROPIC_API_KEY','User')`를 같은 이름의 프로세스 변수로만 넘긴다(값 출력 금지). 작업 스케줄러가 로그오프 전까지 새 사용자 변수를 못 읽을 수 있어서다.
     - 이것은 새 방식이다. SEC 래퍼(run_sec_scheduled_shadow.ps1 219행)는 사용자 변수가 있는지만 기록하고, 프로세스 변수가 비면 넘기지 않고 SEC_USER_AGENT_REQUIRED로 멈춘다(248~251행). 등록 뒤 첫 실행에서 확인한다(7절 4).
   - Claude 세션과 Builder는 값을 읽거나 출력하지 않는다. 시험은 가짜 키와 가짜 클라이언트만 쓰고, 가짜 키 문자열이 출력 어디에도 없음을 단언한다.
2. **SDK:**
   - 공식 `anthropic` Python SDK를 쓴다. 새 파일 `manage-us-stock-strategy/requirements-llm.txt`에 `anthropic==2.3.0`(PyPI 2026-10-24 KST 판, Python ≥ 3.10, 정식 `client.files` 있음 — 휠 `_client.py`·`resources/files.py` 확인)을 적는다.
   - import는 함수 안에서 늦게 한다. 그래서 시험은 SDK 없이 돈다.
   - `max_retries=1`, timeout 120초.
   - 기존 `run_llm_decision_stability.py`는 다른 공급자(OpenAI 키) 하네스라 고치지 않는다. '보유·현금·원가는 싣지 않는다'는 원칙만 따른다(같은 파일 1~8행).
3. **모델 고정:**
   - 시범 1·4는 `claude-sonnet-5-5`, 시범 2·3은 `claude-haiku-5-5`다(B를 다시 열면 `claude-opus-5-5`).
   - 응답의 model이 다르면 결과를 버린다.
   - 서버 쪽 대체 모델(fallbacks)과 advisor 도구는 쓰지 않는다. 모델을 고정하고 베타 없는 경로만 쓰기 위해서다. 대체 모델은 Batch에서 거부되기도 한다(claude-api model-migration).
4. **토큰:**
   - 호출 전에 `messages.count_tokens`로 입력을 센다. 시범별 상한을 넘으면 호출하지 않고 TOO_LARGE로 끝낸다.
   - 호출 뒤에는 응답 `usage`(input·output·cache_creation·cache_read)를 `workspace/outputs/llm/usage.jsonl`에 한 줄씩 덧붙이고, 가격표로 추정 비용을 적는다. Admin API는 쓰지 않는다.
5. **예산:** 시범별 월 상한은 시범 1 $10 · 2 $5 · 3 $5 · 4 $6이다(합 $26, B를 다시 열면 +$20). Max 월 크레딧 $100 안이다. usage.jsonl의 그달 합이 상한을 넘으면 BUDGET_STOP으로 호출하지 않는다.
6. **캐싱:**
   - 모든 요청에서 고정 지시문(시범 1은 결정 색인까지)을 앞에, 바뀌는 자료를 뒤에 둔다.
   - `cache_control`은 같은 앞부분을 5분 안에 여러 번 보내는 곳에만 붙인다: 공통 앞부분이 512토큰 이상인 Batch 묶음(B를 다시 열면 도구 반복이라 자동 캐싱). 512토큰 미만이면 붙이지 않고 '최소 길이 미달'로 기록한다(시범 2 점수 지시문은 약 250토큰 — 사전 등록 md 38행).
     - 5분 캐시의 손익분기는 2회다(쓰기 1.25배 + 읽기 0.1배 대 2배 — claude-api prompt-caching).
     - 최소 길이는 Sonnet 5.5·Haiku 5.5 모두 512토큰이다. 더 짧으면 표시가 있어도 캐시되지 않는다.
   - 시범 1은 하루 1회 호출이라 붙이지 않는다.
   - usage의 `cache_read_input_tokens`로 실제 적중을 확인한다.
7. **출력 형식:**
   - 시범 1·2는 구조화 출력(`output_config.format` json_schema, additionalProperties false)을 쓴다.
   - 시범 3·4는 인용(citations)이 구조화 출력과 함께 쓰이지 않아(400) 엄격한 줄 형식 + 인용 블록으로 한다.
   - `stop_reason`이 refusal·max_tokens면 실패다. thinking 블록이 앞에 올 수 있어 text 블록만 골라 읽는다.
8. **금액·수량 지우기(코디네이터 ④):**
   - API로 보내는 자료에서 계좌 금액·수량을 지운다. 비율과 E만 남긴다.
   - 연구 기록의 account는 허용 키만 남긴다(vsHwmPct·firstCushionPct·approachPct·maxPct·n·reconcile·exposure·holdings[code·weight·mult]).
   - 키 이름 목록(qty·quantity·shares·value·marketvalue·cash·amount·total·totalassets·kiwoomtotal·kiwoomdiff·hwm·price·avgcost·cost·pnl·lines, 또는 usd로 끝남)을 재귀로 지운다(Builder 지시문 3-(나)와 같은 목록).
   - reconcile 문자열은 첫 `:` 앞 낱말(일치·불일치)만 남긴다. 그 뒤에 보유 수량이 '주' 없이 들어 있다("일치: 키움 AAA N·BBB N = 상태 파일").
   - 문자열 속 `$숫자`·`숫자 달러`·`숫자주`, '종목 코드 + 공백 + 정수'("AAA N"), '옛 값·보유·수량·잔고 + 정수'는 `[금액]`·`[수량]`으로 가린다(Builder 지시문 3-(다) 다섯 규칙). 시각·날짜·비율·분할(06:40·10/28·3.0%·3:1)은 가리지 않는다. **결정 색인(active-decisions.md) 글에도 적용한다** — 그 파일에 보유·주문 수량과 지정가가 있다(99·167·233행, 99행은 단위 없는 "옛 값 N" 꼴).
   - 시험은 실제 꼴(reconcile·잔고 줄의 "AAA N", 결정 색인의 "옛 값 N")을 가짜 숫자로 넣고, 보낸 글에 그 숫자가 없음을 단언한다.
9. **인용 확인:** 모델이 근거로 든 문장은 스크립트가 원문의 그 행에서 글자 그대로 찾는다(공백 정규화, 6자 이상). 못 찾으면 그 발견을 버리고 버린 수를 기록한다.
10. **실패:** 모든 실패는 그날 폴더의 failed.md 1줄("검토 못 함: 이유")로 끝나고 다른 작업을 막지 않는다. 쓰기는 원자적이다(임시 파일 → 이름 바꾸기).

**실행 방법:**
- 첫 실행(키 확인)은 사장님이 **새 PowerShell 창에서** 1줄을 친다(작업 1 병합 뒤, 정확한 줄은 그때 드림). 새 창이어야 새 환경 변수가 읽힌다. 줄에 `--day <연구 기록이 있는 가장 최근 날짜>`를 넣는다(기록은 KST 화~토에만 있고, 기록 없음 검사가 키 검사보다 앞). 성공 기준은 API 호출 성공 + review.json 생성이다.
- 그 뒤 매일 실행은 실행기(작업 2)가 맡는다.
  - Windows 작업 `InvestmentV2-LLMPilots`가 10분마다 돈다. 작업 목록과 **시각은 코드에 고정**한다(목록 밖 이름은 거부). 시각을 바꾸려면 개발 큐 작업이다.
  - 켜기 파일 `docs/claude/llm-pilots-schedule.json`은 `{job: {enabled, approved_ref, approved_kst}}`만 담는다.
    - approved_ref = 사장 입력 메시지 id, 또는 카드 id + 제안 id + 선택지 + 누른 계정(버튼 승인 기록 4가지 — active-decisions.md 78행).
    - 실행기는 작업 트리가 아니라 **커밋본**(`git show HEAD:docs/claude/llm-pilots-schedule.json`)만 읽는다. 커밋되지 않은 편집으로는 켜지지 않는다.
    - 실행기는 형식만 확인한다(`cmsg_` id, 사장 계정 id 상수, KST 시각). 형식이 틀리거나 비면 거부한다. 진위는 못 가리므로, 커밋 전에 이 스레드가 승인 원문과 대조하고 `_pending` 파일을 남긴다.
  - 켜기는 지침 4절 ①의 승인(직접 입력 또는 직접 누른 버튼)으로만 받는다. 끄기는 사장님이 Windows 작업을 직접 꺼도 된다.
  - 등록은 사장님 PowerShell 1줄 1번이다(SEC 수집기 등록 스크립트 register_sec_scheduled_shadow_task.ps1과 같은 방식).
  - 이 스레드는 실행기를 실행하거나 등록하지 않는다(e-filing 4번 원칙과 같음).

## 4. 시범별 사양

### 시범 1 — 기록 대조 검토자 (`llm-iccheck`, 작업 1)
- **목적:** 사장 11/03 지시("통합점검에 기록과 다르거나 이상한 곳이 있으면 안 된다")를 매일 독립된 눈으로 본다.
- **언제:** 매일 07:30 KST, 통합점검 06:40 뒤. 그날 연구 기록이 없으면 "검토 못 함: 오늘 연구 기록 없음".
- **입력:**
  - 그날 `research-record.json`: 금액·수량을 지우고 행 번호를 붙인다(`R<n>|`).
  - `docs/claude/active-decisions.md`: 금액·수량을 가린 뒤 행 번호 `D<n>|`(112,265 B — 토큰 수는 첫 실행 count_tokens로 확정, 확인 필요).
- **모델:** `claude-sonnet-5-5`, 보통 호출(Batch 아님, 스트리밍으로 받음), effort medium, max_tokens 16000, 입력 상한 150K 토큰.
- **스크립트:** `llm_pilot_iccheck.py`(+ 공통 `llm_pilot_common.py`), 시험 `test_llm_pilot*.py`. Builder 지시문은 `llm-iccheck-builder-prompt.md`.
- **출력 스키마:** `{findings:[{summary_ko, record_quote{line,text}, decision_quote{line,text}, severity: high|mid|low}] (최대 10), checked_lines{record, decisions}}`. 인용 둘 다 원문에서 찾은 것만 남긴다.
- **결과 파일:** `workspace/outputs/llm/iccheck/<날짜>/review.json`. 발견이 있으면 `alert.md`, 실패면 `failed.md`. 화면 연결은 없다.
- **합격 기준(미리 고정):** 10거래일 동안 이 스레드가 발견마다 원문으로 대조한다.
  - 맞은 비율 ≥ 70%면 통합점검 대시보드 표시 연결을 따로 제안한다.
  - < 50%면 끈다.
  - 그 사이이거나 발견이 3건 미만이면 10거래일을 1번 연장한다. 연장 뒤에도 70%에 못 미치면 끈다(NO_CHANGE).
- **소비자:** 이 스레드의 10거래일 채점 기록(`docs/claude/llm-iccheck-score.md`). 연결 지도(analysis-linkage-map)에 1줄 더한다.
- **비용 추정:** 입력 약 80K × $2/MTok + 출력 약 6K × $10/MTok ≈ 하루 $0.22, 월 22일 약 $5(확인 필요).

### 실행기 (`llm-runner`, 작업 2)
- `llm_runner.py`, 래퍼 `run_llm_pilots.ps1`(사용자 범위 키 변수를 프로세스 변수로만 넘김 — 3절 1), `register_llm_pilots_task.ps1`을 만든다.
- 작업 목록은 코드에 고정한다(iccheck · news-submit · news-collect · pdfcmp-submit · pdfcmp-collect · srccheck-submit · srccheck-collect).
- 켜기 파일은 `{job: {enabled, approved_ref, approved_kst}}`(커밋본만 읽음 — 3절 실행 방법)이고, 시각은 `llm_runner.py` 상수다. 같은 작업이 같은 날 같은 시각에 두 번 돌지 않게 `workspace/outputs/llm/runner/<날짜>.json`에 실행 기록을 남긴다.
- 실행기 자신은 API를 부르지 않는다. 실패해도 다음 작업을 돌린다. 10분 간격이라 시각은 ±10분 정밀도다.
- B를 다시 열어 시범 6을 만들면, 그 작업이 `llm_runner.py` 작업 목록에 review를 더한다(그 작업 허용 파일에 llm_runner.py 포함).

### 시범 2 — 공시·뉴스 요약 + 그림자 점수 (`llm-news`, 작업 3)
- **언제:** 매일 19:30 KST에 Batch를 제출하고 22:00·23:00 KST에 수거한다. 받은 시각 = 수거 스크립트가 결과를 받은 KST 시각이다. 미국 정규장 개장(겨울 23:30 · 여름 22:30 KST) 전에 받은 점수만 표본에 든다(사전 등록 timing). 수거는 개장 30분 앞이라 실행기 10분 간격으로 늦어져도 개장 전이다(182일 기간에 2027-03-14 여름 시간 전환이 들어감).
- **단위:** (종목, s(d)) — s(d)가 같은 날들(토·일·월 KST → 같은 월요일 장)의 기사를 합친다. 주 블록은 s(d)의 ISO 주다.
- **입력:**
  - 대상 30종목은 사전 등록에서 고정한다.
  - `yfinance` `Ticker.news`(최근 약 10건)를 쓴다. 이미 쓰는 의존성을 다시 쓴다(requirements.txt 1행).
  - 처음 본 기사만 쓰고 first_seen_at을 남긴다.
  - 점수 요청에는 회사 이름·종목 기호를 지운 제목+요약을 보낸다(별칭 사전 `llm-news-prereg-v1.json`).
  - 요약 요청은 이름을 그대로 두고 한국어 3줄로 받는다. 표시용이고 점수와 분리한다.
- **모델:** `claude-haiku-5-5` Batch, effort low, 구조화 출력 `{label: good|bad|unknown, reason ≤ 80자}`.
- **기록:**
  - `workspace/outputs/llm/news/records.jsonl`: 덧붙이기만 한다. 줄마다 앞 줄 sha256을 넣어 고치면 깨진다.
  - 점수는 화면에 보이지 않는다. 요약은 `news/<날짜>/digest.md`에 쓴다.
  - 응답 model이 `claude-haiku-5-5`도 `claude-haiku-5-5-YYYYMMDD`(하이픈 + 숫자 8자리 — 공통 check_message와 같음)도 아니거나, 404이거나, 사전 등록 sha가 다르면 HALT한다.
- **소비자:** digest.md는 사장실 지정 시 표시(지정 전에는 이 스레드 확인용), 점수는 182일 채점기.
- **채점:** 사전 등록 v1대로 시작 + 182일에 1번 한다. 채점기는 그때 별도 작업이다.
- **비용:** 점수 요청 하루 약 30~100건 × (입력 약 600 + 출력 약 60토큰) + 요약 요청 같은 수 × (입력 약 600 + 출력 약 200토큰), Haiku 5.5($0.10/$0.50 per MTok) Batch 절반 가격 → 하루 약 $0.004~0.013, 월 약 $0.1~0.4(사고 토큰만큼 늘 수 있음, 확인 필요).

### 시범 3 — 무거운 문서 일 옮기기: 외부자료 PDF 1차 분류 (`llm-pdfcmp`, 작업 4)
- **1회 비교:** 원장(external-claims-ledger.md)에 이미 처리된 외부자료 PDF 10개를 쓴다.
  - 단위는 PDF 하나다. 그래서 **원장에서 처리 경로가 하나뿐인 PDF**만 고른다. 묶음 항목('R0 5' 같은)은 PDF가 3~8개씩 들어 있고, 같은 PDF가 두 무리에 다 들어 있기도 하다(EXT-20261008-02와 -08-03 2번, EXT-20261005-03 6번과 EXT-20261009-06 — 원장 276·343~344·696~750행).
  - 고르기와 파일 이름 적기는 작업 4 등록 전에 이 스레드가 원장 원자료 줄(파일 이름·폴더가 적혀 있음)에서 읽기 전용으로 한다. 후보 5 · R0 5를 유지한다.
  - 이 PDF들을 Files API로 올리고 Haiku Batch + 인용으로 "분류(후보|R0) · 라우트 · 대상 · 근거(인용)" 줄 형식을 받아 원장 결과와 비교한다.
- **합격:** 분류 일치 ≥ 8/10이고 주제 겹침 ≥ 8/10이면 외부자료 PDF 1차 분류를 API로 옮기는 안을 따로 제안한다. 미달이면 지금 방식을 유지하고 질문을 닫는다. PDF가 8개 미만이면 판단 보류다.
- **기타:**
  - 올린 파일은 수거 뒤 지운다.
  - PDF 폴더는 인자로 받는다(기본 = 원장 17행의 외부자료 폴더). **확인 필요:** 이 폴더는 이 스레드에 연결돼 있지 않고, 원장 원자료 줄의 파일 이름 일부에 '...'가 있다. 그래서 실제 파일 유무와 이름을 이 스레드가 확인할 수 없다. 작업 4 실행 전에 폴더를 연결하거나 사장님이 확인한다. 없는 파일은 빼고, 8개 미만이면 보류한다.
- **소비자:** 이 스레드의 1회 비교 기록(외부자료 PDF 처리 경로를 옮길지의 제안).
- **비용:** 10개 × 약 30K토큰 × $0.10 × 0.5 ≈ $0.02.

### 시범 4 — 출처 확인 자동화 (`llm-srccheck`, 작업 5 — A)
- **언제:** 매일 08:10 KST에 Batch를 제출하고 10:10 KST에 수거한다. 하루 최대 5건이다.
- **대상(고침):** 옛 대상 조건(확인 조건이 지남 + 허용 호스트 URL)에 맞는 원장 대기 항목이 0건이다(대기 35건, 허용 호스트 URL 줄 3줄 — 원장 466·494·508행). 그래서 대상을 바꾼다.
  - (a) 그날 연구 기록의 earnings·official_facts 항목 가운데 `source_url`이 허용 호스트인 것. 허용 호스트: sec.gov 문서(`/Archives/edgar/data/`만), federalreserve.gov, bls.gov, bea.gov, treasury.gov, fred.stlouisfed.org, 그리고 작업 5 지시문에 글자 그대로 고정하는 회사 IR 호스트 목록. 경로 없는 첫 화면 URL(예: `investors.delltechnologies.com/`)은 뺀다.
  - (b) SEC 수집기 산출물(`workspace/outputs/official-event-intake/sec/<날짜>/…/normalized-events.json`)의 새 공시. 산출물의 `source_url`은 data.sec.gov submissions JSON이라 쓰지 않고, `https://www.sec.gov/Archives/edgar/data/<cik 정수>/<접수번호 대시 제거>/<primary_document>`로 만든다.
  - 중복: URL(SEC는 접수번호)마다 1번만 본다(`srccheck/seen.jsonl`). 같은 source_url이 날마다 반복되고(최근 기록 19개에서 같은 IR URL 18번), 수집기는 7일을 돌아봐 접수번호가 날마다 겹친다.
  - 새 대상은 이미 확인된 사실이다(연구 기록 earnings `status: VERIFIED`, SEC 산출물 `verification_status: OFFICIAL_SOURCE_VERIFIED`). 그래서 시범 4는 원장 확인을 대신하지 않는다. 통합점검이 쓰는 공식 사실을 원문으로 한 번 더 확인하는 일이다.
  - 정답: 이 스레드가 같은 URL을 원문(WebFetch, 안 되면 WebSearch 발췌)으로 대조한 판정.
- **모델:** `claude-sonnet-5-5` + `web_fetch_20260209`(citations 켬, **max_uses 1**, allowed_domains = 그 URL의 호스트, max_content_tokens 20,000). allowed_domains는 호스트 단위라 같은 호스트의 다른 경로도 열 수 있다. 그래서 응답 `web_fetch_tool_result` 블록의 url이 입력 URL과 글자 그대로 같지 않으면 그 결과를 버리고 기록한다. `server_tool_use` 입력으로 대조하지 않는 까닭은, Sonnet 5.5에서 `web_fetch_20260209`는 동적 필터링(코드 실행 안에서 가져오기)이 켜질 수 있어 그 입력만으로는 놓칠 수 있기 때문이다(확인 필요 — 7절 3). 결과 블록이나 인용이 없으면 '확인 불가'다.
- **출력:** "판정: 맞음|틀림|미정|확인 불가" + 인용된 근거. 인용이 없으면 '확인 불가'로 낮춘다.
  - 결과는 `workspace/outputs/llm/srccheck/<날짜>/checks.md`에 쓴다. **원장·연구 기록·통합점검 규칙은 쓰지 않는다.**
  - 가져오기가 거부된 URL은 기록하고 다시 시도하지 않는다(우회 금지).
- **합격:** 20건에서 이 스레드 원문 대조와 일치 ≥ 80%면 '통합점검 공식 사실 재확인 표시'(통합점검에 '원문 재확인 맞음/틀림' 표시) 안을 따로 제안한다. 켠 뒤 60일 안에 20건이 안 모이면 NO_CHANGE로 닫는다. 첫 2주 '확인 불가' 비율을 기록한다(sec.gov 직접 열람 실패 기록이 있음 — 원장 508행).
- **소비자:** 이 스레드의 통합점검 검토(20건 대조 기록).
- **비용:** 5건 × (입력 약 25K + 출력 약 1K) × Sonnet 가격 × 0.5 ≈ 하루 $0.15, 월 약 $3~5(가져온 본문 토큰에 따라, 확인 필요).

## 5. 시범 4 대 e-filing 결정(2026-10-05) — **맞음(조건부)**

| e-filing 결정(e-filing-feed-review-2026-10-05.md) | 시범 4 |
|---|---|
| 49행 1. Claude는 sec.gov를 bash·python·curl로 가져오지 않는다. WebFetch가 거부한 곳(browse-edgar·efts·daily-index·GlobeNewswire RSS)은 어떤 방법으로도 쓰지 않는다 | 스크립트는 sec.gov에 요청하지 않는다. Anthropic 웹 가져오기가 이미 기록된 **문서 URL**만 연다 — 51행(3)의 'source_url을 WebFetch로 열어 확인'과 같은 종류다. 거부 경로는 정규식(`/cgi-bin`·`efts`·`daily-index`·`rss`)과 allowed_domains로 뺀다 |
| 50행 2. 수집 주체 = 사용자 PC Windows 작업의 저장소 스크립트, data.sec.gov submissions만 | 수집(목록·피드)은 하지 않는다. 대상 URL은 연구 기록과 기존 수집기 산출물에서만 나온다 |
| 51행 3. Claude는 로컬 산출물만 읽고, 수치는 source_url을 WebFetch로 확인 | 같은 확인을 API의 웹 가져오기가 하고, 결과는 로컬 산출물(checks.md)이다 |
| 52행 4. Claude가 수집기를 실행·등록하지 않는다 | 실행·등록은 실행기(사장님 등록)가 한다. 이 스레드는 실행하지 않는다 |
| 53행 5. 스크립트에 /cgi-bin·RSS 경로 금지 | 코드와 시험에서 거부한다 |
| 24행 문서 URL 직접(`/Archives/edgar/data/…`) = robots Allow, '유지 — 수치 읽기용'(10/04 자료) | 대상은 이 경로만이다. 단 10/27 원장 기록에 '본문 직접 열람은 sec.gov 접속 실패'가 있다(508행) — 첫 2주 '확인 불가' 비율로 확인 |

- 조건: SEC가 Anthropic 가져오기를 거부하면(결과 블록 오류), 그 URL은 '확인 불가'로 두고 기존 WebFetch 경로로 돌아간다. 다른 방법으로 우회하지 않는다.

## 6. 순서 · 사장님 손 · 되돌리기

| # | 개발 큐 작업(일반 변경) | 등록 조건 | 사장님 손 |
|---|---|---|---|
| 1 | `llm-iccheck` — 공통 모듈 + 시범 1 + requirements-llm.txt | 이 제안 승인 | `pip install -r manage-us-stock-strategy\requirements-llm.txt` 1줄 + 첫 실행 1줄(새 PowerShell 창) |
| 2 | `llm-runner` — 실행기 + 등록 스크립트 + 켜기 파일(모두 꺼짐) | 1 병합 + 첫 실행 성공 | 등록 승인 + 등록 1줄(1번) · 시범 1 켜기 승인 |
| 3 | `llm-news` — 시범 2 + 사전 등록 v1 파일 | 2 병합 | 시범 2 켜기 승인 |
| 4 | `llm-pdfcmp` — 시범 3 | 3 병합 + PDF 10개 이름 확정(이 스레드) | 1회 실행 켜기 승인 |
| 5 | `llm-srccheck` — 시범 4 | 4 병합 | 시범 4 켜기 승인 |

승인은 매번 이 스레드 카드의 버튼 1번 또는 직접 입력이다(등록 = `예약 작업 변경 승인: InvestmentV2-LLMPilots`, 시범 켜기 = `예약 작업 변경 승인: InvestmentV2-LLMPilots/<시범>`). 한 카드에 결정 1개.

- 병합: 일반 변경은 결과가 READY_TO_MERGE이면 Cowork가 `dev-merge.ps1 <id>`로 병합한다(CLAUDE.md 63~64행). 이 스레드는 병합하지 않는다.
- 작업마다 Builder 지시문은 앞 작업이 병합된 뒤 그 코드를 읽고 확정한다(작업 1 지시문만 지금 완성).
- 되돌리기:
  - 시범 끄기 = 켜기 파일에서 끄기(승인 1번) 또는 Windows 작업 끄기(사장 1줄).
  - 코드 되돌리기 = 개발 큐로 되돌리기 커밋.
  - 키 폐기 = Console에서 사장님이 한다.
  - 시범 출력의 소비자는 시범마다 4절에 적은 기록뿐이고 코어·원장·통합점검은 읽지 않아, 지워도 운영 영향이 없다. 연결 지도(analysis-linkage-map)에 시범마다 1줄을 더한다.

## 7. 확인 필요 (첫 실행·등록 때 확인, 그 전까지 보수적으로)

1. Batch·웹 가져오기 사용분이 Max 월 크레딧에서 빠지는지. 크레딧 문서에 Batch 이름이 없다(api-credits-max-1106). 빠지지 않으면 시범 2~4는 멈추고 묻는다.
2. Batch + 구조화 출력: 문서상 된다. Batch 문서는 'Messages API 기능 모두 지원'(claude-api batches.md 11행), 구조화 출력 문서는 'Works with: Batches API, streaming, token counting'(claude-api tool-use-concepts.md)이다. 시범 2 첫 제출로 실제 확인한다.
3. Batch 안에서 Files API file_id와 웹 가져오기가 되는지: 시범 3·4 첫 제출로 확인한다. 웹 가져오기 결과 블록의 모양(`web_fetch_tool_result`의 url, 인용 유무, 동적 필터링이 켜졌을 때의 모양)도 같이 확인한다.
4. 작업 스케줄러가 새 사용자 변수를 못 읽을 수 있는 문제: 래퍼 `run_llm_pilots.ps1`이 사용자 범위 변수를 직접 읽어 프로세스 변수로 넘기는 설계로 피한다(3절 1). SEC 래퍼는 넘기지 않고 막는 방식이라 선례가 아니다. 등록 뒤 첫 실행이 NO_KEY가 아닌지로 확인한다.
5. 회사PC Windows Python은 3.13.15다(docs/claude/c1-keep-judge-report.md 9행, Judge 실행 환경 기록). SDK 조건(3.10 이상)을 만족한다. PC의 yfinance 판은 확인 필요.
6. (풀림) `anthropic==2.3.0`에 정식 `client.files`(upload·delete, 베타 헤더 없음)가 있다. count_tokens와 stream도 output_config를 받는다(휠 확인).
7. 시범 1 입력 토큰 수와 실제 하루 비용(첫 실행 usage로 확정).

## 8. 바뀔 조건

- 첫 2주 usage에서 한 시범이 월 상한의 80%를 넘을 추세면 그 시범의 빈도·대상 수를 줄인다(사장 승인).
- 시범 1에서 맞은 비율이 낮으면(< 50%) 끄고 질문을 닫는다. 시범 2·3·4는 4절 합격 기준대로 한다.
- 크레딧이 Batch에 쓰이지 않거나 키가 폐기되면 모든 시범이 NO_KEY 또는 BUDGET_STOP으로 스스로 멈춘다(코어 영향 없음).

## 9. 검토 완결

- V5 내장 재검토 2회로 끝냈다. 횟수 상한이 2회라 3회차는 없다(review-stability-2026-10-13.md 120행). subagent는 과제·초안·근거 위치만 받았고, 본 세션이 발견마다 원문을 다시 열어 맞는 것만 고쳤다.
- 1회차(2026-11-06 15:48 KST 보고): 27건, 모두 반영. 일부(SEC 래퍼 선례, B 금액 가리기, 날짜 붙은 모델 이름)는 2회차에서 다시 고쳤다.
- 2회차(16:31 KST 보고, 1회차 반영분만): 21건. 결론을 바꾼 것 6건, 모두 반영:
  - 연구 기록 reconcile·잔고 줄의 단위 없는 수량(3절 8)
  - 결정 색인 99행 "옛 값 N"(3절 8)
  - 시범 2 수거 시각 여유(22:00·23:00으로 당김, 사전 등록 sha 새로 계산)
  - 별칭 대소문자 열린 목록 → 닫힌 목록 6개
  - 두 글자 기호의 `(MU)`·`NASDAQ:MU` 꼴
  - 시범 4 합격 행동·소비자(원장 → 통합점검 재확인)
- 나머지 15건(문구·근거·비용·중복·형식)도 반영했다. 본 세션이 다시 연 원문은 다음과 같다.
  - active-decisions.md 78행, approval-venue-table-2026-10-25.md 26행, btn-approval-proposal-2026-10-27.md 47행
  - scheduled-prompts/README.md 3행, run_sec_scheduled_shadow.ps1 219·248~255행
  - claude-api models.md(Haiku 5.5 가격), batches.md(Batch 캐싱 예시)
- 미해결: 설계 결함으로 남은 것은 0건이다. 첫 실행으로만 풀리는 확인 필요는 7절 1·2·3·4·5·7과 시범 3 PDF 폴더(4절)다.
