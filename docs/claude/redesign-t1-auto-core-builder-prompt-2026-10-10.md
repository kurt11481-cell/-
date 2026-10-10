---
id: redesign-t1-auto-core-builder-prompt-2026-10-10
title: 재설계 T1 Builder 지시문 — 자동 운영 코어 v1 (수집 · 자동 대조 · 노출)
date: 2026-10-10
class: 권한·한도 변경(옛 K3) — 상태 쓰기 승인 방식 변경, 키움 승인 고정 파일 수정. 독립 Judge 필수
decision: 사용자 2026-10-10 09:27 KST "재설계: A1 a, A2 a, A3 a, A4 a, A5 a, A6 a, A7 a" (docs/claude/automation-redesign-2026-10-10.md 7·10절)
absorbs: gap-s7-daily(R1 아침 수집) · r-auto-apply-k3(s7-reconcile-auto-apply-builder-prompt-2026-10-10.md F1·F2) · cash-def-k3(현금 = 주문 가능액) · p-92 9.2-3 · p-92-b1a · r-cost
authority: order_authority=false · quantity_authority=none · execution_quantity=null (이 작업은 주문 권한을 바꾸지 않는다)
consumers: T1 Builder(worktree auto-core-t1) · T1 Judge(Builder 보고 뒤 Cowork 작성) · 06:40 통합 점검(코어 결과 읽기) · 관제판 redesign-t1 · T2 Builder
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `auto-core-t1` · 이유: 상태 쓰기 승인 방식과 키움 승인 고정을 바꾸는 권한 변경, 독립 Judge 필요**

## 1. 사용자 조작 (Windows PowerShell, 이 순서로 한 번)

1. 커밋(이 지시문과 바뀐 CLAUDE.md가 worktree에 들어가야 한다):
```
cd "E:\사업\##금동한\코덱스저장소"
git add -- CLAUDE.md AGENTS.md docs/claude/automation-redesign-2026-10-10.md docs/claude/redesign-t1-auto-core-builder-prompt-2026-10-10.md docs/claude/fx1009-fx4-record.md docs/claude/fx1009-fix-plan-2026-10-09.md docs/claude/ops-dev-touch-reduction-2026-10-09.md docs/claude/fx4-cash-def-builder-prompt-2026-10-09.md docs/claude/s7-reconcile-auto-apply-builder-prompt-2026-10-10.md
git commit -m "docs: automation redesign decision (A1-A7 a), CLAUDE.md goal, T1 builder prompt"
```
2. Builder 시작:
```
claude --worktree auto-core-t1 --model opus --effort xhigh
```
3. Claude Code 첫 메시지로 이 한 줄만 붙여 넣는다:
```
Read docs/claude/redesign-t1-auto-core-builder-prompt-2026-10-10.md and follow sections 2-5 exactly.
```
4. 끝나면 Cowork에 "T1 Builder 완료"만 보낸다(Cowork가 worktree를 직접 읽는다).

## 2. 목표와 완료 기준 (기계 판정)

- 목표: 매 거래일 사람이 하던 일(거래내역 원문 저장 · 30분봉 수집 · 이력 갱신 · 대조 propose · "확인 <코드>" · 노출 점검)을 **Windows 작업 하나가 결정론 코드로** 대신한다. 사람 입력 없음. 주문 없음.
- 완료(Builder 단계): 대상 테스트 통과 · 기준선(docs/claude/test-baseline-2026-10-09.md) 대비 새 실패 0 · 테스트 수 감소 0 · 허용 경로(3절 "범위") 밖 변경 0 · 스키마 감사 PASS · 7절 보고.
- 완료(T1 전체, 병합 뒤): Windows 작업이 3거래일 연속 무인 실행(종료 코드 0 또는 사유 있는 HOLD) · 비교 결과 일치 · 사용자 "켜" 한 번으로 기록 모드 · p-s7-routine 은퇴.

## 3. Builder 지시 (이 절만 따른다)

```
권한 경계: order_authority=false, quantity_authority=none, execution_quantity=null 유지.
키움 주문 명령(overseas orders *)·주문 도구 호출 금지. 체결은 브로커 체결 조회로만, 가격으로 추정 금지.
workspace/policies/* 와 stock-strategy-system/{portfolio_state.json, reconciliation_ledger.jsonl, decision_journal.json, alert_policy.json}
은 직접 수정하지 않는다(정책 변경이 필요하면 F7의 제안 파일로만). 비밀(.env*, 토큰, 계좌번호) 읽기·출력 금지.
판단이 필요하거나 범위를 넘으면 BLOCKED.md를 worktree 루트에 쓰고 멈춘다(사용자에게 묻지 않는다).

범위(허용 경로): manage-us-stock-strategy/{scripts,schemas,tests,references,assets}/ 의 아래 F1~F8 관련 파일,
manage-us-stock-strategy/scripts/ 아래 새 파일, workspace/outputs/regular-session-closes/collect_30m.ps1(이동 원본, 삭제는 하지 않음),
docs/claude/redesign-t1-* (보고·제안 파일). 그 밖은 금지.

0단계 — 사실 확인(읽기만, 보고 맨 위)
 a. 키움 승인(acceptance) 고정이 지금 무엇을 막는가: validate_kiwoom_session_aware_acceptance_candidate.py, scheduled_input_gate.py,
    manual_data_guards.py, run_manual_portfolio_analysis.py preflight, reconcile propose/apply 경로에서 활성 acceptance 해시를
    요구하는 곳을 모두 찾는다. 고정 범위: manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json(27경로).
 b. 체결 조회의 날짜 뜻: kiwoom_account_readonly_bridge.py의 account_fills_read(ust21510)와, 추가할 ust21150(일별 주문체결내역)·
    ust21610(당일매매)·ust21100(거래내역)의 기준일이 미국 세션 날짜인지 한국 날짜인지(명세 + 저장소 fixture). 2026-10-09 미국 세션
    SOXL 22주 매도가 ust21610 --date 20261009에 나오고, 10/10 아침 ust21100에는 아직 없었다(Cowork 관측).
 c. 잔고 ust21070의 qty·poss_qty·pred_cntr_sellq/buyq·frgn_stk_book_uv 뜻과, 매수 체결 직후 poss_qty가 바로 늘어나는지(확인 못 하면 "확인 필요").
 d. 노출 점검의 보류 사유 hwm_line_or_pause_state_missing_or_corrupt의 원인(고치지는 않는다, 보고만).
 e. 테스트 기준선 실패 id 확보(test-runner 서브에이전트 가능, 숫자는 직접 센다).

F1 현금 정의 (kiwoom_broker_shadow.py, 스키마, manual_data_guards.py)
 - available_cash_usd = fc_ord_alowa(키움 주문 가능액). basis 이름 KIWOOM_ORDER_AVAILABLE_USD.
 - 검사는 하나: fc_ord_alowa − fc_pymn_alowa > 1.00이면 같은 스냅샷에서 qty > poss_qty인 종목이 1개 이상 있어야 한다(체결 직후 대금).
   아니면 CASH_UNSETTLED_NOT_RECONCILED_WITH_HOLDINGS로 막는다. fc_ord_alowa < fc_pymn_alowa − 1.00이면 막는다.
   외화예수금(fc_entra)과 비교하지 않는다 — 결제된 돈만 보여 주는 칸이라 체결 직후 상태를 막는다(fx1009-fx4-record.md 4-1).
 - 제안에 cash_components{deposit, withdrawable, order_available, unsettled_component} 기록. 대시보드 매수 자금 상한 코드는 손대지 않는다.
 - 예상 매도대금 칸(verified_orderable_cash_from_expected_proceeds_usd)은 계속 0이어야 한다(체결 안 된 매도는 현금이 아니다).

F2 브리지 조회 추가 (kiwoom_account_readonly_bridge.py) — 읽기 전용만
 - ust21100 거래내역, ust21150 일별 주문체결내역(또는 0단계 b로 정한 체결 조회)을 기존 방식(실전계좌 토큰 재사용, 1회 복구,
   8005면 재발급 없이 실패)으로 추가. 계좌번호는 저장·출력하지 않는다.

F3 거래내역 증거 자동 (cash_flow_evidence.py 호출)
 - 기간 = 원장 마지막 증거 period_to 다음 날(없으면 활성화 기록일)부터 실행일까지, 빈 날 없이. 원문은 저장하지 않고 정규화본만
   workspace/private_inputs/cash_flow_evidence/. 정규화 실패·UNCLASSIFIED > 0이면 그날 기록하지 않음(HOLD).

F4 자동 대조 + 불변 조건 (reconcile_broker_state.py · apply_user_confirmed_broker_snapshot.py)
 - 새 서브커맨드 auto: propose와 같은 읽기 → 아래 I1~I5 판정 → 결과를 workspace/outputs/auto-core/<YYYY-MM-DD>/reconcile.json.
   I1 필수 조회(잔고·예수금·예수금 상세·미체결·체결·거래내역) 모두 return_code 0(미체결 "내역 없음"은 0건으로 인정)
   I2 종목별 poss_qty 변화 = 마지막 기록 이후 브로커 체결 수량(매수 − 매도)과 정확히 일치, 새 종목·사라진 종목도 체결로 설명
   I3 현금(주문 가능액) 변화 = 체결 대금(수수료 포함) ± 분류된 거래내역(입출금·배당·세금·환전)과 1.00 USD 이내
   I4 상태 파일 해시·revision = 마지막 기록, 원장 해시 사슬 정상(밖에서 고친 흔적 없음)
   I5 보유·현금·평단 외 필드(stage, timing_plan, 체결 기록, 후보, 전략 칸) 불변. 쓰기 직전 상태 다시 해시
 - 평단 = 키움 frgn_stk_book_uv(브로커가 정답). 변화 설명 대상에서 평단은 뺀다.
 - 설정 workspace/policies/auto_core.json(F7 제안으로 만듦)의 mode가 "compare"면 쓰지 않고 would_apply만 남긴다. "apply"이고 I1~I5와
   kill_switch=false가 모두 맞으면 apply 라이브러리로 기록: confirmation_method "AUTO_CORE_INVARIANTS", 불변 조건 결과·커밋 SHA를
   원장 줄에 남기고 기존 백업·해시 사슬을 그대로 쓴다. 사람 코드를 흉내 내거나 만들지 않는다.
 - 기존 propose/show/apply(사람 확인 코드) 경로는 그대로 둔다(전환기 대체 경로).
 - 입출금이 있으면 HWM용 cash_flow_declaration을 거래내역 분류에서 자동으로 채운다(사람 신고 불필요).

F5 코어 오케스트레이터 (새 파일)
 - scripts/auto_core.py daily: ① 정지 스위치·설정 읽기 ② 수집(F2·F3 + 30분봉: 종목 = 잔고 보유 ∪ docs/claude/watchlist-registry.json
   members ∪ {SOXX}, 처음 보는 종목은 2026-04-01부터) → regular_session_close_history.py build --update ③ F4 auto
   ④ run_portfolio_exposure_review.py ⑤ 결과 workspace/outputs/auto-core/<날짜>/result.json + LATEST.json
   {status OK|HOLD|FAIL, reasons[], commit_sha, dirty_paths[], mode, invariants{I1..I5}, would_apply|applied, holdings_change,
    exposure{E,N,lines,holds}, compare{streak, last_mismatch}, next_action_for_user: null 또는 한 줄}. 종료 코드 0=OK/HOLD, 1=FAIL.
 - 실행 안 재시도 0회(첫 실패에서 멈춤), 다음 실행이 자연 재시도. 같은 날 두 번 돌아도 결과가 같아야 한다(멱등).
 - 비교 모드 연속 일치: 전날 would_apply와 그 뒤 원장(사람 경로로 적용됐다면)이 같거나, 적용이 없었으면 오늘 스냅샷이 전날 would_apply
   상태와 체결로 설명되면 streak + 1, 아니면 0과 차이 기록. streak ≥ 3이면 next_action_for_user = "기록 모드 켤 준비됨".
 - scripts/collect_30m.ps1: workspace/outputs/regular-session-closes/collect_30m.ps1(현재 로컬 수정본, -KiwoomProfile 포함)을 추적되는
   위치로 복사하고 원본은 남긴다. 출력 경로는 기존 pages 폴더 그대로.
 - scripts/run_auto_core.ps1(ASCII, PowerShell 5.1, kiwoomcli 출력은 cmd /c 리디렉션으로 바이트 그대로) +
   scripts/register_auto_core_task.ps1: register_sec_scheduled_shadow_task.ps1과 같은 방식(Interactive, Limited),
   화~토 06:15 KST 1회(여름·겨울 모두 마감 뒤), 이름 InvestmentV2-AutoCore. 등록 스크립트는 만들기만 하고 실행하지 않는다.

F6 키움 승인 고정 은퇴 (사용자 A5)
 - 0단계 a 결과로, 고정 해시 요구를 "실행 기록에 git 커밋 SHA와 dirty 경로 기록 + apply 모드에서는 고정 대상 파일에 미커밋 수정이 있으면 FAIL"로
   바꾼다. kiwoom-acceptance-pin-scope.json은 지우지 않고 status RETIRED로 표시.
 - workspace/policies/* 를 바꿔야만 은퇴할 수 있으면 직접 고치지 말고 F7 제안 파일에 정확한 새 내용을 쓴다.
 - 은퇴가 위 허용 경로 안에서 끝나지 않으면(다른 권한 경계를 건드림) 은퇴는 하지 말고 BLOCKED.md 대신 보고 7절에 "F6 미실행 + 이유 +
   필요한 최소 변경"을 적고 나머지 F를 완성한다.

F7 정책 제안 파일 (직접 쓰지 않음)
 - docs/claude/redesign-t1-policy-proposals.json: auto_core.json 새 파일 내용({mode:"compare", kill_switch:false, compare_days_required:3,
   schedule_kst:"06:15", symbols_extra:["SOXX"]})과 F6에 필요한 정책 변경(있으면)을 경로·전체 새 내용·이유로. Cowork가 사용자 승인 뒤 적용.

F8 문서
 - references/broker-snapshot-reconciliation.md·portfolio-exposure-review.md에 auto 경로와 I1~I5, 비교 모드를 쓴다. CLAUDE.md는 쓰지 않는다.

테스트(대상만, 새 파일 tests/test_auto_core.py 등): F1 체결 직후(ord > pymn, qty > poss_qty) PASS·대금만 있고 수량 반영 없음 BLOCK·
ord < pymn BLOCK · I1~I5 각각 실패 → 기록 안 함 · 체결로 설명되는 매도·매수·신규 종목·전량 매도 · 입출금·배당 분류 · UNCLASSIFIED HOLD ·
compare 모드에서 상태 무변경 · apply 모드에서 원장 줄 형식·사슬·백업 · kill_switch · 멱등 · 사람 코드 경로 회귀 없음 · 주문 명령 호출 경로 없음.
스키마 감사(validate_schema_contracts.py) PASS.
```

## 4. 보고 형식 (docs/claude/redesign-t1-builder-report-2026-10-10.md, 한국어)
1. 맨 위: 0단계 a~e 결과, F6 실행 여부, BLOCKED 여부.
2. 바꾼 파일 목록(허용 경로 대조), 테스트 결과(대상·전체·기준선 대비 새 실패), 스키마 감사.
3. 사람이 할 일(병합 명령, 정책 제안 적용, 작업 등록 명령) — 각 한 줄.
4. 남는 위험과 확인 필요.

## 5. Judge 확인 항목 (Cowork가 Builder 뒤 Judge 지시문에 그대로 넣는다)
- compare 모드에서 상태·원장·일지 쓰기 경로가 하나도 없는가. apply 모드도 I1~I5·kill_switch 중 하나만 어긋나면 쓰지 않는가.
- 체결 추정 코드가 없는가(가격·종가로 수량을 만드는 경로). 주문 명령·주문 도구 호출 경로가 없는가.
- 현금 = 주문 가능액이고, 예상 매도대금 칸은 여전히 0인가. 대시보드 매수 자금 상한 코드가 그대로인가.
- 보유·현금·평단 외 필드가 바뀌지 않는가. 원장 해시 사슬·백업이 이어지는가. 로그에 계좌 식별자가 없는가.
- F6: 고정 해시를 없앤 대신 커밋 SHA·dirty 검사가 apply를 실제로 막는가.
- 기존 사람 확인 코드 경로가 회귀 없이 남아 있는가. 테스트 수 감소·허용 경로 밖 변경이 없는가.

## 6. 병합 뒤 배포 (Cowork가 진행, 사용자 손은 표시한 곳만)
1. Cowork: Builder 결과 확인 → Judge 지시문 작성 → 사용자: Judge 세션 1번(명령은 그때 한 줄로 제공).
2. 사용자: 병합 명령 1줄(Cowork 제공).
3. Cowork: F7 정책 제안 적용(auto_core.json = compare) — 사용자 "적용" 한 마디.
4. 사용자: `powershell -ExecutionPolicy Bypass -File manage-us-stock-strategy\scripts\register_auto_core_task.ps1` 1번.
5. Cowork: 06:40 통합 점검 로더에 "auto-core LATEST.json 읽기 → status가 OK가 아니면 한 줄 푸시, next_action_for_user가 있으면 함께" 1단계 추가
   (예약 작업 수정 — 사용자 승인 클릭 1번). 규칙 파일 해시는 그대로.
6. 비교 3거래일 → streak 3이면 푸시 → 사용자 "켜" → Cowork가 auto_core.json mode = apply. p-s7-routine 은퇴, 관제판 갱신.
