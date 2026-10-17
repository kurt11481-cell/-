---
id: hwm-fix-builder-prompt
title: S7 HWM 소급 누락(D6) — 풀린 보류 세션을 장 마감 뒤 확정 스냅샷의 주문 가능액으로 다시 평가(①) + 이미 남긴 선 검토 일지 항목 처리(③)
date: 2026-10-17
class: 권한·한도 변경(K3 — 노출·HWM 경로 portfolio_exposure.py·run_portfolio_exposure_review.py, tools/dev_pipeline/authority-paths.txt 44·45행). 수동 경로: 이 Builder(worktree) → 별도 Judge 세션(docs/claude/hwm-fix-judge-prompt.md) → 사용자 병합 스크립트(Judge PASS 뒤 Cowork가 작성)
decision: 사용자 "결정 hwm-fix: a"(2026-10-15 11:00 KST, cpi-shock-review-2026-10-15.md 211행) · "결정 rrec-k3-timing: d"(2026-10-16 09:21 KST, pre-on-roadmap-review-2026-10-15.md 120~125행) — 범위 ①+③, ②(과거 EV4 재계산) 제외, 계산기(t2rc-oracle.py) 고정값 유지(C1 계속)
evidence: cpi-shock-review-2026-10-15.md 2절 D6(129행)·4-4(200~215행) · pre-on-roadmap-review-2026-10-15.md 3절(50~67행)·재검토 절(106~118행) · 관제판 hwm-fix(version 4, next·doneWhen)
base: main(codex/master-recovery-expansion) HEAD 1259f566c729f9a4197359b4495b60821adef59d — portfolio_exposure.py sha256 81130d05c8ab7a96d2368aa456a2224fb44ee998e9385257e4e28a683f17a75a · run_portfolio_exposure_review.py aa137f200371ccf4f0b53605a7aa2d6e0bd53c65226bf302c871e775fc95f0e8 · test_portfolio_exposure_fail_closed.py 63d194fe88a782c761b5b1b3617c9b91c6916b47bbecb21e25d11e25d208fe4e · test_portfolio_exposure_judge_fixes.py 00e3fe59a76328c822fff8d3162d09ca78155d2fa5684b130deb524cd20739ab · s5_exposure_fixtures.py 86a686e5bf5eedaba740b2401fb6ca8325fe2944fbf58b531c93764467452e74
model: Opus · xhigh · 새 worktree (claude --worktree hwm-fix)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 선 비율·행동·멈춤 표지(alert_policy.json)·밴드·상한·R5·R6 신고 규칙(1회 반영)·대조 불변 조건 불변 · auto_core*.py·t2rc-oracle.py·스키마 불변 · 키움 호출 없음 · 판정은 더 엄격하게만
weekly_user_touch: 0 (일회성: Builder 1·Judge 1·병합 1)
deadline: 권장 2026-10-19 L2 수락 세션 전(그 전에 병합되면 L2 검토 기록이 새 키로 한 번에 남는다. 뒤면 ③ 규칙으로 옛 키 기록이 "대체됨"으로 표시되고 새 키로 재기록 1번) · 늦어도 T2 "켜" 전
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree(claude --worktree hwm-fix) · 이유: S7 HWM·검토선 판정 의미 변경(K3)

# 목표

S7 R4 검토선(`evaluate_review_lines`)은 보류 창(R6 입출금 미신고 `cash_holds`, 매도 대금 대기 `sale_holds`) 안의 세션을 건너뛴다(portfolio_exposure.py 516~520행). 매 실행 처음부터 다시 계산하지만 보류 창이 과거 기간으로 고정돼, **보류가 풀린 뒤에도 같은 세션을 영원히 건너뛴다.** 그래서 10/6 실제 고점 $31,711.76이 빠지고 시스템 HWM은 $30,255.36(10/5)이다. 같은 함수 528행 주석("skipping would understate the HWM")이 경계한 결과이고, 승인 정책 R6은 "보류"라고만 했다(loss-limit-review-s5-policy-proposal-2026-10-01.md 56~57행).

**바꿀 의미 두 개**

- ① 평가 세션보다 앞선 세션 S를 덮는 보류 창이 **모두 풀렸으면** 건너뛰지 않고, **S 장 마감 뒤 확정 스냅샷의 보유 × S 정규장 종가 + 그 스냅샷의 브로커 주문 가능액**으로 다시 평가한다. 다시 셀 수 없으면 건너뛰지 않고 fail-closed(UNVERIFIED)로 둔다. 풀린 창 안 세션이 "건너뜀"으로 남는 경로는 없어야 한다.
- ③ 이미 남긴 `line_review_completed` 일지 항목이 ①로 옮겨진 사건(옛 키)을 가리키면, 손상(JOURNAL_REVIEW_UNMATCHED)으로 막지 않고 "대체됨"으로 표시한다. 그 항목은 새 사건을 완료 처리하지 않는다(새 사건은 열린 상태 — L2 이상이면 멈춤 유지). 일지는 쓰지 않는다(새 키 검토 기록은 기존 portfolio_review_journal.py 흐름 — 283~291행이 현재 열린 사건에서 키를 만든다).

**범위 밖(결정 d)**: 관제판 doneWhen의 "EV4 날짜(10/12)"는 ② 제외로 재현하지 않는다. 과거 decision.json의 EV4 기록(10/12 ev4_open false, s7_hwm 30255.36)은 그대로이고, 코어 ev4_sessions·계산기 ev4_hist(t2rc-oracle.py 1472~1484행)도 그 기록을 읽는다. 병합 뒤 실행부터 그날 EV4가 새 HWM × 0.9로 계산된다(auto_core_decide.py 1058행). 이 작업이 재현할 것은 S7 L1 10-12·L2 10-15다.

# 근거 (Cowork 2026-10-17 11:4x~13시 KST 읽기 전용 확인 + 내장 재검토 1회 — Builder는 원문을 다시 연다)

1. **현재 결과**: workspace/outputs/auto-core/2026-10-17/s7/2026-10-16/portfolio-exposure-review.20261016T224505563376Z.json `review_lines` — status EVALUATED, hwm_usd 30255.3600(2026-10-05), skipped_sessions [10-02, 10-06, 10-07, 10-08, 10-09, 10-12], events L1 breach 10-14·L2 breach 10-16(둘 다 hwm 30255.36, open), cash_flow steps: rev 17 HOLD → 18 CLEAR, rev 21~25 HOLD → 26 CLEAR, covered_through 2026-10-17, adjustments [].
2. **보류 창**(reconstruct_snapshots 재현, 평가 세션 10-16): cash_holds (10-02, 10-05)·(10-07, 10-13); sale_holds rev 19 (10-06, 10-07)·rev 21 (10-07, 10-08)·rev 24 (10-09, 10-12). 끝이 모두 있다(풀림). 창 계산에는 평가 세션보다 as_of가 늦은 대조를 버리는 필터(portfolio_exposure.py 1070~1075행)가 먼저 걸린다.
3. **상태 현금 정의가 바뀌었다**: rev 25 전 대조안 `cash_semantics.available_cash_usd_basis` = MIN_WITHDRAWABLE_AND_ORDER_AVAILABLE_USD(예: workspace/outputs/reconciliation/20261007T043650Z, rev 20 — 상태 현금 5.92, 브로커 `cash.order_available_cash` 4463.1). rev 25(20261013T035125Z)부터 KIWOOM_ORDER_AVAILABLE_USD. 그래서 장부 재구성 스냅샷의 `cash_usd`로는 주문 가능액 재평가가 되지 않는다 → **대조안이 가리키는 브로커 스냅샷의 `cash.order_available_cash`**가 필요하다(사용자 현금 정의 2026-10-09/10-10, CLAUDE.md Hard safety).
4. **연결은 이미 검증 가능**: 장부 14건 모두 proposal_id → 대조안 파일(proposal_content_hash 재계산 일치, kiwoom_broker_shadow.py 286행) → `source.snapshot_path`의 브로커 스냅샷(snapshot_hash = canonical_hash(snapshot_hash 키 제외) 재계산 일치, kiwoom_broker_shadow.py 124행, canonical_hash는 validation_common)으로 이어진다(Cowork·재검토 각각 재계산 14/14). 대조안 위치: 사람 경로 workspace/outputs/reconciliation/<UTC>/reconciliation_proposal.json(rev 15~26), 자동 코어 workspace/outputs/auto-core/<KST 날짜>/reconciliation_proposal.json(rev 27~28). 둘 다 git이 추적하지 않는다(.gitignore 48·157행). 캡처 시각: `source.earliest_required_retrieved_at`(가장 이른 읽기) · `source.broker_snapshot_as_of`(가장 늦은 읽기).
5. **세션 시각**: 달력 세션 행의 `core_open_at`·`core_close_at`(session_calendar_artifact.py 98~99행). 하드코딩 16:00 금지(조기 마감일).
6. **기대 실데이터**(Cowork 계산·재검토 재계산 일치, 종가 = workspace/outputs/regular-session-closes/history/{MVLL,SOXL,NBIS}.close-history.json):

| 세션 | 쓰는 확정 스냅샷(rev, 폴더) | 방식 | MVLL/SOXL/NBIS | 주문 가능액 | 자산 |
|---|---|---|---|---|---|
| 10-02 | P rev 17(20261002T040711Z, 10-02 04:07Z) ↔ N rev 18(20261005T235936Z, 10-05 23:59Z) | 브래킷(N이 다음 개장 10-05 13:30Z 뒤; 보유·예수금 5.92·미정산 0 동일) | 396/75/13 | 5.92 | 30,456.97 |
| 10-06 | rev 20(20261007T043650Z, 10-07 04:36Z) | 장 마감 뒤 | 278/75/13 | 4,463.10 | **31,711.76** |
| 10-07 | rev 21(20261007T232156Z, 10-07 23:21Z) | 장 마감 뒤 | 159/75/13 | 9,395.20 | 30,972.82 |
| 10-08 | rev 23(20261009T070141Z, 10-09 07:01Z) | 장 마감 뒤 | 159/75/13 | 9,395.21 | 29,037.23 |
| 10-09 | rev 24(20261009T235205Z, 10-09 23:52Z) | 장 마감 뒤 | 159/53/13 | 12,467.71 | 28,867.2895 |
| 10-12 | rev 25(20261013T035125Z, 10-13 03:51Z) | 장 마감 뒤 | 159/53/13 | 12,469.18 | 27,695.1487 |

   → HWM 31,711.76(10-06). L1 28,540.584 → 10-12 도달. 10-13 27,750.03·10-14 25,548.21은 L2 위. L2 25,369.408 → **10-15**(25,252.58) 도달. L3 22,198.232 → 10-16(23,695.43) 미도달. 보류 밖 세션(10-01·10-05·10-13~10-16)은 지금 값 그대로. 10-07의 rev 22(10-08 12:16Z)는 "첫 장 마감 뒤 스냅샷"이 아니라서 쓰지 않는다. 개장 전 조회는 예수금이 그대로인데 주문 가능액만 +$3.03~3.04 다르게 나온 사례가 3건이다(20261006T124359Z 8.95, 20261006T131852Z = rev 19 4,466.15, 20261008T121613Z = rev 22 9,398.25) — 그래서 브래킷 비교에 주문 가능액을 쓰지 않는다(B-4).
7. **일지**: stock-strategy-system/decision_journal.json 항목 6개(card_decision 3, card_user_decision 2, s5_activation 1), `line_review_completed` 0개(10-17 12시대 확인). docs/claude/l2-full-review-2026-10-17.md 8·133행이 10-19 수락 세션에서 L2 line_review 1건(+ L1 10-14 처리)을 기록할 예정이다 — 병합 전에 기록되면 옛 키(hwm 30255.36, breach 10-16/10-14)다. 병합이 먼저면 그 문서의 "L2(10/16)·L1(10/14)"는 L2 10-15·L1 10-12로 읽으면 된다(키는 open_events에서 만든다). 대조 키는 (line_id, breach_date, hwm), 554~557행.
8. **코어·계산기**: 코어 매수 막힘은 S7 `pauses`(실패 사유 + 열린 멈춤 선 REVIEW_LINE_OPEN, 1167~1175행)를 제안 평가(1371행)·요건 ②(auto_core_tickets.py 240~244행)·G2(922~924행)로 읽는다. 계산기는 같은 S7 파일의 pauses(t2rc-oracle.py 1806·1854행)와 `lines[].triggered_in_current_drawdown`(L2 이상, 1851행)을 읽는다. 둘 다 코어가 쓴 같은 S7 파일을 읽으므로 ① 자체는 어긋남을 만들지 않는다(pre-on 3절, rrec-k3-timing 재검토). 이 조건이 깨지는 변경은 범위 밖이다.

# 바꿀 것

## A. run_portfolio_exposure_review.py — 데이터 공급만

1. 장부 확정 리비전마다 `broker_capture` = {`earliest_read_at`, `latest_read_at`, `order_available_cash_usd`, `foreign_currency_deposit_usd`, `unsettled`(d1/d2 매도·매수 정산 4개), `proposal_id`, `snapshot_hash`} 또는 None을 만든다(금액은 문자열 Decimal). **먼저 검토할 방식**: `reconstruct_snapshots` 출력은 그대로 두고 새 함수가 리비전별 broker_capture를 만들어 `build_exposure_review`에 따로 넘긴다(기존 호출자 auto_core.py 215~231행 `_ledger_snapshot_after`·compare_streak, score_decision_journal.py 773행 영향 0). 스냅샷 dict에 키를 더하는 쪽을 고르면 기존 키·값이 한 글자도 안 바뀜을 테스트로 고정한다. 기존 함수 서명에는 선택 인자만 더한다.
2. 채우는 조건(모두 참일 때만, 하나라도 아니면 None + ledger_notes에 `BROKER_CAPTURE_UNLINKED:<rev>:<이유>`): 장부 APPLY 항목의 proposal_id와 같은 proposal_id를 가진 대조안 파일이 있고 → proposal_content_hash 재계산 = proposal_id → `source.snapshot_path` 파일의 재계산 snapshot_hash = 파일 안 snapshot_hash = `source.snapshot_hash` → 브로커 `cash.cash_status`가 검증 상태이고 쓰는 금액이 0 이상 숫자 → 브로커 보유(held_quantity, 0 초과)가 그 리비전의 재구성 보유와 같다. 새 신뢰 경로를 만들지 말고 기존 해시 함수를 쓴다. 기준 스냅샷(가장 이른 장부 항목 이전 상태)은 메모 없이 None(출력 inputs.ledger_replay_notes가 base와 달라지지 않게).
3. 달력 세션 행의 `core_open_at`·`core_close_at`을 `build_exposure_review`에 새 선택 인자(예: `session_bounds`)로 넘긴다. 없으면 재평가는 실패(B-5)한다.
4. 대조안·스냅샷 파일을 찾을 저장소 뿌리를 정하는 선택 CLI 인자(기본 = 지금 저장소 뿌리)를 더한다 — worktree 실데이터 확인에서 메인 체크아웃을 가리키기 위해서다. 파일은 읽기만 한다.

## B. portfolio_exposure.py `evaluate_review_lines` (+ `build_exposure_review` 전달)

1. 그대로 둘 것: 평가 세션보다 as_of가 늦은 대조를 버리는 필터(1070~1075행), 보류 창 계산(487~503행), 평가 세션 자신이 창 안이면 HELD(546~549행), `sale_pending_hold`, undeclared_cash_flow·SALE_PROCEEDS 트리거(1144~1155행).
2. **재평가 대상**: activation_date ≤ S < evaluation_session이고, S를 덮는 보류 창이 하나 이상이며, **S를 덮는 모든 창에 끝이 있을 때**. 이런 S는 재평가하거나 실패(B-5)로 둔다 — 건너뜀 경로는 없다. S를 덮는 창 중 끝이 없는 것이 있으면 지금처럼 건너뛴다(그 창은 평가 세션까지 덮으므로 결과는 HELD).
3. **미래 정보 금지**: 재평가·해제 판단에는 1070~1075행 필터를 지난 스냅샷만 쓴다(프로젝트 지침 5절 evidence_timestamp ≤ decision_as_of). B-4의 시각 조건은 그 안의 추가 조건이다.
4. **스냅샷 고르기**(리비전 순):
   - N = `earliest_read_at` ≥ core_close_at(S)인 첫 확정 리비전(from_ledger_entry). P = `latest_read_at` ≤ core_open_at(S)인 마지막 확정 리비전.
   - N 앞의 확정 리비전 중 as_of ≥ S이고 broker_capture가 None인 것이 있으면 실패(연결 안 된 스냅샷이 조용히 빠지지 않게). N 자체의 broker_capture가 None이어도 실패.
   - N의 `latest_read_at` < S 다음 세션의 core_open_at이면 N을 쓴다(`POST_CLOSE`).
   - 아니면 P(broker_capture 있음)와 N의 보유가 같고 "예수금 + 미정산 매도 정산 − 미정산 매수 정산" 합이 같을 때만 N을 쓴다(`BRACKETED` — 그 사이 체결이 없었다는 브로커 증거. 정산 이동 d2 → d1 → 예수금은 합을 바꾸지 않는다). 주문 가능액 자체는 비교하지 않는다(근거 6 — 개장 전 +$3 사례). 가격 움직임으로 체결을 추정하지 않는다.
5. **자산**: N 보유 × S 원시 종가 + N `order_available_cash_usd` − B-6 보정. 재평가 세션도 보류 밖 세션처럼 먼저 532~534행 조정(effective_date ≤ S)을 HWM에 적용한 뒤 비교한다. 종가 누락은 `closing_equity` 그대로 UNVERIFIED(D5). 분할: 기존 검사(corporate_actions.py 186~198행, `as_of < effective ≤ session`)는 N의 as_of ≥ S인 재평가에서 S < effective ≤ N인 분할을 못 잡으므로, 보유 종목에 S 다음 세션부터 N 캡처 시각 사이에 효력이 생기는 분할이 있으면 재평가 실패로 둔다(수량을 비율로 바꾸지 않는다). 재평가 실패(N 없음·연결 없음·브래킷 불일치·세션 시각 없음·분할·B-6 판정 불가)는 지금 `NO_CONFIRMED_SNAPSHOT`과 같은 방식으로 status UNVERIFIED, reason `HELD_SESSION_NOT_REVALUABLE:<S>:<이유>`, 반복 중단 → fail-closed(추가·신규 매수 멈춤). 이때 출력 `hwm_usd`·`hwm_date`는 C-1(재평가 끈 계산) 값보다 낮게 두지 않는다(둘 중 큰 쪽) — 코어가 그 값으로 그날 EV4를 계산해 decision.json에 남기고(auto_core_decide.py 1058~1059행) 이후 실행이 다시 읽기 때문이다. 매도·줄이기 권고와 `automatic_sell` false는 그대로.
6. **R6 1회 반영 유지**(정책 56행 "대조 때 사용자 신고로 HWM에 반영"; 기존 테스트 test_portfolio_exposure_fail_closed.py 174행 "declared deposit ... is not a gain"). 조정 시점 규칙(신고한 대조의 as_of부터, 532~534행)은 그대로 두고, 재평가 자산에서 **S보다 늦게 효력이 생기는 조정(effective_date > S)의 새 외부 행 중 deal_date ≤ N 캡처일인 행의 signed_amount_usd 합**을 뺀다(그 흐름은 N 현금에 이미 있으나 HWM 조정은 아직 — 조정 전 기준으로 맞춘다). 날짜 기준(키움 deal_date의 시간대)은 cash_flow_evidence.py `normalize_transaction_history`·키움 스펙에서 확인해 보고서에 적는다. N 자신의 신고 블록 행은 같은 대조 실행에서 읽었으므로 N 현금에 들어 있다고 본다. 그 밖의 블록에서 같은 날이라 앞뒤를 가릴 수 없거나, 조정 금액(hwm_adjustment_usd)이 그 블록 새 외부 행 합과 다르면 그 세션은 재평가 실패. 실데이터 영향 0(신고 블록은 rev 18·19·20·24·26·27·28에만 있고 모두 NO_EXTERNAL_FLOW, hwm_adjustment_usd 0.00. rev 21·22·23·25는 블록이 없어 HOLD였다).
7. **출력**: `review_lines`에 새 키만 더한다 — `revalued_sessions`: [{session, method(POST_CLOSE|BRACKETED), state_revision, earliest_read_at, latest_read_at, order_available_cash_usd, flow_correction_usd, closing_equity_usd}], `superseded_journal_reviews`(③). `skipped_sessions`는 뜻(보류 창 안 세션)과 값을 그대로 둔다(스키마 required, 기존 테스트 단언) — 재평가 여부는 `revalued_sessions`로 본다. docstring에 이 뜻을 적는다(영문, ASCII).
8. **보류 밖 세션은 그대로**(snapshot_for + `cash_usd`). 실데이터에서 보류 밖 세션은 상태 현금 = 브로커 주문 가능액이었다(10-01·10-05·10-13~10-16) — 보고서에 확인 결과를 적는다.

## C. ③ 대체된 검토 기록 (portfolio_exposure.py)

1. 같은 입력으로 **재평가를 끈 계산**(풀린 보류 세션을 지금처럼 건너뜀)을 내부에서 한 번 더 해 옛 사건 목록을 얻는다.
2. 새 계산에서 짝이 없는 `line_review_completed` 항목 중 review_status "completed"이고 (line_id, breach_date, hwm)이 옛 사건과 **정확히** 같은 것만 `superseded_journal_reviews`에 넣는다({entry_id, line_id, breach_date, hwm, reason "HWM_RECOMPUTED_HELD_SESSIONS"}). 이것은 unmatched가 아니다(1148~1149행 트리거 없음). 새 사건을 완료 처리하지 않는다.
3. 그 밖의 짝 없는 항목은 지금처럼 unmatched → fail-closed. 짝이 맞는 항목은 지금처럼 완료.
4. 일지 파일·portfolio_review_journal.py·decision_journal.json은 바꾸지 않는다.

## D. 바꾸지 않는 것

1070~1075행 필터, 선 비율·행동·멈춤 표지와 정책 파일, `pause()`(1170행) 공식, 밴드·상한·제안 평가, `evaluate_peak_reviews`(R5), `activation_candidate`, 표시 블록·렌더(1398행~), cash_flow_evidence.py, auto_core*.py, t2rc-oracle.py, portfolio-exposure-review.schema.json(review_lines에 additionalProperties 설정 없음 — 새 키 허용, 고치지 않는다), portfolio_review_journal.py, 정책·상태·장부·일지 파일.

# 테스트

새 파일 두 개(authority-paths.txt 51·52행 패턴에 맞는 이름):

`manage-us-stock-strategy/tests/test_portfolio_exposure_hwm_fix.py` (순수 함수, s5_exposure_fixtures 방식)
- H1 매도 대기 창이 풀림 → S가 장 마감 뒤 주문 가능액으로 재평가되고(POST_CLOSE), 그 값이 새 HWM이 된다. skipped_sessions에는 그대로 S.
- H2 입출금 미신고 창이 뒤 CLEAR로 풀림 → 재평가로 L1 도달일이 앞당겨진다(10-14 → 10-12형).
- H3 창이 안 풀림(끝 없음) → 지금과 같다: 재평가 없음, status HELD, LINE_EVALUATION_ON_HOLD, sale_pending·undeclared 트리거 그대로("보류 중 fail-closed 불변"). 겹친 창 중 하나만 풀린 세션도 건너뜀(B-2).
- H4 풀렸지만 장 마감 뒤 스냅샷이 다음 개장 뒤이고 브래킷 불일치 → UNVERIFIED `HELD_SESSION_NOT_REVALUABLE`, hwm_line_or_pause_state_missing_or_corrupt 활성, add·new_buy 멈춤, automatic_sell false, 줄이기 권고는 그대로 나온다.
- H5 브래킷 일치(10-02형) → BRACKETED. H5b P의 주문 가능액만 +$3이고 보유·예수금·미정산이 같음 → BRACKETED(거짓 불일치 없음).
- H6 N 또는 S 뒤(as_of ≥ S)·N 앞 리비전의 broker_capture가 None(연결 실패·옛 픽스처) → UNVERIFIED. 옛 동작(건너뜀)으로 돌아가지 않는다.
- H7 과거 `--session`(평가 세션 뒤 as_of 대조는 1070~1075행 필터로 빠짐) → 그 대조로 창이 풀리지 않고, 재평가에도 쓰지 않는다.
- H8 엄격성과 R6 1회 반영: 보류 창 안 입금·출금(늦은 신고 포함)·매도가 섞인 합성 경우 여러 개(매도와 입금 신고가 같은 대조에 있는 경우 포함)에서 (a) 매 세션 새 HWM ≥ 재평가 끈 HWM, 옛 사건의 선은 새 계산에서 같은 날 이전에 걸린다 — 재평가 실패로 반복이 중단된 경우에도 출력 hwm_usd ≥ 재평가 끈 HWM (b) 신고 흐름은 HWM에 정확히 1번 반영된다(B-6 보정) (c) N 아닌 블록에서 날짜를 가릴 수 없는 경우는 UNVERIFIED.
- H12 보유 종목 분할이 S 다음 세션 ~ N 캡처 사이에 효력 → 재평가 실패(수량 비율 변환 없음).
- H9 ③: 옛 사건과 정확히 같은 완료 항목 → superseded, JOURNAL_REVIEW_UNMATCHED 없음, 새 L2 사건 open, new_buy 멈춤(REVIEW_LINE_OPEN:L2). 어느 쪽과도 안 맞는 항목 → unmatched + fail-closed(그대로). 새 사건과 맞는 항목 → 완료(그대로).
- H10 보류가 없는 입력(auto_core_replay.py 223행 형태: holdings_decreased False, cash_flow_declaration None) → review_lines가 기준과 같다(새 키는 빈 목록).
- H11 10-01~10-16 실데이터 모양 합성(근거 6 표의 보유·주문 가능액·예수금·미정산·종가·캡처 시각) → HWM 31711.76(10-06), events L1 10-12·L2 10-15, L3 없음, pauses new_buy·add에 REVIEW_LINE_OPEN:L2, `lines` L2 triggered_in_current_drawdown true(계산기 G2가 읽는 값)·fail_closed 비활성. 매수 제안 1건을 넣으면 그 결과 reasons에 REVIEW_LINE_OPEN:L2.

`manage-us-stock-strategy/tests/test_run_portfolio_exposure_review_hwm_fix.py` (러너)
- R1 임시 폴더의 장부·대조안·브로커 스냅샷 → broker_capture가 채워지고, 기존 키는 기준 출력과 같다.
- R2 proposal_id 불일치·snapshot_hash 불일치·보유 불일치·cash_status 미검증·파일 없음 → 각각 None + ledger_notes 사유.
- R3 `_ledger_snapshot_after`가 읽는 holdings·cash_usd가 기준과 같다.

기존 테스트는 고치지 않는다. 예외 하나: 보류가 풀린 뒤를 단언하는 테스트 중 픽스처에 새 입력(broker_capture·session_bounds)이 없어 재평가가 실패하는 것은 **입력만** 더한다(s5_exposure_fixtures.py에는 기본값이면 지금과 같은 출력을 내는 선택 인자만). 찾은 것: test_portfolio_exposure_fail_closed.py 227~241행(`test_a_later_full_declaration_ends_the_hold`)·243~259행(`test_sale_waiting_for_cash_confirmation_does_not_fire_a_false_line`), test_portfolio_exposure_judge_fixes.py 102~114행(`test_hold_is_lifted_once_the_session_reaches_the_later_reconciliation`). 같은 파일 69~100행은 늦은 대조가 필터로 빠져 창이 안 풀리므로 그대로일 것이다. 넣는 입력값은 사용자 현금 정의대로 쓴다(주문 가능액 = 예수금 + 미정산 매도 정산 — 예: 243~259행의 rev 2는 장 마감 뒤 캡처, 주문 가능액 7000 = 현금 5000 + 매도 대금 2000. 5000을 넣으면 거짓 L1이 난다). 단언은 바꾸지 않는다 — B-6 덕분에 HWM 기대값(11000.00)도 그대로여야 한다. 단언을 바꿔야 하는 기존 테스트가 나오면 **멈추고** 보고서 4절에 파일:행·이유를 적는다(Cowork가 추가 범위를 정한다 — rrec-rg1 선례).

실행(Claude Code는 "auto_core.py"가 든 명령을 거부한다):
- 변경 전 base에서 먼저 기준선을 잰다. Cowork 측정(2026-10-17, Linux Python 3.10): `test_portfolio_exposure*.py` Ran 125 OK, `test_run_portfolio_exposure_review*.py` Ran 24 OK. Windows에서 다시 잰다.
- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure*.py"`, 같은 형식으로 `-p "test_run_portfolio_exposure_review*.py"`, `-p "test_auto_core*.py"`, score_decision_journal을 쓰는 테스트 `-p "test_score_*.py"`·`-p "test_decision_journal_cards.py"`·`-p "test_journal_score_task_static.py"`.
- 전체 스위트는 `test-runner` 서브에이전트(Haiku)로 돌려 실패만 보고. 기준선 대비 새 실패 0, Ran 감소 없음.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` 통과.

# 실데이터 확인 (읽기 전용, 보고서에 결과만)

- worktree 러너와 base 러너를 같은 입력으로 1번씩 돌린다: `--state`·`--ledger`·`--journal`·`--closes-root`(필요하면 `--calendar`) = 메인 체크아웃(E:\사업\##금동한\코덱스저장소) 경로, 새 뿌리 인자(worktree 러너에만 — base 파서에는 없다) = 메인 체크아웃, `--now 2026-10-16T23:00:00Z`(실행 날짜에 따라 NOT_LATEST가 켜지지 않게 고정), `--output-root` = 저장소 밖 임시 폴더(예: $env:TEMP\hwm-fix-check). workspace/outputs·stock-strategy-system에 쓰지 않는다. auto_core.py·키움 실행 금지.
- `--session 2026-10-16` 기대: 근거 6 표의 재평가 6건(±0.01), hwm_usd 31711.76·hwm_date 2026-10-06, events L1 2026-10-12(threshold 28540.584)·L2 2026-10-15(25369.408), status EVALUATED, pauses new_buy·add = REVIEW_LINE_OPEN:L2, fail_closed 비활성, superseded [], unmatched []. base 대비 차이를 키 경로 목록으로 붙인다(바뀌어도 되는 것: review_lines의 hwm_usd·hwm_date·events·open_events·lines·next_line·새 키, 그에 따른 pauses 사유·alerts의 날짜·표시 문구·review_id, inputs의 경로·시각).
- `--session 2026-10-12` 기대: status HELD(10-07~10-12를 덮는 현금 창은 rev 26이 필터로 빠져 끝이 없음), revalued_sessions = 10-02(BRACKETED)·10-06(POST_CLOSE)뿐, hwm 31711.76(10-06), events [], fail_closed 켜짐.
- 외부 현금 흐름 점검(10-05 장 마감 뒤 ~ 10-12 장 마감 뒤): 장 마감 뒤 확정 스냅샷(rev 18·20·21·23·24·25)의 예수금(foreign_currency_deposit) 연속성이 정산된 매도 대금(rev 25까지는 MVLL 118주 4,457.19 · MVLL 119주 4,932.10, cpi-shock 1-1 표 — SOXL 22주 3,072.51은 rev 24 d2·rev 25 d1 미정산이고 예수금에는 rev 27에서 들어온다)과 10-11 예탁금 이용료 $1.47(redesign-t2-firstrun-report 13절)로 설명되는지(5.92 + 4,457.19 + 4,932.10 + 1.47 = 9,396.68), 같은 스냅샷에서 주문 가능액 = 예수금 + 미정산 매도 정산(±0.02)인지 표 하나. 개장 전 조회의 +$3은 예수금이 그대로라 표시만 하고, cash UNVERIFIED 파일(20261007T222718Z·20261009T065931Z)은 뺀다. 장부 신고(rev 18 10-02~10-05·19 10-06·20 10-07·24 10-09~10-10·26 10-08~10-13, 모두 NO_EXTERNAL_FLOW)만으로는 부족하다 — ust21100은 환전·출금을 보여 주지 않는다(같은 보고서 13-1, 사용자 10-13 12:49).

# 지켜야 할 것 (어기면 Judge FAIL)

1. 바뀐 파일은 portfolio_exposure.py, run_portfolio_exposure_review.py, 새 테스트 2개, (입력만) s5_exposure_fixtures.py·test_portfolio_exposure_fail_closed.py·test_portfolio_exposure_judge_fixes.py, 보고서뿐.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 든 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열 없음. 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 금지.
3. 스크립트는 ASCII만(한국어는 `\u` 이스케이프). 정책·상태·장부·일지·workspace/policies·stock-strategy-system·workspace/outputs·docs/claude(보고서 제외) 쓰기 금지. 줄 끝은 base 파일 그대로(일괄 변환 금지).
4. 범위 밖 파일(auto_core*.py, t2rc-oracle.py, 스키마, 정책, cash_flow_evidence.py, portfolio_review_journal.py)을 고쳐야 하면 멈추고 보고한다.
5. **커밋하지 않는다.** 변경은 worktree에 둔다(병합은 사용자 스크립트가 파일 목록·sha256을 확인하고 커밋한다).

# 보고 `docs/claude/hwm-fix-report.md` (worktree 안에 새로)

0 worktree HEAD(base와 다르면 그 사이 커밋이 docs/claude만인지) · 1 바꾼 줄(diff 요약) · 2 새 규칙 한 문단(①·③, B-6 날짜 기준) · 3 테스트 목록과 결과(Ran 수, 대상·전체 새 실패 0, 기존 테스트 입력 수정 목록 파일:행) · 4 멈춤·범위 문제(없으면 "없음") · 5 실데이터 결과(재평가 표, base 대비 차이 키 목록, --session 10-12 결과, 외부 현금 흐름 표) · 6 바뀐 코드·테스트 파일 sha256 · 7 남은 위험: (a) ust21100이 환전·출금을 못 봐 NO_EXTERNAL_FLOW가 틀릴 수 있다(cashflow-api-gap, 별도 K3) (b) 장 마감 뒤 스냅샷에는 시간외 체결이 체결가로 들어간다(10-07 MVLL 60주 애프터 $41.60 vs 종가 $41.38, 약 $13) (c) B-6 날짜 판정 불가 → fail-closed (d) 보류 밖 세션은 상태 현금을 쓴다(rev 25 전 옛 정의 — 실데이터 영향 확인 결과) (e) 재평가 실패는 고정된 과거 창이라 이후 모든 실행이 fail-closed(매수 0)로 남는다. 근거 파일(대조안·브로커 스냅샷)은 git 밖(.gitignore 48·157행)이라 지우거나 옮기면 같은 상태가 된다. 앞으로 매도 대기 창 안에서 장 마감 뒤 리비전이 하루 빠지고 그 사이 예탁금 이용료 같은 현금 변화가 있으면 브래킷 불일치로 같은 상태가 된다 — 보존 의존과 이 경로를 적고, 실패 사유가 코어 결정의 G1_S7_FAIL_CLOSED·예외 알림에 보이는지 확인 (f) 계산기 G2와 코어의 이미 있던 차이(Judge 판정 항목 10 (다)) — 이 변경이 만들지 않음을 근거로.

# 작성 기록 (Cowork, 2026-10-17)

- 원문 확인: 결정 문서 3개·관제판 hwm-fix(v4)·authority-paths.txt·portfolio_exposure.py·run_portfolio_exposure_review.py·cash_flow_evidence.py·kiwoom_broker_shadow.py·auto_core_tickets/decide/auto_core/replay 해당 행·t2rc-oracle.py G2·장부 14건·대조안/브로커 스냅샷 해시 14/14·종가 이력·현재 S7 출력·일지.
- 내장 재검토 2회(Opus, 읽기 전용): 1회차 15건·2회차 14건, 모두 원문 재확인 뒤 반영. 결론이 바뀐 것 — 건너뜀 경로 제거(B-2·B-4), 미래 정보 경계를 기존 1070~1075행 필터로 통일(B-3), R6 1회 반영 보정(B-6, 입금 이중 반영 안 철회), 브래킷 비교를 보유 + 현금 합으로(개장 전 +$3 거짓 불일치), 실패 시 HWM 하한(EV4 기록 느슨해짐 방지), 분할 검사 보강, doneWhen EV4 범위 밖 명시, Judge G2 (라) 삭제·현금 흐름 판정식 정정.
- 미해결(기본 처분 = 현행 유지, 알림만): 없음. 남은 위험은 보고 7절에 Builder가 적는다.

# 추가 범위 (2026-10-17 14시대 KST, Cowork — Builder 보고 4절 선택지 A)

- 이유: `manage-us-stock-strategy/tests/test_auto_core_risk1r.py` `UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before`의 GOLDEN(36~47행)은 주문표 보기 전체의 해시라 티켓 `inputs.s7_review_id`(S7 리뷰 전체 해시)를 포함한다. B-7이 `review_lines`에 새 키 2개(이 픽스처에서는 빈 목록)를 더하므로 s7_review_id가 바뀐다. Cowork 재현(장치 VM, Linux Python 3.10): 새 키 두 개만 뺀 실행은 base와 8개 다이제스트가 모두 같고, 새 실행과의 차이는 티켓 6장의 `inputs.s7_review_id`뿐이다(수량·가격·blocked·no_action·keys 같음). 같은 파일의 선례: t2rc-corefix2가 "sell" 값을 이유 주석과 함께 바꿨다(41~42행). 코어도 재실행 비교에서 s7_review_id를 뺀다(auto_core_decide.py 871행). 선택지 B(빈 목록이면 키를 안 냄)는 B-7·H10과 어긋나서 쓰지 않는다.
- 허용: 그 파일의 GOLDEN 5개(`default`·`sell`·`pwr`·`decide_compare`·`decide_apply`)만 Windows에서 잰 새 값(보고 4절)으로 바꾸고, 바로 위에 영문 주석 1~2줄을 단다: "hwm-fix: review_lines gained revalued_sessions and superseded_journal_reviews (empty here), so inputs.s7_review_id changed; the tickets are otherwise identical (checked by removing the two keys); docs/claude/hwm-fix-report.md". `g2b`·`cash5`·`research_block`, 단언, 다른 테스트·파일은 바꾸지 않는다. 테스트 이름·개수 그대로.
- 주의: `decide_compare`·`decide_apply`는 운영체제에 따라 값이 다르다(Linux에서는 base도 06018e98…·1bc23866…로 실패). 그래서 Windows에서 잰 값을 쓰고, 고친 뒤 Windows에서 이 파일이 통과하는지 확인한다.
- 바뀐 파일은 이제 8개: portfolio_exposure.py, run_portfolio_exposure_review.py, 새 테스트 2개, test_portfolio_exposure_fail_closed.py, test_portfolio_exposure_judge_fixes.py, test_auto_core_risk1r.py, 보고서.
- 할 일: 고친 뒤 `-p "test_auto_core*.py"`와 전체 스위트(test-runner)를 다시 돌려 보고서를 갱신한다 — front matter status, 3절 결과, 4절 "해소(선택지 A)", 5절 `--session 2026-10-12`의 evaluated_through 차이(10-05 → 10-06)는 ①의 직접 결과로 허용, 6절에 test_auto_core_risk1r.py 새 sha256 추가. 커밋하지 않는다.
