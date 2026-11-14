# dev-run runner-deps — NEEDS_APPROVAL

- 시각(UTC): 2026-11-14T05:30:12Z → 2026-11-14T05:54:31Z
- 기준 커밋(base): `5fc010cabea7ca61233676741ab0ec5e926e1652` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/run_auto_core.ps1, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_runner_deps.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3653 · 실패 1 → 변경 후 Ran 3662 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `78d11ba3d44490d796a190441d9dfdf1e3238274d762f224eb52e1a6c40dd1ff`
- Judge 파일 sha256: `425d2824f4de43ed2ae983c84c06a7650109fd8e4252d2ae25a2405672014b4a`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 runner-deps -ApproveAuthority`

## 바뀐 파일

- `docs/claude/runner-deps-report.md`
- `manage-us-stock-strategy/scripts/run_auto_core.ps1`
- `manage-us-stock-strategy/tests/test_auto_core_runner_deps.py`

## Judge 보고 원문 (1회차 PASS)

판정 자료(지시문·diff·checks.json)와 연결표 인용 원문 10곳을 모두 확인했고, 아래에 판정을 적습니다.

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | run_auto_core.ps1:64(작은따옴표·flush=True 코드), :67-77(Continue 상태에서 `& $PythonPath -c $depsCode 2>&1`), :78-101(판 = stdout 형식 첫 줄/unknown, 오류 끝줄 ASCII·300자, :98 실패 줄, :99 상세, :100 `exit 4`), :14-15 머리 주석. TODO·하드코딩 없음 |
| G2 범위 | PASS | changed-files.txt:1-3 = allowed_paths 3개뿐, checks.json:17-21. register_auto_core_task.ps1·기존 테스트 변경 없음 |
| G3 주문·키움·체결 추정 없음 | PASS | diff.patch 주문 문자열 검색 결과: 7행(기존 그대로 둔 줄)과 154행(docstring "no Kiwoom")만 걸림 |
| G4 정책·상태 쓰기 없음·fail-closed | PASS | 쓰는 곳은 실행기 로그뿐(run_auto_core.ps1:34). 종료 코드가 없거나 예외가 나면 실패로 처리(:72-74, :78) → exit 4, 코어 호출 안 함 |
| G5 비밀·계좌 식별자 | PASS | 비밀·계좌 접근 없음. 정상 경로에서는 Python 경로를 쓰지 않음(:98-99는 판·오류 끝줄만 씀) |
| G6 단언 약화·skip·새 동작 테스트 | PASS | 기존 테스트 변경 없음. new_failures [](checks.json:150), targets Ran 17·skipped 0(:155-161). 새 동작별 테스트 test_auto_core_runner_deps.py:61,69,80,92,170,173,176,181,196 |
| G7 class | PASS (class_ok=true) | 주문 단계·도구·예산·상한·불변식·킬 스위치 변경 없음, quantity_authority 추가 없음. authority class는 경로 때문(checks.json:127-129) |
| G8-1 diff 범위 | PASS | changed-files.txt:1-3 |
| G8-2 순서·실패 시 코어 미호출 | PASS | run_auto_core.ps1:18-20 < :70 < :104 < :113. 실패 시 argv 없음 단언 test:162 |
| G8-2-1 큰따옴표 없음·flush·판 읽기 | PASS | run_auto_core.ps1:64, :86-89(ErrorRecord를 먼저 걸러 stdout 줄만 판 후보), test:85,88 |
| G8-3 격리 플래그 없음 | PASS | run_auto_core.ps1:70, test:76-78 |
| G8-4 성공 경로 불변 | PASS | :103-119가 기준과 같음(diff는 :59-101만 추가). test:181-194, 기존 runner 테스트 포함 Ran 17 OK |
| G8-5 회귀 검출 | PASS | 사전 점검을 빼면 가짜 .cmd가 0으로 끝나 test:156 `returncode == 4`, :160 RUNNER_START 단언이 실패함. skipped 0(checks.json:160) → Windows 동작 테스트가 실제로 돌았음. 참고(병합 막지 않음): 보고 :111(diff 기준 줄)은 "argv 없음 단언도 실패"라고 하지만, 가짜 .cmd는 가짜 코어를 실행하지 않아 그 단언은 통과함 |
| G8-6 대상 테스트 | PASS | checks.json:155-162 status OK, failures [] |
| G8-7 / G9 연결표 | PASS | 원문 대조: register_auto_core_task.ps1:25,27(작업명·06:15/07:45), auto-core-alert.txt:36 ①·:49 ⑭, host_status.ps1:20 `$coreTaskNames`·:142-145 7일 안 0 아님→경고, active-decisions.md:62 trig id 두 개, room-digest.txt:2 "돌았는지"·:5 list_triggers last_run·:28 "안 돎·늦음·실패", 테스트 :61·69·80·92·170·173·176·181·196 일치. trig id는 모두 `trig_`로 시작. 참고: 보고 1절의 주석 줄 범위 "58~62"는 실제 59~63(②칸 인용 :64-101은 맞음) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_auto_core.ps1:64-101,14-15"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/runner-deps/changed-files.txt:1-3"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/runner-deps/diff.patch:7,154 (no order strings)"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_auto_core.ps1:72-74,78,100"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_auto_core.ps1:98-99"}, {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/runner-deps/checks.json:150,155-161"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/runner-deps/checks.json:126-129"}, {"id": "G8", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_runner_deps.py:156-162,181-201; run_auto_core.ps1:18-20,70,104,113"}, {"id": "G9", "result": "PASS", "evidence": "register_auto_core_task.ps1:25,27; auto-core-alert.txt:36,49; host_status.ps1:20,142-145; active-decisions.md:62; room-digest.txt:2,5,28"}], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/runner-deps/ 의 원본 기록입니다.)
