---
id: llm-iccheck-report
title: "API 시범 1 — 공통 모듈 + 기록 대조 검토자 Builder 보고 (llm-iccheck)"
date: 2026-11-07
prompt: docs/claude/llm-iccheck-builder-prompt.md
class: general (새 파일 6개만)
authority: "주문·수량 권한 표지 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음"
---

## (a) 만든 파일과 주요 함수

새 파일 6개(모두 LF), 다른 파일은 고치지 않았다.

- `manage-us-stock-strategy/requirements-llm.txt` — `anthropic==2.3.0` 한 줄.
- `manage-us-stock-strategy/scripts/llm_pilot_common.py`
  - 상수: `KEY_ENV` 18행, `MODELS` 20행, `BUDGET_USD_MONTH` 27행, `PRICES` 30행(Haiku 100K 초과 가격·캐시 배수·Batch 배수는 바로 아래), `KST`·`REPO_ROOT`
  - `load_key` 83행 — `INVESTV2_ANTHROPIC_API_KEY` 환경 변수만, 앞뒤 공백 제거, 빈 값은 None
  - `make_client` 91행 — `ANTHROPIC_*` 다섯 변수 지움 → 함수 안 `import anthropic` → `base_url="https://api.anthropic.com"`, `max_retries=1`, `timeout=120.0`
  - `api_error_label` 105행 — 클래스 이름 + (정수일 때) ` HTTP <번호>`, 예외 문장은 쓰지 않음
  - `ACCOUNT_KEEP` 115행 · `AMOUNT_KEYS` 126행 · `AMOUNT_TAG`·`COUNT_TAG` 152행 · `MASK_RULES` 155행(지시문 다섯 정규식 그대로, 그 순서로 적용 — 한글은 유니코드 이스케이프, 아래 수정 1회 참고)
  - `mask_text` 172행, `strip_amounts` 251행(실제 처리 `_clean` 210행, reconcile 첫 낱말 `_reconcile_word` 204행)
  - `number_lines` 264행, `quote_ok` 274행
  - `estimate_cost` 301행, `append_usage` 323행, `month_spend` 331행(읽을 수 없는 줄·숫자 아닌 비용·ts_kst 없음 → 예외)
  - `atomic_write_text` 357행, `FAILED_LINE` 366행, `write_failed` 369행, `response_text` 375행, `check_message` 383행
- `manage-us-stock-strategy/scripts/llm_pilot_iccheck.py`
  - `EXIT_CODES` 54행, `SYSTEM_PROMPT` 70행(지시문 글자 그대로 — 이스케이프로 적고 시험이 원문과 대조), `SCHEMA` 86행(지시문 구조 그대로)
  - 한글 사용자 글 상수 `DECISION_HEADER`·`RECORD_HEADER`·`ALERT_*` 128행, 실패 사유 `REASON_KO` 133행
  - `valid_day` 155행(YYYY-MM-DD만 — 경로 조작 막음), `build_request` 178행(결정 블록 앞, 기록 블록 뒤)
  - `parse_response` 215행(최상위 키·발견 키 4개·severity·인용 line int/text str·checked_lines 손 검사)
  - `run_detail` 291행(지시문 3절 1~14 순서), `run` 481행(`(exit_code, status)` 반환), `main` 490행(예상 못 한 예외 → failed.md + 종료 1, traceback 출력 없음)
- `manage-us-stock-strategy/tests/test_llm_pilot_common.py`, `manage-us-stock-strategy/tests/test_llm_pilot_iccheck.py`
- `docs/claude/llm-iccheck-report.md` (이 보고)

지시문이 정하지 않아 Builder가 고른 것(모두 닫힌 쪽):
- `reconcile` 문자열 줄이기와 holdings 항목 줄이기는 account 안뿐 아니라 키 이름이 같으면 적용한다(reconcile은 어디서든, holdings는 account 아래). dict 키 문자열에도 가리기 다섯 규칙을 적용한다.
- `count_tokens` 예외는 API_ERROR(사유 = `api_error_label`), 그 응답의 `input_tokens`가 정수가 아니면 BAD_RESPONSE.
- `usage.jsonl`의 status는 응답을 받은 뒤 `check_message` 코드(문제 있으면) 또는 `RECEIVED`. 비용 단가는 요청 모델(`claude-sonnet-5-5`) 기준.
- `input_sha256.record`·미리보기 `record_sha256`은 보낸 기록 JSON 글(행 번호 붙이기 전)의 sha256, decisions는 파일 바이트의 sha256.
- review.json보다 alert.md를 먼저 쓴다(중간에 끊겨도 review.json 없는 상태로 남아 다음 실행이 다시 돈다). 발견이 0이면 남은 alert.md를 지운다.
- ALREADY_DONE 때 표준 출력의 findings·dropped는 기존 review.json에서 읽는다(못 읽으면 0).
- 이달 기준은 실행 시각(KST)의 달이다.

## (b) 시험 이름과 단언 요약

test_llm_pilot_common.py (16개)
- `test_escaped_korean_text_decodes_verbatim` — 스크립트 소스 ASCII, `[금액]`·`[수량]`·failed.md 줄 형식이 원문과 같음, 다섯 정규식을 풀면 지시문 정규식과 글자 그대로 같음, 바꿀 글 `\1 [수량]`, 달러·주·옛 값·보유·수량·잔고 글자 꼴이 실제로 가려짐
- `test_strip_amounts_removes_money_and_counts` — account 키 ⊆ 허용 목록, holdings 항목 ⊆ {code, weight, mult}, 숫자 금액 키 없음(usd 꼬리 포함), `$숫자`·`숫자주`·`숫자 달러/USD` 없음, 가짜 금액·수량 숫자 전부 없음, weight·mult·vsHwmPct·s7.e 남음, reconcile = 첫 낱말, status '잔고' 글은 코드 뒤 수량과 금액이 가려짐, 06:40·10/28·3.0%·3:1 남음, 원본 그대로, removed > 0
- `test_mask_text_decision_forms` — '…주 유지', '② …주 LOC $…', '옛 값 N', '키움 AAA N·BBB N', 달러·USD·shares·'보유 N' 꼴이 사라지고 n > 0, 06:40·10/28·3.0%·3:1·날짜는 남음
- `test_mask_text_leaves_plain_text` — 숫자 없는 글은 그대로, n = 0
- `test_number_lines` — 빈 행도 셈, `R1|` 꼴
- `test_quote_ok` — 정확히 같음·공백 차이·`R3|`·`D3|` 앞표시 True, 5자·다른 행·0행·범위 밖·bool 행 False
- `test_month_spend_filters_pilot_and_month` — 그 시범·그달만 합침, 파일 없으면 0, 줄 키 순서 = USAGE_KEYS
- `test_month_spend_raises_on_broken_line` / `test_month_spend_raises_on_missing_cost` — 예외
- `test_estimate_cost` — Sonnet 예시 값, Batch 절반, 캐시 읽기(Sonnet 0.1·Opus 0.05), 캐시 쓰기 1.25배, Haiku 100K 이하·초과 가격, 날짜 붙은 모델명·None 값 처리, 모르는 모델 예외
- `test_atomic_write_and_failed` — failed.md 한 줄 형식, .tmp 남지 않음, LF
- `test_load_key` — 공백 제거, 빈 값·없음 None
- `test_make_client_clears_sdk_env_and_pins_base_url` — 다섯 변수 지워짐, 가짜 Anthropic이 지정 인자로 한 번 불림, 시험 뒤 sys.modules 복원
- `test_api_error_label_hides_message` — 결과는 클래스 이름 + HTTP 번호뿐, 가짜 키·문장 없음
- `test_check_message` — 날짜 붙은 같은 모델 허용, 다른 모델·잘린 날짜 MODEL_MISMATCH, REFUSAL, MAX_TOKENS, BAD_STOP
- `test_response_text_skips_thinking` — 사고 블록 건너뛰고 text 블록만 이어 붙임

test_llm_pilot_iccheck.py (19개, 모두 끝에 (카) `assert_no_key_anywhere`: 임시 루트 모든 파일·stdout·stderr에 가짜 키 없음)
- (가) `test_no_record` — 3, failed.md 한 줄, client_factory 안 불림
- `test_bad_record_and_missing_decisions` — 깨진 기록 9, 결정 색인 없음 9, 클라이언트 안 만듦
- (나) `test_no_key` — 4, client_factory 안 불림
- (다) `test_budget_spent` — 이달 사용액 = 상한 → 5, factory·count_tokens 안 불림(지난달 기록은 안 셈)
- `test_budget_unreadable_usage` — 깨진 usage.jsonl → 5
- `test_budget_worst_case_estimate` — 두 번째 예산 검사(사용액 + 입력 × 입력가 + 16,000 × 출력가 > 상한) → 5, stream 안 불림
- (라) `test_too_large` — count_tokens 150,001 → 6, stream 안 불림, usage 없음
- (마) `test_ok_path` — 0·OK, 발견 1·버림 2, alert.md 있음, 이전 failed.md 지워짐, usage 1줄(cost > 0, batch false), count_tokens가 stream보다 먼저, 요청 인자 키 = model·max_tokens·system·messages·output_config뿐, 모델 `claude-sonnet-5-5`, max_tokens 16000, system = SYSTEM_PROMPT, output_config = format(json_schema, SCHEMA) + effort medium, 어디에도 thinking·cache_control·fallbacks·temperature·top_p·tools·tool_choice·betas 없음, 결정 블록이 앞, 기록 블록에 가짜 금액·수량 없음
- (마-2) `test_amount_forms_never_sent` — count_tokens·stream에 보낸 글 전체(기록·결정 둘 다)에 가짜 수량·지정가·주문 가능 금액 숫자 없음, 결정 블록에 '옛 값 [수량]'·'키움 AAA [수량]·BBB [수량]'·'LOC [금액]', 기록 블록 reconcile = 첫 낱말
- `test_findings_capped_at_ten` — 12개 중 10개만, 버림 2
- `test_no_findings_writes_no_alert` — 발견 0이면 review.json만, alert.md 없음
- (바) `test_model_mismatch` — `claude-sonnet-5` → 8, review.json 없음, usage 1줄, failed.md에 MODEL_MISMATCH
- (사) `test_refusal_max_tokens_and_bad_shape` — refusal 8, max_tokens 8, 여분 최상위 키·JSON 아님·잘못된 severity·문자열 line → 8 '응답 형식 다름', 매번 usage 1줄씩 늘어남
- (아) `test_second_run_already_done` — 0·ALREADY_DONE, factory·클라이언트 호출 없음
- (자) `test_dry_run` — 키 없이 0·DRY_RUN, factory 안 불림, request-preview.json 키 = 지시문 10개, 본문(결정 글·기록 글·시스템 글) 없음, usage 없음
- (차) `test_api_error_hides_message_and_key` — stream이 status_code 529 + 가짜 키 든 문장 예외 → 7, failed.md에 클래스 이름과 529만, 키·문장 없음, usage 없음
- `test_main_prints_ascii_line` — 표준 출력 한 줄 `llm-iccheck 2026-11-06 OK findings=1 dropped=2`, ASCII
- `test_main_unexpected_error` — 예상 못 한 예외 → 1, failed.md "예상 못 한 오류 (RuntimeError)", stderr 비어 있음, traceback 없음
- `test_day_must_be_iso_date` — 경로 조작 날짜는 ValueError, 출력 폴더 안 생김

test_llm_pilot_iccheck.py `EscapedTextTests` (4개, 수정 1회에서 추가)
- `test_script_source_is_ascii` — 스크립트 소스 ASCII
- `test_system_prompt_verbatim` — 풀린 SYSTEM_PROMPT = 지시문 6절 글자 그대로
- `test_block_headers_and_alert_text` — 결정·기록 블록 머리글, 심각도 한글, alert.md 제목·항목·끝 줄이 원문과 같음
- `test_failure_reasons_verbatim` — failed.md 사유 15개가 지시문·원래 글과 같음

## (c) 시험 결과 마지막 3줄

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot*.py"`

```
Ran 39 tests in 0.240s

OK
```

(첫 실행은 시험이 스크립트 모듈의 `KEY_ENV`를 찾지 못해 오류 23건이었고, 스크립트가 공통 모듈의 `KEY_ENV`를 가져오게 고친 뒤 34개 통과였다. 스크립트를 저장소에 대고 실행하지 않았고 `--dry-run`도 돌리지 않았다.)

### 수정 1회 (fix-1)

- 원인: 파이프라인 전체 시험에서 새 실패 2건 — `test_language_contract.test_python_core_is_ascii_only`, `test_v2_5_beginner_renderer.test_v25_ui_07_core_python_ascii`. 둘 다 `manage-us-stock-strategy/scripts/*.py`가 ASCII만 담아야 한다고 단언하는데, 새 스크립트 두 개에 한글 글자(시스템 지시문·실패 사유·가리기 꼬리표·정규식)가 그대로 있었다.
- 고침: 두 스크립트의 한글을 모두 유니코드 이스케이프로 바꿨다(동작·보내는 글은 그대로). 정규식은 raw 문자열 안 `\uXXXX`(re가 풀어 읽음)이고, 바꿀 글 `\1 [수량]`은 일반 문자열로 옮겼다(re 바꿀 글은 `\u`를 받지 않음). 흩어진 한글 글은 상수(`DECISION_HEADER`·`RECORD_HEADER`·`ALERT_*`·`REASON_KO`·`FAILED_LINE`·`AMOUNT_TAG`·`COUNT_TAG`)로 모았다.
- 원문 대조 시험 5개를 더했다(위 (b)). 기존 단언은 바꾸거나 지우지 않았다.
- 확인: 위 대상 시험 39개 통과, `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_language_contract.py"` 2개 통과, `-p "test_v2_5_beginner_renderer.py"` 43개 통과.

## (d) 사장님 첫 실행용 (새 PowerShell 창, 저장소 폴더에서)

```
pip install -r manage-us-stock-strategy\requirements-llm.txt
python manage-us-stock-strategy\scripts\llm_pilot_iccheck.py --day YYYY-MM-DD
```

- `YYYY-MM-DD`에는 연구 기록이 있는 가장 최근 날짜를 넣는다(연구 기록은 KST 화~토에만 생긴다). 기록 없음 검사가 키 검사보다 앞이라, 빈 날이면 키를 보지 않고 종료 코드 3(NO_RECORD)으로 끝난다.
- 키는 환경 변수 `INVESTV2_ANTHROPIC_API_KEY`에서만 읽는다.
- 성공 때 출력 줄 형식: `llm-iccheck <날짜> OK findings=<남은 발견 수> dropped=<버린 발견 수>`
- 다른 결과: `NO_RECORD`(3) · `NO_KEY`(4) · `BUDGET_STOP`(5) · `TOO_LARGE`(6) · `API_ERROR`(7) · `BAD_RESPONSE`(8) · `BAD_INPUT`(9) · `UNEXPECTED`(1). 실패 사유는 `workspace\outputs\llm\iccheck\<날짜>\failed.md` 한 줄.
- 결과 파일: 같은 폴더의 `review.json`(발견이 있으면 `alert.md`도), 사용량은 `workspace\outputs\llm\usage.jsonl`. 표시 전용 그림자 — 다른 작업은 읽지 않는다.

주문·권한 표지 없음. 수량·금액·키 값은 이 보고에 적지 않았다.
