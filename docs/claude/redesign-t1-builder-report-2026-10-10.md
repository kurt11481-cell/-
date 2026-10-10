---
id: redesign-t1-builder-report-2026-10-10
title: 재설계 T1 Builder 보고 — 자동 운영 코어 v1 (수집 · 자동 대조 · 노출)
date: 2026-10-10
class: 권한·한도 변경(옛 K3) — 독립 Judge 필요
prompt: docs/claude/redesign-t1-auto-core-builder-prompt-2026-10-10.md (2~5절)
worktree: .claude/worktrees/auto-core-t1 · 기준 HEAD 74ad71e · 커밋하지 않음
authority: order_authority=false · quantity_authority=none · execution_quantity=null (바꾸지 않음)
consumers: T1 Judge 지시문(Cowork) · 관제판 redesign-t1 · 06:40 통합 점검 로더(LATEST.json) · T2 Builder
---

# 0. 맨 위 요약

- **BLOCKED 아님.** F1~F8 모두 구현. **F6 실행함**(정책 변경 불필요 — 아래 0단계 a).
- 실제 키움 호출 0회, kiwoomcli 실행 0회, 작업 등록 0회. 상태·원장·일지·정책 파일 쓰기 0회. 테스트는 모두 가짜 데이터·임시 폴더.
- 대상 테스트 통과, 전체 스위트 기준선 대비 새 실패 0(2절), 테스트 수 감소 0, 허용 경로 밖 변경 0, 스키마 감사 PASS.

## 0단계 사실 확인 (읽기만)

### a. 키움 승인(acceptance) 고정이 지금 막는 것
- **런타임에서 막는 코드는 없다.** 활성 acceptance 해시(정책 `kiwoom-session-aware-priority-policy.json`의 `835d4f46…`, 10/07 재고정)를 검사하는 곳은 다음뿐이다.
  - `validate_kiwoom_session_aware_acceptance.py:16 validate_acceptance` — 호출처는 `materialize_kiwoom_session_aware_acceptance_candidate.py:171`(재고정 도구)와 테스트뿐.
  - `validate_kiwoom_session_aware_acceptance_candidate.py`(후보 검증, `allowed_drift_for`·`predecessor_implementation_drift`) — 재고정 도구와 테스트뿐.
  - `validate_source_capabilities.py:50` — `acceptance_artifact_sha256`가 64자 문자열인지만 본다(해시 일치 검사 아님).
- 막지 않는 곳(코드 확인): `scheduled_input_gate.py`(배포 provenance 해시 체계, acceptance와 무관), `manual_data_guards.py`, `run_manual_portfolio_analysis.py` preflight, `reconcile_broker_state.py` propose/show/apply, `apply_user_confirmed_broker_snapshot.py`. 2026-09-29 진단(`kiwoom-acceptance-pin-diagnosis-2026-09-29.md` 1절)과 같은 결론.
- 실제로 막던 것: ① 테스트(`test_v2_6_7_session_aware_kiwoom_priority` 14건, `test_materialize_kiwoom_session_aware_acceptance_candidate`) ② 절차 규칙(CLAUDE.md "고정 파일 수정 → 활성 acceptance 무효 → K3 재고정"). 고정 범위 27경로는 `assets/kiwoom-acceptance-pin-scope.json`.
- 따라서 F6은 `workspace/policies/*` 변경 없이 허용 경로 안에서 끝났다.

### b. 체결 조회의 날짜 뜻 (명세 `runtime/Kiwoom-REST-API/kiwoom/_data/kiwoom_api_spec.json` 직접 확인 + 저장소 관측)
| API | 날짜 칸 | 뜻(근거) |
|---|---|---|
| ust21510 당일 주문체결 확인(기존 `account_fills_read`) | 없음 | "당일"의 기준(KST/미국)은 **확인 필요**. 기존 propose 표시용 그대로 둠 |
| ust21150 일별 주문체결내역 | `ord_dt`(주문일자, 미입력=오늘), `query_tp`·`slby_tp` 필수 | 관측: `ord_dt=20261007` 조회에 KST 10/8 05:00:03(종가 경매)·07:07:59(애프터마켓) 체결이 나옴(OI-20261008-MVLL-1). → **주문일 기준**, `cntr_time`은 KST 시각으로 해석. 체결 시각 < 주문 시각이면 다음 KST 날로 계산(코드 `parse_fills`). KST 자정 뒤에 낸 주문의 `ord_dt`가 KST인지 미국 날짜인지는 **확인 필요** |
| ust21610 당일매매 | `base_dt`, `qry_tp`(0 당일매수에대한당일매도 / 1 당일매도전체), `fc_krw_tp` | 관측 1건: `base_dt=20261009`에 미국 10/9 세션 SOXL 22주 매도(KST 10/10 05:00 체결)가 나옴 → **미국 세션 날짜**. 행에 매수·매도 수량·금액·`cmsn_altx`(수수료제세금)가 따로 있음. `qry_tp=1`이 **매수만 있는 종목**도 돌려주는지는 **확인 필요** |
| ust21100 거래내역 | `strt_dt`·`end_dt`(YYYYMMDD), `tp` | `deal_dt` = **한국 처리·결제 반영일**(NBIL 8/12 체결 → 8/14 행, s7-u3 측정). 매매 행은 결제 뒤에 나옴(10/10 아침 SOXL 매도 행 없음). `proc_time`은 KST 처리 시각. 행 없음 = return_code 20 + 501724 |

### c. 잔고 ust21070 필드
- 명세: `qty` 결제기준수량, `poss_qty` 보유수량, `sell_alowq` 매도가능수량, `pred_cntr_sellq`/`pred_cntr_buyq` 전일 매도/매수 수량, `tdy_cntr_sellq`/`tdy_cntr_buyq` 금일 매도/매수 수량, `frgn_stk_book_uv` 매입단가.
- 매도: 체결 직후 `poss_qty`가 바로 줄어든다(10/10 SOXL `qty − poss_qty = 22 = pred_cntr_sellq = 당일매매 매도 22주`, fx1009-fx4-record 4-1).
- **매수 체결 직후 `poss_qty`가 바로 늘어나는지: 확인 필요**(저장소에 매수 쪽 관측 없음). 매수 체결 직후 출금가능액(`fc_pymn_alowa`)이 바로 줄어드는지도 **확인 필요** — 줄지 않으면 F1 규칙("주문 가능 < 출금 가능 − $1이면 막음")에 따라 매수 다음 날 대조가 HOLD된다(4절 위험 1).

### d. 노출 점검 보류 `hwm_line_or_pause_state_missing_or_corrupt`의 원인 (고치지 않음)
- 손상이 아니다. 최신 결과(`exposure-review/2026-10-09/…T235239Z.json`)의 사유는 `LINE_EVALUATION_ON_HOLD`(선 판정 `HELD`).
- `portfolio_exposure.evaluate_review_lines`가 평가 세션 2026-10-09를 보류 구간 안으로 본다. 보류가 두 겹이다.
  1. 입출금 증거 사슬(`cash_flow_chain`): rev 21·22·23 원장 줄에 `cash_flow_declaration`이 없어 `CASH_FLOW_EVIDENCE_MISSING`(그리고 `CASH_FLOW_COVERAGE_GAP`) → 2026-10-07부터 보류. rev 24는 증거가 있지만 앞 구간의 공백을 메우지 못했다(covered_through 2026-10-07).
  2. 매도 대금 보류(`sale_pending_holds`): rev 24가 보유 감소(SOXL 75→53)를 기록했고, 그보다 늦은 as_of의 대조가 아직 없다 → `SALE_PROCEEDS_PENDING_CASH_CONFIRMATION`.
- 해소 경로: 다음 대조(사람 경로 또는 apply 모드 코어)가 증거 구간을 이어서 완전 신고하고(F3 자동), as_of가 늦은 기록이 생기면 풀린다. 코어는 증거를 자동으로 붙이므로 같은 원인이 다시 생기지 않는다.

### e. 테스트 기준선 (변경 전, 이 worktree, HEAD 74ad71e)
- `Ran 2493 tests` · `FAILED (failures=20, errors=9, skipped=2)` → 실패 id 29개(원본 출력에서 `FAIL:` 20줄, `ERROR:` 9줄을 직접 셈).
- 10/09 기준선 문서(27개)에 없던 2개는 이 HEAD에서 이미 실패: `test_reconcile_broker_state.RepositoryRuleTests.test_agent_rules_require_snapshot_and_user_confirmation`(74ad71e에서 CLAUDE.md 문구가 바뀜), `test_evaluate_timing_integration…test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch`(추적되는 상태 파일 SOXL 53 vs 정책 앵커 75, 데이터 의존).

# 1. 무엇을 바꿨나 (F1~F8)

| F | 내용 | 파일 |
|---|---|---|
| F1 | 현금 = `fc_ord_alowa`(basis `KIWOOM_ORDER_AVAILABLE_USD`). 검사 하나: 주문가능 − 출금가능 > $1이면 같은 조회에 `qty > poss_qty` 행이 있어야 함(`CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS`), 주문가능 < 출금가능 − $1이면 막음(`CASH_ORDER_AVAILABLE_BELOW_WITHDRAWABLE`). `fc_entra` 비교 없음. 제안에 `cash_components{deposit, withdrawable, order_available, unsettled_component}`(해시 대상). 수동 대조(`compare_broker_and_system`)도 같은 검사 통과 때만 주문가능액 사용. 스냅샷 `settled_available_cash`(min)는 뜻 그대로 → 대시보드 매수 자금 상한 코드 무변경. 예상 매도대금 칸은 상수 0 그대로 | `kiwoom_broker_shadow.py`, `manual_data_guards.py`, `kiwoom-reconciliation-proposal.schema.json`, locale 1줄 |
| F2 | 읽기 전용 조회 3개 추가: `account_transaction_history_read`(ust21100), `account_daily_fills_read`(ust21150), `account_day_trades_read`(ust21610). 요청 인자는 `YYYYMMDD` 날짜 칸만(`DATED_PARAMETERS`), 나머지 body는 고정 템플릿. 결과에 부모가 검증한 날짜를 `request_params`로 되돌려 붙임. 계좌 라벨(`acnt_print`) 미수집. ust21100 "자료 없음"(501724) 정확 문구만 plan B 표에 추가 | `kiwoom_account_readonly_bridge.py` |
| F3 | 거래내역 증거 자동: 기간 = 원장 마지막 증거 `period_to`(그날을 다시 덮음, 아래 판단 2) 또는 활성화일 → 실행일(KST). 정규화본만 `workspace/private_inputs/cash_flow_evidence/auto-core-*.json`(collection `AUTO_CORE_BRIDGE_READ`, pagination `VERIFIED_BY_BRIDGE`). 외부 순유입을 자동으로 전액 신고(`DECLARED_IN_FULL`/`NO_EXTERNAL_FLOW`). 정규화 실패·UNCLASSIFIED → HOLD | `auto_core_reconcile.py`, `cash_flow_evidence.py`, `kiwoom-cash-flow-evidence.schema.json` |
| F4 | `reconcile_broker_state.py auto` + I1~I5 판정(아래 표) → `workspace/outputs/auto-core/<날짜>/reconcile.json`. compare = 쓰기 없음, would_apply 기록. apply = I1~I5·증거·kill_switch·커밋 SHA·guarded 파일 clean일 때만 `apply_auto_core`로 기록(백업 → 원장 → 원자 교체, 기존 사슬 그대로). 원장 줄 `confirmation_method=AUTO_CORE_INVARIANTS`, `confirm_code=null`, `user_message=null`, `auto_core{invariants, commit_sha, dirty_paths}`. 사람 코드 경로(propose/show/apply)·`CONFIRMATION_METHODS`·CLI 선택지 무변경 | `auto_core_reconcile.py`(새), `reconcile_broker_state.py`, `apply_user_confirmed_broker_snapshot.py` |
| F5 | `auto_core.py daily`, `collect_30m.ps1`(추적 사본, 출력은 기존 pages 폴더, 원본 유지), `run_auto_core.ps1`(ASCII, cmd /c 리디렉션), `register_auto_core_task.ps1`(Interactive·Limited, 화~토 06:15, `InvestmentV2-AutoCore`, 만들기만 함) | 새 파일 4 + 스키마 2 |
| F6 | 고정 해시 요구 은퇴: pin scope `status: RETIRED`(파일 유지). 모든 실행에 `commit_sha`·`dirty_paths` 기록, apply 모드에서 guarded 파일(옛 고정 27경로 + 코어 자체 파일 6) 미커밋 수정이면 **읽기 전에 FAIL**. 옛 후보 도구가 자기모순 없게 `allowed_drift_predecessor_sha256` = 활성 835d4f46, `allowed_predecessor_drift` = T1이 고친 고정 파일 10개(새 acceptance는 만들지 않음) | `kiwoom-acceptance-pin-scope.json`, `kiwoom-acceptance-pin-scope.schema.json`, `auto_core_reconcile.py` |
| F7 | 정책 제안 파일(직접 쓰지 않음): `auto_core.json` 새 내용 그대로 + `.gitignore` 한 줄(허용 경로 밖) | `docs/claude/redesign-t1-policy-proposals.json` |
| F8 | auto 경로·I1~I5·비교 모드 문서. 현금 정의 문단 교체 | `references/broker-snapshot-reconciliation.md` 5절, `references/portfolio-exposure-review.md`, `references/kiwoom-mcp-local-integration.md` 1문단 |

### 불변 조건 (코드: `auto_core_reconcile.py`)
| | 규칙 | 실패 코드 예 |
|---|---|---|
| I1 | 잔고·예수금·예수금 상세·미체결·체결(ust21510)·일별 주문체결(창의 모든 날짜)·당일매매(체결 있는 세션)·거래내역 모두 return_code 0(미체결·거래내역의 측정된 "자료 없음"만 0건 인정) | `REQUIRED_READ_NOT_PASS:<조회>:<상태>:<코드>` |
| I2 | 종목별 `poss_qty` = 기록 수량 + 마지막 기록 이후 체결(매수 − 매도). 새 종목·사라진 종목 포함 | `QUANTITY_CHANGE_NOT_EXPLAINED_BY_FILLS:<종목>`, `FILL_SIDE_UNKNOWN` 등 |
| I3 | 주문가능액 = 기록 현금 + 체결 대금(ust21610 매도 − 매수 − 수수료, 수량이 ust21150과 같아야 함) + 분류된 거래내역(입출금·배당·세금·수수료·환전), $1 이내. 미체결 주문이 있으면 HOLD(주문가능액을 묶으므로) | `CASH_CHANGE_NOT_EXPLAINED:<차이>`, `FILL_SOURCES_DISAGREE`, `OPEN_ORDERS_PRESENT` |
| I4 | 상태 해시·revision = 원장 마지막 줄, 원장 사슬 정상 | `STATE_CHANGED_OUTSIDE_LEDGER`, `LEDGER_INTEGRITY_FAILED` |
| I5 | 보유·평단·원가·현금·브로커 기록 외 필드 불변(미리보기 + `_assert_untouched`), 쓰기 직전 상태 재해시(코어 + 라이브러리 두 번) | `NEVER_TOUCHED_FIELD_CHANGED:<필드>` |

- 체결 추정 코드 없음: 수량은 ust21150 `cntr_qty`, 금액·수수료는 ust21610만. 가격·종가로 수량을 만드는 경로 없음. 평단은 `frgn_stk_book_uv`.
- 주문 경로 없음: 새 조회 3개 모두 `/api/us/acnt` 조회. 코어 파일에 주문 API·명령 문자열 없음(테스트로 고정). kiwoomcli 호출은 `overseas candles stock-minute` 하나뿐, `--profile <정책 별칭> --mode real`.

### Builder 판단 (Judge 확인 요청)
1. **실행 순서**: 지시문 F5는 ②수집(30분봉 포함) → ③F4 순서다. 구현은 ②계좌 조회·거래내역 → ③F4 → ②'30분봉·이력 → ④노출. 이유: 제안 유효시간 15분(apply 라이브러리가 실시간 시계로 만료 검사)이고, 처음 보는 종목의 30분봉 첫 수집은 수 분 걸린다. 30분봉 실패가 그날 대조를 막지 않게 하는 효과도 있다(첫 실패에서 멈추는 규칙은 그대로).
2. **증거 기간 시작**: 지시문은 "period_to 다음 날부터". 구현은 "period_to 당일부터"(하루 겹침). 이유: 실행일 오후에 처리된 행(예: 입금)이 다음 기간에서 영원히 빠지는 구멍을 막는다. 겹친 행은 `build_declaration`의 기존 중복 제거(`previously_counted_keys`)로 두 번 세지 않는다. 사슬 판정(`cash_flow_chain`)의 연속 조건(시작 ≤ 덮인 날 + 1)도 만족.
3. **I1의 "자료 없음"**: 지시문은 미체결만 0건 인정을 명시. ust21100 501724는 이미 승인된 의미(S7 U3: 행 0개 증거)라 bridge plan B 표에 정확 문구로 추가하고 I1에서 0건으로 인정했다. ust21150·ust21610은 문구가 측정되지 않아 추가하지 않았다(4절 위험 2).
4. **경고 처리**: 제안 경고 `POST_APPLY_ALERT_ENGINE_CHECK_FAILED`·`POLICY_POSITIONS_MISMATCH`·`TIMING_PLAN_TICKER_CHANGED`는 I1~I5에 없어 apply를 막지 않고 결과에 남긴다(사람 경로도 경고를 보고 확인할 수 있었음). 막아야 한다면 한 줄 변경.
5. **제안의 `auto_apply` 칸**: 스키마 const false라 auto 경로 제안도 false다. 자동 기록 표시는 원장 줄 `auto_core`·`confirmation_method`와 상태 기록 `VERIFIED_AUTO_CORE_INVARIANTS_BROKER_SNAPSHOT`이 한다.
6. **수정한 고정(lock) 테스트 3개**(뜻을 정확히 새 값으로 다시 잠금, 약화 아님): `test_reconcile…test_account_routes_are_read_only`(조회 API 6→9개 정확 집합), `test_s1b_plan_b…test_production_tables_are_locked`(ust21100 501724 1건 추가), `test_materialize…PinScopeAllowanceTest`(허용 drift = 835d + T1 파일 10개 정확 목록; 테스트 이름 `test_21_allowance_is_exactly_the_t1_change_for_835d`로 변경, 개수 동일).
7. **픽스처 4곳**(뜻 유지): 현금 정의 변경으로 "주문가능 ≠ 출금가능 + 매도 없음"이 이제 막히므로, 다른 것을 시험하던 픽스처의 주문가능액을 출금가능액과 같게 맞춤 — `test_reconcile_broker_state.py` 기본 예수금(1200→1000.50, 기대값 1000.5 그대로)·2곳(20→10, 기대값 10.0 그대로), `test_cash_flow_evidence.py` 1곳. `test_kiwoom_broker_shadow.py` 헬퍼는 날짜 조회에 날짜 인자를 붙이도록 넓힘(새 조회 3개도 같은 보안 검사를 받음).

# 2. 바꾼 파일 · 테스트 · 스키마

### 파일 (허용 경로 대조: 모두 `manage-us-stock-strategy/{scripts,schemas,tests,references,assets}/` 또는 `docs/claude/redesign-t1-*`)
- 수정 19: scripts 6(`apply_user_confirmed_broker_snapshot.py`, `cash_flow_evidence.py`, `kiwoom_account_readonly_bridge.py`, `kiwoom_broker_shadow.py`, `manual_data_guards.py`, `reconcile_broker_state.py`), schemas 3(`kiwoom-acceptance-pin-scope`, `kiwoom-cash-flow-evidence`, `kiwoom-reconciliation-proposal`), assets 2(`kiwoom-acceptance-pin-scope.json`, `locales/reconcile-broker-state-ko-KR.json`), references 3, tests 5(`test_cash_flow_evidence`, `test_kiwoom_broker_shadow`, `test_materialize_kiwoom_session_aware_acceptance_candidate`, `test_reconcile_broker_state`, `test_s1b_plan_b_no_data_pass`). `git diff --stat`: 597+/49−.
- 새 10: `scripts/auto_core.py`(367줄), `scripts/auto_core_reconcile.py`(811), `scripts/collect_30m.ps1`(67), `scripts/run_auto_core.ps1`(67), `scripts/register_auto_core_task.ps1`(91), `schemas/auto-core-config.schema.json`, `schemas/auto-core-result.schema.json`, `tests/test_auto_core.py`(901, 54건), `docs/claude/redesign-t1-policy-proposals.json`, 이 보고서.
- 줄바꿈: 수정한 추적 파일은 모두 작업 트리 CRLF 그대로(줄 수 = CRLF 수 확인), 인덱스 LF. 일괄 변환 없음. `scripts/*.py` 전부 ASCII(기존 테스트 `test_v25_ui_07_core_python_ascii`), ps1 3개 ASCII.
- 허용 경로 밖 변경 0. `workspace/policies/*`, `stock-strategy-system/*`, CLAUDE.md, `.gitignore`, `.claude/` 무변경.

### 테스트
- 대상(26개 모듈, 1,125건): 새 실패 없음. 남은 실패는 모두 기준선 id(`test_reconcile…test_agent_rules…`, `test_portfolio_decision_dashboard…grade_b…`, `test_portfolio_decision_order_intent…lmt…`, `test_materialize…test_05`·`test_12`, `test_v2_6_7…` 14건).
- `tests/test_auto_core.py` 54건 통과: F1(체결 직후 PASS · 대금만 있고 수량 반영 없음 BLOCK · ord < pymn BLOCK · $1 경계 · fc_entra 비교 없음 · 수동 대조 MATCH/UNKNOWN · 예상 매도대금 0 · 대시보드 상한 무변경), F2(날짜 인자 검증 · 조회 전용 · request_params), F3(기간 시작 · 입금/출금 자동 전액 신고 · 배당 분류 · UNCLASSIFIED HOLD · CLI 증거 형식 무변경), F4(매도·매수·신규 종목·전량 매도 설명 · 기록 전 체결 이중 계산 없음 · I1~I5 각각 실패 → 쓰기 없음 · compare 상태 무변경 · apply 원장 줄 형식·사슬·백업·CRLF · kill_switch 읽기 전 정지 · 설정 없음 = compare만 · guarded 파일 미커밋 → apply FAIL · 같은 날 두 번 = 한 번만 기록), 라이브러리 거부(불변 조건 하나라도 FAIL · 커밋 SHA 없음 · compare 모드 · 외부 변경), 사람 코드 경로 회귀 없음(AUTO 방식 거부 · 코드 불일치 거부 · 정상 적용), F5(result/LATEST · 스키마 · 첫 실패 정지 · kill_switch · streak 0→3 · 같은 날 재실행 같은 streak · 설명 안 되는 날 reset), F6(git 상태 파싱 · RETIRED · guarded 집합), F7(제안 = 스키마), 주문 명령 경로 없음 · ps1 ASCII · kiwoomcli 명령 1종.
- 전체 스위트: `Ran 2547 tests` · `FAILED (failures=20, errors=9, skipped=2)` → 실패 id 29개 = 기준선 29개와 **같은 집합**. 새 실패 0, 고쳐진 것 0, 테스트 수 +54(감소 0). 아래 "전체 실행 결과".

### 스키마 감사
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → `{"status": "PASS", "errors": []}`.

# 3. 사람이 할 일 (각 한 줄)
1. 병합(Judge PASS 뒤, Cowork가 명령 1줄 제공): worktree `auto-core-t1` 변경을 커밋·병합.
2. 정책 제안 적용(Cowork, 사용자 "적용"): `docs/claude/redesign-t1-policy-proposals.json`의 `workspace/policies/auto_core.json`(compare) 생성 + `.gitignore`에 `workspace/outputs/auto-core/` 한 줄.
3. 작업 등록(사용자 PowerShell 1번): `powershell -ExecutionPolicy Bypass -File manage-us-stock-strategy\scripts\register_auto_core_task.ps1`

# 4. 남는 위험과 확인 필요
1. **매수 다음 날 HOLD 가능(0단계 c)**: 매수 체결 직후 출금가능액이 바로 줄지 않으면 "주문가능 < 출금가능 − $1" 규칙(F1 지시대로)이 그날 대조를 막는다. compare 3거래일 동안 매수가 있으면 결과로 확인된다.
2. **ust21150·ust21610 "자료 없음" 문구 미측정**: 주문이 없는 날 ust21150이 return_code 0 + 빈 목록이 아니라 20을 돌려주면 I1이 매일 HOLD된다(사유에 `…account_daily_fills_read:<날짜>:KIWOOM_API_RESPONSE_ERROR:20`이 남는다). 그때는 Cowork가 그 문구를 한 번 조회해 plan B 표에 정확 문구 1줄을 더하는 작은 변경이 필요하다(권한·한도 변경 아님이지만 조회 판정 변경이므로 Judge).
3. **첫 비교일 I3 불일치 예상**: 지금 상태(rev 24)의 현금은 옛 정의(min = 출금가능액, SOXL 매도대금 $3,072.50 제외)다. 병합 뒤 첫 실행은 `CASH_CHANGE_NOT_EXPLAINED`로 HOLD되고, 사람 경로(propose/apply)로 새 정의 현금이 한 번 기록되면 풀린다. streak는 그 다음 날부터 센다.
4. **ust21610 `qry_tp=1`(당일매도전체)이 매수만 있는 종목을 돌려주는지 확인 필요**: 안 돌려주면 매수 날 I3가 `FILL_AMOUNT_UNAVAILABLE`로 HOLD.
5. **ust21150 주문일·체결 시각 해석(0단계 b)**: KST 자정 뒤 주문·주간거래 체결은 해석이 틀릴 수 있다. 틀리면 I2/I3 불일치로 HOLD(쓰기 없음, fail-closed).
6. 배당 행의 `fc_exct_amt`가 세후 금액인지 확인 필요(세전이면 배당 날 I3 차이 → HOLD).
7. 30분봉 라벨 기준은 2026-11-02(겨울 시간) 뒤 미검증 → 그 뒤 노출 점검은 기존대로 fail-closed. 분할 점검(usa06012 수정주가)은 T1에 없고 수동 그대로.
8. 처음 보는 관심 종목(MU·BE·DELL·PWR·LITE) 첫 수집은 2026-04-01부터 7일 간격 약 28회씩 → 첫 실행이 길다(작업 제한 60분). HTTP 429면 FAIL → 다음 날 이어서 받음(받은 파일은 재사용).
9. Claude Code 세션이 `reconcile_broker_state.py auto`나 `auto_core.py daily`를 실행하지 못하게 `.claude/settings.json` deny 추가를 권장(apply 모드에서는 상태를 쓴다; 허용 경로 밖이라 Builder는 손대지 않음). 지금 deny는 `… apply`만 막는다.
10. 기준선 실패 `test_agent_rules_require_snapshot_and_user_confirmation`은 CLAUDE.md 새 문구와 옛 기대 문자열의 차이다. 기대 문구를 정하는 것은 사용자·Cowork 몫이라 고치지 않았다.
11. 통합 점검 규칙 파일(82KB)은 여전히 매수 가능 현금 설명에 `fc_entra`를 언급한다(규칙 파일 해시 고정, T1 범위 밖). T2/T4에서 정리.
12. 옛 제안 파일(병합 전 propose 결과)은 새 제안 스키마(`cash_components` 필수, basis 변경)를 통과하지 못해 apply가 거부한다. 제안은 15분 만료라 실제 영향은 없다.

# 전체 실행 결과
- 명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` (worktree 루트, test-runner 서브에이전트 실행, 원본 출력 파일에서 직접 비교)
- 변경 전(HEAD 74ad71e, 작업 트리 clean): `Ran 2493 tests in 294.998s` · `FAILED (failures=20, errors=9, skipped=2)`
- 변경 후: `Ran 2547 tests in 250.709s` · `FAILED (failures=20, errors=9, skipped=2)`
- `FAIL:`/`ERROR:` 줄 집합 비교(스크립트로 차집합): 새 실패 0, 사라진 실패 0. 29개 모두 0단계 e의 기준선 id(입력 파일 없음 9, acceptance manifest 바인딩 14, 기타 환경·데이터 의존 6).

# r2 (2026-10-10) — 실측 결함 3건 수정 (docs/claude/redesign-t1-builder-r2-2026-10-10.md)

## r2-0 요약
- R2-1·R2-2·R2-3 모두 구현. 같은 worktree, 커밋하지 않음. 키움 실제 호출 0회(M1~M8 실측값을 픽스처로 씀), 상태·원장·일지·정책 쓰기 0회.
- 허용 경로 밖 변경 0, **새 경로 0**(변경 파일 집합 = T1과 같은 수정 19 + 새 파일 11). r2가 고친 고정 파일 2개(`apply_user_confirmed_broker_snapshot.py`, `kiwoom_account_readonly_bridge.py`)는 T1 허용 drift 목록 안 → `test_21_allowance…` 통과. `reconcile_broker_state.py`는 손댔다가 되돌려 r2 순변경 없음.
- 전체 스위트: `Ran 2564 tests` · `FAILED (failures=20, errors=9, skipped=2)` → 실패 id 29개 = 기준선 29개와 **같은 집합**(새 실패 0, 사라진 실패 0). 테스트 수 2547 → 2564(+17, 감소 0). 스키마 감사 PASS.
- 보고 4절 위험 2·3·4·6 해소(아래 r2-2).

## r2-1 바꾼 함수
| 파일 | 함수·상수 | 바뀐 것 |
|---|---|---|
| `scripts/auto_core_reconcile.py` | `fill_cash` 삭제 → `fill_sessions` | ust21610은 (세션, 종목)을 ust21150 수량과 묶는 데(`FILL_SOURCES_DISAGREE`)와 총액(`tdy_buy_amt`·`tdy_sell_amt`)에만 쓴다. `cmsn_altx`는 읽지 않는다 |
| 〃 | `settlement_slots` (새) | 예수금 상세(ust21160)의 `dN_setl_dt`·`dN_usd_sell_excta`·`dN_usd_buy_excta`(N=1~4) → 결제일별 미결제 금액. 읽을 수 없는 금액은 그 칸을 쓸 때만 `SETTLEMENT_SLOT_AMOUNT_INVALID` |
| 〃 | `settlement_rows` (새) | 거래내역(ust21100) 매매 행 → 결제일(`deal_dt`)·종목·방향(적요 매도/매수)·수량(`deal_qty`)·정산 금액(`fc_exct_amt`, 실제 수수료 포함) |
| 〃 | `fill_settlement` (새), `_bundle_failures`, `_partitions` | R2-1 본체(r2-4 판단 1·2). 결과 `I3.settlements[]`(결제일·PENDING/SETTLED·세션·정산액·총액) |
| 〃 | `baseline_snapshot`, `_find_proposal` (새) | R2-2 본체(r2-4 판단 4·5) |
| 〃 | `explain_change` | `cash_baseline` 인자(기준 현금·시각·출처). I3 결과 칸: `baseline`(출처·스냅샷 경로·해시·주문가능액·generated_at), `baseline_cash_usd`(옛 `recorded_cash_usd` 대체), `fills_counted`, `settlements` |
| 〃 | `run_auto` | 스냅샷을 create-once 사본 `kiwoom_broker_snapshot.<hash16>.shadow.json`으로도 쓰고, 제안 `source.snapshot_path`가 그 사본을 가리킨다(일반 파일도 계속 씀). 비교(streak) 검사의 기준 현금은 전날 would_apply 현금(= 전날 브로커 주문가능액) 그대로 |
| `scripts/apply_user_confirmed_broker_snapshot.py` | `apply_auto_core` | I3에 `baseline`(status OK, 경로·해시)이 없으면 거부 `AUTO_CORE_BASELINE_SNAPSHOT_REQUIRED`. 원장 줄 `auto_core`에 `baseline_snapshot{path, snapshot_hash}`(I3 기준)과 `snapshot{path, snapshot_hash}`(이 기록의 스냅샷 = 다음 실행의 기준) 추가 |
| `scripts/kiwoom_account_readonly_bridge.py` | `NO_DATA_PASS_MESSAGE_CODES`·`NO_DATA_PASS_MESSAGES` | `account_daily_fills_read` 571758 `[2000](571758:해당 계좌의 체결내역이 없습니다.)`, `account_day_trades_read` 571758 `[2000](571758:조회내역이 없습니다.)` (ASCII 이스케이프, 측정 문구와 일치 확인) |
| 〃 | `SAFE_FIELDS["account_deposit_detail_read"]` | `d3_setl_dt`·`d3_usd_buy_excta`·`d3_usd_sell_excta`·`d4_…` 6칸 추가(r2-4 판단 3) |
| `references/broker-snapshot-reconciliation.md` | 5절 | I1·I3 표, I3 기준·정산 금액 문단 2개, 원장 줄 설명 |

## r2-2 M1~M8 대응
| # | 대응 | 확인 테스트 (`tests/test_auto_core.py`, 따로 적지 않으면) |
|---|---|---|
| M1 | `cmsn_altx` 미사용. 기록 뒤 매도(정산 전)는 d2 `sell_excta` 3072.51로 설명 → 차이 −0.01 PASS. 옛 방식이면 5.53 HOLD | `SettlementAmountTests.test_sale_after_the_record_is_explained_by_the_pending_settlement_not_the_fee_estimate` |
| M2 | 기록 뒤 매수가 결제까지 끝나면 거래내역 `fc_exct_amt` 3227.25로 설명(총액 3225.00과 차이 2.25, 범위 안) | `…test_buy_after_the_record_settled_before_the_run_is_explained_by_the_trade_row` |
| M3 | `qry_tp=1` 그대로(본문 템플릿 무변경). 매수만 있는 종목도 묶인다 → 보고 4절 위험 4 해소 | 매수 픽스처 2건(M2, 기록 전 칸 제외 테스트) |
| M4 | ust21610 자료 없음 → 0건 PASS(plan B 표) | `test_s1b_plan_b_no_data_pass.DatedReadDeclarationTests` 2건, 고정 테스트 재잠금 |
| M5 | ust21150 자료 없음 → 0건 PASS. 미체결 문구(띄어쓰기 없음)·다른 조회 문구·코드 한 자리 차이는 계속 오류 → 위험 2 해소 | 위와 같음(`test_other_messages_stay_errors`) |
| M6 | `cntr_qty` 0 행은 시각을 읽기 전에 건너뛴다(코드 변경 없음, 고정 테스트 추가) → 체결 0, I2·I3 체결 0건 | `NoDataAndInvalidOrderTests.test_m6_invalid_order_row_is_zero_fills` |
| M7 | `fc_exct_amt` = 세후 순액 → `flow_cash` 그대로(코드 변경 없음) → 위험 6 해소 | 기존 배당 테스트 |
| M8 | I3 기준 = rev 24 스냅샷(주문가능 12467.71, generated_at 23:52:05Z). 상태 현금 9395.21(옛 정의)이어도 첫날 PASS → 위험 3 해소(사람 apply 1회 불필요) | `BaselineSnapshotTests.test_old_state_cash_definition_is_explained_from_the_first_day`, `SettlementAmountTests.test_m1_settlement_row_of_a_fill_before_the_record_is_not_a_cash_change` |

## r2-3 픽스처
- r2 지시 4개: ① M1 그대로(기록 뒤 체결 0, SOXL 결제 행만 나타남 → 현금 변화 0) `test_m1_settlement_row…` ② 기록 뒤 매도 체결(정산 전, d2 excta) `test_sale_after…` ③ 기록 뒤 매수 체결 결제 완료(ust21100 fc_exct_amt) `test_buy_after…` ④ 추정 수수료 행 차이 5.5에도 PASS — ②에서 옛 계산 차이 5.5302를 함께 고정.
- 추가: 기록 전 체결의 미결제 칸 제외(`test_pending_slot_of_a_fill_before_the_record_is_not_counted`: 10/13 SOXL 칸은 빼고 10/14 NBIS 칸만 셈) · 세션→결제일 순서 매칭(`test_sessions_are_matched_to_settlement_dates_in_order`) · d3/d4 칸과 읽을 수 없는 금액(`test_later_settlement_slots_and_unreadable_amounts`) · HOLD 3종(수수료 범위 밖 `SETTLEMENT_OUTSIDE_FEE_RANGE`, 정산 금액 없음 `SETTLEMENT_AMOUNT_NOT_FOUND`, 결제 행 수량 불일치 `SETTLEMENT_QUANTITY_MISMATCH`; 모두 apply 모드에서 쓰기 0) · 기준 모름 4종(스냅샷 없음·제안 없음·스냅샷 변조·주문가능액 없음 → `BASELINE_ORDER_AVAILABLE_UNKNOWN:<이유>`; 상태 현금 = 브로커 현금이어도 HOLD) · apply 원장 줄의 두 스냅샷 + 같은 날 재실행 뒤에도 사본 유지 + 다음 실행이 `AUTO_CORE_LEDGER_ENTRY` 기준 사용 · 라이브러리의 기준 참조 요구.
- 기존 픽스처 변경(뜻 유지): `Workspace`가 기록 스냅샷·제안·원장 줄(`proposal_id`)·상태 `evidence_sha256`을 함께 만들고, 제안 검색 경로를 임시 폴더로 바꾼다. 매도·매수 픽스처 5곳에 결제일 d1 정산 칸 추가(현금 기대값 그대로). 연속 일치 테스트는 실행일을 KST 10/14·10/16·10/17·10/18로 바꿈(10/15 결제 뒤 거래내역 행이 있는 현실 순서) — 여전히 streak 0·1·2·3과 같은 날 재실행 값 검증.
- 변형 검사(테스트가 실제로 잡는지 임시 패치로 확인): 수수료 범위 0 → 2건 실패, 기준 모름일 때 상태 현금으로 대체 → 4건(subTest) 실패, 기준 = 상태 현금 → 2건 실패, 매매 행을 현금 변화로 셈(이중 계산) → 1건 실패. 모두 잡혔다.

## r2-4 Builder 판단 (Judge 확인 요청)
1. **결제일별 매칭(R2-1 마지막 줄 해석)**: 정산 금액은 결제일 단위로만 알 수 있으므로, 기준 뒤 체결을 세션 순서대로 결제일에 연속 배정한다. 어느 한 배정에서 모든 날짜·양쪽(매도·매수)이 수수료 범위 안이고, 결제된 날짜는 매매 행 수량까지 정확히 같아야 PASS다. 현금 합계는 배정과 무관하다(대상 칸·행의 합). 배정 후보가 하나뿐이면 구체 사유(`SETTLEMENT_OUTSIDE_FEE_RANGE:<날짜>:<방향>:<차이>` 등), 여럿이면 `SETTLEMENT_NOT_MATCHED_TO_FILLS:<날짜들>`.
2. **날짜 규칙 "결제일 > 체결 KST 날짜"**: 체결은 언제나 다음 날 이후에 결제된다(M1·M2·U3 관측). 그래서 첫 체결의 KST 날짜 이하로 찍힌 칸·행은 기준 전 체결의 것으로 보고 세지 않는다(그 현금은 이미 기준에 있고, 결제는 주문가능액을 바꾸지 않는다). 긴 연휴로 기준 전·후 체결이 같은 결제일에 묶이면 수수료 범위·현금 검사가 HOLD(쓰기 없음).
3. **d3·d4 칸 수집**: r2는 "결제일별 dN"을 쓰라고 했고 명세에 d1~d4가 있다. 연휴에 결제가 d3로 밀리면 d1·d2만으로는 계속 HOLD라 6칸을 조회 허용 필드에 더했다(읽기 전용, 권한 무변경). 스냅샷 스키마는 그대로(d1·d2만 담음), 코어는 조회 결과에서 직접 읽는다.
4. **기준 시각**: I3 = 기준 스냅샷 `generated_at`(지시대로). I2는 기존대로 상태 `as_of_timestamp`(r2 범위 밖이라 유지; 차이 약 1초, 그 사이 체결은 HOLD 쪽으로만 틀린다).
5. **create-once 스냅샷 사본**: 같은 날 두 번 돌면 `kiwoom_broker_snapshot.shadow.json`이 덮여 다음 날 기준을 잃는다(해시 불일치 → 계속 HOLD). 그래서 제안·원장 줄은 해시 이름의 사본을 가리킨다. 사람 경로 제안은 실행마다 폴더가 달라 그대로 찾는다.
6. **수수료 범위**: r2 그대로 `|정산 − 총액| ≤ 총액 × 0.5% + 0.50`(절대값, 방향 검사 없음).

## r2-5 남는 위험과 확인 필요
1. **D0(오늘 결제분)에는 금액 칸이 없다(명세)**. 06:15 실행 때, 그날 08:07경 처리될 결제는 칸에도 거래내역에도 없다. 평소(기준 = 전날 실행)에는 기준 뒤 체결이 내일 이후 결제라 영향이 없다. 기준이 이틀 이상 묵으면(비교 모드는 상태를 안 써서 기록 기준이 고정됨, 또는 HOLD가 이어진 뒤) 그 체결의 결제 당일에 I3 HOLD 1회 → 다음 날 거래내역 행이 생겨 풀린다. 비교 모드 중 체결이 있으면 그날 streak가 0이 되어 "기록 모드 켤 준비됨"이 늦어질 수 있다. `d0_setl_dt`가 오늘 날짜인지, 결제 전 금액이 어디에 보이는지는 **확인 필요**(장 마감 뒤 06:15 무렵 예수금 상세 1회 조회로 확인 가능).
2. dN 칸이 한국 영업일 기준이라는 것은 M1 1건(d1 10/12, d2 10/13)으로 본 추정이다. 틀리면 HOLD 쪽으로만 틀린다.
3. 거래내역 매매 행은 같은 결제일·종목·방향끼리 합산해 비교한다(행이 주문 단위인지 체결 단위인지 몰라도 된다). 매수 쪽 실측은 M2 1건.
4. 보고 4절 위험 1(매수 직후 출금가능액이 안 줄면 F1 검사 HOLD)·5·7~12는 r2 범위 밖이라 그대로.

## r2-6 테스트·감사
- 대상: `test_auto_core` 69건 OK(54 → 69), `test_s1b_plan_b_no_data_pass` 30건 OK(28 → 30), `test_kiwoom_broker_shadow` 24·`test_cash_flow_evidence` 19·`test_cash_flow_evidence_u3` 18·`test_k2_bridge_evidence_integrity` 18·`test_k2_evidence_contract` 34·`test_kiwoom_token_reuse` 15·`test_state_write_boundary` 3·`test_run_portfolio_exposure_review` 24·`test_manual_portfolio_analysis` 115·`test_v2_5_broker_snapshot` 27·`test_v2_6_4_kiwoom_adapter` 44·`test_v2_6_broker_beginner` 25·`test_broker_visibility_audit` 3·`test_s1b_provider_marks` 20 OK. 나머지 실패는 기준선 id뿐(`test_reconcile…test_agent_rules…`, `test_materialize…test_05`·`test_12`, `test_v2_6_7…` 14).
- 전체: test-runner 서브에이전트(Haiku)로 실행. 원본 출력 파일에서 `FAIL:` 20줄·`ERROR:` 9줄을 직접 세고, 기준선 목록(`test-baseline-2026-10-09.md` 27개 + 0단계 e의 2개)과 스크립트로 차집합 → 새 실패 0, 사라진 실패 0.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → PASS. `scripts/*.py` 전부 ASCII. 수정한 추적 파일 줄바꿈 그대로(CRLF), 새 파일도 원래 줄바꿈 그대로.
- 소비처: T1 Judge 지시문(Cowork) · 관제판 redesign-t1 · T2 Builder.

# r3 (2026-10-10) — Judge 조건 C1~C6 + 후속 2건 (docs/claude/redesign-t1-builder-r3-2026-10-10.md)

## r3-0 요약
- C1~C6·T1B-1·T1B-2 모두 반영. BLOCKED 아님. 같은 worktree, 커밋하지 않음.
- 키움 실제 호출 0회, kiwoomcli 실행 0회, `auto_core.py`·`reconcile_broker_state.py auto/apply` 실행 0회, 작업 등록 0회. 상태·원장·일지·정책 쓰기 0회(테스트는 가짜 데이터·임시 폴더).
- 변경 경로 = T1·r2와 같은 집합(수정 19 + 새 11) + `.claude/settings.json`(deny 4줄, r3 예외). 새 경로 0, 허용 경로 밖 변경 0.
- 전체 스위트: `Ran 2584 tests` · `FAILED (failures=19, errors=9, skipped=2)` → 실패 id 28개 = 기준선 29개 − `test_agent_rules…`(새 실패 0, 기준선에서 사라진 것은 그 1건뿐). 테스트 수 2564 → 2584(+20, 감소 0). 스키마 감사 PASS.

## r3-1 바꾼 곳 · 테스트 이름
테스트는 따로 적지 않으면 `tests/test_auto_core.py`.

| 조건 | 바꾼 곳 | 테스트 |
|---|---|---|
| C1 쓰기 직전 재확인 | `apply_user_confirmed_broker_snapshot.py`: `_auto_core_write_recheck`(새), `apply_auto_core`(인자 `config_path`·`provenance_source`, 기본값 = 정책 파일·git). 원장·해시 검사 뒤 `_write_applied` 바로 앞에서 ① `auto_core.json` 다시 읽기(없음·무효 `AUTO_CORE_RECHECK_CONFIG_UNAVAILABLE:<이유>`, `…_KILL_SWITCH_ON`, `…_MODE_NOT_APPLY`) ② provenance 다시 계산(C2 기준 `…_GUARDED_FILES_UNCOMMITTED:<경로>`, `…_GIT_PROVENANCE_UNAVAILABLE`, 실행 기록과 커밋이 다르면 `…_COMMIT_CHANGED` — 판단 1) ③ 제안 `cash_flow_declaration` 없음 `…_CASH_FLOW_DECLARATION_MISSING`, status ∉ {NO_EXTERNAL_FLOW, DECLARED_IN_FULL} `…_CASH_FLOW_NOT_DECLARED_IN_FULL:<status>`. 거부 = ValueError → 그날 FAIL, 백업·원장·상태·감사 파일 0. `auto_core.daily` → `reconcile_auto` → `run_auto` → `apply_auto_core`로 `config_path`·`provenance_source`를 넘김 | `WriteRecheckTests`: `test_configuration_is_read_again`(3 subTest), `test_provenance_is_computed_again`(3), `test_declaration_must_be_present_and_declared_in_full`(2), `test_everything_still_right_writes`, `test_kill_switch_or_code_change_during_the_run_writes_nothing`(조회 중 정지 스위치·코드 변경 → FAIL, 쓰기 0) |
| C2 guard 확장 | `auto_core_reconcile.py`: `GUARDED_PREFIXES`(새, `manage-us-stock-strategy/{scripts,schemas,assets}/`), `git_provenance`: 추적 파일(porcelain 코드 ≠ `??`: 수정·스테이지·삭제·이름변경, 이름변경은 두 이름 모두) 중 그 아래 경로 + 기존 guarded 목록(옛 고정 27 + 코어 6; 목록의 boundary test 3개도 그대로 guard). `apply_guard_reasons`는 그대로 읽기 전 FAIL. `assets/kiwoom-acceptance-pin-scope.json` `retirement_note` 1문장 갱신 | `ProvenanceAndConfigTests.test_apply_guard_covers_every_tracked_file_under_scripts_schemas_and_assets`, `ModeTests.test_apply_guard_covers_files_outside_the_former_pin_list`(Judge가 든 5개 파일 각각 → 읽기 전 FAIL, 조회 0) |
| C3 경고 싣기 | `auto_core_reconcile.proposal_warnings`(새) → `reconcile.json` `warnings[]`(`PROPOSAL_WARNING:<code>`, `POST_APPLY_CHECK_ERROR:<text>`), `auto_core.daily` → `result.json`·`LATEST.json` `warnings[]`; 멈춘 결과(`_auto_stop`)도 `warnings: []`. `schemas/auto-core-result.schema.json`: `warnings` 필수. 상태·기록·status에 영향 없음 | `DailyTests.test_warnings_reach_result_and_latest_without_blocking_the_record`(apply 모드: 경고 3종 + 오류 1줄, `applied` ≠ null, 세 파일 같은 목록, 스키마) |
| C4 (a) 전날 PENDING | `auto_core_reconcile.carried_settlements`(새): 직전 실행 `reconcile.json` `invariants.I3.settlements` 중 결제일 = 오늘(KST)·source `PENDING` → `fill_settlement(today, carried)`가 오늘 날짜를 `PENDING_PREVIOUS_RUN`(`carried_from` = 그 실행 `generated_at`)으로 채우고 보통 검사(수수료 범위·$1). 매칭은 `_assign`·`_settlement_detail`로 분리(뜻 무변경). `run_auto(previous_run=…)`, `reconcile_auto`·`cmd_auto`·`daily`가 `previous_reconcile` 결과를 넘김 | `SettlementDueTodayTests.test_previous_runs_pending_amount_explains_todays_settlement`(apply 모드 기록 + 원장 줄 I3에 출처), `…test_a_carried_amount_that_does_not_match_holds_as_usual`, `…test_only_a_pending_entry_of_today_is_carried`, `DailyTests.test_settlement_day_counts_with_the_previous_runs_pending_amount`(10/14·10/15(D0)·10/16·10/17 → streak 0·1·2·3, "기록 모드 켤 준비됨") |
| C4 (b) D0만이면 유지 | 전날 기록이 없으면 오늘 날짜를 열어 두고(`D0_NOT_SHOWN`) 다른 날짜가 모두 맞을 때만 I3 사유 `SETTLEMENT_D0_NOT_SHOWN:<날짜>` 하나. `explain_change`가 잔차(= 오늘 정산액)를 그날 세션 총액의 수수료 범위(+$1)로 확인, 벗어나면 `SETTLEMENT_D0_OUTSIDE_FEE_RANGE` 추가(→ D0만 아님). `auto_core_reconcile.d0_only`(새). `auto_core.compare_streak`: 사유가 D0뿐이고 비교 검사도 맞거나 D0뿐이면 streak 유지(`basis` `KEPT_D0_SETTLEMENT_NOT_SHOWN`, `kept_reasons`). `reconcile_broker_state.compare_reference`(새): 비교 기준 = D0만으로 보류된 날을 건너뛴 직전 실행(다음 날 `NO_PREVIOUS_WOULD_APPLY` 리셋 방지). 스키마 `compare.basis`·`kept_reasons` 추가. 그날은 언제나 HOLD(쓰기 0) | `SettlementDueTodayTests.test_without_an_earlier_read_only_todays_settlement_is_left_open`(apply 모드 쓰기 0, 잔차 벗어남 → D0만 아님), `DailyTests.test_day_held_only_for_an_unseen_settlement_keeps_the_streak`(애프터마켓 체결: streak 0·1·**1(유지)**·2) |
| C4 80% 한 줄 | `run_auto` 결과 `fill_window{days, maximum_days}`, `auto_core_reconcile.baseline_stale`(새, `STALE_WINDOW_SHARE` 0.8), `auto_core._finish`: compare 모드에서 days > 11.2(= 12일 이상) 또는 `FILL_WINDOW_TOO_LONG`이면 `next_action_for_user` = "기록 모드 켜기 필요(기준 오래됨)". FAIL로 만들지 않음. 한도 초과는 지금처럼 FAIL·쓰기 0 | `DailyTests.test_old_record_in_compare_mode_asks_for_recording_instead_of_failing`(11일 없음 · 12일 OK + 한 줄 · 15일 FAIL + 한 줄 + 쓰기 0), `…test_old_record_line_is_for_compare_mode_only` |
| C5 FAIL 날 | `auto_core._finish`: status FAIL(어느 단계든, 결과 스키마 오류 포함)이면 `compare` = {streak 0, `last_mismatch` `RUN_FAILED`} — 판단 2 | `DailyTests.test_a_failed_step_never_counts_toward_the_streak`(대조 OK 뒤 30분봉·노출 각각 FAIL → 0, 다음 정상일 1) |
| C6 프로필 필수 | `auto_core.kiwoom_profile`(새): 정책 `token_profile_alias` 없음·빈·공백 → 계좌 조회 전에 FAIL `KIWOOM_PROFILE_ALIAS_MISSING`(정지 스위치가 켜져 있으면 지금처럼 HOLD가 먼저). 30분봉 수집에 같은 값. `scripts/collect_30m.ps1`: `-KiwoomProfile` `Mandatory` + `ValidateNotNullOrEmpty` + 공백 검사, `--profile … --mode real` 항상(빈 값 분기 삭제). PowerShell 파서로 매개변수 속성 확인(스크립트 실행 안 함) | `DailyTests.test_missing_profile_alias_fails_before_any_read`(빈·공백·없음 → 조회 0·수집 0·노출 0, 정상 별칭이 수집에 전달), `NoOrderPathTests.test_collection_requires_the_profile_alias` |
| T1B-1 | `.claude/settings.json` `permissions.deny`에 지시한 4줄(기존 `reconcile_broker_state.py apply` 2줄 바로 뒤). diff +4/−0, CRLF·들여쓰기 그대로 | `NoOrderPathTests.test_claude_code_sessions_cannot_run_the_auto_core` |
| T1B-2 | `tests/test_reconcile_broker_state.py` `test_agent_rules_require_snapshot_and_user_confirmation`: "only from a verified read-only broker snapshot" + (`reconcile_broker_state.py apply` 또는 `auto-core … invariant`) + "Never infer (a fill / fills) from price mov…" + 옛 "or" 약화 문구 금지 유지 | 그 테스트가 이제 통과 → 기준선 29 → 28 |

- 문서: `references/broker-snapshot-reconciliation.md` 5절에 C1~C6 동작(재확인, guard 범위, D0 (a)/(b), 80% 한 줄, FAIL 리셋, 프로필 필수, `warnings[]`)을 반영.

## r3-2 추가로 고친 것 (Judge 확인 요청)
- **테스트 시계 의존 제거**: T1 테스트의 apply 경로는 라이브러리가 실시간 시계로 제안 만료(가짜 시각 2026-10-13 21:15Z + 15분)를 검사해서, 실제 시계가 **2026-10-13 21:25Z(KST 10/14 06:25)를 지나면 apply 테스트가 `BROKER_PROPOSAL_EXPIRED`로 실패**하게 되어 있었다(실제 시계를 10/20으로 바꿔 재현). `Workspace`가 apply 라이브러리의 시계만 그 실행의 시각으로 고정한다(`FrozenClock`). 라이브러리 코드(실시간 하한)는 그대로.

## r3-3 Builder 판단 (Judge 확인 요청)
1. **C1 ②에 커밋 동일 검사 추가**: 실행 중 HEAD가 바뀌면 원장 줄 `commit_sha`가 실제로 돈 코드와 다를 수 있다. 실패는 FAIL(쓰기 0)뿐.
2. **C5 "올리지 않는다" = 0으로 리셋**: T1 완료 기준 "3거래일 연속 무인 실행(종료 0 또는 사유 있는 HOLD)"과 맞추려는 것. 유지(+1만 없음)로 하면 FAIL을 사이에 둔 3일이 "준비됨"이 될 수 있다. 유지가 맞다면 `_finish` 한 줄 변경.
3. **C4 (a)는 직전 실행 하나만 본다**(지시대로). 직전 실행 뒤의 애프터마켓 체결이 같은 날 결제되면 옮겨 온 금액이 모자라 보통 HOLD(리셋)가 되고, (b)로 넘어가지 않는다. 드물고 HOLD 쪽으로만 틀린다.
4. **C4 (b) 판정은 쓰기를 열지 않는다**(그날은 언제나 HOLD). 잔차 검사는 streak 유지 여부만 가른다. 다른 결제일 묶음이 틀려 한 세션이 오늘로 돌려지는 경우 하루 유지될 수 있으나, 다음 날 결제 행이 생기면 정밀 검사가 다시 돌아 리셋된다.
5. **C4 (a)는 apply 모드에도 적용**(HOLD로 기준이 하루 이상 묵은 뒤의 결제일). 옮겨 온 금액은 브로커가 전날 보여 준 칸이고 출처가 I3·원장 줄에 남는다. 기록하는 값은 여전히 브로커 `poss_qty`·주문가능액·`frgn_stk_book_uv`.
6. **80% 한 줄**: compare 모드에서만, "기록 모드 켤 준비됨"보다 우선(둘 다 기록 모드를 켜라는 뜻이지만 기준이 오래되면 곧 FAIL). 한도를 넘어 FAIL한 날에도 같은 줄을 남긴다.
7. **C2는 지시대로 "추적 파일"만**: scripts/ 아래의 추적 안 된 새 파일은 guard 밖(`dirty_paths`에는 기록). 표준 모듈 이름을 가리는 파일까지 막으려면 `code != "??"` 조건 하나를 빼면 된다.
8. **C6 위치**: 별칭 검사는 `auto_core.daily`에 두었다(지시: auto_core). `reconcile_broker_state.py auto` 단독 실행은 브리지의 기존 검사(`kiwoom_runtime_bridge._token_profile_alias`, 빈 별칭이면 BridgeError)로 FAIL한다.

## r3-4 남는 위험·알림
1. **T1B-1 deny의 부작용**: 명령 문자열에 `auto_core.py`가 들어간 모든 Bash/PowerShell 명령이 막힌다. CLAUDE.md 형식 `-p "test_auto_core.py"`도 막히므로 Claude Code·Judge 세션은 `-p "test_auto_cor*.py"`로 돌린다(이 세션도 deny 추가 뒤 그렇게 실행). 같은 문자열을 쓰는 grep 등 읽기 명령도 막힌다(Grep 도구는 영향 없음).
2. C2 기준으로 메인 체크아웃의 scripts/schemas/assets 미커밋 변경은 지금 0이다(git status 읽기로 확인). 병합 뒤 그 아래 파일을 고쳐 두고 커밋하지 않으면 apply 모드가 그날 FAIL한다(의도대로).
3. 06:40 로더의 경고 푸시(C3)는 배포 때 Cowork가 붙인다(r3 지시).
4. r2-5 위험 1(D0 결제로 비교 기간 streak가 0이 됨)은 C4로 해소. 나머지 r2-5·4절 위험은 그대로.

## r3-5 테스트·감사
- 대상: `test_auto_core` 89건 OK(69 → 89, +20), `test_reconcile_broker_state` 56건 OK(기준선 실패 1건 해소), `test_cash_flow_evidence` 19·`test_kiwoom_broker_shadow` 24·`test_s1b_plan_b_no_data_pass` 30·`test_state_write_boundary` 3·`test_manual_data_guards` 19·`test_scheduled_input_gate` 8·`test_run_portfolio_exposure_review` 24 OK, `test_materialize_kiwoom_session_aware_acceptance_candidate` 26(기준선 E1·F3만; `test_21_allowance…` 통과 — r3가 고친 고정 파일 `apply_user_confirmed_broker_snapshot.py`·`reconcile_broker_state.py`·pin scope는 T1 허용 drift 목록 안).
- 변형 검사(임시 패치, 스크래치 스크립트): C1 재확인 제거 · C2 접두 규칙 제거 · C3 경고 제거 · C4a 옮기기 제거 · C4b 유지 제거 · C4b 기준 건너뛰기 제거 · C4 한 줄과 C5 리셋 제거 · C6 별칭 검사 제거 → 대상 테스트 11개 모두 실패(잡힘).
- 전체: test-runner 서브에이전트(Haiku)로 `python -m unittest discover … -p "test_*.py"` 실행, 원본 출력 파일에서 `FAIL:` 19줄·`ERROR:` 9줄을 스크립트로 기준선 목록(`test-baseline-2026-10-09.md` 27개 + 0단계 e의 2개)과 대조 → 새 실패 0, 기준선 중 안 보인 것 1(`test_agent_rules…`, T1B-2로 해소). `Ran 2584 tests`.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → PASS. `scripts/*.py` 전부 ASCII, ps1 ASCII. 줄바꿈: CRLF 파일은 CRLF, LF 파일은 LF 그대로(혼합 0), 일괄 변환 없음.

## r3-6 사람이 할 일
- 바뀐 것 없음: 보고 3절 그대로(병합 1줄 — 이번에는 `.claude/settings.json`도 함께 들어감 · 정책 제안 적용 · 작업 등록 1회).
