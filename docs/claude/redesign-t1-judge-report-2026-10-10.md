---
id: redesign-t1-judge-report-2026-10-10
title: 재설계 T1 독립 Judge 판정 — 자동 운영 코어 v1 (r2 포함)
date: 2026-10-10
class: 권한·한도 변경(옛 K3) — 독립 Judge
judge_prompt: docs/claude/redesign-t1-judge-prompt-2026-10-10.md
target: .claude/worktrees/auto-core-t1 (base 74ad71e, 미커밋 — 수정 19 + 새 파일 11)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: Cowork(병합 판단) · 관제판 redesign-t1 / redesign-t1b
---

# PASS-WITH-CONDITIONS

- 병합은 막지 않는다. compare 모드는 상태·원장·일지·백업에 쓰지 않는다(J2). 조건 C1~C3·C5·C6은 apply 모드를 켜기 전(redesign-t1b), C4는 비교 기간 안("켜" 판단 전)에 처리한다.
- 확인 방법: Builder 보고는 증거로 쓰지 않았다. 코드·`git diff 74ad71e`·테스트를 직접 확인했다. 키움 조회·kiwoomcli·`auto_core.py daily`·`reconcile_broker_state.py auto/apply`는 실행하지 않았다. 테스트는 가짜 데이터만 썼다. 예외 1건: rev 24 기준 스냅샷 연결을 파일 읽기로만 확인했다(프로젝트 코드는 실행하지 않았고 금액은 출력하지 않음).

## 판정표

경로는 `manage-us-stock-strategy/scripts/` 기준이고, 다른 위치만 따로 적었다. 근거 줄 번호는 worktree 파일 기준이다.

| # | 판정 | 근거 |
|---|---|---|
| J1 범위 | PASS | 추적 변경 19 + 새 파일 11이 모두 `manage-us-stock-strategy/{scripts,schemas,tests,references,assets}/`와 `docs/claude/redesign-t1-*` 안에 있다. `workspace/policies/*`·`stock-strategy-system/*`·CLAUDE.md·.gitignore·.claude/ 변경 0(무시 파일 portfolio_state.json·alert_runtime_state.json·.claude/settings*.json의 해시가 메인과 같음). **줄바꿈만 다른 파일 0**(`--numstat`과 `--ignore-cr-at-eol --numstat` 결과 동일). 수정 파일은 작업 트리 CRLF를 유지했다(줄 수 = CRLF 수). 원본 `workspace/outputs/regular-session-closes/collect_30m.ps1` sha256 9717579c…도 그대로다. |
| J2 compare | PASS | `apply_auto_core`를 부르는 곳은 auto_core_reconcile.py:950(`mode=="apply"`) 한 곳뿐이다. 그 밖의 경로는 :961에서 상태 해시를 다시 확인한 뒤 반환한다. 설정 파일이 없으면 compare로 강제한다(reconcile_broker_state.py:355). compare 쓰기는 `workspace/outputs/auto-core/<날짜>/`(스냅샷·create-once 사본·제안·reconcile/result), LATEST.json, 증거 정규화본(:881)뿐이다. F5가 지정한 종가 pages/history와 exposure-review 1파일은 상태·원장·일지·백업이 아니다(일지는 `load_journal` 읽기만 함). 테스트: tests/test_auto_core.py:840, :893. |
| J3 apply | PASS (조건 C1) | 조건 하나만 어긋나도 쓰지 않는다. kill_switch와 guard는 읽기 전에 막고(reconcile_broker_state.py:356-358), I1~I5 실패·증거 HOLD·제안 BLOCKED는 `recordable`에서 막는다(auto_core_reconcile.py:945). 쓰기 직전에 파일 해시를 다시 잰다(:952). 라이브러리도 다시 검사한다: I1~I5 전부 PASS + 집합 일치(apply_user_confirmed_broker_snapshot.py:388), I3 baseline(:393), 40자 SHA(:396), mode=apply(:398), revision·해시·만료·사슬·원장 해시 = 상태(:434), 백업 뒤 바이트 재비교(:326). **다만 kill_switch·guarded dirty·증거(선언 블록)는 라이브러리에서 다시 보지 않는다** → C1. InvariantFailureTests 13건이 apply 모드에서 상태·원장·백업이 바뀌지 않음을 assert한다. |
| J4 체결 추정 없음 | PASS | 수량은 ust21150 `cntr_qty`에서만 오고(auto_core_reconcile.py:250-254), 기록하는 값은 브로커 poss_qty·fc_ord_alowa·frgn_stk_book_uv다. r2 뒤 금액은 dN excta(:355)와 거래내역 fc_exct_amt(:386)에서 오고, ust21610은 수량 묶기와 총액 범위 검사에만 쓴다(:336-343). `cntr_uv`는 표시용 `price` 칸에만 저장되고 수량·현금 계산에는 쓰이지 않는다. 종가·평가금액 참조 0. |
| J5 주문 경로 없음 | PASS (메모 C6) | 새 조회 3개는 모두 `/api/us/acnt`(ust21100·21150·21610)이고, 요청 인자는 날짜만 받는다(DATED_PARAMETERS + YYYYMMDD, 워커 쪽도 `validate_request`). 바뀐 코드에서 `ordr`·`ust2000x`·`overseas orders`·주문 도구 이름 grep 결과 0. kiwoomcli 호출은 collect_30m.ps1:44 `overseas candles stock-minute` 하나다. auto_core는 정책 별칭(현재 "실전계좌")을 넘겨 `--profile … --mode real`로 부른다. 다만 별칭이 빈 문자열이면 두 플래그가 빠진다(:37) → C6. |
| J6 현금 | PASS | `available_cash_usd` = `order_available_cash`(= fc_ord_alowa, kiwoom_broker_shadow.py:381). 검사는 둘뿐이다(:262 주문가능 < 출금가능 − 1 막음, :264 주문가능 − 출금가능 > 1이면 같은 조회에 qty > poss_qty 행 필요). fc_entra는 표시용 deposit 칸에만 들어가고 비교에는 안 쓴다. 예상 매도대금 상수 0(continuous_improvement_sidecar.py:150·619, portfolio_reallocation_shadow.py:589)과 judge_* `== 0` 검사는 바뀌지 않았다. 대시보드 `funding_cash`(portfolio_decision_dashboard.py:1470)도 바뀌지 않았고, 스냅샷 `settled_available_cash` = min(출금가능, 주문가능)(kiwoom_broker_shadow.py:82)도 그대로라 매수 자금 상한은 변하지 않는다. |
| J7 불변 필드·기록 | PASS | 쓰기 공통 경로 `_write_applied`가 WRITTEN_STATE_FIELDS 밖의 모든 칸에 `_assert_untouched`를 걸고, NEVER_TOUCHED 목록은 그대로이며, I5 미리보기도 있다. 원장 줄은 confirmation_method=AUTO_CORE_INVARIANTS, confirm_code·user_message=null(:448)이고, previous_entry_sha256 사슬, 백업 `xb`(:324), CRLF 감지(:321)를 갖춘다. 계좌 식별자: acnt_print를 수집하지 않고 새 SAFE_FIELDS에 계좌 칸이 없다(테스트 test_auto_core.py:883). |
| J8 사람 경로 | PASS | propose·show·apply·`resolve_proposal_path`·CONFIRMATION_METHODS의 diff 0. `apply_confirmed`는 AUTO_CORE_INVARIANTS를 CONFIRMATION_METHOD_INVALID로 거부하고(:278), CLI 선택지 2개도 그대로다(test_auto_core.py:996-1012). 메모: auto-core 제안 파일에도 파생 confirm_code가 들어 있어서, 사람 경로에 그 경로를 직접 주면 사용자 코드로만 적용할 수 있다. 전환기 대체 경로와 같은 동작이라 회귀는 아니다. |
| J9 고정 은퇴 | PASS (조건 C2) | grep 결과: 활성 acceptance 해시를 비교하는 곳은 `validate_kiwoom_session_aware_acceptance(_candidate).py`·`materialize_…`(재고정 도구) 안뿐이고, 이들을 부르는 곳은 서로와 테스트뿐이다. validate_source_capabilities.py:50은 64자 형식만 본다. scheduled_input_gate.py는 고정 대상이 아닌 배포 provenance를 쓴다. pin scope status는 RETIRED(파일 유지). apply 모드에서 guarded 파일이 미커밋 수정이면 읽기 전에 FAIL한다(reconcile_broker_state.py:358, 테스트 :901). guarded 집합 = 옛 27 + 코어 6인데, apply 경로가 쓰는 validation_common.py(해시·쓰기)·kiwoom-broker-shadow.schema.json·evaluate_alerts.py 등이 빠졌다 → C2. |
| J10 테스트 | PASS | 직접 실행 결과: test_auto_core **69건 OK**(지시문의 54건 + r2 15건). 바뀐 5개 파일: cash_flow_evidence 19 OK, kiwoom_broker_shadow 24 OK, s1b_plan_b 30 OK, reconcile_broker_state 56(실패 1 = 기준선 test_agent_rules), materialize 26(실패 2 = 기준선 E1·F3). `def test_` 수 감소 0. 고정 테스트 3개·픽스처 4곳: 정확 집합 equality를 유지한 채 확장했고, assert 삭제·완화·skip 추가 0, 픽스처는 기대값을 그대로 둔 채 주문가능 = 출금가능으로 맞췄다. 전체 스위트(test-runner 실행, 원본 출력에서 직접 셈): `Ran 2564`, failures 20, errors 9 → FAIL/ERROR 29건이 기준선(문서 27 + 0단계 e 2)과 **같은 집합**(새 0, 사라짐 0). 기준선에 덧붙은 2건은 바뀌지 않은 입력(CLAUDE.md·AGENTS.md, 무시된 상태 파일)에 의존한다. 스키마 감사 PASS. |
| J11 Builder 판단 | 1~7 수용 | 4번은 조건 C3, 1번은 메모 C5. 아래 "Builder 판단" 절. |
| J12 Windows | PASS | ps1 3개의 비ASCII 줄 0. 등록 스크립트: Interactive·Limited(register_auto_core_task.ps1:81), 실행 제한 60분(:78), 화~토 06:15, 시간대가 KST가 아니면 등록하지 않음, `-Force`는 자기 이름 InvestmentV2-AutoCore에만(:89). Unregister나 다른 작업 조작 없음. 주문·계좌 쓰기 명령 없음(collect_30m.ps1의 Remove-Item은 방금 받은 불량 페이지 파일만 지움). |
| J13 r2 | PASS (조건 C4) | ① `cmsn_altx`는 주석 말고는 쓰이지 않는다. M1(차이 −0.01)·M2(0.00) 테스트 통과. ② `baseline_snapshot`(auto_core_reconcile.py:708-759)은 원장 마지막 줄 → 제안 → 스냅샷 해시 → 상태 evidence_sha256 일치를 요구하고, 실패하면 `BASELINE_ORDER_AVAILABLE_UNKNOWN` HOLD이며 상태 현금으로 대체하지 않는다(테스트 4종). 실제 rev 24도 파일 읽기로 연결을 확인했다(제안 찾음, 해시 3곳 일치, order_available_cash 있음, generated_at 23:52:05Z). ③ 자료 없음 문구 2개가 r2 측정값과 문자 단위로 같다(비교 True). 다른 문구나 코드 한 자리 차이는 계속 오류다. cntr_qty 0 행은 :254에서 시각을 읽기 전에 건너뛴다. ④ flow_cash는 TRADE를 건너뛰고(:554), 기록 뒤 체결이 없으면 0이며(:455), 첫 체결의 KST 날짜 이하인 칸·행은 뺀다(:463, :479). ⑤ 판단 1~6 수용. ⑥ 늦출 수 있다 → C4. |

## Builder 판단 (J11 1~7, r2-4 1~6)

| 판단 | 결과 | 이유 |
|---|---|---|
| 1 실행 순서 | 수용 | 15분 만료와 첫 수집 시간이라는 근거가 맞고, 30분봉 실패가 대조를 막지 않는다. 메모: 30분봉·노출 단계에서 FAIL한 날도 그 전에 계산한 streak가 result.json에 남아 다음 날 이어진다 → C5 |
| 2 증거 기간 period_to 당일부터 | 수용 | 겹친 행은 `settled_keys`로 중복 제거된다(cash_flow_evidence.build_declaration) |
| 3 ust21100 501724 0건 인정 | 수용 | S7 U3 측정 문구와 글자까지 같다(tests/test_cash_flow_evidence_u3.py:27) |
| 4 경고 3종 비차단 | 수용 (조건 C3) | 세 경고 모두 상태 정합성이 아니라 "브로커 사실 ↔ 전략 칸(timing_plan 앵커·alert_policy positions)" 차이다. 상태 정합성 경고(STATE_CHANGED_OUTSIDE_LEDGER·LEDGER_INTEGRITY_FAILED)는 I4가 막는다. 전략 칸은 스냅샷으로 바꾸지 않는 규칙이라, 이 경고로 막으면 타이밍 종목 체결이 있을 때마다(지금도 SOXL 앵커 75 vs 53) 정책을 고치기 전까지 자동 기록이 영구 HOLD된다 → 자동화 목표 위반. 남는 위험은 옛 앵커 때문에 경보 엔진이 STATE_MISMATCH/F로 떨어지는 fail-closed 쪽이고 노출 증가가 아니다. **다만 지금은 경고가 result.json·LATEST.json에 실리지 않아(reasons에 안 들어감) 06:40 로더가 보지 못한다** → C3 |
| 5 auto_apply const false | 수용 | 자동 표시는 원장 줄 `auto_core`·confirmation_method와 authority_state가 맡는다 |
| 6 고정 테스트 3개 | 수용 | J10 |
| 7 픽스처 4곳 | 수용 | J10 |
| r2-1 결제일별 연속 배정 | 수용 | 애매하면 HOLD이고, 현금 합계는 배정과 무관하다 |
| r2-2 결제일 > 체결 KST 날짜 | 수용 | 메모: 기준 뒤 세션이 KST 자정 전에만 체결됐고, 같은 종목·방향·같은 수량의 기준 전 체결이 있으면 결제 행을 잘못 배정할 수 있다. 그래도 결과는 HOLD이거나 $1 안의 우연 일치이고, 기록하는 값은 브로커 값이라 허용한다 |
| r2-3 d3·d4 조회 칸 | 수용 | 조회 허용 필드만 늘렸고 권한은 바뀌지 않는다 |
| r2-4 기준 시각(I3 generated_at / I2 as_of) | 수용 | 그 사이 체결은 HOLD 쪽으로만 틀린다 |
| r2-5 create-once 사본 | 수용 | 같은 날 재실행 뒤에도 사본이 유지된다(테스트) |
| r2-6 수수료 범위 | 수용 | M1 2.21 / 한도 15.87, M2 2.25 / 한도 16.63 |

## 조건

- **C1 (J3, apply 켜기 전)**: `apply_auto_core`가 쓰기 직전에 다음 셋을 다시 확인한다. ① auto_core.json을 다시 읽어 kill_switch=false·mode=apply ② provenance를 다시 계산해 guarded_dirty_paths가 비어 있음 ③ 제안에 cash_flow_declaration이 있고 status가 NO_EXTERNAL_FLOW 또는 DECLARED_IN_FULL. 셋 각각이 어긋날 때 쓰지 않음을 확인하는 테스트를 함께 넣는다.
- **C2 (J9, apply 켜기 전)**: apply 모드 guard를 apply 경로가 import하거나 읽는 추적 파일 전체로 넓힌다. 가장 단순한 형태는 `manage-us-stock-strategy/{scripts,schemas,assets}/` 아래 추적 파일에 미커밋 수정이 하나라도 있으면 FAIL하는 것이다. 최소한 validation_common.py·kiwoom-broker-shadow.schema.json·evaluate_alerts.py·portfolio_exposure.py·portfolio_review_journal.py는 포함한다.
- **C3 (J11-4, apply 켜기 전)**: 제안 warnings와 post_apply_checks.errors를 result.json·LATEST.json(예: `warnings[]`)에 싣는다. 06:40 로더는 경고가 붙은 기록(`applied` ≠ null)이 있으면 한 줄 푸시한다. 기록은 계속 막지 않는다.
- **C4 (J13-⑥, 비교 기간 중, "켜" 판단 전)**: D0 HOLD가 streak를 끝없이 늦출 수 있다. compare 모드는 상태를 쓰지 않아서 I3 기준이 rev 24(또는 마지막 사람 경로 기록)에 고정된다. 그 뒤의 모든 체결이 자기 결제일 06:15 실행에서 한 번씩 SETTLEMENT_* HOLD를 내고, 그날 streak는 0이 된다(TODAY_NOT_OK). 체결이 2~3거래일마다 있으면 streak가 3에 닿지 못한다(사람 경로 기록이 매일 이어지면 완화됨). 또 사람 경로 기록 없이 13일이 넘으면 FILL_WINDOW_TOO_LONG으로 FAIL한다. 고칠 것(택 1, 테스트 포함): (a) 결제일이 오늘(KST)인 몫을 전날 실행이 기록한 같은 결제일 PENDING 금액(reconcile.json I3.settlements)으로 설명한다. (b) 사유가 D0 결제 미표시뿐인 날은 streak를 유지하고(+1 없음) 사유를 남긴다.
- **C5 (J11-1, 경미, apply 켜기 전)**: 30분봉이나 노출 단계에서 FAIL한 날은 streak를 올리지 않는다. 또는 "기록 모드 켤 준비됨"을 최근 N일 result status가 FAIL이 아닐 때만 낸다. T1 완료 기준 "3거래일 연속 무인 실행"과 맞추려는 것이다.
- **C6 (J5, 경미, apply 켜기 전)**: `token_profile_alias`가 비었거나 없으면 auto_core가 수집 전에 FAIL하게 하거나, collect_30m.ps1의 -KiwoomProfile을 필수로 만든다. 키움 조회 규칙(프로필 필수)을 코드로 보장하려는 것이다.

## 알려진 후속에 대한 의견 (병합 차단 아님)

1. `.claude/settings.json` deny: 동의한다. `auto_core.py` 실행 전체와 `reconcile_broker_state.py auto`를 Bash·PowerShell 양쪽 deny에 넣는다. compare도 키움 실조회를 하므로, Claude Code·Codex·Judge 세션의 실행을 막는 데 의미가 있다. apply를 켜기 전에 필수로 처리한다.
2. `test_agent_rules_require_snapshot_and_user_confirmation`: 동의한다. 기대 문구만 2026-10-10 CLAUDE.md·AGENTS.md 문구에 맞추고 뜻(스냅샷 + 사용자 확인, 또는 불변 조건 자동 경로)은 유지한다. 이 실패는 기준선 29건 안에 있다.
3. (추가 메모) 정책 제안 파일의 `.gitignore` 한 줄(`workspace/outputs/auto-core/`)을 적용하지 않으면 메인 체크아웃 status에 생성물이 쌓인다. `git_provenance`는 이 경로를 dirty에서 빼므로 guard에는 영향이 없다.

## FAIL 시 최소 수정 목록

해당 없음(FAIL 아님). 위 조건 C1~C6을 같은 Builder worktree 또는 redesign-t1b에서 고친다.
