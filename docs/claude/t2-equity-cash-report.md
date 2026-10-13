---
id: t2-equity-cash-report
title: 재설계 T2 — 판정 총자산·N·V6·EV4 현금을 승인된 현금 정의로 (Builder 보고)
date: 2026-10-13
prompt: docs/claude/t2-equity-cash-builder-prompt.md
class: 권한·한도 변경(K3) 수동 경로 — Builder(이 worktree) → 별도 Judge 세션 → 사용자 병합
worktree: .claude/worktrees/t2-equity-cash (branch worktree-t2-equity-cash, base 1fe378b = codex/master-recovery-expansion HEAD)
model: Opus 5.5 · xhigh
commit: 없음(지시대로 커밋하지 않음)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 관문 기준값 불변 · 키움 호출 없음
weekly_user_touch: 0 (일회성: Judge 1·병합 1)
---

# 결과 한 줄

판정(decide)의 총자산용 현금을 **키움 주문가능(T1 가드 통과 시)**, 가드 실패·값 누락 시 **세 값 중 알려진 최솟값**으로 바꿨다. 2026-10-13 값으로 총자산 27,695.15 · N 1.2466 · V6 none · EV4 없음(기존 24,622.65 · 1.4022 · review · 열림). 대상 테스트 336개 OK(기준선 324 + 새 12), 전체 스위트 2,979개 — 실패·오류 목록이 기준선과 같음(새 실패 0).

# 1. 바꾼 파일·함수·줄 (diff 요약, `git diff --stat`: 2 files, +52 −10, 새 테스트 1)

| 파일 | 위치(변경 후 줄) | 내용 |
|---|---|---|
| scripts/auto_core_decide.py | 46 | `from kiwoom_broker_shadow import order_available_cash_errors` — T1 가드 **그대로 import**(복제 없음) |
| 〃 | 69~73 | 상수 `EQUITY_CASH_FIELDS`(세 칸 이름), 라벨 `ORDER_AVAILABLE`·`MIN_FALLBACK`·`CASH_UNAVAILABLE` |
| 〃 | 137~163 | **새 순수 함수 `equity_cash(cash, holdings) -> (Decimal\|None, basis)`** (규칙은 2절) |
| 〃 | 505~513 (`_run`) | `cash = deposit = None` → `cash = None`; fc_entra를 읽던 `deposit = ...` 줄 삭제; `total_cash, cash_basis = equity_cash(snapshot.cash, snapshot.holdings)` 추가. 판정 매수 현금 `cash`(주문가능)·G1 대조는 그대로 |
| 〃 | 631 | `evaluate_session(..., deposit=deposit)` → `deposit=total_cash` (= 856행 `rule_file_nominal`의 현금 자리 → 857행 `v6_account`·906행 `ev4_open`이 같은 total을 씀) |
| 〃 | 646 | `decision["exposure"]["cash_basis"] = cash_basis` — 표시용 칸 1개 |
| 〃 | 838~839 | `evaluate_session` docstring에 `cash`/`deposit` 뜻 2줄. **키워드 이름 `deposit`은 유지**(리플레이 `auto_core_replay.py` 252행과 기존 테스트가 이 이름으로 넘김 — 리플레이 불변 조건) |
| 〃 | 1029~1030 (`_dashboard`) | runCore.exposure를 `cash_basis`만 뺀 사본으로 → **runCore 출력 키 불변**(cash_basis는 runCore에 안 들어감). `shock` 줄은 같은 문장 안에서 한 줄로 합침(의미 동일) |
| scripts/auto_core_tickets.py | 152~167 (`rule_file_nominal`) | 인자 `deposit` → `cash`, docstring "cash = 총자산용 USD 현금(equity_cash의 선택)…", 상태 문자열 `DEPOSIT_UNAVAILABLE` → `CASH_UNAVAILABLE` |
| tests/test_auto_core_equity_cash.py | 새 파일(313줄) | T1~T6 (3절) |

- 상태 문자열 읽는 곳(grep `DEPOSIT_UNAVAILABLE`, graphify-out 제외 저장소 전체): 생산처 1곳뿐, 리터럴로 읽는 곳 없음. 일반 표시로만 쓰임: auto_core_tickets.py 230행 매수요건 (2) 칸 `"N " + status`(현금 세 값이 모두 없을 때 "N CASH_UNAVAILABLE"로 보임 — 그날은 G1도 실패해 HOLD). 남은 참조 0.
- 스키마(schemas/auto-core-decision.schema.json): `exposure`가 제한 없는 `{"type": "object"}`라 **변경 불필요, 안 바꿈**. 스키마 감사 `validate_schema_contracts.py` PASS.
- 바꾸지 않은 것(diff 없음 확인): 판정 매수 현금 `cash`(511행)·G1 상태 대조·S7(run_s7·s7_summary)·주문표 수량/가격(plan·tickets)·rules.C 기준값(V6 선·EV4 비율·N 상한 1.85·종목 상한 0.4)·auto_core_rules.py·auto_core_compare.py·auto_core_replay.py·kiwoom_broker_shadow.py·스키마·정책/상태 파일.

# 2. 선택 함수 규칙 `equity_cash(cash, holdings)`

입력: 브로커 스냅샷 `cash`의 `order_available_cash`(fc_ord_alowa)·`withdrawable_cash`(fc_pymn_alowa)·`foreign_currency_deposit`(fc_entra)과 스냅샷 `holdings` 행의 `(settled_quantity, held_quantity)`. 값은 Decimal(`core._decimal`: 숫자 아님·NaN·무한 = 없음). 가격 × 수량으로 만든 금액은 쓰지 않음.

| 순서 | 조건 | 결과 (현금, basis) |
|---|---|---|
| 1 | 세 값 모두 없음 | (None, `CASH_UNAVAILABLE`) → N·total 없음, V6 unk, EV4 아님 (기존 `DEPOSIT_UNAVAILABLE`과 같은 결과) |
| 2 | 주문가능 또는 출금가능이 없음(가드를 돌릴 수 없음) | (알려진 값의 최솟값, `MIN_FALLBACK:CASH_VALUE_MISSING:<없는 칸,…>`) |
| 3 | `order_available_cash_errors(주문가능, 출금가능, 행들)` 오류 있음 | (세 값 중 알려진 최솟값, `MIN_FALLBACK:<가드 오류 코드>`) — 가드 실패 때 주문가능을 그대로 쓰지 않음 |
| 4 | 가드 통과 | (주문가능, `ORDER_AVAILABLE`) — 예수금은 필요 없음 |

- 가드(kiwoom_broker_shadow 252행, T1 F1과 같은 함수): 주문가능 − 출금가능 < −$1 → `CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE`; > +$1인데 settled > held 행 없음 → `CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS`; 그 밖 통과(±$1 허용 그대로).
- 왜 최솟값인가: 매도 결제 전이면 예수금(정산 전 대금 빠짐)이, 매수 결제 전이면 주문가능(나갈 돈 빠짐)이 최솟값 → 어느 쪽이든 자산을 부풀리지 않음(매수 쪽으로 보수적: 총자산↓ → N↑·V6/EV4가 더 쉽게 열림 → 매수만 더 막힘, 매도는 영향 없음).
- 행은 스냅샷 원본 전체(보유 0주로 줄어든 행 포함)를 씀 — T1 가드가 같은 조회의 모든 행을 쓰는 것과 같음.

# 3. 2026-10-13 값 계산 (브로커 스냅샷 + 2026-10-12 종가, 실측 파일과 대조함)

실측 확인(읽기 전용): workspace/outputs/auto-core/2026-10-13/kiwoom_broker_snapshot.shadow.json — MVLL 159/159, NBIS 13/13, SOXL 결제 75/보유 53, 예수금 9,396.68 = 출금가능 9,396.68, 주문가능 12,469.18(계좌 식별자 저장 없음). 같은 날 decision.json: total 24,622.6487, N 1.402175, ev4_open true, s7_hwm_usd 30,255.3600.

| 항목 | 기존(fc_entra) | 변경 후(주문가능, 가드 통과) |
|---|---|---|
| 보유 평가(MVLL 159×35.806 + NBIS 13×209.98 + SOXL 53×128.3599) | 15,225.9687 | 15,225.9687 |
| 현금 | 9,396.68 | 12,469.18 (`ORDER_AVAILABLE`: 차이 3,072.50 > $1, SOXL settled 75 > held 53) |
| 총자산 | 24,622.65 | **27,695.15** |
| N = (2×5,693.154 + 1×2,729.74 + 3×6,803.0747) / 총자산 | 1.4022 | **1.2466** (통합점검 LLM 값과 같음) |
| V6 (첫 선 25,626.55 · 접근 26,395.34) | review (cushion −3.92%) | **none** (cushion +8.07%) |
| EV4 (≤ 첫 선 또는 ≤ hwm 30,255.36 × 0.9 = 27,229.82) | 열림 | **없음** |

테스트는 이 값을 결과만 비교하지 않고 함수(`equity_cash` → `rule_file_nominal` → `v6_account`·`ev4_open`)를 거쳐 계산하고, 별도로 **decide() 전체 실행**(10-13 보유·종가·현금을 넣은 픽스처)에서도 같은 값이 결정 기록에 나오는지 확인한다(`DecideOctober13Tests`).

# 4. 테스트

새 파일 `manage-us-stock-strategy/tests/test_auto_core_equity_cash.py` (12개, 기존 테스트 파일은 안 고침):

| 테스트 | 확인 |
|---|---|
| T1 `test_t1_2026_10_13_order_available_passes_the_check` | basis ORDER_AVAILABLE, 27,695.15·1.2466·V6 none·`ev4_open(total, "30255.3600")` False; 기존 값 24,622.65·1.4022·review·EV4 True |
| T1 `test_t1_through_decide` | decide() 실행 결과 `exposure.cash_basis`·`account.total`·`exposure.N`·`account.state`·`ev4_open`; 같은 픽스처를 기존 방식(fc_entra)으로 돌리면 24,622.65·1.4022·review |
| 가드 `test_the_check_is_t1s_imported_function` | `decide_module.order_available_cash_errors is kiwoom_broker_shadow.order_available_cash_errors`; 그 함수가 실패를 내면 MIN_FALLBACK:<코드>, 넘겨진 인자(주문가능·출금가능·행 쌍) 확인 |
| T2 `test_t2_sale_unsettled_without_a_settled_above_held_row_falls_to_the_deposit` | settled = held / settled 없음 / 행 없음 / None → MIN_FALLBACK:CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS, 현금 = 예수금 9,396.68 |
| T3 `test_t3_buy_unsettled_uses_order_available_without_double_count` | 매수 결제 전(주문가능 7,000 < 출금가능 10,000) → MIN_FALLBACK:CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE, 현금 7,000, 총자산 10,000(매수 전 계좌와 같음, 기존 13,000 = 이중 계산); 출금가능도 줄어든 경우 ORDER_AVAILABLE로 같은 10,000 |
| T4 `test_t4_three_values_equal_keep_the_previous_result` | 세 값 같음 → ORDER_AVAILABLE, rule_file_nominal 결과 dict 전체가 기존과 같음 + 골든(24,622.65·1.4022·review·EV4 True) |
| T4 `test_t4_check_tolerance_is_t1s` | 차이 정확히 $1.00 통과, $1.01 실패(T1 허용 그대로) |
| T5 `test_t5_missing_values_take_the_smallest_known` | 출금가능·주문가능 하나 또는 둘 없음/읽을 수 없음 → 알려진 최솟값 + 사유; 예수금만 없고 가드 통과 → ORDER_AVAILABLE |
| T5 `test_t5_no_value_leaves_n_unknown_as_before` | 세 값 없음(빈 칸·None·NaN) → (None, CASH_UNAVAILABLE), N·total None, V6 unk, EV4 False (기존과 같음) |
| T6 `test_t6_existing_fixtures_give_the_same_record` | test_auto_core_decide.Env 픽스처 4종(기본·MU 매수 주문표·SOXL 매수 주문표·apply 모드 MU 주문표)의 결정 기록 전체가 기존 방식과 같음(`exposure.cash_basis`와 apply의 `journal.decision_sha256`만 제외), N·account·dashboard(runCore) 동일, runCore에 cash_basis 없음 |
| T6 `test_t6_three_values_equal_give_the_same_record` | 세 값 같은 스냅샷 → ORDER_AVAILABLE, 기록 동일 |
| T6 `test_t6_unsettled_money_changes_only_n_and_the_account_total` | 미결제 매도 +3,000 / 미결제 매수 −3,000: N·account 총자산 칸만 바뀌고 주문표·관문·차단·트리거·매수요건·shock 등 나머지 동일 |

T6의 "기존 방식"은 테스트 안에서 `equity_cash`를 기존 fc_entra 선택(`old_deposit`, 기준 구현으로 남김)으로 바꿔 같은 픽스처를 다시 돌린 것이다. 이와 별도로 이 세션에서 **실제 변경 전 코드(편집 전)와 변경 후 코드**로 같은 픽스처 7종을 각각 돌려 결정 기록을 경로 단위로 비교했다(scratchpad, 저장소 밖):

| 픽스처 | 달라진 경로(임시 폴더 경로 `inputs.*.path` 제외) |
|---|---|
| default · mu_buy_ticket · soxl_cues · three_equal | `exposure.cash_basis` 추가뿐 |
| mu_buy_ticket_apply | `exposure.cash_basis` + `journal.decision_sha256`(기록 전체 해시라 새 칸 때문에 바뀜) |
| sale_unsettled (주문가능 30,000 · 출금가능=예수금 27,000 · SOXL 50/40) | `account.total` 31,108 → 34,108, `first_cushion_pct`, `exposure.N` 0.3962 → 0.3613, runCore의 같은 값, `cash_basis` ORDER_AVAILABLE |
| buy_unsettled (주문가능 27,000 · 출금가능=예수금 30,000 · SOXL 30/40) | `account.total` 34,108 → 31,108(이중 계산 제거), cushion, N 0.3613 → 0.3962, runCore 같은 값, `cash_basis` MIN_FALLBACK:CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE |

주문표 qty·price·gates·decision_key, blocked, 트리거 state, runCore 키 구성은 모든 픽스처에서 같았다.

## 실행 결과 (기준선 = 편집 전 같은 worktree)

| 실행 | 기준선 | 변경 후 |
|---|---|---|
| 대상 `-p "test_auto_core*.py"` | Ran 324 · OK (skipped=1) | Ran 336 · OK (skipped=1) — 새 12개, 새 실패 0 |
| 새 파일만 `-p "test_auto_core_equity_cash.py"` | — | Ran 12 · OK |
| 전체 `-p "test_*.py"` | Ran 2967 · FAILED (failures=19, errors=9, skipped=3) | Ran 2979 · FAILED (failures=19, errors=9, skipped=3) — +12개는 새 파일 |
| 스키마 감사 validate_schema_contracts.py | — | PASS |

기준선 실패·오류 28건은 모두 auto-core 밖(worktree에 없는 workspace/outputs/activation/* 산출물·market_snapshot.example.json·키움 acceptance manifest 바인딩 등)이며 편집 전부터 있던 것이다. 변경 후 목록과 기준선 목록 비교(`FAIL:`/`ERROR:` 머리줄 28개를 정렬해 diff): **동일** — 새 실패·새 오류 0, 사라진 것 0. 전체 스위트는 test-runner(Haiku)로 돌리고 결과 파일을 이 세션에서 다시 열어 diff로 확인했다. 마지막 편집(`_dashboard`의 shock 줄 합침, 의미 동일)은 전체 실행 전에 끝났고, 대상·전체 모두 최종 파일로 실행한 결과다.

기준선부터 있던 실패·오류(참고): ERROR 9 — setUpClass(test_holding_baseline_observation_audit · test_mvll_canonical_volume_lineage · test_provider_limitation_audit), test_05_materialized_candidate_passes_binding_validator, test_price_evidence_preserves_same_session_kiwoom_conflict, test_live_price_artifact_schema_and_semantics, test_valuation_uses_kiwoom_and_no_double_count, test_lmt_candidate_classification_is_verified_but_non_actionable, test_snapshot_fixture_declares_contract_version. FAIL 19 — test_v2_6_7_session_aware_kiwoom_priority 14건(acceptance manifest 바인딩 matches=[]), test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch, test_15_current_fixed_activation_is_exactly_bound, test_candidate_support_does_not_replace_active_registry, test_12_allowed_drift_is_recorded_and_validates, test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan.

# 5. 지켜야 할 것 자기 점검 (Judge 확인 항목 대응)

1. 바뀐 파일: auto_core_decide.py, auto_core_tickets.py, 새 테스트, 이 보고서뿐. 스키마 안 바꿈. `git status`: M 2개 + ?? 새 테스트(+ 보고서).
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 든 줄: diff에 0건(grep). 주문 경로 문자열 없음. 키움·auto_core.py·run_auto_core.ps1 실행 없음(테스트·덤프는 가짜 브로커 FakeReader와 임시 폴더만).
3. 가드는 import한 `order_available_cash_errors` 하나만(테스트로 동일 객체 확인). 가드 실패 시 주문가능을 그대로 쓰지 않고 최솟값. 가격 × 수량 추정 금액 없음(브로커 세 값만).
4. 스크립트·테스트 ASCII만(비ASCII grep 0건). 줄 끝은 기존 파일과 같은 LF 유지. 정책·상태 파일·workspace/policies·stock-strategy-system 쓰기 없음(읽기: 테스트가 alert_policy.json 배수 읽음, 이 세션이 10-13 스냅샷·결정 기록 읽음).
5. 커밋 없음.

파일 해시(sha256, 이 보고서 작성 시점):

| 파일 | sha256 |
|---|---|
| manage-us-stock-strategy/scripts/auto_core_decide.py | 88621ca9c0201ef732e7e10ee084492ecccbb527fb29498ec0dfbe067d611bca |
| manage-us-stock-strategy/scripts/auto_core_tickets.py | b6e8f73a7fa05960c0bd0d300b1ef6ca48f46a06c4a34cb9e71ab5bc2460e973 |
| manage-us-stock-strategy/tests/test_auto_core_equity_cash.py | a564f1d6be76ce141fadf26e842b8d0edfcdfbe2695cd46e81fd1d19409dafd0 |
| (불변) scripts/kiwoom_broker_shadow.py | 44e866feb2a55eae469c5c14846f157b2ef93629f5912ffb259a1798c610b16b |
| (불변) scripts/auto_core_replay.py | 8a872b88cf815bcd445f4df37faa3c20e049f0eff010a5d6d02cdb669de78fd2 |
| (불변) scripts/auto_core_compare.py | 4cc7cbef64b96c212d7ebf11925bcf3c4f04d6794c7b79c3ba46584ae9529357 |
| (불변) scripts/auto_core_rules.py | 8d18c6f3565334597ef1ac0cecbdcf7d67f081153a90198a6d6505451e971a80 |
| (불변) schemas/auto-core-decision.schema.json | 4fe55c3e227def1c81ba0782d98ea7ed1c1a64e1ed2cf2062fc93ae63b9341a1 |

# 6. 남은 위험

1. **열린 매수 주문 예약금**: 미체결 매수 주문이 걸린 날은 주문가능이 예약금만큼 줄어 총자산이 낮게 잡힌다(가드 통과든 실패든). 보수적 방향(N↑·V6/EV4 쉽게 열림 → 매수만 더 막힘, 매도 불변). decide 시점(07:45 KST)에 열린 주문이 남아 있으면 기존 G0_OPEN_ORDERS로 그날은 HOLD(새 주문표 없음)다. 다만 그날 기록된 `ev4_open`은 다음 실행들의 R-REC1 EV4 세션 목록에 들어가므로(decide `ev4_sessions`), 낮게 잡힌 날의 EV4는 이후 며칠 매수를 막을 수 있다(매수만, 매도 불변).
2. **규칙 파일 문구**: docs/claude/integrated-check-prompt-v3.12.2-2026-10-09.txt 56행 1-1 ②는 여전히 "USD 현금 = fc_entra(계좌에 속한 돈 전체)"라고 적혀 있다. 코드가 승인된 현금 정의로 바뀌어 문구와 다르다 — 문구 정정은 별도 ⑪(이번 범위 밖, 고치지 않음).
3. **결정 기록 해시**: 기록에 새 칸이 생겨 `decision_identity_hash`(일지 review_id)가 같은 입력에서도 변경 전과 다르다. 기록 모드(apply)에서 병합 전에 같은 날 기록된 결정이 있고 병합 뒤 같은 날 재실행하면 R2-5대로 decision.rerun 파일·HOLD가 된다. 지금은 decision_mode compare라 일지 기록이 없어 영향 없음.
4. **값 누락 시 최솟값**: 출금가능만 없으면 min(주문가능, 예수금), 예수금만 남으면 예수금 — 매도 결제 전이면 자산이 기존처럼 낮게, 매수 결제 전이면 이중 계산 없이 잡힌다. 음수 값 같은 별도 점검은 넣지 않았다(지시: 가드는 import 함수 하나). T1 대조는 음수를 따로 막는다(validate_reconciliation_inputs).
5. 리플레이(auto_core_replay)는 지시대로 안 바꿨다: 리플레이는 여전히 한 가지 현금(`deposit=cash`)으로 총자산을 만든다(지금과 같음).
6. 통합점검 대시보드 runCore: 키 구성은 그대로지만 `runCore.exposure.N`·`runCore.account.total/state/first_cushion_pct` **값**은 새 총자산으로 바뀐다(의도한 변화). graphify-out 코드 지도는 갱신하지 않음(위치 안내용).

# 7. 다음 단계 (사용자 손 0 → Judge 1·병합 1)

- Judge: 별도 세션(Opus xhigh, 읽기만)에서 이 보고서와 worktree diff로 프롬프트의 Judge 확인 항목 1~6을 본다.
- 병합 파일 목록(병합 스크립트가 확인할 목록):
  - manage-us-stock-strategy/scripts/auto_core_decide.py
  - manage-us-stock-strategy/scripts/auto_core_tickets.py
  - manage-us-stock-strategy/tests/test_auto_core_equity_cash.py
  - docs/claude/t2-equity-cash-report.md
