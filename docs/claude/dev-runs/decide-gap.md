# dev-run decide-gap — NEEDS_APPROVAL

- 시각(UTC): 2026-10-21T10:35:10Z → 2026-10-21T10:58:33Z
- 기준 커밋(base): `ab059b07033f55211347c01dff8814087e662d4e` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3278 · 실패 31 → 변경 후 Ran 3283 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `7fd1e55bc178e367d38a287f2a5c7d8d6bdfafbc794698b4be88ea26b77acc10`
- Judge 파일 sha256: `8b1a5b3bcb0d11e61312ba55f7a98f1fe309616075e5badafe824b03106155a2`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 decide-gap -ApproveAuthority`

## 바뀐 파일

- `docs/claude/decide-gap-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core_decide.py:485-494 (대기 중 `KeyboardInterrupt`면 대기만 끝내고 `interrupted: true` 표지), :452-454 (`decide()` 바깥 `except KeyboardInterrupt`에서 FAIL과 `INTERRUPTED:KeyboardInterrupt` 기록 후 `_finish`). 빈 껍데기·하드코딩·TODO 없음 |
| G2 범위 | PASS | changed-files.txt:1-3, checks.json:17-21. 세 경로 모두 allowed_paths 안. 기존 테스트 파일 무변경. auto_core_decide.py의 CRLF 유지(1287줄 모두 `\r` 끝) |
| G3 주문·체결 추정 | PASS | diff.patch:5-41. 주문 경로·키움 호출·가격으로 체결을 추정하는 코드 없음 |
| G4 정책·상태 쓰기 / fail-closed | PASS | `_finish`(auto_core_decide.py:1274-1287)는 바뀌지 않음(decision·LATEST·compare만 씀). 중단되면 연구 기록 없음으로 처리돼 :574 `research_block`이 매수를 막음. 스키마 :27 `"inputs": {"type": "object"}`라 키 추가가 가능하고 스키마 변경 없음 |
| G5 비밀 | PASS | diff.patch 전체. .env·토큰·계좌 식별자를 읽거나 출력하지 않음 |
| G6 단언·테스트 | PASS | test_auto_core_decide_interrupt.py:61-144에 새 동작마다 테스트 있음. 단언 약화·skip·expectedFailure 없음. checks.json:155 `new_failures: []` |
| G7 class | PASS | diff.patch:5-41. 주문 단계·예산·상한·승인 상품·대조 불변 조건·kill_switch·quantity_authority 줄 변경 없음. RESEARCH_WAIT_UNTIL·RESEARCH_POLL_SECONDS 그대로 |
| G8-1 diff 최소 | PASS | auto_core_decide.py:452-454, :476-494만 바뀜. 게이트·티켓 규칙과 대기 시각·간격 그대로 |
| G8-2 매도 무차단 | PASS | test_auto_core_decide_interrupt.py:76-88. 매수 0, 매도 1, 매도 차단 사유에 RESEARCH_RECORD_NOT_OK 없음, 08:30까지 기다린 실행과 결과 같음. :99는 매수가 연구 기록 없음으로 막힘을 확인 |
| G8-3 대기 밖 중단 | PASS | test_auto_core_decide_interrupt.py:131-144. 예외가 밖으로 새지 않고 FAIL 기록, decision.json·LATEST 갱신, 저널 바이트 불변 |
| G8-4 저널·스키마·권한 | PASS | `decision_identity_hash`(auto_core_decide.py:777-779)가 `wait`를 해시에서 빼므로 저널 review_id 영향 없음. R2-5 판정(:730-738) 그대로. 스키마 무변경 |
| G8-5 보고·테스트 | PASS | decide-gap-report.md(diff.patch:98-100)에 (a) 파이썬이 ^C를 받았는지 확인 필요, (b) 잡을 수 없는 종료, (c) 더 강한 대안을 하지 않은 이유가 있음. 대상 테스트 실패 1건(PLTR 등록부 실제 자료 검사, checks.json:161)은 기준선에 있던 실패이고 새 실패는 0(checks.json:155) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:452-454,485-494"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/decide-gap/changed-files.txt:1-3"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/decide-gap/diff.patch:5-41"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:574,1274-1287; manage-us-stock-strategy/schemas/auto-core-decision.schema.json:27"}, {"id": "G5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/decide-gap/diff.patch:1-260"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py:61-144; workspace/outputs/dev-runs/decide-gap/checks.json:155"}, {"id": "G7", "result": "PASS", "evidence": "workspace/outputs/dev-runs/decide-gap/diff.patch:5-41"}, {"id": "G8-1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:452-454,476-494"}, {"id": "G8-2", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py:76-88,99"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_decide_interrupt.py:131-144"}, {"id": "G8-4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:730-738,777-779"}, {"id": "G8-5", "result": "PASS", "evidence": "docs/claude/decide-gap-report.md (diff.patch:98-100); workspace/outputs/dev-runs/decide-gap/checks.json:155,161"}], "min_fixes": []}
```
VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/decide-gap/ 의 원본 기록입니다.)
