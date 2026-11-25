# llm-pdfcmp Builder 보고 (2026-11-25)

- 지시문: docs/claude/llm-pdfcmp-builder-prompt.md · 공통 규칙: tools/dev_pipeline/builder-rules.md
- 바꾼 파일: 새 파일 3개뿐(아래). `llm_pilot_common.py`·`llm_runner.py`·`llm-pilots-schedule.json`·원장·고르기 기록·기존 시험은 고치지 않았다.
- 권한 표지 4종 줄 변경 없음. 키움 호출 없음. 실제 외부자료 폴더·저장소 루트에 대고 스크립트를 돌리지 않았다(`--dry-run` 포함).

## (a) 만든 함수와 상수 — manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py (LF, ASCII만)

상수
- `PILOT`·`MAX_TOKENS`(4096)·`EST_INPUT_TOKENS_PER_PDF`·`EST_OUTPUT_TOKENS_PER_PDF`·`MAX_PDF_BYTES`·`MIN_USED`·`PASS_CLASS`·`PASS_TOPIC`·`QUOTE_MIN_CHARS`·`EVIDENCE_MD_CHARS` — 56~67행
- `EXIT_CODES` — 72행 (SUBMITTED·PENDING·WAITING·PASS·FAIL·HOLD·DONE_ALREADY·NO_BATCH·DRY_RUN = 0, UNEXPECTED = 1, NO_KEY = 4, BUDGET_STOP = 5, API_ERROR = 7. 같은 이름은 `llm_pilot_news.EXIT_CODES`와 같은 값)
- `DEFAULT_PDF_DIR` — 95행 (원장 17행 폴더, 지시문 글자 그대로)
- `PDFS` — 104행 (정답표 10행: pid·파일 이름(`\uXXXX`)·sha256·정답·주제 낱말)
- `INSTRUCTION` — 192행 (원장 21~36행 1절 규칙 1·3·4 요약, 4줄 답 형식. 금액·수량은 "쓰지 않는다"로만 나옴)
- `LABEL_*`·`CLASS_CAND_KO`·`ROUTES` — 219~224행 · `REASON_KO` — 226행 · `MD_*` — 237~250행

함수
- `valid_day` 259 · `pilot_dir` 266 · `day_dir_for` 270 · `_line` 297(마지막 줄 `llm-pdfcmp <day> <STATUS> …`, 200자 안)
- `check_pdfs` 318 — 폴더 읽기만. 없음 MISSING · 32,000,000바이트 초과 TOO_LARGE(읽기 전 크기 확인) · sha256 다름 SHA_MISMATCH
- `estimate_submit_cost` 351 — `estimate_cost(batch=True)`로 PDF당 상한 토큰 가정 × 쓸 PDF 수
- `build_request` 360 — custom_id = pid, `MODELS["pdfcmp"]`, document(file_id, citations 켬) + 지침 text. system·thinking·베타·advisor·대체 모델 없음
- `_delete_files` 383 · `_remove_stale_failed` 394
- `run_submit` 402 — compare.json → DONE_ALREADY · batch.json → PENDING · PDF 확인(`--dry-run`이면 여기서 DRY_RUN) · 8개 미만 HOLD(failed.md 1줄만, batch.json·compare.json 없음, 호출 0) · NO_KEY · `month_spend` 예외/상한 초과 BUDGET_STOP(업로드 전) · `<pid>.pdf` 이름으로 upload(실패 시 이미 올린 파일 지움, API_ERROR) · batches.create(실패 시 모두 지움) · batch.json 원자적 쓰기
- `_field_pattern` 501 · `parse_answer` 516 — 4줄 정규식(앞 `-`·`**` 허용), 분류 후보|R0, 라우트 R1~R4·P·R0, 빈 값·형식 틀림 → None(PARSE_FAIL)
- `topic_overlap` 543 — 대소문자·공백 무시 포함 비교
- `citation_texts` 548 · `quote_overlaps` 558 — 공백 정규화 뒤 가장 긴 공통 부분 ≥ 6자
- `_usage_numbers` 567 · `_message_cost` 580(가격 없는 모델이면 고정 모델 가격으로 계산 — usage 줄이 항상 숫자)
- `verdict` 588 — used < 8 HOLD, 분류 ≥ 8 그리고 주제 ≥ 8 PASS, 아니면 FAIL
- `render_md` 609 — 첫 줄 `판정: … — 분류 n/used · 주제 m/used · 인용 확인 q/used`, PDF별 표(pid로만, 근거 60자 자름), 뺀 PDF, 지우지 못한 파일 수, 표시 전용 줄
- `run_collect` 653 — compare.json → DONE_ALREADY · batch.json 없음 → NO_BATCH(쓰기 없음) · NO_KEY · retrieve가 ended 아님 → WAITING(쓰기 없음) · usage 줄(message 있는 결과마다 1줄, USAGE_KEYS 10개, `usage-done` 표시로 한 번만) · pid별 첫 결과 판정(MODEL_MISMATCH는 분모에서 뺌, REFUSAL·MAX_TOKENS·BAD_STOP·PARSE_FAIL·errored·expired·canceled·결과 없음은 분류·주제 불일치로 셈) · compare.json/md 쓰기 → files.delete → compare 다시 쓰기(`files_not_deleted`)
- `main` 839 — `--phase submit|collect`, `--day`, `--pdf-dir`(기본 `DEFAULT_PDF_DIR`), `--dry-run`. 예외는 UNEXPECTED(종료 1) + `pdfcmp/<day>/failed.md`

쓰는 곳: `workspace/outputs/llm/pdfcmp/`(batch.json·compare.json·compare.md·usage-done) · `workspace/outputs/llm/pdfcmp/<day>/failed.md` · 공용 `workspace/outputs/llm/usage.jsonl`(append_usage). 외부자료 폴더에는 쓰기·이동·삭제 코드가 없다.

## (b) 시험 — manage-us-stock-strategy/tests/test_llm_pilot_pdfcmp.py (LF, 43개)

가짜 클라이언트(FakeFiles·FakeBatches)·가짜 키·임시 폴더만 쓴다. `PDFS`는 `mock.patch.object`로 가짜 sha256 표로 바꾼다(실제 외부자료 폴더를 읽지 않음).

- 제출: `test_submit_ten_pdfs`(요청 10·custom_id P01~P10·document citations 켬·모델 `claude-haiku-5-5`·max_tokens 4096·금지 인자 없음·올린 이름 `P01.pdf` 꼴·원래 파일 이름이 요청에 없음·batch.json 내용) · `test_three_missing_hold_no_call`(HOLD, 업로드·Batch 호출 0, batch.json·compare.json 없음, failed.md 1줄) · `test_hold_then_next_day_submits` · `test_sha_mismatch_and_too_large_skipped` · `test_batch_exists_pending_no_resubmit` · `test_compare_exists_done_already_both_phases` · `test_budget_stop_no_call` · `test_budget_other_month_does_not_stop` · `test_unreadable_usage_budget_stop` · `test_estimate_is_below_budget_and_uses_batch_price` · `test_no_key` · `test_upload_failure_deletes_uploaded` · `test_create_failure_deletes_all` · `test_dry_run_reads_only` · `test_dry_run_hold_writes_nothing`
- 수거: `test_collect_no_batch`(쓰기 없음) · `test_collect_waiting_writes_nothing` · `test_collect_no_key` · `test_collect_pass_eight_eight`(PASS, md 첫 줄·표 줄) · `test_collect_fail_class_seven` · `test_collect_fail_topic_seven` · `test_parse_fail_counts_as_mismatch` · `test_failed_results_count_as_mismatch`(ERRORED·EXPIRED·NO_RESULT·MAX_TOKENS·REFUSAL, usage 줄은 message 있는 것만) · `test_model_mismatch_dropped_from_denominator`(분모 9, 날짜 붙은 고정 모델은 정상) · `test_model_mismatch_below_eight_hold` · `test_quote_counting`(인용은 판정에 안 씀) · `test_quote_overlap_rule` · `test_collect_deletes_files_and_records_leftovers` · `test_collect_all_deleted` · `test_collect_once_then_done_already`(다시 불러도 호출·삭제·usage 줄 변화 없음) · `test_usage_lines_shape_and_month_spend`(키 10개 모두 값 있음, `month_spend`가 예외 없이 읽음, 다른 시범도 읽힘) · `test_unpriced_model_usage_line_still_numeric` · `test_evidence_cut_at_sixty_in_md`
- 실행·계약: `test_main_last_line_and_exit_codes`(마지막 줄이 `llm_runner._LINE_OK`·`_LINE_STATUS`에 맞음) · `test_main_unexpected` · `test_key_never_written_or_printed`(가짜 키가 stdout·stderr·모든 출력 파일에 없음) · `test_exit_codes`(뉴스 시범과 같은 이름 같은 값) · `test_parse_answer` · `test_topic_overlap_ignores_case_and_space` · `test_script_source_contract`(금지어 11개 없음·ASCII·LF·폴더 쓰기/삭제 호출 없음) · `test_answer_table_matches_prompt`(pid·정답·sha256·파일 이름 10행이 시험 안 `\uXXXX` 표와 같고, 지시문 표를 직접 읽어 주제 낱말까지 글자 그대로 같음) · `test_pinned_korean_text`(지침·라벨·실패 이유·md 문구를 풀어 쓴 한국어로 고정) · `test_real_topic_words_match_prompt`

## (c) 시험 결과

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_pilot_pdfcmp*.py"`

```
Ran 43 tests in 0.974s

OK
```

`git status --short`(새 파일이라 `git diff --stat`에는 나오지 않음):

```
?? docs/claude/llm-pdfcmp-report.md
?? manage-us-stock-strategy/scripts/llm_pilot_pdfcmp.py      (867줄)
?? manage-us-stock-strategy/tests/test_llm_pilot_pdfcmp.py   (824줄)
```

전체 시험은 돌리지 않았다(파이프라인이 한다).

## (d) 병합 뒤 사장실이 할 일

- 켜기 카드 1번: `pdfcmp-submit`·`pdfcmp-collect` 두 줄을 한 번에 켠다(`docs/claude/llm-pilots-schedule.json`, 커밋된 판만 실행기가 읽음). 실행은 실행기 13:10 제출 · 15:10/17:10 수거(`llm_runner.py:53-54`).
- 결과: `workspace/outputs/llm/pdfcmp/compare.md` 첫 줄(판정 PASS/FAIL/HOLD). 켠 날 17:30 KST 뒤 이 프로젝트가 직접 읽는다(연결표 ⑤ 알림 끊김은 기존과 같음).
- PASS/FAIL/HOLD(수거 단계)가 나오면 끄기 카드. 제출 단계 HOLD(쓸 PDF 8개 미만)는 compare.json을 쓰지 않으므로 다음 날 13:10에 다시 확인한다 — 빠진 PDF는 `pdfcmp/<날짜>/failed.md`와 실행기 마지막 줄의 `skipped=` 목록으로 본다.
- PASS면 '외부자료 PDF 1차 분류를 API로 옮기는 안'을 따로 제안(별도 승인), FAIL이면 질문을 닫는다.

## (e) 확인 필요로 남은 것

- Haiku 5.5 생각 토큰이 max_tokens 4096 안에 드는지(넘으면 MAX_TOKENS로 그 PDF는 불일치로 셈).
- Batch 안에서 Files API file_id 문서 블록과 문서 인용(citations)이 되는지(api-pilots 7절 3). 안 되면 결과가 errored로 돌아와 불일치로 세어져 FAIL 쪽으로 기운다.
- SDK에서 Files API가 `client.files`(베타 아님) 경로로 열려 있는지. 지시문대로 `client.files.upload`·`client.files.delete`를 쓰고 베타 헤더를 넣지 않았다. 경로가 없으면 올리기 단계에서 API_ERROR(이미 올린 파일 지움)로 끝나고 batch.json은 생기지 않는다.
- Haiku 5.5가 27쪽·16.6MB PDF(P09)를 받는지(크기 상한 안이라 제출은 한다. 거부되면 그 PDF만 불일치).
- Batch·Files 사용분이 크레딧에서 빠지는지(api-pilots 7절 1).
- 실제 외부자료 폴더의 파일 이름·sha256은 이 세션에서 읽지 않았다(지시문 규칙). 정답표는 지시문 표와 글자 그대로 같음을 시험으로 확인했다. 실제 파일과 맞는지는 첫 제출의 `used=`·`skipped=`로 드러난다(맞지 않으면 그 PDF만 빠지고, 8개 미만이면 HOLD).
