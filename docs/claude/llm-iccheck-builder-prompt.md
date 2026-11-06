---
id: llm-iccheck-builder-prompt
title: "API 시범 1 — 공통 모듈 + 기록 대조 검토자(그날 연구 기록 ↔ 결정 색인, 표시 전용) — llm-iccheck"
date: 2026-11-06
class: "general(새 파일만, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork가 dev-merge"
source: "사장 메시지 '세개 다 시범으로 도입'(2026-11-06 14:26:18 KST, 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9WN4WgxbUVKevZGmkb4k24L) + 사장 결정 카드 'A 추가 + B 규칙 개정 검토'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9W8YcsLciv5wVPk5mhWRuUT, 2026-11-06 14:41:48 KST, 계정=사장). 설계 docs/claude/api-pilots-2026-11-06.md 3절·4절 시범 1. 개발 큐 등록은 사장 등록 승인 뒤"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · API 키 값을 읽거나 출력하지 않음"
---

## 목표
- Claude API를 부르는 시범들이 같이 쓸 공통 모듈 `llm_pilot_common.py`와 시범 1 스크립트 `llm_pilot_iccheck.py`를 새로 만든다.
- 시범 1은 그날 06:40 통합점검이 쓴 연구 기록(`workspace/outputs/research-records/<KST 날짜>/research-record.json`)과 `docs/claude/active-decisions.md`를 Claude(`claude-sonnet-5-5`)에 보낸다. 그리고 기록이 결정 색인과 어긋나는 곳을 행 인용과 함께 받는다.
- 결과는 `workspace/outputs/llm/` 아래에만 쓴다. 어떤 기존 작업도 이 결과를 읽지 않는다(표시 전용 그림자). 코어 입력(CLAUDE.md 48~50행)은 바뀌지 않는다.
- 이 작업은 실행기·Windows 작업·일정 파일을 만들지 않는다(다음 작업 llm-runner).

## 바꿀 파일 (이 6개만, 모두 새 파일)
- manage-us-stock-strategy/scripts/llm_pilot_common.py
- manage-us-stock-strategy/scripts/llm_pilot_iccheck.py
- manage-us-stock-strategy/tests/test_llm_pilot_common.py
- manage-us-stock-strategy/tests/test_llm_pilot_iccheck.py
- manage-us-stock-strategy/requirements-llm.txt
- docs/claude/llm-iccheck-report.md (보고)

## 구현 요구 — requirements-llm.txt
- 한 줄만 쓴다: `anthropic==2.3.0`. requirements.txt·requirements-eval.txt는 고치지 않는다.

## 구현 요구 — llm_pilot_common.py
1. **상수**
   - `KEY_ENV = "INVESTV2_ANTHROPIC_API_KEY"`
   - `MODELS = {"iccheck": "claude-sonnet-5-5", "news": "claude-haiku-5-5", "pdfcmp": "claude-haiku-5-5", "srccheck": "claude-sonnet-5-5"}`
   - `BUDGET_USD_MONTH = {"iccheck": 10, "news": 5, "pdfcmp": 5, "srccheck": 6}`
   - 가격(달러/백만 토큰, 입력·출력): Sonnet 5.5 (2.00, 10.00), Opus 5.5 (4.00, 20.00), Haiku 5.5 (0.10, 0.50)이다. Haiku는 요청 입력이 100,000토큰을 넘으면 (0.50, 2.50)을 쓴다.
     - 캐시 쓰기는 입력값의 1.25배다. 캐시 읽기는 Sonnet·Haiku 0.1배, Opus 0.05배다. Batch는 전체 0.5배다.
   - `KST = timezone(timedelta(hours=9))`(KST는 서머타임이 없다).
   - `REPO_ROOT = Path(__file__).resolve().parents[2]`
   - 모든 경로 함수는 루트를 인자로 받는다. 시험은 임시 폴더를 넘긴다.
2. **키**
   - `load_key()`는 `os.environ.get(KEY_ENV)`의 앞뒤 공백을 뗀 값을 돌려준다. 비었으면 None이다. 다른 곳(파일·.env·레지스트리)은 읽지 않는다.
   - `make_client(key, timeout=120.0)`의 순서:
     1. `os.environ`에서 `ANTHROPIC_API_KEY`·`ANTHROPIC_AUTH_TOKEN`·`ANTHROPIC_BASE_URL`·`ANTHROPIC_CUSTOM_HEADERS`·`ANTHROPIC_PROFILE`을 지운다(있을 때만). SDK가 이 변수들도 읽어 키가 다른 주소로 가거나 헤더가 몰래 붙을 수 있기 때문이다.
     2. 함수 안에서 `import anthropic`을 한다(모듈 맨 위 import 금지 — 시험은 SDK 없이 돈다).
     3. `anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com", max_retries=1, timeout=timeout)`를 돌려준다.
   - 키 값은 어떤 print·파일·예외 문장·repr에도 들어가지 않게 한다.
   - `api_error_label(exc)`는 `type(exc).__name__`을 돌려준다. `status_code` 속성이 있으면 `" HTTP <번호>"`를 붙인다. `str(exc)`는 쓰지 않는다.
3. **금액·수량 지우기 `strip_amounts(obj) -> (clean, removed)`**
   - 원본은 고치지 않는다(깊은 복사). removed는 지운 키 수와 가린 문자열 조각 수의 합이다.
   - (가) 키 이름이 `account`인 dict는 아래 키만 남긴다: `vsHwmPct`, `firstCushionPct`, `approachPct`, `maxPct`, `n`, `reconcile`, `exposure`, `holdings`. `holdings`의 각 항목은 `code`, `weight`, `mult`만 남긴다.
     - 지금 실제 연구 기록의 account 키: total, hwm, vsHwmPct, kiwoomTotal, kiwoomDiff, cash, lines{max,first,approach}, firstCushionPct, firstCushionUsd, approachPct, maxPct, n, reconcile, holdings[{code,qty,close,value,weight,mult,contrib}], openOrders, exposure{n,nStatus,s7{session,fresh,e,band,newBuyPaused},capBreaches}.
   - (나) 어디서든 아래 키를 지운다. 조건은 키 이름을 소문자로 바꾸고 `_`를 뺀 값이 목록에 있거나 `usd`로 끝나는 것이고, 값이 숫자(bool 제외)이거나 숫자만 담은 dict·list일 때다. 문자열 값은 지우지 않고 (다)로 가린다.
     - 목록: qty, quantity, shares, value, marketvalue, cash, amount, total, totalassets, kiwoomtotal, kiwoomdiff, hwm, price, avgcost, cost, pnl, lines
   - (가-2) `reconcile` 문자열은 첫 `:` 앞 낱말(일치·불일치 등)만 남긴다. 지금 값에 보유 수량이 '주' 없이 들어 있다("일치: 키움 AAA N·BBB N = 상태 파일 · …").
   - (다) 모든 문자열에서 아래 다섯을 가린다. 같은 규칙을 `mask_text(text) -> (masked, n)`로도 내보내 결정 색인 글에도 쓴다(결정 색인에 보유·주문 수량과 지정가가 있다 — active-decisions.md 99·167·233행).
     - `\$\s?\d[\d,]*(?:\.\d+)?` → `[금액]`
     - `\d[\d,]*(?:\.\d+)?\s?(?:달러|USD)` → `[금액]`
     - `\d[\d,]*\s?(?:주|shares?)` → `[수량]`(‘3주 뒤’처럼 더 가려지는 것은 허용)
     - `\b([A-Z]{2,5})\s(\d[\d,]*)(?![\d:/%.])` → `\1 [수량]`(종목 코드 바로 뒤의 단위 없는 정수 — "AAA 12·BBB 3" 꼴. 시각 06:40·날짜 10/28·비율 3.0%·분할 3:1은 뒤 글자 때문에 가려지지 않는다)
     - `(옛 값|보유|수량|잔고)\s?(\d[\d,]*)(?![\d:/%.])` → `\1 [수량]`(결정 색인 99행 "… 옛 값 N" 꼴)
4. **`number_lines(text, prefix)`**: `text.splitlines()`의 각 행 앞에 `"<prefix><번호>|"`를 붙인다. 번호는 1부터, 빈 행도 센다.
5. **`quote_ok(lines, line_no, quote)`**(lines = 번호 붙이기 전 행 목록):
   - 인용 앞의 `R12|`·`D3|` 같은 표시는 떼어낸다.
   - 연속 공백을 하나로 줄이고 앞뒤 공백을 뗀 인용이 6자 이상이어야 한다.
   - 1 ≤ line_no ≤ len(lines)이고, 같은 방식으로 정규화한 `lines[line_no-1]`에 그 인용이 들어 있을 때만 True다.
6. **사용량·예산**
   - `usage.jsonl`은 `<루트>/workspace/outputs/llm/usage.jsonl`이다. 줄마다 JSON 하나를 덧붙이기만 한다.
     - 키: ts_kst, pilot, model, input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, batch, cost_usd_est, status
   - `month_spend(root, pilot, month)`는 그 시범·그달(`ts_kst[:7]`)의 cost_usd_est 합이다. 읽을 수 없는 줄이 하나라도 있으면 예외를 낸다(호출 쪽이 BUDGET_STOP으로 처리 — 실패는 닫힌 쪽).
   - `estimate_cost(model, usage, batch=False)`: usage의 `input_tokens`는 캐시 밖 입력이다. 캐시 쓰기·읽기 토큰은 따로 더한다.
7. **`atomic_write_text(path, text)`**: 부모 폴더를 만들고, 같은 폴더의 `<이름>.tmp`에 UTF-8·LF로 쓴 뒤 `os.replace`한다.
8. **`write_failed(day_dir, code, reason_ko)`**: `failed.md`에 한 줄 `검토 못 함: <reason_ko> (<code>)`을 원자적으로 쓴다.
9. **응답**
   - `response_text(message)`는 `type == "text"`인 블록의 text만 이어 붙인다(사고 블록이 앞에 올 수 있다).
   - `check_message(message, expected_model)`는 문제가 없으면 None, 있으면 코드를 돌려준다.
     - model이 expected와 같지 않고 `expected + "-" + 숫자 8자리`도 아니면 MODEL_MISMATCH
     - stop_reason이 refusal이면 REFUSAL, max_tokens면 MAX_TOKENS, end_turn이 아닌 다른 값이면 BAD_STOP

## 구현 요구 — llm_pilot_iccheck.py
1. **실행:** `python manage-us-stock-strategy/scripts/llm_pilot_iccheck.py [--day YYYY-MM-DD] [--dry-run]`. 기본 날짜는 오늘(KST)이다.
2. **함수:** `run(day, *, repo_root=REPO_ROOT, client_factory=None, dry_run=False, now=None) -> (exit_code, status)`. client_factory 기본값은 `make_client`다. 시험은 가짜를 넣는다.
3. **순서**(실패하면 그날 폴더 `workspace/outputs/llm/iccheck/<day>/failed.md` + 아래 종료 코드로 끝낸다. API 응답을 받은 경우에만 usage를 덧붙인다):
   1. 그날 폴더에 review.json이 있으면 호출하지 않고 0 · ALREADY_DONE으로 끝낸다.
   2. 연구 기록이 없으면 NO_RECORD "오늘 연구 기록 없음"이다. JSON으로 읽을 수 없으면 BAD_INPUT "연구 기록을 읽을 수 없음"이다.
   3. `docs/claude/active-decisions.md`가 없으면 BAD_INPUT "결정 색인 없음"이다.
   4. 자료를 만든다.
      - 기록: `strip_amounts` 뒤 `json.dumps(clean, ensure_ascii=False, indent=1, sort_keys=True)`의 행
      - 결정: 파일 글(UTF-8)에 `mask_text`를 적용한 뒤의 행. quote_ok도 이 가린 행으로 대조한다
   5. **요청**(이 값만 보낸다):
      - `model = MODELS["iccheck"]`, `max_tokens = 16000`
      - `system = SYSTEM_PROMPT`(아래 글자 그대로)
      - `messages = [{"role": "user", "content": [{"type": "text", "text": "결정 색인(D행)\n" + 결정 행}, {"type": "text", "text": "오늘 연구 기록(R행, 금액·수량 지움)\n" + 기록 행}]}]` — 결정을 앞에, 기록을 뒤에 둔다.
      - `output_config = {"format": {"type": "json_schema", "schema": SCHEMA}, "effort": "medium"}`
      - thinking·temperature·top_p·tools·tool_choice·fallbacks·cache_control·베타 헤더는 보내지 않는다(Sonnet 5.5는 thinking disabled가 400이고, 기본은 적응형 사고다).
   6. dry_run이면 `request-preview.json`만 쓰고 0 · DRY_RUN으로 끝낸다. 키를 읽지 않고 클라이언트도 만들지 않는다.
      - 내용: model, max_tokens, output_config, system_sha256, record_lines, decision_lines, record_sha256, decisions_sha256, removed_amount_items, masked_decision_items(본문은 넣지 않는다)
   7. `load_key()`가 None이면 NO_KEY "키 없음"이다.
   8. 이달 사용액이 상한 이상이거나 usage.jsonl을 읽을 수 없으면 BUDGET_STOP이다.
   9. 클라이언트를 만든다. `client.messages.count_tokens(model=, system=, messages=, output_config=)`의 `input_tokens`를 센다.
      - 150,000을 넘으면 TOO_LARGE다.
      - '이달 사용액 + 입력 × 입력가 + 16,000 × 출력가'가 상한을 넘으면 BUDGET_STOP이다.
   10. `with client.messages.stream(model=, max_tokens=, system=, messages=, output_config=) as s: msg = s.get_final_message()`. 예외는 API_ERROR이고, 사유는 `api_error_label`만 쓴다.
   11. usage를 한 줄 덧붙인다(응답 usage에서 없는 값은 0, batch false).
   12. `check_message`가 코드를 내면 BAD_RESPONSE(사유에 그 코드)다.
       - `response_text`를 JSON으로 읽고 손으로 검사한다: 최상위 키가 정확히 findings·checked_lines, 각 발견의 키 4개, severity 값, 인용의 line은 int이고 text는 str.
       - 어긋나면 BAD_RESPONSE "응답 형식 다름"이다.
   13. 발견은 앞에서 10개까지만 본다. 나머지는 버린 수에 더한다. record_quote·decision_quote가 둘 다 `quote_ok`인 발견만 남기고, 버린 수를 센다.
   14. review.json을 원자적으로 쓴다.
       - 키: `schema "llm-iccheck-review-1"`, day, generated_at_kst, model(응답 값), input_sha256{record(보낸 기록 글), decisions(파일 바이트)}, removed_amount_items, masked_decision_items, findings(남은 것), dropped_findings, checked_lines, usage, cost_usd_est, `display "none"`
       - 남은 발견이 있으면 alert.md(한국어 목록: 심각도 · 요약 · R행 인용 · D행 인용)도 쓴다.
       - 같은 날 failed.md가 남아 있으면 지운다. 0 · OK로 끝낸다.
4. **종료 코드:**
   - 0: OK·ALREADY_DONE·DRY_RUN
   - 3: NO_RECORD
   - 4: NO_KEY
   - 5: BUDGET_STOP
   - 6: TOO_LARGE
   - 7: API_ERROR
   - 8: BAD_RESPONSE
   - 9: BAD_INPUT
   - 1: 예상 못 한 예외. `main`이 잡아 failed.md "예상 못 한 오류 (<예외 이름>)"를 쓴다. traceback은 출력하지 않는다.
5. **표준 출력:** ASCII 한 줄 `llm-iccheck <day> <STATUS> findings=<n> dropped=<m>`.
6. **SYSTEM_PROMPT**(이 글자 그대로, 한 문자열):

```text
너는 투자 운영 기록의 독립 검토자다. 사용자 메시지에 두 자료가 있다.
- 결정 색인: 행마다 "D<번호>|"가 붙어 있다. 지금 효력이 있는 결정과 조건·만료가 적혀 있다.
- 오늘 연구 기록: 행마다 "R<번호>|"가 붙어 있다. 아침 통합점검이 쓴 JSON이다. 금액·수량은 지워져 [금액]·[수량]으로 보이며, 이것은 오류가 아니다.

할 일: 오늘 연구 기록이 결정 색인의 현재 결정과 어긋나는 곳을 찾는다. 예: 폐지되거나 대체된 기준을 아직 쓰는 문장, 결정과 다른 비율·기한·조건, 만료가 지난 결정을 살아 있는 것처럼 쓰는 곳, 날짜·세션이 서로 맞지 않는 곳.

규칙:
1. 발견마다 R행 하나와 D행 하나를 인용한다. line에는 행 번호만 쓰고, text에는 그 행의 글자를 6자 이상 그대로 옮긴다. 고쳐 쓰거나 줄이지 않는다.
2. 두 자료에 적힌 것만 근거로 한다. 추측, 일반론, 시장 전망, 매매 권고는 쓰지 않는다.
3. 발견은 중요한 것부터 최대 10개다. 어긋난 곳이 없으면 findings를 빈 목록으로 낸다.
4. summary_ko는 한국어 한두 문장으로, 무엇이 어떻게 다른지 쓴다.
5. severity: high = 오늘 지시나 보유 판단이 결정과 반대로 읽힐 수 있음, mid = 날짜·만료·조건·비율이 어긋남, low = 표기·설명만 다름.
6. checked_lines에는 읽은 R행 수와 D행 수를 적는다.
```

7. **SCHEMA**(이 구조 그대로. 구조화 출력은 maxItems·minLength 같은 제약을 받지 않으므로 넣지 않는다):

```json
{"type": "object", "additionalProperties": false, "required": ["findings", "checked_lines"],
 "properties": {
  "findings": {"type": "array", "items": {"type": "object", "additionalProperties": false,
    "required": ["summary_ko", "record_quote", "decision_quote", "severity"],
    "properties": {
      "summary_ko": {"type": "string"},
      "record_quote": {"type": "object", "additionalProperties": false, "required": ["line", "text"],
                       "properties": {"line": {"type": "integer"}, "text": {"type": "string"}}},
      "decision_quote": {"type": "object", "additionalProperties": false, "required": ["line", "text"],
                         "properties": {"line": {"type": "integer"}, "text": {"type": "string"}}},
      "severity": {"type": "string", "enum": ["high", "mid", "low"]}}}},
  "checked_lines": {"type": "object", "additionalProperties": false, "required": ["record", "decisions"],
                    "properties": {"record": {"type": "integer"}, "decisions": {"type": "integer"}}}}}
```

## 시험 (test_llm_pilot_common.py · test_llm_pilot_iccheck.py)
- 모든 시험은 임시 폴더를 루트로 쓴다. 가짜 키(예: `fake-key-FOR-TEST-7Q9Z`)와 가짜 클라이언트만 쓴다. 네트워크와 SDK가 없어도 돈다.
- 가짜 연구 기록은 위 account 키 구조를 따른다. 금액·수량 자리에는 다른 곳에 없는 숫자(예: 987654.32, 4321)를 넣어 "보낸 글에 없음"을 단언할 수 있게 한다. 실제 꼴도 넣는다: reconcile = "일치: 키움 AAA 4321·BBB 8765 = 상태 파일 · 주문 가능 $98765.43 · 미체결 없음", status 목록의 '잔고' value = 같은 꼴. 권한 관련 키는 넣지 않는다(검토 대상이 아님).
- 기존 시험 import 방식(`test_llm_decision_stability.py` 7~14행처럼 `spec_from_file_location`)을 따른다.
- **공통 모듈:**
  1. strip_amounts: account에 남는 키 ⊆ 허용 목록, holdings 항목 키 ⊆ {code, weight, mult}, 숫자 금액 키 없음, `$숫자`·`숫자주`·`숫자 달러` 없음, weight·mult·%값 남음, 원본 그대로, removed > 0. mask_text: "AAA 4321주 유지 · AAA ② 4321주 LOC $98.76", "상태 파일은 … 옛 값 4321", "키움 AAA 4321·BBB 8765" 같은 결정 글에서 4321·8765·98.76이 사라지고 n > 0. 같은 글의 "06:40", "10/28", "3.0%", "3:1"은 남는다. reconcile은 첫 낱말만 남는다.
  2. quote_ok: 정확히 같음 True, 공백 차이 True, `R3|` 앞표시 True, 5자 False, 다른 행 False, 범위 밖 행 False.
  3. month_spend: 그 시범·그달만 합침, 깨진 줄이면 예외.
  4. estimate_cost: Sonnet 예시 값, Batch 절반, 캐시 읽기 배수(Sonnet 0.1·Opus 0.05), Haiku 100K 초과 가격.
  5. make_client: 시험 전에 `ANTHROPIC_*` 다섯 변수를 넣고, `sys.modules["anthropic"]`에 가짜 모듈을 넣는다. 부른 뒤 다섯 변수가 없고, 가짜 Anthropic이 api_key·base_url="https://api.anthropic.com"·max_retries=1·timeout=120.0으로 불렸음을 단언한다(시험 뒤 환경·sys.modules 복원).
  6. check_message: 날짜 붙은 같은 모델 허용, 다른 모델 MODEL_MISMATCH, refusal, max_tokens.
  7. api_error_label: 예외 문장(가짜 키 포함)이 결과에 없고 클래스 이름과 HTTP 번호만 있음.
- **시범 1:**
  - (가) 기록 없음 → 3, failed.md 한 줄, client_factory 안 불림.
  - (나) 키 없음 → 4, client_factory 안 불림.
  - (다) 이달 iccheck 사용액이 상한 이상(usage.jsonl에 미리 기록) → 5, count_tokens 안 불림.
  - (라) count_tokens 150,001 → 6, stream 안 불림.
  - (마) 정상: 가짜 응답 발견 3개(둘 다 맞는 인용 1, 기록 인용이 그 행에 없는 것 1, 5자 인용 1) → 0 · OK.
    - review.json에 발견 1·dropped_findings 2, alert.md 있음, usage.jsonl 1줄(cost_usd_est > 0).
    - 보낸 요청: model `claude-sonnet-5-5`, output_config에 format(json_schema)·effort medium, 요청 인자 어디에도 thinking·cache_control·fallbacks 없음, 결정 블록이 기록 블록보다 앞.
    - 보낸 기록 글에 가짜 금액·수량 숫자 없음.
  - (마-2) 가짜 결정 색인에 `4321주`·`$98.76`·"옛 값 4321"·"키움 AAA 4321·BBB 8765"를, 가짜 기록의 reconcile·잔고 value에 같은 꼴을 넣고, stream에 보낸 글 어디에도 4321·8765·98.76·98765.43이 없음을 단언한다.
  - (바) 응답 model `claude-sonnet-5` → 8, review.json 없음, usage는 1줄 남음.
  - (사) refusal → 8, max_tokens → 8.
  - (아) 두 번째 실행 → 0 · ALREADY_DONE, 가짜 클라이언트 호출 없음.
  - (자) dry_run → 0, request-preview.json 있음, 키 없이 돎, client_factory 안 불림, 미리보기에 본문 없음.
  - (차) stream이 `status_code=529`이고 문장에 가짜 키가 든 예외를 냄 → 7. failed.md에 클래스 이름과 529는 있고, 키·문장은 없음.
  - (카) (가)~(차) 모두에서 임시 루트 아래 모든 파일과 잡아 둔 stdout·stderr에 가짜 키 문자열이 없다.
- skip은 넣지 않는다. 다른 시험 파일은 바꾸지 않는다.
- **실행 명령은 이 한 줄만, 글자 그대로 쓴다:** `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot*.py"`
  - 앞에 환경 변수나 옵션을 붙이지 않는다. 전체 스위트는 파이프라인이 한다.
  - git은 status·diff·log만 쓴다. `python -c`·PowerShell·파이프·pip는 쓰지 않는다.
  - 스크립트를 저장소에 대고 실행하지 않는다(--dry-run 포함). 실행하면 허용 밖 경로(workspace/outputs/llm/)가 생긴다.

## 지켜야 할 것
1. 위 6개 파일 밖은 손대지 않는다. 새 파일은 LF로 쓴다.
2. 기존 `run_llm_decision_stability.py`(다른 공급자 하네스)·requirements.txt·requirements-eval.txt를 고치지 않는다.
3. 키 값을 읽으려 하지 않는다. 환경 변수 이름만 코드에 쓰고, 시험은 가짜 키만 쓴다. 비밀(.env*·토큰·계좌번호) 파일을 열지 않는다.
4. 결과를 연구 기록·원장·카드·결정 문서·대시보드·코어 입력에 쓰지 않는다. 출력 폴더는 `workspace/outputs/llm/`뿐이다.
5. 주문·키움·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
6. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/llm-iccheck-report.md
- (a) 만든 파일과 주요 함수(파일:행)
- (b) 시험 이름과 각 단언 요약
- (c) 시험 결과 마지막 3줄
- (d) 사장님 첫 실행용 두 줄(새 PowerShell 창, 저장소 폴더에서):
  - `pip install -r manage-us-stock-strategy\requirements-llm.txt`
  - `python manage-us-stock-strategy\scripts\llm_pilot_iccheck.py --day YYYY-MM-DD`(연구 기록은 KST 화~토에만 생긴다. 키 확인이 목적이므로 기록이 있는 가장 최근 날짜를 넣는다 — 기록 없음 검사가 키 검사보다 앞이라 빈 날이면 키를 보지 않고 3으로 끝난다)
  - 성공 때 나올 출력 줄 형식

수량·금액·키 값은 적지 않는다. 주문·권한 표지 문자열도 적지 않고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 허용 파일 6개뿐이고 모두 새 파일이다.
2. 키:
   - KEY_ENV 환경 변수에서만 읽는다.
   - 출력·파일·예외 문장에 쓰이지 않는다.
   - 클라이언트 전에 `ANTHROPIC_*` 다섯 변수를 지우고 base_url을 공식 주소로 고정한다.
   - 시험이 가짜 키가 어디에도 없음을 단언한다.
3. 요청:
   - 모델 `claude-sonnet-5-5`
   - thinking·fallbacks·cache_control·베타·tools 없음
   - output_config = format(json_schema) + effort medium
   - 결정이 앞, 기록이 뒤
   - count_tokens가 호출보다 먼저, 150,000 상한, 예산 검사가 두 번(호출 전 사용액 · 추정 최대 비용)
4. 금액 지우기: account 허용 목록 + reconcile 첫 낱말 + 숫자 금액 키 + 문자열 가리기 다섯 규칙, 결정 색인 글에도 mask_text. 시험이 실제 꼴(코드 뒤 단위 없는 수량, '옛 값 N')을 포함한 가짜 금액·수량이 보낸 글(기록·결정 둘 다)에 없음을 보인다.
5. 인용 확인: 그 행에서 6자 이상 글자 그대로만 남고, 버린 수를 센다.
6. 쓰기는 `workspace/outputs/llm/` 아래 원자적 쓰기뿐이다. 다른 저장소 경로를 쓰지 않는다. 기존 코드는 이 출력을 읽지 않는다.
7. 시험이 실제로 각 경로를 만든다(항상 참 단언 아님). skip·네트워크 없음. 기존 시험 변경 없음.
8. 새 실패 0(파이프라인 checks).
9. 보고서 (a)~(d) 있음. 수량·금액·키 값·표지 없음.

```dev-run
{"task_id": "llm-iccheck", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 150, "builder_timeout_min": 90, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_pilot_common.py", "manage-us-stock-strategy/scripts/llm_pilot_iccheck.py", "manage-us-stock-strategy/tests/test_llm_pilot_common.py", "manage-us-stock-strategy/tests/test_llm_pilot_iccheck.py", "manage-us-stock-strategy/requirements-llm.txt", "docs/claude/llm-iccheck-report.md"], "target_tests": ["test_llm_pilot*.py"], "commit_message": "feat(llm-pilot): shared Claude API pilot module and daily record-vs-decisions reviewer (llm-iccheck, shadow only)"}
```
