---
id: hwm-fix-report
title: S7 HWM 소급 누락(D6) 수정 Builder 보고 — 풀린 보류 세션 재평가(①) + 대체된 검토 기록(③)
date: 2026-10-17
prompt: docs/claude/hwm-fix-builder-prompt.md
class: K3 수동 경로 Builder(worktree hwm-fix). 커밋하지 않음. 다음 단계: 별도 Judge 세션(docs/claude/hwm-fix-judge-prompt.md)
status: 완료(Judge 대기). 4절 멈춤 항목은 Cowork 추가 범위(선택지 A, 프롬프트 "추가 범위" 절)로 해소 — test_auto_core_risk1r.py GOLDEN 5개만 갱신
---

# 0. worktree HEAD

- worktree `worktree-hwm-fix` HEAD = `1259f566c729f9a4197359b4495b60821adef59d` = 프롬프트 base. 사이 커밋 없음.
- 시작 시 base 파일 sha256 5개 모두 프롬프트 값과 일치(portfolio_exposure.py 81130d05…, run_portfolio_exposure_review.py aa137f20…, test_portfolio_exposure_fail_closed.py 63d194fe…, test_portfolio_exposure_judge_fixes.py 00e3fe59…, s5_exposure_fixtures.py 86a686e5…).
- 변경은 worktree에만 있고 커밋하지 않았다(지켜야 할 것 5).

# 1. 바꾼 줄 (diff 요약)

`git diff --stat`: portfolio_exposure.py +247/−, run_portfolio_exposure_review.py +139/−, test_portfolio_exposure_fail_closed.py +52/−5(입력만), test_portfolio_exposure_judge_fixes.py +6/−2(입력만), test_auto_core_risk1r.py +7/−5(추가 범위: GOLDEN 5개 + 주석 2줄), 새 테스트 2개. 바뀐 파일은 보고서 포함 8개. s5_exposure_fixtures.py는 바꾸지 않았다(sha256 그대로).

**manage-us-stock-strategy/tests/test_auto_core_risk1r.py (추가 범위, 4절)**
- 37~38행 영문 주석 2줄(프롬프트 지정 문구), 39·45~48행 GOLDEN `default`·`sell`·`pwr`·`decide_compare`·`decide_apply` 5개를 Windows에서 잰 새 값으로. `g2b`·`cash5`·`research_block`, 단언(200행), 다른 테스트는 그대로. 테스트 이름·개수 그대로(17개).

**manage-us-stock-strategy/scripts/portfolio_exposure.py**
- 82~86행: 상수 `DEAL_DATE_TIMEZONE`(Asia/Seoul), `UNSETTLED_SELL_KEYS`·`UNSETTLED_BUY_KEYS`, `SUPERSEDED_REVIEW_REASON`.
- 422~563행 새 함수: `_timestamp`, `_capture_view`(캡처 파싱, 금액 음수·시각 없음 → None, 예수금+미정산 매도−미정산 매수 합), `_session_bounds`(달력 행 core_open_at·core_close_at), `revalue_held_session`(B-4~B-6).
- 596~613행 `evaluate_review_lines` 서명에 선택 인자 `broker_captures`, `session_bounds`, `revalue_held_sessions=True`(내부 C-1 스위치) + docstring. 결과 초기 dict에 `revalued_sessions`·`superseded_journal_reviews`(빈 목록).
- 680~708행 세션 반복: 덮는 창을 모아 `skipped_sessions`에 그대로 넣고, 창이 모두 끝났으면 `revalue_held_session` 호출(실패 → `HELD_SESSION_NOT_REVALUABLE:<S>:<이유>` UNVERIFIED 반복 중단, 종가·현금 누락 → 기존 `EQUITY_GAP`), 끝 없는 창이 있으면 지금처럼 건너뜀. 보류 밖 세션 경로(snapshot_for + cash_usd)는 들여쓰기만 바뀜.
- 732~742행: 재평가를 시도했으면 같은 입력을 `revalue_held_sessions=False`로 한 번 더 계산(C-1) — 옛 사건 목록과 HWM 하한(B-5, 둘 중 큰 쪽).
- 749~759행: 짝 없는 완료 항목이 옛 사건과 (line_id, breach_date, hwm) 정확히 같으면 `superseded_journal_reviews`(reason `HWM_RECOMPUTED_HELD_SESSIONS`), 아니면 지금처럼 unmatched.
- 1235~1237·1255~1261·1348~1349행 `build_exposure_review`: 선택 인자 2개 + docstring + 전달.
- 바꾸지 않음: 1070~1075행 필터(지금 1280~1285행), 532~534행 조정 적용(지금 714~716행), 보류 창 계산, HELD 판정, 트리거, `pause()`, 밴드·상한·제안 평가, R5, `activation_candidate`, 표시·렌더.

**manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py**
- 12~14행 모듈 docstring, 33행 `proposal_content_hash` import, 61~66행 상수(`PROPOSAL_GLOBS` 두 위치, `VERIFIED_CASH_STATUSES`, `UNSETTLED_FIELDS`).
- 176~289행 새 함수: `_read_json`, `_read_time`, `proposal_index`, `broker_capture`(A-2 연결 조건), `broker_captures`(리비전별 캡처 + `BROKER_CAPTURE_UNLINKED:<rev>:<이유>` 메모, 기준 스냅샷은 메모 없이 제외), `session_bounds`(달력 행).
- 519~521행: `reconstruct_snapshots` 출력은 그대로 두고 캡처를 따로 만든 뒤 메모를 `ledger_notes`에 덧붙임. 540행: `evidence_root`를 non_default 판정에 추가. 567~568행: `build_exposure_review`에 `broker_captures`·`session_bounds` 전달. 603~605행: 새 CLI `--evidence-root`(기본 = 이 저장소 뿌리, 다른 값이면 non_default_inputs에 `evidence_root` 표시).
- `reconstruct_snapshots`·`read_ledger_entries` 서명·출력 불변(auto_core.py 215~231행 `_ledger_snapshot_after`, score_decision_journal.py 773행 영향 없음 — R1·R3 테스트).

# 2. 새 규칙 (①·③, B-6 날짜 기준)

① 평가 세션보다 앞선 세션 S를 덮는 보류 창(입출금 미신고 `cash_holds`, 매도 대금 대기 `sale_holds`)이 모두 끝났으면 S를 건너뛰지 않고 다시 평가한다. N = 가장 이른 브로커 읽기가 S의 core_close_at 이후인 첫 확정 리비전, P = 가장 늦은 읽기가 S의 core_open_at 이전인 마지막 확정 리비전(둘 다 1070~1075행 필터를 지난 스냅샷만). N 앞에서 as_of ≥ S인데 캡처가 없는 리비전이 있거나 N 캡처가 없으면 실패. N의 가장 늦은 읽기가 다음 세션 개장 전이면 POST_CLOSE, 아니면 P와 N의 보유와 "예수금 + 미정산 매도 정산 − 미정산 매수 정산"이 같을 때만 BRACKETED(주문 가능액 자체는 비교하지 않음 — 개장 전 +$3 사례). 자산 = N 보유 × S 원시 종가 + N 주문 가능액 − B-6 보정, 그 뒤는 보류 밖 세션과 같이 532~534행 조정(효력일 ≤ S)을 먼저 HWM에 더하고 비교한다. 보유 종목에 S 다음 날 ~ N의 가장 늦은 읽기(뉴욕 날짜) 사이 효력 분할이 있으면 실패(수량 비율 변환 없음). 실패는 모두 `HELD_SESSION_NOT_REVALUABLE:<S>:<이유>`로 UNVERIFIED → `hwm_line_or_pause_state_missing_or_corrupt` → 추가·신규 매수 멈춤, 매도·줄이기 권고와 `automatic_sell` false는 그대로, 출력 hwm은 재평가 끈 계산보다 낮지 않다. 창 하나라도 끝이 없으면 지금처럼 건너뛰고 HELD(보류 중 fail-closed 불변). ③ 재평가를 시도한 실행은 같은 입력을 재평가 없이 한 번 더 계산해, 새 계산과 짝이 없는 `line_review_completed` 완료 항목 중 옛 사건과 키가 정확히 같은 것을 "대체됨"으로 표시한다. 그 항목은 unmatched가 아니고 새 사건을 완료하지 않는다(새 L2 사건은 열린 채 멈춤 유지). 일지는 쓰지 않는다. **B-6 날짜 기준**: 키움 거래내역 `deal_dt`는 한국 날짜다 — broker-snapshot-reconciliation.md 269행("Transaction-history rows (I3) count by KST day and processing time"), cash_flow_evidence.py 164행(`deal_dt`를 시각 없는 날짜로만 읽음). 그래서 S보다 늦게 효력이 생기는 조정의 새 외부 행은 N 자신의 신고 블록이면 모두 N 현금에 있다고 보고 빼고, 그 밖의 블록은 행 날짜 < N 첫 읽기의 한국 날짜면 빼고, > N 마지막 읽기의 한국 날짜면 두고, 그 사이(같은 날)면 실패한다. 조정 금액이 그 블록 새 외부 행 합과 다르면 실패.

# 3. 테스트

**기준선(변경 전, Windows Python 3.13.15)**: `test_portfolio_exposure*.py` Ran 125 OK · `test_run_portfolio_exposure_review*.py` Ran 24 OK · `test_auto_core*.py` Ran 423 OK(skipped 1) · `test_score_*.py` Ran 66 OK · `test_decision_journal_cards.py` Ran 36 OK · `test_journal_score_task_static.py` Ran 5 OK · 전체 Ran 3162 FAILED(failures 19, errors 9, skipped 3) — 실패 28건은 모두 worktree에 없는 git 밖 산출물(workspace/outputs/activation·portfolio-strategy 등, stock-strategy-system/market_snapshot.example.json)과 키움 acceptance 바인딩 관련 기존 실패.

**변경 후**:
| 대상 | 결과 |
|---|---|
| `test_portfolio_exposure*.py` | Ran 141 OK (+16) |
| `test_run_portfolio_exposure_review*.py` | Ran 29 OK (+5) |
| `test_auto_core*.py` | 추가 범위 전: Ran 423 FAILED 1(`test_auto_core_risk1r…hash_as_before`, 4절) → GOLDEN 갱신 뒤(Windows): **Ran 423 OK (skipped 1)**, `test_auto_core_risk1r.py` 단독 Ran 17 OK |
| `test_score_*.py` / `test_decision_journal_cards.py` / `test_journal_score_task_static.py` | 66 / 36 / 5 OK |
| 전체(test-runner, 출력 파일의 FAIL/ERROR 줄을 기준선과 직접 비교) | 추가 범위 전: Ran 3183 FAILED(failures 20, errors 9, skipped 3) — 새 실패는 risk1r 1건뿐. GOLDEN 갱신 뒤: **Ran 3183 FAILED(failures 19, errors 9, skipped 3) — 실패·에러 28건이 기준선 28건과 한 줄도 다르지 않음(새 실패 0, 사라진 실패 0)**, Ran 감소 없음(+21 = 새 테스트) |
| `validate_schema_contracts.py` | PASS |

새 테스트(전부 통과):
- `tests/test_portfolio_exposure_hwm_fix.py` — H1 매도 대기 창 풀림 → POST_CLOSE 재평가가 새 HWM(skipped_sessions 그대로) · H2 입출금 창 풀림 → L1 하루 앞당김 · H3 안 풀린 창·매도 대기·겹친 창(하나만 풀림) → HELD, 재평가 없음 · H4 브래킷 불일치 → UNVERIFIED, 트리거·멈춤, 줄이기 권고 유지, automatic_sell false · H5 BRACKETED · H5b 개장 전 주문 가능액 +$3.03 → 거짓 불일치 없음 · H6 N/N 앞 리비전 캡처 없음·옛 픽스처·세션 시각 없음 → UNVERIFIED(건너뜀으로 안 돌아감) · H7 평가 세션 뒤 대조는 창을 풀지도 재평가에 쓰이지도 않음 · H8a 매도와 입금 신고가 같은 대조 · H8b 늦게 신고한 출금(거짓 L1 없음, HWM 9000.00) · H8c 다른 블록 행이 N 캡처일과 같은 날 → UNVERIFIED · H8d 재평가 실패 시 출력 HWM = 재평가 끈 HWM(하한) · H12 분할 → 실패 · H9 ③ 대체/unmatched/완료 세 경우 · H10 보류 없는 입력(auto_core_replay 형태) → review_lines가 재평가 끈 계산과 같고 새 키는 빈 목록 · H11 10-01~10-16 실데이터 모양(근거 6 표의 보유·주문 가능액·예수금·미정산·종가·읽기 시각) → HWM 31711.76(10-06), L1 10-12·L2 10-15, L3 없음, pauses `REVIEW_LINE_OPEN:L2`, L2 triggered_in_current_drawdown true, fail_closed 비활성, 매수 제안 reasons에 REVIEW_LINE_OPEN:L2, 같은 입력의 옛 규칙 = 30255.3600·L1 10-14·L2 10-16. (H8a~d의 "새 HWM ≥ 옛 HWM, 옛 사건의 선은 새 계산에서 같은 날 이전" 단언 포함.)
- `tests/test_run_portfolio_exposure_review_hwm_fix.py` — R1 연결된 리비전 캡처 채움 + 재구성 스냅샷 불변 · R2 proposal_id 없음·대조안 없음·대조안 해시 불일치 · R2 스냅샷 해시 불일치·보유 불일치·cash UNVERIFIED·음수 금액·스냅샷 파일 없음 → 각각 None + 메모 · R3 `auto_core._ledger_snapshot_after`가 읽는 holdings·cash_usd 같음 · R4 실행이 캡처·세션 시각을 넘기고 다른 근거 뿌리는 `evidence_root`로 표시.

**기존 테스트 입력 수정(단언 불변)**:
- `test_portfolio_exposure_fail_closed.py` 8~49행: 입력 도우미 `et`·`session_bounds`·`capture`·`released_review`(Scenario.review()와 같은 호출 + 캡처·세션 시각, 스키마 검사 포함)와 import. Scenario는 test_portfolio_exposure.py(허용 목록 밖)에 있어 인자를 더할 수 없으므로 같은 파일 안 도우미로 넣었다.
- 같은 파일 278~281행 `test_a_later_full_declaration_ends_the_hold`: 호출만 `released_review`로(rev 2 개장 전 읽기 6000, rev 3 다음 날 개장 전 6000). B-6으로 HWM 11000.00 단언 그대로 통과.
- 같은 파일 300~303행 `test_sale_waiting_for_cash_confirmation_does_not_fire_a_false_line`(두 번째 호출만): rev 2 장 마감 뒤 읽기, 주문 가능액 7000 = 현금 5000 + 매도 대금 2000(프롬프트 지시대로).
- `test_portfolio_exposure_judge_fixes.py` 28행 import, 111~114행 `test_hold_is_lifted_once_the_session_reaches_the_later_reconciliation`: 호출만 `released_review`로(rev 2 개장 전 8000, rev 3 EVAL 개장 전 8000 → 09-28 BRACKETED, 09-29 POST_CLOSE).
- 69~100행 두 테스트는 예상대로 그대로 통과(늦은 대조가 필터로 빠져 창이 안 풀림).

# 4. 멈춤·범위 문제

**해소(선택지 A)** — Cowork 추가 범위(프롬프트 "추가 범위" 절, 2026-10-17 14시대 KST)에 따라 아래 GOLDEN 5개만 A의 새 값(Windows 측정)으로 바꾸고 지정 주석을 달았다. 고친 뒤 Windows에서 `test_auto_core_risk1r.py` Ran 17 OK, `test_auto_core*.py` Ran 423 OK(skipped 1). 아래는 처음 보고 그대로 둔 기록이다.

**(처음 보고) 멈춤 1건 — 범위 밖 기존 테스트의 단언 변경 필요(프롬프트 "테스트" 절 마지막 규칙)**
- 파일:행: `manage-us-stock-strategy/tests/test_auto_core_risk1r.py:36-47`(`GOLDEN`), 단언 198행.
- 무엇: 8개 다이제스트 중 `default`·`sell`·`pwr`·`decide_compare`·`decide_apply` 5개가 바뀐다. `g2b`·`cash5`·`research_block`은 그대로.
- 원인(확인): 티켓에 들어가는 `s7_review_id`(= S7 리뷰 전체의 canonical hash, portfolio_exposure.py `review_content_hash`)만 바뀐다. `review_lines`에 새 키 2개(`revalued_sessions`·`superseded_journal_reviews`, 이 픽스처에서는 빈 목록)가 생겨 리뷰 해시가 달라지기 때문이다. 검증: 같은 테스트 도우미를 새 키 두 개만 빼고 다시 돌리면 8개 다이제스트가 모두 GOLDEN과 일치하고, 두 실행의 뷰 diff는 `s7_review_id` 6곳뿐이다(티켓 수량·가격·blocked·no_action·keys 동일).
- 고치지 않았다. Cowork가 고를 길(Builder 의견: A):
  - A) 범위에 `test_auto_core_risk1r.py`를 더해 5개 GOLDEN을 새 값으로 바꾸고 이유 주석을 단다. 새 값: default `0ddc8af344e761de9af9eb90a75a226fafde6b1acd2d238d861f987fa4e20423`, sell `04d0c947817377eb8f51815b0c47173988236afee41519c1eacb9a66ecbbbadc`, pwr `cb46340d4e5c08df3a793fff727dc1c3537fb084f57a0b413d50dd82f7fda807`, decide_compare `612f246deed9729f1d61fa7bdc913c54ddc18945a1f4f943903837bdad993955`, decide_apply `91c252b86a22b15808196cc38f36c5e954bbed5734657c35990ad8b2c4f200a5`.
  - B) 새 키를 비어 있으면 내지 않게 바꾼다 — GOLDEN은 그대로지만 B-7("새 키만 더한다")·H10("새 키는 빈 목록")과 어긋나고, 읽는 쪽이 키 존재를 가정할 수 없다. 권하지 않음.
- 기본 처분(처음 보고 때): Cowork 결정 전까지 NO_CHANGE(병합하지 않음). → Cowork가 A로 정해 해소.
- 그 밖: 범위 밖 파일(auto_core*.py, t2rc-oracle.py, 스키마, 정책, cash_flow_evidence.py, portfolio_review_journal.py)은 고칠 필요가 없었다.

# 5. 실데이터 결과 (읽기 전용)

실행: worktree 러너와 base 러너(변경 전 같은 worktree 코드), 입력 = 메인 체크아웃의 state·ledger·journal·closes-root, worktree 러너만 `--evidence-root` = 메인 체크아웃, `--now 2026-10-16T23:00:00Z`, `--output-root` = 세션 스크래치 폴더(저장소 밖). workspace/outputs·stock-strategy-system에 쓰지 않음, auto_core.py·키움 실행 없음. alert_policy.json은 worktree와 메인이 같은 sha256(98ef14e0…). 장부 14건 모두 연결(BROKER_CAPTURE_UNLINKED 메모 0).

**`--session 2026-10-16`**: status EVALUATED, hwm_usd 31711.7600 · hwm_date 2026-10-06, events L1 2026-10-12(threshold 28540.58400)·L2 2026-10-15(25369.40800) 둘 다 open, pauses add·new_buy = [REVIEW_LINE_OPEN:L2], fail_closed 비활성, superseded [], unmatched [].

| 세션 | 방식 | 리비전 | 가장 이른 읽기 → 가장 늦은 읽기(UTC) | 주문 가능액 | 보정 | 자산 |
|---|---|---|---|---|---|---|
| 10-02 | BRACKETED | 18 | 10-05 23:59:34.97 → 23:59:36.03 | 5.92 | 0 | 30456.97 |
| 10-06 | POST_CLOSE | 20 | 10-07 04:36:49.89 → 04:36:50.91 | 4463.1 | 0 | 31711.76 |
| 10-07 | POST_CLOSE | 21 | 10-07 23:21:55.25 → 23:21:56.27 | 9395.2 | 0 | 30972.82 |
| 10-08 | POST_CLOSE | 23 | 10-09 07:01:40.20 → 07:01:41.21 | 9395.21 | 0 | 29037.23 |
| 10-09 | POST_CLOSE | 24 | 10-09 23:52:04.18 → 23:52:05.19 | 12467.71 | 0 | 28867.2895 |
| 10-12 | POST_CLOSE | 25 | 10-13 03:51:24.12 → 03:51:25.22 | 12469.18 | 0 | 27695.1487 |

근거 6 표와 6건 모두 같다(±0.01 안).

**base 대비 차이 키 경로(10-16)**: `review_id`, `inputs.non_default_inputs`(`evidence_root` 추가), `alerts[0..1].breach_date`, `review_lines.hwm_usd`·`hwm_date`, `review_lines.events[0..1]`와 `open_events[0..1]`의 breach_date·closing_equity_usd·hwm·hwm_date·threshold_usd, `review_lines.lines[0..8]`의 threshold_usd·distance_pct, `review_lines.next_line`의 threshold_usd·distance_pct, 새 키 `review_lines.revalued_sessions`·`superseded_journal_reviews`. pauses는 base와 같다(사유 L2 그대로). 모두 허용 목록 안.

**`--session 2026-10-12`**: status HELD(LINE_EVALUATION_ON_HOLD — 10-07~10-12 현금 창은 rev 26(as_of 10-13)이 필터로 빠져 끝이 없음), revalued_sessions = 10-02(BRACKETED, rev 18)·10-06(POST_CLOSE, rev 20)뿐, hwm 31711.7600(10-06), events [], fail_closed 켜짐(exposure·hwm_line·undeclared_cash_flow). base 대비 차이: `review_id`, `inputs.non_default_inputs`, `review_lines.hwm_usd`·`hwm_date`·`lines[*].threshold_usd`·`next_line.threshold_usd`, 새 키 2개, 그리고 `review_lines.evaluated_through`(base 10-05 → 10-06: 재평가한 세션도 평가된 세션으로 센다 — ①의 직접 결과로 허용, 프롬프트 "추가 범위" 절).

**외부 현금 흐름 점검(브로커 스냅샷, 연결된 14건)**:

| rev | 가장 이른 읽기(UTC) | 예수금 | d1 매도 | d2 매도 | 주문 가능액 | 주문 가능액 − (예수금+미정산 매도) | 예수금 변화 | 설명 |
|---|---|---|---|---|---|---|---|---|
| 18 | 10-05 23:59 (장 마감 뒤) | 5.92 | 0 | 0 | 5.92 | 0.00 | 0.00 | |
| 19 | 10-06 13:18 (개장 전, 표시만) | 5.92 | 0 | 4457.19 | 4466.15 | +3.04 | 0.00 | 개장 전 +$3, 예수금 그대로 |
| 20 | 10-07 04:36 (장 마감 뒤) | 5.92 | 4457.19 | 0 | 4463.10 | −0.01 | 0.00 | |
| 21 | 10-07 23:21 (장 마감 뒤) | 4463.11 | 4932.10 | 0 | 9395.20 | −0.01 | +4457.19 | MVLL 118주 정산 |
| 22 | 10-08 12:16 (개장 전, 표시만) | 4463.11 | 4932.10 | 0 | 9398.25 | +3.04 | 0.00 | 개장 전 +$3 |
| 23 | 10-09 07:01 (장 마감 뒤) | 9395.21 | 0 | 0 | 9395.21 | 0.00 | +4932.10 | MVLL 119주 정산 |
| 24 | 10-09 23:52 (장 마감 뒤) | 9395.21 | 0 | 3072.51 | 12467.71 | −0.01 | 0.00 | SOXL 22주 d2 미정산 |
| 25 | 10-13 03:51 (장 마감 뒤) | 9396.68 | 3072.51 | 0 | 12469.18 | −0.01 | +1.47 | 10-11 예탁금 이용료 |

5.92 + 4457.19 + 4932.10 + 1.47 = 9396.68 = rev 25 예수금. 장 마감 뒤 확정 스냅샷 6건 모두 주문 가능액 = 예수금 + 미정산 매도 정산(±0.02 안, −0.01·0.00). 설명 안 되는 예수금 변화 없음. SOXL 3072.51은 rev 27에서 예수금으로 들어옴(9396.68 + 3072.51 = 12469.19). cash UNVERIFIED 파일(20261007T222718Z·20261009T065931Z)은 장부 리비전이 아니라 표에 없다. 한계: ust21100은 환전·출금을 보여 주지 않으므로 이 표는 "예수금 변화가 정산·이용료로 설명된다"까지만 말한다(7(a)).

**B-8 보류 밖 세션의 현금(상태 현금 = 브로커 주문 가능액?)**: 10-01 rev 16 5.92 = 5.92 · 10-05 rev 18 5.92 = 5.92 · 10-13·10-14 rev 26 12469.18 = 12469.18 · 10-15 rev 27 12469.19 = 12469.19 · 10-16 rev 28 12469.19 = 12469.19. 6/6 같다(옛 최소 정의였던 rev 16·18도 이 시점엔 미정산이 없어 값이 같음).

# 6. 바뀐 코드·테스트 파일 sha256 (최종)

| 파일 | sha256 |
|---|---|
| manage-us-stock-strategy/scripts/portfolio_exposure.py | 9397108ee0f15696206f80681148cb20431d6deb72e915c5aa9774aff9b77a72 |
| manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py | 4ae1eedfc2475a97819055af8f31c90841ee03958fe844502f198cdfc161fb78 |
| manage-us-stock-strategy/tests/test_portfolio_exposure_hwm_fix.py (새) | 5e19fa570fc9202c67c9ff2b77786603aa95a46ef699841872df8921d5359ae1 |
| manage-us-stock-strategy/tests/test_run_portfolio_exposure_review_hwm_fix.py (새) | 84382d5ba8cacb0975816934dfe46a1104b94a58a365258ecee764b83481eb1c |
| manage-us-stock-strategy/tests/test_portfolio_exposure_fail_closed.py | d3129cabff136db2d1c52a5f19e24448889df173e5e73714464fe774db7cee80 |
| manage-us-stock-strategy/tests/test_portfolio_exposure_judge_fixes.py | 1a24514cde57a4671c812e1b6b9e1d6f37bc7f8f500e7a213f65732e0fdbd193 |
| manage-us-stock-strategy/tests/test_auto_core_risk1r.py (추가 범위; base f79a3a974a3e997189d18141745885a2413eb7d1f0271380250cbcba95b8c82c) | e2f16d19214830e5d66b153c92ae354314acf9270faf9c8417905cc972a56e70 |
| manage-us-stock-strategy/tests/s5_exposure_fixtures.py (불변) | 86a686e5bf5eedaba740b2401fb6ca8325fe2944fbf58b531c93764467452e74 |

모든 파일 CRLF(줄 수 = CRLF 수), 스크립트·새 테스트는 ASCII만. diff에 order_authority·quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY가 든 줄 추가·변경·삭제 0(새 테스트 파일에도 0). 실데이터 확인은 docstring 한 줄 수정 전 코드로 했고, 수정 뒤 대상 스위트를 다시 돌려 같은 결과를 확인했다(동작 변경 없음).

# 7. 남은 위험

- (a) ust21100은 환전·출금을 보여 주지 않아 NO_EXTERNAL_FLOW 신고가 틀릴 수 있다(cashflow-api-gap, 별도 K3). 재평가는 신고 블록을 그대로 믿는다. 5절 표는 예수금 변화가 정산·이용료로 설명됨을 보일 뿐이다.
- (b) 장 마감 뒤 스냅샷에는 시간외 체결이 체결가로 들어간다(10-07 MVLL 60주 애프터 $41.60 vs 종가 $41.38, 약 $13). 재평가 자산은 그만큼 종가 기준과 다를 수 있다.
- (c) B-6 날짜 판정 불가(다른 블록 행이 N 읽기의 한국 날짜와 같은 날) → 그 세션 재평가 실패 → fail-closed. 실데이터는 외부 행 0건이라 영향 0.
- (d) 보류 밖 세션은 지금처럼 상태 현금(`cash_usd`)을 쓴다. rev 25 전 상태 현금은 옛 최소 정의였지만, 보류 밖 세션(10-01·10-05·10-13~10-16)에서는 상태 현금 = 브로커 주문 가능액으로 확인(5절 B-8). 앞으로 보류 밖 세션에서 두 정의가 갈리는 경우는 자동 코어 대조(주문 가능액 정의)만 쓰이므로 생기지 않을 것으로 보지만, 옛 정의 리비전을 다시 쓰는 경로는 남아 있다.
- (e) 재평가 실패는 고정된 과거 창이라 이후 모든 실행이 fail-closed(매수 0)로 남는다. 근거 파일(workspace/outputs/reconciliation/<UTC>/ 대조안·브로커 스냅샷, workspace/outputs/auto-core/<날짜>/)은 git 밖(.gitignore 48·157행)이라 지우거나 옮기면 같은 상태가 된다 — 보존 의존. 앞으로 매도 대기 창 안에서 장 마감 뒤 리비전이 하루 빠지고 그 사이 예탁금 이용료 같은 현금 변화가 있으면 브래킷 불일치로 같은 상태가 된다. 보이는 곳: S7 파일의 `review_lines.reasons`·`fail_closed.triggers[hwm_line_or_pause_state_missing_or_corrupt].reasons`에 `HELD_SESSION_NOT_REVALUABLE:<S>:<이유>`가 나온다. 코어 결정(auto_core_decide.py 1049행)에는 `G1_S7_FAIL_CLOSED:hwm_line_or_pause_state_missing_or_corrupt`처럼 트리거 id만 실리고 세부 사유는 실리지 않는다. 예외 알림 후보(auto_core_decide.py 398~457행)에는 G1 S7 fail-closed 전용 줄이 없다 — 세부 사유를 알림에 올리려면 auto_core*.py 변경(범위 밖)이 필요하다. 확인 필요: decide의 다른 예외 경로가 G1 사유를 알리는지는 이번에 열어 보지 않았다.
- (f) 계산기 G2와 코어의 이미 있던 차이(Judge 판정 항목 10 (다)): 계산기는 코어가 쓴 같은 S7 파일의 `pauses`(t2rc-oracle.py 1806·1814·1854~1855행), `review_lines.lines[].triggered_in_current_drawdown`(1851행), `review_lines.hwm_usd`(1821행)를 읽고, 그 키들의 모양 검사(1273·1279·1281행)도 그대로 통과한다(새 키만 더함). 이 변경은 두 쪽이 읽는 값을 같은 파일에서 함께 바꾸므로 새 어긋남을 만들지 않는다. 이미 있던 차이 자체는 이 변경과 무관해 그대로다.
- (g) 추가: H11 테스트에는 프롬프트 지시대로 실데이터 모양(10-01~10-16 종가·보유·현금·읽기 시각)이 들어 있다(계좌 식별자 없음).
- (h) 추가: 매 실행이 근거 뿌리 아래 대조안 파일을 모두 읽는다(지금 27개). 파일이 쌓이면 실행 시간이 늘지만 읽기 전용이다.
