---
id: offsite-bak-builder-prompt
title: PC 밖 백업 — 코드·문서 매일 원격 push + git 밖 기록 파일 매일 OneDrive 압축 사본
date: 2026-10-20
class: 일반 변경(새 스크립트 2 + 기존 점검 스크립트에 항목 1개 추가 + 테스트 2 + 보고 1). 코어·정책·상태 파일 불변, 브로커 호출 없음. 보호 경로(tools/**)·권한 경로(authority-paths.txt) 밖이라 개발 파이프라인
decision: 사용자 "1. 결정 Q2 a(OneDrive)"(2026-10-20 10:24 KST, Cowork 대화) — docs/claude/dual-ai-review-2026-10-20.md 7절 Q2 a "코드·문서 매일 자동 push + 기록 파일 PC 밖 매일 복사", 복사 위치 OneDrive
source: docs/claude/dual-ai-review-2026-10-20.md 2절 F5·5절 E1·E1b · docs/claude/c1-host2-builder-prompt.md(작업 등록·점검 틀)
authority: order_authority=false · 브로커 호출 없음 · 정책·상태 파일 변경 없음(읽기만)
consumers: 05:50 PC 상태 점검(host_status.ps1 8번째 항목 backup_recent, LATEST.json) → 08:50 자동 운영 코어 결과 알림 v2.4(병합·등록·첫 OK 확인 뒤 Cowork가 EXP에 backup_recent 추가 + 백업 전용 문구, 사용자 승인 1번 — 그 전까지 08:50 알림은 없고, host-status LATEST.json과 주간 팀장회의의 PC 점검 항목에는 보일 수 있음(등록 전 'no backup record' 포함)) · 주간 팀장회의 운영관리팀 · 관제판 offsite-bak
weekly_user_touch: 0 (일회성: ① GitHub 원격 비공개 확인 ② .\tools\dev-merge.ps1 offsite-bak ③ register_offsite_backup_task.ps1 ④ 첫 push 인증이 필요하면 터미널 git push 1번 ⑤ 알림 지시문 교체 승인)
---

```dev-run
{"task_id": "offsite-bak", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 90, "builder_timeout_min": 50, "allowed_paths": ["manage-us-stock-strategy/scripts/offsite_backup.ps1", "manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1", "manage-us-stock-strategy/scripts/host_status.ps1", "manage-us-stock-strategy/tests/test_offsite_backup_static.py", "manage-us-stock-strategy/tests/test_host_status_static.py", "docs/claude/offsite-bak-report.md"], "target_tests": ["test_offsite_backup_static*.py", "test_host_status_static*.py"], "commit_message": "feat: daily offsite backup (push current branch + OneDrive zip of untracked records) and host-status backup_recent check"}
```

## 목표
저장소는 원격보다 331커밋 앞서 있고 마지막 push가 2026-09-29다. 결정 일지·대조 원장·상태 백업·자동 코어 기록은 git이 무시하고(.gitignore:31, :46, :47, :53, :157), 연구 기록 등은 추적되지 않아 이 PC에만 있다. 매일 밤 사람 손 없이 ① 지금 브랜치를 원격에 push하고 ② git 밖 기록 파일을 OneDrive에 날짜별 압축 사본으로 남기며, 결과를 파일 하나에 써서 다음 날 05:50 PC 상태 점검이 읽게 한다. 실패는 결과 파일과 점검 항목에 WARN으로 남긴다.

## 바꿀 내용

### 1) 새 `manage-us-stock-strategy/scripts/offsite_backup.ps1`
- Windows PowerShell 5.1, ASCII만(주석 포함), `[CmdletBinding()]`, `$ErrorActionPreference = "Stop"`. 인자: `-RepositoryRoot`(비면 `$PSScriptRoot\..\..` — `host_status.ps1`·`run_auto_core.ps1`의 5.1 처리 방식), `-BackupRoot`(비면 `$env:OneDrive\InvestmentV2-Backup`), `-OutputPath`(비면 `<저장소>\workspace\outputs\backup\LATEST.json`), `-KeepCount`(기본 30), `-SkipPush`, `-SkipCopy`, `-DryRun`(push·복사·삭제 없이 계획만 결과 파일에 씀).
- 파일 맨 위 주석: 하는 일과 하지 않는 일. **테스트 금지 글자를 피해서** 쓴다(예: "no broker call, no forced push, does not commit, does not modify tracked files").
- **외부 명령(git) 호출**: 호출 주변만 `$ErrorActionPreference = "Continue"`로 바꾸고 finally에서 되돌리며, 성패는 `$LASTEXITCODE`로만 판정한다(`run_auto_core.ps1:64-70` 방식 — git은 진행 표시를 stderr로 내서 Stop이면 성공한 push도 실패로 잡힌다). 출력은 `cmd /c ... 2>&1`로 받아 마지막 몇 줄만 note에.
- **A. push** (단계 전체 try/catch, 실패는 `push.state`에만 적고 B는 계속)
  - `git rev-parse --abbrev-ref HEAD` → 브랜치. `HEAD`(분리)면 `SKIPPED`. 브랜치가 `main`이면 `SKIPPED`("main is PR-only", .githooks/pre-push와 같은 규칙). 원격은 `origin` 하나만.
  - 올라갈 경로 목록: `git log -m --name-only --format= HEAD --not --remotes=origin`(원격 브랜치 유무와 상관없이, 범위 안에서 더했다 지운 파일과 병합 커밋 변경까지 포함). 이 목록의 **파일 이름**(경로 마지막 부분)이 `tools/dev_pipeline/devpipe.py`의 `SECRET_NAME_RE`와 같은 규칙 `^(\.env.*|.*\.(pem|key|p12|pfx|ppk)|credentials.*\.json|secrets.*\.json|tokens?\.json|id_(rsa|dsa|ecdsa|ed25519).*)$`(대소문자 무시)에 맞거나, 경로에 `/secrets/` 폴더 또는 `auth.json`이 있으면 push하지 않고 `BLOCKED_SECRET`, 맞은 경로 이름만 note에(내용은 읽지 않음). 이름에 token이 들어간 문서(예: `docs/claude/kiwoom-token-reuse-*.md`)는 대상이 아니다 — 2026-10-20 기준 올라갈 763경로에 이 규칙이 맞는 것 0건.
  - push 명령은 정확히 `git -C <저장소> push origin <브랜치>:refs/heads/<브랜치>` 하나. 강제·미러·전체·태그·삭제·훅 생략 옵션 금지(훅은 그대로 돈다). 환경 변수 `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`(인증 창을 기다리지 않음). push 개별 시간 제한은 두지 않는다(작업 한도 30분이 상한, 멈추면 결과 파일이 낡아 backup_recent 26시간 WARN이 잡는다).
  - 결과: 종료 코드 0 → `OK`, 그 밖 → `FAIL`(git 출력 마지막 3줄을 note에, URL의 `user:pass@`는 `***@`로 가림). 기록: `branch`, `local_sha`, `ahead_before`(`git rev-list --count HEAD --not --remotes=origin`).
- **B. 기록 파일 압축 사본**
  - `-BackupRoot`가 비었거나(`$env:OneDrive` 없음) 그 상위 폴더가 없으면 `copy.state = "FAIL"`("OneDrive folder not found").
  - `onedrive_running`: `Get-Process -Name OneDrive -ErrorAction SilentlyContinue`가 있으면 true. false면 `copy.state`는 그대로 두되 결과 status를 `WARN`으로(파일은 PC에만 있음). note에 "sync completion not verified"를 항상 적는다.
  - 대상(없는 폴더는 건너뛰고 `missing`에 이름):
    - `stock-strategy-system\` 안에서 **추적되지 않는 파일만** — `git ls-files --others --exclude-standard stock-strategy-system`과 `git ls-files --others --ignored --exclude-standard stock-strategy-system`의 합(추적되는 backtests 등은 push로 이미 백업됨). 단 `.tmp_skill_validation/`, `skill-staging/`는 제외.
    - `workspace\outputs\` 아래 폴더 통째로(10개): `auto-core`, `regular-session-closes`(자동 코어 종가 입력, auto_core.py:54 CLOSES_ROOT), `research-records`, `journal-scores`, `decisions`, `reconciliation`, `exposure-review`, `holding-cards`, `status`, `host-status`. 일부러 빼는 것(보고에 이유 1줄): `official-event-intake`(약 278MB, 공식 출처에서 다시 받을 수 있음), `activation`, `dev-runs`.
    - `workspace\private_inputs\`는 **넣지 않는다**(계좌 식별 정보가 있을 수 있어 확인 전까지 제외 — 보고에 "제외" 한 줄).
  - 위 A와 같은 비밀 이름 규칙에 맞는 파일은 넣지 않고 `skipped_secret_files`에 개수만.
  - 임시 폴더(`$env:TEMP` 아래 새 폴더)에 상대 경로를 유지해 복사 → `Compress-Archive`로 `<BackupRoot>\<YYYY-MM-DD>.tmp.zip`(KST 날짜 — PS 5.1 Compress-Archive는 확장자가 .zip이 아니면 거부하므로 `.zip.tmp`를 쓰지 않는다) → 압축을 다시 열어 파일 항목 수가 복사한 파일 수(`Get-ChildItem -Recurse -File`, `-Force` 없이 — Compress-Archive와 같은 기준)와 같으면 `<YYYY-MM-DD>.zip`으로 이름 바꿈(같은 날 파일이 있으면 교체), 다르면 `FAIL`하고 `.tmp.zip`을 지운다. 복사 중 잠긴 파일은 건너뛰고 `locked_files` 개수로 남긴다(1개 이상이면 WARN). 임시 폴더는 끝에 지움.
  - 보관: 오늘 압축이 `OK`일 때만, `<BackupRoot>` 바로 아래에서 이름이 정확히 `^\d{4}-\d{2}-\d{2}\.zip$`인 파일을 날짜 내림차순으로 세어 `KeepCount`개를 넘는 것만 지운다. 다른 이름·폴더는 지우지 않는다.
  - 기록: `path`(OneDrive 경로는 `<OneDrive>`로 줄임), `bytes`, `files`, `entries`, `kept`, `deleted`(이름 목록), `missing`, `skipped_secret_files`, `locked_files`, `onedrive_running`.
- **결과 파일** `<OutputPath>`: UTF-8(BOM 없음) JSON, `.tmp`에 쓴 뒤 교체(`host_status.ps1`의 Replace/Move 방식). 필드 `schema: "backup-status/v1"`, `generated_at`(UTC ISO-8601), `generated_at_kst`, `hostname`, `dry_run`, `push{state, branch, local_sha, ahead_before, note}`, `copy{...}`, `status`(`OK` = push·copy 모두 `OK`이거나 `SKIPPED`이고 onedrive_running true·locked_files 0 / 그 밖 `WARN`), `read_only_repo: true`. 종료 코드는 항상 0.
- 하지 않는 것: git 쓰기 명령(add·commit·reset·checkout·stash·gc·config 쓰기), 저장소 안 파일 쓰기(결과 폴더 `workspace\outputs\backup\` 제외), `stock-strategy-system` 안 쓰기, 브로커·웹 호출(`Invoke-WebRequest`, `Invoke-RestMethod`), 작업 스케줄러 변경.

### 2) 새 `manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1`
`register_host_status_task.ps1`의 틀(PlanOnly·시간대 확인·Interactive·Limited·StartWhenAvailable·깨우기 없음·IgnoreNew·`Register-ScheduledTask -Force`, 같은 출력 형식)을 따르되 **트리거는 `New-ScheduledTaskTrigger -Daily -At 23:50`**(요일 제한 없음 — 그 스크립트의 화~토 Weekly 트리거를 복사하지 않는다). 작업 1개: `InvestmentV2-OffsiteBackup`, 매일 23:50(23:30 DocsCommit 뒤), 제한 30분, `offsite_backup.ps1`을 `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ... -RepositoryRoot ...`로 실행. 이 이름의 작업 하나만 만들거나 덮어쓴다.

### 3) `manage-us-stock-strategy/scripts/host_status.ps1` — 8번째 항목 추가만
- 기존 7개 항목·판정·출력 형식은 그대로. 새 함수 `Get-BackupRecentCheck`를 만들어 `checks` 배열 끝에 `backup_recent` 1개를 더한다(같은 Invoke-Check/try-catch 틀).
- 함수 위치: `Get-SessionCheck` 바로 뒤(기존 테스트가 함수 사이 구간을 잘라 검사하므로 그 사이에 넣지 않는다).
- 읽기: 없음 판정은 `[System.IO.File]::Exists`(기존 메서드 집합 안, `Test-Path`는 쓰지 않음) → 없으면 `WARN`("no backup record"). 있으면 `Get-Content -LiteralPath <저장소>\workspace\outputs\backup\LATEST.json -Raw -Encoding UTF8` + `ConvertFrom-Json`. 깨짐·schema 다름 → `UNKNOWN`. `generated_at`이 **26시간**보다 오래됨 → `WARN`("backup older than 26h" — 23:50 백업, 05:50 점검이라 정상 6시간, 하룻밤 빠지면 30시간). `dry_run` true → `WARN`. `status`가 `OK`가 아님 → `WARN`(push·copy state를 note에). 그 밖 → `OK`. value에 `generated_at_kst`, `push.state`, `copy.state`, `copy.bytes`.
- 최상위 `status`·`warn_count`·`unknown_count` 계산식은 그대로(새 항목도 같이 셈).

### 4) 테스트 (unittest, 표준 라이브러리만, PowerShell을 실행하지 않고 파일 글을 검사)
- 새 `test_offsite_backup_static.py`: 두 새 .ps1이 ASCII이고 `[CmdletBinding()]`·`$ErrorActionPreference = "Stop"`을 가진다. offsite_backup.ps1에 `push origin`, `GIT_TERMINAL_PROMPT`, `GCM_INTERACTIVE`, `--not --remotes=origin`, `backup-status/v1`, `KeepCount`, 날짜 zip 정규식, `BLOCKED_SECRET`, `onedrive_running`, `LASTEXITCODE`, `read_only_repo`가 있다. 금지 글자가 없다: `--force`, `--mirror`, `--all`, `--tags`, `--delete`, `--no-verify`, `git add`, `git commit`, `git reset`, `git checkout`, `git stash`, `Invoke-WebRequest`, `Invoke-RestMethod`, `kiwoom`, `private_inputs\\`(복사 대상 목록에 없음 — 제외 note 문구에는 슬래시 없이 "private inputs"로), `Register-ScheduledTask`. register 스크립트에 `InvestmentV2-OffsiteBackup`, `-Daily`, `23:50`, `PlanOnly`, `Interactive`, `WakeToRun:$false`가 있고 `-Weekly`가 없으며 `InvestmentV2-AutoCore`·`InvestmentV2-HostStatus`·`InvestmentV2-DocsCommit`를 등록하지 않는다.
- **주의(파이프라인 P7, tools/dev_pipeline/README.md)**: 새 줄에 주문 관련 이름이 있거나 `order_authority`와 `true`가 한 줄에 있으면, 또 **지우거나 바꾼 줄에 `order_authority`가 있으면** class가 authority로 올라간다. 그래서 ① 새 파일·새 줄에 주문 이름을 쓰지 않는다(새 테스트에 주문 이름 목록이 필요하면 `from test_host_status_static import ORDER_NAMES, ORDER_IDENTIFIER`로 가져온다) ② `test_host_status_static.py`의 28~30행(ORDER_NAMES·ORDER_IDENTIFIER)·101~110행(test_required_markers_present)과 `host_status.ps1`의 `order_authority` 줄은 **건드리지 않는다** — 새 검사는 별도 test 메서드로 만든다 ③ 결과 JSON에 order_authority 필드를 넣지 않는다. register 스크립트에 틀을 따라 오는 `ORDER_AUTHORITY = $false` 출력 줄은 둬도 된다(P7 대상 아님). 출력·주석의 트리거 문구는 `Daily 23:50`으로(Tue-Sat 문구를 복사하지 않음).
- `test_host_status_static.py`(기존 단언을 약하게 바꾸지 않는다): `CHECK_IDS` 끝에 `"backup_recent"`만 추가, 허용 cmdlet 집합에 `Get-Content`·`ConvertFrom-Json`·`Get-BackupRecentCheck`만 추가(집합이 있는 줄만 고침), `backup-status/v1`·`26` 존재 검사는 **새 test 메서드**로 추가. `[System.IO.File]` 메서드 집합 검사는 그대로 통과해야 한다. **이 세 가지 추가는 단언 약화가 아니다**(새 항목을 덮기 위한 목록 확장).

## 테스트
- 대상: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_offsite_backup_static*.py"`와 `-p "test_host_status_static*.py"` → 전부 OK.
- PowerShell 스크립트는 실행하지 않는다(헤드리스 Builder는 unittest·스키마 감사·git 읽기만 허용 — tools/dev_pipeline/README.md 고정 상수). 실제 동작은 병합 뒤 사용자 등록 → 첫 실행 결과 파일을 Cowork가 읽어 확인한다.

## 보고
`docs/claude/offsite-bak-report.md`(한국어, 20줄 안팎): 만든·바꾼 파일, push 규칙과 비밀 이름 규칙, 복사 대상(제외한 것과 이유 포함)·압축·보관 규칙, host_status 8번째 항목 판정, 테스트 결과, 해석에서 갈린 부분.

## Judge 확인 항목
- J-a 허용 파일 6개 외 변경이 없고 `host_status.ps1`의 기존 7개 항목·판정이 그대로이며(diff가 추가뿐), 테스트 변경이 목록 확장뿐인가.
- J-b push가 정확히 `origin <브랜치>:refs/heads/<브랜치>` 하나이고 강제·미러·전체·태그·삭제·훅 생략 옵션이 없으며, `main`·분리 HEAD에서 push하지 않고, 인증 창을 기다리지 않는가. git 호출 주변만 Continue이고 성패를 `$LASTEXITCODE`로 판정하는가.
- J-c 비밀 이름 규칙이 devpipe `SECRET_NAME_RE`와 같거나 넓고, push 전(`--not --remotes=origin` 범위)과 복사 전 모두 적용되며, 파일 내용을 읽거나 출력하지 않는가.
- J-d 복사 대상이 지시대로인가(stock-strategy-system은 추적 안 되는 파일만, private_inputs 제외), 보관 삭제가 `<BackupRoot>` 바로 아래 `YYYY-MM-DD.zip`에만, 오늘 압축 성공 때만 일어나는가.
- J-e 저장소 추적 파일·`stock-strategy-system`·정책 파일에 쓰지 않고 git 쓰기 명령이 없는가.
- J-f 결과 status 계산(onedrive_running·locked_files 포함)과 `backup_recent`의 26시간·dry_run·status 판정이 맞고, 실패해도 종료 코드 0인가.
- J-g register 스크립트가 매일(-Daily) 23:50 `InvestmentV2-OffsiteBackup` 하나만 다루고 PlanOnly에서 등록하지 않는가. 브로커 호출·주문 표지·권한 값 변경이 없는가.
