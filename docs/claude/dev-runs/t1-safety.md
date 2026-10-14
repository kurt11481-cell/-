# dev-run t1-safety — NEEDS_APPROVAL

- 시각(UTC): 2026-10-13T12:05:10Z → 2026-10-13T12:53:20Z
- 기준 커밋(base): `3edc19f91719c6079f17183656db957a115ea891` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ADDED_LINE:kill_switch, AUTHORITY_PATH:manage-us-stock-strategy/schemas/auto-core-decision.schema.json, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_rules.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_t1_safety.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3003 · 실패 28 → 변경 후 Ran 3022 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `259e2fc77bc7d82dcdefba5d4be933ec2aa216212d671c61bf02daf36d056e78`
- Judge 파일 sha256: `e4f5029c79fe09a6d0b39e6dd51bdb09dec165276cc631f3abd2d46333e55c45`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 t1-safety -ApproveAuthority`

## 바뀐 파일

- `docs/claude/t1-safety-report.md`
- `manage-us-stock-strategy/schemas/auto-core-decision.schema.json`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_rules.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_t1_safety.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 수정 1: `manage-us-stock-strategy/scripts/auto_core_decide.py:217-281`(대상 세션 계획·판정), `:727-762`(_run 연결·push 알림), `:1035-1038`(`ev4_all`에 합류). 수정 2: `manage-us-stock-strategy/scripts/auto_core_tickets.py:545-560`. 빈 껍데기·하드코딩·남은 TODO 없음 |
| G2 범위 | PASS | `changed-files.txt:1-6` 6개 경로 모두 allowed_paths 안. `snapshot_holdings` 추출(`auto_core_decide.py:166-173`, `:622`)은 동작이 같은 정리이고, F1과 같은 코드를 부르기 위해 필요(복제 금지 요구) |
| G3 주문 경로·체결 추정 | PASS | 주문·키움 주문 호출 없음. 권한 표지 문자열은 보고 문서에만 나옴(`diff.patch:300,318`). `_rebuilt_total`은 브로커 스냅샷의 보유 수량 × 종가로 평가액만 구함(`auto_core_decide.py:195-214`). 체결 추정 아님 |
| G4 정책·상태 쓰기 / fail-closed | PASS | 새 쓰기 경로 없음. 읽기는 `<run day>/kiwoom_broker_snapshot.shadow.json`뿐(`auto_core_decide.py:200-204`). 못 구하면 3% 이웃 규칙 + push(`:274-279`, `:758-762`), 이웃이 없으면 열림(`:278-279`) |
| G5 비밀·계좌 식별자 | PASS | 스냅샷에서 holdings·cash만 읽고, 기록에는 total만 남김(`auto_core_decide.py:205-214`, `:271-272`) |
| G6 테스트 | PASS | 새 파일 `test_auto_core_t1_safety.py`(테스트 19개: S1~S6, F1~F3 + 보강). 기존 테스트 파일 수정·skip·expectedFailure 없음. `checks.json:363` new_failures [], `:367-374` 대상 379 OK |
| G7 class | PASS | `ADDED_LINE:kill_switch`는 보고 문서의 "만들지 않았다" 문장에서 나온 오탐(`diff.patch:318`). quantity_authority 추가 없음. 새 상수 `RREC_EV4_NEIGHBOR_MARGIN`(`auto_core_rules.py:59-61`)은 자료가 없을 때 쓰는 여유값으로, 지시문이 허용함(`task-prompt.md:57`). 기존 관문 값·예산·상한·대조 불변 조건은 바뀌지 않음 |
| G8-1 범위·S6 골든 | PASS | `test_auto_core_t1_safety.py:212`(S6, 결정 기록 전체 비교), `:136`(S2 골든). 리플레이는 인자를 넘기지 않아 동작 불변(`auto_core_replay.py:250-257`) |
| G8-2 수정 1 | PASS | F1과 같은 함수를 부름(`snapshot_holdings`→`equity_cash`→`rule_file_nominal`→`rules.ev4_open`, `auto_core_decide.py:205-211,271`). 대상 범위: 첫 기록 이후 ~ 평가 세션 앞, 창 안(`:243-244`). 3% 이웃 규칙(`:274-279`), push(`:758-762`). 남은 fail-open 경로는 아래 6개 |
| G8-3 수정 2 | PASS | 같은 행은 1번만, 다른 행이면 `ORD_NO_DUPLICATE_CONFLICT`로 unknown(`auto_core_tickets.py:556-560`). T1 규칙(`auto_core_reconcile.py:291-294`)과 같고, 원래 행 전체를 비교하므로 더 엄격함. note가 붙으면 결과 unknown·주문표 open 유지(`auto_core_decide.py:342-346`) |
| G8-4 권한·테스트 | PASS | 권한 표지·주문 경로·정책/상태 쓰기·키움 호출 없음. 대상 테스트 새 실패 0, 전체 28건(기준선 28과 같음) 중 새 실패 0(`checks.json:322-363`) |

**남은 fail-open 경로 (G8-2):**
1. **총자산을 모른 채 끝난 F1 기록:** F1까지 갔어도 총자산이 None이면 `ev4_open=false`(bool)로 기록되고 "기록됨"으로 처리됩니다. 그래서 다음 날부터 다시 구하는 대상이 아닙니다(`auto_core_decide.py:234`, `auto_core_rules.py:715-716`). 지시문 정의를 그대로 따른 결과입니다. 후속 과제 후보입니다.
2. **NEIGHBOR_CLEAR는 추정:** 앞뒤 이웃 사이에 하루만 3% 넘게 급락한 경우는 놓칩니다. push로 보이기만 합니다.
3. **스냅샷 날짜·시각 미검증:** run-day 폴더의 스냅샷을 그 세션 장 마감 뒤 상태로 가정합니다.
4. **복구 결과가 저장되지 않음:** 매 실행마다 다시 계산하므로 NEAR↔CLEAR 판정이 날마다 바뀔 수 있습니다.
5. **매일 반복되는 push:** EV4_UNDETERMINED는 억제 없이 나갑니다. 빈 세션이 60세션 창 안에 있는 동안 매일 알림이 갑니다.
6. **NEIGHBOR_NONE 추가:** 지시문에 없는 네 번째 값이지만 더 보수적인 방향입니다. 오늘 총자산이 없을 때만 생기고, 그날은 매수 요건 (2)가 이미 매수를 막습니다.

**실데이터 확인:** 실데이터 확인은 하지 못했습니다(worktree에 auto-core 출력이 없음). 병합 후 Cowork가 첫 decide 기록의 `ev4_backfill`과 `EV4_UNDETERMINED`를 확인해야 합니다.

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:217-281,727-762,1035-1038; manage-us-stock-strategy/scripts/auto_core_tickets.py:545-560"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/t1-safety/changed-files.txt:1-6 all in allowed_paths; snapshot_holdings extraction auto_core_decide.py:166-173,622 behavior-equivalent"}, {"id": "G3", "result": "PASS", "evidence": "no order path or Kiwoom order call; authority strings only in report doc diff.patch:300,318; auto_core_decide.py:195-214 valuation from broker snapshot only"}, {"id": "G4", "result": "PASS", "evidence": "no new write path; read-only snapshot auto_core_decide.py:200-204; missing data -> neighbor rule + push :274-279,758-762; no neighbor -> open :278-279"}, {"id": "G5", "result": "PASS", "evidence": "auto_core_decide.py:205-214,271-272 reads holdings/cash only, records total only"}, {"id": "G6", "result": "PASS", "evidence": "new test_auto_core_t1_safety.py (19 tests S1-S6, F1-F3); no existing test edits, skips or expectedFailure; checks.json:363 new_failures [], :367-374 targets 379 OK"}, {"id": "G7", "result": "PASS", "evidence": "ADDED_LINE:kill_switch is report text (diff.patch:318), false positive; no quantity_authority; RREC_EV4_NEIGHBOR_MARGIN auto_core_rules.py:59-61 is a missing-data margin allowed by task-prompt.md:57; no budget/cap/stage/invariant/kill-switch change"}, {"id": "G8-1", "result": "PASS", "evidence": "test_auto_core_t1_safety.py:212 (S6 golden), :136 (S2 golden); replay unchanged auto_core_replay.py:250-257"}, {"id": "G8-2", "result": "PASS", "evidence": "same F1 functions auto_core_decide.py:205-211,271; target range :243-244; 3% neighbor :274-279; push :758-762. Remaining fail-open: F1 record with total None stores ev4_open=false and counts as covered (:234, auto_core_rules.py:715-716); NEIGHBOR_CLEAR is an estimate; snapshot date not validated; backfill not persisted (NEAR/CLEAR may flip); EV4_UNDETERMINED pushes daily while a gap stays in the window; real-data check not done (no auto-core outputs in worktree) -> Cowork checks the first post-merge record"}, {"id": "G8-3", "result": "PASS", "evidence": "auto_core_tickets.py:556-560 vs auto_core_reconcile.py:291-294; note -> unknown/open auto_core_decide.py:342-346"}, {"id": "G8-4", "result": "PASS", "evidence": "no authority markers/order path/policy-state writes/Kiwoom calls; checks.json:322-363 full 28 failures = baseline 28, new_failures []"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-13T23:33:19Z
- 병합 커밋: `40513919f4f5c4d40947501b9bad3e85a66ff3c3` · 방식: rebase
- 사용자 승인(-ApproveAuthority): 2026-10-13T23:19:00Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/t1-safety/ 의 원본 기록입니다.)
