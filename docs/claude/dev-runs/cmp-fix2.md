# dev-run cmp-fix2 — NEEDS_APPROVAL

- 시각(UTC): 2026-10-13T01:20:07Z → 2026-10-13T01:40:23Z
- 기준 커밋(base): `5ccc6b7a5cb24f01140b424e5e729660bc055b6b` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ADDED_LINE:kill_switch, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_compare.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_rules.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_compare_fix.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 2952 · 실패 28 → 변경 후 Ran 2964 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `cf6e45bac63636d3b8b2a0ccb21730540ed8acb40bdbf3e6ead7702acf665c9d`
- Judge 파일 sha256: `a87a03a57d48a69d91f45edcf946e2106f7215d23a6b968af8c473e58cebc501`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 cmp-fix2 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/cmp-fix2-report.md`
- `manage-us-stock-strategy/scripts/auto_core_compare.py`
- `manage-us-stock-strategy/scripts/auto_core_rules.py`
- `manage-us-stock-strategy/tests/test_auto_core_compare_fix.py`

## Judge 보고 원문 (1회차 PASS)

## cmp-fix2 Judge 판정

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `auto_core_rules.py:398-404`(`_event_day`), `:568-576`·`:610-612`·`:626-627`(hit일 때만 충족일 기록), `:629-630`·`:638-647`(여유 계산을 판정 뒤로 옮기고 충족일 값으로 덮어씀), `:650-681`(기존 본문을 인덱스만 받게 옮김), `auto_core_compare.py:121-132`·`:232-233`(caps를 종목 코드로 비교). 빈 껍데기·하드코딩·TODO 없음 |
| G2 범위 | PASS | `changed-files.txt:1-4`, `checks.json:17-22`. 바뀐 경로 4개 모두 allowed_paths 안. 목표와 무관한 변경 없음(`import re`는 caps 정규식용) |
| G3 주문·키움·체결 추정 | PASS | `diff.patch` 전체: 주문 경로, 키움 호출, 체결 추정 코드 없음. 표시·분류 함수만 바뀜 |
| G4 정책·상태 쓰기 / fail-closed | PASS | `auto_core_rules.py:638-647`은 dict만 돌려줌. 테스트 픽스처는 임시 폴더만 씀(`test_auto_core_decide.py:73-94`). 코드를 못 뽑으면 B7(`auto_core_compare.py:128-129`), hit가 아니면 충족일 없음(`auto_core_rules.py:401-402`) |
| G5 비밀·계좌 | PASS | `diff.patch`: .env, 토큰, 계좌를 읽거나 출력하는 곳 없음 |
| G6 단언·skip·새 테스트 | PASS | `test_auto_core_compare_fix.py:360-586` 테스트 12개(T1~T5와 보강). 기존 테스트는 무변경. `checks.json:142` new_failures 없음, `:145-153` test_auto_core* Ran 324 OK(skip 1은 기존 것). expectedFailure 없음 |
| G7 class | PASS | 주문 단계, 주문 도구, 예산, 상한, 종목 상한값, 승인 상품, 대조 불변 조건, kill switch 모두 무변경. quantity_authority 추가 없음. `checks.json:90`의 `ADDED_LINE:kill_switch`는 보고서 본문의 점검 문장 하나(`docs/claude/cmp-fix2-report.md:92`)라서 권한 표지가 아님 |
| G8-1 diff 구성 | PASS | `changed-files.txt:1-4`: group_margins와 호출 위치, caps 비교, 새 테스트, 보고서만 바뀜 |
| G8-2 hit일 때만 충족일 여유 | PASS | `auto_core_rules.py:572`(`today != "hit"`이면 건너뜀), `:643-646`. 테스트 `test_auto_core_compare_fix.py:412-443`(none·unk·상태형은 변경 전 값과 같음) |
| G8-3 같은 창과 같은 해소 규칙 | PASS | `auto_core_rules.py:401-404`가 `_event_state`(`:383-395`)를 그대로 불러서 쓰고, 같은 `EVENT_WINDOW_SESSIONS` 창에서 `fired[-1]`을 고름. 테스트 `test_auto_core_compare_fix.py:445-460` |
| G8-4 caps 종목 코드 / 못 뽑으면 B7 | PASS | `auto_core_compare.py:127-132`. 테스트 `test_auto_core_compare_fix.py:499-522`(B1, CAP_SET, UNPARSED, 빈 목록, 소문자, 일부만 못 뽑음, timing) |
| G8-5 판정·주문표·관문·알림·일지·결정 키 불변, 부록 B 불변 | PASS | `test_auto_core_compare_fix.py:557-586`(T5). 결정 키는 margins를 쓰지 않음(`auto_core_tickets.py:382-384`). 한계값과 범주는 그대로(`auto_core_compare.py:38-49`). 참고: `decision_sha256`은 margins와 commit_sha를 포함한 기록 전체의 해시라서(`auto_core_decide.py:691-707`) 병합하면 어차피 바뀐다. margins 때문에 생기는 차이는 이 작업에 원래 따라오는 것이고 보고서에 밝혀져 있음 |
| G8-6 권한 표지·주문 문자열·키움·정책 | PASS | 고친 두 스크립트와 새 테스트에서 해당 문자열 0건, ASCII 외 문자 0건. 보고서 `:6`·`:92`는 설명 문장일 뿐 |
| G8-7 기존 테스트 무변경, test_auto_core* 통과 | PASS | `changed-files.txt`(기존 테스트에 M 없음), `checks.json:145-153`(324 OK), `:142`(새 실패 0. 전체 실패 수 28은 기준선과 같음) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_rules.py:398-404,568-576,629-647; manage-us-stock-strategy/scripts/auto_core_compare.py:121-132,232-233"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/cmp-fix2/changed-files.txt:1-4"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/cmp-fix2/diff.patch:1-591"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_rules.py:401-402,638-647; manage-us-stock-strategy/scripts/auto_core_compare.py:128-129"}, {"id": "G5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/cmp-fix2/diff.patch:1-591"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_compare_fix.py:360-586; workspace/outputs/dev-runs/cmp-fix2/checks.json:142-153"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/cmp-fix2/checks.json:90; docs/claude/cmp-fix2-report.md:92"}, {"id": "G8-1", "result": "PASS", "evidence": "workspace/outputs/dev-runs/cmp-fix2/changed-files.txt:1-4"}, {"id": "G8-2", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_rules.py:572,643-646; manage-us-stock-strategy/tests/test_auto_core_compare_fix.py:412-443"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_rules.py:383-404; manage-us-stock-strategy/tests/test_auto_core_compare_fix.py:445-460"}, {"id": "G8-4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_compare.py:127-132; manage-us-stock-strategy/tests/test_auto_core_compare_fix.py:499-522"}, {"id": "G8-5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_compare_fix.py:557-586; manage-us-stock-strategy/scripts/auto_core_tickets.py:382-384; manage-us-stock-strategy/scripts/auto_core_compare.py:38-49"}, {"id": "G8-6", "result": "PASS", "evidence": "docs/claude/cmp-fix2-report.md:6,92"}, {"id": "G8-7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/cmp-fix2/checks.json:142-153"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-13T02:18:36Z
- 병합 커밋: `9f554fcecc3aa92031aa94995d892050741a03a3` · 방식: rebase
- 사용자 승인(-ApproveAuthority): 2026-10-13T02:09:54Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/cmp-fix2/ 의 원본 기록입니다.)
