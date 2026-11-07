---
id: llm-runner2-builder-prompt
title: "API 시범 실행기 — 10분마다 도는 Windows 작업용 실행기 + 래퍼 + 등록 스크립트 + 켜기 파일(모두 꺼짐) — llm-runner2(llm-runner 재시도)"
date: 2026-11-07
class: "general(새 파일만, 코어·정책·주문 경로와 무관). 개발 큐 general: Builder → Judge → READY_TO_MERGE면 Cowork가 dev-merge"
source: "설계 docs/claude/api-pilots-2026-11-06.md 3절 '실행 방법'·4절 '실행기'·6절 작업 2. 개발 큐 등록 승인 = 사장 결정 카드 '시범 1부터 차례로'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9E3aPheNEEsLywwbJ1nm476, 2026-11-06 16:44:47 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH). 등록 조건(6절 작업 2: 작업 1 병합 + 첫 실행 성공) 충족 = 병합 559efb9(2026-11-07) + 사장 첫 실행 2026-11-07 09:35 KST 'llm-iccheck 2026-11-07 OK findings=6 dropped=0'. Windows 작업 등록과 시범 켜기는 이 작업 밖(병합 뒤 따로 사장 승인). 재시도 근거 = llm-runner 병합 멈춤(2026-11-07 13:38 KST dev-merge STOP_BASE_MOVED tests_after_rebase, 아래 재시도 사유)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장·연구 기록·카드 쓰기 없음 · API 키 값을 읽거나 출력하지 않음 · Windows 작업을 등록하거나 실행하지 않음"
---

## 재시도 사유 (먼저 읽는다)
- 앞 작업 `llm-runner`는 Judge PASS·새 실패 0으로 READY_TO_MERGE였지만, `dev-merge`가 rebase 뒤 전체 시험에서 멈췄다: `STOP_BASE_MOVED reason=tests_after_rebase:NEW_FAILURE:test_repository_switch_file_is_all_off` (workspace/outputs/dev-runs/llm-runner/merge-tests.json, target-1.err).
- 원인: (가) 시험이 저장소 켜기 파일을 작업 트리 바이트로 읽고 `assertNotIn(b"\r", raw)`를 단언했다. Builder가 새로 쓴 파일은 LF였지만, 커밋 뒤 Windows 체크아웃(병합 작업 트리)에서는 CRLF가 된다(저장소 blob은 LF — `git ls-files --eol`에서 `i/lf w/crlf`인 파일이 많다). 실행기는 커밋본(`git show HEAD:`)을 읽으므로 실제 동작에는 문제가 없다.
- 함께 고칠 설계 빈틈: (가)가 '모든 항목 enabled false'를 단언하면, 병합 뒤 사장 승인으로 시범 1을 켜는 순간 이 시험이 영구 실패가 된다. 병합 때 모두 꺼짐은 Judge가 확인하고, 시험은 켜기 파일의 **형식**만 본다.
- 그래서 이번 작업은 앞 작업과 같은 7개 파일을 같은 요구대로 만들고, 아래 '시험' 1번 (가)와 '지켜야 할 것' 7번만 다르다.

## 목표
- 시범 스크립트들을 정해진 KST 시각에 한 번씩 돌리는 실행기 `llm_runner.py`를 만든다. 실행기 자신은 API를 부르지 않고 키도 읽지 않는다.
- Windows 작업 `InvestmentV2-LLMPilots`(10분마다)가 부를 래퍼 `run_llm_pilots.ps1`과, 사장님이 한 번 칠 등록 스크립트 `register_llm_pilots_task.ps1`을 만든다.
- 켜기 파일 `docs/claude/llm-pilots-schedule.json`을 만든다. 처음에는 7개 작업이 **모두 꺼짐**이다. 실행기는 작업 트리가 아니라 **커밋본**(`git show HEAD:docs/claude/llm-pilots-schedule.json`)만 읽는다.
- 이 작업은 어떤 시범도 켜지 않고, Windows 작업을 등록하거나 실행하지 않는다. 시범 1 스크립트(`llm_pilot_iccheck.py`)와 공통 모듈(`llm_pilot_common.py`)은 고치지 않는다.

## 바꿀 파일 (이 7개만, 모두 새 파일)
- manage-us-stock-strategy/scripts/llm_runner.py
- manage-us-stock-strategy/scripts/run_llm_pilots.ps1
- manage-us-stock-strategy/scripts/register_llm_pilots_task.ps1
- manage-us-stock-strategy/tests/test_llm_runner.py
- manage-us-stock-strategy/tests/test_llm_runner_task_static.py
- docs/claude/llm-pilots-schedule.json
- docs/claude/llm-runner-report.md (보고)

## 먼저 읽을 것 (고치지 않는다)
- `manage-us-stock-strategy/scripts/llm_pilot_iccheck.py`(import 방식 24~47행, `main`·종료 코드·표준 출력 한 줄), `llm_pilot_common.py`(`KST`·`REPO_ROOT`·`llm_dir`·`atomic_write_text`).
- 선례: `register_journal_score_task.ps1`·`run_journal_score.ps1`(Python 찾기·로그·예외 처리), 시험 `test_journal_score_task_static.py`·`test_journal_score_runner.py`(PowerShell 복사본 시험 방식).

## 구현 요구 — llm_runner.py (ASCII만, `scripts/*.py` 언어 계약)
1. **상수**
   - `JOBS`: 아래 표 그대로의 튜플(순서도 그대로). 항목은 `name`, `times`(KST "HH:MM" 튜플), `script`(scripts 폴더의 파일 이름), `args`(튜플).

     | name | times | script | args |
     |---|---|---|---|
     | iccheck | ("07:30",) | llm_pilot_iccheck.py | () |
     | srccheck-submit | ("08:10",) | llm_pilot_srccheck.py | ("--phase", "submit") |
     | srccheck-collect | ("10:10",) | llm_pilot_srccheck.py | ("--phase", "collect") |
     | pdfcmp-submit | ("13:10",) | llm_pilot_pdfcmp.py | ("--phase", "submit") |
     | pdfcmp-collect | ("15:10", "17:10") | llm_pilot_pdfcmp.py | ("--phase", "collect") |
     | news-submit | ("19:30",) | llm_pilot_news.py | ("--phase", "submit") |
     | news-collect | ("22:00", "23:00") | llm_pilot_news.py | ("--phase", "collect") |

     - iccheck·srccheck·news 시각은 설계서 4절 그대로다. pdfcmp 시각은 설계서에 없어 잠정이다(작업 4가 확정하고, 바꾸면 그 작업이 이 파일을 고친다).
   - `JOB_NAMES` = JOBS의 name 목록. `SCHEDULE_REL = "docs/claude/llm-pilots-schedule.json"`.
   - `CEO_ACCOUNT_ID = "user_01KuMGKfZu1SBYxtMmg4vAiH"`(사장 계정 id — 결정 문서에 이미 있는 값).
   - `CATCH_UP_MINUTES = 60`, `JOB_TIMEOUT_SECONDS = 900`.
   - `KST`·`REPO_ROOT`·`atomic_write_text`·`llm_dir`는 `llm_pilot_common`에서 가져온다(iccheck와 같은 import 방식).
2. **켜기 파일 읽기** `load_schedule(repo_root, now, git_show) -> (status, reason, enabled_names)`
   - `git_show(repo_root, SCHEDULE_REL)`는 커밋본 바이트를 돌려준다. 기본 구현은 `subprocess.run(["git", "-C", str(repo_root), "show", "HEAD:" + SCHEDULE_REL], capture_output=True, timeout=30)`이고, 종료 코드가 0이 아니거나 예외면 None이다. **작업 트리 파일은 읽지 않는다.**
   - None이면 `("SCHEDULE_MISSING", "GIT_SHOW", [])`.
   - UTF-8 JSON이 아니면 `("SCHEDULE_INVALID", "NOT_JSON", [])`. 최상위가 dict가 아니면 `NOT_OBJECT`.
   - 최상위 키가 JOB_NAMES 밖이면 `UNKNOWN_JOB`(없는 작업은 꺼짐으로 본다).
   - 각 항목은 키가 정확히 {enabled, approved_ref, approved_kst}인 dict여야 한다(아니면 `BAD_ENTRY`). enabled는 bool이어야 한다(아니면 `BAD_ENTRY`). approved_ref·approved_kst는 str이어야 한다(아니면 `BAD_ENTRY`).
   - enabled가 true인 항목은:
     - approved_ref에 정규식 `cmsg_[0-9A-Za-z]{20,}`이 있고 `CEO_ACCOUNT_ID` 글자가 들어 있어야 한다(아니면 `BAD_REF`).
     - approved_kst가 `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} KST$`에 맞고 KST 시각으로 읽혀야 하며 now보다 늦지 않아야 한다(아니면 `BAD_KST`).
   - enabled가 false인 항목의 approved_ref·approved_kst는 빈 글이어도 된다(검사하지 않는다).
   - 하나라도 틀리면 **전체를 거부**하고 어떤 작업도 돌리지 않는다(닫힌 쪽 실패). 맞으면 `("OK", None, [enabled가 true인 이름, JOBS 순서])`.
   - 실행기는 형식만 본다. 승인 진위는 이 파일을 커밋하기 전에 사장실 스레드가 원문과 대조한다(설계서 3절).
3. **하루 기록** `workspace/outputs/llm/runner/<KST 날짜>.json`
   - 모양: `{"schema": "llm-runner-day-1", "day": <날짜>, "last_check_kst": <ISO, +09:00>, "schedule": {"status", "reason", "enabled"}, "runs": [...]}`.
   - runs 항목 키: job, slot("HH:MM"), started_kst, finished_kst, exit_code, status, line.
   - 파일이 있는데 JSON으로 읽을 수 없거나 모양이 다르면(schema가 `llm-runner-day-1`이 아님, day가 그날이 아님, runs가 목록이 아님, runs 항목에 문자열 job·slot이 없음) `DAY_FILE_BAD`: 파일을 고치지 않고, 어떤 작업도 돌리지 않는다.
   - 모든 쓰기는 `atomic_write_text`다.
4. **한 번 돌기** `run_once(now=None, *, repo_root=REPO_ROOT, git_show=None, run_job=None, python=sys.executable, dry_run=False) -> (exit_code, summary)`
   1. now = 주어진 값 또는 `datetime.now(KST)`, KST로 바꾼다. day = now의 KST 날짜.
   2. 하루 기록을 읽는다(없으면 빈 runs). DAY_FILE_BAD면 2로 끝낸다.
   3. 켜기 파일을 읽는다. OK가 아니면 schedule 칸·last_check_kst만 갱신해 쓰고(dry_run이면 쓰지 않음) 2로 끝낸다.
   4. JOBS 순서·times 순서로 칸(job, slot)마다:
      - 꺼진 작업이면 넘어간다(기록하지 않음).
      - **때:** `분(now) - 분(slot)`이 0 이상이고 `CATCH_UP_MINUTES` 미만일 때만(분 = 시×60+분, 초는 버림). 07:29는 아니고 07:30·08:29는 맞고 08:30은 아니다.
      - runs에 같은 (job, slot)이 이미 있으면(상태 상관없이, STARTED 포함) 넘어간다. 하루 한 칸 한 번이고 다시 시도하지 않는다.
      - 스크립트 파일(`<repo_root>/manage-us-stock-strategy/scripts/<script>`)이 없으면 status `NOT_BUILT`(exit_code null, line "")로 기록하고 부르지 않는다.
      - dry_run이면 표준 출력에 `due <job> <slot>`만 적고 부르지도 쓰지도 않는다.
      - 부르기 전에 status `STARTED` 항목(started_kst만 채움)을 넣고 하루 기록을 쓴다. 그다음 `run_job(argv, cwd, timeout)`을 부른다.
        - argv = `[python, <스크립트 절대 경로>, *args, "--day", day]`, cwd = repo_root, timeout = `JOB_TIMEOUT_SECONDS`.
        - 기본 run_job은 `subprocess.run(argv, cwd=cwd, timeout=timeout, capture_output=True, text=True, encoding="utf-8", errors="replace")`이고 `(returncode, stdout)`을 돌려준다. **env를 넘기지 않는다**(부모 환경을 그대로 물려줌). stderr는 어디에도 남기지 않는다.
      - 결과로 그 항목을 고친다: finished_kst, exit_code, line, status.
        - line = stdout의 마지막 비지 않은 행이 `^llm-[a-z-]+ [\x20-\x7e]{1,200}$`에 맞으면 그 행, 아니면 "".
        - status = line이 `^llm-[a-z-]+ \d{4}-\d{2}-\d{2} ([A-Z_]+)`이면 그 세 번째 낱말, 아니면 `EXIT_<코드>`.
        - `subprocess.TimeoutExpired` → status `TIMEOUT`, exit_code null.
        - 그 밖의 예외 → status `LAUNCH_ERROR:<예외 클래스 이름>`, exit_code null. 예외 문장은 쓰지 않는다.
        - 한 작업이 실패해도 다음 칸을 계속 본다.
   5. 끝에 last_check_kst·schedule을 갱신해 쓴다(dry_run이면 쓰지 않음). 0으로 끝낸다(작업 실패는 하루 기록에만 남는다).
   - summary는 `{"day", "hm", "schedule", "due", "ran", "not_built"}` dict다.
5. **main(argv=None, ...)**: `--dry-run`만 받는다. 표준 출력에 ASCII 한 줄 `llm-runner <day> <HH:MM> schedule=<STATUS> due=<n> ran=<n> not_built=<n>`. 예상 못 한 예외는 main이 잡아 `llm-runner ERROR <예외 클래스 이름>`을 찍고 1로 끝낸다(traceback 없음).
6. **금지**: `os.environ`을 읽거나 쓰지 않는다. `anthropic`을 import하지 않는다. 키 환경 변수 이름을 코드에 쓰지 않는다. 네트워크 호출 없음. `workspace/outputs/llm/runner/` 밖에 쓰지 않는다.

## 구현 요구 — run_llm_pilots.ps1 (ASCII만, `[CmdletBinding()]`)
- 매개변수 `-RepositoryRoot`, `-PythonPath`. 저장소·Python 찾기는 `run_journal_score.ps1` 18~22행·`.venv`→`venv`→PATH 순서를 그대로 따른다. 못 찾으면 로그 `RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND` / `RUNNER_FAIL RUNNER_SCRIPT_NOT_FOUND`(llm_runner.py 없음)를 쓰고 3으로 끝낸다.
- 로그: `workspace\outputs\llm\runner\logs\<yyyyMMdd>.log`(로컬 날짜 = KST, 하루 한 파일에 덧붙임, ASCII). `RUNNER_START local=<yyyy-MM-ddTHH:mm:ss> timezone=<Id> key_present=<YES|NO>`, 끝에 `RUNNER_END exit=<n>`.
- **키 넘기기(설계서 3절 1)** — 이 모양 그대로:
  ```powershell
  if ([string]::IsNullOrEmpty($env:INVESTV2_ANTHROPIC_API_KEY)) {
      $userValue = [Environment]::GetEnvironmentVariable('INVESTV2_ANTHROPIC_API_KEY', 'User')
      if (-not [string]::IsNullOrEmpty($userValue)) { $env:INVESTV2_ANTHROPIC_API_KEY = $userValue }
      $userValue = $null
  }
  $keyPresent = if ([string]::IsNullOrEmpty($env:INVESTV2_ANTHROPIC_API_KEY)) { "NO" } else { "YES" }
  ```
  - 프로세스 변수가 이미 있으면 사용자 범위 값을 읽지 않는다. 값은 어떤 출력·로그·파일에도 쓰지 않는다. `Start-Transcript`를 쓰지 않는다.
- 실행: `$env:PYTHONIOENCODING = "utf-8"`, `$env:PYTHONUTF8 = "1"`, 저장소로 이동한 뒤 `cmd /c` + `"<python>" "<llm_runner.py>" >> "<log>" 2>&1`(journal 래퍼 방식). 종료 코드 = Python 종료 코드.
- 예상 못 한 예외는 journal 래퍼처럼 catch에서 `RUNNER_FAIL RUNNER_EXCEPTION type=... message=...`(ASCII로 바꾼 300자 이내)를 로그에 쓰고 4로 끝낸다.
- 금지: `Invoke-WebRequest`·`Invoke-RestMethod`·`Remove-Item`·`Start-Sleep`·`Start-Transcript`, 키움 관련 글자, 정책·상태 경로.

## 구현 요구 — register_llm_pilots_task.ps1 (ASCII만, `[CmdletBinding()]`)
- `register_journal_score_task.ps1`와 같은 틀(PlanOnly, 시간대 확인 `Korea Standard Time`, Interactive·Limited, StartWhenAvailable, WakeToRun 끔, IgnoreNew, 숨은 창, Get-TaskExistence, Write-TaskPlan, ORDER_AUTHORITY = $false). 이 작업 이름 하나만 만들거나 덮어쓴다.
- `Name = "InvestmentV2-LLMPilots"; Command = "llm_pilots"; LimitMinutes = 30`, 설명 `"Investment_V2 API pilots runner every 10 minutes (display only, writes workspace\outputs\llm only, no order authority)"`.
- 트리거: 매일 00:00 시작 + 10분 반복, 하루 동안. 이 모양 그대로:
  ```powershell
  $trigger = New-ScheduledTaskTrigger -Daily -At "00:00"
  $trigger.Repetition = (New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 1)).Repetition
  ```
- Write-TaskPlan의 TRIGGER 칸은 `"Daily 00:00 local (KST), repeat every 10 minutes for 1 day"`.
- 동작: `-PlanOnly`는 계획만 찍고 0. 시간대가 KST가 아니면 `APPLY_BLOCKED_TIMEZONE`으로 2. 등록해도 작업을 실행하지 않는다. `Unregister-ScheduledTask`·`Set-ScheduledTask`·`Start-ScheduledTask` 없음.

## 구현 요구 — docs/claude/llm-pilots-schedule.json
- JOBS 7개 이름이 모두 있고, 모두 `{"enabled": false, "approved_ref": "", "approved_kst": ""}`. JOBS 순서, 들여쓰기 2칸, LF, 끝 줄바꿈 1개. 다른 키 없음.

## 시험
- 모든 시험은 임시 폴더를 루트로 쓴다. 저장소의 llm_runner.py는 import만 하고, 저장소 루트를 넘겨 실행하지 않는다(실행하면 허용 밖 `workspace/outputs/llm/runner/`가 생긴다). 가짜 `git_show`·가짜 `run_job`만 쓴다. 네트워크·SDK·git 실행이 필요 없다.
- import 방식은 `test_llm_pilot_iccheck.py`와 같게 한다.
- 가짜 켜기 글의 승인 칸 예: approved_ref `"카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9AAAAAAAAAAAAAAAAAAAA · 선택지 A · 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH"`, approved_kst `"2026-11-07 10:00:00 KST"`(now보다 앞).

### test_llm_runner.py
1. (가) **저장소 켜기 파일(형식만)**: `docs/claude/llm-pilots-schedule.json`을 바이트로 읽고 **먼저 `b"\r\n"`을 `b"\n"`으로 바꾼다**(Windows 체크아웃은 CRLF, 실행기가 읽는 커밋본은 LF). 그 바이트로:
   - JSON dict이고 키 목록(순서 포함) = JOB_NAMES.
   - 바꾼 바이트 = `(json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")`(들여쓰기 2칸·끝 줄바꿈 1개 형식).
   - 가짜 git_show로 넘기고 now = 실행 시각(`datetime.now(KST)`)으로 `load_schedule` → status OK, enabled 목록 = 파일에서 enabled가 true인 이름(JOBS 순서).
   - **enabled 값 자체는 단언하지 않는다**(사장 승인으로 시범을 켜도 이 시험이 깨지지 않게). 시험 이름도 `test_repository_switch_file_format`처럼 '모두 꺼짐'을 뜻하지 않게 한다. run_once는 부르지 않는다.
2. (나) **커밋본만 읽음**: 임시 루트의 작업 트리 켜기 파일은 iccheck 켜짐, git_show는 모두 꺼짐 → 07:35에 run_job 안 불림. 반대(작업 트리 꺼짐, git_show 켜짐 + 임시 루트에 가짜 llm_pilot_iccheck.py 있음) → 1번 불림.
3. (다) git_show가 None → 종료 2, SCHEDULE_MISSING, run_job 안 불림, 하루 기록 schedule.status = SCHEDULE_MISSING.
4. (라) **잘못된 켜기 글** 각각 → 종료 2, SCHEDULE_INVALID, 해당 reason, run_job 안 불림: JSON 아님(NOT_JSON) · 최상위 목록(NOT_OBJECT) · 목록 밖 이름 "review"(UNKNOWN_JOB) · enabled가 "true" 문자열(BAD_ENTRY) · 키 하나 더(BAD_ENTRY) · 켜짐인데 approved_ref 빈 글(BAD_REF) · cmsg_ 없음(BAD_REF) · 사장 계정 id 없음(BAD_REF) · approved_kst 형식 틀림(BAD_KST) · now보다 늦은 approved_kst(BAD_KST). 다른 작업이 맞게 켜져 있어도 아무것도 안 돈다.
5. (마) **때**: iccheck 켜짐 — 07:29 안 부름, 07:30 부름, 08:29 부름, 08:30 안 부름(각각 새 임시 루트).
6. (바) **한 칸 한 번**: 07:35에 부른 뒤 07:45에 다시 돌리면 안 부름. 하루 기록에 미리 STARTED 항목이 있으면 안 부름. 다음 날 07:35에는 다시 부름(새 날짜 파일).
7. (사) **두 칸**: news-collect 켜짐 + 가짜 llm_pilot_news.py — 22:05·23:05에 각각 1번씩, 칸 22:00·23:00 두 항목.
8. (아) **NOT_BUILT**: news-submit 켜짐, llm_pilot_news.py 없음 → 19:35에 run_job 안 불림, NOT_BUILT 1개. 19:45에 다시 돌려도 항목은 1개.
9. (자) **argv**: iccheck → `[python, <루트>/manage-us-stock-strategy/scripts/llm_pilot_iccheck.py, "--day", "<날짜>"]`, news-collect → `[..., llm_pilot_news.py, "--phase", "collect", "--day", "<날짜>"]`, cwd = 루트, timeout = 900. 기본 run_job은 모듈의 `subprocess.run`을 가짜로 바꿔 부르고, 받은 인자에 `env`가 없고 `capture_output=True`·`timeout=900`임을 단언한다(실제 프로세스는 띄우지 않음).
10. (차) **실패가 다음을 막지 않음**: 08:15에 iccheck·srccheck-submit 둘 다 켜짐(가짜 스크립트 둘 다 있음). 첫 번째가 TimeoutExpired → TIMEOUT, 두 번째도 불림. 첫 번째가 OSError → `LAUNCH_ERROR:OSError`, 예외 문장 없음. 종료 7 + 출력 `llm-iccheck 2026-11-08 API_ERROR findings=0 dropped=0` → exit_code 7, status API_ERROR.
11. (카) **line 거르기**: 마지막 행이 한글이 섞인 행 / `llm-`로 시작하지 않음 / 201자 이상 → line "", status `EXIT_<코드>`. 마지막 행 뒤 빈 행은 무시.
12. (타) **키 없음**: 가짜 키 문자열(`fake-key-FOR-TEST-7Q9Z`)을 가짜 run_job 출력의 앞 행에 넣어도 하루 기록·실행기 표준 출력에 그 문자열이 없다(마지막 행만 남기므로). llm_runner.py 원문에 `environ`·`anthropic`·`API_KEY`·`INVESTV2` 글자가 없다.
13. (파) **하루 기록 깨짐**: 그날 파일이 JSON 아님 → 종료 2, run_job 안 불림, 파일 바이트 그대로.
14. (하) **dry_run**: 07:35, iccheck 켜짐 → run_job 안 불림, 임시 루트에 runner 폴더 없음, 표준 출력에 `due iccheck 07:30`.
15. (거) **상수 고정**: JOBS가 위 표와 같다(이름·시각·스크립트·args, 순서 포함). CATCH_UP_MINUTES 60, JOB_TIMEOUT_SECONDS 900, CEO_ACCOUNT_ID 값.
16. (너) **main**: run_once가 RuntimeError("secret text")를 내게 바꿔 치면 1, 출력은 `llm-runner ERROR RuntimeError`이고 "secret text" 없음. 정상 한 줄 형식 확인.

### test_llm_runner_task_static.py (PowerShell을 돌리는 반은 `test_journal_score_runner.py`처럼 Windows에서만)
1. 두 .ps1이 ASCII이고 `[CmdletBinding()]`가 있다.
2. 등록 스크립트: `InvestmentV2-LLMPilots`(InvestmentV2- 이름은 이것 하나), `-Daily`, `"00:00"`, `-RepetitionInterval (New-TimeSpan -Minutes 10)`, `-RepetitionDuration (New-TimeSpan -Days 1)`, `PlanOnly`, `Interactive`, `WakeToRun:$false`, `IgnoreNew`, `Korea Standard Time`, `StartWhenAvailable`, `LimitMinutes = 30`, `-Force`, `run_llm_pilots.ps1`, `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File`, 설명 글 그대로. `Register-ScheduledTask` 1번. `if ($PlanOnly)`가 Register보다 앞이고 그 블록에 `exit 0`. `Unregister-ScheduledTask`·`Set-ScheduledTask`·`Start-ScheduledTask`·요일 이름 없음.
3. 래퍼: `llm_runner.py`, `workspace\outputs\llm\runner\logs`, `RUNNER_START`, `RUNNER_END`, `RUNNER_FAIL RUNNER_EXCEPTION`, `exit 4`, `PYTHONUTF8`, 위 키 넘기기 블록의 여섯 행이 앞 공백을 빼고 글자 그대로 있고 `[string]::IsNullOrEmpty($env:INVESTV2_ANTHROPIC_API_KEY)` 첫 등장이 `GetEnvironmentVariable`보다 앞. `$userValue`가 든 행은 그 블록의 세 행뿐. `INVESTV2_ANTHROPIC_API_KEY`가 든 행에 `Write-`·`Add-Content`·`Out-File`·`Set-Content`가 없다. `Invoke-WebRequest`·`Invoke-RestMethod`·`kiwoom`·`Remove-Item`·`Start-Sleep`·`Start-Transcript` 없음(대소문자 무시).
4. 두 스크립트에 `stock-strategy-system`·`workspace\policies`·`workspace/policies`·`decision_journal.json` 없음.
5. **복사본 실행**(`@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), ...)`, journal 시험과 같은 틀): 임시 저장소에 래퍼 복사본과 가짜 `llm_runner.py`(받은 인자와 `INVESTV2_ANTHROPIC_API_KEY`가 비었는지 여부만 YES/NO로 파일에 쓰고, 모드 변수대로 끝남)를 두고 `-RepositoryRoot <임시> -PythonPath sys.executable`로 돌린다. **모든 실행에서 프로세스 환경에 가짜 키를 넣는다**(그래서 사용자 범위 값은 읽히지 않는다).
   - 정상 → 종료 0, 가짜 실행기가 키 있음 YES, 로그에 `RUNNER_START`·`key_present=YES`·`RUNNER_END exit=0`, 임시 폴더 모든 파일·stdout·stderr에 가짜 키 문자열 없음.
   - 모드 종료 2 → 래퍼 종료 2, `RUNNER_END exit=2`.
   - 가짜 llm_runner.py 없음 → 종료 3, `RUNNER_FAIL RUNNER_SCRIPT_NOT_FOUND`.
   - 저장소의 래퍼·실행기는 돌리지 않는다(경로가 임시 폴더 안인지 단언).
- 다른 시험 파일은 바꾸지 않는다. skip은 위 Windows 반 하나만.
- **실행 명령은 이 한 줄만, 글자 그대로 쓴다:** `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_llm_runner*.py"`
  - 앞에 환경 변수나 옵션을 붙이지 않는다. 전체 스위트는 파이프라인이 한다.
  - git은 status·diff·log만 쓴다. `python -c`·파이프·pip는 쓰지 않는다. PowerShell은 시험이 스스로 띄우는 것 말고 직접 부르지 않는다.
  - 저장소에 대고 실행기·래퍼·등록 스크립트를 돌리지 않는다(-PlanOnly·--dry-run 포함).

## 지켜야 할 것
1. 위 7개 파일 밖은 손대지 않는다. 새 파일은 LF로 쓴다.
2. `llm_pilot_common.py`·`llm_pilot_iccheck.py`·기존 등록·래퍼 스크립트와 그 시험을 고치지 않는다.
3. 키 값을 읽으려 하지 않는다. 시험은 가짜 키만 쓴다. 비밀(.env*·토큰·계좌번호) 파일을 열지 않는다.
4. Windows 작업을 등록·실행·변경하지 않는다. 켜기 파일에서 어떤 작업도 켜지 않는다.
5. 주문·키움·일지·원장·예약·정책·상태와 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음. 주문·권한 표지 문자열을 어떤 파일에도 쓰지 않는다.
6. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.
7. 시험은 작업 트리 파일의 줄 끝(LF/CRLF)에 기대지 않는다. 저장소 파일을 바이트로 읽어 비교하거나 글자를 찾는 시험은 먼저 `\r\n`을 `\n`으로 바꾼다(정적 시험의 .ps1 읽기 포함). '새 파일은 LF로 쓴다'(1번)는 그대로다.

## 보고 docs/claude/llm-runner-report.md
- 첫 줄 아래에 '재시도: llm-runner2 — 앞 작업 llm-runner의 병합 멈춤(켜기 파일 CRLF) 고침'을 적는다.
- (a) 만든 파일과 주요 함수(파일:행)
- (b) 시험 이름과 각 단언 요약(PowerShell 반이 돌았는지 skip인지 포함)
- (c) 시험 결과 마지막 3줄
- (d) 시범 스크립트 약속(작업 3~5가 지킬 것): `--day YYYY-MM-DD`와 표의 args를 받는다, 표준 출력 마지막 행은 ASCII `llm-<시범> <날짜> <STATUS> ...`, 같은 날·같은 단계를 두 번 불러도 한 번만 일한다, 실패는 자기 폴더 failed.md에 쓴다, 실행 시간 900초 안.
- (e) 사장님 등록용 두 줄(관리자 아닌 PowerShell, 저장소 폴더에서): `powershell -NoProfile -ExecutionPolicy Bypass -File manage-us-stock-strategy\scripts\register_llm_pilots_task.ps1 -PlanOnly`(계획 확인), 같은 줄에서 `-PlanOnly`를 뺀 줄(등록). 등록해도 켜기 파일이 모두 꺼짐이라 아무 시범도 돌지 않는다는 점.

수량·금액·키 값은 적지 않는다. 주문·권한 표지 문자열도 적지 않고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 허용 파일 7개뿐이고 모두 새 파일이다. 켜기 파일은 7개 모두 꺼짐.
2. 실행기는 커밋본(`git show HEAD:`)만 읽고, 형식이 하나라도 틀리면 전체를 거부한다(UNKNOWN_JOB·BAD_ENTRY·BAD_REF·BAD_KST). 시험이 작업 트리 켜짐/커밋본 꺼짐을 구별한다.
3. 때 계산(0 ≤ 차이 < 60분), 한 칸 한 번(STARTED 포함), NOT_BUILT, 실패가 다음을 막지 않음, stderr 미보관, line 거르기.
4. 키: 실행기는 환경을 읽지 않고 키 이름도 없다. 래퍼는 프로세스 변수가 비었을 때만 사용자 범위 값을 프로세스 변수로 넘기고, 값을 어디에도 쓰지 않는다. 시험이 가짜 키가 어디에도 없음을 단언한다.
5. 등록 스크립트: 이름 하나, 매일 00:00 + 10분 반복 1일, IgnoreNew, 30분 한도, PlanOnly, KST 확인, 실행·삭제·변경 명령 없음.
6. 쓰기는 `workspace/outputs/llm/runner/` 아래 원자적 쓰기와 래퍼 로그뿐이다. 다른 저장소 경로를 쓰지 않는다.
7. 시험이 실제로 각 경로를 만든다(항상 참 단언 아님). 네트워크 없음. 기존 시험 변경 없음.
8. 새 실패 0(파이프라인 checks).
9. 보고서 (a)~(e) 있음. 수량·금액·키 값·표지 없음.
10. (가)가 줄 끝을 `\n`으로 바꾼 뒤 비교하고, enabled 값을 단언하지 않는다. 저장소 파일을 바이트로 읽는 다른 시험도 줄 끝에 기대지 않는다(지켜야 할 것 7).

```dev-run
{"task_id": "llm-runner2", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 150, "builder_timeout_min": 90, "allowed_paths": ["manage-us-stock-strategy/scripts/llm_runner.py", "manage-us-stock-strategy/scripts/run_llm_pilots.ps1", "manage-us-stock-strategy/scripts/register_llm_pilots_task.ps1", "manage-us-stock-strategy/tests/test_llm_runner.py", "manage-us-stock-strategy/tests/test_llm_runner_task_static.py", "docs/claude/llm-pilots-schedule.json", "docs/claude/llm-runner-report.md"], "target_tests": ["test_llm_runner*.py"], "commit_message": "feat(llm-pilot): 10-minute runner, wrapper and task registration script for the Claude API pilots (all jobs off, llm-runner2 - retry of llm-runner with CRLF-safe switch-file test)"}
```
