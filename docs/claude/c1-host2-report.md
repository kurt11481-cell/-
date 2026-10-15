# c1-host2 Builder 보고 (c1-host-status 재실행, 2026-10-15)

- 만든 파일: `manage-us-stock-strategy/scripts/host_status.ps1`(읽기 전용 점검), `manage-us-stock-strategy/scripts/register_host_status_task.ps1`(작업 `InvestmentV2-HostStatus` 화~토 05:50, 제한 10분, register_auto_core_task.ps1과 같은 틀), `manage-us-stock-strategy/tests/test_host_status_static.py`(글 검사 18개). 기존 파일은 고치지 않았다.
- 출력: `workspace\outputs\host-status\LATEST.json`(schema `host-status/v1`, UTF-8 BOM 없음, `.tmp`에 쓴 뒤 교체). 최상위 status = WARN ≥ 1이면 WARN, 아니고 UNKNOWN ≥ 1이면 UNKNOWN, 그 밖은 OK. `read_only: true`, `order_authority: false`. 종료 코드는 항상 0.
- 점검 7개(항목마다 try/catch, 읽기 실패는 그 항목만 UNKNOWN):
  1. `task_logon_type`: 코어 작업 2개의 LogonType·WakeToRun·StartWhenAvailable·State·LastRunTime·LastTaskResult·NextRunTime. 미등록 → WARN. 최근 7일 안 실행의 결과가 0이 아니면 → WARN. Interactive는 note만 적음.
  2. `auto_logon`: Winlogon에서 `AutoAdminLogon` 값 하나만 읽음(레지스트리 키를 읽기 전용으로 열고 이름 지정 GetValue). "1"=OK, 그 밖·없음=WARN.
  3. `power_sleep`: `powercfg /getactivescheme`, `/query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE|HIBERNATEIDLE`의 AC 인덱스(초). 0이 아닌 값 하나라도 → WARN(분 단위 note), 못 읽으면 UNKNOWN.
  4. `update_active_hours`: ActiveHoursStart/End. 없으면 UNKNOWN. 길이 `(E-S+24)%24`, 05시까지 거리 `(5-S+24)%24`, `거리+4 ≤ 길이`면 OK, 아니면 WARN(자정 넘김 8→2는 WARN, 22→10은 OK).
  5. `pending_reboot`: RebootRequired·RebootPending 키 존재 → WARN.
  6. `uptime`, 7. `session`: 마지막 부팅 시각·가동 시간, 실행 사용자·세션 이름/번호. 기록만(OK).
- 테스트: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_host_status_static*.py"` → Ran 18, OK. 스키마 감사 PASS. 검사 내용: ASCII, `[CmdletBinding()]`, Stop 설정, 금지 명령 없음, 읽기용 cmdlet만 호출, powercfg 조회 옵션만, Winlogon 읽기 1건(AutoAdminLogon), 점검 7개 순서, `exit 0`만, 상태 규칙, 활성 시간 수식 11개 경우, register는 이름 1개·PlanOnly가 등록 앞에서 끝남, 두 스크립트에 주문 이름 없음(`order_authority`만 허용). 매개변수 이름 대소문자 덮어쓰기 검사는 test_auto_core_runner.py의 함수를 재사용.
- PowerShell 실행: **실행 못 함** — 헤드리스 세션 권한이 하위 PowerShell 프로세스 실행과 구문 분석 명령을 승인 없이 거부함. 그래서 관측된 status·WARN 항목은 없다. `register_host_status_task.ps1 -PlanOnly`도 같은 이유로 돌리지 못함. 첫 실제 실행 때 JSON에 `checks` 7개가 있는지 확인이 필요하다.
- 해석에서 갈린 부분:
  - 새 .ps1은 ASCII만이라는 규칙 때문에 note는 영어로 썼다("task not registered", "requires logged-on user (Interactive logon)", "update reboot possible 06:15-08:50").
  - 지시문에 없던 WARN 1개 추가: 코어 작업 State가 Disabled면 WARN(꺼진 작업은 조용히 안 돎). 경고를 늘리기만 한다.
  - LastTaskResult가 0이 아니면 "실행 중" 코드도 WARN이 될 수 있으나, 05:50에는 코어 작업이 돌지 않으므로 지시문대로 두었다.
  - 활성 시간 시작=끝이면 길이 0으로 보고 WARN.
  - 전원 계획 이름은 powercfg 출력 그대로(콘솔 인코딩에 따라 한국어가 깨질 수 있음, GUID는 영향 없음).
