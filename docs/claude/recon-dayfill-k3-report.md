---
id: recon-dayfill-k3-report
title: "계좌 대조 — 키움 주간거래 체결 인정 — Builder 보고"
date: 2026-11-20
class: "K3 수동 경로 Builder(worktree). Judge 전. 병합은 사장 본인 터미널 -ApproveAuthority"
source: "docs/claude/recon-dayfill-k3-proposal-2026-11-20.md(3판 — T3 주문 시각 10:00:01, 착수 승인 2026-11-20 11:12:57 KST) · docs/claude/recon-dayfill-k3-builder-prompt.md"
status: "완료(3판 T3 반영) — Judge 대기"
---

# recon-dayfill-k3 Builder 보고

## 0. 결론
구현 요구 1~5, 사전 등록 시험 T1~T12 전부(T3b 포함 12개 + T10 보강 1개 = 새 시험 13개), 기존 파일 4개 단언 변경을 끝냈다. 기준선 대비 새 실패 0. Judge로 넘길 수 있다.

**3판 반영(2026-11-20)**: 2판 T3(주문 10:00:00)은 주문 시각 창의 열린 아래 끝(11/01 20:00:00 ET)과 같아 2절과 동시에 만족할 수 없어 BLOCKED였다. 사장 3판 승인(11:12:57 KST, 주문 시각만 10:00:01, 기대값 그대로)에 따라 T3을 그대로 더했다. 코드(auto_core_reconcile.py)는 바꾸지 않았다. BLOCKED.md는 이 브랜치에 커밋된 적 없음. 3판 커밋은 keen-mestorf worktree(다른 세션 소유라 쓰기 막힘) 대신 clever-mayer worktree의 브랜치 `worktree-recon-dayfill-k3-t3`(7eb9b2b 위 1커밋, fast-forward 가능)에 있다.

## 1. 바뀐 줄
| 파일:행(이후 기준) | 내용 |
|---|---|
| scripts/auto_core_reconcile.py:94~97 | 주석: 체결 창 (D−1 20:00, D 20:00] ET, D 04:00 ET 전 = DAY_SESSION, 관측 2026-11-19 SOXL |
| scripts/auto_core_reconcile.py:274~279 | parse_fills 독스트링을 새 규칙으로 |
| scripts/auto_core_reconcile.py:320~322 | 요구 1: 체결 창 아래 끝 `datetime.combine(order_day - timedelta(days=1), US_DAY_CLOSE, tzinfo=ET)`, `low_open=True`, 위 끝 그대로 |
| scripts/auto_core_reconcile.py:330~332 | 요구 2: `day_session = moment < D 04:00 ET`; 허용 ET 날짜 DAY_SESSION {D−1, D}, 그 밖 {D}; 아니면 `FILL_SESSION_DATE_MISMATCH` |
| scripts/auto_core_reconcile.py:338~339 | 요구 3: DAY_SESSION일 때만 `item["segment"] = "DAY_SESSION"`(정규·시간외 dict는 키 7개 그대로 — T10) |
| scripts/auto_core_reconcile.py:553~556 | 요구 2-1: fill_settlement 독스트링 기준일 문장 |
| scripts/auto_core_reconcile.py:569~570 | 요구 2-1: `first_day = min(max(last_fill_day, session_date + 1일))` |
| references/broker-snapshot-reconciliation.md:244~253 | 요구 4: ord_dt·체결 창·DAY_SESSION·ust21610 묶임 문장 |
| tests/test_auto_core_reconcile_orddt.py | 4절 4개 단언 + 독스트링·주석(아래 3절) |
| tests/test_auto_core_reconcile_dayfill.py(새) | T1~T12(T3b 포함) |

손대지 않음(요구 5 확인): `_kst_moment`, 주문 시각 창, FILL_TIME_INVALID·FILL_AFTER_SNAPSHOT, fill_sessions, `_assign`·`_bundle_failures`, carried·D0, plan_reads·FILL_WINDOW_MAXIMUM_DAYS, OPEN_ORDERS, unverified_outflow·ledger_days, I1·I4·I5, 권한 값. 새 키움 호출·쓰기 경로 없음.

## 2. 시험
명령(모두 `PYTHONDONTWRITEBYTECODE=1`):
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_reconcile*.py"` — 기준선 56개 OK → 2판 68개 OK → 3판(T3 추가) 69개 OK.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` — 기준선 631개 실패 1·skip 1 → 2판 643개 → 3판 644개 실패 1·skip 1. 실패는 둘 다 같은 기존 실패 `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='SOXL')`(실제 등록부 해시, 이 변경과 무관). **새 실패 0.**
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` — errors [].
- 지시문의 `pytest` 전체 실행은 하지 않았다(코디네이터 지시의 unittest 두 묶음으로 대신).
- 변경 감지 확인: 새 시험을 바꾸기 전 코드(HEAD의 auto_core_reconcile.py)에 돌리면 13개 중 11개 실패(T3도 옛 코드에서 실패 확인, T2·T10은 '안 바뀜' 확인이라 통과) — T11·T12가 first_day 변경을, 나머지가 체결 창 변경을 잡는다.

새 시험(test_auto_core_reconcile_dayfill.py):
| 수정안 | 시험 이름 |
|---|---|
| T1 | DayFillWindowTests.test_t1_observed_nov19_soxl_day_session_fill |
| T2 | DayFillWindowTests.test_t2_est_upper_end_is_the_after_hours_close |
| T3 | DayFillWindowTests.test_t3_est_one_second_after_the_lower_end (3판: 주문·체결 10:00:01 KST 11/02 → 2026-11-02T10:00:01+09:00, DAY_SESSION, 오류 없음) |
| T3b | DayFillWindowTests.test_t3b_est_day_session_fill_after_et_midnight |
| T4 | DayFillWindowTests.test_t4_edt_one_second_after_the_lower_end |
| T5 | DayFillWindowTests.test_t5_day_session_order_after_fill_holds |
| T6 | DayFillWindowTests.test_t6_day_session_fill_later_than_the_snapshot_holds |
| T7 | Nov20ReplayTests.test_t7_quantity_and_cash_pass |
| T8 | Nov20ReplayTests.test_t8_day_session_fill_without_its_day_trade_row_holds |
| T9 | Nov20ReplayTests.test_t9_after_the_rev44_record_the_reread_row_is_not_counted |
| T10 | DayFillWindowTests.test_t10_regular_and_after_hours_fills_keep_their_exact_item (+ 기존 시험 전부 통과) |
| T11 | SettlementBaseDayTests.test_t11_day_session_only_skips_the_earlier_sessions_d_plus_1_slot |
| T12 | SettlementBaseDayTests.test_t12_regular_fill_before_kst_midnight_skips_the_s_plus_1_slot |

시험 입력 중 관측값은 11/19 SOXL 행(주문 11:34:06·체결 12:44:27·74주·51.00), ust21610 3774.00, d2 11/23 3771.28, rev 44 as_of 2026-11-19T23:38:07Z. rev 43 기록 시각·현금 기준값은 합성(TEST_ONLY).

## 3. 기존 단언 변경 4개 (test_auto_core_reconcile_orddt.py, 수정안 4절 목록과 같음)
1. `test_kiwoom_day_session_fill_holds` → `test_kiwoom_day_session_fill_counts_on_its_order_day`: 12:00 KST 10/21 = 10/20 23:00 ET → DAY_SESSION 체결 1건(이전: FILL_TIME_OUTSIDE_US_SESSION).
2. `late`(ord_dt 20261102, 10:29/10:30): KST 11/02 10:30 = 11/01 20:30 ET → DAY_SESSION 체결 1건.
3. `early`(17:59:00/17:59:59): KST 11/02 17:59:59 = 11/02 03:59:59 ET → DAY_SESSION 체결 1건.
4. EDT(ord_dt 20261021, 08:00/09:30): 체결은 창 안(10/20 20:30 ET)이지만 주문 08:00 KST 10/21 = 10/20 19:00 ET가 주문 창 밖 → `FILL_TIME_INVALID:20261021:0`.
이유: 넓힌 체결 창(수정안 1-1)의 직접 결과. 그 밖 단언 변경·삭제·skip 없음. 독스트링(1~6행)·주석(94·107행 근처)만 새 규칙으로 고침.

## 4. 수정안 9절 미해결 (그대로 옮김)
① ust21610 base_dt D가 주간거래 체결을 담는지 — 첫 주간거래 뒤 실행이 T8형 HOLD면 관측으로 확정하고 후속 수정안
② 키움 주간거래 정확한 시간(창이 D−1 20:00~D 04:00 ET 전체를 받으므로 결과 영향 없음, 가정과 다르면 FILL_AFTER_SNAPSHOT로 HOLD)
③ 주간거래 매수 정산 슬롯(미관측, 어긋나면 SETTLEMENT_* HOLD)
④ 11/21(토) 06:15의 d1 슬롯 주말 규칙.

## 5. 남은 위험
- 참조 문서 같은 파일 276~277행("slots and rows dated on or before the first counted fill's KST day")은 지시문 범위(241~250행) 밖이라 고치지 않았다 — 새 기준일(max(마지막 KST 체결일, 세션+1일))과 문구가 어긋난다. 병합 뒤 문서 변경으로 맞추기 권함.
- T12처럼 정규 세션 체결이 KST 자정 전(겨울 23:30~24:00 KST 대)인 경우 기준일이 하루 늦어진다(의도된 변경). 그 세션의 정산이 KST S+1에 오는 일이 있으면 그 금액은 기준 전 몫으로 빠져 CASH_CHANGE_NOT_EXPLAINED로 HOLD(fail-closed, 잘못 기록되지는 않음).
- `segment` 키가 reconcile.json `fills` 목록에 새로 나타날 수 있다. auto-core 스키마는 fills 항목을 검사하지 않음(schemas/auto-core-*.json에 filled_at_kst 없음 확인), auto_core.py는 fills 항목을 읽지 않음(Grep 확인).
- 수정안 9절 별건(auto_core_tickets.py ord_dt=KST 가정)은 범위 밖, 손대지 않음.
