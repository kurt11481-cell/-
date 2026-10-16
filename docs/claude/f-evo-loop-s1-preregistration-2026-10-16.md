---
id: f-evo-loop-s1-preregistration-2026-10-16
type: 설계 + 사전 등록 (진화 루프 1단계 EVOLUTION_1, 표시 전용 D — 규칙 후보 아님, 계산 전 고정)
status: 고정 2026-10-16T15:21+09:00(Cowork, 결과 계산 전 · 내장 재검토 2회 반영 뒤). 해시는 같은 이름 .sha256. 고정 뒤 이 문서를 고친 결과는 이 사전 등록의 결과가 아니다(기준을 바꾸려면 새 사전 등록)
as_of: 2026-10-16
decision: 사용자 "결정 learn-loop: a"(2026-10-15 11:00 KST, cpi-shock-review-2026-10-15.md 211행 원문·213행 기록) — 4-3 REUSE 4개를 결과 보기 전에 설계·사전 등록하고 일반 변경 1건으로 만든다. 이번 요청(2026-10-16 14:29 KST "f-evo-loop 진행")이 fx1009-closing-2026-10-16.md 116행의 "별도 요청"이다
basis: cpi-shock-review-2026-10-15.md 4-2·4-3(164~188행) · future-tools-roadmap-2026-10-05.md §4(128~135행) · 관제판 f-evo-loop(v6) · external-phil-repo-review-2026-10-13.md 55행 · order-instruction-design-2026-10-06.md 132행 · 헌법 §11·§15·§16·§17·§22·§24·§25
consumers: 개발 작업 evo-s1(docs/claude/evo-s1-builder-prompt.md) · 주간 채점 보고서 learning 블록(workspace/outputs/journal-scores/<시각>/journal-scores.json) · Cowork 카드·M6·평가 세션("직전 결정 결과" + Failure Museum 칸) · f-evo-loop 2단계(발견 → 제안) · 다음 R-REC1·매도 하한·트리거 리플레이 사전 등록의 입력 · 관제판 f-evo-loop
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 호출 없음
default: 표본 부족·기준 미달·무응답 = NO_CHANGE(규칙·정책·상태·권한 그대로, 표시만). 발견은 아무것도 바꾸지 않는다
weekly_user_touch: 0 (일회성: 병합 1번 + Windows 작업 등록 1번, 같은 자리에서)
---

# 진화 루프 1단계 — 지난 판단 성적에서 규칙 약점 찾기: 설계·사전 등록

## 0. 결론

1. **결정론 채점기(`score_decision_journal.py`)에 `--learning` 선택 블록을 더한다.** 기본 실행(코어가 부르는 길, `auto_core_decide.py` 1157~1160행)은 그대로다. 넣는 것:
   - ① 관문별 소급 채점: 구속 여부와 함께, R-REC1은 충격 구간(shock.open이 이어지는 동안, C0 목록 표시) 안의 20세션 묶음 단위로
   - ② 감축 매도 미체결 반사실: 하한 없이 팔았다면
   - ③ 사전 부검·사전 축하 판정
     - 코어 주문표는 이미 있는 시나리오 대역(5세션 90/10 분위)으로 자동 판정한다.
     - 옛 지시서 4건은 코드 없이 11/7 이후 Cowork가 1회 판정한다. 규칙은 11절에 지금 고정한다.
   - ④ 주 1회 자동 실행: 새 Windows 작업 `InvestmentV2-JournalScore`(일요일 09:20 KST)
   - 트리거 종류별 성적(로드맵 §4의 원래 발견 단위), Failure Museum 칸, 규칙 시기(epoch) 구분
2. **모두 등급 D(반사실), 표시 전용이다.**
   - 결론은 버킷마다 독립 단위 30건부터 낸다(`MIN_SCORED_FOR_CONCLUSION`, 70행).
   - 발견은 다음을 모두 만족할 때만 낸다.
     - 같은 규칙 시기 안에서 30건 이상
     - 평균·중앙값·앞 반쪽·뒤 반쪽이 모두 같은 부호
     - 채점 불가 10% 이하
   - 발견은 다음 사전 등록 리플레이의 입력일 뿐이다.
3. **decision.json 보존은 확인됐다.**
   - 10/13~10/16 4개가 있고, 지우는 코드가 없다.
   - 다만 git 밖, PC 한 곳에만 있다. 비교 모드에서는 같은 날 재실행이 파일을 덮어쓴다.
   - 그래서 보고서가 날짜별 처음 본 sha256을 계속 넘겨 적는다. 바뀌거나 사라지면 계속 보이게 한다.
4. **지금 계산된 결과는 없다.** 가장 이른 5세션 값은 10/20 종가(10/13 시작 단위) 뒤에 나온다.
   - 지금 있는 단위:
     - R-REC1 구속: DELL·MU(10/16), R-REC1 묶음 1개(충격 구간 안)
     - NBIS 매도 근거 충족·매도 경로 없음
     - "새 근거 아님 + R-REC1" 겹침 여러 개
   - 주문표가 0건이라 ②·③·트리거 표본은 0이다.
   - 관문·근거 규칙이 이 4일 동안 3번 바뀌었다(10/14·10/15·10/16 시작분, 3-6). 그래서 같은 시기 표본은 더 느리게 쌓인다.
5. **개발 작업 evo-s1**(일반 변경, 개발 파이프라인)을 대기열에 넣는다.
   - 사용자 손: 병합 `.\tools\dev-merge.ps1 evo-s1`과 등록 `register_journal_score_task.ps1` 각 1번(같은 자리).
   - 병합 뒤 첫 예약 실행 전에 Cowork가 실제 자료로 읽기 전용 1회 실행을 확인한다.
   - 그 전까지는 Cowork가 지금처럼 수동으로 실행한다.

## 1. 결과 보기 전 확인 (2026-10-16 14:3x~15:3x KST, 이번 세션에서 연 원문)

| 항목 | 값 | 원문 |
|---|---|---|
| decision.json | 10/13·10/14·10/15·10/16 4개. sha256 앞 12자리: cd5c7b69df47 · 441e3f71a106 · 580408b3eaa7 · bf4ad05504dc. commit_sha: 73e18b4 · 4051391 · cf2c86c · ad12759. 10/13은 status HOLD(`G1_S7_FAIL_CLOSED`) | workspace/outputs/auto-core/<날짜>/decision.json |
| 보존 | auto_core*.py·run_auto_core.ps1에 지우는 코드가 없다(collect_30m.ps1 62행은 불량 키움 페이지만 지움). git 무시(.gitignore 157행). 같은 날 재실행 별도 파일(decision.rerun-*)은 기록 모드에서만 생긴다(auto_core_decide.py 22·815~827행) | grep·원문 |
| 쓰기 방식 | `write_json`은 원자적 쓰기가 아니다(validation_common.py 29~32행) | 원문 |
| 주문표 | 4일 모두 tickets 0 | decision.json `tickets` |
| 막힘·충격 | shock.open 4일 모두 true. 마지막 사건(shock.event)은 10/8 → 10/8 → 10/14 → 10/15로 바뀌었다. 10/16 DELL·MU 매수는 `REQ5_RREC1:no` 하나. 10/13은 REQ5 칸이 모두 unk | decision.json `blocked`·`shock`·`buy_requirements` |
| S7 감축 항목 | 4일 모두 없음 | 각 날 s7/…/portfolio-exposure-review.*.json `recommendations.reduce` |
| 일지 | 6건(card_decision 3 · card_user_decision 2 · s5_activation 1) | stock-strategy-system/decision_journal.json |
| 채점 보고서 | 20261004T225915Z · 20261015T005156Z. 20261015는 5세션만 3건 SCORED. 달력 범위 2026-01-01~2026-12-31 | workspace/outputs/journal-scores |
| 이미 본 가격 | 10/15 종가까지(예: SOXL 107.34·NBIS 188.46, decision 10/16 exposure.peaks). cpi-shock D3의 NBIS 10/13→10/14 1세션 반사실(약 −$271) | |

- 이 문서의 지표(①·트리거 5·20·60세션, ② 1·5·20세션, ③ 5세션)는 아직 하나도 계산되지 않았다.
- 단위 모양은 위 4개 파일로 시험했다(셈만, 수익률 계산 없음).
  - 10/13(계획 뒤 HOLD): BE·DELL·LITE·MU·PWR는 {새 근거 아님, REQ2, REQ5_UNK, G1_S7_FAIL_CLOSED} 겹침. NBIS는 {매도 경로 없음, G1_S7_FAIL_CLOSED} 겹침.
  - 10/14·10/15: 같은 5종목이 "새 근거 아님 + REQ5" 겹침. NBIS 매도 경로 없음은 구속.
  - 10/16: DELL·MU는 REQ5 구속. BE·LITE·NBIS·PWR는 "새 근거 아님 + REQ5" 겹침. SOXL은 REQ2가 더해진다. NBIS 매도 경로 없음은 구속.

## 2. 검토 순서 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)

| 순서 | 판단 | 근거 |
|---|---|---|
| NO_CHANGE | 기각. T2 기록 모드가 켜지면 채점기는 매일 돌지만, 관문·하한·대역 칸은 없다. T2 "켜" 시점도 미정이다 | auto_core_decide.py 1157~1160행 · cpi-shock 4-3 |
| REMOVE/SIMPLIFY | ③을 줄인다. 지시서식 사전 부검 칸을 코어에 새로 만들지 않고, 코어 주문표가 이미 계산하는 시나리오 대역(후회표의 상·하 시나리오)을 판정 기준으로 쓴다. 옛 지시서 4건은 코드 없이 1회 판정한다 | auto_core_tickets.py 292~301·308~350행 · cpi-shock 182행 |
| REUSE | 채점기의 종가·달력·분할·상태 규칙(`_score_horizon` 169행~), 주문표 읽기(`load_compare_tickets` 792행~), 출력 보호(`check_output_root` 744행~), 30건 기준(70행)을 쓴다. 실행 틀은 `register_host_status_task.ps1`·`run_auto_core.ps1`과 같은 방식이다 | score_decision_journal.py · manage-us-stock-strategy/scripts |
| REPLACE | 없음 | — |
| ADD | `--learning` 선택 블록 1개, Windows 작업 1개, `docs/claude/failure-museum.json`·`docs/claude/gate-rule-epochs.json` 각 1개. 기본 출력·코어 호출은 바뀌지 않는다 | 8절 |

## 3. 지표 정의 (계산 전 고정)

### 3-0. 공통

- 등급 D(`COUNTERFACTUAL_D`), 표시 전용이다.
- 종가 규칙은 채점기 그대로다.
  - 키움 30분봉 근사 정규장 종가, 분할 반영.
  - 미검증이면 REFERENCE_ONLY.
  - 실패는 상태다(PENDING / NOT_SCORABLE).
  - 시작 세션이 없거나 달력 밖이면 NOT_SCORABLE(`START_SESSION_NOT_IN_CALENDAR`)이다.
- 값 부호:
  - **cf_value > 0 = "막은(하지 않은) 행동이 더 나았다" = 관문·하한의 비용.** cf_value < 0 = 막은 것이 도움.
  - 매수 = 주가 수익률, 매도 = −주가 수익률(`_score_horizon`의 vs_cash와 같음).
  - 경로 최저·최고(`path_20`)는 부호를 바꾸지 않은 주가 수익률이다.
- 시작점: 그 결정 파일의 `buy_session` 종가. 그날 주문표가 나왔다면 쓰였을 종가다. 그 뒤 종가만 쓴다.
- 자격 있는 날:
  - `status`가 OK 또는 HOLD이고, **계획이 돌았음**: evaluation_session·buy_session이 null이 아니고 `symbols`·`buy_requirements`가 비어 있지 않다.
    - HOLD는 두 갈래다. 계획 전 HOLD(KILL_SWITCH_ON, T1_RESULT_MISSING/T1_NOT_OK, auto_core_decide.py 511~513·523~527행)는 빈 결정 틀(545~556행)이다. 이런 날은 `PLAN_NOT_RUN`으로 두고, 자격 없는 날처럼 잇지도 끊지도 않는다. 계획 뒤 HOLD(G0/G1 사유, 777~780행)는 자격이 있다.
    - 계획 뒤 HOLD 날에는 그 사유 앞부분(`decision.reasons`의 첫 ":" 앞)을 그날 모든 단위의 관문에 더한다.
  - `no_new_session` false, `carried_from` null.
  - 형식이 맞음: `buy_requirements` 행마다 칸 6개, 필수 키(`blocked`·`candidates`·`buy_requirements`·`evidence`·`symbols`·`shock`·`buy_session`)가 있음. 아니면 `DECISION_SHAPE_UNKNOWN`.
  - 같은 evaluation_session이 두 번이면 늦은 run_day만 쓴다.
  - FAIL과 나머지는 목록에 사유와 함께 남기고 채점하지 않는다.
- 보존:
  - 보고서는 날짜별 `first_sha256`·`first_generated_at`·`first_evaluation_session`·`first_buy_session`·표지를 직전 learning 보고서에서 이어받는다. 읽지 못한 파일의 sha는 처음 값으로 적지 않는다.
  - 그 주에 결정 폴더를 읽지 못했거나 decision.json을 하나도 못 읽었으면(직전에는 있었는데) 표지를 바꾸지 않고 `DECISIONS_ROOT_UNREADABLE`만 표시한다. 일시 장애로 과거 전체가 자격을 잃지 않게 하려는 것이다.
  - 판정:
    - sha가 처음과 같음 → OK
    - sha가 다르고, 새 generated_at의 KST 날짜 = 그 날 폴더 날짜(run_day)이며 evaluation_session·buy_session이 처음과 같음 → `REWRITTEN`(같은 날 정상 재실행 덮어쓰기). 자격은 유지하고, 한 번 붙으면 남는다.
    - 그 밖에 sha가 다름 → `PRESERVATION_BROKEN`. 한 번 붙으면 남고, 자격을 잃는다.
    - 전에 있던 파일이 없음 → `MISSING_NOW`. 그 주만 자격을 잃는다. 다시 나타나서 sha가 처음과 같으면 OK로 돌아가고 이력만 남는다. 다르면 `PRESERVATION_BROKEN`이다.
- 독립 단위 간격:
  - 같은 키의 다음 단위는 직전에 센 단위의 시작 세션에서 주 판정 세션 수 이상 떨어져야 센다(`unit: true`).
  - 나머지는 `unit: false`로 표시만 한다.
- 결론 허용: 버킷마다 채점된 독립 단위 ≥ 30. 미만이면 "판단 보류"만 표시한다.

### 3-1. ① 관문별 소급 채점

**단위는 자격 있는 날마다 만든다.** 읽는 것은 decision.json과 그 파일 `inputs.s7_review.path`의 S7 검토 파일뿐이다. S7 경로는 저장소 기준이고, `workspace/outputs/auto-core/` 접두어를 떼고 결정 폴더 아래로 해석한다. 결정 폴더 밖이면 `S7_PATH_OUTSIDE`다.

**관문 이름:**
- `REQ1_EARNINGS`·`REQ2_EXPOSURE_CASH_PRODUCT`·`REQ3_EVIDENCE`·`REQ4_M6`·`REQ5_RREC1`은 `buy_requirements` 앞 5칸 순서다(auto_core_tickets.py 916행).
- 칸 상태 표기:
  - `unk`(자료 없음)면 이름 뒤에 `_UNK`를 붙인다. `REQ5_RREC1`(no)과 `REQ5_RREC1_UNK`는 다른 관문이다.
  - REQ1 칸 글에 `RESEARCH_RECORD_NOT_OK`가 있으면(지수 ETF, 221~222행) REQ1이 아니라 `RESEARCH_RECORD_NOT_OK`로 센다.
- `blocked` 사유는 첫 ":" 앞부분을 쓴다. 단 `REQx_…:unk`는 `REQx_…_UNK`로, 같은 원인의 REQ1은 위 규칙대로 바꾼다.

**매수:** `symbols[S].buy_approved = true`인 종목만 본다(매도 전용 MVLL 제외). `evidence[S].buy.basis_met = true`일 때만 단위가 된다. 근거가 없으면 매매도 없으므로 관문이 아니다.
- 회로가 안 열린 경우(매수 후보에 없음), 관문 집합은 다음의 합이다.
  - `CIRCUIT_NEW_EVIDENCE`: 근거는 있지만 새 근거가 아니고, S7 추가 권고도 없다(750행).
  - REQ1~REQ5 중 `ok`가 아닌 칸.
  - 연구 기록이 OK가 아니면 `RESEARCH_RECORD_NOT_OK`.
  - `symbols[S].status`가 OK가 아니거나 `indicators.sigma60`이 없으면 `G1_SYMBOL_DATA`.
- 회로가 열렸는데 주문표가 없는 경우: 그 종목 `blocked` 사유 집합이다.

**매도:** `role = held`인 종목만 본다.
- 매도 후보인데 주문표 없음 → `blocked` 사유 집합.
- 후보가 아니고 카드 TRIM 수량 누락(`blocked`에 `CARD_TRIM_SIZE_MISSING`)이 있는 경우:
  - 매도 근거 있음 → `{CARD_TRIM_SIZE_MISSING}`
  - 근거 없음 → `{CARD_TRIM_SIZE_MISSING, CIRCUIT_SELL_NO_EVIDENCE}`(733~737행: 이 사유는 근거를 보기 전에 붙는다)
- 그 밖에 후보가 아니고 매도 근거 충족 → `{CIRCUIT_SELL_NO_GAP}`. 감축 항목도 카드 TRIM/EXIT 목표도 없는 경우다(cpi-shock D3 유형).
- 그 밖에 그날 S7 `recommendations.reduce`에 있고 근거 미충족 → `{CIRCUIT_SELL_NO_EVIDENCE}`(D1 유형).
  - S7 파일을 못 읽으면 이 판정만 NOT_SCORABLE이다. NO_GAP 판정은 S7이 필요 없다.

**구속(binding):** 관문 집합의 원소가 하나뿐인 경우다.
- 범위는 `binding_scope = "EVALUATED_GATES_ONLY"`로 적는다.
- 후보가 아닌 종목은 카드 점검 사유·정책 미등록·G2(S7 목표)를 decision.json에서 볼 수 없다. 코어는 첫 막힘 뒤의 검사(가격·σ·후회·수량)를 돌리지 않는다. 그래서 구속은 상한 추정이다.

**구간(episode):** 같은 (종목, 방향, 관문 집합, R-REC1이면 충격 구간)이 자격 있는 날마다 이어지는 동안 하나로 센다.
- 자격 없는 날은 잇지도 끊지도 않는다. 자격 있는 날에 빠지면 끊는다.
- 값은 첫날 buy_session 종가에서 5·20·60세션이다. 보조 표시는 `path_20`이다.
- 독립 단위: 같은 (종목, 방향, 관문 집합) 키로 간격 20세션 규칙을 쓴다(3-0).

**충격 구간(R-REC1):**
- 정의: 자격 있는 날들 가운데 `shock.open = true`가 이어지는 동안 하나다.
  - 자격 없는 날과 `shock.open`이 true도 false도 아닌 날(값 없음)은 건너뛴다. open false인 날이 오면 끝난다.
  - 구간 id = 첫날 evaluation_session이다. 그 안에서 본 `shock.event.date`·C0 목록을 표시한다.
  - 이유: 마지막 사건일은 날마다 바뀐다(1절). 사건일로 나누면 한 충격이 여러 개로 세진다.
- 그날 `shock.open`이 true가 아니면 단위의 R-REC1 키는 다음과 같다. 셋 다 R-REC1 발견에는 쓰지 않고 표시만 한다.
  - 종목만 `shock.by_symbol[S].open`이 true(종목 자체 사건 EV5 등) → `SYMBOL_ONLY`
  - 값이 없음 → `UNKNOWN`
  - 둘 다 아님 → `NONE`
- **R-REC1 독립 단위(묶음):** 한 충격 구간 안에서 `{REQ5_RREC1}` 구속 구간들을 시작 세션 순으로 본다.
  - 묶음은 첫 구간의 시작에서 열린다. 시작이 그보다 20세션 안이고 규칙 시기(3-6)가 같은 구간이 같은 묶음에 든다. 그 밖은 새 묶음을 연다.
  - 충격 구간은 창(`RREC_WINDOW_SESSIONS` 60, auto_core_rules.py 53행) 때문에 수개월 이어질 수 있다. 그래서 구간 하나를 단위 하나로 세지 않는다.
  - 묶음 값 = 묶음 안 구간들의 같은 세션 cf_value 단순 평균이다(SCORED만).
  - 묶음은 서로 20세션 이상 떨어지므로 간격 규칙을 저절로 만족한다.
- `{REQ5_RREC1_UNK}` 구속 구간(자료 없음으로 막힘)은 같은 방식으로 따로 묶고 표시만 한다.

**버킷:** (방향, 관문, 규칙 시기)의 구속·unit 구간. R-REC1은 묶음을 쓴다. 겹침 구간은 관문 집합별로 n과 평균만 표시하고 발견에는 쓰지 않는다. 반사실이 관문 여러 개를 함께 빼야 하기 때문이다.

### 3-2. ② 감축 매도 미체결 반사실

- 대상: 매도 주문표(일지 order_ticket과 비교 모드 주문표) 중 다음 둘.
  - 가상 체결 안 됨: 주문표 세션 원 종가 < 하한(`would_fill` false)
  - 기록 모드 사용자 결과 `unfilled`
- 독립 단위:
  - decision_key별 첫 미체결 1건(재발행은 같은 결정).
  - 같은 종목의 다음 단위는 간격 5세션.
- 값: 주문표 세션 종가에 하한 없이 팔았다면(MOC) 대 안 팔림. 1·5·20세션 cf_value = −r이다. **주 판정은 5세션**이다.
- 지연:
  - 같은 종목 매도 주문표가 다음 5세션 안에 가상 체결되면, 첫 체결 세션의 지연값 = −(C체결 / C원래 − 1)이다. 양수면 하한 때문에 더 낮게 판 것이다.
  - 없으면 `NO_LATER_FILL_WITHIN_5`.
- 일지·decision.json 밖의 10/8 SOXL-1 사례(지시서 경로)는 넣지 않는다. cpi-shock D2 서술로만 남는다.

### 3-3. ③ 사전 부검·사전 축하 판정

**③-b (코드, 앞으로 모든 주문표)**
- 대역:
  - 그 주문표를 낸 decision의 evaluation_session(주문표 세션 바로 앞 달력 세션)에서 끝나는 **연속 구간**의 수정 종가를 쓴다. 코어 `rules.build_series`처럼 달력에서 빈 세션이 있으면 그 뒤부터다(auto_core_rules.py 221~235행).
  - 그 마지막 65개로 5세션 수익률 60개를 만들고 90/10 분위(선형 보간)를 낸다.
  - 코어 `auto_core_tickets.scenarios`와 같은 식이다(상수 43~46행, auto_core_decide.py 1001~1004·1102행). 채점기 안에 같은 식을 두고, 같은 값인지는 테스트로만 확인한다(실행 중 코어를 부르지 않음).
  - 65개 미만이면 `SCENARIO_HISTORY_SHORT`.
- 실현 = 주문표 세션 종가 → 5세션 뒤 종가 수익률 r5. 판정:

| 판정 | 조건 |
|---|---|
| `UP_TAIL` | r5 ≥ 상단 |
| `DOWN_TAIL` | r5 ≤ 하단 |
| `INSIDE` | 그 사이 |

- 매수의 사전 부검 경로는 DOWN_TAIL, 사전 축하 경로는 UP_TAIL이다. 매도는 반대다.
- 독립 단위: decision_key별 첫 주문표. 같은 (종목, 방향)은 간격 5세션. 대역이 맞으면 기대 비율은 각 약 10%다.

**③-a (코드 없음, 1회):** 옛 지시서 4건. 11절 규칙으로 2026-11-07(KST) 아침 코어 종가 수집 뒤 Cowork가 한 번 판정한다.

### 3-4. 트리거 종류별 성적 (로드맵 §4 "같은 트리거 유형이 N건 이상 일관되게 틀릴 때")

- 대상: 주문표 행(일지·비교 모드). 채점기 `ticket_results[].evidence_weak_kinds`(일지 = `evidence_weak_kinds`, 비교 모드 = `evidence.weak`에서 옴, score_decision_journal.py 316~346행)의 종류마다 버킷을 만든다.
  - 빈 목록이면 `NO_WEAK_KIND`, 값이 없으면 `WEAK_KINDS_NOT_RECORDED`(발견 없음).
- 한 주문표는 자기 종류마다 한 번씩 센다. 겹침 수를 표시한다.
- 값: 체결과 무관한 방향 부호 수익률. 주문표 세션 종가에서 20세션이 주 판정이고, 5·60은 표시만 한다. 신호 자체의 성적을 본다.
- 독립 단위: decision_key별 첫 주문표. 같은 (종목, 방향, 종류)는 간격 20세션.

### 3-5. Failure Museum 칸 (헌법 §11 "Which assumption failed?", §16, 로드맵 I2)

**후보:** 채점기가 결정론으로 낸다. 20세션 SCORED인 것 중 다음 셋이다.

| 후보 id | 조건 |
|---|---|
| `RESULT:<decision_id>:<ANALYSIS\|USER>:h20` | 카드·사용자 결정 결과(`results`)의 vs_cash < 0 |
| `TICKET:<ticket_id>:USER:h20` | 기록 모드 사용자 체결(filled/partial)의 vs_no_action < 0 |
| `TICKET:<ticket_id>:HYPOTHETICAL:h20` | 비교 모드 가상 체결(`would_fill` true)의 vs_no_action < 0. D로 표시 |

**대조 목록:** 같은 종류의 20세션 양수 결과 id를 표시만 한다. 결과 편향을 줄이려는 것이다. "이긴 결정에도 같은 가정이 있었나"를 볼 수 있게 한다.

**칸:** Cowork가 `docs/claude/failure-museum.json`의 `entries`에 쓴다.

| 필드 | 필수 | 내용 |
|---|---|---|
| `candidate_id` | 예 | 위 후보 id |
| `failed_assumption` | 예 | 한 줄. 어느 가정이 틀렸나 |
| `category` | 예 | THESIS · EVIDENCE · TIMING · SIZE · DATA · RULE · TAIL_EVENT · NONE 중 하나. 가정은 맞았고 결과만 꼬리였으면 TAIL_EVENT, 운이면 NONE |
| `evidence` | 예 | 원문 위치·조회 시각 1개 이상(빈 목록 불가) |
| `written_by`·`written_at` | 예 | 쓴 세션·시각 |
| `feasible_note` | 아니오 | 그때 가능했던 선택만 비교(헌법 §17) |
| `grade` | 아니오 | 기본 "D" |

- 추가만 한다. 고칠 때는 같은 candidate_id로 뒤에 새 항목을 쓰고, 뒤 항목이 이긴다.

**채점기:** 다음을 표시만 한다. 빈 칸은 아무것도 막지 않는다.
- `museum.status`(OK / MISSING / INVALID)
- `candidates`·`control`·`filled`·`pending`

**누가 언제:** Cowork가 이미 하고 있는 카드·M6·평가 세션에서 "직전 결정 결과"를 볼 때 pending을 채운다(analysis-linkage-map 53행). 사용자 손은 늘지 않는다. 결과를 보고 일지(원장)를 고치지 않는다.

### 3-6. 규칙 시기(epoch)

- 관문·근거 규칙이 바뀌면, 그 전과 뒤의 단위를 한 버킷에 섞지 않는다. 섞으면 서로 다른 규칙의 성적이 합쳐진다.
- `docs/claude/gate-rule-epochs.json`의 항목 `{scope, first_run_day, commit, note}`:
  - scope는 `GATE:<관문>` · `EVIDENCE_BUY` · `EVIDENCE_SELL` · `ALL` 중 하나다.
  - 단위의 규칙 시기 번호 = 그 단위에 해당하는 항목 중 `first_run_day` ≤ 단위 첫날인 항목 수다.
    - 모든 단위에는 `ALL`이 해당한다.
    - 관문 단위: 방향의 `EVIDENCE_BUY` 또는 `EVIDENCE_SELL`, 그리고 자기 관문 집합의 각 이름 g에 대한 `GATE:<g>`가 해당한다. `GATE:X`는 X와 `X_UNK` 모두에 해당한다.
    - 주문표 기반 단위: 방향 EVIDENCE 항목이 해당한다. 여기에 매도 하한(②)은 `GATE:SELL_FLOOR`, 대역(③-b)은 `GATE:SCENARIO_BAND`가 더해진다. 트리거는 더하는 것이 없다.
    - 주문표 단위의 첫날 = 주문표를 낸 결정의 run_day다. ticket_id `AT-<YYYYMMDD>-…`의 날짜이고, 없으면 그 주문표가 있던 결정 폴더의 날짜다.
- **현재 규칙 시기** = 같은 방식으로 셌을 때, 채점 시각의 KST 날짜까지 `first_run_day`가 지난 항목 수다.
  - 발견은 현재 규칙 시기와 같은 버킷에서만 낸다. 그보다 앞선 버킷은 표시만 한다(`EARLIER_EPOCH`).
  - 새 규칙이 들어온 뒤 아직 단위가 없으면, 그 관문은 발견이 없다.
- 파일이 없거나 깨졌으면 `EPOCHS_UNAVAILABLE`로 두고 발견을 내지 않는다(fail closed).
- 처음 항목은 git 원문으로 확인했다(git merge-base로 각 날 decision.json의 commit에 포함됐는지 확인).

| scope | first_run_day | commit | 내용 |
|---|---|---|---|
| GATE:REQ5_RREC1 | 2026-10-14 | 55803bf | RG1 연구 기록 시작 전 세션 면제(rrec-rg1-bootstrap B) |
| GATE:REQ5_RREC1 | 2026-10-14 | 4051391 | EV4 이웃 세션 여유(`RREC_EV4_NEIGHBOR_MARGIN`) 추가. 10/14 결정 자체의 commit |
| EVIDENCE_BUY · EVIDENCE_SELL | 2026-10-15 | 1a2b7d6 | C6 반등·눌림 세션 종가 방향 조건 |
| GATE:REQ5_RREC1 · EVIDENCE_BUY · EVIDENCE_SELL | 2026-10-16 | ef3bad1 | R-REC1 사건 SOXX 기준(GRID는 RG2만)·RG3 저가 사건부터·직전 unk는 새 근거 아님·매수 G3 카드 적중 |
| GATE:SELL_FLOOR | 2026-10-17 | 04f9a85 | F6 주문 창(세션 마감 시각까지)이 기록 모드 미체결 분류에 닿음. 관문 정의 변경은 아니고(diff: auto_core_tickets.py `session_close`·주문 시각 창), 보수적으로 ② 버킷만 나눈다 |
- 갱신: Cowork가 관문·근거 규칙 변경의 병합을 확인하는 세션에서 한 줄을 더한다. 사용자 손은 없다.
- 놓쳤을 때 보이기: 버킷마다 서로 다른 commit 수를 표시한다.

## 4. 발견 규칙 (부호 일관성 + 표본·자료 조건, 표시 전용)

이름: 로드맵의 "dead-band"를 여기서는 "30건 + 네 부호 일치 + 자료 90%"로 구체화한다. 크기 기준은 두지 않는다. 크기는 다음 리플레이에서 본다.

- 주 판정 세션: ① 20 · ② 5 · ③-b 5 · 트리거 20.
- 조건(버킷 = 같은 규칙 시기):
  - 채점된 독립 단위 ≥ 30.
  - 채점 가능률: NOT_SCORABLE ÷ (SCORED + NOT_SCORABLE) ≤ 10%. 넘으면 `INSUFFICIENT_COVERAGE`다(관심 목록에서 빠져 종가가 끊긴 종목이 조용히 빠지는 생존 편향을 막는다).
    - 분자·분모 모두에서 `CALENDAR_DOES_NOT_COVER_HORIZON`(달력 범위 밖)은 빼고 따로 센다. PENDING도 뺀다.
    - `START_SESSION_NOT_IN_CALENDAR` 등 그 밖의 NOT_SCORABLE은 센다.
- 판정은 넷(평균, 중앙값, 앞 반쪽 평균, 뒤 반쪽 평균)으로 한다. 반쪽은 (시작 세션, 종목, 단위 id) 순으로 정렬하고, 앞 = ⌊n/2⌋건이다.

| 판정 | 조건 | 뜻 |
|---|---|---|
| `COST`(①·②) / `STRONG`(트리거) | 넷 모두 > 0 | ①·②: 관문·하한이 비용. 트리거: 신호 방향이 맞음 |
| `PROTECT`(①·②) / `WEAK`(트리거) | 넷 모두 < 0 | ①·②: 관문·하한이 도움. 트리거: 신호 방향이 틀림 |
| `MIXED` | 그 밖 | 판단 보류 |
| ③-b `DOWN_TAIL_UNDERSTATED` | DOWN_TAIL 비율 ≥ 20%가 앞·뒤 반쪽 모두 | 하방 시나리오가 너무 작음 |
| ③-b `UP_TAIL_UNDERSTATED` | UP_TAIL 비율 ≥ 20%가 앞·뒤 반쪽 모두 | 상방 시나리오가 너무 작음 |
| ③-b `MIXED` | 그 밖 | 판단 보류 |

- 발견 줄에 함께 쓰는 것:
  - n, 서로 다른 시작 세션 수, 서로 다른 commit 수
  - 평균, 중앙값, 하위 10%
  - ①은 20세션 경로 최저 평균
  - 이유: 평균만 보고 "관문을 빼자"로 읽지 않게 한다. 관문의 목적은 꼬리 방어일 수 있다.
- 발견 뒤 절차:
  1. f-evo-loop 2단계의 입력이 된다.
  2. 도전안은 따로 사전 등록한다(표본 외 구간).
  3. 시점 무결성 리플레이 → 독립 Judge → 사용자 승인(EVOLUTION_4 상한).
  4. 발견 하나당 도전안 2회까지, 그 뒤는 사람이 정한다.
  5. 정책·권한·주문 변경은 여전히 사용자 승인 + K3다.

## 5. ④ 실행처

| 안 | 내용 | 손 | 판정 |
|---|---|---|---|
| **A** | 새 Windows 작업 `InvestmentV2-JournalScore`: 일요일 09:20 KST, 제한 15분. `run_journal_score.ps1` → 채점기 `--learning`. 결정론, 토큰 0 | 일회성 등록 1번 | **선택.** 같은 방식의 선례는 InvestmentV2-HostStatus(c1-host2), InvestmentV2-T2rcCheck(Judge가 Claude 예약 작업 대신 고름, t2-rc-preregistration-2026-10-14.md 48행) |
| B | Claude 예약 작업(주 1회) | 0 | 기각. LLM을 거치고, 매주 토큰이 들고, 결정론이 아니다 |
| C | 06:40 통합 점검 로더 | 0 | 제외. 쓰기 예외 2개·Judge 2 sha 고정(cpi-shock 187행) |
| D | 코어 안(`_score`) | 0 | 제외. 권한 경로·Hot Path(authority-paths.txt 12행). 코어 안에서 부르지 않기로 함(cpi-shock 186행) |

- **시각(일 09:20):** 코어 작업(AutoCore 06:15, AutoCoreDecide 07:45 + 연구 기록 대기 08:30, 제한 60분)·T2rcCheck·HostStatus는 모두 화~토다(register_auto_core_task.ps1 10~12행, auto_core_decide.py 64행).
  - 토요일 아침에는 코어가 08:45까지 돌 수 있다.
  - 기록 모드에서는 코어도 채점 보고서를 쓴다(auto_core_decide.py 847행).
  - decision.json 쓰기는 원자적이지 않다.
  - 일요일에는 이 셋과 겹치지 않는다. 금요일 장 마감(토 05:00, 11/1 뒤 06:00 KST)과 토요일 코어 실행이 끝난 뒤다.
  - 놓치면 켜질 때 실행된다(StartWhenAvailable). 이때도 일요일·월요일에는 코어 작업이 없다.
- **보고서 고르기:** 실행기는 실행 시작 뒤 생긴 보고서 중 `learning` 키가 있는 가장 늦은 것을 `WEEKLY_LATEST.json`에 적는다(코어가 쓴 보고서를 고르지 않게).
- **실패 보이기:**
  - 실행기가 `workspace/outputs/journal-scores/WEEKLY_LATEST.json`에 상태·종료 코드·보고서 경로를 쓴다.
  - 08:50 알림 지시문에 줄을 더하는 것은 예약 작업 지시문 변경이라 이번 범위 밖이다(다음 교체 때 후보, 기본 NO_CHANGE). 그 전까지는 Cowork 카드·M6 세션이 보고서 시각을 본다.
  - 주간 채점은 Cold Path다. 한 주 빠져도 코어·주문표에는 영향이 없다(헌법 §25).
- **배포(loop-design-check "한 번 손으로 → 예약"):**
  1. 파이프라인 테스트(합성 자료)
  2. 사용자 병합 + 등록(같은 자리)
  3. 첫 예약 실행 전에 Cowork가 실제 자료로 `--learning`을 읽기 전용 1회 실행해 확인한다. 개발 파이프라인 Builder는 unittest·git 조회만 허용돼 실제 자료 실행을 못 한다(tools/dev_pipeline/README.md 80행).
  4. 첫 예약 실행 뒤 Cowork가 결과를 확인한다.
- **T2 기록 모드가 켜져도** 주 1회 실행은 유지한다. 코어의 매일 채점(`_score`)에는 learning이 없다. 그래서 cpi-shock-review 223행("켜지면 ④는 뺀다")은 이 문서로 갱신된다.

## 6. 경계 (채점기·정책·원장)

| 대상 | 쓰는 쪽 | 루프(채점기·주간 작업) |
|---|---|---|
| decision_journal.json | portfolio_review_journal.py(사용자 확인) · 코어 기록 모드 | 읽기만 |
| alert_policy.json · workspace/policies/* | 사용자 승인 | 읽지도 쓰지도 않음 |
| portfolio_state.json | 코어 T1·대조 | 읽지 않음 |
| auto-core decision.json · s7 검토 · 종가 이력 | 코어 | 읽기만 |
| card-evidence-registry.json | Cowork(카드 수락) | 읽지 않음 |
| 채점기 코드와 이 문서의 기준(30건, 네 부호, 자료 90%, 꼬리 20%, 세션 수, 간격) | 개발 파이프라인 + Judge + 사용자 병합. 기준을 바꾸면 새 사전 등록 | 못 바꿈 |
| journal-scores/<시각>/ · WEEKLY_LATEST.json · logs/ | 채점기·실행기 | 새로 쓰기만. `check_output_root`가 원장·정책·상태 폴더를 거부(744~755행) |
| failure-museum.json · gate-rule-epochs.json | Cowork | 읽기만 |
| Windows 작업 등록 | 사용자 1번 | 없음 |

- 레드라인:
  - 발견은 정책·규칙·주문표·배분을 바꾸지 않는다.
  - 코어는 learning 블록을 읽지 않는다.
  - 루프에는 병합·주문·배분 권한이 없다.

## 7. 루프 점검 (loop-design-check, 2026-10-16)

- **판정:** 진행. 형태는 주간 regulator(표본·부호 조건) + doc-driven 골격이다.
  - 루프가 결과 칸을 쓰고, Cowork가 Museum 칸과 규칙 시기 칸(문제 칸)을 쓴다.
  - 보고서는 시각 폴더로 한 방향으로만 쌓인다. 종료 코드는 최종이다.
- **0 전제:** 모두 충족한다.
  - 주 1회 반복
  - 결정론 검증(대상 테스트 + 기준선 대비 새 실패 0)
  - 토큰 0(Windows 작업)
  - Cowork가 결과를 읽을 수 있음
- **완료 기준:**
  - 개발: 대상 테스트 통과, 새 실패 0, 독립 Judge PASS, `--learning` 없는 출력 불변.
  - 운영: 매주 WEEKLY_LATEST.json status OK + learning 있음.
- **경계:** 6절. **재시도:** 파이프라인 수정 1회, 주간 실행은 재시도 없음(다음 주가 재시도). **외부 대조:** 키움 종가·브로커 체결(사용자 결과). 자기 주장이 아니다.

| # | 실패 유형 | 판정 |
|---|---|---|
| 1 | 결정 불가 목표 | 통과. 4절 판정을 지금 고정 |
| 2 | 피고가 채점 | 통과(조건). 관문을 만든 코어 코드를 채점에 쓰지 않고, decision.json 기록값 + 키움 종가만 쓴다. ③-b 대역은 채점기 자체 식이고, 코어와 같은지는 테스트로만 확인한다. 개발은 독립 Judge |
| 3 | 경계 미명시 | 통과. 6절 |
| 4 | 실행 중에만 정할 것 | 통과. 겹침·HOLD·자격 없는 날·자료 없음·형식 불일치·규칙 변경을 미리 정했다(→ 상태, 판단 보류). Museum 문장만 사람 몫이고, 루프를 멈추지 않는다 |
| 5 | 낡은 기억 | 통과. 루프는 기계 파일만 읽는다. 자동 합성 기억 없음 |

- 레드라인 위반 없음.

## 8. 개발 작업 evo-s1 (일반 변경)

- 지시문: `docs/claude/evo-s1-builder-prompt.md`.
- 바꾸는 파일:
  - `score_decision_journal.py`
  - 새 실행기 `run_journal_score.ps1`
  - 새 등록 스크립트 `register_journal_score_task.ps1`
  - 새 테스트 2개
  - 보고 1개
- 바뀌지 않는 것: 코어·정책·상태·일지·스키마·로케일. 권한 경로(authority-paths.txt)에 걸리는 파일은 없다.
- 기본 실행(플래그 없음)은 `learning` 키가 없고, 기존 결과 키·값·화면 줄이 같다. 코어의 `_score` 호출도 같다.
- Cowork가 미리 만드는 데이터 파일:
  - `docs/claude/failure-museum.json`(빈 entries)
  - `docs/claude/gate-rule-epochs.json`(3-6 표)
- 개발 작업 수: 대기열이 비어 있고, 관제판에 진행 중인 코드 작업이 없다(autocore-on = 권한·운영, swap-soxl-pwr = K0). 3개 미만 조건을 충족한다(2026-10-16 확인).

## 9. 한계 (미리 적음)

- **D 등급이다.** 막은 행동의 가상 결과라서 다음을 반영하지 않는다.
  - 실제 체결가·수량·현금 제약
  - 첫 막힘 뒤의 다른 검사
  - 위험 예산 상호작용
  - 관문 제거는 당시 정책상 실행 가능한 선택이 아니었으므로, 이것은 후회(헌법 §17)가 아니라 관문 평가다.
- **같은 날 여러 종목은 시장 요인으로 묶여 독립이 아니다.** 반쪽 부호 조건, 간격 규칙, 시작 세션 수 표시로만 완화한다.
- **카드 TRIM/EXIT 목표·카드 점검 사유·S7 목표(G2)는 decision.json에 없다.** 그래서 후보가 아닌 종목의 관문은 일부만 보인다(구속은 상한 추정).
- **키움 겨울 30분봉 문제(fx1009-closing A7, 11/3 측정 예정)가 안 풀리면** 11/2 이후 종가가 비어 NOT_SCORABLE이 늘 수 있다. 채점 가능률 조건이 발견을 막는다.
- **달력 범위가 2026-12-31에서 끝난다.** 그 뒤 세션은 달력이 갱신될 때까지 `CALENDAR_DOES_NOT_COVER_HORIZON`이다.
- **범위 밖(별도 요청 시):**
  - SPY 비교(B7)
  - 일지 밖 결정(M6 20% vs 10%, 계획 이탈)
  - 같은 결정 ID의 분할 사용자 결정(B2)
- **표본 속도:** 30묶음·30구간까지 걸리는 시간은 확인 필요다(구속 빈도 미측정). 단위가 20세션 간격이라 한 (종목, 관문)에서는 1년(약 252세션)에 많아야 12개쯤이다. 규칙이 자주 바뀌는 동안은 더 늦다. 수개월~수년이 걸릴 수 있다.
- **보존:** decision.json은 git 밖, PC 한 곳에만 있다. sha 기록은 손실을 막지 못하고 보이게만 한다.

## 10. 바뀔 조건

- 코어가 decision.json 형식(`blocked`·`candidates`·`buy_requirements` 6칸·`shock`·`evidence`·`symbols.role/buy_approved/status`)을 바꾸면, 그 날은 `DECISION_SHAPE_UNKNOWN`이 되고 새 사전 등록이 필요하다.
- 관문·근거 규칙이 바뀌면 3-6에 한 줄을 더한다(새 버킷 시기). 판정 기준 자체는 바뀌지 않는다.
- 코어 시나리오 상수(43~46행)나 연속 구간 규칙이 바뀌면 ③-b 같음 테스트가 실패한다 → 새 사전 등록.
- 사용자가 "30건" 셈이나 표시 전용 원칙을 바꾸면 그 답이 우선한다.
- 같은 날 decision.json이 `PRESERVATION_BROKEN`이면 그 날은 결론에서 빠진다.

## 11. ③-a 옛 지시서 4건 판정 규칙 (지금 고정, 판정은 11/7 이후 1회)

| 지시서(행) | 세션 · 20세션 창 | 사전 부검 신호 | 사전 축하 신호 | 계산 |
|---|---|---|---|---|
| OI-20261008-MVLL-1 (104·105) | 10/8 · 10/9~11/5 | MRVL 종가 < $271.25 2세션 · S7 R0 해제 시각 | MRVL 종가 ≥ $298 2세션 · 10/16 콜 OI 상단 이동 | 불가: MRVL 키움 종가 이력 없음·옵션·R0 → NOT_SCORABLE |
| OI-20261008-MVLL-2 (104·105) | 10/8 · 10/9~11/5 | 위와 같음 | 위와 같음 | 불가 |
| OI-20261008-SOXL-1 (83·84) | 10/8 · 10/9~11/5 | SOXX 종가 ≥ 10/7 종가 × 1.05 연속 2세션 · PWR의 SOXX 대비 60세션 상대 약세(수동) | SOXX 종가 < EMA20 연속 2세션 · PWR 종가 EMA20 위 유지(수동) | 일부 |
| OI-20261009-SOXL-2 (116·117) | 10/9 · 10/12~11/6 | SOXX 종가 ≥ 10/9 종가 × 1.05 연속 2세션 · SOXL 종가 > EMA20 연속 2세션 | SOXL 10/9 종가 < 144.2 · SOXL 10/12 종가 < EMA50 | 전부 |

- 신호 읽는 법:
  - "N세션"은 창 안에서 연속 N세션이다.
  - 날짜를 박은 신호는 그날만 본다.
  - EMA는 그 세션이 evaluation_session인 decision.json의 `symbols[S].indicators.ema20/ema50`(코어 값)을 먼저 쓴다. 없으면(10/13 전, SOXX) 종가 이력의 그 세션에서 끝나는 연속 구간에 `auto_core_rules.ema_series`(160행)를 적용한다.
- 쪽 판정:
  - HIT: 계산 가능한 신호가 모두 맞음
  - NOT_HIT: 하나라도 창 끝까지 안 맞음
  - PARTIAL: 수동 신호가 섞임(계산 가능한 것만 표시)
  - 두 쪽 모두 HIT일 수 있다.
- 자료가 빌 때: 11/7에 창 안 종가가 비면(예: A7 겨울 30분봉) 11/14로 한 번 미룬다. 그래도 비면 그 신호는 NOT_SCORABLE이다.
- 기한: 2026-11-21까지 판정이 없으면 기본 처분 = 4건 모두 NOT_SCORABLE로 기록하고 알림만 한다.
- **라벨 `POST_HOC_ENCODED_D`:** 이 표는 2026-10-16에 10/15 종가까지 일부 결과를 본 뒤 부호화했다. 그래서 어떤 셈·발견에도 넣지 않고 학습 기록으로만 쓴다.
- 기록 위치: `docs/claude/f-evo-loop-s1-oi-verdicts-2026-11-07.md`(그때 만듦). 소비자는 f-evo-loop 2단계와 다음 SOXL·MVLL 카드다.

## 12. 검토 기록

- **이번 세션에서 연 원문:**
  - cpi-shock-review-2026-10-15.md 1~60·120~251행
  - future-tools-roadmap-2026-10-05.md 1~36·119~206행
  - score_decision_journal.py 1~89·165~262·313~690·744~886행
  - auto_core_tickets.py 210~226·282~388·690~800·832~975행
  - auto_core_decide.py 770~782·840~850·985~1006·1085~1104·1157~1160행
  - auto_core_rules.py 160·221~236행
  - validation_common.py 25~35행
  - portfolio_status.py 200~235행
  - portfolio_review_journal.py 560~610행
  - decision.json 4개(shock·buy_requirements·blocked·evidence·symbols·commit_sha)
  - S7 검토 4개
  - 종가 이력 SOXL
  - OI 6개(사전 부검 행)
  - order-instruction-design 125~140행
  - register_host_status_task.ps1 1~40행 · register-dev-tasks.ps1 1~60행 · register_auto_core_task.ps1 9~13행 · run_auto_core.ps1 해당 행
  - authority-paths.txt · tools/dev_pipeline/README.md 20~56·80행
  - git log·merge-base(규칙 시기 4개 커밋)
  - c1-host2-builder-prompt.md · r-rec1-r3-preregistration 머리 · fx1009-closing A7 행
  - 헌법 §9~§32(프로젝트 지식 검색) · 관제판 f-evo-loop v6
- **loop-design-check:** 7절.
- **내장 재검토 1회차(Opus, 읽기 전용):** 발견 21건(HIGH 2 · MED 12 · LOW 7). 본 세션이 원문으로 다시 확인했다. 21건 모두 반영 또는 정리했다.
  - 결론이 바뀐 것:
    - #1 실행 시각 토 08:20 → 일 09:20, 보고서 고르기
    - #2 R-REC1 단위를 사건일 → 충격 구간으로, REQ5_UNK 분리, SYMBOL_ONLY
    - #3 HOLD 날 포함(G0/G1 관문)
    - #7 규칙 시기(epoch) 추가
    - #9 채점 가능률 조건
  - 보완한 것:
    - #4 G1_SYMBOL_DATA·지수 ETF 연구 기록 REQ1 처리
    - #5 CARD_TRIM_SIZE_MISSING 규칙
    - #6 간격 규칙
    - #8 보존 표지 이어받기·REWRITTEN
    - #10 ③-b 연속 구간
    - #11 S7 경로 해석·범위
    - #12 Museum id·필수 칸
    - #13 트리거 필드
    - #14 ③-a 실행 주체·EMA 출처·기한
    - #15 인용·셈
    - #16 이름(dead-band 구체화)
    - #17 부호·정렬
    - #18 Builder 실제 자료 실행 제거 → Cowork 확인
    - #19 Builder 주의
    - #20 대조 목록
    - #21 이 절
- **내장 재검토 2회차(같은 재검토자, 바뀐 부분만):** 발견 12건(HIGH 0 · MED 5 · LOW 7). 원문으로 다시 확인했다(auto_core_decide.py 511~513·523~527·545~556행, auto_core_rules.py 53행, 4051391 diff, 10/13 REQ2 칸, 04f9a85가 HEAD d597a5b에 포함). 12건 모두 반영했다.
  - 결론이 바뀐 것:
    - #1 계획 전 HOLD = `PLAN_NOT_RUN`
    - #2 보존 표지(읽기 실패 주 무시, MISSING_NOW 되돌림, REWRITTEN 조건)
    - #3 현재 규칙 시기
    - #4 시기 첫날 기준·`X_UNK`
    - #5 R-REC1 단위 = 충격 구간 안 20세션 묶음
  - 보완한 것:
    - #6 epoch 2줄
    - #7 10/13 셈
    - #8 주문표 단위 첫날
    - #9 3-6 문장
    - #10 UNKNOWN·NONE
    - #11 채점 가능률 분모
    - #12 ③-a 실행 주체(관제판 f-evo-loop에 11/7 재개·11/21 기한을 적음)
- 최대 2회 규칙에 따라 여기서 멈춘다. 2회차 반영분은 본 세션이 L1~L6로 직접 점검했다: 주장-원문, 자료 해상도, 같은 사실을 적은 다른 곳(builder·epochs 파일), 막힘이 결함인지, 기존 제약 완화 없음, 빠진 대안.
- 미해결 0. 기본 처분은 해당 없음.

검토 완결: 원문 확인 32/32(1절 표 9행 + 인용 23곳, 모두 이번 세션에서 직접 엶) · 내장 재검토 2회(반영 33건) · 미해결 0 · 자료 시점 decision.json 2026-10-16 07:45 KST 실행분·git HEAD d597a5b(2026-10-16 14:25 KST) · 바뀔 조건 10절

## 13. 변경 기록

- 2026-10-16: 초안 → 재검토 1회차 반영 → 재검토 2회차 반영.
