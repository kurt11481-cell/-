# dev-run approve-1click — FAIL

- 시각(UTC): 2026-10-25T10:40:25Z → 2026-10-25T11:16:01Z
- 기준 커밋(base): `7f98f28c437b0343eaa901e12fdcca390f072342` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ORDER_MARKER:/api/us/ordr, ORDER_MARKER:order_submit, ORDER_MARKER:ust2000, ORDER_MARKER:ust2001)
- 상태: **FAIL** · 재시도: 1
- 테스트: 기준선 Ran 3353 · 실패 31 → 변경 후 Ran 3366 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: judge_fail_after_fix
- 다음: `see docs/claude/dev-runs/approve-1click.md`

## 바뀐 파일

- `approve/approve-one-click.cmd`
- `approve/approve-one-click.ps1`
- `docs/claude/approve-1click-report.md`
- `manage-us-stock-strategy/tests/test_approve_one_click.py`

## Judge 보고 원문 (2회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | FAIL | 메뉴 1·2와 콘솔 검사는 구현됐습니다(approve/approve-one-click.ps1:23-49, 68-96). 하지만 지시문이 요구한 CRLF가 없습니다(task-prompt.md:30). 보고서도 sha256을 비워 두었고 CRLF를 "미충족"이라고 스스로 적었습니다(docs/claude/approve-1click-report.md:9, 13-19). |
| G2 범위 | PASS | 바뀐 파일은 allowed_paths 안의 4개뿐이고 모두 새 파일(A)입니다(changed-files.txt:1-4, checks.json:17-22, 42-48). |
| G3 주문·체결 추정 | PASS | ps1에 키움 호출, 주문 도구, 체결 추정 코드가 없습니다. 실행하는 것은 기존 스크립트 두 개뿐입니다(approve/approve-one-click.ps1:73, 83, 94). |
| G4 정책·상태 쓰기·fail-closed | PASS | 새로 쓰는 경로가 없습니다. 상태에 쓰는 것은 기존 USER_TERMINAL apply뿐이고, 이 apply는 자체 콘솔 검사를 그대로 합니다(reconcile_broker_state.py:286-291). python 없음, 형식 오류, 취소, 알 수 없는 메뉴는 모두 STOP으로 끝납니다(ps1:69, 74, 77, 82, 88, 93, 98). |
| G5 비밀 | PASS | ps1에 .env, `$env:`, 토큰, 계좌를 읽는 코드가 없습니다(ps1:13-99). 테스트도 이를 확인합니다(test_approve_one_click.py:71). |
| G6 테스트 | FAIL | 줄바꿈 테스트가 CRLF가 아니라 "섞이지 않음"만 확인합니다. 그래서 요구 사항(CRLF)을 어긴 LF 파일도 통과합니다(test_approve_one_click.py:45-49). 다른 새 동작은 정적 테스트 13개가 확인하고 모두 통과했습니다(checks.json:110-118). |
| G7 class | PASS (class_ok=true) | 주문 단계, 예산, 상한, 대조 불변 조건, quantity_authority 값은 하나도 바뀌지 않았습니다. checks.json의 authority 판정(checks.json:50-56)은 테스트 안의 금지어 문자열(test_approve_one_click.py:87) 때문에 생긴 것입니다. |
| G8-1 파일 4개만 | PASS | changed-files.txt:1-4. 기존 스크립트, CLAUDE.md, `.claude`, 정책, 상태에는 변경이 없습니다(checks.json:23-49, modified/deleted가 비어 있음). |
| G8-2 입력은 Read-Host만 | PASS | `$code`(ps1:76)와 `$id`(ps1:87)는 각각 한 번만, Read-Host로만 값을 받습니다. param, `$args`, 파일, 클립보드에서 읽지 않습니다. |
| G8-3 표준 입출력 비가로채기 | PASS | 파이프나 리다이렉트 없이 `&`로 직접 실행합니다(ps1:73, 83, 94). y나 Enter를 대신 보내는 코드도 없습니다. 자식 쪽 검사(dev-merge.ps1:43-87, portfolio_review_journal.py:846-856)는 그대로 작동합니다. |
| G8-4 시작 시 콘솔 검사 | PASS | ps1:23-49의 조건이 dev-merge.ps1:43-73과 같습니다. Add-Type이 실패하면 `$false`가 되어 NOT_INTERACTIVE로 멈춥니다. |
| G8-5 명령 표시 후 y | PASS | 표시(ps1:80) → y(81-82) → 실행(83), 표시(ps1:91) → y(92-93) → 실행(94) 순서이고, y가 기본값으로 처리되지 않습니다. |
| G8-6 금지어와 주문·권한 표지 | FAIL | 추가된 줄 test_approve_one_click.py:87에 `/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`가 그대로 들어 있습니다. 이 때문에 일반 변경이 authority로 분류됐습니다(checks.json:50-56, devpipe.py:122, 852). |
| G8-7 ASCII·CRLF·Bypass 없음 | FAIL | ASCII이고 Bypass도 없습니다(cmd:3). 하지만 approve/의 `.cmd`와 `.ps1`에 `\r`이 하나도 없어(Grep으로 0건 확인) LF 전용입니다. 비교용 tools/dev-merge.ps1에는 `\r`이 136개 있어 CRLF입니다. |
| G8-8 승인 검사 약화 없음 | PASS | 입력 순서는 사장 입력(코드/ID) → 명령 표시 → y → 자식의 콘솔 검사와 Enter입니다. 코드는 여전히 confirm_code와 대조됩니다(apply_user_confirmed_broker_snapshot.py:275). 지금 손으로 하는 순서보다 단계가 더 많습니다. |

```json
{"verdict": "FAIL", "class_ok": true, "items": [
 {"id": "G1", "result": "FAIL", "evidence": "task-prompt.md:30; docs/claude/approve-1click-report.md:9,13-19"},
 {"id": "G2", "result": "PASS", "evidence": "changed-files.txt:1-4; checks.json:17-22"},
 {"id": "G3", "result": "PASS", "evidence": "approve/approve-one-click.ps1:73,83,94"},
 {"id": "G4", "result": "PASS", "evidence": "approve/approve-one-click.ps1:69-98; reconcile_broker_state.py:286-291"},
 {"id": "G5", "result": "PASS", "evidence": "approve/approve-one-click.ps1:13-99; test_approve_one_click.py:71"},
 {"id": "G6", "result": "FAIL", "evidence": "manage-us-stock-strategy/tests/test_approve_one_click.py:45-49"},
 {"id": "G7", "result": "PASS", "evidence": "checks.json:50-56 (test literals only); test_approve_one_click.py:87"},
 {"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1-4; checks.json:42-48"},
 {"id": "G8-2", "result": "PASS", "evidence": "approve/approve-one-click.ps1:76,87"},
 {"id": "G8-3", "result": "PASS", "evidence": "approve/approve-one-click.ps1:73,83,94; tools/dev-merge.ps1:43-87; portfolio_review_journal.py:846-856"},
 {"id": "G8-4", "result": "PASS", "evidence": "approve/approve-one-click.ps1:23-49; tools/dev-merge.ps1:43-73"},
 {"id": "G8-5", "result": "PASS", "evidence": "approve/approve-one-click.ps1:80-83,91-94"},
 {"id": "G8-6", "result": "FAIL", "evidence": "manage-us-stock-strategy/tests/test_approve_one_click.py:87; tools/dev_pipeline/devpipe.py:122,852"},
 {"id": "G8-7", "result": "FAIL", "evidence": "approve/approve-one-click.cmd, approve/approve-one-click.ps1: 0 CR bytes (tools/dev-merge.ps1: 136)"},
 {"id": "G8-8", "result": "PASS", "evidence": "approve/approve-one-click.ps1:76-94; apply_user_confirmed_broker_snapshot.py:275"}],
 "min_fixes": [
  "Save approve/approve-one-click.cmd and approve/approve-one-click.ps1 with CRLF line endings (ASCII, no BOM, content unchanged; only these two files).",
  "In manage-us-stock-strategy/tests/test_approve_one_click.py, replace test_line_endings_are_not_mixed with an assertion that both files use CRLF only (crlf > 0 and no bare LF).",
  "Remove the literals '/api/us/ordr', 'ust2000', 'ust2001', 'order_submit' and 'quantity_authority' from the needle list at test_approve_one_click.py:87 (the pipeline order-marker scan at devpipe.py:852 already checks added lines); do not obfuscate them to dodge the scan.",
  "Update docs/claude/approve-1click-report.md: sha256 of the three final files, CRLF applied, the actual target test result, and remove the stale 'CRLF 미충족' and '테스트 미실행' statements."
 ]}
```
VERDICT: FAIL

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/approve-1click/ 의 원본 기록입니다.)
