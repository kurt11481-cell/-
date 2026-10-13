# dev-run ust21100-fix — NEEDS_APPROVAL

- 시각(UTC): 2026-10-13T01:45:08Z → 2026-10-13T02:03:09Z
- 기준 커밋(base): `fcc294b57f5994051b990e066e5e89a064a69369` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ADDED_LINE:kill_switch, AUTHORITY_PATH:manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 2952 · 실패 28 → 변경 후 Ran 2956 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `37d71614a1df0ce1cf77ddc48cbaed868f787827d8c14e28cddbb650feaa739a`
- Judge 파일 sha256: `c8968210a8736c71cb597787c41967334db29d98af0aec8ed3c4d5c858227ee5`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 ust21100-fix -ApproveAuthority`

## 바뀐 파일

- `docs/claude/ust21100-fix-report.md`
- `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py`
- `manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 실제 코드에서 `krw_repl_skip_yn`이 "N"으로 바뀌었고, 지시한 대로 ASCII 주석 2줄(2026-10-13 실측, 1511, "N" = 비제외 = kiwoomcli 기본)이 들어갔다. 껍데기·TODO·하드코딩 없음 (manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py:41-44) |
| G2 범위 | PASS | 바뀐 경로 3개(M 1, A 2)가 모두 allowed_paths 안에 있다. 브리지 diff는 한 덩어리뿐이다 (changed-files.txt:1-3, task-prompt.md:12, diff.patch:5-16) |
| G3 주문 경로·체결 추정 | PASS | 추가된 줄에 주문 경로 문자열이나 주문 도구 호출이 없다. 가격으로 체결을 추정하는 코드도 없다. ACCOUNT_APIS는 `/api/us/acnt`만 쓴다 (kiwoom_account_readonly_bridge.py:21-32, diff.patch:9-13) |
| G4 정책·상태 쓰기, fail-closed | PASS | 새로 생긴 쓰기 경로가 없다. no-data 판정·검증·페이지 처리는 바뀌지 않았다 (kiwoom_account_readonly_bridge.py:113-137, 191-231). checks.json의 ignored에 상태 파일이 보이는데, git이 무시하는 런타임 산출물이고 diff에는 들어 있지 않다 (checks.json:96-97) |
| G5 비밀·계좌 식별자 | PASS | .env, 토큰, 계좌 필드를 읽거나 출력하지 않는다. 새 테스트도 키움을 호출하지 않는다 (test_kiwoom_account_bodies.py:1-61) |
| G6 테스트 | PASS | "N" 단언과 템플릿 전체 비교가 있어서 ""로 되돌리면 실패한다. skip이나 expectedFailure는 추가되지 않았다. 새 실패 없음 (test_kiwoom_account_bodies.py:33-37, checks.json:159) |
| G7 class | PASS | 주문 단계·예산·상한·불변 조건·정지 스위치는 바뀌지 않았다. quantity_authority 줄도 그대로다. class_reasons에 `ADDED_LINE:kill_switch`가 있지만, 보고서에 "건드리지 않았다"고 적은 문장이 걸린 것이다. 이번 class=authority는 경로 때문이다 (docs/claude/ust21100-fix-report.md:48, checks.json:108-111) |
| G8-1 diff 범위 | PASS | 코드 diff는 krw_repl_skip_yn "" → "N"과 주석 2줄뿐이다. "추가 실측" 절은 비어 있다 (diff.patch:9-13, task-prompt.md:61-63) |
| G8-2 빈 값 회귀 검출 | PASS | ""로 되돌리면 `assertEqual(body["krw_repl_skip_yn"], "N")`에서 실패한다 (test_kiwoom_account_bodies.py:36-37) |
| G8-3 다른 본문·경로·검증 불변 | PASS | 나머지 8개 본문을 골든 dict로 고정했고, 그 값이 변경 전 값과 같다. ACCOUNT_APIS 키 집합도 비교한다. 경로·검증·no-data 줄은 diff에 없다 (test_kiwoom_account_bodies.py:19-29, 51-57, diff.patch:5-16) |
| G8-4 권한 표지·주문·키움·정책 | PASS | 권한 표지 줄(357-358, 370, 386)은 diff에 없다. 키움을 호출하는 테스트가 없고, 정책·상태 파일 변경도 없다 (kiwoom_account_readonly_bridge.py:357-358, changed-files.txt:1-3) |
| G8-5 대상 테스트·기존 테스트 | PASS | 대상 6개 패턴이 모두 OK다(4/50/3/24/56/312). 기존 테스트 파일은 바뀌지 않았다. 전체 실행의 28개 실패는 기준선에 이미 있던 것이고, 새 실패는 0개다 (checks.json:4, 159, 162-211) |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py:41-44"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/ust21100-fix/changed-files.txt:1-3"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py:21-32"}, {"id": "G4", "result": "PASS", "evidence": "workspace/outputs/dev-runs/ust21100-fix/diff.patch:5-16"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py:1-61"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py:33-37"}, {"id": "G7", "result": "PASS", "evidence": "docs/claude/ust21100-fix-report.md:48"}, {"id": "G8-1", "result": "PASS", "evidence": "workspace/outputs/dev-runs/ust21100-fix/diff.patch:9-13"}, {"id": "G8-2", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py:36-37"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py:19-29"}, {"id": "G8-4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py:357-358"}, {"id": "G8-5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/ust21100-fix/checks.json:159"}], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/ust21100-fix/ 의 원본 기록입니다.)
