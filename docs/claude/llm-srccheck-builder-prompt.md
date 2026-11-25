---
id: llm-srccheck-builder-prompt
title: "API 시범 4 — 출처 확인 자동화(이미 확인된 공식 사실을 원문 URL로 한 번 더 확인) — llm-srccheck"
date: 2026-11-25
class: "general(새 시범 스크립트 1개와 그 시험만, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork 또는 사장 dev-merge"
source: "설계 docs/claude/api-pilots-2026-11-06.md 4절 시범 4(166~180행)·5절 e-filing 대조(182~193행)·6절 순서 5(사장 2026-11-06 16:44:47 KST 카드 '시범 1부터 차례로'). 이번 등록 = 사장 결정 카드 'P1b 개발 큐 + P2 시범'(cmsg_0137MRzn9nuDvvQmVxm6WeX95rNSzrSLUx2SjPaLHndQPN, 2026-11-25 09:18:26 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH) — docs/claude/api-credit-expand-design-2026-11-25.md 8절. 앞 작업 llm-pdfcmp 병합 f184e56"
authority: "권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · 계좌·보유 자료를 API로 보내지 않음 · API 키 값을 읽거나 출력하지 않음 · 켜기 파일을 바꾸지 않음 · sec.gov에 스크립트가 직접 요청하지 않음"
---

## 목표
- 그날 연구 기록과 SEC 수집기 산출물에 **이미 확인됨으로 적힌 공식 사실**에서 원문 URL이 있는 것을 하루 최대 5건 골라, `claude-sonnet-5-5` Batch + 웹 가져오기 도구(그 URL 1개만, 인용 켬)로 "주장이 원문과 맞는가"를 판정받아 `workspace/outputs/llm/srccheck/<날짜>/checks.md`에 쓴다.
- 이것은 원장 확인을 대신하지 않는다. 통합점검이 쓰는 공식 사실을 원문으로 한 번 더 확인하는 표시 전용 그림자다. **원장·연구 기록·통합점검 규칙·SEC 산출물은 쓰지 않는다.**
- 합격(설계 4절, 이 작업 밖에서 판정): 20건에서 사장실 스레드의 원문 대조(WebFetch)와 일치 ≥ 80%면 '통합점검 공식 사실 재확인 표시' 안을 따로 제안. 켠 뒤 60일 안에 20건이 안 모이면 NO_CHANGE로 닫음. 이 작업은 대조에 쓸 누적 기록 `checks.jsonl`까지만 만든다.

## 바꿀 파일 (이 3개만, 모두 새 파일)
- manage-us-stock-strategy/scripts/llm_pilot_srccheck.py (LF, ASCII만 — 한글 상수는 `\uXXXX` 이스케이프)
- manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py (LF)
- docs/claude/llm-srccheck-report.md (LF, 보고)
- llm_runner.py는 이미 srccheck 두 작업과 스크립트 이름을 갖고 있어(`llm_runner.py:51-52`, 인자 `--phase submit|collect` + 실행기가 붙이는 `--day <날짜>`, 309행) 고치지 않는다.

## 먼저 읽을 것 (고치지 않는다)
- `manage-us-stock-strategy/scripts/llm_pilot_common.py` 전체: `load_key`·`make_client`·`api_error_label`·`estimate_cost(batch=True)`·`append_usage`·`month_spend`·`atomic_write_text`·`write_failed`·`response_text`·`check_message`·`MODELS["srccheck"]`(= claude-sonnet-5-5)·`BUDGET_USD_MONTH["srccheck"]`(= 6)·`USAGE_KEYS`.
- `manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py`: **제출·수거 뼈대를 이 파일에서 그대로 따른다** — `valid_day`·`_line`·`run_submit`(402행, `batches.create` 470행)·`run_collect`(653행, `retrieve` 694행·`results` 702행·custom_id 대조 737행)·`citation_texts`(548행)·`quote_overlaps`(558행)·`_usage_numbers`·`_message_cost`·`_remove_stale_failed`·`_write_unexpected`·`main`(839행). 같은 이름 함수는 복사해도 된다(공통 모듈은 고치지 않는다).
- `manage-us-stock-strategy/tests/test_llm_pilot_news.py`의 `test_script_source_contract`(금지어 목록) — 새 스크립트도 같은 금지어를 쓰지 않는다(environ·zoneinfo·subprocess·import requests·urllib·fallbacks·advisor·socket·http.client·auto_core·kiwoom, 주석 포함). URL은 `urllib` 없이 문자열 규칙으로 나눈다(아래 3).
- `docs/claude/api-pilots-2026-11-06.md` 166~193행(시범 4 사양·e-filing 대조), `docs/claude/e-filing-feed-review-2026-10-05.md` 47~53행(웹 접근 제한 규칙).
- 연구 기록 하나(`workspace/outputs/research-records/<최근 날짜>/research-record.json`)와 SEC 산출물 하나(`workspace/outputs/official-event-intake/sec/<최근 날짜>/<실행 폴더>/normalized-events.json`)의 **모양만** 본다. 값을 보고서에 옮기지 않는다.

## 구현 요구

### 1. 대상 모으기 (`collect_targets(root, day)`)
- **(a) 연구 기록** `workspace/outputs/research-records/<day>/research-record.json`(없으면 (a)는 0건, 실패 아님):
  - `earnings`(종목 → 항목 dict): `status == "VERIFIED"`이고 `source_url`이 있는 항목만. 주장에 쓰는 칸은 **종목 기호·`announcement_session`·`timing`(있을 때)·`source_kind`뿐**이다. `NOT_ANNOUNCED`는 빼다(없음을 원문으로 확인할 수 없다).
  - `official_facts`(목록): `source_url`이 있는 항목. 주장에 쓰는 칸은 **`symbol`·`kind`·`event_session`·`announced_at`·`summary_ko`뿐**이다.
  - 연구 기록의 다른 키(`integrated_check_run`·`order_authority`·`quantity_authority`·`writer` 등)는 읽지도 보내지도 않는다.
- **(b) SEC 수집기 산출물**: `workspace/outputs/official-event-intake/sec/<day-2>~<day>/*/normalized-events.json`의 `events`(수집기가 KST 12시대에 돌아 08:10에는 그날 폴더가 없을 수 있어 사흘을 본다. 중복은 아래 seen이 막는다).
  - `verification_status == "OFFICIAL_SOURCE_VERIFIED"`이고 `form`이 `SEC_FORMS = ("8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A", "6-K", "20-F", "DEF 14A")`에 있는 것만(내부자 Form 4·144는 뺀다).
  - URL은 산출물의 `source_url`(data.sec.gov submissions JSON)을 쓰지 않고 `https://www.sec.gov/Archives/edgar/data/<int(cik)>/<accession_number에서 '-' 제거>/<primary_document>`로 만든다. `cik`는 숫자만, `accession_number`는 `\d{10}-\d{2}-\d{6}`, `primary_document`는 `[A-Za-z0-9._-]+`(슬래시 없음)일 때만. 아니면 그 사건은 뺀다(`skipped`에 이유).
  - 주장에 쓰는 칸은 **`ticker`·`company_name`·`form`·`report_date`·`items_if_available`뿐**이다(`filing_date`는 EDGAR 메타자료라 문서 본문에 없을 수 있어 줄 세우기에만 쓴다). `portfolio_context`·`deferred_symbols`·`ownership_coverage`는 읽지 않는다.
  - 파일이 깨졌으면 그 파일만 건너뛰고 `skipped`에 적는다.
- **중복**: 키 = SEC는 `sec:<accession_number>`, 나머지는 URL 문자열. `workspace/outputs/llm/srccheck/seen.jsonl`(한 줄 = `{"key","day","url"}`)에 있는 키와 그날 안의 같은 키는 뺀다. 한 번 보낸 키는 결과가 오류·거부여도 다시 보내지 않는다(설계 '거부된 URL은 다시 시도하지 않는다').
- **순서와 상한**: official_facts → earnings → SEC(8-K·8-K/A 먼저, 그다음 `filing_date` 내림차순) 순으로 줄 세워 앞에서 `DAILY_MAX = 5`건.

### 2. 주장 문장 (`claim_text(target)`)
- 위 허용 칸만으로 만든 짧은 한국어 문장(상수 틀, 이스케이프). 예: 실적 발표일 = "<기호>의 실적 발표일은 <announcement_session>(<timing>)이다"; SEC = "<company_name>(<ticker>)의 <form> 서류이고, 보고 기준일 <report_date>, 항목 <items>이다".
- 이 문장들은 회사가 공개한 사실이라 `mask_text`·`strip_amounts`를 쓰지 않는다(쓰면 공시 수치가 `[금액]`으로 바뀌어 대조가 안 된다). 대신 **허용 칸 밖의 값이 요청에 들어가지 않음**을 시험으로 막는다(아래 시험).

### 3. URL 허용 규칙 (`url_allowed(url)`, `urllib` 없이)
- `https://`로 시작, `?`·`#`·공백 없음, 호스트(소문자)가 `ALLOWED_HOSTS`와 글자 그대로 같음.
- `ALLOWED_HOSTS`(글자 그대로 고정):
  - 공식 기관: `www.sec.gov` · `www.federalreserve.gov` · `www.bls.gov` · `www.bea.gov` · `home.treasury.gov` · `fred.stlouisfed.org`
  - 회사 IR(연구 기록에 나온 호스트): `investors.delltechnologies.com` · `investors.quantaservices.com` · `investor.lumentum.com` · `investor.marvell.com` · `www.bloomenergy.com` · `investor.bloomenergy.com` · `investors.micron.com` · `ir.crowdstrike.com` · `nebius.com`
- `www.sec.gov`는 경로가 `/Archives/edgar/data/`로 시작할 때만.
- 경로가 비었거나 `/`뿐인 첫 화면 URL은 뺀다.
- 경로·전체 URL에 `cgi-bin`·`efts`·`daily-index`·`rss`·`browse-edgar`가 있으면(대소문자 무시) 뺀다(e-filing 규칙 1·5).
- 빠진 URL은 `skipped`에 키와 이유(HOST_NOT_ALLOWED|ROOT_PAGE|BLOCKED_PATH|BAD_URL)로 적는다.

### 4. 제출 (`--phase submit`)
- 그날 폴더 = `workspace/outputs/llm/srccheck/<day>/`. `checks.json`이 있으면 `DONE_ALREADY`, `batch.json`이 있으면 `PENDING`(다시 제출하지 않음).
- 대상 0건이면 `NO_TARGETS`(API·키 확인 없음, 아무것도 쓰지 않음).
- 키 확인(`load_key`, 없으면 NO_KEY) → 이달 `month_spend(root, "srccheck", "<KST YYYY-MM>")`(예외면 BUDGET_STOP) + 이번 추정(건당 입력 30,000토큰·출력 4,096토큰, Sonnet 가격, Batch 0.5배)이 `BUDGET_USD_MONTH["srccheck"]`를 넘으면 BUDGET_STOP·호출 0.
- `client.messages.batches.create`: 요청 1개 = 대상 1개, `custom_id` = `t1`~`t5`, `model` = `MODELS["srccheck"]`, `max_tokens` 4096, `tools` = 정확히 1개:
  `{"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 1, "allowed_domains": [<그 URL의 호스트>], "max_content_tokens": 20000, "citations": {"enabled": true}}`.
  messages = user 1개: 판정 지침(상수) + `URL: <url>` + `주장: <claim>`. 서버 대체 모델·advisor·베타 헤더·다른 도구(code_execution 포함) 쓰지 않음. `count_tokens`는 쓰지 않는다(가져온 본문 상한은 `max_content_tokens`). `cache_control`은 붙이지 않는다(공통 앞부분이 512토큰 미만, 설계 3절 6).
- 판정 지침(상수, 고정): "아래 URL 하나만 web_fetch로 한 번 연다. 다른 URL은 열지 않는다. 주장이 원문과 맞는지 본다. 답은 두 줄로만: `판정: 맞음|틀림|미정|확인 불가` / `근거: <원문 문장 그대로 한 줄>`. 주장 일부만 원문에 있으면 `판정: 미정`. 열 수 없거나 원문에 해당 내용이 없으면 `판정: 확인 불가`." 금액·수량·보유를 묻지 않는다.
- 쓰기 순서: Batch 생성 → `batch.json`(batch_id, 대상별 custom_id·key·url·claim·source(a|b)) 원자적 쓰기 → `seen.jsonl`에 대상마다 1줄 덧붙이기. 생성이 실패하면 아무것도 쓰지 않고 API_ERROR + failed.md.

### 5. 수거 (`--phase collect`)
- 수거 대상 폴더 = `<day>`와 앞 3일(`<day-3>`~`<day>`) 가운데 `batch.json`은 있고 `checks.json`이 없는 폴더 전부(실행기 수거는 하루 1번 10:10이라, 그때 안 끝난 Batch를 다음 날 수거가 받는다. seen 때문에 대상은 다시 제출되지 않으므로 이것이 없으면 결과와 비용 기록이 사라진다). 폴더마다 아래를 따로 한다.
- 그런 폴더가 하나도 없으면: `<day>`에 `checks.json`이 있으면 `DONE_ALREADY`, 아니면 `NO_BATCH`(아무것도 안 씀). 폴더의 `retrieve`가 ended가 아니면 그 폴더는 `WAITING`(아무것도 안 씀). 마지막 줄 STATUS는 `<day>` 폴더 기준(그 폴더가 대상이 아니면 처리한 폴더 중 가장 최근 것), 처리한 다른 날은 마지막 줄 앞에 `llm-srccheck <그날> <STATUS>`로 한 줄씩 먼저 찍는다.
- 결과마다(custom_id로 대상과 짝):
  1. Batch 결과가 succeeded가 아니거나(errored·expired·canceled·없음) `check_message`가 None이 아니면 → 판정 `확인 불가`, 사유 = 그 이름.
  2. 응답 content에서 `type == "web_fetch_tool_result"` 블록을 찾는다. 없으면 `확인 불가`·NO_FETCH_RESULT. 블록 안 결과가 오류 모양(`type`에 `error`가 들어감 또는 `error_code` 있음)이면 `확인 불가`·FETCH_REFUSED(오류 코드 문자열만 기록). 결과의 `url`이 입력 URL과 **글자 그대로** 같지 않으면 그 결과를 버리고 `확인 불가`·URL_MISMATCH(설계 4절: 같은 호스트 다른 경로를 막음). 블록 모양을 확인하려고 응답 content 블록 `type` 목록을 `block_types`로 함께 적는다(동적 필터링 때 모양 확인, 설계 7절 3).
  3. `response_text`의 마지막 `판정:` 줄과 `근거:` 줄을 정규식으로 읽는다. 형식이 틀리면 `확인 불가`·PARSE_FAIL.
  4. 인용: text 블록 citations 중 `cited_text`가 있고 그 글과 '근거' 줄이 공백 정규화 뒤 6자 이상 겹쳐야 한다(pdfcmp `quote_overlaps`와 같음). 아니면 모델 판정을 `model_verdict`로 남기고 판정은 `확인 불가`·NO_CITATION으로 낮춘다.
- `usage.jsonl`: `llm_pilot_pdfcmp.py:709-731`과 같게 — succeeded이고 message가 있는 결과마다 1줄(모델이 달라도 씀, `status` = `check_message` 이름 또는 OK), 폴더의 `usage-done` 표식으로 한 번만(`append_usage`, USAGE_KEYS 10개 모두: `ts_kst` KST ISO, `pilot` "srccheck", `model`, 토큰 4개, `batch` True, `cost_usd_est`, `status`). 웹 가져오기는 별도 요금 없이 가져온 본문이 입력 토큰으로 잡힌다고 보고 따로 셈하지 않는다(확인 필요로 보고).
- 쓰기: `checks.json`(대상별 key·url·source·claim·verdict·model_verdict·reason·evidence(200자까지)·block_types·stop_reason)과 `checks.md` 원자적 쓰기, 그 뒤에 누적 `workspace/outputs/llm/srccheck/checks.jsonl`에 대상마다 1줄(day·key·url·verdict·reason) 덧붙이기. `checks.md` 첫 줄 = `출처 확인 <day>: 맞음 a · 틀림 b · 미정 c · 확인 불가 d (n건)`, 그 아래 표(# · 출처(a|b) · URL · 주장 · 판정 · 사유 · 근거 60자) — 사장실 스레드가 이 표의 URL과 주장으로 원문을 대조한다.
- 수거 상태 = `CHECKED`.

### 6. 마지막 줄·종료 코드·실패
- stdout 마지막 줄(ASCII): `llm-srccheck <day> <STATUS>`(실행기 정규식 `llm_runner.py:69-70`).
- SUBMITTED·PENDING·WAITING·CHECKED·DONE_ALREADY·NO_TARGETS·NO_BATCH·DRY_RUN = 0, UNEXPECTED = 1, NO_KEY = 4, BUDGET_STOP = 5, API_ERROR = 7(`llm_pilot_pdfcmp.py`·`llm_pilot_news.py`와 같은 값).
- 실패는 `write_failed(<root>/workspace/outputs/llm/srccheck/<day>, STATUS, 이유)` 1줄. 다른 작업을 막지 않는다.
- `--dry-run`: 키·호출·쓰기 없이 그날 대상(키·URL·source)과 skipped만 출력.
- 키 값은 어디에도 쓰지 않는다. 오류는 `api_error_label`만.

## 시험 (test_llm_pilot_srccheck.py, 가짜 클라이언트·가짜 키·임시 폴더만)
- 임시 폴더에 가짜 연구 기록·가짜 SEC 산출물을 만든다(실제 workspace를 읽지 않는다). 가짜 연구 기록에는 `order_authority`·`quantity_authority`·`integrated_check_run`에, 가짜 SEC 파일에는 `portfolio_context`에 표식 문자열(예 `SENTINEL_NOT_SENT_1`)을 넣고 **Batch 요청 전체를 JSON으로 펼친 글에 표식이 없음**을 단언한다. 허용 칸 밖 earnings 키(예 `checked_at`)도 같은 방식.
- 대상: VERIFIED만·NOT_ANNOUNCED 뺌 / 첫 화면 URL 뺌 / 허용 밖 호스트 뺌 / `rss`·`cgi-bin`·`efts`·`daily-index`·`browse-edgar` 뺌 / `www.globenewswire.com`(설계 169행 목록 밖) 뺌 / SEC URL 조립(cik 앞 0 제거·접수번호 대시 제거)·Form 4·144 뺌·슬래시 있는 primary_document 뺌 / seen에 있는 키 뺌 / 순서와 5건 상한 / 깨진 SEC 파일 건너뜀.
- 제출: 요청마다 tools가 1개이고 `web_fetch_20260209`·`max_uses` 1·`allowed_domains` = [그 호스트]·citations 켬·모델 고정 / batch.json 있음 → PENDING / checks.json 있음 → DONE_ALREADY / 대상 0 → NO_TARGETS·클라이언트 생성 0 / 예산 넘음 → BUDGET_STOP·호출 0 / 키 없음 → NO_KEY / 제출 뒤 seen.jsonl 줄 수.
- 수거: 가짜 결과로 맞음(결과 url 같음·인용 겹침) / URL_MISMATCH / FETCH_REFUSED / NO_FETCH_RESULT / NO_CITATION으로 낮춤(model_verdict 보존) / PARSE_FAIL / errored·expired / MODEL_MISMATCH도 usage 1줄(status MODEL_MISMATCH)·usage-done 뒤 두 번째 수거에서 줄 안 늘어남 / 전날 WAITING 폴더를 다음 날 수거가 받음(그날 폴더와 함께) / usage 줄이 USAGE_KEYS 10개를 갖고 `month_spend`가 예외 없이 읽음 / checks.jsonl 줄 수 / WAITING·NO_BATCH는 쓰기 없음 / 마지막 줄 형식.
- 가짜 키 문자열이 stdout·모든 출력 파일에 없음.
- 소스 계약: 금지어 없음, 파일이 ASCII, `ALLOWED_HOSTS`가 이 지시문 목록과 글자 그대로 같음, 스크립트 안에 `sec.gov`로 직접 요청하는 코드가 없음(문자열은 URL 조립·허용 목록에만).
- Builder 시험 명령(이 글자 그대로): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_srccheck*.py"`. 전체 시험은 돌리지 않는다(파이프라인이 한다).

## 지켜야 할 것
1. 허용 파일 3개 밖은 손대지 않는다. `llm_pilot_common.py`·`llm_pilot_pdfcmp.py`·`llm_runner.py`·`llm-pilots-schedule.json`·연구 기록·SEC 산출물을 고치지 않는다. 기존 시험을 고치지 않는다.
2. 키 값을 읽지 않는다. 비밀(.env*·토큰·계좌번호) 파일을 열지 않는다.
3. 어떤 시범도 켜지 않는다. Windows 작업을 등록·실행·변경하지 않는다. 저장소 루트에 대고 스크립트를 돌리지 않는다(`--dry-run` 포함). pip로 무엇도 설치하지 않는다. 웹에 접속하지 않는다.
4. 주문·키움·일지·원장·예약·정책·상태와 무관하다. auto_core.py 실행 금지. git은 status·diff·log만. commit·push·병합 없음. `python -c` 쓰지 않음.
5. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/llm-srccheck-report.md
- (a) 만든 함수(파일:행)와 상수 · (b) 시험 이름과 단언 요약 · (c) 시험 결과 마지막 3줄 · `git diff --stat`
- (d) 병합 뒤 사장실이 할 일: 켜기 카드 1번(`srccheck-submit`·`srccheck-collect` 둘을 한 번에) — 실행은 실행기 08:10 제출·10:10 수거. 켠 날부터 사장실 스레드가 `checks.md`의 URL을 WebFetch로 대조해 20건 일치율을 센다(60일 기한).
- (e) 확인 필요로 남은 것: Batch 안에서 웹 가져오기가 되는지(설계 7절 3), `web_fetch_20260209` 동적 필터링 때 결과 블록 모양(block_types로 첫 실행 확인), sec.gov 문서를 Anthropic 가져오기가 여는지(원장 508행 '직접 열람 실패' 기록 — 첫 2주 '확인 불가' 비율), 가져온 본문 토큰과 실제 하루 비용, Batch·웹 가져오기 사용분이 크레딧에서 빠지는지(7절 1), 10:10에 안 끝난 Batch는 다음 날 수거가 받는다(하루 늦음), `max_tokens` 4096 안에 Sonnet 5.5 생각 토큰이 드는지 — MAX_TOKENS·BAD_STOP(pause_turn 포함) 건수와 `stop_reason`, count_tokens·cache_control을 쓰지 않은 이유 1줄, `www.globenewswire.com` 보도자료 URL은 설계 목록 밖이라 뺐다(넣을지는 사장실 판단).
- 수량·금액·키 값·실제 URL 목록을 적지 않는다. 주문·권한 표지 문자열도 적지 않고 '권한 표지 4종 줄 변경 없음'이라고만 쓴다.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| `workspace/outputs/llm/srccheck/<날짜>/checks.json`·`checks.md` · 누적 `srccheck/checks.jsonl` · `seen.jsonl` · `usage.jsonl` 줄(이 작업이 새로 만듦) | Windows 작업 InvestmentV2-LLMPilots → `manage-us-stock-strategy/scripts/llm_runner.py:51-52` srccheck-submit 08:10 · srccheck-collect 10:10 KST(켜기 파일 `docs/claude/llm-pilots-schedule.json` srccheck 두 줄이 켜졌을 때만) | 사람 단계 — 사장실 회사PC 스레드가 `checks.md`의 URL을 WebFetch로 열어 판정을 대조하고 20건 일치율을 센다(설계 원문 `docs/claude/api-pilots-2026-11-06.md:178-179` '합격 20건 ≥ 80%'·'소비자 = 이 스레드의 통합점검 검토') | 일치 ≥ 80%면 '통합점검 공식 사실 재확인 표시' 안 제안(별도 승인), 60일 안 20건 미달이면 NO_CHANGE로 닫음(`docs/claude/api-pilots-2026-11-06.md:178`) | 끊김 — 실행기 하루 기록 `workspace/outputs/llm/runner/<날짜>.json` status를 읽는 예약이 없다(`docs/claude/llm-pdfcmp-builder-prompt.md` 연결표와 같은 끊김). 메울 변경: 사장실 결과 모음 예약이 실행기 하루 기록을 읽게 하기 · 승인 경로: 지침 4절 `예약 작업 변경 승인: <이름>`(이 작업 밖). 그 전까지는 켠 날부터 사장실 스레드가 10:30 KST 뒤 `checks.md`를 직접 읽는다 | 연결(산출) · 알림 끊김(기존과 같음) |

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이다(새 파일 3개). 공통 모듈·pdfcmp·실행기·켜기 파일·연구 기록·SEC 산출물 변경 없음.
2. `ALLOWED_HOSTS`·SEC 경로 제한·차단 낱말·첫 화면 제외가 이 지시문과 글자 그대로 같고, 스크립트가 sec.gov나 다른 웹 주소에 직접 요청하는 코드가 없다(요청은 Anthropic Batch API뿐).
3. 요청 tools가 웹 가져오기 1개(max_uses 1·allowed_domains = 그 호스트·citations 켬)뿐이고, 결과 url 글자 대조·인용 없으면 '확인 불가'로 낮춤·가져오기 거부는 다시 시도 안 함(seen)이 코드와 시험에 있다.
4. 요청에 허용 칸 밖 값(연구 기록 권한 키·SEC portfolio_context 등)이 들어가지 않음이 표식 시험으로 단언된다.
5. 모델 고정(`MODELS["srccheck"]`, check_message), 대체 모델·advisor·베타 없음, 월 상한 확인이 Batch 생성 전에 있음, 하루 5건 상한, batch.json/checks.json 멱등.
6. usage 줄 10키·month_spend 읽힘, 키 값 미출력 시험·금지어 없음·ASCII 소스. 새 실패 0. 보고서 (a)~(e) 있음, 표지 문자열·URL 목록 없음.

```dev-run
{"task_id": "llm-srccheck", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 100, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_pilot_srccheck.py", "manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py", "docs/claude/llm-srccheck-report.md"], "target_tests": ["test_llm_pilot_srccheck*.py"], "commit_message": "feat(llm-pilot): daily Sonnet batch re-check of already verified official facts against their source URL with a one-URL web fetch, display only (llm-srccheck)"}
```

조언 기록: Fable 형식 점검 1번(medium) 8건 — 결론 바뀜 4(다음 날 수거·checks.md URL·주장 칸·SEC 주장에서 제출일 뺌·globenewswire 뺌) · 정정 4 · 미반영 0 (작업자 약 185k 토큰·200초).
