# dev-run swing-bars — NEEDS_APPROVAL

- 시각(UTC): 2026-11-20T01:35:29Z → 2026-11-20T02:09:44Z
- 기준 커밋(base): `e0f126bac8b66d26cfbed5d1cad6bb06fcdecf17` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_swing_bars.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3750 · 실패 2 → 변경 후 Ran 3773 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `0fc248ec1cedec1b03832f93d2653175ac46e9d65cda256ae89ec6e49df41f36`
- Judge 파일 sha256: `7a3cb7c7a530366f8aaedfebdc5ae9230780cf5430f0f6f905032a3e82ff021f`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 swing-bars -ApproveAuthority`

## 바뀐 파일

- `docs/claude/swing-bars-report.md`
- `manage-us-stock-strategy/scripts/auto_core.py`
- `manage-us-stock-strategy/tests/test_auto_core_swing_bars.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core.py:576-592: 코어 결과를 쓰는 `_finish` 다음 한 곳에서만 swing을 부르고, OK·HOLD 날에만 돌며 전체를 try/except로 감쌈. 266-284: 목록 검증. 315-359: 수집·예산·기록. 219·226: timeout 인자. 472-474: 새 인자. 636: main만 실제 경로를 넘김. 하드코딩·TODO 없음 |
| G2 범위 | PASS | changed-files.txt:1-3은 allowed_paths 3개뿐. 537-539의 `core_symbols` 정리는 지시 5번에 필요한 최소 변경(호출은 여전히 1번). swing-watch.json은 만들지 않음(Glob 0건) |
| G3 주문·체결 추정 | PASS | diff.patch에서 권한 표지·주문 경로 문자열 Grep 0건. 읽기 전용 조회만 씀: 218-228(usa06011), 202-215(usa10098) |
| G4 정책·상태 쓰기와 fail-closed | PASS | 새로 쓰는 곳은 swing-bars.json(310) 하나이고, history·pages 쓰기는 코어와 같은 경로임. 목록이 깨지면 LIST_INVALID(330-333). 단계 밖에서 예외가 나면 OK가 아니라 PARTIAL에 이유를 적음(587-591). 목록 파일이 없을 때 아무것도 안 하는 건 지시 6번이 정한 동작이고(테스트 2), 자료가 비면 장부에서 NO_PRICE·DATA_GAP로 보임(swing_shadow_ledger.py:239,247) |
| G5 비밀 | PASS | 시간 초과 사유에 명령줄과 프로필 별칭을 남기지 않음(301-303). 계좌를 읽는 코드 없음 |
| G6 테스트 | PASS | 기존 테스트 파일은 그대로. skip·expectedFailure 0건. 새 테스트 23개가 지시 1-11번을 모두 다룸(test_auto_core_swing_bars.py:461-743). checks.json:152 new_failures [] |
| G7 class | PASS | 권한 표지 줄·예산·상한·킬 스위치·대조 불변 조건 변경 없음. quantity_authority 추가 없음. 이 작업이 authority 등급인 이유는 경로뿐(checks.json:128-131) |
| G8-1 범위·금지 경로 | PASS | changed-files.txt:1-3. auto_core_decide.py·schemas·기존 테스트 변경 없음 |
| G8-2 마지막 `_finish` 뒤 한 곳, try 감쌈, 반환값 그대로 | PASS | auto_core.py:576-592. 일찍 끝나는 525·565·570행 경로에는 호출 없음. 테스트 3·4·10이 결과 파일 바이트 불변과 종료 코드 0을 확인(test_auto_core_swing_bars.py:442-454,509-529,695-704) |
| G8-3 기본값 None, main만 경로를 넘김 | PASS | auto_core.py:472,636. Grep 결과 다른 호출자 없음. 테스트 1(461-467) |
| G8-4 종목 실패가 daily를 FAIL로 만들지 않음, FAIL·킬 스위치 날엔 안 돎 | PASS | 354-355. 테스트 4·6·7(509-529, 595-614, 618-642). 킬 스위치 날은 reconcile_broker_state.py:443-444 → auto_core.py:523-525에서 일찍 끝남 |
| G8-5 시간 예산·종목 상한 | PASS | 코어 기본 timeout 3600 유지(219), swing은 600(473), 예산 판단(339-342). 테스트 5·11(566-591, 720-734) |
| G8-6 대상 테스트 | PASS | 654개 실행, 실패 1건(checks.json:156-166). 이 1건은 변경 전 기준선에도 같은 이름으로 있음(checks.json:4,145). test_auto_core_decide.py:1369의 실제 등록부 자료(SOXL trim_target_weight) 문제로 이번 diff와 무관하고, 이 worktree에서 고칠 수 없음. 새 실패 0 |
| G8-7/G9 연결표 | PASS | register_auto_core_task.ps1:25(06:15, 60분), swing_shadow_ledger.py:85-92(verified와 close 기준), secretary-daily.txt:17(㉰ resume.date ≤ TODAY), strategy1101_score.py:259(폴더 전체 glob)과 :280(입력 해시), host_status.ps1:142-145(종료 코드 경고), 장부 run()의 trade_status(:362,393) 모두 칸 내용과 일치. swing-bars.json을 읽는 점검이 없는 끊김 행에는 메울 변경과 승인 경로가 적혀 있음(task-prompt.md:83). 1행 ②(목록 파일)는 이번 변경 밖의 입력이라 산출 연결 대상이 아님 |
| G8-8 소비 쪽이 swing을 읽지 않음 | PASS | auto_core_decide.py·t2rc-oracle.py·auto-core-alert.txt에서 `(?i)swing` Grep 0건. auto_core*.py 안에 history 폴더 전체를 훑는 glob 없음 |

```json
{"verdict": "PASS", "class_ok": true, "items": [
{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:266-359,576-592,636"},
{"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/swing-bars/changed-files.txt:1-3; auto_core.py:537-539"},
{"id": "G3", "result": "PASS", "evidence": "diff.patch marker/order-path grep 0; auto_core.py:202-228"},
{"id": "G4", "result": "PASS", "evidence": "auto_core.py:310,330-333,587-591; docs/claude/swing_shadow_ledger.py:239,247"},
{"id": "G5", "result": "PASS", "evidence": "auto_core.py:301-303"},
{"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_swing_bars.py:461-743; checks.json:152"},
{"id": "G7", "result": "PASS", "evidence": "diff.patch authority-marker grep 0; checks.json:128-131 (path-only authority class)"},
{"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1-3"},
{"id": "G8-2", "result": "PASS", "evidence": "auto_core.py:576-592; test_auto_core_swing_bars.py:442-454,509-529,695-704"},
{"id": "G8-3", "result": "PASS", "evidence": "auto_core.py:472,636; test_auto_core_swing_bars.py:461-467"},
{"id": "G8-4", "result": "PASS", "evidence": "auto_core.py:354-355,523-525; reconcile_broker_state.py:443-444; test_auto_core_swing_bars.py:595-642"},
{"id": "G8-5", "result": "PASS", "evidence": "auto_core.py:219,339-342,473; test_auto_core_swing_bars.py:566-591,720-734"},
{"id": "G8-6", "result": "PASS", "evidence": "checks.json:4,145,152,156-166 (only failure is baseline, unrelated: test_auto_core_decide.py:1369 real registry data)"},
{"id": "G8-7", "result": "PASS", "evidence": "register_auto_core_task.ps1:25; swing_shadow_ledger.py:85-92,362,393; secretary-daily.txt:17; strategy1101_score.py:259,280; host_status.ps1:142-145; task-prompt.md:83"},
{"id": "G8-8", "result": "PASS", "evidence": "auto_core_decide.py, docs/claude/t2rc-oracle.py, docs/claude/scheduled-prompts/auto-core-alert.txt: grep (?i)swing 0"},
{"id": "G9", "result": "PASS", "evidence": "task-prompt.md:77-84 cells verified at cited lines; break row has fix and approval path"}
], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-20T02:24:30Z
- 병합 커밋: `af40710dc908bc41ce5397ddf38c6066dd6ca432` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-11-20T02:24:28Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/swing-bars/ 의 원본 기록입니다.)
