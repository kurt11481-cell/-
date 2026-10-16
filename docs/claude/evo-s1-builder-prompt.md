---
id: evo-s1-builder-prompt
title: 진화 루프 1단계 — 채점기 learning 블록(관문별 소급·매도 하한 반사실·시나리오 대역·트리거 종류·Failure Museum 후보·규칙 시기) + 주 1회 Windows 작업
date: 2026-10-16
class: 일반 변경(dev-run class general). 채점기 1개 수정 + 새 PowerShell 2개 + 새 테스트 2개 + 보고 1개. 코어·정책·상태·일지·스키마·로케일 불변. 권한 경로 파일 없음
decision: 사용자 "결정 learn-loop: a"(2026-10-15 11:00 KST, docs/claude/cpi-shock-review-2026-10-15.md 211·213행) + 2026-10-16 "f-evo-loop 진행" 요청
source: docs/claude/f-evo-loop-s1-preregistration-2026-10-16.md (사전 등록, sha256은 같은 이름 .sha256) — 정의가 이 지시문과 다르면 사전 등록이 우선이고, 보고서에 차이를 적는다
authority: order_authority=false · quantity_authority=none · 키움 호출 없음 · 정책·상태·일지 쓰기 없음
consumers: 주간 Windows 작업 InvestmentV2-JournalScore · Cowork 카드·M6·평가 세션 · f-evo-loop 2단계 · portfolio_status.py(기존 읽기, 바뀌면 안 됨)
weekly_user_touch: 0 (일회성: .\tools\dev-merge.ps1 evo-s1 1번 + register_journal_score_task.ps1 1번)
---

```dev-run
{"task_id": "evo-s1", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 240, "builder_timeout_min": 120, "allowed_paths": ["manage-us-stock-strategy/scripts/score_decision_journal.py", "manage-us-stock-strategy/scripts/run_journal_score.ps1", "manage-us-stock-strategy/scripts/register_journal_score_task.ps1", "manage-us-stock-strategy/tests/test_score_learning.py", "manage-us-stock-strategy/tests/test_journal_score_task_static.py", "docs/claude/evo-s1-report.md"], "target_tests": ["test_score_*.py", "test_journal_score_task_static*.py"], "commit_message": "feat(score): opt-in learning block (gate counterfactuals, sell floor, scenario band, trigger kinds, museum candidates, rule epochs) and weekly Windows task scripts"}
```

## 목표

결정론 채점기 `manage-us-stock-strategy/scripts/score_decision_journal.py`에 **선택 플래그 `--learning`** 을 더한다. 켜면 보고서에 `learning` 블록을 붙인다. 블록에 들어가는 것:
- 자동 코어가 막은 매수·매도의 관문별 가상 성적
- 매도 하한 때문에 안 팔린 매도의 가상 성적
- 주문표 시나리오 대역 판정
- 트리거 종류별 성적
- Failure Museum 후보
- 규칙 시기별 요약·발견

또 이 채점을 주 1회 돌릴 Windows 작업 스크립트 2개를 만든다. 모든 값은 등급 D, 표시 전용이다. 규칙·정책·주문을 바꾸지 않는다. **정의의 원문은 사전 등록 3·4절이다. 먼저 그 문서를 끝까지 읽는다.**

## 반드시 지킬 것 (Judge가 본다)

- **기본 길 불변:** `--learning`이 없으면 보고서 JSON에 `learning` 키가 없다. 기존 키와 값, 화면 출력 줄, 종료 코드도 지금과 같다.
  - `score_journal(...)`의 시그니처와 반환값을 바꾸지 않는다.
  - 코어는 `score_decision_journal.main(["--journal", path])`로 부른다(`auto_core_decide.py` 1157~1160행). 이 호출에서 learning 코드가 실행되지 않아야 한다.
  - `portfolio_status.py` 209~235행이 읽는 `summary.pending_decisions`·`journal.head_sha256`는 그대로다.
- **실행 중 코어 모듈 import 금지:** `auto_core*`를 import하지 않는다. 기존 import는 그대로 둔다. 시나리오 대역 식과 분위수는 채점기 안에 둔다. 테스트에서만 `auto_core_tickets`·`auto_core_rules`를 import해 같은 값인지 확인한다.
- **쓰기:** 쓸 수 있는 곳은 다음뿐이다. 일지·정책·상태·decision.json·docs 파일은 읽기만 한다.
  - 출력 루트(`check_output_root` 통과한 곳) 아래 새 폴더
  - 실행기가 쓰는 `workspace/outputs/journal-scores/WEEKLY_LATEST.json`·`logs/`
- **실패는 상태로 남긴다.**
  - 어떤 입력이 깨져도 예외로 멈추지 않는다. 오류 목록·`NOT_SCORABLE` 사유로 남긴다. 기존 종료 코드 규칙(일지 CORRUPT만 2)을 유지한다.
  - `_score_horizon`은 시작 세션이 달력 밖이면 `sessions.index`에서 ValueError를 낸다(173행). learning에서 부를 때는 먼저 막고 `START_SESSION_NOT_IN_CALENDAR`로 둔다. `buy_session`이 None인 경우도 같다.
- **기존 권한 줄:** 기존 `order_authority`·`quantity_authority` 줄과 값을 고치거나 옮기지 않는다.
- **셸 명령:** 명령 문자열에 `auto_core.py`라는 글자를 넣지 않는다(설정이 거부함). 이 실행에서 허용된 명령은 `python -m unittest …`, 스키마 감사, `git status|diff|log`뿐이다. 실제 저장소 자료로 채점기를 돌리거나 PowerShell을 실행하려 하지 않는다(Cowork가 병합 뒤 한다).
- **새 파일에 쓰지 않을 글자:** 새 파일(스크립트·테스트·보고)에 주문 도구·주문 API 이름을 쓰지 않는다. 금지 검사용 문자열로도 쓰지 않는다(파이프라인이 권한 작업으로 올림). 쓸 수 있는 권한 필드 이름은 `order_authority`뿐이다.
- **고칠 파일:** allowed_paths의 6개만 고친다. 로케일 JSON은 고치지 않는다. learning 화면 문구는 채점기 안 상수로 둔다.

## 바꿀 내용

### 1) `score_decision_journal.py`

**CLI(추가만):**
- `--learning` (store_true)
- `--museum PATH`: 기본값 `REPO_ROOT / "docs/claude/failure-museum.json"`
- `--epochs PATH`: 기본값 `REPO_ROOT / "docs/claude/gate-rule-epochs.json"`
- 기존 `--decisions-root`를 learning 입력에도 쓴다.

**상수(추가):**
- `LEARNING_SCHEMA = "journal-learning-1.0"`
- `PREREGISTRATION = {"id": "f-evo-loop-s1-preregistration-2026-10-16", "sha256": "cd3709820e2d16d6d941679327783a0fa73356e8600cea6589d610830b183d53"}`
- `GATE_PRIMARY = 20`
- `FLOOR_HORIZONS = (1, 5, 20)`, `FLOOR_PRIMARY = 5`, `NEXT_FILL_WINDOW = 5`
- `BAND_RETURNS = 60`, `BAND_HORIZON = 5`, `BAND_UP = 0.9`, `BAND_DOWN = 0.1`, `BAND_PRIMARY = 5`
- `TRIGGER_PRIMARY = 20`
- `TAIL_SHARE = Decimal("0.2")`
- `COVERAGE_MAX_UNSCORABLE = Decimal("0.1")`
- `MUSEUM_HORIZON = 20`
- `REQ_LABELS = ("REQ1_EARNINGS", "REQ2_EXPOSURE_CASH_PRODUCT", "REQ3_EVIDENCE", "REQ4_M6", "REQ5_RREC1")`
- 결론 기준은 기존 `MIN_SCORED_FOR_CONCLUSION`(30)을 그대로 쓴다.

**새 순수 함수 `score_learning(...)`:** 파일을 읽지 않는다. 인자:
- 결정 날짜 문서 목록 `[{day, sha256, document | error}]`
- 날짜별 S7 결과 `{day: {"status": "OK"|사유, "reduce": [symbols]}}`
- 기존 보고서의 `results`·`ticket_results`
- 주문표 원본 목록(일지 + 비교 모드; `ticket_id, ticker, side, mode, session, decision_key, would_fill, user_state`)
- 달력, 수정·원 종가, 미검증 사유, 분할 상태
- museum 문서, epochs 문서
- 직전 learning 보고서의 `decision_days`(없으면 None)
- evaluation_as_of

**main 흐름(`--learning`일 때만):**
1. 로더 `load_decision_days(decisions_root)`로 `<YYYY-MM-DD>/decision.json`만 읽는다(`decision.rerun-*` 제외). 각 파일의 raw bytes sha256을 함께 둔다.
2. 각 문서의 `inputs.s7_review.path`를 해석한다. 저장소 기준 상대 경로에서 `workspace/outputs/auto-core/` 접두어를 떼고 decisions_root 아래로 해석한다. 결과가 decisions_root 밖이면 `S7_PATH_OUTSIDE`, 못 읽으면 `S7_REVIEW_UNREADABLE`. 읽히면 `recommendations.reduce[].symbol`을 모은다.
3. museum·epochs 파일을 읽는다. 없으면 MISSING, 깨졌으면 INVALID.
4. 직전 learning 보고서를 찾는다. 출력 루트에서 이번 것보다 앞선 폴더 중 `learning`이 있는 가장 늦은 것이다.
5. 종가를 읽을 tickers에 결정 문서들의 `symbols` 키를 더한다. 일지가 CORRUPT가 아니면 종가를 읽는다.
6. `report["learning"] = score_learning(...)`을 붙이고, 화면 줄 몇 개를 더한다.

**learning 블록:**

**`decision_days`**
- 필드: `[{day, evaluation_session, buy_session, status, commit_sha, generated_at, eligible, exclude_reason, sha256, first_sha256, first_generated_at, first_evaluation_session, first_buy_session, flags, flag_history}]`
- eligible 조건:
  - `status`가 "OK" 또는 "HOLD"
  - **계획이 돌았음**: evaluation_session·buy_session이 null이 아니고 `symbols`·`buy_requirements`가 비어 있지 않음. 아니면 `PLAN_NOT_RUN`. 계획 전 HOLD(KILL_SWITCH_ON·T1_RESULT_MISSING·T1_NOT_OK)는 빈 결정 틀이다.
  - `no_new_session` false, `carried_from` null
  - 형식이 맞음: 필수 키 `blocked`·`candidates`·`buy_requirements`·`evidence`·`symbols`·`shock`·`buy_session`가 있고, `buy_requirements` 모든 행의 `c`가 6칸. 아니면 `DECISION_SHAPE_UNKNOWN`
  - 같은 evaluation_session이면 늦은 day만 남기고, 앞의 것은 `DUPLICATE_SESSION`. evaluation_session이 null인 날끼리는 이 규칙을 쓰지 않는다.
  - 자격 없는 날(사유 무관)은 구간·충격 구간을 잇지도 끊지도 않는다.
- 계획 뒤 HOLD 날: `decision.reasons` 각각의 첫 ":" 앞부분을 `day_gates`로 두고, 그날 모든 단위의 관문에 더한다.
- 보존: 직전 보고서의 같은 day 행에서 `first_*`·`flags`·`flag_history`를 이어받는다. 없으면 이번 값이 처음이다. 읽지 못한 파일(JSON 아님 등)의 sha는 `first_sha256`으로 적지 않는다.
  - 결정 폴더가 없거나 decision.json을 하나도 못 읽었는데 직전 보고서에는 날짜가 있었다면: 표지를 바꾸지 않고 이어받은 행을 그대로 두며, learning 최상위에 `DECISIONS_ROOT_UNREADABLE` 오류만 남긴다.
  - sha == first → 표지 변화 없음.
  - sha != first이고, generated_at의 KST 날짜 == day이며, evaluation_session·buy_session이 first와 같음 → `REWRITTEN`(한 번 붙으면 남음, eligible 유지).
  - 그 밖에 sha != first → `PRESERVATION_BROKEN`(한 번 붙으면 남음, eligible false).
  - 직전 보고서에 있던 day가 이번에 없으면 → 그 day 행을 이어받은 값으로 넣고 `exclude_reason: "MISSING_NOW"`(그 주만 자격 없음, 표지로 남기지 않고 flag_history에 기록).
    - 다시 나타나서 sha == first면 정상으로 돌아온다.
    - 다르면 `PRESERVATION_BROKEN`이다.

**관문 이름 규칙**(사전 등록 3-1)
- REQ 칸 i(0~4)의 상태 s가 "ok"가 아니면 이름은 다음과 같다.
  - s == "unk"이면 `REQ_LABELS[i] + "_UNK"`, 그 밖은 `REQ_LABELS[i]`
  - 단 i == 0이고 칸의 글 `t`에 `RESEARCH_RECORD_NOT_OK`가 있으면 `RESEARCH_RECORD_NOT_OK`
- blocked 사유 r → `r.split(":")[0]`. 단 다음은 바꾼다.
  - `REQx_…:unk`는 `REQx_…_UNK`
  - `REQ1_EARNINGS:no`이고 그 종목 REQ1 칸 글에 `RESEARCH_RECORD_NOT_OK`가 있으면 `RESEARCH_RECORD_NOT_OK`
- 같은 이름은 한 번만 넣는다(집합).

**`gate_units`(날짜 단위 행)**: eligible한 날마다 만든다. 모든 단위의 gates에 그날 `day_gates`를 더한다.

*매수:* `symbols[S].buy_approved is True`이고 `evidence[S].buy.basis_met is True`인 S만 본다.
- `(S, "buy")`가 candidates에 없으면 gates는 다음의 합이다.
  - `{"CIRCUIT_NEW_EVIDENCE"}`
  - REQ 칸 이름들
  - `inputs.research_record.status != "OK"`이면 `RESEARCH_RECORD_NOT_OK`
  - `symbols[S].status != "OK"`이거나 `indicators.sigma60`이 없거나 null이면 `G1_SYMBOL_DATA`
- 후보이고 그 종목 매수 주문표가 없으면, gates = 그 종목 매수 blocked 항목 사유 이름들.
- 주문표가 있으면 행을 만들지 않는다.

*매도:* `symbols[S].role == "held"`인 S만 본다.
- 매도 후보이고 주문표 없음 → blocked 사유 이름들.
- 후보가 아니고 그 종목 매도 blocked에 `CARD_TRIM_SIZE_MISSING` 있음:
  - 근거 있음 → `{CARD_TRIM_SIZE_MISSING}`
  - 근거 없음 → `{CARD_TRIM_SIZE_MISSING, CIRCUIT_SELL_NO_EVIDENCE}`
- 그 밖에 후보가 아니고 `evidence[S].sell.basis_met` → `{CIRCUIT_SELL_NO_GAP}`.
- 그 밖에 근거 미충족이고 S가 그날 S7 reduce에 있음 → `{CIRCUIT_SELL_NO_EVIDENCE}`. 그날 S7 상태가 OK가 아니면 이 판정 대신 행에 `status: "NOT_SCORABLE"`, `reason: <S7 사유>`를 둔다. NO_GAP 판정은 S7과 무관하다.
- 후보 없이 blocked에 있는 다른 매도 사유도 gates에 합친다.

*행 필드:* `{day, symbol, side, gates(정렬 목록), binding: len(gates)==1, binding_scope: "EVALUATED_GATES_ONLY", start_session: buy_session, epoch}`
- REQ5 계열이 있으면 추가로 `shock_open`(= `shock.open`), `symbol_open`(= `shock.by_symbol[S].open`), `event`(= `shock.event`의 date·c0), `rg`(= `shock.by_symbol[S].rg`)를 둔다.

**`shock_periods`**
- eligible한 날을 evaluation_session 순으로 본다. `shock.open is True`가 이어지는 동안을 하나의 구간으로 한다.
  - eligible하지 않은 날과 `shock.open`이 bool이 아닌 날(None·없음)은 건너뛴다.
  - `shock.open is False`인 날에서 끝난다.
- 필드: `{period_id(첫날 evaluation_session), days, event_dates(보인 shock.event.date 목록, 중복 제거), c0s}`
- 단위의 R-REC1 키:
  - 그날 shock.open is True면 그 구간 id
  - 아니고 symbol_open is True면 `"SYMBOL_ONLY"`
  - shock.open이 bool이 아니면 `"UNKNOWN"`
  - 그 밖은 `"NONE"`

**`gate_episodes`**
- 키 = (symbol, side, gates 튜플, R-REC1 키 — gates에 `REQ5_RREC1`이나 `REQ5_RREC1_UNK`가 있을 때만).
- eligible한 날을 순서대로 보며 키가 이어지면 같은 구간이다. eligible하지 않은 날은 건너뛴다(잇지도 끊지도 않음). eligible한 날에 키가 없으면 끝난다.
- 필드: `{episode_id, symbol, side, gates, binding(첫날 기준), first_day, last_day, days, start_session, rrec1_key?, epoch, unit, horizons, path_20}`
  - `horizons`: 5·20·60. `_score_horizon`을 매수 LONG / 매도 REDUCE로 부르고, `cf_value` = 결과의 vs_cash.
  - `path_20`: 시작 종가 대비 이후 1~20세션 각 종가의 최저·최고 **주가 수익률**(부호 그대로). 20세션이 모두 끝나고 종가가 모두 있을 때만 값을 내고, 아니면 PENDING / NOT_SCORABLE.
  - `unit`: 같은 (symbol, side, gates) 키에서 직전 unit 구간의 start_session과 달력상 20세션 이상 떨어졌으면 true. 첫 번째도 true.

**`rrec1_units`(R-REC1 묶음)**
- 대상: binding이고 gates == ["REQ5_RREC1"]이며 R-REC1 키가 구간 id인 구간(episode의 unit 값과 무관).
- 같은 period_id 안에서 start_session 오름차순(동률은 symbol)으로 본다.
  - 묶음은 첫 구간에서 열린다(묶음 시작 = 그 start_session, 묶음 epoch = 그 구간 epoch).
  - 다음 구간이 묶음 시작에서 달력상 20세션 미만이고 epoch가 같으면 같은 묶음에 넣는다. 아니면 새 묶음을 연다.
- 필드: `{unit_id, period_id, start_session, epoch, n_episodes, symbols, episode_ids, horizons}`
  - horizons: 세션 수마다 묶음 구간들의 SCORED cf_value 단순 평균(소수 6자리 문자열). 없으면 PENDING / NOT_SCORABLE.
- 모든 묶음은 독립 단위다.
- gates == ["REQ5_RREC1_UNK"] 구간도 같은 방식으로 `rrec1_unk_units`에 묶는다(표시만).

**`epoch` 계산**
- epochs 문서: `{"schema": "gate-rule-epochs-1.0", "epochs": [{"scope", "first_run_day", "commit", "note"}]}`. 다른 최상위 키는 무시한다.
- 해당 항목 집합 A(단위):
  - 모든 단위: scope `ALL`
  - 관문 단위: 방향의 `EVIDENCE_BUY` 또는 `EVIDENCE_SELL`, 단위 gates의 각 이름 g에 대해 `GATE:<g>`. 단 `GATE:X`는 g == X 또는 g == X + "_UNK"에 해당한다.
  - 주문표 기반 단위: 방향 EVIDENCE. 여기에 sell_floor는 `GATE:SELL_FLOOR`, scenario_band는 `GATE:SCENARIO_BAND`를 더한다. trigger_kinds는 더하는 것이 없다.
- 단위의 epoch = A 중 `first_run_day <= 단위 첫 day`인 항목 수.
  - 관문 단위의 첫 day = 구간 first_day.
  - 주문표 단위의 첫 day = ticket_id가 `AT-YYYYMMDD-`로 시작하면 그 날짜(YYYY-MM-DD). 아니면 그 주문표가 있던 결정 폴더 날짜. 둘 다 없으면 epoch null.
- **현재 epoch**(버킷마다): 그 버킷 키에 해당하는 A 중 `first_run_day <= evaluation_as_of의 KST 날짜`인 항목 수.
- epochs가 MISSING / INVALID면 epoch = null이고, 모든 finding은 `EPOCHS_UNAVAILABLE`.

**`sell_floor`(②)**
- 대상: 주문표 원본 중 side == "sell"이면서 다음 중 하나.
  - `would_fill is False`
  - mode == "apply"이고 user_state == "unfilled"
- `unit`: decision_key별 첫 건이면서, 같은 ticker의 직전 unit과 5세션 이상 떨어지면 true.
- 필드: `{ticket_id, ticker, session, decision_key, unit, epoch, horizons, next_fill}`
  - `horizons`: 1·5·20세션 `_score_horizon` REDUCE의 cf_value(= −r)
  - `next_fill`: 같은 ticker 매도 주문표 중 세션이 뒤이고 5세션 이내이며 would_fill true인 첫 건.
    - 있으면 `{session, sessions_after, delay_value}`. delay_value = −(C_fill/C_t − 1), 수정 종가.
    - 없고 창이 끝났으면 `{status: "NO_LATER_FILL_WITHIN_5"}`, 창이 안 끝났으면 PENDING.

**`scenario_band`(③-b)**
- 대상: 주문표 원본 전부. `unit`: decision_key별 첫 건이면서, 같은 (ticker, side) 직전 unit과 5세션 이상 떨어지면 true.
- 대역:
  - 종가 목록 = 주문표 세션 바로 앞 달력 세션에서 끝나는 **연속 구간**의 수정 종가다. 그 세션부터 거꾸로 달력상 이어진 세션만 쓰고, 달력에서 종가가 빈 세션을 만나면 거기서 멈춘다. `auto_core_rules.build_series`와 같다.
  - 마지막 65개로 5세션 수익률 60개를 만든다. 분위수는 선형 보간(`auto_core_tickets.quantile`과 같은 식)이고 상단 0.9, 하단 0.1이다.
  - 65개 미만이면 `SCENARIO_HISTORY_SHORT`.
- r5 = 주문표 세션 종가 → 5세션 뒤 종가 수익률(`_score_horizon`의 stock_return).
- 판정: `UP_TAIL`(r5 ≥ up) · `DOWN_TAIL`(r5 ≤ down) · `INSIDE` · `PENDING` · `NOT_SCORABLE`.
- `path`: 매수면 DOWN_TAIL → "PREMORTEM", UP_TAIL → "PRECELEBRATION". 매도는 반대. 그 밖은 null.

**`trigger_kinds`**
- 대상: `ticket_results` 행 중 decision_key별 첫 건. ticket_results에는 decision_key가 없으므로 주문표 원본과 ticket_id로 잇는다.
- 행마다 그 행의 `evidence_weak_kinds`에서 kinds를 정한다.
  - None → `["WEAK_KINDS_NOT_RECORDED"]`
  - 빈 목록 → `["NO_WEAK_KIND"]`
- 각 kind마다 행: `{ticket_id, ticker, side, kind, overlap, unit, epoch, horizons}`
  - horizons: 5·20·60 `_score_horizon`(매수 LONG / 매도 REDUCE, 체결 무관)의 cf_value
  - unit: 같은 (ticker, side, kind) 직전 unit과 20세션 이상이면 true

**`buckets`(요약·발견, 사전 등록 4절)**

| family | key | 단위 | 주 세션 |
|---|---|---|---|
| `GATE` | (side, gate, epoch) | binding·unit 구간, gates가 원소 하나 | 20 |
| `GATE_RREC1_UNIT` | (epoch) | rrec1_units | 20 |
| `SELL_FLOOR` | (epoch) | unit 행 | 5 |
| `SCENARIO_BAND` | (side, epoch) | unit 행 | 5 |
| `TRIGGER_KIND` | (side, kind, epoch) | unit 행. `WEAK_KINDS_NOT_RECORDED`는 표시만 | 20 |

- GATE의 REQ5 버킷 처리:
  - gate가 `REQ5_RREC1`·`REQ5_RREC1_UNK`인 GATE 버킷은 표시만 한다(finding `"SEE_RREC1_UNITS"`). 발견은 `GATE_RREC1_UNIT`에서 낸다.
  - R-REC1 키가 SYMBOL_ONLY / UNKNOWN / NONE인 REQ5 구간은 gate 이름을 `REQ5_RREC1@SYMBOL_ONLY` 등으로 바꿔 따로 두고, 표시만 한다(finding `"DISPLAY_ONLY"`).
- 각 버킷 필드: `{family, key, primary_horizon, current_epoch, n_units, n_scored, n_unscorable(사유별 수 포함), n_calendar_out, coverage_ok, distinct_start_sessions, distinct_commits, mean, median, p10, first_half_mean, second_half_mean, path_min_mean(GATE·GATE_RREC1_UNIT만), conclusion_allowed, finding}`
  - 값은 소수 6자리 문자열, 없으면 null.
  - 반쪽: (start_session, symbol, unit id) 오름차순, 앞 = ⌊n/2⌋건.
  - p10: 선형 보간.
  - `distinct_commits`: 그 단위들의 첫 day의 decision `commit_sha` 종류 수.
  - `coverage_ok`: 주 세션에서 NOT_SCORABLE ÷ (SCORED + NOT_SCORABLE) ≤ 0.1.
    - 분자·분모 모두에서 reason `CALENDAR_DOES_NOT_COVER_HORIZON`은 빼고 `n_calendar_out`으로 센다. PENDING도 뺀다.
    - 그 밖의 NOT_SCORABLE(`START_SESSION_NOT_IN_CALENDAR` 포함)은 센다.
    - 분모가 0이면 coverage_ok false.
  - `conclusion_allowed`: n_scored ≥ 30, coverage_ok, epochs OK, 버킷 epoch == `current_epoch`가 모두 맞을 때.
- finding:
  - 다음 경우에는 판정 대신 이 값들을 이 순서로 쓴다: epochs가 OK가 아니면 `"EPOCHS_UNAVAILABLE"`, 버킷 epoch < current_epoch면 `"EARLIER_EPOCH"`, n_scored < 30이면 `"INSUFFICIENT_SAMPLE"`, coverage_ok가 아니면 `"INSUFFICIENT_COVERAGE"`.
  - 그 밖:
    - GATE·GATE_RREC1_UNIT·SELL_FLOOR: 넷(mean, median, 앞, 뒤) 모두 > 0이면 `"COST"`, 모두 < 0이면 `"PROTECT"`, 그 밖 `"MIXED"`.
    - TRIGGER_KIND: 같은 조건으로 `"STRONG"` / `"WEAK"` / `"MIXED"`.
    - SCENARIO_BAND: 판정된(UP/DOWN/INSIDE) 행으로 앞·뒤 반쪽 각각 DOWN_TAIL 비율 ≥ 0.2이면 `"DOWN_TAIL_UNDERSTATED"`, UP_TAIL로 같은 조건이면 `"UP_TAIL_UNDERSTATED"`(둘 다면 목록), 그 밖 `"MIXED"`. 앞·뒤·전체 UP/DOWN 비율을 함께 둔다.
- 겹침 구간(binding false)은 `overlap_summary`에 (side, gates 집합, epoch)별 n과 20세션 평균만 둔다(발견 없음).

**`museum`**
- 후보(20세션 SCORED만):
  - (i) `results` 행의 vs_cash < 0 → `RESULT:<decision_id>:<kind>:h20`(kind = ANALYSIS|USER)
  - (ii) `ticket_results` 행 중 user state filled/partial이고 user 20세션 vs_no_action < 0 → `TICKET:<ticket_id>:USER:h20`
  - (iii) mode == "compare"이고 would_fill true이며 20세션 vs_no_action < 0 → `TICKET:<ticket_id>:HYPOTHETICAL:h20`(grade D)
- `control`: 같은 세 종류에서 20세션 값 > 0인 id 목록(표시만).
- museum 문서: `{"schema": "failure-museum-1.0", "entries": [...]}`. 다른 최상위 키는 무시한다.
  - entries 필수 칸: `candidate_id`, `failed_assumption`(비지 않은 글), `category`(THESIS·EVIDENCE·TIMING·SIZE·DATA·RULE·TAIL_EVENT·NONE), `evidence`(비지 않은 목록), `written_by`, `written_at`.
  - 선택 칸: `feasible_note`, `grade`(기본 "D").
  - 같은 candidate_id는 뒤가 이긴다. 잘못된 항목은 errors에 넣고 그 항목만 뺀다.
- 출력: `{status: OK|MISSING|INVALID, errors, candidates: [{candidate_id, value}], control: [ids], filled: n, pending: [ids]}`.

**그 밖**
- 최상위 필드: `schema`, `preregistration`, `label: "COUNTERFACTUAL_D"`, `display_only: true`, `epochs: {status, count}`, `errors`.

**화면 줄(learning일 때만 덧붙임, 한국어 상수):**
- 날짜 수(자격 / 제외 / 보존 깨짐)
- 버킷 수, 결론 허용 버킷 수
- 발견 목록(COST·PROTECT·STRONG·WEAK·UNDERSTATED). 줄마다 "표시 전용 D — 규칙 변경 근거 아님"
- museum pending 수

### 2) `manage-us-stock-strategy/scripts/run_journal_score.ps1` (새 파일)

- `run_auto_core.ps1`의 인자·파이썬 찾기·UTF-8 환경 방식을 따른다.
  - `-RepositoryRoot` 기본값 `$PSScriptRoot\..\..`(5.1 param 기본값 문제 처리 포함)
  - `-PythonPath`: `.venv` → `venv` → PATH 순
- 하는 일:
  1. `python manage-us-stock-strategy\scripts\score_decision_journal.py --learning`를 실행한다. 출력은 `workspace\outputs\journal-scores\logs\<UTC시각>.log`에 쓴다.
  2. 끝나면 `workspace\outputs\journal-scores\WEEKLY_LATEST.json`을 임시 파일에 쓴 뒤 바꿔 넣는다(`Move-Item -Force`). UTF-8, BOM 없음.
     - 필드: `{schema: "journal-score-weekly/v1", started_at, finished_at(UTC ISO), exit_code, status: "OK"|"FAIL", report_path, learning_present, order_authority: false}`
     - `report_path`: 실행 시작 뒤 생긴 `<시각>\journal-scores.json` 중 `learning` 키가 있는 가장 늦은 것. 없으면 null이고 status FAIL.
- 재시도는 없다. 종료 코드 = 파이썬 종료 코드(보고서가 없으면 1).
- 쓰는 곳은 그 두 곳과 채점기 출력뿐이다. 키움·네트워크 호출 없음.

### 3) `manage-us-stock-strategy/scripts/register_journal_score_task.ps1` (새 파일)

- `register_host_status_task.ps1`을 그대로 본뜬다: PlanOnly, 한국 표준시 확인, Interactive, Limited, StartWhenAvailable, `WakeToRun:$false`, IgnoreNew, `Register-ScheduledTask -Force`, 출력 형식.
- 주기는 매주 한 번이므로 주간 트리거(`New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 09:20`)를 쓴다. 본뜬 스크립트의 요일·시간 표기(화~토 등)를 그대로 두지 않는다.
- 작업 1개:
  - 이름 `InvestmentV2-JournalScore`, **매주 일요일 09:20**, 제한 15분
  - 실행: `run_journal_score.ps1`을 `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ... -RepositoryRoot ...`로
  - 설명: "Investment_V2 weekly journal scoring with the learning block (display only, writes journal-scores only, no order authority)"
- 이 이름 하나만 만들거나 덮어쓴다. 다른 작업은 읽지도 바꾸지도 않는다. 등록이 실행을 뜻하지는 않는다.

### 4) `manage-us-stock-strategy/tests/test_score_learning.py` (unittest, 표준 라이브러리 + 저장소 모듈)

임시 폴더와 합성 자료(달력·종가 이력·일지·결정 폴더·S7 파일·museum·epochs)로 만든다. 실제 workspace 파일에 기대지 않는다. 최소 다음을 확인한다.

**a. 기본 길**
- `--learning` 없이 `main`을 돌리면 보고서에 `learning`이 없다.
- 같은 입력·같은 `--evaluation-as-of`에서 `--learning` 유무와 관계없이 `results`·`ticket_results`·`summary`·`ticket_summary`·`journal`·`calendar` 값이 같다(`close_histories`는 learning 종목만큼 늘 수 있음).
- 종료 코드가 같다.

**b. 날짜**
- 계획 뒤 HOLD는 자격이 있고 `day_gates`가 붙는다.
- 빈 결정 틀의 HOLD(sessions null, symbols {})는 `PLAN_NOT_RUN`이고 구간을 끊지 않는다. FAIL은 제외된다.
- 같은 evaluation_session이면 늦은 날만 쓴다.
- `no_new_session`이면 제외된다.
- `c` 5칸이면 `DECISION_SHAPE_UNKNOWN`.
- 보존:
  - 같은 날 재실행(KST 날짜·세션 같음, sha·generated_at 다름) → `REWRITTEN`, 자격 유지.
  - sha만 다르거나 날짜·세션이 다름 → `PRESERVATION_BROKEN`. 다음 보고서에도 남는다.
  - 사라짐 → `MISSING_NOW`(그 주만). 같은 sha로 돌아오면 정상, 다른 sha로 돌아오면 BROKEN.
  - 결정 폴더 전체를 못 읽은 주 → 표지 변화 없이 `DECISIONS_ROOT_UNREADABLE`.

**c. 관문 이름**
- `unk` → `_UNK`.
- 지수 ETF REQ1의 연구 기록 글 → `RESEARCH_RECORD_NOT_OK` 하나만(REQ1 없음).
- blocked `REQ5_RREC1:unk` → `REQ5_RREC1_UNK`.

**d. 단위**
- 새 근거 아님 + REQ 모두 ok → `["CIRCUIT_NEW_EVIDENCE"]` binding.
- 후보 + blocked `REQ5_RREC1:no` 하나 → binding.
- 새 근거 아님 + REQ5 no → 겹침.
- `buy_approved` false, 또는 basis false → 행 없음.
- sigma60 없음 → `G1_SYMBOL_DATA` 포함.
- 매도 NO_GAP, S7 감축 + 근거 없음 → NO_EVIDENCE.
- CARD_TRIM 두 경우.
- S7 파일 없음 → 그 판정만 NOT_SCORABLE이고, NO_GAP은 정상.
- S7 경로가 밖 → `S7_PATH_OUTSIDE`.

**e. 충격 구간·구간**
- open이 이어지는 3일에서 shock.event.date가 날마다 바뀌어도 구간은 1개다.
- open false 날이 오면 새 구간이다. open None 날은 건너뛰고 키는 UNKNOWN이다.
- SYMBOL_ONLY가 나온다.
- 자격 없는 날을 사이에 둔 구간은 이어지고, 자격 있는 날에 빠지면 끊긴다.
- 간격 20세션 미만 재등장은 unit false다.

**f. 값**
- 매수 cf = r, 매도 cf = −r.
- 시간이 덜 지났으면 PENDING. 종가가 없으면 NOT_SCORABLE.
- 달력 밖 시작 → `START_SESSION_NOT_IN_CALENDAR`(예외 없음).
- path_20은 부호 그대로이고, 20세션이 다 끝났을 때만 나온다.

**g. rrec1_units**
- 한 충격 구간 안에서 시작이 20세션 미만 차이면 한 묶음이다. 20세션 이상이거나 epoch가 다르면 새 묶음이다.
- 묶음 평균이 맞는다.
- REQ5_RREC1_UNK는 따로 묶인다.

**h. 매도 하한**
- would_fill false 매도 → 1·5·20 −r, next_fill 지연값.
- 같은 key 재발행은 unit false.
- would_fill true 매도는 행이 없다.

**i. 시나리오 대역**
- 합성 종가 70개 이상에서 채점기 (up, down)이 `auto_core_tickets.scenarios(closes)`와 소수 9자리까지 같다.
- 달력 중간에 빈 세션이 있는 경우, 채점기 대역이 `auto_core_rules.build_series(...)` 결과 close로 계산한 `scenarios`와 같거나, 둘 다 SHORT다. 이 두 import는 테스트 안에서만 한다.
- UP/DOWN/INSIDE 판정과 path(매수·매도 반대)가 맞는다.

**j. 트리거**
- None → `WEAK_KINDS_NOT_RECORDED`, 빈 목록 → `NO_WEAK_KIND`.
- 비교 모드 주문표의 `evidence.weak`가 반영된다.
- ticket_id로 decision_key를 이어 첫 건만 센다.

**k. epoch**
- 항목 scope별로 단위 epoch가 계산된다. `GATE:REQ5_RREC1`이 `REQ5_RREC1_UNK` 단위에도 적용된다.
- 주문표 단위의 첫 날은 `AT-YYYYMMDD-` 날짜다.
- 새 항목의 first_run_day가 채점일 전이고 아직 그 시기 단위가 없으면, 옛 시기 버킷은 `EARLIER_EPOCH`다(발견 없음).
- epochs 파일이 없으면 `EPOCHS_UNAVAILABLE`.

**l. 버킷·발견**
- n < 30 → INSUFFICIENT_SAMPLE.
- NOT_SCORABLE 10% 초과 → INSUFFICIENT_COVERAGE. 달력 범위 밖과 PENDING은 분자·분모에서 뺀다. START_SESSION_NOT_IN_CALENDAR는 센다.
- 합성 30개로 COST / PROTECT / MIXED(반쪽 부호가 다름), STRONG/WEAK, 대역 20% 경계를 확인한다.
- 반쪽 정렬과 동률 처리.

**m. museum**
- MISSING이면 예외 없이 처리.
- INVALID JSON도 예외가 없다.
- 후보 세 종류와 control.
- 필수 칸이 빠진 항목은 errors로 간다.
- 채운 id는 pending에서 빠진다. 같은 id는 뒤가 이긴다.

**n. 견고성**
- JSON이 아닌 decision.json은 errors에 남고 다른 날은 계속 처리된다.
- `check_output_root`가 일지·정책·상태 폴더를 여전히 거부한다.

### 5) `manage-us-stock-strategy/tests/test_journal_score_task_static.py`

PowerShell을 실행하지 않고 파일 글만 검사한다.
- 두 .ps1이 UTF-8로 읽히고 `[CmdletBinding()]`가 있다.
- register 스크립트에 있어야 하는 글자: `InvestmentV2-JournalScore`, `-Weekly`, `Sunday`, `09:20`, `PlanOnly`, `Interactive`, `WakeToRun:$false`, `IgnoreNew`, `Korea Standard Time`.
- register 스크립트는 다른 `InvestmentV2-` 이름을 등록하지 않는다.
- run 스크립트에 있어야 하는 글자: `--learning`, `WEEKLY_LATEST.json`, `journal-score-weekly/v1`, `order_authority`.
- run 스크립트에 없어야 하는 글자: `Invoke-WebRequest`, `Invoke-RestMethod`, `kiwoom`, `Remove-Item`.
- 두 파일에 `stock-strategy-system`, `workspace\policies`, `decision_journal.json` 경로 글자가 없다.

## 테스트

- 대상:
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_score_*.py"`
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_journal_score_task_static*.py"`
  - 두 명령 모두 전부 OK여야 한다. 기존 `test_score_ticket_outcomes.py`도 그대로 통과해야 한다.
- 실제 자료 실행과 PowerShell 실행은 하지 않는다(허용 밖). 병합 뒤 Cowork가 한다.

## 보고 (`docs/claude/evo-s1-report.md`, 한국어 20줄 안팎)

- 바꾼 파일
- 기본 길 불변을 어떻게 확인했는지
- learning 블록 필드 요약
- 테스트 결과(대상·새 실패 수)
- 사전 등록과 해석이 갈린 곳(있으면 그대로)
- 남은 위험

## Judge 확인 항목

- J-a: 바뀐 파일이 allowed_paths 6개뿐인가. 코어(`auto_core*`)·정책·상태·일지·스키마·로케일 파일이 그대로인가.
- J-b: `--learning`이 없을 때 출력·종료 코드·`score_journal` 시그니처가 그대로인가. 코어의 `main(["--journal", ...])` 호출에서 learning 코드가 실행되지 않는가.
- J-c: learning 계산이 실행 중 `auto_core*`를 import하지 않는가(테스트 안 import만 허용). 대역 식(연속 구간, 65개, 선형 분위수)이 사전 등록 3-3과 같고, 같음 테스트 두 가지가 있는가.
- J-d: 다음이 사전 등록 3-0·3-1·3-6과 같은가.
  - 날짜 자격: 계획 뒤 HOLD 포함·day_gates, PLAN_NOT_RUN
  - 보존 표지 규칙
  - 관문 이름(_UNK·연구 기록)
  - 매수·매도 단위, 구속, 구간
  - 충격 구간(사건일이 아니라 shock.open 연속)
  - R-REC1 20세션 묶음
  - 간격
  - epoch(X_UNK·현재 시기)
- J-e: 부호(cf_value 양수 = 비용, path_20은 부호 그대로)와 발견 조건이 사전 등록 4절과 같은가: n ≥ 30, 네 부호, 반쪽 = ⌊n/2⌋와 정렬, 채점 가능률 10%(분모 규칙), 현재 epoch만, 꼬리 20%.
- J-f: 쓰기가 출력 루트·WEEKLY_LATEST.json·logs/뿐인가. docs 파일·decision.json·일지를 쓰지 않는가. 실행기가 learning 있는 보고서만 고르는가.
- J-g: register 스크립트가 `InvestmentV2-JournalScore` 하나만 다루는가. PlanOnly에서 등록하지 않는가. 매주 일요일 09:20·15분·깨우기 없음·StartWhenAvailable인가.
- J-h: 키움 호출·주문 표지·권한 값 변경이 없는가. 기존 권한 줄이 그대로인가.
