# llm-runner 보고 — API 시범 실행기·래퍼·등록 스크립트·켜기 파일 (2026-11-07)
재시도: llm-runner2 — 앞 작업 llm-runner의 병합 멈춤(켜기 파일 CRLF) 고침

- 지시문: docs/claude/llm-runner2-builder-prompt.md (개발 큐 general)
- 앞 작업과 다른 점: 저장소 켜기 파일 시험 (가)는 바이트를 읽은 뒤 먼저 `\r\n`→`\n`으로 바꾸고 **형식만** 본다(키 순서 = JOB_NAMES, 들여쓰기 2칸·끝 줄바꿈 1개, `load_schedule` OK, enabled 목록 = 파일에서 켜진 이름). enabled 값 자체는 단언하지 않는다(시범을 켜도 깨지지 않음). 정적 시험의 .ps1 읽기도 같은 방식으로 줄 끝에 기대지 않는다.
- 이 작업은 어떤 시범도 켜지 않았고(켜기 파일 7개 모두 꺼짐), Windows 작업을 등록·실행하지 않았고, 저장소에 대고 실행기·래퍼·등록 스크립트를 돌리지 않았다. 표지 없음.

## (a) 만든 파일과 주요 함수
- `manage-us-stock-strategy/scripts/llm_runner.py` (ASCII만)
  - 상수: `Job`(NamedTuple) 40행, `JOBS` 49행(표 그대로 7개, 순서 포함), `JOB_NAMES`·`SCHEDULE_REL`·`CEO_ACCOUNT_ID` 58~60행, `CATCH_UP_MINUTES = 60`·`JOB_TIMEOUT_SECONDS = 900` 61~62행. `KST`·`REPO_ROOT`·`atomic_write_text`·`llm_dir`는 `llm_pilot_common`에서 가져옴(iccheck와 같은 import 방식).
  - `default_git_show` 75행: `git -C <root> show HEAD:docs/claude/llm-pilots-schedule.json`(30초), 0 아닌 종료·예외 → None. 작업 트리 파일은 읽지 않음.
  - `load_schedule` 99행: SCHEDULE_MISSING(GIT_SHOW) / SCHEDULE_INVALID(NOT_JSON·NOT_OBJECT·UNKNOWN_JOB·BAD_ENTRY·BAD_REF·BAD_KST). 하나라도 틀리면 전체 거부. 없는 작업 이름은 꺼짐.
  - `read_day` 155행·`write_day` 179행: `workspace/outputs/llm/runner/<KST 날짜>.json`(schema `llm-runner-day-1`), 모양이 틀리면 None(DAY_FILE_BAD) — 파일을 고치지 않음. 쓰기는 모두 `atomic_write_text`.
  - `default_run_job` 185행: `subprocess.run(argv, cwd, timeout, capture_output=True, text=True, encoding="utf-8", errors="replace")`, 실행 설정 인자를 넘기지 않음(부모 것 그대로), stderr는 버림.
  - `pick_line` 199행(마지막 비지 않은 행이 `^llm-[a-z-]+ [\x20-\x7e]{1,200}$`일 때만), `status_of` 209행(세 번째 낱말 또는 `EXIT_<코드>`).
  - `run_once` 227행: 하루 기록 확인 → 켜기 파일 확인(실패 시 schedule·last_check_kst만 쓰고 2) → 칸마다 0 ≤ 차이 < 60분, 같은 (job, slot) 있으면(STARTED 포함) 넘김, 스크립트 없으면 NOT_BUILT, dry_run이면 `due <job> <slot>`만, 부르기 전 STARTED 기록 → 부름 → TIMEOUT / `LAUNCH_ERROR:<클래스>` / 종료 코드·line·status 기록, 실패해도 다음 칸 계속 → 0.
    - 주어진 now가 있으면 started/finished 시각도 그 값을 쓴다(시험 재현성). 없으면 실제 시계.
    - 하루 기록이 깨졌을 때 summary의 schedule 칸은 `DAY_FILE_BAD`로 찍힌다(켜기 파일은 읽지 않음).
  - `main` 339행: `--dry-run`만, 한 줄 `llm-runner <day> <HH:MM> schedule=<STATUS> due=<n> ran=<n> not_built=<n>`, 예상 못 한 예외는 `llm-runner ERROR <클래스>` + 1.
- `manage-us-stock-strategy/scripts/run_llm_pilots.ps1` (ASCII, `[CmdletBinding()]`): 저장소·Python 찾기는 `run_journal_score.ps1`과 같음, 없으면 `RUNNER_FAIL RUNNER_SCRIPT_NOT_FOUND`(34행)·`RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND`(50행) + 3. 키 넘기기 블록 56~61행(지시문 모양 그대로, 프로세스 값이 비었을 때만 사용자 범위 값을 읽음), `RUNNER_START local=… timezone=… key_present=YES|NO` 64행, `cmd /c` 73행(`>> 로그 2>&1`), `RUNNER_END exit=<n>` 78행, catch에서 `RUNNER_FAIL RUNNER_EXCEPTION type=… message=…`(ASCII 300자) + 4(90행). 로그 `workspace\outputs\llm\runner\logs\<yyyyMMdd>.log`.
- `manage-us-stock-strategy/scripts/register_llm_pilots_task.ps1` (ASCII, `[CmdletBinding()]`): `register_journal_score_task.ps1` 틀. 이름 `InvestmentV2-LLMPilots` 하나, 30분 한도, 트리거 83~84행(매일 00:00 + 10분 반복 1일, 지시문 모양 그대로), `if ($PlanOnly)` 68행 → 계획만 찍고 0, 시간대가 KST가 아니면 `APPLY_BLOCKED_TIMEZONE` + 2(73행), `Register-ScheduledTask` 91행 1번. 실행·삭제·변경 명령 없음.
- `docs/claude/llm-pilots-schedule.json`: 7개 이름 JOBS 순서, 모두 `{"enabled": false, "approved_ref": "", "approved_kst": ""}`, 들여쓰기 2칸, LF, 끝 줄바꿈 1개.
- 시험 2개: 아래 (b).

## (b) 시험과 단언 요약
`manage-us-stock-strategy/tests/test_llm_runner.py` — 모두 임시 루트·가짜 git_show·가짜 run_job(실제 프로세스·git·네트워크 없음). 승인 칸 예는 지시문 그대로, 시험 날짜 2026-11-08(승인 시각 2026-11-07 10:00:00 KST보다 뒤).
- (가) `test_repository_switch_file_format`: CRLF→LF 뒤 dict·키 순서 = JOB_NAMES·바이트 = `json.dumps(indent=2, ensure_ascii=False)+"\n"`·`load_schedule` OK·enabled = 파일에서 켜진 이름. enabled 값 자체는 단언하지 않음.
- (나) `test_worktree_on_but_committed_off_runs_nothing`(작업 트리 켜짐·커밋본 꺼짐 → 안 부름, git_show가 (루트, SCHEDULE_REL)로 불림), `test_worktree_off_but_committed_on_runs_once`(반대 → 1번), `test_default_git_show_reads_head_blob_only`(기본 git_show 인자 `git -C <루트> show HEAD:…`, 종료 128·예외 → None; subprocess.run을 가짜로 바꿔 git을 띄우지 않음).
- (다) `test_missing_committed_file`: 종료 2, SCHEDULE_MISSING, 안 부름, 하루 기록 schedule = SCHEDULE_MISSING/GIT_SHOW, last_check_kst +09:00.
- (라) `test_invalid_switch_text_rejects_everything`(16경우: NOT_JSON 2·NOT_OBJECT·UNKNOWN_JOB "review"·BAD_ENTRY 5(enabled "true", 키 하나 더, 키 하나 빠짐, 항목이 dict 아님, ref가 str 아님)·BAD_REF 4(빈 글, cmsg_ 없음, cmsg_ 뒤 20자 미만, 사장 계정 id 없음)·BAD_KST 3(형식, 없는 날짜, now보다 늦음)) — 매번 iccheck는 맞게 켜져 있고 스크립트도 있지만 종료 2, 안 부름, 하루 기록 reason 일치. 보조: `test_approval_at_the_same_second_is_accepted`, `test_missing_job_counts_as_off`.
- (마) `test_due_window`: 07:29 0번, 07:30 1번, 08:29 1번, 08:30 0번(각각 새 루트).
- (바) `test_one_run_per_slot`(07:35 부름 → 07:45 안 부름 → 다음 날 07:35 다시 부름, 새 날짜 파일), `test_started_entry_blocks_a_second_start`(미리 STARTED 있으면 안 부르고 기록 그대로), `test_started_entry_is_written_before_the_call`(부를 때 파일에 STARTED 항목이 이미 있음).
- (사) `test_two_slots_of_one_job`: news-collect 22:05·23:05 각 1번, 칸 22:00·23:00 두 항목.
- (아) `test_script_not_built`: 19:35 안 부름·NOT_BUILT 1개(exit_code null, line ""), 19:45에도 1개.
- (자) `test_argv_cwd_and_timeout`(iccheck·news-collect argv, cwd = 루트, timeout 900), `test_default_run_job_passes_no_process_settings_and_captures`(기본 run_job을 가짜 subprocess.run으로: `env` 인자 없음, capture_output=True, timeout=900, stderr·앞 행이 기록에 없음).
- (차) `test_failure_does_not_block_the_next_job`: 08:15 iccheck·srccheck-submit — TimeoutExpired → TIMEOUT, OSError → `LAUNCH_ERROR:OSError`(예외 문장 없음), 종료 7 + API_ERROR 행 → exit_code 7·status API_ERROR; 세 경우 모두 두 번째도 불림.
- (카) `test_line_filter`: 한글 섞인 행·`llm-` 아님·201자 → line "" + `EXIT_<코드>`, 끝 빈 행 무시, 마지막 행이 다른 글이면 "", 상태 낱말 없는 llm- 행은 line 유지 + EXIT, 빈 출력.
- (타) `test_no_key_text_reaches_the_record`: 가짜 키가 앞 행에 있어도 하루 기록·임시 폴더 모든 파일·main 출력에 없음; llm_runner.py 원문에 `environ`·`anthropic`·`API_KEY`·`INVESTV2` 없음(대소문자 무시도).
- (파) `test_broken_day_file_stops_everything`(9경우: JSON 아님, UTF-8 아님, 목록, schema 다름, day 다름, runs가 목록 아님, job 없음, slot 숫자, 항목이 dict 아님) → 종료 2, DAY_FILE_BAD, 안 부름, 바이트 그대로, 다른 파일 없음.
- (하) `test_dry_run_starts_and_writes_nothing`(안 부름, `due iccheck 07:30`, 임시 루트에 workspace 폴더 없음), `test_dry_run_with_rejected_schedule_writes_nothing`.
- (거) `test_constants`: JOBS 표(이름·시각·스크립트·args·순서), SCHEDULE_REL, 60, 900, 사장 계정 id.
- (너) `test_unexpected_exception`(RuntimeError("secret text") → 1, 출력 `llm-runner ERROR RuntimeError`만), `test_summary_line`(정상·--dry-run·SCHEDULE_MISSING 한 줄 형식).

`manage-us-stock-strategy/tests/test_llm_runner_task_static.py` — .ps1은 CRLF→LF 뒤 ASCII로 읽음.
- `test_both_scripts_are_ascii_advanced_scripts`, `test_register_script_handles_one_ten_minute_task`(지시문의 필수 글자·트리거 두 행 그대로·설명 글·TRIGGER 칸, InvestmentV2- 이름 하나, Register 1번, PlanOnly 블록이 Register보다 앞이고 exit 0, 요일 이름·Unregister/Set/Start-ScheduledTask 없음), `test_wrapper_hands_over_the_key_without_writing_it`(키 블록 여섯 행 그대로, 프로세스 값 검사가 GetEnvironmentVariable보다 앞, `$userValue` 행은 세 행뿐, 키 이름 행에 Write-·Add-Content·Out-File·Set-Content 없음, 금지 명령·kiwoom 없음), `test_no_state_policy_or_ledger_path_in_either_script`.
- `WrapperCopyBehaviourTests`(Windows에서만, 이번 실행에서 **돌았음** — skip 0): 임시 저장소의 래퍼 복사본 + 가짜 llm_runner.py, 모든 실행에 프로세스 가짜 키.
  - `test_1_normal_run`: 종료 0, 가짜 실행기 인자 없음·키 있음 YES, 로그 `RUNNER_START local=… timezone=… key_present=YES`·`RUNNER_END exit=0`, 임시 폴더 모든 파일·stdout·stderr에 가짜 키 없음.
  - `test_2_runner_exit_code_is_kept`: 종료 2, `RUNNER_END exit=2`.
  - `test_3_missing_runner_exits_3`: 종료 3, `RUNNER_FAIL RUNNER_SCRIPT_NOT_FOUND`, RUNNER_START 없음.
  - 매번 복사본이 임시 폴더 안이고 저장소 밖임을 단언.

## (c) 시험 결과 마지막 3줄
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_runner*.py"`
```
Ran 32 tests in 1.425s

OK
```

## (d) 시범 스크립트 약속 (작업 3~5가 지킬 것)
- `--day YYYY-MM-DD`와 표의 args(`--phase submit|collect`)를 받는다. 실행기는 `[python, <스크립트>, *args, "--day", <KST 날짜>]`, cwd = 저장소 루트로 부른다.
- 표준 출력 마지막 행은 ASCII `llm-<시범> <날짜> <STATUS> ...`(200자 이내). 다른 모양이면 실행기는 line을 비우고 status를 `EXIT_<코드>`로 적는다. stderr는 남지 않는다.
- 같은 날·같은 단계를 두 번 불러도 한 번만 일한다(실행기는 칸마다 하루 한 번만 부르지만, 사람이 손으로 다시 불러도 안전해야 함).
- 실패는 자기 폴더 failed.md에 쓴다(`llm_pilot_common.write_failed`).
- 실행 시간은 900초 안. 넘으면 실행기가 TIMEOUT으로 적고 다시 부르지 않는다.
- 키는 실행기가 넘기지 않는다: 래퍼가 프로세스 값에 넣어 두고 자식은 그대로 물려받는다.

## (e) 사장님 등록용 두 줄 (관리자 아닌 PowerShell, 저장소 폴더에서)
계획 확인:
```
powershell -NoProfile -ExecutionPolicy Bypass -File manage-us-stock-strategy\scripts\register_llm_pilots_task.ps1 -PlanOnly
```
등록:
```
powershell -NoProfile -ExecutionPolicy Bypass -File manage-us-stock-strategy\scripts\register_llm_pilots_task.ps1
```
- 등록해도 켜기 파일이 7개 모두 꺼짐이라 아무 시범도 돌지 않는다. 10분마다 실행기가 켜기 파일을 확인하고 하루 기록(`workspace/outputs/llm/runner/<날짜>.json`)과 로그만 남긴다.
- 시범을 켜는 것은 따로: 사장 승인 뒤 사장실 스레드가 원문과 대조하고 켜기 파일의 그 항목을 고쳐 커밋해야(실행기는 커밋본만 읽음) 돈다.
- 등록과 시범 켜기는 이 작업 밖이다(병합 뒤 따로 사장 승인).
