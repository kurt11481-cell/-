# I0-b 체결 확인 경로 — 최소 설계안 (2026-10-06, K3 설계 제안만)

- 관제판 작업: `r-i0b` ("판 기록을 알림 엔진에 알려 주는 길 만들기")
- 등급: K3 설계. 이 문서는 제안만 한다. 코드·정책·상태·원장은 바꾸지 않았고, apply·키움 도구·주문 도구는 쓰지 않았다.
- 작성: Cowork(Opus). 권장 설정: Opus · xhigh(K3 설계).
- 권한 불변: `order_authority=false`, `quantity_authority=none`, `execution_quantity=null`.
- 조사 방법(모두 읽기 전용): 상태·정책·원장·대조안 파일 읽기, `leveraged_state_integrity_errors`를 메모리에서 실행(쓰기 없음), 대상 테스트 1개 실행(현재 상태 / 사용자 폴더 밖 임시 복사본의 r18 백업 상태), git 조회.
- 근거: P3 §4-3, P4 §2·§4(S4 경고 분기)·§5, S5 제안서 부록 C.11(D5), S7 Builder 보고 §1c·§2.1·§2.2·§5.6, `mvll-investor-day-plan-2026-10-04.md` §11-1, `r-sched-b-scheduled-clone-k3-design-2026-10-06.md` §1·§5. 전체 목록은 §10.
- **소비처(이 문서를 읽는 곳)**
  - 관제판 `r-i0b`(doc·next 칸)
  - S7 2차(관제판 `p-s7-p2`) Builder 지시문: 권장안 (가)를 고르면 §4-C의 완료 기준이 S7 2차 범위로 들어간다
  - (나)·(다)를 고를 때의 Builder 지시문과 독립 Judge(§5, §7)
  - 예약 자동화 재개 판단(r-sched-b §5 보류 목록)

## 0. 결론

1. **멈췄나: "지금 돌리면 멈춘다. 다만 지금 돌리는 곳이 없다."**
   - 현재 상태(revision 19)와 현재 정책으로 알림 엔진의 무결성 검사를 돌리면 오류 1건이 나온다: `MVLL: holdings 278 do not equal anchor less confirmed tranches 396`. 이때 `evaluate()`는 원가 한도·타이밍 판정 전에 `STATE_MISMATCH`, 등급 F로 끝난다(`evaluate_alerts.py:741-747`). 대상 테스트로 재현했다(§1-3).
   - 그러나 알림 엔진을 실제로 부르는 운영 경로는 지금 없다. 예약 자동화는 PAUSED이고, 통합 점검·수동 분석·카드는 이 검사를 부르지 않는다(§1-4). 그래서 실제로 멈춘 실행은 0건이다. 지금 보이는 영향은 ① 대조 표의 상시 "적용 후 검사 실패" ② 통합 테스트 6건 실패 ③ 예약 자동화를 재개하면 F, 세 가지다.
2. **체결 기록 경로(ADD)는 만들지 않기를 권한다.**
   - 118주 매도는 기존 슬롯 형식에 사실대로 들어갈 수 없다. MVLL 슬롯은 한 칸 99주이고, 이번 매도 근거(V5 사용자 지정)는 슬롯 허용 트리거가 아니며, 99주로 적어도 396−99=297≠278이다(§1-5). 맞추려면 거짓 기록이 필요하다.
   - 체결 기록을 읽는 곳은 타이밍 슬롯뿐이고(§1-6), 이 슬롯은 2026-10-01 사용자 결정 D5로 은퇴가 정해졌다. 은퇴할 구조에 새 쓰기 경로를 붙이는 셈이다.
   - 118주 매도 이력은 이미 남아 있다: 대조 원장 줄, `holding_change_reconciliations`(`NO_FILL_RECORDED`), 대조안 폴더의 키움 체결 조회(59주 22:12:15, 59주 22:12:35).
3. **권장: (가) 지금은 NO_CHANGE, 해소는 S7 2차에 합친다. 10/8 M6 v2 결과 뒤 한 번 다시 판정한다.**
   - 근본 원인은 "정책 파일에 보유 수량(anchor)과 보유 종목 목록(등록부)이 박혀 있어, 매매할 때마다 정책과 상태가 어긋나는 구조"다. 이번 anchor 문제를 막아도 MVLL을 다 팔거나(② 119 + ③ 159 = 278) 새 종목을 사면 등록부 검사로 다시 `STATE_MISMATCH`가 된다(§1-7). 둘 다 S7 2차(옛 통제 은퇴 #1~#8, D5 슬롯 은퇴, 등록부 #12)가 다루는 범위다.
4. **S7 2차 전에 경고·테스트를 정상화하고 싶으면 (나) 정책만 바꾸는 SIMPLIFY가 가장 작다(K3).** `holding_timing_rules.positions`에서 MVLL(·SOXL) 키를 지운다. 코드·고정 27개·`deployment_gate`·상태 파일은 그대로다. 대가는 D5가 남기기로 한 gap·halt 감시가 S7 2차까지 빠지는 것(지금은 엔진이 돌지 않아 실질 손실 0)과 shadow cohort 이관 1회다(§5).
5. 사용자 결정 4개(§8). 결정 전에는 아무것도 바꾸지 않는다.

## 1. 확인한 사실 (2026-10-06 22:20~22:55 KST, 읽기 전용)

### 1-1. 상태 파일과 원장: revision 19는 확정이다

| 항목 | 값 | 근거 |
|---|---|---|
| `state_revision` | 19, `last_updated_at` 2026-10-06T13:20:28Z(22:20 KST) | `portfolio_state.json` |
| 보유 | MVLL 278, NBIS 13, SOXL 75 | 같음 |
| 마지막 확인 기록 | `KIWOOM_READONLY_API`, `HOLDINGS_AND_AVAILABLE_CASH`, `as_of` 2026-10-06, `open_orders_verified=true`, `COWORK_CHAT_USER_MESSAGE` | 같음 |
| 원장 마지막 줄 | revision 18→19, MVLL 396→278, 원가 파생, 확인 코드 263684A6, `inferred_fills=false` | `reconciliation_ledger.jsonl`(5줄) |
| 조정 기록 | `BROKER_SNAPSHOT_RECONCILED_NO_FILL_RECORDED`, `fill_recorded=false`, `trade_id=null` | `holding_change_reconciliations` 마지막 항목 |
| 백업 | `backups/portfolio_state.r18.20261006T132028453816Z.json` | 백업 폴더 |

- 시작 지시문의 "396→278주 추정, 확인 필요"는 상태·원장 기준으로 확정이다(적용 완료).

### 1-2. timing_plan(상태)과 타이밍 정책

- 상태 `timing_plan.policy_version` = 정책 `holding_timing_rules.policy_version` = `2026-08-05-ema-timing-v4`(일치). 정책 `status`는 `approved_review_only`(검사가 켜져 있음).
- MVLL: anchor `MVLL-20260731-R3-396`(396주), 완료 슬롯 없음, 체결 기록 없음.
- SOXL: anchor 99주, 완료 `SOXL-R25`(24주, 체결 기록 1건), 보유 75 = 99 − 24(일치).
- 정책 MVLL 슬롯: R25·R50·R75·FINAL-RESIDUAL 각 99주. R25 허용 트리거 = technical_stop, weakness_20ema, weakness_failed_reclaim, weakness_10ema, strength_20ema_reclaim, strength_10ema_reclaim, strength_extension. watch-only = gap_risk, halt_risk.

### 1-3. 알림 엔진은 지금 돌리면 멈춘다 (재현)

- `leveraged_state_integrity_errors(현재 상태, 현재 정책, "2026-10-06")` → `["MVLL: holdings 278 do not equal anchor less confirmed tranches 396"]`. 다른 오류는 없다.
- 이 오류가 있으면 `evaluate_leveraged_mode`는 원가 한도(hard risk)·타이밍 판정 전에 `STATE_MISMATCH`/F로 반환한다(`evaluate_alerts.py:741-747`). 엔진이 돌았다면 NBIS 등의 원가 한도 알림도 함께 나오지 않는다.
- 대조안 `workspace/outputs/reconciliation/20261006T131852Z/reconciliation_proposal.json`: `post_apply_checks.status=FAIL`(같은 오류), 경고 `TIMING_PLAN_TICKER_CHANGED`·`POST_APPLY_ALERT_ENGINE_CHECK_FAILED`, `policy_positions_mismatch=false`.
- 대상 테스트 `test_evaluate_timing_integration.py`(실제 상태·정책 파일을 읽음):
  - 현재 상태: 10건 중 실패 5 + 오류 1. 6건 모두 결과가 `STATE_MISMATCH`/F다(오류 1건은 후보 목록이 비어 `next()`가 실패).
  - 사용자 폴더 밖 임시 폴더에 r18 백업 상태와 현재 정책을 복사해 `STOCK_STRATEGY_SYSTEM_ROOT`로 지정: 10건 모두 통과.
  - 따라서 이 6건은 revision 19가 원인이다. Cowork VM(Python 3.10.12) 결과이고, Windows 재실행은 확인 필요.
  - 다음 Builder 전체 테스트의 기준선에 이 6건이 섞인다. NO_CHANGE 동안 이 모듈은 평가기 회귀를 잡지 못한다.

### 1-4. 알림 엔진을 실제로 부르는 곳

| 경로 | 알림 엔진 호출 | 지금 상태 | 근거 |
|---|---|---|---|
| Codex 예약 2개(Pre-Open·Post-Close) | 예. 오케스트레이터가 `evaluate`를 부른다(`run_portfolio_strategy_orchestrator.py:23`). 어느 예약 단계에서 부르는지는 확인 필요 | PAUSED. 마지막 `workspace/outputs/portfolio-strategy/` 결과 2026-08-13, `alert_runtime_state.json` 수정 2026-08-11 | r-sched-b §1(오늘 Cowork 확인). TOML은 이번에 직접 다시 읽지 못함(확인 필요) |
| Cowork 통합 점검 v3.11(매일) | 아니오(지시문에 `evaluate_alerts` 0건) | 운영 중 | `integrated-check-prompt-v3.11-draft-2026-10-05.txt` |
| 수동 분석(기본 `MANUAL_READ_ONLY`) | 아니오(대시보드 위임은 `LIVE_READ_ONLY`에서만, `run_manual_portfolio_analysis.py:2115-2124`) | 적용 뒤 `manual-20261006T132111850903Z-2817a6a2a07e`: `broker_diff_status=MATCH`, `preflight_status=PASS`, `GRADE_B` | 출력 JSON |
| 카드 fact pack | 일부만: `exact_loss_boundary`(원가 한도 칸 계산). 무결성 검사는 부르지 않음 | 타이밍 칸은 최근 알림 결과가 8/5자라 원래 `NOT_EVALUATED` | `build_holding_fact_pack.py:194, 253-267` |
| 대시보드 | `LIVE_READ_ONLY`(예약 입력)에서만 `evaluate`. `STATE_MISMATCH`면 타이밍 투영이 빈 값 | 예약 PAUSED라 실행 없음 | `portfolio_decision_dashboard.py:403-408` |
| 대조 `propose` | 예(적용 후 사전 검사) | **지금부터 모든 제안에 FAIL 표시.** 현금만 바뀌는 제안도 같다 | `reconcile_broker_state.py:61-80` |

- 관제판 `verify`의 "10/7 점검 결과로 확인"은 성립하지 않는다. 통합 점검은 알림 엔진을 부르지 않는다. §1-3의 재현이 그 확인을 대신한다.
- 활성 Cowork 예약 13개가 알림 엔진을 쓰지 않는다는 것은 r-sched-b §5 기준이다(이번에 직접 확인한 것은 통합 점검 하나).

### 1-5. 118주 매도는 기존 체결 형식에 사실대로 들어가지 않는다

`timing_anchor_errors`(`timing_engine.py:31-108`)가 요구하는 것과 이번 매도의 비교:

| 요구 | 이번 매도 | 맞나 |
|---|---|---|
| 완료 슬롯은 정책 슬롯의 앞부분(R25부터) | R25로 적을 수는 있음 | 형식만 |
| 체결 수량 = 슬롯 수량 99 | 118 | 아니오 |
| 트리거 ∈ R25 허용 트리거 | V5(사용자가 인정한 다른 근거. 행사 전 1회 지정을 행사 뒤로 넓혀 적용) | 아니오 |
| 보유 = anchor − 완료 슬롯 수량 합 | 278 ≠ 396 − 99 = 297 | 아니오 |

- 기존 형식을 통과시키려면 수량·트리거를 바꿔 적어야 한다. 이는 거짓 체결 기록이고 "체결 추론 금지"와 Evidence 원칙에 어긋난다.

### 1-6. 체결 기록을 읽는 곳

- `confirmed_trades`: `scripts/` 안에서 읽는 코드가 없다(대조 쪽 `NEVER_TOUCHED_FIELDS` 목록에만 이름이 있음).
- `timing_plan.positions.*.confirmed_tranche_fills`: `timing_engine.py`만 읽는다(anchor 검사, 재무장 근거).
- 즉 체결 기록의 소비처는 타이밍 슬롯 하나다.

### 1-7. 이미 정해진 결정과 다음 트리거

- **D5(2026-10-01, 사용자 원문 "은퇴")**: SOXL·MVLL 축소 슬롯 은퇴, gap·halt 감시 표시는 유지(S5 제안서 부록 C.11). 적용은 S7 2차(관제판 `p-s7-p2`, waiting, 재개 조건 "새 통제가 실제 자료로 판정되는 것 확인").
- S7 Builder 조사(§1c): 은퇴 종목은 "anchor·슬롯 검사를 건너뛰고, 슬롯 없이 gap·halt만 평가하고, 상태의 timing_plan은 읽지 않는" 엔진 수정으로 **상태 쓰기 없이** 처리할 수 있다. 상태의 옛 계획은 읽히지 않는 이력으로 남는다.
- **다음 트리거(등록부):** MVLL 남은 278주 = ② 119 + ③ 159(`mvll-investor-day-plan-2026-10-04.md` §11-1). 둘 다 체결되면 MVLL이 0주가 되어 `holding_risk_rules.positions` 검사(`evaluate_alerts.py:511-516, 532-535`)에서 다시 `STATE_MISMATCH`가 되고, 대조 표에 `POLICY_POSITIONS_MISMATCH`가 뜬다. 관심 종목을 새로 사도 같다(`:504-509`).
  - 이것은 타이밍 슬롯과 별개 문제이고, P3 §4-3 I0-b의 "정책 종목 갱신" 절반이다. ③은 10/8 M6 v2에서 정한다.

### 1-8. 바꾸면 어디까지 번지나 (고정·해시)

| 파일 | 묶임 | 고치면 |
|---|---|---|
| `reconcile_broker_state.py`, `kiwoom_broker_shadow.py`, `apply_user_confirmed_broker_snapshot.py`, `schemas/kiwoom-reconciliation-proposal.schema.json` | 키움 acceptance 고정 27개(`assets/kiwoom-acceptance-pin-scope.json`) | 활성 acceptance 무효 → K3 + 재수용(R7·R9급 작업) |
| `timing_engine.py`, `evaluate_alerts.py` | 고정 27개 밖. `alert_policy.json` `deployment_gate`의 정규화 해시(현재 일치: `DAC71EA7…`, `66B52485…`)와 설치 Codex 스킬 동기화 | 정책의 `deployment_gate` 갱신 + 설치 스킬 동기화 |
| `alert_policy.json` `holding_timing_rules` | `shadow_acceptance.py` 의미 지문(`:223-229`), `rules_hash`(이벤트 중복 억제), 예약 clone 배포 manifest(원시 바이트) | cohort 이관(현재 `integrated-shadow-4f11526e…`, 카운터 모두 0), 중복 억제 1회 초기화(무해), manifest는 재개 때 어차피 재생성 |
| `assets/locales/reconcile-broker-state-ko-KR.json`, `references/broker-snapshot-reconciliation.md` | 고정 아님 | K0 |

- VM의 git으로 보면 `alert_policy.json`·`evaluate_alerts.py`가 수정됨으로 나오지만 `--ignore-cr-at-eol` 차이는 0이다(줄바꿈만). Windows git(autocrlf)에서의 상태는 확인 필요.

## 2. 문제를 다시 정의한다

- P3 §4-3의 I0-b는 "체결 확인 경로(확정 tranche 기록)와 정책 종목 갱신"이었다. 전제는 "슬롯 계획이 살아 있고, 매매가 슬롯대로 일어난다"였다.
- 지금은 두 전제가 모두 깨졌다. 슬롯은 D5로 은퇴가 정해졌고, 실제 매매(V5 118주, 앞으로 ② 119·③ 159)는 슬롯 수량·트리거와 무관하게 카드·M6 근거로 일어난다.
- 그래서 목표를 이렇게 바꾸기를 제안한다.

  > **매매 뒤에도 알림 엔진 무결성 검사가 "계획이 낡았다"는 이유만으로 F를 내지 않게 한다. 거짓 체결 기록이나 새 상태 쓰기 경로 없이.**

- 관제판 `doneWhen`도 바뀐다(결정 1): "118주 매도가 체결 기록으로 들어가고 알림 엔진 검사가 통과" → "실제 상태·정책으로 무결성 검사 PASS, `test_evaluate_timing_integration` 정상화(새 정책 기준), 매도 이력은 기존 기록(원장·조정 기록·키움 체결 조회)으로 충분".

## 3. 대안 검토 (NO_CHANGE → SIMPLIFY → REUSE → REPLACE → ADD)

| 순서 | 안 | 바꾸는 것 | K | 검사 PASS | 등록부 문제(§1-7) | 판정 |
|---|---|---|---|---|---|---|
| NO_CHANGE | (가) 그대로 두고 S7 2차에 합침 | 없음 | — | 아니오(잠재 F 유지) | S7 2차에서 | **권장(지금)** |
| SIMPLIFY | (나) 정책만: 타이밍 positions에서 MVLL(·SOXL) 키 삭제 | `alert_policy.json` 1곳 + 테스트 + cohort 이관 + K0 문구 | K3(소) | 예 | 해결 안 됨 | 조건부 권장(§4-B) |
| SIMPLIFY | (다) D5 그대로 선행: 엔진이 은퇴 종목을 알고 gap·halt만 평가 | `timing_engine.py`, `evaluate_alerts.py`, `alert_policy.json`(타이밍·`deployment_gate`), 설치 스킬, 테스트, cohort | K3(중) | 예 | 해결 안 됨(등록부 분리까지 넣으면 S7 2차와 사실상 같음) | 비권장(S7 2차와 중복) |
| REUSE | 기존 체결 필드(`confirmed_tranche_fills`, `confirmed_trades`)에 기록 | 상태 + 새 쓰기 경로 | K3 | 사실대로는 불가(§1-5) | — | **기각:** 거짓 기록 |
| REPLACE | anchor를 278로 새로 잡음 | 정책 anchor·슬롯 수량 + 상태 `timing_plan` 쓰기 경로(고정 27개의 apply 경로 또는 새 스크립트) | K3(대) | 예(이번만) | 아니오 | **기각:** 새 슬롯 수량 = 새 전략 결정(D5와 반대), 매도할 때마다 반복(② ③), acceptance 무효 위험 |
| ADD | 새 "체결 확인" 명령(propose/apply, 확인 코드) | 새 스크립트·스키마·규칙·권한·테스트 | K3(대) | 슬롯과 맞을 때만 | 아니오 | **기각:** 소비처가 은퇴할 슬롯뿐(연결 규칙 위반), 가장 복잡 |

- 검토했지만 넣지 않은 것: 엔진의 anchor 등식을 "보유 ≤ 기대값이면 통과"로 느슨하게 하는 안. 슬롯 수량(99주)을 담은 타이밍 검토가 낡은 anchor로 계속 나올 수 있다(`freshness_gate`가 막으려는 것). validator 약화라서 기각한다.

## 4. 권장안

### 4-A. 지금 (결정 2 = 가)

1. 코드·정책·상태 변경 없음.
2. 대조 확인 때의 운영은 절차 문서 §4 그대로다. 적용 후 검사 실패가 뜨면 Cowork가 적용 전에 알리고 사용자가 고른다.
   - Cowork는 오류 목록이 **"<종목>: holdings <n> do not equal anchor less confirmed tranches <anchor>" 한 종류이고, <n>이 이번 브로커 수량과 같을 때만** "알려진 불일치(r-i0b, S7 2차 대기)"로 설명한다.
   - 다른 오류가 하나라도 있으면 새 문제로 보고하고 멈춘다.
   - 이 판단 규칙을 절차 문서에 적을지는 결정 4(K0)다.
3. 예약 자동화 재개의 선행 조건에 "r-i0b 해소(또는 S7 2차 완료)"를 더한다(관제판 메모, r-sched-b 보류 목록).
4. 위험 판단은 지금처럼 카드(원가 한도 칸은 fact pack이 직접 계산)와 통합 점검(V1~V6, 계좌 점검선)이 맡는다. 알림 엔진은 원래 이 경로에 없다.

### 4-B. 다시 판정하는 시점: 10/8 M6 v2 결과 뒤

| 10/8 뒤 상황 | 다음 |
|---|---|
| MVLL 일부 보유가 이어지고, S7 2차 시작이 멀고, 대조 경고·테스트 6건이 부담 | (나) 착수 |
| MVLL 0주가 되거나 새 종목 매수가 예정됨 | (나)만으로는 부족하다. 등록부 분리가 필요하므로 S7 2차의 "타이밍 + 등록부" 부분을 앞당기는 별도 설계(이 문서 범위 밖, K3)를 하거나, (나)에 `holding_risk_rules.positions`의 0주 종목 삭제를 더하는 정책 편집을 한다. 후자는 종목 구성이 바뀔 때마다 K3 정책 편집이 반복된다 |
| 그 밖 | (가) 유지, S7 2차에서 해소 |

### 4-C. S7 2차에 합칠 때 넣을 완료 기준 (권장안 (가)의 연결)

- 실제 상태(그때의 revision)와 새 정책으로 `leveraged_state_integrity_errors` = [].
- MVLL·SOXL은 슬롯·anchor 검사 대상이 아니고, gap·halt watch-only는 남는다(D5).
- 상태 `timing_plan`은 바이트 그대로 둔다(읽히지 않는 이력). 새 상태 쓰기 경로 없음, 체결 추론 없음.
- `test_evaluate_timing_integration`이 새 정책 기준으로 통과한다(슬롯 후보 단언을 은퇴 동작 단언으로 교체).
- 대조 locale·절차 문서의 "I0-b 전까지 STATE_MISMATCH" 문구를 정리한다.

## 5. (나) 정책만 SIMPLIFY: 고를 때의 Builder 범위

- **세션:** Claude Code 새 worktree `i0b-policy`, Opus · xhigh(K3).
- **선행:** 이 대화에서 사용자의 정책 편집 승인(CLAUDE.md "approved policy는 명시 승인 없이 수정 금지"). 시작 전 `workspace/state/integrated_shadow/shadow_progress.json` 카운터 0 확인.
- **바꾸는 것**
  1. `stock-strategy-system/alert_policy.json`: `holding_timing_rules.positions`에서 `MVLL`(결정 3에 따라 `SOXL`도) 키를 지운다. 그 밖의 바이트는 그대로 둔다(줄바꿈 혼합 유지, 대상 블록만 잘라냄). `definitions`·`risk_overlay_rules`·`weakness_rearm`·`status`·`policy_version`은 건드리지 않는다.
     - `policy_version`을 바꾸지 않는 이유: 상태 `timing_plan.policy_version`과 달라지면 그 자체로 F다(`timing_engine.py:39-41`).
     - SOXL도 지우면 `positions`가 빈 객체가 된다. `alert_policy.json` 전용 스키마는 찾지 못했다. 검증기·테스트가 빈 값을 허용하는지 Builder가 먼저 확인하고, 막히면 멈추고 보고한다.
  2. shadow cohort 이관(K2, R9 선례): 의미 지문이 바뀌므로 한다. 카운터 0 확인 뒤.
  3. K0: `assets/locales/reconcile-broker-state-ko-KR.json`의 `warning_TIMING_PLAN_TICKER_CHANGED` 문구를 "timing_plan 종목 수량이 바뀝니다. 아래 '적용 후 알림 엔진 검사' 결과를 확인하세요."로 바꾸고, `references/broker-snapshot-reconciliation.md` §4의 "I0-b" 문구를 정리한다. 경고 자체는 고정 파일 `kiwoom_broker_shadow.py`가 상태의 timing_plan 키로 내므로 계속 뜬다. 그 파일은 고치지 않는다.
  4. 테스트 갱신: 실제 정책을 읽는 테스트의 슬롯 단언.
- **바꾸지 않는 것:** `portfolio_state.json`(timing_plan 포함), 모든 스크립트, 고정 27개, `deployment_gate`, `holding_risk_rules`, `SKILL.md`, 권한 3필드, 대조 원장·백업.
- **효과:** 지금 상태로 무결성 검사 PASS. 대조 표 상시 FAIL 해소. fact pack 타이밍 칸이 MVLL(·SOXL)에서 `NOT_APPLICABLE`(`NO_TIMING_RULE_FOR_TICKER`)로 바뀐다(지금도 `NOT_EVALUATED`라 판단 영향 없음).
- **잃는 것:** MVLL(·SOXL) gap·halt watch-only(D5가 남기기로 한 것)가 S7 2차까지 빠진다. 엔진이 돌지 않는 지금은 실제로 나오던 알림이 없다. 예약 자동화 재개 전에는 S7 2차로 되살려야 한다.
- **되돌리기:** 정책 블록 복원(커밋 되돌림). cohort 이관은 한 방향이다(되돌리면 새 cohort가 다시 시작. 지금 카운터 0이라 잃는 기록 없음).

## 6. 위험

| # | 위험 | 해당 안 | 대응 |
|---|---|---|---|
| 1 | 대조 표의 상시 FAIL이 새 실패를 가림 | 가 | §4-A-2 판단 규칙(한 종류·수량 일치일 때만 "알려진"). 다르면 멈춤 |
| 2 | `test_evaluate_timing_integration` 6건 실패로 평가기 회귀가 안 보임 | 가 | Builder 기준선에 "r19 원인 6건"으로 명시. 평가기를 고치는 작업은 r18 상태 복사본으로도 돌려 대조 |
| 3 | 예약 자동화를 재개하면 F로 멈추고 원가 한도 알림도 함께 안 나옴(`STATE_MISMATCH`가 먼저 반환) | 가 | 재개 선행 조건에 추가(§4-A-3). fail-closed라 거짓 알림은 없음 |
| 4 | MVLL 전량 매도·새 종목 매수 때 등록부 불일치로 다시 F | 가·나·다 | 10/8 뒤 재판정(§4-B). 근본 해결은 S7 2차 |
| 5 | gap·halt 감시가 S7 2차까지 빠짐(D5와 다름) | 나 | 결정 3에서 명시 수용. S7 2차 완료 기준에 복구 |
| 6 | 정책 편집이 줄바꿈·다른 키를 바꿈 | 나·다 | 키 경로 diff, 원시·정규화 해시 전후 보고, 대상 블록 밖 바이트 동일 |
| 7 | worktree 체크아웃·병합으로 `alert_policy.json` 줄바꿈이 바뀜(원본은 CRLF·LF 혼합, S7 보고 §0.2) | 나·다 | 병합 뒤 Cowork가 원시 해시 확인. 원시 해시를 쓰는 곳은 예약 clone manifest(재개 때 재생성)와 기록용뿐 |
| 8 | S7 2차 이관과 별도로 cohort 이관이 1회 더 생김 | 나·다 | 카운터 0 확인 후 이관, S7 2차 때도 0 확인 |
| 9 | 누군가 체결 기록을 "맞춰" 적음(118→99 등) | 전부 | 금지. Judge 항목 2 |

## 7. 테스트와 Judge 범위

### 7-1. (가) NO_CHANGE

- 테스트·Judge 없음. K0 문구(결정 4)는 사용자 승인 뒤 Cowork가 바꾸고, Judge는 필요 없다.

### 7-2. (나) 정책만

- 대상 테스트(실제 정책을 읽거나 타이밍 정책·cohort 지문을 쓰는 것): `test_evaluate_timing_integration`, `test_timing_engine`, `test_v2_5_leveraged_confirmation`, `test_v2_6_integration`, `test_v2_6_shadow_acceptance`, `test_build_holding_fact_pack`, `test_reconcile_broker_state`, `test_kiwoom_broker_shadow`, `test_portfolio_decision_dashboard`, `test_mvll_volume_authority`(`definitions` 유지 확인), `test_v2_6_12_holding_valuation_shadow`, `test_v2_6_3_free_web_new_buy`, `test_v2_6_7_session_aware_kiwoom_priority`. 기준선은 Builder 시작 때 측정한다(§1-3의 6건 포함).
- 새로 넣을 fail-closed 테스트
  1. 타이밍 positions에 남은 종목은 anchor 불일치면 여전히 `STATE_MISMATCH`다(validator 약화 없음).
  2. 타이밍 positions에서 빠진 종목도 `holding_risk_rules` 검사(원가 한도, 등록부)는 그대로 돈다(NBIS 10% 경계 사례가 D로 나옴).
  3. 실제 r19 상태 + 새 정책 → 무결성 오류 0, 상태 파일 바이트 불변.
  4. 상태 `timing_plan.policy_version` 불일치는 여전히 F다.
- 검증: `validate_schema_contracts.py` PASS, 고정 27개 diff 0, `deployment_gate` 스크립트 해시 불변, 상태·원장 diff 0, 전체 테스트는 서브에이전트로 "새 실패 0".
- **Independent Judge(새 Claude Code 세션, 파일 수정 없음) 확인 항목**
  1. `alert_policy.json`에서 바뀐 키 경로가 승인된 것(`holding_timing_rules.positions.MVLL`[·`.SOXL`])뿐이고, 그 밖 바이트가 같다.
  2. 상태 쓰기·체결 기록·체결 추론이 없다. `portfolio_state.json`, 원장, 백업 diff 0. `never_touched` 불변.
  3. validator가 약해지지 않았다(새 테스트 1·2·4가 옛 정책·코드에서도 같은 의미인지).
  4. 고정 27개, 스크립트, `deployment_gate` diff 0 → 키움 acceptance 유효.
  5. 실제 상태로 무결성 PASS(재현 명령 포함).
  6. 소비처 영향이 문서대로다(fact pack `NOT_APPLICABLE`, 대시보드 빈 투영, 대조 사전 검사 PASS).
  7. cohort 이관 전 카운터 0 기록이 있다.
  8. D5와의 차이(gap·halt 일시 중단)가 사용자 결정으로 기록돼 있고, S7 2차 완료 기준에 복구가 들어가 있다.
  9. 권한 3필드 불변.

### 7-3. (다)를 고를 경우

- S7 Builder 보고 §1c, §2.2 2차 3·4번, S6 요구 8의 테스트 11개 + `test_evaluate_timing_integration`, 그리고 `deployment_gate`·설치 스킬 동기화 검증이 더해진다. S7 2차 Judge 범위와 대부분 겹치므로 따로 하지 않기를 권한다.

## 8. 사용자 결정 (하나씩)

1. **I0-b 목표 재정의:** 체결 기록 경로를 만들지 않고 목표를 §2대로 바꾼다. 118주 매도 이력은 기존 기록으로 충분하다. — 권장: 예 → **결정(2026-10-06 사용자): 예**
2. **지금 할 일:** (가) NO_CHANGE, 10/8 M6 v2 뒤 재판정, 해소는 S7 2차 / (나) 정책만 SIMPLIFY 지금 착수 / (다) D5 엔진 선행. — 권장: (가) → **결정(2026-10-06 사용자): (나) 정책만 지금 수정**
3. **(나)를 고를 때만:** 범위 MVLL만 / MVLL+SOXL(D5와 같은 범위라 다음 SOXL 매도 때 K3를 다시 하지 않음). gap·halt 감시 일시 중단 수용 여부. — 권장: MVLL+SOXL → **결정(2026-10-06 사용자): MVLL+SOXL, gap·halt 일시 중단 수용**
4. **K0 문구(선택):** 절차 문서 §4에 §4-A-2 판단 규칙 추가, locale의 "I0-b" 문구 정리를 지금 할지. — 권장: (가)면 판단 규칙만 지금, 문구 정리는 해소 때

## 9. 확인 필요

- Codex 예약 2개의 `PAUSED`는 r-sched-b 문서(오늘) 기준이다. 이번에 TOML을 직접 읽지 못했다(연결 폴더이지만 이 세션 셸에 마운트되지 않음).
- 활성 Cowork 예약 13개 중 알림 엔진을 부르는 것이 없다는 것은 r-sched-b §5 기준이다. 직접 확인한 것은 통합 점검 v3.11뿐이다.
- §1-3 테스트 결과는 Cowork VM(Python 3.10.12) 기준이다. Windows 결과는 확인 필요.
- Windows git에서 `alert_policy.json`·`evaluate_alerts.py`가 깨끗한지(VM에서는 줄바꿈 차이만).
- (나)에서 빈 `positions`를 검증기·테스트가 허용하는지(Builder 첫 확인).
- 118주 체결 가격 $37.80은 사용자 보고·계획 문서 기준이다. 대조안의 키움 체결 조회 표시값은 수량·시각만 담고 있다.

## 10. 근거 파일

- `stock-strategy-system/portfolio_state.json`(revision 19), `reconciliation_ledger.jsonl`, `backups/portfolio_state.r18.20261006T132028453816Z.json`, `alert_policy.json`
- `workspace/outputs/reconciliation/20261006T131852Z/reconciliation_proposal.json`
- `workspace/outputs/manual-portfolio-analysis/manual-20261006T132111850903Z-2817a6a2a07e/manual-portfolio-analysis.json`
- `workspace/state/integrated_shadow/shadow_progress.json`
- `manage-us-stock-strategy/scripts/timing_engine.py:31-108, 394-414`, `evaluate_alerts.py:439-583, 727-747, 875-905`, `reconcile_broker_state.py:61-80, 177-183`, `kiwoom_broker_shadow.py:351-354, 413-430`, `build_holding_fact_pack.py:194, 253-267`, `portfolio_decision_dashboard.py:357-408`, `run_manual_portfolio_analysis.py:2115-2124`
- `manage-us-stock-strategy/tests/test_evaluate_timing_integration.py`
- `manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json`, `assets/locales/reconcile-broker-state-ko-KR.json`, `references/broker-snapshot-reconciliation.md` §4
- `docs/claude/system-review-p3-design-2026-09-30.md` §4-3, `system-review-p4-roadmap-2026-09-30.md` §2·§4(S4 경고 분기)·§5, `loss-limit-review-s5-policy-proposal-2026-10-01.md` 부록 C.11·§9, `s7-builder-report-2026-10-01.md` §1c·§2.1·§2.2·§5.6, `mvll-investor-day-plan-2026-10-04.md` §11-1, `r-sched-b-scheduled-clone-k3-design-2026-10-06.md` §1·§5, `integrated-check-prompt-v3.11-draft-2026-10-05.txt`

## 11. 진행 기록

- 2026-10-06 설계안 작성(Cowork). 사용자 결정 대기. 바꾼 파일: 이 문서 1개.
- 2026-10-06 **결정 1 = 예.** I0-b 목표를 §2대로 바꾼다. 체결 기록 경로(REUSE·REPLACE·ADD)는 만들지 않는다. 118주 매도 이력은 기존 기록(원장·조정 기록·키움 체결 조회)으로 충분하다. 관제판 `doneWhen`은 §2의 새 문구로 바꾼다.
- 2026-10-06 **결정 2 = (나).** 권장 (가)와 달리 10/8을 기다리지 않고 지금 §5 범위로 착수한다. 남는 위험: MVLL 전량 매도·새 종목 매수 때는 등록부 검사로 다시 F(§1-7, §6-4). 그때는 §4-B 둘째 줄대로 다시 판정한다.
- 2026-10-06 **결정 3 = MVLL+SOXL, gap·halt 일시 중단 수용.** `holding_timing_rules.positions`가 빈 객체가 된다(빈 값 허용 여부는 Builder 첫 확인, 막히면 멈춤). S7 2차 완료 기준에 "MVLL·SOXL gap·halt watch-only 복구"를 넣고, 예약 자동화 재개 전 필수로 한다. SOXL weakness_10ema 감시와 SOXL-R50 재무장 잠금도 함께 빠진다(D5·#7·#14에서 이미 은퇴 결정).
- 2026-10-06 결정 4(K0 문구)는 (나)를 골라 Builder 범위(§5-3)에 포함한다. 병합 전까지의 대조 확인은 §4-A-2 판단 규칙으로 Cowork가 설명한다(문서 수정 없음).
- 2026-10-06 Builder 지시문 작성: `docs/claude/i0b-policy-builder-prompt-2026-10-06.md`. §5에 더해 이관 스크립트 `--reason` 선택 인자(K2, R9 보고 §5-1 제안)와 사유 `HOLDING_BASELINE_SEMANTIC_CHANGE`를 넣었다. 정책 편집 직전에 Builder 세션에서 사용자 승인을 한 번 더 받는다.
- 2026-10-06 운영 주의: Cowork VM에서 실행한 `git status`가 `.git/index`의 stat 캐시를 갱신했고, 마지막 호출은 빈 `.git/index.lock`을 남겼다(연결 폴더 삭제 금지 때문). 사용자 승인(삭제 권한)으로 그 잠금 파일 1개만 지웠다. 이후 Cowork VM에서는 `git status`처럼 인덱스를 쓰는 git 명령을 피하고, 필요하면 `git --no-optional-locks status`를 쓴다.
