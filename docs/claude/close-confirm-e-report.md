---
id: close-confirm-e-report
title: 확정 종가 반영 e — Builder 보고 (주문표 판정 유지 구간 priceCalc band·hold, 매수 입력 관문 좁힘)
date: 2026-10-21
class: 권한·한도 변경(K3) 수동 경로 — Builder 보고. Judge는 별도 Opus 세션(docs/claude/close-confirm-e-judge-prompt.md, Cowork 작성 예정)
instruction: docs/claude/close-confirm-e-builder-prompt.md (메인 체크아웃, 읽기 전용으로 처음부터 끝까지 읽음)
worktree: .claude/worktrees/work-close-confirm-e (branch worktree-work-close-confirm-e) — 커밋하지 않음
authority: order_authority false · quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY 줄 손대지 않음 · 키움 호출 없음
---

# 0. worktree HEAD

- `git rev-parse HEAD` = `3e753f3b6cee0e0ed1a1720809ef7c759c779f39` = 지시문 base. 그 사이 커밋 없음.
- 시작 시 `git status --short` 비어 있음. 지시문 머리말의 base sha256(작업 트리 CRLF / LF 정규화) 8개 파일 모두 일치함을 편집 전에 확인했다
  (auto_core_tickets f796af14d92b/c1e9d1f736d7 · auto_core_decide b1ea5d7be88e/ca09842e492a · auto_core_replay d346ba92f783/088a0f30ba20 ·
  ticket schema 24d5cd99917c/a9fbc1d8f8d8 · references 830dc911c738/9dd2af46d6d6 · risk1r 98a40b55dc7e/444ba156db25 ·
  enter_window 9cc3d3c026ea/b1a217e32469 · t2rc-oracle.py d79b12212ee2/6a74f813c918).

# 1. 파일별 바뀐 곳

## manage-us-stock-strategy/scripts/auto_core_tickets.py
- `plan()`(721행~): 매도 루프 본문 → `_plan_sell(ctx, symbol, reduce_items, global_reasons, blocked, candidates)`(788행), 매수 루프 본문 →
  `_plan_buy(ctx, row, add_symbols, global_reasons, blocked, candidates)`(806행). 둘 다 주문표 또는 None. `global_reasons·reduce_items·add_symbols`
  세 줄은 `_circuit_inputs(ctx)`(778행)로 옮겨 plan과 hold가 같은 식으로 읽는다. 본문은 글자 그대로 옮김(E1).
- `plan()` 756~757행: `_limit_daily`(753행) **뒤**·plan_premise·번호 **앞**에 `if ctx.get("hold_eval") is not None: tickets = _with_hold_ranges(ctx, tickets, blocked)`.
- 새 상수(문자열·필드 이름만, 판정 상수 없음): `HOLD_BASIS = "SYMBOL_CLOSE_ONLY:S7_FIXED"`, `HOLD_UNVERIFIED = "HOLD_RANGE_UNVERIFIED"`,
  `HOLD_SELF_CHECK_SKIP = ("after_sale", "ticket_id")`(828~832행).
- 새 함수
  - `_hold_ticket(ctx, ticket, price)`(835행): `ctx["hold_eval"](symbol, price)`가 준 ctx로 같은 방향 helper를 scratch blocked·candidates와 함께 다시 부름.
    매수는 그 ctx의 buy_rows에서 그 종목 행을 다시 꺼냄. 결과 (주문표, None) 또는 (None, `NO_TICKET:<그 종목·방향 첫 사유, CARD_TRIM_SIZE_MISSING 제외>` |
    `NO_TICKET:CIRCUIT_CLOSED` | `DATA`).
  - `_hold_break(ctx, ticket, price)`(861행): 판정 유지 정의. 주문표 없음 → 위 코드, r_b < r → `STEP_DOWN`, 매수만: `p_b = (b × priceCalc.mult)` 센트 내림,
    `max_buy_ticket_pct_of_equity`가 있으면 `floor(equity × pct / p_b) < qty` → `G2B`, `floor(cash / (p_b × (1 + CASH_BUFFER))) < qty` → `CASH`. 유지면 None.
  - `hold_range(ctx, ticket)`(889행): 자기 점검(b = ref, after_sale·ticket_id·gap.plan_premise 제외 전체 비교) → 위로 ⌈ref⌉센트(ref가 센트면 +0.01)부터
    band.hi까지, 아래로 ⌊ref⌋센트(센트면 −0.01)부터 band.lo까지 한 센트씩, 처음 깨지는 센트에서 멈춤. 스캔 중 예외 → 그 센트 `DATA`.
    ref에서 예외 → `unverified`(`EVAL_ERROR:<예외 이름>`), ref에서 ctx 없음 → `unverified`(`DATA`), ref 주문표가 다르거나 없음 → `unverified`(`SELF_CHECK_MISMATCH`).
  - `_with_hold_ranges(ctx, tickets, blocked)`(939행): 남은 주문표마다 hold_range → `priceCalc = {...기존, "band": {lo, hi}, "hold": {...}}`.
    매수 ok → `priceCalc.lo/hi = hold.lo/hi`, 매수 unverified → 주문표 제외 + blocked `{"symbol", "side": "buy", "reasons": ["HOLD_RANGE_UNVERIFIED"]}`
    (candidates 그대로). 매도 → lo/hi = band 그대로(ok·unverified 모두), 주문표 유지.
- `classify_outcome` 645~648행: `band = ticket["priceCalc"].get("band") or ticket["priceCalc"]`에서 lo·hi를 읽는다(그 밖 그대로, 금지 단어 없음 — 가드 테스트 통과).
- 바꾸지 않음: loc_price(376~392), SIZING/CONSTANTS 값, ALLOWED_NO_TICKET, _limit_daily, plan_premise, after_sale_path, _sell_ticket/_buy_ticket(G0~G5), 후회표.

## manage-us-stock-strategy/scripts/auto_core_decide.py
- `_bars_with_close(item, session, price)`(897행, 모듈 함수): load_symbol 결과의 사본. 평가 세션 봉의 raw·adjusted 모두 close = b, high = max(high, b),
  low = min(low, b)(None 유지). raw와 adjusted가 같은 객체면 사본도 하나. 원본 불변. status ≠ OK·세션 없음·평가 세션 raw close ≠ adjusted close면 None.
- `evaluate_session(..., hold_range: bool = False)`(919행). 본문의 종목별 호출을 내부 helper로 뺐다(같은 함수·같은 인자, 계산 로직 복사 없음):
  `raw_closes`(958, 원래 929~930), `judge`(962, evaluate_symbol + official_evidence + evidence_summary, 원래 934~949), `shock_of`(1021, rrec1, 원래 987~992),
  `requirement_row`(1047, buy_requirements, 원래 1010~1016), `data_reason`(1057, 원래 1017~1019), `known`·`sigma_of`·`marks_of`(1075~1082, ctx closes·sigmas·indicators 식).
- `hold_eval(symbol, price)`(1101~1128행, closure): **호출 시점** ctx 얕은 복사. 그 종목 봉만 `_bars_with_close`로 바꾸고 같은 호출로 series(build_series)·F1·근거(judge)·
  rule-file N(rule_file_nominal, closes_raw에서 그 종목만 b)·R-REC1(shock_of: candidate·rg2_series·SOXX benchmark가 그 종목이면 b의 series)·요건 행(close = b, N·근거·shock은 b의 것)·
  data_reason·scenarios·indicators를 다시 구한다. 바꾸는 키: closes·sigmas·symbols·evidence·buy_rows(그 종목 행만)·data_reasons·scenarios·indicators, `model_for=None`, `hold_eval=None`.
  review·s7·equity·weights·proposal_results·keys·cash·gate0·gate1·redeploy_*·policy_instruments·config·calendar는 그대로. `if hold_range: ctx["hold_eval"] = hold_eval`(1130~1131).
- `_run` 655~665행 evaluate_session 호출에 `hold_range=True` 한 줄. 다른 흐름 그대로. auto_core_replay.py 손대지 않음(기본 False).

## manage-us-stock-strategy/schemas/auto-core-ticket.schema.json
- priceCalc에 description 한 줄 + 선택 속성 `band`(lo·hi number ≥ 0, required lo·hi, additionalProperties false),
  `hold`(status enum ok|unverified, lo·hi number|null ≥ 0, lo_limit·hi_limit string|null, checked integer ≥ 0, reason string|null, basis string minLength 1,
  8개 키 required, additionalProperties false). priceCalc required는 그대로 → band·hold 없는 옛 주문표도 유효.
- auto-core-decision.schema.json은 바꾸지 않음(tickets가 ticket 스키마를 참조, open_tickets·orders는 object — decision 전체 검증 통과).

## manage-us-stock-strategy/references/auto-core-decision.md
- 161~167행: Price 항목 뒤에 "Hold range (close-confirm e, user decision 2026-10-20)" 영문 bullet(정의·매수 lo/hi 좁힘·매도 그대로와 경고·unverified 매수 = 주문표 없음·결과 분류는 band).

## 테스트
- 새 파일 manage-us-stock-strategy/tests/test_auto_core_hold_range.py(ASCII, CRLF): 28개 테스트(3절). 되돌리기 함수 `revert_hold_view`를 여기에 둔다.
- 허용 변경 1·2만 사용(3절). 허용 변경 3은 필요 없었다(깨진 decide 수준 priceCalc 단언 없음).

# 2. E1~E7 확인 방법과 결과

- **E1 hold 끔 = base**: (a) base 3e753f3를 `git archive`로 임시 폴더에 풀어 base 코드와 새 코드에서 같은 10개 시나리오(risk1r 6개 + 좁은 매도 + EV5 209.0 + EV5 208.615 + TRIM 크기 없음)의
  `evaluate_session` 기본 호출(리플레이와 같은 호출, hold_range 인자 없음) 출력 전체(symbols·evidence·rows·planned·s7·nominal·shock·series 등)를 JSON으로 떠서 비교 → 10개 모두 동일.
  (b) 테스트 H7: risk1r GOLDEN 6키(default·g2b·cash5·research_block·sell·pwr) 그대로, 옛 plan() 본문을 글자 그대로 옮긴 `base_plan`과 새 plan()이 9개 시나리오에서 planned·rows 동일,
  auto_core_replay 원문에 hold_range 없음·기본값 False. (c) 실데이터: base 코드 리플레이(base-off)와 새 코드 리플레이(cce-off)의 replay.json 동일(4절 R2).
- **E2 hold 켬(decide)**: (a) base vs 새 코드 decide(test_auto_core_decide.Env, compare·apply)의 decision 전체를 비교 — priceCalc를 되돌린 뒤 남는 차이는 inputs.*.path(Env 임시 폴더가 실행마다 다름),
  journal.decision_sha256과 거기서 나온 일지 entry_id·review_id·previous_entry_sha256, user_confirmed_at(추가 시각)뿐. 일지 payload는 decision_sha256 외 동일.
  (b) 테스트 H11 HoldCauseTests: 같은 프로세스에서 hold_range를 False로 강제한 decide와 켠 decide를 비교 — status·reasons·tickets·candidates·blocked·no_action·keys·alerts·dashboard·
  compare·next_action_for_user·outcomes·open_tickets·symbols·evidence·buy_requirements·exposure·shock·account·facts_seen이 되돌린 뒤 동일, journal은 decision_sha256 외 동일,
  apply 모드 dashboard orders의 priceCalc = 주문표 priceCalc. (c) H1: 시나리오 수준에서 되돌린 planned 전체와 evaluate_session의 다른 출력 키 동일.
  (d) H6: unverified 매수는 주문표가 빠지고 blocked에 HOLD_RANGE_UNVERIFIED 1건, candidates 그대로, no_action은 plan 규칙대로(`{"value": true, "reasons": ["HOLD_RANGE_UNVERIFIED"]}`).
- **E3 결과 분류 불변**: classify_outcome가 band(없으면 lo·hi)를 읽음. 테스트 H8: band가 있는 새 주문표와 band 값을 lo/hi로 둔 옛 주문표에서 매수·매도 × 9경우(유지 구간 안, band 안·유지 구간 밖,
  band 위·아래 밖, 부분 체결, 미체결, 취소, LOC 아님, 미입력) 결과 dict 전체 동일. band 안·유지 구간 밖 주문가 220.50은 "filled"(band 기준)임을 따로 단언.
- **E4 구간 정확성**: 테스트 H2(FullPathTests, 8개): H1 매수(MU 433센트)·H1 매도(SOXL 173)·센트 사이 ref(208.615, 418)·H3(209.0, 419)·H4 현금(433)·H4 G2b(433)·H5 좁은 매도(201)·
  보충 ETF(SOXL 201센트)에서 band 안 **모든** 센트 b마다 전체 경로(evaluate_session에 그 종목 평가 세션 봉만 b, s7_runner = ref 검토의 제안 평가를 (symbol, target_weight)로 찾아 주는 가짜,
  없으면 NOT_EVALUATED_AT_REF로 통과 아님)의 판정 **코드**(bool보다 강함: None·NO_TICKET:<사유>·STEP_DOWN·CASH·G2B)가 스캔의 `_hold_break` 코드와 같음, hold = ref부터 끊기지 않는 최대 구간,
  전체 경로의 ref 주문표 = 실제 주문표(band·hold 제외)임을 단언. 제안 목록이 ref와 달라지는 분기: 앞 7개 시나리오에서는 0센트였고, 보충 ETF 시나리오(SOXL, 새 + 신호 둘)에서 60센트 —
  그때마다 차이는 SOXL 하나뿐이고 두 경로 모두 SOXL 주문표 없음(NO_TICKET:CIRCUIT_CLOSED)을 단언(분기 실행 횟수 > 0도 단언).
- **E5 조이기만**: H1에서 band.lo ≤ hold.lo ≤ ref ≤ hold.hi ≤ band.hi, 매수 lo/hi = hold, 매도 lo/hi = band(H1·H5·H6). PRICE_RANGE·SIZING 등 상수 diff 없음.
  E2 비교(되돌린 뒤 동일)로 구간 계산이 주문표를 새로 만들거나 수량·가격을 바꾸지 않음을 확인.
- **E6 결정론**: H9 — 같은 시나리오 두 번 실행 planned 동일, plan 뒤 ctx로 hold_range를 다시 불러도 같은 hold. hold에는 시간·실행 환경 값이 없다(8개 키뿐).
  decision_identity_hash(757행)는 주문표를 해시하므로 같은 입력이면 같은 해시(R2-5 그대로).
- **E7 입력 불변**: H9 — 스캔 뒤 scenario.bars(raw·adjusted 깊은 비교)와 raw is adjusted 동일성 유지, plan 전후 ctx는 기존 동작(redeploy_candidate 설정) 외 동일, 추가 hold_range 호출 뒤 ctx·review 불변.
  `_bars_with_close` 단위 테스트: 입력 불변, raw is adjusted면 사본 하나, 따로인 adjusted도 바뀜, 불가(상태 ≠ OK·세션 없음·raw ≠ adjusted close) → None, high/low None 유지.

# 3. 테스트

| 실행 | 기준선(변경 전, Windows worktree) | 변경 뒤 |
|---|---|---|
| `-p "test_auto_core*.py"` | Ran 460 · failures 1 · skipped 1 | Ran 487 · failures 1 · skipped 1 (새 파일 27개 판에서 완주) + 최종 새 파일 단독 `-p "test_auto_core_hold_range.py"` Ran 28 · OK |
| 전체 `discover -s manage-us-stock-strategy/tests` | Ran 3247 · failures 21 · errors 9 · skipped 3 | **미완료** — 변경 뒤 실행이 시스템 메모리 부족으로 중단됨(7절) |
| `validate_schema_contracts.py` | — | PASS(errors []) |

- 대상 집합의 실패 1건은 기준선과 같은 `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')`(등록부 원인, 이 작업 범위 밖).
  기준선에서 GoldenCauseTests·UnchangedTicketTests는 Windows에서 통과했다(지시문 예상대로). **새 실패 0**.
- 전체 스위트 기준선 실패 30건은 enter-window3 dev-run Windows 참고값(Ran 3247 · 실패 30)과 같고 auto-core 관련은 PLTR 1건뿐.
  변경 뒤 전체 스위트는 결과를 얻지 못했다(7절). 그래서 "전체 스위트 새 실패 0"은 **확인 필요**다. 확인된 범위: auto-core 대상 집합 487개(새 파일 27개 판) 새 실패 0,
  최종 새 파일 28개 OK, 스키마 감사 PASS. 기준선 실패 30건은 모두 auto-core 밖 모듈(kiwoom priority·identity authority·dashboard 등)이고, 이 작업이 바꾼 모듈은 auto_core_tickets·auto_core_decide뿐이다.
- 대상 집합 487개 실행 뒤 새 파일에 E4 테스트 1개(test_supplement_proposals_change_with_the_close)를 더했다. 그 판(28개)의 대상 집합 재실행도 메모리 부족으로 중단됐고, 새 파일 단독 실행(28개 OK)만 끝났다.
- 실행 방법: 기준선·변경 뒤 모두 `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover ...` 출력을 scratchpad 파일로 받아 Ran·실패 이름만 추렸다(test-runner 서브에이전트 대신, 호출자 지시의 대안 방식).
  주의: 전체 스위트 기준선 실행이 도는 동안 편집을 시작했다. 테스트 모듈은 실행 시작 시 import되므로 영향이 없다고 보며, 실패 목록이 위 참고값과 같고 auto-core 실패는 PLTR뿐이다.
  대상 집합 기준선(460/1)은 편집 전에 끝났다.
- 새 테스트(test_auto_core_hold_range.py, 28개): BasicTests(test_buy_and_sell, test_reference_between_cents) · FullPathTests(test_h1_buy, test_h1_sell,
  test_h1_reference_between_cents, test_h3_buy_boundary, test_h4_cash, test_h4_g2b, test_h5_sell, test_supplement_proposals_change_with_the_close) ·
  BuyBoundaryTests(test_own_minus_two_sigma_day_stops_the_range_inside_the_band) · CashTests(test_cash_just_above_the_ticket_stops_hi_at_the_hand_computed_cent) ·
  G2bTests(test_g2b_cap_stops_hi) · SellWarningTests(test_narrower_sell_range_keeps_the_band_and_the_ticket) · UnverifiedTests(5개: 틀린 hold_eval 매수 제외·매도 유지,
  스캔 중 예외/None → DATA, ref 예외/None → unverified, decide 계속) · HoldOffTests(3개: GOLDEN 6키, helper 분리 = base plan, 리플레이 hold 없음) · OutcomeTests(1) ·
  DeterminismTests(2) · SchemaTests(1) · HoldCauseTests(2: test_only_price_calc_changes, test_reverted_view_hashes_as_the_old_golden — 뒤의 것은 Windows에서만, Linux 해시가 달라서 skipUnless win32).
  손 계산 경계: H4 현금 6146.00 → 215.89 × 1.0142 = 218.955638 → 218.95, floor(6146 / (218.95 × 1.0025)) = 28(유지) / 215.90 → 218.96 → 27 → hold.hi = 215.89 `CASH`.
  H3 EV5 경계: 208.61 이하 MU 1일 수익률 ≤ −2σ60(사건), 208.62 이상 아님 → hold.lo = 208.62 `NO_TICKET:REQ5_RREC1:no`(band 206.91~211.09).
- 허용 변경(파일:행)
  1. manage-us-stock-strategy/tests/test_auto_core_risk1r.py 53행(주석 1줄 "close-confirm-e: priceCalc band·hold 추가(매수 lo/hi = 판정 유지 구간) — test_auto_core_hold_range HoldCauseTests로 확인" — 지시문이 준 문구 그대로라 한국어, 이 파일의 기존 주석과 같은 방식),
     54행 decide_compare `2e565c3b…` → `6d24251698e869aaab0aea56603a1a60adffb63ea278320d540af232bcc550d2`, 56행 decide_apply `d78459cb…` → `e4eecf21ef59b01506ee4ba00b8625e3054f39d5867a919f6cd7b02e59303092`. 다른 6키 그대로.
  2. manage-us-stock-strategy/tests/test_auto_core_enter_window.py 28행 import 1줄(`from test_auto_core_hold_range import revert_hold_view`), 216행 old 뷰 해시 전에 `revert_hold_view` 적용(BASE_GOLDEN 그대로).
     revert_hold_view는 깊은 복사로 새 뷰를 돌려주고 입력을 고치지 않는다(223행의 new·old 원본 비교 그대로 통과).
  3. 해당 없음.
- GOLDEN 새 값 근거(H11, Windows 실측): 켠 decide의 GOLDEN 뷰에서 priceCalc를 되돌리면(band·hold 삭제, lo/hi = band) 해시가 옛 값 `2e565c3b7f2d…`·`d78459cbeb51…`과 같다
  (HoldCauseTests.test_reverted_view_hashes_as_the_old_golden 통과, 같은 프로세스 끔/켬 비교 test_only_price_calc_changes 통과). 8키 전체에서 되돌린 뷰 = 옛 GOLDEN도 별도 스크립트로 확인했다.

# 4. 실데이터 R1~R3 (읽기 전용: 코드 = worktree, 입력 = 메인 체크아웃, 출력 = 저장소 밖 %TEMP% 아래 scratchpad\cce-check)

방법: 저장소 밖 드라이버가 worktree 스크립트를 import하고 경로 상수만 메인 체크아웃으로 돌렸다(regular_session_close_history.TRUSTED_ROOT, decide CLOSES_ROOT·DOCS_DIR·RECOVERY_GATE_DOC·
POLICY_PATHS["alert"], replay REPO_ROOT·MEASUREMENTS_PATH, 등록부·관심목록 경로; 등록부 커밋 확인은 리플레이가 어차피 committed=True로 덮으므로 git 호출 없이 통과로 줌). 키움 호출 없음, 저장소에 쓰지 않음.

- **R1 센트 단위**(daily_bars raw close, 각 종목 최근 120세션 2026-04-29~2026-10-19): 센트가 아닌 종가 수 — BE 36 · DELL 31 · GRID 16 · LITE 8 · MU 15 · MVLL 26 · NBIS 12 · PWR 21 ·
  SOXL 52 · SOXX 9. 덧붙여 120세션 모두 close가 [low, high] 안(0건 밖), high·low 없음 0건 → b = ref 봉 사본이 원본과 같다(자기 점검의 거짓 불일치 원인 없음).
- **R2 리플레이 대조**(기본 기간 2026-07-10~2026-10-09, P-R1·P-R2 각 65세션 모두 OK, 자료 없음 0): `cce-off`(그대로)와 `cce-on`(evaluate_session을 hold_range=True로 감쌈)의
  replay.json·summary.md **동일**. 주문표 수 0건(근거 11의 예상대로; 막힘 1위 NO_CIRCUIT_OPEN P-R1 63·P-R2 64세션), hold_range 호출 0, unverified 0, 예외 0, 판정 R_A PASS·R_B PASS·R_C NOT_MET(양쪽 같음).
  추가로 base 코드(3e753f3) 리플레이 `base-off`의 replay.json = 새 코드 `cce-off` (E1 실데이터).
- **R2b 강제 측정**(`--start 2026-10-19 --end 2026-10-19`, P-R1 ctx = MVLL 159·SOXL 53·NBIS 13; 그 세션 주문표 0건이라 판정 비교 없이 hold_eval + 같은 방향 helper 계산만):

| 방향 | 종목 | ref(센트 단위?) | band | 센트 수 | ms/센트 최대 | 중앙값 | DATA |
|---|---|---|---|---|---|---|---|
| 매수 | BE | 226.105 (아님) | 223.84~228.37 | 454 | 12.90 | 3.07 | 0 |
| 매수 | MU | 905.415 (아님) | 896.36~914.47 | 1812 | 13.72 | 4.05 | 0 |
| 매수 | NBIS | 170.19 | 168.49~171.89 | 341 | 10.87 | 3.90 | 0 |
| 매수 | DELL | 455.1047 (아님) | 450.55~459.66 | 912 | 13.28 | 4.05 | 0 |
| 매수 | SOXL | 98.675 (아님) | 97.69~99.66 | 198 | 11.20 | 4.19 | 0 |
| 매수 | PWR | 618.30 | 612.12~624.48 | 1237 | 12.99 | 4.01 | 0 |
| 매수 | LITE | 834.545 (아님) | 826.20~842.89 | 1670 | 12.14 | 4.04 | 0 |
| 매도 | MVLL | 27.99 | 27.71~28.27 | 57 | 9.16 | 3.72 | 0 |
| 매도 | NBIS | 170.19 | 168.49~171.89 | 341 | 13.16 | 4.15 | 0 |
| 매도 | SOXL | 98.675 (아님) | 97.69~99.66 | 198 | 10.09 | 4.00 | 0 |

  모든 센트 결과는 NO_TICKET:CIRCUIT_CLOSED(그날 회로 닫힘), 예외 0.
- **R3 시간 예산**(사용자 PC Windows): 최악값 = Σ(센트 수 × 센트당 최대 ms) = **92.1초 ≤ 120초**, 주문표 1장 최악 = MU 1812 × 13.72 ms = **24.9초 ≤ 30초** → 멈추지 않음.
  보정: 실데이터에서는 회로가 닫혀 주문표 만들기(_buy_ticket·후회표) 비용이 빠졌다. 합성 MU 주문표에서 그 몫은 센트당 중앙값 약 0.26 ms(hold_eval 1.82 → 전체 2.08 ms)였다.
  이를 더해도 MU 약 25.3초, 합계 약 94초로 예산 안. 실제 평균(중앙값 약 4 ms)으로는 MU 주문표 1장 약 7~8초, 리플레이 R2 전체는 off 7.1초·on 7.8초.

# 5. 남는 한계 (코드 위치)

1. **S7 고정**: S7 검토는 근사 종가로 한 번 계산한다 — auto_core_decide.py 1000행 `review = s7_runner(proposals)`, 1065~1066행 equity·weights, hold_eval(1101~1128)은 review·s7·equity·weights·
   proposal_results를 그대로 둔다. 노출 E·멈춤(pauses)·목표 비중 제안 평가·자산·비중·고점 검토는 b에서 다시 구하지 않는다.
2. **다른 종목·교체 후보 고정**: plan()이 redeploy_candidate를 한 번 정한다(auto_core_tickets.py 735~739행), _sell_ticket이 그것을 쓴다(1081행). hold_eval은 다른 종목 값을 그대로 둔다.
   그 종목이 R-REC1 벤치마크(SOXX)나 RG2 벤치마크(GRID)라면 전체 경로에서는 다른 종목의 R-REC1 행·교체 후보 순위도 바뀌지만 스캔은 그 종목 자신의 행만 다시 구한다(shock_of에 b의 series map을 넘기므로
   그 종목 자신의 행은 정확). SOXX·GRID는 승인 매수 상품이 아니다(APPROVED_BUY, auto_core_tickets.py 61행) — 이 한계는 둘 중 하나를 보유해 매도 주문표가 날 때만 생긴다(실제 보유 여부는 이 작업에서 확인하지 않음).
3. **화면 환산 배수 mult**: loc_price(376~392)가 근사 종가의 σ60으로 정한 mult를 쓴다 — _hold_break(861~880)의 p_b = b × priceCalc.mult. order-instruction-design 9-1 2-2의 "남는 위험" 그대로.
4. **E4의 전제(제안 목록)**: decide는 S7에 --cards를 넘기지 않으므로(run_s7 258~274행) S7 add 추천은 보충 ETF뿐이다(portfolio_exposure.py 1426~1427행 `card_adds or [supplement]`).
   그래서 매수 회로가 열림 ⇔ 그 종목 제안 대상(보충 ETF는 basis_met)이 성립한다. 카드 ADD가 S7에 들어가는 구성이 생기면 그 종목은 b에서 new_basis_met이 꺼져도 ref의 제안 평가로 회로가 열릴 수 있다(지금 decide 경로에는 없음).
5. **센트 사이 입력**: 양쪽 센트가 유지면 그 사이 키움 기준종가도 유지로 본다. 키움 기준종가의 소수 자릿수는 확인 필요(지시문 그대로).
6. **매도 뒤 예상(after_sale)**: b에서 다시 구하지 않는다(model_for None, 표시 전용) — 자기 점검에서도 뺀다(HOLD_SELF_CHECK_SKIP).
7. **장수 상한**: hold는 _limit_daily(장수 상한, 지금 꺼짐) 뒤에 붙으므로 HOLD_RANGE_UNVERIFIED로 빠진 매수 자리를 다른 주문표가 채우지 않는다(지시문 A-3).
8. **계산기 누수**: HOLD_RANGE_UNVERIFIED로 매수가 빠진 날은 t2rc-oracle이 ticket_leaks → MISMATCH로 센다(사전 등록 24행 CORE_BUG, 48행 C3 불산입) — 바꾸지 않았다.
9. **시간**: R3는 2026-10-19 자료(139세션)·이 PC 기준. 고가 종목이 늘거나 이력이 길어지면 주문표당 시간이 늘어난다(구간 계산은 그 종목만 다시 하므로 센트 수 × 약 4 ms).

# 6. 바뀐 파일 sha256 (작업 트리 바이트, 모두 CRLF)

| 파일 | sha256 (작업 트리 바이트) | LF 정규화 앞 12자리 | 줄 / CRLF |
|---|---|---|---|
| manage-us-stock-strategy/scripts/auto_core_tickets.py | 8fe20bf3a0e606f5cc318486b02b6cd57b9c11e6ece6aec22b7c35bfe41a5b54 | 71b11066a2e0 | 1304 / 1304 |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 0d09ba0e690d8063110343258fe091c59285005c5d33afdb57fe47cd83aee089 | 41f1946ecccf | 1274 / 1274 |
| manage-us-stock-strategy/schemas/auto-core-ticket.schema.json | 68a11bf7da1939b01c047b1ffcffc0183da8ae2a2283b1374e4f290c33fdce60 | 3d1a26f96971 | 144 / 144 |
| manage-us-stock-strategy/references/auto-core-decision.md | 00ea53c0504746301faf72b15f168ce4f96c7eba1f222fb3811ab58d12e77643 | 2c2d9b0599af | 218 / 218 |
| manage-us-stock-strategy/tests/test_auto_core_hold_range.py (새 파일) | 2b81f4464ab995c2c7a08726b13091c7913244321b56981e3457052a603c5aff | 6868348aa734 | 757 / 757 |
| manage-us-stock-strategy/tests/test_auto_core_risk1r.py | b7ca38b726cc7d3286ec17f742c8790a7fd656cc1bdff2fb5fc35bf1afcf5b3b | 59f10a0e6300 | 392 / 392 |
| manage-us-stock-strategy/tests/test_auto_core_enter_window.py | 7f4eac19dc0846f73ddf163de73821935cf10b9764e88b41d450bf72c42123f4 | 658e56aa2a08 | 229 / 229 |

- 기존 파일은 모두 체크아웃된 CRLF 그대로(bare LF 0). 스크립트 2개는 비 ASCII 바이트 0. 새 테스트 파일도 ASCII·CRLF(다른 작업 트리 파일과 같게 이 세션이 쓴 새 파일만 CRLF로 저장).
  이 보고서 자체는 위 표에 넣지 않았다(자기 해시).
- docs/claude/t2rc-oracle.py LF 정규화 sha256 앞 12자리 = 6a74f813c918 (사전 등록 고정값과 **같음**), 작업 트리 바이트 d79b12212ee2(base와 같음).
- auto_core_replay.py 바꾸지 않음(d346ba92f783 / 088a0f30ba20 그대로).

# 7. 멈춤·범위 문제

범위 문제 없음(R3 예산 안, 골든은 허용된 원인으로만 바뀜, E1~E7 충족, 허용 밖 파일 변경 없음). **실행 문제 1건**:
- 변경 뒤 전체 스위트 실행과, 마지막 E4 테스트를 더한 뒤의 대상 집합 재실행이 Claude Code에 의해 **시스템 메모리 부족**으로 중단됐다(백그라운드 작업 정리; 명령 자체의 실패 아님).
  안내에 따라 스스로 다시 돌리지 않았다. 남은 확인: 메모리 여유가 있을 때 아래 두 명령을 다시 돌려 기준선(전체 3247/실패 30, 대상 460/실패 1 PLTR)과 비교 —
  `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`(기대 Ran 488 · PLTR 1건),
  `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests`(기대 Ran 3275 · 기준선 30건 그대로). 그 전까지 전체 스위트 새 실패 0은 확인 필요.
참고로 적어 둔다: ① risk1r 주석 1줄은 지시문이 준 한국어 문구 그대로라 비 ASCII다(스크립트 scripts/와 새 테스트 파일은 ASCII). ② 새 테스트 파일 실행 약 70초(실가격대 시나리오에서 band 전체 센트 E4 대조) —
낮은 가격대로 줄이는 것은 하지 않았다.

# 8. 화면이 쓸 값 요약 (통합점검 calcBox — 병합 뒤 Cowork 작업용)

| 필드 | 값 | 화면에서 |
|---|---|---|
| priceCalc.lo / hi | 매수: hold.lo / hold.hi (ok일 때만 주문표가 있음) · 매도: band.lo / band.hi | 지금 calcBox 그대로 lo~hi 밖이면 "범위 밖" — 병합만으로 매수는 유지 구간 밖에서 막힘 |
| priceCalc.band {lo, hi} | 근사 종가 ±1%(옛 lo/hi와 같은 값) | 규칙 줄에 band 표기, b가 band 안·hold 밖인지 가르는 기준 |
| priceCalc.hold.status | `ok` · `unverified` | 매도 unverified → "판정 유지 구간 확인 필요" 경고(매수 unverified는 주문표 자체가 없음) |
| hold.lo / hold.hi | 숫자(센트, 또는 첫 센트가 바로 깨진 쪽은 센트 사이 ref 값) · unverified면 null | 매수 b가 band 안·hold 밖 → "판정 유지 구간 밖(<사유>) — 오늘 입력하지 않음 · 다음 아침 재판정", 매도 → 가격 보이고 경고 줄 |
| hold.lo_limit / hi_limit | 아래 사유 코드 · unverified면 null | <사유> 자리에 표시 |
| hold.checked | 계산한 센트 수(자기 점검 포함) | 표시 안 해도 됨(점검용) |
| hold.reason | ok면 null · unverified면 `SELF_CHECK_MISMATCH` · `EVAL_ERROR:<예외 이름>` · `DATA` | 확인 필요 문구 옆 사유 |
| hold.basis | `SYMBOL_CLOSE_ONLY:S7_FIXED` | "그 종목 종가만 바뀐다고 보고 S7은 고정" 주석 |
| blocked 사유 | `HOLD_RANGE_UNVERIFIED`(매수만, 주문표 없음; 허용 사유 아님 = 이상 신호) | gate-rule-epochs.json `GATE:HOLD_RANGE_UNVERIFIED` 1줄(병합 뒤 Cowork, 지시문 4-②) |

limit 사유 코드:

| 코드 | 뜻 | 방향 |
|---|---|---|
| `BAND` | band 끝까지 유지 | 매수·매도 |
| `NO_TICKET:<사유>` | 그 b에서 그 종목·방향 주문표가 안 나옴. <사유> = 그 b의 첫 막힘 사유(예 `REQ5_RREC1:no`, `REQ2_EXPOSURE_CASH_PRODUCT:no`, `LOT_ZERO`, `CASH_ZERO`, `DEADBAND`, `G2:…`), 회로가 안 열리면 `CIRCUIT_CLOSED` | 매수·매도 |
| `STEP_DOWN` | 그 b의 단계 r이 주문표 r보다 낮음(덜 사거나 덜 팖) | 매수·매도 |
| `CASH` | 주문표 수량이 b × mult(센트 내림)에서 G4(현금 × 0.25% 여유) 통과 못 함 | 매수 |
| `G2B` | max_buy_ticket_pct_of_equity가 있을 때 금액 상한 통과 못 함(지금 키 없음 → 안 나옴) | 매수 |
| `DATA` | 그 b의 봉·지표를 만들 수 없거나 계산 예외 | 매수·매도 |
