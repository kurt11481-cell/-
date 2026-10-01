# S6 Independent Judge 지시문 — S5 손실한도·노출 정책 확정안 (2026-10-01)

- 대상: `docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md`의 "S5 확정안" 절(R1~R9)과 5절 diff. 커밋 `7916924`, 문서 blob `67fc0d13…`.
- 성격: K3 정책 심사. 코드 변경 없음. Judge는 파일을 고치지 않는다. 정책·상태 파일은 바꾸지 않았다.
- 기준값(2026-10-01 Cowork 확인): `alert_policy.json` 원본 sha256 `184008bd…0488`, LF 정규화 `4a7c1492…0cf2`, git blob `3d9df21a…`. `portfolio_state.json` 원본 `28fd77c5…70b5`.
- 8절 Judge 질문 4(ETF 코어)·5(F1.32 shadow)는 D1c·D2로 대상이 없어졌다. 이 지시문의 J4·J5가 대신한다.
- 상태: 작성 완료, Judge 미실행.

## 1. 사용자 조작

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `judge-s6` · 이유: K3 Independent Judge(위험 예산·권한 근거 심사), 파일 수정 없음**

1. 새 Windows 터미널에서 `cd "E:\사업\##금동한\코덱스저장소"`를 입력한다.
2. 문서 3개를 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/s6-judge-prompt-2026-10-01.md docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md docs/claude/handover-loss-limit-review-2026-10-01.md`
   `git commit -m "docs: S6 judge prompt for S5 policy proposal"`
3. `claude --worktree judge-s6`를 입력한다.
4. 세션 안에서 `/model`로 Opus, `/effort`로 xhigh를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/s6-judge-prompt-2026-10-01.md 3절 상자 안의 지시를 그대로 따르는 S6 Judge로 일해라. 그 밖의 절은 참고만 한다.`
6. Judge가 끝나면 마지막 "S6 판정" 블록만 복사해 Cowork에 붙여 넣는다.

- 권한 확인 창: 읽기·`git log`/`git show`·`python` 해시 계산은 허용한다. 파일을 쓰거나 고치려는 요청은 거부한다.
- 2번 커밋은 제안서 12절의 진행 기록 한 줄만 바꾼다. Judge의 0단계가 이 차이만 있는지 확인한다.

## 2. Cowork 사전 점검 (Judge 판정 아님, 읽기 전용)

Judge가 직접 다시 확인한다. 같은 내용이 3절 지시문에도 들어 있다.

| # | 발견 | 근거 |
|---|---|---|
| P1 | 제안서의 `risk_overlay_rules.*`, `new_buy_activation.*`는 실제로 `holding_timing_rules.` 아래에 있다 | `alert_policy.json` 키 탐색 |
| P2 | 현행 `return_seeking_rules_blocked`에 "peak drawdown exits", "dynamic leverage cap"이 있다. diff #8은 S5 노출 정책·검토선을 안전 면제 목록에 넣고, 폐기된 "F1.32 promotion"을 차단 목록에 넣는다 | `holding_timing_rules.risk_overlay_rules.walk_forward_activation_gate` |
| P3 | 현행 `peak_drawdown` 초안은 승인된 활성화 시점 뒤 종가 기준, 기존 보유 소급 없음, 5년 OOS + forward shadow 게이트. diff R5는 보유 시작 뒤 고점(소급), `active_review_only` | 같은 파일 `peak_drawdown` |
| P4 | 낡은 초안 부분: 8절 질문 4·5, 4절 표 #7(superseded ↔ R7 재사용), 0절 4항(1.9 폐지 ↔ D3 유지), `portfolio_review_lines.policy_version`이 "s5-draft" | 제안서 0·4·5·8절 |
| P5 | 9/30 구성(SOXL 39.4%·MVLL 49.8%·NBIS 10.8%)은 명목 2.285, V 약 2.80(D)로 절대 상한 1.9 위다. 줄이기 기본은 SOXL, 초과의 대부분은 매도 전용 MVLL(명목 약 1.0 > 종목 상한 0.4) | 제안서 6.1절, diff |
| P6 | `nominal_multipliers.default_unlevered = 1`이 목록 밖 상품 전부에 적용된다. 새 레버리지 상품을 1배로 셀 수 있다 | diff |
| P7 | V의 가격 출처가 없다(`split_adjusted_daily_close`만). 키움 일봉 종가는 시간외가 섞이고(MVLL 카드 정정), Yahoo는 참고(D) | diff, `mvll-holding-card-2026-10-01.md` |
| P8 | `deployment_gate`가 `evaluate_alerts.py`·`timing_engine.py`·`SKILL.md`·`build_market_snapshot.py`·`references/yfinance-data.md`·`assets/locales/ko-KR.json`을 LF 정규화 해시로 고정한다(10-01 현재 일치). `holding_risk_rules`를 읽는 스크립트 8개 중 `evaluate_alerts.py`, slots를 읽는 `timing_engine.py`가 고정 대상. 두 키를 읽는 테스트 파일 11개. `decision_journal.json`은 없다 | 해시 대조, grep |

## 3. 붙여넣기용 지시문

```text
역할: S6 Independent Judge (K3). 대상은 S5 손실한도·노출 정책 확정안(문서)이다. 코드 변경은 없다.
금지: 저장소 파일 수정·생성·삭제·커밋·브랜치 변경, 키움 도구, 주문 도구, .env*·토큰·계좌번호 읽기, 네트워크 조회.
허용: 파일 읽기, git 읽기 명령(log/show/diff/rev-parse/ls-files/grep), 시스템 임시 폴더에서 읽기 전용 python(해시·산술·결과 JSON 읽기).
git 제외 상태 파일(portfolio_state.json, alert_runtime_state.json)이 worktree에 없으면 E:\사업\##금동한\코덱스저장소\stock-strategy-system\ 에서 읽기만 한다.
없는 수치는 만들지 않는다(확인 필요 / NOT VERIFIED). 보고는 한국어, 식별자는 영어.

0. 기준 확인(다르면 멈추고 보고)
   - HEAD가 7916924이거나 그 자손. git rev-parse 7916924:docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md = 67fc0d13...
     HEAD가 7916924가 아니면 git diff 7916924 HEAD -- docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md 가 12절 진행 기록 줄 추가뿐인지 확인한다.
   - alert_policy.json: git blob 3d9df21a..., LF 정규화 sha256 4a7c1492...0cf2(원본 폴더 raw 184008bd...0488). portfolio_state.json 원본 raw 28fd77c5...70b5.
1. 읽을 것
   - 제안서: "S5 확정안" 절, 5절 diff, 7·8·9절, 부록 C.6~C.13. 0~3·6절은 이력이고 확정안이 우선한다.
   - stock-strategy-system/alert_policy.json: holding_risk_rules, holding_timing_rules(positions, new_buy_activation, risk_overlay_rules), cash_policy, deployment_gate, broker_snapshot_max_age_calendar_days
   - docs/claude/loss-limit-review-s5-prep-decisions-2026-10-01.md, docs/claude/s4-3-builder-report-2026-10-01.md,
     stock-strategy-system/backtests/LEVERAGE_UP_RESULTS_2026-10-01.md, leverage_up_2026-10-01_results.json
   - CLAUDE.md, docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md §2-1, manage-us-stock-strategy/references/broker-snapshot-reconciliation.md(R6 관련만)
   - 코드: 위 키를 읽는 scripts를 grep으로 직접 찾는다. 특히 evaluate_alerts.py, timing_engine.py, reconcile_broker_state.py, portfolio_policy_gates.py
2. 상위 규칙(이 세션에서 읽을 수 없는 Project 지식 요약, Cowork 제공)
   - 우선순위: 최신 사용자 명시 안전·권한 승인 > 검증된 Production Runtime/Authority > Constitution > 승인된 Portfolio/Strategy 정책 > 지침 > 연구. RESEARCH_FINDING != PRODUCTION_POLICY.
   - Constitution: Hard Safety 실패는 기대수익으로 상쇄하지 않는다(§2). 정책 변경 lifecycle(VALIDATION → OOS → SHADOW → JUDGE → PROPOSAL → USER APPROVAL)은 변경 규모·권한 영향에 비례해 적용한다(§20). NO_CHANGE도 정상 결과(§21). 등급 A~D, D는 가설용(§22). SHADOW != ACTUAL, EXPECTED PROCEEDS != BROKER CASH(§23). 복잡도는 미충족 요구 + 검증 가능한 이익이 있을 때만(§24). 키움이 canonical, 가격 평균 금지(§30). order_authority=false, quantity_authority=none(§31).
3. Cowork 사전 점검 P1~P8은 단서다. 직접 확인해 CONFIRMED / REJECTED로 적는다.
   P1 제안서의 risk_overlay_rules.*, new_buy_activation.*는 실제로 holding_timing_rules. 아래에 있다.
   P2 현행 walk_forward_activation_gate.return_seeking_rules_blocked에 "peak drawdown exits", "dynamic leverage cap"이 있다. diff #8은 S5 노출 정책·검토선을 safety_only_controls_exempt_from_return_gate에, 폐기된 "F1.32 promotion"을 차단 목록에 넣는다.
   P3 현행 peak_drawdown: anchor_source "prospective completed closes after an explicitly approved activation anchor", existing_holdings_retroactive_application false, activation_gate "five-year stitched out-of-sample acceptance plus forward shadow validation". diff R5: peak_basis "regular_session_close_high_since_holding_start_rearm_on_new_high", status "active_review_only".
   P4 낡은 부분: 8절 질문 4·5(대상 없음, J4·J5로 교체), 4절 표 #7 superseded ↔ R7 재사용, 0절 4항 1.9 폐지 ↔ D3 유지, portfolio_review_lines.policy_version "2026-10-01-s5-draft".
   P5 9/30 구성 SOXL 39.4%·MVLL 49.8%·NBIS 10.8%: 명목 2.285, V 약 2.80(D) > 1.9. reduce_order_default ["SOXL"], MVLL은 sell_only이고 명목 약 1.0 > single_stock_nominal_cap 0.4.
   P6 nominal_multipliers.default_unlevered 1이 목록 밖 상품 전부에 적용된다(새 레버리지 상품을 1배로 셀 수 있음).
   P7 V 가격 출처가 없다. 키움 일봉 종가는 시간외가 섞인다(docs/claude/mvll-holding-card-2026-10-01.md 정정). Yahoo는 참고(D).
   P8 deployment_gate가 evaluate_alerts.py, timing_engine.py, SKILL.md 등 6개를 LF 정규화 해시로 고정한다. holding_risk_rules를 읽는 evaluate_alerts.py, slots를 읽는 timing_engine.py가 고정 대상이다. decision_journal.json은 없다.
4. 판정 항목
   J1 안전 통제 분류: 확정안을 수익 게이트(walk_forward_activation_gate)에서 면제할 수 있는가. 줄이기·절대 상한·검토선·멈춤(위험 축소)과 채우기 권고(E <= 1.25, 수익 추구)를 같은 묶음으로 면제해도 되는가, 나눠야 하는가. 현행 차단 목록의 "dynamic leverage cap"·"peak drawdown exits"와의 관계를 정리한다.
   J2 권한 근거: soxl_only_result_can_validate_live_portfolio_cap=false를 유지한 채 authority_basis "user_approved_risk_budget_not_validated_portfolio_return"으로 1.55를 쓰는 것이 우선순위에 맞는가. 비교 기준 두 개를 모두 적는다: 현 상태(노출 정책 없음, 실제 E 약 2.8) 대비, 검증 범위(1.32) 대비.
   J3 현행 키 정리(R7, diff 기존 키 #1~#8): 경로가 실제와 맞는가. hard-risk 경로, deployment_gate 고정 해시, 키움 acceptance 고정 파일에 주는 영향. 변경마다 K 등급과 영향받는 테스트 파일.
   J4 구성(R3): 카드 종목 코어 + SOXL 보충이 S4-3 근거(SOX 단일, ETF 코어 I1) 밖이라는 점이 표시됐는가. 종목당 0.4배, 실적 금지 구간, MVLL 매도 전용, SOXX 측정 전용, 종목 간 되돌리기 표시 전용이 diff에 모순 없이 들어갔는가.
   J5 K132-G 보고 전용 가상 운용(R8): 실제 원장과 분리, policy_effect none, 승격 경로 없음이 SHADOW != ACTUAL을 지키는가. Cold Path 실패가 Hot Path를 막지 않는가.
   J6 fail-closed: 데이터 누락, 원장 없음, 입출금 미신고, V 계산 불가·이력 60 미만, 대조 지연(4일 초과), 미등록 상품(P6), V 가격 출처(P7), HWM 종가 출처(16:00 표기 30분봉 ↔ 공식 종가). 경로마다 신규 매수·채우기 권고가 멈추는지. 빈틈은 fail-open으로 적는다.
   J7 기각 후보 사후 완화 없음, 1.9 절대 상한 유지(바꾸려면 별도 사용자 승인 + Judge)가 diff에 정확히 들어갔는가.
   J8 1.55를 검증 범위 밖·forward shadow 없이 S7에서 바로 쓰는 처리의 기록 방식과 위험 고지(확정안 "감수 위험", 부록 C.6)가 충분한가. 하루 -20%(L2) 가능, SOX 1994~2010 연 0.2%, 2010~ 최대 낙폭 -64%가 결정 전에 고지됐는지(진행 기록 12절 순서로 본다).
   J9 일관성: 확정안 R1~R9 ↔ 5절 diff ↔ 현행 경로. 어긋남을 모두 적고, "확정안 우선" 문서 규칙으로 해소되는 것과 S7 승인 전에 고쳐야 하는 것을 나눈다.
   J10 R5 기준점(P3): 소급(보유 시작 뒤 고점)과 전향(활성화 뒤) 중 무엇이 맞는가. 소급이면 보유 시작일·종가 이력의 출처가 있는가. 없을 때 fail-closed 경로는.
   J11 S7 전환(P5): 적용일에 E가 1.9 위면 무엇이 표시되는가. 줄이기 기본 SOXL과 MVLL(매도 전용, 종목 상한 초과)의 순서 때문에 의도와 다른 권고(MVLL을 두고 SOXL부터 줄이기)가 나올 수 있는가. 필요한 최소 규칙을 제안한다.
   J12 숫자: L1~L4 금액 산술(HWM 28,473.94). 부록 C.6의 1.0·1.32 열은 S4-3 커밋 결과와, 1.55 열은 결과 JSON의 REF|fixed1.5와 정의(구현 core, 현금 0%, 비용, 조정 폭, 기간)가 같을 때만 비교한다. 다르면 "비교 불가". 부록 B·C의 미저장 탐색 수치는 재현하지 않고 D등급 표시가 맞는지만 본다.
5. 적대 점검(문서 수준): 이 정책이 현 상태보다 위험을 늘리거나 잘못된 매수 권고를 내는 경로를 찾는다. 예: 입출금 신고로 HWM을 움직여 선을 피하기, 짧은 이력으로 V가 작게 잡혀 채우기, 원장 없이 L2 멈춤 해제, 실적 금지 구간을 ETF로 우회.

판정 기준: PASS = 문서 그대로 S7 승인 질문 가능. PASS_WITH_FIXES = 문서 수정만으로 해소되고 사용자 새 결정이 필요 없음. FAIL = 사용자 결정 또는 설계 변경 필요.

출력: 마지막에 아래 블록 하나(45줄 이내). 앞에 긴 설명을 붙이지 않는다.
S6 판정
- 기준: HEAD <id>, 제안서 blob <id>, 정책·상태 해시 일치 여부
- 최종: PASS / PASS_WITH_FIXES / FAIL
- J1~J12: PASS/FIX/FAIL + 한 줄 근거(파일:행)
- P1~P8: CONFIRMED/REJECTED
- 필수 수정(S7 승인 전, 문서): 번호 목록
- S7 Builder 요구 사항(구현 때): 번호 목록
- 사용자 결정 필요: 질문 형태로(없으면 "없음")
- K 등급 요약: 변경별 K0~K3
```

## 4. 판정 뒤 처리

- PASS: Cowork가 S7 승인 질문을 한 번에 하나씩 묻는다 → 승인 뒤 S7 Builder 지시문(새 worktree, K3).
- PASS_WITH_FIXES: Cowork가 제안서를 고친다(문서) → 사용자 커밋 → 같은 Judge 세션에 "수정 커밋 <id> 재확인, 필수 수정 항목만"을 보낸다.
- FAIL: 사용자 결정 항목을 Cowork에서 하나씩 정한다 → 제안서 수정 → 재심사. 같은 항목이 2회 FAIL이면 Cowork(Opus · xhigh)에서 설계를 다시 본다.
- S7 전까지 실제 매매(MVLL 축소 등)는 사용자 수동 판단이다. 이 Judge는 주문·수량 권한을 만들지 않는다.

## 5. 진행 기록

- 2026-10-01 지시문 작성(Cowork, Opus). 사전 점검 P1~P8은 읽기 전용(정책 키 탐색, `deployment_gate` 해시 대조, grep). 정책·상태 파일 원본 해시 변경 없음.
- 2026-10-01 S6 판정 PASS_WITH_FIXES(HEAD `6ff8f25`, 문서 수정 14건, 새 사용자 결정 없음, P1~P8 CONFIRMED). 판정 요약과 필수 수정 반영 위치는 제안서 "S6 Judge 판정" 절. Cowork가 제안서를 r1로 고쳤다. 다음은 6절 재확인.

## 6. S6 재확인 지시문 (r1)

- 사용자 조작
  1. r1 문서를 커밋한다(Cowork가 명령 안내).
  2. Judge 세션이 열려 있으면 그 세션에 아래 상자를 붙여 넣는다.
  3. 닫혔으면 새 Windows 터미널에서 `cd "E:\사업\##금동한\코덱스저장소"` → `claude --worktree judge-s6-r2` → `/model` Opus, `/effort` xhigh → 아래 상자를 붙여 넣는다.
  4. 마지막 "S6 재확인" 블록을 Cowork에 붙여 넣는다.

```text
S6 재확인(K3 Judge). 저장소 파일 수정·생성·커밋·브랜치 변경 금지. 키움·주문 도구, .env*·토큰·계좌번호, 네트워크 금지.
허용: 파일 읽기, git 읽기 명령, 시스템 임시 폴더의 읽기 전용 python.
대상: codex/master-recovery-expansion 브랜치 끝 커밋(git log --oneline -1 codex/master-recovery-expansion).
브랜치는 바꾸지 않고 git show <커밋>:<경로>, git diff 6ff8f25 <커밋> 으로 읽는다.
1. 기준: 6ff8f25 → 대상 커밋 차이가 docs/claude 문서뿐인가. git rev-parse <커밋>:stock-strategy-system/alert_policy.json = 3d9df21a...인가.
   portfolio_state.json(E:\사업\##금동한\코덱스저장소\stock-strategy-system\) 원본 sha256이 28fd77c5...70b5인가.
2. 제안서(docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md) "S6 Judge 판정" 절의 필수 수정 1~14가
   "S5 확정안 r1" 절, 4·5·8·9·11절, 부록 C.6·C.9에 빠짐없이 반영됐는가. 항목마다 OK/부족(파일:행).
3. 같은 절의 S7 확인 항목 5~7(상품 등록·신규 매수 승인, DRAM 종목 상한, SOXL weakness_10ema 은퇴)이
   사용자 결정 D1~D7(제안서 10절, 부록 C.8~C.13) 범위 안인가, 새 사용자 결정이 필요한가.
4. r1에서 새로 생긴 모순이나 fail-open이 있는가(확정안 r1 ↔ 5절 diff r1 ↔ 현행 alert_policy.json 경로).
출력: 마지막에 "S6 재확인" 블록 하나(25줄 이내). 앞에 긴 설명을 붙이지 않는다.
- 대상 커밋, 기준 일치 여부
- 최종: PASS / FAIL
- 필수 수정 1~14: OK/부족
- 확인 항목 5~7: 범위 안/새 결정 필요 + 이유
- 새 문제: 없으면 "없음"
```
