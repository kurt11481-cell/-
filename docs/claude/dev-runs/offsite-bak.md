# dev-run offsite-bak — READY_TO_MERGE

- 시각(UTC): 2026-10-20T01:55:14Z → 2026-10-20T02:31:12Z
- 기준 커밋(base): `624e9e249ebbe99222c89105b387f23d8d97b94f` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 1
- 테스트: 기준선 Ran 3213 · 실패 30 → 변경 후 Ran 3230 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `f31b2d42fe62ab772568eec00936c1feb15145c60760834eedb7106dbe24dfb0`
- Judge 파일 sha256: `8c99c96dcfb033c8974ccb3370f4a6979dea8fab8316e1e91b7fc2fc64836d1a`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 offsite-bak`

## 바뀐 파일

- `docs/claude/offsite-bak-report.md`
- `manage-us-stock-strategy/scripts/host_status.ps1`
- `manage-us-stock-strategy/scripts/offsite_backup.ps1`
- `manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1`
- `manage-us-stock-strategy/tests/test_host_status_static.py`
- `manage-us-stock-strategy/tests/test_offsite_backup_static.py`

## Judge 보고 원문 (1회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `offsite_backup.ps1:111-182`(push), `:228-334`(압축 사본), `:361-388`(결과 파일) · `register_offsite_backup_task.ps1:23-26,82` · `host_status.ps1:261-309,332`. 빈 껍데기·하드코딩·TODO 없음. 비차단 참고 ① 압축이나 교체 중 예외가 나면 `.tmp.zip`이 OneDrive에 남음(`offsite_backup.ps1:327-329`). 지시문에는 항목 수가 다를 때만 지우라고 되어 있음 ② 메인 체크아웃이 `main`에 있으면 push가 매일 SKIPPED인데 status는 OK가 됨. 지시문 설계(task-prompt.md:27,42)대로라 Builder 결함이 아님. 메인 체크아웃 `.git/HEAD`는 worktree 밖이라 읽기 권한이 거부됨 → 확인 필요(Cowork) |
| G2 범위 | PASS | `changed-files.txt:1-6`이 allowed_paths 6개와 같음 · `checks.json:48-53` reasons 빈 배열 |
| G3 주문·체결 추정 | PASS | git(`rev-parse`·`remote`·`rev-list`·`log`·`ls-files`·`push`)만 호출 · `kiwoom`·주문 이름 없음(`test_offsite_backup_static.py` OrderNameTests) |
| G4 정책·상태 쓰기 / fail-closed | PASS | 쓰는 곳은 결과 파일(`offsite_backup.ps1:349-388`), `%TEMP%`(`:353`), BackupRoot(`:289-326`)뿐. stock-strategy-system은 복사 원본으로 읽기만 함(`:203-209`) · 자료 없음은 WARN/UNKNOWN(`host_status.ps1:264-265,272-274,291-293`), 폴더 없음은 FAIL(`offsite_backup.ps1:247-251`) |
| G5 비밀·계좌 | PASS | 파일 내용을 읽지 않음 · `user:pass@` 가림(`offsite_backup.ps1:37`) · `git remote`는 이름만 받음(`:142`) · private inputs 제외(`:27-30`) |
| G6 단언·테스트 | PASS | `test_host_status_static.py:31-32,82-83`은 목록 확장, `:164-190`은 새 메서드 · skip·expectedFailure 추가 없음 · `checks.json:99` new_failures 빈 배열, `:102-118` 대상 테스트 16+20 OK |
| G7 class | PASS | `checks.json:48-49` general, class_reasons 빈 배열 · `register_offsite_backup_task.ps1:62` `ORDER_AUTHORITY = $false`는 출력 줄일 뿐 · quantity_authority 없음 |
| G8 J-a | PASS | `diff.patch:5-79` host_status 변경은 추가 줄만(기존 7개 항목 그대로) · 테스트 변경은 목록 확장과 새 메서드(`diff.patch:84-89,93-99,107-133`) |
| G8 J-b | PASS | push는 `offsite_backup.ps1:169` 한 줄뿐 · HEAD·main은 건너뜀(`:126-135`) · 인증 창 대기 차단(`:167-168`) · Continue는 git 호출 주변만, finally에서 되돌림(`:70-77`) · 성패는 `$LASTEXITCODE`로만 판정(`:74,170`) |
| G8 J-c | FAIL | 정규식은 devpipe와 같음(`offsite_backup.ps1:24` = `devpipe.py:139-141`) · push 전(`:151-161`)과 stock-strategy-system 복사(`:203`)에는 전체 경로로 적용됨. 그러나 workspace\outputs 폴더 10개는 `Test-SecretPath -RelativePath $file.Name`(`:220`)로 파일 이름만 넘겨서, A 규칙의 `/secrets/` 폴더 조건(`:48`)이 걸리지 않음. 지시문 B는 "위 A와 같은 비밀 이름 규칙"(task-prompt.md:38)인데, 보고서는 "파일마다 적용"(`offsite-bak-report.md:5`)이라고 씀 |
| G8 J-d | PASS | stock-strategy-system은 추적 안 되는 파일과 무시된 파일의 합에서 두 폴더를 뺌(`:193-202,31`) · 복사 폴더 목록에 private inputs 없음(`:29-30`) · 보관 삭제는 OK 뒤(`:313`)에만, BackupRoot 바로 아래 `-File` 중 날짜 zip 정규식(`:25`)에 맞는 것만(`:316-326`) |
| G8 J-e | PASS | git 쓰기 명령 없음 · `-c core.quotePath=false`는 그 명령 한 번에만 적용되고 설정 쓰기가 아님 · 저장소 안에 쓰는 것은 결과 파일뿐(`:382-388`) |
| G8 J-f | PASS | 결과 status 계산(`:361-365`) · backup_recent의 26시간(`host_status.ps1:299`), dry_run(`:302`), status(`:305`) 판정 · 종료 코드는 항상 0(`offsite_backup.ps1:390-397`) |
| G8 J-g | PASS | 작업 1개(`register_offsite_backup_task.ps1:24`) · `-Daily -At 23:50`(`:82`) · PlanOnly는 등록(`:89`) 전에 exit 0(`:68-71`) · 브로커 호출·권한 값 변경 없음 |

```json
{"verdict": "FAIL", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:111-388; register_offsite_backup_task.ps1:23-26,82; host_status.ps1:261-309,332 (non-blocking: .tmp.zip left on exception offsite_backup.ps1:327-329; main checkout branch not verifiable from this worktree - .git/HEAD read denied - push SKIPPED on main counts as OK per task-prompt.md:27,42)"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/offsite-bak/changed-files.txt:1-6; checks.json:48-53"}, {"id": "G3", "result": "PASS", "evidence": "offsite_backup.ps1:119-169 (git only); test_offsite_backup_static.py OrderNameTests"}, {"id": "G4", "result": "PASS", "evidence": "offsite_backup.ps1:203-209,247-251,289-326,349-388; host_status.ps1:264-265,272-274,291-293"}, {"id": "G5", "result": "PASS", "evidence": "offsite_backup.ps1:27-30,37,142"}, {"id": "G6", "result": "PASS", "evidence": "test_host_status_static.py:31-32,82-83,164-190; checks.json:99,102-118"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:48-49; register_offsite_backup_task.ps1:62"}, {"id": "G8/J-a", "result": "PASS", "evidence": "diff.patch:5-79,84-89,93-99,107-133"}, {"id": "G8/J-b", "result": "PASS", "evidence": "offsite_backup.ps1:70-77,126-139,167-170"}, {"id": "G8/J-c", "result": "FAIL", "evidence": "offsite_backup.ps1:220 passes $file.Name so the /secrets/ folder condition (offsite_backup.ps1:48) never applies to the 10 workspace/outputs folders; task-prompt.md:38 requires the same rule as A; docs/claude/offsite-bak-report.md:5 claims per-file application"}, {"id": "G8/J-d", "result": "PASS", "evidence": "offsite_backup.ps1:25,29-31,193-202,313-326"}, {"id": "G8/J-e", "result": "PASS", "evidence": "offsite_backup.ps1:119,140,142,147,151,169,193-194,382-388"}, {"id": "G8/J-f", "result": "PASS", "evidence": "offsite_backup.ps1:361-365,390-397; host_status.ps1:299,302,305"}, {"id": "G8/J-g", "result": "PASS", "evidence": "register_offsite_backup_task.ps1:24,62,68-71,82,89"}], "min_fixes": ["manage-us-stock-strategy/scripts/offsite_backup.ps1:219-222: in the workspace\\outputs loop compute $relative before the secret check and call Test-SecretPath -RelativePath $relative (not $file.Name), so the /secrets/ folder condition of rule A also applies to the 10 output folders", "manage-us-stock-strategy/tests/test_offsite_backup_static.py test_secret_name_rule_matches_devpipe: assert the output-folder loop passes the relative path (e.g. assertNotIn('Test-SecretPath -RelativePath $file.Name', text) and assertIn('Test-SecretPath -RelativePath $relative', text))", "docs/claude/offsite-bak-report.md:5: state that the full rule (file name regex, /secrets/ folder, auth.json) is applied to both copy sources"]}
```

VERDICT: FAIL

## Judge 보고 원문 (2회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `offsite_backup.ps1`에 push 단계(111-182), 복사 계획(184-226), 압축·확인·보관(228-334), 결과 파일 작성(336-397)이 모두 실제로 구현됨. `register_offsite_backup_task.ps1:22-99`와 `host_status.ps1:261-309, 332`도 구현됨. TODO나 하드코딩은 없음. 1차 Judge min_fixes 3건은 반영됨(`offsite_backup.ps1:220-221`, `test_offsite_backup_static.py:142-147`, `offsite-bak-report.md:5`). 병합을 막지 않는 참고 1건: 예외로 끝나면 `.tmp.zip`이 남을 수 있지만, 같은 날 다음 실행 때 지워짐(`offsite_backup.ps1:290`) |
| G2 범위 | PASS | `changed-files.txt:1-6`의 6개 파일이 allowed_paths 6개와 같음. checks.json의 changed_paths·reasons에 문제 없음 |
| G3 주문·체결 추정 | PASS | 주문 이름, kiwoom, 가격으로 체결을 추정하는 코드 없음. `test_offsite_backup_static.py:251-262`(ORDER_NAMES·ORDER_IDENTIFIER는 가져다 씀) |
| G4 정책·상태 쓰기 / fail-closed | PASS | 저장소 안에서 쓰는 곳은 결과 파일 하나(`offsite_backup.ps1:349-388`). `stock-strategy-system`은 복사할 때 읽기만 함(203-209). OneDrive 없음·파일 0개·origin 없음은 FAIL(247-251, 257-261, 143-146). 백업 기록이 없으면 WARN(`host_status.ps1:264-265`) |
| G5 비밀 | PASS | 파일 이름만 보고 판정하며 내용은 읽지 않음(`offsite_backup.ps1:42-51`). URL의 `user:pass@`는 가림(37). `private_inputs`는 제외(27-28, 236) |
| G6 단언·테스트 | PASS | `test_host_status_static.py`는 31-32행(CHECK_IDS)과 76-83행(허용 집합) 확장, 164행 새 메서드뿐. 새 파일 테스트 16개, 대상 테스트 OK, new_failures 0, EXPECTED_FAILURES_INCREASED 없음(checks.json:114-134). 수정한 기존 파일 2개의 CRLF 유지 확인(370/370, 252/252) |
| G7 class | PASS | 주문 단계·예산·상한·대조 불변 조건·kill switch 변경 없음. quantity_authority 추가 없음. `ORDER_AUTHORITY = $false`는 등록 틀에서 따라온 출력뿐(`register_offsite_backup_task.ps1:62`) |
| J-a | PASS | `host_status.ps1`은 추가만 함(diff에 `-` 줄 0). 기존 7개 배열은 그대로 두고(322-330) 332행 `+=`로 덧붙임 |
| J-b | PASS | push는 `push origin <b>:refs/heads/<b>` 하나(`offsite_backup.ps1:169`). 그 전에 분리 HEAD·main·이름 검사로 SKIPPED/FAIL 처리(126-139). `GIT_TERMINAL_PROMPT=0`·`GCM_INTERACTIVE=never`(167-168). Continue는 git 호출 주변에만 쓰고 finally에서 되돌리며, 성패는 `$LASTEXITCODE`로 판정(70-77). `.githooks/pre-push:5`의 규칙과 같음 |
| J-c | PASS | 비밀 이름 정규식이 `devpipe.py:139-141`과 같고(`offsite_backup.ps1:24`, 대소문자 무시 `-match`), `/secrets/`·`auth.json` 검사까지 더해 더 넓음. push 전(156-161), 복사 전 두 원천(203, 220-221)에 모두 적용 |
| J-d | PASS | stock-strategy-system은 추적 안 된 파일만, 제외 폴더 2개 빠짐(193-202). 출력 폴더 10개(29-30). 보관 정리는 OK가 된 뒤에만, `<BackupRoot>` 바로 아래 `^\d{4}-\d{2}-\d{2}\.zip$`인 파일만 지움(313-326) |
| J-e | PASS | git은 읽기 명령과 push 하나만 씀(`test_offsite_backup_static.py:83-94`). `-c core.quotePath=false`는 그 명령 한 번에만 적용되고 설정을 쓰지 않음 |
| J-f | PASS | status 계산(`offsite_backup.ps1:361-365`)과 끝의 `exit 0`(397). backup_recent는 26h·dry_run·status 판정(`host_status.ps1:299-307`), 깨짐·schema 다름·시각 해석 실패는 UNKNOWN(266-292) |
| J-g | PASS | `-Daily -At 23:50`(`register_offsite_backup_task.ps1:82`), 작업은 하나뿐(24), PlanOnly면 등록 전에 `exit 0`(68-71), Weekly 없음 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:111-397; register_offsite_backup_task.ps1:22-99; host_status.ps1:261-309,332"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/offsite-bak/changed-files.txt:1-6"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_offsite_backup_static.py:251-262"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:143-146,247-251,257-261,349-388; host_status.ps1:264-265"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:27-28,37,42-51,236"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_host_status_static.py:31-32,76-83,164; checks.json:114-134"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1:62; checks.json:63-64"}, {"id": "J-a", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/host_status.ps1:322-332"}, {"id": "J-b", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:70-77,126-139,167-169"}, {"id": "J-c", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:24,42-51,156-161,203,220-221; tools/dev_pipeline/devpipe.py:139-141"}, {"id": "J-d", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:29-31,193-202,313-326"}, {"id": "J-e", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_offsite_backup_static.py:83-94"}, {"id": "J-f", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/offsite_backup.ps1:361-365,397; host_status.ps1:266-307"}, {"id": "J-g", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1:24,68-71,82"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-20T02:39:26Z
- 병합 커밋: `4fe10b3d23192a99ebcea155ef8ccba0447e1fab` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/offsite-bak/ 의 원본 기록입니다.)
