# dev-run evo-s1 — FAIL

- 시각(UTC): 2026-10-16T06:25:13Z → 2026-10-16T07:13:10Z
- 기준 커밋(base): `5b75ff8b6f6794d557bde07242ada08fdd559975` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ADDED_LINE:kill_switch)
- 상태: **FAIL** · 재시도: 1
- 테스트: 기준선 Ran 3105 · 실패 28 → 변경 후 Ran 3156 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `None`
- Judge 파일 sha256: `None`
- 사유: judge_fail_after_fix
- 다음: `see docs/claude/dev-runs/evo-s1.md`

## 바뀐 파일

- `docs/claude/evo-s1-report.md`
- `manage-us-stock-strategy/scripts/register_journal_score_task.ps1`
- `manage-us-stock-strategy/scripts/run_journal_score.ps1`
- `manage-us-stock-strategy/scripts/score_decision_journal.py`
- `manage-us-stock-strategy/tests/test_journal_score_task_static.py`
- `manage-us-stock-strategy/tests/test_score_learning.py`

## Judge 보고 원문 (2회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `score_decision_journal.py:1923-1976`의 `score_learning`, `:2022-2049`의 `build_learning`, `:2095-2119`의 `main` learning 분기. 사전 등록 3-0~3-6과 4절 블록을 모두 구현했다. TODO·하드코딩 없음(diff 검색 0건) |
| G2 범위 | PASS | `changed-files.txt:1-6`이 allowed_paths 6개와 같다. checks.json `changed_paths`도 같다. 부수 변경 없음 |
| G3 주문·체결 추정 | PASS | diff에 주문 표지·주문 도구 이름 0건. 체결은 기존 `would_fill`(`score_decision_journal.py:539`)만 쓴다 |
| G4 쓰기·fail-closed | FAIL | 쓰기는 `write_report`/`check_output_root`(`:796-817`)와 실행기 logs·WEEKLY_LATEST뿐이다. 그러나 learning이 예외로 실패하면 `_learning_failure` 블록(`:2006-2009`, `:2114-2115`)이 남는다. 실행기는 `"learning":` 글자만 보고(`run_journal_score.ps1:57`) 종료 코드 0이면 status OK로 쓴다(`:65-66`). 실패가 WEEKLY_LATEST에서 OK로 보인다(사전 등록 7절 "status OK + learning 있음" 완료 기준을 무력화) |
| G5 비밀 | PASS | .env·토큰·계좌 읽기 없음. 실행기 로그는 시각·시간대만 적는다(`run_journal_score.ps1:104-105`) |
| G6 테스트 | PASS | 기존 `test_score_ticket_outcomes.py`는 그대로다. 새 테스트 45건이 a~n을 덮는다. skip·expectedFailure 0건. checks.json 대상 59/6 OK, new_failures [] |
| G7 class | PASS | kill switch 관련 글자는 테스트 고정값의 사유 문자열 하나뿐이다(`test_score_learning.py:322` "KILL_SWITCH_ON"). 채점기는 정지 스위치를 읽지도 바꾸지도 않으므로 class_ok=true다. 다만 이 글자가 `devpipe.py:127` CHANGED_LINE_MARKERS에 걸려 class가 authority로 올라갔다(checks.json:103-106). 고치지 않으면 병합에 불필요한 -ApproveAuthority 결정이 생긴다 |
| J-a | PASS | 바뀐 파일 6개뿐. 코어·정책·상태·일지·스키마·로케일은 그대로다(changed-files.txt) |
| J-b | PASS | 플래그가 없으면 `load_inputs` 조건·인자가 같다(`:2093-2102`). learning은 `if args.learning` 안에서만 돈다(`:2110-2119`). `score_journal` 시그니처 불변(`:609-614`). 코어 호출 모양 테스트(`test_score_learning.py:214`)와 기본 길 동일성 테스트(`:192`)가 있다 |
| J-c | PASS | 실행 중 import에 auto_core 없음(`:39-56`). `band_closes`·`_quantile`·`band_quantiles`(`:1585-1614`)는 `auto_core_tickets.py:285-301`, `auto_core_rules.py:221-232`와 같은 식이다. 같음 테스트 2종(전체·빈 세션)이 있다(`test_score_learning.py:646`) |
| J-d | FAIL | 날짜 자격·관문 이름·단위·충격 구간·묶음·간격·epoch는 사전 등록과 맞다. 보존 규칙에 결함이 있다. `find_previous_learning`(`:1024-1042`)이 LEARNING_FAILED 블록(`decision_days: []`, `:2006-2009`)도 직전 보고서로 고른다. 그러면 다음 주 `_decision_days`(`:1259-1265`)가 first_*를 새로 적고, PRESERVATION_BROKEN·MISSING_NOW 이력을 잃는다. 깨졌던 날이 다시 자격을 얻는 fail-open이고, 사전 등록 3-0(102-109행) "한 번 붙으면 남고, 일시 장애로 과거가 바뀌지 않게"에 어긋난다 |
| J-e | PASS | `_bucket`(`:1773-1838`): n≥30, 네 부호, ⌊n/2⌋ 반쪽과 (시작, 종목, 단위) 정렬, 10%(달력 밖·PENDING 제외), 현재 epoch, 꼬리 20%. cf>0=비용, path_20은 부호 그대로. 테스트 `:806`, `:843` |
| J-f | PASS | 채점기는 출력 루트에만 쓴다. 실행기는 logs·WEEKLY_LATEST(임시 파일 → Move-Item, `run_journal_score.ps1:79`)에만 쓴다. learning 있는 보고서만 고른다(`:38-60`) |
| J-g | PASS | 작업 이름 하나(`register_journal_score_task.ps1:23`). PlanOnly면 등록 전에 끝난다(`:67-69`). 일요일 09:20(`:81`), 15분, StartWhenAvailable, `WakeToRun:$false`, IgnoreNew, Interactive/Limited(`:83-87`) |
| J-h | PASS | 키움 호출 없음. 기존 `order_authority`/`quantity_authority` 줄(`:636`) 불변. 새 권한 값 없음 |

```json
{"verdict": "FAIL", "class_ok": true, "items": [
{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:1923-1976,2022-2049,2095-2119"},
{"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/evo-s1/changed-files.txt:1-6"},
{"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:539 (existing would_fill only)"},
{"id": "G4", "result": "FAIL", "evidence": "manage-us-stock-strategy/scripts/run_journal_score.ps1:57,65-66 + score_decision_journal.py:2006-2009,2114-2115 (LEARNING_FAILED report written as status OK)"},
{"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_journal_score.ps1:104-105"},
{"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/evo-s1/checks.json:154-174"},
{"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_score_learning.py:322 (fixture string only; devpipe.py:127 false escalation, checks.json:103-106)"},
{"id": "J-a", "result": "PASS", "evidence": "workspace/outputs/dev-runs/evo-s1/changed-files.txt:1-6"},
{"id": "J-b", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:609-614,2093-2119; tests/test_score_learning.py:192,214"},
{"id": "J-c", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:39-56,1585-1614; auto_core_tickets.py:285-301; auto_core_rules.py:221-232; tests/test_score_learning.py:646"},
{"id": "J-d", "result": "FAIL", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:1024-1042,1259-1265,2006-2009 vs docs/claude/f-evo-loop-s1-preregistration-2026-10-16.md:102-109"},
{"id": "J-e", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:1773-1838; tests/test_score_learning.py:806,843"},
{"id": "J-f", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/run_journal_score.ps1:38-60,79; score_decision_journal.py:796-817"},
{"id": "J-g", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/register_journal_score_task.ps1:23,67-69,81-88"},
{"id": "J-h", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:636"},
{"id": "G8", "result": "FAIL", "evidence": "J-d FAIL (see above); J-a,b,c,e,f,g,h PASS"}
], "min_fixes": [
"score_decision_journal.py find_previous_learning(1024-1042): learning.errors에 LEARNING_FAILED가 있는 블록(_learning_failure, 2006-2009)은 직전 보고서로 고르지 않고 그보다 앞선 정상 learning 보고서로 거슬러 올라간다. test_score_learning.py에 '1주차 PRESERVATION_BROKEN → 2주차 LEARNING_FAILED 보고서 → 3주차에도 PRESERVATION_BROKEN·first_sha256 유지' 테스트를 더한다",
"run_journal_score.ps1(57, 63-66): 고른 보고서의 learning에 LEARNING_FAILED가 있으면 WEEKLY_LATEST status를 FAIL로 쓴다(종료 코드 규칙은 그대로). test_journal_score_task_static.py 필수 글자에 LEARNING_FAILED를 더한다",
"test_score_learning.py:322: 계획 전 HOLD 고정값 사유 \"KILL_SWITCH_ON\"을 \"T1_RESULT_MISSING\"(사전 등록 3-0 96행의 같은 계획 전 HOLD 사유)으로 바꾼다. devpipe.py:127이 이 줄로 run을 authority로 잘못 올려(checks.json:103-106) 불필요한 -ApproveAuthority 결정을 만들지 않게 한다"
]}
```

VERDICT: FAIL

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/evo-s1/ 의 원본 기록입니다.)
