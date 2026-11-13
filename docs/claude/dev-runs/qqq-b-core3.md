# dev-run qqq-b-core3 — NEEDS_APPROVAL

- 시각(UTC): 2026-11-13T06:20:13Z → 2026-11-13T06:46:49Z
- 기준 커밋(base): `3a8cb948897e1e21082b577d1760c4da7f6a4b53` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_qqq_b.py, JUDGE_CLASS_OK_FALSE)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3630 · 실패 1 → 변경 후 Ran 3635 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `08e325f8054b5dea4fc63553ffdec9797450194e963fc4cc8220975f7996a386`
- Judge 파일 sha256: `480de6f0b852221946d8c8413f96bc1a8b74d2da71881bf0871407d18921897a`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 qqq-b-core3 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/qqq-b-core3-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_qqq_b.py`

## Judge 보고 원문 (1회차 PASS)

## Judge 판정 — qqq-b-core3

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core_tickets.py:62에서 INDEX_ETFS에 QQQ를 더했고, :63-64에 주석과 `PARKING_ETFS = ("QQQ",)`를 두었다. auto_core_decide.py:305는 QQQ의 ② NOCARD만 뺀다. auto_core_decide.py:314는 QQQ의 ⑩을 뺀다. 빈 껍데기·하드코딩·TODO는 없다. |
| G2 범위 | PASS | changed-files.txt:1-4가 allowed_paths 4개(task-prompt.md:13)와 같다. checks.json:139의 status는 OK이고 reasons는 []다. diff에는 지시된 줄만 있다(diff.patch:5-21, 27-37). |
| G3 주문·체결 추정 | PASS | diff.patch에 주문 경로 문자열(`/api/us/ordr`·`ust2000x`·`kiwoom_order`·`order_submit`)이 없다(grep 0건). 바뀐 것은 상수와 알림 조건 두 개뿐이다. |
| G4 정책·상태 쓰기·fail-closed | PASS | 정책·상태 파일에 쓰는 경로가 새로 생기지 않았다. 연구 기록이 없으면 QQQ ①은 여전히 막힘이다(auto_core_tickets.py:230-231, 테스트 :62-63). QQQ ②는 "상품 승인 없음" 막힘 그대로다(auto_core_tickets.py:264-265). |
| G5 비밀 | PASS | diff.patch에서 .env·토큰·계좌 식별자를 grep했더니 0건이다. |
| G6 테스트 | PASS | test_auto_core_qqq_b.py:30-85에 새 테스트 5개가 있다. 기존 테스트 파일은 수정하지 않았고, skip이나 expectedFailure도 더하지 않았다. checks.json:154의 new_failures는 []다. |
| G7 class | PASS (class_ok=false) | QQQ가 INDEX_ETFS에 들어가면 single_nominal에서 빠진다(auto_core_tickets.py:186-187). 그러면 매수 요건 ②의 '종목 상한' 사유가 QQQ를 세지 않는다(auto_core_tickets.py:254-256). 종목 상한의 적용 범위가 바뀌므로 사용자 승인 대상이다. 예정된 병합 경로(`-ApproveAuthority`)와 같다(task-prompt.md:9, :83). |
| G8-1 diff 한정·APPROVED_BUY 그대로 | PASS | diff.patch:30은 APPROVED_BUY 줄이 바뀌지 않은 문맥 줄이다. 바뀐 hunk는 tickets 62→62-64, decide 305·314뿐이다. |
| G8-2 테스트가 바뀐 동작을 잡음 | PASS | 아래 다섯 가지 되돌림을 코드로 따라가 확인했다. 직접 돌려 보지는 않았다. 근거는 표 아래에 적었다. |
| G8-3 바꾸지 말아야 할 곳 | PASS | buy_requirements·rule_file_nominal 본문, 재배치 후보, S7, 정책 파일, auto_core_rules.py는 diff에 없다. NOCARD 트리거는 auto_core_rules.py:636-639에 그대로 있다. |
| G8-4 권한 표지·주문·키움·정책 | PASS | diff에서 권한 표지 낱말을 grep했더니 0건이다. auto_core_tickets.py:68의 AUTHORITY 줄은 diff 밖이다. |
| G8-5 대상 테스트 통과 | PASS | checks.json:159-174: `test_auto_core*.py`는 604개를 돌려 실패 0이고, `test_qqq_registration.py`는 8개를 돌려 실패 0이다. 전체 실행의 실패 1건(test_test_only_scheduler_control_plane)은 이번 변경 전 기준선에도 있던 실패다(checks.json:4, :147). |
| G8-6 / G9 연결표 | 해당 없음 (PASS) | task-prompt.md에 `## 연결표` 절이 없다. diff는 새 출력 파일·알림 종류·화면 칸·예약을 만들지 않는다. QQQ ① 칸 값이 바뀌고 QQQ의 ②·⑩ 줄이 빠질 뿐이다. |

**G8-2 근거**
- INDEX_ETFS에서 QQQ를 빼면 테스트 1·2·3이 실패한다.
  - 테스트 1: test:32에서 목록 비교가 어긋난다.
  - 테스트 2: test:44에서 single_nominal에 QQQ가 들어간다.
  - 테스트 3: test:58에서 실패한다. earnings가 None이면 earnings_blackout이 막힘을 돌려준다(portfolio_exposure.py:1087).
- 314행 조건을 되돌리면 테스트 5가 test:78에서 실패한다.
- 305행 조건을 되돌리면 테스트 5가 test:79와 :85에서 실패한다.
- 305행 조건이 QQQ의 다른 ② 트리거까지 막으면 테스트 5가 test:80과 :82에서 실패한다.
- APPROVED_BUY에 QQQ를 넣으면 테스트 1(test:34-35)과 테스트 3(test:59-60)이 실패한다. 테스트 3에서는 막을 다른 사유가 남지 않는다: `r5_state({})`가 "unk"를 돌려주므로(auto_core_rules.py:727-728) "R5 검토"가 붙지 않는다.

```json
{"verdict": "PASS", "class_ok": false, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:62-64; manage-us-stock-strategy/scripts/auto_core_decide.py:305,314"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/qqq-b-core3/changed-files.txt:1-4; task-prompt.md:13; checks.json:139"}, {"id": "G3", "result": "PASS", "evidence": "workspace/outputs/dev-runs/qqq-b-core3/diff.patch (order-path grep 0 hits)"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:230-231,264-265; tests/test_auto_core_qqq_b.py:62-63"}, {"id": "G5", "result": "PASS", "evidence": "diff.patch (secret/account grep 0 hits)"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_qqq_b.py:30-85; checks.json:154"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:186-187,254-256 (QQQ removed from core single-stock cap check -> class_ok=false); task-prompt.md:9,83"}, {"id": "G8-1", "result": "PASS", "evidence": "diff.patch:30 (APPROVED_BUY context line unchanged), hunks tickets:62-64, decide:305,314"}, {"id": "G8-2", "result": "PASS", "evidence": "tests/test_auto_core_qqq_b.py:32,34-35,44,58-60,78-82,85; auto_core_rules.py:727-728; portfolio_exposure.py:1087"}, {"id": "G8-3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_rules.py:636-639 (unchanged); diff.patch hunks only"}, {"id": "G8-4", "result": "PASS", "evidence": "diff.patch (authority-marker grep 0 hits); auto_core_tickets.py:68 outside diff"}, {"id": "G8-5", "result": "PASS", "evidence": "checks.json:4,147,154,159-174"}, {"id": "G9", "result": "PASS", "evidence": "task-prompt.md (no 연결표 section; no new output) - 해당 없음"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-11-13T12:36:33Z
- 병합 커밋: `7936949cea226a4d5c429dc112bd909260f27a8f` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-11-13T12:36:31Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/qqq-b-core3/ 의 원본 기록입니다.)
