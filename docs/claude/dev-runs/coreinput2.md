# dev-run coreinput2 — NEEDS_APPROVAL

- 시각(UTC): 2026-11-01T10:30:07Z → 2026-11-01T10:56:00Z
- 기준 커밋(base): `e174d5c1407e3c3efe3c9eae59af453e58aaa821` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_inputs.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_input_guard.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3443 · 실패 283 → 변경 후 Ran 3473 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `dd8602b89de334bd360935236aff2847330a58d34bf52a8110716a7d39c58f7c`
- Judge 파일 sha256: `879fc7c6928da05c2d947974cfc605824e0f187bc8a4898d2c625a5263384b09`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 coreinput2 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/coreinput2-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_inputs.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_input_guard.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 입력 4종 보호가 실제로 구현됐다. 가드 `auto_core_inputs.py:208-251`, 매수 차단 `auto_core_tickets.py:823`, 후보 제거 `auto_core_tickets.py:741-742`, 설명 파일 검사 `auto_core_decide.py:825-837`. 빈 껍데기·하드코딩·TODO 없음 |
| G2 범위 | PASS | `changed-files.txt:1-5`의 5개 경로가 allowed_paths와 일치한다. `checks.json:117`의 reasons는 빈 배열이고, `auto_core_tickets.py`는 참고 diff와 blob `f38dbde`까지 같다 |
| G3 주문·체결 추정 | PASS | diff에 주문 경로, 키움 호출, 가격 기반 체결 추정이 없다(`diff.patch:1-733`) |
| G4 쓰기 경로·fail-closed | PASS | 새 쓰기 경로가 없고 새 값은 `decision["inputs"]`에만 들어간다(`auto_core_decide.py:576`). 없음·오류는 사유로 남는다(`auto_core_inputs.py:230-233, 247-249`) |
| G5 비밀 | PASS | 문서 3종의 경로·해시·사유 이름만 다룬다(`auto_core_inputs.py:226-246`). `.env*`·토큰·계좌 식별자를 읽거나 출력하지 않는다 |
| G6 테스트 | PASS | 기존 테스트 변경 없음. skip·expectedFailure 없음(새 테스트 파일 grep 0건). 전체 실행 수 3443→3473, skipped 3→3, `new_failures` 빈 배열(`checks.json:5-7, 411-416`) |
| G7 class | PASS | 주문 단계·주문 도구·예산·상한·종목 상한·승인 상품·대조 불변 조건·kill switch 변경이 없고 quantity_authority 값 추가도 없어 class_ok=true다. 선언 class가 authority이므로 PASS면 `NEEDS_APPROVAL`이 된다(`tools/dev_pipeline/devpipe.py:1869, 1940`) |
| G8-1 허용 파일 | PASS | 보고서는 `coreinput2-report.md`이고 스키마·정책·기존 테스트는 무변경이다(`changed-files.txt:1-5`) |
| G8-2 검사 목록 | PASS | decide의 docs/claude 판정 입력은 R-REC1(`auto_core_decide.py:569`), M6(`auto_core_inputs.py:196-197`), 관심 명단(`auto_core_inputs.py:151`), 설명 파일(`auto_core_compare.py:303`), 이미 커밋 검사가 있는 등록부(`auto_core_inputs.py:141`), 절 해시로 고정된 카드 문서(`auto_core_inputs.py:172-179`)뿐이다. `auto_core_rules.py`·`auto_core_tickets.py`에는 파일 읽기가 없다 |
| G8-3 fail-closed | PASS | 미커밋·없음·링크·git 실패·가드 오류가 모두 매수 사유가 된다(`auto_core_inputs.py:232, 235, 239-243, 247-249`, `auto_core_tickets.py:1129-1131`). 가드는 예외를 내지 않아 decide가 FAIL이 되지 않는다. 모두 커밋이면 동일함을 `test_a_all_committed_changes_nothing`이 확인한다 |
| G8-4 반례 탐색 | PASS | 검사 시점은 연구 대기 전이다(`auto_core_decide.py:569-583`). `recovery_text` 재읽기가 없다. 가드 사유는 매도 경로에 들어가지 않는다(`auto_core_tickets.py:805`). 매수 표는 `_plan_buy`→`_buy_ticket`으로만 나오고(`:825, :1116`), `hold_eval`은 ctx를 복사해 input_block을 이어받는다(`auto_core_decide.py:1169`). `_limit_daily`는 표를 줄이기만 한다(`auto_core_tickets.py:1221-1225`). `_no_new_session`은 새 표를 내지 않는다. 이름 바꾸기·사본은 glob과 git 검사로 잡히고, M6 삭제는 조이는 쪽이다(`auto_core_rules.py:988-993`). 관심 명단 삭제는 지시문대로 사유를 만들지 않으며, 대체 섹터도 커밋된 등록부 값이다(`auto_core_decide.py:606-607`). None 대체(`auto_core_decide.py:446`)와 후보 None 위치(`auto_core_tickets.py:738-742`)도 맞다 |
| G8-5 테스트·보고 | PASS | 사례 a~l이 모두 있고(`test_auto_core_input_guard.py`, 30건) skip이 없다. 보고 (a)~(c)와 "표지 없음"이 있다(`coreinput2-report.md:61-65`). 보고가 남긴 관심 명단 쓰기 시점은 토 10:20 실행 후 `_pending` 커밋 경로라 평일 07:45와 겹치지 않는다(`docs/claude/scheduled-prompts/README.md:17`, `watchlist-weekly-rescore.txt:312`) |
| G8-6 참고 diff 대조 | PASS | 다른 곳은 "이번에 다른 점" 1~5뿐이다. 알림은 `\u` 복호화 결과가 B절과 글자 그대로 같다(`auto_core_decide.py:580-582`). 테스트 이름 2개 변경은 3번의 문장 정리이고 단언은 같다. "매도 그대로" 잔존은 부정 단언(`test_auto_core_input_guard.py:280`)뿐이고, 옛 주석 인용은 보고서 대조표(`coreinput2-report.md:55`)뿐이다 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "auto_core_inputs.py:208-251; auto_core_tickets.py:741-742,823; auto_core_decide.py:825-837"}, {"id": "G2", "result": "PASS", "evidence": "changed-files.txt:1-5; checks.json:117"}, {"id": "G3", "result": "PASS", "evidence": "diff.patch:1-733"}, {"id": "G4", "result": "PASS", "evidence": "auto_core_decide.py:576; auto_core_inputs.py:230-233,247-249"}, {"id": "G5", "result": "PASS", "evidence": "auto_core_inputs.py:226-246"}, {"id": "G6", "result": "PASS", "evidence": "test_auto_core_input_guard.py; checks.json:5-7,411-416"}, {"id": "G7", "result": "PASS", "evidence": "diff.patch:1-733; tools/dev_pipeline/devpipe.py:1869,1940"}, {"id": "G8", "result": "PASS", "evidence": "item 1 changed-files.txt:1-5; item 2 auto_core_decide.py:569, auto_core_inputs.py:141,151,172-179,196-197, auto_core_compare.py:303; item 3 auto_core_inputs.py:232-249, auto_core_tickets.py:1129-1131; item 4 auto_core_decide.py:446,569-583,1169, auto_core_tickets.py:738-742,805,825,1221-1225, auto_core_rules.py:988-993; item 5 coreinput2-report.md:61-65, checks.json:416; item 6 auto_core_decide.py:580-582, test_auto_core_input_guard.py:280, coreinput2-report.md:55"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-01T12:34:41Z
- 병합 커밋: `db563031b703e29be38c7079c6010c66e4ef756c` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-11-01T12:34:39Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/coreinput2/ 의 원본 기록입니다.)
