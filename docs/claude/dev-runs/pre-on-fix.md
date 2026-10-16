# dev-run pre-on-fix — NEEDS_APPROVAL

- 시각(UTC): 2026-10-15T07:35:12Z → 2026-10-15T08:13:52Z
- 기준 커밋(base): `ec6817694bc8d8f83e919e688ad22ea2b695ea1f` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_preon_fix.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_t1_safety.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_tickets.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3087 · 실패 28 → 변경 후 Ran 3105 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `d749e2c1de99dc87c56375e1a9301ad8e591bc7e140e87708ed9956dff3e22d3`
- Judge 파일 sha256: `f47935830d54d6a3f54fce0953e05d237ce6f920a10883cd9be552a81bda5ac8`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 pre-on-fix -ApproveAuthority`

## 바뀐 파일

- `docs/claude/pre-on-fix-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_decide.py`
- `manage-us-stock-strategy/tests/test_auto_core_preon_fix.py`
- `manage-us-stock-strategy/tests/test_auto_core_t1_safety.py`
- `manage-us-stock-strategy/tests/test_auto_core_tickets.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 세 가지 수정이 모두 실제로 구현되어 있다. ④ `auto_core_decide.py:946`, `:951-967`(발행일 M/D를 모두 표시하고 "이미 입력했으면 다시 넣지 않음" 문구를 넣음. 발행일을 읽지 못하면 `?`로 표시). ① `auto_core_tickets.py:525-536`(`session_close`), `:559-562`, `:593-598`, 호출부 `auto_core_decide.py:333-343`. ⑥ `auto_core_decide.py:709-713` → `:463-464`(push True). 하드코딩이나 TODO는 없다 |
| G2 범위 | PASS | `changed-files.txt:1-7`의 7개 경로가 모두 allowed_paths 안에 있다. `checks.json:17-25`, `:326`(reasons []). `ticket_rows`를 호출하는 곳은 `auto_core_decide.py:342` 하나뿐이다(grep으로 확인). 그래서 필수 인자가 새로 생겨도 다른 호출부가 깨지지 않는다 |
| G3 주문·체결 추정 | PASS | diff에 주문 경로나 키움 주문 도구 호출이 없다. 결과 분류는 증권사 주문 행(ord_time 포함)만 쓰고 가격 변화로 체결을 추정하지 않는다(`auto_core_tickets.py:571-600`) |
| G4 정책·상태 쓰기 / fail-closed | PASS | 새로 생긴 쓰기 경로가 없다. 마감 시각을 모르면 `ORDER_WINDOW_UNKNOWN`(`auto_core_tickets.py:559-560`, `auto_core_decide.py:334-337`)으로 처리하고, 끝 날짜 주문 시각을 못 읽으면 `ORD_TIME_UNREADABLE`(`auto_core_tickets.py:594-596`)로 처리한다. 둘 다 결과를 unknown으로 두고 주문표를 열린 채로 둔다. 새 세션 없는 날 쓰는 파일 목록이 그대로인 것도 테스트로 확인된다(`test_auto_core_preon_fix.py:95-96`) |
| G5 비밀 | PASS | diff에 .env, 토큰, 계좌번호를 읽거나 출력하는 코드가 없다 |
| G6 테스트 | PASS | skip이나 expectedFailure가 없다(diff grep 0건). `new_failures` []이고 기준선·변경 후 모두 실패 28건이다(`checks.json:4`, `:331-332`, `:370`). 대상 테스트는 Ran 423, OK다(`:377-381`). 새 동작마다 테스트가 있다(`test_auto_core_preon_fix.py` 18개). 기존 테스트는 fixture 시각과 기대값만 고쳤다(`test_auto_core_decide.py:1049`, `:1074`, `:1090`, `test_auto_core_t1_safety.py:320`, `test_auto_core_tickets.py:317`). compare 모드에서 귀속 목록을 남기지 않는다는 단언은 d2 시점에 여전히 실제로 검사된다(`test_auto_core_decide.py:1078`, `:1095`) |
| G7 class | PASS | 주문 단계, 예산, 상한, 대조 불변 조건, kill switch는 바뀌지 않았다. quantity_authority 추가도 없다(diff에는 보고서 문구 `:304`에만 나옴). authority 등급은 경로 때문에 붙은 것이다(`checks.json:315-322`) |
| G8-1 범위·불변 | PASS | 의미가 바뀐 것은 세 가지뿐이다. 관문, 수량, 가격, 후보 계산 코드는 diff에 없다. 스키마 감사는 PASS다(`checks.json:371`) |
| G8-2 ④ | PASS | 새 문구는 apply 모드이고 넘어온 주문 행이 있을 때만 나온다(`auto_core_decide.py:946`). compare 모드는 None이다(`test_auto_core_preon_fix.py:112-118`). 새 세션 날 문구는 그대로다(`auto_core_decide.py:804-805`, 테스트 `:120-127`). dashboard.orders는 바뀌지 않는다(`:91-92`) |
| G8-3 ① | PASS | 끝 날짜에는 `placed > end_clock`인 행을 제외한다(`auto_core_tickets.py:597-598`, 마감 시각 이하만 남음). 발행일 하한(`:585-592`)은 그대로다. 새 상태 이름은 없다. 조기 마감, 겨울 마감, 같은 날 두 경계 적용을 테스트로 확인했다(`test_auto_core_preon_fix.py:174-212`) |
| G8-4 ⑥ | PASS | exceptions에 한 줄이 추가되고 push True로 나간다(`auto_core_decide.py:709-713`, `:463-464`). gate0(`:700`)와 HOLD 처리(`:778-780`)는 그대로다. 테스트 `test_auto_core_preon_fix.py:274-286` |
| G8-5 골든·T5·새 실패 | PASS | risk1r와 compare_fix 파일은 바뀌지 않았다(`changed-files.txt`). 대상·전체 테스트 모두 새 실패가 0이다(`checks.json:370`, `:373-382`) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:946,951-967,709-713; manage-us-stock-strategy/scripts/auto_core_tickets.py:525-536,559-562,593-598"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/pre-on-fix/changed-files.txt:1-7; checks.json:17-25,326"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:571-600"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:559-560,594-596; manage-us-stock-strategy/scripts/auto_core_decide.py:334-337"}, {"id": "G5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/pre-on-fix/diff.patch:1-690"}, {"id": "G6", "result": "PASS", "evidence": "checks.json:4,331-332,370,377-381; manage-us-stock-strategy/tests/test_auto_core_preon_fix.py:84-286; manage-us-stock-strategy/tests/test_auto_core_decide.py:1078,1095"}, {"id": "G7", "result": "PASS", "evidence": "checks.json:315-322; diff.patch:304"}, {"id": "G8", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_decide.py:463-464,700,778-780,804-805,946; manage-us-stock-strategy/scripts/auto_core_tickets.py:585-598; checks.json:370-382"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-16T01:06:38Z
- 병합 커밋: `04f9a853e4ca6b40e6feb31f758918aa26159979` · 방식: rebase
- 사용자 승인(-ApproveAuthority): 2026-10-16T00:50:56Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/pre-on-fix/ 의 원본 기록입니다.)
