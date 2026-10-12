# dev-run risk1r2 — NEEDS_APPROVAL

- 시각(UTC): 2026-10-12T13:15:11Z → 2026-10-12T13:42:48Z
- 기준 커밋(base): `5ed21b4c04e2e23e7fb952e110322470bbe1a4c7` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/schemas/auto-core-ticket.schema.json, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_risk1r.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_tickets.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 0
- 테스트: 기준선 Ran 2927 · 실패 28 → 변경 후 Ran 2944 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `84b4a4837b52554d8d6b800516eb72172f3ac46db3b1c9d2922199469c1e2b28`
- Judge 파일 sha256: `e2435320d178d7fa553056f93309c9a2a0f719c08c18fdc63c129cb0dc9ce9ac`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 risk1r2 -ApproveAuthority`

## 바뀐 파일

- `docs/claude/risk1r2-report.md`
- `manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json`
- `manage-us-stock-strategy/references/decision-journal-cards.md`
- `manage-us-stock-strategy/schemas/auto-core-ticket.schema.json`
- `manage-us-stock-strategy/schemas/portfolio-review-journal-payload.schema.json`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/scripts/portfolio_review_journal.py`
- `manage-us-stock-strategy/scripts/score_decision_journal.py`
- `manage-us-stock-strategy/tests/test_auto_core_decide.py`
- `manage-us-stock-strategy/tests/test_auto_core_risk1r.py`
- `manage-us-stock-strategy/tests/test_auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_score_ticket_outcomes.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `auto_core_tickets.py:406-448`(risk_1r, 상태 3가지, 표시 문장), `:936-945`(최종 qty 뒤 부착, 예외는 unk/CALC_FAILED). `auto_core_decide.py:926`(ctx indicators), `:973`, `:986-987`, `:313`. `portfolio_review_journal.py:589-592`. `score_decision_journal.py:484-492`, `:509`. 문서·보고 있음, 빈 껍데기나 TODO 없음 |
| G2 범위 | PASS | `changed-files.txt` 13개 모두 allowed_paths 안. `checks.json` reasons [], status OK |
| G3 주문·체결 추정 | PASS | diff에 주문 도구·키움 호출 없음. r_multiple은 score-fix의 기존 가상 체결(`would_fill`)과 사용자 ticket_outcome만 씀(`score_decision_journal.py:488-492`) |
| G4 쓰기 경로·fail-closed | PASS | 새 쓰기 경로 없음. 기존 일지 쓰기에 선택 키만 더해졌고, 스키마로 검증(`portfolio_review_journal.py:633`). 상태 파일은 보호 해시 검사를 통과(checks.json). 지표가 없으면 "1R 확인 필요" unk로 보임(`auto_core_tickets.py:416-417`) |
| G5 비밀 | PASS | 비밀·계좌 읽기나 출력 없음 |
| G6 테스트 | PASS | 지운 단언과 skip 없음, expectedFailure 증가 없음. 새 테스트 17개(`test_auto_core_risk1r.py:109-371`). 새 실패 없음(new_failures [], 28=기준선) |
| G7 class | PASS | 권한·한도·주문 단계·kill switch 값 변경 없음. quantity_authority 새 값 없음(class 판정은 경로 때문) |
| J-a | PASS | 허용 경로 밖 변경 없음. recheck·kill_switch·TICKET_AUTHORITY 검사 유지(`portfolio_review_journal.py:231`) |
| J-b | PASS | risk_1r는 주문표가 완성된 뒤에만 붙고, 다른 계산이 이 값을 읽지 않음(`auto_core_tickets.py:929-937`). T4는 8개 픽스처의 tickets(risk_1r 제외)·blocked·no_action·candidates/keys를 GOLDEN 해시와 비교함(`test_auto_core_risk1r.py:36`, `:188`) |
| J-c | PASS | EMA20−0.75×ATR14, ROUND_FLOOR 센트(`auto_core_tickets.py:421`). 지표는 평가 세션 t 값(`auto_core_rules.py:531-534`). 자릿수 6/2/센트/6은 T1·반올림 테스트로 확인(`test_auto_core_risk1r.py:110-128`) |
| J-d | PASS | risk_1r는 표시·일지·채점에서만 쓰임(Grep 결과). 새 키·문구에 "stop" 없음(유일한 등장은 지시문 A.1이 정한 출처 문자열 `auto_core_tickets.py:54`) |
| J-e | PASS | payload 스키마는 선택 속성 2개만 추가. 사람 항목은 정확한 키 집합 검사를 유지(`:175-177`). 매도 payload에는 risk_1r 없음(`:590`, 테스트 `:290`) |
| J-f | PASS | SCORED horizon이고 매수·체결·ok일 때만 계산, PENDING은 null(`score_decision_journal.py:352-369`, 테스트 `:341`). forbidden_keys [] 단언 있음 |
| J-g | PASS | 바뀐 스크립트에 비ASCII 0건. 비교 모드에서 runCore.tickets[].risk1r를 확인하는 테스트 있음(`test_auto_core_risk1r.py:227`, `test_auto_core_decide.py:401`) |

참고(병합 차단 아님):
- **같은 날 재실행 시 HOLD 가능:** decision_sha256에 risk_1r이 들어갑니다. 기록 모드에서 병합 전에 이미 기록된 같은 날 결정을 새 코드로 다시 돌리면, 기존 재실행 규칙(R2-5)대로 HOLD가 한 번 날 수 있습니다. 지금은 비교 모드라 해당이 없고, Builder 보고서에 이미 적혀 있습니다.
- **매도 payload의 evidence_weak_kinds:** 이 키는 매도 payload에도 들어갑니다. 지시문은 risk_1r만 매수로 한정했으므로 지시와 충돌하지 않습니다.

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:406"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/risk1r2/changed-files.txt:1"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:488"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/portfolio_review_journal.py:633"}, {"id": "G5", "result": "PASS", "evidence": "workspace/outputs/dev-runs/risk1r2/diff.patch:1"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_risk1r.py:188"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/portfolio_review_journal.py:231"}, {"id": "J-a", "result": "PASS", "evidence": "workspace/outputs/dev-runs/risk1r2/checks.json:128"}, {"id": "J-b", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:936"}, {"id": "J-c", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:421"}, {"id": "J-d", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/auto_core_tickets.py:940"}, {"id": "J-e", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/portfolio_review_journal.py:590"}, {"id": "J-f", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:352"}, {"id": "J-g", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_auto_core_risk1r.py:227"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-12T14:03:28Z
- 병합 커밋: `8ed2107ff892b3750d7fefe8fe849425b4fd98db` · 방식: ff
- 사용자 승인(-ApproveAuthority): 2026-10-12T14:03:25Z

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/risk1r2/ 의 원본 기록입니다.)
