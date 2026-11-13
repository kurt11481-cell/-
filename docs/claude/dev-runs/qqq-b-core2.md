# dev-run qqq-b-core2 — NEEDS_APPROVAL

- 시각(UTC): 2026-11-13T05:30:11Z → 2026-11-13T05:53:39Z
- 기준 커밋(base): `e629c22e5177a88309baaa35077f89af196514c4` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: ADDED_LINE:kill_switch, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_qqq_b.py, JUDGE_CLASS_OK_FALSE)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 3501 · 실패 168 → 변경 후 Ran 3506 · 새 실패 0 · skipped 2->2 · 스키마 감사 PASS->PASS
- diff_hash: `4192521a31e6a3e1b1876bf3a32c9c574a3ce7990b5c8d5442ef1e17fcad7812`
- Judge 파일 sha256: `b822b356dd009206a471b4394d14a85a63a9a9db31f91e9319edf4fe3353a423`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 qqq-b-core2 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/qqq-b-core2-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_qqq_b.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | auto_core_tickets.py:62에서 `INDEX_ETFS`에 QQQ를 더했다. :63-64에 주석(ASCII)과 `PARKING_ETFS = ("QQQ",)`를 새로 두었다. auto_core_decide.py:314에서 ⑩ 조건이 PARKING_ETFS를 뺀다. 빈 껍데기, 하드코딩, 남은 TODO는 없다. 다만 ② NOCARD 줄은 QQQ에도 남는다(auto_core_rules.py:636-639 → auto_core_decide.py:305-307). 지시문(task-prompt.md:39)이 이 부분을 범위 밖으로 정했고, 보고 6절에 남은 위험으로 적혀 있다. |
| G2 범위 | PASS | changed-files.txt:1-4의 4개 경로가 모두 task-prompt.md:13 allowed_paths 안에 있다. diff.patch:5-25에는 지시문의 1·2·4번만 들어 있다. |
| G3 주문 경로·체결 추정 | PASS | diff.patch 전체에 `/api/us/ordr`·`ust2000x`·`kiwoom_order`·`order_submit`이 없다. 가격 변화로 체결을 추정하는 코드도 없다. |
| G4 정책·상태 쓰기·fail-closed | PASS | 새 쓰기 경로가 없다. 연구 기록이 없으면 QQQ ①은 그대로 막힌다(auto_core_tickets.py:230-231, 테스트 4). ②는 "상품 승인 없음"으로 막힌 채다(:264-265). |
| G5 비밀 | PASS | test_auto_core_qqq_b.py 전체에서 .env·토큰·계좌를 읽지 않는다. 함수를 직접 부르는 단위 테스트만 있다. |
| G6 단언·skip·새 테스트 | PASS | 기존 테스트 파일은 바뀌지 않았다(changed-files.txt). skip 수는 기준선 2와 실행 2로 같다(checks.json:7, :156). new_failures는 빈 배열이다(checks.json:160). 새 동작 3개(INDEX_ETFS, PARKING_ETFS, ⑩ 조건)마다 테스트가 있다(test_auto_core_qqq_b.py:164-203). |
| G7 class | PASS (class_ok=false) | INDEX_ETFS에 QQQ를 넣으면 QQQ가 코어의 single_nominal에서 빠진다(auto_core_tickets.py:186-187). 그래서 ② "종목 상한" 검사(:254-256)가 QQQ를 세지 않게 되어, 코어의 종목 상한 적용 범위가 바뀐다. 영향은 작다: S7 cap_breaches는 계속 QQQ를 잡고(alert_policy.json:769에 면제 없음), QQQ ②는 :264 때문에 어차피 막힌다. 승인 정책 alert_policy.json:747 allowed_index_etfs에는 QQQ가 이미 있다. checks.json:131의 ADDED_LINE:kill_switch는 보고 머리말 문장(diff.patch:41)에서 나온 것이고 정지 스위치 변경이 아니다. APPROVED_BUY는 바이트 그대로다(diff.patch:21은 문맥 줄). |
| G8-1 diff 구성 | PASS | diff.patch:5-25(코드 3곳)와 :29-120(보고), :121-207(새 테스트)뿐이다. APPROVED_BUY는 바뀌지 않았다. |
| G8-2 테스트가 변이를 잡음 | PASS | INDEX_ETFS에서 QQQ를 빼면 세 테스트가 실패한다. 테스트 1은 test:164에서 실패한다. 테스트 2는 QQQ가 single_nominal에 들어가 test:177에서 실패한다. 테스트 3은 기록이 없어 earnings_blackout이 막힘을 돌려주므로(portfolio_exposure.py:1087) test:183에서 실패한다. nocard 조건을 되돌리면 `10:QQQ`가 생겨 테스트 5가 test:200에서 실패한다. APPROVED_BUY에 QQQ를 넣으면 테스트 1이 test:166-168에서 실패한다. 테스트 3도 실패한다: 다른 막힘 사유가 없기 때문이다(n 1.0, e 1.0, 현금 1000 ≥ 10, r5_state({})는 "unk", auto_core_rules.py:727-728). 그래서 ②가 ok가 되어 test:184에서 실패한다. |
| G8-3 그대로 둘 것 | PASS | buy_requirements·rule_file_nominal 식, 재배치 후보, S7, 정책 파일 모두 diff에 없다. NOCARD 트리거(auto_core_rules.py:636-639)도 바뀌지 않았다. |
| G8-4 권한·주문·키움·정책 | PASS | 코드 diff(diff.patch:5-25)에 order_authority·quantity_authority·execution_quantity·kill_switch 줄이 없다. AUTHORITY 줄(auto_core_tickets.py:68)은 문맥에도 없고 그대로다. |
| G8-5 대상 테스트 | PASS | checks.json:164-181: `test_auto_core*.py` 604개 실행 OK, `test_qqq_registration.py` 8개 실행 OK. |
| G8-6 / G9 연결표 | PASS (해당 없음) | task-prompt.md에 `## 연결표` 절이 없다. 새 출력 파일·알림 종류·화면 칸·예약도 없다. QQQ ① 칸 값이 바뀌고 QQQ의 ⑩ 줄이 빠질 뿐이다(auto_core_decide.py:314). |

```json
{"verdict": "PASS", "class_ok": false, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:62-64; manage-us-stock-strategy/scripts/auto_core_decide.py:314; residual ② NOCARD line out of scope per task-prompt.md:39 (auto_core_rules.py:636-639, auto_core_decide.py:305-307)"}, {"id": "G2", "result": "PASS", "evidence": "changed-files.txt:1-4 within task-prompt.md:13 allowed_paths"}, {"id": "G3", "result": "PASS", "evidence": "diff.patch:1-207 no order path strings or fill inference"}, {"id": "G4", "result": "PASS", "evidence": "auto_core_tickets.py:230-231 research block still blocks; :264-265 product approval still blocks; no write paths in diff"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_qqq_b.py:1-81 no secret reads"}, {"id": "G6", "result": "PASS", "evidence": "checks.json:7,156,160; test_auto_core_qqq_b.py:164-203"}, {"id": "G7", "result": "PASS", "evidence": "class_ok=false: INDEX_ETFS add removes QQQ from core single_nominal (auto_core_tickets.py:186-187) used by single-stock cap reason (:254-256); S7 cap still applies (alert_policy.json:769), QQQ ② still blocked (:264); APPROVED_BUY unchanged (diff.patch:21); ADDED_LINE:kill_switch (checks.json:131) is report text diff.patch:41, not a kill-switch change"}, {"id": "G8-1", "result": "PASS", "evidence": "diff.patch:5-25,29-207"}, {"id": "G8-2", "result": "PASS", "evidence": "test_auto_core_qqq_b.py:164-168,177,183-185,200; portfolio_exposure.py:1087; auto_core_rules.py:727-728"}, {"id": "G8-3", "result": "PASS", "evidence": "diff.patch has no hunk in buy_requirements/rule_file_nominal body, S7, policy, auto_core_rules.py:636-639"}, {"id": "G8-4", "result": "PASS", "evidence": "diff.patch:5-25; auto_core_tickets.py:68 unchanged"}, {"id": "G8-5", "result": "PASS", "evidence": "checks.json:164-181"}, {"id": "G9", "result": "PASS", "evidence": "해당 없음: no ## 연결표 in task-prompt.md and no new output (auto_core_decide.py:314 only removes QQQ ⑩)"}], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/qqq-b-core2/ 의 원본 기록입니다.)
