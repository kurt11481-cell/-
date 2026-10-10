# S7 대조 자동화 Builder 지시문 — 거래내역 자동 첨부·체결 분류·확인 코드 자동 apply (2026-10-10, K3)

- 상태: **작성 완료, 착수 보류(FX-1009 동결, fx-6 이후)**. Builder 미실행. 정책·상태·원장·CLAUDE.md·코드 무변경.
- 사용자 결정(2026-10-10 08:59 KST, Cowork 대화): "확인 <코드>도 그냥 자동화해. 시스템이 자동화로 설계 중인데 사용자가 하나하나 개입하는 건 모순이다." 선택지 중 **C 전면 자동 apply**를 골랐다. (권고안 B 좁은 범위 사전 동의는 사용자가 채택하지 않음.)
- 성격: **K3** (보유·현금 상태를 쓰는 유일한 경로의 승인 방식을 바꾼다). 사용자 승인 전 중지, 독립 Judge, 키움 승인 고정 파일 수정(`reconcile_broker_state.py`, `cash_flow_evidence.py`, `kiwoom_runtime_bridge.py`)으로 승인 재고정 필요.
- 풀려는 문제(2026-10-10 실측): ① 거래내역 증거를 사람이 받아 붙이는 수작업 때문에 rev 21·22는 증거가 대조보다 늦게 만들어졌고 rev 23은 붙이지 않아 노출 점검이 `CASH_FLOW_COVERAGE_GAP`으로 보류됐다. ② 열린 주문 지시서(OI-20261009-SOXL-2, 22주)와 브로커 수량 변화(75→53)를 사람이 맞춰 본다. ③ 매 대조마다 `확인 <코드>`가 필요하다.
- 소비처: 아침 통합 점검·브로커 대조, `run_portfolio_exposure_review.py`(보류 해소), 주문 지시서 체결 분류, 관제판.

## 1. 사용자 조작 (동결 해제 후)
**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `s7-auto-reconcile` · 이유: 상태 쓰기 승인 방식을 바꾸는 K3, 독립 Judge 필요**
1. 사용자가 fx-6에서 동결을 푼다.
2. 동시 진행 K3가 1개 이하인지 확인한다(관제판).
3. 이 지시문을 커밋한 뒤 worktree에서 Builder를 시작한다. Judge는 별도 세션이며 파일을 고치지 않는다.

## 2. Cowork 사전 확인 (2026-10-10, 읽기 전용)
- 고정 파일에 포함: `reconcile_broker_state.py`(23행), `cash_flow_evidence.py`(29행), `kiwoom_runtime_bridge.py` — `manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json`.
- `CLAUDE.md`와 `broker-snapshot-reconciliation.md`는 "Claude Code·Codex·예약 작업·Judge는 apply 안 함"을 명시한다. 이 문장 변경은 **사용자 판단**이며 Builder는 고치지 않는다.
- 원장(`reconciliation_ledger.jsonl`) 10건: rev 21·22·23은 `cash_flow_declaration` 없음.

## 3. Builder 지시 (이 상자만 따른다)
```
범위: 아래 4개만. 주문 도구·체결 추론·예약 작업 등록·journal apply·정책(alert_policy 등)·CLAUDE.md는 건드리지 않는다.
order_authority=false, quantity_authority=none, execution_quantity=null 유지.

F1 거래내역 자동 첨부
 - propose가 ust21100을 직접 읽는다(보유·예수금·체결 읽기와 같은 브리지, 실전계좌/real).
 - 기간 = 원장 마지막 증거의 period_to 다음 날(없으면 활성화 기록일)부터 as_of 다음 날까지. 구멍이 없게 한다.
 - 원문은 저장하지 않고 정규화본만 workspace/private_inputs/cash_flow_evidence/ 에 둔다. 정규화 실패(RAW_SHAPE_INVALID 등)는 지금처럼 실패, 제안은 증거 없음 표시로 fail-closed.
 - 기존 --cash-flow-evidence 수동 경로는 유지(없으면 자동).

F2 체결 분류 표시
 - 브로커 수량 변화를 열린 지시서(docs/claude/order-instructions/OI-*.md의 종목·방향·수량·유효 세션)와 대조해 표에 한 줄 추가: 일치 / 불일치 경고. 가격 움직임으로 체결을 추정하지 않는다. 상태에는 쓰지 않는다.

F3 자동 apply (사용자 결정 C)
 - 새 서브커맨드 auto-apply. 사용자 사전 동의 기록(workspace/policies/reconcile_standing_consent.json: 동의 ID, 시작일, 만료일, 사용자 원문)이 유효할 때만 동작한다. Builder는 템플릿만 만들고 실제 동의 기록은 사용자가 승인해 둔다.
 - 아래가 하나라도 어긋나면 apply하지 않고 NOT_APPLIED와 사유를 남기며 지금의 확인 코드 경로로 되돌린다(fail-closed):
   필수 읽기 3종 통과 · 제안 15분 이내 · 상태 파일 해시·revision 일치 · 원장 사슬 정상 · UNRESOLVED·OPEN_ORDERS 외 경고 없음 · 적용 후 알림 엔진 검사 통과 · F1 증거 정규화 OK 및 UNCLASSIFIED 0 · 변경 크기 한도(값은 사용자 결정, 기본값 없음, 한도 초과는 코드 필요).
 - 원장 줄에 confirmation_method=STANDING_AUTO_CONSENT, 동의 ID, 자동 실행 주체를 남기고 기존 해시 사슬·백업 규칙을 그대로 쓴다. 사람 입력 코드를 흉내 내거나 생성하지 않는다.
 - 정지 스위치: 동의 기록 만료·삭제·revoked=true면 즉시 수동 경로.

F4 문서
 - references/broker-snapshot-reconciliation.md와 portfolio-exposure-review.md에 F1~F3 절차를 쓴다(CLAUDE.md는 쓰지 않는다).

테스트(대상만): 구멍 없는 기간 계산, 정규화 실패 fail-closed, F2 일치·불일치·열린 지시서 없음, auto-apply 거부 사유별(만료·해시·revision·사슬·UNCLASSIFIED·한도 초과·동의 없음/만료/revoked), 원장 줄 형식과 사슬, 수동 코드 경로 불변. 스키마 감사와 고정 파일 해시 재계산 보고.
```

## 4. Judge 확인 항목
- auto-apply가 동의 기록 없이 또는 만료 뒤 동작하지 않는다. 사람 코드 경로 회귀 없음.
- 필수 읽기·만료·해시·사슬 중 하나만 어긋나도 쓰지 않는다. 쓰기 직전 상태 재해시.
- 보유·현금·평단 외 필드(stage, timing_plan, 체결 기록, 후보, 전략 필드)가 바뀌지 않는다. 체결 추정 코드 없음.
- 원장·백업·해시 사슬 연속, 로그에 계좌 식별자 없음. 주문 도구 호출 경로 없음.

## 5. 사전 부검과 남는 위험 (council 대용, 정식 council은 착수 전 K3 결정 때)
- 가장 큰 위험: 브로커 조회가 불완전한데(부분 보유 목록 등) 코드 없이 상태에 쓰인다. 사람 코드가 막던 유일한 지점이다. 그래서 F3 조건에 필수 읽기·변경 크기 한도·정지 스위치를 둔다. 한도 값은 사용자가 정한다.
- 가장 강한 반대 의견: 안전 규칙이 "사용자 명시 확인"에서 "사전 동의"로 바뀌므로 CLAUDE.md 하드 안전 문장과 충돌한다. 사용자가 CLAUDE.md 변경을 승인하기 전에는 시행하지 않는다.
- 이번 대화에서 코드·상태·원장은 건드리지 않았다. 동결 해제 전까지 확인 코드 경로를 그대로 쓴다.

## 6. 진행 기록
- 2026-10-10 Cowork: 원인 확인(원장·파일 시각), 설계안 제시, 사용자 C 선택, 이 지시문 작성. 다음: fx-6에서 동결 해제 → 사용자 K3 승인(한도 값, 동의 기록, CLAUDE.md 문장) → Builder.
