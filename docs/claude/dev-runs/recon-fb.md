# dev-run recon-fb — NEEDS_APPROVAL

- 시각(UTC): 2026-10-27T23:30:15Z → 2026-10-27T23:58:53Z
- 기준 커밋(base): `155bc1e37e9f2799790206a02979b92fe665ada8` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_reconcile.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py, JUDGE_CLASS_OK_FALSE)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3406 · 실패 31 → 변경 후 Ran 3416 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `42e388ed7c1c4777c1d59ef1ab22cea67573865d33d1b3246af4beea5170c98e`
- Judge 파일 sha256: `d2ccbd65d0ab3bc2611946e895475682fd05cf5a8c7aa0fca9fe20e0ae70aa80`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 recon-fb -ApproveAuthority`

## 바뀐 파일

- `docs/claude/recon-fb-report.md`
- `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md`
- `manage-us-stock-strategy/scripts/auto_core_reconcile.py`
- `manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py`

## Judge 보고 원문 (1회차 PASS)

## Judge 판정: recon-fb (B2-N 직전 거래일 행 대체)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `auto_core_reconcile.py:778-793`(새 함수 2개), `:825-830`(조건 4개가 모두 맞을 때만 `after = fallback`), `:1212-1229`(조건부 세 번째 읽기, fallback 키). 하드코딩·TODO 없음 |
| G2 범위 | PASS | `changed-files.txt:1-4`가 모두 `task-prompt.md:62` allowed_paths 안. `checks.json:49-50` reasons 없음, status OK. 기존 함수(`ledger_days`, `ledger_balance`, 한도, 상수)는 diff 밖 |
| G3 주문·체결 추정 | PASS | 새 호출은 `LEDGER_OPERATION`(account_deposit_by_date_read, `:99`) 읽기 1건뿐(`:1221-1223`). 주문 도구 호출 없음, 가격으로 체결을 추정하는 코드 없음 |
| G4 정책·상태 쓰기 / fail-closed | PASS | diff에 쓰기 경로 없음. fallback이 안 맞으면 `:832-835`에서 기존 사유로 보류. 세 번째 읽기 예외는 `:1227-1228` READ_FAILED로 보류. 테스트 `test_auto_core_reconcile_outflow.py:538-547` |
| G5 비밀·계좌 식별자 | PASS | 요청 파라미터는 `base_dt` 하나(`:1222`). 테스트 값은 합성 자료. 보고서에 식별자 없음 |
| G6 단언·skip / 새 동작 테스트 | PASS | 테스트 파일 diff는 끝부분 추가뿐(`diff.patch:132-243`), 기존 함수 무변경. 지시 a~j 각각 테스트 있음(`:484-591`). `checks.json:96` new_failures 없음, EXPECTED_FAILURES_INCREASED 없음. target 실패 1건(PLTR registry)은 기준선 31건 안의 실패 |
| G7 class | PASS (class_ok=false) | 대조 불변 조건 I3의 B2-N 증거 요건을 완화하므로 authority(K3). `checks.json:40` class authority, `task-prompt.md:5`와 일치. quantity_authority·주문 단계는 무변경 |
| G8-1 diff 범위, basis 키 | PASS | 바뀐 곳은 `outflow_ledger`·`unverified_outflow`와 그 둘만 부르는 작은 함수 2개(`:778-793`, 호출처 `:827`, `:1219`만), 참조 문서 `:317-333`, 테스트 새 클래스 2개. basis 키 `:846-852` 그대로이고, 키 집합이 같은지 테스트 `:507-525`가 확인 |
| G8-2 켜짐 조건 | PASS | 읽기 1건 통과 + USD 0행일 때만(`:784-787`, `:1218-1219`, `:827`). 실패·USD 2행·VALUE는 False. fallback은 `previous_session` 하나뿐(`:790-793`)이고 `> base_before`(`:1220`, `:826`) |
| G8-3 창·한도·0.05·원화·유출만 | PASS | 창 검사는 `:828`. 그 뒤 `:837-845`(0.05 일치, 한도, 원화 증가 금지)와 호출 조건 `:924-925`(R < −1.00)는 기존 줄 그대로. 테스트 `:528`, `:554`, `:559` |
| G8-4 base_after 행이 있는 경우 | PASS | 세 번째 읽기 없이 `{"days","results"}`만 돌려줌(`:1226`). 기존 테스트 무변경 통과. 연속 거래일은 기존 테스트 `:305-317`이 간접 확인(게이트를 빼면 그 테스트가 깨짐). 읽기 2번은 `:367`, `:578-591`에서 확인 |
| G8-5 반례 탐색 | PASS | R−L = fallback 뒤 순 현금 이동이라서, 그것이 0.05를 넘으면 NOT_MATCHED로 보류(`:838-839`, 테스트 `:554`). fallback 뒤 분류된 흐름(F)은 L에만 차이를 만들어 보류. 입금이 유출로 둔갑하는 새 길은 없음(R < −1 조건은 그대로이고, 통과 조건이 base_after 경로보다 엄격함) |
| G8-6 권한 줄·파일·줄바꿈·새 실패·보고 | PASS | diff에 권한 문자열 없음(hunk 머리 문맥 1줄뿐). 고친 3개 파일 모두 LF만 있는 줄 0개(테스트 파일 593줄 모두 CRLF). new_failures 없음. 보고서 `recon-fb-report.md:51-55`에 (a)~(d)와 "표지 없음" 있음 |

```json
{"verdict": "PASS", "class_ok": false, "items": [
{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:778-793,825-830,1212-1229"},
{"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/recon-fb/changed-files.txt:1-4; task-prompt.md:62; checks.json:49-50"},
{"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:99,1221-1223 (ust21132 read only)"},
{"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:826-835,1227-1228; tests/test_auto_core_reconcile_outflow.py:538-547"},
{"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_reconcile.py:1222 (base_dt only); synthetic test data"},
{"id": "G6", "result": "PASS", "evidence": "diff.patch:132-243 (additions only); tests/test_auto_core_reconcile_outflow.py:484-591; checks.json:96 new_failures []"},
{"id": "G7", "result": "PASS", "evidence": "class_ok=false: reconciliation invariant I3 B2-N evidence relaxed (task-prompt.md:5, checks.json:40); quantity_authority unchanged"},
{"id": "G8-1", "result": "PASS", "evidence": "auto_core_reconcile.py:778-793 (helpers used only at :827,:1219), :846-852 basis keys unchanged; tests :507-525"},
{"id": "G8-2", "result": "PASS", "evidence": "auto_core_reconcile.py:784-787,790-793,1218-1220,826-827"},
{"id": "G8-3", "result": "PASS", "evidence": "auto_core_reconcile.py:828,837-845,924-925; tests :528,554,559"},
{"id": "G8-4", "result": "PASS", "evidence": "auto_core_reconcile.py:1226; tests :305-317,367,578-591; checks.json:96"},
{"id": "G8-5", "result": "PASS", "evidence": "R-L = post-fallback net cash movement -> auto_core_reconcile.py:838-839; tests :554"},
{"id": "G8-6", "result": "PASS", "evidence": "diff.patch (no authority lines); CRLF kept in 3 files; checks.json:96; docs/claude/recon-fb-report.md:51-55"}
], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-28T00:34:17Z
- 병합 커밋: `d82dc15d85ca698598becbdf6273ff96b2597029` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-28T00:34:14Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/recon-fb/ 의 원본 기록입니다.)
