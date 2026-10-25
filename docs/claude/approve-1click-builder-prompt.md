# Builder 지시문: approve-1click (사장 터미널용 승인·병합 원클릭 실행 파일, 일반 변경)

사장 결정: "Projects 결정 권장안대로" (사장실 스레드에 직접 입력, 2026-10-25 10:30Z) = 결정 3 "병합 원클릭 실행 파일(승인 검토 5안)을 일반 변경으로 개발 큐에 올린다". 근거: approval-without-cowork-review-2026-10-25.md 5안, claude-projects-diagnosis-2026-10-25.md 4절 F, docs/claude/approval-venue-table-2026-10-25.md.
작업 위치: dev-run 헤드리스 Builder(워크트리). 커밋·푸시·병합은 하지 않는다. 비밀(.env*, 토큰, 계좌번호)은 읽지 않는다. 키움 도구·주문·정책·상태 파일은 건드리지 않는다.

## 목표
사장이 자기 Windows 터미널에서 더블클릭 한 번으로 "승인이 필요한 한 줄"을 실행하게 한다. 지금은 사장이 폴더 이동 + 명령 붙여넣기를 직접 한다. 이 파일은 그 **입력 횟수만** 줄인다. 승인 검사는 하나도 줄이지 않는다.

## 만들 것 (파일 정확히 이 셋 + 보고서)
1. `approve/approve-one-click.cmd` — `%~dp0approve-one-click.ps1`을 `powershell -NoProfile -ExecutionPolicy RemoteSigned -File`로 부른다. 끝나면 창이 바로 닫히지 않게 `pause`. (실행 정책 때문에 못 뜨면 보고에 쓴다. `Bypass`로 바꾸지 않는다.)
2. `approve/approve-one-click.ps1` — **ASCII만**(Windows PowerShell 5.1이 BOM 없는 파일을 ANSI로 읽음). 메뉴 2개:
   - `1` 대조 apply: ① `python manage-us-stock-strategy/scripts/reconcile_broker_state.py show`를 **출력 가로채기 없이** 그대로 실행(사장이 표를 읽는다). ② 사장이 코드를 **직접 입력**(Read-Host). ③ 실행할 정확한 명령 한 줄을 화면에 보여 주고 사장이 `y`를 쳐야 진행. ④ `python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm <입력한 코드> --confirmed-via USER_TERMINAL`을 같은 콘솔에서 실행. 이 스크립트의 자체 확인(콘솔 핸들 검사 + Enter 한 번)은 그대로 작동해야 한다.
   - `2` 권한 병합: ① 사장이 id를 직접 입력(`^[a-z0-9][a-z0-9-]{1,47}$` 검사, 틀리면 중단). ② 정확한 명령 `.\tools\dev-merge.ps1 <id> -ApproveAuthority`를 보여 주고 사장이 `y`. ③ 같은 콘솔에서 실행. dev-merge의 콘솔 검사 + Enter는 그대로.
   - 결정 일지 apply(`portfolio_review_journal.py`)는 `show`/`apply` 인자 형태를 먼저 읽어 보고, 인자가 한 가지로 분명할 때만 메뉴 `3`으로 넣는다. 분명하지 않으면 넣지 말고 보고서에 "확인 필요"로 쓴다.
   - 시작할 때 대화형 콘솔 검사를 한다: 입력·출력 리다이렉트 아님, `$Host.Name -eq 'ConsoleHost'`, `[Environment]::UserInteractive`, 두 표준 핸들의 GetConsoleMode(`tools/dev-merge.ps1`의 hnd-check/hnd-check2 방식과 같게). 하나라도 어긋나거나 검사를 못 만들면 중단(fail closed).
   - 작업 폴더는 스크립트 위치의 상위(저장소 루트)로 잡는다. 하드코딩한 사용자 경로를 쓰지 않는다.
3. `manage-us-stock-strategy/tests/test_approve_one_click.py` — 파일 내용을 읽어 확인하는 정적 테스트(실행은 하지 않음). 아래 "하지 않는 것"이 파일에 없음을 확인한다.
4. `docs/claude/approve-1click-report.md` — 보고서(아래 "보고").

## 하지 않는 것 (스크립트에 있으면 안 됨 — 테스트가 확인)
- 코드를 만들거나, 파일·환경변수·클립보드·인자·제안 JSON에서 읽어 채우는 일. 코드는 오직 사장이 그 자리에서 친 입력.
- `propose`(키움 읽기) 실행, 키움·네트워크 호출, `Get-Clipboard`, 제안 파일 직접 읽기.
- 자식 프로세스의 입력·출력을 파이프·리다이렉트·`Start-Process -RedirectStandard*`로 가로채기(자식의 콘솔 확인을 깨뜨림). `y`·Enter를 대신 보내는 일.
- `-ApproveAuthority`를 사장 입력 없이 붙이는 일, 기본값으로 `y` 처리, 반복·자동 재시도.
- 기존 스크립트(`reconcile_broker_state.py`, `portfolio_review_journal.py`, `tools/dev-merge.ps1`, `apply_user_confirmed_broker_snapshot.py`) 수정. 이 파일들은 allowed_paths에 없다.
- CLAUDE.md, 정책, 상태, 설정(`.claude/**`) 수정. 사용 안내는 보고서에만 쓴다.

## 먼저 확인
- `.gitignore`/`.gitattributes`가 `approve/`의 `.cmd`·`.ps1`을 무시하거나 줄바꿈을 바꾸는지(`git check-ignore -v`). 무시되면 BLOCKED.md로 멈춘다.
- 줄바꿈은 CRLF(`.cmd`, `.ps1`). 일괄 변환 금지.
- `reconcile_broker_state.py`의 `apply` 인자(`--confirm`, `--confirmed-via`)와 `tools/dev-merge.ps1` 머리말(3~9행)을 읽고 그대로 따른다.

## 테스트
`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_approve_one_click*.py"` 가 통과. 전체 스위트는 새 실패 0(기준선 대비).

## 보고
`docs/claude/approve-1click-report.md`: 만든 파일과 sha256, 메뉴별 실행되는 정확한 명령, 콘솔 검사 구현이 dev-merge와 같은 조건인지 대조, 하지 않는 것 목록이 테스트로 확인되는 방법, 일지 apply 메뉴를 넣었는지와 이유, 사장 사용법 5줄 이내(더블클릭 → 메뉴 번호 → 코드/ID 입력 → y → Enter), 확인 필요.

## Judge 확인 항목
1. 파일이 allowed_paths 안 네 개뿐이고 기존 스크립트·CLAUDE.md·`.claude`·정책·상태에 변경이 없다.
2. 코드·id는 사장 입력(Read-Host)에서만 온다. 파일·환경·클립보드·인자에서 오는 경로가 없다.
3. 자식 프로세스의 표준 입출력이 가로채이지 않아 `reconcile_broker_state.py apply`와 `dev-merge.ps1 -ApproveAuthority`의 자체 콘솔 검사와 Enter가 그대로 작동한다. 래퍼가 Enter·`y`를 대신 보내는 곳이 없다.
4. 시작 시 대화형 콘솔 검사가 있고, 검사를 못 만들면 중단한다.
5. 실행 직전 정확한 명령이 표시되고 `y` 없이는 실행되지 않는다.
6. `propose`, 키움, 네트워크, 클립보드가 없다. 주문·권한 표지(`/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`)가 추가된 줄에 없다.
7. ASCII 전용, CRLF, `.cmd`가 `Bypass`를 쓰지 않는다.
8. 이 변경이 승인 검사를 약화하지 않는다(권한 확대 없음): 사장이 지금 손으로 하는 입력 순서와 같거나 더 엄격하다.

```dev-run
{"task_id": "approve-1click", "class": "general", "builder_model": "sonnet", "builder_effort": "high",
 "max_turns": 80, "builder_timeout_min": 45,
 "allowed_paths": ["approve/approve-one-click.cmd",
                   "approve/approve-one-click.ps1",
                   "manage-us-stock-strategy/tests/test_approve_one_click.py",
                   "docs/claude/approve-1click-report.md"],
 "target_tests": ["test_approve_one_click*.py"],
 "commit_message": "feat(approve): one-click launcher for user-terminal approvals"}
```
