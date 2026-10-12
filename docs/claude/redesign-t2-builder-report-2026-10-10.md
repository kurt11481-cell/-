---
id: redesign-t2-builder-report-2026-10-10
title: 재설계 T2 Builder 보고 — 판정 규칙 코드화 · 주문표(주문 1단계) · 일지 자동
date: 2026-10-10
worktree: .claude/worktrees/t2-core (branch worktree-t2-core, base cd6a56d)
prompt: docs/claude/redesign-t2-builder-prompt-2026-10-10.md (3~6절·부록 A~D)
class: 권한·한도 변경(옛 K3) — 수동 경로. 이 보고 뒤 독립 Judge(6절 J1~J16)
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY". 키움 주문 도구·주문 API 호출 0, 키움 실제 호출 0(테스트는 가짜 자료)
consumers: T2 Judge(Cowork 작성) · Cowork 배포(지시문 8절) · 관제판 redesign-t2 · 06:40 통합 점검 로더(연구 기록 쓰기 단계, 배포 때)
---

# 재설계 T2 Builder 보고 (2026-10-10)

> 지시문과 실측 파일은 이 worktree 생성 시점(HEAD cd6a56d)에 아직 커밋되지 않아 main 체크아웃의 사본을 **읽기만** 했다(지시문 1절 "23:30 자동 커밋 뒤 시작"보다 먼저 시작됨). 리플레이 기본 경로 `docs/claude/redesign-t2-measurements-2026-10-10.json`은 그 자동 커밋 뒤에 존재한다.

## 1. 0단계 사실 확인 · BLOCKED 여부 · 부록 A 대조

**BLOCKED: 없음.** (SAFE_FIELDS·권한 경로 수정 불필요, 판단이 필요한 범위 이탈 없음)

| 항목 | 결과 |
|---|---|
| a 기준선 | HEAD cd6a56d 전체 스위트(`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py" -v`, 직접 실행): **Ran 2710 · FAILED (failures=19, errors=9, skipped=2) · 실패 줄(FAIL/ERROR) 28개** · `def test_` 2671. 모듈별(원본 출력에서 직접 셈): test_v2_6_7_session_aware_kiwoom_priority 14(subTest 4줄 포함), test_materialize_kiwoom_session_aware_acceptance_candidate 2, test_nbis_v4_kiwoom_price_authority 2, setUpClass ERROR 3(holding_baseline_observation_audit · mvll_canonical_volume_lineage · provider_limitation_audit), instrument_identity_authority 1, materialize_instrument_identity_artifact 1, evaluate_timing_integration 1, portfolio_decision_dashboard 1, portfolio_decision_order_intent 1, nbis_v3_shadow_activation 1, validate_research_packet 1. T2와 무관한 기존 실패(인수 고정·활성화 자료 관련) |
| b 재사용 경로 | **수정 없이 가능.** `run_portfolio_exposure_review.run(--earnings, --proposals)` 한 번으로 E·대역·멈춤·종목 상한 위반·R5(peak_reviews)·줄이기 항목(reduce, 순서 1·3)과 제안마다 `_evaluate_proposal(new_buy_within_band)` 결과(status DISPLAY = 사유 없이 통과)를 얻는다 → W* = 0.001 격자에서 통과한 가장 큰 비중. `ExposureModel`(매도 뒤 경로 표시용 투영 E), `earnings_blackout`, `floor_to_step`·`WEIGHT_STEP`, `effective_exposure`, `build_exposure_review`(리플레이), `_sample_std`(σ60 같은 식 — 비공개 이름을 import만 함, 파일 수정 0). increase_blockers·reduce_recommendations는 build_exposure_review 안에서 그대로 쓰인다(직접 호출 안 함). **portfolio_exposure·run_portfolio_exposure_review·regular_session_close_history·corporate_actions 추가·수정 0.** |
| c 봉·분할 | `parse_page`(행 검증) + `build_history`(세션·종가) + `INTERVAL_MINUTES` 재사용. parse_page는 종가만 돌려주므로 시가·고가·저가·거래량은 검증된 같은 페이지 행을 다시 읽는다(같은 "확정 봉 = 뒤 봉이 있는 봉" 규칙). 정규장 봉 = 달력 `core_open_at` ~ `core_close_at`−30분(조기 폐장은 달력대로). 분할: `corporate_actions.adjust_closes`를 시가·고가·저가·종가 칸별로 재사용, 거래량 × new/old만 새로 씀. `applicable_actions`·`applied_summary` 재사용 |
| d T1 출력 | `kiwoom_broker_snapshot.shadow.json`: holdings[].held_quantity(=poss_qty), cash.order_available_cash(=fc_ord_alowa), cash.foreign_currency_deposit(=fc_entra, T1 cash_components.deposit). `reconcile.json`: status·reasons·fills(I2로 설명된 체결: ticker·side·quantity·session_date). `result.json`: status. 상태 파일 최신 여부 = 상태 파일 보유·현금이 그날 스냅샷과 같음(수량 일치, 현금 $1 이내) — G1 |
| e 브리지 | ust21150 SAFE_FIELDS에 ord_no·stk_cd·slby_tp_nm·frgn_trde_tp·ord_qty·cntr_qty·cncl_qty·ord_uv·cntr_uv·ord_stat_nm·ord_time(+crnc_code·ord_remnq·cntr_time·rsrv_tp) **모두 있음**. ust21050(account_open_items) SAFE_FIELDS 있음(행 수만 씀). SAFE_FIELDS 추가 불필요 → BLOCKED 아님 |
| f 일지 읽는 쪽 | **확인: `_entry_inconsistency`가 `user_message.upper()`에서 AttributeError** — entry_inconsistencies의 except 튜플(KeyError·TypeError·ValueError·ArithmeticError) 밖이라 load_journal이 예외로 죽는다. F7에서 AUTO_CORE 항목을 코드 검사 전에 따로 검사하도록 고침. `journal_view`는 종류로 거르므로 새 항목에 영향 없음(테스트로 고정). `score_decision_journal._subjects`는 card_decision·card_user_decision만 보므로 수정 불필요(테스트로 고정). `portfolio_status.journal_pending`은 채점 보고서 head = 일지 마지막 항목 해시를 요구 → decide가 일지 쓰기 직후 채점기를 같은 프로세스에서 1회 실행(F7) |
| g 규칙 파일 대조 | 부록 A-3·A-4 수치와 규칙 파일 v3.12.2 3)·2-3)④가 **모두 같음**(70/30, ATR 2/2.5배, 종가 위치 0.35/0.65, 거래량 1.2배, 1.5%, 5세션 창, C8 문턱, V6 4값, R5 0.70/0.75, R-REC1 2σ/3σ/1σ/2σ, RG4 2σ·1.5배, 20세션). 정의 차이(수치 아님): ① 규칙 파일 L0 = 일봉 저가(정규장 저가보다 3% 넘게 낮을 때만 정규장 저가, v3.12.1) ↔ 지시문 L0 = 정규장 저가 — 지시문대로, 부록 B ③으로 분류 ② 규칙 파일 ATR·C2는 일봉(시간외 포함 가능) 고저 ↔ 코어 정규장 고저 — 부록 B ② ③ C3−는 "그 앞 종가는 위" 조건이 있고 카드 별칭(S4·N6·U7·BE7·DL7·AM7·X7)은 그 조건이 없다 — 카드 정의 우선(규칙 파일 "같은 종류 합치기")대로 구현. 규칙 파일이 맞아야 하는 수치 불일치는 없음 |

## 2. 바꾼 파일 · 줄바꿈 · 재사용 함수

허용 경로(지시문 4절 "범위") 밖 변경 0. `auto_core_reconcile.py`·`score_decision_journal.py`·portfolio_exposure 등은 **수정하지 않았다**(필요 없었음).

| 구분 | 파일 | 내용 |
|---|---|---|
| 새 scripts | auto_core_bars.py | F1 정규장 일봉(OHLCV)·INCOMPLETE·분할 보정·분할 의심 |
| | auto_core_rules.py | F1 상수표(CONSTANTS, 출처 주석)·지표·C1~C8·카드 트리거·합치기·V6·R5 근접·R-REC1·M6 ④ |
| | auto_core_inputs.py | F2 등록부(절 해시·수락·커밋 검사)·F3 연구 기록 검증·관심 명단·M6 문서 |
| | auto_core_tickets.py | F4 요건 ①~⑥·회로·G0~G5·G2b, F5 계산기(후회표·가격·재발행 원장·매도 뒤 경로), F6 결과 분류 |
| | auto_core_decide.py | F8 decide 실행, `evaluate_session`(decide·리플레이 공용 F1~F5), 알림 후보·대시보드 묶음, F7 호출 |
| | auto_core_compare.py | F9 판정 대조(부록 B)·연속 일수·설명 기록 검증·CLI |
| | auto_core_replay.py | F10 리플레이(부록 C)·다른 경로 오라클·외부 오라클·요약 md |
| 수정 scripts | auto_core.py | `decide` 하위 명령(지연 import), 문서 줄 |
| | portfolio_review_journal.py | 항목 3종·`append_auto_core_entries`·`auto_core_payloads`·`_auto_core_inconsistency`(읽는 쪽 보호)·`_atomic_write(newline=)` 선택 인자(기본값 그대로). CONFIRMATION_METHODS·propose/show/apply 경로 불변 |
| | run_auto_core.ps1 | `-Command daily|decide`(기본 daily, 그 밖 exit 3), 로그 이름에 명령 포함, ASCII |
| | register_auto_core_task.ps1 | InvestmentV2-AutoCore(06:15 daily) + InvestmentV2-AutoCoreDecide(화~토 07:45, 60분, IgnoreNew, -Command decide) 두 이름만, -PlanOnly·KST 검사 유지, 실행 안 함 |
| 새 schemas | auto-core-decision · auto-core-ticket · auto-core-card-registry · auto-core-research-record · auto-core-compare(설명 기록 정의 포함) · auto-core-replay | |
| 수정 schemas | auto-core-config | 선택 키 7개(decision_mode, decision_compare_days_required, decide_schedule_kst, reissue_buy_cap_not_above_first, max_buy_ticket_pct_of_equity, max_tickets_per_day, research_only_strong_r_cap) |
| | portfolio-review-journal(.·-payload) | entry_type 3종·AUTO_CORE·confirm_code/user_message null 허용(일치 검사는 코드), payload 새 칸 |
| 새 tests | test_auto_core_rules/tickets/decide/compare/replay.py, fixtures/auto_core_t2/helpers.py · g3-closes-2026-10-08.json(근사 종가 값만, 계좌 정보 없음) | |
| 새 문서 | references/auto-core-decision.md, docs/claude/card-evidence-registry.json, docs/claude/redesign-t2-policy-proposals.json, 이 보고 | |

- **줄바꿈:** 수정한 기존 파일 9개는 원래대로 CRLF(Write로 바뀐 register 스크립트는 CRLF로 되돌림). 새 파일도 작업 트리 관례대로 CRLF(autocrlf=true라 저장소에는 LF로 들어감). 줄바꿈만 다른 파일 0.
- **재사용 함수:** run_portfolio_exposure_review.run·build_parser·load_corporate_actions·expected_completed_session, portfolio_exposure.build_exposure_review·ExposureModel·exposure_config·earnings_blackout·floor_to_step·WEIGHT_STEP·effective_exposure·closing_equity·journal_view·_sample_std, regular_session_close_history.parse_page·build_history·closes_by_session·calendar_from_snapshot·load_production_snapshot·INTERVAL_MINUTES, corporate_actions.adjust_closes·applicable_actions·applied_summary·validate_corporate_actions, auto_core_reconcile.load_config·git_provenance·apply_guard_reasons·_read_passed·_decimal·_repo_relative, auto_core.kiwoom_profile·known_exchange, kiwoom_account_readonly_bridge.invoke_account_bridge_batch(읽기 2종), score_decision_journal.main, validation_common.*.

## 3. 테스트 · 황금 테스트 · 리플레이 스모크 · 스키마 감사

- **대상 테스트:** `-p "test_auto_core*"` → **Ran 223, OK (skipped=1)** (T1 test_auto_core.py 89 + T2 134; 건너뜀 1 = 실자료 리플레이 스모크 — 30분봉 페이지가 main 체크아웃에만 있어 worktree에서는 skip, main에서는 실행됨). 일지 관련 기존 테스트(test_portfolio_review_journal 14, test_decision_journal_cards 30) 통과.
- **전체 스위트(변경 뒤, 같은 명령 직접 실행):** **Ran 2844 · FAILED (failures=19, errors=9, skipped=3)** · `def test_` 2805.
- **기준선 대비:** 실패 줄 28개가 기준선 28개와 **id까지 동일 → 새 실패 0, 고쳐진 것 0**. Ran +134, `def test_` +134(감소 0). skipped +1 = 실자료 리플레이 스모크(worktree에 30분봉 없음). 첫 변경 뒤 실행에서는 ASCII 검사 2건이 새로 실패했고(5절 27번) 고친 뒤 최종 실행이 위 결과다.
- **스키마 감사:** `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → **PASS, errors []**.
- **황금 테스트(test_auto_core_tickets.GoldenTests):**
  - G-1 MVLL: 간격 236·기준가 37.65·자산 30,255.36·+29.6%/−26.1%·r_max ½ → 후회표 4행이 설계 5절 표와 $1 안(0: $0/$2,319 · ⅓ 78주: $869/$1,553 · ½ 118주: $1,315/$1,160 · 1 236주: $2,630/$0), 예산 $907.66 초과 → 최소최대 ½ = **118주** ✓. 꼬리 −20.8%는 LOC 하한 아래라 미체결 → 후회 $1,848 ✓(설계 5절).
  - G-2 SOXL: σ60 8.35%·기준가 142.45 → 매도 하한 **$130.56**(mult 0.9165, 올림) ✓ OI-20261009-SOXL-2 1절. 매수 상한 = 142.45 × 1.0417(내림) = $148.39.
  - G-3 SOXL(OI-SOXL-2 5절 상태: MVLL 159·SOXL 75·NBIS 13·주문가능액 9,395.20, 10/8 근사 종가): S7 매도 전 E **1.8566**(OI 1.857) ✓. S7 줄이기 계획은 ① MVLL 상한 초과분(0.210→0.200)을 먼저 줄이고 ③ SOXL 목표 **0.271**(계획 전체 뒤 투영 E 1.5495) → **Δ = 75 − ⌊0.271 × 29,037.22 ÷ 142.47⌋ = 20주**. 지시문 예상(22 또는 23)과 다름 — OI는 SOXL만 판다고 계산했기 때문. 같은 S7 함수로 SOXL만 팔면 22주 → E **1.5518**(OI 1.552 재현), 23주 → 1.5381. 테스트는 20(계획 기준)과 22·23 재현 값을 함께 고정. → Judge 확인 요청(5절 23번).
- **4종목 실자료 리플레이 스모크**(main 체크아웃의 저장 30분봉, 읽기 전용, 2026-07-10~10-09 65세션, 출력은 세션 임시 폴더): 예외 0, 스키마 오류 0, 3.5초. R-A **PASS**(앵커 26개 = 13건 × 2 포트폴리오 모두 결정론 코드: SELL_CIRCUIT_CLOSED 11 · NOT_HELD_IN_PORTFOLIO 11 · BUY_CIRCUIT_CLOSED 4), R-B **PASS**(오라클 열림 0 — 관심 종목 30분봉이 없어 매수 회로가 열리지 않음), R-C **미달**(P-R1·P-R2 주문표 0, 막힌 사유 1위 NO_CIRCUIT_OPEN 63·64세션, 모든 세션에 관심 종목·GRID "자료 없음"). 지시문대로 전체 리플레이 판정은 10/13 이후 Cowork(외부 오라클 먼저 커밋).
  - 정정(r2): "매수 회로가 열리지 않음"은 틀렸다(Judge 5절 5). 코어 경로에서는 NBIS 08-13(두 포트폴리오)과 MVLL 08-20(P-R1)에서 매수 회로가 열렸고, 둘 다 관문(REQ1·REQ2·POLICY_UNREGISTERED)에서 막혔다. 오라클 열림 0은 "열림 + 모든 관문 통과"만 세기 때문이라 R-B PASS와 모순은 아니다.

## 4. 등록부 첫 내용 (docs/claude/card-evidence-registry.json — 옮겨 적기만, 새 판단 0)

- 작성: redesign-t2 Builder(옮겨 적기만, 새 판단 0). 스키마 `auto-core-card-registry.schema.json` 검증 오류 0(`validation_common.validate_instance`, 파일에서 다시 읽어 확인). 파일은 UTF-8(작업 트리 CRLF, 저장소 LF — 절 해시는 카드 파일 기준이라 영향 없음).
- 9종목: 보유 MVLL·SOXL·NBIS(묶음 2~4절) · 관심 MU·BE·DELL·AMD(묶음 6·5-1·5-2·5-3절) · PWR·LITE(watch-card 전체).
- 절 해시 계산식(코어 로더가 같은 식을 써야 함): 파일을 UTF-8로 읽고 CRLF→LF, `split("\n")` 뒤 마지막 원소가 빈 문자열이면 버림(파일 끝 줄바꿈). `card_section`과 정확히 같은 줄부터, 그 뒤 처음 나오는 "같거나 높은 단계의 머리 줄"(`#`×k 뒤 공백, k ≤ 자기 단계) 직전 줄까지(없으면 파일 끝)를 `"\n".join(...)` 하여 sha256(UTF-8). 끝 줄바꿈은 붙이지 않는다. PWR·LITE는 1단계 `# ` 제목이라 13줄~파일 끝 전체(front matter 제외).
- 절 범위(줄): MVLL 72–107 · SOXL 108–140 · NBIS 141–175 · BE 186–233 · DELL 234–281 · AMD 282–329 · MU 345–393 · PWR 13–66 · LITE 13–67.
- 트리거 출처는 규칙 파일 `integrated-check-prompt-v3.12.2-2026-10-09.txt`의 정의 줄(121 MVLL · 124 SOXL · 125 NBIS · 126 MU · 127 BE · 128 DELL · 129 AMD · 130 W 공통 틀 PW·LT), C8 문턱은 112줄. 카드 표의 같은 정의 줄: MVLL V3 99 · SOXL S4 132·S5 133·S6 134·S8 136 · NBIS N1 162·N5 166·N6 167·N8 169·N9 170·N10 172 · MU U1 382·U4~U8 385~389 · BE BE1 221·BE4~BE9 224~229 · DELL DL1 269·DL4~DL8 272~276 · AMD AM1 317·AM4~AM9 320~325 · PWR PW1 50·PW4~PW8 53~57 · LITE LT1 50·LT4~LT8 53~57.

### 종목별 표

#### MVLL (holding) — docs/claude/integrated-stock-cards-v1-2026-10-02.md · `## 2. MVLL 카드 (갱신)` · sha256 0f662c09fbaa5669…
- 수락: 보유 3종목(MVLL·SOXL·NBIS) 현행 카드(2~4절, 2026-10-04 사용자 확정) (2026-10-04, docs/claude/integrated-stock-cards-v1-2026-10-02.md:10) · card_action HOLD · trigger_set V · sector None · RG2 SOXX · c8 null · domains graniteshares.com, marvell.com
- 정적 근거: 없음(보유 카드에 "매수 근거 후보 현황" 표 없음)

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| V3 | ema_below | - | {"ema": 10} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:121 |
- kill_refs: MVLL-KILL(integrated-stock-cards-v1-2026-10-02.md:85)
- known_events: 2026-10-15 TSMC Q3 콘퍼런스(15:00 KST), 2026-10-15 E2 기한(KST)

#### SOXL (holding) — docs/claude/integrated-stock-cards-v1-2026-10-02.md · `## 3. SOXL 카드 (10/1 수락본 유지 + 10/2 갱신)` · sha256 11a7c8519da4a135…
- 수락: 보유 3종목(MVLL·SOXL·NBIS) 현행 카드(2~4절, 2026-10-04 사용자 확정) (2026-10-04, docs/claude/integrated-stock-cards-v1-2026-10-02.md:10) · card_action HOLD · trigger_set S · sector None · RG2 SOXX · c8 {"one_day": 0.2, "five_day": 0.25} · domains direxion.com
- 정적 근거: 없음(보유 카드에 "매수 근거 후보 현황" 표 없음)

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| S4 | ema20_below_twice | - | {} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:124 |
| S5 | ema_below_unrecovered | - | {"ema": 50, "sessions": 2} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:124 |
| S6 | drop_alert | alert | {"one_day": 0.2, "five_day": 0.25} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:124 |
| S8 | close_at_or_below | alert | {"price": "98.66"} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:124 |
- kill_refs: S2(integrated-stock-cards-v1-2026-10-02.md:130), S3(integrated-stock-cards-v1-2026-10-02.md:131), S7(integrated-stock-cards-v1-2026-10-02.md:135), SOXL-KILL(integrated-stock-cards-v1-2026-10-02.md:121)
- known_events: 2026-10-13 SEMICON West(10/13–15), 2026-10-15 TSMC Q3 콘퍼런스(15:00 KST), 2026-10-20 NVIDIA GTC Berlin(10/20–22, 간접)

#### NBIS (holding) — docs/claude/integrated-stock-cards-v1-2026-10-02.md · `## 4. NBIS 카드 (10/1 수락본 유지 + 10/2 갱신)` · sha256 947747263ff88175…
- 수락: 보유 3종목(MVLL·SOXL·NBIS) 현행 카드(2~4절, 2026-10-04 사용자 확정) (2026-10-04, docs/claude/integrated-stock-cards-v1-2026-10-02.md:10) · card_action HOLD · trigger_set N · sector None · RG2 SOXX · c8 {"one_day": 0.15, "five_day": null} · domains nebius.com
- 정적 근거: 없음(보유 카드에 "매수 근거 후보 현황" 표 없음)

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| N1 | earnings_notice | info | {} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:125 |
| N5 | good_news_drop | - | {} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:125 |
| N6 | ema20_below_twice | - | {} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:125 |
| N8 | drop_alert | alert | {"one_day": 0.15, "five_day": null} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:125 |
| N9 | close_at_or_below | alert | {"price": "193.50"} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:125 |
| N10 | log_only | info | {} | held | integrated-check-prompt-v3.12.2-2026-10-09.txt:125 |
- kill_refs: N2(integrated-stock-cards-v1-2026-10-02.md:163), N3(integrated-stock-cards-v1-2026-10-02.md:164), N4(integrated-stock-cards-v1-2026-10-02.md:165), NBIS-KILL(integrated-stock-cards-v1-2026-10-02.md:154)
- known_events: 2026-10-15 TSMC(군집 참고), 2026-10-20 NVIDIA GTC Berlin(10/20–22, 간접)

#### MU (watch) — docs/claude/integrated-stock-cards-v1-2026-10-02.md · `## 6. MU 관심 카드 (신규, 미보유)` · sha256 2b45ee6adf410d41…
- 수락: cardStatus 수락(2026-10-02) (2026-10-02, docs/claude/watchlist-registry.json:52) · card_action WATCH · trigger_set U · sector B1 메모리 · RG2 SOXX · c8 {"one_day": 0.1, "five_day": null} · domains micron.com

| id | e1_kind | 강도 | 방향 | 출처 | 인용(160자 이내) |
|---|---|---|---|---|---|
| MU-SE1 | thesis | strong | + | integrated-stock-cards-v1-2026-10-02.md:353 | 공식 수치가 기대 상회: 매출 $54.23B, non-GAAP 총이익률 87.0%, EPS $33.42(컨센서스 $31.83, 제3자), FQ1 가이던스 매출 $61.5B±$1.5B(컨센서스 $56.8B), EPS $38.15±$1.00(컨센서스 $36.02) |
| MU-SE2 | valuation | neutral | + | integrated-stock-cards-v1-2026-10-02.md:354 | 불명확. 위스퍼링 EPS $34.14에 못 미쳤고(SAVE 이미지, 외부 가설) FQ1 총이익률 가이던스 약 86.25%가 기대 86.7%보다 낮음. 반면 10/1 정규장 반응은 호재를 흡수. 산술: 시총 $1.24T(키움 기본 주식수) |
| MU-SE3 | event_reaction | weak | + | integrated-stock-cards-v1-2026-10-02.md:355 | 10/1: 시가 -1.0%, 최저 -4.0%, 종가 +3.03%(잠정), 거래량 3,403만 주(직전 20세션 평균 약 2,500만 주의 1.36배). "호재 뒤 하락" 아님 |

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| U1 | earnings_notice | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:126 |
| U4 | good_news_drop | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:126 |
| U5 | new_high_hold | + | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:126 |
| U6 | pullback_rebound | + | {"band": 0.015} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:126 |
| U7 | ema20_below_twice | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:126 |
| U8 | drop_alert | alert | {"one_day": 0.1, "five_day": null} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:126 |
- kill_refs: U3(integrated-stock-cards-v1-2026-10-02.md:384), MU-KILL(integrated-stock-cards-v1-2026-10-02.md:370)
- known_events: 2026-10-13 SEMICON West(10/13–15), 2026-10-15 TSMC Q3 콘퍼런스(15:00 KST), 2026-10-20 NVIDIA GTC Berlin(10/20–22, 간접), 2026-12-09 Micron 자사주 매입 시작(회사 언급)

#### BE (watch) — docs/claude/integrated-stock-cards-v1-2026-10-02.md · `### 5-1. BE (Bloom Energy, NYSE) 관심 카드` · sha256 b795024b7d1fceff…
- 수락: cardStatus 수락(2026-10-02) (2026-10-02, docs/claude/watchlist-registry.json:103) · card_action WATCH · trigger_set BE · sector A1 전력(온사이트) · RG2 GRID · c8 {"one_day": 0.1, "five_day": null} · domains bloomenergy.com

| id | e1_kind | 강도 | 방향 | 출처 | 인용(160자 이내) |
|---|---|---|---|---|---|
| BE-SE1 | thesis | strong | + | integrated-stock-cards-v1-2026-10-02.md:192 | 공식(Bloom 7/28 보도자료): 2분기 매출 $1,065.4M(+165.5% YoY, 1분기 $751.1M 대비 +41.8%), non-GAAP 총이익률 34.3%, non-GAAP EPS $0.78. FY26 가이던스 상향: 매출 $3.9~4.2B |
| BE-SE2 | valuation | weak | - | integrated-stock-cards-v1-2026-10-02.md:193 | 가격 ÷ FY26 non-GAAP EPS 가이던스 = 97~109배(중간값 기준 약 103배, 산술). 시총(saveticker 외부 $81.6B, 키움 상장주식수 2.945억 주×종가와 일치 |
| BE-SE3 | event_reaction | neutral | + | integrated-stock-cards-v1-2026-10-02.md:194 | 7/28 실적(장 마감 후) 다음 세션 7/29 -1.85%, 다음 7/30 +26.5%(원인 확인 필요). 9/24~25 오라클 재확인 보도 뒤 9/25 +8.3% → 9/28 -8.95%(종가 $262.87 < 9/24 종가 $266.65). 후자는 공식 보도자료가 아니라 보도 |

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| BE1 | earnings_notice | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:127 |
| BE4 | good_news_drop | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:127 |
| BE5 | new_high_hold | + | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:127 |
| BE6 | pullback_rebound | + | {"band": 0.015} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:127 |
| BE7 | ema20_below_twice | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:127 |
| BE8 | drop_alert | alert | {"one_day": 0.1, "five_day": null} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:127 |
| BE9 | log_only | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:127 |
- kill_refs: BE2(integrated-stock-cards-v1-2026-10-02.md:222), BE-KILL(integrated-stock-cards-v1-2026-10-02.md:209)
- known_events: 2026-11-23 뉴멕시코 환경부 대기 허가 결정 기한(2차)

#### DELL (watch) — docs/claude/integrated-stock-cards-v1-2026-10-02.md · `### 5-2. DELL (Dell Technologies, NYSE) 관심 카드` · sha256 dd5d5e1d4de45902…
- 수락: cardStatus 수락(2026-10-02) (2026-10-02, docs/claude/watchlist-registry.json:154) · card_action WATCH · trigger_set DL · sector AI 서버 · RG2 SOXX · c8 {"one_day": 0.1, "five_day": null} · domains dell.com, delltechnologies.com

| id | e1_kind | 강도 | 방향 | 출처 | 인용(160자 이내) |
|---|---|---|---|---|---|
| DELL-SE1 | thesis | strong | + | integrated-stock-cards-v1-2026-10-02.md:240 | 공식(Dell 9/1 보도자료): 2분기 매출 $47.0B(+58%), AI 최적화 서버 매출 $16.4B(+100%), AI 서버 수주 $60.9B(분기 기록), AI 백로그 $95B(분기 말 기록), non-GAAP 영업이익률 12.6%(전년 7.7%) |
| DELL-SE2 | valuation | neutral | + | integrated-stock-cards-v1-2026-10-02.md:241 | 가격 ÷ FY27 non-GAAP EPS 가이던스 = 21.2배(산술, FY27은 2027-01 종료). 공식 희석주식수 6.52억 주 × 종가 = 시총 약 $353B(산술, saveticker 외부 $342B). 백로그 $95B ÷ FY27 AI 서버 매출 가이던스 $74B = |
| DELL-SE3 | event_reaction | weak | + | integrated-stock-cards-v1-2026-10-02.md:242 | 9/1 실적(장 마감 후) 다음 세션 9/2 +15.8%(종가 $425.00 → $492.20), 9/3 +4.9%, 9/4 +1.5%. 발표 전일 종가 아래로 복귀 없음. 이후 9/17 종가 고점 $588.40 → 10/1 $541.50(-8.0%)로 눌림 |

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| DL1 | earnings_notice | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:128 |
| DL4 | good_news_drop | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:128 |
| DL5 | new_high_hold | + | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:128 |
| DL6 | pullback_rebound | + | {"band": 0.015} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:128 |
| DL7 | ema20_below_twice | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:128 |
| DL8 | drop_alert | alert | {"one_day": 0.1, "five_day": null} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:128 |
- kill_refs: DL3(integrated-stock-cards-v1-2026-10-02.md:271), DL9(integrated-stock-cards-v1-2026-10-02.md:277), DELL-KILL(integrated-stock-cards-v1-2026-10-02.md:257)
- known_events: 2026-10-30 분기 배당 $0.63 지급(공식)

#### AMD (watch) — docs/claude/integrated-stock-cards-v1-2026-10-02.md · `### 5-3. AMD (Advanced Micro Devices, NASDAQ) 관심 카드` · sha256 5400f3de18f5f449…
- 수락: 수락(v2, 2-2, 10/2): BE·DELL·AMD 관심 카드(WATCH 3종, 확신도 낮음) (2026-10-02, docs/claude/integrated-stock-cards-v1-2026-10-02.md:461) · card_action WATCH · trigger_set AM · sector None · RG2 SOXX · c8 {"one_day": 0.1, "five_day": null} · domains amd.com

| id | e1_kind | 강도 | 방향 | 출처 | 인용(160자 이내) |
|---|---|---|---|---|---|
| AMD-SE1 | thesis | strong | + | integrated-stock-cards-v1-2026-10-02.md:288 | 공식(AMD 8/4 보도자료): 2분기 매출 $11.536B(데이터센터 $6.718B, 클라이언트 $3.062B, 게이밍 $779M, 임베디드 $977M), non-GAAP 총이익률 56%, non-GAAP 영업이익 $3.094B(산술 영업이익률 26.8%) |
| AMD-SE2 | valuation | weak | - | integrated-stock-cards-v1-2026-10-02.md:289 | 시총 약 $1.0T(saveticker 외부 $999B, 키움 상장주식수 16.32억 주×종가와 일치). 외부 2026 컨센서스 EPS $7.58(ts2.tech 9/21) 기준 약 81배(산술). 애널리스트 36명(매수 30·보유 6·매도 0) 평균 목표가 $648.07(현재가 대비 |
| AMD-SE3 | event_reaction | neutral | + | integrated-stock-cards-v1-2026-10-02.md:290 | 8/4 실적(장 마감 후) 다음 세션 8/5 -7.0%(종가 $518.58 → $482.05)로 "호재 뒤 하락" 선례. 이후 9/21 +10.0%(공식 호재 발표 없음, 외부 기사는 위험 선호 장세로 서술), 9/25 종가 고점 $630.63 |

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| AM1 | earnings_notice | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:129 |
| AM4 | good_news_drop | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:129 |
| AM5 | new_high_hold | + | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:129 |
| AM6 | pullback_rebound | + | {"band": 0.015} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:129 |
| AM7 | ema20_below_twice | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:129 |
| AM8 | drop_alert | alert | {"one_day": 0.1, "five_day": null} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:129 |
| AM9 | display_only | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:129 |
- kill_refs: AM3(integrated-stock-cards-v1-2026-10-02.md:319), AMD-KILL(integrated-stock-cards-v1-2026-10-02.md:305)
- known_events: 2026-10-13 SEMICON West(10/13–15), 2026-10-15 TSMC Q3 콘퍼런스(간접), 2026-10-20 NVIDIA GTC Berlin(10/20–22, 간접), 2026-11-03 Q3 실적 발표 외부 추정(확정 아님)

#### PWR (watch) — docs/claude/watch-card-PWR-2026-10-03.md · `# PWR (Quanta Services, NYSE) 관심 카드 v1 (2026-10-03, 신규, 미보유)` · sha256 a8852743d6ca11ed…
- 수락: cardStatus 수락(2026-10-03) (2026-10-03, docs/claude/watchlist-registry.json:182) · card_action WATCH · trigger_set PW · sector A1 전력(그리드 시공) · RG2 GRID · c8 {"one_day": 0.1, "five_day": null} · domains quantaservices.com

| id | e1_kind | 강도 | 방향 | 출처 | 인용(160자 이내) |
|---|---|---|---|---|---|
| PWR-SE1 | thesis | strong | + | watch-card-PWR-2026-10-03.md:23 | 공식(Quanta 2분기 보도자료): 매출 $9.56B(+41.1%), 순이익 $451.4M, 희석 EPS $2.96·조정 $4.24, 영업현금흐름 $1.1B·FCF $0.9B, **총 백로그 $53.4B(전년 $35.8B, +49%)**, 12개월 백로그 $32.3B |
| PWR-SE2 | valuation | neutral | + | watch-card-PWR-2026-10-03.md:24 | 종가 ÷ FY26 조정 EPS 가이던스 중간값 $16.70 = 40.5배(산술). 외부 예상 PER 36.7. 시총 $101.7B(키움 시가총액 필드와 일치). 연초 대비 +60.3%(SOXX +95.9%보다 덜 오름) |
| PWR-SE3 | event_reaction | weak | + | watch-card-PWR-2026-10-03.md:25 | 2분기 실적 발표 세션(7/30) 종가 $657.98, 전일 $561.14 대비 +17.3%. 이후 발표 전일 종가 아래 복귀 없음(최저 8/28 $602.70) |

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| PW1 | earnings_notice | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| PW4 | good_news_drop | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| PW5 | new_high_hold | + | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| PW6 | pullback_rebound | + | {"band": 0.015} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| PW7 | ema20_below_twice | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| PW8 | drop_alert | alert | {"one_day": 0.1, "five_day": null} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
- kill_refs: PW3(watch-card-PWR-2026-10-03.md:52), PWR-KILL(watch-card-PWR-2026-10-03.md:40)
- known_events: 2026-10-29 3분기 실적 외부 추정(확인 필요), 2026-12-24 EO 14420 시행규칙(서명 후 120일 ≈ 12/24)

#### LITE (watch) — docs/claude/watch-card-LITE-2026-10-03.md · `# LITE (Lumentum Holdings, NASDAQ) 관심 카드 v1 (2026-10-03, 신규, 미보유)` · sha256 1d31e432d849981e…
- 수락: cardStatus 수락(2026-10-03) (2026-10-03, docs/claude/watchlist-registry.json:275) · card_action WATCH · trigger_set LT · sector A3 광부품 · RG2 SOXX · c8 {"one_day": 0.1, "five_day": null} · domains lumentum.com

| id | e1_kind | 강도 | 방향 | 출처 | 인용(160자 이내) |
|---|---|---|---|---|---|
| LITE-SE1 | thesis | strong | + | watch-card-LITE-2026-10-03.md:23 | 공식(Lumentum FQ4 FY26 보도자료, 8/11): 매출 $1,006.3M(+109.3%), non-GAAP 총마진 50.4%(+1,260bp), non-GAAP 영업이익률 36.6%(+2,160bp) |
| LITE-SE2 | valuation | neutral | + | watch-card-LITE-2026-10-03.md:24 | 외부 예상 PER 49.8. FQ1 non-GAAP EPS 가이던스 중간값 $4.20 × 4 = $16.80 기준 64.6배(산술, 단순 연환산). 시총 약 $97B(외부). 연초 대비 +194%(SOXX +96%의 2배) |
| LITE-SE3 | event_reaction | weak | + | watch-card-LITE-2026-10-03.md:25 | 8/11 실적(장 마감 후) 다음 세션 8/12 종가 $932.47(+13.6%, 발표 전 $820.59). 8/13 $880.41로 밀렸으나 발표 전 가격 위 유지, 10세션 뒤(8/26) $939.03(+14.4%) |

| 트리거 | kind | side | params | active_when | 출처 |
|---|---|---|---|---|---|
| LT1 | earnings_notice | info | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| LT4 | good_news_drop | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| LT5 | new_high_hold | + | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| LT6 | pullback_rebound | + | {"band": 0.015} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| LT7 | ema20_below_twice | - | {} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
| LT8 | drop_alert | alert | {"one_day": 0.1, "five_day": null} | held_or_member | integrated-check-prompt-v3.12.2-2026-10-09.txt:130 |
- kill_refs: LT3(watch-card-LITE-2026-10-03.md:52), LITE-KILL(watch-card-LITE-2026-10-03.md:40)
- known_events: 2026-11-03 FQ1 FY27 실적 외부 추정(확인 필요), 2026-11-05 실적 11/5(외부 재게시, 금지 구간 11/3~11/6)

### 카드 A행(매수 판정 요건 ③)과의 대조 — 어긋난 곳

| 종목 | 카드 A행의 ③ 산정 | 등록부 정적 근거 | 차이와 이유 |
|---|---|---|---|
| BE | A4: 카드 표 강 1(테제) · 약화 약 1(밸류에이션 −) | 강 1(+, 테제) · 약 1(−, 밸류에이션) · 이벤트 반응 혼합 → neutral | 일치 |
| DELL | A5: 강 1(테제)·약 1(이벤트 반응) | 강 1(테제) · 약 1(이벤트 반응) · 밸류에이션 중립 → neutral | 일치 |
| MU | A3: 숫자 산정 없음(판단 칸: 테제 근거 1개 충족 후보) | 강 1(테제) · 약 1(이벤트 반응 "약(긍정)") · 밸류에이션 중립 → neutral | A3·판단 칸은 이벤트 반응 약 1을 세지 않았다(표 비고 "종가 확정 전이라 보류"). 표의 강도를 그대로 옮겨 weak로 둠 — Judge 확인 요청 |
| AMD | A6: 강 1(테제)·약 1(추세) | 강 1(테제) · 약 1(−, 밸류에이션 약화) · 이벤트 반응 혼합 → neutral | A6의 "약 1(추세)"는 기술 신호 행이라 정적 근거에서 뺐다(매일 다시 계산 — 지시 F2). A6는 밸류에이션 약화(−)를 세지 않았으나 표에 "약화"로 적혀 있어 weak(−)로 옮김 |
| PWR | A행: 강 1(테제)·약 2(이벤트 반응·PW5) | 강 1(테제) · 약 1(이벤트 반응) · 밸류에이션 중립(부담) → neutral | PW5(기술 신호)는 정적 근거가 아님(코어가 매일 PW5를 다시 판정) → 정적 약은 1 |
| LITE | A행: 강 1(테제)·약 2(실적 반응·LT5) | 강 1(테제) · 약 1(이벤트 반응) · 밸류에이션 "부담" → neutral | LT5(기술 신호) 제외 → 정적 약은 1 |

### 등록부 옮겨 적기에서 고른 곳 (Judge 확인 요청)

1. 강도 판독: BE 테제 "강(수치) · 이벤트 불확실" → strong(A4가 "강 1"로 셈). PWR 밸류에이션 "중립(부담)"·LITE 밸류에이션 "부담" → neutral(강·약 표기가 아님). "혼합"(BE·AMD 이벤트 반응) → neutral. neutral은 세지 않는다.
2. 방향: 표가 "약화"로 적은 행만 "−"(BE·AMD 밸류에이션). "부담"·"중립"은 약화 표기가 아니라 "+"로 두었다(neutral이라 계산 영향 없음).
3. 기술 신호 행과 "상대 비교 — 미작성(-)" 행은 넣지 않았다.
4. 인용(quote)은 그 행 "현재 상태" 칸의 앞부분 그대로(160자 이내, 쉼표·공백에서 자름). 출처 줄은 worktree 사본 기준.
5. official_domains(카드에 없는 값): 발행사 자체 도메인만 — MVLL graniteshares.com·marvell.com(기초자산 공식 사실용), SOXL direxion.com, NBIS nebius.com, MU micron.com, BE bloomenergy.com, DELL dell.com·delltechnologies.com, AMD amd.com, PWR quantaservices.com, LITE lumentum.com. sec.gov는 코어가 공통 허용. 보도자료 배포처(businesswire 등)는 넣지 않았다(필요하면 Cowork가 추가).
6. accepted: 보유 3종목은 묶음 10줄 "2026-10-04 사용자 확정"(날짜 2026-10-04). 관심 members는 watchlist-registry.json cardStatus 줄(MU 52·BE 103·DELL 154·PWR 182·LITE 275). AMD는 members가 아니라 묶음 461줄의 v2 수락 문구로 적었다 — 관심 종목 수락은 members cardStatus로만 유효하므로 AMD는 members에 들어오기 전까지 주문표 자격이 없다.
7. sector: members 값 그대로, 보유 3종목·AMD(members 아님)는 null → RG2 기준 SOXX. BE·PWR는 "A1 전력…" → GRID.
8. U6·BE6·AM6("EMA20 부근")은 수치 정의가 없어 규칙 파일 A-3의 C6+ 별칭 규칙대로 band 0.015(DL6·X6와 같은 값)로 적었다.
9. c8: SOXL 20%·5세션 25%, NBIS 15%, 관심 카드 10%(규칙 파일 112줄). MVLL은 카드 값이 없어 null(코어가 2배 → 15% 적용). 5세션 문턱은 SOXL만.
10. known_events: 카드에 날짜가 적힌 것 중 2026-10-10 이후만(지난 일정 10/2 고용·10/6 Marvell 행사 등은 뺌). 범위 일정은 시작일(SEMICON West 10/13, GTC Berlin 10/20). 외부 추정·2차 날짜는 라벨에 표시(표시 전용). BE "2027-02 가스관"·"2028 완공"은 일(日)이 없어 뺐다.
11. kill_refs: 음(−) 공식 강 후보 ID(S2·S3·S7·N2·N3·N4·U3·BE2·DL3·DL9·AM3·PW3·LT3)는 카드 표 줄, 각 카드 kill 칸은 `<SYM>-KILL`로 그 줄(MVLL은 kill 칸만).
12. card_action: 보유 3종목 HOLD(각 카드 판단 칸), 관심 6종목 WATCH. trim_target_weight 모두 null(TRIM 목표가 카드에 없음 → TRIM 주문표 없음).

## 5. Builder 판단 (지시문이 정하지 않아 고른 것 — Judge 확인 요청)

1. **후회 시나리오 창** = 최근 60개의 5세션 수익률(종가 65개). 실자료 검증: MVLL 10/5에 10분위 −26.11%·최악 1일 −20.77%로 설계 5절(−26.1%·−20.8%)과 일치, 90분위 28.2%는 설계 29.6%와 다름(σ60도 10.02% 대 9.94% — 설계 계산 당시 이력 사본이 달랐던 것으로 보임). 분위수는 numpy 'linear'.
2. **LOC 배수** mult를 가격과 같은 방향으로 4자리 반올림(매수 내림·매도 올림)하고 가격 = 기준가 × mult(센트 내림/올림). 대시보드 환산(키움 기준종가 × mult)이 기준가에서 같은 가격을 낸다.
3. **ATR 사슬**: 미완성 세션이 끼면 그 뒤 참범위 14개가 새로 모일 때까지 unk(값을 만들지 않음).
4. **부동소수 표현 허용 1e-9**: 100 × 1.015 같은 선이 이진 소수로 정확히 표현되지 않아 경계 같음을 같음으로 본다(≥·≤는 포함, >·<는 제외). 문턱이 아님.
5. **C3 상태형**: 아래(위) 연속 2회 이상 + 그 연속 직전 종가가 반대쪽(엄격) — 연속이 이어지는 동안 유지. 카드 별칭(S4 등)은 직전 조건 없이 연속 2회.
6. **S5**: EMA50 아래 마감 뒤 2세션 미회복 = 아래 연속 3회 이상에서 hit, 1~2회는 pending.
7. **C6**: "EMA20 아래(위)에 있던" = 2세션 전 종가가 그쪽. 반등·눌림 자체의 가격 방향 조건은 더하지 않음. U6·BE6·AM6("부근")은 C6+ 정의(1.5%)로 판정.
8. **C7 기준가** = 발표 시각 직전 정규장 종가(마지막 마감이 발표 전인 세션), 반응 = 그 뒤 2세션. 연구 기록이 없으면 unk, 있으면 그 안의 사실로 판정(사실 없음 = none). 최근 10개 기록일의 사실을 함께 본다.
   - 정정(r2): "최근 10개 기록일"은 C7만이 아니라 RG1·EV3ⓑ의 뿌리 테제 훼손 사실에도 쓰이고 있었다(Judge 5절 3, F-4). R-REC1 창(60세션)보다 짧아 오래된 훼손 사실이 잊혔다. r2 R2-4부터 훼손 사실은 창 전체의 유효 연구 기록에서 모으고, C7은 10기록일 그대로다.
9. **C8+** 는 C8−와 같은 문턱을 위로(SOXL 5세션 25% 포함).
10. **R-REC1**: σ60은 그 세션 수익률 포함. EV4의 지난 세션은 직전 decide 기록의 ev4_open으로 이어 받음. EV5 이벤트의 C0·L0도 벤치마크 값.
   - 정정(r2): 지난 기록만 이어받아 **그 세션 자신의 EV4가 R-REC1에 들어가지 않았다**(Judge 5절 2, F-3, 탐침 P2: 직전 기록 없음·총자산 1차 선 아래인데 MU 매수 발행). r2 R2-3부터 R-REC1 계산 전에 그 세션 EV4(`auto_core_rules.ev4_open`, 리플레이도 같은 함수)를 넣는다.
11. **매도 간격 출처가 둘 이상**(S7 줄이기와 카드 TRIM/EXIT)이면 목표 비중이 가장 낮은 쪽(간격이 큰 쪽), 출처를 gap.source에 기록.
12. **매도 후회**는 "현금" 경로와 "최선 후보" 경로의 최대 후회 중 큰 값으로 고른다. 후보 = 등록부 자격 + ③ 충족 + M6 ④ + 시나리오 있음, 강 근거 수 → 약 종류 수 → 코드 순.
13. **W\* 격자 범위**: 0.001부터 종목 상한(0.4 ÷ 배수), 상한 면제 ETF는 1.55 ÷ 배수까지(그 위는 명목 N만으로 이미 실패) — 결과를 바꾸지 않고 제안 수만 줄인다. 제안은 회로가 열릴 수 있는 종목(새 근거 기준 충족, 또는 S7 보충 종목 SOXL이 ③ 충족)만.
14. **공식 사실**은 새로울 때만 센다(지시문 F3) — 평가 세션 사실, 또는 직전 세션 사실 중 직전 decide 기록(facts_seen)에 없던 것.
15. **Q2 연결**: 미입력 뒤 같은 결정의 재발행은 설정 키 `reissue_buy_cap_not_above_first`가 **있을 때만**(true = a, false = b). 키가 없으면(Q2 c·무응답) 그 결정은 다시 나오지 않고 소멸(새 결정 키는 새로 셈). 7절 "답이 없으면 그 부분 주문표를 만들지 않는 쪽"과 맞추고 새 키를 만들지 않으려고 고른 방식 — P-1 설명에 적음.
16. **결과 분류가 T1 체결 기록(I2)과 다르면** 그 결과는 일지에 쓰지 않고 푸시하며, 그날 새 주문표도 막는다(G0 실패로 취급, fail-closed).
17. **비교 모드 주문표**도 다음 날 읽기 조회로 분류해 기록하지만 재발행 원장(keys)은 기록 모드 결과로만 갱신한다.
   - 정정(r2): 보고에 없던 사실 — **이른 HOLD/FAIL 날(kill·T1 없음/FAIL·설정·프로필·달력 실패·예외)의 기록은 원장(keys)과 미분류 주문표를 넘기지 않아 다음 날 끊겼다**(Judge 5절 6, J10, 탐침 P1). 닫힌 키가 다시 열리고, 그 주문표는 분류·일지 기록되지 않았으며, G0는 빈 목록이라 통과했다. r2 R2-2에서 고쳤다(f6_ran·carried_from).
18. **정책 값 교차 검사**: alert_policy의 1.55·1.85·1.9·0.4가 코드가 기대한 값과 다르면 G1 `POLICY_THRESHOLD_CHANGED`(그날 주문표 0). 값이 바뀌면 코드·Judge를 함께 거치게 하려는 fail-closed.
19. **연구 기록 URL**: https·도메인 검사는 항목 단위(버림). 스키마는 문자열만 요구 — 스키마에 https를 걸면 한 항목 때문에 파일 전체가 "없음"이 되기 때문.
20. **official_domains**: 발행사 자체 도메인만(보도자료 배포처 businesswire 등 제외). MVLL은 graniteshares.com·marvell.com. Cowork가 필요하면 추가.
21. **화면용 거리**는 margins(조건선까지의 절대 상대 거리, 부호 없음)로 낸다 — 대조 B2 판정과 같은 값.
22. **설정 파일이 없거나 틀리면 decide FAIL**(정지 스위치를 확인할 수 없으므로 HOLD가 아님).
   - 정정(r2): 이 목록에 빠진 사실 — 1차 코드는 **기록 모드에서 같은 날 두 번째 실행을 FAIL(CORE_DECISION_ALREADY_RECORDED)로 끝내고**, DECIDE_FAIL을 푸시하고, 그날 decision.json을 FAIL 기록으로 덮었으며, 이 동작이 테스트(`test_auto_core_decide.py` JournalEntryTests)로 고정돼 있었다(Judge 5절 4). 지시 F8 "같은 날 두 번 = 같은 결과"와 다르다. r2 R2-5에서 바꿨다.
23. **G-3 차이**(3절): S7 계획 기준 20주로 고정. OI의 22주(SOXL만) 재현 값도 고정.
24. **리플레이 가정**: S7 활성화를 첫 리플레이 세션(그날 자산 = HWM)으로 둠, 세션마다 독립(G0 통과·재발행 원장 없음), 등록부 커밋 검사 미적용(과거 재현이라), P-R2 현금 = 기간 끝 세션의 P-R1 자산 − NBIS 13주 가치, 거래소는 이력 파일의 거래소(없으면 NASDAQ → 자료 없음).
25. **일봉 페이지 충돌**: 같은 봉의 종가가 다르면 오류(종가 이력과 같은 규칙), 시가·고가·저가·거래량만 다르면 그 세션 INCOMPLETE.
26. 등록부 옮겨 적기에서 고른 곳 12건은 4절 끝 표(포크 작업 보고 그대로).
27. **스크립트는 ASCII만**(저장소 언어 계약 test_language_contract·test_v2_5_beginner_renderer): 한국어 문구는 `\uXXXX` 이스케이프로 둔다(T1과 같은 방식). 첫 전체 실행에서 이 두 검사가 새로 실패해(편집 도구가 이스케이프를 한글로 저장) 이스케이프로 되돌리고 다시 통과시켰다. f-string 식 안에는 백슬래시를 두지 않았다(파이썬 3.12 미만 호환).

## 6. 사람이 할 일 · 남는 위험

- **병합**: 이 worktree(worktree-t2-core) 병합 — 7절 Q1~Q4 답과 함께(`T2 병합: Q1 a, Q2 a, Q3 a, Q4 a` 형식). Judge(6절) 뒤.
- **작업 등록**: `.\manage-us-stock-strategy\scripts\register_auto_core_task.ps1 -PlanOnly`로 두 작업 확인 → `register_auto_core_task.ps1` 1회(KST 시간대에서만 등록, 실행은 하지 않음).
- **정책 제안**: docs/claude/redesign-t2-policy-proposals.json — P-1(auto_core.json: decide 키 3개·GRID, Q2~Q4 답으로 선택 키) · P-2(alert_policy PWR·LITE 배수·card_stock_core, 권한·한도) 각각 사용자 "적용" 뒤 Cowork.
- **Cowork 배포(지시문 8절)**: 06:40 점검 로더에 연구 기록 쓰기 단계(그 전까지 decide는 연구 기록 없이 돌아 매수 막힘·C7 unk·대조 B4가 정상), 결과 알림 08:50 이동과 runCore·orders 옮기기, 대시보드 core·source·"옵션 생략" 표시, 카드 수락 절차에 "같은 세션 등록부 갱신".
  - 정정(r2): "연구 기록 없이 돌아 매수 막힘"은 1차에서는 개별 주식만 맞았다. **지수 ETF(SOXL·TQQQ) 매수는 막히지 않았다**(Judge 5절 1, J6, 탐침 P3: SOXL 47주 발행). r2 R2-1부터 그날 연구 기록이 OK가 아니면 모든 매수 후보에 `RESEARCH_RECORD_NOT_OK:<이유>`가 붙고 지수 ETF의 요건 ① 칸도 no다.
- **남는 위험·확인 필요**
  1. 관심 종목(MU·BE·DELL·PWR·LITE) 30분봉은 10/13 06:15 T1 첫 수집 뒤 생긴다. 그 전 decide와 Builder 리플레이는 "자료 없음"(R-C 미달은 예상된 결과).
  2. GRID는 P-1 적용 전까지 수집되지 않음 → BE·PWR의 RG2 unk → 열린 R-REC1 이벤트 중 그 종목 매수 막힘(fail-closed).
  3. 실제 키움 응답으로는 실행하지 않았다(가짜 브리지). 첫 실행은 비교 모드라 주문표가 입력 대상이 아니다. ust21150 행의 `frgn_trde_tp` 값 "Limit On Close"(실측 1건)와 다른 표기가 오면 그 결과는 `changed`로 분류된다(보수적).
  4. 정책 값 교차 검사(5절 18번) 때문에 예산·상한 값을 바꾸는 정책 변경은 코드 상수와 함께 바꿔야 주문표가 나온다.
  5. 등록부는 병합(커밋) 전까지 REGISTRY_UNCOMMITTED → 주문표 0(의도된 fail-closed). 카드 파일을 고치면 같은 세션에서 등록부 해시를 갱신해야 한다(CARD_SECTION_CHANGED 1회 푸시).
  6. 지시문 1절의 시작 시각보다 먼저 시작해 지시문·실측 파일을 main 사본에서 읽었다(내용 sha256은 Judge가 커밋본과 대조 권장).

# r2

> 지시: docs/claude/redesign-t2-builder-r2-2026-10-10.md 1~3절(Judge FAIL 최소 수정 F-1~F-4 + "켜" 전 조건 1~5 + 비교 모드 조건 1·3). 같은 worktree, 같은 허용 경로. 정책·상태·일지·.claude·CLAUDE.md·tools 수정 0, 키움 실제 호출 0.

## r2-0 요약

- **BLOCKED: 없음.**
- **바뀐 파일(모두 1차 허용 경로 안):**
  - scripts: auto_core_decide.py · auto_core_tickets.py · auto_core_rules.py · auto_core_inputs.py · auto_core_compare.py · auto_core_replay.py
  - schemas: auto-core-decision(f6_ran·carried_from) · auto-core-compare(b2_wide·b2_wide_count) · auto-core-card-registry(kind·side 규칙 설명)
  - tests: test_auto_core_decide.py · test_auto_core_tickets.py · test_auto_core_rules.py · test_auto_core_compare.py
  - 문서: references/auto-core-decision.md · 이 보고(정정(r2) 6줄 + 이 절)
  - 1차에서 바꾼 auto_core.py·portfolio_review_journal.py·ps1·journal 스키마·등록부·정책 제안 파일은 이번에 손대지 않았다.
- **줄바꿈·ASCII:** 바뀐 파일 모두 CRLF 그대로(줄 수 = CR 줄 수). 스크립트 비ASCII 0줄 — 편집 도구가 `\uXXXX`를 한글로 저장한 두 파일(decide·tickets, 문자열 안 106자)은 바이트 단위로 다시 이스케이프했다.
- **테스트 수:** 대상 `-p "test_auto_core*"` Ran 223 → 253 (+30) (OK, skipped 1 = 실자료 스모크). `def test_` 2805 → 2835 (+30). 감소 0.
- **전체 스위트(변경 뒤):** 직접 셈(원본 로그): **Ran 2874 · FAILED (failures=19, errors=9, skipped=3) · FAIL/ERROR 줄 28개**. 기준선(이 세션에서 r2 수정 전에 같은 명령으로 잰 Ran 2844·28줄 — 1차 보고·Judge 수치와 같음)과 **실패 id 28개가 정렬 diff로 완전히 같다 → 새 실패 0, 고쳐진 것 0**. Ran +30 = 새 테스트 30개.
- **스키마 감사:** `validate_schema_contracts.py` PASS, errors [].
- **실자료 리플레이 스모크(읽기 전용, main의 저장 30분봉, 2026-07-10~10-09, 출력은 세션 임시 폴더):** 종료 0, 예외 0, 스키마 오류 0, R-A PASS · R-B PASS · R-C NOT_MET(1차·Judge와 같음).
- **기존 테스트 변경:** 약화 0. 바꾼 것은 셋뿐이다.
  1. JournalEntryTests.test_apply_appends_a_hash_chained_core_decision_once — 같은 날 두 번째 실행의 기대값을 FAIL에서 "OK·일지 추가 0·그날 decision.json 바이트 그대로·rerun 파일 없음"으로 바꿨다. 약화가 아니라 지시 F8 "같은 날 두 번 = 같은 결과"에 맞춘 것이다(R2-5). 재실행 단언은 3개 → 7개로 늘었다.
  2. 픽스처 기본 현금: test_auto_core_tickets.Scenario 20000 → 30000, test_auto_core_decide.Env 5000 → 30000. R2-3으로 그 세션 EV4가 R-REC1에 들어가면서, 계좌 총자산이 V6 1차 선(25,626.55) 아래인 옛 기본 상태에서는 모든 매수가 막혀 매수 경로 테스트가 성립하지 않는다. 입력만 바꿨고 단언은 그대로다(현금 2만 기준 단언 `≤ 20000`도 그대로 통과).
  3. Scenario.run이 evaluate_session의 새 필수 입력 research를 넘긴다(기본: 오늘 기록 OK, 모든 세션 기록 있음, 훼손 사실 = facts 중 root_thesis_damage).

## r2-1 R2-1~12: 바꾼 곳 · 고정한 테스트

| # | 바꾼 곳(파일:함수) | 고정한 테스트 |
|---|---|---|
| R2-1 연구 기록 OK 아니면 매수 전부 차단 | auto_core_tickets.py:`buy_requirements`(지수 ETF ① 칸 = no `RESEARCH_RECORD_NOT_OK:<이유>`), `plan`(매수 후보마다 같은 사유, 매도 없음) · auto_core_decide.py:`_run`(research_block = 그날 기록 상태 사유 첫 줄), `evaluate_session`(research.block → 요건 행·plan) | test_auto_core_tickets.ResearchRecordGateTests.test_no_research_record_blocks_the_index_etf_buy(SOXL 새 + 가격 단서 2종 → 매수 0·사유·① no / 같은 날 기록 OK면 SOXL 매수 1건), .test_the_sell_circuit_is_the_same_without_a_research_record · test_auto_core_decide.ResearchRecordBuyGateTests.test_record_not_ok_blocks_the_index_etf_buy(없음·스키마 불통과·written_at 불통과 subTest), .test_one_dropped_item_keeps_the_record_ok |
| R2-2 원장·미분류 주문표 이어짐 | auto_core_decide.py:`ledger_carry`(새: f6_ran = true인 가장 최근 기록의 keys·open_tickets + 발행 tickets(issued_day), 그 뒤 읽을 수 없는 기록 표시), `decide`, `_run`(그 출처로 F6, keys 시작값, 읽을 수 없는 기록이 출처 뒤면 G0_PREVIOUS_DECISION_UNREADABLE, F6 뒤 f6_ran true), `_settle`(새), `_finish` · schema auto-core-decision(f6_ran, carried_from) · `read_outcomes`는 그대로(주문표마다 발행일·다음 날을 이미 조회 — 여러 실행일을 건넌 주문표도 각자 날짜) | test_auto_core_decide.LedgerCarryTests: test_t1_missing_hold_between, test_unexpected_exception_fail_between, test_failure_after_f6_commits_nothing, test_g0_does_not_pass_on_an_empty_list_in_between, test_unreadable_record_after_the_source_fails_g0 (D apply 주문표 1건·닫힌 키 → D+1 HOLD/FAIL은 carried_from=D로 그대로 옮겨 적음 → D+2에서 D 주문표 분류·ticket_outcome 일지·닫힌 키 유지·ord_dt D 조회) |
| R2-3 그 세션 EV4 | auto_core_rules.py:`ev4_open`(새, 한 곳) · auto_core_decide.py:`evaluate_session`(S7 → EV4 → R-REC1 순서, ev4_sessions + 그 세션) · 리플레이는 evaluate_session을 그대로 부름(복제 없음) | test_auto_core_tickets.SessionEv4Tests.test_no_previous_record_and_total_below_the_first_line_blocks_buys(직전 기록 없음·총자산 ≤ 1차 선 → shock open·EV4·⑤ ≠ ok·매수 0) · test_auto_core_rules.RecoveryCoverageTests.test_ev4_lines(경계 ±1센트, hwm × 0.9) |
| R2-4 훼손 사실 창·RG1 범위·EV3ⓑ 공백 | auto_core_inputs.py:`load_research`(window_start부터 유효 기록 전부의 훼손 사실·기록 세션, C7용 10기록일 그대로) · auto_core_rules.py:`rrec1`(research_sessions, RG1 = 이벤트 다음 세션~평가 세션 모두 기록 있어야 판정·rg1_coverage, ev3b_coverage_start, EV3B_RECORD_GAP → unk) · auto_core_decide.py:`_run`(창 = 평가 세션까지 60세션), `evaluate_session` · auto_core_replay.py:`run_replay`(모든 세션 기록 있음 가정, 가정 목록에 적음) | test_auto_core_rules.RecoveryCoverageTests: test_damage_fact_fifteen_sessions_back_keeps_rg1_no, test_one_unrecorded_session_after_the_event_makes_rg1_unknown, test_unrecorded_one_sigma_fall_after_the_first_record_is_unknown, test_unrecorded_milder_day_has_no_effect, test_before_the_first_record_only_ev3a_counts · test_auto_core_tickets.ResearchCoverageTests.test_unrecorded_session_after_the_event_blocks_the_buy(기록 다 있으면 이벤트 닫힘·MU 매수 1 / 이벤트 다음 날 기록 없음 → RG1 unk·⑤ unk·매수 0) · test_auto_core_decide.DamageWindowTests.test_old_damage_fact_keeps_rg1_no(15기록일 전 기록의 훼손 사실 → decide에서 RG1 no, 10일 facts에는 없음) |
| R2-5 같은 날 재실행 멱등 | auto_core_decide.py:`_run`(쓰기 전 결정 스키마 검사, 일지의 같은 평가 세션 core_decision 확인), `decision_identity_hash`(새), `_rerun`(새: HOLD·decision.rerun-<HHMMSS>.json만·push) · compare.json 쓰기를 `_finish`로 옮김(재실행이 그날 파일을 덮지 않게) | 바꾼 고정 테스트: JournalEntryTests.test_apply_appends_a_hash_chained_core_decision_once(위 r2-0) · 새: RerunAndScorerTests.test_a_different_rerun_is_kept_aside_as_hold |
| R2-6 매도 주문표 S7 계획 전제 | auto_core_tickets.py:`plan_premise`(새), `REDUCE_STEP_LABELS`, `plan`(일일 개수 상한 뒤 매도 주문표마다 gap·after_sale.plan_premise) · auto_core_decide.py:`_after_sale_line`(대시보드 한 줄 끝) · 수량 불변 | test_auto_core_tickets.PlanPremiseTests.test_earlier_step_without_a_ticket("앞 순서 MVLL 상한 초과분 — 오늘 주문표 없음(매도 근거 없음) · 이 주문표만 체결 시 예상 E 1.5495" 등), .test_sell_ticket_carries_the_line_in_gap_and_after_sale |
| R2-7 불일치 결과는 원장 갱신 안 함 | auto_core_decide.py:`_run`(update_keys에서 reconcile_mismatch 결과 제외) | RerunAndScorerTests.test_mismatched_outcome_leaves_its_key_as_it_was |
| R2-8 채점기 반환값 | auto_core_decide.py:`_score`(반환값 돌려줌), `_run`(0·None 아니면 score_warning "SCORER_EXIT:<값>") | RerunAndScorerTests.test_scorer_exit_code_is_a_warning |
| R2-9 kind·side 묶음 | auto_core_inputs.py:`KIND_SIDES`·`kind_side_mismatches`(새), `load_registry`(kind_side_invalid), `card_check`(REGISTRY_KIND_SIDE_INVALID → 그 종목 자격 없음) · schema auto-core-card-registry(card_triggers 설명) | test_auto_core_decide.RegistryTests.test_kind_and_side_go_together(실제 등록부 위반 0 / S8 side "-" 사본 → SOXL 자격 없음·NBIS는 그대로) |
| R2-10 대조 엄격화 | auto_core_compare.py:`B2_N_MARGIN`·`B2_R5_MARGIN`·`NOT_COMPARED`, `_category_for_trigger`(여유값 반환), `_r5_distance`(새), `compare`(N·R5 B7, b2_wide), `streak_block`(새), `streak` · auto_core_decide.py:`_empty_decision`(대조 기본 NOT_COMPARED), `_run`(연속 일수 이력) · schema auto-core-compare | test_auto_core_compare.StrictCategoryTests: test_n_difference_boundary(0.03 B2 / 0.0301 B7), test_r5_difference_boundary(1%p B2 / 1.01%p B7, 0.70·0.75 양쪽), test_wide_b2_items_are_listed(1.01% 목록 / 1% 아님), test_fail_or_early_end_resets_the_streak |
| R2-11 S7 출력 위치 | auto_core_decide.py:`run_s7`(--output-root <날짜>/s7, earnings·proposals 입력도 그 아래) | test_auto_core_decide.S7OutputTests.test_decide_writes_its_s7_review_under_the_day_folder(decide 한 번 뒤 exposure-review 파일 목록 불변, 검토 파일은 <날짜>/s7/<세션>/) |
| R2-12 LOT_ZERO | auto_core_tickets.py:`_buy_ticket`(단계 적용 직후 0주 = LOT_ZERO) | test_auto_core_tickets.LotZeroAfterStepTests.test_zero_shares_after_the_step_is_lot_zero(1차 코드는 CASH_ZERO) |

## r2-2 Judge 5절 "다른 사실" 1~6 정정 위치(원문 유지, "정정(r2):" 줄 추가)

1. 6절 "Cowork 배포" 줄 아래 — 지수 ETF 매수가 막히지 않았던 사실.
2. 5절 10번 아래 — 그 세션 EV4 누락.
3. 5절 8번 아래 — 10기록일 창이 RG1·EV3ⓑ에도 쓰였던 사실.
4. 5절 22번 아래 — 기록 모드 같은 날 재실행 = FAIL이 목록에 없었던 사실.
5. 3절 리플레이 스모크 줄 아래 — "매수 회로가 열리지 않음"이 틀렸던 사실.
6. 5절 17번 아래 — 이른 HOLD/FAIL 날 원장·미분류 주문표 끊김이 보고에 없었던 사실.

## r2-3 새로 고른 것(이 지시가 정하지 않은 것) — Judge 2차 확인 요청

1. **f6_ran의 뜻 = "F6가 돌았고 그 기록이 FAIL로 끝나지 않음".** F6 뒤에 실패한 기록(S7 예외·대조 스키마·결정 스키마·일지 쓰기 거부)도 F6 전 종료와 같이 "아무것도 확정하지 않음"으로 둔다: 출처의 keys·미분류 주문표를 옮겨 적고(carried_from) f6_ran false. 이유: 그날 분류한 결과가 일지에 들어가지 않은 채 원장만 바뀌어 다음 날부터 그 결과가 영영 일지에 안 남는 길을 막는다. 다음 실행이 같은 브로커 행(발행일·다음 날 ust21150)으로 다시 분류하고 그때 기록한다(테스트 test_failure_after_f6_commits_nothing).
2. **FAIL 기록은 주문표를 내놓지 않는다**(tickets·outcomes·dashboard.orders·runCore.tickets·TICKET 알림·next_action_for_user를 비우고 DECIDE_FAIL push). 1차 코드는 기록 모드에서 일지 쓰기 직전 재확인이 실패해(kill 켜짐·모드 바뀜·보호 파일 미커밋·일지 바뀜) FAIL이 된 날에도 주문표·TICKET push·"저녁 키움 입력"을 남겼다. 결정 스키마 설명("a HOLD or FAIL day has no ticket")과 다르고, 1번에 따라 FAIL 기록은 출처가 아니므로 그 주문표는 분류될 길도 없다. 1차 Judge 판정표에 없던 동작이라 확인 요청.
3. **결정 스키마 검사를 일지 쓰기 전으로 당겼다**(실패 = DECISION_SCHEMA_INVALID FAIL, 아무것도 쓰지 않음). 1차는 일지를 쓴 뒤 `_finish`에서 검사해, 일지에는 기록되고 결정은 FAIL인 상태가 가능했다. `_finish`의 검사는 마지막 방어로 남겼다.
4. **decision_sha256(일지 review_id)의 정의를 바꿨다**: 같은 입력의 재실행에서 달라지는 칸(generated_at·journal·dirty_paths·inputs.research_record.wait·inputs.s7_review·tickets[].issuedAt·tickets[].inputs.s7_review_id·dashboard.orders[].issuedAt)을 뺀 정준 해시. 1차 정의(journal·generated_at만 뺌)로는 S7 검토 파일 경로·id(매 실행 새 파일이고 일지 head도 읽음)와 연구 기록 대기 시각 때문에 운영에서 같은 날 재실행이 거의 늘 "다름"이 되어 R2-5가 무의미하다. dirty_paths를 뺀 것은 docs 편집만으로 "다름"이 되지 않게 하려는 것이다(코드 버전은 commit_sha로 남고, 보호 파일 미커밋은 apply에서 이미 FAIL).
5. **R2-5 "같은 해시 → status OK"**: OK로 덮어쓰지 않고 기록된 결정과 같은 status를 돌려준다(같은 해시면 status·reasons도 같으므로 정상 경우 OK). 기록된 결정이 G0/G1 HOLD였다면 HOLD로 돌려준다 — 그날 decision.json과 어긋나지 않게.
6. **R2-5 기준은 평가 세션**(지시 문장대로 일지의 같은 평가 세션 core_decision). 다른 실행일이 같은 평가 세션을 다시 보는 경우(아래 새 사실 A의 휴장 예)도 "다름 → HOLD, rerun 파일만"이 되어 그날 decision.json이 없다(다음 날 ⑪ "직전 실행 누락" 알림). fail-closed이지만 A와 함께 정하는 것이 좋다.
7. **rerun 파일 내용**: 비교를 위해 tickets는 남기되 dashboard.orders·TICKET 알림·next_action_for_user는 비우고 status HOLD, 알림 CORE_DECISION_ALREADY_RECORDED_DIFFERENT(push). LATEST_DECISION.json·그날 compare.json도 그대로 둔다. 이 push를 받으려면 배포 때 알림 작업이 `<날짜>/decision.rerun-*.json`도 읽어야 한다(Cowork 배포 항목 — 지금 알림 작업은 LATEST만 본다).
8. **R2-7**: 불일치 결과의 주문표는 다시 열지 않는다(open_tickets에 남기지 않음). 다음 날 T1 대조는 다른 세션의 체결이라 같은 불일치가 매일 반복되어 G0가 무기한 닫히기 때문이다. 그 키는 다음 정상 분류(같은 키로 다시 나간 주문표의 결과)까지 그대로이고, 그날 G0 실패·push·일지 제외는 1차 그대로다.
9. **R2-9**: 스키마 검증기(validation_common의 SUPPORTED_SCHEMA_KEYS, 허용 경로 밖)에 if/then·allOf가 없어, 스키마는 card_triggers description에 규칙을 적고 강제는 로더가 한다(`KIND_SIDES`). display_only(AM9)도 alert/info 묶음에 넣었다(근거가 아님). 지시대로 등록부 전체가 아니라 그 종목만 자격 없음이다(load_registry status OK + kind_side_invalid 목록).
10. **R2-4 세부**: (a) "기록 있는 세션" = 유효(스키마·written_at 통과) 연구 기록의 evaluation_session. 창 = 평가 세션까지 60 달력 세션, 기록 폴더 날짜 ≥ 창 첫 세션 날짜. (b) EV3ⓑ 공백: σ60이나 그날 수익률을 모르는 날의 기록 누락도 공백으로 본다(fail-closed). 공백이 있으면 status unk·open null(이벤트가 열렸는지 알 수 없음)·사유 EV3B_RECORD_GAP:<날짜들>. (c) 훼손 사실이 확인되면 기록 누락과 무관하게 RG1 no. (d) `rrec1(research_sessions=None)`은 "추적 안 함"(1차 동작)으로 남겨 기존 규칙 단위 테스트를 바꾸지 않았다. decide·리플레이·테스트 Scenario는 evaluate_session의 필수 입력 research로 항상 넘긴다(기본값 없음). (e) 리플레이 가정에 "모든 세션에 사실 없는 연구 기록이 있다"를 적었다(1차의 "공식 사실 없음"과 같은 뜻을 명시).
11. **R2-10 세부**: N 0.03·R5 1%p 비교에 표현 허용 1e-9(`rules.FLOAT_EQUAL`, 문턱 아님)를 더했다(1.33 − 1.30 = 0.0300000000000000266). 기존 B1 경계(|ΔN| ≤ 0.01)는 손대지 않았다. b2_wide = 가격 여유 1% 넘게 쓴 MARGIN 근거 B2 트리거 항목({item_key, margin, limit}); RSI·불완전 봉 B2는 여유값이 없어 넣지 않았다. 연속 일수: 읽을 수 없는 기록도 0. 대조 블록의 기본값을 NO_RECORD에서 NOT_COMPARED로 바꿔 F9 전에 끝난 날이 "건너뜀"이 아니라 0이 되게 했다(NO_RECORD는 "F9는 돌았고 통합 점검 기록 사본만 없음").
12. **R2-6 세부**: 카드 EXIT/TRIM 출처 주문표에도 한 줄을 붙인다("카드 목표(…) — S7 계획 순서 아님 · 이 주문표만 체결 시 예상 E …"). 계산은 일일 개수 상한(G2b) 뒤라, 상한으로 빠진 앞 순서 종목은 "오늘 주문표 없음(G2B_CAP)"으로 보인다. 대시보드 afterSale 한 줄 끝에도 붙였다.
13. **R2-1 세부**: `<이유>` = 그날 기록 검사 사유의 첫 줄(RESEARCH_RECORD_MISSING·RESEARCH_RECORD_SCHEMA_INVALID·RESEARCH_RECORD_WRITTEN_AT_OUT_OF_RANGE·RESEARCH_RECORD_NOT_JSON·…DAY_MISMATCH·…SESSION_NOT_IN_CALENDAR). 사유는 회로가 열린 매수 후보(blocked)에 붙는다. 개별 주식의 ① 칸은 1차대로 실적 금지 구간 코드(no)다.

### 새로 찾은 사실(이번에 고치지 않음 — Judge·Cowork 판단 필요, "켜" 전 후보)

A. **F6가 주문표 세션이 끝났는지 보지 않는다.** 미국 월요일 휴장 뒤 화요일 07:45 KST 실행은 토요일 실행과 같은 평가 세션(금요일)을 다시 보는데, 토요일 주문표(세션 = 화요일 미국)를 그 세션이 열리기도 전에 분류해 not_entered로 셀 수 있다. 또 주문일 조회 창(발행 KST 날짜·다음 날)은 토요일 발행 주문표를 월요일 KST에 입력하면 놓친다(not_entered 오분류). 기록 모드에서는 둘 다 R-NE1 미입력 집계(연속 2회 → 키 닫힘)에 영향을 준다. 제안(결정 필요): ① 주문표 세션 ≤ 평가 세션일 때만 분류하고 아니면 열린 채 두기(그날 G0), ② 주문일 창 = 발행일 ~ 주문표 세션 개장일(KST). 지시 F6의 "주문일 = 발행일과 다음 날"을 바꾸는 일이라 이번에는 손대지 않았다.
   - 해결(r3): R3-1·R3-2로 고쳤다 — 주문표 세션 ≤ 평가 세션일 때만 분류(아니면 열린 채·조회 없음·`G0_TICKET_SESSION_NOT_YET`), 주문일 창 = 발행 KST 날짜 ~ 그 세션 마감(운영 달력 core_close_at)의 KST 날짜(`auto_core_tickets.ticket_session_ended`·`order_days`, `auto_core_decide.read_outcomes`). 제안 ②의 "개장일"이 아니라 지시대로 "마감 KST 날짜"까지 본다. 아래 "# r3" 절.
B. 위 A의 같은 평가 세션 재평가는 R2-5 규칙으로 HOLD + rerun 파일이 된다(r2-3 6번).
   - 해결(r3): R3-3으로 고쳤다 — 출처(f6_ran true 최신 기록)와 같은 평가 세션이면 OK·`no_new_session`·주문표 0·일지 0·push 0·브로커 조회 0, 원장·미분류 주문표 이어받기(carried_from, f6_ran true)·대조 연속 일수 유지, 그날 decision.json 정상 기록(다음 날 ⑪ 없음). R2-5는 같은 run_day 재실행에만 적용(`auto_core_decide._no_new_session`, `_run`). r2-3 6번도 이것으로 풀린다.

# r3

> 지시: docs/claude/redesign-t2-builder-r3-2026-10-11.md 1~3절(r2 "새로 찾은 사실" A·B — 결과 분류의 날짜 창·휴장일). 같은 worktree, T2 지시문 4절의 허용 경로·금지 그대로. 정책·상태·일지·.claude·CLAUDE.md·tools 수정 0, 키움 실제 호출 0(테스트는 가짜 브리지).

## r3-0 요약

- **BLOCKED: 없음.**
- **바뀐 파일(모두 1차 허용 경로 안):**
  - scripts: auto_core_tickets.py(`ticket_session_ended`·`order_days` 새) · auto_core_decide.py(`read_outcomes`·`ledger_carry`·`_run`·`_no_new_session` 새·`_empty_decision`·모듈 설명) · auto_core_compare.py(`NO_NEW_SESSION`·`streak`)
  - schemas: auto-core-decision(`no_new_session` 필수 칸 추가, f6_ran·carried_from 설명 갱신)
  - tests: test_auto_core_decide.py · test_auto_core_tickets.py · test_auto_core_compare.py · test_auto_core_replay.py
  - 문서: references/auto-core-decision.md · 이 보고(r2 A·B 아래 "해결(r3):" 2줄 + 이 절)
  - auto_core_replay.py·auto_core_rules.py·auto_core_inputs.py·auto_core.py·portfolio_review_journal.py·ps1·다른 스키마·등록부·정책 제안 파일은 손대지 않았다.
- **줄바꿈·ASCII:** 바뀐 파일 모두 CRLF 그대로(LF 수 = CRLF 수, 단독 CR 0). 스크립트 비ASCII 0줄 — 편집 도구가 `\uXXXX`를 한글로 저장한 auto_core_decide.py 3줄(새 알림 문구·next_action 문구)은 바이트 단위로 다시 이스케이프했다.
- **테스트 수:** 대상 `-p "test_auto_core*"` Ran 253 → 268 (+15) (OK, skipped 1 = 실자료 스모크). `def test_` 2835 → 2850 (+15, r2와 같은 셈법 `grep -r "def test_" | wc -l`). 감소 0.
- **전체 스위트:** 이 세션에서 r3 수정 전에 같은 명령(`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py" -v`, test-runner 실행·원본 로그에서 직접 셈)으로 잰 기준: **Ran 2874 · FAILED (failures=19, errors=9, skipped=3) · FAIL/ERROR 28줄**(r2 보고와 같음). 변경 뒤: **Ran 2889 · FAILED (failures=19, errors=9, skipped=3) · FAIL/ERROR 줄 28개**. 실패 id 28개가 정렬 diff로 기준과 완전히 같다(auto_core 테스트 실패 0) → 새 실패 0, 고쳐진 것 0. Ran +15 = 새 테스트 15개.
- **스키마 감사:** `validate_schema_contracts.py` PASS, errors []. 일지 관련 기존 테스트(test_portfolio_review_journal, test_decision_journal_cards)·test_language_contract 통과.
- **변이 확인(테스트가 옛 동작을 잡는지, 저장소 파일 변경 없이 메모리에서만 바꿔 실행):** 창을 옛 정의(발행일·다음 날)로 바꾸면 decide 토요일·휴장 테스트가, 세션 끝 검사를 없애면 휴장·세션 전 테스트가 실패함을 실행해 확인했다. R2-5 한정은 변이 실행을 하지 않았고 코드 경로로만 확인했다(옛 조건이면 그 경우가 rerun HOLD 경로로 가서 test_r2_5_is_only_for_the_same_run_day의 FAIL·rerun 파일 없음 단언이 깨진다).
- **기존 테스트 변경:** 약화 0, 단언 변경 0. 바꾼 것은 픽스처 날짜 다섯 곳뿐이다. 같은 날 실행 기록을 복사해 `run_day_kst`만 "2026-10-01"(또는 D)로 바꾼 기록들이 평가 세션 2026-10-09를 그대로 들고 있었다(10/01 기록이 10/09를 평가했다는, 현실에 없는 값). R3-3은 "출처의 평가 세션 = 오늘 평가 세션"을 새 세션 없음으로 읽으므로 이 픽스처로는 분류 대신 no_new_session이 된다. 새 도우미 `_as_of(record, run_day)`가 그날의 평가 세션·매수 세션을 넣는다(decide와 같은 `expected_completed_session`, 07:45 KST). 대상: DecideRunTests.test_outcome_read_failure_keeps_ticket_open_and_fails_g0 · TicketFlowTests.test_previous_apply_ticket_is_classified_journaled_and_ends_its_key · TicketFlowTests.test_outcome_that_disagrees_with_t1_fills_is_not_journaled · LedgerCarryTests.setUp(D 기록 = 평가 10/07·매수 10/08) · RerunAndScorerTests.test_mismatched_outcome_leaves_its_key_as_it_was.

## r3-1 R3-1~4: 바꾼 곳 · 고정한 테스트

| # | 바꾼 곳(파일:함수) | 고정한 테스트 |
|---|---|---|
| R3-1 분류 시점 | auto_core_tickets.py:`ticket_session_ended`(새: 주문표 세션 ≤ 평가 세션) · auto_core_decide.py:`read_outcomes`(세션이 안 끝난 주문표는 그 날짜를 조회하지 않고 분류·원장 변경 없이 open_tickets로, 사유 `G0_TICKET_SESSION_NOT_YET:<ticket_id>` → G0 실패 → 그날 새 주문표 없음), `_run`(evaluation_session·calendar 전달) | test_auto_core_tickets.OrderWindowTests.test_classified_only_after_the_session · test_auto_core_decide.TicketSessionNotYetTests.test_a_ticket_before_its_session_blocks_new_tickets(평가 10/09에 세션 10/12 주문표 → HOLD·주문표 0(그 주문표가 없으면 MU 1건)·열린 채·브로커 조회는 ust21050만) |
| R3-2 주문일 창 | auto_core_tickets.py:`order_days`(새: 발행 KST 날짜 ~ 운영 달력 core_close_at의 KST 날짜의 모든 날, 세션이 달력에 없거나 마감이 발행일 앞이면 None) · auto_core_decide.py:`read_outcomes`(주문표마다 자기 창의 행만으로 분류, 창 안 조회 하나라도 실패 = OUTCOME_UNKNOWN 그대로, 창 모름 = `ORDER_WINDOW_UNKNOWN:<id>` + `OUTCOME_UNKNOWN:<id>`) | tickets.OrderWindowTests: test_weekday_ticket_reads_its_issue_day_and_the_next · test_saturday_ticket_for_monday_reads_saturday_to_tuesday · test_winter_close_is_six_kst_the_next_day · test_early_close_uses_the_calendar_close · test_unknown_window_fails_closed / decide.OrderWindowTests: test_saturday_ticket_for_monday_reads_saturday_to_tuesday(토 10/17 발행·세션 월 10/19 → 화 07:45 실행: 월요일 KST 행 있으면 filled, 없으면 not_entered, 조회 20261017·18·19·20 4개, ticket_outcome 일지) · test_weekday_ticket_reads_its_issue_day_and_the_next(20261014·20261015 두 날) · 기존 LedgerCarryTests(ord_dt D 조회) 그대로 |
| R3-3 새 세션 없는 날 | auto_core_decide.py:`ledger_carry`(출처의 evaluation_session·기록도 돌려줌), `_run`(평가 세션 계산 직후 분기 — R2-5보다 먼저; R2-5 조건에 일지 payload run_day_kst = 오늘 추가), `_no_new_session`(새), `_empty_decision`(no_new_session false) · auto_core_compare.py:`NO_NEW_SESSION`, `streak`(연속 일수 유지) · schema auto-core-decision(no_new_session) | decide.OrderWindowTests.test_monday_holiday_is_a_no_new_session_day_then_wednesday_classifies(월 10/19 휴장, 토 발행·세션 화 10/20 → 화 07:45: OK·no_new_session·주문표 0·일지 바이트 그대로·push 0·브로커 조회 0·decision.json 스키마 통과·주문표 열린 채(issued_day 토)·carried_from 토·f6_ran true·대조 NO_NEW_SESSION·alert_states 출처 그대로·대시보드에 그 주문표 행 유지 / 같은 run_day 재실행 = 같은 결과·rerun 파일 없음 / 수 07:45: 토~수 5개 날짜 조회·filled·ticket_outcome 일지·⑪ 없음) · decide.OrderWindowTests.test_a_ticket_left_by_a_failed_read_waits_for_the_next_new_session · decide.SameSessionOtherDayTests.test_next_day_with_the_same_session_is_no_new_session_not_a_rerun(일지에 같은 평가 세션 core_decision이 있어도 다음 run_day는 OK·rerun 파일 없음) · .test_r2_5_is_only_for_the_same_run_day · compare.StreakTests.test_a_no_new_session_day_keeps_the_streak · 같은 run_day R2-5 기존 테스트(JournalEntryTests.test_apply_appends_a_hash_chained_core_decision_once · RerunAndScorerTests.test_a_different_rerun_is_kept_aside_as_hold) 그대로 통과 |
| R3-4 리플레이 | 코드 변경 없음. auto_core_replay는 세션마다 `evaluate_session`만 부르고 F6(결과 분류)·열린 주문표·재발행 원장이 없다(가정 "each session independent: no outcome history, G0 passes, no re-issue ledger"). R3-1·R3-2가 쓰일 곳이 없고 복제 구현도 없다 — 두 함수는 순수 함수 모듈 auto_core_tickets에만 두었다. R-A 앵커의 `anchor_session`(KST 주문일 → 그날 07:45 decide의 평가 세션)은 사전 등록(부록 C) 정의라 바꾸지 않았다 | test_auto_core_replay.OneImplementationTests.test_session_end_and_order_window_have_one_implementation(read_outcomes가 두 함수를 부르고 timedelta 없음, 리플레이에 결과 분류 경로 없음, 두 정의는 auto_core_tickets.py에만) |

## r3-2 새로 고른 것(이 지시가 정하지 않은 것) — Judge 2차 확인 요청

1. **R3-3 날, 출처가 못 읽어 열려 있던 주문표(세션은 이미 끝남)는 그날 분류하지 않고 다음 새 세션 날로 넘긴다**(`inputs.no_new_session.deferred`, 열린 채). 이유: 지시 R3-3의 "일지 쓰기 0"·"원장·미분류 주문표 그대로 이어받기"와 "F6는 R3-1대로(분류할 것이 있었다면 했으므로)"가 이 드문 경우(출처의 조회 실패 + 바로 다음 실행이 휴장 뒤)에는 함께 성립하지 않는다. 분류하면 그 결과를 일지에 남길 수 없고(append_auto_core_entries는 같은 평가 세션 core_decision이 있으면 거부 — 쓰려면 결과만 쓰는 새 일지 경로가 필요) 원장만 바뀌어, r2-3 1번이 막은 길(분류 결과가 일지에 영영 안 남음)이 다시 열린다. 다음 새 세션 날이 같은 브로커 행(날짜 고정)으로 분류·기록하므로 잃는 것은 하루 지연뿐이고, 그날은 주문표가 없어 G0 영향도 없다. f6_ran true는 지시 목적("이어받기 출처가 계속 이어지게")대로 둔다.
2. **R3-3 날 키움 조회 0**(ust21050 포함). 그날은 분류 결과를 확정하지 않으므로 읽어 쓸 곳이 없다.
3. **R3-3 기록 내용:** 출처의 같은 세션 판정 보기(symbols·evidence·buy_requirements·exposure·shock·account·earnings_calendar·facts_seen·registry_flags)와 alert_states(다음 날 반복 억제의 기준 — 비우면 다음 날 억제되던 알림이 모두 다시 나감)를 옮기고 candidates·blocked·outcomes는 비운다. compare = {status NO_NEW_SESSION, same_session_as, streak(같은 함수로 다시 셈 = 유지), required, explained_errors}, 그날 compare.json은 쓰지 않는다(F9가 돌지 않음). alerts는 push false 한 줄 "새 미국 세션 없음 — 평가 세션 <날짜> 그대로(주문표·일지 없음)". reasons [], no_action {true, ["NO_NEW_SESSION"]}, inputs.no_new_session {source_run_day, evaluation_session, not_yet, deferred}. T1 대조·G1 검사·연구 기록 대기·S7·봉 읽기는 하지 않는다(새 판정이 없으므로).
4. **R3-3 날 대시보드:** 아직 세션 전인 주문표의 dashboard.orders·runCore.tickets 행은 출처 것을 그대로 둔다(같은 id·발행 시각 — 새 주문표가 아니고 tickets 0·일지 0·TICKET push 0). 이유: 휴장 날 LATEST_DECISION이 그 행을 비우면, 사용자가 실제로 입력해야 하는 저녁(예: 월요일 휴장 뒤 화요일 세션 주문표를 화요일 저녁 입력)에 대시보드에서 주문표가 사라진다. 기록 모드에서 그런 행이 있으면 next_action_for_user도 평소 문구 "주문표 N건 — 저녁 키움 입력". 지시 "주문표 0"을 "새 발행 0"으로 읽은 것이라 확인 요청.
5. **R3-3 조건에 "출처 뒤 읽을 수 없는 기록 없음"을 더했다.** 읽을 수 없는 기록이 있으면 출처가 정말 최신인지 알 수 없어 R3-3을 쓰지 않고 정상 경로로 간다(G0_PREVIOUS_DECISION_UNREADABLE → HOLD, 기록 모드면 아래 6번의 일지 쓰기 거부 → FAIL·DECIDE_FAIL push).
6. **R2-5를 같은 run_day로 한정한 방법:** 일지 core_decision 항목 중 payload `run_day_kst` = 오늘인 것만 R2-5(같은 해시 → 그대로, 다름 → rerun HOLD). 다른 run_day인데 R3-3에 걸리지 않고 여기까지 온 경우(5번, 또는 일지 쓰기 뒤 마지막 스키마 검사에서 FAIL된 출처)는 append_auto_core_entries가 CORE_DECISION_ALREADY_RECORDED로 거부 → FAIL(decision.json 씀, DECIDE_FAIL push). r2의 "rerun 파일만·그날 decision.json 없음(다음 날 ⑪)"보다 잘 보이는 fail-closed다.
7. **사유 형식:** `G0_TICKET_SESSION_NOT_YET:<ticket_id>`(OUTCOME_UNKNOWN:<id>와 같은 꼴, 주문표마다 보임). push는 붙이지 않았다 — 새 세션이 있는 날 이 상태는 정상 운영에서 생기지 않고(출처 평가 세션 < 오늘인데 주문표 세션 > 오늘: 달력 이상 등) HOLD 사유로 남는다. 창을 모르면(주문표 세션이 달력에 없음, 마감이 발행일 앞) `ORDER_WINDOW_UNKNOWN:<id>` + `OUTCOME_UNKNOWN:<id>`(기존 OUTCOME_UNKNOWN push 그대로).
8. **조기 폐장:** 실제 조기 폐장(13:00 ET)은 KST 다음 날 02:00~03:00이라 끝 날짜가 정규 마감과 같다. 테스트는 실제 값(11/27 13:00 EST → 11/28 03:00 KST)과, 달력 값이 끝 날짜를 정함을 보이는 합성 값(KST 자정 전 마감 → 발행일 하루)을 함께 고정했다.
9. **기존 픽스처 날짜 다섯 곳**(r3-0) — 단언은 그대로다.

### 새로 찾은 사실(이번에 고치지 않음 — Judge·Cowork 판단 필요)

C. **주문일 창이 날짜 단위라 같은 종목·방향 주문표가 이어 나오면 창이 하루 겹친다**(평일: T 창 D·D+1, 다음 날 나온 T′ 창 D+1·D+2. 토요일 주문표도 끝 날짜에서 같은 꼴). 사용자가 T를 KST 자정 넘어(D+1 새벽, T 세션 진행 중) 입력하면 T′ 분류 때 그 행이 함께 잡혀 T′가 filled·changed로 잘못 분류될 수 있다. r1부터 있던 성질이고 r3는 평일 창을 바꾸지 않았다. G0 때문에 T가 분류되기 전 T′는 나오지 않으므로 둘이 동시에 열려 있지는 않다. 보완안(결정 필요, F6 정의 변경): 이미 다른 주문표에 귀속된 ord_no를 원장에 남겨 빼거나, 발행일 행은 ord_time ≥ 발행 시각만 쓰기.
   - 해결(r4): R4-1로 고쳤다 — 보완안 둘을 함께 넣었다. 원장 `attributed_orders`({ord_dt, ord_no, ticket_id}, 기록 모드에서만 갱신, 최근 30 달력일, ledger_carry·R3-3·HOLD/FAIL 기록으로 이어짐)에 든 행과 그 실행에서 앞 주문표가 가져간 행을 빼고, 발행일 행은 ord_time ≥ 발행 시각만 쓴다(`auto_core_tickets.ticket_rows`·`attribute_orders`, `auto_core_decide.read_outcomes`·`_run`). 아래 "# r4" 절.
D. 토요일(또는 휴장 앞) 주문표의 enterWindow 문구는 "한국 10/17 17:00 이후 ~ 정규장 개장 전(22:30)"으로 개장일을 적지 않는다(표시 전용, fillAt은 마감 날짜가 맞다).
   - 해결(r4): R4-2로 고쳤다 — 개장 KST 날짜가 발행일과 다르면 "한국 10/17 17:00 이후 ~ 10/19 22:30 개장 전"(운영 달력 core_open_at, 겨울 23:30), 같으면 지금 문구 그대로(`auto_core_tickets.enter_window`). fillAt은 그대로. 아래 "# r4" 절.

# r4

> 지시: docs/claude/redesign-t2-builder-r4-2026-10-11.md 1~3절(r3 "새로 찾은 사실" C·D — 주문 행 귀속 겹침·입력 창 문구, 마지막 Builder 수정). 같은 worktree, T2 지시문 4절의 허용 경로·금지 그대로. 정책·상태·일지·.claude·CLAUDE.md·tools 수정 0, 키움 실제 호출 0(테스트는 가짜 브리지).

## r4-0 요약

- **BLOCKED: 없음.**
- **바뀐 파일(모두 1차 허용 경로 안):**
  - scripts: auto_core_tickets.py(`issue_time`·`ticket_rows`·`attribute_orders`·`enter_window` 새, `ATTRIBUTION_DAYS`·`ISSUED_AT` 상수, `_common_ticket`, `classify_outcome` 설명 한 줄) · auto_core_decide.py(`ledger_carry`·`read_outcomes`·`_run`·`_no_new_session`·`_settle`·`_empty_decision`·모듈 설명)
  - schemas: auto-core-decision(`attributed_orders` 필수 칸 추가)
  - tests: test_auto_core_tickets.py(새 클래스 2개) · test_auto_core_decide.py(새 클래스 1개)
  - 문서: references/auto-core-decision.md(F6 흐름·F6 절·F5 입력 창) · 이 보고(r3 C·D 아래 "해결(r4):" 2줄 + 이 절)
  - auto_core_replay.py·auto_core_rules.py·auto_core_inputs.py·auto_core_compare.py·auto_core.py·auto_core_reconcile.py·portfolio_review_journal.py·ps1·다른 스키마·등록부·정책 제안 파일은 손대지 않았다(auto_core_reconcile.py는 import만).
- **줄바꿈·ASCII:** 바뀐 파일 모두 CRLF 그대로(LF 수 = CRLF 수, 단독 CR 0). 스크립트 비ASCII 0줄(한국어 문구는 `\uXXXX`, 이번에는 편집 도구가 한글로 바꾼 곳 없음 — grep으로 확인).
- **테스트 수:** 대상 `-p "test_auto_core*"` Ran 268 → 286 (+18) (OK, skipped 1 = 실자료 스모크). `def test_`(`grep -r "def test_" manage-us-stock-strategy/tests | wc -l`) 2851 → 2869 (+18). 감소 0. (r3 보고의 2850은 다른 위치에서 센 값으로 보인다 — 이번 수정 전 이 세션에서 같은 명령으로 잰 값이 2851이고, 이번 차이는 새 테스트 18개뿐이다.)
- **전체 스위트:** 이 세션에서 r4 수정 전에 같은 명령(`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py" -v`, test-runner 실행·원본 로그에서 직접 셈)으로 잰 기준: **Ran 2889 · FAILED (failures=19, errors=9, skipped=3) · FAIL/ERROR 28줄**(r3 보고와 같음). 변경 뒤: **Ran 2907 · FAILED (failures=19, errors=9, skipped=3) · FAIL/ERROR 줄 28개**. 실패 id 28개가 정렬 diff로 기준과 완전히 같다(auto_core 테스트 실패 0) → 새 실패 0, 고쳐진 것 0. Ran +18 = 새 테스트 18개.
- **스키마 감사:** `validate_schema_contracts.py` PASS, errors []. 일지 관련 기존 테스트(test_portfolio_review_journal 14, test_decision_journal_cards 30)·test_language_contract(2) 통과.
- **변이 확인(저장소 파일 변경 없이 메모리에서만 바꿔 실행):** ① 원장 목록을 무시하면(`ticket_rows`에 빈 집합) test_the_ledger_alone_keeps_a_later_row_out_across_a_hold_day · test_within_one_run_a_row_counts_once_in_both_modes(두 모드) · test_attributed_rows_are_left_out이 실패. ② 발행 시각 규칙을 끄면 test_issue_day_row_before_the_issue_time_is_not_the_tickets · test_an_issue_day_row_without_an_order_time_is_unknown · test_issue_day_rows_before_the_issue_time_are_left_out · test_unreadable_cells_fail_closed가 실패. ③ 둘 다 끄면 지시 시나리오 test_a_row_entered_after_midnight_counts_only_for_its_ticket가 실패(00:30 행은 두 규칙이 각각 막으므로 하나만 끄면 통과한다). ④ 옛 enterWindow 문구로 바꾸면 EnterWindowTests 5개 중 4개 실패(평일만 같은 문구라 통과 — 지시 "같으면 지금처럼").
- **기존 테스트 변경:** 0(단언·픽스처 모두 그대로). 기존 픽스처 행(helpers.fill_row)은 ord_no "0000001"·ord_time "17:30:00"이라 두 규칙에 걸리지 않는다.

## r4-1 R4-1·R4-2: 바꾼 곳 · 고정한 테스트

| # | 바꾼 곳(파일:함수) | 고정한 테스트 |
|---|---|---|
| R4-1 주문 행 귀속 | auto_core_tickets.py: `issue_time`(새: issuedAt "YYYY-MM-DD HH:MM KST"의 KST 시각), `ticket_rows`(새: 주문표 창의 (주문일, 행) 중 같은 종목·방향이고, (ord_dt, ord_no)가 이미 귀속된 것이 아니고, 발행일 행이면 ord_time ≥ 발행 시각인 것만 · 고른 행의 (ord_dt, ord_no) 목록), `attribute_orders`(새: 원장 + 오늘 귀속, 쌍마다 한 번, 최근 30 달력일만), `ATTRIBUTION_DAYS` = 30 · auto_core_decide.py: `read_outcomes`(새 필수 입력 attributed_orders, 오래된 주문표부터 분류, 원장 목록 + 그 실행에서 앞 주문표가 가져간 행을 빼고 `ticket_rows` → `classify_outcome`, 귀속 목록 반환 — T1과 어긋난 결과 제외), `_run`(기록 모드에서만 `attribute_orders`로 원장 갱신, 비교 모드는 출처 목록 그대로), `ledger_carry`(출처의 attributed_orders), `_no_new_session`·`_settle`(출처 목록 그대로 옮김), `_empty_decision`([]) · schema auto-core-decision(`attributed_orders` 필수: [{ord_dt date, ord_no, ticket_id}]) | test_auto_core_tickets.OrderAttributionTests: test_issue_day_rows_before_the_issue_time_are_left_out(발행일 07:00·07:44:59 뺌, 07:45:00(압축형 "074500") 포함, 다음 날 00:30 포함) · test_attributed_rows_are_left_out(같은 번호 다른 날은 다른 주문) · test_other_symbols_and_sides_are_not_candidates · test_unreadable_cells_fail_closed · test_ledger_keeps_thirty_calendar_days_and_each_pair_once(10/15 기준 09/16 남김·09/15 뺌, 중복 한 번) / test_auto_core_decide.OrderAttributionTests: **test_a_row_entered_after_midnight_counts_only_for_its_ticket**(지시 시나리오: 수 10/14 발행 T를 10/15 00:30 입력 → 10/15 실행 T filled·원장에 (10/15, 번호, T) · 10/15 발행 T′(같은 SOXL 매도) → 10/16 실행에서 같은 행을 다시 읽어도 T′ not_entered·행 0·일지 [T filled, T′ not_entered] · 30일 정리: 10/15 실행에서 09/15 항목 빠짐, 10/16 실행에서 09/16 항목 빠짐) · **test_the_ledger_alone_keeps_a_later_row_out_across_a_hold_day**(10/15 08:10 행(T′ 발행 07:45 뒤, 연구 기록 대기 뒤 읽힘)을 T가 가져감 → 10/16 T1 없음 HOLD 기록이 목록을 그대로 옮김(f6_ran false·carried_from 10/15) → 10/17 실행 T′ not_entered — 원장만이 막는 경우) · test_compare_mode_keeps_no_list(비교 모드는 원장 [] — T′가 같은 행으로 filled, r4 전과 같음) · test_within_one_run_a_row_counts_once_in_both_modes(한 실행에서 화 발행 A와 수 발행 B: 수 08:00 행은 오래된 A만 · 기록 모드는 원장에 남고 비교 모드는 []) · **test_issue_day_row_before_the_issue_time_is_not_the_tickets**(발행일 07:00 행 → not_entered, 귀속 없음) · test_an_issue_day_row_without_an_order_time_is_unknown(OUTCOME_UNKNOWN·열린 채) · test_an_outcome_that_disagrees_with_t1_adds_nothing · test_a_no_new_session_day_carries_the_list(월 휴장 → 화 no_new_session 기록이 출처 목록 그대로, 스키마 통과) |
| R4-2 입력 창 문구 | auto_core_tickets.py: `enter_window`(새: 발행일 17:00 ~ 운영 달력 core_open_at의 KST 날짜·시각; 개장 KST 날짜 = 발행일이면 지금 문구 그대로), `_common_ticket`(enterWindow = `enter_window(run_day, 세션 행)`, fillAt 그대로) | test_auto_core_tickets.EnterWindowTests: test_weekday("한국 10/14 17:00 이후 ~ 정규장 개장 전(22:30)") · test_saturday_for_monday("한국 10/17 17:00 이후 ~ 10/19 22:30 개장 전") · test_tuesday_after_a_holiday(월 10/19 휴장 → "~ 10/20 22:30 개장 전") · test_winter_time("한국 11/4 … 정규장 개장 전(23:30)", "한국 11/7 17:00 이후 ~ 11/9 23:30 개장 전") · test_the_ticket_carries_it_and_fill_at_is_unchanged(실제 주문표 경로: 토 10/10 발행·세션 월 10/12 → "한국 10/10 17:00 이후 ~ 10/12 22:30 개장 전", fillAt "10/13 05:00 (한국) 정규장 종가" 그대로) |

## r4-2 새로 고른 것(이 지시가 정하지 않은 것) — Judge 2차 확인 요청

1. **원장 항목 모양:** `{ord_dt, ord_no, ticket_id}`. ord_dt는 그 행을 읽은 조회일(ust21150 요청의 ord_dt — 행 자체에는 날짜 칸이 없다)을 ISO 날짜(YYYY-MM-DD, 스키마 format date)로 적는다. ticket_id는 지시의 쌍에 더한 추적용 칸이다(어느 주문표가 가져갔는지 Judge·Cowork가 바로 본다). 판정에는 (ord_dt, ord_no) 쌍만 쓴다.
2. **30 달력일 = 실행일 포함 30일**(ord_dt ≥ 실행일 − 29일). 정리는 원장을 갱신하는 실행(기록 모드·F6가 선 실행)에서만 한다. 옮겨 적는 기록(HOLD/FAIL·no_new_session·비교 모드)은 출처 목록을 바꾸지 않는다.
3. **T1과 어긋난 결과(R2-7)의 행은 원장에 넣지 않는다.** R2-7 "불일치 결과는 원장 갱신 안 함"과 맞추었다. 그 실행 안에서는 그 행도 가져간 것으로 본다(같은 실행의 다른 주문표가 다시 세지 않음). 그날은 G0가 실패해 새 주문표가 없고 다음 주문표의 창은 그 뒤에 시작하므로 실제 차이는 없다.
4. **분류 순서 = 오래된 주문표 먼저**(issued_day, issuedAt 순 안정 정렬). 한 실행에서 같은 행이 두 주문표 창에 들면 먼저 발행된 쪽이 가져간다. ledger_carry의 목록이 이미 그 순서라 기존 출력 순서는 바뀌지 않는다.
5. **비교 모드:** 빼는 목록 = 출처 원장 목록(기록 모드였던 기록에서 이어진 것 — 순수 비교 모드 이력이면 빈 목록) + 그 실행에서 앞 주문표가 가져간 행. 결정 기록의 attributed_orders는 출처 것 그대로다.
6. **읽을 수 없는 칸 = 그 주문표 결과 unknown(fail-closed):** 같은 종목·방향 행에 ord_no가 없으면(ORD_NO_UNREADABLE), 발행일 행의 ord_time을 읽을 수 없거나 주문표 issuedAt을 읽을 수 없으면(ORD_TIME_UNREADABLE·ISSUED_AT_UNREADABLE) → 기존 OUTCOME_UNKNOWN:<id> 경로(열린 채·G0 실패·push). 다른 종목·방향 행과 발행일이 아닌 날의 ord_time은 보지 않는다. 사유 줄에는 기존 ROW_UNREADABLE처럼 세부 note를 따로 남기지 않았다. ord_time 해석은 T1 체결 읽기와 같은 함수(`auto_core_reconcile._clock`: "17:29:23" 또는 "172923", KST)를 import해 쓴다(복제 없음).
7. **발행 시각 = issuedAt의 시:분(초 0)** — issuedAt은 "YYYY-MM-DD HH:MM KST"로 초가 없다. 경계는 같은 시각 포함(ord_time ≥ 07:45:00). 비교는 issued_day 날짜의 행에만 하고, issuedAt의 날짜 부분은 issued_day와 대조하지 않는다(운영에서는 늘 같다; 기존 테스트 픽스처 하나가 다른 날짜를 들고 있어 대조하면 그 테스트가 깨진다).
8. **R4-2 문구:** 날짜가 다를 때는 지시 틀 그대로 "한국 10/17 17:00 이후 ~ 10/19 22:30 개장 전"(이때는 "정규장" 낱말이 없다). 같을 때는 지금 문구 "한국 10/14 17:00 이후 ~ 정규장 개장 전(22:30)" 그대로. 개장 KST 날짜는 실제로 언제나 세션 날짜와 같다(09:30 ET = 같은 날 22:30/23:30 KST). 대시보드 orders[].enterWindow는 주문표 값을 그대로 옮기므로 따로 고치지 않았다.

## r4-3 새로 찾은 사실(이번에 고치지 않음 — Judge·Cowork 판단 필요)

E. **창 끝 날짜의 마감 뒤 행:** R4-1은 창의 시작(발행 시각)만 자른다. 창 끝 날짜(세션 마감 KST 날짜)의 행은 시각과 무관하게 그 주문표 것으로 센다. 예: T(세션 D)의 마감은 D+1 05:00 KST인데, 사용자가 D+1 07:00 KST에 같은 종목·방향 주문을 따로 넣으면 D+1 07:45 실행이 그 행을 T에 붙여 T가 changed 등으로 잘못 분류될 수 있다(원장에 귀속되므로 T′ 쪽 이중 계산은 없다). 보완안(결정 필요): 끝 날짜 행은 ord_time ≤ 세션 마감 시각(KST)만 쓰기.
F. **같은 날 조회 안 중복 행:** 한 날짜 조회에 같은 ord_no 행이 두 번 오면(쪽 나눔 중복 등) `classify_outcome`이 수량을 두 번 더한다. T1 체결 읽기는 FILL_ROW_DUPLICATE_CONFLICT로 막지만 F6에는 그 검사가 없다(r1부터). 실측 응답에서 중복을 본 적은 없다.
G. (드묾) 한 실행에서 같은 종목·방향 주문표 두 개가 함께 분류되는데 오래된 쪽이 unknown이면, 그 행들은 가져간 것으로 치지 않아 새 쪽이 가져갈 수 있다. G0 때문에 같은 종목·방향 주문표가 동시에 열려 있는 일은 정상 운영에서 생기지 않는다.

# r5

> 지시: docs/claude/redesign-t2-builder-r5-2026-10-12.md 1~3절(P-2 PWR·LITE 정책 등록에 맞춘 테스트 2개, 테스트만).

## r5-0 요약

- **BLOCKED: 없음.**
- **바뀐 파일:** tests/test_portfolio_exposure.py · tests/test_auto_core_tickets.py · 이 보고. scripts·schemas·references·등록부·정책·상태·일지·.claude·CLAUDE.md·tools 0줄. alert_policy.json·auto_core.json은 Cowork 상태 그대로(되돌리지 않음).
- **테스트 수:** `-p "test_auto_core*"` 287 OK (skipped 1) · `test_portfolio_exposure*` 125 OK · `test_run_portfolio_exposure_review*` 24 OK · `test_portfolio_status*` 15 OK. `def test_`(`grep -r "def test_" manage-us-stock-strategy/tests`) 2871 → 2872 (+1, 감소 0).
- **전체 스위트(test-runner, 원본 로그에서 직접 셈):** Ran 2907(r4) → **2908** · FAILED (failures=19, errors=9, skipped=3) · FAIL/ERROR 줄 **28개** = 기준선 28줄(r4 보고)과 같은 개수. 그중 auto_core·portfolio_exposure·run_portfolio_exposure_review·portfolio_status 테스트 실패 0. 기준선 id 목록 파일이 이 worktree에 없어 정렬 diff는 못 했다(개수·파일군 비교만).

## r5-1 바뀐 곳

- **R5-1** test_portfolio_exposure.py · `PolicyValueTests.test_real_policy_carries_the_fixed_r2_values`: 기대 배수에 `"PWR": 1, "LITE": 1` 추가, `card_stock_core == ["BE","MU","NBIS","DELL","AMD","PWR","LITE"]` 단언 추가. 다른 단언 그대로.
- **R5-2** test_auto_core_tickets.py · `BuyTicketTests.test_policy_unregistered_instrument_has_no_ticket`: run() 전에 시나리오 정책 사본에서 PWR을 card_stock_core·nominal_multipliers에서 뺀다. 단언 그대로.
- **R5-2 새 테스트** `BuyTicketTests.test_registered_instrument_is_not_blocked_by_policy_registration`: 사본 정책에 PWR 등록(없을 때만) 뒤 run() → 막힘 사유에 POLICY_UNREGISTERED_INSTRUMENT 없음.

## r5-2 새 테스트의 단언 범위

- **주문표 1건까지 단언함:** `tickets_of(result, "PWR", "buy")` 길이 1. 실행에서 통과(다른 관문 때문에 막히지 않음).

## r5-3 새로 찾은 사실(고치지 않음)

- 없음.
