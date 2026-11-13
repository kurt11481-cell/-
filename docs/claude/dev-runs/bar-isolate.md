# dev-run bar-isolate — NEEDS_APPROVAL

- 시각(UTC): 2026-11-13T12:45:09Z → 2026-11-13T13:41:10Z
- 기준 커밋(base): `68eedcf92bc4017a5b323e1f3d319b507c8e70a9` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 1
- 테스트: 기준선 Ran 3635 · 실패 1 → 변경 후 Ran 3653 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `c5a8691bdf4dca636006aed87dff9c5102e5d54f0ae3637ea863c7e092642956`
- Judge 파일 sha256: `ae9daccf6199c4143f6f134223c94e16f375fa71290363d52648709b0de3657c`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 bar-isolate -ApproveAuthority`

## 바뀐 파일

- `docs/claude/bar-isolate-report.md`
- `manage-us-stock-strategy/scripts/auto_core.py`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py`

## Judge 보고 원문 (1회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 지시한 동작이 모두 구현됐다. 빈 껍데기·하드코딩·TODO는 없다.<br>• daily: 격리 사유 3종(`manage-us-stock-strategy/scripts/auto_core.py:131`). 격리 가능 종목 = 관심 명단 − 보유 − extra − 노출 검토 종목 − RREC 기준 종목, 읽다 예외가 나면 빈 집합(:157-173). 노출 검토 종목은 run_portfolio_exposure_review.py:505-530과 같은 출처(auto_core.py:134-154). 수집 루프의 격리 분기(:414-428)는 `isolated`가 있을 때만 결과에 넣는다(:430-432). docstring(:15-21)도 고쳤다.<br>• decide: 격리 목록 대조(auto_core_decide.py:183-207). 보유·기준 종목이 정해진 뒤 호출한다(:655-658). 덮어쓰기는 새 dict로 한다(:673). 알림 1줄(:680-686)은 기존 push 경로(:397-398)로 나간다. |
| G2 범위 | PASS | 바뀐 경로 4개(changed-files.txt:1-4)가 allowed_paths(task-prompt.md:13)와 같다. `_held_symbols`·`_watch_members` 추출은 같은 출처를 함께 쓰려는 것이다. `symbols_for_run`의 서명·결과·예외 순서는 그대로다(auto_core.py:98-127). |
| G3 주문·체결 추정 | PASS | diff.patch에 주문 경로 문자열·주문 도구가 없고, 가격으로 체결을 추정하는 코드도 없다. |
| G4 정책·상태 쓰기·fail-closed | PASS | 새 쓰기 경로가 없다. 정책·상태·장부는 읽기만 한다(auto_core.py:142-149, apply_user_confirmed_broker_snapshot.py:52-75).<br>• 집합을 못 읽으면 격리가 꺼진다(auto_core.py:171-172).<br>• 격리 형식이 잘못되면 DecideFailure로 멈춘다(auto_core_decide.py:167-187).<br>• 격리 종목은 "ISOLATED"로 들어가 UNK가 된다(auto_core_rules.py:539-548). 봉을 쓰는 곳은 모두 status OK를 확인한다(auto_core_decide.py:1012, 1067, 1074, 1182). |
| G5 비밀 | PASS | .env·토큰·계좌를 읽지 않는다. 알림 줄에는 종목 코드만 들어간다(auto_core_decide.py:684). |
| G6 테스트 | PASS | 새 테스트 18개(test_auto_core_bar_isolate.py:86-304). load_tests로 이 파일 것만 돈다(:307-324).<br>• 전체 실행 3635→3653(+18)이라 상속 테스트가 두 번 돌지 않는다.<br>• 기존 테스트 수정·skip·expectedFailure 추가는 없다.<br>• new_failures는 [](checks.json:153)이다. |
| G7 class | PASS (class_ok=true) | 주문 단계·도구·예산·상한·승인 상품·대조 불변 조건·kill switch는 바뀌지 않았다. quantity_authority 추가도 없다.<br>checks.json:129의 `ADDED_LINE:kill_switch`는 보고 머리말 문장(diff.patch:247)에서 나왔다. 정지 스위치를 바꾼 것이 아니다. |
| G8-1 diff 구성·권한 표지 | **FAIL** | 코드는 깨끗하다. 그러나 보고 7행(diff.patch:247)이 `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch` 네 이름이 든 새 줄을 만들었다.<br>• 지시문 '지켜야 할 것' 2(task-prompt.md:102, "…가 들어간 줄을 만들거나…", 어기면 FAIL)에 해당한다.<br>• 이 줄 때문에 병합 기록에 경로가 아닌 권한 사유가 붙는다(checks.json:129). 지시문 전제 "경로 때문에 붙는 플래그"(task-prompt.md:9)와 어긋난다.<br>• 같은 선례: docs/claude/dev-runs/first-collect.md:38(1회차 FAIL). |
| G8-2 테스트가 바뀐 동작을 잡음 | PASS | 직접 돌리지 않고 코드로 따라가 확인했다.<br>• auto_core.py:425 분기를 없애면 테스트 1·2가 status FAIL을 받아 실패한다(test:66).<br>• 덮어쓰기(auto_core_decide.py:670-674)를 빼면 bars_loader가 MU를 OK로 돌려준다. 그러면 MU 매수표가 나와(test:230) test:238이 실패한다.<br>• 보유·extra·노출·기준 종목·전역·비 StepFailure 실패는 테스트 3~6이 덮는다(test:111-163). |
| G8-3 격리 종목 매수 0·재배치 아님·매도 같음 | PASS | test:238-243(매수 0건, `redeploy_ranking`·swap_pair에 MU 없음), :252(매도 판정 같음), :255(격리 없을 때 MU가 후보였음). |
| G8-4 실패 없는 날 출력 불변 | PASS | test:176-182(steps.bars 키가 정확히 {status, histories}), test:294-304(decide 출력 같음). status·warnings는 손대지 않았다(auto_core.py:430-432, test:74-75). |
| G8-5 잘못된 격리·T1 FAIL 경로 | PASS | test:265-285(11가지 경우 모두 FAIL `T1_BARS_ISOLATED_INVALID`), test:287-291. T1 FAIL→HOLD 경로(auto_core_decide.py:468-471)는 바뀌지 않았다. |
| G8-6 대상 테스트 | PASS | checks.json:157-166: Ran 622, 실패 0. 전체 실행의 실패 1건은 기준선에도 있던 것이다(checks.json:4, :145-147). |
| G8-7 / G9 연결표 | **FAIL** | 인용된 행은 모두 원문과 맞다(아래 '맞는 행'). trig id 2개는 `trig_`로 시작한다.<br>원문 행도 '끊김(…)'도 없는 칸이 셋 있다.<br>• 2행 ⑤ "사장실 결과 모음… 새 테스트 8"(task-prompt.md:125)<br>• 3행 ② "auto_core_decide.py 07:45 KST"(줄 번호 없음, :126)<br>• 3행 ⑤ "⑫ 알림 자체로 보임"(:126)<br>보고 6절 표가 이 칸들을 그대로 옮겼다(diff.patch:336-337). |
| G8-8 격리 가능 종목 제외·꺼짐·새 dict | PASS | 다섯 가지가 모두 빠진다(auto_core.py:166-173). 기준 종목 값은 "SOXX"·"GRID"다(auto_core_rules.py:64-67; decide의 benchmarks ⊆ {SOXX, GRID}, :991-993). 어느 하나라도 예외면 빈 집합(:171-172). 덮어쓰기는 `{**loaded, ...}`로 새 dict이고(auto_core_decide.py:673), 원본이 안 바뀐 것을 test:247이 확인한다. |

**G9 맞는 행:**
- register_auto_core_task.ps1:25(06:15 AutoCore), :27(07:45 Decide)
- auto_core.py 옛 347-360(diff.patch:109-147)
- auto_core_decide.py 옛 434-436 → 지금 465-467, 옛 366-367 → 지금 397-398
- collect_30m.ps1:43-67(최신부터 페이지마다 저장, 실패하면 exit 1)
- auto-core-alert.txt:42 ⑦, :47 ⑫
- read.py:44 `D PUSH`
- t2rc-oracle.py:214(페이지 직접 glob), :1568-1571(`missing_in_core`)

```json
{"verdict": "FAIL", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:15-21,131,134-154,157-173,408-432; manage-us-stock-strategy/scripts/auto_core_decide.py:179-207,655-686"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/bar-isolate/changed-files.txt:1-4; task-prompt.md:13; auto_core.py:98-127"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/bar-isolate/diff.patch:1-674 (no order markers)"}, {"id": "G4", "result": "PASS", "evidence": "auto_core.py:142-149,171-172; auto_core_decide.py:167-187,673,1012,1067,1074,1182; auto_core_rules.py:539-548"}, {"id": "G5", "result": "PASS", "evidence": "diff.patch:1-674; auto_core_decide.py:684"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py:86-324; checks.json:5,148,153"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:129 ADDED_LINE:kill_switch comes from report prose diff.patch:247; no kill switch/limit/order-stage/quantity_authority change"}, {"id": "G8", "result": "FAIL", "evidence": "docs/claude/bar-isolate-report.md:7 (diff.patch:247) creates a line containing order_authority/quantity_authority/execution_quantity/kill_switch, violating task-prompt.md:102 and producing checks.json:129 against task-prompt.md:9 (precedent docs/claude/dev-runs/first-collect.md:38); items 2-6 and 8 PASS (test:66,230,238-255,176-182,265-291,294-304; checks.json:157-166); item 7 see G9"}, {"id": "G9", "result": "FAIL", "evidence": "task-prompt.md:125 row 2 cell 5 and task-prompt.md:126 row 3 cells 2 and 5 carry neither file:line/trig id nor 끊김(…), copied into docs/claude/bar-isolate-report.md:96-97 (diff.patch:336-337); all cited lines verified: register_auto_core_task.ps1:25,27; collect_30m.ps1:43-67; auto-core-alert.txt:42,47; read.py:44; t2rc-oracle.py:214,1568-1571; auto_core_decide.py:397-398,465-467"}], "min_fixes": ["docs/claude/bar-isolate-report.md:7 - rewrite the front-matter authority line so it contains none of the literal names order_authority, quantity_authority, execution_quantity, kill_switch (e.g. '권한 표지 4종 줄 변경 없음 · 주문 경로 없음 · 스키마 변경 없음 · 키움 호출 없음'); leave code and tests unchanged so class_reasons become AUTHORITY_PATH only", "docs/claude/bar-isolate-report.md:96 (6절 연결표 2행) cell 5 - cite the source of '사장실 결과 모음 sees no run' as a trig id plus prompt line (room digest trig_01GrAs6UCfspeTBK3mMncyrd / trig_01XChapmUEKxAcjKF9AFiERJ per docs/claude/active-decisions.md:62) and cite new test 8 as manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py:228-255; if the room-digest line cannot be cited, write '끊김 — 메울 변경 · 승인 경로' instead", "docs/claude/bar-isolate-report.md:97 (6절 연결표 3행) - cell 2: cite manage-us-stock-strategy/scripts/auto_core_decide.py:762 (candidates) and register_auto_core_task.ps1:27 (07:45); cell 5: cite docs/claude/scheduled-prompts/auto-core-alert.txt:47 (⑫)"]}
```

VERDICT: FAIL

## Judge 보고 원문 (2회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core.py:157-173에서 격리 가능 종목 = 관심 − 보유 − extra − 노출 검토 종목 − RREC 기준 종목이고, 읽다 예외가 나면 빈 집합입니다. 수집 루프(auto_core.py:408-432)는 StepFailure이면서 사유가 ISOLATABLE_REASONS(:131)일 때만 격리하고 나머지는 raise합니다. decide는 t1_isolated(auto_core_decide.py:183-207)로 읽고, 새 dict로 덮어쓰며(:670-674), 알림 1줄을 냅니다(:680-686). 하드코딩·TODO는 없습니다 |
| G2 범위 | PASS | changed-files.txt:1-4가 allowed_paths 4개와 같습니다. symbols_for_run은 서명·결과·예외 순서가 그대로이고(auto_core.py:122-127), 도우미로 떼어 낸 것은 같은 출처를 다시 쓰기 위해서입니다 |
| G3 주문·체결 추정 | PASS | diff에 주문 경로 문자열이 없습니다(+/− 줄 grep 0건). 체결 추정 코드도 없습니다 |
| G4 정책·상태 쓰기 / fail-closed | PASS | exposure_review_symbols(auto_core.py:134-154)는 읽기만 합니다. ledger_status는 읽기 전용입니다(apply_user_confirmed_broker_snapshot.py:52-75). 집합을 못 읽으면 격리를 끄고(:171-172), 형식이 잘못되면 decide FAIL입니다(auto_core_decide.py:188-197, 202, 206). 격리 종목은 status ISOLATED라 소비처가 모두 OK일 때만 씁니다(auto_core_decide.py:1012, 1067, 1074, 1182) |
| G5 비밀 | PASS | 새로 읽는 것은 alert 정책·상태·장부·관심 명단·기존 shadow 스냅숏이고 출력은 종목 코드와 StepFailure 사유뿐입니다(auto_core.py:426, auto_core_decide.py:684) |
| G6 단언·skip·테스트 | PASS | 기존 테스트 파일은 고치지 않았습니다. skip 추가와 expectedFailure 증가가 없습니다(checks.json:149, 165). 새 테스트 18개가 지시문 1~10을 모두 덮습니다(test_auto_core_bar_isolate.py:86-183, 228-305). load_tests로 이 파일 것만 돕니다(:307-324) |
| G7 class | PASS | 권한 표지 4종 줄이 diff에 없습니다. class_reasons는 AUTHORITY_PATH뿐입니다(checks.json:141-145). 대조 불변식·한도·주문 단계·킬 스위치는 바뀌지 않았습니다. 다만 격리만 있는 날은 status OK라 T1 compare streak에 셉니다(auto_core.py:401, 463-465). 지시문 37행이 정한 동작이고, 결과는 next_action 문구일 뿐 I1-I5는 그대로입니다 |
| G8-1 diff 구성 | PASS | 위 G2·G3, 그리고 diff.patch에 schemas 변경이 없습니다 |
| G8-2 테스트가 동작을 잡음 | PASS | 변이 확인은 Builder 보고 근거입니다(bar-isolate-report.md:66 — diff.patch:311). daily 격리 분기를 끄면 테스트 1·2가 실패하고, decide 덮어쓰기를 빼면 테스트 8의 매수 0건 단언이 실패한다고 적혀 있습니다. 보유·extra·노출·기준·전역·비 StepFailure 실패가 FAIL인지는 test_auto_core_bar_isolate.py:111-163에서 확인합니다 |
| G8-3 매수 0·재배치 제외·매도 동일 | PASS | test_auto_core_bar_isolate.py:238-255. 재배치 제외는 redeploy_ranking(auto_core_decide.py:1262-1277)의 실제 결과와 swap_pair(auto_core_tickets.py:1309-1312)로 확인합니다 |
| G8-4 실패 없는 날 불변 | PASS | test_auto_core_bar_isolate.py:176-182(키 정확히 status·histories), :294-304(decide 결과 같음). steps.bars.status, result.status, warnings는 손대지 않았습니다(auto_core.py:430-432) |
| G8-5 잘못된 항목 FAIL / T1 FAIL 경로 | PASS | test_auto_core_bar_isolate.py:265-291. T1 FAIL 판정 줄은 바뀌지 않았습니다(auto_core_decide.py:468) |
| G8-6 대상 테스트 | PASS | checks.json:169-178에서 test_auto_core*.py Ran 622, 실패 0입니다. 전체 실패 1건은 기준선과 같고 new_failures는 비어 있습니다(:4, 165) |
| G8-7 연결표 원문 행 | PASS | register_auto_core_task.ps1:25(06:15), :27(07:45). collect_30m.ps1:43-70(최신부터 저장, 실패 시 exit 1). auto-core-alert.txt:42 ⑦, :47 ⑫. read.py:44 'D PUSH'. t2rc-oracle.py:214, 1568-1571. auto_core_decide.py:762 |
| G8-8 격리 가능 종목·새 dict | PASS | auto_core.py:163-173. 노출 출처는 run_portfolio_exposure_review.py:505-530, 기본 경로는 :52-53, 585-586입니다. RREC 값은 auto_core_rules.py:64-67, 993과 같습니다. 새 dict는 auto_core_decide.py:673, 테스트는 test_auto_core_bar_isolate.py:247입니다 |
| G9 연결표 | PASS | 보고서 6절(diff.patch:335-337)의 ②③⑤ 칸을 원문과 대조했고 모두 맞습니다. 2행 ⑤는 active-decisions.md:62(trig id 2개)와 room-digest.txt:2, 5, 7-20, 28을 인용합니다. 안 돈 날 감지는 '끊김(메울 변경·승인 경로)'으로 표시돼 있습니다. 테스트 인용(test_auto_core_bar_isolate.py:228-255)도 맞습니다. 3행 ⑥은 끊김과 메울 변경·승인 경로가 함께 적혀 있습니다 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:157-173,408-432; manage-us-stock-strategy/scripts/auto_core_decide.py:183-207,657-686"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/bar-isolate/changed-files.txt:1-4; manage-us-stock-strategy/scripts/auto_core.py:122-127"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/bar-isolate/diff.patch (no order path strings in +/- lines)"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:134-154,171-172; manage-us-stock-strategy/scripts/apply_user_confirmed_broker_snapshot.py:52-75; manage-us-stock-strategy/scripts/auto_core_decide.py:188-206,1012,1067,1074,1182"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core.py:426; manage-us-stock-strategy/scripts/auto_core_decide.py:684"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_bar_isolate.py:86-183,228-305,307-324; workspace/outputs/dev-runs/bar-isolate/checks.json:149,165"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/bar-isolate/checks.json:141-145 (AUTHORITY_PATH only); no authority-marker lines in diff; T1 compare streak counts an isolated-only day per task-prompt.md:37 (auto_core.py:401,463-465), invariants I1-I5 untouched"}, {"id": "G8", "result": "PASS", "evidence": "test_auto_core_bar_isolate.py:111-163,238-255,265-304; auto_core_decide.py:468,673; checks.json:169-178; register_auto_core_task.ps1:25,27; collect_30m.ps1:43-70; auto-core-alert.txt:42,47; read.py:44; t2rc-oracle.py:214,1568-1571; run_portfolio_exposure_review.py:505-530"}, {"id": "G9", "result": "PASS", "evidence": "docs/claude/bar-isolate-report.md 6절 (diff.patch:335-337); docs/claude/active-decisions.md:62; docs/claude/scheduled-prompts/room-digest.txt:2,5,7-20,28; manage-us-stock-strategy/scripts/auto_core_decide.py:762"}], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/bar-isolate/ 의 원본 기록입니다.)
