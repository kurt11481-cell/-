# dev-run event-ctx4 — READY_TO_MERGE

- 시각(UTC): 2026-10-14T05:40:05Z → 2026-10-14T06:18:10Z
- 기준 커밋(base): `1a2b7d6f944651f4bc142baef6ee2ea117b70c77` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 1
- 테스트: 기준선 Ran 3026 · 실패 28 → 변경 후 Ran 3047 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `ae1e4feb76aedf9b6a235502aa1b6695ea8982afdbfb4a33ba630d3bbb9a04f7`
- Judge 파일 sha256: `2acb71f620d4bf2ad4eae887eae6ea175d724c47d86bedb5ae4de33eeb7661c7`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 event-ctx4`

## 바뀐 파일

- `docs/claude/event-ctx4-report.md`
- `manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json`
- `manage-us-stock-strategy/references/decision-journal-cards.md`
- `manage-us-stock-strategy/scripts/event_calendar.py`
- `manage-us-stock-strategy/scripts/score_decision_journal.py`
- `manage-us-stock-strategy/tests/test_event_calendar.py`
- `manage-us-stock-strategy/tests/test_score_ticket_outcomes.py`

## Judge 보고 원문 (1회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `event_calendar.py`에 load·landing·exposure·exposure_line·CLI가 모두 있고(event_calendar.py:102, 146, 223-276, 292, 387), 채점기는 주문표 행마다 event_exposure를 붙이고 요약에 2키를 더함(score_decision_journal.py:514-554, 583, 641-643). TODO나 하드코딩 없음 |
| G2 범위 | PASS | 바뀐 7개 경로가 모두 allowed_paths 안(changed-files.txt:1-7, checks.json:17-25). 무시 파일(state)은 실행 전 스냅샷 대비 변화 없음(checks.json:118 status OK, devpipe.py:775) |
| G3 주문·체결 추정 | PASS | 주문 경로나 키움 호출 없음. 세션 일정은 늦게 import하며 읽기만 함(event_calendar.py:322-326). 체결 시각은 core_close_at만 씀(event_calendar.py:173-175, 235) |
| G4 쓰기 경로·fail-closed | PASS | event_calendar.py는 파일 쓰기 0(test_event_calendar.py:313-323). 채점기는 기존 write_report만 씀(score_decision_journal.py:757-765). 일정표가 없거나 깨지면 상태로만 남음(score_decision_journal.py:517-528) |
| G5 비밀 | PASS | 읽는 것은 일정표·결정 파일·로캘뿐. 계좌·토큰 접근 없음(event_calendar.py:26-34, 102-143, 329-338) |
| G6 테스트 | FAIL | 단언 약화나 skip은 없음(test_score_ticket_outcomes.py:316-318은 정확 집합 확장). 다만 timing 없는 자기 실적의 새 날짜 분류(earlier)는 문제가 되는 직전 세션 경우를 검증하지 않음(test_event_calendar.py:146-160) |
| G7 class | PASS | class general, class_reasons 빈 배열(checks.json:112-113). 새로 추가된 줄에 권한 금지어 0(diff.patch `^\+` 검색 결과 없음) |
| G8 J-a 범위·무변경 | PASS | changed-files.txt:1-7. 코어·일지·정책·일정표 파일은 바뀌지 않음 |
| G8 J-b 채점값 불변 | PASS | 인자 없음 기준선과 없음·있음·깨짐 세 경우를 JSON과 렌더 줄에서 모두 비교함(test_score_ticket_outcomes.py:354-362, 385-424). event_exposure는 `_score_ticket` 뒤에 별도 키로만 붙음(score_decision_journal.py:637-642) |
| G8 J-c 착지·경계·조기폐장·서머타임 | PASS | 경계 구현(event_calendar.py:178-191, 240-249)과 테스트(test_event_calendar.py:96-139). 11/27 13:00 조기 폐장과 11/26 건너뛰기(121-128), EST 전환(114-119) 확인 |
| G8 J-d 매수 떠안음·매도 피함 | PASS | 로캘 `event_overnight_buy/sell` 키와 event_calendar.py:305, 테스트(test_event_calendar.py:176-185) |
| G8 J-e 코어 비입력 | PASS | decide는 채점기 종료 코드와 예외만 score_warning에 남김(auto_core_decide.py:839-844, 1111-1114). journal 블록은 해시에서 빠짐(auto_core_decide.py:857). 일정표가 깨져도 상태만 바뀜(test_score_ticket_outcomes.py:437-461) |
| G8 J-f CLI | PASS | 실패 시 exit 0과 상태를 출력하고, 인자 오류만 exit 2(event_calendar.py:387-419, 397). 실행 전후 임시 폴더가 같은지 확인(test_event_calendar.py:256-260, 286-310) |
| G8 J-g ASCII·테스트 격리·키 이름 | PASS | ASCII 검사(test_event_calendar.py:313-319). 테스트는 픽스처·임시 파일만 쓰고 세션 일정 로더도 주입함(test_event_calendar.py:1-5, 228-254). 새 키에 stop·limit·qty·price 없음(271-279) |
| G8 J-h 자기 실적 | FAIL | timing이 없으면 지시상 position은 unplaced여야 함(task-prompt.md:67). 그런데 구현은 `announced < session`이면 earlier로 둠(event_calendar.py:210-212). 예: 세션 10/28, 실적 10/27, timing 없음. 실제로 AFTER_CLOSE였다면 착지가 10/27 16:01로 prev(10/27 16:00)보다 늦어 before_fill인데 earlier로 확정 기록됨. earlier는 SHOWN_OWN_POSITIONS(event_calendar.py:55)에 없어서 표시 줄에서도 사라짐. 시각 정보가 없는데 "시점 확인 필요"로 보이지 않고 확정값으로 기록·숨김 처리되는 것으로, fail-closed 위반 |

```json
{"verdict": "FAIL", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:223-276; manage-us-stock-strategy/scripts/score_decision_journal.py:514-554,641-643"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx4/changed-files.txt:1-7; checks.json:17-25"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:173-175,322-326"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:517-528,757-765; manage-us-stock-strategy/tests/test_event_calendar.py:313-323"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:26-34,102-143,329-338"}, {"id": "G6", "result": "FAIL", "evidence": "manage-us-stock-strategy/tests/test_event_calendar.py:146-160 (no case: announcement on the previous session without timing)"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx4/checks.json:112-113"}, {"id": "J-a", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx4/changed-files.txt:1-7"}, {"id": "J-b", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:354-362,385-424"}, {"id": "J-c", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:178-191,240-249; manage-us-stock-strategy/tests/test_event_calendar.py:96-139"}, {"id": "J-d", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:305; manage-us-stock-strategy/tests/test_event_calendar.py:176-185"}, {"id": "J-e", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:839-844,857,1111-1114; manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:437-461"}, {"id": "J-f", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:387-419; manage-us-stock-strategy/tests/test_event_calendar.py:256-310"}, {"id": "J-g", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_event_calendar.py:1-5,271-279,313-323"}, {"id": "J-h", "result": "FAIL", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:210-212 vs workspace/outputs/dev-runs/event-ctx4/task-prompt.md:67"}], "min_fixes": ["event_calendar.py _own_earnings (210-215): for a record without timing, return earlier only when announcement_session is before the previous session's date (when the ticket session is the first calendar session, keep the current comparison with the session date); in every other case, including the previous session date or a non-session day between it and the ticket session, return unplaced as instructed (task-prompt.md:67). later (date after the fifth next session) may stay", "test_event_calendar.py OwnEarningsTests: add a case where session 2026-10-28 has announcement_session 2026-10-27 with no timing, asserting position unplaced and that the line contains '시각 미정' and '시점 확인 필요'; add a case with no timing where the announcement is before the previous session, asserting earlier", "docs/claude/event-ctx4-report.md interpretation item 1: rewrite the date rule for earnings without timing to match the fix"]}
```
VERDICT: FAIL

## Judge 보고 원문 (2회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `manage-us-stock-strategy/scripts/event_calendar.py:102`(load), `:146`(착지), `:178`(경계), `:226`(exposure), `:296`(문장), `:391`(CLI); `manage-us-stock-strategy/scripts/score_decision_journal.py:514`, `:641`, `:873`. 빈 껍데기·하드코딩·TODO 없음 |
| G2 범위 | PASS | `workspace/outputs/dev-runs/event-ctx4/changed-files.txt:1-7`의 7개 경로가 모두 allowed_paths 안에 있음. `checks.json:129-135` class general, reasons 비어 있음 |
| G3 주문·체결 추정 | PASS | 주문·키움 호출이 없음. 체결 시각은 세션 일정 `core_close_at`만 사용함(`event_calendar.py:243-247`) |
| G4 쓰기 경로·fail-closed | PASS | event_calendar.py에는 쓰기 호출이 없음(AST 검사 `test_event_calendar.py:328`). 채점기 쓰기 위치는 바뀌지 않음(`score_decision_journal.py:744-765`). 일정표 없음·깨짐은 상태로만 남김(`score_decision_journal.py:517-528`) |
| G5 비밀 | PASS | env·토큰·계좌를 읽지 않음. 세션 일정은 기존 로더를 그대로 씀(`event_calendar.py:326-330`) |
| G6 단언·테스트 | PASS | diff에서 지운 줄은 기계적 치환뿐이고 skip·expectedFailure 추가 없음. 새 동작마다 T1~T8 테스트가 있음. 대상 테스트 18/14/36 OK, 새 실패 0(`checks.json:178-206`) |
| G7 class | PASS | 새 줄에 금지어 0건(diff grep). 권한·예산·상한·수량 권한 값 추가 없음 |
| J-a | PASS | 바뀐 파일이 allowed_paths 안뿐임. auto_core*·정책·일지·결정·일정표 파일은 바뀌지 않음 |
| J-b | PASS | `test_score_ticket_outcomes.py:385`: 인자 없음·없음·있음·깨짐 네 보고서를 `without_event_fields`(`:354`)와 문구 제거 후 직접 비교함. 성적 값 계산부는 바뀌지 않음 |
| J-c | PASS | `event_calendar.py:178-191`: prev < 착지 ≤ F, F < 착지 ≤ F1, F5 경계가 지시대로임. 조기 폐장은 `test_event_calendar.py:121`, 서머타임은 `:114`와 `:88`에서 확인함 |
| J-d | PASS | 로캘 `portfolio-exposure-ko-KR.json:63-64`(떠안음/피함), 테스트 `test_event_calendar.py:192-200` |
| J-e | PASS | decide는 `_score(journal_path)`에 경로만 넘김(`auto_core_decide.py:1111-1114`). 반환값은 `journal.score_warning`에만 들어가고(`:840-844`), `journal`은 해시에서 빠짐(`:857`). 일정표가 깨져도 exit 0이고 상태만 바뀜(`score_decision_journal.py:873`, `:882`). 일정표를 import하는 곳은 채점기뿐임 |
| J-h | PASS | `event_calendar.py:194-218`: BEFORE_OPEN은 09:00 ET, AFTER_CLOSE는 core_close+1분, 자료 없으면 null. 1회차 min_fixes(직전 세션일·휴장일 → unplaced, 그보다 앞 → earlier)가 반영됨(`test_event_calendar.py:174-188`) |
| J-f | PASS | CLI는 파일을 쓰지 않음(실행 전후 비교 `test_event_calendar.py:276`). 실패는 exit 0과 상태(`:302-317`), 인자 오류만 exit 2(`:319-325`) |
| J-g | PASS | 두 스크립트가 ASCII 디코드를 통과함(`test_event_calendar.py:329-332`). 새 테스트는 임시 파일·픽스처만 씀. 새 키 이름에 stop·limit·qty·price가 없음(`:298-300`) |
| G8 | PASS | 위 J-a~J-h 참조. 병합을 막지 않는 참고 3건: ① allowed_paths 밖 기존 `test_decision_journal_cards.py:642`가 기본 경로로 저장소 일정표를 읽기만 함(단언과 무관, 보고서 해석 7에 적힘). ② 일정표는 OK인데 세션 일정이 없으면 요약 문구가 "밤새 0건"으로 나옴. 이때 행 JSON 상태와 horizons 사유에는 미확인이 보임. ③ CLI에서 decision의 timing 값이 해시 불가능한 형식이면 예외가 남. 결정론 코어가 만드는 값이라 실제로 생기기 어려움 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:102-422; manage-us-stock-strategy/scripts/score_decision_journal.py:503-554,641,873"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx4/changed-files.txt:1-7; checks.json:129-135"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:243-247"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:517-528,744-765; manage-us-stock-strategy/tests/test_event_calendar.py:328-339"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:326-330"}, {"id": "G6", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx4/checks.json:178-206; diff.patch removed lines 43-302 mechanical only"}, {"id": "G7", "result": "PASS", "evidence": "diff.patch added lines: no authority terms; checks.json:129-130"}, {"id": "J-a", "result": "PASS", "evidence": "workspace/outputs/dev-runs/event-ctx4/changed-files.txt:1-7"}, {"id": "J-b", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:354-424"}, {"id": "J-c", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:178-191,243-252; manage-us-stock-strategy/tests/test_event_calendar.py:95-139"}, {"id": "J-d", "result": "PASS", "evidence": "manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json:63-64; manage-us-stock-strategy/tests/test_event_calendar.py:192-200"}, {"id": "J-e", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:840-844,857,1111-1114; manage-us-stock-strategy/scripts/score_decision_journal.py:873,882"}, {"id": "J-h", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:194-218; manage-us-stock-strategy/tests/test_event_calendar.py:142-188"}, {"id": "J-f", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/event_calendar.py:391-423; manage-us-stock-strategy/tests/test_event_calendar.py:272-325"}, {"id": "J-g", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_event_calendar.py:298-300,328-339"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-14T06:28:32Z
- 병합 커밋: `47e35fe851de30ae501cd690319474c4e2b0a98b` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/event-ctx4/ 의 원본 기록입니다.)
