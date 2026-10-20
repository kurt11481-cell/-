# dev-run enter-window3 — NEEDS_APPROVAL

- 시각(UTC): 2026-10-20T11:55:06Z → 2026-10-20T12:29:00Z
- 기준 커밋(base): `dfa1b079a49420ab37e252347072eda2d169e11c` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_enter_window.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_preon_fix.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_risk1r.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_tickets.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3230 · 실패 30 → 변경 후 Ran 3247 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `ed43a7b974a98d5200bde0add0a8d871723f60f0677b5cac0762405e1ac942b0`
- Judge 파일 sha256: `2f584a5958978f4bbeed995c7366e435d0d18c09f58be572f108a1fad5516be9`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 enter-window3 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/enter-window3-report.md`
- `manage-us-stock-strategy/references/auto-core-decision.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_enter_window.py`
- `manage-us-stock-strategy/tests/test_auto_core_preon_fix.py`
- `manage-us-stock-strategy/tests/test_auto_core_risk1r.py`
- `manage-us-stock-strategy/tests/test_auto_core_tickets.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 입력 시작은 개장일 프리마켓 시작으로 바뀌었습니다. `_entry_start`가 max(발행일 07:45, core_open_at−5h30m)를 계산합니다(auto_core_tickets.py:833-835). 문구 두 형식은 auto_core_tickets.py:856-867, :700 안내는 auto_core_decide.py:699-702, carried 안내는 auto_core_decide.py:876-881에 있습니다. 하드코딩이나 남은 TODO는 없습니다. |
| G2 범위 | PASS | 바뀐 경로 8개가 모두 allowed_paths 안에 있습니다(changed-files.txt:1-8, checks.json:17-26). 부수 변경도 없습니다. |
| G3 주문·키움·체결 추정 | PASS | 새 코드는 문자열과 시각만 계산합니다(auto_core_tickets.py:833-867, auto_core_decide.py:848-881). 주문 경로, 키움 호출, 가격으로 체결을 추정하는 코드는 없습니다. |
| G4 정책·상태 쓰기, fail-closed | PASS | 새 쓰기 경로가 없습니다. 입력 시작을 못 구하면 `entry_start`가 None을 돌려주고(auto_core_tickets.py:841-847), 안내는 추측하지 않고 지금 문구 "저녁"을 씁니다(auto_core_decide.py:854-855, :878). |
| G5 비밀·계좌 | PASS | 비밀이나 계좌 식별자를 읽거나 출력하지 않습니다. 테스트 입력은 모두 합성 자료입니다(test_auto_core_enter_window.py:1-10). |
| G6 테스트 약화, 새 동작 테스트 | PASS | 기존 테스트는 기대 문구만 고쳤습니다(test_auto_core_tickets.py:772-788, test_auto_core_preon_fix.py:37-43·:92·:112·:130-135). skip이나 expectedFailure는 추가되지 않았습니다. 새 테스트 17개가 생겼고(test_auto_core_enter_window.py:487-641), new_failures는 0건입니다(checks.json:385). |
| G7 class | PASS | `AUTHORITY`는 그대로입니다(auto_core_tickets.py:66). 주문 단계, 예산, 상한, 승인 상품, 대조 불변 조건, 정지 스위치도 바뀌지 않았습니다. `PREMARKET_LEAD`는 표시용으로 `_entry_start`에서만 씁니다(auto_core_tickets.py:73, :835). |
| G8-1 범위·의미 | PASS | 바뀐 의미는 표시 문구 셋(enterWindow 시작, :700 안내, carried 안내)과 문서 한 항목뿐입니다(auto-core-decision.md:161-169). 다른 티켓 필드가 바뀌지 않았다는 것은 enterWindow를 뺀 비교로 확인됩니다(test_auto_core_enter_window.py:640). |
| G8-2 시작 시각 정의 | PASS | 입력 시작은 core_open_at−5h30m입니다(auto_core_tickets.py:835). 토요일 발행분은 월요일 날짜, 겨울은 18:00으로 나옵니다(test_auto_core_enter_window.py:492-507). 끝 "개장 전"은 그대로입니다(auto_core_tickets.py:866-867). 상수는 관문이나 설정에 들어가지 않습니다(test_auto_core_enter_window.py:529-534). |
| G8-3 안내 문구 | PASS | apply 모드 안내에 날짜와 시각이 들어갑니다(test_auto_core_enter_window.py:552-557). compare 모드에서는 None입니다(:559-562). 입력 시작을 못 구하면 "저녁" 문구를 씁니다(:564-568, :595-608). |
| G8-4 GOLDEN·T5·테스트 | PASS | GOLDEN은 지정한 5키만 바뀌었고, 값은 2회차 실측 접두어와 같습니다(test_auto_core_risk1r.py:39-55). 나머지 3키는 그대로입니다(:41, :44-45). GoldenCauseTests가 통과해 원인이 enterWindow 문구 하나임이 확인됩니다(test_auto_core_enter_window.py:629-641). 전체 테스트는 Ran 3247, 실패·오류 30건으로 기준선 30건과 같고 새 실패는 0건입니다(checks.json:4, :343-346, :385). |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:833-867; manage-us-stock-strategy/scripts/auto_core_decide.py:699-702,848-881"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/enter-window3/changed-files.txt:1-8; checks.json:17-26"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:833-867"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:841-847; manage-us-stock-strategy/scripts/auto_core_decide.py:854-855,878"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_enter_window.py:1-10"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_enter_window.py:487-641; checks.json:385"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:66,73,835"}, {"id": "G8-1", "result": "PASS", "evidence": "manage-us-stock-strategy/references/auto-core-decision.md:161-169; manage-us-stock-strategy/tests/test_auto_core_enter_window.py:640"}, {"id": "G8-2", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:835,866-867; manage-us-stock-strategy/tests/test_auto_core_enter_window.py:492-507,529-534"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_enter_window.py:552-568,595-608"}, {"id": "G8-4", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_risk1r.py:39-55; manage-us-stock-strategy/tests/test_auto_core_enter_window.py:629-641; checks.json:385"}], "min_fixes": []}
```
VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-20T12:59:24Z
- 병합 커밋: `3e753f3b6cee0e0ed1a1720809ef7c759c779f39` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-20T12:59:22Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/enter-window3/ 의 원본 기록입니다.)
