# llm-news2 Builder 보고 — API 시범 2 뉴스 요약 + 이름 지운 그림자 점수 (2026-11-18)
재시도: llm-news2 — 앞 작업 llm-news의 G9 연결표 FAIL(지시문 쪽) 고침

- 지시문: `docs/claude/llm-news2-builder-prompt.md` (base 8b1cace). 앞 worktree는 쓰지 않고 처음부터 새로 만들었다.
- 만든 파일 3개(모두 새 파일, LF): `manage-us-stock-strategy/scripts/llm_pilot_news.py`, `manage-us-stock-strategy/tests/test_llm_pilot_news.py`, 이 보고.
- 사전 등록 두 파일·켜기 파일·공통 모듈·iccheck·실행기와 그 시험은 고치지 않았다. 시범은 켜지 않았다. 커밋 없음.
- 권한: 주문·키움·일지·원장·정책·상태와 무관. 주문·권한 표지 없음.

## (a) 만든 파일과 주요 함수

`manage-us-stock-strategy/scripts/llm_pilot_news.py` (ASCII만, 한글은 `\U` 이스케이프)
- 상수: `PREREG_SHA256`·`LABEL_PROMPT_SHA256` 56~57행(지시문에서 그대로 옮김), `EXIT_CODES` 69행, 한국어 상수 `SUMMARY_SYSTEM` 96행·`DIGEST_TITLE`·`DIGEST_FOOTER`·`REASON_KO`.
- `load_prereg` 212행: 파일 없음·JSON 아님·정규 해시 다름·지시문 해시 다름·`model.id`가 `MODELS["news"]`와 다름 → `(None, "PREREG_MISMATCH")`.
- 이름 지우기: `_ticker_form_patterns` 238행(거래소 표기·괄호·`$`·`.O`), `_mask_rules` 254행(기호 꼴 → 별칭 긴 것부터 → 3글자 이상 홀로 선 기호), `mask_item_text` 287행(URL 삭제 후 규칙 적용).
- 기사: `default_fetcher` 297행(함수 안에서 yfinance import), `fetch_items` 303행(예외·목록 아님 → None), `normalize_item` 343행(납작한 꼴·안에 든 꼴), `read_seen` 373행·`write_seen` 383행.
- 제출 `run_submit` 391행: 1 HALT 408 · 2 한 번만 412 · 3 사전 등록 420 · 4 키 427~433 · **5 예산 436~442** · 6 가져오기 444 · 7 고르기 456 · 가린 뒤 재검사 477 · 9 dry run 495 · 8 0건 499 · 11 submit-started → create 한 번 509 · 12 batch.json·seen·머리줄 528.
- `build_requests` 567행(L/S 요청 쌍), `ensure_records_header` 603행, `read_records` 613행(사슬 전체 검사), `parse_label` 647행(사전 등록 `label_schema` enum), `_usage_numbers` 661행, `_is_not_found` 677행, `render_digest` 687행.
- 수거 `_collect_day` 707행: 3 사전 등록 738 · 5 retrieve 751 · 6 results 760 · 6-1 사용량 767 · 7 분류 799 · 8 사슬 검사 뒤 덧붙이기 850 · 10 digest 883 · 11 collected 886. `run_collect` 913행(0 밀린 수거 930). `main` 953행.

`manage-us-stock-strategy/tests/test_llm_pilot_news.py` — 50개 시험(아래 (b)).

## (b) 시험과 단언 요약 (지시문 시험 번호)

| 번호 | 시험 | 단언 |
|---|---|---|
| 1 | `test_prereg_pinned_by_repo_json` | 저장소 JSON 정규 해시 = `PREREG_SHA256`, 지시문 해시 = `LABEL_PROMPT_SHA256`, universe 30, `load_prereg` 성공, model.id = `MODELS["news"]` |
| 1 | `test_prereg_one_char_changed_halts` · `test_prompt_hash_mismatch_also_halts` | 한 글자 바꾼 복사본 → `PREREG_MISMATCH`(10) + HALT + failed.md, fetcher·client·create 안 불림, 그 뒤 `HALTED` · 지시문 변경·JSON 깨짐·파일 없음도 불일치 |
| 2 | `test_mask_other_and_target` · `test_mask_mu_forms` · `test_mask_be_on_arm` · `test_mask_url_and_standalone` · `test_mask_is_stable_on_second_pass` | 'Nvidia invests in Nebius'(NBIS) → '[OTHER] invests in [COMPANY]' · MU 꼴 8개 모두 [COMPANY], 'MU'·'Micron' 안 남음, 'micron-scale' 그대로, 홀로 선 'MU' 그대로 · BE·ON·ARM 낱말 그대로, 별칭·기호 꼴은 [COMPANY] · URL 삭제, AMD 대상 'NVDA' → [OTHER] · 두 번 가려도 같음 |
| 4 | `test_normalize_both_forms` · `test_fetch_items_failure_is_none` | 두 yfinance 꼴 정규화, 시각 못 읽음·시간대 없음·id 빔·제목 빔 → None · fetcher 예외·None → None |
| 3 | `test_request_shape` | 요청 4개 L0001·S0001·L0002·S0002, create 1번, 키는 factory에만, model·max_tokens(사전 등록)·effort low, 금지 키 없음, 점수 요청 system·schema = 사전 등록, 점수 글에 기호·별칭·URL 없음, 요약 요청은 이름 그대로·format 없음 |
| 4 | `test_pick_rules` · `test_mask_leak_is_not_sent` | seen 안 보냄 · 25시간 전·미래 발행은 seen에만 · 빈 제목·시각 못 읽음 skipped 2 · 같은 id 두 종목 → 먼저 나온 MU 한 번 · 요약 없음 → 빈 글 · 제목 301 → 300 · 홀로 선 'MU' 기사 보냄 · 가짜로 한 번 덜 가린 기사 → mask_leak 1, 안 보냄 |
| 5 | `test_submit_once` · `test_started_only_is_unknown` · `test_create_error_never_resends` · `test_create_404_halts` | 두 번째 `ALREADY_DONE`, create 1번 · submit-started만 → `SUBMIT_UNKNOWN`(12), client·fetcher 안 불림 · create 예외 → `API_ERROR`(7), failed.md에 클래스·코드만, 재실행 `SUBMIT_UNKNOWN`·create 그대로 1번 · 404 → `MODEL_NOT_FOUND` + HALT, 다음 날 `HALTED` |
| 6 | `test_no_items_and_nothing_to_collect` · `test_all_fetches_failed` · `test_some_fetches_failed_are_counted` | 새 기사 없음 → `NO_ITEMS`, batch.json 모양, seen 씀, 머리줄 없음, collect → `NOTHING_TO_COLLECT` · 30종목 실패 → `FETCH_FAILED`(11) · 일부 실패는 세기만 |
| 7 | `test_budget_stop` · `test_budget_unreadable_stops` · `test_no_key` · `test_halt_marker` | 그 달 news 합 ≥ 한도 → `BUDGET_STOP`(다른 시범·다른 달 무시) · usage 깨짐 → `BUDGET_STOP` · 키 없음 → `NO_KEY` 문장 · HALT → `HALTED`, fetcher 안 불림, 폴더 안 생김 |
| 8 | `test_collect_ok` | 제출 직후 머리줄 1줄(start_day = 제출일) · 수거 뒤 3줄, 키가 `record.fields` 순서까지 같음, 사슬 이어짐 · digest에 제목·요약·footer, good/bad/unknown/label/reason 없음 · collected.json · usage 1줄(`ts_kst`, batch true, `USAGE_KEYS` 순서), 입력 합 240,000 토큰 가짜 usage로 비용 = 건별 `estimate_cost` 합(합친 계산과 다름), `month_spend`가 읽음 |
| 9 | `test_pending_then_ok_then_done` | in_progress → `PENDING`, 파일 변화 없음, results 안 부름 → ended → OK → 다시 `ALREADY_DONE`, 줄 수 그대로 |
| 10 | `test_late_receipt_is_kept` | 23:40 수거 → 줄이 덧붙고 received_at = 23:40 |
| 11 | `test_two_days_and_late_collection` | 첫날 PENDING 두 번 → 둘째 날 collect가 첫날 먼저(`late=1`), 머리줄 하나·start_day 첫날·사슬 이어짐, 첫날 received_at = 둘째 날 22:00, 4일 전 폴더 바이트 그대로·retrieve 안 됨 |
| 12 | `test_broken_chain_halts` · `test_missing_record_file_is_broken` | 가운데 줄 한 글자 변경 → `RECORDS_BROKEN` + HALT, 파일 바이트 그대로 · 파일 없음도 `RECORDS_BROKEN` |
| 13 | `test_model_mismatch_halts_but_usage_is_kept` · `test_errored_not_found_halts` · `test_dated_model_passes` | `claude-haiku-5-5-latest` → `MODEL_MISMATCH` + HALT, records 그대로, usage 1줄 남음, 다음 submit `HALTED` · errored `not_found_error` → `MODEL_NOT_FOUND` + HALT · `claude-haiku-5-5-20261001` 통과·기록 |
| 14 | `test_item_failures_are_dropped_and_counted` · `test_missing_result_counts_as_error` | errored 1·"maybe" 1·refusal 1 → labels 1, errors 1, dropped 2, reason 500 → 200 · 결과 빠짐은 errors |
| 15 | `test_rerun_after_lost_marker` | collected.json 지우고 다시 → records 바이트 그대로, usage 줄 그대로 |
| 15-1 | `test_collect_no_batch` · `test_collect_no_key` · `test_collect_prereg_sha_differs` · `test_collect_retrieve_error` | `NO_BATCH`(failed.md 없음) · `NO_KEY` · prereg_sha256 다름 → `PREREG_MISMATCH` + HALT · retrieve 예외 → `API_ERROR`, records·usage 변화 없음, 예외 문장 없음, 그 뒤 성공하면 failed.md 지움 |
| 15-2 | `test_submit_dry_run_writes_nothing` · `test_submit_dry_run_bad_prereg_no_halt` · `test_collect_dry_run` | 키 없이 `DRY_RUN items=2 symbols_failed=0`, workspace 폴더 안 생김, client 안 만듦 · 틀린 사전 등록에도 HALT 없음 · collect dry run은 호출·쓰기 없음 |
| 16 | `test_no_key_value_and_writes_under_llm_only` · `test_script_source_contract` | 모든 파일·출력에 가짜 키 없음, 사전 등록 복사본 밖의 파일은 모두 `workspace/outputs/llm/` 아래 · 원문 ASCII, `environ`·`zoneinfo`·`subprocess`·`import requests`·`urllib`·`fallbacks`·`advisor`·`socket`·`http.client` 등 없음 |
| — | `test_exit_codes_and_korean_text` | iccheck와 같은 이름은 같은 값, 새 코드 값, 한국어 상수 해독값 고정 |
| 17 | `test_main_requires_phase` · `test_main_submit_and_collect_lines` · `test_main_unexpected` · `test_main_month_spend_error_is_budget_stop` | `--phase` 없음 → 오류 종료 · 마지막 행 모양(ASCII, 200자 이내) · 예외 → 종료 1, `UNEXPECTED`, "secret text" 없음, failed.md엔 클래스 이름만 · `month_spend` 예외 → `BUDGET_STOP` |

## (c) 시험 결과 마지막 3줄

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_news*.py"`

```
Ran 50 tests in 0.857s

OK
```

## (d) 실행기 약속(`docs/claude/llm-runner-report.md` (d)절) 대조

- 인자: `--phase submit|collect`(필수), `--day YYYY-MM-DD`, `--dry-run`. 실행기 JOBS의 `("--phase", "submit")`·`("--phase", "collect")` + `--day <KST 날짜>`와 맞다(`llm_runner.py` 55~56행, 309행).
- 마지막 행: 언제나 ASCII `llm-news <날짜> <STATUS> ...`, `_line`이 200자로 자른다. 실행기 `_LINE_OK`·`_LINE_STATUS` 꼴(`llm-[a-z-]+ \d{4}-\d{2}-\d{2} [A-Z_]+`)과 맞다. collect는 끝에 ` late=<k>`.
- 두 번 불러도 한 번: submit은 batch.json → `ALREADY_DONE`, submit-started만 → `SUBMIT_UNKNOWN`(다시 내지 않음). collect는 collected.json → `ALREADY_DONE`, usage-done으로 사용량 한 번, records는 `(submitted_at, item_id)`로 중복 건너뜀.
- failed.md: 실패 상태마다 `write_failed`(그날 폴더). `PENDING`·`NO_BATCH`·`NOTHING_TO_COLLECT`·`HALTED`·`ALREADY_DONE`은 쓰지 않는다.
- 900초 안: 기사 300건 기준 — 가져오기는 30종목 각 1회(yfinance), 가리기는 종목별 정규식 캐시로 기사당 4번 돌린다(가린 뒤 재검사 포함), create는 한 번(요청 600개, 제목 300자·요약 2,000자 자르기로 요청 하나가 작다; SDK timeout 120초·재시도 1회 = `make_client`). collect는 retrieve 1회 + results 1회. yfinance 응답 시간은 이 환경에서 잴 수 없어 확인 필요((f)).

## (e) 사장님 첫 실행용 줄 (새 PowerShell 창, 저장소 폴더)

```
python manage-us-stock-strategy\scripts\llm_pilot_news.py --phase submit --dry-run
```
보낼 건수만 출력한다(`llm-news <날짜> DRY_RUN items=<n> symbols_failed=<k>`). 키를 읽지 않고, API를 부르지 않고, 아무 파일도 쓰지 않는다(seen.json 포함).

## (f) 확인 필요로 남은 것

- yfinance가 실제로 주는 항목 꼴(납작한 꼴/안에 든 꼴): 실제 꼴은 첫 실행에서 확인 필요. 두 꼴 모두 받게 했고, 못 읽는 항목은 skipped로 센다. yfinance 응답 시간과 멈춤(시간 제한 없음) 여부도 확인 필요 — 멈추면 실행기가 TIMEOUT으로 적고, 그날은 submit-started가 없어 다음 칸에서 다시 낼 수 없다(실행기는 칸마다 하루 한 번).
- Haiku 사고 토큰으로 `max_tokens`(사전 등록 1,024)가 모자라는 비율: 확인 필요. 모자라면 `MAX_TOKENS`로 그 건만 dropped.
- 하루 요청 수와 비용: 확인 필요(첫 주 usage.jsonl로 본다).
- Batch에서 모델 오류가 create 예외(404)로 오는지 결과 errored로 오는지: 확인 필요. 두 길 모두 HALT로 처리했다(errored는 오류 종류 글에 `not_found`가 있을 때).
- Batch 요청의 `output_config.format`·custom_id 규칙(`L0001`·`S0001`)이 실제로 받아들여지는지: 첫 실행에서 확인 필요.

## (g) 사전 등록과 다른 점·더한 점

- 사전 등록 .md '시험' 절은 '늦게 받은 결과의 표본 표시가 false'를 말하지만 원본 JSON `record.fields`에는 표본 칸이 없다 → JSON을 따라 칸을 만들지 않았고, 표본 판정은 채점기가 `received_at`으로 한다.
- 더한 것:
  - 기록 사슬이 깨지면 멈춤(`RECORDS_BROKEN` + HALT). 머리줄의 schema·prereg_sha256이 다르거나 파일이 없어도 깨진 것으로 본다.
  - 제목 300자·요약 2,000자 자르기(설계서 3절 4의 크기 상한을 이 시범에서는 글자 수 자르기로 지킴). 종목당 기사 수는 자르지 않는다.
  - 밀린 수거 3일(`LOOKBACK_DAYS`).
  - `load_prereg`가 `model.id` = `MODELS["news"]`도 확인한다(다르면 `PREREG_MISMATCH`).
  - 가린 뒤 재검사를 dry run·0건 판단보다 먼저 한다: dry run의 items는 새는 기사를 뺀 수이고, 모두 새면 빈 배치를 내지 않고 `NO_ITEMS`.
  - `SUBMIT_UNKNOWN`은 failed.md가 이미 있으면 덮지 않는다(첫 실패 이유 유지). create 직전에 그날의 이전 failed.md를 지운다.
  - seen.json을 못 읽으면 예외 → `UNEXPECTED`(다시 보내는 쪽으로 가지 않음).
  - 사용량 줄의 model·단가는 요청 모델(`MODELS["news"]`)로 적는다(응답 model이 틀린 경우에도 사용량은 남아야 하므로).
  - 결과가 빠졌거나 모르는 custom_id는 errors로 센다.
  - collect `--dry-run`은 로컬 파일만 보고 `ALREADY_DONE`·`NO_BATCH`·`DRY_RUN` 중 하나를 낸다(late 없음).

## 연결표 확인

지시문 `## 연결표` 3행 ③칸의 인용 `manage-us-stock-strategy/scripts/llm_pilot_news.py:436-442`는 이 파일의 제출 단계 5(월 예산 검사: `month_spend` → 예외면 `BUDGET_STOP`, 한도 이상이면 `BUDGET_STOP`)와 행이 일치한다. 1행 ②칸 `llm_runner.py` 55~56행 JOBS 칸도 원문과 같다.
