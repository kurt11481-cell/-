---
id: llm-srccheck-report
title: "API 시범 4 — 출처 확인 자동화(llm-srccheck) Builder 보고"
date: 2026-11-25
prompt: docs/claude/llm-srccheck-builder-prompt.md
class: general
---

# llm-srccheck Builder 보고

권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·SEC 산출물·카드 쓰기 없음 · 켜기 파일 변경 없음 · 스크립트 실행은 시험(임시 폴더·가짜 클라이언트)뿐.

## (a) 만든 함수와 상수

파일 `manage-us-stock-strategy/scripts/llm_pilot_srccheck.py` (새 파일, LF, ASCII만 — 한글 상수는 `\uXXXX` 이스케이프).

상수
- `PILOT`·`MAX_TOKENS`(4096)·`EST_INPUT_TOKENS_PER_TARGET`(30,000)·`EST_OUTPUT_TOKENS_PER_TARGET`(4,096)·`DAILY_MAX`(5)·`SEC_LOOKBACK_DAYS`(2 = day-2~day)·`COLLECT_LOOKBACK_DAYS`(3 = day-3~day)·`QUOTE_MIN_CHARS`(6)·`EVIDENCE_JSON_CHARS`(200)·`EVIDENCE_MD_CHARS`(60) — 56~66행
- `EXIT_CODES` 71행 (SUBMITTED·PENDING·WAITING·CHECKED·DONE_ALREADY·NO_TARGETS·NO_BATCH·DRY_RUN = 0, UNEXPECTED = 1, NO_KEY = 4, BUDGET_STOP = 5, API_ERROR = 7 — pdfcmp와 같은 이름은 같은 값)
- `SEC_FORMS` 89행 · `ALLOWED_HOSTS` 94행(지시문 목록 15개 글자 그대로) · `SEC_PATH_PREFIX` 112행 · `SEC_DOC_URL` 113행(`SEC_HOST`에서 조립) · `BLOCKED_WORDS` 114행
- `WEB_FETCH_TYPE`(`web_fetch_20260209`)·`WEB_FETCH_RESULT_TYPE`·`WEB_FETCH_MAX_CONTENT_TOKENS`(20,000) 117~119행
- 판정 낱말 `VERDICTS` 131~135행 · `INSTRUCTION`(지시문 4의 판정 지침 글자 그대로) 143행 · 주장 틀 `TIMING_KO`·`CLAIM_*` 156~172행 · `REASON_KO` 174행 · `MD_HEAD`·`MD_TABLE_HEAD`·`MD_FOOTER` 183~191행

함수
- 대상: `split_url` 289 · `url_reason` 300 · `url_allowed` 324 · `url_host` 328 · `sec_document_url` 332 · `claim_text` 348 · `_research_targets` 372 · `_sec_targets` 427 · `read_seen` 490 · `collect_targets` 507
- 제출: `estimate_submit_cost` 532 · `web_fetch_tool` 541 · `request_text` 552 · `build_request` 556 · `run_submit` 579
- 판정: `parse_answer` 676 · `citation_texts` 691 · `quote_overlaps` 703(pdfcmp와 같음) · `block_types` 712 · `fetch_check` 716 · `evaluate` 737
- 수거: `_usage_numbers` 787 · `_message_cost` 800 · `verdict_counts` 812 · `render_md` 822 · `_write_usage_once` 847(pdfcmp 709~731과 같은 규칙, 폴더마다 `usage-done`) · `collect_folder` 875 · `run_collect` 952
- `main` 999 (`--phase submit|collect`, `--day`, `--dry-run`; 출력 줄은 모두 ASCII, 마지막 줄 `llm-srccheck <day> <STATUS>`)

지시문 위에 더한 것(모두 대상을 빼는 쪽, fail-closed)
- URL 경로에 `..` 마디가 있으면 `BAD_URL`(SEC `primary_document`가 `..`일 때 등).
- 주장에 쓸 허용 칸이 비면 `MISSING_FIELDS`, SEC 칸 형식이 틀리면 `BAD_SEC_FIELDS`, 연구 기록·SEC 파일이 깨지면 `BROKEN_FILE`로 `skipped`에 적는다.
- `seen.jsonl` 줄이 깨졌으면 대상을 고르지 않고 UNEXPECTED(이미 보낸 URL을 모르고 다시 보내지 않게).
- 수거에서 여러 날 폴더를 처리할 때 종료 코드는 마지막 줄(그날 폴더, 없으면 가장 최근 폴더)의 상태를 따른다. 앞 날 폴더의 API_ERROR는 그 폴더 `failed.md`와 앞 줄 `llm-srccheck <그날> API_ERROR`로 남는다.

## (b) 시험 (`manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py`, 44건, 임시 폴더·가짜 클라이언트·가짜 키만)

대상
- `test_targets_default_order_fields_and_claims`(378) — 순서 official_facts → earnings → SEC 8-K → 10-Q, 주장 문장 4개 글자 대조, 허용 칸만 남음, NOT_ANNOUNCED 뺌, 슬래시 있는 primary_document는 `BAD_SEC_FIELDS`.
- `test_targets_verified_only_and_timing_optional`(393) — VERIFIED만, URL 없는 것 뺌, timing 없을 때 문장.
- `test_targets_url_rules_in_collection`(414) · `test_url_reason_table`(432) — 첫 화면(슬래시 유무)·허용 밖 호스트(globenewswire·data 서브도메인·접미 호스트·`@`·포트)·`rss`·`cgi-bin`·`efts`·`daily-index`·`browse-edgar`(대소문자 무시)·sec 문서 경로 밖·`?`·`#`·공백·http·`..` 를 이유와 함께 뺌.
- `test_sec_url_build`(470) — cik 앞 0 제거·접수번호 대시 제거, 틀린 cik·접수번호·문서 이름은 None.
- `test_targets_insider_forms_and_unverified_left_out`(485) — Form 4·144·미검증 뺌, `SEC_FORMS` 고정.
- `test_targets_seen_keys_left_out`(494) · `test_targets_broken_seen_fails_closed`(504) · `test_targets_same_key_once_a_day`(515).
- `test_targets_order_and_daily_max`(524) — 5건 상한, 8-K·8-K/A 먼저 그다음 filing_date 내림차순.
- `test_targets_broken_sec_file_skipped`(544) · `test_targets_sec_three_days_and_duplicates`(554, day-3 폴더 안 읽음·같은 접수번호 1번) · `test_targets_broken_or_missing_record`(562).

제출
- `test_submit_requests`(573) — params 키가 model·max_tokens·tools·messages뿐, 모델 `claude-sonnet-5-5`, tools 정확히 1개 `{web_fetch_20260209, max_uses 1, allowed_domains [그 호스트], max_content_tokens 20000, citations 켬}`, 메시지 = 지침 + URL + 주장, cache_control·betas·advisor·fallback·code_execution·system·thinking 없음, batch.json 항목·seen.jsonl 줄 수.
- `test_submit_sends_no_value_outside_the_allowed_fields`(610) — 가짜 연구 기록 권한 키·writer·integrated_check_run·earnings `checked_at`·fact의 다른 칸, 가짜 SEC `portfolio_context`·`deferred_symbols`·`ownership_coverage`·`root_theses`·`accepted_at`·submissions URL에 넣은 표식이 Batch 요청 전체 JSON에 없음, `filing_date` 값도 없음.
- `test_submit_idempotent`(621, PENDING·DONE_ALREADY·호출 0) · `test_submit_no_targets`(631, 클라이언트 생성 0·파일 0) · `test_submit_budget_stop`(638, 호출 0·지난달·다른 시범은 안 셈) · `test_submit_budget_unreadable`(657) · `test_submit_no_key`(664) · `test_submit_create_error_writes_nothing_but_failed`(670) · `test_submit_next_day_does_not_resend`(682) · `test_submit_dry_run`(689, 쓰기·호출 0, ASCII 줄).

수거
- `test_collect_all_match`(703) — CHECKED, checks.json 칸, checks.md 첫 줄·표 머리·행·바닥 줄, checks.jsonl 4줄, usage 4줄이 USAGE_KEYS 10개 순서 그대로·`month_spend`가 읽음, 두 번째 수거 DONE_ALREADY·줄 안 늘어남.
- `test_collect_verdict_reasons`(742) — URL_MISMATCH(같은 호스트 다른 경로) · FETCH_REFUSED(오류 코드 기록) · NO_FETCH_RESULT(block_types 기록) · NO_CITATION으로 낮춤(model_verdict 보존).
- `test_collect_parse_and_batch_failures`(760) — PARSE_FAIL · ERRORED · EXPIRED · 결과 없음, usage는 succeeded만.
- `test_collect_undecided_and_model_unverifiable`(773) — 미정, 모델 '확인 불가', pause_turn → BAD_STOP(stop_reason 기록), MAX_TOKENS, usage status.
- `test_collect_model_mismatch_usage_once`(789) — MODEL_MISMATCH도 usage 1줄(status MODEL_MISMATCH), usage-done 뒤 다시 수거해도 usage 줄 안 늘어남.
- `test_collect_waiting_and_no_batch_write_nothing`(807) · `test_collect_previous_day_waiting_is_collected_next_day`(820, 전날 WAITING 폴더를 다음 날 수거가 그날 폴더와 함께 받음, 앞 줄·마지막 줄) · `test_collect_last_line_falls_back_to_latest_processed_folder`(840) · `test_collect_window_is_three_days`(852) · `test_collect_api_errors`(859) · `test_collect_dry_run`(874).

기타
- `test_parse_answer`(884) · `test_quote_overlap_and_citations`(895) · `test_fetch_check_shapes`(905, 대소문자·끝 슬래시·두 번째 가져오기도 URL_MISMATCH, dict 모양도 읽음).
- `test_fake_key_never_written_or_printed`(922) — 가짜 키가 stdout·stderr·모든 출력 파일에 없음(API 오류 문구에 키를 넣어도).
- `test_main_lines_and_exit_codes`(936) — 모든 줄이 실행기 `_LINE_OK`·`_LINE_STATUS`에 맞고 `pick_line`·`status_of`가 CHECKED를 읽음. `test_main_unexpected`(948) · `test_exit_codes`(956).
- `test_korean_constants`(965) — 판정 지침·판정 낱말·표 머리·바닥 줄(pdfcmp와 같음)·REASON_KO·모델·월 상한·추정 비용 고정.
- `test_script_source_contract`(985) — ASCII, news 시험과 같은 금지어 + urlopen·httpx·aiohttp·count_tokens·cache_control·betas·code_execution 없음, `sec.gov` 글자는 허용 호스트 줄 하나뿐, `batches.create(` 1곳.
- `test_allowed_hosts_match_prompt`(998) — `ALLOWED_HOSTS`가 지시문 3의 목록(지시문 파일에서 읽음)과 글자 그대로 같음, 차단 낱말·SEC 경로 고정.

## (c) 시험 결과

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_srccheck*.py"`

```
Ran 44 tests in 0.379s

OK
```

`git diff --stat`: 출력 없음(바뀐 기존 파일 0). `git status --short`:

```
?? docs/claude/llm-srccheck-report.md
?? manage-us-stock-strategy/scripts/llm_pilot_srccheck.py
?? manage-us-stock-strategy/tests/test_llm_pilot_srccheck.py
```

전체 시험은 돌리지 않았다(파이프라인이 한다).

## (d) 병합 뒤 사장실이 할 일

- 켜기 카드 1번: `srccheck-submit`·`srccheck-collect` 두 줄을 한 번에 켠다(`docs/claude/llm-pilots-schedule.json`). 실행은 실행기 08:10 제출·10:10 수거.
- 켠 날부터 사장실 스레드가 10:30 KST 뒤 `workspace/outputs/llm/srccheck/<날짜>/checks.md` 표의 URL을 WebFetch로 열어 주장을 대조하고, 누적 `checks.jsonl`로 20건 일치율을 센다(60일 기한, 20건 ≥ 80%면 '통합점검 공식 사실 재확인 표시' 안을 따로 제안, 못 모이면 NO_CHANGE).
- 실행기 하루 기록을 읽는 예약이 없는 끊김은 지시문 연결표와 같다(이 작업 밖).

## (e) 확인 필요로 남은 것

- Batch 안에서 웹 가져오기 서버 도구가 되는지(설계 7절 3). 안 되면 결과가 errored이거나 `web_fetch_tool_result` 블록이 없어 모두 '확인 불가'로 남는다.
- `web_fetch_20260209` 동적 필터링 때 결과 블록 모양. 코드 실행 안에서 가져오면 `web_fetch_tool_result` 블록이 없을 수 있어 NO_FETCH_RESULT가 된다. 첫 실행의 `block_types`로 확인한다.
- sec.gov 문서를 Anthropic 가져오기가 여는지(원장 508행 '직접 열람 실패' 기록). 첫 2주 FETCH_REFUSED·'확인 불가' 비율로 본다. 거부된 URL은 seen에 남아 다시 보내지 않는다.
- 가져온 본문 토큰과 실제 하루 비용. 웹 가져오기는 별도 요금 없이 가져온 본문이 입력 토큰으로 잡힌다고 보고 따로 세지 않았다(`server_tool_use` 사용량 칸은 기록하지 않음).
- Batch·웹 가져오기 사용분이 크레딧에서 빠지는지(7절 1).
- 10:10에 안 끝난 Batch는 다음 날 수거가 받는다(하루 늦음, 앞 3일까지).
- `max_tokens` 4096 안에 Sonnet 5.5 생각 토큰이 드는지. MAX_TOKENS·BAD_STOP(pause_turn 포함) 건수와 `stop_reason`을 checks.json·usage status로 본다.
- count_tokens·cache_control을 쓰지 않은 이유: 가져온 본문 크기는 `max_content_tokens`가 막고, 공통 앞부분(지침)이 512토큰 미만이라 캐시가 걸리지 않는다(설계 3절 6).
- `www.globenewswire.com` 보도자료 URL은 설계 목록 밖이라 뺐다(`HOST_NOT_ALLOWED`). 넣을지는 사장실 판단.
- 실제 연구 기록·SEC 산출물의 모양은 이 Builder 세션에서 읽지 못했다(그 파일들이 worktree 밖 원본 저장소에만 있고, 그 경로 읽기 권한이 없었다). 대신 스키마 `manage-us-stock-strategy/schemas/auto-core-research-record.schema.json`·`sec-official-normalized-events.schema.json`으로 칸 이름과 모양을 확인했다. 첫 실행의 `--dry-run`(사장실 판단)이나 첫 `batch.json`으로 실제 대상이 잡히는지 확인한다.
