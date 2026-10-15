---
id: c1-host2-builder-prompt
title: (재실행 c1-host-status -> c1-host2) C1 호스트 상태 점검 — 자동 운영 PC가 코어 작업을 못 돌리게 하는 설정을 매일 읽어 기록
date: 2026-10-15
class: 일반 변경 내용(새 스크립트 2개 + 테스트 1개, 읽기 전용, 코어 코드 불변). dev-run class authority — 테스트가 주문 표지 글자를 '없어야 함' 검사용으로 담아 파이프라인이 authority로 올리는 것을 미리 적음(원본 실행 10/12 G7 class_ok=true)
decision: 사용자 "결정 c1-host-status: a"(2026-10-15 14:27 KST, Cowork 대화) — 같은 테스트로 새 id 재실행 뒤 -ApproveAuthority 병합. 근거: 관제판 c1-host-status, docs/claude/dev-runs/c1-host-status.md
source: docs/claude/c1-host-status-builder-prompt.md(원본, 본문 그대로) · docs/claude/f-trading-infra-gap-review-2026-10-12.md 1절 발견 2 · 4절 C1
authority: order_authority=false · 키움 호출 없음 · 정책·상태 파일 변경 없음
consumers: 08:50 알림 지시문(docs/claude/scheduled-prompts/auto-core-alert.txt — Cowork가 병합 뒤 별도로 고침) · 관제판 c1-host-status · T5 질문 문서
weekly_user_touch: 0 (일회성: 병합 .\tools\dev-merge.ps1 c1-host2 -ApproveAuthority 1번 + register_host_status_task.ps1 1번)
---

```dev-run
{"task_id": "c1-host2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/host_status.ps1", "manage-us-stock-strategy/scripts/register_host_status_task.ps1", "manage-us-stock-strategy/tests/test_host_status_static.py", "docs/claude/c1-host2-report.md"], "target_tests": ["test_host_status_static*.py"], "commit_message": "feat: read-only host status check and its Windows task registration script (rerun of c1-host-status)"}
```

## 재실행 사유 (Cowork 2026-10-15 14:3x KST)
- 원본 c1-host-status(10/12)는 테스트 통과·Judge PASS·NEEDS_APPROVAL로 끝났지만 결정이 늦어, 그 사이 메인에 docs/claude 밖 변경이 쌓였다. 병합 도구는 이 경우 STOP_BASE_MOVED(non_docs_commits)로 멈추고, 같은 id는 다시 쓸 수 없다(ID_USED_RUN_FOLDER). 그래서 같은 본문을 새 id로 다시 돌린다.
- 본문(목표·바꿀 내용·테스트·Judge 확인 항목)은 원본과 같다. 다른 점은 아래뿐이다.
  - 보고 파일 이름: `docs/claude/c1-host2-report.md`(본문의 `c1-host-status-report.md` 대신).
  - 테스트의 주문 표지 '없어야 함' 검사는 원본 그대로 둔다(사용자 결정 a). 표지 글자를 쪼개 쓰거나 인코딩해 파이프라인 검출을 피하지 않는다. 보고 문서에는 표지 글자를 적지 않는다.
  - Judge 추가 확인 J-g: 테스트 안의 주문 표지 글자는 '없어야 함' 검사용 문자열일 뿐 실제 주문 경로·호출이 아닌가(class_ok 판단 근거).

## 목표
코어 작업(InvestmentV2-AutoCore 06:15 · AutoCoreDecide 07:45)은 "로그온한 사용자 필요 · 깨우기 없음 · 놓친 실행은 켜질 때 실행" 설정이다. PC가 절전·최대 절전에 들어가거나, 업데이트 재부팅 뒤 로그인이 안 되어 있으면 작업이 조용히 안 돈다. 지금은 사람이 PC 설정을 봐야 안다. 매일 아침 PC 설정과 코어 작업 상태를 **읽기만 해서** 한 파일에 쓰고, 이상 여부를 08:50 알림이 읽을 수 있게 한다. 설정을 고치지 않는다.

## 바꿀 내용 (새 파일 3 + 보고 1, 기존 파일은 고치지 않는다)

### 1) `manage-us-stock-strategy/scripts/host_status.ps1`
- Windows PowerShell 5.1에서 돌고, 인자 `-RepositoryRoot`(비면 `$PSScriptRoot\..\..`), `-OutputPath`(비면 `<저장소>\workspace\outputs\host-status\LATEST.json`). 기존 `run_auto_core.ps1`의 인자 처리 방식(5.1에서 `$PSScriptRoot`가 param 기본값에서 비는 문제)을 따른다.
- **읽기만 한다.** 출력 JSON 파일 한 개(와 그 폴더 생성)만 쓴다. 전원 설정·레지스트리·작업 스케줄러·서비스를 바꾸는 명령(`powercfg /change|/setactive|/hibernate`, `Set-*`, `New-ItemProperty`, `Register-*`, `Unregister-*`, `Enable-*`, `Disable-*`, `Restart-*`, `Stop-*`)은 쓰지 않는다. 키움·네트워크 호출 없음.
- 항목마다 try/catch: 읽지 못하면 그 항목은 `value: null, state: "UNKNOWN"`, 이유 한 줄. 한 항목 실패가 전체를 멈추지 않는다. 종료 코드는 항상 0(점검 실패가 작업 실패로 번지지 않게). 출력은 UTF-8(BOM 없음) JSON, 임시 파일에 쓴 뒤 교체(반쯤 쓴 파일을 알림이 읽지 않게).
- 읽을 것(각각 `checks` 배열의 한 원소 `{id, state, value, note}`; state는 `OK`·`WARN`·`UNKNOWN`):
  1. `task_logon_type`: 작업 `InvestmentV2-AutoCore`, `InvestmentV2-AutoCoreDecide`의 `Principal.LogonType`, `Settings.WakeToRun`, `Settings.StartWhenAvailable`, `State`, `LastRunTime`, `LastTaskResult`, `NextRunTime`(`Get-ScheduledTask`/`Get-ScheduledTaskInfo`). 작업이 없으면 WARN("작업 미등록"). 로그온 방식이 Interactive면 note에 "로그온한 사용자 필요"를 적되 그것만으로 WARN은 아니다(현재 설계). `LastTaskResult`가 0이 아니고 `LastRunTime`이 최근 7일 안이면 WARN.
  2. `auto_logon`: `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`의 `AutoAdminLogon` **값 하나만** 읽는다(`1`=OK, 그 밖·없음=WARN, 읽기 실패=UNKNOWN). **`DefaultPassword`·`DefaultUserName` 등 다른 값은 읽지도 출력하지도 않는다.** (자동 로그인이 꺼져 있으면 재부팅 뒤 사용자가 로그인할 때까지 코어 작업이 안 돈다.)
  3. `power_sleep`: 현재 전원 계획의 AC 전원 시 절전 대기 시간(`powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE`의 AC 인덱스, 초; 0=안 함)과 최대 절전 대기(`HIBERNATEIDLE`). 0이면 OK, 0이 아니면 WARN(분 단위로 note). 전원 계획 이름도 value에 포함. `powercfg`는 **조회 옵션만**(`/getactivescheme`, `/query`).
  4. `update_active_hours`: `HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings`의 `ActiveHoursStart`/`ActiveHoursEnd`(시). 없으면 UNKNOWN. 활성 시간이 05:00~09:00을 모두 덮지 않으면 WARN("06:15~08:50 업데이트 재부팅 가능"). 덮는지 계산은 자정을 넘는 구간(예: 8→2)도 올바르게.
  5. `pending_reboot`: `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired` 키 존재, `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending` 키 존재. 있으면 WARN.
  6. `uptime`: 마지막 부팅 시각(`Win32_OperatingSystem.LastBootUpTime`)과 가동 시간(시간). 값만 기록, state는 OK(부팅 직후/오래된 정보는 참고용).
  7. `session`: 지금 스크립트를 돌리는 사용자(`[Security.Principal.WindowsIdentity]::GetCurrent().Name`)와 세션 이름. state OK.
- 최상위 필드: `schema: "host-status/v1"`, `generated_at`(ISO-8601 UTC), `generated_at_kst`, `timezone`(Windows 시간대 ID), `hostname`, `status`(`OK`: WARN·UNKNOWN 모두 0 / `WARN`: WARN ≥ 1 / `UNKNOWN`: WARN 0이고 UNKNOWN ≥ 1), `warn_count`, `unknown_count`, `checks`, `read_only: true`, `order_authority: false`.
- 파일 맨 위 주석에 한 줄: 무엇을 읽고 무엇을 하지 않는지.

### 2) `manage-us-stock-strategy/scripts/register_host_status_task.ps1`
`register_auto_core_task.ps1`을 그대로 본뜬다(같은 PlanOnly·시간대 확인·Interactive·Limited·StartWhenAvailable·깨우기 없음·IgnoreNew·`Register-ScheduledTask -Force`, 같은 출력 형식). 작업 1개:
- 이름 `InvestmentV2-HostStatus`, 화~토 05:50, 제한 10분, `host_status.ps1`을 `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ... -RepositoryRoot ...`로 실행. 설명: "Investment_V2 host status check (read-only): ...".
- 사용자가 1번 실행한다. `-PlanOnly`는 등록하지 않고 계획만 출력. 이 스크립트는 **이 이름의 작업 하나만** 만들거나 덮어쓴다.

### 3) `manage-us-stock-strategy/tests/test_host_status_static.py` (unittest, 표준 라이브러리만)
Linux에서도 돌도록 PowerShell을 실행하지 않고 **파일 글을 검사**한다.
- 두 .ps1이 UTF-8로 읽히고 `[CmdletBinding()]`와 `$ErrorActionPreference = "Stop"`(host_status.ps1은 try/catch 안에서 항목별 처리)를 가진다.
- host_status.ps1에 금지 토큰이 없다: `powercfg /change`, `powercfg /setactive`, `/hibernate`, `Set-ItemProperty`, `New-ItemProperty`, `Register-ScheduledTask`, `Unregister-ScheduledTask`, `Restart-`, `Stop-Service`, `Invoke-WebRequest`, `Invoke-RestMethod`, `kiwoom`, `DefaultPassword`(주석 포함 어디에도 없게; 주석에서는 "other Winlogon values"로 쓴다).
- host_status.ps1에 `AutoAdminLogon`, `STANDBYIDLE`, `HIBERNATEIDLE`, `ActiveHoursStart`, `RebootRequired`, `RebootPending`, `host-status/v1`, `read_only`, `order_authority`가 있다.
- register_host_status_task.ps1에 `InvestmentV2-HostStatus`, `05:50`, `PlanOnly`, `Interactive`, `WakeToRun:$false`가 있고 `InvestmentV2-AutoCore`로 시작하는 작업 이름을 **등록하지 않는다**(문자열은 host_status.ps1에서 읽기용으로만 나온다).
- 파일 안에 주문 관련 이름(주문 API 경로·주문 도구 이름, `order_submit` 등)이 없다. 단 `order_authority`는 허용.

## 테스트
- 대상: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_host_status_static*.py"` → 전부 OK.
- 가능하면(헤드리스에서 PowerShell 실행이 막히지 않으면) `powershell -NoProfile -File manage-us-stock-strategy\scripts\host_status.ps1 -OutputPath <임시 폴더>\host-status.json`을 한 번 돌려 JSON이 열리고 `checks` 7개가 있는지 보고에 적는다. 실행이 막히면 "실행 못 함(이유)"만 적는다 — 만들어 내지 않는다. `register_host_status_task.ps1`은 **`-PlanOnly`로만** 돌린다(등록 금지).
- 저장소 안에 실행 결과 파일을 남기지 않는다(임시 폴더 사용 후 삭제).

## 보고
`docs/claude/c1-host-status-report.md`(한국어, 15줄 안팎): 만든 파일, 검사 항목 7개와 판정 규칙, 테스트 결과, PowerShell 실행 여부와 그때 관측된 `status`·WARN 항목(실행한 경우에만, 값은 있는 그대로), 해석에서 갈린 부분.

## Judge 확인 항목
- J-a 파일 4개 외 변경이 없고 기존 코어 파일(`auto_core*.py`, `run_auto_core.ps1`, `register_auto_core_task.ps1`)이 그대로인가.
- J-b host_status.ps1이 읽기 전용인가(설정·레지스트리·작업을 바꾸는 명령 없음, 출력 파일 외 쓰기 없음), 항목별 실패가 UNKNOWN으로 격리되고 종료 코드가 0인가.
- J-c `AutoAdminLogon` 외 Winlogon 값(특히 비밀번호)을 읽거나 출력하지 않는가.
- J-d 최상위 `status` 계산(OK/WARN/UNKNOWN)과 활성 시간이 자정을 넘는 경우의 계산이 맞는가.
- J-e register 스크립트가 `InvestmentV2-HostStatus` 하나만 다루고 기존 두 코어 작업 설정을 건드리지 않으며, PlanOnly에서 등록하지 않는가.
- J-f 키움 호출·주문 표지·권한 값 변경이 없는가.
