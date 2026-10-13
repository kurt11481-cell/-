# dev-run runner-fix — NEEDS_APPROVAL

- 시각(UTC): 2026-10-13T00:05:09Z → 2026-10-13T00:24:16Z
- 기준 커밋(base): `6012f2f8ffd622da2f21e6fd808c83fcb147ee92` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/run_auto_core.ps1, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_runner.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 2944 · 실패 28 → 변경 후 Ran 2952 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `803fd92de78d1727e6f6fe4ff538527a0899b9f872fb8b55dcda0f7b081db6cd`
- Judge 파일 sha256: `a05d78b117ed2f6a0aab7ccecaa685f1af51a15740a3820f910120ca89a3f79f`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 runner-fix -ApproveAuthority`

## 바뀐 파일

- `docs/claude/runner-fix-report.md`
- `manage-us-stock-strategy/scripts/run_auto_core.ps1`
- `manage-us-stock-strategy/tests/test_auto_core_runner.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 변수 이름을 `$pythonCommand`로 실제로 바꿨습니다(run_auto_core.ps1:47-50). 정적 테스트 5개와 동작 테스트 3개가 실제 동작을 확인하며, 하드코딩이나 TODO는 없습니다(test_auto_core_runner.py:106-140, 187-196) |
| G2 범위 | PASS | 바뀐 경로 3개가 모두 allowed_paths 안에 있습니다(changed-files.txt:1-3, task-prompt.md:13). 범위 검사 결과는 status OK, reasons [] 입니다(checks.json:93-94) |
| G3 주문 경로 없음 | PASS | 주문 문자열이나 키움 호출을 새로 넣지 않았습니다. `cmd /c` 줄도 그대로입니다(run_auto_core.ps1:63-67). 테스트는 임시 폴더의 가짜 auto_core.py만 실행합니다(test_auto_core_runner.py:44-49). NoOrderPathTests를 포함한 대상 테스트가 모두 통과했습니다(checks.json:140-148) |
| G4 정책·상태 쓰기 없음, fail-closed | PASS | 테스트는 임시 폴더 아래에만 씁니다(test_auto_core_runner.py:147-156, 177). `RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND`에서 exit 3으로 끝나는 동작은 바뀌지 않았습니다(run_auto_core.ps1:53-56). git이 무시하는 state 파일은 스냅샷과 비교한 결과 바뀌지 않았습니다(devpipe.py:752-761, checks.json:93-94) |
| G5 비밀 없음 | PASS | 환경 변수는 자식 프로세스에 넘기기만 하고 출력하지 않습니다(test_auto_core_runner.py:167-172). .env, 토큰, 계좌번호를 읽는 곳이 없습니다 |
| G6 단언 약화·skip 없음, 새 동작마다 테스트 | PASS | 기존 테스트 파일은 바뀌지 않았습니다(changed-files.txt:1-3). new_failures는 []입니다(checks.json:137). Windows가 아닐 때만 skip합니다(test_auto_core_runner.py:143). expectedFailure를 쓰지 않았습니다 |
| G7 class | PASS | 바뀐 것은 변수 이름과 주석 1줄뿐입니다(diff.patch:9-15). 주문 단계, 한도, quantity_authority, kill switch는 손대지 않았으므로 class_ok=true입니다 |
| G8-1 diff는 이름 변경과 주석 1줄뿐 | PASS | 인자(2-6), 로그 문구(37, 54, 58, 72), 종료 코드(18, 38, 55, 73), 후보 순서(41-44), `cmd /c`(67)가 모두 그대로입니다(diff.patch:5-17, run_auto_core.ps1) |
| G8-2 인자와 대소문자만 다른 대입 없음 | PASS | 다시 넣는 곳은 대소문자가 같은 `$RepositoryRoot`, `$PythonPath`뿐입니다(run_auto_core.ps1:22, 45, 50). 정적 검사 결과 0곳입니다(test_auto_core_runner.py:123-134) |
| G8-3 수정 전 패턴을 실제로 잡는지 스스로 확인 | PASS | 수정 전 조각(test_auto_core_runner.py:28-42)에서 `["command","command"]`를 잡는다고 단언합니다(:106-108) |
| G8-4 복사본과 가짜 스크립트만 실행 | PASS | 실행 전에 두 경로가 T 아래에 있고 저장소 아래에는 없다고 단언합니다. `-RepositoryRoot`도 T입니다(test_auto_core_runner.py:161-173). 진짜 runner는 읽기와 복사에만 씁니다(:132, 137, 153) |
| G8-5 동작 테스트가 skip 없이 돌았다는 증거 | PASS | 전체 테스트 수가 2944에서 2952로 8개 늘었고 skip 수는 3에서 3으로 그대로입니다(checks.json:4-7, 132-133). 대상 테스트의 skip 1개는 기존 replay 테스트입니다(checks.json:140-148). 보고서에도 적혀 있습니다(diff.patch:70-72) |
| G8-6 주문·권한·정책·상태·키움·예약 작업 변경 없음 | PASS | changed-files.txt:1-3, checks.json:93-94. 예약 작업 등록 스크립트는 실행하지 않고 읽기만 합니다(test_auto_core_runner.py:130-132) |
| G8-7 기존 테스트 파일 그대로, test_auto_core*.py 모두 통과 | PASS | 312개 실행, failures [], status OK(checks.json:140-148). 기존 테스트 파일은 changed-files에 없습니다 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_auto_core.ps1:47-50; manage-us-stock-strategy/tests/test_auto_core_runner.py:106-140,187-196"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/runner-fix/changed-files.txt:1-3; task-prompt.md:13; checks.json:93-94"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_auto_core.ps1:63-67; manage-us-stock-strategy/tests/test_auto_core_runner.py:44-49; checks.json:140-148"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_runner.py:147-156,177; manage-us-stock-strategy/scripts/run_auto_core.ps1:53-56; tools/dev_pipeline/devpipe.py:752-761; checks.json:93-94"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_runner.py:167-172"}, {"id": "G6", "result": "PASS", "evidence": "changed-files.txt:1-3; checks.json:137; manage-us-stock-strategy/tests/test_auto_core_runner.py:143"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/runner-fix/diff.patch:9-15"}, {"id": "G8-1", "result": "PASS", "evidence": "diff.patch:5-17; manage-us-stock-strategy/scripts/run_auto_core.ps1:2-6,17-18,37-38,41-44,54-55,58,67,72-73"}, {"id": "G8-2", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_auto_core.ps1:22,45,50; manage-us-stock-strategy/tests/test_auto_core_runner.py:123-134"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_runner.py:28-42,106-108"}, {"id": "G8-4", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_runner.py:153,161-173"}, {"id": "G8-5", "result": "PASS", "evidence": "checks.json:4-7,132-133,140-148; diff.patch:70-72"}, {"id": "G8-6", "result": "PASS", "evidence": "changed-files.txt:1-3; checks.json:93-94; manage-us-stock-strategy/tests/test_auto_core_runner.py:130-132"}, {"id": "G8-7", "result": "PASS", "evidence": "checks.json:137,140-148; changed-files.txt:1-3"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-13T01:13:50Z
- 병합 커밋: `6d5ca15d2b46e8de94114fc7b6a761406088cd2e` · 방식: rebase
- 사용자 승인(-ApproveAuthority): 2026-10-13T00:57:32Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/runner-fix/ 의 원본 기록입니다.)
