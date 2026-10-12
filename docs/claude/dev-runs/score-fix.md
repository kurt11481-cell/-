# dev-run score-fix — READY_TO_MERGE

- 시각(UTC): 2026-10-12T11:10:11Z → 2026-10-12T11:34:27Z
- 기준 커밋(base): `e49bc35da87c1487fcd7535c952f82fcb54c9ec0` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): general
- 상태: **READY_TO_MERGE** · 재시도: 0
- 테스트: 기준선 Ran 2910 · 실패 28 → 변경 후 Ran 2927 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `869836e66ec04975ba9573b8df318232c530f86467896228a537f7602887a65d`
- Judge 파일 sha256: `5f51fe3f7db51a5d7ebb5b77b60228d294582501f09571bb929d65d41da54c1a`
- 사유: 없음
- 다음: `.\tools\dev-merge.ps1 score-fix`

## 바뀐 파일

- `docs/claude/score-fix-report.md`
- `manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json`
- `manage-us-stock-strategy/references/decision-journal-cards.md`
- `manage-us-stock-strategy/scripts/score_decision_journal.py`
- `manage-us-stock-strategy/tests/test_decision_journal_cards.py`
- `manage-us-stock-strategy/tests/test_score_ticket_outcomes.py`

## Judge 보고 원문 (1회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | `score_decision_journal.py:255-290`(시작 세션 `_start`), `:292-303`(`pre_action_move`), `:416-450`(주문표 채점), `:685-716`(비교 모드 파일 읽기). 빈 껍데기·하드코딩·TODO 없음 |
| G2 범위 | PASS | `changed-files.txt:1-6`에 허용 경로 6개만 있음. `checks.json` status OK, reasons [] |
| G3 주문·체결 추정 | PASS | 주문 경로·키움 호출 없음. `would_fill`(`:446`)은 보고서 안에서만 쓰는 가상 값(등급 D)이고 상태나 체결 기록으로 흘러가지 않음. 사용자 실제 체결은 일지 `ticket_outcome`만 씀(`:388-413`) |
| G4 쓰기 경로·fail-closed | PASS | 새로 쓰는 경로 없음. `load_compare_tickets`는 읽기만 함(`:685`). 쓰는 곳은 기존 `write_report`(`:650`)뿐. 자료가 없거나 깨지면 `NOT_SCORABLE`이나 `errors`로 남음(`:425-431`, `:441-445`, `:702-713`) |
| G5 비밀·계좌 | PASS | 오류에는 파일 이름과 이유만 남김(`:702-713`). 행 키는 10개로 고정(`test_score_ticket_outcomes.py:313`) |
| G6 테스트 | PASS | 기존 테스트는 시작 세션 기준만 하루 옮겼고 기대값은 같음(`test_decision_journal_cards.py:556-571`). 새 테스트 17개 추가(Ran 2910→2927, skip 3→3), expectedFailure 없음, 새 실패 0 |
| G7 class | PASS | 주문 단계·도구·예산·상한·대조 불변 조건·kill switch 변경 없음. 새 `quantity_authority` 값 없음. `:491`은 원래 있던 줄 |
| J-a | PASS | 6개 경로만 바뀜. `auto_core*.py`, `test_auto_core*.py`는 그대로 |
| J-b | PASS | 시작은 마감 시각이 결정 시각보다 엄격히 뒤인 첫 세션(`:262`, 같으면 다음). USER 규칙(`:286`), `pre_action_move`(`:292`), `start_close_vs_recorded_reference`는 decision_session 종가 기준(`:532-536`). T1 값이 지시문과 같음(`test_decision_journal_cards.py:562-579`) |
| J-c | PASS | 평가 시각까지 마감한 세션만 씀(`_completed_sessions` `:217`). 가상 체결은 그 세션이 끝난 뒤에만 판정(`:441`). 사용자 결과는 SCORED 구간만 계산(`:359-362`). 테스트 `test_decision_journal_cards.py:618`, `test_score_ticket_outcomes.py:126,201` |
| J-d | PASS | 주문표는 `ticket_results`에만 들어감(`:489`, `:543-548`). `results == []` 확인(`test_score_ticket_outcomes.py:277`). `ticket_records` 없이 부르는 기존 형태도 동작(`:317`). test_auto_core_decide 69개, test_portfolio_status 15개 OK |
| J-e | PASS | 매수는 종가 ≤ 상한, 매도는 종가 ≥ 하한(`:446`). 부호와 미체결 0·`NOT_FILLED_AT_CAP` 처리(`:338-349`). 사용자 상태별 처리(`:388-413`). 등급 D(`:424`), 요약 `COUNTERFACTUAL_D`(`:465`). 미체결 줄의 SPY 대비를 `NOT_APPLICABLE`로 둔 것은 Builder가 보고서에 밝힌 해석이라 받아들임 |
| J-f | PASS | 출력에 상한·수량·주문 종류·authority 키와 값이 없고 `forbidden_keys == []`(`test_score_ticket_outcomes.py:290-315`). 스크립트에 비ASCII 문자 0건. import는 기존 4개 + 2개(`:46-49`, `test_decision_journal_cards.py:700-702`). auto_core import 없음 |
| J-g | PASS | 날짜 폴더의 `decision.json`만 읽고 rerun 파일은 제외(`:695-696`). 깨진 파일은 건너뛰고 기록만 남김(`:702-713`). 일지 우선과 중복 제거(`:321-335`). 테스트 `test_score_ticket_outcomes.py:234,248` |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:255-303,416-450,685-716"}, {"id": "G2", "result": "PASS", "evidence": "workspace/outputs/dev-runs/score-fix/changed-files.txt:1-6"}, {"id": "G3", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:388-413,446"}, {"id": "G4", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:650,685,702-713"}, {"id": "G5", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:702-713"}, {"id": "G6", "result": "PASS", "evidence": "manage-us-stock-strategy/tests/test_decision_journal_cards.py:556-571; workspace/outputs/dev-runs/score-fix/checks.json:139-144"}, {"id": "G7", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:491"}, {"id": "J-a", "result": "PASS", "evidence": "workspace/outputs/dev-runs/score-fix/changed-files.txt:1-6"}, {"id": "J-b", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:262,286,292,532-536; manage-us-stock-strategy/tests/test_decision_journal_cards.py:562-579"}, {"id": "J-c", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:217,359-362,441"}, {"id": "J-d", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:489,543-548; manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:277,317"}, {"id": "J-e", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:338-349,388-413,424,446,465"}, {"id": "J-f", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:46-49; manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:290-315"}, {"id": "J-g", "result": "PASS", "evidence": "manage-us-stock-strategy/scripts/score_decision_journal.py:321-335,695-713; manage-us-stock-strategy/tests/test_score_ticket_outcomes.py:234,248"}], "min_fixes": []}
```

VERDICT: PASS

## 병합

- 병합 시각(UTC): 2026-10-12T11:57:45Z
- 병합 커밋: `d70aac2f3ae24dde218d31604adc1fd2d4431b40` · 방식: ff

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/score-fix/ 의 원본 기록입니다.)
