---
id: redesign-t1-judge-prompt-2026-10-10
title: 재설계 T1 독립 Judge 지시문 — 자동 운영 코어 v1
date: 2026-10-10
class: 권한·한도 변경(옛 K3) — 독립 Judge
builder_prompt: docs/claude/redesign-t1-auto-core-builder-prompt-2026-10-10.md
builder_report: .claude/worktrees/auto-core-t1/docs/claude/redesign-t1-builder-report-2026-10-10.md
worktree: .claude/worktrees/auto-core-t1 (base 74ad71e, uncommitted changes)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: Cowork(병합 판단) · 관제판 redesign-t1
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃, worktree 아님) · 이유: 상태 쓰기 승인 방식을 바꾸는 변경의 독립 검토**

## 사용자 조작 (Windows PowerShell, 한 번)
```
cd "E:\사업\##금동한\코덱스저장소"
claude --model opus --effort xhigh
```
첫 메시지로 이 한 줄만:
```
Read docs/claude/redesign-t1-judge-prompt-2026-10-10.md and follow the Judge section exactly.
```
끝나면 Cowork에 "T1 Judge 완료"만 보낸다.

## Judge
```
너는 독립 Judge다. Builder 보고를 증거로 쓰지 말고 코드·diff·테스트로 직접 확인한다.
파일을 고치지 않는다. 유일하게 쓰는 파일은 판정 보고 docs/claude/redesign-t1-judge-report-2026-10-10.md 하나(메인 체크아웃).
키움 조회·kiwoomcli·auto_core.py daily·reconcile_broker_state.py auto/apply 실행 금지(가짜 데이터 테스트만). 커밋·병합 금지.
대상: git -C .claude/worktrees/auto-core-t1 status / diff 74ad71e (CRLF 주의: 줄바꿈 차이만인 파일은 따로 적는다).

확인 항목 — 항목마다 PASS/FAIL + 근거(파일:줄):
J1 범위: 바뀐 경로가 manage-us-stock-strategy/{scripts,schemas,tests,references,assets}/ 와 docs/claude/redesign-t1-* 안뿐인가.
   workspace/policies/*, stock-strategy-system/*, CLAUDE.md, .gitignore, .claude/ 변경 0인가.
J2 compare 모드: auto_core.py·auto_core_reconcile.py에서 mode="compare"(또는 설정 파일 없음)일 때 portfolio_state.json·
   reconciliation_ledger.jsonl·decision_journal.json·backups/ 에 쓰는 경로가 하나도 없는가(쓰기 허용: workspace/outputs/auto-core/,
   workspace/private_inputs/cash_flow_evidence/ 정규화본).
J3 apply 모드: I1~I5 전부 PASS, 거래내역 증거 OK, kill_switch=false, commit_sha 있음, guarded 파일 미커밋 수정 없음 —
   하나라도 어긋나면 쓰지 않는가. apply_auto_core가 같은 조건을 다시 검사하고 쓰기 직전 상태를 다시 해시하는가.
J4 체결 추정 없음: 수량은 브로커 체결 조회(ust21150 cntr_qty), 금액·수수료는 ust21610에서만. 가격·종가·평가금액으로 수량이나
   체결을 만드는 경로가 없는가.
J5 주문 경로 없음: 새·바뀐 코드에 /api/us/ordr, ust2000x, overseas orders, 주문 도구 이름이 없는가. kiwoomcli 호출은
   overseas candles stock-minute 하나이고 --profile <정책 별칭> --mode real 인가.
J6 현금: available_cash_usd = fc_ord_alowa, 검사는 (ord − pymn > 1 → 같은 조회에 qty > poss_qty 행 필요)와 (ord < pymn − 1 → 막음) 둘뿐,
   fc_entra 비교 없음. verified_orderable_cash_from_expected_proceeds_usd 상수 0 유지(judge_continuous_improvement_sidecar.py·
   judge_portfolio_reallocation_shadow.py의 == 0 검사 통과). 대시보드 매수 자금 상한(portfolio_decision_dashboard.py funding_cash)
   코드 무변경.
J7 불변 필드·기록: 보유·현금·평단·원가·브로커 기록 외 필드(stage, timing_plan, 체결 기록, 후보, 전략 칸) 불변. 원장 줄
   confirmation_method=AUTO_CORE_INVARIANTS, confirm_code=null, 해시 사슬·백업 연속, CRLF 보존. 출력·로그에 계좌 식별자 없음.
J8 사람 경로 회귀 없음: reconcile_broker_state.py propose/show/apply와 CONFIRMATION_METHODS가 그대로이고, 사람 apply가
   AUTO 방식 제안을 거부하는가.
J9 고정 은퇴(F6): 0단계 a의 "런타임에서 고정 해시를 요구하는 코드가 없다"를 grep으로 직접 확인. pin scope status RETIRED,
   apply 모드에서 guarded 경로(옛 27 + 코어 파일) 미커밋 수정이면 읽기 전에 FAIL 하는가.
J10 테스트: tests/test_auto_core.py 54건과 바뀐 테스트 5개 파일을 직접 실행. 바뀐 고정 테스트 3개·픽스처 4곳이 뜻을 약화하지 않고
   정확히 다시 잠갔는가(assert 삭제·완화·skip 추가 없음). 테스트 수 감소 0. 전체 스위트는 test-runner 서브에이전트로 돌려
   실패 id 집합이 기준선(Builder 보고 0단계 e의 29개)과 같은지 직접 비교(서브에이전트 출력은 위치 정보, 숫자는 직접 셈).
J11 Builder 판단 1~7 각각 수용/거부: 특히 4번(POST_APPLY_ALERT_ENGINE_CHECK_FAILED·POLICY_POSITIONS_MISMATCH·
   TIMING_PLAN_TICKER_CHANGED 경고가 apply를 막지 않음)은 옛 경보 엔진·옛 정책 앵커(SOXL 75 등) 때문에 자동 기록이 영구 HOLD되는
   것을 피하는 선택인지, 아니면 실제 위험을 놓치는지 판단해 조건을 적는다.
J12 Windows 스크립트: run_auto_core.ps1·register_auto_core_task.ps1·collect_30m.ps1이 ASCII, Interactive·Limited(관리자 권한 없음),
   실행 제한 60분, 주문·계좌 쓰기 명령 없음, 등록 스크립트가 다른 작업을 지우거나 덮지 않는가.

J13 r2(docs/claude/redesign-t1-builder-r2-2026-10-10.md, worktree 안): ① I3 금액·수수료가 실제 정산 금액(예수금 상세 dN excta /
   거래내역 fc_exct_amt)이고 ust21610 cmsn_altx를 $1 검사에 쓰지 않는가(실측 M1·M2 픽스처로 PASS) ② I3 기준 현금이 마지막 원장 줄과
   연결된 스냅샷의 order_available_cash이고, 못 찾으면 HOLD(상태 현금으로 대체 안 함) ③ 자료 없음 문구 2개가 측정값과 글자까지 같고,
   cntr_qty 0 무효주문 행이 체결 0으로 처리되는가 ④ 기록 전 체결의 결제 행이 기록 뒤에 나와도 현금을 두 번 세지 않는가.
   ⑤ Builder 보고 r2-4 판단 1~6(결제일별 연속 배정, "결제일 > 체결 KST 날짜" 규칙, d3·d4 조회 칸 추가, 기준 시각, create-once 스냅샷 사본,
   수수료 범위) 각각 수용/거부 ⑥ r2-5 위험 1(D0 결제 당일 HOLD)이 비교 모드 streak를 끝없이 늦출 수 있는지 — 늦춘다면 조건으로 적는다.

알려진 후속(병합 차단 아님 — 판정에 의견만): ① .claude/settings.json deny에 auto_core.py·reconcile_broker_state.py auto 실행 추가
② test_reconcile_broker_state.test_agent_rules_require_snapshot_and_user_confirmation 기대 문구를 2026-10-10 CLAUDE.md 새 문구에 맞춤.
둘 다 apply 모드를 켜기 전에 처리한다(관제판 redesign-t1b).

판정 보고(한국어, 짧게): 맨 위 한 줄 PASS | PASS-WITH-CONDITIONS | FAIL. 그다음 J1~J12 표, 조건(있으면 번호), FAIL이면 최소 수정
목록(같은 Builder worktree에서 고칠 것). 보고 외 파일 생성·수정 금지.
```
