---
id: redesign-t2-builder-prompt-2026-10-10
title: 재설계 T2 Builder 지시문 — 판정 규칙 코드화 · 주문표 자동 · 일지 자동
date: 2026-10-10
class: 권한·한도 변경(옛 K3) — 주문 1단계(ORDER_INTENT: 코어가 수량·LOC 가격을 낸 주문표, 입력은 사용자) 도입. 수동 경로(worktree Builder → 별도 독립 Judge)
decision: 사용자 2026-10-10 09:27 KST "재설계: A1 a … A7 a" (A7 a = 주문 1단계까지 확정) · docs/claude/automation-redesign-2026-10-10.md 3-2~3-6절·4절 T2
absorbs: oi-k3(지시 계산기) · oi-pilot-2(봉인 시범 폐지) · fx-2(v3.12.3 표시 변경) · r-ne1 · s-split-adj (관제판 2026-10-10 흡수 기록)
authority: 코어 주문표에만 quantity_authority = "ORDER_TICKET_HUMAN_ENTRY"(수량·가격 제시, 키움 입력은 사용자) · order_authority=false · execution_quantity=null · 키움 주문 도구·주문 API 금지 그대로. 일지·결과 파일·정책은 권한을 주지 않는다
inputs: docs/claude/redesign-t2-measurements-2026-10-10.json (Cowork 실측, 2026-10-10)
consumers: T2 Builder(worktree t2-core) · T2 Judge(Builder 보고 뒤 Cowork 작성) · 자동 운영 코어 decide 실행(07:45) · 06:40 통합 점검 로더(연구 기록 쓰기, 배포 때) · 자동 운영 코어 결과 알림 · 통합점검 대시보드 · 관제판 redesign-t2 · T4(LLM 판정 은퇴)
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `t2-core` · 이유: 주문 1단계(수량 권한)를 여는 권한·한도 변경이라 독립 Judge가 필요하고, 파일 여러 개에 걸친 설계다**

## 0. 한눈에

- 06:40 통합 점검(LLM이 82,682바이트 규칙 파일을 읽고 판정)의 **결정론 부분**을 코어 코드로 옮긴다(부록 A 분해표). 뉴스·공시 본문·호재 기준 (a) 같은 **LLM 판단**은 연구 작업에 남고, 그 결과는 정해진 형식의 "연구 기록" 파일로만 코어에 들어간다.
- 코어에 두 번째 실행 `auto_core.py decide`(화~토 07:45 KST)를 더한다: 판정 → 매수 요건 ①~⑥ → 관문 G0~G5 → 주문표(LOC, 수량·가격, 설계 7절) → 전날 주문표 결과 분류(체결·일부·미체결·미입력·변경) → 결정 일지 자동 추가(행동 없음 포함) → 대시보드 결과 칸·알림 후보.
- 첫 5거래일은 **비교 모드**: 주문표는 "비교 중(입력 대상 아님)"으로만 남고 일지는 쓰지 않는다. 기존 통합 점검 판정과 매일 자동 대조하고, 5일 대조와 3개월 리플레이가 끝나면 사용자 "켜" 한 번으로 기록 모드.
- 왜 T3 파이프라인이 아닌가: CLAUDE.md "Authority/limit change … manual route" — T2는 주문 단계·수량 권한을 바꾸는 권한·한도 변경이고, 파이프라인 README도 권한 변경은 기존 방식(worktree Builder → 별도 Judge)이라고 적는다. 파이프라인의 Builder 시간 상한(120분)도 이 규모에 맞지 않는다.

## 1. 사용자 조작 (Windows PowerShell, 이 순서로 한 번)

시작은 **오늘 23:30 뒤**(내일 아무 때나)다. 이 지시문과 실측 파일은 23:30 자동 커밋(InvestmentV2-DocsCommit)이 넣고, 커밋된 뒤라야 새 worktree에 들어간다.

```
cd "E:\사업\##금동한\코덱스저장소"
claude --worktree t2-core --model opus --effort xhigh
```

Claude Code가 열리면 첫 메시지로 이 한 줄만 붙여 넣는다:

```
Read docs/claude/redesign-t2-builder-prompt-2026-10-10.md and follow sections 3-6 and appendices A-D exactly.
```

끝나면 Cowork에 "T2 Builder 완료"만 보낸다(Cowork가 worktree를 직접 읽는다). Builder가 BLOCKED.md를 쓰고 멈췄을 때만 그 내용을 붙여 넣는다.

## 2. 완료 기준 (기계 판정)

**Builder 단계**
- 대상 테스트 통과 · 기준선(Builder가 0단계에서 HEAD에서 잰 실패 id 집합) 대비 새 실패 0 · 테스트 수(`Ran`, `def test_`) 감소 0 · 허용 경로(4절 "범위") 밖 변경 0 · 스키마 감사 PASS · 5절 보고.
- 황금 테스트 통과: G-1 설계 5절 MVLL 후회표(정책 간격 236주 → ½ = 118주), G-2 설계 7-2 가격식(σ 반올림 방향), G-3 OI-20261009-SOXL-2 재현(아래 F5), G-4 규칙 파일의 공통 규칙 C1~C8 경계 사례, G-5 R-REC1 10/8 이벤트(사용자 지정 EV3) 재현.

**T2 전체(병합 뒤, Cowork가 판정 — 사용자 손 없음)**
- R1 리플레이: 부록 C 사전 등록 기준 R-A·R-B·R-C 통과(2026-07-10 ~ 2026-10-09).
- R2 판정 대조: 비교 모드 5거래일 동안 코어 판정과 기존 통합 점검 판정의 차이가 모두 부록 B 범주로 자동 분류되거나 Cowork 설명 기록(docs/claude/redesign-t2-compare-explained.json, LLM_ERROR)으로 설명되고, CORE_BUG로 남은 것이 0(decide의 연속 일수 ≥ 5).
- R3 사용자 "켜" 한 번 → `decision_mode = apply`. 그 뒤 주문 1단계 운영(재설계 3-6: 주문표 오류 0으로 10거래일 또는 주문표 5건이면 2단계 질문).

## 3. Cowork가 정한 설계 결정 (근거와 함께 · Judge가 확인)

| # | 결정 | 근거 |
|---|---|---|
| D1 | **두 단계 실행**: 06:15 `daily`(T1 그대로) + 07:45 `decide`(새). decide는 그날 연구 기록이 아직 없으면 5분마다 다시 보며 08:30까지 기다린 뒤, 없으면 없는 대로(매수 막힘) 진행한다. 브로커 대조는 다시 하지 않고 그날 T1 결과를 읽으며, 주문표 결과 분류용 읽기 조회(ust21150·ust21050)만 한다. 알림 작업은 08:50 | p-earn r1(병합 코드)은 "미공지 확인"이 평가 세션 16:00 ET 뒤에 확인돼야 유효하다. 그 확인을 쓰는 연구 작업(06:40 점검)이 06:15 뒤에 끝나므로 판정은 그 뒤여야 한다. 06:40 실행 기록 시각 실측: 10/9 07:30, 10/10 06:50 |
| D2 | **일봉 = 30분봉에서 만든 정규장 일봉**(시가·고가·저가·종가·거래량, 09:30~마지막 정규장 봉, 조기 폐장은 달력대로). 종가는 기존 종가 이력과 같은 정의(마지막 정규장 30분봉 종가, 잠정). 분할은 corporate-actions.json(공식 기록)으로 보정 | 시스템 원칙 "정규장 종가", 이미 매일 수집 중(T1), 키움 일봉은 시간외가 섞인다(규칙 파일 자신이 그렇게 적음). LLM 점검과의 차이는 부록 B 범주 B2로 설명 |
| D3 | **카드 기계 판독 칸 = 새 파일 docs/claude/card-evidence-registry.json**(스키마 포함). 첫 내용은 Builder가 사용자 수락 카드와 규칙 파일에서 **옮겨 적기만** 한다(새 판단 금지, 줄 번호 인용). **주문표는 매수·매도 모두 그 종목의 등록부 항목이 있고(수락 확인 · 절 해시 일치) 커밋된 상태일 때만** 나온다(NOCARD·해시 불일치·미커밋 = 알림·표시만). 갱신은 카드를 고치거나 수락하는 Cowork 세션이 같은 세션에서 한다(새 사용자 단계 0) | 재설계 6절 "코어는 카드의 기계 판독 칸만 읽는다, 카드 근거가 없으면 행동하지 않는다", 사용자 10/1 "매매마다 카드 근거". 지금 카드는 산문뿐(실측) |
| D4 | **연구 기록 = workspace/outputs/research-records/<KST 날짜>/research-record.json**(스키마 포함): 실적일(p-earn 형식), 회사 공식 사실(출처 URL·종류), 뿌리 테제 훼손 사실, 통합 점검 기록 사본. 쓰는 쪽은 06:40 점검(배포 때 로더에 단계 추가). 없거나 틀리면 매수는 막히고 공식 사실 근거는 0 | P2: LLM은 가장자리, 실패해도 코어는 돈다(fail-closed) |
| D5 | **주문표는 회로가 열린 날만**(설계 1절 ①): 매수 = 오늘 새로 생긴 + 방향 근거(새 M)만으로 근거 기준(공식 사실 1 또는 종류 다른 가격 단서 2)을 채움(규칙 파일 2026-10-03 결정 (i)) **또는** S7 채우기 권고 + 그 종목 카드 근거 충족. 매도 = 노출 정책 간격(S7 줄이기 항목) 또는 카드 EXIT/TRIM 목표가 있고 그 종목 매도 근거(− 방향)가 충족 | 설계 1절 ①·3절 G3, 매매마다 카드 근거(사용자 10/1) |
| D6 | **수량 = 설계 7-1 그대로**(정책 간격 × 단계 r, 첫 진입 ½, 후회표 5절로 줄이기만, 데드밴드 자산 2%, 현금 G4). 매수 목표 비중은 S7 모듈의 투영 E·종목 상한 계산을 그대로 써서 찾는다(새 노출 계산을 만들지 않음) | 재설계 3-3 REUSE, 설계 13절 K3-2·K3-7 권장값 |
| D7 | **가격 = 설계 7-2**: 매수 LOC 상한 = 기준가 × (1 + 0.5σ60) 센트 내림, 계획 축소 매도 LOC 하한 = 기준가 × (1 − σ60) 센트 올림. 대시보드 환산 = 키움 기준종가 × m, 유효 범위 근사 종가 ±1%(설계 9-1). 긴급 축소·MOC·강세 트리거 지정가는 **주문표를 만들지 않고 알림만** | 긴급 축소는 공식 훼손 판단(LLM)이 필요. 권한을 줄이는 쪽 |
| D8 | **유효 1세션, 재발행 1회**(7-3). 미입력은 재발행 횟수에 넣지 않고(R-NE1), 같은 결정 연속 미입력 2회면 닫고, **R-NE1 제한 1("사용자가 다시/종료 선택")은 코어가 다음 날 새 기준가로 관문을 다시 통과할 때만 다시 내는 것으로 바꾸고, 제한 3(다시 낼 때 매수 상한 ≤ 첫 상한)은 설계가 "유지 여부 사용자 확인 필요"로 남긴 값이라 설정 키 `reissue_buy_cap_not_above_first`로 둔다** → 7절 Q2 | CLAUDE.md Goal(2026-10-10): 일상 단계에 사용자가 필요하면 결함, 사람 단계를 없애는 쪽으로 고친다 |
| D9 | **일지 = stock-strategy-system/decision_journal.json에 새 항목 3종**(core_decision 행동 없음 포함 · order_ticket · ticket_outcome), portfolio_review_journal.py의 새 라이브러리 함수로만, confirmation_method "AUTO_CORE", 기록 모드에서만, 쓰기 직전 재확인(T1 C1 방식) | CLAUDE.md "decision_journal … (later the auto-core)", 설계 10절·13절 K3-5 |
| D10 | **모드**: auto_core.json에 `decision_mode`(compare/apply), `decision_compare_days_required` 5, `decide_schedule_kst` "07:45" 추가, `symbols_extra`에 GRID 추가 — 정책 제안 파일로만(직접 쓰지 않음) | T1 F7과 같은 방식. GRID = R-REC1 전력 업종 벤치마크(규칙 파일), 지금 수집 안 됨(실측) |
| D11 | **판정 대조 자동**: decide가 연구 기록 안의 통합 점검 기록 사본과 코어 판정을 부록 B 범주로 비교하고 연속 일치 일수를 센다 | 5거래일 완료 기준을 사람 손 없이 판정 |
| D12 | **리플레이 하네스**(읽기 전용)로 부록 C 기준을 판정. 관심 종목 30분봉은 10/13 첫 코어 실행 뒤에 생기므로 리플레이 실행은 병합 뒤 Cowork가 한다. Builder는 하네스와 가짜 자료 테스트, 저장소에 있는 4종목(MVLL·NBIS·SOXL·SOXX) 스모크까지 | 실측: 종가 이력은 4종목만, 관심 종목 페이지 없음 |
| D13 | **옵션 층(O1~O4)은 T2에서 만들지 않는다**: 주문표·대시보드 orders 문서에 option 칸을 넣지 않는다(화면은 "옵션 생략"으로 표시 — 8절 4(c)) | CLAUDE.md "when it is missing, omit it". 표시 전용 |
| D14 | **PWR·LITE**: 규칙 파일은 승인 상품(10/8 사용자 승인)이지만 alert_policy의 배수·card_stock_core에 없다(실측) → 매수 요건 ②는 규칙 파일대로, 주문표는 `POLICY_UNREGISTERED_INSTRUMENT`로 막힘. 등록은 정책 제안 파일에 별도 항목(사용자 "적용" 뒤 Cowork) | 정책 직접 수정 금지, 승인 상품은 권한·한도 항목 |
| D15 | **위원회·시나리오 확률·봉인 시범·사용자 인정 근거는 코어에 없다**. 사용자 인정 근거(Q5)가 필요한 매매는 지금처럼 Cowork 경로 | CLAUDE.md Council 줄(2026-10-10), 재설계 3-5 |
| D16 | **관문 기준값은 바꾸지 않는다**: 예산 1.55·감축선 1.85·상한 1.9·종목 0.4배·R-REC1 수치·실적 금지 구간·V6 선·C8 문턱·σ 배수·데드밴드 2%·후회 예산 3%·현금 여유 0.25%는 원문 값 그대로(출처 줄과 함께 상수 표). 실측 수수료 0.0699%는 검산 줄 표시에만 쓴다 | 사용자 금지 사항 "관문 기준값 변경" |
| D17 | **재설계 3-2 ⑤의 "1회 주문 크기·하루 주문 수" 관문은 값이 정해진 적이 없다** → 설정 키(`max_buy_ticket_pct_of_equity`, `max_tickets_per_day`)로만 만들고, 키가 없으면 관문 없음(지금과 같음). 값은 7절 Q3 답으로 P-1에 넣는다. 줄이기만 한다 | 새 한도 값은 사용자 결정(권한·한도) |
| D18 | **무인 LLM 연구 기록 하나로만 생긴 강 근거의 단계 상한**은 7절 Q4로 묻는다. 코드는 설정 키 `research_only_strong_r_cap`(없으면 설계 G3 그대로 1) | 지금까지 공식 사실은 Cowork가 확인했고, 무인 LLM이 근거를 쓰는 경로는 새로 생긴다 |

## 4. Builder 지시 (이 절과 부록만 따른다)

```
권한 경계: order_authority=false, execution_quantity=null 유지. 코어 주문표 안에서만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY".
그 밖의 파일·스키마의 quantity_authority 값("none")은 바꾸지 않는다. 키움 주문 명령(overseas orders *, /api/us/ordr, ust2000x)·주문 도구
호출 금지. 체결은 브로커 체결 조회(ust21150 cntr_qty·cntr_uv)로만, 가격·종가로 체결을 추정하지 않는다.
workspace/policies/*, stock-strategy-system/{portfolio_state.json, reconciliation_ledger.jsonl, decision_journal.json, alert_policy.json},
.claude/*, CLAUDE.md, AGENTS.md, tools/** 는 직접 수정하지 않는다(정책 변경은 F12 제안 파일로만). 비밀(.env*, 토큰, 계좌번호·계좌 라벨·이름)
읽기·출력 금지. 키움 실제 호출 0회(테스트는 가짜 데이터). 판단이 필요하거나 범위를 넘으면 worktree 루트에 BLOCKED.md를 쓰고 멈춘다.

범위(허용 경로):
  manage-us-stock-strategy/scripts/ : 새 파일 auto_core_bars.py, auto_core_rules.py, auto_core_inputs.py, auto_core_tickets.py,
      auto_core_decide.py, auto_core_compare.py, auto_core_replay.py / 수정 auto_core.py(decide 하위 명령), auto_core_reconcile.py(설정 키만),
      run_auto_core.ps1(-Command), register_auto_core_task.ps1(두 번째 작업), portfolio_review_journal.py(F7 함수·항목 종류),
      score_decision_journal.py(새 항목 종류 무시 또는 처리 — portfolio_status.py는 고치지 않는다, F7 참고)
  manage-us-stock-strategy/schemas/ : 새 auto-core-decision / auto-core-ticket / auto-core-card-registry / auto-core-research-record /
      auto-core-compare / auto-core-replay .schema.json, 수정 auto-core-config.schema.json, portfolio-review-journal(.|-payload).schema.json
  manage-us-stock-strategy/tests/ : 새 test_auto_core_rules.py, test_auto_core_tickets.py, test_auto_core_decide.py,
      test_auto_core_compare.py, test_auto_core_replay.py, tests/fixtures/auto_core_t2/** / 수정은 F7·F11이 요구하는 기존 테스트만(약화 금지)
  manage-us-stock-strategy/references/auto-core-decision.md (새)
  docs/claude/card-evidence-registry.json (새, F2) · docs/claude/redesign-t2-policy-proposals.json (새, F12) ·
  docs/claude/redesign-t2-builder-report-2026-10-10.md (보고)
  portfolio_exposure.py·run_portfolio_exposure_review.py·regular_session_close_history.py·corporate_actions.py는 import만 한다.
  꼭 고쳐야 하면(예: 비공개 함수를 공개 이름으로 감싸기) 동작이 바뀌지 않는 추가만 허용, 그 파일의 기존 테스트가 그대로 통과해야 하고 보고 2절에 이유를 쓴다.
  main 체크아웃의 무시된 자료(workspace/outputs/regular-session-closes/pages·history, corporate-actions.json, exposure-review, auto-core)는
  읽기만 하고, 테스트 픽스처가 필요하면 최소 부분만 tests/fixtures/auto_core_t2/ 로 복사한다(계좌 식별자 없는 값만).

0단계 — 사실 확인(읽기만, 보고 맨 위)
 a. 테스트 기준선: 이 worktree HEAD에서 전체 스위트 실패 id 집합과 Ran 수(test-runner 서브에이전트 가능, 숫자는 원본 출력에서 직접 센다).
 b. 재사용 경로: portfolio_exposure의 ExposureModel·_evaluate_proposal(new_buy_within_band)·increase_blockers·reduce_recommendations·
    earnings_blackout·floor_to_step(WEIGHT_STEP 0.001)과 run_portfolio_exposure_review.run(--earnings, --proposals)을 수정 없이 불러
    "투영 E ≤ 1.55·종목 상한·차단 사유"를 얻을 수 있는지. 못 하면 필요한 최소 추가를 적는다.
 c. regular_session_close_history의 봉 선택(정규장 시작·마지막 봉, 조기 폐장, 달력)과 corporate_actions의 보정 함수를 일봉 OHLCV에 재사용할 수 있는지.
 d. T1 출력(workspace/outputs/auto-core/<날짜>/result.json·reconcile.json·kiwoom_broker_snapshot*.json)에서 decide가 읽을 칸:
    보유 poss_qty, 주문가능액 fc_ord_alowa, 외화예수금 fc_entra(cash_components.deposit), reconcile status·reasons, 상태 파일 최신 여부 판정 방법.
 e. 브리지 읽기: account_daily_fills_read(ust21150 query_tp 1 = 체결 없는 주문 행 포함)와 account_open_items(ust21050)의 SAFE_FIELDS로
    결과 분류(F6)에 필요한 칸(ord_no, stk_cd, slby_tp_nm, frgn_trde_tp, ord_qty, cntr_qty, cncl_qty, ord_uv, cntr_uv, ord_stat_nm, ord_time)이
    모두 오는지. 모자라면 SAFE_FIELDS 추가가 필요한데 그 파일은 권한 경로이므로 BLOCKED.
 f. decision_journal 읽기 쪽(load_journal·_entry_inconsistency·portfolio_exposure.journal_view·score_decision_journal·
    portfolio_status.journal_pending)이 새 항목 종류를 만나면 어떻게 되는지. Cowork 확인: _entry_inconsistency는 user_message.upper()를 먼저
    부르므로 null이면 예외, journal_pending은 채점 보고서 head가 일지 마지막 항목과 다르면 STALE — F7에서 둘 다 막는다.
 g. 규칙 파일 docs/claude/integrated-check-prompt-v3.12.2-2026-10-09.txt와 부록 A의 수치를 한 줄씩 대조. 다르면 규칙 파일이 맞고 보고에 적는다.

F1 일봉·지표·공통 규칙 (auto_core_bars.py, auto_core_rules.py)
 - 일봉: 저장된 30분봉 페이지에서 정규장 봉(시작 09:30 ET ~ 마지막 정규장 봉, 조기 폐장은 운영 달력)을 세션별로 묶어 O·H·L·C·V. C는 종가 이력의
   값(마지막 정규장 30분봉 종가)과 같아야 하고, 정규장 봉이 하나라도 없으면 그 세션 H·L·V는 INCOMPLETE(그 값을 쓰는 규칙만 unk).
 - 분할 보정: corporate-actions.json(공식 기록)의 SPLIT을 effective_session 전 가격 × old/new, 거래량 × new/old로. 기록 없이
   |C_t/C_{t-1} − 1| ≥ 0.45 이고 그 비율이 k 또는 1/k(k ∈ 2,3,4,5,8,10,15,20)에서 3% 안이면 SPLIT_SUSPECTED:<종목>:<세션> → 그 종목의
   모든 지표 unk(매수 근거·매도 근거 모두 0, 알림 후보 "분할 의심 — 공식 분할 기록 필요"). 보정 근거(기록 id·출처 URL)를 결과에 남긴다.
 - 지표(평가 세션 t까지): EMA10·20·50(표준, 초기값 첫 N개 단순평균), RSI14(Wilder), ATR14(Wilder, 정규장 H·L·전일 C), σ60(최근 60개 일간
   수익률의 표본표준편차 — portfolio_exposure._sample_std와 같은 식), 직전 20세션(당일 제외) 종가 고점·저점, 직전 20세션 평균 거래량,
   종가 위치 (C − L)/(H − L)(H = L이면 0.5), 장중 낙폭(L ÷ 전일 C − 1, ÷σ60 함께 — 표시 전용). 이력이 모자라면 unk(만들어 내지 않음).
 - 공통 규칙 C1~C8(±)·근거 지속(상태형 C1·C3·C5·V3·S4·S5 / 사건형 C2·C4·C6·C7 5세션 창, 반대쪽 같은 번호가 나오면 해소)·신고가 돌파 2세션
   유지·같은 종류 합치기·카드 별칭·카드 고유 트리거(V3, S5, S6, S8, N8, N9, X8 등)·매수 불가 상품 표시·카드 없는 보유(NOCARD) — 부록 A-3의
   정의를 그대로. 상수는 auto_core_rules.py 맨 위 표 하나에 모으고 각 값 옆에 규칙 파일 절 이름을 주석으로 단다.
 - 상태 값: hit(충족, 잠정 포함) · near(수치 정의가 있는 것만: R5 ≤ 0.75P, V6 접근 ≤ 26,395.34) · pending(1세션째 유지 확인 대기) · none ·
   unk(자료 부족) · review(경보 — 근거 아님). 공통 C·카드 가격 트리거의 "근접"은 규칙 파일에 수치 정의가 없으므로 만들지 않고, 화면용 거리
   (조건까지 남은 %)만 따로 낸다.
 - C7(호재 뒤 하락·악재 뒤 상승)은 F3 연구 기록의 공식 사실(event_session·criterion_a)이 있을 때만 판정, 없으면 unk.
 - V6 계좌 점검선(상수: HWM 28,473.94 · 1차 25,626.55 · 접근 26,395.34 · 최대 22,779.15, 규칙 파일 V6), 총자산 = Σ(poss_qty × 종가) + fc_entra
   (규칙 파일 1-1 ②). S7 hwm_usd는 참고 줄로 함께.
 - R-REC1(부록 A-4): EV1·EV2·EV4·EV5·DS1·RG2·RG3·RG4는 결정론, EV3 ⓐ는 docs/claude/recovery-gate-R-REC1-2026-10-09.md에서 정규식
   ^- 이벤트 (\d{4}-\d{2}-\d{2})\(EV 로 읽은 날짜, EV3 ⓑ와 RG1은 연구 기록의 root_thesis_damage 사실(없으면 RG1 unk → 늘리는 매수 막힘).
   L0 = 이벤트일 벤치마크 정규장 저가(D2 일봉). 업종이 "A1 전력"으로 시작하는 종목의 RG2 벤치마크 = GRID(이력 없으면 unk → 막힘).
 - M6 ④: docs/claude/m6-relative-comparison-7stock*.md 가 있고 그 안에 종목 코드가 나오면 통과, 아니면 "막힘 — 비교 카드에 없음".

F2 카드 기계 판독 칸 (docs/claude/card-evidence-registry.json + schemas/auto-core-card-registry.schema.json, auto_core_inputs.py)
 - 종목별: role(holding|watch), card_doc, card_section(머리 줄 문자열), section_sha256(LF 정규화한 절 본문), accepted(카드 수락 문구·날짜),
   card_action(HOLD|WATCH|ADD|TRIM|EXIT), trim_target_weight(null 허용 — null이면 TRIM 주문표 없음), trigger_set, sector, rg2_benchmark,
   official_domains(회사 IR·보도자료 도메인, sec.gov는 공통), c8(1일 문턱, 5세션 문턱), card_triggers[{id, kind, side, strength
   weak|review|info, params, active_when held|member|held_or_member, source(파일:줄)}], static_evidence[{id, e1_kind thesis|valuation|
   event_reaction|relative, strength strong|weak|neutral, direction +|−, as_of, source(파일:줄), quote(160자 이내 원문)}], kill_refs[{id, source}],
   known_events[{date, label}].
 - 첫 내용: MVLL·SOXL·NBIS(integrated-stock-cards-v1-2026-10-02.md 2~4절), MU·BE·DELL·AMD(같은 파일 5·6절), PWR·LITE(watch-card-*-2026-10-03.md).
   트리거 정의·문턱은 규칙 파일(현행 규칙 전부)에서, 정적 근거는 카드의 "매수 근거 후보 현황" 표에서 **표에 적힌 강도 그대로** 옮긴다.
   기술 신호(가격으로 매일 다시 계산되는 것)는 static_evidence에 넣지 않는다. 표에 강도가 명확하지 않으면 neutral(세지 않음).
   AMD는 관심 명단 members가 아니므로 active_when=held_or_member로 지금은 꺼진다.
 - 읽을 때: 카드 파일이 없거나 절 해시가 다르면 그 종목은 CARD_SECTION_CHANGED. 관심 종목의 accepted는 watchlist-registry.json의 그 종목
   cardStatus가 "수락"으로 시작할 때만 유효. 등록부에 없는 보유 종목 = NOCARD, 등록부에 없는 관심 종목 = 매수 요건 ③ 확인 필요.
 - **주문표 자격(매수·매도 공통)**: 그 종목 등록부 항목 있음 · 수락 유효 · 절 해시 일치 · 등록부 파일이 git에 커밋된 상태(미커밋 수정 있으면
   REGISTRY_UNCOMMITTED). 하나라도 아니면 그 종목 주문표 없음(판정·표시·알림은 계속). CARD_SECTION_CHANGED·REGISTRY_UNCOMMITTED는 처음 생긴
   날 한 번만 push 후보(받는 쪽 Cowork — 카드를 고친 세션이 같은 세션에서 등록부도 고치는 것이 정상 절차라 평소에는 생기지 않는다).

F3 연구 기록 (workspace/outputs/research-records/<KST 날짜>/research-record.json + schemas/auto-core-research-record.schema.json)
 - 칸: schema_version, record_day_kst, evaluation_session, written_at(오프셋 포함 ISO), writer, earnings{SYM: p-earn 형식 — VERIFIED
   {announcement_session, timing BEFORE_OPEN|AFTER_CLOSE, source_kind, source_url} 또는 NOT_ANNOUNCED{source_kind, source_url, checked_at}},
   official_facts[{fact_id, symbol, direction, kind(contract|guidance|revenue|funding|dilution|customer_change|kill|thesis|other),
   card_trigger_ids[], event_session, announced_at, source_kind SEC_FILING|COMPANY_PRESS_RELEASE|COMPANY_IR, source_url, criterion_a(bool),
   root_thesis_damage(bool), summary_ko(200자 이내)}], integrated_check_run(그날 통합점검 대시보드 runs 문서 사본, 없으면 null),
   order_authority false, quantity_authority "none".
 - 검증(결정론, 하나라도 틀리면 그 항목 버림 + 사유): https URL이고 호스트가 sec.gov 또는 등록부 official_domains, source_kind 허용값,
   written_at이 평가 세션 16:00 ET 이후이고 decide 시각 이전, event_session이 달력 세션. 파일 전체가 스키마를 못 통과하면 "연구 기록 없음"과 같다.
 - 공식 사실 근거: + 방향은 criterion_a=true일 때만 강 1개(규칙 파일 호재 기준 (a)), − 방향(kill·dilution·customer_change·guidance 하향)은 강 1개.
   "새 근거"로 세는 것은 event_session = 평가 세션(또는 평가 세션 직전 세션이고 직전 decide 기록에 없던 것)뿐이다. 계속 근거로 쓰려면
   카드 재작성으로 등록부 static_evidence에 들어가야 한다(연구 경로).
 - D18: 강 근거가 연구 기록 공식 사실뿐이고(같은 방향 등록부 정적 강 근거 없음) 설정 키 research_only_strong_r_cap이 있으면 r_max ≤ 그 값.
 - 실적 금지 구간은 portfolio_exposure.earnings_blackout 그대로(p-earn r1). 기록 없음 = 막힘.

F4 매수 요건 ①~⑥과 관문 G0~G5 (auto_core_tickets.py)
 - 매수 요건 행(규칙 파일 3) 끝 "매수 요건 상태 줄", 대조용): 관심 members(보유 아님) + 보유 종목(추가). ① 금지 구간(F3) ② 노출(규칙 파일 문장
   그대로: N < 1.85, S7 신선·E < 1.85·신규 매수 멈춤 없음, 보유 추가는 add 멈춤·종목 상한·R5도) + 매수 가능 현금(fc_ord_alowa) + 상품 승인
   (규칙 파일 목록: BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM·PWR·LITE) ③ 근거(등록부 정적 근거 N + 새 트리거 M, + 방향, 공식 사실 1 또는
   종류 다른 가격 단서 2 → ok/no, "카드 표 N + 새 M" 문구) ④ M6 ⑤ R-REC1(열린 이벤트면 RG1~RG4 모두) ⑥ wait(사용자). 각 칸 ok|no|unk|wait.
 - 회로 열림(D5): 매수 열림 = (오늘 새로 hit가 된 + 방향 트리거와 새 공식 사실만으로 근거 기준 충족) 또는 (S7 add 권고에 그 종목이 있고
   ③ 충족). 매도 열림 = 보유 종목에 (S7 reduce 항목 또는 등록부 EXIT/TRIM 목표) 그리고 매도 근거 충족(공식 − 사실 1 또는 같은 종목 − 방향
   가격 단서 2 종류 이상; C8·S6·S8·N9·V6 같은 경보는 근거가 아님). 열리지 않으면 "행동 없음"(정상).
 - G0 연속(설계 G0·R-NE1 그대로, 전체 단위): 직전 주문표가 모두 분류됨(F6, 조회 실패 = 분류 안 됨), 미체결 주문(ust21050)이 없음.
   하나라도 아니면 그날 새 주문표 없음.
 - G1 자료: 그날 T1 result가 있고 reconcile status OK, 상태 파일 보유·현금 = 그날 브로커 스냅샷(수량 일치·현금 $1 이내 — T1 기록 모드면
   자연히 맞는다), S7 검토의 evaluation_session = 최근 완료 세션이고 fail_closed 비활성, 쓰이는 종목 모두 평가 세션 종가·지표 있음,
   등록부 해시 일치. 하나라도 아니면 그날 주문표 없음(사유 코드). 매도도 막는다(설계 G1 그대로, F1 시범 발견은 K3 미결로 둔다).
 - G2 정책: E ≥ 1.9 모든 매수 금지 · E ≥ 1.85 매수 멈춤 · 그 아래에서 늘리는 매수는 투영 E ≤ 1.55(N·V 둘 다) · 종목 명목 ≤ 0.4 · 상품 승인은
   alert_policy(card_stock_core ∪ allowed_index_etfs, 정책 미등록이면 POLICY_UNREGISTERED_INSTRUMENT) · 실적 금지 구간 · 검토선 L2·R5 멈춤
   (S7 pauses·peak_reviews). 전부 S7 모듈 결과를 쓴다.
 - G2b 크기·횟수(D17, 키가 있을 때만): 매수 주문표 금액 ≤ 자산 × max_buy_ticket_pct_of_equity(넘으면 수량을 줄임), 하루 주문표 수 ≤
   max_tickets_per_day(넘치면 매도 → 매수, 같은 방향 안에서는 금액 큰 순으로 남김). 매도 금액에는 상한을 두지 않는다(위험 감축을 늦추지 않게).
 - G3 근거: r_max = 1(강 1개 이상) / ½(종류 다른 약 2개) / 그 외 0. 충족 근거가 공통 C뿐(카드 정의 트리거·공식 사실 동반 없음)이면 r_max ≤ ⅓
   (설계 G3, 사용자 결정 Q2 a′). 위험 한도·S7 권고는 근거가 아니다. F2 주문표 자격이 없으면 r_max = 0(NOCARD 매도·매수 모두 주문표 없음).
 - G4 현금(매수): qty × LOC 상한 × 1.0025 ≤ fc_ord_alowa(T1 스냅샷, 현금 검사 통과값). 넘으면 qty를 줄이고 0이면 CASH_ZERO.
   예상 매도대금은 넣지 않는다. 같은 세션 매도 → 매수 회전 없음(매수 주문표는 다음 아침 결과로만).
 - G5 회복 관문: 열린 R-REC1 이벤트가 있으면 늘리는 매수는 RG1~RG4 모두. 매도는 막지 않는다. 자료 부족 = 막힘.

F5 주문표 계산기 (auto_core_tickets.py) — 설계 7절 그대로
 - 매도 정책 간격 Δ = 보유 − ⌊목표 비중 × S7 자기자본 ÷ 기준가⌋. 목표 비중 = 그 종목 S7 reduce 항목 target_weight(1 종목 상한 초과 · 3 SOXL),
   카드 EXIT = 0, 카드 TRIM = 등록부 trim_target_weight(null이면 CARD_TRIM_SIZE_MISSING, 주문표 없음).
 - 매수 전체 목표 W* = 격자(0.001)에서 S7 제안 평가(new_buy_within_band)가 사유 없이 통과하는 가장 큰 비중. 지금 보유하지 않은 종목은 첫 진입
   ⌊W*/2⌋(격자), 보유 종목은 W*. Δ = ⌊(목표 − 현재 비중) × 자기자본 ÷ 기준가⌋.
 - 단계 r: 설계 5절 후회표. 행동 {0, ⅓, ½, 1} 중 r_max 이하, 시나리오 = 그 종목 최근 60세션(보정 정규장 종가) 5세션 수익률 90분위(상승)·
   10분위(하락)(분위수는 선형 보간, numpy 'linear'와 같은 결과). 후회(a,s) = max_b 손익(b,s) − 손익(a,s). r_max의 최대 후회 ≤ 자산 3%면 r_max,
   아니면 r_max 이하에서 최대 후회가 가장 작은 단계(같으면 작은 쪽). 올리지 않는다. 꼬리(최악 1일)와 LOC 미체결(하한 아래 마감 = 0 단계와 같음)은
   설계 5절 예시처럼 표시 행으로 계산해 남긴다(선택은 상승·하락 두 시나리오, 황금 G-1과 같은 방식).
   매도 후회는 설계 5절 재배치 다리 세 경로로 본다: 보유 · 매도 → 현금 · 매도 → 다음 날 최선 후보 매수(후보 = 등록부 + M6 + ③ 충족, 후보의
   스트레스 수익률도 같은 방식). 후보가 없으면 둘째 경로(현금)와 같다.
 - 수량 = ⌊Δ × r⌋(매도 r = 1이면 Δ 전부). 데드밴드: 수량 × 기준가 < 자산 2%면 DEADBAND, 1주 미만 LOT_ZERO. 줄이기만 한다.
 - 가격(D7): 기준가 = 평가 세션 근사 종가(종가 이력), σ = 그 종목 σ60. 매수 LOC 상한 = ⌊기준가 × (1 + 0.5σ)⌋센트, 매도 LOC 하한 =
   ⌈기준가 × (1 − σ)⌉센트. priceCalc = {mult(소수 넷째 자리), round "down"(매수)|"up"(매도), lo = 기준가 × 0.99, hi = 기준가 × 1.01}.
 - 유효·재발행(D8): 주문표는 buy_session(평가 세션 다음 달력 세션) 1회. decision_key = sha256(종목|방향|근거 id 정렬|카드 절 해시|간격 출처).
   같은 key: 미체결(시장 거절) 1회 뒤 재발행 1회, 미체결 2회면 key 닫힘 / 미입력은 세지 않되 연속 2회면 닫힘 / 설정 키
   reissue_buy_cap_not_above_first가 true면 미입력 뒤 다시 낼 때 매수 상한 ≤ 첫 주문표 상한(7절 Q2) / key가 바뀌면(새 근거·카드 갱신) 새로 센다.
   체결이면 key 끝. 사용자에게 "다시/종료"를 묻는 단계는 만들지 않는다.
 - 매도 주문표에는 매도 뒤 경로(설계 7-4)를 결정론 계산으로 붙인다: 예상 E·N·현금, 열리는/남는 매수 요건, 재배치 후보와 교체 쌍 예상 수량
   (설계 7-1 ⑤: "SOXL k주 매도 → 다음 날 후보 m주", 매도 뒤 예상 E ≤ 1.55, 후보 = 등록부 + M6 + ③ 충족) — 표시 전용. 교체 쌍의 매수는 다음 날
   decide가 매도 체결 뒤 새 상태로 다시 계산할 때만 주문표가 된다(설계 "매수는 매도 대조 뒤").
 - 주문표(decision.json tickets[], 스키마 auto-core-ticket): ticket_id "AT-<YYYYMMDD>-<SYM>-<n>", mode compare|apply, issuedAt, session,
   enterWindow("한국 <날짜> 17:00 이후 ~ 정규장 개장 전(22:30, 11/2부터 23:30)"), fillAt, ref{price,label}, ifUnfilled, ticker, side, type "LOC",
   price, priceRule, priceCalc, qty, amount, feeRate 0.0025, check_line(실측 수수료 0.0699%로 계산한 예상 수수료 한 줄), reason,
   evidence{strong[], weak[], composition, r_max, r}, gates{G0..G5, G2b}, regret{rows, tail_rows}, after_sale{…}(매도만), decision_key,
   inputs{해시}, authority{order_authority false, quantity_authority "ORDER_TICKET_HUMAN_ENTRY", execution_quantity null}.
 - 대시보드 orders 문서(dashboard.orders[], 기록 모드만)는 docs/claude/dashboard-order-panel-2026-10-07.md 3절 형식 그대로: status "official",
   source "auto-core"(새 칸), reason·evidence·afterSale은 한 줄 문자열, option 칸은 넣지 않는다(옵션 자료 없음 — 생략), outcome {state "pending"}.
 - 황금 테스트: G-1 정책 간격 236주·기준가 37.65·자산 30,255.36·상승 +29.6%·하락 −26.1%·r_max ½ → 후회표 4행(설계 5절 표와 $1 안) → 118주.
   G-2 SOXL σ60 8.35%·기준가 142.45 → 하한 130.56(OI-20261009-SOXL-2 1절, 올림), 매수 상한 식은 같은 방식 내림. G-3 OI-20261009-SOXL-2 5절
   상태(SOXL 75주·주문가능액 9,395.20 기준, 10/8 근사 종가) → S7 reduce 3번 SOXL 목표 비중으로 Δ 22주 또는 23주(OI는 22주로 E 1.552를 적었다.
   S7은 투영 E ≤ 1.55를 요구하므로 23주가 나올 수 있다 — 나온 값과 그 E를 보고에 적는다).

F6 결과 분류 (auto_core_tickets.py, decide 안)
 - 대상: 직전 주문표 중 outcome pending. 키움 읽기: ust21150(주문일 = 발행 KST 날짜와 그다음 날, query_tp 1 전체 주문), ust21050 미체결.
   같은 종목·방향 주문 행으로: 없음 = not_entered · Σcntr_qty = qty이고 유형 "Limit On Close"·주문가가 환산 범위 [lo×mult, hi×mult] 안 =
   filled · 0 < Σcntr_qty < qty = partial · 행은 있고 Σcntr_qty = 0 = unfilled(예: 주문상태 "무효주문") · 수량·유형·가격이 주문표와 다름 = changed
   (체결 수량 함께). 평균 체결가 = cntr_uv 가중. 조회 실패 = OUTCOME_UNKNOWN → G0 실패(그날 새 주문표 없음) + 알림 후보.
 - 그날 T1 대조의 I2(체결로 설명된 수량 변화)와 어긋나면 OUTCOME_MISMATCH_WITH_RECONCILE(기록하지 않음, 알림 후보).
 - 가격 움직임으로 체결을 추정하는 경로가 없어야 한다(테스트로 고정).

F7 일지 자동 추가 (portfolio_review_journal.py 새 함수 append_auto_core_entries + 스키마)
 - 항목 종류 추가: core_decision(평가 세션당 1개 — 행동 없음이면 no_action true와 막힌 사유 상위 5개), order_ticket(주문표당 1개), ticket_outcome
   (분류 1건당 1개). confirmation_method "AUTO_CORE", confirm_code null, user_message null, review_id = decision.json 정준 해시. 기존 해시 사슬
   (sequence·previous_entry_sha256) 그대로, 원자 교체, CRLF/LF 원본 유지.
 - 쓰기 조건(기록 모드만): decision_mode = apply · kill_switch false · git provenance의 guarded dirty 0(T1 C2 집합) · 일지 head 해시가 decide 시작
   때와 같음 · 같은 평가 세션 core_decision 없음(멱등). 쓰기 바로 앞에서 설정·provenance·head를 다시 읽는다(T1 C1 방식). 하나라도 어긋나면 쓰지
   않고 FAIL. 비교 모드는 would_append만 결과에 남긴다.
 - 읽는 쪽 보호: _entry_inconsistency는 AUTO_CORE 항목을 확인 코드 검사 전에 따로 검사한다(user_message null에서 예외가 나지 않게 —
   confirmation_method AUTO_CORE·confirm_code null·payload 칸 집합·authority 칸). load_journal이 새 종류를 정상으로 받고, portfolio_exposure.journal_view와
   run_portfolio_exposure_review 결과가 새 항목 전후로 같으며(S7이 CORRUPT로 멈추지 않음), score_decision_journal은 새 종류를 무시하거나 처리한다.
   일지에 쓴 바로 뒤 decide가 score_decision_journal을 같은 프로세스에서 한 번 돌려 채점 보고서 head를 맞춘다(출력 폴더만 씀, 실패는 경고) —
   portfolio_status.journal_pending이 매일 STALE이 되지 않게. 각각 테스트.
 - 사람 확인 코드 경로(propose/show/apply, CONFIRMATION_METHODS)는 바꾸지 않는다. AUTO_CORE는 사람 apply에서 거부된다.

F8 decide 실행 (auto_core.py decide → auto_core_decide.py)
 1 설정·정지 스위치·decision_mode·provenance·프로필 별칭(없으면 조회 전 FAIL, T1 C6 방식). kill_switch면 HOLD.
 2 그날 T1 result.json(같은 KST 날짜) 읽기. 없거나 FAIL이면 decide HOLD(주문표 없음, 사유 T1_RESULT_MISSING|T1_NOT_OK).
 3 입력: 30분봉 페이지·종가 이력·corporate-actions·운영 달력·등록부(F2)·연구 기록(F3)·관심 명단·alert_policy·직전 decision.json.
   그날 연구 기록이 없으면 5분마다 다시 보며 08:30 KST까지 기다린다(기다린 시간과 결과를 inputs에 남김). 그래도 없으면 없는 대로 진행(F3 fail-closed).
   S7 검토는 run_portfolio_exposure_review를 연구 기록의 earnings로 다시 돌린다(읽기 전용 출력 1파일, 기존 경로).
 4 F6 결과 분류(읽기 조회 2종) → 5 F1 판정 → 6 F4 요건·관문 → 7 F5 주문표 → 8 F9 대조 → 9 알림 후보 → 10 F7 일지(apply만)
 11 출력: workspace/outputs/auto-core/<날짜>/decision.json(스키마 auto-core-decision) + workspace/outputs/auto-core/LATEST_DECISION.json.
   T1의 result.json·LATEST.json은 건드리지 않는다.
 - decision.json 칸: schema_version, run_day_kst, generated_at, evaluation_session, buy_session, status OK|HOLD|FAIL, reasons[], mode,
   decision_mode, commit_sha, dirty_paths, inputs{파일·해시·신선도}, symbols{종목별 지표·트리거 상태·근거 집계}, buy_requirements[],
   exposure{N(규칙 파일 방식), S7{E, band, fresh, pauses}, caps[], peaks[]}, shock{R-REC1}, account{V6}, earnings_calendar[], tickets[],
   no_action{true|false, reasons[]}, outcomes[], journal{would_append|appended}, compare{F9}, alerts[], dashboard{runCore, orders[]},
   next_action_for_user, next_action_for_cowork, order_authority false, execution_quantity null.
 - alerts[]: 규칙 파일 알림 ①②③④⑥⑨⑩의 결정론 조건과 반복 억제(직전 decision.json과 상태 비교, 직전 없으면 억제 없음 + "(직전 기록 없음)")를
   그대로 계산한 후보 목록 {code, line(한국어 한 줄), push(bool)}. 비교 모드에서는 push=false(통합 점검이 지금처럼 푸시), 예외만 push=true:
   decide FAIL, 분할 의심, 카드 바뀜·등록부 미커밋(처음 생긴 날 1번), 결과 분류 실패. 기록 모드에서는 주문표 1줄 + 위 조건 push=true.
   v3.12.3 ⑪(직전 실행 누락)도 직전 decision.json 날짜로 계산한다.
 - dashboard.runCore: 통합점검 대시보드 runs 문서의 core 칸으로 그대로 옮길 묶음(triggers·buyReq·exposure·shock·peakReviews·tickets 요약,
   기존 runs 칸 이름과 상태 어휘 hit|wait|info|unk|none 사용). dashboard.orders: 기록 모드의 주문표만(비교 모드는 빈 배열 — 비교 중 주문표는
   runCore.tickets에만 "비교 중" 표시). 이 둘은 값만 담고, 대시보드에 쓰는 것은 배포 때 Cowork가 바꾸는 알림 작업이 한다.
 - 실행 안 재시도 0회. 같은 날 두 번 = 같은 결과(멱등). 종료 코드 0 = OK/HOLD, 1 = FAIL. 결과 스키마 오류 = FAIL.

F9 판정 대조 (auto_core_compare.py, decide가 호출, CLI도 있음 — 읽기 전용)
 - 입력: decision.json + 연구 기록의 integrated_check_run(없으면 "대조 불가 — 기록 없음", 연속 일수 유지·증가 없음).
 - 대조 단위: 종목 × 트리거 종류(별칭은 등록부 kind로 풀어서), 매수 요건 행 × ①②④⑤ 칸, ③(ok 대 그 밖), 노출 N(±0.01)·대역·종목 상한 초과 집합,
   R5 상태, R-REC1 열림·RG1~RG4. LLM의 near는 hit이 아닌 것으로 본다.
 - 차이마다 부록 B 범주를 자동으로 붙인다. 자동으로 못 붙인 것 = B7 UNEXPLAINED. 출력 compare.json + decision.compare{streak, required 5,
   unexplained[], categories{}}.
 - 설명 기록: docs/claude/redesign-t2-compare-explained.json(스키마 auto-core-compare 안의 정의, Cowork가 씀) 항목 {date, item_key, verdict
   LLM_ERROR|CORE_BUG, rule_quote, note}. 연속 일수는 매 실행 처음부터 다시 센다: 한 날이 +1 되는 조건 = 그날 B7이 모두 LLM_ERROR로 설명됨 +
   CORE_BUG 0. 대조 기록이 없는 날은 건너뛴다(유지). 그 밖은 0. 5 이상이면 next_action_for_cowork = "판정 대조 5일 — 완료 판정 필요",
   설명 안 된 B7이 있으면 next_action_for_cowork = "판정 차이 n건 — 설명 기록 필요". 사용자 알림으로 보내지 않는다.

F10 리플레이 (auto_core_replay.py, 읽기 전용, 부록 C를 그대로 구현)
 - 입력: 저장된 30분봉·종가 이력·corporate-actions·달력·등록부(현재본, 소급 D)·docs/claude/redesign-t2-measurements-2026-10-10.json(실측 주문·
   SEC 실적일) · 고정 포트폴리오 두 개(부록 C P-R1·P-R2). 출력 workspace/outputs/auto-core/replay/<run id>/replay.json(스키마) + 한국어 요약 md.
 - 세션마다 F1~F5를 같은 함수로 돌린다(복제 구현 금지). 자료가 없는 종목은 "자료 없음"으로 세고 통과로 치지 않는다.
 - R-B 오라클(should-issue)은 주문표 경로와 다른 경로로 계산한다: 근거 플래그(F1) + S7 모듈 차단 사유·투영 E + earnings_blackout + R-REC1 →
   열림 여부만. 주문표 경로 결과와 비교해 "열렸는데 주문표 없음"마다 허용 사유(DEADBAND·LOT_ZERO·CASH_ZERO·REGRET_ZERO·G2B_CAP) 외에는 실패.
   외부 오라클 입력도 받는다: --external-oracle <json>(세션·종목·방향 목록) — 병합 뒤 Cowork가 규칙 원문만 보고 따로 계산한 목록과 대조(부록 C).
 - Builder는 4종목 실자료 스모크(어떤 세션에서도 예외 없이 끝남)와 가짜 자료 테스트까지. 전체 리플레이 실행·판정은 병합 뒤 Cowork.

F11 Windows 작업 (scripts)
 - run_auto_core.ps1: -Command daily|decide(기본 daily, 허용값 밖이면 exit 3), 로그 파일 이름에 명령 포함. ASCII·PowerShell 5.1·cmd /c 리디렉션 그대로.
 - register_auto_core_task.ps1: 기존 InvestmentV2-AutoCore(06:15)는 그대로 두고 InvestmentV2-AutoCoreDecide(화~토 07:45 KST, Interactive·Limited,
   실행 제한 60분(연구 기록 대기 포함), -MultipleInstances IgnoreNew, -Command decide)를 함께 만들거나 덮어쓴다(두 이름만). -PlanOnly 유지, 시간대 KST 아니면 등록 안 함.
   만들기만 하고 실행하지 않는다.

F12 정책 제안 파일 (docs/claude/redesign-t2-policy-proposals.json, 직접 쓰지 않음)
 - P-1 workspace/policies/auto_core.json 새 전체 내용: 기존 키 그대로 + decision_mode "compare", decision_compare_days_required 5,
   decide_schedule_kst "07:45", symbols_extra ["SOXX", "GRID"]. 7절 Q2~Q4 답에 따라 넣을 선택 키(reissue_buy_cap_not_above_first,
   max_buy_ticket_pct_of_equity, max_tickets_per_day, research_only_strong_r_cap)는 "답에 따라 Cowork가 채움"으로 비워 둔다. 스키마(auto-core-config)는
   이 키들을 선택 칸으로 받는다(없으면 D17·D18의 "현행" 동작).
 - P-2 stock-strategy-system/alert_policy.json portfolio_exposure_policy: nominal_multipliers에 PWR 1·LITE 1, card_stock_core에 PWR·LITE 추가
   (근거 docs/claude/product-approval-PWR-LITE-2026-10-08.md ④). 바뀌는 키만 경로·이전 값·새 값으로. 다른 키는 그대로.
 - 각 항목: 경로, 정확한 새 내용(또는 키 단위 변경), 이유, 적용 뒤 검사 명령(스키마·S7 검토 1회).

F13 문서: references/auto-core-decision.md — decide 흐름, 연구 기록·등록부 계약, 관문·산식, 모드, 대조·리플레이. CLAUDE.md는 쓰지 않는다.

테스트(대상, 가짜 자료): F1 지표 값(작은 손계산 예), C1~C8 각 경계 ±1틱, 상태형·사건형 창, 2세션 돌파·무산, 같은 종류 1개, 카드 별칭 우선,
매수 불가 상품, NOCARD, 분할 보정·분할 의심, INCOMPLETE 세션 → unk / F2 해시 불일치 → 정적 근거 0, 등록부 없음 / F3 URL·도메인·시각 검증,
criterion_a false → 강 아님, 기록 없음 → 금지 구간 막힘 / F4 각 요건·관문 실패마다 주문표 없음과 사유, 매도는 R-REC1에 안 막힘, E ≥ 1.9,
POLICY_UNREGISTERED_INSTRUMENT, C 단독 ⅓, NOCARD·해시 불일치·미커밋 등록부 → 매수·매도 주문표 0, G0 전체 단위, G2b 키 있음/없음,
research_only_strong_r_cap / F5 황금 G-1~G-3, 데드밴드·현금·1주, 재발행·미입력·key 닫힘·첫 상한 키, 매도 후회 세 경로, 교체 쌍 표시 / F6 다섯 상태와
조회 실패, 가격 추정 경로 없음 / F7 비교 모드 무쓰기, 기록 모드 사슬·멱등·재확인 실패 시 무쓰기, AUTO_CORE 항목의 user_message null, S7 journal_view
불변, 채점기·journal_pending CURRENT / F8 T1 결과 없음 HOLD, 연구 기록 대기(가짜 시계), kill_switch, 프로필 없음, 멱등, 스키마 / F9 범주 붙이기·
설명 기록 반영 연속 일수 / F10 오라클 대 주문표 경로, 허용 사유, 외부 오라클 대조 / F11 ps1 ASCII·명령 허용값 /
주문 명령·주문 API 문자열 없음(새 파일 전부) / 계좌 식별자 저장 없음. 스키마 감사(validate_schema_contracts.py) PASS.
Claude Code는 "auto_core.py"가 들어간 명령이 막혀 있다(settings deny): 테스트는 -p "test_auto_core*" 로 돌린다.
```

## 5. 보고 형식 (docs/claude/redesign-t2-builder-report-2026-10-10.md, 한국어)

1. 맨 위: 0단계 a~g 결과, BLOCKED 여부, 부록 A와 규칙 파일이 어긋난 곳.
2. 바꾼 파일(허용 경로 대조, CRLF/LF 유지 확인), 재사용한 함수 목록, portfolio_exposure 등에 추가가 있었다면 그 이유.
3. 테스트(대상·전체·기준선 대비 새 실패·Ran 변화), 황금 테스트 결과, 4종목 리플레이 스모크 결과, 스키마 감사.
4. 등록부 첫 내용: 종목별 정적 근거·트리거 표(출처 줄) — Judge가 카드 원문과 한 줄씩 대조할 수 있게.
5. Builder 판단(이 지시문이 정하지 않아 고른 것)과 이유 — Judge 확인 요청.
6. 사람이 할 일(병합·작업 등록·정책 제안) 각 한 줄, 남는 위험과 확인 필요.

## 6. Judge 확인 항목 (Cowork가 Builder 뒤 Judge 지시문에 그대로 넣는다)

- J1 범위: 허용 경로 밖 변경 0, 정책·상태·일지 파일·.claude·CLAUDE.md·tools 변경 0, 줄바꿈만 다른 파일 0, 테스트 수 감소 0, 약화된 assert 0.
- J2 주문 경로 없음: 새·바뀐 파일에서 `/api/us/ordr`·`ust2000`·`overseas orders`·`kiwoom_order`·`order_submit` 0건. 키움 호출은 기존 브리지의 읽기
  조회 2종(ust21150·ust21050)과 프로필 별칭뿐.
- J3 체결 추정 없음: 결과 분류는 ust21150 cntr_qty·cntr_uv만 쓴다. 종가·가격으로 체결·수량을 만드는 경로 0.
- J4 비교 모드 무쓰기: decision_mode compare에서 일지·상태·원장·정책 쓰기 경로 0. apply에서도 재확인 하나만 어긋나면 쓰지 않는다. 일지 사슬·멱등.
  새 항목 뒤에도 S7 검토 결과(journal_view)가 같다.
- J5 기준값 불변: 상수 표의 모든 값이 출처(규칙 파일·설계·정책·R-REC1 문서)와 같다 — 예산 1.55·1.85·1.9·0.4·R-REC1 수치·V6 4값·C8 문턱·
  σ 배수·데드밴드 2%·후회 예산 3%·현금 여유 0.25%. 새 문턱을 만든 곳이 없다(분할 의심 0.45·3%는 판정을 막기만 하는 자료 검사).
- J6 fail-closed: 연구 기록·등록부·종가·S7·T1 결과 중 하나라도 없거나 낡으면 매수 주문표 0. R-REC1은 매도를 막지 않는다.
- J7 카드 근거: 등록부 자격(항목·수락·절 해시·커밋) 없이는 매수·매도 주문표 0(NOCARD 포함). 등록부 첫 내용이 카드 원문 강도와 같다(종목마다
  표본 대조, 새 판단 0). 기술 신호가 정적 근거에 없다.
- J8 산식: 황금 테스트 G-1~G-3을 직접 다시 돌려 확인. 매수 목표가 S7 함수(투영 E ≤ 1.55·상한)로만 정해진다. r을 올리는 경로 0.
- J9 가격: LOC만, 반올림 방향(매수 내림·매도 올림), 환산 범위 ±1%, 긴급·MOC 주문표 0.
- J10 유효·재발행·R-NE1: 1세션, 미체결 2회·미입력 연속 2회 닫힘, 미입력 뒤 상한 ≤ 첫 상한, 사용자 단계 없음(7절 Q2 결과와 일치).
- J11 권한 칸: quantity_authority "ORDER_TICKET_HUMAN_ENTRY"는 주문표(와 그 일지 payload)에만, 다른 곳의 값은 그대로. order_authority false·
  execution_quantity null 고정.
- J12 대조·리플레이: 부록 B 범주와 부록 C 기준이 코드에 결과 보기 전 값으로 들어 있다(테스트로 고정). 오라클이 주문표 경로와 다른 코드 경로다.
  Judge가 SOXL·NBIS 실자료 3세션(열림 1·닫힘 2)을 손으로 다시 계산해 맞춘다.
- J13 Windows: ps1 ASCII, 두 작업 이름만, 실행 제한·시간대 검사, 실행 안 함.
- J14 보안: 계좌번호·계좌 라벨·이름이 출력·픽스처·로그에 없다(연구 기록·주문 조회 응답의 acnt 칸 미수집).
- J15 일지 읽는 쪽: AUTO_CORE 항목(user_message null)에서 load_journal이 예외 없이 OK, S7 검토 불변, 채점 보고서 head가 맞아 journal_pending CURRENT.
- J16 새 사용자 단계 0: 주문 입력·"켜"·정책 "적용" 말고 사용자에게 묻거나 실행을 요구하는 경로가 없다(카드 바뀜·대조 차이는 Cowork 몫).

## 7. 병합 전 사용자 결정 (한 줄로 답 — 병합 승인과 함께)

답 형식: `T2 병합: Q1 a, Q2 a, Q3 a, Q4 a` (답이 없는 항목은 현행 유지 — Q1·Q2는 그 부분 주문표를 만들지 않는 쪽, Q3·Q4는 설정 키를 넣지 않는 쪽)
주간 사용자 손 비용(CLAUDE.md Touch budget): 이 결정 1번(병합과 함께) + "켜" 1번(한 번만). 운영 중 일상 손은 저녁 주문 입력뿐이고 T2가 더하는 일상 단계는 0.

| Q | 무엇 | 선택지 (권장 먼저) |
|---|---|---|
| Q1 | 설계 13절 K3 값의 채택 범위(A7 a의 주문 1단계) | a) K3-1(1단계·주문표 수량, 입력은 사람)·K3-2(정책 간격 × 단계, 후회 예산 3%, 데드밴드 2%, 첫 진입 ½)·K3-3(매수 LOC +0.5σ, 계획 축소 LOC −1σ)·K3-4(1세션·재발행 1회·G0)·K3-5(일지 항목)·K3-7(매수 목표 = 상한과 E 1.55 중 작은 값)·K3-8(같은 날 매도→매수 없음)·K3-9(점검 대신 코어가 계산)를 이 지시문대로 채택. K3-6(확률)·위원회는 코어에 없음 · b) 값 일부 수정(어느 값인지 적기) |
| Q2 | R-NE1 미입력 처리 | a) 제한 1(사용자 "다시/종료")을 없앤다 — 코어가 다음 날 새 기준가로 관문을 다시 통과할 때만 다시 내고 연속 미입력 2회면 닫는다(사용자 단계 0). 제한 3(다시 낼 때 매수 상한 ≤ 첫 상한)은 유지(낮추기만 하는 쪽) · b) 제한 1만 없애고 제한 3도 없앤다(상한은 새 기준가 산식) · c) 현행 유지(미입력 다음 날 사용자 답이 올 때까지 그 결정 주문표 없음) |
| Q3 | 재설계 3-2 ⑤ "1회 주문 크기·하루 주문 수" 관문 값(지금까지 정한 적 없음) | a) 매수 주문표 1건 ≤ 자산 10%(위원회 Full 기준 "자산 10%"를 재사용), 하루 주문표 ≤ 3건, 매도는 금액 상한 없음 · b) 다른 값(적기) · c) 두지 않음(지금처럼 E 1.55·종목 0.4배·첫 진입 ½·데드밴드만) |
| Q4 | 무인 LLM 연구 기록의 공식 사실 하나로만 생긴 강 근거 | a) 단계 상한 ½(같은 방향 카드 정적 강 근거가 함께 있으면 설계대로 1) · b) 설계 G3 그대로 1 |

## 8. 병합 뒤 배포 (Cowork가 진행, 사용자 손은 ★)

1. Cowork: Builder 결과 확인 → Judge 지시문 → ★ Judge 세션 1번(명령 한 줄 제공).
2. ★ 병합 + 작업 등록(PowerShell 한 블록, Cowork 제공) — 7절 답과 함께.
3. Cowork: 정책 제안 P-1(auto_core.json) 적용, P-2(PWR·LITE 등록)는 따로 — ★ "적용" 한 마디(항목별 선택 가능).
4. Cowork: 예약 작업 변경 — ★ 승인 클릭 1번으로 묶음: (a) 06:40 통합 점검 로더에 "연구 기록 쓰기" 단계(실적일 p-earn 형식, 회사 공식 사실, 대시보드
   기록 사본 → research-record.json, 그 파일 하나만 쓰기 허용. 규칙 파일·해시 고정 그대로) (b) "자동 운영 코어 결과 알림"을 08:50으로 옮기고
   LATEST_DECISION.json의 push 후보·주문표를 한 줄로 알리며 dashboard.runCore를 runs/<날짜>.core에, 기록 모드의 dashboard.orders를 orders에 그대로 옮긴다
   (새 수치를 만들지 않음) (c) 통합점검 대시보드 화면: core 칸 표시, orders의 source "auto-core" 표시, option 칸이 없으면 "생략"으로 표시
   (Artifact 재게시). (d) 카드를 고치거나 수락하는 Cowork 절차에 "같은 세션에서 card-evidence-registry.json 갱신"을 넣는다(analysis-linkage-map·INDEX 1줄).
5. Cowork: CLAUDE.md 문구(주문 1단계 quantity_authority, 일지 자동, 연구 기록 계약) — ★ 승인 한 번. 커널 지침 2절 문구 제안(붙여 넣기는 선택).
6. Cowork: 10/13 이후(관심 종목 30분봉이 쌓인 뒤) 외부 오라클 목록을 먼저 쓰고(규칙 원문만 사용, 결과 보기 전 _pending 커밋) → 리플레이 실행 →
   docs/claude/redesign-t2-replay-<날짜>.md(부록 C 판정). R-C 미달이면 기본 처분대로 비교 모드 유지 + 한 번 알림.
7. 비교 모드 5거래일: 매일 decide가 자동 대조, Cowork는 B7만 redesign-t2-compare-explained.json에 설명(CORE_BUG면 일반 변경으로 고침).
8. R1·R2 충족 → 알림 "판정 대조 완료 — 기록 모드 켤 준비됨" → ★ 사용자 "켜" → Cowork가 decision_mode = apply. 관제판 redesign-t2 완료, T4로.

---

## 부록 A. 통합 점검 규칙 파일 v3.12.2 분해 — 결정론(코어로) / LLM(연구·설명에 남김)

**A-1 결정론 → 코어 (T2가 옮김)**

| 규칙 파일 위치 | 내용 | 코어 위치 |
|---|---|---|
| 대상 | 보유 = 잔고 poss_qty > 0 전부, 관심 = members 중 미보유, 참고 SOXX(+ 업종 "A1 전력" 있으면 GRID) | T1 종목 목록 + F12 P-1(GRID) |
| 문서 읽기 python ⓐⓑⓕ | MEMBERS·LAST·HASH·HELD_STATE·NOCARD | F2 등록부(해시는 절 단위로) |
| 관심 명단 | members ≤ 5, cardStatus "수락" 아니면 ③ 확인 필요, 명단 못 읽으면 보유만 | F4 |
| 종가 정의·확정 | 정규장 종가(잠정), 일봉 등락 직접 계산, 52주 필드 미사용 | F1(D2 정의, 모두 잠정 표시) |
| MVLL 분할 | 6/26 이후 행만 | F1 분할 보정(corporate-actions) |
| 1)·1-1) | 잔고·현금·미체결·상태 대조, poss_qty·fc_entra·fc_pymn_alowa·fc_ord_alowa 정의 | T1(그대로) — decide는 결과만 읽음 |
| 2) | 종가·등락·EMA10/20/50·RSI14·20세션 고저·ATR14·평균 거래량·σ60·정규장 고저·종가 위치·장중 낙폭 | F1 |
| 2-2) python | 공시 피드 새 공시 목록(사실 존재까지) | 표시만(코어 판정에 안 씀), 본문 판정은 LLM |
| 2-3) ① | N = Σ 배수 × 비중, 정책 미등록 1배 가정(PWR·LITE·MRVL) 또는 확인 필요, 종목 명목 0.4 | F4 노출 블록 |
| 2-3) ② | S7 E·대역·신선도, E 없으면 N 하한 | F4 |
| 2-3) ③ | R5 고점 −30%(≤ 0.70P 검토, ≤ 0.75P 근접), 기준일 규칙 | S7 peak_reviews 재사용 |
| 2-3) ④ | R-REC1 EV1·EV2·EV3ⓐ·EV4·EV5, C0·L0, RG2·RG3·RG4, DS1, 닫힘 | F1 |
| 3) 공통 C·지속·합치기·별칭 | C1~C8(±), 상태형·사건형, 같은 종류 1개, V3·S5 등 카드 고유 | F1 + F2 |
| 3) 신고가 돌파 유지 | 2세션 | F1 |
| 3) 카드 가격 트리거 | V3, S4, S5, S6, S8, N6, N8, N9, U5~U8, BE5~BE8, DL5~DL8, AM5~AM8, X5~X8 | F1 + F2 |
| 3) V6 계좌 점검선 | 4개 선, 여유 % | F1 |
| 3) 매수 요건 ①②④⑤⑥ | 금지 구간 계산·노출·현금·상품 승인·M6 파일·R-REC1 | F4 |
| 3) 매수 요건 ③ | 카드 표 N + 새 M, 공식 1 또는 가격 2 | F4(N = 등록부, 공식 사실 = 연구 기록) |
| 점검 상태 ㉠~㉥ | 연결·잔고·종가·카드·검색·명단 | decide status·reasons |
| 대시보드 기록 칸 | triggers·buyReq·account·shock·peakReviews·calendar 등 숫자 칸 | F8 dashboard.runCore |
| 알림 ①②③④⑥⑨⑩ 조건·반복 억제 | 상태 변화 비교 | F8 alerts |
| v3.12.3(흡수) | "C 단독" 근거 구성 표시, 위험 예산 1.55 표기, ⑪ 직전 실행 누락 | F4 composition / 표시 / decide가 직전 decision.json 날짜로 계산 |

**A-2 LLM 판단 → 연구·설명 작업에 남김 (결과는 연구 기록 형식으로만 코어에)**

| 위치 | 내용 | 코어로 들어가는 길 |
|---|---|---|
| 문서 읽기 ⓒⓓⓔ, 넓게 읽기 | 카드·원장 산문 읽기, 문서 변경 대조 | 등록부 갱신(Cowork, 카드 수락 때) |
| 2-1) 개장 전 기록 | 공식 사실 재사용, 매크로 수치 표시 | 연구 기록 official_facts(URL 있는 것만) |
| 2-2) 공시 본문 판정 | WebFetch로 본문 확인, 호재·악재 | 연구 기록 official_facts |
| 3) 강 후보 | S2·S3·S7, N2·N3·N4, U2·U3, BE2·BE3, DL2·DL3·DL9, AM2·AM3, X2·X3, kill ①~③ | official_facts(direction·card_trigger_ids) |
| 3) 호재 기준 (a)·기준 확인 요청 | 인수·인사·제품 제외, 사용자 지정 | criterion_a |
| 3) 실적 일정 점검 | 실적일 공지 WebSearch | earnings(p-earn 형식) |
| 3) N10·BE9·AM9·MRVL 참고 | 로그·표시 | 없음 |
| 3) M6 "인정 규칙" 절 읽기 | 10/8 철회 상태 | 등록부(현재 철회 — 세지 않음) |
| 4) SAVE · 5) 뉴스 · 6) saveticker · 7) 외부 주장 원장 | 참고·가설 | 없음(설명 작업) |
| R-REC1 EV3 ⓑ·RG1 | 뿌리 테제 훼손 공식 확인 | official_facts.root_thesis_damage |
| 출력 (a)~(k) 한국어 보고, 결정 필요 | 설명 | 설명 작업(T4에서 축소) |
| 기록 전 검증 1·2 | LLM 옮겨 적기 오류 잡기 | 코어는 스키마 검증으로 대신(LLM 경로에는 T4까지 남음) |
| 로더 3단계 SCN-27H1 | 표시 전용 | 없음 |

**A-3 공통 규칙 정의 (규칙 파일 3) 그대로 — F1 테스트의 기준)**
- C1− RSI14 ≥ 70 또는 종가 ≥ EMA20(t−1) + 2×ATR14(t−1) ↔ C1+ RSI14 ≤ 30 또는 종가 ≤ EMA20(t−1) − 2×ATR14(t−1).
- C2− 정규장 고가 ≥ EMA20(t−1) + 2.5×ATR14(t−1) · 종가 위치 ≤ 0.35 · 거래량 ≥ 직전 20세션 평균 × 1.2 ↔ C2+ 정규장 저가 ≤ EMA20(t−1) − 2.5×ATR14(t−1) · 종가 위치 ≥ 0.65 · 거래량 ≥ 평균 × 1.2.
- C3− 종가가 EMA20 아래 2회 연속(그 앞 종가는 위) ↔ C3+ 위로 2회 연속(그 앞은 아래). 각 세션 종가를 그 세션 EMA와 비교.
- C4− 직전 세션 종가 > 그 전 20세션 종가 고점(돌파선)이고 이번 종가 < 돌파선 ↔ C4+ 직전 종가 < 그 전 20세션 종가 저점(붕괴선)이고 이번 종가 > 붕괴선.
- C5− 붕괴선 = 1세션째 기준 직전 20세션 종가 저점(2세션째도 같은 선), 종가 < 붕괴선 그리고 < EMA10이 2세션 연속(1세션째 = pending) ↔ C5+ 돌파선(1세션째 기준 직전 20세션 종가 고점, 2세션째도 같은 선) 위 + EMA10 위 2세션 연속(1세션째 pending, 그사이 돌파선 아래면 "돌파 무산").
- C6− EMA20 아래에 있던 종가가 EMA20 아래 1.5% 이내까지 반등한 세션 다음 세션에 전일 대비 하락 마감 + EMA20 아래 유지 ↔ C6+ EMA20 위에 있던 종가가 EMA20 위 1.5% 이내까지 눌린 세션 다음 세션에 전일 대비 상승 마감 + EMA20 위 유지(DL6·X6와 같음).
- C7− 기준 (a) 공식 호재 뒤 2세션 안에 종가가 발표 전일 종가 아래로 ↔ C7+ 회사 공식 악재 뒤 2세션 안에 발표 전일 종가 위로.
- C8∓ 하루 종가 변화 ≤ −T / ≥ +T(경보, 근거 아님). T = 카드 값(SOXL 20%·5세션 25%, NBIS 15%, 관심 카드 10%), 없으면 배수 1배 10%·2배 15%·3배 20%(배수 모르면 10%).
- 지속: 상태형 C1·C3·C5·V3·S4·S5는 성립하는 동안 1개, 사건형 C2·C4·C6·C7은 충족일 포함 5세션 1개(창 안 재충족은 창 재시작, 같은 번호 반대쪽이 충족되면 그날 해소).
- 합치기: 같은 종류(추세선 이탈 C3−·V3·S4·S5·N6·U7·BE7·DL7·AM7·X7 / 신고가 돌파 C5+·U5·BE5·DL5·AM5·X5 / 눌림 반등 C6+·U6·BE6·DL6·AM6·X6 / 호재 뒤 하락 C7−·N5·U4·BE4·DL4·AM4·X4 / 급락 경보 C8−·S6·N8·U8·BE8·DL8·AM8·X8)는 종목당 1개, 카드 정의 우선. C1과 C2는 다른 종류.
- 카드 고유: V3 MVLL 종가 < EMA10(상태형) · S5 SOXL 종가 < EMA50 뒤 2세션 안 미회복(S4와 겹치면 1개) · S6 SOXL −20%/5세션 −25%(경보) · S8 SOXL 종가 ≤ 98.66(경보) · N8 NBIS −15%(경보) · N9 NBIS 종가 ≤ 193.50(경보). 카드 정의는 그 종목이 보유(SOXL·NBIS·MVLL) 또는 members(MU·BE·DELL·AMD 정의)일 때만.
- 매수 불가 상품(신규 매수 승인 목록 밖 보유, 예 MVLL): + 쪽은 계산·표시만.

**A-4 R-REC1 (규칙 파일 2-3 ④ + recovery-gate 문서)**
EV1 SOXX 1일 ≤ −2σ60 · EV2 SOXX 종가 ≤ 직전 20세션 종가 고점 × (1 − 3σ60) · EV3 ⓐ 문서의 사용자 지정 날짜 ⓑ 공식 테제 훼손 + 같은 날 SOXX ≤ −1σ60 · EV4 총자산 ≤ 25,626.55 또는 ≤ S7 hwm × 0.9 · EV5 종목 1일 ≤ −2σ60(그 종목만). 최근 60세션 안 가장 최근 이벤트가 기준. RG1 2세션 경과 + 훼손 공식 확인 없음 · RG2 벤치마크 종가 ≥ EMA50 그리고 후보 종가 ≥ 후보 EMA50(SMA200 "확인 필요" 표시) · RG3 연속 2세션 벤치마크 종가 > C0 그리고 이벤트 뒤 저가 < L0 세션 없음 · RG4 판정일 |1일| ≤ 2σ60 그리고 최근 5세션 σ ≤ 1.5σ60. DS1(종가 < L0 또는 < EMA50)이면 RG3 처음부터. 닫힘 = RG1~RG4 모두 또는 마지막 DS1(없으면 이벤트일) 뒤 20세션 + RG2.

## 부록 B. 판정 대조 범주 (사전 등록 — 결과 보기 전 고정)

| 코드 | 이름 | 자동 판정 조건 |
|---|---|---|
| B1 | SAME | 같음 |
| B2 | DATA_DEFINITION | 코어 값이 그 조건 경계에서 가까움: 가격 조건 여유 ≤ 종가의 1.0%, RSI ± 2.0, 고가·저가·거래량을 쓰는 조건(C2·ATR 띠)은 여유 ≤ 3%. 알려진 정의 차이 넷 — ① 종가(코어 = 마지막 정규장 봉 종가, LLM = 16:00 봉 시가) ② 지표 시작 구간(코어 = 2026-04-01부터 30분봉, LLM = 키움 일봉 pages 3) ③ L0·이벤트 뒤 저가(코어 = 정규장 저가, LLM = 일봉 저가이고 3% 넘게 낮을 때만 정규장 저가, v3.12.1) ④ MVLL 창(LLM은 6/26 이후 행만) — 이 넷에 걸린 조건은 여유 ≤ 3%까지 B2 |
| B3 | LLM_ONLY | 코어가 판정하지 않는 칸(공식 사실·kill·뉴스·호재 기준·원장·SAVE·saveticker·near·실적일 공지 X1) — 비교에서 뺀다 |
| B4 | RESEARCH_RECORD | 그 칸이 연구 기록을 필요로 하는데 기록이 없거나 늦거나 항목이 검증에서 버려짐 |
| B5 | RULE_CODE_PRECEDENCE | 코어가 병합된 코드·정책을 따르는 알려진 곳: p-earn r1(미확인 = 금지 구간) 대 "미공지만으로 막지 않음", ③ LLM "info" 상태, V6 대 S7 HWM(둘 다 표시), 정책 미등록 PWR·LITE(주문표만), S7 현금 정의 |
| B6 | TIMING | LLM 실행의 기준 세션이 다르거나 점검 불완전 |
| B7 | UNEXPLAINED | 위에 없음 → Cowork가 docs/claude/redesign-t2-compare-explained.json에 LLM_ERROR(규칙 문장 인용) 또는 CORE_BUG(일반 변경으로 수정)로 적는다. LLM_ERROR로 모두 설명된 날은 연속 일수에 들어간다 |

## 부록 C. 리플레이 사전 등록 (결과 보기 전 고정 · 기간 2026-07-10 ~ 2026-10-09)

- 자료: 저장된 정규장 30분봉(분할 보정), 운영 달력. 자료가 없는 종목·세션은 "자료 없음"으로 세고 통과로 치지 않는다.
- P-R1 포트폴리오: 기간 내내 rev 24 상태(MVLL 159 · SOXL 53 · NBIS 13 · 현금 = rev 24 기준 스냅샷 주문가능액 12,467.71)를 고정(D, 반사실).
  rev 24의 E(1.73)는 투영 E ≤ 1.55 위라 늘리는 매수가 거의 늘 막힌다 — 그래서 매수 경로 검사는 P-R2로 한다.
- P-R2 포트폴리오(매수 경로 검사용): NBIS 13주 + 나머지 전부 현금(같은 자산 규모, MVLL·SOXL 0). 기간 내내 고정(D).
- 카드: 2026-10-10 등록부를 소급 적용(D). 공식 사실: 없음(가격 단서 + 등록부 정적 근거만).
- E-R1 실적: docs/claude/redesign-t2-measurements-2026-10-10.json의 SEC 8-K 2.02 날짜를 VERIFIED로(발표 30일 전부터 알려진 것으로 봄), 그 밖의 세션은 그날 16:30 ET에 확인한 NOT_ANNOUNCED로 본다(리플레이 전용 가정, D). NBIS는 기록 없음 = 금지 구간(fail-closed).
- R-A 실제 주문 앵커: 실측 파일의 실제 주문 날(7/31, 8/11, 8/12, 8/20, 10/5~10/9)마다 그 종목·방향의 코어 결과(주문표 또는 첫 차단 사유 코드)를 적는다. 통과 = 모든 앵커에 결정론 사유 코드가 붙음(UNEXPLAINED·예외 0). 주문표가 나와야 한다는 뜻은 아니다(당시는 카드·관문이 달랐다).
- R-B 관문 누수: P-R1·P-R2 각각, 오라클이 "열림 + 모든 관문 통과"로 본 (종목, 방향, 세션)마다 주문표가 있거나 허용 사유(DEADBAND·LOT_ZERO·CASH_ZERO·REGRET_ZERO·G2B_CAP)만 있어야 한다. 오라클은 둘: Builder 오라클(주문표와 다른 코드 경로)과 **Cowork 외부 오라클**(병합 뒤, 리플레이를 돌리기 전에 Cowork가 규칙 파일·설계 원문만 보고 따로 쓴 계산으로 만든 목록을 docs/claude/redesign-t2-replay-oracle-<날짜>.json에 먼저 커밋). 통과 = 두 목록 모두 100%이고 두 오라클의 차이는 Cowork가 원문 인용으로 설명.
- R-C 빈도: 주문표 수(방향·종목별, P-R1·P-R2), 막힌 사유 상위 5개(세션 수), 주문표 0인 세션 비율. **P-R2에서 3개월 매수 주문표가 0이면 R-C 미달**("관문 상시 닫힘" — 재설계 6절 사전 부검). 미달의 기본 처분 = 비교 모드 유지(NO_CHANGE), 막힌 사유 순위를 붙여 사용자에게 한 번 알린다.
- Judge 재계산: SOXL·NBIS 실자료 3세션(열림 1·닫힘 2)을 손으로 다시 계산.

## 부록 D. 실측 사실 (2026-10-10 Cowork, 상세는 docs/claude/redesign-t2-measurements-2026-10-10.json)

1. 키움 기간별 주문내역(ust21180)은 조회 기간 3개월 이내(넘으면 code 20). 2026-07-11~10-10 실제 주문 30행: LOC 3건(10/7 MVLL 59 체결, 10/8 SOXL 35 미체결, 10/9 SOXL 22 체결), 그 밖은 지정가·Stop Market.
2. LOC 표기 = 매매구분 "Limit On Close". 10/9 SOXL LOC를 17:29 KST에 넣어 05:00:02 KST 종가 체결(139.76). ord_dt = KST 주문일. 미체결 LOC는 주문상태 "무효주문"(10/9 조회 기록).
3. ust21150(query_tp 1)은 체결 없는 주문 행도 돌려준다(주문수량·체결수량·취소수량·주문단가·체결단가·주문상태). T1 브리지 SAFE_FIELDS에 결과 분류에 필요한 칸이 있다(0단계 e에서 다시 확인).
4. 실제 수수료 = 체결금액의 0.0699%(8건), 매도 제세금 약 0.002%, 매수 0. 결제 행(거래내역)은 미국 세션 2 한국 영업일 뒤.
5. 실적 발표(SEC 8-K 2.02, 2026-04 이후): AMD 5/5·8/4 장후, BE 4/28·7/28 장후, DELL 5/28·9/1 장후, LITE 5/5·8/11 장후, MRVL 5/27·8/27 장후, MU 6/24·9/30 장후, PWR 4/30·7/30 장전. NBIS는 6-K라 항목 번호 없음 — 확인 필요.
6. 종가 이력은 MVLL·NBIS·SOXL·SOXX 4종목만(2026-04-01~10-09, 133세션). 관심 종목(MU·BE·DELL·PWR·LITE) 30분봉은 아직 없음(10/13 첫 코어 실행이 2026-04-01부터 받음). GRID 미수집.
7. 분할 표지: 키움 수정 일봉은 분할일에 upd_stkpc_tp 3231·upd_rt −66.667(MVLL 6/26), 원주가 30분봉에는 분할 표지가 없다("1f"만). 공식 분할 기록은 corporate-actions.json(MVLL 1건).
8. alert_policy: 배수(SOXL 3·TQQQ 3·MVLL 2·BE·MU·NBIS·DELL·AMD·DRAM 1), card_stock_core BE·MU·NBIS·DELL·AMD, allowed_index_etfs SOXL·TQQQ·DRAM, sell_only MVLL, 문턱 1.85·1.25·1.55·1.9, 종목 상한 0.4(SOXL·TQQQ 면제). PWR·LITE 없음.
9. S7 검토는 이미 카드·실적·제안 입력(--cards·--earnings·--proposals)을 받는다(지금은 모두 미제공 → earnings_provided false).
10. decision_journal.json = 해시 사슬 6항목(s5_activation 1·card_decision 3·card_user_decision 2), 스키마의 entry_type은 5종 열거.
11. 06:40 통합 점검 기록 시각: 10/9 07:30, 10/10 06:50.
12. 메인 체크아웃 tools/ 아래 차이는 줄바꿈만(autocrlf 기준 내용 차이 0), docs/claude 미커밋 변경은 다른 세션 것(23:30 자동 커밋 대기).
