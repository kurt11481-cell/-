---
id: evo-s3-builder-prompt
title: 주간 채점 실행기 결함 수정 — WEEKLY_LATEST.json이 안 생김(키 확인 .Contains) + 예외·실패를 상태·종료 코드로 + PC 상태 점검이 주간 작업 실패를 알림 + 실제 PowerShell 실행 테스트
date: 2026-10-18
class: 일반 변경(dev-run class general). 실행기 1개 + PC 상태 점검 스크립트 1개(작업 이름 1개 추가) 수정 + 새 테스트 1개 + 기존 정적 테스트 2개(깨질 때 최소 수정 + host_status 목록 검사 1개 추가) + 보고 1개. 채점기·등록 스크립트·코어·정책·상태·일지·스키마·예약 지시문 불변. 권한 경로 파일 없음
decision: 사용자 2026-10-18 10:23 KST "f-evo-loop 진행 … ① 10/18(일) 09:20 첫 예약 실행 뒤 … WEEKLY_LATEST.json status OK 확인" — 확인 결과 결함(docs/claude/f-evo-loop-s1-weekly-check-2026-10-18.md). CLAUDE.md Goal: 막힌 자동화는 결함으로 고치고, 예외는 자동 알림으로
source: docs/claude/f-evo-loop-s1-preregistration-2026-10-16.md 5절(실패 보이기·보고서 고르기)·7절(운영 완료 기준) — 이 지시문과 다르면 사전 등록이 우선
authority: order_authority=false · quantity_authority=none · 키움 호출 없음 · 정책·상태·일지 쓰기 없음
consumers: Windows 작업 InvestmentV2-JournalScore(일 09:20) · InvestmentV2-HostStatus(화~토 05:50) → 08:50 알림 ⑭(auto-core-alert.txt v2.3, 바뀌지 않음) · Cowork 주간 확인 · 관제판 f-evo-loop
weekly_user_touch: 0 (일회성: .\tools\dev-merge.ps1 evo-s3 1번)
---

```dev-run
{"task_id": "evo-s3", "class": "general", "builder_model": "sonnet", "builder_effort": "high", "max_turns": 90, "builder_timeout_min": 50, "allowed_paths": ["manage-us-stock-strategy/scripts/run_journal_score.ps1", "manage-us-stock-strategy/scripts/host_status.ps1", "manage-us-stock-strategy/tests/test_journal_score_runner.py", "manage-us-stock-strategy/tests/test_journal_score_task_static.py", "manage-us-stock-strategy/tests/test_host_status_static.py", "docs/claude/evo-s3-report.md"], "target_tests": ["test_journal_score_*.py", "test_host_status*.py", "test_score_learning*.py"], "commit_message": "fix(score runner): weekly runner writes WEEKLY_LATEST on Windows PowerShell 5.1, fails with a nonzero exit, and host status watches the weekly task"}
```

## 무슨 일이 있었나 (Cowork 2026-10-18 10:2x~12:xx KST, 원문 확인)

- 10/18 09:20 KST 첫 예약 실행이 돌았다. 채점기는 정상으로 끝났다.
  - 로그 `workspace/outputs/journal-scores/logs/20261018T002001Z.log`: `RUNNER_START` 뒤 채점기 출력이 있고, 마지막 줄은 채점기의 "채점 결과 파일: …\20261018T002001Z\journal-scores.json"이다. **`RUNNER_END` 줄이 없다.**
  - 보고서 `20261018T002001Z/journal-scores.json`은 정상이다: `learning` 있음, `learning.errors` 빈 목록, NaN 없음.
  - **`WEEKLY_LATEST.json`도 `WEEKLY_LATEST.json.tmp`도 없다.** 폴더 시각으로 보면 52행 WriteAllText 전에 멈췄다.
- 원인(가장 유력): `run_journal_score.ps1` 78행 `$Object.Contains($Name)`.
  - Windows PowerShell 5.1에서는 59~62행의 JavaScriptSerializer가 읽기를 맡는다. 이것은 `Dictionary[string,object]`를 돌려준다(70행). 이 형에는 공개 `Contains`가 없다.
  - 그래서 메서드 호출 오류가 난다(5.1에서의 정확한 형·문구는 확인 필요). 16행 `$ErrorActionPreference = "Stop"`이고 146행 호출이 try 밖이라, 스크립트가 173행(Write-WeeklyLatest)과 174행(RUNNER_END) 전에 끝난다.
- Cowork 재현(클라우드, PowerShell 7.4.6, Windows 5.1 아님):
  - `Dictionary[string,object]`에 `.Contains('learning')` → "Cannot find an overload for "Contains" and the argument count: "1"".
  - 실행기 사본에 Dictionary를 돌려주는 가짜 serializer를 넣으면 실제와 증상이 같다: 보고서 폴더 생김, WEEKLY_LATEST·.tmp·RUNNER_END 없음, 종료 코드 1.
  - ConvertFrom-Json 경로(PSCustomObject)는 status OK다.
  - 같은 PS 7에서 `$x.Keys -ccontains 'learning'`은 Dictionary`2·Hashtable·OrderedDictionary 모두 True, 없는 키는 False다. `ContainsKey`는 OrderedDictionary에서 실패한다.
- 이 결함이 빠져나간 이유:
  - 실행기 테스트가 정적 검사뿐이었다(`test_journal_score_task_static.py` 1행 "PowerShell is never run here").
  - 병합 뒤 실제 자료 확인(10/16)은 파이썬 채점기만 돌렸다. Cowork는 Windows PowerShell을 돌릴 수 없다. 그래서 실행기는 첫 예약 전에 한 번도 돌지 않았다(logs/에는 10/18 로그 하나뿐).
  - 실패를 자동으로 알리는 곳도 없었다. 예약 지시문 10개 중 WEEKLY_LATEST·JournalScore를 읽는 것은 0개이고, PC 상태 점검(`host_status.ps1` 17행)은 코어 작업 2개만 본다.

## 목표

1. 주간 실행기가 Windows PowerShell 5.1에서 실제 보고서를 읽고 `WEEKLY_LATEST.json`을 쓰게 한다.
2. 예상 못 한 예외와 모든 FAIL이 로그·상태 파일·**작업 종료 코드**에 남게 한다.
3. 이미 승인된 PC 상태 점검이 주간 작업도 코어 작업과 같은 규칙으로 보게 해서(미등록·사용 안 함·7일 안 0 아닌 마지막 결과 = WARN), 08:50 알림 ⑭가 자동으로 알리게 한다. 알림 지시문은 바꾸지 않는다. ⑭ 꼬리 문구는 "코어 작업이 안 돌 수 있음, Cowork 확인"으로 고정이다(auto-core-alert.txt 158행). 그래서 JournalScore 항목에도 이 꼬리가 붙지만, 항목에 작업 이름이 보이므로 그대로 둔다(코어 영향 없음, 사전 등록 323행).
4. 1·2를 Windows PowerShell로 실제로 실행하는 테스트로 확인한다.

## 바꿀 내용

### 1) `manage-us-stock-strategy/scripts/run_journal_score.ps1`

- **(a) 키 확인:** `Get-JsonValue`의 사전 분기에서 `$Object.Contains($Name)`를 `$Object.Keys -ccontains $Name`(대소문자 구분)으로 바꾼다. 같은 효과의 다른 방법을 쓰면 보고서에 이유를 적는다. Dictionary`2·Hashtable·OrderedDictionary·PSCustomObject 모두에서 맞아야 한다.
- **(b) 예외도 상태로:** `RUNNER_START`를 쓴 뒤의 본문(채점기 실행·보고서 고르기·상태 쓰기)에서 예외가 나면:
  - 로그에 한 줄을 쓴다: `RUNNER_FAIL RUNNER_EXCEPTION type=<예외 형 이름> message=<메시지>`(ASCII로. 글자가 깨져도 됨).
  - `WEEKLY_LATEST.json`을 status FAIL, reason `RUNNER_EXCEPTION`, 그때까지 아는 exit_code·report_path로 쓴다. 파이썬이 끝나기 전에 예외가 났으면 exit_code는 -1로 쓴다(`[int]` 매개변수가 null을 0으로 바꿔 성공처럼 보이지 않게). 머리 주석에 적는다.
  - 이 쓰기마저 실패하면 로그 줄만 남긴다. 두 번째 예외로 로그 줄이 사라지면 안 된다.
  - 프로세스 종료 코드는 4다.
- **(c) FAIL이면 종료 코드도 0이 아니다:** status가 FAIL인데 파이썬 종료 코드가 0이면(지금은 `LEARNING_FAILED`가 이 경우) 프로세스 종료 코드를 1로 한다. 작업 스케줄러의 마지막 결과가 FAIL을 보이게 하려는 것이다. `WEEKLY_LATEST.json`의 `exit_code` 필드는 지금처럼 파이썬 종료 코드다.
- 머리 주석(11~14행)의 FAIL 목록과 종료 코드 설명을 (b)·(c)에 맞게 고친다.
- 그 밖의 동작은 그대로 둔다: 보고서 고르기 규칙(시작 뒤 생긴 폴더 중 learning 있는 가장 늦은 것), status·reason 값과 필드, 종료 코드 0·1·3, 임시 파일 → Move-Item.
- **49행 `order_authority = $false` 줄은 지우거나 옮기거나 고치지 않는다.** 지우거나 바꾼 줄에 `order_authority`가 있으면 파이프라인이 권한 작업으로 올린다(tools/dev_pipeline/README.md 권한 경로). 새 줄에도 `order_authority`를 쓰지 않는다. 예외 경로의 상태 쓰기는 기존 `Write-WeeklyLatest`를 다시 쓴다.
- 파일은 ASCII만 쓴다. `[CmdletBinding()]`을 유지한다. Remove-Item·Start-Sleep·네트워크 명령은 쓰지 않는다.

### 2) `manage-us-stock-strategy/scripts/host_status.ps1`

- 17행 작업 목록에 `"InvestmentV2-JournalScore"`를 더한다. 기존 두 이름과 순서는 그대로다.
- 주석(8~14행)에 **영어로** 한 줄을 더한다. 이 파일은 ASCII만 쓴다(`test_host_status_static.py` 35~36행이 ASCII로 읽음 — 한국어 한 글자면 그 테스트 전부가 오류). 예: `# InvestmentV2-JournalScore (weekly, f-evo-loop) uses the same rules: not registered, disabled, or a nonzero last result within 7 days gives WARN.`
- 이것만 바꾼다. 검사 id·필드·상태 규칙(미등록 116~118행, Disabled 133행, 7일 창 139~142행)·종료 코드는 그대로다. 그래서 08:50 알림의 `host.py`(auto-core-alert.txt 82~107행, ⑭ 규칙 158행)가 고치지 않고 그대로 읽는다: 일요일 실행이 0이 아닌 결과로 끝나면 화요일 05:50 점검부터 `task_logon_type` 검사가 WARN이 되고 ⑭ 한 줄이 나간다.
- 나중에 주간 작업을 끄거나 지우면 이 목록 때문에 ⑭가 화~토 매일 나간다. 끌 때는 같은 변경에서 이 이름을 뺀다(보고서 "남은 위험"에 적는다).
- `"order_authority = $false"`·`read_only` 줄은 건드리지 않는다.

### 3) `manage-us-stock-strategy/tests/test_journal_score_runner.py` (새 파일)

- `test_auto_core_runner.py`의 `RunnerCopyBehaviourTests`(143~200행) 방식을 그대로 따른다.
  - skip 조건은 이것 하나뿐이다: `@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), ...)`. pwsh 유무로 skip하거나 pwsh로 돌리지 않는다.
  - 임시 폴더에 가짜 저장소를 만든다. 실행기 **사본**과 가짜 `manage-us-stock-strategy/scripts/score_decision_journal.py`를 둔다.
  - `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File <사본> -RepositoryRoot <임시> -PythonPath <sys.executable>`로 실행한다.
  - 실제 저장소 파일은 실행하지 않는다. 임시 폴더 밖에 쓰지 않는다. 사본 경로를 assert로 확인한다.
- 가짜 채점기는 환경 변수나 인자로 정한 대로 `workspace/outputs/journal-scores/<UTC시각>/journal-scores.json`을 쓰고 정한 코드로 끝난다.
- 경우(각각 WEEKLY_LATEST.json의 status·reason·learning_present·learning_failed·exit_code, 로그의 RUNNER_END 줄, 프로세스 종료 코드를 확인):
  1. learning 있음, errors 빈 목록, 종료 0 → OK, 종료 0. **10/18 결함의 회귀 테스트다.**
  2. learning 없는 보고서만 있음 → FAIL `NO_LEARNING_REPORT`, 종료 1
  3. learning.errors에 `LEARNING_FAILED…` 사유, 채점기 종료 0 → FAIL `LEARNING_FAILED`, 필드 exit_code 0, **프로세스 종료 1**
  4. 보고서 OK + 채점기 종료 2 → FAIL `SCORER_EXIT`, 종료 2
  5. JSON이 아닌 보고서만 있음 → FAIL `REPORT_NOT_JSON`, 종료 1
  6. 실행 시작 전에 이미 있던 learning 보고서 폴더(이름이 시작 시각보다 이른 것)는 고르지 않는다
  7. 예외 경로(b): 임시 저장소에 `workspace/outputs/journal-scores/WEEKLY_LATEST.json.tmp` **폴더**를 미리 만들고 실행한다. 그러면 52행 WriteAllText가 예외를 내고, catch 안의 두 번째 쓰기도 실패한다. `RUNNER_FAIL RUNNER_EXCEPTION` 로그 줄, 종료 4, WEEKLY_LATEST.json 없음을 확인한다. 이 방법이 안 되면 정적 검사(catch 블록, `RUNNER_EXCEPTION`·`RUNNER_FAIL` 글자, `exit 4`)로 하고 보고서에 적는다. 실행기에 시험용 스위치를 새로 넣지 않는다.
- 경우 1의 보고서 JSON은 learning 블록 안에 중첩 객체·배열(실제 보고서 모양: `counts`·`epochs` 객체, `buckets` 배열)을 넣는다. Windows PowerShell 5.1은 System.Web.Extensions가 있어 JavaScriptSerializer 경로를 쓴다. 이 테스트가 실제 운영 경로를 시험한다.
- ConvertFrom-Json 대체 경로(71행)는 5.1에서 닿지 않으므로 경우에서 뺀다(시험용 스위치를 넣지 않는다).
- 파이프라인은 Windows에서 돌기 때문에 이 테스트는 실제로 실행된다. 기준선보다 skipped가 늘면 실패로 판정된다(tools/dev_pipeline/README.md 고정 상수).

### 4) 기존 정적 테스트 (`test_journal_score_task_static.py`·`test_host_status_static.py`)

- 바꾼 스크립트 때문에 기존 검사가 깨질 때만 최소로 고친다. 지우거나 약하게 만들지 않는다.
  - 실행기의 `Get-JsonValue -Object $learning -Name "errors"`·`-Name "reason"`·`StartsWith("LEARNING_FAILED")`·`order_authority` 줄 1개 검사는 그대로 통과해야 한다.
- `test_host_status_static.py`에 `"InvestmentV2-JournalScore"`가 목록에 있는지 보는 검사를 하나 더한다.

## 반드시 지킬 것 (Judge가 본다)

- 고칠 파일은 allowed_paths 6개뿐이다. 채점기 `score_decision_journal.py`, 두 등록 스크립트, 코어(`auto_core*`), 정책·상태·일지·스키마, 예약 지시문(docs/claude/scheduled-prompts/)은 그대로다.
- 실행기가 쓰는 곳은 지금처럼 `workspace\outputs\journal-scores\WEEKLY_LATEST.json`(임시 파일 경유)과 `logs\<UTC시각>.log`뿐이다. PC 상태 점검이 쓰는 곳도 그대로다.
- 셸 명령: 허용된 명령은 `python -m unittest …`, 스키마 감사, `git status|diff|log`뿐이다. PowerShell은 Builder가 직접 실행하지 않는다. unittest 안의 subprocess로만 돈다. 명령 문자열에 `auto_core.py` 글자를 넣지 않는다.
- 새 파일·바뀐 줄에 주문 도구·주문 API 이름, 정지 스위치 글자, 권한 값 표지를 쓰지 않는다(금지 검사용 문자열로도 쓰지 않음).

## 테스트

- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_journal_score_*.py"` — 전부 OK. Windows에서 새 테스트가 skip이 아니라 실제로 돌아야 한다.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_host_status*.py"` — 전부 OK.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_score_learning*.py"` — 전부 OK(채점기 불변 확인).
- 실제 저장소 자료로 실행기·채점기·PC 상태 점검을 돌리지 않는다.

## 보고 (`docs/claude/evo-s3-report.md`, 한국어 15줄 안팎)

- 바꾼 파일과 줄
- 고치기 전 실행기로 경우 1을 돌렸을 때 실패했는지와 그 오류 형·문구. Windows 5.1에서 원인이 같은지 확인하는 증거다. 가능하면 한 번 확인하고, 못 했으면 "확인 못 함"
- 테스트 결과(대상, Ran 수, skip 수, 새 실패 수)
- 예외 경로(7번)를 어떻게 시험했는지
- 남은 위험

## Judge 확인 항목

- J-a: 바뀐 파일이 allowed_paths 6개뿐인가. 채점기·등록 스크립트·코어·정책·상태·일지·스키마·예약 지시문이 그대로인가.
- J-b: `Get-JsonValue`가 Dictionary[string,object](JavaScriptSerializer 결과)에서 예외 없이 키 유무를 맞게 판단하는가. 대소문자를 구분하는가.
- J-c: RUNNER_START 뒤 예외가 로그 `RUNNER_FAIL RUNNER_EXCEPTION` 줄, WEEKLY_LATEST status FAIL(reason RUNNER_EXCEPTION), 종료 4로 남는가. 파이썬이 끝나기 전 예외면 exit_code -1인가. 상태 쓰기가 다시 실패해도 로그 줄이 남는가. 머리 주석과 맞는가.
- J-d: status FAIL이면 프로세스 종료 코드가 항상 0이 아닌가(LEARNING_FAILED + 파이썬 0 → 1). `exit_code` 필드는 파이썬 코드 그대로인가.
- J-e: 기존 동작(보고서 고르기 규칙, status·reason 값, 필드, 종료 코드 0·1·3·파이썬 코드, 임시 파일 → Move-Item)이 그대로인가. 49행 `order_authority` 줄이 그대로이고 새 `order_authority` 줄이 없는가.
- J-f: `host_status.ps1` 변경이 작업 이름 1개 추가와 영어 주석 1줄뿐이고 파일이 ASCII인가. 검사 id·필드·상태 규칙(미등록·Disabled·7일 창)·종료 코드가 그대로라서 auto-core-alert.txt의 host.py가 고치지 않고 읽는가.
- J-g: 새 테스트가 실행기 **사본**만 임시 폴더에서 돌리고, skip 조건이 `os.name == "nt"` + powershell.exe뿐이며, 경우 1~7을 확인하는가(7은 실행 또는 정적 검사). 경우 1이 중첩 객체·배열이 있는 learning 블록을 쓰는가.
- J-h: 기존 정적 테스트가 지워지거나 약해지지 않았는가. 두 스크립트가 ASCII인가.
- J-i: 키움·네트워크 호출, 주문 표지, 권한 값 변경이 없는가.
